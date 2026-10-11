#!/usr/bin/env python3
"""
facts_check.py — compare every figure on a live site with one list of approved facts,
and check that every page still carries the positioning term it owns.

Read-only. It reads the site's sitemap (or a page list), fetches each page once, finds
every number that names a fact ("27,000+ agents", "NPS of 72", "35 languages") in the
visible text, the title, the meta and social descriptions and the structured data
(JSON-LD), and reports each one that differs from the approved value. It also reports
phrases the owner has retired ("old name", "old figure") wherever they still appear.
It changes nothing on the site.

Standard library only (Python 3.9+), so it runs on a stock python3 with no installs.

Usage:
  python3 facts_check.py --init facts.json          # write a starter facts file
  python3 facts_check.py facts.json                 # check, print the report
  python3 facts_check.py facts.json --out report.md --json report.json \
      --history history.csv                         # the weekly run

Exit codes: 0 every mention matches, 1 at least one finding (mismatch, outdated value or
retired phrase), 2 the run could not start (bad facts file, no pages to read).

How a number is tied to a fact (the rules SKILL.md explains to the owner):
  - after:  one of the fact's `terms` follows the number within `window` words
            (default 4), with no other number or sentence end in between:
            "27,000+ vetted agents" -> term "agent".
            A term matches any word that starts with it ("agent" matches "agents").
  - before: one of the fact's `before` phrases ends right before the number:
            "an NPS of 72" -> before phrase "NPS of".
  - unit:   "%" ties only percentages to the fact; "" (default) only plain numbers.
  - A comma, full stop or other sentence mark ends the search, so "in 60 countries,
    clients ..." does not tie 60 to clients.
  - A plain year (1900 to 2100 right after "in", "since", "seit", "founded", a month, ... or ©)
    is ignored for a fact whose own value is not a year, and a zero for a fact whose own
    value is not 0, so "founded in 2016 clients ..." and a count-up that starts at 0 are
    not client numbers; "über 2000 Kunden" is.
  - A minus sign counts: "NPS of -5" is minus five, not five. A hyphen between things
    ("5-10", "2024-10-09", "COVID-19") is no sign.
Each tied number is OK (the approved value or one in `also_accept`), OUTDATED (in
`retired`) or MISMATCH (anything else).

Positioning (optional `positioning` block): rules map address paths (`/en/business/*`) to
an audience and a term. The term must appear in the <title>, the meta description and the
<h1> or intro paragraph, the rule the starter's tests/positioning.spec.ts enforces; or
clauses per surface (title, desc, h1, body), each a phrase or a list of alternatives. The
first matching rule wins. A page that lost its term is a finding; a page with no rule and
not exempt is listed as a warning.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import email.message
import fnmatch
import gzip
import http.client
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

USER_AGENT = "facts-check/1.0 (read-only site consistency check)"
MAX_BYTES = 5 * 1024 * 1024
MAX_ADDRESS = 8000  # bytes as the address travels: RFC 9110 (4.1) asks recipients for 8000 octets at least, and many servers refuse more
SITEMAP_MAX_BYTES = 52 * 1024 * 1024  # the protocol allows 50 MB, uncompressed
MAX_SITEMAP_FILES = 200  # sitemap files read in one run: a guard against loops and endless indexes
REDIRECT_BLOCKED = -1  # Fetcher.get status: a redirect led to an address robots.txt does not allow
DEFAULT_WINDOW = 4

# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

# Grouped thousands (27,000 / 27.000 / 27 000 with a no-break, narrow or thin space;
# a plain space does not group, or "our 5 120 clients" would read as 5120)
# or a plain run of digits; then an optional decimal part; then an optional
# multiplier, plus sign and percent. The lookbehind keeps a match from starting
# inside a word or inside another number. A minus sign (hyphen or U+2212) right before
# the digits is part of the number unless it follows a word character, a digit, a full
# stop, a comma, a slash or a plus: "NPS of -5" is minus five; "5-10", "2024-10-09",
# "COVID-19" and "+/-3%" have no sign.
NUM_RE = (
    r"(?:(?<![\w.,/+\u00b1])(?P<sign>[-\u2212])(?=\d))?"
    r"(?<![\w.,])"
    r"(?P<int>\d{1,3}(?:[,.\u00a0\u202f\u2009]\d{3})+(?!\d)|\d+)"
    r"(?P<dec>[.,]\d+(?!\d))?"
    r"(?:[\u00a0 ]?(?P<mult>k|K|Tsd\.|M|Mio\.?|Mrd\.?|[Mm]illions?|Millionen|"
    r"[Bb]illions?|Milliarden?|bn)(?!\w))?"
    r"(?P<plus>[\u00a0 ]?\+)?"
    r"(?P<pct>[\u00a0 ]?%)?"
)
WORD_RE = r"[^\W\d_]+(?:['\u2019\-][^\W\d_]+)*"
STOP_RE = r"[.!?;,](?=\s|$)|[|\u2022\u00b7]"
TOKEN_RE = re.compile(
    "(?P<num>%s)|(?P<word>%s)|(?P<stop>%s)" % (NUM_RE, WORD_RE, STOP_RE)
)

# A plain number from 1900 to 2100 right after one of these words (or after ©) is read
# as a year and not tied to a fact that is not itself a year: "founded in 2016",
# "seit 2010". Without such a word it is a count: "über 2000 Kunden".
YEAR_CUES = {
    "in", "since", "until", "till", "founded", "established", "est", "year", "copyright",
    "im", "seit", "bis", "ab", "jahr", "gegründet", "gegruendet",
    # a date: "27 March 2026", "im Herbst 2025"
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
    "januar", "jänner", "februar", "märz", "mai", "juni", "juli", "oktober", "dezember",
    "spring", "summer", "autumn", "fall", "winter", "frühjahr", "frühling", "sommer", "herbst",
}

MULTIPLIERS = {
    "k": 1e3, "K": 1e3, "Tsd.": 1e3,
    "M": 1e6, "Mio": 1e6, "Mio.": 1e6, "million": 1e6, "millions": 1e6,
    "Million": 1e6, "Millions": 1e6, "Millionen": 1e6,
    "Mrd": 1e9, "Mrd.": 1e9, "billion": 1e9, "billions": 1e9, "Billion": 1e9,
    "Billions": 1e9, "Milliarde": 1e9, "Milliarden": 1e9, "bn": 1e9,
}


def parse_number(m: "re.Match") -> Tuple[float, bool]:
    """Value of a NUM match, and whether it was written plainly (no sign, grouping,
    decimals, multiplier, plus or percent): only a plain number can be a year."""
    raw_int = m.group("int")
    digits = re.sub(r"[,.\u00a0\u202f\u2009 ]", "", raw_int)
    value = float(digits)
    dec = m.group("dec")
    if dec:
        value += float("0." + dec[1:])
    mult = m.group("mult")
    if mult:
        value *= MULTIPLIERS[mult]
    plain = (digits == raw_int and not dec and not mult
             and not m.group("plus") and not m.group("pct") and not m.group("sign"))
    if m.group("sign"):
        value = -value
    return value, plain


def same(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


# ---------------------------------------------------------------------------
# Facts file
# ---------------------------------------------------------------------------

STARTER = {
    "site": "https://example.com",
    "sitemap": "",
    "pages": [],
    "extra_urls": [],
    "facts": [
        {
            "id": "clients",
            "label": "Number of clients",
            "value": 120,
            "unit": "",
            "terms": ["client", "customer"],
            "before": [],
            "also_accept": [100],
            "retired": [70],
            "source": "[where the approved value comes from]",
            "owner": "[who confirms it]",
            "checked": "[date it was last confirmed]",
        },
        {
            "id": "customer-nps",
            "label": "Customer NPS",
            "value": 72,
            "unit": "",
            "terms": [],
            "before": ["NPS of", "NPS score of", "NPS"],
            "also_accept": [],
            "retired": [],
            "source": "[where the approved value comes from]",
            "owner": "[who confirms it]",
            "checked": "[date it was last confirmed]",
        },
    ],
    "retired_phrases": [
        {"text": "[an old product name or claim]", "note": "[why it is retired]"}
    ],
    "positioning": {
        "rules": [
            {"pages": "/", "audience": "[buyers]", "term": "[the term the home page owns]"},
            {"pages": ["/en/careers", "/en/careers/*"], "audience": "[applicants]",
             "term": "[the term the careers pages own]"},
        ],
        "exempt": ["/privacy", "/imprint"],
    },
}


class FactsError(Exception):
    pass


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def load_facts(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FactsError("no facts file at %s (create one with --init)" % path)
    except json.JSONDecodeError as e:
        raise FactsError("%s is not valid JSON: %s" % (path, e))
    problems: List[str] = []
    if not isinstance(data, dict):
        raise FactsError("%s must hold one JSON object" % path)
    site = data.get("site", "")
    if not isinstance(site, str) or not re.match(r"https?://[^/\s]+", site) or bad_address(site):
        problems.append('"site" must be the site\'s address, e.g. "https://example.com"')
    sitemap = data.get("sitemap", "")
    if sitemap and (not isinstance(sitemap, str) or bad_address(sitemap)):
        problems.append('"sitemap" must be a full address (https://...)')
    facts = data.get("facts", [])
    if facts is None:
        facts = []
    if not isinstance(facts, list):
        problems.append('"facts" must be a list of facts')
        facts = []
    problems.extend(_positioning_problems(data.get("positioning")))
    pos = data.get("positioning")
    has_rules = isinstance(pos, dict) and isinstance(pos.get("rules"), list) and bool(pos["rules"])
    if not facts and not data.get("retired_phrases") and not has_rules:
        problems.append('nothing to check: add "facts", "retired_phrases" or "positioning" rules')
    seen = set()
    for i, fact in enumerate(facts):
        where = "fact %d" % (i + 1)
        if not isinstance(fact, dict):
            problems.append("%s is not an object" % where)
            continue
        fid = fact.get("id")
        if not isinstance(fid, str) or not fid.strip():
            problems.append('%s needs an "id"' % where)
        else:
            where = 'fact "%s"' % fid
            if fid in seen:
                problems.append("%s appears twice" % where)
            seen.add(fid)
        if not _num(fact.get("value")):
            problems.append('%s needs a numeric "value" (write 27000, not "27,000+")' % where)
        if fact.get("unit", "") not in ("", "%"):
            problems.append('%s: "unit" is "" or "%%"' % where)
        terms = fact.get("terms", [])
        before = fact.get("before", [])
        for key, val in (("terms", terms), ("before", before)):
            if not isinstance(val, list) or not all(isinstance(t, str) and t.strip() for t in val):
                problems.append('%s: "%s" must be a list of words or phrases' % (where, key))
        if isinstance(terms, list) and isinstance(before, list) and not terms and not before:
            problems.append('%s needs "terms" or "before", or no number can be tied to it' % where)
        for key in ("also_accept", "retired"):
            val = fact.get(key, [])
            if not isinstance(val, list) or not all(_num(v) for v in val):
                problems.append('%s: "%s" must be a list of numbers' % (where, key))
        retired = fact.get("retired", [])
        if _num(fact.get("value")) and isinstance(retired, list) and any(
                _num(v) and same(v, fact["value"]) for v in retired):
            problems.append("%s: the approved value is also listed as retired" % where)
        w = fact.get("window", DEFAULT_WINDOW)
        if not isinstance(w, int) or isinstance(w, bool) or not 1 <= w <= 12:
            problems.append('%s: "window" must be a whole number from 1 to 12' % where)
    phrases = data.get("retired_phrases", []) or []
    if not isinstance(phrases, list):
        problems.append('"retired_phrases" must be a list of phrases, each with a "text"')
        phrases = []
    for i, rp in enumerate(phrases):
        if not isinstance(rp, dict) or not isinstance(rp.get("text"), str) or not rp["text"].strip():
            problems.append('retired phrase %d needs a "text"' % (i + 1))
    for key in ("pages", "extra_urls"):
        val = data.get(key, []) or []
        if not isinstance(val, list) or not all(isinstance(u, str) and u.strip().startswith(("http://", "https://")) for u in val):
            problems.append('"%s" must be a list of full addresses (https://...)' % key)
        elif val:
            data[key] = [u.strip() for u in val]  # a pasted address may end in a space or a line break
    if problems:
        raise FactsError("%s has problems:\n  - %s" % (path, "\n  - ".join(problems)))
    data["facts"] = facts
    return data


SURFACES = ("title", "desc", "h1", "body")


def _clause_ok(c) -> bool:
    if isinstance(c, str):
        return bool(c.strip())
    return isinstance(c, list) and bool(c) and all(isinstance(x, str) and x.strip() for x in c)


def _patterns(rule: dict) -> List[str]:
    p = rule.get("pages")
    return [p] if isinstance(p, str) else list(p or [])


def _positioning_problems(pos) -> List[str]:
    if pos is None:
        return []
    if not isinstance(pos, dict) or not isinstance(pos.get("rules"), list):
        return ['"positioning" must be an object with a list of "rules"']
    problems = []
    for i, r in enumerate(pos["rules"]):
        where = "positioning rule %d" % (i + 1)
        if not isinstance(r, dict):
            problems.append("%s is not an object" % where)
            continue
        pats = r.get("pages")
        if not (isinstance(pats, str) or isinstance(pats, list)) or not _patterns(r) or not all(
                isinstance(x, str) and x.startswith("/") for x in _patterns(r)):
            problems.append('%s: "pages" must be an address path or a list of them, '
                            'each starting with "/" (a * matches any rest: "/en/business/*")' % where)
        if "audience" in r and not isinstance(r["audience"], str):
            problems.append('%s: "audience" must be a name' % where)
        if "term" in r:
            if not isinstance(r["term"], str) or not r["term"].strip():
                problems.append('%s: "term" must be a phrase' % where)
            if any(k in r for k in ("title", "desc", "h1")):
                problems.append('%s: use "term" or "title"/"desc"/"h1", not both' % where)
        elif not any(r.get(k) for k in ("title", "desc", "h1", "body")):
            problems.append('%s needs a "term", or clauses for "title", "desc", "h1" or "body"' % where)
        for k in SURFACES:
            if k in r and (not isinstance(r[k], list) or not all(_clause_ok(c) for c in r[k])):
                problems.append('%s: "%s" must be a list of phrases, each a phrase or a list '
                                'of alternatives' % (where, k))
    ex = pos.get("exempt", [])
    if not isinstance(ex, list) or not all(isinstance(x, str) and x.startswith("/") for x in ex):
        problems.append('"positioning" "exempt" must be a list of address paths starting with "/"')
    return problems


# ---------------------------------------------------------------------------
# Finding mentions in text
# ---------------------------------------------------------------------------

def _phrase_words(phrase: str) -> List[str]:
    return [w.lower() for w in re.findall(WORD_RE, phrase)]


def _word_matches(word: str, term: str) -> bool:
    return word.startswith(term)


def tokenize(text: str):
    return [(m.lastgroup, m) for m in TOKEN_RE.finditer(text)]


def find_mentions(text: str, fact: dict) -> List[dict]:
    """Every number in `text` that the fact's rules tie to it."""
    value = float(fact["value"])
    unit = fact.get("unit", "")
    window = fact.get("window", DEFAULT_WINDOW)
    terms = [_phrase_words(t) for t in fact.get("terms", [])]
    terms = [t for t in terms if t]
    befores = [_phrase_words(p) for p in fact.get("before", [])]
    befores = [b for b in befores if b]
    fact_is_year = 1900 <= value <= 2100
    tokens = tokenize(text)
    out = []
    for i, (kind, m) in enumerate(tokens):
        if kind != "num":
            continue
        is_pct = bool(m.group("pct"))
        if (unit == "%") != is_pct:
            continue
        num, plain = parse_number(m)
        if plain and 1900 <= num <= 2100 and not fact_is_year:
            prev = tokens[i - 1][1].group(0).lower() if i > 0 and tokens[i - 1][0] == "word" else ""
            if prev in YEAR_CUES or text[max(0, m.start() - 3):m.start()].strip().endswith("\u00a9"):
                continue
        if num == 0 and value != 0:
            continue
        tied = False
        # after: a term within `window` words, before another number or a stop
        after_words: List[str] = []
        j = i + 1
        while j < len(tokens) and tokens[j][0] == "word" and len(after_words) < window:
            after_words.append(tokens[j][1].group(0).lower())
            j += 1
        for t in terms:
            for s in range(0, len(after_words) - len(t) + 1):
                if all(_word_matches(after_words[s + k], t[k]) for k in range(len(t))):
                    tied = True
                    break
            if tied:
                break
        # before: a phrase that ends right before the number
        if not tied and befores:
            before_words: List[str] = []
            j = i - 1
            while j >= 0 and tokens[j][0] == "word" and len(before_words) < 8:
                before_words.insert(0, tokens[j][1].group(0).lower())
                j -= 1
            for b in befores:
                if len(before_words) >= len(b) and before_words[-len(b):] == b:
                    tied = True
                    break
        if not tied:
            continue
        if same(num, value) or any(same(num, float(v)) for v in fact.get("also_accept", [])):
            status = "OK"
        elif any(same(num, float(v)) for v in fact.get("retired", [])):
            status = "OUTDATED"
        else:
            status = "MISMATCH"
        out.append({
            "status": status,
            "found": m.group(0).strip(),
            "found_value": num,
            "snippet": snippet(text, m.start(), m.end()),
        })
    return out


def snippet(text: str, start: int, end: int, pad: int = 60) -> str:
    a = max(0, start - pad)
    b = min(len(text), end + pad)
    if a > 0:  # start and end on a word boundary
        sp = text.find(" ", a, start)
        a = sp + 1 if sp != -1 else a
    if b < len(text):
        sp = text.rfind(" ", end, b)
        b = sp if sp != -1 else b
    left = ("\u2026" if a > 0 else "") + text[a:start]
    right = text[end:b] + ("\u2026" if b < len(text) else "")
    s = left + "**" + text[start:end].strip() + "**" + right
    return re.sub(r"\s+", " ", s).strip()


def find_phrases(text: str, phrase: str) -> List[str]:
    norm = re.sub(r"\s+", " ", text)
    p = re.sub(r"\s+", " ", phrase.strip())
    out = []
    for m in re.finditer(re.escape(p), norm, re.IGNORECASE):
        out.append(snippet(norm, m.start(), m.end()))
    return out


# ---------------------------------------------------------------------------
# Reading pages
# ---------------------------------------------------------------------------

BLOCK_TAGS = {
    "p", "div", "li", "ul", "ol", "dt", "dd", "h1", "h2", "h3", "h4", "h5", "h6",
    "td", "th", "tr", "br", "section", "article", "header", "footer", "main",
    "nav", "aside", "figure", "figcaption", "blockquote", "span", "a", "button",
    "label", "summary", "details",
}  # inline formatting (b, i, strong, em, ...) is not here: "<b>27</b>,000" stays 27,000
# Start tags that close an open <p> (the HTML rule for an omitted </p>).
P_CLOSERS = {
    "address", "article", "aside", "blockquote", "details", "dialog", "div", "dl", "fieldset",
    "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header",
    "hgroup", "hr", "main", "menu", "nav", "ol", "p", "pre", "search", "section", "table", "ul",
}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
             "param", "source", "track", "wbr"}
SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "iframe", "canvas"}
# Inline elements that still separate words (<span>27</span><span>agents</span> is "27 agents"),
# but not where a tag cuts a number: "<span>27</span>,000" is 27,000. They write a soft
# space that resolve_soft() settles once the whole text is known.
SOFT_TAGS = {"span", "a", "button", "label"}
SOFT = "\u2063"


def resolve_soft(text: str) -> str:
    # A soft space is a space, except where a tag cuts a number: "27</span>,000", "27,</span><span>000",
    # "27</span>,<span>000" and "29</span>.99" are 27,000 and 29.99 (but "Q2</span>,000" is not 2,000: the
    # digits must be a whole number, not the end of a word). A minus sign in an element of its
    # own belongs to the digits after it, unless it sits between two things ("5</span>-</span>10"),
    # and a dash that opens an element after a whole number is a range ("5</span><span>-10"; not "Q2</span><span>-5").
    # (Two list numbers in adjacent spans, "1." and "2", would join; lists use <li>, a hard space.)
    text = re.sub(r"(?<![\w.,])\d+(?:%s*[.,]%s*\d+)+" % (SOFT, SOFT), lambda m: m.group(0).replace(SOFT, ""), text)
    text = re.sub(r"(?<![\w.,])(\d+(?:[.,]\d+)*)%s+(?=[-\u2212]\d)" % SOFT, r"\1", text)   # 5</span><span>-10 is a range

    def sign(m):
        i = m.start() - 1
        while i >= 0 and text[i] == SOFT:
            i -= 1
        return m.group(0) if i >= 0 and re.match(r"[\w.,/+\u00b1]", text[i]) else m.group(1)

    text = re.sub(r"([-\u2212])%s+(?=\d)" % SOFT, sign, text)
    return text.replace(SOFT, " ")


class PageText(HTMLParser):
    """Visible text, title, descriptions and JSON-LD strings of one HTML page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: Dict[str, List[str]] = {
            "page text": [], "title": [], "meta description": [],
            "social description": [], "structured data": [],
            # read for retired phrases (and, except link addresses, for facts): AI
            # crawlers read alt texts, share tags and URLs too
            "image alt text": [], "share title": [], "link addresses": [],
        }
        self._skip = 0
        self._in_title = False
        self._in_ldjson = False
        self._ld_buf: List[str] = []
        # For the positioning check: every <h1>, and the intro, the first <p> of <main>
        # (else of <article>, else of the page), chosen as the starter's positioning test does.
        # Only the first <main> and the first <article> count, and the first <p> in each,
        # as with document.querySelector('main').querySelector('p'). A stack of open
        # elements tells where a <p> ends when its </p> is left out.
        self.h1s: List[str] = []
        self._h1_depth = 0
        self._h1_buf: List[str] = []
        self._titles = 0
        self._stack: List[str] = []
        self._first_at: Dict[str, Optional[int]] = {"main": None, "article": None}
        self._saw = {"main": False, "article": False}
        self.first_p: Dict[str, Optional[str]] = {"main": None, "article": None, "body": None}
        self._p_buf: Optional[List[str]] = None
        self._p_at: Optional[int] = None
        self._p_slots: List[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "script" and a.get("type", "").lower() == "application/ld+json" and not self._skip:
            self._in_ldjson = True
            self._ld_buf = []
            return
        if tag in SKIP_TAGS:
            self._skip += 1
            return
        if self._skip:
            # inside <template>, <noscript>, <svg>...: no structure the page shows, and
            # no paragraph for the intro (querySelector does not see these either)
            return
        if tag == "img" and a.get("alt", "").strip():
            self.parts["image alt text"].append(a["alt"])
        if tag in ("a", "area", "link") and a.get("href", "").strip():
            self.parts["link addresses"].append(a["href"])
        if self._p_at is not None and tag in P_CLOSERS:
            self._close_to(self._p_at)  # a <p> closed implicitly by the next block
        if tag in ("li", "dd", "dt"):  # a new item closes the open one, and a <p> in it
            fence = {"li": ("ul", "ol", "menu"), "dd": ("dl",), "dt": ("dl",)}[tag]
            for i in range(len(self._stack) - 1, -1, -1):
                if self._stack[i] in fence:
                    break
                if self._stack[i] in (("li",) if tag == "li" else ("dd", "dt")):
                    self._close_to(i)
                    break
        if tag in self._first_at and not self._saw[tag]:
            self._saw[tag] = True
            self._first_at[tag] = len(self._stack)
        elif tag == "h1":
            self._h1_depth += 1
            if self._h1_depth == 1:
                self._h1_buf = []
        elif tag == "p" and self._p_buf is None:
            slots = [k for k in ("main", "article")
                     if self._first_at[k] is not None and self.first_p[k] is None]
            if self.first_p["body"] is None:
                slots.append("body")
            if slots:
                self._p_buf, self._p_slots, self._p_at = [], slots, len(self._stack)
        if tag not in VOID_TAGS:
            self._stack.append(tag)
        if tag == "title":
            self._in_title = True
            self._titles += 1
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            content = a.get("content", "")
            if name == "description":
                self.parts["meta description"].append(content)
            elif name in ("og:description", "twitter:description"):
                self.parts["social description"].append(content)
            elif name in ("og:title", "twitter:title", "og:site_name", "application-name", "author"):
                self.parts["share title"].append(content)
            elif name in ("og:url", "og:image", "twitter:image") and content.strip():
                self.parts["link addresses"].append(content)
        if tag in BLOCK_TAGS:
            self.parts["page text"].append(SOFT if tag in SOFT_TAGS else " ")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in SKIP_TAGS and tag != "script":
            self._skip = max(0, self._skip - 1)

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ldjson:
            self._in_ldjson = False
            self._add_ldjson("".join(self._ld_buf))
            return
        if tag in SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag == "title":
            self._in_title = False
        if tag == "h1" and self._h1_depth:
            self._h1_depth -= 1
            if not self._h1_depth:
                self.h1s.append("".join(self._h1_buf))
        if tag in self._stack:  # an end tag closes its element and everything inside it
            self._close_to(len(self._stack) - 1 - self._stack[::-1].index(tag))
        if tag in BLOCK_TAGS:
            self.parts["page text"].append(SOFT if tag in SOFT_TAGS else " ")

    def handle_data(self, data):
        if self._in_ldjson:
            self._ld_buf.append(data)
        elif self._skip:
            return
        elif self._in_title:
            if self._titles == 1:  # document.title is the first <title> only
                self.parts["title"].append(data)
        else:
            self.parts["page text"].append(data)
            if self._h1_depth:
                self._h1_buf.append(data)
            if self._p_buf is not None:
                self._p_buf.append(data)

    def _close_to(self, i: int):
        """Close the element at stack index i and everything opened inside it."""
        if self._p_at is not None and i <= self._p_at:
            self._end_p()
        for k, at in self._first_at.items():
            if at is not None and i <= at:
                self._first_at[k] = None  # only the first <main>/<article> is ever read
        del self._stack[i:]

    def _end_p(self):
        text = "".join(self._p_buf or [])
        for slot in self._p_slots:
            self.first_p[slot] = text
        self._p_buf, self._p_slots, self._p_at = None, [], None

    def surfaces(self) -> Dict[str, str]:
        """The four places the positioning check reads, as the starter's test reads them."""
        if self._p_buf is not None:
            self._end_p()
        if self._h1_depth:
            self.h1s.append("".join(self._h1_buf))
            self._h1_depth = 0
        box = "main" if self._saw["main"] else "article" if self._saw["article"] else "body"
        # As the browser gives them to the starter test: document.title strips and collapses
        # ASCII whitespace only (a no-break space stays); the description and the h1/intro
        # text come raw; the body is collapsed, as innerText roughly is.
        title = re.sub(r"[ \t\n\f\r]+", " ", "".join(self.parts["title"])).strip(" \t\n\f\r")
        return {
            "title": title,
            "desc": self.parts["meta description"][0] if self.parts["meta description"] else "",
            "h1": " \u00b7 ".join(self.h1s) + " \u00b7 " + (self.first_p[box] or ""),
            "body": re.sub(r"\s+", " ", resolve_soft("".join(self.parts["page text"]))).strip(),
        }

    def _add_ldjson(self, raw: str):
        try:
            obj = json.loads(raw)
        except ValueError:
            return

        def words(key: str) -> str:
            return re.sub(r"([a-z])([A-Z])", r"\1 \2", key).lower()

        def walk(o, key=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    # {"numberOfEmployees": {"value": 500}}: the value's name is its parent's
                    walk(v, key if k in ("value", "minValue", "maxValue") else k)
            elif isinstance(o, list):
                for v in o:
                    walk(v, key)
            elif isinstance(o, str) and not o.startswith(("http://", "https://")):
                self.parts["structured data"].append(o)
            elif _num(o):
                # "500 number of employees": the property name follows like a term would
                self.parts["structured data"].append("%s %s" % (fmt_value(o), words(key)))

        walk(obj)

    def locations(self) -> Dict[str, str]:
        out = {}
        for k, v in self.parts.items():
            if k == "page text":
                joined = resolve_soft("".join(v))  # block tags already added their spaces
            else:  # og: and twitter: descriptions often repeat one text
                joined = " | ".join(s for s in dict.fromkeys(x.strip() for x in v) if s)
            # No-break spaces stay: they group thousands ("27\u00a0000").
            text = re.sub(r"[ \t\r\n]+", " ", joined).strip()
            if text:
                out[k] = text
        return out


WEB_ONLY = "only web addresses (http, https) are read"


_AUTHORITY = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^/?]*")


def _escape_beyond_ascii(m) -> str:
    try:
        return urllib.parse.quote(m.group(), safe="")
    except UnicodeEncodeError:  # a lone surrogate is no character: left as it is, for bad_address() to refuse
        return m.group()


def clean_address(url: str) -> str:
    """The address as a request sends it: without the #fragment, which no request carries, and stripped
    (Request() unwraps it). The fragment goes first, and at the FIRST "#" (urllib cuts at the last one, which
    would keep text of a second); stripping first would leave the space that stood before the "#". After the
    host, a character beyond ASCII becomes the %XX of its UTF-8 bytes, as a browser sends it: http.client
    refuses it raw ("ordinal not in range(128)"). The host keeps its letters; http.client sends it in IDNA."""
    url = url.split("#", 1)[0].strip()
    if url.isascii():
        return url
    m = _AUTHORITY.match(url)
    head = m.group() if m else ""
    return head + re.sub(r"[^\x00-\x7f]+", _escape_beyond_ascii, url[len(head):])


def bad_address(url: str) -> str:
    """Why this cannot be fetched (not an http or https address, or not an address at all), or ""."""
    url = clean_address(url)
    if re.search("[\ud800-\udfff]", url):
        return "not a valid address (it contains a lone surrogate, which is no character)"
    # As it travels (clean_address() has escaped every byte beyond ASCII after the host, so one emoji takes 12) and as the
    # robots.txt matcher reads it (robots_form() escapes "{" and the like): matching takes time in proportion to this.
    # The cut keeps a gigantic address from being counted.
    if len(url) > MAX_ADDRESS or len(robots_form(url[:MAX_ADDRESS + 1])) > MAX_ADDRESS:
        return "not a valid address (longer than %s bytes)" % format(MAX_ADDRESS, ",")
    if re.search(r"[\x00-\x20\x7f]", url):  # http.client refuses a space or a control character in what it sends
        return "not a valid address (it contains a space or a control character)"
    try:
        p = urllib.parse.urlsplit(url)
        p.port  # raises ValueError for a port out of range
    except ValueError as e:
        return "not a valid address (%s)" % e
    if not p.scheme:
        return "not a valid address (it does not start with http:// or https://)"
    if p.scheme.lower() not in ("http", "https"):
        return WEB_ONLY
    return "" if p.hostname else "not a valid address (no host)"


class _RedirectBlocked(Exception):
    def __init__(self, url: str, why: str, robots: bool):
        super().__init__(url)
        self.url, self.why, self.robots = url, why, robots


class _RedirectGuard(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect to anything but a web address. For page fetches (requests marked
    `guard_robots`), follow one only where robots.txt allows the address it leads to; robots.txt
    and the sitemaps are read wherever they redirect."""

    def __init__(self, fetcher: "Fetcher"):
        self.fetcher = fetcher

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        newurl = clean_address(newurl)  # urllib would request "/about#a%20b" for "Location: /about#a b#c"
        bad = bad_address(newurl)
        if bad:
            fp.close()
            raise _RedirectBlocked(newurl, bad, False)
        guard = getattr(req, "guard_robots", False)
        if guard:
            why = self.fetcher.blocked(newurl)
            if why:
                fp.close()
                raise _RedirectBlocked(newurl, why, True)
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            new.guard_robots = guard  # the next hop is checked too
        return new


def request_target(url: str) -> str:
    """The path and query a request for this address sends ("GET //a?" for "http://x.test//a?"): urllib's own selector, so
    that robots.txt is judged on what the server receives, whatever the address looks like."""
    return urllib.request.Request(url).selector or "/"


ROBOTS_TOKEN = USER_AGENT.split("/")[0].lower()  # the name a robots.txt group calls this tool by
_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
_ESCAPE_OR_ODD = re.compile(r"%[0-9A-Fa-f]{2}|[^A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]")
_LINE_END = re.compile(r"\r\n|\r|\n")
_AGENT_NAME = re.compile(r"[A-Za-z_-]*")


def robots_form(text: str) -> str:
    """A rule or a request path as RFC 9309 (2.2.2) compares them, both alike: a character that is no URI character (any
    non-ASCII one, a space) becomes percent escapes of its UTF-8 bytes, an escape of an unreserved character becomes the
    character ("%7E" is "~"), any other escape gets capital hex digits. "%2F" stays apart from "/": it names a slash that
    is no separator. The other reserved characters (/ ? : & =) are compared as they are written: the RFC's Figure 4 shows
    "https://foo.bar" in a query value as "https%3A%2F%2Ffoo.bar", which Google's own parser does not do either."""
    def one(m):
        s = m.group()
        if len(s) == 3 and s[0] == "%":
            c = chr(int(s[1:], 16))
            return c if c in _UNRESERVED else s.upper()
        return "".join("%%%02X" % b for b in s.encode("utf-8", "replace"))
    return _ESCAPE_OR_ODD.sub(one, text)


def _matches(parts: List[str], anchored: bool, path: str) -> bool:
    """Does a rule, split at its *, match the start of `path` (all of it, if the rule ended in $)? The pieces are looked
    for one after the other from the left: that is enough for a *, and it takes time in proportion to the path."""
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
    if anchored:  # the last piece ends the path, beyond what the earlier pieces used
        return len(path) - len(last) >= pos and path.endswith(last)
    return path.find(last, pos) >= 0


class RobotsRules:
    """What a robots.txt allows this tool, read as RFC 9309 reads it. The standard library's parser reads the same file
    differently from one Python to the next (the first matching rule instead of the longest, no * or $, "%2F" decoded,
    a second group of one name lost, a group dropped after a leading byte-order mark), so the same site would keep other
    pages out on another machine. A line is "name: value" with a "#" comment cut off; groups are runs of User-agent lines
    followed by Allow and Disallow rules (other lines, such as Sitemap, belong to no group and end none); the group that
    names this tool counts, else the group of "*", else nothing does; the groups of one name are combined. The longest
    rule that matches wins, measured by the rule after its percent-escapes are normalised, "*" and "$" counted: Google's
    parser counts the rule as written, which differs only for a rule that holds an escape of an unreserved character, a
    space or another character that is no URI character; an Allow wins a tie. The newer standard parser measures what a
    rule matched instead, which differs for rules with a "*"."""

    def __init__(self):
        self.allow_all = False  # set by the caller for a robots.txt that is not there
        self.disallow_all = False  # ... and for one that cannot be read
        self.rules: List[Tuple[int, bool, List[str], bool]] = []  # (length, allow, pieces, ends in $), best first

    def parse(self, text: str) -> None:
        named: List[tuple] = []
        everyone: List[tuple] = []
        any_named = mine = star = in_rules = False
        for line in _LINE_END.split(text):
            name, colon, value = line.split("#", 1)[0].lstrip(" \t\ufeff").partition(":")
            name = name.strip().lower()
            if not colon:
                continue
            value = value.strip()
            if name == "user-agent":
                if in_rules:  # an agent line after rules starts the next group
                    mine = star = in_rules = False
                if _AGENT_NAME.match(value).group().lower() == ROBOTS_TOKEN:  # "facts-check/1.0" names this tool too
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
        self.rules = sorted(named if any_named else everyone, key=lambda r: (-r[0], not r[1]))

    def allowed(self, url: str) -> bool:
        """May this address be read? It is judged on the path the request sends ("http://x.test?private" is requested as
        "/?private"). The time grows with the rules in the file and the length of that path; Fetcher.blocked() hands over
        only addresses that bad_address() accepts, which are 8,000 characters at most as robots_form() reads them."""
        if self.disallow_all:
            return False
        if self.allow_all:
            return True
        path = robots_form(request_target(url))
        if path == "/robots.txt":  # RFC 9309 (2.2.2): the file itself is always allowed, in any spelling that reads as it
            return True
        for _, allow, parts, anchored in self.rules:
            if _matches(parts, anchored, path):
                return allow
        return True


class Fetcher:
    def __init__(self, timeout: float, delay: float, respect_robots: bool):
        self.timeout = timeout
        self.delay = delay
        self.respect_robots = respect_robots
        self._opener = urllib.request.build_opener(_RedirectGuard(self))
        self._robots: Dict[str, Tuple[RobotsRules, str]] = {}
        self._last = 0.0

    def _wait(self):
        gap = time.monotonic() - self._last
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last = time.monotonic()

    def get(self, url: str, limit: int = MAX_BYTES,
            guard_redirects: bool = False) -> Tuple[int, str, bytes, str]:
        """(status, content type, body, final url). Status 0 = no answer. The body is
        cut at `limit` bytes. With `guard_redirects`, a redirect to an address robots.txt does
        not allow is not followed: the status is REDIRECT_BLOCKED and the content type says why."""
        url = clean_address(url)
        bad = bad_address(url)
        if bad:
            return 0, bad, b"", url  # a sitemap may list anything: file:, ftp: and nonsense are not pages
        self._wait()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                       "Accept": "text/html,application/xml;q=0.9,*/*;q=0.5"})
            req.guard_robots = guard_redirects
            with self._opener.open(req, timeout=self.timeout) as r:
                body = r.read(limit)
                if getattr(r, "length", None) and len(body) < limit:
                    # http.client hands back a short body without complaint when the server
                    # promised more than it sent
                    raise http.client.IncompleteRead(body, r.length)
                status = r.status if isinstance(r.status, int) else 0
                return status, r.headers.get("Content-Type", ""), body, r.geturl()
        except _RedirectBlocked as e:
            said = ("redirects to %s, which robots.txt does not allow" % e.url if e.why == "robots.txt"
                    else "redirects to %s; %s" % (e.url, e.why))
            return (REDIRECT_BLOCKED if e.robots else 0), said, b"", url
        except urllib.error.HTTPError as e:
            return e.code, "", b"", url
        except http.client.IncompleteRead:
            return 0, "the response ended before it was complete", b"", url
        except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:
            return 0, str(getattr(e, "reason", e)), b"", url

    def blocked(self, url: str) -> str:
        """Why robots.txt keeps this address from being read, or "" when it may be."""
        if not self.respect_robots or bad_address(url):  # get() refuses an address that cannot be read; it is not matched here
            return ""
        p = urllib.parse.urlsplit(url)
        root = "%s://%s" % (p.scheme, p.netloc)
        if root not in self._robots:
            rules = RobotsRules()
            status, _, body, _ = self.get(root + "/robots.txt")
            why = "robots.txt"
            if status == 200:
                rules.parse(body.decode("utf-8", "replace"))
            elif status in (401, 403):
                rules.disallow_all = True
            elif status == 0 or status >= 500 or 300 <= status < 400:
                # A robots.txt that cannot be read (no answer, a server error, a redirect that
                # never resolves) means "keep out" by the robots convention (RFC 9309), not
                # "everything allowed".
                rules.disallow_all = True
                why = ("robots.txt could not be read (%s); --ignore-robots reads the pages "
                       "anyway, on a site you own" % (status or "no answer"))
            else:
                rules.allow_all = True
            self._robots[root] = (rules, why)
        rules, why = self._robots[root]
        return "" if rules.allowed(url) else why


def decode(body: bytes, ctype: str) -> str:
    try:  # charset=iso-8859-1 and charset="iso-8859-1" (RFC 9110 allows the quotes) both
        header = email.message.Message()
        header["Content-Type"] = ctype or ""
        enc = header.get_content_charset()
    except Exception:
        enc = None
    if not enc:  # <meta charset="..."> or <meta http-equiv="Content-Type" content="...; charset=...">
        m = re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", body[:4096], re.I)
        enc = m.group(1).decode("ascii") if m else "utf-8"
    try:
        return body.decode(enc, "replace")
    except (LookupError, UnicodeError):  # an unknown name, or a codec such as idna that is no page encoding
        return body.decode("utf-8", "replace")


def sitemap_urls(fetcher: Fetcher, start: List[str], limit: int, notes: List[str],
                 only: str = "") -> List[str]:
    pages: List[str] = []
    known = set()  # a list lookup per address made a 50,000-address sitemap quadratic
    queue = list(start)
    seen = set()
    junk: List[str] = []
    while queue and len(pages) < limit and len(seen) < MAX_SITEMAP_FILES:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        status, ctype, body, _ = fetcher.get(sm, SITEMAP_MAX_BYTES + 1)
        if status != 200 or not body:
            notes.append("sitemap %s: %s" % (sm, status or ctype or "no answer"))
            continue
        if sm.endswith(".gz") or body[:2] == b"\x1f\x8b":
            try:
                with gzip.GzipFile(fileobj=io.BytesIO(body)) as gz:
                    body = gz.read(SITEMAP_MAX_BYTES + 1)
            except (OSError, EOFError):
                notes.append("sitemap %s: not a readable .gz file" % sm)
                continue
        if len(body) > SITEMAP_MAX_BYTES:
            notes.append("sitemap %s: larger than the 50 MB a sitemap may be; not read" % sm)
            continue
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            notes.append("sitemap %s: not valid XML" % sm)
            continue
        # Only <url><loc> and <sitemap><loc>: image:loc and video:*_loc are not pages.
        locs = [loc.text.strip()
                for entry in root if _local(entry.tag) in ("url", "sitemap")
                for loc in entry if _local(loc.tag) == "loc" and loc.text and loc.text.strip()]
        locs = [clean_address(u) for u in locs]
        if _local(root.tag) == "sitemapindex":
            queue.extend(locs)
        else:
            for u in locs:
                if only and only not in u:
                    continue
                if bad_address(u):
                    junk.append(u)  # left out and said so below: it takes none of the page budget
                    continue
                if u not in known:
                    known.add(u)
                    pages.append(u)
                    if len(pages) >= limit:
                        break
    if junk:
        notes.append("sitemap entries that are not web addresses were left out: %d (the first: %s)"
                     % (len(set(junk)), junk[0]))
    unread = {u for u in queue if u not in seen}
    if unread and len(pages) < limit:
        notes.append("sitemaps: stopped after %d sitemap files; %d more were not read, so pages "
                     "listed only there are missing" % (MAX_SITEMAP_FILES, len(unread)))
    return pages[:limit]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def default_sitemaps(fetcher: Fetcher, site: str) -> List[str]:
    root = site.rstrip("/")
    status, _, body, _ = fetcher.get(root + "/robots.txt")
    listed = []
    if status == 200:
        for line in body.decode("utf-8", "replace").splitlines():
            if line.lower().startswith("sitemap:"):
                listed.append(line.split(":", 1)[1].strip())
    return listed or [root + "/sitemap.xml", root + "/sitemap-index.xml", root + "/sitemap_index.xml"]


# ---------------------------------------------------------------------------
# Positioning
# ---------------------------------------------------------------------------

SURFACE_LABEL = {"title": "<title>", "desc": "<meta description>", "h1": "<h1>/intro",
                 "body": "body"}


def norm_path(url_or_path: str) -> str:
    """/en/about/, /en/about.html and /en/about/index.html all read as /en/about."""
    # a rule path ("/en/about") is a path even if "://" occurs inside it; only an address is parsed
    path = (urllib.parse.urlsplit(url_or_path).path if "://" in url_or_path and not url_or_path.startswith("/")
            else url_or_path)
    path = urllib.parse.unquote(path or "/")
    for tail in ("/index.html", ".html"):
        if path.endswith(tail):
            path = path[: -len(tail)] or "/"
    if len(path) > 1:
        path = path.rstrip("/") or "/"
    return path


def find_rule(path: str, rules: List[dict]) -> Optional[dict]:
    """The first rule with a matching pattern wins, so put specific rules first."""
    for r in rules:
        if matches(path, [norm_path(p) for p in _patterns(r)]):
            return r
    return None


def matches(path: str, normed_patterns: List[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, p) for p in normed_patterns)


def rule_clauses(rule: dict) -> Dict[str, list]:
    if "term" in rule:
        t = rule["term"]
        return {"title": [t], "desc": [t], "h1": [t], "body": rule.get("body", [])}
    return {k: rule.get(k, []) for k in SURFACES}


def check_positioning(surfaces: Dict[str, str], rule: dict) -> List[str]:
    """Every clause the page does not meet, in the starter test's wording."""
    missing = []
    for k, clauses in rule_clauses(rule).items():
        hay = surfaces.get(k, "").lower()
        for c in clauses:
            alts = c if isinstance(c, list) else [c]
            if not any(a.lower() in hay for a in alts):
                missing.append("%s needs %s" % (SURFACE_LABEL[k], (
                    "one of [%s]" % " | ".join(alts)) if isinstance(c, list) else "\u201c%s\u201d" % c))
    return missing


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

def check_page(url: str, locations: Dict[str, str], facts: List[dict],
               retired_phrases: List[dict]) -> List[dict]:
    rows = []
    seen = set()
    for fact in facts:
        for where, text in locations.items():
            if where == "link addresses":  # "/blog/2024/10-tips" states no fact
                continue
            for hit in find_mentions(text, fact):
                key = (fact["id"], where, hit["snippet"])
                if key in seen:
                    continue
                seen.add(key)
                hit.update({"kind": "fact", "fact": fact["id"], "url": url, "where": where})
                rows.append(hit)
    for rp in retired_phrases:
        for where, text in locations.items():
            for snip in find_phrases(text, rp["text"]):
                rows.append({"kind": "phrase", "status": "RETIRED", "phrase": rp["text"],
                             "note": rp.get("note", ""), "url": url, "where": where,
                             "snippet": snip})
    return rows


def run(data: dict, max_pages: int, delay: float, timeout: float, only: str,
        respect_robots: bool, fetcher: Optional[Fetcher] = None) -> dict:
    fetcher = fetcher or Fetcher(timeout, delay, respect_robots)
    notes: List[str] = []
    site = clean_address(data["site"]).rstrip("/")
    if data.get("pages"):
        pages = list(dict.fromkeys(clean_address(u) for u in data["pages"]))
        source = "the facts file's page list"
    else:
        start = [clean_address(data["sitemap"])] if data.get("sitemap") else default_sitemaps(fetcher, site)
        pages = sitemap_urls(fetcher, start, max_pages, notes, only)
        source = "the sitemap"
    if only:
        pages = [u for u in pages if only in u]
    pages = pages[:max_pages]
    own = [(u, "own") for u in pages]
    extra = [(u, "elsewhere") for u in dict.fromkeys(clean_address(u) for u in data.get("extra_urls", []) or [])]
    facts = data["facts"]
    retired_phrases = data.get("retired_phrases", []) or []
    rows: List[dict] = []
    read, failed, skipped = [], [], []
    pos = data.get("positioning") or None
    pos_pages: List[dict] = []
    uncovered: List[str] = []
    exempt = [norm_path(x) for x in (pos or {}).get("exempt", [])]
    # Patterns normalised once, not once per page
    normed_rules = [dict(r, pages=[norm_path(p) for p in _patterns(r)]) for r in (pos or {}).get("rules", [])]
    redirected: List[dict] = []
    also_read: List[str] = []
    for url, origin in own + extra:
        bad = bad_address(url)
        if bad:
            failed.append({"url": url, "origin": origin, "why": bad})
            continue
        why = fetcher.blocked(url)
        if why:
            skipped.append({"url": url, "origin": origin, "why": why})
            continue
        status, ctype, body, final = fetcher.get(url, MAX_BYTES + 1, guard_redirects=True)
        if status == REDIRECT_BLOCKED:
            skipped.append({"url": url, "origin": origin, "why": ctype})
            continue
        if len(body) > MAX_BYTES:
            body = body[:MAX_BYTES]
            notes.append("%s: larger than 5 MB; only the first 5 MB were read" % url)
        if status != 200:
            failed.append({"url": url, "origin": origin, "why": str(status or ctype or "no answer")})
            continue
        if "html" not in ctype.lower() and not body.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")):
            skipped.append({"url": url, "origin": origin, "why": "not an HTML page: %s" % (ctype.split(";")[0] or "unknown type")})
            continue
        parser = PageText()
        try:
            parser.feed(decode(body, ctype))
            parser.close()
        except Exception as e:  # a broken page must not stop the run
            failed.append({"url": url, "origin": origin, "why": "could not parse: %s" % e})
            continue
        if pos and origin == "own":
            path = norm_path(url)
            moved = urllib.parse.urlsplit(final)
            if (moved.netloc, norm_path(final)) != (urllib.parse.urlsplit(url).netloc, path):
                # an old address that redirects is not a page of its own: list it, check
                # its target where the sitemap lists that
                redirected.append({"url": url, "final": final})
            elif not matches(path, exempt):  # exempt wins over any rule
                rule = next((r for r in normed_rules if matches(path, r["pages"])), None)
                if rule is not None:
                    pos_pages.append({
                        "url": url, "path": path, "audience": rule.get("audience", ""),
                        "rule": ", ".join(_patterns(rule)),
                        "missing": check_positioning(parser.surfaces(), rule)})
                else:
                    uncovered.append(url)
        for row in check_page(url, parser.locations(), facts, retired_phrases):
            row["origin"] = origin
            if final != url:
                row["final_url"] = final
            rows.append(row)
        read.append({"url": url, "origin": origin})
    # /llms.txt is written for AI assistants, so its figures and names count too.
    # Not part of the sitemap; read once, unless --only narrows the run to a section.
    llms = site + "/llms.txt"
    if not only and not data.get("pages") and read and not fetcher.blocked(llms):
        status, ctype, body, _ = fetcher.get(llms, guard_redirects=True)
        if status == REDIRECT_BLOCKED:
            notes.append("/llms.txt: %s" % ctype)
        elif status == 200 and body and "html" not in ctype.lower():
            for row in check_page(llms, {"llms.txt": decode(body, ctype)}, facts, retired_phrases):
                row["origin"] = "own"
                rows.append(row)
            also_read.append(llms)
    return {
        "site": site,
        "date": _dt.date.today().isoformat(),
        "source": source,
        "pages_listed": len(pages),
        "read": read, "failed": failed, "skipped": skipped,
        "notes": notes, "rows": rows, "also_read": also_read,
        "facts": facts, "retired_phrases": retired_phrases,
        "positioning": None if not pos else {"pages": pos_pages, "uncovered": uncovered,
                                             "redirected": redirected},
    }


def counts(result: dict) -> Dict[str, int]:
    c = {"OK": 0, "MISMATCH": 0, "OUTDATED": 0, "RETIRED": 0, "POSITIONING": 0}
    for r in result["rows"]:
        c[r["status"]] += 1
    if result.get("positioning"):
        c["POSITIONING"] = sum(1 for p in result["positioning"]["pages"] if p["missing"])
    return c


def fmt_value(v: float) -> str:
    return "{:,}".format(int(v)) if float(v).is_integer() else ("%g" % v)


def report_md(result: dict) -> str:
    c = counts(result)
    rows = result["rows"]
    L: List[str] = []
    L.append("# Facts check: %s" % result["site"])
    L.append("")
    L.append("Run %s. Pages from %s: %d listed, %d read, %d could not be read, %d skipped."
             % (result["date"], result["source"], result["pages_listed"],
                sum(1 for p in result["read"] if p["origin"] == "own"),
                sum(1 for p in result["failed"] if p["origin"] == "own"),
                sum(1 for p in result["skipped"] if p["origin"] == "own"))
             + ("".join(" Also read: %s." % u for u in result.get("also_read", []))))
    if result["pages_listed"] == 0:
        L.append("")
        L.append("**No pages were found, so nothing was checked.** See the notes at the end.")
    elif not any(p["origin"] == "own" for p in result["read"]):
        L.append("")
        L.append("**No page of the site could be read, so nothing was checked.** "
                 "The counts below say nothing about the site. See the list at the end.")
    if result["facts"] or result["retired_phrases"]:  # a positioning-only run has no fact counts
        L.append("")
        L.append("**%d mismatch%s, %d outdated value%s, %d retired phrase%s**, %d mention%s that match."
                 % (c["MISMATCH"], "" if c["MISMATCH"] == 1 else "es",
                    c["OUTDATED"], "" if c["OUTDATED"] == 1 else "s",
                    c["RETIRED"], "" if c["RETIRED"] == 1 else "s",
                    c["OK"], "" if c["OK"] == 1 else "s"))
    pos = result.get("positioning")
    if pos:
        L.append("")
        L.append("**%d page%s lost %s positioning term**, of %d with a rule; %d page%s with no rule."
                 % (c["POSITIONING"], "" if c["POSITIONING"] == 1 else "s",
                    "its" if c["POSITIONING"] == 1 else "their", len(pos["pages"]),
                    len(pos["uncovered"]), "" if len(pos["uncovered"]) == 1 else "s"))
    if result["facts"]:
        L.append("")
        L.append("| Fact | Approved | Match | Mismatch | Outdated | Pages naming it |")
        L.append("|---|---|---|---|---|---|")
    for f in result["facts"]:
        fr = [r for r in rows if r["kind"] == "fact" and r["fact"] == f["id"]]
        unit = f.get("unit", "")
        L.append("| %s | %s%s | %d | %d | %d | %d |" % (
            f.get("label") or f["id"], fmt_value(f["value"]), unit,
            sum(r["status"] == "OK" for r in fr), sum(r["status"] == "MISMATCH" for r in fr),
            sum(r["status"] == "OUTDATED" for r in fr), len({r["url"] for r in fr})))
    for title, status in (("Mismatches", "MISMATCH"), ("Outdated values", "OUTDATED")):
        hits = [r for r in rows if r["status"] == status]
        if not hits:
            continue
        L.append("")
        L.append("## %s" % title)
        for f in result["facts"]:
            fh = [r for r in hits if r["fact"] == f["id"]]
            if not fh:
                continue
            L.append("")
            L.append("### %s: approved %s%s" % (f.get("label") or f["id"], fmt_value(f["value"]), f.get("unit", "")))
            prov = [(k, f.get(key, "")) for k, key in
                    (("Source", "source"), ("Owner", "owner"), ("Last confirmed", "checked"))]
            prov = ["%s: %s." % (k, v) for k, v in prov if isinstance(v, str) and v and not v.startswith("[")]
            if prov:
                L.append(" ".join(prov))
            for r in sorted(fh, key=lambda r: (r["origin"] != "own", r["url"], r["where"])):
                tag = "" if r["origin"] == "own" else " (not your site)"
                L.append("- %s%s, %s: found **%s**. \u201c%s\u201d"
                         % (r["url"], tag, r["where"], r["found"], r["snippet"]))
    ph = [r for r in rows if r["status"] == "RETIRED"]
    if ph:
        L.append("")
        L.append("## Retired phrases still in use")
        for r in sorted(ph, key=lambda r: (r["phrase"], r["origin"] != "own", r["url"])):
            tag = "" if r["origin"] == "own" else " (not your site)"
            note = (" (%s)" % r["note"]) if r.get("note") and not r["note"].startswith("[") else ""
            L.append("- \u201c%s\u201d%s on %s%s, %s: \u201c%s\u201d"
                     % (r["phrase"], note, r["url"], tag, r["where"], r["snippet"]))
    if pos:
        L.append("")
        L.append("## Positioning")
        L.append("")
        L.append("| Audience | Pages with a rule | Carry their term | Lost it |")
        L.append("|---|---|---|---|")
        for aud in sorted({p["audience"] for p in pos["pages"]}):
            ap_ = [p for p in pos["pages"] if p["audience"] == aud]
            L.append("| %s | %d | %d | %d |" % (aud or "(none named)", len(ap_),
                                                 sum(1 for p in ap_ if not p["missing"]),
                                                 sum(1 for p in ap_ if p["missing"])))
        lost = [p for p in pos["pages"] if p["missing"]]
        if lost:
            L.append("")
            L.append("### Pages that lost their term")
            L.append("Either the page or the term needs to change; the team decides which.")
            for p in sorted(lost, key=lambda p: (p["audience"], p["path"])):
                aud = (" (%s)" % p["audience"]) if p["audience"] else ""
                L.append("- %s%s, rule %s: %s" % (p["url"], aud, p["rule"], "; ".join(p["missing"])))
        if pos["uncovered"]:
            L.append("")
            L.append("### Pages with no positioning rule")
            L.append("Not an error: each page here owns no term yet. Add a rule, or list a "
                     "legal or utility page under \u201cexempt\u201d.")
            for u in pos["uncovered"][:50]:
                L.append("- %s" % u)
            if len(pos["uncovered"]) > 50:
                L.append("- and %d more (all are in the JSON result)" % (len(pos["uncovered"]) - 50))
        if pos.get("redirected"):
            L.append("")
            L.append("### Addresses that redirect")
            L.append("Not checked for positioning: each is an old address that leads elsewhere. "
                     "Consider taking it out of the sitemap.")
            for r in pos["redirected"][:50]:
                L.append("- %s \u2192 %s" % (r["url"], r["final"]))
    never = [f for f in result["facts"]
             if not any(r["kind"] == "fact" and r["fact"] == f["id"] for r in rows)]
    if never:
        L.append("")
        L.append("## Facts no page names")
        L.append("Either no page states them, or their terms do not match how the pages say it.")
        for f in never:
            L.append("- %s" % (f.get("label") or f["id"]))
    if result["failed"] or result["skipped"] or result["notes"]:
        L.append("")
        L.append("## Not checked")
        for p in result["failed"]:
            L.append("- %s: could not be read (%s)" % (p["url"], p["why"]))
        for p in result["skipped"]:
            L.append("- %s: skipped (%s)" % (p["url"], p["why"]))
        for n in result["notes"]:
            L.append("- %s" % n)
    L.append("")
    L.append("Read-only: this check changed nothing. Text that appears only after JavaScript runs is not seen.")
    return "\n".join(L) + "\n"


def append_history(path: str, result: dict) -> None:
    c = counts(result)
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "site", "pages_read", "pages_not_read", "mismatches",
                        "outdated", "retired_phrases", "matches", "positioning_lost"])
        w.writerow([result["date"], result["site"],
                    sum(1 for p in result["read"] if p["origin"] == "own"),
                    sum(1 for p in result["failed"] + result["skipped"] if p["origin"] == "own"),
                    c["MISMATCH"], c["OUTDATED"], c["RETIRED"], c["OK"],
                    c["POSITIONING"] if result.get("positioning") else ""])


def main(argv: Optional[List[str]] = None, fetcher: Optional[Fetcher] = None) -> int:
    ap = argparse.ArgumentParser(description="Compare every figure on a live site with one list of "
                                 "approved facts, and check that each page carries its positioning "
                                 "term. Read-only.")
    ap.add_argument("facts", help="the facts file (JSON)")
    ap.add_argument("--init", action="store_true", help="write a starter facts file at that path and stop")
    ap.add_argument("--out", default="", help="write the Markdown report here (default: print it)")
    ap.add_argument("--json", default="", help="also write the full result as JSON here")
    ap.add_argument("--history", default="", help="append one line of counts to this CSV (the weekly trend)")
    ap.add_argument("--max-pages", type=int, default=1000, help="read at most this many of the site's pages (default 1000)")
    ap.add_argument("--only", default="", help="only pages whose address contains this text, e.g. /en/")
    ap.add_argument("--delay", type=float, default=0.5, help="seconds between requests (default 0.5)")
    ap.add_argument("--timeout", type=float, default=20.0, help="seconds to wait for one page (default 20)")
    ap.add_argument("--ignore-robots", action="store_true",
                    help="read pages robots.txt disallows (only on a site you own)")
    a = ap.parse_args(argv)

    if a.init:
        if os.path.exists(a.facts):
            print("%s exists; not overwritten." % a.facts, file=sys.stderr)
            return 2
        with open(a.facts, "w", encoding="utf-8") as f:
            json.dump(STARTER, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("Wrote %s. Fill in the site, the facts and their sources, then run the check." % a.facts)
        return 0

    try:
        data = load_facts(a.facts)
    except FactsError as e:
        print(str(e), file=sys.stderr)
        return 2
    if a.max_pages < 1:
        print("--max-pages must be at least 1", file=sys.stderr)
        return 2

    result = run(data, a.max_pages, a.delay, a.timeout, a.only, not a.ignore_robots, fetcher)
    md = report_md(result)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(md)
        print("Report written to %s" % a.out)
    else:
        sys.stdout.write(md)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    if result["pages_listed"] == 0 or not any(p["origin"] == "own" for p in result["read"]):
        print("No page of the site could be read; nothing was checked%s."
              % (", and the history was not updated" if a.history else ""), file=sys.stderr)
        return 2
    if a.history:
        append_history(a.history, result)
    c = counts(result)
    return 1 if (c["MISMATCH"] or c["OUTDATED"] or c["RETIRED"] or c["POSITIONING"]) else 0


if __name__ == "__main__":
    sys.exit(main())
