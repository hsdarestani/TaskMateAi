import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';
import { marked } from 'marked';

import { CTAButton } from '../components/CTAButton';

type PageProps = {
  params: { locale: string };
};

type BlogPost = {
  id: number;
  slug: string;
  title: string;
  content_markdown: string;
  author?: string;
  created_at?: string;
};

async function fetchPosts(locale: string): Promise<BlogPost[]> {
  const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.APP_BASE_URL ?? 'http://localhost:8000';
  try {
    const response = await fetch(`${baseUrl}/api/blog?lang=${locale}`, {
      cache: 'no-store',
      headers: { 'Accept': 'application/json' }
    });
    if (!response.ok) {
      throw new Error('Failed to load blog posts');
    }
    const payload = await response.json();
    if (Array.isArray(payload)) {
      return payload as BlogPost[];
    }
    return (payload.items ?? []) as BlogPost[];
  } catch (error) {
    console.error(error);
    return [];
  }
}

function toExcerpt(markdown: string, limit = 180) {
  const plain = markdown
    .replace(/[#*_`>\-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  return plain.length > limit ? `${plain.slice(0, limit)}…` : plain;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const blog = await getTranslations({ locale: params.locale, namespace: 'blogPage' });
  return {
    title: `${blog('title')} · TaskMate AI`,
    description: blog('description')
  };
}

export default async function BlogPage({ params }: PageProps) {
  const locale = params.locale;
  const blog = await getTranslations({ locale, namespace: 'blogPage' });
  const common = await getTranslations({ locale, namespace: 'common' });
  const posts = await fetchPosts(locale);

  return (
    <div className="space-y-12">
      <header className="space-y-4 text-center">
        <h1 className="text-4xl font-semibold text-white md:text-5xl">{blog('title')}</h1>
        <p className="mx-auto max-w-3xl text-lg text-slate-300">{blog('description')}</p>
        <CTAButton size="md" className="mx-auto w-fit">
          {common('cta')}
        </CTAButton>
      </header>

      {posts.length === 0 ? (
        <p className="rounded-3xl border border-white/10 bg-slate-900/70 p-8 text-center text-sm text-slate-300">
          {blog('empty')}
        </p>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {posts.map((post) => {
            const html = marked.parse(post.content_markdown ?? '');
            const created = post.created_at ? new Date(post.created_at) : undefined;
            return (
              <article
                key={post.id ?? post.slug}
                className="flex h-full flex-col rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-lg shadow-black/40"
              >
                <header className="space-y-2">
                  <p className="text-xs uppercase tracking-wide text-emerald-300">
                    {created ? created.toLocaleDateString(locale) : '—'}
                  </p>
                  <h2 className="text-2xl font-semibold text-white">{post.title}</h2>
                  {post.author ? (
                    <p className="text-xs text-slate-500">{post.author}</p>
                  ) : null}
                </header>
                <p className="mt-4 text-sm text-slate-300">{toExcerpt(post.content_markdown ?? '')}</p>
                <details className="group mt-4 rounded-2xl bg-slate-900/60 p-4 text-sm text-slate-200">
                  <summary className="cursor-pointer list-none font-semibold text-emerald-300">
                    {blog('readMore')}
                  </summary>
                  <div
                    className="mt-3 space-y-4 leading-relaxed"
                    dangerouslySetInnerHTML={{ __html: html }}
                  />
                </details>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
