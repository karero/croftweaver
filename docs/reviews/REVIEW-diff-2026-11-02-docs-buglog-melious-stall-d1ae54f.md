# DIFF review — branch docs/buglog-melious-stall — a BUGLOG row: a slow Melious stream holds the review round open
Base `b05eef97` · depth: Light (one BUGLOG row, prose no one runs) · verdict: CLEAN · authority used: WORKTREE-WRITE, BRANCH-COMMIT, POST — this session made the branch, its worktree and the pull request

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | d1ae54f7 | `git diff b05eef97..d1ae54f7` plus an evidence file of the author's reads (runs.tsv, transcripts, the two kept raw replies, the script) | codex-cli 0.166.0 (gpt-6.1-sol, effort medium, read-only); Light default seat | codex 96 s, 34,057 | 2 / 1 / 0 |
| 2 | 25a2fe97 | `git diff b05eef97..25a2fe97`, `--verify` round 1, the same evidence plus READ 5 | as round 1 | codex 76 s, 28,737 | 0 / 1 / 0 |
| re-gate | 7cf6f4d9 | `git diff b05eef97...7cf6f4d9`, `--verify` round 2, the same evidence | as round 1 | codex 83 s, 20,285 | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| B1 | BUG | codex | 1 | "up to an hour" states a ceiling the code does not enforce: `MELIOUS_API_TIMEOUT` overrides it, and one run took 4,105 s | fixed, externally_reverified (r2) | the row says "an hour or more", names the 3,600 s default and its variable, and the 3,949 and 4,105 s runs |
| B2 | BUG | codex | 1 | "the seats run at once" omits the ollama fallback path, where Melious starts after ollama, so the subtraction need not measure the real wait | fixed, externally_reverified (r2) | the row names both paths and calls 4.0 h a floor; READ 5: 18 of the 31 rounds also ran ollama |
| R1 | RISK | codex | 1, 2 | the cause (provider slowed, then dropped the streams) is stated without a connection trace | fixed, externally_reverified (re-gate) | the row says "A guess, not traced" |

Stop condition: Light, one round plus one for the BUGs; round 2 found no BUG, and its RISK was a wording fix, re-gated clean.
Follow-ups: none from the review. The row's own fix idea (a speed floor, after measuring good runs) is the row.
Notes: Codex alone is the Light default (REVIEW-RULES.md); no second seat is owed.
