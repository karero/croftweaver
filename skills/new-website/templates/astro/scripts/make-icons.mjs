// Makes the site's icon: its first letter on its brand colour, in the seven files the starter
// links (public/favicon.svg, favicon.ico, apple-touch-icon.png, icon-192.png, icon-512.png,
// icon-maskable-512.png and images/logo.png). Setup runs it once: node scripts/make-icons.mjs --setup
// Run it again after a colour change. The brand kit replaces these files when the owner has a logo.
//
//   --setup          also replace the scaffold's favicon.svg and favicon.ico, on a new site only
//   --letter X       draw this letter or digit (A-Z, 0-9) instead of the name's first
//   --colour #rrggbb the tile colour instead of --brand in src/styles/global.css
//   --replace        also replace icons this script did not make (only on the owner's yes)
//
// It needs the site's own `sharp` (it comes with Astro) and adds no dependency.

import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, realpathSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

export class IconsError extends Error {}

export const RECORD = 'scripts/icons-made.json';
const TMP_DIR = 'scripts/.icons-tmp';
// The seven files, with the folder-relative path each is written to.
export const FILES = [
  'public/favicon.svg',
  'public/favicon.ico',
  'public/apple-touch-icon.png',
  'public/icon-192.png',
  'public/icon-512.png',
  'public/icon-maskable-512.png',
  'public/images/logo.png',
];
const BRAND_KIT_START = '<!-- Installed by the website-brand-kit skill';
const BOM = String.fromCharCode(0xfeff);

// ---- the letter -------------------------------------------------------------------------

// Letters that do not fold to a base letter by dropping accents.
const FOLDS = { 'ß': 'S', 'Æ': 'A', 'Ø': 'O', 'Œ': 'O', 'Ł': 'L', 'Đ': 'D', 'Ð': 'D' };

// The first letter or digit of a name, accents folded; quotes, spaces and signs before it are skipped.
// A letter or digit this script has no drawing for is refused, never guessed.
export function letterFor(name) {
  for (const ch of String(name)) {
    const upper = ch.toUpperCase();
    const folded = FOLDS[ch] ?? FOLDS[upper] ?? upper.normalize('NFD').replace(/\p{M}/gu, '');
    if (/^[A-Z0-9]$/.test(folded)) return folded;
    if (/[\p{L}\p{N}]/u.test(ch)) {
      throw new IconsError(
        `The name starts with "${upper}", which this script has no drawing for. Ask the owner for one letter A-Z or digit 0-9 ` +
          'for the icon, then run it again with --letter X.',
      );
    }
  }
  throw new IconsError(
    'The name has no letter or digit to draw. Ask the owner for one letter A-Z or digit 0-9 for the icon, then run it again with --letter X.',
  );
}

// Strokes on a grid of 4 columns by 6 rows, M/L/Z only. Round joins, so a stroke never reaches
// past half its width beyond a point.
export const GLYPHS = {
  A: 'M0 6L0 2L1 0L3 0L4 2L4 6M0 3.5L4 3.5',
  B: 'M0 6L0 0L3 0L4 1L4 2L3 3L0 3M3 3L4 4L4 5L3 6L0 6',
  C: 'M4 1L3 0L1 0L0 1L0 5L1 6L3 6L4 5',
  D: 'M0 0L0 6L2.5 6L4 4.5L4 1.5L2.5 0Z',
  E: 'M4 0L0 0L0 6L4 6M0 3L3 3',
  F: 'M4 0L0 0L0 6M0 3L3 3',
  G: 'M4 1L3 0L1 0L0 1L0 5L1 6L3 6L4 5L4 3L2 3',
  H: 'M0 0L0 6M4 0L4 6M0 3L4 3',
  I: 'M1 0L3 0M2 0L2 6M1 6L3 6',
  J: 'M4 0L4 5L3 6L1 6L0 5',
  K: 'M0 0L0 6M4 0L0 3.5M1 2.7L4 6',
  L: 'M0 0L0 6L4 6',
  M: 'M0 6L0 0L2 3L4 0L4 6',
  N: 'M0 6L0 0L4 6L4 0',
  O: 'M1 0L3 0L4 1L4 5L3 6L1 6L0 5L0 1Z',
  P: 'M0 6L0 0L3 0L4 1L4 2L3 3L0 3',
  Q: 'M1 0L3 0L4 1L4 5L3 6L1 6L0 5L0 1ZM2.5 4L4.2 6.3',
  R: 'M0 6L0 0L3 0L4 1L4 2L3 3L0 3M2 3L4 6',
  S: 'M4 1L3 0L1 0L0 1L0 2L1 3L3 3L4 4L4 5L3 6L1 6L0 5',
  T: 'M0 0L4 0M2 0L2 6',
  U: 'M0 0L0 5L1 6L3 6L4 5L4 0',
  V: 'M0 0L2 6L4 0',
  W: 'M0 0L1 6L2 3L3 6L4 0',
  X: 'M0 0L4 6M4 0L0 6',
  Y: 'M0 0L2 3L4 0M2 3L2 6',
  Z: 'M0 0L4 0L0 6L4 6',
  0: 'M1 0L3 0L4 1L4 5L3 6L1 6L0 5L0 1ZM3 1.5L1 4.5',
  1: 'M0.8 1.4L2.5 0L2.5 6',
  2: 'M0 1L1 0L3 0L4 1L4 2L0 6L4 6',
  3: 'M0 1L1 0L3 0L4 1L4 2L3 3L1.5 3M3 3L4 4L4 5L3 6L1 6L0 5',
  4: 'M3 6L3 0L0 4.2L4 4.2',
  5: 'M4 0L0 0L0 2.8L3 2.8L4 3.8L4 5L3 6L1 6L0 5',
  6: 'M4 1L3 0L1 0L0 1L0 5L1 6L3 6L4 5L4 4L3 3L0 3',
  7: 'M0 0L4 0L1.5 6',
  8: 'M1 0L3 0L4 1L4 2L3 3L4 4L4 5L3 6L1 6L0 5L0 4L1 3L0 2L0 1ZM1 3L3 3',
  9: 'M0 5L1 6L3 6L4 5L4 1L3 0L1 0L0 1L0 2L1 3L4 3',
};

// The grid on the 512 square: centred, stroke 34, so the pixels stay within 169-350 across and
// 152-369 down (the tail of Q reaches furthest), inside the outline's inner edge at 88 and 424.
export function glyphPath(letter) {
  const num = (n) => String(Math.round(n * 10) / 10);
  return GLYPHS[letter]
    .replace(/(-?[\d.]+) (-?[\d.]+)/g, (_m, c, r) => `${num(186 + 35 * Number(c))} ${num(169 + 29 * Number(r))}`);
}

// ---- colours ----------------------------------------------------------------------------

const HEX = /^#[0-9a-fA-F]{6}$/;

function luminance(hex) {
  const lin = [1, 3, 5].map((i) => {
    const v = parseInt(hex.slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
}

export function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// White on the tile if that reaches 3 to 1, else black (one of the two always reaches 4.58 to 1).
export function markColour(tile) {
  return contrast('#ffffff', tile) >= 3 ? '#ffffff' : '#000000';
}

// ---- what the site says -----------------------------------------------------------------

const SLOT = /\[\s*\p{Lu}\s*[^\]\s][^\]]*\]/u;

function nameFromSource(source) {
  const block = source.match(/export const SITE = \{([\s\S]*?)\n\} as const/)?.[1] ?? '';
  const m = block.match(/^[ \t]*name:[ \t]*(?:'([^'\\\n]*)'|"([^"\\\n]*)")[ \t]*,/m);
  return m ? (m[1] ?? m[2]) : undefined;
}

// SITE.name from src/config.ts. Node strips the types on import; if that throws (an older Node),
// the `name:` line of the SITE block is read instead, and must hold one quoted string.
export async function readSiteName(root) {
  const file = path.join(root, 'src', 'config.ts');
  if (!existsSync(file)) throw new IconsError(`${file} is not there. Run this in the site's folder.`);
  let name;
  try {
    name = (await import(pathToFileURL(file).href)).SITE?.name;
  } catch {
    name = nameFromSource(readFileSync(file, 'utf8'));
  }
  if (typeof name !== 'string' || !name.trim() || name === 'Example' || SLOT.test(name)) {
    throw new IconsError('Set SITE.name in src/config.ts to the site\'s real name first (it is still the starter\'s "Example", a [SLOT], or not one plain string). Then run this again.');
  }
  return name;
}

// The light theme's --brand from src/styles/global.css.
export function readBrand(root) {
  const file = path.join(root, 'src', 'styles', 'global.css');
  if (!existsSync(file)) throw new IconsError(`${file} is not there. Run this in the site's folder, or give --colour #rrggbb.`);
  const value = readFileSync(file, 'utf8').match(/:root\s*\{[^}]*?--brand:\s*([^;}]*?)\s*;/)?.[1];
  if (value === undefined) throw new IconsError('Found no --brand colour in the :root block of src/styles/global.css. Give the tile colour with --colour #rrggbb.');
  if (!HEX.test(value)) throw new IconsError(`--brand in src/styles/global.css is "${value}", which is not #rrggbb. Give the tile colour with --colour #rrggbb.`);
  return value.toLowerCase();
}

// ---- the record -------------------------------------------------------------------------

const sha = (buf) => createHash('sha256').update(buf).digest('hex');

// scripts/icons-made.json: { letter: {value, from}, colour: {value, from}, files: { path: [sha256, ...] } }.
// from is "name"/"brand" when the site chose it, "flag" for --letter/--colour. A path holds two
// hashes only while a run is in progress or was stopped.
export function readRecord(root) {
  const file = path.join(root, RECORD);
  if (!existsSync(file)) return { record: null };
  try {
    const record = JSON.parse(readFileSync(file, 'utf8'));
    const ok = record && typeof record === 'object' && record.files && typeof record.files === 'object'
      && Object.values(record.files).every((h) => Array.isArray(h) && h.every((x) => /^[0-9a-f]{64}$/.test(x)));
    if (!ok) throw new Error('not the expected shape');
    return { record };
  } catch (e) {
    return { record: null, problem: `${RECORD} cannot be read (${e.message})` };
  }
}

// ---- the files --------------------------------------------------------------------------

export function drawSvg(letter, tile) {
  const mark = markColour(tile);
  return `<!-- Made by scripts/make-icons.mjs: the letter ${letter} on ${tile}. Run it again after a colour change. -->\n` +
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">\n' +
    `  <rect width="512" height="512" rx="104" fill="${tile}"/>\n` +
    `  <rect x="72" y="72" width="368" height="368" rx="56" fill="none" stroke="${mark}" stroke-width="32"/>\n` +
    `  <path d="${glyphPath(letter)}" fill="none" stroke="${mark}" stroke-width="34" stroke-linejoin="round" stroke-linecap="round"/>\n` +
    '</svg>\n';
}

// An ICO of PNG frames: a 6-byte header, one 16-byte entry per frame, then the frames.
export function buildIco(frames) {
  const head = Buffer.alloc(6 + 16 * frames.length);
  head.writeUInt16LE(1, 2);
  head.writeUInt16LE(frames.length, 4);
  let offset = head.length;
  frames.forEach(({ size, png }, i) => {
    const at = 6 + 16 * i;
    head[at] = size; head[at + 1] = size;
    head.writeUInt16LE(1, at + 4);
    head.writeUInt16LE(32, at + 6);
    head.writeUInt32LE(png.length, at + 8);
    head.writeUInt32LE(offset, at + 12);
    offset += png.length;
  });
  return Buffer.concat([head, ...frames.map((f) => f.png)]);
}

const SHARP_MISSING = (why) =>
  `The image tool that draws the icons (sharp) cannot be loaded in this site: ${why}\n` +
  'In the site\'s folder, run:\n  npm install --include=optional\nthen check that it loads:\n  node -e "require(\'sharp\')"\n' +
  'If it still does not load, or there is no build of sharp for this computer, this script cannot make the icons on this computer. ' +
  'It never adds sharp to the site\'s package.json.';

async function loadSharp(root) {
  try {
    // Resolved from the site's folder, so a copy of this script anywhere finds the site's own sharp.
    const require = (await import('node:module')).createRequire(path.join(root, 'package.json'));
    return (await import(pathToFileURL(require.resolve('sharp')).href)).default;
  } catch (e) {
    throw new IconsError(SHARP_MISSING(String(e.message).split('\n')[0]));
  }
}

// The seven files' bytes, rendered from the one SVG.
async function render(sharp, svg, tile) {
  const source = Buffer.from(svg);
  const flat = async (size, scale = 1) => {
    const inner = Math.round(size * scale);
    let img = sharp(source, { density: (72 * inner) / 512 }).resize(inner, inner).flatten({ background: tile });
    if (inner !== size) {
      const pad = (size - inner) / 2;
      img = sharp(await img.png().toBuffer()).extend({ top: Math.floor(pad), bottom: Math.ceil(pad), left: Math.floor(pad), right: Math.ceil(pad), background: tile });
    }
    return img.png().toBuffer();
  };
  const png512 = await flat(512);
  const frames = [];
  for (const size of [16, 32, 48, 64]) frames.push({ size, png: await flat(size) });
  return {
    'public/favicon.svg': source,
    'public/favicon.ico': buildIco(frames),
    'public/apple-touch-icon.png': await flat(180),
    'public/icon-192.png': await flat(192),
    'public/icon-512.png': png512,
    'public/icon-maskable-512.png': await flat(512, 0.7),
    'public/images/logo.png': png512,
  };
}

// Which of the seven this script may not overwrite: those present whose hash is not in the record.
function foreignFiles(root, record) {
  return FILES.filter((rel) => {
    const file = path.join(root, rel);
    if (!existsSync(file)) return false;
    return !record?.files?.[rel]?.includes(sha(readFileSync(file)));
  });
}

function checkOwnership(root, { setup, replace }) {
  if (replace) return;
  const { record, problem } = readRecord(root);
  const foreign = foreignFiles(root, record);
  if (!foreign.length) return;
  const svgPath = path.join(root, 'public/favicon.svg');
  const svgText = existsSync(svgPath) ? readFileSync(svgPath, 'utf8') : '';
  const brandKit = svgText.startsWith(BOM) ? svgText.slice(1).startsWith(BRAND_KIT_START) : svgText.startsWith(BRAND_KIT_START);
  if (setup && foreign.every((rel) => rel === 'public/favicon.svg' || rel === 'public/favicon.ico')) {
    const others = FILES.filter((rel) => rel !== 'public/favicon.svg' && rel !== 'public/favicon.ico');
    const fresh = existsSync(svgPath) && !brandKit && !others.some((rel) => existsSync(path.join(root, rel)));
    if (fresh) return;
  }
  throw new IconsError(
    `${setup ? '--setup is for a new site, and these' : 'These'} icon files are not ones this script made: ${foreign.join(', ')}. Nothing was written.` +
      (problem ? `\n${problem}.` : '') +
      (brandKit ? '\nThe site\'s icons come from the brand kit: change them with the brand kit, not with this script.' : '') +
      '\nTo replace them anyway, run this again with --replace, only if the owner says yes.',
  );
}

const tmpWrite = (root, name, data) => {
  const file = path.join(root, TMP_DIR, name);
  writeFileSync(file, data);
  return file;
};

// Draws and writes the seven files and the record. `checkpoint` is called at each step of the
// write, so a test can stop the run there.
export async function makeIcons({ root, setup = false, replace = false, letter, colour, checkpoint = async () => {} }) {
  const letterFrom = letter === undefined ? 'name' : 'flag';
  const colourFrom = colour === undefined ? 'brand' : 'flag';
  if (letter !== undefined) {
    letter = String(letter).toUpperCase();
    if (!/^[A-Z0-9]$/.test(letter)) throw new IconsError('--letter takes one letter A-Z or digit 0-9.');
  } else {
    letter = letterFor(await readSiteName(root));
  }
  if (colour !== undefined && !HEX.test(colour)) throw new IconsError('--colour takes a colour as #rrggbb.');
  const tile = (colour ?? readBrand(root)).toLowerCase();

  checkOwnership(root, { setup, replace });
  const sharp = await loadSharp(root);
  const svg = drawSvg(letter, tile);
  const made = await render(sharp, svg, tile);

  const record = (files) => JSON.stringify(
    { letter: { value: letter, from: letterFrom }, colour: { value: tile, from: colourFrom }, files }, null, 2) + '\n';
  const next = Object.fromEntries(FILES.map((rel) => [rel, [sha(made[rel])]]));
  const both = Object.fromEntries(FILES.map((rel) => {
    const file = path.join(root, rel);
    return [rel, existsSync(file) ? [...new Set([sha(readFileSync(file)), ...next[rel]])] : next[rel]];
  }));

  rmSync(path.join(root, TMP_DIR), { recursive: true, force: true });
  mkdirSync(path.join(root, TMP_DIR), { recursive: true });
  const tmp = {};
  for (const rel of FILES) tmp[rel] = tmpWrite(root, path.basename(rel), made[rel]);
  await checkpoint('files-in-temp');
  const recordTmp = tmpWrite(root, 'icons-made.json', record(both));
  await checkpoint('record-with-both-in-temp');
  renameSync(recordTmp, path.join(root, RECORD));
  await checkpoint('record-with-both');
  for (const rel of FILES) {
    mkdirSync(path.dirname(path.join(root, rel)), { recursive: true });
    renameSync(tmp[rel], path.join(root, rel));
    await checkpoint(`renamed ${rel}`);
  }
  const doneTmp = tmpWrite(root, 'icons-made.json', record(next));
  await checkpoint('record-final-in-temp');
  renameSync(doneTmp, path.join(root, RECORD));
  await checkpoint('record-final');
  rmSync(path.join(root, TMP_DIR), { recursive: true, force: true });
  return { letter, tile, mark: markColour(tile) };
}

// Why the starter's icons no longer match the site: the colour or the letter the record took from
// the site has changed since. Empty when the icons are not all ones this script made (the brand
// kit's, a hand-built set) or the record took the value from --colour/--letter. A value that cannot
// be read now is a reason too: this is a warning, never a failure.
export async function staleReasons(root) {
  const { record } = readRecord(root);
  if (!record) return [];
  const mine = FILES.every((rel) => existsSync(path.join(root, rel)) && record.files[rel]?.includes(sha(readFileSync(path.join(root, rel)))));
  if (!mine) return [];
  // The command that draws them again with the choices made by flag kept.
  const run = 'Run: node scripts/make-icons.mjs'
    + (record.letter?.from === 'flag' ? ` --letter ${record.letter.value}` : '')
    + (record.colour?.from === 'flag' ? ` --colour ${record.colour.value}` : '');
  const out = [];
  if (record.colour?.from === 'brand') {
    try {
      const now = readBrand(root);
      if (now !== record.colour.value) out.push(`--brand is ${now} but the icons were drawn on ${record.colour.value}. ${run}`);
    } catch (e) {
      if (!(e instanceof IconsError)) throw e;
      out.push(e.message);
    }
  }
  if (record.letter?.from === 'name') {
    try {
      const now = letterFor(await readSiteName(root));
      if (now !== record.letter.value) out.push(`the name now starts with ${now} but the icons show ${record.letter.value}. ${run}`);
    } catch (e) {
      if (!(e instanceof IconsError)) throw e;
      out.push(e.message);
    }
  }
  return out;
}

// ---- the command line -------------------------------------------------------------------

const USAGE = 'Usage: node scripts/make-icons.mjs [--setup] [--letter X] [--colour #rrggbb] [--replace]';

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--setup' || a === '--replace') out[a.slice(2)] = true;
    else if (a === '--letter' || a === '--colour') {
      if (argv[i + 1] === undefined) throw new IconsError(`${a} needs a value.\n${USAGE}`);
      out[a.slice(2)] = argv[++i];
    } else throw new IconsError(`Unknown argument "${a}".\n${USAGE}`);
  }
  return out;
}

async function main() {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  try {
    const result = await makeIcons({ root, ...parseArgs(process.argv.slice(2)) });
    console.log(`Made the seven icon files: the letter ${result.letter} in ${result.mark === '#ffffff' ? 'white' : 'black'} on ${result.tile}.`);
  } catch (e) {
    if (!(e instanceof IconsError)) throw e;
    console.error(e.message);
    process.exitCode = 1;
  }
}

if (process.argv[1] && realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url))) await main();
