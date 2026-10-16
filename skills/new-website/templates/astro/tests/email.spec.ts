import { test, expect } from '@playwright/test';
import { PAGES } from './_helpers';
import { emailHint } from '../src/lib/obfuscate';

// Anti-harvest guardrail: the SERVED HTML of every page must contain no plaintext
// email address and no `mailto:` link. Addresses go through <EmailLink>, which
// obfuscates at build time and reassembles the mailto in the browser (the decode
// logic lives in an external bundle, not the page HTML). Catches an accidental raw
// address before scrapers do. Fetches the raw HTML (no JS), which is what a bot sees.
// The bare string "mailto:" from EmailLink's reassembly script is fine — it carries
// no address; we flag a harvestable ADDRESS (including one inside a mailto: link).
// The negative lookahead skips asset-style names like "team@2x.webp" (an image
// filename, not an address) — a real TLD is never an image/asset extension.
const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(?!(?:png|jpe?g|gif|webp|avif|svg|ico|css|js|mjs|json|xml|txt|woff2?)\b)[A-Za-z]{2,}/;

for (const path of PAGES) {
  test(`email — ${path} ships no harvestable address`, async ({ request, baseURL }) => {
    const html = await (await request.get(new URL(path, baseURL!).href)).text();
    const m = html.match(EMAIL);
    expect(m?.[0] ?? null, `${path} ships a plaintext email "${m?.[0]}" — use <EmailLink>`).toBeNull();
  });
}

// The no-JS hint speaks the language of the page it is on, not the site's: the
// German Impressum on an English site must say "[punkt]", not "[dot]". Runs with
// JavaScript off, as a no-JS visitor sees it (with JS on, the decode script swaps
// the hint for the address). Each hint is rebuilt from its encoded address and
// the page's <html lang>; links with their own `text` (no "[at]") are skipped.
test.describe('without JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  for (const path of PAGES) {
    test(`email — ${path} hints use the page's language`, async ({ page }) => {
      await page.goto(path);
      const lang = (await page.locator('html').getAttribute('lang')) ?? '';
      const links = await page.locator('a.email-link[data-email]').evaluateAll((els) =>
        els.map((a) => ({ data: (a as HTMLElement).dataset.email!, text: a.textContent ?? '' })));
      for (const { data, text } of links.filter((l) => l.text.includes('[at]'))) {
        const address = Buffer.from(data, 'base64').toString('utf-8').split('').reverse().join('');
        expect(text, `${path} (<html lang="${lang}">) shows the hint in another language`).toBe(emailHint(address, lang));
      }
    });
  }
});

// encodeEmail lets a % through (an old but valid address character), and a mailto: link
// must carry it as %25, or "a%41@…" opens a mail to "aA@…". A page that shows an address
// is served with one such link added, and EmailLink's own script turns it into the link.
test('email — a % in an address reaches the mail program unchanged', async ({ page, request, baseURL }) => {
  // The first page whose HTML carries an EmailLink, so its script is on the page too.
  const [path] = await pagesWithEmail(request, baseURL!);
  test.skip(!path, 'no page shows an address through EmailLink');
  const address = 'a%41@example.com';
  const data = Buffer.from(address.split('').reverse().join(''), 'utf-8').toString('base64');
  const url = new URL(path!, baseURL!).href;
  await page.route(url, async (route) => {
    const response = await route.fetch();
    const html = (await response.text()).replace(/<body([^>]*)>/, `<body$1><a class="email-link" href="#" data-email="${data}" data-test-percent>a [at] example [dot] com</a>`);
    await route.fulfill({ response, body: html });
  });
  await page.goto(url);
  const link = page.locator('[data-test-percent]');
  await expect(link).toHaveText(address);
  const href = (await link.getAttribute('href')) ?? '';
  expect(href).toBe('mailto:a%2541@example.com');
  expect(decodeURIComponent(href.slice('mailto:'.length))).toBe(address);
});

// The site's one conversion: a click on an email address reports one "Email Tap" event to
// Plausible, and the address is never part of it. Plausible runs only on a live build with
// analytics switched on (Base.astro writes window.plausible there;
// tests/check_analytics_gate.sh checks it), so the builds this runs on have none, and each
// test puts its own recorder in its place, under the same name, before the page's scripts
// run. Every test clicks the real links on the built pages, and checks that the browser is
// still asked to open the mail program: counting must never stop that.
type Counted = Window & { __taps?: unknown[][]; plausible?: unknown };

// Every page whose HTML carries an EmailLink, read from the built site.
async function pagesWithEmail(request: import('@playwright/test').APIRequestContext, baseURL: string) {
  const found: string[] = [];
  for (const p of PAGES) {
    if (/\sdata-email=/.test(await (await request.get(new URL(p, baseURL).href)).text())) found.push(p);
  }
  return found;
}

// Clicks the link and waits for the browser to ask for its mailto: link, which is what
// hands the mail to the visitor's mail program.
async function clickAndOpen(page: import('@playwright/test').Page, link: import('@playwright/test').Locator) {
  const asked = page.waitForRequest((r) => r.url().startsWith('mailto:'), { timeout: 5000 });
  await link.click();
  await asked;
}

test('email — each click on an email address reports one "Email Tap" event and no address', async ({ page, request, baseURL }) => {
  const paths = await pagesWithEmail(request, baseURL!);
  test.skip(paths.length === 0, 'no page shows an address through EmailLink');
  await page.addInitScript(() => {
    const w = window as Counted;
    w.__taps = [];
    w.plausible = (...args: unknown[]) => { w.__taps!.push(args); };
  });
  for (const path of paths) {
    await page.goto(path);
    const links = page.locator('a.email-link');
    const n = await links.count();
    for (let i = 0; i < n; i++) {
      await expect(links.nth(i), `${path}: link ${i + 1} is not turned into a mailto: link`).toHaveAttribute('href', /^mailto:/);
      await clickAndOpen(page, links.nth(i));
      const taps = await page.evaluate(() => (window as Counted).__taps);
      expect(taps, `${path}: after click ${i + 1}`).toEqual(Array.from({ length: i + 1 }, () => ['Email Tap']));
    }
    // A second click on the same link counts again: Plausible shows visitors and totals.
    await clickAndOpen(page, links.first());
    const taps = await page.evaluate(() => (window as Counted).__taps);
    expect(taps, `${path}: a second click on the first link`).toHaveLength(n + 1);
    expect(JSON.stringify(taps), `${path}: an event carries an address`).not.toContain('@');
  }
});

test('email — with no tracker, a broken one or one that throws, the click still opens the mail and nothing breaks', async ({ page, request, baseURL }) => {
  const [path] = await pagesWithEmail(request, baseURL!);
  test.skip(!path, 'no page shows an address through EmailLink');
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(path);
  const link = page.locator('a.email-link').first();
  // No tracker: this build has none, and the test says so before it clicks.
  expect(await page.evaluate(() => typeof (window as Counted).plausible)).toBe('undefined');
  await clickAndOpen(page, link);
  await page.evaluate(() => { (window as Counted).plausible = () => { throw new Error('tracker failure'); }; });
  await clickAndOpen(page, link);
  await page.evaluate(() => { (window as Counted).plausible = 'not a function'; });
  await clickAndOpen(page, link);
  expect(errors, 'a click raised an error on the page').toEqual([]);
});
