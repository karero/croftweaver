#!/usr/bin/env python3
"""
wp_inventory.py — count what a live WordPress site holds, from the outside.

Read-only, and it needs no login and no backup. It asks the site's own public addresses:
robots.txt, the home page, the REST API (the list of content types, then each type's records,
100 at a time) and the sitemap. From the answers it writes three files:

  inventory.md    the report to read: records per content type, sitemap addresses, what the
                  two disagree on, the page builder and forms it saw, and what it could not see
  inventory.json  the same, for a program
  urls.csv        one row per address, from the REST API, the sitemap or both

It counts; it does not copy. No page text is written to disk, only numbers about it, and of
the site's user list only how many names it shows.

Standard library only (Python 3.9+), so it runs on a stock python3 with no installs.

Usage:
  python3 wp_inventory.py https://example.com --out ./inventory
  python3 wp_inventory.py https://example.com --max-requests 200 --delay 2

Exit codes: 0 the count is complete, 1 the count is incomplete (the report says where: a
request was refused, the site was too busy to answer, or the request limit was reached),
2 the run could not start (no such site, or neither a REST API nor a sitemap was found).

What it keeps to:
  - Only the host you name. A redirect to another host is reported, not followed. The one
    exception is the start address itself (example.com -> www.example.com), which it adopts
    and names in the report.
  - robots.txt, under the name "wordpress-inventory", by the rules of RFC 9309 as the toolkit's facts
    check implements them (the longest matching rule wins, * and $ count). An address it may not read is skipped and listed. A
    robots.txt that is refused (401, 403) or cannot be read stops the run.
  - A sitemap that declares a document type is not read: a sitemap needs none, and one can
    carry entity tricks that exhaust an older Python's XML parser. The parser itself is
    made to stop at the declaration, before it reads on. Such a file is a gap in the count.
  - A pause between requests (--delay) and a ceiling on their number (--max-requests).
  - A refusal, a "please wait" or maintenance page, or any web page where data was due is
    never counted as content. It makes the count incomplete.

What it cannot see, and says so in the report: drafts and private records, and the text of
password-protected ones; content a plugin draws inside a page (a directory in pop-ups, say); fields a plugin
keeps to itself (a session's start time, for one); media files themselves, only their number.
"""

from __future__ import annotations

import argparse
import collections
import csv
import gzip
import html
import http.client
import io
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple
from xml.parsers import expat

ROBOTS_TOKEN = "wordpress-inventory"  # the name a robots.txt group calls this tool by
USER_AGENT = ROBOTS_TOKEN + "/0.1 (read-only site inventory)"
MAX_BYTES = 16 * 1024 * 1024
SITEMAP_MAX_BYTES = 52 * 1024 * 1024  # the protocol allows 50 MB, uncompressed
MAX_SITEMAP_FILES = 200  # a guard against loops and endless indexes
MAX_HOPS = 5
PER_PAGE = 100  # the most the REST API hands out in one answer

# Content types WordPress keeps for its own machinery; `attachment` (media) is counted apart.
INTERNAL_TYPES = {
    "attachment", "nav_menu_item", "wp_block", "wp_template", "wp_template_part",
    "wp_global_styles", "wp_navigation", "wp_font_family", "wp_font_face",
}
CORE_NAMESPACES = {"wp/v2", "oembed/1.0", "wp-site-health/v1", "wp-block-editor/v1", "wp-abilities/v1"}

# What a page builder or form plugin leaves in the HTML it produces.
BUILDER_MARKS = {
    "WPBakery": re.compile(r"\bvc_row\b|\[vc_|\bwpb_"),
    "Elementor": re.compile(r"\belementor-"),
    "Divi": re.compile(r"\bet_pb_"),
    "Beaver Builder": re.compile(r"\bfl-builder\b|\bfl-row\b"),
    "block editor": re.compile(r"\bwp-block-"),
}
FORM_MARKS = {
    "Gravity Forms": re.compile(r"gform_wrapper|\[gravityform"),
    "Contact Form 7": re.compile(r"\bwpcf7\b|\[contact-form-7"),
    "WPForms": re.compile(r"\bwpforms-"),
    "Ninja Forms": re.compile(r"\bnf-form-"),
}
_FORM_TAG = re.compile(r"<form\b", re.I)
_SCRIPT = re.compile(r"(?is)<(script|style)\b.*?</\1\s*>")
_TAG = re.compile(r"(?s)<[^>]*>")
_SC_OPEN = re.compile(r"\[([a-z][a-z0-9_-]{2,40})((?:\s[^\[\]]{0,400})?)/?\]")
_SC_CLOSE = re.compile(r"\[/([a-z][a-z0-9_-]{2,40})\]")
_WORD = re.compile(r"[^\W\d_]+")
# Two languages only, the two this guess was checked on. Anything else reads "unknown".
_STOP = {
    "de": frozenset("der die das und ist nicht mit für von auf eine einer den dem zu im sich auch wird sind bei wie".split()),
    "en": frozenset("the and is of to in for with that on are this as by from be at an it has".split()),
}


def strip_tags(markup: str) -> str:
    return html.unescape(_TAG.sub(" ", _SCRIPT.sub(" ", markup)))


def raw_shortcodes(text: str) -> "collections.Counter[str]":
    """Shortcodes left as text ("[vc_row]", "[caption id=...]"): the sign that a plugin's markup
    reached the reader unrendered. A bracketed word counts only when it has a closing tag, an
    attribute or an underscore, so "[sic]" and "[1]" do not."""
    closes = set(_SC_CLOSE.findall(text))
    found: "collections.Counter[str]" = collections.Counter()
    for name, attrs in _SC_OPEN.findall(text):
        if name in closes or "_" in name or "=" in attrs:
            found[name] += 1
    return found


def guess_language(text: str) -> str:
    words = [w.lower() for w in _WORD.findall(text)]
    if len(words) < 40:
        return "unknown"
    hits = {lang: sum(1 for w in words if w in stop) for lang, stop in _STOP.items()}
    (best, n), (_, m) = sorted(hits.items(), key=lambda kv: -kv[1])[:2]
    return best if n >= 8 and n > 1.5 * m else "unknown"


def analyse(markup: str) -> dict:
    text = strip_tags(markup)
    return {
        "words": len(_WORD.findall(text)),
        "builders": sorted(k for k, rx in BUILDER_MARKS.items() if rx.search(markup)),
        "forms": sorted(k for k, rx in FORM_MARKS.items() if rx.search(markup))
                 or (["other form"] if _FORM_TAG.search(markup) else []),
        "raw_shortcodes": dict(raw_shortcodes(text)),
        "iframes": len(re.findall(r"<iframe\b", markup, re.I)),
        "language": guess_language(text),
    }


def web_address(url: str) -> bool:
    """An http(s) address with a host and a port that is a number."""
    try:
        p = urllib.parse.urlsplit(url)
        p.port  # raises ValueError for "host:abc" and for a port out of range
    except ValueError:
        return False
    return p.scheme.lower() in ("http", "https") and bool(p.hostname)


def origin_of(url: str) -> Tuple[str, str, int]:
    """(scheme, host, port). Callers hand it only what web_address() accepts."""
    p = urllib.parse.urlsplit(url)
    return (p.scheme.lower(), (p.hostname or "").lower(), p.port or (443 if p.scheme.lower() == "https" else 80))


def bare_host(host: str) -> str:
    host = (host or "").lower()
    return host[4:] if host.startswith("www.") else host


def path_key(url: str, site_host: str) -> str:
    """The address as the site knows it: its path without a trailing slash, plus its query
    ("/?p=1" and "/?p=3" are two pages). An address on another host keeps its full form, so it
    never matches one of the site's own."""
    p = urllib.parse.urlsplit(url)
    if p.hostname and bare_host(p.hostname) != bare_host(site_host):
        return url
    return (p.path.rstrip("/") or "/") + ("?" + p.query if p.query else "")


def safe_cell(value) -> str:
    """A spreadsheet runs a cell that starts with = + - or @ as a formula. Addresses and slugs
    come from the site, so such a cell gets a leading apostrophe."""
    s = "" if value is None else str(value)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def md(value, limit: int = 120) -> str:
    """Text from the site, made safe for a Markdown table cell."""
    s = re.sub(r"\s+", " ", "" if value is None else str(value)).strip()
    s = s.replace("\\", "\\\\").replace("|", "\\|").replace("`", "'").replace("<", "&lt;")
    s = s.replace("[", "\\[").replace("]", "\\]")  # CommonMark reads an escaped bracket as text, so it opens no link or image
    return s if len(s) <= limit else s[: limit - 1] + "…"


# --- robots.txt, read as RFC 9309 reads it. This is the matcher of skills/facts-check/scripts/
# facts_check.py, copied because a skill travels alone; keep the two in step. The standard
# library's parser cannot be used: before Python 3.13 it ignores * and $, so the same robots.txt
# would keep this tool out on one machine and let it in on another.
_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
_ESCAPE_OR_ODD = re.compile(r"%[0-9A-Fa-f]{2}|[^A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]")
_LINE_END = re.compile(r"\r\n|\r|\n")
_AGENT_NAME = re.compile(r"[A-Za-z_-]*")


def request_target(url: str) -> str:
    """The path and query a request for this address sends: urllib's own selector."""
    return urllib.request.Request(url).selector or "/"


def robots_form(text: str) -> str:
    """A rule or a request path as RFC 9309 (2.2.2) compares them: a character that is no URI
    character becomes percent escapes of its UTF-8 bytes, an escape of an unreserved character
    becomes the character, any other escape gets capital hex digits."""
    def one(m):
        s = m.group()
        if len(s) == 3 and s[0] == "%":
            c = chr(int(s[1:], 16))
            return c if c in _UNRESERVED else s.upper()
        return "".join("%%%02X" % b for b in s.encode("utf-8", "replace"))
    return _ESCAPE_OR_ODD.sub(one, text)


def _matches(parts: List[str], anchored: bool, path: str) -> bool:
    """Does a rule, split at its *, match the start of `path` (all of it, if the rule ended in $)?"""
    if not path.startswith(parts[0]):
        return False
    pos = len(parts[0])
    if len(parts) == 1:
        return len(path) == pos if anchored else True
    for piece in parts[1:-1]:
        at = path.find(piece, pos)
        if at < 0:
            return False
        pos = at + len(piece)
    last = parts[-1]
    if anchored:
        return len(path) - len(last) >= pos and path.endswith(last)
    return path.find(last, pos) >= 0


class RobotsRules:
    """What a robots.txt allows this tool. Groups are runs of User-agent lines followed by Allow
    and Disallow rules; the group that names this tool counts, else the group of "*"; the groups
    of one name are combined. The longest matching rule wins, and an Allow wins a tie."""

    def __init__(self):
        self.rules: List[Tuple[int, bool, List[str], bool]] = []  # (length, allow, pieces, ends in $), best first
        self.sitemaps: List[str] = []

    def parse(self, text: str) -> None:
        named: List[tuple] = []
        everyone: List[tuple] = []
        any_named = mine = star = in_rules = False
        for line in _LINE_END.split(text):
            name, colon, value = line.split("#", 1)[0].lstrip(" \t﻿").partition(":")
            name = name.strip().lower()
            if not colon:
                continue
            value = value.strip()
            if name == "user-agent":
                if in_rules:  # an agent line after rules starts the next group
                    mine = star = in_rules = False
                if _AGENT_NAME.match(value).group().lower() == ROBOTS_TOKEN:
                    mine = any_named = True
                elif value == "*":
                    star = True
            elif name in ("allow", "disallow"):
                in_rules = True
                if not value or not (mine or star):  # an empty rule says nothing, and another agent's is not read
                    continue
                pattern = robots_form(value)
                anchored = pattern.endswith("$")
                rule = (len(pattern), name == "allow", (pattern[:-1] if anchored else pattern).split("*"), anchored)
                if mine:
                    named.append(rule)
                if star:
                    everyone.append(rule)
            elif name == "sitemap" and value:
                self.sitemaps.append(value)
        self.rules = sorted(named if any_named else everyone, key=lambda r: (-r[0], not r[1]))

    def allowed(self, url: str) -> bool:
        path = robots_form(request_target(url))
        if path == "/robots.txt":  # RFC 9309 (2.2.2): the file itself is always allowed
            return True
        for _, allow, parts, anchored in self.rules:
            if _matches(parts, anchored, path):
                return allow
        return True


class Resp:
    __slots__ = ("url", "status", "ctype", "headers", "body", "note", "redirect_to", "via")

    def __init__(self, url, status=0, ctype="", headers=None, body=b"", note="", redirect_to=""):
        self.url, self.status, self.ctype, self.headers = url, status, ctype, headers
        self.body, self.note, self.redirect_to = body, note, redirect_to
        self.via: List[int] = []  # the status of each redirect followed on the way to `url`

    def text(self) -> str:
        m = re.search(r"charset=([\w-]+)", self.ctype or "", re.I)
        try:
            return self.body.decode(m.group(1) if m else "utf-8", "replace")
        except LookupError:
            return self.body.decode("utf-8", "replace")

    def problem(self) -> str:
        """Why this answer cannot be used, or "" when it can."""
        if self.note:
            return self.note
        if self.status in (403, 429, 503):
            return "the site refused the request or was too busy (HTTP %s)" % self.status
        if self.status != 200:
            return "HTTP %s" % self.status
        return ""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # every redirect comes back to Fetcher.get, which decides


class Fetcher:
    def __init__(self, start: str, delay: float, timeout: float, max_requests: int, user_agent: str):
        self.origin = origin_of(start)
        self.delay, self.timeout, self.max_requests, self.user_agent = delay, timeout, max_requests, user_agent
        self.opener = urllib.request.build_opener(_NoRedirect)
        self.robots: Optional[RobotsRules] = None
        self.count = 0
        self.cap_hit = False
        self.log: List[dict] = []
        self._last = 0.0

    def _fetch(self, url: str, limit: int) -> Resp:
        if self.count >= self.max_requests:
            self.cap_hit = True
            return Resp(url, note="not asked: the request limit (%s) was reached" % self.max_requests)
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        self.count += 1
        self._last = time.monotonic()
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent, "Accept": "*/*"})
        try:
            with self.opener.open(req, timeout=self.timeout) as r:
                status, headers, body = r.status, r.headers, r.read(limit + 1)
        except urllib.error.HTTPError as e:
            status, headers = e.code, e.headers
            try:
                body = e.read(65536)
            except (OSError, http.client.HTTPException):
                body = b""
        except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError) as e:
            return Resp(url, note="no answer (%s)" % type(e).__name__)
        resp = Resp(url, status, headers.get("Content-Type", "") if headers else "", headers, body)
        if len(body) > limit:
            resp.note = "the answer is larger than %s MB" % (limit // (1024 * 1024))
        return resp

    def get(self, url: str, limit: int = MAX_BYTES, robots_exempt: bool = False) -> Resp:
        """One address of this site. A redirect within the site is followed; one that leaves
        it comes back as `redirect_to`, unfetched."""
        resp = Resp(url, note="too many redirects")
        via: List[int] = []
        for _ in range(MAX_HOPS + 1):
            if not web_address(url):
                resp = Resp(url, note="not a web address")
                break
            if origin_of(url) != self.origin:
                resp = Resp(url, note="on another host, not asked")
                break
            if not robots_exempt and self.robots is not None and not self.robots.allowed(url):
                resp = Resp(url, note="robots.txt does not allow it")
                break
            resp = self._fetch(url, limit)
            loc = resp.headers.get("Location") if (resp.headers and resp.status in (301, 302, 303, 307, 308)) else None
            if not loc:
                break
            nxt = urllib.parse.urljoin(url, loc)
            if not web_address(nxt):
                resp.note = "redirects to something that is not a web address"
                break
            if origin_of(nxt) != self.origin:
                resp.note = "redirects to another host (%s), not followed" % urllib.parse.urlsplit(nxt).netloc
                resp.redirect_to = nxt
                break
            via.append(resp.status)
            url = nxt
            resp = Resp(url, note="too many redirects")
        resp.via = via
        self.log.append({"url": resp.url, "status": resp.status, "bytes": len(resp.body), "problem": resp.problem()})
        return resp

    def load_robots(self, base: str) -> str:
        """Read robots.txt for the current host. Returns "" or why the run must stop."""
        self.robots = None
        scheme, host, port = self.origin
        resp = self.get("%s://%s/robots.txt" % (scheme, urllib.parse.urlsplit(base).netloc), 1024 * 1024, robots_exempt=True)
        rules = RobotsRules()
        if resp.status == 200 and not resp.note:
            rules.parse(resp.text())  # a web page in its place holds no rule: nothing is disallowed
        elif resp.status in (401, 403):
            return "robots.txt is refused to this tool (HTTP %s), which means keep out; nothing else was asked" % resp.status
        elif 400 <= resp.status < 500 and resp.status != 429 and not resp.note:
            pass  # no robots.txt: nothing is disallowed
        else:
            return "robots.txt could not be read (%s), so nothing else was asked" % (resp.problem() or "no rules")
        self.robots = rules
        return ""


def as_json(resp: Resp):
    """(data, problem). A 200 that is not JSON is never data."""
    problem = resp.problem()
    if problem:
        return None, problem
    try:
        return json.loads(resp.body.decode("utf-8", "replace")), ""
    except ValueError:
        return None, ("a web page came back where data was due" if "html" in (resp.ctype or "").lower()
                      else "the answer is not JSON")


def header_int(resp: Resp, name: str) -> Optional[int]:
    try:
        n = int(resp.headers.get(name)) if resp.headers else None
    except (TypeError, ValueError):
        return None
    return n if n is not None and n >= 0 else None


class Rest:
    """Builds REST addresses in the site's own style: /wp-json/wp/v2/posts or ?rest_route=/wp/v2/posts."""

    def __init__(self, root: str):
        self.root = root

    def url(self, route: str, **params) -> str:
        route = route.strip("/")
        query = urllib.parse.urlencode(params)
        if "rest_route=" in self.root:
            head, _, _ = self.root.partition("rest_route=")
            return head + "rest_route=/" + urllib.parse.quote(route) + ("&" + query if query else "")
        return self.root.rstrip("/") + "/" + route + ("?" + query if query else "")


def read_type(fetcher: Fetcher, rest: Rest, slug: str, info: dict, site_host: str, records: List[dict]) -> dict:
    out = {"type": slug, "name": str(info.get("name") or slug), "total": None, "fetched": 0, "complete": False, "note": ""}
    stats = []
    seen_ids = set()
    repeats = no_id = 0
    route = str(info.get("rest_namespace") or "wp/v2").strip("/") + "/" + str(info["rest_base"]).strip("/")
    page, pages = 1, 1
    while page <= pages:
        resp = fetcher.get(rest.url(route, per_page=PER_PAGE, page=page,
                                    _fields="id,link,slug,date,modified,type,title,content"))
        data, problem = as_json(resp)
        if problem or not isinstance(data, list):
            out["note"] = problem or "the answer is not a list"
            break
        total = header_int(resp, "X-WP-Total")
        if page == 1:
            out["total"] = total
            pages = header_int(resp, "X-WP-TotalPages") or 1
        elif total != out["total"]:
            out["note"] = "the site's total changed while it was read (%s, then %s)" % (out["total"], total)
            break
        for rec in data:
            if not isinstance(rec, dict):
                continue
            if isinstance(rec.get("id"), (int, str)) and not isinstance(rec.get("id"), bool) and rec["id"] != "":
                if rec["id"] in seen_ids:
                    repeats += 1
                    continue
                seen_ids.add(rec["id"])
            else:
                no_id += 1  # still counted and listed; without a usable id a repeat cannot be told from a second record
            content = rec.get("content") if isinstance(rec.get("content"), dict) else {}
            a = analyse(str(content.get("rendered") or ""))
            stats.append((rec, a))
            records.append({"url": str(rec.get("link") or ""), "key": path_key(str(rec.get("link") or ""), site_host),
                            "type": slug, "id": rec.get("id"), "modified": str(rec.get("modified") or "")[:10], **a})
        page += 1
    out["fetched"] = len(stats)  # distinct records: one handed out twice counts once
    if not out["note"]:
        if out["total"] is None:
            out["note"] = "the site did not report a total"
        elif repeats:
            out["note"] = "%s records were handed out twice, so the list changed or repeated while it was read" % repeats
        elif no_id:
            out["note"] = "%s records came without a usable id (a whole number or a text), so a repeat could not be told from a second record" % no_id
        elif out["fetched"] != out["total"]:
            out["note"] = "the site reports %s records, %s were handed out" % (out["total"], out["fetched"])
    out["complete"] = not out["note"]
    words = [a["words"] for _, a in stats]
    out.update({
        "by_year": dict(sorted(collections.Counter(str(r.get("date") or "")[:4] or "?" for r, _ in stats).items())),
        "last_modified": max((str(r.get("modified") or "")[:10] for r, _ in stats), default=""),
        "words_total": sum(words),
        "words_median": round(statistics.median(words)) if words else 0,
        "builders": dict(collections.Counter(b for _, a in stats for b in a["builders"]).most_common()),
        "forms": dict(collections.Counter(f for _, a in stats for f in a["forms"]).most_common()),
        "records_with_forms": sum(1 for _, a in stats if a["forms"]),
        "records_with_raw_shortcodes": sum(1 for _, a in stats if a["raw_shortcodes"]),
        "raw_shortcodes": dict(sum((collections.Counter(a["raw_shortcodes"]) for _, a in stats), collections.Counter()).most_common(12)),
        "records_with_iframes": sum(1 for _, a in stats if a["iframes"]),
        "languages": dict(collections.Counter(a["language"] for _, a in stats).most_common()),
    })
    return out


def count_only(fetcher: Fetcher, rest: Rest, route: str) -> Tuple[Optional[int], str]:
    resp = fetcher.get(rest.url(route, per_page=1, _fields="id"))
    data, problem = as_json(resp)
    if problem:
        return None, problem
    if not isinstance(data, list):
        return None, "the answer is not a list"
    total = header_int(resp, "X-WP-Total")
    return (total, "") if total is not None else (None, "the site did not report a total")


class _StopParsing(Exception):
    pass


def parse_sitemap(body: bytes) -> Tuple[str, List[str], str]:
    """(kind, addresses, problem). `kind` is "urlset", "sitemapindex", "page" (an HTML page),
    "other" (some other XML document) or "" (nothing that could be read).

    One reader decides everything: expat, the XML parser, in whatever encoding the file is
    written. No second look at the bytes can disagree with it.
      - It stops the moment it meets a document type, before the declarations inside it and
        long before any entity could expand; a sitemap needs no document type. Measured on
        expat 2.2.8 (the Python a Mac ships with, which has no expansion guard) and 2.7.4:
        a 10-level entity bomb stops in under a millisecond, also behind white space or a
        comment, and in UTF-16 or Latin-1.
      - It stops at the first element when that is neither <urlset> nor <sitemapindex>.
      - A file that ends early, or is damaged, is a problem: never a shorter sitemap.
    Addresses are the text of <loc> directly inside <url> or <sitemap>, whatever prefix the
    elements carry; image:loc and the like sit deeper and are not pages."""
    seen = {"doctype": None, "root": None}
    path: List[str] = []
    locs: List[str] = []
    text: List[str] = []
    parser = expat.ParserCreate(namespace_separator="}")
    parser.buffer_text = True

    def doctype(name, system_id, public_id, has_internal_subset):
        seen["doctype"] = name
        raise _StopParsing

    def start(name, attrs):
        local = name.rsplit("}", 1)[-1]
        if seen["root"] is None:
            seen["root"] = local
            if local not in ("urlset", "sitemapindex"):
                raise _StopParsing
        path.append(local)

    def end(name):
        if path and path[-1] == "loc" and len(path) == 3 and path[1] in ("url", "sitemap"):
            loc = "".join(text).strip()
            if loc:
                locs.append(loc)
        del text[:]
        path.pop()

    def chars(data):
        if path and path[-1] == "loc":
            text.append(data)

    parser.StartDoctypeDeclHandler = doctype
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = chars
    try:
        parser.Parse(body, True)
    except _StopParsing:
        if seen["doctype"] is not None:
            if seen["doctype"].lower() == "html":
                return "page", [], ""
            return "", [], "declares a document type, which a sitemap does not need"
        return ("page" if seen["root"].lower() == "html" else "other"), [], ""
    except (expat.ExpatError, LookupError, ValueError):  # cut off or damaged; or an encoding the parser does not know
        # An old HTML page opens with a document type XML cannot read (no system identifier), so
        # the parser fails before it can report it. Only where it had met no element yet is the
        # file's own first line consulted, and only to tell a web page from a damaged file.
        if seen["root"] is None and re.match(rb"(?:\xef\xbb\xbf)?\s*<!DOCTYPE\s+html\b", body[:1024], re.I):
            return "page", [], ""
        return "", [], "is not valid XML (cut off, damaged or in an unknown encoding)"
    return seen["root"] or "", locs, ""


def read_sitemaps(fetcher: Fetcher, starts: List[str], broken: List[str], absent: List[str]) -> List[dict]:
    """Every sitemap file reachable from `starts`. `broken` collects each file that could not be
    read; `absent` collects each start address that holds no sitemap at all (not found, or
    something else lives there). A file an index names is never merely absent."""
    queue, seen, files = list(starts), set(), []
    first = set(starts)
    while queue and len(seen) < MAX_SITEMAP_FILES:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        resp = fetcher.get(sm, SITEMAP_MAX_BYTES)
        problem = resp.problem()
        if problem:
            (absent if sm in first and resp.status in (404, 410) and not resp.note else broken).append("sitemap %s: %s" % (sm, problem))
            continue
        body = resp.body
        if body[:2] == b"\x1f\x8b":
            try:
                with gzip.GzipFile(fileobj=io.BytesIO(body)) as gz:
                    body = gz.read(SITEMAP_MAX_BYTES + 1)
            except (OSError, EOFError):
                broken.append("sitemap %s: cannot be unpacked" % sm)
                continue
            if len(body) > SITEMAP_MAX_BYTES:
                broken.append("sitemap %s: unpacks to more than the limit of %d MB; not read" % (sm, SITEMAP_MAX_BYTES // (1024 * 1024)))
                continue
        # A web page or another kind of document at a start address means no sitemap lives
        # there. Anywhere else, and for anything that could not be read whole, it is a gap.
        kind, locs, why = parse_sitemap(body)
        if why or kind not in ("urlset", "sitemapindex"):
            if not why and sm in first:
                absent.append("sitemap %s: %s, not a sitemap" % (sm, "a web page" if kind == "page" else "another kind of document"))
            else:
                broken.append("sitemap %s: %s; not read" % (sm, why or "not a sitemap"))
            continue
        if kind == "sitemapindex":
            queue.extend(urllib.parse.urljoin(sm, x) for x in locs)
        else:
            files.append({"url": resp.url, "urls": locs})
    if queue:
        broken.append("more than %s sitemap files: %s were not read" % (MAX_SITEMAP_FILES, len(queue)))
    return files


def inventory(start: str, delay: float, timeout: float, max_requests: int, user_agent: str) -> Tuple[Optional[dict], str]:
    """(data, "") or (None, why the run could not start)."""
    if not web_address(start):
        return None, "not a web address: %s" % start
    p = urllib.parse.urlsplit(start)
    base = urllib.parse.urlunsplit((p.scheme, p.netloc, p.path if p.path.endswith("/") else p.path + "/", "", ""))
    fetcher = Fetcher(base, delay, timeout, max_requests, user_agent)
    notes: List[str] = []  # worth knowing
    gaps: List[str] = []   # what makes the count incomplete
    moved: List[str] = []
    home = None
    for _ in range(3):  # the start address may redirect to the site's real host, once or twice
        stop = fetcher.load_robots(base)
        if stop:
            return None, stop
        home = fetcher.get(base)
        if not home.redirect_to:
            break
        t = urllib.parse.urlsplit(home.redirect_to)
        moved.append("%s redirects to %s" % (base, home.redirect_to))
        base = urllib.parse.urlunsplit((t.scheme, t.netloc, t.path if t.path.endswith("/") else t.path + "/", "", ""))
        fetcher.origin = origin_of(base)
    home_problem = home.problem() if home is not None else "no answer"
    if home is None or home.redirect_to or home.status == 0:
        return None, "the home page could not be read at %s (%s)" % (base, home_problem)
    site_host = fetcher.origin[1]
    home_html = "" if home_problem else home.text()
    if home_problem:
        gaps.append("home page: %s" % home_problem)

    tech = {
        "html_lang": (re.search(r"<html[^>]*\blang=[\"']([^\"']+)", home_html, re.I) or [None, ""])[1],
        "hreflang_links": len(re.findall(r"<link[^>]+hreflang=", home_html, re.I)),
        "generator": sorted(set(re.findall(r"<meta[^>]+name=[\"']generator[\"'][^>]*content=[\"']([^\"']+)", home_html, re.I))),
        "themes": sorted(set(re.findall(r"/wp-content/themes/([A-Za-z0-9_.-]+)/", home_html))),
        "plugins_seen_on_home_page": sorted(set(re.findall(r"/wp-content/plugins/([A-Za-z0-9_.-]+)/", home_html))),
        "rest_namespaces": [],
    }

    # --- the REST API: its root is announced on the home page; /wp-json/ is the default
    m = re.search(r"<link[^>]+rel=[\"']https://api\.w\.org/[\"'][^>]*href=[\"']([^\"']+)", home_html, re.I)
    root = urllib.parse.urljoin(base, html.unescape(m.group(1))) if m else urllib.parse.urljoin(base, "wp-json/")
    if origin_of(root) != fetcher.origin:
        notes.append("the REST API is announced on another host (%s), not asked" % urllib.parse.urlsplit(root).netloc)
        root = urllib.parse.urljoin(base, "wp-json/")
    rest = Rest(root)
    types: List[dict] = []
    taxonomies: List[dict] = []
    records: List[dict] = []
    media = users = comments = None
    site_name = ""
    index, problem = as_json(fetcher.get(rest.url("")))
    rest_ok = isinstance(index, dict) and "namespaces" in index
    if not rest_ok:
        gaps.append("REST API at %s: %s" % (rest.url(""), problem or "not a WordPress REST index"))
    else:
        site_name = str(index.get("name") or "")
        tech["rest_namespaces"] = sorted(str(n) for n in index.get("namespaces", []) if n not in CORE_NAMESPACES)
        tdata, problem = as_json(fetcher.get(rest.url("wp/v2/types")))
        if not isinstance(tdata, dict):
            gaps.append("content types: %s" % (problem or "unexpected answer"))
            tdata = {}
        for slug, info in sorted(tdata.items()):
            if slug in INTERNAL_TYPES or not isinstance(info, dict) or not info.get("rest_base"):
                continue
            types.append(read_type(fetcher, rest, slug, info, site_host, records))
        xdata, problem = as_json(fetcher.get(rest.url("wp/v2/taxonomies")))
        if not isinstance(xdata, dict):
            gaps.append("taxonomies: %s" % (problem or "unexpected answer"))
            xdata = {}
        for slug, info in sorted(xdata.items()):
            if not isinstance(info, dict) or not info.get("rest_base") or slug in ("nav_menu", "wp_pattern_category"):
                continue
            total, problem = count_only(fetcher, rest, "wp/v2/" + str(info["rest_base"]))
            taxonomies.append({"taxonomy": slug, "name": str(info.get("name") or slug), "terms": total, "note": problem,
                               "for_types": [str(t) for t in info.get("types", [])]})
        media, problem = count_only(fetcher, rest, "wp/v2/media")
        if problem:
            gaps.append("media: %s" % problem)
        users, _ = count_only(fetcher, rest, "wp/v2/users")  # a refusal here is the good case
        comments, _ = count_only(fetcher, rest, "wp/v2/comments")

    # --- the sitemap: robots.txt names it, else the usual addresses
    named = []
    here = urllib.parse.urlsplit(base)
    for sm in (fetcher.robots.sitemaps if fetcher.robots else []):
        t = urllib.parse.urlsplit(urllib.parse.urljoin(base, sm))
        if (web_address(t.geturl()) and bare_host(t.hostname) == bare_host(here.hostname)
                and (t.port == here.port or {t.port, here.port} <= {None, 80, 443})):
            # the same site under its other spelling (http for https, with or without www): ask it here
            t = t._replace(scheme=here.scheme, netloc=here.netloc)
        named.append(t.geturl())
    broken: List[str] = []
    absent: List[str] = []
    files = read_sitemaps(fetcher, named, broken, absent) if named else []
    gaps.extend(broken + absent)  # an address robots.txt names has to hold a sitemap
    if not files:
        for guess in ("sitemap_index.xml", "wp-sitemap.xml", "sitemap.xml"):
            broken, absent = [], []
            files = read_sitemaps(fetcher, [urllib.parse.urljoin(base, guess)], broken, absent)
            gaps.extend(broken)  # refused, busy or damaged is a gap; "not found" at a guessed address is not
            if files:
                break
    if not rest_ok and not files:
        return None, "neither a WordPress REST API nor a sitemap was found at %s (%s)" % (base, "; ".join(gaps) or "no answer")

    # --- compare the two
    rest_by_key = {r["key"]: r for r in records}
    sm_keys: Dict[str, str] = {}
    sm_files = []
    for f in files:
        keys = [path_key(u, site_host) for u in f["urls"]]
        for k, u in zip(keys, f["urls"]):
            sm_keys.setdefault(k, u)
        known = collections.Counter(rest_by_key[k]["type"] for k in keys if k in rest_by_key)
        sm_files.append({"url": f["url"], "urls": len(f["urls"]), "matched_by_type": dict(known),
                         "not_in_rest": sum(1 for k in keys if k not in rest_by_key)})
    only_sitemap = sorted(k for k in sm_keys if k not in rest_by_key)
    groups = collections.Counter((k.strip("/").split("/")[0] if k.startswith("/") and k.count("/") > 1 else "(top level)")
                                 for k in only_sitemap)
    only_rest = collections.Counter(r["type"] for k, r in rest_by_key.items() if k not in sm_keys) if files else collections.Counter()

    problems = [e for e in fetcher.log if e["problem"]]
    incomplete = []
    if fetcher.cap_hit:
        incomplete.append("the request limit of %s was reached; raise --max-requests" % max_requests)
    incomplete += ["%s: %s" % (t["type"], t["note"]) for t in types if not t["complete"]]
    incomplete += ["%s: %s" % (x["taxonomy"], x["note"]) for x in taxonomies if x["note"]]
    incomplete += gaps
    data = {
        "schema_version": 1,
        "site": base, "site_name": site_name, "moved": moved,
        "complete": not incomplete, "incomplete_because": incomplete,
        "rest_api": rest_ok, "types": types, "taxonomies": taxonomies,
        "media_items": media, "public_user_records": users, "comments": comments,
        "sitemap": {"files": sm_files, "urls": sum(f["urls"] for f in sm_files), "distinct": len(sm_keys),
                    "only_in_sitemap": len(only_sitemap), "only_in_sitemap_by_first_segment": dict(groups.most_common(40)),
                    "in_rest_not_in_sitemap_by_type": dict(only_rest)},
        "technology": tech, "notes": notes,
        "requests": {"made": fetcher.count, "with_a_problem": problems},
        "_rows": _rows(records, sm_keys),
    }
    return data, ""


def _rows(records: List[dict], sm_keys: Dict[str, str]) -> List[dict]:
    rows = []
    for r in records:
        rows.append({"url": r["url"], "source": "both" if r["key"] in sm_keys else "rest", "type": r["type"], "id": r["id"],
                     "modified": r["modified"], "words": r["words"], "language_guess": r["language"],
                     "builders": "; ".join(r["builders"]), "raw_shortcodes": "; ".join(sorted(r["raw_shortcodes"])),
                     "forms": "; ".join(r["forms"]), "iframes": r["iframes"]})
    have = {r["key"] for r in records}
    rows += [{"url": u, "source": "sitemap"} for k, u in sorted(sm_keys.items()) if k not in have]
    return rows


CSV_FIELDS = ["url", "source", "type", "id", "modified", "words", "language_guess", "builders", "raw_shortcodes", "forms", "iframes"]


def render(d: dict) -> str:
    L: List[str] = []
    add = L.append
    add("# WordPress inventory: %s" % md(d["site_name"] or d["site"]))
    add("")
    add("Site: %s. Counted from the outside, read-only, in %s requests." % (md(d["site"]), d["requests"]["made"]))
    for m in d["moved"]:
        add("Note: %s." % md(m, 300))
    add("")
    if d["complete"]:
        add("**The count is complete** for everything the site shows the public.")
    else:
        add("**The count is incomplete.** Do not base an estimate on it until these are cleared:")
        add("")
        L.extend("- %s" % md(x, 300) for x in d["incomplete_because"])
    add("")
    add("## Content")
    add("")
    if not d["rest_api"]:
        add("The site's REST API did not answer, so records could not be counted; the sitemap below is all there is.")
    else:
        add("| Content type | Published records | Read | Median words | Last change | Left as raw shortcode text | With a form |")
        add("|---|---|---|---|---|---|---|")
        for t in d["types"]:
            add("| %s (`%s`) | %s | %s | %s | %s | %s | %s |" % (
                md(t["name"]), md(t["type"]), "?" if t["total"] is None else t["total"], t["fetched"],
                t["words_median"], t["last_modified"] or "", t["records_with_raw_shortcodes"],
                t["records_with_forms"]))
        add("")
        for t in d["types"]:
            bits = []
            if t["by_year"]:
                bits.append("published by year: " + ", ".join("%s %s" % kv for kv in t["by_year"].items()))
            if t["builders"]:
                bits.append("page-builder marks: " + ", ".join("%s in %s" % kv for kv in t["builders"].items()))
            if t["raw_shortcodes"]:
                bits.append("raw shortcodes: " + ", ".join("%s ×%s" % (md(k), n) for k, n in t["raw_shortcodes"].items()))
            if t["forms"]:
                bits.append("forms: " + ", ".join("%s in %s" % kv for kv in t["forms"].items()))
            if t["records_with_iframes"]:
                bits.append("embeds (iframes) in %s" % t["records_with_iframes"])
            if set(t["languages"]) - {"unknown"}:
                bits.append("language guess: " + ", ".join("%s %s" % kv for kv in t["languages"].items()))
            if t["note"]:
                bits.append("NOT COMPLETE: " + md(t["note"], 300))
            if bits:
                add("- **%s**: %s." % (md(t["name"]), "; ".join(bits)))
        add("")
        add("Media items: %s. Comments: %s." % (_n(d["media_items"]), _n(d["comments"])))
        if d["taxonomies"]:
            add("")
            add("Groupings: " + ", ".join("%s %s (for %s)" % (md(x["name"]), _n(x["terms"]), md(", ".join(x["for_types"])))
                                          for x in d["taxonomies"]) + ".")
    add("")
    add("## Sitemap")
    add("")
    sm = d["sitemap"]
    if not sm["files"]:
        add("No sitemap was found.")
    else:
        add("%s addresses in %s files (%s distinct)." % (sm["urls"], len(sm["files"]), sm["distinct"]))
        add("")
        add("| Sitemap file | Addresses | Not explained by a counted record |")
        add("|---|---|---|")
        L.extend("| %s | %s | %s |" % (md(f["url"]), f["urls"], f["not_in_rest"]) for f in sm["files"])
        add("")
        if sm["only_in_sitemap"]:
            add("%s sitemap addresses belong to no counted record. A plugin or a listing page usually stands "
                "behind them, and each group needs a decision. By first part of the address: %s."
                % (sm["only_in_sitemap"], ", ".join("%s %s" % (md(k), n) for k, n in sm["only_in_sitemap_by_first_segment"].items())))
        if sm["in_rest_not_in_sitemap_by_type"]:
            add("")
            add("Published but left out of the sitemap (hidden from search on purpose, redirects, or forgotten): %s."
                % ", ".join("%s %s" % (md(k), n) for k, n in sm["in_rest_not_in_sitemap_by_type"].items()))
    add("")
    add("## What the site is built with")
    add("")
    t = d["technology"]
    add("- Theme: %s" % (md(", ".join(t["themes"])) or "not visible on the home page"))
    add("- Plugins visible on the home page: %s" % (md(", ".join(t["plugins_seen_on_home_page"]), 600) or "none"))
    add("- Plugins that add to the REST API: %s" % (md(", ".join(t["rest_namespaces"]), 900) or "none"))
    add("- Language the home page declares: %s; links to other language versions: %s" % (md(t["html_lang"]) or "none", t["hreflang_links"]))
    if d["public_user_records"]:
        add("- The site lists %s user records to anyone who asks. Worth telling its owner." % d["public_user_records"])
    add("")
    add("## What this count cannot see")
    add("")
    add("- Drafts, private records and anything behind a login. A password-protected record may be counted, but its text is not read.")
    add("- A content type the site's REST API does not list. WordPress's own internal types (menus, templates, patterns, styles, fonts) are left out on purpose, and media is one number.")
    add("- Content a plugin draws inside a page, such as a directory shown in pop-ups: it counts as one page.")
    add("- Fields a plugin keeps to itself, such as a session's start time or its speakers.")
    add("- The media files themselves, redirects set inside WordPress, and form entries.")
    add("")
    add("These need the site's backup or a login.")
    if d["notes"]:
        add("")
        add("## Notes from the run")
        add("")
        L.extend("- %s" % md(n, 400) for n in d["notes"])
    return "\n".join(L) + "\n"


def _n(v) -> str:
    return "not readable" if v is None else str(v)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Count what a live WordPress site holds, from the outside. Read-only.")
    ap.add_argument("site", help="the site's address, e.g. https://example.com")
    ap.add_argument("--out", default="wordpress-inventory", help="folder for inventory.md, inventory.json and urls.csv")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default 1)")
    ap.add_argument("--timeout", type=float, default=30.0, help="seconds to wait for one answer (default 30)")
    ap.add_argument("--max-requests", type=int, default=100, help="stop after this many requests (default 100)")
    ap.add_argument("--user-agent", default=USER_AGENT,
                    help="the name sent with each request (robots.txt is still read under the name %s)" % ROBOTS_TOKEN)
    args = ap.parse_args(argv)
    data, stop = inventory(args.site, max(args.delay, 0.0), args.timeout, max(args.max_requests, 1), args.user_agent)
    if data is None:
        print("wp_inventory: %s" % stop, file=sys.stderr)
        return 2
    rows = data.pop("_rows")
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "inventory.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(args.out, "inventory.md"), "w", encoding="utf-8") as fh:
        fh.write(render(data))
    with open(os.path.join(args.out, "urls.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({k: safe_cell(row.get(k, "")) for k in CSV_FIELDS})
    for t in data["types"]:
        print("%-28s %s" % (t["type"], "?" if t["total"] is None else t["total"]))
    print("%-28s %s" % ("sitemap addresses", data["sitemap"]["urls"]))
    print("%s: %s" % ("complete" if data["complete"] else "INCOMPLETE", os.path.join(args.out, "inventory.md")))
    for why in data["incomplete_because"]:
        print("  - %s" % why)
    return 0 if data["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
