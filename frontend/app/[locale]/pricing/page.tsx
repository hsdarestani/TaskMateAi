import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';

import { CTAButton } from '../components/CTAButton';

type PageProps = {
  params: { locale: string };
};

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const pricing = await getTranslations({ locale: params.locale, namespace: 'pricingPage' });
  return {
    title: `${pricing('title')} · TaskMate AI`,
    description: pricing('subtitle')
  };
}

export default async function PricingPage({ params }: PageProps) {
  const locale = params.locale;
  const pricing = await getTranslations({ locale, namespace: 'pricingPage' });
  const common = await getTranslations({ locale, namespace: 'common' });

  const plans = pricing.raw('plans') as Array<{
    name: string;
    price: string;
    period: string;
    features: string[];
  }>;

  return (
    <div className="space-y-12">
      <header className="space-y-4 text-center">
        <h1 className="text-4xl font-semibold text-white md:text-5xl">{pricing('title')}</h1>
        <p className="mx-auto max-w-3xl text-lg text-slate-300">{pricing('subtitle')}</p>
      </header>

      <div className="grid gap-6 md:grid-cols-3">
        {plans.map((plan) => (
          <article
            key={plan.name}
            className="flex h-full flex-col rounded-3xl border border-white/10 bg-slate-950/70 p-8 shadow-lg shadow-black/40"
          >
            <header className="space-y-2">
              <h2 className="text-2xl font-semibold text-white">{plan.name}</h2>
              <div className="text-3xl font-bold text-emerald-300">{plan.price}</div>
              <p className="text-sm text-slate-400">{plan.period}</p>
            </header>
            <ul className="mt-6 space-y-3 text-sm text-slate-200">
              {plan.features.map((feature) => (
                <li key={feature} className="flex items-start gap-3">
                  <span aria-hidden className="mt-1 text-emerald-300">
                    ✓
                  </span>
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
            <CTAButton size="md" className="mt-auto w-full justify-center">
              {common('cta')}
            </CTAButton>
          </article>
        ))}
      </div>

      <p className="text-center text-sm text-slate-400">{pricing('finePrint')}</p>
    </div>
  );
}
