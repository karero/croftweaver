# First deploy to Cloudflare Pages — getting the site online the first time

`PUBLISHING.md` covers the **ongoing** `commit → push → rebuild` loop. This covers the
**one-time bootstrap**: creating the Cloudflare Pages project, the first deploy, and
(optionally) attaching the custom domain + turning on IndexNow. For someone who has never
touched Cloudflare, this is the hardest, most nerve-wracking part — so **offer to do it for
them** rather than handing over a dashboard tour.

> **Assistant: for a site on GitHub, recommend the setup script (S, next section).** It
> gives (B)'s result, a project that builds on every push, with most of (A)'s ease: one
> short-lived token, the owner's yes to a printed list, and no dashboard tour. It does setup day today; on the day the
> site goes live, the domain is attached by hand ("Going live" and "After go-live" below),
> until the script's launch stage exists. (A) stays for an owner who wants no GitHub
> connection; (B) and (C) stay on offer. State the deploy-model tradeoff in (A) before an
> owner picks it.

> **Cloudflare now suggests Workers for new projects.** Its Pages docs open with "Start new
> projects with Workers" (read 2026-10-07). Create a **Pages** project anyway: the kit's
> `functions/_middleware.ts`, its build variables and the steps below are written for Pages,
> which Cloudflare still lists as available on all plans. `WEBSITE_ARCHITECTURE.md` Part 1
> has the reasons.

---

## S. Setup by script, connected to GitHub — RECOMMENDED for a site on GitHub

`scripts/cloudflare-setup.mjs` (beside `cloudflare-check.mjs`; Node 18 or newer, nothing
from npm, no Wrangler) does setup day through Cloudflare's API: it creates the Pages project
connected to the site's GitHub repository (or adopts the one already connected), starts its
first build, writes most of the settings of `docs/CLOUDFLARE-CHECKLIST.md` (what it leaves
is named below), and writes the verification records the owner dictates. It attaches no domain and sends the
domain no request: until launch day the site answers only at the project's `pages.dev`
address.

**What the owner does first, in the browser:**

1. The domain is on Cloudflare already ("Going live" below if it is not). The script moves
   no domain.
2. A token with the rows of the checklist's section 6, Zone → DNS → Edit among them; Zone
   Resources the one domain, Account Resources their own account; an end date of tomorrow,
   a week at most, and no start date. The script refuses a token with no end date, one that
   ends more than eight days ahead (a week, with a day's room: the dashboard sets an end
   date, not a time), and one that reaches more than this zone.
3. Cloudflare's GitHub app gets access to the one repository: GitHub → Settings →
   Applications → Cloudflare Workers and Pages → Configure. Nothing more: a project made
   through the API builds from GitHub without "Connect to Git" in the dashboard.

**The token** goes in `CLOUDFLARE_API_TOKEN`, or, when an assistant's shell keeps no
variable from one command to the next, on a line `CLOUDFLARE_API_TOKEN=…` in the site's
`.dev.vars` (the starter's `.gitignore` excludes it; this is for the script, not for
Wrangler, see below). The script refuses `.dev.vars` if git tracks it or does not ignore
it, sends the token only to Cloudflare's API, never prints it, and keeps it out of the
environment of `git`.

**Run it** in the site's folder:

```bash
node "$SKILLS_ROOT/new-website/scripts/cloudflare-setup.mjs" setup
```

Options: `--confirm <code>` (the owner's yes, below), `--project <name>` (the project to use or create; by default the one connected to
the repository, or one named like it), `--skip <id>` for a line the owner wants left as it is
(`https`, `tls`, `email`, `nel`, `bot`, `ai`; `ai` covers the AI bot policies, AI Labyrinth,
Content bots and Bot Preference Sync together), and `--record "<type> <name> <content>"` for a
verification record from `search-console-setup` (TXT or CNAME; `@` is the domain itself; at
most five in one run, so the code stays quick to check).

**A yes is a second run with a code.** A run with something to change prints the whole list
(what is there now, what it becomes, and, for each Cloudflare setting, that it changes the
whole domain and which hosts that touches), then a code, changes nothing, and ends with 3.
Show the owner the list as printed. On their yes, run the same command again with
`--confirm <code>`. The printed question, confirmed with its code, is the owner's yes to the
changes it lists and to nothing else (guardrail 4 below). The code is made from that list,
the build with the commit it names, and from the end state: the project and its repository,
its production branch and build settings, each setting's new value, the zone's proxied hosts,
the records, and the `--skip` ids. A later run takes the code while what is left to do is
part of that list, so a run cut off half-way carries on. Anything the list did not have, a
build of another commit, or a change to the end state, and the code no longer fits: the run
asks again and changes nothing. What is there now (a setting's old value) is shown but not
bound: if someone changes a listed setting by hand before the yes, the yes still sets it to
the value the list named.

| Status | Means | Then |
|---|---|---|
| 0 | Setup is done, as far as Cloudflare's API shows | Launch day: attach the domain by hand ("Going live") |
| 1 | Something failed or was refused; the report says what, and what to do by hand | Fix that, or do the line by hand |
| 2 | The command was wrong | Read the message |
| 3 | Waiting for the owner's yes | Show the list; on a yes, run again with `--confirm <code>` |
| 4 | Waiting for Cloudflare (a build) or for a push | Run the same command again in a few minutes |

**The proof of the connection** is a build Cloudflare starts itself from a push. Until there
is one the script ends with 4: push one commit to a pull request (an empty commit does), and
run it again. Where the project builds no previews, the push that shows it is the production
branch's: on a two-stage site that is `npm run ship`, on the owner's word.

**By hand, or on launch day:** what `CLOUDFLARE_CHECK.md` lists under "By hand, always"
(Crawler Hints, the Web Analytics switch, the script monitor's switch, HSTS later, deleting the
token), and the rule that removes the NEL headers (the checklist's section 3,
step 4), which the Transform Rules row of the token is for. It is added only if the domain
still sends the headers, and by hand until the launch stage exists.

**It never** merges, runs `npm run ship`, deletes or detaches anything, changes a record
other than one it writes, or repairs a site that is live: a project already serving a domain
gets no build and no branch change from it. No run waits for typed input, and none takes
longer than 55 seconds.

---

## A. Token-assisted bootstrap — for an owner who wants no GitHub connection

The owner mints **one scoped, expiring API token**; you (the agent) run Wrangler to
create the project and deploy — **no dashboard for the deploy itself**. Two doc facts to
know (confirmed against current Cloudflare docs, June 2026):
- **Custom domain:** Wrangler has *no* Pages custom-domain command
  ([workers-sdk#11772](https://github.com/cloudflare/workers-sdk/issues/11772) is open),
  but the **Pages REST API can attach it with the same Pages-Edit token** — so the token
  *does* cover this, just not via the Wrangler CLI.
- **Crawler Hints / IndexNow:** [no API at all](https://community.cloudflare.com/t/how-do-i-enable-crawler-hints-through-the-api/384104) —
  it's the one dashboard toggle in `search-console-setup`, whatever deploy path you pick.

So this is the fastest path to "my site is live"; IndexNow is a short dashboard visit
afterwards (or the browser-assisted path in C).

**Tradeoff — state this up front:** this uses Wrangler's **direct-upload** deploy model.
Ongoing deploys are then `wrangler pages deploy`, **not** Cloudflare's git-push auto-build
that `PUBLISHING.md` assumes. A direct-upload project and a Git-connected project are
*different Pages project types* — pick (A) **or** (B), not both. If the owner wants
push-to-deploy afterwards, prefer (S) or (B). (A) is the right call when the priority is getting
live fast with zero dashboard time.

### The token — least-privilege, never the Global API Key

1. Dashboard → **My Profile → API Tokens → Create Token → Create Custom Token**.
2. **Permissions** — add only what the chosen steps need:
   - **Account › Cloudflare Pages › Edit** (a.k.a. `Pages Write`) — create the project,
     deploy, **and** attach a custom domain via the Pages REST API
     (`POST /accounts/{id}/pages/projects/{name}/domains`). *(required — and it's all the
     happy path needs.)*
   - **Zone › DNS › Edit**, scoped to the **one** zone — **only** if the flow also creates
     or changes DNS records itself. Attaching the custom domain does **not** need this on
     its own; skip it unless you're scripting DNS. *(optional)*
   - *(There is no Crawler Hints permission — it has no API. Enable IndexNow via the single
     dashboard toggle in `search-console-setup`, whichever deploy path you pick.)*
3. **Account Resources:** include only the owner's account. **Zone Resources:** only the
   one target zone (never "All zones").
4. **Expiry:** set an **End date ~1 week out** — enough to bootstrap, then it dies on its own.
5. Create → copy the token (**shown once**).

### Hand it to the agent safely — never the repo

- Provide it as a session env var: `export CLOUDFLARE_API_TOKEN=…` (Wrangler reads this).
  Not `.dev.vars`: that file holds the Worker's own local settings, and Cloudflare's list of
  where Wrangler reads its own variables from names the shell and a `.env` file, not
  `.dev.vars` ([system environment variables](https://developers.cloudflare.com/workers/wrangler/system-environment-variables/)).
  The starter `.gitignore` also excludes `.env`, `.env.*` (but not `.env.example`) and
  `.dev.vars`, a backstop in case a copy lands in a file in a generated site.
  *(This suite repo additionally runs a `clean` CI gate that scans the distributed skill
  package for stray tokens — that gate does **not** run in generated sites.)*
- **Never** commit it, paste it into a tracked file, or put it in the README.

### Assistant guardrails (non-negotiable)

1. **Scoped token only.** If the owner offers a Global API Key or their password, decline
   and ask for a custom token with the permissions above.
2. **Expiring + minimal.** Confirm the token has an end date and only the needed scopes
   before using it; if it looks over-scoped (e.g. "All zones"), say so and ask them to narrow it.
3. **Never commit the credential** — a session env var only; the starter
   `.gitignore` is the backstop.
4. **Confirm before each account-modifying command** — state what it will do (create project
   `X`, deploy, add a DNS record for `Y`) and run it only on the owner's go-ahead. For the
   setup script (S), its printed question, confirmed with its code, is the confirmation for
   the changes it lists, and for nothing else.
5. **Revoke when done** — once the site is live, tell the owner to delete the token
   (My Profile → API Tokens → ⋯ → Delete), or let the expiry retire it. Don't leave a live
   token lying around. And never drive these changes through blind screen control.
6. **The deploy-time guardrails apply from this very first deploy** — the preview-vs-live
   announcements and the cached-404 rule in `templates/PUBLISHING.md` § "For AI
   assistants — deploy-time guardrails" (see the pointer in SKILL.md §4). The first
   request a brand-new custom domain sees is the one the edge caches.

### Commands you run (token in env)

```bash
# 1. Create the Pages project (direct-upload). <production-branch> is main or production.
npx wrangler pages project create <project> --production-branch <production-branch>

# 2. Build, then deploy the static output. Both lines take the production branch from step 1.
#    CF_PAGES_BRANCH: with analytics switched on (USE_ANALYTICS = true in src/config.ts; the
#    starter ships it off), the build writes the script only when this equals PROD_BRANCH
#    in src/config.ts. Cloudflare sets it only when IT builds; this build runs here, so
#    without it the live site ships with no analytics script (no error, no data).
#    The kit ships PROD_BRANCH = 'production': if step 1 chose main, first set PROD_BRANCH
#    in src/config.ts to 'main'. For a preview deploy, build with `CF_PAGES_BRANCH= npm run build`
#    (set to empty, so an exported value can't switch analytics on), then deploy with any
#    other --branch.
#    --branch: without it wrangler uses the local git branch and may make a preview deployment.
#    On Windows, run these in Git Bash or WSL.
CF_PAGES_BRANCH=<production-branch> npm run build
npx wrangler pages deploy dist --project-name <project> --branch <production-branch>

# 3. Custom domain: NO Wrangler command exists for Pages custom domains.
#    Attach it in the dashboard (Workers & Pages -> your project -> Custom domains ->
#    Set up a domain), OR via the Pages REST API with the SAME Pages-Edit token:
#    POST /accounts/{id}/pages/projects/{project}/domains  {"name":"<domain>"}
#    (Zone>DNS>Edit is only needed if you also script the DNS record itself.)
```

> **`pages deploy`, not plain `deploy` — or you get a `workers.dev` URL.** These are static
> **Pages** sites: every command above is `wrangler pages …` and the deploy must print a
> **`<project>.pages.dev`** URL. A bare `wrangler deploy` (no `pages`) publishes a **Worker**
> and hands back a `*.workers.dev` URL instead — a real mistake we've seen on an older kit
> version. If you see `workers.dev`, stop: you deployed the wrong project type. Confirm it's
> the accidental Worker (not a pre-existing one with a similar name), then delete it and
> re-run `wrangler pages deploy`.

Ongoing deploys under (A): re-run both lines of step 2, the variable included —
`CF_PAGES_BRANCH=<production-branch> npm run build`, then
`wrangler pages deploy dist --project-name <project> --branch <production-branch>`
(wrap them in `npm run ship` if you want one command — note the stock `ship.sh` targets the
git-push model of (B), so adapting it for direct-upload is a follow-up, not assumed here).
The owner's version, for after handoff, is `templates/PUBLISHING.md`, "Deploy by command":
keep the two in step: both build with `CF_PAGES_BRANCH=<production-branch>` and deploy
with the same `--branch`. Before handoff, add one sentence
to the site README's "Deploy" paragraph: this site deploys by command, with no GitHub
connection in Cloudflare (project `<project>`, production branch `<production-branch>`), and
`PUBLISHING.md`, "Deploy by command", has the steps. That sentence is how the owner, and the
next assistant, can tell. Then continue with `search-console-setup` for GSC/Bing + Crawler
Hints.

---

## B. GitHub git-integration — RECOMMENDED if the owner wants push-to-deploy and no token

One-time guided dashboard connect, then `git push` builds automatically — the model
`PUBLISHING.md` assumes. No token, but the owner does the one-time OAuth connect. The setup
script (S) makes the same kind of project through the API instead, and writes the
checklist's settings as well; this is the way by hand:

Cloudflare → **Workers & Pages → Create → Pages → Connect to Git** → pick the repo →
framework preset **Astro**, build command `npm run build`, output directory `dist`. For a
two-stage site, choose **Production branch = `production`** in this same form (see
new-website §4): connecting builds and publishes the production branch straight away, so
leaving it at `main` would publish the preview first.

## C. Browser-assisted or manual walk-through — the fallback

If the owner won't mint a token and won't do the dashboard alone: drive the dashboard via
your runtime's browser automation (**Claude in Chrome** under Claude Code; the agent's own
browser tool otherwise — see `search-console-setup`), or read them the clicks one by one.
Both work; both eat time and patience — which is why **(S) is recommended**.

---

## After the first deploy, whichever option: set "Fail open"

Cloudflare serves static files free and without limit only while no Function runs. The
kit's `functions/_middleware.ts` sits at the root of `functions/`, and Pages then runs it in
front of every request, files included. So every page view, image, font and crawler hit,
on the live domain too, counts as a Functions request. On the free plan those come out of
**100,000 requests a day**, shared by every Pages Function and Worker in the account, reset
at midnight UTC.

Don't add a `_routes.json` to exclude the files from the middleware. Cloudflare suggests it
to keep static requests free, but it matches paths only, never the host: on the
`<project>.pages.dev` alias the excluded files would then skip the middleware, so they would
neither redirect nor carry noindex.

One small site rarely gets near that; several sites in one account, or a busy crawler, can.
What happens then is up to the project's **Fail open / closed** setting, which the free
plan offers:

- **Fail open** (recommended): the static site is served without the middleware until
  midnight UTC. Nothing changes on the live domain, which the middleware passes through
  untouched. Previews still carry the `X-Robots-Tag: noindex` that Cloudflare adds to every
  preview deployment itself. `<project>.pages.dev` is the one address that changes: for the
  rest of that day it loses what the middleware gives it, the redirect (once
  `CANONICAL_URL` is set, below) and the noindex.
- **Fail closed**: every request, on the live domain too, gets an error page until midnight
  UTC. That suits a Function that guards something; the kit's does not. If a site later
  gets one that does, choose again.

Either way, any other Function the site has stops until midnight UTC too.

Set it once, right after the first deploy: dashboard → **Workers & Pages** → the project →
**Settings → Runtime → Fail open / closed** (path checked in the dashboard 2026-10-07). A
project created with `wrangler pages project create` started on Fail open that day. One
made in the dashboard or connected to GitHub was not checked, Cloudflare's docs no longer
name a default (they once said Fail open), and the setting was missing from the dashboard
for a while in 2024–25: look rather than assume. Workers Paid ($5/month) removes the daily
limit (10 million requests a month included, then billed per million).

Sources, read 2026-10-07: Cloudflare's
[Functions pricing](https://developers.cloudflare.com/pages/functions/pricing/),
[routing and Fail open / closed](https://developers.cloudflare.com/pages/functions/routing/),
[middleware](https://developers.cloudflare.com/pages/functions/middleware/),
[daily request limit](https://developers.cloudflare.com/workers/platform/limits/#daily-requests),
[preview deployments](https://developers.cloudflare.com/pages/configuration/preview-deployments/)
and [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/); for the
setting's history, the cloudflare-docs pull requests that
[removed](https://github.com/cloudflare/cloudflare-docs/pull/17200) (2024) and
[restored](https://github.com/cloudflare/cloudflare-docs/pull/22331) (2025) its docs.

## After the first deploy: the Cloudflare settings checklist

The kit's promises (no cookies, no tracking the owner didn't choose, open to search engines
and AI assistants) also rest on a few Cloudflare settings that live in the dashboard, such
as HTTPS and TLS, HSTS, Network Error Logging, Bot Fight Mode, Web Analytics, Crawler Hints
and the AI crawler policies. `docs/CLOUDFLARE-CHECKLIST.md` in the Croftweaver folder lists
them with their dashboard paths, and an outside check where one exists. Once the site is
live, offer to go through it with the owner. Offer the token route too (section 6 of the
checklist): the guardrails above apply to it, and the owner runs the checklist's section 5
before the token is deleted. `scripts/cloudflare-check.mjs` runs that section, and lists the
dashboard-only items, in one command; `CLOUDFLARE_CHECK.md` beside this file says how to read it.

---

## Going live: moving an existing domain's DNS to Cloudflare — verify twice

When the site replaces a domain that already serves mail and a live site elsewhere (a
rebuild migrating its DNS to Cloudflare), the cutover is the **single riskiest moment** — a
wrong or wrongly-proxied record silently breaks email or the site right when it goes live.
Treat it as a checklist *with* the owner, never a fire-and-forget edit:

1. **Import, then check every record twice.** When Cloudflare scans the existing zone it
   often misses records. Compare the imported set against the old DNS provider's export
   **entry by entry, twice** — A/AAAA, CNAME, **all MX**, and every TXT (SPF, DKIM, DMARC,
   verification tokens). A missing MX or SPF record = broken mail. The scan is least reliable
   on **CNAME, SRV, and CAA** records even when A/MX/TXT come through, so confirm those by
   hand:
   - **Microsoft 365 / Outlook:** verify `autodiscover` (CNAME → `autodiscover.outlook.com`),
     the DKIM selector CNAMEs (`selector1._domainkey`, `selector2._domainkey`), and the
     Teams/Skype SRV records (`_sip._tls`, `_sipfederationtls._tcp`). A missing `autodiscover`
     has been seen on a real migration (Cloudflare may have since improved this — **verify, don't
     assume**); without it Outlook mailbox auto-setup breaks.
   - **CAA** records — two failure modes: if existing CAA records are *dropped*, or if they
     are *restrictive and don't list Cloudflare's CA*, Cloudflare can't issue the TLS cert
     for the domain (including the Pages custom domain). If any CAA records exist, **confirm
     they permit Cloudflare's CAs before go-live.**
   - **Wildcard (`*`)** records and **subdomain NS delegations** — both commonly skipped.
2. **Get a screenshot and double-check it.** Have the owner screenshot the final Cloudflare
   DNS table and pass it back so you can review it against the old zone before they flip the
   nameservers. A second pair of eyes catches the record that was dropped or mistyped.
3. **Know which records must NOT be proxied (grey cloud, DNS-only).** Cloudflare's orange
   "proxy" cloud only makes sense for the **HTTP(S) hosts you actually serve through
   Cloudflare** (usually apex + `www` for this kit; proxy any other host only if it
   intentionally serves HTTP through Cloudflare). Everything else must stay **DNS-only**, or
   it breaks:
   - **MX records and the mail hostnames they point to** — proxying mail destroys delivery.
   - **SPF / DKIM / DMARC** and other **TXT** records (they aren't HTTP; proxy doesn't apply).
   - **CNAMEs that aren't your website** — the sneaky trap, because only A/AAAA/CNAME records
     *can* be proxied and onboarding often defaults the proxy **ON**: `autodiscover` /
     `autoconfig`, **DKIM selector CNAMEs**, domain-**verification** CNAMEs, and third-party
     service CNAMEs (email, helpdesk, status pages). A stray orange cloud on any of these
     breaks the service — leave them DNS-only.
   - Any record that must resolve to its **real origin IP** (e.g. a service expecting the
     true address, not Cloudflare's edge).
   Make sure the owner *understands* this distinction — don't just set it silently.
4. **Disable DNSSEC at the registrar before touching nameservers.** Check whether DNSSEC is
   enabled at the old provider/registrar; if it is, **turn it off first** (or follow
   Cloudflare's DNSSEC migration path). Flipping nameservers while the old DS record is still
   live leaves a signature chain Cloudflare can't satisfy — resolvers then return
   `SERVFAIL` and the domain goes dark. Re-enable DNSSEC in Cloudflare afterwards if wanted.
5. **Only after the passes agree and DNSSEC is handled**, change the nameservers / flip the
   apex. Then confirm the site loads on the live domain **and** send a test email both
   directions.

> **Pages: attach the custom domain in the project — a DNS record alone isn't enough.** For a
> Pages site, just adding a CNAME/record that points at `<project>.pages.dev` does **not**
> connect the domain; the domain must be added through the Pages **Custom domains** flow
> (dashboard, or the REST API in §A) or visitors get a **522**. And once it's attached, don't
> "test" by pointing the record away from Pages and back — Cloudflare can serve errors until
> it reactivates; use a redirect/origin rule for any temporary routing instead.

> **Make rollback cheap — and don't tear the old setup down yet.** Lower the record TTLs at
> the old provider ~24h *before* the move. After the flip, **keep the old zone, site, and mail
> running through the propagation window** — resolvers may serve cached DNS for a while, so you
> want an instant fall-back. Only retire the old setup once the new domain is confirmed
> resolving and mail flows both directions.

> Drive these changes *with* the owner, not through blind screen control — same guardrail as
> the bootstrap token steps above.

## After go-live: send `<project>.pages.dev` to the live domain

Every Pages project also serves production at its own alias, `<project>.pages.dev`. The
kit's `functions/_middleware.ts` noindexes it, but that does not keep it out of AI
answers: AI search engines have been seen citing the alias instead of the real domain. So
once the site is live, the alias should 301-redirect to the live domain: anyone who
follows such a link lands on the real site, and crawlers are told which host counts. It
won't rewrite an answer an AI engine has already given; re-check citations after a few
weeks.

The redirect is **off until you switch it on**, because before launch the alias may be the
only address that works. Switch it on only when the live domain really serves this site —
custom domain **Active**, DNS flipped, and `https://<live-domain>/build.txt?cb=<something new>`
showing the current build:

1. Cloudflare dashboard → **Workers & Pages** → the project → **Settings → Variables and
   Secrets** → **Production** → add a plain-text variable `CANONICAL_URL` =
   `https://example.com` (the live origin, same as `SITE.url`; no path, no trailing slash).
   Production only: previews must keep working, and the middleware never redirects a
   preview host anyway. Open `<that value>/build.txt?cb=<something new>` (e.g.
   `https://example.com/build.txt?cb=2609261430`) before saving and confirm it
   shows the current build: browsers remember a 301, so a typo'd domain keeps sending
   visitors to the wrong place even after you correct the variable.
2. **Redeploy with a new commit.** A variable only reaches deployments made after it was
   set, so the redirect starts with the site's next ordinary publish. To switch it on now,
   note that `npm run ship` or a push with nothing new to publish does **not** redeploy —
   git says "Everything up-to-date", Cloudflare builds nothing, and ship's "✓ LIVE" check
   still passes on the old build. Make an empty commit
   (`git commit --allow-empty -m "Apply CANONICAL_URL"`) and bring it onto `main` the way
   this site takes changes (`AGENTS.md` §2: an assistant opens a pull request; the owner
   may push directly unless the site is pull-request-only), then run `npm run ship`
   (two-stage); on a single-stage site reaching `main` is the publish. Direct-upload sites
   (§A): re-run `npx wrangler pages deploy dist --project-name <project> --branch
   <production-branch>` — without `--branch`, wrangler may take the local git branch
   (`main`) and make a preview deployment instead.
3. Check: `curl -sI https://<project>.pages.dev/about` answers `301` with
   `location: https://example.com/about`, and a preview host still answers `200` with
   `x-robots-tag: noindex, nofollow` — two-stage: `main.<project>.pages.dev`; single-stage:
   any `<hash>.<project>.pages.dev` from `npx wrangler pages deployment list`. Still `200`
   on the alias? The variable isn't under **Production** (missing, misnamed, or added to
   Preview), the deployment predates it (step 2), the value was rejected (not `https://`,
   a `pages.dev` host, or a malformed host such as `example..com` — check it by eye), or
   the site's `functions/_middleware.ts` predates the redirect (below).

A value the middleware can't use (not `https://`, a `pages.dev` host, or a malformed host)
is ignored and logged, so the alias stays noindexed rather than breaking. A well-formed but
wrong domain is not caught: it redirects there, which is why step 1 checks the value first.

**Sites scaffolded before this redirect existed** need the new `functions/_middleware.ts`
first: copy it from `templates/astro/functions/_middleware.ts`
(`make whats-new PROJECT=<site-dir>` lists it when it changed) and commit it, but don't
push until step 1 is saved: on a single-stage site that push is the production deploy.
Then do steps 1–3; that commit is the new commit step 2 needs. Nothing changes on a live site until that
redeploy.

After the switch, the alias no longer shows the latest production build. To check a build
went Active, use `wrangler pages deployment list` or the deployment's hash URL
(`<hash>.<project>.pages.dev`), never the live domain (see `PUBLISHING.md`).
