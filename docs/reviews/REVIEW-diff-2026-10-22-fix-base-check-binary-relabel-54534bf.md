# DIFF review — fix/base-check-binary-relabel — refuse a text record relabelled as binary; BUGLOG row for --local-only

Base `9acc3b97` · depth: Normal (the logic of a guard script, which the owner's rule never puts at Light; no login, money, user data or deletion, so not High) · verdict: OPEN (round 1 fixed locally; round 2 owed) · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree and the branch); POST AUTHORITY: none yet (no PR)

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `54534bfe` | full since `9acc3b97`, less `docs/reviews/` (15 KB) | codex-cli 0.163.0, gpt-6.1-sol, effort high (config), read-only · Melious glm-5.3, HTTP API, text only · fresh-eyes: Claude Code sub-agent, Sonnet, read-only by instruction | codex 329 s, 66,546 · melious 536 s, 32,168 · fresh-eyes 400 s, 146,130 | 2/3/3 raw (codex 1/2/0, melious 0/1/2, fresh-eyes 1/0/1); 2/1/2 after dedup |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| D1-01 | BUG | fresh-eyes; codex, melious as RISK | 1 | git -M's own diff of a binary file renamed to a text one is refused (by design: its new text is hidden), but the printed remedy used -M too and made the same diff again: a dead end | fixed, locally_verified | the remedy uses `--no-renames` when a mismatch reads "the diff marks it binary"; repository 3 in `test_base_check.sh` makes the rename with `git diff -M`, expects the refusal, runs the printed remedy and expects that diff to run; with the remedy fix taken out, its two remedy checks fail. Invariant: a refusal's printed remedy makes a diff that passes. Checked on git 2.33: `--no-renames` also overrides `diff.renames=copies` |
| D1-02 | BUG | codex | 1 | The comment said a record marked binary shows the reviewers "no content", but a `GIT binary patch` record carries an encoded body | fixed, locally_verified | "no readable lines", in the reader and the test comment |
| D1-03 | RISK | codex | 1 | The BUGLOG row's fix took the window `ollama show` lists to be the window the model serves | fixed, locally_verified | the row's fix now measures first (a marker line at the prompt's start, asked back), then refuses or sets `num_ctx` by the window measured |
| D1-04 | NIT | fresh-eyes, melious | 1 | No test made the deletion branch (old side) refuse | fixed, locally_verified | T5 relabels the deleted `del.txt` as binary and expects the refusal naming it |
| D1-05 | NIT | melious | 1 | The script's BASE CHECK header did not say only the new side is checked | fixed, locally_verified | "on its new side (its old side, for a deletion)" |

Unverifiable entries: melious asked 4 (that `new.txt` exists at HEAD and `bin.dat` changes; that T4's full diff is asserted to run; that git's patch sets the binary flag from `Binary files … differ`; ollama's window), fresh-eyes 2 (ollama's window; `.gitattributes` binary settings), codex 0 beyond its two RISKs; none confirmed as a finding: the fixture lines, `rc_is t4 0` and the parse regex are in the files and the suite passes; the ollama claim is the row's own "Not checked"; both diffs are read in the same repository with the same attributes.

Waivers and deferrals: none.
Follow-ups: none yet.
Notes: substantive BUG in round 1: D1-01 (the remedy's dead end); D1-02 is comment wording.
