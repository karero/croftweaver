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
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # test_search_report's fake Google
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
                f'<head><meta name="geo-runs" content="{RUN}"></head>'
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
        code, out, _ = self.cli(ar, "import", SITE, str(z), "--keep-in", str(self.site_dir))
        self.assertEqual(code, 0)
        self.assertIn("already kept", out, "the same file twice is kept once")
        kept.write_bytes(b"an earlier, different download")
        code, out, _ = self.cli(ar, "import", SITE, str(z), "--keep-in", str(self.site_dir))
        self.assertEqual(code, 0)
        self.assertEqual(kept.read_bytes(), b"an earlier, different download", "an existing copy is never overwritten")
        beside = kept.with_name(kept.stem + "-2.zip")
        self.assertEqual(beside.read_bytes(), z.read_bytes(), "what was imported is what is kept")


class Snapshot(AnalyticsTest):
    def test_b9_writes_the_top_level_and_each_dated_folder(self):
        self.repo()
        self.reports()
        code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        a = self.site_dir / "analytics"
        for f in ("README.md", "seo.html", "geo.html", "2026-10-13_gsc/google-data.json",
                  "2026-10-12_bing/bing-history.csv", f"2026-10-12_geo-run/{RUN}.html",
                  f"2026-10-12_geo-run/answers/{RUN}/openai-finds-broad-1.txt"):
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

    def test_b9_a_kept_file_is_never_rewritten_and_newer_evidence_is_kept_beside_it(self):
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
                d = self.site_dir / "analytics" / folder
                self.assertEqual((d / name).read_text(), "the earlier copy")
                stem, dot, ext = name.rpartition(".")
                self.assertTrue((d / f"{stem}-2.{ext}").is_file(), "the evidence the page was built from is kept too")
        code, out, _ = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertIn("2026-10-13_gsc/google-data-2.json: already kept", out, "a second run adds nothing new")

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


class RoundOne(AnalyticsTest):
    """Review round 1 (docs/reviews/REVIEW-diff-2026-10-14-feat-analytics-folder-f3cea24.md). Invariant A:
    nothing a run writes under analytics/ may show to git unless the owner chose so — every path checked,
    none tracked, a git error refuses. B: what is kept is what was imported. C: the evidence is what the
    page was built from. D: a browser's second-download suffix keeps the file's own date."""

    def test_a_every_path_is_checked_not_a_sample(self):
        self.reports()
        for i, rules in enumerate(("analytics/*.md\n", "/analytics/*\n!/analytics/seo.html\n",
                                   "analytics/README.md\nanalytics/geo.html\n")):
            with self.subTest(rules):
                d = self.site_dir.parent / f"site{i}"
                d.mkdir()
                git("init", "-q", cwd=d)
                (d / ".gitignore").write_text(rules)
                code, _, err = self.cli(snap, SITE, "--site-dir", str(d))
                self.assertEqual(code, 1, f"{rules!r} let a file through")
                self.assertFalse((d / "analytics").exists(), "a refusal writes nothing")
        d = self.site_dir.parent / "site-download"
        d.mkdir()
        git("init", "-q", cwd=d)
        (d / ".gitignore").write_text("analytics/*.csv\n")
        code, _, _ = self.cli(ar, "import", SITE, str(self.google_zip()), "--keep-in", str(d))
        self.assertEqual(code, 1, "the download's own path is checked too")

    def test_a_a_whole_folder_rule_lets_every_part_through(self):
        for rules in ("analytics/*\n", "/analytics/\n", "analytics\n"):
            with self.subTest(rules):
                d = self.site_dir.parent / ("ok-" + str(abs(hash(rules))))
                d.mkdir()
                git("init", "-q", cwd=d)
                (d / ".gitignore").write_text(rules)
                if not (self.cfg / "reports" / SITE).exists():
                    self.reports()
                code, _, err = self.cli(snap, SITE, "--site-dir", str(d))
                self.assertEqual(code, 0, err)

    def test_a_a_tracked_destination_is_refused_but_a_tracked_neighbour_is_not(self):
        self.repo(ignore=False)
        (self.site_dir / "analytics").mkdir()
        (self.site_dir / "analytics" / "README.md").write_text("committed once")
        git("add", "analytics/README.md", cwd=self.site_dir)
        git("commit", "-qm", "x", cwd=self.site_dir)
        (self.site_dir / ".gitignore").write_text("/analytics/\n")
        self.reports()
        code, _, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 1)
        self.assertIn("already tracks analytics/README.md", err)
        git("rm", "-q", "--cached", "analytics/README.md", cwd=self.site_dir)
        old = self.site_dir / "analytics" / "2026-10-08_geo-run"
        old.mkdir()
        (old / "report.html").write_text("kept in the repo by the owner's choice")
        git("add", "-f", "analytics/2026-10-08_geo-run/report.html", cwd=self.site_dir)
        git("commit", "-qm", "y", cwd=self.site_dir)
        code, _, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        self.assertEqual([l for l in self.tracked() if not l.startswith("D ")], [], "only ignored files were added")

    def test_a_a_git_error_refuses_instead_of_guessing(self):
        self.repo()
        self.reports()
        with mock.patch.dict(os.environ, {"GIT_DIR": str(self.site_dir / "no-such-git-dir")}):
            code, _, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 1)
        self.assertIn("Git could not say", err)
        self.assertFalse((self.site_dir / "analytics").exists())

    def test_b_a_failed_save_leaves_no_kept_copy(self):
        self.repo()
        with mock.patch.object(ar, "save", side_effect=OSError("disk full")):
            code, _, err = self.cli(ar, "import", SITE, str(self.google_zip()), "--keep-in", str(self.site_dir))
        self.assertEqual(code, 1)
        self.assertEqual(list((self.site_dir / "analytics").rglob("*")) if (self.site_dir / "analytics").exists() else [], [],
                         "no copy of an import that was not saved")

    def test_c_every_run_the_ai_page_shows_is_kept(self):
        self.repo()
        self.reports()
        older = "20261005T070000Z-1-1-aaaa"
        a = self.cfg / "geo" / "answers" / SITE / older
        a.mkdir(parents=True)
        (a / "gemini-knows-broad-1.txt").write_text("an older run's answer")
        page = self.cfg / "geo" / "reports" / SITE / f"{RUN}.html"
        page.write_text(page.read_text(encoding="utf-8").replace(f'content="{RUN}"', f'content="{older} {RUN}"'), encoding="utf-8")
        code, _, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        run = self.site_dir / "analytics" / "2026-10-12_geo-run" / "answers"
        self.assertTrue((run / older / "gemini-knows-broad-1.txt").is_file(), "gemini's latest answer is from the older run")
        self.assertTrue((run / RUN / "openai-finds-broad-1.txt").is_file())

    def test_c_the_bing_rows_come_from_the_history_the_page_uses(self):
        self.repo()
        self.reports(bing_rows=False)
        (self.cfg / "history.csv").write_text("date,site,source,keyword,query,position,impressions,clicks,window,country\n"
                                             f"2026-10-12,{SITE},bing,bakery,bakery munich,6.8,44,2,,\n")
        other = self.cfg / "elsewhere.csv"
        other.write_text("date,site,source,keyword,query,position,impressions,clicks,window,country\n"
                         f"2026-09-01,{SITE},bing,bakery,from the wrong file,1,1,1,,\n")
        (self.cfg / "sites").mkdir()
        (self.cfg / "sites" / f"{SITE}.json").write_text(json.dumps({"keywords": ["bakery"], "csv": ""}))
        with mock.patch.dict(os.environ, {"GSC_HISTORY_CSV": str(other)}):
            code, _, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        self.assertTrue((self.site_dir / "analytics" / "2026-10-12_bing" / "bing-history.csv").is_file(),
                        "an empty csv in the weekly record means the shared file, as search_report.py reads it")

    def test_c_with_no_google_page_the_ai_page_links_nowhere_rather_than_to_a_missing_file(self):
        self.repo()
        self.reports(google=False)
        code, _, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        a = self.site_dir / "analytics"
        self.assertNotIn("seo.html", (a / "geo.html").read_text())
        self.assertFalse((a / "seo.html").exists())

    def test_c_a_link_the_rewrite_does_not_know_is_reported_not_hidden(self):
        self.repo()
        self.reports()
        g = self.cfg / "reports" / SITE / "google.html"
        g.write_text(g.read_text(encoding="utf-8") + '<a href="../../geo/answers/x.txt">a new kind of link</a>', encoding="utf-8")
        code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        self.assertIn("warning: seo.html still links into the hidden settings folder", out)

    def test_d_a_second_download_keeps_its_own_date(self):
        for i, (name, folder) in enumerate(((f"{SITE}-Performance-on-Search-Generative-AI-Features-2026-10-11 (1).zip",
                                             "2026-10-11_google-ai-report"),
                                            (f"{SITE}_AIPerformanceOverviewStats_10_13_2026 (2).csv", "2026-10-13_bing-ai-report"))):
            with self.subTest(name):
                src = self.google_zip() if name.endswith(".zip") else self.downloads / name
                if name.endswith(".zip"):
                    src = src.rename(self.downloads / name)
                else:
                    src.write_text(bing_csv(), encoding="utf-8")
                code, _, err = self.cli(ar, "import", SITE, str(src), "--keep-in", str(self.site_dir))
                self.assertEqual(code, 0, err)
                self.assertTrue((self.site_dir / "analytics" / folder / name).is_file())


class RoundTwo(AnalyticsTest):
    """Review round 2. Invariant A again: the staging name is a written path too, and every git answer
    is read for errors. Invariant C again: the kept AI evidence is what the kept page shows."""

    def fresh_repo(self, name, rules):
        d = self.site_dir.parent / name
        d.mkdir()
        git("init", "-q", cwd=d)
        (d / ".gitignore").write_text(rules)
        return d

    def test_a_the_staging_name_is_checked_like_the_final_name(self):
        self.reports()
        rules = "analytics/*.md\nanalytics/*.html\nanalytics/**/*.json\nanalytics/**/*.csv\nanalytics/**/*.html\nanalytics/**/*.txt\n"
        d = self.fresh_repo("partial-snap", rules)
        code, _, err = self.cli(snap, SITE, "--site-dir", str(d))
        self.assertEqual(code, 1, "the .partial names are not ignored by these rules")
        self.assertIn(".partial", err)
        self.assertFalse((d / "analytics").exists())
        d = self.fresh_repo("partial-import", "analytics/**/*.zip\n")
        code, _, err = self.cli(ar, "import", SITE, str(self.google_zip()), "--keep-in", str(d))
        self.assertEqual(code, 1)
        self.assertIsNone(self.saved("google"))

    def test_a_a_failed_copy_leaves_no_partial_file(self):
        self.repo()
        def half_copy(src, dst, *a, **k):
            Path(dst).write_bytes(b"half")
            raise OSError("disk full")
        with mock.patch("shutil.copy2", side_effect=half_copy):
            code, _, _ = self.cli(ar, "import", SITE, str(self.google_zip()), "--keep-in", str(self.site_dir))
        self.assertEqual(code, 1)
        self.assertEqual([p for p in (self.site_dir / "analytics").rglob("*") if p.is_file()]
                         if (self.site_dir / "analytics").exists() else [], [])
        self.assertIsNone(self.saved("google"), "the copy failed before the import was saved")

    def test_a_git_errors_after_the_first_question_refuse_too(self):
        self.repo()
        self.reports()
        bad_index = self.site_dir.parent / "bad-index"
        bad_index.write_bytes(b"this is not a git index")
        with mock.patch.dict(os.environ, {"GIT_INDEX_FILE": str(bad_index)}):
            code, _, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 1)
        self.assertIn("Git could not", err)
        self.assertFalse((self.site_dir / "analytics").exists())

    def test_a_a_folder_git_calls_no_work_tree_is_refused(self):
        self.repo()
        self.reports()
        code, _, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir / ".git"))
        self.assertEqual(code, 1)
        self.assertIn("not inside a git work tree", err)

    def test_c_the_kept_answers_are_those_the_kept_page_shows(self):
        self.repo()
        self.reports()
        older, later = "20261005T070000Z-1-1-aaaa", "20261013T070000Z-2-2-bbbb"
        for run in (older, later):
            d = self.cfg / "geo" / "answers" / SITE / run
            d.mkdir(parents=True)
            (d / "gemini-knows-broad-1.txt").write_text(run)
        page = self.cfg / "geo" / "reports" / SITE / f"{RUN}.html"
        page.write_text(page.read_text(encoding="utf-8").replace(f'content="{RUN}"', f'content="{older} {RUN}"'), encoding="utf-8")      # a later run exists, but the page does not list it
        code, _, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        answers = self.site_dir / "analytics" / "2026-10-12_geo-run" / "answers"
        self.assertTrue((answers / older).is_dir(), "the page (built at RUN) shows gemini's answer from the older run")
        self.assertFalse((answers / later).exists(), "a run after the page is not on it")

    def test_c_a_missing_answers_folder_is_named(self):
        self.repo()
        self.reports()
        gone = "20261001T070000Z-3-3-cccc"
        page = self.cfg / "geo" / "reports" / SITE / f"{RUN}.html"
        page.write_text(page.read_text(encoding="utf-8").replace(f'content="{RUN}"', f'content="{gone} {RUN}"'), encoding="utf-8")
        code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        self.assertIn(f"AI-check answers of run {gone}: not on this computer", out)

    def test_c_leftover_links_are_found_in_any_quoting_and_in_the_run_page(self):
        self.repo()
        self.reports()
        g = self.cfg / "reports" / SITE / "google.html"
        g.write_text(g.read_text(encoding="utf-8") + "<a HREF='../../geo/answers/x.txt'>x</a>", encoding="utf-8")
        page = self.cfg / "geo" / "reports" / SITE / f"{RUN}.html"
        page.write_text(page.read_text(encoding="utf-8") + '<a href="../../geo/answers/y.txt">y</a>', encoding="utf-8")
        code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        self.assertIn("warning: seo.html still links", out)
        self.assertIn(f"warning: 2026-10-12_geo-run/{RUN}.html still links", out)
        self.assertIn("warning: geo.html still links", out)


class RoundThree(AnalyticsTest):
    """Review round 3. Invariant C, third time (F10 → F23 → F32): the pages record what they were built
    from — the Google page the fingerprint of its data, the AI page its runs — and the snapshot keeps
    what they record, not a guess. Links are read as a browser reads them."""

    def google_page_through_search_report(self):
        import search_report as sr
        import test_search_report as tsr
        with mock.patch.object(sr, "base_dir", lambda: self.cfg):
            out = sr.build(SITE, SimpleNamespace(keywords=None, country=None, csv=None),
                           service_factory=lambda: tsr.FakeGoogle(daily=tsr.daily_series(40)), today=tsr.TODAY)
        return out

    def test_c_the_kept_google_data_is_the_data_the_page_shows(self):
        self.repo()
        self.google_page_through_search_report()
        code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        self.assertEqual(len(list((self.site_dir / "analytics").glob("*_gsc/google-data.json"))), 1)
        self.assertNotIn("not what seo.html shows", out)

    def test_c_a_copy_the_page_did_not_show_is_not_kept(self):
        self.repo()
        self.google_page_through_search_report()
        data = self.cfg / "reports" / SITE / "google-data.json"
        old = json.loads(data.read_text())
        old["daily"] = old["daily"][:3]                 # what an earlier fetch left when this one's save failed
        data.write_text(json.dumps(old, indent=1))
        code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        self.assertIn("the saved copy is not what seo.html shows", out)
        self.assertEqual(list((self.site_dir / "analytics").glob("*_gsc")), [])

    def test_c_a_page_that_names_its_runs_is_taken_at_its_word(self):
        self.repo()
        self.reports()
        named = "20261001T070000Z-5-5-eeee"
        d = self.cfg / "geo" / "answers" / SITE / named
        d.mkdir(parents=True)
        (d / "gemini-knows-broad-1.txt").write_text("named by the page")
        page = self.cfg / "geo" / "reports" / SITE / f"{RUN}.html"
        page.write_text(page.read_text(encoding="utf-8").replace(f'content="{RUN}"', f'content="{named} {RUN}"'), encoding="utf-8")
        code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        self.assertTrue((self.site_dir / "analytics" / "2026-10-12_geo-run" / "answers" / named).is_dir())
        self.assertNotIn("built before pages listed their runs", out)

    def test_c_links_are_read_as_a_browser_reads_them(self):
        self.repo()
        self.reports()
        g = self.cfg / "reports" / SITE / "google.html"
        g.write_text(g.read_text(encoding="utf-8") + "<a HREF=../../geo/answers/x.txt>x</a>", encoding="utf-8")
        page = self.cfg / "geo" / "reports" / SITE / f"{RUN}.html"
        page.write_text(page.read_text(encoding="utf-8") + '<a href="../seo.html#top">top</a>', encoding="utf-8")
        code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        self.assertIn("warning: seo.html still links", out, "an unquoted link is a link")
        self.assertNotIn(f"{RUN}.html still links", out, "../seo.html#top is the allowed link, with a fragment")

    def test_c_a_page_from_before_run_lists_keeps_no_guessed_answers(self):
        self.repo()
        self.reports()
        page = self.cfg / "geo" / "reports" / SITE / f"{RUN}.html"
        page.write_text(re.sub(r'<head>.*?</head>', "", page.read_text(encoding="utf-8")), encoding="utf-8")
        code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        self.assertIn("was built before pages listed their runs", out)
        self.assertIn("geo_check.py --report", out, "the fix is named")
        self.assertFalse((self.site_dir / "analytics" / "2026-10-12_geo-run" / "answers").exists(), "nothing guessed")
        self.assertTrue((self.site_dir / "analytics" / "2026-10-12_geo-run" / f"{RUN}.html").is_file(), "the page is kept")

    def test_c_the_kept_google_data_is_the_bytes_that_were_checked(self):
        self.repo()
        self.google_page_through_search_report()
        data = self.cfg / "reports" / SITE / "google-data.json"
        checked = data.read_bytes()
        real_keep = __import__("_analytics").keep
        def refresh_then_keep(site_dir, folder, src):
            data.write_text("{}")            # a refresh rewrites the live file mid-snapshot
            return real_keep(site_dir, folder, src)
        with mock.patch.object(snap._analytics, "keep", side_effect=refresh_then_keep):
            code, _, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        kept = list((self.site_dir / "analytics").glob("*_gsc/google-data.json"))
        self.assertEqual([k.read_bytes() for k in kept], [checked])

    def test_c_the_saved_data_file_is_exactly_the_fingerprinted_bytes(self):
        self.google_page_through_search_report()
        data = self.cfg / "reports" / SITE / "google-data.json"
        page = (self.cfg / "reports" / SITE / "google.html").read_text(encoding="utf-8")
        fp = re.search(r'name="gsc-data-sha256" content="([0-9a-f]{64})"', page).group(1)
        self.assertEqual(hashlib.sha256(data.read_bytes()).hexdigest(), fp)
        self.assertNotIn(b"\r\n", data.read_bytes(), "written as bytes: no newline translation on any platform")

    def test_c_an_unreadable_file_is_named_and_the_rest_written(self):
        self.repo()
        self.reports()
        data = self.cfg / "reports" / SITE / "google-data.json"
        data.chmod(0)                              # a file the snapshot cannot read at all
        try:
            if os.access(data, os.R_OK):
                self.skipTest("running as a user who can read any file")
            code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        finally:
            data.chmod(0o644)
        self.assertEqual(code, 0, err)
        self.assertIn("Search Console data: its fetch date cannot be read", out)
        self.assertTrue((self.site_dir / "analytics" / "seo.html").is_file())

    def test_c_an_unreadable_google_page_is_named_as_the_page_and_the_rest_written(self):
        self.repo()
        self.reports()
        page = self.cfg / "reports" / SITE / "google.html"
        page.chmod(0)
        try:
            if os.access(page, os.R_OK):
                self.skipTest("running as a user who can read any file")
            code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        finally:
            page.chmod(0o644)
        self.assertEqual(code, 0, err)
        self.assertIn("seo.html: the Google & Bing page cannot be read", out)
        self.assertIn("the page it belongs to cannot be read", out, "its data is not kept unchecked")
        self.assertTrue((self.site_dir / "analytics" / "geo.html").is_file(), "the rest is written")

    def test_c_the_page_is_read_once_so_copy_and_check_agree(self):
        self.repo()
        self.google_page_through_search_report()
        page = self.cfg / "reports" / SITE / "google.html"
        reads = []
        real = Path.read_text
        def counting(self_path, *a, **k):
            if self_path == page:
                reads.append(1)
            return real(self_path, *a, **k)
        with mock.patch.object(Path, "read_text", counting):
            code, _, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        self.assertEqual(len(reads), 1)

class MergeLink(AnalyticsTest):
    """After merging main's fix proposal (merge link, docs/reviews/REVIEW-diff-2026-10-14-feat-analytics-folder-f3cea24.md):
    the page shows the proposal's figures too, so its record is kept; and its log line is best-effort."""

    def google_page(self, **patches):
        import search_report as sr
        import test_search_report as tsr
        with mock.patch.object(sr, "base_dir", lambda: self.cfg), mock.patch.object(sr.fp, "base_dir", lambda: self.cfg):
            return sr.build(SITE, SimpleNamespace(keywords=None, country=None, csv=None),
                            service_factory=lambda: tsr.FakeGoogle(daily=tsr.daily_series(40)), today=tsr.TODAY)

    def test_the_fix_proposals_record_is_kept_beside_the_data_and_said_to_be_unmatched(self):
        self.repo()
        self.google_page()
        (self.cfg / "sites").mkdir(exist_ok=True)
        (self.cfg / "sites" / f"{SITE}-proposals.json").write_text('{"proposals": []}')
        code, out, err = self.cli(snap, SITE, "--site-dir", str(self.site_dir))
        self.assertEqual(code, 0, err)
        kept = list((self.site_dir / "analytics").glob(f"*_gsc/{SITE}-proposals.json"))
        self.assertEqual(len(kept), 1)
        self.assertIn("it is not matched to seo.html", out)

    def test_a_broken_log_stream_does_not_cost_the_google_page(self):
        class BrokenStream(io.StringIO):
            def write(self, s):
                raise OSError("stderr is gone")
        import search_report as sr
        with mock.patch.object(sr.sys, "stderr", BrokenStream()):
            out = self.google_page()
        self.assertTrue(out.is_file(), "google.html is written even when the log cannot be")


class Starter(unittest.TestCase):
    def test_b1_new_sites_keep_the_folder_off_github(self):
        gi = Path(__file__).resolve().parents[4] / "skills/new-website/templates/.gitignore"
        lines = [l.strip() for l in gi.read_text().splitlines()]
        self.assertIn("/analytics/", lines)


if __name__ == "__main__":
    unittest.main()
