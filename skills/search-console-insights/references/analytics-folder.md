# The site's analytics folder

Each site keeps its reports, downloads and checks in `analytics/` inside the site's own folder,
next to `POSITIONING.md` and `package.json`. It is a kept copy for the owner: the skill still
reads from `~/.config/gsc-insights/`. The folder holds the owner's data, so it stays off GitHub:
the site's `.gitignore` has the line `/analytics/` (new sites get it from the starter). The design
and its scenarios (B1–B14): `docs/reviews/SKILL-PLAN-analytics-folder.md` in the Croftweaver repo.

```text
analytics/
  README.md   actions.md   eeat.md   seo.html   geo.html   facts-history.csv
  2026-10-14_gsc/   2026-10-14_bing/   2026-10-14_google-ai-report/   2026-10-14_bing-ai-report/
  2026-10-12_geo-run/   2026-10-14_facts-check/   2026-10-14_positioning-check/
```

Dated folders put the date first, so they sort by time. The scripts never rewrite a kept file:
newer content under the same name is kept beside it (`google-data-2.json`). `README.md`,
`seo.html` and `geo.html` are the latest views and are rewritten. A check you run twice on one day
writes into that day's folder again.

## Before the first file

1. **Know the site's folder.** Use the folder the session works in when it is the site (it has
   the site's `package.json` or `POSITIONING.md`). Otherwise ask the owner which folder it is;
   never guess one. If the owner has none at hand, import without keeping a copy.
2. **Keep it off GitHub.** If the site's `.gitignore` has no `/analytics/` line (a site built
   before this), add it with its comment from the starter and commit only that, as
   "keep analytics/ off GitHub". The scripts check every path they write and refuse, writing
   nothing, when git would pick one up or already tracks it. For the files you write yourself
   (`actions.md`, `eeat.md`, the facts and positioning checks), check first that,
   in the site folder, for each file you will write, `git check-ignore -q --no-index analytics/<file>` succeeds and `git ls-files -- analytics/<file>` prints nothing.
3. **Only on the owner's ask, and only in a private repo,** keep the folder in the repo: name
   that it holds their data, ask once, then remove the line and pass `--commit-ok`. In a public
   repo say no, as the AI check's rule already does (`geo-check.md`, "Keep them out of a public repo").

## Filling it (when the owner asks)

Run these from this skill's folder with `~/.config/gsc-insights/venv/bin/python`:

- **A download** (Google's or Bing's AI report): `scripts/ai_reports.py import <domain> <file> --keep-in <site folder>`.
  It keeps the file in `<date>_google-ai-report/` or `<date>_bing-ai-report/` (the date from
  the file's name) and imports it.
- **"Update my analytics folder"**, or after showing the reports: build them first
  (`scripts/search_report.py <domain>`, and `scripts/geo_check.py <domain> --report` when the AI
  check is set up), then `scripts/analytics_snapshot.py <domain> --site-dir <site folder>` (add
  `--csv <file>` when the Google & Bing page was built with one). It writes `README.md`,
  `seo.html`, `geo.html`, the Search Console data and Bing rows the page was built from, and the
  AI-check page with the answers of every run it shows, and says what it skipped.
- **The facts check**, when the site has a facts list (`facts.json`, wherever the owner keeps it):
  run the facts-check skill's script from the site folder with
  `--out analytics/<today>_facts-check/facts-report.md --json analytics/<today>_facts-check/facts-report.json --history analytics/facts-history.csv`
  (create the dated folder first: `mkdir -p analytics/<today>_facts-check`). Exit code 1 means
  findings, not a failure.
- **The positioning check**, when `POSITIONING.md` exists and pages were added or changed since
  the last verdict. In the site folder, `git log --since=<the last verdict's date> --name-only --
  <pages folder>` lists the committed ones and `git status --porcelain -- <pages folder>` the rest
  (the pages folder is `src/` in a site built with this toolkit; another site, ask). With no git,
  judge every page. Run the website-positioning-check skill on those pages and save its verdict to
  `analytics/<today>_positioning-check/verdict.md`, starting with "The assistant's judgment, not a
  measurement" and ending with the pages judged and the full list of the site's pages. Nothing
  added or changed: skip it and say so.

## The two files you write

**`actions.md`**, newest entries first, one entry per action:

```markdown
## 2026-10-14
- **P1** — Fix "27,000 members" on /blog/spring-update: the facts list says 31,000.
  Why: a figure on a live page that contradicts the list. Evidence: [facts check](2026-10-14_facts-check/facts-report.md).
  Status: open
```

P1 now (wrong facts on live pages, a Broken positioning verdict, a page Google cannot show), P2
soon (striking-distance searches, a Blurred verdict, snippet fixes the live check supports), P3 when
there is time. Never delete an entry: change its status to `done 2026-10-20` or `dropped
2026-10-20: <why>`, so the owner sees whether the numbers moved after it. Every action names its
evidence as a link into a dated folder.

**`eeat.md`**, a new dated section at each review, newest first. Start the file with: "The
assistant's judgment, not a measurement. Google says E-E-A-T itself isn't a specific ranking
factor (Search Central, 'Creating helpful, reliable, people-first content'), and these reports
collect no signal for it." Judge each item as met, partly, not yet, or can't tell, with one line
why: who wrote the content (named people, their background), an about page, sources cited for
claims, a way to reach a real person, reviews or testimonials, dates on articles and news. An
item that moved since the last section says so.

## Reading it with the owner

Lead with `actions.md` (open P1s first), then the newest numbers in `seo.html` and `geo.html`.
The dated folders are evidence, not reading. When the folder is copied or zipped for someone, it
carries the owner's data: say so before it leaves the computer.
