# Design: the weekly fix proposal

How to build what `SKILL-PLAN-scheduled-search-fixes.md` (the requirements, PR #286) asks
for. The requirements win where the two disagree; the status table lives there, not here.
Sites in this public repo stay unnamed; figures from a real site appear only as counts.

## 1. What the outside services do (the three waived RISKs)

The requirements gate left three RISKs for this plan to settle before any build. Read on
2026-10-14 from the providers' own pages; quotes are short on purpose.

**Google Search Analytics API**
(https://developers.google.com/webmaster-tools/v1/searchanalytics/query, its discovery
document at revision 20261013, and the help pages named per line):

| Question | What the documentation says | What the design does |
|---|---|---|
| When is data complete? | `metadata.firstIncompleteDate` is "populated only when the request's dataState is all and data is grouped by date"; dates are "in PT time" | Unchanged from the report: the window ends before that date. When it is absent although the request asked for it, nothing in range is incomplete (inferred: no page says so); the report already falls back to the last day with a row |
| Do filters change totals? | Rare ("anonymized") queries are "always omitted from the tables" but "included in chart totals, unless you filter by query" (https://developers.google.com/search/blog/2022/10/performance-data-deep-dive) | No query filter on any total. Brand queries are removed on our side from query rows, never by an API filter |
| Does a page's split by query add up to the page's total? | Not stated for that case; the mechanism (omitted rare queries, "stores top data rows") means it falls short. "For accurate counts, you must omit the page and query dimensions" | A page's non-brand figures are a floor, and the report says "at least". Probe P1 measures the gap on a real site |
| How is position averaged? | The "topmost position occupied by a link to your property or page", averaged over impressions; by property for query rows, by page once a page is grouped or filtered (https://support.google.com/webmasters/answer/7042828) | T1 takes its position from query rows (by property), T2 from page-and-query rows (by page), each weighted by impressions. The two are never compared with each other |
| Is there a brand filter? | A Search Console report filter since 2026-03-11, AI-assisted, "NOT based on a regular expression method"; absent from the API's filter dimensions | Our own list of spellings (§3.2) |
| Row limits | `rowLimit` up to 25,000, paging with `startRow`; at most "50,000 rows per day per site per search type" | One page-and-query request per window, paged as `run_query` already does. A small site is far below the cap |

**Serper** (https://serper.dev; it has no prose API reference, so the home page's FAQ and
sample answers are the source):

| Question | What Serper says | What the design does |
|---|---|---|
| Cached or live? | "We do not cache anything so the returned response will reflect the latest" | One live search per T2 check, at most once per report |
| Are `title` and `snippet` what Google displayed? | Not stated; the samples look like it | Not trusted until check P2 compares them by eye with Google |
| Country and language | Set "by specifying the country and language" (`gl`, `hl`); `serp_check.py` already maps them | Taken from the site's country setting, as `serp_check.py` does |
| Price | 2,500 free queries; paid packs from $1.00 per 1,000 (50k for $50), "Credits valid for 6 months"; whether free credits expire is not stated | R4's row stays as written |

**Still open after reading, settled by two small checks with the owner's OK:**

- **P1, a read-only probe on one real site** (a script beside the report's earlier probe,
  `docs/reviews/gsc-report-probe/`, printing counts only): how far a page's split by query
  falls short of its total, for the site's top pages; and whether `firstIncompleteDate`
  is ever missing on a `dataState: all` date request.
- **P2, one Serper search compared by eye:** the owner searches one query on Google in a
  private window and compares the title and snippet for their own page with Serper's.
  One search from the free allowance.

The competitor RISK needs no check here: it concerns the requirements' "Why", not the
build.

## 2. Recommendation: build T1 first, T2 after P1 and P2

The documentation weakens T2 (seen but rarely clicked) on both legs: its figures come from
a split Google says undercounts, and its decision rests on Serper text whose meaning
Serper does not state. T1 (striking distance) needs neither: query rows by property, one
drill-down, the page's own HTML. It is also the low-volume playbook's first item.

**Proposal (decision DD0):** v1 for 0.32 ships T1, the edit, and the measuring. T2 follows
when P1 shows the undercount is small enough to trust a 100-impression floor and P2 shows
Serper's text matches Google's. *Against:* "seen but not clicked" is the playbook's
highest-return item on a small site, and dropping it halves what the proposal can say.

## 3. Shape

### 3.1 Where each part lives

| Part | File | Kind |
|---|---|---|
| Choosing the proposal, the cool-off, live detection, measuring | `scripts/fix_proposal.py` (new) | Pure functions plus a small command line; code decides, no model |
| Fetching what it needs | `scripts/search_report.py`, `fetch_google` | One more request per window: `["query", "page"]`; plus the candidate page's live HTML |
| Showing it | `search_report.py`, `render` | One section at the end: "One thing to fix this week" |
| State per site | `~/.config/gsc-insights/sites/<site>-proposals.json` (new) | Shown, declined, acted on, live dates, results |
| Settings per site | `~/.config/gsc-insights/sites/<site>.json` (exists) | Gains `brand` (spellings), `repo` (the site's folder), `pr_figures` (yes / no / unasked) |
| What the assistant does when asked | `references/fix-proposal.md` (new) | Instructions: check positioning, edit the four places, run the gate, open the pull request, record it |
| How the assistant gets there | `SKILL.md` | A pointer to the reference; the description stays as it is (it is at 998 of 1,024 characters) |
| The weekly log | `track.sh` | One line naming the proposal, or why there is none |

Nothing is written into the site's repository except the edit itself. State stays on the
owner's computer, beside the settings and history that are already there.

### 3.2 Choosing (code)

- **Brand spellings:** `sites/<site>.json` `brand`, a list. Until the owner confirms one,
  the report uses the domain's first label with hyphens as spaces and as nothing
  ("radwerk plagwitz", "radwerkplagwitz") and says "counted as your business name: …;
  tell your assistant if that is wrong". Matching uses `_lang_normalize.fold`, so
  umlaut spellings match.
- **T1:** from the window's `["query"]` rows: not brand, average position 8 to 20, at
  least 50 impressions. For each, from the `["query", "page"]` rows: the page with most of
  its impressions. Then the page's live HTML is fetched once (the report's first request
  to the owner's own site; a timeout or a non-200 answer drops the candidate and the report
  says why). The query is "already on the page" when every word of 3 or more letters,
  folded, appears in the title, the H1 and the first paragraph taken together.
- **Excluded:** everything in R1's "never proposed" list, read from the state file (open
  pull request, merged but not live, measuring not finished, declined within 12 weeks).
- **One proposal:** most impressions wins.

### 3.3 Acting (the assistant, guided by `references/fix-proposal.md`)

The owner says the report's sentence, which names the skill so the assistant loads it
without relying on the description: *"search-console-insights: make this week's fix for
radwerk-plagwitz.example"*. The reference tells the assistant to:

1. read the proposal from the state file (`fix_proposal.py show <site>`), never from
   memory;
2. read `POSITIONING.md`; on a conflict, quote the line, make no edit, and record it
   (`fix_proposal.py decline <site> --reason positioning`);
3. follow the site's own `AGENTS.md` for branch, wording rules, gate and pull request;
   change only the four places;
4. on a public repository, ask about figures once if `pr_figures` is unasked, and record
   the answer;
5. record the pull request (`fix_proposal.py acted <site> --pr <url> --title "<new title>"`),
   so the report can follow it.

Every state write is a command, so the model never edits the JSON by hand.

### 3.4 Live, and measuring (code)

- **Live:** each report run fetches the changed page and looks for the recorded new title.
  The first run that finds it marks the change live; the run before it, the last that did
  not. The before-window ends on the Sunday before that last "not yet" run; the
  after-window starts on the Monday after the first "live" run. A slow detection only
  delays the measuring; it never mixes the two sides.
- **Control (DD3):** needs the site's folder (`repo` in the settings, asked once). The
  report runs `git log` there, read-only, for the span of both windows. Any commit that
  touches `src/` or `public/` other than the proposal's own leaves no control, and the
  report says "other changes to the site in these weeks; no comparison". Without a folder:
  "the site's folder is not known; no comparison".
- **Results** go into the state file, so the comparison is computed once and the page
  shows it from then on.

## 4. Tests

- **Pure functions** in `fix_proposal.py`: choosing (each exclusion, the 50 floor, ties,
  folding), the word check, the window arithmetic for live detection, the control rule.
  The dates of the requirements' scenarios 1, 2, 4, 6 and 8 are test cases as written.
- **Through the real entry point** (global rule 9): `search_report.build` with the fake
  Search Console service `test_search_report.py` already uses (`FakeGoogle`) and a local
  HTTP server for the live page, as `_geo_stub.py` serves the AI check's tests. One test per requirements scenario
  that the report can show (1, 2, 6, 8, 9).
- **The command line** through `subprocess`, the way the owner's assistant calls it.
- **The assistant's part** (scenarios 1, 4, 5, 7): evals in `evals/evals.json`, run with
  and without the reference, as `website-story` had.

## 5. Steps

| # | Step | Waits for |
|---|---|---|
| 1 | P1 probe and P2 eye-check, with the owner | the owner's OK |
| 2 | `fix_proposal.py` and its pure tests | DD0 to DD5 |
| 3 | The report: fetch, render, state, entry-point tests | 2 |
| 4 | `references/fix-proposal.md`, the SKILL.md pointer, evals | 3 |
| 5 | `track.sh` line; `make check` and CI | 3 |
| 6 | Review gate, Normal (code, no untrusted input beyond the owner's own pages) | 5 |
| 7 | Release note line for 0.32 | 6 |

## 6. Decisions for the owner

| # | Decision | Proposal (judgment) |
|---|---|---|
| DD0 | T1 only in v1, T2 after P1 and P2 | Yes (§2) |
| DD1 | State on the owner's computer, beside the settings | Yes: nothing about search figures enters the site's repository |
| DD2 | Live detection by finding the new title on the live page | Yes: needs no access to the hosting, works on both publish models |
| DD3 | Control: any other change under `src/` or `public/` in the span means no comparison | Yes for v1: never wrong, though often "no comparison" on a busy site. Matching changes to single pages is later work |
| DD4 | The owner's sentence names the skill | Yes: the description has no room for new trigger phrases |
| DD5 | Brand spellings start from the domain and are shown until confirmed | Yes: a proposal on day one, with the guess visible |
| DD6 | Run P1 on one of the owner's sites and P2 with one Serper search | Asked separately |
