# Cloudflare checklist: the settings your site relies on

Your Croftweaver site runs on Cloudflare Pages. Most of it works out of the box. A handful
of settings decide whether your privacy page stays true, whether search engines and AI
assistants can reach your pages, and whether visitors connect safely. Go through this list
once, after the first deploy, and again whenever Cloudflare redesigns its dashboard.

**How to read the paths.** `→` means "click". The dashboard is dash.cloudflare.com. Some
settings belong to your **domain** (click your domain's name in the list first), some to
your **Pages project** (Workers & Pages → your project), and some to your **account**. Where
a path says "Security → Settings → filter by …", you land on one long page of settings with
a filter box: pick the filter, then find the setting by name.

The paths below come from Cloudflare's own documentation, read on 2026-10-12. Cloudflare
moves things around. If a name differs, search the dashboard for the setting's name.

---

## 1. Set up the site

- [ ] **Create a Pages project, not a Worker.**
  Workers & Pages → Create application → **Pages** → Connect to Git.
  On the create screen Cloudflare shows **Workers** in the big box and **Pages** only as a
  small line of text beneath it. That small line is the one you need. If you pick the big
  box you get a Worker, and the steps in this kit won't fit. (The other ways to deploy are
  in [`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md).)
- [ ] **Build settings:** framework preset **Astro**, build command `npm run build`, output
  directory `dist`. A two-stage site: set **Production branch** to `production` on this
  same form.
- [ ] **Attach your domain to the project.**
  Workers & Pages → your project → Custom domains → Set up a domain.
  A DNS record on its own is not enough: without this step visitors get an error 522.
- [ ] **Set Fail open.**
  Workers & Pages → your project → Settings → Runtime → Fail open / closed → **Fail open**.
  Then the site stays online if the free plan's daily Functions allowance runs out.
  Cloudflare has hidden this setting at times. If you don't see it, look rather than
  assume: the section on Fail open in
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
  This applies to your own domain. Cloudflare doesn't let you change it for the
  `<project>.pages.dev` address.
- [ ] **HSTS: On.**
  Your domain → SSL/TLS → Edge Certificates → HTTP Strict Transport Security (HSTS) →
  Enable HSTS. Then:
  - **Max Age Header:** 6 months.
  - **Apply HSTS policy to subdomains:** On only if every subdomain you use works over
    HTTPS. A mail or other tool on a subdomain may not. If unsure, Off.
  - **Preload:** Off. It needs a max age of 12 months and is slow to undo.
  - **No-Sniff Header:** Off. The starter already sends `X-Content-Type-Options: nosniff`.

  HSTS tells the browser to use HTTPS and reports nothing to anyone. Once it is on, don't
  switch the domain's records to "DNS only", pause Cloudflare, move the nameservers away or
  turn SSL off: browsers then refuse your site until the max age runs out.

## 3. Keep the privacy page true: no cookies, no scripts, no analytics

Your privacy page says the site sets no cookies and runs no analytics. These settings keep
that true.

- [ ] **Network Error Logging (NEL): Off.** Two steps, because the first is not enough on
  a Pages site.
  *What it is:* the browser keeps a note for seven days (Chrome, Edge and other Chromium
  browsers). If it can't reach your site, it sends a short error report to Cloudflare.
  *Why off:* your page doesn't need it, the privacy page this kit writes doesn't mention
  it, and it leaves a note on the visitor's device. In Germany, § 25 TDDDG asks for
  consent for that unless it is strictly necessary. We found no ruling or guidance on NEL
  specifically (searched October 2026), so this is a risk, not a verdict, and this is not
  legal advice. Off avoids the question.
  *It can be on without you ever choosing it.* Check, don't assume (section 5).
  1. **The switch.** Cloudflare's guide: Account home → Network → Network Error Logging
     Monitoring. If your dashboard shows **Network** only after you open your domain, use
     it there. When we tried this on a Pages site, it alone did not stop the header: the
     setting read "off" through Cloudflare's API, and the header was still served half an
     hour later.
  2. **A rule that removes the header.** Your domain → Rules → Overview → Create rule →
     **Response Header Transform Rule**. Name it "Remove NEL headers". Under *When incoming
     requests match*, choose **All incoming requests**. Under *Modify response header*,
     choose **Remove** and enter the header name `NEL`. Select **Set new header**, choose
     **Remove** again and enter `Report-To`. **Deploy.** On the same site this removed both
     headers within seconds.

  Visitors who came in the last seven days can keep the old note until it expires. The
  `<project>.pages.dev` address is outside your domain, so the rule doesn't reach it. The
  kit redirects that address to your live domain once `CANONICAL_URL` is set. If the header
  is still there after the rule, ask Cloudflare Support to disable the `nel___enable` flag
  for your zone.
- [ ] **Bot Fight Mode: Off.**
  Your domain → Security → Settings → filter by **Bot traffic** → Bot fight mode.
  *Why:* Cloudflare says JavaScript detections come with it and can't be switched off.
  They add a script (`/cdn-cgi/challenge-platform/…`) to your pages and set the cookie
  `cf_clearance`; the bot score uses `__cf_bm`. A static site has little to protect from
  bots, so you lose little.
- [ ] **Web Analytics: Off.** Two places, check both:
  - Workers & Pages → your project → Metrics → Web Analytics. This is where you would
    switch it on, so it should offer **Enable**, not show data. A change reaches your site
    with the next deployment.
  - Web Analytics → Manage site → Disable.
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
  right away. Google learns about changes another way, which `search-console-setup`
  covers. You don't need a key file. With a Bing Webmaster Tools account
  ([`search-console-setup`](../skills/search-console-setup/SKILL.md) walks you through
  it) you can watch the notifications arrive.
- [ ] **AI crawlers: allow.**
  Your domain → Security → Settings → filter by **Bot traffic** → **Configure AI bot
  policies** → set **Search**, **Agent** and **Training** each to **Allow (do not block)**.
  Leave them on Allow so assistants can read your pages. Cloudflare's defaults for new
  domains, from 15 September 2026, block Training and Agent crawlers on pages that show
  ads. Look at what yours shows. If you still see the older **Block AI bots** setting,
  leave it Off. Cloudflare is retiring it.
  Cloudflare's docs add rules to `robots.txt` only when at least one of the three is set
  to a block. Section 5 checks the file.

## 5. Check your work

Replace `yourdomain.com` with your domain.

```bash
curl -sI https://yourdomain.com/ | grep -iE '^(nel|report-to|strict-transport-security|set-cookie):'
```

You want one line: `strict-transport-security: max-age=15552000; includeSubDomains`.
`nel`, `report-to` or `set-cookie` showing up means a setting in section 3 is still on.

```bash
curl -s https://yourdomain.com/robots.txt
```

You want only your own file: no AI-crawler `Disallow` lines you didn't write.

```bash
curl -sI http://yourdomain.com/ | head -1
```

You want `301`, sending visitors on to `https://`.

- **No scripts you didn't add:** open your home page, view the source, and search for
  `cdn-cgi` and `cloudflareinsights`. Neither should be there.
- **TLS:** run your domain through ssllabs.com/ssltest. TLS 1.0 and 1.1 should say "No".

Not covered here: DNS and email records (see "Going live" in
[`CLOUDFLARE_FIRST_DEPLOY.md`](../skills/new-website/references/CLOUDFLARE_FIRST_DEPLOY.md))
and protecting your Cloudflare account (your site's `SETUP.md`).

---

Sources, read 2026-10-12: Cloudflare's
[Pages: create a project](https://developers.cloudflare.com/pages/get-started/git-integration/),
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
[Block AI bots](https://developers.cloudflare.com/bots/additional-configurations/block-ai-bots/)
and [managed robots.txt](https://developers.cloudflare.com/bots/additional-configurations/managed-robots-txt/).
