import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';

import { CTAButton } from '../components/CTAButton';

type PageProps = {
  params: { locale: string };
};

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const contact = await getTranslations({ locale: params.locale, namespace: 'contactPage' });
  return {
    title: `${contact('title')} · TaskMate AI`,
    description: contact('description')
  };
}

export default async function ContactPage({ params }: PageProps) {
  const locale = params.locale;
  const contact = await getTranslations({ locale, namespace: 'contactPage' });
  const common = await getTranslations({ locale, namespace: 'common' });

  const sections = contact.raw('sections') as Record<string, { title: string; body: string }>;

  return (
    <div className="space-y-12">
      <header className="space-y-4 text-center">
        <h1 className="text-4xl font-semibold text-white md:text-5xl">{contact('title')}</h1>
        <p className="mx-auto max-w-2xl text-lg text-slate-300">{contact('description')}</p>
        <CTAButton size="md" className="mx-auto w-fit">
          {common('cta')}
        </CTAButton>
      </header>

      <div className="grid gap-6 md:grid-cols-3">
        {Object.entries(sections).map(([key, value]) => (
          <section
            key={key}
            className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 text-center shadow-lg shadow-black/40"
            aria-labelledby={`contact-${key}`}
          >
            <h2 id={`contact-${key}`} className="text-xl font-semibold text-white">
              {value.title}
            </h2>
            <p className="mt-3 text-sm text-slate-300">
              <a className="text-emerald-300 underline-offset-4 hover:underline" href={`mailto:${value.body}`}>
                {value.body}
              </a>
            </p>
          </section>
        ))}
      </div>
    </div>
  );
}
