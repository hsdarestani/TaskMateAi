import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';

import { CTAButton } from '../components/CTAButton';

type PageProps = {
  params: { locale: string };
};

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const enterprise = await getTranslations({ locale: params.locale, namespace: 'enterprisePage' });
  return {
    title: `${enterprise('title')} · TaskMate AI`,
    description: enterprise('intro')
  };
}

export default async function EnterprisePage({ params }: PageProps) {
  const locale = params.locale;
  const enterprise = await getTranslations({ locale, namespace: 'enterprisePage' });
  const common = await getTranslations({ locale, namespace: 'common' });

  const highlights = enterprise.raw('highlights') as Array<{ title: string; description: string }>;

  return (
    <div className="space-y-12">
      <header className="space-y-4 rounded-3xl border border-emerald-300/40 bg-emerald-400/10 p-10 shadow-lg shadow-emerald-500/20">
        <h1 className="text-4xl font-semibold text-white md:text-5xl">{enterprise('title')}</h1>
        <p className="max-w-3xl text-lg text-emerald-100">{enterprise('intro')}</p>
        <CTAButton size="md" className="w-fit">
          {enterprise('cta')}
        </CTAButton>
      </header>

      <div className="grid gap-6 md:grid-cols-3">
        {highlights.map((item) => (
          <article
            key={item.title}
            className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-lg shadow-black/40"
          >
            <h2 className="text-xl font-semibold text-white">{item.title}</h2>
            <p className="mt-3 text-sm text-slate-300">{item.description}</p>
          </article>
        ))}
      </div>

      <section className="rounded-3xl border border-white/10 bg-slate-900/70 p-8 text-sm text-slate-300">
        <p>
          {common('description')}
        </p>
      </section>
    </div>
  );
}
