import { test, expect } from '@playwright/test';
import { PAGES } from './_helpers';

// Phones must not download images far bigger than they can show (website-qa, "Performance").
// Each page loads as Lighthouse's phone (412px, 1.75x) and is scrolled to the end, so lazy
// images load; every raster the page itself downloads is judged, CSS backgrounds and masks
// included (Lighthouse does not size those). A file fails when it is wider than a 3x phone could use and
// a copy that wide saves an estimated 4 KiB, when it is downloaded but not shown (hidden ones
// under 4 KiB pass), and when the test cannot work out how wide it is drawn. A file used only
// as a border image, cursor or shape-outside is not judged by width; the log names it.
const VIEW = { width: 412, height: 823 };
const RATIO = 1.75;
const MOST = 3 * 1.1;      // a 3x phone, with room for one up to 453 CSS px wide
const FLOOR = 4096;        // bytes; Lighthouse's own floor for an image saving
const BUDGET = 20_000;     // ms for scrolling and settling; the test's own timeout is set above it

// A user of an image: the box it shows in, and how it is fitted there. For `fit`, `size` is an
// object-fit value or `own` (drawn at the file's own size); for `bg`, a background-size or
// mask-size layer with its lengths in px; for `named`, the CSS property.
type User = { url: string; kind: 'fit' | 'bg' | 'named'; w: number; h: number; size: string; hidden: boolean };

// Runs in the page: every element using an image URL right now.
function usersNow(): User[] {
  const out: User[] = [];
  const abs = (u: string) => new URL(u, location.href).href;
  // Computed styles write each URL as url("..."), with " and \ escaped inside.
  const urls = (v: string) => [...v.matchAll(/url\(\s*"((?:[^"\\]|\\.)*)"\s*\)/g)].map((m) => abs(m[1].replace(/\\(.)/g, '$1')));
  // A list split at its top level only: "linear-gradient(a, b), url(x)" is two layers at ',',
  // and "calc(100% - 10px) auto" two words at ' '.
  const split = (v: string, sep: string) => {
    const parts: string[] = [];
    let depth = 0, start = 0, quoted = false;
    for (let i = 0; i < v.length; i++) {
      const c = v[i];
      if (quoted) { if (c === '\\') i++; else if (c === '"') quoted = false; }
      else if (c === '"') quoted = true;
      else if (c === '(') depth++;
      else if (c === ')') depth--;
      else if (c === sep && depth === 0) { parts.push(v.slice(start, i).trim()); start = i + 1; }
    }
    parts.push(v.slice(start).trim());
    return parts.filter(Boolean);
  };
  // A background-size layer in px: a hidden probe box the size of the layer's positioning area
  // works out each % or calc() as width (first word) or height (second); a word it cannot take
  // is left as is. `all: initial` keeps the site's own CSS (a padding or max-width on every div)
  // off the probe, and its computed size, unlike its rect, ignores transforms.
  const PLAIN = 'all: initial; display: block; box-sizing: content-box';
  let probe: HTMLElement | undefined;
  const inPx = (layer: string, w: number, h: number) => {
    if (layer === 'cover' || layer === 'contain') return layer;
    if (!probe) {
      probe = document.createElement('div');
      probe.style.cssText = `${PLAIN}; position: absolute; left: 0; top: 0; visibility: hidden`;
      probe.append(document.createElement('div'));
      document.body.append(probe);
    }
    probe.style.width = `${w}px`;
    probe.style.height = `${h}px`;
    const child = probe.firstElementChild as HTMLElement;
    return split(layer, ' ').map((v, i) => {
      if (v === 'auto' || /^[\d.]+px$/.test(v)) return v;
      const side = i ? 'height' : 'width';
      child.style.cssText = PLAIN;
      child.style[side] = v;
      return child.style[side] ? getComputedStyle(child)[side] : v;
    }).join(' ');
  };
  const els = Array.from(document.querySelectorAll('*'));   // taken before the probe joins the page
  for (const img of Array.from(document.images)) {
    if (!img.currentSrc) continue;
    const r = img.getBoundingClientRect();
    const cs = getComputedStyle(img);
    out.push({ url: abs(img.currentSrc), kind: 'fit', w: r.width, h: r.height, size: cs.objectFit, hidden: cs.visibility !== 'visible' });
  }
  for (const v of Array.from(document.querySelectorAll('video[poster]'))) {
    const r = v.getBoundingClientRect();
    const cs = getComputedStyle(v);
    out.push({ url: abs(v.getAttribute('poster')!), kind: 'fit', w: r.width, h: r.height, size: cs.objectFit, hidden: cs.visibility !== 'visible' });
  }
  for (const el of els) {
    for (const pseudo of [null, '::before', '::after']) {
      const cs = getComputedStyle(el, pseudo);
      if (pseudo && (cs.content === 'none' || cs.content === 'normal')) continue;
      const host = el.getBoundingClientRect();
      const sum = (...props: string[]) => props.reduce((t, p) => t + (parseFloat(cs.getPropertyValue(p)) || 0), 0);
      const bx = sum('border-left-width', 'border-right-width'), by = sum('border-top-width', 'border-bottom-width');
      const padX = sum('padding-left', 'padding-right'), padY = sum('padding-top', 'padding-bottom');
      // The border box. A pseudo-element has no rect of its own; its used width/height are in the style.
      const grow = pseudo && cs.boxSizing === 'content-box';
      const w = pseudo && cs.width.endsWith('px') ? parseFloat(cs.width) + (grow ? bx + padX : 0) : host.width;
      const h = pseudo && cs.height.endsWith('px') ? parseFloat(cs.height) + (grow ? by + padY : 0) : host.height;
      const hidden = cs.visibility !== 'visible';
      // The box a layer's % sizes refer to, from its background-origin or mask-origin.
      const area = (origin: string) => origin === 'border-box' ? [w, h]
        : origin === 'content-box' ? [w - bx - padX, h - by - padY] : [w - bx, h - by];
      // Sizes and origins line up with every layer, gradients included, and repeat from the start
      // when the list is shorter (as CSS does). An image-set() layer names several files: all count.
      for (const [images, size, origin] of [['background-image', 'background-size', 'background-origin'], ['mask-image', 'mask-size', 'mask-origin']]) {
        const sizes = split(cs.getPropertyValue(size), ',');
        const origins = split(cs.getPropertyValue(origin), ',');
        split(cs.getPropertyValue(images), ',').forEach((layer, i) => {
          const [aw, ah] = area(origins[i % origins.length] ?? '');
          for (const url of urls(layer)) out.push({ url, kind: 'bg', w: aw, h: ah, size: inPx(sizes[i % sizes.length] ?? '', aw, ah), hidden });
        });
      }
      // A list marker and a pseudo-element's content image are drawn at the file's own size; an
      // element's own content image fills its box like an <img>.
      for (const [prop, size] of [['list-style-image', 'own'], ['content', pseudo ? 'own' : 'fill']]) {
        for (const url of urls(cs.getPropertyValue(prop))) out.push({ url, kind: 'fit', w, h, size, hidden });
      }
      for (const prop of ['border-image-source', 'cursor', 'shape-outside']) {
        for (const url of urls(cs.getPropertyValue(prop))) out.push({ url, kind: 'named', w, h, size: prop, hidden });
      }
    }
  }
  probe?.remove();
  return out;
}

// The width a file is shown at, from its box, its fit and its own size (fw x fh): for `none`,
// the part its box shows; for `own` and an auto background, the whole file. NaN is a size the
// test cannot read; the caller fails the file.
function drawnWidth(u: User, fw: number, fh: number): number {
  const aspect = fw / fh;
  const contain = Math.min(u.w, u.h * aspect);
  if (u.size === 'cover') return Math.max(u.w, u.h * aspect);
  if (u.size === 'contain') return contain;
  if (u.kind === 'fit') return ({ fill: u.w, none: Math.min(fw, u.w), 'scale-down': Math.min(fw, contain), own: fw } as Record<string, number>)[u.size] ?? NaN;
  const [x, y = 'auto'] = u.size.split(' ');
  const px = (v: string) => (/^[\d.]+px$/.test(v) ? parseFloat(v) : NaN);
  if (x !== 'auto') return px(x);
  if (y !== 'auto') return px(y) * aspect;
  return fw;
}

for (const path of PAGES) {
  test(`phone images — ${path} downloads no image far bigger than a phone shows`, async ({ browser, baseURL }) => {
    test.setTimeout(BUDGET + 40_000);   // room for loading the page and judging after the budget
    // hasTouch gives a phone's media queries (pointer: coarse, hover: none). Not isMobile: its
    // 980px starting viewport lets a desktop-only preload (`media="(min-width: 720px)"`) fetch.
    const context = await browser.newContext({ baseURL, viewport: VIEW, deviceScaleFactor: RATIO, hasTouch: true });
    try {
      const page = await context.newPage();
      const sizes = new Map<string, number>();
      const reads: Promise<void>[] = [];
      // Image requests started and not yet finished, of any kind (img, CSS, preload).
      let pending = 0;
      const done = (r: { resourceType(): string }) => { if (r.resourceType() === 'image') pending--; };
      page.on('request', (r) => { if (r.resourceType() === 'image') pending++; });
      page.on('requestfinished', done);
      page.on('requestfailed', done);
      page.on('response', (r) => {
        const type = (r.headers()['content-type'] ?? '').split(';')[0].trim();
        // Rasters from this page's own document; SVG is not a raster, iframes are not the site's.
        if (!type.startsWith('image/') || type === 'image/svg+xml' || r.frame() !== page.mainFrame()) return;
        // A failed read marks the file only when no read of it worked.
        reads.push(r.body().then((b) => { sizes.set(r.url(), Math.max(sizes.get(r.url()) || 0, b.length)); },
          () => { if (!sizes.has(r.url())) sizes.set(r.url(), NaN); }));
      });
      await page.goto(path, { waitUntil: 'load' });
      expect(await page.evaluate(() => matchMedia('(pointer: coarse)').matches && matchMedia('(hover: none)').matches),
        'the browser does not match a phone\'s media queries').toBe(true);

      // A screen at a time, users noted at each stop (a carousel may swap a file out), until
      // the bottom is reached and stays there once no image request is left pending: the
      // height is read again each time, as a page may grow. Every wait counts against BUDGET.
      const seen: User[] = [];
      const deadline = Date.now() + BUDGET;
      const left = () => Math.max(1, deadline - Date.now());
      const busy = `${path} did not settle at its end within ${BUDGET / 1000} s (still growing, very long, or images still loading)`;
      const atEnd = () => page.evaluate(() => scrollY + innerHeight >= document.documentElement.scrollHeight - 1);
      for (let screen = 0; ; screen++) {
        expect(Date.now() < deadline, busy).toBe(true);
        await page.evaluate((top) => window.scrollTo({ top, behavior: 'instant' }), screen * VIEW.height);
        await page.waitForTimeout(150);
        seen.push(...await page.evaluate(usersNow));
        if (!await atEnd()) continue;
        await page.waitForTimeout(Math.min(500, left()));
        await expect.poll(() => pending, { message: busy, timeout: left() }).toBe(0);
        seen.push(...await page.evaluate(usersNow));
        if (await atEnd()) break;
      }
      await Promise.all(reads);

      // Every file a preload names, in its href or its imagesrcset.
      const preloads = new Set(await page.locator('link[rel~="preload" i][as="image" i]').evaluateAll((els) => els.flatMap((e) =>
        [e.getAttribute('href'), ...(e.getAttribute('imagesrcset') ?? '').split(',').map((c) => c.trim().split(/\s+/)[0])]
          .filter((u): u is string => !!u).map((u) => new URL(u, location.href).href))));
      // The file's own width: a srcset `w` descriptor scales img.naturalWidth, so decode it alone.
      const real = await page.evaluate(async (list) => Object.fromEntries(await Promise.all(list.map(async (u) => {
        const i = new Image(); i.src = u;
        try { await i.decode(); return [u, [i.naturalWidth, i.naturalHeight]]; } catch { return [u, [0, 0]]; }
      }))), [...sizes.keys()]);

      const problems: string[] = [];
      const small: string[] = [];
      const named: string[] = [];
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
        if (Number.isNaN(bytes) || !fw || !fh) { problems.push(`${name}: could not read its size or decode it`); continue; }
        const sized = users.filter((u) => u.kind !== 'named' && !u.hidden && u.w > 0 && u.h > 0);
        if (!sized.length) {
          const as = users.filter((u) => u.kind === 'named' && !u.hidden).map((u) => u.size);
          if (as.length) named.push(`${name} (${[...new Set(as)].join(', ')})`);
          else if (bytes >= FLOOR) problems.push(`${name} is downloaded but hidden at 412px (${Math.round(bytes / 1024)} KB): lazy-load it, or serve it only where it shows`);
          else small.push(name);
          continue;
        }
        const widths = sized.map((u) => drawnWidth(u, fw, fh));
        const unknown = [...new Set(sized.filter((u, i) => !Number.isFinite(widths[i])).map((u) => u.size || '(none)'))];
        if (unknown.length) {
          problems.push(`${name}: the test cannot work out how wide it is drawn (size ${unknown.join('; ')}); give it a size in px, %, calc(), auto, cover or contain`);
          continue;
        }
        judged++;
        const shown = Math.max(...widths);
        const limit = shown * MOST;
        // An estimate by pixel area; the real saving can be smaller, so a file near the floor
        // may fail for a little less than 4 KiB.
        const saving = bytes * (1 - (limit / fw) ** 2);
        if (fw > limit && saving >= FLOOR) {
          problems.push(`${name} is ${fw}px wide, shown at ${Math.round(shown)}px: a 3x phone uses at most ${Math.round(limit)}px; a copy that wide saves an estimated ${Math.round(saving / 1024)} KB`);
        }
      }
      console.log(`phone images — ${path}: ${judged} judged by width${small.length ? `; hidden and under 4 KiB: ${small.join(', ')}` : ''}${named.length ? `; not judged: ${named.join(', ')}` : ''}`);
      expect(problems, 'make a smaller copy (and a srcset) or fix the preload; website-qa "Performance" has the fixes').toEqual([]);
    } finally {
      await context.close();
    }
  });
}
