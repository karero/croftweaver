# Plan: count enquiries by default, with cookieless analytics

Requirements record for the roadmap item "A standard way to count enquiries: cookieless
analytics with one conversion event set up by default, so arrivals can be tied to
enquiries." Where this plan and the shipped files disagree, the files win. The business in
the scenarios is made up.

## Status — 2026-10-14 · merged to main (#287 as `55efb9c`, #294 as `3519d2d`)

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | Requirements and scenarios (this file) | ✅ approved by the owner 2026-10-14, with D1 "Email Tap", D2 Q5 stays optional, D3 Plausible only | in chat |
| 2 | Starter: the email link reports the event; test | ✅ built, local suite green (99 passed, 1 skipped by design); each new test failed on a deliberate break | karero/croftweaver#287, merged as `55efb9c` |
| 3 | Contact form skill: the button reports the event; test | ✅ built, green EN and DE copies; each new test failed on a deliberate break | karero/croftweaver#287, merged as `55efb9c` |
| 4 | Privacy pages EN and DE; interview Q5; README setup step; launch checklist | ✅ written; also `config.ts` names the two call sites (D3) | karero/croftweaver#287, merged as `55efb9c` |
| 5 | Release-note row in `docs/BUGLOG.md` | ✅ written (row of 2026-10-14), read by the wording pass | karero/croftweaver#287, merged as `55efb9c` |
| 6 | Review gate (High: privacy text and data a live site sends) | ✅ passed at 7d7e595: 3 rounds, final full read, wording pass; 27 findings | trail `REVIEW-diff-2026-10-14-feat-enquiry-count-e1ab9d7.md`; review comment on #287 |
| 7 | Follow-ups from the gate: H4 (the `%` test's loose match) and W2 (other browsers, self-hosted goals) | ✅ H4 fixed; W2 narrowed: Playwright's Firefox and WebKit measured, with requests answered locally; real Safari, content blockers, a live Plausible server and self-hosted goal timing stay open as a `docs/BUGLOG.md` row (2026-10-14) | karero/croftweaver#294, merged as `3519d2d`; trail `REVIEW-diff-2026-10-14-fix-enquiry-count-follow-ups-f328f8d.md` |
| 8 | The open-gaps row measured: self-hosted backfill, a real server, the dashboard's periods | ✅ two of four settled; Safari (not yet tapped) and content blockers stay open in the row | this change |

Legend: ✅ done · ▶ in progress · ⏸ not started or blocked

## What is there today (origin/main e038603)

- The starter already loads Plausible on the live build only (`src/config.ts` `ANALYTICS`,
  `Base.astro`), and `tests/check_analytics_gate.sh` proves it is off everywhere else.
- Nothing reports a conversion. The owner sees visitors and sources, but not which of them
  got in touch.
- Contact is by email only: `<EmailLink>` in the starter, and the optional
  `website-contact-form` skill, whose button opens the visitor's own mail program. A form
  that sends is out on purpose (owner, 2026-10-14).
- The site never learns whether the visitor pressed Send. So the honest thing to count is
  the step the site can see: the visitor asked to write to the owner (whether a mail
  program opened, the site never learns either).

## Plausible facts this rests on (docs.plausible.io "custom event goals", read 2026-10-14)

- An event is received but not shown until a goal of exactly the same name exists.
- "Past events are not backfilled": a goal created after launch counts from that moment.
  So the goal must exist before launch.
- Self-hosted (Community Edition v3.2.1), measured 2026-10-14 on a throwaway local
  instance (Docker, removed afterwards): three "Email Tap" events sent while the site had
  no goal showed at once when the goal was created, and five after two more, through the
  Stats API v2, grouped by goal and filtered by it. The source agrees: ingestion
  (`lib/plausible/ingestion/event.ex`) never drops an event for a missing goal; goals load by site only (`for_site_query` in
  `lib/plausible/goals/goals.ex`); filtering (`goal_condition` in
  `lib/plausible/stats/goals.ex`) and grouping (`event_goal_join` in
  `lib/plausible/stats/sql/expression.ex`) match stored events by name, with no limit
  from the goal's creation. Whether Plausible's cloud service behaves the same was not
  tested; its documentation says earlier events are not counted. The advice holds either
  way: add the goal before launch.
- A new site drops events at first (same throwaway instance): four events sent seconds
  after the site was created were answered 202 and not stored; resent a minute later,
  they were. The source fits: `lib/plausible/site/gate_keeper.ex` answers a site that is
  not yet in its cache with the policy `:not_found`, and ingestion drops the event. How
  long the cache takes on a given instance, and whether the cloud service behaves the
  same, was not measured. Q5 and the starter README say to tap again a few minutes later.
- A real server receiving a tap from Firefox, 2026-10-14: one tap from Playwright's
  Firefox 155 to croftweaver.com's live instance at 13:25 UTC (page view and "Email Tap",
  both answered 202), with the referrer `https://example.org/croftweaver-firefox-test`;
  the owner saw the visit under Today, source example.org.
- Dashboard periods (v3.2.1): the "Last 7, 28, 30 and 91 days" views run from n days ago
  to yesterday, in both date paths: `build_datetime_range({:last_n_days, n}, …)` in
  `lib/plausible/stats/query_builder.ex`, and `put_input_date_range` in
  `lib/plausible/stats/legacy/legacy_query_builder.ex` (`Date.shift(day: -1)`). The
  change is in the v3.0.0 changelog (2025-04-11): "Last `7d` and `30d` periods do not
  include today anymore". The dashboard's own labels are "Today" and "Realtime"
  (`assets/js/dashboard/query-time-periods.ts`). So a test tap shows only under one of
  those two. The owner first looked under 28 days and saw nothing.
- Request sent and payload, measured 2026-10-14 on croftweaver.com's live per-site script
  (v33), event requests intercepted locally, in Playwright's Chromium 153, Firefox 155 and
  WebKit 26.6: a real link click and the form's exact sequence each sent one event with
  the page and the referrer (WebKit sent only the referrer's site,
  `https://www.example.org/`; whether Safari does the same was not checked), and the page
  stayed. Each request was answered locally: no Plausible server received it, and no content
  blocker was in the way. Only Chromium reports the mailto: request to
  Playwright; in the other two the event is seen leaving, the mail program is not.
  WebKit is Safari's engine, not Safari itself.
- The dashboard, filtered by a goal, shows which sources and pages bring conversions. That
  is the "tie arrivals to enquiries" part; it needs no code of ours.

## Scenarios

A joinery's site, "Oak & Pine", on Plausible, with the default contact page.

**S1. A tap on the email address is counted once, with nothing personal.**
Given the live site with Plausible on, when a visitor who came from a search clicks the
email address on `/contact`, then Plausible receives one event named "Email Tap" (D1) from
`/contact`, the address is not part of it, and the mail program opens as before.

**S2. Every tap counts.** Given the same page, when the visitor clicks the address, closes
the mail and clicks again, then two events are sent. (Plausible shows both the visitors who
converted and the total; no de-duplication of ours.)

**S3. Each email link on a page counts.** Given a page with the address in the text and in
the footer, when either is clicked, then one event is sent for that click.

**S4. The contact form's button is counted the same way.** Given the contact form is
installed, when a visitor fills it in and presses the button, then one "Email Tap" event
is sent before the mail program opens. Nothing the visitor typed is in it.

**S5. A form the browser refuses is not counted.** Given the message is empty or only
spaces, when the visitor presses the button, then no event is sent (the browser stops it,
and no mail opens, as today).

**S6. Analytics off: nothing changes for the visitor.** Given a preview build, or a site
whose owner chose no analytics, when a visitor clicks the address or presses the button,
then the mail program opens, no event is sent, nothing is loaded, and the page shows no
error.

**S7. A blocked or broken tracker never stops the mail.** Given the analytics script is
blocked (an ad blocker), throws, or is not a function, when the visitor clicks, then the
mail program still opens and the page shows no error.

**S8. Without JavaScript nothing changes.** The "name [at] domain" hint shows, as today.
No event (there is no script to send one).

**S9. The owner sets up the goal before launch.** Given the owner picks Plausible in
interview Q5, then the setup tells them, in plain words, to add a goal of type "Custom
event" named exactly "Email Tap" before the site goes live, and why (earlier taps are lost).
The launch checklist has the same line.

**S10. The privacy page stays true, EN and DE.** Given analytics is kept, then section 3 of
`privacy.astro` and `_datenschutz.astro` says that clicks on the email address and on the
contact form's button are counted together with the page they were on, and that neither the
address nor anything typed is sent. Given analytics is deleted, then that sentence goes with
the analytics paragraphs and no other text mentions counting.

**S11. Plausible's own form counting does not count the same press twice.** Given the
contact form is installed, then the docs say to leave "Form submissions" unticked in
Plausible's installer (they already advise unticking all three optional measurements).
Whether Plausible's form counting would see this form at all is NOT verified.

**S12. An existing site can take it up.** Given a site made before this release, then the
release note says what changed (`EmailLink.astro`, and `mail-form.js` for sites with the
form), the goal to add in Plausible, and the privacy sentence to add, EN and DE.

## Decisions for the owner

- **D1. The event's name.** Recommended: **"Email Tap"** for both the link and the form
  button. It matches croftweaver.com's own event, says what happened, and does not claim a
  sent enquiry. Alternative: "Enquiry" (reads better on a dashboard, but overclaims, since
  nobody knows whether Send was pressed).
- **D2. Interview Q5 stays optional.** Recommended: yes. Plausible becomes the named answer
  for "which sources bring enquiries?", with the conversion on by default when it is picked;
  Search Console alone stays a valid answer. Making analytics a default for every site would
  add a monthly cost and a privacy position every owner has to take.
- **D3. Plausible only.** Recommended: yes. It is the only script tool the interview offers.
  The two call sites are one line each, so an owner on another tool changes those lines;
  the docs say which. Cloudflare Web Analytics (website-build-kit's choice) has no custom
  events as far as known (not checked today); GA4 (marketingskills) sets cookies and brings
  the banner the starter avoids.

- **D4. A tap counts as interaction.** Plausible's default (`interactive` true): a visit
  with a tap is not a bounce. Decided by the owner on 2026-10-14: keep it.

## How the tests enter (Rule 9)

Each test builds the real site, loads the real page and clicks the real link or button, so
the listener production runs is the one tested. The one stand-in is `window.plausible`: the
test installs a recorder under that name before the page's scripts run, because the
Playwright build has analytics off. That the live build defines `window.plausible` is
already proved by `check_analytics_gate.sh` (the init stub runs on every page).

The strongest counter-argument: the recorder is not Plausible's stub, so a stub change that
broke queuing would pass. The gate already runs the stub, and Plausible owns the script, so
this plan does not test past that boundary.

## Shape (after the OK, not before)

- `templates/astro/src/components/EmailLink.astro`: a click listener calls
  `window.plausible?.('Email Tap')` inside try/catch, as croftweaver.com does.
- `website-contact-form/templates/mail-form.js`: the same call after the form passes its
  checks and before `window.location.href = href`.
- Tests: `templates/astro/tests/email.spec.ts` (S1 to S3, S6, S7) and
  `website-contact-form/templates/mail-form.spec.ts` (S4 to S7).
- Docs: `privacy.astro`, `_datenschutz.astro` (S10), `new-website/SKILL.md` Q5 and launch
  list (S9, D2), the starter README setup step (S9), the contact-form SKILL.md (S11).
- Release note: one `docs/BUGLOG.md` "Next release notes" row (S12).
