import { test, expect } from '@playwright/test';
import { PAGES } from './_helpers';
import { SITE } from '../src/config';

// Anchor-integrity guard — the COMPLEMENT to navigation.spec.ts. That spec proves
// every internal ROUTE returns 200; this proves the OTHER half of "internal links
// resolve": every "#fragment" actually points at a real element id on its target
// page. A link like "/#section" or "/?tag=x#section" makes the page return 200, so
// navigation.spec is satisfied — but if nothing on the page has id="section", the
// click scrolls nowhere (or to the wrong place).
//
// Outgoing links are read from the live DOM (so client-rendered links are covered),
// as are the ids of every shipped page (PAGES); a target outside PAGES falls back to
// its served HTML. Target existence uses a plain request (asset-safe: a PDF/file 200s
// without rendering), and fragments on non-HTML targets are skipped — a PDF "#page=3"
// is a viewer instruction, not an element id. Pure markup + fully offline, so it stays
// in the CI gate; external-link *liveness* deliberately does not (see links.spec.ts +
// the outgoing-link-audit skill).

const stripWww = (h: string) => h.replace(/^www\./, '');
const SITE_HOST = stripWww(new URL(SITE.url).hostname.toLowerCase());

type Ref = { route: string; fragment: string };

// Resolve an href against the page it appears on → the in-site { route, fragment }
// it anchors to, or null when it carries no fragment (navigation.spec's job) or is
// external / non-navigational. `new URL(href, base)` normalises every internal form
// the same way: relative ("about#x", "../about#x"), root-relative ("/about#x"),
// query ("/?q#x"), and same-host absolute URLs.
function anchorRef(href: string, sourceAbs: string, testHost: string): Ref | null {
  if (!href || /^(mailto:|tel:|javascript:|data:)/i.test(href)) return null;
  let u: URL;
  try {
    u = new URL(href, sourceAbs);
  } catch {
    return null;
  }
  if (u.protocol !== 'http:' && u.protocol !== 'https:') return null;
  const host = stripWww(u.hostname.toLowerCase());
  if (host !== testHost && host !== SITE_HOST) return null; // external
  let fragment = u.hash.slice(1);
  if (!fragment) return null; // no fragment → not our concern
  // Browsers match "#caf%C3%A9" to id="café": compare the decoded form.
  try {
    fragment = decodeURIComponent(fragment);
  } catch {
    /* malformed escape: compare the raw text */
  }
  const route = u.pathname.replace(/\/+$/, '') || '/';
  return { route, fragment };
}

// Every element id exposed by a freshly-loaded page (read from the live DOM).
const idsOf = (page: import('@playwright/test').Page) =>
  page.locator('[id]').evaluateAll((els) => els.map((e) => e.id).filter(Boolean));

const idsFromHtml = (html: string) =>
  new Set([...html.matchAll(/\sid=(?:"([^"]+)"|'([^']+)')/g)].map((m) => m[1] ?? m[2]));

test('every internal #anchor points at a real element id', async ({ page, request, baseURL }) => {
  const testHost = stripWww(new URL(baseURL!).hostname.toLowerCase());
  const routeOf = (p: string) => new URL(p, baseURL!).pathname.replace(/\/+$/, '') || '/';

  const idsByRoute = new Map<string, Set<string>>();
  const found: { from: string; href: string; ref: Ref }[] = [];

  // 1) Visit every page: record its element ids (live DOM) and its outgoing anchor links.
  for (const path of PAGES) {
    const resp = await page.goto(path, { waitUntil: 'load' });
    if (resp && resp.ok()) idsByRoute.set(routeOf(path), new Set(await idsOf(page)));
    const hrefs = await page
      .locator('a[href]')
      .evaluateAll((as) => as.map((a) => (a as HTMLAnchorElement).getAttribute('href') ?? ''));
    const sourceAbs = new URL(path, baseURL!).href;
    for (const href of hrefs) {
      const ref = anchorRef(href, sourceAbs, testHost);
      if (ref) found.push({ from: routeOf(path), href, ref });
    }
  }

  // 2) Resolve anchor targets not already loaded (a target not in PAGES): confirm it
  //    exists, and if it's HTML grab its ids. Assets 200 without yielding ids.
  const exists = new Map<string, boolean>();
  for (const route of new Set(found.map((f) => f.ref.route))) {
    if (idsByRoute.has(route)) {
      exists.set(route, true);
      continue;
    }
    const resp = await request.get(route);
    exists.set(route, resp.ok());
    if (resp.ok() && (resp.headers()['content-type'] || '').includes('text/html')) {
      idsByRoute.set(route, idsFromHtml(await resp.text()));
    }
  }

  // 3) Every fragment must exist on its target page.
  const problems: string[] = [];
  for (const { from, href, ref } of found) {
    if (!exists.get(ref.route)) {
      problems.push(`[${from}] ${href} → target page "${ref.route}" did not load (404)`);
      continue;
    }
    const ids = idsByRoute.get(ref.route);
    // ids === undefined → non-HTML asset; "#page=3"-style fragments are valid there.
    if (ids && !ids.has(ref.fragment)) {
      problems.push(`[${from}] ${href} → no element with id="${ref.fragment}" on "${ref.route}"`);
    }
  }
  expect(problems, `dead internal anchor(s):\n${problems.join('\n')}`).toEqual([]);
});

// Pure checks of the two helpers above: no page, no server.
test('anchor helpers — single-quoted ids are read, percent-escaped fragments are decoded', () => {
  expect([...idsFromHtml(`<h2 id="a">x</h2><h2 id='b'>y</h2>`)]).toEqual(['a', 'b']);
  const ref = anchorRef('/about#caf%C3%A9', 'http://localhost:4321/', 'localhost');
  expect(ref?.fragment).toBe('café');
  expect(anchorRef('/about#bad%E0%A4%A', 'http://localhost:4321/', 'localhost')?.fragment).toBe('bad%E0%A4%A');
});
