"""The weekly fix proposal on the owner's report page, entered through search_report.build().

Why: the report is where the owner meets the proposal, and the weekly job reaches it only through
build(). A proposal chosen from saved data after Google failed, a thin site told it has work to
do, a "no" forgotten a week later or a before-and-after that claims more than it checked would
each reach the owner from here. Each test runs one scenario of
docs/reviews/SKILL-PLAN-scheduled-search-fixes.md through build(), with the fake Google of
test_search_report.py, a stand-in for the owner's live page and for GitHub, and the assistant's
own commands (fix_proposal.main) in between, as the owner would see it week after week. The live
page reader itself is tested against a local web server at the end.

Run:  python3 -m unittest discover -s skills/search-console-insights/scripts/tests
"""
import datetime as dt
import html
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import fix_proposal as fp  # noqa: E402
import search_report as sr  # noqa: E402
from test_search_report import FakeGoogle  # noqa: E402

SITE = "radwerk-plagwitz.example"
PAGE = f"https://{SITE}/reparatur"
QUERY = "fahrrad reparatur leipzig"
OLD_TITLE = "Reparatur und Service | Radwerk Plagwitz"
NEW_TITLE = "Fahrradreparatur in Leipzig-Plagwitz | Radwerk Plagwitz"
PR = "https://github.com/example-owner/radwerk/pull/31"
D = dt.date.fromisoformat

# Report Mondays and the first date Google calls incomplete on each (a three-day lag).
WEEKS = {"2026-11-02": "2026-10-30", "2026-11-09": "2026-11-06", "2026-11-16": "2026-11-13",
         "2026-12-14": "2026-12-11"}


def q(text, imp, pos, clicks=0):
    return {"keys": [text], "impressions": imp, "position": pos, "clicks": clicks}


def qp(text, page, imp):
    return {"keys": [text, page], "impressions": imp}


def daily(end, days=120, impressions=100):
    return {(end - dt.timedelta(days=i)).isoformat(): (5, impressions, 9.0) for i in range(days)}


def old_page(url):
    return {"title": OLD_TITLE, "h1": "Reparatur und Service", "first_paragraph": "Wir reparieren Räder."}


def new_page(url):
    return {"title": NEW_TITLE, "h1": "Fahrradreparatur in Leipzig", "first_paragraph": "Wir reparieren Räder."}


class ProposalReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / ".config/gsc-insights").mkdir(parents=True)
        self.env = mock.patch.dict(os.environ, {"HOME": str(self.home)}, clear=False)
        self.env.start()
        for k in ("GSC_HISTORY_CSV", "GSC_COUNTRY", "BING_API_KEY"):
            os.environ.pop(k, None)
        self.reads = []

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def google(self, monday, **kw):
        fid = WEEKS[monday]
        kw.setdefault("daily", daily(D(fid) - dt.timedelta(days=1)))
        kw.setdefault("queries", [q(QUERY, 286, 11.6, 2), q("radwerk plagwitz", 900, 1.2, 80)])
        kw.setdefault("query_pages", [qp(QUERY, PAGE, 271), qp(QUERY, f"https://{SITE}/", 15)])
        return FakeGoogle(fid=fid, **kw)

    def build(self, monday, google=None, page=old_page, gh=None, site=SITE):
        g = google or self.google(monday)

        def read(url):
            self.reads.append(url)
            return page(url)

        out = sr.build(site, SimpleNamespace(keywords="", country=None, csv=None),
                       service_factory=g if callable(g) and not isinstance(g, FakeGoogle) else (lambda: g),
                       today=D(monday), page_reader=read, gh=gh or (lambda repo, number: None))
        return out.read_text(encoding="utf-8")

    def state(self, site=SITE):
        return json.loads(fp.state_path(site).read_text(encoding="utf-8"))

    def assistant(self, *argv):
        self.assertEqual(fp.main(list(argv)), 0)


class Scenarios(ProposalReportTest):
    def test_scenario_1_the_report_proposes_one_fix_and_the_sentence_to_say(self):
        page = self.build("2026-11-02")
        self.assertIn("One thing to fix this week", page)
        self.assertIn(html.escape(f"Work “{QUERY}” into the title, heading and first paragraph of /reparatur"), page)
        self.assertIn("In the 4 weeks 2026-09-28 to 2026-10-25", page)
        self.assertIn("286 times, at an average position of 11.6; 271 of those times on this page", page)
        self.assertIn(html.escape(f"search-console-insights: work '{QUERY}' into the title, heading and "
                                  f"first paragraph of {PAGE}"), page)
        self.assertEqual(self.reads, [PAGE])             # only the proposal's own page is read
        st = self.state()
        self.assertEqual(st["current"], fp.proposal_key(PAGE, QUERY))
        self.assertEqual(st["proposals"][st["current"]]["old_title"], OLD_TITLE)
        self.assertIn("Counted as your business name: radwerk plagwitz, radwerkplagwitz", page)

    def test_scenario_2_a_thin_site_gets_an_honest_week_and_no_file(self):
        site = "tonstube-kassel.example"
        start = D("2026-09-28")
        days = {(start + dt.timedelta(days=i)).isoformat(): (0, 4, 14.0) for i in range(16)}  # 16 × 4 = 64
        queries = [q("tonstube kassel", 41, 1.0)] + [q(f"keramik {i}", 3, 14.0) for i in range(9)]
        g = self.google("2026-11-02", daily=days, queries=queries,
                        query_pages=[qp(r["keys"][0], f"https://{site}/", r["impressions"]) for r in queries])
        page = self.build("2026-11-02", google=g, site=site)
        self.assertIn("Too little data to propose a change this week: shown 64 times in 4 weeks "
                      "(2026-09-28 to 2026-10-25), 41 of them for your name.", page)
        self.assertIn(f"a search shown {fp.T1_MIN_IMPRESSIONS} times at position 8 to 20", page)
        self.assertEqual(self.reads, [])
        self.assertFalse(fp.state_path(site).exists())

    def test_scenario_6_the_owners_no_holds_and_the_page_says_until_when(self):
        self.build("2026-11-02")
        self.assistant("decline", SITE)
        until = dt.date.today() + dt.timedelta(days=fp.DECLINE_DAYS)
        page = self.build("2026-11-09")
        self.assertNotIn(html.escape(f"Work “{QUERY}”"), page)
        self.assertIn(html.escape(f"“{QUERY}” on /reparatur: turned down; not proposed again before {until:%d %B %Y}."), page)

    def test_scenario_8_from_the_pull_request_to_before_and_after(self):
        self.build("2026-11-02")                                          # old title seen
        self.assistant("acted", SITE, "--pr", PR, "--new-title", NEW_TITLE)
        merged = lambda repo, number: {"state": "MERGED", "mergedAt": "2026-11-03T10:00:00Z", "closedAt": "2026-11-03T10:00:00Z"}

        page = self.build("2026-11-09", page=new_page, gh=merged)         # new title seen
        self.assertIn(html.escape("live; the before-and-after comparison appears once Google's numbers reach "
                                  "06 December 2026"), page)
        # The page stays out of new proposals, and the page says why in the owner's words.
        self.assertIn(html.escape(f"“{QUERY}”: an earlier change to the same page is still being measured"), page)

        measure = {(QUERY, "2026-10-05", "2026-11-01"): {"impressions": 279, "clicks": 2, "position": 11.4},
                   (QUERY, "2026-11-09", "2026-12-06"): {"impressions": 402, "clicks": 9, "position": 7.9}}
        page = self.build("2026-12-14", google=self.google("2026-12-14", measure=measure), page=new_page, gh=merged)
        self.assertIn("position 11.4 → 7.9, shown 279 → 402 times, visits 2 → 9", page)
        self.assertIn(html.escape("This compares one search before and after the change. It does not check "
                                  "what else changed on your site or in Google's results."), page)
        self.assertNotIn(html.escape(f"Work “{QUERY}”"), page)     # "Fahrradreparatur" now carries the words
        self.assertNotIn("consistent with", page)
        self.assertNotIn("caused", page)
        rec = self.state()["proposals"][fp.proposal_key(PAGE, QUERY)]
        self.assertEqual((rec["result"]["before"]["from"], rec["result"]["after"]["to"]), ("2026-10-05", "2026-12-06"))

    def test_a_closed_pull_request_counts_as_no_from_its_closing_day(self):
        self.build("2026-11-02")
        self.assistant("acted", SITE, "--pr", PR, "--new-title", NEW_TITLE)
        closed = lambda repo, number: {"state": "CLOSED", "mergedAt": None, "closedAt": "2026-11-04T08:00:00Z"}
        page = self.build("2026-11-09", gh=closed)
        self.assertIn("turned down; not proposed again before 27 January 2027", page)

    def test_merged_but_not_live_names_the_publishing_step(self):
        self.build("2026-11-02")
        self.assistant("acted", SITE, "--pr", PR, "--new-title", NEW_TITLE)
        merged = lambda repo, number: {"state": "MERGED", "mergedAt": "2026-11-03T10:00:00Z", "closedAt": None}
        page = self.build("2026-11-09", gh=merged)                        # still the old title live
        self.assertIn("merged in pull request 31, not seen on the live site yet", page)
        self.assertIn("npm run ship", page)

    def test_github_out_of_reach_changes_nothing_and_says_so(self):
        self.build("2026-11-02")
        self.assistant("acted", SITE, "--pr", PR, "--new-title", NEW_TITLE)
        page = self.build("2026-11-09")                                   # gh answers None
        self.assertIn("pull request 31 could not be checked; tell your assistant if it was closed", page)

    def test_scenario_9_no_new_proposal_from_saved_data(self):
        self.build("2026-11-02")
        self.reads.clear()

        def expired():
            raise sr.SignInError("token expired")
        page = self.build("2026-11-09", google=expired)
        self.assertIn("No new proposal this week: Google's numbers could not be refreshed.", page)
        self.assertNotIn(html.escape(f"Work “{QUERY}”"), page)
        self.assertEqual(self.reads, [])

    def test_a_damaged_proposals_file_costs_the_section_not_the_page(self):
        fp.state_path(SITE).parent.mkdir(parents=True, exist_ok=True)
        fp.state_path(SITE).write_text("[]", encoding="utf-8")
        page = self.build("2026-11-02")
        self.assertIn("How people find you on Google", page)
        self.assertIn("could not be worked out", page)
        self.assertEqual(fp.state_path(SITE).read_text(encoding="utf-8"), "[]")


class _Pages(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/reparatur":
            body = f"<html><head><title>{OLD_TITLE}</title></head><body><h1>Reparatur</h1></body></html>".encode()
            self.send_response(200)
        elif self.path == "/huge":
            body = b"<title>x</title>" + b"a" * (sr.PAGE_MAX_BYTES + 10)
            self.send_response(200)
        else:
            body = b"not here"
            self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class LivePageReader(unittest.TestCase):
    """read_live_page against a real local server: what the report reads from the owner's site."""

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), _Pages)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_the_owners_page_is_read(self):
        self.assertEqual(sr.read_live_page(self.base + "/reparatur", "127.0.0.1")["title"], OLD_TITLE)

    def test_a_missing_or_oversized_page_is_unreadable(self):
        self.assertIsNone(sr.read_live_page(self.base + "/gone", "127.0.0.1"))
        self.assertIsNone(sr.read_live_page(self.base + "/huge", "127.0.0.1"))

    def test_another_host_is_never_fetched(self):
        self.assertIsNone(sr.read_live_page(self.base + "/reparatur", "radwerk-plagwitz.example"))
        self.assertIsNone(sr.read_live_page("file:///etc/passwd", "127.0.0.1"))


if __name__ == "__main__":
    unittest.main()
