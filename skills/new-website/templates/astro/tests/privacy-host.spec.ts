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
// slot, so only a plain mark is skipped: text alone in the page's own document (not in
// a shadow root, which placeholders.spec.ts does not read), with no element inside it
// and no element around it that placeholders.spec.ts leaves unread (PLACEHOLDER_EXEMPT,
// script, style, noscript), and in no PLACEHOLDER_ALLOWLIST entry, not even one that
// runs on from text before the mark. Any other mark is compared as a host. The text is
// read as placeholders.spec.ts reads it, from the text nodes (textContent).
const squash = (s: string) => s.replace(/\s+/g, '').toLowerCase();
const inAllowlist = (text: string) =>
  placeholderAllowed(text) || [...PLACEHOLDER_ALLOWLIST].some((a) => squash(a).includes(squash(text)));

const isOneSlot = (text: string) => {
  const found = [...text.matchAll(UNFILLED_SLOT)].map((m) => m[0]);
  return found.length === 1 && found[0] === text;
};

function hostOf(named: string, plain = false): string | null {
  const text = named.trim();
  if (plain && isOneSlot(text) && text.includes('ANALYTICS.scriptHost') && !inAllowlist(text)) return null;
  try {
    return new URL(text.includes('://') ? text : `https://${text}`).hostname;
  } catch {
    return text;
  }
}

// Every mark on the page, and whether it is plain (see above).
async function marks(page: Page): Promise<{ text: string; plain: boolean }[]> {
  const unread = `script, style, noscript, ${PLACEHOLDER_EXEMPT}`;
  return page.locator('[data-analytics-host]').evaluateAll(
    (els, sel) => els.map((el) => ({
      text: el.textContent ?? '',
      plain: el.getRootNode() === document && el.childElementCount === 0 && !el.closest(sel),
    })),
    unread,
  );
}

function wrongHosts(path: string, found: { text: string; plain: boolean }[], expected: string): string[] {
  return found
    .filter(({ text, plain }) => {
      const host = hostOf(text, plain);
      return host !== null && host !== expected;
    })
    .map(({ text }) => `${path} names "${text.trim()}"`);
}

test('privacy host — a slot is skipped, a filled host or address is read by its host', () => {
  // The two shipped slots.
  expect(hostOf('[ANALYTICS HOST, the host name in ANALYTICS.scriptHost in src/config.ts, for example plausible.io]', true)).toBeNull();
  expect(hostOf('[ANALYSE-HOST, der Hostname aus ANALYTICS.scriptHost in src/config.ts, zum Beispiel plausible.io]', true)).toBeNull();
  // Not known to be a plain mark: compared.
  expect(hostOf('[ANALYTICS HOST, the host name in ANALYTICS.scriptHost]')).not.toBeNull();
  expect(hostOf(' plausible.io ')).toBe('plausible.io');
  expect(hostOf('https://example.com/js/script.js')).toBe('example.com');
  // A host left in brackets, or a broken slot, is not the kit's slot: it is compared.
  for (const text of ['[plausible.io]', '[Plausible.io]', '[Wrong.example', '[P]', '[plausible.io, see ANALYTICS.scriptHost]']) {
    expect(hostOf(text, true), text).not.toBeNull();
  }
});

test('privacy host — only a slot placeholders.spec.ts reports is skipped', () => {
  for (const text of ['[ ANALYTICS.scriptHost]', '[AANALYTICS.scriptHost]']) {
    expect(hostOf(text, true), text).toBeNull();
  }
  // Slot-like, but not one whole slot: compared as a host.
  for (const text of ['[A] ANALYTICS.scriptHost', '[A ANALYTICS.scriptHost] x', '[A ANALYTICS.scriptHost', 'ANALYTICS.scriptHost']) {
    expect(hostOf(text, true), text).not.toBeNull();
  }
  // A slot placeholders.spec.ts lets pass is compared too.
  expect(hostOf('[A ANALYTICS.scriptHost]', false), 'a mark that is not plain').not.toBeNull();
  for (const entry of ['[a  analytics.scripthost]', '[Note [A ANALYTICS.scriptHost]']) {
    PLACEHOLDER_ALLOWLIST.add(entry);
    try {
      expect(hostOf('[A ANALYTICS.scriptHost]', true), `allow-listed as ${entry}`).not.toBeNull();
    } finally {
      PLACEHOLDER_ALLOWLIST.delete(entry);
    }
  }
});

test('privacy host — a slot in a mark that is not plain is read as a host on a page', async ({ page }) => {
  const slot = '[A ANALYTICS.scriptHost]';
  const cases = [
    `<p data-placeholder-exempt><span data-analytics-host>${slot}</span></p>`,
    `<p><code><span data-analytics-host>${slot}</span></code></p>`,
    `<pre><span data-analytics-host>${slot}</span></pre>`,
    `<p><span data-analytics-host><code>${slot}</code></span></p>`,
    `<p><span data-analytics-host><b>${slot}</b></span></p>`,
    `<div id="host"></div><script>document.getElementById('host').attachShadow({ mode: 'open' })` +
      `.innerHTML = '<span data-analytics-host>${slot}</span>';</script>`,
  ];
  for (const html of cases) {
    await page.setContent(`<!doctype html><body><p><span data-analytics-host>${slot}</span></p>${html}</body>`);
    const found = await marks(page);
    expect(found.map((m) => m.plain), html).toEqual([true, false]);
    expect(wrongHosts('/test', found, 'plausible.io'), html).toHaveLength(1);
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
