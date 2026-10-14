#!/usr/bin/env python3
"""
ai_reports.py — read Google's and Bing's own AI reports, which the owner downloads by hand.

    ai_reports.py import <domain> <file or folder>   # Google's zip (or the folder Safari unzipped
                                                      # it to), or Bing's AI Performance CSV
    ai_reports.py not-shown <domain>                  # Search Console shows no generative AI
                                                      # report for this site (scenario A3)

Neither report can be read by a program, so the owner downloads it and this script keeps what it
read in ~/.config/gsc-insights/reports/<site>/ai-google.json or ai-bing.json, where
search_report.py shows it. The latest file replaces the earlier one. A file it cannot read, or
one for another site, is refused with the reason and nothing is saved (exit 1).

The rules (scenario ids A1–A10) are in docs/reviews/SKILL-PLAN-ai-reports.md. In short: Google's
files are named and headed in the language of the owner's Search Console screen, so each file is
recognised by its contents (dates, addresses), never by its name; Google's total is the chart's,
never the sum of pages (one answer can show two pages); Bing's export is a daily overview whose
"Cited Pages" cannot be added up across days.
"""
import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _history import normalize_site  # noqa: E402

DAY = re.compile(r"^(\d{4}-\d{2}-\d{2})(?: - (\d{4}-\d{2}-\d{2}))?$")   # a day, or a week "a - b"
NAME_DOMAIN = re.compile(r"^((?:[a-z0-9-]+\.)+[a-z]{2,})[-_]")          # "example.com-Perf…", "example.com_AIPerf…"


class Refused(Exception):
    """The file is not one this script can read, or is for another site."""


def today():
    return dt.date.today()


def base_dir() -> Path:
    return Path(os.path.expanduser("~")) / ".config" / "gsc-insights"


def bare(host):
    host = (host or "").lower()
    return host[4:] if host.startswith("www.") else host


def known_sites():
    names = set()
    for sub, pattern in (("sites", "*.json"), ("reports", "*")):
        d = base_dir() / sub
        if d.is_dir():
            names |= {bare(p.stem if sub == "sites" else p.name) for p in d.glob(pattern)}
    return names


def check_name(path: Path, site):
    """A9: both Google and Bing start the file name with the domain. Another domain is refused; no
    domain at all is fine for an owner with one site, and refused when there are several."""
    m = NAME_DOMAIN.match(path.name.lower())
    if m:
        if bare(m.group(1)) != bare(site):
            raise Refused(f"This file is for {m.group(1)}, not {site}. Nothing was saved.")
        return
    if known_sites() - {bare(site)}:
        raise Refused(f"The file name doesn't say which site it is for, and you have more than one site. "
                      f"Keep the name it was downloaded with, or rename it to start with {site}.")


def number(text):
    """An impressions or citations count; thousands separators allowed. None if it isn't one."""
    s = re.sub(r"[\s,.' ]", "", (text or "").strip())
    return int(s) if s.isdigit() else None


def rows_of(text):
    return [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]


# ─── Google ────────────────────────────────────────────────────────────────────────────────

def read_bundle(path: Path):
    """[(file name, text)] for every CSV in Google's zip, or in the folder it was unzipped to."""
    out = []
    try:
        if path.is_dir():
            for p in sorted(path.iterdir()):
                if p.suffix.lower() == ".csv" and not p.name.startswith("."):
                    out.append((p.name, p.read_bytes().decode("utf-8-sig")))
        else:
            with zipfile.ZipFile(path) as z:
                for i in z.infolist():
                    name = i.filename.rsplit("/", 1)[-1]
                    if name.lower().endswith(".csv") and not name.startswith(".") and "__MACOSX" not in i.filename:
                        out.append((name, z.read(i).decode("utf-8-sig")))
    except (zipfile.BadZipFile, UnicodeDecodeError, OSError) as e:
        raise Refused(f"Could not read {path.name}: {e}. Nothing was saved.")
    return out


def parse_google(files, site):
    chart, page_rows, search_type, seen, wide, counted, headers_only = None, None, "", [], False, False, False
    for name, text in files:
        rows = rows_of(text)
        if not rows:
            continue
        head, body = rows[0], rows[1:]
        seen.append(f"{name} ({', '.join(head)})")
        if len(head) != 2:
            wide = wide or len(head) >= 4
            continue
        if not body:
            headers_only = True
            continue
        firsts, counts = [r[0].strip() for r in body], [number(r[1]) if len(r) > 1 else None for r in body]
        counted = counted or any(c is not None for c in counts)
        if body and all(DAY.match(f) for f in firsts) and None not in counts:
            if chart is not None:
                raise Refused("This download has two files with dates in them; I can't tell which is the chart. "
                              "Nothing was saved.")
            chart = [(DAY.match(f).group(1), DAY.match(f).group(2) or DAY.match(f).group(1), n)
                     for f, n in zip(firsts, counts)]
        elif body and all(f.lower().startswith(("http://", "https://")) for f in firsts) and None not in counts:
            page_rows = list(zip(firsts, counts))
        elif body and None in counts and not search_type:
            search_type = body[0][1].strip() if len(body[0]) > 1 else ""   # the filter file: its first row
    if chart is None:
        if headers_only and not wide and not counted:     # headers only: Google had no rows to give (A2)
            return {"state": "empty", "first": None, "last": None, "total": 0, "pages": [], "search_type": search_type}
        hint = (" This looks like Search Console's ordinary Performance report; open the generative AI report "
                "and export that instead." if wide else "")
        raise Refused("This is not Google's generative AI report: I found no file with dates and impressions. "
                      f"Found: {'; '.join(seen) or 'no CSV files'}.{hint} Nothing was saved.")
    for url, _ in page_rows or []:
        host = urlsplit(url).hostname or ""
        if bare(host) != bare(site):
            raise Refused(f"This download's pages belong to {host}, not {site}. Nothing was saved.")
    total = sum(n for _, _, n in chart)
    shown = sorted(((u, n) for u, n in page_rows or [] if n > 0), key=lambda x: -x[1])
    return {"state": "data" if total > 0 else "empty", "first": min(a for a, _, _ in chart),
            "last": max(b for _, b, _ in chart), "total": total,
            "pages": [list(p) for p in shown], "search_type": search_type}


# ─── Bing ──────────────────────────────────────────────────────────────────────────────────

def _dates(texts):
    """Bing's dates ('7/14/2026 12:00:00 AM'), as consecutive days. Month first as Bing writes them;
    day first only if month first cannot be read or runs out of order. Neither: refused."""
    parts = [t.strip().split(" ")[0] for t in texts]
    if all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", p) for p in parts):
        tries = [lambda p: dt.date.fromisoformat(p)]
    else:
        def md(p, month_first):
            a, b, y = re.split(r"[/.]", p)
            return dt.date(int(y), int(a), int(b)) if month_first else dt.date(int(y), int(b), int(a))
        tries = [lambda p: md(p, True), lambda p: md(p, False)]
    for parse in tries:
        try:
            days = [parse(p) for p in parts]
        except (ValueError, TypeError):
            continue
        if all((b - a).days == 1 for a, b in zip(days, days[1:])):
            return days
    raise Refused("The dates in this file can't be read as one day after another. Nothing was saved.")


def parse_bing(text):
    rows = rows_of(text)
    if len(rows) < 2 or any(len(r) != 3 for r in rows):
        found = ", ".join(rows[0]) if rows else "nothing"
        raise Refused("This is not Bing's AI Performance export (Date, Citations, Cited Pages). "
                      f"Found: {found}. Nothing was saved.")
    body = rows[1:]
    cites = [number(r[1]) for r in body]
    if None in cites or None in [number(r[2]) for r in body]:
        raise Refused("Some citation counts in this file are not numbers. Nothing was saved.")
    days = _dates([r[0] for r in body])
    total = sum(cites)
    return {"state": "data" if total > 0 else "empty", "first": days[0].isoformat(), "last": days[-1].isoformat(),
            "citations": total, "days": len(days), "days_cited": sum(1 for c in cites if c > 0)}


# ─── commands ──────────────────────────────────────────────────────────────────────────────

def save(site, source, record):
    record = dict(record, source=source, added=today().isoformat())
    path = base_dir() / "reports" / site / f"ai-{source}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, indent=1), encoding="utf-8")
    os.replace(tmp, path)
    return path


def do_import(site, path: Path):
    if not path.exists():
        raise Refused(f"{path} does not exist.")
    check_name(path, site)
    suffix = path.suffix.lower()
    if path.is_dir() or suffix == ".zip":
        rec = parse_google(read_bundle(path), site)
        save(site, "google", dict(rec, file=path.name))
        if rec["state"] == "empty":
            return "Google: no impressions in AI answers yet. Saved; that is a result, not a fault."
        return (f"Google: {rec['total']:,} impressions in AI answers, {rec['first']} to {rec['last']}, "
                f"{len(rec['pages'])} pages. Saved.")
    if suffix == ".csv":
        try:
            text = path.read_bytes().decode("utf-8-sig")
        except (UnicodeDecodeError, OSError) as e:
            raise Refused(f"Could not read {path.name}: {e}. Nothing was saved.")
        head = rows_of(text)[:1]
        if head and len(head[0]) == 2:
            raise Refused("This is one file from Google's download. Give me the whole .zip, or the folder it "
                          "unzipped to. Nothing was saved.")
        rec = parse_bing(text)
        save(site, "bing", dict(rec, file=path.name))
        if rec["state"] == "empty":
            return "Bing: no citations in AI answers yet. Saved; that is a result, not a fault."
        return f"Bing: {rec['citations']:,} citations, {rec['first']} to {rec['last']}. Saved."
    raise Refused(f"{path.name} is not a CSV or zip file. Export the report as CSV. Nothing was saved.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read Google's or Bing's downloaded AI report for one site.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    imp = sub.add_parser("import", help="read a downloaded report")
    imp.add_argument("domain")
    imp.add_argument("file")
    ns = sub.add_parser("not-shown", help="record that Search Console shows no AI report for this site")
    ns.add_argument("domain")
    args = ap.parse_args(argv)
    site = normalize_site(args.domain)
    try:
        if args.cmd == "not-shown":
            save(site, "google", {"state": "not_shown", "checked": today().isoformat()})
            print("Google: no AI report shown for this site; recorded as checked today.")
        else:
            print(do_import(site, Path(os.path.expanduser(args.file))))
    except Refused as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"✗ Could not save: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
