# Cloudflare checklist: the settings your site relies on

Your Croftweaver site runs on Cloudflare Pages. Most of it works out of the box. A handful
of settings decide whether your privacy page stays true, whether search engines and AI
assistants can reach your pages, and whether visitors connect safely. Go through this list
once, after the first deploy, and again whenever Cloudflare redesigns its dashboard.

**Fastest way.** Your assistant can make most of these changes for you with one
short-lived token. Section 6 shows how.

**How to read the paths.** `→` means "click". The dashboard is dash.cloudflare.com. Some
settings belong to your **domain** (click your domain's name in the list first), some to
your **Pages project** (Workers & Pages → your project), and some to your **account**. Where
a path says "Security → Settings → filter by …", you land on one long page of settings with
a filter box: pick the filter, then find the setting by name.

The paths come from Cloudflare's own documentation, read on 2026-10-12, and from
[`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md)
for the two project steps in section 1. None was re-checked in a dashboard for this list.
Cloudflare moves things around. If a name differs, search the dashboard for the setting's
name.

---

## 1. Set up the site

**While you create the project** (Workers & Pages → Create application):

- [ ] **Create a Pages project, not a Worker.**
  Workers & Pages → Create application → **Pages** → Connect to Git.
  As of October 2026 the create screen shows **Workers** in the big box and **Pages** only
  as a small line of text beneath it. That small line is the one you need. If you pick the
  big box you get a Worker, and the steps in this kit won't fit. The address tells you
  which you have: a Pages site answers on `<project>.pages.dev`, a Worker on
  `<name>.workers.dev`. If the screen looks different, look for the word Pages. (The other
  ways to deploy are in
  [`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md).)
- [ ] **Build settings:** framework preset **Astro**, build command `npm run build`, output
  directory `dist`. A two-stage site: set **Production branch** to `production` on this
  same form, or it publishes the preview first. To change it later: your project →
  Settings → Builds & deployments → Configure Production deployments, then **Save**.

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
  connection on HTTPS, and it sends nothing anywhere. Once it is on, don't switch the
  domain's records to "DNS only", pause Cloudflare, move the nameservers away or turn SSL
  off: if your site then has no working HTTPS, browsers refuse it until the max age runs out.

## 3. Keep the privacy page true: no cookies, scripts or tracking you didn't choose

Your privacy page says what the site sets and runs: no cookies, and at most the one
measurement tool you chose when the site was built. These settings stop Cloudflare adding
cookies, scripts or tracking you didn't choose.

- [ ] **Network Error Logging (NEL): Off.** A switch, a check, and a rule if the header is
  still there.
  *What it is:* the browser keeps a note, and if it can't reach your site it sends a short
  error report to Cloudflare. Chrome, Edge and other Chromium browsers do this; Firefox
  and Safari don't. When we looked on 12 October 2026, Cloudflare's header set the note to
  seven days and asked for failures only. Your own `nel:` line (section 5) shows yours.
  *Why off:* your page doesn't need it, the privacy page this kit writes doesn't mention
  it, and it makes the visitor's browser send reports to Cloudflare. In Germany, § 25
  TDDDG asks for consent for storing information on a visitor's device or reading it back,
  unless that is strictly necessary for a service the visitor expressly asked for. We found
  no ruling or guidance on NEL specifically (searched October 2026), so whether it reaches
  NEL is untested. This is a risk, not a verdict, and this is not legal advice. Off avoids
  the question.
  *It can be on without you ever choosing it.* Check, don't assume (section 5).
  1. **The switch.** Cloudflare's guide: Account home → Network → Network Error Logging
     Monitoring. If your dashboard shows **Network** only after you open your domain, use
     it there. Switch it **Off**. Any zone administrator can switch it back on. If the
     switch is missing or greyed out, go straight to step 3.
  2. **Check.** Run the first command in section 5. The `nel` and `report-to` lines
     should be gone.
  3. **If they are still there, add a rule that removes them.** When we tried this on a
     Pages site, the switch alone did not stop the header: the setting read "off" through
     Cloudflare's API, and the header was still served half an hour later. Your domain →
     Rules → Overview → Create rule → **Response Header Transform Rule**. Name it "Remove
     NEL headers". Under *When incoming requests match*, choose **All incoming requests**.
     Under *Modify response header*, choose **Remove** and enter the header name `NEL`.
     Select **Set new header**, choose **Remove** again and enter `Report-To`. **Deploy.**
     On the same site this removed both headers within seconds. The rule removes
     `Report-To` from every response, so if your site later sets reporting groups of its
     own, narrow the rule first.

  Visitors who came in the last seven days can keep the old note until it expires. The
  `<project>.pages.dev` address is outside your domain, so the rule doesn't reach it. Once
  `CANONICAL_URL` is set (your assistant does that: "After go-live" in
  [`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md)),
  the kit redirects that address to your live domain. If the header is still there after
  the rule, tell your assistant or ask Cloudflare Support. Cloudflare's support article
  describes a flag, `nel___enable`, that stops NEL being enabled on a zone.
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
    switch it on, so it should offer **Enable**, not show data. A change reaches your site
    with the next deployment.
  - Web Analytics → Manage site → Disable. If your domain isn't listed there, there is
    nothing to disable.

  Cloudflare describes an "automatic setup" for sites that run through it, which adds a
  measurement script to your pages.
- [ ] **Email Address Obfuscation: Off.**
  Your domain → Security → Settings → filter by **Client-side abuse** → Email Address
  Obfuscation.
  *Why:* Cloudflare turns it on when you sign up. It rewrites any plain email address in
  your pages and adds a script (`email-decode.min.js`). The kit already hides addresses.

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
  Cloudflare adds rules to `robots.txt` only when at least one of the three is set to a
  block. Section 5 checks the file.

## 5. Check your work

Run these once the production deployment shows **Active** (your project → Deployments).
The first request a new domain sees is the one Cloudflare's edge keeps, so don't run them
earlier. Replace `yourdomain.com` with your domain. Your assistant can run them; on
Windows use Git Bash or WSL.

```bash
curl -sI "https://yourdomain.com/?cb=1" | grep -iE '^(nel|report-to|strict-transport-security|set-cookie):'
```

You want one line, `strict-transport-security: max-age=15552000` (six months), with
`; includeSubDomains` after it only if you turned that option on in section 2. A `nel` or
`report-to` line means NEL is still on. A `set-cookie` line means something is setting a
cookie: find out what. This check can't see cookies a browser receives only after it runs
a script, such as `cf_clearance`; the source search below covers that.

```bash
curl -s "https://yourdomain.com/robots.txt?cb=1"
```

You want only your own file: no AI-crawler `Disallow` lines you didn't write.

```bash
curl -sI http://yourdomain.com/ | grep -iE '^(HTTP|location):'
```

You want a redirect (301 or 308) and a `location:` line that starts
`https://yourdomain.com`. No output at all means curl could not reach the site: try again
before you trust anything else here.

- **No scripts you didn't add:** open your home page, view the source, and search for
  `cdn-cgi` and `cloudflareinsights`. Neither should be there. `cdn-cgi/challenge-platform`
  is Bot Fight Mode, `cdn-cgi/scripts` is email obfuscation, `cloudflareinsights` is Web
  Analytics.
- **TLS:** run your domain through ssllabs.com/ssltest. TLS 1.0 and 1.1 should say "No".
- **No outside check exists** for Crawler Hints (Caching → Configuration) or Fail open
  (your project → Settings → Runtime). Look at both in the dashboard.

Not covered here: DNS and email records (see "Going live" in
[`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md))
and protecting your Cloudflare account (your site's `SETUP.md`).

## 6. Let your assistant do it: one short-lived token

Most of sections 2 to 4 are settings an assistant can change for you through Cloudflare's
API and read back to show they took. If you would rather not click through the dashboard,
make one token, hand it to your assistant for an afternoon, and delete it afterwards.

**Make the token.** My Profile → API Tokens → Create Token → Create Custom Token. Add these
permission rows, each set to **Edit** (a read-only token can look but not change anything):

| Permission row | What it lets the assistant set |
|---|---|
| Zone → Zone Settings → Edit | Always Use HTTPS, Minimum TLS Version, HSTS, Email Address Obfuscation |
| Zone → Transform Rules → Edit | the rule that removes the NEL headers |
| Zone → Bot Management → Edit | Bot Fight Mode and the AI crawler policies |
| Zone → Zone → Read | finding your domain by name (**Read** is right for this one) |
| Account → Cloudflare Pages → Edit | only if it also creates the project and deploys (option A in [`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md)) |

Then set **Zone Resources** to your one domain, and **TTL** to an end date of tomorrow with
no start date: a start date in the future makes every call fail with "Authentication
error". Create the token and copy it. Cloudflare shows it once.

**Hand it over safely.** The rules in `CLOUDFLARE_FIRST_DEPLOY.md` ("Assistant guardrails")
hold here too. Give the assistant the token as an environment variable for the session.
Never commit it, and never put it in a file the repository tracks or in the README.
Ask the assistant to look before it writes, to tell you each change before it makes it,
and to read each setting back afterwards. Some changes replace a whole list, as the
Transform Rules do, so it must stop if there is something it would overwrite.

**What stays by hand:** Crawler Hints (the kit's notes say Cloudflare has no API for it),
the off switch for Cloudflare Web Analytics, and the Pages choice on the create screen if
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
the API reference for [zone settings](https://developers.cloudflare.com/api/resources/zones/subresources/settings/methods/edit/)
and [Bot Management](https://developers.cloudflare.com/api/resources/bot_management/methods/update/),
and MDN's [Network Error Logging](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Network_Error_Logging).
