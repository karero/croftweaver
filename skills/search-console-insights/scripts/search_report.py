#!/usr/bin/env python3
"""
search_report.py — the owner's Google & Bing report page for one site.

    search_report.py <domain> [--keywords "a,b"] [--country deu] [--csv history.csv]

Writes ~/.config/gsc-insights/reports/<site>/google.html (a stable name, so a saved link keeps
working), plus google-data.json beside it: what the last successful fetch from Google returned,
with the settings and dates it was fetched with. It prints the page's path and opens nothing.
Exit 0 when the page was written — also when Google could not be reached, since the page then
says so at the top — and 1 when no page could be written.

Every number follows the counting rules in docs/reviews/SKILL-PLAN-gsc-report.md (scenario ids
S1–S16 below refer to it). In short: complete Monday–Sunday weeks in Pacific Time; visits and
times shown summed per week, positions averaged weighted by impressions; "the last 4 weeks"
means the last 4 complete weeks; one Google request per key search; Bing from the history, one
point per run date, never a claimed move.
"""
import argparse
import csv
import datetime as dt
import html
import json
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _history import NOISE_IMPRESSIONS, normalize_site  # noqa: E402
import fix_proposal as fp  # noqa: E402

ROW_LIMIT = 25000
HISTORY_DAYS = 16 * 31      # the ~16 months Google keeps; it returns what it has
KEY_WEEKS = 13              # key-search cards: the last 3 months
MIN_WEEKS_PER_SIDE = 2      # a move needs at least 2 usable weeks on each side
PCT_FLOOR = 20              # a percentage only when both 4-week sides have 20+ visits
S6_MIN_IMPRESSIONS = 5      # the text report's striking-distance floor (gsc_query.py)
S6_SHOWN = 15               # rows shown in "just below page 1"
S7_MAX_POSITION, S7_MIN_IMPRESSIONS, S7_MAX_CTR = 10.0, 20, 0.02   # gsc_query.py's low-CTR rule
TRACKER_WINDOW = "28"
STALE_RECORD_DAYS = 14      # a weekly record older than two weeks is named on the page
AI_HEADING = "<h2>Google's and Bing's AI answers</h2>"
STALE_AI_DAYS = 35          # A7: a downloaded AI report whose last day is older than this says so


def base_dir() -> Path:
    return Path(os.path.expanduser("~")) / ".config" / "gsc-insights"


def report_dir(site: str) -> Path:
    return base_dir() / "reports" / site


# ─── settings ────────────────────────────────────────────────────────────────────────────

def split_keywords(s):
    return [k.strip() for k in (s or "").split(",") if k.strip()]


def default_csv() -> str:
    return os.environ.get("GSC_HISTORY_CSV") or str(base_dir() / "history.csv")


def read_history(path, site):
    p = Path(os.path.expanduser(path))
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if normalize_site(r.get("site") or "") == site]


def history_settings(rows):
    """Keywords and country from the latest date with gsc rows, one (window, country) group chosen
    deterministically: window 28 first, then most distinct keywords, then the shorter window
    (blank last), then the country code (blank first) — so every tie ends in one group."""
    gsc = [r for r in rows if r.get("source") == "gsc" and r.get("keyword")]
    if not gsc:
        return None
    latest = max(r.get("date", "") for r in gsc)
    groups = {}
    for r in gsc:
        if r.get("date") == latest:
            groups.setdefault((r.get("window") or "", r.get("country") or ""), set()).add(r["keyword"])

    def rank(item):
        (window, country), kws = item
        w = int(window) if window.isdigit() else math.inf
        return (window != TRACKER_WINDOW, -len(kws), w, country)
    (window, country), kws = sorted(groups.items(), key=rank)[0]
    return {"keywords": sorted(kws), "country": country, "from": f"your last check on {latest}"}


def resolve_settings(domain, args):
    """Flags, else sites/<site>.json (what the weekly job last resolved, or what the scheduler
    installed), else the history, else none. Nothing here re-reads .env or the launchd job: the
    job records its own resolved settings, so the two can never evaluate them differently."""
    site = normalize_site(domain)
    s = {"keywords": [], "country": "", "csv": "", "from": "", "bing": None, "recorded": ""}
    sf = base_dir() / "sites" / f"{site}.json"
    found = None
    if sf.exists():
        try:
            j = json.loads(sf.read_text(encoding="utf-8"))
            if not isinstance(j, dict):
                raise ValueError("not a settings record")
            # A hand-edited record may hold anything: key searches as one string are read the way
            # --keywords is; any other value of the wrong type counts as not set.
            text = lambda k: j.get(k) if isinstance(j.get(k), str) else ""
            kws = j.get("keywords")
            kws = split_keywords(kws) if isinstance(kws, str) else kws if isinstance(kws, list) else []
            found = {"keywords": [k.strip() for k in kws if isinstance(k, str) and k.strip()],
                     "country": text("country"), "csv": text("csv"),
                     "bing": j.get("bing") if isinstance(j.get("bing"), bool) else None,
                     "recorded": j.get("recorded") if isinstance(j.get("recorded"), str) else "",
                     "record_used": True,
                     "from": f"your weekly check on {j['recorded']}" if j.get("recorded") else "your weekly check"}
        except (ValueError, OSError):
            found = None
    if found:
        s.update(found)
    if args.csv is not None:
        s["csv"] = args.csv
    # An explicitly empty history setting (a job's or a flag's) means the shared default file,
    # as it does for track.sh — never a value inherited from the environment.
    explicit = found is not None or args.csv is not None
    csv_path = s["csv"] or (str(base_dir() / "history.csv") if explicit else default_csv())
    rows = read_history(csv_path, site)
    if not found and not args.keywords:
        h = history_settings(rows)
        if h:
            s.update(h)
    if args.keywords is not None:
        s["keywords"], s["from"] = split_keywords(args.keywords), "your request"
    if args.country is not None:
        s["country"] = args.country
    s["csv"] = csv_path
    s["country"] = (s["country"] or "").lower()
    return s, rows


# ─── fetching from Google ──────────────────────────────────────────────────────────────────

class SignInError(Exception):
    """The saved Google sign-in cannot be used (missing, expired, refresh refused)."""


def make_service():
    """The authenticated Search Console client, without ever opening a browser."""
    import gsc_query as g
    cfg = base_dir()
    try:
        from google.auth.exceptions import RefreshError
    except ImportError:
        RefreshError = RuntimeError
    try:
        creds = g.load_credentials(cfg / "client_secret.json", cfg / "token.json", interactive=False)
    except (RuntimeError, RefreshError) as e:
        raise SignInError(str(e)) from e
    except SystemExit as e:    # load_credentials exits when the Google libraries are missing
        raise RuntimeError("the Google libraries are not installed (see SKILL.md setup)") from e
    try:
        return g.build_service(creds)
    except SystemExit as e:
        raise RuntimeError("the Google libraries are not installed (see SKILL.md setup)") from e


def run_query(service, prop, body):
    """One Search Analytics request, paged with startRow when a page comes back full."""
    rows, start = [], 0
    while True:
        b = dict(body, rowLimit=ROW_LIMIT, startRow=start)
        resp = service.searchanalytics().query(siteUrl=prop, body=b).execute()
        page = resp.get("rows", [])
        rows.extend(page)
        if len(page) < ROW_LIMIT:
            return rows, resp
        start += ROW_LIMIT


def _filters(country, query=None):
    f = []
    if country:
        f.append({"dimension": "country", "operator": "equals", "expression": country})
    if query is not None:
        f.append({"dimension": "query", "operator": "equals", "expression": query})
    return [{"groupType": "and", "filters": f}] if f else []


def _body(start, end, dims, country, query=None):
    b = {"startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": dims}
    fl = _filters(country, query)
    if fl:
        b["dimensionFilterGroups"] = fl
    return b


def pick_property(service, domain):
    """sc-domain:<domain>, as the tracker uses; if Google refuses it, a URL-prefix property for the
    same domain from the account's list (plan: Counting rules → Property)."""
    domain = normalize_site(domain)      # "Example.com" or "sc-domain:example.com" as typed
    prop = f"sc-domain:{domain}"
    try:
        service.searchanalytics().query(siteUrl=prop, body={
            "startDate": dt.date.today().isoformat(), "endDate": dt.date.today().isoformat()}).execute()
        return prop
    except Exception as first:
        try:
            entries = service.sites().list().execute().get("siteEntry", [])
        except Exception:
            raise first
        site = domain
        for e in entries:
            url = e.get("siteUrl", "")
            if url.startswith("http") and normalize_site(url) in (site, "www." + site):
                return url
        raise first


def last_sunday(d):
    return d - dt.timedelta(days=(d.weekday() + 1) % 7)


def fetch_google(service, domain, settings, today):
    """Everything the page needs from Google. Required requests raise; the S6 page drill-downs are
    optional and come back as None on failure (S9)."""
    prop = pick_property(service, domain)
    country = settings["country"]
    # The finished date: the day before firstIncompleteDate (probe results in the plan).
    _, meta_resp = run_query(service, prop, dict(
        _body(today - dt.timedelta(days=10), today, ["date"], country), dataState="all"))
    fid = (meta_resp.get("metadata") or {}).get("firstIncompleteDate")
    daily, _ = run_query(service, prop, _body(today - dt.timedelta(days=HISTORY_DAYS), today, ["date"], country))
    if fid:
        finished = dt.date.fromisoformat(fid) - dt.timedelta(days=1)
    elif daily:
        finished = max(dt.date.fromisoformat(r["keys"][0]) for r in daily)
    else:
        finished = today - dt.timedelta(days=3)
    daily = [r for r in daily if dt.date.fromisoformat(r["keys"][0]) <= finished]

    key_start = finished - dt.timedelta(days=KEY_WEEKS * 7 + 7)
    keys = {}
    for kw in settings["keywords"]:
        rows, _ = run_query(service, prop, _body(key_start, finished, ["date", "query"], country, kw.lower()))
        keys[kw] = [{"date": r["keys"][0], "clicks": r.get("clicks", 0), "impressions": r.get("impressions", 0),
                     "position": r.get("position")} for r in rows]

    end4 = last_sunday(finished)
    start4 = end4 - dt.timedelta(days=27)
    qrows, _ = run_query(service, prop, _body(start4, end4, ["query"], country))
    prows, _ = run_query(service, prop, _body(start4, end4, ["page"], country))
    s6 = []
    cands = [r for r in qrows if r.get("position") is not None and 10 < r["position"] <= 20
             and r.get("impressions", 0) >= S6_MIN_IMPRESSIONS]
    cands.sort(key=lambda r: -r.get("impressions", 0))
    for r in cands[:S6_SHOWN]:   # only the rows the page shows get a page drill-down
        pos, imp = r["position"], r.get("impressions", 0)
        try:
            pages, _ = run_query(service, prop, _body(start4, end4, ["page"], country, r["keys"][0]))
            pages.sort(key=lambda p: -p.get("impressions", 0))
            top = pages[0]["keys"][0] if pages else None
            more = max(0, len(pages) - 1)
        except Exception:
            top, more = None, 0
        s6.append({"query": r["keys"][0], "position": pos, "impressions": imp, "page": top, "more": more})
    # The weekly fix proposal's search-and-page rows (DESIGN-weekly-fix-proposal.md §3.1). Optional,
    # like the drill-downs above: without them there is no proposal this week, and the page says so.
    try:
        qprows, _ = run_query(service, prop, _body(start4, end4, ["query", "page"], country))
        qp4 = [{"keys": r["keys"], "impressions": r.get("impressions", 0)} for r in qprows]
    except Exception:
        qp4 = None
    s7 = [{"page": r["keys"][0], "impressions": r.get("impressions", 0), "clicks": r.get("clicks", 0)}
          for r in prows
          if r.get("position") is not None and r["position"] <= S7_MAX_POSITION and r.get("impressions", 0) >= S7_MIN_IMPRESSIONS
          and r.get("ctr", 0) < S7_MAX_CTR]
    return {
        "fetched": today.isoformat(), "property": prop, "country": country,
        "keywords": list(settings["keywords"]), "from": settings.get("from") or "",
        "finished": finished.isoformat(),
        "daily": [{"date": r["keys"][0], "clicks": r.get("clicks", 0), "impressions": r.get("impressions", 0),
                   "position": r.get("position")} for r in daily],
        "keys": keys, "window4": [start4.isoformat(), end4.isoformat()],
        "s6": sorted(s6, key=lambda x: -x["impressions"]), "s7": sorted(s7, key=lambda x: -x["impressions"]),
        "q4": [{"keys": r["keys"], "impressions": r.get("impressions", 0), "clicks": r.get("clicks", 0),
                "position": r.get("position")} for r in qrows],
        "qp4": qp4,
    }


# ─── the weekly fix proposal (DESIGN-weekly-fix-proposal.md §3) ─────────────────────────────

PAGE_MAX_BYTES = 2_000_000


def read_live_page(url, site):
    """The owner's own page as parse_page() reads it, or None (a timeout, an error, a non-200
    answer, another host). Only the site's own addresses are read: the report never fetches
    anything else a Search Console row might name."""
    from urllib.parse import urlsplit
    import urllib.request

    def own(address):
        u = urlsplit(address or "")
        return u.scheme in ("http", "https") and (u.hostname or "").lower() in (site, "www." + site)

    class OwnPagesOnly(urllib.request.HTTPRedirectHandler):
        """A redirect is followed only to the site's own pages, like the first address."""
        def redirect_request(self, req, fp_, code, msg, headers, newurl):
            if not own(newurl):
                return None          # not followed: urllib then raises, and the page is unreadable
            return super().redirect_request(req, fp_, code, msg, headers, newurl)

    if not own(url):
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "search-console-insights fix check"})
        opener = urllib.request.build_opener(OwnPagesOnly)
        with opener.open(req, timeout=20) as resp:
            if resp.status != 200:
                return None
            body = resp.read(PAGE_MAX_BYTES + 1)
            charset = resp.headers.get_content_charset() or "utf-8"
    except Exception:
        return None
    if len(body) > PAGE_MAX_BYTES:
        return None
    return fp.parse_page(body.decode(charset, errors="replace"))


def measure_search(service, prop, country, query, w):
    """One search's figures in the before and the after window: two requests made for this
    purpose, filtered to the search, with the report's country and property (design §3.4)."""
    out = {}
    for side in ("before", "after"):
        start, end = w[side]
        rows, _ = run_query(service, prop, _body(start, end, ["query"], country, query.lower()))
        row = rows[0] if rows else {}
        out[side] = {"from": start.isoformat(), "to": end.isoformat(), "impressions": row.get("impressions", 0),
                     "clicks": row.get("clicks", 0), "position": row.get("position")}
    out["weeks"], out["interrupted"] = w["weeks"], w["interrupted"]
    return out


def _check_today(rec, today, outcome):
    """Add this run's look at the live page. A second run on the same day adds a look only when it
    saw something else, so an "old" in the morning and a "new" after the change went live both
    stay, in the order they were made (fix_proposal.windows reads them that way)."""
    checks = list(rec.get("checks", []))
    last = checks[-1] if checks else None
    if not (last and last.get("date") == today.isoformat() and last.get("outcome") == outcome):
        checks.append({"date": today.isoformat(), "outcome": outcome})
    rec["checks"] = sorted(checks, key=lambda c: c["date"])


def follow_proposals(state, service, prop, country, finished, today, read_page, gh):
    """Each run: ask GitHub about every recorded pull request, look at the live page, and measure
    once the after-window's data is complete. Nothing is released by a timer."""
    for rec in state["proposals"].values():
        if not rec.get("pr") or (rec.get("result") and (rec["pr"].get("state") or "").upper() != "OPEN"):
            continue
        fp.apply_pr_state(rec, gh(rec["pr"]["repo"], rec["pr"]["number"]), today)
        if rec.get("result"):
            continue         # measured; only the pull request's state was still worth asking
        if rec.get("declined_on") or not rec.get("new_title"):
            continue
        page = read_page(rec["page"])
        _check_today(rec, today, fp.classify_title(page.get("title") if page else None,
                                                   rec.get("old_title"), rec["new_title"]))
        w = fp.windows(rec["checks"])
        if w and w["weeks"] == 0 and w["interrupted"]:
            rec["result"] = {"too_soon": True, "interrupted": w["interrupted"]}
        elif fp.ready_to_measure(w, finished):
            try:
                rec["result"] = measure_search(service, prop, country, rec["query"], w)
            except Exception:
                pass     # tried again next run; this run's look at the page is still kept


def update_proposals(site, data, service, today, read_page, gh):
    """Follow what is waiting, then choose this week's proposal from fresh data, under the site's
    lock (the assistant's commands take it too). Returns what the page shows (proposal_view)."""
    with fp.locked(site):
        return _update_proposals(site, data, service, today, read_page, gh)


def _update_proposals(site, data, service, today, read_page, gh):
    state = fp.load_state(site)
    finished = dt.date.fromisoformat(data["finished"])
    follow_proposals(state, service, data["property"], data["country"], finished, today, read_page, gh)
    spellings, _ = fp.brand_spellings(state, site)
    start4, end4 = (dt.date.fromisoformat(x) for x in data["window4"])
    if data.get("qp4") is None:
        cands, notes, unavailable = [], [], True
        proposal = None
    else:
        unavailable = False
        cands = fp.t1_candidates(data.get("q4") or [], data["qp4"], spellings)
        proposal, notes = fp.choose(cands, state, today, read_page)
    if proposal:
        fp.record_shown(state, proposal, (start4, end4), today)
    else:
        state["current"] = None
    # A site that never had a proposal gets no file: nothing to remember yet.
    if state["proposals"] or fp.state_path(site).exists():
        fp.save_state(site, state)
    return proposal_view(site, state, data, today, cands=cands, notes=notes, unavailable=unavailable)


def proposal_view(site, state, data, today, cands=None, notes=None, unavailable=False, stale=False):
    """Everything the section needs, from the state file and the window's figures."""
    spellings, confirmed = fp.brand_spellings(state, site)
    view = {"stale": stale, "unavailable": unavailable, "notes": notes or [], "had_candidates": bool(cands),
            "spellings": spellings, "confirmed": confirmed, "current": None, "follow": []}
    cur = state["proposals"].get(state.get("current")) if state.get("current") else None
    if cur and not stale:
        view["current"] = dict(cur, sentence=fp.sentence(cur))
    view["cur_rec"] = cur if cur and not stale else None
    for rec in list(state.get("done") or []) + list(state["proposals"].values()):
        until = fp.declined_until(rec)
        if until and today < until:
            view["follow"].append(rec)          # turned down: the page says until when
        elif rec.get("result") or (rec.get("pr") and not until):
            view["follow"].append(rec)          # measured, or still in progress
    if data:
        s, e = data["window4"]
        view["window"] = (s, e)
        view["total"] = sum(r.get("impressions", 0) for r in data["daily"] if s <= r["date"] <= e)
        nonbrand = [r for r in data.get("q4") or [] if not fp.is_brand(r["keys"][0], spellings)]
        view["brand"] = sum(r.get("impressions", 0) for r in data.get("q4") or []
                            if fp.is_brand(r["keys"][0], spellings))
        # Enough data, just nothing in striking distance, is not "too little data".
        view["enough"] = any(r.get("impressions", 0) >= fp.T1_MIN_IMPRESSIONS for r in nonbrand)
    return view


def _d(iso):
    return f"{dt.date.fromisoformat(iso):%d %B %Y}" if iso else "an earlier week"


def _follow_line(rec, site, today):
    where = f"“{rec['query']}” on {show_page(rec['page'], site)}"
    pr = rec.get("pr") or {}
    until = fp.declined_until(rec)
    if until and today < until:
        how = (f"you closed pull request {pr.get('number')}" if rec.get("decline_reason") == "closed"
               else "turned down")
        return f"{where}: {how}; not proposed again before {until:%d %B %Y}."
    res = rec.get("result")
    if res and res.get("too_soon"):
        return f"{where}: the page changed again too soon after the change went live to measure it."
    if res:
        b, a = res["before"], res["after"]
        pos = lambda v: f"{v:.1f}" if v is not None else "not shown"
        cut = (f" The page changed again on {_d(res['interrupted'])}, so the after side covers "
               f"{res['weeks']} week{'s' if res['weeks'] != 1 else ''}.") if res.get("interrupted") else ""
        return (f"{where}, before and after the change ({_d(b['from'])} to {_d(b['to'])}, then {_d(a['from'])} "
                f"to {_d(a['to'])}): position {pos(b['position'])} → {pos(a['position'])}, shown "
                f"{_n(b['impressions'])} → {_n(a['impressions'])} times, visits {_n(b['clicks'])} → "
                f"{_n(a['clicks'])}.{cut} This compares one search before and after the change. It does not "
                "check what else changed on your site or in Google's results.")
    gh_note = (" GitHub could not be asked this week, so this is the last state it gave."
               if pr.get("last_check_ok") is False and pr.get("state") else "")
    w = fp.windows(rec.get("checks", []))
    if w:
        end = w["after"][1] if w["after"] else None
        return (f"{where}: live; the before-and-after comparison appears once Google's numbers reach "
                f"{end:%d %B %Y}." if end else f"{where}: live; measuring.") + gh_note
    seen = [c["outcome"] for c in rec.get("checks", []) if c.get("outcome") != "unreadable"]
    if seen and seen[-1] == "other":
        return (f"{where}: the live page's title is neither the old one nor the new one recorded for pull "
                f"request {pr.get('number')}. Ask your assistant to check it and record the title the "
                "page shows.") + gh_note
    state = (pr.get("state") or "").upper()
    if state == "MERGED":
        return (f"{where}: merged in pull request {pr.get('number')}, not seen on the live site yet. "
                "On a site that publishes in two steps, that needs `npm run ship`.") + gh_note
    if state == "OPEN":
        return (f"{where}: your proposal of {_d(rec.get('shown'))} is waiting in pull request "
                f"{pr.get('number')}.") + gh_note
    return (f"{where}: pull request {pr.get('number')} could not be checked; tell your assistant if it "
            "was closed.")


def _plain_reason(why):
    """fix_proposal's short reasons, in the owner's words."""
    if why.startswith("turned down until "):
        return f"you turned it down, until {why[len('turned down until '):]}"
    return {"measuring": "an earlier change to the same page is still being measured",
            "pull request open": "a pull request for the same page is still open",
            "merged, not seen live yet": "a change to the same page is merged but not live yet",
            "already on the page": "its words are already on the page",
            "the page could not be read": "the page could not be read today"}.get(why, why)


def proposal_line(view, alert=None):
    """One line for the weekly log (track.sh shows the report's stderr): the proposal, or why
    there is none. None when the page had no Google data at all."""
    if view is None:
        return f"could not be worked out ({alert})" if alert else None
    cur = view.get("current")
    if view.get("stale"):
        return "none new this week (Google's numbers could not be refreshed)"
    if cur:
        return (f"work “{cur['query']}” into {cur['page']} (shown {_n(cur['impressions'])} times in 4 weeks, "
                f"average position {cur['position']:.1f}); the sentence to say is on the report page")
    if view.get("unavailable"):
        return "none this week (Google's search-by-page numbers could not be loaded)"
    if view.get("had_candidates"):
        return "none this week; passed over: " + "; ".join(f"“{q}”: {_plain_reason(w)}" for q, w in view["notes"])
    if "total" in view and view.get("enough"):
        return "none this week (no search met every condition for a proposal)"
    if "total" in view:
        return f"none this week (too little data: shown {_n(view['total'])} times in 4 weeks)"
    return None


def render_proposal(view, site, today):
    if view is None:
        return ""
    parts = ["<h2>One thing to fix this week</h2>"]
    cur = view.get("current")
    if view.get("stale"):
        parts.append("<p>No new proposal this week: Google's numbers could not be refreshed.</p>")
    elif cur:
        since = "" if cur.get("shown") == today.isoformat() else f" Proposed since {H(_d(cur['shown']))}."
        parts.append(
            f'<section class="card"><p class="move">Work “{H(cur["query"])}” into the title, heading and first '
            f'paragraph of {H(show_page(cur["page"], site))}.</p>'
            f'<p>In the 4 weeks {H(cur["window"][0])} to {H(cur["window"][1])}, people searching for '
            f'“{H(cur["query"])}” were shown your site {_n(cur["impressions"])} times, at an average position of '
            f'{cur["position"]:.1f}; {_n(cur["page_impressions"])} of those times on this page. Its title, heading '
            f'and first paragraph do not yet say it.{since}</p>'
            f'<p>To make the change, say to your assistant:</p><p><code>{H(cur["sentence"])}</code></p>'
            "<p class=\"note\">Your assistant checks it against your positioning first, changes only those three "
            "places, runs your site's tests, and opens a pull request for you to look at. Nothing goes live until you merge it.</p></section>")
    elif view.get("unavailable"):
        parts.append("<p>No proposal this week: Google's search-by-page numbers could not be loaded.</p>")
    elif view.get("had_candidates"):
        reasons = "; ".join(f"“{q}”: {_plain_reason(why)}" for q, why in view["notes"])
        parts.append(f"<p>No proposal this week. Searches looked at and passed over: {H(reasons)}.</p>")
    elif "total" in view and view.get("enough"):
        parts.append(
            "<p>No proposal this week: no search met every condition for one (at position 8 to 20, shown at "
            "least 50 times in 4 weeks, on a page shown at least 10 times, its words not yet on that "
            "page).</p>")
    elif "total" in view:
        parts.append(
            f"<p>Too little data to propose a change this week: shown {_n(view['total'])} times in 4 weeks "
            f"({H(view['window'][0])} to {H(view['window'][1])}), {_n(view['brand'])} of them for your name. The first "
            f"thing that would lead to a proposal: a search shown {fp.T1_MIN_IMPRESSIONS} times at position 8 to 20 "
            "whose words are not yet on the page it leads to.</p>")
    lines = []
    for r in view["follow"]:
        if r is view.get("cur_rec"):
            continue
        try:
            lines.append(_follow_line(r, site, today))
        except Exception:        # a damaged record costs its own line, never the page
            lines.append(f"One earlier proposal could not be read ({r.get('page', 'unknown page')}).")
    if lines:
        parts.append("<h3>Earlier proposals</h3><ul>" + "".join(f"<li>{H(x)}</li>" for x in lines) + "</ul>")
    if not view["confirmed"]:
        parts.append(f'<p class="note">Counted as your business name: {H(", ".join(view["spellings"]))}. If that is '
                     "wrong, tell your assistant the spellings people use.</p>")
    return "".join(parts)


# ─── counting (pure) ───────────────────────────────────────────────────────────────────────

def complete_weeks(daily, finished):
    """Complete Monday–Sunday weeks inside [first date with a row, finished]; a day without a row
    inside that range counts as 0 (Google sends no row for a day without data)."""
    if not daily:
        return []
    by_day = {dt.date.fromisoformat(r["date"]): r for r in daily}
    first = min(by_day)
    monday = first + dt.timedelta(days=(7 - first.weekday()) % 7)
    weeks = []
    while monday + dt.timedelta(days=6) <= finished:
        days = [by_day.get(monday + dt.timedelta(days=i)) for i in range(7)]
        weeks.append(_week(monday, [d for d in days if d]))
        monday += dt.timedelta(days=7)
    return weeks


def _week(monday, rows):
    clicks = sum(r.get("clicks", 0) for r in rows)
    imp = sum(r.get("impressions", 0) for r in rows)
    pos = (sum(r["position"] * r.get("impressions", 0) for r in rows if r.get("position") is not None) / imp) if imp else None
    return {"monday": monday, "clicks": clicks, "impressions": imp, "position": pos}


def key_weeks(rows, finished, n=KEY_WEEKS):
    """The last n complete weeks for one key search; a week under NOISE_IMPRESSIONS is hollow."""
    end = last_sunday(finished)
    by_day = {}
    for r in rows:
        by_day.setdefault(dt.date.fromisoformat(r["date"]), []).append(r)
    out = []
    for k in range(n, 0, -1):
        monday = end - dt.timedelta(days=7 * k - 1)
        days = [x for i in range(7) for x in by_day.get(monday + dt.timedelta(days=i), [])]
        w = _week(monday, days)
        w["hollow"] = w["impressions"] < NOISE_IMPRESSIONS
        out.append(w)
    return out


def _weighted(weeks):
    imp = sum(w["impressions"] for w in weeks)
    return sum(w["position"] * w["impressions"] for w in weeks) / imp if imp else None


def move(weeks):
    """('up'|'down', d) / ('flat', 0) / ('thin', None): the last 4 weeks against the 4 before, only
    weeks that are not hollow, at least 2 per side; d = rounded before − rounded now."""
    before = [w for w in weeks[-8:-4] if not w["hollow"]]
    now = [w for w in weeks[-4:] if not w["hollow"]]
    if len(before) < MIN_WEEKS_PER_SIDE or len(now) < MIN_WEEKS_PER_SIDE:
        return "thin", None, None, None
    b, n = round(_weighted(before)), round(_weighted(now))
    d = b - n
    if d >= 1:
        return "up", d, b, n
    if d <= -1:
        return "down", -d, b, n
    return "flat", 0, b, n


def headline(weeks, moves):
    """The first line (S2): visits first, then every non-zero outcome of the Google key searches."""
    n = len(weeks)
    if n == 0:
        return None
    if n < 4:
        v = sum(w["clicks"] for w in weeks)
        first = f"{_n(v)} visit{'s' if v != 1 else ''} from Google in the last {n} week{'s' if n > 1 else ''}."
    else:
        last4 = sum(w["clicks"] for w in weeks[-4:])
        if n < 8:
            first = f"{_n(last4)} visit{'s' if last4 != 1 else ''} from Google in the last 4 weeks."
        else:
            before = sum(w["clicks"] for w in weeks[-8:-4])
            if last4 >= PCT_FLOOR and before >= PCT_FLOOR:
                pct = round((last4 - before) / before * 100)
                change = (f"{pct}% more than" if pct > 0 else f"{-pct}% fewer than" if pct < 0 else "the same as")
                first = f"{_n(last4)} visits from Google in the last 4 weeks, {change} the 4 weeks before."
            elif last4 == 0 and before == 0:
                first = "No visits from Google in the last 8 weeks."
            elif before == 0:
                first = f"{_n(last4)} visit{'s' if last4 != 1 else ''} from Google in the last 4 weeks, none in the 4 weeks before."
            else:
                first = (f"{_n(last4)} visit{'s' if last4 != 1 else ''} from Google in the last 4 weeks, "
                         f"{_n(before)} in the 4 weeks before.")
    if not moves:
        return first
    return f"{first} {moves_sentence(moves)}."


def moves_sentence(moves):
    """Every outcome that occurred, zero counts left out: "3 of your 5 key searches moved up,
    1 moved down, 1 had too little data to tell" / "None of your 5 key searches moved: …"."""
    total = len(moves)
    phrase = {"up": "moved up", "down": "moved down", "flat": "showed no clear change",
              "thin": "had too little data to tell"}
    counts = [(k, sum(1 for m in moves if m == k)) for k in ("up", "down", "flat", "thin")]
    counts = [(k, c) for k, c in counts if c]
    if total == 1:
        k = moves[0]
        return {"up": "Your key search moved up", "down": "Your key search moved down",
                "flat": "Your key search shows no clear change",
                "thin": "Your key search had too little data to tell"}[k]
    if any(k in ("up", "down") for k, _ in counts):
        (k0, c0), rest = counts[0], counts[1:]
        return ", ".join([f"{c0} of your {total} key searches {phrase[k0]}"] + [f"{c} {phrase[k]}" for k, c in rest])
    # Nothing moved: say what is known, never "none moved" (unknown for the thin ones).
    return f"Of your {total} key searches, " + ", ".join(f"{c} {phrase[k]}" for k, c in counts)


def _n(v):
    return f"{int(round(v)):,}"


def bing_lines(rows, keywords=None):
    """Per CURRENT key search (old one-off keywords in the history are left out), one point per run date: that date's row with the latest row's window and
    country, else the date's row with the most impressions; ‡ where the config differs from the
    previous point, ≠ where the matched query does (both break the line)."""
    by_kw = {}
    for r in rows:
        if r.get("source") == "bing" and r.get("keyword"):
            if keywords is not None and r["keyword"].lower() not in keywords:
                continue
            by_kw.setdefault(r["keyword"], []).append(r)
    out = {}
    for kw, rs in by_kw.items():
        rs.sort(key=lambda r: r.get("date", ""))
        latest_cfg = ((rs[-1].get("window") or ""), (rs[-1].get("country") or ""))
        points = []
        for date in sorted({r.get("date", "") for r in rs}):
            day = [r for r in rs if r.get("date", "") == date]
            same = [r for r in day if ((r.get("window") or ""), (r.get("country") or "")) == latest_cfg]
            pick = (same or sorted(day, key=lambda r: -_int(r.get("impressions"))))[-1 if same else 0]
            points.append({"date": date, "position": _float(pick.get("position")),
                           "query": pick.get("query") or "", "cfg": ((pick.get("window") or ""), (pick.get("country") or ""))})
        for i, p in enumerate(points):
            prev = points[i - 1] if i else None
            p["break"] = "" if not prev else ("‡" if p["cfg"] != prev["cfg"] else "≠" if p["query"] != prev["query"] else "")
        out[kw] = points
    return out


def _int(v):
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return 0


def _float(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def past_variant(rows, keyword):
    """S11: the most recent gsc row for this key search whose matched query was a variant."""
    cands = [r for r in rows if r.get("source") == "gsc" and r.get("keyword") == keyword
             and (r.get("query") or "").strip() and (r.get("query") or "").lower() != keyword.lower()]
    return max(cands, key=lambda r: r.get("date", "")) if cands else None


# ─── the page ──────────────────────────────────────────────────────────────────────────────

H = html.escape
PT, PB = 14, 26
SIZES = {"wide": (640, 44, 104, 2), "narrow": (340, 34, 58, 4)}


def nice_max(v):
    if v <= 0:
        return 1
    mag = 10 ** math.floor(math.log10(v))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * mag >= v:
            return max(1, int(m * mag))
    return int(10 * mag)


def month_ticks(mondays):
    out, seen = [], set()
    for i, w in enumerate(mondays):
        if (w.year, w.month) not in seen and w.day <= 7:
            seen.add((w.year, w.month))
            out.append((i, w.strftime("%b") if w.month != 1 else w.strftime("%b %Y")))
    return out


def line_chart(values, mondays, fmt, title, h=190):
    return "".join(_line_chart(values, mondays, fmt, title, h, k) for k in SIZES)


def _line_chart(values, mondays, fmt, title, h, size):
    W, PL, PR, every = SIZES[size]
    top = nice_max(max(values))
    iw, ih = W - PL - PR, h - PT - PB
    x = (lambda i: PL + iw * i / (len(values) - 1)) if len(values) > 1 else (lambda i: PL + iw / 2)
    y = lambda v: PT + ih * (1 - v / top)
    g = []
    for t in sorted({0, top // 2, top}):
        g.append(f'<line class="grid" x1="{PL}" x2="{W - PR}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
                 f'<text class="tick" x="{PL - 6}" y="{y(t) + 4:.1f}" text-anchor="end">{t:,}</text>')
    for i, lab in month_ticks(mondays)[::every]:
        g.append(f'<text class="tick" x="{x(i):.1f}" y="{h - 6}" text-anchor="middle">{lab}</text>')
    if len(values) > 1:
        g.append('<polyline class="line" points="' + " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values)) + '"/>')
    for i, (w, v) in enumerate(zip(mondays, values)):
        g.append(f'<circle class="hit" cx="{x(i):.1f}" cy="{y(v):.1f}" r="7"><title>week of {w:%d %b %Y}: {H(fmt(v))}</title></circle>')
    lx, ly = x(len(values) - 1), y(values[-1])
    g.append(f'<circle class="dot" cx="{lx:.1f}" cy="{ly:.1f}" r="4"/>'
             f'<text class="endlabel" x="{lx + 10:.1f}" y="{ly + 4:.1f}">{H(fmt(values[-1]))}</text>')
    return f'<svg class="{size}" viewBox="0 0 {W} {h}" role="img" aria-label="{H(title)}"><title>{H(title)}</title>{"".join(g)}</svg>'


def position_chart(name, points, hi, h=150):
    """points: list of (label date, position or None, hollow, break-before marker)."""
    return "".join(_position_chart(name, points, hi, h, k) for k in SIZES)


def _position_chart(name, points, hi, h, size):
    W, PL, PR, every = SIZES[size]
    iw, ih = W - PL - PR, h - PT - PB
    n = len(points)
    x = (lambda i: PL + iw * i / (n - 1)) if n > 1 else (lambda i: PL + iw / 2)
    y = lambda p: PT + ih * (p - 1) / (hi - 1)
    g = []
    ticks = {1, 10} | ({20} if hi >= 20 else set())
    if hi - max(ticks) >= 10:
        ticks.add(hi)
    for t in sorted(ticks):
        cls = "grid strong" if t == 10 else "grid"
        g.append(f'<line class="{cls}" x1="{PL}" x2="{W - PR}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
                 f'<text class="tick" x="{PL - 6}" y="{y(t) + 4:.1f}" text-anchor="end">{t}</text>')
    dates = [p[0] for p in points]
    for i, lab in month_ticks(dates)[::max(1, every // 2)]:
        g.append(f'<text class="tick" x="{x(i):.1f}" y="{h - 6}" text-anchor="middle">{lab}</text>')
    seg = []
    for i, (d, pos, hollow, brk) in enumerate(points):
        if brk and seg:
            g.append('<polyline class="line" points="' + " ".join(seg) + '"/>')
            seg = []
            cx = (x(i - 1) + x(i)) / 2
            g.append(f'<line class="mark" x1="{cx:.1f}" x2="{cx:.1f}" y1="{PT}" y2="{h - PB}"/>'
                     f'<text class="tick" x="{cx + 4:.1f}" y="{PT + 10}">{H(brk)}</text>')
        if pos is None:
            if seg:
                g.append('<polyline class="line" points="' + " ".join(seg) + '"/>')
            seg = []
            continue
        pc = min(max(pos, 1), hi)
        seg.append(f"{x(i):.1f},{y(pc):.1f}")
    if seg:
        g.append('<polyline class="line" points="' + " ".join(seg) + '"/>')
    for i, (d, pos, hollow, brk) in enumerate(points):
        if pos is None:
            continue
        pc = min(max(pos, 1), hi)
        tip = f"{d:%d %b}: position {pos:.1f}" + (" — too few searches to tell" if hollow else "")
        g.append(f'<circle class="{"hollow" if hollow else "hit"}" cx="{x(i):.1f}" cy="{y(pc):.1f}" r="{4 if hollow else 7}"><title>{H(tip)}</title></circle>')
    last = next(((i, p) for i, p in reversed(list(enumerate(points))) if p[1] is not None), None)
    if last:
        i, (d, pos, hollow, brk) = last
        pc = min(max(pos, 1), hi)
        g.append(f'<circle class="dot" cx="{x(i):.1f}" cy="{y(pc):.1f}" r="4"/>'
                 f'<text class="endlabel" x="{x(i) + 10:.1f}" y="{y(pc) + 4:.1f}">{round(pos)}</text>')
    return (f'<svg class="{size}" viewBox="0 0 {W} {h}" role="img" aria-label="Position over time for {H(name)}">'
            f'<title>Position over time: {H(name)}</title>{"".join(g)}</svg>')


def numbers_table(headers, rows):
    head = "".join(f"<th>{H(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{H(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f'<details><summary>See the numbers</summary><table><tr>{head}</tr>{body}</table></details>'


CSS = """:root { color-scheme: light; --bg:#fcfcfb; --card:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --line:#2a78d6; --border:#e1e0d9; --warn:#fff4e5; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark; --bg:#1a1a19;
  --card:#222220; --ink:#ffffff; --ink2:#c3c2b7; --muted:#898781; --grid:#2c2c2a; --line:#3987e5; --border:#33332f; --warn:#3a2f1c; } }
:root[data-theme="dark"] { color-scheme: dark; --bg:#1a1a19; --card:#222220; --ink:#ffffff; --ink2:#c3c2b7;
  --muted:#898781; --grid:#2c2c2a; --line:#3987e5; --border:#33332f; --warn:#3a2f1c; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
main { max-width:760px; margin:0 auto; padding:24px 16px 48px; }
h1 { font-size:1.5rem; margin:0 0 4px; } h2 { font-size:1.2rem; margin:32px 0 8px; } h3 { font-size:1rem; margin:0; }
.sub { color:var(--ink2); margin:0 0 20px; }
.answer { font-size:1.3rem; line-height:1.4; font-weight:600; background:var(--card); border:1px solid var(--border);
  border-radius:12px; padding:16px 18px; margin:0 0 12px; }
.alert { background:var(--warn); border:1px solid var(--border); border-radius:8px; padding:10px 14px; margin:0 0 16px; }
.card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:14px 16px; margin:12px 0; }
.move { color:var(--ink2); margin:2px 0 6px; }
.note { color:var(--ink2); font-size:.9rem; margin:6px 0 0; }
svg { width:100%; height:auto; display:block; overflow:visible; }
svg.narrow { display:none; }
@media (max-width: 559px) { svg.wide { display:none; } svg.narrow { display:block; } }
.grid { stroke:var(--grid); stroke-width:1; } .grid.strong { stroke:var(--muted); stroke-opacity:.5; }
.tick { fill:var(--muted); font-size:11px; }
.line { fill:none; stroke:var(--line); stroke-width:2; stroke-linejoin:round; stroke-linecap:round; }
.dot { fill:var(--line); stroke:var(--card); stroke-width:2; }
.hit { fill:transparent; } .hollow { fill:var(--card); stroke:var(--line); stroke-width:2; }
.mark { stroke:var(--muted); stroke-width:1; }
.endlabel { fill:var(--ink); font-size:12px; font-weight:600; }
svg.key { width:12px; height:12px; display:inline-block; vertical-align:-1px; }
details { margin-top:8px; font-size:.9rem; } summary { cursor:pointer; color:var(--ink2); }
table { border-collapse:collapse; width:100%; margin-top:8px; font-variant-numeric:tabular-nums; }
th, td { text-align:left; padding:6px 8px; border-bottom:1px solid var(--border); } th { color:var(--ink2); font-weight:600; }
"""

COUNTRY_NAMES = {"deu": "Germany", "che": "Switzerland", "aut": "Austria", "usa": "the United States",
                 "gbr": "the United Kingdom", "fra": "France", "ita": "Italy", "esp": "Spain", "nld": "the Netherlands"}


def _day(d):
    return f"{d.day} {d:%B %Y}"


def _span(first, last, sep):
    """'12 July and 13 October 2026' / '12 July – 13 October 2026': the year once when both share it;
    one day once ('14 July 2026')."""
    a, b = dt.date.fromisoformat(first), dt.date.fromisoformat(last)
    if a == b:
        return _day(a)
    left = f"{a.day} {a:%B}" if a.year == b.year else _day(a)
    return f"{left}{sep}{_day(b)}"


def _between(first, last):
    return f"on {_span(first, last, '')}" if first == last else f"between {_span(first, last, ' and ')}"


def _ai_record_ok(source, j):
    """Every field the AI section reads, checked: a hand-edited or damaged record is treated as missing."""
    def date(v):
        return isinstance(v, str) and dt.date.fromisoformat(v)
    def count(v, least=0):
        return isinstance(v, int) and not isinstance(v, bool) and v >= least
    def text(v):          # a string the page can write as UTF-8 (no lone surrogate like "\ud800")
        if not isinstance(v, str):
            return False
        try:
            v.encode("utf-8")
            return True
        except UnicodeEncodeError:
            return False
    def address(v):
        from urllib.parse import urlsplit
        if not text(v):
            return False
        try:
            urlsplit(v)               # raises ValueError on 'https://[broken/'
            return True
        except ValueError:
            return False

    def span_ok(j):
        return date(j.get("first")) and date(j.get("last")) and j["first"] <= j["last"]
    state = j.get("state")
    if source == "google" and state == "not_shown":
        return bool(date(j.get("checked")))
    if j.get("search_type") is not None and not text(j["search_type"]):
        return False
    if source == "google" and state == "empty":
        return (j.get("first") is None and j.get("last") is None) or bool(span_ok(j))
    if source == "google" and state == "data":
        pages = j.get("pages", [])
        return bool(span_ok(j)) and count(j.get("total"), 1) and isinstance(pages, list) and all(
            isinstance(r, list) and len(r) == 2 and address(r[0]) and count(r[1], 1) for r in pages)
    if source == "bing" and state == "empty":
        return bool(span_ok(j))
    if source == "bing" and state == "data":
        return (bool(span_ok(j)) and count(j.get("citations"), 1) and count(j.get("days"), 1)
                and count(j.get("days_cited"), 1) and j["days_cited"] <= j["days"])
    return False


def load_ai(site):
    """What ai_reports.py saved for this site: {'google': …, 'bing': …}; a missing or damaged file is None."""
    out = {}
    for source in ("google", "bing"):
        p = report_dir(site) / f"ai-{source}.json"
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            out[source] = j if isinstance(j, dict) and _ai_record_ok(source, j) else None
        except (ValueError, TypeError, OSError, RecursionError):     # RecursionError: JSON nested too deep
            out[source] = None
    return out


def ai_section(ai, site, today):
    """Google's and Bing's own AI reports (docs/reviews/SKILL-PLAN-ai-reports.md, A1–A10): an empty or
    missing report is said in words, never as a 0, and never as a warning."""
    g, b = ai.get("google"), ai.get("bing")
    parts = [AI_HEADING]
    if not g and not b:
        parts.append("<p>Google and Bing now count how often your site appears in their AI answers, but they don't "
                     "let programs read those numbers. Download the reports and say <i>“here's my AI report from "
                     "Google”</i> (or Bing), and I'll add them here.</p>")
        return "".join(parts)
    parts.append('<p class="sub">Counted by Google and Bing themselves, from the reports you downloaded: real '
                 "answers people saw, not questions we asked.</p>")

    def old(rec):
        last = rec.get("last")
        try:
            if last and (today - dt.date.fromisoformat(last)).days > STALE_AI_DAYS:
                return (f'<p class="note">These numbers end on {H(_day(dt.date.fromisoformat(last)))}; '
                        "download a new report for newer ones.</p>")
        except ValueError:
            pass
        return ""

    def times(n):
        return f"{_n(n)} time{'s' if n != 1 else ''}"

    card = ['<section class="card"><h3>Google: AI Overviews and AI Mode</h3>']
    if not g:
        card.append("<p>Not added yet. In Search Console, open the generative AI report, export it, and say "
                    "<i>“here's my AI report from Google”</i>.</p>")
    elif g["state"] == "not_shown":
        when = _day(dt.date.fromisoformat(g["checked"]))
        card.append(f"<p>Google doesn't show an AI report for this site yet (you checked on {H(when)}). Google shows "
                    "it once a site has appeared in its AI answers often enough.</p>")
    elif g["state"] == "empty":
        # F9: Google writes "not available" as 0, so the card says what the file shows, not that there were none.
        covers = (f"it covers {H(_span(g['first'], g['last'], ' – '))}" if g.get("first") else "it has no rows")
        card.append(f"<p>Your download shows no impressions in Google's AI answers ({covers}). That is normal for a "
                    "small site.</p>")
        card.append(old(g))
    else:
        card.append(f'<p class="move">Your site was shown {times(g["total"])} in Google\'s AI answers (AI Overviews and '
                    f'AI Mode) {H(_between(g["first"], g["last"]))}.</p>')
        pages = g.get("pages") or []
        if pages:
            # A path that Google lists under two addresses (with and without www.) is shown in full
            # both times, so no two rows of the table read the same.
            paths = [show_page(u, site) for u, _ in pages[:15]]
            label = lambda i: paths[i] if paths.count(paths[i]) == 1 else pages[i][0]
            card.append("<table><tr><th>Your page</th><th>Shown</th></tr>"
                        + "".join(f"<tr><td>{H(label(i))}</td><td>{_n(n)}</td></tr>" for i, (u, n) in enumerate(pages[:15]))
                        + "</table>")
            if len(pages) > 15:
                card.append(f'<p class="note">And {len(pages) - 15} more pages in your download.</p>')
            card.append('<p class="note">One answer can show several of your pages, so the pages can add up to '
                        "more than the total.</p>")
        if g.get("search_type"):
            card.append(f'<p class="note">Your download counts “{H(g["search_type"])}”.</p>')
        card.append(old(g))
    parts.append("".join(card) + "</section>")

    card = ["<section class=\"card\"><h3>Bing: Copilot and Bing's AI summaries</h3>"]
    if not b:
        card.append("<p>Not added yet. In Bing Webmaster Tools, open AI Performance, export it, and say "
                    "<i>“here's my AI report from Bing”</i>.</p>")
    elif b["state"] == "empty":
        card.append(f"<p>No citations in Bing's AI answers yet (your download covers "
                    f"{H(_span(b['first'], b['last'], ' – '))}). That is normal for a small site.</p>")
        card.append(old(b))
    else:
        card.append(f"<p class=\"move\">Bing's AI answers (Copilot and Bing's AI summaries) cited your pages "
                    f"{times(b['citations'])} {H(_between(b['first'], b['last']))}"
                    + (f", on {_n(b['days_cited'])} of those {_n(b['days'])} days" if b["days"] > 1 else "") + ".</p>")
        card.append('<p class="note">A citation means your page was shown as a source. Bing counts a sample, and a '
                    "citation says nothing about visits.</p>")
        card.append(old(b))
    parts.append("".join(card) + "</section>")
    return "".join(parts)


def ai_part(site, today):
    """The AI section, behind one boundary: nothing in the saved AI files can stop the page being written.
    A record that fails a check reads as not added (load_ai); anything else that goes wrong while
    reading or showing them is said on the page and in the log, and the rest of the page is written."""
    try:
        return ai_section(load_ai(site), site, today)
    except Exception as e:  # noqa: BLE001 - the boundary is the point
        try:      # the log is best-effort: a broken stderr must not cost the page (review F40)
            print(f"search_report: the saved AI reports could not be shown ({type(e).__name__}: {e})"[:300],
                  file=sys.stderr)
        except Exception:  # noqa: BLE001
            pass
        return (AI_HEADING + "<p>The AI reports you added could not be read. Hand me the downloads again and "
                "I'll add them.</p>")


def render(site, data, alert, settings, rows, ai_link, bing_state, today, current_kw=frozenset(), ai_html=None,
           proposal=None):
    parts = []
    finished = dt.date.fromisoformat(data["finished"]) if data else None
    weeks = complete_weeks(data["daily"], finished) if data else []
    kw_cards, moves = [], []
    if data:
        for kw in data["keywords"]:
            kr = data["keys"].get(kw, [])
            if not kr:
                v = past_variant(rows, kw)
                extra = ""
                if v:
                    when = v.get("date", "")
                    differs = (v.get("country") or "") != (data["country"] or "")
                    cfg = f" (counting {v.get('country') or 'all countries'})" if differs else ""
                    extra = (f'<p class="note">Your check on {H(when)}{H(cfg)} matched “{H(v["query"])}” — '
                             f'say <i>track it</i> to add it.</p>')
                kw_cards.append(f'<section class="card"><h3>“{H(kw)}”</h3><p class="move">No data from Google '
                                f'for this search in the last 3 months.</p>{extra}</section>')
                moves.append("thin")   # counted in the headline as "too little data to tell"
                continue
            kw_w = key_weeks(kr, finished)
            m = move(kw_w)
            moves.append(m[0])
            kw_cards.append((kw, kw_w, m))
    hi = 10
    for c in kw_cards:
        if isinstance(c, tuple):
            ps = [w["position"] for w in c[1] if w["position"] is not None]
            if ps:
                hi = max(hi, int(math.ceil(max(ps) / 5.0) * 5))

    head = headline(weeks, moves) if data else None
    title = f"How people find you on Google — {site}"
    parts.append(f"<h1>How people find you on Google</h1><p class=\"sub\">{H(site)} · updated {today:%d %B %Y}"
                 + (f" · Google's numbers up to {finished:%d %B %Y}" if finished else "") + "</p>")
    if alert:
        parts.append(f'<p class="alert">{H(alert)}</p>')
    # Whenever the recorded settings are in use (even with --keywords, the country and history
    # can still come from them), an old or undated record is named, never passed over silently.
    if settings.get("record_used"):
        rec = settings.get("recorded")
        try:
            stale = (today - dt.date.fromisoformat(rec)).days > STALE_RECORD_DAYS
        except (ValueError, TypeError):     # missing, malformed or not a string at all
            stale, rec = True, ""
        if stale:
            when = f"on {H(rec)}" if rec else "without a date"
            parts.append(f'<p class="alert">The weekly check last recorded this site\'s settings {when}; '
                         'if it no longer runs, ask me to check the weekly tracking.</p>')
    if data and not weeks:
        parts.append('<p class="answer">Google needs a few days to report on a new site. Check back next week.</p>')
        if data["country"]:
            parts.append(f'<p class="note">Counting only searches from {H(COUNTRY_NAMES.get(data["country"], data["country"]))}: '
                         f'if the site is new there too, that is expected.</p>')
    elif head:
        parts.append(f'<p class="answer">{H(head)}</p>')
    parts.append('<details><summary>How to read this</summary><p><b>Visits</b> counts clicks from a Google search '
                 'to your site (one person can visit twice). <b>Shown</b> counts how often your site appeared in '
                 "someone's results, whether or not they clicked. <b>Position</b> is where you appeared: 1 is the "
                 'very top, and positions 1–10 are the first page. Google reports with a delay of 2–3 days, and '
                 'these weeks run Monday to Sunday in Pacific Time.</p></details>')
    if data:
        settings_line = []
        settings_line.append("Counting: searches from " + COUNTRY_NAMES.get(data["country"], data["country"]) if data["country"]
                             else "Counting: searches from all countries")
        if not data["property"].startswith("sc-domain:"):
            settings_line.append(f"only the address {data['property']}")
        # Where the key searches came from is saved with them: a page built from saved data
        # names its own source, not today's. A file saved before 0.29 has none; today's stands
        # in only when the key searches are the same, else no source is named.
        source = data["from"] if "from" in data else (
            settings.get("from") if data["keywords"] == settings.get("keywords") else "")
        if source and data["keywords"]:
            settings_line.append(f"key searches from {source}")
        parts.append(f'<p class="note">{H("; ".join(settings_line))}.</p>')

    if weeks:
        mondays = [w["monday"] for w in weeks]
        visits = [w["clicks"] for w in weeks]
        shown = [w["impressions"] for w in weeks]
        parts.append("<h2>Visits from Google, per week</h2><section class=\"card\">"
                     + line_chart(visits, mondays, lambda v: f"{_n(v)} visits", "Visits from Google per week")
                     + numbers_table(["Week of", "Visits"], [(f"{m:%d %b %Y}", _n(v)) for m, v in zip(mondays, visits)])
                     + "</section>")
        parts.append("<h2>How often you were shown, per week</h2><section class=\"card\">"
                     + line_chart(shown, mondays, _n, "Times shown in Google per week", h=150)
                     + numbers_table(["Week of", "Times shown"], [(f"{m:%d %b %Y}", _n(v)) for m, v in zip(mondays, shown)])
                     + "</section>")

    if data:
        parts.append("<h2>Your key searches on Google, last 3 months</h2>")
        if not data["keywords"]:
            parts.append("<p>Tell me the searches that matter to you and I'll track them here.</p>")
        else:
            parts.append('<p class="sub">Higher is better: the top of each chart is position 1, and the darker line '
                         "at 10 is the end of Google's first page.</p>")
            for c in kw_cards:
                if isinstance(c, str):
                    parts.append(c)
                    continue
                kw, kw_w, m = c
                kind, d, b, n = m
                text = {"up": f"about {n} now, up {d} place{'s' if d != 1 else ''} from the 4 weeks before",
                        "down": f"about {n} now, down {d} place{'s' if d != 1 else ''} from the 4 weeks before",
                        "flat": f"about {n}, no clear change from the 4 weeks before",
                        "thin": "too little data to tell a move"}[kind]
                pts = [(w["monday"], w["position"], w["hollow"], "") for w in kw_w]
                note = ""
                if any(w["hollow"] and w["position"] is not None for w in kw_w):
                    note = ('<p class="note"><svg class="key" viewBox="0 0 12 12"><circle class="hollow" cx="6" cy="6" r="4"/>'
                            '</svg> hollow point: too few searches that week to tell a move</p>')
                rows_t = [(f"{w['monday']:%d %b}", f"{w['position']:.1f}" if w["position"] is not None else "—",
                           _n(w["impressions"])) for w in kw_w]
                parts.append(f'<section class="card"><h3>“{H(kw)}”</h3><p class="move">{H(text)}</p>'
                             + position_chart(kw, pts, hi) + note
                             + numbers_table(["Week of", "Position", "Shown"], rows_t) + "</section>")

        enough = len(weeks) >= 4
        parts.append("<h2>Just below page 1</h2><p class=\"sub\">Searches where you appear just below the first page "
                     "in the last 4 weeks. A small improvement to the page listed could bring you onto page 1.</p>")
        if not enough:
            parts.append("<p>Not enough complete weeks yet.</p>")
        elif not data["s6"]:
            parts.append("<p>None right now.</p>")
        else:
            parts.append("<table><tr><th>Search</th><th>Position</th><th>Shown (4 weeks)</th><th>Your page</th></tr>"
                         + "".join(f"<tr><td>{H(r['query'])}</td><td>{round(r['position'])}</td><td>{_n(r['impressions'])}</td>"
                                   f"<td>{H(show_page(r['page'], site) if r['page'] else 'page unknown')}{H(' (+{} more)'.format(r['more'])) if r.get('more') else ''}</td></tr>"
                                   for r in data["s6"][:S6_SHOWN]) + "</table>")
        parts.append("<h2>Shown often, rarely clicked</h2><p class=\"sub\">Worth a look: first check how the page appears "
                     "in Google today, before changing anything.</p>")
        if not enough:
            parts.append("<p>Not enough complete weeks yet.</p>")
        elif not data["s7"]:
            parts.append("<p>None right now.</p>")
        else:
            parts.append("<table><tr><th>Your page</th><th>Shown (4 weeks)</th><th>Clicked</th></tr>"
                         + "".join(f"<tr><td>{H(show_page(r['page'], site))}</td><td>{_n(r['impressions'])}</td><td>{_n(r['clicks'])}</td></tr>"
                                   for r in data["s7"][:15]) + "</table>")

    try:
        parts.append(render_proposal(proposal, site, today))
    except Exception:
        parts.append("<h2>One thing to fix this week</h2><p>This week's fix proposal could not be shown.</p>")

    parts.append("<h2>Bing</h2>")
    if bing_state == "lines":
        lines = bing_lines(rows, current_kw)
        parts.append('<p class="sub">The tracker records Bing as a rolling average of about 6 months, so these lines '
                     "move slowly. A break marks a week where Bing matched a different wording (≠) or the check was "
                     "measured differently (‡).</p>")
        bhi = 10
        for pts in lines.values():
            ps = [p["position"] for p in pts if p["position"] is not None]
            if ps:
                bhi = max(bhi, int(math.ceil(max(ps) / 5.0) * 5))
        for kw, pts in sorted(lines.items()):
            latest = next((p for p in reversed(pts) if p["position"] is not None), None)
            text = f"latest position about {round(latest['position'])}" if latest else "no position recorded"
            names = []
            for p in pts:
                if p["query"] and p["query"] not in names:
                    names.append(p["query"])
            measured = f'<p class="note">Bing matched: {H(", ".join(names))}</p>' if len(names) > 1 else ""
            chart_pts = [(dt.date.fromisoformat(p["date"]), p["position"], False, p["break"]) for p in pts]
            parts.append(f'<section class="card"><h3>“{H(kw)}”</h3><p class="move">{H(text)}</p>'
                         + (position_chart(kw, chart_pts, bhi) if len(chart_pts) > 1 else "") + measured
                         + numbers_table(["Checked", "Position", "Bing matched"],
                                         [(p["date"], f"{p['position']:.1f}" if p["position"] is not None else "—", p["query"])
                                          for p in pts]) + "</section>")
    elif bing_state == "waiting":
        parts.append("<p>Bing is connected; its section fills in after the next weekly check.</p>")
    elif bing_state == "unknown":
        parts.append("<p>No Bing data for these searches yet. If Bing isn't connected, ask me <i>“connect Bing”</i>.</p>")
    else:
        parts.append("<p>Bing is not connected yet. Ask me <i>“connect Bing”</i> and I'll walk you through it.</p>")

    parts.append(ai_html if ai_html is not None else ai_part(site, today))

    if ai_link:
        parts.append(f'<p class="sub" style="margin-top:32px">Also see: <a href="{H(ai_link)}">Does AI name you?</a> — your AI report.</p>')
    else:
        parts.append('<p class="sub" style="margin-top:32px">The AI check ("Does AI name you?") is not set up for this site.</p>')

    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width, initial-scale=1"><title>{H(title)}</title><style>{CSS}</style></head>'
            f'<body><main>{"".join(parts)}</main></body></html>')


# ─── putting it together ─────────────────────────────────────────────────────────────────

def show_page(url, site):
    """The site's own pages as a path ('/roots', '/?x=1'), which an owner reads more easily;
    other addresses in full."""
    from urllib.parse import urlsplit
    u = urlsplit(url or "")
    if u.scheme in ("http", "https") and (u.hostname or "") in (site, "www." + site):
        return (u.path or "/") + (f"?{u.query}" if u.query else "") + (f"#{u.fragment}" if u.fragment else "")
    return url


def newest_ai_page(site):
    d = base_dir() / "geo" / "reports" / site
    pages = sorted(d.glob("*.html")) if d.exists() else []
    return pages[-1] if pages else None


def write_atomic(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def build(domain, args, service_factory=make_service, today=None, page_reader=None, gh=None):
    today = today or dt.date.today()
    site = normalize_site(domain)
    settings, rows = resolve_settings(domain, args)
    out_dir = report_dir(site)
    cache = out_dir / "google-data.json"
    data, alert, fresh, service = None, None, False, None
    try:
        service = service_factory()
        data = fetch_google(service, domain, settings, today)
        fresh = True
    except Exception as e:
        signin = isinstance(e, SignInError)
        saved = None
        if cache.exists():
            try:
                saved = json.loads(cache.read_text(encoding="utf-8"))
            except (ValueError, OSError):     # an unreadable saved file is the same as none
                saved = None
        reason = "" if signin else f" ({_reason(e)})"
        if saved:
            data = saved
            alert = (f"Google's numbers could not be refreshed{reason}; these are from {saved.get('fetched', '?')}."
                     + (" Say “reconnect Google”." if signin else ""))
        else:
            alert = f"Google's numbers could not be loaded{reason}." + (" Say “reconnect Google”." if signin else "")
    else:
        # Fresh numbers stay on the page even when the copy for next time cannot be saved; only
        # the fallback is lost, and the page says so.
        try:
            write_atomic(cache, json.dumps(data, indent=1))
        except OSError as e:
            print(f"search_report: could not save {cache}: {e}", file=sys.stderr)
            alert = ("These numbers are up to date, but a copy for when Google can't be reached "
                     "could not be saved on this computer.")
    # Bing follows today's key searches, also when Google's part comes from saved data.
    current_kw = {k.lower() for k in settings.get("keywords") or []}
    bing_rows = [r for r in rows if r.get("source") == "bing" and (r.get("keyword") or "").lower() in current_kw]
    # Whether Bing is connected is what the weekly run recorded (it resolved .env); unknown
    # before the first recorded run.
    if bing_rows:
        bing_state = "lines"
    elif settings.get("bing") is True:
        bing_state = "waiting"
    elif settings.get("bing") is False:
        bing_state = "off"
    else:
        bing_state = "unknown"
    proposal, proposal_alert = proposals_for_page(site, data, fresh, service, today, page_reader, gh)
    line = proposal_line(proposal, proposal_alert)
    if line:
        print(f"Fix proposal: {line}", file=sys.stderr)
    if proposal_alert:
        alert = f"{alert} {proposal_alert}" if alert else proposal_alert
    ai = newest_ai_page(site)
    ai_link = f"../../geo/reports/{site}/{ai.name}" if ai else None
    page = render(site, data, alert, settings, rows, ai_link, bing_state, today, current_kw, ai_part(site, today),
                  proposal)
    out = out_dir / "google.html"
    write_atomic(out, page)
    if ai:
        rebuild_ai_page(domain)
    return out


def proposals_for_page(site, data, fresh, service, today, page_reader=None, gh=None):
    """(proposal_view, alert). A new proposal comes from fresh data only (scenario 9): with saved
    data the page shows what is waiting and says there is no new proposal. A problem here never
    costs the owner the rest of the page; it is named instead."""
    if not data:
        return None, None
    read = page_reader or (lambda url: read_live_page(url, site))
    ask = gh or fp.gh_pr_state
    try:
        if fresh:
            return update_proposals(site, data, service, today, read, ask), None
        return proposal_view(site, fp.load_state(site), data, today, stale=True), None
    except Exception as e:
        return None, f"This week's fix proposal could not be worked out ({_reason(e)})."


def _reason(e):
    msg = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
    m = re.search(r"returned \"([^\"]+)\"", msg)
    return (m.group(1) if m else msg)[:120]


def rebuild_ai_page(domain):
    """Refresh the newest AI page from its saved history (no AI request), so its link back to this
    page appears without waiting for the next AI check. Never fails the Google report."""
    try:
        import geo_check
        geo_check.build_report(domain)
    except Exception as e:  # pragma: no cover - best effort
        print(f"note: the AI report page was not refreshed ({type(e).__name__}).", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write the owner's Google & Bing report page for one site.")
    ap.add_argument("domain", help="e.g. example.com")
    ap.add_argument("--keywords", default=None, help="Comma-separated key searches (default: the weekly job's).")
    ap.add_argument("--country", default=None, help="ISO alpha-3 country filter, e.g. deu ('' = all countries).")
    ap.add_argument("--csv", default=None, help="History CSV (default: the weekly job's, else the shared one).")
    args = ap.parse_args(argv)
    try:
        out = build(args.domain, args)
    except OSError as e:
        print(f"✗ Could not write the report page: {e}", file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
