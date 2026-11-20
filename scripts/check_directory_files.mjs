// Checks one file of the directory tree: the blob on stdin, its path as the argument.
// Prints why and exits 1 when the file is refused. Used by publish_directory.sh.
import fs from 'node:fs';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';

const TABLE = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});
// CRC-32 as PNG uses it, written out so no Node version's zlib matters.
export function crc32(buf) {
  let c = 0xffffffff;
  for (const b of buf) c = TABLE[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

const SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

// The reason the icon is refused, or '' when it passes. Only what an icon needs passes: an 8-bit
// RGB or RGBA PNG, not interlaced, whose critical chunks are IHDR first, consecutive IDATs and
// IEND last (no PLTE), with every checksum and every row of image data whole. Ancillary chunks
// (sRGB, eXIf and the like) pass on their checksum alone; pixel values are not checked.
export function pngProblem(buf) {
  if (buf.length < 8 || !buf.subarray(0, 8).equals(SIGNATURE)) return 'no PNG signature';
  const idat = [];
  let pos = 8, first = true, hdr, idatEnded = false;
  for (;;) {
    if (pos + 12 > buf.length) return 'cut short: no IEND chunk';
    const len = buf.readUInt32BE(pos);
    const end = pos + 12 + len;
    if (end > buf.length) return 'cut short inside a chunk';
    const type = buf.toString('latin1', pos + 4, pos + 8);
    if (buf.readUInt32BE(end - 4) !== crc32(buf.subarray(pos + 4, end - 4))) return `the ${type} chunk fails its checksum`;
    if (first) {
      if (type !== 'IHDR' || len !== 13) return 'IHDR is not the first chunk, or is not 13 bytes';
      hdr = { w: buf.readUInt32BE(pos + 8), h: buf.readUInt32BE(pos + 12), depth: buf[pos + 16], colour: buf[pos + 17],
        rest: [buf[pos + 18], buf[pos + 19], buf[pos + 20]] };
      if (hdr.w === 0 || hdr.h === 0) return 'width or height is zero';
      if (hdr.depth !== 8 || (hdr.colour !== 2 && hdr.colour !== 6)) return 'not an 8-bit RGB or RGBA image';
      if (hdr.rest.join() !== '0,0,0') return 'interlaced, or a compression or filter method PNG does not define';
      first = false;
    } else if (type === 'IDAT') {
      if (idatEnded) return 'its IDAT chunks are not consecutive';
      idat.push(buf.subarray(pos + 8, end - 4));
    } else {
      if (idat.length) idatEnded = true;
      // A critical chunk has an upper-case first letter; only IHDR, IDAT and IEND may appear.
      if (type !== 'IEND' && !(buf[pos + 4] & 0x20)) return `a ${type} chunk, which the icon may not have`;
    }
    if (type === 'IEND') {
      if (len !== 0) return 'IEND is not empty';
      if (end !== buf.length) return 'bytes after IEND';
      break;
    }
    pos = end;
  }
  if (!idat.length) return 'no IDAT chunk';
  const rowBytes = 1 + hdr.w * (hdr.colour === 6 ? 4 : 3);
  const size = rowBytes * hdr.h;
  if (size > 64 * 1024 * 1024) return 'larger than an icon needs';
  const data = Buffer.concat(idat);
  let raw;
  try { raw = zlib.inflateSync(data, { info: true, maxOutputLength: size + 1 }); } catch { return 'the image data is not valid zlib, or too long'; }
  if (raw.engine.bytesWritten !== data.length) return 'bytes after the image data';
  if (raw.buffer.length !== size) return 'the image data does not fill its rows';
  for (let row = 0; row < size; row += rowBytes) if (raw.buffer[row] > 4) return 'a row has a filter PNG does not define';
  return '';
}

function textProblem(buf) {
  // Bytes first: a binary file is called binary even when it is not UTF-8 either.
  if (buf.some((b) => (b < 0x20 && b !== 0x09 && b !== 0x0a && b !== 0x0d) || b === 0x7f)) return 'holds a control character other than tab or a line break';
  let text;
  try { text = new TextDecoder('utf-8', { fatal: true }).decode(buf); } catch { return 'is not valid UTF-8'; }
  if (/[\u0080-\u009f]/.test(text)) return 'holds a control character other than tab or a line break';
  if (text.startsWith('#!')) return 'starts with #!: the directory takes text, not scripts';
  return '';
}

// The plugin manifest must also be one JSON object.
function manifestProblem(buf) {
  const text = textProblem(buf);
  if (text) return text;
  let value;
  try { value = JSON.parse(buf.toString('utf8')); } catch (e) { return `is not valid JSON (${e.message})`; }
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return 'is not a JSON object';
  return '';
}

// Run as a command (also through a symlink), not when the tests import crc32. publish_directory.sh
// takes only "ok" as a pass, so a run that checks nothing fails there.
if (process.argv[1] && fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url))) {
  const file = process.argv[2];
  if (!file) { console.log('no path given'); process.exit(1); }
  let problem;
  try {
    const buf = fs.readFileSync(0);
    const png = file === '.claude-plugin/icon.png' ? pngProblem(buf) : '';
    problem = png ? `is not a whole PNG: ${png}` : file === '.claude-plugin/icon.png' ? ''
      : file === '.claude-plugin/plugin.json' ? manifestProblem(buf) : textProblem(buf);
  } catch (e) {
    // On stdout, so publish_directory.sh puts the reason on its ::error:: line.
    problem = `could not be checked: the checker failed (${e.message})`;
  }
  if (problem) { console.log(problem); process.exit(1); }
  console.log('ok');
}
