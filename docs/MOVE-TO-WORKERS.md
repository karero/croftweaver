# Moving your site from Cloudflare Pages to a Worker

For the owner of a Croftweaver site that is live on Cloudflare Pages. Your assistant does most of
the work with a script, `move-to-workers.mjs`; this page says what you decide, do and see. Your
assistant's own rules are in
[`CLOUDFLARE_MOVE.md`](../skills/new-website/references/CLOUDFLARE_MOVE.md) (see the last section).

## 1. Is this for you?

It is if your site is live on your own domain and Cloudflare looks after that domain's DNS.
Launch first if either is not so (a site not yet launched goes on a Worker before it launches;
`CLOUDFLARE_FIRST_DEPLOY.md` says how):

- The site has only a `pages.dev` address.
- The domain's DNS is with another provider. Before you make a token, your assistant reads
  the address in `src/config.ts` and looks up the domain's name servers.

A site published from your computer instead of from GitHub (a Pages project made by direct
upload) cannot move this way. The script refuses it, but only after it has read your token.
So look in the dashboard before you make one: the Pages project must be built from a GitHub
repository (the label's wording is not checked).

You do not have to move. A Pages site keeps working.

## 2. What changes, and what does not

Visitors see the same pages. A Worker that runs no code of its own, which is how the 0.35
starter is built, has no daily limit to hit: Cloudflare states that requests for static files
are free and unlimited (https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/; the kit has not counted this on a live site), where the old starter's
middleware made every request count against the free plan's daily limit. Your site's preview
address changes from a `pages.dev` address to a `workers.dev` one. You can go back (section 8).

## 3. What it takes

- **Your time.** A token, a few dashboard clicks, a yes, and a look at the site. Your
  assistant does the rest.
- **The recording.** Your assistant records what your site serves now. It takes minutes, in
  several runs.
- **Downtime.** A probe that asked for the site about every 2 seconds saw no failed answer
  during the switch in the tests (throwaway sites), and one failed answer in the live move.
  Going back, the site was down 63 to 98 seconds in the tests, and steady after about 2.5
  minutes in the slowest. The switch itself took 5 seconds in the live move.
- **The push.** A couple of minutes where the site runs its tests before a push.

## 4. Which model to use

Use your assistant's strongest model for the whole move, from preparing to the last check. It
reads you the question and helps you decide whether to go back. In Claude Code, that is Opus;
in Codex or Antigravity, the strongest model it offers.

## 5. Before the day: your assistant prepares the site

Your assistant does this ("stage 1" in `CLOUDFLARE_MOVE.md`) and merges it to your live branch:

- Brings in the update's files for a move, and removes the email-tap code (`functions/go/`).
- Makes the privacy page true on both platforms (it names Cloudflare, not Pages).
- Sets up a Worker that serves your live site and has no domain yet.
- With analytics on, changes the `enabled:` line in `src/config.ts` if it reads `CF_PAGES_BRANCH`
  alone (the old starter's line). The script refuses the move until it does. A line that also
  reads another variable stays. It checks that the Worker's live build turns analytics on,
  and asks you if it is unsure.

**You do two things.**

- **Connect the Worker to GitHub** in the dashboard, with the steps in
  [`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md),
  "B. GitHub Workers Builds, by hand". Cloudflare then builds each push. For a site with a
  `production` branch, set that as the Worker's production branch. The build's token is made
  with "Create new token" in the Worker's Build settings, then cut down in place on your
  profile page, as that section lists. Anything that runs in a build can read it, and Workers
  Scripts Edit reaches every Worker in your account. The kit has not yet shown that this token
  set is enough for a build (not checked): if the Worker's first build fails on a permission,
  your assistant stops and tells you.
  **If you already run other Workers in this account, tell your assistant before you go on.**
  The kit advises a separate Cloudflare account for a new site, but the script works in the
  account that holds your domain, so a live site cannot use one. Go on only if you accept that
  reach.
- **Export your DNS records:** your domain, DNS → Records → Import and Export → Export. Keep
  the file outside the site's folder.

Do not delete the script's state file,
`~/.config/croftweaver/moves/<domain>/<owner>-<repo>/state.json`, or its lock beside it.

## 6. Your token

You make one token for the move, at https://dash.cloudflare.com/profile/api-tokens:

- **Zone Read** and **DNS Edit**, on your one domain.
- **Cloudflare Pages Edit** and the Workers permission, on your account. The token page showed
  it as Workers Scripts, set to Edit, in the kit's own moves; Cloudflare's wording may differ,
  and the script's error says so if the token lacks it.
- An end date within a week.

Pages Edit and the Workers permission reach every project and Worker on your account; the
token's zone list also shows every zone, which is expected. The script reads some lists across
your account (your zones, your Pages projects, and your domain's DNS records, which it keeps as
a backup), but it changes only your site: every change it sends is checked against your hosts,
your Pages project and your Worker before it goes out, and anything else is refused.

You make it; your assistant puts it where the script reads it (a variable for the session, or
a `.dev.vars` file that git ignores). It never goes in a file git tracks. Delete it afterwards
(section 10).

## 7. On the day

1. **Freeze.** Make no change to the site from the recording until the last check passes. Tell
   anyone else who edits it.
2. **Record.** Your assistant runs `check`, then `record`, more than once.
3. **The question.** Your assistant reads you the move's end state, word for word, and a code.
   Say yes only if it is what you want. Your yes and the move's prompt must come within 15
   minutes of the question, or your assistant asks again before it starts another host. (A
   host that a stopped move left down is finished first, whatever the time.)
4. **Prompts.** Your assistant's own permission prompts come before the move, the push and any
   deploy. They may describe DNS and domain changes: read them before you approve.
5. **The move.** Each run lasts about a minute at most, so a move with several hosts can take
   more than one run. Then the push, then the check, `after`.

`move-run/status.html` in the site's folder shows where the move stands. Open it in a browser.

## 8. Going back

Choose it if the check fails and the fix is not quick, or the site looks wrong. Tell your
assistant: "go back". It writes an undo commit, reads you the end state of the undo, and waits
for your yes. Each host is down from the moment it leaves the Worker until Pages serves it
again, about a minute; the tests saw up to 98 seconds. Then it pushes the undo commit and runs
`after`. You can move again later (not run in a test yet).

## 9. If a run stops part way

Your assistant runs the same command again at once: a site between platforms is down. Then:

- **The script says to do the move by hand and that nothing was changed.** Every host may still
  be on Pages, and your site works. Your assistant runs plain `undo`. If it says "No move is
  open, so there is nothing to undo", the move never began: the route commit it wrote stays
  local, nobody pushes it, and your assistant stops. This guide has no move by hand. If `undo` goes on, an
  earlier `--confirm` run had begun the move: go back (section 8; not run in a test).
- **A host has moved:** go back with the script (section 8).
- **A host has a record that is not its CNAME:** the script says "delete it by hand". Nobody
  deletes it: your assistant names the record to you and stops. The host may be down while it
  waits, and the record is yours to decide on.
- **If an undo stops with a host on neither platform,** your assistant may go forward with the
  script instead, as `CLOUDFLARE_MOVE.md` says (not run in a test), and tells you which it does.
  If that fails too, it stops and tells you where each host is.
- **The script says to do the undo or finish a host by hand, a host is on both platforms
  ("look at it in the dashboard"), or a host stays down:** go back by hand.

**Going back by hand.** Once you start, no `--confirm` runs, and nobody touches the state file
or its lock. Dashboard labels are as seen on 2026-11-05; Cloudflare moves things, so search for
the name if one differs.

1. Your assistant runs `check` and reads you, for each host, where it is, its address records
   (A, AAAA, CNAME) and both project names, saying which is the Pages project and which is the
   Worker. You check that nothing is queued or building: Workers & Pages → the Pages project
   → Deployments, and the Worker's builds. A late build can move a host back.
2. Your assistant runs plain `undo`. It writes the undo commit and ends with a question and a
   `--confirm` code; here that question goes unanswered, and the status page's "waiting for your
   yes" is wrong. If it refuses over the token, make a new one the same way. If it names a build or
   says to run it again, your assistant waits as it says and runs it again; for anything else
   ("Another run … holds" among them), stop. Start step 3 only when your assistant tells you the undo commit is written.
3. For each host: take it off the Worker (Workers & Pages → the Worker → Settings → Domains),
   add it to the Pages project's Custom domains (Workers & Pages → the Pages project → Custom
   domains), and add a proxied CNAME to `<project>.pages.dev` only if the host has none
   (your domain → DNS → Records). Delete nothing. If the host has any other A, AAAA or CNAME
   record, stop. Wait for "active".
4. Your assistant pushes the undo commit and deploys, as `CLOUDFLARE_MOVE.md` says. If GitHub
   refuses the push it deploys nothing and stops; press no "Retry build" in Workers Builds. Then
   it runs `after`. If `after` says a branch is "not the undo commit … push it", push the undo
   commit and run `after` again. If it says "not the route commit … push it", do not push the route
   commit and deploy nothing: stop and tell the owner.

Not checked: whether taking a host off the Worker leaves a record behind. The steps leave out
going forward by hand.

## 10. Afterwards

- Delete the token unless you may go back soon: https://dash.cloudflare.com/profile/api-tokens.
  An undo later needs a new one.
- Look at the site once in a browser.
- Keep the old Pages project. Retiring it is **not tested yet**: leave it until a later kit
  release gives the steps.

## 11. For your assistant

Read [`CLOUDFLARE_MOVE.md`](../skills/new-website/references/CLOUDFLARE_MOVE.md): in the
Croftweaver folder it is `skills/new-website/references/CLOUDFLARE_MOVE.md`; in an installed
skill, `$SKILLS_ROOT/new-website/references/CLOUDFLARE_MOVE.md`. It has the order of commands,
the exit statuses and every refusal.
