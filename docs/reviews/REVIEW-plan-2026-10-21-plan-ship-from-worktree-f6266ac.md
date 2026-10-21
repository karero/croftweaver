# PLAN review — branch plan/ship-from-worktree — publish from a throwaway worktree (`SKILL-PLAN-ship-from-worktree.md`)

Base `6681e7be` · depth: High (deploy code that publishes to live sites and deletes folders) · verdict: OPEN · authority used: WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch). No PR: POST AUTHORITY and GATED-THIS-DIFF do not apply.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `f6266ac8` | full | Codex CLI 0.163.0, gpt-6.1-sol, config effort, read-only · Melious HTTP API, glm-5.3, text only · fresh-eyes sub-agent, claude-opus-5-5, read-only by instruction | Codex 627 s, 91,452 · Melious 335 s, 24,762 · fresh-eyes 1,180 s, 250,687 | 7 / 9 / 9 after merging duplicates (Codex 2/2/0, Melious 0/2/3, fresh-eyes 4/7/8; A11 raised from RISK to BUG on the host's reproduction). Unverifiable entries: Codex 5 groups, Melious 6, fresh-eyes 4; 2 confirmed by the host and became A7 and A11 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | BUG | Codex, Melious (NIT), fresh-eyes | 1 | The busy check scanned worktrees, then created one: two runs could both pass | fixed, locally_verified | D2 "One publish per clone": atomic folder lock before the fetch; residual race named, argued safe (no force push) |
| A2 | RISK | Melious, fresh-eyes | 1 | Leftovers matched "under the temp folder" never match (`/private/var` vs `/var`; TMPDIR differs) | fixed, locally_verified | D2 "Leftovers": match the name wherever the folder is |
| A3 | BUG | Codex; fresh-eyes NIT | 1 | "Per-checkout" setting is wrong: linked worktrees share the clone's config; a global value could switch a fresh clone on | fixed, locally_verified | D1: clone config, shared on purpose, read from it only |
| A4 | RISK | Codex | 1 | Today's mode switching to `origin/main`'s id could push an untested commit when `main`'s upstream is elsewhere | fixed, locally_verified | D2 "The commit id": today's mode keeps its own checked commit |
| A5 | RISK | Codex; Melious (unverifiable) | 1 | The gate claim rests on a relative hooks path; wiring can fail and exit 0 | fixed, locally_verified | D2 "The gate": any other value announced before the push; all three sites store `scripts/hooks` (fresh-eyes, `git config --show-origin`) |
| A6 | RISK | Melious; fresh-eyes NIT | 1 | `GIT_DIR` reaches gate steps from a linked worktree; only the plan's own test cleared it | fixed, locally_verified | D2 "The hook's variables", D3: hooks clear git's own list (`git rev-parse --local-env-vars`); host saw `GIT_DIR` in a linked-worktree hook only |
| A7 | BUG | fresh-eyes; Codex (unverifiable) | 1 | Production moving during the gate gives `! [remote rejected] … (failed to update ref)`; the classifier says "can't name"; S7 promised "production moved" | fixed, locally_verified | host reproduction, stock git 2.33; D3.1 adds the arm with a stock-git fixture; GitHub's wording unchecked |
| A8 | BUG | fresh-eyes | 1 | Today's messages say "still safely on 'main'", false in worktree mode | fixed, locally_verified | D2 "The messages"; S2, S4, S5 |
| A9 | BUG | fresh-eyes; Melious NIT | 1 | "The shared folder is neither read nor changed" is wrong; plain `git status` rewrites the index | fixed, locally_verified | host: index unchanged with optional locks off, rewritten without; D2 "What the run touches" |
| A10 | BUG | fresh-eyes | 1 | The gate-step git audit missed Site C's test config (`rev-parse --show-toplevel`) | fixed, locally_verified | "Checked" bullet corrected |
| A11 | BUG | Codex (unverifiable), fresh-eyes (RISK) | 1 | A repo-wide prune drops a worktree whose folder is only away, with its HEAD, index and reflog | fixed, locally_verified | host: after prune, a commit made there was reachable from nothing; D2 "Leftovers": never prune, remove our own by path |
| A12 | RISK | fresh-eyes | 1 | A terminate to the script alone runs the trap while push and gate go on; the S10 test as worded could not deliver an interrupt | fixed, locally_verified | host: trap at once, exit 143, child finished 3 s later (bash 3.2, 5.3); D2 "The exit trap", S10 |
| A13 | RISK | fresh-eyes | 1 | The mktemp guard cannot test ship.sh (its probe runs outside a git repo) | fixed, locally_verified | D3.1; S15 |
| A14 | RISK | fresh-eyes | 1 | The real-git test would pick up the machine's or CI's git settings; runs on Windows too | fixed, locally_verified | "How it is tested"; host: `git init -b main` on 2.33 |
| A15 | RISK | fresh-eyes | 1 | One test port per site: another session's test run or preview fails the gate | open — owner: waive as a stated limit, or bring a per-checkout port in | D2 "Known limit" |
| A16 | RISK | fresh-eyes | 1 | "Push them" is wrong where pushes to `main` are refused | fixed, locally_verified | D1 reworded |
| N1 | NIT | fresh-eyes | 1 | Exit trap under stop-on-error can skip steps and flip a success | fixed, locally_verified | D2 "The exit trap" |
| N2 | NIT | fresh-eyes | 1 | A leftover left locked needs removal forced twice | fixed, locally_verified | host 2026-10-20: a locked worktree needs force twice |
| N3 | NIT | fresh-eyes | 1 | A refused liveness check reads like a dead process | fixed, locally_verified | D2: refused counts as alive |
| N6 | NIT | fresh-eyes | 1 | The CDPATH guard does not run ship.sh or its test | fixed, locally_verified | D3.1 |
| N7 | NIT | fresh-eyes | 1 | The script that runs is the folder's copy; the test pins the old push command | fixed, locally_verified | D2, "How it is tested" |
| N8 | NIT | fresh-eyes | 1 | Site B's install only adds time and a failure path | fixed, locally_verified | D3.3 |
| N9 | NIT | Melious | 1 | Any `exec` anywhere defeats the trap | fixed, locally_verified | D2, test |

Waivers and deferrals: none yet.

Follow-ups: none yet.

Notes: Raw reviewer output is kept off this public repo because it names private sites, as for the 2026-10-18 plan gate; it is on the maintainer's machine with this group's session notes. Before round 1 the owner settled O1 to O3 and the depth (High) in chat on 2026-10-21. N4 and N5 were merged into A3 and A6.
