"""The site's analytics/ folder: ai_reports.py --keep-in and analytics_snapshot.py.

Why: the folder keeps, next to the site, what the reports were built from, and the owner's data in
it must never reach GitHub unasked (a site's repo may be public). So every write first checks that
git would ignore it, a refused download is never kept, a dated folder that exists is left alone,
and the copied pages link to each other, not into the hidden settings folder. Each test pins one
scenario of docs/reviews/SKILL-PLAN-analytics-folder.md (B2–B4, B9) and enters through the calls
production makes: `ai_reports.main([...])` and `analytics_snapshot.main([...])`.

Run:  python3 -m unittest discover -s skills/search-console-insights/scripts/tests
"""
import contextlib
import datetime as dt
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import ai_reports as ar  # noqa: E402
import analytics_snapshot as snap  # noqa: E402

TODAY = dt.date(2026, 10, 14)
SITE = "example.com"
GOOGLE_ZIP = f"{SITE}-Performance-on-Search-Generative-AI-Features-2026-10-11.zip"
BING_CSV = f"{SITE}_AIPerformanceOverviewStats_10_13_2026.csv"
RUN = "20261012T070010Z-174318-29336-a2f8"


def google_files():
    chart = "Datum,Impressionen\n2026-10-01,4\n2026-10-02,6"
    return {"Diagramm.csv": chart, "Seiten.csv": f"Die häufigsten Seiten,Impressionen\nhttps://{SITE}/,10",
            "Länder.csv": "Land,Impressionen\nDeutschland,10", "Geräte.csv": "Gerät,Impressionen\nComputer,10",
            "Filter.csv": "Filtern,Wert\nSuchtyp,Web (text-based)"}


def bing_csv():
    return '﻿"Date","Citations","Cited Pages"\r\n"10/1/2026 12:00:00 AM","2","1"\r\n"10/2/2026 12:00:00 AM","0","0"\r\n'


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class AnalyticsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.home = root / "home"
        self.cfg = self.home / ".config/gsc-insights"
        self.cfg.mkdir(parents=True)
        self.downloads = root / "Downloads"
        self.downloads.mkdir()
        self.site_dir = root / "Websites" / "example"
        self.site_dir.mkdir(parents=True)
        self.env = mock.patch.dict(os.environ, {"HOME": str(self.home), "GIT_CONFIG_NOSYSTEM": "1",
                                                "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                                                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"})
        self.env.start()
        for k in ("GSC_HISTORY_CSV", "GSC_COUNTRY", "BING_API_KEY"):
            os.environ.pop(k, None)
        self.today = [mock.patch.object(ar, "today", lambda: TODAY), mock.patch.object(snap, "today", lambda: TODAY)]
        for p in self.today:
            p.start()

    def tearDown(self):
        for p in self.today:
            p.stop()
        self.env.stop()
        self.tmp.cleanup()

    # ── the site folder as a git repo ──
    def repo(self, ignore=True):
        git("init", "-q", cwd=self.site_dir)
        if ignore:
            (self.site_dir / ".gitignore").write_text("node_modules/\n/analytics/\n")
        return self.site_dir

    def tracked(self):
        out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=self.site_dir,
                             capture_output=True, text=True).stdout
        return [l for l in out.splitlines() if "analytics" in l]

    def google_zip(self):
        p = self.downloads / GOOGLE_ZIP
        with zipfile.ZipFile(p, "w") as z:
            for n, text in google_files().items():
                z.writestr(n, text.encode("utf-8"))
        return p

    def cli(self, module, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = module.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def saved(self, source):
        p = self.cfg / "reports" / SITE / f"ai-{source}.json"
        return json.loads(p.read_text()) if p.exists() else None


class KeepIn(AnalyticsTest):
    def test_b2_each_download_lands_in_its_dated_folder_and_the_original_stays(self):
        self.repo()
        z, b = self.google_zip(), self.downloads / BING_CSV
        b.write_text(bing_csv(), encoding="utf-8")
        for f in (z, b):
            code, out, err = self.cli(ar, "import", SITE, str(f), "--keep-in", str(self.site_dir))
            self.assertEqual(code, 0, err)
        a = self.site_dir / "analytics"
        self.assertTrue((a / "2026-10-11_google-ai-report" / GOOGLE_ZIP).is_file(), "the date comes from Google's file name")
        self.assertTrue((a / "2026-10-13_bing-ai-report" / BING_CSV).is_file(), "Bing's, month first")
        self.assertTrue(z.exists() and b.exists(), "the originals in Downloads are left alone")
        self.assertIn("2026-10-13_bing-ai-report", out, "the reply names the folder")

    def test_b2_a_file_with_no_date_in_its_name_takes_today(self):
        b = self.downloads / "bing-ai.csv"
        b.write_text(bing_csv(), encoding="utf-8")
        code, _, err = self.cli(ar, "import", SITE, str(b), "--keep-in", str(self.site_dir))
        self.assertEqual(code, 0, err)
        self.assertTrue((self.site_dir / "analytics" / "2026-10-14_bing-ai-report" / "bing-ai.csv").is_file())

    def test_b3_nothing_in_the_folder_shows_to_git(self):
        self.repo()
        self.cli(ar, "import", SITE, str(self.google_zip()), "--keep-in", str(self.site_dir))
        self.assertTrue((self.site_dir / "analytics").exists())
        self.assertEqual(self.tracked(), [])

    def test_b4_a_folder_git_would_pick_up_is_refused_and_nothing_is_saved_or_kept(self):
        self.repo(ignore=False)
        code, _, err = self.cli(ar, "import", SITE, str(self.google_zip()), "--keep-in", str(self.site_dir))
        self.assertEqual(code, 1)
        self.assertIn("/analytics/", err, "the refusal names the line to add")
        self.assertFalse((self.site_dir / "analytics").exists())
        self.assertIsNone(self.saved("google"), "nothing is half done: no import without the copy asked for")

    def test_b5_the_owners_choice_to_commit_is_honoured(self):
        self.repo(ignore=False)
        code, _, err = self.cli(ar, "import", SITE, str(self.google_zip()), "--keep-in", str(self.site_dir),
                                "--commit-ok")
        self.assertEqual(code, 0, err)
        self.assertTrue((self.site_dir / "analytics" / "2026-10-11_google-ai-report" / GOOGLE_ZIP).is_file())

    def test_a_refused_download_is_never_kept(self):
        self.repo()
        bad = self.downloads / f"{SITE}_report.xlsx"
        bad.write_bytes(b"PK not a csv")
        code, _, _ = self.cli(ar, "import", SITE, str(bad), "--keep-in", str(self.site_dir))
        self.assertEqual(code, 1)
        self.assertFalse((self.site_dir / "analytics").exists())

    def test_the_site_folder_must_exist(self):
        code, _, err = self.cli(ar, "import", SITE, str(self.google_zip()), "--keep-in",
                                str(self.site_dir / "missing"))
        self.assertEqual(code, 1)
        self.assertIn("missing", err)
        self.assertIsNone(self.saved("google"))

    def test_a_second_copy_of_the_same_file_leaves_the_first(self):
        self.repo()
        z = self.google_zip()
        self.cli(ar, "import", SITE, str(z), "--keep-in", str(self.site_dir))
        kept = self.site_dir / "analytics" / "2026-10-11_google-ai-report" / GOOGLE_ZIP
        kept.write_bytes(b"marker")
        code, out, _ = self.cli(ar, "import", SITE, str(z), "--keep-in", str(self.site_dir))
        self.assertEqual(code, 0)
        self.assertEqual(kept.read_bytes(), b"marker", "an existing copy is never overwritten")
        self.assertIn("already", out)


class Snapshot(AnalyticsTest):
    def reports(self, geo=True, google=True, bing_rows=True):
        r = self.cfg / "reports" / SITE
        r.mkdir(parents=True)
        if google:
            (r / "google.html").write_text(
                f'<p>Also see: <a href="../../geo/reports/{SITE}/{RUN}.html">Does AI name you?</a></p>', encoding="utf-8")
            (r / "google-data.json").write_text(json.dumps({"fetched": "2026-10-13", "daily": []}))
        if geo:
            g = self.cfg / "geo" / "reports" / SITE
            g.mkdir(parents=True)
            (g / f"{RUN}.html").write_text(
                f'<p>Also see: <a href="../../../reports/{SITE}/google.html">How people find you</a></p>', encoding="utf-8")
            a = self.cfg / "geo" / "answers" / SITE / RUN
            a.mkdir(parents=True)
            (a / "openai-finds-broad-1.txt").write_text("an answer")
        if bing_rows:
            (self.cfg / "history.csv").write_text(
                "date,site,source,keyword,query,position,impressions,clicks,window,country\n"
                f"2026-10-05,{SITE},bing,bakery,bakery munich,7.2,40,1,,\n"
                f"2026-10-12,{SITE},bing,bakery,bakery munich,6.8,44,2,,\n"
                f"2026-10-12,{SITE},gsc,bakery,bakery munich,9.1,120,3,28,\n"
                "2026-10-12,other.de,bing,x,x,3,9,0,,\n")

    def test_b9_writes_the_top_level_and_each_dated_folder(self):
        self.repo()
        self.reports()
        code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        a = self.site_dir / "analytics"
        for f in ("README.md", "seo.html", "geo.html", "2026-10-13_gsc/google-data.json",
                  "2026-10-12_bing/bing-history.csv", f"2026-10-12_geo-run/{RUN}.html",
                  "2026-10-12_geo-run/answers/openai-finds-broad-1.txt"):
            self.assertTrue((a / f).is_file(), f)
        bing = (a / "2026-10-12_bing/bing-history.csv").read_text()
        self.assertIn("6.8", bing)
        self.assertNotIn("other.de", bing, "only this site's rows")
        self.assertNotIn(",gsc,", bing, "only Bing's rows")
        self.assertEqual(self.tracked(), [], "B3: nothing shows to git")

    def test_b9_the_copied_pages_link_to_each_other_not_into_hidden_settings(self):
        self.repo()
        self.reports()
        self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        a = self.site_dir / "analytics"
        seo, geo = (a / "seo.html").read_text(), (a / "geo.html").read_text()
        self.assertIn('href="geo.html"', seo)
        self.assertIn('href="seo.html"', geo)
        run_page = (a / f"2026-10-12_geo-run/{RUN}.html").read_text()
        self.assertIn('href="../seo.html"', run_page)
        for page in (seo, geo, run_page):
            self.assertNotIn("../../", page)

    def test_b9_a_dated_folder_that_exists_is_left_as_it_is(self):
        self.repo()
        self.reports()
        kept = {"2026-10-13_gsc": "google-data.json", "2026-10-12_bing": "bing-history.csv",
                "2026-10-12_geo-run": f"{RUN}.html"}
        for folder, name in kept.items():
            (self.site_dir / "analytics" / folder).mkdir(parents=True)
            (self.site_dir / "analytics" / folder / name).write_text("the earlier copy")
        code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        for folder, name in kept.items():
            with self.subTest(folder):
                self.assertEqual((self.site_dir / "analytics" / folder / name).read_text(), "the earlier copy")
                self.assertIn(f"{folder}: already there", out)

    def test_b9_parts_that_do_not_exist_are_named_not_faked(self):
        self.repo()
        self.reports(geo=False, bing_rows=False)
        code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        a = self.site_dir / "analytics"
        self.assertFalse((a / "geo.html").exists())
        self.assertIn("AI check: not set up for this site", out)
        self.assertIn("Bing: no rows for this site", out)
        self.assertNotIn('href="geo.html"', (a / "seo.html").read_text())

    def test_b4_the_snapshot_refuses_a_folder_git_would_pick_up(self):
        self.repo(ignore=False)
        self.reports()
        code, _, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 1)
        self.assertIn("/analytics/", err)
        self.assertFalse((self.site_dir / "analytics").exists())

    def test_a_site_with_no_reports_at_all_writes_nothing(self):
        self.repo()
        code, _, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 1)
        self.assertIn("no reports", err)
        self.assertFalse((self.site_dir / "analytics").exists())


class Starter(unittest.TestCase):
    def test_b1_new_sites_keep_the_folder_off_github(self):
        gi = Path(__file__).resolve().parents[4] / "skills/new-website/templates/.gitignore"
        lines = [l.strip() for l in gi.read_text().splitlines()]
        self.assertIn("/analytics/", lines)


if __name__ == "__main__":
    unittest.main()
