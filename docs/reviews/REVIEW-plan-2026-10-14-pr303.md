# PLAN review — karero/croftweaver#303 — Cloudflare setup plan, second version, from the trial
Base `de64ec8` · depth: High (the script this plan describes changes a Cloudflare account with a token and can make a site public; the maintainer chose High for this plan) · verdict: OPEN, round 1 under way · authority used: POST AUTHORITY, WORKTREE-WRITE AUTHORITY and BRANCH-COMMIT AUTHORITY, each by atom A (this session opened the pull request and created the worktree and the branch)

Artifact: `docs/reviews/SKILL-PLAN-cloudflare-setup.md`, second version. A new artifact with a new round count; the first version's gate is `docs/reviews/REVIEW-plan-2026-10-12-pr265.md`. Raw reviewer output is in the pull request's review comment. Each round sends the reviewers the plan and the table "The first gate's open findings" below, so the dispositions in it are reviewed too.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|

## The first gate's open findings

How the second version deals with each finding round 3 of the first gate left open. "Moot" means the rewrite removed the mechanism the finding was about. Every row is the author's claim until a round confirms it.

| id | Sev | Finding (first gate, round 3) | In the second version | Where |
|---|---|---|---|---|
| H1 | BUG | Script step 4 starts a production build on a project that already serves a domain | fixed: a project that serves a domain gets no build and no branch change from `setup` | script step 4; scenario 5 |
| H2 | BUG | The forwarding step on a finished setup ends with 1 on a healthy site | fixed: `CANONICAL_URL` saved and `canonical` `ok` means nothing to do; "A finished setup" defines the end state | script step 13; scenario 32 |
| H3 | BUG | D1's reason (settings only once the domain serves the site) is false | fixed: two yeses, the settings with the first (D1, final); the checklist's "Two items wait" is the reason given | D1; script step 5; "Judgment calls", settings on setup day |
| H4 | BUG (wording) | "ends with an error after four minutes" is not ship.sh's deadline | fixed: no time is stated; the refusal quotes what ship itself says for a site with no domain yet (`templates/astro/scripts/ship.sh:306-307`) | scenario 21 |
| H5 | RISK | What enters a stage's code is not listed; a yes is either unbound or stops fitting after the script's own first write | fixed: the inputs are listed per stage, from the end state only, so the script's own writes do not change the code; the cost of not binding current values is named as a judgment | "A yes is a second run with a code"; "Judgment calls" |
| H6 | RISK | A missing or malformed build marker gets `look` and still reaches the `CANONICAL_URL` write | fixed: the check's `build` item must be `ok`; anything else ends with 1 before the forwarding | script step 11; scenario 26 |
| H7 | RISK | A rerun after status 4 can start a second deployment | fixed: before every deployment call the script reads the deployments and starts none while one of the production branch is queued or building (the trial showed a second call starts a second build, captures 030 to 040) | "Before every deployment call"; scenario 3 |
| H8 | RISK | Script step 5 demands a push whenever there is no fresh proof, the "finished setup" paragraph the opposite | moot: the proof is any push build of the project, of any age, so a finished setup has it; freshness is gone, and its cost is named as a judgment | script step 7; "A finished setup"; "Judgment calls" |
| H9 | RISK | A production deployment matched by commit only passes one built while `main` was the production branch | fixed: the deployment must record `production_branch` as `PROD_BRANCH` (capture 055 shows a deployment records it) | script step 8; scenario 21 |
| H10 | RISK | The record is repointed before the domain is attached; no downtime named; no way back | fixed: attach first, then the record in the same run (the trial: attaching leaves an existing record alone, captures 130, 131); the question names a few minutes of errors; the old record is printed before it changes | script steps 9, 10; scenario 25 |
| H11 | RISK | The guard compares names, so it cannot see a secret whose value was blanked | moot: the script never sends a variable it does not change; a PATCH of one field kept every other variable and secret in the trial (captures 048 to 062) | script step 3 |
| H12 | RISK | One short-lived token cannot serve stages days apart without breaking guardrail 2 | fixed: one token if launch day falls inside its life, otherwise a second token with the same rows | "What the owner does", 1 |
| H13 | NIT | "Does not appear" ends with 1 where a not-yet-visible deployment should be 4 | moot: the script follows the deployment by the id its call returned (capture 030 returns one) | "Before every deployment call" |
| H14 | NIT | G19's point about `tls` and `ai` appears nowhere | refuted in the first gate; the second version names both as "read back through the API only" | the report paragraph after script step 13 |
| H15 | NIT | Nothing records that the check script has `--json` | refuted in the first gate (`CLOUDFLARE_CHECK.md`, option table) | — |
| H16 | NIT | "adds the checklist's ssllabs test" reads as if the script ran it | fixed: "with the checklist's ssllabs test named for Lena to run" | the report paragraph |
| H17 | NIT | How the dictated DNS records reach the script is not named | fixed: `--record "<type> <name> <content>"` | script step 6 |
| H18 | NIT | Exit status for `look` and a blocked `skip`; what `--skip nel` or a refused switch does to the NEL rule | fixed: `look`, `hand`, `skip` give 0, a `blocked` item gives 1; the switch (`nel`, setup) and the rule (`nel-rule`, launch) are separate lines, and the rule depends only on what the check sees | the report paragraph; script steps 5, 12 |
| H19 | NIT | Whether the launch conditions gate a forwarding-only question on a domain attached by hand | fixed: a domain already attached and active skips them; one attached but not active does not | script step 8, last paragraph; scenario 31 |
| H20 | NIT | `--project` naming no existing project is undefined | fixed: the list says one of that name will be created | "Which project"; scenario 8 |
| H21 | NIT | "Opened once" for the preview address has no way through the check script | fixed: the address is read from Cloudflare's `aliases`, not opened | the report paragraph |
| H22 | NIT | The replacement list for captured answers lacks the account's name, emails and IP addresses | fixed: added, with the numeric GitHub ids the trial's captures hold and the record and deployment ids | "Tests" |
| H23 | NIT | Hooks lack `templates/PUBLISHING.md:111` and `templates/AGENTS.md:143` | fixed: both named | "Hooks" |
| H24 | NIT | Child processes inherit the token from the environment | fixed: removed from the environment of every program the script starts | "The token"; scenario 38 |
| H25 | NIT | A local-path fixture `origin` carries no GitHub owner and repository | fixed: a GitHub-form address sent to a local folder by git's `insteadOf` (marked not tried) | "Tests"; "Not verified", 7 |
| H26 | NIT | `PROD_BRANCH` and `SITE.url` read from the working tree, not from the commit that is built | fixed: every file of the site is read at a commit | "What it reads from git" |

The first gate's follow-ups: U1 (the `canonical` comparison ignores the query) is in decision 4's work for the check script. U5 (a host with one A and one AAAA record is refused) stands: changing it would mean deleting a record, which the script never does; scenario 24 names the case. U2, U3, U4 and U6 concern other files or the first trail and are not carried.

## This gate's findings

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|

Waivers and deferrals: none.

Follow-ups: none yet.

Notes:
- Written once from the trial's 159 captures (kept outside every repository; cited by number). A sweep of absence and universal claims (`sweep_claims.sh --file`) ran before round 1; the claims about Cloudflare carry capture numbers or are marked not verified. `bash scripts/check_clean.sh` passed.
