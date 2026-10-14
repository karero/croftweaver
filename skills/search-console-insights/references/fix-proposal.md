# The weekly fix proposal: making the change the report proposes

The Google report page (`search_report.py`) ends with **"One thing to fix this week"**: at
most one search that already brings the site close to page 1 (average position 8 to 20, at
least 50 times shown in four weeks) and whose words the page that search leads to does not
yet say. The page gives the owner one sentence to say to you, for example:

> /search-console-insights work 'fahrrad reparatur leipzig' into the title, heading and
> first paragraph of https://radwerk-plagwitz.example/reparatur

When the owner says it, follow this file. Code chose the proposal; your part is the
judgment (does it fit the positioning, what is the wording) and the edit, through the site's
own tests. The rules behind it: `docs/reviews/SKILL-PLAN-scheduled-search-fixes.md` and
`docs/reviews/DESIGN-weekly-fix-proposal.md` in the Croftweaver repository.

**Contents:** The commands · Step by step · What you may change, and what you may not ·
When the owner says no · Questions owners ask

## The commands

Every record of the proposal lives in `~/.config/gsc-insights/sites/<site>-proposals.json`.
Change it only with these commands, never by editing the file. Run them from this skill's
folder:

```bash
~/.config/gsc-insights/venv/bin/python scripts/fix_proposal.py show <site>
~/.config/gsc-insights/venv/bin/python scripts/fix_proposal.py decline <site> [--reason positioning] [--page <address>]
~/.config/gsc-insights/venv/bin/python scripts/fix_proposal.py acted <site> --pr <pull request address> --new-title "<the built page's whole <title>>" [--page <address>]
~/.config/gsc-insights/venv/bin/python scripts/fix_proposal.py set <site> brand "<spelling>, <spelling>"
~/.config/gsc-insights/venv/bin/python scripts/fix_proposal.py set <site> pr_figures yes|no
```

`<site>` is the bare domain (`radwerk-plagwitz.example`). Without `--page`, `decline` and
`acted` work on the report's current proposal, or, once the owner has acted on it, on the
newest one still in progress. `--page <address>` picks an earlier one.

## Step by step

1. **Read the proposal from the file**, never from memory or from the sentence alone:
   `fix_proposal.py show <site>`. If it shows no proposal, or another search or page than
   the owner named, say so and offer to build the report again; do not edit.
2. **Work in the site's own repository**, following its `AGENTS.md` from §1 on: check for
   unsaved changes, fetch, and start a branch from the newest `main`
   (`content/search-<date>`). If this folder is not the site's repository, or the site has
   no tests (no `tests/` folder with the starter's spec files), stop and say so: the change
   would go out untested.
3. **Check the positioning first.** Read `POSITIONING.md`. If the search pulls against it (a
   price angle the owner ruled out, a service the business does not offer, an audience it
   does not serve), make no edit. Quote the line, say that competing on that would be a
   positioning change (the `website-positioning` skill), and record it:
   `fix_proposal.py decline <site> --reason positioning`.
4. **Find the page's source.** The address's path gives it: `/reparatur` is
   `src/pages/reparatur.astro`, or an entry in `src/content/<collection>/` when the site's
   routes build that page from a collection. The `title` passed to the `Base` layout (or set
   in the entry's frontmatter), the page's `<h1>` and its first paragraph are the three
   places the sentence names. On a collection entry, the title often is the H1 too.
5. **Make the edit** in those three places (below). Work the search's words in as a person
   would say them; the exact phrase is not required, every word is, and a compound counts
   ("Fahrradreparatur" carries "fahrrad" and "reparatur"). Leave the meta `description` as
   it is: the sentence does not name it.
6. **Run the gate** the way `AGENTS.md` §2 says: the pre-push hook runs the full suite, or
   `npm run verify` where the hook is not on. If a test refuses the change (a title over the
   limit, a word `tone.spec.ts` bans, a term `positioning.spec.ts` requires), fix the wording
   in the same places and run it again. Never change a test, never push with
   `--no-verify`.
7. **Read the new title as the site will serve it**: after the gate's build, the page's
   `<title>` in `dist/` (`dist/reparatur.html` for `/reparatur`, `dist/index.html` for the
   home page), layout suffix included. That whole text is what the report looks for on the
   live site.
8. **Figures in the pull request.** `show` prints `Search figures in pull requests`. If the
   repository is public (`gh repo view --json visibility -q .visibility`) and the answer is
   `unasked`, ask the owner once whether search figures may appear in pull requests, which
   anyone can read, and record it (`set <site> pr_figures yes|no`). On `no`, the pull
   request names the change and the reason and points to the report page for the numbers.
   On a private repository, give the figures, each with its four-week window.
9. **Open the pull request** as `AGENTS.md` §2 says, in the owner's language: the page's
   full address, the old and the new wording side by side, why (the search, and that the
   page did not say it), the test result, and the preview address where the site has one.
10. **Record it:** `fix_proposal.py acted <site> --pr <address> --new-title "<title from
    step 7>"`. The command refuses a new title that cannot be told apart from the old one.
11. **Tell the owner what happens next:** nothing is live until they merge (and, on a site
    that publishes in two steps, run `npm run ship`); the weekly report follows the pull
    request and the live page, and about five weeks after the change is live it shows the
    search's position, times shown and visits before and after. You merge only when they ask.

## What you may change, and what you may not

**Change only:** the page's `title`, its `<h1>` and its first paragraph, on an existing page or
collection entry. Not its meta `description`: the sentence does not name it.

**Never, in this task:** create, delete or rename a page; touch redirects, `noindex`,
`robots.txt`, the sitemap, `public/_headers`, `src/config.ts`, `astro.config.mjs`,
`package.json`, `.github/`, `scripts/`, `functions/` or `AGENTS.md`; touch any test, `PAGES`
or a row of `positioning.spec.ts`; add internal links.

**Invent nothing** (`AGENTS.md` §4). Every claim in the new wording must already be on that
page or in `POSITIONING.md`: no new prices, numbers, names, years or customer quotes. If a
good wording needs a fact, ask the owner for it; do not write a `[MISSING: …]` placeholder.
Keep the form of address, the language and the voice of `CONTENT_GUIDE.md` and `BRAND.md`.

**What wins:** `POSITIONING.md` over the search data; the wording rules (tone, the title
limit in `AGENTS.md` §6) over the search's exact
words; the terms `positioning.spec.ts` requires stay.

## When the owner says no

"Not this one", in any words, or closing the pull request: run
`fix_proposal.py decline <site>` (add `--page <address>` if the owner means an earlier
proposal than the report's current one). The report does not propose that search on that page again
for 12 weeks and says until when. Closing the pull request is noticed by the report on its
own (it asks GitHub with `gh`), counted from the day it was closed. The report follows a pull
request only while its proposal is in progress; once that round is measured, or turned down
and its 12 weeks are over, an old pull request reopened later is not followed. If the owner
reopens one, say so and check the page by hand.

## Questions owners ask

- **"Why this search?"** It already brings the site close to page 1, so a page that says
  what people search for has the best chance of moving up. The report names the figures.
- **"Did it work?"** The report answers about five weeks after the change is live, for that
  one search. It does not check what else changed on the site or in Google's results, so
  say "the position went from 11.4 to 7.9", not "the change worked".
- **"The name it counts as my business is wrong."** Record the spellings people use:
  `fix_proposal.py set <site> brand "radwerk, rad werk"`. Searches for the business by name
  are never proposed: they say nothing about how the site is found.
- **"The report says the page changed in another way."** The title recorded with `acted` is
  not what the live page shows (a different layout suffix, a later edit). Read the live
  page's `<title>`, check with the owner that it is the change they merged, and record it:
  `fix_proposal.py acted <site> --page <address> --pr <same address> --new-title "<live title>"`.
- **"Can it just make the change every week without me?"** Not today: every change goes
  through a pull request the owner merges. That is the point of the tests.
