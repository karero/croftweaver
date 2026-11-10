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
| a verify round prints the "drop --base" remedy (M6a) | T9d2 (and T9d's checks) |
| a plain run prints the verify remedy (M6b) | T9a, T9c |
| no-origin case prints the set-head remedy (M7, added in round 2's fix) | T9h |

On `923875f9` all of these were rerun: baseline passes, every mutation KILLED (run output in the
round 3 evidence; load 150 to 180). The first table above was `ef2500b8`'s; round 2 found that
a rerun labelled "case 3 prints case 2's remedy" had used the opposite replacement (`if true`),
so both directions are now run and named.
## Checks

Full `make check` was not run on later heads: the manager's word (2026-11-10) is to run only
`test_base_check.sh` and let CI run the full check; it passed alone on `923875f9` (T9a to T9h).
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
| B5 | NIT | Case 6 (git exit other than 0/1) and a dangling `origin/HEAD` have no test | skipped: the plan's test table lists neither. Corrected in round 2 (R2-2): a dangling `origin/HEAD` takes T9g's path; a git exit other than 0/1 takes the two last `base_refuse` lines, which no test reaches |
| B6 | NIT | A full SHA given to `--base` is printed twice in the refusal header | skipped: cosmetic |

Codex also marked the `make check` and mutation results UNVERIFIABLE (it saw excerpts). Round 2
sends the mutation runner (`run.py`) and the full results as evidence.

## Round 2 (Codex alone, `--verify`, delta `ef2500b8..9aebad0e`, evidence: mutation runner and output)

codex 169 s, 52,848 tokens. 3 BUG / 1 RISK, one BUG outside scope; no fresh-eyes.

| Id | Sev | Finding | Disposition |
|----|-----|---------|-------------|
| R2-1 | BUG | The M6 rerun was mislabelled: `if true` makes plain runs print the verify remedy | fixed: runner has M6a (`if false`) and M6b (`if true`), both KILLED; table above corrected |
| R2-2 | BUG | B5's disposition said both untested cases take T9g's path | fixed (wording): a dangling `origin/HEAD` does; a git exit other than 0/1 takes the last two `base_refuse` lines, which no test reaches. No test added: the plan's table lists neither, and the lines refuse loudly |
| R2-3 | RISK | B1's rarity is unsupported; the no-origin refusal gives a remedy that cannot work | fixed in code (`923875f9`): own refusal naming a commit HEAD contains or `--base none`; T9h; M7 KILLED by T9h; BUGLOG row removed. Two reviewers found it (B1, R2-3), which rule 4 counts |
| R2-4 | BUG (outside scope) | A1 again: the refusal does not pick the merge base itself | refuted again, as in round 1: the plan's one named wrong refusal. Named to the owner in the PR |

## Round 3 (Codex alone, `--verify`, delta `9aebad0e..923875f9`, evidence: full mutation run)

codex 106 s, 38,378 tokens. No BUG, RISK or NIT: CLEAN. Codex marked execution evidence
UNVERIFIABLE (read-only seat), and said "damaged repository only" for git's ancestry errors had no
support: the disposition above now says only that no test reaches those lines.

Gate total (script's line, rounds 1 to 3): 148,328 tokens logged, plus the round 1 fresh-eyes
read (119,611). Codex alone throughout (melious out of balance; no rerun owed). 3 rounds, 8 findings
(A1, A2, B1 to B6 in round 1 were 8; round 2 added 4; round 3 none): 12 in all.
