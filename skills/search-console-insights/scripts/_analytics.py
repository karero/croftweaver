"""
_analytics.py — the site's analytics/ folder, shared by ai_reports.py and analytics_snapshot.py.

The folder is a kept copy, next to the site, of what the reports were built from; the skill never
reads from it (that stays ~/.config/gsc-insights). It holds the owner's data, and a site's repo
may be public, so every write first checks that git would ignore it, unless the owner chose to
keep the folder in a private repo (--commit-ok). Scenarios B1–B14:
docs/reviews/SKILL-PLAN-analytics-folder.md.
"""
import datetime as dt
import re
import shutil
import subprocess
from pathlib import Path

GOOGLE_DATE = re.compile(r"-(\d{4}-\d{2}-\d{2})(?:\.zip)?$", re.IGNORECASE)  # …-Features-2026-10-14.zip, or its folder
BING_DATE = re.compile(r"_(\d{1,2})_(\d{1,2})_(\d{4})\.csv$", re.IGNORECASE)   # …_AIPerformanceOverviewStats_10_14_2026.csv


class NotKeptOff(Exception):
    """The site folder is missing, or git would pick up its analytics/ folder."""


def folder_date(name, today):
    """The download's own date when its name carries one (Google: 2026-10-14; Bing: 10_14_2026, month
    first as Bing writes it), else today (B2)."""
    try:
        m = GOOGLE_DATE.search(name)
        if m:
            return dt.date.fromisoformat(m.group(1))
        m = BING_DATE.search(name)
        if m:
            return dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    except ValueError:
        pass
    return today


def site_folder(path):
    p = Path(path).expanduser()
    if not p.is_dir():
        raise NotKeptOff(f"The site folder {p} does not exist. Nothing was saved.")
    return p


def check_kept_off(site_dir, rel, commit_ok=False):
    """B3/B4: refuse unless git would ignore analytics/<rel> in site_dir. A folder outside any git
    repo has nothing to push; --commit-ok is the owner's own choice for a private repo (B5)."""
    if commit_ok:
        return
    try:
        inside = subprocess.run(["git", "-C", str(site_dir), "rev-parse", "--is-inside-work-tree"],
                                capture_output=True, text=True)
    except FileNotFoundError:          # no git on this computer: nothing can be pushed
        return
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return
    ignored = subprocess.run(["git", "-C", str(site_dir), "check-ignore", "-q", "--no-index", f"analytics/{rel}"],
                             capture_output=True)
    if ignored.returncode != 0:
        raise NotKeptOff(f"Git would put {site_dir}/analytics/ on GitHub. Add the line /analytics/ to the site's "
                         ".gitignore first: the folder holds the owner's data. (If the owner chose to keep it in a "
                         "private repo, pass --commit-ok.) Nothing was saved.")


def keep(site_dir, folder, src):
    """Copy src (a file, or a folder such as an unzipped download) into analytics/<folder>/; an
    existing copy is never overwritten. Returns (where it is, whether it was copied now)."""
    dest_dir = Path(site_dir) / "analytics" / folder
    dest = dest_dir / Path(src).name
    if dest.exists():
        return dest, False
    dest_dir.mkdir(parents=True, exist_ok=True)
    if Path(src).is_dir():
        shutil.copytree(src, dest)
    else:
        shutil.copy2(src, dest)
    return dest, True
