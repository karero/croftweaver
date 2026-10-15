# Plan: Plausible without a browser script ("server mode")

Requirements record for an opt-in way to count visits in Plausible from the site's Cloudflare
Pages Function instead of the browser script, so no analytics code runs on the visitor's
device. The browser script stays the default. Where this plan and the shipped files disagree,
the files win. The business in the scenarios is made up.

## Status

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | Trial on throwaway things (Pages project, Plausible site) | ✅ done 2026-10-15, cleaned up | trial report (owner's private artifact); facts below |
| 2 | Decisions D1–D4 | ✅ decided by the owner 2026-10-15 | in chat; "Decisions" below |
| 3 | Requirements and scenarios (this file) | ▶ written, not yet approved by the owner | this file |
| 4 | Build, test-first: config, layout, middleware, email route, email link | ✅ built; 16 new tests, each failed on a deliberate break; starter suite 85 passed, 1 skipped (positioning, by design) | `721e5442`, `98259173` |
| 5 | Gate script, CSP, privacy pages EN and DE, setup docs, release-note row | ✅ gate green in both modes and fails on both deliberate breaks; CI runs it in server mode too; privacy slots pass tone and a11y (German page routed for the run) | `af102f7e`, `be87502a` and the commits between |
| 6 | End-to-end test on a fresh site from this branch | ⏸ deployed to throwaway project `cw-plausible-e2e` (live build, server mode, plus a trial-only Cloud debug route); Plausible site `plausible-trial.croftweaver.com` and its goal added by the owner; waiting for the custom domain `plausible-trial.croftweaver.com` on the project (owner, 2026-10-15 evening) | — |
| 7 | Review gate (High: privacy text and data a live site sends) | ⏸ `make check` not yet run to the end: `check_clean.sh` scans `node_modules` for over 15 minutes; move `node_modules`, `dist` and `test-results` aside first | — |
| 8 | PR | ⏸ | — |

Legend: ✅ done · ▶ in progress · ⏸ not started or blocked

## Why

The browser script reads a local-storage flag and makes the browser send data. The EDPB says
JavaScript that instructs the browser to send information falls under Article 5(3) ePrivacy
(Guidelines 2/2023 v2.0, para 33). The owner asked (2026-10-15) to try counting from the
server instead, once the kit's consent explanation was written.

## Facts this rests on (trial, 2026-10-15, Plausible Community Edition, source read at v3.2.1)

Observed on a throwaway copy of the starter, a throwaway Pages project and a throwaway site on a
self-hosted instance behind Cloudflare; read through the Stats API.

- `POST /api/event` with `name: pageview`, the page URL, the referrer, the visitor's user agent
  and IP is counted as visits and unique visitors, with page, source, UTM campaign, country,
  device and browser, as the script's events are. A second page joins the same visit. No API
  key: the event's `domain` must match a site on the instance. Plausible always answers 202; a
  dropped event carries `x-plausible-dropped: 1`.
- IP: `PlausibleWeb.RemoteIP` reads `x-plausible-ip`, then `cf-connecting-ip`,
  `b-forwarded-for`, `x-forwarded-for`, `forwarded`. On an instance behind Cloudflare,
  `X-Forwarded-For` alone lost to `CF-Connecting-IP` (the sender's IP was used);
  `X-Plausible-IP` won (a test IP was placed in Japan). The Function receives the visitor's IP
  in `CF-Connecting-IP`.
- Bots: CE drops declared bots and Headless Chrome by user agent (`put_user_agent` in
  `lib/plausible/ingestion/event.ex`), but did not drop `curl` or `python-requests`. A scanner
  found the new host within minutes and was counted 5 times, until the Function required
  `Sec-Fetch-Dest`. CE has no data-centre filter: `drop_datacenter_ip` acts only on an
  `x-plausible-ip-type` header that Plausible's own cloud proxy sets. A full Chrome at a hosting
  network (ASN 12876) was counted; the script counts it too on CE.
- Lost: scroll depth and time on page come back empty; a one-page visit shows 0 s.
- Delay: none measurable with `context.waitUntil` (median first byte 184 ms counting, 207 ms not,
  15 pairs).
- Cost: the starter has no `_routes.json`, so the middleware already runs on every request.
  Counting adds no Function runs and one outgoing request per page view. Free plan: 100,000
  Function requests a day, shared with Workers; past it Cloudflare's default "fail open" serves
  the site without the Function until midnight UTC, and counting stops without an error.
- Email: a link to a Function route that sends `Email Tap` (page from `Referer`) and answers
  `302 Location: mailto:…` worked in a real browser, and Plausible accepted the event. A mail
  program opening was not seen (the test browser has none).
- No Sites API on CE (`/api/v1/sites` answers 404; `on_ee` in `router.ex`): the site and the goal
  are added by hand. A new site drops events for about a minute (see
  `SKILL-PLAN-enquiry-count.md`).
- Plausible Cloud: not tried. Its Events API docs say to send the visitor's IP in
  `X-Forwarded-For` and that a server or CDN IP gets the event dropped.

## Decisions (owner, 2026-10-15)

- **D1** Server mode supports self-hosted Plausible and Plausible Cloud. Cloud is tested in
  step 6 as far as can be done without an account (the Events API's `X-Debug-Request`), and the
  docs say what was and was not tested.
- **D2** The contact form's button is not counted in server mode; only email links are. Counting
  it without a script would mean passing the typed message through our server.
- **D3** The visitor's IP is forwarded, as the script's own request carries it.
- **D4** No filter of hosting networks for now.

## Scenarios

A joinery's site, "Oak & Pine", at `https://oakandpine.example`, on Plausible, with
`ANALYTICS.mode = 'server'` and the two Production variables set, unless a scenario says
otherwise.

**S1. A page view is counted once.** Given a visitor who searched on Google, when they open
`/about`, then the page is answered first and afterwards Plausible receives one `pageview` for
`https://oakandpine.example/about` with the referrer, the visitor's user agent and IP.

**S2. The next page joins the visit.** When the same visitor clicks on to `/contact`, then one
more page view is sent, and Plausible shows one visit with two pages.

**S3. A reload counts, as with the script.** A reload answered `304 Not Modified` for the page
itself counts as a page view.

**S4. Requests that are not a page view are not counted.** No event for: images, styles,
scripts, fonts, `robots.txt`, the sitemap and other non-HTML files; `HEAD` and any method but
`GET`; a prefetch or prerender (`Sec-Purpose`, `Purpose`, `X-Purpose` or `X-Moz` naming
prefetch, preview or prerender); a page loaded in a frame (`Sec-Fetch-Dest` not `document`); and
a request with no `Sec-Fetch-Dest` at all (curl, scripts, scanners, most crawlers).

**S5. A 404 page view counts, other errors do not.** A missing page answered with the site's
404 page counts, as the script on the 404 page does. A 5xx answer does not.

**S6. Previews and unconfigured sites never count.** No event on `*.pages.dev` hosts (the
production alias and every preview), on `localhost`, or when either Production variable is
missing. Nothing breaks and nothing is logged as an error in those cases.

**S7. A slow or broken Plausible never touches the page.** When Plausible is down, slow, answers
an error or drops the event, the visitor's page is the same as without counting; the Function
logs one line.

**S8. No analytics code on any page.** Server mode builds no Plausible tag and no init stub on any
page, live or preview. `public/_headers` needs no analytics host for it.

**S9. An email tap is counted and the mail program opens.** Given the live build, when a visitor
on `/contact` clicks the email link, then the browser asks the site for `/go/email`, Plausible
receives one `Email Tap` for `https://oakandpine.example/contact`, and the answer is
`302 Location: mailto:<address>?subject=<subject>`. The address is not part of the event.

**S10. The address stays out of the HTML.** In server mode the link's target carries the address
encoded the way `EmailLink` encodes it today; the readable address still appears only after the
page's own decoder runs, and without JavaScript the "[at]" hint shows and the link still works.

**S11. The email route counts browsers only.** A request to `/go/email` without browser headers
(S4's rule), or on a preview host, still gets the redirect but sends no event.

**S12. The email route sends nowhere but mail.** `/go/email` answers only with a `mailto:` to one
well-formed address and an optional subject of bounded length; anything else gets `400` and no
event. It never redirects to a web address.

**S13. Off the live build, email links stay as today.** On preview builds and in local
development, where no Function runs (`astro preview`, `astro dev`), the link is the plain
`mailto:` link of today and no `/go/email` request is made.

**S14. The contact form is not counted (D2).** With the contact form installed, pressing its
button opens the mail program as before and sends nothing. The docs say so.

**S15. Script mode is unchanged.** A site with the default `ANALYTICS.mode = 'script'` builds the
same pages as before this change, and the Function counts nothing even if the variables were set
by mistake. (How the Function knows the mode is in "Design" below.)

**S16. The privacy page stays true, EN and DE.** Given server mode, section 3 of `privacy.astro`
and `_datenschutz.astro` says that no analytics code runs in the browser, what the server passes
to Plausible (page address, referrer, user agent, IP), that Plausible does not store the IP, and
that a click on the email address passes through the server, which counts it. The header notes
cite EDPB 2/2023 paras 54–56 (IP-only tracking) and state no consent conclusion.

**S17. The owner can set it up.** Interview Q5 offers the choice; the setup says, in plain words:
set `ANALYTICS.mode`, set the two Production variables in Cloudflare, add the site and an
`Email Tap` goal in Plausible by hand before launch, and wait a few minutes before the first
test.

**S18. Plausible Cloud (D1).** The same request works against `https://plausible.io`: the
visitor's IP, not Cloudflare's, is the one Plausible uses. Checked in step 6 with
`X-Debug-Request`; whether a real Cloud site shows the visits is not checked without a Cloud
account.

## Design

- **Mode.** `ANALYTICS.mode: 'script' | 'server'` in `src/config.ts`, default `'script'`.
  `Base.astro` writes the tag only for `'script'`; `EmailLink.astro` links to `/go/email` only on
  a live build in server mode (S13).
- **How the Function knows.** It cannot import `src/config.ts` (that file reads `process.env`,
  which a Pages Function does not have without the Node compatibility flag). So it counts only
  when both Production variables are set (`PLAUSIBLE_EVENTS_URL`, `PLAUSIBLE_DOMAIN`) and the host
  is not `*.pages.dev` or `localhost`. Production variables reach only production deployments,
  and only production serves the custom domain. S15's guard is the docs plus a build-time marker
  (see open point P1).
- **Counting** sits in `functions/_middleware.ts`, which today returns early for the live domain;
  that path changes so counting runs there.
- **Email route** `functions/go/email.ts`: decodes the address the link carries, validates it
  (S12), counts when S11 allows, answers 302.

## Open points (to settle in step 4)

- **P1** S15: how the Function tells script mode from server mode if an owner sets the variables
  in script mode. Options: docs only; or the build writes a marker the Function can read.
- **P2** S12 is a judgment: the route redirects to any well-formed address it is handed, not to
  a fixed list. Its only target is `mailto:`, so it cannot send anyone to a web page; a list
  would need a second place to keep addresses in step with the pages. Reviewers may push back.
