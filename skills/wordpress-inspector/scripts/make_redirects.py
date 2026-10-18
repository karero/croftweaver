#!/usr/bin/env python3
"""
make_redirects.py — between the count and the check: write the new site's redirects.

It turns the old site's address list (urls.csv from wp_inventory.py, or a text file with one
address per line) and the owner's decisions into lines for the new site's public/_redirects,
in Cloudflare's format, each with 301. check_move.py --moves then checks, after the move, that
each old address ends where the decisions say.

Two steps:

  1. --draft moves.csv writes the decisions sheet: one row per old page, new_address empty.
  2. Fill in new_address for each row, then run it with the sheet to write the redirects.

What new_address may hold (spaces around it do not count; the two words in any case):

  /kontakt                     moved to that page of the new site
  https://the-new-site/x       the same, written in full (on the old host or --site)
  https://shop.example/        moved to another host
  keep                         same page, same address (also: the same path, give or take
                               the closing slash)
  let go                       dropped on purpose; check_move --moves reads it as let go
  (empty)                      not decided yet

Why the lines look as they do (Cloudflare matches the slash, the letter case and every
%-escape exactly, measured on two live kit sites in October 2026):

  - each moved page gets a line for "/old" and one for "/old/";
  - a path with an escape such as %c3%bc gets each spelling the list holds, plus the escapes
    all in upper and all in lower case, since a link and a typed address may differ;
  - no line goes from a page to itself: the host already sends "/page/" to "/page", and a
    line the other way would loop with it;
  - a deep page sent to the home page is refused, as check_move.py would report it;
  - chains are followed (/a -> /b -> /c writes /a -> /c) and loops stop the run;
  - an address with a query (/?p=12) cannot be matched by _redirects: it is listed, not
    dropped. Let it go, or handle it some other way.

Run it in the inventory's folder, never inside the site's repository: the sheet and the list
name another party's addresses. Only the _redirects file goes to the site.

Standard library only (Python 3.9+). It makes no requests.

Usage:
  python3 make_redirects.py urls.csv --draft moves.csv
  python3 make_redirects.py urls.csv moves.csv --site https://new-site.example --out ../site/public/_redirects

Exit codes: 0 written, every listed address decided (with --draft: the sheet written);
1 written, with findings (not decided, not understood, not in the address list, cannot be
written, sent home, or a chain into such a page); 2 nothing written (a usage error, an input
that cannot be read, no addresses, an output that exists without --replace or was not written
by this script, a missing output folder, one page with two different decisions, a loop, or more
than 2,000 lines).
"""

from __future__ import annotations

import argparse
import collections
import csv
import os
import sys
import urllib.parse
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check_move as cm  # noqa: E402  (one reader and one idea of "the same page" for both scripts)
import wp_inventory as wi  # noqa: E402

HEADER = "# Written by make_redirects.py (wordpress-inspector) from moves.csv."
HEADER_REST = "# Change moves.csv and run it again: edits made here are lost."
# Cloudflare's limits, from https://developers.cloudflare.com/pages/configuration/redirects/ (and the
# same on Workers static assets): 2,000 static redirects in a _redirects file, which a site has one
# of, and 1,000 characters per line.
MAX_LINES = 2000
MAX_LINE = 1000
OLD_HOME = {"/"} | {"/" + f for f in cm.HOME_FILES}
FINDING_KINDS = ("not decided", "not understood", "not in the address list", "cannot be written", "sent home",
                 "chain")
LIST_LIMIT = 200


def read_list(path: str) -> Tuple[List[str], Dict[str, str]]:
    """(the addresses, {address: its type from urls.csv}). A plain text list has no types."""
    addresses = cm.read_addresses(path)
    types: Dict[str, str] = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        head = fh.readline()
        fh.seek(0)
        if "url" in [c.strip().strip('"').lower() for c in head.split(",")]:
            for row in csv.DictReader(fh):
                row = {(k or "").strip().lower(): v for k, v in row.items()}
                url = cm.cell(row.get("url"))
                if url and not types.get(url):
                    types[url] = cm.cell(row.get("type"))
    return addresses, types


def pages_of(addresses: List[str]) -> Tuple[str, "collections.OrderedDict[str, List[Tuple[str, str]]]", List[str]]:
    """(old host, {page: [(address as listed, ask)]} in list order, addresses on other hosts)."""
    old_host, mine, elsewhere = cm.split_old(addresses)
    pages: "collections.OrderedDict[str, List[Tuple[str, str]]]" = collections.OrderedDict()
    for old, ask in mine:
        pages.setdefault(cm.page_form(ask), []).append((old, ask))
    return old_host, pages, elsewhere


def draft(list_file: str, out: str) -> int:
    if os.path.exists(out):
        print("make_redirects: %s exists; it is never overwritten. Fill it in, or give another name" % out, file=sys.stderr)
        return 2
    folder = os.path.dirname(os.path.abspath(out))
    if not os.path.isdir(folder):
        print("make_redirects: no folder %s" % folder, file=sys.stderr)
        return 2
    try:
        addresses, types = read_list(list_file)
    except (OSError, UnicodeDecodeError, StopIteration, csv.Error) as e:
        print("make_redirects: cannot read the address list (%s)" % (e if str(e) else type(e).__name__), file=sys.stderr)
        return 2
    try:
        _, pages, elsewhere = pages_of(addresses)
    except ValueError as e:
        print("make_redirects: an address in %s cannot be read (%s)" % (list_file, e), file=sys.stderr)
        return 2
    if not pages:
        print("make_redirects: no addresses in %s" % list_file, file=sys.stderr)
        return 2
    try:
        with open(out, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["old_address", "new_address", "type"])
            for spellings in pages.values():
                kind = next((types.get(old, "") for old, _ in spellings if types.get(old)), "")
                w.writerow([wi.safe_cell(spellings[0][0]), "", wi.safe_cell(kind)])
    except OSError as e:
        print("make_redirects: cannot write %s (%s)" % (out, e.strerror or type(e).__name__), file=sys.stderr)
        return 2
    print("%s pages in %s: fill in new_address for each" % (len(pages), out))
    for a in elsewhere[:LIST_LIMIT]:
        print("left out, on another host: %s" % a)
    return 0


def sources(spellings: List[Tuple[str, str]]) -> List[str]:
    """Every source line one page needs: each listed spelling, plus its escapes all upper and all
    lower case, each with and without the closing slash."""
    out: List[str] = []
    for _, ask in spellings:
        for form in (ask, cm.upper_escapes(ask), cm.lower_escapes(ask)):
            base = form.rstrip("/") or "/"
            for s in ((base,) if base == "/" else (base, base + "/")):
                if s not in out:
                    out.append(s)
    return out


def plan(pages, rows, old_host: str, site_host: str):
    """(lines, counts, findings, notes, stop). stop is why nothing may be written, or ""."""
    findings: Dict[str, List[str]] = collections.defaultdict(list)
    try:
        decisions, first, unlisted = cm.gather(rows, old_host, site_host, set(pages))
    except ValueError as e:
        return [], {}, findings, [], str(e)
    findings["not in the address list"].extend(unlisted)
    for page, d in decisions.items():
        if d.kind == "not understood":
            line, old, new = first[page]
            findings["not understood"].append("%s (row %s): %r — %s" % (old, line, new, d.note))
    for page in pages:
        decisions.setdefault(page, cm.Decision("not decided"))
        if decisions[page].kind == "not decided":
            findings["not decided"].append(pages[page][0][0])
    for page, spellings in pages.items():  # a source _redirects cannot hold is a finding of its own
        if decisions[page].kind in ("move", "off") and ("?" in page or "*" in page or ":" in page):
            decisions[page] = cm.Decision("cannot be written")
            findings["cannot be written"].append("%s: _redirects cannot match a query, and * and : have a meaning there"
                                                 % spellings[0][0])
    final = cm.resolve(decisions)
    loops = sorted({d.note for d in final.values() if d.kind == "loop"})
    if loops:
        return [], {}, findings, [], "a loop: %s" % "; ".join(loops)

    lines: List[str] = []
    notes: List[str] = []
    counts = collections.Counter()
    for page, spellings in pages.items():
        d, old = final[page], spellings[0][0]
        if d.kind in ("keep", "let go"):
            counts["kept" if d.kind == "keep" else "let go"] += 1
            continue
        if d.kind == "chain":
            findings["chain"].append("%s %s" % (old, d.note))
            continue
        if d.kind not in ("move", "off"):
            continue                                      # already a finding above
        if d.kind == "move" and cm.page_form(d.target) == "/" and page not in OLD_HOME:
            findings["sent home"].append("%s: %s" % (old, cm.SENT_HOME_REASON))
            continue
        target_path = d.target.split("?")[0]
        if d.kind == "move" and "?" in d.target and cm.page_form(target_path) == page:
            findings["cannot be written"].append("%s: %s would send it to itself, since _redirects does not read the query"
                                                 % (old, d.target))
            continue
        own = [s for s in sources(spellings) if d.kind == "off" or (s.rstrip("/") or "/") != (target_path.rstrip("/") or "/")]
        page_lines = ["%s %s 301" % (s, d.target) for s in own]
        long = [ln for ln in page_lines if len(ln) > MAX_LINE]
        if long:
            findings["cannot be written"].append("%s: a line would be %s characters; Cloudflare reads %s"
                                                 % (old, len(long[0]), MAX_LINE))
            continue
        lines.extend(page_lines)
        if d.kind == "off":
            counts["off the site"] += 1
        elif cm.page_form(d.target) == page:
            counts["kept"] += 1
        else:
            counts["moved"] += 1
        if page_lines and d.kind == "move" and target_path.endswith("/") and target_path != "/":
            notes.append("%s ends in /: a Croftweaver site serves its pages without it, so each visit takes a second hop"
                         % d.target)
    if len(lines) > MAX_LINES:
        return [], {}, findings, [], ("%s lines, and Cloudflare reads %s per file: nothing written"
                                      % ("{:,}".format(len(lines)), "{:,}".format(MAX_LINES)))
    return lines, counts, findings, sorted(set(notes)), ""


def write(list_file: str, moves_file: str, site: str, out: str, replace: bool) -> int:
    def stop(why: str) -> int:
        print("make_redirects: %s" % why, file=sys.stderr)
        return 2
    if not wi.web_address(site):
        return stop("--site is not a web address: %s" % site)
    folder = os.path.dirname(os.path.abspath(out))
    if not os.path.isdir(folder):
        return stop("no folder %s; nothing is created" % folder)
    if os.path.exists(out):
        if not replace:
            return stop("%s exists; pass --replace to write over it" % out)
        try:
            with open(out, encoding="utf-8", errors="replace") as fh:
                ours = fh.readline().rstrip("\r\n") == HEADER
        except OSError as e:
            return stop("cannot read %s (%s)" % (out, e.strerror))
        if not ours:
            return stop("%s was not written by this script: merge its lines into moves.csv and the address list, "
                        "or move it away" % out)
    try:
        addresses = cm.read_addresses(list_file)
    except (OSError, UnicodeDecodeError, StopIteration, csv.Error) as e:
        return stop("cannot read the address list (%s)" % (e if str(e) else type(e).__name__))
    try:
        rows = cm.read_moves(moves_file)
    except ValueError as e:
        return stop(str(e))
    try:
        old_host, pages, elsewhere = pages_of(addresses)
    except ValueError as e:
        return stop("an address in %s cannot be read (%s)" % (list_file, e))
    if not pages:
        return stop("no addresses in %s" % list_file)
    lines, counts, findings, notes, why = plan(pages, rows, old_host, urllib.parse.urlsplit(site).hostname or "")
    if why:
        return stop(why)
    try:
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("%s\n%s\n" % (HEADER, HEADER_REST))
            fh.writelines(ln + "\n" for ln in lines)
    except OSError as e:
        return stop("cannot write %s (%s)" % (out, e.strerror or type(e).__name__))
    for k in ("kept", "moved", "off the site", "let go"):
        print("%-24s %s" % (k, counts.get(k, 0)))
    for k in FINDING_KINDS:
        print("%-24s %s" % (k, len(findings.get(k, []))))
    print("%s lines written to %s" % (len(lines), out))
    for k in FINDING_KINDS:
        hit = findings.get(k, [])
        for f in hit[:LIST_LIMIT]:
            print("%s: %s" % (k, f))
        if len(hit) > LIST_LIMIT:
            print("%s: … and %s more" % (k, len(hit) - LIST_LIMIT))
    for n in notes:
        print("note: %s" % n)
    for a in elsewhere[:LIST_LIMIT]:
        print("left out, on another host: %s" % a)
    return 1 if any(findings.values()) else 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Write public/_redirects for a moved WordPress site from urls.csv and moves.csv.")
    ap.add_argument("addresses", help="urls.csv from wp_inventory.py, or a text file with one old address per line")
    ap.add_argument("moves", nargs="?", help="moves.csv, the filled-in decisions sheet")
    ap.add_argument("--draft", metavar="FILE", help="write the decisions sheet to fill in (never overwrites)")
    ap.add_argument("--site", help="the new site's live address, e.g. https://example.com (required to write)")
    ap.add_argument("--out", help="the _redirects file to write, e.g. ../site/public/_redirects (required to write)")
    ap.add_argument("--replace", action="store_true", help="write over a _redirects this script wrote before")
    args = ap.parse_args(argv)
    if args.draft:
        if args.moves or args.out or args.replace or args.site:
            ap.print_usage(sys.stderr)
            print("make_redirects: --draft takes only the address list", file=sys.stderr)
            return 2
        return draft(args.addresses, args.draft)
    if not args.moves or not args.out or not args.site:
        ap.print_usage(sys.stderr)
        print("make_redirects: give --draft FILE, or moves.csv with --site and --out", file=sys.stderr)
        return 2
    return write(args.addresses, args.moves, args.site, args.out, args.replace)


if __name__ == "__main__":
    sys.exit(main())
