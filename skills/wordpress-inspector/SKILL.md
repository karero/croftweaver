---
name: wordpress-inspector
description: >
  Count what a live WordPress site holds before anyone promises to move it. Read-only, from
  the outside: no login, no backup. scripts/wp_inventory.py asks the site's public addresses
  (REST API, sitemap) and reports each content type with its number of records, where the
  sitemap disagrees, the page builder and forms it saw, and when the count is incomplete:
  the basis for an estimate. After the move, scripts/check_move.py asks the new site for
  every old address and lists each one that is missing or was sent to the home page. Stdlib
  Python. Trigger phrases: "how big is this WordPress site", "count the pages", "inventory
  the WordPress site", "WordPress migration estimate", "what plugins does this site use",
  "is the crawl complete", "did every page make the move", "check the redirects after the
  move", "are any old addresses broken".
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

## After the move: does every old address still lead somewhere?

Content is lost at this step more often than at any other: a page nobody rebuilt, a redirect
nobody wrote. `urls.csv` from the count is the list to check against.

```bash
python3 skills/wordpress-inspector/scripts/check_move.py ./inventory/urls.csv https://preview.example.com --out ./move-check
```

Give it the new site's deployed address, the preview or the live one. A preview server on
your own computer does not apply the host's redirect rules, so every redirect would read as
missing. Any list of old addresses works in place of `urls.csv`: a text file, one per line.

Read `move-check.md` with the owner. Each old address ends as one of:

- **kept**: the new site answers at the same address.
- **redirected**: the new site forwards it to another of its pages.
- **off the site**: forwarded to another host, such as a shop. Listed, not followed.
- **missing**: the new site says "not found". Build the page or write the redirect.
- **sent home**: a deep address forwarded to the home page. To a reader and to a search
  engine that page is gone, so it counts as a finding. Point it at the page that replaced it.
- **unreadable**: the new site refused or was busy. Run it again.

Some pages are dropped on purpose. Write those addresses into a text file, one per line, and
pass it with `--let-go let-go.txt`; they then read **let go**. Agree that list with the owner:
it is the record of what was given up.

The report also counts temporary redirects (302, 307). A moved page needs a permanent one
(301), or search engines keep the old address.

Exit code 0 means every address is accounted for, 1 that there are findings, 2 that the run
could not start. One reason for 2: the new site answers "found" for an address that cannot
exist. Give it a real "not found" page first, or nothing can be checked.

## What this skill does not do

It does not move anything. It counts before the move and checks after it, so that both
decisions rest on numbers.

## Tests

```bash
make test-wordpress-inventory
```

Stub sites on 127.0.0.1, no real requests.
