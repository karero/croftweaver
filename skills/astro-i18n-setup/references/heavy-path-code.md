# Heavy-path code — the verbatim file edits

The exact code for SKILL.md's "What it changes" §1–§3. Read the matching
SKILL.md section first for what each edit does and the rules around it; apply
the code from here.

## §1. `astro.config.mjs` — i18n routing + sitemap alternates

```js
export default defineConfig({
  site: 'https://example.com',
  trailingSlash: 'never',
  build: { format: 'file', inlineStylesheets: 'always' },
  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'de'],                 // ← the launch locales
    routing: { prefixDefaultLocale: false },
  },
  integrations: [
    // The i18n map makes @astrojs/sitemap emit <xhtml:link> hreflang alternates.
    sitemap({
      i18n: { defaultLocale: 'en', locales: { en: 'en', de: 'de' } },
      changefreq: 'monthly',
      priority: 0.7,
      // Sparse routes (ROUTES entries with an explicit `locales` list — see §2 and
      // "Partial translation" in SKILL.md): the i18n map above emits alternates for
      // EVERY locale on EVERY page; it knows nothing about ROUTES. Filter each entry's
      // alternates to the locales the route actually exists in — a sitemap that
      // advertises a never-built variant contradicts the head hreflang set
      // (international-seo.md: head and sitemap must not disagree).
      serialize(item) {
        const path = decodeURI(new URL(item.url).pathname).replace(/\.html$/, '').replace(/\/$/, '') || '/';
        const locs = routeLocales(neutralPath(path));
        if (item.links && locs.length < LOCALES.length) {
          item.links = item.links.filter((l) =>
            l.lang === 'x-default' ? locs.includes(DEFAULT_LOCALE) : locs.includes(l.lang),
          );
          // A cluster of one says nothing — drop it (deliberate mild asymmetry
          // with the head, which keeps the self + x-default pair; absence in one
          // channel is fine, contradiction between channels is not).
          if (item.links.length < 2) delete item.links;
        }
        return item;
      },
    }),
  ],
});
```

The `serialize` hook imports the shared registry from `src/config.ts` (Vite loads the
Astro config, so the TS import works):

```js
import { LOCALES, DEFAULT_LOCALE, neutralPath, routeLocales } from './src/config';
```

## §2. `src/config.ts` — replace the single locale, add the route registry

```ts
// was: locale: 'en'  inside SITE
export const LOCALES = ['en', 'de'] as const;        // keep in sync with astro.config i18n.locales
export const DEFAULT_LOCALE = 'en';
export const LOCALE_LABELS: Record<string, string> = { en: 'English', de: 'Deutsch' };

// Per-route locale membership — THE single registry that Base.astro (head
// hreflang), astro.config.mjs (sitemap alternates) and the tests all read, so
// they can't drift apart. A route with NO `locales` field exists in every
// LOCALES entry (the fully-translated default: nothing changes for such sites).
// Give a route an explicit `locales` list ONLY when it is NOT fully translated —
// see "Partial translation" in SKILL.md.
export type RouteSpec = { path: string; locales?: readonly string[] };
export const ROUTES: readonly RouteSpec[] = [
  { path: '/' },
  { path: '/privacy' },
  // { path: '/blog/some-post', locales: ['de'] },   // German-only page, no EN twin
];

// Fail loud at import time on registry typos — a duplicate path yields duplicate
// PAGES entries (cryptic Playwright collection errors), an unknown or repeated
// locale yields duplicate/orphan hreflang links the specs then EXPECT.
for (const r of ROUTES) {
  if (ROUTES.filter((x) => x.path === r.path).length > 1) throw new Error(`ROUTES: duplicate path ${r.path}`);
  for (const l of r.locales ?? []) {
    if (!(LOCALES as readonly string[]).includes(l)) throw new Error(`ROUTES: ${r.path} lists unknown locale "${l}"`);
  }
  if (new Set(r.locales ?? []).size !== (r.locales ?? []).length) throw new Error(`ROUTES: ${r.path} lists a locale twice`);
}

// The locale a (possibly prefixed) path belongs to: the prefix segment if it is
// a non-default locale, else the default locale (clean-default routing).
export function pathLocale(path: string): string {
  return (
    LOCALES.find((l) => l !== DEFAULT_LOCALE && (path === `/${l}` || path.startsWith(`/${l}/`))) ??
    DEFAULT_LOCALE
  );
}

// Strip a non-default locale prefix: neutralPath('/de/privacy') === '/privacy'.
export function neutralPath(path: string, locale: string = pathLocale(path)): string {
  if (locale === DEFAULT_LOCALE) return path;
  const stripped = path.replace(new RegExp(`^/${locale}(?=/|$)`), '');
  return stripped === '' ? '/' : stripped;
}

// The locales a neutral path exists in — every LOCALES entry unless ROUTES
// narrows it. Paths absent from ROUTES get the all-locales default, so an
// unregistered page behaves exactly like a fully-translated one.
export function routeLocales(neutral: string): readonly string[] {
  return ROUTES.find((r) => r.path === neutral)?.locales ?? LOCALES;
}
```

## §3. `src/layouts/Base.astro` — locale-aware (VERIFIED build output)

```astro
---
import { getRelativeLocaleUrl } from 'astro:i18n';
import { SITE, DEFAULT_LOCALE, routeLocales /* … */ } from '../config';
// … existing title/description/image props …

const site = Astro.site ?? new URL(SITE.url);
// clean URL: drop index.html + .html, strip trailing slash except root
let cleanPath = Astro.url.pathname.replace(/\/index\.html$/, '/').replace(/\.html$/, '');
if (cleanPath !== '/' && cleanPath.endsWith('/')) cleanPath = cleanPath.slice(0, -1);
const canonical = new URL(cleanPath, site).href;

const currentLocale = Astro.currentLocale ?? DEFAULT_LOCALE;
// Replaces the starter's `Astro.locals.lang = lang;`: components inside the page
// (the contact form) speak the page's language.
Astro.locals.lang = currentLocale;
let neutral = cleanPath;
if (currentLocale !== DEFAULT_LOCALE) {
  neutral = cleanPath.replace(new RegExp('^/' + currentLocale + '(?=/|$)'), '');
}
if (neutral === '') neutral = '/';
// getRelativeLocaleUrl() expects a bare path segment (or none for the locale root) — NOT a
// leading-slash path — or it can drift the trailing slash under trailingSlash: 'never'.
const localePath = neutral === '/' ? undefined : neutral.replace(/^\//, '');
// Sparse-aware: only the locales this ROUTE exists in (routeLocales, §2) get an
// alternate — not every LOCALES entry. Fully-translated routes are unaffected.
// Named i18nAlternates because the template already has an `alternates` PROP
// (the twin-pages light path) in this scope — SKILL.md §3's light-path note
// says what to delete.
const pageLocales = routeLocales(neutral);
const i18nAlternates = pageLocales.map((loc) => ({ loc, href: new URL(getRelativeLocaleUrl(loc, localePath), site).href }));
// x-default → the default-locale variant; a route with NO default-locale variant
// falls back to the route's FIRST listed locale — deterministic, so every variant
// of the route advertises the SAME x-default (per-variant self-reference would
// give conflicting cluster annotations on 3+-locale sites).
const xDefault = new URL(
  getRelativeLocaleUrl(pageLocales.includes(DEFAULT_LOCALE) ? DEFAULT_LOCALE : pageLocales[0], localePath),
  site,
).href;
---
<html lang={currentLocale}>
  <head>
    …
    <link rel="canonical" href={canonical} />
    {i18nAlternates.map((a) => <link rel="alternate" hreflang={a.loc} href={a.href} />)}
    <link rel="alternate" hreflang="x-default" href={xDefault} />
    …
  </head>
```
