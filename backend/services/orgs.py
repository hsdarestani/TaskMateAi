from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Tuple

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import logger
from backend.core.settings import settings
from backend.models import Organization, OrganizationUser, OrganizationUserRole, User

from .base import ServiceBase


class OrganizationService(ServiceBase):
    invite_ttl_hours: int = 168  # one week

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(
        self,
        *,
        name: str,
        owner_user_id: int | None = None,
        plan: str | None = None,
    ) -> Organization:
        if owner_user_id is not None:
            owner = await self.session.get(User, owner_user_id)
            if not owner:
                raise LookupError("user_not_found")
        organization = Organization(name=name, owner_user_id=owner_user_id, plan=plan)
        self.session.add(organization)
        await self.session.flush()

        if owner_user_id is not None:
            await self._ensure_member(
                organization_id=organization.id,
                user_id=owner_user_id,
                role=OrganizationUserRole.ORG_ADMIN,
            )

        await self.session.commit()
        await self.session.refresh(organization)
        logger.info("organization.created", organization_id=organization.id, name=name)
        return organization

    async def get(self, organization_id: int) -> Organization:
        organization = await self.session.get(Organization, organization_id)
        if not organization:
            raise LookupError("organization_not_found")
        return organization

    async def list(self) -> list[Organization]:
        result = await self.session.execute(select(Organization).order_by(Organization.id))
        return list(result.scalars().all())

    async def set_plan(self, organization_id: int, plan: str | None) -> Organization:
        organization = await self.get(organization_id)
        organization.plan = plan
        await self.session.commit()
        await self.session.refresh(organization)
        logger.info("organization.plan_updated", organization_id=organization.id, plan=plan)
        return organization

    async def add_member(
        self,
        organization_id: int,
        user_id: int,
        role: OrganizationUserRole = OrganizationUserRole.MEMBER,
    ) -> OrganizationUser:
        await self.get(organization_id)
        user = await self.session.get(User, user_id)
        if not user:
            raise LookupError("user_not_found")
        membership = await self._ensure_member(
            organization_id=organization_id, user_id=user_id, role=role
        )
        await self.session.commit()
        logger.info(
            "organization.member_added",
            organization_id=organization_id,
            user_id=user_id,
            role=role.value,
        )
        return membership

    async def remove_member(self, organization_id: int, user_id: int) -> None:
        await self.session.execute(
            delete(OrganizationUser).where(
                OrganizationUser.organization_id == organization_id,
                OrganizationUser.user_id == user_id,
            )
        )
        await self.session.commit()
        logger.info(
            "organization.member_removed", organization_id=organization_id, user_id=user_id
        )

    async def generate_invite_code(
        self,
        organization_id: int,
        role: OrganizationUserRole = OrganizationUserRole.MEMBER,
    ) -> str:
        issued_at = int(datetime.now(timezone.utc).timestamp())
        payload = f"{organization_id}:{role.value}:{issued_at}"
        signature = self._sign(payload)
        token = base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode()
        logger.debug(
            "organization.invite_generated",
            organization_id=organization_id,
            role=role.value,
        )
        return token.rstrip("=")

    async def verify_invite_code(self, code: str) -> Tuple[Organization, OrganizationUserRole]:
        padded = code + "=" * (-len(code) % 4)
        raw = base64.urlsafe_b64decode(padded.encode()).decode()
        organization_id_str, role_value, issued_at_str, signature = raw.split(":")

        payload = f"{organization_id_str}:{role_value}:{issued_at_str}"
        if not hmac.compare_digest(self._sign(payload), signature):
            raise ValueError("invalid_invite_signature")

        issued_at = datetime.fromtimestamp(int(issued_at_str), tz=timezone.utc)
        if datetime.now(timezone.utc) - issued_at > timedelta(hours=self.invite_ttl_hours):
            raise ValueError("invite_expired")

        organization_id = int(organization_id_str)
        role = OrganizationUserRole(role_value)
        organization = await self.get(organization_id)
        return organization, role

    async def join_with_invite(self, code: str, user_id: int) -> OrganizationUser:
        organization, role = await self.verify_invite_code(code)
        membership = await self._ensure_member(
            organization_id=organization.id,
            user_id=user_id,
            role=role,
        )
        await self.session.commit()
        logger.info(
            "organization.joined",
            organization_id=organization.id,
            user_id=user_id,
            role=role.value,
        )
        return membership

    async def _ensure_member(
        self,
        *,
        organization_id: int,
        user_id: int,
        role: OrganizationUserRole,
    ) -> OrganizationUser:
        membership_result = await self.session.execute(
            select(OrganizationUser).where(
                OrganizationUser.organization_id == organization_id,
                OrganizationUser.user_id == user_id,
            )
        )
        membership = membership_result.scalar_one_or_none()
        if membership:
            membership.role = role
        else:
            membership = OrganizationUser(
                organization_id=organization_id,
                user_id=user_id,
                role=role,
            )
            self.session.add(membership)
        return membership

    def _sign(self, payload: str) -> str:
        digest = hmac.new(
            settings.jwt_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return digest[:16]
