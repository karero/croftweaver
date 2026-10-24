import { test, expect } from '@playwright/test';
import { PAGES } from './_helpers';

// Positioning spine (see the website-positioning skill + POSITIONING.md). The site's
// positioning is worked out BEFORE content/SEO; each page then NAMES the thing it wants
// to own and threads it through its core semantic surfaces. Presence/threading,
// case-insensitive, hermetic — no network, no extraction library, NOT a density check
// (density rewards stuffing and fights tone/GEO).
//
// A surface (title / desc / h1 / body) is a list of CLAUSES, all of which must match (AND).
// A clause is either:
//   • a phrase string        — that phrase must be present, or
//   • an array of phrases     — ANY ONE of them must be present (OR-group / alternatives)
// So  title: ['mobile app technology', ['React Native vs Flutter vs Native', 'RN vs Flutter']]
// means the <title> must contain "mobile app technology" AND one of the two comparison
// phrasings. `h1` clauses are matched against the <h1> OR the intro paragraph (so the H1 can
// stay human). Omitted surfaces are not checked.
//
// Two map forms:
//   • Shorthand   { term, body? }                 — the term is required in title, desc, and
//                                                   <h1>|intro. Use for a page that owns ONE phrase.
//   • Per-surface { title?, desc?, h1?, body? }    — explicit clause lists per surface, for a
//                                                   page whose surfaces legitimately differ.
//
// Starts EMPTY so the suite is green from commit 1. Add a row the moment a page's
// positioning is decided; the page then has to earn it (red → green), the same loop as
// adding a route to PAGES. Example (delete, replace with the real spine):
//   '/':       { term: '[core term]', body: ['[market category]'] },
//   '/compare': { title: [['React Native vs Flutter', 'RN vs Flutter']], desc: ['React Native', 'Flutter'],
//                 h1: [['React Native vs Flutter', 'mobile app technology']], body: ['mobile app technology'] },
type Clause = string | string[]; // string = required phrase · string[] = any-one (OR-group)
type TermRule = { term: string; body?: Clause[] };
type SurfaceRule = { title?: Clause[]; desc?: Clause[]; h1?: Clause[]; body?: Clause[] };
export const POSITIONING: Record<string, TermRule | SurfaceRule> = {
  // '/': { term: '...', body: ['...'] },
};

// Pages that legitimately own NO positioning term (legal / utility — privacy, imprint,
// 404). Excluded from the coverage flag below so it only nags about real content/offer
// pages. Add to this set for a genuinely term-free page; don't delete the flag.
const POSITIONING_EXEMPT = new Set<string>(['/privacy', '/impressum']);

const norm = (r: TermRule | SurfaceRule): Required<SurfaceRule> =>
  'term' in r
    ? { title: [r.term], desc: [r.term], h1: [r.term], body: r.body ?? [] }
    : { title: r.title ?? [], desc: r.desc ?? [], h1: r.h1 ?? [], body: r.body ?? [] };

const first = (clauses: Clause[]) => {
  const c = clauses[0];
  return Array.isArray(c) ? c[0] : c;
};

const entries = Object.entries(POSITIONING);

test.describe('positioning spine', () => {
  if (entries.length === 0) {
    // Nothing declared yet — green from commit 1. Populate during the
    // website-positioning step (pipeline step 2), before page copy is written.
    test.skip('no positioning terms declared yet (fill POSITIONING + this map)', () => {});
  }

  // Coverage flag (warn-only, non-blocking): a content page with no POSITIONING entry is
  // not an error — positioning is opt-in and the suite stays green from commit 1 — but it
  // usually means the page ships with no term it owns. Surface it as a warning so the
  // opportunity is not lost silently (Rule 12). Hermetic: just compares route sets.
  test('positioning coverage — content pages should declare a term (warn-only)', () => {
    const mapped = new Set(Object.keys(POSITIONING));
    const unmapped = PAGES.filter((p) => !mapped.has(p) && !POSITIONING_EXEMPT.has(p));
    if (unmapped.length) {
      const msg =
        `positioning not declared for ${unmapped.length} content page(s): ${unmapped.join(', ')} — ` +
        `add each to the POSITIONING map (and POSITIONING.md), or it ships with no owned term ` +
        `(a lost opportunity). A genuinely term-free legal/utility page belongs in POSITIONING_EXEMPT.`;
      console.warn('⚠ positioning coverage: ' + msg);
      test.info().annotations.push({ type: 'warning', description: msg });
    }
  });

  for (const [path, rule] of entries) {
    const r = norm(rule);
    const label = first(r.title) || first(r.h1) || first(r.desc) || path;
    test(`positioning — "${label}" carried on ${path}`, async ({ page }) => {
      await page.goto(path);
      const data = await page.evaluate(() => {
        const txt = (el: Element | null) => (el?.textContent || '');
        const main = document.querySelector('main') || document.querySelector('article') || document.body;
        return {
          title: document.title || '',
          description:
            document.querySelector('meta[name="description"]')?.getAttribute('content') || '',
          h1s: Array.from(document.querySelectorAll('h1')).map((h) => h.textContent || ''),
          intro: txt(main.querySelector('p')),
          bodyText: (document.body as HTMLElement).innerText || '',
        };
      });

      const has = (hay: string, needle: string) => hay.toLowerCase().includes(needle.toLowerCase());
      const headline = data.h1s.join(' · ') + ' · ' + data.intro; // <h1> OR intro

      // Collect every unmet clause across the four surfaces.
      const missing: string[] = [];
      const check = (surface: string, hay: string, clauses: Clause[]) => {
        for (const clause of clauses) {
          const ok = Array.isArray(clause) ? clause.some((p) => has(hay, p)) : has(hay, clause);
          if (!ok) {
            missing.push(
              Array.isArray(clause)
                ? `${surface} needs one of [${clause.join(' | ')}]`
                : `${surface} needs "${clause}"`,
            );
          }
        }
      };
      check('<title>', data.title, r.title);
      check('<meta description>', data.description, r.desc);
      check('<h1>/intro', headline, r.h1);
      check('body', data.bodyText, r.body);

      expect(
        missing,
        `${path} positioning not threaded (title="${data.title}" · h1="${data.h1s.join(' · ')}"):\n` +
          `  • ${missing.join('\n  • ')}\n` +
          `Name the thing this page owns in its title, description, and the <h1> or the ` +
          `sentence right under it — do not pad with synonyms or chase density.`,
      ).toEqual([]);
    });
  }
});
