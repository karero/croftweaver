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
      expect(body.subarray(1, 4).toString('latin1'), `${icon.path} is a PNG`).toBe('PNG');
      expect([body.readUInt32BE(16), body.readUInt32BE(20)], `${icon.path} is ${icon.size} x ${icon.size} pixels`).toEqual([icon.size, icon.size]);
    } else if (icon.kind === 'ico') {
      expect(type, `${icon.path} content type`).toMatch(/image\/(x-icon|vnd\.microsoft\.icon)/);
      expect([body.readUInt16LE(0), body.readUInt16LE(2)], `${icon.path} is an ICO (reserved 0, type 1)`).toEqual([0, 1]);
      const entries = Array.from({ length: body.readUInt16LE(4) }, (_, i) => body[6 + 16 * i] || 256);
      expect(entries, `${icon.path} has a 32 pixel frame`).toContain(icon.size);
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
