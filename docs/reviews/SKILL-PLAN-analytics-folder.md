# Plan — an analytics folder in each site's folder

Draft 2, 2026-10-14: B1–B8 and D1–D4 approved by the owner as recommended; draft 2 adds the folder's
layout and B9–B12 from the owner's answers the same day (marked *(draft 2)*).

## Status

| Step | State | Evidence |
|---|---|---|
| Requirements as scenarios (this document) | B1–B8 **approved** 2026-10-14; layout and B9–B12 from the owner's answers (draft 2) | this document |
| Decisions D1–D4, and the layout choices L1–L4 | **decided** 2026-10-14: D1–D4 as recommended; L1–L4 as recorded below | "Decisions" below |
| Build, test-first | **done** 2026-10-14: starter `.gitignore`; `_analytics.py`; `ai_reports.py --keep-in`; `analytics_snapshot.py`; `references/analytics-folder.md` and pointers (SKILL.md 1.9.0, ai-reports, geo-check, facts-check, positioning-check); 15 new tests at round 1 (16 was a miscount), 25 after its fixes; 11 deliberate breakages each caught (one only after a test was added); `make test` 264 OK, `make check` exit 0 at round 1 | this commit; `scripts/tests/test_analytics.py` |
| B12: the owner's `docs/geo/` moved into `analytics/` | not started (a change in that site's repo, after this one) | — |
| Review gate | round 1 done (see trail), fixes in; round 2 next | `REVIEW-diff-2026-10-14-feat-analytics-folder-f3cea24.md` |
| PR | not started | — |

## Why

Two kinds of analytics file now come to the assistant: Google's and Bing's AI reports, which the
owner downloads and `ai_reports.py` imports (search-console-insights 1.8.0), and the AI check's
results, which the reference file already tells the assistant to copy into the site's repo
(`references/geo-check.md`: "for example `docs/geo/<date>/`", private repos only). Both end up
read from `~/.config/gsc-insights/`, a hidden folder the owner rarely opens, and the downloads
stay scattered in `~/Downloads`. The owner asked for one place per site: an `analytics/` folder in
the site's own folder.

## Facts (checked 2026-10-14)

1. The starter's `.gitignore` (`skills/new-website/templates/.gitignore`) is copied once, when a
   site is created (new-website, "init repo"). It has no analytics entry today.
2. The update check (`scripts/whats-new.sh`) compares a fixed list of template files
   (`TEMPLATE_TRACKED`); `templates/.gitignore` is not on it. A site built earlier never hears
   about a new line there.
3. search-console-insights does not know where a site's folder is: no script takes a site folder,
   and nothing records one.
4. A site's repo may be public (the toolkit's own brand site is). The AI check's rule already
   says its results go only into a private repo.
5. On 2026-10-14 the owner's three private site repos got `analytics/ai-reports/2026-10-14/` by
   hand, kept out of git by a local `.git/info/exclude` line, not a committed `.gitignore` line.

## The folder's layout *(draft 2)*

```text
analytics/                         kept off GitHub (.gitignore: /analytics/)
  README.md                        what is here, where each file comes from, why it is not on GitHub
  actions.md                       suggested actions by priority (P1–P3), dated, never deleted
  eeat.md                          E-E-A-T checklist, judged by the assistant, dated sections
  seo.html                         latest Google & Bing page (search, AI Overviews, Copilot)
  geo.html                         latest "Does AI name you?" page
  2026-10-14_gsc/                  raw Search Console data the page was built from
  2026-10-14_bing/                 the site's Bing rows from the tracker's history
  2026-10-14_google-ai-report/     Google's generative AI download, as received
  2026-10-14_bing-ai-report/       Bing's AI Performance download, as received
  2026-10-07_geo-run/              one AI-check run: its page and every answer word for word
  facts-history.csv                one line per facts check: pages read, mismatches, outdated values
  2026-10-14_facts-check/          one facts check: facts-report.md and facts-report.json
  2026-10-14_positioning-check/    one positioning check: verdict.md (the assistant's judgment)
```

The top level is what the owner reads; the dated folders are the evidence `actions.md` links to.
"Over time" lives on the pages (16 months of Search Console, the AI check's weekly trend); a
dated folder keeps what one snapshot was built from.

## Scenarios

Dates and names are examples; the site is `example.com` in the folder `~/Websites/example`.

**B1 — A new site.** Given the owner builds a new site, when the repo is first set up, then its
`.gitignore` holds `/analytics/` with a one-line comment saying why (downloads and AI-check
results hold the owner's data and stay off GitHub unless the owner asks).

**B2 — The owner hands over a download.** Given `example.com-Performance-on-Search-Generative-AI-
Features-2026-10-14.zip` in Downloads, when the owner says *"here's my AI report from Google"*,
then a copy lands in `~/Websites/example/analytics/2026-10-14_google-ai-report/` *(draft 2: the
layout's name)* (the date from the file name when it has one, else today), it is imported from there, and the original in Downloads is
left alone. The reply names the folder.

**B3 — Nothing reaches GitHub unasked.** Given B2 on a public repo, when the owner runs
`git status`, then the folder does not show, and no commit or push the assistant makes includes
it.

**B4 — A site built before this.** Given a site whose `.gitignore` has no `/analytics/` line, when
a file is about to be placed there, then the assistant first adds the line (one small commit,
named as such), and only then places the file. It never puts a file into an `analytics/` folder
git would pick up.

**B5 — The owner wants it in the repo.** Given a private repo and the owner says *"keep the
analytics in the repo"*, then the assistant asks once, names that the files hold the owner's
data, and on a yes removes the line and commits the folder. On a public repo it says no and
explains, as the AI check's rule already does.

**B6 — No site folder at hand.** Given the owner works with no site folder open (the assistant
cannot tell which folder is the site's), when a download is handed over, then the assistant asks
which folder the site lives in, or imports without keeping a copy if the owner prefers; it never
guesses a folder.

**B7 — The AI check's results** (depends on D3). Given a weekly AI check has run, when the owner
asks for the results as files, then they are copied to `analytics/<run date>_geo-run/` (not
`docs/geo/<date>/`), under the same rules as B3–B5.

**B9 — The owner asks to update the folder** *(draft 2)*. Given reports exist for example.com,
when the owner says *"update my analytics folder"* (or asks to see the reports), then the assistant
runs one command that writes `seo.html`, `geo.html` (when the AI check is set up), `README.md`,
and the dated raw folders: `<date>_gsc/` (the saved Google data), `<date>_bing/` (the site's Bing
rows, from the history file the Google & Bing page reads), `<run date>_geo-run/` (the newest
AI-check page and the answers of every run it shows). *(Draft 3, after review round 1: a kept file
is never rewritten; newer content under the same name is kept beside it, `google-data-2.json`, so
the evidence always matches the page. Draft 2 left a whole dated folder alone, which dropped a
second fetch or run on the same day.)* In the copies, `seo.html` and `geo.html` link
to each other, never into the hidden settings folder.

**B10 — Suggested actions** *(draft 2)*. Given a snapshot, when the assistant reviews it, then
`actions.md` gains dated entries, each with a priority (P1 now, P2 soon, P3 when there is time),
what to do, why, the evidence as a link into a dated folder, and a status. Nothing is deleted: a
done action is marked done with its date, so the owner sees whether the numbers moved after it.

**B11 — E-E-A-T** *(draft 2)*. Given a snapshot, when the assistant reviews the site, then
`eeat.md` gains a dated section: each checklist item (who wrote it, about page, sources cited,
contact, reviews and testimonials, dates on content) judged as met, partly, not yet, or can't
tell, with one line why. The file says at the top that this is the assistant's judgment: Google
publishes no E-E-A-T score and these tools collect no signal for it.

**B12 — The owner's existing AI-check results** *(draft 2)*. The owner's one site with results in
`docs/geo/` (a private repo) moves them to `analytics/<run date>_geo-run/` with `git mv`, so that
repo keeps tracking them (the owner's choice, B5). A separate change in that site's repo.

**B13 — The facts check** *(draft 2, owner's addition)*. Given the site has a facts list
(`facts.json`, which stays where the owner keeps it: it is the owner's list, not analytics), when
the folder is updated (B9), then the facts check runs with its report in
`<date>_facts-check/` and one line added to `analytics/facts-history.csv`. A figure on a live page
that no longer matches the list becomes a P1 entry in `actions.md`. Why: a site that blogs or posts
news quotes its figures again and again, and an old number in a new post is the commonest drift.

**B14 — The positioning check** *(draft 2, owner's addition)*. Given `POSITIONING.md` exists, when
the folder is updated and the site has pages it did not have at the last verdict (new posts, news),
then the assistant runs the positioning check on the new and changed pages and saves its verdict
(Clear / Blurred / Broken, the biggest gap, the fixes) to `<date>_positioning-check/verdict.md`,
marked as judgment. Blurred or Broken findings become entries in `actions.md`. With no new pages
since the last verdict, it is skipped and the update says so. *(The "only when pages are new"
trigger is the assistant's proposal, to avoid paying for the same judgment every week: the owner
may overrule it.)*

**B8 — Nothing else changes.** The weekly job, the report pages and `~/.config/gsc-insights/`
work as today; the folder is a kept copy, not where the skill reads from.

## Layout choices *(draft 2, decided by the owner 2026-10-14)*

- **L1 — Names:** date first, ISO with dashes, lowercase source (`2026-10-14_gsc`).
- **L2 — E-E-A-T:** in v1, as a judged checklist (B11).
- **L3 — Who fills it:** the assistant, when asked (B9); the weekly job does not write there in v1.
- **L4 — The existing `docs/geo/`:** moves into `analytics/` and stays committed in its private repo (B12).

## Decisions for the owner

- **D1 — When the folder appears.** *Recommended:* only when the first file needs it (B2), with
  the `.gitignore` line set from the start (B1). *Alternative:* an empty `analytics/` with a short
  README in every new site.
- **D2 — Who makes the copy.** *Recommended:* `ai_reports.py import` gains `--keep-in <site
  folder>`, so the copy and the import happen in one step and are tested together. *Alternative:*
  the assistant copies by hand, as instructed in `references/ai-reports.md`.
- **D3 — The AI check's results.** The reference file says `docs/geo/<date>/`, committed in
  private repos (as one of the owner's sites does). *Recommended:* new results go to
  `analytics/geo/<date>/` and follow B3–B5; existing `docs/geo/` folders stay where they are.
  *Alternative:* keep `docs/geo/` for the AI check and use `analytics/` for downloads only (two
  places).
- **D4 — Telling existing sites.** *Recommended:* B4 (the assistant adds the line when it first
  needs the folder). *Alternative:* also add `templates/.gitignore` to the update check's list,
  which then reports every difference in a file each site owns.

## Not in scope

Moving files that already exist, except B12; the weekly job writing the folder (L3); removing
old dated folders; the toolkit's own repo; any upload or sharing of the folder.
