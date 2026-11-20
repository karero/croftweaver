import { test, expect } from '@playwright/test';
import { PAGES } from './_helpers';
import { SITE } from '../src/config';

const stripWww = (host: string) => host.replace(/^www\./, '');

// The path + query an href points at on this site, or null when it is a pure
// "#fragment", a mailto:/tel: link or another host. The www./apex variant of the
// production host counts as internal (a www link on an apex-canonical site is
// almost always a mistake; checking it beats silently skipping it).
function internalTarget(href: string, pageUrl: string, siteHost: string): string | null {
  if (!href || href.startsWith('#')) return null;
  let u: URL;
  try {
    u = new URL(href, pageUrl);
  } catch {
    return null; // malformed URL: not ours to judge here
  }
  if (u.protocol !== 'http:' && u.protocol !== 'https:') return null;
  if (u.origin !== new URL(pageUrl).origin && stripWww(u.hostname.toLowerCase()) !== siteHost) return null;
  return u.pathname + u.search;
}

test('navigation — internalTarget reads page-relative, root-relative and production-host links', () => {
  const at = (h: string) => internalTarget(h, 'http://localhost:4321/team/', 'example.com');
  expect(at('missing')).toBe('/team/missing');
  expect(at('../missing')).toBe('/missing');
  expect(at('/about?x=1#y')).toBe('/about?x=1');
  expect(at('https://www.example.com/about')).toBe('/about');
  expect(at('https://other.org/about')).toBeNull();
  expect(at('//other.org/about')).toBeNull();
  expect(at('#top')).toBeNull();
  expect(at('mailto:a@b.c')).toBeNull();
});

// Every route in PAGES returns 200, and every internal link on it resolves to a
// 200 with no redirect hop (clean URLs only). Links written as absolute production
// URLs (https://site.tld/about) and page-relative ones (about, ../about) are
// internal too — they get the same check.
// Catches dead links and renamed pages before users do.
for (const path of PAGES) {
  test(`navigation — ${path} loads and its internal links resolve`, async ({ page, request, baseURL }) => {
    const res = await page.goto(path);
    expect(res?.status(), `${path} should return 200`).toBe(200);

    const hrefs = await page.locator('a[href]').evaluateAll((as) =>
      as.map((a) => (a as HTMLAnchorElement).getAttribute('href') ?? ''));
    const siteHost = stripWww(new URL(SITE.url).hostname.toLowerCase());
    const pageUrl = page.url();

    for (const href of [...new Set(hrefs)]) {
      const target = internalTarget(href, pageUrl, siteHost);
      if (target === null) continue;
      const url = new URL(target, baseURL).href;
      const r = await request.get(url, { maxRedirects: 0 });
      expect([200, 304], `internal link ${href} returned ${r.status()} (expected 200, no redirect hop)`).toContain(r.status());
    }
  });
}
