# DIFF review — branch `feat/cut-or-continue-manager-ask` — the manager ask at a kind's second return

Plan: `docs/reviews/SKILL-PLAN-review-cut-or-continue.md`, option (e), built as its tasks say. Depth:
Normal at least (it changes the review script itself; no High-row topic). Seats as asked for: Codex
and GLM 5.3 on melious. `runs.tsv` shows what ran: in rounds 1 and 2 the melious seat FAILED, "out
of balance (HTTP 200)", after 1 s, so each round stands on Codex alone (REVIEW-RULES, 2026-10-27:
no rerun of melious is owed). Gate id `20261117T160711Z-64071`. Run from the primary checkout's
script, which equals `origin/main` for this skill. This session built the change and made every
commit.

Checks: `make check` before round 1 passed; the tests were mutation-checked first: five mutations
(count the cut round as a return; count only rounds with `--cut`; drop the kind normalising; drop
the warning; key the answer to the round, not the kind) each made `test_round_checks.sh` fail.
`test_failed_tier_report.sh` passes with columns moved to 18.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|-------|------|----------|-----------|-----------------|--------------|
| 1 | `4afb1971` | the whole change | Codex alone; melious out of balance | 140 s, 58,539 | 1 / 0 / 0 |
| 2 | `d9a3d8bf` | the fix, `--verify` round 1's finding, `--base 4afb1971` | Codex alone (medium); melious out of balance | 96 s, 52,095 | 0 / 0 / 0 |

Gate 1 (id `20261117T160711Z-64071`) ran before this branch took `origin/main`, which brought the
fresh-eyes seat check (a Normal gate owes a fresh-eyes line at round 1). Gate 1 has none, and my
first version of this trail wrongly said a non-plan diff needs none. After the merge (`76efd406`)
the whole PR diff went through a new gate, so the merge result is what was reviewed, with the
fresh-eyes seat:

Gate 2 (id `20261117T182925Z-15156`), whole PR diff against `origin/main`:

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|-------|------|----------|-----------|-----------------|--------------|
| 1 | `76efd406` | the whole PR diff | Codex alone (melious out of balance, "Required: 170, Available: 0"); fresh-eyes on `sonnet` (a sub-agent given only the diff and the reviewer brief) | Codex 168 s, 68,016; fresh-eyes 218 s, 161,694 | Codex 2 / 0 / 0; fresh-eyes 0 / 2 / 5 |

Gate 1 total 110,634 tokens (2 rounds, 1 finding). Gate 2 round 1 total 229,710 tokens, 9 findings.

## Round 1 findings

| Id | Sev | Finding | Disposition |
|----|-----|---------|-------------|
| A1 | BUG | `--manager-said 'k: keep fixing; j: '` passed validation and hid the blank answer for `j`: the log joins answers with "; " | fixed: a value holding "; " is refused, with a test case for each shape; confirmed in round 2 |

## Gate 2, round 1 findings

| Id | Sev | Source | Finding | Disposition |
|----|-----|--------|---------|-------------|
| B1 | BUG | Codex | `review_log.sh add --manager-said 'k: keep fixing; j: '` (the log's own entry point) stores a blank answer, and `gate` counts it as answering `j` | fixed in the `gate` awk: an entry answers its kind only with a colon and a non-blank answer; a gate test on a log line holding that value |
| B2 | BUG | Codex | this trail said a non-plan diff needs no fresh-eyes seat, against SKILL.md Review depth | fixed: claim corrected above, seat run and logged for gate 2 |
| F1 | RISK | fresh-eyes | after "keep fixing" the round still refuses without `--cut`, yet SKILL.md says nothing is refused | SKILL.md step 6 now says the `--cut` check still applies to those rounds; the plan's S4 does not lift it |
| F2 | RISK | fresh-eyes | step 7 says the next fix after a first return is a cut, but the script lets round 6 run without `--cut` | refuted: round 6 is the round that finds the first return, with no fix between; the next round (7) is the one whose `--cut` the existing check demands |
| N1 | NIT | fresh-eyes | the 300-character guard was untested (the 301 `x` value hit the colon check first) | fixed: the test value is `k: ` and 300 `x` |
| N2 | NIT | fresh-eyes | tab and CR refusals untested | fixed: two cases added |
| N3 | NIT | fresh-eyes | header says the checks warn when the log is off; the ask does not | fixed: header says the ask has no warning of its own |
| N4 | NIT | fresh-eyes | the "17-column" fixture lines had 16 fields | fixed: the fixture adds the reason column |
| N5 | NIT | fresh-eyes | `_: x` (empty after normalising) accepted, unused `back_as`, two flags for one kind, no 40-character cap, a round with only an answer is not shown | first two fixed; the rest re-sorted: rare, harmless (two flags for one kind both show; an over-long kind still matches nothing) |

## Beyond the plan text

`review_log.sh round-check` also prints a `back` record (kind, round of its first cut). The closing
reminder needs the cut round, and the plan's `ask` record exists only at a second return.
