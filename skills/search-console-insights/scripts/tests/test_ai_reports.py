"""ai_reports.py + the AI section of search_report.py — Google's and Bing's own AI reports.

Why: for most small sites these reports are close to empty, and an owner reads a printed 0 as a
finding ("Google stopped showing me"). Google's export even writes "not available" as 0. So an
empty report must say "no data yet" in words, a missing report must never read as a fault, and a
real number must come from the right file (the chart, never the sum of pages, which double-counts
an answer that shows two pages). Every test pins one scenario of
docs/reviews/SKILL-PLAN-ai-reports.md (A1–A10) and enters through the calls production makes:
`ai_reports.main([...])` for the import, `search_report.build()` for the page.

The test files copy the shape of real exports downloaded on 2026-10-14 (a German Search Console
screen, so German file names and headers; Bing's US dates, BOM and CRLF), with example.com in
place of the real domains and fewer rows.

Run:  python3 -m unittest discover -s skills/search-console-insights/scripts/tests
"""
import contextlib
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import ai_reports as ar  # noqa: E402
import search_report as sr  # noqa: E402

TODAY = dt.date(2026, 10, 14)
SITE = "example.com"
GOOGLE_ZIP = f"{SITE}-Performance-on-Search-Generative-AI-Features-2026-10-14.zip"
BING_CSV = f"{SITE}_AIPerformanceOverviewStats_10_14_2026.csv"


def daily_chart(values, start=dt.date(2026, 7, 12)):
    """Google's chart file as a German screen writes it, one row per day."""
    rows = [f"{start + dt.timedelta(days=i)},{v}" for i, v in enumerate(values)]
    return "Datum,Impressionen\n" + "\n".join(rows)


def pages(rows):
    return "Die häufigsten Seiten,Impressionen\n" + "\n".join(f"{u},{n}" for u, n in rows)


def google_files(chart, page_rows, countries=None):
    total = sum(int(line.rsplit(",", 1)[1]) for line in chart.splitlines()[1:]) if chart else 0
    return {
        "Diagramm.csv": chart,
        "Seiten.csv": pages(page_rows),
        "Länder.csv": "Land,Impressionen\n" + (countries or f"Deutschland,{total}"),
        "Geräte.csv": f"Gerät,Impressionen\nComputer,{total}",
        "Filter.csv": "Filtern,Wert\nSuchtyp,Web (text-based)\nDatum,Letzte 3 Monate",
    }


def bing_csv(citations, cited=None, start=dt.date(2026, 7, 14)):
    """Bing's overview export: BOM, CRLF, quoted, US dates with a time."""
    cited = cited or [min(c, 1) for c in citations]
    lines = ['"Date","Citations","Cited Pages"']
    for i, (c, p) in enumerate(zip(citations, cited)):
        d = start + dt.timedelta(days=i)
        lines.append(f'"{d.month}/{d.day}/{d.year} 12:00:00 AM","{c}","{p}"')
    return "﻿" + "\r\n".join(lines) + "\r\n"


class AiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        (self.home / ".config/gsc-insights").mkdir(parents=True)
        self.downloads = Path(self.tmp.name) / "Downloads"
        self.downloads.mkdir()
        self.env = mock.patch.dict(os.environ, {"HOME": str(self.home)}, clear=False)
        self.env.start()
        for k in ("GSC_HISTORY_CSV", "GSC_COUNTRY", "BING_API_KEY"):
            os.environ.pop(k, None)
        self.today = mock.patch.object(ar, "today", lambda: TODAY)
        self.today.start()

    def tearDown(self):
        self.today.stop()
        self.env.stop()
        self.tmp.cleanup()

    # ── files the owner hands over ──
    def google_zip(self, files, name=GOOGLE_ZIP):
        p = self.downloads / name
        with zipfile.ZipFile(p, "w") as z:
            for n, text in files.items():
                z.writestr(n, text.encode("utf-8"))
        return p

    def google_folder(self, files, name=GOOGLE_ZIP[:-4]):
        d = self.downloads / name
        d.mkdir()
        for n, text in files.items():
            (d / n).write_text(text, encoding="utf-8")
        return d

    def bing_file(self, text, name=BING_CSV):
        p = self.downloads / name
        p.write_bytes(text.encode("utf-8"))
        return p

    def other_site(self, name):
        (self.home / ".config/gsc-insights/sites").mkdir(exist_ok=True)
        (self.home / ".config/gsc-insights/sites" / f"{name}.json").write_text("{}")

    # ── the production entry points ──
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ar.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def saved(self, source):
        p = self.home / ".config/gsc-insights/reports" / SITE / f"ai-{source}.json"
        return json.loads(p.read_text()) if p.exists() else None

    def page(self):
        """The owner's page, with Google's live part unreachable: the AI section must not depend on it."""
        def no_google():
            raise RuntimeError("offline in this test")
        out = sr.build(SITE, SimpleNamespace(keywords=None, country=None, csv=None),
                       service_factory=no_google, today=TODAY)
        html = out.read_text(encoding="utf-8")
        start = html.index("<h2>Google's and Bing's AI answers</h2>")
        return html[start:html.index("</main>")], html

    def no_zero_figures(self, section):
        """A 0 printed as a number reads like a finding (owner's caveat)."""
        for bad in (">0<", " 0 times", " 0 impressions", " 0 citations", "shown 0", "cited 0"):
            self.assertNotIn(bad, section)


class Scenarios(AiTest):
    def test_a1_nothing_added_explains_in_two_sentences_with_no_warning(self):
        section, _ = self.page()
        self.assertIn("don't let programs read", section)
        self.assertIn("here's my AI report from Google", section)
        self.assertNotIn('class="alert"', section)
        self.assertNotIn("<table", section)
        self.no_zero_figures(section)

    def test_a2_a_google_report_of_zeros_says_no_data_yet_in_words(self):
        code, out, _ = self.run_cli("import", SITE, str(self.google_zip(google_files(daily_chart([0] * 94), []))))
        self.assertEqual(code, 0, "an empty report is a result, not a failure")
        self.assertEqual(self.saved("google")["state"], "empty")
        section, _ = self.page()
        self.assertIn("Your download shows no impressions in Google's AI answers (it covers 12 July – 13 October "
                      "2026). That is normal for a small site.", section)
        self.assertNotIn("<table", section)
        self.assertNotIn('class="alert"', section)
        self.no_zero_figures(section)

    def test_a3_google_shows_no_report_is_recorded_as_a_result(self):
        code, out, _ = self.run_cli("not-shown", SITE)
        self.assertEqual(code, 0)
        section, _ = self.page()
        self.assertIn("Google doesn't show an AI report for this site yet (you checked on 14 October 2026). "
                      "Google shows it once a site has appeared in its AI answers often enough.", section)
        self.assertNotIn('class="alert"', section)
        self.no_zero_figures(section)

    def test_a4_bing_citations_are_totalled_and_cited_pages_never_added_up(self):
        cites = [0] * 90
        for day, n in {10: 1, 14: 8, 35: 8, 59: 5, 62: 1, 63: 3, 70: 1, 78: 2, 79: 2, 84: 6, 87: 2}.items():
            cites[day] = n                                       # 39 citations on 11 of 90 days
        code, out, _ = self.run_cli("import", SITE, str(self.bing_file(bing_csv(cites))))
        self.assertEqual(code, 0)
        b = self.saved("bing")
        self.assertEqual((b["citations"], b["days_cited"], b["days"]), (39, 11, 90))
        self.assertEqual((b["first"], b["last"]), ("2026-07-14", "2026-10-11"))
        section, _ = self.page()
        self.assertIn("Bing's AI answers (Copilot and Bing's AI summaries) cited your pages 39 times between "
                      "14 July and 11 October 2026, on 11 of those 90 days.", section)
        self.assertIn("says nothing about visits", section)
        self.assertNotIn("cited pages", section.lower(), "cited pages per day are never added up")

    def test_a5_both_reports_get_separate_cards_never_one_number(self):
        self.run_cli("import", SITE, str(self.google_zip(google_files(daily_chart([4] * 93 + [40]), [(f"https://{SITE}/", 412)]))))
        self.run_cli("import", SITE, str(self.bing_file(bing_csv([0] * 50 + [37] + [0] * 39))))
        section, _ = self.page()
        self.assertEqual(section.count('<section class="card">'), 2)
        self.assertIn("shown 412 times in Google", section)
        self.assertIn("cited your pages 37 times", section)
        self.assertNotIn("449", section, "Google impressions and Bing citations are never added together")

    def test_a6_the_total_comes_from_the_chart_never_from_the_pages(self):
        files = google_files(daily_chart([5, 0, 7] + [4] * 91),
                             [(f"https://{SITE}/a", 300), (f"https://www.{SITE}/", 90), (f"https://{SITE}/b", 0)])
        code, out, _ = self.run_cli("import", SITE, str(self.google_zip(files)))
        self.assertEqual(code, 0, out)
        g = self.saved("google")
        self.assertEqual(g["total"], 376)
        self.assertEqual((g["first"], g["last"]), ("2026-07-12", "2026-10-13"))
        section, _ = self.page()
        self.assertIn("Your site was shown 376 times in Google's AI answers (AI Overviews and AI Mode) between "
                      "12 July and 13 October 2026.", section)
        self.assertNotIn("390", section, "the pages' sum is never shown as a total")
        self.assertIn("<td>/a</td><td>300</td>", section)
        self.assertIn("<td>/</td><td>90</td>", section, "the www. address is the same site")
        self.assertNotIn("<td>/b</td>", section, "Google writes 'not available' as 0: such a page is left out")
        self.assertIn("“Web (text-based)”", section, "the search type the download counts is quoted")

    def test_a6_one_path_under_two_addresses_is_shown_in_full_both_times(self):
        files = google_files(daily_chart([3] * 30), [(f"https://{SITE}/", 79), (f"https://{SITE}/team", 11),
                                                      (f"https://www.{SITE}/", 2)])
        self.run_cli("import", SITE, str(self.google_zip(files)))
        section, _ = self.page()
        self.assertIn(f"<td>https://{SITE}/</td><td>79</td>", section)
        self.assertIn(f"<td>https://www.{SITE}/</td><td>2</td>", section)
        self.assertIn("<td>/team</td><td>11</td>", section)

    def test_a6_a_weekly_chart_and_a_folder_read_the_same(self):
        chart = ("Zeitraum,Impressionen\n2026-07-12 - 2026-07-18,33\n2026-07-19 - 2026-07-25,42\n"
                 "2026-10-11 - 2026-10-11,10")
        code, out, _ = self.run_cli("import", SITE, str(self.google_folder(google_files(chart, [(f"https://{SITE}/", 85)]))))
        self.assertEqual(code, 0, out)
        g = self.saved("google")
        self.assertEqual((g["total"], g["first"], g["last"]), (85, "2026-07-12", "2026-10-11"))

    def test_a7_numbers_that_end_more_than_35_days_ago_say_so_without_a_warning(self):
        self.run_cli("import", SITE, str(self.bing_file(bing_csv([1] * 50, start=dt.date(2026, 7, 1)))))
        section, _ = self.page()                              # last day 19 Aug, 56 days before 14 Oct
        self.assertIn("These numbers end on 19 August 2026; download a new report for newer ones.", section)
        self.assertNotIn('class="alert"', section)

    def test_a7_numbers_35_days_old_are_not_old(self):
        self.run_cli("import", SITE, str(self.bing_file(bing_csv([1] * 10, start=dt.date(2026, 8, 31)))))
        section, _ = self.page()                              # last day 9 Sept, exactly 35 days
        self.assertNotIn("These numbers end on", section)

    def test_a8_the_ordinary_performance_export_is_refused_and_nothing_saved(self):
        self.run_cli("import", SITE, str(self.google_zip(google_files(daily_chart([3] * 94), [(f"https://{SITE}/", 9)]))))
        before = self.saved("google")
        ordinary = {"Dates.csv": "Date,Clicks,Impressions,CTR,Position\n2026-10-01,1,20,5%,8.1",
                    "Pages.csv": f"Top pages,Clicks,Impressions,CTR,Position\nhttps://{SITE}/,1,20,5%,8.1"}
        code, out, err = self.run_cli("import", SITE, str(self.google_zip(ordinary)))
        self.assertEqual(code, 1)
        self.assertIn("Date, Clicks, Impressions, CTR, Position", err, "the refusal names what it found")
        self.assertIn("ordinary Performance report", err)
        self.assertEqual(self.saved("google"), before, "the page keeps what it had")

    def test_a8_other_unreadable_files_are_refused(self):
        cases = {
            "an Excel file": self.downloads / f"{SITE}_AIPerformanceOverviewStats_10_14_2026.xlsx",
            "one loose file from Google's zip": self.downloads / "Seiten.csv",
            "Bing's file with a damaged date": self.downloads / BING_CSV,
        }
        cases["an Excel file"].write_bytes(b"PK\x03\x04 not a csv")
        cases["one loose file from Google's zip"].write_text(pages([(f"https://{SITE}/", 3)]), encoding="utf-8")
        cases["Bing's file with a damaged date"].write_text(bing_csv([1, 2]).replace("7/15/2026", "7/15"), encoding="utf-8")
        for why, path in cases.items():
            with self.subTest(why):
                code, out, err = self.run_cli("import", SITE, str(path))
                self.assertEqual(code, 1)
                self.assertTrue(err.strip())
                self.assertIsNone(self.saved("google"))
                self.assertIsNone(self.saved("bing"))

    def test_a8_any_other_zip_is_never_taken_for_an_empty_google_report(self):
        code, _, err = self.run_cli("import", SITE, str(self.google_zip({"notes.csv": "Name,Value\nfoo,bar"})))
        self.assertEqual(code, 1, "'no data yet' must never come from a file that isn't Google's")
        self.assertIsNone(self.saved("google"))

    def test_a2_a_download_with_headers_and_no_rows_is_empty_not_refused(self):
        files = {"Diagramm.csv": "Datum,Impressionen", "Seiten.csv": "Die häufigsten Seiten,Impressionen",
                 "Filter.csv": "Filtern,Wert\nSuchtyp,Web (text-based)"}
        code, _, err = self.run_cli("import", SITE, str(self.google_zip(files)))
        self.assertEqual(code, 0, err)
        section, _ = self.page()
        self.assertIn("Your download shows no impressions in Google's AI answers (it has no rows).", section)
        self.no_zero_figures(section)

    def test_a9_another_sites_file_is_refused_by_its_name(self):
        for path in (self.bing_file(bing_csv([1]), name="other-site.de_AIPerformanceOverviewStats_10_14_2026.csv"),
                     self.google_zip(google_files(daily_chart([1]), []),
                                     name="other-site.de-Performance-on-Search-Generative-AI-Features-2026-10-14.zip")):
            with self.subTest(path.name):
                code, out, err = self.run_cli("import", SITE, str(path))
                self.assertEqual(code, 1)
                self.assertIn("other-site.de", err)
        self.assertIsNone(self.saved("google"))
        self.assertIsNone(self.saved("bing"))

    def test_a9_another_sites_pages_are_refused_even_under_a_matching_name(self):
        files = google_files(daily_chart([2] * 10), [("https://other-site.de/", 20)])
        code, out, err = self.run_cli("import", SITE, str(self.google_zip(files)))
        self.assertEqual(code, 1)
        self.assertIn("other-site.de", err)
        self.assertIsNone(self.saved("google"))

    def test_a9_a_renamed_file_is_fine_for_one_site_and_refused_with_several(self):
        path = self.bing_file(bing_csv([2, 0, 1]), name="bing-ai.csv")
        code, _, err = self.run_cli("import", SITE, str(path))
        self.assertEqual(code, 0, err)
        self.other_site("other-site.de")
        code, _, err = self.run_cli("import", SITE, str(path))
        self.assertEqual(code, 1)
        self.assertIn(f"start with {SITE}", err)

    def test_a10_the_weekly_rebuild_shows_the_last_file_and_flags_nothing(self):
        self.run_cli("import", SITE, str(self.bing_file(bing_csv([3] * 90))))
        first, _ = self.page()
        again, html = self.page()                              # what the weekly job's rebuild does
        self.assertEqual(first, again)
        alerts = [p for p in html.split('<p class="alert">')[1:]]
        self.assertFalse(any("AI" in a.split("</p>")[0] for a in alerts), "no AI line among the page's alerts")


class Reading(AiTest):
    def test_bing_day_first_dates_are_read_when_month_first_cannot_be(self):
        text = bing_csv([0, 4, 0])
        for m_d, d_m in (("7/14/2026", "14/7/2026"), ("7/15/2026", "15/7/2026"), ("7/16/2026", "16/7/2026")):
            text = text.replace(m_d, d_m)
        code, _, err = self.run_cli("import", SITE, str(self.bing_file(text)))
        self.assertEqual(code, 0, err)
        self.assertEqual((self.saved("bing")["first"], self.saved("bing")["last"]), ("2026-07-14", "2026-07-16"))

    def test_bing_dates_out_of_order_are_refused_rather_than_guessed(self):
        text = bing_csv([1, 1, 1]).replace("7/15/2026", "7/20/2026")
        code, _, err = self.run_cli("import", SITE, str(self.bing_file(text)))
        self.assertEqual(code, 1)
        self.assertIsNone(self.saved("bing"))

    def test_a_single_bing_citation_reads_in_the_singular(self):
        self.run_cli("import", SITE, str(self.bing_file(bing_csv([0, 1, 0]))))
        section, _ = self.page()
        self.assertIn("cited your pages 1 time between", section)

    def test_a_newer_file_replaces_the_older_one(self):
        self.run_cli("import", SITE, str(self.bing_file(bing_csv([5] * 3))))
        self.run_cli("import", SITE, str(self.bing_file(bing_csv([0] * 3))))
        self.assertEqual(self.saved("bing")["state"], "empty")

    def test_a_damaged_saved_file_never_breaks_the_page(self):
        d = self.home / ".config/gsc-insights/reports" / SITE
        d.mkdir(parents=True)
        (d / "ai-google.json").write_text("{not json")
        (d / "ai-bing.json").write_text('["a list"]')
        section, _ = self.page()
        self.assertIn("don't let programs read", section, "damaged files read as nothing added")
        (d / "ai-google.json").write_text('{"state": "data"}')
        (d / "ai-bing.json").write_text('{"state": "data", "citations": 3}')
        section, _ = self.page()
        self.assertIn("don't let programs read", section, "a record missing its numbers reads as nothing added")
        (d / "ai-google.json").write_text('{"state": "data", "total": "412", "first": "2026-07-12", "last": "2026-10-11"}')
        (d / "ai-bing.json").write_text('{"state": "empty", "first": "14/7/2026", "last": "2026-10-11"}')
        section, _ = self.page()
        self.assertIn("don't let programs read", section, "a count as text or a bad date reads as nothing added")



class RoundOneFindings(AiTest):
    """Review round 1 (docs/reviews/REVIEW-diff-2026-10-14-ai-reports.md). Invariant: a file is accepted
    only once it is known to be the right report, and every number and date in it reads as one."""

    def refused(self, path):
        code, _, err = self.run_cli("import", SITE, str(path))
        self.assertEqual(code, 1, f"{path.name} was accepted")
        self.assertTrue(err.strip())
        self.assertIsNone(self.saved("google"))
        self.assertIsNone(self.saved("bing"))

    def test_files_that_are_not_googles_search_report_are_refused(self):
        filt = "Filtern,Wert\nSuchtyp,Web (text-based)"
        cases = {
            "a dated metric with no search type": {"Diagramm.csv": "Date,Revenue\n2026-10-01,5\n2026-10-02,7"},
            "headers only, nothing Google's": {"x.csv": "Name,Value", "y.csv": "Name,Value"},
            "the Discover report": dict(google_files(daily_chart([3] * 5), []),
                                        **{"Filter.csv": "Filtern,Wert\nFeed,Discover"}),
            "chart and pages count different things": {"Diagramm.csv": "Datum,Klicks\n2026-10-01,5",
                                                       "Seiten.csv": f"Seiten,Impressionen\nhttps://{SITE}/,5",
                                                       "Filter.csv": filt},
        }
        for i, (why, files) in enumerate(cases.items()):
            with self.subTest(why):
                self.refused(self.google_zip(files, name=f"{SITE}-case{i}.zip"))

    def test_bing_files_with_other_columns_are_refused_and_padding_is_not(self):
        for i, head in enumerate(('"Date","Clicks","Impressions"', '"Date","Visits","Pages"',
                                  '"Date","Cited Pages","Citations"')):
            with self.subTest(head):
                self.refused(self.bing_file(bing_csv([1, 2]).replace('"Date","Citations","Cited Pages"', head),
                                            name=f"{SITE}_AIPerformanceOverviewStats_{i}.csv"))
        padded = bing_csv([1, 2]).replace('"Date","Citations","Cited Pages"', ' DATE , citations ,"Cited pages "')
        code, _, err = self.run_cli("import", SITE, str(self.bing_file(padded)))
        self.assertEqual(code, 0, err)

    def test_a_pages_file_with_an_unreadable_count_is_refused_whoever_it_is_for(self):
        for i, rows in enumerate((("https://other-site.de/", "broken"), (f"https://{SITE}/", "3.5"),
                                  (f"https://{SITE}/", ""))):
            with self.subTest(rows):
                files = google_files(daily_chart([2] * 5), [])
                files["Seiten.csv"] = f"Die häufigsten Seiten,Impressionen\n{rows[0]},{rows[1]}"
                self.refused(self.google_zip(files, name=f"{SITE}-p{i}.zip"))

    def test_impossible_dates_are_refused_before_anything_is_saved(self):
        for i, row in enumerate(("2026-99-99,0", "2026-02-30,4", "2026-07-18 - 2026-07-12,4")):
            with self.subTest(row):
                files = google_files("Datum,Impressionen\n" + row, [])
                self.refused(self.google_zip(files, name=f"{SITE}-d{i}.zip"))

    def test_subdomains_are_the_same_site_and_look_alikes_are_not(self):
        files = google_files(daily_chart([2] * 5), [(f"https://blog.{SITE}/a", 6), (f"https://WWW.{SITE.upper()}:443/", 4)])
        code, _, err = self.run_cli("import", SITE, str(self.google_zip(files)))
        self.assertEqual(code, 0, err)
        for i, host in enumerate((f"evil-{SITE}", f"{SITE}.evil.de", f"not{SITE}")):
            with self.subTest(host):
                files = google_files(daily_chart([2] * 5), [(f"https://{host}/", 6)])
                code, _, err = self.run_cli("import", SITE, str(self.google_zip(files, name=f"{SITE}-h{i}.zip")))
                self.assertEqual(code, 1)
                self.assertIn(host, err)

    def test_a_finder_file_in_the_reports_folder_is_not_a_second_site(self):
        reports = self.home / ".config/gsc-insights/reports"
        (reports / SITE).mkdir(parents=True)
        (reports / ".DS_Store").write_bytes(b"\0")
        code, _, err = self.run_cli("import", SITE, str(self.bing_file(bing_csv([1, 0]), name="bing-ai.csv")))
        self.assertEqual(code, 0, err)
        self.assertEqual(ar.known_sites(), {SITE}, "asserted where the site count is used, not only by the exit code")

    def test_counts_take_thousands_separators_and_never_decimals(self):
        cases = {"1,155": 1155, "1.155": 1155, "12": 12}
        for i, (text, n) in enumerate(cases.items()):
            with self.subTest(text):
                csv_text = bing_csv([1]).replace('"1","1"', f'"{text}","1"')
                code, _, err = self.run_cli("import", SITE, str(self.bing_file(csv_text, name=f"{SITE}_AIPerformance_{i}.csv")))
                self.assertEqual((code, self.saved("bing")["citations"]), (0, n), err)
        for i, text in enumerate(("3.5", "12,5", "1,15", "-1")):
            with self.subTest(text):
                csv_text = bing_csv([1]).replace('"1","1"', f'"{text}","1"')
                code, _, _ = self.run_cli("import", SITE, str(self.bing_file(csv_text, name=f"{SITE}_AIPerformance_x{i}.csv")))
                self.assertEqual(code, 1)

    def test_damaged_records_of_every_shape_read_as_nothing_added(self):
        d = self.home / ".config/gsc-insights/reports" / SITE
        d.mkdir(parents=True)
        good = {"state": "data", "total": 5, "first": "2026-07-12", "last": "2026-07-13", "pages": [], "search_type": "Web"}
        bad_google = [{"state": "empty", "first": "2026-10-01"}, dict(good, pages="x"), dict(good, pages=[["/a"]]),
                      dict(good, pages=[["/a", "3"]]), dict(good, search_type=5), dict(good, total=True),
                      dict(good, first="2026-07-14"), {"state": "not_shown", "checked": 5}, {"state": "other"}]
        for rec in bad_google:
            with self.subTest(rec):
                (d / "ai-google.json").write_text(json.dumps(rec))
                section, _ = self.page()
                self.assertIn("don't let programs read", section)
        (d / "ai-google.json").write_text(json.dumps(good))
        self.assertIn("shown 5 times", self.page()[0], "the good record itself is read")

    def test_one_day_reads_as_one_day(self):
        self.run_cli("import", SITE, str(self.bing_file(bing_csv([2]))))
        self.run_cli("import", SITE, str(self.google_zip(google_files(daily_chart([4]), [(f"https://{SITE}/", 4)]))))
        section, _ = self.page()
        self.assertIn("cited your pages 2 times on 14 July 2026.", section)
        self.assertIn("(AI Overviews and AI Mode) on 12 July 2026.", section)
        self.assertIn("the pages can add up to more than the total", section, "never a claim that they do")

    def test_not_shown_says_when_it_replaces_a_download(self):
        self.run_cli("import", SITE, str(self.google_zip(google_files(daily_chart([1] * 5), []))))
        code, out, _ = self.run_cli("not-shown", SITE)
        self.assertEqual(code, 0)
        self.assertIn(f"replaces the download you added earlier ({GOOGLE_ZIP})", out)

    def test_a_folder_unzipped_twice_is_read(self):
        outer = self.downloads / GOOGLE_ZIP[:-4]
        inner = outer / GOOGLE_ZIP[:-4]
        inner.mkdir(parents=True)
        for n, text in google_files(daily_chart([3] * 3), []).items():
            (inner / n).write_text(text, encoding="utf-8")
        (outer / "__MACOSX").mkdir()
        (outer / "__MACOSX" / "._Seiten.csv").write_bytes(b"\x00\x05junk")
        code, _, err = self.run_cli("import", SITE, str(outer))
        self.assertEqual((code, self.saved("google")["total"]), (0, 9), err)



class RoundTwoFindings(AiTest):
    """Review round 2. Invariant (F2, again): Google's report is known by its structure — the Web search
    type as a whole word, every view under one metric header, and a view that adds up to the chart's
    total; every address readable, both at import and when the page reads a saved record."""

    def refused(self, files, name):
        code, _, err = self.run_cli("import", SITE, str(self.google_zip(files, name=name)))
        self.assertEqual(code, 1, f"{name} was accepted")
        self.assertIn("Nothing was saved", err, "a refusal, never a traceback")
        self.assertIsNone(self.saved("google"))

    def test_an_unreadable_page_address_is_refused_at_import_and_ignored_when_saved(self):
        for i, url in enumerate(("https://[broken/", "http://[::1", "https://]x/")):
            with self.subTest(url):
                files = google_files(daily_chart([3] * 3), [(url, 9)])
                self.refused(files, f"{SITE}-u{i}.zip")
        d = self.home / ".config/gsc-insights/reports" / SITE
        d.mkdir(parents=True)
        (d / "ai-google.json").write_text(json.dumps({"state": "data", "total": 3, "first": "2026-07-12",
                                                      "last": "2026-07-12", "pages": [["https://[broken/", 3]]}))
        self.assertIn("don't let programs read", self.page()[0])

    def test_reports_that_only_look_like_googles_are_refused(self):
        web = "Filtern,Wert\nSuchtyp,Web (text-based)"
        cases = {
            "a filter value that only starts with web": dict(google_files(daily_chart([3] * 3), []),
                                                             **{"Filter.csv": "Kanal,Wert\nKamera,Webcam"}),
            "another web-word": dict(google_files(daily_chart([3] * 3), []),
                                     **{"Filter.csv": "Referrer,Wert\nQuelle,Website xyz"}),
            "a dated metric whose views add up to something else": {
                "Diagramm.csv": "Datum,Umsatz\n2026-10-01,5\n2026-10-02,7",
                "Seiten.csv": f"Seiten,Umsatz\nhttps://{SITE}/,12", "Land.csv": "Land,Umsatz\nDE,40", "Filter.csv": web},
            "a dated metric with no other view": {"Diagramm.csv": "Datum,Umsatz\n2026-10-01,5", "Filter.csv": web},
            "two pages files, the second one hiding another site": dict(
                google_files(daily_chart([3] * 3), [("https://other-site.de/", 9)]),
                **{"Seiten2.csv": f"Die häufigsten Seiten,Impressionen\nhttps://{SITE}/,9"}),
            "headers only beside the ordinary report's wide files": {
                "Diagramm.csv": "Datum,Impressionen", "Seiten.csv": "Seiten,Impressionen", "Filter.csv": web,
                "Queries.csv": "Top queries,Clicks,Impressions,CTR,Position"},
        }
        for i, (why, files) in enumerate(cases.items()):
            with self.subTest(why):
                self.refused(files, f"{SITE}-i{i}.zip")

    def test_a_saved_zero_is_never_shown_as_data(self):
        d = self.home / ".config/gsc-insights/reports" / SITE
        d.mkdir(parents=True)
        (d / "ai-google.json").write_text(json.dumps({"state": "data", "total": 0, "first": "2026-07-12",
                                                      "last": "2026-07-13", "pages": []}))
        (d / "ai-bing.json").write_text(json.dumps({"state": "data", "citations": 0, "days": 2, "days_cited": 0,
                                                    "first": "2026-07-14", "last": "2026-07-15"}))
        section, _ = self.page()
        self.assertIn("don't let programs read", section)
        self.no_zero_figures(section)

    def test_a_folder_with_upper_case_csv_names_is_read_whole(self):
        d = self.downloads / GOOGLE_ZIP[:-4]
        d.mkdir()
        for n, text in google_files(daily_chart([3] * 3), [(f"https://{SITE}/", 9)]).items():
            (d / (n[:-4] + ".CSV" if n.startswith("Seiten") else n)).write_text(text, encoding="utf-8")
        code, _, err = self.run_cli("import", SITE, str(d))
        self.assertEqual(code, 0, err)
        self.assertEqual(self.saved("google")["pages"], [[f"https://{SITE}/", 9]], "the pages file was not skipped")

    def test_a_count_may_use_one_kind_of_separator_only(self):
        for i, text in enumerate(("1,155.000", "1.155,000", "1 155,000")):
            with self.subTest(text):
                csv_text = bing_csv([1]).replace('"1","1"', f'"{text}","1"')
                code, _, _ = self.run_cli("import", SITE, str(self.bing_file(csv_text, name=f"{SITE}_AIPerformance_m{i}.csv")))
                self.assertEqual(code, 1)
                self.assertIsNone(self.saved("bing"))

    def test_the_import_line_for_an_empty_google_download_says_what_the_file_shows(self):
        code, out, _ = self.run_cli("import", SITE, str(self.google_zip(google_files(daily_chart([0] * 5), []))))
        self.assertEqual(code, 0)
        self.assertIn("your download shows no impressions", out)
        self.assertNotIn("yet", out)


if __name__ == "__main__":
    unittest.main()
