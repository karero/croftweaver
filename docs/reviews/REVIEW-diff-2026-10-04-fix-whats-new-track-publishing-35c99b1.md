# DIFF review — branch `fix/whats-new-track-publishing` — whats-new reports drift in PUBLISHING.md and SETUP.md

Base `1a62629` · depth: Normal (changes what `whats-new` reports to every scaffolded site; no user data, no production path) · verdict: **CLEAN; every round ran with one cross-model seat, ollama-cloud being over its weekly limit** · authority used: WORKTREE-WRITE — this session's own worktree, made by the app for it; BRANCH-COMMIT — this session created the branch; POST AUTHORITY — this session opens the pull request; GATED-THIS-DIFF — Codex holds an unbroken chain `35c99b1` → `c9613a2`

**Data release consent** (owner, in this session, quoted verbatim): "Review with the repo's `independent-review` skill (Light is enough if it ends as a comment only; Normal if whats-new behaviour changes)". Normal's seats are Codex and ollama-cloud. The repo has no standing consent; this is session-scoped.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `35c99b1` | full, `1a62629...35c99b1` (`git diff -W`) | codex-cli 0.159.3, gpt-6.1-sol, config effort, read-only — counted by hand (see Notes) · ollama 0.35.1, cloud — FAILED (weekly limit, 429) · fresh-eyes: host-family mid-tier model, read-only sub-agent | codex 245 s, 75 809 · fresh-eyes ~355 s, 159 247 | 0 / 2 / 4 |
| 2 | `c9613a2` | delta since `35c99b1`, with round 1's dispositions | codex, medium, read-only (`--seat codex`; ollama-cloud still over its limit) | 117 s, 39 039 | 0 / 0 / 0 |

Two rounds, 6 findings (0 BUG, 2 RISK, 4 NIT). UNVERIFIABLE entries: round 1 asked 2, the look confirmed 1 (Codex's, which is C1); round 2 asked 2 (records of F1/F4 and of the local test runs), confirmed 0 — see the evidence column.

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| C1 | RISK | codex | 1 | the "SETUP.md is not tracked" comment rested on "no assistant follows it after handoff", which is false: website-qa, website-team-setup, og-images and search-console-setup point into it | fixed — the owner chose to track SETUP.md; locally_verified, externally_reverified (round 2) | `c9613a2`; a scratch site stamped at `1373e28` now lists `templates/SETUP.md` with its 9 upstream commits; the guard fails with the SETUP.md case arm removed |
| F1 | RISK | fresh-eyes | 1 | the coverage guard scans `templates/astro/` only, so dropping a root template from `TEMPLATE_TRACKED` leaves CI green | waived by the owner, 2026-10-05, with a follow-up task | owner: "Waive + follow-up (Recommended)" |
| F2 | NIT | fresh-eyes | 1 | "no assistant follows SETUP.md after handoff" overstated | fixed with C1 — externally_reverified (round 2) | the sentence is gone |
| F3 | NIT | fresh-eyes | 1 | the comment read as if every root template were decided | fixed — externally_reverified (round 2) | "The other root templates have no recorded decision yet." |
| F4 | NIT | fresh-eyes | 1 | a site that re-stamped while the two files were untracked will never be told its copies are behind | fixed outside the diff: the PR description carries a line for the next release notes — locally_verified | PR description |
| F5 | NIT | fresh-eyes | 1 | README's frozen-files line ran to 111 characters | fixed — externally_reverified (round 2) | `README.md:178–179` |

Waivers: F1 — owner, in this session, 2026-10-05: "Waive + follow-up (Recommended)". The gap predates this change: `AGENTS.md` and `content-guide.md` have had the same exposure since they were tracked.

Follow-ups: none from the reviewers. Two tasks offered to the owner: extend the coverage guard to the root templates (F1); make independent-review's parallel-timing test hold under load (it failed `make check` twice on 2026-10-04 at load averages of 80–205 and passed alone; this change does not touch it).

Notes:
- One cross-model seat per round: ollama-cloud hit its weekly limit before round 1. Degraded from the standard pair, not by choice.
- Round 1's Codex reply was a real review (one RISK, eight verified claims) that the script's check rejected as "output is not a review"; counted by hand, as SKILL.md allows.
- The scope moved after round 1: the owner first chose to leave SETUP.md untracked, then chose to track it once C1 showed the premise false.
- The stamped head adds only this trail on top of `c9613a2`: `git diff c9613a2..HEAD -- . ':(exclude)docs/reviews/'` is empty.
- `make check` at `c9613a2`: exit 0, 635 ok lines; 6 pre-push-hook cases skipped because macOS has no `/proc`.
