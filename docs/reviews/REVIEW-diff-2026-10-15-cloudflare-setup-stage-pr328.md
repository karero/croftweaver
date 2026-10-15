# Review trail: Cloudflare setup script, the setup stage (karero/croftweaver#328)

Base `8f7c98b` · depth: High (the maintainer chose High for this plan: the script changes a Cloudflare account with a token and can make a site public) · verdict: in progress

The diff is over the gate script's 117 KB limit, so each round goes in two parts: A (the script, Makefile, CI, the check script's line, and the plan's requirements, scenarios and setup stage as an excerpt for the text-only seat) and B (tests, stub, fixture cleaner, fixture index, prose). The 81 fixture files are read in the tree by the seats that can open files. Part A's run starts the gate (`--round 1`); part B's run attaches to it.

Explicit item of this gate (the maintainer's waiver of Z3, with V15 and V16, in `REVIEW-plan-2026-10-14-pr320.md`): the plan's capture-based claims are checked against the committed fixtures: PATCH preservation, deployment classification by stages, the Bot Management fields, the ruleset calls.

## Rounds

| Round | Head | Scope | Seats | Time, tokens | Findings (BUG / RISK / NIT) |
|---|---|---|---|---|---|
| 1 | `7f16d98` | full, in parts A and B; fixtures read in the tree | Codex (gpt-6.1-sol, config effort) and Melious (glm-5.3) on each part; fresh-eyes (Claude Opus 5.5) on the whole | Codex A 467 s, 125,459 · Melious A 722 s, 63,937 · Codex B 435 s, 126,290 · Melious B 742 s, 71,186 · fresh-eyes 455 s, 229,816 | 8 / 9 / 10 after merging duplicates. UNVERIFIABLE asked: 7, confirmed as findings: 2 (R1-13, R1-14) |

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

The waiver's review item, round 1: all three seats with file access read the fixtures. PATCH preservation VERIFIED for names, plain values, build settings, branch and Fail open (values of secrets: R1-13); deployment classification VERIFIED (the excerpt's label: R1-10); Bot Management VERIFIED for the fields, the 10400 pair and fields left out (leaving out `is_robots_txt_managed`: R1-14); ruleset calls VERIFIED (the setup stage makes none). Fixtures free of real values: VERIFIED by Codex A, Codex B and fresh-eyes.

Decisions by the maintainer, 2026-10-15, asked after round 1 with the recommendation and the case against each. R1-01: "Bind the list (Recommended)". R1-13 and R1-14: "Waive both (Recommended)", to be observed on the first real site (plan step 10).
