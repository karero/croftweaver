# PLAN review — karero/croftweaver#265 — Cloudflare setup by one token, on a site connected to GitHub
Base `714516a` · depth: High (the script this plan describes changes a Cloudflare account with a token and can make a site public; the maintainer confirmed the depth, 2026-10-12) · verdict: OPEN · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY, each by atom A (this session opened the pull request and created the worktree and the branch)

Artifact: `docs/reviews/SKILL-PLAN-cloudflare-setup.md`. Raw reviewer output is in the pull request's review comment.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `50723f3` | full | Codex CLI 0.162.1, gpt-6.1-sol, high (config), read-only · Melious HTTP API, glm-5.3, text only · fresh-eyes sub-agent, claude-opus-5-5, read-only | Codex 296 s, 110,342 · Melious 130 s, 23,033 · fresh-eyes 652 s, 252,372 | 3 / 18 / 11 after merging duplicates (Codex 2/5/0, Melious 0/3/5, fresh-eyes 2/15/12). Unverifiable entries: 20 asked, 2 led to a change (F27, F28); the others are questions for the spike |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex, fresh-eyes | 1 | The domain gate let unfinished legal pages through (`UNFILLED_UNTIL_LAUNCH` targets only warn) | fixed, locally_verified | script step 6 "Before it asks"; scenarios 9 and 12; `tests/placeholders.spec.ts:107` read |
| F2 | BUG | Codex (fresh-eyes, Melious as NIT) | 1 | The report called `main` the preview on every site and built the address by joining strings | fixed, locally_verified | script step 9 "The report"; scenarios 25, 26 |
| F3 | BUG | fresh-eyes (Melious as NIT) | 1 | "Two of its changes can alter what the public sees" was false | fixed, locally_verified | "What a visitor can notice"; script step 2; scenario 27 |
| F4 | RISK | fresh-eyes | 1 | How a yes reaches a script run without a terminal was undefined | fixed, locally_verified | "How a yes reaches it"; Decisions taken 6 |
| F5 | RISK | fresh-eyes | 1 | `PROD_BRANCH` alone does not show the publish model | fixed, locally_verified | script step 1; scenario 4; `templates/astro/src/config.ts:67` read |
| F6 | RISK | fresh-eyes | 1 | No rule for which project is adopted; Direct Upload and foreign projects uncovered | fixed, locally_verified | script step 1; scenarios 5, 6 |
| F7 | RISK | Melious, fresh-eyes | 1 | Nothing made the first production build | fixed, locally_verified | script step 4; Not verified 2 |
| F8 | RISK | Codex, fresh-eyes | 1 | A deployment of "the live commit" is not neutral; the branch can move; source of "head" unstated | fixed, locally_verified | script step 9; "What it reads from git"; scenario 16; Not verified 7 |
| F9 | RISK | Codex, fresh-eyes | 1 | Whether changing one variable keeps the others was unverified and outside the spike | fixed, locally_verified | Not verified 6; script step 9; scenario 15 |
| F10 | RISK | fresh-eyes | 1 | The domain step had one tested ending | fixed, locally_verified | script step 6; scenarios 13, 14 |
| F11 | RISK | fresh-eyes | 1 | TXT and CNAME treated alike | fixed, locally_verified | script step 8; scenarios 18, 19 |
| F12 | RISK | Codex, fresh-eyes (Melious as NIT) | 1 | The connection proof accepted an old deployment; rerun, previews off and no pull request undefined | fixed, locally_verified | script step 5; scenarios 7, 8, 28; D7 |
| F13 | RISK | fresh-eyes | 1 | Later steps undefined without an active domain; the check script would run too early | fixed, locally_verified | "Nothing reaches the domain early"; scenario 14 |
| F14 | RISK | fresh-eyes | 1 | No way to leave a line of the list out | fixed, locally_verified | "Leaving a line out"; scenario 27 |
| F15 | RISK | fresh-eyes | 1 | The swap test could not fire on a code that is a valid host label | fixed, locally_verified | scenario 17; Not verified 8 |
| F16 | RISK | fresh-eyes | 1 | An unrestricted test override could send the token to any host | fixed, locally_verified | "Where it sends requests" |
| F17 | RISK | Codex, fresh-eyes | 1 | The draft token is site-specific | fixed, locally_verified | script step 6; scenario 11; `website-team-setup/SKILL.md:381` read |
| F18 | RISK | fresh-eyes | 1 | "One check, not two" contradicted by the script's own checks | fixed, locally_verified | Decisions taken 5 |
| F19 | RISK | Codex | 1 | Stub expectations would rest on API contracts nobody exercised | fixed, locally_verified | Not verified, first paragraph; status row 4 |
| F20 | RISK | Melious | 1 | How heads and commits are read with only a Cloudflare token was unstated | fixed, locally_verified | "What it reads from git" |
| F21 | RISK | Melious (fresh-eyes as NIT) | 1 | A read probe does not prove write permission; a refused DNS write had no path | fixed, locally_verified | script step 1; scenarios 20, 21 |
| F22 | NIT | Melious | 1 | The CANONICAL_URL step did not wait for its deployment | fixed, locally_verified | script step 9 |
| F23 | NIT | Melious, fresh-eyes | 1 | The DNS lookup named no resolver and no waiting time | fixed, locally_verified | script step 8 |
| F24 | NIT | fresh-eyes | 1 | Decisions taken 2 did not say what the new test compares | fixed, locally_verified | Decisions taken 2 |
| F25 | NIT | fresh-eyes | 1 | Two series both called "step N" | fixed, locally_verified | "plan step" and "script step" throughout |
| F26 | NIT | fresh-eyes | 1 | The hook list left out files the script will contradict | fixed, locally_verified | section "Hooks" |
| F27 | NIT | fresh-eyes | 1 | The trail file the plan cites did not exist | fixed, locally_verified | this file |
| F28 | NIT | fresh-eyes | 1 | Scenario mixed "tracked" with "not ignored" | fixed, locally_verified | scenario 23; `git check-ignore -q` on a tracked and listed file exits 1 |
| F29 | NIT | fresh-eyes | 1 | The check script's JSON states are `hand` and `skip` | fixed, locally_verified | script step 9 |
| F30 | NIT | fresh-eyes | 1 | D2's entry recorded no change | fixed, locally_verified | D2 |
| F31 | NIT | fresh-eyes | 1 | GETTING-STARTED recommends two-factor sign-in, does not require it | fixed, locally_verified | "What the owner does" |
| F32 | NIT | fresh-eyes | 1 | The status header named a main commit that had moved | fixed, locally_verified | status header; merge `52f1edc` |

Waivers and deferrals: none.

Follow-ups: none yet.

Notes: the plan was rewritten once before round 1, to bring it in line with the checklist (#266) and the check script (#267) merged after it was written, and to move the script into the kit (D2, D3). The secrets check on the artifact found nothing. The repository is public and its plans have gone to Codex and to Melious before.
