# PLAN review — branch `claude/plan-base-ancestor-guard-4c9cae` — refuse a `--base` not on the branch

Plan: `docs/reviews/SKILL-PLAN-review-base-ancestor-guard.md`. Evidence sent every round with
`--evidence`: `docs/reviews/EVIDENCE-review-base-ancestor-guard.md`. Depth: Normal (a plan for
a guard script's logic; no High-row item, so no red team). Seats: Codex and GLM 5.3 on melious.

Checks before round 1: `make check` on the round-1 tree failed one check only, `T5 ... in under
6 seconds (took 7s)`, a timing check, with the load average near 700. `test_base_check.sh`
alone then passed (99 ok, 0 FAIL, exit 0). The only file added since, the evidence file, passed
`check_clean.sh`. No full rerun before round 1.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|-------|------|----------|-----------|-----------------|--------------|
| 1 | `e70e090a` | the whole plan | Codex alone; melious out of balance (no rerun owed, owner's rule 2026-10-27) | codex 126 s, 37,007 | 1 / 2 / 0 |

## Round 1 findings

| Id | Sev | Finding | Disposition |
|----|-----|---------|-------------|
| A1 | BUG | Case 3's remedy says to drop `--base`, but a `--verify` run with no `--base` is refused (script lines 610 to 614), so the fix it prints fails | fixed: case 3 prints its own refusal, reusing the delta command and merge-link lines of the existing `--verify`-without-`--base` refusal through one helper |
| A2 | RISK | "On neither HEAD nor main" does not prove a merge link: a `--verify` run with another branch's head also passes; the docs sentence overstated the exception | fixed: the plan, case 4 and the docs sentence now describe the rule of thumb; "What it does not catch" names another branch's head |
| A3 | RISK | No test runs case 3's printed remedy | fixed: T9d now checks the refusal text, and the new T9d2 runs its delta command and expects the reviewer to run; a mutation printing case 2's remedy in case 3 must fail T9d and T9d2 |

Also reworded: "Verified: every row of E1 and E2" now reads "Run or read by me", after Codex
marked the claim UNVERIFIABLE (it saw outputs, not reruns).
