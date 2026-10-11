"""Scenarios 7, 9, 10 (the palette side), 28: the palette the owner pastes, the rows it must
have, and the contrast check that names a failing pair before anything is written.

The matrix is every text colour on every background colour, in both themes. That is wider than
the starter's stylesheet uses today (it styles `--ink` and `--link` on `--bg`, and `--ink` on
`--surface`), on purpose: a stylesheet that starts using `--muted` on `--bg-soft` should not be
the first time anyone checks the pair. A test below holds the matrix to the stylesheet it
protects, so a new pair in the CSS that the matrix lacks fails here.
"""

import re
import unittest

import _testutil as T
import _colour
import _palette
from _refusal import Refusal

STARTER_LIGHT = {"heading": "#16162a", "ink": "#16162a", "muted": "#5a5a72", "accent": "#2b50e0", "link": "#2b50e0",
                 "line": "#e3e7f2", "bg": "#ffffff", "bg_soft": "#f5f7fb", "surface": "#ffffff"}
STARTER_DARK = {"heading": "#e7e9fb", "ink": "#dce0f5", "muted": "#a6abce", "accent": "#8aa0ff", "link": "#9fb0ff",
                "line": "#272c4d", "bg": "#0a0b1e", "bg_soft": "#11132c", "surface": "#161836"}
LABELS = [("heading", "Heading"), ("ink", "Body (ink)"), ("muted", "Muted"), ("accent", "Accent"), ("link", "Link"),
          ("line", "Hairline"), ("bg", "Background"), ("bg_soft", "Soft background"), ("surface", "Surface (cards)")]


def table(rows):
    return "| Token | Hex |\n|---|---|\n" + "\n".join("| %s | `%s` |" % (label, value) for label, value in rows) + "\n"


def brand_md(light=STARTER_LIGHT, dark=STARTER_DARK, primary="#000000", extra=""):
    return (
        "# Example Bakery: brand & style guide\n\n## Colour palette\n\n### Brand (fixed, theme-independent)\n"
        "| Token | Hex | Use |\n|---|---|---|\n| Primary | `%s` | buttons, brand surfaces |\n\n" % primary
        + "### Light theme\n" + table([(l, light[k]) for k, l in LABELS if k in light]) + "\n"
        + "### Dark theme\n" + table([(l, dark[k]) for k, l in LABELS if k in dark]) + extra
    )


class Reading(unittest.TestCase):
    def test_the_extended_table_is_read_into_both_themes(self):
        p = _palette.parse_tables(brand_md())
        self.assertEqual(p.light, STARTER_LIGHT)
        self.assertEqual(p.dark, STARTER_DARK)
        self.assertEqual(p.brand, "#000000")
        self.assertEqual(p.missing(), [])
        self.assertEqual(p.problems, [])

    def test_every_colour_format_in_a_cell_is_read_as_the_same_hex(self):
        light = dict(STARTER_LIGHT, bg="rgb(255, 255, 255)", surface="WHITE", ink="#16162A", heading="hsl(240 30% 12%)",
                     muted="oklch(0.5 0.04 280)")
        p = _palette.parse_tables(brand_md(light=light))
        self.assertEqual(p.light["bg"], "#ffffff")
        self.assertEqual(p.light["surface"], "#ffffff")
        self.assertEqual(p.light["ink"], "#16162a")
        self.assertEqual(p.light["heading"], _colour.parse_colour("hsl(240 30% 12%)"))
        self.assertEqual(p.light["muted"], _colour.parse_colour("oklch(0.5 0.04 280)"))

    def test_a_cell_with_words_around_the_colour(self):
        light = dict(STARTER_LIGHT, accent="#2B50E0 (buttons and links)", bg="**#ffffff**")
        p = _palette.parse_tables(brand_md(light=light))
        self.assertEqual(p.light["accent"], "#2b50e0")
        self.assertEqual(p.light["bg"], "#ffffff")

    def test_one_table_with_a_light_and_a_dark_column(self):
        # what a tool may well hand back when asked for "the token table"
        md = ("| Token | Light | Dark |\n|---|---|---|\n"
              + "\n".join("| %s | %s | %s |" % (l, STARTER_LIGHT[k], STARTER_DARK[k]) for k, l in LABELS) + "\n")
        p = _palette.parse_tables(md)
        self.assertEqual(p.light, STARTER_LIGHT)
        self.assertEqual(p.dark, STARTER_DARK)

    def test_unusual_headings_still_pick_the_theme(self):
        md = ("**Palette 2, light theme**\n" + table([(l, STARTER_LIGHT[k]) for k, l in LABELS])
              + "\nDark theme:\n" + table([(l, STARTER_DARK[k]) for k, l in LABELS]))
        p = _palette.parse_tables(md)
        self.assertEqual((p.light, p.dark), (STARTER_LIGHT, STARTER_DARK))

    def test_a_colour_that_cannot_be_read_is_named_not_dropped(self):
        light = dict(STARTER_LIGHT, muted="rgba(90, 90, 114, 0.8)", accent="notacolour")
        p = _palette.parse_tables(brand_md(light=light))
        by = {(t, k): (code, msg) for t, k, code, msg in p.problems}
        self.assertEqual(by[("light", "muted")][0], "colour-alpha")
        self.assertEqual(by[("light", "accent")][0], "colour-unreadable")
        self.assertIn("Muted", by[("light", "muted")][1])
        self.assertIn(("light", "muted"), p.missing(), "a row that cannot be read is a row she has not given")

    def test_two_palettes_pasted_together_are_not_guessed_between(self):
        other = dict(STARTER_LIGHT, accent="#c0392b")
        with self.assertRaises(Refusal) as cm:
            _palette.parse_tables(brand_md() + "\n### Light theme\n" + table([(l, other[k]) for k, l in LABELS]))
        self.assertEqual(cm.exception.code, "palette-ambiguous")
        # the same table twice is not a conflict
        _palette.parse_tables(brand_md() + "\n### Light theme\n" + table([(l, STARTER_LIGHT[k]) for k, l in LABELS]))

    def test_a_row_given_twice_with_two_values_is_ambiguous_too(self):
        with self.assertRaises(Refusal) as cm:
            _palette.parse_tables(brand_md(extra="| Muted | `#777777` |\n"))
        self.assertEqual(cm.exception.code, "palette-ambiguous")


class Incomplete(unittest.TestCase):
    """Scenario 9: a palette may lack the dark theme, or a row the stylesheet needs."""

    def test_no_dark_theme_at_all(self):
        md = "### Light theme\n" + table([(l, STARTER_LIGHT[k]) for k, l in LABELS])
        p = _palette.parse_tables(md)
        self.assertEqual(sorted(k for t, k in p.missing() if t == "dark"), sorted(STARTER_DARK))
        self.assertEqual([k for t, k in p.missing() if t == "light"], [])

    def test_the_old_template_layout_lacks_the_rows_the_new_one_adds(self):
        # BRAND.md as the template has it today: one fixed Accent, no Link, no Soft background
        old_light = {k: v for k, v in STARTER_LIGHT.items() if k not in ("accent", "link", "bg_soft")}
        old_dark = {k: v for k, v in STARTER_DARK.items() if k not in ("accent", "link", "bg_soft")}
        md = ("### Brand (fixed, theme-independent)\n| Token | Hex | Use |\n|---|---|---|\n| Primary | `#000000` | x |\n"
              "| Accent | `#2b50e0` | links |\n\n### Light theme\n" + table([(l, old_light[k]) for k, l in LABELS if k in old_light])
              + "\n### Dark theme\n" + table([(l, old_dark[k]) for k, l in LABELS if k in old_dark]))
        p = _palette.parse_tables(md)
        self.assertEqual(p.light["accent"], "#2b50e0")
        self.assertEqual(p.dark["accent"], "#2b50e0", "a fixed accent is the accent in both themes")
        self.assertEqual(sorted(p.missing()), sorted([("light", "link"), ("light", "bg_soft"), ("dark", "link"), ("dark", "bg_soft")]))

    def test_the_template_as_shipped_is_all_missing_not_an_error(self):
        p = _palette.parse_tables(T.read(T.BRAND_TEMPLATE))
        self.assertEqual(len(p.missing()), 18)
        self.assertEqual(p.problems, [])

    def test_a_themed_accent_wins_over_the_fixed_one(self):
        # a BRAND.md halfway between the two layouts: the fixed row stays, and a dark accent exists
        md = brand_md().replace("| Primary | `#000000` | buttons, brand surfaces |", "| Primary | `#000000` | buttons |\n| Accent | `#2b50e0` | links |")
        p = _palette.parse_tables(md)
        self.assertEqual(p.light["accent"], "#2b50e0")
        self.assertEqual(p.dark["accent"], "#8aa0ff")

    def test_a_primary_row_in_a_theme_table_is_not_a_theme_colour(self):
        p = _palette.parse_tables(brand_md().replace("| Muted | `#5a5a72` |", "| Primary | `#123456` |\n| Muted | `#5a5a72` |", 1))
        self.assertNotIn("brand", p.light)
        self.assertEqual(p.brand, "#000000")

    def test_a_heading_naming_both_themes_does_not_pick_one(self):
        md = "### Light and dark themes\n" + table([(l, STARTER_LIGHT[k]) for k, l in LABELS])
        p = _palette.parse_tables(md)
        self.assertEqual((p.light, p.dark), ({}, {}))
        self.assertEqual({c for _t, _k, c, _m in p.problems}, {"palette-no-theme"})

    def test_a_table_with_no_heading_at_all_is_named_not_dropped(self):
        p = _palette.parse_tables(table([("Muted", "#5a5a72")]))
        self.assertEqual([(t, k, c) for t, k, c, _m in p.problems], [("?", "muted", "palette-no-theme")])

    def test_a_proposal_is_marked_and_stays_a_proposal_until_the_marker_goes(self):
        dark = dict(STARTER_DARK, muted="#a6abce (proposed)")
        p = _palette.parse_tables(brand_md(dark=dark))
        self.assertEqual(p.dark["muted"], "#a6abce")
        self.assertEqual(p.proposed, {("dark", "muted")})
        self.assertEqual(_palette.parse_tables(brand_md()).proposed, set())


class Matrix(unittest.TestCase):
    def test_every_text_colour_on_every_background_in_both_themes(self):
        pairs = _palette.matrix(_palette.parse_tables(brand_md()))
        self.assertEqual(len(pairs), 2 * 5 * 3)
        self.assertEqual({p.theme for p in pairs}, {"light", "dark"})
        self.assertEqual({p.fg for p in pairs}, {"heading", "ink", "muted", "link", "accent"})
        self.assertEqual({p.bg for p in pairs}, {"bg", "bg_soft", "surface"})
        self.assertTrue(all(p.need == 4.5 for p in pairs))

    def test_the_starters_own_palette_passes_all_of_it(self):
        # the matrix may not be stricter than what the suite itself ships
        pairs = _palette.matrix(_palette.parse_tables(brand_md()))
        self.assertEqual([p for p in pairs if not p.ok], [])
        self.assertGreater(min(p.ratio for p in pairs), 5.0)

    def test_the_matrix_covers_every_pair_the_starters_stylesheet_uses(self):
        css = T.starter_file("src/styles/global.css")
        text_vars = set(re.findall(r"(?<![-\w])color:\s*var\(--([\w-]+)\)", css))
        bg_vars = set(re.findall(r"background(?:-color)?:\s*var\(--([\w-]+)\)", css))
        self.assertTrue(text_vars and bg_vars, "the starter's stylesheet no longer uses colour tokens this test can see")
        key = {"bg-soft": "bg_soft"}
        covered = {(p.fg, p.bg) for p in _palette.matrix(_palette.parse_tables(brand_md()))}
        for fg in text_vars:
            for bg in bg_vars:
                with self.subTest(fg=fg, bg=bg):
                    self.assertIn((key.get(fg, fg), key.get(bg, bg)), covered)

    def test_a_failing_pair_is_named_with_both_hexes_its_ratio_and_the_ratio_it_needs(self):
        # Scenario 7: muted text on the dark background at about 3.1 to 1
        dark = dict(STARTER_DARK, muted="#5c5f80")
        p = _palette.parse_tables(brand_md(dark=dark))
        bad = [x for x in _palette.matrix(p) if not x.ok]
        self.assertIn(("dark", "muted", "bg"), {(x.theme, x.fg, x.bg) for x in bad})
        self.assertEqual({(x.theme, x.fg) for x in bad}, {("dark", "muted")}, "only the muted text can have failed")
        first = [x for x in bad if x.bg == "bg"][0]
        line = _palette.describe(first)
        for part in ("dark", "#5c5f80", "#0a0b1e", "4.5"):
            self.assertIn(part, line)
        self.assertIn(_colour.shown(first.ratio), line)
        self.assertTrue(3.0 < first.ratio < 3.5, first.ratio)

    def test_a_pair_just_under_the_line_fails_even_though_it_prints_as_4_5(self):
        light = dict(STARTER_LIGHT, muted="#7c7480")
        bad = [x for x in _palette.matrix(_palette.parse_tables(brand_md(light=light))) if not x.ok]
        self.assertTrue(bad)
        self.assertNotIn("4.50", _palette.describe(bad[0]))

    def test_a_missing_background_makes_no_pairs_either(self):
        dark = {k: v for k, v in STARTER_DARK.items() if k != "bg_soft"}
        pairs = _palette.matrix(_palette.parse_tables(brand_md(dark=dark)))
        self.assertEqual(len(pairs), 2 * 5 * 3 - 5)
        self.assertFalse([p for p in pairs if p.bg == "bg_soft" and p.theme == "dark"])

    def test_a_row_that_is_missing_makes_no_pairs_but_is_listed(self):
        light = {k: v for k, v in STARTER_LIGHT.items() if k != "muted"}
        p = _palette.parse_tables(brand_md(light=light))
        pairs = _palette.matrix(p)
        self.assertEqual(len(pairs), 2 * 5 * 3 - 3)
        self.assertEqual(p.missing(), [("light", "muted")])


class Stylesheet(unittest.TestCase):
    def test_the_starters_stylesheet_reads_the_same_as_the_extended_table(self):
        css = _palette.read_css(T.starter_file("src/styles/global.css"))
        p = _palette.parse_tables(brand_md())
        self.assertEqual(css.light, STARTER_LIGHT)
        self.assertEqual(css.dark, STARTER_DARK)
        self.assertEqual(css.dark_media, STARTER_DARK)
        self.assertEqual(css.brand, "#000000")
        self.assertEqual(_palette.drift(p, css), [])

    def test_drift_between_the_doc_and_the_stylesheet_is_named(self):
        css = _palette.read_css(T.starter_file("src/styles/global.css"))
        p = _palette.parse_tables(brand_md(light=dict(STARTER_LIGHT, accent="#c0392b"), dark=dict(STARTER_DARK, bg="#000000")))
        d = _palette.drift(p, css)
        self.assertIn(("light", "accent"), [(t, k) for t, k, *_ in d])
        self.assertIn(("dark", "bg"), [(t, k) for t, k, *_ in d])

    def test_a_different_primary_is_drift_too(self):
        css = _palette.read_css(T.starter_file("src/styles/global.css"))
        d = _palette.drift(_palette.parse_tables(brand_md(primary="#112233")), css)
        self.assertEqual([x for x in d if x[0] == "brand"], [("brand", "brand", "#112233", "#000000")])

    def test_a_variable_the_dark_block_leaves_unset_comes_from_the_root_block(self):
        text = """:root { --accent: #2b50e0; --brand: #000000; }
:root[data-theme="dark"] { --link: var(--accent); --bg: #0a0b1e; }"""
        css = _palette.read_css(text)
        self.assertEqual(css.dark, {"link": "#2b50e0", "bg": "#0a0b1e"})
        self.assertEqual(css.found, {"light", "dark"})

    def test_the_media_block_and_the_dark_block_are_two_places_and_both_are_read(self):
        text = T.starter_file("src/styles/global.css").replace("--bg: #0a0b1e;\n    --bg-soft", "--bg: #000000;\n    --bg-soft")
        css = _palette.read_css(text)
        self.assertEqual(css.dark["bg"], "#0a0b1e")
        self.assertEqual(css.dark_media["bg"], "#000000")
        self.assertEqual(_palette.dark_blocks_disagree(css), [("bg", "#0a0b1e", "#000000")])

    def test_a_link_written_as_the_accent_is_read_as_the_accent(self):
        # the starter's :root has --link: var(--accent)
        self.assertIn("--link: var(--accent)", T.starter_file("src/styles/global.css"))
        self.assertEqual(_palette.read_css(T.starter_file("src/styles/global.css")).light["link"], "#2b50e0")


if __name__ == "__main__":
    unittest.main()
