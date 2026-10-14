#!/usr/bin/env python3
"""
analytics_snapshot.py — update a site's analytics/ folder from the saved reports (scenario B9).

    analytics_snapshot.py <domain> --site-dir <site folder> [--commit-ok]

Writes, inside <site folder>/analytics/:
  README.md                 what is here and why it stays off GitHub (rewritten each time)
  seo.html                  the latest Google & Bing page (search_report.py), linking to geo.html
  geo.html                  the latest "Does AI name you?" page, linking to seo.html
  <date>_gsc/               google-data.json, what the Google page was built from (date: when fetched),
                            and the fix proposal's record (<site>-proposals.json) as it is now
  <date>_bing/              bing-history.csv, this site's Bing rows from the tracker (date: the latest row)
  <run date>_geo-run/       the newest AI-check page, and the answers of every run it lists (meta geo-runs)

A file already kept is never rewritten (different content under the same name is kept beside it,
name-2); seo.html, geo.html and README.md are the latest views and are rewritten. A part that does
not exist yet is named, never faked. It reads only ~/.config/gsc-insights and fetches nothing, so
build the reports first (search_report.py, geo_check.py --report). Every path it will write is
checked first (_analytics.check_kept_off); a refusal writes nothing. actions.md, eeat.md and the facts and positioning checks are
written by the assistant: see references/analytics-folder.md.
Exit 0 when something was written, 1 when nothing could be.
"""
import argparse
import csv
import datetime as dt
import hashlib
import html.parser
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _history import normalize_site  # noqa: E402
import _analytics  # noqa: E402
import search_report  # noqa: E402
import fix_proposal  # noqa: E402



class _Page(html.parser.HTMLParser):
    """The page's links and its <meta name=… content=…> records, read as a browser would (any quoting)."""

    def __init__(self, text):
        super().__init__()
        self.hrefs, self.meta = [], {}
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("href") is not None:
            self.hrefs.append(a["href"].strip())
        if tag == "meta" and a.get("name"):
            self.meta[a["name"]] = a.get("content") or ""


def leftover_links(text, allowed=()):
    """Links that still climb out of the analytics folder ("../…"), apart from the allowed ones."""
    return [h for h in _Page(text).hrefs
            if h.startswith("../") and h.split("#")[0].split("?")[0] not in allowed]


GEO_LINK = re.compile(r'href="\.\./\.\./geo/reports/[^"/]+/[^"/]+\.html"')      # on the Google page
GOOGLE_LINK = re.compile(r'href="\.\./\.\./\.\./reports/[^"/]+/google\.html"')    # on an AI-check page
RUN_ID = re.compile(r"^(\d{4})(\d{2})(\d{2})T")

README = """# Analytics for {site}

Written by search-console-insights (`analytics_snapshot.py`) and the assistant. This folder stays
off GitHub: the site's `.gitignore` holds `/analytics/`, because these files are the owner's data.

- `actions.md`: suggested actions by priority (P1 now, P2 soon, P3 when there is time), dated;
  done ones are marked done, never deleted.
- `eeat.md`: an E-E-A-T checklist, judged by the assistant. Google says E-E-A-T itself isn't a
  specific ranking factor, and these reports collect no signal for it.
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


def snapshot(site, site_dir, commit_ok=False, csv_path=None):
    """Returns the lines to print; raises _analytics.NotKeptOff when nothing may be written."""
    reports = base_dir() / "reports" / site
    google = reports / "google.html"
    data = reports / "google-data.json"
    geo_pages = sorted((base_dir() / "geo" / "reports" / site).glob("*.html"))
    # The Bing rows the Google & Bing page uses: the same settings and history file it resolves.
    _, rows = search_report.resolve_settings(site, SimpleNamespace(keywords=None, country=None, csv=csv_path))
    brows = [r for r in rows if r.get("source") == "bing"]
    if not (google.exists() or data.exists() or geo_pages or brows):
        raise _analytics.NotKeptOff(f"There are no reports for {site} yet: build them first "
                                    "(search_report.py, geo_check.py --report). Nothing was written.")
    has_geo = bool(geo_pages)
    out, top, kept = [], {"README.md": README.format(site=site)}, []
    # The Google page is read once: seo.html and the data check use the same text (F50).
    google_text, google_unreadable = None, False
    if google.exists():
        try:
            google_text = google.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            google_unreadable = True
    has_google = google_text is not None
    with tempfile.TemporaryDirectory() as tmpd:
        stage = Path(tmpd)
        if has_google:
            top["seo.html"] = GEO_LINK.sub('href="geo.html"' if has_geo else 'href="#"', google_text)
        elif google_unreadable:
            out.append("seo.html: the Google & Bing page cannot be read, so it was not copied")
        else:
            out.append("seo.html: no Google & Bing page yet (run search_report.py)")
        if has_geo:
            newest = geo_pages[-1]
            page = newest.read_text(encoding="utf-8")
            top["geo.html"] = GOOGLE_LINK.sub('href="seo.html"' if has_google else 'href="#"', page)
            m = RUN_ID.match(newest.stem)
            if m:
                folder = f"{m.group(1)}-{m.group(2)}-{m.group(3)}_geo-run"
                (stage / newest.name).write_text(GOOGLE_LINK.sub('href="../seo.html"' if has_google else 'href="#"', page),
                                                 encoding="utf-8")
                kept.append((folder, stage / newest.name))
                recorded = _Page(page).meta.get("geo-runs")
                if recorded is None:                # no guessing: only the page knows which runs it shows
                    out.append(f"AI-check answers: {newest.name} was built before pages listed their runs, so its "
                               "answers were not kept; rebuild it (geo_check.py --report) and run this again")
                for run in sorted(set((recorded or "").split())):
                    answers = base_dir() / "geo" / "answers" / site / run
                    if answers.is_dir():
                        kept.append((f"{folder}/answers", answers))
                    else:
                        out.append(f"AI-check answers of run {run}: not on this computer, so not kept")
            else:
                out.append(f"AI-check run: {newest.name} carries no run date, so its answers were not kept")
        else:
            out.append("AI check: not set up for this site")
        if data.exists() and google_unreadable:
            out.append("Search Console data: not kept, because the page it belongs to cannot be read to check it")
        elif data.exists():
            # The data is the page's evidence only when it is what the page shows: the page carries the
            # fingerprint of its data (search_report.data_fingerprint), and a failed save leaves an older file.
            shown = _Page(google_text).meta.get("gsc-data-sha256") if has_google else None
            try:
                raw = data.read_bytes()
                fetched = dt.date.fromisoformat(str(json.loads(raw.decode("utf-8")).get("fetched")))
            except (ValueError, OSError, AttributeError, UnicodeDecodeError):
                fetched = None
            if fetched is None:
                out.append("Search Console data: its fetch date cannot be read, so it was not kept")
            elif shown is not None and shown != hashlib.sha256(raw).hexdigest():
                out.append("Search Console data: the saved copy is not what seo.html shows (it could not be "
                           "saved when the page was built), so it was not kept")
            else:      # keep the bytes just checked, not a re-read of a file a refresh may be rewriting
                (stage / data.name).write_bytes(raw)
                kept.append((f"{fetched.isoformat()}_gsc", stage / data.name))
                # The page's fix-proposal section shows figures from the proposal's own record, which no
                # fingerprint covers: kept beside the data as it is now, and said so (merge link, F53).
                try:
                    proposals = fix_proposal.state_path(site)
                except ValueError:
                    proposals = None
                if has_google and proposals is not None and proposals.is_file():
                    try:
                        (stage / proposals.name).write_bytes(proposals.read_bytes())
                        kept.append((f"{fetched.isoformat()}_gsc", stage / proposals.name))
                        out.append("Fix proposal: its record is kept as it is now; unlike the data, it is not "
                                   "matched to seo.html")
                    except OSError:
                        out.append("Fix proposal: its record cannot be read, so it was not kept")
                if has_google and shown is None:
                    out.append("Search Console data: seo.html predates its fingerprint, so the match was not checked")
        else:
            out.append("Search Console data: none saved yet (run search_report.py)")
        if brows:
            try:
                latest = dt.date.fromisoformat(max(r.get("date", "") for r in brows))
                buf = io.StringIO()
                w = csv.DictWriter(buf, fieldnames=list(brows[0].keys()), lineterminator="\n")
                w.writeheader()
                w.writerows(brows)
                (stage / "bing-history.csv").write_text(buf.getvalue(), encoding="utf-8")
                kept.append((f"{latest.isoformat()}_bing", stage / "bing-history.csv"))
            except ValueError:
                out.append("Bing: the newest row's date cannot be read, so the rows were not kept")
        else:
            out.append("Bing: no rows for this site in the tracker's history")
        # Every path this run writes, checked before the first write (B3/B4).
        writes = list(top) + [w for folder, src in kept for w in _analytics.plan(site_dir, folder, src)[1]]
        _analytics.check_kept_off(site_dir, writes, commit_ok)
        a = Path(site_dir) / "analytics"
        a.mkdir(exist_ok=True)
        for name, text in top.items():
            (a / name).write_text(text, encoding="utf-8")
            out.insert(0, f"{name}: written")
            if leftover_links(text):
                out.append(f"warning: {name} still links into the hidden settings folder; tell the owner")
        for folder, src in kept:
            dest, new = _analytics.keep(site_dir, folder, src)
            rel = dest.relative_to(a).as_posix()
            out.append(f"{rel}: kept" if new else f"{rel}: already kept, left as it is")
            if folder.endswith("_geo-run") and leftover_links(dest.read_text(encoding="utf-8"), ("../seo.html",)):
                out.append(f"warning: {rel} still links into the hidden settings folder; tell the owner")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Update a site's analytics/ folder from the saved reports.")
    ap.add_argument("domain", help="e.g. example.com")
    ap.add_argument("--site-dir", required=True, help="the site's own folder (where its .gitignore is)")
    ap.add_argument("--csv", default=None, help="the history file, when the Google & Bing page was built with --csv")
    ap.add_argument("--commit-ok", action="store_true",
                    help="the owner chose to keep analytics/ in a private repo: skip the git check")
    args = ap.parse_args(argv)
    site = normalize_site(args.domain)
    try:
        site_dir = _analytics.site_folder(args.site_dir)
        lines = snapshot(site, site_dir, args.commit_ok, args.csv)
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
