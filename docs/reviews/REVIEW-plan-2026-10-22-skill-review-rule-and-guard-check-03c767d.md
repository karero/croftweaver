# PLAN review — branch `skill/review-rule-and-guard-check` — independent-review: a no-BUG round's open RISK, a bug-log row, a question about guards
Base `e0be6661` · depth: Normal (an instruction file and a review prompt; nothing in the High row) · verdict: CLEAN · authority used: WORKTREE-WRITE and BRANCH-COMMIT — this session created the worktree and the branch (worktree stamped `ccd.owner`)

Plan: `docs/reviews/SKILL-PLAN-review-rule-and-guard-check.md`, reviewed text at `55f88ac3`.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `03c767d4` | full plan | codex-cli 0.163.0 (config.toml model and effort, read-only); melious GLM 5.3; fresh-eyes Sonnet sub-agent | codex 340, 98,670; melious 220, 21,257; fresh-eyes 733, 250,151 | 3 / 10 / 12 |
| 2 | `87f29a6a` | full plan, `--verify` with round 1's rows, changed sections named | codex (medium); melious FAILED (curl exit 56, reply cut off); ollama GLM 5.3 stood in | codex 1060, 80,168; melious 1168, —; ollama 709, — | 4 / 3 / 3 |
| 3 | `8a625be6` | full plan, `--verify` with rounds 1–2's rows | codex (medium); melious GLM 5.3 | codex 111, 66,147; melious 443, 41,074 | 0 / 1 / 3 |
| final full read | `0284242f` | full plan | ollama Kimi K3 (new to this plan) | 229, — | 0 / 2 / 1 |
| wording pass | `55f88ac3` | delta since `8a625be6` (`--base 8a625be6`) | codex (medium) | 56, 35,580 | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| P1-01 | BUG | codex, melious (NIT) | 1 | The paragraph's "a check that reads source text or syntax sees only the spellings it lists" is false for a syntax check | fixed; re-broken as P2-01, then cut | see P2-01 |
| P1-02 | BUG | codex | 1 | The inventory missed SKILL.md's other BUG-only round text (258, 279, 320) | fixed, externally_reverified (r2, r3) | §1 lists every "substantive" line with its change or why it stays |
| P1-03 | BUG | codex, fresh-eyes | 1 | T1 said the agy and paste tiers were not stubbed; `test_failed_tier_report.sh:175–192` and case 5 reach both | fixed, externally_reverified (r2) | T1 covers all four tiers |
| P1-04 | RISK | melious | 1 | A RISK-earned round may be refused if the script checks severity | refuted | `independent_review.sh:224–241, 266–268`: kinds only, no severity (codex r1 and r3 VERIFIED) |
| P1-05 | RISK | melious | 1 | The fresh-eyes prompt is built outside the four tier assignments | fixed, externally_reverified (r2) | §3 says the host builds it; T1's "cannot catch" names it |
| P1-06 – P1-11 | NIT | melious | 1 | Header qualifier; RISK/NIT precedence; meaning-free RISK; assignment before `readonly`; T2 "control" relabelled; step table rows | fixed, externally_reverified (r2) | plan at `87f29a6a` |
| P1-12 | RISK | fresh-eyes | 1 | T2's archive held the old PLAN trail, the comparison itself | fixed, externally_reverified (r2, r3) | `docs/reviews/` removed; P2-06 adds the phrase search |
| P1-13 | RISK | fresh-eyes | 1 | T2's raw output would quote a private, unmerged fix in a public repo | fixed, externally_reverified (r2) | raw output stays outside the repo and out of PR comments |
| P1-14 | RISK | fresh-eyes | 1 | T2/T3 had no rule for a fail | fixed; tightened by P2-03 | — |
| P1-15 | RISK | fresh-eyes | 1 | Inventory incomplete; the wording pass's anchor breaks under RISK-earned rounds | fixed, externally_reverified (r2) | 307 re-anchored on "after the rounds end" |
| P1-16 | RISK | fresh-eyes | 1 | The limits on RISK-earned rounds are mostly host judgment, not enforcement | fixed; qualified by P2-02 | §1 says which limit the script enforces |
| P1-17 | RISK | fresh-eyes | 1 | The past-round-8 owner decision may be the ask the owner's rule wants gone | fixed (named as a judgment, put to the owner with the go) | §3, judgment paragraph |
| P1-18 | RISK | fresh-eyes | 1 | The paragraph in every verification round re-asks about every guard | fixed, externally_reverified (r2) | the `--verify` sentence limits it to changed sections |
| P1-19 | RISK | fresh-eyes | 1 | "a refusal in code" made the plan's own fix a guard | fixed, externally_reverified (r2) | list narrowed to checks against a future mistake |
| P1-20 – P1-25 | NIT | fresh-eyes | 1 | T2 cost; a dangling reference; attribution; the allow-list wording; BUGLOG category and the reason line; newlines and model names | fixed, externally_reverified (r2); the `cut:` stderr line not reproduced here, so left out | — |
| P2-01 | BUG | codex | 2 | "an allow-list cannot see what an allowed form does" is false (`check_prompt_sync.sh:54–63` computes values) | fixed by a cut, externally_reverified (r3) | the general claim removed; the reviewer names an input the particular check misses |
| P2-02 | BUG | codex | 2 | The cut refusal is not unconditional: with no log answer the script warns and goes on (305–308) | fixed, externally_reverified (r3) | §1 qualifies it |
| P2-03 | RISK | codex | 2 | Revising after one failed trial can break the other | fixed, externally_reverified (r3) | both trials rerun on the shipped text |
| P2-04 | BUG | ollama | 2 | The earning test stated two ways | fixed, externally_reverified (r3) | step 6's full test everywhere |
| P2-05 | BUG | ollama | 2 | Keeping 317 contradicts the new earning rule | refuted | SKILL.md 307–318: the wording pass runs after the rounds, with "prose-only scope"; "Its RISK/NIT are follow-ups"; its fixes get one confirmation (codex r3 VERIFIED) |
| P2-06 | RISK | ollama | 2 | Old findings may sit outside `docs/reviews/` in T2's copy | fixed, externally_reverified (r3) | phrase search before the run; on 2026-10-22 the plan held only the trail's path and a status line |
| P2-07 | RISK | ollama | 2 | A wording-grade RISK in a gate with no BUG had no route | fixed, externally_reverified (r3) | fixed like a NIT under (a2) |
| P2-08 – P2-10 | NIT | ollama | 2 | The `cut:` note; argv re-check; "the script needs no change" | fixed, externally_reverified (r3) | argv: exit 2, "invalid UTF-8 was detected in one or more arguments" |
| P3-01 | RISK | melious | 3 | P2-05's refutation rests on unread lines | refuted | the quotes above; the seat had no tools; codex r3 read the lines |
| P3-02 | NIT | melious | 3 | A RISK that changes meaning but neither what runs nor what someone acts on has no route | refuted | step 6: a fix that leaves the meaning for a builder unchanged is wording; every other fix changes what someone acts on |
| P3-03, P3-04 | NIT | melious (outside scope) | 3 | T2's pass wording; `PROMPT_PLAN` is zero bytes for a diff | fixed, externally_reverified (wording pass) | `0284242f` |
| F-01, F-02 | RISK | Kimi (final full read) | — | Step 1 names no test for a RISK-earned round or for the cut refusal | fixed, externally_reverified (wording pass) | §1 names `test_round_checks.sh` sections 3, 4, 6 and 9, which pin both (a kind is only a name) |
| F-03 | NIT | Kimi | — | T3's pass rule could fail on a harmless mention | fixed, externally_reverified (wording pass) | a finding that treats §1/§2 as adding a guard fails; other mentions are counted as noise |

Waivers and deferrals: none.
Follow-ups: none.
Notes: round 2's melious seat broke off (curl exit 56, "Can't assign requested address", load average 300 to 540); the script's ollama stand-in ran the same model, so the pair stayed cross-model. Round 3 was clean under (a2): its RISK and NIT refuted, its two outside-scope NITs fixed. No round past 3. The fresh-eyes pass made one network call (`gh repo view`, the repo's visibility) and one local `--seat codex` run, refused by Codex before sending. UNVERIFIABLE entries were not counted. Cost logged: 593,047 tokens over 10 seat runs (3 with no figure: melious r2, ollama r2, Kimi); host work not counted. Raw reviewer output goes in the PR's review comment, not here.
