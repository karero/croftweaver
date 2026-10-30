# The tab icon: a tile with an inner outline

How to build a site's tab icon so it stays visible on a dark tab bar, the way it was
built for a client site on 2026-10-29. Read this when the site has no logo yet and
needs an interim letter-mark, or when her mark vanishes on a dark tab bar.

## Why this shape

A browser shows the tab icon on its own tab bar, light or dark, not on the page. A
plain tile in a dark brand colour vanishes on a dark tab bar. Two other fixes were
tried and rejected on that site: a white tile in dark mode (a `prefers-color-scheme`
rule in the SVG, which the PNG and ICO files cannot follow), and a thin light rim.
A white outline inside the tile, the same in both modes, kept the icon visible and
looked best.

The intake does not check this: it checks her mark against the page backgrounds, then
white and black (`scripts/_icons.py`), never against a tab bar. Look at the finished
icon in a browser with a dark tab bar before you call it done.

## The SVG

`public/favicon.svg`, on a 512 grid:

- the tile: the whole square, corners rounded (`rx="104"`), in the brand colour;
- the outline: a square from 72 to 440, `rx="56"`, no fill, a white stroke 32 wide
  (it covers 56 to 88 on each side);
- the mark inside the outline, white, with clear space to it;
- no `prefers-color-scheme` rule: one picture for light and dark.

An interim letter-mark is one letter drawn as strokes. The example is an "A" on a
dark green:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-label="Example">
  <!-- Interim letter-mark on a tile with an inner outline. Before the owner's logo is installed, remove this icon's tests (brand kit, references/tab-icon.md). -->
  <rect width="512" height="512" rx="104" fill="#1f5c3a"/>
  <rect x="72" y="72" width="368" height="368" rx="56" fill="none" stroke="#ffffff" stroke-width="32"/>
  <path d="M170 360L256 152L342 360M206 286H306" fill="none" stroke="#ffffff" stroke-width="34" stroke-linejoin="miter" stroke-linecap="butt"/>
</svg>
```

The comment line stays in the file: it tells the next person what to do before her
logo arrives.

**Contrast.** The outline and the mark must reach 3 to 1 or better against the tile,
by the intake's own measure (`_colour.ratio` in `scripts/_colour.py`; white on
`#1f5c3a` is 7.92 to 1, on `#44494c` 9.12 to 1). Where white does not reach it on her
brand colour, stop and ask her for another pair from her palette that does. Never
propose a pair that fails. A light tile with a dark outline should work the same way,
but it has not been tried.

**Her own mark in the tile.** Only on her yes: the intake installs her mark as it is,
and the tile is a choice about her logo. The mark in the tile is white (or the colour
of the outline), so it needs a one-colour version of her mark in that colour, from her
package or from whoever made the mark (§8 of `SKILL.md`, "a mark with colours of its
own"). Never recolour her SVG yourself.

## The five raster files

Render them from the SVG with `rsvg-convert` (librsvg) and `magick` (ImageMagick 7).
Both are needed; without them, stop and say so (on a Mac: `brew install librsvg
imagemagick`; elsewhere, the system's package manager). There is no fallback. Each
file is flattened on the brand colour, so its corners are square: phones and launchers
cut their own shape.

```bash
C='#1f5c3a'   # the brand colour, the tile's
rsvg-convert -w 512 -h 512 -b "$C" favicon.svg -o icon-512.png
rsvg-convert -w 192 -h 192 -b "$C" favicon.svg -o icon-192.png
rsvg-convert -w 180 -h 180 -b "$C" favicon.svg -o apple-touch-icon.png
rsvg-convert -w 358 -h 358 -b "$C" favicon.svg -o maskable-tile.png
magick maskable-tile.png -background "$C" -gravity center -extent 512x512 icon-maskable-512.png
for s in 16 32 48 64; do rsvg-convert -w $s -h $s -b "$C" favicon.svg -o ico-$s.png; done
magick ico-16.png ico-32.png ico-48.png ico-64.png favicon.ico
```

Then delete `maskable-tile.png` and the `ico-*.png` files, and put the five files and
the SVG in `public/`. `magick identify` on them should list 512, 192, 180 and 512
pixels square, and an ICO with 16, 32, 48 and 64 pixel frames.

- **The maskable icon draws the tile at 70 % (358 of 512).** The manifest spec's safe
  zone is a circle of radius 40 % of the icon (W3C App Manifest, "Icon masks and safe
  zone"). The outline's outer corner reaches 0.494 of the side from the centre (the
  corner arc's centre at 128,128, radius 72), so at 70 % it sits at 0.346: on the
  example, the farthest white pixel measured 0.345. At 80 % it would sit at 0.395,
  on the edge. The intake's `MASKABLE_SCALE = 0.56` is for a bare mark that fills its
  box, a different shape; both are right for what they draw.
- **The ICO has four frames.** 16, 32 and 48 pixels are the usual favicon sizes. The 64 pixel
  frame is there for the test below, which draws every file at 64 pixels: a 48 pixel
  frame scaled up to 64 blurred the outline (9.6 grey levels on the client site).
- **This differs from the intake on purpose.** The intake renders with the site's own
  `sharp` and writes a one-frame 32 pixel ICO, for the mark it installs. This recipe is
  built by hand, outside the intake.

## The tests

Put this file in the site as `tests/tab-icon.spec.ts`. It ran green on the example
above and failed on each break described after it. Change four things for your site:

- `TILE`: the tile colour, written in the test, not read from the site's colours, so a
  colours-only run of the intake stays green (see "Later changes").
- `damaged`: the SVG with part of the mark taken away (the example removes the A's
  left leg and crossbar). Change it with the mark.
- `LIMITS`: measured, never copied (below).
- `PROBES`: four points on the 512 grid: the tile (40,256), the outline (72,256), plain
  tile inside the outline, and a point in the middle of one of the mark's strokes. The
  last two depend on the mark; pick them so a stroke's edge is at least 10 units away.

```ts
import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

// The tab icon: a tile in the brand colour, a white inner outline and the mark (website-brand-kit,
// references/tab-icon.md). Remove this file before the owner's logo is installed: the intake runs
// the site's tests after it writes and would put everything back.

// The tile colour, written here rather than read from the site's colours, so a colours-only run of
// the intake stays green. Change it, the SVG and the raster files together.
const TILE = '#1f5c3a';
const MASKABLE_SCALE = 0.7; // the maskable icon draws the tile at 70 %
// The SVG with part of the mark gone (here the A's left leg and crossbar): change it with the mark.
const damaged = (svg: string) => svg.replace(/<path d="[^"]*"/, '<path d="M256 152L342 360"');
// Mean grey difference allowed per file, set between its own score and the damaged mark's
// (measured on this site; see the reference).
const LIMITS: Record<string, number> = {
  '/icon-512.png': 2, '/favicon.ico': 2, '/icon-maskable-512.png': 2, '/icon-192.png': 5, '/apple-touch-icon.png': 5,
};
// Points on the 512 grid and the colour each must show: tile, outline, plain tile inside, the mark.
const PROBES: [number, number, string][] = [[40, 256, TILE], [72, 256, '#ffffff'], [120, 256, TILE], [213, 256, '#ffffff']];

const svgText = () => readFileSync(new URL('../public/favicon.svg', import.meta.url), 'utf8');

test('tab icon: favicon.svg has no dark-mode variant', () => {
  // The icon is the same in light and dark mode: the outline keeps it visible on a dark tab bar.
  expect(svgText()).not.toMatch(/prefers-color-scheme/);
});

test('tab icon: favicon.svg draws the same picture in a light and a dark colour scheme', async ({ page }) => {
  // Catches a dark-mode rule in any spelling, where Chromium applies it to an SVG drawn as an image.
  const draw = async (scheme: 'light' | 'dark') => {
    await page.emulateMedia({ colorScheme: scheme });
    await page.goto('/');
    return page.evaluate(async () => {
      const img = new Image();
      img.src = '/favicon.svg';
      await img.decode();
      const c = document.createElement('canvas');
      c.width = 256; c.height = 256;
      const ctx = c.getContext('2d')!;
      ctx.drawImage(img, 0, 0, 256, 256);
      return Array.from(ctx.getImageData(0, 0, 256, 256).data);
    });
  };
  const light = await draw('light');
  const dark = await draw('dark');
  expect(light.filter((v, i) => v !== dark[i]).length, 'values that differ between the two schemes').toBe(0);
});

test('tab icon: favicon.svg shows the tile, the outline and the mark in their colours', async ({ page }) => {
  await page.goto('/');
  const got = await page.evaluate(async (probes) => {
    const img = new Image();
    img.src = '/favicon.svg';
    await img.decode();
    const c = document.createElement('canvas');
    c.width = 512; c.height = 512;
    const ctx = c.getContext('2d')!;
    ctx.drawImage(img, 0, 0, 512, 512);
    return probes.map(([x, y]) => Array.from(ctx.getImageData(x, y, 1, 1).data.slice(0, 3)));
  }, PROBES);
  PROBES.forEach(([x, y, hex], i) => {
    const want = [1, 3, 5].map((n) => parseInt(hex.slice(n, n + 2), 16));
    const off = Math.max(...got[i].map((v, k) => Math.abs(v - want[k])));
    expect(off, `the point ${x},${y} shows ${got[i]}, not ${hex}`).toBeLessThanOrEqual(2);
  });
});

test('tab icon: the raster files show the same picture as favicon.svg', async ({ page }) => {
  await page.goto('/');
  const svg = svgText();
  const diffs = await page.evaluate(async ({ files, tile, scale, svg, broken }) => {
    const grey = async (src: string, s = 1) => {
      const img = new Image();
      img.src = src;
      await img.decode();
      const c = document.createElement('canvas');
      c.width = 64; c.height = 64;
      const ctx = c.getContext('2d')!;
      ctx.imageSmoothingQuality = 'high';
      ctx.fillStyle = tile;
      ctx.fillRect(0, 0, 64, 64);
      ctx.drawImage(img, (64 - 64 * s) / 2, (64 - 64 * s) / 2, 64 * s, 64 * s);
      const d = ctx.getImageData(0, 0, 64, 64).data;
      const out: number[] = [];
      for (let i = 0; i < d.length; i += 4) out.push(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]);
      return out;
    };
    const diff = (a: number[], b: number[]) => a.reduce((s, v, i) => s + Math.abs(v - b[i]), 0) / a.length;
    const url = (t: string) => 'data:image/svg+xml,' + encodeURIComponent(t);
    const ref = await grey(url(svg));
    const refMaskable = await grey(url(svg), scale);
    const result: Record<string, number> = {};
    for (const f of files) result[f] = diff(await grey(f), f.includes('maskable') ? refMaskable : ref);
    result['damaged'] = diff(await grey(url(broken)), ref);
    result['damaged, maskable'] = diff(await grey(url(broken), scale), refMaskable);
    return result;
  }, { files: Object.keys(LIMITS), tile: TILE, scale: MASKABLE_SCALE, svg, broken: damaged(svg) });
  expect(damaged(svg), 'the damaged copy differs from favicon.svg').not.toBe(svg);
  for (const [file, limit] of Object.entries(LIMITS)) {
    expect(diffs[file], `${file} differs from favicon.svg by ${diffs[file].toFixed(2)} grey levels`).toBeLessThan(limit);
    const broken = file.includes('maskable') ? diffs['damaged, maskable'] : diffs['damaged'];
    expect(broken, `self-check: the damaged mark (${broken.toFixed(2)}) must fail the limit of ${file}`).toBeGreaterThan(limit);
  }
});
```

**Setting the limits.** Set every limit to 99, add `console.log(JSON.stringify(diffs))`
after the `evaluate`, and run the file. It prints each file's score and the score of
the damaged mark (`damaged`, and `damaged, maskable` for the maskable icon). Set each
limit between the file's own score and the damaged mark's, then remove the log line.
On the example the files scored 0.6 to 0.7 (512, ICO, maskable) and 3.5 to 4.0 (192 and
180, which lose detail at 64 pixels); the damaged mark scored 7.17, and 3.48 at 70 %. So
2 and 5. Where the damaged mark does not score clearly above a file's own score, which
happens with a thin mark (an "I" with half its stem gone scored 1.88 when a reviewer
measured it with `rsvg-convert`),
the test cannot guard that file at 64 pixels: compare at a larger size, or write in
the test that it does not guard that file.

**What each test catches, and what it does not:**

| Test | Catches | Lets through |
|---|---|---|
| no dark-mode variant | the text `prefers-color-scheme` in the SVG | an escaped spelling |
| same picture in both schemes | any dark-mode rule that changes the picture in Chromium, escaped spellings too | a rule only another browser applies |
| tile, outline and mark | a wrong colour at the four points | a change elsewhere |
| raster files | a file that differs from the SVG by more than its limit: a stale or wrong mark, a wrong colour | smaller damage (an "A" without its crossbar scored 1.17 against a limit of 2.58, measured by a reviewer with `rsvg-convert`) |

Checked on the example: a 192 file rendered from the damaged mark failed (10.78); a
`prefers-color-scheme` rule failed the text check; an escaped rule that hid only the
crossbar in dark mode passed the text check and failed the comparison; a tile one shade
off failed the colour points and the raster test. None of them sees a real tab bar.

## Later changes

- **Her logo arrives.** Delete `tests/tab-icon.spec.ts` in the same change, before the
  intake runs: the intake runs the site's tests after it writes, and the colour points
  would fail on her bare mark and make it put everything back. The intake then asks
  before replacing the hand-built icons (`--replace-icons`, only on her yes). If she
  wants her mark in the tile, build that by hand afterwards (see "Her own mark in the
  tile") and bring the tests back with it.
- **New colours.** A colours-only run of the intake leaves a `favicon.svg` it did not
  install alone and does not redraw it. It says so in a note only when a page
  background changes; when only the brand colour changes, it says nothing about the
  icon. The tests stay green either way, because their colour is their own (checked:
  the example's tests passed after the site's brand colour changed). So after any run
  that changes the brand colour, redraw the SVG, the five files and `TILE` by hand,
  together, in one change.
