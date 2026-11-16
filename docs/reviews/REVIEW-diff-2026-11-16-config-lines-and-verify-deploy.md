# DIFF review — branch fix/config-lines-and-verify-deploy — the config.ts checks name the missing line, and verify needs the deploy scripts

Base `07211892` · depth: Normal (two starter tests, the starter's verify script and the update
report; no user data or auth; the deploy path is read, not changed) · verdict: CLEAN after round 4, a wording pass and a confirmation ·
authority used: WORKTREE-WRITE and BRANCH-COMMIT. This session (the small BUGLOG sweep) created the
worktree and the branch.

Artifact: round 1 `git diff 07211892...93ac3e08 -- . ':(exclude)docs/reviews/'`; round 2 `git diff
93ac3e08..3814fa2e` (same exclusion), with `--base 93ac3e08`. Round 3 `git diff 3814fa2e..02d73dec`, with `--base 3814fa2e`. Round 4 `git diff 02d73dec..0f2464e5`, with `--base 02d73dec`, `--earned-by deploy-script-match --cut "removed the deploy-script parser: verify takes only the starter's two lines"`. Wording pass `git diff 0f2464e5..e68b7313`, with `--base 0f2464e5`; confirmation `git diff e68b7313..b708c512`, with `--base e68b7313`; both Codex alone. Evidence: round 1
`scripts/test_verify.sh` and `scripts/test_config_lines.sh` on 93ac3e08 and on a copy with
origin/main's `whats-new.sh`, `verify.mjs`, `check_analytics_gate.sh` and `check_deploy.sh` put
back. Gate id 20261116T145245Z-81888. Round 1 started before its `make check`; the run that
followed was spoiled by the round-1 fixes landing during it, so the final head gets a clean run.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `93ac3e08` | full, merge base with origin's HEAD | Codex (gpt-6.1-sol, read-only); melious (glm-5.3, HTTP API, text only); fresh-eyes (Claude Sonnet sub-agent, read-only) | codex 162 s, 63,541; melious 353 s, 24,938; fresh-eyes 116 s, 143,571 | 2 / 3 / 4 after dedup |
| 2 | `3814fa2e` | delta from `93ac3e08`, verify of F1-F9 | Codex (medium); melious | codex 504 s, 47,186; melious 225 s, 18,737 | 2 / 1 / 2 |
| 3 | `02d73dec` | delta from `3814fa2e`, verify of F10-F14 | Codex (medium); melious | codex 147 s, 47,526; melious 177 s, 15,868 | 2 / 1 / 2 |
| 4 | `0f2464e5` | delta from `02d73dec`, verify of F1-F18 | Codex (medium); melious | codex 204 s, 46,234; melious 140 s, 11,077 | 0 / 0 / 2 |
| wording | `e68b7313` | the round 4 fixes and the BUGLOG rows | Codex (medium), `--wording-pass` | codex 75 s, 42,120 | 3 / 0 / 0 |
| confirm | `b708c512` | delta from `e68b7313` | Codex (medium), `--wording-pass` | codex 48 s, 46,161 | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex, fresh-eyes (RISK) | 1 | The gate gave a site made before the switch the starter's enabled: line, which reads USE_ANALYTICS; that site has no such line, so pasting it broke the build. | fixed in `3814fa2e` | Every message that gives the line also says to add `export const USE_ANALYTICS = true;` when `src/config.ts` names no USE_ANALYTICS. Two cases in `test_config_lines.sh` fail on 93ac3e08. |
| F2 | BUG | Codex, melious (NIT) | 1 | verify checked only that the two deploy scripts exist, though its comment said they run `deploy.sh`; `"deploy:live": "echo hi"` passed. | fixed in `3814fa2e` | Each script must name `scripts/deploy.sh`. The case "a deploy:live that does not run deploy.sh" fails on 93ac3e08. |
| F3 | RISK | Codex, melious (NIT), fresh-eyes (NIT) | 1 | The `make whats-new` case ignored the exit status, and its site had no skills stamp, so the report ended in an error the test never saw. | fixed in `3814fa2e` | The site gets a skills stamp and the case asserts exit 0. It passes on 93ac3e08 too: the report was right, the test was weak. |
| F4 | RISK | fresh-eyes | 1 | The report's new line, "the test names any line it lacks", was false for USE_ANALYTICS in the gate. | fixed in `3814fa2e` | With F1 the gate names it; check_deploy.sh named it already. |
| F5 | RISK | melious | 1 | verify's comment, that `tests/check_deploy.sh` tests the deploy scripts in the toolkit's CI, had no support. | refuted | `check_deploy.sh` lines 156 to 165 run `deploy:live` and `deploy:preview` with `--dry-run`; `.github/workflows/template-tests.yml` lines 161 and 188 run it. The comment now names the command. |
| F6 | NIT | melious, fresh-eyes | 1 | A package.json that is not valid JSON ended verify in a stack trace. | fixed in `3814fa2e` | One line, "✗ verify: package.json is not valid JSON (…)". The case fails on 93ac3e08. |
| F7 | NIT | fresh-eyes | 1 | No test covers the gate's message after the Workers live build (`check_analytics_gate.sh` line 780 at 93ac3e08). | no change | It prints only after a real build, which needs `npm ci` and is not run by these tests. Mutation M8 survives for that reason; the other six of the seven mutations at 93ac3e08 were killed. |
| F8 | NIT | fresh-eyes | 1 | The README's list of scripts lacked `test_config_lines.sh`. | fixed in `3814fa2e` | Added after `test_verify.sh`. |
| F9 | NIT | melious | 1 | `check_cdpath_safe.sh` said `test_verify.sh` needs node; it also needs a real npm. | fixed in `3814fa2e` | The note says so. |
| F10 | BUG | Codex | 2 | F2 half done: verify took any script naming `scripts/deploy.sh`, so `"deploy:live": "echo scripts/deploy.sh live"` passed. | fixed in `02d73dec` | Each script must run deploy.sh as a command, in its own mode. Cases "only echoes the path" and "runs the preview mode" fail on 3814fa2e; `./scripts/deploy.sh` and a command after `&&` stay green. |
| F11 | BUG | Codex | 2 | The JSON message was not one line: Node's error for a file broken across lines holds newlines. | fixed in `02d73dec` | Whitespace in the error folds to spaces. The multi-line case prints 3 lines on 3814fa2e and 1 now. |
| F12 | RISK | melious | 2 | The hint looked for any `USE_ANALYTICS`, and the starter's enabled: line names it, so a site that pasted that line but lacked the export got no hint (F1's case). | fixed in `02d73dec` | Only the export counts. The case "enabled: line pasted, no export" fails on 3814fa2e. |
| F13 | NIT | melious | 2 | The README line said the tests cover every config.ts message; they cover those before a build. | fixed in `02d73dec` | It says "before a build". |
| F14 | NIT | melious | 2 | The hint added after the Workers live build is covered by no test. | no change | The same gap as F7: that message prints only after a real build. |
| F15 | BUG | Codex, melious (NIT) | 3 | F10 came back: `echo 'release; scripts/deploy.sh live '` passed, the separator hidden in an echo's quotes. | fixed in `0f2464e5` (a cut) | The parser is gone: each script must be the starter's line exactly, and the message says no other form counts. That case fails on 02d73dec. |
| F16 | BUG | Codex | 3 | The F10 parser refused a working command, `bash scripts/deploy.sh live; echo done`. | refused on purpose in `0f2464e5` | The same cut: only the starter's line counts, and the message says so. A test pins that a command around the starter's line fails. |
| F17 | RISK | melious | 3 | The parser refused a run after `\|\|`, `\|` or `&`. | refused on purpose in `0f2464e5` | As F16. |
| F18 | NIT | melious | 3 | The hint's export check misses an indented or typed `USE_ANALYTICS` export. | no change | The gate itself takes only `export const USE_ANALYTICS = true;` or `false;` at the line start and fails any other form with its own message, so the hint looks for the form the gate takes. |
| F19 | NIT | melious | 4 | The comment said a shell command "cannot be told apart" from text naming deploy.sh; a quote-aware parser could. | fixed in `87e28532`, cut in `b708c512` | It says verify does not parse shell, so it cannot tell them apart. |
| F20 | NIT | melious | 4 | With round 2's green `./scripts/deploy.sh` case gone, nothing pinned that it now fails. | fixed in `87e28532` | Case "the same script run another way". On a copy with 02d73dec's `verify.mjs` the new test file fails 4 checks, this one among them; on 87e28532 it passes, 57 ok. |
| F21 | BUG | Codex | wording | Rows 325 and 345 said both checks name each line, `enabled:` included; `check_deploy.sh` never reads `enabled:`, and the gate passes a missing `USE_ANALYTICS` that nothing names. | cut in `b708c512` | The rows say the checks name the lines they find missing. |
| F22 | BUG | Codex | wording | Test lines in a wording pass. | refuted | They are F20's fix, a round 4 NIT, with its runs in the evidence. |
| F23 | BUG | Codex | wording | "Exactly" is wider than `verify.mjs`, which trims the value first. | fixed in `b708c512` | The word is gone from the rows; the message's "exactly as they are" stands, since padding is the only difference it takes. |

Mutation check on `87e28532` (the code is unchanged since, but for the comment cut in `b708c512`),
base `07211892`, tests `scripts/test_verify.sh` and `scripts/test_config_lines.sh`: 10 mutations (the
fix's hunks reverted one at a time, and four hand-made breaks: verify taking any line that names
deploy.sh, or one that contains the starter's line; the JSON error kept on many lines; the hint's
check taking any mention of `USE_ANALYTICS`), 9 killed, 1 survived. M8 puts back the old message
after a Workers live build, the path no test reaches without a real build (F7, F14).

Rebased onto main after #574 merged (cef99c83); the hashes above are from before the rebase.
`docs/BUGLOG.md` merges with git's union driver, so the rebase kept both versions of four rows
(the base's open rows 325-327 and an earlier draft of row 325); `make check`'s row guard caught
them on `8cac1fd6`, and the next commit deleted them. Old → new: 93ac3e08 → 1e7aae0d, 3814fa2e → fa7c046a, 02d73dec → 589ec99a, 0f2464e5 →
8e85a35f, 87e28532 → 0ecc787c, e68b7313 → 1e874382, b708c512 → e8caab3e, 485f4f16 → 41ccc37b. On the
rebased head, `test_whats_new.sh`, `test_whats_new_removed_skill.sh`, `test_config_lines.sh` and
`test_verify.sh` all pass (both branches change `scripts/whats-new.sh`).
