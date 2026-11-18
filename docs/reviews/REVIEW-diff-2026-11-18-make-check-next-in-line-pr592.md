# DIFF review — branch claude/make-check-next-in-line-build-fd8144 — the next-in-line entry for `make check` (PR 592)

Base `817a63f6` · depth: Normal (a script every session runs before a push; no user data, auth or deploy path) · verdict: CLEAN after round 3 · authority used: WORKTREE-WRITE, BRANCH-COMMIT and PUSH of this branch.
This session (the next-in-line build, started by the coordinator for the Croftweaver manager) created the worktree and the branch. The plan it builds is `docs/reviews/SKILL-PLAN-make-check-next-in-line.md` (PR 591); the plan left one question to this review: that the entry flock is held from the read to the emptying.

Seats (REVIEW-RULES): rounds 1 and 2 the pair, Codex plus GLM 5.3 on melious, as the brief said; round 1 also a fresh-eyes Sonnet sub-agent (read-only). Round 3 Codex alone, by choice: it checked a 50-line delta of test code and one message line, and GLM had verified the same fixes' findings in round 2.
Gate id 20261118T152020Z-78098.

Artifact: round 1 `git diff 817a63f6...1dff9c41 -- . ':(exclude)docs/reviews/'`; rounds 2 and 3 the delta since the head the earlier round saw, with `--base`, `--verify` and `--evidence`. Evidence: the full test records, the mutation results and the guard runs, each with the command and the head.

| Round | Head | Artifact | Reviewers | tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `1dff9c41` | full | Codex (gpt-6.1-sol, medium, read-only); melious (glm-5.3); fresh-eyes (Claude Sonnet, read-only) | codex 52,929; melious 53,012; fresh-eyes 160,501 | 1 / 2 / 10 after dedup |
| 2 | `9e367286` | delta, verify of 1-13 | Codex (medium); melious (glm-5.3) | codex 60,180 (144 s); melious 38,134 (372 s) | 0 / 1 / 3 |
| 3 | `8891884b` | delta, verify of 14-17 | Codex (medium) | codex 37,529 (76 s) | 0 / 0 / 0 |

Gate total after round 3: 402,285 tokens logged by the script, fresh-eyes included.

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| 1 | BUG | Codex | 1 | N7 asserted only `took >= 4`, so a 20 s wait passed. | fixed in `9e367286` | The cap is now 15 s (18 s from round 3); mutation "wait loop 100 to 400 tries" fails all six N7 cases (took 22-23 s). |
| 2 | RISK | GLM, fresh-eyes | 1 | The lock's `$ENV{CROFTWEAVER_CHECK_LOCK}` leaked into the guards' environment. | fixed in `9e367286` | `local` around the one `system` call; new case N8 records what the stub guard sees. Mutation "drop local" fails N8. |
| 3 | RISK | Codex | 1 | The docs row said "or delete it", but an unlinked entry breaks the flock. | fixed in `9e367286` | The row says run `check_next.sh clear` and why not delete; check `emptied` in N1 and N5. Mutation `unlink` in `empty_entry` fails N1. |
| 4 | NIT | GLM | 1 | `gate` is not in the usage line. | refuted | The header marks it internal; a bare `gate` by a person follows the lock's own rules for that session. |
| 5-13 | NIT | GLM, fresh-eyes | 1 | A reused pid in N5; a 4096-byte read of the old lock file; two messages when the gate exits 1; no N4 case reaching `$l[4] eq ""`; `no_entry` passes on a missing file; a stale step name in `clean.yml`; "only reads and empties" in the docs; the `set` text with no run going; mutation evidence run against the old N7 holder. | fixed (table in the round 2 brief) | A fixed pid check with `ps -p`; 16384 bytes; the lock's line only when the gate could not run; a fifth-line-without-newline case; `emptied`; the step name; "creates it empty, reads it and empties it"; "10 minutes from now, or from the end of the current run if one is running"; a full test run after the holder got autoflush (39 ok). |
| 14 | RISK | Codex | 2 | N5's `emptied` after `clear` ran after `mk`, whose gate recreates the file, so a clear-only unlink passed. | fixed in `8891884b` | `emptied` is captured right after `clear`. Mutation `unlink $entry` in the clear branch fails N5 clear. |
| 15 | NIT | GLM | 2 | A gate ending with an odd exit code (not 1, 75, a signal) left `make check` with a bare `Error 1`. | fixed in `8891884b` | The lock prints its line unless the gate exited 1. Codex ran the condition on exits 0, 1, 2, 75, 127 and SIGTERM in round 3. |
| 16 | NIT | GLM | 2 | N5's replace case still used `no_entry`. | fixed in `8891884b` | Now `emptied`. |
| 17 | NIT | GLM | 2 | N7's 15 s cap is tight on a loaded runner. | fixed in `8891884b` | 18 s; the 20 s-wait mutation still fails (22-23 s). |

Mutations, all run by hand in a scratch copy of the Makefile and the three scripts with one exact-string replacement each, then the whole lock test:
- the plan's four: no gate call (fails N1, N2, N3, N4, N5, N7); grace counted from the set time only (fails N2); no self-refusal in `set` (fails N5); no `ended` write (fails N6);
- round 2: wait loop to 400 tries (N7); environment assignment without `local` (N8); `unlink` in `empty_entry` (N1);
- round 3: `unlink` in the clear branch (N5 clear); wait loop to 400 tries against the 18 s cap (all six N7 cases).

The plan's question about the flock: Codex and GLM read the gate in rounds 1 to 3 and raised nothing against it. `check_next.sh gate` takes the flock, reads, decides and empties in one Perl program, and `set` and `clear` use the same one.

Not checked: the claim that the desktop app's id is the same in a session's shell and in the commands it starts (the plan's step 3, "checked on 18 Nov", with its limit named there); the built zip's contents beyond the `check_package_scripts.sh` guard (it lists `check_next.sh`). UNVERIFIABLE entries: about 9 asked over three rounds, none confirmed as a finding. `make check` itself is run under the lock before the merge; its result is on the PR.
