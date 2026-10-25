import { test, expect } from '@playwright/test';
import { PAGES } from './_helpers';

// Phones must not download images far bigger than they can show (website-qa, "Performance").
// Each page loads as Lighthouse's phone (412px, 1.75x) and is scrolled to the end, so lazy
// images load. Every raster the page downloads is then judged against what displays it, CSS
// backgrounds included, which Lighthouse's own image check does not size at all.
// A file fails when it is wider than a 3x phone could use (1.1 × displayed width × 3) and
// cutting it to that width would save at least 4 KiB; and a file nothing on the page uses
// fails too (a preload whose `media` drifted from the CSS breakpoint does this).
const VIEW = { width: 412, height: 823 };
const RATIO = 1.75;
const MOST = 3 * 1.1;      // a 3x phone, with room for one up to 453 CSS px wide
const FLOOR = 4096;        // bytes; Lighthouse's own floor for an image saving

type User = { url: string; kind: 'img' | 'bg' | 'poster' | 'other'; w: number; h: number; cover: boolean; repeat: boolean };

// Runs in the page: every element using an image URL right now, with the box it shows in.
function usersNow(): User[] {
  const out: User[] = [];
  const abs = (u: string) => new URL(u, location.href).href;
  const urls = (v: string) => [...v.matchAll(/url\(\s*["']?([^"')]+)["']?\s*\)/g)].map((m) => abs(m[1]));
  // A comma list split at its top level only: "linear-gradient(a, b), url(x)" is two layers.
  const layers = (v: string) => {
    const parts: string[] = [];
    let depth = 0, start = 0;
    for (let i = 0; i < v.length; i++) {
      if (v[i] === '(') depth++;
      else if (v[i] === ')') depth--;
      else if (v[i] === ',' && depth === 0) { parts.push(v.slice(start, i).trim()); start = i + 1; }
    }
    parts.push(v.slice(start).trim());
    return parts;
  };
  for (const img of Array.from(document.images)) {
    if (!img.currentSrc) continue;
    const r = img.getBoundingClientRect();
    out.push({ url: abs(img.currentSrc), kind: 'img', w: r.width, h: r.height, cover: getComputedStyle(img).objectFit === 'cover', repeat: false });
  }
  for (const v of Array.from(document.querySelectorAll('video[poster]'))) {
    const r = v.getBoundingClientRect();
    out.push({ url: abs(v.getAttribute('poster')!), kind: 'poster', w: r.width, h: r.height, cover: false, repeat: false });
  }
  for (const el of Array.from(document.querySelectorAll('*'))) {
    for (const pseudo of [null, '::before', '::after']) {
      const cs = getComputedStyle(el, pseudo);
      if (pseudo && (cs.content === 'none' || cs.content === 'normal')) continue;
      const host = el.getBoundingClientRect();
      // A pseudo-element has no rect of its own; its used width/height are in the style.
      const w = pseudo && cs.width.endsWith('px') ? parseFloat(cs.width) : host.width;
      const h = pseudo && cs.height.endsWith('px') ? parseFloat(cs.height) : host.height;
      // One entry per background layer. Size and repeat line up with every layer, gradients
      // included, and repeat from the start when their lists are shorter (as CSS does).
      const sizes = layers(cs.backgroundSize);
      const repeats = layers(cs.backgroundRepeat);
      layers(cs.backgroundImage).forEach((layer, i) => {
        const [url] = urls(layer);
        if (!url) return;
        const size = sizes[i % sizes.length];
        const rep = repeats[i % repeats.length];
        out.push({ url, kind: 'bg', w, h, cover: size === 'cover', repeat: size !== 'cover' && rep !== 'no-repeat' });
      });
      for (const prop of ['mask-image', 'border-image-source', 'list-style-image', 'content', 'cursor', 'shape-outside']) {
        for (const url of urls(cs.getPropertyValue(prop))) out.push({ url, kind: 'other', w, h, cover: false, repeat: false });
      }
    }
  }
  return out;
}

for (const path of PAGES) {
  test(`phone images — ${path} downloads no image far bigger than a phone shows`, async ({ browser, baseURL }) => {
    // hasTouch gives a phone's media queries (pointer: coarse, hover: none). Not isMobile: its
    // 980px starting viewport lets a desktop-only preload (`media="(min-width: 720px)"`) fetch.
    const context = await browser.newContext({ baseURL, viewport: VIEW, deviceScaleFactor: RATIO, hasTouch: true });
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

    // Scroll a screen at a time, noting users at each stop: a carousel may swap a file out.
    const seen: User[] = [];
    const height = await page.evaluate(() => document.documentElement.scrollHeight);
    for (let y = 0; y <= height; y += VIEW.height) {
      await page.evaluate((top) => window.scrollTo(0, top), y);
      await page.waitForTimeout(150);
      seen.push(...await page.evaluate(usersNow));
    }
    // Only images that started loading: a hidden lazy one (a dark-theme copy) never starts.
    await page.waitForFunction(() => Array.from(document.images).every((i) => i.complete || !i.currentSrc));
    await page.waitForLoadState('networkidle');
    seen.push(...await page.evaluate(usersNow));
    await Promise.all(reads);

    const preloads = new Set(await page.locator('link[rel="preload"][as="image"][href]').evaluateAll(
      (els) => els.map((e) => new URL(e.getAttribute('href')!, location.href).href)));
    // The file's own width: a srcset `w` descriptor scales img.naturalWidth, so decode it alone.
    const real = await page.evaluate(async (list) => Object.fromEntries(await Promise.all(list.map(async (u) => {
      const i = new Image(); i.src = u;
      try { await i.decode(); return [u, [i.naturalWidth, i.naturalHeight]]; } catch { return [u, [0, 0]]; }
    }))), [...sizes.keys()]);
    await context.close();

    const problems: string[] = [];
    const listed: string[] = [];
    let judged = 0;
    for (const [url, bytes] of sizes) {
      const name = new URL(url).pathname;
      const [fw, fh] = real[url] as number[];
      const users = seen.filter((u) => u.url === url);
      if (!users.length) {
        problems.push(preloads.has(url)
          ? `${name} is preloaded and downloaded, but nothing on the page shows it at 412px (check the preload's media against the CSS breakpoint)`
          : `${name} was downloaded, but nothing on the page shows it`);
        continue;
      }
      if (Number.isNaN(bytes) || !fw) { problems.push(`${name}: could not read its size or decode it`); continue; }
      const sized = users.filter((u) => u.kind !== 'other' && !u.repeat && u.w > 0 && u.h > 0);
      if (!sized.length) {
        const why = users.some((u) => u.repeat) ? 'repeating background' : users.some((u) => u.kind === 'other') ? 'used by a CSS property not judged by width' : 'only zero-size users';
        listed.push(`${name} (${why})`);
        continue;
      }
      judged++;
      // With cover the file is drawn wider than its box when the box is taller than the file.
      const shown = Math.max(...sized.map((u) => (u.cover ? Math.max(u.w, (u.h * fw) / fh) : u.w)));
      const limit = shown * MOST;
      const saving = bytes * (1 - (limit / fw) ** 2);
      if (fw > limit && saving >= FLOOR) {
        problems.push(`${name} is ${fw}px wide, shown at ${Math.round(shown)}px: a 3x phone uses at most ${Math.round(limit)}px; a copy that wide saves about ${Math.round(saving / 1024)} KB`);
      }
    }
    console.log(`phone images — ${path}: ${judged} judged${listed.length ? `; not judged: ${listed.join(', ')}` : ''}`);
    expect(problems, 'make a smaller copy (and a srcset) or fix the preload; website-qa "Performance" has the fixes').toEqual([]);
  });
}
