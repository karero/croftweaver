# The move: from a Pages project to a Worker

`scripts/move-to-workers.mjs` moves a live site's domain from its Cloudflare Pages project to
its Worker, checks that nothing a visitor can see has changed, and gives the domain back to
Pages if you ask. It needs Node 18 or newer and nothing from npm. It never pushes to GitHub:
you push the one commit it writes.

A site whose domain is not yet on its Pages project has nothing to move: it launches first, as
`CLOUDFLARE_FIRST_DEPLOY.md` says. Before the User makes a token, read the address in
`SITE.url` in `src/config.ts` and look up its name servers (`dig NS <domain> +short`): if they are not
Cloudflare's, the domain's DNS is elsewhere and the site launches first.

This page tells an assistant when to run each command. It is not the User guide: that is
`docs/MOVE-TO-WORKERS.md` in the Croftweaver folder.

## Where it is, and how to run it

The script belongs to the `new-website` skill: `skills/new-website/scripts/move-to-workers.mjs`
in the Croftweaver folder, and `$SKILLS_ROOT/new-website/scripts/move-to-workers.mjs` in the
installed skill (see `CLOUDFLARE_CHECK.md` for where `$SKILLS_ROOT` is). A scaffolded site does
not carry a copy. Run it **in the site's folder**, on a clean checkout of the live branch:

```bash
node "$SKILLS_ROOT/new-website/scripts/move-to-workers.mjs" check
```

Run it on one computer only. Its state lives under `~/.config/croftweaver/moves/` on that
computer, and a second computer would not know the move had begun.

## The five stages

1. **Prepare (not this script).** The Worker must already serve the live commit, with no domain
   yet. That means: the site's shared files are current; `functions/go/` is gone; the privacy
   text is true on both platforms (it names Cloudflare, not Pages); and the site has exactly one
   Workers config (a `.json` or `.jsonc` that holds `assets` and no `pages_build_output_dir`) with
   `workers_dev: false`, `preview_urls: true`, `not_found_handling: "404-page"` and no domain
   routes. `astro.config` should not set the sitemap's `lastmod` to the build time
   (`lastmod: new Date()`): two builds of one commit would serve two sitemaps and `record` would
   stop on their bodies. Remove the line or give a fixed date. `check` warns about that one form
   and goes on; it is a guess, so it can miss one or warn needlessly. When `record` stops on
   sitemap bodies alone, its refusal names this cause. All of it is merged to the live branch. The Worker itself is made as
`CLOUDFLARE_FIRST_DEPLOY.md` says for a new site: connected to GitHub with Workers Builds
(B; the setup script, S, says how and reads the Worker once a build has made it), which then builds each push.

   With analytics on (`USE_ANALYTICS = true` in `src/config.ts`), stage 1 has one more step.
   The `enabled:` line in `src/config.ts` must read as the 0.35 starter's does, on one line:

   ```ts
   enabled: USE_ANALYTICS && (process.env.CF_PAGES_BRANCH ?? process.env.WORKERS_CI_BRANCH) === PROD_BRANCH,
   ```

   Workers Builds sets `WORKERS_CI_BRANCH`, not `CF_PAGES_BRANCH` (seen on real runs:
   `templates/astro/tests/fixtures/workers-builds-2026-11-08.txt`). A site made before 0.35
   reads `CF_PAGES_BRANCH` only. `src/config.ts` is the site's own file, so an update does not
   change the line: change it by hand and ship it with the rest of stage 1. The 0.35
   `tests/check_analytics_gate.sh` fails until it is changed. Left as it is, a Worker that
   Workers Builds builds serves its pages without analytics, so `record` stops on their body
   difference. `check` lists a gap when the `ANALYTICS` object's `enabled:` line reads
   `CF_PAGES_BRANCH` and no other variable. A site built some other way may read its own
   build's variable beside it; `check` lets that pass, but the analytics gate refuses any
   variable other than these two, so build such a site with its own variable set and check that
   the built pages carry the analytics tag. `check` refuses when it cannot tell whether analytics
   is on, and when `src/config.ts` holds a block comment (`/* … */`) or a template string over
   more than one line or inside another's `${…}`: turn the one into `//` comments, keep the other on one line and on its own. It reads the
   `enabled:` property only alone on its line or lines, with no template string, no slash and no
   backslash in it, each variable read as `process.env.NAME`, and no `...` spread in the object. A site
   with no `USE_ANALYTICS` line at all counts as on; since the new line names it, add
   `export const USE_ANALYTICS = true;` above it too.
   With analytics off, leave the line alone.
2. **Freeze and record.** `check` and `record`. Run `check` before the freeze, while the User
   works through the ready list in `docs/MOVE-TO-WORKERS.md` section 6, and once more when every
   other box is ticked; its status page names `record` under "What to do next" only when stage 1
   is done. Nothing is merged or shipped from the freeze until
   `after` passes, except the commit the script writes.
3. **Switch.** `move`, and `undo` if you want to go back.
4. **Check on the domain.** `after`.
5. **Clean up (later, not this script).** Delete the token if you will not undo soon; an undo
   later needs a new one, made the same way. Keep the Pages project 14 days in
   case you want `undo`, then retire it as a step of its own. Only then do
   `functions/_middleware.ts` and the Pages config go. Retiring it is **not tested yet**: this page has no steps for it, so leave the Pages project alone.

## The token

Make one token with four permissions in two policies, and an end date of 7 days: **Cloudflare
Pages Edit** and **Workers Scripts Edit** on the User's account, and **Zone Read** and **DNS Edit**
on the site's one zone. The token page is https://dash.cloudflare.com/profile/api-tokens. If the
token has no Workers Scripts permission, the script's error on the Worker domains points back to
this section. A token with Workers Scripts at Read is not stopped early (read from the code, not run): check that
the row says Edit (step 3 below).

Walk the User through the page one step at a time. These labels are as seen on 2026-11-17;
Cloudflare moves things, so search for the name if one differs:
1. My Profile → API Tokens → **Create Token**.
2. **Token name:** any name she will know again.
3. **Start from scratch** → **Start with an Account policy**. Next to **Include**, the account
   list says **All accounts**; she picks her own account instead (the script does not check
   this). In the permissions box, under Developer Platform: **Cloudflare Pages** → **Edit**,
   **Workers Scripts** → **Edit**. The row called just **Workers** next to it is the wrong one.
4. **Add new policy**, a Zone policy. Next to **Include**, the zone choice says **All zones**;
   she picks **Specific zone**, then her domain. Under DNS & Zones: **Zone** → **Read**,
   **DNS** → **Edit**.
5. **Token expiration:** **7 days**. The page starts on No expiration.
6. Before **Continue to summary**, she looks over the form: the four rows, one account, one
   domain, 7 days. Then **Continue to summary**, and the same look at the summary page. Then she
   creates the token and copies it. The summary page and what follows it were not looked at on
   2026-11-17: give no labels for them.

Say why there are two tokens: the build token has no end date and any package in a build can
read it, so it must not hold DNS Edit or Pages Edit; the move token holds them for 7 days, and the
User deletes it once she will not go back (`after` says so).

Say this plainly to the User: Pages Edit and Workers Scripts Edit reach every Pages project and
every Worker on her account. The script reads some lists across the account (her zones, her Pages projects, the DNS
export) but changes only her site: every change it sends is checked against her hosts, her
Pages project and her Worker before it goes out, and anything else is refused.

Workers Scripts Edit makes every zone of the account show up in the token's zone list; that is
expected. The script finds her zone as the one zone where Cloudflare lists DNS Edit for the
token; no other permission in any zone counts. It refuses a token with DNS Edit in more than one
zone or none, one with no end date or an end date more than 8 days out, and one that is not
active. When more than one zone has DNS Edit, the refusal shows the DNS and zone-settings
permissions Cloudflare lists there: a token made with account permissions only was listed with
DNS Edit in every zone of its account (read on 2026-11-08; which permission gave that is not
known). When `SITE.url` in `src/config.ts` gives an address, the refusal names it: if no zone the
token lists is that domain or a parent of it, the domain may not be on Cloudflare yet;
if it is a `pages.dev` or `workers.dev` address, the refusal says to launch first when the site has
no domain, and else to put the domain in `SITE.url`. A first `move` and a first `undo` also refuse
a token with less than an hour left; any other run only warns. If the token ends mid-move, make
a new one the same way and run the same command again.

Put the token in `CLOUDFLARE_API_TOKEN`, or, when the assistant's shell keeps no variable from
one command to the next, on a line `CLOUDFLARE_API_TOKEN=…` in the site's `.dev.vars`. The script
refuses a `.dev.vars` that git tracks or does not ignore. It never prints the token, and it
never gives it to a program it starts (the build, `git`).

## The order

| Step | Command | What it does |
|---|---|---|
| 1 | `check` | Reads only. Says what the move would touch and what is there now, one line for how each host answers `/build.txt` now (the Pages project's hosts, and the zone's apex and `www.` when they are not among them), and refuses a site that is not ready (below). |
| 2 | `record` | Freezes the live branch's tip and builds it apart from your working folder, then records what the live site serves. |
| 3 | `move` | Writes the route commit on your branch (local, not pushed), then asks: the end state in plain words and a code. Nothing on Cloudflare changes. Claude Code may ask before plain `move` runs: it writes the route commit (local, not pushed), the state file and the status page, and sends Cloudflare only reads (a test checks that). Ask the User once, before the day, whether to allow it. This is about the first plain `move` only; it says nothing about plain `undo`. |
| 4 | `move --confirm <code>` | After the User says yes to that question. Changes only Cloudflare, and only if HEAD already holds the route commit step 3 wrote and nothing has changed since step 3 (below): it moves each host off Pages, deletes its Pages CNAME, and attaches it to the Worker. |
| 5 | push | You push the route commit to `main` (`git push origin HEAD:main`). If a ruleset on `main` refuses it, push the commit to a branch of its own, have the User merge a pull request, then run `git fetch origin`; `after` accepts the merged commit (see "After the push"). On a two-stage site, push `production` second, only once `main` has the commit: `git fetch origin`, then `git push origin origin/main:production`. Never push both in one command. The push runs the site's own tests first (a couple of minutes on the kit), so it can look hung. If the Worker has no Workers Builds, deploy it as well, as stage 1 did, on the User's own Cloudflare login, not the move token. On a site with the starter's `scripts/deploy.sh` (a `wrangler.jsonc` with no `wrangler.json` or `wrangler.toml` beside it), switch to the live branch with the pushed commit checked out and run `npm run deploy:live`: it builds with the live branch's name set, so analytics stays on, and deploys. Otherwise, on a kit site, from the pushed commit: `CF_PAGES_BRANCH=<the live branch> npm run build` (without it, a site with analytics on has its analytics and email-tap tracking switched off; this build sets `CF_PAGES_BRANCH`, which the old `enabled:` line and the 0.35 one both read), then `npx wrangler deploy --config <the Workers config file>` (the root `.json` or `.jsonc` file with `assets` that stage 1 deployed with; its name is not always `wrangler.jsonc`). `after` fails until the Worker serves the new commit. After an `undo`, the same with the undo commit, never the route commit (`npm run deploy:live` takes the commit at the branch's tip). |
| 6 | `after` | Compares the live site with the recording and reports what differs. |

**`check` refuses** (and each refusal says what to do): a Pages project made by direct upload, or
none found for this repository; a Worker that already has a domain; more than one Workers
config; a `functions/` folder holding anything but `_middleware.ts`, or a `public/_worker.js`;
and a site in analytics server mode. Once the Worker's domain is checked, the other gaps (the
Workers config, `functions/`, `public/_worker.js`, server mode and the analytics lines)
are listed together, and after a refused token too, so one run shows what stage 1 still lacks. Every run that gets that far reads
the Workers config; the other checks are for a first move, and while a move is open they are
lifted. A site is two-stage when `PROD_BRANCH` in `src/config.ts` is `production` and
GitHub has a branch `production`; `check` then also shows whether `main` is on the live branch's
commit, and `record` refuses until it is. `check` first verifies the token and reads the branches with `git ls-remote`; of its GitHub reads, the repository's answer
comes first, and it names a private repository (and, when `gh` is missing, says where to get it); while a move is open it says which commit `after` waits for
and, when a host is not where the move ends, the command that carries it on.

**`record` takes minutes.** The build runs apart from the command and is kept under
`move-run/build/`. A run that finds no build for the commit starts one and exits 4, "The build is
not finished. Run the same command again in a minute.", and so does every run while it builds. A
run that finds the finished build goes straight on to the recording; one that finds a failed build
exits 1 and names its log. The recording itself can exit 4 too, when addresses did not answer: run
it again.

**The question (`move`) is the User's to answer.** Read her the plain lines at the top, word for
word, not a summary; the lines under "For your assistant" are for you, and you read them to her
when she asks. She should say yes within 10 minutes (the script allows 15). Plain `undo` prints the same shape. The code changes with every fact in that end state, so a code from an earlier
question will not fit a later one: a wrong code asks again and changes nothing.

## Exit statuses

| Status | Means | What to do |
|---|---|---|
| 0 | Finished. | Go to the next step. |
| 1 | Something failed or was refused. | Read the report. It says what, and where each host is now. Two cases need no change from you: a `--confirm` run more than 15 minutes after its plain run finishes a host that is on neither platform first, then refuses if another host is still to move; run the plain command again, then `--confirm` with the code it prints. And "GitHub could not be reached": git got no answer in 15 seconds and nothing was changed; check the connection, or try again later. |
| 2 | The command was wrong. | Fix the command. |
| 3 | Waiting for a yes. | Ask the User the question in the report. Run `--confirm <code>` only after her yes. |
| 4 | Not finished. | Run the same command again. At once after a switch that stopped part way, or left a host unstarted for lack of time; after a minute if the report names a build; in the seconds the report names if it names GitHub's pause (30 seconds at most). Only a plain `move`, `undo` or `after` meets that pause: a `--confirm` run reads no GitHub. At the time limit, the report names the call it stopped at and, while it reads addresses, how many are kept: run again while that number grows. If it stops growing, or runs keep stopping at the time limit, check the connection, or try again later. |

A run lasts at most about a minute. The switch is built for that.

- **The plain `move` or `undo` reads everything once**: every page of the Pages deployments and the
  check runs of the commits in range. It refuses on an unfinished build. When it passes, it keeps
  in the state file what it saw: how many deployments there are, the newest one's id, the tips of
  the branches on GitHub, and the time.
- **`--confirm` checks that nothing changed since.** It reads page 1 of the deployments and the
  branch tips (one `git ls-remote`), no check runs, and compares them with the plain run's record.
  If the count, the newest deployment or a tip differs, or the plain run is more than 15 minutes
  old, it changes nothing and says to run the plain command again, then confirm. A host that is on
  neither platform is finished first however old the record is; if another host is still to change,
  the run then refuses. When no host is left to change, the run finishes with the difference printed
  as a warning: `after` reads the builds again before it compares.
- **Between the plain command and its confirm, don't re-run a build or deploy by hand.** A re-run
  changes none of the four values the confirm compares. `after` catches one that put a host back, or
  one still building, but it should not have to.
- **A host is started only with its longest time left in the run**: 45 seconds (five requests at
  their slowest, and some slack). If the run's own reading leaves no room for one host that is
  still on its platform, the run refuses before any host leaves and says how long the reading
  took: do that move by hand in the Cloudflare dashboard. A host on neither platform that does not
  fit ends the run with status 4 at once, and the next run starts it with its whole time; if that
  repeats, finish it by hand. Any other host that does not fit is left for the next run.
- **Records are asked for by host name**, one page each, whatever the zone holds. A host with more
  than 100 records, or an answer holding another name, stops the run: that move is for the dashboard.
- The reads before the first host run several at a time.

If a change fails, the run stops at once, reads the host back and says whether it is on Pages, on
the Worker or on neither; **run the same command again at once**, because a host on neither is
down. Each host is down from the moment it leaves its platform until the other serves it: a few seconds going
forward, one to two minutes going back (63 to 98 seconds in the tests). 15 minutes is the target, not a promise; past it the report says to go back.

## After the push

`after` reads the tips of the branches on GitHub. `main` must be the commit of the last
`move --confirm` or `undo --confirm` (that commit says which way the hosts should be: the route
commit means on the Worker, the undo commit means back on Pages), or a pull request's merge of it:
a commit with that commit's files and the same first parent. From then on `after` waits for that
merged commit everywhere. On a two-stage site `production` must reach the same commit; if it is
behind `main`, `after` prints the `production` step, and if it is not behind `main` (the route
commit pushed there before a squash merge), `after` says to ask for help. When the merged commit is
not the route commit, `move` and `undo` must run from it (`after` prints how to bring the folder's
`main` there: `git fetch origin`, `git switch main`, `git reset --keep <commit>`). The commit of a plain `move` or
`undo` that nobody confirmed counts only when every host already sits where it points, as when the
steps were done by hand. No build of Pages or Workers Builds may be unfinished. Where Workers
Builds is connected (any commit since the last pass has one of its check runs), a pushed branch tip
it has not reported on yet counts as unfinished too. A Workers Builds check run was seen in progress
while its build ran; when it first appears after a push is not known. Once a run is completed it
counts as finished whatever its conclusion: `after` does not read the conclusion; what it does compare is the
commit line in `/build.txt` with the expected commit; a difference reads "the site serves A; B is
expected". GitHub's `started_at` of a run equals its
`completed_at`, so the script does not use it. `after` then reads where Cloudflare puts each host (a
Pages domain counts once the project's domain list shows it `active`: the list shows a new domain at
once as `initializing`, later `pending`; while it shows either, `after` exits 4: run it again in a
minute. That wait has not been seen live: in the one live undo both domains were active by the first
`after`. A host serves Pages while its domain is still `pending`, so the serving wait of `move` and
`undo` can pass first) and which platform
answers it (`/build.txt`); a host that Cloudflare lists on the Worker but Pages still answers
fails. The serving wait (two good answers in a row) belongs to `move` and `undo`, not to `after`.
`after` compares the live site with the recording. Differences the platforms are known to make are
listed as known; every difference between the live domain and the recording that the script does
not know fails `after`, among them a `noindex` or an `x-robots-tag` the recording did not have. It
also checks that `http://` redirects to `https://`, on the host the recording went to.
It keeps its answers in the state file, so a large site is finished over several runs; an address
that did not answer is asked for again (exit 4, up to three runs) before it counts as a difference.
`record` does the same.

A host that a zone Redirect Rule answers on every address (usually `www`, sent to the apex) is
recorded as that redirect. It is compared only with itself, never with the Worker's version URL.
It counts as serving when it answers its recorded status and Location, and Cloudflare's lists say
which platform has it.

## Going back

`undo` is the same shape as `move`: `undo` writes the undo commit on your branch (local, not
pushed) and asks; `undo --confirm <code>` changes only Cloudflare and refuses unless HEAD holds
that commit: each host leaves the Worker and goes back to the Pages project with its CNAME. Push
the commit as in step 5 of the table (`main` first, then `production` on a two-stage site), and where the Worker has
no Workers Builds, deploy it as well, from the undo commit and the same way as in step 5: otherwise
the Worker keeps serving the old commit and `check` says so. Then run `after`; it closes the move when the hosts serve from Pages again. A move that
stopped can be undone the same way, by hand if need be: `after` follows the commit, so it closes
either. If an undo stops part way, `move` goes forward again from where it stopped. If `main` is protected and the route commit went in as a squash merge, an `undo` after anything else was merged into `main` can stop and say to ask for help (then tell the User that going back needs help). Ordinary commits
shipped meanwhile, a changed compatibility date among them, do not stand in the way: the commit the
script writes changes the routes and nothing else, and it refuses a HEAD that changed the routes
together with something else.

Once an undo has started, never deploy the route commit: a Workers build of it attaches the hosts
to the Worker again. One exception: if an undo failed with a host on neither platform, going
forward is the way out, and that deploys the route commit.

## The status page

After every run that gets as far as the site's folder (a folder without git, or without a GitHub
`origin`, gets none) the script writes `move-run/status.html` in it. A run that stops before it has
read the state file (a token, zone or GitHub problem) writes the page too, but marks no stage. Open it in a
browser for the stages, the hosts, what the run checked, the differences nobody expected, what
to do next and how to go back. It is a local file from a template. It loads nothing from the
network, and `move-run/` is ignored by git. Tell the User where it is.

## Afterwards, by hand

- Once `after` passes, delete the token if you will not undo soon: https://dash.cloudflare.com/profile/api-tokens.
  The move stays open for `undo` while the Pages project is kept, and an undo later needs a new
  token, made the same way. After an `undo` that `after` has closed, delete the token.
- Look at the live site once in a browser.
- Wait 14 days before retiring the Pages project; that is a step of its own, not this script,
  and **not tested yet**: until a later kit release gives the steps, keep it.
