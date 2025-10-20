from __future__ import annotations

import asyncio
import csv
import html
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Sequence
from zoneinfo import ZoneInfo

from weasyprint import HTML
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.i18n import format_date, format_datetime, normalize_locale, translate
from backend.core.logging import logger
from backend.core.rbac import Principal
from backend.core.settings import settings
from backend.models import Project, Task, TaskAssignment, User
from backend.schemas.reports import (
    OrgMetrics,
    ReportCounts,
    ReportFormat,
    ReportRequest,
    ReportResponse,
    ReportScope,
    ReportTask,
    TrendPoint,
)

from .base import ServiceBase


class ReportService(ServiceBase):
    reports_dir = Path("/tmp/taskmate_reports")

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def generate(self, payload: ReportRequest, principal: Principal) -> ReportResponse:  # type: ignore[override]
        user = await self._fetch_user(payload.user_id)
        locale = normalize_locale(payload.locale or (user.language if user else None))
        tz = self._resolve_timezone(payload.timezone or (user.timezone if user and user.timezone else None))
        window_start, window_end, anchor = self._calculate_window(payload.report_type, payload.date, tz)
        scope = self._determine_scope(payload)

        tasks = await self._fetch_tasks(payload, window_start, window_end)
        counts = self._compute_counts(tasks)

        next_tasks: List[ReportTask] = []
        overdue_tasks: List[ReportTask] = []
        metrics: OrgMetrics | None = None
        file_url: str | None = None

        if scope is ReportScope.USER:
            next_tasks = self._select_next_tasks(tasks, tz)
            overdue_tasks = self._select_overdue_tasks(tasks, tz)
            summary = self._format_user_summary(
                locale=locale,
                report_type=payload.report_type,
                anchor=anchor,
                counts=counts,
                next_tasks=next_tasks,
                overdue_tasks=overdue_tasks,
                tz=tz,
                window_start=window_start,
                window_end=window_end,
            )

            if payload.format is ReportFormat.PDF:
                file_path = await self._render_user_pdf(
                    locale=locale,
                    payload=payload,
                    principal=principal,
                    counts=counts,
                    summary=summary,
                    tasks=tasks,
                    tz=tz,
                    window_start=window_start,
                    window_end=window_end,
                )
                file_url = file_path.as_posix()
            elif payload.format is ReportFormat.CSV:
                logger.warning("report.format.unsupported", scope=scope.value, format=payload.format.value)
        else:
            metrics = self._compute_org_metrics(tasks, tz, locale)
            summary = self._format_org_summary(
                locale=locale,
                scope=scope,
                report_type=payload.report_type,
                counts=counts,
                metrics=metrics,
                tz=tz,
                window_start=window_start,
                window_end=window_end,
            )

            if payload.format is ReportFormat.CSV:
                file_path = await self._render_org_csv(
                    locale=locale,
                    payload=payload,
                    principal=principal,
                    metrics=metrics,
                    tz=tz,
                    window_start=window_start,
                    window_end=window_end,
                )
                file_url = file_path.as_posix()
            elif payload.format is ReportFormat.PDF:
                logger.warning("report.format.unsupported", scope=scope.value, format=payload.format.value)

        logger.info(
            "report.generated",
            scope=scope.value,
            report=payload.report_type,
            user=payload.user_id,
            organization=payload.organization_id,
            team=payload.team_id,
            project=payload.project_id,
            task_count=len(tasks),
        )

        return ReportResponse(
            report_type=payload.report_type,
            scope=scope,
            summary=summary,
            counts=counts,
            next_tasks=next_tasks,
            overdue_tasks=overdue_tasks,
            metrics=metrics,
            file_url=file_url,
            format=payload.format,
            generated_at=datetime.now(timezone.utc),
        )

    async def _fetch_user(self, user_id: int | None) -> User | None:
        if user_id is None:
            return None
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    def _resolve_timezone(self, name: str | None) -> ZoneInfo:
        candidate = name or settings.default_timezone
        try:
            return ZoneInfo(candidate)
        except Exception:  # noqa: BLE001
            logger.warning("report.invalid_timezone", requested=name)
            try:
                return ZoneInfo(settings.default_timezone)
            except Exception:  # noqa: BLE001
                return ZoneInfo("UTC")

    def _calculate_window(
        self,
        report_type: str,
        report_date: date | None,
        tz: ZoneInfo,
    ) -> tuple[datetime, datetime, datetime]:
        now_local = datetime.now(timezone.utc).astimezone(tz)
        anchor = datetime.combine(report_date, time.min, tzinfo=tz) if report_date else now_local.replace(hour=0, minute=0, second=0, microsecond=0)

        if report_type == "weekly":
            window_start_local = anchor
            window_end_local = anchor + timedelta(days=7)
        elif report_type == "monthly":
            window_start_local = anchor.replace(day=1)
            next_month = (window_start_local + timedelta(days=32)).replace(day=1)
            window_end_local = next_month
        else:
            window_start_local = anchor
            window_end_local = anchor + timedelta(days=1)

        return (
            window_start_local.astimezone(timezone.utc),
            window_end_local.astimezone(timezone.utc),
            window_start_local,
        )

    def _determine_scope(self, payload: ReportRequest) -> ReportScope:
        if payload.user_id is not None:
            return ReportScope.USER
        if payload.project_id is not None:
            return ReportScope.PROJECT
        if payload.team_id is not None:
            return ReportScope.TEAM
        if payload.organization_id is not None:
            return ReportScope.ORGANIZATION
        return ReportScope.USER

    async def _fetch_tasks(
        self, payload: ReportRequest, window_start: datetime, window_end: datetime
    ) -> List[Task]:
        query = (
            select(Task)
            .where(Task.created_at >= window_start, Task.created_at < window_end)
            .order_by(Task.created_at)
        )

        if payload.user_id is not None:
            query = query.where(Task.user_id == payload.user_id)
        if payload.organization_id is not None:
            query = query.where(Task.organization_id == payload.organization_id)
        if payload.project_id is not None:
            query = query.where(Task.project_id == payload.project_id)
        if payload.team_id is not None:
            team_assignment = (
                select(TaskAssignment.id)
                .where(
                    TaskAssignment.task_id == Task.id,
                    TaskAssignment.assigned_team_id == payload.team_id,
                )
                .exists()
            )
            project_match = (
                select(Project.id)
                .where(Project.id == Task.project_id, Project.team_id == payload.team_id)
                .exists()
            )
            query = query.where(or_(team_assignment, project_match))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    def _compute_counts(self, tasks: Iterable[Task]) -> ReportCounts:
        total = 0
        completed = 0
        overdue = 0
        now_utc = datetime.now(timezone.utc)

        for task in tasks:
            total += 1
            if self._is_completed(task):
                completed += 1
            elif task.due_at and task.due_at < now_utc:
                overdue += 1

        return ReportCounts(total=total, completed=completed, overdue=overdue)

    def _is_completed(self, task: Task) -> bool:
        status = (task.status or "").lower()
        return status in {"done", "completed", "resolved"} or task.end_at is not None

    def _select_next_tasks(self, tasks: Iterable[Task], tz: ZoneInfo, limit: int = 3) -> List[ReportTask]:
        pending = [task for task in tasks if not self._is_completed(task)]
        default_due = datetime.max.replace(tzinfo=timezone.utc)
        pending.sort(key=lambda task: ((task.due_at or default_due), task.created_at or default_due))
        return [self._to_report_task(task, tz) for task in pending[:limit]]

    def _select_overdue_tasks(self, tasks: Iterable[Task], tz: ZoneInfo, limit: int = 3) -> List[ReportTask]:
        now_utc = datetime.now(timezone.utc)
        overdue_tasks = [
            task
            for task in tasks
            if task.due_at and task.due_at < now_utc and not self._is_completed(task)
        ]
        overdue_tasks.sort(key=lambda task: task.due_at)
        return [self._to_report_task(task, tz) for task in overdue_tasks[:limit]]

    def _to_report_task(self, task: Task, tz: ZoneInfo) -> ReportTask:
        due_local = task.due_at.astimezone(tz) if task.due_at else None
        return ReportTask(
            id=task.id,
            title=task.title,
            status=task.status,
            priority=task.priority,
            due_at=due_local,
        )

    def _format_user_summary(
        self,
        *,
        locale: str,
        report_type: str,
        anchor: datetime,
        counts: ReportCounts,
        next_tasks: Sequence[ReportTask],
        overdue_tasks: Sequence[ReportTask],
        tz: ZoneInfo,
        window_start: datetime,
        window_end: datetime,
    ) -> str:
        header_key = {
            "daily": "report_user_header_daily",
            "weekly": "report_user_header_weekly",
            "monthly": "report_user_header_monthly",
        }.get(report_type, "report_user_header_daily")
        period_label = translate(
            locale,
            header_key,
            date=format_date(anchor, locale, tz, fmt="medium"),
        )

        lines = [period_label]
        lines.append(
            translate(
                locale,
                "report_user_counts",
                total=counts.total,
                completed=counts.completed,
                overdue=counts.overdue,
            )
        )

        start_local = format_datetime(window_start, locale, tz, fmt="short")
        end_local = format_datetime(window_end, locale, tz, fmt="short")
        lines.append(translate(locale, "report_period", start=start_local, end=end_local))

        if counts.total == 0:
            lines.append(translate(locale, "report_user_no_tasks"))
            return "\n".join(lines)

        if next_tasks:
            lines.append(translate(locale, "report_user_next_header"))
            for task in next_tasks:
                if task.due_at:
                    due_text = format_datetime(task.due_at, locale, tz, fmt="short")
                    lines.append(translate(locale, "report_user_task_line", title=task.title, due=due_text))
                else:
                    lines.append(translate(locale, "report_user_task_line_no_due", title=task.title))

        if overdue_tasks:
            lines.append(translate(locale, "report_user_overdue_header"))
            for task in overdue_tasks:
                if task.due_at:
                    due_text = format_datetime(task.due_at, locale, tz, fmt="short")
                    lines.append(translate(locale, "report_user_task_line", title=task.title, due=due_text))
                else:
                    lines.append(translate(locale, "report_user_task_line_no_due", title=task.title))
        else:
            lines.append(translate(locale, "report_user_overdue_empty"))

        return "\n".join(lines)

    def _compute_org_metrics(self, tasks: Iterable[Task], tz: ZoneInfo, locale: str) -> OrgMetrics:
        throughput = 0
        completed = 0
        overdue_by_period: defaultdict[str, int] = defaultdict(int)
        active_users = set()

        for task in tasks:
            throughput += 1
            if task.user_id:
                active_users.add(task.user_id)
            if self._is_completed(task):
                completed += 1
            elif task.due_at:
                period_key = format_date(task.due_at, locale, tz, fmt="medium")
                overdue_by_period[period_key] += 1

        completion_rate = (completed / throughput * 100) if throughput else 0.0
        trend = [
            TrendPoint(period=period, overdue=count)
            for period, count in sorted(overdue_by_period.items())
        ]

        return OrgMetrics(
            throughput=throughput,
            completion_rate=round(completion_rate, 1),
            overdue_trend=trend,
            active_users=len(active_users),
        )

    def _format_org_summary(
        self,
        *,
        locale: str,
        scope: ReportScope,
        report_type: str,
        counts: ReportCounts,
        metrics: OrgMetrics,
        tz: ZoneInfo,
        window_start: datetime,
        window_end: datetime,
    ) -> str:
        period_label = {
            "daily": translate(locale, "report_period_label_daily"),
            "weekly": translate(locale, "report_period_label_weekly"),
            "monthly": translate(locale, "report_period_label_monthly"),
        }.get(report_type, translate(locale, "report_period_label_daily"))

        header_key = {
            ReportScope.ORGANIZATION: "report_org_header_organization",
            ReportScope.TEAM: "report_org_header_team",
            ReportScope.PROJECT: "report_org_header_project",
        }.get(scope, "report_org_header_organization")

        lines = [translate(locale, header_key, period=period_label)]
        lines.append(
            translate(
                locale,
                "report_user_counts",
                total=counts.total,
                completed=counts.completed,
                overdue=counts.overdue,
            )
        )

        lines.append(translate(locale, "report_org_throughput", count=metrics.throughput))
        lines.append(
            translate(
                locale,
                "report_org_completion_rate",
                rate=f"{metrics.completion_rate:.1f}",
            )
        )
        lines.append(
            translate(locale, "report_org_active_users", count=metrics.active_users)
        )

        if metrics.overdue_trend:
            trend_entries = [
                translate(locale, "report_org_trend_entry", period=point.period, overdue=point.overdue)
                for point in metrics.overdue_trend
            ]
            lines.append(
                translate(locale, "report_org_overdue_trend", trend=", ".join(trend_entries))
            )
        else:
            lines.append(translate(locale, "report_org_no_trend"))

        start_local = format_datetime(window_start, locale, tz, fmt="short")
        end_local = format_datetime(window_end, locale, tz, fmt="short")
        lines.append(translate(locale, "report_period", start=start_local, end=end_local))
        return "\n".join(lines)

    async def _render_user_pdf(
        self,
        *,
        locale: str,
        payload: ReportRequest,
        principal: Principal,
        counts: ReportCounts,
        summary: str,
        tasks: Sequence[Task],
        tz: ZoneInfo,
        window_start: datetime,
        window_end: datetime,
    ) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(datetime.now(timezone.utc).timestamp())
        scope_slug = payload.report_type
        filename = self.reports_dir / f"{scope_slug}-{self._safe_slug(principal.subject)}-{timestamp}.pdf"

        direction = "rtl" if locale in {"fa", "ar"} else "ltr"
        align = "right" if direction == "rtl" else "left"

        start_local = format_datetime(window_start, locale, tz, fmt="short")
        end_local = format_datetime(window_end, locale, tz, fmt="short")
        counts_line = translate(
            locale,
            "report_pdf_counts",
            total=counts.total,
            completed=counts.completed,
            overdue=counts.overdue,
        )

        table_rows = []
        for task in tasks:
            due_text = (
                format_datetime(task.due_at, locale, tz, fmt="short")
                if task.due_at
                else translate(locale, "report_task_no_due")
            )
            table_rows.append(
                "<tr>"
                f"<td>{task.id}</td>"
                f"<td>{html.escape(task.title)}</td>"
                f"<td>{html.escape(task.status or '-')}</td>"
                f"<td>{html.escape(due_text)}</td>"
                f"<td>{html.escape(task.priority or '-')}</td>"
                "</tr>"
            )

        html_content = f"""
        <html lang="{locale}" dir="{direction}">
            <head>
                <meta charset="utf-8" />
                <style>
                    body {{ font-family: 'DejaVu Sans', Arial, sans-serif; margin: 2rem; direction: {direction}; text-align: {align}; }}
                    h1 {{ margin-bottom: 0.5rem; }}
                    table {{ border-collapse: collapse; width: 100%; margin-top: 1.5rem; }}
                    th, td {{ border: 1px solid #ccc; padding: 0.5rem; text-align: {align}; }}
                    th {{ background-color: #f5f5f5; }}
                    .summary {{ white-space: pre-line; margin-top: 1rem; }}
                </style>
            </head>
            <body>
                <h1>{html.escape(translate(locale, "report_pdf_title"))}</h1>
                <p>{html.escape(translate(locale, "report_period", start=start_local, end=end_local))}</p>
                <p>{html.escape(counts_line)}</p>
                <div class="summary">{html.escape(summary)}</div>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>{html.escape(translate(locale, "report_table_task"))}</th>
                            <th>{html.escape(translate(locale, "report_table_status"))}</th>
                            <th>{html.escape(translate(locale, "report_table_due"))}</th>
                            <th>{html.escape(translate(locale, "report_table_priority"))}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(table_rows) if table_rows else '<tr><td colspan="5">' + html.escape(translate(locale, "report_user_no_tasks")) + '</td></tr>'}
                    </tbody>
                </table>
            </body>
        </html>
        """

        await asyncio.to_thread(HTML(string=html_content).write_pdf, filename)
        return filename

    async def _render_org_csv(
        self,
        *,
        locale: str,
        payload: ReportRequest,
        principal: Principal,
        metrics: OrgMetrics,
        tz: ZoneInfo,
        window_start: datetime,
        window_end: datetime,
    ) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(datetime.now(timezone.utc).timestamp())
        scope_slug = self._determine_scope(payload).value
        filename = self.reports_dir / f"{payload.report_type}-{scope_slug}-{self._safe_slug(principal.subject)}-{timestamp}.csv"

        start_local = format_datetime(window_start, locale, tz, fmt="short")
        end_local = format_datetime(window_end, locale, tz, fmt="short")

        rows: List[List[str]] = [
            [translate(locale, "report_csv_period_start"), start_local],
            [translate(locale, "report_csv_period_end"), end_local],
            ["", ""],
            [translate(locale, "report_csv_header_metric"), translate(locale, "report_csv_header_value")],
            [translate(locale, "report_metric_throughput"), str(metrics.throughput)],
            [
                translate(locale, "report_metric_completion_rate"),
                f"{metrics.completion_rate:.1f}%",
            ],
            [translate(locale, "report_metric_active_users"), str(metrics.active_users)],
        ]

        if metrics.overdue_trend:
            rows.append(["", ""])
            rows.append([
                translate(locale, "report_metric_overdue_trend"),
                "",
            ])
            rows.append([
                translate(locale, "report_csv_header_period"),
                translate(locale, "report_csv_header_overdue"),
            ])
            for point in metrics.overdue_trend:
                rows.append([point.period, str(point.overdue)])
        else:
            rows.append([
                translate(locale, "report_metric_overdue_trend"),
                translate(locale, "report_org_no_trend"),
            ])

        await asyncio.to_thread(self._write_csv, filename, rows)
        return filename

    @staticmethod
    def _write_csv(path: Path, rows: Sequence[Sequence[str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerows(rows)

    @staticmethod
    def _safe_slug(value: object) -> str:
        base = str(value or "subject")
        sanitized = [char if char.isalnum() else "-" for char in base.lower()]
        return "".join(sanitized).strip("-") or "subject"
