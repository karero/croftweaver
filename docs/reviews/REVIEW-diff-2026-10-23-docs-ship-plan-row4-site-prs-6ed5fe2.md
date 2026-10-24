# DIFF review — branch docs/ship-plan-row4-site-prs — the ship-from-worktree plan's row 4 records the three site pull requests
Base `fc92406a` (the head of karero/croftweaver#386, which this branch is stacked on) · depth: Normal (a plan file is never Light) · verdict: CLEAN · authority used: WORKTREE-WRITE, BRANCH-COMMIT, POST — atom A, this session made the branch, its worktree and the pull request

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | 6ed5fe2d | `git diff fc92406a..6ed5fe2d -- docs/reviews/SKILL-PLAN-ship-from-worktree.md` | codex-cli 0.164.0 (gpt-6.1-sol, read-only); GLM 5.3 on melious; fresh-eyes Sonnet sub-agent | codex 136 s, 44,841; melious 34 s, 3,292; fresh-eyes 240 s, 118,722 | 0 / 2 / 4 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| R1 | RISK | fresh-eyes | 1 | Sites A and C had trail commits not yet pushed when it looked | fixed by pushing; Site C pushed at `a518f8e`. Site A's push is held by its own pre-push gate while another checkout holds its test port; the pull request text says so | `git ls-remote` |
| R2 | RISK | fresh-eyes | 1 | the PR numbers and "open, not merged" cannot be checked offline | refuted | `gh pr view` on each: OPEN |
| R3 | NIT | codex | 1 | the plan's opening said the site copies "are not" built | fixed, locally_verified | opening line reworded |
| R4 | NIT | GLM 5.3 | 1 | `pr<N>` placeholder in the trail reference | fixed, l_v | the three file names |
| R5 | NIT | fresh-eyes | 1 | D3 item 5 cited for merging and shipping too | fixed, l_v | item 5 cited for the setting only |
| R6 | NIT | fresh-eyes | 1 | `ec46c16` is comment-only in ship.sh but also edits the trail, and was not re-verified | fixed, l_v | row says both |

Stop condition (a2): no BUG, and no RISK needing a fix that changes what runs; the NITs are fixed, closing edits not externally re-verified.
Follow-ups: none.
