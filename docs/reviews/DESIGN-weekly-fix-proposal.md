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
| Country and language | Set "by specifying the country and language" (`gl`, `hl`) | For T2 later: the site's country setting is three letters (`deu`), while `serp_check.py` expects two (`de`) and picks the language from them; the code must convert first |
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

**P1 results (2026-10-14, one real site, read-only; the script is
`docs/reviews/fix-proposal-probe/fix_probe.py` and prints counts only; it uses the report
page's window rule, and a rerun after review round 1 gave the same output, since the last
finished day was a Sunday):**

```
[1] recent range: metadata=yes firstIncompleteDate=2026-10-12; range ending 2026-09-24: metadata=no None
    window 2026-09-14..2026-10-11
[2] query rows=76; share of the property's impressions in listed queries: 28%
[3] pages=31; query-and-page rows=87; top pages, split by query as a share of the page total:
    page#1 100+: 54%  page#2 100+: 38%  page#3 100+: 6%  page#4 100+: 37%  page#5 100+: 12%
    page#6 50-99: 8%  page#7 50-99: 5%  page#8 50-99: 12%  page#9 20-49: 33%  page#10 20-49: 20%
[4] queries at position 8-20 with 50+ impressions (brand not removed): 2
[4] queries at position 8-20 with 20+ impressions (brand not removed): 4
[5] queries whose property position and weighted page position differ by 1+ places: 5 of 76
```

- **Missing metadata:** a range with nothing incomplete came back without `metadata`, so
  "absent means complete" holds on this site.
- **T2's figures:** a page's split by query held between 5% and 54% of the page's own
  total. A "100 non-brand impressions" floor on that split would be measuring a small,
  uneven slice. This settles DD0: T2 waits.
- **T1 on a small site:** before brand queries are taken out, 2 queries met the 50-impression
  floor in four weeks, 4 would at 20. Most weeks will have no proposal or the same one; that
  is what R5 asks for, but it is worth knowing before 0.32.
- **Position:** for 5 of 76 queries the two ways of averaging differ by a place or more, so
  T1 must take its position from the query rows, as §1 says.

**P2 so far (2026-10-14, one Serper search, the same site):** the site ranked 8th. Serper's
snippet for it was the page's own meta description, word for word. Serper's title was not
the page's `<title>`: the same words in another order, with the brand first, a rewrite.
Two of the ten results came back with no snippet at all. **The by-eye half (the owner, the same day):** Google, searched in private windows of
Safari, Chrome and Firefox at https://www.google.de/search?q=ai+events+munich&hl=de&gl=de,
showed the result 9th in all three, with the same title and snippet as Serper, word for
word. So on this sample Serper's text is Google's text, and Google keeps the page's
description and rewrites its title. For T2 later: a new description has a fair chance of
being shown; a new title may be rewritten again. P2 is settled. T2 still waits, for one
reason: P1 showed that a page's split by query held only 5% to 54% of its total, so T2
needs a page figure it can trust before it ships.

## 2. T1 first; T2 when a trustworthy page figure exists

The documentation weakens T2 (seen but rarely clicked) on both legs: its figures come from
a split Google says undercounts, and its decision rests on Serper text whose meaning
Serper does not state. T1 (striking distance) needs neither: query rows by property, one
drill-down, the page's own HTML. It is also the low-volume playbook's second item (`SKILL.md`, "Low-volume playbook").

**Decided (DD0, owner, 2026-10-14):** v1 for 0.32 ships T1, the edit, and the measuring. T2 follows
when P1 shows the undercount is small enough to trust a 100-impression floor and P2 shows
Serper's text matches Google's. *Against:* "seen but not clicked" is the playbook's
highest-return item on a small site, and dropping it halves what the proposal can say.

## 3. Shape

### 3.1 Where each part lives

| Part | File | Kind |
|---|---|---|
| Choosing the proposal, the cool-off, live detection, measuring | `scripts/fix_proposal.py` (new) | Pure functions plus a small command line; code decides, no model |
| Fetching what it needs | `scripts/search_report.py`, `fetch_google` | One more dimension group per window, `["query", "page"]`, paged as `run_query` already pages; plus the candidate page's live HTML |
| Showing it | `search_report.py`, `render` | One section at the end: "One thing to fix this week" |
| State and the owner's answers, per site | `~/.config/gsc-insights/sites/<site>-proposals.json` (new) | Proposals shown, declined, acted on, live observations, results; and the owner's answers: `brand` (spellings) and `pr_figures` (yes / no / unasked) |
| What the assistant does when asked | `references/fix-proposal.md` (new) | Instructions: check positioning, edit the four places, run the gate, open the pull request, record it |
| How the assistant gets there | `SKILL.md` | A pointer to the reference; the description stays as it is (it is at 998 of 1,024 characters) |
| The weekly log | `track.sh` | One line naming the proposal, or why there is none |

The owner's answers live in the new state file, **not** in `sites/<site>.json`: `track.sh`
and `schedule_tracking.sh` rewrite that file whole on every run, so anything else in it
would be lost. Nothing is written into the site's repository except the edit itself.

The **four places** are the requirements' R2 list: the page's `title`, its meta
`description`, its H1 and its first paragraph.

### 3.2 Choosing (code)

- **Fresh data only.** A proposal is chosen only from data fetched in this run. When
  `build` falls back to saved data (`search_report.py`, `build`, the `except` branch),
  the page shows no new proposal and says why (scenario 9); a proposal already acted on
  keeps its own line.
- **Brand spellings:** the state file's `brand`, a list. Until the owner confirms one,
  the report uses the domain's first label with hyphens as spaces and as nothing
  ("radwerk plagwitz", "radwerkplagwitz") and says "counted as your business name: …;
  tell your assistant if that is wrong". Matching uses `_lang_normalize.fold`, so
  umlaut spellings match.
- **T1 candidates:** from the window's `["query"]` rows (position by property): not brand,
  average position 8 to 20, at least 50 impressions. For each, from the
  `["query", "page"]` rows: the page with most of its impressions.
- **The page check:** the candidate page's live HTML is fetched once. A timeout, an
  answer other than 200, or a page without a `<title>` drops the candidate, and the
  report says why. The query counts as **already on the page**, and is dropped, when
  every word of it appears as a whole word, folded, in the title, the H1 and the first
  paragraph taken together. Every word counts, short ones too ("ki"); only these are left out: der, die, das, den,
  dem, des, ein, eine, und, oder, in, im, am, an, auf, für, mit, von, zu, bei; the, a, an,
  and, or, in, on, at, for, of, to, with, near. A query left with no word to check is never
  "already on the page".
- **Excluded:** everything in R1's "never proposed" list, read from the state file (open
  pull request, merged but not live, measuring not finished, declined within 12 weeks),
  and a query already on the page.
- **One proposal:** most impressions wins.

### 3.3 Acting (the assistant, guided by `references/fix-proposal.md`)

The owner says the report's sentence. It starts with the skill's name, so the assistant
loads it without relying on the description, and then names the search, every place and
the page, as R1 asks: *"search-console-insights: work 'fahrrad reparatur leipzig' into the
title, heading and first paragraph of https://radwerk-plagwitz.example/reparatur"*. Whether that sentence alone loads the skill in a fresh
session is not known; step 4 tries it cold in Claude Code and in Codex before the
wording is final.

The reference tells the assistant to:

1. read the proposal from the state file (`fix_proposal.py show <site>`), never from
   memory;
2. read `POSITIONING.md`; on a conflict, quote the line, make no edit, and record it
   (`fix_proposal.py decline <site> --reason positioning`);
3. follow the site's own `AGENTS.md` for branch, wording rules, gate and pull request;
   change only the four places;
4. on a public repository, ask about figures once if `pr_figures` is unasked, and record
   the answer (`fix_proposal.py set <site> pr_figures yes|no`; the same command records
   the owner's spellings, `set <site> brand "radwerk, rad werk"`, which replace the guess);
5. record the pull request and the page's new `<title>` text, not the pull request's
   title (`fix_proposal.py acted <site> --pr <url> --new-title "<the whole new <title> of the built page>"`;
   the command reads the number and repository from the address).

Every state write is a command, so the model never edits the JSON by hand.

### 3.4 Following the pull request, live, and measuring (code)

- **Pull request state.** `acted` records the pull request's number and repository
  (`owner/name`) beside its address. Each run asks GitHub with
  `gh pr view <number> --repo <owner/name> --json state,mergedAt,closedAt` when `gh` is
  installed and signed in. Closed without merging counts as the owner's "not this one"
  (R3): the 12 weeks start on the `closedAt` day, not the day the report noticed;
  reopened cancels that. Merged: the proposal waits to be seen live.
- **Nothing is released by a timer.** While the pull request is open, or merged but not
  seen live, the page stays excluded (R1) and each report says what is waiting: "your
  proposal of 2 November is waiting in pull request 31", or "merged, not seen on the live
  site yet; on a two-stage site that needs `npm run ship`". The owner can turn it down in
  words at any time. When `gh` is missing or fails, the state stays as it was and the
  report says "pull request 31 could not be checked; tell your assistant if it was
  closed".
- **Live.** When the proposal is chosen, the report keeps the page's current `<title>`
  (it fetched the page for the word check). The assistant records the **whole rendered**
  new `<title>`, layout suffix included, read from the built page after the gate's build
  (`--new-title`). `acted` refuses a new title that equals the old one once folded and
  with spaces collapsed, since the two could not be told apart. Each later run fetches the
  page again and compares whole titles the same way. Four outcomes: **new** (equal to the
  recorded new title), **old** (equal to the kept old one), **other** (a readable title
  that is neither), **unreadable** (a timeout, an error, an answer other than 200, no
  `<title>`). Unreadable changes nothing. Other, before the first new check, means the
  page changed in another way: the report says so and keeps waiting; after it, see below.
- **Windows (DD8).** Measured from the weekly checks, not from the exact day: the
  before-window is the four full weeks ending on the last Sunday before the last **old**
  check; the after-window is the four full weeks starting on the first Monday on or after
  the first **new** check. With scenario 8's Monday checks (old on 2026-11-02, new on
  2026-11-09) that gives 2026-10-05 to 2026-11-01 and 2026-11-09 to 2026-12-06. Both edges
  are fixed at the first **new** check: "the last old check" means the last one before
  it. A missed or unreadable check only makes the gap between the windows wider; it never
  puts a day of the new page into the before-window.
- **Before and after only (DD7).** The report shows the query's position, impressions and
  clicks in both windows and says: "This compares one search before and after the change.
  It does not check what else changed on your site or in Google's results." It never says
  "consistent with". If a check during the after-window finds any title other than the
  new one (the old one back, or a third), the page has changed again: the report shows the
  figures up to that week and says so. Comparing against the rest of the site is later work.
- **The figures** come from two requests made for this purpose, one per window, filtered
  to the proposal's query (`equals`, lowercased, as the report's key searches are) with the
  report's country setting and property; the rolling proposal window is not used. They are
  fetched once the complete data (R1) reaches the after-window's last Sunday, and the
  result goes into the state file, so the comparison is computed once and the page shows
  it from then on.

## 4. Tests

- **Pure functions** in `fix_proposal.py`: choosing (each exclusion, the 50 floor, ties,
  folding, the word check with short words and a query of stop words only); the four live
  outcomes (a shortened new title inside the old one, the old title with a new layout
  suffix, an unreadable answer, and a new title equal to the old one, which `acted`
  refuses); the window edges, a rollback after the first new check included; the pull
  request states (open, merged, closed between two checks, reopened, unknown); and a page
  that changes again during the after-window. The dates of the requirements' scenarios 1,
  2, 4, 6 and 8 are test cases as written.
- **Through the real entry point** (global rule 9): `search_report.build` with the fake
  Search Console service `test_search_report.py` already uses (`FakeGoogle`) and a local
  HTTP server for the live page, as `_geo_stub.py` serves the AI check's tests. One test
  per requirements scenario that the report can show (1, 2, 6, 8, 9), and one where Google
  fails while an eligible proposal sits in the saved data.
- **The command line** through `subprocess`, the way the owner's assistant calls it, with
  a stub `gh` on the path answering each pull request state.
- **The assistant's part** (scenarios 1, 4, 5, 7): evals in `evals/evals.json`, run with
  and without the reference, as `website-story` had; plus the cold start of §3.3.
- **Scenario 3** (seen but not clicked) has no test in v1: T2 waits (§2).

## 5. Steps

| # | Step | Waits for |
|---|---|---|
| 1 | P1 probe and P2 check (both done 2026-10-14) | — |
| 2 | `fix_proposal.py` and its pure tests | — |
| 3 | The report: fetch, render, state, entry-point tests | 2 |
| 4 | `references/fix-proposal.md`, the SKILL.md pointer, evals, the cold start | 3 |
| 5 | `track.sh` line; `make check` and CI | 3 |
| 6 | Review gate, Normal (code, no untrusted input beyond the owner's own pages) | 4 and 5 |
| 7 | Release note line for 0.32 | 6 |

## 6. Decisions for the owner

Answered by the owner on 2026-10-14: DD0 to DD5 as proposed; DD6 yes (P1 on one of the
owner's sites, P2 with one Serper search).

| # | Decision | Answer |
|---|---|---|
| DD0 | T1 only in v1; T2 when a trustworthy page figure exists | Yes (§2) |
| DD1 | State on the owner's computer, beside the settings | Yes: nothing about search figures enters the site's repository |
| DD2 | Live detection by finding the new title on the live page | Yes: needs no access to the hosting, works on both publish models |
| DD3 | Control: any other change under `src/` or `public/` in the span means no comparison | Replaced by DD7 |
| DD4 | The owner's sentence names the skill | Yes: the description has no room for new trigger phrases |
| DD5 | Brand spellings start from the domain and are shown until confirmed | Yes: a proposal on day one, with the guess visible |
| DD6 | Run P1 on one of the owner's sites and P2 with one Serper search | Yes; both done 2026-10-14 (§1) |
| DD7 | Measuring in v1: before and after of the one search, without the comparison against the rest of the site, and never "consistent with" | Yes (owner, 2026-10-14): the comparison drew BUGs in both review rounds |
| DD8 | Windows from the weekly checks that saw the old and the new page, not from the exact day | Yes (owner, 2026-10-14) |
