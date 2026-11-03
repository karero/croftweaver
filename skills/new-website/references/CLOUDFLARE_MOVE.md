# The move: from a Pages project to a Worker

`scripts/move-to-workers.mjs` moves a live site's domain from its Cloudflare Pages project to
its Worker, checks that nothing a visitor can see has changed, and gives the domain back to
Pages if you ask. It needs Node 18 or newer and nothing from npm. It never pushes to GitHub:
you push the one commit it writes.

This page tells an assistant when to run each command. It is not the User guide.

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
   text says Workers; and the site has exactly one Workers config (a `.json` or `.jsonc` that
   holds `assets` and no `pages_build_output_dir`) with `workers_dev: false`,
   `preview_urls: true`, `not_found_handling: "404-page"` and no domain routes. All of it is
   merged to the live branch.
2. **Freeze and record.** `check`, then `record`. Nothing is merged or shipped from here until
   `after` passes, except the commit the script writes.
3. **Switch.** `move`, and `undo` if you want to go back.
4. **Check on the domain.** `after`.
5. **Clean up (later, not this script).** Delete the token. Keep the Pages project 14 days in
   case you want `undo`, then retire it as a step of its own. Only then do
   `functions/_middleware.ts` and the Pages config go.

## The token

Make one token on the site's one zone: **Zone Read** and **DNS Edit** on that zone; **Cloudflare
Pages Edit** and the Workers permission that custom domains need, both on the account; and an
end date within a week. The token page is
https://dash.cloudflare.com/profile/api-tokens. (The Workers permission's exact name is not
checked yet; the script's error says so if the token lacks it.)

Say this plainly to the User: Pages Edit and the Workers permission reach every project on her
account. The script keeps to her site: every request it sends is checked against her hosts, her
Pages project and her Worker before it goes out, and anything else is refused.

The script refuses a token that reaches more than one zone, one with no end date or an end date
more than 8 days out, and one that is not active. A first `move` and a first `undo` also refuse
a token with less than an hour left; any other run only warns. If the token ends mid-move, make
a new one the same way and run the same command again.

Put the token in `CLOUDFLARE_API_TOKEN`, or, when the assistant's shell keeps no variable from
one command to the next, on a line `CLOUDFLARE_API_TOKEN=…` in the site's `.dev.vars`. The script
refuses a `.dev.vars` that git tracks or does not ignore. It never prints the token, and it
never gives it to a program it starts (the build, `git`).

## The order

| Step | Command | What it does |
|---|---|---|
| 1 | `check` | Reads only. Says what the move would touch and what is there now, and refuses a site that is not ready (below). |
| 2 | `record` | Freezes the live branch's tip and builds it apart from your working folder, then records what the live site serves. |
| 3 | `move` | Writes the route commit on your branch (local, not pushed), then asks: the end state in plain words and a code. Nothing on Cloudflare changes. |
| 4 | `move --confirm <code>` | After the User says yes to that question. Changes only Cloudflare, and only if HEAD already holds the route commit step 3 wrote: it moves each host off Pages, deletes its Pages CNAME, and attaches it to the Worker. |
| 5 | push | You push the route commit to the live branch; on a two-stage site, to `main` too (`git push origin HEAD:production HEAD:main`). If the Worker has no Workers Builds, deploy it as well. |
| 6 | `after` | Compares the live site with the recording and reports what differs. |

**`check` refuses** (and each refusal says what to do): a Pages project made by direct upload, or
none found for this repository; a Worker that already has a domain; more than one Workers
config; a `functions/` folder holding anything but `_middleware.ts`, or a `public/_worker.js`;
and a site in analytics server mode. These checks are for a first move; while a move is open
they are lifted. A site is two-stage when `PROD_BRANCH` in `src/config.ts` is `production` and
GitHub has a branch `production`; `check` then also shows whether `main` is on the live branch's
commit, and `record` refuses until it is. `check` reads GitHub's answer for the repository first and names a private repository (and, when
`gh` is missing, says where to get it); while a move is open it says which commit `after` waits for
and, when a host is not where the move ends, the command that carries it on.

**`record` takes minutes.** The build runs apart from the command. While it runs, `record`
exits 4: run the same command again until it finishes.

**The question (`move`) is the User's to answer.** Read her the printed end state, not a
summary of it. The code changes with every fact in that end state, so a code from an earlier
question will not fit a later one: a wrong code asks again and changes nothing.

## Exit statuses

| Status | Means | What to do |
|---|---|---|
| 0 | Finished. | Go to the next step. |
| 1 | Something failed or was refused. | Read the report. It says what, and where each host is now. |
| 2 | The command was wrong. | Fix the command. |
| 3 | Waiting for a yes. | Ask the User the question in the report. Run `--confirm <code>` only after her yes. |
| 4 | Not finished. | Run the same command again. At once after a switch that stopped part way; after a minute if the report names a build; in 30 seconds if it names GitHub's pause or too little time left in the run. |

A run lasts at most about a minute. The switch is built for that: a host is started only
with 45 seconds left in the run; if its changes cannot finish in the time left, the run stops
cleanly, says which hosts have already left their platform, and the next run carries on. If a change fails, the run stops at once, reads the host back and says
whether it is on Pages, on the Worker or on neither; **run the same command again at once**,
because a host on neither is down. Each host is down from the moment it leaves its platform until
the other serves it: about a minute. 15 minutes is the target, not a promise; past it the report
says to go back.

## After the push

`after` reads the tips of the branches on GitHub. They must equal the commit of the last
`move --confirm` or `undo --confirm` (that commit says which way the hosts should be: the route
commit means on the Worker, the undo commit means back on Pages). The commit of a plain `move` or
`undo` that nobody confirmed counts only when every host already sits where it points, as when the
steps were done by hand. No build of Pages or Workers Builds may be unfinished. Where Workers
Builds is connected (any commit since the last pass has one of its check runs), a pushed branch tip
it has not reported on yet counts as unfinished too. Not checked yet: whether Workers Builds posts
its check run before it deploys; the trial move settles it. `after` then reads where Cloudflare puts each host and which platform
answers it (`/build.txt`); a host that Cloudflare lists on the Worker but Pages still answers
fails. The serving wait (two good answers in a row) belongs to `move` and `undo`, not to `after`.
`after` compares the live site with the recording. Differences the platforms are known to make are
listed as known; everything else is listed as unexpected, and a `noindex` on the domain is a
failure. It also checks that `http://` redirects to `https://`, on the host the recording went to.
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
the commit, then run `after`; it closes the move when the hosts serve from Pages again. A move that
stopped can be undone the same way, by hand if need be: `after` follows the commit, so it closes
either. If an undo stops part way, `move` goes forward again from where it stopped. Ordinary commits
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

- Delete the token once `after` passes: https://dash.cloudflare.com/profile/api-tokens.
- Look at the live site once in a browser.
- Wait 14 days before retiring the Pages project; that is a step of its own, not this script.
