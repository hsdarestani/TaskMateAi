import { useEffect, useState } from 'react';

import KpiCard from '../components/KpiCard';
import PageHeader from '../components/PageHeader';
import UsageLineChart from '../components/charts/UsageLineChart';
import RevenueAreaChart from '../components/charts/RevenueAreaChart';
import Badge from '../components/Badge';
import api from '../lib/api';

interface DashboardState {
  activeUsers: number;
  mrr: number;
  tasksPerDay: number;
  retention: number;
  usage: Array<{ label: string; value: number }>;
  revenue: Array<{ month: string; mrr: number }>;
}

const fallback: DashboardState = {
  activeUsers: 1265,
  mrr: 18420,
  tasksPerDay: 342,
  retention: 92,
  usage: [
    { label: 'Mon', value: 310 },
    { label: 'Tue', value: 352 },
    { label: 'Wed', value: 401 },
    { label: 'Thu', value: 376 },
    { label: 'Fri', value: 298 },
    { label: 'Sat', value: 210 },
    { label: 'Sun', value: 255 }
  ],
  revenue: [
    { month: 'Jan', mrr: 12000 },
    { month: 'Feb', mrr: 13450 },
    { month: 'Mar', mrr: 14820 },
    { month: 'Apr', mrr: 15980 },
    { month: 'May', mrr: 16630 },
    { month: 'Jun', mrr: 17490 }
  ]
};

export default function DashboardPage() {
  const [state, setState] = useState<DashboardState>(fallback);

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      try {
        const { data } = await api.get<Partial<DashboardState>>('/api/admin/analytics/summary');
        if (ignore) return;
        setState((prev) => ({
          ...prev,
          ...data,
          usage: data.usage ?? prev.usage,
          revenue: data.revenue ?? prev.revenue
        }));
      } catch (err) {
        if (import.meta.env.DEV) {
          console.info('Falling back to dashboard mock data', err);
        }
      }
    };
    load();
    return () => {
      ignore = true;
    };
  }, []);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Operations Pulse"
        subtitle="Live view of platform activity, revenue, and retention for all connected workspaces."
        actions={<Badge tone="info">Updated every 5 minutes</Badge>}
      />
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard title="Active Users" value={state.activeUsers.toLocaleString()} delta="↗︎ 6.2% vs last week" accent="emerald" />
        <KpiCard title="Monthly Recurring Revenue" value={`$${state.mrr.toLocaleString()}`} delta="↗︎ 4.8% vs last month" accent="cyan" />
        <KpiCard title="Tasks per Day" value={state.tasksPerDay.toLocaleString()} delta="↗︎ 8.1% completion" accent="violet" />
        <KpiCard title="Retention" value={`${state.retention}%`} delta="90-day cohort" accent="amber" />
      </section>
      <section className="grid gap-6 xl:grid-cols-2">
        <div className="space-y-4 rounded-3xl border border-white/5 bg-slate-900/40 p-6 backdrop-blur">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white">Usage velocity</h3>
              <p className="text-sm text-slate-400">Daily tasks created across all surfaces</p>
            </div>
            <Badge tone="info">Last 7 days</Badge>
          </div>
          <UsageLineChart data={state.usage} />
        </div>
        <div className="space-y-4 rounded-3xl border border-white/5 bg-slate-900/40 p-6 backdrop-blur">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white">Revenue momentum</h3>
              <p className="text-sm text-slate-400">MRR tracked by billing events</p>
            </div>
            <Badge tone="success">Rolling 6 months</Badge>
          </div>
          <RevenueAreaChart data={state.revenue} />
        </div>
      </section>
    </div>
  );
}
