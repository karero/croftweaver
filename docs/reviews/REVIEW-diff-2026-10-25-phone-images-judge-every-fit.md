# DIFF review — branch fix/phone-images-judge-every-fit: phone-images.spec.ts judges every fit

Gate: Normal (a test that ships in every new site, its CI job and a SKILL.md paragraph; a test
copied into users' projects is never Light). Seats: Codex, melious (glm-5.3), fresh-eyes (Claude
Sonnet, round 1). Artifact: `git diff origin/main...HEAD -- . ':(exclude)docs/reviews/'`.

Why: the review of a site that copied this spec (its PR for phone copies of eight blog photos)
found one BUG, one RISK and three NITs in the spec itself. The owner deferred them here so every
site gets the fix.

| # | From | Kind | Finding | Fix in this branch |
|---|------|------|---------|--------------------|
| 1 | codex | BUG | the header says every raster is judged, but `object-fit: scale-down`/`none`, a `calc()` background-size and a file used only by mask-image and similar were listed as "not judged" and passed | scale-down and none worked out from the file's size and the box; calc() and % resolved in the page by a probe box; mask-image judged by mask-size; border-image, list-style-image, cursor and content judged by their box or own size; shape-outside dropped (it paints nothing); anything still not worked out fails. Red cases: scale-down, calc(), mask |
| 2 | codex | RISK | the saving estimate by pixel area can overstate the real saving | kept, called an estimate in the message, the comment and website-qa; at a 4 KiB floor it can only fail a file that would save a little less |
| 3 | glm | NIT | the preload list misses `rel~=preload` and `imagesrcset` | `link[rel~="preload" i][as="image" i]`, href and every imagesrcset candidate; red case |
| 4 | glm | NIT | a failed body read overwrites a size already read | a failed read marks the file only when no read worked |
| 5 | glm | NIT | posters are judged as `contain` | the video's computed object-fit (Chromium's default for video is `contain`); green case with `cover` that the old code failed |

## Round 1

Before round 1: `make check` green; the CI job's steps run locally as written (green page 16
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
