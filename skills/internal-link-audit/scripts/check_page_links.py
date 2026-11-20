#!/usr/bin/env python3
"""Is one new page linked well enough? Reads the built site (dist/) and checks three things:

  L1  at least 2 other pages link to it, and at least 1 of them from its body: inside that page's
      <main>, and not inside a <header>, <nav>, <footer> or <aside>.
  L2  (with --hub) the hub links to it from the hub's body, and the page links back to the hub
      from an <a> inside the page's own <main> (a breadcrumb <nav> inside <main> counts).
  L3  it is at most 3 clicks from the home page.

  python3 check_page_links.py dist /new-page --site https://example.com (--hub /hub | --no-hub)

Exit 0: all met. Exit 1: each miss is listed, with the pages that link here. Exit 2: the check
cannot judge (no dist/, no file for the page or the hub, neither --hub nor --no-hub, or --hub given
and the page has no <main>). An <a> with a `hidden` attribute, or inside an element that has one,
is not counted; CSS is not read. Standard library only; Python 3.9 or newer.
"""
import argparse
import os
import sys
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

NEEDED = 2          # pages that must link here (L1)
MAX_DEPTH = 3       # clicks from home (L3)
LIST_MAX = 10       # inbound pages printed; a footer link makes every page one
NOT_BODY = {"header", "nav", "footer", "aside"}
VOID = {"br", "hr", "img", "input", "meta", "link", "wbr", "source", "col", "area", "base", "embed",
        "track", "param"}


def fold_host(host):
    host = (host or "").lower()
    return host[4:] if host.startswith("www.") else host


def fold_path(path):
    """A page's key: leading slash, no closing slash (home is "/")."""
    path = "/" + path.lstrip("/")
    return path.rstrip("/") or "/"


class Links(HTMLParser):
    """Every <a href> of one page, each with whether it sits in the body (inside <main>, outside
    header, nav, footer and aside) and whether it sits inside <main> at all. Hidden ones are left out."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []             # (tag, hidden, in-main marker, not-body marker) of open tags
        self.has_main = False
        self.links = []             # (href, in_main, body)

    def _state(self):
        hidden = any(h for _, h, _, _ in self.stack)
        in_main = any(m for _, _, m, _ in self.stack)
        not_body = any(n for _, _, _, n in self.stack)
        return hidden, in_main, in_main and not not_body

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href") is not None and "hidden" not in a:
            hidden, in_main, body = self._state()
            if not hidden:
                self.links.append((a["href"], in_main, body))
        if tag in VOID:
            return
        if tag == "main":
            self.has_main = True
        self.stack.append((tag, "hidden" in a, tag == "main", tag in NOT_BODY))

    def handle_endtag(self, tag):
        if tag in VOID or all(t != tag for t, _, _, _ in self.stack):
            return
        while self.stack:                       # close tags the markup left open inside this one
            if self.stack.pop()[0] == tag:
                break


def served_address(rel):
    """dist-relative file path -> (page key, the address the file is served at)."""
    p = "/" + rel.replace(os.sep, "/")
    p = p[:-len(".html")]
    if p == "/index":
        return "/", "/"
    if p.endswith("/index"):
        key = p[:-len("/index")]
        return key, key + "/"
    return p, p


def read_site(dist, site_host):
    """{page key: (has_main, [(target key, in_main, body)])} for every dist/**/*.html."""
    pages = {}
    for root, _, files in os.walk(dist):
        for name in sorted(files):
            if not name.endswith(".html"):
                continue
            full = os.path.join(root, name)
            key, address = served_address(os.path.relpath(full, dist))
            with open(full, encoding="utf-8") as f:
                parser = Links()
                parser.feed(f.read())
                parser.close()
            base = "https://" + site_host + address
            edges = []
            for href, in_main, body in parser.links:
                u = urlsplit(urljoin(base, href.strip()))
                if u.scheme not in ("http", "https") or fold_host(u.hostname) != site_host:
                    continue
                edges.append((fold_path(u.path), in_main, body))
            pages[key] = (parser.has_main, edges)
    return pages


def depths(pages):
    """Clicks from home to each page (breadth first over every counted link)."""
    seen = {"/": 0}
    queue = ["/"]
    while queue:
        cur = queue.pop(0)
        for tgt, _, _ in pages.get(cur, (False, []))[1]:
            if tgt in pages and tgt not in seen:
                seen[tgt] = seen[cur] + 1
                queue.append(tgt)
    return seen


def plural(n, one, many):
    return "%d %s" % (n, one if n == 1 else many)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check that one new page is linked well enough.")
    ap.add_argument("dist", help="the built site folder")
    ap.add_argument("page", help="the page's path, such as /guides/new-page")
    ap.add_argument("--site", required=True, help="the site's address, such as https://example.com")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--hub", help="the page's hub, as a path")
    grp.add_argument("--no-hub", action="store_true", help="the page has no hub")
    args = ap.parse_args(argv)

    def cannot(msg):
        print("cannot judge: " + msg, file=sys.stderr)
        return 2

    site_host = fold_host(urlsplit(args.site).hostname)
    if not site_host:
        return cannot("--site %r has no host" % args.site)
    if not os.path.isdir(args.dist):
        return cannot("%s is not a folder (build the site first)" % args.dist)
    if not args.hub and not args.no_hub:
        return cannot("say --hub /path, or --no-hub if the page has no hub")
    page = fold_path(args.page)
    hub = fold_path(args.hub) if args.hub else None
    pages = read_site(args.dist, site_host)
    if page not in pages:
        return cannot("no built file for %s in %s" % (page, args.dist))
    if hub and hub not in pages:
        return cannot("no built file for the hub %s in %s" % (hub, args.dist))
    if hub and not pages[page][0]:
        return cannot("%s has no <main>, so it cannot link back to its hub from one" % page)

    inbound = []                    # (source, in_main, body, source has main)
    for src, (has_main, edges) in sorted(pages.items()):
        if src == page:
            continue
        hits = [e for e in edges if e[0] == page]
        if hits:
            inbound.append((src, any(e[2] for e in hits), has_main))
    bodies = [s for s, body, _ in inbound if body]
    depth = depths(pages).get(page)

    print("%s: %s" % (page, "hub " + hub if hub else "no hub"))
    print("%s link here (%d needed), %d from their body:" % (
        plural(len(inbound), "page", "pages"), NEEDED, len(bodies)))
    shown = sorted(inbound, key=lambda i: (not i[1], i[0]))[:LIST_MAX]     # body links first
    for src, body, has_main in shown:
        note = "body" if body else ("not body (outside <main>, or in header, nav, footer, aside)" if has_main else "no <main> on that page")
        print("  %s  %s" % (src, note))
    if len(inbound) > LIST_MAX:
        print("  ... and %d more" % (len(inbound) - LIST_MAX))
    print("clicks from home: %s" % ("not reachable" if depth is None else depth))

    misses = []
    if len(inbound) < NEEDED:
        misses.append("only %s here, %d needed" % (
            "1 page links" if len(inbound) == 1 else "%d pages link" % len(inbound), NEEDED))
    if not bodies:
        misses.append("no body link: no page links here from inside its <main> "
                      "(outside header, nav, footer and aside)")
    if hub:
        hub_has_main, hub_edges = pages[hub]
        if not hub_has_main:
            misses.append("the hub %s has no <main>, so it has no body link to this page" % hub)
        elif not any(t == page and body for t, _, body in hub_edges):
            misses.append("the hub %s has no body link to this page" % hub)
        if not any(t == hub and in_main for t, in_main, _ in pages[page][1]):
            misses.append("does not link back to its hub %s from <main>" % hub)
    if depth is None:
        misses.append("cannot be reached from the home page")
    elif depth > MAX_DEPTH:
        misses.append("is %d clicks from the home page, %d allowed" % (depth, MAX_DEPTH))

    if misses:
        for m in misses:
            print("MISS: " + m)
        return 1
    print("OK: L1, L2 and L3 met" if hub else "OK: L1 and L3 met (no hub)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
