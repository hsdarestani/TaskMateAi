import { getRequestConfig } from 'next-intl/server';

export default getRequestConfig(async ({ locale }) => ({
  locale,
  messages: (await import(`../../i18n/${locale}.json`)).default
}));
