# DIFF review — README and WHAT-THE-SKILLS-RUN: skills.sh lists the suite under the new name and forwards the old one

Base `f4eb2ab` · depth: Light (prose for people: one README sentence and one bullet of a docs page; no code, no instructions an agent loads) · verdict: CLEAN · authority used: WORKTREE-WRITE, BRANCH-COMMIT and POST — atom A (this session's worktree, branch and pull request)

Data check: no key, token or password. Destination: Codex, the owner's OK in chat on 2026-10-14 ("Yes, Codex + melious (Recommended)"), session-scoped.

| Round | Head | Artifact | Reviewer | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `9544440` | full: `f4eb2ab...9544440` (README), with the curl observations as context | codex-cli 0.162.1, medium, read-only | 63 s / 21,807 | 0/0/1 |
| Confirmation (not a round) | `fdb7564` | delta `9544440..fdb7564` (the NIT's fix) | codex, medium | 35 s / 31,224 | 0/0/0 |

N1 (NIT, Codex): `docs/WHAT-THE-SKILLS-RUN.md` described the listing as of a check earlier the same day (old name, 29 skills, no new page), opposite to the README. Fixed in `fdb7564`: the bullet says that was before the install under the new name, and what followed.

Observed on 2026-10-14 with curl: https://skills.sh/karero/website-builder ends at https://www.skills.sh/karero/croftweaver (200), which shows 37 skills and 194 total installs. The install under the new name ran that day with `skills` 1.7.2, telemetry on, on the owner's word.
