interface Props {
  title: string;
  value: string;
  delta?: string;
  accent?: 'emerald' | 'cyan' | 'violet' | 'amber';
}

const accentMap: Record<NonNullable<Props['accent']>, string> = {
  emerald: 'from-emerald-500/40 to-emerald-500/10 text-emerald-200',
  cyan: 'from-cyan-500/40 to-cyan-500/10 text-cyan-200',
  violet: 'from-violet-500/40 to-violet-500/10 text-violet-200',
  amber: 'from-amber-500/40 to-amber-500/10 text-amber-200'
};

export default function KpiCard({ title, value, delta, accent = 'emerald' }: Props) {
  return (
    <div
      className={`rounded-3xl border border-white/5 bg-gradient-to-br p-6 backdrop-blur ${accentMap[accent]} flex flex-col gap-3`}
    >
      <p className="text-sm font-medium uppercase tracking-wider text-white/70">{title}</p>
      <p className="text-3xl font-semibold text-white drop-shadow-sm">{value}</p>
      {delta && <p className="text-xs text-white/80">{delta}</p>}
    </div>
  );
}
