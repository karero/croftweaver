# DIFF review — PR #228 — Guard mktemp in the test scripts that delete their temp folder
Base `739145f` · depth: Normal (named in the owner's task; the change is test-only, which the skill would have allowed at Light) · verdict: CLEAN · authority used: POST AUTHORITY — atom A (this session opened PR #228) and atom B (the owner's instruction to post the verdict as a PR comment); WORKTREE-WRITE — atom A (this session's own worktree); BRANCH-COMMIT — atom A (this session created the branch)

Data consent, quoted: the owner answered "Yes: Codex and melious.ai (Recommended)" to "OK to send this PR's diff (393 lines of shell scripts, Makefile, CI workflow and README; a grep for keys, tokens and addresses found nothing) to Codex and to melious.ai (GLM 5.3) for the Normal-depth review?" (2026-10-09). ollama-cloud received nothing (its CLI was kept off PATH); Antigravity was not used.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `9d47a13` | full: `739145f...9d47a13`, 393 lines | codex-cli 0.161.0, gpt-6.1-sol, effort from config, read-only; melious glm-5.3, HTTP API, text only; fresh-eyes: Claude Sonnet through the Agent tool, read-only by instruction, no shared context | codex 299 s / 58,405; melious 208 s / 31,767; fresh-eyes 1,118 s / 311,143 | 2/5/5 (14 raw, 12 after dedup) |
| 2 | `fe452e7` | delta `9d47a13..fe452e7`, 317 lines | codex medium; melious FAILED (stalled, stopped by the host after 1,731 s, curl exit 143) | codex 247 s / 67,140 | 1/1/0 |
| 3 | `c498e7f` | delta `fe452e7..c498e7f`, 70 lines | codex medium; melious glm-5.3 | codex 135 s / 35,141; melious 101 s / 9,055 | 1/0/0 |
| 4 | `eb20496` | delta `c498e7f..eb20496`, 50 lines | codex medium; melious glm-5.3 | codex 120 s / 26,169; melious 185 s / 12,820 | 0/1/0 |
| wording | `f6a0c7d` | delta `eb20496..f6a0c7d`, 10 lines (BUGLOG rows) | codex medium, `--seat codex` | codex 120 s / 40,931 | 2/0/0 |
| confirmation | `b9dd742` | delta `f6a0c7d..b9dd742`, 12 lines | codex medium, `--seat codex` | codex 74 s / 31,930 | 0/0/0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| R1-1 | BUG | codex, fresh-eyes | 1 | README, Makefile, clean.yml and the test header claim "every script" that builds a throwaway folder stops on a failed mktemp; `independent_review.sh` `run_agy` does not check it | fixed, externally_reverified (r2) | `fe452e7`: claims narrowed to the listed scripts, an EXEMPT table names the exceptions, BUGLOG rows |
| R1-2 | BUG | codex | 1 | the sentinel check compared file names only | fixed (see R2-1, R3-1) | `fe452e7`, `c498e7f`, `eb20496` |
| R1-3 | RISK | codex | 1 | `check_cdpath_safe.sh`: a second `mktemp` the always-failing stub never reaches, so its guard could vanish unseen | fixed, externally_reverified (r2) | `fe452e7`: one `mktemp`, `$tmp/decoy`, `$tmp/proj` |
| R1-4 | RISK | fresh-eyes, melious | 1 | the list is hand-kept; four already-guarded scripts unexplained; a new mktemp user is never forced onto a list | fixed, externally_reverified (r2) | `fe452e7`: EXEMPT table plus a completeness check; mutations run (drop an entry, add a stale one) |
| R1-5 | RISK | fresh-eyes | 1 | a guard that prints the message but forgets `exit` passes | fixed, externally_reverified (r2, r3) | `fe452e7`: the message must be the last line; see R2-2 |
| R1-6 | RISK | fresh-eyes | 1 | the self-test replayed one failure, so three `why_wrong` arms never fired | fixed, externally_reverified (r2) | `fe452e7`: a fixture per arm, eight now |
| R1-7 | RISK | melious | 1 | the CI tool precheck omits `npm` | refuted | `test_pre_push_hook.sh` checks `git` at line 21, calls `mktemp` at 27, looks up `npm` at 51 and `node` at 161; the loop was replaced by `REQUIRE_EVERY_SCRIPT` |
| R1-8 | NIT | fresh-eyes | 1 | a skipped script still ended in "all checks passed" | fixed, externally_reverified (r2) | `fe452e7`; `clean.yml` sets `REQUIRE_EVERY_SCRIPT=1` |
| R1-9 | NIT | fresh-eyes | 1 | a failed `cd` after `T=$(...) \|\| exit` empties `T` and leaks the folder | fixed, externally_reverified (r2) | `fe452e7`: `phys=...; T="$phys"` |
| R1-10 | NIT | fresh-eyes | 1 | commit `9d47a13` says it can be dropped on its own, and later fixes build on it | fixed in the PR text (history not rewritten, so the reviewed head stays reachable) | PR #228, "For you to decide" item 1 |
| R1-11 | NIT | fresh-eyes | 1 | `check_internal_links.sh` fails open on a failed mktemp (pre-existing, outside the diff) | follow-up | BUGLOG row (`f6a0c7d`, `b9dd742`); measured: "0 pages, 0 internal links", exit 0 |
| R1-12 | NIT | melious | 1 | no `timeout` on a stock Mac, so a runaway script could hang `make check` forever | refuted | an unguarded script runs to its normal end (`make check` takes about 2.5 min); comment reworded in `fe452e7` |
| R2-1 | BUG | codex | 2 | `$(cat sentinel)` drops trailing newlines | fixed (see R3-1) | `c498e7f` |
| R2-2 | RISK | codex | 2 | "the message is the last line" does not prove the script stopped at it | fixed by narrowing the claim, externally_reverified (r3, both seats) | `c498e7f`: the header states the gap |
| R3-1 | BUG | codex | 3 | bash 3.2 drops NUL bytes inside `$(...)`, so "byte for byte" overclaimed | fixed, externally_reverified (r4) | `eb20496`: `cksum` before and after, a NUL fixture; mutation runs: the old comparison turns only the NUL fixture red, a plain `$(cat ...)` turns the newline and NUL fixtures red |
| R4-1 | RISK | melious | 4 | the claim that `cksum` sees every byte, NUL included, has no support in the review | refuted | measured on macOS (BSD) and in a Linux container (GNU): `printf 'a'` gives `1220704766 1`, `printf 'a\0'` gives `3130775862 2`, `printf 'a\n'` gives `2418082923 2`, `printf 'a\n\n'` gives `853898590 3`; Codex reproduced it on all 256 byte values |
| W1 | BUG | codex | wording | a BUGLOG row said `whats-new` reports a fix "to every existing site"; it reports from each site's baseline | fixed, confirmed | `b9dd742` |
| W2 | BUG | codex | wording | a BUGLOG row said Antigravity "takes `--with-antigravity`" (`--seat agy` and `WITH_ANTIGRAVITY=1` also start it) and asserted an `rm -rf ""` result that was never run | fixed, confirmed | `b9dd742` |

Waivers and deferrals: none. No BUG was deferred.
Follow-ups: the two BUGLOG rows. `independent_review.sh` runs the Antigravity tier in the caller's folder if `mktemp` fails (measured with a stub); `check_internal_links.sh` prints "0 pages" and exits 0 if `mktemp` fails (measured). Neither deletes anything; the mktemp test lists both as exempt.
UNVERIFIABLE entries: round 1 had 11, of which the macOS `mktemp` fallback, `cd ""` on bash 5, the `set -e` claim, the SKIP convention and the ruleset were settled by measurement (the ruleset went to the PR text), and the completeness question became R1-4; later rounds had 14 more (round 2: 3; round 3: 4; round 4: 3; wording pass: 3; confirmation: 1), none confirmed as a finding except the unrun `rm -rf ""` claim, which became W2.
Notes: round 2 had one counted seat (the GLM request stalled and was stopped), so the GLM chain breaks there; the stamp relies on Codex, whose chain is unbroken from round 1 through the confirmation. Fresh-eyes ran in round 1 only, as Normal depth has it. Round 4 was earned by R3-1, a substantive BUG; it is the only round past 3. The wording pass called my own scope text ("you may rely on") an attempt to relax evidence requirements: it was my wording, and the next scope text will say "re-check".
