// The hero carousel (the website-hero-carousel skill), installed as tests/hero-carousel.spec.ts.
// Set PAGE, PAUSE and SWAP below to what the page passes to <HeroCarousel>; the spec fails while
// one is empty. LANG only if the page passes lang="…".
// One copy guards one carousel (one per page: its ids are fixed).
//
// Every test enters the way a visitor does: the page as built, served by `astro preview`, the real
// buttons. Time is a fake clock, frozen, so that a swap comes exactly when the interval says; a
// real clock would make every timing test flaky on a loaded machine. The CSS fade is the exception:
// the browser runs transitions on real time, so the fade tests read the opacity as it goes.
//
// What it cannot know is checked at build time by HeroCarousel.astro itself: two or more slides, an
// alt text and a label for each, a language it has texts for.
import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { parse } from 'node-html-parser';
import { TEXT, hasText } from '../src/components/hero-carousel-text';

const PAGE: string = '';   // the page with the carousel, e.g. '/'
const PAUSE: string = '';  // the page's pause setting: 'button' or 'dots' (default of the component: 'button')
const SWAP: string = '';   // the page's swap setting: 'instant' or 'fade' (default of the component: 'instant')
const LANG: string = '';   // only if the page passes lang="…": that language; else the page's own

const root = '[data-hero-carousel]';
const dot = (page: Page, i: number) => page.locator(`${root} [data-hc-pick="${i}"]`);
const toggle = (page: Page) => page.locator(`${root} [data-hc-toggle]`);
const active = (page: Page) => page.evaluate(() => Array.from(document.querySelectorAll<HTMLElement>('[data-hc-slide]')).filter((s) => s.hasAttribute('data-active')).map((s) => Number(s.dataset.hcSlide)));

// The fake clock, frozen: after install() Playwright lets the fake time keep flowing with the
// real time, so on a loaded machine a second or two slip in and a swap comes early. Paused, only
// runFor moves it.
async function freeze(page: Page) {
  await page.clock.install({ time: new Date('2026-10-23T08:00:00Z') });
  await page.clock.pauseAt(new Date('2026-10-23T08:00:01Z'));
}
async function open(page: Page, opts: { reduced?: boolean; scheme?: 'light' | 'dark'; frozen?: boolean } = {}) {
  if (opts.reduced) await page.emulateMedia({ reducedMotion: 'reduce' });
  if (opts.scheme) await page.emulateMedia({ colorScheme: opts.scheme });
  if (opts.frozen !== false) await freeze(page);
  await page.goto(PAGE);
  await page.waitForLoadState('load');
  await expect(page.locator(root)).toHaveAttribute('data-ready', '');
  // On screen: the pixel tests clip the screenshot to the viewport.
  await page.locator(root).scrollIntoViewIfNeeded();
}
const interval = (page: Page) => page.locator(root).evaluate((el) => Number((el as HTMLElement).dataset.interval));
const decoded = (page: Page) => page.evaluate(() => Promise.all(Array.from(document.querySelectorAll('[data-hc-slide] img')).map((im) => (im as HTMLImageElement).decode().catch(() => undefined))));
// A rotation by a visitor-less click: a mouse click would leave the pointer on the carousel, which holds it.
const press = (page: Page, i: number) => page.evaluate((k) => document.querySelector<HTMLButtonElement>(`[data-hc-pick="${k}"]`)!.click(), i);
const contrast = (a: number, b: number) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
const lum = (px: number[]) => {
  const l = (v: number) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  return 0.2126 * l(px[0]) + 0.7152 * l(px[1]) + 0.0722 * l(px[2]);
};
async function pixelsAt(page: Page, clip: { x: number; y: number; width: number; height: number }, points: [number, number][]) {
  const png = await page.screenshot({ clip });
  return page.evaluate(async ({ b64, points }) => {
    const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
    const c = document.createElement('canvas'); c.width = img.width; c.height = img.height; const x = c.getContext('2d')!; x.drawImage(img, 0, 0);
    return points.map(([px, py]) => Array.from(x.getImageData(px, py, 1, 1).data).slice(0, 3));
  }, { b64: png.toString('base64'), points });
}
// The photos of the page as built: the slides' <img> files and their attributes, read from the HTML.
async function slidesOf(page: Page) {
  const html = await (await page.request.get(PAGE)).text();
  return parse(html).querySelectorAll('[data-hc-slide]').map((s) => ({
    img: s.querySelector('img')!, href: s.querySelector('a')?.getAttribute('href') ?? null,
  }));
}
const stemOf = (src: string) => (src.split('/').pop() ?? '').split('.')[0];
// The slides whose links take keyboard focus when a visitor tabs through the page from its start: the real
// Tab key, a stop at a time, until focus leaves the page's own stops (back to the document) or 200 presses.
async function slideLinksInTabOrder(page: Page): Promise<number[]> {
  await page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur(); window.scrollTo(0, 0); });
  const seen = new Set<number>();
  const stops = new Set<number>(); // which element of the page each press landed on, by its place in the document
  for (let i = 0; i < 200; i++) {
    await page.keyboard.press('Tab');
    const at = await page.evaluate(() => {
      const el = document.activeElement;
      const a = el?.closest('[data-hc-slide] a');
      return { slide: a ? Number((a.closest('[data-hc-slide]') as HTMLElement).dataset.hcSlide) : -1, body: el === document.body || el === null, place: el ? Array.prototype.indexOf.call(document.querySelectorAll('*'), el) : -1 };
    });
    if (at.slide >= 0) seen.add(at.slide);
    if (at.body || stops.has(at.place)) break; // back at the document, or at a stop already visited: the page's stops have come round
    stops.add(at.place);
  }
  return [...seen];
}
// How many photos with this alt text the accessibility tree of the slides holds (aria-hidden ones are not in it), matched by accessible name, not by text.
const inTree = (page: Page, alt: string) => page.locator(`${root} .hc-slides`).getByRole('img', { name: alt, exact: true }).count();
const same = (a: string, b: string) => a.replace(/\s+/g, ' ') === b.replace(/\s+/g, ' ');

test('hero carousel — the install is complete: the page and both settings are named', () => {
  expect(PAGE, 'set PAGE in tests/hero-carousel.spec.ts to the page with the carousel').not.toBe('');
  expect(['button', 'dots'], 'set PAUSE to what the page passes (or the default, "button")').toContain(PAUSE);
  expect(['instant', 'fade'], 'set SWAP to what the page passes (or the default, "instant")').toContain(SWAP);
});

test('hero carousel — the markup: every slide in order with its alt text, one dot each, named; a button only in pause mode "button"', async ({ page }) => {
  await open(page);
  const slides = await slidesOf(page);
  expect(slides.length, 'two or more slides').toBeGreaterThanOrEqual(2);
  const lang = ((await page.locator(root).getAttribute('lang')) ?? '') as string;
  expect(hasText(lang), `the carousel speaks "${lang}", which has no texts in hero-carousel-text.ts`).toBe(true);
  const pageLang = ((await page.locator('html').getAttribute('lang')) ?? '').toLowerCase().split('-')[0];
  expect(lang, 'the carousel speaks the page\'s language, unless the page passes lang="…" and LANG names it').toBe((LANG || pageLang).toLowerCase().split('-')[0]);
  expect(await page.locator(root).getAttribute('data-pause'), 'the page\'s pause setting is what this spec says').toBe(PAUSE);
  expect(await page.locator(root).getAttribute('data-swap'), 'the page\'s swap setting is what this spec says').toBe(SWAP);
  const t = TEXT[lang as keyof typeof TEXT];
  for (const [i, s] of slides.entries()) expect((s.img.getAttribute('alt') ?? '').trim().length, `slide ${i + 1} has an alt text`).toBeGreaterThanOrEqual(10);
  await expect(page.locator(`${root} .hc-dot`)).toHaveCount(slides.length);
  for (let i = 0; i < slides.length; i++) {
    const name = (await dot(page, i).getAttribute('aria-label')) ?? '';
    expect(name.startsWith(t.photo(i + 1, slides.length, '').slice(0, -1)), `dot ${i + 1} is named "${name}"`).toBe(true);
    expect((await dot(page, i).textContent())?.trim(), 'a dot carries no text').toBe('');
  }
  await expect(toggle(page)).toHaveCount(PAUSE === 'button' ? 1 : 0);
  await expect(page.locator(`${root} .hc-controls button`)).toHaveCount(slides.length + (PAUSE === 'button' ? 1 : 0));
  // the first photo is the one that matters for the first paint; the others must not compete with it
  expect(slides[0].img.getAttribute('fetchpriority'), 'the first photo is loaded first').toBe('high');
  for (const s of slides.slice(1)) expect(s.img.getAttribute('fetchpriority'), 'a later photo is loaded at low priority').toBe('low');
});

test('hero carousel — it shows the first photo, then the next after the interval, then the first again', async ({ page }) => {
  await open(page);
  const ms = await interval(page);
  const n = await page.locator(`${root} [data-hc-slide]`).count();
  expect(await active(page)).toEqual([0]);
  await page.clock.runFor(ms - 1);
  expect(await active(page), `not yet at ${ms - 1} ms`).toEqual([0]);
  await page.clock.runFor(1);
  expect(await active(page)).toEqual([1]);
  for (let k = 2; k <= n; k++) await page.clock.runFor(ms);
  expect(await active(page), 'back to the first after one round').toEqual([0]);
  await expect(dot(page, 0)).toHaveAttribute('aria-current', 'true');
  await expect(page.locator(`${root} .hc-dot[aria-current="true"]`), 'one dot on show').toHaveCount(1);
});

test('hero carousel — pause mode "button": Pause stops it and says Resume (no aria-pressed); Resume starts it again; a dot restarts the interval and never clears a pause', async ({ page }) => {
  test.skip(PAUSE !== 'button', 'this page uses pause mode "dots"');
  await open(page);
  const lang = (await page.locator(root).getAttribute('lang')) as keyof typeof TEXT;
  const t = TEXT[lang];
  const ms = await interval(page);
  await expect(toggle(page)).toHaveText(t.pause);
  await expect(page.locator(`${root} .hc-slides`)).toHaveAttribute('aria-live', 'off');
  await toggle(page).click();
  await expect(toggle(page)).toHaveText(t.resume);
  await expect(toggle(page)).not.toHaveAttribute('aria-pressed', /.*/);
  await expect(page.locator(`${root} .hc-slides`), 'polite once it no longer moves').toHaveAttribute('aria-live', 'polite');
  await page.clock.runFor(5 * ms);
  expect(await active(page), 'a pause holds').toEqual([0]);
  await toggle(page).click();
  await expect(toggle(page)).toHaveText(t.pause);
  await page.clock.runFor(ms);
  expect(await active(page)).toEqual([1]);
  // a dot shows its photo at once and restarts the interval
  await page.clock.runFor(ms - 1000);
  await press(page, 0);
  expect(await active(page), 'at once').toEqual([0]);
  await page.clock.runFor(1000);
  expect(await active(page), 'the swap due a second after the click is not made').toEqual([0]);
  await page.clock.runFor(ms - 1000);
  expect(await active(page), 'one interval after the click').toEqual([1]);
  // a pick never clears a pause
  await toggle(page).click();
  await press(page, 0); // not a mouse click: the pointer left on the carousel would hold it anyway
  expect(await active(page)).toEqual([0]);
  await expect(toggle(page), 'still paused').toHaveText(t.resume);
  await page.clock.runFor(5 * ms);
  expect(await active(page)).toEqual([0]);
});

test('hero carousel — pause mode "dots": choosing a dot shows its photo at once and stops the rotation until the visitor reloads', async ({ page }) => {
  test.skip(PAUSE !== 'dots', 'this page uses pause mode "button"');
  await open(page);
  const ms = await interval(page);
  await page.clock.runFor(ms - 1000);
  await press(page, 1);
  expect(await active(page), 'at once').toEqual([1]);
  await expect(dot(page, 1)).toHaveAttribute('aria-current', 'true');
  await expect(dot(page, 0)).not.toHaveAttribute('aria-current', /.*/);
  await expect(page.locator(`${root} .hc-slides`), 'polite once it no longer moves').toHaveAttribute('aria-live', 'polite');
  await page.clock.runFor(10 * ms);
  expect(await active(page), 'it stays').toEqual([1]);
  await press(page, 0); // not a mouse click: the pointer left on the carousel would hold it anyway
  expect(await active(page)).toEqual([0]);
  await page.clock.runFor(10 * ms);
  expect(await active(page), 'and stays again').toEqual([0]);
});

test('hero carousel — keyboard focus entering from outside stops it, moving between the controls changes nothing, and leaving it entirely leaves it stopped', async ({ page }) => {
  await open(page);
  const ms = await interval(page);
  await page.keyboard.press('Tab'); // the visitor is using the keyboard
  await dot(page, 0).focus();
  await expect(page.locator(`${root} .hc-slides`)).toHaveAttribute('aria-live', 'polite');
  await page.clock.runFor(3 * ms);
  expect(await active(page), 'stopped by focus').toEqual([0]);
  await dot(page, 1).focus(); // from one control to another
  await page.clock.runFor(3 * ms);
  expect(await active(page), 'still stopped').toEqual([0]);
  await page.evaluate(() => (document.activeElement as HTMLElement).blur());
  await page.clock.runFor(3 * ms);
  expect(await active(page), 'focus left the carousel entirely: it stays stopped').toEqual([0]);
  if (PAUSE === 'button') {
    await toggle(page).focus();
    await page.keyboard.press('Enter');
    await expect(toggle(page), 'focus stays on the button').toBeFocused();
    await page.clock.runFor(ms);
    expect(await active(page), 'Resume starts it again').toEqual([1]);
  }
});

test('hero carousel — the pointer over it holds it, leaving starts the interval afresh', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 1600 }); // room below the carousel to leave it
  await open(page);
  const ms = await interval(page);
  const box = (await page.locator(`${root} .hc-slides`).boundingBox())!;
  await page.mouse.move(box.x + 50, box.y + 50);
  await page.clock.runFor(4 * ms);
  expect(await active(page), 'held while hovering').toEqual([0]);
  await page.mouse.move(box.x + 50, box.y + box.height + 20);
  await page.clock.runFor(ms - 1);
  expect(await active(page)).toEqual([0]);
  await page.clock.runFor(1);
  expect(await active(page)).toEqual([1]);
});

test('hero carousel — with reduced motion it starts stopped, and a dot shows its photo', async ({ page }) => {
  await open(page, { reduced: true });
  const ms = await interval(page);
  await expect(page.locator(`${root} .hc-slides`)).toHaveAttribute('aria-live', 'polite');
  await page.clock.runFor(5 * ms);
  expect(await active(page)).toEqual([0]);
  await dot(page, 1).click();
  await page.clock.runFor(5 * ms);
  expect(await active(page), 'shown at the visitor\'s request, then still').toEqual([1]);
});

test('hero carousel — a hidden tab does not advance; on return the interval starts afresh', async ({ page }) => {
  await open(page);
  const ms = await interval(page);
  const tab = (hidden: boolean) => page.evaluate((h) => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => h }); document.dispatchEvent(new Event('visibilitychange')); }, hidden);
  await page.clock.runFor(ms / 2);
  await tab(true);
  await page.clock.runFor(5 * ms);
  expect(await active(page)).toEqual([0]);
  await tab(false);
  await page.clock.runFor(ms - 1);
  expect(await active(page), 'unchanged just before the interval after the return').toEqual([0]);
  await page.clock.runFor(1);
  expect(await active(page)).toEqual([1]);
});

// The second photo held back, or broken: the first stays, nothing blank is shown.
async function holdSecondPhoto(page: Page) {
  const slides = await slidesOf(page);
  const stem = stemOf(slides[1].img.getAttribute('src') ?? '');
  test.skip(stem === stemOf(slides[0].img.getAttribute('src') ?? ''), 'the first two slides share one file; a held-back second photo cannot be told from the first');
  return new RegExp(`/_astro/${stem.replace(/[^\w-]/g, '')}\\.`);
}
test('hero carousel — a late second image: it stays on the first photo and swaps when the image arrives', async ({ page }) => {
  const late = await holdSecondPhoto(page);
  let release!: () => void;
  const gate = new Promise<void>((r) => { release = r; });
  await page.route(late, async (route) => { await gate; await route.continue(); });
  await freeze(page);
  await page.goto(PAGE, { waitUntil: 'commit' });
  await expect(page.locator(root)).toHaveAttribute('data-ready', '');
  const ms = await interval(page);
  await page.clock.runFor(ms + 1000);
  expect(await active(page), 'no blank slide while the image is late').toEqual([0]);
  release();
  await expect.poll(() => active(page), { timeout: 15000 }).toEqual([1]);
});

test('hero carousel — a dot for a late image waits for it, also when the pointer enters and leaves meanwhile', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 1600 });
  const late = await holdSecondPhoto(page);
  let release!: () => void;
  const gate = new Promise<void>((r) => { release = r; });
  await page.route(late, async (route) => { await gate; await route.continue(); });
  await freeze(page);
  await page.goto(PAGE, { waitUntil: 'commit' });
  await expect(page.locator(root)).toHaveAttribute('data-ready', '');
  await press(page, 1);
  expect(await active(page), 'the pick does not show a slide that is not there').toEqual([0]);
  const box = (await page.locator(`${root} .hc-slides`).boundingBox())!;
  await page.mouse.move(box.x + 50, box.y + 50);
  await page.mouse.move(box.x + 50, box.y + box.height + 20);
  release();
  await expect.poll(() => active(page), { timeout: 15000 }).toEqual([1]);
});

test('hero carousel — a first image that fails: the first other slide whose image is there takes its place, also when that image is still on its way', async ({ page }) => {
  const slides = await slidesOf(page);
  const stem = (i: number) => stemOf(slides[i].img.getAttribute('src') ?? '').replace(/[^\w-]/g, '');
  test.skip(stem(0) === stem(1), 'the first two slides share one file');
  const re = (i: number) => new RegExp(`/_astro/${stem(i)}\\.`);
  // 1. the other photos are held back: nothing else to show yet, then the second one arrives
  let release!: () => void;
  const gate = new Promise<void>((r) => { release = r; });
  await page.route(re(0), (route) => route.fulfill({ status: 404, body: 'gone' }));
  await page.route(re(1), async (route) => { await gate; await route.continue(); });
  for (let i = 2; i < slides.length; i++) await page.route(re(i), async (route) => { await gate; await route.continue(); });
  await freeze(page);
  await page.emulateMedia({ reducedMotion: 'reduce' }); // stopped: only the failure moves it
  await page.goto(PAGE, { waitUntil: 'commit' });
  await expect(page.locator(root)).toHaveAttribute('data-ready', '');
  await expect.poll(() => page.evaluate(() => (document.querySelector('[data-hc-slide] img') as HTMLImageElement).complete)).toBe(true); // the first has failed
  expect(await active(page), 'nothing else is there yet: it stays').toEqual([0]);
  release();
  await expect.poll(() => active(page), { timeout: 15000, message: 'the photo that arrives takes the place of the one that failed' }).not.toContain(0);
  expect((await active(page)).length, 'one photo on show').toBe(1);
});

test('hero carousel — a first image that fails after the script has started, while the others are still on their way: the second photo takes its place when it arrives, and the stopped rotation stays stopped', async ({ page }) => {
  const slides = await slidesOf(page);
  // three photos: the one after the second must be a working one, or a rotation restarted by the recovery would show nothing new
  test.skip(slides.length < 3, 'needs three photos');
  const stem = (i: number) => stemOf(slides[i].img.getAttribute('src') ?? '').replace(/[^\w-]/g, '');
  test.skip(new Set(slides.slice(0, 3).map((_, i) => stem(i))).size < 3, 'the first three slides do not have three files');
  const re = (i: number) => new RegExp(`/_astro/${stem(i)}\\.`);
  let failFirst!: () => void; let releaseSecond!: () => void; let releaseRest!: () => void;
  const gateFirst = new Promise<void>((r) => { failFirst = r; });
  const gateSecond = new Promise<void>((r) => { releaseSecond = r; });
  const gateRest = new Promise<void>((r) => { releaseRest = r; });
  await page.route(re(0), async (route) => { await gateFirst; await route.fulfill({ status: 404, body: 'gone' }); });
  await page.route(re(1), async (route) => { await gateSecond; await route.continue(); });
  // one route per file: a later slide that repeats the first or second file must not take over its route
  for (let i = 2; i < slides.length; i++) if (stem(i) !== stem(0) && stem(i) !== stem(1)) await page.route(re(i), async (route) => { await gateRest; await route.continue(); });
  await freeze(page);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(PAGE, { waitUntil: 'commit' });
  await expect(page.locator(root)).toHaveAttribute('data-ready', ''); // the script is running, no photo has arrived
  failFirst(); // now the first photo fails
  await expect.poll(() => page.evaluate(() => (document.querySelector('[data-hc-slide] img') as HTMLImageElement).complete)).toBe(true);
  expect(await active(page), 'nothing else is there yet: it stays').toEqual([0]);
  releaseSecond();
  await expect.poll(() => active(page), { timeout: 15000 }).toEqual([1]);
  releaseRest();
  await expect.poll(() => page.evaluate(() => { const im = document.querySelectorAll<HTMLImageElement>('[data-hc-slide] img')[2]; return im.complete && im.naturalWidth > 0; }), { timeout: 15000 }).toBe(true);
  // reduced motion started it stopped: the recovery does not start the rotation (the third photo is there to be shown if it did)
  const ms = await interval(page);
  for (let i = 0; i < 2; i++) { await page.clock.runFor(ms); expect(await active(page), 'still stopped after the recovery').toEqual([1]); }
});

test('hero carousel — a second image that fails: the rotation passes over it (with two photos, it stays on the first)', async ({ page }) => {
  const late = await holdSecondPhoto(page);
  const n = (await slidesOf(page)).length;
  await page.route(late, (route) => route.fulfill({ status: 404, body: 'gone' }));
  await open(page);
  const ms = await interval(page);
  const seen: number[] = [];
  for (let i = 0; i < 2 * n; i++) { await page.clock.runFor(ms); seen.push(...(await active(page))); }
  expect(seen, 'the failed photo is never shown').not.toContain(1);
  if (n === 2) expect(seen.every((k) => k === 0), 'two photos: it stays on the first').toBe(true);
  else expect(seen, 'the photos after the failed one are shown').toContain(2);
});

test('hero carousel — with JavaScript off, or with only the carousel script blocked, every slide shows and no control is offered', async ({ browser }) => {
  const off = await browser.newContext({ javaScriptEnabled: false });
  const blocked = await browser.newContext();
  await blocked.route(/\/js\/hero-carousel\.js$/, (route) => route.abort());
  for (const [what, ctx] of [['JavaScript off', off], ['carousel script blocked', blocked]] as const) {
    const page = await ctx.newPage();
    await page.goto(PAGE);
    const n = await page.locator(`${root} [data-hc-slide]`).count();
    await expect(page.locator(`${root} [data-hc-slide]:visible`), what).toHaveCount(n);
    await expect(page.locator(`${root} .hc-controls`), what).toBeHidden();
    await expect(page.locator(root), what).not.toHaveAttribute('data-ready', /.*/);
    await ctx.close();
  }
});

test('hero carousel — the slides share one place and the page does not change height when the photo changes, at a desktop, a tablet and a phone width', async ({ page }) => {
  for (const width of [1280, 768, 390]) {
    await page.setViewportSize({ width, height: 800 });
    await open(page);
    const ms = await interval(page);
    const n = await page.locator(`${root} [data-hc-slide]`).count();
    const height = () => page.evaluate(() => Math.round(document.documentElement.scrollHeight));
    const place = () => page.locator(`${root} .hc-slides`).evaluate((el) => Math.round(el.getBoundingClientRect().height));
    const shown = () => page.locator(`${root} .hc-slide[data-active] img`).evaluate((el) => Math.round(el.getBoundingClientRect().height));
    const first = [await height(), await place(), await shown()];
    // one place for all slides, not one under the other: the place is as tall as the photo on show
    expect(first[1], `${width} px: the place is one photo tall, not ${n}`).toBe(first[2]);
    // every photo has the place's shape, whatever shape the file has
    for (let i = 1; i < n; i++) {
      await page.clock.runFor(ms);
      expect(await active(page)).toEqual([i]);
      if (SWAP === 'fade') await page.waitForTimeout(1300);
      expect([await height(), await place(), await shown()], `page, place and photo height at ${width} px, photo ${i + 1}`).toEqual(first);
    }
  }
});

test('hero carousel — a slide not on show cannot be reached: not by the Tab key (its link), not in the accessibility tree', async ({ page }) => {
  await open(page);
  const slides = await slidesOf(page);
  test.skip(!slides.some((s) => s.href), 'no slide has an href: the page links no photo');
  const alts = slides.map((s) => (s.img.getAttribute('alt') ?? '').trim());
  test.skip(alts.some((a) => !a) || [0, 1].some((i) => alts.some((b, j) => i !== j && same(alts[i], b))), 'an alt text is empty, or the first or second is the same as another: the tree cannot tell the photos apart');
  // before and after a swap: tabbing through the page reaches the link of the slide on show, and of no other
  for (const on of [0, 1]) {
    if (on === 1) { await press(page, 1); expect(await active(page)).toEqual([1]); } // (the Tab key above stopped the rotation: a dot moves it on)
    const reached = await slideLinksInTabOrder(page);
    expect(reached, `slide ${on + 1} on show: the slide links reached by Tab`).toEqual(slides[on].href ? [on] : []);
    // the accessibility tree lists the alt text of the slide on show only
    expect(await inTree(page, alts[on]), 'the slide on show is in the tree').toBe(1);
    for (const [k, alt] of alts.entries()) if (k !== on) expect(await inTree(page, alt), `slide ${k + 1}, not on show, is not`).toBe(0);
  }
});

test('hero carousel — the photo links to its page, a dot does not, and the controls are not inside the link', async ({ page }) => {
  await open(page);
  const slides = await slidesOf(page);
  test.skip(!slides[0].href, 'the first slide has no href: the page links no photo');
  expect(await page.locator(`${root} .hc-controls`).evaluate((el) => !!el.closest('a')), 'the controls are not inside a link').toBe(false);
  const before = page.url();
  await press(page, 1);
  expect(page.url(), 'a dot leaves the address as it was').toBe(before);
  await dot(page, 0).click();
  expect(page.url()).toBe(before);
  const box = (await page.locator(`${root} .hc-slide[data-active] img`).boundingBox())!;
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 3); // on the photo, away from the dots
  await expect(page).toHaveURL(new RegExp(slides[0].href!.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '/?$'));
});

test('hero carousel — the dots sit on the bottom edge of the photo, are 32 px targets (44 px on touch), and axe finds nothing at A and AA in either theme', async ({ page, browser }) => {
  for (const scheme of ['light', 'dark'] as const) {
    // Real time here: axe works with timers of its own, which a frozen clock would never fire.
    // Reduced motion keeps the carousel still, so the state of the dots does not change while they are measured.
    await open(page, { reduced: true, scheme, frozen: false });
    const photo = (await page.locator(`${root} .hc-slide[data-active] img`).boundingBox())!;
    const n = await page.locator(`${root} .hc-dot`).count();
    for (let i = 0; i < n; i++) {
      const box = (await dot(page, i).boundingBox())!;
      expect(box.width, `dot ${i} width`).toBeGreaterThanOrEqual(32);
      expect(box.height, `dot ${i} height`).toBeGreaterThanOrEqual(32);
      expect(box.y, `dot ${i} is on the photo`).toBeGreaterThanOrEqual(photo.y + photo.height - 3 * 44);
      expect(box.y + box.height, `dot ${i} is on the photo`).toBeLessThanOrEqual(photo.y + photo.height);
      const c = await dot(page, i).evaluate((el) => { const cs = getComputedStyle(el, '::before'); return { border: cs.borderTopColor, width: cs.borderTopWidth, current: el.getAttribute('aria-current') }; });
      expect(c.border, `dot ${i}: a white circle`).toBe('rgb(255, 255, 255)');
      // under forced colours the fill is replaced by the system's; the border width is what still tells the photo on show from the others
      expect(c.width, `${scheme} dot ${i}: border width`).toBe(c.current ? '5px' : '1px');
    }
    // the pill behind the controls: white on it is at least 4.5:1 (the bar for the small Pause text) even where the photo behind it is pure white
    const pill = await page.locator(`${root} .hc-controls`).evaluate((el) => getComputedStyle(el).backgroundColor);
    const [r, g, b, a = 1] = (pill.match(/[\d.]+/g) ?? []).map(Number);
    expect(contrast(1, lum([r * a + 255 * (1 - a), g * a + 255 * (1 - a), b * a + 255 * (1 - a)])), `${scheme}: white on the pill over a white photo`).toBeGreaterThanOrEqual(4.5);
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice']).analyze();
    expect(JSON.stringify(results.violations.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length }))), `axe, ${scheme}`).toBe('[]');
  }
  // a phone: touch targets of 44 px, and no sideways scroll
  const phone = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
  const p = await phone.newPage();
  await p.goto(PAGE);
  await expect(p.locator(root)).toHaveAttribute('data-ready', '');
  const n = await p.locator(`${root} .hc-dot`).count();
  for (let i = 0; i < n; i++) {
    const box = (await dot(p, i).boundingBox())!;
    expect(box.width, `phone dot ${i} width`).toBeGreaterThanOrEqual(44);
    expect(box.height, `phone dot ${i} height`).toBeGreaterThanOrEqual(44);
  }
  expect(await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth), 'no horizontal scroll on a phone').toBeLessThanOrEqual(0);
  await phone.close();
});

// Pixels, not styles: the page as rendered, the photo behind the dots included. A pale part of a
// photo is what made the pill necessary; the CI page therefore uses a pale and a dark photo.
test('hero carousel — rendered over every photo, at three widths, the dot on show is white on the pill and the pill is not the photo', async ({ page }) => {
  for (const [w, h] of [[1280, 800], [390, 844], [1920, 1080]]) {
    await page.setViewportSize({ width: w, height: h });
    await open(page, { reduced: true, frozen: false });
    const n = await page.locator(`${root} .hc-dot`).count();
    for (let i = 0; i < n; i++) {
      await press(page, i);
      await expect.poll(() => active(page)).toEqual([i]);
      await decoded(page);
      const pill = (await page.locator(`${root} .hc-controls`).boundingBox())!;
      const d = (await dot(page, i).boundingBox())!;
      const clip = { x: pill.x, y: pill.y, width: pill.width, height: pill.height };
      const [centre, edge] = await pixelsAt(page, clip, [[Math.round(d.x - pill.x + d.width / 2), Math.round(d.y - pill.y + d.height / 2)], [3, Math.round(pill.height / 2)]]);
      expect(contrast(lum(centre), lum(edge)), `${w} px, photo ${i + 1}: the dot on show against the pill (${centre} on ${edge})`).toBeGreaterThanOrEqual(3);
    }
  }
});

test('hero carousel — under forced colours the dots are drawn on the photo, the dot on show differs from the others, and a focused dot shows a ring', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce', forcedColors: 'active' });
  await page.goto(PAGE);
  await page.waitForLoadState('load');
  await expect(page.locator(root)).toHaveAttribute('data-ready', '');
  await page.locator(root).scrollIntoViewIfNeeded();
  await decoded(page);
  // the photo out of the way, so that the dots are compared on the plain page and not on whatever lies behind each one
  await page.addStyleTag({ content: `${root} .hc-slides { visibility: hidden !important; }` });
  // the centre of each dot as drawn: the dot on show must look clearly different from the others (a few levels of grey is not enough)
  const centres = async () => {
    const pill = (await page.locator(`${root} .hc-controls`).boundingBox())!;
    const n = await page.locator(`${root} .hc-dot`).count();
    const points: [number, number][] = [];
    for (let i = 0; i < n; i++) { const d = (await dot(page, i).boundingBox())!; points.push([Math.round(d.x - pill.x + d.width / 2), Math.round(d.y - pill.y + d.height / 2)]); }
    return pixelsAt(page, { x: pill.x, y: pill.y, width: pill.width, height: pill.height }, points);
  };
  for (const k of [0, 1]) {
    await press(page, k);
    await expect.poll(() => active(page)).toEqual([k]);
    const c = await centres();
    for (let i = 0; i < c.length; i++) {
      if (i !== k) expect(contrast(lum(c[k]), lum(c[i])), `photo ${k + 1} on show: its dot against the dot of photo ${i + 1} (${c[k]} and ${c[i]})`).toBeGreaterThanOrEqual(3);
    }
  }
  await page.keyboard.press('Tab');
  const ring = async () => { const b = (await dot(page, 0).boundingBox())!; return page.screenshot({ clip: { x: b.x, y: b.y, width: b.width, height: b.height } }); };
  const before = await ring();
  await dot(page, 0).focus();
  expect((await ring()).equals(before), 'a focused dot shows a ring').toBe(false);
});

// What a page does during a stretch of time, with the carousel rotating or (reduced motion) standing still:
// the cross-origin requests it makes and what it adds to cookies and storage.
async function observe(page: Page, reduced: boolean) {
  await open(page, { reduced });
  const ms = await interval(page);
  const origin = new URL(page.url()).origin;
  const state = () => page.evaluate(() => ({ cookie: document.cookie, local: Object.keys(localStorage).sort(), session: Object.keys(sessionStorage).sort() }));
  const before = await state();
  const requests: string[] = [];
  page.on('request', (r) => requests.push(r.url()));
  await page.clock.runFor(3 * ms + 2000);
  return { before, after: await state(), foreign: requests.filter((u) => !u.startsWith('data:') && new URL(u).origin !== origin) };
}
test('hero carousel — rotating adds nothing to what the same page does standing still: no cookie, no storage entry, no request to another origin', async ({ page, browser }) => {
  // the baseline: the same page, the same stretch of time, with the carousel standing still (reduced motion)
  const still = await observe(page, true);
  const ctx = await browser.newContext();
  const rotating = await observe(await ctx.newPage(), false);
  await ctx.close();
  expect(rotating.after, 'storage after rotating is storage after standing still').toEqual(still.after);
  expect(rotating.foreign.filter((u) => !still.foreign.includes(u)), 'requests to another origin only while rotating').toEqual([]);
});

test('hero carousel — the script is a file of the site\'s own: no inline script is needed (a strict script-src \'self\' holds)', async ({ page }) => {
  await open(page);
  const inline = await page.evaluate(() => Array.from(document.querySelectorAll('script')).filter((s) => !s.src && /hero-carousel|data-hero-carousel/.test(s.textContent ?? '')).length);
  expect(inline, 'no inline script of the carousel').toBe(0);
  await expect(page.locator('script[src="/js/hero-carousel.js"]')).toHaveCount(1);
});

test('hero carousel — swap "instant": the photo changes at once, no transition runs', async ({ page }) => {
  test.skip(SWAP !== 'instant', 'this page uses swap "fade"');
  await open(page);
  const ms = await interval(page);
  await page.clock.runFor(ms);
  expect(await active(page)).toEqual([1]);
  const t = await page.locator(`${root} .hc-slide`).evaluateAll((els) => els.map((el) => getComputedStyle(el).transitionDuration));
  expect(t.every((d) => d === '0s'), `no transition on any slide: ${t.join(', ')}`).toBe(true);
  expect(await page.locator(`${root} .hc-slide[data-active]`).evaluate((el) => getComputedStyle(el).opacity), 'the photo on show is fully there at once').toBe('1');
});

const opacities = (page: Page) => page.locator(`${root} .hc-slide`).evaluateAll((els) => els.map((el) => Number(getComputedStyle(el).opacity)));
// The opacities of a settled carousel with slide `i` on show: 1 for it, 0 for every other.
const settled = (page: Page, i: number) => page.locator(`${root} .hc-slide`).count().then((n) => Array.from({ length: n }, (_, k) => (k === i ? 1 : 0)));
test('hero carousel — swap "fade": a frame part-way shows both photos between 0 and 1, it completes in about a second, and a dot mid-fade shows its photo at once', async ({ page }) => {
  test.skip(SWAP !== 'fade', 'this page uses swap "instant"');
  await open(page, { reduced: false });
  const ms = await interval(page);
  await page.clock.runFor(ms);
  expect(await active(page), 'the slide on show changes at once, the fade is in the CSS').toEqual([1]);
  // the browser runs the transition on real time: read it as it goes
  let part = false;
  const t0 = Date.now();
  while (Date.now() - t0 < 900) {
    const o = await opacities(page);
    if (o[0] > 0.02 && o[0] < 0.98 && o[1] > 0.02 && o[1] < 0.98) { part = true; break; }
    await page.waitForTimeout(40);
  }
  expect(part, 'a frame part-way: both photos at an opacity strictly between 0 and 1').toBe(true);
  await expect.poll(() => opacities(page), { timeout: 3000, message: 'the fade completes: the first photo gone, the second there' }).toEqual(await settled(page, 1));
  // a dot pressed mid-fade shows its photo at once (the slide on show changes immediately), and the fade settles
  const n = await page.locator(`${root} [data-hc-slide]`).count();
  await page.clock.runFor(ms); // the next swap starts a new fade ...
  expect(await active(page)).toEqual([2 % n]);
  await press(page, 0); // ... and a dot is pressed in the middle of it
  expect(await active(page), 'at once').toEqual([0]);
  await expect.poll(() => opacities(page), { timeout: 3000 }).toEqual(await settled(page, 0));
});

// Waits, on the real clock, until a fade is part-way: the slide that is going and the one that is coming both at an opacity between 0.02 and 0.98.
async function untilMidFade(page: Page) {
  await expect.poll(async () => { const o = await opacities(page); return o.filter((v) => v > 0.02 && v < 0.98).length >= 2; }, { timeout: 2000, intervals: [20, 20, 40] }).toBe(true);
}
test('hero carousel — swap "fade" with pause mode "button": a pause pressed in the middle of a fade leaves one settled, correct photo', async ({ page }) => {
  test.skip(SWAP !== 'fade' || PAUSE !== 'button', 'needs swap "fade" and pause mode "button"');
  await open(page, { reduced: false });
  const ms = await interval(page);
  await page.clock.runFor(ms);
  await untilMidFade(page); // a fade is under way
  await toggle(page).click();
  await page.clock.runFor(5 * ms);
  expect(await active(page)).toEqual([1]);
  await expect.poll(() => opacities(page), { timeout: 3000 }).toEqual(await settled(page, 1));
  // and while it settled, the photo that went is out of reach
  expect(await slideLinksInTabOrder(page), 'no link of a slide that went is reachable').not.toContain(0);
});

test('hero carousel — swap "fade": in the middle of a fade (confirmed by the opacities, before and after) the photo that is going cannot be focused and is not in the accessibility tree', async ({ page }) => {
  test.skip(SWAP !== 'fade', 'this page uses swap "instant"');
  const slides = await slidesOf(page);
  const alts = slides.map((s) => (s.img.getAttribute('alt') ?? '').trim());
  test.skip(!alts[0] || !alts[1] || same(alts[0], alts[1]), 'the first two alt texts are empty or the same: the tree cannot tell the two photos apart');
  await open(page, { reduced: false });
  // a fade of ten seconds, so that everything below happens inside it, on a machine of any speed
  await page.addStyleTag({ content: `${root} .hc-slide { transition-duration: 10s !important; }` });
  const ms = await interval(page);
  await page.clock.runFor(ms);
  expect(await active(page)).toEqual([1]);
  await untilMidFade(page);
  // from the first dot backwards through the carousel: the real Shift+Tab, the slide links it lands on
  await dot(page, 0).focus();
  const landed: number[] = [];
  for (let i = 0; i < 4; i++) {
    await page.keyboard.press('Shift+Tab');
    landed.push(await page.evaluate(() => { const a = document.activeElement?.closest('[data-hc-slide] a'); return a ? Number((a.closest('[data-hc-slide]') as HTMLElement).dataset.hcSlide) : -1; }));
  }
  const coming = await inTree(page, alts[1]);
  const going = await inTree(page, alts[0]);
  await untilMidFade(page); // still part-way: everything above was read inside the fade
  // the focus check means something only when both photos link: then Shift+Tab must reach the one coming in and never the one going
  if (slides[0].href && slides[1].href) {
    expect(landed, 'mid-fade: focus does land on the link of the photo coming in').toContain(1);
    expect(landed.filter((k) => k >= 0 && k !== 1), 'mid-fade: focus never lands on the link of the photo that is going, or of any other not coming in').toEqual([]);
  }
  expect(coming, 'mid-fade: the photo coming in is in the tree').toBe(1);
  expect(going, 'mid-fade: the photo that is going is not').toBe(0);
  // keyboard focus entered the carousel: the rotation stopped (one interval, not a whole lap), and it says so
  await page.clock.runFor(ms);
  expect(await active(page), 'focus stopped the rotation').toEqual([1]);
  await expect(page.locator(`${root} .hc-slides`), 'stopped: the photo area is a polite live region').toHaveAttribute('aria-live', 'polite');
});

test('hero carousel — swap "fade" with reduced motion: no transition at all', async ({ page }) => {
  test.skip(SWAP !== 'fade', 'this page uses swap "instant"');
  await open(page, { reduced: true });
  await dot(page, 1).click();
  const t = await page.locator(`${root} .hc-slide`).evaluateAll((els) => els.map((el) => getComputedStyle(el).transitionDuration));
  expect(t.every((d) => d === '0s'), `no transition on any slide: ${t.join(', ')}`).toBe(true);
  expect(await opacities(page), 'settled at once').toEqual(await settled(page, 1));
});
