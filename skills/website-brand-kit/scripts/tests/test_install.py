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
import tempfile
import unittest

import _testutil as T
import brand_intake
import _palette
import _site
from test_palette import LABELS, STARTER_DARK, STARTER_LIGHT, table
from test_site_edits import tree

GREEN = "true"
# what Playwright's list reporter prints for a failure (octal escapes: every sh's printf reads them)
RED = ("printf '  1) [chromium] \\342\\200\\272 tests/a11y.spec.ts:8:5 \\342\\200\\272 a11y \\342\\200\\224 / [dark] \\342\\224\\200\\342\\224\\200\\n"
       "  2) [chromium] \\342\\200\\272 tests/seo.spec.ts:20:3 \\342\\200\\272 theme colour\\n'; exit 1")
BAKERY_BRAND_MD = (
    "# Bäckerei Example: brand & style guide\n\n## Colour palette\n\n### Brand (fixed, theme-independent)\n"
    "| Token | Hex | Use |\n|---|---|---|\n| Primary | `#b4531a` | buttons, brand surfaces |\n\n"
    "### Light theme\n" + table([(l, T.BAKERY_LIGHT[k]) for k, l in LABELS]) + "\n"
    "### Dark theme\n" + table([(l, T.BAKERY_DARK[k]) for k, l in LABELS]))


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
        # the same suite is red without the install, and the report says so
        self.assertIn("without", out.lower())

    def test_when_the_tests_are_green_before_and_red_only_after_the_report_says_the_install_did_it(self):
        self.brand_md()
        marker = os.path.join(self.tmp.name, "ran-once")
        flip = "if [ -e %s ]; then exit 0; else touch %s; printf '  1) [chromium] x tests/a11y.spec.ts\\n'; exit 1; fi" % (marker, marker)
        code, out = self.intake(command=flip)
        self.assertEqual(code, 1, out)
        self.assertIn("pass without", out.lower())

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
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-low-contrast", "both")
        self.assertEqual(code, 3, out)
        self.assertIn("#6b2c0b", out)
        self.assertIn("not in", out)
        self.assertFalse(self.exists("public/favicon.svg"))
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(code, 0, out)
        self.assertIn("#6b2c0b", self.read("public/favicon.svg"))

    def test_scenario_15_a_colour_that_vanishes_on_a_theme_is_named_with_the_theme_and_the_one_colour_way_out(self):
        self.brand_md()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--mono", T.REAL_MONO, "--accept-colours")
        self.assertEqual(code, 3, out)
        self.assertIn("dark", out)
        self.assertIn("1.7", out)
        self.assertIn("one-colour", out)
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--mono", T.REAL_MONO, "--accept-colours",
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
            code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        finally:
            _site.SCAFFOLD_DEFAULTS = old
        self.assertEqual(code, 0, out)
        self.assertIn("placeholder", out)
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
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--mono", T.REAL_MONO, "--accept-colours",
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
        args = ("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both")
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
