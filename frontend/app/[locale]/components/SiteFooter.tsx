import Link from 'next/link';
import { getTranslations } from 'next-intl/server';

type SiteFooterProps = {
  locale: string;
};

export async function SiteFooter({ locale }: SiteFooterProps) {
  const common = await getTranslations({ locale, namespace: 'common' });
  const nav = await getTranslations({ locale, namespace: 'nav' });

  const legalLinks = [
    { href: 'privacy', label: common('footer.privacy') },
    { href: 'terms', label: common('footer.terms') }
  ];

  return (
    <footer className="border-t border-white/5 bg-slate-950/60 py-12">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 text-sm text-slate-300 md:flex-row md:items-center md:justify-between">
        <div className="space-y-2">
          <p className="text-base font-semibold text-white">{common('brand')}</p>
          <p className="max-w-md text-sm leading-relaxed text-slate-400">{common('footer.tagline')}</p>
          <p className="text-xs text-slate-500">© {new Date().getFullYear()} TaskMate AI · {common('footer.rights')}</p>
        </div>
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:gap-8">
          <nav aria-label="Footer navigation" className="flex flex-col gap-2 md:flex-row md:gap-4">
            <Link href={`/${locale}`} className="transition hover:text-emerald-300">
              {nav('home')}
            </Link>
            <Link href={`/${locale}/features`} className="transition hover:text-emerald-300">
              {nav('features')}
            </Link>
            <Link href={`/${locale}/pricing`} className="transition hover:text-emerald-300">
              {nav('pricing')}
            </Link>
            <Link href={`/${locale}/contact`} className="transition hover:text-emerald-300">
              {nav('contact')}
            </Link>
          </nav>
          <nav aria-label="Legal" className="flex flex-col gap-2 md:flex-row md:gap-4">
            {legalLinks.map((item) => (
              <Link key={item.href} href={`/${locale}/${item.href}`} className="transition hover:text-emerald-300">
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </div>
    </footer>
  );
}
