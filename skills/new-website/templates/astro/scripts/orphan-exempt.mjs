// Reads orphan-exempt.txt: the pages the site leaves unlinked on purpose. One reader for
// tests/orphans.spec.ts and scripts/check_internal_links.sh. Run it: node scripts/orphan-exempt.mjs <siteRoot>
//
// One address per line, starting with /. A # after white space (or at the line start) begins a comment.
// A missing file means no exemptions. A bad line throws, naming the file and the line.

import { readFileSync, realpathSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const FILE = 'orphan-exempt.txt';

// White space other than space and tab, and control characters other than tab: they can never match a page.
// Numbers, not escapes: an escape typed into a source file can reach it as the raw character.
function isBadChar(cp) {
  return cp <= 0x08 || (cp >= 0x0a && cp <= 0x1f) || (cp >= 0x7f && cp <= 0x9f)
    || cp === 0xa0 || cp === 0x1680 || (cp >= 0x2000 && cp <= 0x200a)
    || cp === 0x2028 || cp === 0x2029 || cp === 0x202f || cp === 0x205f || cp === 0x3000 || cp === 0xfeff;
}
const code = (ch) => 'U+' + ch.codePointAt(0).toString(16).toUpperCase().padStart(4, '0');

export function parseOrphanExempt(text) {
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1); // one BOM, at the very start
  const lines = text.split('\n');
  const found = [];
  lines.forEach((raw, i) => {
    const n = i + 1;
    const fail = (why) => { throw new Error(`${FILE} line ${n}: ${why}`); };
    // A \r belongs to the line ending only right before a \n, so not on the last piece.
    let line = raw;
    if (i < lines.length - 1 && line.endsWith('\r')) line = line.slice(0, -1);
    const cr = line.indexOf('\r');
    if (cr >= 0) fail(`stray ${code('\r')} (a carriage return that is not part of a line ending)`);
    // A comment starts at a # at the line start or after a space or tab.
    let end = line.length;
    for (let k = 0; k < line.length; k++) {
      if (line[k] === '#' && (k === 0 || line[k - 1] === ' ' || line[k - 1] === '\t')) { end = k; break; }
    }
    const address = line.slice(0, end).replace(/[ \t]+$/, '');
    if (address === '') return;
    for (const ch of address) {
      if (isBadChar(ch.codePointAt(0))) fail(`${code(ch)} in "${address}" can never match a page; remove it`);
    }
    if (/[ \t]/.test(address)) fail(`white space before or inside "${address}"; write one address per line, starting at the first column`);
    if (address[0] !== '/') fail(`"${address}" must start with /`);
    if (address === '/') fail('"/" is the home page, the crawl root, and is never an orphan; remove the line');
    if (address.endsWith('/')) fail(`"${address}" must not end with /`);
    if (address.includes('?') || address.includes('#')) fail(`"${address}" must not hold ? or #`);
    found.push(address);
  });
  return found;
}

export function readOrphanExempt(siteRoot) {
  let text;
  try {
    text = readFileSync(path.join(siteRoot, FILE), 'utf8');
  } catch (e) {
    if (e && e.code === 'ENOENT') return [];
    throw new Error(`${FILE}: cannot be read (${e && e.code ? e.code : e})`);
  }
  return parseOrphanExempt(text);
}

if (process.argv[1] && realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url))) {
  const root = process.argv[2];
  if (!root) {
    console.error('usage: node scripts/orphan-exempt.mjs <siteRoot>');
    process.exitCode = 1;
  } else {
    try {
      for (const a of readOrphanExempt(root)) console.log(a);
    } catch (e) {
      console.error(e.message);
      process.exitCode = 1;
    }
  }
}
