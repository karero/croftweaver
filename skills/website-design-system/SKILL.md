---
name: website-design-system
description: >
  The visual build standards for a new site: mobile-first responsive graphics
  (WebP/AVIF, sized-to-display, srcset, lazy-load, descriptive alt, no layout
  shift), dark mode (CSS-variable theme tokens + a no-FOUC script + WCAG AA
  contrast in BOTH themes), and the brand/theme token block that BRAND.md
  mirrors. Use when building or reviewing layout, images, theming, or BRAND.md
  (step 6 of the new-website pipeline). Contrast is enforced by a11y.spec.ts
  (light+dark). Trigger phrases: "dark mode", "theme toggle", "responsive
  images", "mobile optimization", "image optimization", "WebP", "layout shift",
  "CLS", "design system", "theme tokens", "brand colors", "BRAND.md".
---

# Website design system

Owns the **how it looks and performs visually** layer: mobile graphics, dark
mode, and the theme tokens. Outputs/maintains `BRAND.md` (template: the `new-website`
skill's `templates/brand.md`) and the token block in that skill's
`templates/astro/src/styles/global.css`. Image rules
are below (WebP/AVIF via Astro's `astro:assets`); the `images.spec.ts` test
enforces them. For generating image assets, use the `image` skill.

## Dark mode (first-class)

- **Tokens, not hard-coded colours.** All colour flows through CSS custom
  properties; light is the `:root` default, dark overrides under
  `:root[data-theme="dark"]`, plus a `@media (prefers-color-scheme: dark)` block
  for no-JS visitors. The starter ships this exact structure.
- **No-FOUC script** in `<head>` sets `data-theme` from `localStorage.theme` or
  the system preference *before first paint* (already wired in `Base.astro`).
  The toggle writes `localStorage.theme` (the starter ships none; if you add one,
  say so in the privacy page's section 3).
- **Contrast both themes:** every text/background pair passes WCAG AA (4.5:1
  body, 3:1 large/UI). A colour that passes in light often fails in dark — the
  a11y test runs the full light+dark matrix, so check both.

## Mobile & responsive graphics

- **Mobile first:** design from 360px up; tap targets ≥ 44px; no horizontal
  scroll. Verify at 360 / 768 / 1280 (preview_resize).
- **Modern formats:** WebP (or AVIF) over JPEG/PNG for photos.
- **Size to display, not source.** Never ship a 2000px image into an 80px slot;
  generate width variants and use `srcset`/`sizes` (or `<picture>`).
- **No layout shift:** set explicit `width`/`height` **attributes** so the box is
  reserved before the image loads (protects CLS / LCP). Astro's `<Image>` sets them
  automatically; `images.spec.ts` requires the attributes (a CSS-only aspect-ratio
  will not satisfy the test).
- **Lazy vs eager:** `loading="lazy"` below the fold; the LCP/hero image loads
  eager with `fetchpriority="high"` (do NOT lazy-load it).
- **Alt text on every image** (`alt=""` only if purely decorative).
- **Fonts:** self-host woff2 with `font-display: swap`; preload only the 1–2 used
  above the fold. Avoid layout shift from late font swaps.

### Text-length responsiveness (translated copy)

- **Translated text runs longer.** German (and many other languages) commonly runs
  20–35% longer than the equivalent English copy. A button, nav link, or card sized
  to fit English placeholder text will silently overflow, wrap ugly, or truncate the
  moment real translated copy replaces it.
- **Prefer flexible widths.** Use `min-width` / flex / grid `auto`/`fr` sizing for any
  element holding translated text, not a fixed `width` sized to the English string.
- **Overflow ≠ width:** flexible sizing doesn't stop a SINGLE long compound noun
  (`Datenschutzerklärung`) from bursting a narrow column — that needs
  `hyphens: auto` (correct per-language via the `lang` attribute Base.astro already
  sets) plus `overflow-wrap: break-word` as the fallback; the starter's `global.css`
  ships both on `body`. Table cells turn hyphenation off (see Tables).
- **Don't rely on `white-space: nowrap` + `text-overflow: ellipsis` alone** as the
  handling for nav links or button labels — truncating a nav link is usually not
  acceptable UX (the visitor can no longer tell where it goes). Fine for content
  where truncation is an accepted tradeoff (e.g. a table cell), not for navigation.
- **Verify with real translated labels, not English placeholders.** When a site ships
  `astro-i18n-setup`'s `LanguageSwitcher.astro` or any bilingual/multilingual nav,
  check layout at 360/768/1280 (preview_resize) using the actual shipped copy in
  every language — not just the English placeholder.

## Tables

One style for every table; a page carries no layout CSS for a table. It lives in the starter's
`src/styles/tables.css` (imported after `global.css` by `Base.astro`) and `tests/tables.spec.ts` checks
it. A site made before this section copies `tables.css` in, adds the import line to its layout, and
removes each page's own table CSS first.

Two kinds, told apart by what the cells hold:

- **`stack`** (sentences): a table above 40rem; below it each row stacks, the row header as a title and
  each cell under its column's name. Four columns of prose cannot share 320px.
- **`figures`** (short numbers, `class="num"` on a number cell): stays a table on a phone and must fit in
  320px. If it no longer fits, make it `stack`; a scroll bar is not the fix. `stack figures` together is
  the figures look with the stacked layout.

Markup, every table:

```astro
<div class="table-wrap stack" role="region" aria-label="What the table shows" tabindex="0">
  <table role="table">
    <thead role="rowgroup"><tr role="row">
      <th scope="col" role="columnheader">{cols[0]}</th><th scope="col" role="columnheader">{cols[1]}</th>
    </tr></thead>
    <tbody role="rowgroup">{rows.map((r) => (
      <tr role="row"><th scope="row" role="rowheader">{r.item}</th><td role="cell" data-label={cols[1]}>{r.text}</td></tr>
    ))}</tbody>
  </table>
</div>
```

- Write the column names once, in a list, and use it for the header and for every `data-label`: the label
  of a stacked cell must equal its column header, and the test compares the two. A `figures` table needs no
  per-cell roles and no `data-label`.
- A stacked table is no longer `display: table`. The roles are a fallback for a browser that drops the
  table when the layout changes; that they work there is not checked. In Chromium, measured once on a real
  table, the accessibility tree kept the table without them.
- `class="tap"` on a link that stands alone in a cell makes it a 44px tap target on a phone. `nowrap` keeps a
  short value (`1, 3, 6`) on one line. `long-head` (with `stack`) widens the first column when the row
  headers are sentences.
- Words are not hyphenated in cells. The body's `hyphens: auto` squeezes a narrow first column to
  fragments ("An-thropic"), so the block sets `hyphens: manual` there.
- A page whose tables come from outside and cannot carry the markup goes into `TABLE_EXEMPT` in the spec,
  with the reason. `PAGES` stays whole: the sitemap and `llms.txt` checks need every live route in it.

What `tables.spec.ts` checks: every table is in a `.table-wrap` of one kind with its region, label and
`tabindex`, `scope="col"` on every header cell and a `<th scope="row">` as the first cell of every row, with `<td>` for the rest; a stacked table has its roles and a label equal to the header on each cell; at 360 and 320px no
page and no table scrolls sideways; at 641px and above a stacked table is a table again with its header row
showing and no word broken (this catches rules such as `overflow-wrap: anywhere` that let a column squeeze a
word); no cell has `hyphens: auto`. It also tests the CSS on a fixture it adds to the
home page, with axe in both themes, so a site with no table still proves the block. Headless Chromium does
not hyphenate, so the hyphen guard reads the computed style, not the layout. Safari and VoiceOver are not
checked.

## Email obfuscation (hide addresses from crawlers)

Never put a plaintext email or `mailto:your@addr` in the HTML source — scrapers harvest it
for spam within hours. Render every address through the **`EmailLink.astro`** component
(`src/components/EmailLink.astro` in the `new-website` skill's `templates/astro/`, + its
`lib/obfuscate.ts` helper): the address is reversed + base64-encoded at build time and
reassembled in the browser, so the served HTML contains no readable address. No-JS visitors
see a still-usable "name [at] domain [dot] com" hint.

```astro
<EmailLink address="hello@example.com" subject="Project enquiry" text="Email us" />
```
Rule: **zero raw `mailto:` links and zero literal `@`-addresses in built HTML** — `website-qa`
checks this. Same idea for any phone number you don't want harvested.

## Brand tokens

Mirror `BRAND.md`'s palette into the token block and keep them in sync. Define:
brand (fixed), and per-theme heading/ink/muted/accent/link/line/bg/bg-soft/surface. The
accent and the link colour must pass AA on the background in both themes, which is why
each theme has its own. The optional `website-brand-kit` does the mirroring with a
check: its intake reads `BRAND.md`'s tables, holds every text colour to 4.5:1 on every
background in both themes, and writes the values into all three colour blocks of
`global.css` (light, dark, and the dark block for visitors without JavaScript). By hand,
change all three blocks together.

## Done means

`BRAND.md` filled and consistent with the token block; images are WebP, sized,
lazy/eager-correct, with alt; the a11y test (light+dark) is green; layout holds
at 360/768/1280 with no shift; every table is `stack` or `figures` and `tables.spec.ts` is green. Perf numbers (FCP/LCP) are verified in `website-qa`.
Layout also holds at 360/768/1280 with **real** (not placeholder) copy in every
shipped language, not just the default locale.
