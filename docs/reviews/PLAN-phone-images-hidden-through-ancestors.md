# PLAN — the phone-images test judges "hidden" through an image's ancestors

Status: passed the PLAN gate (5 rounds and a final full read; trail `docs/reviews/REVIEW-plan-2026-10-30-phone-images-hidden-through-ancestors.md`). Being built.
Branch: `fix/phone-images-hidden-through-ancestors`.

## What

In `skills/new-website/templates/astro/tests/phone-images.spec.ts`, `usersNow()` marks a user of an image `hidden` when its own computed `visibility` is not `visible` (three places: `<img>`, `video[poster]`, every element and its `::before`/`::after`). Change that one judgment so an image also counts as hidden when:

1. it, or any ancestor, has `opacity: 0`, or an ancestor has `content-visibility: hidden`;
2. an ancestor that clips (`overflow` `hidden` or `clip`) leaves none of its box showing.

Everything else stays: the size floor (hidden files under 4 KiB pass), the messages, the width judgment.

## Why

Found by Codex in the review of a site's PR that took this test from v0.34. Today a 4 KiB+ file that nobody sees passes when it hides by opacity (a fade carousel's waiting slides, a "reveal on scroll" that never ran) or sits clipped out of an `overflow: hidden` track (a sliding carousel's other slides, a collapsed accordion). That is a silent wrong pass. `visibility: hidden` on an ancestor is already caught, because `visibility` inherits; `opacity` does not inherit, and clipping is not a style of the image.

## How

All new code lives inside `usersNow()`: `page.evaluate` sends the function's source to the page, so a helper at module level would not exist there.

1. **Opacity and content-visibility: the browser's own check.** `el.checkVisibility({ opacityProperty: true, visibilityProperty: true })` returns false when the element or an ancestor has opacity 0, when an ancestor has `content-visibility: hidden`, when its own `visibility` is not `visible`, and when it has no box. The starter runs Chromium only (`playwright.config.ts`, one project). Read on the starter's own Playwright 1.64.1 (Chromium 156), 2026-10-30 (evidence READ 1):

   | Case | `checkVisibility` |
   |---|---|
   | img in a `div` with `opacity: 0` | false |
   | img in a `div` with `opacity: 0.01` | true |
   | img in a `div` fading from 0 to 1 (`transition: opacity 1s`), read 50 ms in (opacity 0.07) | true |
   | img in a `div` with `content-visibility: hidden` | false |
   | img with its own `opacity: 0` | false |
   | img with `visibility: visible` inside a `visibility: hidden` div | true |

   So a fade carousel's incoming slide counts as shown as soon as its opacity is above 0, and its waiting slides do not. (CI pins the static case, G1; the mid-fade case rests on this read, and any one scroll stop that sees a slide shown is enough.)
   - **A browser that ignores the option.** An older Chromium ignores the unknown `opacityProperty` and answers true for opacity 0, which would switch the fix off without a word; a site copying the file in may run an older Playwright. Once per `usersNow()` call, a throwaway `div` with a child is added, both styled inline with `all: initial; display: block` (which resets the probe's own styles; CSS on an ancestor such as the body, or an `!important` rule such as `div:empty { display: none !important }`, can still hide it), and removed after two reads: the child must read visible with the parent at opacity 1, then hidden at opacity 0. If the first read fails, the function throws that the probe is hidden at opacity 1 (site CSS on the body, such as a page fade-in, or an `!important` rule); if the second fails, "this browser's checkVisibility does not read opacity; update Playwright". Either way the test fails loudly.
   - **Pseudo-elements** have no element to call it on. A `::before`/`::after` is hidden when its host fails `checkVisibility({ opacityProperty: true })`, or its own computed `visibility` is not `visible`, or its own `opacity` is 0. The host's own `visibility` is left out, because a pseudo-element can set `visibility: visible` inside a hidden host (READ 1, `vh`).
   - **`display: contents` host.** Such a host has no box, so `checkVisibility` is false (READ 1, `dc`), yet its `::before`/`::after` are drawn. For a pseudo-element, the check runs on the nearest ancestor-or-self of the host whose `display` is not `contents`. Today such a pseudo-element counts as shown; without this the fix would turn it into a false "hidden".
2. **Clipping: one walk up the ancestors.** Start from the element's border box (`getBoundingClientRect`). Walk from its parent up to, but not including, `document.body`. An ancestor clips on an axis when its computed `overflow-x` (or `overflow-y`) is `hidden` or `clip` and its `display` is not one where `overflow` does not apply (`inline`, `contents`, and the table row, row-group and column displays; one literal regex). A clipping ancestor narrows a clip box, on that axis, to its own border box (`getBoundingClientRect`). An ancestor with `overflow: clip` (on either axis) and an `overflow-clip-margin` other than `0px` is skipped: its clip can reach past the border box, and skipping errs toward shown. Hidden when the part of the element's box the clip box leaves showing, on either axis, is under 1 CSS px, or under the box's own size on that axis where that is smaller (so an image under 1px tall that a clip leaves whole stays shown). The 1px: fractional layout (a track moved by `translateX(-33.3333%)`, a container of fractional width) leaves the slide beside the clip a sliver inside it, which must not count as shown. A collapsed accordion (`height: 0`, no border) has a clip box with no height, so its content is hidden.
   - **Why the border box, not the padding box.** `clientWidth` is 0 on boxes where overflow does not apply, and does not scale with a transform while the rect does (READ 1: `scale(2)` gives rect width 100, `clientWidth` 50). The border box comes from the same rect as the element's own box, so both are in the same, transformed, coordinates. It is a little larger than the true clip (by the border), which can only make an image count as shown.
   - **Why not `body` and `html`.** Their `overflow` usually passes to the viewport (`body { overflow-x: hidden }` is common), and the viewport is not a clip here: the test scrolls the page.
   - **What is not a clip:** `overflow: auto` and `scroll`. The user can scroll to that content, so a horizontal scroll gallery's later pictures count as shown, as today.
   - **Containing blocks.** An absolutely positioned or fixed box is clipped only by ancestors from its containing block up. The walk finds that block itself (`offsetParent` passes over a transformed ancestor): for `absolute`, the nearest ancestor that is positioned or moved by `transform`, `translate`, `rotate` or `scale`; for `fixed`, the nearest so moved. Ancestors below it are skipped, and the same is done for each out-of-flow ancestor met. No such ancestor below the body: not clipped.
   - **Pseudo-elements:** their own box is not readable, and an absolutely positioned one can escape its host's ancestors. A static or relative `::before`/`::after` takes the host's clip result: the walk runs on the host's box, from the host's parent up, and only when the host's box has a size. An `absolute` or `fixed` one gets no clip test (today's result).
   - **The element's own overflow** does not clip its own background or `<img>`, so the walk starts at the parent.
3. **Cost.** The judgment runs only for elements that use an image URL (today `hidden` is worked out for every element and pseudo-element on the page). One helper, `hiddenOf(el, pseudoStyle?)`, used at the three places: one native call plus one ancestor walk per image user per scroll stop.
4. **The log line sorts its lists.** `hidden and under 4 KiB` and `not judged` list file names in download order, which varies run to run. They are sorted, so the CI job can expect an exact line with more than one name. No other output changes.
5. **Comment and docs.** The spec's header says what "not shown" now means, in one line. `skills/website-qa` and the starter's docs get a sentence only where they say what counts as hidden (found by grep for "hidden"). A `docs/BUGLOG.md` row for the next release notes, as the repo does for starter changes: an existing site gets this only by copying the file in again, and may then see new failures it should fix.

**Not covered, on purpose.** Each case below errs toward today's result (the image counts as shown):
- `clip-path` and the legacy `clip`. No browser API reports the area a clip-path leaves; working it out means parsing `inset()`, `circle()`, `polygon()` and `path()` against the box. The shapes that hide a whole box are the screen-reader-only idiom (`clip-path: inset(50%)` on a 1 px box), which holds text, not 4 KiB pictures, and a reveal effect, which is shown once it plays.
- A pseudo-element on a host that itself clips to nothing (`height: 0; overflow: hidden` with a sized `::before`): the walk starts at the host's parent.
- A containing block made by `filter`, `perspective`, `contain` or `will-change` rather than `position` or `transform` (the walk passes over it), a clip with an `overflow-clip-margin` (skipped, above), an `html` that clips, and an element covered by another element (nothing in the test judges stacking).

**Where a new false "hidden" remains possible.** A static pseudo-element moved outside its host by `relative` offsets or negative margins while the host is clipped away; an element whose rect lies outside a clipping ancestor's border box though a rotation or skew draws part of it inside. Both rare; a false "hidden" fails loudly and names the file, and a site can fix it by giving the image a box of its own.

## How it is tested

The `phone-images-test` job in `.github/workflows/template-tests.yml` builds a starter site with generated WebP files and a block of cases on the home page. It gets these cases. Noise files are well over 4 KiB; flat files under it (the job's size check extends to the new flat files).

Green page, added:

| Case | Markup | Expected |
|---|---|---|
| G1 fade carousel | a grid of two stacked slide `div`s, each holding an `<img>` 200px wide; `.slide { opacity: 0; transition: opacity 1s }`, `.slide.on { opacity: 1 }`; showing slide `fade.webp` (noise), waiting slide `wait.webp` (flat) | `fade.webp` judged by width; `wait.webp` listed as hidden and under 4 KiB |
| G2 sliding track | a 200.3px box (fractional, so `off.webp` sits 0.3px inside the clip) with `overflow-x: hidden` only (so `overflow-y` is `auto`) holding a 400px flex row of two 200px images: `track.webp` (noise), `off.webp` (flat) | `track.webp` judged; `off.webp` hidden and under 4 KiB |
| G3 scroll gallery | a 200px `overflow-x: auto` box, `tabindex="0" role="region" aria-label="Gallery"` (the starter's axe test needs a scroll box to be focusable), holding a 400px row: a spacer, then `scroll.webp` (noise) outside the scrollport | judged (auto is not a clip) |
| G4 escaping box | `position: relative` wrapper, then an `overflow: hidden; height: 0` box, then an `<img position: absolute>` `esc.webp` (noise) | judged (the clip box is below its containing block) |
| G5 `display: contents` host | a `display: contents` element whose `::before` has a 100px background `dc.webp` (noise) | judged |
| G6 inline clipper | an inline `<span style="overflow: hidden; font-size: 0">` around a 200px `<img>` `inl.webp` (noise); the span's rect then has no height, so the case fails if inline boxes are taken as clips | judged (overflow does not apply to an inline box) |
| G7 pseudo-element in a clip box | a 200px box with `overflow: clip` (height auto) holding a static `div` whose `::before` has a 100px background `cb.webp` (noise) | judged |
| G8 thin image | an `<img>` `thin.webp` (noise), 200px wide and 0.5px tall, `object-fit: cover` (the starter's images test fails a stretched image), inside an `overflow: hidden` box that leaves it whole | judged (the clip leaves its whole height) |
| G10 clip with a margin | an `overflow: clip; overflow-clip-margin: 20px; height: 0` box holding a 200px `<img>` `margin.webp` (noise); 20px of it shows | judged (the case fails if the margin skip is dropped) |
| G9 fixed box escaping a clip | an `overflow: hidden; height: 0` box holding a `position: fixed` 40px `<img>` `pin.webp` (noise, 120 × 80) at the viewport's bottom left | judged (a fixed box is clipped only from a transformed ancestor up) |

The green step's exact line becomes: `26 judged by width; hidden and under 4 KiB: /fx/hidden.webp, /fx/off.webp, /fx/wait.webp; not judged: /fx/border.webp (border-image-source)`. With today's spec that line does not match (`wait.webp` and `off.webp` count as shown and are judged by width), so the green step fails before the fix.

Red cases, added, one change each, run through the job's existing `red` helper (exactly one test fails, it is the home page's, the message names the file):

| Case | Change | Message must say |
|---|---|---|
| R1 waiting slide over the floor | `wait.webp` → `zero.webp` (noise) | `/fx/zero.webp is downloaded but hidden at 412px` |
| R2 clipped slide over the floor | `off.webp` → `zero.webp` | same |
| R3 own opacity | `opacity: 0` added to `#fx-vis` | `/fx/vis.webp is downloaded but hidden at 412px` |
| R4 escaping box caught | G4's `height: 0` box gets `position: relative` (now the containing block) | `/fx/esc.webp is downloaded but hidden at 412px` |
| R5 pseudo-element's own opacity | `opacity: 0` added to G5's `::before` | `/fx/dc.webp is downloaded but hidden at 412px` |
| R6 pseudo-element clipped | G7's box gets `height: 0` | `/fx/cb.webp is downloaded but hidden at 412px` |
| R8 transformed containing block, absolute | G4's `height: 0` box gets `transform: translateX(0)` | `/fx/esc.webp is downloaded but hidden at 412px` |
| R9 translated containing block, fixed | G9's box gets `translate: 0px` | `/fx/pin.webp is downloaded but hidden at 412px` |
| R7 a browser that ignores the option | an inline page script wraps `Element.prototype.checkVisibility` so it drops `opacityProperty` | `does not read opacity; update Playwright` |

R1 to R9 all stay green with today's spec. Every existing case and expected message stays as it is, apart from the green line's count and list.

**Before/after proof.** The job stops at its first surprise, so a run of it cannot show every "before" result. A local runner (a script in the PR's evidence, not committed) builds the job's site once, then for each spec (today's, then the fix) runs the green check and each red case on its own, recording pass or fail for every case and never stopping early. Expected: today's spec fails the green check and leaves R1 to R7 green; the fix passes the green check and turns R1 to R7 red with their messages. With the fix, the runner also runs `npm test` once on the green page, as the job does, so the starter's other tests (axe among them) see the new markup. Both outputs go in the PR. CI then runs the job as it is, on the fix.

Review depth after build: Normal (the diff changes a test that ships into users' sites, which is never Light).

## Status

| Step | State | Evidence |
|---|---|---|
| Plan | done | 0bc3d3cd |
| PLAN gate | passed: 5 rounds (Codex alone each round, melious out of balance; fresh-eyes Sonnet in round 1) and a final full read (Opus) | `docs/reviews/REVIEW-plan-2026-10-30-phone-images-hidden-through-ancestors.md` |
| Build: spec change, fixture cases, website-qa sentence, BUGLOG row | done | this branch's build commit |
| Local before/after run | done: before, the green line fails and R1 to R7 stay green; after, all pass and turn red, and `npm test` passes | the PR description |
| PR, DIFF gate (Normal), CI green | in progress; G6, G8, G9, R8, R9 and the containing-block and overlap rules changed in DIFF round 1 | karero/croftweaver#454 |
