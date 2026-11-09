"""gsc_query.py: fixed windows, the completeness check, the exact page match, --pages-csv.

Why: a moved page is judged against two fixed 28-day windows (website-new-page, "Moving a page
from an old site"). A window that slides with today's date, a page filter that matches more
than the one address, a day Search Console has not filled yet, or a page list cut at 25,000
rows would each give a false drop or a false all-clear. Every test enters through main(), as a
run from the command line does; the Google service is a stub that records each request body.

The real-answer test reads fixtures/gsc-searchanalytics-query-googleapiclient-2.198.0.json, a
live answer of the API (property sc-domain:croftweaver.com, window 2026-10-10 to 2026-11-06,
page rows cut to the first five). Its expected values below were read off that file by hand:
27 date rows (2026-10-10 has none), the last 2026-11-06; five pages, the first with 2 clicks
on 18 impressions.

Run:  python3 -m unittest discover -s skills/search-console-insights/scripts/tests
"""
import contextlib
import csv
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import gsc_query  # noqa: E402

REAL = json.loads((Path(__file__).parent / "fixtures" /
                   "gsc-searchanalytics-query-googleapiclient-2.198.0.json").read_text(encoding="utf-8"))


def row(key, clicks=0, impressions=1, ctr=0.0, position=5.0):
    return {"keys": [key], "clicks": clicks, "impressions": impressions, "ctr": ctr,
            "position": position}


class FakeService:
    """Answers by the request's dimensions and startRow; keeps every body it was sent."""

    def __init__(self, answer):
        self.answer, self.bodies = answer, []

    def sites(self):
        return mock.Mock(list=lambda: mock.Mock(
            execute=lambda: {"siteEntry": [{"siteUrl": "sc-domain:example.com",
                                            "permissionLevel": "siteOwner"}]}))

    def searchanalytics(self):
        outer = self

        class Q:
            def query(self, siteUrl, body):
                outer.bodies.append(body)
                return mock.Mock(execute=lambda: {"rows": outer.answer(body)})
        return Q()


def run_main(service, *args):
    """main() as the command line runs it; returns (exit code or None, stdout, stderr)."""
    argv = ["gsc_query.py", "--site", "sc-domain:example.com", "--no-csv", *args]
    out, err, code = io.StringIO(), io.StringIO(), None
    with mock.patch.object(sys, "argv", argv), \
            mock.patch.object(gsc_query, "load_credentials", return_value=object()), \
            mock.patch.object(gsc_query, "build_service", return_value=service), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            gsc_query.main()
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


def answer_with(date_rows=(), page_rows=(), query_rows=()):
    def answer(body):
        dims = body.get("dimensions", [])
        if dims == ["date"]:
            return list(date_rows)
        if dims == ["page"]:
            return list(page_rows)
        if dims == ["query"]:
            return list(query_rows)
        return []
    return answer


class FixedWindow(unittest.TestCase):
    def test_start_and_end_are_sent_as_given_and_every_pull_uses_them(self):
        svc = FakeService(answer_with())
        code, out, _ = run_main(svc, "--start", "2026-09-11", "--end", "2026-10-08")
        self.assertIsNone(code)
        self.assertTrue(svc.bodies)
        for b in svc.bodies:
            self.assertEqual((b["startDate"], b["endDate"]), ("2026-09-11", "2026-10-08"))
        self.assertIn("2026-09-11 → 2026-10-08 (28 days)", out)   # days counted inclusive

    def test_days_still_ends_two_days_ago_and_spans_exactly_n_days(self):
        svc = FakeService(answer_with())
        run_main(svc, "--days", "28")
        end = dt.date.today() - dt.timedelta(days=2)
        b = svc.bodies[0]
        self.assertEqual(b["endDate"], end.isoformat())
        self.assertEqual(b["startDate"], (end - dt.timedelta(days=27)).isoformat())

    def test_no_flag_still_means_90_days(self):
        svc = FakeService(answer_with())
        run_main(svc)
        b = svc.bodies[0]
        span = dt.date.fromisoformat(b["endDate"]) - dt.date.fromisoformat(b["startDate"])
        self.assertEqual(span.days, 89)

    def test_wrong_flags_stop_before_any_request(self):
        today = dt.date.today()
        cases = {
            "start alone": ["--start", "2026-09-11"],
            "end alone": ["--end", "2026-10-08"],
            "days with a window": ["--days", "28", "--start", "2026-09-11", "--end", "2026-10-08"],
            "start after end": ["--start", "2026-10-08", "--end", "2026-09-11"],
            "end in the future": ["--start", "2026-09-11",
                                  "--end", (today + dt.timedelta(days=1)).isoformat()],
            "not a date": ["--start", "11.09.2026", "--end", "2026-10-08"],
            "impossible date": ["--start", "2026-02-30", "--end", "2026-03-08"],
        }
        for name, args in cases.items():
            with self.subTest(name):
                svc = FakeService(answer_with())
                code, _, err = run_main(svc, *args)
                self.assertEqual(code, 2, err)
                self.assertEqual(svc.bodies, [])

    def test_a_fixed_window_adds_no_history_row(self):
        # The history file dates its rows today; a window from September would read as today's.
        svc = FakeService(answer_with(query_rows=[row("backkurs münchen", 3, 40)]))
        with tempfile.TemporaryDirectory() as d:
            hist = os.path.join(d, "history.csv")
            argv = ["gsc_query.py", "--site", "sc-domain:example.com", "--csv", hist,
                    "--keywords", "backkurs münchen", "--start", "2026-09-11", "--end", "2026-10-08"]
            err = io.StringIO()
            with mock.patch.object(sys, "argv", argv), \
                    mock.patch.object(gsc_query, "load_credentials", return_value=object()), \
                    mock.patch.object(gsc_query, "build_service", return_value=svc), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                gsc_query.main()
            self.assertFalse(os.path.exists(hist))
        self.assertIn("not added to the history CSV", err.getvalue())


class PageFilter(unittest.TestCase):
    def test_page_filter_is_sent_with_operator_equals(self):
        svc = FakeService(answer_with())
        run_main(svc, "--page", "https://example.com/backkurs-muenchen/")
        filtered = [b for b in svc.bodies if "dimensionFilterGroups" in b]
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["dimensionFilterGroups"][0]["filters"],
                         [{"dimension": "page", "operator": "equals",
                           "expression": "https://example.com/backkurs-muenchen/"}])


    def test_a_page_with_more_than_100_queries_says_how_many_it_cut(self):
        rows = [row(f"query {n:03d}", clicks=200 - n) for n in range(120)]
        svc = FakeService(answer_with(query_rows=rows))
        _, out, _ = run_main(svc, "--page", "https://example.com/a/")
        section = out.split("## Queries landing on")[1].split("\n## ")[0]
        self.assertIn("query 099", section)
        self.assertNotIn("query 100", section)
        self.assertIn("Showing 100 of 120 queries.", section)

    def test_a_query_served_by_more_than_100_pages_says_how_many_it_cut(self):
        rows = [row(f"https://example.com/p{n:03d}/", clicks=200 - n) for n in range(120)]
        svc = FakeService(answer_with(page_rows=rows))
        _, out, _ = run_main(svc, "--query", "backkurs")
        section = out.split("## Pages serving")[1].split("\n## ")[0]
        self.assertIn("/p099/", section)
        self.assertNotIn("/p100/", section)
        self.assertIn("Showing 100 of 120 pages.", section)


class Completeness(unittest.TestCase):
    def dates(self, first, last):
        d, rows = dt.date.fromisoformat(first), []
        while d <= dt.date.fromisoformat(last):
            rows.append(row(d.isoformat()))
            d += dt.timedelta(days=1)
        return rows

    def test_rows_up_to_the_last_day_make_the_window_complete(self):
        svc = FakeService(answer_with(date_rows=self.dates("2026-10-10", "2026-11-06")))
        _, out, _ = run_main(svc, "--start", "2026-10-10", "--end", "2026-11-06", "--by-date")
        self.assertIn("**Complete.**", out)
        self.assertNotIn("Not complete", out)
        self.assertEqual([b["dimensions"] for b in svc.bodies if b.get("dimensions") == ["date"]],
                         [["date"]])
        date_body = [b for b in svc.bodies if b.get("dimensions") == ["date"]][0]
        self.assertNotIn("dimensionFilterGroups", date_body)   # the property's own rows

    def test_rows_that_stop_short_of_the_last_day_are_not_complete(self):
        svc = FakeService(answer_with(date_rows=self.dates("2026-10-10", "2026-11-04")))
        _, out, _ = run_main(svc, "--start", "2026-10-10", "--end", "2026-11-06", "--by-date")
        self.assertIn("**Not complete.**", out)
        self.assertIn("last day with rows is 2026-11-04", out)
        self.assertNotIn("**Complete.**", out)

    def test_a_window_with_no_rows_at_all_is_not_complete_and_still_says_so(self):
        # The report's "no data" early return must not swallow the verdict.
        svc = FakeService(answer_with())
        _, out, _ = run_main(svc, "--start", "2026-10-10", "--end", "2026-11-06", "--by-date")
        self.assertIn("No Search Analytics data in this window", out)
        self.assertIn("**Not complete.**", out)
        self.assertIn("no rows by date", out)

    def test_without_the_flag_there_is_no_date_pull_and_no_verdict(self):
        svc = FakeService(answer_with(date_rows=self.dates("2026-10-10", "2026-11-06")))
        _, out, _ = run_main(svc, "--start", "2026-10-10", "--end", "2026-11-06")
        self.assertNotIn(["date"], [b.get("dimensions") for b in svc.bodies])
        self.assertNotIn("Is this window complete?", out)

    def test_a_day_inside_the_window_with_no_row_is_named_but_does_not_block(self):
        rows = [r for r in self.dates("2026-10-10", "2026-11-06") if r["keys"][0] != "2026-10-20"]
        svc = FakeService(answer_with(date_rows=rows))
        _, out, _ = run_main(svc, "--start", "2026-10-10", "--end", "2026-11-06", "--by-date")
        self.assertIn("**Complete.**", out)
        self.assertIn("no row: 2026-10-20", out)


class PagesCsv(unittest.TestCase):
    def test_pages_past_25000_rows_are_paged_with_startrow_and_all_written(self):
        full = [row(f"https://example.com/p{i}", 1, 2) for i in range(gsc_query.ROW_LIMIT)]
        rest = [row("https://example.com/last", 0, 1), row("https://example.com/last2", 0, 1)]

        def answer(body):
            if body.get("dimensions") == ["page"]:
                return rest if body.get("startRow") == gsc_query.ROW_LIMIT else full
            return []
        svc = FakeService(answer)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "pages.csv")
            code, _, err = run_main(svc, "--pages-csv", path)
            self.assertIsNone(code, err)
            with open(path, encoding="utf-8", newline="") as f:
                lines = list(csv.reader(f))
        self.assertEqual(lines[0], ["page", "clicks", "impressions", "ctr", "position"])
        self.assertEqual(len(lines) - 1, gsc_query.ROW_LIMIT + 2)
        self.assertEqual(lines[-1][0], "https://example.com/last2")
        page_bodies = [b for b in svc.bodies if b.get("dimensions") == ["page"]]
        self.assertEqual([b.get("startRow", 0) for b in page_bodies], [0, gsc_query.ROW_LIMIT])

    def test_a_short_answer_is_one_request(self):
        svc = FakeService(answer_with(page_rows=[row("https://example.com/a", 4, 9)]))
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "pages.csv")
            run_main(svc, "--pages-csv", path)
            text = Path(path).read_text(encoding="utf-8")
        self.assertEqual(len([b for b in svc.bodies if b.get("dimensions") == ["page"]]), 1)
        self.assertIn("https://example.com/a,4,9,", text)

    def test_a_loop_that_never_ends_stops_loudly(self):
        full = [row(f"https://example.com/p{i}") for i in range(gsc_query.ROW_LIMIT)]
        svc = FakeService(answer_with(page_rows=full))
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(gsc_query, "MAX_PAGED_REQUESTS", 3):
            code, _, err = run_main(svc, "--pages-csv", os.path.join(d, "pages.csv"))
        self.assertEqual(code, 1)
        self.assertIn("not paging further", err)

    def test_an_unwritable_path_exits_1_and_says_so(self):
        svc = FakeService(answer_with(page_rows=[row("https://example.com/a")]))
        code, _, err = run_main(svc, "--pages-csv", "/nonexistent-folder/pages.csv")
        self.assertEqual(code, 1)
        self.assertIn("Could not write", err)


class RealAnswer(unittest.TestCase):
    """The API's own answer, not our stub's idea of one."""

    def svc(self):
        return FakeService(answer_with(date_rows=REAL["date"]["rows"], page_rows=REAL["page"]["rows"]))

    def test_the_real_date_rows_make_the_window_complete_and_name_the_missing_first_day(self):
        _, out, _ = run_main(self.svc(), "--start", "2026-10-10", "--end", "2026-11-06", "--by-date")
        self.assertIn("**Complete.**", out)
        self.assertIn("no row: 2026-10-10", out)

    def test_the_same_rows_do_not_complete_a_window_that_ends_two_days_later(self):
        _, out, _ = run_main(self.svc(), "--start", "2026-10-12", "--end", "2026-11-08", "--by-date")
        self.assertIn("last day with rows is 2026-11-06", out)

    def test_the_real_page_rows_reach_the_csv(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "pages.csv")
            run_main(self.svc(), "--start", "2026-10-10", "--end", "2026-11-06", "--pages-csv", path)
            with open(path, encoding="utf-8", newline="") as f:
                lines = list(csv.reader(f))
        self.assertEqual(len(lines) - 1, 5)
        self.assertEqual(lines[1][:3], ["https://croftweaver.com/", "2", "18"])


if __name__ == "__main__":
    unittest.main()
