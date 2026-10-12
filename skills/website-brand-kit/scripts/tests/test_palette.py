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


def rows(theme, **changed):
    """The nine rows of a theme as (label, value), with some values changed."""
    return [(l, changed.get(k, theme[k])) for k, l in LABELS]


def lines(theme, **changed):
    return ["| %s | %s |" % row for row in rows(theme, **changed)]


def codes(palette):
    return [(t, k, c) for t, k, c, _m in palette.problems]


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

    def test_two_different_primaries_are_not_guessed_between_either(self):
        # the last one used to win without a word: the theme colour and the manifest took whichever came later
        second = "\n### Brand\n| Token | Hex |\n|---|---|\n| Primary | `%s` |\n"
        for where, md in (("a second Brand table", brand_md() + second % "#123456"),
                          ("two rows of one table", brand_md().replace("| Primary | `#000000` | buttons, brand surfaces |",
                                                                       "| Primary | `#000000` | a |\n| Primary | `#123456` | b |")),
                          ("a Primary row in a theme table", brand_md(extra="| Primary | `#123456` |\n"))):
            with self.subTest(where=where):
                with self.assertRaises(Refusal) as cm:
                    _palette.parse_tables(md)
                self.assertEqual(cm.exception.code, "palette-ambiguous")
                for part in ("Primary", "#000000", "#123456"):
                    self.assertIn(part, str(cm.exception))
        # the same Primary twice, in any spelling, is not a conflict
        self.assertEqual(_palette.parse_tables(brand_md() + second % "rgb(0, 0, 0)").brand, "#000000")

    def test_two_different_fixed_accents_in_the_brand_table_are_not_guessed_between(self):
        md = "### Brand\n| Token | Hex |\n|---|---|\n| Accent | #111111 |\n| Accent | %s |\n"
        with self.assertRaises(Refusal) as cm:
            _palette.parse_tables(md % "#222222")
        self.assertEqual(cm.exception.code, "palette-ambiguous")
        self.assertIn("Accent", str(cm.exception))
        self.assertEqual(_palette.parse_tables(md % "#111111").light["accent"], "#111111")

    def test_a_colour_name_in_a_column_before_the_value_is_not_taken_for_the_value(self):
        # | Background | Beige | #c9bfa6 |: the name beige is #f5f5dc, a colour nobody chose, and the check passed on it
        for order in ("| %(label)s | %(name)s | %(value)s |", "| %(label)s | %(value)s | %(name)s |", "| %(label)s | %(name)s | `%(value)s` | page |"):
            with self.subTest(order=order):
                body = "\n".join(order % {"label": l, "name": "Beige" if k == "bg" else "Ink", "value": "#c9bfa6" if k == "bg" else STARTER_LIGHT[k]}
                                 for k, l in LABELS)
                p = _palette.parse_tables("### Light theme\n| Token | Name | Hex |\n|---|---|---|\n" + body + "\n")
                self.assertEqual(p.light["bg"], "#c9bfa6")
                self.assertEqual(p.light, dict(STARTER_LIGHT, bg="#c9bfa6"))
                self.assertEqual(p.problems, [])
        # with no other colour in the row, a name is the value, as before
        self.assertEqual(_palette.parse_tables("### Light theme\n" + table([("Background", "Beige")])).light, {"bg": "#f5f5dc"})
        self.assertEqual(_palette.parse_tables("### Light theme\n| Token | Name | Hex |\n|---|---|---|\n| Background | Page | Beige |\n").light, {"bg": "#f5f5dc"})

    def test_a_row_that_holds_two_different_colours_is_named_and_neither_is_picked(self):
        for name, cells, both in (("two hexes", "#c9bfa6 | #101010", ["#c9bfa6", "#101010"]),
                                  ("a hex and a function", "#c9bfa6 | rgb(16, 16, 16)", ["#c9bfa6", "#101010"]),
                                  ("a hex among words and a hex", "#c9bfa6 (page) | #101010", ["#c9bfa6", "#101010"]),
                                  ("two names", "Beige | Snow", ["#f5f5dc", "#fffafa"])):
            with self.subTest(name=name):
                p = _palette.parse_tables("### Light theme\n| Token | A | B |\n|---|---|---|\n| Background | %s |\n| Muted | #5a5a72 | x |\n" % cells)
                self.assertNotIn("bg", p.light)
                self.assertEqual(p.light, {"muted": "#5a5a72"})
                self.assertEqual(codes(p), [("light", "bg", "palette-two-values")])
                for part in ["Background", "light"] + both:
                    self.assertIn(part, p.problems[0][3])
        # the same colour written twice is one colour
        p = _palette.parse_tables("### Light theme\n| Token | Hex | RGB |\n|---|---|---|\n| Background | #C9BFA6 | rgb(201, 191, 166) |\n")
        self.assertEqual((p.light, p.problems), ({"bg": "#c9bfa6"}, []))

    def test_a_style_guide_that_gives_each_colour_as_hex_rgb_and_hsl_reads_as_one_colour_a_row(self):
        # an owner's own guide often has all three columns, and whole-number hsl or a rounded rgb can land
        # a step or two from the hex beside it (here rgb's red is 203 where the hex says 201). The first
        # value written is taken.
        p = _palette.parse_tables("### Light theme\n| Token | Hex | RGB | HSL |\n|---|---|---|---|\n"
                                  "| Background | #c9bfa6 | rgb(203, 191, 166) | hsl(43, 24%, 72%) |\n")
        self.assertEqual((p.light, p.problems), ({"bg": "#c9bfa6"}, []))
        # three steps apart is a different colour, and is named
        p = _palette.parse_tables("### Light theme\n| Token | Hex | RGB |\n|---|---|---|\n| Background | #c9bfa6 | rgb(204, 191, 166) |\n")
        self.assertEqual(codes(p), [("light", "bg", "palette-two-values")])

    def test_a_see_through_colour_among_words_is_named_as_see_through(self):
        # the cell as a whole is "not a colour name"; what is wrong with it is the alpha in the hex inside
        for value, code, shown in (("#2b50e080 (buttons)", "colour-alpha", "#2b50e080"), ("buttons: rgba(43, 80, 224, 0.5)", "colour-alpha", "rgba(43, 80, 224, 0.5)"),
                                   ("oklch(0.7 0.4 150) accent", "colour-gamut", "oklch(0.7 0.4 150)")):
            with self.subTest(value=value):
                p = _palette.parse_tables(brand_md(light=dict(STARTER_LIGHT, accent=value)))
                self.assertEqual(codes(p), [("light", "accent", code)])
                self.assertIn(shown, p.problems[0][3])
                self.assertNotIn("colour name", p.problems[0][3])
        # words with no colour inside them keep the sentence about the words
        p = _palette.parse_tables(brand_md(light=dict(STARTER_LIGHT, accent="a warm blue")))
        self.assertEqual(codes(p), [("light", "accent", "colour-unreadable")])

    def test_a_colour_written_as_a_link_is_a_colour_and_the_templates_placeholders_are_still_not(self):
        for value in ("[#2b50e0](http://example.com/c)", "[#2B50E0]", "[`#2b50e0`](https://example.com/#top)"):
            with self.subTest(value=value):
                p = _palette.parse_tables(brand_md(light=dict(STARTER_LIGHT, accent=value)))
                self.assertEqual(p.light["accent"], "#2b50e0")
                self.assertEqual((p.missing(), p.problems), ([], []))
        for value in ("#[…]", "#[...]", "[hex]", "[…]", "#[hex]", "[ ]", "-", "—"):
            with self.subTest(value=value):
                p = _palette.parse_tables(brand_md(light=dict(STARTER_LIGHT, accent=value)))
                self.assertEqual((p.missing(), p.problems), ([("light", "accent")], []), "not filled in yet is not a mistake")

    def test_a_table_with_no_header_row_keeps_its_first_row(self):
        for name, md in (("no header", "### Light theme\n" + "\n".join(lines(STARTER_LIGHT)) + "\n"),
                         ("no header, a rule line on top", "### Light theme\n|---|---|\n" + "\n".join(lines(STARTER_LIGHT)) + "\n"),
                         ("no header, three columns", "### Light theme\n" + "\n".join(l + " use |" for l in lines(STARTER_LIGHT)) + "\n")):
            with self.subTest(name=name):
                p = _palette.parse_tables(md)
                self.assertEqual(p.light, STARTER_LIGHT)
                self.assertEqual(p.light["heading"], "#16162a", "the first row is a row")

    def test_a_blank_line_inside_a_table_does_not_cost_the_row_after_it(self):
        body = lines(STARTER_LIGHT)
        for cut in (1, 4, 8):
            with self.subTest(cut=cut):
                md = "### Light theme\n| Token | Hex |\n|---|---|\n" + "\n".join(body[:cut]) + "\n\n" + "\n".join(body[cut:]) + "\n"
                self.assertEqual(_palette.parse_tables(md).light, STARTER_LIGHT)
        # and a table with a light and a dark column goes on being read by its columns
        both = ["| %s | %s | %s |" % (l, STARTER_LIGHT[k], STARTER_DARK[k]) for k, l in LABELS]
        md = "| Token | Light | Dark |\n|---|---|---|\n" + "\n".join(both[:3]) + "\n\n\n" + "\n".join(both[3:]) + "\n"
        p = _palette.parse_tables(md)
        self.assertEqual((p.light, p.dark, p.problems), (STARTER_LIGHT, STARTER_DARK, []))
        # a new table after the blank line, with a header of its own, is read by that header
        md = ("| Token | Light | Dark |\n|---|---|---|\n" + "\n".join(both) + "\n\n### Brand\n\n| Token | Hex |\n|---|---|\n| Primary | #123456 |\n")
        self.assertEqual(_palette.parse_tables(md).brand, "#123456")

    def test_one_header_cell_naming_both_themes_is_not_a_light_and_a_dark_column(self):
        # "Light / Dark" set both columns to the same cell: both themes got the light values, and all passed
        for header in ("| Token | Light / Dark | Use |", "| Token | Light and dark | Use |", "| Token | Light, Dark | Use |"):
            with self.subTest(header=header):
                md = header + "\n|---|---|---|\n" + "\n".join("| %s | %s | x |" % row for row in rows(STARTER_LIGHT)) + "\n"
                p = _palette.parse_tables(md)
                self.assertEqual((p.light, p.dark), ({}, {}))
                self.assertEqual({c for _t, _k, c in codes(p)}, {"palette-no-theme"})
        # under a heading that names the theme, the same table is that theme's
        p = _palette.parse_tables("### Dark theme\n| Token | Light / Dark |\n|---|---|\n" + "\n".join(lines(STARTER_DARK)) + "\n")
        self.assertEqual((p.light, p.dark), ({}, STARTER_DARK))

    def test_a_secondary_brand_colour_is_not_the_muted_text(self):
        # an owner's Primary / Secondary / Accent palette: her second brand colour is no text colour
        p = _palette.parse_tables("### Light theme\n" + table([("Primary", "#111111"), ("Secondary", "#c0392b"), ("Accent", "#2b50e0")]))
        self.assertNotIn("muted", p.light)
        self.assertEqual(p.light, {"accent": "#2b50e0"})
        self.assertEqual(p.unused, [("Secondary", ["#c0392b"])], "and it is kept to be shown, not dropped")
        for label in ("Secondary text", "secondary text", "Muted text", "Muted"):
            with self.subTest(label=label):
                self.assertEqual(_palette.parse_tables("### Light theme\n" + table([(label, "#5a5a72")])).light, {"muted": "#5a5a72"})

    def test_a_row_under_a_name_it_does_not_know_is_kept_with_its_colour_to_be_shown(self):
        md = brand_md().replace("| Heading | `#16162a` |", "| Headings: | `#16162a` |").replace(
            "| Surface (cards) | `#ffffff` |", "| Surface / cards | `#ffffff` |").replace("| Link | `#2b50e0` |", "| --link | `#2b50e0` |")
        p = _palette.parse_tables(md + "| Success | - |\n| Warning | #aa5500 | #ffbb66 |\n")
        self.assertEqual(p.unused, [("Headings:", ["#16162a"]), ("--link", ["#2b50e0"]), ("Surface / cards", ["#ffffff"]),
                                    ("Warning", ["#aa5500", "#ffbb66"])])
        self.assertEqual(p.missing(), [("light", "heading"), ("light", "link"), ("light", "surface")])
        self.assertIn("Success", p.ignored)
        self.assertNotIn("Success", [label for label, _c in p.unused], "a row with no colour in it has nothing to show")
        self.assertEqual(_palette.parse_tables(brand_md()).unused, [])


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
        # it is the Primary all the same (see the next test); where the Brand table says another, see Reading
        p = _palette.parse_tables(brand_md().replace("| Muted | `#5a5a72` |", "| Primary | `#000000` |\n| Muted | `#5a5a72` |", 1))
        self.assertNotIn("brand", p.light)
        self.assertEqual(p.brand, "#000000")
        self.assertEqual(p.problems, [])

    def test_the_primary_is_read_wherever_its_row_stands(self):
        # outside a Brand table it was refused for having "no theme" (a plain table) or dropped unseen (a light | dark one)
        combined = "\n".join("| %s | %s | %s |" % (l, STARTER_LIGHT[k], STARTER_DARK[k]) for k, l in LABELS) + "\n"
        cases = (
            ("a theme table", "### Light theme\n" + table([("Primary", "#123456")] + rows(STARTER_LIGHT))),
            ("a table under no heading", table([("Primary", "#123456")])),
            ("a light | dark table, both cells", "| Token | Light | Dark |\n|---|---|---|\n| Primary | #123456 | #123456 |\n" + combined),
            ("a light | dark table, one cell", "| Token | Light | Dark |\n|---|---|---|\n| Primary | #123456 | |\n" + combined),
            ("a light | dark table, a cell beside them", "| Token | Light | Dark | Fixed |\n|---|---|---|---|\n| Primary | | | #123456 |\n" + combined),
        )
        for name, md in cases:
            with self.subTest(name=name):
                p = _palette.parse_tables(md)
                self.assertEqual(p.brand, "#123456")
                self.assertEqual(p.problems, [])
                self.assertNotIn("brand", p.light)
                self.assertNotIn("brand", p.dark)
        p = _palette.parse_tables("| Token | Light | Dark |\n|---|---|---|\n| Primary | #123456 | #654321 |\n" + combined)
        self.assertIsNone(p.brand, "one colour for both themes: a light and a dark one are two, and neither is picked")
        self.assertEqual(codes(p), [("brand", "brand", "palette-two-values")])
        self.assertEqual((p.light, p.dark), (STARTER_LIGHT, STARTER_DARK))
        p = _palette.parse_tables("### Light theme\n" + table([("Primary", "rgba(0, 0, 0, 0.5)")] + rows(STARTER_LIGHT)))
        self.assertEqual(codes(p), [("brand", "brand", "colour-alpha")], "and one that cannot be read is named for what it is")

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

    def test_a_proposed_primary_is_a_proposal_too(self):
        # the mark was dropped with the Primary: the check passed and the install wrote a colour nobody had confirmed
        for value in ("#000000 (proposed)", "`#000000` (proposed)", "#000000 (Proposed)"):
            with self.subTest(value=value):
                p = _palette.parse_tables(brand_md(primary=value))
                self.assertEqual(p.brand, "#000000")
                self.assertEqual(p.proposed, {("brand", "brand")})
                self.assertEqual(p.theme("brand"), {"brand": "#000000"}, "so that whoever lists the proposals can show its value")
        # given twice, proposed once: still a proposal
        twice = brand_md(primary="#000000 (proposed)") + "\n### Brand\n| Token | Hex |\n|---|---|\n| Primary | #000000 |\n"
        self.assertEqual(_palette.parse_tables(twice).proposed, {("brand", "brand")})
        self.assertEqual(_palette.Palette().theme("brand"), {})

    def test_a_proposed_fixed_accent_is_a_proposal_in_each_theme_that_takes_it(self):
        md = ("### Brand\n| Token | Hex |\n|---|---|\n| Accent | `#2b50e0` (proposed) |\n\n### Light theme\n" + table([("Background", "#ffffff")])
              + "\n### Dark theme\n" + table([("Accent", "#8aa0ff")]))
        p = _palette.parse_tables(md)
        self.assertEqual(p.proposed, {("light", "accent")}, "the dark theme has an accent of its own, which nobody proposed")

    def test_the_word_proposed_anywhere_in_a_row_marks_the_row(self):
        for name, row in (("in the label", "| Muted (proposed) | `#a6abce` |"), ("in a third column", "| Muted | `#a6abce` | (proposed) |"),
                          ("as proposal", "| Muted | `#a6abce` (proposal) |"), ("without brackets", "| Muted | `#a6abce` proposed |"),
                          ("before the value", "| Muted | proposed: `#a6abce` |"), ("in capitals", "| Muted | `#a6abce` | PROPOSED |"),
                          ("in a column before the value", "| Muted | proposed | `#a6abce` |"), ("in words", "| Muted | `#a6abce` | my proposal, not yet agreed |")):
            with self.subTest(name=name):
                p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", row))
                self.assertEqual(p.dark["muted"], "#a6abce")
                self.assertEqual(p.proposed, {("dark", "muted")})
                self.assertEqual((p.missing(), p.problems), ([], []))
        # a word that only contains it is not it
        p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | unproposed, purposed |"))
        self.assertEqual(p.proposed, set())

    def test_proposed_in_the_heading_over_a_table_or_in_its_header_row_marks_every_row_of_it(self):
        every = {("dark", k) for k in STARTER_DARK}
        for name, md in (("the heading", brand_md().replace("### Dark theme", "### Dark theme (proposed)")),
                         ("the heading, as proposal", brand_md().replace("### Dark theme", "### Proposal: dark theme")),
                         ("the header row", brand_md().replace("### Dark theme\n| Token | Hex |", "### Dark theme\n| Token | Hex (proposed) |")),
                         ("a label that is not a heading", brand_md().replace("### Dark theme", "**Dark theme (proposed)**"))):
            with self.subTest(name=name):
                p = _palette.parse_tables(md)
                self.assertEqual(p.proposed, every)
                self.assertEqual((p.light, p.dark), (STARTER_LIGHT, STARTER_DARK))
        # the next heading ends it
        p = _palette.parse_tables(brand_md().replace("### Light theme", "### Light theme (proposed)"))
        self.assertEqual(p.proposed, {("light", k) for k in STARTER_LIGHT})
        p = _palette.parse_tables(brand_md().replace("### Brand (fixed, theme-independent)", "### Brand (proposed)"))
        self.assertEqual(p.proposed, {("brand", "brand")})

    def test_proposed_over_one_table_is_not_said_of_the_table_under_the_next_heading_or_label(self):
        md = "Light theme (proposed):\n" + table(rows(STARTER_LIGHT)) + "\nDark theme:\n" + table(rows(STARTER_DARK))
        self.assertEqual(_palette.parse_tables(md).proposed, {("light", k) for k in STARTER_LIGHT})
        md = "### Dark theme (proposed)\n" + table(rows(STARTER_DARK)) + "\n### Light theme\n" + table(rows(STARTER_LIGHT))
        self.assertEqual(_palette.parse_tables(md).proposed, {("dark", k) for k in STARTER_DARK})

    def test_in_a_light_and_dark_table_a_mark_in_a_cell_is_that_theme_and_one_beside_them_is_both(self):
        head = "| Token | Light | Dark | Note |\n|---|---|---|---|\n"
        p = _palette.parse_tables(head + "| Muted | #5a5a72 | #a6abce (proposed) | |\n")
        self.assertEqual(p.proposed, {("dark", "muted")})
        p = _palette.parse_tables(head + "| Muted | #5a5a72 | #a6abce | proposed |\n")
        self.assertEqual(p.proposed, {("light", "muted"), ("dark", "muted")})
        p = _palette.parse_tables(head + "| Muted (proposed) | #5a5a72 | #a6abce | |\n")
        self.assertEqual(p.proposed, {("light", "muted"), ("dark", "muted")})


class Sections(unittest.TestCase):
    """Which theme a table is filed under: the heading over it, or a line that is nothing but a label."""

    def test_a_sentence_that_mentions_the_other_theme_does_not_file_the_table_under_it(self):
        # "(pairs with the dark theme below)" swapped the themes without a word
        for prose in ("(pairs with the dark theme below)", "Pairs with the dark theme below.", "*(see also: dark)*", "Paired with: dark",
                      "Dark theme:", "**Dark theme**", "Not for dark mode"):
            with self.subTest(prose=prose):
                p = _palette.parse_tables("### Light theme\n%s\n" % prose + table(rows(STARTER_LIGHT)))
                self.assertEqual((p.light, p.dark), (STARTER_LIGHT, {}), "a heading named the theme; no line under it files its table elsewhere")
                self.assertEqual(p.problems, [])

    def test_a_theme_is_named_by_whole_words_only(self):
        for heading in ("## Highlights", "## Lightweight palette", "### Darkroom", "## Delightful colours", "## Rebranding"):
            with self.subTest(heading=heading):
                p = _palette.parse_tables(heading + "\n" + table(rows(STARTER_LIGHT)))
                self.assertEqual((p.light, p.dark, p.brand), ({}, {}, None))
                self.assertEqual({c for _t, _k, c in codes(p)}, {"palette-no-theme"}, "said, not filed under a theme the heading never named")
        for heading, theme in (("## Light", "light"), ("### Dark-mode colours", "dark"), ("## Palette: light theme", "light"), ("#### DARK", "dark")):
            with self.subTest(heading=heading):
                p = _palette.parse_tables(heading + "\n" + table([("Muted", "#5a5a72")]))
                self.assertEqual(p.theme(theme), {"muted": "#5a5a72"})
        # a header row too: "Highlights" beside "Dark" is not a light and a dark column
        for first, second in (("Highlights", "Dark"), ("Light", "Darkest"), ("Lightweight", "Darkroom")):
            with self.subTest(first=first, second=second):
                p = _palette.parse_tables("| Token | %s | %s |\n|---|---|---|\n| Muted | #5a5a72 | #a6abce |\n" % (first, second))
                self.assertEqual((p.light, p.dark), ({}, {}))
                self.assertEqual(codes(p), [("?", "muted", "palette-two-values")], "two colours and no way to tell which is which")

    def test_a_line_that_is_nothing_but_a_label_names_the_theme_of_the_table_under_it(self):
        for light, dark in (("Light theme", "Dark theme"), ("Light:", "Dark:"), ("**Light mode**", "**Dark mode**"), ("_Palette A, light_", "_Palette A, dark_"),
                            ("Light theme (default)", "Dark theme (optional):"), ("LIGHT", "DARK"), ("Colours - light", "Colours - dark")):
            with self.subTest(light=light):
                p = _palette.parse_tables(light + "\n" + table(rows(STARTER_LIGHT)) + "\n" + dark + "\n" + table(rows(STARTER_DARK)))
                self.assertEqual((p.light, p.dark, p.problems), (STARTER_LIGHT, STARTER_DARK, []))

    def test_a_label_after_a_headings_own_table_names_the_next_table(self):
        md = "### Light theme\n" + table(rows(STARTER_LIGHT)) + "\n**Dark theme**\n" + table(rows(STARTER_DARK))
        p = _palette.parse_tables(md)
        self.assertEqual((p.light, p.dark, p.problems), (STARTER_LIGHT, STARTER_DARK, []))

    def test_a_sentence_between_two_labelled_tables_changes_nothing(self):
        md = ("Light theme:\n" + table(rows(STARTER_LIGHT)) + "\nThe next one is tuned for OLED screens, where pure black is dark enough to smear.\n\n"
              "Dark theme:\n" + table(rows(STARTER_DARK)) + "\nBoth pass AA; the light one is the default.\n")
        p = _palette.parse_tables(md)
        self.assertEqual((p.light, p.dark, p.problems), (STARTER_LIGHT, STARTER_DARK, []))


class OtherTables(unittest.TestCase):
    """A BRAND.md holds more than colours. A row of another table whose label happens to be one of the
    palette's ("Heading", "Body") is not a colour that could not be read."""

    TYPE = "| Style | Weight | Tracking |\n|---|---|---|\n| Heading | 700 | -0.02em |\n| Body | 400 | 0 |\n| Link | Inter | underline |\n"

    def test_a_table_with_no_colour_in_it_is_not_a_table_of_colours(self):
        for name, before in (("under its own heading", "\n## Typography\n"), ("under a bold line", "\n**Type scale**\n"),
                             ("right under the dark theme's table, after a line of text", "\nThe type scale:\n"),
                             ("right under the dark theme's table, after a blank line and nothing else", "\n"),
                             ("under a heading with a word that only looks like a theme", "\n## Highlights and weights\n")):
            with self.subTest(name=name):
                p = _palette.parse_tables(brand_md() + before + self.TYPE)
                self.assertEqual(p.problems, [], "a complete palette is not made partial by the type table")
                self.assertEqual(p.missing(), [])
                self.assertEqual((p.light, p.dark), (STARTER_LIGHT, STARTER_DARK))
                for label in ("Heading", "Body", "Link"):
                    self.assertIn(label, p.ignored)

    def test_a_row_of_another_table_that_does_hold_a_colour_is_still_spoken_of(self):
        p = _palette.parse_tables(brand_md() + "\n## Typography\n| Style | Weight | Colour |\n|---|---|---|\n| Heading | 700 | #16162a |\n| Body | 400 | n/a |\n")
        self.assertEqual(sorted(codes(p)), [("?", "heading", "palette-no-theme"), ("?", "ink", "palette-no-theme")],
                         "a colour was found in the table, so its rows are rows of colours")

    def test_a_value_that_is_no_colour_in_a_table_of_colours_is_still_named(self):
        # the same words that are nothing in a type table are a mistake here
        p = _palette.parse_tables(brand_md(light=dict(STARTER_LIGHT, accent="700", muted="Inter")))
        self.assertEqual(sorted(codes(p)), [("light", "accent", "colour-unreadable"), ("light", "muted", "colour-unreadable")])
        self.assertIn(("light", "accent"), p.missing())

    def test_the_one_row_of_the_table_a_heading_announces_is_named_even_with_no_colour_beside_it(self):
        p = _palette.parse_tables(brand_md(primary="notacolour"))
        self.assertEqual(codes(p), [("brand", "brand", "colour-unreadable")])
        p = _palette.parse_tables("### Light theme\n" + table([("Accent", "bleu")]))
        self.assertEqual(codes(p), [("light", "accent", "colour-unreadable")])
        p = _palette.parse_tables("Dark theme:\n" + table([("Accent", "bleu")]))
        self.assertEqual(codes(p), [("dark", "accent", "colour-unreadable")])


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

    def test_a_failing_accent_taken_from_the_old_layouts_fixed_row_says_where_it_came_from(self):
        # BRAND.md in the old layout, filled with the starter's own colours: one Accent in the Brand table,
        # which then stands in the dark theme too, where no page shows it and where it fails
        old_light = {k: v for k, v in STARTER_LIGHT.items() if k != "accent"}
        old_dark = {k: v for k, v in STARTER_DARK.items() if k != "accent"}
        md = ("### Brand (fixed, theme-independent)\n| Token | Hex | Use |\n|---|---|---|\n| Primary | `#000000` | x |\n| Accent | `#2b50e0` | links |\n\n"
              "### Light theme\n" + table([(l, old_light[k]) for k, l in LABELS if k in old_light])
              + "\n### Dark theme\n" + table([(l, old_dark[k]) for k, l in LABELS if k in old_dark]))
        p = _palette.parse_tables(md)
        self.assertEqual(p.fixed_accent, {"light", "dark"})
        bad = [x for x in _palette.matrix(p) if not x.ok]
        self.assertEqual({(x.theme, x.fg) for x in bad}, {("dark", "accent")})
        for x in bad:
            line = _palette.describe(x)
            self.assertIn("taken from the Brand table's Accent", line)
            self.assertIn("give the dark theme its own", line)
        ok = [x for x in _palette.matrix(p) if x.ok and x.fg != "accent"]
        self.assertTrue(ok and all(x.note == "" for x in ok), "only the accent came from there")
        # a theme with an accent of its own is not spoken of
        p = _palette.parse_tables(md + "| Accent | `#5c5f80` |\n")
        self.assertEqual(p.fixed_accent, {"light"})
        bad = [x for x in _palette.matrix(p) if not x.ok]
        self.assertTrue(bad)
        self.assertFalse([x for x in bad if "Brand table" in _palette.describe(x)])
        self.assertEqual(_palette.parse_tables(brand_md()).fixed_accent, set())

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

    def starter(self):
        return T.starter_file("src/styles/global.css")

    def assert_all_three_blocks(self, text):
        css = _palette.read_css(text)
        self.assertEqual(css.found, {"light", "dark", "dark_media"})
        self.assertEqual((css.light, css.dark, css.dark_media, css.brand), (STARTER_LIGHT, STARTER_DARK, STARTER_DARK, "#000000"))
        self.assertEqual(css.problems, [])

    def test_a_statement_before_the_root_block_does_not_hide_it(self):
        # @import url("./fonts.css"); made the selector "@import ...; :root", and the light theme was not read
        for before in ('@import url("./fonts.css");\n', '@charset "utf-8";\n', '@charset "utf-8";\n@import "a.css";\n@import url(b.css) screen;\n',
                       '@import url("a;b.css");', '@namespace svg url(http://www.w3.org/2000/svg);\n\n\n'):
            with self.subTest(before=before):
                self.assert_all_three_blocks(before + self.starter())
        # and one between the blocks hides neither of the dark ones
        text = self.starter().replace(':root[data-theme="dark"]', '@import "late.css";\n:root[data-theme="dark"]', 1)
        self.assert_all_three_blocks(text.replace("@media (prefers-color-scheme: dark)", '@import "later.css"; @media (prefers-color-scheme: dark)', 1))

    def test_root_among_other_selectors_or_in_capitals_is_still_the_root_block(self):
        for old, new in ((":root {", ":root, html {"), (":root {", "html, :root {"), (":root {", ":ROOT {"), (":root {", ":Root,body{"),
                         (':root[data-theme="dark"] {', ':root[data-theme="dark"], .dark {'), (':root[data-theme="dark"] {', ":ROOT[DATA-THEME='dark'] {"),
                         ("@media (prefers-color-scheme: dark) {", "@MEDIA (PREFERS-COLOR-SCHEME: DARK) {"),
                         (":root:not([data-theme]) {", ":root:not([data-theme]), html.auto {"), (":root:not([data-theme]) {", ":ROOT:NOT([data-theme]) {")):
            with self.subTest(new=new):
                self.assertIn(old, self.starter())
                self.assert_all_three_blocks(self.starter().replace(old, new, 1))
        # the value of the attribute is not a word of CSS: "DARK" is another theme
        css = _palette.read_css(self.starter().replace(':root[data-theme="dark"] {', ':root[data-theme="DARK"] {', 1))
        self.assertEqual(css.found, {"light", "dark_media"})

    def test_a_brace_inside_a_string_is_not_a_brace(self):
        for rule in ('a::before { content: "{"; }\n', "a::after { content: '}'; }\n", 'q::before { content: "\\"{"; }\n', 'a[title="{"] { color: red; }\n',
                     '@import "we}ird{.css";\n'):
            with self.subTest(rule=rule):
                self.assert_all_three_blocks(rule + self.starter())
                self.assert_all_three_blocks(self.starter().replace(":root[data-theme", rule + ":root[data-theme", 1))
        css = _palette.read_css(':root { --font: "a{b"; --bg: #ffffff; }')
        self.assertEqual(css.light, {"bg": "#ffffff"}, "and the block that holds the string is read to its end")

    def test_braces_that_do_not_pair_up_are_refused_not_read_as_far_as_they_go(self):
        # a } too many ended the :root block early and hid the dark block; nothing said so
        broken = (("a } too many inside the root block", self.starter().replace("--radius: 12px;", "--radius: 12px; }", 1)),
                  ("a } too many at the end", self.starter() + "\n}\n"),
                  ("a { never closed", self.starter()[:self.starter().index("--bg-soft: #11132c;")]),
                  ("a { too many", self.starter().replace(":root {", ":root { {", 1)),
                  ("only a }", "}"), ("only a {", ":root {"))
        for name, text in broken:
            with self.subTest(name=name):
                with self.assertRaises(Refusal) as cm:
                    _palette.read_css(text)
                self.assertEqual(cm.exception.code, "css-unreadable")
                self.assertIn("braces", str(cm.exception))

    def test_each_block_it_does_not_find_is_named(self):
        whole = self.starter()
        dark_at = whole.index(':root[data-theme="dark"]')
        media_at = whole.index("@media (prefers-color-scheme: dark)")
        rest_at = whole.index("*, *::before")
        cases = (("no dark block", whole[:dark_at] + whole[media_at:], {"dark"}), ("no media block", whole[:media_at] + whole[rest_at:], {"dark_media"}),
                 ("no root block", whole[dark_at:], {"light"}), ("none of them", "body { color: red; }", {"light", "dark", "dark_media"}), ("empty", "", {"light", "dark", "dark_media"}),
                 ("a media block with no root rule inside", whole.replace(":root:not([data-theme])", ".other", 1), {"dark_media"}),
                 ("a dark block spelt another way", whole.replace(':root[data-theme="dark"]', "html.dark", 1), {"dark"}))
        for name, text, lacking in cases:
            with self.subTest(name=name):
                css = _palette.read_css(text)
                self.assertEqual({block for block, _v, _m in css.problems}, lacking)
                self.assertEqual(css.found, {"light", "dark", "dark_media"} - lacking)
                for block, variable, message in css.problems:
                    self.assertIsNone(variable)
                    self.assertIn("has no", message)
                    self.assertIn({"light": ":root {", "dark": 'data-theme="dark"', "dark_media": "prefers-color-scheme"}[block], message)
        self.assertEqual(_palette.read_css(whole).problems, [])

    def test_a_block_written_twice_is_one_block_and_its_later_lines_win(self):
        # a browser reads both; the second used to replace the first, so var(--accent) was looked up in half a block
        css = _palette.read_css(":root { --accent: #111111; --link: var(--accent); }\n:root { --accent: #222222; }")
        self.assertEqual(css.light, {"accent": "#222222", "link": "#222222"}, "the link is the accent the page ends up with")
        css = _palette.read_css(":root { --link: var(--accent); }\nbody { margin: 0 }\n:root { --accent: #222222; }")
        self.assertEqual((css.light, [p for p in css.problems if p[1]]), ({"accent": "#222222", "link": "#222222"}, []))
        css = _palette.read_css(":root { --bg: #ffffff; --ink: #111111; }\n:root { --bg: #fafafa; }\n:root { --muted: #555555; }")
        self.assertEqual(css.light, {"bg": "#fafafa", "ink": "#111111", "muted": "#555555"})
        # the dark blocks too, and a dark value that points at a root variable set in a later root block
        text = (':root { --accent: #111111; }\n:root[data-theme="dark"] { --link: var(--accent); --bg: #000000; }\n:root { --accent: #222222; }\n'
                ':root[data-theme="dark"] { --bg: #0a0b1e; }\n@media (prefers-color-scheme: dark) { :root:not([data-theme]) { --bg: #000000; } }\n'
                "@media (prefers-color-scheme: dark) { :root:not([data-theme]) { --bg: #0a0b1e; --link: var(--accent); } }")
        css = _palette.read_css(text)
        self.assertEqual(css.dark, {"link": "#222222", "bg": "#0a0b1e"})
        self.assertEqual(css.dark_media, css.dark)
        self.assertEqual(_palette.dark_blocks_disagree(css), [])

    def test_a_variable_one_dark_block_has_and_the_other_lacks_is_a_disagreement(self):
        # scenario 29: --surface taken out of the @media block only; both blocks agreed on all they shared
        whole = self.starter()
        media_at = whole.index("@media (prefers-color-scheme: dark)")
        only_media = whole[:media_at] + whole[media_at:].replace("    --surface: #161836;\n", "", 1)
        css = _palette.read_css(only_media)
        self.assertIn("surface", css.dark)
        self.assertNotIn("surface", css.dark_media)
        self.assertEqual(_palette.dark_blocks_disagree(css), [("surface", "#161836", _palette.MISSING)])
        only_dark = whole[:media_at].replace("  --surface: #161836;\n", "", 1) + whole[media_at:]
        self.assertEqual(_palette.dark_blocks_disagree(_palette.read_css(only_dark)), [("surface", _palette.MISSING, "#161836")])
        both = only_dark[:only_dark.index("@media (prefers-color-scheme: dark)")] + only_media[media_at:].replace("--bg: #0a0b1e;", "--bg: #000000;", 1)
        self.assertEqual(_palette.dark_blocks_disagree(_palette.read_css(both)), [("bg", "#0a0b1e", "#000000")],
                         "a variable neither block has is not a disagreement between them")
        self.assertEqual(_palette.dark_blocks_disagree(_palette.read_css(whole)), [])
        # a block that is not there at all is said once, by read_css, not once for each of its variables
        gone = _palette.read_css(whole[:media_at] + whole[whole.index("*, *::before"):])
        self.assertEqual(_palette.dark_blocks_disagree(gone), [])
        self.assertEqual([block for block, _v, _m in gone.problems], ["dark_media"])

    def test_a_row_the_document_has_and_the_stylesheet_lacks_is_drift(self):
        p = _palette.parse_tables(brand_md())
        whole = self.starter()
        css = _palette.read_css(whole.replace("  --surface: #ffffff;\n", "", 1))
        self.assertEqual(_palette.drift(p, css), [("light", "surface", "#ffffff", _palette.MISSING)])
        css = _palette.read_css(whole.replace("  --muted: #a6abce;\n", "", 1).replace("  --brand: #000000;\n", "", 1))
        self.assertEqual(_palette.drift(p, css), [("dark", "muted", "#a6abce", _palette.MISSING), ("brand", "brand", "#000000", _palette.MISSING)])
        # a row the document has not filled in is listed as missing by the palette check, not as drift
        self.assertEqual(_palette.drift(_palette.parse_tables(brand_md(dark={})), _palette.read_css(whole)), [])
        # and a block that is not there at all is said once, not row by row
        css = _palette.read_css(whole[:whole.index(':root[data-theme="dark"]')] + whole[whole.index("@media (prefers-color-scheme: dark)"):])
        self.assertEqual(_palette.drift(p, css), [])
        self.assertEqual([block for block, _v, _m in css.problems], ["dark"])

    def test_a_stylesheet_value_that_could_not_be_read_is_said_as_that_and_not_as_no_value(self):
        p = _palette.parse_tables(brand_md())
        whole = self.starter()
        css = _palette.read_css(whole.replace("--muted: #5a5a72;", "--muted: rgba(90, 90, 114, 0.8);", 1).replace("--brand: #000000;", "--brand: url(#g);", 1))
        self.assertEqual(sorted((block, variable) for block, variable, _m in css.problems), [("light", "--brand"), ("light", "--muted")])
        self.assertEqual(_palette.drift(p, css), [], "it is there; what it is could not be read, and css.problems says so")
        at = whole.index("@media (prefers-color-scheme: dark)")
        css = _palette.read_css(whole[:at] + whole[at:].replace("--surface: #161836;", "--surface: transparent;", 1))
        self.assertEqual([(block, variable) for block, variable, _m in css.problems], [("dark_media", "--surface")])
        self.assertEqual(_palette.dark_blocks_disagree(css), [])


if __name__ == "__main__":
    unittest.main()
