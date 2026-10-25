import { test, expect } from '@playwright/test';
import { PAGES } from './_helpers';

// Phones must not download images far bigger than they can show (website-qa, "Performance").
// Each page loads as Lighthouse's phone (412px, 1.75x) and is scrolled to the end, so lazy
// images load; every raster it downloads is judged, CSS backgrounds included (Lighthouse does
// not size those). A file fails when it is wider than a 3x phone could use and a copy that
// wide saves at least 4 KiB, and when it is downloaded but not shown.
const VIEW = { width: 412, height: 823 };
const RATIO = 1.75;
const MOST = 3 * 1.1;      // a 3x phone, with room for one up to 453 CSS px wide
const FLOOR = 4096;        // bytes; Lighthouse's own floor for an image saving
const MAX_SCREENS = 200;   // a page still growing after this many screens is refused

// A user of an image: the box it shows in, and how it is fitted there (`size` is the
// background-size or object-fit value, worked out once the file's own size is known).
type User = { url: string; kind: 'img' | 'bg' | 'poster' | 'other'; w: number; h: number; size: string };

// Runs in the page: every element using an image URL right now.
function usersNow(): User[] {
  const out: User[] = [];
  const abs = (u: string) => new URL(u, location.href).href;
  // Computed styles write each URL as url("..."), with " and \ escaped inside.
  const urls = (v: string) => [...v.matchAll(/url\(\s*"((?:[^"\\]|\\.)*)"\s*\)/g)].map((m) => abs(m[1].replace(/\\(.)/g, '$1')));
  // A comma list split at its top level only: "linear-gradient(a, b), url(x)" is two layers.
  const layers = (v: string) => {
    const parts: string[] = [];
    let depth = 0, start = 0, quoted = false;
    for (let i = 0; i < v.length; i++) {
      const c = v[i];
      if (quoted) { if (c === '\\') i++; else if (c === '"') quoted = false; }
      else if (c === '"') quoted = true;
      else if (c === '(') depth++;
      else if (c === ')') depth--;
      else if (c === ',' && depth === 0) { parts.push(v.slice(start, i).trim()); start = i + 1; }
    }
    parts.push(v.slice(start).trim());
    return parts;
  };
  for (const img of Array.from(document.images)) {
    if (!img.currentSrc) continue;
    const r = img.getBoundingClientRect();
    out.push({ url: abs(img.currentSrc), kind: 'img', w: r.width, h: r.height, size: getComputedStyle(img).objectFit });
  }
  for (const v of Array.from(document.querySelectorAll('video[poster]'))) {
    const r = v.getBoundingClientRect();
    out.push({ url: abs(v.getAttribute('poster')!), kind: 'poster', w: r.width, h: r.height, size: 'contain' });
  }
  for (const el of Array.from(document.querySelectorAll('*'))) {
    for (const pseudo of [null, '::before', '::after']) {
      const cs = getComputedStyle(el, pseudo);
      if (pseudo && (cs.content === 'none' || cs.content === 'normal')) continue;
      const host = el.getBoundingClientRect();
      // A pseudo-element has no rect of its own; its used width/height are in the style.
      const w = pseudo && cs.width.endsWith('px') ? parseFloat(cs.width) : host.width;
      const h = pseudo && cs.height.endsWith('px') ? parseFloat(cs.height) : host.height;
      // Sizes line up with every layer, gradients included, and repeat from the start when
      // the list is shorter (as CSS does). An image-set() layer names several files: all count.
      const sizes = layers(cs.backgroundSize);
      layers(cs.backgroundImage).forEach((layer, i) => {
        for (const url of urls(layer)) out.push({ url, kind: 'bg', w, h, size: sizes[i % sizes.length] });
      });
      for (const prop of ['mask-image', 'border-image-source', 'list-style-image', 'content', 'cursor', 'shape-outside']) {
        for (const url of urls(cs.getPropertyValue(prop))) out.push({ url, kind: 'other', w, h, size: '' });
      }
    }
  }
  return out;
}

// The width a file is drawn at, from its box, its fit and its own aspect (fw / fh).
function drawnWidth(u: User, fw: number, fh: number): number {
  const aspect = fw / fh;
  if (u.size === 'cover') return Math.max(u.w, u.h * aspect);
  if (u.size === 'contain') return Math.min(u.w, u.h * aspect);
  if (u.kind !== 'bg') return u.w;   // object-fit fill, none, scale-down: the box
  const [x, y = 'auto'] = u.size.split(/\s+/);
  const length = (v: string, of: number) => (v.endsWith('%') ? (parseFloat(v) / 100) * of : parseFloat(v));
  if (x !== 'auto') return length(x, u.w);
  if (y !== 'auto') return length(y, u.h) * aspect;
  return fw;                          // auto auto: drawn at the file's own size
}

for (const path of PAGES) {
  test(`phone images — ${path} downloads no image far bigger than a phone shows`, async ({ browser, baseURL }) => {
    // hasTouch gives a phone's media queries (pointer: coarse, hover: none). Not isMobile: its
    // 980px starting viewport lets a desktop-only preload (`media="(min-width: 720px)"`) fetch.
    const context = await browser.newContext({ baseURL, viewport: VIEW, deviceScaleFactor: RATIO, hasTouch: true });
    try {
      const page = await context.newPage();
      const sizes = new Map<string, number>();
      const reads: Promise<void>[] = [];
      page.on('response', (r) => {
        const type = (r.headers()['content-type'] ?? '').split(';')[0].trim();
        // Rasters from this page's own document; SVG is not a raster, iframes are not the site's.
        if (!type.startsWith('image/') || type === 'image/svg+xml' || r.frame() !== page.mainFrame()) return;
        reads.push(r.body().then((b) => { sizes.set(r.url(), Math.max(sizes.get(r.url()) ?? 0, b.length)); },
          () => { sizes.set(r.url(), NaN); }));
      });
      await page.goto(path, { waitUntil: 'load' });
      expect(await page.evaluate(() => matchMedia('(pointer: coarse)').matches && matchMedia('(hover: none)').matches),
        'the browser does not match a phone\'s media queries').toBe(true);

      // A screen at a time, users noted at each stop (a carousel may swap a file out), until
      // the bottom is reached; the height is read again each time, as a page may grow.
      const seen: User[] = [];
      for (let screen = 0; ; screen++) {
        expect(screen, `${path} was still growing after ${MAX_SCREENS} screens`).toBeLessThan(MAX_SCREENS);
        await page.evaluate((top) => window.scrollTo({ top, behavior: 'instant' }), screen * VIEW.height);
        await page.waitForTimeout(150);
        seen.push(...await page.evaluate(usersNow));
        const end = await page.evaluate(() => scrollY + innerHeight >= document.documentElement.scrollHeight - 1);
        if (end) break;
      }
      // Only images that started loading: a hidden lazy one (a dark-theme copy) never starts.
      await page.waitForFunction(() => Array.from(document.images).every((i) => i.complete || !i.currentSrc));
      const quiet = await page.waitForLoadState('networkidle', { timeout: 5000 }).then(() => true, () => false);
      seen.push(...await page.evaluate(usersNow));
      await Promise.all(reads);

      const preloads = new Set(await page.locator('link[rel="preload"][as="image"][href]').evaluateAll(
        (els) => els.map((e) => new URL(e.getAttribute('href')!, location.href).href)));
      // The file's own width: a srcset `w` descriptor scales img.naturalWidth, so decode it alone.
      const real = await page.evaluate(async (list) => Object.fromEntries(await Promise.all(list.map(async (u) => {
        const i = new Image(); i.src = u;
        try { await i.decode(); return [u, [i.naturalWidth, i.naturalHeight]]; } catch { return [u, [0, 0]]; }
      }))), [...sizes.keys()]);

      const problems: string[] = [];
      const listed: string[] = [];
      let judged = 0;
      for (const [url, bytes] of sizes) {
        const name = decodeURI(new URL(url).pathname);
        const [fw, fh] = real[url] as number[];
        const users = seen.filter((u) => u.url === url);
        if (!users.length) {
          problems.push(preloads.has(url)
            ? `${name} is preloaded and downloaded, but nothing on the page shows it at 412px (check the preload's media against the CSS breakpoint)`
            : `${name} was downloaded, but nothing on the page shows it`);
          continue;
        }
        if (Number.isNaN(bytes) || !fw || !fh) { problems.push(`${name}: could not read its size or decode it`); continue; }
        const sized = users.filter((u) => u.kind !== 'other' && u.w > 0 && u.h > 0);
        if (!sized.length) {
          if (users.some((u) => u.kind === 'other')) listed.push(`${name} (used by a CSS property not judged by width)`);
          else if (bytes >= FLOOR) problems.push(`${name} is downloaded but hidden at 412px (${Math.round(bytes / 1024)} KB): lazy-load it, or serve it only where it shows`);
          else listed.push(`${name} (hidden at 412px, under 4 KiB)`);
          continue;
        }
        judged++;
        const shown = Math.max(...sized.map((u) => drawnWidth(u, fw, fh)));
        const limit = shown * MOST;
        const saving = bytes * (1 - (limit / fw) ** 2);
        if (fw > limit && saving >= FLOOR) {
          problems.push(`${name} is ${fw}px wide, shown at ${Math.round(shown)}px: a 3x phone uses at most ${Math.round(limit)}px; a copy that wide saves about ${Math.round(saving / 1024)} KB`);
        }
      }
      console.log(`phone images — ${path}: ${judged} judged${listed.length ? `; not judged: ${listed.join(', ')}` : ''}${quiet ? '' : '; the network never went quiet for 500 ms'}`);
      expect(problems, 'make a smaller copy (and a srcset) or fix the preload; website-qa "Performance" has the fixes').toEqual([]);
    } finally {
      await context.close();
    }
  });
}
