# DIFF review — #491 — the starter's updates for a site already on Cloudflare Workers (0.35)

Base `38bf1768` (rounds 1–3), then `3cf57d5e` after the merge of `origin/main` · depth: Normal (code a
site's build runs; no box, user data, login, money, deletion or schema) · verdict: CLEAN, with A2 deferred by the owner · authority used: POST AUTHORITY, WORKTREE-WRITE and BRANCH-COMMIT — atom A, session
"0.35 B" created the PR, the worktree and the branch. Plan: `PLAN-workers-site-updates.md` in the
private hub (PLAN gate closed: 41 findings, 6 BUGs). Seats: Codex and GLM 5.3 on melious in one
command (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`), fresh-eyes Sonnet in round 1. The artifact
leaves out `docs/reviews/`. The evidence files sit in the session's scratchpad.

## Rounds

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `7bd4b05f` | whole change (503 lines); evidence 19,874 bytes (READ 1–4, PLAN-READ 1–9) | Codex 0.167.0 gpt-6.1-sol, read-only; melious glm-5.3; fresh-eyes Sonnet | Codex 147 s, 54,466 · melious 212 s, 36,628 · fresh-eyes 51 s, 119,741 | 2 / 3 / 4 |
| 2 | `b7cc885e` | verify: delta since `7bd4b05f`, PRIOR round 1; evidence READ 5 | Codex (medium); melious | Codex 187 s, 57,187 · melious 231 s, 25,417 | 2 / 0 / 3 |
| 3 | `6ba70f63` | verify: delta since `b7cc885e`, PRIOR round 2; evidence READ 6–7 | Codex (medium); melious | Codex 102 s, 56,725 · melious 279 s, 36,540 | 0 / 0 / 1 |
| merge link (not a round) | `c71a4d5c` | `merge_link.sh 38bf1768 6ba70f63 3cf57d5e` (736 lines), PRIOR through round 3; evidence READ 8 | Codex (medium); melious | Codex 264 s, 88,364 · melious 663 s, 81,811 | 0 / 4 / 1 (Codex 0/1/0, melious 0/3/1), and one outside scope |
| wording pass (not a round) | `0371af4a` | the BUGLOG row added since `c71a4d5c` (1 line), `--wording-pass` | Codex | Codex 63 s, 43,972 | 0 / 0 / 0 |
| second merge link (not a round) | `1ecbce2a` | `merge_link.sh 3cf57d5e 0371af4a e7c68dbe` (2 BUGLOG rows from #485, prose), `--wording-pass` | Codex | Codex 90 s, 60,556 | 1 / 0 / 0, outside this change |

Three rounds, 15 findings; with the wording pass and two merge links, 11 seat runs, 661,407 tokens (the script's running total).

## Findings

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | RISK | Codex, GLM | 1 | The gate accepted any name the capture lists (`WORKERS_CI`, `WORKERS_CI_COMMIT_SHA`), since its builds set that name to a branch | fixed, externally_reverified | `b7cc885e`: only `WORKERS_CI_BRANCH`; mutations M10, M11 killed |
| A2 | BUG | Codex | 1 | A Worker deployed by command that kept `functions/go/email.ts` is not refused | deferred | owner, 2026-11-08; BUGLOG row of 2026-11-08 (EmailLink.astro) |
| A3 | BUG | Codex, GLM, fresh-eyes | 1 | `templates/astro/README.md:39` still said "four builds" | fixed, externally_reverified | `b7cc885e` |
| A4 | RISK | GLM | 1 | The gate required exactly one `enabled:` line in all of `config.ts` | fixed, externally_reverified | `b7cc885e`, then B1; P1 passes |
| A5 | NIT | GLM | 1 | ship's stall hint named only `*.pages.dev` | fixed, externally_reverified | `b7cc885e` |
| A6 | NIT | GLM | 1 | Release-note item 5 said ship.sh works "as it is" | fixed, externally_reverified | `b7cc885e` |
| A7 | RISK | fresh-eyes | 1 | ship's comment gave 300 s as the Workers build time; 42 s was seen on 2026-11-08 | fixed (wording), externally_reverified | `b7cc885e`: "the slowest Workers build seen" |
| A8 | NIT | fresh-eyes | 1 | The 2026-11-02 BUGLOG row still said 0.24 and the four-minute warning | fixed, externally_reverified | `b7cc885e` |
| A9 | NIT | fresh-eyes | 1 | The fixture's header dated the 2026-10-28 preview section 2026-11-08 | fixed, externally_reverified | `b7cc885e`: "read 2026-11-08" |
| B1 | BUG | Codex | 2 | A4's fix picked the `enabled:` line by `USE_ANALYTICS`, refusing a config from before that switch | fixed, externally_reverified | `6ba70f63`: picked by `process.env.`; P2 passes, the round-1 selector counts 0 lines there |
| B2 | BUG | Codex | 2 | README said a Workers build is refused, previews included; only a live build is | fixed, externally_reverified | `6ba70f63` |
| B3 | NIT | GLM | 2 | README line missing its verb | fixed, externally_reverified | `6ba70f63` |
| B4 | NIT | GLM | 2 | The gate comment read as if the builds would catch another name | fixed, then C1 | `6ba70f63` |
| B5 | NIT | GLM | 2 | The gate's message said "beside CF_PAGES_BRANCH", which the check does not require | fixed, externally_reverified | `6ba70f63` |
| C1 | NIT | Codex (as BUG), GLM | 3 | B4's comment says the builds cannot catch another name; with the name fixed they can | fixed, externally_reverified | `67b4a2e4`; re-sorted: a comment, nothing runs differently; both seats confirmed it in the merge link |
| M1 | RISK | Codex | link | A second `enabled:` line reading `process.env` elsewhere in `config.ts` fails the gate | follow-up | re-sorted: rare (the starter has one; the gate refuses loudly, naming the line); BUGLOG row of 2026-11-08 (the Workers name check) |
| M2 | RISK | GLM | link | T2–T5 rely on BSD `script` passing the child's exit status | refuted | #490's code; `SHIP_TEST_TTY=1 bash tests/check_ship_push.sh` on macOS: ✓, 384 real-git checks (318 without the T cases) |
| M3 | RISK | GLM | link | T2's "Not published" check may meet `report_leftovers` first | refuted | #490's code; the same run passed T2 |
| M4 | RISK | GLM | link | T8's stand-in uses `SHIP_T_REAL_SLEEP`, set nowhere | refuted | `check_ship_push.sh:983` sets it; the same run passed T8 |
| M6 | BUG | Codex | link 2 | #485's BUGLOG row (Bot Management `ai_agents`) says the field is "silently cleared"; the read-back would print it | outside this change | base-side text from #485, unchanged here; sent to the release manager |
| M5 | NIT | GLM | link | The ✓ line names the question's checks when T1–T8 were skipped | follow-up | #490's code, not this change's; sent to the release manager |

## Waivers and deferrals

- **A2**, deferred to row 2.1 (Workers for new sites). The owner's answer in this session, 2026-11-08: "Defer to row 2.1 (Recommended)". At the merge base `38bf1768` no build refuses server mode at all, so the case went wrong there too. No test pins today's result: such a build looks exactly like a Pages build (both pass `CF_PAGES_BRANCH`). That condition of the skill's deferral rule cannot be met; the owner deferred knowing that. Deferral not externally re-verified.

## Follow-ups

- Round 3, GLM, outside scope: the "about 5 minutes" in release-note item 4. Refuted: PLAN-READ 3 in round 1's evidence (the row-0.4 trial, about 300 s).
- Round 3, GLM, outside scope: markers read 0.25 in a 0.35 row. Not a defect of this change: the marker runs on its own count (v0.34 shipped ship.sh at 0.23; 0.24 and 0.25 both land in 0.35). The merge link's one outside-scope finding (Codex): `ship.sh`'s comment calls the marker "the website-builder release this revision ships in", which it no longer is. Older than this change; sent to the release manager.

## Notes

- Mutation check, by hand (the scratchpad's `mutate2.sh`): 12 mutations killed, 2 must-pass cases passed; listed in the PR body.
- After round 3 `origin/main` was merged twice (`754d9a9d`, then `1ecbce2a` for #485 and #486, whose BUGLOG rows GitHub could not merge). #490 also took ship.sh and its test from 0.24 to 0.25; both sides bumped the same line, and one 0.25 covers both changes within 0.35. A merge link reviewed it (the table above); nothing shipped since v0.34, whose ship.sh is 0.23.
- Codex asked UNVERIFIABLE questions about Cloudflare's variables, Astro's `process.env` handling and Plausible's counting. Each round's evidence held the READs (the real build captures, and the gate's builds across the modes); a live `/go/email` on a Worker was not read.
