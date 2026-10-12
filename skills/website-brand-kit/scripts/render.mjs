#!/usr/bin/env node
// Draws the cleaned SVG into square PNG files. It draws and does nothing else: every check and
// every decision is made by brand_intake.py. Started with the SITE as its working folder, so
// `sharp` is the site's own (it comes with Astro; nothing is added to the site's package.json).
//
// The SVG arrives as text on standard input and is handed to sharp as a Buffer, never as a path:
// measured on 2026-10-10 and 2026-10-11, given a path the renderer follows <image href>,
// xlink:href, file:// URLs and CSS @import; given a Buffer it follows none of them.
//
//   node render.mjs --check            load sharp and draw one pixel; prints the versions
//   node render.mjs < request.json     {svg, viewBox, intrinsic, outDir, jobs:[{name,file,size,scale,background}]}
//   The svg has a width and height whose long side is `intrinsic` pixels; each job scales that to its icon.
//
// It always answers with one JSON line: {"ok":true,...} or {"ok":false,"error":...,"message":...},
// and then ends by itself. It never calls process.exit(): on Windows a line written to a pipe
// is still on its way when write() returns, and an exit right behind it would cut the answer off.
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve, sep } from 'node:path';

const reply = (obj) => { process.exitCode = 0; process.stdout.write(JSON.stringify(obj) + '\n'); };
// A refusal stops the work where it stands: it is thrown, and answered once at the end.
class Refused extends Error { constructor(error, message) { super(String(message)); this.error = error; } }
const fail = (error, message) => { throw new Refused(error, message); };

const HEX = /^#[0-9a-fA-F]{6}$/;
const FILE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,60}$/;

async function main() {
  const require = createRequire(join(process.cwd(), 'package.json'));
  let sharp;
  try { sharp = require('sharp'); } catch (e) { fail('sharp-missing', e && e.message ? e.message : e); }
  sharp.cache(false);
  sharp.concurrency(1);
  const versions = () => ({ sharp: sharp.versions.sharp, rsvg: sharp.versions.rsvg, node: process.version });

  if (process.argv.includes('--check')) {
    const tiny = Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect width="1" height="1" fill="#000"/></svg>');
    await sharp(tiny).png().toBuffer();
    return { ok: true, ...versions() };
  }

  const req = JSON.parse(readFileSync(0, 'utf8'));
  const svg = Buffer.from(String(req.svg), 'utf8');
  const [, , vw, vh] = req.viewBox;
  if (!(vw > 0 && vh > 0 && Number.isFinite(vw) && Number.isFinite(vh))) fail('bad-job', 'the viewBox is not usable');
  const outDir = resolve(String(req.outDir));
  mkdirSync(outDir, { recursive: true });
  const long = Number(req.intrinsic);
  if (!(long >= 1 && long <= 8192)) fail('bad-job', 'the intrinsic size is not usable');
  const results = [];
  for (const job of req.jobs) {
    const { name, file, size, scale, background } = job;
    if (typeof file !== 'string' || !FILE.test(file) || resolve(outDir, file).startsWith(outDir + sep) === false) fail('bad-job', `file name not allowed: ${String(file).slice(0, 40)}`);
    if (!Number.isInteger(size) || size < 1 || size > 2048) fail('bad-job', `size not allowed: ${size}`);
    if (!(typeof scale === 'number' && scale > 0 && scale <= 1)) fail('bad-job', `scale not allowed: ${scale}`);
    if (background !== null && !(typeof background === 'string' && HEX.test(background))) fail('bad-job', `background not allowed: ${String(background).slice(0, 20)}`);
    const target = size * scale;
    const want = Math.max(1, Math.round(target)); // the mark's long side, in whole pixels
    // 72 dpi draws the svg at its own size; scale the density so its long side lands on `target`
    let mark = await sharp(svg, { density: Math.min(100000, Math.max(1, (72 * target) / long)) }).png().toBuffer();
    let { width: mw, height: mh } = await sharp(mark).metadata();
    if (mw > want || mh > want) { // a rounding of one pixel past it, or a target under the smallest picture sharp draws
      mark = await sharp(mark).resize(want, want, { fit: 'inside' }).png().toBuffer();
      ({ width: mw, height: mh } = await sharp(mark).metadata());
    }
    // measured 2026-10-12: the long side lands within half a pixel of `target`; anything else is not what was asked for
    if (Math.abs(Math.max(mw, mh) - target) > 1) fail('render-failed', `the mark came out ${mw} by ${mh} pixels, not ${want} on its long side`);
    const bg = background === null ? { r: 0, g: 0, b: 0, alpha: 0 }
      : { r: parseInt(background.slice(1, 3), 16), g: parseInt(background.slice(3, 5), 16), b: parseInt(background.slice(5, 7), 16), alpha: 1 };
    let img = sharp({ create: { width: size, height: size, channels: 4, background: bg } })
      .composite([{ input: mark, left: Math.floor((size - mw) / 2), top: Math.floor((size - mh) / 2) }]);
    if (background !== null) img = img.removeAlpha();
    const png = await img.png().toBuffer();
    writeFileSync(join(outDir, file), png);
    results.push({ name, file, width: size, height: size });
  }
  return { ok: true, ...versions(), results };
}

try {
  reply(await main());
} catch (e) {
  const message = e && e.message ? e.message : e;
  reply({ ok: false, error: e instanceof Refused ? e.error : 'render-failed', message: String(message).split('\n')[0].slice(0, 300) });
}
