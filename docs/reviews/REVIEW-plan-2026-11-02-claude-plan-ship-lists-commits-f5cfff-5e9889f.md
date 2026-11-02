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
| 3 | `e01fe127` | full plan, verification of B1–B9; evidence `evidence-r2.md` | Codex gpt-6.1-sol, config effort; melious FAILED (out of balance), Codex alone; fresh-eyes Opus 5.5 | Codex 178 s, 69,058 · fresh-eyes 301 s, 144,124 | 3 / 2 / 2 (Codex 1/1/0, fresh-eyes 2/2/3; C1 and C2 from both) |
| 4 | `4f5f1bb9` | full plan, verification of C1–C7 and a trace of every mutation; earned by C1, C3, C4 (`--earned-by test-guard-blind,race-claim`) | Codex gpt-6.1-sol, config effort; melious FAILED (out of balance), Codex alone; no fresh-eyes (rounds 1–3 only) | Codex 190 s, 78,295 | 0 / 2 / 0 |
| final read | `0f2bea34` | whole plan, fresh, no trail; evidence `evidence-r2.md` | fresh Opus 5.5 subagent that had not reviewed this plan (melious out of balance; ollama does not stand in; Kimi only on the owner's ask) | 493 s, 176,867 | 0 / 0 / 7 |

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

| C1 | BUG | Codex (BUG), fresh-eyes (NIT) | 3 | B5's reason is wrong: `push_once` names no expected value, so a production that moved forward inside `$id`'s history still fast-forwards | fixed, locally_verified | `ship.sh` 273–282 read; step 1 now says refused outside `$id`'s history, else goes through with the list naming the commits that went live meanwhile |
| C2 | RISK | Codex, fresh-eyes | 3 | The stub's option loop (60–67) moves every `-c` into `$FAKE_DIR/settings`, so a `log` arm cannot see `-c log.showSignature=false` (B4 partly fixed) | fixed, locally_verified | the `log` arm refuses unless the last line of the settings file is `log.showSignature=false`; L4 stays the real-git check |
| C3 | BUG | fresh-eyes | 3 | `prodfail` cannot catch its mutation: an empty `live_prod` makes the next read ask for `..$SHA`, the stub refuses it, and the run still ends with 0 pushes (B3 partly fixed) | fixed, locally_verified | fresh-eyes: `git rev-list --count "..$id"` printed 0, rc 0; `prodfail` now asserts no `rev-list` or `log` call |
| C4 | BUG | fresh-eyes | 3 | `stopat-revlist` passes with the `stop_point` dropped: `on_exit` (302–305) prints the stop message on its own | fixed, locally_verified | `on_exit` read; the case also asserts no "couldn't list" line, as `stopverdict` does (check_ship_push.sh 555); mutation added |
| C5 | RISK | fresh-eyes | 3 | L6's `git pull --no-rebase` opens an editor when the file runs in a terminal | fixed, locally_verified | fresh-eyes under `script`: "Waiting for your editor"; L6 uses `-q --no-rebase --no-edit` |
| C6 | NIT | fresh-eyes | 3 | L4 names no mode; in worktree mode a decoration would show `refs/`, not `(HEAD` | fixed, locally_verified | L4 is worktree mode and also rejects `refs/` |
| C7 | NIT | fresh-eyes | 3 | "List line" is undefined for L2's exact count and L4's checks | fixed, locally_verified | defined at the head of the real-git half: standard output, `^    [0-9a-f]{7} `, header to blank line |

| D1 | RISK | Codex | 4 | L4's `ignature` check reads only list lines, so a stray `No signature` line (no id) would pass it | fixed, locally_verified, closing edit not externally re-verified | not earning: the stub `log` arm's settings check already fails that mutation; L4 now holds the whole block to the expected lines |
| D2 | RISK | Codex | 4 | C1's new claim (an ancestor move still fast-forwards) is not measured for a move during the gate | fixed, locally_verified, closing edit not externally re-verified | not earning: nothing built changes; cut, the plan now claims nothing about the push after a move |

| E1 | NIT | final read | final | `prodfail`'s "no call logged" works only if refused calls are logged | fixed, locally_verified, closing edits not externally re-verified | the arms log on entry, before the exact match |
| E2 | NIT | final read | final | L6: branch and folder change on one file would make the pull stop on a conflict | fixed, locally_verified | two different files |
| E3 | NIT | final read | final | No case pins `LC_ALL=C` | fixed, locally_verified | final read measured macOS `tr` "Illegal byte sequence", exit 1; L4 gains a raw `\xff` subject; mutation "drop `LC_ALL=C`" (Mac job only) |
| E4 | NIT | final read | final | Where the `tr` runs is unsaid; outside the guard it would end the run without the plan's message | fixed, locally_verified | the `tr` is the guard's fifth step |
| E5 | NIT | final read | final | In folder mode no blank line follows the list | fixed, locally_verified | a blank line after the list and its notes |
| E6 | NIT | final read | final | With nothing new the run still ends "✓ Pushed. Cloudflare is building the live site now." | follow-up | `ship.sh` 835; listed under Not covered |
| E7 | NIT | final read | final | New wording checks would turn a translated site's stub tests red | fixed, locally_verified | they go through `expect`'s marker or honour `SHIP_GATE_SKIP_WORDING` (check_ship_push.sh 230–240) |

Follow-ups: E6, the last line of a run with nothing new (`ship.sh` 835). UTF-8 C1 controls pass the `tr` (fresh-eyes, UNVERIFIABLE; listed under Not covered).
Notes: rounds 1 to 3 melious out of balance; one kind came back: a test guard that cannot fire (B1, B3 in round 2; C2, C3, C4 in round 3), so round 4 asked the seat to check every case against every mutation it is credited with (it traced all 13, each caught); round 4 had no BUG and no earning RISK, so the rounds end there (stop condition a2); Codex alone counts by the owner's rule, no rerun owed.
