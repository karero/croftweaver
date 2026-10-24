import { test, expect } from '@playwright/test';
import { SITE } from '../src/config';
import { loadCard, parseLighthouse, sameState, stateOf, summarize, today } from '../scripts/scorecard.mjs';

// Guards the published scorecard (the website-scorecard skill): the page shows the
// numbers in scorecard.json, the file adds up, and the script's own arithmetic is
// pinned. It belongs to that skill, not to the starter, because a new site has no
// scorecard to check, and it needs the script the skill installs: follow the skill's
// install steps (three files and the package script), then set PAGE below. Until
// scorecard.json exists the two file tests skip and say why.

// The page that carries <Scorecard />, e.g. '/about'. Empty = the page test skips.
const PAGE = '';

const { card, broken } = loadCard();

// While `npm run scorecard` writes a new card, the checks of the old one sit out:
// otherwise a card that is wrong could never be replaced.
test.skip(!!process.env.SCORECARD_RUN, 'a new scorecard is being written');

test('scorecard — the script counts a run correctly and refuses bad input', () => {
  const run = {
    suites: [
      { file: 'a11y.spec.ts', specs: [{ tests: [{ status: 'expected' }, { status: 'expected' }] }] },
      { file: 'seo.spec.ts', specs: [{ tests: [{ status: 'expected' }] }], suites: [{ specs: [{ tests: [{ status: 'skipped' }] }] }] },
      { file: 'tone.spec.ts', specs: [{ tests: [{ status: 'unexpected' }, { status: 'flaky' }] }] },
      { file: 'scorecard.spec.ts', specs: [{ tests: [{ status: 'expected' }, { status: 'skipped' }] }] },
    ],
  };
  expect(summarize(run)).toEqual({
    checks: [
      { area: 'a11y', passed: 2, skipped: 0, failed: 0 },
      { area: 'seo', passed: 1, skipped: 1, failed: 0 },
      { area: 'tone', passed: 0, skipped: 0, failed: 2 },
    ],
    passed: 3, skipped: 1, failed: 2,
  });

  const on = '2026-10-04';
  expect(parseLighthouse('98,100,100,100', '2026-10-04', 'mobile', on).value).toEqual({
    date: '2026-10-04', strategy: 'mobile', performance: 98, accessibility: 100, bestPractices: 100, seo: 100,
  });
  expect(parseLighthouse('98,100,100,100', '2024-02-29', 'desktop', on).value?.date, 'a real leap day').toBe('2024-02-29');
  for (const bad of ['98,100,100', '98,100,100,101', '98,100,100,x', '9.8,100,100,100', '']) {
    expect(parseLighthouse(bad, '2026-10-04', 'mobile', on).error, `"${bad}" must be refused`).toBeTruthy();
  }
  for (const bad of ['4 October', '2026-02-30', '2026-04-31', '2026-02-29', '2026-13-01', '2026-10-05']) {
    expect(parseLighthouse('98,100,100,100', bad, 'mobile', on).error, `the date "${bad}" must be refused`).toBeTruthy();
  }
  expect(parseLighthouse('98,100,100,100', '2026-10-04', 'tablet', on).error, 'an unknown strategy must be refused').toBeTruthy();
  expect(today(new Date(2026, 9, 4, 23, 30)), 'the local day, also late in the evening').toBe('2026-10-04');

  // "Edited since" is decided here: any path added, removed or changed counts.
  expect(sameState({ src: 'a', public: 'b' }, { src: 'a', public: 'b' })).toBe(true);
  expect(sameState({ src: 'a', public: 'b' }, { src: 'a', public: 'c' }), 'a changed folder').toBe(false);
  expect(sameState({ src: 'a', functions: 'f' }, { src: 'a' }), 'a folder added later').toBe(false);
  expect(sameState({ src: 'a' }, { src: 'a', functions: 'f' }), 'a folder removed later').toBe(false);
  expect(sameState({}, undefined), 'nothing to compare is not "unchanged"').toBe(false);

  // A file that cannot be read is reported, never thrown.
  expect(loadCard('does-not-exist.json')).toEqual({ card: null, broken: false });
  expect(loadCard('package.json'), 'valid JSON that is not a scorecard').toEqual({ card: null, broken: true });
  expect(loadCard('tests/scorecard.spec.ts'), 'not JSON at all').toEqual({ card: null, broken: true });
});

test('scorecard — scorecard.json adds up', () => {
  expect(broken, 'scorecard.json cannot be read as a scorecard. Run "npm run scorecard" to write a new one.').toBe(false);
  test.skip(!card, 'no scorecard.json yet: run "npm run scorecard"');
  const sum = (k: 'passed' | 'skipped') => card.checks.reduce((n: number, c: Record<string, number>) => n + (c[k] ?? 0), 0);
  expect(card.passed, 'the total must be the sum of the areas').toBe(sum('passed'));
  expect(card.skipped, 'the skipped total must be the sum of the areas').toBe(sum('skipped'));
  expect(card.passed, 'a card with nothing passed is not a card').toBeGreaterThan(0);
  expect(card.commit, 'the tested commit must be a full id').toMatch(/^[0-9a-f]{40}$/);
  expect(card.generated).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  expect(Object.keys(card.tested ?? {}), 'the card must say what it tested').toEqual(expect.arrayContaining(['src', 'tests', 'package.json']));
});

test('scorecard — the page shows the numbers in the file', async ({ page }) => {
  test.skip(!PAGE, 'PAGE is not set: name the page that carries <Scorecard />');
  test.skip(!card, 'no scorecard.json to show: run "npm run scorecard"');
  await page.goto(PAGE);
  const section = page.locator('[data-scorecard]');
  await expect(section, `${PAGE} must render the scorecard`).toHaveCount(1);

  // Every figure on the page against the file: the totals, each area, the date, the version.
  const whole = (n: number) => new RegExp(`(^|\\D)${n}(\\D|$)`);
  // The summary names the checks first and the pages second, in both built-in
  // languages. A language added to the component with another order: adapt this line.
  const figures = ((await section.locator('[data-scorecard-summary]').textContent()) ?? '').match(/\d+/g)?.map(Number) ?? [];
  expect(figures, 'the summary: checks passed, then pages').toEqual([card.passed, card.pages]);
  await expect(section.locator('[data-scorecard-skipped]')).toHaveCount(card.skipped > 0 ? 1 : 0);
  if (card.skipped > 0) await expect(section.locator('[data-scorecard-skipped]')).toHaveText(whole(card.skipped));
  await expect(section.locator('[data-scorecard-tested]')).toContainText(card.generated);
  await expect(section.locator('[data-scorecard-tested]')).toContainText(card.commit.slice(0, 7));
  await expect(section.locator('tbody tr')).toHaveCount(card.checks.length);
  for (const c of card.checks) {
    await expect(section.locator(`tbody tr[data-area="${c.area}"] td`), `the row for ${c.area}`).toHaveText(String(c.passed));
  }
  const lighthouse = section.locator('[data-scorecard-lighthouse]');
  await expect(lighthouse).toHaveCount(card.lighthouse ? 1 : 0);
  if (card.lighthouse) {
    const { date, strategy, performance, accessibility, bestPractices, seo } = card.lighthouse;
    await expect(lighthouse).toContainText(date);
    await expect(lighthouse).toContainText(strategy);
    // The four scores, in the order the page lists them.
    const shown = ((await lighthouse.textContent()) ?? '').split(':').slice(1).join(':').match(/\d+/g)?.map(Number) ?? [];
    expect(shown.slice(0, 4), 'the four Lighthouse scores').toEqual([performance, accessibility, bestPractices, seo]);
    // The link re-runs the same test: PageSpeed, this site's address, the same device class.
    const href = new URL((await lighthouse.locator('a').getAttribute('href')) ?? 'about:blank');
    expect([href.origin, href.pathname], 'the re-run link opens PageSpeed').toEqual(['https://pagespeed.web.dev', '/analysis']);
    expect(href.searchParams.get('url'), 'the re-run link tests this site').toBe(SITE.url + '/');
    expect(href.searchParams.get('form_factor'), 'the re-run link uses the same device class').toBe(strategy);
  }

  // What the page says about the card's age, against the same question asked here.
  // (The page was built from this working tree, so the answer has to be the same.)
  const expected = stateOf(card);
  await expect(section, 'the page must say whether the site was edited since').toHaveAttribute('data-state', expected);
  await expect(section.locator('[data-scorecard-edited]')).toHaveCount(expected === 'edited' ? 1 : 0);
  await expect(section.locator('[data-scorecard-current]')).toHaveCount(expected === 'current' ? 1 : 0);
});
