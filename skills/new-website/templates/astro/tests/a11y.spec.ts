import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { PAGES, THEMES, contrastWarning } from './_helpers';

// Accessibility (WCAG 2.0/2.1 A + AA + best practice) on every page, in BOTH
// light and dark themes. Contrast that passes in light can fail in dark, so the
// full matrix runs. Text axe cannot measure (over an image or a gradient) is not a
// violation: it comes back in `incomplete`, and is printed as a warning (warn-only).
for (const path of PAGES) {
  for (const theme of THEMES) {
    test(`a11y — ${path} [${theme}]`, async ({ page }) => {
      await page.addInitScript((t) => {
        try { localStorage.setItem('theme', t); } catch (e) { /* ignore */ }
      }, theme);
      await page.goto(path);
      await page.evaluate(() => document.fonts.ready);

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
        .analyze();

      const undecided = contrastWarning(path, theme, results.incomplete);
      if (undecided) {
        console.warn('⚠ a11y contrast: ' + undecided);
        test.info().annotations.push({ type: 'warning', description: undecided });
      }

      const summary = results.violations.map((v) => ({
        id: v.id, impact: v.impact, nodes: v.nodes.length,
      }));
      expect(JSON.stringify(summary, null, 2)).toBe('[]');
    });
  }
}

// The `incomplete` list from a real axe run (text over a background image, a gradient and an <img>), read
// through the same function as above: the warning names each element and axe's reason.
test('a11y — contrast axe could not decide is reported from a real axe answer', () => {
  const capture = JSON.parse(readFileSync(join(process.cwd(), 'tests', 'fixtures', 'axe-core-4.14.0-playwright-4.14.0-incomplete.json'), 'utf8'));
  expect(contrastWarning('/probe', 'light', capture.incomplete)).toBe(
    '/probe [light]: axe could not decide the contrast of 3 element(s); look at them by eye: ' +
    "div:nth-child(2) > p (Element's background color could not be determined due to a background image) | " +
    "div:nth-child(3) > p (Element's background color could not be determined due to a background gradient) | " +
    "div:nth-child(4) > p (Element's background color could not be determined because element contains an image node)",
  );
  expect(contrastWarning('/probe', 'light', [])).toBeNull();
  expect(contrastWarning('/probe', 'light', [{ id: 'aria-valid-attr', nodes: capture.incomplete[0].nodes }])).toBeNull();
});
