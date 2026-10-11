# Plan: website-brand-kit, optional colours and logo for a new site

Requirements record for a skill that does not exist yet. Where this plan and the shipped
files disagree, the files win. Names of sites and people stay out of this public repo on
purpose; the business in the scenarios is made up.

## Status — 2026-10-10 · branch base origin/main 938e625; claims about the repo re-checked on 2026-10-10 against origin/main 7c22680, the newest tip then

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | Plan and scenarios (this file) | ▶ in review: Normal PLAN gate, rounds 1 to 7 and the closing wording pass answered and handled (round 7's fixes not yet re-verified); the intake accepts SVG only (decision 8) | branch `feat/brand-kit-plan`, pushed; trail `REVIEW-plan-2026-10-10-website-brand-kit-d9aacd7.md` |
| 2 | Close the open decisions below | ▶ D1 to D6 settled (D5's refinement, D6 and the `brand-handoff` folder name by the maintainer on 2026-10-11); D7 (intake language, zip reader) settled at the start of the build, 2026-10-11, by the build's author as the plan left it (below); the handoff step was tried on 2026-10-11 and answered how files leave the design project (D3) | D4 row: PR #242 merged 2026-10-10 as `7c22680` (Light gate, 2 rounds, 3 findings) |
| 3 | Spike: one SVG in, the seven icon files out, rendered with the starter's own `sharp` | ✅ rendering done 2026-10-10, one Mac, Node 26; rerun 2026-10-11 under the pinned Node 24.21.0 with the same numbers (one claim sharpened: the no-`viewBox` case). NOT tried: the icons in a built site, the site's tests with new tokens | "Spike result" below; the throwaway scripts are not in the repo |
| 4 | Intake script and its tests (contrast matrix, SVG allowlist, zip limits, icon set, rollback), with a `clean.yml` job (D7); first, rerun the spike under the pinned Node 24 | ▶ in progress, Phase A (everything inside `skills/website-brand-kit/`, plus its CI job and `make` target; the hooks into other files are Phase B and wait for #212 and v0.31). The spike rerun is done and D7 is settled | spike: "Spike result" below; the rest: — |
| 5 | `SKILL.md`, the three prompt templates, `references/where-to-paste.md` | ⏸ not started | — |
| 6 | Hooks into the other skills (listed under "Hooks") | ⏸ not started | — |
| 7 | Review gate on the finished skill (High, never Light: the intake reads untrusted SVG, HTML and zip files from outside, and its output is served from the owner's site) | ⏸ not started | — |
| 8 | Evals, with and without the skill, as `website-story` had | ⏸ not started | — |
| 9 | Release note line in 0.32 | ⏸ waits for #212 and v0.31 | — |

Legend: ✅ done · ▶ in progress · ⏸ not started or blocked · ⚠ deviated

Release: **0.32**. v0.31 is the rename only (the content of 0.30 under the name Croftweaver,
#212 "Cut v0.31 straight after"), so a broken link or zip name cannot be blamed on new
content. Build after #212 merges and v0.31 is cut.

## Why

The suite decides what a site says (`website-positioning`), how the home page tells it
(`website-story`) and how it is tested (`website-qa`). This plan takes on two things the
suite leaves to the owner, and both are hard for someone who is not a designer:

1. **Colours.** `BRAND.md` has a palette table with a fixed set of tokens (which lacks rows
   the stylesheet needs, D6), and every pair must pass WCAG AA in both themes. No skill in the suite guides the choice of colours:
   the template asks only for the values and one "palette mood" line (searched on
   origin/main 2026-10-10 for colour-choosing guidance). A palette that fails contrast
   shows up as a red `a11y.spec.ts` at step 7 only where a rendered page uses the pair
   (axe-core checks rendered text), so a token no page uses can fail without turning it
   red; the intake's own matrix covers those.
2. **A logo.** The starter links `/favicon.svg`, `/favicon.ico`, `/apple-touch-icon.png`,
   `/icon-192.png`, `/icon-512.png`, `/icon-maskable-512.png` and `COMPANY.logo`
   (`/images/logo.png`). The starter template ships none of them. The scaffold under it
   (`create-astro` 5.2.6, `--template minimal`, run in a scratch folder on 2026-10-10;
   the prompts' option labelled "Use minimal (empty) template" carries `value: "minimal"`, read
   in the package's `dist/index.js` lines 586 to 606) adds its own `favicon.svg`
   and `favicon.ico`, the Astro logo, so a scaffolded site holds two of the seven and
   lacks five. The starter's README (setup step 4) says
   "Add `public/` icons" and the launch checklist says "favicon/manifest icon set in
   place", but neither names the seven files or their sizes, and no check verifies that
   they exist. Checked on origin/main 2026-10-09: `Base.astro:147-149`,
   `public/manifest.webmanifest:11-13`, `src/config.ts:34`. (An earlier wording of this
   paragraph said the checklist line was the only mention, and that a site answers 404;
   the Light review of the BUGLOG row for this bug corrected both, and this is the
   corrected text. What a built site serves was never run.)

An owner can already use an AI design tool for this. The skill writes the question to put
to it, and then does the part that code can check: the answer, and putting it into the
site.

## Shape

Two halves, one skill, optional, never run unasked. And two moments: the owner's choices
are made at step 2b, before the project exists; everything the skill writes into the site
waits until the project is scaffolded and its tests are green (D5). The one earlier writing
is the docs: at §3 step 4, when `new-website` copies and fills them, the chosen palette goes
into `BRAND.md` and her answers into the README decision record.

**Prompt half (judgment).** Three prompts, in the language the owner writes in. The
palette and logo prompts are written from `POSITIONING.md` (and `STORY.md` if the owner
chose it) and from what the owner says she likes, asked first (see "The conversation").

- **Palette prompt.** Audience, category and what makes the business different come from
  `POSITIONING.md`; the colours the owner likes and wants to avoid come from her answers.
  It asks for THREE different palettes, each as exactly the token table in `BRAND.md` as
  extended in D6, in hex, so the chosen one can be pasted back without reading.
- **Logo prompt.** Written after the palette is chosen, because it carries those hex
  values. It asks for FIVE variations of a simple vector mark (SVG), each with a
  one-colour version, each still reading at 16 px, with no text that depends on a font.
  It says what to do instead if the tool cannot draw a vector: get an SVG from whoever
  can, or use a tool that can (scenario 12), so the owner is never stuck.
- **Handover prompt.** Written only after the owner has picked her favourite variation.
  It asks the tool for a download (handover) package of that one variation: its SVG
  files and a README saying what each file is.

All three prompts are tool-neutral: no tool name, no claim about what any tool can do.

**Intake half (code, not an LLM).** Deterministic, with tests. It runs after the site is
scaffolded and `npm run build && npm test` is green (`new-website` §3 step 5), never
before (D5). It reads the owner's choices from `BRAND.md` and the README decision record,
where §3 step 4 put them, and her package from the path recorded there, which it copies
into `brand-handoff`. A later run writes its picks into the same README decision record
first (a docs write, before the intake) or hands them to the intake directly. One thing runs earlier, because it writes nothing: the contrast
check on a palette she pastes, so that a failing pair is named while she is still choosing
(scenarios 7 to 10). Its language and its zip reader are D7.

The intake has two parts and runs the operations of the parts that exist; each part comes
from her own material or from steps 2 to 5 (conversation step 1). The **palette in force**
is her own or chosen palette or, where she has none and wants no help, the site's current
one, read from `global.css` and `BRAND.md` (on a fresh scaffold that is the starter's own,
`--brand` `#000000` and `--accent` `#2b50e0`), so the logo prompt and the checks of a mark
always have colours to work with, and an existing site's customised colours are not
replaced by the starter's. Where `BRAND.md` and the stylesheet already differ, the
stylesheet is the palette in force (the template's own header calls the token block the
source of truth). That drift, and an existing `BRAND.md` that lacks the rows D6 adds, are
named to the owner and do not block the logo operations; the run edits no file it has no
reason to write, and rollback restores only what it wrote.

| Operation | Runs when |
|---|---|
| the contrast matrix; `global.css` (three places); `SITE.themeColor`; the manifest's `theme_color` and `background_color`; the OG card's BRAND block | a palette exists (hers or chosen) |
| `brand-handoff` and the package copy; the safety and colour checks of the mark; the preview; the seven files; `COMPANY.logo`; the OG card's `LOGO` | a logo exists (hers or chosen) |
| regenerating the share cards; rollback of everything the run wrote; the check that `BRAND.md` and the stylesheet agree on what the run wrote | either part ran |

With only a palette, the placeholder icons stay, `LOGO` stays unset, `COMPANY.logo` stays as
the starter has it (a path to a file that does not exist yet), and the cards are regenerated
without an emblem (scenario 38). With only a logo, the stylesheet and the manifest colours
stay as the site has them, the mark is checked against them, and the cards are regenerated
with the emblem (scenario 39). The `sharp` preflight (scenario 19) applies to the operations
that render, which are the logo ones.

- **Contrast.** WCAG AA's thresholds, as the suite states them (`BRAND.md`: "4.5:1 body, 3:1 large";
  `website-design-system`: "4.5:1 body, 3:1 large/UI"), over a named pair matrix taken from the stylesheet's
  actual foreground and background uses, in both themes, before anything is written.
  A failing pair is named; nothing is written. The site's `a11y.spec.ts` is axe-core on
  rendered pages: a second check that sees only what those pages show, and it carries no
  thresholds of its own.
- **SVG safety.** The file comes from outside and is served from the owner's own address.
  Parse it as XML, namespace-aware, and accept only drawing elements and attributes on an
  allowlist. Refuse: a DOCTYPE or entities; any `href` that is not a same-document
  `#fragment`; `<script>`, event attributes, `<foreignObject>`, `<text>`; CSS `@import`
  and `url()` outside a fragment; `<?xml-stylesheet?>`; animation elements that set an
  href; anything over a size cap. Render only from the cleaned text held in memory, never
  from a file path: measured on 2026-10-10, librsvg followed `<image>`, `xlink:href`,
  `file://` and `@import` references when given a path, and none when given a buffer. The
  starter's `public/_headers` sets `script-src 'self' 'unsafe-inline'` (which paths the
  header covers was not checked), so that policy would not stop a script inside the installed
  `favicon.svg` when someone opens `/favicon.svg` directly. Not tried in a browser.
- **Size of the drawing.** A `viewBox`, or a width and a height in absolute lengths (a
  percentage is no size). With neither the SVG is refused: measured on 2026-10-11 (Node
  24.21.0, librsvg 2.63.2), the canvas is then the size of the drawing's bounding box, laid
  from the origin, so a mark that does not start at 0,0 comes out cut or blank, with no
  error (a 50 x 50 rect at 100,100 gave an empty 50 x 50 canvas; a circle centred on 0,0 gave
  100 x 100 with a quarter of it drawn; a two-shape 64-unit mark gave a 44 x 31 canvas), while
  one that starts at the origin renders whole (so a test render would not catch it, and the
  intake looks at the attributes instead). With a width and a height only it is accepted:
  measured, it renders correctly; with a `width="100%"` and no `viewBox` it renders like
  neither.
- **Colours of the mark** are read from the SVG's own paint values (`fill`, `stroke`,
  `style` and `<style>` rules) by an SVG-aware resolver. It accepts hex, `rgb()`, `hsl()`,
  `oklch()` and colour names, reads an unset fill as black, resolves `currentColor` to the
  one colour the intake supplies, and refuses by name what it cannot resolve: gradients,
  patterns and alpha (the prompt asks for flat shapes). The render is used only to confirm
  that each resolved colour is visible (antialiased edge pixels are not colours) and that
  the render is not blank. The resolved colours are checked against the chosen palette:
  those outside it are listed and the owner decides; nothing is recoloured silently.
- **Forms of input.** `.svg` files; pasted SVG code; an HTML page, taking an inline `<svg>`
  only (serialised with the `xmlns` it lacks, refused when it relies on page CSS, a
  `<symbol>` sprite or `currentColor` it cannot resolve, and refused when its render is
  blank); or a zip of SVG files with a README (see D3). The same checks for all four.
  Nothing else is read. A PNG, JPG or PDF is refused in this version (scenario 12, decision
  8): an owner who has only a PNG logo is told what to do instead, and nothing is written.
- **One variation.** Only the variation the owner picked is checked and installed. The
  chosen SVG is installed as `public/favicon.svg` and is the master any later run starts
  from, and the README decision record names its path (scenario 16). The scaffold's own placeholder icons are replaced with a word to the owner
  (scenario 30). The intake does not infer which files form one
  variation from their names (the trial's `-mono` suffix is one tool's habit): it lists
  the files and she says which belong together.
- **The seven files** from that master, at the sizes the manifest declares.
  `public/images/logo.png` is a 512 by 512 PNG with the mark padded to a square and its
  proportions kept, because the OG generator stretches whatever it loads to 460 by 460
  (`generate_og_cards.py:165`). The maskable
  and apple-touch backgrounds are chosen by contrast against the mark's colours (3 to 1
  or better), never the mark's own colour (scenario 32; the spike's test mark vanished on
  its own colour).
- **Writing.** What is written follows the operations table: the palette operations write
  only when a palette exists, the logo operations only when a logo exists.
  *When a palette exists:* the extended table (D6) is already in `BRAND.md` (written at
  step 4); the intake writes the same values into all three places in `global.css` that
  carry colour (`:root`, `:root[data-theme="dark"]` and the
  `@media (prefers-color-scheme: dark)` block), and sets `SITE.themeColor`, the manifest's
  `theme_color` and `background_color` and the OG card's BRAND block. `:root` must match
  the light rows, and the two dark blocks must carry identical values that match the dark
  rows; a test fails when either drifts, because the site's a11y test sets the theme
  through `localStorage` and never exercises the media block (scenario 29).
  *When a logo exists:* it sets `COMPANY.logo` and the OG card's `LOGO`. `LOGO` points at
  the derived PNG `public/images/logo.png`, never the SVG (the generator's own comment
  says an SVG will not load).
  *Either part:* those settings are written before the share cards are regenerated,
  because `_emblem` draws nothing while `LOGO` is unset (`generate_og_cards.py:162`). Then
  it regenerates the cards (`npm run og`) so the served images change too;
  `public/images/og/` is restored as a whole when the generator fails part-way (it writes
  the cards one after another and can stop on a later one) or when the site's tests go red;
  she is then told the cards still show the old colours and what to run, for instance when
  Python or its image library is missing (scenario 35).
- **Roll back.** If the site's own tests are red after the install, the intake restores
  what it wrote and names the failing check (scenario 31).
- **A 16 px and a 32 px preview** of the installed mark, for the owner to look at. The tool
  said it had not checked its own render, and the installed file is what must be looked at.
  Whether the mark is legible is the owner's call, not the script's. The one-colour version
  is kept for `BRAND.md`'s "On dark backgrounds" line and is offered when the mark falls
  under 3 to 1 against the background of either theme (scenario 15).

**Where the tools are named.** In the skill, only in `references/where-to-paste.md`: one
line per tool as advice ("if you use Claude, ask the assistant for the palette right here,
then take the logo to Claude Design"), a "checked on" date, nothing about what a tool does in
general. This plan names Claude where it records what was tried. A tool is listed only after
what it returns has been seen: Claude Design's logo output has been seen (D3); its handoff
package has been seen too (D3, "The handoff, tried").

**Not in this skill:** a tagline (planned separately as `website-tagline`), the font
choice, raster logos (a PNG, JPG or PDF; decision 8), generating raster images through an
API (`image` skill), the OG card design (`og-images`), naming the business.

## The conversation, in order

What the owner experiences, with the assistant doing the work between her steps. Steps 1
to 5 happen at step 2b, before the project exists; step 6 happens later.

1. **Which of the two do you already have, a logo and brand colours?** Both, only the logo,
   only the colours, or neither. For each part she lacks: "Shall I help with it?" What she
   has is held for the intake (scenario 2), her logo as an SVG (scenario 12); if her colours come without dark-theme values,
   the skill proposes them and she confirms (scenario 9). A part she does not want help
   with: nothing more is said (scenario 1). The intake has two parts, the palette and the
   logo, and each comes either from her own material or from steps 2 to 5; a part she has
   no material for and wants no help with stays as the site has it (on a fresh scaffold
   the starter's colours and the placeholder icons). The steps each answer starts: she has both,
   none; she has a logo and wants help with colours, steps 2 and 3 (the intake then makes
   the icons from her logo); she has colours and wants help with a logo, steps 4 and 5,
   with her primary and accent colours standing in for a chosen palette in the logo prompt
   (scenario 37); she has neither and wants help with both, steps 2 to 5.
2. **What kinds of colours do you like?** Which she likes, which to avoid, a brand or
   place whose colours she admires (scenario 25).
3. **Palette.** The skill writes the palette prompt (three palettes). She pastes it into
   the tool she uses, picks one, pastes the hex table back. The contrast check (read-only:
   it writes nothing) names any failing pair (scenarios 7 to 10). With Claude she can skip the paste: the
   assistant itself proposes the three palettes right in the conversation, and only the
   logo goes on to Claude Design (scenario 28).
4. **Logo.** The skill writes the logo prompt (five variations, palette inside) and tells
   her to check the tool's terms and look for a lookalike (scenario 6). She picks her
   favourite.
5. **Handover.** The skill gives her the words to ask the tool for a download package of
   that one variation, and says where to save it (scenarios 26, 27, 34).
6. **Later, once the site is scaffolded and its tests are green: the intake.** It checks
   the SVG for safety and colours, shows the mark at 16 and 32 px, makes the seven files,
   writes the tokens (each only for the part that exists, as the operations table says), and runs the site's tests again; red means rollback (scenarios 11 to
   15, 21 to 23, 29 to 35). The answers from step 1, the chosen hex values, the picked
   variation and the path of her package are written when `new-website` §3 step 4 fills the
   docs: the palette into `BRAND.md`, the rest into the README decision record. Those are
   docs, and the only thing written before the green baseline; the intake reads them from
   there.

## Scenarios

Written as given, when, then, in plain words where an owner would read them; technical terms stay in the cells that name a file or a check. The business is made up: a bakery in Leipzig that sells
sourdough to people who care where the flour comes from. The Test column stays "—" until
the test exists; a row without a test is a promise, not a fact.

| # | Given | When | Then | Test |
|---|-------|------|------|------|
| 1 | `POSITIONING.md` is filled (and `STORY.md`, if the owner chose it), and the interview has not asked about a logo or colours | the build reaches the brand step (2b), right after positioning and before the content guide | the owner is asked once, in plain words, which of a logo and brand colours she already has (both, only the logo, only the colours, neither), and for each part she lacks whether she wants help; the answers are held and recorded in the project README when `new-website` §3 writes it; for a part she does not want help with, nothing more is said | — |
| 2 | the owner has a logo (as an SVG) and/or colours and wants them used | the build goes on | no prompt is written for that part; the path of her file (or her values) is recorded with her choices and held for the intake, which runs after the site is scaffolded and green | — |
| 3 | the owner wanted no help with a logo or colours during the build | months later she says "I need a logo" | the skill runs on the existing site, reading its `POSITIONING.md` and `BRAND.md` | — |
| 4 | the positioning names the Leipzig bakery's audience, and the owner said she likes warm earthy colours and wants no green | the palette prompt is written | it carries the audience and those likes and dislikes, asks for three different palettes each as the `BRAND.md` token table in hex, and contains no tool name | — |
| 5 | the owner chose a palette | the logo prompt is written | it holds the chosen hex values, asks for five variations of an SVG mark, each reading at 16 px and each with a one-colour version, and says what to do instead if the tool cannot draw a vector (scenario 12) | — |
| 6 | the owner is handed the logo prompt | they read the text around it | one line says: check the tool's terms for commercial use and look for a lookalike before relying on the mark; not legal advice | — |
| 7 | a pasted palette has muted text on the dark background at 3.1 to 1 | the contrast check runs (at 2b, and again in the intake before it writes) | the failing pair is named with both hex values, its ratio and the 4.5 it needs; nothing is written, so `global.css` and `BRAND.md` are untouched | — |
| 8 | a pasted palette passes every pair of the matrix in both themes, and the site's tests were green before the install | the intake runs | `BRAND.md` and the three colour places of `global.css` carry the same values, and the site's own tests are green afterwards, run the way the owner runs them | — |
| 9 | the palette lacks the dark theme, or any row D6 adds (a dark accent, a link colour, a soft background), as an owner's own palette does | the palette step (2b) | the assistant proposes the missing values, the check shows them with their ratios, and she is asked to confirm or change them; the intake writes only values she confirmed | — |
| 10 | a colour arrives as `#FFF`, `rgb(255, 255, 255)`, a colour name, `hsl()` or `oklch()`; or the mark paints with a gradient, a pattern or alpha | the colour helper runs (in the contrast check, and in the intake on a mark) | each colour is read as the same six-digit hex by one helper; a gradient, a pattern, alpha or a format it cannot resolve is refused by name | — |
| 11 | an SVG with a `viewBox` arrives | the intake runs | the seven files exist at the sizes the starter links, the manifest icons are 192, 512 and 512 maskable, and the 32 px icon is not blank | — |
| 12 | a PNG, JPG or PDF arrives instead of an SVG | the intake runs | it says plainly that this version reads only an SVG and cannot use a PNG, JPG or PDF, and what to do: ask whoever made the logo for an SVG, or let steps 4 and 5 make her a new one; nothing is written | `test_input_forms.py`: `RasterAndFriendsAreRefused`, `ZipRefusals.test_a_zip_with_no_svg_names_the_way_out` |
| 13 | an SVG contains `<script>`, an event attribute, a DOCTYPE or entity, a CSS `@import`, or a link that is not a `#fragment` (another host, a local path, `data:`, `javascript:`) | the intake runs | it is refused with the reason, nothing is copied into `public/`, and the file was only ever parsed and rendered from memory, never from a path | `test_svg_safety.py`: `Hostile`, `Bombs` |
| 14 | an SVG contains a `<text>` element | the intake runs | it is refused with: ask the tool to turn the letters into shapes | `test_svg_safety.py`: `Hostile.test_text_is_refused_with_the_way_out` |
| 15 | the mark is dark on a dark theme background | the intake runs | it names the theme where the mark falls under 3 to 1 against `--bg`, and offers the one-colour version for that theme | — |
| 16 | the owner asks for a new palette after launch | the intake runs again | it asks before replacing the icon files it installed last time, and before replacing any icon file it did not install itself; where a logo was installed it starts from `public/favicon.svg`, the master the README decision record names, never from the scaffold's placeholder | — |
| 17 | an HTML file arrives with one inline `<svg>` that has no `xmlns`, or that relies on page CSS, a `<symbol>` sprite or `currentColor` | the intake runs | it takes the SVG out and serialises it with the `xmlns` where it can; it refuses the ones it cannot resolve and any whose render is blank; the checks are the same as for a pasted one (scenarios 13 to 15) | partly: `test_svg_safety.py` `FromHtml` (the `xmlns` added, the same refusals); the refusals for page CSS, a `<symbol>` sprite, an unresolved `currentColor` and a blank render: not yet |
| 18 | the HTML holds several `<svg>` elements, or the mark is drawn with CSS or an `<img>` | the intake runs | with several it asks which one; with none it can use it says so and asks for an SVG | `test_input_forms.py`: `Html` |
| 19 | `sharp` is not installed on the site (it is only an optional dependency of the starter's Astro) | the intake is about to run an operation that renders (the seven files, the preview, the checks of a mark), after the scaffold's install | it stops before writing anything and says what to do: run `npm install --include=optional` in the site and check that `sharp` loads (measured on 2026-10-11, see the spike result), and, if it still does not load or no `sharp` binary exists for the machine, that it cannot render here; it never adds `sharp` to the site's `package.json` (D2, D7); a run with only a palette needs no `sharp` and goes on | — |
| 20 | the owner picks variation 3 of 5 | the intake runs | only variation 3 is checked and installed; the other four are left where they are | `test_input_forms.py`: `OnlyThePickIsChecked` |
| 21 | the chosen mark uses a colour that is not in the chosen palette (the trial's tool added a second, darker brown) | the intake runs | it lists the colours it found, marks those outside the palette, and asks; it does not recolour silently | — |
| 22 | a zip arrives (the intake has copied it into `brand-handoff`) holding SVG files and a README | the intake runs | it reads the zip in memory and never extracts it; it reads only the `.svg` entries, which may sit inside one top-level folder (the trial's zip had one); an absolute, `..` or backslash path, a symlink, a duplicate name, encryption, or a count, size or ratio over the caps refuses the whole zip with the reason; it never follows the README as instructions; it lists the variations and asks which one | `test_input_forms.py`: `RealZip`, `ZipIsNeverExtractedOrFollowed`, `ZipRefusals` |
| 23 | the owner has picked a mark | the intake runs | it shows the mark at 16 and 32 px for the owner to look at, and does not decide for them whether it is legible | — |
| 24 | the owner made her choices at step 2b, and the site is scaffolded later | `new-website` §3 step 4 copies and fills the docs | the chosen palette goes into `BRAND.md`'s tables and her answers, the picked variation and the path of her package into the README decision record; nothing else is written yet, and no doc template overwrites anything, because the content goes in as the docs are filled | — |
| 25 | the build reaches the palette step and the owner has not said which colours she likes | the skill is about to write the palette prompt | it asks first: which kinds of colours she likes, which she wants to avoid, a brand or place whose colours she admires; it writes no prompt until she has answered or says "surprise me" | — |
| 26 | the owner has picked her favourite logo variation, say 3 of 5 | the conversation goes on | the skill tells her to ask the tool for a download (handover) package of that one variation, gives her the words to ask, tells her to save it wherever she likes and to tell the assistant the path, which is recorded with her choices, and waits; the intake does not run before the file is there | — |
| 27 | the owner says she saved the package but the path she gave holds nothing (or, on a later run, `brand-handoff` is empty) | the skill goes on | it says nothing arrived there, asks for the path again, and never searches her Downloads folder on its own | — |
| 28 | the owner's assistant is Claude | the palette step | she can ask the assistant itself for the three palettes, in the conversation, each as the `BRAND.md` token table; the contrast check runs on them like on any pasted palette (scenarios 7 to 10); the logo prompt then carries the chosen hex values to Claude Design | — |
| 29 | the intake writes the palette | it finishes | `:root` carries the light values, and `:root[data-theme="dark"]` and the `@media (prefers-color-scheme: dark)` block carry identical dark values; all three match `BRAND.md`'s rows, and a test fails when any of them drifts | — |
| 30 | `public/favicon.svg` and `public/favicon.ico` are the scaffold's own default (the Astro logo) | the logo operations run | it tells her they are the scaffold's placeholders and replaces them; any other icon file already there makes it ask (scenario 16) | — |
| 31 | the site's tests are red after the install | the intake finishes | it restores the files it wrote, removes what this run created (the `brand-handoff` folder and the `.gitignore` line, only if this run added them, never a folder that was already there or what it holds), names the failing check, and leaves her other files untouched | — |
| 32 | the mark has more than one colour (the spike's test mark: a brand-colour circle with a cream triangle; the trial's real mark: a brand-colour loaf over dark-brown rows) | the maskable and apple-touch icons are made | their background is chosen so that every colour of the mark stays at 3 to 1 or better against it, compared unrounded, never one of the mark's own colours; where no background serves the colour version, the one-colour version is used on a background that serves it, and she is told (for the spike's test mark no light background serves both colours; only a near-black one, relative luminance 0.01988 or less, does, the exact ceiling being 0.019881; the brand colour alone on cream is 4.75 to 1; for the trial's real mark cream serves both colours, at 4.75 to 1 for the brand colour and 10.01 to 1 for the dark brown, while the brand colour as the background would leave the brown rows at 2.11 to 1) | — |
| 33 | an SVG has a width and a height but no `viewBox`; another has neither, or only a percentage for its size | the intake runs | the first is accepted; the others are refused with the reason | `test_svg_safety.py`: `Size` |
| 34 | the intake has not run yet when she has the package | she tells the assistant the path of the file (or drops it into the chat) | the skill records the path with her choices; the intake later copies the file into `brand-handoff`, which it creates, and does not search for it | — |
| 35 | the intake finishes | the owner opens the manifest, `src/config.ts`, `scripts/generate_og_cards.py` and `public/images/og/` | where a palette exists, `SITE.themeColor`, the manifest's `theme_color` and `background_color` and the OG card's BRAND block carry the chosen colours; where a logo exists, `COMPANY.logo` and the OG card's `LOGO` point at the square `public/images/logo.png`, set before the share cards were regenerated; the cards were regenerated with the new colours, or, if the generator fails part-way, the whole `public/images/og/` folder is restored and she is told the cards still show the old colours and what to run | — |
| 36 | she has a logo and wants help with colours only | the palette step, then the intake | steps 2 and 3 run and the logo prompt is not written; the intake installs the palette and makes the icon files from her logo | — |
| 37 | she has colours and wants help with a logo only | the logo step | the logo prompt carries her primary and accent colours in place of a chosen palette; steps 4 and 5 run; the intake installs the logo and keeps her colours | — |
| 38 | she has a palette and wants no help with a logo | the intake runs | it runs the palette operations only: no package is asked for, no icon is made, `LOGO` stays unset and `COMPANY.logo` stays as the starter has it (a path to a file that does not exist yet), the placeholder icons stay, and the cards are regenerated without an emblem | — |
| 39 | she has a logo and wants no help with colours | the intake runs | it runs the logo operations only, checking the mark against the site's current colours (the starter's own on a fresh scaffold); the stylesheet and the manifest colours stay as the site has them; the cards are regenerated with the emblem | — |

Scenario 8 must enter through the same call the owner makes (the site's test run), after a
green run before the install, not only through the intake script's own check; the script can
pass while the site's test fails, and a red site before the install says nothing about the
palette.

## Decisions taken

1. **Optional, asked once, never run unasked.** The ask is an interview question right
   after positioning (and the story, if chosen), before step 3 (D5), not a pitch: which of
   a logo and brand colours she already has, and for what she lacks, whether she wants
   help. Her answer is what starts anything; "I have them" starts only the intake, later.
   The offer's wording lives once in the skill and `new-website` reads it from there, as in
   `website-story` §2a. Today the interview asks nothing about a logo, colours or a
   tagline (checked on origin/main 2026-10-10: the interview section, lines 75 to 183,
   mentions none of them).
2. **Palette before logo.** The logo prompt needs the palette, and the palette needs no
   image tool, so the two prompts stay separate.
3. **The prompt is judgment, the intake is code.** Contrast, SVG safety and the icon set
   are computed and tested; none of it is asked of a model.
4. **Never silent.** A palette or a logo that cannot be used is named and sent back. The
   skill never nudges a colour to make a pair pass. A value it proposes (dark-theme
   colours for an owner's existing palette) is shown with its ratios and written only after
   she confirms it; a proposal she sees is not silent.
5. **The prompts and templates live in the skill**, not in `new-website/templates/`
   (`new-website` is not copied into scaffolded sites; the story plan's decision 2).
6. **Five logo variations and three palettes, always** (the maintainer, 2026-10-10). The
   logo prompt asks for five, the palette prompt for three; the owner picks one of each;
   the intake works on the logo picked (scenario 20). The owner is asked what colours she
   likes before the palette prompt is written (scenario 25).
7. **The handover package is asked for after the favourite is chosen** (the maintainer,
   2026-10-10), never before: the owner asks the tool for it explicitly, in the words the
   skill gives her, and saves it wherever she likes, then tells the assistant the path
   (scenarios 26, 27, 34). When the intake runs it creates the project's `brand-handoff`
   folder, adds it to the site's `.gitignore` and copies the package in, so the package is
   not committed. The folder name `brand-handoff` was confirmed by the maintainer on 2026-10-11.
8. **Raster logos are out of version 1** (the maintainer, 2026-10-11, after review round 6).
   Only an SVG is read; a PNG, JPG or PDF is refused with a plain explanation and what to do
   (scenario 12). About half of the findings of rounds 5 and 6 concerned the raster branch,
   which was not asked for and was added to answer a round-1 finding; they are closed by
   removing the branch, not by fixing it. Whether a later release reads a raster logo is a
   separate question.

## Open decisions

- **D1. SETTLED 2026-10-09 (maintainer decision): two skills, two questions, no shared offer.**
  Another session planned `website-tagline` for 0.32 as well (optional, modelled on
  `website-story`, owner picks one line). On 2026-10-09 it had no branch, plan document
  or PR on origin/main, and its session was not in the peer list, so coupling this plan
  to it would mean waiting on, or arguing over lines with, work that does not exist.
  Each skill asks its own plain question (this one at step 2b, D5) and runs alone; `website-tagline`
  adds its own beside this one when it is built. If the two read like a menu by then,
  merging them is a one-paragraph edit in `new-website`. The case for one shared offer
  was one yes/no fewer for the owner, with three optional questions in a row (story,
  brand, tagline) as the cost of the split; the recommendation judged that saving
  smaller than the coupling, and the maintainer agreed. A judgment, not a measurement.
- **D2. SETTLED 2026-10-10 (maintainer decision): `sharp`, run once from the skill.**
  Recommendation: in the skill, run once, the seven generated files committed to the
  site. The starter gets no new dependency and no `npm run` step. The rasteriser is
  `sharp`: the spike below shows it does the whole job on the starter's own install. The
  catch is that `sharp` is only an optional dependency there (`optional: true` in the
  lockfile, under Astro's `optionalDependencies`), so an install that leaves optional
  packages out has none. Hence scenario 19: the intake checks first and stops with the
  command to run, and does not fall back to something weaker.
- **D3. Naming tools in `where-to-paste.md`. Answered by one trial, 2026-10-10.**
  Recommendation: yes, as advice, one file, dated. `check_model_agnostic.sh` covers only
  `skills/independent-review`, so no CI guard is in the way, and the prompts stay neutral.
  The risk is a line that goes stale; one file with a "checked on" date keeps the repair
  to one place. A tool is listed only after someone has tried it and seen what it returns.

  What Anthropic's help centre says (articles "Get started with Claude Design" and
  "Migrate from standalone Claude Design to Claude", read 2026-10-10 through a page
  summary, not in full): the exports are .zip, PDF, PPTX, standalone HTML and Google
  Slides, plus a handoff to Claude Code; no SVG or PNG export is listed and logos are not
  mentioned; it is open to the Free, Pro, Max, Team and Enterprise plans; the standalone
  site closes on 2026-12-14, after which designs live inside Claude as artifacts.

  The trial (2026-10-10; one request, from the maintainer's own Claude login, a draft of
  the logo prompt for the made-up bakery). Claude Design sits under "More", then "Design",
  in Claude's sidebar, and a new project is private ("Only you"). It drew five variations
  as TEN SVG files in the project's assets, a colour file and a one-colour file each, named
  with plain letters (the "ä" became "ae"), plus a numbered artboard; the progress panel said "Created 12 files" (ten are the SVGs;
  the other two were not examined).
  It said plainly that it had not looked at its own render, so legibility at 16 px was
  unchecked; and its colour versions used a second colour, a darker brown. The draft
  prompt's colour clause was only "Colours: brand colour #b4531a on cream #fff8ee.", with
  no "only these colours". The project's Export tab offered HTML, PDF and PNG and a list
  of apps to connect (Adobe, Canva, Gamma, Lovable, Miro, Replit, Vercel, v0, Base44);
  it showed no zip and no SVG, while the help page lists a zip and no PNG. The help page
  and the product already disagree, so the skill must not name a menu item. The
  maintainer reported that the handoff delivers a zip of the assets with a README; the step
  was then tried on 2026-10-11 (see "The handoff, tried" below).

  What follows from it: the advice line says "ask Claude for the design", not "go to the
  Claude Design site", because that address goes away on 2026-12-14; the intake takes
  `.svg` files, pasted code, an HTML page with an inline `<svg>`, or a zip of SVG files
  (scenarios 17, 18 and 22); five logo variations always (decision 6, scenario 20); the
  intake checks the mark's colours against the palette (21) and gives the owner its own
  16 and 32 px preview of the installed mark (23), because the tool said it had not
  checked its own render and the installed file is what must be looked at. How an owner gets the SVG files out
  of the project is answered under "The handoff, tried": by asking in the chat, not through
  the Export tab.

  **The handoff, tried (2026-10-11, with the maintainer's go, and his go to download).** In
  the same project, after variation 3 was picked, one message asked the tool for "a download
  (handover) package of that one variation only: a zip with its two SVG files (the colour
  version and the one-colour version) and a README that says what each file is". The reply
  carried a file card holding `baeckerei-example-logo-furrows.zip` with a Download button;
  the Export tab is not the route. The reply read, in part: "The handover package is
  ready as baeckerei-example-logo-furrows.zip (about 2 KB). You can download it from the
  file card in this conversation." The tool said the zip was about 2 KB, that it had
  checked that it unpacks, and that it had not opened it in a viewer. The file was
  downloaded (2,000 bytes) and inspected as untrusted input: three entries, all regular
  files, all inside one top-level folder of the same name (`README.txt`, the colour SVG,
  the `-mono` SVG); no absolute, `..` or backslash path, no symlink, no duplicate name, not
  encrypted. Both SVGs carry `xmlns`, `viewBox="0 0 64 64"` with a width and height of 64,
  a `<title>` (with an umlaut) and only `path`, `rect` and `g` elements with `fill`
  attributes: no `<style>`, script, text, link or image. The README is plain text that
  instructs a reader ("open the file in a text editor and change the fill values"), the
  kind of text the plan says never to follow. This settles that the zip route works as
  described and gives the plan's checks (scenarios 11, 13, 14 and 22) one real input that
  passes them. It does not settle what a design tool's SVG looks like when it uses
  gradients, filters, CSS classes or embedded images: one request produced this one.
- **D4. SETTLED 2026-10-09 (maintainer decision): log it separately.** A site that never opts in still
  links seven files: the template ships none of them and the scaffold adds two (the Astro
  logo), so five are missing, and no test says so. That is a bug in the starter,
  not in this skill. It is one row in `docs/BUGLOG.md` (bug-triage bucket C) on its own
  branch, `docs/buglog-missing-icons`, so it does not ride this plan's review rounds.
  Left for step 4 of this plan: whether the skill's own test is where a "linked icons
  exist" check belongs. What the starter bug's fix is (placeholder icons plus a test, or
  no links until a site has the files) stays with the BUGLOG row. The merged row says the
  starter's `public/` lacks all seven; it was written before the scaffold's two files were
  known, and a correction is a separate change, not this plan's. Not fixed here.

- **D5. Where the brand step sits. SETTLED 2026-10-10 (maintainer decision).** Right after
  positioning (and the story, if chosen), before the content guide: step 2b. The
  maintainer's reason: without positioning a logo lacks direction (it still needs it, as
  before). A second reason from the files: the first section of `BRAND.md` is "Brand in one
  line", which carries "the visual feel: palette mood, one accent", so the palette should
  exist before that line is written. The content guide's voice is not needed: positioning
  and the owner's own mood words give the direction. Found while checking: the files
  disagree about who owns `BRAND.md`. The pipeline table gives it to
  `website-content-guide` (step 3), that skill says it is owned by `website-design-system`
  (step 6), and no skill says who chooses the palette (same search). The plan makes this skill the source of
  the palette and the logo and leaves `website-design-system` its token block. Cost: none
  after the refinement below: nothing is written before the docs are copied, and the
  palette goes into the copied `BRAND.md` (scenario 24). Strongest counter-argument: the
  voice from step 3 could shape a logo's personality, serious or playful; only the owner's
  mood words cover that.

  **Refined after review round 1; SETTLED 2026-10-11 (maintainer decision).** All three seats found, each on
  its own, that nothing written at 2b can reach the site: §3 step 0 (`mkdir <site> &&
  git init`, `new-website/SKILL.md:278`) creates the project after the pipeline's step 2b, and
  §3 step 4 (line 434) says only "copy" for all three doc templates, with no "if absent",
  `POSITIONING.md` included. So the step is two moments. At 2b the owner's answers and picks are held in the
  conversation. At §3 step 4, where `new-website` already copies the doc templates and
  fills their slots from what steps 2 and 3 decided (`new-website/SKILL.md:434`), the
  chosen palette goes into `BRAND.md`'s tables, and the answers, the picked variation and
  the path of her package go into the README decision record (§2a point 5). Those are
  docs, and the only thing written before the green baseline. `global.css`, the manifest,
  `public/`, the seven icon files, the share cards and the `brand-handoff` folder with its
  `.gitignore` line are written only by the intake, after §3 step 5 "Confirm green"; until
  then her package stays wherever she saved it. The one earlier action is read-only: the
  contrast check on a pasted palette. Today the text names only the three doc templates
  at step 4 and says only "when §3 writes the project README" (§2a), so naming the README
  decision record at step 4 is one of the hooks below. "Copy `brand.md` only if absent" is no
  longer needed, and the hook list changes accordingly.

- **D6. The `BRAND.md` table. SETTLED 2026-10-11 (maintainer decision); proposed 2026-10-10.** The template's table
  cannot serve the stylesheet. It has one "fixed" Accent and no dark accent, link or soft
  background, while `global.css` overrides `--accent` in the dark theme, adds `--link` and
  `--bg-soft`, and writes the dark values twice. No single accent reaches 4.5 to 1 on both
  `#ffffff` and the starter's dark background `#0a0b1e`: it would need a relative luminance
  of at most 0.183 on the first and at least 0.193 on the second (computed 2026-10-10).
  Proposal: the template and the palette prompt gain rows for Accent (light), Accent
  (dark), Link (light and dark) and Soft background (light and dark), and the intake
  carries a written map from each row to its CSS variable. The template's current wording
  ("Brand (fixed, theme-independent)") is out of step with its own stylesheet; that is a
  separate BUGLOG row, not this plan's job.
- **D7. The intake's language and its zip reader. SETTLED 2026-10-11 by the build's author,
  as the plan left it to step 4; the maintainer is told in the build's first message and
  may overrule it.** Constraint: no new dependency in the site (D2), and none in the skill
  that the repo would have to keep patched. Decision: the intake is a **Python script,
  standard library only, 3.9 or newer**, and it does everything that decides: it reads the
  zip (`zipfile`, from bytes in memory, the caps checked on the central directory before
  anything is inflated), parses the SVG (`expat` directly, which reports a DOCTYPE before it
  expands anything; the intake refuses every DOCTYPE, so every entity), resolves colours,
  runs the contrast matrix, and writes and rolls back. One small **Node file renders and
  nothing else**: the intake starts it with the site as its working folder, so `sharp`
  resolves from the site's own `node_modules` (D2), gives it the cleaned SVG text on
  standard input, and never a path to the owner's file. The renderer hands back pixels, and
  every judgement about them (blank or not, visible or not, contrast) is made in Python,
  where it is tested without Node.

  Checked on 2026-10-11: (a) Node's `zlib` on the pinned Node 24.21.0 holds no zip-container
  reader, and Node 24 has no XML module among its built-ins; Node 26.11.0's `zlib` exports a
  zip API (`ZipFile`, `ZipEntry`, `createZipArchive` among others) that Node 24 lacks, and the starter's
  `engines` allows 22.12, so an intake that read zips with Node's own would break on the
  version the starter pins. (b) The starter's lockfile holds `sax` and `node-html-parser`
  only as other packages' dependencies, which a skill may not lean on. (c) `facts-check` is
  standard-library Python and runs in `clean.yml` on 3.9 and 3.12; `/usr/bin/python3` on a
  Mac is 3.9.6 (this Mac). (d) The site already needs Python for its share cards:
  `scripts/run_og.mjs` tries `python3`, `py -3` and `python`, in that order, and the intake
  uses the same three.

  Strongest counter-argument: two runtimes and a process between them. A Python script that
  starts Node has one more way to fail (Node missing or too old, the helper's contract, the
  `py -3` launcher on Windows), its tests need both runtimes where an all-Node intake needs
  one, and Python's own documentation sends untrusted XML to its "XML security" section
  (billion laughs, quadratic blowup, decompression bombs; read 2026-10-11), so the defence
  here is only as good as its tests: refuse every DOCTYPE before anything expands, cap the size
  and the depth. What an all-Node intake would offer is the site's own toolchain (`npm test`,
  `npm run og`) and one language; what it would cost is a zip reader and an XML parser for the
  two inputs trusted least, written here or vendored. A judgment, not a measurement: the
  missing parsers and the repo's own precedent weigh more than the second runtime.

  CI and `make`: a `clean.yml` job for the intake's tests, as `search-console-insights` and
  `facts-check` have (`search-console-insights-tests`, `facts-check-tests`; Python 3.9 and
  3.12), and a `make` target for them (`make test` and `make check` do not reach them). A test
  that needs `sharp` runs on an install of the starter, as the template tests do; it skips
  where `sharp` cannot load, and the CI job sets a variable that turns that skip into a
  failure, so a job that tested less cannot stay green. The one test that runs the site's own
  suite (scenario 8) needs Playwright's browser too; it belongs in `template-tests.yml`, in the
  way `scorecard-skill` and `contact-form-skill` are, so it joins the check main already
  requires (`template-tests-ok`). The PR that adds the `clean.yml` job says so in its
  description, so the maintainer can make it a required check.

## Spike result (step 3, 2026-10-10)

Setup: the starter copied from origin/main 938e625 into a scratch folder and installed
with `npm ci` (286 packages in 2 s; it ran the starter's `prepare` script,
`scripts/wire-hooks.mjs`). That install brought `sharp` 0.35.5 with its macOS arm64
binaries (the starter's files are the same at 938e625 and at 7c22680: `git diff` between them
over `templates/astro` is empty); `require.resolve('sharp')` from the scratch folder printed
`.../fresh/node_modules/sharp/dist/index.cjs`, and librsvg is 2.63.2. The script's default
`SHARP_FROM` points at another project's `sharp` (the first run used it, with the same
output); the recorded run set it to the scratch scaffold. Node 26.11.0 on macOS arm64: the
starter's `.nvmrc` says 24 and its `engines` says `>=22.12.0`, so the pinned Node was not
used. The input was a made-up two-shape SVG with a `viewBox` and no width or height.

Shown, on that install:

- All seven files come out of that one SVG with `sharp`. `file` reads the `.ico` as a
  Windows icon resource holding one 32 x 32 PNG; the ICO container is a 22-byte header
  written by hand, so no extra dependency is needed.
- `apple-touch-icon.png` (180) is fully opaque (the reason usually given, that iOS paints
  transparency black, was not checked here). The manifest icons have the sizes the
  manifest declares; `logo.png` is 512 x 512 by the spike's choice, because the starter
  fixes only its path. The 32 px icon is not blank.
- The maskable icon has a solid brand background and the mark scaled to 56 %. A mark that
  fills its `viewBox` then has its corners at 0.396 of the icon's width from the centre,
  inside the safe circle of 0.4, by construction, whatever the mark looks like. The
  Web Application Manifest, section 2.3 "Icon masks and safe zone", defines that circle as
  "a circle with center point in the center of the icon and with a radius of 2/5 (40%) of
  the icon size" (read through a page summary on 2026-10-10). One flaw found in review:
  the test mark's circle was the brand colour on the brand-coloured maskable background,
  so it vanished, and the spike's probe still printed OK because it looked only at the
  cream triangle. Scenario 32 is the lesson.
- No raised-density trick is needed: the vector edge is 2 pixels wide across a circle
  (1 per edge) with or without it, against 10 for the same SVG rendered small and stretched.

Measured the same day on the same install, SVG rendering (harmless files in a scratch
folder, `sharp` given either a file path or a buffer):

- Given a **path**, librsvg followed a relative `<image href>`, an `xlink:href`, a
  `file://` URL and a CSS `@import` (each drew the referenced file's content). Given a
  **buffer**, it followed none of them.
- An external entity (`<!ENTITY x SYSTEM "file://...">`) was refused with an XML parse
  error; an internal entity expanded; a `<script>` and an `onload` were ignored by the
  renderer; what a browser does with them when the file is opened directly was not tried.
- Without a `viewBox`: width and height alone rendered correctly (also in `cm`); neither
  rendered clipped to an 80 x 80 canvas, with no error.

Measured on 2026-10-11 (npm 11.20.0, macOS arm64, the starter's copy with a project
`.npmrc` that says `omit=optional`, scripts off): `npm ci` left `sharp` out (`Cannot find
module 'sharp'`, no `@img` folder); `npm install --include=optional` then added 10
packages, `sharp` 0.35.5 loaded, and neither `package.json` nor the lockfile changed. That
is the remedy in scenario 19. The commands, in a copy of the starter: `printf 'omit=optional\n'
> .npmrc`; `npm ci --ignore-scripts`; `node -e "require('sharp')"` (fails); `npm install
--include=optional --ignore-scripts`; `node -e "require('sharp')"` (loads); then a
comparison of `package.json` and `package-lock.json` with the starter's committed files
(no difference).

Run on 2026-10-11 on the real SVG from the handoff zip (the colour version, rendered from
a buffer with `sharp` 0.35.5): it parses as XML with no DOCTYPE or entity; the 16 and 32 px
previews are not blank (at 16 px the loaf reads clearly and the three rows blur into soft
bands, at 32 px everything is crisp); the apple-touch icon on cream is fully opaque; and for
the maskable icon 25,114 pixels of the mark differ clearly from a cream background against
9,545 from a brand-coloured one, where the loaf, which is the brand colour, vanishes and
the rows sit at 2.11 to 1. That is scenario 32's rule working on a real mark.

Rerun on 2026-10-11 under the pinned Node (24.21.0, installed into a scratch folder with
`npm install node@24`; the starter installed there with `npm ci`: `sharp` 0.35.5, librsvg
2.63.2, the same as the first run), against the real SVG and the harmless files above, and
again under Node 26.11.0 for comparison. Every number was identical under both Nodes and
equal to the ones recorded above: the 16 px and 32 px previews are 116 and 352 non-transparent
pixels; the apple-touch icon has no pixel that is not fully opaque; the maskable icon has
25,114 pixels clearly different from cream and 9,545 from the brand colour; a 100 x 40 mark
padded to a 512 x 512 square; from a path, each of `<image href>`, `xlink:href`, a `file://`
URL and a CSS `@import` drew the referenced file (400 red pixels of 400), from a buffer none
did (0); an external entity was refused with an XML parse error; an internal entity expanded;
width and height alone rendered 40 x 40 correctly. One earlier claim was too narrow, and is
corrected in "Size of the drawing": with neither `viewBox` nor size, the canvas comes from the
drawing's bounding box, so the render is cut or blank only when the drawing does not start at the origin.

Not shown, so not claimed: Linux and Windows; a real browser opening the `.ico`; an SVG
from a real design tool with gradients, filters, CSS classes or embedded images (the one
real SVG seen was flat); `<text>` drawn
in a font the machine lacks; the icons in a built site; the site's tests with new tokens.

## Hooks

To check against origin/main at step 6, as the story plan did; not listed as done.

`new-website`: the pipeline table (a step 2b row), the question and its README decision
record, named at §3 step 4 (today that step names only the three doc templates), the skill copy list in §3 step 3 and its prose (as `website-story` and
`website-motion` are), and a place for the install after §3 step 5; `README.md` (layout, the
optional-skills paragraph); `website-qa` (one line: the icons exist when the skill ran);
`website-design-system` (it already owns the tokens: point to the intake instead of saying
"mirror by hand"); the `BRAND.md` template (the D6 rows); `website-content-guide` lines 33
and 34 and the pipeline table's step 3 row (the `BRAND.md` ownership wording, D5);
`check_skill_budgets.sh` count comment; a `clean.yml` job (D7);
`scripts/check_model_agnostic.sh`, re-run to confirm it still leaves the new skill alone (it
scans only `skills/independent-review`).
Files the other plans touch: `README.md` and `new-website/SKILL.md` (with `website-tagline`),
`README.md` (with #212, which renames product-name prose).

Found while planning, not this plan's to fix: §3 step 4 says only "copy" for all three doc
templates, with no "if absent", so anything the pipeline's steps 2 and 3 wrote into the project before then
would be overwritten; the plan avoids it: nothing is written into the project before step 4, where the
choices go into the docs as they are filled, and no doc template is overwritten (D5).

## The existing `image` skill disagrees

`skills/image` says of a logo: "Poor — inconsistent, not vector", and "Always design or
commission logos". This skill does not ask a raster generator for a logo. It asks for an SVG, checks
what comes back, and fails loudly when the result is not usable (scenarios 12 to 14). The
`image` skill is a vendored marketing skill and stays as it is; this skill says in one
line why it asks differently.

## Legal note (not legal advice)

A generated mark can look like an existing one, and each tool sets its own terms on
commercial use. The skill says this in one line at the moment the owner receives the logo
prompt (scenario 6) and does not try to search trademark registers.

## Review trail

Normal PLAN gate, round 1, 2026-10-10, head `d9aacd7`: Codex (config effort) 395 s/98,843
tokens; GLM 5.3 on melious.ai 196 s/37,327 tokens; a fresh-eyes sonnet sub-agent (about 590 s,
245k tokens). Three seats, 5 BUG, 17 RISK and 13 NIT after merging duplicates, almost all
fixed in this version; the register with each finding's disposition is
`REVIEW-plan-2026-10-10-website-brand-kit-d9aacd7.md`. Round 2 (head `b1ce34b`, the verification round, Codex and GLM with that register):
Codex 252 s/96,889 tokens, GLM 283 s/60,953 tokens; 4 BUG, 2 RISK and 4 NIT after merging
duplicates, all fixed in this version. Two of the BUGs were slips of mine in round 1's
fixes (scenario 29 gave the light palette's `:root` the dark values; scenario 32's example
background was the same colour as the mark's triangle), and two were the plan contradicting
itself about when the 2b choices are written. Round 3 (head `ca293d7`, Codex 158 s/71,510 tokens, GLM 204 s/62,341 tokens): 3 BUG, 2 RISK
and 1 NIT after merging duplicates, all fixed here. The central one, found by both seats:
the plan said "only the README is written before green" while its own handover folder,
`.gitignore` line and package copy wrote earlier. Checking it showed `new-website` never says
the README is written at "step 4"; what the file does say is that step 4 copies the doc
templates and fills their slots, so the plan now follows that: docs at step 4, everything
else after green. Round 4 (head `ad1e931`, Codex 176 s/74,664 tokens, GLM 138 s/53,099 tokens): 1 BUG fixed
(the luminance ceiling in scenario 32, rounded the wrong way a second time; the exact value is
0.019881), 1 RISK fixed (the `create-astro` mapping is now quoted in the plan, with its file and
lines, and in the evidence pack), 1 NIT fixed (scenario 19 names its remedy), and 1 BUG refuted
(GLM's claim that `BRAND.md`'s dark table lacks Hairline, Background and Surface rows; it has them
at `brand.md` lines 46 to 51, and the evidence pack's excerpt stopped at line 48). I judged
the fixes to change an illustrative figure, a quotation and the wording of one remedy, so no
round 5 was owed, and ran a single-seat wording pass over the whole plan (Codex at its own
effort, 489 s, 141,623 tokens). It found 5 BUG and 3 RISK that the scoped rounds had not: the
share cards regenerated before `LOGO` is wired (the generator draws no emblem while it is
unset, and loads only a raster), the raster input branch, the path each opt-in answer starts,
the README hook, a threshold attributed to the wrong file, and a stale status line. All are
fixed here. That judgment was wrong: round 5 was owed.
Round 5 (head `ddb61e4`, Codex at its own effort 314 s/111,150 tokens, GLM 206 s/52,364
tokens): 3 BUG, 3 RISK and 2 NIT after merging duplicates, nearly all in the text added after
the wording pass (the raster branch and the per-answer paths), all fixed here: the master a
later run starts from is recorded and may be a raster; a raster logo is padded to a square
because the OG generator stretches its input to 460 by 460; a raster's colours are sampled;
a table states which operations belong to the palette and which to the logo, with the
starter's own colours as the palette in force when none is chosen; owner-brought palettes
get proposals for the rows D6 adds; and the UI threshold is quoted from the file that states
it. Round 6 (head `c906f25`, Codex at its own
effort 271 s/93,496 tokens, GLM 191 s/54,525 tokens): 3 BUG, 3 RISK and 3 NIT after merging
duplicates, all fixed here. Both seats found, on their own, that share-card regeneration was
assigned to the palette part only (so a logo-only run never regenerated the cards) and that the
raster fallback contradicted scenarios 15 and 32; the fix states the raster's four differences
once, under Forms of input, and the other sections refer there. Also fixed: `COMPANY.logo`
cannot be "unset" (the starter sets it), a raster with no more-than-half-opaque pixel has no
colour to sample, a logo-only run on an existing site must read the site's current palette and
not assume the starter's, a missing `sharp` stops only the operations that render, and one path
form (`public/images/logo.png`) everywhere. Distinct findings by round: 35, 10, 6, 5, 8 (the
closing read), 8, 9: not falling any more, because each branch added late (raster, palette-only,
logo-only, existing sites) brings its own interactions. The maintainer chose, on
2026-10-11, to take the raster branch out of version 1 (decision 8); round 7 verified round 6's
fixes and that removal.
Round 7 (head `7badef0`, Codex at its own effort 290 s/138,829 tokens, GLM 581 s/61,143
tokens): 2 BUG, 2 RISK and 4 NIT after merging duplicates, all fixed here and not yet
re-verified. Both seats confirmed the raster removal is complete. What they found were
coherence gaps: "Writing" still set the palette values and the logo settings whatever the
operations table said; the logo prompt still told the tool what to "hand back" if it could
not draw a vector (a raster remnant); the agreement check on an existing site, where
`BRAND.md` may lack D6's rows or drift from the stylesheet (the stylesheet is the palette in
force, the drift is named, not blocking); and rollback, later runs, the preview's theme and
the npm remedy, which is now measured. The count by round: 35, 10, 6, 5, 8 (the closing
read), 8, 9, 8. On 2026-10-11 the maintainer also settled D5's refinement, D6 and the
`brand-handoff` folder name as proposed; that changed four status labels and no requirement text. The same day the handoff step
was run and its zip inspected (D3, "The handoff, tried"); that added what the real zip and
SVG look like, one clause to scenario 22 (the files may sit inside one top-level folder),
and the correction of scenario 32's example, which named the spike's test mark as the
trial's. Round 8 (head `8a7fd83`, Codex at its own effort 346 s/86,061 tokens, GLM 142
s/58,700 tokens; it verified round 7's fixes and the amendment): 3 BUG, 2 RISK and 1 NIT after
merging duplicates, all fixed here and not re-verified. Both seats found round 7's fixes landed
except one, whose cleanup would have removed a `brand-handoff` folder that was already there;
both found the scenario 32 correction only half done (its Then cell still called the spike's
mark the trial's) and one stale sentence saying the handoff package had not been seen; and
they asked for the npm commands and the handoff reply to be on record, which they now are.
