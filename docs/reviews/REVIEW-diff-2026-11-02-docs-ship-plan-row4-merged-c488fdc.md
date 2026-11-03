# DIFF review — branch docs/ship-plan-row4-merged — the ship-from-worktree plan's row 4 records the three site merges
Base `2eb0b309` · depth: Normal (a plan file is never Light) · verdict: CLEAN · authority used: WORKTREE-WRITE, BRANCH-COMMIT, POST — this session made the branch, its worktree and the pull request

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | c488fdc1 | `git diff 2eb0b309..c488fdc1` plus an evidence file of the author's live queries | codex-cli (gpt-6.1-sol, read-only); fresh-eyes Sonnet sub-agent; advisory: GLM 5.3 Flash on ollama cloud (the script picked it; Flash is for Light only, so it does not count as the second seat). GLM 5.3 on melious was then run and failed: balance empty, so by the owner's rule (2026-10-27) the round stands on Codex alone as the cross-model seat | codex 135 s, 39,454; ollama 95 s, not reported; fresh-eyes 145 s, 90,184 | 0 / 3 / 3 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| R1 | RISK | codex, GLM 5.3 Flash | 1 | "published" in the opening claims more than "the merge is on `production`" shows | fixed, locally_verified | the opening says "on their sites' `production` branches" |
| R2 | RISK | GLM 5.3 Flash (advisory) | 1 | the same word newly covered row 3, a merge into this repository | fixed, l_v | row 3 is "built and merged" again |
| R3 | RISK | codex | 1 | the setting was read without `--local`, while ship.sh reads it with `--local` | refuted | `git config --local --bool --get ship.fromGitHub` printed `true` in all three clones |
| R4 | NIT | fresh-eyes | 1 | same as R1 | fixed, l_v | as R1 |
| R5 | NIT | fresh-eyes | 1 | the row's `production` claim is right; don't tighten it to "live" without a live check | no change | row 4 says only `production` |
| R6 | NIT | GLM 5.3 Flash (advisory) | 1 | `claude/ship-0-22` is named as if it still exists | fixed, l_v | `git ls-remote --heads` finds it in none of the three; the row says it was deleted after the merge |

Stop condition (a2): no BUG, and no RISK needing a fix that changes what runs; the fixes are wording only, closing edits not externally re-verified.
Follow-ups: none.
