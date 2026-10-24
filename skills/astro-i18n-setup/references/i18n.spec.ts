import { test, expect } from '@playwright/test';
import { PAGES, germanFunctionWordDensity } from './_helpers';
import { SITE, LOCALES, DEFAULT_LOCALE, pathLocale, neutralPath, routeLocales } from '../src/config';

// hreflang contract for a multi-locale site (the gap seo.spec.ts does NOT cover).
// Drop this file into tests/ when astro-i18n-setup runs. Hermetic: it navigates the
// preview server only (no external network), reads the <head>, and checks the
// cross-locale invariants Google actually enforces — see
// seo-audit/references/international-seo.md for the WHY behind each.
//
// SPARSE ROUTES: a route does not have to exist in every locale. `ROUTES` in
// src/config.ts is the single registry — a route with an explicit `locales` list
// exists only in those locales (a German-only blog post on a DE+EN site), and this
// spec derives every per-page expectation from that registry via routeLocales().
// Base.astro and astro.config.mjs (sitemap serialize) read the SAME registry, so
// head, sitemap and tests cannot drift apart.
//
// Invariants asserted:
//   • completeness — every page lists ONE alternate per locale THE ROUTE EXISTS IN
//                    (routeLocales), plus exactly one x-default
//   • absolute     — every alternate href is the production URL (SITE.url + path)
//   • self-canonical — the page's <link rel=canonical> equals its OWN-locale alternate
//   • x-default    — points at the default-locale variant; a route with NO
//                    default-locale variant uses its first listed locale instead
//                    (deterministic — the same x-default on every variant)
//   • reciprocity  — if page A (locale x) links B as its locale-y alternate, then B
//                    links A back as its locale-x alternate (the #1 hreflang mistake)

// URL for a route, matching Base.astro's canonical/alternate output: root keeps its
// trailing slash, every other path has none (trailingSlash:'never').
// encodeURI: a non-ASCII route (/über-uns) reaches the DOM percent-encoded, so
// build the comparison URL the same way (ASCII slugs remain the house rule).
const urlFor = (path: string) => encodeURI(path === '/' ? `${SITE.url}/` : `${SITE.url}${path}`);

// The locale a route belongs to — shared helper from src/config.ts (the prefix
// segment if it is a non-default locale, else the default locale).
const localeOf = pathLocale;

// Per-page expected hreflang codes: the locales this page's ROUTE exists in, plus
// x-default (Base.astro always emits one — self-referencing on sparse routes with
// no default-locale variant).
const expectedCodesFor = (path: string) => {
  const locs = routeLocales(neutralPath(path, localeOf(path)));
  return [...locs, 'x-default'].sort();
};

test.describe('i18n — hreflang contract', () => {
  // Single-locale sites have no hreflang to check (astro-i18n-setup only runs for 2+).
  test.skip(LOCALES.length < 2, 'single-locale site — no hreflang contract');

  test('hreflang set is complete, absolute, self-canonical, and reciprocal', async ({ page }) => {
    type Alt = { hreflang: string; href: string };
    const seen = new Map<string, { alts: Alt[]; canonical: string | null; url: string }>();

    for (const path of PAGES) {
      await page.goto(path);
      const alts: Alt[] = await page.$$eval('link[rel="alternate"][hreflang]', (els) =>
        els.map((e) => ({ hreflang: e.getAttribute('hreflang') || '', href: e.getAttribute('href') || '' })),
      );
      const canonical = await page.locator('link[rel="canonical"]').getAttribute('href');
      seen.set(path, { alts, canonical, url: urlFor(path) });
    }

    // Per-page: completeness + absolute hrefs + self-canonical + correct x-default.
    for (const [path, { alts, canonical }] of seen) {
      expect(
        alts.map((a) => a.hreflang).sort(),
        `${path}: hreflang set must be every locale the route exists in (ROUTES/routeLocales) + x-default`,
      ).toEqual(expectedCodesFor(path));

      for (const a of alts) {
        // SITE.url + '/' (not bare SITE.url) so a lookalike origin or a slash-less
        // join like "https://example.comabout" can't sneak through.
        expect(a.href.startsWith(SITE.url + '/'), `${path}: alternate "${a.hreflang}" href must be the absolute production URL (${a.href})`).toBe(true);
      }

      const selfLocale = localeOf(path);
      const selfAlt = alts.find((a) => a.hreflang === selfLocale);
      expect(canonical, `${path}: canonical must equal its own-locale alternate`).toBe(selfAlt?.href);

      // x-default → the default-locale variant. A sparse route with NO default-locale
      // variant can't do that (the page doesn't exist) — Base.astro deterministically
      // falls back to the route's FIRST listed locale, so every variant of the route
      // advertises the SAME x-default (not a per-variant self-reference, which would
      // give conflicting cluster annotations on 3+-locale sites).
      const routeLocs = routeLocales(neutralPath(path, selfLocale));
      const xdLocale = routeLocs.includes(DEFAULT_LOCALE) ? DEFAULT_LOCALE : routeLocs[0];
      const xDefault = alts.find((a) => a.hreflang === 'x-default');
      const xdAlt = alts.find((a) => a.hreflang === xdLocale);
      expect(
        xDefault?.href,
        `${path}: x-default must point at the default-locale variant (or the route's first listed locale when it has no default-locale variant)`,
      ).toBe(xdAlt?.href);
    }

    // Cross-page: reciprocity. For each alternate that targets a page we know,
    // that page must link back to this one under this page's locale.
    const urlToPath = new Map([...seen].map(([p, v]) => [v.url, p]));
    for (const [path, { alts, url }] of seen) {
      const selfLocale = localeOf(path);
      for (const a of alts) {
        if (a.hreflang === 'x-default') continue;
        const target = urlToPath.get(a.href);
        // Every locale alternate must resolve to a page in PAGES — otherwise that
        // locale's pages were never built/listed and its reciprocity goes unchecked
        // (the exact "A links B, B never links back" mistake this file exists to catch).
        // Sparse routes emit alternates only for routeLocales(), so a correctly
        // narrowed route never trips this on its missing locales.
        expect(target, `${path}: alternate "${a.hreflang}" → ${a.href} has no matching page in PAGES — build + list every locale's routes (or narrow the route's \`locales\` in ROUTES)`).toBeDefined();
        const back = seen.get(target!)!.alts.find((x) => x.hreflang === selfLocale);
        expect(back?.href, `${target} must link back to ${path} under hreflang="${selfLocale}"`).toBe(url);
      }
    }
  });

  test('every multi-locale page carries a language switcher matching its real locale siblings', async ({ page }) => {
    for (const path of PAGES) {
      const selfLocale = localeOf(path);
      const neutral = neutralPath(path, selfLocale);
      const locs = routeLocales(neutral);
      if (locs.length < 2) continue; // sparse single-locale route: no switcher required
      await page.goto(path);
      // Per-switcher: header + footer switchers are both legitimate — each must
      // be complete on its own. Classify by aria-current PRESENCE (a self-link
      // variant using aria-current="page" is as valid as the span pattern).
      const switchers = await page.$$eval('nav.lang-switcher', (navs) =>
        navs.map((nav) =>
          [...nav.querySelectorAll('a[hreflang], [aria-current]')].map((e) => ({
            code: e.hasAttribute('aria-current') ? '(current)' : e.getAttribute('hreflang'),
            href: e.getAttribute('href'),
          })),
        ),
      );
      expect(
        switchers.length,
        `${path}: no language switcher found — copy references/LanguageSwitcher.astro into the nav (SKILL.md §4); ` +
          `hreflang <link> tags only talk to crawlers, visitors need a visible way to switch`,
      ).toBeGreaterThan(0);
      for (const entries of switchers) {
        const offered = entries.filter((e) => e.code !== '(current)');
        const expectedCodes = locs.filter((l) => l !== selfLocale).sort();
        expect(
          offered.map((e) => e.code).sort(),
          `${path}: each switcher must offer exactly the route's OTHER locales (routeLocales minus self)`,
        ).toEqual(expectedCodes);
        // hreflang alone can lie about the target: assert each link points at
        // THIS route's sibling, not e.g. the locale's home page.
        for (const e of offered) {
          const expectedPath =
            e.code === DEFAULT_LOCALE ? neutral : neutral === '/' ? `/${e.code}` : `/${e.code}${neutral}`;
          expect(
            decodeURI(new URL(e.href ?? '', 'https://x.invalid').pathname).replace(/\/$/, '') || '/',
            `${path}: switcher link "${e.code}" must target this page's sibling (${expectedPath}), not another route`,
          ).toBe(expectedPath);
        }
      }
    }
  });

  test('sitemap <xhtml:link> alternates agree with the head hreflang sets', async ({ request, baseURL }) => {
    // Replaces the SKILL.md "manual grep of dist/sitemap-0.xml" instruction with
    // a real check: for each sitemap entry carrying alternates, the linked
    // locale set must match the route's routeLocales() (the serialize hook's
    // contract) — head/sitemap hreflang disagreement makes Google drop the
    // cluster (international-seo.md).
    const res = await request.get(new URL('/sitemap-0.xml', baseURL!).href);
    expect(res.status(), 'sitemap-0.xml should exist').toBe(200);
    const xml = await res.text();
    let checked = 0;
    for (const entry of xml.matchAll(/<url>([\s\S]*?)<\/url>/g)) {
      const loc = entry[1].match(/<loc>([^<]+)<\/loc>/)?.[1];
      if (!loc) continue;
      const path = decodeURI(new URL(loc).pathname).replace(/\/$/, '') || '/';
      const langs = [...entry[1].matchAll(/hreflang="([^"]+)"/g)].map((m) => m[1]).filter((l) => l !== 'x-default').sort();
      if (!langs.length) continue; // singleton clusters are dropped by the serialize hook (documented)
      checked++;
      const expected = [...routeLocales(neutralPath(path, localeOf(path)))].sort();
      expect(
        langs,
        `${loc}: sitemap alternates must match the route's locales (serialize hook contract)`,
      ).toEqual(expected);
    }
    // Wholesale-vanished alternates (the i18n map deleted from sitemap()) must
    // not slip through as "every entry skipped": if any route is multi-locale,
    // at least one sitemap entry must carry alternates.
    const anyMultiLocale = PAGES.some((p) => routeLocales(neutralPath(p, localeOf(p))).length > 1);
    if (anyMultiLocale) {
      expect(checked, 'no sitemap entry carries <xhtml:link> alternates — is the i18n map missing from sitemap()?').toBeGreaterThan(0);
    }
  });

  test('translated pages are not thin — body content roughly matches the default-locale original', async ({ page }) => {
    // KNOWN LIMITATION: word-splitting on \s+ assumes a whitespace-delimited language (this
    // suite's documented use case is DE+EN). It does NOT work for scripts without whitespace
    // word boundaries (Japanese, Chinese, Thai, ...) -- a fully-translated page in one of those
    // scripts can come back as a handful of "words" and fail this check even though nothing is
    // actually thin. If you add a non-whitespace-delimited locale, either skip this check for it
    // or switch to Intl.Segmenter(locale, { granularity: 'word' }) instead of split(/\s+/).
    //
    // Reverse lookup: production URL -> PAGES path (mirrors the reciprocity check's urlToPath
    // above), so a page's own default-locale hreflang href can be resolved back to a page we
    // can navigate to and compare against.
    const urlToPath = new Map(PAGES.map((p) => [urlFor(p), p]));

    const countWords = async () =>
      page
        .evaluate(() => document.body.innerText)
        .then((text) => text.trim().split(/\s+/).filter(Boolean).length);

    for (const path of PAGES) {
      if (localeOf(path) === DEFAULT_LOCALE) continue;
      // Sparse route with no default-locale variant: there is no original to
      // compare against — nothing to check (the route IS the only version).
      if (!routeLocales(neutralPath(path, localeOf(path))).includes(DEFAULT_LOCALE)) continue;

      await page.goto(path);
      const defaultHref = await page
        .locator(`link[rel="alternate"][hreflang="${DEFAULT_LOCALE}"]`)
        .getAttribute('href');
      const originalPath = defaultHref ? urlToPath.get(defaultHref) : undefined;
      expect(
        originalPath,
        `${path}: default-locale ("${DEFAULT_LOCALE}") alternate href "${defaultHref}" has no matching page in PAGES`,
      ).toBeDefined();

      const translatedWords = await countWords();

      await page.goto(originalPath!);
      const originalWords = await countWords();

      // An empty original isn't a valid baseline — fail loud rather than let ratio=1
      // silently wave the translation through (that would hide a broken original page,
      // not just a thin translation of a real one).
      expect(
        originalWords,
        `${originalPath} (the default-locale original for ${path}) has 0 words — fix the original ` +
          `page before this check can validate its translation`,
      ).toBeGreaterThan(0);
      const ratio = translatedWords / originalWords;

      expect(
        ratio,
        `${path} (${translatedWords} words) looks like a STUB/THIN translation of its default-locale ` +
          `original ${originalPath} (${originalWords} words) — only ${(ratio * 100).toFixed(0)}% as much ` +
          `content. This catches a dramatically shorter body (a placeholder page); it can NOT tell a ` +
          `same-length body that's still in the wrong language — see the German-specific check below for ` +
          `that failure mode. Google's own guidance: "Translating only the boilerplate text of your pages ` +
          `while keeping the bulk of your content in a single language...can create a bad user experience" ` +
          `(seo-audit/references/international-seo.md, "Partial Translation").`,
      ).toBeGreaterThanOrEqual(0.4);
    }
  });

  test('German-locale pages actually read as German, not the original language left in place', async ({ page }) => {
    // The word-count check above only catches a STUB/THIN translation. It can NOT catch the
    // sibling failure mode Google's guidance also warns about: nav/footer got translated, but
    // the body itself was left in the original (single) language -- same word count either
    // way, so the ratio check passes clean while the page reads as e.g. English under a German
    // <html lang>. Word count can't distinguish "German body" from "English body under a German
    // nav", so check for a minimum density of common German function words instead -- real
    // German prose runs at roughly 15-20% (verified against a real shipped page); an English
    // (or any non-German) body scores ~0%, since these exact words essentially don't occur in
    // other languages. This heuristic is deliberately German-specific -- it does not generalize
    // to whatever other locale LOCALES might contain, so it only runs for pages whose PRIMARY
    // language subtag is 'de' -- matched on the primary subtag (not exact-equality against the
    // literal string 'de'), so 'de-DE'/'de-AT'/'de-CH' are covered too, not silently skipped.
    //
    // Scope: nav/header/footer are stripped before counting. Chrome legitimately CONTAINS German
    // function words once translated (e.g. a German legal footer: "Alle Rechte vorbehalten..."),
    // and on a short page that chrome can be a large enough fraction of the total text to push
    // whole-body density above the threshold even when the actual body content is still 100%
    // untranslated -- verified empirically: a realistic German footer (~40 words of real prose)
    // plus a fully-English ~30-word body scores ~19% density on document.body (a false pass),
    // vs. 0% once nav/header/footer are excluded first.
    // Word list + density math live in _helpers.germanFunctionWordDensity —
    // ONE implementation shared with tone.spec.ts (which covers single-locale
    // German sites), so the two enforcement points can't drift.
    const MIN_DENSITY = 0.03; // real German prose: ~15-20%; wrong-language body: ~0% -- huge margin

    for (const path of PAGES) {
      if (localeOf(path).toLowerCase().split('-')[0] !== 'de') continue; // no-op unless a 'de'-family locale is configured

      await page.goto(path);
      const text = await page.evaluate(() => {
        const body = document.body.cloneNode(true) as HTMLElement;
        body.querySelectorAll('nav, header, footer, script, style, noscript, blockquote, q, [data-tov-exempt]').forEach((el) => el.remove());
        return body.innerText;
      });
      const words = text.trim().split(/\s+/).filter(Boolean).length;
      const density = germanFunctionWordDensity(text);
      const hits = Math.round(density * words);

      expect(
        density,
        `${path} (lang="de"): body reads as non-German — only ${hits} common German function word(s) ` +
          `in ${words} total words (${(density * 100).toFixed(1)}%, expected >=${MIN_DENSITY * 100}%). The ` +
          `nav/footer may be translated while the body content itself was left in the original language.`,
      ).toBeGreaterThanOrEqual(MIN_DENSITY);
    }
  });
});
