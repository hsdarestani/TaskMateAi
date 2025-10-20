import type { Metadata } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages, getTranslations, unstable_setRequestLocale } from 'next-intl/server';
import { notFound } from 'next/navigation';
import type { ReactNode } from 'react';

import { SiteFooter } from './components/SiteFooter';
import { SiteHeader } from './components/SiteHeader';

const locales = ['en', 'fa', 'ar'] as const;
type Locale = (typeof locales)[number];

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export async function generateMetadata({
  params
}: {
  params: { locale: Locale };
}): Promise<Metadata> {
  const locale = params.locale;
  const meta = await getTranslations({ locale, namespace: 'meta' });

  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://taskmate.ai';
  const url = `${baseUrl}/${locale}`;

  return {
    title: meta('title'),
    description: meta('description'),
    keywords: meta('keywords'),
    alternates: {
      canonical: url
    },
    openGraph: {
      title: meta('ogTitle'),
      description: meta('ogDescription'),
      url,
      siteName: meta('siteName'),
      type: 'website'
    },
    twitter: {
      card: 'summary_large_image',
      title: meta('ogTitle'),
      description: meta('ogDescription'),
      site: meta('twitterHandle')
    }
  };
}

export default async function LocaleLayout({
  children,
  params
}: {
  children: ReactNode;
  params: { locale: Locale };
}) {
  const locale = params.locale;

  if (!locales.includes(locale)) {
    notFound();
  }

  unstable_setRequestLocale(locale);
  const messages = await getMessages();
  const dir: 'ltr' | 'rtl' = locale === 'ar' || locale === 'fa' ? 'rtl' : 'ltr';

  return (
    <html lang={locale} dir={dir} suppressHydrationWarning>
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <div className="relative min-h-screen overflow-hidden">
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top,_rgba(16,185,129,0.35),_transparent_55%),radial-gradient(circle_at_bottom,_rgba(59,130,246,0.25),_transparent_55%)]"
            />
            <div className="absolute inset-0 -z-10 bg-slate-950/80" aria-hidden />
            <div className="relative flex min-h-screen flex-col backdrop-blur">
              <SiteHeader locale={locale} dir={dir} />
              <main className="flex-1">
                <div className="mx-auto w-full max-w-6xl px-6 pb-16 pt-8 md:pt-12">{children}</div>
              </main>
              <SiteFooter locale={locale} />
            </div>
          </div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
