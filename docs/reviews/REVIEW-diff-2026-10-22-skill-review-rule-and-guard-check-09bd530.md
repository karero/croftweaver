# DIFF review — branch `skill/review-rule-and-guard-check` — independent-review: an earning RISK earns a round; plan reviews ask about proposed guards; BUGLOG row
Base `001c68b7` (merge base with origin/main after merging it at `09bd5309`) · depth: Normal (an instruction file, a review prompt and its test; nothing in the High row) · verdict: CLEAN · authority used: WORKTREE-WRITE and BRANCH-COMMIT — this session created the worktree and the branch (worktree stamped `ccd.owner`)

Artifact: `git diff <base>...HEAD -- . ':(exclude)docs/reviews/'`. Seen pair for the stamp: merge base `d2d015c6`, head `70553e4f` after the second merge of `main`; Codex's chain is unbroken (round 1 full, round 2, the re-gate and the merge link each from the head before).

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `09bd5309` | full (base check: merge base with origin's HEAD, fetched) | codex-cli 0.163.0 (config.toml model and effort, read-only); melious GLM 5.3; fresh-eyes Sonnet sub-agent | codex 286, 86,560; melious 228, 29,164; fresh-eyes 648, 278,892 | 2 / 2 / 6 |
| 2 | `fbd4df6f` | delta since `09bd5309` (`--base 09bd5309`), `--verify` with round 1's rows | codex (medium); melious GLM 5.3 | codex 134, 62,572; melious 175, 23,877 | 0 / 0 / 2, plus 2 NIT outside scope |
| re-gate (prose only) | `8db31704` | delta since `fbd4df6f` (`--base fbd4df6f`) | codex (medium) | 53, 34,148 | 0 / 0 / 0 |
| merge link | `70553e4f` | `merge_link.sh 001c68b7 8db31704 d2d015c6` (`--base 8db31704`): `docs/BUGLOG.md` only | codex (medium) | 177, 57,895 | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| D1-01 | BUG | codex | 1 | rationale: "the owner no longer sees a late round's RISKs" contradicts step 8's update between rounds | fixed, externally_reverified (r2) | "the owner still gets each round's update (step 8), but no longer decides a late round's RISKs before the next round runs" |
| D1-02 | BUG | codex, fresh-eyes | 1 | BUGLOG: Codex is not the round's only reviewer that can open files | fixed, externally_reverified (r2, re-gate) | "the script's one seat told to read the files"; the reason line quoted whole |
| D1-03 | RISK | melious | 1 | "the script needed no change" rests on code outside the diff; a RISK-earned round might be refused | refuted | codex r1 ran `review_log.sh`'s round check: kinds only; `independent_review.sh:224–241, 266–268`; `test_round_checks.sh` sections 3, 4, 6, 9 (codex r2 traced them) |
| D1-04 | NIT | melious, fresh-eyes | 1 | (a2)'s "a RISK that calls for a fix" vs a wording RISK fixed "like a NIT under (a2)" | fixed, externally_reverified (r2) | (a2) names step 6's test |
| D1-05 | NIT | melious, fresh-eyes | 1 | A gate with no substantive BUG has no wording pass; its prose had no stated route | fixed, externally_reverified (r2) | "or, where no round had a substantive BUG, to the prose-only re-gate (step 2)" |
| D1-06 | RISK | fresh-eyes | 1 | Step 8's "an owed or earned round runs without waiting" had no round limit, against the kept round-8 stop | fixed, externally_reverified (r2, re-gate) | "up to round 8 …; past round 8, the owner decides each further round (6(b))" |
| D1-07 | NIT | fresh-eyes | 1 | "ask only for …" read as the complete list of owner asks | fixed, externally_reverified (re-gate) | "when a round ends, ask about its findings and the rounds only for …: a RISK or NIT waiver …" |
| D1-08 – D1-10 | NIT | fresh-eyes | 1 | rationale overstated T3; test 25b's negatives hard-coded literals; the verify sentence's "it" | fixed, externally_reverified (r2) | "the prompt asks for no entry"; `$GUARDS`, `$GUARDS_VERIFY`; "ask these questions only of guards …" (prompt and test together) |
| D2-01 | NIT | melious | 2 | "past round 8, 6(b) decides" could read as automatic | fixed, externally_reverified (re-gate) | see D1-06 |
| D2-02 | NIT | melious | 2 | D1-07 partly fixed: an Antigravity offer is also asked at a round's end | fixed, externally_reverified (re-gate) | see D1-07; step 8 keeps the offer |

Waivers and deferrals: none.
Follow-ups: (a2) says "no BUG" while its parenthetical says deferred BUGs call for no fix (older text; melious r2, outside scope). Test 25b checks the verify sentence's absence in the Codex prompt only, not ollama's (melious r2, outside scope; both prompts embed the same variable).
Notes: no substantive BUG in any round (D1-01 and D1-02 were prose in the rationale and the bug log), so no wording pass; the closing edits got the prose-only re-gate (closeout, clerk item 2). No round past 3. Before review the branch merged origin/main (`09bd5309`; one conflict, two BUGLOG rows appended by #376, both kept). After review it merged origin/main again (`70553e4f`, for #380 and #379's release-notes row; the same kind of BUGLOG conflict, both rows kept), bridged by the merge link; its `--suggest-callees` names came from BUGLOG prose, none called by the change's code. Fresh-eyes ran its own mutation check of test 25b (seven mutants caught) and one `--seat codex` run, refused by Codex before sending. `make check` green at `6ae85997`, at the merged head `09bd5309`, at `8db31704` and at the second merged head `70553e4f`; the tier test green at `fbd4df6f`. Cost logged: 515,213 tokens over 6 seat runs, plus the merge link's 57,895; the PLAN gate before it, 593,047. Raw reviewer output goes in this PR's review comment, not here.
