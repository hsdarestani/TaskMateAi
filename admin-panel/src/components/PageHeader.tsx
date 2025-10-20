import { type ReactNode } from 'react';

interface Props {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export default function PageHeader({ title, subtitle, actions }: Props) {
  return (
    <div className="flex flex-col gap-4 rounded-3xl border border-white/5 bg-slate-900/40 p-6 backdrop-blur">
      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-white">{title}</h2>
        {subtitle && <p className="text-sm text-slate-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
    </div>
  );
}
