---
name: wordpress-inspector
description: >
  Count what a live WordPress site holds before anyone promises to move it. Read-only,
  from the outside: no login, no backup. scripts/wp_inventory.py asks the site's public
  addresses (REST API, sitemap) and reports each content type the API lists (WordPress's
  internal ones left out) with its number of records, where the sitemap disagrees, signs
  of a page builder and forms, and when the count is incomplete: the basis for an
  estimate. After the move, scripts/check_move.py asks the new site for each listed
  address and names those missing or sent to the home page. Stdlib Python. Trigger
  phrases: "how big is this WordPress site", "count the pages", "inventory the WordPress
  site", "WordPress migration estimate", "what plugins does this site use", "is the crawl
  complete", "did every page make the move", "check the redirects after the move", "are
  any old addresses broken".
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

It pauses one second between requests and stops after 100, which covers a site of a few
thousand records. If the report says the request limit was reached, run it again with a
higher `--max-requests`. It obeys the site's robots.txt, wildcards included, and asks only
the host you name. A robots.txt that is refused or cannot be read stops the run.

It writes three files into the folder:

- `inventory.md`: the report. Read this first.
- `urls.csv`: one row per address, for a spreadsheet.
- `inventory.json`: the same numbers for a program.

Keep that folder out of any public repository: it lists another party's addresses.

## Read the result with the owner

1. **Is the count complete?** The report's first lines say so. If not, it names each gap.
   Clear the gaps before you estimate. Exit code 0 means complete, 1 incomplete, 2 the run
   could not start. Two kinds of gap name a sitemap address:
   - marked "a usual address, only tried": the script guessed it, because robots.txt names
     no sitemap. If the note says the file was "sent as text/html", open the address in a
     browser: an ordinary web page there means the site keeps no sitemap at that address,
     and this gap is settled. Any other note about such an address (the site refused or
     was busy, the file could not be unpacked, or it was sent as something else) a browser
     does not settle: run the count again later.
   - not marked so: robots.txt or a sitemap index names that file, so the site says a
     sitemap is there and the count lacks its addresses. A web page in its place is an
     error on the site. Have it repaired, or count those pages another way.
2. **Content types.** The count covers the types the site's REST API lists, apart from
   WordPress's own internal ones (menus, templates, patterns, styles, fonts); media is one
   number. Posts and pages are WordPress's own. Any other type comes from a plugin (events,
   speakers, products, jobs): ask who keeps it up to date, and how often it changes, before
   you price it.
3. **"Left as raw shortcode text".** The text the site hands out for such a record holds a
   code such as `[vc_row]` or `[gallery ids="1,2"]` where content should be: a page builder,
   a gallery or another plugin wrote it. This is a sign, not proof. Open two or three of
   these pages in a browser and compare them with their rows in `urls.csv`; where the page
   shows what the text lacks, plan to rebuild it by hand.
4. **Forms and page-builder marks.** These are found by the traces each plugin leaves in the
   text, so a form drawn another way is not counted. Walk the site's menus once to check.
   Each form needs a new home on the new site: ask where its entries should go.
5. **Sitemap addresses no record explains.** A plugin or a listing page stands behind each
   group. Decide for each: keep, redirect, or let go.
6. **Published but not in the sitemap.** Often hidden on purpose. Ask before moving them.

## What it cannot see

Say this to the owner before they rely on the numbers:

- Drafts, private records and anything behind a login. A password-protected record may be
  counted, but its text is not read.
- A content type the site's REST API does not list.
- Content a plugin draws inside a page, such as a directory shown in pop-ups. It counts as
  one page.
- Fields a plugin keeps to itself, such as an event's start time.
- The media files themselves, redirects set inside WordPress, and form entries.

Those need the site's backup or a login. The language of each record is a guess, for German
and English only; treat it as a hint.

## After the move: does every old address still lead somewhere?

This is the step where a page nobody rebuilt, or a redirect nobody wrote, goes unnoticed.
`urls.csv` from the count is the list to check against. It holds the records and sitemap
entries the count found; a listing page the sitemap left out is not in it, so add such
addresses to the file by hand if they matter.

```bash
python3 skills/wordpress-inspector/scripts/check_move.py ./inventory/urls.csv https://preview.example.com --out ./move-check
```

Give it the new site's deployed address, the preview or the live one. A preview server on
your own computer may not apply the host's redirect rules; where it does not, every redirect
reads as missing. Any list of old addresses works in place of `urls.csv`: a text file, one
per line. `/a` and `/a/` are asked separately, since a site can answer the two differently.

Read `move-check.md` with the owner. Each old address ends as one of:

- **kept**: the new site answers at the same address.
- **redirected**: the new site forwards it to another of its pages.
- **off the site**: forwarded to another host, such as a shop. Not followed; the report
  lists each with its target, for you to check.
- **missing**: the new site says "not found". Build the page or write the redirect.
- **sent home**: a deep address forwarded to the home page. A reader who follows an old link
  to it lands on the front page and has to search again, so it counts as a finding. Point
  it at the page that replaced it. The old home address itself (`/`, `/index.php`,
  `/index.html` or `/index.htm`) may go wherever the new home page lives.
- **unreadable**: the new site refused or was busy. Run it again.

Some pages are dropped on purpose. Write those addresses into a text file, one per line, and
pass it with `--let-go let-go.txt`; they then read **let go**. Agree that list with the owner:
it is the record of what was given up.

The report also counts temporary redirects (302, 303, 307), and `move-check.csv` says which.
If the move is for good, make them permanent (301 or 308).

Exit code 0 means every address is accounted for, 1 that there are findings, 2 that the run
could not start. One reason for 2: asked for an address that cannot exist, the new site
did not answer with a plain "not found". Give it a real "not found" page first, or nothing
can be checked.

## What this skill does not do

It does not move anything. It counts before the move and checks after it, so that both
decisions rest on numbers.

## Tests

```bash
make test-wordpress-inventory
```

Stub sites on 127.0.0.1, no real requests.
