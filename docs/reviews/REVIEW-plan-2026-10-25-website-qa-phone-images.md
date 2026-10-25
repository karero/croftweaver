# Review trail: SKILL-PLAN-website-qa-phone-images.md (PLAN gate, Normal)

Gate `20261025T072914Z-87967`. The plan SHAs below were on the local branch before it was squashed, unpushed, to keep
client names out of the repo's history; sites are named by letter, as in the plan. Seats: Codex (gpt-6.1-sol), melious (glm-5.3), fresh-eyes (Claude Sonnet, round 1 only).

## Round 1 — plan at 9010a818

`reviewers: codex OK, melious OK`; `timings: codex 518s (90174 tokens), melious 193s (18230 tokens)`; fresh-eyes 75 s, about 101k tokens.
24 findings: 4 BUG, 12 RISK, 8 NIT. All fixed in the next revision unless noted.

| # | Seat | Kind | Finding | Disposition |
|---|------|------|---------|-------------|
| 1 | codex | BUG | "within 3 points of a target" undefined; which metric picks the median run | Fixed: always 5 runs, median by performance score |
| 2 | codex | BUG | the starter does hold a raster (`og/default.jpg`) | Fixed: "renders no raster images"; the OG image is only named in a meta tag |
| 3 | fresh | BUG | `naturalWidth` is scaled by a `w` srcset | Fixed: real width from decoding the file |
| 4 | fresh | BUG | CI fixtures unspecified: PNG would fail `images.spec.ts`; which suites run per case | Fixed: noise WebP via sharp, full attributes; green runs `npm test`, red runs the spec alone and checks the failing test and file name |
| 5 | codex | RISK | preview has no analytics, so it can pass while production does not | Fixed: production run counts for "done"; preview for comparing |
| 6 | codex | RISK | a file swapped out during scrolling looks unused | Fixed: users recorded at every scroll step; a swap case in the green fixture |
| 7 | codex | RISK | srcset "smallest sharp file" rule unsupported | Fixed: recipe uses a fresh context per width; named as a site recipe with a working, passing example (site A's repo `main`) |
| 8 | glm, fresh | RISK | "not shown" finder misses mask/border/list/content/poster/canvas | Fixed: finder widened; the rule narrowed to preloaded images; canvas named under Judgment |
| 9 | glm | RISK | flat-colour fixtures fall under the 4 KiB floor, red cases vacuous | Fixed: random-noise fixtures, plus a just-under-floor case |
| 10 | glm | RISK | `CHROME_PATH` to Playwright's Chromium unproven | Refuted with evidence: the recorded run used exactly that; command in the evidence file |
| 11 | fresh | RISK | one jump to the bottom misses lazy images | Fixed: scroll in viewport steps, wait for `complete` and network idle |
| 12 | fresh | RISK | zero-width users; a file used at two sizes | Fixed: widest non-zero box; zero-only users listed |
| 13 | fresh | RISK | background-size values other than cover undefined | Fixed: cover drawn width, all else box width, layers separately |
| 14 | fresh | RISK | `<picture>`/poster/other users report as unused | Fixed with #8 |
| 15 | fresh | RISK | run conditions: context, isMobile, listener order, cache, preload match | Fixed: fresh context per page, listener before goto, match by content type |
| 16 | fresh | RISK | file size source undefined | Fixed: `response.body()` |
| 17 | glm, fresh | NIT | "0 judged" only printed | Fixed: every downloaded raster must be judged or listed with a reason, else fail |
| 18 | glm | NIT | pseudo-element and repeat branches untested | Fixed: `::before` red case, repeating green case |
| 19 | glm | NIT | 1.1 slack's bound not stated | Fixed: covers up to 453 CSS px |
| 20 | glm | NIT | "two of four" against a five-row table | Fixed: "two of the four other sites" |
| 21 | fresh | NIT | "same estimate" as Lighthouse overstates | Fixed: "modelled on" |
| 22 | fresh | NIT | site A's third test is site-specific | Fixed: named as a recipe example, not the shipped test |
| 23 | fresh | NIT | median by what; scratch install leaves package.json alone | Fixed in #1 and step 1 |
| 24 | codex | NIT (unverifiable table) | step 0, Lighthouse source, compression and PSI claims lack retained evidence | Fixed: `EVIDENCE-website-qa-phone-images.md`. Checking compression found the plan wrong: `astro preview` gzips (only `python -m http.server` does not); text corrected |

Host note: codex's "412px cannot see preload drift near 710px" is taken into section 3's hero recipe.

## Round 2 — plan at a2ffa018 (verification, Codex at medium)

`reviewers: codex OK, melious OK`. 9 findings: 1 BUG, 5 RISK, 3 NIT.

| # | Seat | Kind | Finding | Disposition |
|---|------|------|---------|-------------|
| 25 | codex | BUG | the step 0 table's counts disagree with the retained evidence (site C 18/4, site D 35/24) | Fixed: table and predictions from the retained run; the plan says the earlier run differed (lazy loading on live sites) and adds the YouTube thumbnail it found |
| 26 | codex, glm | RISK | #6 partly fixed: no swap-out fixture; users missed after the last step | Fixed: one more snapshot after the final wait; green fixture shows a preloaded file then swaps it out. Shown-and-removed within one pause: re-sorted rare, named under Judgment |
| 27 | codex | RISK | srcset pick rule still unsupported | Fixed: the recipe asserts the observed pick at ten pairs; it passed in site A's repo PR 130's CI (`test SUCCESS`, merge `d5bace7`) |
| 28 | codex | RISK | a right-sized repeating fixture cannot prove the exemption | Fixed: oversized repeating background, asserted listed with reason |
| 29 | glm | RISK | without isMobile/hasTouch, hover/pointer media differ from a phone | Fixed: `isMobile: true, hasTouch: true`, as Lighthouse and the step 0 run |
| 30 | glm | NIT | `cursor`/`shape-outside` users not seen | Fixed: added to the list |
| 31 | glm | NIT | multi-layer and zero-size paths lack fixtures | Fixed: both in the green case |
| 32 | glm | NIT | "any phone" overstates for narrow phones | Fixed: the line holds for phones 412px and wider |
| — | codex | note, not counted (unverifiable list) | runtime behaviour of Chromium, Lighthouse, servers, sharp | Left for the build: these are what the CI fixtures and the before/after site A run check; the evidence file holds what was run |

## Round 3 — plan at 819caa33 (verification)

`reviewers: codex OK, melious FAILED (error mid-stream (HTTP 200)), ollama-cloud FAILED (exit 1; quota/rate limit)`; melious rerun alone: FAILED again, same error. 1 finding.

| # | Seat | Kind | Finding | Disposition |
|---|------|------|---------|-------------|
| 34 | codex | RISK (earning) | #27 again: the srcset pick rule has no retained per-pair results | Tested, not argued (raised twice): the sweep rerun against production, Chromium 151, 10 of 10 pairs as expected, kept in the evidence file. Cut, not patched: the recipe no longer states a general rule, only the listed pairs; the "fix sizes or report" sentence of 4465500a removed. Earns round 4 (`--earned-by srcset-pick`) |

## Round 4 — plan at 217e22da (verification; earned by #34, `--earned-by srcset-pick`, cut: the general pick rule)

`reviewers: codex OK, melious FAILED (error mid-stream (HTTP 200)), ollama-cloud FAILED (exit 1; quota/rate limit)`; `timings: codex 111s (49310 tokens)`.
Codex: no findings; it recounted the evidence (7/1/0/18/35 rasters, 24 site D tiles) and checked the ten sweep pairs. Rounds 3 and 4 ran on one seat: the second seat failed both times (melious mid-stream three times, ollama out of quota). Last two rounds not re-verified by a second model.

## Final full read — plan at bd4afce2 (Claude Opus, fresh; Kimi on ollama unavailable: out of quota)

About 120k tokens, 166 s. 10 findings: 2 BUG, 3 RISK, 5 NIT. Both BUGs are substantive and earn round 5.

| # | Kind | Finding | Disposition |
|---|------|---------|-------------|
| 35 | BUG | the preload rule, read from `<link>` tags, fails site A `main`'s desktop-only preload (`index.astro:53`, `media="(min-width: 720px)"`) | Confirmed and fixed: only a preload that was downloaded counts; green case for a non-matching `media` |
| 36 | BUG | the "not accounted for" guard has no red case | Fixed: red case, a raster loaded by `new Image()` and never attached |
| 37 | RISK | a new fixture page fails `orphans`, `llms-coverage`, `seo` | Fixed: images go into `src/pages/index.astro`, as other jobs do |
| 38 | RISK | step 1 lacks the command; `--headless=new`; where `node -e` runs | Fixed: exact command; `@playwright/test` import checked in site A's repo, prints the Chrome for Testing path |
| 39 | RISK | analytics "defer" contradicts the starter's `async` | Fixed: a fix for a site that needs it; the starter and the existing bullet stay; spec named as site A's |
| 40 | NIT | logos are 3–14 KB | Fixed |
| 41 | NIT | the 26 KB figure not in evidence | Fixed: widths, bytes and arithmetic added to the evidence file |
| 42 | NIT | "skips CSS images outright" overstates; 12 KiB application not quoted | Fixed: "does not judge CSS images by size"; lines 207–208 quoted |
| 43 | NIT | the skill asks for desktop too | Fixed: one `--preset=desktop` run as well; targets judged on mobile |
| 44 | NIT | hero-carousel makes flat JPEGs; under-floor case listed as red | Fixed both |

## Round 5 — plan at the final-read fixes (verification; earned by #35, #36, `--earned-by preload-rule,accounting-guard`)

`reviewers: codex OK, melious OK`; `timings: codex 169s (85587 tokens), melious 130s (22119 tokens)`. Codex: no findings. melious: 3 NIT, no BUG or RISK, so the rounds end (stop condition a2).

| # | Seat | Kind | Finding | Disposition |
|---|------|------|---------|-------------|
| 45 | glm | NIT | `npx lighthouse` location unstated; in the site folder npx would fetch the latest | Fixed: runs in the scratch folder (`locally_verified`, closing edit not externally re-verified) |
| 46 | glm | NIT | 26 KB not named in the verified list; 1900px file attributed to post-PR `origin/main` | Fixed: bytes and saving named; the file is still the desktop hero (`locally_verified`) |
| 47 | glm | NIT | "(Lighthouse's default)" reads as 5 runs being default | Fixed: "(the default preset)" (`locally_verified`) |

## Wording pass — the round 5 NIT edits (Codex alone, `--seat codex`)

`reviewers: codex OK`; `timings: codex 145s (44936 tokens)`. No findings.

## Close

5 rounds plus a final full read; 47 findings: 7 BUG, 21 RISK, 19 NIT (rows 1–47; the round 2 "unverifiable" note not counted). Every BUG fixed, no RISK waived, none open. Rounds 3 and 4 ran on Codex alone (the second seat failed); round 5 had both seats.
Tokens logged: Codex 381,958 over six runs; melious 65,557 over three; fresh-eyes about 101k and the final read about 120k (host agents). About 670k in all; the fixes and the host's own work not counted.
