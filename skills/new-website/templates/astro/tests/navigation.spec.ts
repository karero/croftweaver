import { test, expect } from '@playwright/test';
import { PAGES } from './_helpers';
import { SITE } from '../src/config';

// Every route in PAGES returns 200, and every internal link on it resolves to a
// 200 with no redirect hop (clean URLs only). Links written as absolute production
// URLs (https://site.tld/about) are internal too — they get the same check.
// Catches dead links and renamed pages before users do.
for (const path of PAGES) {
  test(`navigation — ${path} loads and its internal links resolve`, async ({ page, request, baseURL }) => {
    const res = await page.goto(path);
    expect(res?.status(), `${path} should return 200`).toBe(200);

    const hrefs = await page.locator('a[href]').evaluateAll((as) =>
      as.map((a) => (a as HTMLAnchorElement).getAttribute('href') ?? ''));
    // Absolute URLs on the production host count as internal — including the
    // www./apex variant of it (a www link on an apex-canonical site is almost
    // always a mistake; checking it beats silently skipping it).
    const stripWww = (host: string) => host.replace(/^www\./, '');
    const siteHost = stripWww(new URL(SITE.url).hostname);
    const internal = [...new Set(hrefs)]
      .map((h) => {
        if (!/^https?:\/\//i.test(h)) return h;
        try {
          const u = new URL(h);
          if (stripWww(u.hostname.toLowerCase()) === siteHost) return u.pathname + u.search + u.hash;
        } catch { /* malformed absolute URL — leave it; the filter drops it */ }
        return h;
      })
      .filter((h) => h.startsWith('/') && !h.startsWith('//') && !h.startsWith('/#'));

    for (const href of internal) {
      const url = new URL(href, baseURL).href;
      const r = await request.get(url, { maxRedirects: 0 });
      expect([200, 304], `internal link ${href} returned ${r.status()} (expected 200, no redirect hop)`).toContain(r.status());
    }
  });
}
