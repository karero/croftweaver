# DIFF review — one site's AI check at a time
Base `89f965b5` · depth: Normal (shipped code in a skill; no user data, login, money or deletion) · verdict: CLEAN (2026-10-18). 2 rounds, 12 findings, no BUG; one round-2 NIT fixed after the last round, not externally re-verified. The record prose (SKILL.md, the BUGLOG row), written after #354 merged, passed a prose-only re-gate and one confirmation; Codex's chain then reached the pushed head through a merge link (clean). One follow-up (X1).

Artifact: `git diff 89f965b5...HEAD -- . ':(exclude)docs/reviews/'`; round 2 the delta since `5f63f1ef`. Plan: `SKILL-PLAN-ai-check-lock.md`, its gate in `REVIEW-plan-2026-10-18-ai-check-lock.md`. Destinations: Codex and melious.ai, as for the PLAN gate. The maintainer's go to build: "Yes, go ahead" (asked in session, 2026-10-18). A first round-1 start was stopped before any seat reported, while that go was asked for. Heads named here from before `1c4f9b41` were folded into that one commit on the maintainer's OK (an earlier commit named the owner's sites), so they are not in the pushed history; the reviewed content is.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `5f63f1ef` | full diff | Codex CLI 0.162.1, gpt-6.1-sol, config effort, read-only · Melious glm-5.3, text only · fresh-eyes sub-agent, sonnet, read-only (ran the tests and three mutations) | Codex 196 s, 62,174 · Melious 320 s, 28,530 · fresh-eyes 189 s, 102,134 | 0 / 2 / 4 after merging duplicates (Codex 0/1/0, Melious 0/1/2, fresh-eyes 0/0/3, one UNVERIFIABLE, the clock, merged into D2) |
| 2 | `93931e51` | delta since `5f63f1ef`, as a verification round (D1 to D6) | Codex (medium) · Melious glm-5.3 | Codex 86 s, 35,411 · Melious 198 s, 16,948 | 0 / 1 / 3 (Codex's RISK re-raises D2 without new evidence; Melious 0/0/3). No BUG, no RISK calling for a fix: rounds end (stop condition a2) |
| prose re-gate (not a round) | `787553da` | delta since the merge of main (`c5c9dee0`): SKILL.md, BUGLOG | Codex (medium) | 60 s, 50,670 | 1 contradiction (P1), fixed |
| confirmation (not a round) | `fd248838` | that fix's delta | Codex (medium) | 34 s, 21,617 | No BUG/RISK/NIT findings |
| merge link (not a round) | `798ef83d` | `merge_link.sh 89f965b5 93931e51 9ce0f906`: E3's fix, the merge of #354, the prose and the BUGLOG number | Codex (medium) | 131 s, 51,614 | No BUG/RISK/NIT findings in scope; one RISK outside scope (X1), a follow-up |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| D1 | RISK | Codex | 1 | T1 got its contention from a 0.5 s delay; a slow start could run the two one after the other | fixed, locally_verified, externally_reverified (round 2) | engine replies wait on a gate opened only once a run's log shows the waiting line; without the lock T1 fails ("0 != 1" waiting lines); 5 runs in a row green |
| D2 | RISK | Melious, fresh-eyes (unverifiable) | 1 | `time.monotonic` not counting sleep had no support in the diff | fixed, locally_verified | docstring cites `time.get_clock_info` and Apple's `mach_absolute_time` page: "this clock does not increment while the system is asleep". Codex re-raised it in round 2 without network or new evidence: refuted on that quote |
| D3 | NIT | Melious | 1 | tests leaned on `env_for` for `GEO_TEST_MODE` | fixed, locally_verified, externally_reverified (round 2) | set in `setUp` |
| D4 | NIT | Melious, fresh-eyes | 1 | a non-numeric `GEO_LOCK_WAIT` raises `ValueError` | refuted | honoured only with `GEO_TEST_MODE=1`; a traceback is the right failure for a broken test setup |
| D5 | NIT | fresh-eyes | 1 | `ai_lock.close()` is not in `try/finally` | refuted | `run()`'s only caller is `main()`, whose result goes to `sys.exit`; an exception ends the process and the kernel drops the lock (T3) |
| D6 | NIT | fresh-eyes | 1 | the plan said T1 used a 1 s delay | fixed, locally_verified | plan's T1 describes the gate |
| E1 | NIT | Melious | 2 | T1's poll would wait out its 30 s if the waiting line were not flushed | refuted | it is flushed (`flush=True` in `_ai_check_lock`); the six tests run in about 8 s; T6 fails if the flush is removed |
| E2 | NIT | Melious | 2 | `STATE["gate"]` is never cleared | refuted | `stub.reset()` in every `setUp` clears all of `STATE` |
| E3 | NIT | Melious | 2 | killed children are never reaped | fixed, locally_verified (not externally re-verified) | `stop()` kills and waits, `458af541`; externally re-verified by the merge link |
| P1 | BUG (contradiction) | Codex | prose re-gate | SKILL.md said the wait is listed under "This run needs attention"; the list holds only "AI check: exit 1", the wait is a ⚠ line above it | fixed, externally_reverified (confirmation) | `fd248838` |
| X1 | RISK | Codex | merge link (outside scope) | on a failing test, cleanup kills the `track.sh` shell but its Python child can live on, holding the lock or calling the stub; older than this change's `stop()` | follow-up | start the children in their own process group and kill the group; not done here

Negative controls, run by hand and not committed: the lock taken out (`ai_lock = None`): T1, T2, T5 and T6 fail; `asks = usable` (ignoring `--engines`): T4 fails; the waiting line not flushed: T6 fails. `make check` and `make test` (387 tests) green at `458af541`.
