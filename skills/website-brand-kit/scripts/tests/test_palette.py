"""Scenarios 7, 9, 10 (the palette side), 28: the palette the owner pastes, the rows it must
have, and the contrast check that names a failing pair before anything is written.

`_palette.parse_tables` reads ONE form, the three tables this skill itself writes, by the numbered
rules of its docstring. Each rule has its own class below, named for the rule, and each class tests
both sides of it: what the rule reads, and the near-misses it must not read (and what is said about
them). The three promises above all of them: a value the reader returns is the colour in the second
cell of a row with a known name under one of the three headings; a colour written as a value anywhere
else is named in `problems` (rule 12); and so is the word "proposed" wherever it is not read as a mark
(rule 9).

The matrix is every text colour on every background colour, in both themes. That is wider than
the starter's stylesheet uses today (it styles `--ink` and `--link` on `--bg`, and `--ink` on
`--surface`), on purpose: a stylesheet that starts using `--muted` on `--bg-soft` should not be
the first time anyone checks the pair. A test below holds the matrix to the stylesheet it
protects, so a new pair in the CSS that the matrix lacks fails here.
"""

import os
import re
import sys
import time
import unicodedata
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


def of(palette, code):
    """The messages of the problems with this code."""
    return [m for _t, _k, c, m in palette.problems if c == code]


NOT_READ, MARK = "palette-colour-not-read", "palette-mark-not-read"
LINE_END = "palette-line-end"
# What str.splitlines() ends a line at beside a line feed and a carriage return: a vertical tab, a form feed, U+001C to U+001E, U+0085, U+2028, U+2029
LINE_ENDS = ("\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029")


def brand_md(light=STARTER_LIGHT, dark=STARTER_DARK, primary="#000000", extra=""):
    return (
        "# Example Bakery: brand & style guide\n\n## Colour palette\n\n### Brand (fixed, theme-independent)\n"
        "| Token | Hex | Use |\n|---|---|---|\n| Primary | `%s` | buttons, brand surfaces |\n\n" % primary
        + "### Light theme\n" + table([(l, light[k]) for k, l in LABELS if k in light]) + "\n"
        + "### Dark theme\n" + table([(l, dark[k]) for k, l in LABELS if k in dark]) + extra
    )


def pasted(*args, **kwargs):
    """The same three tables as a tool hands them back: no guide around them and no `## Colour palette` heading, so
    the whole text is the palette (rule 0)."""
    whole = brand_md(*args, **kwargs)
    top = "# Example Bakery: brand & style guide\n\n## Colour palette\n\n"
    assert whole.startswith(top)
    return whole[len(top):]


# Every slot of the suite's BRAND.md template outside its colour tables, and a realistic value for it: a made-up bakery's
# brand guide. Several hold a colour, as the template asks (the logo on dark, the shadow, the share cards).
GUIDE_SLOTS = (
    ("[Site name]", "Example Bakery"),
    ("[Positioning + the visual feel in one sentence: palette mood, one accent,\nwhitespace, shape language. No clichéd stock photography.]",
     "A village bakery that bakes through the night: warm cream and brown, one burnt-orange accent,\ngenerous whitespace, rounded shapes."),
    ("`[path]` ([dimensions])", "`public/images/logo.png` (512 × 512)"), ("[30%]", "30%"), ("[24]", "24"),
    ("On dark backgrounds: [usage].", "On dark backgrounds: the cream version (#fff8ee), never the brown one (#3a1d0a).\n"
                                      "- History: the mark was proposed by the studio in March and confirmed in April."),
    ("[system stack or self-hosted woff2 + fallback]", "Inter, self-hosted woff2, with the system stack as fallback"), ("[700–800]", "700"), ("[≈ −0.02em]", "−0.02em"),
    ("[12]", "12"), ("`[0 8px 24px rgba(...,0.06)]`", "`0 8px 24px rgba(58, 29, 10, 0.06)`"), ("[72rem]", "72rem"),
    ("[background / gradient]", "a gradient from #2a1f17 at the top to #1a120d at the bottom"), ("Logo [position, size]", "Logo top left, 96px"),
    ("Wordmark [text, position, size, colour]", 'Wordmark "Example Bakery", beside the logo, 40px, #fbeedd'),
    ("Headline [text, position, size, colour]", "Headline the page's title, centred, 72px, rgb(226, 135, 74)"), ("Footer URL [text, position]", "Footer URL example.com, bottom left"),
    ("[palette, motifs, real people if used, breathing room; legible in both\n  themes]", "the palette above, loaves and hands, real people, room to breathe; legible in both\n  themes"),
    ('[rainbow palettes, busy gradients, AI "robot/brain" clichés,\n  low-contrast text on images]', "rainbow palettes, busy gradients, the proposed neon green (#39ff14),\n  pale text such as #c4ae98 on photographs"),
)


def filled_guide():
    """The suite's BRAND.md template filled in COMPLETELY, as its opening comment asks: the bakery's palette in the three
    tables, and a value in every other slot."""
    text = T.read(T.BRAND_TEMPLATE)
    for value in ["#b4531a"] + [T.BAKERY_LIGHT[k] for k, _l in LABELS] + [T.BAKERY_DARK[k] for k, _l in LABELS]:
        text = text.replace("`#[…]`", "`%s`" % value, 1)
    for slot, value in GUIDE_SLOTS:
        assert text.count(slot) == 1, slot
        text = text.replace(slot, value)
    comment, _, rest = text.partition("-->")
    left = re.findall(r"\[[^\]\n]*\]", rest)
    assert not left, "the template has a slot this test does not fill: %r" % left
    return text


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
        self.assertEqual((p.missing(), p.problems, p.ignored, p.proposed), ([], [], [], set()))
        self.assertEqual(p.rows_found, 19)

    def test_the_template_as_shipped_is_all_missing_not_an_error(self):
        p = _palette.parse_tables(T.read(T.BRAND_TEMPLATE))
        self.assertEqual(len(p.missing()), 18)
        self.assertIsNone(p.brand)
        self.assertEqual(p.problems, [], "its opening comment and its `rgba(...,0.06)` are no colours and no rows")
        self.assertEqual(p.rows_found, 19, "its rows are found; they are not filled in yet")

    def test_the_template_filled_in_is_the_palette_and_matches_the_starters_stylesheet(self):
        template = T.read(T.BRAND_TEMPLATE)
        self.assertEqual(template.count("`#[…]`"), 19)
        values = ["#000000"] + [STARTER_LIGHT[k] for k, _l in LABELS] + [STARTER_DARK[k] for k, _l in LABELS]
        for value in values:
            template = template.replace("`#[…]`", "`%s`" % value, 1)
        p = _palette.parse_tables(template)
        self.assertEqual((p.light, p.dark, p.brand, p.problems), (STARTER_LIGHT, STARTER_DARK, "#000000", []))
        pairs = _palette.matrix(p)
        self.assertEqual((len(pairs), [x for x in pairs if not x.ok]), (30, []))
        self.assertEqual(_palette.drift(p, _palette.read_css(T.starter_file("src/styles/global.css"))), [])

    def test_the_two_fixtures_the_evals_hand_over(self):
        p = _palette.parse_tables(T.read(os.path.join(EVALS, "pasted-palette.md")))
        self.assertEqual((p.missing(), p.problems, p.brand), ([], [], "#b4531a"))
        bad = [x for x in _palette.matrix(p) if not x.ok]
        self.assertEqual([(x.theme, x.fg, x.bg, _colour.shown(x.ratio)) for x in bad],
                         [("dark", "muted", "bg", "3.58"), ("dark", "muted", "bg_soft", "3.34"), ("dark", "muted", "surface", "3.11")])
        p = _palette.parse_tables(T.read(os.path.join(EVALS, "own-colours.md")))
        self.assertEqual(p.missing(), [("light", "link"), ("light", "bg_soft")] + [("dark", k) for k in _palette.KEYS])
        self.assertEqual((p.problems, p.brand), ([], "#b4531a"))


class Rule0WhereTheCheckLooks(unittest.TestCase):
    """0. Where exactly one heading says `Colour palette`, the palette is the part of the text under that heading, and
    nothing outside it is read or named, but for one of the three headings with a table under it. With no such heading
    the whole text is the palette; with more than one, nothing is read."""

    def bakery(self, p):
        self.assertEqual((p.light, p.dark, p.brand), (T.BAKERY_LIGHT, T.BAKERY_DARK, "#b4531a"))

    def test_a_brand_guide_filled_in_as_its_template_asks_is_read_and_nothing_else_in_it_is_the_palettes_business(self):
        # round 3: a shadow's rgba(), the share cards' colours and the word "proposed" in the logo's history each stopped the check
        text = filled_guide()
        p = _palette.parse_tables(text)
        self.bakery(p)
        self.assertEqual((p.problems, p.missing(), p.proposed, p.ignored, p.rows_found), ([], [], set(), [], 19))
        pairs = _palette.matrix(p)
        self.assertEqual((len(pairs), [x for x in pairs if not x.ok]), (30, []))
        # the guide does hold what the two rules for the whole text would name, outside its palette: seven lines with a colour, two with the word
        outside = text.replace("## Colour palette", "## Colours")
        self.assertNotEqual(outside, text)
        unscoped = _palette.parse_tables(outside)
        self.assertEqual(([len(of(unscoped, code)) for code in (NOT_READ, MARK)]), [6, 2], "with no such heading every line of it is the palette's business")
        self.assertEqual(of(unscoped, NOT_READ)[5], "2 more lines hold a colour that was not read; the next is line 121.")
        self.assertIn("rgba(58, 29, 10, 0.06)", said(unscoped))
        self.assertIn('holds the word "proposed"', said(unscoped))

    def test_inside_the_section_every_rule_holds_as_in_a_pasted_answer_and_lines_keep_the_numbers_they_have_in_the_file(self):
        text = filled_guide()
        at = text.index("### Light theme")
        inside = text[:at] + "Our ink is #3a2a1e, and the dark theme is still a proposal.\n\n" + text[at:]
        p = _palette.parse_tables(inside)
        self.bakery(p)
        self.assertEqual([c for _t, _k, c in codes(p)], [MARK, NOT_READ])
        number = inside.splitlines().index("Our ink is #3a2a1e, and the dark theme is still a proposal.") + 1
        self.assertGreater(number, 30)
        for message in (p.problems[0][3], p.problems[1][3]):
            self.assertIn('Line %d, "Our ink is #3a2a1e, and the dark theme is still a proposal."' % number, message)
        p = _palette.parse_tables(text.replace("| Muted | `#6b5744` |", "| Muted | `#6b5744` (proposed) |"))
        self.assertEqual((p.proposed, p.problems), ({("light", "muted")}, []))

    def test_where_the_section_begins_and_ends(self):
        tables = pasted(T.BAKERY_LIGHT, T.BAKERY_DARK, "#b4531a")
        noise = "Our old ink was #111111, and a new one is proposed.\n\n| Muted | #777777 |\n"
        # the heading in every spelling the rule takes, at any level; the section ends at a heading of its level or a higher one
        for heading, after in (("## Colour palette", "## Typography"), ("## Color palette", "# Appendix"), ("# COLOUR PALETTE", "# Type"), ("#### **Colour palette**", "## Type"),
                               ("## `Colour   palette` ##", "## Type"), ("### Colour pal*ette", "### Type"), ("## _Colour_ pal_ette_", "# Type"), ("  ## Colour palette", "## Type")):
            with self.subTest(heading=heading):
                level = len(heading.strip()) - len(heading.strip().lstrip("#"))
                deeper = "#" * (level + 1) + " Notes\n\nThe accent may change.\n\n"   # a deeper heading does not end the section
                text = "# Our guide\n\n" + noise + "\n" + heading + "\n\n" + deeper + tables.replace("### ", "#" * (level + 2) + " ") + "\n" + after + "\n\n" + noise
                p = _palette.parse_tables(text)
                self.bakery(p)
                self.assertEqual(p.problems, [], "what stands before the section and after it is not read and not named")
        # what is no such heading: the whole text is then the palette, as for a pasted answer
        for line in ("## Colour palette (draft)", "## Our colour palette", "## Colour palettes", "## Palette", "Colour palette", "**Colour palette**", "<!-- ## Colour palette -->",
                     "## Colour palette:", "## Colour-palette", "## Colour palette" + " x" * 1000, "###Colour palette", "####### Colour palette", "#Colour palette"):
            with self.subTest(line=line[:30]):
                p = _palette.parse_tables(noise + "\n" + line + "\n\n" + tables)
                self.bakery(p)
                self.assertEqual([c for _t, _k, c in codes(p)], ["palette-no-section", MARK, NOT_READ], "the table, the word and the colour of the lines above are all named")
        # a section with no heading after it runs to the end of the text; an empty one holds nothing
        p = _palette.parse_tables("## Colour palette\n" + tables + "\nA last line with #123456.\n")
        self.assertEqual([c for _t, _k, c in codes(p)], [NOT_READ])
        p = _palette.parse_tables("## Colour palette\n## Type\n" + noise)
        self.assertEqual((p.rows_found, p.problems, len(p.missing())), (0, [], 18))

    def test_the_three_tables_outside_the_section_are_named_and_not_read(self):
        text = filled_guide()
        start, end = text.index("### Brand (fixed"), text.index("## Typography")
        moved = text[:start] + text[end:] + "\n## Appendix\n\n" + text[start:end]
        p = _palette.parse_tables(moved)
        self.assertEqual((p.light, p.dark, p.brand, p.rows_found), ({}, {}, None, 0), "a palette in the wrong place of the file is not read")
        self.assertEqual(codes(p), [("?", None, "palette-outside-section")] * 3, "and it is not silently not there")
        lines_ = moved.splitlines()
        first, last = lines_.index("## Colour palette") + 1, lines_.index("## Typography")
        for message, heading in zip(of(p, "palette-outside-section"), ("### Brand (fixed, theme-independent)", "### Light theme", "### Dark theme")):
            for part in ('Line %d, the heading "%s", has a table under it' % (lines_.index(heading) + 1, heading), "stands outside the part of this text that the check reads",
                         'the part under the heading "## Colour palette" (lines %d to %d)' % (first, last), "that table was not read", "Move the heading and its table into that part"):
                self.assertIn(part, message)
        # one table left behind is named, and the two in the section are read
        start = text.index("### Dark theme")
        p = _palette.parse_tables(text[:start] + text[end:] + "\n## Appendix\n\n" + text[start:end])
        self.assertEqual((p.light, p.dark, p.brand, [c for _t, _k, c in codes(p)]), (T.BAKERY_LIGHT, {}, "#b4531a", ["palette-outside-section"]))
        # the near-misses: one of the three headings outside the section with no table under it is only a heading (a guide
        # titled "# Brand"), and a table outside under any other heading is not the palette's business
        for outside in ("# Brand\n\nWho we are.\n\n", "## Light theme\n\nUsed by day: see below.\n\n## Type\n| Muted | #777777 |\n\n", "## Notes\n" + HEAD + "| Muted | #777777 (proposed) |\n\n",
                        "## Dark theme\n- Muted: #777777\n\n", "### Brand\n\n### Other\n| Primary | #123456 |\n\n"):
            with self.subTest(outside=outside[:20]):
                p = _palette.parse_tables(outside + text)
                self.bakery(p)
                self.assertEqual(p.problems, [])
        p = _palette.parse_tables("".join("### Dark theme\n| Muted | #77777%d |\n\n" % n for n in range(8)) + text)
        self.assertEqual(len(of(p, "palette-outside-section")), 6)
        self.assertEqual(of(p, "palette-outside-section")[5], "3 more headings with a table under them stand outside that part; the next is on line 16.")

    def test_the_heading_twice_is_named_and_nothing_is_read(self):
        text = filled_guide()
        for name, twice, numbers in (("a second one further down", text + "\n## Colour palette\n\nSee above.\n", "lines 23 and 124"),
                                     # round 4: a quick test on the line as written let a heading with emphasis inside a word through as no heading
                                     ("a second one with emphasis inside a word", text + "\n## Colour pal*ette\n\nSee above.\n", "lines 23 and 124"),
                                     ("a second one with emphasis inside both words", "#### C_olour_ `pal`ette\n\n" + text, "lines 1 and 25"),
                                     ("two palettes pasted one after the other", ("## Colour palette\n" + pasted()) * 2, "lines 1 and 32"),
                                     ("a second one at another level", "# Color palette\n\n" + text, "lines 1 and 25")):
            with self.subTest(name=name):
                p = _palette.parse_tables(twice)
                self.assertEqual((p.light, p.dark, p.brand, p.rows_found, p.proposed), ({}, {}, None, 0, set()))
                self.assertEqual(codes(p), [("?", None, "palette-section-twice")])
                for part in ("stands 2 times in this text (on %s)" % numbers, "cannot tell which of them holds it", "it read nothing", "Leave that heading once, above the three tables"):
                    self.assertIn(part, p.problems[0][3])
        p = _palette.parse_tables("## Colour palette\n" * 9)
        self.assertIn("stands 9 times in this text (on lines 1, 2, 3, 4 and 5 and further down)", p.problems[0][3])

    def test_a_pasted_answer_with_and_without_the_heading(self):
        tables = pasted()
        # without it the whole answer is the palette: an opening sentence with the word is named, and the check does not pass
        p = _palette.parse_tables("Here are three proposed palettes.\n\n" + tables)
        self.assertEqual((p.light, p.dark, p.brand, [c for _t, _k, c in codes(p)]), (STARTER_LIGHT, STARTER_DARK, "#000000", [MARK]))
        # with its own heading above the three tables it is read like a brand guide: the sentence above the heading stands outside
        # the section and is not named, and the values, which carry no mark, are read as they are. Intended (see rule 0): what
        # makes a value a proposal is a mark on its row or on its section's heading, and those are inside the section.
        p = _palette.parse_tables("Here are three proposed palettes.\n\n## Colour palette\n\n" + tables)
        self.assertEqual((p.light, p.dark, p.brand, p.proposed, p.problems), (STARTER_LIGHT, STARTER_DARK, "#000000", set(), []))
        # the same sentence under that heading, a mark on a row and a mark on a section's heading are all inside, and none passes
        p = _palette.parse_tables("## Colour palette\n\nHere are three proposed palettes.\n\n" + tables)
        self.assertEqual([c for _t, _k, c in codes(p)], [MARK])
        p = _palette.parse_tables("Here you are.\n\n## Colour palette\n\n" + pasted(dark=dict(STARTER_DARK, muted="#a6abce (proposed)")))
        self.assertEqual((p.proposed, p.problems), ({("dark", "muted")}, []))
        p = _palette.parse_tables("## Colour palette\n\n" + tables.replace("### Dark theme", "### Dark theme (proposed)"))
        self.assertEqual((p.proposed, p.problems), ({("dark", k) for k in STARTER_DARK}, []))

    def test_a_comment_that_never_closes_is_named_where_it_hides_a_part_of_the_palette(self):
        text = "## Colour palette\n" + pasted() + "\n## Notes\n\n"
        self.assertEqual(_palette.parse_tables(text + "<!-- to do\nmore\n").problems, [], "after the section it hides nothing of the palette")
        p = _palette.parse_tables(text.replace("### Dark theme", "<!-- later\n### Dark theme"))
        self.assertEqual((p.dark, [c for _t, _k, c in codes(p)]), ({}, ["palette-comment-open"]), "inside the section it hides the dark theme, and the heading that would end the section")
        p = _palette.parse_tables("<!-- draft\n" + text)
        self.assertEqual((p.rows_found, [c for _t, _k, c in codes(p)]), (0, ["palette-comment-open"]), "before it, it hides the section's heading too: the whole text is then a comment")

    def test_no_megabyte_with_the_heading_in_it_makes_the_reading_slow(self):
        head = "## Colour palette\n" + pasted()
        for name, text in (("a megabyte of headings after the section", head + "## Type\n" * 131000), ("a megabyte of deeper headings in the section", head + "### Type\n" * 116000),
                           ("a megabyte of palette headings", "## Colour palette\n" * 58000), ("a megabyte of tables outside under one of the three headings", head + "## x\n" + "### Dark theme\n|Muted|#777|\n" * 37000),
                           ("a megabyte of lines before the section", "Our ink is #111111, as proposed.\n" * 31000 + head)):
            with self.subTest(name=name):
                start = time.process_time()
                _palette.parse_tables(text)
                self.assertLess(time.process_time() - start, 6.0)


    def test_a_line_that_starts_with_a_hash_and_is_no_heading_ends_no_section_and_is_read_as_text(self):
        # round 4: any line that began with # ended the part under `Colour palette`, so `#1: the dark values are still proposed`
        # after three good tables was neither read nor named, and the check ended with 0
        guide = "# Our guide\n\n## Colour palette\n\n" + pasted()
        # (round 8: U+001F after the # is no blank, so the line is text; it is quoted with the character shown)
        for line in ("#1: the dark values are still proposed", "#proposed", "#16162a is the ink; the rest is proposed", "#Brand (proposed)", "####### proposed", "##proposed",
                     "#\x1fthe dark values are proposed", "##\x1fproposed"):
            with self.subTest(line=line):
                p = _palette.parse_tables(guide + "\n" + line + "\n\nA last word: #123456 is proposed too.\n")
                self.bakery_starter(p)
                self.assertEqual(len(of(p, MARK)), 2, "the line is text of the section, and so is the line after it")
                self.assertIn('Line 36, "%s", holds the word "proposed"' % line.replace("\x1f", "<U+001F>"), of(p, MARK)[0])
                self.assertIn("Line 38,", of(p, MARK)[1])
                self.assertEqual(len(of(p, NOT_READ)), 2 if line.startswith("#16162a") else 1)
        # the near-miss: a heading of the section's level ends it, with a blank after its # or nothing at all, up to six of them
        # (a blank is what rule 1 makes one space of: a space, a tab, and what else a person sees as a space. Round 8: a no-break space
        # after the # is typed with Option+Space and came back to this side, where round 4 had it)
        for line in ("# 1: the dark values are still proposed", "## proposed", "##", "#\tproposed", "# \t the dark values are proposed",
                     "#\u00a0the dark values are proposed", "##\u2003proposed", "##\u3000proposed", "## \u00a0\tproposed", "##\u00a0"):
            with self.subTest(line=line):
                p = _palette.parse_tables(guide + "\n" + line + "\n\nA last word: #123456 is proposed too.\n")
                self.bakery_starter(p)
                self.assertEqual(p.problems, [])
        # and inside the section a deeper line of that kind ends no table's section either: the table after it is named as rule 3 has it
        p = _palette.parse_tables("### Light theme\n" + HEAD + "| Heading | #16162a |\n#notes\n" + HEAD + "| Muted | #5a5a72 |\n")
        self.assertEqual((p.light, [c for _t, _k, c in codes(p)]), ({"heading": "#16162a"}, ["palette-no-section"]))
        self.assertIn('after the line "#notes", further down under `### Light theme`', p.problems[0][3])

    def bakery_starter(self, p):
        self.assertEqual((p.light, p.dark, p.brand), (STARTER_LIGHT, STARTER_DARK, "#000000"))

    def test_no_line_inside_a_fenced_code_block_is_a_heading(self):
        # round 5: a `# comment` in a code sample was a level-1 heading and ended the palette's part; a sentence with the word
        # after the sample was then outside it, named by nothing, and the check ended with 0
        for fence, close in (("```", "```"), ("```css", "```"), ("~~~", "~~~"), ("````", "`````"), ("~~~ sh", "~~~~"), ("  ```", "```  ")):
            with self.subTest(fence=fence):
                md = "# Guide\n\n## Colour palette\n\n" + pasted() + "\n%s\n# a comment in the sample\n## Colour palette\n%s\n\nThe dark values are proposed.\n\n## Type\n\nproposed\n" % (fence, close)
                p = _palette.parse_tables(md)
                self.assertEqual((p.light, p.dark, p.brand), (STARTER_LIGHT, STARTER_DARK, "#000000"))
                self.assertEqual([c for _t, _k, c in codes(p)], [MARK], "the sample ends no part and names no second one; the sentence after it is inside, and named")
                self.assertIn('Line 41, "The dark values are proposed."', p.problems[0][3])
        # a fence that is never closed runs to the end of the text, so the heading after it ends nothing either
        p = _palette.parse_tables("## Colour palette\n\n" + pasted() + "\n```\n# x\n\n## Type\n\nBody text #333333.\n")
        self.assertEqual([c for _t, _k, c in codes(p)], [NOT_READ])
        # one of the three headings inside a fence is no heading either: its table stands under none, and the problem says what to do
        for fence in ("```", "```markdown", "~~~"):
            with self.subTest(fence=fence):
                p = _palette.parse_tables(fence + "\n" + pasted() + fence[:3] + "\n")
                self.assertEqual((p.light, p.dark, p.brand, p.rows_found), ({}, {}, None, 0))
                self.assertEqual([c for _t, _k, c in codes(p)], ["palette-no-section"] * 3)
                for part in ('stands under the line "### Brand (fixed, theme-independent)", which stands inside a code block (between two lines of ``` or ~~~), where this check takes no '
                             "line for a heading", "Take the two lines that open and close the code block out, so that the headings inside it count."):
                    self.assertIn(part, p.problems[0][3])
                self.assertNotIn("a heading is one to six #", p.problems[0][3])
                # followed, it ends the matter
                self.assertEqual(_palette.parse_tables(pasted()).problems, [])
        # round 6: only the line that OPENS the block was copied with the palette. The sentence says what is there, one line and
        # its number, where it said "the two lines" before
        for fence in ("```", "```markdown", "~~~~"):
            with self.subTest(fence=fence, closed=False):
                p = _palette.parse_tables("Here it is:\n\n" + fence + "\n" + pasted())
                self.assertEqual((p.light, p.dark, p.brand, p.rows_found), ({}, {}, None, 0))
                self.assertEqual([c for _t, _k, c in codes(p)], ["palette-no-section"] * 3)
                for part in ('stands under the line "### Brand (fixed, theme-independent)", which stands inside a code block (line 3 opens one with ``` or ~~~, and no line after it '
                             "closes it), where this check takes no line for a heading", "Take line 3, which opens the code block, out, so that the headings after it count."):
                    self.assertIn(part, p.problems[0][3])
                self.assertNotIn("two lines", said(p))
                self.assertEqual(_palette.parse_tables("Here it is:\n\n" + pasted()).problems, [], "followed, it ends the matter")
        # a block that is closed and, further down, one that is not: each table is told of its own
        text = "```\n### Light theme\n" + plain(STARTER_LIGHT) + "```\n\n~~~\n### Dark theme\n" + plain(STARTER_DARK)
        first, second = of(_palette.parse_tables(text), "palette-no-section")
        self.assertIn("(between two lines of ``` or ~~~)", first)
        self.assertIn("Take the two lines that open and close the code block out", first)
        opens = text.splitlines().index("~~~") + 1
        self.assertIn("(line %d opens one with ``` or ~~~, and no line after it closes it)" % opens, second)
        self.assertIn("Take line %d, which opens the code block, out" % opens, second)
        # round 7 (R7-209): a heading that counts stands ABOVE the block (`### Brand` and its table, then the two themes pasted with their
        # fence). The sentence said the theme's heading "is not a heading" and never named the code block.
        brand, themes = "### Brand\n" + HEAD + "| Primary | #000000 |\n\n", "### Light theme\n" + plain(STARTER_LIGHT) + "\n### Dark theme\n" + plain(STARTER_DARK)
        for name, text, where, do in (
                ("closed", brand + "```markdown\n" + themes + "```\n", "(between two lines of ``` or ~~~)", "Take the two lines that open and close the code block out, so that the headings inside it count."),
                ("never closed", brand + "~~~\n" + themes, "(line 6 opens one with ``` or ~~~, and no line after it closes it)", "Take line 6, which opens the code block, out, so that the headings after it count.")):
            with self.subTest(name=name):
                p = _palette.parse_tables(text)
                self.assertEqual((p.light, p.dark, p.brand, [c for _t, _k, c in codes(p)]), ({}, {}, "#000000", ["palette-no-section"] * 2))
                for message, heading in zip(of(p, "palette-no-section"), ("### Light theme", "### Dark theme")):
                    for part in ('stands under the line "%s", which stands inside a code block %s, where this check takes no line for a heading' % (heading, where), do):
                        self.assertIn(part, message)
                    for part in ("is not a heading", "further down under `### Brand`", "does not guess whether it was meant as one"):
                        self.assertNotIn(part, message)
                self.assertEqual(_palette.parse_tables(brand + themes).problems, [], "followed, it ends the matter")
        # the near-miss: a line of text above the second table, in no code block, is told what it was told before
        p = _palette.parse_tables(brand + "Light theme\n" + plain(STARTER_LIGHT))
        for part in ('stands after the line "Light theme", further down under `### Brand`', "A line of text is not a heading, and this check does not guess whether it was meant as one."):
            self.assertIn(part, of(p, "palette-no-section")[0])
        # a marked heading inside a fence marks nothing, and is named for its word
        p = _palette.parse_tables(pasted() + "\n```\n### Dark theme (proposed)\n```\n")
        self.assertEqual((p.proposed, [c for _t, _k, c in codes(p)]), (set(), [MARK]))
        # the near-misses: three backticks in the middle of a line, a line of code between single backticks, and fewer than three
        for line in ("Use ``` to open a sample.", "```#16162a``` is the ink", "``", "~~ struck ~~", "`# not a fence`"):
            with self.subTest(line=line):
                p = _palette.parse_tables("## Colour palette\n\n" + pasted() + "\n%s\n\n## Type\n\nBody text #333333, proposed.\n\n%s\n" % (line, line))
                self.assertEqual((p.light, [c for _t, _k, c in codes(p)]), (STARTER_LIGHT, [NOT_READ] * ("#16162a" in line)), "the next heading still ends the part")

    def test_the_three_headings_with_as_many_hashes_as_the_palette_heading_are_told_that_and_not_to_move(self):
        # round 4: `### Colour palette` and then `### Brand`: "Move the heading and its table into that part" cannot be followed
        tables = pasted()
        for palette, three, example in (("### Colour palette", "###", "`#### Brand` under `### Colour palette`"), ("### Colour palette", "##", "`#### Brand` under `### Colour palette`"),
                                        ("# Colour palette", "#", "`## Brand` under `# Colour palette`"), ("###### Colour palette", "######", "`###### Brand` under `##### Colour palette`")):
            with self.subTest(palette=palette, three=three):
                text = "# Our guide\n\n" + palette + "\n\n" + tables.replace("### ", three + " ") + "\n## Type\n"
                p = _palette.parse_tables(text)
                self.assertEqual((p.light, p.dark, p.brand, p.rows_found), ({}, {}, None, 0))
                self.assertEqual(codes(p), [("?", None, "palette-outside-section")] * 3)
                first = of(p, "palette-outside-section")[0]
                for part in ('Line 5, the heading "%s Brand (fixed, theme-independent)", has a table under it' % three, 'begins at the heading "%s" (line 3)' % palette,
                             "ends at the next heading that has as many # as that one, or fewer: this heading", "that table was not read",
                             "Give the three headings with the tables more # than the `Colour palette` heading has (%s)" % example):
                    self.assertIn(part, first)
                self.assertNotIn("Move the heading", first)
                for message in of(p, "palette-outside-section")[1:]:
                    self.assertIn('or fewer: line 5, "%s Brand (fixed, theme-independent)"' % three, message)
        # only the last of the three is written too high: the two before it are read, and it is told the same
        p = _palette.parse_tables("## Colour palette\n\n" + tables.replace("### Dark theme", "## Dark theme"))
        self.assertEqual((p.light, p.dark, p.brand, [c for _t, _k, c in codes(p)]), (STARTER_LIGHT, {}, "#000000", ["palette-outside-section"]))
        self.assertIn("or fewer: this heading", p.problems[0][3])
        # the near-miss: where the part ended at another heading, a table further down is still told to move (the test above)
        p = _palette.parse_tables("### Colour palette\n\n### Type\n\n### Dark theme\n" + plain(STARTER_DARK))
        self.assertIn("Move the heading and its table into that part", p.problems[0][3])

class Rule1Lines(unittest.TestCase):
    """1. A byte-order mark at the start is dropped and every HTML comment is blanked, before anything else.
    Runs of blanks (what a person sees as a space) are made one space; a table row longer than 2,000 characters
    is not read, and a problem names it."""

    def test_a_byte_order_mark_before_the_first_heading_does_not_hide_it(self):
        # round 3: the table under the first heading was lost, and the rows were said to be not filled in
        p = _palette.parse_tables("\ufeff" + brand_md().partition("### Brand")[1] + brand_md().partition("### Brand")[2])
        self.assertEqual((p.brand, p.light, p.dark, p.problems), ("#000000", STARTER_LIGHT, STARTER_DARK, []))
        # only at the very start: one further in is a character of the line it stands on, and is shown as one
        p = _palette.parse_tables("### Light theme\n" + HEAD + "| Muted | \ufeff#5a5a72 |\n")
        self.assertEqual((p.light, codes(p)), ({}, [("light", "muted", "palette-not-one-colour")]))
        self.assertIn('"<U+FEFF>#5a5a72"', said(p))

    def test_nothing_inside_a_comment_is_read_and_nothing_inside_one_is_named(self):
        # round 3: rows inside <!-- ... --> filled the gaps of the palette under them
        hidden = "<!--\n### Light theme\n| Token | Hex |\n|---|---|\n| Link | #000000 |\n| Soft background | #ffffff |\n-->\n"
        p = _palette.parse_tables(hidden + T.read(os.path.join(EVALS, "own-colours.md")))
        self.assertEqual((p.missing()[:2], p.problems), ([("light", "link"), ("light", "bg_soft")], []))
        for name, comment in (("a colour", "<!-- was #123456 -->"), ("the word", "<!-- proposed by the designer -->"), ("another section's name", "<!-- Dark theme -->"),
                              ("a row", "<!-- | Muted | #777777 | -->"), ("over several lines", "<!--\n### Dark theme\n| Muted | #777777 (proposed) |\n-->"),
                              ("the shortest comments", "<!--> <!--->"), ("two on a line", "<!-- #111111 --> <!-- #222222 -->")):
            with self.subTest(name=name):
                p = _palette.parse_tables("### Light theme\n%s\n" % comment + plain(STARTER_LIGHT) + comment + "\n")
                self.assertEqual((p.light, p.dark, p.proposed, p.problems), (STARTER_LIGHT, {}, set(), []))
        # a comment between two tables is no line of text: the second table carries on the first
        p = _palette.parse_tables("### Light theme\n" + HEAD + "| Heading | #16162a |\n<!-- backgrounds -->\n" + HEAD + "| Background | #ffffff |\n")
        self.assertEqual((p.light, p.problems), ({"heading": "#16162a", "bg": "#ffffff"}, []))
        # the near-miss: what only looks like a comment is text, and what stands after a comment on its line is read
        p = _palette.parse_tables("### Light theme\n<!- was #123456 ->\n" + plain(STARTER_LIGHT) + "<!-- a --> Our ink is #16162a.\n")
        self.assertEqual([c for _t, _k, c in codes(p)], [NOT_READ, NOT_READ])
        self.assertIn("Line 2,", p.problems[0][3])
        self.assertIn("Line 14,", p.problems[1][3], "a blanked comment keeps its line breaks, so every line keeps its number")

    def test_a_comment_ends_where_a_browser_ends_it_also_at_dash_dash_bang(self):
        # FFR-3: a comment ended only at `-->`, but a browser ends one at `--!>` too, so a row between `--!>` and the next
        # `-->` was blanked here while the page showed it.
        p = _palette.parse_tables("### Light theme\n<!-- note --!>\n" + plain(STARTER_LIGHT) + "<!-- later -->\n")
        self.assertEqual((p.light, p.problems), (STARTER_LIGHT, []))
        # and what is not an end stays inside: `<!--!>` and `<!---!>` open a comment that runs on to its real end
        for opening in ("<!--!>", "<!---!>"):
            with self.subTest(opening=opening):
                p = _palette.parse_tables("### Light theme\n%s | Muted | #777777 |\n-->\n" % opening + plain(STARTER_LIGHT))
                self.assertEqual((p.light, p.problems), (STARTER_LIGHT, []))
        # `<!----!>` is a whole comment to a browser
        p = _palette.parse_tables("### Light theme\n<!----!>\n" + plain(STARTER_LIGHT))
        self.assertEqual((p.light, p.problems), (STARTER_LIGHT, []))

    def test_a_comment_that_is_never_closed_runs_to_the_end_and_is_named(self):
        p = _palette.parse_tables("### Light theme\n" + plain(STARTER_LIGHT) + "\n<!-- the dark theme, later\n### Dark theme\n" + plain(STARTER_DARK))
        self.assertEqual((p.light, p.dark), (STARTER_LIGHT, {}))
        self.assertEqual(codes(p), [("?", None, "palette-comment-open")])
        for part in ("Line 14 opens a comment with `<!--`", "never closed with `-->`", "everything after it", "was not read"):
            self.assertIn(part, p.problems[0][3])

    def timed(self, md, limit=1.0):
        # the time this process spent, not the clock on the wall: a busy machine must not fail this, a slow pattern must
        start = time.process_time()
        try:
            p = _palette.parse_tables(md)
        except Refusal:
            p = None
        took = time.process_time() - start
        self.assertLess(took, limit, "reading took %.2f s of processor time" % took)
        return p

    def test_a_long_run_of_spaces_or_tabs_anywhere_in_a_row_is_one_space(self):
        gap = " " * 40000
        md = "###%sLight   theme\n%s|%sMuted%s|%s`#5a5a72`\t\t(proposed)%s|%sa   note%s|\n" % (gap, HEAD, gap, gap, gap, gap, gap, gap)
        p = self.timed(md)
        self.assertEqual((p.light, p.proposed, p.problems), ({"muted": "#5a5a72"}, {("light", "muted")}, []))

    def test_what_a_person_sees_as_a_space_is_a_blank_of_a_line_and_a_character_nobody_sees_is_none(self):
        # Round 7 (R7-201): the blanks of a line were folded with Python's split(), which also takes U+001F for one, a character nobody sees: `pro`
        # + U+001F + `posed` was two words, and the check ended with 0. Round 7 then folded a space and a tab only, and round 8 (R8-201) found
        # what that cost: a no-break space (Option+Space on a Mac keyboard, or pasted from a web page or a chat) after a heading's #, before a
        # row's first | or inside a value made the line text or the value unreadable. INVARIANT: what a person sees as a space is a blank (the
        # space, the tab, Unicode's category Zs), and what nobody sees is none, so it is still in the line for rule 9's one cleaning pass.
        spaces = [chr(c) for c in range(sys.maxunicode + 1) if unicodedata.category(chr(c)) == "Zs"]
        self.assertEqual(len(spaces), 17, "the same on the Unicode tables of every Python this runs on")
        for c in ("\u00a0", "\u2003", "\u2009", "\u202f", "\u3000"):
            self.assertIn(c, spaces)
        self.assertEqual([chr(c) for c in range(sys.maxunicode + 1) if _palette._BLANKS.fullmatch(chr(c))], ["\t"] + spaces, "the tab, that category, and no other character")
        dark = "### Dark theme\n" + plain(STARTER_DARK)
        for c in spaces + ["\t"]:
            for name, text, proposed in (
                    ("after the # of a heading, and before it", "###%sLight theme\n" % c + plain(STARTER_LIGHT) + "\n%s###%sDark theme%s\n" % (c, c, c) + plain(STARTER_DARK), set()),
                    ("two of them, and one beside a space", "###%s%sLight theme\n" % (c, c) + plain(STARTER_LIGHT) + "\n### %sDark theme\n" % c + plain(STARTER_DARK), set()),
                    ("before the first | of a row, and after its last", "### Light theme\n" + HEAD + "\n".join(c + line + c for line in lines(STARTER_LIGHT)) + "\n\n" + dark, set()),
                    ("inside a value", "### Light theme\n" + plain(STARTER_LIGHT, bg="rgb(255,%s255,%s%s255)" % (c, c, c), bg_soft="rgb(245%s247%s251)" % (c, c)) + "\n" + dark, set()),
                    ("between a value and its mark", "### Light theme\n" + plain(STARTER_LIGHT, muted="#5a5a72%sproposed" % c, link="`#2b50e0`%s(proposed)" % c) + "\n" + dark,
                     {("light", "muted"), ("light", "link")}),
                    ("in a row's name and in a heading's", "### Light%stheme\n" % c + plain(STARTER_LIGHT).replace("Soft background", "Soft%sbackground" % c) + "\n" + dark, set()),
                    ("a line that holds nothing else, between two tables of a section", "### Light theme\n" + HEAD + "\n".join(lines(STARTER_LIGHT)[:4]) + "\n" + c + "\n"
                     + "\n".join(lines(STARTER_LIGHT)[4:]) + "\n\n" + dark, set())):
                with self.subTest(c="U+%04X" % ord(c), name=name):
                    p, same = _palette.parse_tables(text), _palette.parse_tables(text.replace(c, " "))
                    self.assertEqual((p.light, p.dark, p.proposed, p.problems), (STARTER_LIGHT, STARTER_DARK, proposed, []))
                    self.assertEqual((p.light, p.dark, p.proposed, p.problems, p.rows_found), (same.light, same.dark, same.proposed, same.problems, same.rows_found),
                                     "read as the same text with a plain space there")
        # the heading that says where the palette is, in the suite's own template filled in: read as with a plain space, and nothing outside it is named
        guide = filled_guide()
        for c in ("\u00a0", "\u3000", "\u2009"):
            with self.subTest(c="U+%04X" % ord(c), name="the template's `## Colour palette`"):
                typed = guide.replace("## Colour palette", "##%sColour%spalette" % (c, c))
                self.assertNotEqual(typed, guide)
                p = _palette.parse_tables(typed)
                self.assertEqual((p.brand, p.light, p.dark, p.proposed, p.problems), ("#b4531a", T.BAKERY_LIGHT, T.BAKERY_DARK, set(), []))
        # WHAT NOBODY SEES IS NO BLANK. U+001F and a zero-width space stay in their line: after the # they make it text, before a | no row, and
        # each is shown in the quote
        for c in ("\x1f", "\u200b", "\u2060", "\u00ad"):
            with self.subTest(c="U+%04X" % ord(c)):
                self.assertIsNone(_palette._BLANKS.search(c))
                p = _palette.parse_tables("###%sLight theme\n" % c + plain(STARTER_LIGHT))
                self.assertEqual((p.light, [k for _t, _k, k in codes(p)]), ({}, ["palette-no-section"]))
                self.assertIn('stands under the line "###<U+%04X>Light theme", which is not a heading' % ord(c), p.problems[0][3])
                p = _palette.parse_tables("### Light theme\n" + HEAD + c + "| Muted | #5a5a72 |\n")
                self.assertEqual((p.light, [k for _t, _k, k in codes(p)]), ({}, [NOT_READ]), "a line with that character before its first | is no row of a table")
                self.assertIn('Line 4, "<U+%04X>| Muted | #5a5a72 |", holds a colour (#5a5a72) that was not read' % ord(c), p.problems[0][3])
                p = _palette.parse_tables(one("#5a5a72%sproposed" % c))
                self.assertEqual((p.light, [k for _t, _k, k in codes(p)]), ({}, ["palette-not-one-colour"]), "and between a value and its mark it is no blank: never a colour taken as confirmed")
        # the characters that end a line to this reader are no blanks either. (Round 9: a text that holds one is not read at all, rule 9:
        # until then the heading ended at the character, and the table under it was named as standing under no heading.)
        for c in LINE_ENDS:
            with self.subTest(c="U+%04X" % ord(c)):
                self.assertIsNone(_palette._BLANKS.search(c))
                p = _palette.parse_tables("###%sLight theme\n" % c + plain(STARTER_LIGHT))
                self.assertEqual((p.light, codes(p)), ({}, [("?", None, LINE_END)]))
                self.assertIn('Line 1, "###<U+%04X>Light theme", holds a character that this check takes for the end of a line' % ord(c), p.problems[0][3])
        # R7-201 stays mended: the word with U+001F inside it is the word (rule 9), in a sentence and in a note cell, and so is a theme's
        p = _palette.parse_tables("### Light theme\n" + plain(STARTER_LIGHT) + "\nAll of these are pro\x1fposed.\n")
        self.assertEqual([k for _t, _k, k in codes(p)], [MARK])
        self.assertIn('"All of these are pro<U+001F>posed.", holds the word "proposed"', p.problems[0][3])
        p = _palette.parse_tables("### Light theme\n" + HEAD + "| Muted | #5a5a72 | pro\x1fposed |\n")
        self.assertEqual((p.light, p.proposed, p.problems), ({"muted": "#5a5a72"}, {("light", "muted")}, []))
        p = _palette.parse_tables("### Light theme\nDar\x1fk\n" + plain(STARTER_DARK))
        self.assertEqual((p.light, [k for _t, _k, k in codes(p)]), ({}, ["palette-label"]))
        self.assertIn('"Dar<U+001F>k", stands between the heading `### Light theme` and its table, and it reads as a label for the other theme', p.problems[0][3])
        # and the rule's own sentences say so
        rules = " ".join(_palette.parse_tables.__doc__.split())
        for part in ("A line's blanks are what a person sees as a space: the space, the tab, and every character of Unicode's category Zs",
                     "So a `#` with a no-break space after it, or before it (as with a tab or four spaces), starts a heading, a line with one before its first `|` is a row of a table",
                     "No other character is a blank: not the information separators (U+001C to U+001F), not U+0085."):
            self.assertIn(part, rules)

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

    def test_no_megabyte_of_input_makes_the_reading_slow(self):
        # A megabyte is the most the command reads. The slowest shape found is the one round 4's reviewer brought (rows of 990
        # cells that each begin a colour): 0.84 seconds of processor time with a load of 5.5 on the machine, and 1.7 while another
        # heavy job ran beside it; half a million one-pipe lines take 0.59 and 1.2, 75,000 rows that are each refused 0.55 and 1.0.
        # All of them grow with the length and no faster; the limit leaves room for a slower machine still, and fails what round 3
        # measured (81 seconds) many times over.
        # Round 5: a value cell that is one run of underscores, stars or backticks took 5.0, 3.2 and 4.6 seconds, because the pattern for
        # the mark after a colour began again at every character of the run; the mark is now looked for from the end of the cell, once
        # (0.09 seconds each). The slowest shape is still the rows of 990 cells: 1.34 seconds on Python 3.13 and 2.51 on 3.9, with a load
        # of 7 to 10 on the machine; of the shapes this round added, the footnote figures after a colour (0.44 and 0.70).
        for name, md in (# round 3 measured 81 seconds for this megabyte: each row was looked up in a list of the rows before it
                         ("a megabyte of rows under no heading, every other one with a colour", "|Body|#000|\n|Body||\n" * 52428),
                         ("the same under a header that is not Hex", "### Light theme\n|a|b|\n|-|-|\n" + "|Body|#000|\n|Body||\n" * 52000),
                         ("a megabyte of lines that each hold a colour that is not read", "- Muted: #5a5a72\n" * 61000),
                         ("a megabyte of lines that each hold the word", "a proposal\n" * 95000),
                         ("a megabyte of comments", "<!-- #123456 -->\n" * 61000), ("a megabyte of comments that never close", "<!--" * 262144),
                         ("a megabyte of comments that end at --!>, with no --> anywhere", "<!-- #123456 --!>\n" * 58000),
                         ("a megabyte of functions that never close", "- " + "rgb(" * 262000), ("a megabyte of hashes and digits", "#12345 " * 149000),
                         ("a megabyte of labels", "### Light theme\n" + "**Dark theme**\n" * 69000), ("a megabyte of one-pipe lines", "### Light theme\n" + "|\n" * 524000),
                         ("a megabyte of rows that are each see-through", "### Light theme\n" + "|Muted|#1118|\n" * 74000),
                         ("a megabyte of rows of a thousand cells", "### Light theme\n" + ("|Muted" + "|x" * 990 + "|\n") * 527),
                         # round 4: the slowest shape is this one, 1.4 times the one-pipe lines
                         ("a megabyte of rows whose every cell begins a colour", "### Light theme\n" + ("|#" * 990 + "\n") * 529),
                         ("a megabyte of rows whose every cell opens a function", "### Light theme\n" + ("|a(" * 600 + "\n") * 582),
                         ("a megabyte of lines that begin with # and are no headings", "#x\n" * 349000),
                         ("a megabyte of headings with a remark that is not read", "### Dark theme (x)\n" * 55000),
                         ("a megabyte of headings that are the palette's with emphasis in them", "## *Colour* pal_ette_\n" * 47000),
                         ("a megabyte of header rows that name another section", "### Light theme\n" + "| Dark theme | Hex |\n|---|---|\n| Muted | #777 |\n\n" * 21800),
                         ("a megabyte of the word between underscores", "_proposed_ __proposal__\n" * 43600),
                         # round 5
                         ("a megabyte of value cells that are one run of underscores", "### Light theme\n" + ("|x|" + "_" * 1990 + "\n") * 526),
                         ("the same of stars", "### Light theme\n" + ("|x|" + "*" * 1990 + "\n") * 526),
                         ("of backticks after a colour", "### Light theme\n" + ("|Muted|#fff " + "`" * 1980 + "\n") * 526),
                         ("of tildes after a colour", "### Light theme\n" + ("|Muted|#fff " + "~" * 1980 + "\n") * 526),
                         ("of footnote figures after a colour", "### Light theme\n" + ("|Muted|#fff " + "\u00b2" * 1980 + "\n") * 526),
                         ("of brackets before the mark", "### Light theme\n" + ("|Muted|#fff " + "(" * 1970 + "proposed)\n") * 526),
                         ("a megabyte of lines beyond ASCII that hold the word", "prop\u00adosed \u00e9\n" * 87000), ("of character references", ("&shy;" * 390 + "\n") * 537),
                         ("of lines that could be a label for the other theme", "### Light theme\n" + "x dark\n" * 149000),
                         ("of brackets, tags and markers in such lines", "### Light theme\n" + ("(" * 1990 + "\n" + "<b" * 995 + "\n" + ">" * 1990 + "\n" + "1" * 1990 + "\n") * 131),
                         ("of fence lines", "```\n" * 262144), ("of fences that are never closed", "~~~\n# x\n" * 131000),
                         ("of lines inside one fence that look like headings", "```\n" + "### Light theme\n|Muted|#fff|\n" * 37000),
                         ("of header rows that say the other theme's word", "### Light theme\n" + "| Token (dark) | Hex |\n|---|---|\n| Muted | #777 |\n\n" * 21000),
                         # round 6. A character reference of more than 4,300 digits was a traceback on Python 3.13 and 11 seconds on 3.9, and a long
                         # run of combining characters 52 seconds for half a megabyte on 3.9: references are not resolved any more, and no text is
                         # put into a normal form. Cells that begin a colour and hold a character beyond ASCII took 21 and 31 seconds, because each
                         # built a refusal whose sentence was spelled out character by character.
                         ("of one character reference", "A &#" + "9" * 1000000 + "; proposed\n"), ("of references of 5,000 digits", ("&#" + "1" * 5000 + ";roposed\n") * 200),
                         ("of named references", "prop&shy;osed &zwnj;\n" * 49000),
                         ("of two combining characters after a letter, and the word", "A" + "\u0315" * 262144 + "\u0300" * 262144 + " proposed\n"),
                         ("of mixed combining characters on short lines", "pro\u0336\u0315\u0300\ufe0f\u20dd\u034fposed \u0301\u0489\n" * 37000),
                         ("of the same in the cells of rows", "### Light theme\n" + ("|Muted|#fff|" + "a\u0336\u0300|" * 300 + "\n") * 580),
                         ("of control characters", "pro\x01\x7fposed \x9b\x02\n" * 65000),
                         ("of labels with combining characters", "### Light theme\n" + ("dark" + "\u0336\u0315" * 990 + "\n") * 262),
                         ("of rows whose every cell begins a colour and holds a letter beyond ASCII", "### Light theme\n" + ("|#\u00e9" * 660 + "\n") * 397),
                         ("of the same with a character nobody sees", "### Light theme\n" + ("|#\ufe0f" * 400 + "\n") * 524),
                         ("of the same under a row's name", "### Light theme\n" + ("|Muted|#\u00e9|\n") * 80000)):
            with self.subTest(name=name):
                self.timed(md, limit=6.0)

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
                               ("### _Light theme_", "light"), ("###\tDark theme", "dark"), ("  ### Light theme", "light")):
            with self.subTest(heading=heading):
                p = _palette.parse_tables(heading + "\n" + HEAD + "| Muted | #5a5a72 |\n")
                self.assertEqual((p.theme(theme), p.problems), ({"muted": "#5a5a72"}, []))
        for heading in ("### Brand", "## Brand (fixed, theme-independent)", "### BRAND", "### **Brand**", "### Brand (Fixed,  Theme-Independent)", "### Brand(fixed, theme-independent)",
                        "### **Brand** (*fixed, theme-independent*)", "### Brand ( fixed, theme-independent )"):
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
                # (a heading that holds the word "proposed" and names no section is named for that too: rule 9)
                self.assertEqual(codes(p), [("?", None, "palette-no-section")] + [("?", None, MARK)] * ("ropos" in heading.lower()))
                for part in ("under the heading", heading.strip()[:40], "Heading", "Surface (cards)", "`### Light theme`", "`### Dark theme`", "were not used"):
                    self.assertIn(part, p.problems[0][3])

    def test_a_heading_longer_than_the_limit_names_no_section_whatever_it_begins_with(self):
        # round 3: cut at the limit, "### Light theme" + 2,000 characters of padding + " typography" named the light section
        for filler in ("_" * 2000, " " + "x" * 2000, "`" * 2000):
            with self.subTest(filler=filler[:3]):
                p = _palette.parse_tables("### Light theme" + filler + " typography\n" + plain(STARTER_LIGHT))
                self.assertEqual((p.light, [c for _t, _k, c in codes(p)]), ({}, ["palette-no-section"]))
        # spaces do not count towards the length (rule 1)
        p = _palette.parse_tables("### Light theme" + " " * 5000 + "(" + " " * 5000 + "proposed )\n" + plain(STARTER_LIGHT))
        self.assertEqual((p.light, p.proposed, p.problems), (STARTER_LIGHT, {("light", k) for k in STARTER_LIGHT}, []))

    def test_a_line_that_is_no_heading_names_no_section_whatever_it_says(self):
        # labels, bold lines, underlined headings, HTML: none of them is read as a heading, and none is guessed at
        for label in ("Light theme", "Light theme:", "**Light theme**", "_Light theme_", "LIGHT THEME", "<h3>Light theme</h3>", "- Light theme",
                      "> ### Light theme", "1. Light theme", "Light theme\n-----------", "Light theme\n===========", "Palette 2, light theme:",
                      "###Light theme", "#Light theme", "####### Light theme"):
            with self.subTest(label=label):
                p = _palette.parse_tables(label + "\n" + plain(STARTER_LIGHT))
                self.assertEqual((p.light, p.dark), ({}, {}))
                self.assertEqual(codes(p), [("?", None, "palette-no-section")])
                self.assertIn("under the line", p.problems[0][3])
                self.assertIn("which is not a heading (a heading is one to six # and then a space: `### Light theme`)", p.problems[0][3])
                self.assertIn(" ".join(label.splitlines()[-1].split()), p.problems[0][3])

    def test_no_line_of_text_under_a_heading_files_its_table_elsewhere(self):
        # round 2: "Not for dark mode" filed the table under dark; "These colours belong to our brand" under Brand
        # (round 5: a line that is nothing but a label for the other theme is named: the test after the next one)
        for prose in ("(pairs with the dark theme below)", "Pairs with the dark theme below.", "*(see also: dark)*", "Paired with: dark", "Not for dark mode",
                      "These colours belong to our brand", "Note: the dark theme", "Same roles as dark", "Warm paper, dark ink.", "Dark ink on warm paper", "Brand colours",
                      "Light theme", "**Light theme:**", "Light theme (ours)", "The light theme", "- Light mode", "Light theme (not the dark one)", "Light (for the day)",
                      "This table is for the dark theme of the site.", "Darker than the theme before", "Night and day", "The values", "dark_theme_v2",
                      # round 6: a line that names its OWN theme too is no label for the other one
                      "Light for day, dark for night.", "Light \u2014 the day theme; dark \u2014 the night theme", "dark / light", "Dark theme, light theme", "Day and night", "Dark (not light)",
                      # and the limits rule 2 states: a word outside the list, another language, a character reference, a wide letter, emphasis or a tag inside the word
                      "Dark theme (see (note))", "Dark theme (a (b (c)) d) colours", "Dark theme v2", "Dunkel", "Dunkles Thema (dark)", "Dark&nbsp;mode", "&#68;ark theme",
                      "Dark theme &mdash; values", "D&#173;ark theme", "\uff24ark theme", "\uff44\uff41\uff52\uff4b", "The da**rk** theme", "<b>Da</b>rk mode", "Da_rk_ mode",
                      # (round 9: a character inside the word that ends a line to this reader is no limit any more. The text that holds one is
                      # not read: Rule9ALineEndThatIsNoPlainNewLine below has the seven lines that stood here.)
                      # R7-202: emphasis inside the word is seen through for the three exact names only (the test after this one)
                      "da**rk** mode", "The da**rk** mode", "Da*r*k",
                      # R7-206: a character nobody sees that the one pass does not take out (a filler Unicode files as a letter, a private-use
                      # character, one that is not assigned)
                      "Da\u1160rk theme", "Da\u3164rk", "D\u115fark mode", "Dar\uffa0k", "Da\ue000rk theme", "Da\u2065rk mode",
                      # R7-208: a word that only begins with the other theme's word is an ordinary word
                      "Darker", "Darker palette", "Darkened values", "Hex values (darkened 10%)", "Version 2 (darker)", "Darkness", "Darken", "The darkest tokens",
                      "Darkroom", "Darkmodes", "Darkthemed", "Dark2a", "Nightly", "Night2", "Tonight"):
            with self.subTest(prose=prose):
                p = _palette.parse_tables("### Light theme\n%s\n" % prose + plain(STARTER_LIGHT))
                self.assertEqual((p.light, p.dark, p.brand), (STARTER_LIGHT, {}, None))
                self.assertEqual(p.problems, [])

    def test_a_line_before_the_first_table_that_is_the_name_of_another_section_is_named_and_no_table_under_the_heading_is_read(self):
        # round 3: `### Dark theme`, then `**Light theme**`, then the table: filed as the dark theme's without a word
        # (R7-202: emphasis marks are taken out of the three exact names wherever they stand, inside a word too; R7-201: so is U+001F)
        for label, there in (("**Light theme**", "light"), ("Light theme:", "light"), ("Light theme", "light"), ("_LIGHT THEME_", "light"), ("`Light theme` :", "light"),
                             ("**Light theme:**", "light"), ("Brand", "brand"), ("**Brand (fixed, theme-independent)**", "brand"), ("Light theme (the default)", "light"),
                             ("li**ght** theme", "light"), ("Light th_e_me", "light"), ("Br`a`nd", "brand"), ("Lig\x1fht theme", "light"), ("Light the\x1fme:", "light")):
            with self.subTest(label=label):
                p = _palette.parse_tables("### Dark theme\n\n%s\n\n" % label + plain(STARTER_LIGHT) + "\n" + HEAD + "| Muted | #777777 |\n")
                self.assertEqual((p.light, p.dark, p.brand, p.rows_found), ({}, {}, None, 0))
                self.assertEqual(codes(p), [("?", None, "palette-label")], "said once, for every table under that heading")
                for part in ('Line 3, "%s", stands between the heading `### Dark theme` and its table' % label.replace("\x1f", "<U+001F>"), "the name of another section", "not a heading",
                             "read no table under that heading", "write that line as a heading (`%s`)" % _palette.HEADING[there], "if it belongs under `### Dark theme`, take the line out"):
                    self.assertIn(part, p.problems[0][3])
        # R7-202: the example rule 2 gives, word for word, and the one it gives for the limit
        p = _palette.parse_tables("### Light theme\nda**rk** theme\n" + plain(STARTER_DARK))
        self.assertEqual((p.light, [c for _t, _k, c in codes(p)]), ({}, ["palette-label"]))
        self.assertIn('Line 2, "da**rk** theme", stands between the heading `### Light theme` and its table, and it is the name of another section.', p.problems[0][3])
        p = _palette.parse_tables("### Light theme\nda**rk** mode\n" + plain(STARTER_DARK))
        self.assertEqual((p.light, p.problems), (STARTER_DARK, []), "the limit: passed over without a word")
        rules = " ".join(_palette.parse_tables.__doc__.split())
        self.assertIn("so `da**rk** theme` under `### Light theme` IS named, as the name of another section", rules)
        self.assertIn("INSIDE the word (`da**rk** mode`, `<b>Da</b>rk mode`)", rules)
        # a sentence between the label and the table changes nothing, and neither does a table that holds no colour yet
        p = _palette.parse_tables("### Dark theme\n**Light theme**\nBright and floury.\n" + plain(STARTER_LIGHT))
        self.assertEqual((p.dark, [c for _t, _k, c in codes(p)]), ({}, ["palette-label"]))
        p = _palette.parse_tables("### Dark theme\n**Light theme**\n" + HEAD + "| Muted | #[…] |\n")
        self.assertEqual((p.rows_found, [c for _t, _k, c in codes(p)], p.ignored), (0, ["palette-label"], ["Muted"]))
        # under the next heading everything is read as before
        p = _palette.parse_tables("### Dark theme\n**Light theme**\n" + plain(STARTER_LIGHT) + "### Light theme\n" + plain(STARTER_LIGHT))
        self.assertEqual((p.light, p.dark, [c for _t, _k, c in codes(p)]), (STARTER_LIGHT, {}, ["palette-label"]))

    def test_a_line_before_the_first_table_that_is_nothing_but_a_label_for_the_other_theme_is_named_too(self):
        # round 5: only the exact name of another section was a label. Under `### Light theme`, the line `Dark mode` and the dark
        # table: read as the light theme, exit 0. The words such a line may be made of are rule 2's short list.
        # Round 6: one test for a line and for a cell of a header row. The words inside brackets count, the other theme's word is `dark...` at
        # a word's start or `night`, the line's own theme's word makes it no label, and what nobody sees is taken out first.
        for label in ("Dark", "**Dark**", "Dark mode", "The dark theme", "Dark theme - night", "Dark theme values", "- Dark theme", "> Dark theme", "* Dark", "1. Dark theme", "2) Dark mode",
                      "> - **Dark theme:**", "Dark theme.", "#Dark theme", "####### Dark theme", "<b>Dark theme</b>",
                      "<strong class=\"x\">Dark</strong> mode", "DARK MODE", "Dark theme colours", "Colors for the dark theme", "Tokens: dark", "The night palette (dark)... dark",
                      "`dark`", "Dark\u00a0mode", "Dark\u2003values", "_Dark_ _mode_",
                      # the word inside brackets
                      "(Dark theme)", "*(dark mode)*", "Palette (dark)", "Colours (dark)", "Theme (dark)", "(dark)", "[Dark]", "Dark (theme (mode))",
                      # with a character nobody sees: a soft hyphen, a zero-width space, a variation selector, a combining stroke, a control character
                      "Dar\u00adk", "D\u200bark mode", "Dark\ufe0f mode", "D\u0336a\u0336r\u0336k\u0336", "Da\x01rk mode", "Dark mo\u200dde", "\u034fDark",
                      # round 7: U+001F, which Python's split() takes for a blank and nobody sees, inside the theme's word and inside a label word
                      "Dar\x1fk", "D\x1fark mode", "Dark mo\x1fde", "The da\x1frk the\x1fme", "Dark\x1fmode",
                      # one word: the two closed compounds, each with or without digits after it; in two words (a hyphen) they read the same,
                      # with digits after them as a word of their own (R7-208; round 8 pins what digits joined to the second word do, below)
                      "Darkmode", "DarkTheme", "darkTheme tokens", "Dark2", "dark-mode", "Dark-Theme", "darkmode2", "DarkTheme 3", "dark-theme-2", "darktheme10 colours",
                      # the label words round 6 added, and a number
                      "Dark scheme", "Dark variant", "Dark version", "Dark colour scheme", "Dark color", "Dark hex", "Dark theme table", "Use in dark mode", "These are the dark values",
                      "Table 2: dark theme", "Dark set", "Dark token", "Dark value", "Dark theme 2",
                      # night for dark
                      "Night", "Night mode", "The night theme", "night / dark"):
            with self.subTest(label=label):
                p = _palette.parse_tables("### Light theme\n\n%s\n\n" % label + plain(STARTER_DARK) + "\n" + HEAD + "| Muted | #777777 |\n\n### Dark theme\n" + plain(STARTER_LIGHT))
                self.assertEqual((p.light, p.dark, p.brand), ({}, STARTER_LIGHT, None), "no table under that heading is read; the next heading is read as before")
                self.assertEqual(codes(p), [("?", None, "palette-label")], "said once, for every table under that heading")
                shown = label.replace("\u00a0", " ").replace("\u2003", " ")  # the label is quoted as the line is read: with its blanks made one space (rule 1)
                for part in ('Line 3, %s, stands between the heading `### Light theme` and its table, and it reads as a label for the other theme.' % _palette._quoted(shown),
                             "A line of text is not a heading", "read no table under that heading", "If the table belongs under `### Dark theme`, write that line as a heading (`### Dark theme`)",
                             "if it belongs under `### Light theme`, take the line out"):
                    self.assertIn(part, p.problems[0][3])
        # the other way round, under `### Dark theme`
        # (R7-208: `day` whole is the light theme's word, so "Day 2" and "Day 1 palette" stay labels)
        for label in ("Light", "Light mode", "The light theme:", "- Light theme values", "Light theme (default)", "Day (light)... light", "Day", "Day mode", "Lightmode", "(Light theme)",
                      "Li\u00adght scheme", "Light variant 1", "Lig\x1fht", "light-mode", "LightTheme2", "Light3", "lighttheme", "Day 2", "Day 1 palette"):
            with self.subTest(label=label):
                p = _palette.parse_tables("### Dark theme\n%s\n" % label + plain(STARTER_LIGHT))
                self.assertEqual((p.light, p.dark, [c for _t, _k, c in codes(p)]), ({}, {}, ["palette-label"]))
                self.assertIn("If the table belongs under `### Light theme`, write that line as a heading (`### Light theme`); if it belongs under `### Dark theme`, take the line out", p.problems[0][3])
        # a line underlined as a heading of the other kind is a line of text, and a label like any other
        p = _palette.parse_tables("### Light theme\nNight\n=====\n" + plain(STARTER_DARK))
        self.assertEqual((p.light, [c for _t, _k, c in codes(p)]), ({}, ["palette-label"]))
        self.assertIn('Line 2, "Night", stands between the heading `### Light theme` and its table, and it reads as a label for the other theme.', p.problems[0][3])
        # and what is only text under `### Dark theme`: its own word beside the other's, and a word that only holds the other's
        # (R7-208: and a word that only begins with it, which round 6 took for the theme's word: a correct palette with such a note was refused)
        for prose in ("Light colours for the dark theme.", "Dark theme for night; light theme for day", "Daylight", "Delight", "Twilight", "Highlight colours", "Today", "Lighter than dark",
                      "Lightness values", "Lightness 20", "Lightness", "Lighting", "Lightened 5 %", "Lighten", "Lighter", "Lighter variant", "Lights", "Lightbox colours", "Daytime",
                      "Lightmodes", "Light2go"):
            with self.subTest(prose=prose):
                p = _palette.parse_tables("### Dark theme\n%s\n" % prose + plain(STARTER_DARK))
                self.assertEqual((p.dark, p.problems), (STARTER_DARK, []))
        # the name of another section with a character nobody sees in it is that name (the first kind of label)
        for label in ("Light the\u00adme", "Light theme:\u200b", "**Li\u200bght theme**", "Bra\u2060nd"):
            with self.subTest(label=label):
                p = _palette.parse_tables("### Dark theme\n\n%s\n\n" % label + plain(STARTER_LIGHT))
                self.assertEqual((p.light, p.dark, [c for _t, _k, c in codes(p)]), ({}, {}, ["palette-label"]))
                for part in ("Line 3, %s, stands between the heading `### Dark theme` and its table, and it is the name of another section." % _palette._quoted(label),
                             "is a character that does not show on the screen: take it out"):
                    self.assertIn(part, p.problems[0][3])
        # the limits rule 2 states: under `### Brand` only the exact name is a label, and a line after the first table is the text that ends the section's tables (rule 3)
        p = _palette.parse_tables("### Brand\nDark mode\n" + HEAD + "| Primary | #123456 |\n")
        self.assertEqual((p.brand, p.problems), ("#123456", []))
        p = _palette.parse_tables("### Light theme\n" + plain(STARTER_LIGHT) + "\nDark mode\n\n" + plain(STARTER_DARK))
        self.assertEqual((p.light, p.dark, [c for _t, _k, c in codes(p)]), (STARTER_LIGHT, {}, ["palette-no-section"]))
        # a caption AFTER the only table, and a note in a cell of a row, are the stated limit: the table is read under its heading
        p = _palette.parse_tables("### Light theme\n" + plain(STARTER_DARK) + "\n*Table: dark theme*\n")
        self.assertEqual((p.light, p.problems), (STARTER_DARK, []))
        p = _palette.parse_tables("### Light theme\n" + plain(STARTER_DARK).replace("| Heading | #e7e9fb |", "| Heading | #e7e9fb | dark theme |"))
        self.assertEqual((p.light, p.problems), (STARTER_DARK, []))
        # a line of more than 2,000 characters is no label, as before
        p = _palette.parse_tables("### Light theme\nDark %s\n" % ("theme " * 400) + plain(STARTER_LIGHT))
        self.assertEqual((p.light, p.problems), (STARTER_LIGHT, []))

    def test_every_other_heading_ends_the_section(self):
        for heading in ("## Notes", "### Typography", "#", "######", "### Light theme typography"):
            with self.subTest(heading=heading):
                p = _palette.parse_tables("### Light theme\n" + HEAD + "| Heading | #16162a |\n" + heading + "\n" + HEAD + "| Muted | #5a5a72 |\n")
                self.assertEqual(p.light, {"heading": "#16162a"})
                self.assertEqual(codes(p), [("?", None, "palette-no-section")])
                self.assertIn("Muted", p.problems[0][3])
        # and the next of the three headings starts its own
        p = _palette.parse_tables("### Light theme\n" + plain(STARTER_LIGHT) + "### Dark theme\n" + plain(STARTER_DARK))
        self.assertEqual((p.light, p.dark, p.problems), (STARTER_LIGHT, STARTER_DARK, []))


    def test_a_line_that_starts_with_a_hash_and_is_no_heading_ends_no_section(self):
        # round 4: a heading is one to six # and then a blank or the end of the line; `#notes` and seven # are text
        for line in ("#notes", "####### seven", "#1", "#16162a", "###Typography", "#Dark theme tables follow"):
            with self.subTest(line=line):
                p = _palette.parse_tables("### Light theme\n%s\n" % line + plain(STARTER_LIGHT) + "\n### Dark theme\n" + plain(STARTER_DARK))
                self.assertEqual((p.light, p.dark), (STARTER_LIGHT, STARTER_DARK), "a line of text between a heading and its table is only text")
                self.assertEqual([c for _t, _k, c in codes(p)], [NOT_READ] * (line == "#16162a"))

    OTHER_REMARKS = ("(vorgeschlagen)", "(Vorschlag)", "(propos\u00e9)", "(draft)", "(the default)", "()", "(proposed, not yet agreed)", "(Proposal 2, not final)",
                     "(fixed, theme-independent)", "(not proposed)", "(proposed1)", "(suggested)", "(#fff)", "(~~proposed~~ ?)", "(proposed\u200b)", "(prop\u00adosed)")

    def test_a_heading_with_any_other_remark_names_no_section_and_is_said_to(self):
        # round 4: `### Dark theme (vorgeschlagen)` was a heading with a remark, so a mark written in the assistant's own
        # language passed, with exit 0, and the dark theme counted as confirmed
        for remark in self.OTHER_REMARKS:
            for theme, name in (("dark", "Dark theme"), ("light", "Light theme")):
                with self.subTest(remark=remark, theme=theme):
                    heading = "### %s %s" % (name, remark)
                    p = _palette.parse_tables(brand_md().replace("### %s\n" % name, heading + "\n"))
                    other = "light" if theme == "dark" else "dark"
                    self.assertEqual((p.theme(theme), p.theme(other), p.brand, p.proposed), ({}, {"light": STARTER_LIGHT, "dark": STARTER_DARK}[other], "#000000", set()))
                    word = bool(re.search(r"propos(ed|al)(?![\w\u00e9])", remark, re.I)) or remark in ("(proposed\u200b)", "(prop\u00adosed)")
                    colour = remark == "(#fff)"
                    self.assertEqual([c for _t, _k, c in codes(p)], ["palette-heading-remark"] + [MARK] * word + [NOT_READ] * colour,
                                     "one problem for the heading; its table is not named a second time")
                    message = p.problems[0][3]
                    for part in ("Line %d, the heading " % (10 if theme == "light" else 23), "names none of the three sections", "no table under it was read",
                                 "After `%s` a heading may carry one remark in brackets and no other: the mark `(proposed)`, written in English" % name,
                                 "Write the heading as `### %s`, or as `### %s (proposed)` if the values under it are still proposals" % (name, name)):
                        self.assertIn(part, message)
                    self.assertIn(_palette._quoted(" ".join(heading.split())), message)
        # on Brand the template's own remark is read, and no other
        p = _palette.parse_tables(brand_md().replace("### Brand (fixed, theme-independent)", "### Brand (fest, f\u00fcr beide)"))
        self.assertEqual((p.brand, p.light, [c for _t, _k, c in codes(p)]), (None, STARTER_LIGHT, ["palette-heading-remark"]))
        self.assertIn("written in English (or, on this one, the template's `(fixed, theme-independent)`)", p.problems[0][3])
        # every table under such a heading is left unread, filled in or not, and the next heading is read as before
        p = _palette.parse_tables("### Dark theme (entwurf)\n" + plain(STARTER_DARK) + "\n" + HEAD + "| Muted | #[\u2026] |\n\nA line.\n\n" + HEAD + "| Link | #9fb0ff |\n"
                                  + "### Dark theme\n" + HEAD + "| Muted | #a6abce |\n")
        self.assertEqual((p.dark, p.rows_found, [c for _t, _k, c in codes(p)], p.ignored), ({"muted": "#a6abce"}, 1, ["palette-heading-remark"], ["Muted"]))
        # the near-misses: what is no bracketed remark after the name is another heading, as before
        for heading in ("### Dark theme (a) (b)", "### Dark theme [vorgeschlagen]", "### Dark theme (unclosed"):
            with self.subTest(heading=heading):
                p = _palette.parse_tables(heading + "\n" + plain(STARTER_DARK))
                self.assertEqual([c for _t, _k, c in codes(p)], ["palette-no-section"])

    def test_such_a_heading_outside_the_palettes_part_with_a_table_under_it_is_still_a_palette_in_the_wrong_place(self):
        p = _palette.parse_tables("## Colour palette\n\n" + pasted(dark={}) + "\n## Appendix\n\n### Dark theme (vorgeschlagen)\n" + plain(STARTER_DARK))
        self.assertEqual((p.dark, [c for _t, _k, c in codes(p)]), ({}, ["palette-outside-section"]))

    def test_a_label_is_the_name_with_or_without_a_remark_however_long_up_to_the_one_limit(self):
        # round 4: the label check stopped at 200 characters and the heading matcher at 2,000, so a longer label filed the table without a word
        for label in ("Light theme (%s)" % ("x" * 200), "Light theme (%s)" % ("x" * 1980), "**Light theme** (%s):" % ("the default, " * 40), "Light theme (hell)",
                      "Light theme (proposed)", "Light theme" + " " * 3000 + "(ours)"):
            with self.subTest(label=label[:30], length=len(label)):
                p = _palette.parse_tables("### Dark theme\n\n%s\n\n" % label + plain(STARTER_LIGHT))
                self.assertEqual((p.light, p.dark, p.rows_found), ({}, {}, 0))
                self.assertEqual([c for _t, _k, c in codes(p)], ["palette-label"] + [MARK] * ("proposed" in label))
        # the limit is the heading's own: a line of more than 2,000 characters is no label, as a heading that long is no heading
        p = _palette.parse_tables("### Dark theme\n\nLight theme (%s)\n\n" % ("x" * 2000) + plain(STARTER_DARK))
        self.assertEqual((p.dark, p.problems), (STARTER_DARK, []))

    def test_the_limits_round_7_states_are_what_the_reader_does(self):
        # R7-207: the other theme's name in a row in FRONT of the table, or in a header row with no separator line under it (which is no
        # header row to this check), is passed over without a word, and the table is read under its heading
        for name, md in (("a title row", "### Light theme\n| Dark theme |\n" + plain(STARTER_DARK)),
                         ("a title row and a blank line", "### Light theme\n| Dark theme |\n\n" + plain(STARTER_DARK)),
                         ("a header row without its separator line", "### Light theme\n| Dark theme | Hex |\n" + "\n".join(lines(STARTER_DARK)) + "\n"),
                         ("the same, the word in brackets", "### Light theme\n| Token (dark) | Hex |\n" + "\n".join(lines(STARTER_DARK)) + "\n")):
            with self.subTest(name=name):
                p = _palette.parse_tables(md)
                self.assertEqual((p.light, p.dark, p.problems), (STARTER_DARK, {}, []))
        # (with the separator line the same header row is named: the test below)
        p = _palette.parse_tables("### Light theme\n| Token (dark) | Hex |\n|---|---|\n" + "\n".join(lines(STARTER_DARK)) + "\n")
        self.assertEqual((p.light, [c for _t, _k, c in codes(p)]), ({}, ["palette-label"]))
        # R7-210: an accent written as a separate mark is taken out for the search, so the same line is a label written that way and
        # text written with the one accented letter
        for apart, joined, under, rows in (("Da\u0303y 2", "D\u00e3y 2", "Dark", STARTER_LIGHT), ("The\u0300me dark", "Th\u00e8me dark", "Light", STARTER_DARK)):
            with self.subTest(line=joined):
                import unicodedata
                self.assertEqual(unicodedata.normalize("NFC", apart), joined)
                p = _palette.parse_tables("### %s theme\n%s\n\n" % (under, apart) + plain(rows))
                self.assertEqual((p.light, p.dark, [c for _t, _k, c in codes(p)]), ({}, {}, ["palette-label"]))
                p = _palette.parse_tables("### %s theme\n%s\n\n" % (under, joined) + plain(rows))
                self.assertEqual((p.theme(under.lower()), p.problems), (rows, []))

    def test_a_compound_in_two_words_reads_the_same_but_not_with_digits_joined_to_its_second_word(self):
        # round 8 (R8-204): rule 2 said the closed compounds count "with or without digits" and "with a hyphen ... the same", which read as if
        # `dark-mode2` were caught. It is not, and the rule now says what the reader does: a hyphen or an underscore makes two words, the
        # first is the theme's word and the second must be one of the label words, which `mode2` is not.
        rules = " ".join(_palette.parse_tables.__doc__.split())
        for part in ("A hyphen or an underscore makes two words of a compound, which reads the same (`dark-mode`, `dark_theme`: the word `dark` and one of (c)'s words), but not "
                     "with digits joined to its second word: `dark-mode2`, `dark_theme3` and `Dark mode2` are no labels, because `mode2` is none of (c)'s words (`Dark-mode 2` "
                     "is one, and so is `darkmode2`).",
                     "a compound in two words with digits joined to the second (`dark-mode2`, point (a) above)"):
            self.assertIn(part, rules)
        for theme, other, own, theirs in (("Light", "dark", STARTER_LIGHT, STARTER_DARK), ("Dark", "light", STARTER_DARK, STARTER_LIGHT)):
            # passed over without a word, as a line before the table and as a cell of its header row: the table is read under its heading
            for word in ("%s-mode2", "%s-theme3", "%s_mode2", "%s_theme3", "%s mode2", "%s theme3", "%s-Mode10 colours"):
                word = word % other.capitalize()
                for name, md in (("a line", "### %s theme\n\n%s\n\n" % (theme, word) + plain(theirs)),
                                 ("a header cell", "### %s theme\n| %s | Hex |\n|---|---|\n" % (theme, word) + "\n".join(lines(theirs)) + "\n")):
                    with self.subTest(theme=theme, word=word, name=name):
                        p = _palette.parse_tables(md)
                        self.assertEqual((p.theme(theme.lower()), p.theme(other), p.problems), (theirs, {}, []))
            # and each of these is a label, in both places: no table under that heading is read
            for word in ("%s-mode", "%s_theme", "%s_mode", "%s-mode 2", "%s_theme_2", "%smode2", "%stheme3", "%s2", "%s-2", "%s-mode-2"):
                word = word % other.capitalize()
                for name, md in (("a line", "### %s theme\n\n%s\n\n" % (theme, word) + plain(theirs)),
                                 ("a header cell", "### %s theme\n| %s | Hex |\n|---|---|\n" % (theme, word) + "\n".join(lines(theirs)) + "\n")):
                    with self.subTest(theme=theme, word=word, name=name):
                        p = _palette.parse_tables(md)
                        self.assertEqual((p.light, p.dark, [c for _t, _k, c in codes(p)]), ({}, {}, ["palette-label"]))

    def test_a_header_row_that_calls_its_first_column_by_another_sections_name_is_named_and_its_table_is_not_read(self):
        # round 4: under `### Light theme`, a table headed `| Dark theme | Hex |` was read as the light theme's without a word
        for header, there in (("| Dark theme | Hex |", "dark"), ("| **Dark theme** | Hex |", "dark"), ("| DARK THEME: | Hex | Use |", "dark"), ("| Brand | Hex |", "brand"),
                              ("| Dark theme (proposed) | Hex |", "dark"), ("| Dark theme (dunkel) | Hex |", "dark"), ("| Dark theme | Value |", "dark"), ("| Brand | Hex | for dark |", "brand")):
            with self.subTest(header=header):
                p = _palette.parse_tables("### Light theme\n" + header + "\n|---|---|\n" + "\n".join(lines(STARTER_DARK)) + "\n\n### Dark theme\n" + plain(STARTER_DARK))
                self.assertEqual((p.light, p.dark), ({}, STARTER_DARK))
                self.assertEqual([c for _t, _k, c in codes(p)], ["palette-label"] + [MARK] * ("proposed" in header))
                for part in ('Line 2, the header row "%s", calls its first column by the name of another section' % header, "its table stands under `### Light theme`",
                             "it did not read the table", "If the table belongs under `%s`, write that heading on a line of its own above it" % _palette.HEADING[there],
                             'if it belongs under `### Light theme`, call the first column "Token" (`| Token | Hex |`)'):
                    self.assertIn(part, p.problems[0][3])
        # a table that holds no colour yet is told the same, and the table after it under the same heading is read
        p = _palette.parse_tables("### Light theme\n| Dark theme | Hex |\n|---|---|\n| Muted | #[\u2026] |\n\n" + plain(STARTER_LIGHT))
        self.assertEqual((p.light, [c for _t, _k, c in codes(p)], p.ignored), (STARTER_LIGHT, ["palette-label"], ["Muted"]))
        # round 5: a header row that says the other theme's word in any cell, and not its own, is named in the same way
        # round 6: the test is the line's, held for each cell on its own. So one word (`Darkmode`), `night`, and a cell with a character nobody sees are
        # labels too, and a cell that says its own theme's word no longer excuses another cell that is a label for the other theme.
        for header, word in (("| Dark | Hex |", "dark"), ("| Dark theme tokens | Hex |", "dark"), ("| Token (dark) | Hex |", "dark"), ("| Token | Hex | Dark theme |", "dark"),
                             ("| Token | Hex (DARK) |", "dark"), ("| Token | Hex | _dark_ mode |", "dark"), ("| Dark token | Hex | Use |", "dark"), ("| Token | Hex | Use | dark |", "dark"),
                             ("| dark_tokens | Hex |", "dark"), ("| Token | Dark |", "dark"), ("| Token | Value | for dark mode |", "dark"),
                             ("| Token | Hex | Darkmode |", "darkmode"), ("| Darkmode | Hex |", "darkmode"), ("| DarkTheme | Hex |", "darktheme"), ("| Token | Hex | Night |", "night"),
                             ("| Token | Hex | Da\u200brk |", "dark"), ("| Token (d\u00adark) | Hex |", "dark"), ("| Token | Hex | Da\x1frk |", "dark"),
                             ("| Dark-mode | Hex |", "dark"), ("| Token | Hex | DarkTheme2 |", "darktheme2"),
                             ("| Token | Hex | dark2 |", "dark2"), ("| Token | Hex | Dark scheme |", "dark"), ("| Token | Hex | (dark) | Use |", "dark"),
                             ("| Light token | Hex | Darkmode |", "darkmode"), ("| Hex | Hex | Dark colour 2 |", "dark")):
            with self.subTest(header=header):
                p = _palette.parse_tables("### Light theme\n" + header + "\n|---|---|\n" + "\n".join(lines(STARTER_DARK)) + "\n\n### Dark theme\n" + plain(STARTER_DARK))
                self.assertEqual((p.light, p.dark, [c for _t, _k, c in codes(p)]), ({}, STARTER_DARK, ["palette-label"]))
                for part in ('Line 2, the header row %s, says "%s", and its table stands under `### Light theme`' % (_palette._quoted(header), word), "it did not read the table",
                             "If the table belongs under `### Dark theme`, write that heading on a line of its own above it",
                             "if it belongs under `### Light theme`, take that word out of the header row (`| Token | Hex |`)"):
                    self.assertIn(part, p.problems[0][3])
        p = _palette.parse_tables("### Dark theme\n| Token (light) | Hex |\n|---|---|\n" + "\n".join(lines(STARTER_LIGHT)) + "\n")
        self.assertEqual((p.dark, [c for _t, _k, c in codes(p)]), ({}, ["palette-label"]))
        self.assertIn('says "light", and its table stands under `### Dark theme`', p.problems[0][3])
        # the near-misses: the section's own name or word, the other word as a part of a longer word, and any other first cell
        # (a header row that holds both words with an underscore joined to each is not rule 10's "both themes", and with its own word in it no label)
        # Round 6: a cell with other words in it is a note, and the limits are rule 2's (a character reference, emphasis inside the word, another language)
        for header in ("| Light theme | Hex |", "| Token (light) | Hex |", "| Token | Hex | Lighter than dark? No: light |", "| Theme | Hex |",
                       "| Token | Hex | light_bg, dark_bg |", "| light_token | Hex | on_dark |", "| Token | Hex | Contrast on dark ink |", "| Token | Hex | Pairs with dark |",
                       "| Token | Hex | D&#97;rk |", "| Token | Hex | da**rk** |", "| Token | Hex | Dunkel |", "| Token | Hex | \uff24ark |", "| Token | Hex | Day |", "| Token | Hex | Nightly |",
                       # R7-208: a word that only begins with the other theme's word names no theme (round 6 refused these)
                       "| Darker | Hex |", "| Token | Hex | Darkness |", "| Token | Hex | Darkened |", "| Token | Hex | Darken 10 |", "| Token | Hex | Darker variant |"):
            with self.subTest(header=header):
                p = _palette.parse_tables("### Light theme\n" + header + "\n|---|---|\n" + "\n".join(lines(STARTER_LIGHT)) + "\n")
                self.assertEqual((p.light, [c for _t, _k, c in codes(p)]), ({} if "No: light" in header else STARTER_LIGHT, ["palette-combined-table"] * ("No: light" in header)))
        for header in ("| Token | Hex | Light equivalent |", "| Token | Hex | Use (light text) |", "| Token | Hex | Night |", "| Token | Hex | on light paper |",
                       "| Token | Hex | Lightness |", "| Token | Hex | Lightness % |", "| Token | Hex | Lighten |", "| Lightness | Hex |", "| Token | Hex | Lighter variant |"):
            with self.subTest(header=header, under="dark"):
                p = _palette.parse_tables("### Dark theme\n" + header + "\n|---|---|\n" + "\n".join(lines(STARTER_DARK)) + "\n")
                self.assertEqual((p.dark, p.problems), (STARTER_DARK, []))
        # a cell with a character nobody sees is quoted with it written out, and the sentence says so
        p = _palette.parse_tables("### Light theme\n| Token | Hex | Da\u200brk |\n|---|---|\n" + "\n".join(lines(STARTER_DARK)) + "\n")
        for part in ('the header row "| Token | Hex | Da<U+200B>rk |", says "dark"', "is a character that does not show on the screen: take it out"):
            self.assertIn(part, p.problems[0][3])
        # under `### Brand` a header row may say either word
        p = _palette.parse_tables("### Brand\n| Token | Hex | on dark |\n|---|---|---|\n| Primary | #123456 | fine |\n")
        self.assertEqual((p.brand, p.problems), ("#123456", []))

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
        for label in ("**Dark theme**", "Dark theme:", "Dark theme", "And for the night:", "<!- dark ->", "---"):
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

    def test_a_row_without_its_first_pipe_is_no_row_and_its_colour_is_named_wherever_it_stands(self):
        # round 3: named only under one of the three headings; rule 12 names such a line anywhere
        for heading in ("### Light theme\n", "## Colours\n", ""):
            for name, md, first in (("no outer pipes", "Token | Hex\n---|---\nHeading | #16162a\nBackground | #ffffff\n", '"Heading | #16162a"'),
                                    ("a quoted table", "> | Token | Hex |\n> |---|---|\n> | Heading | #16162a |\n", '"> | Heading | #16162a |"')):
                with self.subTest(heading=heading, name=name):
                    p = _palette.parse_tables(heading + md)
                    self.assertEqual((p.light, p.rows_found), ({}, 0))
                    self.assertEqual({c for _t, _k, c in codes(p)}, {NOT_READ})
                    self.assertEqual(len(p.problems), md.count("#"), "each line that holds a colour, once")
                    for part in (first, "holds a colour (#16162a) that was not read", "only from the second cell of a named row (`| Muted | #5a5a72 |`)"):
                        self.assertIn(part, p.problems[0][3])
        # a sentence with a | and no colour is a sentence
        p = _palette.parse_tables("### Light theme\nEither | or.\n" + plain(STARTER_LIGHT))
        self.assertEqual((p.light, p.problems), (STARTER_LIGHT, []))


class Rule4Rows(unittest.TestCase):
    """4. The first cell is the row's name, exactly one of the template's or of the old template's two
    short forms. The second cell is the value, always. The cells after it are notes."""

    def test_the_names_the_template_uses_and_the_two_short_forms(self):
        for key, label in LABELS + [("ink", "Body"), ("surface", "Surface"), ("ink", "body (INK)"), ("heading", "**Heading**"), ("muted", "`Muted`"),
                                    ("bg", "BACKGROUND"), ("bg_soft", "Soft   background"), ("surface", "_Surface (cards)_")]:
            with self.subTest(label=label):
                p = _palette.parse_tables(one("#123456", label=label))
                self.assertEqual((p.light, p.problems), ({key: "#123456"}, []))
        for label in ("Primary", "primary", "**Primary**"):
            with self.subTest(label=label):
                self.assertEqual(_palette.parse_tables(one("#123456", label=label, heading="### Brand")).brand, "#123456")

    def test_no_other_name_is_a_row_and_a_colour_under_one_is_named_as_not_read(self):
        # a second brand colour is not the muted text, "Text" is not the body, a CSS variable is not its row
        for label in ("Headings", "Heading:", "Heading text", "Text", "Body text", "Ink", "Secondary", "Secondary text", "Muted text", "Border", "Line",
                      "Divider", "--link", "Links", "Link colour", "Accent colour", "Bg", "Page background", "Soft bg", "Surface / cards", "Cards", "Card",
                      "Brand", "Primary colour", "Brand primary", "Muted (proposed)", "Überschrift", "Body (ink) 2", "Soft-background", "Heading 1"):
            with self.subTest(label=label):
                p = _palette.parse_tables(one("#123456", label=label))
                self.assertEqual((p.light, p.dark, p.brand, p.proposed, p.rows_found), ({}, {}, None, set(), 0))
                # ("Muted (proposed)" holds the word in its first cell, where it is not read as a mark: rule 9 names that too)
                self.assertEqual(codes(p), [("?", None, MARK)] * ("proposed" in label) + [("?", None, NOT_READ)])
                for part in ('Line 4, "| %s | #123456 |", holds a colour (#123456) that was not read' % label, "the names are Primary under `### Brand`",
                             "Heading, Body (ink), Muted, Accent, Link, Hairline, Background, Soft background, Surface (cards) under the two themes"):
                    self.assertIn(part, of(p, NOT_READ)[0])

    def test_the_second_cell_is_the_value_and_a_later_cell_is_a_note(self):
        for note in ("buttons, brand surfaces", "6.5:1 on #ffffff", "sits on #fdfdfd", "Gray", "white", "16.9:1 (AAA)", "—", "",
                     "hover is #1a3fb0", "was 5a5a72", "ok | really | fine"):
            with self.subTest(note=note):
                p = _palette.parse_tables("### Light theme\n| Token | Hex | Note |\n|---|---|---|\n| Muted | #5a5a72 | %s |\n" % note)
                self.assertEqual((p.light, p.problems), ({"muted": "#5a5a72"}, []))

    def test_a_value_is_never_taken_from_a_cell_after_the_second(self):
        for cells in ("| #5a5a72 |", "#[…] | #5a5a72 |", "- | `#5a5a72` | note |", "| | rgb(90, 90, 114) |", "| #5a5a7280 |", "-- | #5a5a72 |"):
            with self.subTest(cells=cells):
                p = _palette.parse_tables("### Light theme\n| Token | Hex | Other |\n|---|---|---|\n| Muted | %s\n" % cells)
                self.assertEqual((p.light, p.rows_found), ({}, 1))
                self.assertEqual(codes(p), [("?", None, NOT_READ)], "the row is not filled in, and the colour further along it was not read")
                for part in ('Line 4, "| Muted | %s", holds a colour' % cells, "that was not read", "only from the second cell of a named row"):
                    self.assertIn(part, p.problems[0][3])
        # with no colour written as a value further along, an empty value cell is a row not filled in yet (the limit of
        # rule 12: a colour name and hex digits without their # are not seen there)
        for cells in ("| white, for now |", "| 5a5a72 |", "| |"):
            with self.subTest(cells=cells):
                p = _palette.parse_tables("### Light theme\n| Token | Hex | Other |\n|---|---|---|\n| Muted | %s\n" % cells)
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
                      "`#e2874a` (proposal)", "#e2874a ( proposed )", "`#e2874a` PROPOSED",
                      # round 5: a strike-through and a footnote figure beside the mark are not counted either, as rule 9 has them
                      "#e2874a ~~proposed~~", "`#e2874a` ~~proposed~~", "#e2874a proposed\u00b2", "#e2874a (proposed\u00b9)", "#e2874a (proposed)\u00b2", "#e2874a (~~proposed~~)",
                      "#e2874a ~~(proposed)~~", "#e2874a **~~Proposals~~**\u2460", "`#e2874a` (`proposed`)", "#e2874a _(_proposal_)_", "#e2874a proposed\u00b2\u00b3", "#e2874a ( *proposed* )"):
            with self.subTest(value=value):
                p = _palette.parse_tables(one(value))
                self.assertEqual((p.light, p.proposed, p.problems), ({"muted": "#e2874a"}, {("light", "muted")}, []))
        # the near-misses: the word must stand after a space or in brackets, whole, and last in the cell
        for value in ("#e2874aproposed", "#e2874a~~proposed~~", "#e2874a proposed1", "#e2874a unproposed", "#e2874a (proposed", "#e2874a proposed)", "#e2874a (proposed) yes",
                      "#e2874a (not proposed)", "#e2874a \u00b2proposed", "#e2874a pro~~posed~~", "#e2874a (  proposed)"[:9] + "( x proposed)", "proposed #e2874a"):
            with self.subTest(value=value):
                p = _palette.parse_tables(one(value))
                self.assertEqual((p.light, p.proposed), ({}, set()))
                self.assertEqual(len(p.problems), 1, "the row is named, and has no value")

    def test_an_empty_cell_or_a_placeholder_is_a_row_not_filled_in_which_is_not_a_mistake(self):
        for value in ("", "`#[…]`", "#[…]", "#[...]", "#...", "#…", "[hex]", "[…]", "#[hex]", "[ ]", "-", "—", "–", "--", "---", "—–-"):
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
                      "#e3e7f2 @ 100%", "#f5f7fb 50% opacity", "#2b50e0;", "proposed: `#a6abce`", "#ffffff - proposed", "#5a5a72\u200b", "rgb(90 90 114) or so",
                      "#e3e7f2 [proposed]", "#ffffff ← proposed", "#a6abce*", "#5a5a72 (Vorschlag)", "#5a5a72 (not proposed)", "White #ffffff", "<code>#5a5a72</code>",
                      "rgb(1, 2)", "#fff #000", "``#000000` (proposed)`"):
            with self.subTest(value=value):
                p = _palette.parse_tables(one(value))
                self.assertEqual((p.light, p.proposed), ({}, set()), "no value, and so nothing to mark")
                self.assertEqual(codes(p), [("light", "muted", "palette-not-one-colour")])
                message = p.problems[0][3]
                for part in ("Muted (light theme): the second cell holds", value[:40].replace("\u200b", "<U+200B>"), "exactly one colour", "A note belongs in a third cell"):
                    self.assertIn(part, message)
                self.assertNotIn("type sizes", message)
                self.assertIn(("light", "muted"), p.missing(), "a row that cannot be read is a row she has not given")
        # round 3: a zero-width space after the colour was quoted as it is, so the quote showed a colour with nothing wrong with it
        message = _palette.parse_tables(one("#5a5a72\u200b")).problems[0][3]
        self.assertIn('the second cell holds "#5a5a72<U+200B>"', message)
        self.assertIn("a character that does not show on the screen: take it out", message)
        self.assertNotIn("<U+", _palette.parse_tables(one("#5a5a72 or so")).problems[0][3])

    def test_words_that_hold_nothing_like_a_colour_are_named_too_with_a_word_on_other_tables(self):
        # (hex digits without their #, a # with five digits or a letter that is no hex digit: no colour written as a value)
        for value in ("a warm blue", "notacolour", "bleu", "700", "Inter", "tbd", "?", "n/a", "proposed", "see below", "5a5a72", "# 2b50e0", "#c81e3", "#2b50eO",
                      "Facade", "see #12345"):
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


    def test_square_brackets_are_a_placeholder_only_around_what_could_not_be_a_colour_and_a_function_with_an_ellipsis_is_none(self):
        # round 4: the rule's text said less than the code does; these hold the two to each other
        for cell in ("[hex]", "[note]", "#[hex]", "[to be decided]", "[]", "#[\u2026]", "#...", "\u2026", "-", "\u2014"):
            with self.subTest(cell=cell):
                p = _palette.parse_tables(one(cell))
                self.assertEqual((p.light, p.rows_found, p.problems), ({}, 1, []), "not filled in")
        for cell, code in (("[bad]", "colour-unreadable"), ("[facade]", "colour-unreadable"), ("[FACADE]", "colour-unreadable"), ("[red]", "colour-unreadable"), ("[12]", "colour-unreadable"),
                           ("[#5a5a72]", "palette-not-one-colour"), ("rgba(...)", "colour-unreadable"), ("rgba(...,0.06)", "colour-unreadable"), ("rgb(\u2026)", "colour-unreadable")):
            with self.subTest(cell=cell):
                p = _palette.parse_tables(one(cell))
                self.assertEqual((p.light, codes(p)), ({}, [("light", "muted", code)]))
        # in a line of text the same function is passed over by rule 12's search, and a whole one is named
        p = _palette.parse_tables(pasted() + "\nShadow: 0 8px 24px rgba(...,0.06)\n")
        self.assertEqual(p.problems, [])
        p = _palette.parse_tables(pasted() + "\nShadow: 0 8px 24px rgba(0,0,0,0.06)\n")
        self.assertEqual([c for _t, _k, c in codes(p)], [NOT_READ])

    def test_a_third_cell_that_is_nothing_but_a_second_colour_is_named_and_a_colour_among_the_words_of_a_note_is_a_note(self):
        # round 4: the assistant's instructions say exactly this; held here for a hex and for each function form
        for second in ("#111111", "#111", "#111111ff", "rgb(17, 17, 17)", "rgba(17,17,17,1)", "hsl(0 0% 7%)", "hsla(0, 0%, 7%, 1)", "oklch(0.2 0 0)", "`#111111`",
                       "#11111180", "rgba(17,17,17,0.5)", "oklch(0.7 0.4 150)"):
            with self.subTest(second=second):
                p = _palette.parse_tables(one("#5a5a72 | " + second))
                self.assertEqual((p.light, codes(p)), ({}, [("light", "muted", "palette-two-colours")]), "neither colour is taken")
                p = _palette.parse_tables(one("#5a5a72 | was %s before" % second))
                self.assertEqual((p.light, p.problems), ({"muted": "#5a5a72"}, []), "among the words of a note it is part of the note")
                p = _palette.parse_tables(one("#5a5a72 | - | " + second))
                self.assertEqual(codes(p), [("light", "muted", "palette-two-colours")], "in any later cell")
        # the same colour said again, in any spelling, and a colour name are notes
        for note in ("#5a5a72", "#5A5A72", "rgb(90, 90, 114)", "#5a5a72ff", "navy", "white"):
            with self.subTest(note=note):
                p = _palette.parse_tables(one("#5a5a72 | " + note))
                self.assertEqual((p.light, p.problems), ({"muted": "#5a5a72"}, []))

class Rule6HeaderRowsAndRowsUnderOtherNames(unittest.TestCase):
    """6. The row directly above a separator row is the table's header row, unless its first cell is a
    row name; its second cell must be Hex. Any other row under another name goes to `unused` when a
    cell of it holds a colour, and is passed over when none does."""

    def test_a_header_row_that_calls_the_second_column_hex(self):
        for header in ("| Token | Hex |", "| Token | Hex | Use |", "| Rolle | HEX | Verwendung |", "| | **Hex** |", "| Name | `hex` | Name |", "|Token|Hex|"):
            with self.subTest(header=header):
                p = _palette.parse_tables("### Light theme\n%s\n|---|---|\n" % header + "\n".join(lines(STARTER_LIGHT)) + "\n")
                self.assertEqual((p.light, p.problems, p.ignored), (STARTER_LIGHT, [], []))

    def test_under_any_other_header_a_table_with_colours_is_not_read_and_the_header_is_quoted(self):
        # the Name column before the hex: "| Muted | DimGray | 9a9aa8 |" was read as DimGray, and a failing pair printed as passing
        body = "\n".join("| %s | %s | %s |" % (l, "DimGray" if k == "muted" else "Ours", "9a9aa8" if k == "muted" else STARTER_LIGHT[k]) for k, l in LABELS) + "\n"
        for second, table_ in (("Name", body), ("Colour", body), ("Color", body), ("Value", plain(STARTER_LIGHT).split("\n", 2)[2]), ("HSL", "| Heading | hsl(240, 31%, 13%) | #16162a |\n"),
                               ("Hex code", "| Heading | #16162a |\n"), ("Hex (proposed)", "| Heading | #16162a |\n"), ("#b4531a", "| Heading | #16162a |\n"),
                               ("Background", "| Accent | #2b50e0 | white |\n"), ("Weight", "| Heading | Black |\n"), ("Hexadecimal", "| Muted | #5a5a72 |\n")):
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
                p = _palette.parse_tables(pasted() + before + type_table)
                self.assertEqual(p.problems, [], "a complete palette is not made partial by the type table")
                self.assertEqual((p.missing(), p.light, p.dark), ([], STARTER_LIGHT, STARTER_DARK))
                self.assertEqual(p.ignored, ["Heading", "Body", "Link"])
        # round 3: words made of hex letters and an issue number of five digits were taken for colours, and the table for one of colours
        p = _palette.parse_tables(pasted() + "\n## Type\n| Element | Font |\n|---|---|\n| Heading | Facade Display 700 |\n| Body | decade, see #12345 |\n")
        self.assertEqual((p.problems, p.ignored), ([], ["Heading", "Body"]))

    def test_a_table_with_no_header_row_is_read_and_its_first_row_is_a_row(self):
        for name, md in (("no header", "### Light theme\n" + "\n".join(lines(STARTER_LIGHT)) + "\n"),
                         ("a rule line on top", "### Light theme\n|---|---|\n" + "\n".join(lines(STARTER_LIGHT)) + "\n"),
                         ("three columns", "### Light theme\n" + "\n".join(l + " use |" for l in lines(STARTER_LIGHT)) + "\n"),
                         ("a header line with no rule under it", "### Light theme\n| Token | Hex |\n" + "\n".join(lines(STARTER_LIGHT)) + "\n"),
                         ("any header line with no rule under it", "### Light theme\n| Token | Name |\n" + "\n".join(lines(STARTER_LIGHT)) + "\n")):
            with self.subTest(name=name):
                p = _palette.parse_tables(md)
                self.assertEqual((p.light, p.problems), (STARTER_LIGHT, []))

    def test_a_row_above_a_separator_that_has_a_row_name_is_a_row(self):
        p = _palette.parse_tables("### Light theme\n| Heading | #16162a |\n|---|---|\n| Muted | #5a5a72 |\n")
        self.assertEqual((p.light, p.problems), ({"heading": "#16162a", "muted": "#5a5a72"}, []))

    def test_two_tables_that_stand_together_are_each_read_by_their_own_header(self):
        md = "### Light theme\n" + HEAD + "| Heading | navy |\n| Token | Name |\n|---|---|\n| Muted | Gray |\n" + HEAD + "| Link | blue |\n"
        p = _palette.parse_tables(md)
        self.assertEqual(p.light, {"heading": "#000080", "link": "#0000ff"})
        self.assertEqual(codes(p), [("?", None, "palette-header")])
        self.assertIn("colours for Muted", p.problems[0][3])

    def test_a_row_under_another_name_is_named_when_it_holds_a_colour_written_as_a_value_and_passed_over_when_it_does_not(self):
        md = brand_md().replace("| Heading | `#16162a` |", "| Headings: | `#16162a` |").replace(
            "| Surface (cards) | `#ffffff` |", "| Surface / cards | `#ffffff` |").replace("| Link | `#2b50e0` |", "| --link | `#2b50e0` |")
        p = _palette.parse_tables(md + "| Success | - |\n| Notes | see the guide |\n| Warning | #aa5500 | #ffbb66 |\n| Text | Near Black | `#16162A` |\n"
                                       "| Hover | #1a3fb0 on hover |\n| Glass | rgba(0, 0, 0, 0.5) |\n| Ink | Navy |\n")
        self.assertEqual(p.missing(), [("light", "heading"), ("light", "link"), ("light", "surface")])
        self.assertEqual({c for _t, _k, c in codes(p)}, {NOT_READ})
        messages = of(p, NOT_READ)
        for message, row in zip(messages, ('"| Headings: | `#16162a` |"', '"| --link | `#2b50e0` |"', '"| Surface / cards | `#ffffff` |"', '"| Warning | #aa5500 | #ffbb66 |"',
                                           '"| Text | Near Black | `#16162A` |"')):
            self.assertIn(row, message)
        self.assertEqual(len(messages), 6, "the first five, and a count of the rest")
        self.assertEqual(messages[5], "2 more lines hold a colour that was not read; the next is line 39.")
        self.assertEqual(p.ignored, [], "a row under another name with no colour in it (Success, Notes) has nothing to show")
        self.assertNotIn("Navy", said(p), "the limit of rule 12: a colour name outside a cell that is read is not seen")
        self.assertEqual(_palette.parse_tables(brand_md()).problems, [])

    def test_a_header_row_that_holds_a_colour_is_named_too(self):
        p = _palette.parse_tables("### Light theme\n| Brandfarbe | #b4531a |\n|---|---|\n| Heading | #16162a |\n")
        self.assertEqual(([c for _t, _k, c in codes(p)], p.light), (["palette-header", NOT_READ], {}))
        self.assertIn('Line 2, "| Brandfarbe | #b4531a |", holds a colour (#b4531a) that was not read', of(p, NOT_READ)[0])


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
                p = _palette.parse_tables(pasted() + before + body)
                self.assertEqual((p.problems, p.missing()), ([], []))
                self.assertEqual((p.light, p.dark, p.brand), (STARTER_LIGHT, STARTER_DARK, "#000000"))
                self.assertEqual(p.ignored, ignored)

    def test_a_row_whose_cell_cannot_be_read_is_not_said_to_have_a_value(self):
        # round 2: "has a value but no heading says which theme" was printed for a cell that held no value at all
        p = _palette.parse_tables(HEAD + "| Muted | notacolour |\n")
        self.assertEqual((p.problems, p.ignored), ([], ["Muted"]), "no colour, no section: nothing is claimed of it")
        p = _palette.parse_tables(HEAD + "| Muted | #5a5a72 or so |\n")
        self.assertEqual(codes(p), [("?", None, "palette-no-section")], "a colour among words is spoken of: where the table stands")
        self.assertNotIn("has a value", said(p))
        p = _palette.parse_tables(HEAD + "| Muted | 5a5a72 |\n")
        self.assertEqual((p.problems, p.ignored), ([], ["Muted"]), "the limit of rule 12: hex digits without their # are seen only in a cell that is read")
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
    """9. The mark is the word proposed, proposal or proposals. It is read in the value cell or a later cell of
    a row that is read, and in the bracketed remark of a section's heading. Everywhere else in the text the word
    is a problem that quotes the line: no text that holds it outside a comment passes without a word."""

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
                          ("said not to be", "| Muted | #a6abce | not proposed |"), ("in the plural", "| Muted | #a6abce | one of two proposals |"),
                          ("in the plural, in the value cell", "| Muted | #a6abce (proposals) |"), ("after a hyphen", "| Muted | #a6abce | counter-proposal |")):
            with self.subTest(name=name):
                p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", row))
                self.assertEqual((p.dark["muted"], p.proposed, p.missing(), p.problems), ("#a6abce", {("dark", "muted")}, [], []))
        p = _palette.parse_tables("### Brand\n" + HEAD + "| Primary | #000000 | - | proposed |\n")
        self.assertEqual((p.brand, p.proposed), ("#000000", {("brand", "brand")}))
        # a word that only contains it is not it
        for note in ("unproposed, purposed", "proposer", "re-proposing", "propose", "proposes", "proposition", "proposalsheet"):
            with self.subTest(note=note):
                p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | %s |" % note))
                self.assertEqual((p.proposed, p.problems), (set(), []))

    def test_a_mark_beside_an_empty_value_cell_is_a_proposal_that_is_not_filled_in_and_is_said_to_be(self):
        # round 3: "| Muted | #[…] | proposed |" beside a complete palette: the mark was dropped, and the check ended with 0
        for row in ("| Muted | #[…] | proposed |", "| Muted | | (proposed) |", "| Muted | `#[…]` (proposed) |", "| Muted | (proposed) |", "| Muted | - | - | Proposals |",
                    "| Muted | #... proposed |"):
            with self.subTest(row=row):
                p = _palette.parse_tables(brand_md() + row + "\n")
                self.assertEqual((p.dark, p.proposed), (STARTER_DARK, set()), "the row has no value, so nothing is marked; the value above it stays")
                self.assertEqual(codes(p), [("dark", "muted", "palette-proposal-empty")])
                for part in ("Muted (dark theme): the row is marked as a proposal", "second cell is empty or still the placeholder", "no value to confirm",
                             "not filled in", "Write the proposed colour in the second cell"):
                    self.assertIn(part, p.problems[0][3])
        # the near-miss: an empty row without the word is only not filled in
        p = _palette.parse_tables(brand_md() + "| Muted | #[…] | to be decided |\n")
        self.assertEqual((p.proposed, p.problems), (set(), []))
        # and a row whose cell cannot be read keeps its own problem: with no value there is nothing to mark
        p = _palette.parse_tables(brand_md(dark={}) + HEAD + "| Muted | rgba(0, 0, 0, 0.5) | proposed |\n")
        self.assertEqual((p.proposed, codes(p)), (set(), [("dark", "muted", "colour-alpha")]))

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
        # where BOTH themes have their own, the proposed row under Brand is used by neither: the mark marks nothing, and that is said
        p = _palette.parse_tables(brand_md() + "\n### Brand\n" + HEAD + "| Accent | `#2b50e0` (proposed) |\n")
        self.assertEqual((p.proposed, p.fixed_accent, codes(p)), (set(), set(), [("brand", "accent", MARK)]))
        for part in ("Accent (brand table): the row is marked as a proposal", "neither theme uses it", "marked no value"):
            self.assertIn(part, p.problems[0][3])
        self.assertEqual(_palette.parse_tables(brand_md() + "\n### Brand\n" + HEAD + "| Accent | `#2b50e0` |\n").problems, [], "unmarked, a row nobody uses is only that")

    def test_the_word_in_the_headings_bracketed_remark_marks_every_row_under_it_until_the_next_heading(self):
        every = {("dark", k) for k in STARTER_DARK}
        # round 3: "### Dark theme (proposals)" was read as a heading and its rows as confirmed
        for heading in ("### Dark theme (proposed)", "### Dark theme (Proposal)", "### Dark theme ( PROPOSED )", "### **Dark theme** (*proposed*)",
                        "### Dark theme (proposals)", "### Dark theme (_proposed_)", "### Dark theme (__proposals__)", "### Dark theme(`proposed`)", "### Dark theme (**proposed**) ###"):
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
        # round 4: any other remark was let through, so a mark in the assistant's own language passed as confirmed. See Rule2Sections.
        p = _palette.parse_tables(brand_md().replace("### Dark theme", "### Dark theme (suggested)"))
        self.assertEqual((p.proposed, p.dark, [c for _t, _k, c in codes(p)]), (set(), {}, ["palette-heading-remark"]), "the mark is the one word, and no other remark is read")

    def test_a_heading_whose_mark_marks_no_value_is_named(self):
        # a marked heading with nothing under it, and the same heading again without the mark: the rows would pass as confirmed
        for name, md in (("the heading twice", brand_md().replace("### Dark theme\n", "### Dark theme (proposed)\n\n### Dark theme\n")),
                         ("rows not filled in", brand_md(dark={}).replace("### Dark theme\n", "### Dark theme (proposed)\n") + "| Muted | #[…] |\n"),
                         ("a table that is not read", brand_md(dark={}).replace("### Dark theme\n", "### Dark theme (proposed)\nSoon.\n") + "\nLater:\n" + plain(STARTER_DARK)),
                         ("at the end of the text", brand_md() + "\n### Brand (proposal)\n")):
            with self.subTest(name=name):
                p = _palette.parse_tables(md)
                self.assertEqual(p.proposed, set())
                self.assertIn(("?", None, MARK), codes(p))
                for part in ("the heading \"### ", "carries the mark (proposed)", "no row under it has a value that was read", "marked no value"):
                    self.assertIn(part, of(p, MARK)[0])

    WHERE_IT_IS_NOT_READ = (
        # round 2: a line between heading and table, a footnote, a heading above the three, the header row
        ("a line between the heading and the table", "### Dark theme\n", "### Dark theme\n\n*Proposed, not yet confirmed*\n\n", '"*Proposed, not yet confirmed*"'),
        ("a sentence under the heading", "### Dark theme\n", "### Dark theme\nThese dark values are a proposal; please confirm.\n", '"These dark values are a proposal; please confirm."'),
        ("a heading above the three", "## Colours", "## Proposed colours", '"## Proposed colours"'),
        ("the header row", "### Dark theme\n| Token | Hex |", "### Dark theme\n| Token | Hex | Status: proposed |", '"| Token | Hex | Status: proposed |"'),
        # round 3: each of these was read as confirmed, and the check ended with 0
        ("a sentence under the heading above the three", "## Colours\n", "## Colours\n\nThe dark values below are proposed; the owner has not confirmed them.\n",
         '"The dark values below are proposed; the owner has not confirmed them."'),
        ("a sentence before the first heading", "# Example Bakery", "Here are three proposed palettes.\n\n# Example Bakery", '"Here are three proposed palettes."'),
        ("a heading beside the three", "### Brand (fixed", "### Proposed dark values\n\n### Brand (fixed", '"### Proposed dark values"'),
        ("a row under another name", "### Dark theme\n| Token | Hex |\n|---|---|\n", "### Dark theme\n| Token | Hex |\n|---|---|\n| Status | proposed |\n", '"| Status | proposed |"'),
        ("the first cell of a row", "| Muted | `#a6abce` |", "| Muted | `#a6abce` |\n| proposed | yes |", '"| proposed | yes |"'),
        ("a list line", "### Dark theme\n", "### Dark theme\n- status: proposal\n", '"- status: proposal"'),
        ("the plural in a sentence", "### Dark theme\n", "### Dark theme\nThese are proposals.\n", '"These are proposals."'),
        ("a heading with the word between two of the three", "### Light theme\n", "## Proposal B\n\n### Light theme\n", '"## Proposal B"'),
        ("a sentence under a later heading", "\x00", "\x00\n## Notes\n\nAll dark values are PROPOSED.\n", '"All dark values are PROPOSED."'),
        ("a closing sentence", "\x00", "\x00\nLet me know if you would like me to adjust any of these proposed colours!\n", '"Let me know if you would like me to adjust any of these proposed colours!"'),
        ("a row of a table under another heading", "\x00", "\x00\n## Type\n| Element | Font |\n|---|---|\n| Heading | proposed: Inter |\n", '"| Heading | proposed: Inter |"'),
    )

    def test_the_word_anywhere_else_marks_nothing_and_is_named_with_its_line(self):
        # (a text with no `Colour palette` heading: all of it is the palette. Rule 0's class has the other side.)
        whole = "# Example Bakery\n\n## Colours\n\n" + pasted() + "\x00"
        for name, old, new, quote in self.WHERE_IT_IS_NOT_READ:
            with self.subTest(name=name):
                md = whole.replace(old, new)
                self.assertNotEqual(md, whole)
                p = _palette.parse_tables(md.replace("\x00", ""))
                self.assertEqual((p.proposed, p.light, p.dark, p.brand), (set(), STARTER_LIGHT, STARTER_DARK, "#000000"), "it marked nothing, and nothing else changed")
                self.assertEqual(codes(p), [("?", None, MARK)])
                number = md.replace("\x00", "").splitlines().index(quote.strip('"')) + 1
                word = _palette._mark_in(quote)[2]
                for part in ("Line %d, %s, holds the word \"%s\"" % (number, quote, word), "`| Muted | #a6abce (proposed) |`", "`### Dark theme (proposed)`", "marked no value",
                             "take the word out of that line", "inside a comment (`<!-- ... -->`)"):
                    self.assertIn(part, p.problems[0][3])

    def test_the_word_in_a_place_where_something_else_is_wrong_too_is_named_beside_that(self):
        # in the header's second cell the table is not read at all; a heading that is not one of the three files nothing
        p = _palette.parse_tables(brand_md().replace("### Dark theme\n| Token | Hex |", "### Dark theme\n| Token | Hex (proposed) |"))
        self.assertEqual((p.dark, p.proposed, [c for _t, _k, c in codes(p)]), ({}, set(), ["palette-header", MARK]))
        p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", "| Muted (proposed) | `#a6abce` |"))
        self.assertEqual((p.proposed, p.missing(), [c for _t, _k, c in codes(p)]), (set(), [("dark", "muted")], [MARK, NOT_READ]))
        for heading in ("### Dark theme proposals", "### Proposal: dark theme", "### Dark theme, proposed", "### Dark theme [proposed]", "### Dark theme (proposed", "### Dark theme - proposed"):
            with self.subTest(heading=heading):
                p = _palette.parse_tables(brand_md().replace("### Dark theme", heading))
                self.assertEqual((p.dark, p.proposed, [c for _t, _k, c in codes(p)]), ({}, set(), ["palette-no-section", MARK]))
        # a row that is not read holds it beside its colour: the table's problem names the row, and the word is named for itself
        p = _palette.parse_tables("## Colours\n" + HEAD + "| Muted | #a6abce (proposed) |\n")
        self.assertEqual([c for _t, _k, c in codes(p)], ["palette-no-section", MARK])

    def test_the_word_inside_a_comment_is_not_looked_at_and_the_near_misses_of_the_word_are_no_marks(self):
        md = ("<!-- The designer proposed three palettes; this is the one we chose. -->\n\n" + pasted()
              + "\n## Notes\n\nWe propose a serif face next year. The proposer was unproposed.\n\n<!--\n### Proposed changes\n-->\n")
        p = _palette.parse_tables(md)
        self.assertEqual((p.proposed, p.problems), (set(), []))

    def test_the_first_five_such_lines_are_quoted_and_the_rest_are_counted(self):
        p = _palette.parse_tables(brand_md() + "".join("\nNote %d: proposed.\n" % n for n in range(8)))
        messages = of(p, MARK)
        self.assertEqual((len(messages), len(p.problems)), (6, 6))
        self.assertIn("put the mark in one of those places", messages[0])
        for n, message in enumerate(messages[1:5], 1):
            self.assertEqual(message, 'Line %d, "Note %d: proposed.", holds the word "proposed" where this check does not read it as a mark either, so it marked no value there.'
                             % (36 + 2 * n, n))
        self.assertEqual(messages[5], 'The word "proposed" (or "proposal") stands on 3 more lines where it is not read as a mark; the next is line 46.')
        p = _palette.parse_tables(brand_md() + "".join("\nNote %d: proposed.\n" % n for n in range(6)))
        self.assertIn("stands on 1 more line where", of(p, MARK)[5])

    def test_a_long_line_is_quoted_around_the_word(self):
        # round 3: the quote was the first 60 characters of the line, and the word the sentence is about came after them
        line = "This palette was put together in March, after two rounds with the printer, and its dark half is still only proposed by the studio, who will write again."
        p = _palette.parse_tables(brand_md() + "\n" + line + "\n")
        self.assertIn('"...er, and its dark half is still only proposed by the studio, who will write again..."', p.problems[0][3])


    EMPHASIS = ("_proposed_", "__proposed__", "*proposed*", "**proposed**", "`proposed`", "(_proposed_)", "~~proposed~~", "_proposal_", "__proposals__", "__Proposed__",
                "proposed_palette", "proposed\u00b2", "proposed\u00b9", "PROPOSED\u2082", "_proposed", "proposed_", "proposed\u2460", "~~proposal~~\u00b3", "(~~proposed~~)",
                "(proposed\u00b2)", "~proposed~", "**~~proposed~~**", "(proposed)\u00b9", "proposed\u00bd")
    # which of them is the mark after a colour and the whole of a heading's remark: the word with nothing joined to it
    AS_A_MARK = re.compile("\\(?[*_`~]*propos(ed|als?)[*_`~\u00b2\u00b9\u00b3\u2082\u2460\u00bd]*\\)?[\u00b9]?", re.I)

    def test_the_word_with_emphasis_or_an_underscore_or_a_footnote_figure_beside_it_is_the_word_wherever_it_stands(self):
        # round 4: `| Muted | #a6abce | _proposed_ |` was read as confirmed and the check ended with 0, because an underscore
        # counted as a letter of the word. Promise 3: in each place the word is read as a mark, or a problem names it.
        marked = {("dark", "muted")}
        for word in self.EMPHASIS:
            with self.subTest(word=word, where="a later cell"):
                p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | %s |" % word))
                self.assertEqual((p.dark["muted"], p.proposed, p.problems), ("#a6abce", marked, []))
            with self.subTest(word=word, where="the value cell"):
                p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` %s |" % word))
                if self.AS_A_MARK.fullmatch(word):
                    self.assertEqual((p.dark["muted"], p.proposed, p.problems), ("#a6abce", marked, []), "emphasis around the mark is not counted")
                else:
                    self.assertEqual((p.dark.get("muted"), p.proposed, codes(p)), (None, set(), [("dark", "muted", "palette-not-one-colour")]), "the row is named, and has no value")
            with self.subTest(word=word, where="a heading's brackets"):
                p = _palette.parse_tables(brand_md().replace("### Dark theme", "### Dark theme (%s)" % word.replace("(", "").replace(")", "")))
                if self.AS_A_MARK.fullmatch(word):
                    self.assertEqual((p.proposed, p.problems), ({("dark", k) for k in STARTER_DARK}, []))
                else:
                    self.assertEqual((p.proposed, p.dark, [c for _t, _k, c in codes(p)]), (set(), {}, ["palette-heading-remark", MARK]))
            for where, md in (("a sentence", brand_md() + "\nThe dark values are %s still.\n" % word), ("a heading", brand_md() + "\n#### Notes %s\n" % word),
                              ("a list", brand_md() + "\n- %s\n" % word), ("the first cell of a row", brand_md() + "| %s | yes |\n" % word),
                              ("a header row", brand_md().replace("### Dark theme\n| Token | Hex |", "### Dark theme\n| Token | Hex | %s |" % word))):
                with self.subTest(word=word, where=where):
                    p = _palette.parse_tables(md)
                    self.assertEqual((p.proposed, [c for _t, _k, c in codes(p)]), (set(), [MARK]))
                    self.assertIn('holds the word "%s"' % re.search("propos[a-z]+", word, re.I).group().lower(), p.problems[0][3])
        # a letter or a digit joined to it makes another word, in a note and in a sentence alike
        for word in ("proposed1", "1proposed", "proposed2nd", "unproposed", "proposedly", "\u00e9proposed", "proposed\u00e9", "_unproposed_", "proposals3"):
            with self.subTest(word=word):
                p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | %s |" % word) + "\nA %s line.\n" % word)
                self.assertEqual((p.proposed, p.problems), (set(), []))

    def test_the_word_with_a_character_inside_it_that_nobody_sees_is_the_word(self):
        # round 5: `prop` + a soft hyphen + `osed` in a note cell or a sentence was no word to the search, and the check ended with 0
        marked = {("dark", "muted")}
        # round 6: what is taken out is four of Unicode's categories and nothing else. Cf (the first six), Cc (a NUL, another control character, a
        # delete, one of the upper controls), Mn (a variation selector, the grapheme joiner, the strokes that "strike-through text" tools write) and Me
        # round 7 (R7-201): U+001F is a control character like the others, and Python's split() takes it for a blank: the line's blanks were
        # folded with it before this pass ran, so the word was cut in two. (The other characters split() takes for one and nobody sees end a
        # line to this reader: the limit below.)
        for hidden in ("\u00ad", "\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\x00", "\x01", "\x7f", "\x9b", "\ufe0f", "\u034f", "\u0336", "\u0332", "\u20dd", "\x1f"):
            for word in ("prop%sosed" % hidden, "%sproposed" % hidden, "proposed%s" % hidden, "p%sr%so%sposal" % (hidden, hidden, hidden), "PROP%sOSALS" % hidden):
                with self.subTest(word=word, where="a later cell"):
                    p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | %s |" % word))
                    self.assertEqual((p.dark["muted"], p.proposed, p.problems), ("#a6abce", marked, []))
                with self.subTest(word=word, where="a sentence"):
                    p = _palette.parse_tables(brand_md() + "\nThe dark values are %s still.\n" % word)
                    self.assertEqual((p.proposed, [c for _t, _k, c in codes(p)]), (set(), [MARK]))
                    self.assertIn('holds the word "propos', p.problems[0][3])
                with self.subTest(word=word, where="the value cell"):
                    p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` %s |" % word))
                    self.assertIn(p.proposed, (marked, set()))
                    if not p.proposed:  # (the word with the character at its end is the mark after the colour only where that character is one the cell is trimmed of)
                        self.assertEqual(codes(p), [("dark", "muted", "palette-not-one-colour")])
        # the whole word struck through, as such a tool writes it, and a figure that is no digit beside the word
        for word in ("p\u0336r\u0336o\u0336p\u0336o\u0336s\u0336e\u0336d\u0336", "proposed\u2460", "\u24b6 proposed\u00b2\u00b3", "pro\ufe0f\u200b\x01posed", "proposed&#49;", "&nbsp;proposed&nbsp;"):
            with self.subTest(word=word):
                p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | %s |" % word) + "\nNote: %s.\n" % word)
                self.assertEqual((p.proposed, [c for _t, _k, c in codes(p)]), (marked, [MARK]))
        # where the line is quoted, what does not show is written out, and the sentence says so
        p = _palette.parse_tables(brand_md() + "\nThe dark values are prop\u00adosed still.\n")
        for part in ('"The dark values are prop<U+00AD>osed still."', 'holds the word "proposed"', "is a character that does not show on the screen: take it out"):
            self.assertIn(part, p.problems[0][3])
        # the near-misses stay near-misses when seen that way: a letter or a digit joined to the word, also a wide one
        for word in ("unprop\u00adosed", "proposed\uff11", "\uff55\uff4eproposed", "prop\u00adosedly", "proposed\u0661", "un\u0336proposed", "proposed\ufe0fly"):
            with self.subTest(word=word):
                p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | %s |" % word) + "\nA %s line.\n" % word)
                self.assertEqual((p.proposed, p.problems), (set(), []))
        # rule 9's stated limits, none of which is seen through: emphasis or a tag INSIDE the word, a look-alike letter of another script, and
        # (round 6, where resolving them was a traceback and a stall) a character reference and a wide or mathematical letter. (Round 9: a
        # character that this reader takes for the end of a line is no limit any more: the eight words that stood here, `pro\x0bposed` to
        # `pro\u2029posed`, are in Rule9ALineEndThatIsNoPlainNewLine below, where the text that holds one is not read.)
        for word in ("**pro**posed", "pro_posed", "\u0440roposed", "prop\u03bfsed", "pro<b>posed</b>", "<i>p</i>roposed", "&#112;roposed", "propose&#x64;", "&#80;ROPOSED", "prop&shy;osed",
                     "prop&#173;osed", "prop&#x200B;osed", "prop&zwnj;osed", "\uff50\uff52\uff4f\uff50\uff4f\uff53\uff45\uff44", "\U0001d429roposed", "&#" + "9" * 5000 + ";roposed",
                     # R7-206: a character nobody sees that Unicode files under another category than the four: a filler filed as a letter,
                     # a private-use character, one that is not assigned; and (R9, rule 1) a thin blank, which makes two words of it
                     "pro\u115fposed", "pro\u1160posed", "pro\u3164posed", "pro\uffa0posed", "pro\ue000posed", "pro\u2065posed", "pro\u200aposed", "pro\u2009posed", "pro\u202fposed"):
            with self.subTest(word=word[:30]):
                p = _palette.parse_tables(brand_md() + "\nA %s line.\n" % word)
                self.assertEqual((p.proposed, p.problems), (set(), []))
        # R7-206: the pass follows the Unicode tables of the Python that runs it. U+180F is a mark since Unicode 14 and U+13439 a format
        # character since 15: a Python that knows them takes them out, an older one passes the word over
        import unicodedata
        for hidden in ("\u180f", "\U00013439"):
            with self.subTest(hidden=hidden):
                known = unicodedata.category(hidden) in ("Cf", "Cc", "Mn", "Me")  # (Python 3.13: yes for both; 3.9: for neither)
                p = _palette.parse_tables(brand_md() + "\nA pro%sposed line.\n" % hidden)
                self.assertEqual([c for _t, _k, c in codes(p)], [MARK] if known else [])
        # in the VALUE cell none of these is passed over: whatever stands beside the colour there makes the cell one that cannot be read
        for word in ("prop\u00adosed", "&#112;roposed", "\uff50\uff52\uff4f\uff50\uff4f\uff53\uff45\uff44", "**pro**posed", "proposed \u00b2", "p\u0336roposed"):
            with self.subTest(word=word, where="the value cell"):
                p = _palette.parse_tables(brand_md().replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` %s |" % word))
                self.assertEqual((p.dark.get("muted"), p.proposed, codes(p)), (None, set(), [("dark", "muted", "palette-not-one-colour")]))
        # R6-208: in a heading's remark a strike-through or a figure INSIDE the word makes it another remark; beside the word they are not counted
        for remark, mark in (("pro~posed", False), ("pro~~pos~~ed", False), ("pro\u00b2posed", False), ("p~roposed~", False), ("~~proposed~~", True), ("proposed\u00b2", True),
                             (" ~proposed~ ", True), ("proposed \u00b2\u00b3", True), ("~~proposal~~\u00b9", True)):
            with self.subTest(remark=remark):
                p = _palette.parse_tables(brand_md().replace("### Dark theme", "### Dark theme (%s)" % remark))
                if mark:
                    self.assertEqual((p.proposed, p.problems), ({("dark", k) for k in STARTER_DARK}, []))
                else:
                    self.assertEqual((p.proposed, p.dark, [c for _t, _k, c in codes(p)]), (set(), {}, ["palette-heading-remark"]))
        # (emphasis marks are taken out of a heading wherever they stand, rule 2, so there the word with emphasis inside it is the mark: it errs towards asking)
        p = _palette.parse_tables(brand_md().replace("### Dark theme", "### Dark theme (**pro**posed)"))
        self.assertEqual((p.proposed, p.problems), ({("dark", k) for k in STARTER_DARK}, []))


class Rule9ALineEndThatIsNoPlainNewLine(unittest.TestCase):
    """9, its refusal (round 9). This reader cuts a text into lines with `str.splitlines()`, which ends a line at eight
    characters beside the line feed and the carriage return; a Markdown reader ends a line at none of the eight. One of
    them inside the word made two lines of it: the word was not seen, and the check ended with 0 on a proposal. A text
    that holds one, anywhere, is not read: ONE problem gives the number of the first line that holds one, as an editor
    counts it, and the character's code point. A text that holds none is read as before."""

    def refused(self, text, number, c, more=0, kinds=""):
        """Nothing of the text is read, and the one problem names this line (counted as an editor counts) and this character, and
        says that the tables may be fine as they are."""
        p = _palette.parse_tables(text)
        self.assertEqual((p.light, p.dark, p.brand, p.proposed, p.ignored, p.fixed_accent, p.rows_found), ({}, {}, None, set(), [], set(), 0))
        self.assertEqual(codes(p), [("?", None, LINE_END)])
        message = p.problems[0][3]
        self.assertTrue(message.startswith("Line %d, \"" % number), message)
        self.assertIn("<U+%04X>" % ord(c), message.partition(", holds a character that this check takes for the end of a line and a Markdown reader does not (")[0])
        self.assertIn("does not (U+%04X, written as <U+%04X> in the quote). " % (ord(c), ord(c)), message)
        self.assertEqual(message.count(" more character"), 1 if more else 0)
        if more:
            self.assertIn(" The text holds %d more character%s of that kind%s. " % (more, "" if more == 1 else "s", kinds and " (%s)" % kinds), message)
        self.assertIn(" so it read nothing of this text: its tables were not looked at, and may be fine as they are.", message)
        self.assertTrue(message.endswith(" Delete each such character, or put a plain new line in its place, then check again."), message)
        return message

    @staticmethod
    def line(text, part):
        """The number of the line of a text with plain new lines on which `part` begins."""
        return text[:text.index(part)].count("\n") + 1

    def test_the_eight_are_every_character_at_which_this_reader_ends_a_line_and_a_markdown_reader_does_not(self):
        # the refusal closes the gap only if it knows every such character: asked of the Python that runs this, for every code point
        ends = [chr(n) for n in range(sys.maxunicode + 1) if len(("a%sb" % chr(n)).splitlines()) == 2]
        self.assertEqual(sorted(ends), sorted(("\n", "\r") + LINE_ENDS))
        self.assertEqual(sorted(_palette._BREAKS), sorted(ends))
        self.assertEqual([c for c in ends if _palette._OTHER_BREAK.search(c)], sorted(LINE_ENDS))
        self.assertEqual(_palette._OTHER_BREAK.pattern, "[%s]" % "".join(LINE_ENDS), "and the pattern holds nothing else")
        # so a text that is read has the lines an editor shows: cut at \r\n, \n and \r, and nowhere else
        text = brand_md().replace("### Light", "### Light\r").replace("| Muted |", "| Muted |\r\n") + "\x1f \u00a0\u200b"
        self.assertIsNone(_palette._other_line_end(text))
        self.assertEqual(text.splitlines(), _palette._PLAIN_BREAK.split(text))

    def test_each_of_the_eight_in_each_place_is_the_one_problem_with_the_number_of_its_line(self):
        good = brand_md()
        guide = good + "\n## Type\n\nInter, 700.\n"
        row = "| Muted | `#a6abce` |"
        # (what the place is called; the text, with %s where the character goes; what the line it goes on holds, or the line so many
        # lines above it; whether the text without the character is the whole palette, read without a problem)
        places = (
            # the finding: the word on two lines was no word, in a sentence and in a note cell, and the check ended with 0 on a proposal
            ("inside the word, in a sentence", good + "\nAll dark values are pro%sposed.\n", "All dark", 0, False),
            ("inside the word, in a note cell", good.replace(row, row + " pro%sposed |"), row, 0, False),
            ("inside the mark after a value", good.replace(row, "| Muted | `#a6abce` (pro%sposed) |"), "| Muted | `#a6abce` (", 0, False),
            ("inside the mark of a heading", good.replace("### Dark theme", "### Dark theme (pro%sposed)"), "### Dark theme", 0, False),
            # a value cut in two was read as another colour: `#a6a` is a colour too
            ("inside a value", good.replace(row, "| Muted | #a6a%sbce |"), "| Muted | #a6a", 0, True),
            ("inside a row's name", good.replace(row, "| Mu%sted | `#a6abce` |"), "| Mu%sted", 0, True),
            ("between two rows, where the new line would be", good.replace(row + "\n", row + "%s"), row, 0, False),
            ("between two rows, on a line of its own", good.replace(row + "\n", row + "\n%s\n"), row, 1, True),
            ("at the end of a row's line", good.replace(row, row + "%s"), row, 0, True),
            ("at the end of a heading's line", good.replace("### Dark theme", "### Dark theme%s"), "### Dark theme", 0, True),
            ("between the # and the words of a heading", good.replace("### Dark theme", "###%sDark theme"), "###%sDark theme", 0, False),
            ("in a line of mood text", good.replace("### Dark theme\n", "### Dark theme\n\nWarm paper,%sdark ink.\n\n"), "Warm paper", 0, True),
            ("inside the name of the other theme, between a heading and its table", good.replace("### Light theme\n", "### Light theme\nDa%srk mode\n"), "Da%srk mode", 0, False),
            ("the first character of the text", "%s" + good, "# Example", 0, True),
            ("the last character of the text", good + "%s", "| Surface (cards) | `#161836` |", 1, True),
            # everywhere, which is wider than the rest of rule 9: where the lines are not the text's, where the part under `## Colour palette`
            # ends cannot be trusted either, and a blanked comment keeps its line breaks
            ("above the part under `## Colour palette`", good.replace("# Example Bakery", "# Example%sBakery"), "# Example", 0, True),
            ("below that part", guide.replace("Inter, 700.", "Inter,%s700."), "Inter,", 0, True),
            # (this one ended with 0 too: the reader took `## Notes` for a heading that ends the part, and the sentence after it for none of its business)
            ("before what then reads as a heading that ends that part", good + "\nA note.%s## Notes\n\nAll dark values are still proposed.\n", "A note.", 0, False),
            ("inside a comment", good + "\n<!-- a note%sover two lines -->\n", "<!-- a note", 0, True),
            ("inside a comment that is never closed", good + "\n<!-- a note%s\n", "<!-- a note", 0, False),
        )
        for name, text, part, down, _whole in places:
            self.assertEqual(text.count("%s"), 1, name)
            for c in LINE_ENDS:
                with self.subTest(name=name, c="U+%04X" % ord(c)):
                    self.refused(text % c, self.line(text, part) + down, c)
        # the same text without the character is the palette, read: the refusal is about the character and nothing else
        for name, text, _part, _down, whole in places:
            if whole:
                with self.subTest(name=name, c="none"):
                    p = _palette.parse_tables(text % "")
                    self.assertEqual((p.light, p.dark, p.brand, p.rows_found, p.problems), (STARTER_LIGHT, STARTER_DARK, "#000000", 19, []))

    def test_what_rules_2_and_9_stated_as_a_limit_until_round_9_is_refused(self):
        # the seven lines that test_no_line_of_text_under_a_heading_files_its_table_elsewhere had as passed over, and the eight words that
        # test_the_word_with_a_character_inside_it_that_nobody_sees_is_the_word had: each was read with no problem at all
        for prose in ("Da\x0brk mode", "Da\u2028rk theme", "Da\x1crk theme", "Da\x1drk", "Da\x1erk mode", "Da\x85rk theme", "D\u2028ark mode"):
            with self.subTest(prose=prose):
                self.refused("### Light theme\n%s\n" % prose + plain(STARTER_LIGHT), 2, next(c for c in prose if c in LINE_ENDS))
        last = brand_md().count("\n") + 2
        for word in ("pro\x0bposed", "pro\x0cposed", "pro\x1cposed", "pro\x1dposed", "pro\x1eposed", "pro\x85posed", "pro\u2028posed", "pro\u2029posed"):
            with self.subTest(word=word):
                message = self.refused(brand_md() + "\nA %s line.\n" % word, last, word[3])
                self.assertIn('Line %d, "A pro<U+%04X>posed line.", holds' % (last, ord(word[3])), message)
        # what nobody sees and ends no line stays what it was: the word with U+001F inside it is the word, and is named as one
        p = _palette.parse_tables(brand_md() + "\nA pro\x1fposed line.\n")
        self.assertEqual((p.light, p.dark, [code for _t, _k, code in codes(p)]), (STARTER_LIGHT, STARTER_DARK, [MARK]))

    def test_the_number_is_the_one_an_editor_shows_whatever_ends_the_lines(self):
        good = brand_md()
        row = "| Muted | `#a6abce` |"
        number = self.line(good, row)
        self.assertEqual(number, 28)
        for name, end in (("plain new lines", "\n"), ("Windows line ends", "\r\n"), ("old Mac line ends", "\r")):
            for c in LINE_ENDS:
                with self.subTest(name=name, c="U+%04X" % ord(c)):
                    self.refused(good.replace(row, row + " pro%sposed |" % c).replace("\n", end), number, c)
                    self.refused("\ufeff" + good.replace(row, row + c).replace("\n", end), number, c)
        # the three mixed, a carriage return straight before the character, and the character between a carriage return and a line feed
        for name, text, want in (("mixed line ends", "one\r\ntwo\rthree\n\nfive %s\n", 5), ("after a carriage return", "one\r%stwo\n", 2), ("after a Windows line end", "one\r\n%stwo\n", 2),
                                 ("between a carriage return and a line feed", "one\r%s\nthree\n", 2), ("on the only line", "one %s", 1), ("alone", "%s", 1)):
            for c in LINE_ENDS:
                with self.subTest(name=name, c="U+%04X" % ord(c)):
                    self.refused(text % c, want, c)
        # what this reader's own count of lines would have said, which is not the editor's: the fifth of those characters is on line 1
        self.assertEqual(len(("\x0b\x0c\x1c\x1d" + "\x1e").splitlines()), 5)
        self.refused("\x0b\x0c\x1c\x1d\x1e", 1, "\x0b", more=4, kinds="U+000C, U+001C, U+001D, U+001E")

    def test_the_first_one_is_named_and_the_others_are_counted(self):
        good = brand_md()
        # R9-205: where another kind is among the others, they are named by their code points (each once, in the order they stand)
        self.refused(good.replace("### Light theme", "### Light theme\u2028").replace("### Dark theme", "### Dark\x0b theme"), 10, "\u2028", more=1, kinds="U+000B")
        self.refused(good.replace("### Light theme", "### Light theme\x0b").replace("### Dark theme", "### Dark\u2028 theme\x85") + "\x0c\u2028", 10, "\x0b", more=4,
                     kinds="U+2028, U+0085, U+000C")
        self.refused("| Muted | #5a5a72 |\x1e\x1e\x1e\n", 1, "\x1e", more=2)
        self.refused("| Muted | #5a5a72 |\x1e\x0b\x1e\n", 1, "\x1e", more=2, kinds="U+000B, U+001E")
        # R9-205: in a comment the quote is the line as written, not the blanks the reading puts there (a byte order mark is not quoted)
        for text, number, quote in (("A\n<!-- a pro\u2028posed note -->\n", 2, "<!-- a pro<U+2028>posed note -->"), ("\ufeff<!-- x\x0c -->", 1, "<!-- x<U+000C> -->"),
                                    ("a <!-- b\nc\u2029 --> d", 2, "c<U+2029> --> d")):
            self.assertIn('Line %d, "%s", holds' % (number, quote), self.refused(text, number, next(ch for ch in text if ch in LINE_ENDS)))
        # the whole sentence, once: the line, cut around the character where the line is long, with the character written out
        self.assertEqual(self.refused("### Light theme\n" + HEAD + "| Muted | #5a5a72 | still pro\u2028posed |\n\nA line\x0bmore.\n", 4, "\u2028", more=1, kinds="U+000B"),
                         'Line 4, "| Muted | #5a5a72 | still pro<U+2028>posed |", holds a character that this check takes for the end of a line and a Markdown reader does not '
                         "(U+2028, written as <U+2028> in the quote). This check would begin a new line there where the text has none, which can cut a word or a value in "
                         "two, so it read nothing of this text: its tables were not looked at, and may be fine as they are. The text holds 1 more character of that kind "
                         "(U+000B). Delete each such character, or put a plain new line in its place, then check again.")
        message = self.refused("### Light theme\n" + "x" * 3000 + "\x85" + "y" * 3000 + "\n", 2, "\x85")
        self.assertIn('Line 2, "...%s<U+0085>%s...", holds' % ("x" * 39, "y" * 40), message)
        # with it, nothing else is said of the text, and nothing is raised: not the comment that is never closed, not two palettes pasted together
        self.refused(good + "\n<!-- later\x0c\n### Dark theme\n| Muted | #777777 |\n", good.count("\n") + 2, "\x0c")
        twice = pasted() + pasted().replace("#a6abce", "#777777")
        with self.assertRaises(Refusal):
            _palette.parse_tables(twice)
        self.refused(twice + "\x1d", twice.count("\n") + 1, "\x1d")

    def test_a_file_with_windows_or_old_mac_line_ends_and_none_of_the_eight_is_read_as_the_same_file_with_plain_new_lines(self):
        def whole(text):
            p = _palette.parse_tables(text)
            return p.light, p.dark, p.brand, p.proposed, p.problems, p.ignored, p.fixed_accent, p.rows_found
        texts = (("the palette", brand_md()), ("a brand guide filled in", filled_guide()), ("the pasted tables", pasted()),
                 ("a colour and the word where they are not read", brand_md() + "\nOur ink is #16162a.\n\nStill proposed.\n"),
                 ("a mark on a row and one on a heading", brand_md(dark=dict(STARTER_DARK, muted="#a6abce (proposed)")).replace("### Light theme", "### Light theme (proposed)")),
                 ("a comment over three lines and one that is never closed", brand_md().replace("### Dark theme", "<!-- a\nnote\nhere -->\n### Dark theme") + "\n<!-- later\n| Fancy | #123456 |\n"),
                 ("a table in a code block", pasted().replace("### Dark theme", "```\n### Dark theme") + "```\n"))
        for name, text in texts:
            want = whole(text)
            self.assertNotIn(LINE_END, [code for _t, _k, code, _m in want[4]])
            for end in ("\r\n", "\r"):
                with self.subTest(name=name, end=repr(end)):
                    self.assertEqual(whole(text.replace("\n", end)), want, "the values, and every problem with its line number and its quote")
        self.assertEqual(whole(texts[0][1])[:3], (STARTER_LIGHT, STARTER_DARK, "#000000"))
        self.assertEqual([code for _t, _k, code, _m in whole(texts[3][1])[4]], [MARK, NOT_READ])

    def test_no_megabyte_with_such_characters_makes_the_refusal_slow(self):
        for name, text, number in (("a megabyte of them", "\u2028" * 1000000, 1), ("one at the end of a line of a megabyte", "x" * 1000000 + "\x0b", 1),
                                   ("one after 300,000 short lines", "| a | b |\n" * 300000 + "\x1c", 300001), ("one in each of 100,000 lines", "pro\x85posed\r\n" * 100000, 1)):
            with self.subTest(name=name):
                start = time.process_time()
                p = _palette.parse_tables(text)
                took = time.process_time() - start
                self.assertLess(took, 1.0, "the refusal took %.2f s of processor time" % took)
                self.assertEqual(codes(p), [("?", None, LINE_END)])
                self.assertTrue(p.problems[0][3].startswith("Line %d, " % number), p.problems[0][3][:60])

    def test_the_rule_says_so_and_states_it_as_no_limit_any_more(self):
        rules = " ".join(_palette.parse_tables.__doc__.split())
        for part in ("A WHOLE text that holds, anywhere (outside the part rule 0 names and inside a comment too), a character that this reader takes for the end of a line and a "
                     "Markdown reader does not (a vertical tab U+000B, a form feed U+000C, U+001C, U+001D, U+001E, U+0085, U+2028, U+2029), which would cut a line in two and a "
                     "word on it, is not read: ONE problem (`palette-line-end`) quotes the first line that holds one, with its number as an editor counts it (by line feeds and "
                     "carriage returns alone), names the character by its code point, says how many more the text holds (by code point, where another is among them) and "
                     "what to do (delete each, or put a plain new line in its place), and no row and no value is returned.",
                     "And a text that holds a line-end character other than a plain new line is not read at all, wherever in it that character stands: rule 9.",
                     "Two things outside it are named: rule 9's line-end characters, and, so that a palette written in the wrong place",
                     "a blank of rule 1, also a thin one (U+2009, U+200A, U+202F), which makes two words of it;",
                     "nothing inside one is named (but for rule 9's line-end characters, which are line breaks inside a comment too)"):
            self.assertIn(part, rules)
        for limits in (rules[rules.index("THE LIMITS of the label test."):rules.index("Two things go the other way")],
                       rules[rules.index("THE LIMITS. Each of these inside the word"):rules.index("The mark is read in three places")]):
            self.assertNotIn("end of a line", limits)
            self.assertNotIn("U+2028", limits)


class Rule10NothingIsReadFromAnywhereElse(unittest.TestCase):
    """10. No table with a Light and a Dark column, no column of names, no tolerance between two
    spellings of a colour, no labels, no names beyond rule 4's."""

    COMBINED = "\n".join("| %s | %s | %s |" % (l, STARTER_LIGHT[k], STARTER_DARK[k]) for k, l in LABELS) + "\n"

    def test_a_table_whose_header_names_both_themes_is_a_problem_and_is_not_read(self):
        # round 3: under a header whose second cell said Hex, a Light and a Dark column were let through
        for header in ("| Token | Light | Dark |", "| Token | Light theme | Dark theme |", "| Token | Light / Dark | Use |", "| Token | Light and dark | Use |",
                       "| Token | LIGHT | DARK | Notes |", "| Token | Dark | Light |", "| Token | Hex | Light | Dark |", "| Token | Hex | Dark | Light |",
                       "| Light | Hex | Dark |", "| Token | Hex | **Light** and `dark` |"):
            for heading in ("", "## Colours\n", "### Light theme\n", "### Dark theme\n"):
                with self.subTest(header=header, heading=heading):
                    p = _palette.parse_tables(heading + header + "\n|---|---|---|\n" + self.COMBINED)
                    self.assertEqual((p.light, p.dark, p.brand, p.rows_found), ({}, {}, None, 0))
                    self.assertEqual(codes(p), [("?", None, "palette-combined-table")])
                    for part in ("names both themes", header.strip("| "), "give each theme its own table", "`### Light theme`", "`### Dark theme`", "`| Token | Hex |`", "was not read"):
                        self.assertIn(part, p.problems[0][3])
        # the near-miss: a header that says Hex and names the table's OWN theme, or none, is a header that says Hex
        # (round 5: one that names the other theme alone is rule 2's label)
        for header in ("| Token | Hex | Light |", "| Token | Hex | On light |", "| Token | Hex | Highlights, darker |", "| Token | Hex | Use |"):
            with self.subTest(header=header):
                p = _palette.parse_tables("### Light theme\n" + header + "\n|---|---|---|\n" + "\n".join(l + " x |" for l in lines(STARTER_LIGHT)) + "\n")
                self.assertEqual((p.light, p.problems), (STARTER_LIGHT, []))

    def test_a_table_like_it_with_no_colours_yet_is_passed_over_and_one_without_the_header_is_two_colours_a_row(self):
        p = _palette.parse_tables("| Token | Light | Dark |\n|---|---|---|\n| Heading | | |\n| Muted | #[…] | #[…] |\n")
        self.assertEqual((p.problems, p.ignored), ([], ["Heading", "Muted"]))
        p = _palette.parse_tables("### Light theme\n" + self.COMBINED)
        self.assertEqual(p.light, {})
        self.assertEqual([c for _t, _k, c in codes(p)], ["palette-two-colours"] * 9)
        # "Highlights" beside "Light" names one theme, the table's own: the header is quoted for what it calls the second column
        p = _palette.parse_tables("### Light theme\n| Token | Highlights | Light |\n|---|---|---|\n| Muted | #5a5a72 | #a6abce |\n")
        self.assertEqual(([c for _t, _k, c in codes(p)], p.light), (["palette-header"], {}))

    def test_what_the_liberal_reader_did_is_gone(self):
        for name in ("_same_but_rounded", "_label_of", "_section_of", "_ALIASES", "_KEY_OF_ALIAS", "_INNER", "_row", "_cell", "_key"):
            self.assertFalse(hasattr(_palette, name), name)
        # and what round 3's two rules for the whole text (9 and 12) made unnecessary
        for name in ("_COLOUR_LIKE", "_EDIT_ROOT", "_EDIT_DARK", "_EDIT_MEDIA", "_EDIT_MEDIA_ROOT", "_mask", "_after_string"):
            self.assertFalse(hasattr(_palette, name), name)
        for name in ("unused",):
            self.assertFalse(hasattr(_palette.Palette(), name), name)
        for name in ("above", "loose", "mark_not_read"):
            self.assertFalse(hasattr(_palette._Reader(), name), name)
        self.assertEqual(sorted(_palette.ROW_KEY), sorted(["primary", "heading", "body (ink)", "muted", "accent", "link", "hairline", "background",
                                                           "soft background", "surface (cards)", "body", "surface"]))

    def test_every_value_returned_stands_in_the_value_cell_of_a_row_the_rules_read(self):
        # the rule above all rules, on a document with everything else in it
        md = ("# Light and dark: our brand\n\nLight theme: #111111. Dark theme: #222222. | Muted | #333333 |\n\n**Light theme**\n" + HEAD + "| Muted | #444444 |\n\n"
              + pasted(light=dict(STARTER_LIGHT, muted="#5a5a72"))
              + "\n\n| Element | Colour |\n|---|---|\n| Link | #555555 |\n\nDark theme\n\n" + HEAD + "| Muted | #666666 |\n\n## Dark theme extras\n" + HEAD + "| Muted | #777777 |\n")
        p = _palette.parse_tables(md)
        self.assertEqual((p.light, p.dark, p.brand), (STARTER_LIGHT, STARTER_DARK, "#000000"))
        self.assertEqual([c for _t, _k, c in codes(p)], ["palette-no-section", "palette-header", "palette-no-section", "palette-no-section", NOT_READ])
        for value in ("#444444", "#555555", "#666666", "#777777"):
            self.assertNotIn(value, list(p.light.values()) + list(p.dark.values()))
        self.assertIn('Line 3, "Light theme: #111111. Dark theme: #222222. | Muted | #333333 |", holds a colour (#111111)', of(p, NOT_READ)[0])
        self.assertEqual(len(of(p, NOT_READ)), 1, "the rows a table's own problem names are not said a second time")


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
        self.assertEqual([c for _t, _k, c in codes(p)], ["palette-no-section", NOT_READ, NOT_READ])
        self.assertIn('under the heading "### Light Mode"', said(p))
        self.assertIn('also calls the second column "Color"', said(p))
        self.assertIn('"| Text | Near Black | `#16162A` |"', of(p, NOT_READ)[0])
        self.assertIn('"| Border | Light Gray | `#E3E7F2` |"', of(p, NOT_READ)[1])

    def test_a_row_found_and_not_filled_in_is_a_row_found(self):
        self.assertEqual(_palette.parse_tables(one("#[…]")).rows_found, 1)
        self.assertEqual(_palette.parse_tables(one("notacolour")).rows_found, 1)

    def test_the_sentence_names_the_three_headings_the_header_row_and_every_row(self):
        for part in ["`### Brand`", "`### Light theme`", "`### Dark theme`", "`| Token | Hex |`", "`|---|---|`", "Primary", "The assistant can write",
                     "under the heading `## Colour palette`", "looks only at the part under it"] + [l for _k, l in LABELS]:
            self.assertIn(part, _palette.FORM)


class Rule12ColoursThatWereNotRead(unittest.TestCase):
    """12. A colour written as a value (a # with 3, 4, 6 or 8 hex digits; rgb(), rgba(), hsl(), hsla() or oklch()
    with its brackets) on a line that is neither a row whose value was read nor a row that another problem names
    is a problem that quotes the line. Colour names and hex digits without their # are the limit of the rule."""

    FULL = pasted()   # (a text with no `Colour palette` heading: all of it is the palette. Rule 0's class has the other side.)

    def test_a_colour_in_any_place_that_is_not_read_is_named_with_its_line(self):
        # round 3: columns the wrong way round and a list under the heading were neither read nor named, and the rows
        # were printed as "not filled in"
        cases = (("columns the wrong way round", "### Light theme\n| Hex | Token |\n|---|---|\n| `#3a1d0a` | Heading |\n| #3a2a1e | Body (ink) |\n", ['"| `#3a1d0a` | Heading |"', '"| #3a2a1e | Body (ink) |"']),
                 ("a list under the heading", "### Light theme\n- Heading: #3a1d0a\n- Body (ink): #3a2a1e\n", ['"- Heading: #3a1d0a"', '"- Body (ink): #3a2a1e"']),
                 ("a sentence", "### Light theme\nOur ink is #16162a.\n", ['"Our ink is #16162a."']),
                 ("a sentence before any heading", "We use rgb(22, 22, 42) for text.\n", ['"We use rgb(22, 22, 42) for text."']),
                 ("a heading", "## Palette (#16162A on white)\n", ['"## Palette (#16162A on white)"']),
                 ("a line that starts with the colour", "#16162a is our ink.\n", ['"#16162a is our ink."']),
                 ("the first cell", "### Light theme\n" + HEAD + "| #5a5a72 | Muted |\n", ['"| #5a5a72 | Muted |"']),
                 ("a row under another name", "### Light theme\n" + HEAD + "| Hover | hsl(228 74% 40%) |\n", ['"| Hover | hsl(228 74% 40%) |"']),
                 ("a header row", "### Light theme\n| Token | Hex | was #000 |\n|---|---|---|\n", ['"| Token | Hex | was #000 |"']),
                 ("a row whose value cell is empty", "### Light theme\n" + HEAD + "| Muted | | #5a5a72 |\n", ['"| Muted | | #5a5a72 |"']),
                 ("a see-through colour", "### Light theme\n- Muted: rgba(90, 90, 114, 0.9)\n- Link: #2b50e080\n", ['"- Muted: rgba(90, 90, 114, 0.9)"', '"- Link: #2b50e080"']),
                 ("emphasis around it", "Ink: **#16162a**, muted: _#5a5a72_\n", ['"Ink: **#16162a**, muted: _#5a5a72_"']),
                 ("a colour outside what a screen shows", "Accent: OKLCH(0.7 0.4 150)\n", ['"Accent: OKLCH(0.7 0.4 150)"']),
                 ("a label and its colour on one line", "Muted #5a5a72\n", ['"Muted #5a5a72"']))
        for name, md, quotes in cases:
            for around in ("%s", self.FULL + "\n%s", "%s\n" + self.FULL):
                with self.subTest(name=name, around=around[:4]):
                    text = around % md
                    p = _palette.parse_tables(text)
                    self.assertEqual({c for _t, _k, c in codes(p)}, {NOT_READ})
                    messages = of(p, NOT_READ)
                    self.assertEqual(len(messages), len(quotes), "one problem for each line")
                    for message, quote in zip(messages, quotes):
                        self.assertIn("Line %d, %s, holds a colour (" % (text.splitlines().index(quote.strip('"')) + 1, quote), message)
                        self.assertIn("that was not read", message)
                    for part in ("only from the second cell of a named row (`| Muted | #5a5a72 |`)", "`### Brand`, `### Light theme` or `### Dark theme`",
                                 "write it in such a row", "take it out of this file or put it inside a comment (`<!-- ... -->`)"):
                        self.assertIn(part, messages[0])
                    if "%s" != around:
                        self.assertEqual((p.light, p.dark, p.brand), (STARTER_LIGHT, STARTER_DARK, "#000000"), "the palette beside it is read as it is")

    def test_what_is_read_or_is_named_by_its_own_problem_is_not_named_a_second_time(self):
        for name, md, expected in (("a note in a later cell of a row that was read", "### Light theme\n" + HEAD + "| Muted | #5a5a72 | 6.5:1 on #ffffff, was rgb(1, 2, 3) |\n", []),
                                   ("a row whose own problem names it", "### Light theme\n" + HEAD + "| Muted | #5a5a72 / #777777 |\n| Link | #2b50e080 |\n| Accent | #111 | #222 |\n",
                                    ["palette-not-one-colour", "colour-alpha", "palette-two-colours"]),
                                   ("the rows of a table that is not read", "## Colours\n" + plain(STARTER_LIGHT), ["palette-no-section"]),
                                   ("the rows of a table under another header", "### Light theme\n| Token | Value |\n|---|---|\n| Muted | #5a5a72 |\n", ["palette-header"]),
                                   ("a row under the wrong heading", "### Light theme\n" + HEAD + "| Primary | #000000 |\n", ["palette-wrong-section"]),
                                   ("a row that is too long", "### Light theme\n" + HEAD + "| Muted | #5a5a72 | %s |\n" % ("x" * 2100), ["palette-long-line"]),
                                   ("the rows under a label", "### Dark theme\n**Light theme**\n" + plain(STARTER_LIGHT), ["palette-label"])):
            with self.subTest(name=name):
                self.assertEqual([c for _t, _k, c in codes(_palette.parse_tables(md))], expected)

    def test_what_is_no_colour_written_as_a_value_is_not_named(self):
        # the near-misses of the definition, each beside a complete palette that must stay complete
        for text in ("The Facade type, decade by decade.", "See issue #12 and #12345, or page.html#fab and &#123;.", "Call 5a5a72 the muted one.", "A # alone, a #zzz, a #1234567.",
                     "Soft shadow: `[0 8px 24px rgba(...,0.06)]`", "Soft shadow: rgba(…)", "An rgb( that never closes", "xrgb(1, 2, 3) and hwb(0 0% 0%) and color(srgb 1 0 0)",
                     "navy, white and DimGray", "#[…] and #... are placeholders", "é#fff and #fffé", "- [ ] check the colours", "| Ink | Navy |"):
            with self.subTest(text=text):
                p = _palette.parse_tables(self.FULL + "\n" + text + "\n")
                self.assertEqual((p.problems, p.missing()), ([], []))
        # the limit, the other way: a number sign with three, four, six or eight digits is taken for a colour
        p = _palette.parse_tables(self.FULL + "\nSee issue #123.\n")
        self.assertEqual([c for _t, _k, c in codes(p)], [NOT_READ])

    def test_the_first_five_such_lines_are_quoted_and_the_rest_are_counted(self):
        p = _palette.parse_tables("".join("- colour %d: #12345%d\n" % (n, n) for n in range(9)))
        messages = of(p, NOT_READ)
        self.assertEqual((len(messages), len(p.problems)), (6, 6))
        self.assertIn("write it in such a row", messages[0])
        for n, message in enumerate(messages[1:5], 1):
            self.assertEqual(message, 'Line %d, "- colour %d: #12345%d", holds a colour (#12345%d) that was not read either: only the second cell of a named row under '
                                      "one of the three headings is read." % (n + 1, n, n, n))
        self.assertEqual(messages[5], "4 more lines hold a colour that was not read; the next is line 6.")
        p = _palette.parse_tables("".join("- colour %d: #12345%d\n" % (n, n) for n in range(6)))
        self.assertEqual(of(p, NOT_READ)[5], "1 more line holds a colour that was not read; the next is line 6.")

    def test_a_long_line_is_quoted_around_the_colour(self):
        line = "The sign above the door was painted in 1962 and has been repainted twice since then, most recently in a brown close to #6b2c0b, which the painter mixed by eye."
        p = _palette.parse_tables(line + "\n")
        self.assertIn('"...then, most recently in a brown close to #6b2c0b, which the painter mixed by eye."', p.problems[0][3])
        self.assertIn("holds a colour (#6b2c0b)", p.problems[0][3])


    REMEDY = "put the three headings with their tables under a heading `## Colour palette`. This check then looks only at that part"

    def test_a_guide_whose_palette_heading_has_another_name_is_told_the_heading_that_fits_also_when_its_rows_were_read(self):
        # round 4: with `## Colours` above the three tables every colour in the rest of the guide is named, and the one remedy
        # that fits a guide was printed only when no row was found at all
        guide = "# Example Bakery\n\n## Colours\n\n" + pasted() + "\n## Share cards\n\nBackground #2a1f17, wordmark rgb(251, 238, 221).\n\nShadow: #000.\n"
        p = _palette.parse_tables(guide)
        self.assertEqual((p.light, p.dark, p.brand, [c for _t, _k, c in codes(p)]), (STARTER_LIGHT, STARTER_DARK, "#000000", [NOT_READ, NOT_READ]))
        self.assertIn(self.REMEDY, of(p, NOT_READ)[0])
        self.assertNotIn("Colour palette", of(p, NOT_READ)[1], "said once")
        # round 5: once in a run, however many lines are quoted (five) and counted (the rest)
        p = _palette.parse_tables(guide + "".join("\nCard %d: #%06x.\n" % (n, n) for n in range(1, 9)))
        self.assertEqual(len(of(p, NOT_READ)), 6)
        self.assertEqual(sum(message.count("under a heading `## Colour palette`") for message in of(p, NOT_READ)), 1)
        self.assertEqual("\n".join(of(p, NOT_READ)).count(self.REMEDY), 1)
        # followed, it ends the matter
        self.assertEqual(_palette.parse_tables(guide.replace("## Colours", "## Colour palette")).problems, [])
        # the near-misses: a text with no heading but the three is a pasted answer, and one that has the heading is told what is true of it
        for name, text in (("a pasted answer", pasted() + "\nShadow: #000.\n"), ("a pasted answer with a sentence first", "Here you are.\n\n" + pasted() + "\nShadow: #000.\n"),
                           ("under the heading", "## Colour palette\n\n" + pasted() + "\nShadow: #000.\n"),
                           ("one of the three with a remark that is not read", pasted().replace("### Dark theme", "### Dark theme (dunkel)") + "\nShadow: #000.\n")):
            with self.subTest(name=name):
                p = _palette.parse_tables(text)
                self.assertEqual(len(of(p, NOT_READ)), 1)
                self.assertNotIn("## Colour palette", of(p, NOT_READ)[0])


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
                # (the first of them holds the word "proposed" in a row that is not read: rule 9 names it)
                self.assertEqual(self.outcome(md), (0, 0, None, ["palette-combined-table"] + [MARK] * ("proposed" in md)))
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
    """`read_css` reads the three blocks as `scan_css` finds them, which is also how the intake's editor
    (`_site.edit_css`) finds them, and names everything else: a block in another shape, one that stands twice,
    a colour set twice in a block, one marked !important, a colour set in any other rule. That the editor
    writes to exactly what this reads is held in tests/test_site_edits.py, by what the two do."""

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
                         ("@media (prefers-color-scheme: dark) {", "@media  ( prefers-color-scheme : dark )\n{"), (":root:not([data-theme]) {", ":root:not( [ data-theme ] ){"),
                         # what line a block starts on, and what comment stands beside its selector, are nobody's business
                         (":root {", ":root\r\n{"), (":root {", "/* light */ :root /* the tokens */ {"), (":root {", '@charset "utf-8"; :root {'),
                         ('}\n\n:root[data-theme="dark"] {', '} :root[data-theme="dark"] {'), ("  :root:not([data-theme]) {", "/* no JS */:root:not([data-theme]){")):
            with self.subTest(new=new):
                self.assertIn(old, self.starter())
                self.assert_all_three_blocks(self.starter().replace(old, new, 1))
        self.assert_all_three_blocks(self.starter().replace("\n", "\r\n"))
        self.assert_all_three_blocks(" ".join(self.starter().replace("/*", "\n/*").replace("*/", "*/\n").split(" ")).replace("\n", " "))  # all of it on one line

    def test_a_block_in_another_shape_is_named_and_not_read(self):
        # the reading used to take these for the block; the editor writes to none of them
        whole = self.starter()
        dark_at, media_at, rest_at = whole.index(':root[data-theme="dark"]'), whole.index("@media (prefers-color-scheme: dark)"), whole.index("*, *::before")
        swap = lambda old, new: (self.assertEqual(whole.count(old), 1), whole.replace(old, new))[1]  # noqa: E731
        media = "@media (prefers-color-scheme: dark) { "
        cases = ((swap(":root {", ":root, html {"), "light", "`:root, html { ... }`"), (swap(":root {", "html, :root {"), "light", "`html, :root { ... }`"),
                 (swap(":root {", ":ROOT {"), "light", "`:ROOT { ... }`"), (swap(":root {", ":Root,body{"), "light", "`:Root,body { ... }`"),
                 (swap(":root {", "html:root {"), "light", "`html:root { ... }`"), (swap(":root {", "html,\n:root {"), "light", "`html, :root { ... }`"),
                 (swap(":root {", ":root\u00a0{"), "light", "`:root<U+00A0> { ... }`"),
                 ("@layer base {\n" + whole[:dark_at] + "}\n" + whole[dark_at:], "light", "`@layer base { :root { ... } }`"),
                 (swap(':root[data-theme="dark"] {', ':root[data-theme="dark"], .dark {'), "dark", '`:root[data-theme="dark"], .dark { ... }`'),
                 (swap(':root[data-theme="dark"] {', ":ROOT[DATA-THEME='dark'] {"), "dark", "`:ROOT[DATA-THEME='dark'] { ... }`"),
                 (swap(':root[data-theme="dark"] {', ":root[data-theme=dark] {"), "dark", "`:root[data-theme=dark] { ... }`"),
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
                self.assertEqual([(block, variable) for block, variable, _m in css.problems], [(lacking, None)], "said once: the block that is not there, and the rule that may be it")
                self.assertTrue(css.problems[0][2].startswith("The stylesheet has no "), css.problems[0][2])
                for part in ("The rule " + shown + " sets --", "written in another way than the starter writes it", "did not read it", "does not write to it"):
                    self.assertIn(part, css.problems[0][2])
                self.assertNotIn("theme's colours, but", css.problems[0][2], "what the rule is for is not guessed: round 3 read `:root.dark` called the light theme's colours")
                self.assertEqual({"light": css.light, "dark": css.dark, "dark_media": css.dark_media}[lacking], {})
                self.assertEqual(_palette.drift(_palette.parse_tables(brand_md()), css), [], "what was not read is not also reported as drift")
        # the value of the attribute is not a word of CSS: "DARK" is another theme, and so is "night"
        css = _palette.read_css(whole.replace(':root[data-theme="dark"] {', ':root[data-theme="night"] {', 1))
        self.assertEqual(css.found, {"light", "dark_media"})
        # what such a rule is for is not guessed beyond what its selector says: this one is said as a block that is not
        # there and as a rule that sets the colours somewhere else, and nowhere as "the light theme's colours"
        css = _palette.read_css(whole.replace(':root[data-theme="dark"] {', ':root[data-theme~="dark"] {', 1))
        self.assertEqual((css.found, [(b, v) for b, v, _m in css.problems]), ({"light", "dark_media"}, [("dark", None), (None, None)]))
        self.assertNotIn("light theme", css.problems[1][2])

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

    def test_a_colour_set_in_any_other_rule_is_named_with_the_rule_and_the_variable(self):
        # a colours run ended "Done" while the page showed the colour of `body { --bg: ... }`; and `:root.dark` was called the light theme's colours
        three = "`:root {`, `:root[data-theme=\"dark\"] {`, and `:root:not([data-theme]) {` inside `@media (prefers-color-scheme: dark) {`"
        on_root = "a rule on :root that is written in another way than the starter writes it"
        for name, rule, said_ in (("on body", "body { --bg: #eeeeee }\n", "--bg is also set in the rule `body { ... }`, outside the three blocks that hold the palette (%s)" % three),
                                  ("on html, for a theme", 'html[data-theme="dark"] {\n  --bg: #000000;\n  --ink: #ffffff;\n}\n', '--bg and --ink are also set in the rule `html[data-theme="dark"] { ... }`, outside'),
                                  ("on a part of the page", ".card { --bg: #eeeeee; }\n", "--bg is also set in the rule `.card { ... }`, outside"),
                                  ("in a supports block", "@supports (color: oklch(0 0 0)) {\n  :root { --accent: oklch(0.5 0.2 265); }\n}\n", "--accent is also set in the rule `@supports (color: oklch(0 0 0)) { :root { ... } }`, " + on_root),
                                  ("in a print block", "@media print {\n:root { --bg: #ffffff; }\n}\n", "--bg is also set in the rule `@media print { :root { ... } }`, " + on_root),
                                  ("for a light attribute", ':root[data-theme="light"] { --bg: #fafafa; }\n', '--bg is also set in the rule `:root[data-theme="light"] { ... }`, ' + on_root),
                                  ("on :root with a class", ":root.dark { --bg: #000000; }\n", "--bg is also set in the rule `:root.dark { ... }`, " + on_root),
                                  ("deep inside other blocks", "@layer a {\n @layer b {\n  @media print {\n   .x { --brand: #111111 }\n  }\n }\n}\n", "--brand is also set in the rule `... { @layer b { @media print { .x { ... } } } }`, outside"),
                                  ("beside the block for visitors without JavaScript", "@media (prefers-color-scheme: dark) {\n  body { --surface: #000000; }\n}\n", "--surface is also set in the rule `@media (prefers-color-scheme: dark) { body { ... } }`, outside"),
                                  ("many of them at once", "a { --brand: #111; --accent: #222; --heading: #333; --ink: #444; --muted: #555 }\n", "--brand, --accent, --heading and others are also set in the rule `a { ... }`"),
                                  # round 6, checked in a browser by the reviewer: a line whose value holds a block is a line to a browser (the page's --bg was then no
                                  # colour), and this took it for the selector of a block inside the rule and never looked at it as a line
                                  ("in a line whose value holds a block", "html:root { --bg: #ff0000 {} }\n", "--bg is also set in the rule `html:root { --bg: #ff0000 { ... } }`, outside"),
                                  ("the same with nothing before the block", "html:root { --bg: {} }\n", "--bg is also set in the rule `html:root { --bg: { ... } }`, outside"),
                                  ("the same on :root twice", ":root:root { --accent: {} }\n", "--accent is also set in the rule `:root:root { --accent: { ... } }`, outside"),
                                  ("such a line after a line and a block", "html { color: red; a {} --ink : x {} }\n", "--ink is also set in the rule `html { --ink : x { ... } }`, outside"),
                                  ("such a line deep inside other blocks", "@supports (a: b) { div { span { --link: x {} } } }\n", "--link is also set in the rule `... { div { span { --link: x { ... } } } }`, outside"),
                                  ("such a line at the top level", "--bg: #f00 {}\n", "--bg is also set in the rule `--bg: #f00 { ... }`, outside"),
                                  ("such a line in a second block for the dark preference", "@media (prefers-color-scheme: dark) {\n  --surface: #000 {}\n}\n",
                                   "--surface is also set in the rule `@media (prefers-color-scheme: dark) { --surface: #000 { ... } }`, outside"),
                                  ("such a line whose block sets a colour too", "b { --bg: { --ink: #000 } }\n", "--bg and --ink are also set in the rule `b { --bg: { ... } }`, outside")):
            for before in (False, True):
                with self.subTest(name=name, before=before):
                    css = _palette.read_css(rule + self.starter() if before else self.starter() + rule)
                    self.assertEqual((css.found, css.light, css.dark, css.dark_media), ({"light", "dark", "dark_media"}, STARTER_LIGHT, STARTER_DARK, STARTER_DARK))
                    self.assertEqual([(b, v) for b, v, _m in css.problems], [(None, None)])
                    for part in (said_, "the page may show another colour there than the block's", "did not read that rule", "does not write to it"):
                        self.assertIn(part, css.problems[0][2])
                    self.assertNotIn("theme's colours", css.problems[0][2], "which theme such a rule is for is not guessed")
        # such a line beside a plain line of the same rule: each is named, the plain one as the rule's and the other with what stands before its block
        css = _palette.read_css(self.starter() + "i { --ink: #000; --bg: {} }\n")
        self.assertEqual([m.partition(", outside")[0] for _b, _v, m in css.problems], ["--ink is also set in the rule `i { ... }`", "--bg is also set in the rule `i { --bg: { ... } }`"])
        # inside one of the three blocks it is "a block inside the block", as before, which stops the editor too
        css = _palette.read_css(self.starter().replace("  --bg: #ffffff;", "  --bg: #ffffff;\n  --accent: {};", 1))
        self.assertEqual(([(b, v) for b, v, _m in css.problems], css.found), ([("light", None)], {"dark", "dark_media"}))
        self.assertIn("The :root block holds another block inside it (`--accent: { ... }`)", css.problems[0][2])
        # the near-misses: a rule that sets none of the palette's variables, whatever it is on and whatever else it sets
        for rule in ("@media (prefers-reduced-motion: reduce) {\n  :root { scroll-behavior: auto; --speed: 0s; }\n}\n", ".card { --card-bg: #eeeeee; --my--bg: #fff; background: var(--bg); }\n",
                     "@media print {\n  :root {\n    --shadow: none;\n  }\n}\n", 'body::after { content: "--bg: #000;"; }\n', "body { /* --bg: #000; */ color: var(--ink); }\n",
                     "a { background: url(data:image/svg+xml;--bg:#000;x) }\n", "html { --BG: #000; --bg2: #000; --bg-: #000; }\n",
                     # round 6: a block after something that only HOLDS the name is no line (a browser takes `a --bg: x {}` for a rule with a selector it drops)
                     "@supports (--bg: red) { a { color: red } }\n", "html { --x: {} }\n", "html { a --bg: x {} }\n", "html { --bg-image: {} --my--bg: {} }\n", "html { color: var(--bg) {} }\n",
                     'html { "--bg: " {} }\n', "html { /* --bg: */ a {} }\n"):
            with self.subTest(rule=rule):
                self.assert_all_three_blocks(self.starter() + rule)
                self.assert_all_three_blocks(rule + self.starter())

    def test_the_first_five_such_rules_are_named_and_the_rest_are_counted(self):
        css = _palette.read_css(self.starter() + "".join(".c%d { --bg: #eeeeee; }\n" % n for n in range(40)))
        self.assertEqual([(b, v) for b, v, _m in css.problems], [(None, None)] * 6)
        self.assertEqual(css.problems[5][2], "35 more rules outside the three blocks set one of the palette's colours.")
        css = _palette.read_css(self.starter() + "".join(".c%d { --bg: #eeeeee; }\n" % n for n in range(6)))
        self.assertEqual(css.problems[5][2], "1 more rule outside the three blocks sets one of the palette's colours.")
        css = _palette.read_css(self.starter() + "".join(".c%d { --bg: #eeeeee {} }\n" % n for n in range(7)))
        self.assertEqual(([(b, v) for b, v, _m in css.problems], css.problems[5][2]), ([(None, None)] * 6, "2 more rules outside the three blocks set one of the palette's colours."))
        # rules that may be a block that is not there are said with that block, and those past the tenth are counted too
        css = _palette.read_css("".join(":root, .c%d { --bg: #eeeeee; }\n" % n for n in range(12)))
        self.assertEqual([(b, v) for b, v, _m in css.problems], [("light", None), ("dark", None), ("dark_media", None), (None, None)])
        self.assertIn("The rule `:root, .c0 { ... }` sets --bg", css.problems[0][2])
        self.assertIn("9 other rules are like it too", css.problems[0][2])
        self.assertEqual(css.problems[3][2], "2 more rules outside the three blocks set one of the palette's colours.")

    def test_a_block_that_stands_twice_is_named_and_not_read(self):
        # no merging, and no later line taken to win. Round 4: the sentence still said "the intake writes to the first",
        # which it does not (it refuses such a stylesheet), and "a later one sets no colour" of a block that set none
        whole = self.starter()
        for block, again, holds in (("light", ":root { --accent: #111111; }", "the light theme's colours"), ("light", ":root {\n  --radius: 4px;\n}", "the light theme's colours"),
                                    ("dark", ':root[data-theme="dark"] { --bg: #222222; }', "the dark theme's colours"),
                                    ("dark_media", "@media (prefers-color-scheme: dark) {\n  :root:not([data-theme]) { --bg: #000000; }\n}", "the dark colours for visitors without JavaScript")):
            with self.subTest(again=again):
                css = _palette.read_css(whole + "\n" + again + "\n")
                self.assertEqual(css.found, {"light", "dark", "dark_media"} - {block})
                self.assertEqual({"light": css.light, "dark": css.dark, "dark_media": css.dark_media}[block], {})
                self.assertEqual([(b, v) for b, v, _m in css.problems], [(block, None)])
                for part in ("The stylesheet has 2 blocks", holds, "Each of the three colour blocks must stand once", "this check does not choose which of several holds the colours",
                             "the intake does not write to a stylesheet that has one of them twice", "Fold them into one"):
                    self.assertIn(part, css.problems[0][2])
                for gone in ("writes to the first", "a later one", "sets no colour"):
                    self.assertNotIn(gone, css.problems[0][2])
                self.assertEqual(_palette.drift(_palette.parse_tables(brand_md()), css), [])
                self.assertEqual(_palette.dark_blocks_disagree(css), [])
        css = _palette.read_css(":root { --bg: #ffffff; }\n" * 3)
        self.assertIn("The stylesheet has 3 blocks", css.problems[0][2])
        # round 3: written on one line the first of two was read, on two lines neither
        for text in (":root{--bg:#ff0000}:root{--bg:#0000ff}\n", ":root{--bg:#ff0000}\n:root{--bg:#0000ff}\n"):
            css = _palette.read_css(text)
            self.assertEqual((css.light, [(b, v) for b, v, _m in css.problems][0]), ({}, ("light", None)))
            self.assertIn("The stylesheet has 2 blocks", css.problems[0][2])
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
        # (in the :root block it wins over the dark blocks' lines too, so those have no value either: the test after this one)
        everywhere = [("light", "--bg"), ("dark", "--bg"), ("dark_media", "--bg")]
        for name, text, problems in (("alone", whole.replace("--bg: #ffffff;", "--bg: #ffffff !important;", 1), everywhere),
                                     ("in capitals", whole.replace("--bg: #ffffff;", "--bg: #ffffff ! IMPORTANT ;", 1), everywhere),
                                     ("with a plain line after it", whole.replace("--bg: #ffffff;", "--bg: #000000 !important;\n  --bg: #ffffff;", 1), everywhere),
                                     ("on the last of three lines", whole.replace("--bg: #ffffff;", "--bg: #ffffff;\n  --bg: #eeeeee;\n  --bg: #000000 !important;", 1), everywhere),
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

    def test_a_colour_marked_important_in_the_root_block_wins_over_the_dark_blocks_line_which_then_has_no_value(self):
        # round 4, checked in a browser: `:root { --bg: #fff !important }` shows white in the dark theme too, whatever the dark block says
        whole = self.starter()
        css = _palette.read_css(whole.replace("--bg: #ffffff;", "--bg: #ffffff !important;", 1))
        self.assertEqual(("bg" in css.dark, "bg" in css.dark_media, css.dark["ink"]), (False, False, "#dce0f5"))
        for block, message in [(b, m) for b, _v, m in css.problems][1:]:
            self.assertEqual(message, "It is marked !important in the :root block, and that line wins over this block's: the page shows the colour of the :root block "
                                      "here too. Take the !important off there.")
        # several lines of which ONE is marked: the marked one wins wherever it stands, so the variable is said to be both
        css = _palette.read_css(whole.replace("--bg: #ffffff;", "--bg: #000000 !important;\n  --bg: #ffffff;", 1))
        for part in ("set 2 times in this block (#000000 !important and #ffffff), and marked !important there", "leave one line, without !important"):
            self.assertIn(part, css.problems[0][2])
        # the near-misses: a dark block that does not set the variable has nothing to lose, a variable that is no colour is nobody's business
        # here, and !important in ONE dark block says nothing of the other (they never apply together)
        css = _palette.read_css(":root { --bg: #ffffff !important; --ink: #111111; }\n" + ':root[data-theme="dark"] { --ink: #eeeeee; }\n')
        self.assertEqual([(b, v) for b, v, _m in css.problems], [("light", "--bg"), ("dark_media", None)])
        css = _palette.read_css(whole.replace("--radius: 12px;", "--radius: 12px !important;", 1))
        self.assertEqual(css.problems, [])
        css = _palette.read_css(whole.replace("  --muted: #a6abce;", "  --muted: #a6abce !important;", 1))
        self.assertEqual(([(b, v) for b, v, _m in css.problems], css.dark_media["muted"]), ([("dark", "--muted")], "#a6abce"))

    def test_a_block_that_holds_another_block_is_named_and_not_read(self):
        # its own lines used to be lost without a word
        text = self.starter().replace(":root {\n", ':root {\n  &[data-theme="sepia"] { --bg: #f4ecd8; }\n', 1)
        css = _palette.read_css(text)
        self.assertEqual((css.found, css.light), ({"dark", "dark_media"}, {}))
        self.assertEqual([(b, v) for b, v, _m in css.problems], [("light", None)])
        for part in ("The :root block holds another block inside it", '&[data-theme="sepia"]', "plain list of lines", "was not read"):
            self.assertIn(part, css.problems[0][2])

    def test_a_colour_written_as_a_variable_that_has_no_one_value_is_never_read_from_another_block(self):
        # round 3: dark `--page: #000000 !important; --bg: var(--page)` over light `--page: #ffffff`: the dark Background was read as #ffffff, and nothing was said.
        # (Round 4: only another of the palette's variables is followed at all, so these are written with the accent and the link.)
        light, dark = ":root { --accent: #ffffff; --link: var(--accent); }\n", ':root[data-theme="dark"] { %s --link: var(--accent); }\n'
        for name, lines_, why in (("marked important", "--accent: #000000!important;", '(it is marked !important in the :root[data-theme="dark"] block)'),
                                  ("set twice", "--accent: #000000; --accent: #111111;", '(it is set 2 times in the :root[data-theme="dark"] block)'),
                                  ("set twice, once important", "--accent: #000000; --accent: #111111 !important;", '(it is set 2 times in the :root[data-theme="dark"] block, and marked !important there)')):
            with self.subTest(name=name):
                css = _palette.read_css(light + dark % lines_)
                self.assertEqual((css.light, css.dark), ({"accent": "#ffffff", "link": "#ffffff"}, {}))
                self.assertEqual([(b, v) for b, v, _m in css.problems if v], [("dark", "--accent"), ("dark", "--link")])
                self.assertIn("It is written as var(--accent), and --accent has no one value that this check can read here " + why, [m for _b, v, m in css.problems if v][1])
        # the :root block's own line marked important wins over the dark block's plain one: not read as the dark block's either
        css = _palette.read_css(":root { --accent: #ffffff !important; --bg: #ffffff; }\n" + dark % "--accent: #000000;")
        self.assertEqual((css.dark, [(b, v) for b, v, _m in css.problems if v]), ({}, [("light", "--accent"), ("dark", "--accent"), ("dark", "--link")]))
        self.assertIn("(it is marked !important in the :root block, which wins over the line in the :root[data-theme=\"dark\"] block)", [m for _b, v, m in css.problems if v][2])
        # round 4 (a): two lines in :root of which one is marked important are "important", not only "twice": the dark block's line does not win
        css = _palette.read_css(":root { --accent: #ffffff !important; --accent: #eeeeee; --bg: #ffffff; }\n" + dark % "--accent: #000000;")
        self.assertEqual((css.dark, [(b, v) for b, v, _m in css.problems if v]), ({}, [("light", "--accent"), ("dark", "--accent"), ("dark", "--link")]))
        # the near-misses: a variable the dark block sets once and plainly, and one only the :root block sets
        self.assertEqual(_palette.read_css(light + dark % "--accent: #000000;").dark, {"accent": "#000000", "link": "#000000"})
        self.assertEqual(_palette.read_css(light + dark % "").dark, {"link": "#ffffff"})
        self.assertEqual(_palette.read_css(":root { --accent: #ffffff; --accent: #eeeeee; --bg: #ffffff; }\n" + dark % "--accent: #000000;").dark, {"accent": "#000000", "link": "#000000"},
                         "set twice in :root, plainly, and once in the dark block: the dark block's line is laid over both")
        css = _palette.read_css(":root { --accent: #ffffff; --accent: #eeeeee; --bg: #ffffff; }\n" + dark % "")
        self.assertEqual((css.dark, [(b, v) for b, v, _m in css.problems if v]), ({}, [("light", "--accent"), ("dark", "--link")]))

    def test_a_colour_written_as_a_variable_that_is_not_the_palettes_is_not_followed_and_is_told_to_write_the_colour_out(self):
        # round 4, checked in a browser: `--bg: var(--page)` with `html:root { --page: #000 }` further down was read as #ffffff while the page was black.
        # Nothing holds a variable that is not the palette's to one value, so none is followed.
        whole = self.starter()
        via = whole.replace("--bg: #ffffff;", "--page: #ffffff;\n  --bg: var(--page);", 1)
        for name, text in (("set in the block, once", via), ("and set again in another rule", via + "\nhtml:root { --page: #000000; }\n"),
                           ("and set twice, once important", via.replace("--page: #ffffff;", "--page: #000000 !important; --page: #ffffff;", 1)),
                           ("set nowhere", whole.replace("--bg: #ffffff;", "--bg: var(--nowhere);", 1)), ("with space inside", whole.replace("--bg: #ffffff;", "--bg: var( --page );", 1))):
            with self.subTest(name=name):
                css = _palette.read_css(text)
                self.assertEqual(("bg" in css.light, [(b, v) for b, v, _m in css.problems]), (False, [("light", "--bg")]))
                self.assertIn("which points at a variable this check does not read", css.problems[0][2])
                self.assertIn("Write the colour out.", css.problems[0][2])
                self.assertEqual(_palette.scan_css(text).problems, [], "the scan has no problem with it: the editor writes over the value like over any other")
        # in a dark block, and for every one of the palette's variables that points outside the palette
        css = _palette.read_css(whole.replace("  --ink: #dce0f5;", "  --ink: var(--text);", 1))
        self.assertEqual(([(b, v) for b, v, _m in css.problems], css.dark_media["ink"]), ([("dark", "--ink")], "#dce0f5"))
        # the near-miss: the starter's own line, which points at another of the palette's variables, is read (the test above this one has the rest)
        self.assertEqual(_palette.read_css(whole).light["link"], "#2b50e0")

    def test_the_primary_written_as_a_variable_is_never_read_and_is_told_to_write_the_colour_out(self):
        # round 7 (R7-204), checked in a browser by the reviewer: `--brand: var(--accent);` in `:root`, a line a developer writes, was read as
        # ONE colour (the light Accent), with no problem and no drift, while the page shows the dark Accent on a dark page: the dark blocks
        # set `--accent`, and no dark block sets `--brand`. The Primary is one colour, the same in every theme.
        whole = self.starter()
        same = _palette.Palette()
        same.light, same.dark, same.brand = dict(STARTER_LIGHT), dict(STARTER_DARK), STARTER_LIGHT["accent"]
        for points_at in ("--accent", "--link", "--heading", "--bg", "--brand", "--mine", " --accent\n  "):
            with self.subTest(points_at=points_at):
                text = whole.replace("  --brand: #000000;", "  --brand: var(%s);" % points_at, 1)
                self.assertNotEqual(text, whole)
                css = _palette.read_css(text)
                self.assertEqual((css.brand, [(b, v) for b, v, _m in css.problems]), (None, [("light", "--brand")]))
                self.assertEqual((css.light, css.dark, css.dark_media), (STARTER_LIGHT, STARTER_DARK, STARTER_DARK), "every other colour is read as before")
                self.assertEqual(css.problems[0][2], "It is written as var(%s): the brand colour points at another variable, which each theme may set differently, and the "
                                                     "Primary is one colour for both themes. Write the colour out (`--brand: #1a2b3c;`, with your colour)." % points_at.strip())
                self.assertEqual(_palette.scan_css(text).problems, [], "the scan has no problem with it: the editor writes the colour over it")
                self.assertEqual(_palette.drift(same, css), [], "said once: a palette whose Primary is that Accent's colour is not told of a drift as well")
        # in a dark block too (where the editor refuses a Primary of any kind)
        css = _palette.read_css(whole.replace(':root[data-theme="dark"] {\n', ':root[data-theme="dark"] {\n  --brand: var(--accent);\n', 1))
        self.assertEqual((css.brand, [(b, v) for b, v, _m in css.problems]), ("#000000", [("dark", "--brand")]))
        # the near-misses: the starter's own line, which points from one theme colour at another and is set again by each dark block, and a
        # theme colour that points at the Primary, which is one colour everywhere
        self.assert_all_three_blocks(whole)
        self.assertIn("  --link: var(--accent);", whole)
        css = _palette.read_css(whole.replace("  --accent: #2b50e0;", "  --accent: var(--brand);", 1))
        self.assertEqual((css.brand, css.light["accent"], css.light["link"] if "link" in css.light else None, css.problems[:1] and css.problems[0][:2]), ("#000000", "#000000", None, ("light", "--link")),
                         "(the link then points at a line that points on, which is its own problem)")

    def test_no_stylesheet_makes_the_reading_slow(self):
        # round 3 measured 100 seconds for a megabyte of `a{b:c}` on one line: the start of the line was looked for again at every rule.
        # Round 4 added the shapes from "of brace pairs" on. The slowest measured is that one, which makes half a million rules: 0.88
        # seconds of processor time with a load of 5.5 on the machine (1.8 while another heavy job ran beside it), about twice a megabyte
        # of opening braces. While round 4 was mended, half a megabyte of blocks inside blocks took 9 seconds for a while, because every
        # block was searched to its end for a backslash: that shape is in the list too.
        mb = 1024 * 1024
        shapes = (("a megabyte of small rules on one line", "a{b:c}" * (mb // 6)), ("of root blocks on one line", ":root{--bg:red}" * (mb // 15)),
                  ("of rules that set a colour", "x :root{--bg:#fff}\n" * (mb // 19)), ("of comment openers", "/* " * (mb // 3)), ("of quotes", "a{b:'" * (mb // 5)),
                  ("of one block's lines", ":root {\n" + "--x: 1;\n" * (mb // 8) + "}\n"), ("of one colour set again and again", ":root {\n" + "--bg: #000;\n" * (mb // 12) + "}\n"),
                  ("of blocks inside blocks", "@a{" * (mb // 8) + "x{--bg:red}" + "}" * (mb // 8)), ("of opening braces", "{" * mb), ("of brackets in a value", ":root{--bg:" + "(" * mb + "}"),
                  ("of url( that never close", ":root{--bg:" + "url(" * (mb // 4)), ("of space in a value", ":root{--bg:" + " " * mb + "red}"), ("of important marks", ":root{--bg:" + "! important " * (mb // 12) + "}"),
                  ("of backslashes in a string", ":root{--f:'" + "\\" * mb + "'}"), ("of blocks in the media block", "@media (prefers-color-scheme: dark) {" + "a{--bg:red}" * (mb // 11) + "}"),
                  ("of brace pairs", "{}" * (mb // 2)), ("of blocks inside blocks, all the way down", "{" * (mb // 2) + "}" * (mb // 2)), ("of the same with a backslash in the innermost", "{" * (mb // 2) + "\\" + "}" * (mb // 2)),
                  ("of backslashes", "\\" * mb), ("of escaped braces", "\\{" * (mb // 2)), ("of names written with an escape", "a{--b\\67:x}" * (mb // 11)), ("of the same in one block", "a{" + "--b\\67:x;" * (mb // 9) + "}"),
                  ("of ; at the top level", ";" * mb), ("of round bracket pairs", "()" * (mb // 2)), ("of square brackets that open", "[" * mb), ("of brackets in brackets in a value", ":root{--bg:" + "(" * (mb // 2) + ")" * (mb // 2) + "}"),
                  ("of rules that register a colour", "@property --bg{}" * (mb // 16)), ("of default namespaces", "@namespace url(x);" * (mb // 18)), ("of url( after an escape", "\\url(" * (mb // 5)),
                  ("of lines written as a variable", ":root{" + "--bg:var(--x);" * (mb // 14) + "}"), ("of line breaks before a bracket too many", "\n" * mb + ")"),
                  # round 5: 128 KB of the first of these took 13 seconds (0.04 now), because the block around a block was searched for through
                  # every open bracket. The slowest of the round's shapes at a megabyte, blocks with a block in brackets each, takes 0.64 seconds
                  # of processor time on Python 3.13 and 1.14 on 3.9 (load 8); the slowest of all is still "of brace pairs", 1.16 and 2.21.
                  ("of brace pairs inside round brackets in a value", ":root { --x:" + "(" * (mb // 4) + "{}" * (mb // 4) + ")" * (mb // 4) + "; --bg:#fff }"),
                  ("of the same inside square brackets", ":root { --x:" + "[" * (mb // 4) + "{}" * (mb // 4) + "]" * (mb // 4) + "; --bg:#fff }"),
                  ("of the same in another rule, in both kinds of bracket", "a { --x:" + "([" * (mb // 8) + "{}" * (mb // 4) + "])" * (mb // 8) + " }"),
                  ("of braces inside brackets inside braces", "a{(" * (mb // 4) + ")}" * (mb // 4)), ("of the same with square brackets", "a{[" * (mb // 4) + "]}" * (mb // 4)),
                  ("of open braces, then open brackets, then brace pairs", "a{" * (mb // 8) + "(" * (mb // 8) + "{}" * (mb // 8) + ")" * (mb // 8) + "}" * (mb // 8)),
                  ("of blocks with a block in brackets each", "a{(b{})}" * (mb // 8)), ("of round brackets, then one brace at the top level", "(" * mb + "{"),
                  ("of imports", "@import 'x.css';" * (mb // 16)), ("of strings that run over a line end", "a{b:'\\41\n'}" * (mb // 11)),
                  ("of backslashes before a line end in one string", "a{b:'" + "\\" * (mb - 1) + "\n"), ("of strings that end in backslashes", "'\\\\\\\n" * (mb // 5)),
                  ("of hex digits before a line end in strings", ("'" + "\\" + "a" * 7 + "\n") * (mb // 10)), ("of url( with a backslash each", "url(\\))" * (mb // 7)),
                  # round 6
                  ("of HTML comment marks that open", "<!--" * (mb // 4)), ("of ones that close", "-->" * (mb // 3)), ("of both in one value", ":root{--x:" + "<!-- -->" * (mb // 8) + "}"),
                  ("of dashes", "-" * mb), ("of lines whose value holds a block", "a{--bg:x{}}" * (mb // 11)), ("of such lines inside each other", "--bg:{" * (mb // 6) + "}" * (mb // 6)),
                  ("of blocks after a long name that is no line", ("--" + "x" * 1000 + " {}\n") * (mb // 1006)), ("of one name before one block", "--" + "x" * mb + " {}"))
        for name, text in shapes:
            with self.subTest(name=name):
                start = time.process_time()
                try:
                    _palette.read_css(text)
                except Refusal:
                    pass
                took = time.process_time() - start
                self.assertLess(took, 4.0, "reading took %.2f s of processor time" % took)

    def test_a_brace_inside_a_string_is_not_a_brace(self):
        for rule in ('a::before { content: "{"; }\n', "a::after { content: '}'; }\n", 'q::before { content: "\\"{"; }\n', 'a[title="{"] { color: red; }\n',
                     '@import "we}ird{.css";\n'):
            with self.subTest(rule=rule):
                self.assert_all_three_blocks(rule + self.starter())
                self.assert_all_three_blocks(self.starter().replace(":root[data-theme", rule + ":root[data-theme", 1))
        css = _palette.read_css(':root { --font: "a{b;c"; --bg: #ffffff; }')
        self.assertEqual(css.light, {"bg": "#ffffff"}, "and the block that holds the string is read to its end")

    def test_what_stands_inside_a_string_is_not_a_comment_a_line_or_the_end_of_a_block(self):
        # round 3: `--label: "/*";` hid the rest of the stylesheet as a comment, and it was refused for braces that pair up
        for line in ('--label:"/*";', "--label: '/* not a comment';", '--quote: "}";', '--label:"{";', '--note: "--bg: none; x";', '--note: "; --bg: #000000";',
                     '--icon: url(data:image/svg+xml;utf8,{--bg:#000;});', '--close: "*/";', '--esc: "a\\"; --bg: #000; \\"";', '--important: "x !important";'):
            with self.subTest(line=line):
                for old in (":root {\n", "  --radius: 12px;\n", '[data-theme="dark"] {\n', ":root:not([data-theme]) {\n"):
                    self.assertIn(old, self.starter())
                    self.assert_all_three_blocks(self.starter().replace(old, old + "  " + line + "\n", 1))
        # and a comment is one although a quote stands in it
        self.assert_all_three_blocks(self.starter().replace(":root {\n", ":root {\n  /* don't */\n", 1))
        self.assert_all_three_blocks(self.starter().replace("--bg: #ffffff;", "--bg: #ffffff; /* the page's \"paper\" */", 1))

    def test_the_last_line_of_a_block_needs_no_semicolon(self):
        text = self.starter().replace("--surface: #161836;\n  --shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 10px 28px rgba(0, 0, 0, 0.5);\n}", "--shadow: none;\n  --surface: #161836\n}", 1)
        self.assertNotEqual(text, self.starter())
        self.assert_all_three_blocks(text)
        self.assertEqual(_palette.read_css(":root{--bg:#fff}").light, {"bg": "#ffffff"})

    def test_a_comment_is_not_text(self):
        comment = "/*\n:root {\n  --bg: #123456;\n}\n:root[data-theme=\"dark\"] {\n  --bg: #654321 !important;\n}\n*/\n"
        self.assert_all_three_blocks(comment + self.starter())
        self.assert_all_three_blocks(self.starter().replace("--bg: #ffffff;", "--bg: #ffffff /* was #fafafa; --bg: #000000 !important */;", 1))
        self.assert_all_three_blocks(self.starter() + "/* never closed: :root { --bg: #000000; }\n")

    def test_braces_that_do_not_pair_up_are_refused_not_read_as_far_as_they_go(self):
        # a } too many ended the :root block early and hid the dark block; nothing said so
        # (round 4: round and square brackets pair up like braces, and the sentence names the bracket and its line: the test after this one)
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
                self.assertIn("The stylesheet's brackets do not pair up: the `", str(cm.exception))
                self.assertIn("Mend the stylesheet, then run this again.", str(cm.exception))
        for text, what in ((self.starter() + "\n}\n", "the `}` on line 90 closes nothing: no `{` is open there"), (":root {\n --bg: #fff;\n", "the `{` on line 1 is never closed")):
            with self.assertRaises(Refusal) as cm:
                _palette.read_css(text)
            self.assertIn(what, str(cm.exception))

    def test_round_and_square_brackets_pair_up_like_braces_and_a_value_ends_only_where_all_of_them_are_closed(self):
        # round 4, checked in a browser: with `--bg: rgb(1,2; --other: 3px;` a browser reads on to the bracket's end, through the end of the
        # block and of the stylesheet, while this read the block and the editor replaced everything up to the next `;` of the bracket
        whole = self.starter()
        for name, text, what in (
                ("a ( never closed in a value", whole.replace("--bg: #ffffff;", "--bg: rgb(1,2; --other: 3px;", 1), "the `(` on line 15 is still open where the `}` on line 22 closes something else"),
                ("a [ never closed in a value", whole.replace("--radius: 12px;", "--grid: [full;", 1), "the `[` on line 19 is still open where the `}` on line 22 closes something else"),
                ("a ( never closed in a selector", whole + "\na:not(.b { color: red; }\n", "the `(` on line 90 is still open where the `{` on line 90 opens a block, so a browser "
                                                                                             "takes that block for a part of what the bracket holds and for no rule"),
                ("a ( never closed at the end", whole + "\na { color: rgb(1, 2, 3 ", "the `(` on line 90 is never closed"),
                ("a ) too many", whole.replace("--radius: 12px;", "--radius: 12px);", 1), "the `)` on line 19 closes nothing: no `(` is open there"),
                ("a ] too many at the top level", "]\n" + whole, "the `]` on line 1 closes nothing: no `[` is open there"),
                ("closed by the other kind", whole.replace("--radius: 12px;", "--grid: [a);", 1), "the `)` on line 19 closes nothing: no `(` is open there"),
                ("the line numbers are the file's own, whatever comments and strings stand above", "/*\n\n*/ a { content: '(';\n }\n" + whole.replace("--radius: 12px;", "--grid: [a;", 1),
                 "the `[` on line 23 is still open where the `}` on line 26 closes something else"),
                ("closed in the wrong order", whole.replace("--radius: 12px;", "--grid: ([)];", 1), "the `[` on line 19 is still open where the `)` on line 19 closes something else"),
                ("a url( never closed", whole + "\na { background: url(a.svg; }\n", "the `(` on line 90 is never closed"),
                ("a function that only ends like url(", whole.replace("--radius: 12px;", "--x: -url(();", 1), "the `(` on line 19 is still open where the `}` on line 22 closes something else")):
            with self.subTest(name=name):
                with self.assertRaises(Refusal) as cm:
                    _palette.read_css(text)
                self.assertEqual(cm.exception.code, "css-unreadable")
                self.assertIn("The stylesheet's brackets do not pair up: " + what + ". So this check cannot tell where", str(cm.exception))
        # the near-misses: brackets that pair up, whatever they hold, and brackets that are no brackets
        for line in ("--grid: [full-start] 1fr [full-end];", "--grid: [; --ink: #000000; ];", "--calc: calc(100% - (2 * var(--gap, 1rem)));", "--x: (; --bg: #000000; );", "--x: ([()]);",
                     '--s: "(";', "--s: '[';", "--u: url(a(b.svg);", "/* ( [ */", "--x: -url(());"):
            with self.subTest(line=line):
                self.assert_all_three_blocks(whole.replace("  --radius: 12px;\n", "  --radius: 12px;\n  " + line + "\n", 1))
        css = _palette.read_css(":root { --grid: [; --ink: #111111; ]; --bg: #ffffff; --shadow: 0 0 rgba(0, 0, 0, 0.5), (; --muted: #222222; ); }")
        self.assertEqual(css.light, {"bg": "#ffffff"}, "a line inside brackets is part of the value around it, and no line of the block")

    def test_a_block_inside_brackets_where_a_browser_expects_a_rule_is_refused_like_a_bracket_that_does_not_pair_up(self):
        # round 5, checked in a browser: `( a{} :root { ... } ) a{}` is ONE rule to Chromium, whose selector runs to the last `{`; every light
        # variable was unset on the page, and this read the block inside the brackets as the :root block
        whole = self.starter()
        dark_at, media_at, rest_at = whole.index(':root[data-theme="dark"]'), whole.index("@media (prefers-color-scheme: dark)"), whole.index("*, *::before")
        light, dark, media, rest = whole[:dark_at], whole[dark_at:media_at], whole[media_at:rest_at], whole[rest_at:]
        inner = media[media.index("  :root:not"):media.rindex("}")]
        for name, text, what in (
                ("the light block in round brackets", "( a{} " + light + ") a{}\n" + dark + media + rest, "the `(` on line 1 is still open where the `{` on line 1 opens a block"),
                ("in square brackets", "[ a{} " + light + "] a{}\n" + dark + media + rest, "the `[` on line 1 is still open where the `{` on line 1 opens a block"),
                ("the dark block, with nothing else in the brackets", light + "(\n" + dark + ") a{}\n" + media + rest, "the `(` on line 24 is still open where the `{` on line 25 opens a block"),
                ("in the brackets of an at-rule", "@supports ( a{} " + light + ") {}\n" + dark + media + rest, "the `(` on line 1 is still open where the `{` on line 1 opens a block"),
                ("a bracket inside a bracket", light + "a:is((b{})) {}\n" + dark + media + rest, "the `(` on line 24 is still open where the `{` on line 24 opens a block"),
                ("the rule in the media block", light + dark + media.replace(inner, "( a{}\n" + inner + ") a{}\n", 1) + rest, "the `(` on line 37 is still open where the `{` on line 37 opens a block"),
                ("after the three blocks", whole + "\n[ x { } ]\n", "the `[` on line 90 is still open where the `{` on line 90 opens a block")):
            with self.subTest(name=name):
                self.assertNotEqual(text, whole)
                with self.assertRaises(Refusal) as cm:
                    _palette.read_css(text)
                self.assertEqual(cm.exception.code, "css-unreadable")
                for part in ("The stylesheet's brackets do not pair up: " + what + ", so a browser takes that block for a part of what the bracket holds and for no rule. So this check cannot tell",
                             "Mend the stylesheet, then run this again."):
                    self.assertIn(part, str(cm.exception))
        # the near-misses. Brackets that are closed before the block opens are a selector's or an at-rule's own
        for rule in ("a:not(.b) { color: red }", "a[href^='('] { color: red }", "@supports (display: grid) { a { color: red } }", "@media (min-width: 40em) and (hover: hover) { a { color: red } }",
                     "a:is(b, c[d]) { e: f }"):
            with self.subTest(rule=rule):
                self.assert_all_three_blocks(rule + "\n" + whole)
        # and inside a block (in a value, or in a block within another at-rule) a block in brackets is what it was before: a block of that block
        css = _palette.read_css(whole.replace("  --radius: 12px;", "  --radius: 12px;\n  --json: [{}];", 1))
        self.assertEqual([(b, m[:45]) for b, _v, m in css.problems], [("light", "The :root block holds another block inside it")])
        self.assert_all_three_blocks(whole + "\nbody { --json: ({a: [b, {c: d}]}); }\n@supports (a: b) { ( x{} ) y {} }\n")
        self.assertEqual(self.only(whole + "\nbody { --x: ( i { --bg: #000000 } ); }\n", "elsewhere")[:36], "--bg is also set in the rule `body {")


    def only(self, text, kind):
        """The stylesheet is read as the starter's, and has exactly one problem, of the stylesheet as a whole and of this kind: its message."""
        css = _palette.read_css(text)
        self.assertEqual((css.light, css.dark, css.dark_media), (STARTER_LIGHT, STARTER_DARK, STARTER_DARK))
        self.assertEqual([(t.block, t.variable, t.kind) for t in _palette.scan_css(text).problems], [(None, None, kind)])
        return css.problems[0][2]

    def test_a_semicolon_where_a_browser_expects_a_rule_is_named_because_the_rule_after_it_is_dropped(self):
        # round 4, checked in a browser: after `};` the dark block is ignored, and after `color: red;` the :root block; this read them all the same
        whole = self.starter()
        dark, media = ':root[data-theme="dark"] {', "@media (prefers-color-scheme: dark) {"
        for name, text, line, quote in (("a ; after the block before", whole.replace("}\n\n" + dark, "};\n\n" + dark, 1), 22, '";"'),
                                        ("a line of a block before the first block", "color: red;\n" + whole, 1, '"color: red;"'),
                                        ("a ; alone at the start", ";" + whole, 1, '";"'),
                                        ("a ; at the start of the media block", whole.replace(media, media + ";", 1), 36, '";"'),
                                        ("a ; after the rule in the media block", whole.replace("  }\n}\n", "  };\n}\n", 1), 48, '";"'),
                                        ("a line in a media block for something else", "@media print { color: black; a { color: red } }\n" + whole, 1, '"color: black;"'),
                                        ("a selector cut off by a ;", whole.replace(dark, "html;\n" + dark, 1), 24, '"html;"'),
                                        ("after an at-rule with a block", whole.replace("}\n\n*, *::before", "};\n\n*, *::before", 1), 49, '";"'),
                                        # found by comparing with a browser: an @ is the start of a statement only with a name straight after it
                                        ("an @ with a space after it", "@ import 'x.css';\n" + whole, 1, '"@ import \'x.css\';"'),
                                        ("an @ before a digit", "@1x;\n" + whole, 1, '"@1x;"')):
            with self.subTest(name=name):
                message = self.only(text, "statement")
                for part in ("Line %d of the stylesheet has a `;` where a browser expects a rule (%s)" % (line, quote), "no statement that starts with `@`",
                             "takes the `;` and what follows for the selector of the next rule, and drops that rule",
                             "Take that `;` out." if quote == '";"' else "Take that piece out, or move it into the block it belongs to."):
                    self.assertIn(part, message)
        # several are named once, and counted
        css = _palette.read_css(whole + "\na { };\nb { };\n\nc { };\n")
        self.assertEqual([m[:8] for _b, _v, m in css.problems] + [css.problems[1][2]], ["Line 90 ", "2 more p", "2 more pieces like it; the next is on line 91."])
        self.assertEqual(_palette.read_css(";;" + whole).problems[1][2], "1 more piece like it; the next is on line 1.")
        # the near-misses: a statement that starts with @, a ; inside a block, inside brackets, a string or a comment, and one in a block inside another at-rule
        for text in ("@import 'a.css';\n@layer base, theme;\n@foo bar;\n@media print;\n@-x-y z;\n@--x;\n@_a;\n@\u00e9;\n" + whole, whole.replace("--radius: 12px;", "--radius: 12px;;;", 1), whole + "\na { color: red;; }\n",
                     whole + "\n@supports (display: grid) { ; a { color: red } }\n", '@import url(a;b.css);\n@import "c;d.css";\n/* ; */\n' + whole,
                     whole + "\n@font-face { font-family: X; src: url(x.woff2); }\n", whole + "\n@media print { @page { margin: 0; } a { color: red; } }\n"):
            with self.subTest(text=text[:40]):
                self.assert_all_three_blocks(text)

    def kinds(self, text):
        return [(t.block, t.kind) for t in _palette.scan_css(text).problems]

    def test_a_backslash_anywhere_outside_a_string_and_a_comment_is_named_and_stops_the_editor(self):
        # round 4, checked in a browser: `--b\67: #000` IS `--bg` (the page went black, before and after the edit). Round 4 then read escapes
        # so that an escaped class name stayed ordinary, and round 5 found three more names an escape spells that this did not see: `u\72l(`
        # is `url(` to Chromium (what follows up to the `)` is no code), `@n\61mespace` a default namespace, `@p\72operty` a registration.
        # So no name written with a backslash is read any more, wherever it stands: it is one problem, and the editor does not write.
        import _site
        whole = self.starter()
        bakery = self.bakery()
        message = None
        for name, text, line, shown in (
                ("a property name, in the :root block", whole.replace("--bg: #ffffff;", "--bg: #ffffff;\n  --b\\67: #000000;", 1), 16, "`--b\\67:`"),
                ("in any other rule", whole + "\nbody { --b\\67 : #000000; }\n", 90, "`--b\\67`"),
                ("with a blank after the digits", whole + "\nbody { --b\\000067 : #000000; }\n", 90, "`--b\\000067`"),
                ("an escaped dash", whole + "\nbody { \\-\\-bg: #000000; }\n", 90, "`\\-\\-bg:`"),
                ("of a property that is no variable", whole + "\nbody { c\\6f lor: red; }\n", 90, "`c\\6f`"),
                ("deep inside other blocks", whole + "\n@media print {\n @supports (a: b) {\n  i { x: y; --\\62 g: #000 }\n }\n}\n", 92, "`--\\62`"),
                ("a selector that spells :root", whole + "\n:r\\6f ot { --bg: #000000; }\n", 90, "`:r\\6f`"),
                ("a selector with an escaped bracket", whole + "\n:root\\[data-theme\\] { --bg: #000000; }\n", 90, "`:root\\[data-theme\\]`"),
                ("an at-rule's name", "@m\\65 dia print { :root { --bg: #000000 } }\n" + whole, 1, "`@m\\65`"),
                # round 5: the function and the two at-rules that an escape spells
                ("url( spelt with an escape, a quote inside it", whole.replace("  --bg: #ffffff;", "  --bg: #ffffff;\n  --x: u\\72l(a'b); --bg: #ff0000; /*'*/ );", 1), 16, "`u\\72l(a'b)`"),
                ("the same in capitals", whole.replace("  --bg: #ffffff;", "  --bg: #ffffff;\n  --x: \\55 RL(a'b); --bg: #ff0000; /*'*/ );", 1), 16, "`\\55`"),
                ("a default namespace spelt with an escape", "@n\\61mespace url(http://www.w3.org/2000/svg);\n" + whole, 1, "`@n\\61mespace`"),
                ("the same, the first letter escaped", "@\\6e amespace url(urn:x);\n" + whole, 1, "`@\\6e`"),
                ("a registration spelt with an escape", whole + "@p\\72operty --bg { syntax: '<color>'; inherits: false; initial-value: #ff0000; }\n", 89, "`@p\\72operty`"),
                ("the same, the first letter escaped", whole + "@\\70roperty --bg { syntax: '<length>'; inherits: false; initial-value: 0px; }\n", 89, "`@\\70roperty`"),
                ("a registration of a name written with a backslash", whole + "@property --b\\67 { syntax: '<color>'; inherits: true; initial-value: #fff; }\n", 89, "`--b\\67`"),
                ("an import spelt with an escape", "@\\69mport 'x.css';\n" + whole, 1, "`@\\69mport`"),
                # what round 4 took for ordinary: now named like the rest
                ("a class name with an escaped colon", whole + "\n.sm\\:flex { display: flex }\n", 90, "`.sm\\:flex`"),
                ("with escaped brackets and quotes", ".before\\:content-\\[\\'\\'\\]::before { content: '' }\n" + whole, 1, "`.before\\:content-\\[\\'\\'\\]::before`"),
                ("with an escaped quote", '.q\\" { color: red }\n' + whole, 1, '`.q\\"`'),
                ("with an escaped brace", whole + "\n.a\\{b { color: red }\n", 90, "`.a\\{b`"),
                ("with an escaped semicolon", whole + "\n.a\\;b { color: red }\n", 90, "`.a\\;b`"),
                ("with escaped round brackets", whole + "\n.w-\\[calc\\(100\\%-2rem\\)\\] { width: 1px }\n", 90, "`.w-\\[calc\\(100\\%-2rem\\)\\]`"),
                ("in a value", whole.replace("--radius: 12px;", "--radius: 12px;\n  --note: \\--bg\\: x;", 1), 20, "`\\--bg\\:`"),
                ("an escaped ; in a value", whole.replace("--radius: 12px;", "--radius: 12px;\n  --x: a\\;b;", 1), 20, "`a\\;b`"),
                ("an escaped bracket in a value", whole.replace("--radius: 12px;", "--radius: 12px;\n  --e: \\(;", 1), 20, "`\\(`"),
                ("in an unquoted address", whole.replace("--radius: 12px;", "--radius: 12px;\n  --u: url(a\\).svg);", 1), 20, "`url(a\\).svg)`"),
                ("an escaped blank in a font's name", whole + "\na { font-family: a\\ b }\n", 90, "`a\\ b`"),
                ("two backslashes", whole + "\n.x\\\\ { color: red }\n", 90, "`.x\\\\`"),
                ("before a line end, outside a string", whole + "\na { --x: \\\n1; }\n", 90, "`\\<U+000A>1`"),
                ("an @ before a backslash at the end of a line", "@\\\n@layer a, b;\n" + whole, 1, "`@\\<U+000A>@layer`"),
                ("url( after a backslash", whole.replace("--radius: 12px;", "--radius: 12px;\n  --x: \\\\url(());", 1), 20, "`\\\\url(())`"),
                ("the last character of the stylesheet", whole + ".end\\", 89, "`.end\\`")):
            with self.subTest(name=name):
                found = [t for t in _palette.scan_css(text).problems if t.kind == "escape"]
                self.assertEqual([(t.block, t.variable) for t in found], [(None, None)], "one problem of the stylesheet, however many backslashes it holds")
                message = found[0].message
                for part in ("Line %d of the stylesheet writes a name with a backslash (%s). A backslash can spell any character" % (line, shown),
                             "`--b\\67` is `--bg` to a browser, and `u\\72l(` is `url(`", "this check does not read a name written with one",
                             "Write the name out without the backslash.", "(a class name with a colon in it), move that rule into another stylesheet."):
                    self.assertIn(part, message)
                self.assertIn((None, None, message), _palette.read_css(text).problems)
                # and the editor does not write, with that sentence, whatever part of the palette it is asked to write
                for which in (bakery, self.only_dark()):
                    with self.assertRaises(Refusal) as cm:
                        _site.edit_css(text, which)
                    self.assertEqual(cm.exception.code, "css-layout")
                    self.assertIn(message, str(cm.exception))
        # several backslashes are one problem, which names the first
        css = _palette.read_css(whole + "\nbody { --b\\67: #000; --\\69nk: #000; }\ni { --b\\67: #000 }\n.sm\\:flex { }\n")
        self.assertEqual([m[:8] for _b, _v, m in css.problems if "backslash" in m], ["Line 90 "])
        # where what follows the backslash leaves the brackets unpaired to this reading, the refusal is that sentence, and not one about brackets
        for line, shown in (("--x: \\28 ;", "`\\28`"), ("--x: \\url(();", "`\\url(()`"), ("--x: a\\ ) b;", "`a\\ )`")):
            with self.subTest(line=line):
                text = whole.replace("--radius: 12px;", "--radius: 12px;\n  " + line.replace("\\28 ;", "\\28 ; --y: );"), 1)
                with self.assertRaises(Refusal) as cm:
                    _palette.read_css(text)
                self.assertEqual(cm.exception.code, "css-unreadable")
                self.assertIn("Line 20 of the stylesheet writes a name with a backslash (%s)." % shown, str(cm.exception))
                self.assertNotIn("brackets", str(cm.exception))
                with self.assertRaises(Refusal) as edit:
                    _site.edit_css(text, bakery)
                self.assertEqual(str(edit.exception), str(cm.exception))
        # the near-misses: a backslash inside a string or a comment is ordinary, and so is one in a quoted address
        for rule in ("a::after { content: \"\\201C\"; }", "a::before { content: '\\'' }", 'q::before { content: "\\"{"; }', "a { --esc: \"a\\\"; --bg: #000; \\\"\"; }", "/* .sm\\:flex { } and u\\72l( */",
                     "a { background: url(\"a\\).svg\") }", "a { background: url( 'a\\\\b.svg' ) }", "a { content: '\\\\' }", "/* \\ */", "a { content: \"\\41 \\42\" '\\a' }",
                     "@import 'a\\62.css';", "a[title='\\{'] { color: red }"):
            with self.subTest(rule=rule):
                self.assert_all_three_blocks(whole + "\n" + rule + "\n")
                self.assert_all_three_blocks(rule + "\n" + whole)
                self.assertNotEqual(_site.edit_css(rule + "\n" + whole, bakery), rule + "\n" + whole)

    def only_dark(self):
        p = self.bakery()
        p.light, p.brand = {}, None
        return p

    def test_an_html_comment_mark_anywhere_outside_a_string_and_a_comment_is_named_and_stops_the_editor(self):
        # round 6, checked in a browser by the reviewer: Chromium passes over `<!--` and `-->` at the top level of a stylesheet, so `<!-- @property
        # --bg { ... }` registers the variable; and it reads `<!--url(` as the start of an address, so what follows up to the `)` is no code. This
        # read both as text, was clean, and the editor wrote while the page showed #ff0000. Neither mark is followed: it is one problem.
        import _site
        whole = self.starter()
        bakery = self.bakery()
        registers = ' @property --bg { syntax: "<color>"; inherits: false; initial-value: #ff0000; }\n'
        for name, text, line, mark in (
                ("before url(, in a value of the :root block", whole.replace("  --bg: #ffffff;", "  --bg: #ffffff;\n  --x: <!--url(a'b); --bg: #ff0000; /*'*/ );", 1), 16, "<!--"),
                ("before a registration, at the top", "<!--" + registers + whole, 1, "<!--"),
                ("the closing mark before a registration", "-->" + registers + whole, 1, "-->"),
                ("after the blocks", whole + "\n<!--\n", 90, "<!--"),
                ("the closing mark as the last characters", whole + "-->", 89, "-->"),
                ("on a line of its own between two other rules", whole + "a { color: red }\n-->\nb { color: red }\n", 90, "-->"),
                ("in the selector of another rule", whole + "\na <!-- b { color: red }\n", 90, "<!--"),
                ("in a value of another rule", whole + "\nbody { --note: a --> b; }\n", 90, "-->"),
                ("inside round brackets", whole + "\na { width: calc(1px <!-- ); }\n", 90, "<!--"),
                ("inside a media block", whole + "\n@media print {\n  <!--\n  a { color: red }\n}\n", 91, "<!--"),
                ("with a comment of the stylesheet's own kind before it", whole + "/* a\nb */ <!--", 90, "<!--"),
                ("after Windows line ends", whole.replace("\n", "\r\n") + "\r\n-->", 90, "-->"),
                # the blunt side of the rule: a class name that ends in two dashes, before a `>`, is `.a--` and `>` to a browser, and is named all the same
                ("a class name that ends in two dashes before >", whole + "\n.a-->.b { color: red }\n", 90, "-->")):
            with self.subTest(name=name):
                message = self.only(text, "html-comment")
                for part in ("Line %d of the stylesheet holds an HTML comment mark (`%s`). A browser passes over such a mark in some places of a stylesheet" % (line, mark),
                             "this check does not follow that, so it cannot tell what the stylesheet says from there on", "Take the mark out. (A comment in a stylesheet is written `/* ... */`.)"):
                    self.assertIn(part, message)
                # and the editor does not write, with that sentence, whatever part of the palette it is asked to write
                for which in (bakery, self.only_dark()):
                    with self.assertRaises(Refusal) as cm:
                        _site.edit_css(text, which)
                    self.assertEqual(cm.exception.code, "css-layout")
                    self.assertIn(message, str(cm.exception))
        # several marks are one problem, which names the first; and where a mark stands before one of the three blocks, that block is "not there" as well
        self.assertEqual(self.kinds(whole + "<!--\n-->\n<!-- -->"), [(None, "html-comment")])
        self.assertIn("Line 89 of the stylesheet holds an HTML comment mark (`<!--`)", _palette.read_css(whole + "<!--\n-->\n<!-- -->").problems[0][2])
        wrapped = "<!--\n" + whole + "-->\n"
        self.assertEqual(self.kinds(wrapped), [("light", "missing"), (None, "html-comment")])
        with self.assertRaises(Refusal) as cm:
            _site.edit_css(wrapped, self.only_dark())
        self.assertIn("Line 1 of the stylesheet holds an HTML comment mark (`<!--`)", str(cm.exception))
        # where what follows the mark leaves the brackets unpaired to this reading, the refusal is that sentence, and not one about brackets
        for rule, mark in (("a { b: <!--url(') }", "<!--"), ("a { b: --> ( }", "-->")):
            with self.subTest(rule=rule):
                with self.assertRaises(Refusal) as cm:
                    _palette.read_css(whole + "\n" + rule + "\n")
                self.assertEqual(cm.exception.code, "css-unreadable")
                self.assertIn("Line 90 of the stylesheet holds an HTML comment mark (`%s`)." % mark, str(cm.exception))
                self.assertNotIn("brackets", str(cm.exception))
                with self.assertRaises(Refusal) as edit:
                    _site.edit_css(whole + "\n" + rule + "\n", bakery)
                self.assertEqual(str(edit.exception), str(cm.exception))
        # the near-misses: a mark inside a comment, a string or an address is text, and so is what only looks like a mark
        for rule in ("/* <!-- --> */", "/* --> */\n/* <!-- */", 'a::before { content: "<!-- -->"; }', "a::after { content: '-->' }", 'a { background: url("<!--.svg") }', "a { background: url(<!--x-->) }",
                     '@import "<!--.css";', "a { --x: <! --; --y: - ->; --z: -- >; }", "a > b { color: red }", "a { --arrow: ->; --less: <; }", ".a-- > .b { color: red }", "a { --x: <!- -; }"):
            with self.subTest(rule=rule):
                self.assert_all_three_blocks(whole + "\n" + rule + "\n")
                self.assert_all_three_blocks(rule + "\n" + whole)
                self.assertNotEqual(_site.edit_css(rule + "\n" + whole, bakery), rule + "\n" + whole)

    def test_a_string_that_a_browser_reads_on_over_the_end_of_its_line_is_named_and_stops_the_editor(self):
        # round 4 followed a string over a backslash and a line end. Round 5, checked in a browser: a backslash and hex digits take ONE blank
        # after them, a line end too, so `"a\41` + a line end goes on in Chromium as well, where this ended the string: it read a `--bg` line
        # that was text to the browser, and the editor wrote into it. No string is followed over a line end any more: such a one is named.
        import _site
        whole = self.starter()
        for end in ("\n", "\r\n", "\r", "\f"):
            for name, tail in (("a backslash", "a\\"), ("a backslash and two hex digits", "a\\41"), ("and one", "\\9"), ("and six", "a\\00004A"), ("in capitals and small letters", "\\aF"),
                               ("after an escaped backslash", "\\\\\\41"), ("after an escaped quote", "\\\"\\\'\\"), ("after another escape", "\\41 \\42")):
                for quote in "\"'":
                    with self.subTest(end=repr(end), name=name, quote=quote):
                        line = "  --x: %s%s%s; --bg: #111111; %s ; /*%s*/" % (quote, tail, end, quote, quote)
                        text = whole.replace("  --bg: #ffffff;", line + end + "  --bg: #ffffff;", 1)
                        self.assertNotEqual(text, whole)
                        found = [t for t in _palette.scan_css(text).problems if t.kind == "string"]
                        self.assertEqual([(t.block, t.variable) for t in found], [(None, None)])
                        for part in ("Line 15 of the stylesheet has a string that runs over the end of its line (%s: a backslash, or a backslash and a number, stands last on the line)"
                                     % ("`" + quote + tail + "`"), "A browser reads the next line as a part of that string", "this check does not follow a string over a line end",
                                     "Write the string on one line."):
                            self.assertIn(part, found[0].message)
                        for which in (self.bakery(), self.only_dark()):
                            with self.assertRaises(Refusal) as cm:
                                _site.edit_css(text, which)
                            self.assertIn(found[0].message, str(cm.exception))
            # in any other rule too, and several are one problem that names the first
            text = "a::after { content: 'x\\" + end + "} :root { --bg: #000 }'; }" + end + "b { c: 'y\\41" + end + "' }" + end + whole
            with self.subTest(end=repr(end)):
                # what stands after such a string may leave the brackets unpaired to this reading (they pair up to a browser, which reads the
                # string on): then the refusal is this sentence too, and not one about brackets
                with self.assertRaises(Refusal) as cm:
                    _palette.scan_css(text)
                self.assertEqual(cm.exception.code, "css-unreadable")
                self.assertTrue(str(cm.exception).startswith("Line 1 of the stylesheet has a string that runs over the end of its line (`'x\\`: "), str(cm.exception))
                self.assertNotIn("brackets", str(cm.exception))
                self.assertEqual(str(cm.exception).count("has a string that runs over"), 1)
                with self.assertRaises(Refusal) as edit:
                    _site.edit_css(text, self.bakery())
                self.assertEqual(str(edit.exception), str(cm.exception))
            # the near-misses. A string that is never closed and that a browser does not read on ends at the end of its line, to both:
            # after an escaped backslash, after seven hex digits (six are the number, the seventh a letter), after a number and its one blank
            for tail in ("a", "a\\\\", "\\1234567", "a\\41 ", "a\\41\t", "\\g", "\\41x", "\\\\41 \\\\", ""):
                with self.subTest(end=repr(end), tail=tail):
                    css = _palette.read_css(":root { --bg: #ffffff;" + end + ' --note: "' + tail + end + " --ink: #111111;" + end + "}")
                    self.assertEqual((css.light, [m for b, _v, m in css.problems if b is None]), ({"bg": "#ffffff"}, []),
                                     "as a browser has it: the line with the broken string takes the next one with it")
            # and a string that is closed on its line is a string, whatever backslashes it holds
            for line in ('--note: "a\\41";', "--note: 'a\\\\';", '--note: "\\"";', '--a: "x\\41 "; --b: "\\\\";', "--note: 'it\\'s';"):
                with self.subTest(end=repr(end), line=line):
                    self.assert_all_three_blocks(whole.replace(":root {\n", ":root {\n  " + line + end, 1))

    def test_a_rule_that_registers_one_of_the_colours_is_named(self):
        # round 4, checked in a browser: with `@property --bg { syntax: '<length>'; ... }` the page's --bg is 0px, whatever the block says
        whole = self.starter()
        rule = "@property %s {\n  syntax: '<color>';\n  inherits: true;\n  initial-value: #ffffff;\n}\n"
        for name, text, line, what, shown in (("after the blocks", whole + rule % "--bg", 89, "one of the palette's variables", "`@property --bg`"),
                                              ("before them", rule % "--brand" + whole, 1, "one of the palette's variables", "`@property --brand`"),
                                              ("in capitals, on its own lines", whole + "\n\n@PROPERTY\n--bg-soft" + (rule % "")[10:], 91, "one of the palette's variables", "`@PROPERTY --bg-soft`"),
                                              ("inside another block", whole + "@layer base {\n" + rule % "--ink" + "}\n", 90, "one of the palette's variables", "`@property --ink`")):
            with self.subTest(name=name):
                message = self.only(text, "registered")
                for part in ("Line %d of the stylesheet registers %s with an `@property` rule (%s)" % (line, what, shown), "has a type and a starting value of its own",
                             "the page may show another colour than the block's line says", "Take the rule out, or set the colours by hand."):
                    self.assertIn(part, message)
        css = _palette.read_css(whole + rule % "--bg" + rule % "--ink")
        self.assertEqual(css.problems[1][2], "1 more rule like it; the next is on line 94.")
        # the near-misses: a variable that is none of the palette's, and a name that only begins like one
        for name in ("--gap", "--bg-image", "--BG", "--my-bg"):
            with self.subTest(name=name):
                self.assert_all_three_blocks(whole + rule % name)

    def test_a_default_namespace_is_named_and_one_with_a_prefix_is_not(self):
        # checked in a browser while round 4 was mended: with `@namespace url(http://www.w3.org/2000/svg);` first, `:root` matches no web page's root
        whole = self.starter()
        for statement in ("@namespace url(http://www.w3.org/2000/svg);", '@namespace "http://www.w3.org/2000/svg";', "@NAMESPACE\n  'http://www.w3.org/1999/xhtml' ;", '@namespace url("x");'):
            with self.subTest(statement=statement):
                message = self.only('@charset "utf-8";\n' + statement + "\n" + whole, "namespace")
                for part in ("of the stylesheet sets a default namespace (%s)" % _palette._quoted(" ".join(statement.split())), "a web page may show none of the palette",
                             "Take the statement out, or give the namespace a prefix"):
                    self.assertIn(part, message)
        for statement in ("@namespace svg url(http://www.w3.org/2000/svg);", '@namespace svg "http://www.w3.org/2000/svg";', "a { content: '@namespace url(x);' }", "/* @namespace url(x); */"):
            with self.subTest(statement=statement):
                self.assert_all_three_blocks(statement + "\n" + whole)

    def test_a_charset_that_names_another_encoding_than_utf8_is_named_and_stops_the_editor(self):
        # round 7 (R7-205), checked in a browser by the reviewer: with `@charset "iso-2022-kr";` as its first bytes, a stylesheet that a
        # browser loads as a file (no encoding said by a server) is read in that encoding: the page had none of the ten variables, and with
        # another encoding a `/*` was half of a two-byte character and the rule after it set the colour. This read the text as UTF-8 and was clean.
        import _site
        whole = self.starter()
        for statement, shown in (('@charset "iso-2022-kr";', '@charset "iso-2022-kr"'), ("@charset 'hz-gb-2312';", "@charset 'hz-gb-2312'"), ('@CHARSET "ISO-2022-JP";', '@CHARSET "ISO-2022-JP"'),
                                 ('@charset\n  "windows-1252" ;', '@charset "windows-1252"'), ('@charset /* old */ "latin1";', '@charset "latin1"'), ('@charset "utf-7";', '@charset "utf-7"'),
                                 ('@charset "utf-16le";', '@charset "utf-16le"'), ('@charset "";', '@charset ""'), ('@charset "utf-8 x";', '@charset "utf-8 x"'),
                                 # round 8: what only looks like one of the names a browser takes for UTF-8
                                 ('@charset "utf_8";', '@charset "utf_8"'), ('@charset "utf 8";', '@charset "utf 8"'), ('@charset "x-utf8";', '@charset "x-utf8"'),
                                 ('@charset "unicode-1-1-utf8";', '@charset "unicode-1-1-utf8"'), ('@charset "utf-8-sig";', '@charset "utf-8-sig"'), ('@charset "utf88";', '@charset "utf88"'),
                                 # R9-205: blanks inside the quotes, which Chromium does not pass over (it took the page's encoding instead)
                                 ('@charset " utf8 ";', '@charset " utf8 "'), ('@charset "utf-8\t";', '@charset "utf-8 "'), ("@charset ' UTF-8';", "@charset ' UTF-8'")):
            for name, text, line in (("first", statement + "\n" + whole, 1), ("after a comment", "/* styles */\n" + statement + "\n" + whole, 2), ("last", whole + statement + "\n", 89),
                                     ("after one that says UTF-8", '@charset "UTF-8";\n' + statement + "\n" + whole, 2), ("twice", statement + "\n" + statement + "\n" + whole, 1)):
                with self.subTest(statement=statement, name=name):
                    message = self.only(text, "charset")
                    self.assertEqual(message, "Line %d of the stylesheet says the file is written in another encoding than UTF-8 (`%s`). This tool reads stylesheets written "
                                              "in UTF-8 only. Save the file as UTF-8 and take that line out." % (line, shown))
                    for which in (self.bakery(), self.only_dark()):
                        with self.assertRaises(Refusal) as cm:
                            _site.edit_css(text, which)
                        self.assertEqual(cm.exception.code, "css-layout")
                        self.assertIn(message, str(cm.exception))
        # the near-misses: UTF-8 in any case and either quote; a statement with no quoted name, which names no encoding to a browser; the
        # words in a string or in a comment; a longer name.
        # Round 8 (R8-205): `@charset "utf8";` was refused with "written in another encoding than UTF-8", which is untrue: a browser takes
        # six names for UTF-8 (the reviewer's Chromium painted the starter's colours under `utf8` and `unicode-1-1-utf-8`). Each counts, in any
        # case, as written between the quotes (R9-205: with blanks there it is refused, above).
        self.assertEqual(sorted(_palette._UTF8_NAMES), ["unicode-1-1-utf-8", "unicode11utf8", "unicode20utf8", "utf-8", "utf8", "x-unicode20utf8"])
        self.assertIn("none of the names a browser takes for UTF-8: `utf-8`, `utf8`, `unicode-1-1-utf-8`, `unicode11utf8`, `unicode20utf8`, `x-unicode20utf8`, as written between "
                      "the quotes, case ignored", " ".join(_palette.scan_css.__doc__.split()))
        also_utf8 = ['@charset "%s";' % spelt for name in sorted(_palette._UTF8_NAMES) for spelt in (name, name.upper(), name.title())] + ["@charset 'UTF8' ;", '@CHARSET\n"Utf8";']
        for statement in also_utf8 + ['@charset "utf-8";', '@charset "UTF-8";', "@charset 'Utf-8';", '@CHARSET\n"utf-8";', "@charset utf-8;", "@charset iso-2022-kr;",
                          '/* @charset "iso-2022-kr"; */', "a { content: '@charset \"iso-2022-kr\";' }", '@charset-x "iso-2022-kr";', '.charset::after { content: "iso-2022-kr" }']:
            with self.subTest(statement=statement):
                self.assert_all_three_blocks(statement + "\n" + whole)
                self.assertNotEqual(_site.edit_css(statement + "\n" + whole, self.bakery()), statement + "\n" + whole)

    def test_url_is_the_word_itself_and_the_end_of_a_longer_name_is_a_function_like_any_other(self):
        # found by comparing with a browser while round 4 was mended: `-url(`, `@url(`, `#url(` and `url(` after a character beyond ASCII are no
        # addresses, so a bracket or a quote inside them counts; this read on to the next `)` and lost the browser's place. (Round 5: `url(`
        # after a backslash is a stylesheet with a backslash in it, which is named whatever stands after it: the test of that is below.)
        whole = self.starter()
        for before in ("-", "_", "x", "9", "@", "#", "\u00e9", "\u2028", "\ufeff", "\x00"):
            with self.subTest(before=before):
                with self.assertRaises(Refusal, msg="its ( is a bracket, and what it holds is read: the second ( is never closed"):
                    _palette.read_css(whole.replace("--radius: 12px;", "--x: %surl(();" % before, 1))
                self.assert_all_three_blocks(whole.replace("--radius: 12px;", "--x: %surl(());" % before, 1))
        # the word itself, in any case and after anything else, is an address up to its ): nothing inside it is read
        for before in ("", " ", "(", ",", "/", "+", ".", "%", "!"):
            for word in ("url", "URL", "Url"):
                with self.subTest(before=before, word=word):
                    text = whole.replace("--radius: 12px;", "--x: %s%s({'\"[(;--bg:#000;%s;" % (before, word, "))" if before == "(" else ")"), 1)
                    self.assert_all_three_blocks(text)

    def test_each_block_it_does_not_find_is_named(self):
        whole = self.starter()
        dark_at = whole.index(':root[data-theme="dark"]')
        media_at = whole.index("@media (prefers-color-scheme: dark)")
        rest_at = whole.index("*, *::before")
        cases = (("no dark block", whole[:dark_at] + whole[media_at:], {"dark"}), ("no media block", whole[:media_at] + whole[rest_at:], {"dark_media"}),
                 ("no root block", whole[dark_at:], {"light"}), ("none of them", "body { color: red; }", {"light", "dark", "dark_media"}), ("empty", "", {"light", "dark", "dark_media"}),
                 ("a media block with no root rule inside", whole.replace(":root:not([data-theme])", ".other", 1), {"dark_media", None}),
                 ("a dark block spelt another way", whole.replace(':root[data-theme="dark"]', "html.dark", 1), {"dark", None}))
        for name, text, lacking in cases:
            with self.subTest(name=name):
                css = _palette.read_css(text)
                self.assertEqual({block for block, _v, _m in css.problems}, lacking)
                self.assertEqual(css.found, {"light", "dark", "dark_media"} - lacking)
                for block, variable, message in css.problems:
                    self.assertIsNone(variable)
                    if block is None:  # the rule that holds the colours instead sets them outside the three blocks, and is named for that
                        self.assertIn("also set in the rule `", message)
                        continue
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
        for value, part in (("var(--nowhere)", "points at a variable this check does not read"), ("var(--accent, #2b50e0)", "is not one this check can read"), ("light-dark(#ffffff, #0a0b1e)", "is not one this check can read")):
            with self.subTest(value=value):
                css = _palette.read_css(whole.replace("--link: var(--accent);", "--link: %s;" % value, 1))
                self.assertEqual([(block, variable) for block, variable, _m in css.problems], [("light", "--link")])
                self.assertIn(part, css.problems[0][2])
                self.assertNotIn("link", css.light)

    # what Python's strip() takes for a blank and CSS does not (tests/test_colour.py has the colour reader's own test)
    NOT_CSS_SPACE = ("\u00a0", "\u2003", "\u3000", "\u2028", "\u0085", "\x0b", "\x1c", "\x1d", "\x1e", "\x1f")

    def test_a_blank_beside_a_value_that_css_does_not_take_for_white_space_makes_it_no_colour_and_the_editor_writes_over_it(self):
        # round 5, checked in a browser: `--bg:` + a no-break space + `#ffffff;` (a line pasted from a web page) is no colour to Chromium,
        # and the body had no background. This read #ffffff, and the editor left the line "as it stands" for a palette that wants #ffffff.
        import _site
        whole = self.starter()
        want = _palette.Palette()
        want.light, want.dark, want.brand = dict(STARTER_LIGHT), dict(STARTER_DARK), "#000000"
        self.assertEqual(_site.edit_css(whole, want), whole, "the starter's stylesheet with its own palette comes back byte for byte")
        for blank in self.NOT_CSS_SPACE:
            for name, old, new, block, variable, written in (
                    ("before the value", "  --bg: #ffffff;", "  --bg:%s#ffffff;" % blank, "light", "--bg", "  --bg:#ffffff;"),
                    ("after it", "  --bg: #ffffff;", "  --bg: #ffffff%s;" % blank, "light", "--bg", "  --bg: #ffffff;"),
                    ("on both sides, among plain blanks", "  --muted: #a6abce;", "  --muted: %s #a6abce %s ;" % (blank, blank), "dark", "--muted", "  --muted: #a6abce ;"),
                    ("in the media block", "    --ink: #dce0f5;", "    --ink:\t%s#dce0f5;" % blank, "dark_media", "--ink", "    --ink:\t#dce0f5;"),
                    ("inside a function", "  --bg: #ffffff;", "  --bg: rgb(255,%s255, 255);" % blank, "light", "--bg", "  --bg: #ffffff;"),
                    ("before a colour name", "  --surface: #ffffff;", "  --surface: %swhite;" % blank, "light", "--surface", "  --surface: #ffffff;")):
                with self.subTest(blank=repr(blank), name=name):
                    text = whole.replace(old, new, 1)
                    self.assertNotEqual(text, whole)
                    css = _palette.read_css(text)
                    self.assertEqual([(b, v) for b, v, _m in css.problems], [(block, variable)])
                    self.assertNotIn(_palette.KEY_OF_VARIABLE[variable], {"light": css.light, "dark": css.dark, "dark_media": css.dark_media}[block])
                    if name != "inside a function":
                        self.assertIn("has a character before or after it that looks like a space and is none to a browser", css.problems[0][2])
                    # the editor does not leave it as it stands: it writes the colour in the place of the value, the blank with it
                    self.assertEqual(_site.edit_css(text, want), text.replace(new, written, 1))
                    self.assert_all_three_blocks(_site.edit_css(text, want))
        # the blanks CSS does take are only blanks: read, and left as they stand
        for blank in (" ", "\t", "\n", "\r\n", "\f", " \t \n"):
            with self.subTest(blank=repr(blank)):
                text = whole.replace("  --bg: #ffffff;", "  --bg:%s#ffffff%s;" % (blank, blank), 1)
                self.assert_all_three_blocks(text)
                self.assertEqual(_site.edit_css(text, want), text)

    def test_a_byte_order_mark_at_the_start_of_the_stylesheet_is_read_past_and_stays_where_it_is(self):
        # round 5: with one, the `:root` block was "not there", while a browser reads the file (its decoder takes the mark off)
        import _site
        whole = self.starter()
        for text in ("\ufeff" + whole, "\ufeff\n" + whole, "\ufeff/* colours */ " + whole, "\ufeff@import 'fonts.css';\n" + whole):
            with self.subTest(text=text[:20]):
                self.assert_all_three_blocks(text)
                new = _site.edit_css(text, self.bakery())
                self.assertEqual((new[0], new[1:]), ("\ufeff", _site.edit_css(text[1:], self.bakery())), "the mark stays, and everything else is written as without it")
                self.assertEqual(_palette.read_css(new).light, T.BAKERY_LIGHT)
        # only at the very start: anywhere else it is a character of a name, as it is to a browser
        self.assertEqual({b for b, _v, _m in _palette.read_css("\n\ufeff" + whole).problems}, {"light"})
        self.assertEqual({b for b, _v, _m in _palette.read_css("\ufeff\ufeff" + whole).problems}, {"light"})
        self.assertEqual([b for b, _v, _m in _palette.read_css("\ufeff").problems], ["light", "dark", "dark_media"])

    def test_a_stylesheet_that_brings_in_another_one_gets_a_note_and_no_problem(self):
        # round 5, checked in a browser: `@import url("data:text/css,html:root{--bg:%23ff0000}");` before the starter's rules sets the page's
        # background, and nothing said so. An import is ordinary (fonts), so it stops nothing: it is a note.
        import _site
        whole = self.starter()
        self.assertEqual((_palette.read_css(whole).notes, _palette.scan_css(whole).notes), ([], []))
        note = "line %d of the stylesheet brings in another stylesheet (`%s`), which this check does not read. If that one sets the site's colours, the page can show other colours than these."
        for name, text, notes in (
                ("one", '@import url("./fonts.css");\n' + whole, [note % (1, '@import url("./fonts.css");')]),
                ("after a comment and a charset, in capitals, over two lines", '/* x */\n@charset "utf-8";\n\n@IMPORT\n  "a.css" screen ;\n' + whole, [note % (4, '@IMPORT "a.css" screen ;')]),
                ("one that sets the colours", '@import url("data:text/css,html:root{--bg:%23ff0000}");\n' + whole, [note % (1, '@import url("data:text/css,html:root{--bg:%23ff0000}");')]),
                ("two", "@import 'a.css';\n@import 'b.css';\n" + whole, [note % (1, "@import 'a.css';"), "1 more statement like it brings in another stylesheet; the next is on line 2."]),
                ("four, one of them between the blocks", "@import 'a.css'; @import 'b.css';\n@import url(c.css);\n" + whole.replace(':root[data-theme="dark"]', '@import "d.css";\n:root[data-theme="dark"]', 1),
                 [note % (1, "@import 'a.css';"), "3 more statements like it bring in other stylesheets; the next is on line 1."]),
                ("a long one", "@import url('%s.css');\n" % ("f" * 90) + whole, [note % (1, "@import url('%s..." % ("f" * 47))])):
            with self.subTest(name=name):
                css = _palette.read_css(text)
                self.assertEqual((css.notes, css.problems, css.found), (notes, [], {"light", "dark", "dark_media"}))
                self.assertEqual(_palette.scan_css(text).notes, notes)
                self.assertEqual(_palette.read_css(_site.edit_css(text, self.bakery())).light, T.BAKERY_LIGHT, "and the editor writes")
        # the near-misses: an import inside a block (which no browser follows), in a comment or a string, and another statement
        for text in ("@media print { @import 'a.css'; }\n" + whole, "/* @import 'a.css'; */\n" + whole, "a::after { content: \"@import 'a.css';\" }\n" + whole, "@layer base, theme;\n@charset 'x';\n" + whole,
                     "@important x;\n" + whole, "@import-x 'a.css';\n" + whole):
            with self.subTest(text=text[:30]):
                self.assertEqual(_palette.read_css(text).notes, [])



class StylesheetQuotes(unittest.TestCase):
    """A stylesheet message quotes the stylesheet. To CSS a tab, a line end or a form feed is a blank, so the quote shows
    it as one: written as <U+0009> it looked like a hidden character to take out, and the owner would have been told to
    remove a tab. Any other character that does not show is written as <U+...>, and then the message says what that is,
    as the palette's own messages do."""

    def test_a_tab_is_shown_as_a_blank_and_a_hidden_character_is_explained(self):
        whole = T.starter_file("src/styles/global.css")
        with self.assertRaises(Refusal) as tab:
            _palette.read_css(whole + 'a::after { content: "a\tb\\\n" }\n')
        self.assertIn('(`"a b\\`:', str(tab.exception))
        self.assertNotIn("<U+", str(tab.exception))
        with self.assertRaises(Refusal) as hidden:
            _palette.read_css(whole + 'a::after { content: "a\u200bb\\\n" }\n')
        self.assertIn("<U+200B>", str(hidden.exception))
        self.assertTrue(str(hidden.exception).endswith(_palette._UNSEEN_NOTE))
        # a problem the scan reports (not a refusal) carries the sentence too, once
        css = _palette.read_css(whole + "@media print {\n\t:root\u200b { --bg: #fff; } }\n")
        quoted = [t[2] for t in css.problems if "<U+200B>" in t[2]]
        self.assertTrue(quoted)
        for t in quoted:
            self.assertEqual(t.count(_palette._UNSEEN_NOTE), 1)
        # and a note (no problem, said beside the check) carries it too: an import with a hidden character in its address
        note = _palette.read_css('@import url("a\u200bb.css");\n' + whole).notes[0]
        self.assertIn("<U+200B>", note)
        self.assertTrue(note.endswith(_palette._UNSEEN_NOTE))


if __name__ == "__main__":
    unittest.main()
