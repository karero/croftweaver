# Plan — an analytics folder in each site's folder

Draft 1, 2026-10-14: requirements as scenarios, for the owner to approve. No product code yet.

## Status

| Step | State | Evidence |
|---|---|---|
| Requirements as scenarios (this document) | draft 1, **waiting for the owner** | this document |
| Decisions D1–D4 | open | "Decisions" below |
| Build, test-first | not started | — |
| Review gate | not started | — |
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

## Scenarios

Dates and names are examples; the site is `example.com` in the folder `~/Websites/example`.

**B1 — A new site.** Given the owner builds a new site, when the repo is first set up, then its
`.gitignore` holds `/analytics/` with a one-line comment saying why (downloads and AI-check
results hold the owner's data and stay off GitHub unless the owner asks).

**B2 — The owner hands over a download.** Given `example.com-Performance-on-Search-Generative-AI-
Features-2026-10-14.zip` in Downloads, when the owner says *"here's my AI report from Google"*,
then a copy lands in `~/Websites/example/analytics/ai-reports/2026-10-14/` (the date from the file
name when it has one, else today), it is imported from there, and the original in Downloads is
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
asks for the results as files, then they are copied to `analytics/geo/<date>/` (not
`docs/geo/<date>/`), under the same rules as B3–B5.

**B8 — Nothing else changes.** The weekly job, the report pages and `~/.config/gsc-insights/`
work as today; the folder is a kept copy, not where the skill reads from.

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

Moving files that already exist; the toolkit's own repo; any upload or sharing of the folder.
