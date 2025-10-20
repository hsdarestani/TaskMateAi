import { type ReactNode } from 'react';

interface Props {
  tone?: 'success' | 'warning' | 'danger' | 'info';
  children: ReactNode;
}

const toneMap: Record<NonNullable<Props['tone']>, string> = {
  success: 'bg-emerald-500/20 text-emerald-200 border border-emerald-400/30',
  warning: 'bg-amber-500/20 text-amber-200 border border-amber-400/30',
  danger: 'bg-rose-500/20 text-rose-200 border border-rose-400/30',
  info: 'bg-cyan-500/20 text-cyan-200 border border-cyan-400/30'
};

export default function Badge({ tone = 'info', children }: Props) {
  return <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${toneMap[tone]}`}>{children}</span>;
}
