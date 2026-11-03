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
| 3 | `move` | Asks. Prints the end state in plain words and a code. Changes nothing. |
| 4 | `move --confirm <code>` | After the User says yes to that question. Writes the route commit, then moves each host: off Pages, its Pages DNS record deleted, onto the Worker. |
| 5 | push | You push the route commit to the live branch; on a two-stage site, to `main` too (`git push origin HEAD:production HEAD:main`). If the Worker has no Workers Builds, deploy it as well. |
| 6 | `after` | Compares the live site with the recording and reports what differs. |

**`check` refuses** (and each refusal says what to do): a Pages project made by direct upload, or
none found for this repository; a Worker that already has a domain; more than one Workers
config; a `functions/` folder holding anything but `_middleware.ts`, or a `public/_worker.js`;
and a site in analytics server mode. These checks are for a first move; while a move is open
they are lifted. On a two-stage site (a Pages `wrangler.toml` beside `workers.jsonc`) `check`
also shows whether `main` is on the live branch's commit, and `record` refuses until it is.

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
| 4 | Not finished. | Run the same command again at once. |

A run lasts at most about a minute. The switch is built for that: if a host's changes cannot
finish in the time left, the run stops cleanly and the next run carries on. If a change fails,
the run stops at once, reads the host back and says whether it is on Pages, on the Worker or on
neither; **run the same command again at once**, because a host on neither is down.

## After the push

`after` reads the tips of the branches on GitHub. They must equal the route commit, and no build
of Pages or Workers Builds may be unfinished. The Worker then has to serve the host with the
route commit, twice in a row. After 15 minutes without that, the report says to undo. `after`
then compares the live site with the recording. Differences the platforms are known to make are
listed as known; everything else is listed as unexpected, and a `noindex` on the domain is a
failure. It also checks that `http://` goes to `https://`.

## Going back

`undo` is the same shape as `move`: `undo` asks, `undo --confirm <code>` gives each host back to
the Pages project and writes a commit that removes the routes. Push it, then run `after`; it
closes the move when the hosts serve from Pages again. If an undo stops part way, `move` goes
forward again from where it stopped.

## The status page

After every run the script writes `move-run/status.html` in the site's folder. Open it in a
browser for the stages, the hosts, what the run checked, the differences nobody expected, what
to do next and how to go back. It is a local file from a template. It loads nothing from the
network, and `move-run/` is ignored by git. Tell the User where it is.

## Afterwards, by hand

- Delete the token once `after` passes: https://dash.cloudflare.com/profile/api-tokens.
- Look at the live site once in a browser.
- Wait 14 days before retiring the Pages project; that is a step of its own, not this script.
