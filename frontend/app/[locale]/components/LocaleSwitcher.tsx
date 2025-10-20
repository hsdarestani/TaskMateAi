'use client';

import { usePathname, useRouter } from 'next/navigation';
import { useTransition } from 'react';

const locales = [
  { code: 'en', label: 'English' },
  { code: 'fa', label: 'فارسی' },
  { code: 'ar', label: 'العربية' }
];

interface LocaleSwitcherProps {
  locale: string;
  dir: 'ltr' | 'rtl';
}

export function LocaleSwitcher({ locale, dir }: LocaleSwitcherProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  return (
    <label className="flex items-center gap-2 text-xs font-medium text-slate-300">
      <span className="sr-only">Change language</span>
      <select
        aria-label="Change language"
        className="rounded-full border border-slate-700/60 bg-slate-900/60 px-3 py-1 text-slate-100 shadow-inner focus:border-emerald-400 focus:outline-none"
        defaultValue={locale}
        dir={dir}
        onChange={(event) => {
          const targetLocale = event.target.value;
          startTransition(() => {
            const segments = (pathname ?? '/').split('/').filter(Boolean);
            if (segments.length === 0) {
              router.replace(`/${targetLocale}`);
              return;
            }

            segments[0] = targetLocale;
            router.replace(`/${segments.join('/')}`);
          });
        }}
        disabled={isPending}
      >
        {locales.map((item) => (
          <option key={item.code} value={item.code}>
            {item.label}
          </option>
        ))}
      </select>
    </label>
  );
}
