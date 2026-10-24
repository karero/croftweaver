#!/usr/bin/env python3
"""
serp_check.py — Phase 2/3 of the search-console-insights skill.

GSC only shows YOUR data — it can't tell you who holds the Top 10 for a
keyword you don't rank for yet. This script fetches the live Google Top-10
for each target keyword so you can see the competitors, the result *format*
Google rewards (event aggregators vs. listicle guides), and your own true
position (or absence).

Also prints each result's rendered SNIPPET. Google frequently discards the
shipped <meta description> and auto-generates a snippet from body text
instead — confirmed live 2026-07-30 (a real site), where a "truncation caused
0% CTR" diagnosis turned out to be flatly wrong for one page (the description
was never shown at all) while holding for another (it was shown, truncated).
ALWAYS compare the printed snippet against the actual shipped description
before attributing a CTR gap to description wording — do not diagnose from
GSC numbers alone.

Providers (pluggable, both have a free tier):
  - serper  (default) — https://serper.dev  — 2,500 free searches, no card.
  - serpapi            — https://serpapi.com — 250 free searches / month.

API key comes from the environment; the script EXITS CLEARLY if it's unset,
so the rest of the skill (free Phase-1 GSC data) still works without it.

  export SERPER_API_KEY=...      # for --provider serper (default)
  export SERPAPI_KEY=...         # for --provider serpapi

Usage:
  python serp_check.py \
      --keywords "AI Events Munich,AI Meetups Munich,AI Treffen München" \
      --domain example.com

The SERP language (hl) defaults to the target country's language: gl=de/at/ch →
hl=de, everything else hl=en. gl defaults to 'de'. Override with --hl / --gl.

Dependencies: requests (see ../requirements.txt)
"""

import argparse
import os
import sys

try:
    import requests
except ImportError:
    print("Missing 'requests'. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(2)

def eprint(*a):
    print(*a, file=sys.stderr)


def auto_hl(gl: str) -> str:
    """Default the SERP language to the target country's language.

    Was a 5-word German hint list matched against the keyword — which classified
    'Zahnarzt Köln' as English and queried a mixed-locale SERP whose features and
    competitors differ from what a German searcher sees. If you target Germany
    (gl=de) you almost always want German-language results; --hl overrides for
    the exceptions (e.g. English-keyword checks against the German index).
    """
    return {"de": "de", "at": "de", "ch": "de"}.get(gl.lower(), "en")


def serper(keyword, gl, hl, num, key):
    r = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": key, "Content-Type": "application/json"},
        json={"q": keyword, "gl": gl, "hl": hl, "num": num},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return [
        {"position": o.get("position"), "title": o.get("title", ""),
         "link": o.get("link", ""), "snippet": o.get("snippet", "")}
        for o in data.get("organic", [])
    ]


def serpapi(keyword, gl, hl, num, key):
    r = requests.get(
        "https://serpapi.com/search.json",
        params={"engine": "google", "q": keyword, "gl": gl, "hl": hl,
                "num": num, "api_key": key},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    out = []
    for o in data.get("organic_results", []):
        out.append({"position": o.get("position"), "title": o.get("title", ""),
                    "link": o.get("link", ""), "snippet": o.get("snippet", "")})
    return out


PROVIDERS = {
    "serper": (serper, "SERPER_API_KEY", "https://serper.dev (2,500 free, no card)"),
    "serpapi": (serpapi, "SERPAPI_KEY", "https://serpapi.com (250 free / month)"),
}


def main():
    ap = argparse.ArgumentParser(description="Live Google Top-10 per keyword.")
    ap.add_argument("--keywords", required=True, help="Comma-separated keywords.")
    ap.add_argument("--domain", required=True,
                    help="Your domain, e.g. example.com — flagged in results if present.")
    ap.add_argument("--provider", choices=PROVIDERS.keys(), default="serper")
    ap.add_argument("--gl", default="de", help="Country (default de = Germany).")
    ap.add_argument("--hl", default="", help="Language; default follows --gl (de/at/ch → de, else en).")
    ap.add_argument("--num", type=int, default=10)
    args = ap.parse_args()

    fn, key_env, signup = PROVIDERS[args.provider]
    key = os.environ.get(key_env)
    if not key:
        eprint(f"No {key_env} set — skipping competitive SERP (Phase 1 GSC data is\n"
               f"unaffected). Get a free key at {signup}, then:\n"
               f"  export {key_env}=...")
        sys.exit(3)

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    used = 0
    target = args.domain.lower().replace("www.", "")

    for kw in keywords:
        hl = args.hl or auto_hl(args.gl)
        print(f"\n## {kw}   (gl={args.gl}, hl={hl})\n")
        try:
            results = fn(kw, args.gl, hl, args.num, key)
            used += 1
        except Exception as e:  # noqa: BLE001 — surface, don't hide
            eprint(f"  query failed: {e}")
            continue

        ours = None
        our_snippet = ""
        for o in results[: args.num]:
            mark = ""
            if target in o["link"].lower():
                mark = "  ← US"
                ours = o["position"]
                our_snippet = o.get("snippet", "")
            print(f"{o['position']:>2}. {o['title'][:70]}{mark}")
            print(f"    {o['link']}")
            if o.get("snippet"):
                print(f"    snippet: {o['snippet'][:160]}")
        if ours:
            print(f"\n→ {args.domain} ranks #{ours} for \"{kw}\".")
            # The rendered snippet is frequently NOT the shipped <meta description> —
            # Google auto-generates from body text a large share of the time. A CTR
            # diagnosis built on "the description is too long/short" without checking
            # this is unverified at best. Confirmed live 2026-07-30 (a real site): one
            # page's real 318-char description was fully discarded for an auto-generated
            # body-text snippet, while a different page's real (145-char) description WAS
            # shown, truncated. Compare `our_snippet` above against the page's actual
            # <meta description> by hand before concluding truncation (or anything else
            # about the description) explains a CTR gap.
            if our_snippet:
                print(f"  Compare the snippet above against the page's actual <meta description> —\n"
                      f"  do not assume they match.")
        else:
            print(f"\n→ {args.domain} NOT in Top {args.num} for \"{kw}\".")

    cap = "2,500 (Serper)" if args.provider == "serper" else "250/month (SerpApi)"
    eprint(f"\nSearches used this run: {used}. Free-tier cap: {cap}.")


if __name__ == "__main__":
    main()
