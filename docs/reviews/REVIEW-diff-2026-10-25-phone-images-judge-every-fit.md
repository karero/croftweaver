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
