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
// CRC-32 as PNG uses it; zlib.crc32 is missing on older Node 20.
export function crc32(buf) {
  let c = 0xffffffff;
  for (const b of buf) c = TABLE[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

const SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

// The reason a PNG is not whole, or '' when it is. No pixel decoding.
export function pngProblem(buf) {
  if (buf.length < 8 || !buf.subarray(0, 8).equals(SIGNATURE)) return 'no PNG signature';
  const idat = [];
  let pos = 8, first = true;
  for (;;) {
    if (pos + 12 > buf.length) return 'cut short: no IEND chunk';
    const len = buf.readUInt32BE(pos);
    const end = pos + 12 + len;
    if (end > buf.length) return 'cut short inside a chunk';
    const type = buf.toString('latin1', pos + 4, pos + 8);
    if (buf.readUInt32BE(end - 4) !== crc32(buf.subarray(pos + 4, end - 4))) return `the ${type} chunk fails its checksum`;
    if (first) {
      if (type !== 'IHDR' || len !== 13) return 'IHDR is not the first chunk, or is not 13 bytes';
      if (buf.readUInt32BE(pos + 8) === 0 || buf.readUInt32BE(pos + 12) === 0) return 'width or height is zero';
      first = false;
    } else if (type === 'IHDR') return 'a second IHDR chunk';
    else if (type === 'IDAT') idat.push(buf.subarray(pos + 8, end - 4));
    if (type === 'IEND') {
      if (len !== 0) return 'IEND is not empty';
      if (end !== buf.length) return 'bytes after IEND';
      break;
    }
    pos = end;
  }
  if (!idat.length) return 'no IDAT chunk';
  try { zlib.inflateSync(Buffer.concat(idat)); } catch { return 'the image data is not valid zlib'; }
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

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const file = process.argv[2];
  if (!file) { console.log('no path given'); process.exit(1); }
  const buf = fs.readFileSync(0);
  const problem = file === '.claude-plugin/icon.png'
    ? (pngProblem(buf) && `is not a whole PNG: ${pngProblem(buf)}`)
    : textProblem(buf);
  if (problem) { console.log(problem); process.exit(1); }
}
