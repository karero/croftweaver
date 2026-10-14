#!/usr/bin/env python3
"""
analytics_snapshot.py — update a site's analytics/ folder from the saved reports (scenario B9).

    analytics_snapshot.py <domain> --site-dir <site folder> [--commit-ok]

Writes, inside <site folder>/analytics/:
  README.md                 what is here and why it stays off GitHub (rewritten each time)
  seo.html                  the latest Google & Bing page (search_report.py), linking to geo.html
  geo.html                  the latest "Does AI name you?" page, linking to seo.html
  <date>_gsc/               google-data.json, what the Google page was built from (date: when fetched)
  <date>_bing/              bing-history.csv, this site's Bing rows from the tracker (date: the latest row)
  <run date>_geo-run/       the newest AI-check run: its page and its answers

A dated folder that already exists is left as it is; a part that does not exist yet is named, never
faked. It reads only ~/.config/gsc-insights and fetches nothing, so build the reports first
(search_report.py, geo_check.py --report). Before writing, it checks that git would ignore the
folder (_analytics.check_kept_off). actions.md, eeat.md and the facts and positioning checks are
written by the assistant: see references/analytics-folder.md.
Exit 0 when something was written, 1 when nothing could be.
"""
import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _history import normalize_site  # noqa: E402
import _analytics  # noqa: E402

GEO_LINK = re.compile(r'href="\.\./\.\./geo/reports/[^"/]+/[^"/]+\.html"')      # on the Google page
GOOGLE_LINK = re.compile(r'href="\.\./\.\./\.\./reports/[^"/]+/google\.html"')    # on an AI-check page
RUN_ID = re.compile(r"^(\d{4})(\d{2})(\d{2})T")

README = """# Analytics for {site}

Written by search-console-insights (`analytics_snapshot.py`) and the assistant. This folder stays
off GitHub: the site's `.gitignore` holds `/analytics/`, because these files are the owner's data.

- `actions.md`: suggested actions by priority (P1 now, P2 soon, P3 when there is time), dated;
  done ones are marked done, never deleted.
- `eeat.md`: an E-E-A-T checklist, judged by the assistant. Google publishes no E-E-A-T score.
- `seo.html`: how people find the site on Google and Bing, including Google's AI Overviews and
  AI Mode and Bing's Copilot, as of the newest folder below.
- `geo.html`: whether AI assistants name the business, as of the newest `_geo-run` folder.
- `facts-history.csv`: one line per facts check, so drift in the site's figures shows over time.

Dated folders hold what one report was built from, date first so they sort by time:
`_gsc` (Search Console), `_bing` (Bing Webmaster), `_google-ai-report` and `_bing-ai-report`
(downloads as received), `_geo-run` (one AI check with every answer), `_facts-check`,
`_positioning-check`.
"""


def today():
    return dt.date.today()


def base_dir() -> Path:
    return Path(os.path.expanduser("~")) / ".config" / "gsc-insights"


def history_path(site):
    """The history file the site's weekly job uses (sites/<site>.json), else the shared default."""
    try:
        j = json.loads((base_dir() / "sites" / f"{site}.json").read_text(encoding="utf-8"))
        if isinstance(j, dict) and isinstance(j.get("csv"), str) and j["csv"]:
            return Path(os.path.expanduser(j["csv"]))
    except (ValueError, OSError):
        pass
    env = os.environ.get("GSC_HISTORY_CSV")
    return Path(os.path.expanduser(env)) if env else base_dir() / "history.csv"


def bing_rows(site):
    p = history_path(site)
    if not p.exists():
        return None, []
    with open(p, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get("source") == "bing" and normalize_site(r.get("site") or "") == site]
        return reader.fieldnames, rows


def snapshot(site, site_dir, commit_ok=False):
    """Returns the lines to print; raises _analytics.NotKeptOff when nothing may be written."""
    reports = base_dir() / "reports" / site
    google = reports / "google.html"
    data = reports / "google-data.json"
    geo_pages = sorted((base_dir() / "geo" / "reports" / site).glob("*.html"))
    fields, brows = bing_rows(site)
    if not (google.exists() or data.exists() or geo_pages or brows):
        raise _analytics.NotKeptOff(f"There are no reports for {site} yet: build them first "
                                    "(search_report.py, geo_check.py --report). Nothing was written.")
    _analytics.check_kept_off(site_dir, "README.md", commit_ok)
    a = Path(site_dir) / "analytics"
    a.mkdir(exist_ok=True)
    out = []
    (a / "README.md").write_text(README.format(site=site), encoding="utf-8")
    out.append("README.md: written")
    has_geo = bool(geo_pages)
    if google.exists():
        page = google.read_text(encoding="utf-8")
        page = GEO_LINK.sub('href="geo.html"', page) if has_geo else GEO_LINK.sub('href="#"', page)
        (a / "seo.html").write_text(page, encoding="utf-8")
        out.append("seo.html: written")
    else:
        out.append("seo.html: no Google & Bing page yet (run search_report.py)")
    if has_geo:
        newest = geo_pages[-1]
        (a / "geo.html").write_text(GOOGLE_LINK.sub('href="seo.html"', newest.read_text(encoding="utf-8")),
                                    encoding="utf-8")
        out.append("geo.html: written")
        m = RUN_ID.match(newest.stem)
        if m:
            folder = f"{m.group(1)}-{m.group(2)}-{m.group(3)}_geo-run"
            dest = a / folder
            if dest.exists():
                out.append(f"{folder}: already there, left as it is")
            else:
                dest.mkdir()
                (dest / newest.name).write_text(GOOGLE_LINK.sub('href="../seo.html"', newest.read_text(encoding="utf-8")),
                                                encoding="utf-8")
                answers = base_dir() / "geo" / "answers" / site / newest.stem
                if answers.is_dir():
                    shutil.copytree(answers, dest / "answers")
                out.append(f"{folder}: written")
    else:
        out.append("AI check: not set up for this site")
    if data.exists():
        try:
            fetched = dt.date.fromisoformat(str(json.loads(data.read_text(encoding="utf-8")).get("fetched")))
        except (ValueError, OSError, AttributeError):
            fetched = None
        if fetched:
            dest, new = _analytics.keep(site_dir, f"{fetched.isoformat()}_gsc", data)
            out.append(f"{dest.parent.name}: " + ("written" if new else "already there, left as it is"))
        else:
            out.append("Search Console data: its fetch date cannot be read, so it was not copied")
    if brows:
        latest = max(r.get("date", "") for r in brows)
        try:
            folder = f"{dt.date.fromisoformat(latest).isoformat()}_bing"
        except ValueError:
            folder = None
        if folder and (a / folder).exists():
            out.append(f"{folder}: already there, left as it is")
        elif folder:
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(brows)
            (a / folder).mkdir()
            (a / folder / "bing-history.csv").write_text(buf.getvalue(), encoding="utf-8")
            out.append(f"{folder}: written")
    else:
        out.append("Bing: no rows for this site in the tracker's history")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Update a site's analytics/ folder from the saved reports.")
    ap.add_argument("domain", help="e.g. example.com")
    ap.add_argument("--site-dir", required=True, help="the site's own folder (where its .gitignore is)")
    ap.add_argument("--commit-ok", action="store_true",
                    help="the owner chose to keep analytics/ in a private repo: skip the git check")
    args = ap.parse_args(argv)
    site = normalize_site(args.domain)
    try:
        site_dir = _analytics.site_folder(args.site_dir)
        lines = snapshot(site, site_dir, args.commit_ok)
    except _analytics.NotKeptOff as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"✗ Could not write: {e}", file=sys.stderr)
        return 1
    print(f"{site_dir}/analytics:")
    for line in lines:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
