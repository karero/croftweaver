import { test, expect, type Page } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { staleReasons } from '../scripts/make-icons.mjs';
import { SITE } from '../src/config';

// The seven icon files every site links, with the size each must have. Written out here, not read
// from scripts/make-icons.mjs, so a change to the script cannot change what this test asks for.
// It checks files, not pictures: an icon redrawn by hand in another colour passes.
type Icon = { path: string; linkedBy: 'icon' | 'apple' | 'manifest' | 'logo'; kind: 'svg' | 'ico' | 'png'; size?: number };
const ICONS: Icon[] = [
  { path: '/favicon.svg', linkedBy: 'icon', kind: 'svg' },
  { path: '/favicon.ico', linkedBy: 'icon', kind: 'ico', size: 32 },       // a 32-pixel frame among its entries
  { path: '/apple-touch-icon.png', linkedBy: 'apple', kind: 'png', size: 180 },
  { path: '/icon-192.png', linkedBy: 'manifest', kind: 'png', size: 192 },
  { path: '/icon-512.png', linkedBy: 'manifest', kind: 'png', size: 512 },
  { path: '/icon-maskable-512.png', linkedBy: 'manifest', kind: 'png', size: 512 },
  { path: '/images/logo.png', linkedBy: 'logo', kind: 'png', size: 512 },  // the logo the page's structured data names
];

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

// The size the browser itself decodes these bytes to, so a stub, a cut-off or an empty picture
// fails here as it would for a visitor. null when they do not decode.
const decodedSize = (page: Page, bytes: Buffer, type: string) =>
  page.evaluate(async ([b64, t]) => {
    try {
      const bitmap = await createImageBitmap(new Blob([Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))], { type: t }));
      return [bitmap.width, bitmap.height];
    } catch {
      return null;
    }
  }, [bytes.toString('base64'), type]);

// An SVG as an <img> shows it (createImageBitmap takes no SVG): its size once decoded, or null when
// it does not decode, as with a cut-off file. One with no width or height still has a size (Chromium
// gives a viewBox-only file 150 x 150, an empty <svg> 300 x 150): this checks the file, not the picture.
const svgSize = (page: Page, bytes: Buffer) =>
  page.evaluate(async (b64) => {
    const img = new Image();
    img.src = `data:image/svg+xml;base64,${b64}`;
    try {
      await img.decode();
      return [img.naturalWidth, img.naturalHeight];
    } catch {
      return null;
    }
  }, bytes.toString('base64'));

// SITE.url must be a web address with a host. `new URL('localhost:4321')` parses too, with the
// scheme 'localhost:' and no host, so the plain parse would let it through.
const isWebAddress = (text: string) => {
  try {
    const u = new URL(text);
    return /^https?:$/.test(u.protocol) && u.hostname !== '';
  } catch {
    return false;
  }
};

// A link's address as this test compares it: its path when it is on this site, its whole address
// when it is on another host, so it matches none of our files. `own` lists this site's addresses
// (the server under test, SITE.url); `base` only resolves a relative link and never makes a host ours.
const sitePath = (href: string, base: string, own: string[]) => {
  const url = new URL(href, base);
  return own.some((o) => new URL(o).origin === url.origin) ? url.pathname : url.href;
};

// What a link or manifest entry declares for a PNG's size (`sizes`), against the size the file decodes to.
// null when it is fine: nothing declared (both are optional), or exactly the one NxN size the file has.
const sizesProblem = (declared: string | null, size: number) => {
  if (declared === null || declared.trim() === '') return null;
  const tokens = declared.trim().toLowerCase().split(/\s+/);
  return tokens.length === 1 && tokens[0] === `${size}x${size}` ? null : `declares sizes="${declared}", but the file is ${size}x${size}`;
};

// Every logo the JSON-LD gives as a URL, at any depth and on a node of any type (Organization, a
// subtype such as LocalBusiness, or an array of types): a URL string, or the string url of an object
// such as an ImageObject. An empty one is skipped, and so is a logo given only as an @id.
const logoUrls = (value: unknown): string[] => {
  if (Array.isArray(value)) return value.flatMap(logoUrls);
  if (typeof value === 'string') return value ? [value] : [];
  const url = value && typeof value === 'object' ? (value as { url?: unknown }).url : undefined;
  return typeof url === 'string' && url ? [url] : [];
};
const logosIn = (node: unknown): string[] => {
  if (Array.isArray(node)) return node.flatMap(logosIn);
  if (!node || typeof node !== 'object') return [];
  return Object.entries(node).flatMap(([key, value]) => [...(key === 'logo' ? logoUrls(value) : []), ...logosIn(value)]);
};

test('icons — a link on another host is not one of this site\'s files', () => {
  const [home, live] = ['http://localhost:4400/', 'https://example.com'];
  const own = [home, live];
  expect(sitePath('/favicon.svg', home, own), 'a path').toBe('/favicon.svg');
  expect(sitePath('https://example.com/favicon.svg', home, own), 'the live address of this site').toBe('/favicon.svg');
  expect(sitePath('http://localhost:4400/favicon.svg', home, own), 'the server under test').toBe('/favicon.svg');
  expect(sitePath('https://cdn.example.net/favicon.svg', home, own), 'another host').toBe('https://cdn.example.net/favicon.svg');
  expect(sitePath('//cdn.example.net/favicon.svg', home, own), 'another host, no scheme').toBe('http://cdn.example.net/favicon.svg');
  // A manifest on another host does not make its icons ours, even when they are given as paths.
  const cdnManifest = 'https://cdn.example.net/site.webmanifest';
  expect(sitePath('/icon-192.png', cdnManifest, own), "a path in another host's manifest").toBe('https://cdn.example.net/icon-192.png');
  expect(sitePath('icon-512.png', cdnManifest, own), "a relative file in another host's manifest").toBe('https://cdn.example.net/icon-512.png');
  expect(sitePath('/icon-192.png', 'http://localhost:4400/site.webmanifest', own), "a path in this site's manifest").toBe('/icon-192.png');
});

test('icons — a declared size must be the size of the PNG', () => {
  expect(sizesProblem('192x192', 192), 'the size the file has').toBeNull();
  expect(sizesProblem(' 192X192 ', 192), 'case and spaces').toBeNull();
  expect(sizesProblem(null, 192), 'nothing declared').toBeNull();
  expect(sizesProblem('512x512', 192), 'another size').not.toBeNull();
  expect(sizesProblem('192x192 512x512', 192), 'a list: the file has one size').not.toBeNull();
  expect(sizesProblem('any', 192), 'any: a PNG has one size').not.toBeNull();
});

test('icons — SITE.url must be a web address with a host', () => {
  expect(isWebAddress('https://example.com'), 'a full address').toBe(true);
  expect(isWebAddress('http://localhost:4321'), 'a local address').toBe(true);
  expect(isWebAddress('localhost:4321'), 'a host and port with no scheme parses, but is not an address').toBe(false);
  expect(isWebAddress('example.com'), 'a bare host').toBe(false);
  expect(isWebAddress('ftp://example.com'), 'another scheme').toBe(false);
  expect(isWebAddress('https://'), 'no host').toBe(false);
  expect(isWebAddress(''), 'empty').toBe(false);
});

test('icons — the logo reader finds every logo the structured data names, and only those', () => {
  expect(logosIn({ '@type': 'Organization', logo: '/a.png' }), 'a URL').toEqual(['/a.png']);
  expect(logosIn({ '@type': ['Organization', 'LocalBusiness'], logo: { '@type': 'ImageObject', url: '/a.png' } }), 'an ImageObject on a node of two types').toEqual(['/a.png']);
  expect(logosIn({ '@graph': [{ '@type': 'WebSite', publisher: { '@type': 'Organization', logo: '/a.png' } }] }), 'a node nested in another').toEqual(['/a.png']);
  expect(logosIn({ logo: { url: '/outer.png', creator: { logo: '/a.png' } } }), "a logo inside a logo's ImageObject").toEqual(['/outer.png', '/a.png']);
  expect(logosIn({ logo: [['/a.png'], '/b.png'] }), 'arrays of URLs, at any depth').toEqual(['/a.png', '/b.png']);
  expect(logosIn({ logo: '' }), 'an empty URL is no logo').toEqual([]);
  expect(logosIn({ logo: { '@type': 'ImageObject' } }), 'nor an ImageObject with no url').toEqual([]);
  expect(logosIn({ '@type': 'Organization', image: '/a.png', url: 'https://example.com' }), 'nor another property').toEqual([]);
});

for (const icon of ICONS) {
  test(`icons — ${icon.path} is linked and is ${icon.kind === 'png' ? `a ${icon.size} px PNG` : icon.kind === 'ico' ? 'an ICO with a 32 px frame' : 'an SVG'}`, async ({ page, request }) => {
    const live = SITE.url;
    expect(isWebAddress(live), `SITE.url in src/config.ts is '${live}': set it to the site's full address, such as https://example.com (this test compares each icon link with it)`).toBe(true);
    await page.goto('/');
    const home = page.url();
    const own = [home, live];
    let linked: string[];
    const declared: (string | null)[] = []; // the sizes each link or entry to this file declares
    if (icon.linkedBy === 'icon') {
      linked = (await page.locator('link[rel~="icon"]').evaluateAll((els) => els.map((e) => e.getAttribute('href') ?? ''))).map((h) => sitePath(h, home, own));
    } else if (icon.linkedBy === 'apple') {
      const links = await page.locator('link[rel="apple-touch-icon"]').evaluateAll((els) => els.map((e) => ({ href: e.getAttribute('href') ?? '', sizes: e.getAttribute('sizes') })));
      linked = links.map((l) => sitePath(l.href, home, own));
      links.forEach((l, i) => { if (linked[i] === icon.path) declared.push(l.sizes); });
    } else if (icon.linkedBy === 'manifest') {
      const hrefs = await page.locator('link[rel="manifest"]').evaluateAll((els) => els.map((e) => e.getAttribute('href') ?? ''));
      expect(hrefs, 'the home page links one manifest').toHaveLength(1);
      const manifest = new URL(hrefs[0], home).href;
      const res = await request.get(manifest);
      expect(res.ok(), `${manifest} is served`).toBe(true);
      const entries = (await res.json()).icons as { src: string; sizes?: string }[];
      linked = entries.map((i) => sitePath(i.src, manifest, own));
      entries.forEach((e, i) => { if (linked[i] === icon.path) declared.push(e.sizes ?? null); });
    } else {
      // The logo the page's structured data names. It must be on the site's own origin: a logo on
      // another host is not this file, so it shows here as its whole address and fails.
      const blocks = await page.locator('script[type="application/ld+json"]').allTextContents();
      linked = blocks
        .flatMap((text, i) => {
          try {
            return logosIn(JSON.parse(text));
          } catch (err) {
            throw new Error(`the home page's structured data block ${i + 1} is not valid JSON: ${(err as Error).message}`);
          }
        })
        .map((logo) => sitePath(logo, live, [live]));
    }
    expect(linked, `${icon.path} is linked (by ${icon.linkedBy === 'icon' ? '<link rel="icon">' : icon.linkedBy === 'apple' ? '<link rel="apple-touch-icon">' : icon.linkedBy === 'manifest' ? "the page's manifest" : "a logo in the page's structured data"})`).toContain(icon.path);

    const res = await request.get(icon.path);
    expect(res.ok(), `${icon.path} is served (status ${res.status()})`).toBe(true);
    const type = res.headers()['content-type'] ?? '';
    const body = await res.body();
    if (icon.kind === 'png') {
      expect(type, `${icon.path} content type`).toContain('image/png');
      expect(body.subarray(0, 8).equals(PNG_SIGNATURE), `${icon.path} starts as a PNG (not a picture of another kind with a .png name)`).toBe(true);
      expect(await decodedSize(page, body, 'image/png'), `${icon.path} decodes to ${icon.size} x ${icon.size} pixels`).toEqual([icon.size, icon.size]);
      for (const d of declared) expect(sizesProblem(d, icon.size!), `${icon.path}: the ${icon.linkedBy === 'apple' ? '<link rel="apple-touch-icon">' : 'manifest entry'} ${sizesProblem(d, icon.size!)}`).toBeNull();
    } else if (icon.kind === 'ico') {
      expect(type, `${icon.path} content type`).toMatch(/image\/(x-icon|vnd\.microsoft\.icon)/);
      expect(body.length, `${icon.path} holds an ICO header`).toBeGreaterThanOrEqual(6);
      expect([body.readUInt16LE(0), body.readUInt16LE(2)], `${icon.path} is an ICO (reserved 0, type 1)`).toEqual([0, 1]);
      // A frame that lists 32 pixels, lies past the directory and inside the file, and that the
      // browser decodes to 32 x 32 on its own, cut out into a one-entry ICO.
      const count = body.readUInt16LE(4);
      const frame = Array.from({ length: count }, (_, i) => 6 + 16 * i)
        .filter((at) => at + 16 <= body.length)
        .map((at) => ({ at, size: body[at] || 256, length: body.readUInt32LE(at + 8), offset: body.readUInt32LE(at + 12) }))
        .find((f) => f.size === icon.size && f.length > 0 && f.offset >= 6 + 16 * count && f.offset + f.length <= body.length);
      expect(frame, `${icon.path} has a 32 pixel frame inside the file`).toBeDefined();
      const f = frame!;
      const offset = Buffer.alloc(4);
      offset.writeUInt32LE(22);
      const alone = Buffer.concat([Buffer.from([0, 0, 1, 0, 1, 0]), body.subarray(f.at, f.at + 12), offset, body.subarray(f.offset, f.offset + f.length)]);
      expect(await decodedSize(page, alone, 'image/x-icon'), `${icon.path}: its 32 pixel frame decodes to 32 x 32`).toEqual([icon.size, icon.size]);
    } else {
      expect(type, `${icon.path} content type`).toContain('image/svg+xml');
      const size = await svgSize(page, body);
      expect(size !== null && size[0] > 0 && size[1] > 0, `${icon.path} decodes as an SVG image (size ${JSON.stringify(size)})`).toBe(true);
    }
  });
}

// The sizes the <link rel="icon"> tag declares for the ICO are the frames the file holds, so the tag
// cannot hide a frame or claim one that is not there. Each frame is checked whole: its width and
// height, its place inside the file, and that the browser decodes it to that size.
test('icons — the sizes declared for favicon.ico are the frames inside it', async ({ page, request }) => {
  await page.goto('/');
  const declared = await page.locator('link[rel~="icon"][href$="/favicon.ico"]').getAttribute('sizes');
  expect(declared, 'the ICO link has a sizes attribute').not.toBeNull();
  const body = Buffer.from(await (await request.get('/favicon.ico')).body());
  const count = body.readUInt16LE(4);
  const frames: string[] = [];
  for (let i = 0; i < count; i++) {
    const at = 6 + 16 * i;
    const [w, h] = [body[at] || 256, body[at + 1] || 256];
    const length = body.readUInt32LE(at + 8);
    const offset = body.readUInt32LE(at + 12);
    expect(length > 0 && offset >= 6 + 16 * count && offset + length <= body.length, `frame ${i + 1} lies inside the file`).toBe(true);
    const at22 = Buffer.alloc(4);
    at22.writeUInt32LE(22);
    const alone = Buffer.concat([Buffer.from([0, 0, 1, 0, 1, 0]), body.subarray(at, at + 12), at22, body.subarray(offset, offset + length)]);
    expect(await decodedSize(page, alone, 'image/x-icon'), `frame ${i + 1} decodes to ${w} x ${h}`).toEqual([w, h]);
    frames.push(`${w}x${h}`);
  }
  const norm = (list: string[]) => [...new Set(list)].sort();
  expect(norm(declared!.trim().split(/\s+/)), 'the sizes of the favicon.ico link in src/layouts/Base.astro must list every frame in public/favicon.ico (sizes in the tag, against the frames in the file)').toEqual(norm(frames));
});

// Warns, never fails: the starter's icons show the colour or letter the site had when they were
// drawn, and the site has changed it since. The brand kit's icons are not read.
test('icons — the starter\'s icons still show the site\'s colour and letter (warns only)', async () => {
  const reasons = await staleReasons(fileURLToPath(new URL('..', import.meta.url)));
  for (const description of reasons) {
    console.warn(`icons: ${description}`);
    test.info().annotations.push({ type: 'warning', description });
  }
});
