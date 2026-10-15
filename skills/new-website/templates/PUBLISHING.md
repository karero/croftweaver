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

# 3. Look at the preview. Open the preview link from Cloudflare
#    (stable address: main.<your-project>.pages.dev, where <your-project> is the
#    first part of the project's own address as Cloudflare shows it) and check it's right.

# 4. Happy? Publish it to the live site — ONE command:
npm run ship
```

`npm run ship` uploads `main` to the live (`production`) branch for you — you never run the
branch commands by hand. Then it **waits and verifies** that the live site really serves the
new version (every build stamps its id into `/build.txt`; ship polls for it, up to 4 min).
"✓ LIVE — verified" means it's truly online; a warning means Cloudflare didn't build — the
message tells you exactly what to click. Never assume a push went live without that check.

> **Each upload may run a quick self-check** (it builds the site and runs the tests before
> uploading — so does `npm run ship`, which uploads too). It can take a minute, and **if
> something is broken it stops the upload and tells you** rather than publishing a broken
> page. To skip the check on a *manual* `git push` you've already verified:
> `git push --no-verify`. If **`npm run ship`** stops partway, don't force it — ask for help.

> **Nothing reaches the live domain until step 4.** Steps 1–3 only update the noindexed preview.

---

## Single-stage (simplest) — "push = live"

One branch, `main`, and it **is** the live site. There's no preview — every upload goes
straight online. Simple, but there's no safety net, so check locally first (`npm run dev`).

> **"Push = live" is a promise, not a fact.** Cloudflare can silently stop building (it
> happened in production: green pushes, no deploy). After an important upload, confirm the
> change is really online — `curl https://your-site/build.txt` shows which build is serving
> (compare with `git rev-parse HEAD`). If it's stale: Cloudflare dashboard → your project →
> Deployments (retry the failed build, or re-connect GitHub under Settings → Builds).

> **You need a custom domain for Google to see the site.** A bare Cloudflare
> `*.pages.dev` URL is **noindexed by design** (so stray preview URLs never get indexed).
> Until you attach your real domain in Cloudflare, the live site works but search engines
> ignore it. Once your real domain shows the new site, your assistant switches the
> `pages.dev` address to forward visitors there, so a link to it in an AI answer still
> brings people to your real domain.

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
assistant).
Such a site has no preview step, and `git push` only updates GitHub. **Nothing goes online
until someone runs the commands below.** They publish `main`, so first check your change
locally (`npm run dev`), then save and upload it on `main` with `git add -A`, `git commit`
and `git push` as above. Skip `npm run ship` here: it waits for Cloudflare to build, and on
such a site Cloudflare never does.

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

- `CF_PAGES_BRANCH=` turns on your visitor statistics. Without it the live site counts no
  visitors, with no error to tell you. (It only works when the name matches `PROD_BRANCH`
  in `src/config.ts`. If you're not sure it does, ask your assistant to check.)
- Without `--branch`, the upload can land as a preview instead of on the live site.

The `&&` means each line runs only if the one before it worked. If `git` or the build stops
with an error, nothing was uploaded: ask for help rather than running the upload on its own.
If the upload itself shows an error, part of it may have gone live anyway: ask for help
before running it again. The first
time, `npx` may ask "Ok to proceed?": type `y`. If the command says you aren't logged in, run
`npx wrangler login` once (it opens your browser so you can log in to Cloudflare), then
run it again.
On Windows, run it in Git Bash or WSL.

---

## If something goes wrong

- **Mistake already live?** Don't panic — in the **Cloudflare dashboard → your Pages
  project → Deployments**, every past version is listed; click an older one →
  **Rollback** to restore it instantly.
- **Made a typo in the last save (not pushed yet)?** Re-edit, then
  `git add -A && git commit -m "fix typo"` again.
- **`git push` says "rejected"?** (on `main`) Someone/something updated the cloud copy — run
  `git pull` first, then `git push` again.

`npm run ship` names which of these it is, and stops before publishing anything. The
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

When in doubt, ask before you `npm run ship`, `git push` or the deploy command above — those
are the only commands that change what the public sees.

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

> ✅ Your changes are on the **preview**: `https://main.<project>.pages.dev` — **this is NOT
> live yet.** When it looks right, run `npm run ship` to publish to `<live-domain>`.

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

**Which URL to quote.** `<project>` below is the first part of the project's own address,
as Cloudflare shows it on the project's page: not always the project's name. Prefer the
**memorable `pages.dev` alias** — the branch alias
`main.<project>.pages.dev` (or, before go-live, the project alias `<project>.pages.dev` —
after go-live it redirects to the live domain) — over the random
per-deploy hash URL `<hash>.<project>.pages.dev`. The hash URL is ugly but **immutable**, so
keep it as a **backup**: when an alias looks **stale** (cache/propagation lag, or it's still
serving an older build), the hash URL pins the exact fresh deployment and confirms the new
build is up. For a **brand-new page**, though, the next section wins: until the production
build is Active, the page exists only on the hash URL. Whichever URL you quote, **open it
and confirm it loads** rather than reporting it blind — and note it for the project.
(A `pages.dev` URL is also the signal you deployed to **Pages**, not a Worker — if a deploy
ever prints a `*.workers.dev` URL, stop: you published the wrong project type.)

### Never request a page on the live domain before its build is Active

The edge caches whatever it first sees. If anyone — you, the owner's browser, a link
checker — requests a brand-new path on the live domain while the production build is still
running, a zone cache rule (Cache Everything on HTML) will cache the **404**, and a cached
404 does not reliably self-heal: observed surviving `cf-cache-status: HIT` more than 90
minutes past a 30-minute `max-age`, immune to plain re-requests. Only a **manual dashboard
purge** clears it (Cloudflare dashboard → the zone → Caching → Purge Cache → custom purge by
URL; wrangler's OAuth token has `zone (read)` only and cannot purge programmatically). So:

- Until the production deployment shows **Active**, verify new pages ONLY on the hash
  deployment URL (`<hash>.<project>.pages.dev`) — pre-Active the live domain still serves
  the *previous* deployment, so a brand-new path 404s there no matter how you request it.
  Check Active status without touching the live domain: `wrangler pages deployment list`,
  the `<project>.pages.dev` alias (Cloudflare's own domain, outside the zone cache — but
  only before go-live; once `CANONICAL_URL` is set it redirects to the live domain, so
  don't follow it), or ask the owner — NEVER poll the live custom domain to see whether the build is done.
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
