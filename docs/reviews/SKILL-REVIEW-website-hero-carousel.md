# Review trail: the website-hero-carousel skill (docs/reviews/SKILL-PLAN-website-hero-carousel.md), 2026-10-24

Gate: High depth, Codex and GLM 5.3 (melious) both counted in every round. Plan: 3 rounds (see the plan's own
trail). Diff: 3 rounds below. Reviewers did not run the code; every fix was run in a fresh scaffold of the starter
(three configurations: button + instant, dots + fade, button + fade; the whole scaffold suite, 114 / 116 / 117
passed) and the tests that guard it were mutation-checked (a mutation removes the thing the test guards; the test
must fail).

## DIFF round 1 (Codex 362 s, GLM 5.3): 4 BUG, 2 RISK, NITs
| Finding | Disposition |
|---|---|
| BUG: first slide shown unconditionally; a failed first image stays on show | fixed in `hero-carousel.js` (`recover()`), see rounds 2 and 3 |
| RISK: an outgoing slide's link reachable during a fade | fixed: `inert` and `aria-hidden` set at once by the script; real Tab-key and accessibility-tree tests |
| BUG: the mid-fade pause/focus test never established a fade | fixed: waits for a frame with both opacities between 0.02 and 0.98, separate tests for Pause and focus |
| BUG: "not by Tab" never pressed Tab | fixed: real Tab (and Shift+Tab) traversal |
| RISK: the privacy guard was page-wide | reworked in rounds 2 and 3 |
| BUG: removal instructions left the import | fixed |
| plan text: budget script, WHAT-THE-SKILLS-RUN wording, JPEG count, an `intervalMs` message citing 2.2.2 | fixed |

## DIFF round 2 (verify): 2 BUG, 2 RISK, NITs
Recovery waited only for images already loaded (fixed: it waits for the first other image that arrives, with both
orderings tested); Tab-coverage not proven inside the fade (fixed: a ten-second fade for the test, focus and
tree read between two frames confirmed part-way); privacy compared with the page as loaded (fixed: compared with
the same page standing still); NITs on comments and wrap detection (fixed).

## DIFF round 3 (verify): 2 BUG, 2 RISK, NITs
| Finding | Disposition |
|---|---|
| BUG: the mid-fade test skipped only if no slide linked, then required slide 2 to link | fixed: the focus expectation depends on slide 2's `href` |
| BUG: alt texts with a shared 20-character prefix made the tree test contradict itself | fixed: full strings; the test skips when one alt text contains another |
| RISK: an absolute storage assertion stayed | removed; only the comparison with the standing run is kept |
| RISK (unverifiable): no browser evidence for the inert / aria-hidden exclusion | run: with both assignments removed, two tests fail (mutation check) |
| RISK: `schedule()` may restart a stopped rotation after a failure | `schedule()` starts the timer only if `running()`; comment added; the failure test runs under reduced motion |
| NIT: second ordering (a failure after the script started) untested | test added; mutation-checked |
| NITs: focus-stop assertion dropped, wrap detection, a table row's wording | fixed |

**Not re-verified by a fourth round:** the round-3 fixes (the two BUG fixes are test-logic; all were run in the
fresh scaffold, three configurations, and the mutation checks). A fourth round needs `--earned-by` and `--cut`
(the review rules) and is the maintainer's to order.

## Mutation checks run by hand (each: the test fails when the guarded thing is removed)
No shared grid; no `aspect-ratio`; no pill background; no thick border on the dot on show (this one SURVIVED the
first version of the forced-colours test, which compared pixels for any difference; it now compares the centres'
contrast and is killed); no fade `transition`; no `pointer-events` rule; no `inert` / `aria-hidden`; no `recover()`;
`recover()` that does not wait for an image still on its way; no `error` listener.

## Found on the way (a bug in the site this was taken from)
The first site's forced-colours test had the same weakness (it passed without the thick border); fixed there in a
separate commit (the same contrast comparison).
