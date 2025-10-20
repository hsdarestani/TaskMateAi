import { useEffect, useState } from 'react';

import Badge from '../components/Badge';
import PageHeader from '../components/PageHeader';
import FunnelConversion from '../components/charts/FunnelConversion';
import LanguageDonut from '../components/charts/LanguageDonut';
import UsageHeatmap from '../components/charts/UsageHeatmap';
import api from '../lib/api';

interface HeatmapRow {
  label: string;
  values: number[];
}

interface FunnelRow {
  stage: string;
  value: number;
}

interface LanguageRow {
  code: string;
  label: string;
  value: number;
}

const fallbackHeatmap: HeatmapRow[] = [
  { label: 'Mon', values: [5, 4, 7, 12, 22, 30, 45, 60, 72, 80, 84, 82, 79, 70, 66, 58, 52, 48, 40, 34, 26, 18, 12, 8] },
  { label: 'Tue', values: [6, 5, 8, 14, 28, 35, 50, 68, 86, 92, 95, 88, 82, 76, 70, 63, 56, 49, 42, 36, 30, 20, 12, 9] },
  { label: 'Wed', values: [6, 6, 9, 16, 24, 33, 45, 60, 78, 90, 96, 94, 88, 82, 74, 68, 60, 52, 45, 38, 30, 22, 14, 10] },
  { label: 'Thu', values: [4, 4, 7, 12, 20, 28, 38, 52, 64, 75, 82, 84, 80, 70, 64, 55, 48, 40, 32, 26, 19, 14, 9, 6] },
  { label: 'Fri', values: [3, 3, 5, 8, 12, 18, 26, 34, 40, 48, 54, 58, 56, 50, 44, 38, 32, 26, 20, 16, 12, 8, 6, 4] },
  { label: 'Sat', values: [2, 2, 3, 6, 10, 14, 20, 26, 32, 38, 40, 38, 35, 30, 26, 22, 18, 14, 10, 8, 6, 4, 3, 2] },
  { label: 'Sun', values: [2, 2, 4, 6, 10, 14, 18, 24, 28, 34, 38, 40, 38, 34, 30, 25, 20, 16, 12, 9, 6, 4, 3, 2] }
];

const fallbackFunnel: FunnelRow[] = [
  { stage: 'Trials started', value: 420 },
  { stage: 'Activated', value: 360 },
  { stage: 'Billing setup', value: 220 },
  { stage: 'Paying', value: 168 }
];

const fallbackLanguages: LanguageRow[] = [
  { code: 'en', label: 'English', value: 52 },
  { code: 'fa', label: 'Farsi', value: 31 },
  { code: 'ar', label: 'Arabic', value: 17 }
];

export default function AnalyticsPage() {
  const [heatmap, setHeatmap] = useState<HeatmapRow[]>(fallbackHeatmap);
  const [funnel, setFunnel] = useState<FunnelRow[]>(fallbackFunnel);
  const [languages, setLanguages] = useState<LanguageRow[]>(fallbackLanguages);

  useEffect(() => {
    let ignore = false;
    const fetchAnalytics = async () => {
      try {
        const { data } = await api.get<{
          heatmap?: HeatmapRow[];
          funnel?: FunnelRow[];
          languages?: LanguageRow[];
        }>('/api/admin/analytics/insights');
        if (ignore) return;
        if (Array.isArray(data.heatmap)) {
          setHeatmap(data.heatmap);
        }
        if (Array.isArray(data.funnel)) {
          setFunnel(data.funnel);
        }
        if (Array.isArray(data.languages)) {
          setLanguages(data.languages);
        }
      } catch (err) {
        if (import.meta.env.DEV) {
          console.info('Using fallback analytics data', err);
        }
      }
    };
    fetchAnalytics();
    return () => {
      ignore = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics"
        subtitle="Understand adoption, conversion, and language distribution across surfaces."
        actions={<Badge tone="info">Data normalized nightly</Badge>}
      />
      <section className="space-y-4 rounded-3xl border border-white/5 bg-slate-900/40 p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Usage heatmap</h3>
          <Badge tone="success">All time zones</Badge>
        </div>
        <UsageHeatmap rows={heatmap} />
      </section>
      <div className="grid gap-6 xl:grid-cols-2">
        <section className="space-y-4 rounded-3xl border border-white/5 bg-slate-900/40 p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Trial → paid funnel</h3>
            <Badge tone="warning">Rolling 30 days</Badge>
          </div>
          <FunnelConversion data={funnel} />
        </section>
        <section className="space-y-4 rounded-3xl border border-white/5 bg-slate-900/40 p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Language distribution</h3>
            <Badge tone="info">Telegram + web</Badge>
          </div>
          <LanguageDonut languages={languages} />
        </section>
      </div>
    </div>
  );
}
