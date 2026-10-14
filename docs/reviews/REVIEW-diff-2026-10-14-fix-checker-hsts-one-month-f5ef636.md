# DIFF review — branch `fix/checker-hsts-one-month` — the checker's HSTS "shorter than one month" compare

Base `de64ec8` · depth: Normal (the logic of a check script) · verdict: CLEAN · authority used: WORKTREE-WRITE and BRANCH-COMMIT (this session created the worktree and the branch)

The commit ids below are as reviewed; the branch keeps them.

| Round | Head | Artifact | Reviewers (script header: Codex `gpt-6.1-sol`, read-only; GLM 5.3 over HTTP API; fresh-eyes: a `sonnet` sub-agent, read-only) | Seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `f5ef636` | full: `MONTH` 2629800 → 2592000, one new test | Codex at config effort, GLM 5.3, fresh-eyes | Codex 294 s / 136,450; GLM 212 s / 16,640; fresh-eyes 607 s / 222,726 | 0 / 1 / 5 |
| wording pass | `08750f3` | delta since `f5ef636` (comments, one message, test rows) | Codex, medium | 189 s / 54,329 | 1 / 1 / 0 |
| confirmation | `00a1032` | delta since `08750f3` (comments, one test name) | Codex, medium | 109 s / 33,728 | 0 / 1 / 0 |
| 2 | `2bf45f9` | delta since `00a1032`: a redesign, the threshold is the shortest month (28 days) | Codex medium (the `--verify` default), GLM 5.3 | Codex 226 s / 49,863; GLM 114 s / 12,689 | 0 / 1 / 3 |
| wording pass 2 | `8001fcc` | delta since `2bf45f9` (a comment, one constant) | Codex, medium | 118 s / 39,248 | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| R1-1 | RISK | Codex, GLM, fresh-eyes | 1 | The comments state "the dashboard's 1 month is 2592000 seconds" as fact; the support is live headers, and Cloudflare's pages give months, not seconds | superseded by the redesign (see W2, C1, R2-1) | the HSTS page says "Disable, or a range from 1 to 12 months" and gives no seconds; the zone-settings API reference says "Max age in seconds" with no values |
| R1-2 | NIT | fresh-eyes | 1 | `Math.round(age / MONTH)`: one constant for display and threshold made "about N months" read about 1.5% high | superseded: `MONTH` is the original line again | `git diff origin/main` shows `MONTH` untouched |
| R1-3 | NIT | fresh-eyes | 1 | "(about 1 month) ... shorter than the one month" for 15 to 29 days, number not pinned, so a floor-for-round mutant survived | fixed, `locally_verified` and `externally_reverified` (round 2) | the message names the threshold; the test row asserts "(about 1 month)" and the days and seconds; mutants M8 (floor), M9, M10, M11 fail the new test |
| R1-4 | NIT | GLM | 1 | The display rounding was pinned only where round and floor agree | fixed with R1-3 | same mutants |
| R1-5 | NIT | GLM | 1 | An escaped apostrophe in the new test's name | refuted, then moot | the file escapes apostrophes in other test names (line 427, "Cloudflare\'s"); the new name has none |
| R1-6 | NIT | fresh-eyes | 1 | Two rows of the new test repeated older coverage (6 and 12 months) | fixed | rows removed; older tests at lines 446 and 1173 remain |
| W1 | BUG | Codex | wording pass | The author's record said both comments quote the checklist's condition; the comment on `MONTH` did not | fixed in the record (the code was right) | only the test's comment quotes "start with 1 month when the domain moved recently" |
| W2 | RISK | Codex | wording pass | The comments still read as if the dashboard was shown to send 2592000 for "1 month" | superseded by the redesign | R2-1 |
| C1 | RISK | Codex | confirmation | "the mapping is observed" still asserts a mapping without paired setting and header | superseded by the redesign | the threshold no longer depends on what Cloudflare sends |
| R2-1 | RISK | Codex | 2 | Treating 28 days as enough for `ok` lacks support for what Cloudflare's 1 month is; shorter policies could pass | fixed, `locally_verified`, `externally_reverified` (wording pass 2) | the comment names 28 days as the check's own acceptance policy and its cost (28 and 29 days pass as `ok`) |
| R2-2 | NIT | GLM | 2 | The unchanged `MONTH` line says "the dashboard offers whole months" | not changed: a line from main, nothing depends on it; the HSTS page says "a range from 1 to 12 months" | `git diff origin/main` |
| R2-3 | NIT | GLM | 2 | The 28 and 29 day leniency was not acknowledged | fixed with R2-1 | the comment |
| R2-4 | NIT | GLM | 2 | The message hard-coded "28 days" and interpolated the seconds | fixed, `locally_verified`, `externally_reverified` | one constant, `SHORTEST_MONTH_DAYS`, used for both; mutants M10 and M11 |

Waivers and deferrals: none.

Follow-ups: none from this gate. (The wording about the checker's NEL sentence is in the other change, `docs/checklist-script-monitor`.)

Notes:
- Round 1 saw the first design: threshold 2592000, "the dashboard's 1 month". Every seat and every later pass raised the same point in a different form: Cloudflare's pages give months, not seconds, so the number is an observation. Two comment rewrites did not end it. The change was redesigned instead (a cut, not a patch): the threshold is the least a month can be, 28 days, and nothing in the code depends on what the dashboard sends. `MONTH` is unchanged.
- The evidence the first design rested on, kept here: `curl -sI --http1.1`, 2026-10-14T15:34Z, four sites on Cloudflare, names left out: `max-age=2592000; includeSubDomains`, `max-age=15552000; includeSubDomains`, `max-age=15552000`, `max-age=31536000; includeSubDomains; preload`. The first is what was called "shorter than one month" before this change.
- Codex's sandbox cannot open sockets (`listen EPERM`), so its runs of the suite are UNVERIFIABLE; the fresh-eyes agent ran it in round 1 (94 of 94), and the author's runs are in the PR body. Codex measured the evaluator in memory (boundary values, 124 cases against `2bf45f9`, the mutants) in every pass.
- Mutants: eleven breakages in a scratch copy of the final change (threshold back to `MONTH`; `<=`; branch removed; 28 days plus and minus a second; 30 days; 31 days; floor for round; message without the days and seconds; message with another seconds; message with another days) all fail the new test; the older table test also fails for the removed branch and for floor-for-round.
- GLM 5.3 saw round 1 in full and round 2's delta; it did not see the wording pass or the confirmation, so Codex holds the unbroken chain. Fresh-eyes ran in round 1 only, as Normal depth says. 7 script seat runs (343k tokens logged by the script) and one fresh-eyes run (223k), 2 rounds.
