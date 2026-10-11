# DIFF review — fix/whats-new-removed-skill — say when a bundled skill was removed from the suite

Base `origin/main` (`e2f8cf7`) · depth: **Normal** (script that overwrites a site's skill copies, plus a new CI job and test) · verdict: **CLEAN** — one BUG found and fixed in each of rounds 1 and 2; round 3 had none; one RISK outside this change's scope became a BUGLOG row. Authority used: WORKTREE-WRITE and BRANCH-COMMIT (this session created the worktree and branch at the owner's "go, fix it with a test"); GATED

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `b8f5690` | `origin/main...b8f5690`, `docs/reviews/` excluded | Codex `gpt-6.1-sol` (config effort), read-only; Melious `glm-5.3`; fresh-eyes Sonnet sub-agent | codex 326 s/71,454; glm 84 s/17,869; fresh-eyes 124 s/102,475 | 1 / 4 / 4 |
| 2 `--verify` | delta since `b8f5690` | the round-1 fixes | Codex (medium); Melious glm-5.3 | codex 230 s/80,110; glm 203 s/22,252 | 1 / 0 / 3 |
| 3 `--verify` | delta since round 2's head | the round-2 fix | Codex (medium); Melious glm-5.3 | codex 70 s/27,771; glm 198 s/17,520 | 0 / 1 / 2 |
| wording | delta since round 3's head | two assertions and one BUGLOG row, `--seat codex` | Codex (medium) | codex 76 s/34,595 | 0 / 0 / 1 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| W1 | BUG | codex | 1 | a skill whose folder is deleted in the suite's working tree, but still in HEAD, read as "removed upstream" | fixed; externally_reverified r2 | classified with `git cat-file -e HEAD:skills/$s`; case 7 fails when the `-d` test comes back |
| W2 | RISK | codex | 1 | the "updated only" cases ignored the exit status and the `--refresh` command line | fixed; externally_reverified r2 | three assertions added |
| W3 | RISK | fresh-eyes | 1 | case 2's error assertion passed on the report's own text (stderr and stdout merged) | fixed; externally_reverified r2 | stderr alone, "REFRESH-KEEP, then re-run" |
| W4 | RISK | glm | 1 | `beta # kept on purpose` in REFRESH-KEEP might not pin | refuted | the loader strips `#…` (`sed 's/#.*//'`); case 5 asserts the pin |
| W5 | RISK | fresh-eyes | 1 | the new CI job is not in the ruleset's required checks | refuted as a gap; owner decision | the required `macos-stock-tools` job runs `make smoke`, which runs this test; adding the Linux job to the ruleset is a repo setting |
| W6–W9 | NIT | fresh-eyes, glm | 1 | an untrue sentence about the pinned route; "re-copies" when only pinned skills remain; README and workflow-header entries; no removed-plus-pinned case | fixed; externally_reverified r2 | case 4b added |
| X1 | BUG | codex (glm RISK) | 2 | the report read "removed" from HEAD but `--refresh` still tested the working tree: an untracked leftover folder was called removed by one and copied by the other, stamping HEAD over content matching no commit | fixed; externally_reverified r3 | one helper `suite_has` for both; case 8 (leftover folder) and an uncommitted-deletion refresh case; the old `-d` test in the refresh loop fails 3 assertions |
| X3–X5 | NIT | glm | 2 | "re-copies the skills above" false for pinned ones; mixed case had no exit-status check; one `git cat-file` per skill | X3, X4 fixed; X5 noted | — |
| Y1 | RISK | glm | 3 | an untracked file inside a kept skill's folder passes `suite_dirty` (`-uno`) and is copied by `--refresh` | follow-up | not introduced by this change; existed before it; BUGLOG row |
| Y2, Y3 | NIT | glm | 3 | two assertions could pass vacuously (case 8 and case 7) | fixed; locally_verified, not externally re-verified | `has "$err" "was removed upstream"`, `has "$err" "uncommitted changes"` |
| Z1 | NIT | codex | wording | the BUGLOG row cited a review record that did not exist yet | fixed | the row now cites this file by its exact name |

Waivers: none. Deferrals: none. Follow-ups: Y1 (the BUGLOG row).

Host evidence: the test has 37 cases and fails 8 of the first 21 on the old script. Mutations: the refresh loop back on `-d` fails 3 assertions; classifying from the working tree fails case 7. The test also passes in the unzipped handoff zip and under `/bin/bash` 3.2. Repo guards pass (`check_cdpath_safe`, `check_pipefail_pipes`, `check_lf_checkout`, `check_clean`, `check_template_coverage`, `check_skill_budgets`); `package.sh` builds the zip.

Notes: the ollama seat was absent by design (Melious is the second seat; CLI hidden from `PATH`); consent for Melious is recorded in #192's trail. Round 3 had no BUG and its RISK went to a follow-up (stop condition a2); the closing edits got the one-seat wording pass.
