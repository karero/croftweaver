import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { PAGES, THEMES } from './_helpers';

// Tables (website-design-system, "Tables"; the CSS is in src/styles/tables.css). Two kinds: "stack"
// (sentences: a table above 40rem, labelled stacked rows below it) and "figures" (short numbers: stays a table
// and must fit in 320px). Two layers. The contract layer puts one table of each kind into the home page, so a
// site with no table still proves the CSS. The scan layer reads the real tables of every page in PAGES.
// All measures are Chromium's (Range rectangles, the accessibility tree); Safari and VoiceOver are not checked.
// Headless Chromium does not hyphenate (hyphens: auto and manual lay out alike there), so no measure can see a hyphen:
// the cells' computed `hyphens` is read instead.

// A page whose tables the site cannot change (a table that comes from outside): path -> why. PAGES stays whole,
// because the sitemap and llms.txt checks need every live route in it.
const TABLE_EXEMPT: Record<string, string> = {};

const PHONES = [360, 320];

test('tables — every exempt page is a live PAGES route and has a reason', () => {
  for (const [path, why] of Object.entries(TABLE_EXEMPT)) {
    expect(PAGES as readonly string[], `${path} is exempt but is not in PAGES`).toContain(path);
    expect(why.trim().length, `${path} is exempt with no reason`).toBeGreaterThan(0);
  }
});

// The first row header is one long word in a table capped at 20rem above the breakpoint. Chromium raises a cell to
// its longest word, so the word only breaks under a rule that lets it shrink (overflow-wrap: anywhere, word-break).
// The second link is one character, so its tap target comes from the rule and not from the text's width.
const FIXTURE = `
<style>@media (min-width: 40.01rem) { #table-fixture .stack { max-width: 20rem; } }</style>
<div id="table-fixture" class="wrap">
  <div class="table-wrap stack" role="region" aria-label="Text table fixture" tabindex="0">
    <table role="table">
      <thead role="rowgroup"><tr role="row">
        <th scope="col" role="columnheader">Item</th><th scope="col" role="columnheader">Steps</th><th scope="col" role="columnheader">Note</th>
      </tr></thead>
      <tbody role="rowgroup">
        <tr role="row">
          <th scope="row" role="rowheader">Internationalisation</th>
          <td role="cell" class="nowrap" data-label="Steps">1, 3, 6</td>
          <td role="cell" data-label="Note">A sentence long enough to wrap onto several lines in a narrow column, as the notes of a real table do.</td>
        </tr>
        <tr role="row">
          <th scope="row" role="rowheader"><a class="tap" href="/">/</a></th>
          <td role="cell" class="nowrap" data-label="Steps">2</td>
          <td role="cell" data-label="Note">Optional.</td>
        </tr>
      </tbody>
    </table>
  </div>
  <div class="table-wrap figures" role="region" aria-label="Figures table fixture" tabindex="0">
    <table>
      <thead><tr><th scope="col">Day</th><th scope="col" class="num">Clicks</th><th scope="col" class="num">Appearances</th></tr></thead>
      <tbody>
        <tr><th scope="row">18 October 2026</th><td class="num">3</td><td class="num">1,139</td></tr>
        <tr><th scope="row">19 October 2026</th><td class="num">13</td><td class="num">2,299</td></tr>
      </tbody>
    </table>
  </div>
</div>`;

async function openFixture(page: Page, width: number, theme: (typeof THEMES)[number] = 'light') {
  await page.setViewportSize({ width, height: 800 });
  await page.addInitScript((t) => {
    try { localStorage.setItem('theme', t); } catch (e) { /* ignore */ }
  }, theme);
  await page.goto(PAGES[0]);
  await page.evaluate((html) => document.querySelector('main')!.insertAdjacentHTML('afterbegin', html), FIXTURE);
}

// What the markup of every .table-wrap under `root` must carry. Returns one line per problem.
function markupProblems(root: string): string[] {
  const out: string[] = [];
  document.querySelectorAll(`${root} table`).forEach((t, i) => {
    const wrap = t.closest('.table-wrap');
    if (!wrap) { out.push(`table ${i} is not inside a .table-wrap`); return; }
    if (wrap.getAttribute('role') !== 'region') out.push(`table ${i}: its .table-wrap has no role="region"`);
    if (!wrap.getAttribute('aria-label')) out.push(`table ${i}: its .table-wrap has no aria-label`);
    if (wrap.getAttribute('tabindex') !== '0') out.push(`table ${i}: its .table-wrap has no tabindex="0"`);
    if (!wrap.classList.contains('stack') && !wrap.classList.contains('figures')) out.push(`table ${i}: its .table-wrap is neither "stack" nor "figures"`);
    const cols = [...t.querySelectorAll('thead th')];
    if (cols.length === 0 || cols.some((h) => h.getAttribute('scope') !== 'col')) out.push(`table ${i}: every header cell needs scope="col"`);
    // One row shape for both kinds: a <th scope="row"> first, a <td> for each other column. Only the cell count skips a row that has colspan.
    t.querySelectorAll('tbody tr').forEach((tr, r) => {
      const [first, ...rest] = [...tr.children];
      if (first?.tagName !== 'TH' || first.getAttribute('scope') !== 'row' || rest.some((c) => c.tagName !== 'TD')) {
        out.push(`table ${i}, row ${r}: the first cell must be a <th scope="row"> and every other cell a <td>`);
      }
      if (!tr.querySelector('[colspan]') && tr.children.length !== cols.length) out.push(`table ${i}, row ${r}: ${tr.children.length} cells for ${cols.length} columns`);
    });
    if (!wrap.classList.contains('stack')) return;
    const roles: [string, string][] = [
      ['', 'table'], ['thead', 'rowgroup'], ['tbody', 'rowgroup'], ['tr', 'row'],
      ['thead th', 'columnheader'], ['tbody th', 'rowheader'], ['td', 'cell'],
    ];
    for (const [sel, role] of roles) {
      const els = sel ? [...t.querySelectorAll(sel)] : [t];
      const wrong = els.filter((e) => e.getAttribute('role') !== role).length;
      if (wrong > 0) out.push(`table ${i}: ${wrong} of ${els.length} "${sel || 'table'}" lack role="${role}"`);
    }
    const norm = (x: string | null) => (x ?? '').replace(/\s+/g, ' ').trim();
    const headers = cols.map((h) => norm(h.textContent));
    t.querySelectorAll('tbody tr').forEach((tr, r) => {
      if (tr.querySelector('[colspan]')) return;
      const tds = [...tr.querySelectorAll(':scope > td')];
      tds.forEach((td, c) => {
        if (norm(td.getAttribute('data-label')) !== headers[c + 1]) {
          out.push(`table ${i}, row ${r}: a cell's data-label is "${td.getAttribute('data-label')}", its column header is "${headers[c + 1]}"`);
        }
      });
    });
  });
  return out;
}

// Words split across lines, and row headers with too many lines, in the cells under `root`.
// A word is split at a space or a hyphen on purpose; what is left must stay on one line.
function layoutProblems(root: string): { broken: string[]; tall: string[]; hyphenated: number } {
  const broken: string[] = [];
  const tall: string[] = [];
  const cells = [...document.querySelectorAll(`${root} th, ${root} td`)];
  const hyphenated = cells.filter((c) => getComputedStyle(c).hyphens === 'auto').length;
  for (const cell of cells) {
    const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      for (const m of (n.textContent ?? '').matchAll(/[^\s\-–]+/g)) {
        const range = document.createRange();
        range.setStart(n, m.index!);
        range.setEnd(n, m.index! + m[0].length);
        if (range.getClientRects().length > 1) broken.push(m[0]);
      }
    }
  }
  for (const th of document.querySelectorAll(`${root} tbody th`)) {
    const range = document.createRange();
    range.selectNodeContents(th);
    const lines = new Set([...range.getClientRects()].map((r) => Math.round(r.top))).size;
    const text = (th.textContent ?? '').trim();
    if (lines > (text.length <= 40 ? 3 : 4)) tall.push(`"${text.slice(0, 40)}" (${lines} lines)`);
  }
  return { broken, tall, hyphenated };
}

// ---- contract layer: the CSS promises, on one table of each kind -------------------------------------

test('tables — the table style is on the site', async ({ page }) => {
  await openFixture(page, 1280);
  await expect(page.locator('#table-fixture .stack'), 'no table style: copy src/styles/tables.css from the starter and import it in the layout after global.css').toHaveCSS('overflow-x', 'auto', { timeout: 2000 });
});

for (const width of PHONES) {
  test(`tables — fixture at ${width} px: rows stack, each cell has its column's label, nothing scrolls sideways`, async ({ page }) => {
    await openFixture(page, width);
    expect(await page.evaluate(markupProblems, '#table-fixture'), 'the fixture markup is wrong').toEqual([]);
    const wrap = page.locator('#table-fixture .stack');
    await expect(wrap, 'the text fixture has lost its "stack" class').toHaveCount(1, { timeout: 2000 });
    const wrapWidth = await wrap.evaluate((el) => el.clientWidth);
    const widths = await wrap.locator('tbody th, tbody td').evaluateAll((cells) => cells.map((c) => c.getBoundingClientRect().width));
    for (const w of widths) {
      expect(w, `a cell is squeezed to ${Math.round(w)} px in a ${Math.round(wrapWidth)} px table`).toBeGreaterThan(wrapWidth * 0.8);
    }
    const headers = (await wrap.locator('thead th').allTextContents()).map((h) => h.trim());
    const labels = await wrap.locator('tbody tr').evaluateAll((trs) =>
      trs.map((tr) => [...tr.querySelectorAll('td')].map((td) => getComputedStyle(td, '::before').content)));
    for (const row of labels) {
      expect(row, 'a cell shows no label, or one that is not its column header').toEqual(headers.slice(1).map((h) => `"${h}"`));
    }
    const scrolling = await page.locator('#table-fixture .table-wrap').evaluateAll((ws) => ws.filter((w) => w.scrollWidth - w.clientWidth > 1).length);
    expect(scrolling, `a fixture table scrolls inside its region at ${width} px`).toBe(0);
  });
}

test('tables — fixture on a phone: a link that stands alone in a cell is a 44px tap target', async ({ page }) => {
  await openFixture(page, 360);
  const box = await page.locator('#table-fixture a.tap').boundingBox();
  expect(box!.height, 'the link is shorter than the 44px tap target').toBeGreaterThanOrEqual(44);
  expect(box!.width, 'the link is narrower than the 44px tap target').toBeGreaterThanOrEqual(44);
});

// The region clips what is drawn outside it, and the first column starts at its edge. The ring must also be
// visible, in both themes: at least 2px wide (the starter's own ring) and 3:1 against the background it is
// drawn on (WCAG 1.4.11). Background images and gradients are not read.
for (const theme of THEMES) {
  test(`tables — fixture [${theme}]: the focus ring of a link in the first column is visible and not clipped by the region`, async ({ page }) => {
    await openFixture(page, 360, theme);
    const link = page.locator('#table-fixture a.tap');
    await link.focus();
    const ring = await link.evaluate((a) => {
      // A computed CSS colour to sRGB 0-255 plus alpha 0-1, by painting it on a canvas.
      const ctx = document.createElement('canvas').getContext('2d', { willReadFrequently: true })!;
      const rgba = (c: string) => {
        ctx.clearRect(0, 0, 1, 1);
        // A colour the canvas refuses leaves the fill as it was; a colour it reads differs from one sentinel at least.
        const read = ['#010203', '#040506'].some((sentinel) => { ctx.fillStyle = sentinel; ctx.fillStyle = c; return ctx.fillStyle !== sentinel; });
        if (!read) throw new Error(`the canvas cannot read the colour "${c}"`);
        ctx.fillRect(0, 0, 1, 1);
        const [r, g, b, al] = ctx.getImageData(0, 0, 1, 1).data;
        return { rgb: [r, g, b], a: al / 255 };
      };
      const over = (top: { rgb: number[]; a: number }, under: number[]) => top.rgb.map((v, i) => v * top.a + under[i] * (1 - top.a));
      // The background the ring is drawn on, stacked over white: from the link itself when a negative offset draws
      // the ring inside it, else from its parent.
      const s = getComputedStyle(a);
      const layers: { rgb: number[]; a: number }[] = [];
      for (let el: Element | null = parseFloat(s.outlineOffset) < 0 ? a : a.parentElement; el; el = el.parentElement) {
        const c = rgba(getComputedStyle(el).backgroundColor);
        if (c.a > 0) layers.push(c);
        if (c.a === 1) break;
      }
      const bg = layers.reverse().reduce((under, top) => over(top, under), [255, 255, 255]);
      const fg = over(rgba(s.outlineColor), bg);
      const lum = (rgb: number[]) => {
        const [r, g, b] = rgb.map((v) => { const x = v / 255; return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
      };
      const [hi, lo] = [lum(fg), lum(bg)].sort((x, y) => y - x);
      return {
        style: s.outlineStyle, width: parseFloat(s.outlineWidth), contrast: (hi + 0.05) / (lo + 0.05),
        reach: parseFloat(s.outlineWidth) + parseFloat(s.outlineOffset),
      };
    });
    expect(ring.style, 'a focused link shows no outline').not.toBe('none');
    expect(ring.width, 'the focus ring is thinner than 2px').toBeGreaterThanOrEqual(2);
    expect(ring.contrast, `the focus ring is ${ring.contrast.toFixed(2)}:1 against its background, under 3:1`).toBeGreaterThanOrEqual(3);
    const box = (await link.boundingBox())!;
    const wrapBox = (await page.locator('#table-fixture .stack').boundingBox())!;
    expect(box.x - ring.reach, 'the focus ring reaches outside the region, which clips it').toBeGreaterThanOrEqual(wrapBox.x);
  });
}

for (const width of [641, 1280]) {
  test(`tables — fixture at ${width} px: a table again, the header row shows, no word is broken, row headers take few lines`, async ({ page }) => {
    await openFixture(page, width);
    const wrap = page.locator('#table-fixture .stack');
    await expect(wrap, 'the text fixture has lost its "stack" class').toHaveCount(1, { timeout: 2000 });
    const head = await wrap.locator('thead').boundingBox();
    expect(head?.height ?? 0, 'the header row is hidden or clipped').toBeGreaterThan(20);
    expect(await wrap.locator('thead').evaluate((el) => getComputedStyle(el).clipPath), 'the header row is clipped').toBe('none');
    const tops = await wrap.locator('tbody tr').first().locator('th, td').evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().top)));
    expect(new Set(tops).size, `the cells of a row are stacked (tops ${tops.join(', ')})`).toBe(1);
    const found = await page.evaluate(layoutProblems, '#table-fixture');
    expect(found.broken, 'words broken across lines').toEqual([]);
    expect(found.tall, 'row headers with too many lines').toEqual([]);
    expect(found.hyphenated, 'cells that inherit hyphens: auto (it squeezes a narrow column down to fragments)').toBe(0);
  });
}

// The browser's own view of a stacked table: the table, its rows, headers and cells are all still there.
test('tables — fixture at 360 px: the accessibility tree still holds the table, its headers and its cells', async ({ page }) => {
  await openFixture(page, 360);
  const cdp = await page.context().newCDPSession(page);
  const { nodes } = (await cdp.send('Accessibility.getFullAXTree')) as { nodes: { nodeId: string; role?: { value: string }; name?: { value: string }; childIds?: string[] }[] };
  const byId = new Map(nodes.map((n) => [n.nodeId, n]));
  const region = nodes.find((n) => n.role?.value === 'region' && n.name?.value === 'Text table fixture');
  expect(region, 'the text fixture is not exposed as a named region').toBeTruthy();
  const counts: Record<string, number> = {};
  const walk = (n: (typeof nodes)[number]) => {
    counts[n.role?.value ?? '?'] = (counts[n.role?.value ?? '?'] ?? 0) + 1;
    (n.childIds ?? []).forEach((c) => walk(byId.get(c)!));
  };
  walk(region!);
  expect({ table: counts.table, row: counts.row, columnheader: counts.columnheader, rowheader: counts.rowheader, cell: counts.cell })
    .toEqual({ table: 1, row: 3, columnheader: 3, rowheader: 2, cell: 4 });
});

for (const theme of THEMES) {
  for (const width of [360, 1280]) {
    test(`tables — fixture [${theme}] at ${width} px has no accessibility violation`, async ({ page }) => {
      await openFixture(page, width, theme);
      const results = await new AxeBuilder({ page })
        .include('#table-fixture')
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
        .analyze();
      const summary = results.violations.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length }));
      expect(JSON.stringify(summary, null, 2)).toBe('[]');
    });
  }
}

// ---- scan layer: the real tables of every page --------------------------------------------------------

const SCANNED = PAGES.filter((p) => !(p in TABLE_EXEMPT));

test('tables — every table on every page is in the shared style with the markup it needs', async ({ page }) => {
  for (const path of SCANNED) {
    await page.goto(path);
    const problems = await page.evaluate(markupProblems, 'body');
    expect(problems, `${path}: ${problems.join('; ')}. Wrap the table in <div class="table-wrap stack|figures" role="region" aria-label="…" tabindex="0">; see "Tables" in website-design-system`).toEqual([]);
  }
});

for (const width of PHONES) {
  test(`tables — at ${width} px no page and no table scrolls sideways`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 });
    for (const path of SCANNED) {
      await page.goto(path);
      expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth), `${path} scrolls sideways at ${width} px`).toBeLessThanOrEqual(0);
      const scrolling = await page.locator('.table-wrap').evaluateAll((ws) => ws.map((w, i) => ({ i, by: w.scrollWidth - w.clientWidth })).filter((w) => w.by > 1));
      expect(scrolling, `${path}: a table scrolls inside its region at ${width} px (table, px); a table of figures that no longer fits needs "stack"`).toEqual([]);
    }
  });
}

for (const width of [641, 1280]) {
  test(`tables — at ${width} px a real stacked table is a table again, no word is broken, row headers take few lines`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    for (const path of SCANNED) {
      await page.goto(path);
      const stackedBad = await page.evaluate(() => [...document.querySelectorAll('.table-wrap.stack')].flatMap((w, i) => {
        const head = w.querySelector('thead')!;
        const out: string[] = [];
        if (head.getBoundingClientRect().height <= 20 || getComputedStyle(head).clipPath !== 'none') out.push(`stacked table ${i}: the header row is hidden or clipped`);
        w.querySelectorAll('tbody tr').forEach((tr, r) => {
          const tops = new Set([...tr.querySelectorAll('th, td')].map((c) => Math.round(c.getBoundingClientRect().top)));
          if (tops.size > 1) out.push(`stacked table ${i}, row ${r}: the cells are stacked`);
        });
        return out;
      }));
      expect(stackedBad, `${path}: a stacked table is not a table again at ${width} px`).toEqual([]);
      const found = await page.evaluate(layoutProblems, '.table-wrap');
      expect(found.broken, `${path}: words broken across lines at ${width} px`).toEqual([]);
      expect(found.tall, `${path}: row headers with too many lines at ${width} px (a long header needs "long-head")`).toEqual([]);
      expect(found.hyphenated, `${path}: cells that inherit hyphens: auto at ${width} px`).toBe(0);
    }
  });
}
