# First deploy to Cloudflare — getting the site online the first time

`PUBLISHING.md` covers the **ongoing** `commit → push → rebuild` loop. This covers the
**one-time bootstrap**: the site's Worker, the first deploy, and (optionally) attaching the
custom domain + turning on IndexNow. For someone who has never touched Cloudflare, this is the
hardest, most nerve-wracking part — so **offer to do it for them** rather than handing over a
dashboard tour.

> **Assistant: for a site on GitHub, recommend the setup script (S, next section).** It
> gives (B)'s result, a Worker that Cloudflare builds on every push, with most of (A)'s ease:
> one short-lived token, the owner's yes to a printed list, and no dashboard tour beyond one
> click. Its `setup` stage checks the zone and the Worker and writes the settings; with no
> Worker yet it says how to connect the repository to Workers Builds (the one dashboard
> click) or to run `npm run deploy:live`. Its `launch` stage attaches the domain on the day
> the site goes live. (A) stays for an owner who wants no GitHub connection; (B) and (C) stay
> on offer. State the deploy-model tradeoff in (A) before an owner picks it.

> **New sites are Workers.** The starter is a Worker with static assets and no script of its
> own (`wrangler.jsonc`), so no request for a page or a file runs code. Cloudflare's own docs
> for its older product open with "Start new projects with Workers" (read 2026-10-07).
> `WEBSITE_ARCHITECTURE.md` Part 1 has the reasons. A site made before 0.35 is still on
> Cloudflare's older product, Pages, and stays there until it moves: its steps are in the last
> section, "Sites already on Pages".

---

## S. Setup by script, connected to GitHub — RECOMMENDED for a site on GitHub

`scripts/cloudflare-setup.mjs` (beside `cloudflare-check.mjs`; Node 18 or newer, nothing
from npm, no Wrangler) does setup day through Cloudflare's API: it finds the site's zone and
its Worker (the site's `wrangler.jsonc` names it), writes most of the settings of
`docs/CLOUDFLARE-CHECKLIST.md` (what it leaves is named below), and writes the verification
records the owner dictates. It makes no Worker and starts no build: the first build or
deploy makes the Worker. It attaches no domain and sends the domain no request: until launch
day the live `workers.dev` address stays off, and the site answers only at its Preview link.

**What the owner does first, in the browser:**

1. The domain is on Cloudflare already ("Going live" below if it is not). The script moves
   no domain.
2. A token with the rows of the checklist's section 6, Account → Workers Scripts → Edit and
   Zone → DNS → Edit among them; Zone Resources the one domain, Account Resources their own
   account; an end date of tomorrow, a week at most, and no start date. The script refuses a
   token with no end date, one that ends more than eight days ahead (a week, with a day's
   room: the dashboard sets an end date, not a time), one whose zones belong to more than one
   account, and one with DNS Edit in more than one zone (a token made for the account alone
   gets it in every zone). If the owner already runs other Workers in that account, say that
   Workers Scripts Edit reaches every one of them, and that a separate Cloudflare account
   for the site keeps them out of reach.
3. Where the Worker does not exist yet, the repository is connected to Workers Builds in the
   dashboard (B below), or the assistant runs `npm run deploy:live` once from the owner's
   computer (A). The setup script says which, with the Worker's name from `wrangler.jsonc`,
   and ends with 4.

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

Options: `--confirm <code>` (the owner's yes, below), `--skip <id>` for a line the owner
wants left as it is (`https`, `tls`, `email`, `nel`, `bot`, `ai`; `ai` covers the AI bot
policies, AI Labyrinth, Content bots and Bot Preference Sync together; on `launch` also
`nel-rule`), and `--record "<type> <name> <content>"` for a verification record from
`search-console-setup` (TXT or CNAME; `@` is the domain itself; at most five in one run, so
the code stays quick to check).

**A yes is a second run with a code.** A run with something to change prints the whole list
(what is there now, what it becomes, and, for each Cloudflare setting, that it changes the
whole domain and which hosts that touches), then a code, changes nothing, and ends with 3.
Show the owner the list as printed. When the run also prints notes on the AI bot policies (Training on Block or Disallow, Search or Agent left blocked, a value the kit does not know), pass them on as printed, in the ask and again in the report: they say what Block costs in search and how to keep a training choice with `--skip ai`. On their yes, run the same command again with
`--confirm <code>`. The printed question, confirmed with its code, is the owner's yes to the
changes it lists and to nothing else (guardrail 4 below). The code is made from that list: the
Worker and its repository, each setting's new value, the zone's proxied hosts, the records,
and the `--skip` ids. A later run takes the code while what is left to do is part of that
list, so a run cut off half-way carries on. Anything the list did not have, or a change to
the end state, and the code no longer fits: the run asks again and changes nothing. What is
there now (a setting's old value) is shown but not bound: if someone changes a listed
setting by hand before the yes, the yes still sets it to the value the list named.

| Status | Means | Then |
|---|---|---|
| 0 | `setup`: done, as far as Cloudflare's API shows. `launch`: the domain serves the site, and the check passes | After `setup`: on launch day, `launch` (below) |
| 1 | Something failed or was refused; the report says what, and what to do by hand | Fix that, or do the line by hand |
| 2 | The command was wrong | Read the message |
| 3 | Waiting for the owner's yes | Show the list; on a yes, run again with `--confirm <code>` |
| 4 | Waiting for Cloudflare, a build or the first deploy | Do what the report says if it names a step; run the same command again in a few minutes |

**What setup says about the Worker.** It reads the Worker's deployments and its version link
(a Worker's address for one build, which carries `noindex`):

- **No Worker yet:** it prints how to connect the repository to Workers Builds (B below),
  or to run `npm run deploy:live` once, and ends with 4. The zone lines still run on the
  owner's yes. The first build or deploy makes the Worker; run setup again after it.
- **A Worker that Cloudflare made from its own template and no build of this site yet
  replaced:** it says no build has passed, and ends with 4. If Workers Builds shows no
  repository connected, the Worker is someone else's: rename the site's Worker in
  `wrangler.jsonc`.
- **A Worker that is not this site's** (its version link serves no `build.txt`, or names a
  commit this repository does not have): refused, nothing changed. Pick another `name` in
  `wrangler.jsonc`.
- **A Worker that serves this site:** reported as it is, with the commit.

It refuses a `wrangler.jsonc` whose `workers_dev` is not `false`, whose `routes` name another
host, or whose `account_id` is not the zone's, and a site with no GitHub remote (the no-GitHub
path is (A)).

**Launch day.** Once the site is finished (new-website §4), run:

```bash
node "$SKILLS_ROOT/new-website/scripts/cloudflare-setup.mjs" launch
```

It refuses, and asks nothing, while the Worker's version link does not serve the head of the
production branch, while at that commit `UNFILLED_UNTIL_LAUNCH` in `tests/placeholders.spec.ts`
lists a page or the draft token (`[MISSING:`, or the site's own, which `ci.yml` must search
for too) is in `src/` or `public/` (or it cannot read that test or `ci.yml` in the starter's
form), while the host has more than one address record or, below the domain itself, a record
of another type, while the host's record is a CNAME to a `*.pages.dev` address (the site is
live on Pages: the move guide applies, not this script), while the host is on another
Worker, and while the working tree has changes or HEAD is not the head of `main` on GitHub
(the route commit below is written on a clean tree, on top of `main`). While the Worker
still serves an earlier commit than the head, it waits (status 4). These are the script's
own stops; the launch check stays new-website §4 and the site's tests.

Its question names the domain, the commit, the host's record now and what happens to it: the
script **deletes that record** (Cloudflare refuses to attach a domain over one: the attach was
refused over a CNAME, an A and an AAAA record alike, observed 2026-11-12), attaches the domain
to the Worker, and Cloudflare makes the new record itself. The site becomes public, with a few
minutes of errors. The yes does this in order:

1. It saves the old record, and the zone's DNS export, in `setup-run/` in the site's folder
   (git ignores that folder; the script never deletes the file; the owner or the assistant
   may), then deletes the record.
2. It attaches the domain. If Cloudflare refuses, the same run **puts the old record back**
   and ends with 1; if even that fails, it prints the whole record and says where to add it
   by hand (DNS → Records → Add record), and every later run prints it again until the host
   has a record. A domain that does not answer yet ends the run with 4: run the same command,
   with the same code, until it does (Cloudflare takes a few minutes).
3. It writes the **route commit**: the host as a `custom_domain` route in `wrangler.jsonc`,
   as a local commit, never pushed. On the owner's word the assistant pushes it (`git push
   origin HEAD:main`) or runs `npm run ship`, so that the next build keeps the domain.
4. It asks the domain through `cloudflare-check.mjs`, looked up at the zone's own
   nameservers, which must see the commit, and runs the check on the Worker's `workers.dev`
   address and its Preview links (`--site`), as the checker says.
5. It adds the checklist's rule that removes the NEL headers (section 3, step 4) if the
   domain still sends them. `--skip nel-rule` leaves it out. Of setup's `--skip` ids, `https`,
   `bot` and `email` let that item's failure through at the end; `--skip nel` is setup's
   switch, not `--skip nel-rule`.

A yes covers the list it answered: a run that finds something more to do, the NEL rule
after a yes to the attach alone say, asks again. A run that ends with 0 prints the replaced
record, where its file is, and the way back: remove the domain from the Worker (Workers &
Pages → the Worker → Settings → Domains & Routes), add the record back, and take the host
out of `routes` in `wrangler.jsonc` in a new commit.

A launch run with nothing left to do ends with the whole check. Its status is 1 when a
request got no answer or an item could not be judged, whatever `--skip` says. It is 1 too
when an item fails, unless the run was given that item's `--skip` (`https`, `nel-rule`,
`bot`, `email`); a Web Analytics failure never counts. The report says which, and what is left
by hand.
That run also reads Bot Management once and prints setup's notes on the AI bot policies
(Training on Block, say), worded for a run that changes no AI setting; pass them on as printed.
A refused read prints one line instead, and changes neither the status nor the rest.

**By hand, always:** what `CLOUDFLARE_CHECK.md` lists under "By hand, always" (Crawler
Hints, the Web Analytics switch, the script monitor's switch, HSTS a few days after launch,
deleting the token).

**It never** merges, runs `npm run ship`, pushes, creates a Worker, or repairs a site that is
live. On launch day the one record it deletes is the host's own address record, after the
yes, and it puts that back if the attach fails; the route commit stays local. No run waits
for typed input, and none takes longer than 55 seconds.

---

## A. No GitHub connection — deploy from the owner's computer

The assistant deploys the site as a Worker with the two commands the starter ships,
`npm run deploy:preview` and `npm run deploy:live` (`scripts/deploy.sh`; Wrangler is a
dependency of the site, so `npm install` is the only setup). Nothing is connected to GitHub
and Cloudflare builds nothing: the build runs on the owner's computer, and the first deploy
makes the Worker. Two facts to know:

- **Custom domain:** it is the site's own `custom_domain` route in `wrangler.jsonc`, which
  `npm run deploy:live` attaches. The starter ships without one, so until launch the live
  `workers.dev` address stays off, and the only address that answers is the Preview link.
- **Crawler Hints / IndexNow:** [no API at all](https://community.cloudflare.com/t/how-do-i-enable-crawler-hints-through-the-api/384104) —
  it's the one dashboard toggle in `search-console-setup`, whatever deploy path you pick.

**Tradeoff — state this up front:** ongoing deploys are `npm run deploy:live` from the
owner's computer, **not** Cloudflare's git-push build that `PUBLISHING.md`'s loop assumes: a
push to GitHub publishes nothing. If the owner wants push-to-deploy afterwards, prefer (S) or
(B) now (whether a Worker made by `deploy:live` can be connected to Workers Builds later is
not checked). (A) is the right call when the priority is getting live fast with zero dashboard
time and no GitHub connection.

**Sign in to Cloudflare once,** either way:

- `npx wrangler login` opens the owner's browser, and she approves Wrangler there. No token
  to make or to delete. (Wrangler's own flow; not checked on this kit's version.)
- Or a token the owner makes, for an assistant that cannot open a browser:
  1. Dashboard → **My Profile → API Tokens → Create Token → Create Custom Token**.
  2. **Permissions:** **Account → Workers Scripts → Edit**, which uploads the Worker and
     makes it the first time (the permission's name as the checklist's section 6 gives it;
     whether `wrangler deploy` needs more rows is not checked). On
     launch day the deploy also attaches the domain, which Wrangler does with the zone's
     rows **Zone → Workers Routes → Edit** and **SSL and Certificates → Edit**, scoped to
     the one zone (the rows the Workers Builds token needs for the same step, (B) below;
     not checked for this path). There is no Crawler Hints permission.
  3. **Account Resources:** only the owner's account. **Zone Resources:** only the one target
     zone (never "All zones"). If other Workers live in that account, Workers Scripts Edit
     reaches every one of them: use a separate Cloudflare account for the site.
  4. **Expiry:** an **End date ~1 week out**, so it dies on its own.
  5. Create → copy the token (**shown once**).

### Hand a token to the agent safely — never the repo

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
4. **Confirm before each account-modifying command** — state what it will do (deploy the
   Worker `X`, delete the record `Y` and attach `Z`) and run it only on the owner's go-ahead. For the
   setup script (S), its printed question, confirmed with its code, is the confirmation for
   the changes it lists, and for nothing else.
5. **Revoke when done** — once the site is live, tell the owner to delete the token
   (My Profile → API Tokens → ⋯ → Delete), or let the expiry retire it. Don't leave a live
   token lying around. And never drive these changes through blind screen control.
6. **The deploy-time guardrails apply from this very first deploy** — the preview-vs-live
   announcements and the cached-404 rule in `templates/PUBLISHING.md` § "For AI
   assistants — deploy-time guardrails" (see the pointer in SKILL.md §4). The first
   request a brand-new custom domain sees is the one the edge caches.

### Commands you run

```bash
# 0. The account id, if Wrangler asks for it. With a token, Wrangler may stop with
#    "Failed to automatically retrieve account IDs": the token may not list accounts. The id
#    is no secret: Workers & Pages → Account Details → the copy button next to "Account ID",
#    or search (Cmd/Ctrl+K) for "Copy account ID"
#    (https://developers.cloudflare.com/fundamentals/account/find-account-and-zone-ids/).
#    A tool that runs each command in a fresh shell, as some assistants do, loses an
#    export: there, put it in front of each command (`CLOUDFLARE_ACCOUNT_ID=<account-id>
#    npm run deploy:preview`).
export CLOUDFLARE_ACCOUNT_ID=<account-id>

# 1. A Preview, to look at. It builds the files as they are and prints a Preview link.
npm run deploy:preview

# 2. The live Worker. It stops if any file is unsaved or the branch is not PROD_BRANCH
#    (src/config.ts), so the live build is exactly a commit. The first run makes the
#    Worker; the domain waits for the route of "Launch day" below.
npm run deploy:live
```

Add `-- --dry-run` to either to build and print the Wrangler command without running it.
On Windows, run these in Git Bash or WSL. The build in both commands runs as Workers Builds
runs it, with every `CF_*` and `CLOUDFLARE_*` variable removed first, so no package in the
build can read a token from the environment.

**Before launch**, the owner looks at the site on the Preview link `deploy:preview` prints,
of the form `https://<prefix>-<worker>.<account>.workers.dev` (`CLOUDFLARE_CHECK.md` says how
the checker takes it). It carries `noindex`. Until launch, the live `workers.dev` address is
off, so the Preview link is the one place to look.

**Launch day, by hand (the owner has no GitHub connection to run the setup script's launch).**
Cloudflare refuses to attach a domain while an address record stands at its name (refused over
CNAME, A and AAAA alike, observed 2026-11-12), so the domain's old record is deleted first.
The owner does that herself, in the dashboard, so each click is shown. In this order:

1. **Ready first.** The domain is already on Cloudflare ("Going live" below, if not). The owner
   has looked at the site on its Preview link, and the assistant has the attach ready: the domain's `custom_domain`
   route in `wrangler.jsonc`, committed, so that one `npm run deploy:live` attaches it.
2. **Export.** She exports the zone's DNS records (dashboard → the domain → DNS → Records →
   Import and Export → Export) and saves the file where her assistant can read it, **outside
   the site's folder** (`deploy:live` refuses a folder with an untracked file).
3. **The row.** The assistant reads the export and names the one row to delete by its type,
   name, content and proxy status, and writes down the values to add it back (DNS → Records →
   Add record). Whether the export shows the proxy status is not checked: where it does not,
   she reads it off that row in the dashboard and tells the assistant.
4. **Delete, or stop.** She deletes only a row whose dashboard line matches all four. She
   deletes nothing and stops if: there is no export file; the name is not exactly the host in
   `SITE.url`; two or more A, AAAA or CNAME rows stand at that name; the row is MX, TXT, CAA
   or NS; the row is locked (a record a Worker or Pages made); or it is a CNAME to a
   `*.pages.dev` address (the site is on Pages: the move guide applies). On a stop the
   assistant names the record to her and stops; the site stays on its Preview link.
5. **Attach.** The assistant runs `npm run deploy:live` at once. She adds the row back from
   the written values **only when the assistant says Wrangler refused the domain**. If the
   deploy went through but `deploy:live`'s check after it timed out, or the assistant cannot
   tell, she adds nothing back and stops, as in item 4: an attach still under way could meet
   the restored row. The assistant tells her where the host stands (the Worker's Settings →
   Domains & Routes, DNS → Records).

What to expect: the domain answers nothing from the delete until the attach takes. By the
setup script the attach took 28 to 39 seconds on a rehearsal; by hand it is a few minutes (not
checked), so she picks a quiet hour. Then continue with `search-console-setup` for GSC/Bing +
Crawler Hints. Before handoff, add one sentence to the site README's "Deploy" paragraph: this
site deploys by command, with no GitHub connection in Cloudflare (Worker `<worker>`), and
`PUBLISHING.md`, "Deploy by command", has the steps. That sentence is how the owner, and the
next assistant, can tell.

---

## B. GitHub Workers Builds, by hand — if the owner wants push-to-deploy and the setup script is not used

One-time guided dashboard connect, then `git push` builds automatically — the model
`PUBLISHING.md` assumes. The setup script (S) reads the same kind of Worker and writes the
checklist's settings as well; this is the way by hand (labels as row 0.4 saw them; not
re-checked since):

Cloudflare → **Workers & Pages → Create → Import a repository** → pick the repo. The Worker's
name comes from `wrangler.jsonc`; build command `npm run build`. For a two-stage site, set the
**production branch** to `production` (see new-website §4), and leave **Preview builds** on:
connecting builds the production branch straight away, so leaving it at `main` would publish
the preview first.

**The build token.** Under Advanced settings, the API token field picks an existing token by
default: choose **Create new token**, so this Worker has a token of its own. Then cut it down in
place, on the profile page's API Tokens: account **Workers Scripts → Edit** and **Account
Settings → Read**; user **Memberships → Read** and **User Details → Read**; and, for the
site's own zone only, **Workers Routes → Edit** and **SSL and Certificates → Edit**. Anything
that runs in a build (any npm package) can read that token, and Workers Scripts Edit reaches
every Worker in the account: **an owner who already runs other Workers in that account uses a
separate Cloudflare account for the site.** This token set has not yet been proven by a build of a new site (not checked).

## C. Browser-assisted or manual walk-through — the fallback

If the owner won't mint a token and won't do the dashboard alone: drive the dashboard via
your runtime's browser automation (**Claude in Chrome** under Claude Code; the agent's own
browser tool otherwise — see `search-console-setup`), or read them the clicks one by one.
Both work; both eat time and patience — which is why **(S) is recommended**.

---

## After the first deploy: no daily limit to set

A Worker with no script runs no code, so a request for a page or a file is not a script run,
and there is no daily limit to set for. Cloudflare states that requests for static assets are
free and unlimited ([static assets billing](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/);
the kit has not counted this on a live site). A site still on Pages has a setting for its
Functions limit: "After the first deploy, whichever option: set "Fail open"" in the last section.

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
     for the domain (including its custom domain on the Worker). If any CAA records exist, **confirm
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

> **The domain's own address record is the one record launch day replaces.** A custom domain on
> a Worker is attached through the Worker, never by a DNS record alone, and Cloudflare refuses
> the attach while an address record stands at that name: (S)'s launch and (A)'s launch day
> delete it first, and put it back if the attach fails.

> **Make rollback cheap — and don't tear the old setup down yet.** Lower the record TTLs at
> the old provider ~24h *before* the move. After the flip, **keep the old zone, site, and mail
> running through the propagation window** — resolvers may serve cached DNS for a while, so you
> want an instant fall-back. Only retire the old setup once the new domain is confirmed
> resolving and mail flows both directions.

> Drive these changes *with* the owner, not through blind screen control — same guardrail as
> the bootstrap token steps above.

---

## Sites already on Pages

Everything above is for a new site, which is a Worker. A site made before 0.35 is on Cloudflare
Pages and stays there until it moves. What it still needs is gathered here, under the headings
the rest of the kit refers to.

**Moving a Pages site to Workers:** `docs/MOVE-TO-WORKERS.md` is the owner's guide, and
`references/CLOUDFLARE_MOVE.md` tells an assistant when to run each command of
`scripts/move-to-workers.mjs`. The first stage of a move is a Worker serving the live commit
with no domain yet. For a site still on Pages that Worker is made by Workers Builds, set up as
in "B. GitHub Workers Builds, by hand" above, with the Workers files of the 0.35 starter; the guide has no
`npm run deploy:live` path for that stage.

**A site set up on Pages but not launched** switches to a Worker before launch: it takes the
new site's Workers files (`wrangler.jsonc`, the deploy scripts, the starter's changed
config), and launches by (S) or (A) above. Nothing about it is moved, because no domain is on
Pages yet. The setup script refuses a host whose record is a CNAME to a `*.pages.dev` address
and points to the move guide: that site is live on Pages.

### A, Pages form: token-assisted bootstrap with Wrangler's direct upload

For a Pages site that deploys by command, with no GitHub connection in Cloudflare. The owner
mints **one scoped, expiring API token**; the agent runs Wrangler to create the project and
deploy. The guardrails under "A. No GitHub connection" above apply to this token too. Two doc facts (confirmed
against current Cloudflare docs, June 2026):

- **Custom domain:** Wrangler has *no* Pages custom-domain command
  ([workers-sdk#11772](https://github.com/cloudflare/workers-sdk/issues/11772) is open),
  but the **Pages REST API can attach it with the same Pages-Edit token**.
- **Crawler Hints / IndexNow:** no API at all: the one dashboard toggle in `search-console-setup`.

**Tradeoff:** this uses Wrangler's **direct-upload** deploy model. Ongoing deploys are then
`wrangler pages deploy`, **not** Cloudflare's git-push auto-build that `PUBLISHING.md`'s loop
assumes. A direct-upload project and a Git-connected project are *different Pages project
types*.

**The token:** dashboard → **My Profile → API Tokens → Create Token → Create Custom Token**.
Permissions, only what the steps need: **Account › Cloudflare Pages › Edit** (a.k.a.
`Pages Write`) to create the project, deploy, **and** attach a custom domain via the Pages REST
API (`POST /accounts/{id}/pages/projects/{name}/domains`); **Zone › DNS › Edit**, scoped to
the **one** zone, only if the flow also creates or changes DNS records itself. Account
Resources: only the owner's account; Zone Resources: only the one target zone (never "All
zones"). An **End date ~1 week out**. Provide it as a session env var, as in A. above.

```bash
# 0. The account id, set the same way as the token. With a token, Wrangler may stop with
#    "Failed to automatically retrieve account IDs": the token may not list accounts. Seen
#    on 2026-10-16 (wrangler 4.151.0, a token with the Pages Edit row and zone rows); it ran
#    once the id was set. The id is no secret: Workers & Pages → Account Details → the copy
#    button next to "Account ID", or search (Cmd/Ctrl+K) for "Copy account ID"
#    (https://developers.cloudflare.com/fundamentals/account/find-account-and-zone-ids/).
#    Set it for every command below. A tool that runs each command in a fresh shell, as
#    some assistants do, loses the export: there, put it in front of each wrangler command
#    (`CLOUDFLARE_ACCOUNT_ID=<account-id> npx wrangler pages …`), as the 2026-10-16 run did.
export CLOUDFLARE_ACCOUNT_ID=<account-id>

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

> **`pages deploy`, not plain `deploy` — or you get a `workers.dev` URL.** On a Pages site
> every command above is `wrangler pages …` and the deploy must print a
> **`<project>.pages.dev`** URL. A bare `wrangler deploy` (no `pages`) publishes a **Worker**
> and hands back a `*.workers.dev` URL instead — a real mistake we've seen on an older kit
> version. If you see `workers.dev` on a site that is meant to stay on Pages, stop: you
> deployed the wrong project type. Confirm it's the accidental Worker (not a pre-existing one
> with a similar name), then delete it and re-run `wrangler pages deploy`.

Ongoing deploys under (A), Pages form: with `CLOUDFLARE_ACCOUNT_ID` set as in step 0, re-run both lines of step 2, `CF_PAGES_BRANCH=` still included —
`CF_PAGES_BRANCH=<production-branch> npm run build`, then
`wrangler pages deploy dist --project-name <project> --branch <production-branch>`.
The owner's version, for after handoff, is `templates/PUBLISHING.md`, "Deploy by command":
keep the two in step: both build with `CF_PAGES_BRANCH=<production-branch>` and deploy
with the same `--branch`. Before handoff, add one sentence
to the site README's "Deploy" paragraph: this site deploys by command, with no GitHub
connection in Cloudflare (project `<project>`, production branch `<production-branch>`), and
`PUBLISHING.md`, "Deploy by command", has the steps.

### After the first deploy, whichever option: set "Fail open"

On a Pages site, Cloudflare serves static files free and without limit only while no Function runs. The
kit's (before 0.35) `functions/_middleware.ts` sits at the root of `functions/`, and Pages then runs it in
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
  untouched, unless analytics runs in server mode: then counting stops for the rest of
  that day, and the email links, which go through `/go/email`, do not open the mail
  program until midnight UTC (with no Function, no page answers `/go/email`, so the visitor
  should get the site's 404 page; reasoned from how Pages serves files, not tested). Previews still carry the `X-Robots-Tag: noindex` that Cloudflare adds to every
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

### Attaching a Pages custom domain

> **Pages: attach the custom domain in the project — a DNS record alone isn't enough.** For a
> Pages site, just adding a CNAME/record that points at `<project>.pages.dev` does **not**
> connect the domain; the domain must be added through the Pages **Custom domains** flow
> (dashboard, or the REST API in (A), Pages form) or visitors get a **522**. And once it's attached, don't
> "test" by pointing the record away from Pages and back — Cloudflare can serve errors until
> it reactivates; use a redirect/origin rule for any temporary routing instead.

### After go-live: send `<project>.pages.dev` to the live domain

The setup script does not do these steps: it sets up Workers only, and a Worker has no
`pages.dev` address. They are for a site on Pages.

Every Pages project also serves production at its own alias, `<project>.pages.dev`.
Cloudflare usually makes it from the project's name, but not always (when the name is taken
it adds to it): read the address on the project's page and use it wherever
`<project>.pages.dev` stands below. In a Wrangler command, `<project>` stays the project's
name. The
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
   ((A), Pages form): re-run `npx wrangler pages deploy dist --project-name <project> --branch
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

**Sites scaffolded before this redirect existed** need the newer `functions/_middleware.ts`
first. The 0.35 starter no longer has it: take it from the 0.34 release of the kit
(`skills/new-website/templates/astro/functions/_middleware.ts` in the tag `v0.34` of
https://github.com/karero/croftweaver) and commit it, but don't
push until step 1 is saved: on a single-stage site that push is the production deploy.
Then do steps 1–3; that commit is the new commit step 2 needs. Nothing changes on a live site until that
redeploy.

After the switch, the alias no longer shows the latest production build. To check a build
went Active, use `wrangler pages deployment list` or the deployment's hash URL
(`<hash>.<project>.pages.dev`), never the live domain (see `PUBLISHING.md`).
