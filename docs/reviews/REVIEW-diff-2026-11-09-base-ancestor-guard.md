# DIFF review — branch `feat/base-ancestor-guard` — refuse a `--base` not on the branch

Plan: `docs/reviews/SKILL-PLAN-review-base-ancestor-guard.md` (PLAN gate clean, see
`REVIEW-plan-2026-11-09-base-ancestor-guard.md`). Build: `ef2500b8`. Depth: Normal (the logic of a
guard script, so never Light; no High-row item). Seats: Codex alone, `--seat codex`; melious is
out of balance (owner's rule 2026-10-27, no rerun owed).

## Before round 1

- `test_base_check.sh` alone: PASS (T9a to T9g, 122 ok, 0 FAIL). `make check`: see Checks below.
- Mutation check, by hand: the `mutation-check` skill has no preset for a shell test runner, so
  each mutation was applied with a one-line string replace in a `git archive` copy of `ef2500b8`
  and `test_base_check.sh` run in the copy. Baseline passes; all six KILLED, by the tests the
  plan names:

| Mutation | Failed |
|----------|--------|
| delete the guard | T9a, T9c, T9d, T9d2, T9g |
| exempt every `--verify` | T9d, T9d2 |
| drop the exemption (refuse every base off the branch) | T9e, T9f |
| exemption only for `--verify` runs | T9f |
| two-dot remedy | T9a, T9c |
| case 3 prints case 2's "drop --base" remedy | T9d, T9d2 |

## Checks

`make check` on `ef2500b8`: passed in full (the machine load was about 500, so it took over 20
minutes; no check failed, T5's 6-second timing check included). The trail file and the BUGLOG row
added after it passed `check_clean.sh`, `check_buglog_rows.sh`, `test_buglog_rows.sh` and
`check_skill_budgets.sh`, and `test_base_check.sh` alone passed again.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|-------|------|----------|-----------|-----------------|--------------|
| 1 | `ef2500b8` | the three-file diff, `--evidence` (checks and mutation run) | Codex alone (`--seat codex`), melious out of balance; fresh-eyes: a Sonnet subagent, read-only | codex 190 s, 57,102; fresh-eyes 190 s, 119,611 | codex 2 / 0 / 0; fresh-eyes 0 / 1 / 5 |

## Round 1 findings

| Id | Sev | Finding | Disposition |
|----|-----|---------|-------------|
| A1 | BUG (Codex) | A reviewed head that landed on main while the feature commit was amended is refused, and the remedy repeats the rejected base | refuted: this is the plan's one named wrong refusal (plan, "What it does not catch", E5 second half), closed by the PLAN gate; case 3's text names the cause (the base is on the default branch) and the plan's way out is the merge base as `--base`, which the host applies; the refusal does not pick it (re-raised in round 2, R2-4). Not a defect of this build |
| A2 | BUG (Codex) | SKILL.md "a base on the default branch only is refused" is false for a main newer than the cached `origin/HEAD` | fixed: the claim was my overstatement; SKILL.md now says the test uses the local, unfetched `origin/HEAD` and a newer main passes, and the script header says the same. The code matches the plan, which lists this case |
| B1 | RISK (fresh-eyes) | No `origin` remote: a base HEAD lacks is refused with a fix (`remote set-head origin --auto`) that cannot work there | first re-sorted as rare with a BUGLOG row; Codex raised it again in round 2 (R2-3), so two reviewers found it: fixed after all (own refusal, T9h), row removed |
| B2 | NIT | `default_name` is printed unquoted | fixed: `printf '%q'` |
| B3 | NIT | T9a does not assert the delta and other-branch lines | fixed: asserted |
| B4 | NIT | SKILL.md sentence hard to parse | fixed with A2 |
| B5 | NIT | Case 6 (git exit other than 0/1) and a dangling `origin/HEAD` have no test | skipped: the plan's test table lists neither. Corrected in round 2 (R2-2): a dangling `origin/HEAD` takes T9g's path; a git exit other than 0/1 takes the two last `base_refuse` lines, which no test reaches (git fails there only on a damaged repository) |
| B6 | NIT | A full SHA given to `--base` is printed twice in the refusal header | skipped: cosmetic |

Codex also marked the `make check` and mutation results UNVERIFIABLE (it saw excerpts). Round 2
sends the mutation runner (`run.py`) and the full results as evidence.
