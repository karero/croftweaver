# DIFF review — karero/croftweaver#433 — Pages or Workers: results of the one-site Workers trial

Base `a14581ea` · depth: Normal (adds a config block to a document a person follows, and edits a skill reference agents load; no High-row item) · verdict: CLEAN · authority used: POST AUTHORITY, WORKTREE-WRITE, BRANCH-COMMIT — atom A, this session created the PR, the worktree and the branch; GATED-THIS-DIFF — atom A, the chain below

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `023413cf` | full, base `a14581ea`; evidence 6,180 bytes (the trial's results log) | codex-cli, gpt-6.1-sol (config effort, read-only); melious glm-5.3 (HTTP API, text only); fresh-eyes sonnet sub-agent (read-only) | codex 193 s, 44,407; melious 136 s, 15,703; fresh-eyes 75 s, 115,710 | 1 / 5 / 4 |
| 2 | `4c7bc1fd` | delta since `023413cf`; evidence 7,893 bytes (adds the pricing sentences, the screenshot description, the 2026-10-25 figures) | codex (medium), melious glm-5.3 | codex 98 s, 41,572; melious 130 s, 17,958 | 2 / 1 / 2 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | codex; fresh-eyes NIT | 1 | `WEBSITE_ARCHITECTURE.md` Part 1 still called a move without middleware "untried" | fixed `4c7bc1fd` (externally_reverified r2) | now: tried on one throwaway site, worked with gaps, kit not moved |
| F2 | RISK | codex, glm, fresh-eyes | 1 | "`preview_urls = false` turns them off" was never tried | fixed `4c7bc1fd` (externally_reverified r2) | now Wrangler's suggestion, "not tried" |
| F3 | RISK | glm, codex, fresh-eyes | 1 | Row 8's daily-limit claim had no source; window and outside traffic unstated | fixed `4c7bc1fd` (externally_reverified r2), completed by F11 | Pages Functions pricing and static assets billing quoted (fetched 2026-10-28) |
| F4 | RISK | fresh-eyes | 1 | Recommendation said route B "worked as the docs describe" | fixed `4c7bc1fd` (externally_reverified r2) | names the two premises; gaps noted |
| F5 | RISK | fresh-eyes | 1 | Config tables lacked the keys the trial needed; Setup row silent on Previews | fixed `4c7bc1fd` (externally_reverified r2) | `previews`, `workers_dev: false`, `routes`; "(on the trial, Previews ignored it)" |
| F6 | RISK | fresh-eyes | 1 | "is for the trial below" already answered | fixed `4c7bc1fd` (externally_reverified r2) | points to Trial results, step 1 |
| F7 | NIT | fresh-eyes | 1 | Decision note's wording did not match the list item | fixed `4c7bc1fd` (externally_reverified r2) | — |
| F8 | NIT | fresh-eyes | 1 | Row 9 "one hour"; the 2026-10-25 note dropped | fixed `4c7bc1fd`, completed by F12 | "two minutes (12:39 to 12:41 UTC)" |
| F9 | NIT | glm | 1 | Row 4 "alike" over a differing item | fixed `4c7bc1fd` (externally_reverified r2) | — |
| F10 | NIT | glm | 1 | "Left for a plan" dropped the two candidate causes | fixed `4c7bc1fd` (externally_reverified r2) | — |
| F11 | BUG | glm BUG, codex RISK | 2 | "none from the trial's own runs": the trial's missing-path checks were 404s | fixed after round 2 (locally_verified; wording pass) | now "a few were the trial's own missing-path checks and none were timing requests"; the rest not traced |
| F12 | BUG | codex BUG, glm NIT | 2 | "about twice as slowly" did not match 23–51 ms vs 73–169 ms, other sites | fixed after round 2 (locally_verified; wording pass) | now states both ranges and "two other sites" |
| F13 | NIT | glm | 2 | "Both counts include traffic not the trial's": no Pages breakdown | fixed with F11 | "The Pages count was not broken down" |

UNVERIFIABLE entries: round 1, 9 asked, 2 confirmed (F2, F3); round 2, 6 asked, 0 confirmed. They concern Cloudflare's runtime behaviour, the dashboard screenshots and Wrangler output, which the text-only seat could not observe.

Waivers and deferrals: none.

Follow-ups: none.

Notes: round 2's findings were wording in the results record (no change to what someone builds or runs), so no round 3 was owed; they went to the wording pass. `make check` passed on `be536c86`; `scripts/check_clean.sh` passed on each later commit.
