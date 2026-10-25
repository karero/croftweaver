# Launch check: [Site name]

<!-- The structure of every launch-check report. Write the report in the owner's language
(headings too), fill each section, drop a section that has nothing in it, and keep the order.
The file is docs/launch/launch-check-<YYYY-MM-DD>-<baseline|prelaunch|live>.md. -->

**Date:** [YYYY-MM-DD] · **Run:** [baseline | pre-launch | live] · **Settings:** `docs/launch/config.json` ([business in Germany: yes/no], [site languages], [story layer: yes/no], [replaces: the old site's address, or none])

**Verdict:** [🟢 Ready to launch | 🟡 Ready with the items below | 🔴 Not ready | Baseline, not a launch verdict]

[One or two sentences: why this verdict.]

## 🔴 Before launch

- [ ] [What is wrong, where (file or page), and what fixes it.]

## 🟡 Soon after launch

- [ ] [Item.]

## 🟢 Later

- [ ] [Item.]

## Left to the site's tests, as they stand in this site, for the pages in `PAGES`

`npm run build` and `npx playwright test` on [YYYY-MM-DD]: [N passed, N failed, N skipped]. These tests
are the site's own: they are read as they stand in this site, edits included.

| Category | Test | Pages it passed on |
|---|---|---|
| Alt text on images | `images — <page> uses optimised, dimensioned, described images` | [/, /privacy, …] |
| One H1, title and description length | `seo — head contract on <page>` | [/, /privacy, …] |

Pages the check looked at itself for these categories, and why: [a page not in `PAGES`; a
test skipped, filtered out or missing].

## Checked by the launch check

| Area | Result | Finding |
|---|---|---|
| Imprint / privacy / consent | [✅ / ⚠️ / ❌ / not checked] | [one line] |
| Titles and descriptions unique across pages | | |
| The starter's example values, `llms.txt` slots, the 404 page's text | | |
| [Story layer / blog / testimonials / contact form, as the settings say] | | |
| Console errors on the local preview | | |

## E-E-A-T and local signals (an assessment, not a measurement)

| | Rating | Why |
|---|---|---|
| Experience | [★★★★☆] | [one line] |
| Expertise | | |
| Authority | not checked: no outside data | [backlinks, press, awards: none given] |
| Trust | | |
| Local | | |
| **Overall** | **[3.8 / 5, over Experience, Expertise, Trust, Local]** | [one line] |

## Not checked yet

- [What only a deployed site shows: HTTPS, the 404 status, errors from the `_headers`
  rules. Checked at the live re-check (step 12a).]

## Skipped by the settings

- [Story layer checks (no story layer).]
