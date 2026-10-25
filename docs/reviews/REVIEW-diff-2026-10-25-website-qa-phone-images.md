# DIFF review — branch plan/website-qa-phone-images: phone-images.spec.ts, its CI job, website-qa Performance

Gate: Normal (a test that ships in every site, a CI job and a SKILL.md; none of it is Light).
Seats: Codex, melious (glm-5.3), fresh-eyes (Claude Sonnet, round 1). Artifact: `git diff origin/main...HEAD -- . ':(exclude)docs/reviews/'`.

Before round 1: `make check` green; the spec green on the starter (0 judged), the CI job's steps run locally as written (green page, whole suite 112 passed and 1 skipped, every red case red); mutations of the spec each caught by a fixture case; the spec run on site A before and after its hero fix (red on the 1900px hero, about 25 KB to save; green after).

## Round 1 — 5fd0c36b

`reviewers: codex OK, melious OK`; fresh-eyes about 110k tokens. 23 findings: 5 BUG, 11 RISK, 7 NIT (some overlap, each kept in its own row).

| # | Seat | Kind | Finding | Disposition |
|---|------|------|---------|-------------|
| 1 | fresh | BUG | smooth scrolling (the starter sets it) can stop the loop short of the end | Fixed: `behavior: 'instant'`, and the loop now ends only when the bottom is reached. Tested: smooth scrolling with the old loop still reached the end on the fixture (the final wait lets it finish), so this is a guard, not a seen failure |
| 2 | fresh | BUG | "Done means" asks for a production number before launch | Fixed: the `main` preview before launch, production after; single-stage sites measure production after the first upload |
| 3 | codex | BUG | `background-size` ignored: a file drawn at 50px is judged at the box width | Fixed: the drawn width from cover, contain, lengths, percentages and auto; red case (a 600px file drawn at 50px). Mutation (sizes ignored) caught |
| 4 | codex | BUG | the URL parser cuts `url("/photo(1).webp")` at `)` | Fixed: computed styles always write `url("...")`, now parsed with escapes; the layer splitter skips quoted text; green case `paren(1).webp`. Mutation (old parser) caught |
| 5 | codex | BUG | the page height is read once; a page that grows is not scrolled to its end | Fixed: the end is checked at every stop, at most 200 screens (more fails loudly); red case (an oversized image in content added at the end, 8000px down). Mutation (height read once) caught |
| 6 | fresh | RISK | `background-repeat` defaults to `repeat`, so ordinary backgrounds were skipped as "repeating" | Fixed: repeat is no longer a reason to skip; a tile is judged at the width it is drawn |
| 7 | fresh | RISK | `image-set()` names several files; only the first counted | Fixed: every URL of a layer counts; green case. Mutation (first URL only) caught |
| 8 | fresh | RISK | an eager image hidden at phone width passes | Fixed: one of 4 KiB or more fails ("downloaded but hidden"), smaller ones are listed; red and green cases. Mutation caught |
| 9 | fresh | RISK | `networkidle` hangs on pages that poll | Fixed: at most 5 s, and the output says when the network never went quiet |
| 10 | fresh | RISK | `npm install` without `npm init` writes into the site; one command, no five-run loop or median; Node version | Fixed: `npm init -y`, a five-run loop and a median one-liner (run once as written, see below); Lighthouse 13.5 needs Node >= 22.19, the starter's floor is `^22.23.4 \|\| ^24.22.1 \|\| >=26.12.1` |
| 11 | fresh | RISK | a single-stage site has no preview | Fixed with #2 |
| 12 | fresh | RISK | `background-size` under or over 100% judged wrong | Fixed with #3 |
| 13 | codex | RISK | the byte saving is estimated, not measured | Refuted: the same estimate Lighthouse uses (wasted pixel share × bytes, `ImageDelivery.js`, quoted in the evidence file); a rule of thumb by design, called "modelled on" in the plan |
| 14 | glm | RISK | the job leans on the line reporter's format | Refuted with evidence: the job's steps ran locally as written and every check matched; the tagline job reads the same format |
| 15 | glm | RISK | `sharp` is not installed explicitly | Refuted: the starter's install provides it (the fixtures were made with it here), as the hero-carousel job already relies on; a comment in the step says so |
| 16 | glm | RISK | `hasTouch` giving phone media queries is assumed | Fixed: the test asserts `(pointer: coarse)` and `(hover: none)`; both matched here |
| 17 | fresh | NIT | the new job sat between `template-tests-ok` and its comment | Fixed: moved above the comment |
| 18 | fresh | NIT | relying on hoisted `sharp` | See #15 |
| 19 | fresh | NIT | `printf … \| grep -q` under pipefail can exit 141 | Fixed: here-strings and `[[ … ]]` |
| 20 | fresh | NIT | the context closes only on success | Fixed: `try`/`finally` |
| 21 | fresh | NIT | a perl edit hits the first match only | Fixed: anchored to a line holding only `<script is:inline>`; the grep after it proves the edit landed |
| 22 | glm | NIT | the fixed 150 ms settle and growing pages | Fixed with #5; a final snapshot follows the image and network waits |
| 23 | glm | NIT | one grep had no error message | Fixed |

Checks after the round 1 fixes: the regenerated job's three steps run locally as written under `bash -eo pipefail` (9 judged on the green page, whole suite 112 passed and 1 skipped, all seven red cases red); the skill's steps 1 and 2 run verbatim in a fresh scratch folder against https://croftweaver.com/ (five runs, median printed: `100 1.0 s 1.7 s`).
Site A again with the revised spec, on a quiet machine (50 pages in about 21 s): before its hero fix, red on `/images/hero-bg.webp is 1900px wide, shown at 426px … saves about 23 KB`; on its `main`, the hero passes and the only failures are 8 blog photos (1280–1600px files shown at 372px), real findings for that site; no "hidden" or "nothing shows it" result on any of its 50 pages.

## Round 2 — e579ca1e (verification, Codex at medium)

`reviewers: codex OK, melious OK`. 7 findings: 2 BUG, 3 RISK, 2 NIT.

| # | Seat | Kind | Finding | Disposition |
|---|------|------|---------|-------------|
| 24 | codex | BUG | `decodeURI` throws on a file named with `%` | Fixed: names are reported as served, undecoded |
| 25 | codex | BUG | #5 partly fixed: a page that grows during the final waits is not scrolled again | Fixed: after the waits the end is checked again and scrolling goes on if the page grew; the grow fixture now adds its content 400 ms late. Mutation (stop at the first end) caught |
| 26 | codex | RISK | a `calc()` background-size gives NaN and passes silently | Fixed: a size not worked out lists the file with the value ("size not worked out: calc(100% - 10px) auto", asserted on the green page); lengths are read only when they are plain px or % |
| 27 | codex | RISK | `visibility: hidden` with a box escapes the hidden rule | Fixed: visibility is recorded and a hidden user counts as not shown; red case. Mutation (visibility ignored) caught |
| 28 | glm | RISK | `object-fit: none` and `scale-down` judged at the box | Fixed: none at the file's width, scale-down at the smaller of it and contain. No fixture: both only make a file look larger or equal, never pass a wrong one; named here |
| 29 | glm | NIT | `failed_test_is` still pipes into `grep -q` | Fixed: captured first, matched with `[[ … ]]` |
| 30 | glm | NIT | the new proof greps had no error message | Fixed: one `edit` helper makes each change and names the edit that did not land |

Checks after the fixes: the job's steps run locally as written (10 judged on the green page, `calc.webp` and `hidden.webp` listed with their reasons, whole suite 112 passed and 1 skipped, 8 red cases red); site A as before (red on the old hero, the same 8 blog photos on `main`, nothing else).
