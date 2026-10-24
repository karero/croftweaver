# DIFF review — feat/flash-think-tag-guard — the light Melious model is refused when the prompt holds a think tag

Base `683f7ea3` · depth: Normal (changes a guard's logic in a reviewer script: never Light) · verdict: CLEAN · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session made the worktree, and finishes the branch on the owner's request of 2026-10-24, "Can you pick this one up and finish it in a subsession?"); POST AUTHORITY — atom A (this session opens the PR); GATED-THIS-DIFF — atom A (the chain below)

The branch's first three commits (2026-10-22) mention a round 1, but no trail or raw output for it exists in the repo, so this gate started again at round 1. Before it, `origin/main` was merged in (`8bdab13f`, one conflict in the R-MELIOUS-THINK row, resolved by keeping main's wording and recording the guard). `make check` passed on `8bdab13f` (exit 0); its Perl minimum-version check was skipped locally (Perl::MinimumVersion not installed) and runs in CI.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `8bdab13f` | full, `683f7ea3...8bdab13f`, `docs/reviews/` excluded | Codex CLI 0.164.0, gpt-6.1-sol, config effort, read-only; Melious glm-5.3 (HTTP API, text only); fresh-eyes: Claude Sonnet sub-agent, read-only | codex 226 s, 69,517; melious 289 s, 38,475; fresh-eyes 147 s, 102,854 | 0/0/2 |
| wording pass (not a round) | `946a0e3a` | delta `8bdab13f..946a0e3a`, prose only (Markdown and Perl comment lines) | Codex, medium effort | 115 s, 37,232 | 1 contradiction in a comment, labelled BUG by the seat |
| confirmation (not a round) | `dff6ed22` | delta `946a0e3a..dff6ed22`, one comment line | Codex, medium effort | 40 s, 29,156 | 0/0/0 |
| merge link (not a round) | `a085fb89` | `merge_link.sh 683f7ea3 dff6ed22 36fdafef -- melious_models.txt` (main moved: #393 listed a second light model) | Codex, medium effort; Melious glm-5.3 | codex 81 s, 55,276; melious 90 s, 15,627 | 0/0/0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| N1 | NIT | GLM 5.3; fresh-eyes the same | 1 | `perl/think_tag.pl`: the pattern also matches a name that goes on with `-` or `.`; the comment did not say so | fixed, locally_verified; externally_reverified by the wording pass | `946a0e3a`: the comment says it is on purpose |
| N2 | NIT | GLM 5.3 | 1 | setup guide's parenthetical understated what matches (`thinking`, spaces or tabs, no closing bracket needed) | fixed, locally_verified; externally_reverified by the wording pass | `946a0e3a`: states the shape and points to `perl/think_tag.pl` |
| W1 | wording | Codex, wording pass | — | N1's new comment said a wrong refusal "sends the round to Codex"; `--seat melious` exits 4 and the pair falls back to ollama | fixed, externally_reverified by the confirmation | `dff6ed22`: "costs a rerun on another seat" |

UNVERIFIABLE entries, round 1 (5 asked, 0 confirmed as findings): the measured Flash behaviour (rests on the 2026-10-12 replies in the comment on karero/croftweaver#274, as the row says; a false premise only over-refuses); `melious_rule` set on every path (checked: set at startup for any named model, before any seat runs; tests tseat, ttpair, ttfall); the Perl minimum (CI's check); the test harness helpers and the JSON encoder not escaping `<` (the suite passed, ttany included).

Second merge of `origin/main` (`a085fb89`, base `36fdafef`): #393 listed `deepseek-v4.1-flash-1017` as a light model, measured reading the zebra plan 3 of 3. The guard keys on the `light` marker, as the plan chose, so it refuses that model too on a tagged prompt; kept, and put to the owner. The refusal message, the helper's header, the setup guide, the row and the release-notes row were reworded so none claims a measured failure for that model. `make check` was run again on `a085fb89`.

Follow-ups: owner decision, whether a measured light model should be exempt from the guard (needs a new marker in `melious_models.txt`; a plan first). R-MELIOUS-THINK stays open for the five-of-five measurement on glm-5.3, by hand.
Notes: round 1 had no BUG and no RISK, so no further round was owed (step 6, a2). Release-notes row added to `docs/BUGLOG.md` after round 1 and read by the wording pass. The trail commit that follows `dff6ed22` changes only this file, outside the reviewed scope.
