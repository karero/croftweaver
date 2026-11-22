# Trial result (2026-11-22): inconclusive, the plan is parked

Codex, 3 runs per cell, the plan's wording (after) against origin/main's (before).

The prompts sent were not archived. "Before" is `independent_review.sh` at origin/main 05ea4d13;
"after" is that script with the plan's wording, which this PR does not keep. Only T1 has before-runs.

| Case | What it tests | Result |
|---|---|---|
| T1 (as written) | rare case on a `- NIT (rare)` line, ordinary bug kept | **1/3 — failed**. The rare case (a stale temp file in `save_cart`) drew a RISK in two runs by an ordinary reading, so the fixture did not hold a rare case. |
| T1b (the one rewrite) | `receipt_header` raises only for an order `build_order` never makes, with the flag on | **0/3 — failed, and the fixture was flawed.** No run put the case on a `- NIT (rare):` line. All three listed the receipt branches under CLEAN for a non-empty order and none named the empty-items case; all three marked the `GIFT_NOTES` comment UNVERIFIABLE. The ordinary bug (`total_cents`) was found as BUG in 3/3. The Codex review of this record then showed an ordinary path to the exception: `build_order` keeps the caller's list, so a caller that clears it after the order is made leaves `items` empty. Two runs raised that aliasing as a RISK (items change while the total stays), so they found the defect behind it, not the empty-items exception itself. |
| T2, T3, T4, T5 | the three RISK kinds stay RISKs; a loud rare failure is still reported | passed |

T5r is T5's real-script variant, meant as the plan's real-diff case: the shipped
`scripts/check_buglog_rows.sh`, after-runs only. It was not scored against a bar. All three runs
reported ordinary defects of the script as BUG or RISK, and one run (3) added a `- NIT (rare):` line
(an unchecked `cd`). Whether its source trail holds a `re-sorted: rare` line was not checked.

T5 is the one case with a rare, loud failure and no ordinary reading: `- NIT (rare):` with a cost
sentence in 3/3 runs. T1 and T1b, the two cases built to test a rare case that Codex leaves out,
both turned out to have an ordinary reading, so neither shows that Codex fails to report one.

The plan is parked on the terms agreed before the rewrite: one rewrite, 2/3 or better, no second
rewrite. Read that as a rule kept, not as proof that the wording fails: the trial is inconclusive.

## A different approach?

None named, and no second rewrite under the agreed terms. The trial does not show the wording
harmful or unable to work: T2 to T5 passed. A later attempt would need a fixture whose rare case
has no ordinary reading, checked by running it and not only by a reviewer's reading. The working
rule that re-sorts a rare RISK as a follow-up stays the way to keep rare RISKs from earning rounds.
