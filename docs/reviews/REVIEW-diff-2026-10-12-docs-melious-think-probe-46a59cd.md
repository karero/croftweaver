# DIFF review — PR #274, branch `docs/melious-think-probe` — R-MELIOUS-THINK measured on the two models the Melious seat may run
Base `b8daa7e` · depth: Light (one row of the open-findings tracker and this trail: prose no agent loads as instructions and no person runs) · verdict: CLEAN at `3ef8557`: 1 round and two confirmations, 3 findings (1 BUG, 2 RISK), all fixed; one follow-up · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree and the branch); POST AUTHORITY — atom A (this session opened PR #274) and atom B (the owner, 2026-10-12, to the offer to push the branch, open the PR and post the eight replies as its comment: "push it")

Light gate, by the owner's standing rule for prose-only diffs: Codex alone, one round, one more only if it finds a BUG. It found none.

Data consent: the owner asked for this measurement on 2026-10-12 ("then this: The think-tag test on GLM 5.3 and Flash", including Flash through the new script against the real Melious). What went to Melious was a nine-line made-up plan, eight times; what went to Codex was the tracker row's diff and those plans. No secret in either; the request bodies carry no key (the script sends it as a header).

| Round | Head | Artifact | Reviewer: CLI version, model, effort, sandbox | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `46a59cd` | full: `origin/main...46a59cd`, one file, plus the two plans as context | codex-cli 0.162.1, gpt-6.1-sol, effort medium, read-only | 119 s / 50,053 | 0/2/0 |
| not a round: confirmation of T1's fix | `3356c0b` | delta `46a59cd..3356c0b`, the tracker row, `--verify` | same | 172 s / 51,433 | 1/0/0 (T2 re-raised) |
| not a round: confirmation of T3's fix | `3ef8557` | delta `3356c0b..3ef8557`, the tracker row, `--verify` | same | 80 s / 30,637 | 0/0/0 |

| id | Sev | Source | Finding | Status | Evidence |
|---|---|---|---|---|---|
| T1 | RISK | Codex | The row stated a mechanism (tags not seen as typed, text missing from what the model reviewed) that the replies do not establish; one failing run's reasoning holds the word | fixed `3356c0b`, externally_reverified by the first confirmation: the row says what the reviews said, that the cause is not established, and that the runs neither confirm nor rule out the rewrite tried earlier | the diff |
| T2 | RISK | Codex | The measurement's support was only in files git ignores | fixed: the eight replies and the two plans are in a comment on PR #274, https://github.com/karero/croftweaver/pull/274#issuecomment-6131520825, which the row links; the request bodies are not committed, because they hold the tags, which this repo's files avoid. Codex confirmed the link landed; that the comment holds what the row says was checked by the author (PR open, ten collapsed sections), not by Codex, which has no network | the comment |
| T3 | BUG | Codex | The fix to T1 said both failing glm-5.3-flash reviews denied "tags and animal"; one denies tags and calls the codename undefined | fixed `4300a86`, externally_reverified by the second confirmation | `flash-tagged.out`, `flash-tagged3.out` |

What Codex verified against the captured runs: the counts (glm-5.3 3 of 3, glm-5.3-flash 1 of 3, both controls), that each tagged request body holds the tag pair around the word, that the saved reviews match the raw streams, and that every run ended `reviewers: melious OK`.

The measurement itself, for the record: `MELIOUS_MODEL=<model> independent_review.sh <plan> --plan --seat melious --depth <normal for glm-5.3, light for glm-5.3-flash>`, the installed script at `4e5ff23`, 2026-10-12, eight runs, 4 to 29 s and 995 to 1,845 tokens each.

Follow-up, for the owner: the row's opening sentence, written on 2026-10-06 and not part of this change, states a provider mechanism ("reads think tags … as reasoning markers") that no capture establishes. Codex raised it in both confirmations as outside their scope.

After the gate: `main` had moved to `08e1275` and the repository merges only an up-to-date branch, so `origin/main` was merged in as `8a69539`, no conflict. `main` changed neither of this change's two files, and `git diff origin/main 8a69539` is byte-identical to `git diff b8daa7e 1d8febc`, the diff the seat saw plus this trail (compared with `cmp`). No re-gate; the stamp moves to the head that records this.

`main` moved once more (`4257b23`, PR #268) while the checks ran; merged in again as `23cf35a`, no conflict, and `git diff origin/main 23cf35a` is byte-identical to `git diff 08e1275 0351b1e` (`cmp`). No re-gate.

