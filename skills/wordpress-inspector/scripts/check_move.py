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
  let go        the address is missing, and it is in your --let-go list (or let go in
                --moves): dropped on purpose

Anything else is a finding, and the run exits 1:

  missing       the new site says "not found"
  sent home     a deep address is forwarded to the home page: a reader who follows an old
                link to it lands on the front page and has to search again
  unreadable    the new site refused, was too busy, or forwards in a loop
  not as decided  (with --moves) the address answers, but not where moves.csv sends it

Read-only: it only asks the new site for pages. Standard library only (Python 3.9+).

Usage:
  python3 check_move.py inventory/urls.csv https://new-site.example --out ./move-check
  python3 check_move.py old-addresses.txt https://preview.new-site.example --let-go let-go.txt
  python3 check_move.py urls.csv https://preview.new-site.example --moves moves.csv --site https://new-site.example

Exit codes: 0 every address is accounted for, 1 at least one finding, 2 the run could not
start (no address list, the new site does not answer, or asking it for an address that
cannot exist did not bring a plain "not found", so kept and missing cannot be told apart;
or moves.csv cannot be read).

Notes:
  - Run it against a deployed address (the preview or the live site). A preview server on
    your own computer may not apply the host's redirect rules; where it does not, every
    redirect reads as missing.
  - "/a" and "/a/" are asked separately: a site can answer the two differently.
  - It does not consult robots.txt: the new site is your own, and a preview often keeps
    robots out on purpose. It still pauses between requests (--delay).
  - The old addresses' paths are asked on the new host. Addresses on a host other than the
    old site's (a shop, a policy page elsewhere) are listed and skipped.
  - --moves takes the decisions sheet make_redirects.py reads (old_address,new_address). A
    decision may name the live site's full address; when the check runs on a preview, pass
    the live address as --site, or such a row reads "not as decided".
"""

from __future__ import annotations

import argparse
import collections
import csv
import io
import os
import re
import secrets
import sys
import urllib.parse
from typing import Dict, List, NamedTuple, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wp_inventory as wi  # noqa: E402  (one fetcher for both scripts)

USER_AGENT = "wordpress-inventory/0.1 (move check, read-only)"
FINDINGS = ("missing", "sent home", "unreadable", "not as decided")
ORDER = ("kept", "redirected", "off the site", "let go") + FINDINGS[:3]  # + "not as decided" with --moves
TEMPORARY = (302, 303, 307)
HOME_FILES = ("index.html", "index.htm", "index.php")  # "/index.php" is the old home page under another name
CSV_FIELDS = ["old_address", "result", "status", "ends_at", "temporary_redirect", "note"]
SAFE_PATH = "/%:@!$&'()*+,;=~-._"  # what ask_of leaves unescaped in a path: existing escapes stay as they are
SENT_HOME_REASON = ("a reader who follows an old link to it lands on the front page and has to search again: "
                    "point it at the page that replaced it, or let it go")
_ESCAPE = re.compile(r"%[0-9A-Fa-f]{2}")


def cell(value) -> str:
    """A cell as the sheet means it: trimmed, without the apostrophe wp_inventory puts before a
    cell a spreadsheet would run."""
    return (value or "").strip().lstrip("'")


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
        line = cell(line)
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
    return urllib.parse.quote(p.path or "/", safe=SAFE_PATH) + ("?" + p.query if p.query else "")


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


def upper_escapes(text: str) -> str:
    return _ESCAPE.sub(lambda m: m.group(0).upper(), text)


def lower_escapes(text: str) -> str:
    return _ESCAPE.sub(lambda m: m.group(0).lower(), text)


def page_form(ask: str) -> str:
    """The one form every "is this the same page?" question uses, in make_redirects.py too: the
    path as ask_of gives it, each escape's hex digits uppercased, the closing slash dropped, the
    query kept. Nothing is decoded, so "/a%2Fb" and "/a/b" stay two pages."""
    path, q, query = ask.partition("?")
    return (upper_escapes(path).rstrip("/") or "/") + q + query


def absolute_form(url: str) -> str:
    """An address on another host, in page_form's spirit: scheme and host in lower case."""
    p = urllib.parse.urlsplit(url)
    ask = urllib.parse.quote(p.path or "/", safe=SAFE_PATH) + ("?" + p.query if p.query else "")
    return "%s://%s%s" % (p.scheme.lower(), p.netloc.lower(), page_form(ask))


class Decision(NamedTuple):
    """What moves.csv says for one old page. kind: keep, let go, move (target is a path on the new
    site, escaped as written), off (target is an address on another host), not decided, not
    understood. resolve() adds: loop, chain (note says into what)."""
    kind: str
    target: str = ""
    note: str = ""


def read_moves(path: str) -> List[Tuple[int, str, str]]:
    """(line number, old_address, new_address) for each row of a decisions sheet. Commas or
    semicolons (German Excel), UTF-8 with or without the mark Excel adds. Raises ValueError with
    the reason the sheet cannot be read."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            text = fh.read()
    except UnicodeDecodeError:
        raise ValueError("%s is not UTF-8: save it as CSV UTF-8" % path)
    except OSError as e:
        raise ValueError("cannot read %s (%s)" % (path, e.strerror or type(e).__name__))
    head = text.split("\n", 1)[0]
    delimiter = ";" if head.count(";") > head.count(",") else ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)  # a line break inside a cell stays in it
    try:
        header = [c.strip().lower() for c in next(reader)]
    except StopIteration:
        raise ValueError("%s is empty" % path)
    except csv.Error as e:
        raise ValueError("cannot read %s (%s)" % (path, e))
    if "old_address" not in header or "new_address" not in header:
        raise ValueError("%s needs the columns old_address and new_address" % path)
    o, n = header.index("old_address"), header.index("new_address")
    rows = []
    try:
        line = reader.line_num + 1
        for row in reader:
            old = cell(row[o]) if o < len(row) else ""
            if old:
                rows.append((line, old, cell(row[n]) if n < len(row) else ""))
            line = reader.line_num + 1
    except csv.Error as e:
        raise ValueError("cannot read %s (%s)" % (path, e))
    return rows


def decide(new: str, old_host: str, site_host: str) -> Decision:
    """One new_address cell, read. A full address on the old host or the new site's own host
    (site_host) is read as its path, so it can never become a redirect to itself."""
    word = new.strip().lower()
    if word == "keep":
        return Decision("keep")
    if word == "let go":
        return Decision("let go")
    if not new:
        return Decision("not decided")
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in new) or "#" in new:
        return Decision("not understood", note="a space, a line break or a # anchor; this script writes no anchors")
    if new.startswith("/") and not new.startswith("//"):
        p = urllib.parse.urlsplit(new)
        absolute = False
    elif new.lower().startswith(("http://", "https://")) and wi.web_address(new):
        p = urllib.parse.urlsplit(new)
        absolute = _bare(p.hostname or "") not in {old_host, _bare(site_host)}
    else:
        return Decision("not understood", note="a new address starts with / or https://, or reads keep or let go")
    if "*" in p.path or ":" in p.path:
        return Decision("not understood", note="* and : have a meaning in _redirects")
    if p.username is not None or p.password is not None:
        return Decision("not understood", note="a name or password in the address")
    query = urllib.parse.quote(p.query, safe=SAFE_PATH + "=?") if p.query else ""
    path = upper_escapes(urllib.parse.quote(p.path or "/", safe=SAFE_PATH) + ("?" + query if query else ""))
    if absolute:
        return Decision("off", "%s://%s%s" % (p.scheme.lower(), p.netloc.lower(), path))
    return Decision("move", path)


def same_decision(d: Decision, page: str) -> tuple:
    """What a decision means for one page, for telling two rows of it apart: keep and a move to
    the same page are one decision, and so are two addresses elsewhere that differ by a slash."""
    if d.kind == "keep" or (d.kind == "move" and page_form(d.target) == page):
        return ("keep",)
    if d.kind == "move":
        return ("move", page_form(d.target))
    if d.kind == "off":
        return ("off", absolute_form(d.target))
    return (d.kind,)


def gather(rows: List[Tuple[int, str, str]], old_host: str, site_host: str,
           listed: Optional[set] = None) -> Tuple[Dict[str, Decision], Dict[str, Tuple[int, str, str]], List[str]]:
    """({page: decision}, {page: the row it came from}, rows for pages not in `listed`), one
    reading of a decisions sheet for both scripts. Raises ValueError when one page has two
    different decisions: which one was meant cannot be guessed."""
    decisions: Dict[str, Decision] = {}
    first: Dict[str, Tuple[int, str, str]] = {}
    unlisted: List[str] = []
    for line, old, new in rows:
        try:
            ask = ask_of(old, old_host)
        except ValueError:                                # "http://[::1" and the like
            ask = None
        page = page_form(ask) if ask is not None else None
        if page is None or (listed is not None and page not in listed):
            unlisted.append("%s (row %s): add it to the address list first, or fix it" % (old, line))
            if page is not None and page not in decisions:
                decisions[page] = Decision("not in the address list")  # a chain into it is a finding too
                first[page] = (line, old, new)
            continue
        d = decide(new, old_host, site_host)
        if page in first and decisions[page].kind != "not in the address list":
            if same_decision(decisions[page], page) != same_decision(d, page):
                l0, old0, new0 = first[page]
                raise ValueError("one page, two different decisions: %s (row %s) says %r, %s (row %s) says %r"
                                 % (old0, l0, new0 or "(empty)", old, line, new or "(empty)"))
            continue                                      # the same decision again
        decisions[page], first[page] = d, (line, old, new)
    return decisions, first, unlisted


def resolve(decisions: Dict[str, Decision]) -> Dict[str, Decision]:
    """Each page's decision with its chain followed to the end: /a -> /b and /b -> /c gives
    /a -> /c. A chain that runs into a page let go, not decided or not understood (or any kind
    make_redirects marks as a finding) ends in kind "chain"; one that comes back is a "loop"."""
    out = {}
    for page in decisions:
        here, d, seen = page, decisions[page], [page]
        while d.kind == "move":
            nxt = page_form(d.target)
            if nxt == here or nxt not in decisions:
                break                                     # the same page, or a page of the new site
            nd = decisions[nxt]
            if same_decision(nd, nxt) == ("keep",):
                break                                     # kept, or moved to itself (/b -> /b/)
            if nxt in seen:
                d = Decision("loop", note=" -> ".join(seen + [nxt]))
                break
            if nd.kind not in ("move", "off"):
                d = Decision("chain", note="points at %s, which is %s" % (nxt, nd.kind))
                break
            here, d = nxt, nd
            seen.append(nxt)
        out[page] = d
    return out


def expectations(moves_file: str, old_host: str, site_host: str) -> Dict[str, Decision]:
    """{page_form of an old page: its decision, chains followed}. Raises ValueError for a sheet
    that cannot be read, one page with two decisions, or a loop: make_redirects.py stops on
    those too, so no check can rest on them."""
    decisions, _, _ = gather(read_moves(moves_file), old_host, site_host)
    final = resolve(decisions)
    loops = sorted({d.note for d in final.values() if d.kind == "loop"})
    if loops:
        raise ValueError("moves.csv has a loop: %s" % "; ".join(loops))
    return final


def observed(url: str, origin: Tuple[str, str, int]) -> str:
    """Where a redirect ended, in the form decisions are compared in. Anywhere but the checked
    site's own origin (another port too) keeps its full address."""
    if not wi.web_address(url) or wi.origin_of(url) != origin:
        return absolute_form(url)
    p = urllib.parse.urlsplit(url)
    return page_form(urllib.parse.quote(p.path or "/", safe=SAFE_PATH) + ("?" + p.query if p.query else ""))


def check(addresses_file: str, new_site: str, let_go_file: Optional[str], delay: float, timeout: float,
          max_requests: int, moves_file: Optional[str] = None, site: Optional[str] = None) -> Tuple[Optional[dict], str]:
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
    if site is not None and not wi.web_address(site):
        return None, "--site is not a web address: %s" % site
    expected: Optional[Dict[str, Decision]] = None
    if moves_file:
        try:
            expected = expectations(moves_file, old_host, urllib.parse.urlsplit(site or new_site).hostname or "")
        except ValueError as e:
            return None, str(e)
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
    old_home = {root_key} | {wi.path_key("%s/%s" % (base, f), host) for f in HOME_FILES}

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
            if wi.path_key(resp.url, host) in home_keys and asked_key not in old_home:
                result, note = "sent home", SENT_HOME_REASON
            else:
                result = "redirected"
        elif resp.status in (404, 410):
            dropped = key_of(ask) in let_go or (expected is not None and expected.get(page_form(ask), Decision("")).kind == "let go")
            result = "let go" if dropped else "missing"
            if resp.via:
                note = "forwards to %s, which is not found" % resp.url
        else:
            result, note = "unreadable", problem
        row = {"old_address": old, "result": result, "status": resp.status or "", "ends_at": ends_at,
               "temporary_redirect": temp[0] if temp else "", "note": note}
        if expected is not None:
            d = expected.get(page_form(ask), Decision(""))
            want = {"keep": page_form(ask), "move": page_form(d.target) if d.kind == "move" else "",
                    "off": d.target if d.kind == "off" else ""}.get(d.kind, "")
            row["decided"] = want if d.kind in ("keep", "move", "off") else d.kind
            if want and result in ("kept", "redirected", "off the site"):
                got = page_form(ask) if result == "kept" else observed(ends_at, fetcher.origin)
                if got != (absolute_form(want) if d.kind == "off" else want):
                    row["result"] = "not as decided"
                    row["note"] = "moves.csv sends it to %s; it %s" % (want, "stays where it was" if result == "kept"
                                                                       else "ends at %s" % ends_at)
                    if d.kind == "off" and site is None and not got.startswith(("http://", "https://")):
                        row["note"] += " (if %s is the new site's live address, pass it as --site)" % urllib.parse.urlsplit(want).hostname
        rows.append(row)
    counts = collections.Counter(r["result"] for r in rows)
    order = ORDER + (("not as decided",) if expected is not None else ())
    return {
        "new_site": base + "/", "old_host": old_host, "moved": moved, "checked": len(rows), "rows": rows,
        "counts": {k: counts.get(k, 0) for k in order}, "order": order, "moves": expected is not None,
        "elsewhere": elsewhere,
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
    L.extend("| %s | %s |" % (k, d["counts"][k]) for k in d["order"])
    if d["temporary"]:
        add("")
        add("%s temporary (302, 303 or 307); move-check.csv says which. If the move is for good, make "
            "%s permanent (301 or 308)." % (("1 redirect is", "it") if d["temporary"] == 1
                                           else ("%s redirects are" % d["temporary"], "them")))
    for kind, title in (("missing", "Missing"), ("sent home", "Sent to the home page"), ("unreadable", "Unreadable"),
                        ("not as decided", "Not where moves.csv sends it")):
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
    ap.add_argument("--moves", help="moves.csv, the decisions make_redirects.py writes from: is each address where it says?")
    ap.add_argument("--site", help="with --moves: the new site's live address, when the checked address is a preview")
    ap.add_argument("--delay", type=float, default=0.2, help="seconds between requests (default 0.2)")
    ap.add_argument("--timeout", type=float, default=30.0, help="seconds to wait for one answer (default 30)")
    ap.add_argument("--max-requests", type=int, default=5000, help="stop after this many requests (default 5000)")
    args = ap.parse_args(argv)
    if args.site and not args.moves:
        ap.print_usage(sys.stderr)
        print("check_move: --site goes with --moves", file=sys.stderr)
        return 2
    data, stop = check(args.addresses, args.new_site, args.let_go, max(args.delay, 0.0), args.timeout, max(args.max_requests, 3),
                       args.moves, args.site)
    if data is None:
        print("check_move: %s" % stop, file=sys.stderr)
        return 2
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "move-check.md"), "w", encoding="utf-8") as fh:
        fh.write(render(data))
    with open(os.path.join(args.out, "move-check.csv"), "w", encoding="utf-8", newline="") as fh:
        fields = CSV_FIELDS + (["decided"] if data["moves"] else [])
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in data["rows"]:
            w.writerow({k: wi.safe_cell(row[k]) for k in fields})
    for k in data["order"]:
        print("%-14s %s" % (k, data["counts"][k]))
    print("%s: %s" % ("FINDINGS" if data["findings"] else "all accounted for", os.path.join(args.out, "move-check.md")))
    return 1 if data["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
