// Post-build: give every h2/h3 in the built HTML a stable slug `id`, so any
// section is linkable from an external site with zero per-page work.
//
// Runs over dist/ AFTER `astro build` (see package.json "build"). Static ids in
// the shipped HTML — no runtime JS — so crawlers, AI answer engines and the
// browser's on-load scroll all see them.
//
// Two KINDS of heading are LEFT ALONE (never get a generated id):
//   1. one that already has an explicit id (a hand-curated anchor always wins);
//   2. one inside a <section>/<article> that has an id — that curated wrapper
//      (e.g. #plain-english, #outcomes) is already the anchor for the section,
//      so adding a second id to the heading would just fragment the anchor.
// Generated slugs are deduped against every existing id on the page, so a
// generated id can never collide with (or duplicate) a curated one.
//
// The parser is used ONLY to decide which headings qualify and what to call
// them; the id is then spliced into the raw HTML by string replacement, so the
// rest of the file is preserved byte-for-byte (node-html-parser's re-serializer
// rewrites self-closing SVG tags, which would corrupt inline diagrams). If a
// file's raw heading count and parsed heading count disagree (a stray "<h2" in
// a comment or script), that file is skipped rather than risk a misaligned edit.

import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { parse } from 'node-html-parser';

const DIST = 'dist';
const HEADING_TAG = /<(h[23])\b[^>]*>/gi;
const ID_WORDS = 2; // how many meaningful words a generated id uses by default

// Filler words dropped before picking the id words, so "The outcomes we deliver"
// -> "outcomes-deliver" rather than "the-outcomes". Articles, conjunctions,
// prepositions, pronouns, auxiliaries and question words. The German set is
// applied ONLY on German-lang pages: several German fillers ARE meaningful
// English heading words ("Die Casting Services", "MIT License", "The War on
// Talent", "Living with ALS") — a combined set silently erases those topics
// from English ids (and renames published anchors on adoption).
const STOP_EN = new Set(
  ('a an the and or but of to in into on for with at by from as is are be been ' +
    'this that these those it its our your their we you they i how what why when ' +
    'where which who will can do does has have')
    .split(' ')
);
const STOP_DE = new Set(
  ('der die das den dem des ein eine einen einem einer und oder aber zu im in ' +
    'auf mit bei von aus als ist sind war waren wir ihr sie es fuer wie was ' +
    'warum wann wo wer wird werden kann koennen so ' +
    'zum zur vom am beim ins ans')
    .split(' ')
);

// The ordered MEANINGFUL words of a heading, for building its id. Lowercased and
// accent-stripped, split on whitespace/punctuation -- but an intra-name hyphen is
// PRESERVED, so a hyphenated name or domain like "acme-corp" stays ONE word (up to
// two hyphens kept, domain-style). Filler words are dropped. The id uses the
// first ID_WORDS; more are appended only to break a collision.
function idWords(text, stop) {
  const words = text
    .toLowerCase()
    // NFC first: a decomposed umlaut (u + combining mark, e.g. pasted content)
    // would miss the precomposed replaces below and degrade to bare
    // accent-stripping (ü->u instead of ue).
    .normalize('NFC')
    // German transliteration BEFORE the ASCII strip: ß does not decompose
    // under NFKD, so it would fall through to the [^a-z0-9-] separator and
    // SPLIT the word ("Maßnahmen" -> "ma" + "nahmen"); umlauts get their
    // German digraphs (ä->ae) instead of bare accent-stripping (ä->a), so
    // "Größen" becomes "groessen", matching the ASCII-slug house rule.
    // (German-specific by design — other non-decomposing letters (ø æ œ ł)
    // still word-split; extend the replace chain if your site needs them.)
    .replace(/ß/g, 'ss')
    .replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue')
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '') // strip accents (e.g. accented -> plain)
    .replace(/[^a-z0-9-]+/g, ' ') // separators -> space, but KEEP hyphens
    .split(/\s+/)
    // A number glued to the START of a word (collapsed markup, "1Understand") splits
    // into "1","understand". Requires a leading digit-run + 3+ trailing letters, so a
    // digit inside a term ("b2b", "web3d"), a number+unit ("3d", "4k", "10x"), an
    // ordinal ("1st", "21st") and short acronyms ("2fa", "4wd") are all left intact.
    .flatMap((w) => {
      const m = w.match(/^(\d+)([a-z]{3,}.*)$/);
      return m ? [m[1], m[2]] : [w];
    })
    .map((w) => w.split('-').filter(Boolean).slice(0, 3).join('-')) // <= 2 hyphens / name
    .filter(Boolean);
  const meaningful = words.filter((w) => !stop.has(w));
  return meaningful.length ? meaningful : words.length ? words : ['section'];
}

// Walk up to the document root; true if any ancestor section/article carries an id.
function coveredByCuratedSection(node) {
  for (let p = node.parentNode; p && p.tagName; p = p.parentNode) {
    const tag = p.tagName.toLowerCase();
    if ((tag === 'section' || tag === 'article') && p.getAttribute('id')) return true;
  }
  return false;
}

function htmlFiles(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    const fp = join(dir, entry);
    if (statSync(fp).isDirectory()) htmlFiles(fp, out);
    else if (entry.endsWith('.html')) out.push(fp);
  }
  return out;
}

let totalAdded = 0;
let filesChanged = 0;
let skipped = 0;

for (const file of htmlFiles(DIST)) {
  const src = readFileSync(file, 'utf8');
  const root = parse(src, { comment: true });
  const headings = root.querySelectorAll('h2, h3');
  if (!headings.length) continue;

  const rawCount = (src.match(HEADING_TAG) || []).length;
  if (rawCount !== headings.length) {
    console.warn(`anchor-ids: SKIP ${file} (heading count mismatch: raw ${rawCount} vs parsed ${headings.length})`);
    skipped++;
    continue;
  }

  const used = new Set(
    root.querySelectorAll('[id]').map((el) => el.getAttribute('id')).filter(Boolean)
  );

  // Locale-conditional stop set, from the page's own <html lang>.
  const pageLang = (root.querySelector('html')?.getAttribute('lang') ?? 'en').toLowerCase().split('-')[0];
  const stop = pageLang === 'de' ? STOP_DE : STOP_EN;

  // Parser order matches regex order, so decisions[] aligns 1:1 with the tags below.
  const decisions = headings.map((h) => {
    if (h.getAttribute('id')) return null;          // explicit id wins
    if (coveredByCuratedSection(h)) return null;    // section/article anchor covers it
    const words = idWords(h.text || '', stop);
    const base = words.slice(0, ID_WORDS).join('-') || 'section';
    // ID_WORDS words by default; append the next word(s) to disambiguate a clash
    // before resorting to a numeric suffix (so two clashing headings become
    // foo-bar / foo-bar-baz, not foo-bar / foo-bar-2).
    let id = base;
    for (let k = ID_WORDS; used.has(id) && k < words.length; ) id = words.slice(0, ++k).join('-');
    for (let n = 2; used.has(id); n++) id = `${base}-${n}`;
    used.add(id);
    return id;
  });

  if (decisions.every((d) => d === null)) continue;

  let i = 0;
  let added = 0;
  const out = src.replace(HEADING_TAG, (tag) => {
    const id = decisions[i++];
    if (!id) return tag;
    added++;
    return tag.replace(/^<(h[23])\b/i, `<$1 id="${id}"`);
  });

  writeFileSync(file, out);
  totalAdded += added;
  filesChanged++;
}

console.log(
  `anchor-ids: added ${totalAdded} id(s) across ${filesChanged} file(s)` +
    (skipped ? `, skipped ${skipped} file(s)` : '')
);

// Fail the build if any file was skipped. The skip itself is the safe choice (never
// mutate HTML we couldn't parse confidently), but a skipped file ships a page with
// un-id'd headings — silently breaking the "every section is linkable" promise. Exit
// non-zero so `npm run build` / CI catches it; fix the stray "<h2"/"<h3" (usually in a
// code block, comment or string) and rebuild. Clean output → skipped 0 → exit 0.
if (skipped) {
  console.error(
    `anchor-ids: FAILING build — ${skipped} file(s) skipped (heading-count mismatch); ` +
      `their h2/h3 anchors were NOT generated. Resolve the stray "<h2"/"<h3" logged above.`
  );
  process.exitCode = 1;
}
