import { test, expect } from '@playwright/test';
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

// A PNG with its signature, IHDR first, image data, and IEND last, its chunks end to end with
// nothing after them. Not a decoder.
const isPng = (b: Buffer) => {
  if (b.length < 45 || !b.subarray(0, 8).equals(PNG_SIGNATURE)) return false;
  const chunks: { name: string; length: number }[] = [];
  let at = 8;
  while (at + 12 <= b.length) {
    const length = b.readUInt32BE(at);
    if (at + 12 + length > b.length) return false;
    chunks.push({ name: b.subarray(at + 4, at + 8).toString('latin1'), length });
    at += 12 + length;
  }
  return at === b.length && chunks[0]?.name === 'IHDR' && chunks.at(-1)?.name === 'IEND' &&
    chunks.some((c) => c.name === 'IDAT' && c.length > 0);
};

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
      expect(isPng(body), `${icon.path} is a whole PNG (signature, IHDR first, image data, IEND last)`).toBe(true);
      expect([body.readUInt32BE(16), body.readUInt32BE(20)], `${icon.path} is ${icon.size} x ${icon.size} pixels`).toEqual([icon.size, icon.size]);
    } else if (icon.kind === 'ico') {
      expect(type, `${icon.path} content type`).toMatch(/image\/(x-icon|vnd\.microsoft\.icon)/);
      expect(body.length, `${icon.path} holds an ICO header`).toBeGreaterThanOrEqual(6);
      expect([body.readUInt16LE(0), body.readUInt16LE(2)], `${icon.path} is an ICO (reserved 0, type 1)`).toEqual([0, 1]);
      // A 32-pixel entry whose frame lies past the directory and inside the file, and is a whole PNG
      // or starts with a 40-byte BITMAPINFOHEADER.
      const count = body.readUInt16LE(4);
      const frames = Array.from({ length: count }, (_, i) => 6 + 16 * i)
        .filter((at) => at + 16 <= body.length)
        .map((at) => ({ size: body[at] || 256, length: body.readUInt32LE(at + 8), offset: body.readUInt32LE(at + 12) }));
      const whole = frames
        .filter((f) => f.offset >= 6 + 16 * count && f.offset + f.length <= body.length)
        .filter((f) => isPng(body.subarray(f.offset, f.offset + f.length)) || (f.length >= 40 && body.readUInt32LE(f.offset) === 40))
        .map((f) => f.size);
      expect(whole, `${icon.path} has a 32 pixel frame, inside the file, that is a PNG or a bitmap`).toContain(icon.size);
    } else {
      expect(type, `${icon.path} content type`).toContain('image/svg+xml');
      expect(body.toString('utf8'), `${icon.path} is an SVG`).toMatch(/<svg[\s>]/);
    }
  });
}

// Warns, never fails: the starter's icons show the colour or letter the site had when they were
// drawn, and the site has changed it since. The brand kit's icons are not read.
test('icons — the starter\'s icons still show the site\'s colour and letter (warns only)', async () => {
  const reasons = await staleReasons(fileURLToPath(new URL('..', import.meta.url)));
  for (const description of reasons) {
    console.warn(`icons: ${description}`);
    test.info().annotations.push({ type: 'warning', description });
  }
});
