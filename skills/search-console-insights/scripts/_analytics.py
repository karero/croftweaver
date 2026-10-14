"""
_analytics.py — the site's analytics/ folder, shared by ai_reports.py and analytics_snapshot.py.

The folder is a kept copy, next to the site, of what the reports were built from; the skill never
reads from it (that stays ~/.config/gsc-insights). It holds the owner's data, and a site's repo
may be public, so before a run writes anything, every path it will write is checked: none may be
tracked by git, and git must ignore all of them, unless the owner chose to keep the folder in a
private repo (--commit-ok). A file already kept is never rewritten: different content under the
same name is kept beside it (name-2.ext). Scenarios B1–B14: docs/reviews/SKILL-PLAN-analytics-folder.md.
"""
import datetime as dt
import filecmp
import os
import re
import shutil
import subprocess
from pathlib import Path

# Google: …-Features-2026-10-14.zip (or its unzipped folder); Bing: …_AIPerformanceOverviewStats_10_14_2026.csv,
# month first, as the owner's real download of 2026-10-14 was named. A browser adds " (1)" to a second download.
GOOGLE_DATE = re.compile(r"-(\d{4}-\d{2}-\d{2})(?: \(\d+\))?(?:\.zip)?$", re.IGNORECASE)
BING_DATE = re.compile(r"_(\d{1,2})_(\d{1,2})_(\d{4})(?: \(\d+\))?\.csv$", re.IGNORECASE)


class NotKeptOff(Exception):
    """The site folder is missing, or git would (or might) put something under analytics/ on GitHub."""


def folder_date(name, today):
    """The download's own date when its name carries one, else today (B2)."""
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


def _git(site_dir, *args, stdin=None):
    env = dict(os.environ, LC_ALL="C", LANGUAGE="C")      # git's own words, whatever the screen language
    return subprocess.run(["git", "-C", str(site_dir), *args], input=stdin, capture_output=True, text=True, env=env)


def check_kept_off(site_dir, rels, commit_ok=False):
    """B3/B4, for EVERY path a run will write (rels: relative to analytics/). Refuses when one is
    tracked (rewriting it would be a committable change) or not ignored. A folder outside any git
    repo has nothing to push; a git error refuses rather than guess."""
    if commit_ok or not rels:
        return
    try:
        inside = _git(site_dir, "rev-parse", "--is-inside-work-tree")
    except FileNotFoundError:          # no git on this computer: nothing can be pushed
        return
    if inside.returncode != 0:
        # Only git's own "no repository here or above" is a folder with nothing to push; any other
        # error (a GIT_DIR that points nowhere says "not a git repository" too) refuses.
        if "or any of the parent directories" in inside.stderr and not os.environ.get("GIT_DIR"):
            return
        first = (inside.stderr.strip().splitlines() or ["no message"])[0]
        raise NotKeptOff(f"Git could not say whether {site_dir}/analytics/ stays off GitHub ({first}). "
                         "Nothing was saved.")
    if inside.stdout.strip() != "true":     # e.g. inside a .git folder: no work tree to judge
        raise NotKeptOff(f"{site_dir} is not inside a git work tree git can judge. Nothing was saved.")
    paths = [f"analytics/{r}" for r in rels]
    listed = _git(site_dir, "ls-files", "-z", "--", *paths)
    if listed.returncode != 0:
        raise NotKeptOff(f"Git could not list what it tracks in {site_dir} "
                         f"({(listed.stderr.strip().splitlines() or ['no message'])[0]}). Nothing was saved.")
    tracked = [p for p in listed.stdout.split("\0") if p]
    if tracked:
        raise NotKeptOff(f"Git already tracks {tracked[0]}, so rewriting it would put the change on GitHub. "
                         "Nothing was saved. (If the owner chose to keep analytics/ in a private repo, pass --commit-ok.)")
    checked = _git(site_dir, "check-ignore", "--no-index", "-z", "--stdin", stdin="\0".join(paths) + "\0")
    if checked.returncode not in (0, 1):        # 1 = none of them ignored, an answer; anything else an error
        raise NotKeptOff(f"Git could not say what it ignores in {site_dir} "
                         f"({(checked.stderr.strip().splitlines() or ['no message'])[0]}). Nothing was saved.")
    ignored = {p for p in checked.stdout.split("\0") if p}
    missing = [p for p in paths if p not in ignored]
    if missing:
        raise NotKeptOff(f"Git would put {site_dir}/{missing[0]} on GitHub. Add the line /analytics/ to the "
                         "site's .gitignore first: the folder holds the owner's data. (If the owner chose to "
                         "keep it in a private repo, pass --commit-ok.) Nothing was saved.")


def _same(a: Path, b: Path):
    if a.is_dir() != b.is_dir():
        return False
    if a.is_file():
        return filecmp.cmp(a, b, shallow=False)
    left = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    right = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    return left == right and all(filecmp.cmp(a / r, b / r, shallow=False) for r in left)


def _numbered(name, n):
    p = Path(name)
    return f"{p.stem}-{n}{p.suffix}" if p.suffix else f"{name}-{n}"


def plan(site_dir, folder, src):
    """Where keep() will put src under analytics/<folder>/, as (destination, the paths it writes
    relative to analytics/); (existing copy, []) when an identical copy is already there."""
    dest_dir = Path(site_dir) / "analytics" / folder
    src = Path(src)
    dest, n = dest_dir / src.name, 1
    while dest.exists():
        if _same(src, dest):
            return dest, []
        n += 1
        dest = dest_dir / _numbered(src.name, n)
    base = f"{folder}/{dest.name}"
    staging = f"{folder}/{dest.name}.partial"          # keep() copies here first: checked like the rest
    if src.is_dir():
        files = [p.relative_to(src).as_posix() for p in sorted(src.rglob("*")) if p.is_file()]
        return dest, ([f"{base}/{f}" for f in files] + [f"{staging}/{f}" for f in files]) or [base, staging]
    return dest, [base, staging]


def keep(site_dir, folder, src):
    """Copy src (a file, or a folder such as an unzipped download) into analytics/<folder>/. Never
    overwrites: different content under a taken name gets name-2, name-3 …. Staged under a .partial
    name and then renamed, so a failed copy never looks finished. Returns (where it is, copied now)."""
    dest, writes = plan(site_dir, folder, src)
    if not writes:
        return dest, False
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".partial")
    if tmp.is_dir():
        shutil.rmtree(tmp)
    elif tmp.exists():
        tmp.unlink()
    try:
        if Path(src).is_dir():
            shutil.copytree(src, tmp)
        else:
            shutil.copy2(src, tmp)
        os.replace(tmp, dest)
    except OSError:
        unkeep(tmp)            # no half copy left behind under a name git might not ignore
        raise
    return dest, True


def unkeep(dest):
    """Undo keep() when what it was kept for failed (ai_reports.py: the import could not be saved)."""
    if Path(dest).is_dir():
        shutil.rmtree(dest)
    elif Path(dest).exists():
        Path(dest).unlink()
    try:
        Path(dest).parent.rmdir()          # only when that left the dated folder empty
    except OSError:
        pass
