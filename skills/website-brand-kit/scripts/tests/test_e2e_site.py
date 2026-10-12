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
import subprocess
import unittest

import _testutil as T
import _palette
from test_install import BAKERY_BRAND_MD, run

SITE = os.environ.get("BRAND_KIT_E2E_SITE")
SEVEN = ("public/favicon.svg", "public/favicon.ico", "public/apple-touch-icon.png", "public/icon-192.png",
         "public/icon-512.png", "public/icon-maskable-512.png", "public/images/logo.png")


@unittest.skipUnless(SITE, "set BRAND_KIT_E2E_SITE to a throwaway, installed copy of the starter (this test changes it)")
class ARealSite(unittest.TestCase):
    def p(self, rel):
        return os.path.join(SITE, *rel.split("/"))

    def test_scenario_8_green_before_the_palette_and_the_logo_go_in_and_green_after_by_the_sites_own_tests(self):
        T.require_sharp(self)
        T.require_pillow(self)
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

        css = _palette.read_css(T.read(self.p("src/styles/global.css")))
        self.assertEqual((css.light, css.dark, css.dark_media), (T.BAKERY_LIGHT, T.BAKERY_DARK, T.BAKERY_DARK))
        self.assertEqual(_palette.drift(_palette.parse_tables(T.read(self.p("BRAND.md"))), css), [])
        for rel in SEVEN:
            self.assertTrue(os.path.isfile(self.p(rel)), rel)
        # the build the tests ran against was made after the install: it serves the new mark and the new colours
        self.assertEqual(T.read_bytes(self.p("dist/favicon.svg")), T.read_bytes(self.p("public/favicon.svg")))
        self.assertEqual(T.read_bytes(self.p("dist/icon-maskable-512.png")), T.read_bytes(self.p("public/icon-maskable-512.png")))
        built_css = "".join(T.read(os.path.join(d, n)) for d, _s, names in os.walk(self.p("dist")) for n in names if n.endswith((".css", ".html")))
        self.assertIn(T.BAKERY_LIGHT["bg"], built_css)
        self.assertIn(T.BAKERY_DARK["bg"], built_css)


if __name__ == "__main__":
    unittest.main()
