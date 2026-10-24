# PLAN review — karero/croftweaver#390 — where the owner of a generated site meets "first draft, not legal advice"
Base `36fdafef` · depth: High (the plan writes legal text a site owner relies on) · verdict: OPEN · authority used: POST AUTHORITY and BRANCH-COMMIT — atom B, the maintainer's request to finish and merge this PR (2026-10-24, relayed by the starting session); WORKTREE-WRITE — atom A, this session created the worktree

Host preconditions: (1) no status table → host RISK H1, fixed before round 1 (table added); (2) four open owner questions → asked before round 1, answered "all as recommended" (2026-10-24), written into the plan's Decisions; (3) no separate spec; (4) no code.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | 97d6bc35 | full plan | codex-cli 0.164.0, gpt-6.1-sol, config effort (high), read-only · melious glm-5.3, text only · fresh-eyes claude-opus-5-5 sub-agent, read-only | codex 315 s, 107,560 · melious 91 s, 13,483 · fresh-eyes 209 s, 144,490 | 2/5/7 (after dedup) |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| H1 | RISK | host | pre | Plan had no per-step status | fixed, locally_verified | `## Status` table, commit 2616c0d3 |
| F1 | BUG | fresh-eyes | 1 | "only in source comments" also cited `SKILL.md:260/:283`, which are §1 Q5's owner-facing analytics/banner lines | fixed, locally_verified | What rewritten; `sed -n 250,290p SKILL.md` shows both lines in Q5's "Tell the owner plainly" |
| F2 | BUG | codex | 1 | "A visible note does not break handoff" contradicts §4's first item (no "not ready to launch" warning) | fixed, locally_verified | Handoff section rewritten; SKILL.md §4 first item quoted |
| F3 | RISK | fresh-eyes, codex | 1 | Clearing steps only in `new-website/SKILL.md`, which a site does not carry | fixed, locally_verified | Steps now in `templates/AGENTS.md` §5 (How 2); SKILL.md §3 copy list omits new-website |
| F4 | RISK | fresh-eyes, melious | 1 | "I use my own texts" deletes the note before the texts are on the page | fixed, locally_verified | How 2: texts first, else record nothing |
| F5 | RISK | fresh-eyes, codex, melious | 1 | Source-prefix guard credited with catching rewording; misses gutted body, comment-wrap, exempt attribute, wrong language | fixed, locally_verified | Guard replaced by a rendered-page test in `placeholders.spec.ts` (How 5), claim narrowed to what it catches; `template-tests.yml` runs that suite |
| F6 | RISK | melious | 1 | Deleting the note on a site with no recorded answer is caught by nothing | fixed, locally_verified | How 5: note or a `legal pages:` README line |
| F7 | NIT | fresh-eyes | 1 | Header/README "test turns red until you do" lines become untrue | fixed | How 1 edits them |
| F8 | NIT | fresh-eyes | 1 | Rule belongs next to AGENTS.md §5's UNFILLED bullet, not §4 | fixed | How 2 |
| F9 | NIT | fresh-eyes | 1 | No-answer default unstated | fixed | How 2 |
| F10 | NIT | fresh-eyes | 1 | "reviewed by a lawyer" line undated | fixed | How 2: every line dated |
| F11 | NIT | fresh-eyes, codex | 1 | Cited trail file did not exist | fixed | this file |
| F12 | NIT | melious | 1 | "starter README's placeholders paragraph" ambiguous | fixed | How 4 names `templates/astro/README.md` |
| F13 | NIT | melious | 1 | `/datenschutz` swap and i18n route untested | fixed | moved into the build's test list (How it is tested) |
| F14 | NIT | melious | 1 | "(judgment, see below)" dangled | fixed | Judgment list has the item |

UNVERIFIABLE asked in round 1: 6 (Playwright totals, croftweaver-site `terms.astro`, scaffold copying, trail, tone/slot rules, drift); confirmed as findings: 1 (trail → F11). The Playwright totals and `terms.astro` stay the plan author's claims; the plan says the runs predate step 5.

Follow-ups: none.
Notes: "no trace in git history" corrected to "before this plan" (fresh-eyes, letter only).
