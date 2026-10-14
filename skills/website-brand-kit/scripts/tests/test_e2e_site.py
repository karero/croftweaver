"""Scenario 8, through the door the owner uses: a real site, its real `npm run build && npm test`.

Every other test stands a command in for the site's tests, so that red can be made on demand. This one
does not: it takes a copy of the starter that has been installed (`npm ci`, Playwright's browser), sees
that its own tests are green, runs the intake with no test command of its own, and looks at what the
site's build then serves. It takes minutes and changes the site it is given, so it runs only when
BRAND_KIT_E2E_SITE names a throwaway copy:

  cp -R skills/new-website/templates/astro /tmp/site && cd /tmp/site && npm ci && npx playwright install chromium
  BRAND_KIT_E2E_SITE=/tmp/site python3 -m unittest discover -s skills/website-brand-kit/scripts/tests -p 'test_e2e_site.py'
"""

import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import unittest

import _testutil as T
import _install
import _palette
from test_install import BAKERY_BRAND_MD, run

SITE = os.environ.get("BRAND_KIT_E2E_SITE")
SEVEN = ("public/favicon.svg", "public/favicon.ico", "public/apple-touch-icon.png", "public/icon-192.png",
         "public/icon-512.png", "public/icon-maskable-512.png", "public/images/logo.png")


def preview_port(site):
    """The port the site's tests serve its build on: playwright.config.ts works it out from SITE.url (FNV-1a, 32 bit)."""
    url = re.search(r"(?m)^\s*url:\s*'([^']*)'", T.read(os.path.join(site, "src", "config.ts"))).group(1)
    h = 2166136261
    for ch in url:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return 4330 + h % 670


def serving(port):
    """Whether something answers on that port of this computer."""
    try:
        socket.create_connection(("localhost", port), timeout=2).close()
        return True
    except OSError:
        return False


def previews():
    """The preview servers running on this computer, as `ps` shows them: [(process id, command)]."""
    listing = subprocess.run(["ps", "-Ao", "pid=,command="], capture_output=True, text=True, errors="replace").stdout
    return [(int(l.split()[0]), l.split(None, 1)[1]) for l in listing.splitlines() if "astro" in l and " preview" in l and "--port %d" % preview_port(SITE) in l]


@unittest.skipUnless(SITE, "set BRAND_KIT_E2E_SITE to a throwaway, installed copy of the starter (this test changes it)")
class ARealSite(unittest.TestCase):
    def p(self, rel):
        return os.path.join(SITE, *rel.split("/"))

    def test_scenario_8_green_before_the_palette_and_the_logo_go_in_and_green_after_by_the_sites_own_tests(self):
        T.require_sharp(self)
        T.require_pillow(self)
        self.assertFalse(serving(preview_port(SITE)), "something is already serving on the site's preview port, so its tests cannot run")
        before = subprocess.run("npm run build && npm test", shell=True, cwd=SITE, capture_output=True, text=True)
        self.assertEqual(before.returncode, 0, "the site must be green before the install, or the run says nothing about the palette:\n"
                         + (before.stdout + before.stderr)[-3000:])
        with open(self.p("BRAND.md"), "w", encoding="utf-8") as f:
            f.write(BAKERY_BRAND_MD)
        pack = self.p("../brand-kit-e2e-logo.zip")
        with open(pack, "wb") as f:
            f.write(T.real_zip_bytes())
        self.addCleanup(os.remove, pack)

        # no --test-command: the intake runs what the owner runs. --with-colours: a logo and a palette that
        # changes the site's colours go in together only when she has said so.
        code, out = run("install", "--site", SITE, "--input", pack, "--pick", T.REAL_COLOUR, "--mono", T.REAL_MONO,
                        "--with-colours", "--accept-colours", "--accept-low-contrast", "dark", "--json")
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["tests"]), (0, "done", "passed"), "\n".join(data.get("report", [])) + str(data.get("failing")))
        self.assertEqual(data["cards"], "regenerated")
        # after writing, and before the site's tests ran, the site's own Node and Python said what they read from the two
        # files this tool edits by line: what the report says of the theme colour, the logo's address and the cards rests on that
        self.assertEqual(data["read_back"], {"src/config.ts": {"status": "ok"}, "scripts/generate_og_cards.py": {"status": "ok"}})
        self.assertEqual([n for n in data["notes"] if "could not check" in n], [])
        # the tests started a preview server and stopped it themselves; the intake left them the time, and nothing of it is left
        self.assertFalse(serving(preview_port(SITE)), "the site's preview port is still served after the run")
        self.assertEqual(previews(), [])
        # the share cards' emblem is not this tool's: the generator's line is as the starter has it, and the report says so in one line
        self.assertIn("\nLOGO = None ", T.read(self.p("scripts/generate_og_cards.py")))
        self.assertEqual(len([n for n in data["notes"] if n.startswith("the share cards get no emblem from this tool")]), 1)

        css = _palette.read_css(T.read(self.p("src/styles/global.css")))
        self.assertEqual((css.light, css.dark, css.dark_media), (T.BAKERY_LIGHT, T.BAKERY_DARK, T.BAKERY_DARK))
        self.assertEqual(_palette.drift(_palette.parse_tables(T.read(self.p("BRAND.md"))), css), [])
        for rel in SEVEN:
            self.assertTrue(os.path.isfile(self.p(rel)), rel)
        # the build the tests ran against was made after the install: it serves the new mark and the new colours
        self.assertEqual(T.read_bytes(self.p("dist/favicon.svg")), T.read_bytes(self.p("public/favicon.svg")))
        # the favicon starts with the line this tool knows its own file by, and the site's tests were green with it
        self.assertTrue(T.read_bytes(self.p("dist/favicon.svg")).startswith(_install.MARK.encode("utf-8")))
        self.assertEqual(T.read_bytes(self.p("dist/icon-maskable-512.png")), T.read_bytes(self.p("public/icon-maskable-512.png")))
        built_css = "".join(T.read(os.path.join(d, n)) for d, _s, names in os.walk(self.p("dist")) for n in names if n.endswith((".css", ".html")))
        self.assertIn(T.BAKERY_LIGHT["bg"], built_css)
        self.assertIn(T.BAKERY_DARK["bg"], built_css)
        # what the report says it set outside the stylesheet is what the built site carries: the theme colour
        # in the pages' heads (Astro read src/config.ts), and the manifest's two colours
        if "src/config.ts" in data["written"]:
            self.assertIn("src/config.ts, themeColor: #000000 becomes #b4531a", data["changes"])
        self.assertRegex(built_css, r'<meta name="theme-color" content="#b4531a"')
        self.assertNotRegex(built_css, r'<meta name="theme-color" content="#000000"')
        served = json.loads(T.read(self.p("dist/manifest.webmanifest")))
        self.assertEqual((served["theme_color"], served["background_color"]), ("#b4531a", T.BAKERY_LIGHT["bg"]))

    @unittest.skipUnless(os.name == "posix", "a stop from outside is a signal, and the processes are looked for with ps")
    def test_a_stop_from_outside_while_the_sites_real_tests_serve_the_build_ends_the_preview_server_too_and_puts_every_file_back(self):
        # The real `npm run build && npm test`: npm starts Playwright, Playwright starts the build and the
        # preview server in a session of its own. Killed at once, Playwright could not stop that server, and it
        # kept the site's port for every later `npm test`. It is told to end first, and what is still there
        # after the grace is stopped by its own number.
        T.require_pillow(self)
        port = preview_port(SITE)
        self.assertFalse(serving(port), "something is already serving on the site's preview port, so its tests cannot run")
        kept = ("src/styles/global.css", "src/config.ts", "public/manifest.webmanifest", "scripts/generate_og_cards.py", "public/images/og/default.jpg")
        before = {rel: T.read_bytes(self.p(rel)) for rel in kept}
        had_brand = os.path.exists(self.p("BRAND.md"))
        with open(self.p("BRAND.md"), "w", encoding="utf-8") as f:
            f.write(BAKERY_BRAND_MD)
        if not had_brand:
            self.addCleanup(os.remove, self.p("BRAND.md"))
        cli = os.path.join(T.SCRIPTS, "brand_intake.py")
        p = subprocess.Popen([sys.executable, cli, "install", "--site", SITE, "--json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        try:
            end = time.time() + 900
            while not serving(port) and p.poll() is None and time.time() < end:
                time.sleep(0.05)
            self.assertIsNone(p.poll(), "the run ended before the site's tests served the build: %s" % (p.stdout.read() if p.poll() is not None else ""))
            self.assertTrue(serving(port), "the preview server never came up")
            server = previews()
            p.send_signal(signal.SIGTERM)
            out, err = p.communicate(timeout=300)
        finally:
            if p.poll() is None:
                p.kill()
        data = json.loads(out)
        self.assertEqual((p.returncode, err, data["status"], data["written"], data.get("not_restored")), (2, "", "stopped", [], None), "\n".join(data["report"]))
        self.assertIn("The run was stopped from outside (SIGTERM) before it had finished, and what it had started was stopped with it as far as this tool could find it.", data["report"])
        self.assertIn("Everything it had written was put back.", data["report"])
        self.assertTrue(server, "the preview server was seen in ps while it served")
        end = time.time() + 30
        while (serving(port) or previews()) and time.time() < end:
            time.sleep(0.2)
        self.assertFalse(serving(port), "the preview server still holds the site's port")
        self.assertEqual(previews(), [], "the preview server is still running")
        self.assertEqual({rel: T.read_bytes(self.p(rel)) for rel in kept}, before)


if __name__ == "__main__":
    unittest.main()
