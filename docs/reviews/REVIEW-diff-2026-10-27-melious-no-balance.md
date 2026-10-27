# Review trail: DIFF gate, an empty Melious balance means Codex alone

Gate: DIFF, depth Normal (a review script's logic). Diff: `git diff origin/main...HEAD -- skills`
(the plan and trails under `docs/reviews/` are not in it). Pair run as one command
(`SECOND_SEAT=melious`). Plan: `docs/reviews/SKILL-PLAN-melious-no-balance-codex-alone.md`
(PLAN gate CLEAN, `docs/reviews/REVIEW-plan-2026-10-27-melious-no-balance.md`).

Before round 1: `make check` green at 9d8e5dc0 (one SKIP: Perl::MinimumVersion is not installed
locally; CI checks it). Mutation check, one copy of d55ad455 per mutation, the suite run in each:
(a) match the message instead of the code: `mechoed` and `mcodeonly` fail; (a2) require both:
`mcodeonly` fails; (b) ignore how Melious ran: `mnobalance` fails; (c) keep the paste prompt:
`sseatbal` fails. All four killed.

| Round | Artifact | Seats | Findings | Disposition |
|-------|----------|-------|----------|-------------|
| 1 | d1.diff at 9d8e5dc0, evidence = test records | codex OK (137 s, 47,688 tokens); melious FAILED, out of balance: Codex alone, no rerun owed (the new rule, printed by the new code) | 1 RISK (D1) | re-sorted: rare; BUGLOG row |

**Result: CLEAN after 1 round, 1 finding (a RISK, re-sorted as rare), Codex alone (melious out of
balance), 47,688 tokens logged.**

## Round 1 findings (Codex)

- D1 RISK: a balance error in a JSON error reply (exit 2 or 9) would keep the old rerun advice.
  Re-sorted: rare. All 280 balance replies kept on the maintainer's machine (2026-10-25 to 27)
  came as HTTP 200 streams with one error chunk. The miss is safe: the old advice comes back, no
  wrong waiver. BUGLOG row 2026-10-27.
- Not acted on: three UNVERIFIABLE notes (capture provenance, the owner's words, the test records'
  completeness; the records are the saved outputs of the runs).
