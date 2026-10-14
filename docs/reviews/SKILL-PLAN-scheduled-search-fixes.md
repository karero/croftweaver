# Requirements: the weekly fix proposal, from the search data to one tested edit

Requirements record for a feature that does not exist yet. It says what the feature must do
and how we will know, not how to build it: no mechanism is chosen here. Where this file and
the shipped files disagree, the files win. The businesses, domains and figures in the
scenarios are made up.

## Status — 2026-10-14 · written against origin/main e038603

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | Requirements and scenarios (this file) | ▶ rewritten for Option 0 after the decisions; not reviewed | draft PR #286 (branch `docs/scheduled-search-fixes-requirements`) |
| 2 | Owner answers the open decisions | ✅ D0 to D11 decided 2026-10-14 | owner's answers in chat, 2026-10-14 |
| 3 | Review gate on this file (Normal: a plan, so never Light) | ⏸ next | — |
| 4 | Design plan (the mechanism), then build, then its own review gate | ⏸ waits for 3 | — |
| 5 | Release note line in 0.32 (D10) | ⏸ waits for 4 | — |

Legend: ✅ done · ▶ in progress · ⏸ not started or blocked · ⚠ deviated

## Why

The competitive review of 2026-10-14 (croftweaver-site, branch
`docs/competitive-review-2026-10-14`, `docs/competitors.md`, not merged yet) lists "a
scheduled agent that opens pull requests" as a gap. The owner chose the message for it on
the same day: **sell the fix, not the watching.** Watching whether search engines and AI
name a business is becoming free; making the change, and re-testing the site after it, is
not.

**What Croftweaver does today** (read on origin/main e038603):

- `search-console-insights` reads Search Console and Bing, keeps a history, and builds a
  report page for the owner. `schedule_tracking.sh` runs `track.sh` weekly, per site, only
  after the owner says yes. That scheduler is launchd on macOS; on Linux the skill says to
  run `track.sh` from a systemd user timer or cron by hand; Windows is not mentioned.
- The weekly job **only records data** (SKILL.md, "Weekly auto-tracking": "The job only
  *records* data"). The report lists striking-distance queries and pages seen but not
  clicked, but turning one into a change is left to the owner.
- Every change to a Croftweaver site goes through the site's own gate: 13 Playwright spec
  files in the starter (`skills/new-website/templates/astro/tests/`), run by the pre-push
  hook (`scripts/verify.mjs`) and again by CI on every pull request. The site's
  `AGENTS.md` forbids a direct push to `main` and lets the assistant merge only when the
  owner asks.

**What the competitor does.** marketingskills' recipe
`skills/marketing-loops/references/seo-operator.md` (read 2026-10-14; last commit to the
file 2588c27100, 2026-10-07) runs SEO from the site's repository on a schedule: a run
every day or deploy, more work weekly and monthly. It keeps its memory in `.agents/seo/`,
reads Search Console, analytics, rank and AI-visibility tools, and ships changes as pull
requests by default, or "merge when checks pass" if the owner says so. Before shipping it
runs "the repo's lint, type check, and build" and loads each changed page.

**Croftweaver's difference** is the gate, not the watching: the edit passes the same 13
test files the owner's own edits must pass, before the owner is asked to merge it. The
competitor checks whatever the repository happens to have.

## v1 is Option 0 (D0, decided 2026-10-14)

No assistant runs unattended. The weekly report ends with **at most one proposal**: the
page, what to change there, why, and the sentence to say to the assistant ("fix the title
of /reparatur for 'fahrrad reparatur leipzig'"). The owner asks in a normal session; the
assistant checks the proposal against the positioning, edits on a branch, the gate runs,
and a pull request opens.

Why first: on a small site most weeks have nothing worth changing (scenario 2), and an
unattended loop would bring a scheduler on three platforms, keys that may leave the
owner's computer, and a running cost for a pull request that may come once a month. What
Option 0 gives up: the change does not wait ready-made for the owner. The loop is
described under "Later" and follows only if owners act on the proposals.

## Who it is for

- **For:** the owner of a site built from the Croftweaver starter, with its tests and CI
  in place, verified in Search Console, connected to `search-console-insights` and its
  weekly report, with a filled `POSITIONING.md`. The owner may not be technical: they
  read a pull request in plain words, look at the preview, and say yes or no.
- **Not for:** a site on another stack, or one whose tests were removed (there is no
  gate; the report may still show the proposal, but the assistant says the change would
  go out untested); a site without Search Console data yet (R5).

## R1. Which proposal the report shows

Code picks the proposal from the numbers; the report calls no assistant. All figures are
non-brand rows of the tracker's 28-day window, read the way SKILL.md's "Reading the
numbers" demands (named denominator and window; query-to-page link proved with `--query`,
never inferred).

| | Kind | Condition | Proposal |
|---|---|---|---|
| T1 | **Striking distance** | A query at average position 8 to 20 with at least **50** impressions, whose landing page is proved by the `--query` drill-down, and whose words are not yet in that page's title, H1 or first paragraph | Thread the query's wording into those places (SKILL.md, low-volume playbook, item 2) |
| T2 | **Seen, rarely clicked** | A page at position 10 or better, CTR under 2%, at least **100** impressions | Rewrite the title or the meta description, **only after** the live-result check shows Google displays the page's own title or description |

- **One proposal per report**, the strongest by impressions; ties go to T1.
- **Never proposed:** brand queries; a row under 10 impressions (the tracker's `~`); a
  move the tracker marks `≠` or `‡`; a ranking drop (too many possible causes; it stays a
  line in the report); Bing alone (a six-month total); the AI check's results (`ai-seo` is
  how to act on them, on the owner's request); a page with an open pull request; a page
  and query the owner turned down in the last **12 weeks**; a page changed by an earlier
  proposal whose measuring window (R3) has not closed.
- An unanswered proposal stays while its condition holds, and the report says since when
  it has been shown. A stronger one may take its place.
- 50 and 100 are judgment (the toolkit's own floors are 10 for noise and about 20 for "too
  thin to diagnose"). Changing them later is a settings change, not a redesign.

## R2. What the edit may change, and what it may not

**May change, on an existing page or content-collection entry only:** the `title`, the
meta `description`, the H1, the first paragraph (D4). No internal links in v1.

**May not:**

- create, delete or rename a page; touch redirects, `noindex`, `robots.txt`, the
  sitemap, `public/_headers`, `src/config.ts`, `astro.config.mjs`, `package.json`,
  `.github/`, `scripts/`, `functions/` or `AGENTS.md`;
- touch any test, `PAGES`, `UNFILLED_UNTIL_LAUNCH`, or a row of `positioning.spec.ts`.
  Never add, remove or loosen a test to get green;
- add a fact. Every claim in the new wording must already be on that page or in
  `POSITIONING.md` (`AGENTS.md` §4, "Invent nothing"): no prices, numbers, names, years
  or customer quotes that are not already there. If a good edit needs a fact, the
  assistant asks the owner for it instead of writing a `[MISSING: …]` placeholder;
- change the form of address, the language, or the voice set in `CONTENT_GUIDE.md` and
  `BRAND.md`.

**What wins when they disagree:**

1. **`POSITIONING.md` wins over the search data.** The report cannot judge this; the
   assistant does, before editing. A query that contradicts the positioning (a price
   angle the owner ruled out, a service the business does not offer) gets no edit: the
   assistant quotes the line of `POSITIONING.md`, points to `website-positioning` in case
   the owner wants to change course, and the proposal counts as turned down (12 weeks).
2. **The wording rule wins over the query.** `tone.spec.ts`, the title limit (`TITLE_MAX`
   in `AGENTS.md` §6), the description length (140 to 160, test 120 to 160). If the
   query's exact words cannot fit, the assistant uses the nearest wording that does, or
   says it cannot.
3. **The terms `positioning.spec.ts` requires stay.** An edit may not drop one.

**The gate.** The branch is pushed the way `AGENTS.md` §2 says, so the pre-push hook runs
the full suite. Red: fix the wording within the same four places and push again. Never
`--no-verify`, never a change outside the four places to make a test pass.

## R3. How the owner approves, and what they learn afterwards

- **A pull request**, from a branch of its own (`content/search-<date>`, the `content/`
  convention of `AGENTS.md` §1), never a push to `main`. The assistant merges only when
  the owner asks and never runs `npm run ship` unasked (`AGENTS.md` §2).
- **The pull request explains itself** in the owner's language: the full URL, the old and
  the new wording side by side, the reason, the test result, and where the site has git
  integration, the preview address.
- **Figures in the pull request (D5).** On a **public** site repository, the first time,
  the assistant asks whether search figures may appear in pull requests, and remembers
  the answer for that site. On "no", the pull request names the change and the reason
  without figures and points to the private report page. On a private repository it
  quotes them, each with its window and denominator.
- **"Not this one."** The owner can turn a proposal down in plain words, in the session or
  by closing the pull request. That page and query are not proposed again for 12 weeks,
  and the next report says until when.
- **Measuring (D11: in v1).** When the owner acts on a proposal, the toolkit keeps which
  page, query and pull request it was, so the report can follow it. The clock starts when the change is **live**, not when it is
  merged: on a two-stage site nothing is live before `npm run ship`. 28 full days later
  (plus Search Console's lag), the report compares 28 days after with the 28 days before,
  against the site's untouched pages as a control, and says "consistent with", never
  "caused by" (SKILL.md rule 7).

## R4. Cost and keys

| Item | Cost | Source |
|---|---|---|
| Search Console, Bing Webmaster Tools | free; Search Console read-only | SKILL.md |
| Live-result check (T2 only) | Serper: 2,500 searches free, then about $0.30 per 1,000 | SKILL.md, Phase 2 |
| The assistant's edit | the owner's normal assistant use, as for any edit they ask for | — |
| The site's tests | the CI the site already runs on each pull request | starter `ci.yml` |

- No new key. Without a Serper key there are no T2 proposals; the report says what the
  key would add, once.
- Keys stay in `~/.config/gsc-insights/`, never printed, committed, or written into a pull
  request or the report.
- If Google's data fails (`track.sh` exit 2, "the sign-in needs renewing"), the report
  shows no proposal and says how to reconnect. The 7-day sign-in question for apps left in
  "Testing" is tracked in `docs/BUGLOG.md` (#290), not here.

## R5. A site with almost no data

Most small sites. The report must make that a calm, honest week:

- Below the thresholds there is no proposal. The report says so in one sentence with the
  figures ("shown 64 times in 28 days, 41 of them for your name") and names what would
  lead to a proposal first.
- It does not guess past missing data, and it does not suggest new pages to fill the gap.

## R6. Where it runs

Nothing new is scheduled: the proposal comes with the weekly report the owner already has
(launchd on macOS, the owner's own timer on Linux). On any platform, including Windows,
an owner who asks for their report gets the proposal with it. The edit runs in the owner's
normal session, with whichever assistant they use (`AGENTS.md` serves Claude Code and
Codex alike).

## Scenarios

Report day is a Monday; the 28-day window ends three days earlier because of Search
Console's lag.

**1. The report proposes a fix, and the owner asks for it.**
Given radwerk-plagwitz.example, a bike repair shop in Leipzig, whose report of
2026-11-02 (window 2026-10-03 to 2026-10-30) finds the non-brand query "fahrrad reparatur
leipzig" at average position 11.6 with 286 impressions; the `--query` drill-down puts 271
of them on https://radwerk-plagwitz.example/reparatur, whose title "Reparatur und
Service", H1 and first paragraph do not contain the phrase; `POSITIONING.md` names
repairs as the core offer.
When the owner opens the report.
Then it ends with one proposal: the page's full URL, "work 'fahrrad reparatur leipzig'
into the title, heading and first paragraph", the figures with their window, and the
sentence to say to the assistant.
And when the owner says that sentence, the assistant checks `POSITIONING.md`, edits only
those three places on branch `content/search-2026-11-02`, the pre-push hook passes all 13
test files, and a pull request opens showing old and new wording. Nothing is merged.

**2. A thin site gets an honest week.**
Given tonstube-kassel.example, a pottery studio, whose window shows 64 impressions
(property-level), 0 clicks, 41 of them for the studio's name, and nine other queries each
under 10 impressions.
When the owner opens the report.
Then there is no proposal, and the report says "Too little data to propose a change this
week: shown 64 times in 28 days, 41 of them for your name. The first thing that would lead
to a proposal: a search shown 50 times at position 8 to 20."

**3. Seen but not clicked.**
Given https://radwerk-plagwitz.example/preise at position 4.2 with 520 impressions and
3 clicks (0.6%), and no Serper key.
When the report is built.
Then there is no T2 proposal, and the report says once that checking whether the snippet
is the cause needs the free live-result key (2,500 searches).
And given the key is added and the live result shows Google displays text from the page
body instead of the meta description: still no proposal, because a new description would
not be shown; the report says so.

**4. The positioning says no.**
Given the report proposes "fahrrad günstig reparieren leipzig" (position 9.8, 140
impressions) for /reparatur, and `POSITIONING.md` says the shop does not compete on price.
When the owner asks the assistant to make the fix.
Then the assistant makes no edit, quotes the `POSITIONING.md` line, says that competing on
price would be a positioning change (`website-positioning`), and the proposal is not shown
again before 2027-01-25 (12 weeks after 2026-11-02).

**5. The tests refuse the first draft.**
Given the owner asked for the fix of scenario 1, and the drafted title makes the full page
title 63 characters, over the limit of 60.
When the assistant pushes.
Then the pre-push hook refuses it; the assistant shortens the title and pushes again;
green, so the pull request opens and says the first draft was too long. No test file is
touched, and nothing is pushed with `--no-verify`.

**6. The owner turns a proposal down.**
Given the report of 2026-11-02 proposed the change to /reparatur, and the same day the
owner said "not this one, it does not sound like us".
When the reports of 2026-11-09 and later are built.
Then none proposes that page and query before 2027-01-25; the next report says it was
turned down and until when; another proposal may take its place.

**7. A public repository, figures declined.**
Given the site's repository is public and the owner has never been asked about figures.
When the assistant is about to open the first pull request of scenario 1.
Then it asks once whether search figures may appear in pull requests. The owner says no:
the pull request shows the old and new wording and "This search sends people to this page;
see your report for the numbers", with no impressions or positions. Later pull requests
for this site do not ask again.

**8. Measuring after the change is live.**
Given a two-stage site where the pull request of scenario 1 was merged on 2026-11-03 and
shipped live on 2026-11-05 (the live page shows the new title).
When the report of 2026-12-07 compares 2026-11-05 to 2026-12-02 with 2026-10-08 to
2026-11-04.
Then it shows "fahrrad reparatur leipzig": position 11.6 → 7.9, impressions 286 → 402,
clicks 2 → 9; the untouched pages' impressions 2,840 → 3,190 (+12%) in the same windows;
and "consistent with the change; the rest of the site grew 12% in the same weeks". It does
not say the change caused it.

**9. Google's data is missing.**
Given the weekly run of 2026-11-09 where Google's data fails with "the sign-in needs
renewing" (exit 2) and Bing's succeeds.
When the owner opens the report.
Then there is no proposal (Bing alone never leads to one), and the report says the Google
connection needs renewing and how.

## Later: the unattended loop

Only if owners act on the proposals. The same requirements hold, plus: an assistant runs
the edit on a schedule and opens the pull request itself; at most one open pull request
from it per site; a weekly cost cap, and each run prints its cost; and a choice of where
it runs, each with its price:

- **The owner's computer:** keys stay there, but the computer must be on, and Windows has
  no scheduler in the toolkit today.
- **A cloud routine of the owner's assistant:** runs with the laptop shut, but the Google
  sign-in must be stored in the cloud.
- **A scheduled GitHub workflow in the site's repository:** the tests already run there,
  but the Google sign-in and an assistant key become repository secrets, and GitHub's docs
  say scheduled workflows in public repositories pause after 60 days without activity (to
  recheck).

The questions that come with it (which assistants, how runs are paid) are reopened then.

## What this rests on

- **Verified (read 2026-10-14):** the files and lines cited above on origin/main e038603;
  the competitor's recipe; the competitive review's wording on its branch; Google's OAuth
  page; the maintainer's weekly logs.
- **Judgment, not fact:** that most Croftweaver sites are thin enough for scenario 2 to be
  the common week; the thresholds 50 and 100; that four places on a page are enough.
- **Strongest case against v1 as written:** a proposal the owner has to ask for may simply
  be ignored, just as today's report lines are, and then the "fix" message rests on a step
  the owner never takes. Scenario 1's single sentence to say is the answer offered; whether
  it is enough shows only once real owners have it.

## Decisions

| # | Decision | Answer (owner, 2026-10-14) |
|---|---|---|
| D0 | The unattended loop, or Option 0 first | Option 0 first; the loop follows only if owners use it |
| D1 | A new skill, or part of `search-console-insights` | Part of `search-console-insights`; the rules for acting on a proposal go in a reference file, so SKILL.md barely grows |
| D2 | Where it runs | No longer a question under Option 0 (R6); back with the loop |
| D3 | Thresholds | 50 impressions for T1, 100 for T2, one proposal per report, 12 weeks after a "no" |
| D4 | Places an edit may change | Title, meta description, H1, first paragraph; no internal links |
| D5 | Search figures in pull requests on a public repository | Ask once per site; on "no", point to the report page |
| D6 | Which assistants | No longer a question: whichever the owner uses; back with the loop |
| D7 | Paying for the assistant's runs | No longer a question: no unattended runs; back with the loop |
| D8 | When croftweaver.com may name it | Only once it ships |
| D9 | The 7-day Google sign-in | Tracked separately: `docs/BUGLOG.md`, merged in #290 |
| D10 | Release | In 0.32 |
| D11 | Measuring the result (R3, scenario 8) in v1, or later | In v1: the proposal, the tested edit and the 28-day comparison all ship in 0.32 |
