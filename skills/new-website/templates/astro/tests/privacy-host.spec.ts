import { test, expect } from '@playwright/test';
import { PAGES, UNFILLED_SLOT } from './_helpers';
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

// Skipped: the kit's own slot and nothing else. The whole text is one "unfilled [SLOT]"
// to placeholders.spec.ts (UNFILLED_SLOT in _helpers.ts, the rule that spec reports) and
// names ANALYTICS.scriptHost, as both shipped slots do. Any other text in the mark,
// brackets or not, is compared as a host. Skipping is safe only because placeholders.spec.ts
// reports the slot, so the tests below fail on any skip that is not one whole slot.
const isOneSlot = (text: string) => {
  const found = [...text.matchAll(UNFILLED_SLOT)].map((m) => m[0]);
  return found.length === 1 && found[0] === text;
};

function hostOf(named: string): string | null {
  const text = named.trim();
  if (isOneSlot(text) && text.includes('ANALYTICS.scriptHost')) return null;
  try {
    return new URL(text.includes('://') ? text : `https://${text}`).hostname;
  } catch {
    return text;
  }
}

test('privacy host — a slot is skipped, a filled host or address is read by its host', () => {
  // The two shipped slots.
  expect(hostOf('[ANALYTICS HOST, the host name in ANALYTICS.scriptHost in src/config.ts, for example plausible.io]')).toBeNull();
  expect(hostOf('[ANALYSE-HOST, der Hostname aus ANALYTICS.scriptHost in src/config.ts, zum Beispiel plausible.io]')).toBeNull();
  expect(hostOf(' plausible.io ')).toBe('plausible.io');
  expect(hostOf('https://example.com/js/script.js')).toBe('example.com');
  // A host left in brackets, or a broken slot, is not the kit's slot: it is compared.
  for (const text of ['[plausible.io]', '[Plausible.io]', '[Wrong.example', '[P]', '[plausible.io, see ANALYTICS.scriptHost]']) {
    expect(hostOf(text), text).not.toBeNull();
  }
});

test('privacy host — whatever is skipped is one slot placeholders.spec.ts reports', () => {
  const skipped = [
    '[ANALYTICS HOST, the host name in ANALYTICS.scriptHost in src/config.ts, for example plausible.io]',
    '[ANALYSE-HOST, der Hostname aus ANALYTICS.scriptHost in src/config.ts, zum Beispiel plausible.io]',
    '[ ANALYTICS.scriptHost]',
    '[AANALYTICS.scriptHost]',
  ];
  for (const text of skipped) {
    expect(hostOf(text), text).toBeNull();
    expect(isOneSlot(text), text).toBe(true);
  }
  // Slot-like, but not one whole slot: compared as a host.
  for (const text of ['[A] ANALYTICS.scriptHost', '[A ANALYTICS.scriptHost] x', '[A ANALYTICS.scriptHost', 'ANALYTICS.scriptHost']) {
    expect(hostOf(text), text).not.toBeNull();
  }
});

test('privacy host — the host marked data-analytics-host is ANALYTICS.scriptHost', async ({ page }) => {
  const expected = new URL(ANALYTICS.scriptHost).hostname;
  const wrong: string[] = [];
  const unreported: string[] = [];
  for (const path of PAGES) {
    await page.goto(path);
    for (const named of await page.locator('[data-analytics-host]').allInnerTexts()) {
      const host = hostOf(named);
      if (host === null && !isOneSlot(named.trim())) unreported.push(`${path} skips "${named.trim()}"`);
      if (host !== null && host !== expected) wrong.push(`${path} names "${named.trim()}"`);
    }
  }
  expect(unreported, 'Skipped text must be one slot that placeholders.spec.ts reports.').toEqual([]);
  expect(
    wrong,
    `The sentence on refusing the measurement must name the host analytics loads from, ` +
      `${expected} (ANALYTICS.scriptHost in src/config.ts). Change the page or the config.`,
  ).toEqual([]);
});
