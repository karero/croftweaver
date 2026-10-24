import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { PAGES, THEMES } from './_helpers';

// Accessibility (WCAG 2.0/2.1 A + AA + best practice) on every page, in BOTH
// light and dark themes. Contrast that passes in light can fail in dark, so the
// full matrix runs.
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

      const summary = results.violations.map((v) => ({
        id: v.id, impact: v.impact, nodes: v.nodes.length,
      }));
      expect(JSON.stringify(summary, null, 2)).toBe('[]');
    });
  }
}
