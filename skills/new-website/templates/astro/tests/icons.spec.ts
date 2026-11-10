import { test, expect, type Page } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { COMPANY } from '../src/config';
import { staleReasons } from '../scripts/make-icons.mjs';

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
  { path: '/images/logo.png', linkedBy: 'logo', kind: 'png', size: 512 },  // COMPANY.logo, the Organization schema's logo
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

const pathOf = (href: string, base: string) => new URL(href, base).pathname;

for (const icon of ICONS) {
  test(`icons — ${icon.path} is linked and is ${icon.kind === 'png' ? `a ${icon.size} px PNG` : icon.kind === 'ico' ? 'an ICO with a 32 px frame' : 'an SVG'}`, async ({ page, request }) => {
    await page.goto('/');
    const home = page.url();
    let linked: string[];
    if (icon.linkedBy === 'icon') {
      linked = (await page.locator('link[rel~="icon"]').evaluateAll((els) => els.map((e) => e.getAttribute('href') ?? ''))).map((h) => pathOf(h, home));
    } else if (icon.linkedBy === 'apple') {
      linked = (await page.locator('link[rel="apple-touch-icon"]').evaluateAll((els) => els.map((e) => e.getAttribute('href') ?? ''))).map((h) => pathOf(h, home));
    } else if (icon.linkedBy === 'manifest') {
      const hrefs = await page.locator('link[rel="manifest"]').evaluateAll((els) => els.map((e) => e.getAttribute('href') ?? ''));
      expect(hrefs, 'the home page links one manifest').toHaveLength(1);
      const manifest = new URL(hrefs[0], home).href;
      const res = await request.get(manifest);
      expect(res.ok(), `${manifest} is served`).toBe(true);
      linked = ((await res.json()).icons as { src: string }[]).map((i) => pathOf(i.src, manifest));
    } else {
      linked = [pathOf(COMPANY.logo, home)];
    }
    expect(linked, `${icon.path} is linked (by ${icon.linkedBy === 'icon' ? '<link rel="icon">' : icon.linkedBy === 'apple' ? '<link rel="apple-touch-icon">' : icon.linkedBy === 'manifest' ? "the page's manifest" : 'COMPANY.logo'})`).toContain(icon.path);

    const res = await request.get(icon.path);
    expect(res.ok(), `${icon.path} is served (status ${res.status()})`).toBe(true);
    const type = res.headers()['content-type'] ?? '';
    const body = await res.body();
    if (icon.kind === 'png') {
      expect(type, `${icon.path} content type`).toContain('image/png');
      expect(body.subarray(0, 8).equals(PNG_SIGNATURE), `${icon.path} starts as a PNG (not a picture of another kind with a .png name)`).toBe(true);
      expect(await decodedSize(page, body, 'image/png'), `${icon.path} decodes to ${icon.size} x ${icon.size} pixels`).toEqual([icon.size, icon.size]);
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
      expect(body.toString('utf8'), `${icon.path} is an SVG`).toMatch(/<svg[\s>]/);
    }
  });
}

// The sizes the <link rel="icon"> tag declares for the ICO are the frames the file holds, so the
// tag cannot hide a frame (Google asks for a 48 px favicon, so that frame must be there and declared).
test('icons — the sizes declared for favicon.ico are the frames inside it', async ({ page, request }) => {
  await page.goto('/');
  const declared = await page.locator('link[rel~="icon"][href$="/favicon.ico"]').getAttribute('sizes');
  expect(declared, 'the ICO link has a sizes attribute').not.toBeNull();
  const body = Buffer.from(await (await request.get('/favicon.ico')).body());
  const frames = Array.from({ length: body.readUInt16LE(4) }, (_, i) => body[6 + 16 * i] || 256);
  const norm = (list: number[]) => [...new Set(list)].sort((a, b) => a - b);
  expect(norm(declared!.split(/\s+/).map((s) => Number(s.split('x')[0]))), 'sizes in the tag').toEqual(norm(frames));
  expect(norm(frames), 'the ICO holds a 48 px frame').toContain(48);
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
