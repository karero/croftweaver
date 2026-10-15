import { test, expect } from '@playwright/test';
import { PAGES } from './_helpers';
import { ANALYTICS } from '../src/config';

// The privacy page tells a visitor how to refuse the measurement: block scripts from
// one host. That host must be the one the site loads its analytics from,
// ANALYTICS.scriptHost in src/config.ts, or the advice blocks nothing. The page names
// it in a [BRACKET] slot until launch; a slot still in brackets passes here, since
// placeholders.spec.ts reports it. A site without analytics deletes the paragraph, and
// a page without the sentence passes too. The full address of a proxied script
// (https://example.com/js/script.js) counts by its host.
const REFUSAL = [
  /block\s+scripts\s+from\s+(.+?)\s+with\s+a\s+content\s+blocker/gi,
  /Skripte\s+von\s+(.+?)\s+mit\s+einem\s+Inhaltsblocker/gi,
];

function namedHosts(text: string): string[] {
  const hosts: string[] = [];
  for (const re of REFUSAL) {
    for (const [, named] of text.matchAll(re)) {
      if (named.startsWith('[')) continue;
      try {
        hosts.push(new URL(named.includes('://') ? named : `https://${named}`).hostname);
      } catch {
        hosts.push(named);
      }
    }
  }
  return hosts;
}

test('privacy host — the refusal sentence is read in both languages, slots skipped', () => {
  expect(namedHosts('You can refuse the measurement: block scripts from plausible.io with a content blocker in your browser.')).toEqual(['plausible.io']);
  expect(namedHosts('Blockieren Sie Skripte von https://example.com/js/script.js mit einem Inhaltsblocker in Ihrem Browser.')).toEqual(['example.com']);
  expect(namedHosts('block scripts from [ANALYTICS HOST, for example plausible.io] with a content blocker')).toEqual([]);
});

test('privacy host — the page names the host in ANALYTICS.scriptHost', async ({ page }) => {
  const expected = new URL(ANALYTICS.scriptHost).hostname;
  const wrong: string[] = [];
  for (const path of PAGES) {
    await page.goto(path);
    for (const host of namedHosts(await page.locator('body').innerText())) {
      if (host !== expected) wrong.push(`${path} names ${host}`);
    }
  }
  expect(
    wrong,
    `The sentence on refusing the measurement must name the host analytics loads from, ` +
      `${expected} (ANALYTICS.scriptHost in src/config.ts). Change the page or the config.`,
  ).toEqual([]);
});
