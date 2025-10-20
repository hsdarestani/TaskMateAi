import { ResponsiveContainer, FunnelChart, Funnel, LabelList, Tooltip } from 'recharts';

interface Props {
  data: Array<{ stage: string; value: number }>;
}

export default function FunnelConversion({ data }: Props) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <FunnelChart>
          <Tooltip
            contentStyle={{ backgroundColor: '#020617', borderRadius: 16, border: '1px solid rgba(148,163,184,0.2)' }}
            formatter={(value: number) => [`${value}`, 'Accounts']}
          />
          <Funnel dataKey="value" data={data} stroke="#22d3ee" fill="#22d3ee">
            <LabelList dataKey="stage" position="inside" fill="#0f172a" stroke="none" />
          </Funnel>
        </FunnelChart>
      </ResponsiveContainer>
    </div>
  );
}
