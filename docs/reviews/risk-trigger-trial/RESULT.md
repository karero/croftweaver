# Trial result (2026-11-22): the plan is dropped as written

Codex, 3 runs per cell, the plan's wording (after) against origin/main's (before).

| Case | What it tests | Result |
|---|---|---|
| T1 (as written) | rare case on a `- NIT (rare)` line, ordinary bug kept | **1/3 — failed**. The rare case (a stale temp file in `save_cart`) drew a RISK in two runs by an ordinary reading, so the fixture did not hold a rare case. |
| T1b (the one rewrite) | `receipt_header` raises only for an order `build_order` never makes, with the flag on | **0/3 — failed**. No run put the case on a `- NIT (rare):` line. Two runs listed it under CLEAN, one under CLEAN and UNVERIFIABLE; one did not mention it. The ordinary bug (`total_cents`) was found as BUG in 3/3. |
| T2, T3, T4, T5 | the three RISK kinds stay RISKs; a loud rare failure is still reported | passed |

The wording did what it should for the three kinds that stay RISKs. It did not make Codex report
a rare case it judged harmless: asked to list every rare case, it left it out or called it clean.
Terms agreed before the rewrite: one rewrite, 2/3 or better, otherwise drop. No second rewrite.

## A different approach?

None named. The trial shows that Codex does not report a rare case it judges harmless, so a
prompt cannot be made to list them. It does not show the wording harmful: T2 to T5 passed. The
BUGLOG row is closed. The working rule that re-sorts a rare RISK as a follow-up stays the way
to keep rare RISKs from earning rounds.
