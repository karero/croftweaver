# Review trail: plan, the phone-images test judges "hidden" through an image's ancestors

Artifact: `docs/reviews/PLAN-phone-images-hidden-through-ancestors.md`. PLAN gate, Normal depth (a
test that ships into users' sites; no High-row item). Seats: Codex and GLM 5.3 on melious, one
command (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`); fresh-eyes Sonnet in round 1.

| Round | Seats | Findings | Time, tokens |
|-------|-------|----------|--------------|
| 1 | Codex; fresh-eyes Sonnet. melious out of balance ("Insufficient balance … Available: 0"); no rerun owed | 1 BUG, 5 RISK, 4 NIT | Codex 289 s, 54,710; Sonnet 256 s, 117,283 |
| 2 | Codex alone (`--verify`); melious still out of balance | 2 RISK; P1-1 to P1-10 confirmed | Codex 236 s, 46,899 |
| 3 | Codex alone (`--verify`); melious still out of balance | 1 RISK (re-sorted: rare); P2-1, P2-2 confirmed | Codex 187 s, 25,186 |
| Final full read | a fresh Opus pass, which ran the draft's `usersNow()` and axe on rebuilt pages | 1 BUG, 1 RISK, 6 NIT | Opus 769 s, 168,207 |
| 4 | Codex alone (`--verify`, earned by `fixture-a11y,clip-tolerance`); melious still out of balance | 2 BUG; FR-1 to FR-8 confirmed | Codex 211 s, 54,254 |
| 5 | Codex alone (`--verify`, earned by `clip-tolerance`, cut: the overlap test runs only on a clipped axis); melious still out of balance | none; P4-1, P4-2 confirmed | Codex 220 s, 53,597 |
| Wording pass | Codex (`--wording-pass`, over the status rows changed after round 5) | 1 RISK: "passed" claimed before this pass was recorded; fixed by recording it here | Codex 819 s, 35,735 |

Total: 4 BUG (one each in round 1 and the final read, two in round 4), 9 RISK, 10 NIT. Round 3
found no BUG and no RISK that ordinary use produces, so the delta rounds stopped there (stop
condition a2); the final full read found a BUG and a silent wrong pass, which earned round 4;
round 4's BUG in the tolerance earned round 5, sent as a cut. Round 5 was clean. The status
rows changed after it went to the wording pass; the gate closed with it.

## Round 1

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| P1-1 | BUG | Codex | One run of the job cannot show every "before" result: it stops at its first surprise | fixed: a local runner runs the green check and each red case on its own | plan, "Before/after proof" |
| P1-2 | RISK | Sonnet | An inline ancestor reads `overflow: hidden` but has `clientWidth` 0, so a shown image would count as hidden | fixed: inline, contents and table-row displays skipped; clip box from the border box; new G6 | READ 1 "inline" |
| P1-3 | RISK | Sonnet | An older Chromium ignores `opacityProperty`; the fix would switch off silently. The reads were on 1.62.1, the starter ships 1.64.1 | fixed: a probe throws; reads re-run on 1.64.1 | READ 1 |
| P1-4 | RISK | Sonnet | An absolute pseudo-element escapes its host's ancestors; nothing tests the pseudo-element walk | fixed: no clip test for absolute or fixed pseudo-elements; new G7, R6 | plan, How 2 |
| P1-5 | RISK | Sonnet | `body { overflow-x: hidden }` goes to the viewport, so body does not clip | fixed: the walk stops below the body | plan, How 2 |
| P1-6 | RISK | Codex | False "hidden" not ruled out for nested contents hosts, scaled clips, `overflow-clip-margin`, pseudo-elements placed outside their host | fixed in part (nested hosts, scaled clips via the rect); the rest stated as the remaining false-hidden cases instead of "never" | READ 1 "scaled"; plan, "Where a new false hidden remains possible" |
| P1-7 | NIT | Sonnet | The mid-fade claim rests on the read alone | fixed: the plan says so | plan, How 1 |
| P1-8 | NIT | Sonnet | Per-axis logic and `overflow: clip` not exercised | fixed in part: G2 uses `overflow-x` only; G7, R6 use `clip` | plan, tests |
| P1-9 | NIT | Sonnet | A host's own `content-visibility: hidden` and its `::before` not stated | left: errs toward today's result | — |
| P1-10 | NIT | Sonnet | Helpers must live inside `usersNow()` | fixed: stated | plan, How |

## Round 2

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| P2-1 | RISK | Codex | `overflow-clip-margin` can draw past the border box: a false "hidden" | fixed: an ancestor whose margin is not `0px` is skipped | READ 2 |
| P2-2 | RISK | Codex | Site CSS (`div:empty { display: none }`) could hide the probe's child and let an unsupported browser pass | fixed: inline `all: initial` on both boxes; the child must read visible at opacity 1 and hidden at 0 | plan, How 1 |

## Round 3

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| P3-1 | RISK | Codex | An `!important` site rule can still hide the probe's baseline, and the error would blame Playwright | re-sorted: rare (an `!important` rule hiding plain empty divs), and it fails loudly. The two-line fix was made anyway: its own message for a failed baseline, and the plan's claim narrowed. The code goes through the DIFF gate | plan, How 1 |

## Final full read

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| FR-1 | BUG | Opus | G3's scroll box fails the starter's axe test (`scrollable-region-focusable`), so the green step's `npm test` goes red | fixed: `tabindex="0" role="region" aria-label="Gallery"`; the local runner runs `npm test` once | the reader's axe 4.14.0 run on that markup: `[]` |
| FR-2 | RISK | Opus | Fractional layout leaves the next slide 0.006px inside the clip, so it counts as shown: a silent wrong pass | fixed: an overlap under 1px counts as none; G2's box is 200.3px | reproduced by the reader with a `translateX(-33.3333%)` track |
| FR-3 | NIT | Opus | Plan says `<a>`, draft uses `<span>` for G6 | fixed | — |
| FR-4 | NIT | Opus | The clip-margin skip also applied to `overflow: hidden` | fixed: only for `clip` | — |
| FR-5 | NIT | Opus | A host clipping its own `::before` to nothing is not covered and not listed | fixed: listed | — |
| FR-6 | NIT | Opus | `body { opacity: 0 }` also trips the probe's first message | fixed: the message names both | reproduced by the reader |
| FR-7 | NIT | Opus | Nothing in CI runs the older-browser guard | fixed: R7 | — |
| FR-8 | NIT | Opus | Status table stale | fixed | — |

## Round 4

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| P4-1 | BUG | Codex | FR-2's tolerance also judged an axis nothing clips: an unclipped image 0.5px tall counted as hidden | fixed, a cut: only an axis some ancestor clips is judged; new green G8 | Codex reproduced it with the draft's expression |
| P4-2 | BUG | Codex | "only an `!important` rule" was still claimed in the plan and the spec comment | fixed: both name ancestor CSS too | — |

## Round 5

No BUG/RISK/NIT findings. Codex ran the helper on mocked boxes: an unclipped 200 × 0.5px image
stays shown, an x-only clip leaves height unjudged, a 0.3px x overlap counts as hidden; with the
axis gates removed, P4-1 came back.

## Evidence

The browser reads sent with every round (`--evidence`), run on the starter's own Playwright
1.64.1 (HeadlessChrome 156.0.8078.4), 2026-10-30:

READ 1: `checkVisibility({ opacityProperty: true, visibilityProperty: true })` gives false for an
image under `opacity: 0`, true under 0.01, true 50 ms into a fade from 0 (opacity 0.07), false
under `content-visibility: hidden`, false with its own `opacity: 0`, true for `visibility:
visible` inside a hidden parent. A `display: contents` element reads false, while its `::before`
is 50px wide. A pseudo-element can read `visible` in a hidden host. The absolute image's
`offsetParent` is its positioned wrapper. `overflow-x: hidden` gives `overflow-y: auto`. An
inline `<a style="overflow: hidden">` reads `overflow: hidden` with `clientWidth` 0. A
`scale(2)` box 50px wide has rect width 100 and `clientWidth` 50.

READ 2: computed `overflow-clip-margin` reads `0px` by default and for `0`, `30px` for 30px,
`content-box` for content-box.
