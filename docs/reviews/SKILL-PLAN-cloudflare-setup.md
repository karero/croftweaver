# Plan: Cloudflare setup by one token, for a site connected to GitHub

Requirements record for a script that does not exist yet. Where this plan and the shipped
files disagree, the files win until plan step 6 changes them. Names of sites and people
stay out of this public repo on purpose; the business in the scenarios is made up.

**Do not build from this text yet.** The PLAN gate stopped after round 3 without a clean
verdict. Round 3 found four BUGs, eight RISKs and fourteen NITs that are not worked in
(H1 to H26 in `docs/reviews/REVIEW-plan-2026-10-12-pr265.md`). Three of them are wrong
statements in this file: script step 4 would build on a project that already serves a
domain; script step 7 reports a failure on a finished setup; and D1's reason is false,
because the settings can be written before the domain is attached.

**What happens next** (maintainer, 2026-10-13: "Trial run first, go back to two yeses"):
the spike of plan step 4 ran first (done 2026-10-13, see "Seen in the spike"). Now this
file is rewritten once, from what the spike showed and with two yeses (D1), and that text goes
through a new PLAN gate.

Two series of steps run through this file. **Plan steps** are the rows of the status
table. **Script steps** are the nine things the script does, under "Shape".

## Status, 2026-10-13 · the kit's files read at origin/main 714516a

| # | Plan step | State | Evidence |
|---|-----------|-------|----------|
| 1 | Requirements and scenarios (this file) | ⚠ written; the PLAN gate (High) stopped after round 3, not converging. Rounds 1 and 2 are worked in, round 3 is open. How to go on is the maintainer's decision | this file; trail: `docs/reviews/REVIEW-plan-2026-10-12-pr265.md` |
| 2 | The Cloudflare checklist reaches `main` (`docs/CLOUDFLARE-CHECKLIST.md`; another session's work) | ✅ merged 2026-10-12. The script that runs its outside checks followed the same day | karero/croftweaver#266 (`7642954`); the check script: karero/croftweaver#267 (`d382cbe`) |
| 3 | The maintainer closes the decisions D1 to D7 below | ✅ all seven decided as recommended (maintainer, 2026-10-12: "all as recommended"). D2 and D3 changed the same day: the script lives in the kit ("In the kit"). D1 changed twice on 2026-10-13: first to three stages with a yes for each ("Three, one per stage"), asked for with a reason round 3 showed to be false (H3); then back to two yeses ("go back to two yeses") | section "Decisions D1 to D7" |
| 4 | Spike on a throwaway repository and project: every write call once, the eight questions under "Not verified" and the observations round 3 added (section "The spike") | ✅ done 2026-10-13, apart from two points: whether a change to Fail open reaches the build that is live (Cloudflare does not record it), and Bot Management's PUT with only some fields (not tried on a live zone). The answers are under "Seen in the spike"; the body of this file is not yet rewritten from them | 147 captures, kept outside every repository; the private throwaway repository |
| 5 | The script and its tests against a stub of Cloudflare's API. Two pull requests: the project and domain stages (script steps 1 to 7), then the settings stage (script steps 8 and 9) | ⏸ not started | — |
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
   the domain was open to search engines. (Scenarios 1, 3, 4, 12 and 13.)
2. The project lost its connection to GitHub. Merges and pushes built nothing, and the
   one sign found that day was a banner in the dashboard. (Scenarios 9, 10 and 38.)
3. "Create deployment" in the dashboard did nothing while the connection was broken.
   (Scenario 22.)
4. A variable was typed into the dashboard and not saved; later it was saved, but no
   production build followed, so it had no effect until the next publish. (Scenarios 21
   and 22.)
5. The owner took the project's own `pages.dev` address for the preview. It is the live
   build's second address; on that site the preview is the same address with `main.` in
   front. (Scenarios 35 to 37.)
6. A DNS record for a search engine's verification was entered with name and target the
   wrong way round. (Scenario 29.)

## Shape

### What the owner does

**Before the script, once.** Neither is this plan's work; the script only checks the second.

- Accounts at GitHub and Cloudflare. `docs/GETTING-STARTED.md` recommends protecting both
  with two-factor sign-in.
- The domain is on Cloudflare: bought there, or moved there with its records compared entry
  by entry ("Going live" in `CLOUDFLARE_FIRST_DEPLOY.md`). The script moves no domain.

**For the script,** none of it in a terminal:

1. Makes one short-lived token, from the permission rows the assistant shows: the rows of
   the checklist's section 6, and Zone → DNS → Edit. The domain stage reads the domain's
   own record and may have to change it, and the settings stage writes the verification
   records.
2. Authorizes Cloudflare's GitHub app for the one repository, once, in the browser.
   (Whether the script can do everything after that, or the owner must also click
   "Connect to Git" once, is the first question of the spike.)
3. Reads what each stage is about to do and says yes to it: three times in all, once per
   stage.
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

**Three stages,** each named on the command line and run on its own:

| Stage | When | It asks one yes for | Script steps |
|---|---|---|---|
| `project` | setup day | the list of changes to the Pages project | 1 to 5 |
| `domain` | launch day | attaching the domain, and forwarding the `pages.dev` address to it | 6 and 7 |
| `settings` | once the domain serves the site | the list of Cloudflare settings and DNS records | 8 and 9 |

A stage does only its own changes. Each stage can be run on a site that was set up by
hand; it reads what is there and leaves what is already right.

**The token.** The script reads the token from the environment (`CLOUDFLARE_API_TOKEN`) or
from `.dev.vars`, never from an argument. It refuses `.dev.vars` if git tracks the file or
does not ignore it. It never prints or stores the token, and sends it to Cloudflare's API
host only. It refuses a token that has no end date, and one that it can see reaches more
zones than this site's: it says so and asks for a narrower one (guardrail 2 in
`CLOUDFLARE_FIRST_DEPLOY.md`).

**How a yes reaches it.** An assistant runs the script, usually in a shell with no
terminal, so the script never waits for typed input. A stage that has something to change
prints its question and a short code, changes nothing, and ends with exit status 3. The
assistant shows the owner the question. On the owner's yes it runs the same stage again
with `--confirm <code>`. The code is made from the end state the question describes and
the facts it names (which project, which branch, which commit, which record, which
values), not from what is left to do. So the same code keeps fitting while the stage is
carried out over more than one run, and stops fitting when one of those facts changes: the
script then prints the new question and a new code, and changes nothing. A stage that
finds nothing to change asks nothing. The tests give a yes the same way.

**It does not wait long.** An assistant's shell ends a command after a minute or two. So
no run waits more than 60 seconds in all. Where Cloudflare is not done by then (a build, a
domain becoming active), the run ends with exit status 4 and says what it waits for; the
assistant runs the same command again, with the same code. A run that was cut off leaves
nothing half-written: each write is one call, and the next run reads what is there.

**Exit status.** 0: the stage is finished and everything it set is in effect. 1: something
failed, was refused, or is not in effect. 2: the command was wrong. 3: waiting for a yes.
4: waiting for Cloudflare, or for a push; run it again.

**Where it sends requests.** Cloudflare's API host; the site's own addresses (the live
domain and the project's `pages.dev` addresses, through the check script); the zone's
nameservers, for DNS lookups; and GitHub, only through `git ls-remote origin`. For the
tests, the API host, the site's addresses and the resolver can each be replaced by an
address on this machine. Such an override is read from the environment only, never from
`.dev.vars`, and is accepted only as a literal loopback address (`127.0.0.0/8` or `[::1]`),
never as a name. This is narrower than the check script's rule for a local page, which
also takes names ending in `.test` and `.localhost`; that rule is not reused here. The
script prints a line whenever an override is in effect.

**What it reads from git.** The site's own checkout. A branch's head is what `git
ls-remote origin` answers at that moment, not a local ref. To read files at a commit it
needs that commit in the local repository, and says to fetch if it is missing.

**What it never does.** It never merges and never runs `npm run ship`; that stays with the
owner, or the assistant on the owner's word. It never deletes or detaches a project, a
domain, a variable or a DNS record. The one existing DNS record it may change is the
attached domain's own, inside the domain stage's yes (script step 6). It does not repair a
project that already serves a domain with the wrong production branch (scenario 4).

### The `project` stage

1. **Looks first.** From the site's folder: `PROD_BRANCH` and `SITE.url` in
   `src/config.ts`, and the repository behind the `origin` remote. From Cloudflare: that
   the token is active and when it ends, the zone of the domain, and the Pages projects of
   the account that holds that zone. It stops here if `SITE.url` is still the starter's
   `example.com`, or if Cloudflare has no active zone for the domain. Every stage begins
   with this step.
   - **The publish model.** `PROD_BRANCH` is `main` and `origin` has no `production`
     branch: single-stage. `PROD_BRANCH` is `production` and `origin` has that branch:
     two-stage. Anything else: the two signs disagree. The script stops, says so, and says
     what each model needs. The starter ships `PROD_BRANCH = 'production'` for every site,
     so the value alone decides nothing.
   - **Which project is this site's.** With `--project <name>`: that project, if its
     `source` names this repository; the script stops if it names another repository or
     has no `source` (a Direct Upload project cannot be turned into a connected one;
     `website-team-setup` §6, item 9, has the way round). Without `--project`: the one
     project whose `source` names this repository; if two do, it stops and asks for
     `--project`. If none does, it looks for a project named like the repository, with
     the same two stops, and if there is none it will create one of that name.
   - **What the token may do.** The call that tests a token does not say. The script
     makes one read call for each area the stage will change. An area it cannot read is a
     step it will skip. A read that works does not prove the write will: a write
     Cloudflare refuses later ends that one line as "by hand" in the report, with the
     permission row it needs, and the run goes on. A refused write to the project itself
     ends the run.
2. **Says what it will do.** Prints every change the stage is about to make, each with
   what is there now and what it will be, and which steps it will skip and why. Its last
   line says that afterwards the assistant pushes one commit to a pull request, so that
   Cloudflare can show the connection works (script step 5).
3. **Sets up the project.** Creates it, or adopts the one found in script step 1: build
   command `npm run build`, output `dist`, production branch as `PROD_BRANCH` says, Fail
   open. It changes an existing project's settings only with the request the spike showed
   to keep the project's variables, secrets included; if the spike found none, such a line
   reads "by hand" on a project that has a secret, and nothing is written for it. It lists
   the variables' names before and after each such write and stops with exit status 1 if
   one is missing. From here on it takes the project's `pages.dev` address from the
   `subdomain` Cloudflare returns, never from the project's name: the two can differ.
4. **Gets a first build of the production branch, if there is none.** If the project has
   no succeeded production deployment of the head of the production branch, the list
   holds the line "build the production branch; it is served at the project's `pages.dev`
   address, not on your domain". The script starts that build if creating the project did
   not, and reports its state.
5. **Reports whether the GitHub connection works.** The proof is a preview deployment
   that Cloudflare started itself from a push, whose last stage succeeded, and that is no
   more than 60 minutes old. If there is one, the report names its commit and time. If
   there is none, the stage ends with exit status 4 and says: push a commit to a pull
   request's branch, wait for Cloudflare's check on it, and run the stage again. A
   deployment that Cloudflare started and that failed is reported as "Cloudflare started
   a build of this commit and it failed": the connection works, the build does not. A
   deployment started through the API or by an upload does not count. If the project
   builds no previews, the script says that the connection cannot be shown this way.
   Every run without a proof also names the two likely causes for the case that a commit
   was pushed (the connection is broken or was never made; the build is still queued)
   and how to tell them apart in the dashboard. The script keeps no count of runs.

### The `domain` stage

6. **Attaches the domain.** The domain is the host of `SITE.url`, and only that one; a
   second host (`www` beside the apex, or the reverse) is named in the report as left by
   hand.
   - **Before it asks,** it refuses, with exit status 1 and the reason, unless all of
     these hold:
     - the `project` stage has nothing left to change;
     - script step 5 has its proof;
     - the project's newest production deployment is of the head of the production
       branch, succeeded, and was built by Cloudflare from the branch, not uploaded;
     - at that commit, `tests/placeholders.spec.ts` has an empty `UNFILLED_UNTIL_LAUNCH`
       list (the kit's own condition for a launch, `new-website` §4);
     - a search of that commit's `src/` and `public/` for the site's own draft token
       finds nothing. The token is `DRAFT_TOKEN` in the same file (the starter's is
       `[MISSING:`), and the search in the site's `.github/workflows/ci.yml` must name the
       same one;
     - the script can read the domain's DNS records, and the host has at most one address
       record (A, AAAA or CNAME).

     If a file is missing, or the script cannot read a line in the form the starter
     writes it, or the two tokens differ, it cannot tell, and refuses in the same way.
     Where the reason is a production build that is missing or old, the refusal says
     that on a two-stage site `npm run ship` publishes it, and that ship's own last check
     cannot pass while no domain is attached: it ends with an error after four minutes
     although the branch was published. These are the script's own stops, not the launch
     check: that stays `new-website` §4 and the site's tests, which the script does not
     run, and the question says so.
   - **The question** names the domain, the commit, the proof of script step 5, the token
     it searched for, the record the host has now and what it will be, and the forwarding
     of script step 7. It says that this makes the site public.
   - **After the yes** it points the host's record at the project (it creates the record,
     or changes the one the question named), unless the spike shows that Cloudflare does
     this itself, and attaches the domain. Until Cloudflare reports the domain active,
     runs end with exit status 4. `error`, `blocked` or `deactivated` ends the run with
     exit status 1 and what Cloudflare said; the script does not detach the domain.
     Once the domain is active, and not before, it sends the first request to it, by
     running the check script with the commit the question named. If the domain serves
     another commit, it says so as a failure and stops before script step 7. The
     conditions above are checked before the domain is attached, not again on a run that
     carries on after it. A run with a fitting code takes the proof the question named,
     however old it is by then. If the domain is already attached and active when the
     stage starts, it attaches nothing, and its question names the forwarding alone.
7. **Forwards the project's `pages.dev` address to the domain.** It sets `CANONICAL_URL`
   to `https://` and the attached domain, taken from Cloudflare's answer and not typed by
   anyone, with the same care for the other variables as script step 3. Then it starts a
   production deployment, but only if all three hold: the head of the production branch
   is the commit that is live; the live deployment was built by Cloudflare from the
   branch, not uploaded; and its recorded variables and build settings differ from the
   project's saved ones in `CANONICAL_URL` alone. Otherwise it says "the variable is
   saved, but no build has picked it up", names every other difference a new build would
   also pick up, leaves the build to the next publish, and ends with exit status 1. It
   says the same if the deployment it started does not appear or fails. When the
   deployment is done it checks that it is of the commit it expected, and runs the check
   script's `canonical` item. `--skip canonical` leaves this step out: the question then
   does not name the forwarding.

### The `settings` stage

It refuses to start unless the domain is attached and active.

8. **Applies the settings of the Cloudflare checklist that an API can set:** Always Use
   HTTPS, Minimum TLS Version, Email Address Obfuscation, the NEL switch, Bot Fight Mode
   and the AI crawler policies. Order, values and cautions are the checklist's, which
   stays the one place they live. It does not switch HSTS on.
   - **Every one of these changes the whole domain,** not only this site. The list says
     so on each line, names the zone's other proxied hosts beside it (or says that it
     could not read them), and says what changes for a visitor there: plain-HTTP visits
     are redirected, very old clients are turned away, the served pages change, bots are
     no longer challenged, AI crawlers are let in.
   - **The NEL rule.** After the switch reads off, the script runs the check script's
     `nel` item once. If the headers are still sent, it adds the rule that removes them,
     as the checklist's steps 3 and 4 do. It reads the ruleset first and sends the
     existing rules back with the new one. The rule removes `Report-To` on every host.
   - **Leaving a line out.** `--skip <id>` leaves one line as it is: `https`, `tls`,
     `email`, `nel`, `nel-rule`, `bot`, `ai`.
9. **Writes DNS records the owner dictates,** such as the verification records of Google
   and Bing, each written "DNS only". It checks the record's shape (scenario 29) and the
   list shows type, name and content.
   - A TXT record is added beside the TXT records already at that name, which the list
     shows; it never changes or removes one. (A domain with mail has its SPF record at the
     same name Google's record goes to.)
   - A CNAME is written only if no record of that name exists. If one exists with another
     target, the script writes nothing and reports the line as "by hand".
   - It reads each record back through the API, then asks the zone's own nameservers
     within the run. If they do not show it yet, the line reads "read back through the
     API only".

### What every stage ends with

- **The outside check,** when the domain is active: `cloudflare-check.mjs --json`, run
  with the project's `pages.dev` address and the commit the script expects (the check
  script's `build` item compares it). The script passes each line on as that script judged
  it. Only `ok` is reported as in effect. A `fail` on something this stage set makes the
  exit status 1. `look`, `hand` and `skip` are reported as what they are.
- **The report** gives, for each thing the stage set, what it was, what it is now and how
  that was checked: seen from outside, or "read back through the API only" where no
  outside check exists (Fail open, the build settings, Minimum TLS Version, where it adds
  the checklist's ssllabs test, and the AI crawler policies). It names the live address.
  It names the preview address by the publish model: on a two-stage site the alias of
  `main` that the newest preview deployment of `main` carries in `aliases`, opened once
  before it is named, or a line saying that `main` has no preview build yet; on a
  single-stage site, that `main` is the live site and each pull request gets its own
  preview. It lists what is left for the owner by hand, HSTS with the earliest day for
  it; says that Cloudflare can put previews behind a sign-in (D5); and reminds the owner
  to delete the token.

**Nothing reaches the domain early.** No stage sends a request to the live domain before
Cloudflare reports the domain active.

**A second run on a finished setup changes nothing.** Every step reads first and skips
what is already right, so each stage can be run again after a failure or a year later. On
such a run the `project` stage asks for no push: it reports whether the newest production
deployment is of the head of the production branch, succeeded and was started by
Cloudflare from a push, and says that this shows the connection worked at the last
publish, not that it works today.

## Scenarios

The owner is Lena. Her site is `lenas-backstube` on GitHub, two-stage (`PROD_BRANCH` is
`production`, and the branch exists), and her domain is `lenas-backstube.example`, already
on Cloudflare. Where a scenario does not say otherwise, the project's `pages.dev` address
is `lenas-backstube.pages.dev`, and a yes is a second run with the code.

| # | Given | When | Then | Test |
|---|-------|------|------|------|
| | **The `project` stage** | | | |
| 1 | Lena has made the token and authorized the GitHub app; no project exists | the stage runs, and runs again with the code | the first run ends with status 3 and has sent no write call; after the second, the project `lenas-backstube` exists with production branch `production`, build command `npm run build`, output `dist`, Fail open on, and a build of `production` was started or found; her domain was never requested | stub API: no write before the code; the create call carries these values; the stub site records no request |
| 2 | the first build is not done within the run | the stage runs with the code, and again with the same code | the first of these ends with status 4; the second carries on and sends no second create call | stub: a build that finishes between the two runs |
| 3 | a project connected to her repository exists with production branch `main`, and no domain is attached | the stage runs | its list holds the line "Your live address would publish `main`, the preview. I will set the production branch to `production`" | stub API returns such a project; the first write after the code is the branch change |
| 4 | the same project, but her domain is attached to it | the stage runs | it stops with status 1 and writes nothing: it says what her domain serves now, that the script does not repair a site that is live, and gives the checklist's path for changing the branch | stub API returns the project with a domain; no write call |
| 5 | `PROD_BRANCH` is `production` and `origin` has no `production` branch | the stage runs | it stops with status 1, says the two signs disagree, and says what each model needs: for two-stage, the assistant creates the branch from the reviewed `main` on the owner's word (D6); for single-stage, `PROD_BRANCH` becomes `main` | fixture repository without the branch; no write call |
| 6 | a project named `lenas-backstube` exists and has no `source` | the stage runs | it stops: "this is a Direct Upload project; Cloudflare cannot connect it to GitHub", and points to `website-team-setup` §6, item 9 | stub API returns such a project; no write call |
| 7 | Lena made a project by hand under another name, connected to her repository; or two projects name her repository; or `--project` names one connected to another repository | the stage runs | in the first case it adopts that project and creates none; in the other two it stops and writes nothing | three stub states |
| 8 | the adopted project has one variable and one secret, and Fail open is off | the stage runs with the code | Fail open is on and both names are still there on the read-back; if the spike found no request that keeps a secret, the line reads "by hand" and no write is sent | stub API with a variable and a secret; both endings |
| 9 | the project is set up; Cloudflare cannot reach the repository; the assistant has pushed a commit to a pull request | the stage runs, several times | each run ends with status 4, asks for a push, and names both likely causes and how to tell them apart; none says the connection works | stub: the commit never appears among the deployments |
| 10 | the newest preview deployment is a day old; or it is fresh and failed; or it is fresh and was uploaded | the stage runs | none of the three counts as proof; the failed one is reported as "Cloudflare started a build of this commit and it failed" | three stub deployments |
| 11 | the project builds no previews | the stage runs | it says that the connection cannot be shown this way, and how to look for Cloudflare's check on a pull request by hand | stub: previews off |
| | **The `domain` stage** | | | |
| 12 | at the head of `production`, `UNFILLED_UNTIL_LAUNCH` still lists `/privacy` | the stage runs | it refuses, names the list and its entries, and asks no question | fixture repository with the starter's list; no domain call |
| 13 | the list is empty, and a page under `src/` holds `[MISSING: opening hours]` | the stage runs | it refuses and names the file and the line | fixture repository with the marker |
| 14 | a German site whose `DRAFT_TOKEN` and CI search are both `[FEHLT:`, with `[FEHLT: Öffnungszeiten]` in a page | the stage runs | it refuses the same way, and the search it reports is for `[FEHLT:` | fixture repository with that token |
| 15 | the site has no `tests/placeholders.spec.ts`; or its `DRAFT_TOKEN` is `[FEHLT:` while its CI search is for `[MISSING:` | the stage runs | it refuses: it cannot tell whether the site is ready, and says the domain can be attached by hand | two fixture repositories |
| 16 | the `project` stage still has a change to make; or there is no proof of the connection in the last 60 minutes; or the newest production deployment is of an older commit, failed, or was uploaded | the stage runs | it refuses and names which; for the older commit it says how to publish, and what `npm run ship` will report while no domain is attached | one stub state for each |
| 17 | all conditions hold; her apex has one A record, at her old host | the stage runs; Lena reads the question; it runs with the code, and again with the same code | the question named the commit, the proof, the record and what it becomes, and the forwarding; the first run with the code changes the record, attaches the domain and ends with status 4; the next sends no second attach call, finds the domain active, runs the check script as its first request to the domain, and says "live" | stub: status pending, then active; the stub site records when the first request comes |
| 18 | her apex has two A records; or the token cannot read DNS records | the stage runs | it refuses: the script will not attach a domain whose records it cannot see or would have to sort out, and points to "Going live" | two stub states; no domain call |
| 19 | the same as 17, but Cloudflare answers `error` | the stage runs with the code | exit status 1 with Cloudflare's own words; the domain stays attached; script step 7 is not done; a later run takes up there | stub: status `error` |
| 20 | the same as 17, but the domain turns out to serve another commit than the question named | the stage reaches the check | it reports that as a failure and does not go on to script step 7 | stub site whose `build.txt` differs |
| 21 | the domain is active and serves the head of `production`; the project has one other variable and one secret | the stage carries on with script step 7 | both other names are there on the read-back, a production deployment was started, and once it is done the check script's `canonical` item is `ok` | stub API with a variable and a secret; a local stub site for the 301 |
| 22 | the same, but the head of `production` is newer than the live build; or a second variable was saved since the live build; or the live build was uploaded; or the deployment the script starts never appears | the stage carries on with script step 7 | it says "the variable is saved, but no build has picked it up", with the other difference by name, and ends with status 1; in the first three cases it sends no deployment call | four stub states |
| 23 | Lena does not want the forwarding | the stage runs with `--skip canonical` | the question does not name the forwarding, and `CANONICAL_URL` is not written | stub API: no variable write |
| | **The `settings` stage** | | | |
| 24 | her domain is not attached, or not active | the stage runs | it refuses and sends no write call and no request to the domain | stub: no domain; a pending domain |
| 25 | her zone also has a proxied host `shop.lenas-backstube.example` | the stage runs, then runs with `--skip tls`, then with that run's code | every line of the list names that host and what changes there; with `--skip tls` the TLS line is gone and the code is another; after the code each remaining setting reads as wanted through the API, and TLS was not written | stub API with the second host |
| 26 | the NEL switch reads off and the stub site still sends the headers | the stage runs with the code | the rule is added and the ruleset's two existing rules are still there; with `--skip nel-rule` no rule is written and `nel` is reported as a failure, status 1 | stub API holding a ruleset with two rules |
| 27 | the token reads zone settings but may not change them | the stage runs with the code | each refused setting is "by hand" in the report with the permission row it needs; the other lines ran | stub: 403 on the setting's write |
| 28 | the token cannot read DNS records | the stage runs | the list says the other hosts could not be read, and the DNS records as skipped | stub: the DNS read is refused |
| 29 | Lena gives the Bing record with name and content the wrong way round | the stage runs | it sees that the name ends in a verification host the kit knows (`verify.bing.com`), or that a CNAME's target has no dot, says the two look swapped, and puts no such line in the list | unit test on the record check, with a record in the form Bing issues it (captured in the spike, code removed) |
| 30 | her domain has an SPF record, a TXT at the apex | the stage writes Google's TXT record at the apex | Google's record is added, the SPF record is listed and untouched | stub API holding the SPF record; the write is a create, never an update |
| 31 | a CNAME of the wanted name exists with another target | the stage is to write hers | it writes nothing and reports the line as "by hand", with both targets | stub API holding the other record |
| 32 | the record is written, and the nameservers do not show it within the run | the stage reports | the line reads "read back through the API only" | a stub resolver that answers "no such name" |
| | **Every stage** | | | |
| 33 | the token has no end date; or the zone list shows more zones than hers | any stage runs | it refuses before any write call, says which, and asks for a narrower token | stub: no `expires_on`; a zone list with two zones |
| 34 | the token is in `.dev.vars`, and git tracks that file; or git neither tracks nor ignores it | any stage runs | it stops before reading the file and says how to ignore it | two fixture repositories |
| 35 | Cloudflare gave the project the address `lenas-backstube-9x2.pages.dev` | the stages check and report | every check and every line of the report uses that address; `lenas-backstube.pages.dev` is requested nowhere | stub API whose `subdomain` differs from the name; the stub site records the hosts requested |
| 36 | all three stages are done on Lena's two-stage site | the `settings` stage reports | the report names `lenas-backstube.example` as live, gives the alias of `main` it read from the newest preview deployment of `main` and opened, says that `lenas-backstube.pages.dev` forwards to the live address, marks Minimum TLS Version, the AI crawler policies and Fail open as "read back through the API only", lists Crawler Hints, the Web Analytics switch and HSTS, with a date, as left for Lena, and says that previews can be put behind a sign-in | snapshot of the report |
| 37 | a single-stage site (`PROD_BRANCH` is `main`, no `production` branch) | a stage reports | the report names no preview of `main`; it says that `main` is the live site and that each pull request gets its own preview address | snapshot of the report |
| 38 | all three stages ran last month | each runs again | none makes a write call or asks a question; the `project` stage asks for no push and says what the newest production deployment shows about the connection and what it does not | stub API holding the end state |

The tests run the script as a program against a stub of Cloudflare's API, small sites and
a resolver on `127.0.0.1`, and fixture repositories as `origin`, the way `make
test-cloudflare-check` tests the check script. They are wired into the same CI workflow
(`.github/workflows/clean.yml`). The stub's answers are the ones captured in the spike.
Before a captured answer is committed, every name, id and address in it is replaced by
the scenarios' made-up ones: the token, the account's and zone's ids, the zone's name and
nameservers, the GitHub owner and repository, the project and its `pages.dev` address,
and commit messages.

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

**Seen in the spike, 2026-10-13** (the two observations that need no token; git 2.33.0
and Node 26.11.1 on the maintainer's Mac, not Node 18):

- `git ls-remote`, run with its input closed, returned in every case tried and never
  waited for an answer: an unknown host failed at once, a repository that does not exist
  failed after 24 seconds, and a normal remote answered in 0.6 seconds. So one such call
  can use a large part of a 60-second run.
- A remote's address is not always `https://github.com/<owner>/<repository>`. On that Mac
  one remote carries a user name before the host, and a global git setting rewrites
  GitHub addresses to SSH. The script has to read owner and repository from each of these
  forms, and must not print a remote's address as it is, because that part of an address
  can hold a credential.
- Node's resolver, set to `127.0.0.1` and a port, asked a stand-in DNS server on this
  machine and returned its TXT record. So the tests can replace the resolver (spike
  observation 10, second half).

**Seen in the spike, 2026-10-13, read-only calls** with a token limited to one zone and one
account, on the zone and the live project the maintainer named. Captures 001 to 027, kept
outside every repository.

- **Testing a token.** For a token with no end date the answer holds `id` and `status`
  and no `expires_on`. After the maintainer set a date, the same call returned
  `expires_on` and `not_before`. So the script can tell the two apart (spike
  observation 8).
- **A refused read does not say which permission is missing.** The token had no DNS row.
  Listing DNS records answered 403 with code 10000, "Authentication error", and nothing
  else. A read of an area the token has no row for can also succeed: listing Workers
  scripts answered 200 with an empty list.
- **The `permissions` list on a zone is not the token's.** Both the list of zones and a
  zone's own record carry `permissions`, and here it named `#dns_records:read` and
  `#dns_records:edit` while the DNS read was refused. The script must not read a token's
  reach from it. What a token may do is learned by trying, as script step 1 says.
- **The list of zones shows a token's reach in zones.** It returned one zone, the one the
  token was limited to.
- **What a project and a deployment record** (the live project, 128 deployments):
  - A project has `subdomain` and `domains`, and here its `name` is not the first part
    of its `subdomain`. `domains` holds the `pages.dev` address too.
  - A deployment records `deployment_trigger.type`, the branch and commit it was built
    from, `environment`, the project's `production_branch` at that time, its own
    `env_vars` and `build_config`, `aliases`, `url`, `latest_stage` and `is_skipped`.
    So a deployment's variables and build settings can be compared with the project's
    saved ones, and a production build made while another branch was the production
    branch can be told (spike observation 4, the reading half).
  - A build Cloudflare started from a push has the trigger type `github:push`. The
    upload of 2026-10-12 and two deployments started by hand that day have `ad_hoc`.
    `source.type` is `github` on all of them, so it does not tell them apart. Whether
    a deployment started through the API also reads `ad_hoc` is not yet seen.
  - The preview of `main` carries its alias in `aliases`
    (`https://main.<subdomain>`); the newest production deployment carries the live
    domain there. A failed deployment has the stage `deploy` with status `failure` and
    no alias.
- **Zone settings answer with `value`, `editable` and `modified_on`.** `modified_on` was
  empty for two settings that had never been changed. The NEL setting's value is an
  object, `{"enabled": false}`; the others read are strings.
- **A setting can read "on" and show nothing from outside.** Email Address Obfuscation
  read `on` through the API on a site whose pages hold no plain address, and the check
  script found no trace of it in the page. The outside check cannot stand in for the
  read-back there, and the read-back cannot stand in for the outside check on NEL
  (decision 3 keeps both).

**Seen in the spike, 2026-10-13, calls on the throwaway project** (captures 027 to 062; the
maintainer gave one go-ahead for the list of them):

- **A project created through the API builds from GitHub** (spike observation 1). The
  create call carried a `source` with the owner's and the repository's names, after the
  maintainer had given Cloudflare's GitHub app access to that repository. Cloudflare
  filled in the repository's ids itself. A commit pushed afterwards had a preview build
  one second later, with the trigger type `github:push`, and the pull request showed
  Cloudflare's check. "Connect to Git" in the dashboard was not needed.
- **Creating a project starts no build** (observation 2). None was listed 38 seconds
  later. The deployment call with an empty form then built the head of the production
  branch as a production deployment. Its trigger type is `ad_hoc`.
- **A second deployment call starts a second build** (observation 3). Sent while the
  first was queued, it was accepted, and both ran to the end. So the script has to look
  for a build that is queued or running before it starts one.
- **A build and an upload are both `ad_hoc`, and their stages tell them apart**
  (observation 4). A deployment Cloudflare built has the stages `clone_repo` and `build`
  with status `success`. The two uploads on the live project have them `idle`.
- **A change to one setting keeps the rest** (observation 5). Each of these went as the
  smallest request, a PATCH of the project holding only what changes: adding a secret,
  changing a plain variable, a build setting, the production branch, Fail open. After
  each, the other variables were still listed. A secret's value never comes back. The
  test function gave the same hash of the secret after all changes, on the production
  address and on a preview.
- **Fail open has to be the same for production and preview.** A request for one alone
  answered 400, code 8000066.
- **A change of the production branch changes nothing that is served** until the next
  build. The project kept naming the old production build as its newest, and the
  `pages.dev` address kept serving it. The next deployment call built the new branch.
  A deployment records which branch was the production branch at its time.
- **A variable reaches only deployments made after it.** After the changes and before a
  new build, the function still answered with the old values.
- **A branch's preview address** replaces the slash in `trial/first-pr` by a dash, and
  moves to the branch's newest deployment: the older one lost its entry in `aliases`.
- **A deployment does not record Fail open.** So whether a change reaches the build that
  is live cannot be read from it (observation 6 stays open).
- A build took about two and a half minutes the first time and under 90 seconds after.

**Seen in the spike, 2026-10-13, the settings, the domain and the pull requests** (captures
063 to 103; the maintainer's go-ahead: "do all items in a row, just check everything"):

- **The settings calls work with the checklist's token rows** (observation 9). On the
  live zone each of four settings was read, written to the checklist's value with a
  PATCH of `{"value": …}`, and read back: Always Use HTTPS, Minimum TLS Version and NEL
  were already right; Email Address Obfuscation went from `on` to `off`. Writing a value
  that is already there is accepted. It left `modified_on` as it was for Always Use
  HTTPS and moved it for NEL, so `modified_on` does not show whether anything changed.
- **Bot Management.** Bot Fight Mode is `fight_mode`, a true or false. The AI crawler
  policies are `ai_bots_protection`, `ai_training`, `ai_search` and `ai_user`; the value
  `disabled` means nothing is blocked. The zone's own values, sent back whole with PUT,
  were accepted and changed nothing. Whether PUT with only some fields keeps the others
  was not tried: the only zone at hand was live.
- **The header rule.** The ruleset of the phase `http_response_headers_transform`, read
  and sent back with PUT with the same one rule, kept the rule, its id and its version.
- **Attaching a domain creates no DNS record** (observation 7, first case). The call
  answered `initializing`, then stayed `pending` with the verification message "CNAME
  record not set". The host had no record before and none a minute after, and it
  answered an error. So the script has to write the host's record itself, and the token
  needs the DNS row for the domain step, as "What the owner does" says. The cases with
  an existing record, and both orders, are not tried yet: the token had no DNS row.
- **A pull request and the connection** (observation 11). GitHub opened a pull request
  for a branch whose one commit is empty, and Cloudflare built it. A second project,
  connected to the same repository later, built nothing for a pull request that was
  already open; it built that pull request's next commit. With two projects on one
  repository, each puts its own check on a pull request, named after the project.

**Seen in the spike, 2026-10-13, the DNS calls** (captures 104 to 147, after the maintainer
added the DNS row to the token):

- **The script writes the domain's record, and the domain then turns active**
  (observation 7). With the domain attached and pending, a proxied CNAME from the host
  to the project's `pages.dev` address was created. The verification turned `active`
  after about a minute and the domain after two and a half. The host then served the
  production build.
- **An existing record is left alone by the attach call, and one update turns it into
  the needed one.** A host with an A record elsewhere was attached: Cloudflare kept the
  record and reported "CNAME record not set". One PATCH of that record, to type CNAME
  with the project's address, was accepted and kept the record's id. No delete was
  needed. The domain was active two minutes later. Both orders work: attach first, or
  record first.
- **A computer that asked for the host before its record existed can go on getting "no
  such host"** for a while. Here plain requests from the Mac failed for minutes after
  the domain was active, while a request sent to the address the nameserver gave
  succeeded. The script's first request to a new domain has to allow for that.
- **TXT records** (observation 10). A second TXT at a name that has one was accepted and
  both were served. The zone's nameserver showed a new record within four seconds. The
  same TXT sent a second time was refused with code 81058, "An identical record already
  exists", so a second run cannot double a record. A CNAME at a name that has one was
  refused with code 81053.
- **Node's resolver, set to the nameserver's address,** returned both TXT records.
- **Bing's record** (observation 8) is in the zone since the launch: a CNAME whose name
  is a code of 32 hexadecimal characters and whose target is `verify.bing.com`, DNS
  only. The swapped entry of the launch day had `verify.bing.com` as its name, which is
  what scenario 29's rule looks for.

**Removed on 2026-10-14, on the maintainer's word:** the two throwaway Pages projects, with
their hosts, and the four DNS records; the zone has its 14 earlier records again and the
account its four earlier projects. Left for the maintainer: the private repository
the private throwaway repository (the GitHub sign-in the assistant uses may not delete a
repository), the local folder of the trial, which holds the token in `.dev.vars`, and the
token itself.

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
   script adopts the project (scenario 7).
2. Whether creating a connected project starts a first production build by itself, and
   whether the deployment call above, sent without a branch to a connected project, builds
   the head of the production branch (script steps 4 and 7).
3. What attaching a domain does to DNS: whether it creates or changes the host's record
   or the script must; whether a domain becomes active while its record still points
   elsewhere; and what the domain serves until it is active (script step 6).
4. What read calls show about a token: whether a refused read names the missing
   permission, and whether listing zones shows that a token reaches more than one
   (scenario 33).
5. Which request changes one setting of an existing project (a variable, Fail open, the
   production branch, a build setting) and keeps its other variables, secrets included,
   in both environments (script steps 3 and 7).
6. What a deployment records: whether its variables and build settings can be compared
   with the project's saved ones; how a deployment Cloudflare started from a push differs
   from one started through the API or by an upload; and whether a change to Fail open
   reaches the deployment that is live or only later ones (script steps 3, 5 and 7).
7. Whether Cloudflare builds a preview for a new commit on a pull request that was opened
   before the project was connected, and whether GitHub opens a pull request for a branch
   whose one commit is empty (script step 5, D7).
8. The exact record Bing issues for CNAME verification (scenario 29).

Whatever the spike answers differently from what a script step or a scenario assumes,
that step and that scenario are rewritten before plan step 5, and this file says which.

The settings of script step 8, their permission rows and their cautions are the
checklist's, with that file's own sources. The checklist says that of those calls only the
Transform Rules call has been run on live sites.

## The spike

Plan step 4. It answers the eight questions above and makes the observations round 3 of
the PLAN gate asked for, on a throwaway repository and a throwaway Pages project. No
script exists yet, so the assistant makes each call by hand, and guardrail 4 of
`CLOUDFLARE_FIRST_DEPLOY.md` holds as written: every call that changes something is shown
to the owner first and made on the owner's go-ahead.

**What it needs from the owner.**

- A domain on Cloudflare to try on. The zone-wide settings are written to it, so it is a
  spare domain, or a live one whose owner wants the checklist's values anyway. On a live
  domain every setting is read first and written only to the checklist's value, and the
  domain step uses a host of its own (`spike.` and the domain), never the apex or `www`.
- One token with the rows of the checklist's section 6 and Zone → DNS → Edit, limited to
  that domain and that account, ending in two or three days. It goes into a file git
  ignores, never into a chat.
- Cloudflare's GitHub app authorized for the throwaway repository.
- For question 8: the record Bing shows for CNAME verification, with the code removed.

**What is kept.** Each request and each answer, in a folder outside every repository.
Nothing is committed until every name, id and address in it is replaced as the paragraph
under the scenario table lists. The token is never written into a capture.

**What it observes.**

| # | Question | The observation that settles it |
|---|----------|--------------------------------|
| 1 | "Not verified" 1: does a project created with a `source` object build from GitHub? | Create it through the API with the app authorized; push a commit; read the list of deployments |
| 2 | "Not verified" 2: first build on creation; the deployment call without a branch | The list of deployments right after creation; then the call, and which commit and branch the new deployment records |
| 3 | H7: what a rerun meets | A second deployment call while the first is still building: the answer, and how the pending one is listed |
| 4 | "Not verified" 6, H9: what a deployment records | One deployment each from a push, the API call and an upload: trigger, branch, commit, variables, build settings, `aliases`. Then change the production branch and read the same fields and `build.txt` on the `pages.dev` address before and after |
| 5 | "Not verified" 5, H11: does a change to one setting keep the rest? | A project holding a plain variable and a secret, and a Function that answers with a hash of the secret. Change a variable, Fail open, the branch and a build setting, each with the smallest body; after each, read the variables by name and value and ask the Function |
| 6 | "Not verified" 6: when does Fail open apply? | Read it on the live deployment before and after the change, and after a new build |
| 7 | "Not verified" 3, H10: the domain and its record | Attach `spike.` and the domain with no record, with a CNAME elsewhere, and with an A record elsewhere: what Cloudflare creates or changes, the statuses over time, and what the host answers at each point. Whether one update call turns an A record into the record Pages needs. Both orders: record first, attach first |
| 8 | "Not verified" 4: what a token shows | The test call for a token with and without an end date; a read the token has no row for; the list of zones |
| 9 | Script step 8: the settings calls | For each of the six settings and the NEL rule: read, write the checklist's value, read back, and the time of the last change if the answer has one |
| 10 | Script step 9, H-follow-ups on DNS | Create a TXT beside an existing TXT at one name; time until the zone's nameservers show it; a lookup through Node 18's resolver set to a nameserver's address |
| 11 | "Not verified" 7: pull requests | A new commit on a pull request opened before the project was connected; a pull request whose one commit is empty |
| 12 | A shell without a terminal | `git ls-remote origin` against an unreachable remote and one that needs credentials, with input closed: does it return? |

**Afterwards.** The answers go into "What is known, and how", each with its date and the
capture it rests on. Then this file is rewritten once and gated again. The throwaway
project and repository are deleted by the owner, or by the assistant on the owner's word;
the token is deleted by the owner.

## Decisions taken

1. **The model is route B** (connected to GitHub), by the maintainer, 2026-10-12.
   Previews per pull request and `npm run ship` are worth one authorization in the browser.
2. **The checklist stays the list.** The script takes its settings, their order and their
   cautions from `docs/CLOUDFLARE-CHECKLIST.md`; this plan adds the project and domain
   stages. A test keeps the two in step: item titles and dashboard paths as `make
   test-cloudflare-check` compares them for the check script, and also each value the
   script writes, against the checklist's own words for it (the value in an item's title;
   the three AI policy values and the two header names of the NEL rule in the item's
   text).
3. **Read, say, do, read back, and check from outside where an outside check exists.** A
   setting the check script can see counts as in effect when a request from outside shows
   it, not when the API says so: the checklist records a case where the API reported a
   header off and the site still sent it. For the others the report says "read back
   through the API only".
4. **One check, not two.** Whenever the script needs to know what the live site or the
   `pages.dev` address answers (the build that is live, the forwarding, the NEL headers),
   it runs `cloudflare-check.mjs` and reads that item. It carries no reading of its own
   for what that script covers. What the check script lacks for this is added to it in
   plan step 5, in the first of the two pull requests: a way to run single items, and a
   `canonical` item that asks for a path with a query and checks that both are kept.
5. **A yes is a second run with a code** made from the end state (see "How a yes reaches
   it"). A flag that says yes to whatever the script would do does not exist.
6. **No run waits long** (see "It does not wait long"). What takes Cloudflare minutes is
   met by running the stage again.
7. **The script sets up; it does not repair a live site.** A project that already serves
   a domain with the wrong production branch is left alone (scenario 4).

8. **Open to every AI crawler, not to a list of names** (maintainer, 2026-10-14: "yes to:
   the three switches go into the plan's rewrite and into the checklist"). Besides the
   three AI crawler policies (`ai_search`, `ai_user`, `ai_training`) and the rule
   `ai_bots_protection`, the settings stage turns off three more switches that can keep
   AI crawlers out, which the spike read on the live zone: the link maze for AI scrapers
   (`crawler_protection`), the block on content bots (`content_bots_protection`), and
   Cloudflare's managed `robots.txt` (`is_robots_txt_managed`). The checklist names them
   too (plan step 6). Training crawlers are let in by default as well: the maintainer
   weighed it (2026-10-14: "Add it to training. I think the upside is bigger, than the
   contrary"). An owner who decides otherwise leaves the line out with `--skip ai`, since
   the checklist calls it the owner's choice. What
   "disabled" does in each of these fields is read from Cloudflare's field descriptions,
   not yet seen in a test.

## Decisions D1 to D7

Closed by the maintainer. The argument against each stays here as the record of what was
weighed.

- **D1. One yes or many.** *Decided first (2026-10-12):* one yes for the whole list, a
  second for the domain. *Changed (2026-10-13):* three stages and a yes for each. The
  reason given for it, that the settings can only be applied once the domain serves the
  site, was false (H3 in the trail): the checklist makes only HSTS and the forwarding
  wait. *Changed back the same day:* two yeses, one for the project and the settings on
  setup day, a second for the domain. "Shape" and the scenarios below still show three
  stages; the rewrite after the spike brings them in line. *Rests on:* "the owner should not have
  to do anything". *Against:* guardrail 4 in `CLOUDFLARE_FIRST_DEPLOY.md` asks for a yes
  before each change to the account; a yes to a list is weaker, and the list must be read
  carefully to be worth it. The settings stage changes the whole domain; its list says so
  on every line, names the other hosts, and each line can be left out with `--skip`. Plan
  step 6 rewrites that guardrail for the script: a stage's printed question, confirmed
  with its code, is the confirmation for the changes it names, and for nothing else.
- **D2. What it is written in.** *Decided first:* Node, as one file in the site template.
  *Changed the same day, with D3:* Node, as one file in the kit with nothing from npm,
  like the check script. *Against:* most of the kit's own scripts are bash or Python.
- **D3. Where it lives.** *Decided first:* in the site template. *Changed the same day:*
  in the kit, in the `new-website` skill beside the check script, run in the site's
  folder. The check script was merged there after the first decision; a script in the kit
  can call it, and is the installed kit's version instead of a copy that ages in each
  site. *Against:* a site whose owner has no kit installed cannot run it; such an owner
  follows route B by hand.
- **D4. Project steps only, or the checklist's settings too.** *Decided:* both, in the
  same script; the settings are its third stage. *Against:* the settings touch the whole
  domain, not only this site, and two of them are judgment calls the checklist explains
  at length.
- **D5. Previews behind a login.** Cloudflare can ask for a sign-in before a preview opens
  (project → Settings → General → Enable access policy; this path is the maintainer's
  note, no kit file has it). *Decided:* leave it out of the first version and name the
  option in the report, without the path. *Against:* previews are public to anyone who
  has the address, and an owner asked for hidden ones on the first day.
- **D6. Creating the `production` branch.** *Decided:* the script asks the assistant,
  which does it on the owner's word (scenario 5). *Against:* one more stop in a flow meant
  to have none.
- **D7. The first build to prove the connection.** *Decided:* Cloudflare's own build of a
  commit pushed to a real pull request (scenarios 9 to 11). *Against:* a new site may
  have no open pull request; the assistant then opens one for the purpose, which is noise
  in the history.

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
- `docs/CLOUDFLARE-CHECKLIST.md`: section 6, whose table of permission rows has no row for
  DNS, and section 5's "your Pages project's name (the first part of its `.pages.dev`
  address)".
- `CLOUDFLARE_CHECK.md` and the check script's own messages: "By hand, always", the new
  way to run single items, and the places that take `<name>.pages.dev` for the project's
  address.
- `search-console-setup`, which calls the DNS record a human action.

## Review trail

`docs/reviews/REVIEW-plan-2026-10-12-pr265.md`: the PLAN gate, at High depth because the
script this plan describes changes a Cloudflare account with a token and can make a site
public.
