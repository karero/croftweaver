import { test, expect, type Page } from '@playwright/test';
import { PAGES, UNFILLED_SLOT, PLACEHOLDER_ALLOWLIST, PLACEHOLDER_EXEMPT, placeholderAllowed } from './_helpers';
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
// to placeholders.spec.ts (UNFILLED_SLOT in _helpers.ts) and names ANALYTICS.scriptHost,
// as both shipped slots do. A skip is safe only while placeholders.spec.ts reports the
// slot, so a slot that spec lets pass (in PLACEHOLDER_ALLOWLIST, or inside an element
// matching PLACEHOLDER_EXEMPT, script, style or noscript) is compared as a host instead,
// like any other text in the mark.
const isOneSlot = (text: string) => {
  const found = [...text.matchAll(UNFILLED_SLOT)].map((m) => m[0]);
  return found.length === 1 && found[0] === text;
};

function hostOf(named: string, exempt = false): string | null {
  const text = named.trim();
  if (!exempt && isOneSlot(text) && text.includes('ANALYTICS.scriptHost') && !placeholderAllowed(text)) return null;
  try {
    return new URL(text.includes('://') ? text : `https://${text}`).hostname;
  } catch {
    return text;
  }
}

// Every mark on the page, with whether placeholders.spec.ts skips the element it is in.
async function marks(page: Page): Promise<{ text: string; exempt: boolean }[]> {
  const unread = `script, style, noscript, ${PLACEHOLDER_EXEMPT}`;
  return page.locator('[data-analytics-host]').evaluateAll(
    (els, sel) => els.map((el) => ({ text: (el as HTMLElement).innerText, exempt: !!el.closest(sel) })),
    unread,
  );
}

function wrongHosts(path: string, found: { text: string; exempt: boolean }[], expected: string): string[] {
  return found
    .filter(({ text, exempt }) => {
      const host = hostOf(text, exempt);
      return host !== null && host !== expected;
    })
    .map(({ text }) => `${path} names "${text.trim()}"`);
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

test('privacy host — only a slot placeholders.spec.ts reports is skipped', () => {
  for (const text of ['[ ANALYTICS.scriptHost]', '[AANALYTICS.scriptHost]']) {
    expect(hostOf(text), text).toBeNull();
  }
  // Slot-like, but not one whole slot: compared as a host.
  for (const text of ['[A] ANALYTICS.scriptHost', '[A ANALYTICS.scriptHost] x', '[A ANALYTICS.scriptHost', 'ANALYTICS.scriptHost']) {
    expect(hostOf(text), text).not.toBeNull();
  }
  // A slot placeholders.spec.ts lets pass is compared too.
  expect(hostOf('[A ANALYTICS.scriptHost]', true), 'inside an exempt element').not.toBeNull();
  PLACEHOLDER_ALLOWLIST.add('[a  analytics.scripthost]');
  try {
    expect(hostOf('[A ANALYTICS.scriptHost]'), 'allow-listed').not.toBeNull();
  } finally {
    PLACEHOLDER_ALLOWLIST.delete('[a  analytics.scripthost]');
  }
});

test('privacy host — a slot in an exempt element is read as a host on a page', async ({ page }) => {
  for (const wrap of ['<p data-placeholder-exempt>%</p>', '<p><code>%</code></p>', '<pre>%</pre>']) {
    const html = wrap.replace('%', '<span data-analytics-host>[A ANALYTICS.scriptHost]</span>');
    await page.setContent(`<!doctype html><body><p><span data-analytics-host>[A ANALYTICS.scriptHost]</span></p>${html}</body>`);
    const found = await marks(page);
    expect(found.map((m) => m.exempt), wrap).toEqual([false, true]);
    expect(wrongHosts('/test', found, 'plausible.io'), wrap).toHaveLength(1);
  }
});

test('privacy host — the host marked data-analytics-host is ANALYTICS.scriptHost', async ({ page }) => {
  const expected = new URL(ANALYTICS.scriptHost).hostname;
  const wrong: string[] = [];
  for (const path of PAGES) {
    await page.goto(path);
    wrong.push(...wrongHosts(path, await marks(page), expected));
  }
  expect(
    wrong,
    `The sentence on refusing the measurement must name the host analytics loads from, ` +
      `${expected} (ANALYTICS.scriptHost in src/config.ts). Change the page or the config.`,
  ).toEqual([]);
});
