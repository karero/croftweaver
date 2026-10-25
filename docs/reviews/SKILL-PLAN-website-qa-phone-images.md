# Plan: website-qa keeps phone images small and runs Lighthouse itself

Built on the maintainer's go (2026-10-25), in the PR that carries this file. One change from the
plan, found in the build: `isMobile` is off (see "Run").

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | Step 0: do other sites have the problem? | ✅ 2026-10-25: yes, two of the four other sites | `docs/reviews/EVIDENCE-website-qa-phone-images.md` |
| 2 | This plan | ✅ written 2026-10-25 | this file |
| 3 | Plan review gate (Normal: a shipped test and a SKILL.md) | ✅ 2026-10-25: 5 rounds and a final full read, 47 findings (7 BUG), none open; wording pass clean | `docs/reviews/REVIEW-plan-2026-10-25-website-qa-phone-images.md` |
| 4 | Build: the test, its CI step, the SKILL.md changes (one PR) | ✅ merged 2026-10-25: DIFF review 6 rounds, 49 findings, no BUG open (two rare RISKs are BUGLOG follow-ups); CI green (55 checks) | karero/croftweaver#409, merge `1db96a6b` |
| 5 | Each site gets the test when its owner copies `tests/phone-images.spec.ts` in (`whats-new.sh` lists a new test but never copies one), and fixes what it finds | ⬜ each site's own PR | `scripts/whats-new.sh:74–76`: tests are frozen copies, "never auto-refreshed" |

## Why

Sites are named by letter: the repo keeps client names out (`scripts/check_clean.sh`). Site A
is an app's marketing site, B an agency's, C a meetup's, D an architecture practice's.

Site A went from mobile PageSpeed 98–99 to 100 (two PRs in its private repo, 127 and 130). Its
phones were downloading a 1900px CSS background hero; a 1200px phone copy brought LCP from about
2.0 s to 1.5 s. No toolkit test would have caught it, and Lighthouse would not have either:
Lighthouse 13.5's image check does not judge CSS images by size at all, and ignores savings
under 4 KiB (under 12 KiB for an image with a srcset); the lines are quoted in the evidence file. The skill also tells
the agent it cannot run Lighthouse and must ask the user. That is no longer true: `npx
lighthouse` 13.5 with `CHROME_PATH` set to Playwright's Chrome for Testing ran here against
https://croftweaver.com/ (mobile, 412px, 1.75x, score 0.99, LCP 1.8 s).

## Step 0: the other sites, measured

Home page, live production, 412×823 at 1.75x (Lighthouse's phone), scrolled in steps to load
lazy images. "Need" is displayed width × 1.75. Counts are from the retained run in the evidence
file; an earlier run the same morning found a few more site D tiles and no YouTube thumbnail, as
lazy loading on a live site lands differently between runs.

| Site | Rasters | Over 1.5× need | Worst |
|------|--------:|---------------|-------|
| <site A>/ (after PR 130) | 7 | hero 1.66, 3 logos (3–14 KB) | hero-bg-phone 1200px for 721: deliberate, PSI 100 |
| https://croftweaver.com/ | 1 | none | — |
| <site B>/ | 0 | — | SVG only |
| <site C>/ | 18 | 2 photos, 1 logo, 1 YouTube thumbnail | a 720px speaker photo shown 72px wide (5.7×); no srcset |
| <site D>/ | 35 | 24 tiles at 2.04, 3 at 1.70–1.74 | 1200px project tiles shown 336px wide, no srcset |

So the problem is real beyond site A: build the test.

## 1. A shipped test: `tests/phone-images.spec.ts` in the starter

**Run.** For every page in `PAGES`, a fresh `browser.newContext({ viewport: 412×823,
deviceScaleFactor: 1.75, hasTouch: true })`; no cache is carried between pages. `hasTouch`
gives a phone's media queries (`pointer: coarse`, `hover: none`, checked). Built without
`isMobile`, against the plan: with it, Chromium's phone emulation starts at a 980px layout width,
and under the test runner the starter's fixture fetched its `media="(min-width: 720px)"` preload
4 times out of 4 (0 of 4 without), which would fail site A's correct desktop preload. The response listener is attached
before `goto` and records every response whose content type is a raster image, whatever
requested it (preloads included), with its size from `response.body()`. The page is then
scrolled one viewport at a time with a short pause, and the test waits until every `<img>` is
`complete` and the network is idle.

**Who uses each file.** At each scroll step and once more after the final wait (a carousel may
swap a file out), the test records every element using a URL: `<img>` `currentSrc`, `<video poster>`, and
any `url()` in the computed style of an element or its `::before`/`::after` (`background-image`,
`mask-image`, `border-image-source`, `list-style-image`, `content`, `cursor`, `shape-outside`).
A file shown and removed again within one pause is not seen; that is rare, and named under
Judgment. A file's displayed width is
the widest non-zero box among its users. With `cover` (object-fit or background-size) it is the
width it is drawn at (box height × file aspect, if larger); with any other value, the box width,
since that is all that shows. Each layer of a multi-layer background counts on its own. The
file's real width comes from decoding it (`new Image()` on its URL), never from
`img.naturalWidth`, which a `w`-descriptor srcset scales.

**It fails when:**

- **a file is wider than a 3x phone could use**: real width > 1.1 × displayed width × 3, **and**
  cutting it to that width saves at least 4 KiB, estimated as bytes × (1 − (limit/real)²)
  (modelled on Lighthouse's estimate and floor);
- **a preloaded image is downloaded and not shown**: a `<link rel="preload" as="image">` file
  that was downloaded and that no element uses at any scroll step (a preload whose `media` does
  not match at 412px is not fetched and not counted, so site A's desktop-only hero preload
  passes) (the bug PR 130 guarded against: a preload whose `media` drifts from
  the CSS breakpoint makes phones fetch both heroes);
- **a downloaded raster is not accounted for**: every file must end up judged or on a short
  list with its reason (repeating background, only zero-size users, used by a property above
  but not judged by width). A file in neither fails, so nothing is skipped silently. The output
  prints, per page, how many files were judged and the list.

SVG is not a raster and is not collected.

**Why not 1.5× need.** 1.5 fails good choices: site A's new phone hero (1.66) and site D's 1000px
and 1024px tiles (1.70, 1.74) are each one file serving every phone, and right for a 3x phone
(412 × 3 = 1236). One file cannot be right for both 1.75x and 3x phones; that is what srcset is
for. So the test sets a floor no single file may pass, "sharper than any phone can show", and
the skill (section 3) asks for srcset above it. The 1.1 slack covers 3x phones up to 453 CSS px
wide (1.1 × 412); the widest current ones are about 440. The line holds for phones 412px and
wider: a full-width file that passes at 412 can still be more than a 360px 3x phone shows. In the brief's terms the limit is
1.9× need.

Against the step 0 data: fails site C's two speaker photos (about 12 and 8 KB to save) and,
just, its YouTube thumbnail (1280px for a 364px box, about 4.2 KB: a site picks that URL, so a
third-party host is judged too); fails site D's 24 tiles (1200 > 1.1 × 1008 = 1109; 6–54 KB each); passes all of site A, croftweaver and
site B; and fails site A before PR 130 (1900px hero, 26 KB to save). It would not have caught
site A's trip screenshot (780px for 630 needed): that was a 1.75x saving, the srcset recipe's
job, and the 1.5 threshold would have missed it too.

**How it is tested.** The starter renders no raster images (its only one, `og/default.jpg`, is
named in a meta tag and never downloaded by the page), so on its own the test passes with
"0 judged". A job in `template-tests.yml`, in the tagline job's pattern ("each mistake turns its
own test red"), copies the starter and adds a page with WebP images made by `sharp` (the
hero-carousel job already makes images this way) from random noise, so each oversized file is
well over the 4 KiB floor (the hero-carousel job already uses `sharp`, for flat JPEGs). The
images go into the starter's `src/pages/index.astro`, as the tagline and hero-carousel jobs do,
not a new page, which `orphans`, `llms-coverage` and `seo` would fail; every `<img>` carries alt,
width, height and `loading`, so `images.spec.ts` stays green. Cases:

- green, whole `npm test`: a right-sized `<img>`; a right-sized CSS background with `cover`; a
  two-layer background; an oversized repeating background, asserted to be on the list with its
  reason; an image whose only user is zero-size, asserted listed; a preloaded file shown first
  and swapped out by script at a scroll step; a preload with `media="(min-width: 720px)"`
  (not fetched at 412px); a file just under the 4 KiB floor;
- red, `phone-images.spec.ts` alone, checking that it is the failing test and that the message
  names the file: an oversized `<img>`; an oversized `::before` background; an image preloaded
  but not shown; a raster a script loads with `new Image()` and never attaches (the "not
  accounted for" rule).

This enters through the same call production makes: Playwright against the built site. Before
the PR, the spec also runs once against site A at `d5bace7^1` (red: the 1900px hero) and
`main` (green); the output goes in the PR.

## 2. Rewrite "Performance — Lighthouse / PageSpeed"

Replace the handoff with steps the agent runs:

1. `npm install lighthouse@13` into a scratch folder, so the site's `package.json` and its
   pre-push hook are untouched. Then, with `CHROME_PATH` set to Playwright's Chromium (printed by
   `node -e "import('@playwright/test').then(m=>console.log(m.chromium.executablePath()))"` run in the
   site folder, where Playwright is installed), run in the scratch folder, so `npx` finds that
   install and not the latest version, the command the evidence file records: `npx lighthouse <url> --only-categories=performance --output=json --output-path=<file>
   --chrome-flags="--headless=new" --quiet`. Without `--headless=new` it opens a window, and
   fails where there is no display.
2. Measure a deployed URL, never a local server. `python -m http.server` sends no compression,
   which inflated sizes and misled a decision on site A; `astro preview` does gzip (checked) but
   is still not Cloudflare. The `main` preview (PUBLISHING.md's step 3) is for comparing a change
   before it goes live. It has no analytics (`src/config.ts` turns it on for production only),
   so the number that counts for "done" is production's, measured after publishing.
3. 5 mobile runs (the default preset); report the run whose performance score is the median,
   with its FCP, LCP and the insights it raises. One run with `--preset=desktop` as well, since
   the skill asks for both today; the targets are judged on mobile.
4. Fallback when Lighthouse cannot run: https://pagespeed.web.dev/ in the built-in browser. The
   keyless PSI API ran out of quota two days running on site A (that session's note, not
   checked here); do not lean on it.
5. Judge image sizes by the test in section 1, not by Lighthouse's image insight alone: that
   insight judges one device and skips CSS images.

Targets stay (FCP ≤ 1.8 s, LCP ≤ 2.5 s). "Done means" changes from "the user's PageSpeed run" to
"the agent's median production run, or the user's when the agent could not run one".

## 3. "Fixes that worked" (a short list in the same section)

- **Analytics, when Lighthouse flags the analytics script:** defer the init and the library,
  the library placed after the site's own deferred script (site A PR 127; reference site A's repo
  `tests/analytics-load-order.spec.ts`). The starter keeps its `async` tag (`Base.astro`), and
  the skill's existing bullet about it stays; this is a fix for a site that needs it, not a
  starter change.
- **CSS background hero:** a phone-sized copy, with `<link rel="preload" media>` pairs whose
  queries match the CSS breakpoint exactly (site A: 719/720px), and a test at each side of the
  breakpoint that only that side's file downloads (the shipped test runs at 412px only, so it
  cannot see drift near the breakpoint).
- **srcset/sizes:** `sizes` mirrors the CSS, as `min()` of the real column widths; tested by a
  width sweep: a fixed list of width/ratio pairs, one fresh context each, and for each pair the
  file expected there. The skill gives site A's repo `tests/phone-images.spec.ts`'s third test as
  the example and claims no more than it shows: at its ten pairs, Chromium picked the smallest
  file at least displayed width × ratio wide (PR 130's CI, merge `d5bace7`; rerun against
  production in Chromium 151, output in the evidence file). A site's own sweep lists its own
  pairs. This is a recipe the site writes, not part of the shipped test.

## What was verified, what is judgment, and the case against

- **Verified here, kept in the evidence file:** the step 0 table; Lighthouse 13.5's 4 KiB and
  12 KiB floors and its CSS skip; one local Lighthouse run and its command; `astro preview`
  gzips, production sends brotli. Also checked: site A's 1900/1200/780/640px widths from
  site A's repo (`origin/main`) (the 1900px file is still there as the desktop hero), and the
  1900px hero's bytes and its 26 KB saving, in the evidence file. Not checked: that local runs match PSI, and the PSI quota failures
  (both from site A's own session).
- **Judgment:** "3x phone + 10%" as the limit; the 4 KiB floor; scrolling instead of forcing
  `loading=eager`; the list of CSS properties that count as "used" (canvas drawing is not seen:
  a site that draws a preloaded image on a canvas would fail the preload rule); not seeing a
  file shown and removed within one scroll pause.
- **Against:** the floor is loose. Site D's three 1000–1024px tiles would save 74–167 KB each on a
  1.75x phone, and pass. A 1.5 limit would push sites harder. The answer here is that a test
  which fails right-sized files gets switched off, and the srcset recipe covers the rest; but it
  is a choice, and the maintainer may prefer the stricter line.
