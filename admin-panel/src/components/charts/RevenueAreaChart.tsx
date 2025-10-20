import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

interface Props {
  data: Array<{ month: string; mrr: number }>;
}

export default function RevenueAreaChart({ data }: Props) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="mrrGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.6} />
              <stop offset="100%" stopColor="#22d3ee" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#1f2937" strokeDasharray="4 4" />
          <XAxis dataKey="month" stroke="#94a3b8" axisLine={false} tickLine={false} />
          <YAxis stroke="#94a3b8" axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ backgroundColor: '#020617', borderRadius: 16, border: '1px solid rgba(148,163,184,0.2)' }} />
          <Area type="monotone" dataKey="mrr" stroke="#22d3ee" strokeWidth={3} fill="url(#mrrGradient)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
