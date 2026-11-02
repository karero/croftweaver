import { test, expect, type Page } from '@playwright/test';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { PAGES, UNFILLED_SLOT, PLACEHOLDER_ALLOWLIST, PLACEHOLDER_EXEMPT, placeholderAllowed } from './_helpers';

// Leftover guardrail on the RENDERED site: a placeholder, or a note the author wrote
// to themselves, must not reach a visitor, a search engine or a share card. Reads every
// page's copy, <head> metadata, the text attributes a visitor meets (alt, aria-label,
// title, a form field's hint, a button's label) and JSON-LD, plus the web manifest.
//
// The "[MISSING:" grep in .github/workflows/ci.yml is the fast source-side half: it
// knows one token and looks in src/ and public/ only. This spec reads what a page
// actually serves, whichever file it came from, and knows the leftovers that grep
// was never told about.
//
// Not read, so still a human check at launch (new-website §4): pages outside PAGES
// (the 404 page, noindex pages), other files in public/ (llms.txt and its own slots
// included), PDFs, text inside images, and the starter's own example values (the name
// "Example", hello@example.com). No rule here knows those.
//
// Precision over recall: a rule is here only if what it matches is rarely genuine
// copy; the collisions known so far are named next to each rule. Text that only LOOKS
// like a leftover stays legal in <code>/<pre>/<kbd>/<samp>, under
// [data-placeholder-exempt], or via PLACEHOLDER_ALLOWLIST (both in tests/_helpers.ts).
type Rule = { label: string; re: RegExp; exceptLang?: string[]; onlyLang?: string[] };
// "todo" means "all" in these languages, and headings are often set in capitals.
const TODO_IS_A_WORD = ['es', 'pt', 'gl'];
const RULES: Rule[] = [
  // The content token "[MISSING: year built]" (AGENTS.md §4), a site's own
  // non-English one ("[FEHLT: …]") and every slot: an opening bracket, a capital letter, and at least
  // one more character. That is the shape of all the kit's own slots ("[DATE]",
  // "[W-IdNr., …]", "[Handelsregister / Vereinsregister]") and of the ones AI
  // assistants leave behind ("[Your Name]"). "[1]", "[A]", "[sic]" and EmailLink's
  // "[at]" do not match. Genuine bracketed text that starts with a capital ("[PDF]",
  // an editor's note in a quote) does: add it to PLACEHOLDER_ALLOWLIST or mark it [data-placeholder-exempt].
  // No length limit: a long "[MISSING: …]" is still one. The price is that a bracket
  // opened with a capital and never closed runs on to the next "]"; that is worth a look too.
  // The rule itself is in _helpers.ts: privacy-host.spec.ts skips what it matches.
  { label: 'unfilled [SLOT]', re: UNFILLED_SLOT },
  // The same slots written small: a bracket that opens with a word only a slot opens
  // with ("[your name]", "[insert link]", "[company name]"). Other lower-case brackets
  // ("[the team]" in a quote, "[sic]") pass; on a page still listed below they are
  // looked at more closely (UNSEEN_SLOT).
  { label: 'unfilled [SLOT]', re: /\[\s*(?:insert|add|enter|your|company|name|missing|fehlt|tbd|todo)\b[^\]]*\]/giu },
  { label: 'filler text', re: /\b(?:lorem\s+ipsum|dolor\s+sit\s+amet)\b/gi },
  // Case-sensitive: "todo" in running prose is a word, "TODO" is a note. Where "todo"
  // is an everyday word, only "TODO:" counts. "XXX" also collides with Roman numerals.
  // "TBD" and "TBA" are deliberately not here: on an event page they are genuine copy.
  { label: 'author note', re: /\b(?:TODO|FIXME|XXX)\b/g, exceptLang: TODO_IS_A_WORD },
  { label: 'author note', re: /\bTODO\s*:|\b(?:FIXME|XXX)\b/g, onlyLang: TODO_IS_A_WORD },
  // A template expression nobody evaluated, or an object printed as text.
  { label: 'unrendered template', re: /\{\{[^{}]{0,80}\}\}|\$\{[^{}]{0,80}\}|\[object Object\]/g },
  // Only wordings that are a placeholder on their own. "Type your text here" in a form
  // hint and "a free sample copy" are genuine, so "your … here" is limited to the
  // words nobody asks a visitor for, and "sample" is not a trigger.
  {
    label: 'placeholder wording',
    re: /\b(?:your\s+(?:headline|tagline|copy)\s+(?:goes\s+)?here|(?:text|copy|content|headline)\s+goes\s+here|placeholder\s+(?:text|copy|content|image)|dummy\s+(?:text|copy|content)|(?:john|jane)\s+doe)\b/gi,
  },
  // German. \p{L} lookarounds instead of \b, which does not see ä/ö/ü/ß as letters
  // (same reasoning as GERMAN_RULES in _helpers.ts). "Mustertext" is not here: a
  // site offering template letters uses it genuinely.
  {
    label: 'placeholder wording',
    re: /(?<!\p{L})(?:platzhaltertext|blindtext|hier\s+steht\s+(?:ihr|dein|euer)\s+text|(?:max|erika)\s+mustermann|musterstra(?:ß|ss)e|musterstadt|musterfirma)(?!\p{L})/giu,
  },
];
// Exact matches to tolerate: PLACEHOLDER_ALLOWLIST in tests/_helpers.ts, shared with
// privacy-host.spec.ts. Until 2026-10 it was ALLOWLIST in this file: a site updating
// this spec moves its own entries there.

// A slot the rules above cannot see: bracketed, several words, lower-case first
// ("[self-hosted on our own server / operated for us by …]"). In finished copy that
// shape is usually genuine (an editor's "[the team]" in a quote), so it is checked
// only on a target still listed in UNFILLED_UNTIL_LAUNCH: there it is a draft's slot,
// and without this check the owner who fills every reported slot is told the page is
// done while one is still on it.
const UNSEEN_SLOT = /\[\s*\p{Ll}[^\]]*\s[^\]]*\]/gu;

// The content placeholder of the draft flow (AGENTS.md §2 and §4). A branch may carry
// it into a DRAFT pull request, so on a developer's machine it is reported and the
// push goes through; in CI it fails like any other leftover, which keeps the draft
// unmergeable, next to the grep in ci.yml. Nothing here stops a direct push of `main`
// that still carries one: that was so before this spec, and belongs to the publish step.
// Site translated the token ("[FEHLT: …]")? Put the same word here and in that grep.
// Until then the translated token is an ordinary slot and fails everywhere: the safe side.
const DRAFT_TOKEN = /^\[MISSING:/;

// Served files that carry copy but are not pages. Read as JSON.
const STATIC_FILES = ['/manifest.webmanifest'] as const;

// Input types whose value the browser shows as text. A checkbox's, a hidden field's or
// a password field's value is never on screen.
const SHOWN_AS_TEXT = ['text', 'search', 'email', 'tel', 'url', 'submit', 'button', 'reset'];

// The starter's legal pages and manifest ship with [BRACKET] slots only the owner can
// fill (legal name, address, register number), and the suite has to be green from
// commit 1. So the targets listed here are REPORTED on every run, not failed, while
// they still carry leftovers.
//
// The list empties itself: the moment a listed target is clean, its test fails until
// the entry is deleted, and an entry naming no checked target (page renamed or
// removed) fails too. So the exemption cannot outlive its reason. The site may not
// launch while anything is listed (new-website §4).
//
// Add an entry only when routing another of the kit's slot-carrying drafts before
// launch (a second locale's privacy page). Never to get an unfinished page green:
// that is weakening the test (AGENTS.md §5). Fill the slot, or use the content
// placeholder and keep the pull request a draft.
const UNFILLED_UNTIL_LAUNCH = new Set<string>(['/privacy', '/impressum', '/manifest.webmanifest']);

// The draft notice under the heading of the legal pages (AGENTS.md §5). It is slot-shaped,
// so a listed page reports it as "not ready to launch". It leaves with the owner's answer,
// not with the last filled slot. These are the texts the starter ships; a notice translated
// for another language is added here, or this spec does not see it.
const LEGAL_NOTES = [
  '[DRAFT NOTICE, DELETE BEFORE LAUNCH: This page is a first draft, not legal advice. It cannot know your whole situation, and what the law asks of you depends on your country and on what your site does. Ask a lawyer to review it before you publish, or replace it with your own text.]',
  '[ENTWURFSHINWEIS, VOR DEM START LÖSCHEN: Diese Seite ist ein erster Entwurf und keine Rechtsberatung. Sie kennt Ihre Lage nicht im Ganzen, und was das Gesetz von Ihnen verlangt, hängt von Ihrem Land und von Ihrer Website ab. Lassen Sie den Text vor der Veröffentlichung von einer Anwältin oder einem Anwalt prüfen, oder ersetzen Sie ihn durch Ihren eigenen.]',
];
// The three recorded answers, each a line of its own in README.md. The date is checked
// for its shape only.
const LEGAL_RECORDS = [
  /^legal pages: reviewed by a lawyer \(\d{4}-\d{2}-\d{2}\)\r?$/m,
  /^legal pages: own texts \(\d{4}-\d{2}-\d{2}\)\r?$/m,
  /^legal pages: published as drafted \(owner's decision, \d{4}-\d{2}-\d{2}\)\r?$/m,
];
// Whether a note is on the page for a visitor: a known text, visible in full.
async function noteIsVisible(page: Page): Promise<boolean> {
  for (const note of LEGAL_NOTES) {
    for (const el of await page.getByText(note).all()) if (await el.isVisible()) return true;
  }
  return false;
}
const LEGAL_LAST_SEGMENTS = ['privacy', 'datenschutz', 'impressum'];
const isLegalPage = (path: string) => LEGAL_LAST_SEGMENTS.includes(path.split('/').filter(Boolean).pop() ?? '');
const hasLegalRecord = (readme: string) => LEGAL_RECORDS.some((re) => re.test(readme));

// null = fine. A legal page passes while it is listed and shows a note, or once an answer
// is recorded. Anything else (note dropped, or page delisted with the note still on, and
// no answer) fails.
function legalVerdict(path: string, { listed, noteVisible, recorded }: { listed: boolean; noteVisible: boolean; recorded: boolean }): string | null {
  if (recorded || (listed && noteVisible)) return null;
  return (
    `${path} is a legal page with no recorded answer, and ${listed ? 'is listed in UNFILLED_UNTIL_LAUNCH' : 'is not listed in UNFILLED_UNTIL_LAUNCH'} ` +
    `and ${noteVisible ? 'shows' : 'does not show'} its draft notice. Do not delete the notice or the entry to turn this green. ` +
    `Ask the owner as AGENTS.md section 5 says, record the answer as one line of its own in README.md ` +
    `("legal pages: reviewed by a lawyer (YYYY-MM-DD)", "legal pages: own texts (YYYY-MM-DD)" or ` +
    `"legal pages: published as drafted (owner's decision, YYYY-MM-DD)"), then delete the notices.`
  );
}

// The README.md in the folder that holds package.json (tests run from there). Missing
// counts as no record; any other read error is not hidden.
function readme(dir = process.cwd()): string {
  try {
    return readFileSync(join(dir, 'README.md'), 'utf8');
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === 'ENOENT') return '';
    throw e;
  }
}

// A leftover is the same leftover however it is spaced. The page copy is read three
// times (see readPage), and markup inside a slot puts spaces into some of the readings:
// "[BO<b>LD</b> SLOT]" is "[BOLD SLOT]" in the two fused ones and "[BO LD SLOT]" in the
// spaced one. So findings, PLACEHOLDER_ALLOWLIST and DRAFT_TOKEN are compared with all whitespace
// removed (squash); fold is only how a match is printed.
const fold = (s: string) => s.replace(/\s+/g, ' ');
const squash = (s: string) => s.replace(/\s+/g, '');
const allowed = placeholderAllowed;

// One finding per distinct leftover, in the spelling met first. `match` is the leftover
// itself, folded; `line` is what a person reads, with the text around it. `lang` is
// the page's <html lang>.
type Finding = { label: string; match: string; line: string };
function scan(text: string, lang = ''): Finding[] {
  const primary = lang.toLowerCase().split('-')[0];
  const found = new Map<string, Finding>();
  for (const { label, re, exceptLang, onlyLang } of RULES) {
    if (exceptLang?.includes(primary) || (onlyLang && !onlyLang.includes(primary))) continue;
    for (const m of text.matchAll(re)) {
      const match = fold(m[0]);
      if (allowed(match)) continue;
      const key = `${label}|${squash(match)}`;
      if (found.has(key)) continue;
      const i = m.index ?? 0;
      const ctx = text.slice(Math.max(0, i - 25), i + Math.min(m[0].length, 160) + 25).replace(/\s+/g, ' ').trim();
      found.set(key, { label, match, line: `"${label}" → …${ctx}…` });
    }
  }
  return [...found.values()];
}

function unseenSlots(text: string): string[] {
  const seen = new Map<string, string>();
  for (const m of text.matchAll(UNSEEN_SLOT)) if (!seen.has(squash(m[0]))) seen.set(squash(m[0]), fold(m[0]));
  return [...seen.values()].filter((u) => !allowed(u));
}

// The text inside a JSON document, decoded: in the raw file a line break is the two
// characters \n and any character may be written as \uXXXX, so a rule would look at
// the encoding instead of the words. null = not valid JSON.
function jsonStrings(raw: string): string | null {
  const strings = (v: unknown): string[] =>
    typeof v === 'string' ? [v] : v && typeof v === 'object' ? Object.values(v).flatMap(strings) : [];
  try {
    return strings(JSON.parse(raw)).join('\n');
  } catch {
    return null;
  }
}

// What a target's text means, with no side effect, so the self-check below can pin
// every case. `fail` stops the test; `warn` is printed and the test passes.
type Where = { listed: boolean; ci: boolean; lang?: string };
function verdict(target: string, text: string, { listed, ci, lang }: Where): { fail: string | null; warn: string | null } {
  const all = scan(text, lang);
  const bullets = (lines: string[]) => lines.map((l) => '  • ' + l).join('\n');
  if (listed) {
    const unseen = unseenSlots(text);
    if (unseen.length) {
      return {
        fail:
          `${target} carries bracketed text the slot rule cannot see, because it starts with a ` +
          `lower-case letter. A slot: start it with a capital word ("[CHOOSE ONE: …]"). Genuine ` +
          `text: add it to PLACEHOLDER_ALLOWLIST (tests/_helpers.ts) or mark it [data-placeholder-exempt].\n${bullets(unseen)}`,
        warn: null,
      };
    }
    if (all.length === 0) {
      return {
        fail:
          `${target} has nothing left to fill but is still listed in UNFILLED_UNTIL_LAUNCH. Delete ` +
          `its entry in tests/placeholders.spec.ts so it stays checked from now on.`,
        warn: null,
      };
    }
    // Warn-only while listed (same mechanism as the coverage flag in positioning.spec.ts):
    // visible on every run, never silent (Rule 12), and not launchable in this state.
    const more = all.length > 3 ? `\n  • … and ${all.length - 3} more` : '';
    return {
      fail: null,
      warn: `${target} is not ready to launch, ${all.length} leftover(s) to fill:\n${bullets(all.slice(0, 3).map((f) => f.line))}${more}`,
    };
  }
  const drafts = ci ? [] : all.filter((f) => DRAFT_TOKEN.test(squash(f.match)));
  const blocking = all.filter((f) => !drafts.includes(f));
  return {
    fail: blocking.length
      ? `${target} still serves a placeholder or an author note. Fill it or remove it. Genuine ` +
        `text that only looks like one → <code>, [data-placeholder-exempt] or PLACEHOLDER_ALLOWLIST (tests/_helpers.ts).\n${bullets(blocking.map((f) => f.line))}`
      : null,
    warn: drafts.length
      ? `${target} carries ${drafts.length} content placeholder(s). Fine on a branch headed for a ` +
        `DRAFT pull request; CI fails them, so nothing merges until they are filled:\n${bullets(drafts.map((f) => f.line))}`
      : null,
  };
}

function judge(target: string, text: string, lang = '') {
  const { fail, warn } = verdict(target, text, { listed: UNFILLED_UNTIL_LAUNCH.has(target), ci: !!process.env.CI, lang });
  if (warn) {
    console.warn('⚠ placeholders: ' + warn);
    test.info().annotations.push({ type: 'warning', description: warn });
  }
  expect(fail === null, fail ?? '').toBe(true);
}

// The rules and the verdicts, pinned by example. An edit that stops catching one of
// these, or starts flagging genuine copy, fails here before it can wave a real
// leftover through.
test('placeholders — the rules catch leftovers and pass genuine copy', () => {
  const leftovers = [
    'Built in [MISSING: year built].',
    `[MISSING: ${'a long note the author left for later '.repeat(12)}]`,
    `[OWNER TO DECIDE: ${'a long question the author left for later '.repeat(12)}]`,
    'Baujahr: [FEHLT: Baujahr]',
    'Last updated: [DATE].',
    '[LEGAL NAME INCL. FORM, e.g. Beispiel GmbH]',
    '[W-IdNr., e.g. DE123456789-00001]',
    '[Handelsregister / Vereinsregister]: Registergericht',
    '[CHOOSE ONE: self-hosted on our own server / operated for us by Plausible Insights OÜ,\n      Västriku tn 2, 50403 Tartu, Estonia (EU)]',
    'Kind regards, [Your Name]',
    'Kind regards, [your name]',
    'More at [insert link here]',
    '[company name] was founded in [tbd]',
    'Visit us at [STREET\n      AND NUMBER]',
    'Call [ PHONE ] today',
    'Lorem ipsum dolor sit amet',
    'Lorem\nipsum',
    'TODO: add the prices',
    'Prices TODO',
    'Hello {{ name }}',
    'Hello {{ site.title |\n default: "x" }}',
    'Hello ${name}',
    'Team: [object Object]',
    'Your headline here',
    'Your text goes here',
    'Jane Doe, CEO',
    'Max Mustermann, Musterstraße 1, 12345 Musterstadt',
    'Hier steht Ihr Text',
    jsonStrings('{"name":"Lorem\\nipsum"}') ?? '',
    jsonStrings('{"name":"\\u005bSITE NAME\\u005d"}') ?? '',
  ];
  const genuine = [
    'See footnote [1] and appendix [A], or [ B ], quoted as written [sic].',
    'As [the team] put it',
    'hello [at] example [dot] com',
    'A todo list for the week',
    'Sizes S to XXXL',
    'Prices from $5 {per month}',
    'Type your text here',
    'Upload your logo here',
    'Enter your company name here',
    'Request a free sample copy',
    'Speakers: TBA. Venue: TBD.',
    'Das Muster der Tapete, ein Text für alle',
    'Mustertext für die Kündigung',
    jsonStrings('{"@type":["Organization","LocalBusiness"],"name":"Example"}') ?? 'FIXME',
  ];
  expect(leftovers.filter((s) => scan(s).length === 0), 'leftovers the rules no longer catch').toEqual([]);
  expect(genuine.filter((s) => scan(s).length > 0), 'genuine copy the rules now flag').toEqual([]);
  expect(jsonStrings('{"name": '), 'broken JSON must be reported as such').toBeNull();

  // Language: "TODO" alone is a word in Spanish, a note in English; "TODO:" is a note in both.
  expect(scan('VER TODO INCLUIDO', 'es-ES'), 'Spanish "todo" is a word').toEqual([]);
  expect(scan('TODO: precios', 'es').length, 'a Spanish "TODO:" is still a note').toBe(1);
  expect(scan('VER TODO', 'en').length, 'an English "TODO" is a note').toBe(1);

  // One finding per leftover, however it is spaced; and PLACEHOLDER_ALLOWLIST ignores case and spacing.
  expect(scan('Call [BOLD SLOT] or [ BOLD SLOT ] or [BOLD\nSLOT] or [BO LD SLOT]').map((f) => f.match),
    'one finding per leftover, whatever its spacing').toEqual(['[BOLD SLOT]']);
  expect(scan('Download [ PDF ] or [P DF]').length, 'a "[PDF]" is a finding until it is allow-listed').toBe(1);
  expect(unseenSlots('as [the team] and [the  team] said')).toEqual(['[the team]']);
  PLACEHOLDER_ALLOWLIST.add('[pdf]').add('[The Team]');
  try {
    expect(scan('Download [ PDF ] or [P DF]'), 'PLACEHOLDER_ALLOWLIST must cover a rule match').toEqual([]);
    expect(unseenSlots('as [the team] said'), 'PLACEHOLDER_ALLOWLIST must cover the lower-case check').toEqual([]);
  } finally {
    PLACEHOLDER_ALLOWLIST.delete('[pdf]');
    PLACEHOLDER_ALLOWLIST.delete('[The Team]');
  }

  // The verdicts. On an unlisted target a leftover fails, on a developer's machine and in CI.
  const local = { listed: false, ci: false };
  const inCi = { listed: false, ci: true };
  const pending = { listed: true, ci: false };
  expect(verdict('/x', 'Prices: FIXME', local).fail, 'a leftover must fail').not.toBeNull();
  expect(verdict('/x', 'Prices: FIXME', inCi).fail, 'a leftover must fail in CI').not.toBeNull();
  expect(verdict('/x', 'All filled in.', local), 'clean copy must pass in silence').toEqual({ fail: null, warn: null });
  // The content placeholder: reported locally so a draft branch can be pushed, failed in CI.
  expect(verdict('/x', 'Built in [MISSING: year].', local).fail, 'a draft placeholder must not fail locally').toBeNull();
  expect(verdict('/x', 'Built in [MISSING: year].', local).warn, 'a draft placeholder must be reported').not.toBeNull();
  expect(verdict('/x', 'Built in [MISSING: year].', inCi).fail, 'a draft placeholder must fail in CI').not.toBeNull();
  expect(verdict('/x', 'Built in [MIS SING: year].', local).fail, 'a draft placeholder split by markup is still one').toBeNull();
  expect(verdict('/x', '[MISSING: year] FIXME', local).fail, 'another leftover beside it must still fail').not.toBeNull();
  expect(verdict('/x', 'Baujahr [FEHLT: Jahr]', local).fail, 'a token this file does not know is a plain slot').not.toBeNull();
  // A listed target: leftovers only warn, a filled one may not stay listed, and it may
  // not hide a slot the rules cannot see.
  expect(verdict('/x', 'Updated [DATE]', pending), 'a listed target with leftovers only warns')
    .toMatchObject({ fail: null, warn: expect.stringContaining('not ready to launch') });
  expect(verdict('/x', 'Built in [MISSING: year].', pending).fail, 'a content placeholder counts as a leftover there').toBeNull();
  expect(verdict('/x', 'All filled in.', pending).fail, 'a filled target must not stay listed').toContain('nothing left to fill');
  expect(verdict('/x', 'Hosted [DATE] [self-hosted on our own server / operated for us]', pending).fail,
    'a lower-case slot on a listed target must fail').toContain('cannot see');
  // And judge acts on the verdict: a failing one throws.
  expect(() => judge('/x', 'Prices: FIXME'), 'judge must fail the test').toThrow();
  expect(() => judge('/x', 'All filled in.'), 'judge must pass clean copy').not.toThrow();
});

test('placeholders — UNFILLED_UNTIL_LAUNCH names only checked targets', () => {
  const checked = new Set<string>([...PAGES, ...STATIC_FILES]);
  const stale = [...UNFILLED_UNTIL_LAUNCH].filter((t) => !checked.has(t));
  expect(
    stale,
    `UNFILLED_UNTIL_LAUNCH lists ${stale.join(', ')}, which this spec does not check (not in ` +
      `PAGES, not a static file). Page renamed → rename the entry. Page removed → delete it.`,
  ).toEqual([]);
});

// Everything a page serves that a visitor, a search engine or a share card can read.
async function readPage(page: Page): Promise<{ text: string; lang: string }> {
  const { text, jsonLd, lang } = await page.evaluate(({ shownAsText, exempt }) => {
    const body = document.body.cloneNode(true) as HTMLElement;
    // A space around every element the browser lays out as a block (and every <br>), for
    // the first of the readings below. Layout is read from the live page, because a copy
    // has none. A hidden element (display: none) has no layout of its own to ask, so the
    // browser is asked how it lays out a bare element of the same tag on this page: a
    // hidden <span> or <del> stays inline, a hidden <div> is a block. A block is what the
    // browser calls block, flex, grid, table (and table parts), list-item or flow-root, or
    // what stays `none` when bare (script, template, rp); every other answer is inline:
    // inline*, contents, and ruby, which is what Chromium answers for <ruby>. A hidden
    // element the page has registered as a custom element is not asked: a bare one would
    // run that element's own code on the page under test. It counts as inline, which is
    // the browser's answer for a custom element the page does not style.
    const live = Array.from(document.body.querySelectorAll('*'));
    const copied = Array.from(body.querySelectorAll('*'));
    const bare = new Map<string, string>();
    const displayOfBare = (el: Element) => {
      const tag = el.tagName;
      if (customElements.get(el.localName)) return 'inline';
      if (!bare.has(tag)) {
        // In the element's own namespace: an SVG <text> is a block, an HTML element of
        // that name is not.
        const probe = document.createElementNS(el.namespaceURI, el.localName);
        document.body.append(probe);
        bare.set(tag, getComputedStyle(probe).display);
        probe.remove();
      }
      return bare.get(tag)!;
    };
    const spaces: Text[] = [];
    live.forEach((el, i) => {
      let display = getComputedStyle(el).display;
      if (display === 'none') display = displayOfBare(el);
      const block = /^(block|flex|grid|table|list-item|flow-root|-webkit-box|none)/.test(display);
      if (!block && el.tagName !== 'BR') return;
      const before = new Text(' ');
      const after = new Text(' ');
      copied[i].before(before);
      copied[i].after(after);
      spaces.push(before, after);
    });
    body.querySelectorAll(`script, style, noscript, ${exempt}`).forEach((el) => el.remove());
    // Text nodes, not innerText: content the layout hides (a closed <details>, a
    // collapsed menu) is still served and still indexed.
    const textNodes = () => {
      const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
      const nodes: string[] = [];
      while (walker.nextNode()) nodes.push(walker.currentNode.nodeValue ?? '');
      return nodes;
    };
    const bounded = textNodes();
    spaces.forEach((space) => space.remove());
    const served = textNodes();
    // Three readings of the same copy, because none is safe alone. Fused, with a space
    // around each block: a word or slot split by inline markup stays whole
    // ("Lo<em>rem</em>"), also at the start of a block the HTML puts no space before:
    // "<p>Prices</p><p>Lo<em>rem</em> ipsum</p>" reads "PricesLorem ipsum" without those
    // spaces and "Prices Lo rem ipsum" with one between all text nodes, and neither is a
    // match. Fused as served, with no spaces added: an element the page lays out as a
    // block inside a word (a floated first letter, the items of a flex heading) does not
    // split it, and neither does a wrong answer about a hidden element. Spaced: one inline
    // element's last word never fuses with the next one's first ("pricesTODO"). The fused
    // readings come first, so a leftover several readings see is printed in its unbroken
    // spelling. Not seen by any of the three: a leftover split by inline markup at the
    // start of an inline element that follows another one with no space between them
    // ("<span>Prices</span><span>Lo<em>rem</em> ipsum</span>").
    const copy = [bounded.join(''), served.join(''), served.join(' ')];
    // Same <head> surfaces as tone.spec.ts: user-facing in SERPs and share cards.
    const metaSel = [
      'meta[name="description"]',
      'meta[property="og:title"]', 'meta[property="og:description"]',
      'meta[name="twitter:title"]', 'meta[name="twitter:description"]',
    ];
    const meta = [document.title, ...metaSel.map((s) => document.querySelector(s)?.getAttribute('content') ?? '')];
    // Attributes a visitor reads or hears, and what a form field shows: its current
    // value (as set in the HTML or by the page's own scripts), for the input types
    // that display it as text.
    const attrs = Array.from(document.querySelectorAll('[alt], [aria-label], [title], [placeholder], input'))
      .filter((el) => !el.closest(exempt))
      .flatMap((el) => [
        el.getAttribute('alt'), el.getAttribute('aria-label'), el.getAttribute('title'),
        el.getAttribute('placeholder'),
        el instanceof HTMLInputElement && shownAsText.includes(el.type) ? el.value : null,
      ].map((v) => v ?? ''));
    const jsonLd = Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
      .map((el) => el.textContent ?? '');
    return { text: [...meta, ...copy, ...attrs].join('\n'), jsonLd, lang: document.documentElement.lang || '' };
  }, { shownAsText: SHOWN_AS_TEXT, exempt: PLACEHOLDER_EXEMPT });
  // JSON-LD that does not parse is seo.spec.ts's failure; here it is still read, raw.
  return { text: [text, ...jsonLd.map((raw) => jsonStrings(raw) ?? raw)].join('\n'), lang };
}

// The reading itself, pinned in a real browser: one leftover planted on each surface
// readPage reads, and one on each place it must leave out. Checked against the
// matches themselves, not against the printed lines, whose context also shows
// neighbouring text.
test('placeholders — the page reading reaches each surface it claims', async ({ page }) => {
  // No slider here: the browser turns a range input's value into a number, so it
  // cannot carry text either way.
  const notShown = ['hidden', 'checkbox', 'radio', 'password'];
  // Named here on purpose, not taken from SHOWN_AS_TEXT: dropping a type from the
  // reader must fail this test. A type added to the reader is planted as well.
  const mustShow = ['text', 'search', 'email', 'tel', 'url', 'submit', 'button', 'reset'];
  const shown = [...new Set([...mustShow, ...SHOWN_AS_TEXT])];
  await page.setContent(`<!doctype html><html lang="en-GB"><head>
    <title>[TITLE SLOT]</title>
    <meta name="description" content="[DESCRIPTION SLOT]">
    <meta property="og:title" content="[OG TITLE SLOT]">
    <meta property="og:description" content="[OG DESCRIPTION SLOT]">
    <meta name="twitter:title" content="[TWITTER TITLE SLOT]">
    <meta name="twitter:description" content="[TWITTER DESCRIPTION SLOT]">
    <script type="application/ld+json">{"name":"\\u005bSCHEMA\\nSLOT\\u005d"}</script>
    </head><body>
    <p>Call [<strong>BOLD SLOT</strong>] now.</p>
    <p>Ask [IN<strong>NER</strong> SLOT] too.</p>
    <p>Visit [BROKEN
       SLOT] soon.</p>
    <p>Lo<em>rem</em> ipsum.</p>
    <span>prices</span><span>TODO</span>
    <p>Prices</p><p>do<em>lor</em> sit amet</p><p>Terms</p><p><b>FIX</b>ME</p><p>Rates<br><b>XX</b>X</p>
    <p>Sizes</p><p>dum<span hidden>my</span> text</p><div hidden>Fees</div><div hidden><b>blind</b>text</div>
    <p>Notes</p><p>place<del hidden>holder</del> text</p>
    <p>Dates</p><p>dum<ins hidden>my</ins> copy</p><p>Names</p><p>place<ruby hidden>holder</ruby> copy</p>
    <p>Towns</p><p>muster<button hidden>stadt</button></p><p>Firms</p><p>muster<ruby>firma</ruby></p>
    <ul><li>Stock</li><li>dum<em>my</em> content</li></ul><table><tr><td>Cost</td><td>place<b>holder</b> image</td></tr></table>
    <div>Shelf<div style="display:flow-root">place<b>holder</b> content</div></div>
    <div>Crate<div style="display:-webkit-box">tex<i>t</i> goes here</div></div>
    <div>Bench<div style="display:flex"><span style="display:contents">your head<em style="display:contents">line</em> here</span></div></div>
    <div>Chest<div style="display:grid"><span style="display:contents">co<em style="display:contents">py</em> goes here</span></div></div>
    <p><span style="float:left">J</span>ohn doe</p> <h2 style="display:flex"><span>muster</span><span>strasse</span></h2>
    <p>ma<script></script>x mustermann</p>
    <style>body > u { display: block; }</style> <p>eri<u hidden>ka</u> mustermann</p>
    <script>customElements.define('x-probe', class extends HTMLElement {
      connectedCallback() { window.mounted = (window.mounted || 0) + 1; }
    });</script>
    <x-probe hidden></x-probe>
    <style>x-note { display: block; }</style> <div>Vault<x-note style="display:none">platz<b>halter</b>text</x-note></div>
    <svg width="1" height="1"><title>Rows</title><text style="display:none">ja<tspan>ne</tspan> doe</text></svg>
    <details><summary>More</summary><p>[FOLDED SLOT]</p></details>
    <img alt="[ALT SLOT]" src="data:,">
    <button aria-label="[LABEL SLOT]">Go</button>
    <abbr title="[TITLE ATTRIBUTE SLOT]">x</abbr>
    <input placeholder="[HINT SLOT]">
    ${shown.map((t) => `<input type="${t}" value="[VALUE OF ${t.toUpperCase()}]">`).join('\n')}
    <input id="late">
    <script>document.getElementById('late').value = '[SCRIPTED SLOT]';</script>
    ${notShown.map((t) => `<input type="${t}" value="[UNSEEN ${t.toUpperCase()}]">`).join('\n')}
    <code>[IN CODE]</code> <pre>[IN PRE]</pre> <kbd>[IN KBD]</kbd> <samp>[IN SAMP]</samp>
    <p data-placeholder-exempt>[EXEMPT NOTE] <img alt="[EXEMPT ALT]" src="data:,"></p>
    <noscript>[IN NOSCRIPT]</noscript>
    <style>.x::after { content: '[IN STYLE]'; }</style>
    <script>window.note = '[IN SCRIPT]';</script>
    </body></html>`);
  const { text, lang } = await readPage(page);
  expect(lang, 'the page language must reach the rules').toBe('en-GB');
  const findings = scan(text, lang);
  const mustFind = [
    'TITLE SLOT', 'DESCRIPTION SLOT', 'OG TITLE SLOT', 'OG DESCRIPTION SLOT', 'TWITTER TITLE SLOT',
    'TWITTER DESCRIPTION SLOT', 'SCHEMA SLOT', 'BOLD SLOT', 'INNER SLOT', 'BROKEN SLOT', 'FOLDED SLOT',
    'ALT SLOT', 'LABEL SLOT', 'TITLE ATTRIBUTE SLOT', 'HINT SLOT', 'SCRIPTED SLOT',
    ...shown.map((t) => `VALUE OF ${t.toUpperCase()}`),
  ];
  const hits = (m: string) => findings.filter((f) => squash(f.match) === squash(`[${m}]`)).length;
  expect(mustFind.filter((m) => hits(m) !== 1), 'planted slots not found exactly once').toEqual([]);
  expect(findings.find((f) => squash(f.match) === '[INNERSLOT]')?.match, 'printed in its unbroken spelling').toBe('[INNER SLOT]');
  // Two leftovers that one kind of reading misses: "Lorem ipsum" needs a fused reading,
  // "TODO" needs the spaced one.
  const found = (label: string, match: string) => findings.some((f) => f.label === label && squash(f.match).toLowerCase() === match);
  expect(found('filler text', 'loremipsum'), '"Lo<em>rem</em> ipsum" needs the fused reading').toBe(true);
  expect(found('author note', 'todo'), '"prices" + "TODO" needs the spaced reading').toBe(true);
  // A leftover split by inline markup at the start of a block, with no space in the HTML
  // before that block: only the fused reading with its block boundaries sees these.
  expect(found('filler text', 'dolorsitamet'), '"<p>Prices</p><p>do<em>lor</em> sit amet</p>"').toBe(true);
  expect(found('author note', 'fixme'), '"<p>Terms</p><p><b>FIX</b>ME</p>"').toBe(true);
  expect(found('author note', 'xxx'), '"Rates<br><b>XX</b>X"').toBe(true);
  // Hidden elements: a hidden inline piece of a word still fuses, a hidden block still ends one.
  expect(found('placeholder wording', 'dummytext'), '"dum<span hidden>my</span> text"').toBe(true);
  expect(found('placeholder wording', 'blindtext'), '"<div hidden>Fees</div><div hidden><b>blind</b>text</div>"').toBe(true);
  expect(found('placeholder wording', 'placeholdertext'), '"place<del hidden>holder</del> text": no list of tags, the browser says <del> is inline').toBe(true);
  expect(found('placeholder wording', 'dummycopy'), '"dum<ins hidden>my</ins> copy"').toBe(true);
  expect(found('placeholder wording', 'placeholdercopy'), '"place<ruby hidden>holder</ruby> copy": Chromium lays <ruby> out as "ruby", which is inline').toBe(true);
  expect(found('placeholder wording', 'musterstadt'), '"muster<button hidden>stadt</button>": inline-block').toBe(true);
  expect(found('placeholder wording', 'musterfirma'), '"muster<ruby>firma</ruby>": a <ruby> that is shown').toBe(true);
  // The other kinds of block. What a flex or grid box holds is laid out as blocks itself,
  // unless it is display: contents; only then does the box's own boundary decide.
  expect(found('placeholder wording', 'dummycontent'), '"<li>Stock</li><li>dum<em>my</em> content</li>": list-item').toBe(true);
  expect(found('placeholder wording', 'placeholderimage'), '"<td>Cost</td><td>place<b>holder</b> image</td>": table-cell').toBe(true);
  expect(found('placeholder wording', 'placeholdercontent'), '"Shelf<div style="display:flow-root">place<b>holder</b> content</div>"').toBe(true);
  expect(found('placeholder wording', 'textgoeshere'), '"Crate<div style="display:-webkit-box">tex<i>t</i> goes here</div>"').toBe(true);
  expect(found('placeholder wording', 'yourheadlinehere'), '"Bench<div style="display:flex">…your head<em>line</em> here…</div>", the children display: contents: flex').toBe(true);
  expect(found('placeholder wording', 'copygoeshere'), '"Chest<div style="display:grid">…co<em>py</em> goes here…</div>", the children display: contents: grid').toBe(true);
  // What only the fused reading as served sees: the spaces around blocks split these.
  expect(found('placeholder wording', 'johndoe'), '"<span style="float:left">J</span>ohn doe": a floated first letter is a block').toBe(true);
  expect(found('placeholder wording', 'musterstrasse'), '"<span>muster</span><span>strasse</span>" in a flex heading: each item is a block').toBe(true);
  expect(found('placeholder wording', 'maxmustermann'), '"ma<script></script>x mustermann": a script counts as a block').toBe(true);
  expect(found('placeholder wording', 'erikamustermann'), '"eri<u hidden>ka</u> mustermann" where the page styles "body > u" as a block: the bare <u> is asked, and answers wrongly').toBe(true);
  expect(found('placeholder wording', 'janedoe'), '"<title>Rows</title><text style="display:none">ja<tspan>ne</tspan> doe</text>" in an <svg>: a hidden SVG <text> is a block, an HTML element of that name is not').toBe(true);
  expect(found('placeholder wording', 'platzhaltertext'), '"Vault<x-note style="display:none">platz<b>halter</b>text</x-note>", which the page styles as a block and has not registered: it is asked like any other tag').toBe(true);
  expect(await page.evaluate(() => (window as unknown as { mounted: number }).mounted), 'a hidden custom element must not be built a second time to ask for its layout').toBe(1);
  const mustSkip = [
    ...notShown.map((t) => `UNSEEN ${t.toUpperCase()}`),
    'IN CODE', 'IN PRE', 'IN KBD', 'IN SAMP', 'EXEMPT NOTE', 'EXEMPT ALT', 'IN NOSCRIPT', 'IN STYLE',
    'IN SCRIPT',
  ];
  expect(mustSkip.filter((m) => text.includes(m)), 'text that must stay out of the reading').toEqual([]);
});

for (const path of PAGES) {
  test(`placeholders — no leftover on ${path}`, async ({ page }) => {
    await page.goto(path);
    const { text, lang } = await readPage(page);
    judge(path, text, lang);
  });
}

// The legal pages' draft notice, pinned by example (AGENTS.md §5).
test('placeholders — the draft notice rules pick the legal pages and read the answer', () => {
  for (const p of ['/privacy', '/impressum', '/datenschutz', '/de/privacy', '/fr/privacy', '/de/impressum']) {
    expect(isLegalPage(p), `${p} is a legal page`).toBe(true);
  }
  for (const p of ['/', '/about', '/legal', '/privacy-policy', '/privacy/team', '/blog/privacy-tips']) {
    expect(isLegalPage(p), `${p} is not selected: only the last segment decides`).toBe(false);
  }
  // Each note is a slot, so a listed page reports it as "not ready to launch".
  for (const note of LEGAL_NOTES) {
    expect(scan(note).map((f) => f.label), 'a note must match the slot rule once').toEqual(['unfilled [SLOT]']);
  }
  // The recorded answer: exactly the three forms, a date of the right shape, a line of its own.
  const accepted = [
    'legal pages: reviewed by a lawyer (2026-11-02)',
    'legal pages: own texts (2026-11-02)',
    "legal pages: published as drafted (owner's decision, 2026-11-02)",
    '# Site\n\nlegal pages: own texts (2026-11-02)\r\nmore\n',
  ];
  const refused = [
    '',
    'legal pages: reviewed by a lawyer (soon)',
    'legal pages: reviewed by a lawyer (2026-1-2)',
    'legal pages: reviewed by a lawyer 2026-11-02',
    'legal pages: checked (2026-11-02)',
    'legal pages: published as drafted (2026-11-02)',
    'Legal pages: own texts (2026-11-02)',
    'we said legal pages: own texts (2026-11-02)',
    'legal pages: own texts (2026-11-02) and more',
    'legal pages: own texts\n(2026-11-02)',
  ];
  expect(accepted.filter((r) => !hasLegalRecord(r)), 'recorded forms the test no longer accepts').toEqual([]);
  expect(refused.filter(hasLegalRecord), 'near misses the test now accepts').toEqual([]);
  // A missing README.md is no record; a README.md that cannot be read is an error.
  const empty = mkdtempSync(join(tmpdir(), 'legal-readme-'));
  try {
    expect(readme(empty), 'a missing README.md counts as no record').toBe('');
    writeFileSync(join(empty, 'README.md'), '# Site\n\nlegal pages: own texts (2026-11-02)\n');
    expect(hasLegalRecord(readme(empty)), 'the answer is read from README.md in the given folder').toBe(true);
    rmSync(join(empty, 'README.md'));
    mkdirSync(join(empty, 'README.md'));
    expect(() => readme(empty), 'a README.md that cannot be read must not pass as empty').toThrow();
  } finally {
    rmSync(empty, { recursive: true, force: true });
  }
  expect(existsSync(join(process.cwd(), 'package.json')), 'the tests must run from the folder that holds package.json, where the answer is read').toBe(true);
  // The verdict: a note on a listed page, or a record. Nothing else.
  const fine = (listed: boolean, noteVisible: boolean, recorded: boolean) => legalVerdict('/privacy', { listed, noteVisible, recorded });
  expect(fine(true, true, false), 'listed with its note is fine').toBeNull();
  expect(fine(true, false, true), 'a recorded answer clears the note').toBeNull();
  expect(fine(false, false, true), 'a recorded answer clears the note and the entry').toBeNull();
  expect(fine(false, true, true), 'a recorded answer with the note still on is not this test\'s business').toBeNull();
  expect(fine(true, false, false), 'the note gone with no answer fails').toContain('AGENTS.md section 5');
  expect(fine(false, true, false), 'the page delisted with the note on and no answer fails').toContain('is not listed in UNFILLED_UNTIL_LAUNCH and shows its draft notice');
  expect(fine(false, false, false), 'neither the note nor an answer fails').not.toBeNull();
  expect(fine(true, false, false)).toContain('legal pages: published as drafted (owner\'s decision, YYYY-MM-DD)');
});

// The notice reading, pinned in a real browser: the note planted where it counts and
// where it must not, as the notes are told apart from a page that only looks like one.
test('placeholders — the draft notice is read as a visitor sees it', async ({ page }) => {
  const [en, de] = LEGAL_NOTES;
  const seen = async (body: string, head = '', lang = 'en') => {
    await page.setContent(`<!doctype html><html lang="${lang}"><head><title>Privacy</title>${head}</head><body><h1>Privacy</h1>${body}</body></html>`);
    return noteIsVisible(page);
  };
  expect(await seen(`<p>${en}</p>`), 'the English note shows').toBe(true);
  expect(await seen(`<p>${de}</p>`, '', 'de'), 'the German note shows').toBe(true);
  expect(await seen(`<p>${en}</p>`, '', 'fr'), 'a note counts on a page of any language').toBe(true);
  expect(await seen(`<p>\n  ${en.replace(' It cannot', '\n   It cannot')}\n</p>`), 'line breaks in the source do not matter').toBe(true);
  expect(await seen(`<p>${en.replace('first draft', 'rough sketch')}</p>`), 'a reworded note').toBe(false);
  expect(await seen(`<p>${en.replace(' Ask a lawyer to review it before you publish, or replace it with your own text.', '')}</p>`), 'a cut note').toBe(false);
  expect(await seen('<p>[A NOTE OF OTHER WORDS THAN ANY IN LEGAL_NOTES, DELETE BEFORE LAUNCH.]</p>'),
    'a note whose text is not in LEGAL_NOTES is not seen').toBe(false);
  expect(await seen('<p>Nothing here.</p>'), 'no note').toBe(false);
  expect(await seen(`<!-- ${en} -->`), 'in a comment').toBe(false);
  expect(await seen(`<p>${en}</p>`.replace('<p>', '<p style="display:none">')), 'display: none').toBe(false);
  expect(await seen(`<p style="visibility:hidden">${en}</p>`), 'visibility: hidden').toBe(false);
  expect(await seen(`<p hidden>${en}</p>`), 'the hidden attribute').toBe(false);
  expect(await seen('<p>x</p>', `<meta name="description" content="${en}">`), 'in a meta tag').toBe(false);
  expect(await seen('<p>x</p>', `<script type="application/ld+json">{"description":"${en}"}</script>`), 'in a script').toBe(false);
  expect(await seen(`<p data-note="${en}">x</p>`), 'in an attribute').toBe(false);
});

// Enters the way an owner's run does: the rendered page and the README.md in this folder.
// Catches, with no answer recorded, a note that was dropped, reworded, put in a comment, the
// frontmatter or a meta tag, or hidden (display: none, visibility: hidden, hidden), and a
// page taken out of UNFILLED_UNTIL_LAUNCH while its note is on. It cannot catch a recorded
// answer that is not true; a note made unreadable another way (opacity: 0, off-screen, text
// in a hidden child); a legal page added after the answer; a page at another address
// (/legal); or a note in another language than its page. In the toolkit the folder is
// templates/astro, whose README.md has no answer, so /privacy and /impressum hold their notes.
for (const path of PAGES.filter(isLegalPage)) {
  test(`placeholders — ${path} keeps its draft notice until the owner's answer is recorded`, async ({ page }) => {
    await page.goto(path);
    const fail = legalVerdict(path, { listed: UNFILLED_UNTIL_LAUNCH.has(path), noteVisible: await noteIsVisible(page), recorded: hasLegalRecord(readme()) });
    expect(fail === null, fail ?? '').toBe(true);
  });
}

for (const file of STATIC_FILES) {
  test(`placeholders — no leftover in ${file}`, async ({ request, baseURL }) => {
    const res = await request.get(new URL(file, baseURL!).href);
    // Anything but "served" or "not there" must not pass as "nothing found".
    expect([200, 404], `${file} answered ${res.status()}, so it was not checked`).toContain(res.status());
    if (res.status() === 404) {
      // This site ships no such file: nothing to read, and nothing to keep listed.
      expect(
        UNFILLED_UNTIL_LAUNCH.has(file),
        `${file} is not served by this site but is still listed in UNFILLED_UNTIL_LAUNCH. Delete its entry.`,
      ).toBe(false);
      return;
    }
    const strings = jsonStrings(await res.text());
    expect(strings, `${file} is not valid JSON, so it was not checked`).not.toBeNull();
    judge(file, strings ?? '');
  });
}
