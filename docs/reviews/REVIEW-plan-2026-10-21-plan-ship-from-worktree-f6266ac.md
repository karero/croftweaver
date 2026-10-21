# PLAN review — branch plan/ship-from-worktree — publish from a throwaway worktree (`SKILL-PLAN-ship-from-worktree.md`)

Base `6681e7be` · depth: High (deploy code that publishes to live sites and deletes folders) · verdict: OPEN · authority used: WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch). No PR: POST AUTHORITY and GATED-THIS-DIFF do not apply.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `f6266ac8` | full | Codex CLI 0.163.0, gpt-6.1-sol, config effort, read-only · Melious HTTP API, glm-5.3, text only · fresh-eyes sub-agent, claude-opus-5-5, read-only by instruction | Codex 627 s, 91,452 · Melious 335 s, 24,762 · fresh-eyes 1,180 s, 250,687 | 7 / 9 / 7 after merging duplicates (Codex 2/2/0, Melious 0/2/3, fresh-eyes 4/7/8; A11 raised from RISK to BUG on the host's reproduction). Unverifiable entries: Codex 5 groups, Melious 6, fresh-eyes 4; 2 confirmed by the host and became A7 and A11 |
| 2 | `73bb0291` | full, as a verification round (prior findings A1 to N9) | same three seats; Codex at config effort | Codex 538 s, 115,737 · Melious 729 s, 42,558 · fresh-eyes 1,426 s, 279,189 | 6 / 9 / 6, plus 2 NIT outside scope, fixed (Codex 5/3/0, Melious 0/2/2, fresh-eyes 3/6/6+2). Substantive BUGs: B1, B2 (kind: lock), B3 (trap status), B4 (hook wiring order). Unverifiable entries: Codex 6 groups, Melious 9, fresh-eyes 5; none became a finding |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | BUG | Codex, Melious (NIT), fresh-eyes | 1 | The busy check scanned worktrees, then created one: two runs could both pass | superseded by B1, B2 | round 2: the lock's takeover still let two through |
| A2 | RISK | Melious, fresh-eyes | 1 | Leftovers matched "under the temp folder" never match (`/private/var` vs `/var`; TMPDIR differs) | fixed, externally_reverified | round 2, Codex and fresh-eyes |
| A3 | BUG | Codex; fresh-eyes NIT | 1 | "Per-checkout" setting is wrong: linked worktrees share the clone's config; a global value could switch a fresh clone on | fixed, externally_reverified | round 2, Codex and fresh-eyes |
| A4 | RISK | Codex | 1 | Today's mode switching to `origin/main`'s id could push an untested commit when `main`'s upstream is elsewhere | fixed, externally_reverified | round 2, Codex; its added claim became B5 |
| A5 | RISK | Codex; Melious (unverifiable) | 1 | The gate claim rests on a relative hooks path; wiring can fail and exit 0 | fixed in part, externally; rest in B4 | round 2 |
| A6 | RISK | Melious; fresh-eyes NIT | 1 | `GIT_DIR` reaches gate steps from a linked worktree; only the plan's own test cleared it | fixed, externally_reverified; gaps in B10, B15 | round 2, fresh-eyes reproduced `GIT_DIR` |
| A7 | BUG | fresh-eyes; Codex (unverifiable) | 1 | Production moving during the gate gives `! [remote rejected] … (failed to update ref)`; the classifier says "can't name" | fixed, externally_reverified; GitHub's wording in B8 | round 2, fresh-eyes reproduced the wording |
| A8 | BUG | fresh-eyes | 1 | Today's messages say "still safely on 'main'", false in worktree mode | fixed, externally_reverified | round 2, Codex |
| A9 | BUG | fresh-eyes; Melious NIT | 1 | "The shared folder is neither read nor changed" is wrong; plain `git status` rewrites the index | fixed, externally_reverified | round 2, fresh-eyes reproduced the index behaviour |
| A10 | BUG | fresh-eyes | 1 | The gate-step git audit missed Site C's test config (`rev-parse --show-toplevel`) | fixed, externally_reverified | round 2, fresh-eyes |
| A11 | BUG | Codex (unverifiable), fresh-eyes (RISK) | 1 | A repo-wide prune drops a worktree whose folder is only away, with its HEAD, index and reflog | fixed, externally_reverified | round 2, fresh-eyes: removal by path works with the folder gone |
| A12 | RISK | fresh-eyes | 1 | A terminate to the script alone runs the trap while push and gate go on | superseded by B7 | round 2: no mechanism named |
| A13 | RISK | fresh-eyes | 1 | The mktemp guard cannot test ship.sh | superseded by B11 | round 2 |
| A14 | RISK | fresh-eyes | 1 | The real-git test would pick up the machine's or CI's git settings | fixed, externally_reverified | round 2, Codex |
| A15 | RISK | fresh-eyes | 1 | One test port per site: another session's test run or preview fails the gate | open — owner: waive as a stated limit, or bring a per-checkout port in | D2 "Known limit"; carried by Codex in round 2 |
| A16 | RISK | fresh-eyes | 1 | "Push them" is wrong where pushes to `main` are refused | fixed, externally_reverified | round 2, Codex |
| N1 | NIT | fresh-eyes | 1 | Exit trap under stop-on-error can skip steps and flip a success | superseded by B3 | round 2 |
| N2 | NIT | fresh-eyes | 1 | A leftover left locked needs removal forced twice | fixed, externally_reverified | round 2, fresh-eyes |
| N3 | NIT | fresh-eyes | 1 | A refused liveness check reads like a dead process | superseded by B17 | round 2 |
| N6 | NIT | fresh-eyes | 1 | The CDPATH guard does not run ship.sh or its test | fixed, externally_reverified | round 2, Codex |
| N7 | NIT | fresh-eyes | 1 | The script that runs is the folder's copy; the test pins the old push command | fixed, externally_reverified; consequence in B12 | round 2 |
| N8 | NIT | fresh-eyes | 1 | Site B's install only adds time and a failure path | fixed, externally_reverified | round 2, fresh-eyes |
| N9 | NIT | Melious | 1 | Any `exec` anywhere defeats the trap | fixed; reason corrected in B6 | round 2 |
| B1 | BUG | Codex, fresh-eyes, Melious (NIT) | 2 | The lock still let two runs through: a check-then-remove takeover, and a window where the lock has no process id yet reads as stale | fixed by a cut, locally_verified | D2: automatic takeover removed; any existing lock stops the run; message names path and removal command |
| B2 | BUG | fresh-eyes, Melious (NIT) | 2 | The trap removed the lock whether or not this run took it, so a stopped second run freed the first run's lock | fixed, locally_verified | D2 "The exit trap": only its own lock; S9 asserts the lock still names the first |
| B3 | BUG | Codex, fresh-eyes | 2 | The trap's stated order (stop-on-error off, then save the status) always saves 0 | fixed, locally_verified | host: `false; set +e; echo $?` prints 0, saving first prints 1 (bash 3.2, 5.3); real-git cases assert the exit status |
| B4 | BUG | Codex, Melious (RISK), fresh-eyes (NIT) | 2 | The hooks-path announcement came before the install that may change it, and wiring can fail silently | fixed, locally_verified | D2 "The install", "The gate": read after the install, from inside the worktree; host: a throwaway made from a session worktree sees the shared `scripts/hooks` |
| B5 | BUG | Codex | 2 | "A commit landing mid-publish changes nothing" overclaims for today's mode, whose gate still builds the folder | fixed, locally_verified | D2 "The commit id" reworded |
| B6 | BUG | Codex | 2 | "Any `exec` replaces the shell" is wrong: a redirect-only `exec` keeps the trap | fixed, locally_verified | host: trap ran after `exec 3>/dev/null`; D2 states the ban as deliberately wider |
| B7 | RISK | Codex, fresh-eyes | 2 | Stopping the push names no mechanism; the obvious ones fail; nothing is guaranteed once git is sending | fixed, locally_verified | D2 "Signals": own process group, status file, terminate and wait; "may or may not have landed" after the gate; S10 with a slow remote |
| B8 | RISK | Codex | 2 | GitHub's ref-lock wording is unchecked, so S7's message on GitHub is unsupported | fixed, locally_verified | S7 qualified |
| B9 | RISK | Codex | 2 | A15 carried open | see A15 | — |
| B10 | RISK | Melious | 2 | Site B's hook was left out of the variable clearing | fixed, locally_verified | D3.3 |
| B11 | RISK | fresh-eyes | 2 | A mktemp stub failing every call stops at the first, so the worktree's mktemp is never failed | fixed, locally_verified | S15: each call in turn, with a sentinel file |
| B12 | RISK | fresh-eyes | 2 | In worktree mode a half-edited or outdated `ship.sh` from any branch could publish | fixed, locally_verified | D2 "The publishing script", S16 |
| B13 | RISK | fresh-eyes | 2 | A hard kill leaves the lock; a reused process id reads as alive, with no way out named | fixed by B1's cut, locally_verified | the message gives path and command; S8 |
| B14 | RISK | fresh-eyes | 2 | S9 and S10 depend on timing inside the pre-push gate; S10's signal could reach a real publish | fixed, locally_verified | "How it is tested": marker files; own process group, checked |
| B15 | RISK | fresh-eyes | 2 | The hooks' variable clearing has no test | fixed, locally_verified | D3.1: the hook's test pushes from a linked worktree |
| B16 | NIT | Melious | 2 | D2's list of what applies in today's mode was ambiguous | fixed, locally_verified | D2 intro; today's mode takes no lock |
| B17 | NIT | fresh-eyes | 2 | A liveness check cannot tell a refused check from a missing process | fixed, locally_verified | the lock rule no longer depends on it; the message says "seems to be running" |
| B18 | NIT | fresh-eyes | 2 | git prints the shared git folder relative in a primary checkout; the trap's removal needs force twice | fixed, locally_verified | D2 |
| B19 | NIT | fresh-eyes | 2 | Name `npm ci`; every publish then needs the registry or a warm cache | fixed, locally_verified | D2 "The install" |
| B20 | NIT | fresh-eyes | 2 | Site B's test copy cannot run S6; its marker was unstated | fixed, locally_verified | D3.3 |
| B21 | NIT | fresh-eyes | 2 | A dev server makes the gate fail only on the gate's own port | fixed, locally_verified | "Checked" reworded |
| B22 | NIT | fresh-eyes (outside scope) | 2 | This trail's round 1 count said 9 NIT for 7 rows | fixed | round 1 row |
| B23 | NIT | fresh-eyes (outside scope) | 2 | A fetch can start git's own housekeeping, which prunes records older than three months | fixed, locally_verified | host: `man git-fetch`, auto-maintenance on by default; D2 "Leftovers" |

Waivers and deferrals: none yet.

Follow-ups: none open (B22 and B23 were fixed).

Notes: Raw reviewer output is kept off this public repo because it names private sites, as for the 2026-10-18 plan gate; it is on the maintainer's machine with this group's session notes. Before round 1 the owner settled O1 to O3 and the depth (High) in chat on 2026-10-21. N4 and N5 were merged into A3 and A6. Round 2's lock fix is a cut (kind: lock, which earned rounds 2 and 3): automatic takeover of a stale lock was removed and replaced by a strict rule (any existing lock stops the run; only the run that took a lock removes it).
