# DIFF review — branch docs/move-token-clicks — the move token's click-by-click text

Base `5a0b3010` (origin/main, merge of PR 579) · depth: High (the text tells a person which
permissions a token gets) · verdict: CLEAN after round 3 and one wording pass · authority used:
WORKTREE-WRITE and BRANCH-COMMIT. This session (move-token-clicks) created the worktree and branch.

Seats: Codex (gpt-6.1-sol, read-only) alone in every round. The melious seat (glm-5.3) failed each
round with "out of balance"; by the owner's rule (2026-10-27) no rerun is owed. Rounds 1 to 3 also
had a fresh-eyes host pass (an Opus sub-agent, read-only; 393,349 sub-agent tokens in all). Seat
tokens for Codex: 215,504 over four runs. Round 1 ran while the `make check` lock was busy, so it
stood on the fast doc guards only (check_clean, check_buglog_rows, check_model_agnostic,
check_skill_budgets); the full `make check` passed later on the tree of `436e093f`, and runs again
after the last edit.

Evidence for every round: `evidence-all*.md`, holding the author's brief and two (round 3: three)
READs of the live look at Cloudflare's token page (2026-11-17), the only source of labels. The
reviewers were told that the summary page was not seen.

| Round | Reviewed head | Artifact | Codex seconds, tokens | Findings (Codex; fresh-eyes) |
|---|---|---|---|---|
| 1 | `a66b33bc` | full diff | 176 s, 60,271 | 1 BUG, 2 RISK, 1 unverifiable; fresh-eyes 2 RISK, 9 NIT |
| 2 | `d279cd56` | delta, verify of round 1 | 131 s, 50,874 | 1 RISK; fresh-eyes 1 BUG, 4 NIT |
| 3 | `436e093f` | delta, verify of round 2 | 154 s, 54,284 | 1 RISK; fresh-eyes 1 RISK, 3 NIT |
| wording | `2d720503` | delta of round 3's fixes | 134 s, 50,075 | 1 RISK (re-sorted) |

| Finding | Status |
|---|---|
| Summary check relied on a page nobody saw | fixed: the look-over is first on the form (seen), then again on the summary page; the unseen-page note stays |
| "The script's error names the Workers permission" | fixed twice: only the Worker-domains error points back to the section; Workers Scripts at Read is not stopped early (the guide's own ready list, "read from the code, not run") |
| Four permissions may not authorise domain attachment (Codex, rounds 1 to 3, wording pass) | not introduced here: the permission set is the 0.35 guide's own, which named Workers Scripts at Edit in the kit's own moves; re-sorted as outside this change. Left unverified; a real attachment with exactly this token would settle it |
| Other old labels (Zone Resources, Account Resources, End date, TTL, two scripts and their tests) | follow-up: one BUGLOG row lists each place with its line; not changed here (scripts are code) |
| FIRST_DEPLOY "an Account or Zone policy" read as "pick one" | fixed: Account policy, then Add new policy for a Zone policy where the rows name zone rows |
| BUGLOG line numbers stale after round 1's edit (BUG) | fixed; recomputed after the last edit to FIRST_DEPLOY and re-checked in round 3 |
| "no parameter for an end date" in the set-up row | fixed: "no end-date parameter is documented, and none was tried"; the row's older "not checked" and "not done" sentences updated |
| NITs: Include and its list are two controls; "two policies"; Workers Scripts Edit by name; Developer Platform; "every Pages project and every Worker"; ready list says form then summary; two more script phrases in the BUGLOG row | fixed |
| "Add new policy" to a Zone policy, and "My Profile → API Tokens", not in the first evidence | answered with READ 3 (the live look's own note); kept |
