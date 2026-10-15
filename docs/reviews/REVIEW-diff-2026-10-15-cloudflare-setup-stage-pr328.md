# Review trail: Cloudflare setup script, the setup stage (karero/croftweaver#328)

Base `8f7c98b` · depth: High (the maintainer chose High for this plan: the script changes a Cloudflare account with a token and can make a site public) · verdict: in progress

The diff is over the gate script's 117 KB limit, so each round goes in two parts: A (the script, Makefile, CI, the check script's line, and the plan's requirements, scenarios and setup stage as an excerpt for the text-only seat) and B (tests, stub, fixture cleaner, fixture index, prose). The 81 fixture files are read in the tree by the seats that can open files. Part A's run starts the gate (`--round 1`); part B's run attaches to it.

Explicit item of this gate (the maintainer's waiver of Z3, with V15 and V16, in `REVIEW-plan-2026-10-14-pr320.md`): the plan's capture-based claims are checked against the committed fixtures: PATCH preservation, deployment classification by stages, the Bot Management fields, the ruleset calls.

## Rounds

| Round | Head | Scope | Seats | Time, tokens | Findings (BUG / RISK / NIT) |
|---|---|---|---|---|---|
| 1 | `7f16d98` | full, in parts A and B; fixtures read in the tree | Codex (gpt-6.1-sol, config effort) and Melious (glm-5.3) on each part; fresh-eyes (Claude Opus 5.5) on the whole | Codex A 467 s, 125,459 · Melious A 722 s, 63,937 · Codex B 435 s, 126,290 · Melious B 742 s, 71,186 · fresh-eyes 455 s, 229,816 | 8 / 9 / 10 after merging duplicates. UNVERIFIABLE asked: 7, confirmed as findings: 2 (R1-13, R1-14) |
| 2 | `9944d9c` | verification: the change since `7f16d98` (60 KB, one part), prior findings R1-01 to R1-27 | Codex (config effort); Melious FAILED (no reply within 900 s), ollama (glm-5.3:cloud) in its place; fresh-eyes (Claude Opus 5.5) | Codex 488 s, 109,202 · Melious 900 s, failed · ollama 541 s, no token figure · fresh-eyes 401 s, 184,003 | 3 / 4 / 10 after merging duplicates. R1-01 (one key for two build settings), R1-02, R1-03, R1-04 and R1-17 confirmed only in part; the rest confirmed |
| 3 | `906fdfb` | verification: the change since `9944d9c` (41 KB; the fixture files renumbered by T1-019 left out but T1-019), prior findings R1 and R2 | Codex (config effort); Melious FAILED again (900 s), ollama (glm-5.3:cloud) in its place; fresh-eyes (Claude Opus 5.5) | Codex 405 s, 118,477 · Melious 900 s, failed · ollama 766 s, no token figure · fresh-eyes 553 s, 183,893 | 4 / 2 / 6 after merging duplicates. R2 fixes confirmed, apart from R2-04 (R3-03) and R2-16's side effect (R3-01). Two kinds came back: the deadline's hold on git's children (R1-06, R3-01) and the fixture check (R1-17, R2-04, R3-03); both were cut, not patched |

## Findings

| Id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| R1-01 | BUG | fresh-eyes, Codex A, Codex B | 1 | The code does not bind the build's commit or the lines the question listed; the reference said any change to what the question covers voids the code | fixed, locally_verified: the maintainer chose to bind the list (2026-10-15, below) | the code covers the end state and the listed lines, the build with its commit; a later run takes any part of the list; tests: a setting changed after the question asks again, a moved production branch asks again, a cut-off run carries on; plan judgment call 1 and §S follow |
| R1-02 | BUG | fresh-eyes | 1 | Checklist: "fields it does not change sent as they are" is wrong for `is_robots_txt_managed` and, with `--skip ai`, `bot_preference_sync_enabled` | fixed, locally_verified | checklist §6 names both exceptions |
| R1-03 | RISK | fresh-eyes, Codex A, Codex B | 1 | Decisions (domains, variables, Fail open) rest on the projects list, which no capture shows | fixed, locally_verified | the project is read by name (T1-054's shape); test: a list item without domains still stops on a live project |
| R1-04 | RISK | fresh-eyes; Melious B (NIT) | 1 | The empty multipart form's bytes are not in any fixture; the stub ignores the form | fixed, locally_verified | T1-030's fixture records the trial helper's form; test 1 compares; the stub refuses any other body |
| R1-05 | RISK | fresh-eyes, Melious A | 1 | "failure" and the running statuses rest on one word each | fixed, locally_verified | failed = neither skipped, running nor succeeded; test with `canceled` |
| R1-06 | BUG | Codex A | 1 | The deadline did not bound a program whose children hold its output open | fixed, locally_verified | process group, timed stop; test with a git whose child holds stdout; fails with the old code |
| R1-07 | BUG | Codex A | 1 | With the zone's records unreadable, zone-wide settings were written with no hosts named (R5) | fixed, locally_verified | changing lines held back "by hand" with the DNS row; test |
| R1-08 | BUG | Codex A | 1 | A proxied CNAME to the right target counted as "there already" | fixed, locally_verified | "by hand" with the fix; test |
| R1-09 | RISK | Codex A | 1 | Over 200 pages a list was used in part | fixed, locally_verified | the run stops; test with 201 pages |
| R1-10 | BUG | fresh-eyes (NIT), Codex A, Codex B | 1 | T1-021's excerpt called all three `ad_hoc` deployments uploads; one was built by Cloudflare | fixed, locally_verified | the cleaner classifies by stages; README follows |
| R1-11 | BUG | Codex B; Melious A (RISK) | 1 | `.dev.vars` checks ran in the current folder, the file read was the root's | fixed, locally_verified | `git -C <root>`; test from `src/pages` |
| R1-12 | BUG | Codex B | 1 | Test 33's "second zone on page 2" never reached page 2 | fixed, locally_verified | the stub caps the page; the test asserts page 2 was read |
| R1-13 | RISK | Codex A, Codex B, Melious A | 1 | A PATCH keeping secrets' values is unsupported: secrets read back empty | waived (maintainer, 2026-10-15): observed on the first real site, plan step 10 | names are kept (T1-048 to T1-061); values cannot be read through the API |
| R1-14 | RISK | Codex A, Codex B, Melious B | 1 | Leaving `is_robots_txt_managed` out of the PUT was never tried | waived (maintainer, 2026-10-15): observed on the first real site, plan step 10 | the read-back makes any field that moved "by hand" with status 1 (test 13b) |
| R1-15 | RISK | Melious B | 1 | `enable_js` and `cf_robots_variant` might be set, not echoed | refuted | the PUT body takes them from the read (`BOT_PUT_FIELDS`); test 13 now pins non-default values sent as read |
| R1-16 | RISK | Melious B | 1 | The Transform Rules row is asked for, and setup ends 0 without the NEL rule | fixed, locally_verified | §S and the report say the rule is launch day's |
| R1-17 | RISK | Melious B | 1 | The made-up test cannot catch free text such as a person's name | fixed, locally_verified | every free-text string is checked against a list; a planted name fails it |
| R1-18 | NIT | Melious A | 1 | Two predicates for "builds no previews" | fixed, locally_verified | one predicate |
| R1-19 | NIT | Melious A | 1 | An unused array in `main` | fixed, locally_verified | removed |
| R1-20 | NIT | Melious A | 1 | A port above 65535 passed the loopback check | fixed, locally_verified | refused; test |
| R1-21 | NIT | Melious B | 1 | Test 4 pinned the method and body, not the path | fixed, locally_verified | path pinned |
| R1-22 | NIT | Melious B | 1 | The wrong-command test could reach the real API if the order changed | fixed, locally_verified | a closed loopback port for every case |
| R1-23 | NIT | Melious B | 1 | One `--skip ai` id covers several checklist rows | fixed in docs, locally_verified; the omitted field under `--skip ai` is the plan's (script step 5) | §S says what `ai` covers |
| R1-24 | NIT | fresh-eyes | 1 | The stub's Bot comment was wrong, and it refused `true` alone | fixed, locally_verified | refuses the pair, answers with the object |
| R1-25 | NIT | fresh-eyes | 1 | The plan said seven days, the script and reference eight | fixed, locally_verified | plan line 252 |
| R1-26 | NIT | fresh-eyes | 1 | The plan said `is_robots_txt_managed: true` "alone" was refused | fixed, locally_verified | plan row says both requests sent `policy_only` |
| R1-27 | NIT | fresh-eyes | 1 | ssh waiting on a terminal looks like a slow Cloudflare | fixed, locally_verified | ls-remote past the deadline is said as git; with R1-06 |
| R2-01 | BUG | Codex | 2 | One key, `project:build_config`, covered two edits: a yes to the build command also wrote an output folder changed later | fixed, locally_verified | one key per build setting; test: a yes to one build setting is not a yes to another |
| R2-02 | BUG | fresh-eyes | 2 | The checklist named two fields left out of the Bot Management PUT; four are | fixed, locally_verified | the checklist names the nine fields sent and says every other is left out |
| R2-03 | RISK | fresh-eyes | 2 | Which project is connected, or Direct Upload, still came from a list no capture showed | fixed, locally_verified | T1-019 (the account's list, cleaned) committed: items carry source, domains, settings; Direct Upload has no source; the script re-checks the connection on the project it reads; test |
| R2-04 | RISK | Codex; fresh-eyes (NIT) | 2 | The free-text check missed a single lower-case or accented word | fixed, locally_verified | letters outside ASCII count; fields that name something are checked against a list; a planted "Élodie" and a named branch fail |
| R2-05 | RISK | Codex; fresh-eyes (UNVERIFIABLE) | 2 | The empty form's bytes rested on the cleaner's word | fixed, locally_verified | the trial's helper is committed (`trial-helper.txt`, local paths replaced); the cleaner reads the form from it; a test compares |
| R2-06 | BUG | Codex | 2 | The fixture README claimed every free-text string was checked | fixed, locally_verified | it says what is checked, and what would pass |
| R2-07 | RISK | ollama | 2 | A project with no `preview_deployment_setting` now reads as building no previews | refuted | every captured project with a source carries the field (T1-019, T1-027, T1-054, T2-021; T1-019's Direct Upload project has no source and is refused before the predicate); the plan treats every value but `all` so ("Not verified" 10); the advice to push production is on the owner's word |
| R2-08 | NIT | fresh-eyes | 2 | The deadline message blamed an ssh prompt, which the new process group rules out | fixed, locally_verified | "a program git started did not end" |
| R2-09 | NIT | fresh-eyes | 2 | The reference did not say that old values are not bound | fixed, locally_verified | §S says so, with the case |
| R2-10 | NIT | fresh-eyes | 2 | "the hosts the list names": the code takes the zone's proxied hosts whenever a setting is in | fixed, locally_verified | §S says "the zone's proxied hosts" |
| R2-11 | NIT | fresh-eyes, Codex | 2 | The cleaner's comment still said three uploads; its count read only `build` | fixed, locally_verified | comment; both stages idle |
| R2-12 | NIT | fresh-eyes | 2 | A by-hand line began lower-case | fixed, locally_verified | capitalised; test |
| R2-13 | NIT | fresh-eyes, ollama | 2 | The five-record cap was only in `--help` | fixed, locally_verified | §S says it, and why |
| R2-14 | NIT | fresh-eyes | 2 | A deployment between two stages, or with no stage, read as failed | fixed, locally_verified | running covers both; unit asserts |
| R2-15 | NIT | ollama | 2 | On Windows only the direct child is stopped | fixed, locally_verified (comment) | the comment says POSIX stops the group, Windows the program, and the run goes on either way |
| R2-16 | NIT | ollama | 2 | The second timer was not cleared when the program ended | fixed, locally_verified | cleared in `settle` |
| R2-17 | NIT | ollama, outside scope | 2 | Test 40's title says "a week at most" | refuted | the title quotes the checklist §6, which says that; the script's eight days is the counted form |
| R3-01 | BUG | Codex | 3 | R2-16 cleared the second timer when git ended, so a child that ignored SIGTERM outlived the deadline | fixed by a cut, locally_verified | the SIGTERM grace and both timers are gone: at the deadline the group is killed at once and the run goes on; test: a SIGTERM-ignoring child with closed output is gone after the run; with SIGTERM instead the test fails |
| R3-02 | BUG | fresh-eyes | 3 | The committed helper's `#!/bin/bash` line made the shell-script guards count it; `cdpath-safe` failed in CI | fixed, locally_verified | the cleaner turns that line into a comment; `scripts/list_shell_scripts.sh` no longer lists the file |
| R3-03 | BUG | Codex (README); ollama, fresh-eyes (RISK) | 3 | The fixture check still let a branch in `production_branch`, a root folder, a flag or a host label through, and the README said otherwise | fixed by a cut, locally_verified | every string and key must be a made-up id by pattern or on `allowed-values.json` (104 strings, 61 parts, 153 keys, read before committing); a test plants 13 values earlier checks missed and each fails |
| R3-04 | BUG | ollama; fresh-eyes (NIT) | 3 | The checklist said fields left out kept their values, `is_robots_txt_managed` included, which was never tried (R1-14) | fixed, locally_verified | the checklist says which field was seen kept, and that the first real site shows the other |
| R3-05 | RISK | ollama; fresh-eyes (NIT) | 3 | A real 64-character hash (`wrangler_config_hash`) passed into T1-019 | fixed, locally_verified | the cleaner makes 64-character hashes up; the check's patterns know them |
| R3-06 | RISK | fresh-eyes; ollama (NIT) | 3 | The re-check of the project read by name had no test | fixed, locally_verified | test: the list says connected, the project read says otherwise: status 1, reads only |
| R3-07 | NIT | fresh-eyes | 3 | The stub's header still called the list of projects made up | fixed, locally_verified | header |
| R3-08 | NIT | fresh-eyes | 3 | "left out" where the cleaner sets null | fixed, locally_verified | README, excerpt |
| R3-09 | NIT | ollama | 3 | The README named six of ten checked keys | fixed, locally_verified | superseded by R3-03's README text |
| R3-10 | NIT | ollama | 3 | The build-setting keys were written out twice | fixed, locally_verified | derived from `BUILD` |
| R3-11 | NIT | ollama | 3 | `running(undefined)` read as true | fixed, locally_verified | guarded |
| R3-12 | NIT | ollama, outside scope | 3 | R2-07's refutation said "every captured project"; T1-019's Direct Upload one has no source | fixed, locally_verified | the row says "every captured project with a source" |

The waiver's review item, round 1: all three seats with file access read the fixtures. PATCH preservation VERIFIED for names, plain values, build settings, branch and Fail open (values of secrets: R1-13); deployment classification VERIFIED (the excerpt's label: R1-10); Bot Management VERIFIED for the fields, the 10400 pair and fields left out (leaving out `is_robots_txt_managed`: R1-14); ruleset calls VERIFIED (the setup stage makes none). Fixtures free of real values: VERIFIED by Codex A, Codex B and fresh-eyes.

Decisions by the maintainer, 2026-10-15, asked after round 1 with the recommendation and the case against each. R1-01: "Bind the list (Recommended)". R1-13 and R1-14: "Waive both (Recommended)", to be observed on the first real site (plan step 10).
