#!/usr/bin/env python3
"""
check_move.py — after a site has moved: does every listed old address still lead somewhere?

It takes a list of the old site's addresses (urls.csv from wp_inventory.py, or any text
file with one address per line) and asks the NEW site for each of them. The check is as
complete as that list: urls.csv holds the records and sitemap entries the count found, not
listing pages the sitemap left out. Every address must end in one of these:

  kept          the new site answers at the same address
  redirected    the new site forwards it to another of its pages, and that page answers
  off the site  the new site forwards it to another host (not followed, only listed)
  let go        the address is missing, and it is in your --let-go list: dropped on purpose

Anything else is a finding, and the run exits 1:

  missing       the new site says "not found"
  sent home     a deep address is forwarded to the home page: a reader who follows an old
                link to it lands on the front page and has to search again
  unreadable    the new site refused, was too busy, or forwards in a loop

Read-only: it only asks the new site for pages. Standard library only (Python 3.9+).

Usage:
  python3 check_move.py inventory/urls.csv https://new-site.example --out ./move-check
  python3 check_move.py old-addresses.txt https://preview.new-site.example --let-go let-go.txt

Exit codes: 0 every address is accounted for, 1 at least one finding, 2 the run could not
start (no address list, the new site does not answer, or asking it for an address that
cannot exist did not bring a plain "not found", so kept and missing cannot be told apart).

Notes:
  - Run it against a deployed address (the preview or the live site). A preview server on
    your own computer may not apply the host's redirect rules; where it does not, every
    redirect reads as missing.
  - "/a" and "/a/" are asked separately: a site can answer the two differently.
  - It does not consult robots.txt: the new site is your own, and a preview often keeps
    robots out on purpose. It still pauses between requests (--delay).
  - The old addresses' paths are asked on the new host. Addresses on a host other than the
    old site's (a shop, a policy page elsewhere) are listed and skipped.
"""

from __future__ import annotations

import argparse
import collections
import csv
import os
import secrets
import sys
import urllib.parse
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wp_inventory as wi  # noqa: E402  (one fetcher for both scripts)

USER_AGENT = "wordpress-inventory/0.1 (move check, read-only)"
FINDINGS = ("missing", "sent home", "unreadable")
ORDER = ("kept", "redirected", "off the site", "let go") + FINDINGS
TEMPORARY = (302, 303, 307)
CSV_FIELDS = ["old_address", "result", "status", "ends_at", "temporary_redirect", "note"]


def read_addresses(path: str) -> List[str]:
    """Addresses from urls.csv (its `url` column) or from a text file, one per line."""
    with open(path, encoding="utf-8-sig", newline="") as fh:
        head = fh.readline()
        fh.seek(0)
        if "url" in [c.strip().strip('"').lower() for c in head.split(",")]:
            reader = csv.DictReader(fh)
            col = next(c for c in reader.fieldnames if c.strip().lower() == "url")
            raw = [row.get(col) or "" for row in reader]
        else:
            raw = fh.read().splitlines()
    out = []
    for line in raw:
        line = line.strip().lstrip("'")  # wp_inventory puts an apostrophe before a cell a spreadsheet would run
        if line and not line.startswith("#"):
            out.append(line)
    return out


def _bare(host: str) -> str:
    host = (host or "").lower()
    return host[4:] if host.startswith("www.") else host


def ask_of(address: str, old_host: str) -> Optional[str]:
    """The path (and query) to ask the new site for, or None for an address on another host.
    A line without a host ("/about/") is a path on the old site."""
    p = urllib.parse.urlsplit(address if "://" in address else "//" + old_host + "/" + address.lstrip("/"))
    if _bare(p.hostname or "") != old_host:
        return None
    return urllib.parse.quote(p.path or "/", safe="/%:@!$&'()*+,;=~-._") + ("?" + p.query if p.query else "")


def key_of(ask: str) -> str:
    """The key a let-go line is matched by: "/a" and "/a/" name the same dropped page."""
    path, q, query = ask.partition("?")
    return (path.rstrip("/") or "/") + q + query


def split_old(addresses: List[str]) -> Tuple[str, List[Tuple[str, str]], List[str]]:
    """(the old site's host, [(old address, path to ask for)], addresses on other hosts).
    The old host is the one most addresses share."""
    hosts = collections.Counter(_bare(urllib.parse.urlsplit(a).hostname or "") for a in addresses if "://" in a)
    old_host = hosts.most_common(1)[0][0] if hosts else ""
    mine, elsewhere, seen = [], [], set()
    for a in addresses:
        ask = ask_of(a, old_host)
        if ask is None:
            elsewhere.append(a)
        elif ask not in seen:  # the same address twice is asked once; "/a" and "/a/" are two addresses
            seen.add(ask)
            mine.append((a, ask))
    return old_host, mine, elsewhere


def check(addresses_file: str, new_site: str, let_go_file: Optional[str], delay: float, timeout: float,
          max_requests: int) -> Tuple[Optional[dict], str]:
    """(result, "") or (None, why the run could not start)."""
    try:
        addresses = read_addresses(addresses_file)
        let_go_raw = read_addresses(let_go_file) if let_go_file else []
    except (OSError, UnicodeDecodeError, StopIteration, csv.Error) as e:
        return None, "cannot read the address list (%s)" % (e if str(e) else type(e).__name__)
    old_host, todo, elsewhere = split_old(addresses)
    if not todo:
        return None, "no addresses to check in %s" % addresses_file
    let_go = {key_of(a) for a in (ask_of(x, old_host) for x in let_go_raw) if a is not None}

    if not wi.web_address(new_site):
        return None, "not a web address: %s" % new_site
    p = urllib.parse.urlsplit(new_site)
    base = urllib.parse.urlunsplit((p.scheme, p.netloc, p.path.rstrip("/"), "", ""))
    fetcher = wi.Fetcher(base + "/", delay, timeout, max_requests, USER_AGENT)  # .robots stays None: see the notes above
    moved = []
    home = None
    for _ in range(3):  # example.com may forward to www.example.com
        home = fetcher.get(base + "/")
        if not home.redirect_to:
            break
        moved.append("%s forwards to %s" % (base + "/", home.redirect_to))
        t = urllib.parse.urlsplit(home.redirect_to)
        base = urllib.parse.urlunsplit((t.scheme, t.netloc, t.path.rstrip("/"), "", ""))
        fetcher.origin = wi.origin_of(base + "/")
    if home is None or home.problem():
        return None, "the new site's home page could not be read at %s/ (%s)" % (base, home.problem() if home else "no answer")
    host = fetcher.origin[1]
    root_key = wi.path_key(base + "/", host)      # the home address as asked
    home_keys = {root_key, wi.path_key(home.url, host)}  # ... and where it ends ("/en/", "/index.html")

    # Only a plain "not found" for an address that cannot exist lets kept and missing be told apart.
    probe = fetcher.get("%s/no-such-page-%s/" % (base, secrets.token_hex(8)))
    if not probe.problem():
        return None, ("the new site answers \"found\" for an address that cannot exist (%s), so kept and missing "
                      "cannot be told apart. Give it a real \"not found\" page first" % probe.url)
    if probe.status not in (404, 410):  # refused, busy, or forwarded to another host
        return None, ("asking the new site for an address that cannot exist brought no plain \"not found\" (%s), so kept "
                      "and missing cannot be told apart yet. Run it again" % probe.problem())

    rows = []
    for old, ask in todo:
        resp = fetcher.get(base + ask)
        asked_key = wi.path_key(base + ask, host)
        problem = resp.problem()
        ends_at, note = "", ""
        temp = [s for s in resp.via + ([resp.status] if resp.redirect_to else []) if s in TEMPORARY]
        if resp.redirect_to:
            result, ends_at = "off the site", resp.redirect_to
        elif not problem and not resp.via:
            result = "kept"
        elif not problem:
            ends_at = resp.url
            # the old home address may be forwarded wherever the home page lives; a deep address may not
            if wi.path_key(resp.url, host) in home_keys and asked_key != root_key:
                result = "sent home"
            else:
                result = "redirected"
        elif resp.status in (404, 410):
            result = "let go" if key_of(ask) in let_go else "missing"
            if resp.via:
                note = "forwards to %s, which is not found" % resp.url
        else:
            result, note = "unreadable", problem
        rows.append({"old_address": old, "result": result, "status": resp.status or "", "ends_at": ends_at,
                     "temporary_redirect": temp[0] if temp else "", "note": note})
    counts = collections.Counter(r["result"] for r in rows)
    return {
        "new_site": base + "/", "old_host": old_host, "moved": moved, "checked": len(rows), "rows": rows,
        "counts": {k: counts.get(k, 0) for k in ORDER}, "elsewhere": elsewhere,
        "temporary": sum(1 for r in rows if r["temporary_redirect"]),
        "findings": sum(counts.get(k, 0) for k in FINDINGS), "requests": fetcher.count, "cap_hit": fetcher.cap_hit,
    }, ""


def render(d: dict, list_limit: int = 200) -> str:
    md = wi.md
    L: List[str] = []
    add = L.append
    add("# Move check: %s" % md(d["new_site"]))
    add("")
    add("%s addresses of %s asked on %s, in %s requests." % (d["checked"], md(d["old_host"]) or "the old site", md(d["new_site"]), d["requests"]))
    for m in d["moved"]:
        add("Note: %s." % md(m, 300))
    add("")
    if d["findings"]:
        add("**%s not accounted for.** Each needs a page, a redirect, or a line in the let-go list."
            % ("1 address is" if d["findings"] == 1 else "%s addresses are" % d["findings"]))
    else:
        add("**Every address is accounted for.**")
    if d["cap_hit"]:
        add("")
        add("The request limit was reached, so some addresses read \"unreadable\": raise --max-requests.")
    add("")
    add("| Result | Addresses |")
    add("|---|---|")
    L.extend("| %s | %s |" % (k, d["counts"][k]) for k in ORDER)
    if d["temporary"]:
        add("")
        add("%s temporary (302, 303 or 307); move-check.csv says which. If the move is for good, make "
            "%s permanent (301 or 308)." % (("1 redirect is", "it") if d["temporary"] == 1
                                           else ("%s redirects are" % d["temporary"], "them")))
    for kind, title in (("missing", "Missing"), ("sent home", "Sent to the home page"), ("unreadable", "Unreadable")):
        hit = [r for r in d["rows"] if r["result"] == kind]
        if hit:
            add("")
            add("## %s (%s)" % (title, len(hit)))
            add("")
            L.extend("- %s%s" % (md(r["old_address"], 300), " — " + md(r["note"], 200) if r["note"] else "") for r in hit[:list_limit])
            if len(hit) > list_limit:
                add("- … and %s more, all in move-check.csv" % (len(hit) - list_limit))
    off = [r for r in d["rows"] if r["result"] == "off the site"]
    if off:
        add("")
        add("## Forwarded to another host (%s)" % len(off))
        add("")
        add("Not followed. Check that each target is the one you mean.")
        add("")
        L.extend("- %s → %s" % (md(r["old_address"], 300), md(r["ends_at"], 300)) for r in off[:list_limit])
        if len(off) > list_limit:
            add("- … and %s more, all in move-check.csv" % (len(off) - list_limit))
    if d["elsewhere"]:
        add("")
        add("## On another host, not checked (%s)" % len(d["elsewhere"]))
        add("")
        L.extend("- %s" % md(a, 300) for a in d["elsewhere"][:list_limit])
    return "\n".join(L) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="After a move: does every old address still lead somewhere on the new site?")
    ap.add_argument("addresses", help="urls.csv from wp_inventory.py, or a text file with one old address per line")
    ap.add_argument("new_site", help="the new site's deployed address, e.g. https://preview.example.com")
    ap.add_argument("--out", default="move-check", help="folder for move-check.md and move-check.csv")
    ap.add_argument("--let-go", help="text file: one address per line that was dropped on purpose")
    ap.add_argument("--delay", type=float, default=0.2, help="seconds between requests (default 0.2)")
    ap.add_argument("--timeout", type=float, default=30.0, help="seconds to wait for one answer (default 30)")
    ap.add_argument("--max-requests", type=int, default=5000, help="stop after this many requests (default 5000)")
    args = ap.parse_args(argv)
    data, stop = check(args.addresses, args.new_site, args.let_go, max(args.delay, 0.0), args.timeout, max(args.max_requests, 3))
    if data is None:
        print("check_move: %s" % stop, file=sys.stderr)
        return 2
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "move-check.md"), "w", encoding="utf-8") as fh:
        fh.write(render(data))
    with open(os.path.join(args.out, "move-check.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        w.writeheader()
        for row in data["rows"]:
            w.writerow({k: wi.safe_cell(row[k]) for k in CSV_FIELDS})
    for k in ORDER:
        print("%-14s %s" % (k, data["counts"][k]))
    print("%s: %s" % ("FINDINGS" if data["findings"] else "all accounted for", os.path.join(args.out, "move-check.md")))
    return 1 if data["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
