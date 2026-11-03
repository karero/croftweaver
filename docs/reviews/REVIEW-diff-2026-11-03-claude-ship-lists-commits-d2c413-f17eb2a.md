# DIFF review — branch `claude/ship-lists-commits-d2c413` — `npm run ship` lists the commits that go live

Base `505723087eb5` (merge base with origin's HEAD `98a0ef9d`) · depth: High (the starter's publish script; the High row names deploy code) · verdict: CLEAN · authority used: WORKTREE-WRITE and BRANCH-COMMIT, atom A (the app made this worktree and branch for this session). The PR comment and the stamp: POST AUTHORITY and GATED-THIS-DIFF, set out at the end.

Plan: `docs/reviews/SKILL-PLAN-ship-lists-commits.md` (plan gate CLEAN). Seats: Codex gpt-6.1-sol (config effort, read-only) and GLM 5.3 on melious in one command (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`, `CODEX_EFFORT=config`); fresh-eyes on Sonnet 5.5 in round 1 (the host's own model; the chain ends at round 3 and no later round was owed); final full read by a fresh Opus 5.5 pass; wording pass on Codex. Melious counted in every round of this gate (it was out of balance for the plan gate). The first send of this repo's content to melious was cleared in the plan gate; the artifact and evidence held no secrets (grep).

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `f17eb2a6` | full change, `git diff origin/main...HEAD` without `docs/reviews/`; evidence `evidence-r1` (61,172 bytes: test records on bash 5.3 and 3.2, `make check`, 17 mutations with the mutator's source, `ship.sh` whole) | Codex, GLM 5.3 · fresh-eyes Sonnet 5.5 | Codex 252 s, 65,645 · GLM 578 s, 56,639 · fresh-eyes 198 s, 155,655 | 1 / 1 / 6 (Codex 1/0/0, GLM 0/1/2, fresh-eyes 0/0/4) |
| re-gate | `5bd25863` | delta `f17eb2a6..5bd25863`, `--verify`, `--base`; evidence `evidence-r2` (53,179 bytes) | Codex, GLM 5.3 | Codex 120 s, 54,503 · GLM 158 s, 26,405 | 2 / 0 / 1 (Codex 2 BUG: A1 re-raised, A6 wording; GLM 0/0/1) |
| final read | `5bd25863` | whole current change, fresh pass with no trail; evidence `evidence-r2` | fresh Opus 5.5 pass | 378 s, 164,933 | 0 / 0 / 4 |
| re-gate | `ce071850` | delta `5bd25863..ce071850` (holds code), `--verify`, `--base`; evidence `evidence-r3` (52,956 bytes) | Codex, GLM 5.3 | Codex 132 s, 93,763 · GLM 245 s, 29,604 | 0 / 1 / 2 (Codex 0/1/0 on a BUGLOG sentence, GLM 0/0/2) |
| wording pass | `34f84033` | delta `ce071850..34f84033`, `--wording-pass --seat codex` | Codex | 175 s, 42,048 | 0 / 1 / 0 (follow-up) |

No round had a substantive BUG: the one BUG of round 1 is refuted, so rounds 2 and 3 were owed by nothing except the code the fixes changed (a stall-warning branch and two test cases), which is why the last two deltas ran as full-scope re-gates, not rounds. The wording pass is the prose-only re-gate for the stamp. Gate total from the cost log: 368,607 tokens over 7 script seat runs, plus fresh-eyes 155,655 and the final read 164,933: about 689,000.

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | BUG | Codex | 1, re-gate | The push line follows the count read before the push, not the push's own answer; another clone publishing the same commit between list and push leaves "✓ Pushed" | refuted as a BUG, kept as follow-up (re-sorted: rare) | the same commit is pushed, so the live-site check that follows verifies it; the plan lists it under Not covered; the old line said the same; one seat only, twice, no new evidence the second time; BUGLOG row 2026-11-03 |
| A2 | RISK | GLM 5.3 | 1 | L4 needs `en_US.UTF-8`; on a glibc machine without it the `lcall` mutation could survive | refuted | GNU `tr` works on bytes in any locale, so only the Mac job can see `LC_ALL=C` matter; that job runs this file (`template-tests.yml`, "Publish script on the Mac's bash 3.2"); `lcall` killed at l4 on the Mac (evidence READ 5); plan row E3 says "Mac job only" |
| A3 | NIT | GLM 5.3 | 1 | "… and 1 more lines" | fixed, locally_verified | `live_word`; case L2b; mutation (switch removed) fails L2b |
| A4 | NIT | GLM 5.3 | 1 | a test message said "before the push" but checks presence only | fixed, locally_verified | words removed |
| A5 | NIT | fresh-eyes | 1 | comment: "before anything is made" is wrong in worktree mode | fixed, locally_verified | "before the worktree is made or anything is pushed" |
| A6 | NIT, then BUG | fresh-eyes, Codex, GLM 5.3, final read | 1, re-gate, re-gate 2 | the comment on the stripped bytes overstated (C1; tab; newline) | fixed, locally_verified | "7-bit control bytes other than tab and newline"; C1 stays in the plan's Not covered |
| A7 | NIT | fresh-eyes | 1 | test header did not mention the L cases | fixed, locally_verified | a sentence; reworded twice (re-gate, re-gate 2) |
| A8 | NIT | fresh-eyes | 1 | with nothing new, a stop during the push or live check prints "The publish went out" | follow-up (re-sorted: rare) | the sentence stays true (production is now that commit) |
| A9 | NIT | Codex | 1 | BUGLOG row: "closing line" no longer claims a build | fixed, locally_verified | reworded twice; final form names the push line and the stall warning |
| F1 | NIT | final read | final | the four-minute stall warning said "Pushed OK" when nothing was new (a re-run after a stall: ordinary) | fixed, locally_verified | `ship.sh` prints "Nothing was pushed (…)" when `live_n` is 0; cases L2c and L3b (stale build via `SHIP_T_STALE`); the branch turned off fails L3b; plan item 7 names it |
| F2 | NIT | final read | final | BUGLOG: wrong line named | fixed | see A9 |
| F3 | NIT | final read | final | tab in the comment | fixed | see A6 |
| F4 | NIT | final read | final | okpush's skip check took any non-empty `SHIP_GATE_SKIP_WORDING`; `expect` takes ''/0/false/no as "check" | fixed, locally_verified | the same `case` list; ran with both shells |
| G1 | RISK | Codex | re-gate 2 | BUGLOG: "Cloudflare is building that commit then" has no deployment evidence | fixed | sentence replaced by what the script checks (the live-site check looks for the commit) |
| G2 | NIT | GLM 5.3 | re-gate 2 | header: L cases now also check the stall warnings; the comment omitted newline | fixed | both reworded |
| W1 | RISK | Codex (wording pass) | wording | BUGLOG: "only the word 'Pushed' is loose" excuses the old "Cloudflare is building" assertion, which the script never confirms | follow-up | pre-existing text of the push line, kept for the case with news; the live-site check that follows is what verifies; not a contradiction with the code |

UNVERIFIABLE entries asked: signed L4 (answered: ssh-keygen and git 2.54 present, no "runs without its signed commit" note, and the final read saw the signed commit exercised); marker agreement (`check_ship_push.sh` lines 211–224, not in the diff); `whats-new.sh` line 80 names all three files; `git push --porcelain` marks an up-to-date ref with `=` (the BUGLOG row's fix to consider; Codex found it in git's manual; not tested for translation, not built). Cloudflare deployment timing is not testable here.

Waivers and deferrals: none. Follow-ups: A1 (BUGLOG row 2026-11-03), A8, W1 (same row family), C1 control characters (plan, Not covered).

Notes: no round past 3; no `--earned-by`. The final read and the delta re-gates sent evidence files; the PR carries the test records. Mutation checks: 17 of 17 at round 1, plus the singular switch and the stall branch, all killed. "Closing edits not externally re-verified": none beyond the wording pass's own scope; the last code change (`ce071850`) was seen by Codex and GLM 5.3.
