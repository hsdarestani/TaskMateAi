import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';

type PageProps = {
  params: { locale: string };
};

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const privacy = await getTranslations({ locale: params.locale, namespace: 'privacyPage' });
  return {
    title: `${privacy('title')} · TaskMate AI`,
    description: privacy('intro')
  };
}

export default async function PrivacyPage({ params }: PageProps) {
  const locale = params.locale;
  const privacy = await getTranslations({ locale, namespace: 'privacyPage' });

  const sections = privacy.raw('sections') as Array<{ heading: string; body: string }>;

  return (
    <div className="space-y-8">
      <header className="space-y-4">
        <h1 className="text-4xl font-semibold text-white md:text-5xl">{privacy('title')}</h1>
        <p className="max-w-2xl text-base text-slate-300">{privacy('intro')}</p>
      </header>
      <div className="space-y-6">
        {sections.map((section) => (
          <section
            key={section.heading}
            className="rounded-3xl border border-white/10 bg-slate-900/70 p-6 shadow-inner shadow-black/40"
          >
            <h2 className="text-xl font-semibold text-white">{section.heading}</h2>
            <p className="mt-3 text-sm leading-relaxed text-slate-300">{section.body}</p>
          </section>
        ))}
      </div>
    </div>
  );
}
