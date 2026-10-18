"""check_move.py against a stub of the NEW site on 127.0.0.1 (no real network calls).

Every site test goes in through main() and reads the files it wrote. The last class runs the
real chain: wp_inventory.py counts a stub WordPress, and its urls.csv is what check_move.py reads.

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
import test_wp_inventory as stub_wp  # noqa: E402
import wp_inventory as wi  # noqa: E402

OLD = "https://old.example"


class NewSite:
    def __init__(self):
        self.hits = []
        self.pages = {"/", "/about/", "/news/first/"}
        self.redirects = {}      # path -> (status, target path or absolute address)
        self.unknown = (404, "")  # what an address that does not exist gets: (status, Location)
        self.probe = None         # ... and what the "cannot exist" probe gets, when that differs
        self.busy = set()

    def base(self):
        return "http://127.0.0.1:%d" % self.port


class Handler(BaseHTTPRequestHandler):
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
        path = urllib.parse.urlsplit(self.path).path
        site.hits.append(self.path)
        if path in site.busy:
            return self.answer(503)
        if path in site.redirects:
            return self.answer(*site.redirects[path])
        if path in site.pages:
            return self.answer(200)
        if path.rstrip("/") + "/" in site.pages:  # a host that adds the closing slash, as static hosts do
            return self.answer(308, path.rstrip("/") + "/")
        if site.probe is not None and path.startswith("/no-such-page-"):
            return self.answer(*site.probe)
        return self.answer(*site.unknown)


@contextlib.contextmanager
def serve(site=None):
    site = site or NewSite()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.site = site
    site.port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield site
    finally:
        httpd.shutdown()
        httpd.server_close()
        t.join(5)


def run(lines, new_site, let_go=None, extra=()):
    """main() as a person runs it. Returns (exit code, {old address: csv row}, move-check.md, stderr)."""
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "old.txt")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        args = [src, new_site, "--out", os.path.join(tmp, "out"), "--delay", "0", "--timeout", "5", *extra]
        if let_go is not None:
            lg = os.path.join(tmp, "let-go.txt")
            with open(lg, "w", encoding="utf-8") as fh:
                fh.write("\n".join(let_go) + "\n")
            args += ["--let-go", lg]
        err, sink = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(sink):
            code = cm.main(args)
        out = os.path.join(tmp, "out", "move-check.csv")
        if not os.path.exists(out):
            return code, None, None, err.getvalue()
        with open(out, encoding="utf-8", newline="") as fh:
            rows = {r["old_address"]: r for r in csv.DictReader(fh)}
        with open(os.path.join(tmp, "out", "move-check.md"), encoding="utf-8") as fh:
            return code, rows, fh.read(), err.getvalue()


class EveryAddressEndsSomewhere(unittest.TestCase):
    """The point of the check: an old address that leads nowhere is content a reader has lost."""

    def test_kept_redirected_and_missing_are_told_apart(self):
        site = NewSite()
        site.redirects["/old-news/"] = (301, "/news/first/")
        with serve(site):
            code, rows, report, _ = run([OLD + "/about/", OLD + "/old-news/", OLD + "/gone/"], site.base())
        self.assertEqual({k: v["result"] for k, v in rows.items()},
                         {OLD + "/about/": "kept", OLD + "/old-news/": "redirected", OLD + "/gone/": "missing"})
        self.assertEqual(code, 1)
        self.assertTrue(rows[OLD + "/old-news/"]["ends_at"].endswith("/news/first/"))
        self.assertIn("**1 address is not accounted for.**", report)
        self.assertIn("- https://old.example/gone/", report)

    def test_all_accounted_for_exits_0(self):
        site = NewSite()
        site.redirects["/old-news/"] = (301, "/news/first/")
        with serve(site):
            code, rows, report, _ = run([OLD + "/", OLD + "/about/", OLD + "/old-news/"], site.base())
        self.assertEqual(code, 0)
        self.assertIn("Every address is accounted for", report)

    def test_a_missing_closing_slash_is_not_a_lost_page(self):
        with serve() as site:
            code, rows, _, _ = run([OLD + "/about"], site.base())
        self.assertEqual((code, rows[OLD + "/about"]["result"]), (0, "redirected"))

    def test_a_deep_address_forwarded_to_the_home_page_is_a_finding(self):
        # the lazy catch-all: nothing reads "missing", yet the page is gone for reader and search engine
        site = NewSite()
        site.redirects["/programme/talk-1/"] = (301, "/")
        with serve(site):
            code, rows, report, _ = run([OLD + "/", OLD + "/programme/talk-1/"], site.base())
        self.assertEqual((code, rows[OLD + "/programme/talk-1/"]["result"], rows[OLD + "/"]["result"]), (1, "sent home", "kept"))
        self.assertIn("## Sent to the home page (1)", report)

    def test_a_redirect_that_leads_to_a_missing_page_is_missing(self):
        site = NewSite()
        site.redirects["/a/"] = (301, "/b/")
        with serve(site):
            code, rows, _, _ = run([OLD + "/a/"], site.base())
        self.assertEqual((code, rows[OLD + "/a/"]["result"]), (1, "missing"))
        self.assertIn("which is not found", rows[OLD + "/a/"]["note"])

    def test_a_redirect_loop_is_a_finding(self):
        site = NewSite()
        site.redirects["/a/"] = (301, "/b/")
        site.redirects["/b/"] = (301, "/a/")
        with serve(site):
            code, rows, _, _ = run([OLD + "/a/"], site.base())
        self.assertEqual((code, rows[OLD + "/a/"]["result"]), (1, "unreadable"))

    def test_a_busy_answer_is_never_read_as_kept_or_missing(self):
        site = NewSite()
        site.busy.add("/about/")
        with serve(site):
            code, rows, _, _ = run([OLD + "/about/"], site.base())
        self.assertEqual((code, rows[OLD + "/about/"]["result"]), (1, "unreadable"))

    def test_a_temporary_redirect_is_accounted_for_but_flagged(self):
        site = NewSite()
        site.redirects["/old/"] = (302, "/about/")
        with serve(site):
            code, rows, report, _ = run([OLD + "/old/"], site.base())
        self.assertEqual((code, rows[OLD + "/old/"]["result"], rows[OLD + "/old/"]["temporary_redirect"]), (0, "redirected", "302"))
        self.assertIn("1 redirect is temporary (302, 303 or 307)", report)

    def test_a_temporary_redirect_to_another_host_is_flagged_too(self):
        site = NewSite()
        site.redirects["/shop/"] = (302, "http://127.0.0.1:1/cart")
        site.redirects["/tickets/"] = (307, "/about/")
        with serve(site):
            code, rows, report, _ = run([OLD + "/shop/", OLD + "/tickets/"], site.base())
        self.assertEqual((rows[OLD + "/shop/"]["result"], rows[OLD + "/shop/"]["temporary_redirect"]), ("off the site", "302"))
        self.assertIn("2 redirects are temporary", report)
        self.assertIn("## Forwarded to another host (1)", report)
        self.assertIn("- https://old.example/shop/ → http://127.0.0.1:1/cart", report)

    def test_a_redirect_to_an_address_with_a_query_is_not_the_home_page(self):
        site = NewSite()
        site.redirects["/old/"] = (301, "/?page_id=2")
        with serve(site):
            code, rows, _, _ = run([OLD + "/old/"], site.base())
        self.assertEqual((code, rows[OLD + "/old/"]["result"]), (0, "redirected"))

    def test_a_redirect_to_an_address_that_is_no_web_address_is_unreadable_not_a_crash(self):
        site = NewSite()
        site.redirects["/bad/"] = (301, "http://127.0.0.1:notaport/x")
        site.redirects["/worse/"] = (301, "mailto:someone@example.com")
        with serve(site):
            code, rows, _, _ = run([OLD + "/bad/", OLD + "/worse/"], site.base())
        self.assertEqual((code, {r["result"] for r in rows.values()}), (1, {"unreadable"}))

    def test_a_redirect_to_another_host_is_listed_not_followed(self):
        with serve() as other, serve() as site:
            site.redirects["/privacy/"] = (301, other.base() + "/policy/")
            code, rows, _, _ = run([OLD + "/privacy/"], site.base())
            self.assertEqual(other.hits, [])
        self.assertEqual((code, rows[OLD + "/privacy/"]["result"]), (0, "off the site"))


class TheHomePage(unittest.TestCase):
    """"Sent home" is for a deep address. The old home address itself may go wherever the new
    home page lives."""

    def site(self):
        site = NewSite()
        site.pages = {"/en/", "/about/"}
        site.redirects["/"] = (302, "/en/")          # a home page that forwards by language
        site.redirects["/programme/"] = (301, "/")    # deep, sent to the front door
        site.redirects["/speakers/"] = (301, "/en/")  # deep, sent to where the front door leads
        return site

    def test_the_old_home_address_is_not_sent_home(self):
        with serve(self.site()) as site:
            code, rows, _, _ = run([OLD + "/", OLD + "/about/"], site.base())
        self.assertEqual((code, rows[OLD + "/"]["result"]), (0, "redirected"))

    def test_the_old_home_page_under_its_file_name_is_not_sent_home(self):
        site = self.site()
        site.redirects["/index.php"] = (301, "/")
        site.redirects["/index.html"] = (301, "/en/")
        with serve(site):
            code, rows, _, _ = run([OLD + "/index.php", OLD + "/index.html"], site.base())
        self.assertEqual((code, {r["result"] for r in rows.values()}), (0, {"redirected"}))

    def test_a_deep_address_is_sent_home_by_either_route(self):
        with serve(self.site()) as site:
            code, rows, _, _ = run([OLD + "/programme/", OLD + "/speakers/"], site.base())
        self.assertEqual((code, {r["result"] for r in rows.values()}), (1, {"sent home"}))
        self.assertEqual({r["note"] for r in rows.values()}, {cm.SENT_HOME_REASON})


class LetGo(unittest.TestCase):
    def test_an_address_dropped_on_purpose_is_not_a_finding(self):
        with serve() as site:
            code, rows, _, _ = run([OLD + "/about/", OLD + "/gone/", OLD + "/gone-too/"], site.base(),
                                   let_go=["# retired in 2026", "/gone", OLD + "/gone-too/"])
        self.assertEqual(code, 0)
        self.assertEqual({rows[OLD + "/gone/"]["result"], rows[OLD + "/gone-too/"]["result"]}, {"let go"})

    def test_only_the_listed_address_is_let_go(self):
        with serve() as site:
            code, rows, _, _ = run([OLD + "/gone/", OLD + "/gone/deeper/"], site.base(), let_go=["/gone/"])
        self.assertEqual((code, rows[OLD + "/gone/deeper/"]["result"]), (1, "missing"))


class CannotStart(unittest.TestCase):
    def test_a_site_that_says_found_for_everything(self):
        # without this guard every old address would read "kept" on such a site
        site = NewSite()
        site.unknown = (200, "")
        with serve(site):
            code, rows, _, err = run([OLD + "/gone/"], site.base())
        self.assertEqual((code, rows), (2, None))
        self.assertIn("cannot be told apart", err)

    def test_a_site_that_forwards_everything_to_its_home_page(self):
        site = NewSite()
        site.unknown = (301, "/")
        with serve(site):
            code, rows, _, err = run([OLD + "/gone/"], site.base())
        self.assertEqual((code, rows), (2, None))

    def test_a_probe_that_was_refused_or_busy_proves_nothing(self):
        # the site says "found" for everything, but the one probe request happened to be throttled
        for answer in ((429, ""), (503, ""), (403, "")):
            with self.subTest(answer=answer):
                site = NewSite()
                site.unknown = (200, "")
                site.probe = answer
                with serve(site):
                    code, rows, _, err = run([OLD + "/gone/"], site.base())
                self.assertEqual((code, rows), (2, None))
                self.assertIn("no plain \"not found\"", err)

    def test_a_site_that_forwards_everything_to_another_host(self):
        site = NewSite()
        site.unknown = (301, "http://127.0.0.1:1/elsewhere")
        with serve(site):
            code, rows, _, err = run([OLD + "/gone/"], site.base())
        self.assertEqual((code, rows), (2, None))
        self.assertIn("another host", err)

    def test_an_address_list_that_cannot_be_parsed(self):
        with tempfile.TemporaryDirectory() as tmp, serve() as site:
            p = os.path.join(tmp, "urls.csv")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write('url,source\n"%s",rest\n' % ("x" * (csv.field_size_limit() + 10)))
            err = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                code = cm.main([p, site.base(), "--out", os.path.join(tmp, "out")])
        self.assertEqual(code, 2)
        self.assertIn("cannot read the address list", err.getvalue())

    def test_no_addresses_and_no_site(self):
        with serve() as site:
            self.assertEqual(run([], site.base())[0], 2)
            gone = site.base()
        self.assertEqual(run([OLD + "/about/"], gone)[0], 2)
        self.assertEqual(run([OLD + "/about/"], "ftp://new.example")[0], 2)
        self.assertEqual(run([OLD + "/about/"], "https://new.example:notaport")[0], 2)


class AddressList(unittest.TestCase):
    def test_addresses_on_another_host_are_listed_and_skipped(self):
        with serve() as site:
            code, rows, report, _ = run([OLD + "/about/", "https://www.old.example/", "https://shop.other.example/cart"], site.base())
        self.assertEqual((code, sorted(rows)), (0, [OLD + "/about/", "https://www.old.example/"]))
        self.assertIn("On another host, not checked (1)", report)

    def test_the_same_address_twice_is_asked_once(self):
        with serve() as site:
            run([OLD + "/about/", "https://www.old.example/about/", "/about/"], site.base())
            asked = [h for h in site.hits if h.startswith("/about")]
        self.assertEqual(asked, ["/about/"])

    def test_with_and_without_the_closing_slash_are_two_addresses(self):
        # a site can keep "/a" and forward "/a/" to its home page: asking only one would hide that
        site = NewSite()
        site.pages.add("/a")
        site.redirects["/a/"] = (301, "/")
        with serve(site):
            code, rows, _, _ = run([OLD + "/a", OLD + "/a/"], site.base())
        self.assertEqual((code, rows[OLD + "/a"]["result"], rows[OLD + "/a/"]["result"]), (1, "kept", "sent home"))

    def test_a_cell_the_inventory_defused_is_read_back_as_the_address(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "urls.csv")
            with open(p, "w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["url", "source"])
                w.writerow([wi.safe_cell("=odd/address"), "rest"])
                w.writerow(["https://old.example/b/", "sitemap"])
            self.assertEqual(cm.read_addresses(p), ["=odd/address", "https://old.example/b/"])


def run_moves(lines, new_site, decisions, extra=()):
    """run() with a moves.csv of (old_address, new_address) rows."""
    with tempfile.TemporaryDirectory() as tmp:
        moves = os.path.join(tmp, "moves.csv")
        with open(moves, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["old_address", "new_address"])
            w.writerows(decisions)
        return run(lines, new_site, extra=("--moves", moves, *extra))


class Moves(unittest.TestCase):
    """With --moves the check asks more than "does it lead somewhere": does it lead where the
    owner decided? A redirect to the wrong page answers 200 and passes every other test."""

    def test_a_redirect_to_another_page_than_decided_is_a_finding(self):
        site = NewSite()
        site.redirects["/a/"] = (301, "/news/first/")
        with serve(site):
            code, rows, report, _ = run_moves([OLD + "/a/"], site.base(), [(OLD + "/a/", "/about")])
        self.assertEqual((code, rows[OLD + "/a/"]["result"]), (1, "not as decided"))
        self.assertIn("moves.csv sends it to /about", rows[OLD + "/a/"]["note"])
        self.assertIn("## Not where moves.csv sends it (1)", report)

    def test_a_page_kept_though_a_move_was_decided_is_a_finding(self):
        site = NewSite()
        site.pages.add("/a/")
        with serve(site):
            code, rows, _, _ = run_moves([OLD + "/a/"], site.base(), [(OLD + "/a/", "/about")])
        self.assertEqual((code, rows[OLD + "/a/"]["result"]), (1, "not as decided"))

    def test_the_decided_page_passes(self):
        site = NewSite()
        site.redirects["/a/"] = (301, "/about/")
        with serve(site):
            code, rows, _, _ = run_moves([OLD + "/a/", OLD + "/about/"], site.base(),
                                         [(OLD + "/a/", "/about"), (OLD + "/about/", "keep")])
        self.assertEqual(code, 0)
        self.assertEqual(rows[OLD + "/a/"]["decided"], "/about")

    def test_let_go_rows_count_as_let_go(self):
        with serve() as site:
            code, rows, _, _ = run_moves([OLD + "/gone/"], site.base(), [(OLD + "/gone/", "let go")])
        self.assertEqual((code, rows[OLD + "/gone/"]["result"]), (0, "let go"))

    def test_a_let_go_row_matches_across_escape_case(self):
        with serve() as site:
            code, rows, _, _ = run_moves([OLD + "/%c3%bcber/"], site.base(), [(OLD + "/%C3%BCber", "let go")])
        self.assertEqual((code, rows[OLD + "/%c3%bcber/"]["result"]), (0, "let go"))

    def test_a_let_go_row_that_still_answers_keeps_its_label(self):
        site = NewSite()
        site.redirects["/deep/"] = (301, "/")
        with serve(site):
            code, rows, _, _ = run_moves([OLD + "/about/", OLD + "/deep/"], site.base(),
                                         [(OLD + "/about/", "let go"), (OLD + "/deep/", "let go")])
        self.assertEqual(rows[OLD + "/about/"]["result"], "kept")
        self.assertEqual((code, rows[OLD + "/deep/"]["result"]), (1, "sent home"))  # still a finding

    def test_raw_and_escaped_forms_are_one_page(self):
        site = NewSite()
        site.pages.add("/%C3%BCber/")
        site.redirects["/alt/"] = (301, "/%C3%BCber/")
        with serve(site):
            code, rows, _, _ = run_moves([OLD + "/alt/"], site.base(), [(OLD + "/alt/", "/über")])
        self.assertEqual((code, rows[OLD + "/alt/"]["result"]), (0, "redirected"))

    def test_an_escaped_slash_or_hash_is_not_decoded(self):
        site = NewSite()
        site.pages.add("/a/b/")
        site.redirects["/x/"] = (301, "/a/b/")
        with serve(site):
            code, rows, _, _ = run_moves([OLD + "/x/"], site.base(), [(OLD + "/x/", "/a%2Fb")])
        self.assertEqual((code, rows[OLD + "/x/"]["result"]), (1, "not as decided"))

    def test_a_preview_checked_against_live_addresses_needs_site(self):
        site = NewSite()
        site.redirects["/old-x/"] = (301, "/about/")
        decisions = [(OLD + "/old-x/", "https://acme.example/about")]
        with serve(site):
            code, rows, _, _ = run_moves([OLD + "/old-x/"], site.base(), decisions, ("--site", "https://acme.example"))
            self.assertEqual((code, rows[OLD + "/old-x/"]["result"]), (0, "redirected"))
            code, rows, _, _ = run_moves([OLD + "/old-x/"], site.base(), decisions)
        self.assertEqual((code, rows[OLD + "/old-x/"]["result"]), (1, "not as decided"))
        self.assertIn("pass it as --site", rows[OLD + "/old-x/"]["note"])

    def test_an_off_site_decision_against_an_off_site_result(self):
        site = NewSite()
        site.redirects["/shop/"] = (301, "https://shop.example/x/")
        site.redirects["/cart/"] = (301, "https://other.example/x")
        with serve(site):
            code, rows, _, _ = run_moves([OLD + "/shop/", OLD + "/cart/"], site.base(),
                                         [(OLD + "/shop/", "https://SHOP.example/x"), (OLD + "/cart/", "https://shop.example/x")])
        self.assertEqual(rows[OLD + "/shop/"]["result"], "off the site")
        self.assertEqual((code, rows[OLD + "/cart/"]["result"]), (1, "not as decided"))

    def test_decided_column_and_report_section_only_with_moves(self):
        site = NewSite()
        with serve(site):
            _, plain, plain_report, _ = run([OLD + "/about/"], site.base())
            _, moved, moved_report, _ = run_moves([OLD + "/about/"], site.base(), [(OLD + "/about/", "keep")])
        self.assertNotIn("decided", plain[OLD + "/about/"])
        self.assertNotIn("not as decided", plain_report)
        self.assertEqual(moved[OLD + "/about/"]["decided"], "/about")
        self.assertIn("| not as decided | 0 |", moved_report)

    def test_a_redirect_to_another_port_is_not_the_decided_page(self):
        site = NewSite()
        with serve(site):                                 # same scheme and host, another port
            site.redirects["/x/"] = (301, "http://127.0.0.1:%d/about/" % (site.port + 1 if site.port < 65535 else 1))
            code, rows, _, _ = run_moves([OLD + "/x/"], site.base(), [(OLD + "/x/", "/about")])
        self.assertEqual((code, rows[OLD + "/x/"]["result"]), (1, "not as decided"))

    def test_an_off_site_decision_ending_in_a_slash(self):
        site = NewSite()
        site.redirects["/shop/"] = (301, "https://shop.example/x")
        with serve(site):
            code, rows, _, _ = run_moves([OLD + "/shop/"], site.base(), [(OLD + "/shop/", "https://shop.example/x/")])
        self.assertEqual((code, rows[OLD + "/shop/"]["result"]), (0, "off the site"))

    def test_a_sheet_with_two_decisions_for_one_page_or_a_loop_stops_the_run(self):
        for decisions in ([(OLD + "/a", "/x"), (OLD + "/a/", "/about")],
                          [(OLD + "/a/", "/b"), (OLD + "/b/", "/a")]):
            with self.subTest(decisions=decisions), serve() as site:
                code, rows, _, err = run_moves([OLD + "/a/"], site.base(), decisions)
                self.assertEqual((code, rows), (2, None))

    def test_an_undecided_row_is_named_in_the_decided_column(self):
        with serve() as site:
            _, rows, _, _ = run_moves([OLD + "/about/"], site.base(), [(OLD + "/about/", "")])
        self.assertEqual(rows[OLD + "/about/"]["decided"], "not decided")

    def test_site_without_moves_or_not_a_web_address(self):
        with serve() as site:
            self.assertEqual(run([OLD + "/about/"], site.base(), extra=("--site", "https://acme.example"))[0], 2)
            code, _, _, err = run_moves([OLD + "/about/"], site.base(), [(OLD + "/about/", "keep")], ("--site", "acme"))
        self.assertEqual(code, 2)
        self.assertIn("--site", err)

    def test_a_query_compares_in_one_escaped_form(self):
        site = NewSite()
        site.redirects["/alt/"] = (301, "/about/?q=%c3%bcber")
        with serve(site):
            code, rows, _, _ = run_moves([OLD + "/alt/"], site.base(), [(OLD + "/alt/", "/about?q=über")])
        self.assertEqual((code, rows[OLD + "/alt/"]["result"]), (0, "redirected"))

    def test_rows_naming_no_readable_address_are_listed(self):
        with serve() as site:
            code, _, report, _ = run_moves([OLD + "/about/"], site.base(),
                                           [(OLD + "/about/", "keep"), ("http://[::1", "/x")])
        self.assertEqual(code, 0)
        self.assertIn("## Rows of moves.csv that name no address it can read (1)", report)

    def test_an_address_list_with_an_address_that_cannot_be_parsed_stops_the_run(self):
        with serve() as site:
            code, rows, _, err = run([OLD + "/about/", "http://[::1"], site.base())
        self.assertEqual((code, rows), (2, None))
        self.assertIn("cannot be read", err)

    def test_a_sheet_that_cannot_be_read_stops_the_run(self):
        with serve() as site, tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "moves.csv")
            with open(bad, "w", encoding="cp1252") as fh:
                fh.write("old_address,new_address\n/a/,/über\n")
            code, rows, _, err = run([OLD + "/about/"], site.base(), extra=("--moves", bad))
        self.assertEqual((code, rows), (2, None))
        self.assertIn("save it as CSV UTF-8", err)


class TheRealChain(unittest.TestCase):
    """wp_inventory.py counts the old site; its urls.csv, unedited, is what check_move.py reads."""

    def test_the_inventorys_address_list_drives_the_check(self):
        new = NewSite()
        new.pages |= {"/news-%d/" % i for i in range(1, 229)}        # 228 posts moved as they were
        new.redirects["/news-229/"] = (301, "/news-1/")               # one merged into another
        new.redirects["/directory/a/"] = (301, "/about/")             # /news-230/, /directory/b/, the talks and
        with stub_wp.serve() as old, serve(new), tempfile.TemporaryDirectory() as tmp:  # /enquiry/ were forgotten
            sink = io.StringIO()
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                self.assertEqual(wi.main([old.base(), "--out", tmp, "--delay", "0"]), 0)
                code = cm.main([os.path.join(tmp, "urls.csv"), new.base(), "--out", tmp, "--delay", "0"])
            with open(os.path.join(tmp, "move-check.csv"), encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
        got = {}
        for r in rows:
            got[r["result"]] = got.get(r["result"], 0) + 1
        self.assertEqual(code, 1)
        self.assertEqual(len(rows), 240)
        self.assertEqual(got, {"kept": 230, "redirected": 2, "missing": 8})


if __name__ == "__main__":
    unittest.main()
