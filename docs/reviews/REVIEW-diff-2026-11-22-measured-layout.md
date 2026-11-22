# Review trail: a layout claim gets a browser measurement, not a CSS quote (2026-11-22)

Change: one sentence in `skills/independent-review/SKILL.md`, step 2's run-once rule. Gate
20261122T172553Z-28729, DIFF, Normal depth: an instruction file agents load is never Light
(REVIEW-RULES). Codex alone (REVIEW-RULES), plus one fresh-eyes pass (Sonnet subagent) at round 1.

Why: on one of the owner's sites, reviewers repeated a 24px container padding quoted from
`public/css/style.css:138`, while a later `@supports` rule (lines 1132-1134) makes it 20px at
every width; that site's PR spent rounds on it. The owner, 2026-11-22: "Add it".

Result: clean at round 3. 3 rounds, 7 findings (0 BUG, 5 RISK, 2 NIT): 5 fixed, 2 NITs no change.

| Round | Seat | Finding | Disposition |
|---|---|---|---|
| 1 | Codex | none (two claims marked unverifiable: the override, the incident) | the override: READ 4 measures with and without the later rule |
| 1 | fresh-eyes | RISK: "such a claim" could point at the "cannot be run" sentence | fixed: the sentence moved before it and says "gets that run too" |
| 1 | fresh-eyes | RISK: "the widths it names" misses breakpoints either side | fixed: "on each side of any breakpoint that could change it" |
| 1 | fresh-eyes | RISK: what to measure and send is unsaid | fixed: "the computed value ... with the script and the browser's version" |
| 1 | fresh-eyes | RISK: "test instance, never production" fits a page poorly | fixed: "in a real browser on a local build or a preview" |
| 1 | fresh-eyes | NIT: names a later rule only, not specificity | no change: the evidence shows a later rule; not false as written |
| 1 | fresh-eyes | NIT: headless Chromium reports zero safe-area insets | no change, re-sorted: rare |
| 2 | Codex | RISK: a claim that names no width gets no widths | fixed: "a phone and a desktop width when it names none" |
| 3 | Codex | none | — |

Evidence sent each round: the site's review-trail lines at its PR head a837b8be; the stylesheet
lines on the site's main 2ceb6c6; headless Chromium 151.0.7922.34 measuring `.container` at 360,
719, 730, 759 and 1024 px: 20px padding at every width, and 24px from 730 px up once only the
`@supports` block is removed; the fixture and script whole. Not tested: other browsers, and
non-zero safe-area insets.

Cost: Codex 54,667 + 37,231 + 35,245 tokens; fresh-eyes 85,058; 212,201 in all.
