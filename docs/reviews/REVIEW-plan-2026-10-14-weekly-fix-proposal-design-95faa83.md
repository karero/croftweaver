# Review trail: design plan for the weekly fix proposal

Artifact: `docs/reviews/DESIGN-weekly-fix-proposal.md` and the probe
`docs/reviews/fix-proposal-probe/fix_probe.py` (PR #297). Gate: Normal, PLAN. Reviewers:
Codex and GLM 5.3 on melious. A severity bar was agreed in the brief before round 1:
claims about Google and Serper that the plan quotes or measured are not re-raised, and
the owner's decisions are settled.

## Round 1 — reviewed at 95faa83, 2026-10-14

Codex 14 findings, GLM 9; merged, 21: 9 BUG, 9 RISK, 3 NIT. All fixed.

| # | Seat | Kind | Finding | Disposition |
|---|---|---|---|---|
| 1 | Codex | BUG | `track.sh` and `schedule_tracking.sh` rewrite `sites/<site>.json` whole, so `brand`, `repo`, `pr_figures` stored there would be lost | Fixed: the owner's answers live in the new state file |
| 2 | Codex | BUG | The control ignored shared files outside `src/` and `public/` (`astro.config.mjs`) | Fixed: any commit outside the starter's documentation-only rule voids the control |
| 3 | Codex, GLM | BUG + NIT | The live-detection windows did not give scenario 8's dates, and "the Sunday before / Monday after" a run was ambiguous | Fixed: last Sunday before the last "old" observation; first Monday on or after the first "new" one; scenario 8 worked through |
| 4 | Codex, GLM | BUG + RISK | A closed pull request was never noticed, so the page could stay blocked | Fixed: `gh pr view` each run; closed = "not this one"; without `gh`, a 6-week release |
| 5 | Codex | BUG | Words under 3 letters were skipped, so "ki" made every page "already" match | Fixed: every word counts, whole words, a short stop-word list; an empty set never matches |
| 6 | Codex | BUG | `serp_check.py` expects a two-letter country, the settings hold three | Fixed in §1 for T2 later |
| 7 | Codex | BUG | The probe's window lacked the report's Sunday alignment | Fixed; rerun gave the same output (the finished day was a Sunday) |
| 8 | Codex | BUG | P2 called Serper's text "what Google keeps" before the by-eye half | Fixed: worded as Serper's result, conditional on the owner's check |
| 9 | Codex | BUG | T1 is the playbook's second item, not its first | Fixed |
| 10 | Codex | RISK | `git log` on a stale local checkout can miss other people's changes | Fixed: `git fetch`, then the remote default branch; a failed fetch means no comparison |
| 11 | Codex | RISK | A failed page fetch counted as "not live yet" | Fixed: three outcomes, unknown moves nothing |
| 12 | Codex | RISK | Saved data after a Google failure could still produce a proposal | Fixed: proposals only from fresh data; a test for it |
| 13 | Codex | RISK | Whether the owner's sentence loads the skill cold is unproven | Fixed as a step: tried cold in Claude Code and Codex in step 4 |
| 14 | Codex | RISK | The review step did not wait for the reference and evals | Fixed: step 6 waits for 4 and 5 |
| 15 | GLM | RISK | No rule for which commits are the proposal's own | Fixed: commits naming the pull request number |
| 16 | GLM | RISK | "Already on the page" was not in the exclusion list | Fixed |
| 17 | GLM | RISK | `--title` could be read as the pull request's title | Fixed: `--new-title`, the page's `<title>`, folded substring match |
| 18 | GLM | RISK | No command wrote the owner's answers | Fixed: `fix_proposal.py set` |
| 19 | GLM | NIT | The four places were not listed | Fixed |
| 20 | GLM | NIT | Scenario 3 had no test and no reason | Fixed: T2 waits |
| 21 | GLM | NIT | "One more request" could be read as unpaged | Fixed |
