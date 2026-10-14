# Cloudflare checklist: the settings your site relies on

Your Croftweaver site runs on Cloudflare Pages. Most of it works out of the box. A handful
of settings decide whether your privacy page stays true, whether search engines and AI
assistants can reach your pages, and whether visitors connect safely. Go through this list
once after the first deploy, and again whenever Cloudflare redesigns its dashboard. Two
items wait: HSTS waits a few days, and the `.pages.dev` forward waits until your own domain
serves the site.

**Fastest way.** Your assistant can make most of these changes for you with one
short-lived token. Section 6 shows how.

**How to read the paths.** `→` means "click". The dashboard is dash.cloudflare.com. Some
settings belong to your **domain** (click your domain's name in the list first), some to
your **Pages project** (Workers & Pages → your project), and some to your **account**. Where
a path says "Security → Settings → filter by …", you land on one long page of settings with
a filter box: pick the filter, then find the setting by name.

The paths come from Cloudflare's own documentation, read on 2026-10-12 (the AI switches in
section 4 and the script monitor in section 3 on 2026-10-14), and from
[`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md)
for three project steps in section 1 (attach the domain, Fail open, and the
`CANONICAL_URL` variable under Production). None was re-checked in a dashboard for this
list. Cloudflare moves things around. If a name differs, search the dashboard for the
setting's name.

---

## 1. Set up the site

**While you create the project** (Workers & Pages → Create application):

- [ ] **Create a Pages project, not a Worker.**
  Workers & Pages → Create application → **Pages** → Connect to Git.
  As of October 2026 the create screen shows **Workers** in the big box and **Pages** only
  as a small line of text beneath it. That small line is the one you need. If you pick the
  big box you get a Worker, and the steps in this kit won't fit. The address tells you
  which you have: a Pages site answers on `<project>.pages.dev`, a Worker on a
  `.workers.dev` address. If the screen looks different, look for the word Pages. (The
  other ways to deploy are in
  [`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md).)
- [ ] **Build settings:** framework preset **Astro**, build command `npm run build`, output
  directory `dist`. A two-stage site: set **Production branch** to `production` on this
  same form, or it publishes the preview first. To change it later: your project →
  Settings → Builds & deployments → Configure Production deployments, then **Save**. That
  path is for projects connected to Git. A Direct Upload project has no such option: ask
  your assistant.

**After the first deploy:**

- [ ] **Attach your domain to the project.**
  Workers & Pages → your project → Custom domains → Set up a domain.
  A DNS record on its own is not enough: without this step visitors get an error 522.
- [ ] **Set Fail open.**
  Workers & Pages → your project → Settings → Runtime → Fail open / closed → **Fail open**.
  Then the site stays online if the free plan's daily Functions allowance runs out.
  Cloudflare has hidden this setting at times. If you don't see it, tell your assistant
  and don't assume the site stays up: the section on Fail open in
  [`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md)
  has the history.

**Once your own domain serves this site** (Active, and `https://yourdomain.com/build.txt`
shows the current build):

- [ ] **Send the `<project>.pages.dev` address to your live domain (301).**
  Ask your assistant to do this. It sets a plain-text variable `CANONICAL_URL` to your live
  address, `https://` and your own domain with nothing after it, under your project →
  Settings → Variables and Secrets → **Production**. Then it publishes the production site
  again: a variable reaches only deployments made after it was set, and a plain commit
  does not publish production on a two-stage site or a Direct Upload project. "After
  go-live" in
  [`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md)
  has the steps for each kind of project. Browsers remember a 301, so a wrong address
  keeps sending visitors to the wrong place after you correct it: the assistant opens
  `build.txt` on that address first, as that section says.
  *Why:* without it the same site answers on two addresses, and the kit's notes say AI
  search engines have been seen citing the `.pages.dev` one. A site scaffolded before this
  redirect existed needs the newer `functions/_middleware.ts` first (same section of that
  file). Preview deployments keep answering 200 with `noindex`. That is meant.
  *Check:* the last command in section 5.

Moving an existing domain, with its mail, to Cloudflare is a bigger job: see "Going live"
in [`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md).

## 2. Safe connections (your domain)

- [ ] **Always Use HTTPS: On.**
  Your domain → SSL/TLS → Overview (check the encryption mode is not Off) → Edge
  Certificates → Always Use HTTPS.
- [ ] **Minimum TLS Version: TLS 1.2.**
  Your domain → SSL/TLS → Edge Certificates → Minimum TLS Version. Leave TLS 1.3 on.
  TLS 1.2 is the kit's choice; Cloudflare's page names no recommendation. Devices that
  speak only TLS 1.0 or 1.1 get no connection. Cloudflare's page also says this can't be
  configured for Cloudflare Pages hostnames, so if the TLS check in section 5 still shows
  TLS 1.0 or 1.1 as "Yes", tell your assistant.
- [ ] **HSTS: On, and last.** Do this one when the site has been live and working for a
  few days: browsers remember it, so it removes the easy way back to plain HTTP.
  Your domain → SSL/TLS → Edge Certificates → HTTP Strict Transport Security (HSTS) →
  Enable HSTS. Confirm the warning (**I understand**, **Next**), set these, and **Save**:
  - **Max Age Header:** 6 months. If the domain moved recently, start with 1 month; the
    setting allows 1 to 12.
  - **Apply HSTS policy to subdomains:** On only if every subdomain you use works over
    HTTPS. A mail or other tool on a subdomain may not. If unsure, Off.
  - **Preload:** Off. It needs a max age of 12 months, and Cloudflare's page warns it can
    make a site without HTTPS completely inaccessible.
  - **No-Sniff Header:** Off. The starter already sends `X-Content-Type-Options: nosniff`.

  HSTS also leaves a note in the browser. Its only job is to keep the visitor's own
  connection on HTTPS, and it sends nothing anywhere. If your privacy page says that
  nothing at all is stored on the visitor's device, that is then no longer literally true:
  ask your assistant to add a line about it. That is our judgment, not a ruling. Once HSTS
  is on, don't switch the domain's records to "DNS only", pause Cloudflare, move the
  nameservers away or turn SSL off: if your site then has no working HTTPS, browsers
  refuse it until the max age runs out.

## 3. Keep the privacy page true: no cookies, scripts or tracking you didn't choose

Your privacy page says what the site sets and runs: no cookies, and at most the one
measurement tool you chose when the site was built. These settings stop Cloudflare adding
cookies, scripts or tracking you didn't choose.

- [ ] **Network Error Logging (NEL): Off.** A look, a switch, a check, a rule if the
  header is still there, and a second switch for Cloudflare's script monitor.
  *What it is:* the browser keeps a note, and if it can't reach your site it sends a short
  error report to Cloudflare. Chrome, Edge and other Chromium browsers do this; Firefox
  and Safari don't. When we looked on 12 October 2026, Cloudflare's header set the note to
  seven days (604800 seconds) and asked for failures only.
  *Why off:* your page doesn't need it, the privacy page this kit writes doesn't mention
  it, and it makes the visitor's browser send reports to Cloudflare. In Germany, § 25
  TDDDG asks for consent for storing information on a visitor's device or reading it back,
  unless that is strictly necessary for a service the visitor expressly asked for. We found
  no ruling or guidance on NEL specifically (searched October 2026), so whether it reaches
  NEL is untested. This is a risk, not a verdict, and this is not legal advice. Off avoids
  the question.
  *It can be on without you ever choosing it.* Check, don't assume (section 5).
  1. **Look first.** Run the first command in section 5. If it shows a `nel:` line, note
     the `max_age` number in it: it is how many seconds visitors keep the note.
  2. **The switch.** Cloudflare's guide: Account home → Network → Network Error Logging
     Monitoring. If your dashboard shows **Network** only after you open your domain, use
     it there. Switch it **Off**. Any zone administrator can switch it back on. If the
     switch is missing or greyed out, go straight to step 4.
  3. **Check.** Run the same command again. The `nel:` and `report-to:` lines should be
     gone. A `nel:` line, or a `report-to:` line that names `cf-nel`, is still NEL: step 4,
     whatever else the command shows. A `report-to:` line that sends to an address on
     `csp-reporting.cloudflare.com` is Cloudflare's script monitor: step 5.
  4. **If they are still there, add a rule that removes them.** When we tried this on a
     Pages site, the switch alone did not stop the header: the setting read "off" through
     Cloudflare's API, and the header was still served half an hour later. Your domain →
     Rules → Overview → Create rule → **Response Header Transform Rule**. Name it "Remove
     NEL headers". Under *When incoming requests match*, choose **All incoming requests**.
     Under *Modify response header*, choose **Remove** and enter the header name `NEL`.
     Select **Set new header**, choose **Remove** again and enter `Report-To`. **Deploy.**
     On the same site this removed both headers within seconds. The rule is set to remove
     `Report-To` from every response, so if your site later sets reporting groups of its
     own, narrow the rule first.
  5. **Switch off Cloudflare's script monitor too, whatever the command showed.**
     Your domain → Security → Settings → filter by **Client-side abuse** →
     **Continuous script monitoring**. Cloudflare's page shows turning it on; this is the
     same switch.
     *What it is:* Cloudflare says it adds a `content-security-policy-report-only` header to
     a sample of pages, and that the visitor's browser then sends reports to Cloudflare
     ([how it works](https://developers.cloudflare.com/client-side-security/how-it-works/)).
     It is not NEL. On the one site where we saw it, the answers that carried it also had a
     `report-to:` line that names `cf-csp-endpoint` and sends to
     `csp-reporting.cloudflare.com`: 2 of 40 answers on 14 October 2026. Step 4's rule had
     been set there on 12 October. We did not read it when we counted, so we can't say
     whether it was working then.
     *Why off:* the visitor's browser sends reports to Cloudflare, and the privacy page this
     kit writes doesn't mention it. If you keep it on, say so on your privacy page.
     *Check:* it comes on a sample, so one answer without it shows nothing. Switch it off,
     then count with the loop in
     [`CLOUDFLARE_CHECK.md`](../skills/new-website/references/CLOUDFLARE_CHECK.md), with
     your own domain. The count should read `100 clean` (after we switched it off we made
     200 requests and saw no `report-to:` line). An `other` line did not count: tell your
     assistant what the line says. The reference says which address to use. If you can't
     find the switch, or a `header` count shows after you switched it off, tell your
     assistant.
     *The trade-off:* you give up Cloudflare's view of the scripts your visitors load. The
     switch may be marked Global. If it says so, it may apply to every domain in your
     account: look at your other sites before you switch it off.

  Visitors who came in before can keep the old NEL note until that many seconds have
  passed (the `max_age` from step 1; 604800 seconds is seven days). The
  `<project>.pages.dev` address is outside your domain, so the rule can't reach it, and we
  have found no way to remove the headers there. Sending that address to your live domain
  (section 1) moves visitors on; it removes nothing. The last command in section 5 shows
  whether that address still sends them. If a `nel:` line, or a `report-to:` line that
  names `cf-nel`, is still there on your own domain after the rule, tell your assistant or
  ask Cloudflare Support. Cloudflare's support article describes a flag, `nel___enable`,
  that stops NEL being enabled on a zone.
- [ ] **Bot Fight Mode: Off.**
  Your domain → Security → Settings → filter by **Bot traffic** → Bot fight mode.
  *Why:* Cloudflare says JavaScript detections come with it and can't be switched off.
  They add a script (`/cdn-cgi/challenge-platform/…`) to your pages and set the cookie
  `cf_clearance`; the bot score uses `__cf_bm`. A static site has little to protect from
  bots. The trade-off: simple bots are no longer challenged, so more of them reach your
  site, and each page view counts against the free daily Functions allowance (see Fail
  open).
- [ ] **Cloudflare Web Analytics: Off.** This is Cloudflare's own measurement, separate
  from any tool you chose for the site. Two places, check both:
  - Workers & Pages → your project → Metrics → Web Analytics. This is where you would
    switch it on, so it should offer **Enable**, not show data.
  - Web Analytics → Manage site → Disable. If your domain isn't listed there, there is
    nothing to disable.

  Cloudflare describes an "automatic setup" for sites that run through it, which adds a
  measurement script to your pages. After you disable it, deploy again and check the page
  source (section 5).
- [ ] **Email Address Obfuscation: Off.**
  Your domain → Security → Settings → filter by **Client-side abuse** → Email Address
  Obfuscation.
  *Why:* Cloudflare turns it on when you sign up. It rewrites the plain email addresses it
  finds in your pages, mail links included, and adds a script (`email-decode.min.js`). The
  kit already hides addresses.

## 4. Be found, by search engines and AI assistants

- [ ] **Crawler Hints: On.**
  Your domain → Caching → Configuration → Crawler Hints.
  Bing and the other search engines that use IndexNow hear about new and changed pages
  soon after. Google learns about changes another way, which `search-console-setup`
  covers. With a Bing Webmaster Tools account
  ([`search-console-setup`](../skills/search-console-setup/SKILL.md) walks you through it)
  you can watch the notifications arrive.
- [ ] **AI crawlers: allow.**
  Your domain → Security → Settings → filter by **Bot traffic** → **Configure AI bot
  policies** → set **Search**, **Agent** and **Training** each to **Allow (do not block)**.
  Search and Agent let assistants find and read your pages. Training means crawlers that
  gather text to train AI models: Allow is the kit's default, and opting out is your
  choice. Cloudflare's page says a block on Training also blocks crawlers that combine
  Search and Training. Its defaults for new domains, from 15 September 2026, block
  Training and Agent crawlers on pages that show ads. Look at what yours shows. If you
  still see the older **Block AI bots** setting, make sure it is Off. Cloudflare is
  retiring it. (`search-console-setup` still shows the older names, Security → Bots →
  Control AI crawlers. This list is the newer one.)
  Three more switches can keep AI crawlers out. Set each to off, with the one exception
  under Bot Preference Sync:
  - **Bot Preference Sync: Off, unless you block Training.** Same place: Configure AI bot
    policies → **Enable Bot Preference Sync**. This is Cloudflare's managed `robots.txt`:
    when a policy is set to block or disallow, it puts Cloudflare's own lines for AI
    crawlers, and a `Content-signal` line, in front of your file, or writes a file if you
    have none. The file the kit made already says who may read your site. If you chose to
    block or disallow Training, this switch is what writes that into `robots.txt`: then
    leave it on. Cloudflare's settings page lists a setting called **Instruct AI bot
    traffic with robots.txt** and links it to the documentation page for this switch.
    Section 5 shows the file.
  - **AI Labyrinth: Off.** Your domain → Security → Settings → filter by **Bot traffic** →
    **AI Labyrinth**. It adds invisible links to your pages that lead AI crawlers which
    ignore crawl rules and crawl without permission into an endless maze. Cloudflare says
    only bots see the links and they don't affect your search ranking. Off is the kit's
    choice: the file the kit made lets every crawler in, and we would rather your pages
    carry only links you wrote.
  - **Content bots: Off.** We found no page in Cloudflare's documentation that names this
    switch or says where it is in the dashboard (searched 14 October 2026). Cloudflare's
    API describes it as a rule that blocks automated traffic with low bot scores, apart
    from verified bots in safe categories, so it can also refuse an AI crawler. If your
    **Bot traffic** list shows a switch for content bots, turn it off. If not, ask your
    assistant to read it through the API (section 6).

## 5. Check your work

Run these once your own domain serves this site: the production deployment shows
**Active** (your project → Deployments), the custom domain is Active, and
`https://yourdomain.com/build.txt` shows the current build. Earlier, the live domain
serves the previous deployment or an error, and the kit's notes describe such a 404 being
cached at Cloudflare's edge ("Never request a page on the live domain before its build is
Active" in [`PUBLISHING.md`](../skills/new-website/templates/PUBLISHING.md)). Don't run
them earlier. Replace `yourdomain.com` with your domain and `yourproject` with your Pages
project's name (the first part of its `.pages.dev` address). Before you trust any answer,
make sure the domain in the command is yours: a placeholder left in can reach a stranger's
site and print a clean-looking 200, and the robots.txt below must be your own file. An
empty answer is never a pass either: it means curl could not reach the site. Your
assistant can run them; on Windows use Git Bash or WSL. A script runs all of them at once,
and lists the items that only the dashboard shows
([`CLOUDFLARE_CHECK.md`](../skills/new-website/references/CLOUDFLARE_CHECK.md) says how).

```bash
curl -sI "https://yourdomain.com/?cb=$(date +%s)" | grep -iE '^(HTTP/|nel:|report-to:|strict-transport-security:|set-cookie:)'
```

You want a 200 status line (`HTTP/2 200`, or `HTTP/1.1 200 OK` on an older curl) and
nothing else until you switch HSTS on (section 2). A 3xx status line is not the 200 you want:
find out what answers with it, and why, before you trust the rest. A `nel:` line
means NEL is still on, and so does a `report-to:` line that names `cf-nel`. A `report-to:`
line that sends to an address on `csp-reporting.cloudflare.com` is Cloudflare's script
monitor (section 3, step 5), and a clean answer does not show it is off. A `report-to:`
line of your own is yours to judge. A `set-cookie:` line means
something is setting a cookie: tell your assistant. Once HSTS is on you also want a
`strict-transport-security:` line with `max-age=` followed by the seconds for the months
you chose (for six months we saw 15552000), with `; includeSubDomains` after it only if you
turned that option on. This check can't see cookies a browser receives only after it runs a
script, such as `cf_clearance`; the source search below covers that.

```bash
curl -s https://yourdomain.com/robots.txt
```

You want your own file: the starter's begins `User-agent: *` and ends with a `Sitemap:`
line that names your own domain, not the starter's `example.com`. It should have no
AI-crawler `Disallow` lines you didn't write, other than ones from a policy you set to
block or disallow. If Cloudflare's own lines for AI crawlers show and you didn't ask for
them, tell your assistant: Cloudflare can add a managed `robots.txt` (Bot Preference Sync,
section 4).

```bash
curl -sI http://yourdomain.com/ | grep -iE '^(HTTP/|location:)'
```

You want a redirect (301 or 308) and a `location:` line that starts
`https://yourdomain.com/`. The slash matters: `https://yourdomain.com.au/` is a different
site. A status line with no `location:` line means there is no redirect.

```bash
curl -sI "https://yourproject.pages.dev/?cb=$(date +%s)" | grep -iE '^(HTTP/|location:|nel:|report-to:)'
```

Run this one only after you set `CANONICAL_URL` and published again (section 1). You want a
301 and a `location:` line that starts `https://yourdomain.com/`. A 200 means one of: the
variable isn't under Production, it is misnamed, the deployment is older than the variable,
the site predates the redirect, the value isn't one the redirect accepts (it must start
`https://`, must not be a pages.dev address and must not have an empty part such as
`example..com`), or the day's Functions allowance ran out and Fail open is serving the
files without the redirect until midnight UTC. If `nel:` or `report-to:` lines show on
this address, the rule in section 3 doesn't reach it: that address belongs to Cloudflare,
not to your domain. Tell your assistant; we have found no way to remove them there.

- **No scripts you didn't add:** open your home page, view the source, and search for
  `cdn-cgi`, `email-decode` and `cloudflareinsights`. None should be there.
  `cdn-cgi/challenge-platform` is Bot Fight Mode, `email-decode` is email obfuscation,
  `cloudflareinsights` is Web Analytics.
- **TLS:** run your domain through ssllabs.com/ssltest. TLS 1.0 and 1.1 should say "No".
- **No outside check exists** for Crawler Hints (Caching → Configuration) or Fail open
  (your project → Settings → Runtime). Look at both in the dashboard.

Not covered here: DNS and email records (see "Going live" in
[`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md))
and protecting your Cloudflare account (your site's `SETUP.md`).

## 6. Let your assistant do it: one short-lived token

Most of sections 1 to 4 are settings an assistant can change for you through Cloudflare's
API. A token only gives permission: the changes happen when your assistant makes the API
calls, one at a time. If you would rather not click through the dashboard, make one token,
hand it to your assistant for an afternoon, and delete it afterwards. HSTS is not part of
that afternoon: switch it on a few days after go-live (section 2), with a second token or
by hand. Setting `CANONICAL_URL` waits too, until your own domain serves the site (section
1).

**Make the token.** My Profile → API Tokens → Create Token → Create Custom Token. Add these
permission rows, each set to **Edit** except the Zone → Read row (a read-only token can
look but not change anything):

| Permission row | What it lets the assistant set |
|---|---|
| Zone → Zone Settings → Edit | Always Use HTTPS, Minimum TLS Version, Email Address Obfuscation, the NEL switch |
| Zone → Transform Rules → Edit | the rule that removes the NEL headers |
| Zone → Bot Management → Edit | Bot Fight Mode, the AI crawler policies and the three switches after them (`bot_preference_sync_enabled`, `crawler_protection`, `content_bots_protection`), all on Cloudflare's [Bot Management update](https://developers.cloudflare.com/api/resources/bot_management/methods/update/) call |
| Zone → Zone → Read | finding your domain by name |
| Account → Cloudflare Pages → Edit | only if it also creates the project, attaches the domain, deploys, or sets `CANONICAL_URL` (option A in [`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md) covers creating and deploying) |

Cloudflare documents these calls. We have run the Transform Rules call on live sites and
the Bot Management call on one spare domain, and we have not run any of them often, so for every call the
assistant should read each setting back, and you run section 5.
Bot Preference Sync is the field `bot_preference_sync_enabled`. A trial on that spare
domain (14 October 2026) set it with the Bot Management update call. With it on and
Training disallowed, Cloudflare put its own lines in front of the site's `robots.txt`; set
to off, the site's own file came back within seconds. A similar field,
`is_robots_txt_managed`, did not do that: the same call refused to set it to `true` (code
10400), and accepted it as `false`. The trial's record, with its captures by number, is in
`docs/reviews/SKILL-PLAN-cloudflare-setup.md` ("Seen in the second trial").

Then set **Zone Resources** to your one domain and **Account Resources** to your account
only (Pages Edit covers the whole account). Set **TTL** to an end date of tomorrow, a week
at most, with no start date: a start date in the future makes every call fail with
"Authentication error". Create the token and copy it. Cloudflare shows it once.

**Hand it over safely.** The rules in `CLOUDFLARE_FIRST_DEPLOY.md` ("Assistant guardrails")
hold here too. Tell your assistant you have the token. It shows you where to put it: an
environment variable for the session, or a file the repository ignores. Don't paste it
into email, a document or a chat other people can read. Never commit it, and never put it
in a file the repository tracks or in the README. Ask the assistant to look before it
writes, to tell you each change before it makes it, and to read each setting back
afterwards. Some changes replace a whole list, as the Transform Rules do: it must read
what is there and send it back with the change. A change to one variable may replace the
project's others: it must list the variables before and after, and stop and tell you if
any is missing, because it may not be able to put them back. If the API refuses a setting
(some are limited to certain plans), or it can't be sure the project's other variables are
kept, do that item by hand from sections 1 to 4.

**Then check it yourself.** Before you delete the token, run the commands in section 5 and
look at the output. An API can say a setting is off while the site still sends the header,
as it did for NEL on the site we tried.

**What stays by hand:** Crawler Hints (the kit's notes say Cloudflare has no API for it),
the off switch for Cloudflare Web Analytics, the script monitor's switch (section 3, step
5; we did not look for an API call for it), and the Pages choice on the create screen if
you connect through Git.

**When it is done,** delete the token: My Profile → API Tokens → ⋯ → Delete. Then ask the
assistant for a short report: each setting, what it was, what it is now, and why.

---

Sources, read 2026-10-12: Cloudflare's
[Pages: create a project](https://developers.cloudflare.com/pages/get-started/git-integration/),
[Pages branch and build controls](https://developers.cloudflare.com/pages/configuration/branch-build-controls/),
[Always Use HTTPS](https://developers.cloudflare.com/ssl/edge-certificates/additional-options/always-use-https/),
[Minimum TLS version](https://developers.cloudflare.com/ssl/edge-certificates/additional-options/minimum-tls/),
[HSTS](https://developers.cloudflare.com/ssl/edge-certificates/additional-options/http-strict-transport-security/),
[Network Error Logging](https://developers.cloudflare.com/network-error-logging/get-started/),
[turning NEL off](https://developers.cloudflare.com/support/network/understanding-network-error-logging/),
[Response Header Transform Rules](https://developers.cloudflare.com/rules/transform/response-header-modification/create-dashboard/),
[updating a ruleset](https://developers.cloudflare.com/ruleset-engine/rulesets-api/update/),
[Bot Fight Mode](https://developers.cloudflare.com/use-cases/application-security/bots/stop-malicious-bots/),
[JavaScript detections](https://developers.cloudflare.com/bots/additional-configurations/javascript-detections/),
[Cloudflare cookies](https://developers.cloudflare.com/fundamentals/reference/policies-compliances/cloudflare-cookies/),
[Web Analytics](https://developers.cloudflare.com/web-analytics/get-started/),
[Pages Web Analytics](https://developers.cloudflare.com/pages/how-to/web-analytics/),
[Email Address Obfuscation](https://developers.cloudflare.com/waf/tools/scrape-shield/email-address-obfuscation/),
[Crawler Hints](https://developers.cloudflare.com/cache/advanced-configuration/crawler-hints/),
[Block AI bots](https://developers.cloudflare.com/bots/additional-configurations/block-ai-bots/),
[managed robots.txt](https://developers.cloudflare.com/bots/additional-configurations/managed-robots-txt/),
[creating an API token](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/),
[API token permissions](https://developers.cloudflare.com/fundamentals/api/reference/permissions/),
the API reference for [zone settings](https://developers.cloudflare.com/api/resources/zones/subresources/settings/methods/edit/),
[Bot Management](https://developers.cloudflare.com/api/resources/bot_management/methods/update/)
and [editing a Pages project](https://developers.cloudflare.com/api/resources/pages/subresources/projects/methods/edit/);
MDN's [Network Error Logging](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Network_Error_Logging)
and its [browser compatibility data](https://github.com/mdn/browser-compat-data/blob/main/http/headers/NEL.json);
[RFC 6797](https://www.rfc-editor.org/rfc/rfc6797) (HSTS) and
[§ 25 TDDDG](https://www.gesetze-im-internet.de/ttdsg/__25.html).
Read 2026-10-14, for the three AI switches in section 4: Cloudflare's
[AI Labyrinth](https://developers.cloudflare.com/bots/additional-configurations/ai-labyrinth/)
and [Security settings](https://developers.cloudflare.com/security/settings/) pages, and
the managed robots.txt page and the Bot Management API reference again.
Read 2026-10-14, for the script monitor in section 3: Cloudflare's client-side security
[how it works](https://developers.cloudflare.com/client-side-security/how-it-works/) and
[get started](https://developers.cloudflare.com/client-side-security/get-started/) pages,
and the Security settings page again.
