import { test, expect } from '@playwright/test';

// Guards the website-story layer on the home page (see STORY.md): the direct CTA is
// repeated, the story's key line is really on the page, and the plan is a real
// numbered list. Hermetic string checks, a sibling of positioning.spec.ts: no
// network, no extraction library, not a density check.
//
// This file lives in the website-story skill rather than the new-website Astro
// overlay because a fresh scaffold has no story to assert. Copy it into tests/ only
// when the site opted in, then fill CONFIG from the values listed at the end of
// STORY.md. While CONFIG is empty every test skips with a stated reason, so an
// unconfigured copy reports "not applicable" instead of failing like a product bug.

// ── EDIT THIS BLOCK ──────────────────────────────────────────────────────────
const CONFIG = {
  /** Direct CTA label, verbatim from STORY.md §5. Empty = every test skips. */
  directCta: '',
  /** Header plus at least one repeat. */
  directCtaMin: 2,
  /**
   * The CTA's target (e.g. '/contact', '/#contact', 'mailto:hello@example.com'). Set it and
   * every link carrying the label must point there: same site, same page (a trailing slash
   * does not matter, a query string is ignored), and the same #section when you give one.
   * Empty = the target is not checked.
   */
  directCtaHref: '',
  /** The one-liner OR the controlling idea, verbatim. Empty = that test skips. */
  keyLine: '',
  /** Selector for the plan container, one element (e.g. '#plan ol'). Empty = that test skips. */
  planList: '',
  /**
   * Selector for one step inside it, relative to the container. 'li' for a real
   * list; a card grid of numbered steps uses its card class (e.g. '.card'). The
   * count and the empty-step check are the assertion, not the markup.
   */
  planStep: 'li',
  /** A plan has three steps; four at most. Five is a process page. */
  planSteps: { min: 3, max: 4 },
  /** The page the story is told on. */
  home: '/',
};
// ─────────────────────────────────────────────────────────────────────────────

// Case- and whitespace-insensitive, same spirit as positioning.spec.ts: a label
// wrapped onto two lines or set in small caps still counts.
const norm = (s: string) => s.toLowerCase().replace(/\s+/g, ' ').trim();
// A CTA label matches when it IS the label, give or take trailing decoration such as
// an emoji or an arrow. "Book" does not match "Bookings", and "Request quote" does
// not match "Get a quote". A drifted copy therefore drops out of the count: the test
// fails once fewer than directCtaMin copies still carry the exact label.
const isLabel = (text: string, label: string) =>
  norm(text).replace(/[^\p{L}\p{N}]+$/u, '') === norm(label).replace(/[^\p{L}\p{N}]+$/u, '');

test.beforeEach(() => {
  test.skip(!CONFIG.directCta,
    'CONFIG.directCta is empty: fill it from STORY.md §5 to enable the story guard');
});

test.describe('story layer (home page)', () => {
  test('the direct CTA appears as a link or button at least twice', async ({ page }) => {
    await page.goto(CONFIG.home);
    // Counted in visible <a>/<button> text, not body text, so a sentence that merely
    // mentions the words is not a call to action, a collapsed mobile menu does not
    // count, and a <button> inside an <a> counts once.
    const ctas = await page.locator('a:visible, button:visible').evaluateAll((els) =>
      els.filter((el) => !(el.tagName === 'BUTTON' && el.closest('a')))
        // .href is the browser-resolved absolute URL, so '/contact', 'contact' and
        // 'https://this-site/contact' compare alike; '' for a <button> or an <a> without href.
        .map((el) => ({ text: (el as HTMLElement).innerText, link: el.tagName === 'A',
          href: el.tagName === 'A' ? (el as HTMLAnchorElement).href : '' })));
    const hits = ctas.filter((c) => isLabel(c.text, CONFIG.directCta));
    expect(hits.length,
      `"${CONFIG.directCta}" found ${hits.length}x as a visible link/button on ${CONFIG.home}; ` +
      `STORY.md asks for at least ${CONFIG.directCtaMin} (header + one repeat), same label`)
      .toBeGreaterThanOrEqual(CONFIG.directCtaMin);
    if (CONFIG.directCtaHref) {
      // Links only: a <button> CTA (a form submit, a dialog opener) has no href to compare.
      // Resolved against the page's base URL, as the browser resolved each link's href. The
      // scheme counts too: mailto: and tel: both have the origin "null".
      const want = new URL(CONFIG.directCtaHref, await page.evaluate(() => document.baseURI));
      const path = (u: URL) => u.pathname.replace(/\/+$/, '');
      const same = (href: string) => {
        let u: URL;
        try { u = new URL(href); } catch { return false; }   // no href, or one the browser could not parse
        return u.protocol === want.protocol && u.origin === want.origin && path(u) === path(want) &&
          (!want.hash || u.hash === want.hash);
      };
      const off = hits.filter((c) => c.link && !same(c.href)).map((c) => c.href || '(none)');
      expect(off, `"${CONFIG.directCta}" must always point to ${CONFIG.directCtaHref}`).toEqual([]);
    }
  });

  test('the one-liner or controlling idea is in the body text', async ({ page }) => {
    test.skip(!CONFIG.keyLine,
      'CONFIG.keyLine is empty: set the one-liner or the controlling idea');
    await page.goto(CONFIG.home);
    const body = await page.evaluate(() => document.body.innerText);
    expect(norm(body).includes(norm(CONFIG.keyLine)),
      `key line missing from ${CONFIG.home}: "${CONFIG.keyLine}". ` +
      'Say it once, in the header or the intro paragraph.')
      .toBe(true);
  });

  test('the plan is one container of three or four non-empty steps', async ({ page }) => {
    test.skip(!CONFIG.planList,
      'CONFIG.planList is empty: point it at the plan container');
    await page.goto(CONFIG.home);
    const plan = page.locator(CONFIG.planList);
    await expect(plan, `expected exactly one element matching "${CONFIG.planList}"`)
      .toHaveCount(1);
    const steps = await plan.locator(`:scope > ${CONFIG.planStep}`).allInnerTexts();
    expect(steps.length,
      `plan has ${steps.length} steps; STORY.md asks for ${CONFIG.planSteps.min}-${CONFIG.planSteps.max}`)
      .toBeGreaterThanOrEqual(CONFIG.planSteps.min);
    expect(steps.length,
      `plan has ${steps.length} steps; more than ${CONFIG.planSteps.max} is a process page, not a plan`)
      .toBeLessThanOrEqual(CONFIG.planSteps.max);
    expect(steps.filter((s) => !s.trim()).length, 'an empty plan step').toBe(0);
  });
});
