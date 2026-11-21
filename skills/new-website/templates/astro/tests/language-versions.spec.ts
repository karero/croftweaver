import { test } from '@playwright/test';
import { PAGES } from './_helpers';
import { SITE } from '../src/config';

// A page in several languages keeps the same shape in every language. A page's language set is
// the pages its hreflang links name (x-default apart); one test compares every set:
//   • FAILS when the versions differ in heading count per level, in image count, or when one
//     version of a set does not list the same versions as another.
//   • WARNS, and passes, when numbers differ. A changed number is the usual quiet drift, but a
//     number can also be wording ("zu 100 %" for "you own"), so the owner decides, in chat.
// What it reads: the body without nav, header, footer, script, style, template, noscript and
// anything inside an element marked data-versions-exempt="why" (a reason is required).
// Numbers are digit groups, so 1,200 / 1.200 / 1 200 match. Wording, ids and links may differ.

const NO_SETS = 'No page names versions in other languages (hreflang), so there is nothing to compare';
const FIX = 'Make the same change on every version, or mark text that belongs to one language with `data-versions-exempt="why"` on an HTML element.';
const TELL = "Not a failure. Tell the site's owner in plain words and ask whether each difference is meant. If it is not, make the same change on every version.";
const LEVELS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'];

type Seen = { alts: { hreflang: string; href: string }[]; heads: Record<string, number>; imgs: number; numbers: Record<string, number>; blankExempt: number };

const key = (url: string) => new URL(url, SITE.url).href;
const sameSite = (url: string) => new URL(url, SITE.url).origin === new URL(SITE.url).origin;
const byValue = (a: string, b: string) => a.length - b.length || (a < b ? -1 : a > b ? 1 : 0);

test('language versions of a page stay in step', async ({ page }) => {
  test.slow(); // one visit to every page
  const route = new Map<string, string>(PAGES.map((p) => [key(p), p]));
  const seen = new Map<string, Seen>();
  for (const path of PAGES) {
    await page.goto(path);
    const alts = await page.$$eval('link[rel="alternate"][hreflang]', (els) =>
      els.map((e) => ({ hreflang: (e.getAttribute('hreflang') || '').toLowerCase(), href: e.getAttribute('href') || '' })),
    );
    const read = await page.evaluate(() => {
      const root = document.body.cloneNode(true) as HTMLElement;
      const blankExempt = [...root.querySelectorAll('[data-versions-exempt]')].filter((e) => !(e.getAttribute('data-versions-exempt') || '').trim()).length;
      root.querySelectorAll('nav, header, footer, script, style, template, noscript, [data-versions-exempt]').forEach((e) => e.remove());
      const heads: Record<string, number> = {};
      for (const h of ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']) heads[h] = root.querySelectorAll(h).length;
      const parts: string[] = [];
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) parts.push(n.nodeValue || '');
      return { heads, imgs: root.querySelectorAll('img').length, text: parts.join(' '), blankExempt };
    });
    const numbers: Record<string, number> = {};
    for (const n of read.text.match(/[0-9]+/g) ?? []) numbers[n] = (numbers[n] ?? 0) + 1;
    seen.set(path, { alts, heads: read.heads, imgs: read.imgs, numbers, blankExempt: read.blankExempt });
  }

  // Each page's own list of versions: its same-site alternates, x-default apart, as URLs.
  const listed = new Map<string, Set<string>>();
  for (const [path, s] of seen) {
    listed.set(path, new Set(s.alts.filter((a) => a.hreflang !== 'x-default' && a.href && sameSite(a.href)).map((a) => key(a.href))));
  }
  const sets = new Map<string, string[]>(); // one entry per distinct set of 2 or more versions
  for (const members of listed.values()) if (members.size >= 2) sets.set([...members].sort().join(' '), [...members]);
  if (!sets.size) {
    console.log(NO_SETS);
    test.skip(true, NO_SETS);
  }

  const failures: string[] = [];
  const name = (url: string) => route.get(url) ?? url;
  for (const [path, s] of seen) {
    if (s.blankExempt) failures.push(`${path}: ${s.blankExempt} element(s) have data-versions-exempt with no reason. Write why that text belongs to one language, as data-versions-exempt="why".`);
    for (const a of s.alts) {
      if (a.hreflang === 'x-default' || !a.href || !sameSite(a.href) || route.has(key(a.href))) continue;
      failures.push(`${path}: alternate "${a.hreflang}" → ${a.href} is same-site but not a PAGES route (tests/_helpers.ts). Fix the href, or add the page to PAGES.`);
    }
  }
  // Every version of a set lists the same versions (Google: each lists itself and all others).
  const leftOut = new Set<string>();
  for (const [path, members] of listed) {
    for (const m of members) {
      const other = route.get(m);
      if (!other || other === path) continue;
      const theirs = listed.get(other)!;
      const missing = [...members].filter((u) => !theirs.has(u) && route.has(u)).map((u) => (u === m ? 'itself' : name(u)));
      if (missing.length) leftOut.add(`${other} leaves out ${missing.join(', ')}, which ${path} lists. Every version must list every version, itself included.`);
    }
  }
  failures.push(...leftOut);

  for (const members of sets.values()) {
    const pages = members.map((u) => route.get(u)).filter((p): p is string => !!p);
    if (pages.length < 2) continue;
    const title = pages.join(', ');
    const heads = LEVELS.filter((l) => new Set(pages.map((p) => seen.get(p)!.heads[l])).size > 1);
    if (heads.length) {
      failures.push(`Headings differ between the versions ${title}: ` + pages.map((p) => `${p} has ${heads.map((l) => `${seen.get(p)!.heads[l]} ${l}`).join(' and ')}`).join('; ') + `. ${FIX}`);
    }
    if (new Set(pages.map((p) => seen.get(p)!.imgs)).size > 1) {
      failures.push(`Image counts differ between the versions ${title}: ` + pages.map((p) => `${p} has ${seen.get(p)!.imgs}`).join(', ') + `. ${FIX}`);
    }
    const all = [...new Set(pages.flatMap((p) => Object.keys(seen.get(p)!.numbers)))].sort(byValue);
    const differing = all.filter((n) => new Set(pages.map((p) => seen.get(p)!.numbers[n] ?? 0)).size > 1);
    if (differing.length) {
      const lines = differing.map((n) => `  ${n}: ` + pages.map((p) => `${seen.get(p)!.numbers[n] ?? 0} on ${p}`).join(', '));
      const warn = `The versions ${title} have different numbers (how many times each appears):\n${lines.join('\n')}\n${TELL}`;
      console.warn('⚠ language versions: ' + warn);
      test.info().annotations.push({ type: 'warning', description: warn });
    }
  }
  if (failures.length) throw new Error(`Language versions differ:\n- ${failures.join('\n- ')}`);
});
