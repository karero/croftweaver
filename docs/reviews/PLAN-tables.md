# Plan: a "Tables" section in website-design-system, with the CSS and a test in the starter

Status: built 2026-10-23 (PLAN gate: 2 rounds, `docs/reviews/REVIEW-plan-2026-10-23-skill-tables-c4260eb.md`; DIFF gate: `docs/reviews/REVIEW-diff-2026-10-23-skill-tables-4f49a0d.md`). Two things changed in the build: the hyphen guard reads the computed style (headless Chromium does not hyphenate), and the contract layer's fixture is a table capped at 20rem. Written at the owner's request ("Yes: write a one-page plan for a Tables section in website-design-system plus the CSS and test in the starter template, and review the plan before building"). The plan gate (Codex) runs before any file below is built.

## Why

A site built from the starter grew 13 tables on 9 pages, and each page wrote its own table CSS. Four of them scrolled sideways at 320 px, one had a first column squeezed to "An-thropic", and nothing in the toolkit said what a table should look like or checked it. The cause sits in the starter: `src/styles/global.css` sets `hyphens: auto` on `body`, which cells inherit, and the skill's mobile rules never mention tables. The fix on that site was one shared style, two kinds of table, and tests. This plan moves the lesson into the toolkit so the next site starts with it.

## What

1. **`skills/website-design-system/SKILL.md`: a "Tables" section** (about 25 lines). The rule: one style, no table CSS on a page. Two kinds: `stack` (sentences in the cells: a table above 40rem, labelled stacked rows below it) and `figures` (short numbers: stays a table, must fit in 320 px). The markup recipe: a `.table-wrap` with `role="region"`, an `aria-label` and `tabindex="0"`; `data-label` on each cell equal to its column header, written once from a list; ARIA roles on a stacked table; `class="tap"` on a link that stands alone in a cell. What the test checks. One line in "Done means".
2. **`templates/astro/src/styles/global.css`: the Tables block** (about 55 lines, the CSS that passed review on the site). It also sets `hyphens: manual` in cells.
3. **`templates/astro/tests/tables.spec.ts`: a new shipped test**, in two layers.
   - *Contract*, which runs on any site, including the starter, which has no table: the test puts a text table and a figures table into the home page's DOM and checks what the CSS promises. At 360 and 320 px the rows stack and each cell shows its column header as a label. At 641 px and above it is a table, the header row shows, no word breaks across lines, a row header takes at most four lines. A standalone link is 44 px tall and wide. Nothing scrolls sideways.
   - *Site scan*, over `PAGES`: every `<table>` is inside a `.table-wrap` that carries `stack` or `figures`, `role="region"`, an `aria-label` and `tabindex="0"`; a stacked table has its roles and a label equal to the header on every cell; at 360 and 320 px no page and no table scrolls sideways. The message names the fix.
   A page whose tables a site cannot change (a table that comes from outside) goes into a `TABLE_EXEMPT` list in the spec, each entry with its reason, and a test that every exempt path is a live `PAGES` route, the pattern of `LLMS_EXEMPT`. `PAGES` itself is never narrowed: the sitemap check and the `llms.txt` check reject a route that is live and not listed. The site's own count of stacked tables stays out: it is the site's business.
   - *Accessibility of the fixtures:* the contract layer also runs axe (already a starter dev dependency) on the injected fixtures, in light and dark, at 360 and at 1280 px, and reads the exposed table, header and cell roles from the browser's accessibility tree (a CDP `Accessibility.getFullAXTree` count at 360 px, which on the first site built from the starter gave 1 table, 9 rows, 3 column headers, 8 row headers, 16 cells). It does not test Safari with VoiceOver.
   - *The hyphen guard reads the computed style, not the layout.* Built 2026-10-23: headless Chromium 156 does not hyphenate (a paragraph with `hyphens: auto` and one with `hyphens: manual`, both 60 px wide with `overflow-wrap: normal`, laid out alike: 3 lines, `scrollWidth` 124 in both), so no layout measure can see `hyphens: auto` come back. The spec therefore asserts that no cell's computed `hyphens` is `auto`. The fixture's long word in a forced-narrow column still catches a squeezed column, which breaks the word by `overflow-wrap`. This replaces the draft's claim that the break is visible in the layout.
4. **Where it lands.** `tests/` is drift-tracked as a whole (`TEMPLATE_TRACKED` in `scripts/whats-new.sh`), so a new spec needs no list entry; `whats-new` reports it to an existing site, which copies it by hand (it is reported, not installed). `global.css` is site-owned (`src/**`), so `whats-new` will not flag the CSS: the skill section tells an existing site to copy the block, and says so plainly.

Not in this plan: a `<DataTable>` component (a page's cells hold links, code, `<time>`; a component would not fit them), any change to the first site built from the starter (it keeps its tests; adopting the shipped spec and dropping its copy is a follow-up PR), a new skill, and the release (the owner's step: `website-builder-release`).

## How it is tested

- A scratch copy of the starter (`cp -R`, `npm ci`, build): the whole starter suite stays green with the new CSS and spec, including `a11y.spec.ts` (light and dark) and `tone.spec.ts`.
- Each check of the new spec is shown to fail by a deliberate break, one at a time, restored from memory and compared by a hash of the diff: the `stack` class removed, a label changed, a role removed, `hyphens: auto` back in a cell, the tap rule's `min-width` removed, a table forced to 40rem, stacking up to 80rem, header text too faint in dark (axe).
- `make check` (template coverage, skill budgets, no private names) and `make smoke`.
- The toolkit's CI runs the starter's whole Playwright suite on a change under `templates/astro` (`.github/workflows/template-tests.yml`), so the new spec runs there too. Its contract layer is what gives that run something to check, because the starter has no table; the breaks above are proved by hand in the scratch copy and again on a CI run with a deliberate break (a throwaway branch, not merged), and the PR says so. Two breaks cannot show in the starter, which has no real table: a squeezed row-header column (the scan layer has nothing to read) and a table outside `.table-wrap`; the first site's own tests caught both.

## Risks

| Risk | Answer |
|---|---|
| The CSS changes how an existing site's tables look when someone copies it in | it is a copy the site chooses to make, and the skill says the pages' own table CSS has to go first; the starter has no table today |
| The scan fails a site with a table the owner cannot change | the message names the two classes to add; `TABLE_EXEMPT` takes the page with a reason, and `PAGES` stays whole |
| The contract layer tests a fixture, not the site's real tables | the scan layer covers the real tables; the contract layer exists so the starter, with no table, still proves the CSS, and its fixture is built so that each break shows (see the word-break fixture above) |
| Chromium-only measurements (Range rectangles for broken words and lines) | said in the spec's header; Safari and VoiceOver are not checked, as on the site |
| A third layer of upkeep: skill text, CSS and spec can drift apart | the spec reads the CSS's behaviour, not its text; the skill section names the spec file and nothing else about it |

## Steps

| # | Step | State | Evidence |
|---|---|---|---|
| 1 | This plan, reviewed (PLAN gate) | round 1 done (Codex alone: 1 BUG, 2 RISK, all fixed in draft 2); round 2 not run | `docs/reviews/REVIEW-plan-2026-10-23-skill-tables-c4260eb.md` |
| 2 | The CSS block and the spec in the starter, proven in a scratch copy | built in the scratch copy; done when the PR carries two logs: the unchanged baseline passing, and the break `hyphens: auto` in a cell failing at the computed-style assertion itself, with the browser version | — |
| 3 | The skill section | not built | — |
| 4 | DIFF review, PR, merge; release is the owner's | not started | — |

Cost of the plan's review (my estimate): one to two rounds, 0.1 to 0.25 million tokens with Codex alone, because GLM 5.3 on melious.ai has no balance and the ollama seat is at its weekly limit. No red team: nothing here touches a server, user data, logins, money, deletion or a schema.
