import Script from 'next/script';
import { getTranslations } from 'next-intl/server';

import { CTAButton } from './components/CTAButton';

type PageProps = {
  params: { locale: string };
};

export default async function HomePage({ params }: PageProps) {
  const locale = params.locale;
  const home = await getTranslations({ locale, namespace: 'home' });
  const common = await getTranslations({ locale, namespace: 'common' });

  const stats = home.raw('hero.stats') as Array<{ label: string; value: string }>;
  const cards = home.raw('featureHighlights.cards') as Array<{
    title: string;
    description: string;
    badge: string;
  }>;
  const steps = home.raw('workflow.steps') as Array<{
    title: string;
    description: string;
    icon: string;
  }>;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: common('brand'),
    applicationCategory: 'ProductivityApplication',
    operatingSystem: 'Web',
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'USD'
    },
    inLanguage: ['en', 'fa', 'ar']
  };

  return (
    <div className="space-y-20">
      <Script id="json-ld-home" type="application/ld+json">
        {JSON.stringify(jsonLd)}
      </Script>

      <section className="grid gap-10 rounded-3xl bg-white/5 p-10 shadow-xl shadow-emerald-500/5 ring-1 ring-white/10 backdrop-blur-md md:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-emerald-300">
            {home('hero.eyebrow')}
          </p>
          <h1 className="text-4xl font-bold tracking-tight text-white md:text-6xl">
            {home('hero.title')}
          </h1>
          <p className="text-lg leading-relaxed text-slate-200 md:text-xl">
            {home('hero.subtitle')}
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <CTAButton>{common('cta')}</CTAButton>
            <a
              href={`#workflow`}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-slate-900/60 px-5 py-3 text-sm font-semibold text-white transition hover:border-emerald-300 hover:text-emerald-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-200"
            >
              {home('hero.secondaryCta')}
            </a>
          </div>
        </div>
        <div className="grid gap-4 text-sm md:items-center">
          <div className="rounded-3xl bg-slate-900/70 p-6 shadow-inner shadow-black/60 ring-1 ring-white/10">
            <p className="text-sm font-semibold text-emerald-300">{common('tagline')}</p>
            <p className="mt-3 text-sm text-slate-300">
              {common('description')}
            </p>
            <dl className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
              {stats.map((item) => (
                <div key={item.label} className="rounded-2xl bg-slate-950/60 p-4 text-center shadow shadow-black/40">
                  <dt className="text-xs uppercase tracking-wide text-slate-500">{item.label}</dt>
                  <dd className="mt-2 text-2xl font-semibold text-white">{item.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </section>

      <section className="space-y-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-3xl font-semibold text-white md:text-4xl">{home('featureHighlights.title')}</h2>
            <p className="mt-2 max-w-2xl text-base text-slate-300">
              {common('description')}
            </p>
          </div>
        </div>
        <div className="grid gap-6 md:grid-cols-3">
          {cards.map((card) => (
            <article
              key={card.title}
              className="group relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/60 p-6 shadow-lg shadow-emerald-500/10 transition hover:-translate-y-1 hover:border-emerald-300"
            >
              <span className="inline-flex rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-emerald-300">
                {card.badge}
              </span>
              <h3 className="mt-4 text-xl font-semibold text-white">{card.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-slate-300">{card.description}</p>
              <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-emerald-400/10 blur-2xl" aria-hidden />
            </article>
          ))}
        </div>
      </section>

      <section id="workflow" className="rounded-3xl border border-white/5 bg-slate-950/70 p-10 shadow-lg shadow-black/40">
        <h2 className="text-3xl font-semibold text-white md:text-4xl">{home('workflow.title')}</h2>
        <ol className="mt-8 grid gap-6 md:grid-cols-3">
          {steps.map((step) => (
            <li
              key={step.title}
              className="rounded-3xl bg-slate-900/70 p-6 text-sm leading-relaxed text-slate-300 shadow-inner shadow-black/40 ring-1 ring-white/10"
            >
              <span className="text-3xl" aria-hidden>
                {step.icon}
              </span>
              <p className="mt-4 text-lg font-semibold text-white">{step.title}</p>
              <p className="mt-2 text-sm text-slate-300">{step.description}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="rounded-3xl border border-emerald-400/30 bg-emerald-400/10 p-8 text-center shadow-lg shadow-emerald-500/20">
        <blockquote className="text-lg font-medium text-white md:text-xl">“{home('testimonial.quote')}”</blockquote>
        <p className="mt-4 text-sm text-emerald-100">— {home('testimonial.attribution')}</p>
      </section>
    </div>
  );
}
