# PLAN review — karero/croftweaver#265 — Cloudflare setup by one token, on a site connected to GitHub
Base `714516a` · depth: High (the script this plan describes changes a Cloudflare account with a token and can make a site public; the maintainer confirmed the depth, 2026-10-12) · verdict: OPEN · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY, each by atom A (this session opened the pull request and created the worktree and the branch)

Artifact: `docs/reviews/SKILL-PLAN-cloudflare-setup.md`. Raw reviewer output is in the pull request's review comment.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `50723f3` | full | Codex CLI 0.162.1, gpt-6.1-sol, high (config), read-only · Melious HTTP API, glm-5.3, text only · fresh-eyes sub-agent, claude-opus-5-5, read-only | Codex 296 s, 110,342 · Melious 130 s, 23,033 · fresh-eyes 652 s, 252,372 | 3 / 18 / 11 after merging duplicates (Codex 2/5/0, Melious 0/3/5, fresh-eyes 2/15/12). Unverifiable entries: 20 asked, 2 led to a change (F27, F28); the others are questions for the spike |
| 2 | `2ae354c` | full, as a verification round (prior findings F1 to F32) | the same three seats, same versions and effort | Codex 419 s, 142,885 · Melious 358 s, 37,983 · fresh-eyes 742 s, 260,498 | 1 / 14 / 11 after merging duplicates (Codex 0/6/0, Melious 0/5/4, fresh-eyes 1/7/9), and three outside scope (U1 to U3). All 32 round-1 fixes confirmed by all three seats, five of them as partial; those five are G4, G9/G12, G15, G1/G11 and G20 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex, fresh-eyes | 1 | The domain gate let unfinished legal pages through (`UNFILLED_UNTIL_LAUNCH` targets only warn) | fixed, locally_verified, externally_reverified (round 2) | script step 6 "Before it asks"; scenarios 9 and 12; `tests/placeholders.spec.ts:107` read |
| F2 | BUG | Codex (fresh-eyes, Melious as NIT) | 1 | The report called `main` the preview on every site and built the address by joining strings | fixed, locally_verified, externally_reverified (round 2) | script step 9 "The report"; scenarios 25, 26 |
| F3 | BUG | fresh-eyes (Melious as NIT) | 1 | "Two of its changes can alter what the public sees" was false | fixed, locally_verified, externally_reverified (round 2) | "What a visitor can notice"; script step 2; scenario 27 |
| F4 | RISK | fresh-eyes | 1 | How a yes reaches a script run without a terminal was undefined | fixed, locally_verified, externally_reverified (round 2) | "How a yes reaches it"; Decisions taken 6 |
| F5 | RISK | fresh-eyes | 1 | `PROD_BRANCH` alone does not show the publish model | fixed, locally_verified, externally_reverified (round 2) | script step 1; scenario 4; `templates/astro/src/config.ts:67` read |
| F6 | RISK | fresh-eyes | 1 | No rule for which project is adopted; Direct Upload and foreign projects uncovered | fixed, locally_verified, externally_reverified (round 2) | script step 1; scenarios 5, 6 |
| F7 | RISK | Melious, fresh-eyes | 1 | Nothing made the first production build | fixed, locally_verified, externally_reverified (round 2) | script step 4; Not verified 2 |
| F8 | RISK | Codex, fresh-eyes | 1 | A deployment of "the live commit" is not neutral; the branch can move; source of "head" unstated | fixed, locally_verified, externally_reverified (round 2) | script step 9; "What it reads from git"; scenario 16; Not verified 7 |
| F9 | RISK | Codex, fresh-eyes | 1 | Whether changing one variable keeps the others was unverified and outside the spike | fixed, locally_verified, externally_reverified (round 2) | Not verified 6; script step 9; scenario 15 |
| F10 | RISK | fresh-eyes | 1 | The domain step had one tested ending | fixed, locally_verified, externally_reverified (round 2) | script step 6; scenarios 13, 14 |
| F11 | RISK | fresh-eyes | 1 | TXT and CNAME treated alike | fixed, locally_verified, externally_reverified (round 2) | script step 8; scenarios 18, 19 |
| F12 | RISK | Codex, fresh-eyes (Melious as NIT) | 1 | The connection proof accepted an old deployment; rerun, previews off and no pull request undefined | fixed, locally_verified, externally_reverified (round 2) | script step 5; scenarios 7, 8, 28; D7 |
| F13 | RISK | fresh-eyes | 1 | Later steps undefined without an active domain; the check script would run too early | fixed, locally_verified, externally_reverified (round 2) | "Nothing reaches the domain early"; scenario 14 |
| F14 | RISK | fresh-eyes | 1 | No way to leave a line of the list out | fixed, locally_verified, externally_reverified (round 2) | "Leaving a line out"; scenario 27 |
| F15 | RISK | fresh-eyes | 1 | The swap test could not fire on a code that is a valid host label | fixed, locally_verified, externally_reverified (round 2) | scenario 17; Not verified 8 |
| F16 | RISK | fresh-eyes | 1 | An unrestricted test override could send the token to any host | fixed, locally_verified, externally_reverified (round 2) | "Where it sends requests" |
| F17 | RISK | Codex, fresh-eyes | 1 | The draft token is site-specific | fixed, locally_verified, externally_reverified (round 2) | script step 6; scenario 11; `website-team-setup/SKILL.md:381` read |
| F18 | RISK | fresh-eyes | 1 | "One check, not two" contradicted by the script's own checks | fixed, locally_verified, externally_reverified (round 2) | Decisions taken 5 |
| F19 | RISK | Codex | 1 | Stub expectations would rest on API contracts nobody exercised | fixed, locally_verified, externally_reverified (round 2) | Not verified, first paragraph; status row 4 |
| F20 | RISK | Melious | 1 | How heads and commits are read with only a Cloudflare token was unstated | fixed, locally_verified, externally_reverified (round 2) | "What it reads from git" |
| F21 | RISK | Melious (fresh-eyes as NIT) | 1 | A read probe does not prove write permission; a refused DNS write had no path | fixed, locally_verified, externally_reverified (round 2) | script step 1; scenarios 20, 21 |
| F22 | NIT | Melious | 1 | The CANONICAL_URL step did not wait for its deployment | fixed, locally_verified, externally_reverified (round 2) | script step 9 |
| F23 | NIT | Melious, fresh-eyes | 1 | The DNS lookup named no resolver and no waiting time | fixed, locally_verified, externally_reverified (round 2) | script step 8 |
| F24 | NIT | fresh-eyes | 1 | Decisions taken 2 did not say what the new test compares | fixed, locally_verified, externally_reverified (round 2) | Decisions taken 2 |
| F25 | NIT | fresh-eyes | 1 | Two series both called "step N" | fixed, locally_verified, externally_reverified (round 2) | "plan step" and "script step" throughout |
| F26 | NIT | fresh-eyes | 1 | The hook list left out files the script will contradict | fixed, locally_verified, externally_reverified (round 2) | section "Hooks" |
| F27 | NIT | fresh-eyes | 1 | The trail file the plan cites did not exist | fixed, locally_verified, externally_reverified (round 2) | this file |
| F28 | NIT | fresh-eyes | 1 | Scenario mixed "tracked" with "not ignored" | fixed, locally_verified, externally_reverified (round 2) | scenario 23; `git check-ignore -q` on a tracked and listed file exits 1 |
| F29 | NIT | fresh-eyes | 1 | The check script's JSON states are `hand` and `skip` | fixed, locally_verified, externally_reverified (round 2) | script step 9 |
| F30 | NIT | fresh-eyes | 1 | D2's entry recorded no change | fixed, locally_verified, externally_reverified (round 2) | D2 |
| F31 | NIT | fresh-eyes | 1 | GETTING-STARTED recommends two-factor sign-in, does not require it | fixed, locally_verified, externally_reverified (round 2) | "What the owner does" |
| F32 | NIT | fresh-eyes | 1 | The status header named a main commit that had moved | fixed, locally_verified, externally_reverified (round 2) | status header; merge `52f1edc` |
| G1 | BUG | fresh-eyes | 2 | The test override was called loopback-only "as the check script does"; that rule also takes `.test` and `.localhost` names | fixed, locally_verified | "Where it sends requests"; `cloudflare-check.mjs:23` read |
| G2 | RISK | Codex, fresh-eyes | 2 | Nothing carried a yes, or the connection proof, from one run to the next | fixed, locally_verified | three stages; "How a yes reaches it"; scenarios 2, 17 |
| G3 | RISK | Codex | 2 | An uploaded live build is not what a rebuild of its commit gives | fixed, locally_verified | script steps 6, 7; scenarios 16, 22 |
| G4 | RISK | Codex, fresh-eyes | 2 | Writes to an adopted project had no guard for its variables and secrets (F9 in part) | fixed, locally_verified | script step 3; Not verified 5, 6; scenario 8 |
| G5 | RISK | Codex | 2 | No rule for two projects naming the repository; `--project` consulted too late | fixed, locally_verified | script step 1; scenario 7 |
| G6 | RISK | Codex | 2 | The connection proof had lost "last stage succeeded" | fixed, locally_verified | script step 5; scenario 10. caused-by: F12 (regression in the rewrite) |
| G7 | RISK | Codex | 2 | The no-pull-request fallback assumed GitHub opens one for an empty commit | fixed, locally_verified | Not verified 7; D7 |
| G8 | RISK | Melious | 2 | With the domain already attached, nothing checked readiness before a branch change | fixed, locally_verified | case cut: scenario 4; Decisions taken 7 |
| G9 | RISK | Melious, fresh-eyes | 2 | No step wrote the domain's own DNS record, and the never-change rules forbade it (F10 in part) | fixed, locally_verified | script step 6; "What it never does"; scenario 18 |
| G10 | RISK | Melious | 2 | Which check-script item tells the served commit was unstated | fixed, locally_verified | "What every stage ends with"; `CLOUDFLARE_CHECK.md` `--build` row read |
| G11 | RISK | Melious, fresh-eyes | 2 | Nameserver lookups and `git ls-remote` were outside the declared destinations and the test override (F16, F23 in part) | fixed, locally_verified | "Where it sends requests"; scenario 32 |
| G12 | RISK | Melious, fresh-eyes | 2 | The domain question needs a DNS read the token rows did not give | fixed, locally_verified | "What the owner does" 1; scenario 18; Hooks |
| G13 | RISK | fresh-eyes (Melious as NIT) | 2 | Waits an assistant's shell cannot serve; no wait had a value | fixed, locally_verified | "It does not wait long"; script step 5 |
| G14 | RISK | fresh-eyes | 2 | Bot Fight Mode and the AI policies were not marked as zone-wide | fixed, locally_verified | script step 8; scenario 25 |
| G15 | RISK | fresh-eyes | 2 | `--skip` could not leave out the NEL rule or the forwarding (F14 in part) | fixed, locally_verified | ids `nel-rule`, `canonical`; scenarios 23, 26 |
| G16 | NIT | Melious, fresh-eyes | 2 | D5's line was in neither the report nor its scenario | fixed, locally_verified | "The report"; scenario 36 |
| G17 | NIT | Melious | 2 | The push the script asks for was not in the list | fixed, locally_verified | script step 2 |
| G18 | NIT | Melious | 2 | Scenario 1's "nothing answers on her domain" had no test | fixed, locally_verified | scenario 1 |
| G19 | NIT | fresh-eyes | 2 | `fail` unmapped; `tls` and `ai` can never be `ok` | fixed, locally_verified | "What every stage ends with"; `cloudflare-check.mjs:59` read |
| G20 | NIT | fresh-eyes | 2 | Hooks lacked the check script's `<name>.pages.dev` places; guardrail 2 softened (F26 in part) | fixed, locally_verified | Hooks; scenario 33 |
| G21 | NIT | fresh-eyes | 2 | A failed build of the head was never retried | fixed, locally_verified | script step 4 |
| G22 | NIT | fresh-eyes | 2 | The preview address's field was unnamed | fixed, locally_verified | "The report" |
| G23 | NIT | fresh-eyes | 2 | The draft token lives in two places in a site | fixed, locally_verified | script step 6; scenarios 14, 15 |
| G24 | NIT | fresh-eyes | 2 | A refusal sends the owner to `npm run ship`, whose last check cannot pass yet | fixed, locally_verified | script step 6; `templates/astro/scripts/ship.sh:288-308` read |
| G25 | NIT | fresh-eyes | 2 | No waiting time before the NEL rule | fixed, locally_verified | script step 8 |
| G26 | NIT | fresh-eyes | 2 | Captured answers carry more names than the token and ids | fixed, locally_verified | paragraph under the scenario table |

Waivers and deferrals: none. Owner decision between rounds 2 and 3 (maintainer, 2026-10-13, asked how many times the script should ask): "Three, one per stage". It changes D1.

Follow-ups: U1 (RISK, Codex, round 2) the check script's `canonical` comparison ignores the query string; taken into the check-script work of plan step 5. U2 (NIT, fresh-eyes, round 2) `CLOUDFLARE_CHECK.md` says any other `http://` address is refused, while the code also accepts `.test` and `.localhost` names. U3 (NIT, fresh-eyes, round 2) D5's dashboard path is in no kit file; D5 now says so.

Notes: the plan was rewritten once before round 1, to bring it in line with the checklist (#266) and the check script (#267) merged after it was written, and to move the script into the kit (D2, D3). The secrets check on the artifact found nothing. The repository is public and its plans have gone to Codex and to Melious before.
