import { type InputHTMLAttributes } from 'react';

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export default function SearchInput({ label, ...props }: Props) {
  return (
    <label className="flex w-full flex-col gap-2 text-xs uppercase tracking-wide text-slate-400">
      <span>{label}</span>
      <input
        {...props}
        className="w-full rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-2 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400 focus:outline-none"
      />
    </label>
  );
}
