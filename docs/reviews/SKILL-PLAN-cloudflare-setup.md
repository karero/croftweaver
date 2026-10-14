# Plan: Cloudflare setup by one token, for a site connected to GitHub

Requirements record for a script that does not exist yet,
`skills/new-website/scripts/cloudflare-setup.mjs`. Where this plan and the shipped files
disagree, the files win until plan step 6 changes them. Names of sites and people stay out
of this public repo on purpose; the business in the scenarios is made up.

This is the second version. The first went through a PLAN gate that stopped after three
rounds without converging (`docs/reviews/REVIEW-plan-2026-10-12-pr265.md`); then a trial
run on a throwaway project answered the questions that gate had left open. This text is
written once from that trial, with two yeses (D1), and passed a new PLAN gate on 2026-10-14
(trail under "Review trail"). What no one has tried yet is listed under "Not verified"; plan
step 9 tries the untried Cloudflare calls before the real site of plan step 10.

Two series of steps run through this file. **Plan steps** are the rows of the status
table. **Script steps** are what the script does, numbered under "Shape".

## Status, 2026-10-14 · the kit's files read at origin/main `de64ec8`

| # | Plan step | State | Evidence |
|---|-----------|-------|----------|
| 1 | Requirements and scenarios (this file) | ✅ rewritten from the trial on 2026-10-14; PLAN gate (High) clean the same day, after six rounds, a final full read and a wording pass | this file; trail: `docs/reviews/REVIEW-plan-2026-10-14-pr303.md`. First version and its gate: karero/croftweaver#265 (`b5bf49e`), `docs/reviews/REVIEW-plan-2026-10-12-pr265.md` |
| 2 | The Cloudflare checklist and its check script reach `main` | ✅ merged 2026-10-12 | karero/croftweaver#266 (`7642954`); karero/croftweaver#267 (`d382cbe`) |
| 3 | The maintainer closes the decisions | ✅ D1 to D7 on 2026-10-12, D1 final on 2026-10-13, decision 8 on 2026-10-14 | sections "Decisions taken" and "Decisions D1 to D7" |
| 4 | Trial run on a throwaway repository and project | ✅ 2026-10-13, apart from two points (see "Not verified", 1 and 2) | 159 captures, kept outside every repository; the private throwaway repository |
| 5 | The checklist names the three more AI switches of decision 8 | ✅ merged 2026-10-14 (another session's work) | karero/croftweaver#285 (`321d26f`) |
| 6 | The script and its tests against a stub of Cloudflare's API, in two pull requests: the `setup` stage, then the `launch` stage with what the check script needs for it | ⏸ not started | — |
| 7 | The kit's files that say otherwise today change with the script (list under "Hooks") | ⏸ not started | — |
| 8 | Review gate on the script (High: it changes an account with a token, and it can make a site public) | ⏸ not started | — |
| 9 | A second trial on a spare domain: the apex, a Bot Management PUT that changes values, a record PATCH with a comment, adding one rule to a ruleset and creating one, a project with previews off, a long record comment, the accounts list, and which dashboard switch `is_robots_txt_managed` is ("Not verified" 2, 3, 5, 9, 10) | ✅ done 2026-10-14; the first domain named turned out to be in use, so most steps ran on a second, empty one. Results under "Seen in the second trial"; cleaned up on the maintainer's word | 78 captures (T2-001 to T2-078), kept outside every repository; the checklist's field fix: karero/croftweaver#319 |
| 10 | One real site set up with it, start to finish, with the owner watching | ⏸ not started | — |
| 11 | Release note line | ⏸ not started | — |

Legend: ✅ done · ▶ in progress · ⏸ not started or blocked · ⚠ deviated

## Why

Putting a new site on Cloudflare is where an owner who has never seen the dashboard loses
the most time, and where a wrong click does the most harm. The kit has three routes today
(`skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md`): A, by token, gives a Direct
Upload project that Cloudflare does not build from GitHub; B, connected to GitHub, builds
on every push but leaves the owner alone in the dashboard; C, the assistant drives the
browser, is slow. The maintainer's decision (2026-10-12): route B's result, with as much of
route A's ease as Cloudflare's API allows.

One site launched by hand on route B on 2026-10-12. Six things went wrong that day, and
each has a scenario below:

1. The project was made with production branch `main` on a two-stage site, so Cloudflare
   put `main` on the live domain at once, with unfilled legal pages, open to search
   engines. (Scenarios 4, 19, 21.)
2. The project lost its connection to GitHub; pushes built nothing, and the only sign was
   a banner in the dashboard. (Scenarios 10, 22.)
3. "Create deployment" did nothing while the connection was broken. (Scenario 22.)
4. A variable was typed and not saved; later it was saved, but no build followed, so it
   had no effect. (Scenarios 28, 29.)
5. The owner took the project's own `pages.dev` address for the preview. It is the live
   build's second address. (Scenarios 35, 36.)
6. A search engine's verification record went in with name and target swapped.
   (Scenario 15.)

## Requirements

R1. **One token at a time, two yeses.** The owner makes a short-lived token and says yes twice: on
setup day to a list of project changes, Cloudflare settings and DNS records; on launch day
to attaching the domain. Nothing in the account changes without one of these yeses, and a
yes covers only the list it answered.

R2. **Nothing public before the second yes.** Until then the site answers only at the
project's `pages.dev` addresses. The domain is not attached, and the script sends it no
request.

R3. **No launch while the site is unfinished.** The script never makes a site public on its
own: when it attaches the domain, the second yes is not even asked while
legal pages are unfilled, a draft marker is left, or the build that would go live is not
the head of the production branch built by Cloudflare.

R4. **The site is shown to be connected to GitHub.** A push builds. The script shows this
with a build that Cloudflare started from a push, never with one it started itself. That
shows the connection worked when that build ran; no read shows it works today (see
"Judgment calls").

R5. **Zone-wide is said out loud.** Every Cloudflare setting changes the whole domain.
Each line of the list says so and names the zone's other hosts.

R6. **In effect means seen.** A setting counts as in effect when a request from outside
shows it. Where no outside check exists, the report says "read back through the API only".

R7. **Nothing is destroyed.** The script deletes nothing. The one existing DNS record it
may change is the host's own address record, inside the second yes. It does not repair a
site that is live (decision 7).

R8. **Safe to run again.** Each write is one call. A run cut off between two writes leaves
a state the next run with the same code reads and carries on from (scenario 39). A run on
a finished setup changes nothing and asks nothing.

R9. **It fits an assistant's shell.** No run waits for typed input, and none takes longer
than 60 seconds: the run has one deadline, and every call and program it starts gets only
the time left.

R10. **The token stays secret.** It is never printed, stored, passed to another program, or
sent anywhere but Cloudflare's API.

R11. **Open to AI crawlers by default** (decision 8). The owner can leave that line out.

R12. **The checklist stays the one list.** The settings, their values and their cautions
are `docs/CLOUDFLARE-CHECKLIST.md`'s.

## Scenarios

The owner is Lena. Her site is `lenas-backstube` on GitHub, two-stage (`PROD_BRANCH` is
`production`, and the branch exists), and her domain `lenas-backstube.example` is already
on Cloudflare. Unless a row says otherwise, the project's `pages.dev` address is
`lenas-backstube.pages.dev`, and "with the code" means the run after Lena's yes.

| # | Given | When | Then | Test |
|---|-------|------|------|------|
| | **`setup`** | | | |
| 1 | Lena made the token and gave Cloudflare's GitHub app her repository; no project exists | `setup` runs, then runs with the code | the first run sends no write and ends with 3. The second creates `lenas-backstube` (branch `production`, `npm run build`, `dist`, Fail open on in both environments), starts one build of `production`, writes the settings, and ends with 4: it waits for that build and for a push | stub API: no write before the code; the create call's body; the stub site records no request to her domain |
| 2 | the build has finished, and the assistant pushed a commit to a pull request, which Cloudflare built | `setup` runs again with the same code | no second create and no second build; it reports the push build and ends with 0 | stub: a `github:push` preview deployment |
| 3 | the build is still queued | `setup` runs again with the code | it sends no deployment call and ends with 4 | stub: one queued production deployment |
| 4 | a project connected to her repository has production branch `main` and no domain | `setup` runs | the list says "your live address would publish `main`, the preview; I will set the production branch to `production`" | stub project; the first write after the code is that PATCH |
| 5 | the same project, but her domain, or another custom domain, is attached to it | `setup` runs | it ends with 1 and writes nothing: the site is live, the script does not repair it, and the checklist's section 1 says how to change the branch | stub project with her domain; with another domain; no write call |
| 6 | `PROD_BRANCH` is `production` and `origin` has no `production` branch | `setup` runs | it ends with 1: the two signs disagree. For two-stage the assistant creates the branch from the reviewed `main` on Lena's word (D6); for single-stage `PROD_BRANCH` becomes `main` | fixture repository; no write call |
| 7 | a project of that name exists with no `source` | `setup` runs | it ends with 1: a Direct Upload project cannot be connected to GitHub; `website-team-setup` §6, item 9, has the way round | stub; no write call |
| 8 | Lena made a project by hand under another name, connected to her repository; or two projects name it; or `--project` names one connected elsewhere; or `--project` names none that exists | `setup` runs | it adopts the first and creates nothing; it stops on the second and third; for the fourth its list says it will create a project of that name | four stub states |
| 9 | the adopted project has a variable and a secret, and Fail open is off | `setup` runs with the code | one PATCH carries Fail open for both environments and no variable; both names are there before and after | stub; the PATCH body |
| 10 | the project has never had a build Cloudflare started from a push; the assistant has pushed | `setup` runs, several times | each run ends with 4, asks for a push, and names the likely causes and how to tell them apart; a failed push build is reported as "Cloudflare started a build of this commit and it failed" | stub: no `github:push` deployment; then one with `failure` |
| 11 | the project may not build previews (`source.config.preview_deployment_setting` is not `all`) | `setup` runs | it says a pull request may not show the connection, and that the production branch's push can: on her two-stage site, `npm run ship` on her word | stub: previews off |
| 12 | her zone has a second proxied host, `shop.lenas-backstube.example`, and her apex still points, proxied, at her old host | `setup` runs, then with `--skip tls`, then with that run's code | every setting line names both hosts and what changes for a visitor there; `--skip tls` drops the TLS line and gives another code; after the code each other setting reads as wanted, and TLS was not written | stub with both hosts |
| 13 | Bot Management reads Bot Fight Mode on and AI training blocked | `setup` runs with the code; then a new question with `--skip ai` | the first PUT turns Bot Fight Mode off and every AI field to the checklist's value; with `--skip ai` the AI fields are sent as they were read | stub; the two PUT bodies |
| 14 | the token reads zone settings but may not change them | `setup` runs with the code | each refused setting reads "by hand" with the permission row it needs; the other lines ran; it ends with 1 | stub: 403 on those writes |
| 15 | Lena gives Bing's record with name and target swapped | `setup` runs | it says the two look swapped and puts no such line in the list | unit test with a record in Bing's shape (trial, code removed) |
| 16 | her apex has an SPF record, and Google's TXT record is to go there; on a later run the same TXT exists | `setup` writes it; then runs again | the first run creates it beside the SPF record, which it lists and leaves; the second writes nothing | stub; the write is a create, never an update |
| 17 | a CNAME of the wanted name exists with another target | `setup` is to write hers | it writes nothing and reports the line "by hand", with both targets | stub |
| 18 | the record is written, and the nameservers do not show it within the run | `setup` reports | the line reads "written; the nameservers do not show it yet", status 0 | a stub resolver that answers "no such name" |
| | **`launch`** | | | |
| 19 | at the head of `production`, `UNFILLED_UNTIL_LAUNCH` still lists `/privacy` | `launch` runs | it refuses, names the list's entries, and asks nothing | fixture repository; no call to the domain or the domains API |
| 20 | a page under `src/` holds `[MISSING: opening hours]`; or a German site holds `[FEHLT: Öffnungszeiten]` with `DRAFT_TOKEN` and CI both `[FEHLT:`; or the two tokens differ, or `tests/placeholders.spec.ts` is missing | `launch` runs | it refuses, naming the file and line; for the German site the search it reports is for `[FEHLT:`; in the last case it says it cannot tell, and that the domain can be attached by hand | four fixture repositories |
| 21 | the head of `production` has no good production build (below): its build is queued; or failed; or Cloudflare never built it; or the newest is uploaded, or was built while `main` was the production branch | `launch` runs | queued: it ends with 4. Otherwise it refuses and names which; for "never built" it says Cloudflare did not build this commit, so the connection may be broken, and gives no advice to run `npm run ship` | five stub states |
| 22 | the project has no build Cloudflare started from a push, of any age; or it has an old one, and launch's own forwarding build came after it | `launch` runs | in the first case it refuses: the connection was not shown; in the second the proof stands and launch goes on | two stub states |
| 23 | everything holds; her apex has one A record, at her old host | `launch` runs; Lena reads the question; it runs with the code, and again | the question named the domain, the commit, the record now and what it becomes, a few minutes of errors, the forwarding, and the NEL rule if needed. The first run with the code attaches the domain, changes the record, and ends with 4. A later run finds the domain active, sends its first request to the domain through the check script, sees the commit, and goes on | stub: pending, then active; the stub site records when the first request comes |
| 24 | her apex has an A and an AAAA record; or her site is on `www`, which has an A record and a TXT record; or the token cannot read DNS | `launch` runs | it refuses: it will not attach a domain whose records it cannot see or would have to delete, and points to "Going live" | three stub states; no attach call |
| 25 | the same as 23, but Cloudflare answers `error` on a later run | `launch` runs with the code | it ends with 1 and Cloudflare's words; the domain stays attached; the report gives the old record, read from the comment the script wrote on the record, so it can be put back by hand | stub: `error` on the third run |
| 26 | the domain turns out to serve another commit, or no `build.txt` | `launch` reaches the check | it reports a failure and stops before the forwarding | stub site |
| 27 | the NEL switch reads off, and the domain still sends the headers | `launch` reaches the NEL line | one add-rule call holding only the new rule, the two existing rules untouched; with no ruleset for the phase, one call creates it with the rule; with the kit's rule already there, nothing is added and the run ends with 1; with `--skip nel-rule` no rule is written and `nel` is listed as left to Lena, status 0 | stub ruleset with two rules; none; one holding the kit's rule |
| 28 | the domain serves the head of `production`, built by Cloudflare; the project has one other variable and one secret | `launch` reaches the forwarding | it saves `CANONICAL_URL` alone, starts one production build, ends with 4; a later run finds it done and the check's `canonical` item `ok`, and ends with 0 | stub; a stub site for the 301 |
| 29 | the domain was attached earlier and is active, and the head of `production` is newer than the live build; or another variable changed since the live build; or the live build was uploaded | `launch` reaches the forwarding | it says "the variable is saved, but no build has picked it up", names the other difference, sends no deployment call, and ends with 1 | three stub states |
| 30 | Lena does not want the forwarding | `launch` runs with `--skip canonical` | the question does not name it, and `CANONICAL_URL` is not written | stub: no variable write |
| 31 | the domain was attached by hand and is active | `launch` runs | it checks no launch condition and attaches nothing; its question names only the forwarding and the NEL rule, and the commit it expects the domain to serve: that of the newest production deployment that succeeded; while a newer one is queued or building, it ends with 4 | stub: a live build and a newer queued one |
| 42 | the live build records `CANONICAL_URL` as saved, and the `pages.dev` address still answers 200 | `launch` reaches the forwarding | no PATCH and no deployment call; it says the live build has the variable and the forwarding does not answer, with the checklist's causes, and ends with 1 | stub: deployment `env_vars` holding the variable; a stub site answering 200 |
| 41 | `setup` ran with `--skip bot`, and Bot Fight Mode is on; or it ran without, and someone has since turned Always Use HTTPS off | `launch` runs with `--skip bot`; then the second case without any `--skip` | the `bot` failure is listed as left to Lena, status 0; the `https` failure gives 1 | stub site with the cookie; stub site with no redirect |
| | **Every stage** | | | |
| 32 | both stages ran last month | each runs again | no write call, no question, status 0 | stub holding the end state |
| 33 | the token has no end date; or the zone list shows a second zone; or token verify is refused; or the zone list is refused | any stage runs | it refuses before any write and names the token to make instead: no end date, one with an end date; a second zone, one limited to her zone; verify refused, a new token (the old one may be revoked or not yet valid); zone list refused, one with the Zone → Zone → Read row | stub: no `expires_on`; two zones; a 403 on verify; a 403 on the zone list |
| 34 | the token is in `.dev.vars`, and git tracks that file, or does not ignore it | any stage runs | it stops before reading the file and says how to ignore it | two fixture repositories |
| 35 | Cloudflare gave the project the address `lenas-backstube-9x2.pages.dev` | the stages check and report | every check and line uses that address; `lenas-backstube.pages.dev` is asked nowhere | stub `subdomain`; the stub site records the hosts asked |
| 36 | both stages are done on Lena's two-stage site | `launch` reports | it names the live address, the address of `main`'s newest preview build as Cloudflare lists it, the forwarding, which lines are "read back through the API only", and what is left by hand (Crawler Hints, the Web Analytics switch, HSTS with its earliest day, deleting the token), and that previews can be put behind a sign-in | snapshot of the report |
| 37 | a single-stage site | a stage reports | it names no preview of `main`: `main` is the live site, and each pull request gets its own preview | snapshot |
| 38 | the script runs `git` and the check script | any stage runs | neither child gets the token in its environment | the stub `git` and check script record their environment |
| 39 | a `launch` run with the code is cut off after the attach call and before the record; or the stub API answers slowly | `launch` runs again with the code | the next run finds the domain attached, writes the record and carries on; with the slow stub the run ends with 4 at the deadline, before 60 seconds | stub: a run killed between the two calls; a stub that waits 30 seconds per answer |
| 40 | the token ends in 30 days | any stage runs | it refuses: the checklist says a week at most | stub `expires_on` |

## Shape

### What the owner does

**Before, once:** accounts at GitHub and Cloudflare, and the domain on Cloudflare (bought
there, or moved there as "Going live" in `CLOUDFLARE_FIRST_DEPLOY.md` says). The script
moves no domain.

**For the script,** none of it in a terminal:

1. Makes a short-lived token from the rows the assistant shows: the checklist's section 6,
   plus Zone → DNS → Edit (the launch stage writes the host's record; the trial showed
   Cloudflare does not, captures 085 to 091). One token can serve both days if launch day
   falls inside its life; otherwise a second token with the same rows.
2. Gives Cloudflare's GitHub app access to the one repository, in the browser. Nothing
   more: the trial's project was created through the API and built from GitHub without
   "Connect to Git" in the dashboard (captures 027 to 047).
3. Says yes twice: on setup day and on launch day.
4. Gives the verification records of Google and Bing, if the script is to write them
   (`search-console-setup`).

**Afterwards, by hand,** as `CLOUDFLARE_CHECK.md` lists under "By hand, always": Crawler
Hints, the Web Analytics switch, HSTS a few days after launch, and deleting the token.

### The script

One Node file beside `cloudflare-check.mjs`, Node 18 or newer, nothing from npm, no
Wrangler. The assistant starts it in the site's folder with a stage:
`cloudflare-setup.mjs setup` or `cloudflare-setup.mjs launch`.

**A yes is a second run with a code.** No run waits for typed input. A stage with
something to change prints its question and a short code, writes nothing, and ends with 3.
The assistant shows Lena the question; on her yes it runs the same command with
`--confirm <code>`. A stage with nothing to change asks nothing.

The code is made from the end state the question names, never from what is there now.
So it keeps fitting while the stage is carried out over several runs, and the script's
own writes do not change it.

- `setup`: the account; the project's name and the repository its `source` names (not
  whether it is created or adopted, which the script's own create would change); the
  production branch, build command, output folder and Fail open; the zone; each setting's
  target value; the `--skip` ids; the zone's proxied hosts the list names; each record
  given with `--record`.
- `launch`: the project and its `pages.dev` address; the host; the commit that goes live;
  whether the forwarding and the NEL rule are in; the zone's proxied hosts other than the
  site's own host (which the stage itself makes proxied), when the NEL rule is in.

What is there now (the record the host has, a setting's old value) is shown in the
question but not in the code. A change made by someone else between the question and the
yes therefore needs no new yes when it leaves the end state the same. That is a judgment
(see "Judgment calls"). A new commit, a new host in the zone, or a changed flag gives a new
question and a new code; the old code then changes nothing.

**No run waits long.** A run has one deadline, 55 seconds after it starts, which leaves
time to report. Every API call, every `git ls-remote` (it took 24 seconds to fail on a
repository that does not exist, in the trial) and every run of the check script gets only
the time left. The check script's `--timeout` bounds each answer, not the run, and a home
page can take up to four answers, so the script passes a quarter of the time left; when
that is under a second it skips the check and ends with 4. A program still running at the deadline is
stopped.
A run that reaches the deadline ends with 4; the next run reads what is there. Where
Cloudflare is not done (a build, a domain becoming active), the run also ends with 4 and
says what it waits for; the assistant runs the same command again.

**Before every deployment call** the script reads the project's deployments and starts
none while one of the production branch is queued or building. The trial showed that a
second call starts a second build (captures 030 to 040). It then follows the deployment
by the id the call returned.

**Exit status.** 0: the stage is finished and in effect (for `setup`, as far as the API
shows; see the end of script step 7). 1: something failed, was
refused, or is not in effect. 2: the command was wrong. 3: waiting for a yes. 4: waiting
for Cloudflare or for a push; run it again.

**The token.** Read from `CLOUDFLARE_API_TOKEN` or from `.dev.vars`, never from an
argument; `.dev.vars` is refused if git tracks it or does not ignore it. It goes only to
`api.cloudflare.com`, and the environment of every program the script starts (`git`, the
check script) has it removed. A token with no end date is refused: token verify then
omits `expires_on` (capture 001; with an end date it carries one, capture 003). So is one
whose end date is more than seven days ahead (the checklist: "a week at most"), one whose
verify call or zone list is refused, and one whose zone list shows more than this site's
zone (capture 002 showed one zone for a token limited to one). The account in the code is the zone's own: the
zone list names the account of each zone (capture 002). No read shows which accounts a
token reaches: with the plan's rows the accounts list answered 200 and an empty list (T2-003,
T2-009), so the script does not use it. The question asks Lena to have set Account
Resources to her one account. The zone list does show the reach in zones: it named eight
zones for a token whose zones were not yet narrowed, and one after (T2-002, T2-011).

**What the token may do** is learned by trying. A refused read answers 403, code 10000,
"Authentication error", and does not say which row is missing (capture 015); a read can
also succeed with no row for it (capture 016); and the `permissions` list on a zone is not
the token's (capture 018). So a line whose read is refused is skipped with the row it
needs, and a write refused later reads "by hand" with that row, while the run goes on. A
refused write to the project ends the run.

**What it reads from git.** Every file of the site it reads (`src/config.ts`,
`tests/placeholders.spec.ts`, `.github/workflows/ci.yml`, `src/`, `public/`), it reads at a
commit, never from the working tree: `setup` at the head of `main` on GitHub, `launch` at
the commit that goes live. A branch's head is what `git ls-remote origin` answers; if that
commit is not in the local repository, the script says to fetch. Owner and repository come
from the remote's address as configured (`git config remote.origin.url`), in any of its
forms (HTTPS, with or without a user name; SSH), and that address is never printed: the
user name part can hold a credential.

**Where it sends requests.** Cloudflare's API host; the site's own addresses, only through
the check script; the zone's nameservers, for DNS lookups; GitHub, only through `git
ls-remote`. For the tests the API host, the site's addresses and the resolver can each be
replaced from the environment by a literal loopback address (`127.0.0.0/8`, `[::1]`),
never by a name and never from `.dev.vars`. The script prints a line while such an override
is in effect.

**It never** merges, runs `npm run ship`, deletes or detaches anything, or changes a
record other than the host's own address record.

**A good production build** of a commit, in both stages: a deployment of this project
in the production environment, of that commit, that succeeded, that Cloudflare built (the
stages `clone_repo` and `build` succeeded; an upload has them `idle`, captures 021 to 026),
and that records `production_branch` as `PROD_BRANCH` (a deployment records the production
branch of its time, capture 055).

### Which project and which publish model (script step 1, both stages)

- **Publish model.** `PROD_BRANCH` `main` and no `production` branch on `origin`:
  single-stage. `PROD_BRANCH` `production` and that branch exists: two-stage. Anything else:
  the script stops and says what each model needs (scenario 6). The starter ships
  `production` for every site, so the value alone decides nothing.
- **The project.** With `--project <name>`: that project if its `source` names this
  repository; it stops if it names another or has none; if no project has that name, the
  list says one of that name will be created. Without `--project`: the one project whose
  `source` names this repository (owner and repository compared without regard to case);
  it stops if two do. If none does, a project named like the repository (lowercased, each
  character other than a letter, digit or `-` made `-`, cut to 58 characters as the check
  script's own rule allows, then dashes trimmed from both ends; it stops if nothing is
  left),
  with the same stops; if none, it will create one of that name.
- **Its address** is the `subdomain` Cloudflare returns, never the name: in the trial the
  live project's name was not the first part of its `subdomain` (captures 019, 020).
- **It stops** if `SITE.url` is still the starter's `example.com`, or if Cloudflare has no
  active zone for its host.

### The `setup` stage (setup day, first yes)

2. **Asks.** Lists every change with what is there now and what it will be, and what it
   will skip and why. It ends by saying that afterwards the assistant pushes one commit to
   a pull request (script step 7).
3. **The project.** Creates it with a `source` naming the repository (production branch,
   `npm run build`, `dist`, Fail open on in both environments; no framework preset, which
   the trial's project did not have either and built without, capture 027), or adopts it. A change to
   an adopted project is a PATCH that holds only what changes: the trial made five such
   changes and every other variable and secret survived each (captures 048 to 062). Fail
   open always goes for both environments: one alone is refused, code 8000066 (capture
   050). The script lists the variables' names before and after; a missing name ends the
   run with 1. It never sends a variable it does not change, so it cannot blank a secret
   whose value it cannot read (a secret reads back with an empty value, capture 054).
4. **A first build, if needed.** If the project has no domain and no good production build
   of the head of the production branch, the script starts one: the
   deployment call with an empty form builds that head (capture 030; creating a project
   starts none, capture 028). If the newest production build of that head failed, it
   starts none and ends with 1, naming the failure. A project that serves any custom domain, this site's or another, gets no
   build and no branch change from this stage (decision 7): if its production branch is
   the wrong one, the stage ends with 1 and writes nothing (scenario 5); if it is right,
   the stage goes on with the rest of its list.
5. **The settings** the checklist lets an API set: Always Use HTTPS on, Minimum TLS
   Version 1.2, Email Address Obfuscation off, the NEL switch off (zone settings, a PATCH
   of `{"value": …}` each, read back; captures 067 to 078); Bot Fight Mode off and the AI
   fields (one PUT to Bot Management with the ten fields the first trial's PUT sent,
   `fight_mode`, `enable_js`, the four AI policies, `crawler_protection`,
   `content_bots_protection`, `is_robots_txt_managed` and `cf_robots_variant`, each as read
   except those it changes, plus `bot_preference_sync_enabled`; captures 079 to 081,
   T2-061 to T2-064). The AI fields are decision 8's: `ai_bots_protection`, `ai_search`,
   `ai_user` and `ai_training` set to `disabled`, and `crawler_protection`,
   `content_bots_protection` and `bot_preference_sync_enabled` off. Bot Preference Sync is
   `bot_preference_sync_enabled`, the field that puts Cloudflare's lines in `robots.txt`
   (T2-062 to T2-064). `is_robots_txt_managed` is always sent as `false`: the first
   trial's PUT sent `false` and was accepted, and Cloudflare refused `true` (T2-065). Each
   line says it changes the whole domain, names the zone's proxied hosts (the site's own
   host too, if it already serves something), and says what changes for a visitor there.
   HSTS is not among them. `--skip <id>` leaves a line as it is: `https`, `tls`, `email`,
   `nel`, `bot`, `ai`.
6. **The records Lena dictates,** each given as `--record "<type> <name> <content>"`: the
   first two words are the type and the name (`@` or a name relative to the zone, or the
   full name), the rest is the content, spaces and all. Each is written DNS only. The script checks the shape: a name that ends in a verification host
   the kit knows (`verify.bing.com`), or a CNAME target with no dot, looks swapped
   (scenario 15). A TXT goes beside the TXT records at that name, which the list shows; one
   that is already there is not sent again (the trial's second identical TXT was refused,
   code 81058, capture 145). A CNAME is written only where the name has no address record
   (a second one is refused, code 81053, capture 146). Each is read back through the API,
   then asked of the zone's nameservers; one not seen there within the run reads "written;
   the nameservers do not show it yet", and is no failure.
7. **Shows the connection.** The proof is a deployment of this project that Cloudflare
   started from a push (`github:push`, captures 033 to 040), of any branch and any age,
   that Cloudflare did not skip: with previews off, a push to a pull request leaves a
   `github:push` deployment marked `is_skipped`, which was never built (T2-026, T2-027).
   Until there is one, runs end with 4 and ask for a commit pushed to a pull request (D7).
   Where `source.config.preview_deployment_setting` is not `all`, a pull request may not
   build, and the run says the push that does is the production branch's: on a two-stage
   site that is `npm run ship`, on the owner's word, once `main` has a commit that
   `production` lacks (a merged pull request; ship pushes nothing while the two are equal,
   `templates/astro/scripts/ship.sh:165`). Ship's own last check then reports an old
   build, since no domain is attached; that is expected, and the proof comes on setup's
   next run. On a single-stage site the push is a merge to `main`. A failed push build counts as proof of the connection and is reported as a
   failed build. Each run without proof names the likely causes (the connection was never
   made or is broken; builds are paused on the project; the build is still queued) and how
   to tell them apart in the dashboard. The stage also ends with 4
   while the build of script step 4 runs.

The report says the settings are "read back through the API only" for now: the outside
check comes with the launch stage, since no request may reach the domain before then. So
`setup`'s 0 means: finished, and in effect as far as the API shows.

### The `launch` stage (launch day, second yes)

8. **Refuses before it asks,** with 1 and the reason, unless all of these hold:
   - the project's own lines of `setup` (script step 3) have nothing left to change; the
     zone settings and records are not launch conditions, so a `--skip` there does not
     stop a launch;
   - the project has the proof of script step 7 (scenario 22);
   - its newest production deployment is a good production build of the head of the
     production branch; one still queued or building ends the run with 4;
   - at that commit, `UNFILLED_UNTIL_LAUNCH` in `tests/placeholders.spec.ts` is empty, and
     `src/` and `public/` hold no `DRAFT_TOKEN` of that file, which `ci.yml` must search
     for too. A missing file, a line the script cannot read in the starter's form, or two
     tokens that differ: it cannot tell, and refuses;
   - the token can read the zone's DNS records, and the host has at most one address
     record (A, AAAA or CNAME); below the apex, also no record of another type, which a
     CNAME cannot stand beside (scenario 24; the trial did not try it); and that record's
     type, content and proxy state fit in the 100 characters of script step 10.

   These are the script's own stops, not the launch check: that stays `new-website` §4
   and the site's tests, and the question says so. When the domain is already attached
   and active (by hand, or by an earlier run), none of them is checked and nothing is
   attached (scenario 31). The site is public already, and script step 13 starts a build
   only of the commit that is live, so nothing new goes live that way. The commit the
   stage then expects is that of the newest production deployment that succeeded; while a
   newer one is queued or building, the run ends with 4.
9. **Asks.** The question names the domain, the commit, the host's record now and what it
   will be, and that this makes the site public. It says visitors may get errors for a few
   minutes (in the trial the domain turned active about two and a half minutes after its
   record, captures 104 to 128). It names the forwarding unless `--skip canonical`, and
   the NEL rule unless `--skip nel-rule`, as "if the headers are still sent". If the
   project has secrets, it says the forwarding build takes them as saved now: their values
   read back empty (capture 054), so the script cannot tell whether one changed since the
   live build.
10. **Attaches, then points the host.** The attach call first, unless the domain is
    already attached (Cloudflare leaves an
    existing record alone and waits for it, captures 130 and 131), then the record in the
    same run: a proxied CNAME to the project's `pages.dev` address, created if the host
    has none (capture 104), or the one existing record changed to it with one PATCH, which
    keeps its id (capture 132). The same write puts the old record's type, content and
    proxy state in the record's `comment` field, then as much of the comment the record had
    as fits in 100 characters (Cloudflare's limit: 100 was stored, 101 refused with code
    9313, on a Free zone, T2-057 and T2-058; the script uses 100 on every plan). So every later run can print the old
    record and it can be put back by hand; the part of the owner's comment that did not fit
    is printed in that run. Script step 8 refused an old record too long for this;
    one that has grown too long since the question changes nothing here, and the run
    ends with 1, printing it in full and saying to change it by hand. The trials wrote
    comments on new records (captures 104, 129) and with the PATCH that turned an apex A
    record into the CNAME (T2-046, T2-047). If
    that PATCH is refused, the run ends with 1, the host's record unchanged and the domain
    pending, and says to change the record by hand. Runs end with 4 until the
    domain is `active`; `error`, `blocked` or `deactivated` ends with 1 and Cloudflare's
    words, and nothing is detached.
11. **The first request.** Only when the domain is active does the script ask it
    anything, through the check script with `--build <commit>`, the domain's host looked up at the
    zone's own nameservers (other hosts, such as the `pages.dev` address, as usual). In the trial a computer that had asked for the host before its
    record existed kept getting "no such host" for minutes after the domain was active.
    The `build` item must be `ok`; anything else (another commit, no `build.txt`) ends with
    1 before script step 12.
12. **NEL.** If the check's `nel` item fails, the script reads the zone's ruleset for the
    phase `http_response_headers_transform`. If it already holds the kit's rule (by its
    description, "Remove NEL headers", the checklist's name), it adds nothing and ends
    with 1: the rule is there and the headers still come. Otherwise it adds the
    checklist's rule that removes `NEL` and `Report-To`. Where the zone has a ruleset for
    the phase
    `http_response_headers_transform`, it adds the rule with the call that adds one rule to
    a ruleset, which left the rule already there, its id and its version untouched
    (T2-024, T2-025); where it has none (asking for it answers code 10003, T2-018), one PUT
    to the phase creates the ruleset with the rule (T2-023). Whether a rule another person
    adds at the same moment survives was not tried. The rule took
    effect within seconds on the site the checklist records, so this run ends with 4, and
    the next runs `nel` again; a failure then ends with 1.
13. **Forwards `pages.dev` to the domain.** If `CANONICAL_URL` is saved as `https://` and
    the domain and the check's `canonical` item is `ok`, there is nothing to do. If the
    live build already records `CANONICAL_URL` with that value and `canonical` still fails,
    it starts no build: it says the live build has the variable and the forwarding does
    not answer, names the causes the checklist's section 5 lists for a 200 there, and ends
    with 1 (scenario 42). Otherwise it saves `CANONICAL_URL` alone, from Cloudflare's own name for the domain, in a PATCH
    as in script step 3. A variable reaches only builds made after it (seen in the trial
    through a test function), so it then starts a production build, but only if the head of the production
    branch is the live commit, the live build was built by Cloudflare, and the live build's
    recorded variables and build settings (a deployment records both, captures 030, 062,
    063) differ from the saved ones in `CANONICAL_URL` alone. A secret is compared by name
    only: its value reads empty on the project and on the deployment alike (capture 062). Otherwise it says "the
    variable is saved, but no build has picked it up", names each other difference, and
    ends with 1. When the build is done it checks its commit and runs the check's
    `canonical` item; if that still fails, it says the build is done and the forwarding
    does not answer, and ends with 1.

A `launch` run ends with the whole check script. Its exit status follows from the check's JSON,
in this order, and nothing else:

1. Any request in `unanswered`, or any item marked `blocked`: 1 (nothing was seen, and an
   empty answer is never a pass), whatever the rest says.
2. Otherwise, any item whose state is `fail`, unless the table below gives that item's
   `fail` 0, or names a `--skip` id that this run was given: 1.
3. Otherwise: 0. Every `look`, `hand` and `skip`, and every `fail` that rule 2 lets through,
   is listed for Lena as what it is.

| Check item | Set by | A `fail` gives |
|---|---|---|
| `pages` | `setup` (the project) | 1 |
| `build-settings` | `setup` | never `fail`: a `hand` item |
| `domain` | `launch` | 1 |
| `fail-open` | `setup` | never `fail`: a `hand` item |
| `canonical` | `launch` | 1; 0 with `--skip canonical` |
| `https` | `setup` | 1; 0 with `--skip https` |
| `tls` | `setup` | never `fail`: a `hand` item |
| `hsts` | nobody: Lena, later | never `fail`: the script never passes `--hsts-on` |
| `nel` | `setup` (switch), `launch` (rule) | 1; 0 with `--skip nel-rule` |
| `bot` | `setup` | 1; 0 with `--skip bot` |
| `analytics` | nobody: Lena, by hand | 0 |
| `email` | `setup` | 1; 0 with `--skip email` |
| `hints` | nobody: Lena, by hand | never `fail`: a `hand` item |
| `ai` | `setup` | never `fail` (a refusal is a `look`) |
| `robots` | the site's own file | 1: the site is now public and its `robots.txt` keeps crawlers out |
| `build` | `launch` checks it first (script step 11) | 1 |
| `scripts` | nobody | never `fail` (another path is a `look`) |

The ids are the check script's (`CLOUDFLARE_CHECK.md`, "For an assistant"); a test fails
when its list and this table differ. `launch` accepts every `--skip` id `setup` does, plus
`canonical` and `nel-rule`; on `launch`, `tls`, `ai` and `nel` change no exit status (`nel`
is the switch, which `launch` does not write). Only the ids a run is given count: `setup`'s
report prints the `launch` command with the ids it was run with, and a `fail` that gives 1
says that if the setting was left out on purpose, its `--skip` belongs on the command.
The report gives, for each thing set, what it was, what it is now, and how that was
checked. Fail open, the build settings, Minimum TLS Version and the AI fields have no
outside check: "read back through the API only", with the checklist's ssllabs test named
for Lena to run. The report names the live address and, on a two-stage site, the address
Cloudflare lists in `aliases` for `main`'s newest preview build (captures 021 to 026;
read, not opened), or, where `main` has no preview build, says so. It lists what is left by hand, HSTS with its earliest day, says that
previews can be put behind a sign-in (D5), and reminds Lena to delete the token.

**A finished setup** is one where every line of both lists reads as its end state, the
project has a push build, and the domain is active with the check's `build`, `nel` and
`canonical` items `ok` (or skipped). Run on it, each stage writes nothing, asks nothing and
ends with 0.

## Tests

The tests run the script as a program against a stub of Cloudflare's API, small sites and
a resolver on `127.0.0.1`, and fixture repositories as `origin`, the way `make
test-cloudflare-check` tests the check script, in the same CI workflow
(`.github/workflows/clean.yml`). A fixture's `origin` is a GitHub-form address that the
test's own git config sends to a local folder (`url.<folder>.insteadOf`), so the script
reads an owner and a repository as in real use (not tried).

The stub's answers are the two trials' captures. Before a capture is committed, every name, id and
address in it is replaced by the scenarios' made-up ones: the token, the account's and
the zone's ids, the account's name, any email address, the zone's name and nameservers,
IP addresses, the GitHub owner and repository with their numeric ids, project names and
`pages.dev` addresses, deployment and record ids, commit hashes and messages. `bash
scripts/check_clean.sh` must pass on them, but it looks for listed names, email addresses
and secrets, not ids: a test of its own checks that every id, IP address, host name (apart from public
hosts such as `api.cloudflare.com`, `github.com` and `verify.bing.com`, on a short list) and
commit hash in the fixtures is one of the scenarios' made-up values.

## What is known, and how

**Seen in the trial, 2026-10-13** (captures 001 to 159, kept outside every repository; a
token limited to one account and the live zone; a throwaway repository and two throwaway
projects; hosts of their own below the zone, never its apex):

| What | Captures |
|---|---|
| A project created with a `source` builds from GitHub once the app has the repository; Cloudflare fills in the ids; a pushed commit built a preview within a second, `github:push` | 027, 033 |
| Creating a project starts no build; a deployment call with an empty form builds the head of the production branch, as production, `ad_hoc` | 028, 030 |
| A second call while the first is queued starts a second build; both ran to the end | 031, 033 to 040 |
| A Cloudflare build and an upload are both `ad_hoc`; Cloudflare's has `clone_repo` and `build` `success`, an upload has them `idle`; `source.type` is `github` on all | 021 to 026, 040 |
| A push to the production branch builds a production deployment, `github:push` (18 of them on the live project) | 021 to 026 |
| A PATCH holding only the change keeps every other variable and secret (secret, plain variable, build setting, production branch, Fail open) | 048 to 062 |
| Fail open for one environment alone: 400, code 8000066 | 050, 053 |
| A changed production branch changes nothing served until the next build; a deployment records the production branch of its time | 052, 054, 055 |
| A deployment records its variables (a secret by name, its value empty) and its build settings | 030, 062, 063 |
| A deployment does not record Fail open | 030, 055 |
| A branch's preview address replaces `/` by `-` and moves to its newest build | 038 to 046 |
| Token verify: no `expires_on` without an end date | 001, 003, 064, 148 |
| A refused read: 403, code 10000, no reason; a read with no row can succeed; a zone's `permissions` are not the token's | 014, 015, 016, 018 |
| Zone settings: a PATCH of `{"value": …}`, read back; writing the same value is accepted and does not always move `modified_on`; NEL's value is `{"enabled": false}` | 067 to 078 |
| Bot Management: Bot Fight Mode is `fight_mode`; the AI fields and the three switches read `disabled` or `false` on the live zone; a PUT of ten fields with the zone's own values was accepted and changed nothing, the three fields it left out included | 013, 079 to 081 |
| The header rule: a PUT with the existing rule kept it, its id and version | 082 to 084 |
| Attaching a domain creates no record: `initializing`, then `pending` with "CNAME record not set" | 085 to 091 |
| A proxied CNAME to the `pages.dev` address turns the domain active: verification after about a minute, the domain after two and a half | 104 to 128 |
| Attaching a host that has an A record elsewhere keeps the record; one PATCH to a proxied CNAME is accepted, keeps the id, and the domain was active two minutes later | 129 to 142 |
| A second TXT at a name is accepted; an identical one is refused, 81058; a second address record at a name is refused, 81053 | 143 to 147 |
| A pull request whose one commit is empty is built; a project connected later builds a pull request's next commit, not one already pushed | 092 to 101 |
| Removed afterwards on the maintainer's word: both throwaway projects, their hosts and the four records | 149 to 159 |

Seen without a capture: a test function in the throwaway project gave the same hash of the
secret after every PATCH, on production and on a preview, and answered with the old values
until a new build, so a variable reaches only builds made after it; the zone's nameserver served a new TXT within four seconds, and
Node's resolver, set to that nameserver, returned it; `git ls-remote` with its input
closed always returned (an unknown host at once, a missing repository after 24 seconds, a
normal remote in 0.6); a computer that asked for a host before it had a record went on
getting "no such host" for minutes after the domain was active; Bing's record is a CNAME
from a name of 32 hexadecimal characters to `verify.bing.com`, and the swapped entry of the
launch day had `verify.bing.com` as its name. The trial ran Node 26 and git 2.33, not
Node 18.

**Seen in the second trial, 2026-10-14** (captures T2-001 to T2-078, in a folder of their
own outside every repository; a token of the plan's rows; a throwaway repository with a
three-file site and one throwaway project). The first domain named turned out to hold live
services; T2-012 to T2-029 ran there, and only the project and two header rules were
written, both removed. Everything from T2-030 ran on an empty spare zone.

| What | Captures |
|---|---|
| The zone list shows a token's reach in zones: eight, until the token was narrowed, then one. The narrowing showed only after some minutes | T2-002, T2-004, T2-007, T2-008, T2-011 |
| The accounts list does not show a token's reach: with the plan's rows, 200 and an empty list; with Account → Account Settings → Read added, two accounts | T2-003, T2-005, T2-009, T2-031 |
| A new zone's defaults: Always Use HTTPS off, Minimum TLS 1.0, Email Address Obfuscation on, NEL on | T2-012 to T2-015, T2-036 to T2-039 |
| With previews off (`preview_deployment_setting: none`, kept as sent), a push to a pull request leaves a `github:push` preview deployment marked `is_skipped`, never built; a push to the production branch builds, `github:push`, in about 30 seconds | T2-021, T2-026 to T2-029 |
| A missing response-header ruleset answers code 10003; one PUT to the phase creates it with one rule; the call that adds one rule appends and leaves the first rule's id and version as they were | T2-018, T2-023 to T2-025 |
| The apex behaves like a host below the zone: attaching keeps its A record, "CNAME record not set"; one PATCH to a proxied CNAME, with a comment, keeps the id; verification active after about a minute, the domain after 2 minutes 18 seconds; the apex then served the production build | T2-042 to T2-056 |
| A record comment holds 100 characters; 101 is refused, code 9313 | T2-057, T2-058 |
| A Bot Management PUT that changes a value works and keeps the three fields it leaves out, `bot_preference_sync_enabled: true` among them; `ai_training` takes `disallow`; a PUT with `ai_training: block` and `is_robots_txt_managed: true` was refused (10400), and so was one with `is_robots_txt_managed: true` alone | T2-059 to T2-062, T2-065, T2-066 |
| `bot_preference_sync_enabled` is Bot Preference Sync: on, with training disallowed, Cloudflare put 132 lines of its own in front of the site's `robots.txt`; off, the site's own file came back within 15 seconds | T2-061 to T2-064 |
| The checklist's NEL rule removed `NEL` and `Report-To` from the apex within 20 seconds | T2-067 |
| Removed on the maintainer's word: the domain, the apex record, the test record, the ruleset, the project; Bot Management put back as found, read back the same | T2-069 to T2-078 |

Seen without a capture, in the second trial: this Mac, having asked for the apex before it
had a record, went on answering "could not resolve host" after the domain was active,
while the zone's nameserver gave the address at once (requests through that address
succeeded).

**Read in Cloudflare's API reference, not tried:** the domain statuses `blocked`,
`deactivated` and `error`; what `disabled` and `false` do in each AI field (from the
field descriptions); the Bot Management update call's own description.

**Not verified.** Each is named with what follows if it turns out otherwise.

1. Whether a change to Fail open reaches the build that is live, or only later ones. A
   deployment does not record it. The report says so for an adopted project; a created
   project has it from its first build.
2. Settled by the second trial for the three fields the PUT leaves out (T2-061, T2-062):
   they kept their values, a `true` among them. The script still reads the whole object
   back; a field it did not mean to change that reads differently ends the line as "by
   hand", with 1.
3. Settled by the second trial (T2-042 to T2-056): the apex behaves as a host below the
   zone does.
4. What the host answers between the record change and `active`. Not observed; the
   question says "a few minutes of errors" on the strength of the trial's timings.
5. Settled by the second trial (T2-061 to T2-066): Bot Preference Sync is
   `bot_preference_sync_enabled`. Should Cloudflare change that, the check's `ai` item
   reports Cloudflare's lines in `robots.txt` as a `look`, which gives 0: the report lists
   it, and says that if those lines are Cloudflare's, the switch did not take.
6. That the check script can make its requests through a resolver set to the zone's
   nameservers. Node's resolver answered a TXT lookup that way; an HTTPS request through it
   was not tried. Plan step 6 adds it to the check script with a test.
7. The fixture `origin` sent to a local folder by `insteadOf` (section "Tests").
8. Node 18: everything the script uses must exist there; CI runs the tests on it.
9. Settled by the second trial: the calls that create a ruleset for a phase and add one
   rule to it (T2-023 to T2-025), a PATCH that sets a record's `comment` and its limit of
   100 characters (T2-046, T2-057, T2-058), and the accounts list, which does not show a
   token's reach (T2-003, T2-031). Not tried: two people adding rules at the same moment.
10. `preview_deployment_setting` takes `none` besides `all` (T2-021); other values were not
    tried. The script treats every value but `all` as "a pull request may not build".
11. Whether a CNAME is refused beside a record of another type below the apex. The script
    refuses that case before it asks (script step 8), so nothing is tried on it.

## Judgment calls

Facts above were seen; these were weighed. Each with the strongest case against.

- **A yes binds the end state, not the old values.** Seen: the script's own writes would
  break any code made from current values (round 3, H5). Judgment: a change by someone else
  that leaves the end state the same needs no new yes. *Against:* the yes to replacing
  Lena's apex record was given knowing what it pointed to; if a colleague repoints it in
  between, the script still replaces it. The record is printed before it changes, and the
  commit in the code means a code rarely outlives a day of work on the site.
- **Any push build counts as proof of the connection.** Seen: a deployment records its
  trigger. Judgment: a timer (first gate, H8), or a rule that the push build be newer than
  the script's own builds (this gate, round 1, cut in round 2 because launch's own build
  then made a finished setup ask for a push again), adds a rule and still proves nothing
  about today. *Against:* an adopted project the
  script started no build on, whose connection broke last week, passes on its old push
  builds; failure 2 of the launch day was exactly that. The launch stage still demands that the newest production build is the
  head of the production branch, which a broken connection after `npm run ship` fails.
- **The NEL rule waits for launch day.** Seen: the switch alone did not stop the header on a
  live site (the checklist), and no request may reach the domain before launch. Judgment:
  ask for the rule as "if needed" in the second yes, rather than adding it on setup day
  without looking. *Against:* until launch the domain's old site, if any, keeps sending
  the headers, and the second question gets one more line.
- **Settings on setup day.** Seen: only HSTS and the forwarding must wait (the checklist,
  first paragraph). Judgment: write the rest with the first yes (D1). *Against:* if the
  domain still serves an old site, it gets them days before the new one is live; the list
  names that host on every line, and each line can be left out.

## Decisions taken

Numbered 1 to 8 and cited as "decision N". The questions the maintainer closed are D1 to
D7, in the next section.

1. **Route B is the model** (2026-10-12). Previews per pull request and `npm run ship` are
   worth one authorization in the browser.
2. **The checklist stays the list.** A test compares the script with
   `docs/CLOUDFLARE-CHECKLIST.md`: item titles and dashboard paths, as `make
   test-cloudflare-check` does for the check script, and each value the script writes
   against the checklist's words for it.
3. **Read, say, do, read back, and check from outside where an outside check exists.** The
   checklist records a case where the API said a header was off and the site still sent
   it, and the trial a setting that read on and showed nothing from outside (Email Address
   Obfuscation, captures 007 and 070, on a page with no plain address).
4. **One check, not two.** What the live site or the `pages.dev` address answers, the script
   learns from `cloudflare-check.mjs`, never from a reading of its own. The check script
   gains, in plan step 6's second pull request: running single items, a path-and-query
   check in its `canonical` item, which today asks only for `/` (follow-up U1 of the first
   gate), and a resolver option for the domain's host.
5. **A yes is a second run with a code.** No flag says yes to whatever the script would do.
6. **No run waits long.** What takes Cloudflare minutes is met by running again.
7. **The script sets up; it does not repair a live site.**
8. **Open to every AI crawler, by category, training included** (2026-10-14: "Add it to
   training. I think the upside is bigger, than the contrary"). Besides the AI policies,
   `crawler_protection` (AI Labyrinth), `content_bots_protection` and Bot Preference Sync
   go off. The decision named Bot Preference Sync's field as `is_robots_txt_managed`; the
   second trial showed it is `bot_preference_sync_enabled` (script step 5). `--skip ai` stays for an owner who decides otherwise,
   since the checklist calls Training the owner's choice.

## Decisions D1 to D7

Closed by the maintainer. The case against each stays as the record.

- **D1. How many yeses: two** (final, 2026-10-13: "go back to two yeses"). One for the
  project changes and the Cloudflare settings on setup day, one for attaching the domain.
  First decided as two (2026-10-12); changed the next day to three, one per stage, with the
  reason that the settings could only be written once the domain serves the site. That
  reason was false (round 3, H3): the checklist makes only HSTS and the forwarding wait.
  *Against:* guardrail 4 of `CLOUDFLARE_FIRST_DEPLOY.md` asks for a yes before each change;
  a yes to a list is weaker. Plan step 7 rewrites that guardrail for the script: a printed
  question confirmed with its code is the confirmation for the changes it names, and for
  nothing else.
- **D2. Node, with nothing from npm** (2026-10-12), like the check script. *Against:* most
  of the kit's scripts are bash or Python.
- **D3. In the kit,** in the `new-website` skill beside the check script, run in the site's
  folder (2026-10-12). *Against:* an owner without the kit cannot run it, and follows route
  B by hand.
- **D4. The project and the checklist's settings, in one script.** *Against:* the settings
  touch the whole domain, and two of them are judgment calls the checklist explains at
  length.
- **D5. Previews behind a sign-in: not in the first version;** the report names the
  option. *Against:* previews are public to anyone with the address.
- **D6. The `production` branch is created by the assistant on the owner's word,** not by
  the script. *Against:* one more stop.
- **D7. The connection is proved by Cloudflare's own build of a commit pushed to a real
  pull request** (or, where previews do not build, of the production branch, script step
  7). *Against:* a new site may have none, and one opened for the purpose is
  noise in the history.

## Hooks

Plan step 7 brings these in line in the same pull requests as the script:

- `CLOUDFLARE_FIRST_DEPLOY.md`: the opening advice that recommends route A to newcomers
  (the script becomes the recommended way; A stays for an owner who wants no GitHub
  connection), option B, guardrail 4 (D1), and "After go-live".
- `skills/new-website/SKILL.md` §4, which repeats that advice.
- `website-team-setup` §6: connecting by hand, and item 3, which takes the project's name
  for the first part of its `pages.dev` address.
- `docs/CLOUDFLARE-CHECKLIST.md`: section 6's table, which has no DNS row (its field for Bot
  Preference Sync is corrected in karero/croftweaver#319); section 5's "your
  Pages project's name (the first part of its `.pages.dev` address)"; section 6's "for an
  afternoon", now that one token may serve two days; section 1's framework preset, which
  the script does not set, and the check script's `build-settings` line, which looks for
  it. Section 6 also gains the API field and value for each setting
  the script writes (the four AI policies and `disabled`, NEL's `{"enabled": false}`), so
  that decision 2's test reads them there and not from a copy inside the test. And
  section 6's "Some changes replace a whole list, as the Transform Rules do", since the
  script now adds one rule and sends nothing back.
- `CLOUDFLARE_CHECK.md` and the check script's messages: "By hand, always", the new options,
  the local addresses the option table names (follow-up U2 of the first gate).
- Every place in the kit that builds `<name>.pages.dev` from the project's name (a search
  for `pages.dev` finds them in `templates/PUBLISHING.md`, `CLOUDFLARE_FIRST_DEPLOY.md`,
  `new-website/SKILL.md`, `templates/AGENTS.md`, the template's README, `website-review`,
  `website-qa`, `search-console-setup`, `references/WEBSITE_ARCHITECTURE.md`,
  `docs/PAGES-OR-WORKERS.md`, the comments of `templates/astro/functions/_middleware.ts`,
  the check script and its reference, among others).
- `templates/PUBLISHING.md`, "Deploy by command", which says a site put online with a token
  has no GitHub connection; and `templates/AGENTS.md`'s "Preview before merging", which
  sends the owner to `website-team-setup` §6 to connect.
- `search-console-setup`, which calls the verification record a human step and says to run
  it after the site is live, while the records can now go in on setup day.

## Review trail

The first version's gate: `docs/reviews/REVIEW-plan-2026-10-12-pr265.md`. This version's:
`docs/reviews/REVIEW-plan-2026-10-14-pr303.md`, at High depth, because the script changes a
Cloudflare account with a token and can make a site public. That trail says, for each of
the first gate's open findings H1 to H26, how this version deals with it.
