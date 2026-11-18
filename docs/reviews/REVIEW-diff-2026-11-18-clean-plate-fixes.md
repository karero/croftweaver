# DIFF review — branch fix/clean-plate-links-bot-email — three owner-facing BUGLOG rows

Base `c1538949` (origin/main at the start) · depth: High (one row changes what setup writes to a
Cloudflare zone) · verdict: no BUG open after round 3 and one wording pass · authority used:
WORKTREE-WRITE and BRANCH-COMMIT. This session (clean-plate fixes) created the worktree and branch.

Seats: Codex (read-only) and melious (GLM 5.3) in rounds 1 to 3, plus a fresh-eyes host pass in each
(an Opus sub-agent, read-only: 181,292, 147,210 and 162,765 tokens). The wording pass ran on Codex
alone, by the rule. The cost log shows 879,118 seat and fresh-eyes tokens for the gate in all. Round 1
ran while the `make check` lock was busy, so it stood on the fast guards (check_clean,
check_buglog_rows, check_model_agnostic, check_skill_budgets); the full `make check` runs once the
lock is free, on the last head, before the push.

Evidence for every round: one file of READs and RUNs. READ 1 is Cloudflare's own docs page for the
Bot Management update (partial bodies are valid); READ 2 is what the captures show about leaving
fields out of the PUT. Nothing ran against a real zone, token or account.

| Round | Reviewed head | Artifact | Findings (Codex; melious; fresh-eyes) |
|---|---|---|---|
| 1 | `ba59f9f8` | full diff | Codex 2 BUG, 1 RISK; melious 1 RISK, 1 NIT; fresh-eyes 1 BUG, 4 NIT |
| 2 | `caf8fd24` | delta, verify of round 1 | Codex 1 BUG, 1 RISK; melious 1 RISK, 3 NIT; fresh-eyes 1 BUG, 1 RISK, 7 NIT |
| 3 | `98b80b52` | delta, verify of round 2 | Codex 1 RISK; melious 2 RISK, 3 NIT; fresh-eyes 1 BUG, 3 NIT |
| wording | `0fef351c` | delta of round 3's fixes | Codex 1 BUG, 1 RISK |

| Finding | Status |
|---|---|
| "Nothing is lost" / "not overwritten" overclaimed (a field the run changes is still sent) | fixed: code comment, both BUGLOG rows say "any other field" |
| Cloudflare keeping a left-out field is unsupported for the nine newly omitted fields (Codex and melious, every round) | not fixable here: no captured before/partial-PUT/after exists, and a live check needs an API token, which I may not create. Disclosed in the code, the checklist and both BUGLOG rows. Kept as the PR's stated weak point |
| T2-061 "true stayed true" was the zone's starting value (T2-040), so it proves nothing (fresh-eyes, round 3, checked by hand against the fixtures) | fixed: all places now say no capture shows a left-out top-level field keeping a value that differs from the zone's start |
| The checklist's "What it writes" described the old nine-field PUT; missed `ai_agents`; "sync when the AI lines run"; "the read-back stops the run" | fixed |
| "The first real site shows it" (wording pass BUG): the read-back cannot see a reset of a field that held its default | fixed: the paragraph says what the read-back can and cannot show |
| "Quits outside a git repo" false on macOS bash 3.2 (`cd ""` succeeds) | fixed: the exemption says what the script needs, without a git claim |
| Email test's `typeof` assertion could never fail after the `delete` | fixed: it runs only on builds with no stub in the page; a stub shipped by mistake is `check_analytics_gate.sh`'s job, said in the comment |
| Links script header; stale step in the setup plan record; BUGLOG release-note wording | fixed |
| melious RISK: do any BOT_LINES fields name `enable_js` or `cf_robots_variant`? | answered: no (BOT_LINES read; fresh-eyes and Codex checked too); not a finding |

Open for later, not done here: the live check of the partial PUT on a throwaway zone, with the
maintainer's own login (it settles the Cloudflare RISK for good).
