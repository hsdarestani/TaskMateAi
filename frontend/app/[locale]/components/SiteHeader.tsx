import Link from 'next/link';
import { getTranslations } from 'next-intl/server';

import { CTAButton } from './CTAButton';
import { LocaleSwitcher } from './LocaleSwitcher';

type SiteHeaderProps = {
  locale: string;
  dir: 'ltr' | 'rtl';
};

export async function SiteHeader({ locale, dir }: SiteHeaderProps) {
  const nav = await getTranslations({ locale, namespace: 'nav' });
  const common = await getTranslations({ locale, namespace: 'common' });

  const links = [
    { href: '', label: nav('home') },
    { href: 'features', label: nav('features') },
    { href: 'pricing', label: nav('pricing') },
    { href: 'guide', label: nav('guide') },
    { href: 'blog', label: nav('blog') },
    { href: 'enterprise', label: nav('enterprise') }
  ];

  return (
    <header className="sticky top-0 z-30 border-b border-white/5 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
        <Link
          href={`/${locale}`}
          className="flex items-center gap-3 text-sm font-semibold text-white transition hover:text-emerald-300"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-emerald-400/10 text-lg text-emerald-300 shadow-inner shadow-emerald-500/10">
            TM
          </span>
          <span className="hidden md:inline">{common('brand')}</span>
        </Link>
        <nav className="hidden items-center gap-6 text-sm font-medium text-slate-200 md:flex">
          {links.map((item) => (
            <Link
              key={item.href}
              href={`/${locale}/${item.href}`.replace(/\/$/, '')}
              className="rounded-full px-3 py-2 transition hover:bg-white/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-200"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <LocaleSwitcher locale={locale} dir={dir} />
          <CTAButton size="md" className="hidden md:inline-flex">
            {common('cta')}
          </CTAButton>
        </div>
      </div>
    </header>
  );
}
