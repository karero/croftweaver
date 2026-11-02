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
| 2 | `87e7f537` | full plan, verification of A1–A9; evidence `evidence-r2.md` (91,129 bytes: round 1's plus the pager and pull --no-rebase READs) | Codex gpt-6.1-sol, config effort; melious FAILED (out of balance), Codex alone; fresh-eyes Opus 5.5 | Codex 351 s, 89,937 · fresh-eyes 305 s, 150,832 | 1 / 3 / 5 (Codex 1/1/0, fresh-eyes 0/3/5 incl. 1 outside scope; B1 from both) |

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

| B1 | BUG | Codex (BUG), fresh-eyes (RISK) | 2 | With `live_prod` = `$SHA` in the stub, a swapped range is the same string: the stub arms cannot see it | fixed, locally_verified | stub `rev-parse` answers a distinct `PROD`; arms expect `$PROD..$SHA`; mutation "origin/production instead of live_prod" added |
| B2 | RISK | Codex | 2 | The "lists them all" hint names `origin/production`, which points at `$id` once the publish lands | fixed, locally_verified | hint prints `<live_prod 12>..<id 12>` |
| B3 | RISK | fresh-eyes | 2 | A5 partly fixed: four reads, two failure cases | fixed, locally_verified | one guard for the four reads; `prodfail`, `countfail`, `allfail`, `logfail`, a mutation each |
| B4 | RISK | fresh-eyes | 2 | No case catches a dropped `-c log.showSignature=false` (unsigned commits print nothing extra) | fixed, locally_verified | fresh-eyes measured a "No signature" line with an ssh-signed commit; L4 signs one commit, stub arm matches the `-c`; mutation added |
| B5 | NIT | fresh-eyes | 2 | A8 partly fixed: the divergence check still reads the name on its own | refuted as accepted | a moved production makes the push fail as `raced`; only one run's list text is off; plan step 1 says so |
| B6 | NIT | fresh-eyes | 2 | L6 needs a one-commit branch and folder-mode preparation | fixed, locally_verified | L6 names both |
| B7 | NIT | fresh-eyes | 2 | C1 bytes pass raw too, not only as UTF-8 | fixed, locally_verified | Not covered entry widened |
| B8 | NIT | fresh-eyes | 2 | "… and 4 more" is a bare number | fixed, locally_verified | `<live_n − 20>` |
| B9 | NIT | fresh-eyes (outside scope) | 2 | "the merges above" may be cut off past 20 lines | fixed, locally_verified | "the merges in this range" |

Follow-ups: UTF-8 C1 controls pass the `tr` (fresh-eyes, UNVERIFIABLE; listed under Not covered).
Notes: rounds 1 and 2 melious out of balance; Codex alone counts by the owner's rule, no rerun owed.
