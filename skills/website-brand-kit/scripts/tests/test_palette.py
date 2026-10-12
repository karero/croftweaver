"""Scenarios 7, 9, 10 (the palette side), 28: the palette the owner pastes, the rows it must
have, and the contrast check that names a failing pair before anything is written.

`_palette.parse_tables` reads ONE form, the three tables this skill itself writes, by the numbered
rules of its docstring. Each rule has its own class below, named for the rule, and each class tests
both sides of it: what the rule reads, and the near-misses it must not read (and what is said about
them). The rule above all of them: never silent, never guessed. A value the reader returns is the
value written in the value cell of a row with a known name under one of the three headings;
everything else that holds a colour is named in `problems` or `unused`.

The matrix is every text colour on every background colour, in both themes. That is wider than
the starter's stylesheet uses today (it styles `--ink` and `--link` on `--bg`, and `--ink` on
`--surface`), on purpose: a stylesheet that starts using `--muted` on `--bg-soft` should not be
the first time anyone checks the pair. A test below holds the matrix to the stylesheet it
protects, so a new pair in the CSS that the matrix lacks fails here.
"""

import os
import re
import time
import unittest

import _testutil as T
import _colour
import _palette
import _site
from _refusal import Refusal

STARTER_LIGHT = {"heading": "#16162a", "ink": "#16162a", "muted": "#5a5a72", "accent": "#2b50e0", "link": "#2b50e0",
                 "line": "#e3e7f2", "bg": "#ffffff", "bg_soft": "#f5f7fb", "surface": "#ffffff"}
STARTER_DARK = {"heading": "#e7e9fb", "ink": "#dce0f5", "muted": "#a6abce", "accent": "#8aa0ff", "link": "#9fb0ff",
                "line": "#272c4d", "bg": "#0a0b1e", "bg_soft": "#11132c", "surface": "#161836"}
LABELS = [("heading", "Heading"), ("ink", "Body (ink)"), ("muted", "Muted"), ("accent", "Accent"), ("link", "Link"),
          ("line", "Hairline"), ("bg", "Background"), ("bg_soft", "Soft background"), ("surface", "Surface (cards)")]
HEAD = "| Token | Hex |\n|---|---|\n"
EVALS = os.path.join(T.REPO, "skills", "website-brand-kit", "evals", "files")


def table(rows):
    return HEAD + "\n".join("| %s | `%s` |" % (label, value) for label, value in rows) + "\n"


def rows(theme, **changed):
    """The nine rows of a theme as (label, value), with some values changed."""
    return [(l, changed.get(k, theme[k])) for k, l in LABELS]


def lines(theme, **changed):
    return ["| %s | %s |" % row for row in rows(theme, **changed)]


def plain(theme, **changed):
    """A theme's table with its header row, the values written without backticks."""
    return HEAD + "\n".join(lines(theme, **changed)) + "\n"


def codes(palette):
    return [(t, k, c) for t, k, c, _m in palette.problems]


def said(palette):
    return " ".join(m for _t, _k, _c, m in palette.problems)


def brand_md(light=STARTER_LIGHT, dark=STARTER_DARK, primary="#000000", extra=""):
    return (
        "# Example Bakery: brand & style guide\n\n## Colour palette\n\n### Brand (fixed, theme-independent)\n"
        "| Token | Hex | Use |\n|---|---|---|\n| Primary | `%s` | buttons, brand surfaces |\n\n" % primary
        + "### Light theme\n" + table([(l, light[k]) for k, l in LABELS if k in light]) + "\n"
        + "### Dark theme\n" + table([(l, dark[k]) for k, l in LABELS if k in dark]) + extra
    )


def one(value, label="Muted", heading="### Light theme", head=HEAD):
    """A document with one row under one heading."""
    return "%s\n%s| %s | %s |\n" % (heading, head, label, value)


class TheFormThisSkillWrites(unittest.TestCase):
    """What the reader is for: the three tables as the template, the prompt and the fixtures have them."""

    def test_the_three_tables_are_read_into_both_themes_and_the_primary(self):
        p = _palette.parse_tables(brand_md())
        self.assertEqual(p.light, STARTER_LIGHT)
        self.assertEqual(p.dark, STARTER_DARK)
        self.assertEqual(p.brand, "#000000")
        self.assertEqual((p.missing(), p.problems, p.unused, p.ignored, p.proposed), ([], [], [], [], set()))
        self.assertEqual(p.rows_found, 19)

    def test_the_template_as_shipped_is_all_missing_not_an_error(self):
        p = _palette.parse_tables(T.read(T.BRAND_TEMPLATE))
        self.assertEqual(len(p.missing()), 18)
        self.assertIsNone(p.brand)
        self.assertEqual((p.problems, p.unused), ([], []))
        self.assertEqual(p.rows_found, 19, "its rows are found; they are not filled in yet")

    def test_the_template_filled_in_is_the_palette_and_matches_the_starters_stylesheet(self):
        template = T.read(T.BRAND_TEMPLATE)
        self.assertEqual(template.count("`#[…]`"), 19)
        values = ["#000000"] + [STARTER_LIGHT[k] for k, _l in LABELS] + [STARTER_DARK[k] for k, _l in LABELS]
        for value in values:
            template = template.replace("`#[…]`", "`%s`" % value, 1)
        p = _palette.parse_tables(template)
        self.assertEqual((p.light, p.dark, p.brand, p.problems, p.unused), (STARTER_LIGHT, STARTER_DARK, "#000000", [], []))
        pairs = _palette.matrix(p)
        self.assertEqual((len(pairs), [x for x in pairs if not x.ok]), (30, []))
        self.assertEqual(_palette.drift(p, _palette.read_css(T.starter_file("src/styles/global.css"))), [])

    def test_the_two_fixtures_the_evals_hand_over(self):
        p = _palette.parse_tables(T.read(os.path.join(EVALS, "pasted-palette.md")))
        self.assertEqual((p.missing(), p.problems, p.unused, p.brand), ([], [], [], "#b4531a"))
        bad = [x for x in _palette.matrix(p) if not x.ok]
        self.assertEqual([(x.theme, x.fg, x.bg, _colour.shown(x.ratio)) for x in bad],
                         [("dark", "muted", "bg", "3.58"), ("dark", "muted", "bg_soft", "3.34"), ("dark", "muted", "surface", "3.11")])
        p = _palette.parse_tables(T.read(os.path.join(EVALS, "own-colours.md")))
        self.assertEqual(p.missing(), [("light", "link"), ("light", "bg_soft")] + [("dark", k) for k in _palette.KEYS])
        self.assertEqual((p.problems, p.unused, p.brand), ([], [], "#b4531a"))


class Rule1Lines(unittest.TestCase):
    """1. Runs of spaces and tabs are made one space before anything is looked at; a table row longer
    than 2,000 characters is not read, and a problem names it."""

    def timed(self, md):
        # the time this process spent, not the clock on the wall: a busy machine must not fail this, a slow pattern must
        start = time.process_time()
        try:
            p = _palette.parse_tables(md)
        except Refusal:
            p = None
        took = time.process_time() - start
        self.assertLess(took, 1.0, "reading took %.2f s of processor time" % took)
        return p

    def test_a_long_run_of_spaces_or_tabs_anywhere_in_a_row_is_one_space(self):
        gap = " " * 40000
        md = "###%sLight   theme\n%s|%sMuted%s|%s`#5a5a72`\t\t(proposed)%s|%sa   note%s|\n" % (gap, HEAD, gap, gap, gap, gap, gap, gap)
        p = self.timed(md)
        self.assertEqual((p.light, p.proposed, p.problems), ({"muted": "#5a5a72"}, {("light", "muted")}, []))

    def test_no_input_makes_the_reading_slow(self):
        # round 2 measured 11 seconds for one cell of 40,000 spaces
        big = 40000
        for name, md in (("spaces in a cell", one("#5a5a72" + " " * big + "x")),
                         ("spaces before the mark", one("#5a5a72" + " " * big + "proposed")),
                         ("spaces in a heading", "### Light theme" + " " * big + "(" + " " * big + "\n" + plain(STARTER_LIGHT)),
                         ("brackets in a cell", one("(" * big)), ("a function that never closes", one("rgb(" + "1," * big)),
                         ("hashes", one("#" * big)), ("one megabyte of pipes", "### Light theme\n" + "|" * (1024 * 1024)),
                         ("ten thousand rows", "### Light theme\n" + "| Muted | #5a5a72 | a note |\n" * 10000),
                         ("ten thousand tables", "### Light theme\n" + (HEAD + "| Muted | #5a5a72 |\n\n") * 10000),
                         ("a megabyte of words under a heading", "### Light theme\n" + "proposed " * 110000 + "\n"),
                         ("ten thousand headings that hold the word", "## Proposed\n" * 10000 + "### Light theme\n" + HEAD + "| Muted | #5a5a72 |\n")):
            with self.subTest(name=name):
                self.timed(md)

    def test_a_row_longer_than_the_limit_is_named_and_not_read(self):
        long_row = "| Muted | #5a5a7280 | %s |" % ("x" * 2100)
        p = _palette.parse_tables("### Light theme\n" + HEAD + "| Heading | #16162a |\n" + long_row + "\n| Link | #2b50e0 |\n")
        self.assertEqual(p.light, {"heading": "#16162a", "link": "#2b50e0"}, "cut at the limit it would have read #5a5a72, which nobody wrote")
        self.assertEqual(codes(p), [("?", None, "palette-long-line")])
        for part in ("Line 5", "| Muted | #5a5a7280", "2000", "not read"):
            self.assertIn(part, p.problems[0][3])
        self.assertIn(("light", "muted"), p.missing())

    def test_a_row_of_exactly_the_limit_is_read_and_long_lines_that_are_no_rows_are_no_problem(self):
        row = "| Muted | #5a5a72 | "
        row += "x" * (_palette.MAX_LINE - len(row) - 2) + " |"
        self.assertEqual(len(row), _palette.MAX_LINE)
        p = _palette.parse_tables("A sentence. " * 400 + "\n### Light theme\n" + HEAD + row + "\n")
        self.assertEqual((p.light, p.problems), ({"muted": "#5a5a72"}, []))
        # spaces do not count towards the length: they are made one first
        p = _palette.parse_tables("### Light theme\n" + HEAD + "| Muted |" + " " * 5000 + "#5a5a72 |\n")
        self.assertEqual((p.light, p.problems), ({"muted": "#5a5a72"}, []))


class Rule2Sections(unittest.TestCase):
    """2. Only a heading line names a section, and only when its text is exactly Brand, Light theme or
    Dark theme, optionally followed by one bracketed remark. Every other heading ends the section. No
    other line names one."""

    def test_the_three_headings_in_every_spelling_the_rule_allows(self):
        for heading, theme in (("### Light theme", "light"), ("# Light theme", "light"), ("###### Dark theme", "dark"), ("### **Light theme**", "light"),
                               ("### `Dark theme`", "dark"), ("### LIGHT THEME", "light"), ("###   Dark    theme  ", "dark"), ("### Light theme ###", "light"),
                               ("### _Light theme_ (the default)", "light"), ("### Dark theme (fixed, optional; see below)", "dark"), ("  ### Light theme", "light")):
            with self.subTest(heading=heading):
                p = _palette.parse_tables(heading + "\n" + HEAD + "| Muted | #5a5a72 |\n")
                self.assertEqual((p.theme(theme), p.problems), ({"muted": "#5a5a72"}, []))
        for heading in ("### Brand", "## Brand (fixed, theme-independent)", "### BRAND", "### **Brand**"):
            with self.subTest(heading=heading):
                p = _palette.parse_tables(heading + "\n" + HEAD + "| Primary | #123456 |\n")
                self.assertEqual((p.brand, p.problems), ("#123456", []))

    def test_a_heading_that_is_not_exactly_one_of_the_three_names_no_section(self):
        for heading in ("### Light", "### Light mode", "### Light theme colours", "### Light theme:", "## Palette: light theme", "### Light theme typography",
                        "### Dark theme proposals", "### Proposal: dark theme", "### Light theme (a) (b)", "### Light and dark themes", "## Highlights",
                        "### Lightweight theme", "### Brand colours", "## Rebranding", "### Dark-mode colours", "### Theme: Dark (default off)",
                        "### Light theme, proposed", "### The light theme", "#### DARK", "### Light theme (unclosed", "### Helles Design"):
            with self.subTest(heading=heading):
                p = _palette.parse_tables(heading + "\n" + plain(STARTER_LIGHT))
                self.assertEqual((p.light, p.dark, p.brand), ({}, {}, None), "not filed under a section the heading never named")
                self.assertEqual(codes(p), [("?", None, "palette-no-section")])
                for part in ("under the heading", heading.strip()[:40], "Heading", "Surface (cards)", "`### Light theme`", "`### Dark theme`", "were not used"):
                    self.assertIn(part, p.problems[0][3])

    def test_a_line_that_is_no_heading_names_no_section_whatever_it_says(self):
        # labels, bold lines, underlined headings, HTML: none of them is read as a heading, and none is guessed at
        for label in ("Light theme", "Light theme:", "**Light theme**", "_Light theme_", "LIGHT THEME", "<h3>Light theme</h3>", "- Light theme",
                      "> ### Light theme", "1. Light theme", "Light theme\n-----------", "Light theme\n===========", "Palette 2, light theme:"):
            with self.subTest(label=label):
                p = _palette.parse_tables(label + "\n" + plain(STARTER_LIGHT))
                self.assertEqual((p.light, p.dark), ({}, {}))
                self.assertEqual(codes(p), [("?", None, "palette-no-section")])
                self.assertIn("under the line", p.problems[0][3])
                self.assertIn("which is not a heading (a heading starts with #)", p.problems[0][3])
                self.assertIn(label.splitlines()[-1], p.problems[0][3])

    def test_no_line_of_text_under_a_heading_files_its_table_elsewhere(self):
        # round 2: "Not for dark mode" filed the table under dark; "These colours belong to our brand" under Brand
        for prose in ("(pairs with the dark theme below)", "Pairs with the dark theme below.", "*(see also: dark)*", "Paired with: dark", "Dark theme:",
                      "**Dark theme**", "Not for dark mode", "These colours belong to our brand", "Note: the dark theme", "Brand", "Dark theme",
                      "Same roles as dark\n\nDark"):
            with self.subTest(prose=prose):
                p = _palette.parse_tables("### Light theme\n%s\n" % prose + plain(STARTER_LIGHT))
                self.assertEqual((p.light, p.dark, p.brand), (STARTER_LIGHT, {}, None))
                self.assertEqual(p.problems, [])

    def test_every_other_heading_ends_the_section(self):
        for heading in ("## Notes", "### Typography", "#", "####### seven", "#notes", "### Light theme typography"):
            with self.subTest(heading=heading):
                p = _palette.parse_tables("### Light theme\n" + HEAD + "| Heading | #16162a |\n" + heading + "\n" + HEAD + "| Muted | #5a5a72 |\n")
                self.assertEqual(p.light, {"heading": "#16162a"})
                self.assertEqual(codes(p), [("?", None, "palette-no-section")])
                self.assertIn("Muted", p.problems[0][3])
        # and the next of the three headings starts its own
        p = _palette.parse_tables("### Light theme\n" + plain(STARTER_LIGHT) + "### Dark theme\n" + plain(STARTER_DARK))
        self.assertEqual((p.light, p.dark, p.problems), (STARTER_LIGHT, STARTER_DARK, []))


class Rule3Tables(unittest.TestCase):
    """3. A table is a run of lines that start with |. The first table under a section's heading belongs
    to it, and so does each table that follows with only blank lines between; a table after a line of
    text further down belongs to no section."""

    def test_a_blank_line_ends_a_table_and_the_next_one_still_belongs_to_the_section(self):
        body = lines(STARTER_LIGHT)
        for cut in (1, 4, 8):
            with self.subTest(cut=cut):
                md = "### Light theme\n" + HEAD + "\n".join(body[:cut]) + "\n\n\n" + "\n".join(body[cut:]) + "\n"
                p = _palette.parse_tables(md)
                self.assertEqual((p.light, p.problems), (STARTER_LIGHT, []))

    def test_a_row_after_a_blank_line_is_read_like_any_other_and_what_is_wrong_with_it_is_said(self):
        # round 2: a complete palette, a blank line, then this row: exit 0, and not a word about it
        p = _palette.parse_tables(brand_md(dark={k: v for k, v in STARTER_DARK.items() if k != "accent"}) + "\n| Accent | rgba(0,0,0,0.5) |\n")
        self.assertEqual(codes(p), [("dark", "accent", "colour-alpha")])
        self.assertIn(("dark", "accent"), p.missing())
        with self.assertRaises(Refusal) as cm:
            _palette.parse_tables(brand_md() + "\n| Accent | #123456 |\n")
        self.assertEqual(cm.exception.code, "palette-ambiguous", "a readable one is a second value for the row")
        p = _palette.parse_tables(brand_md() + "\n| Accent | rgba(0,0,0,0.5) |\n")
        self.assertEqual(codes(p), [("dark", "accent", "colour-alpha")], "and an unreadable one is named, beside the value the row has")
        self.assertEqual(p.dark, STARTER_DARK)

    def test_a_table_after_a_line_of_text_further_down_is_not_filed_under_the_heading_above(self):
        # the line may be a label for the other theme. Filed under the heading above, a dark table under "**Dark theme**"
        # was either the light theme's values (silently) or "two palettes pasted together" (the wrong reason).
        for label in ("**Dark theme**", "Dark theme:", "Dark theme", "And for the night:", "<!-- dark -->", "---"):
            with self.subTest(label=label):
                p = _palette.parse_tables("### Light theme\n" + plain(STARTER_LIGHT) + "\n" + label + "\n" + plain(STARTER_DARK))
                self.assertEqual((p.light, p.dark), (STARTER_LIGHT, {}))
                self.assertEqual(codes(p), [("?", None, "palette-no-section")])
                for part in ("after the line", label, "further down under `### Light theme`", "A line of text is not a heading", "does not guess"):
                    self.assertIn(part, p.problems[0][3])
        # a table of two rows that would have clashed with nothing: not taken for the light theme's either
        p = _palette.parse_tables("### Light theme\n" + HEAD + "| Heading | #16162a |\n\n**Dark theme**\n" + HEAD + "| Muted | #a6abce |\n| Link | #9fb0ff |\n")
        self.assertEqual(p.light, {"heading": "#16162a"})
        self.assertIn("Muted and Link", said(p))
        # nor is any later table, blank lines or not
        p = _palette.parse_tables("### Light theme\n" + HEAD + "| Heading | #16162a |\ntext\n" + HEAD + "| Muted | #5a5a72 |\n\n" + HEAD + "| Link | #2b50e0 |\n")
        self.assertEqual(p.light, {"heading": "#16162a"})
        self.assertEqual([c for _t, _k, c in codes(p)], ["palette-no-section", "palette-no-section"])

    def test_text_between_a_heading_and_its_first_table_is_only_text(self):
        p = _palette.parse_tables("### Light theme\nThe daytime look.\n\nWarm, with one accent.\n" + plain(STARTER_LIGHT) + "\nBoth pass AA.\n")
        self.assertEqual((p.light, p.problems), (STARTER_LIGHT, []))

    def test_separator_rows_are_skipped_wherever_they_stand(self):
        for name, md in (("on top", "### Light theme\n|---|---|\n" + "\n".join(lines(STARTER_LIGHT)) + "\n"),
                         ("with colons", "### Light theme\n| Token | Hex |\n|:---|---:|\n" + "\n".join(lines(STARTER_LIGHT)) + "\n"),
                         ("in the middle", "### Light theme\n" + HEAD + "\n".join(lines(STARTER_LIGHT)[:4]) + "\n|---|---|\n" + "\n".join(lines(STARTER_LIGHT)[4:]) + "\n")):
            with self.subTest(name=name):
                p = _palette.parse_tables(md)
                self.assertEqual((p.light, p.problems), (STARTER_LIGHT, []))

    def test_a_row_without_its_first_pipe_is_no_row_and_is_named(self):
        for name, md in (("no outer pipes", "### Light theme\nToken | Hex\n---|---\nHeading | #16162a\nBackground | #ffffff\n"),
                         ("a quoted table", "### Light theme\n> | Token | Hex |\n> |---|---|\n> | Heading | #16162a |\n")):
            with self.subTest(name=name):
                p = _palette.parse_tables(md)
                self.assertEqual((p.light, p.rows_found), ({}, 0))
                self.assertEqual(codes(p), [("?", None, "palette-not-a-row")], "once for the heading, not once a line")
                for part in ("#16162a", "does not start with |", "`### Light theme`"):
                    self.assertIn(part, p.problems[0][3])
        # a sentence with a | and no colour, or a colour and no |, is a sentence
        p = _palette.parse_tables("### Light theme\nEither | or.\nOur ink is #16162a.\n" + plain(STARTER_LIGHT))
        self.assertEqual((p.light, p.problems), (STARTER_LIGHT, []))


class Rule4Rows(unittest.TestCase):
    """4. The first cell is the row's name, exactly one of the template's or of the old template's two
    short forms. The second cell is the value, always. The cells after it are notes."""

    def test_the_names_the_template_uses_and_the_two_short_forms(self):
        for key, label in LABELS + [("ink", "Body"), ("surface", "Surface"), ("ink", "body (INK)"), ("heading", "**Heading**"), ("muted", "`Muted`"),
                                    ("bg", "BACKGROUND"), ("bg_soft", "Soft   background"), ("surface", "_Surface (cards)_")]:
            with self.subTest(label=label):
                p = _palette.parse_tables(one("#123456", label=label))
                self.assertEqual((p.light, p.problems, p.unused), ({key: "#123456"}, [], []))
        for label in ("Primary", "primary", "**Primary**"):
            with self.subTest(label=label):
                self.assertEqual(_palette.parse_tables(one("#123456", label=label, heading="### Brand")).brand, "#123456")

    def test_no_other_name_is_a_row_and_a_colour_under_one_is_kept_to_be_shown(self):
        # a second brand colour is not the muted text, "Text" is not the body, a CSS variable is not its row
        for label in ("Headings", "Heading:", "Heading text", "Text", "Body text", "Ink", "Secondary", "Secondary text", "Muted text", "Border", "Line",
                      "Divider", "--link", "Links", "Link colour", "Accent colour", "Bg", "Page background", "Soft bg", "Surface / cards", "Cards", "Card",
                      "Brand", "Primary colour", "Brand primary", "Muted (proposed)", "Überschrift", "Body (ink) 2", "Soft-background", "Heading 1"):
            with self.subTest(label=label):
                p = _palette.parse_tables(one("#123456", label=label))
                self.assertEqual((p.light, p.dark, p.brand, p.problems, p.proposed), ({}, {}, None, [], set()))
                self.assertEqual(p.unused, [(label, ["#123456"])])

    def test_the_second_cell_is_the_value_and_a_later_cell_is_a_note(self):
        for note in ("buttons, brand surfaces", "6.5:1 on #ffffff", "sits on #fdfdfd", "Gray", "white", "16.9:1 (AAA)", "—", "",
                     "hover is #1a3fb0", "was 5a5a72", "ok | really | fine"):
            with self.subTest(note=note):
                p = _palette.parse_tables("### Light theme\n| Token | Hex | Note |\n|---|---|---|\n| Muted | #5a5a72 | %s |\n" % note)
                self.assertEqual((p.light, p.problems), ({"muted": "#5a5a72"}, []))

    def test_a_value_is_never_taken_from_a_cell_after_the_second(self):
        for cells in ("| #5a5a72 |", "#[…] | #5a5a72 |", "- | `#5a5a72` | note |", "| | rgb(90, 90, 114) |", "| #5a5a7280 |"):
            with self.subTest(cells=cells):
                p = _palette.parse_tables("### Light theme\n| Token | Hex | Other |\n|---|---|---|\n| Muted | %s\n" % cells)
                self.assertEqual(p.light, {})
                self.assertEqual(codes(p), [("light", "muted", "palette-wrong-cell")])
                for part in ("Muted (light theme)", "second cell is empty", "further along", "write it there"):
                    self.assertIn(part, p.problems[0][3])
        # with no colour further along, an empty value cell is a row not filled in yet
        p = _palette.parse_tables("### Light theme\n| Token | Hex | Other |\n|---|---|---|\n| Muted | | white, for now |\n")
        self.assertEqual((p.light, p.problems, p.missing()[2]), ({}, [], ("light", "muted")))

    def test_two_different_colours_in_the_cells_of_one_row_are_named_and_neither_is_picked(self):
        # round 2: "#767676 | #777777" took the first, which passes on white where the second fails
        for value, other in (("#767676", "#777777"), ("#c9bfa6", "rgb(16, 16, 16)"), ("rgb(201, 191, 166)", "#101010"), ("#c9bfa6", "hsl(43, 24%, 71%)"),
                             ("#c9bfa6", "rgb(203, 191, 166)"), ("#9a9aa8", "#9a9aa8cc"), ("#9a9aa8", "rgba(154, 154, 168, 0.8)"), ("#2b50e0", "oklch(0.7 0.4 30)")):
            with self.subTest(value=value, other=other):
                p = _palette.parse_tables("### Light theme\n| Token | Hex | Also |\n|---|---|---|\n| Background | %s | %s |\n| Muted | #5a5a72 | x |\n" % (value, other))
                self.assertEqual(p.light, {"muted": "#5a5a72"})
                self.assertEqual(codes(p), [("light", "bg", "palette-two-colours")])
                for part in ("Background (light theme)", "two different colours", value, other, "does not choose"):
                    self.assertIn(part, p.problems[0][3])
        # the same colour written twice is one colour; so is a description of it in words
        for other in ("rgb(201, 191, 166)", "#C9BFA6", "`#c9bfa6`", "hsl(43, 24%, 72%)", "a warm sand", "Tan", "tan, like #c9bfa6"):
            with self.subTest(other=other):
                p = _palette.parse_tables("### Light theme\n| Token | Hex | Also |\n|---|---|---|\n| Background | #c9bfa6 | %s |\n" % other)
                self.assertEqual((p.light, p.problems), ({"bg": "#c9bfa6"}, []))


class Rule5TheValueCell(unittest.TestCase):
    """5. The value cell holds exactly one colour and nothing else: backticks may stand around it, and
    the mark (proposed) after it."""

    def test_every_colour_format_is_read_as_the_same_hex(self):
        for value, expected in (("#16162a", "#16162a"), ("#16162A", "#16162a"), ("#FFF", "#ffffff"), ("`#1A120DFF`", "#1a120d"), ("rgb(255, 255, 255)", "#ffffff"),
                                ("hsl(240 30% 12%)", _colour.parse_colour("hsl(240 30% 12%)")), ("oklch(0.5 0.04 280)", _colour.parse_colour("oklch(0.5 0.04 280)")),
                                ("WHITE", "#ffffff"), ("`tomato`", "#ff6347"), ("  #16162a  ", "#16162a")):
            with self.subTest(value=value):
                p = _palette.parse_tables(one(value))
                self.assertEqual((p.light, p.problems), ({"muted": expected}, []))

    def test_the_mark_after_the_colour_in_the_spellings_the_rule_allows(self):
        for value in ("`#e2874a (proposed)`", "`#e2874a` (proposed)", "#e2874a (proposed)", "#e2874a (Proposed)", "#e2874a(proposed)", "#e2874a proposed",
                      "`#e2874a` (proposal)", "#e2874a ( proposed )", "`#e2874a` PROPOSED"):
            with self.subTest(value=value):
                p = _palette.parse_tables(one(value))
                self.assertEqual((p.light, p.proposed, p.problems), ({"muted": "#e2874a"}, {("light", "muted")}, []))

    def test_an_empty_cell_or_a_placeholder_is_a_row_not_filled_in_which_is_not_a_mistake(self):
        for value in ("", "`#[…]`", "#[…]", "#[...]", "#...", "#…", "[hex]", "[…]", "#[hex]", "[ ]", "-", "—", "–", "`#[…]` (proposed)", "(proposed)"):
            with self.subTest(value=value):
                p = _palette.parse_tables(brand_md(light={k: v for k, v in STARTER_LIGHT.items() if k != "accent"}) + "\n### Light theme\n" + HEAD + "| Accent | %s |\n" % value)
                self.assertEqual((p.missing(), p.problems, p.proposed), ([("light", "accent")], [], set()))
                self.assertEqual(p.rows_found, 19)

    def test_what_only_looks_like_a_placeholder_and_holds_a_colour_is_named(self):
        for value in ("[#2B50E0]", "[#2b50e0](http://example.com/c)", "[`#2b50e0`](https://example.com/#top)", "[red]", "[2b50e0]", "#[2b50e0]", "[abc]"):
            with self.subTest(value=value):
                p = _palette.parse_tables(one(value))
                self.assertEqual(p.light, {})
                self.assertEqual(len(p.problems), 1)
                self.assertIn(value[:40], p.problems[0][3])

    def test_anything_else_in_the_cell_is_a_problem_that_names_the_row_the_theme_and_what_was_found(self):
        # round 2: of two colours in one cell the first was taken, without a word
        for value in ("#2b50e0 / #9fb0ff", "#2b50e0 or #1a3fb0", "#16162a (was #000000)", "#2B50E0 (buttons and links)", "**#ffffff**", "_#16162a_",
                      "#16162a — near-black navy", "#5a5a72 (AA on white, 6.5:1)", "#2b50e0, underlined", "#FFFFFF / white", "`#2b50e0` **bold**",
                      "#e3e7f2 @ 100%", "#f5f7fb 50% opacity", "5a5a72", "# 2b50e0", "#2b50e0;", "#c81e3", "#2b50eO", "proposed: `#a6abce`", "#ffffff - proposed",
                      "#e3e7f2 [proposed]", "#ffffff ← proposed", "#a6abce*", "#5a5a72 (Vorschlag)", "#5a5a72 (not proposed)", "White #ffffff", "<code>#5a5a72</code>",
                      "rgb(1, 2)", "#fff #000", "``#000000` (proposed)`"):
            with self.subTest(value=value):
                p = _palette.parse_tables(one(value))
                self.assertEqual((p.light, p.proposed), ({}, set()), "no value, and so nothing to mark")
                self.assertEqual(codes(p), [("light", "muted", "palette-not-one-colour")])
                message = p.problems[0][3]
                for part in ("Muted (light theme): the second cell holds", value[:40], "exactly one colour", "A note belongs in a third cell"):
                    self.assertIn(part, message)
                self.assertNotIn("type sizes", message)
                self.assertIn(("light", "muted"), p.missing(), "a row that cannot be read is a row she has not given")

    def test_words_that_hold_nothing_like_a_colour_are_named_too_with_a_word_on_other_tables(self):
        for value in ("a warm blue", "notacolour", "bleu", "700", "Inter", "tbd", "?", "n/a", "proposed", "see below"):
            with self.subTest(value=value):
                p = _palette.parse_tables(one(value))
                self.assertEqual(p.light, {})
                self.assertEqual(codes(p), [("light", "muted", "colour-unreadable")])
                for part in ("Muted (light theme): the second cell holds", '"%s"' % value, "another table (type sizes, say)", "a heading of its own"):
                    self.assertIn(part, p.problems[0][3])

    def test_a_colour_that_is_refused_is_named_for_what_it_is(self):
        for value, code, part in (("rgba(90, 90, 114, 0.8)", "colour-alpha", "see-through"), ("#2b50e080", "colour-alpha", "see-through"),
                                  ("`#0000` (proposed)", "colour-alpha", "see-through"), ("transparent", "colour-alpha", "see-through"),
                                  ("oklch(0.7 0.4 150)", "colour-gamut", "outside the colours a screen can show"),
                                  ("currentColor", "colour-current", "no colour of its own"), ("url(#gradient)", "colour-gradient", "one flat colour")):
            with self.subTest(value=value):
                p = _palette.parse_tables(one(value))
                self.assertEqual(p.light, {})
                self.assertEqual(codes(p), [("light", "muted", code)])
                self.assertIn("Muted (light theme): ", p.problems[0][3])
                self.assertIn(part, p.problems[0][3])
                self.assertNotIn("mark", p.problems[0][3], "the sentence is about a palette, not about a logo")
        p = _palette.parse_tables(brand_md(primary="rgba(0, 0, 0, 0.5)"))
        self.assertEqual(codes(p), [("brand", "brand", "colour-alpha")])
        self.assertTrue(p.problems[0][3].startswith("Primary: "))

    def test_a_colour_name_is_a_value_only_under_a_header_row_that_says_hex(self):
        # | Muted | DimGray | 9a9aa8 | with no header: the name may stand in a column of names, and the check passed on it
        for row in ("| Muted | DimGray |", "| Muted | DimGray | 9a9aa8 |", "| Muted | Gray | the real one is 9a9aa8 |", "| Muted | `white` (proposed) |"):
            with self.subTest(row=row):
                for md in ("### Light theme\n%s\n" % row, "### Light theme\n| Token | Hex |\n%s\n" % row, "### Light theme\n|---|---|\n%s\n" % row):
                    p = _palette.parse_tables(md)
                    self.assertEqual((p.light, p.proposed), ({}, set()))
                    self.assertEqual(codes(p), [("light", "muted", "palette-name-no-header")])
                    for part in ("Muted (light theme)", "the colour name", "no header row", "`| Token | Hex |`", "`|---|---|`"):
                        self.assertIn(part, p.problems[0][3])
        # under the header the owner has said which column it is; and a hex or a function needs no header to be a value
        self.assertEqual(_palette.parse_tables("### Light theme\n" + HEAD + "| Muted | DimGray | 9a9aa8 |\n").light, {"muted": "#696969"})
        for value in ("#696969", "rgb(105, 105, 105)", "hsl(0 0% 41%)"):
            with self.subTest(value=value):
                p = _palette.parse_tables("### Light theme\n| Muted | %s | DimGray |\n" % value)
                self.assertEqual((p.light, p.problems), ({"muted": "#696969"}, []))

    def test_a_name_in_the_value_cell_and_another_colour_further_along_are_two_colours(self):
        for other, shown in (("#9a9aa8", "#9a9aa8"), ("`#9a9aa8`", "#9a9aa8"), ("#9a9aa8cc", "#9a9aa8cc"), ("rgb(154, 154, 168)", "rgb(154, 154, 168)")):
            with self.subTest(other=other):
                p = _palette.parse_tables("### Light theme\n| Token | Hex | Actual |\n|---|---|---|\n| Muted | DimGray | %s |\n" % other)
                self.assertEqual(p.light, {})
                self.assertEqual(codes(p), [("light", "muted", "palette-two-colours")])
                for part in ("DimGray", shown):
                    self.assertIn(part, p.problems[0][3])
        p = _palette.parse_tables("### Light theme\n| Token | Hex | Actual |\n|---|---|---|\n| Muted | DimGray | #696969 |\n")
        self.assertEqual((p.light, p.problems), ({"muted": "#696969"}, []), "the same colour, said twice")


class Rule6HeaderRowsAndRowsUnderOtherNames(unittest.TestCase):
    """6. The row directly above a separator row is the table's header row, unless its first cell is a
    row name; its second cell must be Hex. Any other row under another name goes to `unused` when a
    cell of it holds a colour, and is passed over when none does."""

    def test_a_header_row_that_calls_the_second_column_hex(self):
        for header in ("| Token | Hex |", "| Token | Hex | Use |", "| Rolle | HEX | Verwendung |", "| | **Hex** |", "| Name | `hex` | Name |", "|Token|Hex|"):
            with self.subTest(header=header):
                p = _palette.parse_tables("### Light theme\n%s\n|---|---|\n" % header + "\n".join(lines(STARTER_LIGHT)) + "\n")
                self.assertEqual((p.light, p.problems, p.unused, p.ignored), (STARTER_LIGHT, [], [], []))

    def test_under_any_other_header_a_table_with_colours_is_not_read_and_the_header_is_quoted(self):
        # the Name column before the hex: "| Muted | DimGray | 9a9aa8 |" was read as DimGray, and a failing pair printed as passing
        body = "\n".join("| %s | %s | %s |" % (l, "DimGray" if k == "muted" else "Ours", "9a9aa8" if k == "muted" else STARTER_LIGHT[k]) for k, l in LABELS) + "\n"
        for second, table_ in (("Name", body), ("Colour", body), ("Color", body), ("Value", plain(STARTER_LIGHT).split("\n", 2)[2]), ("HSL", "| Heading | hsl(240, 31%, 13%) | #16162a |\n"),
                               ("Hex code", "| Heading | #16162a |\n"), ("Hex (proposed)", "| Heading | #16162a |\n"), ("#b4531a", "| Heading | #16162a |\n"),
                               ("Background", "| Accent | #2b50e0 | white |\n"), ("Weight", "| Heading | Black |\n"), ("Hexadecimal", "| Muted | 5a5a72 |\n")):
            with self.subTest(second=second):
                p = _palette.parse_tables("### Light theme\n| Token | %s | Hex |\n|---|---|---|\n%s" % (second, table_))
                self.assertEqual((p.light, p.dark, p.brand, p.rows_found), ({}, {}, None, 0))
                self.assertIn(("?", None, "palette-header"), codes(p))
                message = [m for _t, _k, c, m in p.problems if c == "palette-header"][0]
                for part in ('calls its second column "%s"' % second, "under `### Light theme`", '"Hex"', "`| Token | Hex |`", "was not read"):
                    self.assertIn(part, message)
        p = _palette.parse_tables("### Light theme\n| Token |\n|---|\n| Heading | #16162a |\n")
        self.assertEqual((p.light, [c for _t, _k, c in codes(p)]), ({}, ["palette-header"]), "a header row with no second cell names no column")

    def test_under_another_header_a_table_without_any_colour_is_no_table_of_colours(self):
        # a BRAND.md holds more than colours: a type table under the dark theme's own heading is not nine mistakes
        type_table = "| Style | Weight | Tracking |\n|---|---|---|\n| Heading | 700 | -0.02em |\n| Body | 400 | 0 |\n| Link | Inter | underline |\n"
        for name, before in (("under its own heading", "\n## Typography\n"), ("under a bold line", "\n**Type scale**\n"), ("after a line of text", "\nThe type scale:\n"),
                             ("right under the dark theme's table", "\n"), ("under a heading that only looks like a theme's", "\n## Light theme typography\n"),
                             ("under one of the three headings itself", "\n### Dark theme\n")):
            with self.subTest(name=name):
                p = _palette.parse_tables(brand_md() + before + type_table)
                self.assertEqual(p.problems, [], "a complete palette is not made partial by the type table")
                self.assertEqual((p.missing(), p.light, p.dark, p.unused), ([], STARTER_LIGHT, STARTER_DARK, []))
                self.assertEqual(p.ignored, ["Heading", "Body", "Link"])

    def test_a_table_with_no_header_row_is_read_and_its_first_row_is_a_row(self):
        for name, md in (("no header", "### Light theme\n" + "\n".join(lines(STARTER_LIGHT)) + "\n"),
                         ("a rule line on top", "### Light theme\n|---|---|\n" + "\n".join(lines(STARTER_LIGHT)) + "\n"),
                         ("three columns", "### Light theme\n" + "\n".join(l + " use |" for l in lines(STARTER_LIGHT)) + "\n"),
                         ("a header line with no rule under it", "### Light theme\n| Token | Hex |\n" + "\n".join(lines(STARTER_LIGHT)) + "\n"),
                         ("any header line with no rule under it", "### Light theme\n| Token | Name |\n" + "\n".join(lines(STARTER_LIGHT)) + "\n")):
            with self.subTest(name=name):
                p = _palette.parse_tables(md)
                self.assertEqual((p.light, p.problems, p.unused), (STARTER_LIGHT, [], []))

    def test_a_row_above_a_separator_that_has_a_row_name_is_a_row(self):
        p = _palette.parse_tables("### Light theme\n| Heading | #16162a |\n|---|---|\n| Muted | #5a5a72 |\n")
        self.assertEqual((p.light, p.problems), ({"heading": "#16162a", "muted": "#5a5a72"}, []))

    def test_two_tables_that_stand_together_are_each_read_by_their_own_header(self):
        md = "### Light theme\n" + HEAD + "| Heading | navy |\n| Token | Name |\n|---|---|\n| Muted | Gray |\n" + HEAD + "| Link | blue |\n"
        p = _palette.parse_tables(md)
        self.assertEqual(p.light, {"heading": "#000080", "link": "#0000ff"})
        self.assertEqual(codes(p), [("?", None, "palette-header")])
        self.assertIn("colours for Muted", p.problems[0][3])

    def test_a_row_under_another_name_is_shown_when_it_holds_a_colour_and_passed_over_when_it_does_not(self):
        md = brand_md().replace("| Heading | `#16162a` |", "| Headings: | `#16162a` |").replace(
            "| Surface (cards) | `#ffffff` |", "| Surface / cards | `#ffffff` |").replace("| Link | `#2b50e0` |", "| --link | `#2b50e0` |")
        p = _palette.parse_tables(md + "| Success | - |\n| Notes | see the guide |\n| Warning | #aa5500 | #ffbb66 |\n| Text | Near Black | `#16162A` |\n"
                                       "| Hover | #1a3fb0 on hover |\n| Glass | rgba(0, 0, 0, 0.5) |\n| Ink | Navy |\n")
        self.assertEqual(p.unused, [("Headings:", ["#16162a"]), ("--link", ["#2b50e0"]), ("Surface / cards", ["#ffffff"]), ("Warning", ["#aa5500", "#ffbb66"]),
                                    ("Text", ["#16162a"]), ("Hover", ["#1a3fb0 on hover"]), ("Glass", ["rgba(0, 0, 0, 0.5)"]), ("Ink", ["Navy"])])
        self.assertEqual(p.missing(), [("light", "heading"), ("light", "link"), ("light", "surface")])
        self.assertEqual((p.problems, p.ignored), ([], []), "a row with no colour in it has nothing to show")
        self.assertEqual(_palette.parse_tables(brand_md()).unused, [])

    def test_a_header_row_that_holds_a_colour_is_shown_too(self):
        p = _palette.parse_tables("### Light theme\n| Brandfarbe | #b4531a |\n|---|---|\n| Heading | #16162a |\n")
        self.assertEqual(p.unused, [("Brandfarbe", ["#b4531a"])])
        self.assertEqual(([c for _t, _k, c in codes(p)], p.light), (["palette-header"], {}))


class Rule7WhereARowMayStand(unittest.TestCase):
    """7. Primary under Brand only, the nine theme rows under Light theme or Dark theme only; a row or a
    table with a colour anywhere else is named, never dropped and never filed by guess."""

    OLD = ("### Brand (fixed, theme-independent)\n| Token | Hex | Use |\n|---|---|---|\n| Primary | `#000000` | x |\n| Accent | `%s` | links |\n\n"
           "### Light theme\n%s\n### Dark theme\n%s")

    def old_layout(self, accent="#2b50e0", light=("accent",), dark=("accent",)):
        return self.OLD % (accent, table([(l, STARTER_LIGHT[k]) for k, l in LABELS if k not in light]),
                           table([(l, STARTER_DARK[k]) for k, l in LABELS if k not in dark]))

    def test_a_primary_in_a_themes_table_is_named_on_its_row_and_the_rest_is_read(self):
        # round 2: one Primary in each theme's table (two values) refused the whole file as "pasted together"
        md = "### Light theme\n" + HEAD + "| Primary | #2b50e0 |\n" + "\n".join(lines(STARTER_LIGHT)) + "\n### Dark theme\n" + HEAD + "| Primary | #8aa0ff |\n" + "\n".join(lines(STARTER_DARK)) + "\n"
        p = _palette.parse_tables(md)
        self.assertEqual((p.light, p.dark, p.brand), (STARTER_LIGHT, STARTER_DARK, None))
        self.assertEqual(codes(p), [("light", "brand", "palette-wrong-section"), ("dark", "brand", "palette-wrong-section")])
        for part in ("Primary: this row stands under `### Light theme`", "#2b50e0", "only under `### Brand`", "was not used"):
            self.assertIn(part, p.problems[0][3])
        # beside a Brand table that has one, it is still not a second value for it
        p = _palette.parse_tables(brand_md(extra="| Primary | `#123456` |\n"))
        self.assertEqual((p.brand, codes(p)), ("#000000", [("dark", "brand", "palette-wrong-section")]))
        p = _palette.parse_tables(brand_md(extra="| Primary | rgba(0, 0, 0, 0.5) |\n"))
        self.assertEqual(codes(p), [("dark", "brand", "palette-wrong-section")])
        self.assertIn("rgba(0, 0, 0, 0.5)", said(p))

    def test_a_theme_row_in_the_brand_table_is_named_and_not_filed(self):
        p = _palette.parse_tables("### Brand\n" + HEAD + "| Primary | #000000 |\n| Heading | #16162a |\n| Background | white |\n")
        self.assertEqual((p.brand, p.light, p.dark), ("#000000", {}, {}))
        self.assertEqual(codes(p), [("brand", "heading", "palette-wrong-section"), ("brand", "bg", "palette-wrong-section")])
        for part in ("Heading: this row stands under `### Brand`", "#16162a", "`### Light theme`", "`### Dark theme`", "was not used"):
            self.assertIn(part, p.problems[0][3])

    def test_the_old_layouts_accent_in_the_brand_table_is_the_accent_of_each_theme_that_has_none(self):
        p = _palette.parse_tables(self.old_layout(light=("accent", "link", "bg_soft"), dark=("accent", "link", "bg_soft")))
        self.assertEqual((p.light["accent"], p.dark["accent"], p.fixed_accent), ("#2b50e0", "#2b50e0", {"light", "dark"}))
        self.assertEqual(sorted(p.missing()), sorted([("light", "link"), ("light", "bg_soft"), ("dark", "link"), ("dark", "bg_soft")]))
        self.assertEqual(p.problems, [])
        # a theme with an accent of its own keeps it
        p = _palette.parse_tables(self.old_layout(dark=()))
        self.assertEqual((p.light["accent"], p.dark["accent"], p.fixed_accent), ("#2b50e0", "#8aa0ff", {"light"}))
        self.assertEqual(_palette.parse_tables(brand_md()).fixed_accent, set())

    def test_a_table_under_no_section_that_holds_colours_is_one_problem_that_says_where_it_stands(self):
        for name, md, where in (("above the first heading", plain(STARTER_LIGHT), "stands above the first heading"),
                                ("under another heading", "## Colours\n" + plain(STARTER_LIGHT), 'stands under the heading "## Colours"'),
                                ("under a line of text", "# Dark Roast Example Cafe\n\n**Light theme**\n\n" + plain(STARTER_LIGHT), 'stands under the line "**Light theme**"'),
                                ("after a line of text", "### Brand\n" + HEAD + "| Primary | #000000 |\nLight:\n" + plain(STARTER_LIGHT), 'stands after the line "Light:", further down under `### Brand`')):
            with self.subTest(name=name):
                p = _palette.parse_tables(md)
                self.assertEqual((p.light, p.dark), ({}, {}))
                self.assertEqual(codes(p), [("?", None, "palette-no-section")])
                for part in ("A table with colours for Heading, Body (ink), Muted, Accent, Link, Hairline, Background, Soft background and Surface (cards)", where,
                             "only under one of the three headings `### Brand`, `### Light theme` and `### Dark theme`", "were not used"):
                    self.assertIn(part, p.problems[0][3])
        # a header row that would not be read either is said in the same breath
        p = _palette.parse_tables("## Buttons\n| Variant | Background | Text |\n|---|---|---|\n| Primary | #2b50e0 | #ffffff |\n")
        self.assertEqual(codes(p), [("?", None, "palette-no-section")])
        self.assertIn('also calls the second column "Background"', p.problems[0][3])

    def test_a_named_row_without_a_colour_under_no_section_is_passed_over(self):
        # round 2: "## Light theme typography" over "| Heading | Inter 700 |" made a complete palette partial
        for before, body, ignored in (("\n## Typography\n\nInter in three weights: Bold, Regular, Light\n\n", "| Element | Weight | Size |\n|---|---|---|\n| Heading | 700 | 2.5rem |\n| Body | 400 | 1rem |\n| Link | 400 | 1rem |\n", ["Heading", "Body", "Link"]),
                                      ("\n## Light theme typography\n", "| Heading | Inter 700 |\n", ["Heading"]),
                                      ("\n## Brand fonts\n", "| Role | Font |\n|---|---|\n| Primary | Inter |\n| Secondary | Georgia |\n", ["Primary"]),
                                      ("\n## Typography\n\n- Weights: 700, 400, 300 light\n\n", "| Heading | 700 |\n| Body | 400 |\n", ["Heading", "Body"]),
                                      ("\n## Notes\n", "| Muted | notacolour |\n| Accent | #[…] |\n| Link | |\n", ["Muted", "Accent", "Link"])):
            with self.subTest(before=before):
                p = _palette.parse_tables(brand_md() + before + body)
                self.assertEqual((p.problems, p.missing(), p.unused), ([], [], []))
                self.assertEqual((p.light, p.dark, p.brand), (STARTER_LIGHT, STARTER_DARK, "#000000"))
                self.assertEqual(p.ignored, ignored)

    def test_a_row_whose_cell_cannot_be_read_is_not_said_to_have_a_value(self):
        # round 2: "has a value but no heading says which theme" was printed for a cell that held no value at all
        p = _palette.parse_tables(HEAD + "| Muted | notacolour |\n")
        self.assertEqual((p.problems, p.ignored), ([], ["Muted"]), "no colour, no section: nothing is claimed of it")
        p = _palette.parse_tables(HEAD + "| Muted | 5a5a72 |\n")
        self.assertEqual(codes(p), [("?", None, "palette-no-section")], "what looks like a colour is spoken of: where the table stands")
        self.assertNotIn("has a value", said(p))
        p = _palette.parse_tables("### Light theme\n" + HEAD + "| Muted | notacolour |\n")
        self.assertEqual(codes(p), [("light", "muted", "colour-unreadable")], "and under its heading: what the cell holds")
        self.assertIn('the second cell holds "notacolour"', said(p))

    def test_a_row_in_the_wrong_table_without_a_colour_is_passed_over(self):
        p = _palette.parse_tables(brand_md(extra="| Primary | Inter |\n| Primary | #[…] |\n") + "\n### Brand\n" + HEAD + "| Heading | 700 |\n")
        self.assertEqual((p.problems, p.ignored, p.brand), ([], ["Primary", "Primary", "Heading"], "#000000"))


class Rule8TheSameRowTwice(unittest.TestCase):
    """8. The same row twice in one section with two different values is refused as ambiguous, for the
    theme rows, for Primary and for the Brand table's Accent alike. The same value twice is fine."""

    def refused(self, md, *parts):
        with self.assertRaises(Refusal) as cm:
            _palette.parse_tables(md)
        self.assertEqual(cm.exception.code, "palette-ambiguous")
        for part in parts + ("two different values", "pasted together"):
            self.assertIn(part, str(cm.exception))

    def test_two_palettes_under_the_same_headings_are_not_guessed_between(self):
        other = dict(STARTER_LIGHT, accent="#c0392b")
        self.refused(brand_md() + "\n### Light theme\n" + table([(l, other[k]) for k, l in LABELS]), "Accent in the light theme", "#2b50e0", "#c0392b")
        self.refused(brand_md(extra="| Muted | `#777777` |\n"), "Muted in the dark theme", "#a6abce", "#777777")
        self.refused(brand_md(extra="\n" + HEAD + "| Muted | `#777777` |\n"), "Muted in the dark theme")

    def test_two_different_primaries_or_two_different_fixed_accents(self):
        second = "\n### Brand\n" + HEAD + "| Primary | `%s` |\n"
        self.refused(brand_md() + second % "#123456", "Primary", "#000000", "#123456")
        self.refused(brand_md().replace("| Primary | `#000000` | buttons, brand surfaces |", "| Primary | `#000000` | a |\n| Primary | `#123456` | b |"), "Primary")
        md = "### Brand\n" + HEAD + "| Accent | #111111 |\n| Accent | %s |\n"
        self.refused(md % "#222222", "Accent", "#111111", "#222222")
        self.assertEqual(_palette.parse_tables(md % "#111111").light["accent"], "#111111")

    def test_the_same_value_twice_in_any_spelling_is_not_a_conflict(self):
        p = _palette.parse_tables(brand_md() + "\n### Light theme\n" + table([(l, STARTER_LIGHT[k].upper()) for k, l in LABELS]) + "\n### Brand\n" + HEAD + "| Primary | rgb(0, 0, 0) |\n")
        self.assertEqual((p.light, p.dark, p.brand, p.problems), (STARTER_LIGHT, STARTER_DARK, "#000000", []))

    def test_the_two_themes_are_two_sections_and_a_row_in_each_is_not_twice(self):
        p = _palette.parse_tables(brand_md())
        self.assertNotEqual(p.light["muted"], p.dark["muted"])

    def test_a_second_row_that_cannot_be_read_is_named_and_the_first_keeps_its_value(self):
        p = _palette.parse_tables(brand_md(extra="| Muted | 700 |\n"))
        self.assertEqual((p.dark["muted"], codes(p)), ("#a6abce", [("dark", "muted", "colour-unreadable")]))


class Rule9Proposals(unittest.TestCase):
    """9. A row is a proposal when the word proposed or proposal stands in its value cell or a later
    cell, or in the bracketed remark of its section's heading. Nowhere else: and where the word stands
    where it is not read, a problem quotes the line."""

    def test_a_proposal_is_marked_and_stays_one_until_the_mark_goes(self):
        p = _palette.parse_tables(brand_md(dark=dict(STARTER_DARK, muted="#a6abce (proposed)")))
        self.assertEqual((p.dark["muted"], p.proposed, p.problems), ("#a6abce", {("dark", "muted")}, []))
        self.assertEqual(_palette.parse_tables(brand_md()).proposed, set())

    def test_the_word_in_any_cell_after_the_first_marks_the_row(self):
        # round 2: "| Primary | #000000 | - | proposed |" lost the mark, passed, and got past the installer's question
        for name, row in (("in the value cell", "| Muted | `#a6abce` (proposed) |"), ("in a third cell", "| Muted | `#a6abce` | (proposed) |"),
                          ("in capitals", "| Muted | `#a6abce` | PROPOSED |"), ("among words", "| Muted | `#a6abce` | my proposal, not yet agreed |"),
                          ("after a dash cell", "| Muted | #a6abce | - | proposed |"), ("after an empty cell", "| Muted | #a6abce | | | Proposal |"),
                          ("after a placeholder cell", "| Muted | #a6abce | #[…] | proposed |"), ("after a cell that is no colour", "| Muted | #a6abce | 6.5:1 | n/a | proposed |"),
                          ("said not to be", "| Muted | #a6abce | not proposed |")):
            with self.subTest(name=name):
                p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", row))
                self.assertEqual((p.dark["muted"], p.proposed, p.missing(), p.problems), ("#a6abce", {("dark", "muted")}, [], []))
        p = _palette.parse_tables("### Brand\n" + HEAD + "| Primary | #000000 | - | proposed |\n")
        self.assertEqual((p.brand, p.proposed), ("#000000", {("brand", "brand")}))
        # a word that only contains it is not it
        for note in ("unproposed, purposed", "proposals", "proposer", "re-proposing"):
            with self.subTest(note=note):
                p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | %s |" % note))
                self.assertEqual((p.proposed, p.problems), (set(), []))

    def test_a_proposed_primary_and_a_proposed_fixed_accent(self):
        for value in ("#000000 (proposed)", "#000000 (Proposed)", "#000000 proposed"):
            with self.subTest(value=value):
                p = _palette.parse_tables(brand_md(primary=value))
                self.assertEqual((p.brand, p.proposed), ("#000000", {("brand", "brand")}))
                self.assertEqual(p.theme("brand"), {"brand": "#000000"}, "so that whoever lists the proposals can show its value")
        # given twice, proposed once: still a proposal
        twice = brand_md(primary="#000000 (proposed)") + "\n### Brand\n" + HEAD + "| Primary | #000000 |\n"
        self.assertEqual(_palette.parse_tables(twice).proposed, {("brand", "brand")})
        self.assertEqual(_palette.Palette().theme("brand"), {})
        md = ("### Brand\n" + HEAD + "| Accent | `#2b50e0` (proposed) |\n\n### Light theme\n" + table([("Background", "#ffffff")])
              + "\n### Dark theme\n" + table([("Accent", "#8aa0ff")]))
        self.assertEqual(_palette.parse_tables(md).proposed, {("light", "accent")}, "the dark theme has an accent of its own, which nobody proposed")

    def test_the_word_in_the_headings_bracketed_remark_marks_every_row_under_it_until_the_next_heading(self):
        every = {("dark", k) for k in STARTER_DARK}
        for heading in ("### Dark theme (proposed)", "### Dark theme (Proposal)", "### Dark theme (proposed, not yet agreed)", "### **Dark theme** (*proposed*)"):
            with self.subTest(heading=heading):
                p = _palette.parse_tables(brand_md().replace("### Dark theme", heading))
                self.assertEqual((p.proposed, p.light, p.dark, p.problems), (every, STARTER_LIGHT, STARTER_DARK, []))
        # every table of the section, also one that follows after blank lines (the second table is still that section)
        body = lines(STARTER_DARK)
        md = "### Dark theme (proposed)\n" + HEAD + "\n".join(body[:4]) + "\n\n\n" + HEAD + "\n".join(body[4:]) + "\n### Light theme\n" + plain(STARTER_LIGHT)
        p = _palette.parse_tables(md)
        self.assertEqual((p.proposed, p.dark, p.light), (every, STARTER_DARK, STARTER_LIGHT), "and the next heading ends it")
        p = _palette.parse_tables(brand_md().replace("### Brand (fixed, theme-independent)", "### Brand (proposed)"))
        self.assertEqual(p.proposed, {("brand", "brand")})
        p = _palette.parse_tables(brand_md().replace("### Dark theme", "### Dark theme (suggested)"))
        self.assertEqual((p.proposed, p.problems), (set(), []), "the mark is the one word")

    def test_the_word_where_it_is_not_read_marks_nothing_and_is_named(self):
        # round 2: a mark in a parent heading, in a line between heading and table, in a footnote: lost without a word
        cases = (
            ("a line between the heading and the table", brand_md().replace("### Dark theme\n", "### Dark theme\n\n*Proposed, not yet confirmed*\n\n"), 'The line "*Proposed, not yet confirmed*", under `### Dark theme`,'),
            ("a sentence under the heading", brand_md().replace("### Dark theme\n", "### Dark theme\nThese dark values are a proposal; please confirm.\n"), 'The line "These dark values are a proposal; please confirm.", under `### Dark theme`,'),
            ("a footnote under the table", brand_md() + "\n\\* proposed, to be confirmed\n", 'The line "\\* proposed, to be confirmed", under `### Dark theme`,'),
            ("a heading above the three", brand_md().replace("## Colour palette", "## Proposed palette"), 'The heading "## Proposed palette", above `### Brand`,'),
            ("the header row", brand_md().replace("### Dark theme\n| Token | Hex |", "### Dark theme\n| Token | Hex | Status: proposed |"), 'The header row "Token | Hex | Status: proposed" of the table under `### Dark theme`'),
        )
        for name, md, where in cases:
            with self.subTest(name=name):
                p = _palette.parse_tables(md)
                self.assertEqual((p.proposed, p.light, p.dark, p.brand), (set(), STARTER_LIGHT, STARTER_DARK, "#000000"))
                self.assertEqual(codes(p), [("?", None, "palette-mark-not-read")])
                for part in (where, 'holds the word "proposed"', "`#a6abce (proposed)`", "`### Dark theme (proposed)`", "marked no value"):
                    self.assertIn(part, p.problems[0][3])

    def test_the_word_in_a_place_that_is_not_a_place_for_a_mark_either_way(self):
        # in the header's second cell the table is not read at all, in the first cell the row is not; both are said
        p = _palette.parse_tables(brand_md().replace("### Dark theme\n| Token | Hex |", "### Dark theme\n| Token | Hex (proposed) |"))
        self.assertEqual((p.dark, p.proposed, [c for _t, _k, c in codes(p)]), ({}, set(), ["palette-mark-not-read", "palette-header"]))
        p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", "| Muted (proposed) | `#a6abce` |"))
        self.assertEqual((p.proposed, p.unused, p.missing()), (set(), [("Muted (proposed)", ["#a6abce"])], [("dark", "muted")]))
        # a heading that is not one of the three is no heading of a table: its table is not read, so nothing is unmarked
        for heading in ("### Dark theme proposals", "### Proposal: dark theme", "### Dark theme, proposed"):
            with self.subTest(heading=heading):
                p = _palette.parse_tables(brand_md().replace("### Dark theme", heading))
                self.assertEqual((p.dark, p.proposed, [c for _t, _k, c in codes(p)]), ({}, set(), ["palette-no-section"]))

    def test_the_word_far_from_the_tables_is_only_a_word(self):
        md = ("The designer proposed three palettes; this is the one we chose.\n\n" + brand_md()
              + "\n## Notes\n\nWe proposed a serif face and dropped it.\n\n### Proposed changes for next year\n\nNone yet.\n")
        p = _palette.parse_tables(md)
        self.assertEqual((p.proposed, p.problems), (set(), []))
        # a heading with the word that is no ancestor of the three is not above them
        p = _palette.parse_tables("### Proposed logo\n\ntext\n\n" + brand_md().replace("# Example Bakery: brand & style guide\n\n## Colour palette\n\n", ""))
        self.assertEqual((p.proposed, p.problems), (set(), []))


class Rule10NothingIsReadFromAnywhereElse(unittest.TestCase):
    """10. No table with a Light and a Dark column, no column of names, no tolerance between two
    spellings of a colour, no labels, no names beyond rule 4's."""

    COMBINED = "\n".join("| %s | %s | %s |" % (l, STARTER_LIGHT[k], STARTER_DARK[k]) for k, l in LABELS) + "\n"

    def test_a_table_whose_header_names_both_themes_is_a_problem_and_is_not_read(self):
        for header in ("| Token | Light | Dark |", "| Token | Light theme | Dark theme |", "| Token | Light / Dark | Use |", "| Token | Light and dark | Use |",
                       "| Token | LIGHT | DARK | Notes |", "| Token | Dark | Light |"):
            for heading in ("", "## Colours\n", "### Light theme\n", "### Dark theme\n"):
                with self.subTest(header=header, heading=heading):
                    p = _palette.parse_tables(heading + header + "\n|---|---|---|\n" + self.COMBINED)
                    self.assertEqual((p.light, p.dark, p.brand, p.rows_found), ({}, {}, None, 0))
                    self.assertEqual(codes(p), [("?", None, "palette-combined-table")])
                    for part in ("names both themes", header.strip("| "), "give each theme its own table", "`### Light theme`", "`### Dark theme`", "`| Token | Hex |`", "was not read"):
                        self.assertIn(part, p.problems[0][3])

    def test_a_table_like_it_with_no_colours_yet_is_passed_over_and_one_without_the_header_is_two_colours_a_row(self):
        p = _palette.parse_tables("| Token | Light | Dark |\n|---|---|---|\n| Heading | | |\n| Muted | #[…] | #[…] |\n")
        self.assertEqual((p.problems, p.ignored), ([], ["Heading", "Muted"]))
        p = _palette.parse_tables("### Light theme\n" + self.COMBINED)
        self.assertEqual(p.light, {})
        self.assertEqual([c for _t, _k, c in codes(p)], ["palette-two-colours"] * 9)
        # "Highlights" beside "Dark" names one theme: the header is quoted for what it calls the second column
        p = _palette.parse_tables("### Light theme\n| Token | Highlights | Dark |\n|---|---|---|\n| Muted | #5a5a72 | #a6abce |\n")
        self.assertEqual(([c for _t, _k, c in codes(p)], p.light), (["palette-header"], {}))

    def test_what_the_liberal_reader_did_is_gone(self):
        for name in ("_same_but_rounded", "_label_of", "_section_of", "_ALIASES", "_KEY_OF_ALIAS", "_INNER", "_row", "_cell", "_key"):
            self.assertFalse(hasattr(_palette, name), name)
        self.assertEqual(sorted(_palette.ROW_KEY), sorted(["primary", "heading", "body (ink)", "muted", "accent", "link", "hairline", "background",
                                                           "soft background", "surface (cards)", "body", "surface"]))

    def test_every_value_returned_stands_in_the_value_cell_of_a_row_the_rules_read(self):
        # the rule above all rules, on a document with everything else in it
        md = ("# Light and dark: our brand\n\nLight theme: #111111. Dark theme: #222222. | Muted | #333333 |\n\n**Light theme**\n" + HEAD + "| Muted | #444444 |\n\n"
              + brand_md(light=dict(STARTER_LIGHT, muted="#5a5a72"))
              + "\n\n| Element | Colour |\n|---|---|\n| Link | #555555 |\n\nDark theme\n\n" + HEAD + "| Muted | #666666 |\n\n## Dark theme extras\n" + HEAD + "| Muted | #777777 |\n")
        p = _palette.parse_tables(md)
        self.assertEqual((p.light, p.dark, p.brand), (STARTER_LIGHT, STARTER_DARK, "#000000"))
        self.assertEqual([c for _t, _k, c in codes(p)], ["palette-no-section", "palette-header", "palette-no-section", "palette-no-section"])
        for value in ("#444444", "#555555", "#666666", "#777777"):
            self.assertNotIn(value, list(p.light.values()) + list(p.dark.values()))


class Rule11WhenNoRowWasFound(unittest.TestCase):
    """11. When no row was found at all, rows_found is 0 and the command prints FORM."""

    def test_documents_in_which_no_row_stands_where_one_is_read(self):
        ai = ("## Color Palette\n\n### Light Mode\n| Role | Color | Hex |\n|------|-------|-----|\n| Background | White | `#FFFFFF` |\n| Surface | Ghost White | `#F5F7FB` |\n"
              "| Text | Near Black | `#16162A` |\n| Primary | Royal Blue | `#2B50E0` |\n| Border | Light Gray | `#E3E7F2` |\n")
        for name, md in (("nothing", ""), ("a sentence", "Our colours are warm.\n"), ("headings and no rows", "### Brand\n\n### Light theme\n\n### Dark theme\n"),
                         ("another tool's answer", ai), ("the tables under translated headings", brand_md().replace("### Light theme", "### Helles Design").replace(
                             "### Dark theme", "### Dunkles Design").replace("### Brand (fixed, theme-independent)", "### Marke"))):
            with self.subTest(name=name):
                p = _palette.parse_tables(md)
                self.assertEqual((p.rows_found, p.light, p.dark, p.brand), (0, {}, {}, None))
                self.assertEqual(len(p.missing()), 18)
        p = _palette.parse_tables(ai)
        self.assertEqual([c for _t, _k, c in codes(p)], ["palette-no-section"])
        self.assertIn('under the heading "### Light Mode"', said(p))
        self.assertIn('also calls the second column "Color"', said(p))
        self.assertEqual(p.unused, [("Text", ["#16162a"]), ("Border", ["#e3e7f2"])])

    def test_a_row_found_and_not_filled_in_is_a_row_found(self):
        self.assertEqual(_palette.parse_tables(one("#[…]")).rows_found, 1)
        self.assertEqual(_palette.parse_tables(one("notacolour")).rows_found, 1)

    def test_the_sentence_names_the_three_headings_the_header_row_and_every_row(self):
        for part in ["`### Brand`", "`### Light theme`", "`### Dark theme`", "`| Token | Hex |`", "`|---|---|`", "Primary", "The assistant can write"] + [l for _k, l in LABELS]:
            self.assertIn(part, _palette.FORM)


class Round2Inputs(unittest.TestCase):
    """The inputs of the review round that ended the liberal reader. Each ends in a correct reading or in a
    named problem: never in a silent misreading, and never in "two palettes pasted together" for a label
    the reader does not read."""

    L, D = plain(STARTER_LIGHT), plain(STARTER_DARK)

    def outcome(self, md):
        p = _palette.parse_tables(md)  # a Refusal here fails the test: none of these is two palettes
        return len(p.light), len(p.dark), p.brand, sorted({c for _t, _k, c in codes(p)})

    def test_headings_that_name_a_theme_in_passing_and_bold_labels(self):
        for name, md in (("dark heading, bold labels", "## Dark-mode first palette\n\n**Light theme**\n" + self.L + "\n**Dark theme**\n" + self.D),
                         ("logo on dark backgrounds", "## Logo on dark backgrounds\n\nUse the white version.\n\n**Light theme**\n" + self.L),
                         ("a business with Dark in its name", "# Dark Roast Example Cafe\n\n**Light theme**\n\n" + self.L + "\n**Dark theme**\n\n" + self.D),
                         ("a caption that ends in the other theme", "**Light theme**\n" + self.L + "\n**Dark theme**\nAccent and link are lighter than in light mode\n" + self.D),
                         ("only dark, with a caption", "**Dark theme**\nSame roles as light\n" + self.D),
                         ("labels with a word after them", "**Light theme tokens**\n" + self.L + "\n**Dark theme tokens**\n" + self.D),
                         ("list items", "- Light\n" + self.L + "- Dark\n" + self.D), ("an underlined heading", "Light theme\n-----------\n\n" + self.L),
                         ("sub-headings under a theme", "## Light theme\n### Text\n" + HEAD + "| Heading | #16162a |\n### Backgrounds\n" + HEAD + "| Background | #ffffff |\n")):
            with self.subTest(name=name):
                self.assertEqual(self.outcome(md), (0, 0, None, ["palette-no-section"]))

    def test_a_label_under_a_real_heading_does_not_make_two_palettes(self):
        for label, extra in (("**Dark theme – proposed**", ["palette-mark-not-read"]), ("Dark theme, proposed:", ["palette-mark-not-read"]),
                             ("**Dark theme (proposed):**", ["palette-mark-not-read"]), ("**Dark theme**", []), ("Dark version", [])):
            with self.subTest(label=label):
                self.assertEqual(self.outcome("### Light theme\n" + self.L + "\n" + label + "\n" + self.D), (9, 0, None, sorted(extra + ["palette-no-section"])))

    def test_type_tables_beside_a_complete_palette(self):
        both = "### Light theme\n" + self.L + "\n### Dark theme\n" + self.D
        for tail in ("\n## Typography\n\nInter in three weights: Bold, Regular, Light\n\n| Element | Weight | Size |\n|---|---|---|\n| Heading | 700 | 2.5rem |\n| Body | 400 | 1rem |\n",
                     "\n## Typography\n\n- Weights: 700, 400, 300 light\n\n| Element | Weight |\n|---|---|\n| Heading | 700 |\n| Body | 400 |\n",
                     "\n## Brand fonts\n| Role | Font |\n|---|---|\n| Primary | Inter |\n| Secondary | Georgia |\n"):
            with self.subTest(tail=tail):
                self.assertEqual(self.outcome(both + tail), (9, 9, None, []))
        # a table of button colours under its own heading holds a colour under the name Primary: said, not taken
        self.assertEqual(self.outcome(both + "\n## Buttons\n| Variant | Background | Text |\n|---|---|---|\n| Primary | #2b50e0 | #ffffff |\n"), (9, 9, None, ["palette-no-section"]))

    def test_a_column_of_names_before_the_hex(self):
        head = "### Light theme\n| Token | Name | Hex |\n|---|---|---|\n"
        for body in ("| Background | Beige | c9bfa6 |\n| Heading | Navy | 1b2a4a |\n", "| Background | White | #ffffffcc |\n| Accent | Tomato | #e8604c80 |\n",
                     "| Accent | Coral | oklch(0.7 0.4 30) |\n", "| Surface (cards) | White | rgba(255, 255, 255, 0.8) |\n", "| Background | White | #[…] |\n",
                     "| Accent | Crimson | #c81e3 |\n| Link | Blue | #2b50eO |\n", "| Muted | DimGray | 9a9aa8 |\n", "| Muted | Gray | #9a9aa8cc |\n"):
            with self.subTest(body=body):
                self.assertEqual(self.outcome(head + body), (0, 0, None, ["palette-header"]))

    def test_notes_and_second_colours_in_the_cells(self):
        head = "### Light theme\n| Token | Hex | Contrast |\n|---|---|---|\n"
        self.assertEqual(_palette.parse_tables(head + "| Heading | #16162a | 16.9:1 (AAA) |\n| Muted | #5a5a72 | 6.5:1 on #ffffff |\n| Background | #ffffff | — |\n").light,
                         {"heading": "#16162a", "muted": "#5a5a72", "bg": "#ffffff"})
        self.assertEqual(_palette.parse_tables(head + "| Surface (cards) | #ffffff | sits on #fdfdfd |\n| Background | #fdfdfd | cards on it are #ffffff |\n").light,
                         {"surface": "#ffffff", "bg": "#fdfdfd"})
        self.assertEqual(self.outcome("### Light theme\n" + HEAD + "| Link | #2b50e0 / #9fb0ff |\n| Accent | #2b50e0 or #1a3fb0 |\n| Heading | #16162a (was #000000) |\n"),
                         (0, 0, None, ["palette-not-one-colour"]))
        hex_rgb_hsl = "### Light theme\n| Token | Hex | RGB | HSL |\n|---|---|---|---|\n| Heading | #16162a | rgb(22, 22, 42) | hsl(240, 31%, 13%) |\n| Muted | #5a5a72 | rgb(90, 90, 114) | hsl(240, 12%, 40%) |\n"
        self.assertEqual(self.outcome(hex_rgb_hsl), (1, 0, None, ["palette-two-colours"]), "one row's three spellings agree, the other's do not: no tolerance, and it is said")

    def test_marks_in_the_form_the_skill_writes_and_in_forms_it_does_not(self):
        md = ("### Light theme\n" + HEAD + "| Accent | `#e2874a (proposed)` |\n| Link | `#e2874a` (proposed) |\n| Muted | #5a5a72 (Proposed) |\n| Heading | #16162a(proposed) |\n"
              "| Hairline | #e3e7f2 [proposed] |\n| Background | #ffffff - proposed |\n| Surface (cards) | #ffffff ← proposed |\n")
        p = _palette.parse_tables(md)
        self.assertEqual(p.proposed, {("light", "accent"), ("light", "link"), ("light", "muted"), ("light", "heading")})
        self.assertEqual(sorted(k for _t, k, _c in codes(p)), ["bg", "line", "surface"], "what is not the mark's form is no value at all: nothing goes in unmarked")
        status = ("### Dark theme\n| Token | Hex | Status |\n|---|---|---|\n| Heading | #e7e9fb | confirmed |\n| Muted | #a6abce | Proposed |\n| Link | #9fb0ff | PROPOSAL |\n"
                  "| Accent | #8aa0ff | proposal — pending |\n| Background | #0a0b1e | not proposed |\n")
        self.assertEqual(_palette.parse_tables(status).proposed, {("dark", "muted"), ("dark", "link"), ("dark", "accent"), ("dark", "bg")})

    def test_other_shapes_of_one_table_for_both_themes(self):
        for md in ("## Colours\n| Token | Light | Dark | Notes |\n|---|---|---|---|\n| Heading | #16162a | #e7e9fb | |\n| Primary | #000000 | #000000 | brand |\n| Accent | #2b50e0 | #8aa0ff (proposed) | |\n",
                   "| Token | Light | Dark |\n|---|---|---|\n| Primary | #2b50e0 | #8aa0ff |\n| Heading | #16162a | #e7e9fb |\n",
                   "| Token | Light / Dark |\n|---|---|\n| Heading | #16162a / #e7e9fb |\n| Background | #ffffff / #0a0b1e |\n"):
            with self.subTest(md=md):
                self.assertEqual(self.outcome(md), (0, 0, None, ["palette-combined-table"]))
        self.assertEqual(self.outcome("### Light theme\n| Token | Value |\n|---|---|\n| Heading | #16162a / #e7e9fb |\n"), (0, 0, None, ["palette-header"]))
        self.assertEqual(self.outcome("## Colours\n\n| Light theme | Hex |\n|---|---|\n| Heading | #16162a |\n\n| Dark theme | Hex |\n|---|---|\n| Heading | #e7e9fb |\n"),
                         (0, 0, None, ["palette-no-section"]))


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
    """`read_css` reads the three blocks in the form the intake's editor (`_site.edit_css`) can write to,
    and names everything else: a block in another shape, one that stands twice, a colour set twice in a
    block, one marked !important."""

    def bakery(self):
        p = _palette.Palette()
        p.light, p.dark, p.brand = dict(T.BAKERY_LIGHT), dict(T.BAKERY_DARK), "#b4531a"
        return p

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
                       '@import url("a;b.css");', '@namespace svg url(http://www.w3.org/2000/svg);\n\n\n', '@import "theme.css";\n@theme {\n  --color-brand: #000;\n}\n'):
            with self.subTest(before=before):
                self.assert_all_three_blocks(before + self.starter())
        # and one between the blocks hides neither of the dark ones
        text = self.starter().replace(':root[data-theme="dark"]', '@import "late.css";\n:root[data-theme="dark"]', 1)
        self.assert_all_three_blocks(text.replace("@media (prefers-color-scheme: dark)", '@import "later.css"; @media (prefers-color-scheme: dark)', 1))

    def test_the_spellings_of_the_three_blocks_that_the_editor_finds_are_read(self):
        for old, new in ((":root {", ":root{"), (":root {", ":root\n{"), (":root {", "  \t:root   {"), (':root[data-theme="dark"] {', ":root[data-theme='dark'] {"),
                         (':root[data-theme="dark"] {', ':root[ data-theme = "dark" ]\n{'), ("@media (prefers-color-scheme: dark) {", "@media(prefers-color-scheme:dark){"),
                         ("@media (prefers-color-scheme: dark) {", "@media  ( prefers-color-scheme : dark )\n{"), (":root:not([data-theme]) {", ":root:not( [ data-theme ] ){")):
            with self.subTest(new=new):
                self.assertIn(old, self.starter())
                self.assert_all_three_blocks(self.starter().replace(old, new, 1))

    def test_a_block_in_another_shape_is_named_and_not_read(self):
        # the reading used to take these for the block; the editor writes to none of them
        whole = self.starter()
        dark_at, media_at, rest_at = whole.index(':root[data-theme="dark"]'), whole.index("@media (prefers-color-scheme: dark)"), whole.index("*, *::before")
        swap = lambda old, new: (self.assertEqual(whole.count(old), 1), whole.replace(old, new))[1]  # noqa: E731
        media = "@media (prefers-color-scheme: dark) { "
        cases = ((swap(":root {", ":root, html {"), "light", "`:root, html { ... }`"), (swap(":root {", "html, :root {"), "light", "`html, :root { ... }`"),
                 (swap(":root {", ":ROOT {"), "light", "`:ROOT { ... }`"), (swap(":root {", ":Root,body{"), "light", "`:Root,body { ... }`"),
                 (swap(":root {", "html:root {"), "light", "`html:root { ... }`"), (swap(":root {", '@charset "utf-8"; :root {'), "light", "`:root { ... }`"),
                 ("@layer base {\n" + whole[:dark_at] + "}\n" + whole[dark_at:], "light", "`@layer base { :root { ... } }`"),
                 (swap(':root[data-theme="dark"] {', ':root[data-theme="dark"], .dark {'), "dark", '`:root[data-theme="dark"], .dark { ... }`'),
                 (swap(':root[data-theme="dark"] {', ":ROOT[DATA-THEME='dark'] {"), "dark", "`:ROOT[DATA-THEME='dark'] { ... }`"),
                 (swap(':root[data-theme="dark"] {', ":root[data-theme=dark] {"), "dark", "`:root[data-theme=dark] { ... }`"),
                 (swap('}\n\n:root[data-theme="dark"] {', '} :root[data-theme="dark"] {'), "dark", '`:root[data-theme="dark"] { ... }`'),
                 (swap("@media (prefers-color-scheme: dark) {", "@MEDIA (PREFERS-COLOR-SCHEME: DARK) {"), "dark_media", "`@MEDIA (PREFERS-COLOR-SCHEME: DARK) { :root:not([data-theme]) { ... } }`"),
                 (swap("@media (prefers-color-scheme: dark) {", "@media screen and (prefers-color-scheme: dark) {"), "dark_media", "`@media screen and (prefers-color-scheme: dark) { :root:not([data-theme]) { ... } }`"),
                 (whole[:media_at] + "@supports (color: red) {\n" + whole[media_at:rest_at] + "}\n" + whole[rest_at:], "dark_media", "`@supports (color: red) { " + media + ":root:not([data-theme]) { ... } } }`"),
                 (swap(":root:not([data-theme]) {", ":root:not([data-theme]), html.auto {"), "dark_media", "`" + media + ":root:not([data-theme]), html.auto { ... } }`"),
                 (swap(":root:not([data-theme]) {", ":ROOT:NOT([data-theme]) {"), "dark_media", "`" + media + ":ROOT:NOT([data-theme]) { ... } }`"),
                 (swap(":root:not([data-theme]) {", ":root {"), "dark_media", "`" + media + ":root { ... } }`"),
                 (swap(":root:not([data-theme]) {", ':root:not([data-theme="light"]) {'), "dark_media", "`" + media + ':root:not([data-theme="light"]) { ... } }`'))
        for text, lacking, shown in cases:
            with self.subTest(shown=shown):
                css = _palette.read_css(text)
                self.assertEqual(css.found, {"light", "dark", "dark_media"} - {lacking})
                self.assertEqual([(block, variable) for block, variable, _m in css.problems], [(lacking, None)], "said once, and not also as not found")
                for part in ("The rule " + shown, "written in another way than the starter writes it", "did not read it", "does not write to it"):
                    self.assertIn(part, css.problems[0][2])
                self.assertEqual({"light": css.light, "dark": css.dark, "dark_media": css.dark_media}[lacking], {})
                self.assertEqual(_palette.drift(_palette.parse_tables(brand_md()), css), [], "what was not read is not also reported as drift")
        # the value of the attribute is not a word of CSS: "DARK" is another theme, and so is "night"
        css = _palette.read_css(whole.replace(':root[data-theme="dark"] {', ':root[data-theme="night"] {', 1))
        self.assertEqual(css.found, {"light", "dark_media"})

    def test_a_rule_that_names_two_of_the_blocks_at_once_is_named_for_both(self):
        # round 2: `:root, :root[data-theme="dark"] { ... }` was filed as the light block only, and the dark one reported missing
        text = ':root, :root[data-theme="dark"] {\n  --bg: #ffffff;\n  --ink: #111111;\n}\n'
        css = _palette.read_css(text)
        self.assertEqual((css.found, css.light, css.dark), (set(), {}, {}))
        self.assertEqual([(b, v) for b, v, _m in css.problems], [("light", None), ("dark", None), ("dark_media", None)])
        for block, _v, message in css.problems[:2]:
            self.assertIn('`:root, :root[data-theme="dark"] { ... }`', message)
            self.assertIn("written in another way than the starter writes it", message)
        self.assertIn("has no @media", css.problems[2][2])

    def test_another_rule_that_sets_a_colour_on_root_is_named_beside_the_block_that_is_read(self):
        for name, rule in (("in a supports block", "@supports (color: oklch(0 0 0)) {\n  :root { --accent: oklch(0.5 0.2 265); }\n}\n"),
                           ("in a print block", "@media print {\n:root { --bg: #ffffff; }\n}\n"), ("for a light attribute", ':root[data-theme="light"] { --bg: #fafafa; }\n')):
            with self.subTest(name=name):
                css = _palette.read_css(self.starter() + rule)
                self.assertEqual((css.found, css.light, css.dark), ({"light", "dark", "dark_media"}, STARTER_LIGHT, STARTER_DARK))
                self.assertEqual([(b, v) for b, v, _m in css.problems], [("light", None)])
                self.assertIn("written in another way than the starter writes it", css.problems[0][2])
        # a rule on :root that sets no colour, and a rule elsewhere, are nobody's business here
        self.assert_all_three_blocks(self.starter() + "@media (prefers-reduced-motion: reduce) {\n  :root { scroll-behavior: auto; --speed: 0s; }\n}\n.card { --bg: #eeeeee; }\n")

    def test_a_block_that_stands_twice_is_named_and_not_read(self):
        # no merging, and no later line taken to win: the intake writes to the first block, a browser shows the last
        whole = self.starter()
        for block, again, holds in (("light", ":root { --accent: #111111; }", "the light theme's colours"), ("light", ":root {\n  --radius: 4px;\n}", "the light theme's colours"),
                                    ("dark", ':root[data-theme="dark"] { --bg: #222222; }', "the dark theme's colours"),
                                    ("dark_media", "@media (prefers-color-scheme: dark) {\n  :root:not([data-theme]) { --bg: #000000; }\n}", "the dark colours for visitors without JavaScript")):
            with self.subTest(again=again):
                css = _palette.read_css(whole + "\n" + again + "\n")
                self.assertEqual(css.found, {"light", "dark", "dark_media"} - {block})
                self.assertEqual({"light": css.light, "dark": css.dark, "dark_media": css.dark_media}[block], {})
                self.assertEqual([(b, v) for b, v, _m in css.problems], [(block, None)])
                for part in ("The stylesheet has 2 blocks", holds, "only where it stands once", "the intake writes to the first", "a browser lets a later one win", "Fold them into one"):
                    self.assertIn(part, css.problems[0][2])
                self.assertIn("a later one sets %s" % ("no colour" if "radius" in again else again.split("{")[-1].split(":")[0].strip()), css.problems[0][2])
                self.assertEqual(_palette.drift(_palette.parse_tables(brand_md()), css), [])
                self.assertEqual(_palette.dark_blocks_disagree(css), [])
        css = _palette.read_css(":root { --bg: #ffffff; }\n" * 3)
        self.assertIn("The stylesheet has 3 blocks", css.problems[0][2])
        # two media blocks for the dark preference, of which one holds the rule, are one block
        self.assert_all_three_blocks(whole.replace("@media (prefers-color-scheme: dark) {", "@media (prefers-color-scheme: dark) {\n  img { opacity: 0.9; }\n}\n@media (prefers-color-scheme: dark) {", 1))

    def test_a_colour_set_twice_in_one_block_has_no_value_and_is_named(self):
        whole = self.starter()
        css = _palette.read_css(whole.replace("  --accent: #2b50e0;", "  --accent: #2b50e0;\n  --accent: oklch(0.5 0.2 265);", 1))
        self.assertEqual(css.found, {"light", "dark", "dark_media"})
        self.assertNotIn("accent", css.light)
        self.assertNotIn("link", css.light, "the link is written as the accent, which has no one value")
        self.assertEqual([(b, v) for b, v, _m in css.problems], [("light", "--accent"), ("light", "--link")])
        for part in ("set 2 times in this block", "#2b50e0", "oklch(0.5 0.2 265)", "does not pick one"):
            self.assertIn(part, css.problems[0][2])
        self.assertIn("var(--accent)", css.problems[1][2])
        self.assertEqual({k: v for k, v in css.light.items()}, {k: v for k, v in STARTER_LIGHT.items() if k not in ("accent", "link")})
        self.assertEqual(_palette.drift(_palette.parse_tables(brand_md()), css), [], "said by the reading, not again as drift")
        # the same line twice is twice all the same; a variable that is no colour may be set as often as it likes
        css = _palette.read_css(whole.replace("  --bg: #ffffff;", "  --bg: #ffffff;\n  --bg: #ffffff;\n  --radius: 4px;", 1))
        self.assertEqual([(b, v) for b, v, _m in css.problems], [("light", "--bg")])

    def test_a_colour_marked_important_has_no_value_and_is_named_whatever_stands_after_it(self):
        # round 2: a later plain line erased the !important one and the word about it, and the check passed on a colour the page does not show
        whole = self.starter()
        for name, text, problems in (("alone", whole.replace("--bg: #ffffff;", "--bg: #ffffff !important;", 1), [("light", "--bg")]),
                                     ("in capitals", whole.replace("--bg: #ffffff;", "--bg: #ffffff ! IMPORTANT ;", 1), [("light", "--bg")]),
                                     ("with a plain line after it", whole.replace("--bg: #ffffff;", "--bg: #000000 !important;\n  --bg: #ffffff;", 1), [("light", "--bg")]),
                                     ("in the media block", whole.replace("    --muted: #a6abce;", "    --muted: #a6abce !important;", 1), [("dark_media", "--muted")])):
            with self.subTest(name=name):
                css = _palette.read_css(text)
                self.assertEqual([(b, v) for b, v, _m in css.problems], problems)
                block, variable = problems[0]
                self.assertNotIn(_palette.KEY_OF_VARIABLE[variable], {"light": css.light, "dark_media": css.dark_media}[block])
                self.assertEqual(_palette.dark_blocks_disagree(css), [])
        css = _palette.read_css(whole.replace("--bg: #ffffff;", "--bg: #ffffff !important;", 1))
        self.assertTrue(css.problems[0][2].startswith("The colour '#ffffff !important' is not one this check can read"), css.problems[0][2])
        self.assertIn("Take the !important off", css.problems[0][2])

    def test_a_block_that_holds_another_block_is_named_and_not_read(self):
        # its own lines used to be lost without a word
        text = self.starter().replace(":root {\n", ':root {\n  &[data-theme="sepia"] { --bg: #f4ecd8; }\n', 1)
        css = _palette.read_css(text)
        self.assertEqual((css.found, css.light), ({"dark", "dark_media"}, {}))
        self.assertEqual([(b, v) for b, v, _m in css.problems], [("light", None)])
        for part in ("The :root block holds another block inside it", '&[data-theme="sepia"]', "plain list of lines", "was not read"):
            self.assertIn(part, css.problems[0][2])

    def test_what_the_reading_takes_the_editor_writes_to_and_the_written_stylesheet_reads_back_as_the_palette(self):
        # through the door the intake uses: edit_css on the same text, then the reading of what it wrote
        whole = self.starter()
        dark_at = whole.index(':root[data-theme="dark"]')
        variants = [whole, '@import url("./fonts.css");\n' + whole, whole.replace(":root {", ":root{", 1), whole.replace(":root {", ":root, html {", 1),
                    whole.replace(":root {", ":ROOT {", 1), whole + "\n:root { --accent: #123456; }\n", whole + '\n:root[data-theme="dark"] { --bg: #222222; }\n',
                    whole.replace("--bg: #ffffff;", "--bg: #ffffff !important;", 1), whole.replace("  --accent: #2b50e0;", "  --accent: #2b50e0;\n  --accent: #111111;", 1),
                    whole.replace(":root {\n", ":root {\n  .x { --bg: #f4ecd8; }\n", 1), "@layer base {\n" + whole[:dark_at] + "}\n" + whole[dark_at:],
                    whole + "@supports (color: red) {\n  :root { --accent: #123456; }\n}\n", whole.replace("@media (prefers-color-scheme: dark) {", "@media(prefers-color-scheme:dark){", 1),
                    whole.replace(':root[data-theme="dark"] {', ":root[data-theme='dark'] {", 1), whole.replace(":root:not([data-theme]) {", ":root {", 1)]
        clean = 0
        for n, text in enumerate(variants):
            with self.subTest(n=n):
                before = _palette.read_css(text)
                if before.problems:
                    continue  # named: the tests above say how
                clean += 1
                self.assertEqual(before.found, {"light", "dark", "dark_media"})
                after = _palette.read_css(_site.edit_css(text, self.bakery()))
                self.assertEqual((after.light, after.dark, after.dark_media, after.brand, after.problems), (T.BAKERY_LIGHT, T.BAKERY_DARK, T.BAKERY_DARK, "#b4531a", []))
        self.assertEqual(clean, 5, "the starter's own spellings, and no other")

    def test_the_shapes_it_reads_are_the_editors_own_patterns(self):
        # if the editor learns another spelling, or forgets one, the reading must follow: this says so
        self.assertEqual("(?m)^" + _palette._EDIT_ROOT.pattern, _site._ROOT.pattern)
        self.assertEqual("(?m)^" + _palette._EDIT_DARK.pattern, _site._DARK.pattern)
        self.assertEqual(_palette._EDIT_MEDIA.pattern, _site._MEDIA.pattern)
        self.assertEqual(_palette._EDIT_MEDIA_ROOT.pattern, _site._MEDIA_ROOT.pattern)

    def test_a_brace_inside_a_string_is_not_a_brace(self):
        for rule in ('a::before { content: "{"; }\n', "a::after { content: '}'; }\n", 'q::before { content: "\\"{"; }\n', 'a[title="{"] { color: red; }\n',
                     '@import "we}ird{.css";\n'):
            with self.subTest(rule=rule):
                self.assert_all_three_blocks(rule + self.starter())
                self.assert_all_three_blocks(self.starter().replace(":root[data-theme", rule + ":root[data-theme", 1))
        css = _palette.read_css(':root { --font: "a{b;c"; --bg: #ffffff; }')
        self.assertEqual(css.light, {"bg": "#ffffff"}, "and the block that holds the string is read to its end")

    def test_a_comment_is_not_text(self):
        comment = "/*\n:root {\n  --bg: #123456;\n}\n:root[data-theme=\"dark\"] {\n  --bg: #654321 !important;\n}\n*/\n"
        self.assert_all_three_blocks(comment + self.starter())
        self.assert_all_three_blocks(self.starter().replace("--bg: #ffffff;", "--bg: #ffffff /* was #fafafa; --bg: #000000 !important */;", 1))
        self.assert_all_three_blocks(self.starter() + "/* never closed: :root { --bg: #000000; }\n")

    def test_braces_that_do_not_pair_up_are_refused_not_read_as_far_as_they_go(self):
        # a } too many ended the :root block early and hid the dark block; nothing said so
        broken = (("a } too many inside the root block", self.starter().replace("--radius: 12px;", "--radius: 12px; }", 1)),
                  ("a } too many at the end", self.starter() + "\n}\n"),
                  ("a { never closed", self.starter()[:self.starter().index("--bg-soft: #11132c;")]),
                  ("a { too many", self.starter().replace(":root {", ":root { {", 1)),
                  ("a string never closed, which runs to the end of its line and takes the } with it", ".a { font-family: 'Inter; }\n" + self.starter()),
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

    def test_a_variable_one_dark_block_has_and_the_other_lacks_is_a_disagreement(self):
        # scenario 29: --surface taken out of the @media block only; both blocks agreed on all they shared
        whole = self.starter()
        media_at = whole.index("@media (prefers-color-scheme: dark)")
        only_media = whole[:media_at] + whole[media_at:].replace("    --surface: #161836;\n", "", 1)
        css = _palette.read_css(only_media)
        self.assertIn("surface", css.dark)
        self.assertNotIn("surface", css.dark_media)
        self.assertEqual(_palette.dark_blocks_disagree(css), [("surface", "#161836", _palette.MISSING)])
        self.assertEqual(_palette.MISSING, "not set in this block", "the value is there in the other block: it is this block that does not set it")
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

    def test_a_stylesheet_value_that_could_not_be_read_is_said_as_that_and_not_as_not_set(self):
        p = _palette.parse_tables(brand_md())
        whole = self.starter()
        css = _palette.read_css(whole.replace("--muted: #5a5a72;", "--muted: rgba(90, 90, 114, 0.8);", 1).replace("--brand: #000000;", "--brand: url(#g);", 1))
        self.assertEqual(sorted((block, variable) for block, variable, _m in css.problems), [("light", "--brand"), ("light", "--muted")])
        self.assertEqual(_palette.drift(p, css), [], "it is there; what it is could not be read, and css.problems says so")
        at = whole.index("@media (prefers-color-scheme: dark)")
        css = _palette.read_css(whole[:at] + whole[at:].replace("--surface: #161836;", "--surface: transparent;", 1))
        self.assertEqual([(block, variable) for block, variable, _m in css.problems], [("dark_media", "--surface")])
        self.assertEqual(_palette.dark_blocks_disagree(css), [])
        # a value written as another variable that is not there, or with a fallback, or as a function of the theme
        for value, part in (("var(--nowhere)", "--nowhere has no one value"), ("var(--accent, #2b50e0)", "is not one this check can read"), ("light-dark(#ffffff, #0a0b1e)", "is not one this check can read")):
            with self.subTest(value=value):
                css = _palette.read_css(whole.replace("--link: var(--accent);", "--link: %s;" % value, 1))
                self.assertEqual([(block, variable) for block, variable, _m in css.problems], [("light", "--link")])
                self.assertIn(part, css.problems[0][2])
                self.assertNotIn("link", css.light)


if __name__ == "__main__":
    unittest.main()
