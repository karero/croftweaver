# Requirements: scheduled search fixes, a weekly pull request from the search data

Requirements record for a feature that does not exist yet. It says what the feature must do
and how we will know, not how to build it: no mechanism is chosen here. Where this file and
the shipped files disagree, the files win. The businesses, domains and figures in the
scenarios are made up.

## Status — 2026-10-14 · written against origin/main e038603

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | Requirements and scenarios (this file) | ▶ draft, not reviewed | branch `docs/scheduled-search-fixes-requirements`, not pushed |
| 2 | Owner answers the open decisions below | ▶ D0 decided 2026-10-14 (Option 0 first); D1 to D10 open | owner's answer in chat, 2026-10-14 |
| 3 | Review gate on this file (Normal: a plan, so never Light) | ⏸ waits for 2 | — |
| 4 | Spike: one unattended run on one real site, measuring time and cost | ⏸ waits for 2 | — |
| 5 | Design plan (the mechanism), then build | ⏸ waits for 3 and 4 | — |

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
  *records* data"). A change to the site happens only when the owner asks the assistant.
- Every change to a Croftweaver site goes through the site's own gate: 13 Playwright spec
  files in the starter (`skills/new-website/templates/astro/tests/`), run by the pre-push
  hook (`scripts/verify.mjs`) and again by CI on every pull request. The site's
  `AGENTS.md` forbids a direct push to `main` and lets the assistant merge only when the
  owner asks.

**What the competitor does.** marketingskills' recipe
`skills/marketing-loops/references/seo-operator.md` (read 2026-10-14; last commit to the
file 2588c27100, 2026-10-07) runs SEO from the site's repository on a schedule: a run
every day or deploy, more work weekly and monthly. It keeps its memory in `.agents/seo/`
(a query map, a work queue, a claims ledger, weekly reports), reads Search Console,
analytics, rank and AI-visibility tools, and ships changes as pull requests by default, or
"merge when checks pass" if the owner says so. Before shipping it runs "the repo's lint,
type check, and build" and loads each changed page. It also writes new pages, watches
competitors' sitemaps, and drafts outreach and social posts.

**Croftweaver's difference** is the gate, not the watching: every proposed edit has
passed the same 13 test files the owner's own edits must pass, before the owner sees it.
The competitor checks whatever the repository happens to have.

**What we do not take from it**, for v1: daily runs (the low-volume playbook in
SKILL.md says daily is noise on a small site), auto-merge in any form, new pages written
unattended, competitor sitemap watching, backlinks, outreach and social drafts, and a
second copy of the business facts (the site's `POSITIONING.md`, `CONTENT_GUIDE.md` and
pages are the facts).

## The simpler alternative, first (D0)

Most Croftweaver sites are small, and on a small site most weeks will have nothing worth
changing (scenario 2). An unattended loop brings a scheduler on three platforms, an
assistant running with nobody watching, keys that may have to leave the owner's computer,
and a new running cost, for a pull request that may come once a month.

**Option 0:** no unattended assistant. The weekly job already finds striking-distance
queries and pages seen but not clicked. It could end each report with at most one
concrete proposal and the sentence to say to the assistant ("fix the title of
/reparatur for 'fahrrad reparatur leipzig'"). The owner asks; the assistant edits on a
branch; the gate runs; a pull request opens. That is still "the fix, through the tests",
with no new keys and no new cost. What it loses: the change does not wait ready-made for
the owner, so it is a weaker answer to the competitor's recipe.

The rest of this file describes the full loop. Most requirements (what may change, the
gate, approval, thin data) hold for Option 0 too.

## Who it is for

- **For:** the owner of a site built from the Croftweaver starter, with its tests and CI
  in place, verified in Search Console and connected to `search-console-insights`, with a
  filled `POSITIONING.md`. The owner may not be technical: they read a pull request in
  plain words, look at the preview, and say yes or no.
- **Not for:**
  - a site on another stack, or one whose tests were removed: there is no gate, so
    nothing may be edited unattended. The owner can still ask by hand.
  - a site where nobody reviews pull requests. The competitor's own recipe says the same
    ("No one will review the PRs").
  - a site without Search Console data yet (see "A site with almost no data").

## R1. What triggers an edit

Code decides whether there is a trigger, from the numbers. The assistant is called only
when there is one, and only for the judgment parts: whether the change fits the
positioning, and the wording.

All figures are non-brand rows of the tracker's 28-day window, read the way SKILL.md's
"Reading the numbers" demands (named denominator and window; query-to-page link proved
with `--query`, never inferred).

| | Trigger | Edit it may lead to |
|---|---|---|
| T1 | **Striking distance.** A query at average position 8 to 20, with at least *N₁* impressions (D3), whose landing page is proved by the `--query` drill-down, and whose words are not yet in that page's title, H1 or first paragraph | Thread the query's wording into those places (SKILL.md, low-volume playbook, item 2) |
| T2 | **Seen, rarely clicked.** A page at position 10 or better, CTR under 2%, at least *N₂* impressions (D3), **and** the live-result check shows Google displays the page's own title or description | Rewrite the title or the meta description |

**Never a trigger:** brand queries; a row under 10 impressions (the tracker's `~`); a
move the tracker marks `≠` or `‡`; a ranking drop (it has too many possible causes; it
goes in the report); Bing alone (a six-month total); the AI check's results (they
measure; `ai-seo` is how to act, and only on the owner's request); a page with an open
pull request from anyone; a page the loop changed whose after-window (R3) has not closed;
a page and query the owner turned down within the cool-off (D3).

**Limits per run:** one pull request per site, at most *M* pages in it (D3), and none at
all while an earlier pull request from the loop is still open.

## R2. What an edit may change, and what it may not

**May change (v1), on an existing page or content-collection entry only:**
the `title`, the meta `description`, the H1, the first paragraph (D4).

**May not:**

- create, delete or rename a page; touch redirects, `noindex`, `robots.txt`, the
  sitemap, `public/_headers`, `src/config.ts`, `astro.config.mjs`, `package.json`,
  `.github/`, `scripts/`, `functions/` or `AGENTS.md`;
- touch any test, `PAGES`, `UNFILLED_UNTIL_LAUNCH`, or a row of `positioning.spec.ts`.
  The loop never adds, removes or loosens a test to get green;
- add a fact. Every claim in the new wording must already be on that page or in
  `POSITIONING.md` (`AGENTS.md` §4, "Invent nothing"). No prices, numbers, names, years
  or customer quotes that are not already there. The loop never writes a
  `[MISSING: …]` placeholder; if a good edit needs a fact, the report asks for it instead;
- change the form of address, the language, or the voice set in `CONTENT_GUIDE.md` and
  `BRAND.md`.

**What wins when they disagree:**

1. **`POSITIONING.md` wins over the search data.** A query that would win clicks but
   contradicts the positioning (a price angle the owner ruled out, a service the
   business does not offer) gets no edit. The report names the query and the line of
   `POSITIONING.md` it conflicts with, and points to `website-positioning` in case the
   owner wants to change course.
2. **The wording rule wins over the query.** `tone.spec.ts` (no long dash, the banned
   words, no contractions in English), the title limit (`TITLE_MAX` in `AGENTS.md` §6),
   the description length (140 to 160, test 120 to 160). If the query's exact words
   cannot fit inside these rules, the loop uses the nearest wording that does, or makes no
   edit.
3. **The terms `positioning.spec.ts` requires stay.** An edit may not drop one.

**The gate.** The edit is pushed the way `AGENTS.md` §2 says, so the pre-push hook runs
the full suite. Red: the loop may redraft once, within the same four places. Still red:
no pull request; the report says which test refused what. Never `--no-verify`, never a
change outside the four places to make a test pass.

## R3. How the owner approves

- **Always a pull request**, from a branch of its own (`content/search-<date>`, the
  `content/` convention of `AGENTS.md` §1). Never a push to `main`. The loop never
  merges, never sets auto-merge, never runs `npm run ship`, never closes a pull request.
- **The pull request explains itself** in the owner's language (the language rule in
  `AGENTS.md`), for each page: the full URL, the old and the new wording side by side, the
  query and its figures with their window and denominator, the reason, the test result,
  and the date the effect will be measured. Where the site has git integration, the
  preview address is linked.
- **"No" is a complete answer.** A closed pull request turns that page and query off for
  the cool-off (D3). An owner's edits to the branch win; the loop does not redo them.
- **Measuring.** The clock starts when the change is **live**, not when it is merged: on
  a two-stage site nothing is live before `npm run ship`. The loop confirms the live page
  serves the new wording. After 28 full days (plus Search Console's lag), the report
  compares 28 days after with the 28 days before, against the site's untouched pages as a
  control, and says "consistent with", never "caused by" (SKILL.md rule 7).
- **Waiting proposals.** While a loop pull request is open, the loop opens no new one and
  the report says what is waiting. After three weekly runs with it still open, the report
  asks once whether to pause the loop.

## R4. Cost and keys

| Item | Cost | Source |
|---|---|---|
| Search Console | free, read-only scope | SKILL.md, "Scope notes" |
| Bing Webmaster Tools | free | SKILL.md |
| Live-result check (needed for T2 only) | Serper: 2,500 searches free, then about $0.30 per 1,000 | SKILL.md, Phase 2 |
| The site's tests | the CI the site already runs on each pull request | starter `ci.yml` |
| AI check | not used by this loop; $0.72 a week per site when the owner runs it | `references/geo-check.md`, measured 2026-09-26 |
| **The assistant's run** | **not measured** | step 4 measures it |

Requirements:

- A run with no trigger calls no assistant and costs nothing beyond today's weekly job.
- Each run that calls the assistant prints its cost, as the AI check does. A weekly cap
  is set at install (D7); a run that would pass it stops and says so.
- Keys stay where they are today (`~/.config/gsc-insights/`). They are never printed,
  committed, or written into a pull request or the report.
- **Google sign-in, unattended.** The toolkit reads Search Console through its own script,
  not an MCP server: `gsc_query.py` signs in once in the browser (OAuth, read-only scope)
  and keeps a refresh token in `~/.config/gsc-insights/token.json`, which every later
  run, the weekly job included, uses without a browser. Google's OAuth page says a project with an external
  consent screen in "Testing" status gets a refresh token that expires in 7 days.
  `references/onboarding.md` sets the owner up as a test user and says nothing about
  publishing the app. The maintainer's own weekly jobs logged no Google sign-in failure
  on any run through 2026-10-12, so in practice the token held there; whether it holds
  for a new owner set up by today's onboarding is not checked. If it does not, today's
  weekly job is affected too (D9). Either way: a run whose Google data failed (`track.sh`
  exit 2) makes no edit and tells the owner how to sign in again.
- Any option that runs away from the owner's computer (D2, options B and C) needs the
  Google sign-in, and an assistant key, stored with someone else. That is the owner's
  call, made knowingly, and never a default.

## R5. A site with almost no data

Most small sites. The loop must make that a calm, honest week, not a busy one:

- Below the thresholds, there is no trigger, no assistant call, no pull request.
- The report says so in one sentence with the figures ("shown 64 times in 28 days, 41 of
  them for the business name"), and names what would trigger first.
- It does not guess past missing data, and it does not fill the gap with new pages.
- After eight weeks in a row without a trigger, the report says once that the loop has
  had nothing to do, and offers to pause it. It does not ask again.

## R6. Platform scheduling

What a run needs, wherever it runs: the search data, a checkout of the site repository,
Node and a browser for the tests, an assistant that can run with nobody watching, and the
right to push a branch and open a pull request.

| Option | Covers | Gains | Costs |
|---|---|---|---|
| **A. The owner's computer** (extend today's weekly job) | macOS by launchd, as today. Linux by the owner's own timer, as today. Windows: nothing today | Keys never leave the computer; reuses the per-site, opt-in install | Computer must be on; Windows uncovered in v1; the assistant needs a headless mode (Claude Code and Codex both have one; which to support is D6) |
| **B. A cloud routine** of the owner's assistant | any computer | Runs with the laptop shut | Google sign-in must be stored in the cloud; depends on one vendor's product |
| **C. A scheduled GitHub workflow** in the site's own repository | any computer | Tests already run there; one setup for every owner | Google sign-in and an assistant key become repository secrets, visible to the site's admins; GitHub's docs say scheduled workflows in public repositories pause after 60 days without activity (to recheck in the spike) |

Requirements, whichever option: per site and opt-in, never installed unasked (as today);
removal is one sentence to the assistant; a missed run is skipped, not run twice; the
owner can see when the next run is and what the last one did.

## Scenarios

Run day is a Monday; the 28-day window ends three days earlier because of Search
Console's lag.

**1. A striking-distance query becomes a pull request.**
Given radwerk-plagwitz.example, a bike repair shop in Leipzig, with the loop on, and on
2026-11-02 the window 2026-10-03 to 2026-10-30 shows the non-brand query "fahrrad
reparatur leipzig" at average position 11.6 with 286 impressions and 2 clicks; the
`--query` drill-down puts 271 of those 286 on https://radwerk-plagwitz.example/reparatur,
whose title is "Reparatur und Service" and whose H1 and first paragraph do not contain
the phrase; `POSITIONING.md` names repairs as the core offer.
When the weekly run ends.
Then branch `content/search-2026-11-02` changes only that page's title, H1 and first
paragraph; the pre-push hook passes all 13 test files; a pull request opens in German
showing old and new wording, "271 of the page's 286 impressions, 3 to 30 October,
position 11.6", and "effect measured from 28 days after it is live"; nothing is merged,
and the report page says "1 proposal waiting for you".

**2. A thin site gets an honest week.**
Given tonstube-kassel.example, a pottery studio, whose window shows 64 impressions
(property-level), 0 clicks, 41 of them for the studio's name, and nine other queries
each under 10 impressions.
When the weekly run ends.
Then no assistant is called and no branch is made; the report says "Too little data to
change anything this week: shown 64 times in 28 days, 41 of them for your name. The
first thing that would lead to a proposal: a search shown 50 times at position 8 to 20."

**3. Seen but not clicked, and no live-result key.**
Given https://radwerk-plagwitz.example/preise at position 4.2 with 520 impressions and
3 clicks (0.6%) and no Serper key.
When the weekly run ends.
Then no edit; the report says the page is seen but rarely clicked, and that telling
whether its snippet is the cause needs the free live-result key (2,500 searches).
And given the key is added and the live result shows Google displays text from the page
body instead of the meta description: still no edit, because a new description would
not be shown; the report says so.

**4. The positioning says no.**
Given the query "fahrrad günstig reparieren leipzig" at position 9.8 with 140
impressions, and `POSITIONING.md` says the shop does not compete on price.
When the weekly run ends.
Then no edit; the report names the query, quotes the `POSITIONING.md` line, and says that
competing on price would be a positioning change (`website-positioning`), the owner's to
make.

**5. The tests refuse the first draft.**
Given a trigger for /reparatur and a drafted title that makes the full page title 63
characters, over the limit of 60.
When the loop pushes.
Then the pre-push hook refuses it; the loop redrafts the title once; green, so the pull
request opens and says one draft was shortened. If the second draft is red too: no pull
request, and the report says "A proposal for https://radwerk-plagwitz.example/reparatur
did not pass the site's tests (title too long). Nothing was proposed." No test file is
touched, and nothing is pushed with `--no-verify`.

**6. Last week's proposal is still open.**
Given pull request 31 from the loop, open since 2026-11-02, and a new trigger on
2026-11-16.
When the weekly run ends.
Then no new pull request; the report says "Your proposal of 2 November (pull request 31)
is still waiting. Nothing new until you decide." On the third such run it asks once
whether to pause the loop. It never merges or closes pull request 31.

**7. The owner says no.**
Given the owner closed pull request 31 with "Lieber nicht, klingt nicht nach uns".
When the next runs see the same query and page.
Then they propose nothing for that page and query until the cool-off ends (D3); the next
report says the proposal was turned down and will not come back before that date.

**8. Measuring after a change is live.**
Given a two-stage site where pull request 31 was merged on 2026-11-03 and shipped live on
2026-11-05 (the live page shows the new title).
When the run of 2026-12-07 compares 2026-11-05 to 2026-12-02 with 2026-10-08 to
2026-11-04.
Then the report shows "fahrrad reparatur leipzig": position 11.6 → 7.9, impressions
286 → 402, clicks 2 → 9; the untouched pages' impressions 2,840 → 3,190 (+12%) in the same
windows; and the line "consistent with the change; the rest of the site grew 12% in the
same weeks". It does not say the change caused it.

**9. The Google sign-in has run out.**
Given the run of 2026-11-09 where Google's data fails with "the sign-in needs renewing"
(exit 2) and Bing's succeeds.
When the weekly run ends.
Then no edit is made from Bing alone; the report and the run's log say "Google sign-in
needs renewing: tell your assistant 'connect Search Console again'"; the next run after
the owner signs in works as usual.

## What this rests on

- **Verified (read today):** the files and lines cited above on origin/main e038603; the
  competitor's recipe; the competitive review's wording on its branch; Google's OAuth page
  on the 7-day refresh token; the maintainer's weekly logs (no Google sign-in failure).
- **Judgment, not fact:** that most Croftweaver sites are thin enough for scenario 2 to be
  the common week (no count of real sites behind it); the thresholds; that four places on
  a page are enough for v1; option A as the starting point.
- **Strongest case against building the loop at all:** see D0. If most weeks are
  empty, Option 0 delivers the fix through the tests for a fraction of the work and none
  of the key risk, and the loop can follow once real sites show triggers often enough.

## Open decisions for the owner

| # | Decision | Proposal (judgment) |
|---|---|---|
| D0 | Build the unattended loop, or start with Option 0 (one proposal per report, the owner asks) | **Decided 2026-10-14: Option 0 first.** The loop follows only if owners use it |
| D1 | A new skill, or a step inside `search-console-insights` | A new skill: that SKILL.md is 497 lines and its description already over the 900-character warning (BUGLOG, 2026-10-09 row) |
| D2 | Where it runs: A, B or C, and which platforms in v1 | A on macOS only, Linux by hand as today, Windows said plainly not covered |
| D3 | Thresholds: N₁ (T1) and N₂ (T2) impressions, M pages per pull request, cool-off after a "no" | N₁ 50, N₂ 100, M 3, 12 weeks |
| D4 | Places an edit may change in v1; are internal links between existing pages in or out | Title, description, H1, first paragraph; links out |
| D5 | Search figures in pull requests on a **public** site repository (anyone can read them) | Ask once per site; if no, the pull request points to the report page instead |
| D6 | Which assistants: Claude Code, Codex, or both | Both, since `AGENTS.md` serves both; the spike tries one |
| D7 | How the assistant's run is paid, and the default weekly cap | Decide after step 4 measures a run |
| D8 | What the site calls it, and when it may be named on croftweaver.com | Not before it ships; "sell the fix" copy describes the hand-asked fix until then |
| D9 | The 7-day Google sign-in for "Testing" apps: check it with a fresh owner setup; if it bites, should onboarding have the owner publish the app, or connect by a service account added to the property instead (not tried here) | A BUGLOG row for today's weekly job, separate from this feature |
| D10 | Release | After 0.32 |
