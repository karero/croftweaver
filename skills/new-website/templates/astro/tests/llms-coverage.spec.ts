import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { PAGES } from './_helpers';
import { SITE } from '../src/config';

// llms.txt coverage guard. public/llms.txt is the curated GEO / AI-answer-engine
// page map — and it is hand-maintained, so it drifts: a page gets registered in
// PAGES, nav and the sitemap but never added here. That exact slip happened FOUR
// times on a real site built with this kit (2026-06/07), each time caught only by
// a human review — attention wasn't the problem, the workflow was, so the fix is
// a test, not a checklist line. This makes both mechanical halves of the defect
// checkable: a MISSING entry (page added, never listed) and a STALE one (page
// removed/renamed, entry lingers). The third half — an entry whose WORDING has
// drifted from the page — is not mechanically checkable and stays a
// website-review Pass-2 / website-seo-geo judgment item.

// Pages you DELIBERATELY keep out of the public AI index (a paid-ad landing page,
// a print-QR page — typically the same routes as orphans.spec's ORPHAN_EXEMPT).
// llms.txt is served publicly, so listing a hidden page would hand it to AI
// answer engines and defeat the unlinking. Opt OUT explicitly with a reason
// rather than loosen the test (Rule 12).
const LLMS_EXEMPT = new Set<string>([
  // '/lp/spring-promo',  // paid-ad landing page — deliberately not in the AI index
]);

// SITE.url ships without a trailing slash by convention (src/config.ts), but
// normalize anyway — a config edit must not turn every expected URL into a
// double-slash mismatch. PAGES paths are slash-less too (trailingSlash: 'never').
const base = SITE.url.replace(/\/+$/, '');

// ONE parse all three tests share: every same-site markdown link TARGET in
// llms.txt, normalized to a PAGES-style path. `](` pins a link target (a bare
// URL in prose does not count); the fragment/query is stripped — a link to
// /pricing#plans still lists the /pricing page; trailing slash dropped; the
// bare origin maps to '/'. Two tests parsing the same file two different ways
// is exactly how false positives creep in — so they don't.
function linkedPaths(): string[] {
  const txt = readFileSync(join(process.cwd(), 'public', 'llms.txt'), 'utf8');
  return [
    ...new Set(
      [...txt.matchAll(/\]\(\s*(https?:\/\/[^)\s]+)/g)]
        .map((m) => m[1].split(/[?#]/)[0])
        .filter((u) => u === base || u.startsWith(`${base}/`))
        .map((u) => {
          const path = u.slice(base.length).replace(/\/$/, '');
          return path === '' ? '/' : path;
        }),
    ),
  ];
}

// Hosted-asset links (a /whitepaper.pdf, an /og-image.png) are not pages. Known
// extensions only — a dotted ROUTE like /guides/v2.0 is still a page and must
// not silently escape the stale guard.
const ASSET =
  /\.(pdf|png|jpe?g|svg|gif|webp|avif|ico|css|js|mjs|json|xml|txt|webmanifest|mp4|webm|zip)$/i;

test('every PAGES route is listed in public/llms.txt', () => {
  const listed = new Set(linkedPaths());
  const missing = PAGES.filter((route) => !LLMS_EXEMPT.has(route) && !listed.has(route));
  expect(
    missing,
    `routes missing from public/llms.txt (add a "- [Title](URL): description" line):\n  ` +
      missing.join('\n  '),
  ).toEqual([]);
});

// The reverse guard: every same-site page link in llms.txt must map back to a
// PAGES route, so a removed or renamed page cannot linger as a stale entry (the
// missing-entry check above structurally cannot see that half).
test('no stale llms.txt entry — every same-site page link is a PAGES route', () => {
  const known = new Set<string>(PAGES);
  // the asset skip assumes no real PAGE route ends like an asset — fail loud if
  // that ever changes, instead of silently exempting the route from this guard
  expect(
    PAGES.filter((p) => ASSET.test(p)),
    'PAGES routes ending in an asset extension would silently escape the stale guard',
  ).toEqual([]);
  const stale = linkedPaths().filter((p) => !ASSET.test(p) && !known.has(p));
  expect(
    stale,
    `stale llms.txt entries — same-site links to routes not in PAGES (page removed or renamed?):\n  ` +
      stale.join('\n  '),
  ).toEqual([]);
});

// The exemption must actually exempt: a route in LLMS_EXEMPT is hidden ON
// PURPOSE, so it appearing in the public llms.txt is the leak the exemption
// exists to prevent — not a pass.
test('LLMS_EXEMPT routes stay out of public llms.txt', () => {
  const listed = new Set(linkedPaths());
  const exposed = [...LLMS_EXEMPT].filter((route) => listed.has(route));
  expect(
    exposed,
    `deliberately-hidden routes listed in the public AI index (remove the line or the exemption):\n  ` +
      exposed.join('\n  '),
  ).toEqual([]);
});

// An exemption for a page that no longer exists is dead config — prune it, or
// it shields a future route of the same name without anyone deciding that.
test('LLMS_EXEMPT contains only live PAGES routes', () => {
  const known = new Set<string>(PAGES);
  const dead = [...LLMS_EXEMPT].filter((route) => !known.has(route));
  expect(
    dead,
    `stale exemptions — routes no longer in PAGES:\n  ` + dead.join('\n  '),
  ).toEqual([]);
});
