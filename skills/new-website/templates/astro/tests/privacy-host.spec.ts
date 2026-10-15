import { test, expect } from '@playwright/test';
import { PAGES } from './_helpers';
import { ANALYTICS } from '../src/config';

// The privacy page tells a visitor how to refuse the measurement: block scripts from
// one host. That host must be the one the site loads its analytics from,
// ANALYTICS.scriptHost in src/config.ts, or the advice blocks nothing. The page marks
// the host it names with data-analytics-host, so this reads the mark, not the sentence
// around it: the check holds through a reworded or translated sentence as long as the
// mark stays. Until launch the mark holds a [BRACKET] slot, which passes here
// (placeholders.spec.ts reports it). A site without analytics deletes the paragraph,
// mark and all, and passes too. A proxied script's full address
// (https://example.com/js/script.js) counts by its host.

// The kit's own slot shape, as placeholders.spec.ts reads it: "[" and a capital letter.
const SLOT = /^\[\s*\p{Lu}/u;

function hostOf(named: string): string | null {
  const text = named.trim();
  if (SLOT.test(text)) return null;
  try {
    return new URL(text.includes('://') ? text : `https://${text}`).hostname;
  } catch {
    return text;
  }
}

test('privacy host — a slot is skipped, a filled host or address is read by its host', () => {
  expect(hostOf('[ANALYTICS HOST, for example plausible.io]')).toBeNull();
  expect(hostOf(' plausible.io ')).toBe('plausible.io');
  expect(hostOf('https://example.com/js/script.js')).toBe('example.com');
  // Brackets around a real host are not a slot: the host is still compared.
  expect(hostOf('[plausible.io]')).not.toBeNull();
});

test('privacy host — the host marked data-analytics-host is ANALYTICS.scriptHost', async ({ page }) => {
  const expected = new URL(ANALYTICS.scriptHost).hostname;
  const wrong: string[] = [];
  for (const path of PAGES) {
    await page.goto(path);
    for (const named of await page.locator('[data-analytics-host]').allInnerTexts()) {
      const host = hostOf(named);
      if (host !== null && host !== expected) wrong.push(`${path} names ${named.trim()}`);
    }
  }
  expect(
    wrong,
    `The sentence on refusing the measurement must name the host analytics loads from, ` +
      `${expected} (ANALYTICS.scriptHost in src/config.ts). Change the page or the config.`,
  ).toEqual([]);
});
