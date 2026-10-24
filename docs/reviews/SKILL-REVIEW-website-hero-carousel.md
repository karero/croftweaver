# Review trail: the website-hero-carousel skill (docs/reviews/SKILL-PLAN-website-hero-carousel.md), 2026-10-24

Gate: High depth, Codex and GLM 5.3 (melious) both counted in every round. Plan: 3 rounds (see the plan's own
trail). Diff: 9 rounds below, then a final full read and the wording pass. Reviewers did not run the code; every fix was run in a fresh scaffold of the starter
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

## Rounds 4 to 9 (2026-10-24, a second session; the branch merged with main twice, the merge links empty)
Each fix was run in a fresh copy of the starter in CI's three configurations (132, 134 and 135 passed after the
merges with main) and its guard mutation-checked. Codex at config.toml's effort, GLM 5.3 on melious.

| Round (head reviewed) | Earned by | Found | Disposition |
|---|---|---|---|
| 4 (`572844c0`, delta from `2ac6aff2`) | round 3's BUGs (mid-fade test, alt prefixes) and RISKs (privacy guard, recovery restart); cut: the mid-fade focus check runs only when slides 1 and 2 both link, then asserts both ways | 0 BUG, 3 RISK (both reviewers raised all three) | "focus stopped the rotation" ran three intervals, a full lap on three slides: now one interval, plus `aria-live="polite"`; the recovery-after-start test could not see a restart: two intervals checked; the tree tests matched alt text in `ariaSnapshot()` text: replaced (a cut) by counting `getByRole('img', { name, exact: true })`, the containment skip dropped (an alt with quotes and a double space passes) |
| 5 (`4f4aa44d`) | the three kinds of round 4; cut: `recover()` no longer calls `schedule()` | 0 BUG, 2 RISK, 1 NIT | Codex: the recovery guard could not fire when the last slide took over (always with two photos): redesigned in round 6; GLM's "recover() may be reached from the tick": refuted (it is called only from the image listeners and once at start); GLM's empty-alt NIT: refuted (the build refuses an empty alt) |
| 6 (`1886c8c9`) | recovery restart; cut: the test names its input (three photos, slide 2 arrives first, slide 3 loaded before the stop is checked) | 0 BUG, 1 RISK | a later slide repeating the second file would register a second route: re-sorted as rare (it fails loudly), fixed anyway in `aa0f2d42` (one route per file) |
| final full read (`aa0f2d42`, the whole change) | | 1 BUG, 2 RISK, 5 NIT | a fresh Claude Opus sub-agent (Kimi on ollama was out of its weekly quota, so no Kimi). BUG: README still said "four skills … the fourth travels with every site": rewritten for five. RISKs: the Pause text was 4.40:1 over pure white (pill alpha 0.6 → 0.65, 5.17:1; the spec now asks 4.5); `tick()` retried a failed photo for ever (new `after()` passes over it). NITs: a SKILL.md sentence, a CI case for an unknown `swap`, two "stays" checks after a mouse click (now `press()`): fixed; the dot-name label and the line's place in new-website: refuted |
| 7 (`8b13f2bf`) | the full read's README count, failed-photo skip, pill contrast | 1 BUG (Codex) | the new failed-photo test hard-coded slide 3 as shown, wrong for a page repeating the failed file: the expectation now comes from which slides share that file |
| 8 (`fcd14293`) | failed-photo test; cut: positions replaced by a rule from the files | 0 BUG, 3 RISK, 1 NIT | Codex: the expectation shared the route's matcher, so a route matching nothing passed: the test first proves the second photo failed and that the matcher marks it; GLM's async `getAttribute`, anchored regex and `g` flag: refuted (node-html-parser is synchronous; the RegExp has no anchors and no flags) |
| 9 (`8bca9ec8`), granted by the maintainer past round 8 ("Grant round 9", 2026-10-24) | failed-photo test | 0 BUG, 0 RISK, 1 NIT | a comment claimed more than its check proves: reworded |

Trend, BUG/RISK by round: r4 0/3, r5 0/1 (one more refuted), r6 0/1 (rare), full read 1/2, r7 1/0, r8 0/1 (two more
refuted), r9 0/0. No BUG open.

**Cost, rounds 4 to 9 and the full read** (the `timings:` lines; the cost log holds no gate for this worktree):
Codex 335,801 tokens, GLM 5.3 105,571, the Opus full read 149,298; about 590,000 in all.

## Mutation checks run by hand (each: the test fails when the guarded thing is removed)
No shared grid; no `aspect-ratio`; no pill background; no thick border on the dot on show (this one SURVIVED the
first version of the forced-colours test, which compared pixels for any difference; it now compares the centres'
contrast and is killed); no fade `transition`; no `pointer-events` rule; no `inert` / `aria-hidden`; no `recover()`;
`recover()` that does not wait for an image still on its way; no `error` listener. Rounds 4 to 9 added: no `inert`
(the mid-fade focus check); no stop on keyboard focus; a recovery that starts a timer whatever the state (three runs
out of three); no `aria-hidden` (both tree tests); `tick()` back to the next slide only (the failed-photo test); the
pill at alpha 0.6 (the contrast test); a route that lets the failed photo through (the failed-photo test). Each
failed its test. An unknown `swap` was checked by hand to stop the build with the CI step's message.

## Found on the way (a bug in the site this was taken from)
The first site's forced-colours test had the same weakness (it passed without the thick border); fixed there in a
separate commit (the same contrast comparison).
