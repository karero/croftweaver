"""search_report.py — the owner's Google & Bing report page.

Why: this page is what a non-technical owner reads to decide whether their site is doing well. A
wrong number here is worse than no page: a sum of positions, a percentage on three visits or a
half-finished week read as a drop would all send them the wrong way. Every test below pins one
rule of docs/reviews/SKILL-PLAN-gsc-report.md (S1–S16 and the counting rules) and enters through
the same `build()` the command line calls, with a fake Google that records every request.

Run:  python3 -m unittest discover -s skills/search-console-insights/scripts/tests
"""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import search_report as sr  # noqa: E402

TODAY = dt.date(2026, 9, 27)                 # a Sunday
FID = "2026-09-25"                           # Google: numbers from 25 Sept on may still change
FINISHED = dt.date(2026, 9, 24)              # so the data ends on Thursday 24 Sept
LAST_SUNDAY = dt.date(2026, 9, 20)           # the last complete week ends here
DOMAIN = "example-bakery.de"


def d(x):
    return x.isoformat()


class FakeGoogle:
    """Answers Search Analytics requests from scenario data and records every request body."""

    def __init__(self, daily=None, keys=None, queries=None, pages=None, drill=None,
                 fid=FID, fail=None, refuse_domain=False, sites=None, query_pages=None, measure=None):
        self.daily = daily or {}          # date -> (clicks, impressions, position)
        self.keys = keys or {}            # lowercase query -> {date: (clicks, impressions, position)}
        self.queries = queries or []      # rows for ["query"]
        self.pages = pages or []          # rows for ["page"]
        self.drill = drill or {}          # query -> page rows
        self.fid, self.fail, self.refuse = fid, fail, refuse_domain
        self.sites_list = sites or []
        self.query_pages = query_pages or []   # rows for ["query", "page"] (the fix proposal)
        self.measure = measure or {}           # (query, start, end) -> one ["query"] row (its measuring)
        self.calls = []

    # the googleapiclient shape: service.searchanalytics().query(siteUrl=, body=).execute()
    def searchanalytics(self):
        return self

    def sites(self):
        return SimpleNamespace(list=lambda: SimpleNamespace(execute=lambda: {"siteEntry": self.sites_list}))

    def query(self, siteUrl, body):
        return SimpleNamespace(execute=lambda: self._answer(siteUrl, body))

    def _answer(self, site, body):
        self.calls.append((site, body))
        if self.refuse and site.startswith("sc-domain:"):
            raise RuntimeError('<HttpError 403 returned "User does not have sufficient permission">')
        if self.fail and self.fail(body):
            raise RuntimeError('<HttpError 429 returned "Quota exceeded">')
        dims = body.get("dimensions")
        if not dims:
            return {}
        start, end = body["startDate"], body["endDate"]
        qf = [f["expression"] for g in body.get("dimensionFilterGroups", []) for f in g["filters"]
              if f["dimension"] == "query"]
        if dims == ["date"]:
            rows = [{"keys": [k], "clicks": c, "impressions": i, "position": p}
                    for k, (c, i, p) in sorted(self.daily.items()) if start <= k <= end]
            resp = {"rows": rows}
            if body.get("dataState") == "all" and self.fid:
                resp["metadata"] = {"firstIncompleteDate": self.fid}
            return resp
        if dims == ["date", "query"]:
            assert len(qf) == 1, "one key search per request"
            data = self.keys.get(qf[0], {})
            return {"rows": [{"keys": [k, qf[0]], "clicks": c, "impressions": i, "position": p}
                             for k, (c, i, p) in sorted(data.items()) if start <= k <= end]}
        if dims == ["query"]:
            if qf:
                row = self.measure.get((qf[0], start, end))
                return {"rows": [dict(row, keys=[qf[0]])] if row else []}
            return {"rows": self.queries}
        if dims == ["query", "page"]:
            return {"rows": self.query_pages}
        if dims == ["page"]:
            return {"rows": self.drill.get(qf[0], []) if qf else self.pages}
        raise AssertionError(dims)


def daily_series(days, clicks=10, impressions=100, position=5.0, end=FINISHED):
    """`days` consecutive days ending at `end`, each with the same numbers."""
    return {d(end - dt.timedelta(days=i)): (clicks, impressions, position) for i in range(days)}


def weekly_key(positions, impressions=50, end=LAST_SUNDAY):
    """A key search whose complete weeks (oldest first, ending at `end`) sit at these positions;
    every day of a week carries the week's position and impressions/7."""
    out = {}
    n = len(positions)
    for w, pos in enumerate(positions):
        monday = end - dt.timedelta(days=7 * (n - w) - 1)
        for i in range(7):
            out[d(monday + dt.timedelta(days=i))] = (0, impressions / 7, pos)
    return out


def args(**kw):
    base = {"keywords": None, "country": None, "csv": None}
    base.update(kw)
    return SimpleNamespace(**base)


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / ".config/gsc-insights").mkdir(parents=True)
        self.env = mock.patch.dict(os.environ, {"HOME": str(self.home)}, clear=False)
        self.env.start()
        for k in ("GSC_HISTORY_CSV", "GSC_COUNTRY", "BING_API_KEY"):
            os.environ.pop(k, None)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def build(self, google, domain=DOMAIN, **kw):
        factory = google if callable(google) and not isinstance(google, FakeGoogle) else (lambda: google)
        # Never the network: the owner's live page and GitHub are stood in for here, and tested
        # with a local server and a stub gh in test_fix_proposal_report.py.
        out = sr.build(domain, args(**kw), service_factory=factory, today=TODAY,
                       page_reader=lambda url: None, gh=lambda repo, number: None)
        return out.read_text(encoding="utf-8"), out

    def cache(self, domain=DOMAIN):
        p = self.home / ".config/gsc-insights/reports" / domain / "google-data.json"
        return json.loads(p.read_text()) if p.exists() else None

    def history(self, rows, name="history.csv"):
        p = self.home / ".config/gsc-insights" / name
        cols = ["date", "site", "source", "keyword", "query", "position", "impressions", "clicks", "window", "country"]
        with open(p, "w") as f:
            f.write(",".join(cols) + "\n")
            for r in rows:
                f.write(",".join(str(r.get(c, "")) for c in cols) + "\n")
        return p


class CountingRules(ReportTest):
    def test_only_complete_weeks_count_at_both_ends(self):
        """A half week at either end would read as a drop (or a jump) that never happened."""
        daily = daily_series(40)                     # 16 Aug (Sun) … 24 Sep (Thu)
        weeks = sr.complete_weeks([{"date": k, "clicks": c, "impressions": i, "position": p}
                                   for k, (c, i, p) in daily.items()], FINISHED)
        self.assertEqual(weeks[0]["monday"], dt.date(2026, 8, 17))   # the lone Sunday 16 Aug is dropped
        self.assertEqual(weeks[-1]["monday"], dt.date(2026, 9, 14))  # 21–24 Sept is unfinished
        self.assertTrue(all(w["clicks"] == 70 for w in weeks))

    def test_a_quiet_day_inside_the_range_counts_as_zero(self):
        """Google sends no row for a day without data; dropping the week would hide a quiet week."""
        daily = daily_series(14, end=LAST_SUNDAY)
        del daily[d(LAST_SUNDAY - dt.timedelta(days=2))]
        weeks = sr.complete_weeks([{"date": k, "clicks": c, "impressions": i, "position": p}
                                   for k, (c, i, p) in daily.items()], FINISHED)
        self.assertEqual([w["clicks"] for w in weeks], [70, 60])

    def test_weekly_position_is_weighted_by_impressions_never_summed(self):
        """Seven days at position 8 must be position 8, not 56; a busy day weighs more."""
        rows = [{"date": d(dt.date(2026, 9, 14) + dt.timedelta(days=i)), "clicks": 0, "impressions": 10,
                 "position": 8.0} for i in range(7)]
        rows[0]["impressions"], rows[0]["position"] = 90, 2.0
        w = sr.complete_weeks(rows, FINISHED)[0]
        self.assertAlmostEqual(w["position"], (90 * 2 + 60 * 8) / 150)

    def test_moves_count_both_ways_and_need_two_usable_weeks_per_side(self):
        """A drop must be reported as a drop (round 6's BUG: only rises counted)."""
        def weeks(ps, imp=50):
            return [{"position": p, "impressions": imp, "hollow": imp < 10} for p in ps]
        self.assertEqual(sr.move(weeks([12, 12, 12, 12, 8, 8, 8, 8]))[:2], ("up", 4))
        self.assertEqual(sr.move(weeks([8, 8, 8, 8, 12, 12, 12, 12]))[:2], ("down", 4))
        self.assertEqual(sr.move(weeks([8.2, 8, 8, 8, 8.4, 8, 8, 8]))[0], "flat")
        thin = weeks([12, 12, 12, 12, 8, 8, 8, 8])
        for w in thin[4:7]:
            w["hollow"] = True
        self.assertEqual(sr.move(thin)[0], "thin")

    def test_headline_percentage_needs_twenty_visits_on_both_sides(self):
        """"100% more" about three extra visits would mislead; small numbers are given as numbers."""
        def wk(clicks):
            return [{"clicks": c} for c in clicks]
        self.assertEqual(sr.headline(wk([87, 87, 87, 88, 98, 101, 104, 109]), []),
                         "412 visits from Google in the last 4 weeks, 18% more than the 4 weeks before.")
        self.assertEqual(sr.headline(wk([1, 1, 1, 0, 2, 2, 1, 1]), []),
                         "6 visits from Google in the last 4 weeks, 3 in the 4 weeks before.")
        self.assertEqual(sr.headline(wk([0, 0, 0, 0, 3, 4, 0, 5]), []),
                         "12 visits from Google in the last 4 weeks, none in the 4 weeks before.")
        self.assertEqual(sr.headline(wk([0] * 8), []), "No visits from Google in the last 8 weeks.")

    def test_headline_follows_the_number_of_complete_weeks(self):
        """A young site must not be told about "the last 4 weeks" it doesn't have (round 3's BUG)."""
        self.assertEqual(sr.headline([{"clicks": 10}, {"clicks": 13}], []), "23 visits from Google in the last 2 weeks.")
        self.assertEqual(sr.headline([{"clicks": 5}] * 5, []), "20 visits from Google in the last 4 weeks.")
        self.assertIsNone(sr.headline([], []))

    def test_headline_names_every_outcome_so_a_drop_is_never_hidden(self):
        self.assertEqual(sr.moves_sentence(["up", "up", "up", "down", "thin"]),
                         "3 of your 5 key searches moved up, 1 moved down, 1 had too little data to tell")
        self.assertEqual(sr.moves_sentence(["flat", "flat", "flat", "thin", "thin"]),
                         "Of your 5 key searches, 3 showed no clear change, 2 had too little data to tell")
        # All thin: nothing is known about moves, so nothing is claimed (review round 1).
        self.assertEqual(sr.moves_sentence(["thin", "thin"]), "Of your 2 key searches, 2 had too little data to tell")


class Scenarios(ReportTest):
    def google(self, **kw):
        kw.setdefault("daily", daily_series(480))
        return FakeGoogle(**kw)

    def test_s1_first_look_is_full_on_day_one(self):
        """Charts come straight from Google, so a new tracker still shows 16 months at once."""
        g = self.google(keys={"sourdough munich": weekly_key([9] * 13)})
        page, out = self.build(g, keywords="Sourdough Munich")
        self.assertIn("Visits from Google, per week", page)
        self.assertIn("“Sourdough Munich”", page)
        self.assertEqual(out, self.home / ".config/gsc-insights/reports" / DOMAIN / "google.html")
        self.assertEqual(self.cache()["finished"], d(FINISHED))
        self.assertIn("No Bing data for these searches yet", page)   # not known before a recorded run

    def test_s2_headline_on_the_real_page(self):
        daily = {}
        for w, c in enumerate([87, 87, 87, 88, 98, 101, 104, 109]):
            monday = LAST_SUNDAY - dt.timedelta(days=7 * (8 - w) - 1)
            for i in range(7):
                daily[d(monday + dt.timedelta(days=i))] = (c / 7, 100, 5)
        keys = {"a": weekly_key([12] * 4 + [8] * 4 + [8] * 5, end=LAST_SUNDAY)}
        page, _ = self.build(self.google(daily=daily, keys=keys), keywords="a")
        self.assertIn("412 visits from Google in the last 4 weeks, 18% more than the 4 weeks before.", page)

    def test_s3_card_numbers_agree_with_each_other(self):
        """"about 8 now, up 4 places": the two numbers on a card come from the same rounding."""
        g = self.google(keys={"a": weekly_key([12] * 9 + [8] * 4)})
        page, _ = self.build(g, keywords="a")
        self.assertIn("about 8 now, up 4 places from the 4 weeks before", page)

    def test_s4_thin_weeks_are_hollow_and_claim_nothing(self):
        g = self.google(keys={"a": weekly_key([12] * 13, impressions=4)})
        page, _ = self.build(g, keywords="a")
        self.assertIn("too little data to tell a move", page)
        self.assertIn('class="hollow"', page)
        self.assertIn("Your key search had too little data to tell", page)

    def test_s5_the_country_filter_goes_into_every_google_request(self):
        """Mixing filtered and unfiltered numbers on one page would compare different markets."""
        g = self.google(keys={"a": weekly_key([9] * 13)})
        page, _ = self.build(g, keywords="a", country="DEU")
        data_calls = [b for _, b in g.calls if b.get("dimensions")]
        self.assertTrue(data_calls)
        for b in data_calls:
            f = [x for grp in b.get("dimensionFilterGroups", []) for x in grp["filters"] if x["dimension"] == "country"]
            self.assertEqual([x["expression"] for x in f], ["deu"], b)
        self.assertIn("searches from Germany", page)

    def test_one_request_per_key_search_lowercased(self):
        """Two key searches in one request return nothing (probe); Google stores queries lowercase."""
        g = self.google(keys={"a b": weekly_key([9] * 13), "c": weekly_key([9] * 13)})
        self.build(g, keywords="A B,c")
        qcalls = [b for _, b in g.calls if b.get("dimensions") == ["date", "query"]]
        self.assertEqual(sorted(f["expression"] for b in qcalls for grp in b["dimensionFilterGroups"]
                                for f in grp["filters"] if f["dimension"] == "query"), ["a b", "c"])

    def test_s6_just_below_page_1_is_above_10_up_to_20(self):
        queries = [{"keys": ["on page one"], "position": 9.9, "impressions": 50},
                   {"keys": ["just below"], "position": 10.4, "impressions": 50},
                   {"keys": ["page two end"], "position": 20.0, "impressions": 50},
                   {"keys": ["too far"], "position": 20.5, "impressions": 50},
                   {"keys": ["too rare"], "position": 12.0, "impressions": 4}]
        drill = {"just below": [{"keys": ["/a"], "impressions": 5}, {"keys": ["/b"], "impressions": 30}]}
        page, _ = self.build(self.google(queries=queries, drill=drill))
        self.assertIn("just below", page)
        self.assertIn("page two end", page)
        for gone in ("on page one", "too far", "too rare"):
            self.assertNotIn(gone, page)
        self.assertIn("/b (+1 more)", page)                   # the page Google shows most

    def test_s6_a_failed_drill_down_does_not_block_the_refresh(self):
        """One bad drill-down must not freeze the saved data forever (round 6's RISK)."""
        queries = [{"keys": ["just below"], "position": 12, "impressions": 50}]
        fail = lambda b: b.get("dimensions") == ["page"] and b.get("dimensionFilterGroups")
        page, _ = self.build(self.google(queries=queries, fail=fail))
        self.assertIn("page unknown", page)
        self.assertIsNotNone(self.cache())
        self.assertNotIn("could not be refreshed", page)

    def test_s7_shown_often_rarely_clicked_uses_the_text_report_rule(self):
        pages = [{"keys": ["/cakes/"], "position": 6, "impressions": 900, "clicks": 3, "ctr": 3 / 900},
                 {"keys": ["/fine/"], "position": 6, "impressions": 900, "clicks": 90, "ctr": 0.1},
                 {"keys": ["/deep/"], "position": 14, "impressions": 900, "clicks": 1, "ctr": 1 / 900},
                 {"keys": ["/rare/"], "position": 3, "impressions": 19, "clicks": 0, "ctr": 0}]
        page, _ = self.build(self.google(pages=pages))
        self.assertIn("/cakes/", page)
        for gone in ("/fine/", "/deep/", "/rare/"):
            self.assertNotIn(gone, page)
        self.assertIn("first check how the page appears", page)

    def test_s8_bing_lines_break_on_a_new_variant_and_claim_no_move(self):
        self.history([
            {"date": "2026-08-31", "site": DOMAIN, "source": "bing", "keyword": "k", "query": "k", "position": 12, "impressions": 40, "window": "~180"},
            {"date": "2026-09-07", "site": DOMAIN, "source": "bing", "keyword": "k", "query": "k", "position": 11, "impressions": 40, "window": "~180"},
            {"date": "2026-09-14", "site": DOMAIN, "source": "bing", "keyword": "k", "query": "best k", "position": 3, "impressions": 60, "window": "~180"},
        ])
        page, _ = self.build(self.google(), keywords="k")
        self.assertIn("latest position about 3", page)
        self.assertIn(">≠<", page)
        self.assertIn("Bing matched: k, best k", page)
        self.assertNotIn("moved up", page.split("<h2>Bing</h2>")[1])

    def test_s8_bing_shows_only_the_current_key_searches(self):
        """Found in the live run: old one-off keywords in the history must not come back as cards."""
        self.history([
            {"date": "2026-09-14", "site": DOMAIN, "source": "bing", "keyword": "Current", "query": "current", "position": 5, "impressions": 40, "window": "~180"},
            {"date": "2026-09-14", "site": DOMAIN, "source": "bing", "keyword": "old one-off", "query": "old one-off", "position": 7, "impressions": 40, "window": "~180"},
        ])
        page, _ = self.build(self.google(keys={"current": weekly_key([9] * 13)}), keywords="current")
        bing = page.split("<h2>Bing</h2>")[1]
        self.assertIn("“Current”", bing)
        self.assertNotIn("old one-off", bing)

    def test_bing_follows_todays_key_searches_even_from_saved_google_data(self):
        """Review round 2: after a failed refresh, Bing must not bring back the old key searches."""
        self.history([
            {"date": "2026-09-14", "site": DOMAIN, "source": "bing", "keyword": "old", "query": "old", "position": 5, "impressions": 40, "window": "~180"},
            {"date": "2026-09-14", "site": DOMAIN, "source": "bing", "keyword": "current", "query": "current", "position": 7, "impressions": 40, "window": "~180"},
        ])
        self.build(self.google(), keywords="old")
        def expired():
            raise sr.SignInError("expired")
        page, _ = self.build(expired, keywords="current")
        bing = page.split("<h2>Bing</h2>")[1]
        self.assertIn("“current”", bing)
        self.assertNotIn("“old”", bing)

    def test_bing_with_no_rows_for_todays_searches_is_never_an_empty_section(self):
        """Review round 2: history for other keywords only must still say something."""
        self.site_file(bing=True)
        self.history([{"date": "2026-09-14", "site": DOMAIN, "source": "bing", "keyword": "other", "query": "other", "position": 5, "impressions": 40, "window": "~180"}])
        page, _ = self.build(self.google(), keywords="mine")
        self.assertIn("fills in after the next weekly check", page)

    def test_the_sites_own_pages_show_as_paths(self):
        """Found in the live run: owners read /cakes/ more easily than a full address."""
        pages = [{"keys": [f"https://www.{DOMAIN}/cakes/"], "position": 6, "impressions": 900, "clicks": 3, "ctr": 0.003},
                 {"keys": ["https://other.example/x"], "position": 6, "impressions": 800, "clicks": 1, "ctr": 0.001}]
        page, _ = self.build(self.google(pages=pages))
        self.assertIn("<td>/cakes/</td>", page)
        self.assertEqual(sr.show_page(f"https://{DOMAIN}?x=1", DOMAIN), "/?x=1")      # review round 2
        self.assertEqual(sr.show_page(f"https://{DOMAIN}", DOMAIN), "/")
        self.assertIn("other.example/x", page)                  # not the site's own: kept in full

    def site_file(self, **kw):
        sites = self.home / ".config/gsc-insights/sites"
        sites.mkdir(exist_ok=True)
        (sites / f"{DOMAIN}.json").write_text(json.dumps({"keywords": [], "country": "", "csv": "", **kw}))

    def test_s8_bing_waits_when_the_weekly_run_recorded_a_key(self):
        """Whether Bing is connected is what track.sh resolved (review round 5: reading .env as
        text called BING_API_KEY=${MISSING:-} "set")."""
        self.site_file(bing=True)
        page, _ = self.build(self.google())
        self.assertIn("fills in after the next weekly check", page)
        self.site_file(bing=False)
        page, _ = self.build(self.google())
        self.assertIn("Bing is not connected yet", page)

    def test_s8_bing_waits_when_connected_but_not_run(self):
        self.site_file(bing=True)
        page, _ = self.build(self.google())
        self.assertIn("fills in after the next weekly check", page)

    def test_bing_falls_back_to_a_differing_row_and_marks_it(self):
        """A date without the latest configuration keeps a point and a ‡ break (round 6's BUG)."""
        rows = [{"date": "2026-09-01", "source": "bing", "keyword": "k", "query": "k", "position": "9", "impressions": "5", "window": "", "country": ""},
                {"date": "2026-09-08", "source": "bing", "keyword": "k", "query": "k", "position": "8", "impressions": "5", "window": "~180", "country": ""}]
        pts = sr.bing_lines(rows)["k"]
        self.assertEqual([p["position"] for p in pts], [9.0, 8.0])
        self.assertEqual(pts[1]["break"], "‡")

    def test_s9_expired_sign_in_uses_saved_data_with_its_own_date(self):
        self.build(self.google(keys={"a": weekly_key([9] * 13)}), keywords="a")
        def expired():
            raise sr.SignInError("token expired")
        page, _ = self.build(expired, keywords="b")
        self.assertIn("could not be refreshed; these are from 2026-09-27. Say “reconnect Google”", page)
        self.assertIn("“a”", page)                        # shown with the settings it was fetched with
        self.assertNotIn("“b”", page)

    def test_s9_no_saved_data_says_could_not_be_loaded(self):
        def expired():
            raise sr.SignInError("token expired")
        page, _ = self.build(expired)
        self.assertIn("could not be loaded. Say “reconnect Google”", page)
        self.assertNotIn("<svg", page)

    def test_s9_other_failures_never_say_reconnect_and_keep_the_old_data(self):
        """A quota error is not a sign-in problem; a failed REQUIRED request keeps the saved file."""
        self.build(self.google(), keywords="")
        before = self.cache()
        fail = lambda b: b.get("dimensions") == ["query"]
        page, _ = self.build(self.google(fail=fail))
        self.assertIn("could not be refreshed (Quota exceeded)", page)
        self.assertNotIn("reconnect", page)
        self.assertEqual(self.cache(), before)

    def test_s9_a_copy_that_cannot_be_saved_never_replaces_fresh_numbers(self):
        """Second-model review: a failed save was handled as a failed fetch, so the page showed
        the older saved numbers under "could not be refreshed" although Google had answered."""
        self.build(self.google(keys={"a": weekly_key([9] * 13)}), keywords="a")
        (self.home / ".config/gsc-insights/reports" / DOMAIN / "google-data.json.tmp").mkdir()
        page, _ = self.build(self.google(keys={"b": weekly_key([9] * 13)}), keywords="b")
        self.assertIn("“b”", page)
        self.assertNotIn("“a”", page)
        self.assertNotIn("could not be refreshed", page)
        self.assertIn("could not be saved on this computer", page)

    def test_s9_saved_numbers_name_where_their_key_searches_came_from(self):
        """Second-model review: saved key searches were labelled with today's source."""
        self.build(self.google(keys={"a": weekly_key([9] * 13)}), keywords="a")
        sites = self.home / ".config/gsc-insights/sites"
        sites.mkdir()
        (sites / f"{DOMAIN}.json").write_text(json.dumps({"keywords": ["b"], "country": "", "csv": "", "recorded": "2026-09-21"}))
        def expired():
            raise sr.SignInError("token expired")
        page, _ = self.build(expired)
        self.assertIn("“a”", page)
        self.assertIn("key searches from your request", page)
        self.assertNotIn("key searches from your weekly check", page)
        # A file saved before 0.29 carries no source: today's is named only for the same key searches.
        saved = self.cache(); del saved["from"]
        (self.home / ".config/gsc-insights/reports" / DOMAIN / "google-data.json").write_text(json.dumps(saved))
        page, _ = self.build(expired)
        self.assertIn("“a”", page)
        self.assertNotIn("key searches from", page)

    def test_the_property_is_asked_for_as_the_bare_lowercase_domain(self):
        """Second-model review: "Example-Bakery.DE" as typed became sc-domain:Example-Bakery.DE."""
        for typed in ("Example-Bakery.DE", "sc-domain:example-bakery.de"):
            g = self.google(keys={"a": weekly_key([9] * 13)})
            self.build(g, domain=typed, keywords="a")
            self.assertEqual({site for site, _ in g.calls}, {"sc-domain:example-bakery.de"}, typed)

    def test_s6_s7_ask_for_the_last_four_complete_weeks(self):
        """Second-model review: the fake answered any dates, so a wrong window would pass."""
        g = self.google()
        self.build(g, keywords="")
        four = [(b["startDate"], b["endDate"]) for _, b in g.calls if b.get("dimensions") in (["query"], ["page"])]
        self.assertTrue(four)
        self.assertEqual(set(four), {(d(LAST_SUNDAY - dt.timedelta(days=27)), d(LAST_SUNDAY))})

    def test_a_hand_edited_record_never_crashes_the_page(self):
        """Second-model review: a string of key searches was read letter by letter."""
        sites = self.home / ".config/gsc-insights/sites"
        sites.mkdir()
        rec = sites / f"{DOMAIN}.json"
        rec.write_text(json.dumps({"keywords": "sourdough, rye", "country": "", "csv": "", "recorded": "2026-09-21"}))
        page, _ = self.build(self.google(keys={"sourdough": weekly_key([9] * 13), "rye": weekly_key([9] * 13)}))
        self.assertIn("“sourdough”", page)
        self.assertIn("“rye”", page)
        self.assertNotIn("“s”", page)
        rec.write_text(json.dumps({"keywords": ["rye", None, 1], "recorded": "2026-09-21"}))
        page, _ = self.build(self.google(keys={"rye": weekly_key([9] * 13)}))
        self.assertIn("“rye”", page)
        self.assertNotIn("“None”", page)
        self.assertNotIn("“1”", page)
        # Fresh-eyes review: other fields of the wrong type crashed it too.
        for bad in ({"keywords": 5}, {"keywords": {"a": 1}}, [1, 2], "text",
                    {"keywords": ["a"], "country": 5}, {"keywords": ["a"], "csv": 5}):
            rec.write_text(json.dumps(bad))
            self.build(self.google())                     # a page, never a crash

    def test_s10_brand_new_site_shows_no_empty_charts(self):
        page, _ = self.build(FakeGoogle(daily={}))
        self.assertIn("Google needs a few days to report on a new site", page)
        self.assertNotIn("<svg", page)

    def test_s11_no_data_card_names_a_past_variant_without_claiming_it_now(self):
        self.history([{"date": "2026-09-12", "site": DOMAIN, "source": "gsc", "keyword": "ai treffen",
                       "query": "ai treffen münchen", "position": 8, "impressions": 30, "window": "28"}])
        page, _ = self.build(self.google(), keywords="ai treffen")
        self.assertIn("No data from Google for this search in the last 3 months.", page)
        self.assertIn("Your check on 2026-09-12 matched “ai treffen münchen”", page)
        self.assertNotIn("shows you", page)

    def test_s12_no_key_searches_known(self):
        page, _ = self.build(self.google())
        self.assertIn("Tell me the searches that matter to you", page)
        self.assertIn("Visits from Google, per week", page)

    def test_s13_each_site_has_its_own_page(self):
        self.build(self.google(), domain="one.example")
        self.build(self.google(), domain="two.example")
        base = self.home / ".config/gsc-insights/reports"
        self.assertTrue((base / "one.example/google.html").exists())
        self.assertTrue((base / "two.example/google.html").exists())

    def test_s14_one_private_file_with_numbers_as_text(self):
        """No outside script, font or tracker; every chart has a "See the numbers" table."""
        page, _ = self.build(self.google(keys={"a": weekly_key([9] * 13)}), keywords="a")
        self.assertNotIn("<script", page)
        self.assertNotIn("http://", page)
        self.assertNotIn("https://", page)
        self.assertEqual(page.count("<svg class=\"wide\""), page.count("<svg class=\"narrow\""))
        self.assertGreaterEqual(page.count("See the numbers"), 3)

    def test_url_prefix_fallback_is_named_on_the_page(self):
        g = self.google(refuse_domain=True, sites=[{"siteUrl": f"https://{DOMAIN}/"}])
        page, _ = self.build(g)
        self.assertIn(f"only the address https://{DOMAIN}/", page)


class Settings(ReportTest):
    def test_s16_an_older_job_before_its_first_new_run_uses_the_history(self):
        """Until the weekly job has recorded its settings, the history's own rows decide — with
        the country each check actually used, so a Germany-only job still counts Germany."""
        self.history([{"date": "2026-09-14", "site": DOMAIN, "source": "gsc", "keyword": k,
                       "position": 9, "impressions": 20, "window": "28", "country": "deu"} for k in ("k1", "k2")])
        s, _ = sr.resolve_settings(DOMAIN, args())
        self.assertEqual((s["keywords"], s["country"]), (["k1", "k2"], "deu"))
        self.assertIn("your last check on 2026-09-14", s["from"])

    def test_an_old_weekly_record_is_named_on_the_page(self):
        """Review round 6: a record the weekly check stopped updating must not pass silently."""
        sites = self.home / ".config/gsc-insights/sites"
        sites.mkdir()
        (sites / f"{DOMAIN}.json").write_text(json.dumps({"keywords": ["k"], "country": "", "csv": "", "recorded": "2026-08-01"}))
        page, _ = sr.build(DOMAIN, args(), service_factory=lambda: FakeGoogle(daily=daily_series(60)), today=TODAY).read_text(), None
        self.assertIn("last recorded this site's settings on 2026-08-01", page)
        self.assertIn("key searches from your weekly check on 2026-08-01", page)
        (sites / f"{DOMAIN}.json").write_text(json.dumps({"keywords": ["k"], "country": "", "csv": "", "recorded": "2026-09-21"}))
        page = sr.build(DOMAIN, args(), service_factory=lambda: FakeGoogle(daily=daily_series(60)), today=TODAY).read_text()
        self.assertNotIn("last recorded this site's settings", page)
        # Review round 7: an undated record, and a stale one used with --keywords, are named too.
        (sites / f"{DOMAIN}.json").write_text(json.dumps({"keywords": ["k"], "country": "deu", "csv": ""}))
        page = sr.build(DOMAIN, args(), service_factory=lambda: FakeGoogle(daily=daily_series(60)), today=TODAY).read_text()
        self.assertIn("last recorded this site's settings without a date", page)
        for bad in (20260801, True, ["2026-08-01"], {"d": 1}):      # review round 8: never a crash
            (sites / f"{DOMAIN}.json").write_text(json.dumps({"keywords": ["k"], "country": "", "csv": "", "recorded": bad}))
            page = sr.build(DOMAIN, args(), service_factory=lambda: FakeGoogle(daily=daily_series(60)), today=TODAY).read_text()
            self.assertIn("without a date", page)
        (sites / f"{DOMAIN}.json").write_text(json.dumps({"keywords": ["k"], "country": "deu", "csv": "", "recorded": "2026-08-01"}))
        page = sr.build(DOMAIN, args(keywords="new"), service_factory=lambda: FakeGoogle(daily=daily_series(60)), today=TODAY).read_text()
        self.assertIn("last recorded this site's settings on 2026-08-01", page)

    def test_an_empty_history_setting_means_the_shared_default_file(self):
        """An explicitly empty value is "none", never one inherited from the environment."""
        sites = self.home / ".config/gsc-insights/sites"
        sites.mkdir()
        (sites / f"{DOMAIN}.json").write_text(json.dumps({"keywords": ["k"], "country": "", "csv": ""}))
        os.environ["GSC_HISTORY_CSV"] = "/tmp/inherited-other.csv"
        s, _ = sr.resolve_settings(DOMAIN, args())
        self.assertEqual(s["csv"], str(self.home / ".config/gsc-insights/history.csv"))

    def test_only_the_shown_searches_get_a_page_drill_down(self):
        """100 candidates must not mean 100 extra requests for 15 shown rows (review round 1)."""
        queries = [{"keys": [f"q{i}"], "position": 12, "impressions": 100 + i} for i in range(100)]
        g = Scenarios.google(self, queries=queries)
        self.build(g)
        drills = [b for _, b in g.calls if b.get("dimensions") == ["page"] and b.get("dimensionFilterGroups")]
        self.assertEqual(len(drills), sr.S6_SHOWN)
        self.assertIn("q99", {f["expression"] for b in drills for grp in b["dimensionFilterGroups"] for f in grp["filters"]})

    def test_precedence_flags_then_site_file_then_history(self):
        sites = self.home / ".config/gsc-insights/sites"
        sites.mkdir()
        (sites / f"{DOMAIN}.json").write_text(json.dumps({"keywords": ["from-file"], "country": "che", "csv": ""}))
        s, _ = sr.resolve_settings(DOMAIN, args())
        self.assertEqual((s["keywords"], s["country"]), (["from-file"], "che"))
        s, _ = sr.resolve_settings(DOMAIN, args(keywords="from-flag", country=""))
        self.assertEqual((s["keywords"], s["country"]), (["from-flag"], ""))

    def test_history_fallback_takes_one_group_deterministically(self):
        """A same-day ad-hoc run must not mix its keywords or country into the tracker's."""
        rows = [{"date": "2026-09-14", "source": "gsc", "keyword": k, "window": w, "country": c}
                for k, w, c in [("a", "28", "deu"), ("b", "28", "deu"), ("x", "90", "che"),
                                ("y", "90", "che"), ("z", "90", "che"), ("old", "28", "deu")]]
        rows[-1]["date"] = "2026-09-01"
        self.assertEqual(sr.history_settings(rows)["keywords"], ["a", "b"])
        tied = [{"date": "2026-09-14", "source": "gsc", "keyword": k, "window": w, "country": ""}
                for k, w in [("p", "90", ), ("q", "7")]]
        self.assertEqual(sr.history_settings(tied)["keywords"], ["q"])     # the shorter window


if __name__ == "__main__":
    unittest.main()
