import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

interface Props {
  data: Array<{ label: string; value: number }>;
}

export default function UsageLineChart({ data }: Props) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid stroke="#1f2937" strokeDasharray="4 4" />
          <XAxis dataKey="label" stroke="#9ca3af" tickLine={false} axisLine={false} />
          <YAxis stroke="#9ca3af" tickLine={false} axisLine={false} />
          <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: 16, border: '1px solid rgba(148,163,184,0.2)' }} />
          <Line type="monotone" dataKey="value" stroke="#34d399" strokeWidth={3} dot={{ stroke: '#34d399', strokeWidth: 2 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
