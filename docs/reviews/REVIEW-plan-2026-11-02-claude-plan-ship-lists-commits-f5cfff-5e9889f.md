# PLAN review — branch `claude/plan-ship-lists-commits-f5cfff` — `npm run ship` lists the commits that go live

Artifact: `docs/reviews/SKILL-PLAN-ship-lists-commits.md`. Base `9fcce2cc` · depth: High (the
starter's publish script; the High row names deploy code) · verdict: OPEN · authority used:
WORKTREE-WRITE and BRANCH-COMMIT, atom A (the app made this worktree and branch for this session).
No PR: POST AUTHORITY and GATED-THIS-DIFF do not apply. Seats: Codex and GLM 5.3 on melious in one
command (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`, `CODEX_EFFORT=config`), fresh-eyes Opus 5.5
in rounds 1 to 3.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `5e9889fb` | full plan; evidence `evidence-r1.md` (90,177 bytes: `ship.sh` whole, the test file's stub and harness, `whats-new.sh` line 80, three git READs) | Codex gpt-6.1-sol, config effort, read-only; melious FAILED (out of balance), so Codex alone by the owner's rule of 2026-10-27; fresh-eyes Opus 5.5 | Codex 205 s, 65,730 · fresh-eyes 319 s, 157,987 | 3 / 2 / 4 (Codex 2/1/1, fresh-eyes 2/3/3; A1 and A4 from both) |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | BUG | Codex, fresh-eyes | 1 | `list` already holds the worktree list's path (`ship.sh` 381, 405, 572); overwriting it breaks worktree mode | fixed, locally_verified | new names `live_prod`, `live_n`, `live_all`, `live_lines`; `local` ruled out (dynamic scope); mutation "name it `list` again" added |
| A2 | BUG | fresh-eyes | 1 | With `--first-parent`, "3 commits" in the header counts lines, not commits | fixed, locally_verified | header carries no number; a "commits in all" line from a second count when the two differ |
| A3 | RISK | fresh-eyes | 1 | After the script's own `git pull --no-rebase` advice, other people's merges hide behind one merge line | fixed, locally_verified | reproduced 2026-11-02, git 2.54: first-parent lines "Merge branch 'main' of ../o", "my local change"; counts fp=2 all=4. The "commits in all" line plus case L6 |
| A4 | BUG | Codex (BUG), fresh-eyes (RISK) | 1 | `--no-pager` is not load-bearing: a captured `git log` starts no pager, so L5 and its mutation cannot fail | fixed, locally_verified | under `script -q /dev/null`, git 2.54: the captured call left no mark, the direct one left `mark-direct`. `--no-pager`, L5 and the mutation dropped |
| A5 | RISK | fresh-eyes | 1 | Only the count read's failure had a case; a failed log read could go on unseen | fixed, locally_verified | stub cases `countfail` and `logfail`, a mutation for each |
| A6 | NIT | fresh-eyes | 1 | macOS `tr` in a UTF-8 locale stops on a non-UTF-8 byte | fixed, locally_verified | `LC_ALL=C tr` |
| A7 | NIT | fresh-eyes | 1 | Say `-n 20` is the only cap, or the mutation could survive | fixed, locally_verified | plan step 1 says so |
| A8 | NIT | fresh-eyes | 1 | Same ref name is not same value: a shared clone's fetch could move production between reads | fixed, locally_verified | `live_prod` read once for the three reads |
| A9 | NIT | Codex | 1 | Say which bytes the `tr` removes | fixed, locally_verified | step 4 names the ranges, keeps tab and newline |

Follow-ups: UTF-8 C1 controls pass the `tr` (fresh-eyes, UNVERIFIABLE; listed under Not covered).
Notes: round 1 melious out of balance; Codex alone counts by the owner's rule, no rerun owed.
