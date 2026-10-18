"""make_redirects.py: from the address list and the owner's decisions to public/_redirects.

Every test goes in through main(), as a person runs it, and reads the files it wrote. The last
class runs the whole chain: wp_inventory.py counts a stub WordPress, make_redirects.py drafts the
sheet and writes the lines, a stub new site applies them the way Cloudflare was measured to (the
slash, the letter case and every escape matched exactly), and check_move.py --moves checks it.

Run:  python3 -m unittest discover -s skills/wordpress-inspector/scripts/tests
"""

import contextlib
import csv
import io
import os
import sys
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import check_move as cm  # noqa: E402
import make_redirects as mr  # noqa: E402
import test_wp_inventory as stub_wp  # noqa: E402
import wp_inventory as wi  # noqa: E402

OLD = "https://old.example"
SITE = "https://acme.example"


class Folder:
    """A throwaway inventory folder with a site's public/ folder beside it."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        os.makedirs(os.path.join(self.dir, "site", "public"))
        self.out = os.path.join(self.dir, "site", "public", "_redirects")

    def path(self, name):
        return os.path.join(self.dir, name)

    def urls(self, addresses, types=None):
        """urls.csv as wp_inventory.py writes it: url, source, type."""
        with open(self.path("urls.csv"), "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["url", "source", "type"])
            for a in addresses:
                w.writerow([wi.safe_cell(a), "both", (types or {}).get(a, "page")])
        return self.path("urls.csv")

    def moves(self, rows, delimiter=",", encoding="utf-8"):
        with open(self.path("moves.csv"), "w", encoding=encoding, newline="") as fh:
            w = csv.writer(fh, delimiter=delimiter)
            w.writerow(["old_address", "new_address", "type"])
            for old, new in rows:
                w.writerow([old, new, ""])
        return self.path("moves.csv")

    def run(self, *args):
        """(exit code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = mr.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def write(self, rows, addresses=None, *extra):
        """Write the redirects for these decisions; addresses default to the decided ones."""
        urls = self.urls(addresses if addresses is not None else [o for o, _ in rows])
        return self.run(urls, self.moves(rows), "--site", SITE, "--out", self.out, *extra)

    def lines(self):
        """The redirect lines written, comments left out."""
        with open(self.out, encoding="utf-8") as fh:
            return [ln.rstrip("\n") for ln in fh if not ln.startswith("#")]

    def close(self):
        self.tmp.cleanup()


class Case(unittest.TestCase):
    def setUp(self):
        self.f = Folder()
        self.addCleanup(self.f.close)


class Draft(Case):
    """The sheet the owner fills in: one row per old page, so each page gets one decision."""

    def draft(self, addresses, types=None):
        code, out, err = self.f.run(self.f.urls(addresses, types), "--draft", self.f.path("moves.csv"))
        if code:
            return code, None, err
        with open(self.f.path("moves.csv"), encoding="utf-8", newline="") as fh:
            return code, list(csv.DictReader(fh)), out

    def test_one_row_per_page_whatever_the_slash(self):
        code, rows, _ = self.draft([OLD + "/about/", OLD + "/about"])
        self.assertEqual(code, 0)
        self.assertEqual([(r["old_address"], r["new_address"]) for r in rows], [(OLD + "/about/", "")])

    def test_two_inventory_records_for_one_page_make_one_row(self):
        # wp_inventory's _rows does not merge two records whose links differ only by the slash
        code, rows, _ = self.draft([OLD + "/a/", OLD + "/a", OLD + "/%c3%bcber/", OLD + "/%C3%BCber"])
        self.assertEqual((code, len(rows)), (0, 2))

    def test_a_query_keeps_pages_apart(self):
        code, rows, _ = self.draft([OLD + "/?p=12", OLD + "/", OLD + "/?p=13"])
        self.assertEqual((code, len(rows)), (0, 3))

    def test_a_sitemap_only_row_has_an_empty_type(self):
        code, rows, _ = self.draft([OLD + "/a/", OLD + "/b/"], types={OLD + "/a/": "post", OLD + "/b/": ""})
        self.assertEqual([r["type"] for r in rows], ["post", ""])

    def test_an_existing_sheet_is_never_overwritten(self):
        with open(self.f.path("moves.csv"), "w", encoding="utf-8") as fh:
            fh.write("old_address,new_address\n/a/,/b\n")
        code, _, err = self.draft([OLD + "/a/"])
        self.assertEqual(code, 2)
        self.assertIn("never overwritten", err)
        with open(self.f.path("moves.csv"), encoding="utf-8") as fh:
            self.assertIn("/a/,/b", fh.read())

    def test_merged_records_take_the_first_type_given(self):
        code, rows, _ = self.draft([OLD + "/a/", OLD + "/a"], types={OLD + "/a/": "", OLD + "/a": "post"})
        self.assertEqual((code, [r["type"] for r in rows]), (0, ["post"]))

    def test_a_cell_a_spreadsheet_would_run_is_defused(self):
        code, _, _ = self.draft(["-x/"])
        with open(self.f.path("moves.csv"), encoding="utf-8") as fh:
            self.assertIn("'-x/,", fh.read())

    def test_addresses_on_another_host_are_left_out_and_named(self):
        code, rows, out = self.draft([OLD + "/a/", OLD + "/b/", "https://shop.example/cart"])
        self.assertEqual((code, len(rows)), (0, 2))
        self.assertIn("left out, on another host: https://shop.example/cart", out)


class Lines(Case):
    """What a decision turns into. Cloudflare matches the slash exactly, so a moved page needs
    a line for each form, and every line states 301 (a line without a code means 302)."""

    def test_a_moved_page_gets_both_slash_forms_with_301(self):
        code, _, _ = self.f.write([(OLD + "/leistungen/", "/angebot")])
        self.assertEqual(code, 0)
        self.assertEqual(self.f.lines(), ["/leistungen /angebot 301", "/leistungen/ /angebot 301"])

    def test_a_page_that_only_loses_its_slash_gets_no_line(self):
        # the host sends /about/ to /about itself; a line /about -> /about/ would loop with it
        code, out, _ = self.f.write([(OLD + "/about/", "/about"), (OLD + "/team/", "KEEP")])
        self.assertEqual((code, self.f.lines()), (0, []))
        self.assertRegex(out, r"kept\s+2")

    def test_let_go_writes_no_line(self):
        code, out, _ = self.f.write([(OLD + "/impressum/", "  Let Go ")])
        self.assertEqual((code, self.f.lines()), (0, []))
        self.assertRegex(out, r"let go\s+1")

    def test_a_page_moved_to_another_host(self):
        code, out, _ = self.f.write([(OLD + "/shop/", "https://shop.example/")])
        self.assertEqual((code, self.f.lines()), (0, ["/shop https://shop.example/ 301", "/shop/ https://shop.example/ 301"]))
        self.assertRegex(out, r"off the site\s+1")
        self.assertRegex(out, r"moved\s+0")

    def test_lowercase_spellings_are_added_when_the_list_has_uppercase_only(self):
        code, _, _ = self.f.write([(OLD + "/%C3%BCber/", "/ueber")])
        self.assertEqual(code, 0)
        self.assertIn("/%c3%bcber /ueber 301", self.f.lines())
        self.assertIn("/%c3%bcber/ /ueber 301", self.f.lines())

    def test_a_query_in_the_destination_is_escaped(self):
        self.f.write([(OLD + "/alt/", "/suche?q=über")])
        self.assertEqual(self.f.lines()[0], "/alt /suche?q=%C3%BCber 301")

    def test_the_same_path_with_a_query_is_refused_not_looped(self):
        # _redirects does not read the query, so /search -> /search?lang=de would match again
        code, out, _ = self.f.write([(OLD + "/search/", "/search?lang=de")])
        self.assertEqual((code, self.f.lines()), (1, []))
        self.assertIn("send it to itself", out)

    def test_a_full_address_on_the_site_itself_is_a_path(self):
        code, _, _ = self.f.write([(OLD + "/x/", SITE + "/x"), (OLD + "/y/", OLD + "/neu")])
        self.assertEqual((code, self.f.lines()), (0, ["/y /neu 301", "/y/ /neu 301"]))

    def test_an_escaped_source_is_written_as_listed_plus_the_other_case(self):
        code, _, _ = self.f.write([(OLD + "/%c3%bcber-uns/", "/ueber-uns")])
        self.assertEqual(code, 0)
        self.assertEqual(sorted(self.f.lines()), sorted([
            "/%c3%bcber-uns /ueber-uns 301", "/%c3%bcber-uns/ /ueber-uns 301",
            "/%C3%BCber-uns /ueber-uns 301", "/%C3%BCber-uns/ /ueber-uns 301"]))
        self.assertNotIn("%25", "\n".join(self.f.lines()))  # an escape is never escaped again

    def test_every_listed_spelling_and_both_cases_are_written(self):
        listed = [OLD + "/%c3%bcber", OLD + "/%C3%BCber", OLD + "/%c3%BCber"]
        code, _, _ = self.f.write([(listed[0], "/ueber")], listed)
        sources = [ln.split()[0] for ln in self.f.lines()]
        self.assertEqual(code, 0)
        self.assertEqual(sorted(sources), sorted({"/%c3%bcber", "/%C3%BCber", "/%c3%BCber",
                                                  "/%c3%bcber/", "/%C3%BCber/", "/%c3%BCber/"}))
        self.assertEqual(len(sources), len(set(sources)))

    def test_a_target_that_differs_only_in_escape_case_is_kept(self):
        # whether the host serves a page under both escape cases is unmeasured: the lowercase
        # spellings get a line, the spelling of the target itself never does
        code, out, _ = self.f.write([(OLD + "/%c3%bcber-uns/", "/%C3%BCber-uns")])
        self.assertEqual(code, 0)
        self.assertEqual(self.f.lines(), ["/%c3%bcber-uns /%C3%BCber-uns 301", "/%c3%bcber-uns/ /%C3%BCber-uns 301"])
        self.assertRegex(out, r"kept\s+1")

    def test_no_line_ever_redirects_a_page_to_itself(self):
        rows = [(OLD + "/a/", "/a"), (OLD + "/b", "/b/"), (OLD + "/%C3%BC/", "/%c3%bc"), (OLD + "/", "/")]
        code, _, _ = self.f.write(rows)
        self.assertEqual(code, 0)
        for ln in self.f.lines():
            src, dst, _ = ln.split()
            self.assertNotEqual(src.rstrip("/") or "/", dst.rstrip("/") or "/", ln)

    def test_a_raw_umlaut_destination_is_written_escaped(self):
        self.f.write([(OLD + "/alt/", "/über-uns")])
        self.assertEqual(self.f.lines()[0], "/alt /%C3%BCber-uns 301")

    def test_a_lowercase_escaped_destination_is_written_uppercase(self):
        self.f.write([(OLD + "/alt/", "/%c3%bcber-uns")])
        self.assertEqual(self.f.lines()[0], "/alt /%C3%BCber-uns 301")

    def test_the_file_opens_with_the_comment(self):
        self.f.write([(OLD + "/a/", "/b")])
        with open(self.f.out, encoding="utf-8") as fh:
            self.assertEqual(fh.readline().rstrip("\n"), mr.HEADER)

    def test_a_destination_ending_in_a_slash_gets_a_note(self):
        code, out, _ = self.f.write([(OLD + "/a/", "/b/")])
        self.assertEqual((code, self.f.lines()), (0, ["/a /b/ 301", "/a/ /b/ 301"]))
        self.assertIn("note: /b/ ends in /", out)


class Home(Case):
    def test_the_old_home_addresses_may_go_home(self):
        code, _, _ = self.f.write([(OLD + "/", "/"), (OLD + "/index.php", "/")])
        self.assertEqual((code, self.f.lines()), (0, ["/index.php / 301", "/index.php/ / 301"]))

    def test_a_deep_page_sent_home_is_refused(self):
        code, out, _ = self.f.write([(OLD + "/blog/post/", "/"), (OLD + "/a/", "/b")])
        self.assertEqual(code, 1)
        self.assertEqual(self.f.lines(), ["/a /b 301", "/a/ /b 301"])
        self.assertIn("sent home: %s/blog/post/: %s" % (OLD, cm.SENT_HOME_REASON), out)


class Chains(Case):
    def test_a_chain_is_flattened(self):
        code, _, _ = self.f.write([(OLD + "/a/", "/b"), (OLD + "/b/", "/c")])
        self.assertEqual(code, 0)
        self.assertEqual([ln for ln in self.f.lines() if ln.startswith("/a")], ["/a /c 301", "/a/ /c 301"])

    def test_a_loop_stops_the_run(self):
        code, _, err = self.f.write([(OLD + "/a/", "/b"), (OLD + "/b/", "/a")])
        self.assertEqual(code, 2)
        self.assertIn("a loop", err)
        self.assertIn("/a", err)
        self.assertIn("/b", err)
        self.assertFalse(os.path.exists(self.f.out))

    def test_one_page_two_targets_stops_the_run(self):
        code, _, err = self.f.write([(OLD + "/a", "/x"), (OLD + "/a/", "/y")])
        self.assertEqual(code, 2)
        self.assertIn("two different decisions", err)
        self.assertFalse(os.path.exists(self.f.out))

    def test_two_targets_differing_only_in_escape_case_stop_the_run(self):
        code, _, _ = self.f.write([(OLD + "/%c3%bcber", "/x"), (OLD + "/%C3%BCber", "/y")])
        self.assertEqual(code, 2)

    def test_two_different_kinds_of_decision_for_one_page_stop_the_run(self):
        code, _, err = self.f.write([(OLD + "/a", "let go"), (OLD + "/a/", "/b")])
        self.assertEqual(code, 2)
        self.assertIn("row 2", err)
        self.assertIn("row 3", err)

    def test_a_chain_into_a_let_go_or_undecided_page_writes_no_line(self):
        for target_row in ("let go", "", "kontakt"):
            with self.subTest(target_row=target_row):
                code, out, _ = self.f.write([(OLD + "/a/", "/b"), (OLD + "/b/", target_row)], None, "--replace")
                self.assertEqual(code, 1)
                self.assertFalse([ln for ln in self.f.lines() if ln.startswith("/a")])
                self.assertIn("chain: %s/a/ points at /b" % OLD, out)

    def test_a_chain_into_an_address_not_in_the_list_writes_no_line(self):
        code, out, _ = self.f.write([(OLD + "/a/", "/typo"), (OLD + "/typo/", "/x")], [OLD + "/a/"])
        self.assertEqual((code, self.f.lines()), (1, []))
        self.assertIn("chain: %s/a/ points at /typo" % OLD, out)

    def test_a_loop_closed_through_a_query_is_a_finding(self):
        # _redirects matches /b whatever the query, so /a -> /b?x and /b -> /a would loop
        code, out, _ = self.f.write([(OLD + "/a/", "/b?x=1"), (OLD + "/b/", "/a")])
        self.assertEqual(code, 1)
        self.assertEqual(self.f.lines(), [])
        self.assertIn("chain: %s/a/ points at /b?x=1" % OLD, out)

    def test_a_chain_through_a_page_moved_to_itself_ends_there(self):
        code, out, _ = self.f.write([(OLD + "/a/", "/b"), (OLD + "/b", "/b/")])
        self.assertEqual(code, 0)
        self.assertEqual([ln for ln in self.f.lines() if ln.startswith("/a")], ["/a /b 301", "/a/ /b 301"])
        self.assertNotIn("note:", out)

    def test_keep_and_a_move_to_the_same_page_are_one_decision(self):
        code, _, _ = self.f.write([(OLD + "/a", "keep"), (OLD + "/a/", "/a"),
                                   (OLD + "/s", "https://shop.example/x"), (OLD + "/s/", "https://shop.example/x/")])
        self.assertEqual(code, 0)

    def test_the_same_missing_address_twice_is_a_finding_not_a_crash(self):
        code, out, _ = self.f.write([(OLD + "/a/", "/b"), (OLD + "/typo/", "/x"), (OLD + "/typo", "/y")], [OLD + "/a/"])
        self.assertEqual(code, 1)
        self.assertEqual(out.count("not in the address list: "), 2)

    def test_an_address_that_cannot_be_parsed_is_a_finding_not_a_crash(self):
        code, out, _ = self.f.write([(OLD + "/a/", "/b"), ("http://[::1", "/x")], [OLD + "/a/"])
        self.assertEqual(code, 1)
        self.assertIn("not in the address list: http://[::1", out)

    def test_home_and_query_rules_run_on_the_final_target(self):
        code, out, _ = self.f.write([(OLD + "/a/", "/index.php"), (OLD + "/index.php", "/")])
        self.assertEqual(code, 1)
        self.assertIn("sent home: %s/a/" % OLD, out)
        self.assertEqual(self.f.lines(), ["/index.php / 301", "/index.php/ / 301"])


class CannotBeWritten(Case):
    def test_an_address_with_a_query_is_listed_not_dropped(self):
        code, out, _ = self.f.write([(OLD + "/?p=12", "/kontakt")])
        self.assertEqual((code, self.f.lines()), (1, []))
        self.assertIn("cannot be written: %s/?p=12" % OLD, out)

    def test_letting_it_go_clears_the_finding(self):
        code, _, _ = self.f.write([(OLD + "/?p=12", "let go")])
        self.assertEqual(code, 0)

    def test_a_splat_or_placeholder_in_a_source_is_refused(self):
        code, out, _ = self.f.write([(OLD + "/a*b/", "/x"), (OLD + "/c:d/", "/y")])
        self.assertEqual((code, self.f.lines()), (1, []))
        self.assertEqual(out.count("cannot be written: "), 2)

    def test_a_line_over_1000_characters_is_refused(self):
        code, out, _ = self.f.write([(OLD + "/" + "a" * 600 + "/", "/" + "b" * 400), (OLD + "/x/", "/y")])
        self.assertEqual(code, 1)
        self.assertEqual(self.f.lines(), ["/x /y 301", "/x/ /y 301"])
        self.assertIn("Cloudflare reads 1000", out)


class Findings(Case):
    def test_an_undecided_page_is_written_around_and_exits_1(self):
        listed = [OLD + "/a/", OLD + "/b/", OLD + "/c/"]
        code, out, _ = self.f.write([(OLD + "/a/", "/x"), (OLD + "/b/", "/y")], listed)
        self.assertEqual(code, 1)
        self.assertEqual(len(self.f.lines()), 4)
        self.assertIn("not decided: %s/c/" % OLD, out)

    def test_a_destination_that_is_not_understood_is_a_finding(self):
        for new in ("/ueber uns", "kontakt", "/neu\n/evil /x 301", "ftp://x.example/"):
            with self.subTest(new=new):
                code, out, _ = self.f.write([(OLD + "/a/", new)], None, "--replace")
                self.assertEqual((code, self.f.lines()), (1, []))
                self.assertIn("not understood: ", out)

    def test_a_line_break_inside_a_cell_is_not_understood(self):
        # a quoted cell may hold a line break; it must not be joined into a valid path
        code, out, _ = self.f.write([(OLD + "/a/", "/con\ntact")])
        self.assertEqual((code, self.f.lines()), (1, []))
        self.assertIn("not understood", out)

    def test_a_line_break_inside_an_old_address_matches_no_page(self):
        code, out, _ = self.f.write([(OLD + "/a\nb/", "/contact")], [OLD + "/ab/"])
        self.assertEqual((code, self.f.lines()), (1, []))
        self.assertIn("not in the address list: ", out)

    def test_a_tab_in_the_address_list_stops_the_run(self):
        code, _, err = self.f.write([(OLD + "/ab/", "/x")], [OLD + "/a\tb/", OLD + "/ab/"])
        self.assertEqual(code, 2)
        self.assertIn("control character", err)

    def test_a_name_or_password_in_a_destination_is_not_understood(self):
        code, _, _ = self.f.write([(OLD + "/a/", "https://user:pw" + chr(64) + "shop.example/x")])  # no literal at sign: check_clean
        self.assertEqual((code, self.f.lines()), (1, []))

    def test_a_destination_with_a_broken_port_is_not_understood(self):
        code, _, _ = self.f.write([(OLD + "/a/", "https://shop.example:abc/")])
        self.assertEqual((code, self.f.lines()), (1, []))

    def test_findings_past_200_are_counted_not_listed(self):
        listed = [OLD + "/p%d/" % i for i in range(202)]  # one decided, 201 not
        code, out, _ = self.f.write([(listed[0], "/x")], listed)
        self.assertEqual(code, 1)
        self.assertEqual(out.count("not decided: "), 201)  # 200 listed, then the line naming the rest
        self.assertIn("not decided: … and 1 more", out)

    def test_a_protocol_relative_destination_is_not_understood(self):
        code, out, _ = self.f.write([(OLD + "/x/", "//shop.example/cart")])
        self.assertEqual((code, self.f.lines()), (1, []))
        self.assertIn("not understood", out)

    def test_a_splat_or_colon_in_a_destination_is_not_understood(self):
        code, _, _ = self.f.write([(OLD + "/x/", "/neu*"), (OLD + "/y/", "/a:b")])
        self.assertEqual((code, self.f.lines()), (1, []))

    def test_an_anchor_in_a_destination_is_not_understood(self):
        code, out, _ = self.f.write([(OLD + "/versand/", "/faq#versand")])
        self.assertEqual((code, self.f.lines()), (1, []))
        self.assertIn("anchor", out)

    def test_a_decision_for_an_address_not_in_the_list_is_a_finding(self):
        code, out, _ = self.f.write([(OLD + "/a/", "/b"), (OLD + "/typo/", "/x")], [OLD + "/a/"])
        self.assertEqual((code, self.f.lines()), (1, ["/a /b 301", "/a/ /b 301"]))
        self.assertIn("not in the address list: %s/typo/ (row 3)" % OLD, out)


class Limits(Case):
    def test_more_than_2000_lines_writes_nothing_and_2000_writes(self):
        many = [(OLD + "/p%d/" % i, "/n%d" % i) for i in range(1001)]
        code, _, err = self.f.write(many)
        self.assertEqual(code, 2)
        self.assertIn("2,002 lines", err)
        self.assertFalse(os.path.exists(self.f.out))
        code, _, _ = self.f.write(many[:1000])
        self.assertEqual((code, len(self.f.lines())), (0, 2000))
        code, _, err = self.f.write([(OLD + "/", "/en")] + many[:1000], None, "--replace")  # "/" takes one line
        self.assertEqual(code, 2)
        self.assertIn("2,001 lines", err)


class Overwrite(Case):
    def test_an_existing_file_needs_replace(self):
        self.f.write([(OLD + "/a/", "/b")])
        code, _, err = self.f.write([(OLD + "/a/", "/c")])
        self.assertEqual(code, 2)
        self.assertIn("--replace", err)
        self.assertEqual(self.f.lines()[0], "/a /b 301")
        code, _, _ = self.f.write([(OLD + "/a/", "/c")], None, "--replace")
        self.assertEqual((code, self.f.lines()[0]), (0, "/a /c 301"))

    def test_replace_never_overwrites_a_hand_written_file(self):
        with open(self.f.out, "w", encoding="utf-8") as fh:
            fh.write("/old-campaign /angebot 301\n")
        code, _, err = self.f.write([(OLD + "/a/", "/b")], None, "--replace")
        self.assertEqual(code, 2)
        self.assertIn("not written by this script", err)
        with open(self.f.out, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "/old-campaign /angebot 301\n")

    def test_a_missing_output_folder_is_not_created(self):
        out = self.f.path("no-such-site/public/_redirects")
        code, _, _ = self.f.run(self.f.urls([OLD + "/a/"]), self.f.moves([(OLD + "/a/", "/b")]), "--site", SITE, "--out", out)
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(self.f.path("no-such-site")))

    def test_writing_without_site_is_a_usage_error(self):
        code, _, _ = self.f.run(self.f.urls([OLD + "/a/"]), self.f.moves([(OLD + "/a/", "/b")]), "--out", self.f.out)
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(self.f.out))

    def test_a_site_that_is_no_web_address_stops_the_run(self):
        code, _, err = self.f.run(self.f.urls([OLD + "/a/"]), self.f.moves([(OLD + "/a/", "/b")]),
                                  "--site", "acme.example", "--out", self.f.out)
        self.assertEqual(code, 2)
        self.assertIn("--site", err)

    def test_draft_with_site_is_a_usage_error(self):
        self.assertEqual(self.f.run(self.f.urls([OLD + "/a/"]), "--draft", self.f.path("d.csv"), "--site", SITE)[0], 2)

    def test_an_output_that_cannot_be_written_exits_2(self):
        locked = self.f.path("locked")
        os.makedirs(locked)
        os.chmod(locked, 0o555)
        self.addCleanup(os.chmod, locked, 0o755)
        if os.access(locked, os.W_OK):
            self.skipTest("running as a user who can write anywhere")
        code, _, _ = self.f.run(self.f.urls([OLD + "/a/"]), self.f.moves([(OLD + "/a/", "/b")]),
                                "--site", SITE, "--out", os.path.join(locked, "_redirects"))
        self.assertEqual(code, 2)
        code, _, _ = self.f.run(self.f.urls([OLD + "/a/"]), "--draft", os.path.join(locked, "moves.csv"))
        self.assertEqual(code, 2)

    def test_draft_and_moves_together_is_a_usage_error(self):
        urls, moves = self.f.urls([OLD + "/a/"]), self.f.moves([(OLD + "/a/", "/b")])
        self.assertEqual(self.f.run(urls, moves, "--draft", self.f.path("d.csv"))[0], 2)

    def test_draft_with_out_is_a_usage_error(self):
        self.assertEqual(self.f.run(self.f.urls([OLD + "/a/"]), "--draft", self.f.path("d.csv"), "--out", self.f.out)[0], 2)

    def test_draft_with_replace_is_a_usage_error(self):
        self.assertEqual(self.f.run(self.f.urls([OLD + "/a/"]), "--draft", self.f.path("d.csv"), "--replace")[0], 2)
        self.assertFalse(os.path.exists(self.f.path("d.csv")))


class Input(Case):
    def test_a_semicolon_sheet_reads_like_a_comma_sheet(self):
        urls = self.f.urls([OLD + "/a/"])
        with open(self.f.path("moves.csv"), "w", encoding="utf-8-sig", newline="") as fh:  # German Excel, "CSV UTF-8"
            fh.write("old_address;new_address;type\r\n%s/a/;/b;page\r\n" % OLD)
        code, _, _ = self.f.run(urls, self.f.path("moves.csv"), "--site", SITE, "--out", self.f.out)
        self.assertEqual((code, self.f.lines()), (0, ["/a /b 301", "/a/ /b 301"]))

    def test_a_sheet_that_is_not_utf8_stops_the_run(self):
        urls = self.f.urls([OLD + "/a/"])
        moves = self.f.moves([(OLD + "/a/", "/über")], encoding="cp1252")
        code, _, err = self.f.run(urls, moves, "--site", SITE, "--out", self.f.out)
        self.assertEqual(code, 2)
        self.assertIn("save it as CSV UTF-8", err)
        self.assertFalse(os.path.exists(self.f.out))

    def test_a_sheet_without_the_two_columns_or_empty_stops_the_run(self):
        urls = self.f.urls([OLD + "/a/"])
        for text in ("address,target\n/a/,/b\n", ""):
            with self.subTest(text=text):
                with open(self.f.path("moves.csv"), "w", encoding="utf-8") as fh:
                    fh.write(text)
                code, _, _ = self.f.run(urls, self.f.path("moves.csv"), "--site", SITE, "--out", self.f.out)
                self.assertEqual(code, 2)
                self.assertFalse(os.path.exists(self.f.out))

    def test_a_cell_the_inventory_defused_is_read_back(self):
        # wp_inventory writes '-x/ for an address a spreadsheet would run as a formula
        code, _, _ = self.f.write([("'-x/", "/y")], ["-x/"])
        self.assertEqual((code, self.f.lines()), (0, ["/-x /y 301", "/-x/ /y 301"]))


class CroftweaverSite(BaseHTTPRequestHandler):
    """The new site as Cloudflare Pages serves a Croftweaver build, as measured on two live kit
    sites: _redirects lines first, matched exactly (slash, letter case, escapes as written)
    whatever the query, which is passed on to the target;
    then pages, which live without the closing slash, "/page/" forwarded to "/page" with 308."""

    def log_message(self, *a):
        pass

    def answer(self, status, location=""):
        body = b"<html><body>x</body></html>"
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        if location:
            self.send_header("Location", location)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        site = self.server.site
        path, query = urllib.parse.urlsplit(self.path).path, urllib.parse.urlsplit(self.path).query
        if path in site["rules"]:
            return self.answer(301, site["rules"][path] + ("?" + query if query else ""))
        if path in site["pages"]:
            return self.answer(200)
        if path.endswith("/") and path.rstrip("/") in site["pages"]:
            return self.answer(308, path.rstrip("/"))
        return self.answer(404)


@contextlib.contextmanager
def croftweaver_site(pages, redirects_file):
    rules = {}
    with open(redirects_file, encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip() and not ln.startswith("#"):
                src, dst, _ = ln.split()
                rules.setdefault(src, dst)  # the top-most line wins
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), CroftweaverSite)
    httpd.site = {"pages": set(pages), "rules": rules}
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield "http://127.0.0.1:%d" % httpd.server_address[1]
    finally:
        httpd.shutdown()
        httpd.server_close()
        t.join(5)


class TheRealChain(unittest.TestCase):
    """Count, decide, write, deploy, check: the step this script fills, end to end."""

    def test_decisions_become_redirects_that_check_move_accepts(self):
        with stub_wp.serve() as old, tempfile.TemporaryDirectory() as tmp:
            sink = io.StringIO()
            urls, moves = os.path.join(tmp, "urls.csv"), os.path.join(tmp, "moves.csv")
            public = os.path.join(tmp, "site", "public")
            os.makedirs(public)
            out = os.path.join(public, "_redirects")
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                self.assertEqual(wi.main([old.base(), "--out", tmp, "--delay", "0"]), 0)
                self.assertEqual(mr.main([urls, "--draft", moves]), 0)
            with open(moves, encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
            host = urllib.parse.urlsplit(rows[0]["old_address"]).netloc
            plan = {"/": "keep", "/about/": "/ueber", "/directory/a/": "/angebot", "/news-1/": "/blog/erster"}

            def fill(changes):
                with open(moves, "w", encoding="utf-8", newline="") as fh:
                    w = csv.writer(fh)
                    w.writerow(["old_address", "new_address", "type"])
                    for r in rows:
                        path = urllib.parse.urlsplit(r["old_address"]).path or "/"
                        w.writerow([r["old_address"], {**plan, **changes}.get(path, "let go"), r["type"]])
            fill({})
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                self.assertEqual(mr.main([urls, moves, "--site", "https://" + host, "--out", out]), 0)
            with croftweaver_site({"/", "/ueber", "/angebot", "/blog/erster"}, out) as new:
                with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                    code = cm.main([urls, new, "--moves", moves, "--out", os.path.join(tmp, "check"), "--delay", "0"])
                self.assertEqual(code, 0, sink.getvalue()[-2000:])
                # the slash twin urls.csv does not list is redirected too
                fetcher = wi.Fetcher(new + "/", 0, 5, 10, "test")
                twin = fetcher.get(new + "/about")
                self.assertEqual((twin.via[:1], urllib.parse.urlsplit(twin.url).path), ([301], "/ueber"))
                # a decision changed after the deploy: the check says the address is not where it should be
                fill({"/about/": "/angebot"})
                with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                    code = cm.main([urls, new, "--moves", moves, "--out", os.path.join(tmp, "check"), "--delay", "0"])
                self.assertEqual(code, 1)
                with open(os.path.join(tmp, "check", "move-check.csv"), encoding="utf-8", newline="") as fh:
                    wrong = [r for r in csv.DictReader(fh) if r["result"] == "not as decided"]
                self.assertEqual([urllib.parse.urlsplit(r["old_address"]).path for r in wrong], ["/about/"])


if __name__ == "__main__":
    unittest.main()
