# DIFF review — PR 505 — `review_log.sh add` refuses bad round, seconds, tokens and outcome values
Base `2dc47c690f3708398960cf68d6e5eb0b7caee3e7` · depth: Normal (a guard script is never Light) · verdict: CLEAN · authority used: POST AUTHORITY — this session's own PR 505; WORKTREE-WRITE — this session's own worktree; BRANCH-COMMIT — this session's own branch

Plan: `docs/reviews/SKILL-PLAN-review-log-add-checks.md` (PLAN gate skipped: a fix that restores intended behaviour).

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `a78deaf2` | full, base `2dc47c69`; evidence file | Codex gpt-6.1-sol, read-only; GLM 5.3 on melious (HTTP API); fresh-eyes subagent | codex 294 s / 55985; melious 395 s / 30973; fresh-eyes 652 s / 151090 (logged by hand) | 1 BUG / 2 RISK / 5 NIT |
| 2 | `2115a8c3` | delta since `71d7bb3b` (`--base`); evidence file | Codex gpt-6.1-sol, effort medium, read-only; GLM 5.3 | codex 178 s / 47012; melious 275 s / 17115 | 1 BUG / 0 RISK / 1 NIT |
| 3 | `7a0f7255` | delta since `2115a8c3`; evidence file | Codex, effort medium; GLM 5.3 | codex 149 s / 49674; melious 230 s / 18998 | 1 BUG / 0 RISK / 2 NIT |
| re-gate | `7a0f7255` | delta since `2115a8c3` (`--base`), no `--round` | Codex, effort medium; GLM 5.3 FAILED (out of balance, HTTP 200) | codex 86 s / 38323; melious 0 s | none |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex | 1 | `written()` checked no stderr; outcome cases checked only the column; the plan says each case checks exit, stderr and line count | FIXED `71d7bb3b` | `written()` requires empty stderr; accepted-value and outcome cases check the `logged:` line; section 27a green |
| F2 | RISK | GLM | 1 | The `--` check also covers `--reason` and `--cut`; a text starting `--` would drop the row | REFUTED | `--cut`, `--earned-by` are refused by the script itself when they start with `-`; every `WHY=` and `reason=` in `independent_review.sh` starts with a letter (two seats read it); the reason column of the real log holds none; a refusal is loud on stderr and `log_seat`'s status is ignored by design |
| F3 | RISK | GLM | 1 | A new outcome label at a call site would drop its row silently | REFUTED | Every `outcome=` in `report_tier` read: OK, SKIPPED (rc 3, never logged), NOT COUNTED, FAILED; `log_seat` strips to the first word; `costlog`, `costfail`, `costnc` pin all three through the production entry; stderr is not hidden by `>/dev/null` |
| F4 | NIT | GLM | 1 | Accepted-value cases did not check the `logged:` line | FIXED `71d7bb3b` | as F1 |
| F5 | NIT | GLM | 1 | Refused numeric cases did not check the value in the message | FIXED `71d7bb3b` | message must name flag and value |
| F6 | NIT | fresh-eyes | 1 | `lacks … "review_log.sh add"` missed `review_log.sh: … needs a value` | FIXED `71d7bb3b` | needle is `review_log.sh` |
| F7 | NIT | fresh-eyes | 1 | `*[!0-9]*` against the repo's spelled-out class | FIXED `71d7bb3b` | `*[!0123456789]*` |
| F8 | NIT | fresh-eyes | 1 | Gate-id check passed on an empty id | FIXED `71d7bb3b` | id must be non-empty, then matched with `has` |
| G1 | BUG | Codex | 2 | `REVIEW_LOG=off` cases and the zsh case did not check stderr and line count | FIXED `2115a8c3` | off case checks stdout, rc, empty stderr, no file created, line count; zsh case counts two refusals naming `--seconds` |
| G2 | NIT | GLM | 2 | Gate-id check used an inline `sh -c` instead of `has` | FIXED `2115a8c3` | split into id-not-empty and `has` |
| H1 | BUG | Codex | 3 | Off cases did not show the default log untouched | FIXED `7a0f7255` | both off cases snapshot the default log's line count and run in a folder under the test temp dir; tightens an assertion on a test that already fails on wrong behaviour, so not a substantive BUG (SKILL.md step 6) |
| H2 | NIT | GLM | 3 | `$PWD/off` probe could fail on a stray file | FIXED `7a0f7255` | probe confined to the temp dir |
| H3 | NIT | GLM | 3 | The zsh loop reads `~/.zshenv`, which could set `shwordsplit` | FIXED `7a0f7255` | `zsh -f -c` |

Waivers and deferrals: none.
Follow-ups: none new. The BUGLOG row of 2026-11-07 is marked fixed in this PR.

Notes:
- Rounds: 3 plus one re-gate. Findings: 13 distinct (3 BUG, 2 RISK, 8 NIT); 11 fixed, 2 refuted. Items the seats could not verify (run transcripts, log history) were confirmed as findings: 0.
- Round 3's delta held only test code that tightened existing assertions, so no further full round was owed. The re-gate ran without `--round` and with the delta since `2115a8c3`; the delta held code, so it was not a wording pass.
- Melious was out of balance at the re-gate; Codex alone is enough by the owner's rule (2026-10-27). Codex holds an unbroken chain from round 1 through the re-gate; the Melious chain broke at the re-gate; fresh-eyes' chain ended at round 1 (Normal depth).
- Mutation check: 14 of 14 mutations killed, on `a78deaf2` and again on `7a0f7255`, run by hand against section 27 (the helper has no shell runner preset).
- Final run on `7a0f7255`: `test_failed_tier_report.sh` all checks passed (exit 0), `test_round_checks.sh` 96 of 96 (exit 0), no SKIP line for the zsh case. A fresh `make check` was not run locally (the first run was stale and was stopped to free a machine at load 500 to 1000); CI runs it.
- A slip, disclosed: while writing the tests I ran a stray `review_log.sh add` against the real cost log, then removed the last line with `sed -i '' '$d'` in the same command, about a second apart. Checked afterwards: the rows around that time (16:09:25Z, then 16:12:58Z) are consecutive and none from this branch lies between them, so the removed line was almost certainly that stray row. A row another session appended in that second would leave no trace; that cannot be excluded.
