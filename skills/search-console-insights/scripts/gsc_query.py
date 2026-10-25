#!/usr/bin/env python3
"""
gsc_query.py — Phase 1 of the search-console-insights skill.

Pulls Google Search Console *Search Analytics* data (queries, pages, CTR,
average position) via the official API and writes a Markdown report that
surfaces the highest-leverage things:

  1. Where each TARGET keyword currently ranks (or "not yet ranking").
  2. Striking-distance queries (avg position ~8-20) — the fastest Top-10 wins.
  3. High-impression / low-CTR pages — snippet/SERP investigation targets
     (a title/meta rewrite only after the live-SERP check confirms a
     controllable snippet problem).
  4. On demand, query<->page attribution: --page <url> (which queries land on a
     page) and --query "<q>" (which pages serve a query) — so attribution and
     cannibalization are read from data, never guessed from separate tables.

Read-only: it uses the `webmasters.readonly` scope and never writes to GSC.

Auth: OAuth "installed app" (desktop) flow. You download an OAuth client
once from Google Cloud Console (Desktop app type) as
~/.config/gsc-insights/client_secret.json (the default; --client-secret or
$GSC_CLIENT_SECRET point elsewhere); the first run opens a browser for consent
and caches a refresh token at ~/.config/gsc-insights/token.json so later runs
are non-interactive.

Usage:
  python gsc_query.py \
      --site sc-domain:example.com \
      --days 90 \
      --keywords "AI Events Munich,AI Meetups Munich,AI Treffen München" \
      --out <site folder>/analytics/<today>_gsc/report.md   # make that folder first

Dependencies: see ../requirements.txt
"""

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

from _history import NOISE_IMPRESSIONS
from _lang_normalize import match_keywords as _match_keywords

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
DEFAULT_TOKEN = Path.home() / ".config" / "gsc-insights" / "token.json"
# Beside the token, as insights.py and search_report.py read it. Never the current folder:
# run from a site's folder, a client file found there could end up committed.
DEFAULT_SECRET = DEFAULT_TOKEN.parent / "client_secret.json"
# Same default + override as track.sh's CSV, so an ad-hoc run with --keywords
# builds the same history a scheduled track.sh run would -- no separate
# "remember to seed it" step. --no-csv opts a single run out.
DEFAULT_CSV = os.environ.get("GSC_HISTORY_CSV", str(Path.home() / ".config" / "gsc-insights" / "history.csv"))
ROW_LIMIT = 25000  # GSC max rows per request; plenty for a small site.

# Striking distance = ranking on roughly page 1-2 but not yet in the Top 10.
STRIKING_MIN, STRIKING_MAX = 8.0, 20.0
# An average position over a handful of impressions is noise, not a win — don't
# rank such rows as opportunities (they're still counted, never silently dropped).
STRIKING_MIN_IMPRESSIONS = 5
# A page in a good position that few people click = snippet OR SERP-context
# problem — the mandatory live-SERP check decides which.
LOW_CTR_MAX_POSITION = 10.0
LOW_CTR_THRESHOLD = 0.02  # 2%
# How far a dimensioned sum may drift from the property-level total before it's
# worth explaining (query-level: anonymization undercounts; page-level: several
# of your pages in one results page — e.g. brand sitelinks — overcount).
TOTALS_MISMATCH_THRESHOLD = 0.10  # 10%
LOW_CTR_MIN_IMPRESSIONS = 20


def eprint(*a):
    print(*a, file=sys.stderr)


def load_credentials(client_secret: Path, token_path: Path, interactive: bool = True):
    """OAuth installed-app flow with a cached, auto-refreshed token.

    interactive=False NEVER opens a browser: if the token is missing/expired and a
    silent refresh isn't possible, it raises instead of launching a consent flow —
    so non-interactive callers (insights.py's combined view) can't hang on a browser.
    Interactive, a refresh Google refuses (the sign-in was revoked, or it expired) falls
    through to the browser sign-in: that run is how the owner reconnects."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google.auth.exceptions import RefreshError
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        eprint(
            "Missing dependencies. Install them (locally, one-time):\n"
            "  pip install -r requirements.txt"
        )
        sys.exit(2)

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds
    refreshed = refused = False
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            refreshed = True
        except RefreshError:
            if not interactive:
                raise
            refused = True
    if not refreshed and not interactive:
        raise RuntimeError(
            "GSC token missing or expired and a silent refresh isn't possible — "
            "re-run the connect/onboarding step to re-consent.")
    if not refreshed:
        if not client_secret.exists():
            eprint(
                f"OAuth client not found: {client_secret}\n"
                "Create one in Google Cloud Console → APIs & Services → Credentials →\n"
                "  Create credentials → OAuth client ID → Application type: Desktop app,\n"
                "then download it as client_secret.json (see SKILL.md, one-time setup)."
            )
            sys.exit(2)
        if refused:
            eprint("Google refused the saved Search Console sign-in; opening the browser to sign in again.")
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
        creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    os.chmod(token_path, 0o600)
    return creds


def build_service(creds):
    try:
        from googleapiclient.discovery import build
    except ImportError:
        eprint("Missing google-api-python-client. Run: pip install -r requirements.txt")
        sys.exit(2)
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def query(service, site, start, end, dimensions, row_limit=ROW_LIMIT, country="",
          page="", query_str=""):
    body = {
        "startDate": start,
        "endDate": end,
        "rowLimit": row_limit,
    }
    if dimensions:
        body["dimensions"] = dimensions
    # No dimensions at all → GSC aggregates BY PROPERTY: one impression per
    # results page, however many of your pages appeared on it. That single row
    # is the only true site-wide total (page-sums overcount, query-sums
    # undercount — see build_report).
    filters = []
    if country:
        # ISO-3166-1 alpha-3, lowercase (GSC convention), e.g. 'deu' for Germany.
        # Without this, a bilingual/German-market site reads BLENDED global
        # averages — German positions get masked by (or fake) other markets'.
        filters.append({"dimension": "country", "expression": country.lower()})
    if page:
        filters.append({"dimension": "page", "expression": page})
    if query_str:
        filters.append({"dimension": "query", "expression": query_str})
    if filters:
        # groupType "and" is GSC's effective behavior for multiple filters
        # (verified empirically 2026-08-29: country+page returned the
        # intersection, not the union) — stated explicitly so nobody has to
        # re-litigate the API default.
        body["dimensionFilterGroups"] = [{"groupType": "and", "filters": filters}]
    resp = service.searchanalytics().query(siteUrl=site, body=body).execute()
    return resp.get("rows", [])


def pct(x):
    return f"{x * 100:.1f}%"


def fmt_rows(rows, dim_label, limit=20):
    """rows: GSC rows with keys[0] = the dimension value."""
    out = [f"| {dim_label} | Clicks | Impr. | CTR | Avg pos |",
           "|---|---:|---:|---:|---:|"]
    for r in rows[:limit]:
        key = r["keys"][0]
        out.append(
            f"| {key} | {int(r['clicks'])} | {int(r['impressions'])} | "
            f"{pct(r['ctr'])} | {r['position']:.1f} |"
        )
    return "\n".join(out)


def match_keywords(query_rows, keywords):
    """[(keyword, matched_rows)], best match first — see _lang_normalize.
    The floor is the trend's own: a row the tracker would flag as noise (`~`)
    shouldn't be the headline over one it wouldn't."""
    return _match_keywords(query_rows, keywords, lambda r: r["keys"][0],
                           NOISE_IMPRESSIONS)


def build_report(site, start, end, top_queries, top_pages, kw_matches,
                 perm_level, days, country="", site_total=None,
                 page_drill=None, page_url="", query_drill=None, query_term=""):
    L = []
    L.append(f"# Search Console insights — {site}")
    country_note = f", country filter: {country}" if country else ""
    L.append(f"\n_Window: {start} → {end} ({days} days){country_note}. Permission: "
             f"{perm_level or 'unknown'}._\n")

    st_has_data = bool(site_total) and (
        site_total.get("impressions", 0) > 0 or site_total.get("clicks", 0) > 0)
    total_clicks = sum(int(r["clicks"]) for r in top_queries)
    total_impr = sum(int(r["impressions"]) for r in top_queries)
    total_clicks_pages = sum(int(r["clicks"]) for r in top_pages)
    total_impr_pages = sum(int(r["impressions"]) for r in top_pages)
    dims_total = total_clicks + total_impr + total_clicks_pages + total_impr_pages
    # At the row cap a sum is possibly-truncated: "ceiling"/"anonymization"
    # claims must soften, since a truncated sum has no guaranteed relation
    # to the property total.
    q_capped = len(top_queries) >= ROW_LIMIT
    p_capped = len(top_pages) >= ROW_LIMIT

    # --- Honest emptiness check (Rule 12) ---------------------------------
    # Gated on every pull carrying zero DATA (not merely zero rows): the
    # pulls are independent API calls (see main()) and can diverge — one can
    # be genuinely empty (GSC's own anonymization, a transient hiccup) while
    # another still has real data. And a row whose metrics are all zero is
    # the same "nothing to see" as no row — reporting it as a divergence
    # between the pulls would be a false alarm.
    if not st_has_data and dims_total == 0:
        L.append("> ⚠️ **No Search Analytics data in this window.**\n>\n"
                 "> This is expected for a property verified recently — GSC only\n"
                 "> collects data *forward from verification*, with a ~2–3 day lag,\n"
                 "> and there is no historical backfill. Re-run this in 1–2 weeks.\n")
        if country:
            L.append(f"> Also note the active `--country {country}` filter — zero rows can\n"
                     f"> simply mean no traffic from that market in the window; re-run\n"
                     f"> without the filter to compare.\n")
        return "\n".join(L)

    # Three totals, three meanings, each from its own API call:
    #   property-level (no dimensions) — one impression per results page however
    #     many of your pages appeared on it: the only true site-wide figure and
    #     the only valid site-wide denominator.
    #   page-level sum — counts each of your pages separately when several share
    #     one results page (brand sitelinks!), so it can run ABOVE the truth.
    #   query-level sum — anonymization drops rare queries on thin sites, so it
    #     runs BELOW the truth.
    # An earlier fix (2026-08-27) blessed the page-level sum as "the real
    # figure" — replacing one wrong denominator with a subtler one. Both sums
    # are also capped at ROW_LIMIT rows; the property-level row is not.
    if st_has_data:
        st_clicks = int(site_total.get("clicks", 0))
        st_impr = int(site_total.get("impressions", 0))
        cflt = f", {country}-filtered" if country else ""
        L.append(f"**Site-wide total (property-level{cflt} — the denominator for "
                 f"any site-wide claim):** {st_clicks} clicks, {st_impr} "
                 f"impressions.\n")
        refs = []
        if top_pages:
            refs.append(f"page-level sum {total_clicks_pages} clicks / "
                        f"{total_impr_pages} impr (counts each page separately when "
                        f"several share one results page)")
        if top_queries:
            refs.append(f"query-level sum {total_clicks} clicks / {total_impr} impr "
                        f"(anonymization drops rare queries)")
        if refs:
            L.append("_For reference only, never as a denominator: "
                     + "; ".join(refs) + "._\n")
        # Both metrics, not impressions alone (page-sum clicks should track the
        # property's clicks closely — a click is attributed to one URL — so a
        # clicks-only divergence is a real, silent anomaly). Zero-safe: 0 vs
        # nonzero is the starkest disagreement, not a suppressed one. Both
        # DIRECTIONS: the expected direction gets its known explanation, the
        # unexpected one an explicit "this isn't the normal pattern" flag.
        def _div(sum_v, prop_v):
            if prop_v > 0:
                return abs(sum_v - prop_v) / prop_v > TOTALS_MISMATCH_THRESHOLD
            return sum_v > 0
        if top_pages:
            # Sitelinks explain exactly one pattern: IMPRESSIONS inflated
            # above a positive property figure. Clicks attribute to one URL
            # (the sums should match), and a zero or below-property figure
            # isn't multi-page counting — those get the anomaly message.
            if (st_impr > 0 and
                    (total_impr_pages - st_impr) / st_impr > TOTALS_MISMATCH_THRESHOLD):
                L.append(f"> ⚠️ **The page-level sum diverges above the property "
                         f"total (impressions)** — several of your pages often "
                         f"appear in the same results page (typically brand "
                         f"sitelinks). A percentage computed against the page-level "
                         f"sum understates every share.\n")
            anom = [m for m, s, p in (("impressions", total_impr_pages, st_impr),
                                      ("clicks", total_clicks_pages, st_clicks))
                    if _div(s, p) and not (m == "impressions" and p > 0 and s > p)]
            if anom:
                L.append(f"> ⚠️ **The page-level sum diverges from the property "
                         f"total ({' and '.join(anom)}) in a way sitelinks can't "
                         f"explain** — row-cap truncation, or transient divergence "
                         f"between the independent pulls. Treat both numbers with "
                         f"caution this run.\n")
        if top_queries:
            metrics = (("impressions", total_impr, st_impr),
                       ("clicks", total_clicks, st_clicks))
            under = [m for m, s, p in metrics if _div(s, p) and s <= p]
            q_over = [m for m, s, p in metrics if _div(s, p) and s > p]
            if under:
                cov = (f"; query rows cover {total_impr / st_impr:.0%} of impressions"
                       if "impressions" in under and st_impr > 0 else "")
                cause = ("GSC is anonymizing rare queries on this site"
                         + (" and/or the row cap truncated the pull" if q_capped else ""))
                L.append(f"> ⚠️ **The query-level sum diverges below the property "
                         f"total ({' and '.join(under)}{cov})** — {cause}. Individual "
                         f"query rows are fine; their sum is not a total.\n")
            if q_over:
                L.append(f"> ⚠️ **The query-level sum runs above the property total "
                         f"({' and '.join(q_over)}) — the unexpected direction** "
                         f"(not the anonymization pattern; transient divergence). "
                         f"Re-pull before quoting either.\n")
    else:
        # Property-level didn't deliver — distinguish an explicit zero row
        # (the pulls disagree outright) from no row at all (pull unavailable).
        if site_total is not None:
            L.append(f"> ⚠️ **Property-level total returned 0 clicks / 0 impressions "
                     f"while the dimensioned reports below have data** — the "
                     f"independent pulls disagree outright; re-pull before quoting "
                     f"any of these as a total.\n")
        else:
            L.append(f"> ⚠️ **Property-level totals unavailable this run.**\n")
        if top_pages:
            if p_capped:
                L.append(f"**Site-wide (page-level sum, row-capped — partial, bounds "
                         f"unknown):** {total_clicks_pages} clicks, "
                         f"{total_impr_pages} impressions.\n")
            else:
                L.append(f"**Site-wide (page-level sum, ceiling — counts each of "
                         f"your pages separately when several share one results "
                         f"page):** {total_clicks_pages} clicks, "
                         f"{total_impr_pages} impressions.\n")
        elif q_capped:
            L.append(f"**Site-wide (query-level sum, row-capped — partial, bounds "
                     f"unknown):** {total_clicks} clicks, {total_impr} impressions.\n")
        else:
            L.append(f"**Site-wide (query-level sum, floor — undercounts rare "
                     f"queries on a thin site):** {total_clicks} clicks, "
                     f"{total_impr} impressions.\n")
    if len(top_pages) >= ROW_LIMIT or len(top_queries) >= ROW_LIMIT:
        L.append(f"> ⚠️ **A dimensioned pull hit the {ROW_LIMIT}-row cap** — that "
                 f"sum may be partial, and truncation (not just anonymization) can "
                 f"explain gaps against the property total.\n")
    if not top_queries:
        L.append(f"> ⚠️ **Query-level report returned no rows this window.** The "
                 f"\"Target keywords\" section below will show every keyword as \"no "
                 f"impressions yet\" — that reflects missing query-level detail this "
                 f"run, not necessarily zero real traffic.\n")
    if not top_pages:
        L.append(f"> ⚠️ **Page-level report returned no rows this window.** The "
                 f"top-pages and low-CTR sections below reflect a missing page-level "
                 f"pull this run, not an absence of pages.\n")

    # --- Target keywords ---------------------------------------------------
    L.append("## Target keywords — where we stand\n")
    for kw, matched in kw_matches:
        if not matched:
            L.append(f"- **{kw}** — _no impressions yet_ (not surfacing in Google "
                     "for this term in this window).")
            continue
        best = matched[0]
        L.append(f"- **{kw}** — best match `{best['keys'][0]}`: "
                 f"avg position **{best['position']:.1f}**, "
                 f"{int(best['impressions'])} impr, {int(best['clicks'])} clicks, "
                 f"CTR {pct(best['ctr'])}")
        # Show the runners-up so the pick can be checked at a glance — a mis-pick
        # was invisible when only the winner printed.
        for r in matched[1:3]:
            L.append(f"  - also `{r['keys'][0]}`: position {r['position']:.1f}, "
                     f"{int(r['impressions'])} impr")
        if len(matched) > 3:
            L.append(f"  - _+{len(matched) - 3} more variants_")
    L.append("")

    # --- Striking distance -------------------------------------------------
    in_range = [r for r in top_queries
                if STRIKING_MIN <= r["position"] <= STRIKING_MAX and r["impressions"] > 0]
    striking = sorted(
        [r for r in in_range if r["impressions"] >= STRIKING_MIN_IMPRESSIONS],
        key=lambda r: r["impressions"], reverse=True,
    )
    thin = len(in_range) - len(striking)
    L.append("## Striking-distance queries (pos ~8–20 = fastest Top-10 wins)\n")
    if striking:
        L.append(fmt_rows(striking, "Query", limit=20))
    else:
        L.append("_None in range yet"
                 + (" with enough impressions to trust" if thin else "") + "._")
    if thin:
        L.append(f"\n_{thin} more in-range quer{'y' if thin == 1 else 'ies'} under "
                 f"{STRIKING_MIN_IMPRESSIONS} impressions not listed as wins — an "
                 f"average position over a handful of impressions is noise, not a "
                 f"signal (still counted in the totals; the top-queries table shows "
                 f"the top 25)._")
    L.append("")

    # --- Low-CTR pages -----------------------------------------------------
    low_ctr = sorted(
        [r for r in top_pages
         if r["position"] <= LOW_CTR_MAX_POSITION
         and r["ctr"] < LOW_CTR_THRESHOLD
         and r["impressions"] >= LOW_CTR_MIN_IMPRESSIONS],
        key=lambda r: r["impressions"], reverse=True,
    )
    L.append("## Good position, low CTR — snippet/SERP investigation candidates\n")
    if low_ctr:
        L.append(fmt_rows(low_ctr, "Page", limit=15))
        L.append("\n_Position and CTR here are page-level averages across every query that "
                 "landed on the page, not one query's numbers -- re-run with "
                 "`--page <url>` for a candidate page to see which specific queries land "
                 "on it before diagnosing a snippet problem._"
                 "\n\n→ Before rewriting: check the live SERP snippet (`serp_check.py`) "
                 "against the page's actual shipped meta description (mandatory, see "
                 "\"Reading the numbers\" in SKILL.md). Then hand off to `copywriting` "
                 "(title) + `website-seo-geo` (meta-description limits).")
    else:
        L.append("_None flagged (need pages ranking ≤10 with CTR <2% and ≥20 impr)._")
    L.append("")

    # --- Attribution drill-downs (only when requested) ---------------------
    if page_url:
        L.append(f"## Queries landing on {page_url}\n")
        if page_drill:
            L.append(fmt_rows(page_drill, "Query", limit=15))
            L.append("\n_Attribution from GSC itself (query rows filtered to this "
                     "page). Rare queries can still be anonymized away, so rows here "
                     "may not sum to the page's total impressions._")
        else:
            L.append("_No query rows for this page in the window. The `--page` "
                     "filter is an exact URL match — compare against the top-pages "
                     "table first (https vs http, trailing slash, www) — and rare "
                     "queries can also be anonymized away even when the page itself "
                     "shows impressions._")
        L.append("")
    if query_term:
        L.append(f"## Pages serving \"{query_term}\"\n")
        if query_drill:
            L.append(fmt_rows(query_drill, "Page", limit=15))
            if sum(1 for r in query_drill if r["impressions"] > 0) > 1:
                L.append("\n_More than one page draws impressions for this exact "
                         "query. That can be benign — several of your pages sharing "
                         "one results page (sitelinks), or URLs alternating over "
                         "the window — or it can be cannibalization. Compare their "
                         "positions and intents before concluding; if it is "
                         "cannibalization, ask which page Google prefers and whether "
                         "it's the one you'd pick._")
        else:
            L.append("_No pages returned for this exact query in the window (the "
                     "filter is an exact match — check spelling/casing against the "
                     "top-queries table)._")
        L.append("")

    # --- Reference tables --------------------------------------------------
    L.append("## Top queries\n")
    L.append(fmt_rows(top_queries, "Query", limit=25))
    L.append("\n## Top pages\n")
    L.append(fmt_rows(top_pages, "Page", limit=25))
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Pull GSC Search Analytics into a report.")
    ap.add_argument("--site", required=True,
                    help="Property, e.g. sc-domain:example.com or "
                         "https://example.com/")
    def _days(v: str) -> int:
        n = int(v)
        if n < 1:
            raise argparse.ArgumentTypeError(f"--days must be >= 1 (got {v!r})")
        return n
    ap.add_argument("--days", type=_days, default=90)
    ap.add_argument("--keywords", default="",
                    help="Comma-separated target keywords.")
    ap.add_argument("--out", default="", help="Write the Markdown report to this file.")
    ap.add_argument("--client-secret",
                    default=os.environ.get("GSC_CLIENT_SECRET", str(DEFAULT_SECRET)))
    ap.add_argument("--token", default=str(DEFAULT_TOKEN))
    def _country(v: str) -> str:
        # GSC matches lowercase alpha-3; the natural mistake is alpha-2 ('de',
        # the convention serp_check's --gl uses) — which matches NOTHING and
        # reads as "no impressions yet". Reject it loudly instead.
        if v and (len(v) != 3 or not v.isalpha()):
            raise argparse.ArgumentTypeError(f"--country takes ISO alpha-3, e.g. 'deu' (got {v!r})")
        return v.lower()
    ap.add_argument("--country", default="", type=_country,
                    help="ISO-3166-1 alpha-3 country filter, e.g. 'deu' — see the "
                         "German-market note in SKILL.md. Default: all countries blended. "
                         "(Google only; Bing has no country parameter.)")
    ap.add_argument("--csv", default=DEFAULT_CSV,
                    help="Append target-keyword positions to this history CSV (trend tracking). "
                         f"Defaults to {DEFAULT_CSV} (same file track.sh uses, override with "
                         "$GSC_HISTORY_CSV) so a plain run with --keywords builds history "
                         "automatically. Pass --no-csv to skip appending for this run.")
    ap.add_argument("--no-csv", action="store_true",
                    help="Don't append to the history CSV for this run.")
    ap.add_argument("--page", default="",
                    help="Full URL: also report which queries land on THIS page "
                         "(attribution from data, not inference).")
    ap.add_argument("--query", default="",
                    help="Exact query string: also report which pages serve it "
                         "(cannibalization check).")
    ap.add_argument("--no-browser", action="store_true",
                    help="Never open a browser for sign-in: if the saved token can't be "
                         "refreshed silently, exit 2 with instructions (track.sh uses this, "
                         "so a scheduled run can't hang waiting for a browser nobody opens).")
    args = ap.parse_args()

    if args.no_browser:
        try:
            from google.auth.exceptions import RefreshError
        except ImportError:  # load_credentials reports missing dependencies itself
            RefreshError = RuntimeError
        try:
            creds = load_credentials(Path(args.client_secret), Path(args.token), interactive=False)
        except (RuntimeError, RefreshError) as e:
            eprint(f"Search Console sign-in needs renewing ({type(e).__name__}: {e}).\n"
                   "Ask Claude to reconnect Search Console (it re-runs the one-time sign-in).")
            sys.exit(2)
    else:
        creds = load_credentials(Path(args.client_secret), Path(args.token))
    service = build_service(creds)

    # Confirm access + capture permission level (proxy for "is this set up?").
    perm_level = None
    try:
        sites = service.sites().list().execute().get("siteEntry", [])
        for s in sites:
            if s.get("siteUrl") == args.site:
                perm_level = s.get("permissionLevel")
        if perm_level is None:
            eprint(f"Note: {args.site} not in your verified properties. "
                   "Check the --site value (sc-domain:… for a Domain property) "
                   "and that verification (search-console-setup) is done.")
    except Exception as e:  # noqa: BLE001 — surface, don't hide (Rule 12)
        eprint(f"Could not list sites (continuing): {e}")

    end = dt.date.today() - dt.timedelta(days=2)   # GSC lags ~2 days
    # GSC treats start/end as INCLUSIVE dates, so an N-day window spans
    # end-(N-1)..end — subtracting N would silently pull N+1 days.
    start = end - dt.timedelta(days=args.days - 1)
    s_start, s_end = start.isoformat(), end.isoformat()

    try:
        top_queries = query(service, args.site, s_start, s_end, ["query"], country=args.country)
        top_pages = query(service, args.site, s_start, s_end, ["page"], country=args.country)
    except Exception as e:  # noqa: BLE001
        eprint(f"Search Analytics query failed: {e}")
        sys.exit(1)

    # The property-level pull degrades on its own: build_report handles
    # site_total=None honestly, so a transient error here must not cost the
    # reader the dimensioned report.
    site_total = None
    try:
        # No dimensions → the property-level totals row (the true site-wide figure).
        totals_rows = query(service, args.site, s_start, s_end, [], country=args.country)
        site_total = totals_rows[0] if totals_rows else None
    except Exception as e:  # noqa: BLE001
        eprint(f"property-level totals pull failed (continuing without it): {e}")

    # Drill-downs degrade on their own — a malformed --page/--query must not
    # cost the reader the base report. On failure the section is omitted
    # (clearing the term below), not rendered as a misleading "no rows".
    page_drill = query_drill = None
    page_url, query_term = args.page, args.query
    if args.page:
        try:
            page_drill = query(service, args.site, s_start, s_end, ["query"],
                               country=args.country, page=args.page)
        except Exception as e:  # noqa: BLE001
            eprint(f"--page drill-down failed (continuing without it): {e}")
            page_url = ""
    if args.query:
        try:
            query_drill = query(service, args.site, s_start, s_end, ["page"],
                                country=args.country, query_str=args.query)
        except Exception as e:  # noqa: BLE001
            eprint(f"--query drill-down failed (continuing without it): {e}")
            query_term = ""

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    kw_matches = match_keywords(top_queries, keywords) if keywords else []

    history_failed = False
    if args.csv and not args.no_csv and kw_matches:
        import _history
        today = dt.date.today().isoformat()
        site_key = _history.normalize_site(args.site)
        items = []
        for kw, matched in kw_matches:
            b = matched[0] if matched else None
            items.append({
                "date": today, "site": site_key, "source": "gsc", "keyword": kw,
                "query": b["keys"][0] if b else "",
                "position": round(b["position"], 1) if b else "",
                "impressions": int(b["impressions"]) if b else 0,
                "clicks": int(b["clicks"]) if b else 0,
                "window": args.days, "country": args.country or "",
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

    report = build_report(args.site, s_start, s_end, top_queries, top_pages,
                          kw_matches, perm_level, args.days, country=args.country,
                          site_total=site_total,
                          page_drill=page_drill, page_url=page_url,
                          query_drill=query_drill, query_term=query_term)
    print(report)
    if args.out:
        Path(args.out).write_text(report)
        eprint(f"\nWrote {args.out}")
    if history_failed:
        sys.exit(4)


if __name__ == "__main__":
    main()
