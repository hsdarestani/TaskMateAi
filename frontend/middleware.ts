import createMiddleware from 'next-intl/middleware';

export default createMiddleware({
  locales: ['en', 'fa', 'ar'],
  defaultLocale: 'en'
});

export const config = {
  matcher: ['/', '/(fa|ar|en)/:path*']
};
