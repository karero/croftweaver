# DIFF review — fix/base-check-binary-relabel — refuse a text record relabelled as binary; BUGLOG row for --local-only

Base `9acc3b97` · depth: Normal (the logic of a guard script, which the owner's rule never puts at Light; no login, money, user data or deletion, so not High) · verdict: CLEAN (2026-10-22): no BUG open, every RISK fixed; round 2 clean · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree and the branch); POST AUTHORITY: none yet (no PR)

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `54534bfe` | full since `9acc3b97`, less `docs/reviews/` (15 KB) | codex-cli 0.163.0, gpt-6.1-sol, effort high (config), read-only · Melious glm-5.3, HTTP API, text only · fresh-eyes: Claude Code sub-agent, Sonnet, read-only by instruction | codex 329 s, 66,546 · melious 536 s, 32,168 · fresh-eyes 400 s, 146,130 | 2/3/3 raw (codex 1/2/0, melious 0/1/2, fresh-eyes 1/0/1); 2/1/2 after dedup |
| 2 | `ea8fea10` | delta since `54534bfe` (`--base 54534bfe`), `--verify` with round 1's rows | codex-cli 0.163.0, gpt-6.1-sol, effort medium, read-only · Melious glm-5.3, HTTP API, text only | codex 67 s, 45,347 · melious 427 s, 28,769 | 0/0/2 (codex 0/0/0, melious 0/0/2); every round-1 fix confirmed by both |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| D1-01 | BUG | fresh-eyes; codex, melious as RISK | 1 | git -M's own diff of a binary file renamed to a text one is refused (by design: its new text is hidden), but the printed remedy used -M too and made the same diff again: a dead end | fixed, locally_verified | the remedy uses `--no-renames` when a mismatch reads "the diff marks it binary"; repository 3 in `test_base_check.sh` makes the rename with `git diff -M`, expects the refusal, runs the printed remedy and expects that diff to run; with the remedy fix taken out, its two remedy checks fail. Invariant: a refusal's printed remedy makes a diff that passes. Checked on git 2.33: `--no-renames` also overrides `diff.renames=copies` |
| D1-02 | BUG | codex | 1 | The comment said a record marked binary shows the reviewers "no content", but a `GIT binary patch` record carries an encoded body | fixed, locally_verified | "no readable lines", in the reader and the test comment |
| D1-03 | RISK | codex | 1 | The BUGLOG row's fix took the window `ollama show` lists to be the window the model serves | fixed, locally_verified | the row's fix now measures first (a marker line at the prompt's start, asked back), then refuses or sets `num_ctx` by the window measured |
| D1-04 | NIT | fresh-eyes, melious | 1 | No test made the deletion branch (old side) refuse | fixed, locally_verified | T5 relabels the deleted `del.txt` as binary and expects the refusal naming it |
| D1-05 | NIT | melious | 1 | The script's BASE CHECK header did not say only the new side is checked | fixed, locally_verified | "on its new side (its old side, for a deletion)" |
| D2-01 | NIT | melious | 2 | The script picks the remedy by matching the reader's mismatch text, with no shared constant, so a reworded message would bring the dead end back | refuted | not silently: repository 3 checks the refusal text ("t.txt: the diff marks it binary, but git shows its content") and that the printed remedy holds `--no-renames`, so a reword on either side fails the suite (with the switch taken out, those two remedy checks failed) |
| D2-02 | NIT | melious | 2 | The test discards the remedy's stderr, so a failing remedy shows only as a failed run | refuted | a failing remedy leaves an empty diff, which the reader refuses ("no diff --git record", exit 2), so "T4 the printed remedy makes a diff that runs" fails; the existing `t4remedy` case discards stderr the same way |

Unverifiable entries: melious asked 4 (that `new.txt` exists at HEAD and `bin.dat` changes; that T4's full diff is asserted to run; that git's patch sets the binary flag from `Binary files … differ`; ollama's window), fresh-eyes 2 (ollama's window; `.gitattributes` binary settings), codex 0 beyond its two RISKs; none confirmed as a finding: the fixture lines, `rc_is t4 0` and the parse regex are in the files and the suite passes; the ollama claim is the row's own "Not checked"; both diffs are read in the same repository with the same attributes.

Waivers and deferrals: none.
Follow-ups: none.
Notes: substantive BUG in round 1: D1-01 (the remedy's dead end); D1-02 is comment wording. Round 2 found no BUG and no RISK, so the rounds end (stop condition a2). The plan's status row 4 (changed in the first commit, under `docs/reviews/`, which the rounds leave out) and this record are read by the wording pass.

Cost: 2 rounds; 13 findings raw, 7 after dedup (BUG 2, RISK 1, NIT 4): 5 fixed, 2 refuted (D2-01, D2-02); 318,960 tokens logged (fresh-eyes 146,130 of them), 1,759 s of seat time, about 16 minutes of wall clock with each round's seats in parallel. Estimated before round 1 at 100-200k tokens for round 1.
Raw reviewer output: in the PR's review comment (closeout, clerk item 1), not in this file.
