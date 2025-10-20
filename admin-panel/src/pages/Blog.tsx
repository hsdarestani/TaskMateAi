import { FormEvent, useEffect, useMemo, useState } from 'react';

import Badge from '../components/Badge';
import DataTable from '../components/DataTable';
import PageHeader from '../components/PageHeader';
import api from '../lib/api';

interface BlogPost extends Record<string, unknown> {
  id: string;
  title: string;
  slug: string;
  author: string;
  locale: 'en' | 'fa' | 'ar';
  published: boolean;
  updatedAt: string;
}

const fallbackPosts: BlogPost[] = [
  {
    id: 'post-en-1',
    title: 'Scaling Telegram productivity with TaskMate',
    slug: 'scaling-telegram-productivity',
    author: 'Team TaskMate',
    locale: 'en',
    published: true,
    updatedAt: '2024-07-03T14:00:00Z'
  },
  {
    id: 'post-fa-1',
    title: 'بهینه‌سازی مدیریت تیم‌ها با تاسک‌میت',
    slug: 'optimize-team-management',
    author: 'تیم تاسک‌میت',
    locale: 'fa',
    published: false,
    updatedAt: '2024-07-04T10:20:00Z'
  }
];

const locales = [
  { code: 'en', label: 'English' },
  { code: 'fa', label: 'Farsi' },
  { code: 'ar', label: 'Arabic' }
] as const;

type LocaleCode = (typeof locales)[number]['code'];

export default function BlogPage() {
  const [posts, setPosts] = useState<BlogPost[]>(fallbackPosts);
  const [selectedLocale, setSelectedLocale] = useState<LocaleCode>('en');
  const [draft, setDraft] = useState({ title: '', slug: '', content: '', locale: 'en' as LocaleCode, published: false });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    const fetchPosts = async () => {
      try {
        const { data } = await api.get<{ results: BlogPost[] }>('/api/admin/blog');
        if (ignore) return;
        if (Array.isArray(data.results)) {
          setPosts(data.results);
        }
      } catch (err) {
        if (import.meta.env.DEV) {
          console.info('Using fallback blog posts', err);
        }
      }
    };
    fetchPosts();
    return () => {
      ignore = true;
    };
  }, []);

  const filtered = useMemo(() => posts.filter((post) => post.locale === selectedLocale), [posts, selectedLocale]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const payload = { ...draft };
      const { data } = await api.post<BlogPost>('/api/admin/blog', payload);
      setPosts((prev) => [data, ...prev.filter((post) => post.id !== data.id)]);
      setDraft({ title: '', slug: '', content: '', locale: selectedLocale, published: false });
      setMessage('Post saved successfully.');
    } catch (err) {
      if (import.meta.env.DEV) {
        console.info('Simulating blog save in dev', err);
        const simulated: BlogPost = {
          id: `draft-${Date.now()}`,
          title: draft.title,
          slug: draft.slug,
          author: 'You',
          locale: draft.locale,
          published: draft.published,
          updatedAt: new Date().toISOString()
        };
        setPosts((prev) => [simulated, ...prev]);
        setDraft({ title: '', slug: '', content: '', locale: selectedLocale, published: false });
        setMessage('Post saved (development mock).');
      } else {
        setMessage('Failed to save post.');
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Blog CMS"
        subtitle="Draft, localize, and publish updates for every TaskMate audience."
        actions={<Badge tone="info">Supports fa / en / ar</Badge>}
      />
      <div className="grid gap-6 xl:grid-cols-2">
        <section className="space-y-4 rounded-3xl border border-white/5 bg-slate-900/40 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-lg font-semibold text-white">Posts</h3>
            <div className="flex gap-2 rounded-2xl border border-white/10 bg-slate-950/60 p-1">
              {locales.map((locale) => (
                <button
                  key={locale.code}
                  onClick={() => setSelectedLocale(locale.code)}
                  className={`rounded-2xl px-4 py-2 text-xs font-semibold transition ${
                    selectedLocale === locale.code ? 'bg-emerald-500 text-slate-950' : 'text-slate-300 hover:bg-white/5'
                  }`}
                >
                  {locale.label}
                </button>
              ))}
            </div>
          </div>
          <DataTable<BlogPost>
            columns={[
              { key: 'title', label: 'Title' },
              { key: 'slug', label: 'Slug' },
              { key: 'author', label: 'Author' },
              {
                key: 'published',
                label: 'Status',
                render: (post) => <Badge tone={post.published ? 'success' : 'warning'}>{post.published ? 'Published' : 'Draft'}</Badge>
              },
              {
                key: 'updatedAt',
                label: 'Updated',
                render: (post) => <span className="text-sm text-slate-300">{new Date(post.updatedAt).toLocaleString()}</span>
              }
            ]}
            data={filtered}
            emptyLabel="No posts for this locale"
          />
        </section>
        <section className="space-y-4 rounded-3xl border border-white/5 bg-slate-900/40 p-6">
          <div className="space-y-1">
            <h3 className="text-lg font-semibold text-white">Create / update post</h3>
            <p className="text-sm text-slate-400">Preview changes across locales before publishing.</p>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <label className="flex flex-col gap-2 text-xs uppercase tracking-wide text-slate-400">
              <span>Locale</span>
              <select
                value={draft.locale}
                onChange={(event) => setDraft((prev) => ({ ...prev, locale: event.target.value as LocaleCode }))}
                className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-emerald-400 focus:outline-none"
              >
                {locales.map((locale) => (
                  <option key={locale.code} value={locale.code}>
                    {locale.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-2 text-xs uppercase tracking-wide text-slate-400">
              <span>Title</span>
              <input
                value={draft.title}
                onChange={(event) => setDraft((prev) => ({ ...prev, title: event.target.value }))}
                className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-emerald-400 focus:outline-none"
                required
              />
            </label>
            <label className="flex flex-col gap-2 text-xs uppercase tracking-wide text-slate-400">
              <span>Slug</span>
              <input
                value={draft.slug}
                onChange={(event) => setDraft((prev) => ({ ...prev, slug: event.target.value }))}
                className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-emerald-400 focus:outline-none"
                required
              />
            </label>
            <label className="flex flex-col gap-2 text-xs uppercase tracking-wide text-slate-400">
              <span>Markdown</span>
              <textarea
                value={draft.content}
                onChange={(event) => setDraft((prev) => ({ ...prev, content: event.target.value }))}
                className="h-40 rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white focus:border-emerald-400 focus:outline-none"
                placeholder="# Headline"
              />
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={draft.published}
                onChange={(event) => setDraft((prev) => ({ ...prev, published: event.target.checked }))}
                className="h-4 w-4 rounded border border-white/20 bg-slate-900"
              />
              Publish immediately
            </label>
            {message && <p className="rounded-2xl bg-emerald-500/10 px-4 py-2 text-xs text-emerald-200">{message}</p>}
            <button
              type="submit"
              disabled={saving}
              className="w-full rounded-2xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? 'Saving…' : 'Save post'}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
