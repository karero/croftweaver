# DIFF review — karero/croftweaver#567 — BUGLOG: close 28 release-notes rows whose lines are in the v0.35 notes

Base `36229c9d` · depth: Light gate (BUGLOG status cells only, prose no agent follows; the brief named
Light for this PR) · verdict: CLEAN after round 1 (1 round, 1 finding, refuted; gate total 83,823 seat
tokens logged) · authority used: WORKTREE-WRITE and BRANCH-COMMIT. This session (the bug sweep before
0.36) created the worktree and the branch `docs/close-released-note-rows`.

Artifact: `git diff 36229c9d...92dc6a35 -- . ':(exclude)docs/reviews/'`. Evidence file with READ 1: the
v0.35 release's body and publish time, from `gh release view v0.35 -R karero/croftweaver --json
publishedAt,body`, run 2026-11-15T23:43:45Z. Gate id 20261115T234401Z-47190.

Claims sweep (`sweep_claims.sh --base 36229c9d`), before round 1: each "is not in it" note on rows 217,
230, 250, 253, 268 and 288 was checked against READ 1 by search. Row 217's first note also said the
`search-console-setup` mention was missing; v0.35 names `search-console-setup` for other changes
(lines 34 and 42), so the note was cut to what is missing: the "weekly, or every 2 or 4 weeks" cadence
(v0.35 says "repeated asks"), and that the control is also in `search-console-setup` (`92dc6a35`).

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `92dc6a35` | full, `--base 36229c9d` | Codex (gpt-6.1-sol, effort medium, read-only), alone, as Light allows | codex 169 s, 83,823 | 1 / 0 / 0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| L1 | BUG | Codex | 1 | Row 284 says the four-week check "lists every query with at least 1 click", but `gsc_query.py` lists at most 100 (`DRILL_LIMIT = 100`, line 184). | refuted | Not in this change: the diff changes only row 284's status cell, and the sentence is the row as filed on 2026-11-09 and in the published v0.35 notes. The text the check is run from, `skills/website-new-page/SKILL.md:191-197`, says "every query the before report lists" and that the note counts the rows left out when a report says "Showing 100 of N queries". |

Notes:
- UNVERIFIABLE: 7 asked, 0 confirmed. The first (the release's body and time) is READ 1. The other six
  are about the features the closed rows describe (Cloudflare, Google and Bing, studies, Playwright,
  permissions, Node), which this PR does not change.
- No second round: Light adds one only for a BUG, and L1 was refuted with no change.
- `scripts/check_buglog_rows.sh` passed in Codex's run (310 rows, no duplicates), and `make check`
  passed on `92dc6a35`.
