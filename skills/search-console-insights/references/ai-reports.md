# Google's and Bing's own AI reports

Google and Bing now count how often a site appears in their AI answers: **Google** the
impressions in AI Overviews and AI Mode (Search Console → the generative AI report for Search),
**Bing** the citations in Copilot and Bing's AI summaries (Bing Webmaster Tools → AI
Performance). These are real answers people saw, which the AI check (`geo-check.md`) cannot
give: that one asks questions of its own.

Neither report can be read by a program: Google's API has no AI value (probed 2026-10-14) and
Bing's API has no AI method. The owner downloads each one and hands it to you;
`scripts/ai_reports.py` reads it and the Google & Bing page (`search_report.py`) shows it until a
newer file comes. The design and its scenarios (A1–A10): `docs/reviews/SKILL-PLAN-ai-reports.md`
in the Croftweaver repo.

## When the owner asks

Owners say *"here's my AI report from Google"*, *"add my Bing AI numbers"*, or just drop a file.

1. **Ask for the download if there is none.** Google: Search Console → the generative AI report
   (Search) → **Export** → CSV. It arrives as a zip; Safari may unzip it to a folder,
   which works too. Bing: Bing Webmaster Tools → **AI Performance** → **Export** → CSV. Never ask
   them to rename the files: both start with the domain, and that is how the wrong site's file is
   caught.
2. **Read it:** `~/.config/gsc-insights/venv/bin/python scripts/ai_reports.py import <domain> <file or folder>`.
   It prints one line on success. On a refusal (exit 1) it says why and saves nothing: pass the
   reason on in plain words.
3. **If Search Console shows no generative AI report** for the site, that is a result: Google
   usually shows it once a site has appeared in its AI answers often enough. Record it with
   `ai_reports.py not-shown <domain>`.
4. **Show the page:** `search_report.py <domain>` and open the path it prints.

## Reading the numbers

- **Empty is a result, never a fault.** Many small sites have little or nothing here yet. Say "no
  data yet", never "0", and never suggest something is broken.
- **Google writes "not available" as 0** in its download. A 0 on one day or one page is not
  evidence of anything.
- **Google's total is the chart's.** The pages add up to more, because one answer can show
  several pages of the same site (rule 1 of "Reading the numbers" in `SKILL.md`, again).
- **Google's download counts one search type**, named on the page (on 2026-10-14: "Web
  (text-based)").
- **Bing counts a sample**, and a citation says nothing about visits. Bing's export holds no page
  addresses; its "Cited Pages" is per day and is never added up.
- **Never add or compare Google's impressions and Bing's citations.** Different things, counted
  by different companies.
- The files are named and headed in the language of the owner's screen (a German Search Console
  writes `Seiten.csv`). The script reads them by their contents (dates, addresses, numbers), not their names; it was
  tested with a German screen's download.
