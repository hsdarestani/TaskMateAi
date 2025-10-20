import fs from 'node:fs/promises';
import path from 'node:path';

import type { Metadata } from 'next';
import { marked } from 'marked';
import { getTranslations } from 'next-intl/server';

import { CTAButton } from '../components/CTAButton';

type PageProps = {
  params: { locale: string };
};

async function loadGuide(locale: string) {
  const basePath = path.join(process.cwd(), 'content', 'guide');
  const target = path.join(basePath, `${locale}.md`);
  const filePath = await fs
    .stat(target)
    .then(() => target)
    .catch(() => path.join(basePath, 'en.md'));

  const [raw, stat] = await Promise.all([fs.readFile(filePath, 'utf-8'), fs.stat(filePath)]);

  const html = marked.parse(raw);
  return { html, updatedAt: stat.mtime };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const guide = await getTranslations({ locale: params.locale, namespace: 'guidePage' });
  return {
    title: `${guide('title')} · TaskMate AI`,
    description: guide('description')
  };
}

export default async function GuidePage({ params }: PageProps) {
  const locale = params.locale;
  const guide = await getTranslations({ locale, namespace: 'guidePage' });
  const common = await getTranslations({ locale, namespace: 'common' });
  const { html, updatedAt } = await loadGuide(locale);

  return (
    <div className="space-y-10">
      <header className="space-y-4">
        <h1 className="text-4xl font-semibold text-white md:text-5xl">{guide('title')}</h1>
        <p className="max-w-2xl text-lg text-slate-300">{guide('description')}</p>
        <p className="text-xs uppercase tracking-wide text-slate-500">
          {guide('lastUpdated')}: {updatedAt.toLocaleDateString(locale)}
        </p>
        <CTAButton size="md">{common('cta')}</CTAButton>
      </header>
      <article
        className="prose prose-invert max-w-none prose-headings:text-white prose-strong:text-white prose-a:text-emerald-300"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
