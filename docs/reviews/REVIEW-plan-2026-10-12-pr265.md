# PLAN review — karero/croftweaver#265 — Cloudflare setup by one token, on a site connected to GitHub
Base `714516a` · depth: High (the script this plan describes changes a Cloudflare account with a token and can make a site public; the maintainer confirmed the depth, 2026-10-12) · verdict: OPEN. Stopped after round 3: not converging (see Notes); the next step is the maintainer's · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY, each by atom A (this session opened the pull request and created the worktree and the branch)

Artifact: `docs/reviews/SKILL-PLAN-cloudflare-setup.md`. Raw reviewer output is in the pull request's review comment.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `50723f3` | full | Codex CLI 0.162.1, gpt-6.1-sol, high (config), read-only · Melious HTTP API, glm-5.3, text only · fresh-eyes sub-agent, claude-opus-5-5, read-only | Codex 296 s, 110,342 · Melious 130 s, 23,033 · fresh-eyes 652 s, 252,372 | 3 / 18 / 11 after merging duplicates (Codex 2/5/0, Melious 0/3/5, fresh-eyes 2/15/12). Unverifiable entries: 20 asked, 2 led to a change (F27, F28); the others are questions for the spike |
| 2 | `2ae354c` | full, as a verification round (prior findings F1 to F32) | the same three seats, same versions and effort | Codex 419 s, 142,885 · Melious 358 s, 37,983 · fresh-eyes 742 s, 260,498 | 1 / 14 / 11 after merging duplicates (Codex 0/6/0, Melious 0/5/4, fresh-eyes 1/7/9), and three outside scope (U1 to U3). All 32 round-1 fixes confirmed by all three seats, five of them as partial; those five are G4, G9/G12, G15, G1/G11 and G20 |
| 3 | `286b02a` | full, as a verification round (prior findings G1 to G26) | the same three seats, same versions and effort | Codex 720 s, 135,786 · Melious 318 s, 49,124 · fresh-eyes 774 s, 265,622 | 4 / 8 / 14 after merging duplicates (Codex 2/3/0, Melious 1/2/7, fresh-eyes 1/6/10), and three outside scope (U4 to U6). All 26 round-2 fixes confirmed as landed; G2, G4, G8, G19 and G26 in part |

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
| G1 | BUG | fresh-eyes | 2 | The test override was called loopback-only "as the check script does"; that rule also takes `.test` and `.localhost` names | fixed, locally_verified, externally_reverified (round 3) | "Where it sends requests"; `cloudflare-check.mjs:23` read |
| G2 | RISK | Codex, fresh-eyes | 2 | Nothing carried a yes, or the connection proof, from one run to the next | fixed, locally_verified, externally_reverified (round 3) | three stages; "How a yes reaches it"; scenarios 2, 17 |
| G3 | RISK | Codex | 2 | An uploaded live build is not what a rebuild of its commit gives | fixed, locally_verified, externally_reverified (round 3) | script steps 6, 7; scenarios 16, 22 |
| G4 | RISK | Codex, fresh-eyes | 2 | Writes to an adopted project had no guard for its variables and secrets (F9 in part) | fixed, locally_verified, externally_reverified (round 3) | script step 3; Not verified 5, 6; scenario 8 |
| G5 | RISK | Codex | 2 | No rule for two projects naming the repository; `--project` consulted too late | fixed, locally_verified, externally_reverified (round 3) | script step 1; scenario 7 |
| G6 | RISK | Codex | 2 | The connection proof had lost "last stage succeeded" | fixed, locally_verified, externally_reverified (round 3) | script step 5; scenario 10. caused-by: F12 (regression in the rewrite) |
| G7 | RISK | Codex | 2 | The no-pull-request fallback assumed GitHub opens one for an empty commit | fixed, locally_verified, externally_reverified (round 3) | Not verified 7; D7 |
| G8 | RISK | Melious | 2 | With the domain already attached, nothing checked readiness before a branch change | fixed, locally_verified, externally_reverified (round 3) | case cut: scenario 4; Decisions taken 7 |
| G9 | RISK | Melious, fresh-eyes | 2 | No step wrote the domain's own DNS record, and the never-change rules forbade it (F10 in part) | fixed, locally_verified, externally_reverified (round 3) | script step 6; "What it never does"; scenario 18 |
| G10 | RISK | Melious | 2 | Which check-script item tells the served commit was unstated | fixed, locally_verified, externally_reverified (round 3) | "What every stage ends with"; `CLOUDFLARE_CHECK.md` `--build` row read |
| G11 | RISK | Melious, fresh-eyes | 2 | Nameserver lookups and `git ls-remote` were outside the declared destinations and the test override (F16, F23 in part) | fixed, locally_verified, externally_reverified (round 3) | "Where it sends requests"; scenario 32 |
| G12 | RISK | Melious, fresh-eyes | 2 | The domain question needs a DNS read the token rows did not give | fixed, locally_verified, externally_reverified (round 3) | "What the owner does" 1; scenario 18; Hooks |
| G13 | RISK | fresh-eyes (Melious as NIT) | 2 | Waits an assistant's shell cannot serve; no wait had a value | fixed, locally_verified, externally_reverified (round 3) | "It does not wait long"; script step 5 |
| G14 | RISK | fresh-eyes | 2 | Bot Fight Mode and the AI policies were not marked as zone-wide | fixed, locally_verified, externally_reverified (round 3) | script step 8; scenario 25 |
| G15 | RISK | fresh-eyes | 2 | `--skip` could not leave out the NEL rule or the forwarding (F14 in part) | fixed, locally_verified, externally_reverified (round 3) | ids `nel-rule`, `canonical`; scenarios 23, 26 |
| G16 | NIT | Melious, fresh-eyes | 2 | D5's line was in neither the report nor its scenario | fixed, locally_verified, externally_reverified (round 3) | "The report"; scenario 36 |
| G17 | NIT | Melious | 2 | The push the script asks for was not in the list | fixed, locally_verified, externally_reverified (round 3) | script step 2 |
| G18 | NIT | Melious | 2 | Scenario 1's "nothing answers on her domain" had no test | fixed, locally_verified, externally_reverified (round 3) | scenario 1 |
| G19 | NIT | fresh-eyes | 2 | `fail` unmapped; `tls` and `ai` can never be `ok` | fixed, locally_verified, externally_reverified (round 3) | "What every stage ends with"; `cloudflare-check.mjs:59` read |
| G20 | NIT | fresh-eyes | 2 | Hooks lacked the check script's `<name>.pages.dev` places; guardrail 2 softened (F26 in part) | fixed, locally_verified, externally_reverified (round 3) | Hooks; scenario 33 |
| G21 | NIT | fresh-eyes | 2 | A failed build of the head was never retried | fixed, locally_verified, externally_reverified (round 3) | script step 4 |
| G22 | NIT | fresh-eyes | 2 | The preview address's field was unnamed | fixed, locally_verified, externally_reverified (round 3) | "The report" |
| G23 | NIT | fresh-eyes | 2 | The draft token lives in two places in a site | fixed, locally_verified, externally_reverified (round 3) | script step 6; scenarios 14, 15 |
| G24 | NIT | fresh-eyes | 2 | A refusal sends the owner to `npm run ship`, whose last check cannot pass yet | fixed, locally_verified, externally_reverified (round 3) | script step 6; `templates/astro/scripts/ship.sh:288-308` read |
| G25 | NIT | fresh-eyes | 2 | No waiting time before the NEL rule | fixed, locally_verified, externally_reverified (round 3) | script step 8 |
| G26 | NIT | fresh-eyes | 2 | Captured answers carry more names than the token and ids | fixed, locally_verified, externally_reverified (round 3) | paragraph under the scenario table |
| H1 | BUG | Codex (fresh-eyes as RISK) | 3 | Script step 4 starts a production build on a project that already serves a domain: the guard "if no domain is attached" was dropped in the rewrite, and the list still says "not on your domain" | open | `2ae354c` had the guard, `286b02a` has not. caused-by: G21 and G8 (regression of F7's fix) |
| H2 | BUG | Melious | 3 | Script step 7 on a finished setup falls into "otherwise" and ends with status 1 on a healthy site | open | script step 7 has no branch for "already in effect" |
| H3 | BUG | fresh-eyes | 3 | D1's reason, "the settings can only be applied once the domain serves the site", is false: the checklist makes only HSTS and the forwarding wait (`docs/CLOUDFLARE-CHECKLIST.md:6-8`, `:290-293`). In the three-stage order the site is public with Cloudflare's defaults until the settings stage runs | open | checked: the checklist says "Two items wait". The maintainer's change of D1 on 2026-10-13 was asked for with this false reason; it goes back to the maintainer |
| H4 | BUG | Codex (Melious as NIT) | 3 | "ends with an error after four minutes" is not ship.sh's deadline: 24 tries, ten seconds apart, plus each request's time | open; wording, not counted as substantive | `templates/astro/scripts/ship.sh:288-298` |
| H5 | RISK | Codex, fresh-eyes (Melious as NIT) | 3 | What enters a stage's code is not listed; the script keeps nothing between runs, so a yes is either not bound to what the question showed or stops fitting after the script's own first write or when the proof ages (G2 in part) | open | — |
| H6 | RISK | Codex | 3 | A domain whose build marker is missing or malformed gets `look` from the check script and still reaches the `CANONICAL_URL` write | open | `cloudflare-check.mjs:749-760` |
| H7 | RISK | Codex, Melious | 3 | A rerun after status 4 can start a second deployment: no rule reads a pending one | open | — |
| H8 | RISK | Melious (fresh-eyes as NIT) | 3 | Script step 5 demands a push whenever there is no fresh proof, the "finished setup" paragraph the opposite; "finished" and that run's exit status are undefined | open | — |
| H9 | RISK | fresh-eyes | 3 | A production deployment is matched by commit only; one built while `main` was the production branch passes, with analytics off | open | `templates/astro/src/config.ts:70` |
| H10 | RISK | fresh-eyes | 3 | The host's record is repointed before the domain is attached; the question names no downtime, and a failure leaves the host pointing at nothing with no line saying how to put it back | open | caused-by: G9 (introduced) |
| H11 | RISK | fresh-eyes | 3 | The guard compares variable names, so it cannot see a secret whose value was blanked; the spike question names no way to observe it (G4 in part) | open | — |
| H12 | RISK | fresh-eyes | 3 | One short-lived token cannot serve stages that run days apart without breaking guardrail 2 | open | `docs/CLOUDFLARE-CHECKLIST.md:310-311` |
| H13 | NIT | Melious | 3 | "Does not appear" ends with status 1 where a not-yet-visible deployment should be status 4 | open | — |
| H14 | NIT | Melious | 3 | G19's point about `tls` and `ai` "appears nowhere" | refuted | it is in "What every stage ends with", the report's list: "Minimum TLS Version, where it adds the checklist's ssllabs test, and the AI crawler policies" |
| H15 | NIT | Melious | 3 | Nothing records that the check script has `--json` | refuted | `skills/new-website/references/CLOUDFLARE_CHECK.md`, option table: "`--json`: Print the results as JSON" |
| H16 | NIT | Melious | 3 | "adds the checklist's ssllabs test" reads as if the script ran it | open | — |
| H17 | NIT | Melious | 3 | How the dictated DNS records reach the script is not named | open | — |
| H18 | NIT | fresh-eyes | 3 | Exit status for `look` and a blocked `skip`; what `--skip nel` or a refused switch do to the NEL rule (G19, G25 in part) | open | — |
| H19 | NIT | fresh-eyes | 3 | Whether the six conditions gate a forwarding-only question on a domain attached by hand | open | — |
| H20 | NIT | fresh-eyes | 3 | `--project` naming no existing project is undefined | open | — |
| H21 | NIT | fresh-eyes | 3 | "Opened once" for the preview address has no way through the check script | open | `cloudflare-check.mjs:156` |
| H22 | NIT | fresh-eyes | 3 | The replacement list for captured answers lacks the account's name, email fields and IP addresses (G26 in part) | open | — |
| H23 | NIT | fresh-eyes | 3 | Hooks lacks `templates/PUBLISHING.md:111` and `templates/AGENTS.md:143` | open | — |
| H24 | NIT | fresh-eyes | 3 | Child processes inherit the token from the environment | open | — |
| H25 | NIT | fresh-eyes | 3 | A local-path fixture origin carries no GitHub owner and repository | open | — |
| H26 | NIT | fresh-eyes | 3 | `PROD_BRANCH` and `SITE.url` are read from the working tree, not from the commit that is built | open | — |

Waivers and deferrals: none. Owner decision between rounds 2 and 3 (maintainer, 2026-10-13, asked how many times the script should ask): "Three, one per stage". It changes D1.

Follow-ups: U1 (RISK, Codex, round 2) the check script's `canonical` comparison ignores the query string; taken into the check-script work of plan step 5. U2 (NIT, fresh-eyes, round 2) `CLOUDFLARE_CHECK.md` says any other `http://` address is refused, while the code also accepts `.test` and `.localhost` names. U3 (NIT, fresh-eyes, round 2) D5's dashboard path is in no kit file; D5 now says so. U4 (NIT, fresh-eyes, round 3) the status header names `714516a` and `origin/main` has moved on; the commits between touch none of the files the plan leans on. U5 (NIT, fresh-eyes, round 3) a host with one A and one AAAA record, a common pair, is refused as "more than one address record". U6 (fresh-eyes, round 3) a slip in the round-2 record: it said "five in part" and listed six ids.

Notes:
- **Stopped: not converging.** Findings per round after merging duplicates: 3/18/11, 1/14/11, 4/8/14. Each round's findings land mostly on text the round before added. Twice a rewrite between rounds dropped something an earlier text had (G6 in round 2; H1 in round 3, which undoes part of F7's fix). The skill's rule for that is to stop patching and redesign, or take the open items to the owner. Round 3's findings are therefore recorded here and are NOT worked into the plan.
- Round 4 would have been earned by round 3's substantive BUGs (H1, H2, H3); it was not run, for the reason above.
- The author's reading of the cause: the plan fixes a multi-run mechanism in detail while eight questions about Cloudflare's behaviour are still open, and the spike (plan step 4) will rewrite parts of it anyway.
- No final full read and no wording pass were run: the gate did not reach them.
- Cost of the three rounds: Codex 1,435 s and 389,013 tokens; Melious 806 s and 110,140; fresh-eyes 2,168 s and 778,492.
- The plan was rewritten once before round 1, to bring it in line with the checklist (#266) and the check script (#267) merged after it was written, and to move the script into the kit (D2, D3). The secrets check on the artifact found nothing. The repository is public and its plans have gone to Codex and to Melious before.
