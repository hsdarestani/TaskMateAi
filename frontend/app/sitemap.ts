import type { MetadataRoute } from 'next';

const locales = ['en', 'fa', 'ar'] as const;
const routes = ['', 'features', 'pricing', 'guide', 'blog', 'terms', 'privacy', 'contact', 'enterprise'];

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://taskmate.ai';
  const lastModified = new Date();

  return routes.flatMap((route) => {
    const basePath = route ? `/${route}` : '';
    const languages: Record<string, string> = {};
    locales.forEach((locale) => {
      languages[locale] = `${baseUrl}/${locale}${basePath}`;
    });

    return locales.map((locale) => ({
      url: `${baseUrl}/${locale}${basePath}`,
      lastModified,
      alternates: {
        languages
      }
    }));
  });
}
