# Review trail: diff, the phone-images test judges "hidden" through an image's ancestors

PR: karero/croftweaver#454. DIFF gate, Normal depth: the change edits a test that ships into
users' sites (never Light). Seats: Codex and GLM 5.3 on melious, one command
(`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`); fresh-eyes Sonnet in round 1. Plan and its gate:
`PLAN-phone-images-hidden-through-ancestors.md`, `REVIEW-plan-2026-10-30-phone-images-hidden-through-ancestors.md`.

| Round | Head | Seats | Findings | Time, tokens |
|-------|------|-------|----------|--------------|
| 1 | 292b1d27 (from c24704de) | Codex; fresh-eyes Sonnet. melious out of balance ("Insufficient balance … Available: 0"); no rerun owed | 1 BUG, 2 RISK, 2 NIT | Codex 177 s, 65,426; Sonnet 116 s, 112,740 |
| 2 | e82c6c2c (`--verify`, delta from 292b1d27) | Codex alone; melious still out of balance | 1 RISK, 1 NIT; D1-1 to D1-5 confirmed | Codex 142 s, 43,682 |
| 3 | d196172e (`--verify`, delta from e82c6c2c) | Codex alone; melious still out of balance | none; D2-1, D2-2 confirmed | Codex 87 s, 39,187 |

Total: 1 BUG, 3 RISK, 3 NIT, all fixed. Round 3 was clean.

## Round 1

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| D1-1 | BUG | Codex | A 200 × 0.5px image wholly inside a clip counted as hidden: the 1px rule took its whole height | fixed: an axis shows when the part left is at least the smaller of 1px and the box's own size; G8 moved inside a clip | mutation back to `>= 1` fails the green check on `thin.webp` |
| D1-2 | RISK | Codex | `offsetParent` passes over a transformed containing block, and a fixed box under a transform can be clipped: hidden downloads could pass | fixed: the walk finds the containing block itself; new G9, R8, R9 | all three behave as expected in the local run |
| D1-3 | RISK | Sonnet | G6 could not fail if inline boxes counted as clips: the span's rect overlaps the image by the text's ascent | fixed: the span gets `font-size: 0` (its rect then has no height) | mutation dropping `inline` fails the green check on `inl.webp` |
| D1-4 | NIT | Sonnet | No case for `position: fixed` or the `overflow-clip-margin` skip | fixed: G9, R9 (fixed); G10 in round 2 (margin) | — |
| D1-5 | NIT | Sonnet | Workflow comment broken mid-sentence | fixed | — |

## Round 2

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| D2-1 | RISK | Codex | The separate `translate`, `rotate` and `scale` properties also make a containing block | fixed: all four count; R9 uses `translate: 0px`, R8 `transform` | each moves a fixed child into the box in Chromium 156 |
| D2-2 | NIT | Codex | No case pins the clip-margin skip | fixed: G10 | mutation dropping the skip fails the green check on `margin.webp` |

## Local runs

The job's own step scripts, extracted from the workflow and run with `exit 1` turned off so every
case reports, on the starter's Playwright 1.64.1, at the final head: the green line
`26 judged by width; hidden and under 4 KiB: /fx/hidden.webp, /fx/off.webp, /fx/wait.webp; not judged: /fx/border.webp (border-image-source)`,
all 26 red cases red, `npm test` 116 passed and 1 skipped, `astro check` 0 errors. With the spec
from `main` on the same page (before G9, G10, R8 and R9 were added): 26 judged files and only
`hidden.webp` listed, so the green check fails, and every new red case of the time stayed green.
