# Plan: Cloudflare setup by one token, for a site connected to GitHub

Requirements record for a script that does not exist yet. Where this plan and the shipped
files disagree, the files win until plan step 6 changes them. Names of sites and people
stay out of this public repo on purpose; the business in the scenarios is made up.

Two series of steps run through this file. **Plan steps** are the rows of the status
table. **Script steps** are the nine things the script does, under "Shape".

## Status, 2026-10-12 · the kit's files read at origin/main 714516a

| # | Plan step | State | Evidence |
|---|-----------|-------|----------|
| 1 | Requirements and scenarios (this file) | ▶ written; PLAN gate (High) in progress, round 1 done and its findings worked in | this file; trail: `docs/reviews/REVIEW-plan-2026-10-12-pr265.md` |
| 2 | The Cloudflare checklist reaches `main` (`docs/CLOUDFLARE-CHECKLIST.md`; another session's work) | ✅ merged 2026-10-12. The script that runs its outside checks followed the same day | karero/croftweaver#266 (`7642954`); the check script: karero/croftweaver#267 (`d382cbe`) |
| 3 | The maintainer closes the decisions D1 to D7 below | ✅ all seven decided as recommended (maintainer, 2026-10-12: "all as recommended"). D2 and D3 changed the same day, after plan step 2: the script lives in the kit (maintainer, 2026-10-12: "In the kit") | section "Decisions D1 to D7" |
| 4 | Spike on a throwaway repository, project and zone: every write call once, and the eight questions under "Not verified" | ⏸ not started | — |
| 5 | The script and its tests against a stub of Cloudflare's API. Two pull requests: the project stage (script steps 1 to 6 and 9), then the settings and DNS stage (script steps 7 and 8) | ⏸ not started | — |
| 6 | The kit's files that say otherwise today are changed with the script (list under "Hooks") | ⏸ not started | — |
| 7 | Review gate on the script (High: it changes an account with a token, and it can make a site public) | ⏸ not started | — |
| 8 | One real site set up with it, start to finish, with the owner watching | ⏸ not started | — |
| 9 | Release note line | ⏸ not started | — |

Legend: ✅ done · ▶ in progress · ⏸ not started or blocked · ⚠ deviated

## Why

Putting a new site on Cloudflare is the step where an owner who has never seen the
dashboard loses the most time, and where a wrong click has the biggest effect. The kit has
three routes today (`skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md`):

- **A, by token:** the assistant creates the project and deploys with Wrangler, but the
  site is a Direct Upload project. Cloudflare does not build it from GitHub, so
  `PUBLISHING.md`'s push-to-deploy does not apply to it.
- **B, connected to GitHub:** a push builds, but the owner clicks through the dashboard
  alone, with `website-team-setup` §6 warning about the traps.
- **C, the assistant drives the browser.** Slow, and not every assistant can.

The maintainer's decision (2026-10-12): the setup should be done for the owner as far as a
token allows, on the model of route B. This plan is that: route B's result, with as much of
route A's effort as Cloudflare's API allows.

It is written after one site's launch on 2026-10-12, set up by hand on route B. Six things
went wrong that day. Each has at least one scenario below:

1. The project was created with production branch `main` on a two-stage site. Cloudflare
   published `main` to the live domain at once, with unfilled slots on the legal pages, and
   the domain was open to search engines. (Scenarios 2, 3, 9 and 10.)
2. The project lost its connection to GitHub. Merges and pushes built nothing, and the
   one sign found that day was a banner in the dashboard. (Scenarios 7, 8 and 28.)
3. "Create deployment" in the dashboard did nothing while the connection was broken.
   (Scenario 16.)
4. A variable was typed into the dashboard and not saved; later it was saved, but no
   production build followed, so it had no effect until the next publish. (Scenarios 15
   and 16.)
5. The owner took the project's own `pages.dev` address for the preview. It is the live
   build's second address; on that site the preview is the same address with `main.` in
   front. (Scenarios 24 to 26.)
6. A DNS record for a search engine's verification was entered with name and target the
   wrong way round. (Scenario 17.)

## Shape

### What the owner does

**Before the script, once.** Neither is this plan's work; the script only checks the second.

- Accounts at GitHub and Cloudflare. `docs/GETTING-STARTED.md` recommends protecting both
  with two-factor sign-in.
- The domain is on Cloudflare: bought there, or moved there with its records compared entry
  by entry ("Going live" in `CLOUDFLARE_FIRST_DEPLOY.md`). The script moves no domain.

**For the script,** none of it in a terminal:

1. Makes one short-lived token, from the permission rows the assistant shows: the rows of
   the checklist's section 6, and Zone → DNS → Edit if the script is to write DNS records.
2. Authorizes Cloudflare's GitHub app for the one repository, once, in the browser.
   (Whether the script can do everything after that, or the owner must also click
   "Connect to Git" once, is the first question of the spike.)
3. Reads what the script is about to do and says yes: once to its list, once more before
   the domain is attached, and once more in each of two rarer cases (scenarios 3 and 22).
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

**The token.** It reads the token from the environment (`CLOUDFLARE_API_TOKEN`) or from
`.dev.vars`, never from an argument. It refuses `.dev.vars` if git tracks the file or does
not ignore it. It never prints or stores the token.

**How a yes reaches it.** An assistant runs the script, usually in a shell with no
terminal, so the script never waits for typed input. A run that needs a yes prints the
question and a short code made from exactly what it asks, changes nothing further, and
ends with exit status 3. The assistant shows the owner the question. On the owner's yes it
runs the script again with `--confirm <code>`. If what the script would do is no longer
what the code was made from (a setting changed, a branch moved), it does not go on: it
prints the new question and a new code. The tests give a yes the same way.

**Exit status.** 0: finished, nothing failed. 1: something failed, was refused, or stops
the run. 2: the command was wrong. 3: waiting for a yes.

**Leaving a line out.** `--skip <id>` leaves one setting of script step 7 as it is. The
ids are the check script's (`https`, `tls`, `nel`, `bot`, `email`, `ai`).

**Where it sends requests.** Cloudflare's API host and the site's own addresses. For the
tests, an override of the API host and of the site's addresses is accepted from the
environment only, only for a loopback address (as `cloudflare-check.mjs` does for a local
page), and never from `.dev.vars`; the script prints a line whenever one is in effect.

**What it reads from git.** The site's own checkout. A branch's head is what `git
ls-remote origin` answers at that moment, not a local ref. To read files at a commit it
needs that commit in the local repository, and says to fetch if it is missing.

### What the script does

1. **Looks first.** From the site's folder: `PROD_BRANCH` and `SITE.url` in
   `src/config.ts`, and the repository behind the `origin` remote. From Cloudflare: that
   the token is active and when it ends, the zone of the domain, and the Pages projects of
   the account that holds that zone. It stops here if `SITE.url` is still the starter's
   `example.com`, or if Cloudflare has no active zone for the domain.
   - **The publish model.** `PROD_BRANCH` is `main` and `origin` has no `production`
     branch: single-stage. `PROD_BRANCH` is `production` and `origin` has that branch:
     two-stage. Anything else: the two signs disagree. The script stops, says so, and says
     what each model needs. The starter ships `PROD_BRANCH = 'production'` for every site,
     so the value alone decides nothing.
   - **Which project is this site's.** First a project whose `source` names this
     repository. If there is none, a project with the wanted name (`--project`, by default
     the repository's name): it stops if that project has no `source` (a Direct Upload
     project cannot be turned into a connected one; `website-team-setup` §6, item 9, has
     the way round) or names another repository. If there is none of either, it will
     create one.
   - **What the token may do.** The call that tests a token does not say. The script
     makes one read call for each area it will change (zone settings, Transform Rules,
     Bot Management, DNS records, Pages). An area it cannot read is a step it will skip. A
     read that works does not prove the write will: a write Cloudflare refuses later ends
     that one line as "by hand" in the report, and the run goes on. A refused write to the
     project itself ends the run.
2. **Says what it will do.** Prints every change it is about to make, each with what is
   there now and what it will be: which lines touch every host of the domain and not only
   this site, with the zone's other proxied hosts named beside them (or a line saying it
   could not read them); which lines a visitor can notice; and which steps it will skip
   and why. Nothing has changed yet. It goes on after a yes to this list.
3. **Sets up the project.** Creates it, or adopts the one found in script step 1: build
   command `npm run build`, output `dist`, production branch as `PROD_BRANCH` says, Fail
   open. From here on it takes the project's `pages.dev` address from the `subdomain`
   Cloudflare returns, never from the project's name: the two can differ.
4. **Gets a first build of the production branch, if there is none.** If no domain is
   attached and the project's newest production deployment is not of the head of the
   production branch (a new project has none at all), the list of script step 2 holds the
   line "build the production branch; it is served at the project's `pages.dev` address,
   not on your domain". The script then waits for that build, starting it itself if
   creating the project did not.
5. **Proves the GitHub connection with a build Cloudflare started itself.** It first reads
   whether the project builds previews at all; if they are switched off, it says that it
   cannot prove the connection this way and stops before the domain. Otherwise it asks the
   assistant to push a commit to a pull request's branch now (a new pull request, or a
   new commit on an open one), and waits for a preview deployment of that commit that
   Cloudflare created after the script began to wait. None within the set time is reported
   as "Cloudflare has not built this commit", with the two likely causes (the connection
   is broken or was never made; the build is still queued) and how to tell them apart.
   The run stops before the domain.
6. **Attaches the domain, and only on a yes of its own.** The domain is the host of
   `SITE.url`, and only that one; a second host (`www` beside the apex, or the reverse) is
   named in the report as left by hand.
   - **Before it asks,** it refuses unless all of these hold: the project's newest
     production deployment, as Cloudflare lists it, is of the head of the production
     branch and succeeded; at that commit, `tests/placeholders.spec.ts` has an empty
     `UNFILLED_UNTIL_LAUNCH` list (the kit's own condition for a launch, `new-website`
     §4); and a search of that commit's `src/` and `public/` for the site's own draft
     token (`DRAFT_TOKEN` in the same file; the starter's is `[MISSING:`) finds nothing.
     If that file is missing, or the script cannot read either line in the form the
     starter writes it, it cannot tell, and refuses in the same way. A refusal names what
     it found and what to do. These are the script's own stops, not the launch check:
     that stays `new-website` §4 and the site's tests, which the script does not run, and
     the question says so.
   - **The question** names the domain, the commit, the token it searched for, the DNS
     record the domain has now and where it points, and what will change.
   - **After the yes** it attaches the domain and waits for Cloudflare to report it
     active. Any other ending (`error`, `blocked`, `deactivated`, or still not active at
     the time limit) ends the run with exit status 1 and what Cloudflare said; the script
     does not detach the domain, and a later run takes up at this point. Only once the
     domain is active does it send the first request to it. It then runs the check
     script: if the domain serves another commit than the one in the question (the branch
     moved after the yes), it says so as a failure and stops.
7. **Applies the settings of the Cloudflare checklist that an API can set:** Always Use
   HTTPS, Minimum TLS Version, Email Address Obfuscation, the NEL switch, Bot Fight Mode
   and the AI crawler policies, and the rule that removes the NEL headers only if they are
   still sent after the switch. Order, values and cautions are the checklist's, which
   stays the one place they live. It does not switch HSTS on.
8. **Writes DNS records the owner dictates,** such as the verification records of Google
   and Bing, each written "DNS only". It checks the record's shape (scenario 17) and shows
   type, name and content before writing.
   - A TXT record is added beside the TXT records already at that name, which it lists;
     it never changes or removes one. (A domain with mail has its SPF record at the same
     name Google's record goes to.)
   - A CNAME is written only if no record of that name exists. If one exists with another
     target, the script writes nothing and reports the line as "by hand".
   - It reads each record back through the API, then asks the zone's own nameservers,
     for up to a set time. If they do not show it in that time, the line reads "read back
     through the API only".
9. **Sets `CANONICAL_URL`, checks from outside, and reports.**
   - **The variable.** The value is `https://` and the attached domain, taken from
     Cloudflare's answer and not typed by anyone. The script writes it only if the spike
     showed how to change one variable and keep the others, secrets included; it lists the
     variables' names before and after, and stops with exit status 1 if one is missing.
     Then it starts a production deployment and waits for its last stage, but only if two
     things hold: the head of the production branch is the commit that is live, and the
     live deployment's recorded variables and build settings differ from the project's
     saved ones in `CANONICAL_URL` alone. Otherwise it says "the variable is saved, but no
     build has picked it up", names every other difference a new build would also pick
     up, and leaves the build to the next publish. It says the same, with exit status 1,
     if the deployment it started does not appear or does not succeed in the set time.
     After a deployment it started, it checks that the new deployment is of the commit it
     expected, and says so as a failure if not.
   - **The outside check** is `cloudflare-check.mjs --json`, run with the project's
     `pages.dev` address and the commit the script expects. The script passes each line on
     as that script judged it: only `ok` is reported as done; `look`, `hand` and `skip`
     are reported as what they are.
   - **The report** gives, for each setting, what it was, what it is now and how that was
     checked (read back through the API, seen from outside, or "no outside check
     exists"); the live address; the preview address, which depends on the publish model
     and which it takes from a deployment Cloudflare lists and opens before naming it
     (two-stage: the newest preview deployment of `main`, or a line saying `main` has no
     preview build yet; single-stage: there is no preview of `main`, and the report says
     that pull requests get their own); what is left for the owner by hand, HSTS with the
     earliest day for it; and a reminder to delete the token.

**Nothing reaches the domain early.** Script steps 7, 8 and 9, and every request to the
live domain, run only when the domain is attached and active, in this run or an earlier
one. If it is not, the report lists them as not done.

**What a visitor can notice.** Attaching the domain; a change of the production branch on
a project that already serves a domain; the forwarding of the `pages.dev` address; and
four of the settings of script step 7 (Always Use HTTPS redirects plain-HTTP visitors of
every host in the zone, Minimum TLS Version turns away very old clients, Email Address
Obfuscation changes the served pages, and the NEL rule removes `Report-To` on every
host). The first two have a yes of their own. The others are lines of the list, each
marked as one a visitor can notice.

**What it never does.** It never merges and never runs `npm run ship`; that stays with the
owner, or the assistant on the owner's word. It never deletes or detaches a project, a
domain, a variable or a DNS record.

**A second run on a finished setup changes nothing.** Every step reads first and skips
what is already right, so the script can be run again after a failure or a year later. On
such a run it does not ask for a new pull request: it reports whether the newest
production deployment is of the head of the production branch, succeeded and was started
by Cloudflare from a push, and says that this shows the connection worked at the last
publish, not that it works today.

## Scenarios

The owner is Lena. Her site is `lenas-backstube` on GitHub, two-stage (`PROD_BRANCH` is
`production`, and the branch exists), and her domain is `lenas-backstube.example`, already
on Cloudflare. Where a scenario does not say otherwise, the project's `pages.dev` address
is `lenas-backstube.pages.dev`, and each yes is given by a second run with the code.

| # | Given | When | Then | Test |
|---|-------|------|------|------|
| 1 | Lena has made the token and authorized the GitHub app; no project exists | the script runs, and runs again with the list's code | the first run ends with status 3 and has sent no write call; after the second, the project `lenas-backstube` exists with production branch `production`, build command `npm run build`, output `dist`, Fail open on, and a build of `production` was started or found; nothing answers on her domain | stub API: no write before the code; the create call carries these values |
| 2 | a project connected to her repository exists with production branch `main`, and no domain is attached | the script looks | its list holds the line "Your live address would publish `main`, the preview. I will set the production branch to `production`" | stub API returns such a project; the first write after the code is the branch change |
| 3 | the same project, but her domain is attached to it | the script looks | it leaves that change out of the list and asks about it alone, with a code of its own: what her domain serves now, and that this changes at the next production build | the branch change is sent only after its own code |
| 4 | `PROD_BRANCH` is `production` and `origin` has no `production` branch | the script looks | it stops with status 1, says the two signs disagree, and says what each model needs: for two-stage, the assistant creates the branch from the reviewed `main` on the owner's word (D6); for single-stage, `PROD_BRANCH` becomes `main` | fixture repository without the branch; no write call to Cloudflare |
| 5 | a project named `lenas-backstube` exists and has no `source` | the script looks | it stops: "this is a Direct Upload project; Cloudflare cannot connect it to GitHub", and points to `website-team-setup` §6, item 9 | stub API returns such a project; no write call |
| 6 | Lena made a project by hand under another name, connected to her repository | the script looks | it adopts that project and creates none | stub API returns it; no create call |
| 7 | the project exists but Cloudflare cannot reach the repository | the assistant pushes a commit to a pull request and the script waits | after the set time it reports "Cloudflare has not built this commit", with both likely causes and how to tell them apart, exit status 1, and no question about the domain | stub: the commit never appears among the deployments |
| 8 | an open pull request was built yesterday, and the connection has broken since | the script is to prove the connection | yesterday's deployment does not count; it asks for a new commit and ends as scenario 7 | stub: one older deployment of the old head |
| 9 | at the head of `production`, `UNFILLED_UNTIL_LAUNCH` still lists `/privacy` | Lena wants her domain attached | the script refuses, names the list and its entries, and asks no question | fixture repository with the starter's list; no domain call |
| 10 | the list is empty, and a page under `src/` holds `[MISSING: opening hours]` | Lena wants her domain attached | the script refuses and names the file and the line | fixture repository with the marker |
| 11 | a German site whose `DRAFT_TOKEN` is `[FEHLT:`, with `[FEHLT: Öffnungszeiten]` in a page | Lena wants her domain attached | the script refuses the same way, and the search it reports is for `[FEHLT:` | fixture repository with that token |
| 12 | the site has no `tests/placeholders.spec.ts` | Lena wants her domain attached | the script refuses: it cannot tell whether the site is ready, and says the domain can be attached by hand | fixture repository without the file |
| 13 | the conditions of script step 6 hold; her apex record points at her old host | Lena reads the question and gives its code | the question named the commit, the record and its target, and what will change; then the domain is attached, the script waits until it is active, sends no request to the domain before that, runs the check script, and only then says "live" | stub: status pending then active; the stub site records when the first request comes |
| 14 | the same, but Cloudflare answers `error`, or the domain is still pending at the time limit | the script waits | exit status 1 with Cloudflare's own words; the domain stays attached; script steps 7 to 9 are reported as not done; a later run takes up at the wait | stub: status `error`; and a status that stays `pending` |
| 15 | the domain is active and serves the head of `production`; the project has one other variable and one secret | the script sets `CANONICAL_URL` | both other names are there on the read-back, a production deployment was started and finished, and the check script's `canonical` item is `ok` | stub API with a variable and a secret; a local stub site for the 301 |
| 16 | the same, but the head of `production` is newer than the live build; or a second variable was saved since the live build; or the deployment the script starts never appears | the script sets `CANONICAL_URL` | it says "the variable is saved, but no build has picked it up", with the other difference by name; in the first two cases it sends no deployment call, in the third it ends with status 1 | stub: a newer head; a deployment whose recorded variables lack a saved one; a deployment call that is answered and followed by no deployment |
| 17 | Lena gives the Bing record with name and content the wrong way round | the script shows what it will write | it sees that the name ends in a verification host the kit knows (`verify.bing.com`), or that a CNAME's target has no dot, says the two look swapped, and writes nothing until she gives them again | unit test on the record check, with a record in the form Bing issues it (captured in the spike, code removed) |
| 18 | her domain has an SPF record, a TXT at the apex | the script writes Google's TXT record at the apex | Google's record is added, the SPF record is listed and untouched | stub API holding the SPF record; the write is a create, never an update |
| 19 | a CNAME of the wanted name exists with another target | the script is to write hers | it writes nothing and reports the line as "by hand", with both targets | stub API holding the other record |
| 20 | the token cannot read DNS records | the script looks | its list names which areas it can read, and the DNS step as skipped | stub: the DNS read is refused |
| 21 | the token reads zone settings but may not change them | the script applies the settings | each refused setting is "by hand" in the report with the permission row it needs; the other steps ran | stub: 403 on the setting's write |
| 22 | the token has no end date, or the zone list shows more zones than hers | the script looks | it says so and asks for a narrower token; it goes on with this one only after a yes of its own, with a code | stub: no `expires_on`; a zone list with two zones |
| 23 | the token is in `.dev.vars`, and git tracks that file; or git neither tracks nor ignores it | the script starts | it stops before reading the file and says how to ignore it | two fixture repositories |
| 24 | Cloudflare gave the project the address `lenas-backstube-9x2.pages.dev` | the script checks and reports | every check and every line of the report uses that address; `lenas-backstube.pages.dev` is requested nowhere | stub API whose `subdomain` differs from the name; the stub site records the hosts requested |
| 25 | the run is finished on Lena's two-stage site | the script reports | the report names `lenas-backstube.example` as live, gives the preview address it read from the newest preview deployment of `main` and opened, says that `lenas-backstube.pages.dev` now forwards to the live address, and lists Crawler Hints, the Web Analytics switch and HSTS, with a date, as left for Lena | snapshot of the report |
| 26 | a single-stage site (`PROD_BRANCH` is `main`, no `production` branch) | the script reports | the report names no preview of `main`; it says that `main` is the live site and that each pull request gets its own preview address | snapshot of the report |
| 27 | her zone also has a proxied host `shop.lenas-backstube.example` | the script prints its list | the lines for Always Use HTTPS, Minimum TLS Version, Email Address Obfuscation and the NEL rule name that host; with `--skip tls` the TLS line is gone and that setting is not written | stub API with the second host |
| 28 | the script ran last month | it runs again | it makes no write call, asks for no pull request, reports every setting as already right, and says what the newest production deployment shows about the connection and what it does not | stub API holding the end state |

The tests run the script as a program against a stub of Cloudflare's API and small sites
on `127.0.0.1`, the way `make test-cloudflare-check` tests the check script, and are wired
into the same CI workflow (`.github/workflows/clean.yml`). The stub's answers are the ones
captured in the spike, with the token and the account's ids removed.

## What is known, and how

**Done on one live site, 2026-10-12** (a project connected to GitHub, two-stage):

- `wrangler pages deploy dist --project-name <project> --branch production` made a
  production deployment in a project that is connected to GitHub. It was the way out while
  the GitHub connection was broken. The script does not use it; it stays the emergency
  route in the kit's notes. A live build made that way was built on a computer, not by
  Cloudflare from the branch.
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
- The preview of `main` answered at the project's `pages.dev` address with `main.` in
  front.

**Read in Cloudflare's API reference, 2026-10-12, not tried:**

- [Creating a project](https://developers.cloudflare.com/api/resources/pages/subresources/projects/methods/create/)
  takes `production_branch`, a `build_config` (build command, output directory),
  `deployment_configs` per environment with `env_vars` and `fail_open`, and a `source`
  object for GitHub (owner, repository name, production branch, which previews build).
  Permission: Pages Write.
- [A project](https://developers.cloudflare.com/api/resources/pages/subresources/projects/methods/get/)
  comes back with `subdomain` ("The Cloudflare subdomain associated with the project") and
  `domains`. A deployment carries the commit that caused it
  (`deployment_trigger.metadata.commit_hash`), its environment, its `aliases` and its
  `latest_stage`.
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

**Not verified. The spike (plan step 4) settles these before any code.** It also makes
every write call the script will make, once, against a throwaway project and zone, reads
each back, and keeps each request and answer as the stub's fixture.

1. Whether a project created through the API with a `source` object is connected to
   GitHub once the app is authorized for the repository, or whether "Connect to Git" in
   the dashboard is the only way. If it is the only way, the owner clicks once more and the
   script adopts the project (scenario 6).
2. Whether creating a connected project starts a first production build by itself, and
   whether the deployment call above, sent without a branch to a connected project, builds
   the head of the production branch (script steps 4 and 9).
3. Whether attaching a domain creates or changes its DNS record, or the script must write
   it; and what the domain serves while its status is not yet active.
4. What the read calls of script step 1 show about a token: whether a refused read names
   the missing permission, and whether listing zones shows that a token reaches more than
   one.
5. What a domain serves between a change of the production branch and the first build of
   the new branch (scenario 3).
6. Whether a change to one variable, or to Fail open on an adopted project, keeps the
   project's other variables, secrets included, in both environments; and which request
   body does that. If no body keeps secrets, the script leaves `CANONICAL_URL` "by hand" on
   a project that has one.
7. What a deployment records: whether its variables and build settings can be compared
   with the project's saved ones, and how a deployment Cloudflare started from a push
   differs from one started by the API or by an upload (script steps 5 and 9).
8. Whether Cloudflare builds a preview for a commit pushed to a pull request that was
   opened before the project was connected, and the exact record Bing issues for CNAME
   verification (scenario 17).

Whatever the spike answers differently from what a scenario assumes, that scenario is
rewritten before plan step 5, and this file says which.

The settings of script step 7, their permission rows and their cautions are the
checklist's, with that file's own sources. The checklist says that of those calls only the
Transform Rules call has been run on live sites.

## Decisions taken

1. **The model is route B** (connected to GitHub), by the maintainer, 2026-10-12.
   Previews per pull request and `npm run ship` are worth one authorization in the browser.
2. **The checklist stays the list.** The script takes its settings, their order and their
   cautions from `docs/CLOUDFLARE-CHECKLIST.md`; this plan adds the project steps. A test
   keeps the two in step: item titles and dashboard paths as `make test-cloudflare-check`
   compares them for the check script, and also each value the script writes, against the
   checklist's own words for it (the value in an item's title; the three AI policy values
   and the two header names of the NEL rule in the item's text).
3. **The domain has its own yes,** because it is the step that makes a site public and
   open to search engines.
4. **Read, say, do, read back, and check from outside where an outside check exists.** A
   setting the check script can see counts as done when a request from outside shows it,
   not when the API says so: the checklist records a case where the API reported a header
   off and the site still sent it. Fail open and the build settings have no outside check
   (`CLOUDFLARE_CHECK.md`); for them the report says "read back through the API only".
5. **One check, not two.** Whenever the script needs to know what the live site or the
   `pages.dev` address answers (the build that is live, the forwarding, the NEL headers),
   it runs `cloudflare-check.mjs` and reads that item. It carries no reading of its own
   for what that script covers. What the check script lacks for this is added to the check
   script in plan step 5, in the first of its two pull requests: a way to run single
   items, and the `canonical` item asking for a path and not only the home page.
6. **A yes is a second run with a code** (see "How a yes reaches it"). A flag that says
   yes to whatever the script would do does not exist.

## Decisions D1 to D7

Closed by the maintainer on 2026-10-12. The argument against each stays here as the record
of what was weighed.

- **D1. One yes or many.** *Decided:* one yes for the whole list, a second for the
  domain. Two rarer cases have one too: a production-branch change on a project that
  already serves a domain (scenario 3), and a token broader than needed (scenario 22).
  *Rests on:* "the owner should not have to do anything". *Against:* guardrail 4 in
  `CLOUDFLARE_FIRST_DEPLOY.md` asks for a yes before each change to the account; one yes
  is weaker, and the list must be read carefully to be worth it. The list holds changes a
  visitor can notice on every host of the domain; it marks them, names the other hosts,
  and each can be left out with `--skip`. Plan step 6 rewrites that guardrail for the
  script: the printed list, confirmed with its code, is the confirmation for the changes
  it names, and for nothing else.
- **D2. What it is written in.** *Decided first:* Node, as one file in the site template.
  *Changed the same day, with D3:* Node, as one file in the kit with nothing from npm,
  like the check script. *Against:* most of the kit's own scripts are bash or Python.
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
  build of a real pull request (scenarios 7 and 8). *Against:* a new site may have no open
  pull request; the assistant then opens one with an empty commit, which is noise in the
  history.

## Hooks

Plan step 6 brings these in line in the same pull requests as the script, because each
says something the script makes untrue or incomplete. Known today:

- `CLOUDFLARE_FIRST_DEPLOY.md`: the opening advice, which recommends route A to newcomers
  (by decision 1 the script becomes the recommended way; route A stays for an owner who
  wants no connection to GitHub); option B; guardrail 4; "Redeploy with a new commit"
  under "After go-live".
- `skills/new-website/SKILL.md` §4, which repeats that recommendation.
- `website-team-setup` §6: connecting by hand, and item 3, which treats the project's name
  as the first part of its `pages.dev` address.
- `docs/CLOUDFLARE-CHECKLIST.md`: section 6, and section 5's "your Pages project's name
  (the first part of its `.pages.dev` address)".
- `CLOUDFLARE_CHECK.md`: "By hand, always", and the new way to run single items.
- `search-console-setup`, which calls the DNS record a human action.

## Review trail

`docs/reviews/REVIEW-plan-2026-10-12-pr265.md`: the PLAN gate, at High depth because the
script this plan describes changes a Cloudflare account with a token and can make a site
public.
