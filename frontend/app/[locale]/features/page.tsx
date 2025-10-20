import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';

import { CTAButton } from '../components/CTAButton';

type PageProps = {
  params: { locale: string };
};

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const features = await getTranslations({ locale: params.locale, namespace: 'featuresPage' });
  return {
    title: `${features('title')} · TaskMate AI`,
    description: features('intro')
  };
}

export default async function FeaturesPage({ params }: PageProps) {
  const locale = params.locale;
  const features = await getTranslations({ locale, namespace: 'featuresPage' });
  const common = await getTranslations({ locale, namespace: 'common' });

  const sections = features.raw('sections') as Record<
    string,
    { title: string; description: string; points: string[] }
  >;

  return (
    <div className="space-y-16">
      <header className="space-y-4 rounded-3xl border border-white/10 bg-slate-950/60 p-10 shadow-lg shadow-black/40">
        <p className="text-sm uppercase tracking-[0.3em] text-emerald-300">TaskMate AI</p>
        <h1 className="text-4xl font-semibold text-white md:text-5xl">{features('title')}</h1>
        <p className="max-w-3xl text-lg text-slate-300">{features('intro')}</p>
        <CTAButton size="md">{common('cta')}</CTAButton>
      </header>

      <div className="grid gap-8">
        {Object.values(sections).map((section) => (
          <section
            key={section.title}
            className="rounded-3xl border border-white/5 bg-slate-900/70 p-8 shadow-lg shadow-black/40"
          >
            <h2 className="text-2xl font-semibold text-white">{section.title}</h2>
            <p className="mt-4 max-w-3xl text-base leading-relaxed text-slate-300">
              {section.description}
            </p>
            <ul className="mt-6 grid gap-3 text-sm text-slate-200 md:grid-cols-2">
              {section.points.map((point) => (
                <li
                  key={point}
                  className="flex items-start gap-3 rounded-2xl bg-slate-950/70 p-4 shadow-inner shadow-black/50"
                >
                  <span aria-hidden className="mt-1 text-emerald-300">
                    ●
                  </span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
