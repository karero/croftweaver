"""wp_inventory.py against stub WordPress sites served on 127.0.0.1 (no real network calls).

Every site test goes in through main(), the call a person makes, and reads the files it wrote:
an estimate is made from those files, so they are what must be right.

Run:  python3 -m unittest discover -s skills/wordpress-inspector/scripts/tests
"""

import contextlib
import csv
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
        self.wordpress = True

    def base(self):
        return "http://127.0.0.1:%d" % self.port

    @staticmethod
    def rec(i, typ, path, content, year="2026"):
        return {"id": i, "type": typ, "slug": "s%d" % i, "link": path, "date": year + "-03-01T10:00:00",
                "modified": year + "-04-02T10:00:00", "title": {"rendered": "T%d" % i}, "content": {"rendered": content}}

    def index(self, names):
        return "<?xml version='1.0'?><sitemapindex>%s</sitemapindex>" % "".join(
            "<sitemap><loc>%s/%s</loc></sitemap>" % ("{base}", n) for n in names)

    def urlset(self, paths):
        return "<?xml version='1.0'?><urlset>%s</urlset>" % "".join(
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
        if url.path == "/robots.txt":
            return self.send(200, "text/plain", site.robots) if site.robots is not None else self.send(404, "text/plain", "")
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
        base = route[len("wp/v2/"):] if route.startswith("wp/v2/") else None
        per, page = int(q.get("per_page", 10)), int(q.get("page", 1))
        if (base, page) in site.fail:
            return self.send(*site.fail[(base, page)])
        if base in site.records:
            recs = [dict(r, link=site.base() + r["link"]) for r in site.records[base]]
            part = recs[(page - 1) * per: page * per]
            total = site.total_override.get(base, len(recs))
            return self.send(200, "application/json", json.dumps(part),
                             [("X-WP-Total", str(total)), ("X-WP-TotalPages", str(max(1, -(-total // per))))])
        if base in site.totals:
            return self.send(200, "application/json", "[]", [("X-WP-Total", str(site.totals[base])), ("X-WP-TotalPages", "1")])
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
            code, data, _, _, _ = run(site.base())
            self.assertEqual(other.hits, [])
        self.assertEqual(data["sitemap"]["urls"], 0)
        self.assertEqual(types(data)["post"]["total"], 230)

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
        code, data, _, _, err = run("ftp://example.com")
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

    def test_an_address_on_another_host_never_matches_one_of_the_sites(self):
        self.assertEqual(wi.path_key("https://www.example.com/a/", "example.com"), "/a")
        self.assertEqual(wi.path_key("https://shop.example.net/a/", "example.com"), "https://shop.example.net/a/")


if __name__ == "__main__":
    unittest.main()
