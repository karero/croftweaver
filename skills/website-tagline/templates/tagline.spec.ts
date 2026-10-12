import { test, expect } from '@playwright/test';
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { SITE } from '../src/config';

// Guards the tagline (see TAGLINE.md): the line on the page is SITE.tagline word for
// word, it is a paragraph and not a heading, it is typed in one place only, and it
// keeps to the length a line under a logo can have. Hermetic checks, a sibling of
// positioning.spec.ts: no network, no extraction library.
//
// This file lives in the website-tagline skill rather than the new-website Astro
// overlay because a fresh scaffold shows no tagline. Copy it into tests/ once the
// site shows the line, then set CONFIG.selector. While it is empty every test skips
// with a stated reason, so an unconfigured copy reports "not applicable" instead of
// failing like a product bug. It needs the site's src/config.ts, as the other specs do.

// ── EDIT THIS BLOCK ──────────────────────────────────────────────────────────
const CONFIG = {
  /**
   * CSS selector of the one element that shows the tagline (e.g. 'header .tagline').
   * Empty = every test skips.
   */
  selector: '',
  /** Pages to check. A header is shared, so the home page is usually enough. */
  pages: ['/'],
  /** The skill's limits for a line under a logo (website-tagline §3). */
  maxWords: 8,
  maxChars: 50,
};
// ─────────────────────────────────────────────────────────────────────────────

// What the starter ships in SITE.tagline. A site that still holds it has no tagline yet.
const PLACEHOLDER = 'One-line positioning.';
// Source files that can hold page copy. The line may appear in src/config.ts only.
const COPY_FILES = /\.(astro|ts|tsx|js|jsx|mjs|md|mdx|html|json|ya?ml)$/;

// Whitespace only: a line wrapped onto two lines in the source still counts as the
// same line. Case and punctuation stay as they are, because the line is verbatim.
const norm = (s: string) => s.replace(/\s+/g, ' ').trim();
const line = norm(SITE.tagline);

// A copy in a source file may be written with a backslash before a quote
// ('Freelancers\' evenings back.'), with a numeric character reference (&#39;, &#039;,
// &#x27;) or with one of six named entities. All of these are undone before the search,
// so an escaped copy is still a copy. Any other named entity (&eacute;) is left as it
// is: a copy written with one is not found.
const NAMED: Record<string, string> = {
  amp: '&', quot: '"', apos: "'", rsquo: '\u2019', lsquo: '\u2018', nbsp: ' ',
};
const unescaped = (source: string) => norm(source
  .replace(/\\(['"`])/g, '$1')
  .replace(/&#(\d{1,7});/g, (_, digits: string) => String.fromCodePoint(Math.min(Number(digits), 0x10ffff)))
  .replace(/&#[xX]([0-9a-fA-F]{1,6});/g, (_, hex: string) => String.fromCodePoint(Math.min(parseInt(hex, 16), 0x10ffff)))
  .replace(/&(amp|quot|apos|rsquo|lsquo|nbsp);/g, (_, name: string) => NAMED[name]));

// The line counts as typed in a text only where it stands on its own, with no letter
// or digit directly before or after it. A short line inside a longer word is not a copy.
const LETTER_OR_DIGIT = /[\p{L}\p{N}]/u;
const holds = (text: string, needle: string) => {
  for (let at = text.indexOf(needle); at !== -1; at = text.indexOf(needle, at + 1)) {
    // Whole characters, not halves: a letter outside the basic plane takes two places
    // in a string, and half of it would not look like a letter.
    const before = [...text.slice(Math.max(0, at - 2), at)].pop() ?? '';
    const after = [...text.slice(at + needle.length, at + needle.length + 2)][0] ?? '';
    if (!LETTER_OR_DIGIT.test(before) && !LETTER_OR_DIGIT.test(after)) return true;
  }
  return false;
};

test.beforeEach(() => {
  test.skip(!CONFIG.selector,
    'CONFIG.selector is empty: set it to the element that shows the tagline to enable this guard');
});

test.describe('tagline', () => {
  for (const path of CONFIG.pages) {
    test(`the line on ${path} is SITE.tagline, word for word`, async ({ page }) => {
      await page.goto(path);
      const shown = page.locator(CONFIG.selector);
      await expect(shown,
        `"${CONFIG.selector}" should match exactly one element on ${path}: the tagline is shown once`)
        .toHaveCount(1);
      await expect(shown, `the tagline on ${path} is in the page but not visible`).toBeVisible();
      // textContent, not innerText: small caps or uppercase styling does not change the words.
      expect(norm((await shown.textContent()) ?? ''),
        `${path} shows a different line than SITE.tagline in src/config.ts. ` +
        `Read SITE.tagline in the page instead of typing the line there`)
        .toBe(line);
    });

    test(`the line on ${path} is a paragraph, not a heading`, async ({ page }) => {
      await page.goto(path);
      const el = await page.locator(CONFIG.selector).first().evaluate((node) => ({
        tag: node.tagName.toLowerCase(),
        inHeading: !!node.closest('h1, h2, h3, h4, h5, h6'),
      }));
      expect(el,
        `the tagline on ${path} is a <${el.tag}>${el.inHeading ? ' inside a heading' : ''}; ` +
        `it belongs in a <p>, so the page keeps its one <h1> and its heading outline`)
        .toEqual({ tag: 'p', inHeading: false });
    });
  }

  test('the line is typed once: only src/config.ts holds it', () => {
    // An empty line is "in" every file. The limits test below reports the empty config.
    test.skip(line === '', 'SITE.tagline is empty: nothing to search for');
    const src = join(process.cwd(), 'src');
    const copies: string[] = [];
    const walk = (dir: string) => {
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const file = join(dir, entry.name);
        if (entry.isDirectory()) walk(file);
        else if (COPY_FILES.test(entry.name) && relative(src, file) !== 'config.ts'
          && holds(unescaped(readFileSync(file, 'utf8')), line)) {
          copies.push(relative(process.cwd(), file));
        }
      }
    };
    walk(src);
    expect(copies,
      `the tagline is typed again in ${copies.join(', ')}. Read SITE.tagline there instead, ` +
      `or the two copies drift apart the next time the line changes`)
      .toEqual([]);
  });

  test('SITE.tagline is a real line within the limits', () => {
    expect(line, 'SITE.tagline in src/config.ts is empty').not.toBe('');
    expect(line, "SITE.tagline still holds the starter's placeholder").not.toBe(PLACEHOLDER);
    const words = line.split(' ').length;
    expect(words,
      `"${line}" has ${words} words; a line under a logo has at most ${CONFIG.maxWords}`)
      .toBeLessThanOrEqual(CONFIG.maxWords);
    // Counted as a reader sees them: an umlaut counts once however it is stored, and so
    // does an emoji made of several code points.
    const chars = [...new Intl.Segmenter(undefined, { granularity: 'grapheme' }).segment(line)].length;
    expect(chars,
      `"${line}" has ${chars} characters; a line under a logo has at most ${CONFIG.maxChars}`)
      .toBeLessThanOrEqual(CONFIG.maxChars);
  });
});
