# DIFF review — live analytics check after a publish (`check_live_analytics.py`, launch check §8)

Plan: `docs/reviews/SKILL-PLAN-live-analytics-check.md` (PLAN gate closed, trail beside this file).
Depth: Normal (a script a site's owner runs; no box, user data, login, money, deletion or schema).
Seats: Codex gpt-6.1-sol alone in rounds 1 to 5 (melious out of balance, no rerun owed); Codex and
GLM 5.3 on melious (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`) from round 6. Built by the build
session `local_4be595ef` (rounds 1 to 5) and `local_1f478129` (rounds 6 to 11, after the account
switch and a rebase onto `9f7d3ff6`). Gate 20261109T210813Z-33270.

Rounds 1 to 5 were written up from the commit messages and the cost log: the old session's
findings files were not kept, so the per-finding detail for rounds 3 to 5 is not recorded here.

## Rounds

| Round | Head | Artifact | seconds, tokens | Result |
|---|---|---|---|---|
| 1 | `91ffdf4a` | whole change | Codex 163 s, 53,096 | 3 BUG, 1 RISK, 0 NIT: unreadable mode defaulted to script; truncated reply and non-UTF-8 config escaped as exit 1; "sends no visits" unsupported. Fixed in `210f6806` |
| 2 | `570ce058` | verify | Codex 158 s, 44,867 | 1 BUG, 1 RISK: `mode : 'server'` and quoted keys bypassed the mode check; "does not load the script" overclaimed. Fixed in `d9f8477c` |
| 3 | `d9f8477c` | verify | Codex 138 s, 45,145 | fixed in `fdca0404` (any other line naming mode refused); findings not recorded |
| 4 | `fdca0404` | verify; kind `mode-key-syntax` | Codex 145 s, 41,060 | fixed in `d09a8c91` (a mode line is read whole or refused); findings not recorded |
| 5 | `d09a8c91` | verify; `mode-key-syntax`, cut: two syntax-by-syntax mode readers | Codex 135 s, 45,907 | fixed in `8f1649fb` (computed keys, comments, unclosed comment); findings not recorded |
| 6 | `6c5348ae` (rebased on `9f7d3ff6`) | whole change; cut: the comment scanner `code_of` deleted, `/*` in the block refused | Codex 179 s, 72,297 · melious 320 s, 58,619 | Codex 3 BUG; GLM 2 RISK, 3 NIT |
| 7 | `668d1d2e` | verify since `6c5348ae`; `mode-key-syntax,config-line-syntax` | Codex 165 s, 28,677 · melious 241 s, 16,804 | Codex 3 BUG (one a false test comment); GLM 0 BUG, 2 NIT |
| 8 | `caa3440f` | verify since `668d1d2e`; cut: a whitelist of block lines replaces the per-property patches | Codex 229 s, 35,042 · melious 530 s, 34,315 | Codex 2 BUG, GLM 0 BUG, 2 NIT |
| 9 | `23da3ae8` | verify since `caa3440f`; grant: Daniel, "Run round 9" (2026-11-10) | Codex 180 s, 33,387 · melious 241 s, 13,557 | Codex 1 BUG, GLM 0 BUG, 1 NIT |
| 10 | `8c5e00e1` | verify since `23da3ae8`; grant: Daniel, "Run round 10" (2026-11-10) | Codex 109 s, 24,000 · melious 217 s, 11,980 | Codex 0 BUG, 1 NIT; GLM 1 BUG, 1 NIT |
| 11 | `60142951` | verify since `8c5e00e1`; grant: Daniel, "Run round 11" (2026-11-10) | Codex 160 s, 26,869 · melious 436 s, 23,663 | Codex 1 BUG; GLM 2 RISK, 1 NIT |

## Round 6 to 11 findings

| id | Sev | Source | Round | Finding | Status |
|---|---|---|---|---|---|
| 6a | BUG | Codex | 6 | A commented `export const USE_ANALYTICS = true;` overrode the live `false` | fixed: a `/*` anywhere in the file exits 2 (`668d1d2e`) |
| 6b | BUG | Codex | 6 | `export const ANALYTICS = { mode: 'server',` defaulted to script | fixed: the opening line must be `{` alone (`668d1d2e`) |
| 6c | BUG | Codex | 6 | `scriptHost: '…' + '/proxy'` was read as its literal prefix | fixed: host and id lines must be a plain quoted value; a second one exits 2 (`668d1d2e`) |
| 6d | RISK | GLM | 6 | No test reads the starter's real config | fixed: `test_the_starters_own_config_is_read` |
| 6e | RISK | GLM | 6 | The gate test might skip silently | refuted: `make test-launch-check` sets `LAUNCH_CHECK_REQUIRE_STARTER=1`; Codex and GLM both verified it in round 7 |
| 6f | NIT | GLM | 6 | `cb` hex drops leading zeros (flaky test) | fixed: `:010x` |
| 7a | BUG | Codex | 7 | `enabled: true, mode: 'server',` still defaults to script | fixed in `caa3440f`: whitelist of block lines |
| 7b | BUG | Codex | 7 | A later `scriptHost: '…' + '/proxy'` or `'scriptId': …` escapes the duplicate check | fixed in `caa3440f`: same whitelist |
| 7c | BUG | Codex | 7 | Test comment said every case evaluates differently in Node; two do not | fixed: comment reworded |
| 8a | BUG | Codex | 8 | `enabled: {` passes and a nested object replaces outer values | fixed in `23da3ae8`: no comma, brace or bracket in the enabled value; test |
| 8b | BUG | Codex, GLM NIT | 8 | `A` and `\x2e` in a host or id are not decoded | fixed in `23da3ae8`: a backslash in the value refuses the file; tests |
| 8c | NIT | GLM | 8 | `block[1:]` invariant; enabled-line comment | fixed: both commented |
| 9a | BUG | Codex | 9 | A multi-line template literal in `enabled` hides nested mode, host and id lines | fixed: a backtick in the enabled value refuses the file; test |
| 9b | NIT | GLM | 9 | The enabled-line comment blamed the comma | fixed: comment names brace, bracket and backtick |
| 10a | BUG | GLM | 10 | `enabled: PROD /*` opens a hidden comment | refuted: any `/*` in the file exits 2 before the line checks; regression case added |
| 10b | BUG | GLM | 10 | `enabled: "x\` (line continuation) swallows later lines | fixed: a backslash in the enabled value refuses the file; test; the old class accepts it, the new does not |
| 10c | NIT | Codex | 10 | The backtick test passed on the old regex too | fixed: the case now opens the template on the enabled line |
| 10d | NIT | GLM | 10 | The comment listed an incomplete set of characters | fixed: reworded |
| 11a | BUG | Codex | 11 | The `//` comment tail of the enabled line still takes a backslash (`enabled: "x // \`) | fixed: the tail may not hold a backslash; test |
| 11b | RISK | GLM | 11 | The `/*` regression case failed on the whitelist, not on the file-wide refusal | fixed: every other line is now valid; mutation (file-wide check off) fails exactly that case |
| 11c | RISK | GLM | 11 | `enabled: PROD /*` rests on a check outside the diff | refuted: the check is `if "/*" in text` in `read_config`, shown by 11b's mutation |
| 11d | NIT | GLM | 11 | `enabled: 'x` (unterminated) or `PROD */` read as valid | declined: both fail a build; the check refuses wrong readings, it does not parse JavaScript |

## State

Tests: `make test-launch-check`, 54 tests, OK at `23da3ae8`. Live run against the guide's real
`src/config.ts` and https://guide.croftweaver.com/ at `caa3440f`: exit 0.
The fix of 11a is not re-reviewed: Daniel chose "Push, no round 12" (2026-11-10). It is a one-character regex change with a test, and a mutation shows the test fails without it (past the round-8 stop).
Totals through round 11: 17 seat runs, about 612,000 tokens (the script's running total; round 8 stood at 475,829).
