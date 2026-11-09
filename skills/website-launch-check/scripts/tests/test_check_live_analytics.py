"""Tests for check_live_analytics.py. Each test runs the script the way the launch check does,
`python3 check_live_analytics.py <address>` in a site folder, against a local server that serves
captures of live pages (tests/fixtures, fetched 2026-11-09; the only edits are made-up names,
hosts and script ids in place of real ones). Standard library
only; no real requests.

    python3 -m unittest discover -s skills/website-launch-check/scripts/tests

Expected counts are written by hand from the captures: the guide page has one script tag
(/js/pa-<id>.js) and one plausible.init stub; the webcroft.dev page has no analytics tag;
the older-tag page has one older tag (data-domain, /js/script.js) and no stub.
"""
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "check_live_analytics.py"
FIX = HERE / "fixtures"
sys.path.insert(0, str(HERE.parent))
import check_live_analytics as cla  # noqa: E402

GUIDE = (FIX / "live-home-guide.croftweaver.com-2026-11-09.html").read_text(encoding="utf-8")
BARE = (FIX / "live-home-webcroft.dev-2026-11-09.html").read_text(encoding="utf-8")
OLDTAG = (FIX / "live-home-older-tag-2026-11-09.html").read_text(encoding="utf-8")

HOST = "https://analytics.example.com"
SID = "pa-ExampleId0000000000000"
WANT = f"{HOST}/js/{SID}.js"
STARTER = HERE.parents[2] / "new-website" / "templates" / "astro"
GATE = STARTER / "tests" / "check_analytics_gate.sh"
REQUIRE_STARTER = os.environ.get("LAUNCH_CHECK_REQUIRE_STARTER") == "1"


def config(use="export const USE_ANALYTICS = true;", mode="'script' as 'script'", extra=""):
    use_line = use + "\n" if use else ""
    return (f"export const PROD_BRANCH = 'production';\n{use_line}{extra}"
            "export const ANALYTICS = {\n"
            f"  enabled: {'USE_ANALYTICS && ' if use else ''}process.env.WORKERS_CI_BRANCH === PROD_BRANCH,\n"
            f"  mode: {mode},\n"
            f"  scriptHost: '{HOST}',\n"
            f"  scriptId: '{SID}',\n"
            "} as const;\n")


class Server:
    """Serves one response for every path and records the paths asked for."""

    def __init__(self, status=200, body="", truncate=False):
        self.paths = []
        self.agents = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                outer.paths.append(self.path)
                outer.agents.append(self.headers.get("User-Agent"))
                data = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Length", str(len(data) + (100 if truncate else 0)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.address = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def run(cfg, address, body=None, status=200, truncate=False, server=None):
    """Runs the script in a site folder holding cfg as src/config.ts. With body, serves it first
    and uses the server's address; returns (exit code, output, paths the server saw)."""
    srv = server or (Server(status, body, truncate) if body is not None else None)
    try:
        with tempfile.TemporaryDirectory() as d:
            if cfg is not None:
                (Path(d) / "src").mkdir()
                path = Path(d) / "src" / "config.ts"
                path.write_bytes(cfg if isinstance(cfg, bytes) else cfg.encode("utf-8"))
            r = subprocess.run([sys.executable, "-I", str(SCRIPT), srv.address if srv else address],
                               cwd=d, capture_output=True, text=True, timeout=60)
            return r.returncode, r.stdout + r.stderr, (srv.paths if srv else [])
    finally:
        if srv:
            srv.close()


class OnScriptMode(unittest.TestCase):
    def test_the_page_with_its_tag_passes(self):
        code, out, _ = run(config(), None, GUIDE)
        self.assertEqual(code, 0, out)
        self.assertIn("1 analytics script tag(s), 1 init stub(s), 0 other", out)

    def test_a_page_without_the_tag_fails_with_the_causes(self):
        # The guide's failure of 2026-11-08: config on, live page bare.
        code, out, _ = run(config(), None, BARE)
        self.assertEqual(code, 1, out)
        self.assertIn("0 analytics script tag(s), 0 init stub(s), 0 other", out)
        self.assertIn("WORKERS_CI_BRANCH", out)
        self.assertIn("production branch", out)

    def test_an_older_tag_fails(self):
        code, out, _ = run(config(), None, OLDTAG)
        self.assertEqual(code, 1, out)
        self.assertIn("0 analytics script tag(s), 0 init stub(s), 1 other", out)
        # A tag is there, so "the build had analytics off" would point the owner the wrong way.
        self.assertIn("not the one", out)
        self.assertNotIn("had analytics off", out)

    def test_a_per_site_script_with_another_id_is_another_tag(self):
        # No data-domain here: only the /js/pa-<id>.js address makes it an analytics tag.
        for src in ("https://analytics.example.com/js/pa-Other0000.js", "https://analytics.example.com/js/script.hash.js"):
            with self.subTest(src):
                page = f'<html><head><script async src="{src}"></script><script>plausible.init()</script></head></html>'
                code, out, _ = run(config(), None, page)
                self.assertEqual(code, 1, out)
                self.assertIn("0 analytics script tag(s), 1 init stub(s), 1 other", out)

    def test_the_word_mode_in_comments_does_not_fail_a_healthy_site(self):
        cfg = config().replace("  scriptHost:", "  /* the mode is read below */\n  scriptHost:")
        cfg = cfg.replace("process.env.WORKERS_CI_BRANCH === PROD_BRANCH,", "process.env.WORKERS_CI_BRANCH === PROD_BRANCH, // script mode")
        cfg = cfg.replace("  mode: 'script' as 'script',", "  mode: 'script' as 'script' | 'server', // mode of the tag")
        cfg = cfg.replace("  scriptHost:", "  /* a longer note\n  mode is set below\n  */\n  scriptHost:")
        for text in ("the mode is read", "// script mode", "// mode of the tag", "mode is set below"):
            self.assertIn(text, cfg)
        code, out, _ = run(cfg, None, GUIDE)
        self.assertEqual(code, 0, out)

    def test_a_comment_with_no_end_is_refused(self):
        cfg = config().replace("  scriptHost:", "  /* never closed\n  scriptHost:")
        code, out, _ = run(cfg, None, GUIDE)
        self.assertEqual(code, 2, out)
        self.assertIn("has no end", out)

    def test_no_mode_line_means_script_mode(self):
        cfg = config().replace("  mode: 'script' as 'script',\n", "")
        self.assertNotIn("mode:", cfg)
        code, out, _ = run(cfg, None, GUIDE)
        self.assertEqual(code, 0, out)

    def test_two_scripts_fail(self):
        page = GUIDE.replace("</head>", f'<script async src="{WANT}"></script></head>', 1)
        code, out, _ = run(config(), None, page)
        self.assertEqual(code, 1, out)
        self.assertIn("2 analytics script tag(s), 1 init stub(s)", out)

    def test_a_json_ld_script_naming_the_call_is_not_a_stub(self):
        page = (f'<html><head><script async src="{WANT}"></script>'
                '<script type="application/ld+json">{"x": "plausible.init()"}</script></head></html>')
        code, out, _ = run(config(), None, page)
        self.assertEqual(code, 1, out)
        self.assertIn("1 analytics script tag(s), 0 init stub(s)", out)

    def test_a_call_written_with_a_space_is_a_stub(self):
        page = (f'<html><head><script async src="{WANT}"></script>'
                "<script>plausible.init ()</script></head></html>")
        code, out, _ = run(config(), None, page)
        self.assertEqual(code, 0, out)

    def test_a_commented_out_stub_does_not_count(self):
        page = (f'<html><head><script async src="{WANT}"></script>'
                "<!-- <script>plausible.init()</script> --></head></html>")
        code, out, _ = run(config(), None, page)
        self.assertEqual(code, 1, out)
        self.assertIn("1 analytics script tag(s), 0 init stub(s)", out)

    def test_another_objects_mode_does_not_fail_a_healthy_site(self):
        extra = "export const OTHER = {\n  mode: 'dark',\n};\n"
        code, out, _ = run(config(extra=extra), None, GUIDE)
        self.assertEqual(code, 0, out)

    def test_a_site_without_the_switch_counts_as_on(self):
        code, out, _ = run(config(use=""), None, BARE)
        self.assertEqual(code, 1, out)


class Off(unittest.TestCase):
    OFF = "export const USE_ANALYTICS = false; // not yet"

    def test_a_clean_page_passes(self):
        code, out, _ = run(config(use=self.OFF), None, BARE)
        self.assertEqual(code, 0, out)

    def test_a_page_with_a_tag_fails(self):
        code, out, _ = run(config(use=self.OFF), None, GUIDE)
        self.assertEqual(code, 1, out)
        self.assertIn("carries an analytics tag", out)

    def test_a_page_naming_only_the_id_fails_with_the_second_message(self):
        page = f"<html><body><p>Our id is {SID}.</p></body></html>"
        code, out, _ = run(config(use=self.OFF), None, page)
        self.assertEqual(code, 1, out)
        self.assertIn("names the analytics script or id", out)
        self.assertNotIn("carries an analytics tag", out)

    def test_a_page_naming_only_the_path_fails_with_the_second_message(self):
        page = f"<html><body><p>See {WANT}</p></body></html>"
        code, out, _ = run(config(use=self.OFF), None, page)
        self.assertEqual(code, 1, out)
        self.assertIn("names the analytics script or id", out)


class ServerMode(unittest.TestCase):
    def test_a_page_without_tags_passes(self):
        code, out, _ = run(config(mode="'server'"), None, BARE)
        self.assertEqual(code, 0, out)

    def test_an_older_tag_fails(self):
        code, out, _ = run(config(mode="'server'"), None, OLDTAG)
        self.assertEqual(code, 1, out)
        self.assertIn("browser analytics on the page in server mode", out)


class NotChecked(unittest.TestCase):
    """Exit 2 is never a verdict about the site."""

    def test_a_404(self):
        code, out, _ = run(config(), None, "gone", status=404)
        self.assertEqual((code, "404" in out), (2, True), out)

    def test_a_403_from_a_bot_rule(self):
        code, out, _ = run(config(), None, "no", status=403)
        self.assertEqual((code, "403" in out), (2, True), out)

    def test_an_empty_200(self):
        code, out, _ = run(config(), None, "")
        self.assertEqual(code, 2, out)
        self.assertIn("empty", out)

    def test_a_truncated_answer(self):
        # Content-Length promises more than arrives: an ordinary network event, not a verdict.
        code, out, _ = run(config(), None, GUIDE, truncate=True)
        self.assertEqual(code, 2, out)
        self.assertIn("could not be fetched", out)
        self.assertNotIn("Traceback", out)

    def test_a_config_that_is_not_utf8(self):
        code, out, _ = run(config().encode("utf-8") + b"// \xff\xfe\n", None, GUIDE)
        self.assertEqual(code, 2, out)
        self.assertIn("not UTF-8", out)
        self.assertNotIn("Traceback", out)

    def test_a_mode_it_cannot_read(self):
        for mode in ("getMode()", "'SERVER'"):
            with self.subTest(mode):
                code, out, _ = run(config(mode=mode), None, GUIDE)
                self.assertEqual(code, 2, out)
                self.assertIn("mode:", out)
        for line in ("  mode : 'server',", "  'mode': 'server',", '  "mode": \'server\',',
                     "  mode /* c */: 'server',", "  ['mode']: 'server',", "  mode: 'script' && 'server',",
                     "  [ 'mode' ]: 'server',", "  [`mode`]: 'server',", "  ['mo' + 'de']: 'server',"):
            with self.subTest(line):
                cfg = config().replace("  mode: 'script' as 'script',", line)
                self.assertIn(line, cfg)
                code, out, _ = run(cfg, None, BARE)
                self.assertEqual(code, 2, out)
                self.assertIn("mode:", out)

    def test_a_refused_connection(self):
        s = Server()
        address = s.address
        s.close()
        code, out, _ = run(config(), address)
        self.assertEqual(code, 2, out)
        self.assertIn("could not be fetched", out)

    def test_a_typed_switch_is_not_read_as_on(self):
        code, out, _ = run(config(use="export const USE_ANALYTICS: boolean = false;"), None, BARE)
        self.assertEqual(code, 2, out)
        self.assertIn("USE_ANALYTICS", out)

    def test_two_switch_lines(self):
        cfg = config(use="export const USE_ANALYTICS = true;\nexport const USE_ANALYTICS = false;")
        code, out, _ = run(cfg, None, GUIDE)
        self.assertEqual(code, 2, out)
        self.assertIn("more than one", out)

    def test_no_config_file(self):
        code, out, _ = run(None, None, GUIDE)
        self.assertEqual(code, 2, out)

    def test_an_unknown_mode(self):
        code, out, _ = run(config(mode="'both'"), None, GUIDE)
        self.assertEqual(code, 2, out)

    def test_no_address(self):
        r = subprocess.run([sys.executable, "-I", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


class Request(unittest.TestCase):
    def test_the_request_carries_a_fresh_cb_query(self):
        _, _, first = run(config(), None, GUIDE)
        _, _, second = run(config(), None, GUIDE)
        self.assertEqual(len(first), 1, first)
        self.assertRegex(first[0], r"^/\?cb=[0-9a-f]{6,}$")
        self.assertNotEqual(first, second)

    def test_the_request_names_the_launch_check(self):
        # A bot rule that blocks Python's default agent is why the plan names one.
        srv = Server(200, GUIDE)
        run(config(), None, server=srv)
        self.assertEqual(srv.agents, ["croftweaver-launch-check"])


@unittest.skipUnless(GATE.is_file() or REQUIRE_STARTER, "the starter's gate is not in this checkout")
class AgreesWithTheGate(unittest.TestCase):
    """The starter's gate counts the same tags on a build; on these inputs the counts must agree."""

    @classmethod
    def perl_program(cls):
        text = GATE.read_text(encoding="utf-8")
        m = re.search(r"tags_program\(\) \{\n  cat <<'PERL'\n(.*?)\nPERL\n", text, re.S)
        if not m:
            raise AssertionError("the Perl counter was not found in check_analytics_gate.sh")
        return m.group(1)

    def gate_counts(self, page):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "page.html"
            f.write_text(page, encoding="utf-8")
            r = subprocess.run(["perl", "-e", self.perl_program(), str(f)], capture_output=True, text=True,
                               env={**os.environ, "ANALYTICS_SRC": WANT}, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return tuple(int(n) for n in r.stdout.split()[:3])

    def test_same_counts_on_the_captures_and_edge_pages(self):
        commented = (f'<html><head><script async src="{WANT}"></script>'
                     "<!-- <script>plausible.init()</script> --></head></html>")
        other_id = ('<html><script async src="https://analytics.example.com/js/pa-Other0000.js"></script>'
                    "<script>plausible.init()</script></html>")
        # The gate's Perl reads bytes, so a no-break space is no whitespace and é no word character.
        nbsp = f'<html><script\u00a0src="{WANT}"></script></html>'
        accent = '<html><script src="https://analytics.example.com/js/script.\u00e9.js"></script></html>'
        nbsp_stub = "<html><script\u00a0>plausible.init()</script></html>"
        for name, page, expected in [("guide", GUIDE, (1, 1, 0)), ("webcroft", BARE, (0, 0, 0)),
                                     ("older tag", OLDTAG, (0, 0, 1)), ("comment-only stub", commented, (1, 0, 0)),
                                     ("another id, no data-domain", other_id, (0, 1, 1)),
                                     ("no-break space", nbsp, (0, 0, 0)), ("accented src", accent, (0, 0, 0)),
                                     ("stub after a no-break space", nbsp_stub, (0, 0, 0))]:
            with self.subTest(name):
                self.assertEqual(self.gate_counts(page), expected, "the gate's counter")
                self.assertEqual(cla.count_tags(page, WANT), expected, "check_live_analytics")


if __name__ == "__main__":
    unittest.main()
