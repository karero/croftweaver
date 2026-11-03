# DIFF review — branch docs/review-evidence-other-repos — a READ covers another repository's code, quoting whole functions
Base `98a0ef9d` · depth: Normal (SKILL.md is an instruction file agents load, never Light) · verdict: CLEAN · authority used: WORKTREE-WRITE, BRANCH-COMMIT — this session made the branch and its worktree

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | 901212ff | `git diff origin/main...901212ff` plus an evidence file of the author's reads (a backend trail where a client claim came back in two re-gates, a count of such trails, the 25e phrase checks) | codex-cli (gpt-6.1-sol, read-only); melious glm-5.3, which failed at 782 s (curl exit 56, reply cut off) and was rerun once | codex 67 s, 28,816; melious rerun 107 s, 8,577 | 0 / 1 / 1 |
| 2 | 88ff6d31 | `git diff 901212ff..88ff6d31`, `--verify` round 1, the same evidence | Codex + melious glm-5.3 | codex 83 s, 18,483; melious 75 s, 10,268 | 0 / 0 / 1 |
| re-gate | 411bc150 | `git diff 88ff6d31..411bc150`, `--wording-pass --verify` round 2, the same evidence | Codex | codex 63 s, 12,671 | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| R1 | RISK | glm-5.3 | 1 | whole-function quotes cannot show that no other caller exists, the rule's own first example | fixed, externally_reverified (r2) | the sentence now asks for the search that found every caller; `references/claims-sweep.md` already asks for that list |
| N1 | NIT | glm-5.3 | 1 | "code in another repository" is not out of reach in every run | fixed, externally_reverified (r2) | "a client app's code in a repository the seats were not given" |
| N2 | NIT | glm-5.3 | 2 | the caller search's scope is unstated | fixed, externally_reverified (re-gate) | "over every repository a caller can live in" |
| N3 | NIT | glm-5.3 | 2 | the evidence calls both backend re-gates test or comment deltas, though re-gate 2 carried evidence | refuted | re-gate 2's head was a commit of test and comment fixes; the evidence file rode along with it. No sentence of the diff rests on it |

Checks: `make check` passed at 901212ff (0 failures; skips only for Perl::MinimumVersion and `/proc`, which this Mac lacks); `check_clean.sh` and the three 25e phrases rechecked after each fix.
Stop condition: Normal; round 2 found no BUG or RISK, and its NIT was a wording fix, re-gated clean.
Follow-ups: none.
