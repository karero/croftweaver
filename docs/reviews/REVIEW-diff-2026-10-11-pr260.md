# DIFF review — PR #260 — docs: after 0.30, close the release-note rows, mark the forms decision reversed, record two waivers
Base `067adcb` · depth: Light (tracker rows, a decisions row and a review record; nothing anyone runs, nothing an agent loads as instructions) · verdict: CLEAN · authority used: POST AUTHORITY — atom A (this session opened #260); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch); GATED-THIS-DIFF — atom A (the chain below)

Light gate: Codex alone at medium effort, the owner's standing choice for a diff of prose no one runs. One round, and one more because round 1 found a BUG.

| Round | Head | Artifact | Reviewer: CLI version, model, effort, sandbox | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `f28696e` | full: `origin/main...f28696e`, 3 files (`docs/reviews/REVIEW-diff-2026-10-11-pr257.md` included, since it is part of the change) | codex-cli 0.162.1, gpt-6.1-sol, medium, read-only | 203 s / 73,835 | 1/3/0 |
| 2 | `3763dcc` | delta `f28696e..3763dcc`, with round 1's dispositions (`--verify`) | same | 75 s / 26,703 | 0/0/0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| P1 | BUG | codex | 1 | #257's trail, row F4: the reason said the case needs a rival term longer than the window; a three-word rival with window 3 shows it too | fixed — externally_reverified (round 2) | `3763dcc`: "reaches beyond the words collected for this fact's window"; codex reproduced the case on this head and on `c495d93` |
| P2 | RISK | codex | 1 | The three row closures rest on release-note text that is not in the checkout | refuted | the published body of v0.30 holds each required line once: "compare my PUBLISHING.md and SETUP.md with the latest template"; "as MISSING" and the `verify` entry and `pre-push` hook sentence; "bring the merging rule in my AGENTS.md up to date", "so Claude Code asks at each merge unless", "the person still presses the button", "§7 replaces the old bullet" |
| P3 | RISK | codex | 1 | Row for #255: "pins the merge to the commit it checked" has no traced support for `--match-head-commit` | no change | the sentence is #255's, reviewed there; this change sets only the row's status |
| P4 | RISK | codex | 1 | Row for #255: "approval at each merge" depends on the effective permissions | no change | as P3; the published notes carry the limit, and #258's trail lists it as W3 |

4 findings (1 BUG in a record sentence, 3 RISK) in 2 rounds: 1 fixed, 1 refuted, 2 unchanged. No waiver.

Waivers recorded by this change, for #257: the owner's words of 2026-10-11 are quoted in that trail.

Notes:
- The BUG was a sentence in a review record, not code that runs, so the gate stayed Light.
- The commit that adds this file changes nothing else; the stamp names it, and the reviewed scope is the one at `3763dcc`.
