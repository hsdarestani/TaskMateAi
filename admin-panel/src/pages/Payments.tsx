import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import Badge from '../components/Badge';
import PageHeader from '../components/PageHeader';
import Timeline from '../components/Timeline';
import api from '../lib/api';

interface PaymentRecord {
  id: string;
  title: string;
  timestamp: string;
  description: string;
  status: 'pending' | 'completed' | 'failed';
}

interface RevenueBreakdown {
  label: string;
  zibal: number;
  crypto: number;
}

const fallbackTimeline: PaymentRecord[] = [
  {
    id: 'p-1',
    title: 'Moonlit AI upgraded to Growth plan',
    timestamp: '2024-07-06 09:42',
    description: 'Zibal • 42,000,000 IRR • Ref #ZB-9123',
    status: 'completed'
  },
  {
    id: 'p-2',
    title: 'Atlas Labs renewed Starter plan',
    timestamp: '2024-07-05 19:15',
    description: 'CryptoBot • 180 USDT • Invoice #CB-5530',
    status: 'completed'
  },
  {
    id: 'p-3',
    title: 'Aurora Studio payment failed',
    timestamp: '2024-07-05 08:03',
    description: 'Zibal • 24,000,000 IRR • Card declined',
    status: 'failed'
  }
];

const fallbackRevenue: RevenueBreakdown[] = [
  { label: 'Week 22', zibal: 42, crypto: 9 },
  { label: 'Week 23', zibal: 44, crypto: 14 },
  { label: 'Week 24', zibal: 46, crypto: 18 },
  { label: 'Week 25', zibal: 52, crypto: 25 },
  { label: 'Week 26', zibal: 59, crypto: 31 }
];

export default function PaymentsPage() {
  const [timeline, setTimeline] = useState<PaymentRecord[]>(fallbackTimeline);
  const [revenue, setRevenue] = useState<RevenueBreakdown[]>(fallbackRevenue);

  useEffect(() => {
    let ignore = false;
    const fetchPayments = async () => {
      try {
        const [{ data: timelineResponse }, { data: revenueResponse }] = await Promise.all([
          api.get<{ results: PaymentRecord[] }>('/api/admin/payments'),
          api.get<{ breakdown: RevenueBreakdown[] }>('/api/admin/payments/summary')
        ]);
        if (ignore) return;
        if (Array.isArray(timelineResponse.results)) {
          setTimeline(timelineResponse.results);
        }
        if (Array.isArray(revenueResponse.breakdown)) {
          setRevenue(revenueResponse.breakdown);
        }
      } catch (err) {
        if (import.meta.env.DEV) {
          console.info('Using fallback payment data', err);
        }
      }
    };
    fetchPayments();
    return () => {
      ignore = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Payments"
        subtitle="Monitor revenue performance and gateway health across Zibal and CryptoBot."
        actions={<Badge tone="success">Settlements synced hourly</Badge>}
      />
      <div className="grid gap-6 xl:grid-cols-2">
        <section className="space-y-4 rounded-3xl border border-white/5 bg-slate-900/40 p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Gateway revenue mix</h3>
            <Badge tone="info">in millions IRR</Badge>
          </div>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={revenue}>
                <CartesianGrid stroke="#1f2937" vertical={false} />
                <XAxis dataKey="label" stroke="#94a3b8" axisLine={false} tickLine={false} />
                <YAxis stroke="#94a3b8" axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#020617', borderRadius: 16, border: '1px solid rgba(148,163,184,0.2)' }}
                />
                <Bar dataKey="zibal" stackId="gateway" fill="#34d399" radius={[12, 12, 12, 12]} />
                <Bar dataKey="crypto" stackId="gateway" fill="#22d3ee" radius={[12, 12, 12, 12]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="space-y-4 rounded-3xl border border-white/5 bg-slate-900/40 p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Recent transactions</h3>
            <Badge tone="warning">Realtime feed</Badge>
          </div>
          <Timeline items={timeline} />
        </section>
      </div>
    </div>
  );
}
