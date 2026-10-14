# Plan — Google's and Bing's own AI reports in search-console-insights

Draft 2, 2026-10-14: scenarios approved by the owner (A1–A10, D1 as recommended), then changed where
the real files and the API probe proved draft 1 wrong — the changes are marked *(draft 2)*.

## Status

| Step | State | Evidence |
|---|---|---|
| Facts re-checked against the sources | done 2026-10-14 | "Facts" below |
| Requirements as scenarios (this document) | **approved** 2026-10-14 (draft 1); draft 2 changes A4 and A9 to fit the real files, as agreed in chat | this document |
| Decisions D1–D5 | **decided** 2026-10-14: D1 Google & Bing page; D3 probe done; D4 real files given; Bing pages and grounding queries later | "Decisions" below |
| Real exports, to build the reader against | **done**: Google and Bing exports of three of the owner's sites, downloaded 2026-10-14 (kept outside the repo; test copies use example.com) | "What the real files look like" below |
| API probe (D3) | **done** 2026-10-14, read-only, owner's OK: no AI value | "What the real files look like" below |
| Build, test-first | **done** 2026-10-14: `ai_reports.py`, the AI section in `search_report.py`, `references/ai-reports.md`, SKILL.md 1.8.0; 23 new tests (A1–A10 and the reading rules), 9 deliberate breakages of key rules each caught; the six real exports read into a throwaway home, totals match a separate count; page checked light and dark, phone width | this commit; `scripts/tests/test_ai_reports.py` |
| Owner's OK on A2 and A7 wording (draft 2: no download date in either file) | **approved** 2026-10-14 (chat) | — |
| DIFF gate (Normal: Codex + GLM 5.3) | running | trail: `REVIEW-diff-2026-10-14-ai-reports.md` |
| PR | not started | — |

## Facts (checked 2026-10-14)

1. **Google** launched "Search Generative AI performance reports" on 3 June 2026: one report for
   Search (AI Overviews and AI Mode), one for Discover. The only number is **impressions**:
   no clicks, CTR, position or queries. Views: Pages, Countries, Devices, Dates. Source:
   https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports
2. **Google's rollout is finished.** A note on that post and on the help page says that as of
   31 August 2026 the report is available to all websites worldwide. So "a site not in Google's
   rollout" no longer happens. What does happen: the report "usually doesn't appear" for a site
   that has not had enough impressions in AI features, and a site that has opted out of AI
   features is not eligible. Source: https://support.google.com/webmasters/answer/16984139
3. **Google's export writes "no data" as 0.** The help page: values shown as "~" or "-" in the
   report download as zeros. A 0 in the file is therefore not proof of zero.
4. **Google's API does not offer it.** The Search Analytics API reference (last updated
   11 August 2026) allows `type` = web, image, video, news, discover, googleNews: no AI type.
   It does not list `searchAppearance` values; only a real query shows them. Third-party reports
   say no AI value exists there either; that is not yet checked against a real property
   (decision D3). Source: https://developers.google.com/webmaster-tools/v1/searchanalytics/query
5. **Bing** launched "AI Performance" as a public preview on 10 February 2026: citations in
   Microsoft Copilot, Bing's AI summaries and some partner integrations; total citations,
   average cited pages, grounding queries, citations per page. No clicks or traffic. Bing's own
   post says the data is a sample. Source:
   https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview
6. **Bing has no API for it** that anyone has found; export is CSV or Excel. This rests on
   secondary sources and an unanswered Microsoft Q&A thread, not on a statement from Microsoft.
7. **Not confirmed by any source:** the data start date (18 May 2026 in the review), and the exact
   file names and column headers of either export. The reader must be built against real files.
8. `skills/search-console-insights` on main (e038603) uses neither report.

## What the real files look like (2026-10-14, three sites)

- **Google** downloads a zip named `<domain>-Performance-on-Search-Generative-AI-Features-<date>.zip`.
  Its files and headers are in the **language of the Search Console screen**: in German,
  `Diagramm.csv` (`Datum,Impressionen`), `Seiten.csv` (`Die häufigsten Seiten,Impressionen`),
  `Länder.csv`, `Geräte.csv`, `Filter.csv`. So the reader recognises each file by its contents
  (dates, addresses), never by a name or a header. The chart file has one row per day, or one per
  week (`2026-07-12 - 2026-07-18`) when the screen was set to weeks; the last week can be cut
  short. `Filter.csv` names the search type the download counts: all three said
  `Web (text-based)`, so the page quotes it. Safari may unzip the file into a folder; a folder
  is read the same way.
- **Totals agree where Facts expected:** chart, countries and devices add up to the same number
  (564, 1,155 and 193 on the three sites); the pages add up to more (621, 1,217, 204). The total
  comes from the chart file (A6). One site's pages include its `www.` address.
- **Bing**'s export (`<domain>_AIPerformanceOverviewStats_<M>_<D>_<YYYY>.csv`, UTF-8 with BOM,
  CRLF) is a daily overview only: `"Date","Citations","Cited Pages"`, dates written
  `7/14/2026 12:00:00 AM`, 90 rows. No page addresses, no grounding queries, no domain inside
  the file. "Cited Pages" counts pages per day, so it cannot be added up across days.
- **Google's API:** on one of the owner's sites (8,077 web impressions and 1,155 AI impressions in the
  same 90 days) a query grouped by `searchAppearance` returned no rows at all, for `web` and for
  `discover`; `type` values `aiOverview` and `aiMode` are refused (400). The API does not expose
  these numbers. Download is the only route.
- **Bing's API:** its published method list (last updated 2023-11-14) has no AI or citation
  method. A Bing key cannot fetch this report either.

## What changes for the owner

Today the owner's Google & Bing page (`search_report.py`) shows how often Google showed and
sent visitors to the site, and the AI page (`geo_check.py`) shows what assistants say when we
**ask** them. Neither shows what Google and Bing **record** about their own AI answers. These
two reports do: real impressions and real citations. Neither can be fetched by a program, so the
owner downloads each one and hands the file over; the page then shows it until a newer file
comes.

For most small sites both will be close to empty. That is a result, said plainly, not a fault.

## Scenarios

Dates are examples. "The page" is `~/.config/gsc-insights/reports/<site>/google.html`.

**A1 — Nothing added yet.** Given a site whose owner has never handed over either report, when
the page is built, then a section "Google's and Bing's AI answers" says in two sentences that
both now count how often the site appears in their AI answers, that they don't let programs read
those counts, and that the owner can download them and say *"here's my AI report from Google"*
(or Bing). No numbers, no warning box.

**A2 — A site with no AI data yet (Google).** Given the owner hands over Google's export,
covering 15 Jul – 13 Oct 2026, in which every impression is 0, when it is read and the page is
built, then the Google part says: *"Your download shows no impressions in Google's AI answers (it
covers 15 July – 13 October 2026). That is normal for a small site."* *(Changed after review round
1, owner's OK 2026-10-14: Google writes "not available" as 0, so the card says what the file shows.)* No 0 is printed, and no table or chart is drawn. The import
itself reports success.

**A3 — Google shows no AI report for the site.** Given the owner opens Search Console on
14 Oct 2026 and finds no generative AI report for the site, when they say so, then I record
"not shown, checked 14 Oct 2026" and the Google part says: *"Google doesn't show an AI report
for this site yet (you checked on 14 October 2026). Google shows it once a site has appeared in
its AI answers often enough."* This is a result, not a failure, and nothing reads as 0.
(This replaces "a site not in Google's rollout": see Facts 2.)

**A4 — A site with a Bing export that has data.** *(draft 2: Bing's export has no pages or
grounding queries.)* Given Bing's AI Performance export covering 14 Jul – 11 Oct 2026 with 39
citations on 11 of its 90 days, when it is read and the page is built, then the Bing part says:
*"Bing's AI answers (Copilot and Bing's AI summaries) cited your pages 39 times between 14 July
and 11 October 2026, on 11 of those 90 days."* One note: a citation means your page was shown as
a source; Bing counts a sample, and it says nothing about visits. Cited pages per day are not
added up. Pages and grounding queries come later, from Bing's other exports.

**A5 — A site with both.** Given a Google export with data (say 412 impressions, 9 pages) and
the Bing export of A4, when the page is built, then each has its own card with its own date
range and its own wording ("shown" for Google, "cited" for Bing). The page never adds the two,
never compares them, and never puts them in one table.

**A6 — Google export with data.** Given a Google export covering 15 Jul – 13 Oct 2026 with
412 impressions, when the page is built, then it says *"Your site was shown 412 times in
Google's AI answers (AI Overviews and AI Mode) between 15 July and 13 October 2026."* The total
comes from the dates view, never from adding up pages (one answer can show two of your pages).
Below: the pages, largest first. A page listed with 0 is left out of the table, since Google
writes "not available" as 0 (Facts 3).

**A7 — An old download.** *(draft 2: neither file holds its download date, so age is counted from
its last day of data.)* Given an export whose last day is more than 35 days ago, when the page is
built, then the card still shows it and adds: *"These numbers end on 2 September 2026; download
a new report for newer ones."* Not a warning box.

**A8 — A file I can't read.** Given a file that is not one of these two exports (an Excel file,
the ordinary Performance export, a renamed file), when the owner hands it over, then the import
stops with a plain reason and the column names it found, writes nothing, and the page keeps
what it had. Exit code non-zero.

**A9 — The wrong site's file.** *(draft 2: Bing's file holds no address.)* Given an owner with
four sites hands over an export whose file name, or (Google) whose pages, belong to another
domain, when it is read, then the import stops and names the domain the file is for. Nothing is
saved. A file whose name names no domain is accepted for an owner with one site; with more than
one, the import stops and asks for the domain at the start of the file name, as both Google and
Bing already write it.

**A10 — The weekly job.** Given the weekly job rebuilds the page, when it runs, then it shows the
last export handed over, unchanged, and fetches nothing new (there is nothing to fetch). It never
lists a missing export under "This run needs attention".

## Decisions for the owner

- **D1 — Where it shows.** *Recommended:* a new section on the Google & Bing page, after the
  Bing section. *Alternative:* on the AI page ("Does AI name you?") beside the questions we ask.
  Reason for the recommendation: these are Google's and Bing's own numbers, read like the rest of
  that page; the AI page measures something different (answers we ask for).
- **D2 — Google: Search only.** *Recommended:* read the Search report (AI Overviews, AI Mode);
  leave Discover out until a site of yours has Discover traffic. Discover is a separate report
  and a separate download.
- **D3 — One read-only probe.** *Recommended:* with your OK, one read-only query of Google's API
  on one of your sites, grouped by `searchAppearance`, to see whether any AI value exists. If one
  does, the Google half reads itself weekly instead of from a download, and I come back to you
  before building it.
- **D4 — Real files.** I need one real export of each report (any one of your sites, even an
  empty one) to build the reader against. Their headers are not documented anywhere I could
  find. The test copies in the repo will use example.com, never your domain.
- **D5 — Review depth.** *Recommended:* no PLAN gate (these scenarios are the check); a Normal
  DIFF gate (Codex + GLM 5.3) on the code, since it is shipped code.

## Release note (draft, for the next release)

- 📊 **See what Google and Bing count in their own AI answers.** Google now counts how often your site is shown in its AI Overviews and AI Mode, and Bing counts how often Copilot cites your pages. Neither lets a program read those numbers, so download each report and tell your assistant *"here's my AI report from Google"* (or Bing). Your Google & Bing page then shows them, each on its own, never added together. For a small site they are often empty for now, and the page says so plainly instead of showing a row of zeros.

*For the technically curious:* search-console-insights 1.8.0: `ai_reports.py` reads Google's generative AI export (the zip or its unzipped folder, in any screen language) and Bing's AI Performance overview CSV, and refuses another site's file. Google's Search Console API has no AI value and Bing's API no AI method (both checked 2026-10-14), hence the download.

## Not in scope

Countries and devices views; Discover (D2); charts over time (a total and a page list first);
reading Bing's Intents, Topics, Citation Share and Compare views (June 2026 additions);
reminding the owner to download on a schedule.
