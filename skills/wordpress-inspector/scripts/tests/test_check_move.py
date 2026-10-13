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
        self.assertEqual((code, rows[OLD + "/old/"]["result"]), (0, "redirected"))
        self.assertIn("temporary redirect (302)", rows[OLD + "/old/"]["note"])
        self.assertIn("1 redirects are temporary", report)

    def test_a_redirect_to_another_host_is_listed_not_followed(self):
        with serve() as other, serve() as site:
            site.redirects["/privacy/"] = (301, other.base() + "/policy/")
            code, rows, _, _ = run([OLD + "/privacy/"], site.base())
            self.assertEqual(other.hits, [])
        self.assertEqual((code, rows[OLD + "/privacy/"]["result"]), (0, "off the site"))


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

    def test_no_addresses_and_no_site(self):
        with serve() as site:
            self.assertEqual(run([], site.base())[0], 2)
            gone = site.base()
        self.assertEqual(run([OLD + "/about/"], gone)[0], 2)
        self.assertEqual(run([OLD + "/about/"], "ftp://new.example")[0], 2)


class AddressList(unittest.TestCase):
    def test_addresses_on_another_host_are_listed_and_skipped(self):
        with serve() as site:
            code, rows, report, _ = run([OLD + "/about/", "https://www.old.example/", "https://shop.other.example/cart"], site.base())
        self.assertEqual((code, sorted(rows)), (0, [OLD + "/about/", "https://www.old.example/"]))
        self.assertIn("On another host, not checked (1)", report)

    def test_one_address_in_two_spellings_is_asked_once(self):
        with serve() as site:
            run([OLD + "/about/", OLD + "/about", "/about/"], site.base())
            asked = [h for h in site.hits if h.startswith("/about")]
        self.assertEqual(len(asked), 1)

    def test_a_cell_the_inventory_defused_is_read_back_as_the_address(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "urls.csv")
            with open(p, "w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["url", "source"])
                w.writerow([wi.safe_cell("=odd/address"), "rest"])
                w.writerow(["https://old.example/b/", "sitemap"])
            self.assertEqual(cm.read_addresses(p), ["=odd/address", "https://old.example/b/"])


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
