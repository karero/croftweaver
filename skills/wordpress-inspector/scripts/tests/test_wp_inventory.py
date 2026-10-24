"""wp_inventory.py against stub WordPress sites served on 127.0.0.1 (no real network calls).

Every site test goes in through main(), the call a person makes, and reads the files it wrote:
an estimate is made from those files, so they are what must be right.

Run:  python3 -m unittest discover -s skills/wordpress-inspector/scripts/tests
"""

import contextlib
import csv
import gzip
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import wp_inventory as wi  # noqa: E402

LONG_EN = " ".join(["the plan is to move the site and it has to be done with care for the people"] * 5)
LONG_DE = " ".join(["der Umzug der Seite ist nicht schwer und wird mit dem Team für die Kunden gemacht"] * 5)


class Site:
    """A stub WordPress. Tests change its fields to build the case they need."""

    def __init__(self):
        self.hits = []
        self.robots = "User-agent: *\nDisallow: /wp-admin/\n"
        self.rest_style = "pretty"  # or "query" (?rest_route=/...)
        self.types = {
            "post": {"name": "Posts", "rest_base": "posts"},
            "page": {"name": "Pages", "rest_base": "pages"},
            "talk": {"name": "Talks", "rest_base": "talk"},
            "attachment": {"name": "Media", "rest_base": "media"},
            "wp_block": {"name": "Patterns", "rest_base": "blocks"},
        }
        self.records = {
            "posts": [self.rec(i, "post", "/news-%d/" % i, LONG_DE if i % 2 else LONG_EN, "20%02d" % (16 + i % 10))
                      for i in range(1, 231)],
            "pages": [
                self.rec(1001, "page", "/", '<div class="row">[vc_column width=&#8221;1/2&#8243;][vc_column_text]'
                                            "<h2>Contact</h2>[/vc_column_text][/vc_column]</div>"),
                self.rec(1002, "page", "/about/", '<div class="vc_row">[vc_row]<p>About [sic] us [1]</p>[/vc_row]</div>'),
                self.rec(1003, "page", "/enquiry/", '<div class="gform_wrapper"><form action="/"></form></div>'),
            ],
            "talk": [self.rec(2000 + i, "talk", "/talk/t-%d/" % i, "<p>short</p>") for i in range(5)],
        }
        self.totals = {"media": 1234, "users": 3, "comments": 0, "categories": 7, "tags": 2}
        self.total_override = {}   # rest_base -> the X-WP-Total to claim
        self.fail = {}             # (rest_base, page) -> (status, content type, body)
        self.sitemaps = {
            "/sitemap_index.xml": self.index(["post-sitemap.xml", "extra-sitemap.xml"]),
            "/post-sitemap.xml": self.urlset(["/news-%d/" % i for i in range(1, 229)] + ["/", "/about/"]),
            "/extra-sitemap.xml": self.urlset(["/directory/a/", "/directory/b/"]),
        }
        self.redirects = {}        # path -> absolute address
        self.extra = {}            # path -> (status, content type, body): any other answer a test needs
        self.robots_status = 200
        self.no_total = set()      # rest_base values answered without an X-WP-Total header
        self.total_on_page = {}    # (rest_base, page) -> the X-WP-Total to claim on that page
        self.replay_first_page = set()  # rest_base values that hand out page 1 again for every page
        self.wordpress = True

    def base(self):
        return "http://127.0.0.1:%d" % self.port

    @staticmethod
    def rec(i, typ, path, content, year="2026"):
        return {"id": i, "type": typ, "slug": "s%d" % i, "link": path, "date": year + "-03-01T10:00:00",
                "modified": year + "-04-02T10:00:00", "title": {"rendered": "T%d" % i}, "content": {"rendered": content}}

    def index(self, names):
        return "<?xml version='1.0'?><sitemapindex xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>%s</sitemapindex>" % "".join(
            "<sitemap><loc>%s/%s</loc></sitemap>" % ("{base}", n) for n in names)

    def urlset(self, paths):
        return ("<?xml version='1.0'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9' "
                "xmlns:image='http://www.google.com/schemas/sitemap-image/1.1'>%s</urlset>") % "".join(
            "<url><loc>{base}%s</loc><image:image><image:loc>{base}/x.png</image:loc></image:image></url>" % p for p in paths)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, status, ctype, body, headers=()):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        site = self.server.site
        url = urllib.parse.urlsplit(self.path)
        q = dict(urllib.parse.parse_qsl(url.query))
        site.hits.append(self.path)
        if url.path in site.redirects and "rest_route" not in q:
            return self.send(301, "text/html", "", [("Location", site.redirects[url.path])])
        if url.path in site.extra:
            return self.send(*site.extra[url.path])
        if url.path == "/robots.txt":
            if site.robots is None:
                return self.send(404, "text/plain", "")
            return self.send(site.robots_status, "text/plain", site.robots)
        route = None
        if site.wordpress and site.rest_style == "pretty" and url.path.startswith("/wp-json"):
            route = url.path[len("/wp-json"):].strip("/")
        elif site.wordpress and site.rest_style == "query" and "rest_route" in q:
            route = q["rest_route"].strip("/")
        if route is not None:
            return self.rest(site, route, q)
        if url.path == "/":
            link = ""
            if site.wordpress:
                href = site.base() + ("/wp-json/" if site.rest_style == "pretty" else "/?rest_route=/")
                link = '<link rel="https://api.w.org/" href="%s" />' % href
            return self.send(200, "text/html; charset=utf-8",
                             '<html lang="en-US"><head>%s<link href="/wp-content/themes/acme/style.css">'
                             '<script src="/wp-content/plugins/js_composer/a.js"></script></head><body>home</body></html>' % link)
        if url.path in site.sitemaps:
            return self.send(200, "text/xml", site.sitemaps[url.path].replace("{base}", site.base()))
        return self.send(404, "text/html", "<html><body>not found</body></html>")

    def rest(self, site, route, q):
        if route == "":
            return self.send(200, "application/json", json.dumps({"name": "Stub | site", "namespaces": ["wp/v2", "yoast/v1"]}))
        if route == "wp/v2/types":
            return self.send(200, "application/json", json.dumps(site.types))
        if route == "wp/v2/taxonomies":
            return self.send(200, "application/json", json.dumps({
                "category": {"name": "Categories", "rest_base": "categories", "types": ["post"]},
                "post_tag": {"name": "Tags", "rest_base": "tags", "types": ["post"]},
                "nav_menu": {"name": "Menus", "rest_base": "menus", "types": ["nav_menu_item"]}}))
        base = route[len("wp/v2/"):] if route.startswith("wp/v2/") else route  # another namespace: the whole route
        per, page = int(q.get("per_page", 10)), int(q.get("page", 1))
        if (base, page) in site.fail:
            return self.send(*site.fail[(base, page)])
        if base in site.records:
            recs = [dict(r, link=site.base() + r["link"]) for r in site.records[base]]
            at = 1 if base in site.replay_first_page else page
            part = recs[(at - 1) * per: at * per]
            total = site.total_override.get(base, len(recs))
            pages = max(1, -(-total // per))
            total = site.total_on_page.get((base, page), total)
            return self.send(200, "application/json", json.dumps(part),
                             [] if base in site.no_total else [("X-WP-Total", str(total)), ("X-WP-TotalPages", str(pages))])
        if base in site.totals:
            return self.send(200, "application/json", "[]",
                             [] if base in site.no_total else [("X-WP-Total", str(site.totals[base])), ("X-WP-TotalPages", "1")])
        return self.send(404, "application/json", json.dumps({"code": "rest_no_route"}))


@contextlib.contextmanager
def serve(site=None):
    site = site or Site()
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


def run(site_url, *extra):
    """main() as a person runs it. Returns (exit code, inventory.json, urls.csv rows, inventory.md, stderr)."""
    with tempfile.TemporaryDirectory() as out:
        err, sink = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(sink):
            code = wi.main([site_url, "--out", out, "--delay", "0", "--timeout", "5", *extra])
        if not os.path.exists(os.path.join(out, "inventory.json")):
            return code, None, None, None, err.getvalue()
        with open(os.path.join(out, "inventory.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        with open(os.path.join(out, "urls.csv"), encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        with open(os.path.join(out, "inventory.md"), encoding="utf-8") as fh:
            report = fh.read()
        return code, data, rows, report, err.getvalue()


def types(data):
    return {t["type"]: t for t in data["types"]}


class FullCount(unittest.TestCase):
    """Given a site with 230 posts, 3 pages and 5 talks, the estimate is built on those numbers."""

    @classmethod
    def setUpClass(cls):
        with serve() as site:
            cls.code, cls.data, cls.rows, cls.report, _ = run(site.base())
            cls.hits = list(site.hits)

    def test_every_record_is_counted_and_the_run_says_complete(self):
        t = types(self.data)
        self.assertEqual({k: (v["total"], v["fetched"]) for k, v in t.items()},
                         {"post": (230, 230), "page": (3, 3), "talk": (5, 5)})
        self.assertEqual(self.code, 0)
        self.assertTrue(self.data["complete"])
        self.assertIn("The count is complete", self.report)

    def test_a_plugins_own_content_type_is_found_without_being_named(self):
        self.assertIn("talk", types(self.data))  # nobody told the script that "talk" exists

    def test_wordpress_own_machinery_is_not_counted_as_content(self):
        self.assertNotIn("wp_block", types(self.data))
        self.assertNotIn("attachment", types(self.data))
        self.assertFalse([h for h in self.hits if "/blocks" in h])
        self.assertEqual(self.data["media_items"], 1234)

    def test_pages_whose_builder_markup_arrives_unrendered_are_flagged(self):
        # the hand-work signal: a page whose text holds "[vc_column ...]" cannot be converted as it is
        page = types(self.data)["page"]
        self.assertEqual(page["records_with_raw_shortcodes"], 2)
        self.assertIn("vc_column", page["raw_shortcodes"])
        self.assertNotIn("sic", page["raw_shortcodes"])
        self.assertEqual(page["forms"].get("Gravity Forms"), 1)
        self.assertEqual(types(self.data)["post"]["records_with_raw_shortcodes"], 0)

    def test_sitemap_addresses_no_record_explains_are_surfaced(self):
        sm = self.data["sitemap"]
        self.assertEqual(sm["urls"], 232)
        self.assertEqual(sm["only_in_sitemap"], 2)
        self.assertEqual(sm["only_in_sitemap_by_first_segment"], {"directory": 2})
        self.assertIn("directory 2", self.report)

    def test_published_records_missing_from_the_sitemap_are_surfaced(self):
        self.assertEqual(self.data["sitemap"]["in_rest_not_in_sitemap_by_type"], {"post": 2, "page": 1, "talk": 5})

    def test_the_address_list_has_one_row_per_address(self):
        self.assertEqual(len(self.rows), 230 + 3 + 5 + 2)
        self.assertEqual(collections_count(self.rows, "source"), {"both": 230, "rest": 8, "sitemap": 2})

    def test_languages_mixed_in_one_tree_show_up(self):
        self.assertEqual(types(self.data)["post"]["languages"], {"de": 115, "en": 115})

    def test_what_the_site_is_built_with(self):
        tech = self.data["technology"]
        self.assertEqual(tech["themes"], ["acme"])
        self.assertEqual(tech["plugins_seen_on_home_page"], ["js_composer"])
        self.assertEqual(tech["rest_namespaces"], ["yoast/v1"])
        self.assertEqual(self.data["public_user_records"], 3)

    def test_text_from_the_site_cannot_break_the_report_table(self):
        self.assertIn("Stub \\| site", self.report)

    def test_no_page_text_is_written_to_disk(self):
        self.assertNotIn("Umzug", json.dumps(self.data) + self.report + json.dumps(self.rows))


def collections_count(rows, key):
    out = {}
    for r in rows:
        out[r[key]] = out.get(r[key], 0) + 1
    return out


class IncompleteCounts(unittest.TestCase):
    """A count that is short must say so and exit 1: an estimate made from it would be too low."""

    def test_a_maintenance_page_in_place_of_data_is_not_counted(self):
        site = Site()
        site.fail[("posts", 2)] = (200, "text/html", "<html><title>Maintenance in progress</title></html>")
        with serve(site):
            code, data, _, report, _ = run(site.base())
        post = types(data)["post"]
        self.assertEqual((code, post["total"], post["fetched"], post["complete"]), (1, 230, 100, False))
        self.assertFalse(data["complete"])
        self.assertIn("The count is incomplete", report)
        self.assertIn("a web page came back where data was due", report)

    def test_a_busy_site_is_not_counted(self):
        site = Site()
        site.fail[("pages", 1)] = (503, "text/html", "busy")
        with serve(site):
            code, data, _, _, _ = run(site.base())
        self.assertEqual(code, 1)
        self.assertIn("too busy (HTTP 503)", " ".join(data["incomplete_because"]))

    def test_fewer_records_than_the_site_reports(self):
        site = Site()
        site.total_override["talk"] = 9
        with serve(site):
            code, data, _, _, _ = run(site.base())
        self.assertEqual(code, 1)
        self.assertIn("talk: the site reports 9 records, 5 were handed out", data["incomplete_because"])

    def test_the_request_limit_stops_the_run_and_says_so(self):
        with serve() as site:
            code, data, _, _, _ = run(site.base(), "--max-requests", "5")
            hits = len(site.hits)
        self.assertEqual((code, hits), (1, 5))
        self.assertIn("request limit of 5", " ".join(data["incomplete_because"]))

    def test_a_site_that_keeps_robots_out_of_the_rest_api_is_not_asked(self):
        site = Site()
        site.robots = "User-agent: *\nDisallow: /wp-json/\n"
        with serve(site):
            code, data, _, _, _ = run(site.base())
            asked = [h for h in site.hits if h.startswith("/wp-json")]
        self.assertEqual((code, asked, data["rest_api"]), (1, [], False))
        self.assertEqual(data["sitemap"]["urls"], 232)  # the sitemap alone still gives a floor
        self.assertIn("robots.txt does not allow it", " ".join(data["incomplete_because"]))


class StaysOnTheSite(unittest.TestCase):
    def test_a_redirect_to_another_host_is_reported_not_followed(self):
        with serve() as other, serve() as site:
            site.redirects["/sitemap_index.xml"] = other.base() + "/sitemap_index.xml"
            site.redirects["/wp-sitemap.xml"] = other.base() + "/sitemap_index.xml"
            site.sitemaps.pop("/sitemap_index.xml")
            site.redirects["/sitemap.xml"] = other.base() + "/sitemap_index.xml"
            code, data, _, report, _ = run(site.base())
            self.assertEqual(other.hits, [])
        self.assertEqual((code, data["sitemap"]["urls"]), (1, 0))
        self.assertEqual(types(data)["post"]["total"], 230)
        self.assertIn("redirects to another host", report)

    def test_a_sitemap_file_on_another_host_is_reported_not_asked(self):
        with serve() as other, serve() as site:
            site.robots += "Sitemap: %s/sitemap_index.xml\n" % site.base()
            site.sitemaps["/sitemap_index.xml"] = (
                "<sitemapindex><sitemap><loc>{base}/post-sitemap.xml</loc></sitemap>"
                "<sitemap><loc>%s/extra-sitemap.xml</loc></sitemap></sitemapindex>" % other.base())
            code, data, _, _, _ = run(site.base())
            self.assertEqual(other.hits, [])
        self.assertEqual((code, data["sitemap"]["urls"]), (1, 230))
        self.assertIn("on another host, not asked", " ".join(data["incomplete_because"]))

    def test_the_start_address_may_move_to_the_sites_real_host_and_the_report_names_it(self):
        with serve() as real:
            front = Site()
            front.wordpress = False
            front.sitemaps = {}
            with serve(front):
                front.redirects["/"] = real.base() + "/"
                code, data, _, report, _ = run(front.base())
        self.assertEqual((code, data["site"]), (0, real.base() + "/"))
        self.assertEqual(len(data["moved"]), 1)
        self.assertIn("redirects to", report)

    def test_a_rest_api_reached_by_query_string_is_read_too(self):
        site = Site()
        site.rest_style = "query"
        with serve(site):
            code, data, _, _, _ = run(site.base())
        self.assertEqual((code, types(data)["post"]["total"], data["media_items"]), (0, 230, 1234))


class SitemapReading(unittest.TestCase):
    """The sitemap is the second witness. A sitemap that could not be read must not pass for one
    that is not there: the count would read complete with half the evidence missing."""

    def test_no_sitemap_anywhere_is_not_a_gap(self):
        site = Site()
        site.sitemaps = {}
        with serve(site):
            code, data, _, report, _ = run(site.base())
        self.assertEqual((code, data["complete"], data["sitemap"]["urls"]), (0, True, 0))
        self.assertIn("No sitemap was found", report)

    def test_a_web_page_at_a_guessed_address_is_not_a_gap(self):
        for page in ("<html><body>Nothing here</body></html>",
                     "<!DOCTYPE html><html><body><p>Nothing here<br></body></html>"):
            with self.subTest(page=page[:15]):
                site = Site()
                site.sitemaps = {}
                site.extra["/sitemap_index.xml"] = (200, "text/html; charset=utf-8", page)
                with serve(site):
                    code, data, _, _, _ = run(site.base())
                self.assertEqual((code, data["complete"]), (0, True))

    def test_an_old_style_page_the_parser_cannot_name_is_a_gap_that_names_the_address(self):
        # the price of having one reader only: this page is not told from a damaged file. It is the loud side.
        site = Site()
        site.sitemaps = {}
        site.extra["/sitemap_index.xml"] = (200, "text/html", "<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01 Transitional//EN'>\n<html><p>Not found<br></html>")
        with serve(site):
            code, data, _, report, _ = run(site.base())
        self.assertEqual((code, data["complete"]), (1, False))
        # the note says what the run knows: the address was a guess, what came back, and that it may be a page
        self.assertIn("/sitemap_index.xml (a usual address, only tried): is not valid XML", report)
        self.assertIn("a web page of a kind the XML parser cannot name); sent as text/html; not read", report)

    def test_a_sitemap_the_site_names_is_a_real_gap_whatever_answers_there(self):
        # robots.txt or an index says a sitemap is there; a web page in its place means addresses are missing
        page = "<!DOCTYPE html><html><body><p>Error<br></body></html>"
        site = Site()
        with serve(site):
            site.robots += "Sitemap: %s/sitemap_index.xml\n" % site.base()
            site.extra["/post-sitemap.xml"] = (200, "text/html", page)      # a file the index names
            code, data, _, report, _ = run(site.base())
        self.assertEqual((code, data["complete"], data["sitemap"]["urls"]), (1, False, 2))
        self.assertIn("/post-sitemap.xml: a web page or another kind of document, not a sitemap; sent as text/html; not read", report)
        site = Site()
        with serve(site):
            site.robots += "Sitemap: %s/sitemap_index.xml\n" % site.base()
            site.extra["/sitemap_index.xml"] = (200, "text/html", page)    # the file robots.txt names
            code, data, _, report, _ = run(site.base())
            asked = [h for h in site.hits if "sitemap" in h]
        self.assertEqual((code, data["complete"]), (1, False))
        self.assertIn("/sitemap_index.xml: a web page, not a sitemap", report)
        self.assertNotIn("only tried", report)
        # where robots.txt names a sitemap, no usual address is tried: one address, asked once, one kind of note
        self.assertEqual(asked, ["/sitemap_index.xml"])

    def test_a_gap_note_keeps_its_end_however_long_the_address(self):
        site = Site()
        long_path = "/maps/" + "a" * 5000 + ".xml"
        with serve(site):
            site.robots += "Sitemap: %s%s\n" % (site.base(), long_path)
            site.extra[long_path] = (200, "text/html", "<urlset><url><lo")
            code, data, _, report, _ = run(site.base())
        self.assertEqual(code, 1)
        self.assertIn(long_path + ": is not valid XML", report)
        self.assertIn("a web page of a kind the XML parser cannot name); sent as text/html; not read", report)

    def test_a_packed_file_that_cannot_be_unpacked_says_what_it_was_sent_as(self):
        site = Site()
        site.sitemaps = {}
        site.extra["/sitemap_index.xml"] = (200, "application/x-gzip", b"\x1f\x8b" + b"not really packed")
        with serve(site):
            code, data, _, report, _ = run(site.base())
        self.assertEqual(code, 1)
        self.assertIn("/sitemap_index.xml (a usual address, only tried): cannot be unpacked; sent as application/x-gzip; not read", report)

    def test_a_cut_off_sitemap_is_a_gap_wherever_its_first_element_sits(self):
        # the invariant: a sitemap is read whole or it is a gap, never a quietly missing one
        start = "<?xml version='1.0'?>%s<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'><url><loc>{base}/a/</loc></url><url><lo"
        for lead in ("", "<!-- %s -->" % ("x" * 5000), "\n" * 6000):
            with self.subTest(lead=len(lead)):
                site = Site()
                site.sitemaps = {"/sitemap_index.xml": start % lead}
                with serve(site):
                    code, data, _, _, _ = run(site.base())
                self.assertEqual((code, data["complete"], data["sitemap"]["urls"]), (1, False, 0))
                self.assertIn("not valid XML", " ".join(data["incomplete_because"]))

    def test_a_cut_off_sitemap_sent_as_a_web_page_is_still_a_gap(self):
        # the header may lie; a page is known by its own markup, and a cut-off sitemap has none
        cut = "<?xml version='1.0'?>%s<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'><url><loc>http://x.test/a/</loc></url><url><lo"
        for lead in ("", "<!-- %s -->" % ("x" * 5000), "<!-- <html> <!DOCTYPE html> -->", "<?note <html lang='en'> ?>"):
            with self.subTest(lead=lead[:24]):
                site = Site()
                site.sitemaps = {}
                site.extra["/sitemap_index.xml"] = (200, "text/html; charset=utf-8", cut % lead)
                with serve(site):
                    code, data, _, _, _ = run(site.base())
                self.assertEqual((code, data["complete"]), (1, False))
                self.assertIn("not valid XML", " ".join(data["incomplete_because"]))

    def test_a_document_type_however_it_is_written_stops_the_reader(self):
        # the invariant: nothing after a document type is read, so no entity can expand.
        # (Kept small on purpose: were the guard gone, a large one would hang the test run.)
        bomb = ("<?xml version='1.0'%s?>%s<!DOCTYPE urlset [<!ENTITY a 'aaaaaaaaaa'><!ENTITY b '&a;&a;&a;&a;'>]>"
                "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'><url><loc>http://x.test/&b;/</loc></url></urlset>")
        cases = {
            "plain": (bomb % ("", "")).encode(),
            "after 5,000 spaces, no declaration": (bomb % ("", " " * 5000)).split("?>", 1)[1].encode(),
            "after a comment and 9,000 line ends": (bomb % ("", "<!-- note -->" + "\n" * 9000)).encode(),
            "after a processing instruction": (bomb % ("", "\n<?xml-stylesheet href='a.xsl'?>\n  ")).encode(),
            "behind a UTF-8 byte-order mark": b"\xef\xbb\xbf" + (bomb % ("", "")).encode(),
            "utf-16 with a byte-order mark": (bomb % (" encoding='UTF-16'", "")).encode("utf-16"),
            "utf-16 little-endian, no mark": (bomb % ("", "")).encode("utf-16-le"),
            "utf-16 big-endian, no mark": (bomb % ("", "")).encode("utf-16-be"),
            "latin-1, declared": (bomb % (" encoding='ISO-8859-1'", "")).encode("latin-1"),
            "an 8-bit code page, declared": (bomb % (" encoding='cp1252'", "")).encode("cp1252"),
        }
        for name, body in cases.items():
            with self.subTest(name=name):
                self.assertEqual(wi.parse_sitemap(body), ("", [], "declares a document type, which a sitemap does not need"))
                site = Site()
                site.sitemaps = {}
                site.extra["/sitemap_index.xml"] = (200, "text/xml", body)
                with serve(site):
                    code, data, _, _, _ = run(site.base())
                self.assertEqual((code, data["complete"], data["sitemap"]["urls"]), (1, False, 0))
        # letters the parser cannot read as XML at all (EBCDIC after an ASCII declaration, UTF-32)
        for body in (b"<?xml version='1.0' encoding='cp500'?>" + (bomb % ("", "")).split("?>", 1)[1].encode("cp500"),
                     (bomb % ("", "")).encode("utf-32")):
            self.assertEqual(wi.parse_sitemap(body), ("", [], "is not valid XML (cut off, damaged, in an unknown encoding, or a web page of a kind the XML parser cannot name)"))

    def test_the_words_of_a_comment_are_not_a_document_type(self):
        ok = ("%s<?xml version='1.0' encoding='UTF-8'?>\n<!-- made by a plugin; no <!DOCTYPE here -->\n<?xml-stylesheet href='a.xsl'?>\n"
              "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'><!-- <!DOCTYPE x> --><url><loc>http://x.test/\u00e4/</loc></url></urlset>")
        for name, body in (("plain", (ok % "").encode()), ("with a byte-order mark", b"\xef\xbb\xbf" + (ok % "").encode()),
                           ("in Latin-1, declared", (ok % "").replace("UTF-8", "ISO-8859-1").encode("latin-1")),
                           ("in UTF-16", (ok % "").replace("UTF-8", "UTF-16").encode("utf-16"))):
            with self.subTest(name=name):
                self.assertEqual(wi.parse_sitemap(body), ("urlset", ["http://x.test/\u00e4/"], ""))
                site = Site()
                site.sitemaps = {}
                site.extra["/sitemap_index.xml"] = (200, "text/xml", body)
                with serve(site):
                    code, data, _, _, _ = run(site.base())
                self.assertEqual((code, data["sitemap"]["urls"]), (0, 1))

    def test_what_the_reader_takes_for_an_address(self):
        ns = "xmlns='http://www.sitemaps.org/schemas/sitemap/0.9' xmlns:image='http://www.google.com/schemas/sitemap-image/1.1'"
        doc = ("<urlset %s><url><loc> http://x.test/a?b=1&amp;c=2 </loc><image:image><image:loc>http://x.test/i.png</image:loc></image:image>"
               "</url><url><loc></loc></url><loc>http://x.test/stray/</loc><url><x><loc>http://x.test/deep/</loc></x></url></urlset>" % ns)
        self.assertEqual(wi.parse_sitemap(doc.encode()), ("urlset", ["http://x.test/a?b=1&c=2"], ""))
        self.assertEqual(wi.parse_sitemap(b"<sitemapindex><sitemap><loc>/s1.xml</loc></sitemap></sitemapindex>"), ("sitemapindex", ["/s1.xml"], ""))
        for page in (b"<!DOCTYPE html><html><p>x<br></html>",
                     b"\xef\xbb\xbf<!DOCTYPE html><html><p>x<br></html>",
                     b"<!-- served by a cache -->\n" + b" " * 3000 + b"<!DOCTYPE html><html><p>x<br></html>",
                     b"<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01//EN' 'http://www.w3.org/TR/html4/strict.dtd'><html><p>x<br></html>"):
            self.assertEqual(wi.parse_sitemap(page), ("page", [], ""))
        # a document type that only looks like a page's, in front of a cut-off sitemap, is refused or unreadable, never a page
        damaged = "is not valid XML (cut off, damaged, in an unknown encoding, or a web page of a kind the XML parser cannot name)"
        refused = "declares a document type, which a sitemap does not need"
        cut = b"<urlset><url><lo"
        self.assertEqual(wi.parse_sitemap(b"<!DOCTYPE htmlx [<!ENTITY a 'b'>]>" + cut), ("", [], refused))
        self.assertEqual(wi.parse_sitemap(b"<!DOCTYPE html-foo SYSTEM 'x'>" + cut), ("", [], refused))
        # a page's document type is read past only as far as the first element: a sitemap behind it is refused,
        # and one that declares anything itself (an internal subset) is refused at once, page or not
        self.assertEqual(wi.parse_sitemap(b"<!DOCTYPE html>" + cut), ("", [], refused))
        self.assertEqual(wi.parse_sitemap(b"<!DOCTYPE html><sm:urlset xmlns:sm='x'><sm:url/></sm:urlset>"), ("", [], refused))
        self.assertEqual(wi.parse_sitemap(b"<!DOCTYPE html [<!ENTITY a 'b'>]><html><p>&a;</p></html>"), ("", [], refused))
        self.assertEqual(wi.parse_sitemap(b"<!DOCTYPE html [ ]><html/>"), ("", [], refused))
        self.assertEqual(wi.parse_sitemap(b"<!DOCTYPE html><head><title>x</title>"), ("other", [], ""))
        self.assertEqual(wi.parse_sitemap(b"<!DOCTYPE html>\n<!-- nothing follows -->"), ("", [], damaged))
        for name in (b"html-foo", b"html:foo", b"html.foo", b"html"):
            # PUBLIC with no system identifier: XML cannot read it, so the reader names nothing
            self.assertEqual(wi.parse_sitemap(b"<!DOCTYPE " + name + b" PUBLIC 'x'>" + cut), ("", [], damaged))
        self.assertEqual(wi.parse_sitemap(b"\n<html lang='en'><body><p>Nothing<br></body></html>"), ("page", [], ""))
        self.assertEqual(wi.parse_sitemap(b"<rss version='2.0'><channel/></rss>"), ("other", [], ""))
        for body in (b"", b"Not found", b"<urlset><url><loc>http://x.test/a/</loc></url>", b"<urlset><url><loc>&nope;</loc></url></urlset>"):
            self.assertEqual(wi.parse_sitemap(body), ("", [], damaged))

    def test_a_sitemap_the_parser_cannot_decode_is_a_gap_not_a_crash(self):
        for enc in ("bogus-enc", "utf-7"):
            with self.subTest(enc=enc):
                site = Site()
                site.sitemaps = {"/sitemap_index.xml": "<?xml version='1.0' encoding='%s'?><urlset><url><loc>{base}/a/</loc></url></urlset>" % enc}
                with serve(site):
                    code, data, _, _, _ = run(site.base())
                self.assertEqual((code, data["complete"]), (1, False))

    def test_a_sitemap_with_a_document_type_is_refused_unparsed(self):
        # entity tricks need a document type; the Python a Mac ships with has no guard against them
        bomb = ("<?xml version='1.0'?><!DOCTYPE urlset [<!ENTITY a 'aaaaaaaaaa'><!ENTITY b '&a;&a;&a;&a;&a;&a;&a;&a;'>]>"
                "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'><url><loc>{base}/&b;/</loc></url></urlset>")
        site = Site()
        site.sitemaps = {"/sitemap_index.xml": bomb}
        with serve(site):
            code, data, _, _, _ = run(site.base())
        self.assertEqual((code, data["sitemap"]["urls"]), (1, 0))
        self.assertIn("declares a document type", " ".join(data["incomplete_because"]))

    def test_guessed_addresses_that_are_busy_or_refused_make_the_count_incomplete(self):
        for status in (503, 403, 429):
            with self.subTest(status=status):
                site = Site()
                site.sitemaps = {}
                for path in ("/sitemap_index.xml", "/wp-sitemap.xml", "/sitemap.xml"):
                    site.extra[path] = (status, "text/html", "wait")
                with serve(site):
                    code, data, _, report, _ = run(site.base())
                self.assertEqual((code, data["complete"]), (1, False))
                self.assertIn("sitemap", " ".join(data["incomplete_because"]))
                self.assertIn("The count is incomplete", report)

    def test_a_sitemap_cut_off_in_the_middle_is_a_gap_not_a_shorter_sitemap(self):
        site = Site()
        whole = site.sitemaps["/post-sitemap.xml"]
        site.sitemaps["/post-sitemap.xml"] = whole[: len(whole) // 2]
        with serve(site):
            code, data, _, _, _ = run(site.base())
        self.assertEqual(code, 1)
        self.assertIn("not valid XML", " ".join(data["incomplete_because"]))
        self.assertEqual(data["sitemap"]["urls"], 2)  # the other file was still read

    def test_a_cut_off_sitemap_at_a_guessed_address_is_a_gap_too(self):
        site = Site()
        site.sitemaps = {"/sitemap_index.xml": "<?xml version='1.0'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'><url><loc>{base}/a/</loc></url><url><lo"}
        with serve(site):
            code, data, _, _, _ = run(site.base())
        self.assertEqual((code, data["sitemap"]["urls"]), (1, 0))

    def test_a_sitemap_whose_elements_carry_a_prefix_is_read(self):
        site = Site()
        site.sitemaps = {"/sitemap_index.xml": (
            "<?xml version='1.0'?><sm:urlset xmlns:sm='http://www.sitemaps.org/schemas/sitemap/0.9'>"
            "<sm:url><sm:loc>{base}/news-1/</sm:loc></sm:url><sm:url><sm:loc> {base}/directory/a/ </sm:loc></sm:url></sm:urlset>")}
        with serve(site):
            code, data, _, _, _ = run(site.base())
        self.assertEqual((code, data["sitemap"]["urls"], data["sitemap"]["only_in_sitemap"]), (0, 2, 1))

    def test_a_packed_sitemap_is_read_and_one_that_unpacks_too_large_is_a_gap(self):
        site = Site()
        packed = gzip.compress(("<?xml version='1.0'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>%s</urlset>"
                                % "".join("<url><loc>http://127.0.0.1/p-%d/</loc></url>" % i for i in range(400))).encode())
        site.sitemaps = {}
        site.extra["/sitemap_index.xml"] = (200, "application/x-gzip", packed)
        with serve(site):
            code, data, _, _, _ = run(site.base())
            self.assertEqual((code, data["sitemap"]["urls"]), (0, 400))
            limit, wi.SITEMAP_MAX_BYTES = wi.SITEMAP_MAX_BYTES, 4096  # the packed file is under it, its contents are not
            try:
                self.assertLess(len(packed), 4096)
                code, data, _, _, _ = run(site.base())
            finally:
                wi.SITEMAP_MAX_BYTES = limit
        self.assertEqual((code, data["sitemap"]["urls"]), (1, 0))
        self.assertIn("unpacks to more than the limit of 0 MB; sent as application/x-gzip; not read", " ".join(data["incomplete_because"]))

    def test_a_sitemap_named_under_the_sites_other_spelling_is_asked_on_the_site(self):
        # robots.txt files often still say http:// (or https://) after the site changed over
        site = Site()
        with serve(site):
            site.robots += "Sitemap: https://127.0.0.1:%d/sitemap_index.xml\n" % site.port
            code, data, _, _, _ = run(site.base())
        self.assertEqual((code, data["sitemap"]["urls"]), (0, 232))


class RecordCounting(unittest.TestCase):
    def test_a_list_that_repeats_itself_is_not_a_full_count(self):
        # 230 rows arrive, but they are the first 100 records again and again
        site = Site()
        site.replay_first_page.add("posts")
        with serve(site):
            code, data, rows, _, _ = run(site.base())
        post = types(data)["post"]
        self.assertEqual((code, post["complete"], post["fetched"]), (1, False, 100))
        self.assertIn("handed out twice", post["note"])
        self.assertEqual(sum(1 for r in rows if r["type"] == "post"), 100)

    def test_records_without_an_id_cannot_pass_for_a_full_count(self):
        # two rows with no id may be one record twice; the count must not call that complete
        site = Site()
        for bad in (None, "", True, 1.5, [7], {"n": 7}):
            with self.subTest(bad=bad):
                site.records["talk"] = [dict(site.rec(0, "talk", "/talk/x/", "<p>x</p>"), id=bad) for _ in range(2)]
                with serve(site):
                    code, data, _, _, _ = run(site.base())
                talk = types(data)["talk"]
                self.assertEqual((code, talk["complete"], talk["fetched"]), (1, False, 2))
                self.assertIn("without a usable id", talk["note"])

    def test_a_total_that_changes_between_pages_is_said(self):
        site = Site()
        site.total_on_page[("posts", 2)] = 231
        with serve(site):
            code, data, _, _, _ = run(site.base())
        self.assertEqual(code, 1)
        self.assertIn("total changed while it was read (230, then 231)", types(data)["post"]["note"])

    def test_a_type_without_a_total_is_incomplete_and_says_why(self):
        site = Site()
        site.no_total.add("talk")
        with serve(site):
            code, data, _, report, _ = run(site.base())
        self.assertEqual(code, 1)
        self.assertEqual(types(data)["talk"]["note"], "the site did not report a total")
        self.assertNotIn("None", report)

    def test_media_or_a_grouping_without_a_usable_count_is_incomplete(self):
        for base, kind in (("media", "no_total"), ("categories", "no_total"), ("media", "not_a_list"), ("media", "negative")):
            with self.subTest(base=base, kind=kind):
                site = Site()
                if kind == "no_total":
                    site.no_total.add(base)
                elif kind == "negative":
                    site.totals[base] = -4
                else:
                    site.fail[(base, 1)] = (200, "application/json", json.dumps({"code": "odd"}), [("X-WP-Total", "5")])
                with serve(site):
                    code, data, _, _, _ = run(site.base())
                self.assertEqual((code, data["complete"]), (1, False))

    def test_a_type_registered_under_a_plugins_own_namespace_is_read_there(self):
        site = Site()
        site.types["job"] = {"name": "Jobs", "rest_base": "jobs", "rest_namespace": "acme/v1"}
        site.records["acme/v1/jobs"] = [site.rec(3000 + i, "job", "/jobs/j-%d/" % i, "<p>x</p>") for i in range(4)]
        with serve(site):
            code, data, _, _, _ = run(site.base())
            asked = [h for h in site.hits if "/acme/v1/jobs" in h]
        self.assertEqual((code, types(data)["job"]["total"], len(asked)), (0, 4, 1))

    def test_two_addresses_that_differ_only_in_the_query_are_two_addresses(self):
        site = Site()
        site.records["talk"] = [site.rec(2000 + i, "talk", "/?p=%d" % (2000 + i), "<p>x</p>") for i in range(5)]
        site.sitemaps["/extra-sitemap.xml"] = site.urlset(["/?p=2000", "/?p=9999"])
        with serve(site):
            code, data, rows, _, _ = run(site.base())
        self.assertEqual(sum(1 for r in rows if r["type"] == "talk"), 5)
        self.assertEqual(sum(1 for r in rows if r["source"] == "sitemap"), 1)      # /?p=9999 only
        self.assertEqual(data["sitemap"]["in_rest_not_in_sitemap_by_type"].get("talk"), 4)


class Robots(unittest.TestCase):
    """The promise is "obeys robots.txt". The standard library reads the file differently from one
    Python to the next, so these run the same on 3.9 and on 3.13."""

    def rules(self, text):
        r = wi.RobotsRules()
        r.parse(text)
        return r

    def test_wildcards_and_the_end_mark_count(self):
        r = self.rules("User-agent: *\nDisallow: /private*\nDisallow: /*?rest_route=\nDisallow: /*.pdf$\n")
        self.assertFalse(r.allowed("https://e.test/private-area/x"))
        self.assertFalse(r.allowed("https://e.test/?rest_route=/wp/v2/posts"))
        self.assertFalse(r.allowed("https://e.test/files/a.pdf"))
        self.assertTrue(r.allowed("https://e.test/files/a.pdf.html"))
        self.assertTrue(r.allowed("https://e.test/public/"))

    def test_the_longest_rule_wins_and_allow_wins_a_tie(self):
        r = self.rules("User-agent: *\nDisallow: /wp-json/\nAllow: /wp-json/wp/v2/\nDisallow: /a\nAllow: /a\n")
        self.assertTrue(r.allowed("https://e.test/wp-json/wp/v2/posts"))
        self.assertFalse(r.allowed("https://e.test/wp-json/other/v1/x"))
        self.assertTrue(r.allowed("https://e.test/a"))

    def test_a_group_that_names_this_tool_replaces_the_group_for_everyone(self):
        r = self.rules("User-agent: *\nDisallow: /\n\nUser-agent: wordpress-inventory\nDisallow: /wp-admin/\n")
        self.assertTrue(r.allowed("https://e.test/wp-json/"))
        self.assertFalse(r.allowed("https://e.test/wp-admin/x"))
        self.assertEqual(self.rules("Sitemap: https://e.test/s.xml\nUser-agent: *\nDisallow:\n").sitemaps, ["https://e.test/s.xml"])

    def test_a_wildcard_rule_keeps_the_tool_out_of_the_rest_api(self):
        site = Site()
        site.robots = "User-agent: *\nDisallow: /wp-json/wp/v2/po*\n"
        with serve(site):
            code, data, _, _, _ = run(site.base())
            asked = [h for h in site.hits if h.startswith("/wp-json/wp/v2/posts")]
        self.assertEqual((code, asked), (1, []))
        self.assertEqual(types(data)["page"]["total"], 3)
        self.assertIn("robots.txt does not allow it", types(data)["post"]["note"])

    def test_a_refused_or_unreadable_robots_file_stops_the_run(self):
        for status in (401, 403, 429, 500):
            with self.subTest(status=status):
                site = Site()
                site.robots_status = status
                with serve(site):
                    code, data, _, _, err = run(site.base())
                    self.assertEqual(len(site.hits), 1)
                self.assertEqual((code, data), (2, None))
                self.assertIn("robots.txt", err)


class CannotStart(unittest.TestCase):
    def test_a_site_that_is_not_wordpress_and_has_no_sitemap(self):
        site = Site()
        site.wordpress = False
        site.sitemaps = {}
        with serve(site):
            code, data, _, _, err = run(site.base())
        self.assertEqual((code, data), (2, None))
        self.assertIn("neither a WordPress REST API nor a sitemap", err)

    def test_not_a_web_address(self):
        for bad in ("ftp://example.com", "https://example.com:notaport/", "https:///nohost"):
            with self.subTest(bad=bad):
                code, data, _, _, err = run(bad)
                self.assertEqual((code, data), (2, None))
                self.assertIn("not a web address", err)

    def test_nothing_answers(self):
        with serve() as site:
            gone = site.base()
        code, data, _, _, _ = run(gone)
        self.assertEqual((code, data), (2, None))


class Pieces(unittest.TestCase):
    def test_a_bracketed_word_is_a_shortcode_only_with_a_closing_tag_an_attribute_or_an_underscore(self):
        text = wi.strip_tags("[vc_column width=&#8221;1/2&#8243;]x[/vc_column] [caption id=\"a\"]y[/caption] "
                             "[gallery ids=\"1,2\"] [sic] [1] [Anm. d. Red.] [more]")
        self.assertEqual(set(wi.raw_shortcodes(text)), {"vc_column", "caption", "gallery"})

    def test_short_text_gets_no_language(self):
        self.assertEqual(wi.guess_language("der die das und"), "unknown")
        self.assertEqual(wi.guess_language(LONG_DE), "de")
        self.assertEqual(wi.guess_language(LONG_EN), "en")

    def test_a_cell_a_spreadsheet_would_run_is_defused(self):
        self.assertEqual(wi.safe_cell("=HYPERLINK(1)"), "'=HYPERLINK(1)")
        self.assertEqual(wi.safe_cell("https://example.com/a"), "https://example.com/a")
        self.assertEqual(wi.safe_cell(None), "")

    def test_text_from_the_site_cannot_write_a_link_into_the_report(self):
        self.assertEqual(wi.md("[click](http://x.test) ![i](y)"), "\\[click\\](http://x.test) !\\[i\\](y)")

    def test_an_address_on_another_host_never_matches_one_of_the_sites(self):
        self.assertEqual(wi.path_key("https://www.example.com/a/?b=1", "example.com"), "/a?b=1")
        self.assertEqual(wi.path_key("https://www.example.com/a/", "example.com"), "/a")
        self.assertEqual(wi.path_key("https://shop.example.net/a/", "example.com"), "https://shop.example.net/a/")


if __name__ == "__main__":
    unittest.main()
