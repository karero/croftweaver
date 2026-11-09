# Plan: every new site gets its own icon at setup

Status: plan, for the PLAN gate. BUGLOG row 2026-10-09, `src/layouts/Base.astro` and
`public/manifest.webmanifest` ("The starter links seven files that its `public/` folder does
not hold…"). Decision (the maintainer, 2026-11-09): "Icon from the site's initial". Every new
site gets the site's initial on its own colour at setup; the brand kit replaces it when the
owner wants a real logo.

## What and why

The starter links seven files it does not ship: `/favicon.svg`, `/favicon.ico`,
`/apple-touch-icon.png`, `/icon-192.png`, `/icon-512.png`, `/icon-maskable-512.png` (in
`Base.astro` and the manifest), and `/images/logo.png` (`COMPANY.logo` in `src/config.ts`, the
Organization schema's `logo`). The scaffold leaves the Astro logo as `favicon.svg` and
`favicon.ico`; the other five are missing and nothing checks them. So a new site ships the Astro
logo in the tab, a broken home-screen icon and a schema `logo` that is a 404, unless the owner
takes the optional brand kit. After this change every site has all seven files from its first
green test run, and a test keeps it so.

## Scenarios

| Id | Given | When | Then |
|---|---|---|---|
| S1 | A new site "Bäckerei Krume", `--brand` still the starter's `#000000`, the scaffold's Astro logo in `public/` | setup runs `node scripts/make-icons.mjs --setup` | the seven files exist; the icon is a black tile, a white inner outline and a white "B"; `npm test` is green |
| S2 | A site named "Ölmühle Rapp" | the same | the letter is "O": accents are folded (`Ö` → `O`; also `ß` → `S`, `Æ` → `A`, `Ø` → `O`, `Œ` → `O`, `Ł` → `L`, `Đ`/`Ð` → `D`) |
| S3 | A site named "3D-Druck Weber", or "„Café Mohn“" | the same | "3" is drawn for the first, "C" for the second: the first letter or digit counts; quotes, spaces and signs before it are skipped |
| S4 | A site named "Жар-птица" (Cyrillic) | the same | it writes nothing and says: the name starts with "Ж", which it has no drawing for; ask the owner for one letter A–Z or digit, and run it again with `--letter X`. A name with no letter or digit at all gets its own sentence, with the same way out |
| S5 | A light brand colour, `#f2d16b` | the same | the outline and the letter are black, since white is under 3 to 1 on that tile (black then always reaches it: one of the two always reaches 4.58 to 1 or better) |
| S6 | `SITE.name` is still the starter's `Example`, or an unfilled `[BRACKET]` slot, or cannot be read as a plain string | the same | it writes nothing and says to set `SITE.name` first |
| S7 | `sharp` does not load in the site | the same | it writes nothing and prints the brand kit's advice (`npm install --include=optional`, then check `node -e "require('sharp')"`); it never adds `sharp` to `package.json` |
| S8 | The site's icons came from the brand kit, or from anywhere but this script (an existing site run from `whats-new`, without `--setup`) | `node scripts/make-icons.mjs` | it writes nothing and names the files that are not its own; for brand-kit files (their `favicon.svg` starts with `<!-- Installed by the website-brand-kit skill`, the start all three forms of the brand kit's line share: `MARK`, `MARK_CURRENT`, `MARK_CURRENT_OWN` in `_install.py`) it says to use the brand kit. `--replace` overrides, and an assistant passes it only on the owner's yes |
| S9 | The starter's icons are in place | the owner gives the brand kit a logo | the intake replaces all seven with a word, as it does the scaffold's Astro logo today, without asking `--replace-icons` |
| S10 | The starter's icons are in place | a brand kit run changes only the colours, `--brand` included | the intake leaves the icons and says in its report that they still show the old colour; the brand kit's §6 has the assistant run `node scripts/make-icons.mjs` and commit; until then the icon test warns (S12), it does not fail |
| S11 | An existing site | the owner runs `whats-new` | it lists `scripts/make-icons.mjs` and `tests/icons.spec.ts` as MISSING, with a note for each kind of site: copy both; a site with no icons (or only the Astro logo) runs `node scripts/make-icons.mjs --setup` before `npm test`; a site with the brand kit's icons needs nothing more; a site built by hand from `tab-icon.md` copies `public/icon-512.png` to `public/images/logo.png` |
| S12 | Any site | `npm test` | `tests/icons.spec.ts` fails when one of the seven is no longer linked, or a linked file is missing, of the wrong type or the wrong size (512, 192, 180, 512 and 512 pixels; an ICO with a 32-pixel frame; an SVG). For the starter's icons it warns, not fails, when the colour recorded in `scripts/icons-made.json` came from `--brand` and `--brand` has changed since, or the recorded letter came from the name and the name's letter has changed |

## How

**Where in setup.** The starter's `README.md` step 3 runs `npm install`; its step 4 sets
`SITE.name` and the theme colour, and today says "Add `public/` icons". That sentence becomes
`node scripts/make-icons.mjs --setup`, placed after the name and the theme colour are set. `new-website` §3 step 1, which lists
the values to set in `src/config.ts`, adds `SITE.name` to its list and the same command after it.
Both come before step 5's first green run, because the icon test is part of that run. The launch checklist line in §4 ("favicon/manifest icon set in place … built as
`tab-icon.md` says") becomes: the starter's icons in place, or the brand kit's.

**The tool.** `scripts/make-icons.mjs`, Node with no new dependency, in the starter overlay:

- reads `SITE.name` by importing `src/config.ts` (Node strips the types; seen working on Node 26,
  not checked on 22.23, the starter's floor: the builder checks it there first, and if it fails,
  reads the `name:` line in the `SITE` block whenever the import throws, at run time; that line
  must yield one quoted literal or be refused as S6), and the light theme's `--brand` from `src/styles/global.css` with a literal
  regex. A value that is not `#rrggbb` is refused with a sentence, and `--colour #rrggbb`
  overrides. Both readers, and the letter rule, are exported, so the icon test uses the same code;
- draws `public/favicon.svg` by the tab icon recipe (`website-brand-kit/references/tab-icon.md`):
  the tile in `--brand` with `rx="104"`, the inner outline 72 to 440 with a 32-wide stroke, and
  the letter inside it. The letter is drawn as strokes from a table of 36 glyphs (A–Z, 0–9) on the
  512 grid, one stroke width, so no font is needed and the letter does not depend on the fonts a
  machine has. The first line is a comment that names the script, the letter and the colour;
- renders the PNGs from that SVG with the site's own `sharp` (checked in the starter's
  `package-lock.json`: `sharp` 0.35.5 is there with `optional: true`, from Astro's
  `optionalDependencies`; the brand kit renders with the same one; where it does not load, S7). It makes `icon-512.png`,
  `icon-192.png`,
  `apple-touch-icon.png` (180), each flattened on the tile colour; `icon-maskable-512.png`, the
  whole icon (tile, outline and letter) at 70 % on the tile colour (the recipe's safe-zone figure); `images/logo.png`, the same
  picture as `icon-512.png`, as the brand kit does;
- writes `favicon.ico` itself: PNG frames of 16, 32, 48 and 64 pixels behind a 6-byte header and
  one 16-byte entry each (the brand kit's `ico_from_png` does one frame the same way);
- writes `scripts/icons-made.json`: each file's path and SHA-256, the letter and the colour, and
  for each whether it came from the site (`SITE.name`, `--brand`) or from `--letter`/`--colour`.

**Whose files it may overwrite.** A file may be written when it is missing or its SHA-256 is in
`scripts/icons-made.json`. With `--setup`, which setup passes minutes after the scaffold wrote
them, `public/favicon.svg` and `public/favicon.ico` may be written too, whatever they hold, but
only on a site that looks fresh: `favicon.svg` exists and does not start with the brand kit's
line, and none of the other five files exists; otherwise `--setup` is refused as S8. No hash of the Astro logo
is needed, so a newer create-astro with another logo does not stop setup
(CI never runs create-astro, so nothing would catch that). Anything else stops the run before it
writes (S8). A stop part way must not leave files no record
knows, or the next run would refuse them. So the run writes all seven to temporary files first (in `scripts/.icons-tmp/`, outside
`public/` so a stopped run serves nothing half-made, on the same disk so the renames hold),
then writes the record with both the old and the new hash of each path, then renames the seven
into place one by one, then writes the record again with the new hashes only. Each record is
itself written to a temporary file and renamed into place, so it is always whole. Whatever point a
run stops at, each file is either the old or the new one, and the record knows both; the next run
overwrites it. A mixed set (some old, some new) can be left, and the next run puts it right.

**The brand kit.** `_site.is_scaffold_default` also returns true for a file whose SHA-256 matches
its entry in `scripts/icons-made.json` (S9): about ten lines and one test. The brand kit writes the
same seven paths at the sizes the icon test pins (`_icons.py`: 32-pixel ICO frame, 192, 512, 180,
512 maskable, `images/logo.png` a copy of the 512), so its sites pass that test. So do the six
files `tab-icon.md` has an owner make by hand (512, 192, 180, 512 maskable, an ICO of 16, 32, 48
and 64), once `images/logo.png` is added (S11). A colours-only run
changes nothing in the icons and adds one note when the starter's icons stay on the old colour
(S10). `tab-icon.md` keeps the by-hand recipe for the owner's own mark in a tile; its opening says
the starter now makes the letter tile at setup.

**Existing sites.** `scripts/make-icons.mjs` and `tests/icons.spec.ts` go into
`TEMPLATE_TRACKED` in `scripts/whats-new.sh`, with the line of S11. A site that already has icons
keeps them: the test passes on any seven files of the right type and size, and the script refuses
to touch icons it did not make. A site built by hand from `tab-icon.md` has six of the seven and no
`images/logo.png`; the `whats-new` line says to copy `public/icon-512.png` there, as the brand kit
does. One release-notes row in `docs/BUGLOG.md` for 0.35.

**Rare cases, refused.** A name with no letter A–Z or digit after folding (S4). A `--brand` that
is not a hex value. Nothing is guessed: no transliteration, no "first Latin letter further on".

## How it is tested

- `tests/icons.spec.ts` in the starter (S12): holds the seven paths and their sizes, written in
  the test; checks that the built home page's `<link rel="icon">` and `rel="apple-touch-icon"`,
  the manifest that page's `<link rel="manifest">` points to, its `icons`, and `COMPANY.logo` still
  link each of them; and for each, that the file
  is served, its type matches, and its size is read from the PNG header (the ICO: from its
  entries, which must include 32). The warnings read `scripts/icons-made.json` through the
  script's exported readers. It runs in every site's `npm test`. It checks files, not pictures:
  an icon redrawn by hand in another colour passes it.
- A Node self-test for the script, run in `template-tests.yml` on the scaffolded site with its
  real `sharp`, covering S1 to S8: the letter chosen for each name in S1 to S4 (expected letters
  written by hand), the mark colour for S5, the refusals of S4, S6 (on the starter's
  `config.ts` as shipped, so its `Example` and the refusal stay in step), S7 (the script run in a copy
  of the site with no `node_modules`, where `sharp` cannot be found) and S8 (a file that is not its
  own, a brand-kit file in each of its three first-line forms, the two favicons without `--setup`,
  and `--setup` on a site that has one of the other five or the brand kit's favicon), `--setup`
  replacing a favicon of unknown content on a fresh site, the files' sizes read back, and a run stopped at each point of the write (after
  the temporary files, while and after each record is written, after each rename), each followed by a run that must succeed without
  `--replace` and leave seven new files and a record of them.
- CI's own runs of the suite: every job in `template-tests.yml` that runs `npm test` on the
  overlay sets `SITE.name` and runs `node scripts/make-icons.mjs --setup` first, in one named step,
  so the suite meets a site as setup leaves it. The suite runs nowhere else in the toolkit (the
  Makefile and the other workflows do not run it; checked by grep); the builder lists the jobs in
  the PR. For each glyph, it renders the icon at 32 and 64 pixels and checks
  that the letter's pixels stay inside the outline with clear space, and that no two glyphs give
  the same picture at 32.
- The brand kit: one test in its suite for S9, on a site whose icons came from `make-icons.mjs`.
  It also asserts the seven paths and sizes the icon test pins on the files the intake wrote, so
  a later change to `_icons.py`'s sizes fails there before brand-kitted sites go red.
- The 16-pixel frame is checked by eye only (the sheet below); the automated glyph checks run at
  32 and 64.
- By eye, once, before the PR is marked ready: the 36 glyphs on one sheet at 16, 32 and 180
  pixels, on a light and a dark tab bar, attached to the PR for the maintainer's look.

## Open questions closed here (judgment, not measured)

- The tile colour is `--brand`, the Primary. On the starter's colours it is black: every
  unbranded site gets a black tile. A colour from the name (a hash) would set sites apart but
  ignore the owner's own colour; the decision says "on its own colour", which reads as the site's.
- `images/logo.png` is made too, so the schema `logo` is not a 404. Google may show it beside
  the site in search; it shows the favicon there already.

## Status

| Step | State | Evidence |
|---|---|---|
| Plan, PLAN gate | done: 4 rounds, no BUG open | `docs/reviews/REVIEW-plan-2026-11-09-starter-icons.md` |
| The maintainer's go | waiting | — |
| Build: script, test, setup lines, brand kit, whats-new | not started | — |
| DIFF gate, merge | not started | — |
