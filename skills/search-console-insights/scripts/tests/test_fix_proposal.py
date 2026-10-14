"""fix_proposal.py — choosing the weekly fix proposal, and following it.

Why: the owner acts on what this code proposes, and reads what it measures. A proposal for a
search that is already on the page wastes their time; one re-shown before their "no" has run its
12 weeks ignores them; a before-window that holds days of the new page credits the change with
numbers from after it. Each test pins one rule of docs/reviews/SKILL-PLAN-scheduled-search-fixes.md
(R1, R3, scenarios 1, 2, 4, 6, 8) or docs/reviews/DESIGN-weekly-fix-proposal.md (§3.2 to §3.4),
with the scenarios' own figures and dates. The command line is run as the owner's assistant runs
it, through a real subprocess, with HOME pointed at a temporary folder and a stub `gh`.

Run:  python3 -m unittest discover -s skills/search-console-insights/scripts/tests
"""
import copy
import datetime as dt
import fcntl
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import fix_proposal as fp  # noqa: E402

SCRIPT = os.path.join(HERE, "..", "fix_proposal.py")
SITE = "radwerk-plagwitz.example"
PAGE = "https://radwerk-plagwitz.example/reparatur"
QUERY = "fahrrad reparatur leipzig"
SPELLINGS = fp.default_brand(SITE)
NEW_TITLE = "Fahrradreparatur in Leipzig-Plagwitz | Radwerk Plagwitz"
OLD_TITLE = "Reparatur und Service | Radwerk Plagwitz"
D = dt.date.fromisoformat


def q(text, imp, pos, clicks=0):
    return {"keys": [text], "impressions": imp, "position": pos, "clicks": clicks}


def qp(text, page, imp):
    return {"keys": [text, page], "impressions": imp}


def page(title=OLD_TITLE, h1="Reparatur und Service", p="Wir reparieren Räder aller Art."):
    return {"title": title, "h1": h1, "first_paragraph": p}


SCENARIO1_QUERIES = [q(QUERY, 286, 11.6, 2), q("radwerk plagwitz", 900, 1.2, 80)]
SCENARIO1_PAGES = [qp(QUERY, PAGE, 271), qp(QUERY, "https://radwerk-plagwitz.example/", 15)]


class BrandTests(unittest.TestCase):
    def test_the_guess_comes_from_the_domain_with_and_without_the_hyphen(self):
        self.assertEqual(SPELLINGS, ["radwerk plagwitz", "radwerkplagwitz"])

    def test_brand_searches_match_in_every_spelling_people_type(self):
        for query in ("radwerk plagwitz", "radwerk-plagwitz öffnungszeiten", "radwerkplagwitz leipzig"):
            self.assertTrue(fp.is_brand(query, SPELLINGS), query)
        self.assertFalse(fp.is_brand(QUERY, SPELLINGS))

    def test_a_short_name_run_together_does_not_match_inside_other_words(self):
        # "ab" run together would match "fahrrad laborbedarf"; under 6 letters only whole words count.
        self.assertFalse(fp.is_brand("labor bedarf", ["ab"]))
        self.assertTrue(fp.is_brand("ab werkstatt", ["ab"]))

    def test_confirmed_spellings_replace_the_guess(self):
        st = fp.empty_state(SITE)
        self.assertEqual(fp.brand_spellings(st, SITE), (SPELLINGS, False))
        st["brand"] = ["radwerk"]
        self.assertEqual(fp.brand_spellings(st, SITE), (["radwerk"], True))


class CandidateTests(unittest.TestCase):
    def test_scenario_1_the_search_and_its_proved_page(self):
        cands = fp.t1_candidates(SCENARIO1_QUERIES, SCENARIO1_PAGES, SPELLINGS)
        self.assertEqual(len(cands), 1)          # the brand search is out, though stronger
        c = cands[0]
        self.assertEqual((c["query"], c["page"], c["impressions"], c["page_impressions"]),
                         (QUERY, PAGE, 286, 271))

    def test_a_business_name_search_is_never_proposed_even_in_striking_distance(self):
        # Searching for the business by name says nothing about SEO progress (SKILL.md rule 3),
        # however many impressions it has.
        rows = [q("radwerk plagwitz öffnungszeiten", 500, 9.0), q(QUERY, 286, 11.6)]
        pages = [qp("radwerk plagwitz öffnungszeiten", PAGE, 500), qp(QUERY, PAGE, 271)]
        self.assertEqual([c["query"] for c in fp.t1_candidates(rows, pages, SPELLINGS)], [QUERY])

    def test_the_floor_and_both_ends_of_striking_distance(self):
        rows = [q("a b", 50, 8.0), q("c d", 50, 20.0), q("e f", 49, 12.0),
                q("g h", 400, 7.9), q("i j", 400, 20.1)]
        pages = [qp(r["keys"][0], PAGE, 10) for r in rows]
        got = [c["query"] for c in fp.t1_candidates(rows, pages, SPELLINGS)]
        self.assertEqual(sorted(got), ["a b", "c d"])

    def test_a_page_under_the_noise_floor_is_never_proposed(self):
        # R1: 50 impressions for the search, but only 7 of them on its best page.
        rows = [q("a b", 60, 12.0)]
        self.assertEqual(fp.t1_candidates(rows, [qp("a b", PAGE, 7)], SPELLINGS), [])
        self.assertEqual(len(fp.t1_candidates(rows, [qp("a b", PAGE, 10)], SPELLINGS)), 1)
        # The floor is the page's own non-brand total, over all its searches (round 2), and
        # searches for the business by name do not lift a page over it.
        self.assertEqual(len(fp.t1_candidates(rows, [qp("a b", PAGE, 7), qp("c d", PAGE, 100)], SPELLINGS)), 1)
        self.assertEqual(fp.t1_candidates(rows, [qp("a b", PAGE, 7), qp("radwerk plagwitz", PAGE, 100)], SPELLINGS), [])

    def test_a_search_with_no_proved_page_is_never_guessed(self):
        self.assertEqual(fp.t1_candidates([q("a b", 300, 12.0)], [], SPELLINGS), [])

    def test_strongest_first(self):
        rows = [q("small one", 60, 12.0), q("big one", 300, 12.0)]
        pages = [qp("small one", PAGE, 60), qp("big one", PAGE, 300)]
        self.assertEqual([c["query"] for c in fp.t1_candidates(rows, pages, SPELLINGS)],
                         ["big one", "small one"])


class PageTests(unittest.TestCase):
    def test_the_first_paragraph_in_main_wins_over_a_cookie_note(self):
        html = ("<html><head><title> Reparatur &amp; Service </title></head><body>"
                "<p>We use cookies.</p><main><h1>Reparatur</h1><p></p>"
                "<p>Wir <b>reparieren</b> Räder.</p></main></body></html>")
        self.assertEqual(fp.parse_page(html), {"title": "Reparatur & Service", "h1": "Reparatur",
                                               "first_paragraph": "Wir reparieren Räder."})

    def test_short_words_count_and_umlauts_fold(self):
        on = page(title="KI-Events in München", h1="", p="")
        self.assertTrue(fp.query_on_page("ki events muenchen", on))
        # "ki" is not inside "kino": whole words only, so this page still needs the edit.
        self.assertFalse(fp.query_on_page("ki events muenchen", page(title="Kino-Events in München")))

    def test_the_three_places_count_together(self):
        self.assertTrue(fp.query_on_page(QUERY, page(title="Fahrrad", h1="Reparatur", p="in Leipzig")))
        self.assertFalse(fp.query_on_page(QUERY, page()))

    def test_a_german_compound_carries_the_words_written_apart(self):
        # The owner's new title says "Fahrradreparatur"; the search was "fahrrad reparatur leipzig".
        done = page(title="Fahrradreparatur in Leipzig-Plagwitz", h1="", p="")
        self.assertTrue(fp.query_on_page(QUERY, done))
        # A compound with something else in it does not count: "fahrradladen" is not "fahrrad reparatur".
        self.assertFalse(fp.query_on_page(QUERY, page(title="Fahrradladen in Leipzig", h1="", p="")))

    def test_a_compound_still_counts_when_one_of_its_words_also_stands_alone(self):
        # Round 1: greedy matching used up "fahrrad" and missed "Fahrradreparatur".
        self.assertTrue(fp.query_on_page(QUERY, page(title="Fahrrad und Fahrradreparatur in Leipzig", h1="", p="")))

    def test_a_search_of_stop_words_only_is_never_already_on_the_page(self):
        self.assertFalse(fp.query_on_page("in der", page(title="in der")))


class ChooseTests(unittest.TestCase):
    def setUp(self):
        self.cands = fp.t1_candidates(SCENARIO1_QUERIES, SCENARIO1_PAGES, SPELLINGS)
        self.state = fp.empty_state(SITE)

    def test_scenario_1_proposes_and_keeps_the_old_title(self):
        prop, notes = fp.choose(self.cands, self.state, D("2026-11-02"), lambda url: page())
        self.assertEqual((prop["query"], prop["old_title"]), (QUERY, OLD_TITLE))
        self.assertEqual(notes, [])
        self.assertEqual(fp.sentence(prop), "/search-console-insights work 'fahrrad reparatur leipzig' "
                         "into the title, heading and first paragraph of " + PAGE)

    def test_scenario_2_no_candidate_no_proposal(self):
        rows = [q("tonstube kassel", 41, 1.0)] + [q(f"ton {i}", 3, 14.0) for i in range(9)]
        cands = fp.t1_candidates(rows, [qp(r["keys"][0], PAGE, 3) for r in rows],
                                 fp.default_brand("tonstube-kassel.example"))
        self.assertEqual(fp.choose(cands, self.state, D("2026-11-02"), lambda url: page()), (None, []))

    def test_already_on_the_page_moves_on_to_the_next(self):
        rows = SCENARIO1_QUERIES + [q("fahrrad service", 120, 13.0)]
        pages = SCENARIO1_PAGES + [qp("fahrrad service", PAGE + "-service", 120)]
        cands = fp.t1_candidates(rows, pages, SPELLINGS)
        reads = {PAGE: page(title="Fahrrad Reparatur Leipzig"), PAGE + "-service": page()}
        prop, notes = fp.choose(cands, self.state, D("2026-11-02"), reads.get)
        self.assertEqual(prop["query"], "fahrrad service")
        self.assertEqual(notes, [(QUERY, "already on the page")])

    def test_an_unreadable_page_is_passed_over_and_named(self):
        prop, notes = fp.choose(self.cands, self.state, D("2026-11-02"), lambda url: None)
        self.assertIsNone(prop)
        self.assertEqual(notes, [(QUERY, "the page could not be read")])

    def test_scenario_6_a_no_holds_for_exactly_12_weeks(self):
        rec = fp.record_shown(self.state, dict(self.cands[0], old_title=OLD_TITLE),
                              (D("2026-09-28"), D("2026-10-25")), D("2026-11-02"))
        rec["declined_on"], rec["decline_reason"] = "2026-11-02", "owner"
        _, notes = fp.choose(self.cands, self.state, D("2027-01-24"), lambda url: page())
        self.assertEqual(notes, [(QUERY, "turned down until 2027-01-25")])
        prop, _ = fp.choose(self.cands, self.state, D("2027-01-25"), lambda url: page())
        self.assertEqual(prop["query"], QUERY)

    def test_a_finished_round_keeps_its_record_when_the_search_comes_back(self):
        rec = fp.record_shown(self.state, dict(self.cands[0], old_title=OLD_TITLE),
                              (D("2026-09-28"), D("2026-10-25")), D("2026-11-02"))
        rec["pr"] = {"url": "u", "repo": "o/r", "number": 31, "state": "MERGED"}
        rec["result"] = {"weeks": 4}
        again = fp.record_shown(self.state, dict(self.cands[0], old_title=NEW_TITLE),
                                (D("2027-02-01"), D("2027-02-28")), D("2027-03-08"))
        self.assertEqual((again["shown"], "pr" in again), ("2027-03-08", False))
        self.assertEqual([r["result"] for r in self.state["done"]], [{"weeks": 4}])

    def test_a_search_turned_down_in_words_starts_fresh_when_it_comes_back(self):
        rec = fp.record_shown(self.state, dict(self.cands[0], old_title=OLD_TITLE),
                              (D("2026-09-28"), D("2026-10-25")), D("2026-11-02"))
        rec["declined_on"], rec["decline_reason"] = "2026-11-02", "owner"
        again = fp.record_shown(self.state, dict(self.cands[0], old_title=OLD_TITLE),
                                (D("2027-01-04"), D("2027-01-31")), D("2027-02-08"))
        self.assertEqual(again["shown"], "2027-02-08")
        self.assertNotIn("declined_on", again)
        self.assertEqual(self.state["done"][0]["declined_on"], "2026-11-02")

    def test_an_open_or_unchecked_pull_request_keeps_the_whole_page_out(self):
        rec = fp.record_shown(self.state, dict(self.cands[0], old_title=OLD_TITLE),
                              (D("2026-09-28"), D("2026-10-25")), D("2026-11-02"))
        rec["pr"] = {"url": "https://github.com/o/r/pull/31", "repo": "o/r", "number": 31, "state": None}
        other = dict(self.cands[0], query="fahrrad werkstatt leipzig")
        _, notes = fp.choose([other], self.state, D("2027-06-01"), lambda url: page())
        self.assertEqual(notes, [("fahrrad werkstatt leipzig", "pull request open")])


class PullRequestTests(unittest.TestCase):
    def rec(self):
        return {"page": PAGE, "query": QUERY, "pr": {"url": "u", "repo": "o/r", "number": 31, "state": None}}

    def test_closed_counts_as_no_from_the_day_github_closed_it(self):
        r = fp.apply_pr_state(self.rec(), {"state": "CLOSED", "closedAt": "2026-11-05T14:02:00Z", "mergedAt": None})
        self.assertEqual((r["declined_on"], r["decline_reason"]), ("2026-11-05", "closed"))
        self.assertEqual(fp.declined_until(r), D("2027-01-28"))
        self.assertEqual(fp.page_block(r), "")       # the page is free; only this search is turned down

    def test_reopened_takes_the_no_back(self):
        r = fp.apply_pr_state(self.rec(), {"state": "CLOSED", "closedAt": "2026-11-05T14:02:00Z"})
        r = fp.apply_pr_state(r, {"state": "OPEN", "closedAt": None})
        self.assertNotIn("declined_on", r)
        self.assertEqual(fp.page_block(r), "pull request open")

    def test_merged_waits_to_be_seen_live_and_no_answer_changes_nothing(self):
        r = fp.apply_pr_state(self.rec(), {"state": "MERGED", "mergedAt": "2026-11-03T10:00:00Z"})
        self.assertEqual(fp.page_block(r), "merged, not seen live yet")
        before = copy.deepcopy(r)
        after = fp.apply_pr_state(r, None)
        # Only the failed check is noted; the last known state stays (a deep copy, so a change
        # made in place would show).
        self.assertIs(after["pr"].pop("last_check_ok"), False)
        before["pr"].pop("last_check_ok", None)
        self.assertEqual(after, before)
        r["checks"] = [{"date": "2026-11-02", "outcome": "old"}, {"date": "2026-11-09", "outcome": "new"}]
        self.assertEqual(fp.page_block(r), "measuring")
        r["result"] = {"done": True}
        self.assertEqual(fp.page_block(r), "")

    def test_merged_after_a_close_takes_the_no_back_and_a_close_without_a_day_counts_today(self):
        r = fp.apply_pr_state(self.rec(), {"state": "CLOSED", "closedAt": "2026-11-05T14:02:00Z"})
        r = fp.apply_pr_state(r, {"state": "MERGED", "mergedAt": "2026-11-06T09:00:00Z"})
        self.assertNotIn("declined_on", r)
        self.assertEqual(fp.page_block(r), "merged, not seen live yet")
        r = fp.apply_pr_state(self.rec(), {"state": "CLOSED", "closedAt": None}, D("2026-11-09"))
        self.assertEqual(r["declined_on"], "2026-11-09")

    def test_an_open_pull_request_keeps_the_page_out_even_after_a_result(self):
        r = self.rec()
        r["pr"]["state"], r["result"] = "OPEN", {"weeks": 4}
        self.assertEqual(fp.page_block(r), "pull request open")

    def test_only_github_pull_request_addresses_are_taken(self):
        self.assertEqual(fp.parse_pr_url("https://github.com/example-owner/site/pull/31"), ("example-owner/site", 31))
        for bad in ("https://gitlab.com/a/b/-/merge_requests/3", "github.com/a/b/pull/3", "#31"):
            with self.assertRaises(ValueError):
                fp.parse_pr_url(bad)


class LiveTests(unittest.TestCase):
    def test_whole_titles_folded_and_four_outcomes(self):
        self.assertEqual(fp.classify_title("  fahrradreparatur in LEIPZIG-Plagwitz |  Radwerk Plagwitz",
                                           OLD_TITLE, NEW_TITLE), "new")
        self.assertEqual(fp.classify_title(OLD_TITLE, OLD_TITLE, NEW_TITLE), "old")
        self.assertEqual(fp.classify_title("Something else", OLD_TITLE, NEW_TITLE), "other")
        self.assertEqual(fp.classify_title(None, OLD_TITLE, NEW_TITLE), "unreadable")

    def test_a_shortened_title_or_a_new_layout_suffix_is_not_live(self):
        old, new = "Bike repair Leipzig | Brand", "Bike repair | Brand"
        self.assertEqual(fp.classify_title("Bike repair Leipzig | Brand", old, new), "old")
        self.assertEqual(fp.classify_title("Bike repair Leipzig | Brand Shop", old, new), "other")


def checks(*pairs):
    return [{"date": d, "outcome": o} for d, o in pairs]


class WindowTests(unittest.TestCase):
    def test_scenario_8_dates(self):
        w = fp.windows(checks(("2026-11-02", "old"), ("2026-11-09", "new"), ("2026-11-16", "new")))
        self.assertEqual(w["before"], (D("2026-10-05"), D("2026-11-01")))
        self.assertEqual(w["after"], (D("2026-11-09"), D("2026-12-06")))
        self.assertEqual((w["weeks"], w["interrupted"]), (4, None))
        self.assertFalse(fp.ready_to_measure(w, D("2026-12-05")))
        self.assertTrue(fp.ready_to_measure(w, D("2026-12-06")))

    def test_scenario_8_a_third_title_on_23_november_cuts_it_to_two_weeks(self):
        w = fp.windows(checks(("2026-11-02", "old"), ("2026-11-09", "new"), ("2026-11-23", "other")))
        self.assertEqual(w["after"], (D("2026-11-09"), D("2026-11-22")))
        self.assertEqual((w["weeks"], w["interrupted"]), (2, "2026-11-23"))

    def test_a_rollback_never_moves_the_before_window_onto_new_days(self):
        w = fp.windows(checks(("2026-11-02", "old"), ("2026-11-09", "new"), ("2026-11-16", "old")))
        self.assertEqual(w["before"], (D("2026-10-05"), D("2026-11-01")))
        self.assertEqual((w["after"], w["weeks"]), ((D("2026-11-09"), D("2026-11-15")), 1))

    def test_changed_again_too_soon_leaves_nothing_to_show(self):
        w = fp.windows(checks(("2026-11-02", "old"), ("2026-11-09", "new"), ("2026-11-12", "other")))
        self.assertEqual((w["after"], w["weeks"]), (None, 0))
        self.assertFalse(fp.ready_to_measure(w, D("2027-01-01")))

    def test_an_old_and_a_new_look_on_the_same_day_both_count(self):
        # Round 1: a second report on the day the change went live overwrote the "old" look.
        w = fp.windows(checks(("2026-11-09", "old"), ("2026-11-09", "new")))
        self.assertEqual(w["before"], (D("2026-10-12"), D("2026-11-08")))   # ends the Sunday before the old look
        self.assertEqual(w["after"][0], D("2026-11-09"))
        self.assertEqual(fp.windows(checks(("2026-11-09", "old"), ("2026-11-09", "new"),
                                           ("2026-11-09", "other")))["weeks"], 0)

    def test_unreadable_and_early_other_checks_change_nothing(self):
        plain = fp.windows(checks(("2026-11-02", "old"), ("2026-11-09", "new")))
        noisy = fp.windows(checks(("2026-11-02", "old"), ("2026-11-05", "unreadable"),
                                  ("2026-11-06", "other"), ("2026-11-09", "new"), ("2026-11-16", "unreadable")))
        self.assertEqual(plain, noisy)

    def test_a_missed_week_only_widens_the_gap(self):
        w = fp.windows(checks(("2026-11-02", "old"), ("2026-11-09", "unreadable"), ("2026-11-16", "new")))
        self.assertEqual(w["before"][1], D("2026-11-01"))
        self.assertEqual(w["after"][0], D("2026-11-16"))

    def test_not_seen_live_yet_means_no_windows(self):
        self.assertIsNone(fp.windows(checks(("2026-11-02", "old"), ("2026-11-09", "old"))))


class GhTests(unittest.TestCase):
    """gh_pr_state through a real subprocess and a stub `gh` on PATH, as the report will call it."""

    def run_with_stub(self, body):
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "gh"
            stub.write_text("#!/bin/sh\n" + body + "\n")
            stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
            old = os.environ["PATH"]
            os.environ["PATH"] = tmp + os.pathsep + old
            try:
                return fp.gh_pr_state("example-owner/site", 31)
            finally:
                os.environ["PATH"] = old

    def test_the_answer_is_read(self):
        got = self.run_with_stub("echo '{\"state\":\"CLOSED\",\"mergedAt\":null,\"closedAt\":\"2026-11-05T14:02:00Z\"}'")
        self.assertEqual(got["state"], "CLOSED")

    def test_a_failure_or_a_strange_answer_is_none(self):
        self.assertIsNone(self.run_with_stub("echo 'not signed in' >&2; exit 4"))
        self.assertIsNone(self.run_with_stub("echo 'garbage'"))
        self.assertIsNone(self.run_with_stub("echo '{\"state\":\"DRAFT\"}'"))

    def test_no_gh_at_all_is_none(self):
        def missing(*a, **k):
            raise FileNotFoundError("gh")
        self.assertIsNone(fp.gh_pr_state("example-owner/site", 31, run=missing))


class CommandLineTests(unittest.TestCase):
    """The commands the owner's assistant runs (design §3.3), through a real subprocess."""

    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        self.env = dict(os.environ, HOME=self.home.name)
        self.path = Path(self.home.name) / ".config" / "gsc-insights" / "sites" / f"{SITE}-proposals.json"

    def run_cli(self, *args):
        return subprocess.run([sys.executable, SCRIPT, *args], env=self.env, capture_output=True, text=True)

    def seed(self):
        old = os.environ.get("HOME")
        os.environ["HOME"] = self.home.name
        try:
            st = fp.load_state(SITE)
            cand = fp.t1_candidates(SCENARIO1_QUERIES, SCENARIO1_PAGES, SPELLINGS)[0]
            fp.record_shown(st, dict(cand, old_title=OLD_TITLE), (D("2026-09-28"), D("2026-10-25")), D("2026-11-02"))
            fp.save_state(SITE, st)
        finally:
            os.environ["HOME"] = old

    def state(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_answers_are_recorded_by_command(self):
        self.assertEqual(self.run_cli("set", SITE, "brand", "radwerk, rad werk").returncode, 0)
        self.assertEqual(self.run_cli("set", SITE, "pr_figures", "no").returncode, 0)
        st = self.state()
        self.assertEqual((st["brand"], st["pr_figures"]), (["radwerk", "rad werk"], "no"))
        self.assertNotEqual(self.run_cli("set", SITE, "pr_figures", "maybe").returncode, 0)
        self.assertEqual(self.state()["pr_figures"], "no")

    def test_show_without_a_proposal(self):
        out = self.run_cli("show", SITE)
        self.assertEqual(out.returncode, 0)
        self.assertIn("Proposal: none", out.stdout)
        self.assertIn("(a guess, not confirmed)", out.stdout)

    def test_acted_records_the_pull_request_and_the_new_title(self):
        self.seed()
        out = self.run_cli("acted", SITE, "--pr", "https://github.com/example-owner/radwerk/pull/31",
                           "--new-title", NEW_TITLE)
        self.assertEqual(out.returncode, 0, out.stderr)
        rec = self.state()["proposals"][fp.proposal_key(PAGE, QUERY)]
        self.assertEqual((rec["pr"]["repo"], rec["pr"]["number"], rec["new_title"]),
                         ("example-owner/radwerk", 31, NEW_TITLE))
        self.assertIn("pull/31", self.run_cli("show", SITE).stdout)

    def test_acted_refuses_a_title_that_could_not_be_told_apart(self):
        self.seed()
        before = self.path.read_text(encoding="utf-8")
        out = self.run_cli("acted", SITE, "--pr", "https://github.com/example-owner/radwerk/pull/31",
                           "--new-title", OLD_TITLE.upper())
        self.assertNotEqual(out.returncode, 0)
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_acted_refuses_an_address_that_is_not_a_pull_request(self):
        self.seed()
        out = self.run_cli("acted", SITE, "--pr", "https://github.com/example-owner/radwerk", "--new-title", NEW_TITLE)
        self.assertNotEqual(out.returncode, 0)
        self.assertNotIn("pr", self.state()["proposals"][fp.proposal_key(PAGE, QUERY)])

    def test_decline_starts_the_12_weeks_today(self):
        self.seed()
        self.assertEqual(self.run_cli("decline", SITE, "--reason", "positioning").returncode, 0)
        rec = self.state()["proposals"][fp.proposal_key(PAGE, QUERY)]
        self.assertEqual((rec["declined_on"], rec["decline_reason"]),
                         (dt.date.today().isoformat(), "positioning"))

    def test_a_damaged_file_is_never_overwritten_with_a_fresh_one(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("[1, 2]", encoding="utf-8")
        out = self.run_cli("set", SITE, "pr_figures", "yes")
        self.assertNotEqual(out.returncode, 0)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "[1, 2]")

    def after_next_report(self):
        """The report after the owner acted: the page is in progress, so there is no current proposal."""
        st = self.state()
        st["current"] = None
        self.path.write_text(json.dumps(st), encoding="utf-8")

    def test_a_later_no_finds_the_proposal_already_acted_on(self):
        # Found by the evals (2026-10-14): once the report ran again, decline said "no proposal".
        self.seed()
        self.run_cli("acted", SITE, "--pr", "https://github.com/example-owner/radwerk/pull/31", "--new-title", NEW_TITLE)
        self.after_next_report()
        out = self.run_cli("decline", SITE)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        rec = self.state()["proposals"][fp.proposal_key(PAGE, QUERY)]
        self.assertEqual(rec["declined_on"], dt.date.today().isoformat())
        self.assertEqual(fp.page_block(rec), "")       # a "no" in words frees the page, like closing it

    def test_a_wrong_recorded_title_can_be_corrected_by_page(self):
        self.seed()
        self.run_cli("acted", SITE, "--pr", "https://github.com/example-owner/radwerk/pull/31",
                     "--new-title", "Fahrradreparatur in Leipzig-Plagwitz | Example")
        self.after_next_report()
        out = self.run_cli("acted", SITE, "--page", PAGE, "--pr", "https://github.com/example-owner/radwerk/pull/31",
                           "--new-title", NEW_TITLE)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(self.state()["proposals"][fp.proposal_key(PAGE, QUERY)]["new_title"], NEW_TITLE)
        out = self.run_cli("decline", SITE, "--page", "https://radwerk-plagwitz.example/kontakt")
        self.assertNotEqual(out.returncode, 0)

    def test_show_names_the_proposal_in_progress_after_the_next_report(self):
        self.seed()
        self.run_cli("acted", SITE, "--pr", "https://github.com/example-owner/radwerk/pull/31", "--new-title", NEW_TITLE)
        self.after_next_report()
        out = self.run_cli("show", SITE)
        self.assertIn("pull/31", out.stdout)
        self.assertNotIn("Proposal: none", out.stdout)

    def test_a_site_name_cannot_lead_the_file_out_of_its_folder(self):
        for bad in ("../../outside", "a/b.example", "..", "nodot"):
            with self.assertRaises(ValueError, msg=bad):
                fp.state_path(bad)
        out = self.run_cli("set", "../../outside", "pr_figures", "yes")
        self.assertNotEqual(out.returncode, 0)
        self.assertFalse((Path(self.home.name) / ".config" / "outside-proposals.json").exists())

    def test_the_lock_keeps_a_second_writer_waiting(self):
        old = os.environ.get("HOME")
        os.environ["HOME"] = self.home.name
        try:
            with fp.locked(SITE):
                lock = Path(self.home.name) / ".config/gsc-insights" / f".{SITE}-proposals.lock"
                with open(lock, "a") as f, self.assertRaises(BlockingIOError):
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.environ["HOME"] = old

    def test_commands_on_a_site_with_no_proposal_say_so(self):
        out = self.run_cli("decline", SITE)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("no proposal", out.stdout + out.stderr)


if __name__ == "__main__":
    unittest.main()
