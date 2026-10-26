# DIFF review — branch fix/phone-images-judge-every-fit: phone-images.spec.ts judges every fit

Gate: Normal (a test that ships in every new site, its CI job and a SKILL.md paragraph; a test
copied into users' projects is never Light). Seats: Codex, melious (glm-5.3), fresh-eyes (Claude
Sonnet, round 1). Artifact: `git diff origin/main...HEAD -- . ':(exclude)docs/reviews/'`.

Why: the review of a site that copied this spec (its PR for phone copies of eight blog photos)
found one BUG, one RISK and three NITs in the spec itself. The owner deferred them here so every
site gets the fix.

| # | From | Kind | Finding | Fix in this branch |
|---|------|------|---------|--------------------|
| 1 | codex | BUG | the header says every raster is judged, but `object-fit: scale-down`/`none`, a `calc()` background-size and a file used only by mask-image and similar were listed as "not judged" and passed | scale-down and none worked out from the file's size and the box; calc() and % resolved in the page by a probe box; mask-image judged by mask-size; list markers and content images by their box or own size; border images, cursors and shape-outside named, not judged (round 1, #5); anything still not worked out fails. Red cases: scale-down, calc(), mask |
| 2 | codex | RISK | the saving estimate by pixel area can overstate the real saving | kept, called an estimate in the message, the comment and website-qa; at a 4 KiB floor it can only fail a file that would save a little less |
| 3 | glm | NIT | the preload list misses `rel~=preload` and `imagesrcset` | `link[rel~="preload" i][as="image" i]`, href and every imagesrcset candidate; red case |
| 4 | glm | NIT | a failed body read overwrites a size already read | a failed read marks the file only when no read worked |
| 5 | glm | NIT | posters are judged as `contain` | the video's computed object-fit (Chromium's default for video is `contain`); green case with `cover` that the old code failed |

## Before round 1

 `make check` green; the CI job's steps run locally as written (green page 16
judged, whole suite 112 passed, every red case red); main's spec run on the new fixture (it fails
the cover poster and misses the scale-down, calc and mask cases). Evidence file:
`docs/reviews/EVIDENCE-phone-images-judge-every-fit.md`.

## Round 1 — 0decf01a

`reviewers: codex OK, melious OK`; codex 164 s / 60,811 tokens, melious 524 s / 49,090 tokens,
fresh-eyes (Sonnet) about 111k tokens. 0 BUG, 6 RISK, 9 NIT (some overlap, each in its own row).

| # | Seat | Kind | Finding | Disposition |
|---|------|------|---------|-------------|
| 1 | fresh | RISK | `none`, and the list-marker, cursor and content paths, are counted as judged but can never fail | Fixed for `none`: the width its box shows, `min(fw, box)`; red case (a 2000px file in a 200px box). Mutation (`none` at full size) caught. List markers and pseudo-element content images are drawn at the file's own size (measured: a 600x400 marker and `::before` image draw at 600x400), so they can only fail as hidden; cursors moved to "named" (#5) |
| 2 | fresh, codex, glm | RISK / NIT | the probe inherits site CSS (`div { max-width }`) and sizes `%` against the border box, not the padding box | Fixed: `all: initial` on the probe and its child; red case with a `:global()` rule squeezing the probe's child to 60px still gives 190px. Mutation (no `all: initial`) caught: widths came out 120px. The padding box: re-sorted, rare and lenient (a bordered box comes out a little wide); said in the comment |
| 3 | fresh | RISK | the probe is added and removed at each stop, which a site's MutationObserver can see | Re-sorted: rare (hidden probe, no starter script watches the body); BUGLOG row |
| 4 | glm | RISK | `em` and container units inside `calc()` resolve against the probe's font, not the element's | Refuted by measurement: Chromium's computed style already turns them into px (`calc(50% + 2em)` at 20px reads `calc(50% + 40px)`; `10cqw` in a 300px container reads `30px`) |
| 5 | glm, codex | RISK / NIT | border images are not drawn across the box; a cursor's drawn size is unsupported | Fixed by narrowing the claim: a file used only as a border image, cursor or shape-outside is named in the log ("not judged"), stated in the header and in website-qa; green case for a border image |
| 6 | glm | NIT | shape-outside dropped silently: a file used only there fails as not shown | Fixed with #5 |
| 7 | fresh | NIT | the comment says content images draw at own size, the code fills the box on a non-pseudo element | Fixed: the comment names both |
| 8 | fresh | NIT | an `imagesrcset` URL with a comma is cut | Re-sorted: rare, and the file still fails (with the "downloaded" message); BUGLOG row |
| 9 | fresh | NIT | the unknown-size message omits calc() | Fixed |
| 10 | glm | NIT | the green check is end-anchored, so a second small file fails with a general message | Kept on purpose: it asserts the whole line, which is printed just above the error |
| 11 | glm | NIT | the "cannot work out" failure has no red case | Kept: a one-line loud refusal for a size no fixture can produce (every computed size the probe cannot take is one the browser rejects); said here |
| 12 | fresh, codex | NIT | no red case for the cover poster | Fixed: red case (cover removed, the poster is drawn at 100px). Mutation (poster hard-coded `contain`) caught on the green page |
| 13 | fresh, glm | unverifiable | Chromium on CI's Linux may serialize computed styles differently | Settled by the PR's own `phone-images-test` run |

Checks after the fixes: the job's steps run locally again (16 judged; whole suite 112 passed; 16
red cases red), three mutations caught, `make check` green.

## Round 2 — verify, delta 0decf01a..ce84378c

`reviewers: codex OK, melious FAILED, ollama-cloud FAILED`: melious said "Insufficient balance
for request ... Available: 0"; the ollama stand-in hit its weekly usage limit. A degraded round:
Codex alone (217 s / 54,373 tokens). It confirmed fixes #1, #5–7, #9, #10 and #12 and raised 2
RISKs, both re-raises of #2. The PR's `phone-images-test` job passed on CI's Linux Chromium at
ce84378c, which settles #13.

| # | Seat | Kind | Finding | Disposition |
|---|------|------|---------|-------------|
| 14 | codex | RISK | the probe's rect is skewed by a transform on an ancestor; a site `!important` rule still reaches it | Fixed for transforms: the probe's computed width/height is read, not its rect. `!important` on every div: re-sorted, rare (one seat) |
| 15 | codex | RISK | `%` sizes resolved against the border box, not the positioning area (re-raise of #2, which two seats raised in round 1, so it counts) | Fixed: each layer's area comes from its `background-origin` / `mask-origin` (border, padding or content box); a pseudo-element's border box is built from its used size. Red case: a 20px border on a 200px border-box box gives `calc(100% - 10px)` = 150px. Mutation (area = border box) caught: it reads 190px |

## Round 3 — verify, delta ce84378c..1797dc83

`reviewers: codex OK, melious FAILED, ollama-cloud FAILED` (the same balance and weekly limit as
round 2). Codex alone (113 s / 49,081 tokens) confirmed #14 and #15 landed and raised 2 RISKs,
both re-raises of rare cases with no new evidence of ordinary use.

| # | Seat | Kind | Finding | Disposition |
|---|------|------|---------|-------------|
| 16 | codex | RISK | a site `!important` rule still reaches the probe (re-raise of #14) | Re-sorted: rare (one seat); BUGLOG row |
| 17 | codex | RISK | on a transformed element, the rect is scaled while borders and padding are not | Re-sorted: rare (a transform, borders and a `%` background size on one element); BUGLOG row |

Gate state: 3 rounds, 17 findings (0 BUG, 10 RISK, 7 NIT), no BUG open. Rounds 2 and 3 are
degraded: Codex only, because melious had no credit and ollama had hit its weekly limit. Round 1
had the full pair and fresh-eyes.

## Wording pass — Codex, the prose in website-qa and BUGLOG (88 s / 46,472 tokens)

Two wording errors, both fixed: "every raster it downloads" now reads "every raster the page
itself downloads (not those inside an iframe)" (the spec reads only the main frame); and a file
used only as a border image, cursor or shape-outside is "not judged by width" rather than "not
judged", since it still fails when hidden at 4 KiB or more, or when it cannot be decoded. Same
wording in the spec's header.
