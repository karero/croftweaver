#!/usr/bin/env python3
"""Read-only probe of Search Console answers behind DESIGN-weekly-fix-proposal.md, section 1.

Usage (with the skill's venv and your own sign-in):
    ~/.config/gsc-insights/venv/bin/python fix_probe.py <domain> [--p2]

Prints facts only (counts, shares, dates, yes/no): no query text and no page address, so the
output can be quoted in a public repo. With --p2 it also prints, on stderr, one query where the
site ranks on page 1 and the page it lands on, for the by-eye Serper check; keep that line out of
the repo."""
import datetime as dt
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills/search-console-insights/scripts"))
import gsc_query as g  # noqa: E402

CFG = Path.home() / ".config/gsc-insights"
SITE = "sc-domain:" + sys.argv[1]
P2 = "--p2" in sys.argv[2:]

creds = g.load_credentials(CFG / "client_secret.json", CFG / "token.json", interactive=False)
svc = g.build_service(creds)
today = dt.date.today()


def raw(body):
    return svc.searchanalytics().query(siteUrl=SITE, body=body).execute()


def rows(start, end, dims, **extra):
    out, s = [], 0
    while True:
        b = {"startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": dims,
             "rowLimit": 25000, "startRow": s, **extra}
        page = raw(b).get("rows", [])
        out.extend(page)
        if len(page) < 25000:
            return out
        s += 25000


def pct(part, whole):
    return f"{100 * part / whole:.0f}%" if whole else "n/a"


# 1. When is metadata sent? A recent range (may hold incomplete days) and an old one (cannot).
recent = raw({"startDate": (today - dt.timedelta(days=10)).isoformat(), "endDate": today.isoformat(),
              "dimensions": ["date"], "dataState": "all"})
old_end = today - dt.timedelta(days=20)
old = raw({"startDate": (old_end - dt.timedelta(days=10)).isoformat(), "endDate": old_end.isoformat(),
           "dimensions": ["date"], "dataState": "all"})
fid = (recent.get("metadata") or {}).get("firstIncompleteDate")
print(f"[1] recent range: metadata={'yes' if recent.get('metadata') else 'no'} firstIncompleteDate={fid}; "
      f"range ending {old_end}: metadata={'yes' if old.get('metadata') else 'no'} {old.get('metadata')}")

# The window the report page uses (search_report.py, fetch_google): four full weeks ending on the
# last Sunday on or before the last finished day (the day before the first incomplete date).
finished = (dt.date.fromisoformat(fid) - dt.timedelta(days=1)) if fid else today - dt.timedelta(days=3)
end = finished - dt.timedelta(days=(finished.weekday() + 1) % 7)
start = end - dt.timedelta(days=27)
print(f"    window {start}..{end}")

# 2. How much of the property's total is in listed queries?
total = raw({"startDate": start.isoformat(), "endDate": end.isoformat()}).get("rows", [{}])
total_imp = total[0].get("impressions", 0) if total else 0
q = rows(start, end, ["query"])
q_imp = sum(r.get("impressions", 0) for r in q)
print(f"[2] query rows={len(q)}; share of the property's impressions in listed queries: {pct(q_imp, total_imp)}")

# 3. Per page: the page's own total against its split by query (the T2 question).
pages = rows(start, end, ["page"])
qp = rows(start, end, ["query", "page"])
split = defaultdict(float)
for r in qp:
    split[r["keys"][1]] += r.get("impressions", 0)
pages.sort(key=lambda r: -r.get("impressions", 0))


def bucket(n):
    return "100+" if n >= 100 else "50-99" if n >= 50 else "20-49" if n >= 20 else "<20"


print(f"[3] pages={len(pages)}; query-and-page rows={len(qp)}; top pages, split by query as a share of the page total:")
for n, r in enumerate(pages[:10], 1):
    t = r.get("impressions", 0)
    print(f"    page#{n} total {bucket(t)}: {pct(split.get(r['keys'][0], 0), t)}")

# 4. How many T1-like candidates (position 8-20), before brand is taken out?
for floor in (50, 20):
    c = [r for r in q if 8 <= (r.get("position") or 0) <= 20 and r.get("impressions", 0) >= floor]
    print(f"[4] queries at position 8-20 with {floor}+ impressions (brand not removed): {len(c)}")

# 5. Does a query's position by property differ from its by-page positions, weighted?
byq = defaultdict(lambda: [0.0, 0.0])
for r in qp:
    imp = r.get("impressions", 0)
    byq[r["keys"][0]][0] += imp * (r.get("position") or 0)
    byq[r["keys"][0]][1] += imp
diff = sum(1 for r in q if byq[r["keys"][0]][1]
           and abs(r.get("position", 0) - byq[r["keys"][0]][0] / byq[r["keys"][0]][1]) >= 1)
print(f"[5] queries whose property position and weighted page position differ by 1+ places: {diff} of {len(q)}")

if P2:
    first = [r for r in q if (r.get("position") or 99) <= 10 and r.get("impressions", 0) >= 20]
    first.sort(key=lambda r: -r.get("impressions", 0))
    if first:
        k = first[0]["keys"][0]
        land = max((r for r in qp if r["keys"][0] == k), key=lambda r: r.get("impressions", 0), default=None)
        print(f"P2 query: {k!r} position {first[0].get('position'):.1f}; page: {land['keys'][1] if land else '?'}",
              file=sys.stderr)
    else:
        print("P2: no query on page 1 with 20+ impressions in the window", file=sys.stderr)
