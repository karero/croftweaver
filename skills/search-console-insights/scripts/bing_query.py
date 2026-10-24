#!/usr/bin/env python3
"""
bing_query.py — Bing Webmaster Tools companion to gsc_query.py.

Bing's index feeds Microsoft Copilot and ChatGPT search, so this is a useful
proxy for AI-assistant visibility — and it's FAR simpler to connect than Google:
one API key, no OAuth, no browser. Volume is much smaller than Google for niche
local queries, so treat Bing as a secondary signal, not the headline.

Auth (one-time, ~2 min): Bing Webmaster Tools → Settings → **API Access** →
generate an API key → put it in the env as BING_API_KEY (or pass --api-key).
The same `~/.config/gsc-insights/.env` the Serper key lives in is a fine home.

Endpoint: GetQueryStats returns ONE aggregate row per query over Bing's last
~6 months (Bing accepts no start/end dates — so there is no --days here).

Usage:
  export BING_API_KEY=...
  python bing_query.py --site https://example.com \
     --keywords "AI Events Munich,AI Meetups Munich,AI Treffen München" --out bing.md

Dependencies: requests (see ../requirements.txt)
"""

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

from _history import NOISE_IMPRESSIONS
from _lang_normalize import match_keywords as _match_keywords

try:
    import requests
except ImportError:
    print("Missing 'requests'. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(2)

API = "https://ssl.bing.com/webmaster/api.svc/json"


class BingApiError(requests.RequestException):
    """A failed Bing call, with the API key already redacted from the message.

    The original exception's request — and its response, when there is one —
    are deliberately NOT propagated: both carry the keyed URL (`.url`), which
    would undo the redaction. `status_code` is copied over on its own since a
    bare number isn't sensitive and lets a caller branch on 4xx vs 5xx.
    """
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


# Striking distance = ranking on roughly page 1-2 but not yet Top 10.
STRIKING_MIN, STRIKING_MAX = 8.0, 20.0
# Same rationale as gsc_query.py: an average position over a handful of
# impressions is noise, not a win (Bing aggregates ~6 months, so the bar
# still filters out one-off appearances).
STRIKING_MIN_IMPRESSIONS = 5
# Same threshold and rationale as gsc_query.py's TOTALS_MISMATCH_THRESHOLD.
TOTALS_MISMATCH_THRESHOLD = 0.10  # 10%
# Same default + override as gsc_query.py's DEFAULT_CSV / track.sh's CSV.
DEFAULT_CSV = os.environ.get("GSC_HISTORY_CSV", str(Path.home() / ".config" / "gsc-insights" / "history.csv"))


def eprint(*a):
    print(*a, file=sys.stderr)


def pct(x):
    return f"{x * 100:.1f}%"


def _fetch(endpoint, site, key):
    """GET one Bing endpoint and return the rows under the `d` node.

    The API key travels as a query parameter, so most `requests` error messages
    (HTTPError, ConnectionError, ...) embed the request URL WITH the key; the rest
    embed nothing sensitive, and redaction is a no-op on them.
    Callers print those messages to stderr, and the scheduled runs redirect stderr
    into a log file — so redact the key here, once, before anyone can print it.
    The redacted error is raised OUTSIDE the except block on purpose: that way
    neither __cause__ nor __context__ keeps the unredacted original alive
    (`raise ... from None` inside the handler would still keep it in __context__).
    """
    try:
        r = requests.get(f"{API}/{endpoint}",
                         params={"apikey": key, "siteUrl": site}, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        msg = str(e)
        if key:
            msg = msg.replace(key, "<redacted>")
            # requests encodes params with quote_plus (space → "+"), so match that
            msg = msg.replace(quote_plus(key), "<redacted>")
        # Belt and braces: also blank the apikey= query value structurally, so a
        # future change in how requests encodes params can't quietly re-leak it.
        # Literal pattern on purpose — never build a regex from the key itself.
        msg = re.sub(r"(apikey=)[^&\s]+", r"\1<redacted>", msg, flags=re.IGNORECASE)
        err = BingApiError(f"{type(e).__name__}: {msg}",
                           status_code=getattr(e.response, "status_code", None))
    else:
        return r.json().get("d", []) or []
    raise err  # deliberate: outside the except block, see docstring


def get_query_stats(site, key):
    """GetQueryStats → normalized rows. Bing wraps the list under the `d` node."""
    rows = _fetch("GetQueryStats", site, key)
    # Bing can return MORE than one row per query (observed live — e.g. per-date or
    # per-market buckets), so fold to one row per query: sum clicks/impressions and
    # impression-weight the average position (matches how GSC aggregates a period).
    agg = {}
    for it in rows:
        q = it.get("Query", "")
        impr = it.get("Impressions", 0) or 0
        clicks = it.get("Clicks", 0) or 0
        pos = it.get("AvgImpressionPosition", 0) or 0
        a = agg.setdefault(q, {"query": q, "impressions": 0, "clicks": 0, "_pw": 0.0})
        a["impressions"] += impr
        a["clicks"] += clicks
        a["_pw"] += pos * impr
    out = []
    for a in agg.values():
        impr = a["impressions"]
        if impr <= 0:
            continue  # 0 impressions → a 0/0 "position 0.0" would read as better-than-#1
        out.append({
            "query": a["query"],
            "impressions": impr,
            "clicks": a["clicks"],
            "position": a["_pw"] / impr,
            "ctr": a["clicks"] / impr,
        })
    return out


def fmt(rows, limit=20, key="query", label="Query"):
    L = [f"| {label} | Clicks | Impr. | CTR | Avg pos |", "|---|---:|---:|---:|---:|"]
    for r in rows[:limit]:
        L.append(f"| {r[key]} | {int(r['clicks'])} | {int(r['impressions'])} | "
                 f"{pct(r['ctr'])} | {r['position']:.1f} |")
    return "\n".join(L)


def get_page_stats(site, key):
    """GetPageStats — Bing reuses the QueryStats schema, so the PAGE URL lives in the
    `Query` field (Page/Url come back null). Aggregate by URL like get_query_stats."""
    rows = _fetch("GetPageStats", site, key)
    agg = {}
    for it in rows:
        url = it.get("Query", "")  # the URL is in Query for GetPageStats
        impr = it.get("Impressions", 0) or 0
        clicks = it.get("Clicks", 0) or 0
        pos = it.get("AvgImpressionPosition", 0) or 0
        a = agg.setdefault(url, {"page": url, "impressions": 0, "clicks": 0, "_pw": 0.0})
        a["impressions"] += impr
        a["clicks"] += clicks
        a["_pw"] += pos * impr
    out = []
    for a in agg.values():
        impr = a["impressions"]
        if impr <= 0:
            continue  # skip 0-impression pages (phantom position 0.0)
        out.append({"page": a["page"], "impressions": impr, "clicks": a["clicks"],
                    "position": a["_pw"] / impr,
                    "ctr": a["clicks"] / impr})
    return out


def match_keywords(rows, keywords):
    """[(keyword, matched_rows)], best match first — the one matcher shared
    with gsc_query.py (see _lang_normalize), same trend noise floor."""
    return _match_keywords(rows, keywords, lambda r: r["query"], NOISE_IMPRESSIONS)


def build_report(site, rows, kw_matches, page_rows=None):
    page_rows = page_rows or []
    L = [f"# Bing Webmaster insights — {site}", "",
         "_Bing aggregates the last ~6 months (no date range). Volume is much smaller "
         "than Google, but Bing's index feeds Copilot/ChatGPT._", ""]
    if not rows and not page_rows:
        L.append("> ⚠️ **No Bing query rows.** Either the site is newly added, has little "
                 "Bing traffic yet, or the API key / siteUrl is wrong. Confirm the property "
                 "is verified in Bing Webmaster Tools and that `--site` is the exact URL "
                 "registered there (https, trailing slash as shown in Bing).")
        return "\n".join(L)

    # Same query-vs-page reconciliation as gsc_query.py's build_report, and for
    # the same reason: GetQueryStats and GetPageStats are independent API calls
    # (see main()), so a total computed from queries alone can miss real
    # traffic the page-level pull still has, or vice versa. Unlike GSC, Bing's
    # API offers no property-level (dimensionless) total, so BOTH sums are
    # proxies: the page-level one is the better of the two but still counts
    # each page separately when several share one results page.
    tot_c = sum(int(r["clicks"]) for r in rows)
    tot_i = sum(int(r["impressions"]) for r in rows)
    tot_c_pages = sum(int(r["clicks"]) for r in page_rows)
    tot_i_pages = sum(int(r["impressions"]) for r in page_rows)
    if not page_rows:
        L.append(f"**Totals (query-level, page-level unavailable this run):** {tot_c} "
                 f"clicks, {tot_i} impressions across {len(rows)} queries.\n")
    elif not rows:
        L.append(f"**Totals (page-level, query-level unavailable this run):** "
                 f"{tot_c_pages} clicks, {tot_i_pages} impressions across "
                 f"{len(page_rows)} pages.\n")
    else:
        L.append(f"**Totals (page-level sum — the better proxy, but a ceiling: it "
                 f"counts each page separately when several share one results "
                 f"page):** {tot_c_pages} clicks, {tot_i_pages} impressions.\n")
        L.append(f"_Query-level, for reference only: {tot_c} clicks, {tot_i} "
                 f"impressions across {len(rows)} queries._\n")
        # Checked on both metrics, not impressions alone -- same reasoning as
        # gsc_query.py's build_report. Zero-safe: a 0-vs-nonzero pair is the
        # starkest disagreement, not a suppressed one.
        impr_mismatch = ((abs(tot_i_pages - tot_i) / tot_i_pages) if tot_i_pages > 0
                         else (1.0 if tot_i > 0 else 0))
        clicks_mismatch = ((abs(tot_c_pages - tot_c) / tot_c_pages) if tot_c_pages > 0
                           else (1.0 if tot_c > 0 else 0))
        flagged = [name for name, m in (("impressions", impr_mismatch), ("clicks", clicks_mismatch))
                   if m > TOTALS_MISMATCH_THRESHOLD]
        if flagged:
            threshold_pct = f"{TOTALS_MISMATCH_THRESHOLD * 100:.0f}%"
            metrics_str = " and ".join(flagged).capitalize()
            # Direction-neutral on purpose: with no property-level truth to
            # anchor on, picking a "right" side per metric would just guess.
            L.append(f"> ⚠️ {metrics_str} disagree by more than {threshold_pct} "
                     f"between the two Bing pulls — both are proxies (Bing has no "
                     f"property-level total), so avoid computing any \"site-wide\" "
                     f"percentage from Bing numbers at all.\n")

    L.append("## Target keywords — where we stand on Bing\n")
    for kw, m in kw_matches:
        if not m:
            L.append(f"- **{kw}** — _no Bing impressions_.")
            continue
        b = m[0]
        L.append(f"- **{kw}** — `{b['query']}`: avg position **{b['position']:.1f}**, "
                 f"{int(b['impressions'])} impr, {int(b['clicks'])} clicks, CTR {pct(b['ctr'])}")
        for r in m[1:3]:  # runners-up, so the pick can be checked at a glance
            L.append(f"  - also `{r['query']}`: position {r['position']:.1f}, "
                     f"{int(r['impressions'])} impr")
        if len(m) > 3:
            L.append(f"  - _+{len(m) - 3} more variants_")
    L.append("")

    in_range = [r for r in rows
                if STRIKING_MIN <= r["position"] <= STRIKING_MAX and r["impressions"] > 0]
    striking = sorted(
        [r for r in in_range if r["impressions"] >= STRIKING_MIN_IMPRESSIONS],
        key=lambda r: r["impressions"], reverse=True,
    )
    thin = len(in_range) - len(striking)
    L.append("## Striking-distance queries on Bing (pos ~8–20)\n")
    L.append(fmt(striking, 20) if striking
             else "_None in range" + (" with enough impressions to trust" if thin else "") + "._")
    if thin:
        L.append(f"\n_{thin} more in-range quer{'y' if thin == 1 else 'ies'} under "
                 f"{STRIKING_MIN_IMPRESSIONS} impressions not listed — too thin to "
                 f"call wins (still counted in the totals; the top-queries table "
                 f"shows the top 25)._")

    # Good-position-but-no-clicks pages (Bing's volume is tiny, so the bar is low).
    seen_unclicked = sorted(
        [r for r in page_rows if r["position"] <= 10 and r["clicks"] == 0 and r["impressions"] >= 2],
        key=lambda r: r["impressions"], reverse=True,
    )
    L.append("\n## Pages seen on Bing but not clicked (snippet/SERP investigation targets)\n")
    L.append(fmt(seen_unclicked, 15, key="page", label="Page") if seen_unclicked
             else "_None (need a page ranking ≤10 with 0 clicks and ≥2 impressions)._")

    L.append("\n## Top Bing queries\n")
    L.append(fmt(sorted(rows, key=lambda r: r["impressions"], reverse=True), 25))
    if page_rows:
        L.append("\n## Top Bing pages\n")
        L.append(fmt(sorted(page_rows, key=lambda r: r["impressions"], reverse=True), 15,
                     key="page", label="Page"))
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Pull Bing Webmaster query stats into a report.")
    ap.add_argument("--site", required=True,
                    help="Verified Bing site URL, e.g. https://example.com")
    ap.add_argument("--keywords", default="", help="Comma-separated target keywords.")
    ap.add_argument("--out", default="", help="Write the Markdown report to this file.")
    ap.add_argument("--api-key", default=os.environ.get("BING_API_KEY", ""))
    ap.add_argument("--csv", default=DEFAULT_CSV,
                    help="Append target-keyword positions to this history CSV (trend tracking). "
                         f"Defaults to {DEFAULT_CSV} (same file track.sh uses, override with "
                         "$GSC_HISTORY_CSV). Pass --no-csv to skip appending for this run.")
    ap.add_argument("--no-csv", action="store_true",
                    help="Don't append to the history CSV for this run.")
    args = ap.parse_args()

    if not args.api_key:
        eprint("No BING_API_KEY set — skipping Bing (the GSC Phase 1 data is unaffected).\n"
               "Get a key: Bing Webmaster Tools → Settings → API Access → generate, then:\n"
               "  export BING_API_KEY=...   (or add it to ~/.config/gsc-insights/.env)")
        sys.exit(3)

    try:
        rows = get_query_stats(args.site, args.api_key)
    except Exception as e:  # noqa: BLE001 — surface, don't hide (Rule 12)
        eprint(f"Bing API call failed: {e}")
        sys.exit(1)
    try:
        page_rows = get_page_stats(args.site, args.api_key)
    except Exception as e:  # noqa: BLE001 — pages are a bonus; degrade, don't abort
        eprint(f"Bing GetPageStats failed (continuing without page stats): {e}")
        page_rows = []

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    kw_matches = match_keywords(rows, keywords) if keywords else []

    history_failed = False
    if args.csv and not args.no_csv and kw_matches:
        import datetime as _dt
        import _history
        today = _dt.date.today().isoformat()
        site_key = _history.normalize_site(args.site)
        items = []
        for kw, matched in kw_matches:
            b = matched[0] if matched else None
            items.append({
                "date": today, "site": site_key, "source": "bing", "keyword": kw,
                "query": b["query"] if b else "",
                "position": round(b["position"], 1) if b else "",
                "impressions": int(b["impressions"]) if b else 0,
                "clicks": int(b["clicks"]) if b else 0,
                "window": "~180", "country": "",  # Bing: fixed ~6-month aggregate, no country param
            })
        try:
            n = _history.append_rows(args.csv, items)
            eprint(f"appended {n} keyword rows to {args.csv}")
        except Exception as e:  # noqa: BLE001 — history is a side effect; nothing
            # it can raise (write failure, lock contention, an unexpected
            # encoding/csv error) may cost the user the ranking report they
            # actually asked for. history_failed still surfaces it via a
            # distinct exit code once the report has printed, so a caller
            # that specifically depends on history (track.sh) can tell —
            # while an ad-hoc caller that only wants the report can ignore it.
            eprint(f"note: could not write history to {args.csv} ({e}) — "
                   f"continuing without it")
            history_failed = True

    report = build_report(args.site, rows, kw_matches, page_rows)
    print(report)
    if args.out:
        Path(args.out).write_text(report)
        eprint(f"\nWrote {args.out}")
    if history_failed:
        sys.exit(4)


if __name__ == "__main__":
    main()
