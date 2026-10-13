---
name: wordpress-inspector
description: >
  Count what a live WordPress site holds before anyone promises to move it. Read-only, from
  the outside: no login, no backup, no plugin. scripts/wp_inventory.py asks the site's own
  public addresses (REST API, sitemap, robots.txt, home page) and reports every content type
  with its number of published records, the sitemap's addresses, where the two disagree, the
  page builder and forms it saw, and what it could not see. It says plainly when a count is
  incomplete. The first step of a move to a new site, and the basis for an estimate. Stdlib
  Python. Trigger phrases: "how big is this WordPress site", "count the pages", "inventory
  the WordPress site", "what would it take to move this site", "WordPress migration
  estimate", "what plugins does this site use", "is the crawl complete".
---

# WordPress inspector: count the site before you promise to move it

A move goes wrong at the start, when someone guesses the size of the site. A crawler's copy
looks complete and is not: it misses whatever no page links to and saves error pages under
real page names. This skill asks the site itself, which knows how many records it has.

It reads; it never writes to the site, logs in, or copies its text.

## When to use it

- Before quoting or planning a move from WordPress to a new site.
- To check a crawler's copy against the truth.
- To learn what a site is built with: page builder, forms, plugins that keep their own data.

Run it only on a site you own or are asked to look at.

## Run it

```bash
python3 skills/wordpress-inspector/scripts/wp_inventory.py https://example.com --out ./inventory
```

It pauses one second between requests and stops after 100. A site with thousands of posts
needs more: add `--max-requests 300`. It obeys the site's robots.txt and asks only the host
you name.

It writes three files into the folder:

- `inventory.md`: the report. Read this first.
- `urls.csv`: one row per address, for a spreadsheet.
- `inventory.json`: the same numbers for a program.

Keep that folder out of any public repository: it lists another party's addresses.

## Read the result with the owner

1. **Is the count complete?** The report's first lines say so. If not, it names each gap.
   Clear the gaps before you estimate. Exit code 0 means complete, 1 incomplete, 2 the run
   could not start.
2. **Content types.** Posts and pages are WordPress's own. Any other type comes from a plugin
   (events, speakers, products, jobs) and is usually the costly part of a move: ask who keeps
   it up to date, and how often it changes.
3. **"Left as raw shortcode text".** A record counted here was built with a page builder, and
   its text holds codes such as `[vc_row]` where content should be. It cannot be converted
   as it is. Plan to rebuild those pages by hand.
4. **Forms.** Each form needs a new home on the new site. List them and ask where the entries
   should go.
5. **Sitemap addresses no record explains.** A plugin or a listing page stands behind each
   group. Decide for each: keep, redirect, or let go.
6. **Published but not in the sitemap.** Often hidden on purpose. Ask before moving them.

## What it cannot see

Say this to the owner before they rely on the numbers:

- Drafts, private and password-protected records, and anything behind a login.
- Content a plugin draws inside a page, such as a directory shown in pop-ups. It counts as
  one page.
- Fields a plugin keeps to itself, such as an event's start time.
- The media files themselves, redirects set inside WordPress, and form entries.

Those need the site's backup or a login. The language of each record is a guess, for German
and English only; treat it as a hint.

## What this skill does not do

It does not move anything. It counts, so that the next decision rests on numbers.

## Tests

```bash
make test-wordpress-inventory
```

Stub sites on 127.0.0.1, no real requests.
