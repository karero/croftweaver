# Plan: Cloudflare setup by one token, for a site connected to GitHub

Requirements record for a script that does not exist yet. Where this plan and the shipped
files disagree, the files win. Names of sites and people stay out of this public repo on
purpose; the business in the scenarios is made up.

## Status, 2026-10-12 · read against origin/main 4257b23

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | Requirements and scenarios (this file) | ▶ written, and brought in line with the checklist and the check script as merged; the PLAN gate (High) is running | this file; trail: `docs/reviews/REVIEW-plan-2026-10-12-pr265.md` |
| 2 | The Cloudflare checklist reaches `main` (`docs/CLOUDFLARE-CHECKLIST.md`; another session's work) | ✅ merged 2026-10-12. The script that runs its outside checks followed the same day | karero/croftweaver#266 (`7642954`); the check script: karero/croftweaver#267 (`d382cbe`) |
| 3 | The maintainer closes the decisions D1 to D7 below | ✅ all seven decided as recommended (maintainer, 2026-10-12: "all as recommended"). D2 and D3 changed the same day, after step 2: the script lives in the kit (maintainer, 2026-10-12: "In the kit") | section "Decisions D1 to D7" |
| 4 | Spike on a throwaway repository and project: the five things marked "not verified" under "What is known" | ⏸ not started | — |
| 5 | The script and its tests against a stub of Cloudflare's API | ⏸ not started | — |
| 6 | Hooks: `CLOUDFLARE_FIRST_DEPLOY.md` (option B, and guardrail 4), `website-team-setup` §6, the checklist's section 6, `CLOUDFLARE_CHECK.md` ("By hand, always") | ⏸ not started | — |
| 7 | Review gate on the script (High: it changes an account with a token, and it can make a site public) | ⏸ not started | — |
| 8 | One real site set up with it, start to finish, with the owner watching | ⏸ not started | — |
| 9 | Release note line | ⏸ not started | — |

Legend: ✅ done · ▶ in progress · ⏸ not started or blocked · ⚠ deviated

## Why

Putting a new site on Cloudflare is the step where an owner who has never seen the
dashboard loses the most time, and where a wrong click has the biggest effect. The kit has
three routes today (`skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md`):

- **A, by token:** the assistant creates the project and deploys with Wrangler, but the
  site is a Direct Upload project.
  Cloudflare does not build it from GitHub, so `PUBLISHING.md`'s push-to-deploy does not
  apply to it.
- **B, connected to GitHub:** a push builds, but the owner clicks through the dashboard
  alone, with `website-team-setup` §6 warning about the traps.
- **C, the assistant drives the browser.** Slow, and not every assistant can.

The maintainer's decision (2026-10-12): the setup should be done for the owner as far as a
token allows, on the model of route B. This plan is that: route B's result, with as much of
route A's effort as Cloudflare's API allows.

It is written after one site's launch on 2026-10-12, set up by hand on route B. Six things
went wrong that day. Each is a scenario below, so that the script does not repeat it:

1. The project was created with production branch `main` on a two-stage site. Cloudflare
   published `main` to the live domain at once, with unfilled slots on the legal pages, and
   the domain was open to search engines.
2. The project lost its connection to GitHub. Merges and pushes built nothing, and the
   one sign found that day was a banner in the dashboard.
3. "Create deployment" in the dashboard did nothing while the connection was broken.
4. A variable was typed into the dashboard and not saved; later it was saved, but no
   production build followed, so it had no effect until the next publish.
5. The owner took the project's own `pages.dev` address for the preview. It is the live
   build's second address; the preview is the same address with `main.` in front.
6. A DNS record for a search engine's verification was entered with name and target the
   wrong way round.

## Shape

### What the owner does

**Before the script, once.** Neither is this plan's work; the script only checks the second.

- Accounts at GitHub and Cloudflare, protected with two-factor sign-in
  (`docs/GETTING-STARTED.md`).
- The domain is on Cloudflare: bought there, or moved there with its records compared entry
  by entry ("Going live" in `CLOUDFLARE_FIRST_DEPLOY.md`). The script moves no domain.

**For the script,** none of it in a terminal:

1. Makes one short-lived token, from the permission rows the assistant shows: the rows of
   the checklist's section 6, and Zone → DNS → Edit if the script is to write DNS records.
2. Authorizes Cloudflare's GitHub app for the one repository, once, in the browser.
   (Whether the script can do everything after that, or the owner must also click
   "Connect to Git" once, is the first question of the spike in step 4.)
3. Says yes to the list the script prints, and gives a separate yes before the domain is
   attached.
4. Gives the verification records of Google and Bing, if the script is to write them. The
   codes live in the owner's accounts there (`search-console-setup`).

**Afterwards, by hand,** as `CLOUDFLARE_CHECK.md` ("By hand, always") lists: Crawler Hints
and the off switch for Cloudflare Web Analytics (the kit's notes say Cloudflare has no API
for them), HSTS a few days after go-live (the checklist's section 2 says why it goes on
last), and deleting the token.

### What the script is

One Node file, `skills/new-website/scripts/cloudflare-setup.mjs`, beside
`cloudflare-check.mjs`. Node 18 or newer, nothing from npm, no Wrangler: it calls
Cloudflare's API with Node's own HTTP client. The assistant starts it in the site's folder.
It reads the token from the environment (`CLOUDFLARE_API_TOKEN`) or from `.dev.vars`, never
from an argument, and it reads `.dev.vars` only if git ignores that file.

### What the script does

1. **Looks first.** From the site's folder: the production branch (`PROD_BRANCH` in
   `src/config.ts`; `main` means single-stage, anything else two-stage), the domain
   (`SITE.url`), and the repository (the `origin` remote). From Cloudflare: that the token
   is active and when it ends, the zone of the domain, and the project if one exists. It
   stops here if `SITE.url` is still the starter's `example.com`, or if Cloudflare has no
   active zone for the domain. The
   call that tests a token does not say what the token may do, so the script learns that
   by reading: one read call for each area it will change (zone settings, Transform Rules,
   Bot Management, DNS records, Pages). An area it cannot read is a step it will skip.
2. **Says what it will do.** Prints every change it is about to make, in the owner's
   words: which change touches the whole domain and not only this site, which one makes
   the site public, and which steps it will skip and why. Nothing has changed yet. It goes
   on after one yes to this list.
3. **Sets up the project.** Creates it, or adopts the one the owner created: build command
   `npm run build`, output `dist`, production branch as `PROD_BRANCH` says, Fail open. From
   here on it takes the project's `pages.dev` address from the `subdomain` Cloudflare
   returns, never from the project's name: the two can differ.
4. **Proves the GitHub connection with a real build.** It pushes nothing itself. The
   assistant opens the first pull request, or names one that is open; the script reads
   that branch's head commit and waits until the project's list of deployments holds a
   preview deployment of that commit whose last stage succeeded. None within a set time is
   a named failure, with the repair steps.
5. **Attaches the domain, last of the project steps and only on a separate yes.** Before
   it asks, it reads `build.txt` on the project's `pages.dev` address, checks that it is
   the head of the production branch, and searches that commit's `src/` and `public/` for
   the kit's `[MISSING:` marker, the search the site's CI runs. (The template's own
   bracket slots on the rendered pages stay with the site's `tests/placeholders.spec.ts`;
   the script does not repeat that check.) The question names the domain and that commit. After the yes it attaches the domain, waits until Cloudflare
   reports it active, and only then sends the first request to the domain.
6. **Sets `CANONICAL_URL`, then makes it take effect.** The value is `https://` and the
   attached domain, taken from Cloudflare's answer and not typed by anyone; it opens
   `build.txt` on that address first. It reads the project's variables before and after,
   and stops if another variable is missing afterwards. Then it starts a production
   deployment, but only when the head of the production branch is the commit that is
   already live: a deployment of that commit publishes nothing new. If the head is newer,
   it says that the variable is saved and waits for the next `npm run ship`.
7. **Applies the settings of the Cloudflare checklist that an API can set:** Always Use
   HTTPS, Minimum TLS Version, Email Address Obfuscation, the NEL switch, Bot Fight Mode
   and the AI crawler policies, and the rule that removes the NEL headers only if they are
   still sent after the switch. Order, values and cautions are the checklist's, which
   stays the one place they live. It does not switch HSTS on. A setting the API refuses
   goes into the report as "by hand".
8. **Writes DNS records the owner dictates,** such as the verification records of Google
   and Bing. It shows type, name and target before writing. If a record of that type and
   name exists with another target, it shows both and asks; it never replaces one
   silently. A record that is not the website itself is written "DNS only", as "Going
   live" in `CLOUDFLARE_FIRST_DEPLOY.md` rules. It reads each record back through the API
   and with a lookup.
9. **Checks from outside, and reports.** It runs `cloudflare-check.mjs --json` with the
   project's `pages.dev` address and the commit it expects, and passes each line on as
   that script judged it: a `look` or a `by hand` is never reported as done. The report
   gives, for each setting, what it was, what it is now and how that was checked (read
   back through the API, seen from outside, or "no outside check exists"); each address
   and what it is (live, preview of `main`, preview of a pull request); what is left for
   the owner by hand, HSTS with the earliest day for it; and a reminder to delete the
   token.

**What it never does.** It never merges and never runs `npm run ship`; that stays with the
owner, or the assistant on the owner's word. Two of its changes can alter what the public
sees, and each has a yes of its own: attaching the domain (step 5), and changing the
production branch of a project that already serves a domain (scenario 3). The deployment
of step 6 is not a third: it builds the commit that is already live. It never deletes a
project, a variable or a DNS record, and never keeps or prints the token.

**A second run on a finished setup changes nothing.** Every step reads first and skips
what is already right, so the script can be run again after a failure or a year later.

## Scenarios

The owner is Lena. Her site is `lenas-backstube` on GitHub, two-stage, and her domain is
`lenas-backstube.example`, already on Cloudflare. Where a scenario does not say otherwise,
the project's `pages.dev` address is `lenas-backstube.pages.dev`.

| # | Given | When | Then | Test |
|---|-------|------|------|------|
| 1 | Lena has made the token and authorized the GitHub app | the script runs for the first time and she says yes to its list | the project `lenas-backstube` exists with production branch `production`, build command `npm run build`, output `dist`, Fail open on; nothing answers on her domain yet | stub API: the create call carries these values; a second run sends no create call |
| 2 | a project exists with production branch `main`, the site is two-stage, and no domain is attached | the script looks | its list holds the line "Your live address would publish `main`, the preview. I will set the production branch to `production`", and nothing is written before the yes to the list | stub API returns such a project; no write call before the yes; the first write is the branch change |
| 3 | the same project, but her domain is attached to it | the script looks | it leaves that change out of the list and asks about it alone: it says what her domain serves now, that this changes at the next production build, and that the `production` branch must exist first | stub API returns the project with a domain; the branch change is sent only after its own yes |
| 4 | the site is two-stage and the repository has no `production` branch | the script looks | it says so and asks the assistant to create the branch from the reviewed `main`; it does not create a project that would have nothing to build | fixture repository without the branch |
| 5 | the project exists but Cloudflare cannot reach the repository | the script waits for a preview deployment of the pull request's head commit | after the set time it reports "Cloudflare did not build this pull request. The connection to GitHub is broken or was never made", with the steps to repair it, and stops before the domain step | stub: the commit never appears in the list of deployments; exit status and message |
| 6 | the head of `production` holds a page with `[MISSING: opening hours]` in `src/` | Lena says "attach my domain" | the script refuses: it names the file and the marker, and attaches nothing | fixture repository with the marker; no domain call is sent |
| 7 | the live build is the head of `production` and holds no marker | Lena says yes to "attach `lenas-backstube.example`, serving commit …" | the domain is attached, the script waits until Cloudflare reports it active, checks `https://lenas-backstube.example/build.txt` with a cache-busting query, and only then says "live" | stub: status goes pending then active; no request to the domain before active; the "live" line comes after the `build.txt` check |
| 8 | the domain serves the site | the script sets `CANONICAL_URL` | the variable is there on a read-back, the project's other variables are unchanged, a production deployment was started, and `lenas-backstube.pages.dev/about` answers 301 to the same path on her domain | stub API with two existing variables; a local stub site for the 301 |
| 9 | the variable was set but the production deployment failed or did not start, or the head of `production` is newer than the live build | the script checks the 301 | it says "the variable is saved, but no build has picked it up", and what will pick it up; it does not say "done" | stub: no new deployment; and a head that differs from the live build, where no deployment call is sent |
| 10 | Lena gives the Bing record with name and target the wrong way round | the script shows what it will write | it notices that the name is the verifying service's host (`verify.bing.com`) and the target is not a host name, says the two look swapped, and asks before writing | unit test on the record check |
| 11 | a TXT or CNAME record of the same name exists with another target | the script is to write Lena's record | it shows the existing record and hers, and asks; without a yes it writes nothing and replaces nothing | stub API holding the other record |
| 12 | the token cannot read DNS records | the script looks | it lists which steps it can do and which it will skip, before changing anything | stub: the DNS read is refused |
| 13 | the token has no end date, or reaches more zones than hers | the script looks | it says so and asks for a narrower token; it goes on only if Lena insists | stub: no `expires_on`; a zone list with two zones |
| 14 | the token is in `.dev.vars` and git does not ignore that file | the script starts | it stops before reading the file and says how to ignore it | fixture repository that tracks `.dev.vars` |
| 15 | Cloudflare gave the project the address `lenas-backstube-9x2.pages.dev` | the script checks and reports | every check and every line of the report uses that address; `lenas-backstube.pages.dev` is requested nowhere | stub API whose `subdomain` differs from the name; the stub site records the hosts requested |
| 16 | the run is finished | the script reports | the report names `lenas-backstube.example` as live, `main.lenas-backstube.pages.dev` as the preview, says that `lenas-backstube.pages.dev` now forwards to the live address, and lists Crawler Hints, the Web Analytics switch and HSTS, with a date, as left for Lena | snapshot of the report |
| 17 | the script ran last month | it runs again | it makes no write call and reports every setting as already right | stub API holding the end state |

The tests run the script as a program against a stub of Cloudflare's API and small sites
on `127.0.0.1`, the way `make test-cloudflare-check` tests the check script, and are wired
into the same CI workflow (`.github/workflows/clean.yml`).

## What is known, and how

**Done on one live site, 2026-10-12** (a project connected to GitHub, two-stage):

- `wrangler pages deploy dist --project-name <project> --branch production` made a
  production deployment in a project that is connected to GitHub. It was the way out while
  the GitHub connection was broken. The script does not use it; it stays the emergency
  route in the kit's notes.
- `wrangler pages download config <project>` shows the project's saved plain-text
  variables per environment. It told a variable that was typed but not saved from one that
  was saved.
- A variable reached only deployments made after it was saved. After the next production
  build, the project's `pages.dev` address answered 301 with path and query kept, and
  previews kept answering 200 with `noindex`.
- With the connection repaired, Cloudflare built a pushed branch by itself and put its
  check on the commit; `npm run ship` then published and confirmed the build.
- Wrangler's browser sign-in had permission to write Pages projects but only to read
  zones, so it cannot stand in for the token where zone settings or DNS are changed.
- By the evening Wrangler listed the project under a name that is not the first part of
  its `pages.dev` address, and refused the old name. Who changed it is not recorded.

**Read in Cloudflare's API reference, 2026-10-12, not tried:**

- [Creating a project](https://developers.cloudflare.com/api/resources/pages/subresources/projects/methods/create/)
  takes `production_branch`, a `build_config` (build command, output directory),
  `deployment_configs` per environment with `env_vars` and `fail_open`, and a `source`
  object for GitHub (owner, repository name, production branch, which previews build).
  Permission: Pages Write.
- [A project](https://developers.cloudflare.com/api/resources/pages/subresources/projects/methods/get/)
  comes back with `subdomain` ("The Cloudflare subdomain associated with the project") and
  `domains`. A deployment carries the commit that caused it
  (`deployment_trigger.metadata.commit_hash`), its environment and its `latest_stage`.
- [Adding a domain](https://developers.cloudflare.com/api/resources/pages/subresources/projects/subresources/domains/methods/create/)
  is `POST …/pages/projects/{project}/domains` with the domain's name; its status is one
  of `initializing`, `pending`, `active`, `deactivated`, `blocked`, `error`. The page does
  not say whether a DNS record is created.
- [Creating a deployment](https://developers.cloudflare.com/api/resources/pages/subresources/projects/subresources/deployments/methods/create/)
  is "from a Git branch or Direct Upload manifest"; `branch` "defaults to the project's
  production branch", and "Git repositories must already be authorized in Cloudflare
  Pages".
- [Testing a token](https://developers.cloudflare.com/api/resources/user/subresources/tokens/methods/verify/)
  returns `status`, `expires_on` and `not_before`. It returns neither permissions nor the
  zones and accounts the token reaches.

**Not verified. Step 4, the spike, settles these before any code:**

1. Whether a project created through the API with a `source` object is connected to
   GitHub once the app is authorized for the repository, or whether "Connect to Git" in
   the dashboard is the only way. If it is the only way, the owner clicks once more and the
   script adopts the project (scenarios 2 and 3).
2. Whether attaching a domain creates its DNS record, or the script must write it.
3. Whether the deployment call above, sent without a branch to a connected project,
   builds the head of the production branch.
4. What the read calls of step 1 show about a token: whether a refused read names the
   missing permission, and whether listing zones shows that a token reaches more than one.
5. What a domain serves between a change of the production branch and the first build of
   the new branch (scenario 3).

If the spike answers 3 or 4 with no, the scenarios that rest on them (8 and 9; 12 and 13)
are rewritten before step 5, and this file says so.

The settings of step 7, their permission rows and their cautions are the checklist's, with
that file's own sources.

## Decisions taken

1. **The model is route B** (connected to GitHub), by the maintainer, 2026-10-12.
   Previews per pull request and `npm run ship` are worth one authorization in the browser.
2. **The checklist stays the list.** The script takes its settings, their order and their
   cautions from `docs/CLOUDFLARE-CHECKLIST.md`; this plan adds the project steps. A test
   compares the script's list with the checklist's, as `make test-cloudflare-check` does
   for the check script.
3. **The domain is the last project step and has its own yes,** because it is the step
   that makes a site public and open to search engines.
4. **Read, say, do, read back, and check from outside where an outside check exists.** A
   setting the check script can see counts as done when a request from outside shows it,
   not when the API says so: the checklist records a case where the API reported a header
   off and the site still sent it. Fail open and the build settings have no outside check
   (`CLOUDFLARE_CHECK.md`); for them the report says "read back through the API only".
5. **One check, not two.** The script calls `cloudflare-check.mjs` and does not carry
   checks of its own for what that script covers.

## Decisions D1 to D7

Closed by the maintainer on 2026-10-12. The argument against each stays here as the record
of what was weighed.

- **D1. One yes or many.** *Decided:* one yes for the whole list, a second for the
  domain, and one for a production-branch change on a project that already serves a domain
  (scenario 3). *Rests on:* "the owner should not have to do anything". *Against:*
  guardrail 4 in `CLOUDFLARE_FIRST_DEPLOY.md` asks for a yes before each change to the
  account; one yes is weaker, and the list must be read carefully to be worth it. Step 6
  rewrites that guardrail for the script: the printed list, confirmed once, is the
  confirmation for the changes it names, and for nothing else.
- **D2. What it is written in.** *Decided:* Node, as one file with nothing from npm, like
  the check script. *Against:* most of the kit's own scripts are bash or Python.
- **D3. Where it lives.** *Decided first:* in the site template. *Changed the same day:*
  in the kit, in the `new-website` skill beside the check script, run in the site's
  folder. The check script was merged there after the first decision; a script in the kit
  can call it, and is the installed kit's version instead of a copy that ages in each
  site. *Against:* a site whose owner has no kit installed cannot run it; such an owner
  follows route B by hand.
- **D4. Project steps only, or the checklist's settings too.** *Decided:* both, the
  project steps first and the settings as a second stage of the same script. *Against:*
  the settings touch the whole domain, not only this site, and two of them are judgment
  calls the checklist explains at length.
- **D5. Previews behind a login.** Cloudflare can ask for a sign-in before a preview opens
  (project → Settings → General → Enable access policy). *Decided:* leave it out of
  the first version and name it in the report as an option. *Against:* previews are public
  to anyone who has the address, and an owner asked for hidden ones on the first day.
- **D6. Creating the `production` branch.** *Decided:* the script asks the assistant,
  which does it on the owner's word. *Against:* one more stop in a
  flow meant to have none.
- **D7. The first build to prove the connection.** *Decided:* wait for Cloudflare's
  build of a real pull request (scenario 5). *Against:* a new site may have no open pull
  request; the assistant would have to open an empty one, which is noise in the history.

## Review trail

`docs/reviews/REVIEW-plan-2026-10-12-pr265.md`: the PLAN gate, at High depth because the
script this plan describes changes a Cloudflare account with a token and can make a site
public.
