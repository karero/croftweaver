#!/usr/bin/env python3
"""
insights.py — the DEFAULT combined view: Google Search Console + Bing, side by side.

Auto-detects which free sources are connected and acts accordingly:
  • GSC connected (cached token) + Bing connected (API key) → show BOTH columns.
  • only one connected → show it, and nudge the user to connect the other (with the
    benefit + the ~2-min steps).
  • Serper key absent → suggest one, because the live competitor Top-10 is very useful
    (but it stays OPT-IN — it spends API quota — so this script never calls it).

Read-only, free. Reuses the pulls in gsc_query.py + bing_query.py (no duplication).

Usage:
  python insights.py --domain example.com \
     --keywords "AI Events Munich,AI Meetups Munich,AI Treffen München" [--days 90]
"""

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsc_query   # noqa: E402  — reuse its OAuth + Search Analytics pull
import bing_query  # noqa: E402  — reuse its API-key query pull

CONFIG = Path.home() / ".config" / "gsc-insights"
DEFAULT_TOKEN = CONFIG / "token.json"
DEFAULT_SECRET = CONFIG / "client_secret.json"
# Same default + override as gsc_query.py / bing_query.py / track.sh's CSV.
DEFAULT_CSV = os.environ.get("GSC_HISTORY_CSV", str(CONFIG / "history.csv"))
# A source returns None when NOT CONNECTED (no creds) vs FETCH_ERROR when it IS
# connected but the API call failed — so we never tell a connected user to re-set-up.
FETCH_ERROR = "__fetch_error__"


def eprint(*a):
    print(*a, file=sys.stderr)


def _best(kw_matches, keyfn):
    """{keyword: {'pos','impr','clicks','query'} | None} from a match_keywords() result."""
    out = {}
    for kw, matched in kw_matches:
        if matched:
            b = matched[0]
            out[kw] = {"pos": b["position"], "impr": b["impressions"],
                       "clicks": b["clicks"], "query": keyfn(b)}
        else:
            out[kw] = None
    return out


def gsc_positions(domain, keywords, days, client_secret, token, country=""):
    """Pull GSC positions — only if a cached token exists (never trigger OAuth here)."""
    if not Path(token).exists():
        return None  # not connected (or onboarding not finished)
    try:
        creds = gsc_query.load_credentials(Path(client_secret), Path(token), interactive=False)
        svc = gsc_query.build_service(creds)
        end = dt.date.today() - dt.timedelta(days=2)
        # GSC dates are inclusive: an N-day window is end-(N-1)..end.
        start = end - dt.timedelta(days=days - 1)
        rows = gsc_query.query(svc, f"sc-domain:{domain}",
                               start.isoformat(), end.isoformat(), ["query"],
                               country=country)
        return _best(gsc_query.match_keywords(rows, keywords), lambda r: r["keys"][0])
    except SystemExit:
        return None  # missing client_secret/deps → treat as not fully connected
    except Exception as e:  # noqa: BLE001 — connected, but the call failed
        eprint(f"GSC pull failed: {e}")
        return FETCH_ERROR


def bing_positions(domain, keywords, key):
    if not key:
        return None
    try:
        rows = bing_query.get_query_stats(f"https://{domain}", key)
        return _best(bing_query.match_keywords(rows, keywords), lambda r: r["query"])
    except Exception as e:  # noqa: BLE001 — connected, but the call failed
        eprint(f"Bing pull failed: {e}")
        return FETCH_ERROR


def cell(src, kw):
    if src is None:
        return "_not connected_"
    if src is FETCH_ERROR:
        return "⚠️ fetch failed"
    v = src.get(kw)
    return f"{v['pos']:.1f}" if v else "—"


def main():
    ap = argparse.ArgumentParser(description="Combined Google + Bing rankings.")
    ap.add_argument("--domain", required=True, help="e.g. example.com")
    ap.add_argument("--keywords", required=True, help="Comma-separated target keywords.")
    def _days(v):
        n = int(v)
        if n < 1:
            ap.error(f"--days must be >= 1 (got {v!r})")
        return n
    ap.add_argument("--days", type=_days, default=90)
    ap.add_argument("--client-secret", default=str(DEFAULT_SECRET))
    ap.add_argument("--token", default=str(DEFAULT_TOKEN))
    def _country(v):
        if v and (len(v) != 3 or not v.isalpha()):
            ap.error(f"--country takes ISO alpha-3, e.g. 'deu' not {v!r}")
        return v.lower()
    ap.add_argument("--country", default="", type=_country,
                    help="ISO-3166-1 alpha-3 GSC country filter, e.g. 'deu'. Google column "
                         "only — Bing's API has no country parameter, so its column stays "
                         "global; note that when comparing the two.")
    ap.add_argument("--csv", default=DEFAULT_CSV,
                    help="Append target-keyword positions to this history CSV (trend tracking). "
                         f"Defaults to {DEFAULT_CSV} (same file track.sh uses, override with "
                         "$GSC_HISTORY_CSV) so the default combined view builds history "
                         "automatically -- this is most users' actual entry point. Pass "
                         "--no-csv to skip appending for this run.")
    ap.add_argument("--no-csv", action="store_true",
                    help="Don't append to the history CSV for this run.")
    args = ap.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    serper = bool(os.environ.get("SERPER_API_KEY"))
    bing_key = os.environ.get("BING_API_KEY", "")

    gsc = gsc_positions(args.domain, keywords, args.days, args.client_secret, args.token,
                        country=args.country)
    bing = bing_positions(args.domain, keywords, bing_key)

    # Build history from this default entry point too, not just the single-engine
    # scripts -- most users' actual "where do I rank" ask goes through here, so
    # tying history-building to gsc_query.py/bing_query.py alone would miss most
    # runs. Only a genuinely successful pull (a dict) is recorded; None (not
    # connected) and FETCH_ERROR both stay out of the history.
    history_failed = False
    if args.csv and not args.no_csv:
        import datetime as _dt
        import _history
        today = _dt.date.today().isoformat()
        site_key = _history.normalize_site(args.domain)
        items = []
        if isinstance(gsc, dict):
            for kw in keywords:
                v = gsc.get(kw)
                items.append({
                    "date": today, "site": site_key, "source": "gsc", "keyword": kw,
                    "query": v["query"] if v else "",
                    "position": round(v["pos"], 1) if v else "",
                    "impressions": int(v["impr"]) if v else 0,
                    "clicks": int(v["clicks"]) if v else 0,
                    "window": args.days, "country": args.country or "",
                })
        if isinstance(bing, dict):
            for kw in keywords:
                v = bing.get(kw)
                items.append({
                    "date": today, "site": site_key, "source": "bing", "keyword": kw,
                    "query": v["query"] if v else "",
                    "position": round(v["pos"], 1) if v else "",
                    "impressions": int(v["impr"]) if v else 0,
                    "clicks": int(v["clicks"]) if v else 0,
                    "window": "~180", "country": "",
                })
        if items:
            try:
                n = _history.append_rows(args.csv, items)
                eprint(f"appended {n} keyword rows to {args.csv}")
            except Exception as e:  # noqa: BLE001 — history is a side effect;
                # nothing it can raise (write failure, lock contention, an
                # unexpected encoding/csv error) may cost the user the
                # ranking report they actually asked for.
                eprint(f"note: could not write history to {args.csv} ({e}) — "
                       f"continuing without it")
                history_failed = True

    print(f"# Rankings across Google & Bing — {args.domain}\n")
    if gsc is None and bing is None:
        print("> ⚠️ **Neither source is connected.** Connect Google Search Console first "
              "(the primary, free source) — ask me to *onboard Search Console*. Bing is an "
              "optional 2-minute add-on after that.")
        return

    print("| Keyword | Google (pos) | Bing (pos) |")
    print("|---|---|---|")
    for kw in keywords:
        print(f"| {kw} | {cell(gsc, kw)} | {cell(bing, kw)} |")
    print("\n_Lower position = better. “—” = connected but no impressions yet; "
          "“not connected” = that source isn’t set up._")
    if isinstance(gsc, dict) and isinstance(bing, dict):
        country_bit = (f" and the --country {args.country} filter (Google only)"
                       if args.country else "")
        print(f"\n_The two columns are not the same measurement — Google covers "
              f"your {args.days}-day window{country_bit}; Bing is a ~6-month "
              f"global aggregate. A difference can be window or geography, not "
              f"ranking._")

    # Cross-engine takeaways — where one engine ranks you Top-10 and the other doesn't.
    notes = []
    for kw in keywords:
        g = gsc.get(kw) if isinstance(gsc, dict) else None
        b = bing.get(kw) if isinstance(bing, dict) else None
        if g and b:
            if b["pos"] <= 10 < g["pos"]:
                notes.append(f"- **{kw}**: strong on **Bing** (#{b['pos']:.0f}) but weak on "
                             f"Google (#{g['pos']:.0f}) — good Copilot/ChatGPT visibility already.")
            elif g["pos"] <= 10 < b["pos"]:
                notes.append(f"- **{kw}**: strong on **Google** (#{g['pos']:.0f}) but weak on Bing.")
    if notes:
        print("\n**Where the engines disagree:**")
        print("\n".join(notes))

    # Suggest connecting whatever's missing (all free).
    sugg = []
    if gsc is None:
        sugg.append("- ⚠️ **Google Search Console not connected** — the primary source. "
                    "Ask me to *onboard Search Console* (~10 min, I do most of it).")
    if bing is None:
        sugg.append("- 💡 **Bing not connected** — a ~2-minute API key (Bing Webmaster Tools → "
                    "Settings → API Access). It's a Copilot/ChatGPT-visibility proxy and you "
                    "often rank *better* on Bing than Google. Add `BING_API_KEY` to "
                    "`~/.config/gsc-insights/.env`.")
    if not serper:
        sugg.append("- 💡 **No SERP key** — add a SERP API key (Serper is the default: "
                    "https://serper.dev, ~2,500 free/mo; SerpApi etc. also work) to see the live "
                    "**Top-10 competitors** for a keyword — who's beating you and what format wins, "
                    "not just your own data. Add `SERPER_API_KEY` to the `.env`, then run "
                    "`serp_check.py`. (Free tiers change — any SERP API works; see SKILL.md.)")
    if sugg:
        print("\n## Connect more (all free, read-only)\n")
        print("\n".join(sugg))
    elif isinstance(gsc, dict) and isinstance(bing, dict) and serper:
        print("\n✅ All three sources connected (Google, Bing, Serper). For competitors, "
              "run `serp_check.py` (opt-in — it spends Serper quota).")

    if history_failed:
        sys.exit(4)


if __name__ == "__main__":
    main()
