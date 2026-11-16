# DIFF review — branch docs/buglog-check-after-merge — BUGLOG header: run the row check after a merge or rebase

Base `c36d4d0e` · depth: Normal (the header names a command sessions run, so it is not Light under
the review rules; no user data, auth or deploy path) · verdict: CLEAN after round 1.
This session (the tool improvement evaluator) created the worktree and the branch, on the owner's
"Add it" to the idea from the small kit sweep before 0.36.

Artifact: round 1 `git diff c36d4d0e...f8f4bdb8`. Gate id 20261116T215103Z-75072.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `f8f4bdb8` | full, merge base with origin's HEAD | Codex alone (gpt-6.1-sol, read-only), the default seat for a Normal DIFF off the High row | codex 77 s, 31,724 | 0 / 0 / 0 |

Codex marked one claim UNVERIFIABLE: that a rebase, too, keeps two versions of an edited row.
Settled by a replay in a throwaway repo (git 2.54.0, `log.md merge=union`): a branch closed row A
while main closed row B and added row C; `git rebase main` exited 0 with no conflict, and the file
held both versions of rows A and B. The small kit sweep's rebases of 2026-11-16 left the same
result in real commits on main (fb255d2c, 484f0edd, each "delete the rows the rebase's union
merge kept twice").

Checks on `f8f4bdb8`: `make check` exit 0 (2,201 ok, 0 FAIL; skips are the Mac's missing `/proc`
cases). After this trail was added: `check_buglog_rows.sh`, `check_clean.sh` and
`check_lf_checkout.sh` again; the full `make check` was not rerun for a trail-only commit.
