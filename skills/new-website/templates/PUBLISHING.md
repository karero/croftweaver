# Publishing your site — a plain-English guide

This explains how your changes get onto the internet. **No prior git knowledge needed** —
read the glossary once, then follow the steps for your site's model.

---

## The five words you'll see (in plain English)

| Word | What it actually means |
|---|---|
| **commit** | **Save a snapshot** of your changes on your own computer, with a short note describing them. Nothing is online yet — it's like saving a document. |
| **push** | **Upload** your saved snapshots to GitHub (the cloud). On most sites this is what triggers a build (not on one that deploys by command, see "Deploy by command"). |
| **branch** | A **named line of work**. Your site has up to two: `main` and (sometimes) `production`. Think of them as "the draft" and "the published version." |
| **checkout** | **Switch** which branch you're looking at / working on. `git checkout main` = "show me the draft." |
| **merge** | **Copy the changes** from one branch into another — e.g. take everything in `main` and bring it into `production` to publish. |

A normal edit is always the same three moves: **commit** (save) → **push** (upload) →
the site rebuilds automatically (except on a site that deploys by command, see "Deploy by
command"). The only question is *which branch* you push to, and that's
what your model below decides.

---

## Which model is your site? (check your README)

Your site uses **one** of these. If you're not sure, your README's "Deploy" section says
which, or just look at your branches: only `main` = single-stage; `main` **and**
`production` = two-stage. One more case: if your site isn't connected to GitHub in
Cloudflare, a push publishes nothing. See "Deploy by command" below.

---

## Two-stage (recommended) — "preview first, then publish"

`main` is an **unlisted, noindexed preview**; `production` is the **live** site. You can
push freely to `main` — nothing reaches your live domain until you publish. (Search engines
are told to ignore the preview, but it isn't password-protected: **anyone who has the preview
URL can open it.** Don't put confidential content on a preview unless the project is behind
Cloudflare Access or similar.)

**Every time you change the site:**

```bash
# 1. Save your changes (a snapshot + a short description)
git add -A
git commit -m "describe what you changed, e.g. update opening hours"

# 2. Upload them — this builds your NOINDEXED PREVIEW (not on the live domain yet)
git push

# 3. Look at the preview. Open the preview link from Cloudflare (a Worker's looks like
#    https://<prefix>-<worker>.<account>.workers.dev; your assistant can read it off the
#    build in Cloudflare) and check it's right.
#    If your site is still on Pages: main.<your-project>.pages.dev; if Cloudflare gave the
#    project an address other than its name, use the one on the project's page.

# 4. Happy? Publish it to the live site — ONE command:
npm run ship
```

`npm run ship` uploads `main` to the live (`production`) branch for you — you never run the
branch commands by hand. Before it uploads, it lists the commits that go live, newest first.
It names the site first. Run in a terminal window with its output on screen, it then asks you
to type y before it uploads. Where it has no terminal window to ask in, or its output goes to
a file, it says it is not asking and goes on.
Then it **waits and verifies** that the live site really serves the
new version (every build stamps its id into `/build.txt`; ship polls for it, about 6 min).
"✓ LIVE — verified" means it's truly online; a warning means the new build isn't live yet:
it may still be running, or Cloudflare didn't build — the message tells you what to check.
Never assume a push went live without that check.

Before your site has its own domain, `npm run ship` has nothing live to check: it says the
change was sent, and that it is checked when the site launches. Look at the Preview link instead.

> **Each upload may run a quick self-check** (it builds the site and runs the tests before
> uploading — so does `npm run ship`, which uploads too). It can take a minute, and **if
> something is broken it stops the upload and tells you** rather than publishing a broken
> page. To skip the check on a *manual* `git push` you've already verified:
> `git push --no-verify`. If **`npm run ship`** stops partway, don't force it — ask for help.

> **Nothing reaches the live domain until step 4.** Steps 1–3 only update the noindexed preview.

### On a shared computer: publish GitHub's `main` instead

`npm run ship` stops when this folder isn't on `main` or has unsaved files. That protects you
from publishing while you've forgotten to save an edit. But where several people or AI
assistants work in the same folder, it's seldom tidy: someone's draft, or a branch left
checked out, blocks every publish, though none of it would have been published.

For such a folder, switch on one setting, once, in the site's folder:

```bash
git config ship.fromGitHub true
```

From then on, `npm run ship` publishes **GitHub's `main`**, from a temporary copy it makes
and removes again. The checks run on exactly what goes live, and none of the files in this
folder are built, published or changed. Unsaved files no longer block it: they're listed under "Not
published", and the last line says how many there were. So the one thing to keep in mind:
**an edit that is only in this folder doesn't go live.** Get it onto GitHub's `main` first
(a pull request, or a push), then ship. The site it names is the one on GitHub's `main`, not
the one in this folder, so it names it a moment later, once it has read GitHub.

- The setting is saved in this folder's own git settings, so it covers every copy of the site
  that shares them (an assistant's `git worktree` of it, say), and no other copy. A fresh
  copy of the site starts without it.
- Each publish installs the site's packages fresh in the temporary copy (`npm ci`), so it
  needs the internet (or packages npm has cached before) and takes a little longer.
- One publish runs at a time across this folder and every copy that shares its settings; a
  second one stops and says why.
- To see whether it's on: `git config --local --get ship.fromGitHub`. To switch it off:
  `git config --unset ship.fromGitHub`.

---

## Single-stage (simplest) — "push = live"

One branch, `main`, and it **is** the live site. There's no preview step — every upload goes
straight online (before the site has its own domain, "online" means only its Preview link;
see the box "You need a custom domain" below). Simple, but there's no safety net, so check locally first (`npm run dev`).

> **"Push = live" is a promise, not a fact.** Cloudflare can silently stop building (it
> happened in production: green pushes, no deploy). After an important upload, confirm the
> change is really online — `curl https://your-site/build.txt` shows which build is serving
> (compare with `git rev-parse HEAD`). If it's stale: Cloudflare dashboard → your Worker →
> Builds (retry the failed build). If your site is still on Pages: your project → Deployments
> (retry the failed build, or re-connect GitHub under Settings → Builds).

> **You need a custom domain for Google to see the site.** A new site has no public address
> of its own: the site's live `workers.dev` address is switched off (Preview links also end in
> `workers.dev`, and they do work), and Preview links are
> **noindexed by design** (so stray preview URLs never get indexed). Until your real domain
> is attached at launch, only Preview links show the site, and search engines ignore them.
> If your site is still on Pages: a bare Cloudflare `*.pages.dev` URL is noindexed by design,
> and once your real domain shows the new site, your assistant switches the `pages.dev` address
> to forward visitors there, so a link to it in an AI answer still brings people to your real
> domain.

**Every time you change the site:**

```bash
# 1. (Optional but wise) preview locally first
npm run dev        # opens a local copy in your browser; Ctrl-C to stop

# 2. Save your changes
git add -A
git commit -m "describe what you changed"

# 3. Upload — this goes LIVE within a minute
git push
```

---

## Deploy by command — if your site isn't connected to GitHub in Cloudflare

Some sites are uploaded to Cloudflare by command and have no GitHub connection there
(your README's "Deploy" section says if yours is one; if you're not sure, ask your
assistant). On such a site `git push` only updates GitHub. **Nothing goes online until
someone runs a command below.** (If there is no GitHub repository at all, leave out the
`git push` and `git pull` lines below: save with `git add -A` and `git commit`, then run the
command.)

A new site is a Worker, and has two commands. First look at your change on a **Preview**
link, which only people who have the link can open and which search engines are told to
ignore:

```bash
npm run deploy:preview
```

It builds the site as it is and prints the Preview link (of the form
`https://<prefix>-<worker>.<account>.workers.dev`). Check your change there. When it's right,
save it with `git add -A`, `git commit` and `git push` as above, then put it **live**:

```bash
# Get the newest version from GitHub, then put the site LIVE. On a two-stage site,
# your assistant first brings your change from `main` into `production`: `deploy:live`
# publishes the commit that `production` is at, nothing else.
git switch <production-branch> &&
  git pull &&
  npm run deploy:live
```

`<production-branch>` is `PROD_BRANCH` in `src/config.ts`: `main` on a single-stage site,
`production` on a two-stage one. `npm run deploy:live` stops, and changes nothing, if you're on
another branch or any file is unsaved, so that what goes live is exactly a saved commit. It
builds the site for the live address (that is what switches your visitor statistics on, once
they are switched on: `USE_ANALYTICS = true` in `src/config.ts`; a new site has them off) and
then checks that the live address serves this version (before your site has its own
domain there is no live address, and it says so).

The `&&` means each line runs only if the one before it worked. If `git` or the build stops
with an error, nothing was uploaded: ask for help rather than running the upload on its own.
If the upload itself shows an error, part of it may have gone live anyway: ask for help
before running it again. The first time, `npx` may ask "Ok to proceed?": type `y`. If the
command says you aren't logged in, run `npx wrangler login` once (it opens your browser so you
can log in to Cloudflare), then run it again. If it says "Failed to automatically retrieve
account IDs" (this happened with a Cloudflare token that could not look up the account), ask
your assistant to give it your account id (`CLOUDFLARE_ACCOUNT_ID`), then run it again.
On Windows, run it in Git Bash or WSL.

**If your site is still on Pages and is uploaded by command** (no GitHub connection in
Cloudflare) it has no preview step, and `npm run ship` is not for it either: it waits for
Cloudflare to build, and on such a site Cloudflare never does. Run the
commands below instead. They publish `main`, so first check your change locally (`npm run dev`),
then save and upload it on `main` with `git add -A`, `git commit` and `git push` as above.

```bash
# Get the newest main from GitHub, build the site, then upload it to Cloudflare.
# One command over four lines: copy all of it. The last line puts the site LIVE.
git switch main &&
  git pull &&
  CF_PAGES_BRANCH=<production-branch> npm run build &&
  npx wrangler pages deploy dist --project-name <your-project> --branch <production-branch>
```

`<your-project>` is your site's project name in Cloudflare. `<production-branch>` is the
branch the project was created with: `main` on a single-stage site, `production` on a
two-stage one. You upload from `main` either way: with no preview step, `main` holds the
change you just checked and saved. Put the same branch name in both places, and leave both in:

- `CF_PAGES_BRANCH=` lets your visitor statistics run on the live site, once they are
  switched on (`USE_ANALYTICS = true` in `src/config.ts`; a new site has them off). With
  them on and this left out, the live site counts no visitors, with no error to tell you.
  (It only works when the name matches `PROD_BRANCH` in `src/config.ts`. If you're not sure
  it does, ask your assistant to check.)
- Without `--branch`, the upload can land as a preview instead of on the live site.

The `&&` means each line runs only if the one before it worked. If `git` or the build stops
with an error, nothing was uploaded: ask for help rather than running the upload on its own.
If the upload itself shows an error, part of it may have gone live anyway: ask for help
before running it again. The first
time, `npx` may ask "Ok to proceed?": type `y`. If the command says you aren't logged in, run
`npx wrangler login` once (it opens your browser so you can log in to Cloudflare), then
run it again. If it says "Failed to automatically retrieve account IDs" (this happened
with a Cloudflare token that could not look up the account), ask your assistant to give
it your account id (`CLOUDFLARE_ACCOUNT_ID`), then run it again.
On Windows, run it in Git Bash or WSL.

---

## If something goes wrong

- **Mistake already live?** Don't panic — in the **Cloudflare dashboard → your Worker →
  Deployments**, every past version is listed; click an older one → **Rollback** to restore
  it instantly (labels not checked). If your site is still on Pages: **your Pages
  project → Deployments**, the same way.
- **Made a typo in the last save (not pushed yet)?** Re-edit, then
  `git add -A && git commit -m "fix typo"` again.
- **`git push` says "rejected"?** (on `main`) Someone/something updated the cloud copy — run
  `git pull` first, then `git push` again.

`npm run ship` names which of these it is, and says whether anything was published. The
ones you're most likely to meet:

- **"Couldn't reach GitHub"** or **"couldn't fetch from GitHub"?** Your internet, not your
  site. Nothing was published. Wait a moment and run `npm run ship` again.
- **"GitHub has changes that aren't on your computer yet"?** Someone (or another
  computer) saved work you don't have. Run `git pull`, look at the site, then ship again —
  publishing without it would put an **older** version live.
- **"Publish blocked — 'production' has commits that 'main' doesn't have"?** The live
  branch has history your preview doesn't. **Don't force anything** — ask for help. This
  one is rare and worth a second pair of eyes.
- **"The connection to GitHub dropped part-way through the upload"?** Genuinely unclear whether it
  landed, so the script won't guess. Just run `npm run ship` again: if it already landed,
  git says "Everything up-to-date" and the checks carry on as normal.
- **"The push failed, for a reason this script can't name"?** Read the error printed just
  above it — most often your own tests failed, and the site is fine until you fix them.
- **"Your copy and GitHub's have BOTH changed"?** You edited here, something else edited
  there. Run `git pull --no-rebase` (the flag matters — a plain `git pull` refuses to
  guess when both sides moved), and if it mentions a **conflict**, ask for help rather
  than guessing. Then `git push`, then ship.
- **"'production' moved while this was publishing"?** Rare, and harmless: something
  published between the check and the upload. Run `npm run ship` again — it re-checks
  and will tell you plainly if anything is actually wrong.
- **"'git fetch' failed, and not for a network reason"?** Not a blip — running it again
  won't help. Read git's own error printed above it; a missing connection to GitHub or
  an expired login both land here.
- **"This branch isn't connected to GitHub yet"?** A brand-new site that has never been
  uploaded. Run `git push -u origin main` once, then ship.
- **"may or may not have landed"?** The publish was stopped part-way (Ctrl-C, say), or the
  script couldn't read git's result. Run `npm run ship` again: if it already landed, git says
  "Everything up-to-date" and the checks carry on as normal.
- **"Publish stopped — you did not answer y"?** The run asked "Publish to …?" and got no y
  (or yes). Nothing was published. Run `npm run ship` again and type y when it asks.
- **"The publish went out", after a stop?** You stopped it after the upload: the site is being
  published, and only the last check was skipped. In a few minutes, open your live site's
  `/build.txt`: it shows the commit the live site serves.
- **"The site's test port was taken"?** Another test run, or a preview of the site
  (`npm run dev`), is using the port the checks need. Close it, then ship again.
- **"A newer publish followed"?** Someone published again right after you. Your live site's
  `/build.txt` shows which of the two it serves.

With `ship.fromGitHub` switched on (see "On a shared computer" above), you may also meet these:

- **"another publish holds this clone's lock"?** One publish runs at a time. If the message
  says that process is still running, a publish is under way (it may be waiting for your
  yes in another window): let it finish. If it isn't
  running (or the script can't tell), an earlier publish was stopped hard and left its lock
  behind. The message gives the command that removes it; first make sure no `git push` from
  that publish is still running.
- **"Left over from an earlier publish that was stopped hard"?** Its temporary copy is still
  there. It blocks nothing. Once nothing is working in it any more, remove it with the command
  the message gives; where the message says to check by hand, its record is damaged, so look
  at that folder yourself (or ask for help) before deleting anything.
- **"this folder's scripts/ship.sh is not the one on GitHub's main"?** The script that
  publishes has to be the one being published. Run it from a copy that is up to date with
  GitHub's `main`.
- **"installing the site's packages in the temporary copy failed"?** Read npm's error just
  above it. The install needs the internet, or packages npm has cached before.
- **"has no runnable scripts/hooks/pre-push"?** GitHub's `main` lacks the pre-push check this
  mode insists on, so it publishes nothing. Ask for help.

When in doubt, ask before you `npm run ship`, `git push` or the deploy command above — those
are the only commands that change what the public sees.

---

## In an emergency

**Something wrong is live.** The quickest way back is Cloudflare's **Rollback** ("Mistake
already live?" above). To fix it for good, undo the change on `main` (on GitHub, the pull
request that brought it in has a **Revert** button; merge the pull request it makes), then
publish as usual with `npm run ship`.

**`npm run ship` itself is broken**, and the live site needs a fix now. Publish GitHub's
`main` by hand, from the site's folder. It is one command over four lines: copy all of it.

```bash
id="$(git ls-remote origin refs/heads/main | awk '$2 == "refs/heads/main" { print $1 }')" &&
  git -c maintenance.auto=false -c gc.auto=0 fetch -q origin "${id:?}" &&
  git push --no-verify origin "${id:?}:refs/heads/production" &&
  echo "Published $id. The live site's /build.txt should show it in a few minutes."
```

It asks GitHub which commit its `main` branch points at now (that branch alone: a branch
whose name merely ends in `main` is ignored), fetches exactly that commit and publishes it.
The commit's id stays in your terminal, so nothing else that runs in this folder (an
assistant's fetch, say, or the same command in another terminal) can change which commit
goes live; nor do this folder's fetch settings, or a tag that happens to be called `main`. The
two settings keep git from tidying up while it fetches: on a shared folder, a tidy-up can drop
the record of another session's work. If GitHub can't be reached or has no `main`, nothing is
published. `--no-verify` skips the pre-push check on purpose: that
check also runs ship's own test, and ship is the part that may be broken. So nothing checks
this publish. Do it only for a `main` whose checks are green on GitHub, and never add
`--force`. A few minutes later, open your live site's `/build.txt`: it shows the commit the
live site serves, which should be the id the last line printed.

**Is the pre-push check switched on?** `git config --get core.hooksPath` prints
`scripts/hooks` when it is. Anything else, or nothing: run `npm install` once in the site's
folder, which switches it on (unless the site sits inside a bigger repository). On a shared
computer, first ask whoever else works in this folder: they may have set it their own way on
purpose. With `ship.fromGitHub` on, `npm run ship` runs the published commit's own check
whatever this setting says.

---

## For AI assistants — deploy-time guardrails

*This section is written for an AI assistant working in this repo — from here on, "you"
means the assistant. Owner: you can skim it; it explains why the assistant is careful with
links. Assistant: these rules apply to **every** publish, from the site's first deploy on,
not just while it was being built. If this file ever gets translated or rewritten for the
owner, this section must survive the rewrite — translating it is fine, dropping it is not.
The direct `git push` steps above are the OWNER's path; you work through pull requests,
per `AGENTS.md` §2.*

### Always say whether it's PREVIEW or LIVE

A non-technical owner cannot tell a preview URL from the live site. So **every time** you
push to `main` (or they do), state it explicitly — never let a preview read as live:

> ✅ Your changes are on the **preview**: `<preview link>` — **this is NOT live yet.** When it
> looks right, run `npm run ship` to publish to `<live-domain>`.

(For a Worker the preview link has the form `https://<prefix>-<worker>.<account>.workers.dev`.
For a site still on Pages it is `https://main.<project>.pages.dev`.)

Only after `npm run ship` (or the merge into `production`) **and** the Cloudflare production
build finishes is it actually live at `<live-domain>`. After `npm run ship` prints
"✓ LIVE — verified" (it polls `/build.txt` until the live site serves the new SHA), announce
it live on that result — no manual re-check needed. For a plain merge into `production` — or
when ship reports it could not verify — confirm manually before announcing ("✅ now live
at …"). On a **single-stage** site there is no preview: say plainly that the push **is
going live now**. On a site **not connected to GitHub** ("Deploy by command" above), this
rule wins over both models: a push builds nothing, not even a preview. Say the change is
saved on GitHub only, and goes live when the deploy command runs. Deliver these
announcements in the owner's language, like everything else you say to them.

**Which URL to quote.** On a Worker, quote the **preview link** of the build (the form
`https://<prefix>-<worker>.<account>.workers.dev`; read it off the build in Cloudflare), or,
for one exact version, that version's own link. A version's link is ugly but **immutable**, so
keep it as a **backup**: when the preview link looks **stale** (cache/propagation lag, or it's
still serving an older build), the version link pins the exact fresh build and confirms the new
build is up. For a **brand-new page**, though, the next section wins: until the production
build is Active, the page exists only on such a link. Whichever URL you quote, **open it and
confirm it loads** rather than reporting it blind — and note it for the project. (A deploy that
prints a `*.pages.dev` address means the site is on Pages, not a Worker; a deploy of a new site
that prints a live `*.workers.dev` address is wrong: its `workers_dev` is `false`, so stop and ask.)

*If your site is still on Pages:* where Cloudflare gave the project an address other than its
name (it does when the name is taken), use that address, from the project's page, in place of
`<project>.pages.dev` below. Prefer the **memorable `pages.dev` alias** — the branch alias
`main.<project>.pages.dev` (or, before go-live, the project alias `<project>.pages.dev` —
after go-live it redirects to the live domain) — over the random
per-deploy hash URL `<hash>.<project>.pages.dev`. The hash URL is ugly but **immutable**, so
keep it as a **backup**, in the same way.
(A `pages.dev` URL is also the signal you deployed to **Pages**, not a Worker — if a deploy
of a Pages site ever prints a `*.workers.dev` URL, stop: you published the wrong project type.)

### Never request a page on the live domain before its build is Active

The edge caches whatever it first sees. If anyone — you, the owner's browser, a link
checker — requests a brand-new path on the live domain while the production build is still
running, a zone cache rule (Cache Everything on HTML) will cache the **404**, and a cached
404 does not reliably self-heal: observed surviving `cf-cache-status: HIT` more than 90
minutes past a 30-minute `max-age`, immune to plain re-requests. Only a **manual dashboard
purge** clears it (Cloudflare dashboard → the zone → Caching → Purge Cache → custom purge by
URL; wrangler's OAuth token has `zone (read)` only and cannot purge programmatically). So:

- Until the production deployment shows **Active**, verify new pages ONLY on the version's own
  link (on Pages: the hash deployment URL `<hash>.<project>.pages.dev`) — pre-Active the live
  domain still serves the *previous* deployment, so a brand-new path 404s there no matter how
  you request it. Check Active status without touching the live domain: on a Worker, the
  build's page in Cloudflare (Workers & Pages → your Worker → Builds) or the Worker's version
  link, or ask the owner (on Pages: `wrangler pages deployment list`, or the
  `<project>.pages.dev` alias, Cloudflare's own domain, outside the zone cache — but only
  before go-live; once `CANONICAL_URL` is set it redirects to the live domain, so don't
  follow it) — NEVER poll the live custom domain to see whether the build is done.
  (`npm run ship`'s built-in check is the one exception: it polls `/build.txt` — a path
  that exists in every build — with a cache-bust.) Once Active, check the live domain with a
  `?cb=<anything>` cache-bust first (under default cache settings that is a distinct cache
  key, so it cannot poison the bare URL).
- Touch the **bare canonical URL last**, after Active — and only then tell the owner the
  link is safe to open. Announcing a URL before Active invites the owner to click it —
  and that first request makes the edge cache the 404 for everyone.
- The same applies to Search Console **Request Indexing**: Googlebot is served the same
  edge cache, so requesting indexing while a stale 404 is cached shows Google exactly the
  wrong thing.
- If a 404 does get cached anyway: ask the owner to run the single-URL purge in the
  Cloudflare dashboard (a human-only step — the assistant has no dashboard access; path
  above), then re-verify.
