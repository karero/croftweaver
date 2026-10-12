"""Scenarios 8, 16, 19, 21, 26 (the path), 27, 30, 31, 34, 35, 36 to 39 and the rest of 7, 9, 15, 29: the
intake as a whole, through the door the assistant uses (`brand_intake.main`, the same function the
command line calls), on a real copy of the starter.

The site's own tests are stood in for by a command that prints what Playwright prints, so that red can be
made on demand; the one run that uses `npm test` for real is test_e2e_site.py.
"""

import contextlib
import hashlib
import io
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest

import _testutil as T
import brand_intake
import _colour
import _install
import _palette
import _site
import _svg
from test_palette import LABELS, STARTER_DARK, STARTER_LIGHT, table
from test_site_edits import bakery, tree

GREEN = "true"
# what Playwright's list reporter prints for a failure (octal escapes: every sh's printf reads them)
RED = ("printf '  1) [chromium] \\342\\200\\272 tests/a11y.spec.ts:8:5 \\342\\200\\272 a11y \\342\\200\\224 / [dark] \\342\\224\\200\\342\\224\\200\\n"
       "  2) [chromium] \\342\\200\\272 tests/seo.spec.ts:20:3 \\342\\200\\272 theme colour\\n'; exit 1")
BAKERY_BRAND_MD = (
    "# Bäckerei Example: brand & style guide\n\n## Colour palette\n\n### Brand (fixed, theme-independent)\n"
    "| Token | Hex | Use |\n|---|---|---|\n| Primary | `#b4531a` | buttons, brand surfaces |\n\n"
    "### Light theme\n" + table([(l, T.BAKERY_LIGHT[k]) for k, l in LABELS]) + "\n"
    "### Dark theme\n" + table([(l, T.BAKERY_DARK[k]) for k, l in LABELS]))
# A dark theme that passes all its pairs and still cannot be read on a share card: grey text that reads on
# the white surface and on the black background, and not on the greys the card's gradient runs through.
GREY_DARK = dict(T.BAKERY_DARK, heading="#767676", ink="#767676", muted="#767676", accent="#767676", link="#767676",
                 bg="#000000", bg_soft="#000000", surface="#ffffff")
LOGO_ARGS = ("--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both")
# What `npm test` printed on an installed copy of the starter with public/llms.txt moved away (Playwright
# 1.63, the list reporter the starter configures), 2026-10-12: the lines around the four failures, with the
# folder's path shortened to /site. The first three headings end in a space, the fourth in a rule.
PLAYWRIGHT_RED = "\n".join((
    "  \u2713  68 [chromium] \u203a tests/seo.spec.ts:428:1 \u203a seo \u2014 hosted PDFs carry a descriptive doc-title (1ms)",
    "  \u2718  60 [chromium] \u203a tests/seo.spec.ts:329:1 \u203a robots.txt stays open and llms.txt exists (5ms)",
    "",
    "",
    "  1) [chromium] \u203a tests/llms-coverage.spec.ts:59:1 \u203a every PAGES route is listed in public/llms.txt ",
    "",
    "    Error: ENOENT: no such file or directory, open '/site/public/llms.txt'",
    "",
    "      37 | // is exactly how false positives creep in \u2014 so they don't.",
    "      38 | function linkedPaths(): string[] {",
    "    > 39 |   const txt = readFileSync(join(process.cwd(), 'public', 'llms.txt'), 'utf8');",
    "         |               ^",
    "        at linkedPaths (/site/tests/llms-coverage.spec.ts:39:15)",
    "",
    "    Error Context: test-results/llms-coverage-every-PAGES-route-is-listed-in-public-llms-txt-chromium/error-context.md",
    "",
    "  2) [chromium] \u203a tests/llms-coverage.spec.ts:72:1 \u203a no stale llms.txt entry \u2014 every same-site page link is a PAGES route ",
    "",
    "    Error: ENOENT: no such file or directory, open '/site/public/llms.txt'",
    "",
    "  3) [chromium] \u203a tests/llms-coverage.spec.ts:91:1 \u203a LLMS_EXEMPT routes stay out of public llms.txt ",
    "",
    "    Error: ENOENT: no such file or directory, open '/site/public/llms.txt'",
    "",
    "  4) [chromium] \u203a tests/seo.spec.ts:329:1 \u203a robots.txt stays open and llms.txt exists " + "\u2500" * 14,
    "",
    "    Error: public/llms.txt (the AI answer-engine index) must be served",
    "",
    "    Expected: 200",
    "    Received: 404",
    "",
    "  4 failed",
    "    [chromium] \u203a tests/llms-coverage.spec.ts:59:1 \u203a every PAGES route is listed in public/llms.txt \u2500",
    "    [chromium] \u203a tests/seo.spec.ts:329:1 \u203a robots.txt stays open and llms.txt exists " + "\u2500" * 15,
    "  1 skipped",
    "  63 passed (5.9s)",
    ""))
PLAYWRIGHT_RED_NAMES = ["tests/llms-coverage.spec.ts:59:1 \u203a every PAGES route is listed in public/llms.txt",
                        "tests/llms-coverage.spec.ts:72:1 \u203a no stale llms.txt entry \u2014 every same-site page link is a PAGES route",
                        "tests/llms-coverage.spec.ts:91:1 \u203a LLMS_EXEMPT routes stay out of public llms.txt",
                        "tests/seo.spec.ts:329:1 \u203a robots.txt stays open and llms.txt exists"]


def rects(*shapes):
    """A small SVG of rectangles, each (x, y, width, height, fill), later ones over earlier ones."""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            + "".join('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>' % shape for shape in shapes) + "</svg>").encode("utf-8")


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = brand_intake.main(list(argv))
    return code, out.getvalue()


class SiteCase(unittest.TestCase):
    modules = True

    def setUp(self):
        if self.modules:
            T.require_sharp(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.site = T.make_starter_site(os.path.join(self.tmp.name, "site"), with_modules=self.modules)
        self.pack = os.path.join(self.tmp.name, "pack")
        os.makedirs(self.pack)

    def p(self, rel):
        return os.path.join(self.site, *rel.split("/"))

    def read(self, rel):
        return T.read(self.p(rel))

    def bytes(self, rel):
        return T.read_bytes(self.p(rel))

    def exists(self, rel):
        return os.path.exists(self.p(rel))

    def brand_md(self, text=BAKERY_BRAND_MD):
        with open(self.p("BRAND.md"), "w", encoding="utf-8") as f:
            f.write(text)

    def package(self, name="logo.zip", data=None):
        path = os.path.join(self.pack, name)
        with open(path, "wb") as f:
            f.write(data if data is not None else T.real_zip_bytes())
        return path

    def intake(self, *extra, command=GREEN, brand=True):
        if brand and not self.exists("BRAND.md"):
            self.brand_md()
        return run("install", "--site", self.site, "--test-command", command, *extra)

    def snapshot(self):
        return tree(self.site)

    def put(self, rel, data):
        with open(self.p(rel), "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode("utf-8"))

    def not_as_root(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root may read and write anywhere, so nothing can be closed to it")

    def closed(self, rel, mode=0):
        """Close a file or folder of the site to this account until the test is over; returns the mode it had."""
        was = stat.S_IMODE(os.stat(self.p(rel)).st_mode)
        os.chmod(self.p(rel), mode)
        self.addCleanup(lambda: os.path.lexists(self.p(rel)) and os.chmod(self.p(rel), was))
        return was

    def both_runs(self, *extra, **kwargs):
        """A dry run and then a real run of the same command: [(code, what it printed)]. They must agree on
        every refusal, so most tests of one ask both."""
        return [self.intake(*extra, "--dry-run", **kwargs), self.intake(*extra, **kwargs)]

    def links(self):
        """Every link in the site (node_modules aside) with what it points at: a link must stay a link."""
        out = {}
        for base, dirs, files in os.walk(self.site):
            for n in dirs + files:
                if os.path.islink(os.path.join(base, n)) and n != "node_modules":
                    out[os.path.relpath(os.path.join(base, n), self.site)] = os.readlink(os.path.join(base, n))
        return out

    def drive(self, patch, *extra, command=GREEN, ignored=(), tmpdir=None):
        """The whole command line as a process of its own, because a signal ends a process that does not
        catch it. `patch` is Python run before the command line is: it puts a signal at an exact moment.
        The process starts with each signal as a shell would hand it over, or ignored when `ignored` names it."""
        def signals():
            for name in ("SIGINT", "SIGHUP", "SIGTERM"):
                signal.signal(getattr(signal, name), signal.SIG_IGN if name in ignored else signal.SIG_DFL)
        program = "import os, signal, sys\nsys.path.insert(0, %r)\nimport brand_intake, _install, _site, _icons\n%s\nsys.exit(brand_intake.main(sys.argv[1:]))\n" % (T.SCRIPTS, patch)
        env = dict(os.environ, TMPDIR=tmpdir) if tmpdir else None
        return subprocess.run([sys.executable, "-c", program, "install", "--site", self.site, "--test-command", command] + list(extra),
                              capture_output=True, text=True, encoding="utf-8", timeout=180, preexec_fn=signals, env=env)

    def gone(self, pid, wait=5.0):
        """Whether a process has ended (given a moment: one that was killed is not gone at once)."""
        end = time.time() + wait
        while time.time() < end:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            except PermissionError:
                return False
            time.sleep(0.05)
        return False

    def sleeper(self):
        """A command that would run for five minutes, told apart from every other by its length, and a
        way to ask afterwards whether it is still running."""
        length = "300.%06d" % (int.from_bytes(os.urandom(3), "big") % 1000000)

        def running():
            listing = subprocess.run(["ps", "-Ao", "pid=,command="], capture_output=True, text=True).stdout
            return [int(line.split()[0]) for line in listing.splitlines() if line.strip().endswith("sleep " + length)]

        def stop():
            for pid in running():
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
        self.addCleanup(stop)
        return "sleep " + length, running

    def none_left(self, running, wait=5.0):
        end = time.time() + wait
        while running() and time.time() < end:
            time.sleep(0.05)
        return running() == []

    def stop_leftovers(self, pid_file):
        """Tidy up after a test that expects the intake to stop what a command started: whatever it left."""
        if os.path.exists(pid_file):
            for pid in T.read(pid_file).split():
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except OSError:
                    pass


class OnlyColours(SiteCase):
    """Scenarios 38 and 8: she has a palette and wants no help with a logo."""
    modules = False  # a run with only colours needs no sharp (scenario 19)

    def test_a_dry_run_says_what_it_would_do_and_writes_nothing(self):
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("Dry run", out)
        self.assertIn("src/styles/global.css", out)
        self.assertEqual(self.snapshot(), before)

    def test_the_palette_is_written_everywhere_it_belongs_and_the_logo_things_stay(self):
        T.require_pillow(self)
        og_before = self.bytes("public/images/og/default.jpg")
        config_before = self.read("src/config.ts")
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        css = _palette.read_css(self.read("src/styles/global.css"))
        self.assertEqual((css.light, css.dark, css.dark_media, css.brand), (T.BAKERY_LIGHT, T.BAKERY_DARK, T.BAKERY_DARK, "#b4531a"))
        self.assertIn("themeColor: '#b4531a'", self.read("src/config.ts"))
        manifest = json.loads(self.read("public/manifest.webmanifest"))
        self.assertEqual((manifest["theme_color"], manifest["background_color"]), ("#b4531a", "#fff8ee"))
        self.assertRegex(self.read("scripts/generate_og_cards.py"), r"(?m)^BG_BOT = \(26, 18, 13\)")
        self.assertIn("LOGO = None", self.read("scripts/generate_og_cards.py"))
        self.assertEqual(self.read("src/config.ts").replace("'#b4531a'", "'#000000'"), config_before, "COMPANY.logo is as the starter has it")
        for gone in ("public/favicon.svg", "public/favicon.ico", "public/apple-touch-icon.png", "public/icon-192.png",
                     "public/icon-512.png", "public/icon-maskable-512.png", "public/images/logo.png", "brand-handoff"):
            self.assertFalse(self.exists(gone), gone)
        self.assertNotIn("brand-handoff", self.read(".gitignore"))
        self.assertNotEqual(self.bytes("public/images/og/default.jpg"), og_before, "the share card has the new colours")
        self.assertEqual(self.read("BRAND.md"), BAKERY_BRAND_MD, "BRAND.md is the source; the run leaves it alone")

    def test_the_share_cards_are_real_pictures_at_the_size_the_tests_demand(self):
        T.require_pillow(self)
        self.intake()
        data = self.bytes("public/images/og/default.jpg")
        self.assertEqual(data[:3], b"\xff\xd8\xff")
        self.assertLessEqual(len(data), 300 * 1024)

    def test_the_document_and_the_stylesheet_agree_afterwards(self):
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        css = _palette.read_css(self.read("src/styles/global.css"))
        self.assertEqual(_palette.drift(_palette.parse_tables(self.read("BRAND.md")), css), [])
        self.assertEqual(_palette.dark_blocks_disagree(css), [])

    def test_a_failing_pair_stops_it_before_anything_is_written(self):
        # scenario 7, the second time it is checked: inside the intake
        self.brand_md(BAKERY_BRAND_MD.replace(T.BAKERY_DARK["muted"], "#5c5f80"))
        before = self.snapshot()
        code, out = self.intake()
        self.assertEqual(code, 1, out)
        self.assertIn("FAILS dark: Muted #5c5f80", out)
        self.assertIn("4.5 to 1", out)
        self.assertEqual(self.snapshot(), before)

    def test_proposed_values_stop_it_until_she_has_confirmed_them(self):
        # scenario 9: the intake writes only values she confirmed
        self.brand_md(BAKERY_BRAND_MD.replace("`%s`" % T.BAKERY_DARK["muted"], "`%s (proposed)`" % T.BAKERY_DARK["muted"]))
        before = self.snapshot()
        code, out = self.intake()
        self.assertEqual(code, 3, out)
        self.assertIn("confirm", out.lower())
        self.assertEqual(self.snapshot(), before)

    def test_an_incomplete_palette_is_not_applied_and_asking_for_colours_says_so(self):
        self.brand_md(BAKERY_BRAND_MD.replace("| Soft background | `#fef5e8` |\n", ""))
        before = self.snapshot()
        code, out = self.intake("--with-colours")
        self.assertEqual(code, 2, out)
        self.assertIn("Soft background", out)
        self.assertEqual(self.snapshot(), before)

    def test_with_neither_colours_nor_a_logo_there_is_nothing_to_do_and_it_says_so(self):
        before = self.snapshot()
        code, out = self.intake(brand=False)
        self.assertEqual(code, 2, out)
        self.assertIn("nothing to do", out.lower())
        self.assertEqual(self.snapshot(), before)

    def test_red_tests_put_everything_back_and_name_the_failing_check(self):
        # scenario 31
        T.require_pillow(self)
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake(command=RED)
        self.assertEqual(code, 1, out)
        self.assertEqual(self.snapshot(), before, "every file, the share cards included, is as it was")
        self.assertIn("a11y.spec.ts", out)
        self.assertIn("put back", out)
        # the same suite is red with the install taken out again, and the report says that and no more:
        # it did not see the site before this run, so it does not say how the site was then
        self.assertIn("With the install taken out again, the same tests still fail.", out)
        self.assertNotIn("before this run", out)

    def test_when_the_tests_are_red_with_the_install_and_green_once_it_is_taken_out_the_report_says_what_it_saw_and_blames_nothing(self):
        # a second run that passes shows the tests pass now, not that the install was the cause (a test
        # that fails every other time looks the same)
        self.brand_md()
        marker = os.path.join(self.tmp.name, "ran-once")
        flip = "if [ -e %s ]; then exit 0; else touch %s; printf '  1) [chromium] x tests/a11y.spec.ts\\n'; exit 1; fi" % (marker, marker)
        code, out = self.intake(command=flip)
        self.assertEqual(code, 1, out)
        self.assertIn("With the install taken out again, the same tests pass.", out)
        self.assertNotIn("it was the install", out)

    def test_a_generator_that_fails_leaves_the_old_cards_and_says_what_to_run(self):
        # scenario 35: the generator writes the cards one after another and can stop on a later one
        self.brand_md()
        gen = self.read("scripts/generate_og_cards.py")
        self.assertIn("def main():", gen)
        broken = gen.replace("def main():\n", "def main():\n    (OUT / 'default.jpg').write_bytes(b'half way')\n    raise SystemExit('simulated: a later card failed')\n", 1)
        with open(self.p("scripts/generate_og_cards.py"), "w", encoding="utf-8") as f:
            f.write(broken)
        old = self.bytes("public/images/og/default.jpg")
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.bytes("public/images/og/default.jpg"), old, "the whole folder is restored")
        self.assertIn("still show the old colours", out)
        self.assertIn("npm run og", out)
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT, "the colours themselves are in")

    def test_a_palette_alone_leaves_the_scaffolds_placeholder_icons_where_they_are(self):
        # scenario 38: the placeholder is not a logo, so a run with only colours makes no icons from it
        # (without sharp, as here, it could not; it must not even try)
        placeholder = b"<svg>placeholder</svg>"
        with open(self.p("public/favicon.svg"), "wb") as f:
            f.write(placeholder)
        old = _site.SCAFFOLD_DEFAULTS
        _site.SCAFFOLD_DEFAULTS = {"public/favicon.svg": {hashlib.sha256(placeholder).hexdigest()}}
        try:
            code, out = self.intake()
        finally:
            _site.SCAFFOLD_DEFAULTS = old
        self.assertEqual(code, 0, out)
        self.assertEqual(self.bytes("public/favicon.svg"), placeholder)
        self.assertFalse(self.exists("public/images/logo.png"))
        self.assertIn("LOGO = None", self.read("scripts/generate_og_cards.py"))

    def test_a_palette_without_a_primary_row_uses_the_accent_as_the_theme_colour_and_says_so(self):
        self.brand_md(BAKERY_BRAND_MD.replace("| Primary | `#b4531a` | buttons, brand surfaces |\n", ""))
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        self.assertIn("no Primary row", out)
        self.assertIn("themeColor: '%s'" % T.BAKERY_LIGHT["accent"], self.read("src/config.ts"))

    def test_scenario_29_a_stylesheet_that_does_not_carry_the_palette_in_all_three_places_is_not_kept(self):
        # the check on the file the intake wrote, the last guard after the same check on the planned text:
        # here the writing is broken on purpose, so that what lands in the file is not what was planned.
        # Once it is the block for visitors without JavaScript (which the site's own a11y test never
        # exercises) that keeps an old value, once the Primary.
        self.brand_md()
        before = self.snapshot()
        real = _site.Journal.write
        for name, planned, landed, found in (("the block for visitors without JavaScript", "--bg: %s;" % T.BAKERY_DARK["bg"], "--bg: #0a0b1e;",
                                              "Background, dark theme for visitors without JavaScript is #0a0b1e, not #1a120d"),
                                             ("the Primary", "--brand: #b4531a;", "--brand: #000000;", "Primary is #000000, not #b4531a"),
                                             ("a value that cannot be read", "--brand: #b4531a;", "--brand: bakery-brown;", "--brand in the :root block: The colour 'bakery-brown'")):
            with self.subTest(name=name):
                def broken(journal, rel, data, planned=planned, landed=landed):
                    if rel == "src/styles/global.css":
                        head, found, tail = data.decode("utf-8").rpartition(planned)
                        self.assertTrue(found)
                        data = (head + landed + tail).encode("utf-8")
                    return real(journal, rel, data)
                _site.Journal.write = broken
                try:
                    code, out = self.intake()
                finally:
                    _site.Journal.write = real
                self.assertEqual(code, 2, out)
                self.assertIn("all three places", out)
                self.assertIn(found, out)
                self.assertIn("put back", out)
                self.assertNotIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)

    def test_asking_for_a_logo_when_there_is_none_stops_and_says_so(self):
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--with-logo")
        self.assertEqual(code, 2, out)
        self.assertIn("no logo to apply", out)
        self.assertEqual(self.snapshot(), before)

    def test_a_site_that_is_not_the_starters_layout_is_refused_whole(self):
        self.brand_md()
        with open(self.p("src/styles/global.css"), "w", encoding="utf-8") as f:
            f.write(self.read("src/styles/global.css").replace(':root[data-theme="dark"] {', ":root.night {"))
        before = self.snapshot()
        code, out = self.intake()
        self.assertEqual(code, 2, out)
        self.assertIn("global.css", out)
        self.assertEqual(self.snapshot(), before)

    def test_a_folder_that_is_not_a_site_is_named(self):
        empty = os.path.join(self.tmp.name, "empty")
        os.makedirs(empty)
        code, out = run("install", "--site", empty, "--test-command", GREEN)
        self.assertEqual(code, 2)
        self.assertIn("generate_og_cards.py", out)

    def test_json_for_the_assistant(self):
        T.require_pillow(self)
        self.brand_md()
        code, out = self.intake("--json")
        data = json.loads(out)
        self.assertEqual((data["status"], data["exit"]), ("done", 0))
        self.assertIn("src/styles/global.css", data["written"])
        self.assertEqual(data["tests"], "passed")
        self.assertEqual(data["cards"], "regenerated")
        before = self.snapshot()
        code, out = self.intake("--json", "--dry-run")
        self.assertEqual(json.loads(out)["status"], "dry-run")
        self.assertEqual(self.snapshot(), before)

    # --- what is said -------------------------------------------------------------------------

    def test_every_report_the_dry_run_too_lists_the_stylesheet_values_that_change(self):
        self.brand_md()
        self.assertIn("Primary: #000000 becomes #b4531a", json.loads(self.intake("--json", "--dry-run")[1])["changes"])
        for extra, heading in ((("--dry-run",), "Colours that would change in src/styles/global.css:"), ((), "Colours that changed in src/styles/global.css:")):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 0, out)
                self.assertIn(heading, out)
                for line in ("  Primary: #000000 becomes #b4531a", "  Accent, light theme: #2b50e0 becomes #b4531a", "  Link, light theme: #2b50e0 becomes #a14a14",
                             "  Background, dark theme: #0a0b1e becomes #1a120d"):
                    self.assertIn(line, out.splitlines())
                self.assertNotIn("without JavaScript: #", out, "a dark row that both dark blocks have alike is named once")
        code, out = self.intake("--json")
        self.assertEqual(json.loads(out)["changes"], [], "and a second run changes no value")

    def test_a_dark_value_that_only_the_block_for_visitors_without_javascript_has_differently_is_named_for_that_block(self):
        self.brand_md()
        head, sep, media = self.read("src/styles/global.css").partition("@media (prefers-color-scheme: dark)")
        self.put("src/styles/global.css", head + sep + media.replace("--muted: #a6abce;", "--muted: #999999;", 1))
        code, out = self.intake("--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("  Muted, dark theme: #a6abce becomes #c4ae98", out.splitlines())
        self.assertIn("  Muted, dark theme for visitors without JavaScript: #999999 becomes #c4ae98", out.splitlines())

    def test_when_the_generator_fails_the_report_does_not_say_the_palette_is_in_the_share_cards_and_names_pillow_only_when_that_is_what_is_missing(self):
        T.require_pillow(self)   # without it every failure here would be the missing library
        self.brand_md()
        gen = self.read("scripts/generate_og_cards.py")
        for name, said, pillow in (("the library is missing", "Pillow is required: pip3 install Pillow  (one-time, local only)", True),
                                   ("something else", "simulated: a title is too long", False)):
            with self.subTest(name=name):
                self.put("scripts/generate_og_cards.py", gen.replace("def main():\n", "def main():\n    raise SystemExit(%r)\n" % said, 1))
                code, out = self.intake()
                self.assertEqual(code, 0, out)
                self.assertIn("in the theme colour and the manifest. The share cards do not have it: see below.", out)
                self.assertNotIn("and in the share cards", out)
                self.assertIn("still show the old colours", out)
                self.assertIn("run: npm run og", out)
                self.assertEqual("pip3 install Pillow" in out, pillow, out)
                self.assertEqual("Pillow" in out, pillow, out)

    def test_the_card_generator_is_told_to_write_utf8_whatever_the_shell_around_it_says(self):
        # the generator prints an arrow, which the encoding a Windows pipe gets (cp1252) does not hold
        T.require_pillow(self)
        self.brand_md()
        old = os.environ.get("PYTHONIOENCODING")
        os.environ["PYTHONIOENCODING"] = "cp1252"
        try:
            code, out = self.intake("--json")
        finally:
            if old is None:
                del os.environ["PYTHONIOENCODING"]
            else:
                os.environ["PYTHONIOENCODING"] = old
        data = json.loads(out)
        self.assertEqual((code, data["cards"], data.get("cards_why")), (0, "regenerated", None))

    def test_a_node_that_cannot_be_started_is_a_card_failure_said_in_words(self):
        self.brand_md()
        real = _install.shutil.which
        _install.shutil.which = lambda name, *a, **k: os.path.join(self.tmp.name, "no-such-node") if name == "node" else real(name, *a, **k)
        try:
            code, out = self.intake()
        finally:
            _install.shutil.which = real
        self.assertEqual(code, 0, out)
        self.assertIn("the generator could not be started", out)
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT, "the colours themselves are in")

    def test_red_tests_that_print_nothing_are_said_so_and_the_cards_are_reported_as_put_back(self):
        T.require_pillow(self)
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--json", command="exit 1")
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["tests"], data["failing"]), (1, "tests-failed", "failed", []))
        self.assertEqual(data["cards"], "restored", "they were regenerated, and then put back with everything else")
        self.assertEqual([l for l in data["report"] if l.startswith("The failing check")], [])
        self.assertTrue(any("printed nothing" in l and "exit 1" in l for l in data["report"]), data["report"])
        self.assertEqual(self.snapshot(), before)

    def test_the_failing_checks_are_read_from_what_playwrights_list_reporter_really_prints(self):
        self.assertEqual(_install.failing_checks(PLAYWRIGHT_RED), PLAYWRIGHT_RED_NAMES)
        self.brand_md()
        log = os.path.join(self.tmp.name, "npm-test.log")
        with open(log, "w", encoding="utf-8") as f:
            f.write(PLAYWRIGHT_RED)
        code, out = self.intake("--json", command="cat '%s'; exit 1" % log)
        self.assertEqual(code, 1, out)
        self.assertEqual(json.loads(out)["failing"], PLAYWRIGHT_RED_NAMES)

    # --- what she asked for, checked before anything else ---------------------------------------

    def test_an_unknown_theme_to_accept_is_refused_on_a_run_with_only_colours_too(self):
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--accept-low-contrast", "purple")
        self.assertEqual(code, 2, out)
        self.assertIn("purple", out)
        self.assertEqual(self.snapshot(), before)

    def test_pick_or_mono_without_a_package_is_refused_by_name_not_ignored(self):
        self.brand_md()
        before = self.snapshot()
        for flags, said in ((("--pick", "a.svg"), "--pick can only be used with a package"), (("--mono", "a-mono.svg"), "--mono can only be used with a package"),
                            (("--pick", "a.svg", "--mono", "a-mono.svg"), "--pick and --mono can only be used with a package")):
            with self.subTest(flags=flags):
                code, out = self.intake(*flags)
                self.assertEqual(code, 2, out)
                self.assertIn(said, out)
                self.assertIn("--input", out)
                self.assertEqual(self.snapshot(), before)

    def test_asking_to_apply_the_colours_and_to_keep_the_colours_at_once_is_refused(self):
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--with-colours", "--keep-colours")
        self.assertEqual(code, 2, out)
        self.assertIn("--with-colours and --keep-colours", out)
        self.assertEqual(self.snapshot(), before)

    def test_keeping_the_colours_with_no_logo_leaves_nothing_to_do(self):
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--keep-colours")
        self.assertEqual(code, 2, out)
        self.assertIn("nothing to do", out.lower())
        self.assertEqual(self.snapshot(), before)

    def test_a_primary_colour_still_marked_proposed_stops_it_until_she_has_confirmed_it(self):
        # scenario 9, for the one colour outside the two theme tables
        self.brand_md(BAKERY_BRAND_MD.replace("| Primary | `#b4531a` |", "| Primary | `#b4531a (proposed)` |"))
        before = self.snapshot()
        code, out = self.intake()
        self.assertEqual(code, 3, out)
        self.assertIn("Primary", out)
        self.assertNotIn("(brand)", out, "she is told the row's name, not the program's word for its table")
        self.assertIn("confirm", out.lower())
        self.assertEqual(self.snapshot(), before)

    # --- files that cannot be edited safely are refused whole, before anything is written -------

    def test_a_stylesheet_too_large_to_be_read_whole_is_refused_by_name_and_never_cut_short(self):
        self.brand_md()
        self.put("src/styles/global.css", self.read("src/styles/global.css") + "/* " + "x" * (1200 * 1024) + " */\n.last-rule { color: red; }\n")
        before = self.snapshot()
        for extra in ((), ("--dry-run",)):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 2, out)
                self.assertIn("src/styles/global.css is larger than 1024 KB", out)
                self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)

    def test_a_file_to_edit_that_is_not_utf8_is_refused_by_name_and_its_letters_stay_as_they_are(self):
        self.brand_md()
        latin1 = self.bytes("src/config.ts").replace(b"legalName: 'Example GmbH'", "legalName: 'Müller GmbH'".encode("latin-1"))
        self.assertNotEqual(latin1, self.bytes("src/config.ts"))
        self.put("src/config.ts", latin1)
        before = self.snapshot()
        for extra in ((), ("--dry-run",)):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 2, out)
                self.assertIn("src/config.ts is not saved as UTF-8", out)
                self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)

    def test_a_colour_that_a_later_block_sets_again_is_refused_before_anything_is_written_and_the_dry_run_says_the_same(self):
        # the edit lands on the first `:root` block; the browser takes the last. Checked on the text as it
        # would be written, so that neither run touches the site (the Primary too, which the check on the
        # written file did not look at: such a run ended "Done")
        self.brand_md()
        # (the reading of the stylesheet takes each colour block only where it stands once, so what is said is
        # that the block stands twice and which colour the later one sets, not what the colour would be)
        for name, again, said in (("the accent", ":root { --accent: #123456; }", "--accent"),
                                  ("the primary", ":root { --brand: #111111; }", "--brand"),
                                  ("a dark value", ':root[data-theme="dark"] { --bg: #222222; }', "--bg")):
            with self.subTest(name=name):
                self.put("src/styles/global.css", T.starter_file("src/styles/global.css") + "\n" + again + "\n")
                before = self.snapshot()
                for extra in (("--dry-run",), ()):
                    code, out = self.intake(*extra)
                    self.assertEqual(code, 2, out)
                    self.assertIn("src/styles/global.css would not carry the palette after the colours were set", out)
                    self.assertIn(said, out)
                    self.assertNotIn("would be unreadable", out, "not a list of every row of a block that was not read")
                    self.assertIn("Nothing was written", out)
                    self.assertEqual(self.snapshot(), before)

    def test_a_dark_block_that_stands_after_its_media_block_instead_of_in_it_is_refused_before_anything_is_written(self):
        self.brand_md()
        head, sep, tail = T.starter_file("src/styles/global.css").partition("@media (prefers-color-scheme: dark) {")
        inner, _close, rest = tail.partition("\n}\n")
        self.put("src/styles/global.css", head + sep + "\n  img { opacity: 0.9; }\n}\n" + inner.replace("  :root:not", ":root:not") + "\n" + rest)
        before = self.snapshot()
        code, out = self.intake()
        self.assertEqual(code, 2, out)
        self.assertIn("inside the `@media (prefers-color-scheme: dark)` block", out)
        self.assertIn("Nothing was written", out)
        self.assertEqual(self.snapshot(), before)

    def test_a_colour_block_spelt_in_a_way_the_reading_knows_and_the_edit_does_not_is_refused_by_name_before_anything_is_written(self):
        # the edit knows the starter's spelling of each block, and the reading names a block that is spelt in
        # another way. Such a stylesheet must end in a refusal that says so, never in an edit of some blocks
        # and not others.
        self.brand_md()
        starter = T.starter_file("src/styles/global.css")
        for name, old, new in (("a selector list", ":root {", ":root, html {"), ("capitals", ":root {", ":ROOT {"),
                               ("a selector list for the dark block", ':root[data-theme="dark"] {', ':root[data-theme="dark"], html.dark {'),
                               ("capitals in the media block", ":root:not([data-theme]) {", ":ROOT:not([data-theme]) {")):
            with self.subTest(name=name):
                self.assertEqual(starter.count(old), 1)
                css = starter.replace(old, new)
                read = _palette.read_css(css)
                self.assertEqual((len(read.problems), len(read.found)), (1, 2), "the reading names the one block that is spelt in another way")
                self.put("src/styles/global.css", css)
                before = self.snapshot()
                for extra in (("--dry-run",), ()):
                    code, out = self.intake(*extra)
                    self.assertEqual(code, 2, out)
                    self.assertIn("src/styles/global.css has no", out)
                    self.assertIn("written in another way than the starter writes it", out)
                    self.assertIn("Nothing was written", out)
                    self.assertEqual(self.snapshot(), before)

    def test_what_the_reading_of_the_stylesheet_could_not_find_is_given_as_the_reason_for_refusing_to_edit_it(self):
        # the edit stops at the first block it misses; the reading names every one that is not there
        self.brand_md()
        css = T.starter_file("src/styles/global.css").replace("@media (prefers-color-scheme: dark)", "@media (min-width: 40em)").replace(
            ':root[data-theme="dark"] {', ':root[data-theme="night"] {')
        self.put("src/styles/global.css", css)
        before = self.snapshot()
        code, out = self.intake()
        self.assertEqual(code, 2, out)
        self.assertIn('src/styles/global.css has no `:root[data-theme="dark"]` block', out)
        self.assertIn('The stylesheet has no :root[data-theme="dark"] { ... } block that this check can find.', out)
        self.assertIn("The stylesheet has no @media (prefers-color-scheme: dark) block with :root:not([data-theme]) { ... } inside it", out)
        self.assertIn("Nothing was written", out)
        self.assertEqual(self.snapshot(), before)

    def test_a_comment_after_a_value_is_kept_when_the_value_changes(self):
        self.brand_md()
        self.put("src/styles/global.css", self.read("src/styles/global.css").replace("  --bg: #ffffff;", "  --bg: #ffffff /* the page */;", 1))
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        self.assertIn("  --bg: #fff8ee /* the page */;", self.read("src/styles/global.css"))

    def test_important_after_a_value_is_not_dropped_and_as_it_cannot_be_read_back_nothing_is_written(self):
        self.brand_md()
        self.put("src/styles/global.css", self.read("src/styles/global.css").replace("  --bg-soft: #f5f7fb;", "  --bg-soft: #f5f7fb !important;", 1))
        before = self.snapshot()
        code, out = self.intake()
        self.assertEqual(code, 2, out)
        self.assertIn("Soft background, light theme would be unreadable", out)
        self.assertIn("--bg-soft in the :root block: The colour '#fef5e8 !important' is not one this check can read", out, "the reading's own reason")
        self.assertIn("Nothing was written", out)
        self.assertEqual(self.snapshot(), before)

    def test_a_theme_colour_in_another_object_before_site_is_left_alone_and_sites_own_is_set(self):
        self.brand_md()
        other = "export const PRINT = {\n  themeColor: '#111111',\n} as const;\n\n"
        self.put("src/config.ts", other + self.read("src/config.ts"))
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        config = self.read("src/config.ts")
        self.assertTrue(config.startswith(other))
        self.assertIn("  themeColor: '#b4531a',", config[len(other):])

    def test_a_manifest_colour_inside_another_entry_before_the_manifests_own_is_refused_before_anything_is_written(self):
        self.brand_md()
        self.put("public/manifest.webmanifest", self.read("public/manifest.webmanifest").replace(
            '  "lang": "en",', '  "lang": "en",\n  "shortcuts": [{ "name": "x", "url": "/x", "theme_color": "#111111" }],', 1))
        before = self.snapshot()
        for extra in (("--dry-run",), ()):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 2, out)
                self.assertIn("public/manifest.webmanifest", out)
                self.assertIn("by hand", out)
                self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)

    def test_a_file_to_write_that_is_a_link_is_refused_before_anything_is_written_and_the_dry_run_says_the_same(self):
        self.brand_md()
        elsewhere = os.path.join(self.tmp.name, "manifest-kept-elsewhere.json")
        os.replace(self.p("public/manifest.webmanifest"), elsewhere)
        os.symlink(elsewhere, self.p("public/manifest.webmanifest"))
        before, target = self.snapshot(), T.read_bytes(elsewhere)
        for extra in (("--dry-run",), ()):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 2, out)
                self.assertIn("public/manifest.webmanifest is a link", out)
                self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(T.read_bytes(elsewhere), target)

    def test_a_link_in_the_share_cards_folder_is_refused_before_anything_is_written(self):
        # the generator writes that folder and a rollback rebuilds it, which would turn the link into a file
        self.brand_md()
        elsewhere = os.path.join(self.tmp.name, "about-card.jpg")
        with open(elsewhere, "wb") as f:
            f.write(b"a card kept somewhere else")
        os.symlink(elsewhere, self.p("public/images/og/about.jpg"))
        before = self.snapshot()
        for extra in (("--dry-run",), ()):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 2, out)
                self.assertIn("public/images/og holds a link (about.jpg)", out)
                self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)
                self.assertTrue(os.path.islink(self.p("public/images/og/about.jpg")))

    @unittest.skipUnless(os.name == "posix", "folder permissions as POSIX has them")
    def test_a_folder_this_account_may_not_write_in_is_found_before_anything_is_written(self):
        self.not_as_root()
        self.brand_md()
        before = self.snapshot()
        os.chmod(self.p("public"), 0o555)
        self.addCleanup(os.chmod, self.p("public"), 0o755)
        for extra in (("--dry-run",), ()):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 2, out)
                self.assertIn("public/manifest.webmanifest cannot be written: this account is not allowed to write in public", out)
                self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)

    # --- when the computer says no: words, the right exit status, and the truth about the files ----

    @unittest.skipUnless(os.name == "posix", "file permissions as POSIX has them")
    def test_a_file_that_may_not_be_read_is_said_in_words_with_its_path_and_json_stays_json(self):
        self.not_as_root()
        self.brand_md()
        before = self.snapshot()
        os.chmod(self.p("src/config.ts"), 0)
        try:
            code, out = self.intake("--json")
            code_plain, out_plain = self.intake()
        finally:
            os.chmod(self.p("src/config.ts"), 0o644)
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["exit"], data["code"]), (2, "refused", 2, "os-error"))
        self.assertIn(self.p("src/config.ts"), data["message"])
        self.assertIn("ermission", data["message"])
        self.assertIn("Nothing was written.", data["report"])
        self.assertEqual(code_plain, 2, out_plain)
        self.assertIn("The run had to stop", out_plain)
        self.assertEqual(self.snapshot(), before)

    def test_a_write_that_fails_half_way_is_said_in_words_and_what_was_written_before_it_is_put_back(self):
        # a file the disk refuses, which no check beforehand can see: stood in for at the journal's last step
        self.brand_md()
        before = self.snapshot()
        real = _site.Journal._put

        def refusing(journal, path, data, mode=0o644):
            if path.endswith("manifest.webmanifest"):
                raise PermissionError(13, "Permission denied", path)
            return real(journal, path, data, mode)
        _site.Journal._put = refusing
        try:
            code, out = self.intake("--json")
        finally:
            _site.Journal._put = real
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["written"]), (2, "refused", []))
        self.assertIn("manifest.webmanifest could not be read or written (Permission denied)", data["message"])
        self.assertIn("Everything it had written was put back.", data["report"])
        self.assertNotIn("not_restored", data)
        self.assertEqual(self.snapshot(), before, "the stylesheet, written before the manifest, is as it was")

    @unittest.skipUnless(os.name == "posix", "folder permissions as POSIX has them")
    def test_a_file_that_cannot_be_put_back_is_named_and_every_other_file_is_put_back_all_the_same(self):
        self.not_as_root()
        self.brand_md()
        before = self.snapshot()
        self.addCleanup(os.chmod, self.p("public"), 0o755)
        code, out = self.intake("--json", command="chmod 555 public; exit 1")
        os.chmod(self.p("public"), 0o755)
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["tests"], data["written"]), (1, "rollback-incomplete", "failed", []))
        self.assertEqual([l["file"] for l in data["not_restored"]], ["public/manifest.webmanifest"])
        report = "\n".join(data["report"])
        self.assertIn("NOT as they were", report)
        self.assertIn("  public/manifest.webmanifest (", report)
        self.assertNotIn("everything was put back", report)
        self.assertNotIn("With the install taken out", report, "it was not all taken out, so the tests are not run a second time")
        after = self.snapshot()
        self.assertNotEqual(after["public/manifest.webmanifest"], before["public/manifest.webmanifest"], "the one file it says it could not put back")
        after["public/manifest.webmanifest"] = before["public/manifest.webmanifest"]
        self.assertEqual(after, before, "every other file is as it was")

    def test_a_file_whose_folder_the_tests_moved_away_is_named_as_not_put_back_instead_of_skipped(self):
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--json", command="mv src/styles src/styles.moved; exit 1")
        data = json.loads(out)
        self.assertEqual((code, data["status"]), (1, "rollback-incomplete"))
        self.assertEqual(data["not_restored"], [{"file": "src/styles/global.css", "why": "its folder is no longer there"}])
        self.assertIn("  src/styles/global.css (its folder is no longer there)", data["report"])
        self.assertNotIn("everything was put back", "\n".join(data["report"]))
        after = self.snapshot()
        for rel in ("src/config.ts", "public/manifest.webmanifest", "scripts/generate_og_cards.py", "public/images/og/default.jpg"):
            self.assertEqual(after[rel], before[rel], rel)

    # --- what the run started is stopped before the files are put back ---------------------------

    @unittest.skipUnless(os.name == "posix", "the stand-in command is a shell's")
    def test_tests_that_run_too_long_are_stopped_with_everything_they_started(self):
        # a preview server left running would hold the site's port for the next run
        self.brand_md()
        before = self.snapshot()
        pids = os.path.join(self.tmp.name, "started")
        self.addCleanup(self.stop_leftovers, pids)
        old = _install.TEST_TIMEOUT
        _install.TEST_TIMEOUT = 2
        try:
            code, out = self.intake(command="sleep 300 & echo $! >> '%s'; wait" % pids)
        finally:
            _install.TEST_TIMEOUT = old
        self.assertEqual(code, 1, out)
        self.assertIn("were stopped", out)
        self.assertNotIn("The failing check", out, "tests that were stopped named no failing check")
        self.assertEqual(self.snapshot(), before)
        started = [int(pid) for pid in T.read(pids).split()]
        # the second run, with the install taken out again, would wait the same time over: it is left out, and that is said
        self.assertEqual(len(started), 1, "the tests are not run a second time after they ran too long")
        self.assertIn("They were not run a second time with the install taken out again", out)
        for pid in started:
            self.assertTrue(self.gone(pid), "the process the test command started (%d) is still running" % pid)

    @unittest.skipUnless(os.name == "posix", "process groups as POSIX has them")
    def test_a_card_generator_that_runs_too_long_is_stopped_with_the_python_its_launcher_started(self):
        # the launcher is Node, the generator a Python it starts: stopping the launcher alone leaves the
        # generator writing into the share cards' folder while that folder is put back
        T.require_pillow(self)
        self.brand_md()
        pids = os.path.join(self.tmp.name, "started")
        self.addCleanup(self.stop_leftovers, pids)
        cards = self.bytes("public/images/og/default.jpg")
        gen = self.read("scripts/generate_og_cards.py")
        self.put("scripts/generate_og_cards.py", gen.replace(
            "def main():\n", "def main():\n    import os, time\n    with open(%r, 'a') as f:\n        f.write('%%d\\n' %% os.getpid())\n    time.sleep(300)\n" % pids, 1))
        old = _install.CARDS_TIMEOUT
        _install.CARDS_TIMEOUT = 6   # long enough for Node, Python and the image library to start
        try:
            code, out = self.intake()
        finally:
            _install.CARDS_TIMEOUT = old
        self.assertEqual(code, 0, out)
        self.assertIn("the generator took more than", out)
        self.assertIn("and was stopped", out)
        self.assertEqual(self.bytes("public/images/og/default.jpg"), cards)
        started = [int(pid) for pid in T.read(pids).split()]
        self.assertEqual(len(started), 1)
        self.assertTrue(self.gone(started[0]), "the generator (%d) is still running" % started[0])

    def test_the_signal_handlers_are_as_they_were_once_a_run_is_over(self):
        self.brand_md()
        names = [n for n in ("SIGTERM", "SIGHUP", "SIGINT") if hasattr(signal, n)]
        before = [signal.getsignal(getattr(signal, n)) for n in names]
        for command, extra in ((GREEN, ()), (RED, ()), (GREEN, ("--dry-run",)), (GREEN, ("--with-logo",))):
            with self.subTest(command=command, extra=extra):
                self.intake(*extra, command=command)
                self.assertEqual([signal.getsignal(getattr(signal, n)) for n in names], before)

    @unittest.skipUnless(os.name == "posix" and hasattr(signal, "SIGHUP"), "signals as POSIX has them")
    def test_a_run_stopped_from_outside_while_the_tests_run_puts_everything_back_and_stops_what_it_started(self):
        # an assistant's shell tool stops a command that runs for minutes. The whole command line is run
        # here, as a process of its own, because the signal ends a process that does not catch it.
        self.brand_md()
        before = self.snapshot()
        pids = os.path.join(self.tmp.name, "started")
        self.addCleanup(self.stop_leftovers, pids)
        # Ctrl-C (SIGINT) is a stop like the other two: the same words, the same exit status, no traceback
        for name in ("TERM", "HUP", "INT"):
            with self.subTest(signal=name):
                command = "sleep 300 & echo $! >> '%s'; kill -%s $PPID; wait" % (pids, name)
                r = self.drive("", command=command)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertIn("stopped from outside (SIG%s)" % name, r.stdout)
                self.assertIn("Everything it had written was put back.", r.stdout)
                self.assertEqual(r.stderr, "", "no traceback")
                self.assertEqual(self.snapshot(), before)
        # a stop in the very instant the command starts something: that, too, is not left running
        sleep, running = self.sleeper()
        r = self.drive("", "--json", command="kill -INT $PPID; " + sleep)
        data = json.loads(r.stdout)
        self.assertEqual((r.returncode, data["status"], data["exit"], data["rolled_back"], data["written"]), (2, "stopped", 2, True, []))
        self.assertIn("stopped from outside (SIGINT)", data["message"])
        self.assertEqual((r.stderr, self.snapshot()), ("", before))
        self.assertTrue(self.none_left(running), "what the test command was just starting is still running")
        started = [int(pid) for pid in T.read(pids).split()]
        self.assertEqual(len(started), 3)
        for pid in started:
            self.assertTrue(self.gone(pid), "the process the test command started (%d) is still running" % pid)

    def test_red_tests_put_the_share_cards_folder_back_with_its_empty_folders_and_its_modes(self):
        self.brand_md()
        os.makedirs(self.p("public/images/og/drafts"))
        os.chmod(self.p("public/images/og/default.jpg"), 0o600)
        before = self.snapshot()
        self.assertIn(os.path.join("public", "images", "og", "drafts") + "/", before)
        code, out = self.intake(command=RED)
        self.assertEqual(code, 1, out)
        self.assertEqual(self.snapshot(), before, "the empty folder too")
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(os.stat(self.p("public/images/og/default.jpg")).st_mode), 0o600)

    # --- the share cards --------------------------------------------------------------------

    def test_text_that_would_not_read_half_way_down_the_share_cards_leaves_their_colours_alone_and_says_so(self):
        # all thirty pairs pass: the grey reads on the white surface and on the black background. The card's
        # background is the gradient between those two, and half way down it is the grey itself.
        self.brand_md(BAKERY_BRAND_MD.partition("### Dark theme\n")[0] + "### Dark theme\n" + table([(l, GREY_DARK[k]) for k, l in LABELS]))
        generator = self.read("scripts/generate_og_cards.py")
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read("scripts/generate_og_cards.py"), generator, "the cards' colours are as they were")
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).dark, GREY_DARK, "the site itself has the palette")
        self.assertIn("the share cards keep the colours they have", out)
        self.assertIn("Heading #767676 falls to 1 to 1", out)
        self.assertIn("text needs 4.5 to 1", out)
        self.assertNotIn("and in the share cards", out)
        self.assertNotIn("with the new colours", out)

    def test_however_the_palette_writes_a_colour_the_share_cards_get_its_three_numbers(self):
        # BRAND.md may say rgb(), a short hex, upper case or a name; the palette holds each as #rrggbb
        md = BAKERY_BRAND_MD
        for old, new in (("| Heading | `#fbeedd` |", "| Heading | `rgb(251, 238, 221)` |"), ("| Accent | `#e2874a` |", "| Accent | `tomato` |"),
                         ("| Background | `#1a120d` |", "| Background | `#1A120D` |"), ("| Muted | `#c4ae98` |", "| Muted | `#CBA` |")):
            self.assertIn(old, md)
            md = md.replace(old, new)
        self.brand_md(md)
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        generator = self.read("scripts/generate_og_cards.py")
        for line in ("TITLE_COL = (251, 238, 221)", "SUB_COL = (255, 99, 71)", "ACCENT = (255, 99, 71)", "BG_BOT = (26, 18, 13)", "FOOTER_COL = (204, 187, 170)"):
            self.assertIn(line, generator)

    # --- an icon she did not hand over --------------------------------------------------------

    def test_a_palette_alone_leaves_a_favicon_this_tool_did_not_write_as_it_is_and_says_why(self):
        # no sharp here, and none is needed: her own favicon is not a logo she handed over. One has <text>
        # (a logo given with --input would be refused for it), one is a clean drawing that the cleaning
        # would still rewrite; neither is judged, redrawn, or a reason to stop.
        self.brand_md()
        clean = _svg.clean_svg(T.real_svg(T.REAL_COLOUR)).text.encode("utf-8")
        self.assertEqual(_svg.clean_svg(clean).text.encode("utf-8"), clean, "a drawing that comes out of the cleaning as it went in")
        for name, own in (("with text", b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><text x="4" y="24">B</text></svg>'),
                          ("a drawing as a design tool exported it", T.real_svg(T.REAL_COLOUR)),
                          ("a drawing she wrote by hand as cleanly as the cleaning would", clean),
                          ("this tool's own file, edited by hand since", _install.MARK.encode("utf-8") + clean.replace(b"#b4531a", b"#B4531A")),
                          ("this tool's line, moved down a line", b"\n" + _install.MARK.encode("utf-8") + clean)):
            with self.subTest(name=name):
                self.put("public/favicon.svg", own)
                self.put("src/styles/global.css", T.starter_file("src/styles/global.css"))
                code, out = self.intake()
                self.assertEqual(code, 0, out)
                self.assertEqual(self.bytes("public/favicon.svg"), own)
                for absent in ("public/favicon.ico", "public/images/logo.png", "public/icon-192.png", "brand-handoff"):
                    self.assertFalse(self.exists(absent), absent)
                self.assertIn("LOGO = None", self.read("scripts/generate_og_cards.py"))
                self.assertIn("the icons were left as they are: public/favicon.svg is not a file this tool wrote", out)
                self.assertIn("--with-logo", out)
                self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT, "the colours are in")


class OnlyALogo(SiteCase):
    """Scenarios 39, 11 and 34: she has a logo and wants no help with colours."""

    def test_the_seven_files_come_from_her_zip_and_the_colours_stay_as_the_site_has_them(self):
        T.require_pillow(self)
        css_before, manifest_before = self.read("src/styles/global.css"), self.read("public/manifest.webmanifest")
        zip_path = self.package()
        code, out = self.intake("--input", zip_path, "--pick", T.REAL_COLOUR, "--mono", T.REAL_MONO, "--accept-colours",
                                "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        for rel in ("public/favicon.svg", "public/favicon.ico", "public/apple-touch-icon.png", "public/icon-192.png",
                    "public/icon-512.png", "public/icon-maskable-512.png", "public/images/logo.png"):
            self.assertTrue(self.exists(rel), rel)
        self.assertEqual(self.read("src/styles/global.css"), css_before)
        self.assertEqual(self.read("public/manifest.webmanifest"), manifest_before)
        self.assertIn('LOGO = ROOT / "public/images/logo.png"', self.read("scripts/generate_og_cards.py"))
        self.assertIn("logo: '/images/logo.png'", self.read("src/config.ts"))

    def test_the_package_is_kept_in_a_folder_git_ignores_with_a_preview_beside_it(self):
        zip_path = self.package("furrows.zip")
        code, out = self.intake("--input", zip_path, "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.bytes("brand-handoff/furrows.zip"), T.real_zip_bytes())
        self.assertTrue(self.exists("brand-handoff/preview.png"))
        self.assertEqual(self.read(".gitignore").splitlines()[-1], "brand-handoff/")
        self.assertEqual(T.read_bytes(zip_path), T.real_zip_bytes(), "her own copy is untouched")

    def test_the_preview_is_the_installed_mark_and_the_report_leaves_whether_it_reads_to_her(self):
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        import _png
        w, h = _png.size(self.bytes("brand-handoff/preview.png"))
        self.assertEqual((w, h), (2 * 432, 336))
        self.assertIn("brand-handoff/preview.png", out)
        self.assertIn("your call", out)
        for verdict in ("looks good", "too small", "unreadable", "is fine", "passes the legibility"):
            self.assertNotIn(verdict, out.lower())

    def test_two_files_in_the_zip_are_asked_about_and_nothing_is_written(self):
        before = self.snapshot()
        code, out = self.intake("--input", self.package(), brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn(T.REAL_COLOUR, out)
        self.assertIn(T.REAL_MONO, out)
        self.assertEqual(self.snapshot(), before)

    def test_a_package_that_will_not_do_is_refused_with_nothing_written(self):
        before = self.snapshot()
        for name, data in (("raster.png", b"\x89PNG\r\n\x1a\n" + b"\0" * 30),
                           ("evil.svg", b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><script>x</script></svg>'),
                           ("nosvg.zip", T.build_zip([("a.png", b"\x89PNG..."), ("README.txt", b"hi")]))):
            with self.subTest(name=name):
                code, out = self.intake("--input", self.package(name, data), brand=False)
                self.assertEqual(code, 2, out)
                self.assertEqual(self.snapshot(), before)
        code, out = self.intake("--input", self.package("raster.png", b"\x89PNG\r\n\x1a\n" + b"\0" * 30), brand=False)
        self.assertIn("SVG", out)

    def test_scenario_27_a_path_that_holds_nothing_is_said_so_and_nothing_is_searched_for(self):
        before = self.snapshot()
        for path in (os.path.join(self.pack, "missing.zip"), self.pack):
            with self.subTest(path=path):
                code, out = self.intake("--input", path, brand=False)
                self.assertEqual(code, 2, out)
                self.assertIn("nothing", out.lower())
                self.assertIn("path", out.lower())
                self.assertEqual(self.snapshot(), before)

    def test_a_folder_holding_one_package_is_the_package(self):
        # a later run: the package is in brand-handoff
        os.makedirs(self.p("brand-handoff"))
        with open(self.p("brand-handoff/furrows.zip"), "wb") as f:
            f.write(T.real_zip_bytes())
        code, out = self.intake("--input", self.p("brand-handoff"), brand=False)
        self.assertEqual(code, 3, out)   # it is the real zip with two SVGs: asked which
        self.assertIn(T.REAL_COLOUR, out)

    def test_a_folder_holding_several_packages_asks_which(self):
        self.package("a.zip")
        self.package("b.svg", T.real_svg(T.REAL_COLOUR))
        code, out = self.intake("--input", self.pack, brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("a.zip", out)
        self.assertIn("b.svg", out)

    def test_scenario_21_a_colour_outside_the_palette_is_listed_and_never_recoloured(self):
        self.brand_md()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--with-colours", "--accept-low-contrast", "both")
        self.assertEqual(code, 3, out)
        self.assertIn("#6b2c0b", out)
        self.assertIn("not in", out)
        self.assertFalse(self.exists("public/favicon.svg"))
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--with-colours", "--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(code, 0, out)
        self.assertIn("#6b2c0b", self.read("public/favicon.svg"))

    def test_scenario_15_a_colour_that_vanishes_on_a_theme_is_named_with_the_theme_and_the_one_colour_way_out(self):
        self.brand_md()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--mono", T.REAL_MONO, "--with-colours", "--accept-colours")
        self.assertEqual(code, 3, out)
        self.assertIn("dark", out)
        self.assertIn("1.7", out)
        self.assertIn("one-colour", out)
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--mono", T.REAL_MONO, "--with-colours", "--accept-colours",
                                "--accept-low-contrast", "dark")
        self.assertEqual(code, 0, out)

    def test_the_mark_is_checked_against_the_sites_own_colours_when_no_palette_is_given(self):
        # scenario 39: on a fresh scaffold those are the starter's; on a site whose colours were customised, its own
        css = self.read("src/styles/global.css").replace("--bg: #0a0b1e;", "--bg: #6b2c0b;").replace("#0a0b1e", "#6b2c0b")
        with open(self.p("src/styles/global.css"), "w", encoding="utf-8") as f:
            f.write(css)
        code, out = self.intake("--input", self.package("one.svg", T.real_svg(T.REAL_MONO)), "--accept-colours", brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("dark", out)

    def test_scenario_30_the_scaffolds_placeholders_are_replaced_with_a_word(self):
        placeholder_svg, placeholder_ico = b"<svg>placeholder</svg>", b"placeholder-ico"
        for rel, data in (("public/favicon.svg", placeholder_svg), ("public/favicon.ico", placeholder_ico)):
            with open(self.p(rel), "wb") as f:
                f.write(data)
        old = _site.SCAFFOLD_DEFAULTS
        _site.SCAFFOLD_DEFAULTS = {"public/favicon.svg": {hashlib.sha256(placeholder_svg).hexdigest()},
                                   "public/favicon.ico": {hashlib.sha256(placeholder_ico).hexdigest()}}
        try:
            args = ("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both")
            dry_code, dry_out = self.intake(*args, "--dry-run", brand=False)
            code, out = self.intake(*args, brand=False)
        finally:
            _site.SCAFFOLD_DEFAULTS = old
        self.assertEqual(dry_code, 0, dry_out)
        self.assertIn("would replace", dry_out)
        self.assertNotIn("now replaced", dry_out, "a dry run has replaced nothing")
        self.assertEqual(code, 0, out)
        self.assertIn("now replaced", out)
        self.assertNotEqual(self.read("public/favicon.svg"), placeholder_svg.decode())

    def test_scenario_16_an_icon_that_is_not_a_placeholder_is_asked_about(self):
        with open(self.p("public/apple-touch-icon.png"), "wb") as f:
            f.write(b"somebody's own icon")
        before = self.snapshot()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("public/apple-touch-icon.png", out)
        self.assertEqual(self.snapshot(), before)
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both",
                                "--replace-icons", brand=False)
        self.assertEqual(code, 0, out)
        self.assertNotEqual(self.bytes("public/apple-touch-icon.png"), b"somebody's own icon")

    def test_running_it_again_with_the_same_mark_asks_nothing_and_changes_nothing_more(self):
        args = ("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(self.intake(*args, brand=False)[0], 0)
        after_first = self.snapshot()
        code, out = self.intake(*args, brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.snapshot(), after_first)

    def test_a_later_run_with_no_palette_and_no_file_has_nothing_to_do(self):
        # the installed mark alone starts nothing: the logo is redone only when a file is given or the colours change
        args = ("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(self.intake(*args, brand=False)[0], 0)
        after_first = self.snapshot()
        code, out = self.intake(brand=False)
        self.assertEqual(code, 2, out)
        self.assertIn("nothing to do", out.lower())
        self.assertEqual(self.snapshot(), after_first)

    def test_a_package_already_in_brand_handoff_is_not_copied_a_second_time(self):
        # its name has a space, which a copy would turn into an underscore: a second file would show
        os.makedirs(self.p("brand-handoff"))
        kept = self.p("brand-handoff/my logo.zip")
        with open(kept, "wb") as f:
            f.write(T.real_zip_bytes())
        code, out = self.intake("--input", kept, "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(os.listdir(self.p("brand-handoff"))), ["my logo.zip", "preview.png"])
        self.assertNotIn("is kept in", out)
        self.assertEqual(self.read(".gitignore").splitlines()[-1], "brand-handoff/", "the preview alone is reason to ignore the folder")

    def test_a_different_file_of_the_same_name_in_brand_handoff_is_kept_and_the_new_one_gets_its_own_name(self):
        os.makedirs(self.p("brand-handoff"))
        with open(self.p("brand-handoff/logo.zip"), "wb") as f:
            f.write(b"an earlier package")
        code, out = self.intake("--input", self.package("logo.zip"), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.bytes("brand-handoff/logo.zip"), b"an earlier package")
        self.assertEqual(self.bytes("brand-handoff/logo-2.zip"), T.real_zip_bytes())
        self.assertIn("brand-handoff/logo-2.zip", out)

    def test_an_unknown_theme_to_accept_is_refused_not_ignored(self):
        before = self.snapshot()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "purple", brand=False)
        self.assertEqual(code, 2, out)
        self.assertIn("purple", out)
        self.assertEqual(self.snapshot(), before)

    def test_a_half_filled_palette_beside_a_logo_is_named_and_the_colours_stay(self):
        # never silent: she may think her colours went in with the logo
        self.brand_md(BAKERY_BRAND_MD.replace("| Soft background | `#fef5e8` |\n", ""))
        css_before = self.read("src/styles/global.css")
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(code, 0, out)
        self.assertIn("the colours were not changed", out)
        self.assertIn("Soft background", out)
        self.assertEqual(self.read("src/styles/global.css"), css_before)

    def test_a_logo_alone_leaves_the_theme_colour_and_the_share_cards_colours_as_the_site_has_them(self):
        # scenario 39, on a site whose config and card colours no longer match the stylesheet's
        for rel, old, new in (("src/config.ts", "themeColor: '#000000'", "themeColor: '#123456'"),
                              ("scripts/generate_og_cards.py", "BG_TOP = (30, 33, 64)", "BG_TOP = (1, 2, 3)")):
            text = self.read(rel)
            self.assertIn(old, text)
            with open(self.p(rel), "w", encoding="utf-8") as f:
                f.write(text.replace(old, new))
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        self.assertIn("themeColor: '#123456'", self.read("src/config.ts"))
        self.assertIn("BG_TOP = (1, 2, 3)", self.read("scripts/generate_og_cards.py"))
        self.assertIn('LOGO = ROOT / "public/images/logo.png"', self.read("scripts/generate_og_cards.py"))

    def test_scenario_31_red_tests_remove_the_package_copy_the_ignore_line_and_the_folder(self):
        before = self.snapshot()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both",
                                command=RED, brand=False)
        self.assertEqual(code, 1, out)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.exists("brand-handoff"))

    def test_scenario_31_in_a_brand_handoff_that_was_already_there_only_this_runs_copy_goes(self):
        os.makedirs(self.p("brand-handoff"))
        with open(self.p("brand-handoff/earlier.zip"), "wb") as f:
            f.write(b"earlier")
        with open(self.p(".gitignore"), "a") as f:
            f.write("brand-handoff/\n")
        before = self.snapshot()
        code, out = self.intake("--input", self.package("this.zip"), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both",
                                command=RED, brand=False)
        self.assertEqual(code, 1, out)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.exists("brand-handoff/earlier.zip"))

    def test_an_existing_ignore_line_is_not_added_twice(self):
        with open(self.p(".gitignore"), "a") as f:
            f.write("/brand-handoff\n")
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read(".gitignore").count("brand-handoff"), 1)

    def test_an_ignore_rule_that_a_later_line_takes_back_does_not_count_and_the_line_is_added_at_the_end(self):
        with open(self.p(".gitignore"), "a") as f:
            f.write("brand-handoff/*\n!brand-handoff/logo.zip\n")
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read(".gitignore").splitlines()[-3:], ["brand-handoff/*", "!brand-handoff/logo.zip", "brand-handoff/"])
        self.assertIn(".gitignore", out)

    def test_a_logo_beside_a_palette_that_would_change_the_sites_colours_asks_first_and_names_every_value(self):
        # she came with a logo; BRAND.md holds a palette the site does not show. Colours she set by hand in
        # the stylesheet are not overwritten on the way without one of them being named.
        self.brand_md()
        before = self.snapshot()
        for extra in ((), ("--dry-run",)):
            with self.subTest(extra=extra):
                code, out = self.intake("--input", self.package(), *LOGO_ARGS, *extra)
                self.assertEqual(code, 3, out)
                for said in ("Nothing was written", "--with-colours", "--keep-colours", "    * Primary: #000000 becomes #b4531a",
                             "    * Accent, light theme: #2b50e0 becomes #b4531a", "    * Surface (cards), dark theme: #161836 becomes #2a1f17"):
                    self.assertIn(said, out)
                self.assertEqual(self.snapshot(), before)
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, "--json")
        asks = json.loads(out)["asks"]
        self.assertEqual([k["code"] for k in asks], ["colours-too"])
        self.assertIn("Primary: #000000 becomes #b4531a", asks[0]["options"])

    def test_keep_colours_installs_the_logo_and_leaves_every_colour_as_the_site_has_it(self):
        self.brand_md()
        kept = {rel: self.read(rel) for rel in ("src/styles/global.css", "public/manifest.webmanifest")}
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, "--keep-colours")
        self.assertEqual(code, 0, out)
        for rel, text in kept.items():
            self.assertEqual(self.read(rel), text, rel)
        self.assertIn("themeColor: '#000000'", self.read("src/config.ts"))
        self.assertIn("BG_TOP = (30, 33, 64)", self.read("scripts/generate_og_cards.py"))
        self.assertTrue(self.exists("public/images/logo.png"))
        self.assertIn("the palette in BRAND.md was not applied (--keep-colours)", out)
        self.assertNotIn("Colours:", out)
        import _png
        self.assertEqual(_png.at(_png.decode(self.bytes("public/icon-maskable-512.png")), 0, 0)[:3], (0xff, 0xff, 0xff), "the icons sit on the site's own background")

    def test_a_logo_beside_a_palette_the_site_already_shows_asks_nothing(self):
        self.brand_md()
        self.assertEqual(self.intake()[0], 0)   # the colours first, on their own
        code, out = self.intake("--input", self.package(), *LOGO_ARGS)
        self.assertEqual(code, 0, out)
        self.assertTrue(self.exists("public/images/logo.png"))

    def test_a_favicon_that_is_not_the_recorded_placeholder_is_asked_about_before_a_logo_replaces_it(self):
        # what a newer scaffold's placeholder is to this tool, whose two hashes nothing keeps up to date: an
        # icon it does not know. She is asked; it is never replaced with only a word.
        self.put("public/favicon.svg", b"<svg>the placeholder of a scaffold newer than the recorded one</svg>")
        before = self.snapshot()
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("public/favicon.svg", out)
        self.assertIn("--replace-icons", out)
        self.assertEqual(self.snapshot(), before)
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, "--replace-icons", brand=False)
        self.assertEqual(code, 0, out)
        self.assertNotIn("placeholder", out)

    def test_asking_for_the_logo_with_no_file_draws_the_icons_again_from_the_installed_master(self):
        self.assertEqual(self.intake("--input", self.package(), *LOGO_ARGS, brand=False)[0], 0)
        after_first = self.snapshot()
        os.remove(self.p("public/icon-192.png"))
        code, out = self.intake("--with-logo", "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.snapshot(), after_first, "the icon that was missing is back, and nothing else moved")

    def test_a_dry_run_lists_what_the_real_run_would_write_and_nothing_it_would_leave_alone(self):
        args = ("--input", self.package(), *LOGO_ARGS, "--json")
        dry = json.loads(self.intake(*args, "--dry-run", brand=False)[1])
        real = json.loads(self.intake(*args, brand=False)[1])
        self.assertEqual((dry["status"], real["status"]), ("dry-run", "done"))
        self.assertEqual(dry["written"], real["written"])
        self.assertIn("brand-handoff/preview.png", dry["written"])
        again = json.loads(self.intake(*args, "--dry-run", brand=False)[1])
        self.assertEqual(again["written"], [], "the site holds all of it already, as the real run finds too")
        self.assertEqual(json.loads(self.intake(*args, brand=False)[1])["written"], [])
        code, out = self.intake(*args[:-1], "--dry-run", brand=False)
        self.assertIn("  nothing: every file is already as this run would write it", out)
        os.remove(self.p("public/icon-512.png"))
        self.assertEqual(json.loads(self.intake(*args, "--dry-run", brand=False)[1])["written"], ["public/icon-512.png"])

    def test_a_package_called_preview_png_does_not_take_the_preview_sheets_name(self):
        # what a file is, is read from its content, so an SVG may be called anything
        path = self.package("preview.png", T.real_svg(T.REAL_MONO))
        code, out = self.intake("--input", path, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        import _png
        self.assertEqual(_png.size(self.bytes("brand-handoff/preview.png")), (2 * 432, 336), "the preview sheet")
        self.assertEqual(self.bytes("brand-handoff/preview-2.png"), T.real_svg(T.REAL_MONO), "her file, under the next name")
        self.assertIn("is kept in brand-handoff/preview-2.png", out)

    def test_a_company_logo_that_pointed_at_her_own_file_is_repointed_with_a_note_that_names_it(self):
        self.put("src/config.ts", self.read("src/config.ts").replace("logo: '/images/logo.png',", "logo: '/brand/own-logo.svg',"))
        # said by what happened: a dry run has pointed it nowhere
        for extra, said in ((("--dry-run",), "Note: COMPANY.logo in src/config.ts points at /brand/own-logo.svg; this run would point it at /images/logo.png"),
                            ((), "Note: COMPANY.logo in src/config.ts pointed at /brand/own-logo.svg; it now points at /images/logo.png")):
            with self.subTest(extra=extra):
                code, out = self.intake("--input", self.package(), *LOGO_ARGS, *extra, brand=False)
                self.assertEqual(code, 0, out)
                self.assertIn(said, out)
                self.assertEqual("it now points at" in out, not extra, out)
        self.assertIn("logo: '/images/logo.png',", self.read("src/config.ts"))
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, brand=False)
        self.assertNotIn("COMPANY.logo in src/config.ts pointed at", out, "once it points there, there is nothing to say")

    def test_an_emblem_already_wired_with_single_quotes_is_not_taken_for_somebody_elses(self):
        wired = self.read("scripts/generate_og_cards.py").replace("LOGO = None", "LOGO = ROOT / 'public/images/logo.png'")
        self.put("scripts/generate_og_cards.py", wired)
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read("scripts/generate_og_cards.py"), wired)

    def test_a_note_that_explains_a_question_is_printed_with_the_question(self):
        # the question names a colour she cannot see in her mark; the note says why it is counted
        hidden = self.package("hidden.svg", rects((2, 2, 28, 28, "#123456"), (2, 2, 28, 28, "#16162a")))
        note = "the colour #123456 is painted in the file but hardly shows when it is drawn"
        before = self.snapshot()
        code, out = self.intake("--input", hidden, "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("not in the palette: #123456", out)
        self.assertIn("Note: " + note, out)
        data = json.loads(self.intake("--input", hidden, "--accept-low-contrast", "both", "--json", brand=False)[1])
        self.assertEqual(data["status"], "needs-decision")
        self.assertTrue(any(n.startswith(note) for n in data["notes"]), data["notes"])
        self.assertTrue(any(l.startswith("Note: " + note) for l in data["report"]), data["report"])
        self.assertEqual(self.snapshot(), before)

    def test_a_question_asked_before_the_mark_is_drawn_carries_the_notes_made_so_far(self):
        # two packages in the folder, and a palette that is half filled in: she is told both at once
        self.brand_md(BAKERY_BRAND_MD.replace("| Soft background | `#fef5e8` |\n", ""))
        self.package("a.zip")
        self.package("b.svg", T.real_svg(T.REAL_COLOUR))
        code, out = self.intake("--input", self.pack)
        self.assertEqual(code, 3, out)
        self.assertIn("Which one is it?", out)
        self.assertIn("Note: the colours were not changed: BRAND.md does not hold a complete palette", out)

    def test_a_question_does_not_say_a_placeholder_was_replaced_when_nothing_was_written(self):
        placeholder = b"<svg>placeholder</svg>"
        self.put("public/favicon.svg", placeholder)
        self.put("public/apple-touch-icon.png", b"somebody's own icon")
        old = _site.SCAFFOLD_DEFAULTS
        _site.SCAFFOLD_DEFAULTS = {"public/favicon.svg": {hashlib.sha256(placeholder).hexdigest()}}
        try:
            code, out = self.intake("--input", self.package(), *LOGO_ARGS, brand=False)
            self.assertEqual(code, 3, out)
            self.assertIn("public/apple-touch-icon.png", out)
            self.assertNotIn("now replaced", out)
            code, out = self.intake("--input", self.package(), *LOGO_ARGS, "--replace-icons", brand=False)
        finally:
            _site.SCAFFOLD_DEFAULTS = old
        self.assertEqual(code, 0, out)
        self.assertIn("public/favicon.svg was the scaffold's placeholder (the Astro logo), now replaced", out)

    def test_the_one_colour_version_is_held_against_the_palette_but_never_asked_about_on_the_page(self):
        # the colour version cannot sit on any background whole (one half is near white, the other near
        # black), so the app icons are drawn from the one-colour version, on white. That version's navy would
        # vanish on the dark page, but it never stands there: only the colour version does.
        pack = self.package("two.zip", T.build_zip([("mark.svg", rects((2, 2, 12, 28, "#fefefe"), (18, 2, 12, 28, "#050505"))),
                                                    ("mark-mono.svg", rects((2, 2, 28, 28, "#222244")))]))
        args = ("--input", pack, "--pick", "mark.svg", "--mono", "mark-mono.svg")
        code, out = self.intake(*args, "--accept-colours", brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("drawn from the one-colour version on #ffffff", out)
        self.assertIn("On the light theme the mark falls under 3 to 1 against the background (#fefefe is 1 to 1)", out)
        self.assertIn("On the dark theme the mark falls under 3 to 1 against the background (#050505 is 1.04 to 1)", out)
        self.assertNotIn("#222244", out, "the one-colour version's colour is not asked about on a page it never stands on")
        code, out = self.intake(*args, "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("not in the palette: #fefefe, #050505, #222244", out, "and it is still held against the palette")

    def test_brand_handoff_that_is_a_file_is_refused_in_words_before_anything_is_written(self):
        self.put("brand-handoff", b"a file where the folder would go")
        before = self.snapshot()
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, brand=False)
        self.assertEqual(code, 2, out)
        self.assertIn("brand-handoff is a file, not a folder", out)
        self.assertIn("Nothing was written", out)
        self.assertEqual(self.snapshot(), before)


OTHER_HEADINGS = BAKERY_BRAND_MD.replace("### Light theme", "### Light").replace("### Dark theme", "### Dark").replace("### Brand (fixed, theme-independent)", "### Brand colours")
NESTED_SHORTCUT = '  "lang": "en",\n  "shortcuts": [{ "name": "x", "url": "/x", "theme_color": "#111111", "background_color": "#222222" }],'
POSIX = unittest.skipUnless(os.name == "posix", "signals, permissions and the stand-in commands as POSIX has them")


class ColoursOnASiteAsSheLeftIt(SiteCase):
    """The second round of the review: a run about colours on a site that somebody has worked on since
    the starter. What it reads is what the site reads; what it cannot be sure of it refuses, the dry run in
    the same words; a file that is there is never taken for one that is not. No sharp is needed here."""
    modules = False

    def fresh(self):
        shutil.rmtree(self.site)
        T.make_starter_site(self.site, with_modules=self.modules)
        self.brand_md()

    # --- an edit changes the value the site reads, or nothing ---------------------------------

    def test_a_copy_of_the_site_block_that_is_commented_out_or_quoted_is_left_alone_and_the_theme_colour_the_site_reads_is_set(self):
        config = T.starter_file("src/config.ts")
        start = config.index("export const SITE")
        old = config[start:config.index("\n}", start) + 2].replace("#000000", "#111111")
        for name, copy in (("a block comment", "/*\n" + old + "\n*/\n"), ("line comments", "".join("// " + line + "\n" for line in old.splitlines())),
                           ("a template string", "const notes = `\n" + old + "\n`;\n")):
            with self.subTest(name=name):
                self.fresh()
                self.put("src/config.ts", copy + config)
                (dry_code, dry), (code, out) = self.both_runs("--json")
                self.assertEqual((dry_code, code), (0, 0), out)
                self.assertEqual(json.loads(dry)["written"], json.loads(out)["written"])
                self.assertIn("src/config.ts, themeColor: #000000 becomes #b4531a", json.loads(dry)["changes"], "the value that is read is the real block's")
                after = self.read("src/config.ts")
                self.assertTrue(after.startswith(copy), "the copy is exactly as it was")
                self.assertEqual(after[len(copy):], config.replace("themeColor: '#000000'", "themeColor: '#b4531a'"))

    def test_a_theme_colour_that_the_site_cannot_be_known_to_read_is_refused_before_anything_is_written(self):
        config, line = T.starter_file("src/config.ts"), "  themeColor: '#000000',"
        self.assertEqual(config.count(line), 1)
        for name, text, said in (("the block twice", config + "\nexport const SITE = {\n  themeColor: '#111111',\n};\n", "`export const SITE` twice"),
                                 ("the key once with quotes and once without", config.replace(line, line + "\n  'themeColor': '#111111',"), "sets `themeColor` twice in SITE"),
                                 ("the key twice on one line", config.replace(line, line + " themeColor: '#111111',"), "sets `themeColor` twice in SITE"),
                                 ("the key a second time with a value that is no colour", config.replace(line, line + "\n  themeColor: BRAND_COLOUR,"), "sets `themeColor` twice in SITE")):
            with self.subTest(name=name):
                self.fresh()
                self.put("src/config.ts", text)
                before = self.snapshot()
                for code, out in self.both_runs():
                    self.assertEqual(code, 2, out)
                    self.assertIn(said, out)
                    self.assertIn("Nothing was written", out)
                    self.assertEqual(self.snapshot(), before)

    def test_a_manifest_she_set_by_hand_as_the_refusal_told_her_to_is_left_exactly_as_it_is(self):
        # run 1 refuses: another entry has colours of the same names. She sets the manifest's own two by hand.
        # Run 2 must not then edit the first line of each name (the other entry's) and call it done.
        self.brand_md()
        nested = self.read("public/manifest.webmanifest").replace('  "lang": "en",', NESTED_SHORTCUT, 1)
        self.put("public/manifest.webmanifest", nested)
        before = self.snapshot()
        for code, out in self.both_runs():
            self.assertEqual(code, 2, out)
            self.assertIn('public/manifest.webmanifest has "theme_color" more than once', out)
            self.assertIn("by hand to #b4531a", out)
            self.assertEqual(self.snapshot(), before)
        half = nested.replace('"theme_color": "#000000"', '"theme_color": "#b4531a"')
        self.put("public/manifest.webmanifest", half)
        for code, out in self.both_runs():
            self.assertEqual(code, 2, out)
            self.assertIn('has "background_color" more than once', out)
            self.assertIn("by hand to #fff8ee", out)
            self.assertEqual(self.read("public/manifest.webmanifest"), half)
        by_hand = half.replace('"background_color": "#ffffff"', '"background_color": "#fff8ee"')
        self.assertEqual(by_hand.count("#111111") + by_hand.count("#222222"), 2)
        self.put("public/manifest.webmanifest", by_hand)
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, json.loads(out)["status"]), (0, 0, "done"), out)
        for report in (dry, out):
            self.assertNotIn("public/manifest.webmanifest", json.loads(report)["written"])
            self.assertEqual([c for c in json.loads(report)["changes"] if "manifest" in c], [])
        self.assertEqual(self.read("public/manifest.webmanifest"), by_hand, "the other entry's colours too")

    def test_a_primary_that_a_dark_block_sets_again_is_refused_before_anything_is_written_naming_the_block(self):
        css = T.starter_file("src/styles/global.css")
        dark, media = ':root[data-theme="dark"] {\n', "  :root:not([data-theme]) {\n"
        for name, text, said in (
                ("the dark block", css.replace(dark, dark + "  --brand: #123456;\n", 1), '--brand (the Primary) inside the `:root[data-theme="dark"]` block'),
                ("the block for visitors without JavaScript", css.replace(media, media + "    --brand: #123456;\n", 1), "--brand (the Primary) inside the dark block inside the `@media (prefers-color-scheme: dark)` block"),
                ("a value no colour can be read from", css.replace(dark, dark + "  --brand: var(--accent);\n", 1), "--brand (the Primary) inside the `:root[data-theme=\"dark\"]` block"),
                ("a rule further down that names the dark theme among others", css + '\n.print, :root[data-theme="dark"] {\n  --brand: #123456;\n}\n', "written in another way than the starter writes it")):
            with self.subTest(name=name):
                self.assertNotEqual(text, css)
                self.fresh()
                self.put("src/styles/global.css", text)
                before = self.snapshot()
                for code, out in self.both_runs():
                    self.assertEqual(code, 2, out)
                    self.assertIn(said, out)
                    self.assertIn("Nothing was written", out)
                    self.assertEqual(self.snapshot(), before)
        self.fresh()   # a comment that only mentions it is no reason to stop
        self.put("src/styles/global.css", css.replace(dark, dark + "  /* --brand: #123456; */\n", 1))
        self.assertEqual(self.intake()[0], 0)

    def test_a_file_saved_with_a_byte_order_mark_is_read_past_the_mark_and_keeps_it(self):
        mark = chr(0xFEFF)
        self.brand_md()
        self.assertEqual(self.intake()[0], 0)
        plain = {rel: self.read(rel) for rel in _site.REQUIRED_FILES}
        for rel in _site.REQUIRED_FILES:
            with self.subTest(rel=rel):
                self.fresh()
                self.put(rel, mark + T.starter_file(rel))
                (dry_code, dry), (code, out) = self.both_runs("--json")
                self.assertEqual((dry_code, code), (0, 0), out)
                self.assertIn(rel, json.loads(dry)["written"])
                self.assertEqual(self.read(rel), mark + plain[rel], "the same edit as without the mark, and the mark is still there")

    # --- a palette that is there and is not used is never taken for no palette -----------------

    def test_a_palette_the_reading_names_but_does_not_use_is_said_with_the_reason_one_thing_to_a_line(self):
        cases = (("its tables under other headings", OTHER_HEADINGS, True),
                 ("a header row that does not call the column Hex", BAKERY_BRAND_MD.replace("| Token | Hex |", "| Token | Value |"), True),
                 ("one of its tables under another heading", BAKERY_BRAND_MD.replace("### Dark theme", "### Night"), False),
                 ("a value among words", BAKERY_BRAND_MD.replace("| Muted | `#c4ae98` |", "| Muted | about `#c4ae98` |"), False))
        for name, text, no_row in cases:
            with self.subTest(name=name):
                self.brand_md(text)
                read = _palette.parse_tables(text)
                problems = [m for _theme, _row, _code, m in read.problems]
                self.assertTrue(problems)
                self.assertEqual(not read.rows_found, no_row)
                before = self.snapshot()
                for flags, first in ((("--with-colours",), None), ((), "There is nothing to do: no complete palette was found in BRAND.md, and no logo file was given.")):
                    for code, out in self.both_runs(*flags):
                        self.assertEqual(code, 2, out)
                        lines = out.splitlines()
                        for said in problems:
                            self.assertIn(said, lines, "each thing the reading could not use, on a line of its own")
                        self.assertEqual(_palette.FORM in lines, no_row, "the form it reads is given when it found no row at all")
                        self.assertIn(first or lines[0], lines)
                        for untrue in ("has no filled-in colour rows", "no BRAND.md was found"):
                            self.assertNotIn(untrue, out)
                        self.assertIn("Nothing was written.", lines)
                        self.assertEqual(self.snapshot(), before)
                data = json.loads(self.intake("--with-colours", "--json")[1])
                self.assertEqual((data["status"], data["code"]), ("refused", "palette-incomplete"))
                self.assertEqual(data["message"].splitlines()[1:1 + len(problems)], problems)
        first = {name: self.intake_with(text)[1].splitlines()[0] for name, text, _no_row in cases}
        self.assertEqual(first["its tables under other headings"], "No colour could be read from the palette in BRAND.md.")
        self.assertEqual(first["one of its tables under another heading"], "The palette in BRAND.md is not complete. Rows without a colour: the dark theme: Heading, Body (ink), Muted, "
                         "Accent, Link, Hairline, Background, Soft background, Surface (cards).")
        self.brand_md(T.read(T.BRAND_TEMPLATE))   # the template, not filled in: no colour and nothing wrong with it
        code, out = self.intake("--with-colours")
        self.assertEqual(code, 2, out)
        self.assertIn("There are no colours to apply: BRAND.md has no filled-in colour rows.", out)

    def intake_with(self, text):
        self.brand_md(text)
        return self.intake("--with-colours")

    # --- the Primary and the rest of the palette, said in every report --------------------------

    def test_a_run_that_ends_without_the_colours_still_lists_the_ones_it_would_have_changed(self):
        self.brand_md()
        lines = ("Colours that would have changed in src/styles/global.css:", "  Primary: #000000 becomes #b4531a",
                 "Colours that would have changed in the site's other files:", "  src/config.ts, themeColor: #000000 becomes #b4531a")
        code, out = self.intake(command=RED)                              # red tests: all of it was put back
        self.assertEqual(code, 1, out)
        for line in lines:
            self.assertIn(line, out.splitlines())
        self.assertIn("Primary: #000000 becomes #b4531a", json.loads(self.intake("--json", command=RED)[1])["changes"])
        self.put("public/manifest.webmanifest", self.read("public/manifest.webmanifest").replace('  "lang": "en",', NESTED_SHORTCUT, 1))
        for code, out in self.both_runs():                                # a refusal after the colours were worked out
            self.assertEqual(code, 2, out)
            for line in lines:
                self.assertIn(line, out.splitlines())
        data = json.loads(self.intake("--json")[1])
        self.assertEqual(data["status"], "refused")
        self.assertIn("scripts/generate_og_cards.py, BG_TOP: #1e2140 becomes #2a1f17", data["changes"])

    def test_every_colour_the_palette_changes_outside_the_stylesheet_is_listed_with_its_file(self):
        self.brand_md()
        other = ["src/config.ts, themeColor: #000000 becomes #b4531a", "public/manifest.webmanifest, theme_color: #000000 becomes #b4531a",
                 "public/manifest.webmanifest, background_color: #ffffff becomes #fff8ee", "scripts/generate_og_cards.py, BG_TOP: #1e2140 becomes #2a1f17",
                 "scripts/generate_og_cards.py, BG_BOT: #0a0b1e becomes #1a120d", "scripts/generate_og_cards.py, TITLE_COL: #ffffff becomes #fbeedd",
                 "scripts/generate_og_cards.py, SUB_COL: #8aa0ff becomes #e2874a", "scripts/generate_og_cards.py, ACCENT: #8aa0ff becomes #e2874a",
                 "scripts/generate_og_cards.py, FOOTER_COL: #9696aa becomes #c4ae98"]
        (_c, dry), (_c2, out) = self.both_runs("--json")
        for report in (dry, out):
            changes = json.loads(report)["changes"]
            self.assertEqual(changes[-len(other):], other)
            self.assertEqual(changes[0], "Primary: #000000 becomes #b4531a", "the stylesheet's own come first, as they did")
        self.assertEqual(json.loads(self.intake("--json")[1])["changes"], [], "and once they are in, nothing changes")
        self.fresh()
        code, out = self.intake("--dry-run")
        at = out.splitlines().index("Colours that would change in the site's other files:")
        self.assertEqual(out.splitlines()[at + 1:at + 1 + len(other)], ["  " + line for line in other])
        # cards that keep their colours (the text would not read on them) have no colour of theirs listed
        self.brand_md(BAKERY_BRAND_MD.partition("### Dark theme\n")[0] + "### Dark theme\n" + table([(l, GREY_DARK[k]) for k, l in LABELS]))
        changes = json.loads(self.intake("--json", "--dry-run")[1])["changes"]
        self.assertEqual([c for c in changes if c.startswith("scripts/")], [])
        self.assertIn("src/config.ts, themeColor: #000000 becomes #b4531a", changes)

    # --- a file that is there is never taken for one that is not --------------------------------

    @POSIX
    def test_a_file_or_a_folder_that_is_there_and_closed_to_this_account_stops_the_run_with_its_path_and_the_reason(self):
        self.not_as_root()
        for name, rel, make, named in (("a folder of the site", "src", None, "src/styles/global.css"),
                                       ("the palette", "BRAND.md", None, "BRAND.md"),
                                       ("the folder the palette is kept in", "docs", "docs/BRAND.md", "docs/BRAND.md"),
                                       ("the installed logo", "public/favicon.svg", "public/favicon.svg", "public/favicon.svg"),
                                       ("a file it would write", "public/manifest.webmanifest", None, "public/manifest.webmanifest")):
            with self.subTest(name=name):
                self.fresh()
                if make == "docs/BRAND.md":
                    os.makedirs(self.p("docs"))
                    os.replace(self.p("BRAND.md"), self.p("docs/BRAND.md"))
                elif make:
                    self.put(make, _install.MARK.encode("utf-8") + _svg.clean_svg(T.real_svg()).text.encode("utf-8"))
                before = self.snapshot()
                was = self.closed(rel)
                try:
                    runs = self.both_runs(brand=False)
                finally:
                    os.chmod(self.p(rel), was)
                for code, out in runs:
                    self.assertEqual(code, 2, out)
                    self.assertIn("%s could not be read or written (Permission denied)" % self.p(named), out)
                    self.assertIn("Nothing was written.", out)
                    for untrue in ("does not look like a site", "nothing to do", "no complete palette"):
                        self.assertNotIn(untrue, out)
                self.assertEqual(self.snapshot(), before)

    # --- the share cards' folder is put back the way every other file is ---------------------------

    @POSIX
    def test_something_in_the_share_cards_folder_that_cannot_be_read_is_refused_by_name_before_anything_is_written(self):
        # left out of what is kept, it would be gone once the folder was put back, under "everything was put back"
        self.not_as_root()
        self.brand_md()
        os.makedirs(self.p("public/images/og/drafts"))
        self.put("public/images/og/drafts/note.txt", b"a note")
        before = self.snapshot()
        for rel, said in (("public/images/og/drafts", "public/images/og/drafts cannot be listed (Permission denied)"),
                          ("public/images/og/default.jpg", "public/images/og/default.jpg cannot be read (Permission denied)"),
                          ("public/images/og/drafts/note.txt", "public/images/og/drafts/note.txt cannot be read (Permission denied)")):
            with self.subTest(rel=rel):
                was = self.closed(rel)
                try:
                    runs = self.both_runs() + [self.intake(command=RED)]
                finally:
                    os.chmod(self.p(rel), was)
                for code, out in runs:
                    self.assertEqual(code, 2, out)
                    self.assertIn(said, out)
                    self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)

    def test_a_share_cards_folder_that_is_a_link_or_lies_behind_one_is_refused_before_anything_is_written(self):
        for rel in ("public/images/og", "public/images"):
            with self.subTest(rel=rel):
                self.fresh()
                elsewhere = os.path.join(self.tmp.name, "kept-elsewhere-" + os.path.basename(rel))
                os.rename(self.p(rel), elsewhere)
                os.symlink(elsewhere, self.p(rel))
                kept, links = tree(elsewhere), self.links()
                modes = {base: os.stat(base).st_mode for base, _dirs, _files in os.walk(elsewhere)}
                for code, out in self.both_runs() + [self.intake(command=RED)]:
                    self.assertEqual(code, 2, out)
                    self.assertIn("public/images/og is a link", out)
                    self.assertIn("Nothing was written", out)
                    self.assertEqual((tree(elsewhere), self.links()), (kept, links))
                    self.assertEqual({base: os.stat(base).st_mode for base, _dirs, _files in os.walk(elsewhere)}, modes, "no mode was changed through the link")

    def test_on_a_site_that_had_no_images_folder_none_is_left_behind_when_the_run_is_taken_back(self):
        T.require_pillow(self)
        self.brand_md()
        shutil.rmtree(self.p("public/images"))
        before = self.snapshot()
        code, out = self.intake("--json", command=RED)
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["cards"]), (1, "tests-failed", "restored"), out)
        self.assertEqual(self.snapshot(), before, "the folder the generator made is gone again, and the one above it")
        # and when the generator itself stops after it made the folder
        gen = self.read("scripts/generate_og_cards.py")
        self.put("scripts/generate_og_cards.py", gen.replace("def main():\n", "def main():\n    OUT.mkdir(parents=True, exist_ok=True)\n    (OUT / 'default.jpg').write_bytes(b'half way')\n"
                                                             "    raise SystemExit('simulated: a later card failed')\n", 1))
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        self.assertIn("the generator failed (simulated: a later card failed)", out)
        self.assertFalse(self.exists("public/images"))

    @POSIX
    def test_whatever_the_tests_did_to_the_share_cards_folder_it_is_put_back_in_place_file_by_file(self):
        T.require_pillow(self)
        self.not_as_root()
        self.brand_md()
        os.makedirs(self.p("public/images/og/drafts/empty"))
        self.put("public/images/og/drafts/note.txt", b"a note")
        self.put("public/images/og/about.jpg", b"the about card")
        before, folder = self.snapshot(), os.stat(self.p("public/images/og")).st_ino
        once = os.path.join(self.tmp.name, "wrecked-once")   # the tests are run a second time, and must not undo the putting back
        wreck = "; ".join(("if [ -e '%s' ]; then exit 1; fi" % once, "touch '%s'" % once, "cd public/images/og", "rm about.jpg", "mkdir about.jpg",
                           "echo x > extra.jpg", "mkdir -p new/deeper", "echo y > new/deeper/card.jpg", "chmod 000 new/deeper", "rm -r drafts", "echo z > drafts",
                           "ln -s ../logo.png linked.png", "chmod 555 . ..", "exit 1"))
        for rel in ("public/images", "public/images/og"):
            self.addCleanup(os.chmod, self.p(rel), 0o755)
        code, out = self.intake("--json", command=wreck)
        os.chmod(self.p("public/images"), 0o755)   # the folder above is not the run's to change, and it did not need it
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["cards"], data.get("not_restored")), (1, "tests-failed", "restored", None), out)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(os.stat(self.p("public/images/og")).st_ino, folder, "the folder itself was never deleted")
        self.assertEqual(stat.S_IMODE(os.stat(self.p("public/images/og")).st_mode), 0o755)

    def test_a_card_that_cannot_be_put_back_is_named_by_its_own_name_and_the_cards_around_it_are_put_back(self):
        T.require_pillow(self)
        self.brand_md()
        for name in ("about.jpg", "zebra.jpg"):
            self.put("public/images/og/" + name, b"a card of her own")
        before = self.snapshot()
        real = _site.Journal._put

        def refusing(journal, path, data, mode=0o644):
            if path.endswith(os.path.join("og", "default.jpg")):
                raise PermissionError(13, "Permission denied", path)
            return real(journal, path, data, mode)
        _site.Journal._put = refusing
        try:
            code, out = self.intake("--json", command="echo x > public/images/og/about.jpg; echo x > public/images/og/zebra.jpg; exit 1")
        finally:
            _site.Journal._put = real
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["cards"]), (1, "rollback-incomplete", "not-restored"), out)
        self.assertEqual(data["not_restored"], [{"file": "public/images/og/default.jpg", "why": "Permission denied"}])
        self.assertIn("  public/images/og/default.jpg (Permission denied)", data["report"])
        after = self.snapshot()
        card = os.path.join("public", "images", "og", "default.jpg")
        self.assertNotEqual(after[card], before[card])
        after[card] = before[card]
        self.assertEqual(after, before, "the card before it and the card after it are back, and every other file")

    def test_a_generator_that_fails_leaves_cards_that_cannot_be_put_back_named_and_nothing_else_of_the_run(self):
        T.require_pillow(self)   # without it the generator stops before it writes anything
        self.brand_md()
        gen = self.read("scripts/generate_og_cards.py")
        self.put("scripts/generate_og_cards.py", gen.replace("def main():\n", "def main():\n    (OUT / 'default.jpg').write_bytes(b'half way')\n    raise SystemExit('simulated: a later card failed')\n", 1))
        before = self.snapshot()
        real = _site.Journal._put

        def refusing(journal, path, data, mode=0o644):
            if path.endswith(os.path.join("og", "default.jpg")):
                raise PermissionError(13, "Permission denied", path)
            return real(journal, path, data, mode)
        _site.Journal._put = refusing
        try:
            code, out = self.intake("--json")
        finally:
            _site.Journal._put = real
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["code"]), (2, "rollback-incomplete", "cards-not-restored"), out)
        self.assertEqual([l["file"] for l in data["not_restored"]], ["public/images/og/default.jpg"])
        after = self.snapshot()
        after[os.path.join("public", "images", "og", "default.jpg")] = before[os.path.join("public", "images", "og", "default.jpg")]
        self.assertEqual(after, before)

    # --- what is said ----------------------------------------------------------------------------

    def test_keeping_the_colours_with_no_logo_says_that_and_does_not_say_no_palette_was_found(self):
        self.brand_md()
        code, out = self.intake("--keep-colours")
        self.assertEqual(code, 2, out)
        self.assertIn("There is nothing to do: --keep-colours leaves the palette in BRAND.md out, and no logo file was given.", out)
        self.assertNotIn("no complete palette was found", out)
        self.brand_md(BAKERY_BRAND_MD.replace("| Soft background | `#fef5e8` |\n", ""))   # where that is the reason, it is still the reason given
        for extra in ((), ("--keep-colours",)):
            self.assertIn("There is nothing to do: no complete palette was found in BRAND.md, and no logo file was given.", self.intake(*extra)[1])
        os.remove(self.p("BRAND.md"))
        self.assertIn("There is nothing to do: no complete palette was found, and no logo file was given.", self.intake(brand=False)[1])

    def test_the_share_cards_are_named_in_the_dry_run_and_under_written_also_when_no_file_is_written(self):
        T.require_pillow(self)
        self.brand_md()
        code, out = self.intake("--dry-run")
        self.assertIn("  the share cards under public/images/og would be made again", out.splitlines())
        code, out = self.intake()
        self.assertEqual(out.splitlines()[out.splitlines().index("Written:") + 5], "  the share cards under public/images/og, made again")
        code, out = self.intake("--dry-run")   # everything is in already: no file would be written, and the cards would still be made again
        at = out.splitlines().index("  nothing: every file is already as this run would write it")
        self.assertEqual(out.splitlines()[at + 1], "  the share cards under public/images/og would be made again")
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        at = out.splitlines().index("Written:")
        self.assertEqual(out.splitlines()[at + 1:at + 3], ["  nothing: every file was already as this run writes it", "  the share cards under public/images/og, made again"])

    def test_red_tests_whose_output_names_no_check_in_a_form_this_tool_reads_are_said_to_be_that_with_their_last_lines(self):
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--json", command="echo 'FAIL src/a.test.js'; echo '  expected 1, got 2' >&2; exit 1")
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["failing"], data["output_tail"]), (1, "tests-failed", [], ["FAIL src/a.test.js", "expected 1, got 2"]))
        said = [l for l in data["report"] if "does not name the failing checks in a form this tool reads" in l]
        self.assertEqual(len(said), 1, data["report"])
        self.assertIn("Its last lines: FAIL src/a.test.js; expected 1, got 2.", said[0])
        for untrue in ("printed nothing", "The failing check"):
            self.assertEqual([l for l in data["report"] if untrue in l], [])
        self.assertEqual(self.snapshot(), before)

    def test_what_the_tests_print_is_read_as_utf8_whatever_this_computers_own_encoding_is(self):
        self.brand_md()
        real, seen = _install._run, []

        def watching(command, cwd, timeout, shell=False, env=None, encoding=None):
            if shell:
                seen.append(encoding)
            return real(command, cwd, timeout, shell=shell, env=env, encoding=encoding)
        _install._run = watching
        try:
            code, out = self.intake("--json", command=RED)
            raw_code, raw = self.intake("--json", command="printf 'caf\\351 \\377\\376 failed\\n'; exit 1")
        finally:
            _install._run = real
        self.assertEqual(seen, ["utf-8"] * 4, "the tests with the install and with it taken out again, both times")
        self.assertEqual(json.loads(out)["failing"], ["tests/a11y.spec.ts:8:5 \u203a a11y \u2014 / [dark]", "tests/seo.spec.ts:20:3 \u203a theme colour"])
        self.assertEqual((raw_code, json.loads(raw)["output_tail"]), (1, ["caf\ufffd \ufffd\ufffd failed"]), "bytes that are no UTF-8 are shown as that, and stop nothing")

    @POSIX
    def test_what_a_test_command_left_running_is_stopped_once_the_command_has_ended(self):
        # a preview server it started and did not stop would hold the site's port for the second run and after
        self.brand_md()
        pids = os.path.join(self.tmp.name, "started")
        self.addCleanup(self.stop_leftovers, pids)
        for ending, code_wanted, runs in (("exit 1", 1, 2), ("exit 0", 0, 1)):
            with self.subTest(ending=ending):
                if os.path.exists(pids):
                    os.remove(pids)
                code, out = self.intake(command="(sleep 300 > /dev/null 2>&1 & echo $! >> '%s'); %s" % (pids, ending))
                self.assertEqual(code, code_wanted, out)
                started = [int(pid) for pid in T.read(pids).split()]
                self.assertEqual(len(started), runs)
                for pid in started:
                    self.assertTrue(self.gone(pid), "what the test command started (%d) is still running" % pid)

    def test_a_web_page_is_not_taken_for_a_logo_and_the_refusal_says_what_to_hand_over_instead(self):
        page = (b'<!doctype html><html><body><h1>Logo</h1><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8">'
                b'<rect width="8" height="8" fill="#b4531a"/></svg></body></html>')
        before = self.snapshot()
        for name in ("logo.html", "logo.svg"):   # what a file is, is read from its content
            with self.subTest(name=name):
                path = self.package(name, page)
                for code, out in self.both_runs("--input", path, brand=False):
                    self.assertEqual(code, 2, out)
                    self.assertIn("This looks like a web page", out)
                    self.assertIn("Ask the tool for the SVG file itself", out)
                    self.assertIn("Nothing was written", out)
                    self.assertEqual(self.snapshot(), before)
                data = json.loads(self.intake("--input", path, "--json", brand=False)[1])
                self.assertEqual((data["status"], data["exit"], data["code"], data["written"]), ("refused", 2, "web-page", []))
                self.assertIn(data["message"], data["report"])
        only = os.path.join(self.tmp.name, "only-a-page")   # a folder is looked through for a zip or an SVG, and for nothing else
        os.makedirs(only)
        with open(os.path.join(only, "logo.html"), "wb") as f:
            f.write(page)
        code, out = self.intake("--input", only, brand=False)
        self.assertEqual(code, 2, out)
        self.assertIn("that folder holds no .zip or .svg file", out)
        self.assertEqual(self.snapshot(), before)


class TheIconsWaitForTheImageLibrary(SiteCase):
    """A run about colours on a site whose logo this tool installed, on a computer where sharp does not load."""
    modules = False

    def setUp(self):
        super().setUp()
        self.brand_md()
        self.clean = _svg.clean_svg(T.real_svg(T.REAL_COLOUR)).text.encode("utf-8")
        self.installed = _install.MARK.encode("utf-8") + self.clean

    def test_the_colours_go_in_the_icons_are_left_and_the_report_says_what_to_run_later(self):
        self.put("public/favicon.svg", self.installed)
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code), (0, 0), out)
        self.assertEqual(json.loads(dry)["written"], json.loads(out)["written"])
        self.assertEqual(json.loads(dry)["notes"], json.loads(out)["notes"])
        note = [n for n in json.loads(out)["notes"] if n.startswith("the icons were left as they are")]
        self.assertEqual(len(note), 1, json.loads(out)["notes"])
        for said in ("they could not be drawn again here", "sharp", "That does not hold the colours back", "npm install --include=optional", "--with-logo"):
            self.assertIn(said, note[0])
        self.assertNotIn("is not a file this tool wrote", note[0])
        self.assertEqual([w for w in json.loads(out)["written"] if w.startswith(("public/favicon", "public/icon", "public/apple", "public/images/logo", "brand-handoff"))], [])
        self.assertEqual(self.bytes("public/favicon.svg"), self.installed)
        self.assertFalse(self.exists("public/favicon.ico"))
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT, "the colours are in")

    def test_asked_for_outright_the_icons_cannot_wait_and_the_run_stops_with_what_to_install(self):
        self.put("public/favicon.svg", self.installed)
        before = self.snapshot()
        for code, out in self.both_runs("--with-logo"):
            self.assertEqual(code, 2, out)
            self.assertIn("npm install --include=optional", out)
            self.assertIn("Nothing was written", out)
            self.assertEqual(self.snapshot(), before)

    def test_a_clean_favicon_without_this_tools_line_is_hers_and_the_image_library_is_not_even_asked_for(self):
        self.put("public/favicon.svg", self.clean)
        asked = []
        real = _install._render.Renderer.preflight
        _install._render.Renderer.preflight = lambda renderer: asked.append(renderer) or real(renderer)
        try:
            (dry_code, dry), (code, out) = self.both_runs()
        finally:
            _install._render.Renderer.preflight = real
        self.assertEqual((dry_code, code, asked), (0, 0, []), out)
        for report in (dry, out):
            self.assertIn("the icons were left as they are: public/favicon.svg is not a file this tool wrote", report)
            self.assertNotIn("sharp", report)
        self.assertEqual(self.bytes("public/favicon.svg"), self.clean)


class StoppedFromOutside(SiteCase):
    """A stop is a signal: SIGTERM (an assistant's shell tool ends a command), SIGHUP (the terminal is
    closed), SIGINT (Ctrl-C). Whenever it comes, the run ends in words with exit status 2, the site as it
    was, and nothing of its own left running or lying about."""
    modules = False

    def setUp(self):
        if os.name != "posix":
            self.skipTest("signals as POSIX has them")
        super().setUp()
        self.brand_md()

    AT = "real = %s\ndef stopped_here(*args, **kwargs):\n    os.kill(os.getpid(), signal.%s)\n    return real(*args, **kwargs)\n%s = stopped_here\n"

    def test_a_stop_while_the_run_is_still_planning_ends_in_words_with_nothing_written_and_no_temporary_folder_left(self):
        before = self.snapshot()
        for name in ("SIGTERM", "SIGHUP", "SIGINT"):
            for extra in ((), ("--json",), ("--dry-run",)):
                with self.subTest(signal=name, extra=extra):
                    scratch = tempfile.mkdtemp(dir=self.tmp.name)
                    r = self.drive(self.AT % ("_site.edit_css", name, "_site.edit_css"), *extra, tmpdir=scratch)
                    self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout + r.stderr)
                    said = "\n".join(json.loads(r.stdout)["report"]) if extra == ("--json",) else r.stdout
                    self.assertIn("The run was stopped from outside (%s) before it had finished" % name, said)
                    self.assertIn("Nothing was written.", said)
                    self.assertIn("Colours that would have changed in src/styles/global.css:", said)
                    if extra == ("--json",):
                        data = json.loads(r.stdout)
                        self.assertEqual((data["status"], data["exit"], data["written"], data.get("rolled_back")), ("stopped", 2, [], None))
                    self.assertEqual(os.listdir(scratch), [], "the folder the icons are drawn in is gone again")
                    self.assertEqual(self.snapshot(), before)

    def test_a_stop_at_any_step_of_the_writing_leaves_the_site_as_it_was(self):
        before = self.snapshot()
        moments = (("just before the first file is replaced", "os.replace"), ("just after a folder was looked at", "os.path.isdir"),
                   ("while the share cards are made", "_install.regenerate_cards"), ("while the stylesheet is read back", "_install._palette.read_css"))
        for moment, where in moments:
            with self.subTest(moment=moment):
                patch = ("real_write = _site.Journal.write\ndef write(journal, rel, data):\n    global armed\n    armed = True\n    return real_write(journal, rel, data)\n"
                         "_site.Journal.write = write\narmed = False\nreal = %s\ndef stopped_here(*args, **kwargs):\n    global armed\n    if armed:\n        armed = False\n"
                         "        os.kill(os.getpid(), signal.SIGTERM)\n    return real(*args, **kwargs)\n%s = stopped_here\n" % (where, where))
                r = self.drive(patch)
                self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout + r.stderr)
                self.assertIn("stopped from outside (SIGTERM)", r.stdout)
                self.assertTrue("Everything it had written was put back." in r.stdout or "Nothing was written." in r.stdout, r.stdout)
                self.assertEqual(self.snapshot(), before)

    def test_a_stop_that_comes_once_the_install_stands_does_not_make_the_report_say_that_nothing_was_written(self):
        # the tests have passed and nothing will be put back any more: the report must say what is in the site
        r = self.drive(self.AT % ("_install._changes_lines", "SIGTERM", "_install._changes_lines"))
        self.assertEqual((r.returncode, r.stderr), (0, ""), r.stdout + r.stderr)
        self.assertIn("Done. The site's own tests pass afterwards.", r.stdout)
        self.assertNotIn("stopped from outside", r.stdout)
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT, "and it is in")

    def test_more_signals_while_the_files_are_put_back_and_while_the_report_is_made_change_nothing(self):
        # one stop is enough: a second Ctrl-C, or a shell that sends SIGTERM and then SIGHUP, must neither cut
        # the putting back short nor the report
        before = self.snapshot()
        again = "    for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):\n        os.kill(os.getpid(), s)\n"
        patch = ("real_rollback = _site.Journal.rollback\ndef rollback(journal):\n" + again + "    return real_rollback(journal)\n_site.Journal.rollback = rollback\n"
                 "real_install = _install.install\ndef install(a, out):\n    result = real_install(a, out)\n" + again + "    return result\n_install.install = install\n")
        for first in ("TERM", "INT"):
            with self.subTest(first=first):
                sleep, running = self.sleeper()
                r = self.drive(patch, command="kill -%s $PPID; %s" % (first, sleep))
                self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout + r.stderr)
                self.assertIn("stopped from outside (SIG%s)" % first, r.stdout)
                self.assertIn("Everything it had written was put back.", r.stdout)
                self.assertEqual(self.snapshot(), before)
                self.assertTrue(self.none_left(running), "what the test command was just starting is still running")
        r = self.drive(patch, command=RED)   # the first signal arrives while red tests are being undone
        self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout + r.stderr)
        self.assertIn("stopped from outside (SIGINT)", r.stdout)
        self.assertIn("Everything it had written was put back.", r.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_a_signal_the_run_was_started_to_ignore_stays_ignored(self):
        # `nohup` starts a command with SIGHUP ignored, a shell starts a background job with SIGINT ignored:
        # the run must not begin to listen to what it was told to ignore
        for name in ("HUP", "INT"):
            with self.subTest(signal=name):
                self.put("src/styles/global.css", T.starter_file("src/styles/global.css"))
                r = self.drive("", ignored=("SIG" + name,), command="kill -%s $PPID; sleep 1" % name)
                self.assertEqual((r.returncode, r.stderr), (0, ""), r.stdout + r.stderr)
                self.assertIn("Done.", r.stdout)
                self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT)
        before = self.snapshot()
        sleep, running = self.sleeper()
        r = self.drive("", ignored=("SIGHUP",), command="kill -TERM $PPID; " + sleep)   # and the others still stop it
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.none_left(running))


class ALogoOnASiteAsSheLeftIt(SiteCase):
    """The same round, for a run that installs a logo (sharp is needed)."""

    WHITE = rects((4, 4, 24, 24, "#ffffff"))

    def fresh(self):
        shutil.rmtree(self.site)
        T.make_starter_site(self.site, with_modules=self.modules)

    def logo(self, *more):
        return ("--input", self.package()) + LOGO_ARGS + more

    # --- what the logo is checked against --------------------------------------------------------

    def test_a_logo_beside_a_palette_the_reading_does_not_use_goes_in_and_the_report_says_why_the_colours_stayed(self):
        night = BAKERY_BRAND_MD.replace("### Dark theme", "### Night")
        for name, text, head in (("no colour read", OTHER_HEADINGS, "Note: the colours were not changed: no colour could be read from the palette in BRAND.md"),
                                 ("one table read and one not", night, "Note: the colours were not changed: BRAND.md does not hold a complete palette (rows not filled in: "
                                  "Accent, Background, Body (ink), Hairline, Heading, Link, Muted, Soft background, Surface (cards))")):
            with self.subTest(name=name):
                self.fresh()
                self.brand_md(text)
                read = _palette.parse_tables(text)
                stylesheet = self.read("src/styles/global.css")
                for code, out in self.both_runs(*self.logo()):
                    self.assertEqual(code, 0, out)
                    lines = out.splitlines()
                    at = lines.index(head)
                    self.assertEqual(lines[at + 1:at + 1 + len(read.problems)], ["  " + m for _theme, _row, _code, m in read.problems])
                    self.assertEqual("  " + _palette.FORM in lines, not read.rows_found)
                self.assertEqual(self.read("src/styles/global.css"), stylesheet)
                self.assertTrue(self.exists("public/images/logo.png"))

    def test_a_logo_is_not_checked_against_the_sites_own_colours_when_this_tool_could_not_read_all_of_them(self):
        css = T.starter_file("src/styles/global.css")
        for name, text in (("a colour block written in another way than the starter's", css.replace(":root {", ":root, html {", 1)),
                           ("a colour that points at a variable nothing sets", css.replace("  --bg: #ffffff;", "  --bg: var(--paper);", 1)),
                           ("a dark block that stands twice", css + '\n:root[data-theme="dark"] {\n  --bg: #222222;\n}\n'),
                           ("a colour marked important", css.replace("  --bg-soft: #f5f7fb;", "  --bg-soft: #f5f7fb !important;", 1))):
            for keep in (False, True):   # a logo alone, and a logo beside a palette she said to leave out
                with self.subTest(name=name, keep=keep):
                    self.assertNotEqual(text, css)
                    self.fresh()
                    self.put("src/styles/global.css", text)
                    if keep:
                        self.brand_md()
                    problems = _install._css_problems(_palette.read_css(text))
                    self.assertTrue(problems)
                    before = self.snapshot()
                    for code, out in self.both_runs(*self.logo(*(("--keep-colours",) if keep else ())), brand=keep):
                        self.assertEqual(code, 2, out)
                        self.assertIn("this tool could not read all of them from src/styles/global.css:", out)
                        for said in problems:
                            self.assertIn(said, out.splitlines())
                        self.assertIn("Nothing was written.", out.splitlines())
                        self.assertEqual(self.snapshot(), before)
                    self.assertEqual(json.loads(self.intake(*self.logo("--json", *(("--keep-colours",) if keep else ())), brand=keep)[1])["code"], "site-colours-unread")

    # --- the favicon this tool installed is known by its own line ---------------------------------

    def test_the_installed_favicon_starts_with_this_tools_line_is_still_one_svg_and_is_known_again_by_the_next_run(self):
        import xml.dom.minidom
        self.assertEqual(self.intake(*self.logo(), brand=False)[0], 0)
        data, line = self.bytes("public/favicon.svg"), _install.MARK.encode("utf-8")
        self.assertTrue(data.startswith(line))
        self.assertRegex(_install.MARK, r"^<!-- [^\n]* -->\n$")
        self.assertNotIn("--", _install.MARK[4:-4], "two hyphens would end the comment early")
        body = data[len(line):]
        self.assertEqual(_svg.clean_svg(body).text.encode("utf-8"), body, "the rest is the cleaned drawing")
        self.assertEqual(_svg.clean_svg(data).text.encode("utf-8"), body, "and the line is no part of the drawing")
        self.assertEqual(xml.dom.minidom.parseString(data).documentElement.tagName, "svg")
        after_first = self.snapshot()
        self.assertEqual(self.intake(*self.logo(), brand=False)[0], 0)
        self.assertEqual(self.snapshot(), after_first, "a second run sees its own file and writes nothing")
        self.brand_md()   # the colours change: the file is known as this tool's own, and the icons are drawn again
        code, out = self.intake("--accept-colours", "--accept-low-contrast", "both", "--replace-icons")
        self.assertEqual(code, 0, out)
        self.assertNotIn("is not a file this tool wrote", out)
        self.assertEqual(self.bytes("public/favicon.svg"), data)
        import _png
        self.assertEqual(_png.at(_png.decode(self.bytes("public/icon-maskable-512.png")), 0, 0)[:3], (0xff, 0xf8, 0xee), "on the palette's background")

    # --- the share cards' emblem ----------------------------------------------------------------

    def low(self, cards, mark):
        return " and ".join("%s %s would fall to %s to 1 over the mark's %s" % (_palette.LABEL[k], h, _colour.shown(r), c) for k, h, r, c in _site.og_emblem_low(cards, mark))

    def test_a_mark_under_which_the_cards_text_would_not_read_is_not_made_their_emblem_and_the_colours_still_go_in(self):
        self.brand_md()
        args = ("--input", self.package("white.svg", self.WHITE), "--with-colours", "--accept-colours", "--accept-low-contrast", "both")
        why = self.low(bakery(), ["#ffffff"])
        self.assertIn("Accent #e2874a would fall to 3.2 to 1 over the mark's #ffffff", why)
        (dry_code, dry), (code, out) = self.both_runs(*args)
        self.assertEqual((dry_code, code), (0, 0), out)
        for report in (dry, out):
            self.assertIn("Note: the share cards go without the emblem (the logo, shown faintly on the right of each card).", report)
            self.assertIn("and there %s; text needs 4.5 to 1." % why, report)
            self.assertNotIn("goes back to None", report)
        generator = self.read("scripts/generate_og_cards.py")
        self.assertIn("LOGO = None", generator)
        self.assertRegex(generator, r"(?m)^BG_BOT = \(26, 18, 13\)", "the cards' colours are the palette's all the same")
        self.assertIn("and COMPANY.logo points at public/images/logo.png.", out)
        for untrue in ("the share cards' emblem point at", "and the emblem"):
            self.assertNotIn(untrue, out)
        self.assertTrue(self.exists("public/images/logo.png"))
        self.assertIn("logo: '/images/logo.png'", self.read("src/config.ts"))

    def test_a_logo_alone_is_held_against_the_colours_the_cards_already_have(self):
        generator = self.read("scripts/generate_og_cards.py")
        why = self.low(_install.palette_from_cards(_site.og_colours(generator)), ["#ffffff"])
        self.assertIn("Accent #8aa0ff would fall to 3.46 to 1 over the mark's #ffffff", why)
        args = ("--input", self.package("white.svg", self.WHITE), "--accept-colours", "--accept-low-contrast", "both")
        for code, out in self.both_runs(*args, brand=False):
            self.assertEqual(code, 0, out)
            self.assertIn("the share cards go without the emblem", out)
            self.assertIn(why, out)
        self.assertEqual(self.read("scripts/generate_og_cards.py"), generator, "not a line of the generator is changed")
        self.fresh()   # the bakery's own mark reads on the starter's cards: it is their emblem
        code, out = self.intake(*self.logo(), brand=False)
        self.assertEqual(code, 0, out)
        self.assertIn('LOGO = ROOT / "public/images/logo.png"', self.read("scripts/generate_og_cards.py"))
        self.assertIn("COMPANY.logo and the share cards' emblem point at public/images/logo.png.", out)
        self.assertNotIn("go without the emblem", out)

    def test_an_emblem_an_earlier_run_set_is_taken_out_when_the_new_colours_would_not_read_over_it(self):
        self.brand_md()
        self.assertEqual(self.intake(*self.logo("--with-colours"))[0], 0)
        self.assertIn('LOGO = ROOT / "public/images/logo.png"', self.read("scripts/generate_og_cards.py"))
        self.assertIn("| Accent | `#e2874a` |", BAKERY_BRAND_MD)
        self.brand_md(BAKERY_BRAND_MD.replace("| Accent | `#e2874a` |", "| Accent | `#d47c44` |"))   # passes every pair and the gradient
        cards = bakery()
        cards.dark["accent"] = "#d47c44"
        self.assertEqual((_site.og_low_contrast(cards), [p for p in _palette.matrix(cards) if not p.ok]), ([], []))
        why = self.low(cards, ["#b4531a", "#6b2c0b"])
        self.assertIn("Accent #d47c44 would fall to 4.33 to 1 over the mark's #b4531a", why)
        for code, out in self.both_runs("--accept-colours", "--accept-low-contrast", "both"):
            self.assertEqual(code, 0, out)
            self.assertIn("the share cards go without the emblem (the logo, shown faintly on the right of each card), so the LOGO line an earlier run set there goes back to None.", out)
            self.assertIn(why, out)
        generator = self.read("scripts/generate_og_cards.py")
        self.assertIn("LOGO = None", generator)
        self.assertIn("SUB_COL = (212, 124, 68)", generator)

    def test_an_emblem_she_pointed_somewhere_herself_is_left_and_new_colours_under_it_are_said_to_be_unchecked(self):
        self.brand_md()
        wired = self.read("scripts/generate_og_cards.py").replace("LOGO = None", 'LOGO = ROOT / "public/mine.png"')
        self.put("scripts/generate_og_cards.py", wired)
        for code, out in self.both_runs(brand=True):
            self.assertEqual(code, 0, out)
            self.assertIn("Whether the text can still be read there was not checked, because the emblem is a picture this tool did not install", out)
        self.assertIn('LOGO = ROOT / "public/mine.png"', self.read("scripts/generate_og_cards.py"))

    # --- the colours a logo run would change, in all four files ---------------------------------

    def test_a_logo_run_asks_before_it_changes_a_colour_she_set_by_hand_in_any_of_the_four_files(self):
        # the stylesheet already shows the palette, so it has nothing to say; the other three hold colours too
        self.brand_md()
        self.assertEqual(self.intake()[0], 0)
        settled = {rel: self.read(rel) for rel in _install.OTHER_FILES}
        hand = (("src/config.ts", "themeColor: '#b4531a'", "themeColor: '#123456'", "src/config.ts, themeColor: #123456 becomes #b4531a"),
                ("public/manifest.webmanifest", '"theme_color": "#b4531a"', '"theme_color": "#123456"', "public/manifest.webmanifest, theme_color: #123456 becomes #b4531a"),
                ("public/manifest.webmanifest", '"background_color": "#fff8ee"', '"background_color": "#654321"', "public/manifest.webmanifest, background_color: #654321 becomes #fff8ee"),
                ("scripts/generate_og_cards.py", "BG_TOP = (42, 31, 23)", "BG_TOP = (1, 2, 3)", "scripts/generate_og_cards.py, BG_TOP: #010203 becomes #2a1f17"),
                ("scripts/generate_og_cards.py", "FOOTER_COL = (196, 174, 152)", "FOOTER_COL = (200, 200, 200)", "scripts/generate_og_cards.py, FOOTER_COL: #c8c8c8 becomes #c4ae98"))
        for rel, old, new, line in hand:
            with self.subTest(line=line):
                for other, text in settled.items():
                    self.put(other, text)
                self.assertEqual(settled[rel].count(old), 1)
                self.put(rel, settled[rel].replace(old, new))
                before = self.snapshot()
                for code, out in self.both_runs(*self.logo()):
                    self.assertEqual(code, 3, out)
                    self.assertIn("    * " + line, out.splitlines())
                    self.assertIn("--with-colours", out)
                    self.assertIn("--keep-colours", out)
                    self.assertIn("Nothing was written", out)
                    self.assertEqual(self.snapshot(), before)
                data = json.loads(self.intake(*self.logo("--json"))[1])
                self.assertEqual(([k["code"] for k in data["asks"]], data["asks"][0]["options"], data["changes"]), (["colours-too"], [line], [line]))
                code, out = self.intake(*self.logo("--keep-colours"))
                self.assertEqual(code, 0, out)
                self.assertIn(new, self.read(rel), "kept, as she said")
                self.put(rel, settled[rel].replace(old, new))
                code, out = self.intake(*self.logo("--with-colours"))
                self.assertEqual(code, 0, out)
                self.assertIn(old, self.read(rel))
                at = out.splitlines().index("Colours that changed in the site's other files:")
                self.assertEqual(out.splitlines()[at + 1], "  " + line)
                self.assertNotIn("Colours that changed in src/styles/global.css:", out)

    def test_a_question_about_something_else_still_lists_the_colours_the_run_would_change_and_the_question_about_them_lists_them_once(self):
        self.brand_md()
        self.put("public/apple-touch-icon.png", b"somebody's own icon")
        before = self.snapshot()
        for code, out in self.both_runs(*self.logo("--with-colours")):
            self.assertEqual(code, 3, out)
            self.assertIn("public/apple-touch-icon.png", out)
            for line in ("Colours that would change in src/styles/global.css:", "  Primary: #000000 becomes #b4531a",
                         "Colours that would change in the site's other files:", "  src/config.ts, themeColor: #000000 becomes #b4531a"):
                self.assertIn(line, out.splitlines())
            self.assertEqual(self.snapshot(), before)
        data = json.loads(self.intake(*self.logo("--with-colours", "--json"))[1])
        self.assertEqual([k["code"] for k in data["asks"]], ["replace-icons"])
        self.assertIn("Primary: #000000 becomes #b4531a", data["changes"])
        self.assertIn("public/manifest.webmanifest, background_color: #ffffff becomes #fff8ee", data["changes"])
        code, out = self.intake("--input", self.package(), "--with-colours")   # two drawings in the zip: which one is asked first
        self.assertEqual(code, 3, out)
        self.assertIn(T.REAL_MONO, out)
        self.assertIn("  Primary: #000000 becomes #b4531a", out.splitlines())
        code, out = self.intake(*self.logo())   # the question about the colours themselves names each once
        self.assertEqual(code, 3, out)
        self.assertEqual(out.count("Primary: #000000 becomes #b4531a"), 1)

    # --- a file that is there is never taken for one that is not --------------------------------

    @POSIX
    def test_a_file_the_run_would_replace_or_draw_from_that_is_closed_to_this_account_stops_it_before_anything_is_written(self):
        self.not_as_root()
        master = _install.MARK.encode("utf-8") + _svg.clean_svg(T.real_svg()).text.encode("utf-8")
        for name, rel, data, args in (("an icon it would replace", "public/favicon.ico", b"an icon of her own", self.logo("--replace-icons")),
                                      ("a package kept from an earlier run", "brand-handoff/logo.zip", b"an earlier package", self.logo()),
                                      ("the preview sheet of an earlier run", "brand-handoff/preview.png", b"an earlier preview", self.logo()),
                                      ("the installed logo, asked for outright", "public/favicon.svg", master, ("--with-logo", "--accept-colours", "--accept-low-contrast", "both")),
                                      ("the installed logo, with a new one given", "public/favicon.svg", master, self.logo("--replace-icons"))):
            with self.subTest(name=name):
                self.fresh()
                os.makedirs(os.path.dirname(self.p(rel)), exist_ok=True)
                self.put(rel, data)
                before = self.snapshot()
                was = self.closed(rel)
                try:
                    runs = self.both_runs(*args, brand=False)
                finally:
                    os.chmod(self.p(rel), was)
                for code, out in runs:
                    self.assertEqual(code, 2, out)
                    self.assertIn("%s could not be read or written (Permission denied)" % self.p(rel), out)
                    self.assertIn("Nothing was written.", out)
                    self.assertNotIn("no logo to apply", out)
                self.assertEqual(self.snapshot(), before)

    def test_a_planned_file_that_is_a_link_or_lies_behind_one_is_refused_before_anything_is_written_whatever_the_link_points_at(self):
        outside = os.path.join(self.tmp.name, "outside")
        os.makedirs(os.path.join(outside, "folder"))
        with open(os.path.join(outside, "file.ico"), "wb") as f:
            f.write(b"an icon kept elsewhere")
        for name, rel, target in (("a link to a file", "public/favicon.ico", os.path.join(outside, "file.ico")),
                                  ("a link to a folder", "public/favicon.ico", os.path.join(outside, "folder")),
                                  ("a link to nothing", "public/favicon.ico", os.path.join(outside, "nothing-here")),
                                  ("a link where a folder above the file would be", "brand-handoff", os.path.join(outside, "folder"))):
            with self.subTest(name=name):
                self.fresh()
                os.symlink(target, self.p(rel))
                links, kept = self.links(), tree(outside)
                before = None if name == "a link to nothing" else self.snapshot()   # a link to nothing cannot be read to compare it
                for code, out in self.both_runs(*self.logo("--replace-icons"), brand=False):
                    self.assertEqual(code, 2, out)
                    self.assertIn("%s is a link, and nothing is written through a link." % ("brand-handoff/logo.zip" if rel == "brand-handoff" else rel), out)
                    self.assertIn("Nothing was written", out)
                    self.assertEqual((self.links(), tree(outside)), (links, kept))
                    if before is not None:
                        self.assertEqual(self.snapshot(), before)
                    self.assertFalse(self.exists("public/images/logo.png"))

    # --- what is said, by what happened ----------------------------------------------------------

    def test_a_note_about_something_the_run_changes_says_would_before_was_after_and_put_back_when_it_was_taken_back(self):
        placeholder = b"<svg>placeholder</svg>"
        self.put("public/favicon.svg", placeholder)
        self.put("src/config.ts", self.read("src/config.ts").replace("logo: '/images/logo.png',", "logo: '/brand/own-logo.svg',"))
        before = self.snapshot()
        old = _site.SCAFFOLD_DEFAULTS
        _site.SCAFFOLD_DEFAULTS = {"public/favicon.svg": {hashlib.sha256(placeholder).hexdigest()}}
        try:
            dry = json.loads(self.intake(*self.logo("--json", "--dry-run"), brand=False)[1])
            red = json.loads(self.intake(*self.logo("--json"), command=RED, brand=False)[1])
            self.put("brand-handoff", b"a file where the folder would go")   # refused by the check of every path: nothing is written
            refused = json.loads(self.intake(*self.logo("--json"), brand=False)[1])
            os.remove(self.p("brand-handoff"))
            done = json.loads(self.intake(*self.logo("--json"), brand=False)[1])
        finally:
            _site.SCAFFOLD_DEFAULTS = old
        self.assertEqual((dry["status"], red["status"], refused["status"], done["status"]), ("dry-run", "tests-failed", "refused", "done"))
        would = ["public/favicon.svg is the scaffold's placeholder (the Astro logo), which this run would replace",
                 "COMPANY.logo in src/config.ts points at /brand/own-logo.svg; this run would point it at /images/logo.png, the picture made from this logo, and leave "
                 "the file it points at where it is"]
        for data in (dry, refused):
            self.assertEqual([n for n in data["notes"] if "placeholder" in n or "COMPANY.logo" in n], would)
        self.assertEqual([n for n in red["notes"] if "placeholder" in n or "COMPANY.logo" in n],
                         ["public/favicon.svg is the scaffold's placeholder (the Astro logo): this run replaced it and then put it back",
                          "COMPANY.logo in src/config.ts points at /brand/own-logo.svg, as before: this run pointed it at /images/logo.png and then put that back"])
        self.assertEqual([n for n in done["notes"] if "placeholder" in n or "COMPANY.logo" in n],
                         ["public/favicon.svg was the scaffold's placeholder (the Astro logo), now replaced",
                          "COMPANY.logo in src/config.ts pointed at /brand/own-logo.svg; it now points at /images/logo.png, the picture made from this logo. The file it "
                          "pointed at is left where it is"])
        for data in (dry, red, refused):
            for note in data["notes"]:
                for untrue in ("now replaced", "it now points at", "has the palette"):
                    self.assertNotIn(untrue, note)

    def test_a_company_logo_with_an_escaped_quote_in_it_is_refused_by_name_and_a_run_that_does_not_touch_it_goes_through(self):
        self.put("src/config.ts", self.read("src/config.ts").replace("logo: '/images/logo.png',", "logo: '/it\\'s.png',"))
        self.assertIn("logo: '/it\\'s.png',", self.read("src/config.ts"))
        before = self.snapshot()
        for code, out in self.both_runs(*self.logo(), brand=False):
            self.assertEqual(code, 2, out)
            self.assertIn("the value of `logo` in COMPANY has a backslash in it", out)
            self.assertIn("Nothing was written", out)
            self.assertEqual(self.snapshot(), before)
        self.brand_md()   # the colours alone do not touch that line
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        self.assertIn("logo: '/it\\'s.png',", self.read("src/config.ts"))
        self.assertIn("themeColor: '#b4531a'", self.read("src/config.ts"))

    def test_the_folders_line_goes_to_the_end_of_gitignore_whenever_a_later_line_could_take_it_back_and_ends_as_the_files_lines_end(self):
        starter = self.bytes(".gitignore").decode("utf-8")
        self.assertNotIn("\r", starter)
        for name, text, end in (("a later line that names no folder", starter + "brand-handoff/*\n!*.svg\n", "\n"),
                                ("the same in a file with Windows line ends", (starter + "brand-handoff/\n!*\n").replace("\n", "\r\n"), "\r\n"),
                                ("a rule with spaces before it, which git reads as part of the name", starter + "  brand-handoff/\n", "\n")):
            with self.subTest(name=name):
                self.fresh()
                self.put(".gitignore", text.encode("utf-8"))
                code, out = self.intake(*self.logo(), brand=False)
                self.assertEqual(code, 0, out)
                self.assertEqual(self.bytes(".gitignore").decode("utf-8"), text + "brand-handoff/" + end)
                self.assertIn("(git ignores that folder)", out)
                self.assertEqual(self.intake(*self.logo(), brand=False)[0], 0)
                self.assertEqual(self.bytes(".gitignore").decode("utf-8"), text + "brand-handoff/" + end, "and it is not added a second time")

    # --- stopped from outside while a logo goes in ------------------------------------------------

    @POSIX
    def test_a_stop_while_the_icons_are_drawn_or_just_after_a_folder_was_made_leaves_nothing_behind(self):
        before = self.snapshot()
        drawn = StoppedFromOutside.AT % ("_icons.build", "SIGTERM", "_icons.build")
        made = ("real = os.mkdir\ndef stopped_here(path, *args, **kwargs):\n    real(path, *args, **kwargs)\n    if os.path.basename(path) == 'brand-handoff':\n"
                "        os.kill(os.getpid(), signal.SIGTERM)\nos.mkdir = stopped_here\n")
        for moment, patch, said in (("while the icons are drawn", drawn, "Nothing was written."), ("just after brand-handoff was made", made, "Everything it had written was put back.")):
            with self.subTest(moment=moment):
                scratch = tempfile.mkdtemp(dir=self.tmp.name)
                r = self.drive(patch, *self.logo(), tmpdir=scratch)
                self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout + r.stderr)
                self.assertIn("stopped from outside (SIGTERM)", r.stdout)
                self.assertIn(said, r.stdout)
                self.assertEqual(os.listdir(scratch), [], "the folder the icons were drawn in is gone")
                self.assertEqual(self.snapshot(), before)
                self.assertFalse(self.exists("brand-handoff"))


class NoSharp(SiteCase):
    """Scenario 19, the half that stops."""
    modules = False

    def test_a_logo_without_sharp_stops_before_writing_with_the_command_to_run(self):
        before = self.snapshot()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", brand=False)
        self.assertEqual(code, 2, out)
        self.assertIn("npm install --include=optional", out)
        self.assertIn("package.json", out)
        self.assertEqual(self.snapshot(), before)


class BothParts(SiteCase):
    def test_the_whole_run_and_what_it_leaves_behind(self):
        T.require_pillow(self)
        self.brand_md()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--mono", T.REAL_MONO, "--with-colours", "--accept-colours",
                                "--accept-low-contrast", "dark")
        self.assertEqual(code, 0, out)
        css = _palette.read_css(self.read("src/styles/global.css"))
        self.assertEqual((css.light, css.dark, css.dark_media), (T.BAKERY_LIGHT, T.BAKERY_DARK, T.BAKERY_DARK))
        self.assertTrue(self.exists("public/images/logo.png"))
        self.assertTrue(self.exists("brand-handoff/logo.zip"))
        self.assertIn("Done", out)
        self.assertIn("src/styles/global.css", out)
        self.assertIn("public/icon-maskable-512.png", out)

    def test_a_palette_after_launch_starts_from_the_installed_master_not_the_placeholder(self):
        # scenario 16: the logo is already installed; only the colours change
        self.brand_md()
        args = ("--input", self.package(), "--pick", T.REAL_COLOUR, "--with-colours", "--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(self.intake(*args)[0], 0)
        master = self.read("public/favicon.svg")
        warmer = BAKERY_BRAND_MD.replace(T.BAKERY_LIGHT["bg"], "#fffaf2")
        self.brand_md(warmer)
        code, out = self.intake("--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(code, 3, out)
        self.assertIn("public/apple-touch-icon.png", out, "the icons that depend on the background are asked about")
        code, out = self.intake("--accept-colours", "--accept-low-contrast", "both", "--replace-icons")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read("public/favicon.svg"), master, "the master is what it was")
        import _png
        pic = _png.decode(self.bytes("public/icon-maskable-512.png"))
        self.assertEqual(_png.at(pic, 0, 0), (0xff, 0xfa, 0xf2, 255), "the new light background is under the maskable icon")


if __name__ == "__main__":
    unittest.main()
