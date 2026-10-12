# Plan: Cloudflare setup by one token, for a site connected to GitHub

Requirements record for a script that does not exist yet. Where this plan and the shipped
files disagree, the files win. Names of sites and people stay out of this public repo on
purpose; the business in the scenarios is made up.

## Status, 2026-10-12 · branch base origin/main e58d3ae

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | Requirements and scenarios (this file) | ▶ written; not reviewed. The PLAN gate waits for step 2, because this plan takes its list of settings from that file | this file |
| 2 | The Cloudflare checklist reaches `main` (`docs/CLOUDFLARE-CHECKLIST.md`; another session's work, on a local branch `docs/cloudflare-checklist`, read at `7a665a0`, not on GitHub when this was written) | ⏸ not this plan's to do; this plan takes its list of settings from that file | — |
| 3 | The maintainer closes the decisions D1 to D7 below | ✅ all seven decided as recommended (maintainer, 2026-10-12: "all as recommended") | section "Decisions D1 to D7" |
| 4 | Spike on a throwaway repository and project: the three things marked "not verified" under "What is known" | ⏸ not started | — |
| 5 | The script and its tests against a stub of Cloudflare's API | ⏸ not started | — |
| 6 | Hooks: `CLOUDFLARE_FIRST_DEPLOY.md` option B, `website-team-setup` §6, the checklist's section 6 | ⏸ not started | — |
| 7 | Review gate on the script (High: it changes an account with a token, and it can make a site public) | ⏸ not started | — |
| 8 | One real site set up with it, start to finish, with the owner watching | ⏸ not started | — |
| 9 | Release note line | ⏸ not started | — |

Legend: ✅ done · ▶ in progress · ⏸ not started or blocked · ⚠ deviated

## Why

Putting a new site on Cloudflare is the step where an owner who has never seen the
dashboard loses the most time, and where a wrong click has the biggest effect. The kit has
three routes today (`skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md`):

- **A, by token:** the assistant does everything, but the site is a Direct Upload project.
  It has no preview per pull request, and `npm run ship` does not publish it.
- **B, connected to GitHub:** previews and `npm run ship` work, but the owner clicks
  through the dashboard alone, with `website-team-setup` §6 warning about the traps.
- **C, the assistant drives the browser.** Slow, and not every assistant can.

The maintainer's decision (2026-10-12): the setup should be done for the owner as far as a
token allows, on the model of route B. This plan is that: route B's result, with route A's
effort.

It is written after one site's launch on 2026-10-12, set up by hand on route B. Five things
went wrong that day. Each is a scenario below, so that the script cannot repeat it:

1. The project was created with production branch `main` on a two-stage site. Cloudflare
   published `main` to the live domain at once, with unfilled slots on the legal pages, and
   the domain was open to search engines.
2. The project lost its connection to GitHub. Merges and pushes built nothing, with no
   error anywhere but a banner in the dashboard.
3. "Create deployment" in the dashboard did nothing while the connection was broken.
4. A variable was typed into the dashboard and not saved; later it was saved, but no
   production build followed, so it had no effect until the next publish.
5. The owner took `<project>.pages.dev` for the preview. It is the live build's second
   address; the preview is `main.<project>.pages.dev`.

## Shape

**What the owner does.** Three things, none of them in a terminal:

1. Makes one short-lived token, from a list of permission rows the assistant shows.
2. Authorizes Cloudflare's GitHub app for the one repository, once, in the browser.
   (Whether the script can do everything after that, or the owner must also click
   "Connect to Git" once, is the first question of the spike in step 4.)
3. Switches on Crawler Hints, which has no API according to the kit's notes.

**What the script does.** It runs in the site's folder, started by the assistant. It reads
the token from the environment or a file the repository ignores, never from an argument.

1. **Looks first.** Checks the token (which account, which zone, which permissions, when
   it ends), reads the project if one exists, and reads the site's publish model from the
   repository (two-stage or single-stage).
2. **Says what it will do.** Prints every change it is about to make, in the owner's
   words, and which of them makes the site public. Nothing has changed yet.
3. **Sets up the project.** Creates it, or adopts the one the owner created: build command
   `npm run build`, output `dist`, production branch as the publish model says, Fail open.
4. **Proves the GitHub connection with a real build.** It pushes nothing itself: it asks
   the assistant to open the first pull request (or uses one that is open) and waits for
   Cloudflare's own check on it. No check within a set time is a named failure, with the
   repair steps.
5. **Attaches the domain, last and only on a separate yes.** Before it does, it checks that
   the production build is the reviewed one (`build.txt`) and that no unfilled slot is in
   the built pages.
6. **Sets `CANONICAL_URL`, then makes it take effect.** Reads the variables before and
   after, starts a production build, and checks that `<project>.pages.dev` answers 301 and
   a preview still answers 200 with `noindex`.
7. **Applies the settings of the Cloudflare checklist** that an API can set (its sections
   2 to 4), in the order and with the cautions that file gives. This plan does not repeat
   the list: the checklist is the one place it lives.
8. **Writes DNS records the owner dictates,** such as the verification records of Google
   and Bing: it shows name and target before writing and reads them back with a lookup.
9. **Reports.** Each setting: what it was, what it is now, how it was checked. Each
   address: what it is (live, preview of `main`, preview of a pull request). What is left
   for the owner by hand. Then it reminds the owner to delete the token.

**What it never does.** It never merges, never publishes (`npm run ship` stays with the
owner or the assistant on the owner's word), never deletes a project or a DNS record it
did not create in this run, and never keeps the token.

**A second run changes nothing.** Every step reads first and skips what is already right,
so the script can be run again after a failure or a year later.

## Scenarios

The owner is Lena. Her site is `lenas-backstube` on GitHub, two-stage, and her domain is
`lenas-backstube.example`, already on Cloudflare.

| # | Given | When | Then | Test |
|---|-------|------|------|------|
| 1 | Lena has made the token and authorized the GitHub app | the script runs for the first time and she says yes to its list | the project `lenas-backstube` exists with production branch `production`, build command `npm run build`, output `dist`, Fail open on; nothing answers on her domain yet | stub API: the create call carries these values; a second run sends no create call |
| 2 | the site is two-stage and a project already exists with production branch `main` | the script looks | it stops before any change and says: "Your live address would publish `main`, the preview. I will set the production branch to `production`. Yes?" | stub API returns such a project; the first write is the branch change, and only after a yes |
| 3 | the site is two-stage and the repository has no `production` branch | the script looks | it says so and asks the assistant to create the branch from the reviewed `main`; it does not create a project that would have nothing to build | fixture repository without the branch |
| 4 | the project exists but Cloudflare cannot reach the repository | the script waits for Cloudflare's check on the open pull request | after the set time it reports "Cloudflare did not build this pull request. The connection to GitHub is broken or was never made", with the steps to repair it, and stops before the domain step | stub: no check appears; exit code and message |
| 5 | everything above is done; `main` holds a page with an unfilled slot | Lena says "attach my domain" | the script refuses: it names the page and the slot, and attaches nothing | fixture build with a slot |
| 6 | the production build is the reviewed one | Lena says "attach my domain" | the domain is attached, the script waits until Cloudflare reports it active, checks `https://lenas-backstube.example/build.txt` with a cache-busting query, and only then says "live" | stub: status goes pending then active; the "live" line comes after the `build.txt` check |
| 7 | the domain serves the site | the script sets `CANONICAL_URL` | the variable is there on a read-back, the project's other variables are unchanged, a production build was started, and `lenas-backstube.pages.dev/about` answers 301 to the same path on her domain | stub API with two existing variables; a curl against a local stub for the 301 |
| 8 | the variable was set but the production build failed or did not start | the script checks the 301 | it says "the variable is saved, but no build has picked it up", not "done" | stub: no new deployment |
| 9 | Lena gives the Bing record with name and target the wrong way round | the script shows what it will write | it notices that the name is the verifying service's host (`verify.bing.com`) and the target is not a host name, says the two look swapped, and asks before writing | unit test on the record check |
| 10 | the token lacks the DNS permission | the script looks | it lists which steps it can do and which it will skip, before changing anything | stub: permission list without DNS |
| 11 | the token has no end date, or covers all zones | the script looks | it says so and asks for a narrower token; it goes on only if Lena insists | stub: token details |
| 12 | the run is finished | the script reports | the report names `lenas-backstube.example` as live, `main.lenas-backstube.pages.dev` as the preview, and says that `lenas-backstube.pages.dev` now forwards to the live address | snapshot of the report |
| 13 | the script ran last month | it runs again | it makes no write call and reports every setting as already right | stub API holding the end state |

## What is known, and how

**Done on one live site, 2026-10-12** (a project connected to GitHub, two-stage):

- `wrangler pages deploy dist --project-name <project> --branch production` made a
  production deployment in a project that is connected to GitHub. It was the way out while
  the GitHub connection was broken. This plan keeps it as the emergency route, not the
  normal one.
- `wrangler pages download config <project>` shows the project's saved plain-text
  variables per environment. It told a variable that was typed but not saved from one that
  was saved.
- A variable reached only deployments made after it was saved. After the next production
  build, `<project>.pages.dev` answered 301 with path and query kept, and previews kept
  answering 200 with `noindex`.
- With the connection repaired, Cloudflare built a pushed branch by itself and put its
  check on the commit; `npm run ship` then published and confirmed the build.
- Wrangler's browser sign-in had permission to write Pages projects but only to read
  zones, so it cannot stand in for the token where zone settings or DNS are changed.

**Read in Cloudflare's API reference, 2026-10-12, not tried:**

- Creating a project takes `production_branch`, a `build_config` (build command, output
  directory), `deployment_configs` per environment with `env_vars` and `fail_open`, and a
  `source` object for GitHub (owner, repository name, production branch, whether previews
  build). Permission: Pages Write.
- Adding a domain is `POST …/pages/projects/{project}/domains` with the domain's name;
  its status runs from `initializing` and `pending` to `active`.

**Not verified. Step 4, the spike, settles these before any code:**

1. Whether a project created through the API with a `source` object is connected to
   GitHub once the app is authorized for the repository, or whether "Connect to Git" in
   the dashboard is the only way. The reference page does not say. If it is the only way,
   the owner clicks once more and the script adopts the project (scenario 2).
2. Whether attaching a domain creates its DNS record, or the script must write it.
3. How a production build is started for a connected project without a new commit.

The settings of sections 2 to 4, their permission rows and their cautions are the
checklist's, with that file's own sources.

## Decisions taken

1. **The model is route B** (connected to GitHub), by the maintainer, 2026-10-12.
   Previews per pull request and `npm run ship` are worth one authorization in the browser.
2. **The checklist stays the list.** The script reads its order and cautions from
   `docs/CLOUDFLARE-CHECKLIST.md`; this plan adds the project steps and the checks.
3. **The domain is the last step and has its own yes,** because it is the step that makes
   a site public and open to search engines.
4. **Read, say, do, read back, check from outside.** A setting counts as done when a
   request from outside shows it, not when the API says so. The checklist records a case
   where the API reported a header off and the site still sent it.

## Decisions D1 to D7

Closed by the maintainer on 2026-10-12, each as recommended. The argument against each
stays here as the record of what was weighed.

- **D1. One yes or many.** *Decided:* one yes for the whole list, a second for the
  domain. *Rests on:* "the owner should not have to do anything". *Against:*
  `CLOUDFLARE_FIRST_DEPLOY.md`'s guardrail asks for a yes before each change to the
  account; one yes is weaker, and the list must be read carefully to be worth it.
- **D2. What it is written in.** *Decided:* Node, as one file in the site template,
  because every site has Node and the starter already carries Node scripts. *Against:* the kit's own
  scripts are bash, and a file in the template is copied into every site, where it ages.
- **D3. Where it lives.** *Decided:* in the site template, called from
  `CLOUDFLARE_FIRST_DEPLOY.md` B. *Against:* a script in the kit, run against a site's
  folder, is always the newest version; `whats-new` would otherwise have to track it.
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
  check on a real pull request (scenario 4). *Against:* a new site may have no open pull
  request; the script would have to ask for an empty one, which is noise in the history.

## Review trail

None yet. The PLAN gate (Normal depth) runs when step 2 is done.
