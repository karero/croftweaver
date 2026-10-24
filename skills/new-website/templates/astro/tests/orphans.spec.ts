import { test, expect } from '@playwright/test';
import { PAGES } from './_helpers';
import { SITE } from '../src/config';

// Orphan guard: every indexable page must be REACHABLE from the home page by
// following internal <a href> links. A page can be in the sitemap (and pass every
// other suite) yet be linked from nowhere — Google calls these "orphaned" pages;
// they get crawled rarely, rank poorly, and are invisible to humans browsing the
// site. navigation.spec checks links that EXIST resolve; this checks the inverse —
// that every page IS a link target — the failure a per-page sweep structurally
// cannot see (it's a graph property, not a page property).
//
// This is the offline, deterministic half of internal-link hygiene (no network).
// The judgment half — WHERE to add the missing contextual links, and which pages
// are merely "thin" (one inbound link, usually just the nav) — is the
// `internal-link-audit` skill + `scripts/check_internal_links.sh`.
//
// Pages you DELIBERATELY leave unlinked (a paid-campaign landing page reached only
// from an ad, a print-QR page) go in ORPHAN_EXEMPT with a reason — opt OUT explicitly
// rather than loosen the test (Rule 12). The home page is the crawl root, never an
// orphan. Empty exempt set = green from commit 1 (the starter's '/' + '/privacy' are
// both linked from the layout).
const ORPHAN_EXEMPT = new Set<string>([
  // '/lp/spring-promo',  // reached only from the paid ad — intentionally unlinked
]);

// The crawl root: a page reachable means "reachable from here". Home is '/'.
const ROOT = '/';

// Normalize an href to a PAGES-style path identity, or null if it is not an
// in-site page link. Mirrors navigation.spec's notion of "internal": absolute URLs
// on the production host (incl. the www/apex variant) count as internal. Strips the
// query + fragment (a link to /x?a=1#y still reaches the /x page) and the trailing
// slash, mapping the bare origin to '/'.
const stripWww = (host: string) => host.replace(/^www\./, '');
const siteHost = stripWww(new URL(SITE.url).hostname);

function toPath(href: string, sourceAbs: string): string | null {
  // Resolve EVERY internal form against the page it appears on — a browser crawler
  // reaches page-relative links ("about", "../pricing", "./team") too, not just
  // "/rooted" ones. (anchors.spec.ts resolves the same way.) Skip non-navigational
  // schemes / fragments / protocol-relative first.
  if (/^(mailto:|tel:|javascript:):?/i.test(href) || href.startsWith('#') || href.startsWith('//')) {
    return null;
  }
  let u: URL;
  try { u = new URL(href, sourceAbs); } catch { return null; }
  const host = stripWww(u.hostname.toLowerCase());
  const baseHost = stripWww(new URL(sourceAbs).hostname.toLowerCase());
  if (host !== siteHost && host !== baseHost) return null; // external
  const path = u.pathname.split(/[?#]/)[0];
  if (path === '' || path === '/') return '/';
  return path.replace(/\/$/, '');
}

test('no orphan pages — every route is reachable from the home page', async ({ page, baseURL }) => {
  const known = new Set<string>(PAGES);
  expect(known.has(ROOT), `crawl root ${ROOT} must be in PAGES (home page)`).toBe(true);

  // BFS over the in-site link graph, starting at home. We only enqueue targets that
  // are themselves in PAGES (the indexable set the sitemap drift-alarm pins): a page
  // reachable only THROUGH a noindex/excluded page is still orphaned for crawlers.
  const reachable = new Set<string>([ROOT]);
  const queue: string[] = [ROOT];
  while (queue.length) {
    const path = queue.shift()!;
    const res = await page.goto(path);
    expect(res?.status(), `${path} should return 200 while crawling for orphans`).toBe(200);
    const sourceAbs = new URL(path, baseURL!).href; // resolve page-relative hrefs against here

    const hrefs = await page.locator('a[href]').evaluateAll((as) =>
      as.map((a) => (a as HTMLAnchorElement).getAttribute('href') ?? ''));
    for (const href of hrefs) {
      const target = toPath(href, sourceAbs);
      if (target && known.has(target) && !reachable.has(target)) {
        reachable.add(target);
        queue.push(target);
      }
    }
  }

  const orphans = [...known].filter((p) => !reachable.has(p) && !ORPHAN_EXEMPT.has(p));
  expect(
    orphans,
    `orphaned page(s) — in the sitemap but reachable from no internal link:\n` +
      orphans.map((p) => `  ${p}`).join('\n') +
      `\n\nAdd a contextual in-body link from a related page (or a nav/footer entry in ` +
      `src/config.ts) so crawlers and humans can find them. Run the internal-link-audit ` +
      `skill for WHERE to link. Deliberately-unlinked pages go in ORPHAN_EXEMPT with a reason.`,
  ).toEqual([]);
});
