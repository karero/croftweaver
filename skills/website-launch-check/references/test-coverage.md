# What the site's tests already check

The launch check runs the site's tests first and does not check again by eye what they check.
This file is the one place that says which test covers which category, written against the
starter's specs in `new-website/templates/astro/tests/`, by what each test asserts, not by its
name.

## The rule

1. Run, in the site's folder: `npm run build`, then `npm test 2>&1 | tee <scratch file>`. The
   starter's Playwright config uses the `list` reporter: one line per test, with its title and
   `✓` (passed), `✘` (failed) or `-` (skipped).
2. A category below counts as **left to the site's tests on a page** only when the output shows
   that page's test, by the title below, as passed. A page whose test was skipped, filtered out
   (a narrowed test command, a `grep` in the config), failed or is missing is the check's, for
   that category, on that page.
3. The tests read only the pages in `PAGES` (`tests/_helpers.ts`). List every built page
   (`dist/**/*.html`, as a path: `dist/about/index.html` is `/about`) that `PAGES` lacks, and
   check those pages yourself. `seo.spec.ts`'s sitemap test already fails for a sitemap page
   missing from `PAGES`, so these are mostly noindex pages and the 404 page.
4. The site's tests are its contract **as they stand in this site**, edits included (a German
   site edits `seo.spec.ts` at the scaffold). An older or edited test may assert less than the
   starter's; the report says so in those words, and does not compare versions.
5. If the site has no such spec file at all, the check does the category and says why.

## The mapping

| Category | Spec | Test title (one per page in `PAGES`) | What it asserts |
|---|---|---|---|
| Images: alt text present, width and height set, modern formats | `images.spec.ts` | `images — <page> uses optimised, dimensioned, described images` | every `<img>` has an `alt` attribute (an empty one is allowed, for a decorative image), `width` and `height`, a `loading` choice and no stretched ratio, and no JPEG/PNG/GIF is served where WebP/AVIF is expected. Not whether the alt text describes the image: that stays a read by eye |
| Exactly one H1 | `seo.spec.ts` | `seo — head contract on <page>` | `h1` count is 1 |
| Title and description length | `seo.spec.ts` | `seo — head contract on <page>` | title not empty and at most 60 characters; description 120 to 160 characters |

Not covered by any test, so always the check's: titles or descriptions shared by two pages,
whether a title or description says what the page is, the starter's example values (the name
`Example`, `hello@example.com`), `public/llms.txt`'s own `[bracket]` slots, the 404 page's
text, and everything under "What the launch check checks" in `SKILL.md`.

## Warnings in the output

The suite passes with some warnings. Read every line that starts with `⚠`:

- `⚠ placeholders:` is a **blocker**, whichever kind: a page still listed in
  `UNFILLED_UNTIL_LAUNCH` ("… is not ready to launch"), or a `[MISSING: …]` content placeholder
  (only a warning outside CI). Quote the line in the report.
- `⚠ positioning coverage:` is a 🟡 finding: a page has no positioning entry.
- A skipped test (`-` in the list, or the summary's "skipped" count) is a finding, and its
  page's categories above are the check's.

## Keeping this file right

When a spec in `new-website/templates/astro/tests/` changes what it asserts, or a test's
title, change this table in the same pull request.
