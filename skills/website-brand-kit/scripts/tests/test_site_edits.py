"""Scenarios 8 (what is written), 29, 30, 31 and 35: the edits to the site's own files, and the
journal that undoes them.

Each edit changes the lines it must and no others (a diff of the file says so), names the file and
the line it could not find instead of guessing, and leaves a file that already says the right thing
byte for byte as it was. The journal restores every file it touched, deletes what it created (and only
that), and leaves alone anything that was there before.
"""

import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import _testutil as T
import _palette
import _site
from _refusal import Refusal


def bakery():
    p = _palette.Palette()
    p.light, p.dark, p.brand = dict(T.BAKERY_LIGHT), dict(T.BAKERY_DARK), "#b4531a"
    return p


def changed_lines(before, after):
    return [l for l in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]


class Stylesheet(unittest.TestCase):
    CSS = T.starter_file("src/styles/global.css")

    def test_the_three_places_carry_the_new_values_and_the_stylesheet_reads_back_as_the_palette(self):
        new = _site.edit_css(self.CSS, bakery())
        css = _palette.read_css(new)
        self.assertEqual(css.light, T.BAKERY_LIGHT)
        self.assertEqual(css.dark, T.BAKERY_DARK)
        self.assertEqual(css.dark_media, T.BAKERY_DARK)
        self.assertEqual(css.brand, "#b4531a")
        self.assertEqual(_palette.dark_blocks_disagree(css), [])

    def test_only_the_values_change_comments_and_other_lines_stay(self):
        new = _site.edit_css(self.CSS, bakery())
        lines = changed_lines(self.CSS, new)
        self.assertTrue(lines)
        for l in lines:
            self.assertRegex(l[1:], r"^\s*--(brand|accent|heading|ink|muted|link|line|bg|bg-soft|surface):", l)
        # a trailing comment on a changed line is kept
        self.assertRegex(new, r"--accent: #b4531a;\s+/\* links/highlights")
        self.assertIn("--shadow: 0 1px 2px rgba(0, 0, 0, 0.06)", new)
        self.assertIn("--radius: 12px;", new)
        self.assertEqual(new.count("--brand:"), self.CSS.count("--brand:"))
        # the light block's link was an alias of the accent; it now says its own value
        self.assertIn("--link: #a14a14;", new)
        self.assertNotIn("--link: var(--accent)", new)

    def test_writing_the_same_palette_twice_changes_nothing_more(self):
        once = _site.edit_css(self.CSS, bakery())
        self.assertEqual(_site.edit_css(once, bakery()), once)

    def test_a_dark_theme_row_goes_to_both_dark_blocks(self):
        p = bakery()
        p.dark["muted"] = "#c0c0d0"
        css = _palette.read_css(_site.edit_css(self.CSS, p))
        self.assertEqual((css.dark["muted"], css.dark_media["muted"]), ("#c0c0d0", "#c0c0d0"))
        self.assertEqual(css.light["muted"], T.BAKERY_LIGHT["muted"], "and never to the light block")

    def test_a_palette_without_a_primary_leaves_brand_alone(self):
        p = bakery()
        p.brand = None
        new = _site.edit_css(self.CSS, p)
        self.assertEqual(_palette.read_css(new).brand, "#000000")

    def test_a_stylesheet_that_is_not_laid_out_as_the_starters_is_refused_naming_the_place(self):
        cases = {
            "the dark block": (self.CSS.replace(':root[data-theme="dark"] {', ':root[data-theme="night"] {'), "dark"),
            "the media block": (self.CSS.replace("@media (prefers-color-scheme: dark)", "@media (min-width: 40em)"), "media"),
            "a variable in the dark block": (self.CSS.replace("  --bg-soft: #11132c;\n  --surface", "  --surface", 1), "--bg-soft"),
            "a variable in the root block": (self.CSS.replace("  --muted: #5a5a72;", ""), "--muted"),
            "a variable in the media block": (re.sub(r"(@media[^}]*?)--line: #272c4d;", r"\1", self.CSS, flags=re.S), "--line"),
        }
        for name, (text, mention) in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(Refusal) as cm:
                    _site.edit_css(text, bakery())
                self.assertEqual(cm.exception.code, "css-layout")
                self.assertIn(mention, str(cm.exception))

    def test_a_comment_that_looks_like_a_block_is_not_one(self):
        comment = "/*\n:root {\n  --bg: #123456;\n}\n:root[data-theme=\"dark\"] {\n  --bg: #654321;\n}\n*/\n"
        new = _site.edit_css(comment + self.CSS, bakery())
        self.assertTrue(new.startswith(comment), "the comment is left exactly as it was")
        self.assertEqual(_palette.read_css(new).light, T.BAKERY_LIGHT)
        self.assertEqual(_palette.read_css(new).dark, T.BAKERY_DARK)

    def test_a_variable_whose_name_ends_like_another_is_not_mistaken_for_it(self):
        text = self.CSS.replace(":root {\n  --brand: #000000;", ":root {\n  --my--bg: #abcdef;\n  --brand: #000000;", 1)
        new = _site.edit_css(text, bakery())
        self.assertIn("--my--bg: #abcdef;", new)
        self.assertEqual(_palette.read_css(new).light["bg"], T.BAKERY_LIGHT["bg"])

    def test_a_block_with_a_block_inside_it_is_refused_not_misread(self):
        text = self.CSS.replace(":root {\n  --brand: #000000;", ":root {\n  @supports (a: b) { --x: 1; }\n  --brand: #000000;", 1)
        with self.assertRaises(Refusal) as cm:
            _site.edit_css(text, bakery())
        self.assertEqual(cm.exception.code, "css-layout")
        self.assertIn("plain list", str(cm.exception))

    def test_a_comment_between_a_value_and_its_semicolon_stays(self):
        # only the value is replaced: what the owner wrote after it is hers
        text = self.CSS.replace("  --bg: #ffffff;", "  --bg: #ffffff /* the page */;", 1).replace("  --bg-soft: #f5f7fb;", "  --bg-soft: /* soft */ #f5f7fb\n    /* panels */\n    ;", 1)
        self.assertNotEqual(text, self.CSS)
        new = _site.edit_css(text, bakery())
        self.assertIn("  --bg: #fff8ee /* the page */;", new)
        self.assertIn("  --bg-soft: /* soft */ #fef5e8\n    /* panels */\n    ;", new)
        self.assertEqual(_palette.read_css(new).light["bg"], T.BAKERY_LIGHT["bg"])

    def test_a_colour_marked_important_is_refused_with_the_readings_own_words_not_written_around(self):
        # the edit used to write the new value in front of the !important, and the reading of what it wrote then had no
        # value for that colour: the two now say the same thing, before anything is changed
        text = self.CSS.replace("  --bg-soft: #f5f7fb;", "  --bg-soft: #f5f7fb !important;", 1)
        with self.assertRaises(Refusal) as cm:
            _site.edit_css(text, bakery())
        self.assertEqual(cm.exception.code, "css-layout")
        said = _palette.read_css(text).problems
        self.assertEqual([(b, v) for b, v, _m in said], [("light", "--bg-soft")])
        self.assertIn("--bg-soft in the :root block: " + said[0][2], str(cm.exception))
        self.assertIn("this tool cannot write the colours into the `:root` block (the light theme) as it stands", str(cm.exception))

    def test_the_dark_block_for_visitors_without_javascript_is_looked_for_inside_its_media_block_only(self):
        # the same selector after the @media block has closed is another rule: editing it would leave the
        # real block (here: missing) as it was
        head, sep, tail = self.CSS.partition("@media (prefers-color-scheme: dark) {")
        self.assertTrue(sep)
        inner, close, rest = tail.partition("\n}\n")
        self.assertIn(":root:not([data-theme])", inner)
        moved = head + sep + "\n  img { opacity: 0.9; }\n}\n" + inner.replace("  :root:not", ":root:not") + "\n" + rest
        with self.assertRaises(Refusal) as cm:
            _site.edit_css(moved, bakery())
        self.assertEqual(cm.exception.code, "css-layout")
        self.assertIn("inside the `@media (prefers-color-scheme: dark)` block", str(cm.exception))

    def test_an_earlier_media_block_for_dark_that_holds_something_else_does_not_hide_the_right_one(self):
        text = self.CSS.replace("@media (prefers-color-scheme: dark) {", "@media (prefers-color-scheme: dark) {\n  img { opacity: 0.9; }\n}\n@media (prefers-color-scheme: dark) {", 1)
        css = _palette.read_css(_site.edit_css(text, bakery()))
        self.assertEqual(css.dark_media, T.BAKERY_DARK)

    def test_a_primary_set_again_in_a_dark_block_is_refused_naming_the_block(self):
        # the Primary is one colour for both themes, set in `:root` alone: the edit would leave the dark one
        # as it is, and the dark theme would show another Primary
        dark, media = ':root[data-theme="dark"] {\n', "  :root:not([data-theme]) {\n"
        for name, text, block in (("the dark block", self.CSS.replace(dark, dark + "  --brand: #123456;\n", 1), '`:root[data-theme="dark"]` block'),
                                  ("the block for visitors without JavaScript", self.CSS.replace(media, media + "    --brand: #123456;\n", 1), "inside the `@media (prefers-color-scheme: dark)` block"),
                                  ("the palette's own value there", self.CSS.replace(dark, dark + "  --brand: #b4531a;\n", 1), '`:root[data-theme="dark"]` block'),
                                  ("a value that is no colour", self.CSS.replace(dark, dark + "  --brand: var(--accent);\n", 1), '`:root[data-theme="dark"]` block')):
            with self.subTest(name=name):
                self.assertNotEqual(text, self.CSS)
                with self.assertRaises(Refusal) as cm:
                    _site.edit_css(text, bakery())
                self.assertEqual(cm.exception.code, "css-primary-in-dark")
                self.assertIn("--brand (the Primary) inside", str(cm.exception))
                self.assertIn(block, str(cm.exception))
        # a second dark block further down that sets it is refused as well, for the reason the reading gives: the block stands twice
        later = self.CSS + '\n:root[data-theme="dark"] {\n  --brand: #123456;\n}\n'
        with self.assertRaises(Refusal) as cm:
            _site.edit_css(later, bakery())
        self.assertEqual(cm.exception.code, "css-layout")
        for part in ("would not carry the palette after the colours were set", "The stylesheet has 2 blocks of the kind that holds the dark theme's colours", "a later one sets --brand"):
            self.assertIn(part, str(cm.exception))

    def test_a_primary_that_a_dark_block_only_mentions_in_a_comment_or_under_another_name_is_no_reason_to_refuse(self):
        dark = ':root[data-theme="dark"] {\n'
        for extra in ("  /* --brand: #123456; */\n", "  --my-brand: #123456;\n", "  --brand-soft: #123456;\n"):
            with self.subTest(extra=extra):
                new = _site.edit_css(self.CSS.replace(dark, dark + extra, 1), bakery())
                self.assertIn(extra, new)
                self.assertEqual(_palette.read_css(new).brand, "#b4531a")


    # --- the reading and the edit are one fact -----------------------------------------------------

    def shapes(self):
        """The starter's stylesheet and it in every shape a review has put to the reading or to the edit: [(name, a
        function that makes it from a stylesheet)]. A function gives the text back unchanged where it does not apply."""
        dark, media, inner = ':root[data-theme="dark"] {', "@media (prefers-color-scheme: dark) {", "  :root:not([data-theme]) {"
        once = lambda old, new: (lambda t: t.replace(old, new, 1))  # noqa: E731
        return [
            ("as the starter has it", lambda t: t),
            # round 3, where the reading was clean and the edit refused with an untrue sentence, or wrote to another place
            ("a print block on :root that sets no colour, before the blocks", lambda t: "@media print {\n  :root {\n    --shadow: none;\n  }\n}\n" + t),
            ("the same after them", lambda t: t + "@media print {\n  :root {\n    --shadow: none;\n  }\n}\n"),
            ("a last line without its semicolon", once("--surface: #161836;\n  --shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 10px 28px rgba(0, 0, 0, 0.5);\n}", "--shadow: none;\n  --surface: #161836\n}")),
            ("a closing brace in a string", once(":root {\n", ':root {\n  --quote: "}";\n')),
            ("an opening brace in a string", once("--radius: 12px;", '--radius: 12px;\n  --label:"{";')),
            ("a colour's name in a string", once(":root {\n", ':root {\n  --note: "--bg: none; x";\n')),
            ("a comment opener in a string", once(dark + "\n", dark + '\n  --label: "/*";\n')),
            ("a comment before :root", once(":root {", "/* the light theme */ :root {")),
            ("a comment between a selector and its brace", once(dark, ':root[data-theme="dark"] /* dark */ {')),
            ("an import first", lambda t: '@import url("./fonts.css");\n' + t),
            ("the brace on the next line, after a carriage return", once(":root {", ":root\r\n{")),
            ("Windows line ends", lambda t: t.replace("\n", "\r\n")),
            ("no space anywhere before a brace", lambda t: t.replace(" {", "{")),
            ("the dark block on the line of the brace before it", once("}\n\n" + dark, "} " + dark)),
            ("comments around a value", once("  --bg: #ffffff;", "  --bg: /* page */ #ffffff /* was #fafafa; --bg: #000 */ ;")),
            ("a value over two lines", once("  --muted: #5a5a72;", "  --muted:\n    rgb(90,\n        90, 114);")),
            ("a value written as another variable", once("    --link: #9fb0ff;", "    --link: var(--accent);")),
            ("a value that is no colour", once("  --line: #272c4d;", "  --line: rgba(0, 0, 0, 0.2);")),
            ("an empty value", once("  --bg-soft: #f5f7fb;", "  --bg-soft: ;")),
            ("a second media block for the dark preference, with something else in it", once(media, media + "\n  img { opacity: 0.9; }\n}\n" + media)),
            ("another rule inside the media block", once(inner, "  img { opacity: 0.9; }\n" + inner)),
            ("the three blocks in another order", lambda t: t[t.index(dark):t.index("*, *::before")] + t[:t.index(dark)] + t[t.index("*, *::before"):]),
            # what the reading names, and the edit must refuse with
            ("html, on the line before :root", once(":root {", "html,\n:root {")),
            ("a selector list", once(":root {", ":root, html {")),
            ("capitals", once(dark, ':ROOT[data-theme="dark"] {')),
            ("no quotes around dark", once(dark, ":root[data-theme=dark] {")),
            ("the media block for screens only", once(media, "@media screen and (prefers-color-scheme: dark) {")),
            ("the dark block gone", lambda t: t[:t.index(dark)] + t[t.index(media):]),
            ("the media block gone", lambda t: t[:t.index(media)] + t[t.index("*, *::before"):]),
            ("the light block inside a layer", lambda t: "@layer base {\n" + t[:t.index(dark)] + "}\n" + t[t.index(dark):]),
            ("a second :root block that sets a colour", lambda t: t + "\n:root { --accent: #123456; }\n"),
            ("a second :root block that sets none", lambda t: t + "\n:root {\n  --gap: 4px;\n}\n"),
            ("a second dark block", lambda t: t + '\n:root[data-theme="dark"] { --bg: #222222; }\n'),
            ("a block inside the :root block", once(":root {\n", ":root {\n  .x { --bg: #f4ecd8; }\n")),
            ("a block inside the media block's rule", once(inner + "\n", inner + "\n    & { --bg: #000000; }\n")),
            ("a colour marked important", once("  --bg: #ffffff;", "  --bg: #ffffff !important;")),
            ("a colour marked important in the media block", once("    --muted: #a6abce;", "    --muted: #a6abce ! IMPORTANT;")),
            ("a colour set twice", once("  --accent: #2b50e0;", "  --accent: #2b50e0;\n  --accent: #111111;")),
            ("a colour set twice in the dark block", once("  --bg: #0a0b1e;", "  --bg: #0a0b1e; --bg: #0a0b1e;")),
            ("a colour set on body", lambda t: t + "\nbody { --bg: #eeeeee }\n"),
            ("a colour set for a theme on html", lambda t: 'html[data-theme="dark"] { --bg: #000000; }\n' + t),
            ("a colour set on :root in a print block", lambda t: "@media print {\n  :root {\n    --bg: #ffffff;\n  }\n}\n" + t),
            ("a colour set on :root with a class", lambda t: t + "\n:root.dark { --bg: #000000; }\n"),
            ("a colour set in a rule of the media block", once(inner, "  body { --surface: #000000; }\n" + inner)),
            # what only the edit refuses, by name: a line that is not there, and a Primary in a dark block
            ("a colour's line gone from :root", once("  --muted: #5a5a72;", "")),
            ("a colour's line gone from the media block", once("    --line: #272c4d;\n", "")),
            ("a colour under a name in capitals", once("  --bg: #ffffff;", "  --BG: #ffffff;")),
            ("a Primary in the dark block", once(dark + "\n", dark + "\n  --brand: #123456;\n")),
            ("a Primary in the media block's rule", once(inner + "\n", inner + "\n    --brand: #123456;\n")),
            # what neither can take
            ("a brace too many", once("--radius: 12px;", "--radius: 12px; }")),
            ("cut short", lambda t: t[:t.index("--bg-soft: #11132c;")]),
        ]

    def palettes(self):
        whole, light, dark = bakery(), bakery(), bakery()
        light.dark, dark.light, dark.brand = {}, {}, None
        some = bakery()
        some.light, some.dark, some.brand = {"bg": "#fff8ee", "ink": "#3a2a1e"}, {"muted": "#c4ae98"}, None
        return (("the whole palette", whole), ("the light theme and the Primary only", light), ("the dark theme only", dark), ("three colours", some))

    def outside(self, text, sheet, palette):
        """The text without the values the palette is written into: what an edit must leave byte for byte as it was."""
        spans = sorted(sheet.spans[block][var] for block, var, _value in self.wanted(palette))
        return "".join(text[a:b] for a, b in zip([0] + [end for _start, end in spans], [start for start, _end in spans] + [len(text)]))

    def wanted(self, palette):
        out = [("light", _palette.VARIABLE[k], v) for k, v in palette.light.items()] + ([("light", "--brand", palette.brand)] if palette.brand else [])
        return out + [(block, _palette.VARIABLE[k], v) for block in ("dark", "dark_media") for k, v in palette.dark.items()]

    def test_what_the_scan_takes_the_edit_writes_exactly_and_what_the_scan_names_the_edit_refuses_with(self):
        # Round 3: the reading and the edit were two programs, held together by a test that compared the TEXT of their
        # patterns and passed while they disagreed. They are now one scan (_palette.scan_css), and this holds them to
        # each other by what they DO, over the starter's stylesheet in every shape above and in pairs of those shapes.
        import random
        shapes = self.shapes()
        rng = random.Random(20261012)
        sheets = [(name, make(self.CSS)) for name, make in shapes]
        for name, _text in sheets[1:]:
            self.assertNotEqual(_text, self.CSS, "the shape %r no longer changes the starter's stylesheet" % name)
        for _ in range(120):
            (name_a, a), (name_b, b) = rng.sample(shapes[1:], 2)
            sheets.append(("%s + %s" % (name_a, name_b), b(a(self.CSS))))
        counts = {"written": 0, "refused with the scan's problem": 0, "refused: a line is not there": 0, "refused: a Primary in a dark block": 0, "refused: braces": 0}
        for name, text in sheets:
            for which, palette in self.palettes():
                with self.subTest(name=name, palette=which):
                    wanted = self.wanted(palette)
                    try:
                        sheet = _palette.scan_css(text)
                    except Refusal as scan_refusal:
                        with self.assertRaises(Refusal) as cm:
                            _site.edit_css(text, palette)
                        self.assertEqual((cm.exception.code, str(cm.exception)), (scan_refusal.code, str(scan_refusal)))
                        counts["refused: braces"] += 1
                        continue
                    read = _palette.read_css(text)
                    self.assertEqual(read.found, set(sheet.spans))
                    self.assertEqual(read.problems[:len(sheet.problems)], [(t.block, t.variable, t.message) for t in sheet.problems], "the reading says what the scan says, first")
                    stops = [t for t in sheet.problems if t.block is None or t.block in {block for block, _var, _value in wanted}]
                    primary = [block for block in ("dark", "dark_media") if "--brand" in sheet.spans.get(block, ()) or "--brand" in sheet.unsure.get(block, ())]
                    gone = [(block, var) for block, var, _value in wanted if not stops and var not in sheet.spans[block]]
                    if stops or primary or gone:
                        with self.assertRaises(Refusal) as cm:
                            _site.edit_css(text, palette)
                        message = str(cm.exception)
                        if stops:
                            # the scan has a problem for a block the edit must write, or for a rule outside the blocks: refused with it
                            self.assertEqual(cm.exception.code, "css-layout")
                            for t in stops:
                                self.assertIn(t.message, message)
                                if t.variable:
                                    self.assertIn("%s in %s: " % (t.variable, _palette.BLOCK[t.block]), message)
                            counts["refused with the scan's problem"] += 1
                        elif primary:
                            self.assertEqual(cm.exception.code, "css-primary-in-dark")
                            counts["refused: a Primary in a dark block"] += 1
                        else:
                            # no problem, and a line the palette needs is not there: the edit names it, and the reading has no value for it either
                            self.assertEqual(cm.exception.code, "css-layout")
                            block, var = gone[0]
                            self.assertIn("sets no %s" % var, message)
                            self.assertNotIn(_palette.KEY_OF_VARIABLE[var], {"light": dict(read.light, brand=read.brand) if read.brand else read.light,
                                                                              "dark": read.dark, "dark_media": read.dark_media}[block])
                            counts["refused: a line is not there"] += 1
                        continue
                    # no problem for what it must write: it writes, into exactly the places of the old values
                    new = _site.edit_css(text, palette)
                    after_scan = _palette.scan_css(new)
                    self.assertEqual(self.outside(new, after_scan, palette), self.outside(text, sheet, palette), "every byte outside the values is as it was")
                    for block, var, value in wanted:
                        a, b = after_scan.spans[block][var]
                        self.assertEqual(new[a:b], value)
                    after = _palette.read_css(new)
                    got = {"light": after.light, "dark": after.dark, "dark_media": after.dark_media}
                    for block, var, value in wanted:
                        self.assertEqual(after.brand if var == "--brand" else got[block][_palette.KEY_OF_VARIABLE[var]], value)
                    self.assertEqual([(t.block, t.variable) for t in after_scan.problems], [(t.block, t.variable) for t in sheet.problems], "and the edit made no new problem")
                    self.assertEqual(_site.edit_css(new, palette), new, "written a second time, nothing changes")
                    counts["written"] += 1
        self.assertEqual(sum(counts.values()), len(sheets) * 4)
        for outcome, n in counts.items():
            self.assertGreater(n, 8, "no stylesheet of the set ends as %r any more: %r" % (outcome, counts))
        # with the whole palette, every shape of the first group is written and every shape of the second is refused
        whole = bakery()
        for (name, make), expect in zip(shapes, [True] * 23 + [False] * (len(shapes) - 23)):
            with self.subTest(name=name):
                try:
                    _site.edit_css(make(self.CSS), whole)
                    self.assertTrue(expect, "written, though it should be refused")
                except Refusal:
                    self.assertFalse(expect, "refused, though it should be written")


class LineRule(unittest.TestCase):
    """What Config, Manifest and ShareCards share: _site.set_lines edits a value only on its one line in
    the starter's shape, refuses everything else in one kind of sentence, and that sentence can be followed."""
    rel = code = None

    def set(self, text, **want):
        return _site.set_lines(self.rel, text, want)

    def unchanged(self, text, **want):
        self.assertEqual(self.set(text, **want), (text, []), "nothing to edit, and no change to report")

    def refused(self, text, saying, **want):
        with self.assertRaises(Refusal) as cm:
            self.set(text, **want)
        self.assertEqual(cm.exception.code, self.code)
        message = str(cm.exception)
        self.assertIn(saying, message)
        self.assertRegex(message, r"^%s: this tool sets .* only where the file has this one line" % re.escape(self.rel))
        self.assertIn("\nWhat it found instead: ", message)
        self.assertTrue(message.endswith(", then run this again: a line that already says this is left exactly as it is."), message)
        return message

    def line_asked_for(self, message):
        """The line a refusal quotes: the one she is told she may write herself."""
        return re.search(r"only where the file has this one line[^\n]*:\n    (.*)\nWhat it found instead: ", message).group(1)


class Config(LineRule):
    rel, code = "src/config.ts", "config-layout"
    CONFIG = T.starter_file("src/config.ts")
    OWN = "  themeColor: '#000000',               // matches the brand primary + manifest\n"
    LOGO = "  logo: '/images/logo.png',            // resolved against SITE.url for schema\n"

    def test_the_starter_has_each_of_the_two_lines_once(self):
        self.assertEqual((self.CONFIG.count(self.OWN), self.CONFIG.count(self.LOGO)), (1, 1))

    def test_the_theme_colour_is_the_primary_and_nothing_else_moves(self):
        new, changes = self.set(self.CONFIG, themeColor="#b4531a")
        self.assertEqual(changes, [("themeColor", "#000000", "#b4531a")])
        self.assertEqual(len(changed_lines(self.CONFIG, new)), 2)
        self.assertEqual(new, self.CONFIG.replace("themeColor: '#000000'", "themeColor: '#b4531a'"), "the comment after the value is kept")

    def test_company_logo_is_set_to_the_derived_png_and_only_what_was_asked_for_is_touched(self):
        other = self.CONFIG.replace("logo: '/images/logo.png',", "logo: '/images/other.png',")
        new, changes = self.set(other, logo="/images/logo.png")
        self.assertEqual((new, changes), (self.CONFIG, [("logo", "/images/other.png", "/images/logo.png")]))
        self.unchanged(self.CONFIG, logo="/images/logo.png")
        self.assertIn("logo: '/images/other.png',", self.set(other, themeColor="#b4531a")[0], "a run about colours leaves COMPANY.logo alone")
        self.assertIn("themeColor: '#000000'", self.set(other, logo="/images/logo.png")[0], "and a run about the logo leaves the theme colour alone")
        both, changes = self.set(other, themeColor="#b4531a", logo="/images/logo.png")
        self.assertEqual(both, self.CONFIG.replace("themeColor: '#000000'", "themeColor: '#b4531a'"))
        self.assertEqual([name for name, _old, _new in changes], ["themeColor", "logo"])

    def test_the_line_may_be_written_with_either_quote_with_or_without_its_comma_and_comment_and_with_windows_line_ends(self):
        for name, line, after in (("double quotes", '  themeColor: "#000000",\n', '  themeColor: "#b4531a",\n'),
                                  ("no comma", "  themeColor: '#000000'\n", "  themeColor: '#b4531a'\n"),
                                  ("no comment", "  themeColor: '#000000',\n", "  themeColor: '#b4531a',\n"),
                                  ("no space after the colon", "  themeColor:'#000000',\n", "  themeColor:'#b4531a',\n"),
                                  ("three digits", "  themeColor: '#000', // short\n", "  themeColor: '#b4531a', // short\n"),
                                  ("a tab before it", "\tthemeColor: '#000000',\n", "\tthemeColor: '#b4531a',\n")):
            with self.subTest(name=name):
                text = self.CONFIG.replace(self.OWN, line).replace("  url:", line[:len(line) - len(line.lstrip())] + "url:", 1)
                self.assertEqual(self.set(text, themeColor="#b4531a")[0], text.replace(line, after))
        crlf = self.CONFIG.replace("\n", "\r\n")
        new, changes = self.set(crlf, themeColor="#b4531a", logo="/images/logo.png")
        self.assertEqual(new, crlf.replace("'#000000'", "'#b4531a'"))
        self.assertEqual(changes, [("themeColor", "#000000", "#b4531a")])
        other = self.CONFIG.replace(self.LOGO, '  logo: "/it\'s mine.png",\n')
        self.assertEqual(self.set(other, logo="/images/logo.png")[0], self.CONFIG.replace(self.LOGO, '  logo: "/images/logo.png",\n'), "the other kind of quote inside the value is part of it")

    def test_a_value_that_already_is_the_colour_is_not_edited_and_is_no_change_however_it_is_spelt(self):
        for spelt in ("#b4531a", "#B4531A", "#b4531aff", "#B4531AFF"):
            with self.subTest(spelt=spelt):
                self.unchanged(self.CONFIG.replace("'#000000'", "'%s'" % spelt), themeColor="#b4531a")
        for spelt in ("#abc", "#ABC", "#aabbcc", "#abcf"):
            with self.subTest(spelt=spelt):
                self.unchanged(self.CONFIG.replace("'#000000'", "'%s'" % spelt), themeColor="#aabbcc")
        new, changes = self.set(self.CONFIG.replace("'#000000'", "'#B4531B'"), themeColor="#b4531a")
        self.assertEqual(changes, [("themeColor", "#B4531B", "#b4531a")], "another colour is a change, and is shown as it stood")

    # --- what the old scanner got wrong by trying to read TypeScript: the line rule does not look at it at all ---

    def test_nothing_above_the_block_can_hide_it_whatever_quotes_and_braces_it_holds(self):
        want = self.CONFIG.replace("themeColor: '#000000'", "themeColor: '#b4531a'")
        for name, above in (("a regex literal holding an apostrophe", "const APOS = /'/g;\n"),
                            ("a regex literal holding both quotes", "const QUOTES = /['\"]/g;\n"),
                            ("a regex literal holding a backtick and a brace", "const TICK = /`{/;\n"),
                            ("a template string nested in a template string", "const n = 1;\nconst T = `a${n ? `x'` : 'y'}b`;\n"),
                            ("a template string with a quoted brace", "const T = `a${n ? '}' : \"{\"}b`;\n"),
                            ("a comment with an apostrophe", "/* the site's settings; don't remove */\n"),
                            ("a division that looks like a regex", "const half = 4 / 2; const q = '/';\n")):
            with self.subTest(name=name):
                self.assertEqual(self.set(above + self.CONFIG, themeColor="#b4531a"), (above + want, [("themeColor", "#000000", "#b4531a")]))
        inside = self.CONFIG.replace("  locale: 'en',\n", "  locale: 'en',\n  apostrophe: /it's/,\n  fmt: (s: string) => { return s + '}' + \"{\"; },\n")
        self.assertEqual(self.set(inside, themeColor="#b4531a")[0], inside.replace("'#000000'", "'#b4531a'"), "nor anything inside the block above the line")

    def test_a_line_written_another_way_is_refused_and_quoted(self):
        for name, line in (("a choice between two values", "  themeColor: dark ? '#111111' : '#000000',\n"),
                           ("a value joined from two", "  themeColor: '#000000' + '',\n"),
                           ("a value with a type after it", "  themeColor: '#000000' as string,\n"),
                           ("a name in place of the value", "  themeColor: BRAND,\n"),
                           ("a colour by name", "  themeColor: 'black',\n"),
                           ("a quoted key", "  'themeColor': '#000000',\n"),
                           ("a space before the colon", "  themeColor : '#000000',\n"),
                           ("another entry before it on the line", "  locale2: 'en', themeColor: '#000000',\n"),
                           ("another entry after it on the line", "  themeColor: '#000000', locale2: 'en',\n"),
                           ("a block comment after it", "  themeColor: '#000000', /* brand */\n"),
                           ("five digits", "  themeColor: '#00000',\n"),
                           ("the value on the next line", "  themeColor:\n    '#000000',\n")):
            with self.subTest(name=name):
                text = self.CONFIG.replace(self.OWN, line)
                message = self.refused(text, "line 10 is written another way: `%s" % line.split("\n")[0].strip()[:20], themeColor="#b4531a")
                self.assertEqual(self.line_asked_for(message), "themeColor: '#b4531a',")
        for name, value in (("an escaped single quote", "'/it\\'s.png'"), ("an escaped double quote", '"/say-\\"hi\\".png"'), ("an escaped backslash", "'/a\\\\b.png'"),
                            ("a name in place of the value", "LOGO"), ("a template string", "`/images/logo.png`")):
            with self.subTest(name=name):
                message = self.refused(self.CONFIG.replace(self.LOGO, "  logo: %s,\n" % value), "is written another way: `logo: ", logo="/images/logo.png")
                self.assertEqual(self.line_asked_for(message), "logo: '/images/logo.png',")

    def test_a_name_that_stands_more_than_once_is_refused_with_every_line_it_stands_on_whatever_the_other_one_is(self):
        # which one the site reads cannot be known from the text: a later key wins, a comment does not count,
        # and this tool cannot tell the two apart. So the name stands once, or nothing is edited.
        after_own = self.OWN + "%s"
        for name, text, lines in (
                ("a copy in a line comment", self.CONFIG.replace(self.OWN, self.OWN + "  // themeColor: '#111111',\n"), "lines 10 and 11"),
                ("a copy of the whole block in a block comment", "/*\nexport const SITE2 = {\n  themeColor: '#111111',\n};\n*/\n" + self.CONFIG, "lines 3 and 15"),
                ("a copy in a template string", "const notes = `\n  themeColor: '#111111',\n`;\n" + self.CONFIG, "lines 2 and 13"),
                ("the same key in another object above", "export const PRINT = {\n  themeColor: '#111111',\n} as const;\n" + self.CONFIG, "lines 2 and 13"),
                ("the same key in an object inside SITE", self.CONFIG.replace("export const SITE = {\n", "export const SITE = {\n  print: {\n    themeColor: '#111111',\n  },\n"), "lines 7 and 13"),
                ("an object inside SITE on the line itself", self.CONFIG.replace(self.OWN, "  nav: { themeColor: '#111111' }, themeColor: '#000000',\n"), "lines 10 and 10"),
                ("the key a second time, quoted", self.CONFIG.replace(self.OWN, after_own % "  'themeColor': '#111111',\n"), "lines 10 and 11"),
                ("the key a second time, computed", self.CONFIG.replace(self.OWN, after_own % "  ['themeColor']: '#111111',\n"), "lines 10 and 11"),
                ("the name alone further down (a shorthand entry, which wins)", "const themeColor = '#111111';\n" + self.CONFIG.replace("  tagline:", "  themeColor,\n  tagline:"), "lines 1, 11 and 14"),
                ("a getter of that name further down", self.CONFIG.replace("  tagline:", "  get themeColor() { return '#111111'; },\n  tagline:"), "lines 10 and 13"),
                ("an assignment after the block", self.CONFIG + "(SITE as { themeColor: string }).themeColor = '#111111';\n", "lines 10, 74 and 74"),
                ("the name in the comment on its own line", self.CONFIG.replace("// matches the brand primary", "// themeColor matches the brand primary"), "lines 10 and 10"),
                ("the name as a value", self.CONFIG.replace(self.OWN, "  key: 'themeColor',\n" + self.OWN), "lines 10 and 11")):
            with self.subTest(name=name):
                self.assertNotEqual(text, self.CONFIG)
                count = len(re.findall(r"\d+", lines))
                self.refused(text, "the name `themeColor` stands %d times in the file (%s)" % (count, lines), themeColor="#b4531a")
        for name, text in (("the key twice in COMPANY", self.CONFIG.replace(self.LOGO, self.LOGO + "  'logo': '/other.png',\n")),
                           ("a comment in COMPANY that names it", self.CONFIG.replace(self.LOGO, "  // the logo, square\n" + self.LOGO)),
                           ("an object inside COMPANY", self.CONFIG.replace(self.LOGO, "  parent: { logo: '/images/parent.png' },\n" + self.LOGO))):
            with self.subTest(name=name):
                self.refused(text, "the name `logo` stands 2 times in the lines of `export const COMPANY`", logo="/images/logo.png")

    def test_a_longer_name_and_the_name_outside_its_blocks_lines_are_not_the_name(self):
        longer = self.CONFIG.replace(self.OWN, "  darkthemeColor: '#111111',\n  themeColor2: '#222222',\n  $themeColor: '#333333',\n" + self.OWN)
        self.assertEqual(self.set(longer, themeColor="#b4531a")[0], longer.replace(self.OWN, self.OWN.replace("#000000", "#b4531a")))
        # `logo` is counted in COMPANY's lines only: the word is an everyday one, and stands in the value itself
        elsewhere = self.CONFIG.replace("export const SAME_AS: string[] = [", "// the logo: see COMPANY\nexport const SAME_AS: string[] = [\n  // logo: '/x.png',") \
                               .replace(self.LOGO, "  logoAlt: 'the logo',\n".replace("the logo", "our mark") + "  logo: '/images/mine.png',\n")
        new, changes = self.set(elsewhere, logo="/images/logo.png")
        self.assertEqual(changes, [("logo", "/images/mine.png", "/images/logo.png")])
        self.assertIn("  // logo: '/x.png',", new)
        self.unchanged(self.CONFIG, logo="/images/logo.png")   # '/images/logo.png' holds the word: what the line's own quotes hold is not counted

    def test_a_block_that_cannot_be_found_once_is_refused_and_so_is_a_name_outside_it(self):
        for name, text, saying in (
                ("declared with let", self.CONFIG.replace("export const SITE = {", "export let SITE = {"), "no line that starts `export const SITE`"),
                ("exported further down", self.CONFIG.replace("export const SITE = {", "const SITE = {") + "export { SITE };\n", "no line that starts `export const SITE`"),
                ("two spaces in the declaration", self.CONFIG.replace("export const SITE = {", "export const  SITE = {"), "no line that starts `export const SITE`"),
                ("the block twice, one of them in a comment", "/*\nexport const SITE = {\n  url: 'old',\n};\n*/\n" + self.CONFIG, "2 lines (lines 2 and 10), not one, that start `export const SITE`"),
                ("no closing brace at the start of a line", self.CONFIG.split("} as const;")[0].rstrip("\n") + " };\n", "no line after line 5 that starts with `}`"),
                ("the whole block on one line", self.CONFIG.replace(self.OWN, "").replace("export const SITE = {\n", "export const SITE = { themeColor: '#000000',\n"),
                 "the name `themeColor` stands on line 5, which is not between those two lines (they are lines 5 and 17)"),
                ("the line below the block", self.CONFIG.replace(self.OWN, "").replace("} as const;\n", "} as const;\n  themeColor: '#000000',\n", 1),
                 "the name `themeColor` stands on line 18, which is not between those two lines (they are lines 5 and 17)"),
                ("no such line", self.CONFIG.replace("themeColor:", "colour:"), "the name `themeColor` is not in the file")):
            with self.subTest(name=name):
                self.refused(text, saying, themeColor="#b4531a")
        self.refused(self.CONFIG.replace(self.LOGO, ""), "the name `logo` is not in the lines of `export const COMPANY`", logo="/images/logo.png")
        # a longer name that starts the same is another constant
        other = "export const SITE_URL = 'https://example.com';\nexport const SITE$ = {\n};\n" + self.CONFIG
        self.assertEqual(self.set(other, themeColor="#b4531a")[1], [("themeColor", "#000000", "#b4531a")])

    def test_a_line_of_an_object_inside_the_block_is_not_the_blocks_own_line(self):
        nested = self.CONFIG.replace(self.OWN, "  print: {\n    themeColor: '#000000',\n  },\n")
        self.refused(nested, "line 11 is not indented as the first line of the block is, as if it were a line of an object inside SITE", themeColor="#b4531a")

    def test_what_stands_further_down_in_the_block_and_could_set_the_value_again_without_naming_it_is_refused(self):
        # a later entry wins in the browser, and a spread, a computed key or an escaped name does not show what it sets
        for name, later, saying in (("a spread", "  ...OVERRIDES,\n", "line 18, further down in the same block, holds `...`"),
                                    ("a spread on a line with something else", "  extra: 1, ...OVERRIDES,\n", "line 18, further down in the same block, holds `...`"),
                                    ("a computed key", "  [KEY]: '#111111',\n", "line 18, further down in the same block, holds `[`"),
                                    ("a computed key after another entry on the line", "  extra: 1, [KEY]: '#111111',\n", "line 18, further down in the same block, holds `[`"),
                                    ("a getter with a computed name", "  get [KEY]() { return '#111111'; },\n", "line 18, further down in the same block, holds `[`"),
                                    ("a list, which this tool cannot tell from a computed key", "  tags: ['a', 'b'],\n", "line 18, further down in the same block, holds `[`"),
                                    ("the name spelt with an escape, quoted", "  'theme\\u0043olor': '#111111',\n", "line 18, further down in the same block, holds `\\u`"),
                                    ("the name spelt with an escape, bare", "  theme\\u{43}olor: '#111111',\n", "line 18, further down in the same block, holds `\\u`"),
                                    ("the name spelt with another escape", "  'theme\\x43olor': '#111111',\n", "line 18, further down in the same block, holds `\\x`")):
            with self.subTest(name=name):
                text = self.CONFIG.replace("} as const;\n", later + "} as const;\n", 1)
                message = self.refused(text, saying, themeColor="#b4531a")
                self.assertIn("which can set the theme colour again without naming it. Move the `themeColor` line down to just above the block's closing `}`, then run this again", message)
                # what the sentence says to do, done: the line moved to just above the closing brace
                moved = text.replace(self.OWN, "").replace("} as const;\n", self.OWN + "} as const;\n", 1)
                self.assertEqual(self.set(moved, themeColor="#b4531a")[1], [("themeColor", "#000000", "#b4531a")])
        before = self.CONFIG.replace("export const SITE = {\n", "export const SITE = {\n  ...BASE,\n  [KEY]: '#111111',\n  'th\\u0065me': 1,\n  tags: ['a'],\n")
        self.assertEqual(self.set(before, themeColor="#b4531a")[1], [("themeColor", "#000000", "#b4531a")], "above the line they are overridden by it, and are no reason to refuse")
        outside = self.CONFIG.replace("export const COMPANY", "const LIST = ['a', ...more, 'caf\\u00e9'];\nexport const COMPANY")
        self.assertEqual(self.set(outside, themeColor="#b4531a")[1], [("themeColor", "#000000", "#b4531a")], "and outside the block they are nothing to it")

    def follow(self, text, message, name="themeColor", const="SITE"):
        """Do what a refusal says: write the one line it quotes inside the block, and the name nowhere else."""
        line = self.line_asked_for(message)
        word = re.compile(r"(?<![\w$])%s(?![\w$])" % name)
        lines = text.split("\n")
        start = next(i for i, l in enumerate(lines) if l.startswith("export const %s " % const))
        end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("}"))
        scope = range(len(lines)) if name == "themeColor" else range(start, end + 1)
        kept = [l for i, l in enumerate(lines) if not (i in scope and word.search(l))]
        at = next(i for i, l in enumerate(kept) if l.startswith("export const %s " % const))
        close = next(i for i in range(at + 1, len(kept)) if kept[i].startswith("}"))
        return "\n".join(kept[:close] + ["  " + line] + kept[close:])

    def test_doing_what_a_refusal_says_makes_the_next_run_go_through_and_leaves_her_line_as_she_wrote_it(self):
        cases = (("written another way", self.CONFIG.replace(self.OWN, "  themeColor: dark ? '#111111' : '#000000',\n"), "themeColor"),
                 ("twice", self.CONFIG.replace(self.OWN, self.OWN + "  // themeColor: '#111111',\n"), "themeColor"),
                 ("in another object too", "export const PRINT = {\n  themeColor: '#111111',\n} as const;\n" + self.CONFIG, "themeColor"),
                 ("not there", self.CONFIG.replace(self.OWN, ""), "themeColor"),
                 ("below the block", self.CONFIG.replace(self.OWN, "").replace("} as const;\n", "} as const;\n  themeColor: '#000000',\n", 1), "themeColor"),
                 ("in an object inside the block", self.CONFIG.replace(self.OWN, "  print: {\n    themeColor: '#000000',\n  },\n"), "themeColor"),
                 ("a regex with a quote above, and the line written another way", "const APOS = /'/g;\n" + self.CONFIG.replace(self.OWN, "  themeColor: BRAND,\n"), "themeColor"),
                 ("logo escaped", self.CONFIG.replace(self.LOGO, "  logo: '/it\\'s.png',\n"), "logo"),
                 ("logo twice", self.CONFIG.replace(self.LOGO, self.LOGO + "  'logo': '/other.png',\n"), "logo"),
                 ("logo not there", self.CONFIG.replace(self.LOGO, ""), "logo"))
        for label, text, name in cases:
            with self.subTest(label=label):
                want = {name: "#b4531a" if name == "themeColor" else "/images/logo.png"}
                with self.assertRaises(Refusal) as cm:
                    self.set(text, **want)
                mended = self.follow(text, str(cm.exception), name, "SITE" if name == "themeColor" else "COMPANY")
                self.assertIn("  %s\n" % self.line_asked_for(str(cm.exception)), mended)
                self.unchanged(mended, **want)
        # the block that is not found: written as the starter writes it
        for label, text, mend in (("let", self.CONFIG.replace("export const SITE = {", "export let SITE = {"), lambda t: t.replace("export let SITE", "export const SITE")),
                                  ("a commented copy of the block", "/*\nexport const SITE = {\n  url: 'old',\n};\n*/\n" + self.CONFIG, lambda t: t.split("*/\n", 1)[1]),
                                  ("no closing line", self.CONFIG.split("} as const;")[0].rstrip("\n") + " };\n", lambda t: t.replace(" };\n", "\n};\n"))):
            with self.subTest(label=label):
                message = self.refused(text, "", themeColor="#b4531a")
                self.assertRegex(message, r"(Write `export const SITE = \{` at the start of a line|Leave one `export const SITE` in the file|Close the block with a `\}` at the start of a line)")
                self.assertEqual(self.set(mend(text), themeColor="#b4531a")[1], [("themeColor", "#000000", "#b4531a")])


class Manifest(LineRule):
    rel, code = "public/manifest.webmanifest", "manifest-layout"
    MANIFEST = T.starter_file("public/manifest.webmanifest")
    BOTH = {"theme_color": "#b4531a", "background_color": "#fff8ee"}

    def test_theme_is_the_primary_and_background_the_light_page_colour(self):
        new, changes = self.set(self.MANIFEST, **self.BOTH)
        data = json.loads(new)
        self.assertEqual((data["theme_color"], data["background_color"]), ("#b4531a", "#fff8ee"))
        self.assertEqual(changes, [("theme_color", "#000000", "#b4531a"), ("background_color", "#ffffff", "#fff8ee")])
        self.assertEqual(len(changed_lines(self.MANIFEST, new)), 4)
        self.assertEqual(data["icons"], json.loads(self.MANIFEST)["icons"])
        self.unchanged(new, **self.BOTH)

    def test_a_manifest_that_is_not_valid_json_is_refused_as_that_before_anything_is_edited(self):
        # also when both colours stand in it as lines that could be edited: what a browser makes of it is not known
        for name, text in (("a comma too many", self.MANIFEST.replace('"standalone",', '"standalone",,')),
                           ("a comma before the closing brace", self.MANIFEST.replace('  ]\n}', '  ],\n}')),
                           ("a comment", "// the manifest\n" + self.MANIFEST), ("empty", ""), ("cut short", self.MANIFEST[:200]),
                           ("nested deeper than can be read", "[" * 100000)):
            with self.subTest(name=name):
                with self.assertRaises(Refusal) as cm:
                    self.set(text, **self.BOTH)
                self.assertEqual(cm.exception.code, "manifest-layout")
                self.assertIn("public/manifest.webmanifest is not valid JSON (", str(cm.exception))
                self.assertIn("so this tool does not edit it. Mend the file so that it is valid JSON", str(cm.exception))
                self.assertNotIn("after the colours were set", str(cm.exception))
        with self.assertRaises(Refusal) as cm:
            self.set('[{"background_color": "#ffffff", "theme_color": "#000000"}]', **self.BOTH)
        self.assertIn("does not hold one object in braces at its top level", str(cm.exception))

    def test_a_manifest_without_the_keys_is_refused(self):
        for key in ("theme_color", "background_color"):
            with self.subTest(key=key):
                message = self.refused(self.MANIFEST.replace('"%s"' % key, '"x_%s"' % key), 'the name "%s" is not in the file' % key, **self.BOTH)
                self.assertEqual(self.line_asked_for(message), '"%s": "%s",' % (key, self.BOTH[key]))

    NESTED = '  "lang": "en",\n  "shortcuts": [{ "name": "x", "url": "/x", "theme_color": "#111111", "background_color": "#222222" }],'

    def nested(self, **own):
        text = self.MANIFEST.replace('  "lang": "en",', self.NESTED, 1)
        for key, value in own.items():
            was = json.loads(self.MANIFEST)[key]
            self.assertEqual(text.count('"%s": "%s"' % (key, was)), 1)
            text = text.replace('"%s": "%s"' % (key, was), '"%s": "%s"' % (key, value))
        self.assertEqual(json.loads(text)["shortcuts"][0]["theme_color"], "#111111")
        return text

    def test_a_colour_that_must_change_is_never_set_by_its_place_in_the_file(self):
        after_own = self.MANIFEST.replace('  "icons"', '  "related": { "theme_color": "#111111" },\n  "icons"', 1)
        self.assertEqual(json.loads(after_own)["related"]["theme_color"], "#111111")
        twice = self.MANIFEST.replace('  "lang": "en",', '  "lang": "en",\n  "theme_color": "#111111",')
        self.assertEqual(json.loads(twice)["theme_color"], "#000000", "the last one is what is read")
        for name, text, key, lines in (("another entry's colour before the manifest's own", self.nested(), "theme_color", "lines 6 and 10"),
                                       ("another entry's colour after the manifest's own", after_own, "theme_color", "lines 9 and 10"),
                                       ("only the background still to set", self.nested(theme_color="#b4531a"), "background_color", "lines 6 and 9"),
                                       ("only the theme colour still to set", self.nested(background_color="#fff8ee"), "theme_color", "lines 6 and 10"),
                                       ("the manifest's own key twice", twice, "theme_color", "lines 6 and 10")):
            with self.subTest(name=name):
                message = self.refused(text, 'the name "%s" stands 2 times in the file (%s)' % (key, lines), **self.BOTH)
                self.assertIn("Set the value on the manifest's own line yourself, then run this again", message)

    def test_a_manifest_that_already_holds_both_colours_is_not_edited_at_all_whatever_else_in_it_has_a_colour_of_that_name(self):
        # what she is told to do after the refusal above: set the manifest's own two by hand. The next run
        # must then leave the file alone, not edit the first line of that name and call it done.
        self.unchanged(self.nested(theme_color="#b4531a", background_color="#fff8ee"), **self.BOTH)

    def test_a_colour_she_wrote_in_capitals_or_in_another_spelling_is_the_same_colour(self):
        for theme, background in (("#B4531A", "#FFF8EE"), ("#b4531aff", "#FFF8EEFF"), ("rgb(180, 83, 26)", "#fff8ee")):
            with self.subTest(theme=theme):
                self.unchanged(self.nested(theme_color=theme, background_color=background), **self.BOTH)
        self.unchanged(self.MANIFEST.replace('"#000000"', '"black"').replace('"#ffffff"', '"#FFF"'), theme_color="#000000", background_color="#ffffff")

    def test_a_colour_that_is_already_right_is_left_alone_and_the_other_is_set(self):
        half = self.MANIFEST.replace('"theme_color": "#000000"', '"theme_color": "#B4531A"')
        new, changes = self.set(half, **self.BOTH)
        self.assertEqual(changes, [("background_color", "#ffffff", "#fff8ee")])
        self.assertEqual(len(changed_lines(half, new)), 2)
        self.assertIn('"theme_color": "#B4531A"', new)

    def test_a_value_with_an_escaped_quote_is_replaced_whole_and_shown_as_it_was(self):
        text = self.MANIFEST.replace('"theme_color": "#000000"', '"theme_color": "bl\\"ack"')
        self.assertEqual(json.loads(text)["theme_color"], 'bl"ack')
        new, changes = self.set(text, **self.BOTH)
        self.assertEqual(new, self.set(self.MANIFEST, **self.BOTH)[0])
        self.assertEqual(changes[0], ("theme_color", 'bl"ack', "#b4531a"))

    def test_a_value_that_is_no_text_or_a_name_that_is_not_the_manifests_own_entry_is_refused(self):
        for name, value in (("a number", "0"), ("nothing", "null"), ("a list", '["#000000"]')):
            with self.subTest(name=name):
                self.refused(self.MANIFEST.replace('"theme_color": "#000000"', '"theme_color": %s' % value), 'line 9 is written another way: `"theme_color": %s' % value[:4], **self.BOTH)
        split = self.MANIFEST.replace('"theme_color": "#000000"', '"theme_color":\n    "#000000"')
        self.refused(split, 'line 9 is written another way: `"theme_color":`', **self.BOTH)
        # the manifest's own key spelt with an escape, and the plain name once, inside another entry
        hidden = self.MANIFEST.replace('"theme_color": "#000000"', '"theme\\u005fcolor": "#000000"').replace('  "lang": "en",', '  "lang": "en",\n  "related": { "theme_color": "#111111" },')
        self.assertEqual(json.loads(hidden)["theme_color"], "#000000")
        self.refused(hidden, 'the one place where "theme_color" stands (line 6) is not the manifest\'s own entry', **self.BOTH)
        only_inside = self.MANIFEST.replace('  "theme_color": "#000000",\n', "").replace('  "lang": "en",', '  "lang": "en",\n  "related": { "theme_color": "#111111" },')
        self.refused(only_inside, 'the one place where "theme_color" stands (line 6) is not the manifest\'s own entry', **self.BOTH)

    def test_a_manifest_on_one_line_or_with_the_name_inside_a_text_is_set_where_the_name_stands_once(self):
        one = '{"name":"X","background_color":"#ffffff","theme_color":"#000000"}'
        self.assertEqual(self.set(one, **self.BOTH)[0], '{"name":"X","background_color":"#fff8ee","theme_color":"#b4531a"}')
        said = self.MANIFEST.replace('"lang": "en",', '"description": "set \\"theme_color\\": here",')
        self.assertEqual(json.loads(self.set(said, **self.BOTH)[0])["description"], 'set "theme_color": here')
        odd = self.MANIFEST.replace('"lang": "en",', '"ratio": NaN, "big": 1e999,')   # what Python's reading lets through and compares unequal to itself
        self.assertEqual(self.set(odd, **self.BOTH)[1], [("theme_color", "#000000", "#b4531a"), ("background_color", "#ffffff", "#fff8ee")])

    def test_doing_what_a_refusal_says_makes_the_next_run_go_through_and_leaves_the_file_as_she_wrote_it(self):
        def write_own_line(text, message, key):
            """Write the line the refusal quotes as the manifest's own: the last line of that name at the top level, or a new one."""
            line = "  " + self.line_asked_for(message)
            lines = text.split("\n")
            own = [i for i, l in enumerate(lines) if l.startswith('  "%s"' % key)]
            if own:
                lines[own[-1]] = line
                return "\n".join(lines)
            return text.replace("{\n", "{\n" + line + "\n", 1)
        for label, text in (("in another entry too", self.nested()), ("not there", self.MANIFEST.replace('  "theme_color": "#000000",\n', "")),
                            ("a number", self.MANIFEST.replace('"theme_color": "#000000"', '"theme_color": 0')),
                            ("only inside another entry", self.MANIFEST.replace('  "theme_color": "#000000",\n', "").replace('  "lang": "en",', '  "lang": "en",\n  "related": { "theme_color": "#111111" },'))):
            with self.subTest(label=label):
                for _round in range(3):   # one refusal for each colour at most, then it goes through
                    try:
                        new, changes = self.set(text, **self.BOTH)
                        break
                    except Refusal as r:
                        key = re.search(r'the manifest\'s own "(\w+)"', str(r)).group(1)
                        text = write_own_line(text, str(r), key)
                        json.loads(text)
                data = json.loads(new)
                self.assertEqual((data["theme_color"], data["background_color"]), ("#b4531a", "#fff8ee"))
                self.unchanged(new, **self.BOTH)
        broken = self.MANIFEST.replace('"standalone",', '"standalone",,')
        with self.assertRaises(Refusal):
            self.set(broken, **self.BOTH)
        self.assertEqual(self.set(broken.replace(",,", ","), **self.BOTH), self.set(self.MANIFEST, **self.BOTH), "mended as the refusal says, it is edited like any other")
        listed = "[%s]" % self.MANIFEST
        with self.assertRaises(Refusal) as cm:
            self.set(listed, **self.BOTH)
        self.assertIn("Write it as the starter's manifest is written, then run this again.", str(cm.exception))
        self.assertEqual(self.set(listed[1:-1], **self.BOTH), self.set(self.MANIFEST, **self.BOTH))


class ShareCards(LineRule):
    rel, code = "scripts/generate_og_cards.py", "og-layout"
    OG = T.starter_file("scripts/generate_og_cards.py")
    NAMES = ("BG_TOP", "BG_BOT", "TITLE_COL", "SUB_COL", "ACCENT", "FOOTER_COL")
    WANT = {"BG_TOP": "#2a1f17", "BG_BOT": "#1a120d", "TITLE_COL": "#fbeedd", "SUB_COL": "#e2874a", "ACCENT": "#e2874a", "FOOTER_COL": "#c4ae98"}

    def want(self, palette):
        return {name: palette.dark[key] for name, key in _site.OG_COLOURS}

    def test_the_cards_take_the_dark_themes_colours(self):
        self.assertEqual(self.want(bakery()), self.WANT)
        self.assertEqual(tuple(name for name, _key in _site.OG_COLOURS), self.NAMES)
        new, changes = self.set(self.OG, **self.WANT)
        for name, h in self.WANT.items():
            rgb = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
            self.assertRegex(new, r"(?m)^%s = \(%d, %d, %d\) +# " % ((name,) + rgb), "the comment after the numbers is kept")
        self.assertEqual(len(changed_lines(self.OG, new)), 12)
        self.assertEqual(changes, [("BG_TOP", "#1e2140", "#2a1f17"), ("BG_BOT", "#0a0b1e", "#1a120d"), ("TITLE_COL", "#ffffff", "#fbeedd"),
                                   ("SUB_COL", "#8aa0ff", "#e2874a"), ("ACCENT", "#8aa0ff", "#e2874a"), ("FOOTER_COL", "#9696aa", "#c4ae98")])
        self.unchanged(new, **self.WANT)

    def test_the_card_colours_read_well_on_the_cards_own_background(self):
        # title, subtitle and footer sit on a gradient between the dark surface and the dark background
        p = bakery()
        from _colour import ratio
        for fg in ("heading", "accent", "muted"):
            for bg in ("surface", "bg"):
                self.assertGreaterEqual(ratio(p.dark[fg], p.dark[bg]), 4.5)

    def test_the_emblems_line_is_never_touched_whatever_it_says_and_however_often_it_stands(self):
        # the share cards' emblem is not this tool's to set, to take out or to judge: the LOGO line is hers
        self.assertIn("\nLOGO = None ", self.OG)
        for name, text in (("the starter's", self.OG), ("the picture this tool installs", self.OG.replace("LOGO = None", 'LOGO = ROOT / "public/images/logo.png"')),
                           ("with single quotes", self.OG.replace("LOGO = None", "LOGO = ROOT / 'public/images/logo.png'")),
                           ("a picture of her own", self.OG.replace("LOGO = None", 'LOGO = ROOT / "public/mine.png"')),
                           ("twice", self.OG.replace("# Home + fallback card", 'LOGO = ROOT / "public/mine.png"\n\n# Home + fallback card', 1)),
                           ("not there", self.OG.replace("LOGO = None", "EMBLEM = None")),
                           ("something that is no path", self.OG.replace("LOGO = None", "LOGO = pick_one()"))):
            with self.subTest(name=name):
                new, _changes = self.set(text, **self.WANT)
                self.assertEqual([l for l in new.splitlines() if "LOGO" in l or "EMBLEM" in l], [l for l in text.splitlines() if "LOGO" in l or "EMBLEM" in l])
                self.assertEqual(len(changed_lines(text, new)), 12)
        self.assertFalse([name for name in dir(_site) if "logo" in name.lower() and name != "LOGO_ADDRESS" or "emblem" in name.lower()], "nothing in the module reads or writes it")

    def test_a_line_written_another_way_is_refused_naming_the_line(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                text = re.sub(r"(?m)^%s = \(.*\)" % name, "%s = pick_a_colour()" % name, self.OG)
                message = self.refused(text, "is written another way: `%s = pick_a_colour()" % name, **self.WANT)
                rgb = tuple(int(self.WANT[name][i:i + 2], 16) for i in (1, 3, 5))
                self.assertEqual(self.line_asked_for(message), "%s = (%d, %d, %d)" % ((name,) + rgb))
        for name, line in (("a hex text", 'BG_TOP = "#1e2140"'), ("a sum", "BG_TOP = (30, 33, 64) + extra"), ("two numbers", "BG_TOP = (30, 33)"),
                           ("four numbers", "BG_TOP = (30, 33, 64, 255)"), ("a decimal", "BG_TOP = (30.0, 33, 64)"), ("a typed name", "BG_TOP: tuple = (30, 33, 64)"),
                           ("two names at once", "BG_TOP = SPARE = (30, 33, 64)"), ("added to", "BG_TOP += (1,)"),
                           ("a number longer than any colour's, which Python itself would not read", "BG_TOP = (%s, 33, 64)" % ("9" * 5000))):
            with self.subTest(name=name):
                self.refused(self.OG.replace("BG_TOP = (30, 33, 64)", line, 1), "line 52 is written another way: `%s" % line[:12], **self.WANT)

    def test_a_name_that_is_set_on_more_than_one_line_is_refused_with_the_lines_wherever_and_however_the_other_one_stands(self):
        # Python uses the last one it runs: an edit of the first would change nothing and be reported as done
        for name, text, lines in (
                ("again further down", self.OG.replace("# Home + fallback card", "BG_BOT = (200, 200, 200)   # my override\n\n# Home + fallback card", 1), "BG_BOT"),
                ("again at the end of the block", self.OG.replace("FOOTER_COL = (150, 150, 170)", "FOOTER_COL = (150, 150, 170)\nTITLE_COL = (10, 10, 10)", 1), "TITLE_COL"),
                ("again, indented, under a condition", self.OG.replace("# Home + fallback card", "if True:\n    SUB_COL = (1, 2, 3)\n\n# Home + fallback card", 1), "SUB_COL"),
                ("again, after another statement on the line", self.OG.replace("# Home + fallback card", "x = 1; ACCENT = (1, 2, 3)\n\n# Home + fallback card", 1), "ACCENT"),
                ("again, together with another name", self.OG.replace("# Home + fallback card", "FOOTER_COL, spare = (1, 2, 3), 4\n\n# Home + fallback card", 1), "FOOTER_COL"),
                ("again, as the second of two names", self.OG.replace("BG_TOP = (30, 33, 64)", "BG_TOP = BG_BOT = (30, 33, 64)", 1), "BG_BOT"),
                ("again, in a text that runs over lines", self.OG.replace("# Home + fallback card", 'NOTE = """\nBG_TOP = (1, 2, 3)\n"""\n\n# Home + fallback card', 1), "BG_TOP"),
                ("again, in a comment (it holds `NAME =`, and this tool does not read Python)", self.OG.replace("# Home + fallback card", "# BG_TOP = (1, 2, 3)\n\n# Home + fallback card", 1), "BG_TOP")):
            with self.subTest(name=name):
                self.assertNotEqual(text, self.OG)
                want = {k: v for k, v in self.WANT.items() if k == lines}
                message = self.refused(text, "2 lines begin with %s or set it (lines " % lines, **want)
                self.assertIn("Write that one line there yourself, and set %s on no other line" % lines, message)

    def test_a_line_that_only_names_a_colour_or_sets_a_longer_name_does_not_set_it(self):
        text = self.OG.replace("# Home + fallback card", "# BG_TOP is the top of the gradient\nprint(BG_TOP == BG_BOT, TITLE_COL)\nspare = dict(top=BG_TOP)\nMY_BG_TOP = (9, 9, 9)\n"
                               "BG_TOP2 = (8, 8, 8)\ncard.BG_TOP = (7, 7, 7)\n\n# Home + fallback card", 1)
        new, changes = self.set(text, **self.WANT)
        self.assertEqual(len(changes), 6)
        for kept in ("# BG_TOP is the top of the gradient\n", "MY_BG_TOP = (9, 9, 9)\n", "BG_TOP2 = (8, 8, 8)\n", "card.BG_TOP = (7, 7, 7)\n"):
            self.assertIn(kept, new)

    def test_numbers_that_are_no_colour_are_set_all_the_same_and_shown_as_they_stood(self):
        odd = self.OG.replace("BG_TOP = (30, 33, 64)", "BG_TOP = (300, 33, 64)").replace("BG_BOT = (10, 11, 30)", "BG_BOT = ( 010,11 , 999 )")
        new, changes = self.set(odd, **self.WANT)
        self.assertEqual(changes[:2], [("BG_TOP", "(300, 33, 64)", "#2a1f17"), ("BG_BOT", "(10, 11, 999)", "#1a120d")])
        self.assertIn("\nBG_TOP = (42, 31, 23) ", new)
        self.assertIn("\nBG_BOT = (26, 18, 13) ", new)

    def test_a_colour_that_already_stands_there_is_not_edited_however_its_numbers_are_spaced(self):
        done = self.set(self.OG, **self.WANT)[0].replace("BG_TOP = (42, 31, 23)", "BG_TOP = ( 42,31 ,  23 )")
        self.assertIn("BG_TOP = ( 42,31 ,  23 )", done)
        self.unchanged(done, **self.WANT)

    def test_a_text_colour_that_passes_on_both_ends_of_the_gradient_can_still_fail_in_between(self):
        # the card's background runs from the dark surface to the dark background; a grey that reads on
        # white and on black does not read on the greys between them
        self.assertEqual(_site.og_low_contrast(bakery()), [])
        p = bakery()
        from _colour import ratio
        p.dark.update({"heading": "#767676", "accent": "#767676", "muted": "#767676", "surface": "#ffffff", "bg": "#000000"})
        for end in ("surface", "bg"):
            self.assertGreaterEqual(ratio("#767676", p.dark[end]), 4.5, "it passes on both ends")
        low = _site.og_low_contrast(p)
        self.assertEqual([(k, h) for k, h, _r in low], [("heading", "#767676"), ("accent", "#767676"), ("muted", "#767676")])
        for _k, _h, worst in low:
            self.assertEqual(worst, 1.0, "one row of the gradient is that very grey")

    def test_the_gradient_is_the_one_the_generator_draws(self):
        # the same rows, the same rounding: if the starter's generator changes its gradient, this says so
        self.assertIn("W, H = 1200, %d" % _site.OG_ROWS, self.OG)
        self.assertIn("t = y / (h - 1)", self.OG)
        self.assertIn("px[0, y] = tuple(round(top[i] + (bot[i] - top[i]) * t) for i in range(3))", self.OG)
        self.assertIn("card = vgradient(W, H, BG_TOP, BG_BOT)", self.OG)
        for name, fill in (("TITLE_COL", "heading"), ("SUB_COL", "accent"), ("FOOTER_COL", "muted")):
            self.assertIn("fill=%s)" % name, self.OG)
            self.assertIn((name, fill), _site.OG_COLOURS)
            self.assertIn(fill, _site.OG_TEXT)

    def test_whatever_way_a_colour_is_written_in_the_palette_the_cards_get_its_three_numbers(self):
        # the palette holds every colour as #rrggbb however BRAND.md wrote it, which is what the edit relies on
        md = ("### Dark theme\n| Token | Hex |\n|---|---|\n| Heading | `#FED` |\n| Muted | `rgb(196, 174, 152)` |\n| Accent | `tomato` |\n"
              "| Background | `#1A120DFF` |\n| Surface (cards) | `hsl(25 29% 13%)` |\n")
        p = _palette.parse_tables(md)
        for value in p.dark.values():
            self.assertRegex(value, r"^#[0-9a-f]{6}$")
        new, _changes = self.set(self.OG, **self.want(p))
        for line in ("TITLE_COL = (255, 238, 221)", "FOOTER_COL = (196, 174, 152)", "SUB_COL = (255, 99, 71)", "ACCENT = (255, 99, 71)", "BG_BOT = (26, 18, 13)"):
            self.assertIn(line, new)
        self.assertRegex(new, r"(?m)^BG_TOP = \(\d+, \d+, \d+\)")

    def test_doing_what_a_refusal_says_makes_the_next_run_go_through_and_leaves_her_line_as_she_wrote_it(self):
        for label, text, name in (("written another way", self.OG.replace("BG_TOP = (30, 33, 64)", 'BG_TOP = "#1e2140"', 1), "BG_TOP"),
                                  ("set again further down", self.OG.replace("# Home + fallback card", "BG_BOT = (200, 200, 200)\n\n# Home + fallback card", 1), "BG_BOT"),
                                  ("not there", re.sub(r"(?m)^ACCENT = .*\n", "", self.OG), "ACCENT")):
            with self.subTest(label=label):
                with self.assertRaises(Refusal) as cm:
                    self.set(text, **self.WANT)
                line = self.line_asked_for(str(cm.exception))
                kept = [l for l in text.split("\n") if not re.match(r"[ \t]*%s\b" % name, l)]
                at = next(i for i, l in enumerate(kept) if l.startswith("FOOTER_COL = "))
                mended = "\n".join(kept[:at] + [line] + kept[at:])
                new, changes = self.set(mended, **self.WANT)
                self.assertNotIn(name, [n for n, _old, _new in changes], "her line already says it")
                self.assertIn("\n%s\n" % line, new)


class Gitignore(unittest.TestCase):
    def test_the_line_is_added_once(self):
        self.assertEqual(_site.add_ignore("node_modules\n"), "node_modules\nbrand-handoff/\n")
        self.assertEqual(_site.add_ignore("node_modules"), "node_modules\nbrand-handoff/\n")
        self.assertEqual(_site.add_ignore(""), "brand-handoff/\n")
        self.assertIsNone(_site.add_ignore("a\nbrand-handoff/\nb\n"))

    def test_other_spellings_of_the_same_rule_count_as_there(self):
        for line in ("brand-handoff/", "/brand-handoff/", "brand-handoff", "/brand-handoff", "brand-handoff/*"):
            with self.subTest(line=line):
                self.assertIsNone(_site.add_ignore("a\n%s\n" % line))

    def test_a_commented_or_negated_line_does_not_count(self):
        self.assertIsNotNone(_site.add_ignore("# brand-handoff/\n"))
        self.assertIsNotNone(_site.add_ignore("!brand-handoff/\n"))
        self.assertIsNotNone(_site.add_ignore("x/brand-handoff/\n"))

    def test_a_rule_that_a_later_line_takes_back_does_not_count_and_the_line_goes_at_the_end(self):
        for text in ("brand-handoff/*\n!brand-handoff/logo.svg\n", "brand-handoff/\n!brand-handoff/\n", "/brand-handoff\n!/brand-handoff/keep.zip\nnode_modules\n"):
            with self.subTest(text=text):
                self.assertEqual(_site.add_ignore(text), text + "brand-handoff/\n")
                self.assertIsNone(_site.add_ignore(text + "brand-handoff/\n"), "and once it is there, it is not added again")
        self.assertIsNone(_site.add_ignore("!brand-handoff/\nbrand-handoff/\n"), "a negation before the rule takes nothing back")

    def test_a_byte_order_mark_before_the_first_rule_does_not_hide_it(self):
        self.assertIsNone(_site.add_ignore("\ufeffbrand-handoff/\nnode_modules\n"))
        self.assertEqual(_site.add_ignore("\ufeffnode_modules\n"), "\ufeffnode_modules\nbrand-handoff/\n")

    # What a .gitignore may hold, and whether the folder's line must be added (True) or is there and holds (False).
    CASES = (
        ("", True), ("dist/\nbrand-handoff/\n", False), ("brand-handoff\n", False), ("/brand-handoff/\n", False), ("brand-handoff/*\n", False),
        ("dist/", True),
        # a later line that starts with ! may take the rule back without naming the folder
        ("brand-handoff/*\n!*.svg\n", True), ("brand-handoff/*\n!*\n", True), ("brand-handoff/*\n!brand-*/logo.zip\n", True),
        ("brand-handoff/\n!brand-*/\n", True), ("brand-handoff/*\n!brand-handoff/keep.svg\n", True), ("/brand-handoff/*\n!/brand-handoff/logo.zip\n", True),
        ("brand-handoff/\n!docs/notes.md\n", True),   # it takes nothing back, and one line too many does no harm
        ("brand-handoff/\n!brand-handoff/\nbrand-handoff/\n", False), ("!*.svg\nbrand-handoff/\n", False),
        ("brand-handoff/\n# !brand-handoff/ was here\n", False), ("brand-handoff/\n\\!important.txt\n", False), ("brand-handoff/\n  !*.svg\n", False),
        # spaces before a rule are part of it; spaces after it are not, unless a backslash keeps them
        ("  brand-handoff/\n", True), ("brand-handoff/   \n", False), ("brand-handoff/\\ \n", True),
        ("Brand-Handoff/\n", True), ("x/brand-handoff/\n", True),
        ("dist/\r\nbrand-handoff/\r\n", False), ("dist/\r\nbrand-handoff/*\r\n!*.svg\r\n", True), ("dist/\r\nnode_modules", True),
    )

    def test_the_folders_rule_counts_only_when_no_later_line_can_take_it_back_and_spaces_are_read_as_git_reads_them(self):
        for text, add in self.CASES:
            with self.subTest(text=text):
                new = _site.add_ignore(text)
                self.assertEqual(new is not None, add)
                if add:
                    end = "\r\n" if "\r\n" in text else "\n"
                    self.assertEqual(new, text + ("" if not text or text.endswith("\n") else end) + "brand-handoff/" + end, "added at the end, and nothing else moved")
                    self.assertIsNone(_site.add_ignore(new), "and once it is the last word, it is not added again")

    def test_a_file_with_windows_line_ends_gets_a_line_that_ends_the_same_way(self):
        self.assertEqual(_site.add_ignore("dist/\r\nnode_modules\r\n"), "dist/\r\nnode_modules\r\nbrand-handoff/\r\n")
        self.assertEqual(_site.add_ignore("dist/\r\nnode_modules"), "dist/\r\nnode_modules\r\nbrand-handoff/\r\n")
        self.assertNotIn("\r", _site.add_ignore("dist/\nnode_modules\n"))

    def test_the_added_line_ends_as_the_files_last_line_ends_not_as_some_line_above_it_does(self):
        # one stray CRLF further up does not make the file a Windows file
        for text, end in (("a\nb\r\nc\n", "\n"), ("a\r\nb\nc\r\n", "\r\n"), ("a\r\nb\n", "\n"), ("a\nb\r\n", "\r\n"), ("a\r\nb\nc", "\n"), ("a\nb\r\nc", "\r\n"),
                          ("a", "\n"), ("a\r\n", "\r\n"), ("\r\n", "\r\n"), ("a\rb\r", "\n")):
            with self.subTest(text=text):
                self.assertEqual(_site.add_ignore(text), text + ("" if text.endswith("\n") else end) + "brand-handoff/" + end)

    @unittest.skipUnless(shutil.which("git"), "git itself is asked whether the folder is ignored")
    def test_after_the_line_is_added_or_found_git_itself_ignores_what_is_in_the_folder(self):
        # the report says git ignores the folder: git is the judge of that, for every case above
        with tempfile.TemporaryDirectory() as repo:
            subprocess.run(["git", "init", "-q", repo], check=True, capture_output=True)
            for text, _add in self.CASES + (("\ufeffbrand-handoff/\n", False), ("\ufeffdist/\n", True)):
                with self.subTest(text=text):
                    new = _site.add_ignore(text)
                    with open(os.path.join(repo, ".gitignore"), "w", encoding="utf-8", newline="") as f:
                        f.write(text if new is None else new)
                    for kept in ("brand-handoff/logo.zip", "brand-handoff/mark.svg", "brand-handoff/preview.png"):
                        r = subprocess.run(["git", "-C", repo, "-c", "core.excludesFile=" + os.devnull, "-c", "core.ignorecase=false",
                                            "check-ignore", "-q", "--no-index", kept], capture_output=True)
                        self.assertEqual(r.returncode, 0, "%s is not ignored" % kept)


def tree(root):
    out = {}
    for base, dirs, files in os.walk(root):
        for d in dirs:
            out[os.path.relpath(os.path.join(base, d), root) + "/"] = None
        for f in files:
            p = os.path.join(base, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


class TheJournal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.site = os.path.join(self.tmp.name, "site")
        os.makedirs(os.path.join(self.site, "public", "images", "og"))
        for rel, data in {"package.json": b"{}", "public/favicon.svg": b"<svg/>", "public/images/og/default.jpg": b"jpg-old",
                          "public/images/og/other.jpg": b"jpg-two", ".gitignore": b"node_modules\n"}.items():
            with open(os.path.join(self.site, rel), "wb") as f:
                f.write(data)
        self.before = tree(self.site)
        self.j = _site.Journal(self.site)

    def test_rollback_puts_every_file_back_and_removes_what_was_made(self):
        self.j.write("public/favicon.svg", b"<svg>new</svg>")          # replaced
        self.j.write("public/favicon.ico", b"ico")                      # created
        self.j.write("public/images/logo.png", b"png")                  # created, in a folder that was there
        self.j.write("brand-handoff/pack.zip", b"zip")                  # created in a folder that was not there
        self.j.write("brand-handoff/preview.png", b"png2")
        self.j.write(".gitignore", b"node_modules\nbrand-handoff/\n")   # changed
        self.assertNotEqual(tree(self.site), self.before)
        self.j.rollback()
        self.assertEqual(tree(self.site), self.before)

    def test_a_file_written_twice_is_restored_to_what_it_was_before_the_first_write(self):
        self.j.write("public/favicon.svg", b"one")
        self.j.write("public/favicon.svg", b"two")
        self.j.rollback()
        self.assertEqual(tree(self.site), self.before)

    def test_a_folder_that_was_there_stays_and_so_does_what_it_held(self):
        # scenario 31's loose end: the package copy this run added to a brand-handoff that already existed
        os.makedirs(os.path.join(self.site, "brand-handoff"))
        with open(os.path.join(self.site, "brand-handoff", "earlier.zip"), "wb") as f:
            f.write(b"earlier")
        before = tree(self.site)
        self.j.write("brand-handoff/this-run.zip", b"new")
        self.j.write("brand-handoff/preview.png", b"p")
        self.j.rollback()
        self.assertEqual(tree(self.site), before)
        self.assertTrue(os.path.isfile(os.path.join(self.site, "brand-handoff", "earlier.zip")))

    def test_folders_made_inside_folders_all_go_the_deepest_first(self):
        self.j.write("brand-handoff/deep/er/file.txt", b"x")
        self.assertTrue(os.path.isdir(os.path.join(self.site, "brand-handoff", "deep", "er")))
        self.j.rollback()
        self.assertEqual(tree(self.site), self.before)

    def test_what_something_else_did_to_the_snapshotted_folder_is_undone_by_rollback_too(self):
        # the share-card generator writes the folder without going through the journal
        self.j.snapshot_dir("public/images/og")
        with open(os.path.join(self.site, "public/images/og/default.jpg"), "wb") as f:
            f.write(b"regenerated")
        os.remove(os.path.join(self.site, "public/images/og/other.jpg"))
        with open(os.path.join(self.site, "public/images/og/new.jpg"), "wb") as f:
            f.write(b"new card")
        self.j.rollback()
        self.assertEqual(tree(self.site), self.before)

    def test_a_folder_the_run_made_is_removed_only_when_nothing_else_is_in_it(self):
        self.j.write("brand-handoff/pack.zip", b"zip")
        with open(os.path.join(self.site, "brand-handoff", "someone-elses.txt"), "wb") as f:
            f.write(b"mine")  # put there while the run was going: not ours to delete
        self.j.rollback()
        self.assertTrue(os.path.isfile(os.path.join(self.site, "brand-handoff", "someone-elses.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.site, "brand-handoff", "pack.zip")))

    def test_the_share_card_folder_is_restored_as_a_whole(self):
        self.j.snapshot_dir("public/images/og")
        os.remove(os.path.join(self.site, "public/images/og/other.jpg"))   # what a generator that stops half way may do
        with open(os.path.join(self.site, "public/images/og/default.jpg"), "wb") as f:
            f.write(b"jpg-new")
        with open(os.path.join(self.site, "public/images/og/extra.jpg"), "wb") as f:
            f.write(b"extra")
        self.j.restore_dir("public/images/og")
        self.assertEqual(tree(self.site), self.before)

    def test_a_snapshot_of_a_folder_that_is_not_there_restores_to_not_there(self):
        self.j.snapshot_dir("public/cards")
        os.makedirs(os.path.join(self.site, "public", "cards"))
        with open(os.path.join(self.site, "public", "cards", "a.jpg"), "wb") as f:
            f.write(b"x")
        self.j.restore_dir("public/cards")
        self.assertEqual(tree(self.site), self.before)

    def test_rollback_after_a_folder_snapshot_too(self):
        self.j.snapshot_dir("public/images/og")
        self.j.write("public/images/og/default.jpg", b"new")
        self.j.write("public/favicon.ico", b"ico")
        self.j.rollback()
        self.assertEqual(tree(self.site), self.before)

    def test_what_a_write_leaves_is_the_new_file_and_no_temporary_files(self):
        self.j.write("public/favicon.ico", b"ico")
        self.assertEqual(sorted(os.listdir(os.path.join(self.site, "public"))), ["favicon.ico", "favicon.svg", "images"])

    # --- a kept folder is put back in place, file by file, the way any other file is ------------

    def og(self, *more):
        return os.path.join(self.site, "public", "images", "og", *more)

    def test_a_kept_folder_is_put_back_in_place_and_is_itself_never_deleted(self):
        self.j.snapshot_dir("public/images/og")
        folder, untouched = os.stat(self.og()).st_ino, os.stat(self.og("other.jpg")).st_ino
        with open(self.og("default.jpg"), "wb") as f:
            f.write(b"regenerated")
        self.assertEqual(self.j.restore_dir("public/images/og"), [])
        self.assertEqual(tree(self.site), self.before)
        self.assertEqual(os.stat(self.og()).st_ino, folder, "the folder is the one that was there, not a new one of the same name")
        self.assertEqual(os.stat(self.og("other.jpg")).st_ino, untouched, "and a file that is as it was is not written again")
        self.assertEqual(self.j.undone, ["public/images/og/default.jpg"])

    def test_whatever_was_done_to_a_kept_folder_it_comes_back_to_exactly_what_it_held(self):
        os.makedirs(self.og("drafts", "empty"))
        with open(self.og("drafts", "note.txt"), "wb") as f:
            f.write(b"a note")
        outside = os.path.join(self.tmp.name, "outside")
        os.makedirs(outside)
        with open(os.path.join(outside, "kept.txt"), "wb") as f:
            f.write(b"not the site's")
        before = tree(self.site)
        self.j.snapshot_dir("public/images/og")
        os.remove(self.og("other.jpg"))
        os.makedirs(self.og("other.jpg"))                       # a folder where a file was
        shutil.rmtree(self.og("drafts"))
        with open(self.og("drafts"), "wb") as f:                # a file where a folder was
            f.write(b"x")
        os.makedirs(self.og("new", "deeper"))                   # a folder it did not hold, with something in it
        with open(self.og("new", "deeper", "card.jpg"), "wb") as f:
            f.write(b"new")
        os.remove(self.og("default.jpg"))
        os.symlink(os.path.join(outside, "kept.txt"), self.og("default.jpg"))   # a link where a file was
        os.symlink(outside, self.og("linked"))                  # a link to a folder: removed as a link, never followed
        self.assertEqual(self.j.rollback(), [])
        self.assertEqual(tree(self.site), before)
        self.assertFalse(os.path.islink(self.og("default.jpg")))
        self.assertEqual(os.listdir(outside), ["kept.txt"], "what a link pointed at is not touched")
        self.assertEqual(T.read_bytes(os.path.join(outside, "kept.txt")), b"not the site's")

    def test_a_kept_folder_that_was_not_there_goes_again_with_the_folders_above_it_that_were_not_there(self):
        shutil.rmtree(os.path.join(self.site, "public", "images"))
        before = tree(self.site)
        self.j.snapshot_dir("public/images/og")
        os.makedirs(self.og("sub"))                             # what the generator does: it makes the folder
        for name in ("default.jpg", os.path.join("sub", "a.jpg")):
            with open(self.og(name), "wb") as f:
                f.write(b"made")
        self.assertEqual(self.j.rollback(), [])
        self.assertEqual(tree(self.site), before, "public/images is gone again too, and public is still there")
        self.assertEqual(self.j.rollback(), [])
        with open(os.path.join(self.site, "public", "images"), "wb") as f:   # a file made where one of those folders would be
            f.write(b"x")
        self.assertIn("public/images", [rel for rel, _why in self.j.rollback()], "is named: it was not there, and it is not this run's to delete")

    def test_putting_a_kept_folder_back_carries_on_after_a_file_that_cannot_be_put_back_and_names_it(self):
        with open(self.og("third.jpg"), "wb") as f:
            f.write(b"jpg-three")
        before = tree(self.site)
        self.j.snapshot_dir("public/images/og")
        for name in ("default.jpg", "other.jpg", "third.jpg"):
            with open(self.og(name), "wb") as f:
                f.write(b"regenerated")
        real = _site.Journal._put

        def refusing(journal, path, data, mode=0o644):
            if path.endswith("other.jpg"):
                raise PermissionError(13, "Permission denied", path)
            return real(journal, path, data, mode)
        _site.Journal._put = refusing
        try:
            left = self.j.rollback()
        finally:
            _site.Journal._put = real
        self.assertEqual(left, [("public/images/og/other.jpg", "Permission denied")])
        after = tree(self.site)
        self.assertNotEqual(after["public/images/og/other.jpg".replace("/", os.sep)], before["public/images/og/other.jpg".replace("/", os.sep)])
        after["public/images/og/other.jpg".replace("/", os.sep)] = before["public/images/og/other.jpg".replace("/", os.sep)]
        self.assertEqual(after, before, "the cards before it and after it are back")

    def test_a_folder_to_keep_that_is_itself_a_link_or_lies_behind_one_is_refused(self):
        elsewhere = os.path.join(self.tmp.name, "cards-kept-elsewhere")
        os.rename(self.og(), elsewhere)
        os.symlink(elsewhere, self.og())
        with self.assertRaises(Refusal) as cm:
            self.j.snapshot_dir("public/images/og")
        self.assertEqual(cm.exception.code, "site-path")
        self.assertIn("public/images/og is a link", str(cm.exception))
        os.remove(self.og())
        os.rename(elsewhere, self.og())
        images = os.path.join(self.tmp.name, "images-kept-elsewhere")
        os.rename(os.path.join(self.site, "public", "images"), images)
        os.symlink(images, os.path.join(self.site, "public", "images"))
        with self.assertRaises(Refusal) as cm:
            self.j.snapshot_dir("public/images/og")
        self.assertIn("is a link", str(cm.exception))
        self.assertEqual(sorted(os.listdir(os.path.join(images, "og"))), ["default.jpg", "other.jpg"])

    def test_a_file_where_the_folder_to_keep_would_be_is_refused(self):
        shutil.rmtree(self.og())
        with open(self.og(), "wb") as f:
            f.write(b"a file")
        with self.assertRaises(Refusal) as cm:
            self.j.snapshot_dir("public/images/og")
        self.assertIn("public/images/og is a file, not a folder", str(cm.exception))

    @unittest.skipUnless(os.name == "posix", "permissions as POSIX has them")
    def test_what_cannot_be_listed_or_read_in_a_folder_to_keep_is_refused_by_name_instead_of_being_left_out(self):
        # left out of what is kept, it would be deleted when the folder is put back
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root may read anything, so nothing can be closed to it")
        os.makedirs(self.og("drafts"))
        with open(self.og("drafts", "note.txt"), "wb") as f:
            f.write(b"a note")
        for rel, mode, said in (("drafts", 0o000, "public/images/og/drafts cannot be listed (Permission denied)"),
                                ("drafts", 0o300, "public/images/og/drafts cannot be listed (Permission denied)"),
                                ("drafts", 0o600, "public/images/og/drafts/note.txt cannot be read (Permission denied)"),
                                ("other.jpg", 0o000, "public/images/og/other.jpg cannot be read (Permission denied)"),
                                ("drafts/note.txt", 0o200, "public/images/og/drafts/note.txt cannot be read (Permission denied)")):
            with self.subTest(rel=rel, mode=oct(mode)):
                was = os.stat(self.og(*rel.split("/"))).st_mode & 0o777
                os.chmod(self.og(*rel.split("/")), mode)
                try:
                    with self.assertRaises(Refusal) as cm:
                        _site.Journal(self.site).snapshot_dir("public/images/og")
                finally:
                    os.chmod(self.og(*rel.split("/")), was)
                self.assertEqual(cm.exception.code, "site-path")
                self.assertIn(said, str(cm.exception))
        _site.Journal(self.site).snapshot_dir("public/images/og")   # and once it is open again, it is kept

    @unittest.skipUnless(os.name == "posix" and hasattr(os, "mkfifo"), "a pipe in the file system, as POSIX has them")
    def test_something_in_a_folder_to_keep_that_is_neither_a_file_nor_a_folder_is_refused_by_name(self):
        os.mkfifo(self.og("pipe"))
        with self.assertRaises(Refusal) as cm:
            self.j.snapshot_dir("public/images/og")
        self.assertIn("public/images/og/pipe is neither a file nor a folder", str(cm.exception))

    @unittest.skipUnless(os.name == "posix", "folder permissions as POSIX has them")
    def test_a_kept_folder_that_was_made_read_only_afterwards_is_still_put_back_and_the_folder_above_it_is_not_needed(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root may write anywhere, so a folder cannot be closed to it")
        self.j.snapshot_dir("public/images/og")
        with open(self.og("default.jpg"), "wb") as f:
            f.write(b"regenerated")
        with open(self.og("extra.jpg"), "wb") as f:
            f.write(b"extra")
        images = os.path.join(self.site, "public", "images")
        for closed in (self.og(), images):
            os.chmod(closed, 0o555)
            self.addCleanup(os.chmod, closed, 0o755)
        self.assertEqual(self.j.rollback(), [])
        os.chmod(images, 0o755)
        self.assertEqual(tree(self.site), self.before)
        self.assertEqual(os.stat(self.og()).st_mode & 0o777, 0o755, "the folder has the mode it had when it was kept")

    # --- what the run makes is noted before it is made --------------------------------------------

    def test_a_run_stopped_between_making_a_folder_and_anything_else_still_takes_the_folder_away(self):
        real = os.mkdir

        def stopped_just_after(path, *args, **kwargs):
            real(path, *args, **kwargs)
            raise KeyboardInterrupt()
        os.mkdir = stopped_just_after
        try:
            with self.assertRaises(KeyboardInterrupt):
                self.j.write("brand-handoff/deep/pack.zip", b"zip")
        finally:
            os.mkdir = real
        self.assertTrue(os.path.isdir(os.path.join(self.site, "brand-handoff")))
        self.assertEqual(self.j.rollback(), [])
        self.assertEqual(tree(self.site), self.before)

    def test_a_write_stopped_at_any_step_leaves_no_temporary_file_once_it_is_rolled_back(self):
        for step in ("fdopen", "chmod", "replace"):
            with self.subTest(step=step):
                real = getattr(os, step)

                def stopped(*args, **kwargs):
                    raise KeyboardInterrupt()
                setattr(os, step, stopped)
                try:
                    with self.assertRaises(KeyboardInterrupt):
                        self.j.write("public/favicon.svg", b"<svg>new</svg>")
                finally:
                    setattr(os, step, real)
                self.assertEqual(self.j.rollback(), [])
                self.assertEqual(tree(self.site), self.before)

    # --- a file that is there is never taken for one that is not ---------------------------------

    @unittest.skipUnless(os.name == "posix", "file permissions as POSIX has them")
    def test_a_file_that_is_there_and_cannot_be_read_is_an_error_not_a_missing_file(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root may read anything, so nothing can be closed to it")
        path = os.path.join(self.site, "public", "favicon.svg")
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, 0o644)
        with self.assertRaises(PermissionError):
            self.j.read("public/favicon.svg")
        with self.assertRaises(PermissionError):
            self.j.write("public/favicon.svg", b"<svg>new</svg>")
        self.assertIsNone(self.j.read("public/not-there.svg"))
        self.assertIsNone(self.j.read("package.json/not-there.svg"), "below something that is a file, nothing is there")
        os.chmod(os.path.join(self.site, "public"), 0)
        self.addCleanup(os.chmod, os.path.join(self.site, "public"), 0o755)
        with self.assertRaises(PermissionError):
            _site.missing_files(self.site)

    def test_a_file_the_tests_deleted_comes_back_with_the_mode_it_had(self):
        path = os.path.join(self.site, "public", "favicon.svg")
        os.chmod(path, 0o600)
        self.j.write("public/favicon.svg", b"<svg>new</svg>")
        os.remove(path)
        self.assertEqual(self.j.rollback(), [])
        self.assertEqual(tree(self.site), self.before)
        if os.name == "posix":
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_a_planned_path_that_is_a_link_or_lies_behind_one_is_refused_by_the_check_whatever_the_link_points_at(self):
        outside = os.path.join(self.tmp.name, "outside")
        os.makedirs(os.path.join(outside, "folder"))
        with open(os.path.join(outside, "file.png"), "wb") as f:
            f.write(b"elsewhere")
        public = os.path.join(self.site, "public")
        os.symlink(os.path.join(outside, "file.png"), os.path.join(public, "to-a-file.png"))
        os.symlink(os.path.join(outside, "folder"), os.path.join(public, "to-a-folder.png"))
        os.symlink(os.path.join(outside, "nothing-here"), os.path.join(public, "dangling.png"))
        os.symlink(os.path.join(outside, "folder"), os.path.join(self.site, "linked"))
        for rel in ("public/to-a-file.png", "public/to-a-folder.png", "public/dangling.png", "linked/a.png", "linked/deeper/a.png"):
            for name in ("check", "read"):
                with self.subTest(rel=rel, call=name):
                    with self.assertRaises(Refusal) as cm:
                        getattr(self.j, name)(rel)
                    self.assertEqual(cm.exception.code, "site-path")
                    self.assertIn("%s is a link" % rel, str(cm.exception))
        self.assertEqual(os.listdir(os.path.join(outside, "folder")), [])

    def read_only(self, rel):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root may write anywhere, so a folder cannot be closed to it")
        path = os.path.join(self.site, *rel.split("/"))
        os.chmod(path, 0o555)
        self.addCleanup(os.chmod, path, 0o755)

    @unittest.skipUnless(os.name == "posix", "folder permissions as POSIX has them")
    def test_a_write_that_fails_leaves_nothing_of_its_own_to_undo_and_the_earlier_writes_are_put_back(self):
        self.j.write(".gitignore", b"changed\n")
        self.read_only("public")
        with self.assertRaises(PermissionError):
            self.j.write("public/favicon.svg", b"<svg>new</svg>")   # the original was noted, the file never changed
        self.assertEqual(self.j.written, [".gitignore"])
        self.assertEqual(self.j.rollback(), [], "the file that was never changed is not reported as not put back")
        self.assertEqual(tree(self.site), self.before)

    @unittest.skipUnless(os.name == "posix", "folder permissions as POSIX has them")
    def test_rollback_tries_every_file_and_names_the_ones_it_could_not_put_back(self):
        self.j.write("package.json", b'{"changed": true}')
        self.j.write("public/favicon.svg", b"<svg>new</svg>")
        self.j.write("public/favicon.ico", b"ico")
        self.j.write(".gitignore", b"changed\n")
        self.read_only("public")
        left = self.j.rollback()
        self.assertEqual(sorted(rel for rel, _why in left), ["public/favicon.ico", "public/favicon.svg"])
        for _rel, why in left:
            self.assertIn("ermission", why)
        after = tree(self.site)
        for rel in ("package.json", ".gitignore"):
            self.assertEqual(after[rel], self.before[rel], "%s is back although files before and after it could not be put back" % rel)

    def test_a_file_whose_folder_is_gone_is_named_as_not_put_back_and_the_others_are_put_back(self):
        self.j.write("public/favicon.svg", b"<svg>new</svg>")
        self.j.write(".gitignore", b"changed\n")
        os.rename(os.path.join(self.site, "public"), os.path.join(self.site, "public.moved"))
        self.assertEqual(self.j.rollback(), [("public/favicon.svg", "its folder is no longer there")])
        self.assertEqual(tree(self.site)[".gitignore"], self.before[".gitignore"])

    def test_a_file_the_run_made_in_a_folder_that_is_gone_again_needs_no_putting_back(self):
        self.j.write("brand-handoff/pack.zip", b"zip")
        os.remove(os.path.join(self.site, "brand-handoff", "pack.zip"))
        os.rmdir(os.path.join(self.site, "brand-handoff"))
        self.assertEqual(self.j.rollback(), [])
        self.assertEqual(tree(self.site), self.before)

    def test_rolling_back_twice_is_the_same_as_once(self):
        self.j.snapshot_dir("public/images/og")
        self.j.write("public/favicon.svg", b"<svg>new</svg>")
        self.j.write("brand-handoff/pack.zip", b"zip")
        self.assertEqual(self.j.rollback(), [])
        self.assertEqual(self.j.rollback(), [])
        self.assertEqual(tree(self.site), self.before)

    def test_the_snapshotted_folder_comes_back_with_its_empty_folders_and_its_modes(self):
        og = os.path.join(self.site, "public", "images", "og")
        os.makedirs(os.path.join(og, "drafts", "empty"))
        with open(os.path.join(og, "drafts", "note.txt"), "wb") as f:
            f.write(b"a note")
        os.chmod(os.path.join(og, "default.jpg"), 0o600)
        os.chmod(os.path.join(og, "drafts"), 0o750)
        before = tree(self.site)
        self.j.snapshot_dir("public/images/og")
        import shutil
        shutil.rmtree(og)                                  # what a generator may do: start from an empty folder
        os.makedirs(og)
        with open(os.path.join(og, "default.jpg"), "wb") as f:
            f.write(b"regenerated")
        self.j.restore_dir("public/images/og")
        self.assertEqual(tree(self.site), before, "the empty folder is back too")
        if os.name == "posix":
            self.assertEqual(os.stat(os.path.join(og, "default.jpg")).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(os.path.join(og, "drafts")).st_mode & 0o777, 0o750)
            self.assertEqual(os.stat(os.path.join(og, "other.jpg")).st_mode & 0o777, 0o644)
        self.j.restore_dir("public/images/og")             # and a second time, as rollback does after a failed generator
        self.assertEqual(tree(self.site), before)

    @unittest.skipUnless(os.name == "posix", "folder permissions as POSIX has them")
    def test_a_folder_that_was_read_only_comes_back_read_only_and_can_be_restored_again(self):
        og = os.path.join(self.site, "public", "images", "og")
        os.makedirs(os.path.join(og, "locked"))
        with open(os.path.join(og, "locked", "a.jpg"), "wb") as f:
            f.write(b"a")
        os.chmod(os.path.join(og, "locked"), 0o555)
        self.addCleanup(lambda: os.path.isdir(os.path.join(og, "locked")) and os.chmod(os.path.join(og, "locked"), 0o755))
        before = tree(self.site)
        self.j.snapshot_dir("public/images/og")
        self.j.restore_dir("public/images/og")
        self.j.restore_dir("public/images/og")
        self.assertEqual(tree(self.site), before)
        self.assertEqual(os.stat(os.path.join(og, "locked")).st_mode & 0o777, 0o555)

    def test_a_link_in_a_folder_to_snapshot_is_refused_because_restoring_would_make_it_a_file(self):
        outside = os.path.join(self.tmp.name, "elsewhere.jpg")
        with open(outside, "wb") as f:
            f.write(b"elsewhere")
        os.symlink(outside, os.path.join(self.site, "public", "images", "og", "linked.jpg"))
        with self.assertRaises(Refusal) as cm:
            self.j.snapshot_dir("public/images/og")
        self.assertEqual(cm.exception.code, "site-path")
        self.assertIn("linked.jpg", str(cm.exception))
        os.remove(os.path.join(self.site, "public", "images", "og", "linked.jpg"))
        os.symlink(self.tmp.name, os.path.join(self.site, "public", "images", "og", "linked-folder"))
        with self.assertRaises(Refusal) as cm:
            self.j.snapshot_dir("public/images/og")
        self.assertIn("linked-folder", str(cm.exception))

    def test_what_can_be_known_before_a_write_is_checked_without_writing(self):
        os.symlink(self.tmp.name, os.path.join(self.site, "linked"))
        with open(os.path.join(self.site, "brand-handoff"), "wb") as f:
            f.write(b"a file where a folder is needed")
        before = tree(self.site)
        for rel, mention in (("linked/a.png", "link"), ("../escape.png", "not inside"), ("brand-handoff/logo.zip", "brand-handoff is not a folder"),
                             ("brand-handoff/deep/logo.zip", "brand-handoff is not a folder"), ("public/images", "is a folder")):
            with self.subTest(rel=rel):
                with self.assertRaises(Refusal) as cm:
                    self.j.check(rel)
                self.assertEqual(cm.exception.code, "site-path")
                self.assertIn(mention, str(cm.exception))
        for rel in ("public/favicon.svg", "public/new.png", "new-folder/deeper/file.txt", ".gitignore"):
            self.j.check(rel)
        self.assertEqual(tree(self.site), before, "a check makes no folder and writes no file")
        self.assertEqual(self.j.written, [])

    @unittest.skipUnless(os.name == "posix", "folder permissions as POSIX has them")
    def test_a_folder_this_account_may_not_write_in_is_found_by_the_check(self):
        self.read_only("public")
        for rel in ("public/favicon.svg", "public/new.png", "public/new-folder/file.png"):
            with self.subTest(rel=rel):
                with self.assertRaises(Refusal) as cm:
                    self.j.check(rel)
                self.assertEqual(cm.exception.code, "site-path")
                self.assertIn("not allowed to write in public", str(cm.exception))
        self.j.check("public/images/logo.png")   # the folder below it is open

    def test_a_path_that_leaves_the_site_or_goes_through_a_link_is_refused(self):
        outside = os.path.join(self.tmp.name, "outside")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(self.site, "linked"))
        os.symlink(os.path.join(outside, "x"), os.path.join(self.site, "public", "link.png"))
        for rel in ("../escape.png", "/etc/x", "linked/a.png", "public/link.png", "public/../../escape.png", ""):
            with self.subTest(rel=rel):
                with self.assertRaises(Refusal) as cm:
                    self.j.write(rel, b"x")
                self.assertEqual(cm.exception.code, "site-path")
        self.assertEqual(os.listdir(outside), [])
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "escape.png")))

    # --- the folders above a kept folder that were not there go last, when nothing of the run is left in them ---

    def test_a_file_the_run_wrote_beside_a_kept_folder_that_was_not_there_does_not_keep_the_folder_above_from_going(self):
        # a logo run on a site without public/images: the run writes public/images/logo.png, the generator makes
        # public/images/og. Taking the folder away before the logo is out of it fails, and was counted as not put back.
        for made_by in ("the journal", "the generator"):
            with self.subTest(made_by=made_by):
                shutil.rmtree(os.path.join(self.site, "public", "images"), ignore_errors=True)
                before = tree(self.site)
                j = _site.Journal(self.site)
                j.snapshot_dir("public/images/og")
                if made_by == "the generator":
                    os.makedirs(self.og())                      # before the run writes there: the folder is then not one the journal made
                j.write("public/images/logo.png", b"png")
                j.write("public/favicon.ico", b"ico")
                os.makedirs(self.og("sub"), exist_ok=True)
                with open(self.og("default.jpg"), "wb") as f:
                    f.write(b"card")
                self.assertEqual(j.rollback(), [], "nothing is named as not put back")
                self.assertEqual(tree(self.site), before)
                self.assertEqual(j.rollback(), [])

    def test_putting_only_the_kept_folder_back_leaves_the_runs_own_file_beside_it_and_names_nothing(self):
        # the generator failed and the install stands: the cards' folder goes again, the logo beside it stays
        shutil.rmtree(os.path.join(self.site, "public", "images"))
        before = tree(self.site)
        self.j.snapshot_dir("public/images/og")
        self.j.write("public/images/logo.png", b"png")
        os.makedirs(self.og())
        with open(self.og("half.jpg"), "wb") as f:
            f.write(b"half a card")
        self.assertEqual(self.j.restore_dir("public/images/og"), [])
        self.assertEqual(sorted(os.listdir(os.path.join(self.site, "public", "images"))), ["logo.png"])
        self.assertEqual(self.j.rollback(), [])
        self.assertEqual(tree(self.site), before)

    def test_a_folder_above_a_kept_folder_goes_again_at_once_when_nothing_is_in_it(self):
        shutil.rmtree(os.path.join(self.site, "public", "images"))
        before = tree(self.site)
        self.j.snapshot_dir("public/images/og")
        os.makedirs(self.og())
        self.assertEqual(self.j.restore_dir("public/images/og"), [])
        self.assertEqual(tree(self.site), before, "a run about colours whose generator failed leaves no empty public/images")

    def test_something_foreign_in_a_folder_that_was_not_there_is_named_at_the_end_and_not_deleted(self):
        shutil.rmtree(os.path.join(self.site, "public", "images"))
        self.j.snapshot_dir("public/images/og")
        self.j.write("public/images/logo.png", b"png")
        with open(os.path.join(self.site, "public", "images", "hers.txt"), "wb") as f:
            f.write(b"put there meanwhile")
        left = self.j.rollback()
        self.assertEqual([rel for rel, _why in left], ["public/images"])
        self.assertEqual(os.listdir(os.path.join(self.site, "public", "images")), ["hers.txt"])

    # --- what stands at a path is looked at before it is touched, and only a plain file is ever opened ---

    def within(self, seconds, call, unblock):
        """The result of `call`, which must come within `seconds`; when it does not (it waits on a pipe),
        `unblock` lets it go so that the test can end, and the test fails."""
        import threading
        got = []

        def run():
            try:
                got.append((call(), None))
            except Exception as e:   # carried over to the test's own thread
                got.append((None, e))
        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(seconds)
        if t.is_alive():
            import time
            end = time.time() + 30
            while t.is_alive() and time.time() < end:   # every pipe it comes to, until it has got through
                for path in unblock:
                    try:
                        os.close(os.open(path, os.O_WRONLY | os.O_NONBLOCK))
                    except OSError:
                        pass
                t.join(0.05)
            self.fail("it waited on a pipe instead of looking at what stands there first")
        if got[0][1] is not None:
            raise got[0][1]
        return got[0][0]

    @unittest.skipUnless(os.name == "posix" and hasattr(os, "mkfifo"), "pipes and links in the file system, as POSIX has them")
    def test_a_pipe_a_link_or_a_dangling_link_where_a_kept_file_was_is_taken_away_and_the_file_put_back_without_being_opened(self):
        outside = os.path.join(self.tmp.name, "outside.txt")
        with open(outside, "wb") as f:
            f.write(b"not the site's")

        def pipe(path):
            os.mkfifo(path)

        for name, make in (("a pipe", pipe), ("a link to a file outside", lambda p: os.symlink(outside, p)),
                           ("a dangling link", lambda p: os.symlink(os.path.join(self.tmp.name, "nothing"), p)),
                           ("a link to a folder", lambda p: os.symlink(self.tmp.name, p))):
            with self.subTest(name=name):
                j = _site.Journal(self.site)
                j.snapshot_dir("public/images/og")              # a card that was kept
                j.write("public/favicon.svg", b"<svg>new</svg>")  # a file the run replaced
                j.write("public/favicon.ico", b"ico")           # a file the run made
                for path in (self.og("default.jpg"), os.path.join(self.site, "public", "favicon.svg"), os.path.join(self.site, "public", "favicon.ico")):
                    os.remove(path)
                    make(path)
                pipes = [self.og("default.jpg"), os.path.join(self.site, "public", "favicon.svg"), os.path.join(self.site, "public", "favicon.ico")]
                try:
                    self.assertEqual(self.within(20, j.rollback, pipes), [])
                finally:   # whatever became of it: nothing that is no file is left for the comparison below, or for the next case, to open
                    for path, data in zip(pipes, (b"jpg-old", b"<svg/>", None)):
                        if os.path.lexists(path) and not (os.path.isfile(path) and not os.path.islink(path)):
                            os.remove(path)
                            if data is not None:
                                with open(path, "wb") as f:
                                    f.write(data)
                self.assertEqual(tree(self.site), self.before)
                self.assertFalse(os.path.lexists(os.path.join(self.site, "public", "favicon.ico")), "what stood where no file was is gone, a dangling link too")
                self.assertEqual(T.read_bytes(outside), b"not the site's", "what a link pointed at is not touched")

    @unittest.skipUnless(os.name == "posix" and hasattr(os, "mkfifo"), "a pipe in the file system, as POSIX has them")
    def test_a_pipe_at_a_planned_path_is_refused_by_name_by_the_check_and_never_opened(self):
        path = os.path.join(self.site, "public", "favicon.ico")
        os.mkfifo(path)
        for call in (self.j.check, self.j.read):
            with self.subTest(call=call.__name__):
                with self.assertRaises(Refusal) as cm:
                    self.within(20, lambda: call("public/favicon.ico"), [path])
                self.assertEqual(cm.exception.code, "site-path")
                self.assertIn("public/favicon.ico is neither a file nor a folder", str(cm.exception))
        os.mkfifo(os.path.join(self.site, "brand-handoff"))
        with self.assertRaises(Refusal) as cm:
            self.j.check("brand-handoff/logo.zip")
        self.assertIn("brand-handoff/logo.zip cannot be written: brand-handoff is not a folder", str(cm.exception))
        # what the refusal says to do, done
        os.remove(path)
        os.remove(os.path.join(self.site, "brand-handoff"))
        self.j.check("public/favicon.ico")
        self.j.check("brand-handoff/logo.zip")

    def test_a_file_where_a_folder_above_the_kept_folder_would_be_is_refused_when_the_folder_is_kept(self):
        # looked at only as far as "is not there", the share cards' folder seemed to be merely missing: a dry
        # run passed, and the real run failed when the generator could not make the folder
        shutil.rmtree(os.path.join(self.site, "public", "images"))
        with open(os.path.join(self.site, "public", "images"), "wb") as f:
            f.write(b"a file")
        with self.assertRaises(Refusal) as cm:
            self.j.snapshot_dir("public/images/og")
        self.assertEqual(cm.exception.code, "site-path")
        self.assertIn("public/images/og cannot be made: public/images is a file, not a folder", str(cm.exception))
        self.assertIn("move the file away, then run this again", str(cm.exception))
        os.remove(os.path.join(self.site, "public", "images"))
        self.j.snapshot_dir("public/images/og")   # as the refusal says: moved away, it is kept as "not there"

    def test_a_folder_to_keep_that_holds_more_than_is_kept_in_memory_is_refused_by_name_before_it_is_read(self):
        real, opened = _site.MAX_KEPT, []
        with open(self.og("big.bin"), "wb") as f:
            f.write(b"x" * 5000)
        real_note = _site.Journal._note
        _site.MAX_KEPT = 4096
        _site.Journal._note = lambda journal, rel: (opened.append(rel), real_note(journal, rel))[1]
        try:
            with self.assertRaises(Refusal) as cm:
                self.j.snapshot_dir("public/images/og")
            self.assertEqual(cm.exception.code, "site-path")
            self.assertIn("public/images/og holds more than 0 MB", str(cm.exception))
            self.assertIn("the largest file it came to is public/images/og/big.bin", str(cm.exception))
            self.assertNotIn("public/images/og/big.bin", opened, "the file that takes it over the limit is not read")
            os.remove(self.og("big.bin"))                       # what the refusal says to do
            opened[:] = []
            self.j.snapshot_dir("public/images/og")
            self.assertEqual(sorted(opened), ["public/images/og/default.jpg", "public/images/og/other.jpg"])
        finally:
            _site.MAX_KEPT, _site.Journal._note = real, real_note
        self.assertGreaterEqual(_site.MAX_KEPT, 100 * 1024 * 1024, "room for a site's worth of cards")

    def test_a_write_that_fails_names_the_file_that_was_to_be_written_not_the_temporary_one_beside_it(self):
        real = os.replace

        def refusing(src, dst, *args, **kwargs):
            raise PermissionError(1, "Operation not permitted", src, None, dst)
        os.replace = refusing
        try:
            with self.assertRaises(PermissionError) as cm:
                self.j.write("public/favicon.svg", b"<svg>new</svg>")
        finally:
            os.replace = real
        self.assertEqual(cm.exception.filename, os.path.join(self.j.site, "public", "favicon.svg"))
        self.assertIsNone(cm.exception.filename2)
        self.assertNotIn(".write-", str(cm.exception))
        self.assertEqual(self.j.rollback(), [])
        self.assertEqual(tree(self.site), self.before)

    @unittest.skipUnless(sys.platform == "darwin" and shutil.which("chflags"), "the lock that macOS shows in what stat returns (chflags uchg)")
    def test_a_locked_file_or_folder_is_found_by_the_check_and_when_a_folder_is_kept_before_anything_is_written(self):
        def lock(path):
            subprocess.run(["chflags", "uchg", path], check=True)
            self.addCleanup(subprocess.run, ["chflags", "nouchg", path])

        def unlock(path):
            subprocess.run(["chflags", "nouchg", path], check=True)
        target = os.path.join(self.site, "public", "favicon.svg")
        lock(target)
        with self.assertRaises(Refusal) as cm:
            self.j.check("public/favicon.svg")
        self.assertIn("public/favicon.svg cannot be written: the file is locked against change. Unlock it", str(cm.exception))
        with self.assertRaises(OSError) as raised:              # and what the write itself says, were it tried: the planned file's name
            self.j.write("public/favicon.svg", b"<svg>new</svg>")
        self.assertEqual(raised.exception.filename, os.path.join(self.j.site, "public", "favicon.svg"))
        unlock(target)
        self.j.check("public/favicon.svg")                      # what the refusal says to do, done
        public = os.path.join(self.site, "public")
        lock(public)
        with self.assertRaises(Refusal) as cm:
            self.j.check("public/new.png")
        self.assertIn("public/new.png cannot be written: public is locked against change", str(cm.exception))
        unlock(public)
        self.j.check("public/new.png")
        for rel, said in (("public/images/og", "public/images/og is locked against change"), ("public/images/og/other.jpg", "public/images/og/other.jpg is locked against change")):
            path = os.path.join(self.site, *rel.split("/"))
            lock(path)
            with self.assertRaises(Refusal) as cm:
                _site.Journal(self.site).snapshot_dir("public/images/og")
            self.assertIn(said, str(cm.exception))
            unlock(path)
        _site.Journal(self.site).snapshot_dir("public/images/og")
        self.assertEqual(tree(self.site), self.before)

    def test_the_layout_check_names_what_a_site_lacks(self):
        self.assertEqual(sorted(_site.missing_files(self.site)),
                         sorted(["src/styles/global.css", "src/config.ts", "public/manifest.webmanifest", "scripts/generate_og_cards.py"]))
        for rel in ("src/styles/global.css", "src/config.ts", "public/manifest.webmanifest", "scripts/generate_og_cards.py"):
            os.makedirs(os.path.dirname(os.path.join(self.site, rel)), exist_ok=True)
            open(os.path.join(self.site, rel), "w").close()
        self.assertEqual(_site.missing_files(self.site), [])


class Scaffold(unittest.TestCase):
    """The scaffold's own placeholders (the Astro logo) may be replaced with a word to the owner; any other
    icon file already there is asked about. The two files are known by hash: create-astro 5.2.6,
    --template minimal, run on 2026-10-11, wrote public/favicon.svg (749 bytes) and public/favicon.ico (655
    bytes), the same bytes as examples/minimal in the Astro repository that day."""

    def test_only_those_two_paths_have_placeholders_and_the_hashes_are_sha256(self):
        self.assertEqual(set(_site.SCAFFOLD_DEFAULTS), {"public/favicon.svg", "public/favicon.ico"})
        for digests in _site.SCAFFOLD_DEFAULTS.values():
            for d in digests:
                self.assertRegex(d, r"^[0-9a-f]{64}$")

    def test_a_file_is_a_placeholder_when_its_bytes_hash_to_the_known_value_at_its_own_path(self):
        data = b"stand-in bytes for the logo file"
        digest = hashlib.sha256(data).hexdigest()
        old = _site.SCAFFOLD_DEFAULTS
        try:
            _site.SCAFFOLD_DEFAULTS = {"public/favicon.svg": {digest}}
            self.assertTrue(_site.is_scaffold_default("public/favicon.svg", data))
            self.assertFalse(_site.is_scaffold_default("public/favicon.svg", data + b" "), "one byte more is no placeholder")
            self.assertFalse(_site.is_scaffold_default("public/favicon.ico", data), "and the path counts")
            self.assertFalse(_site.is_scaffold_default("public/apple-touch-icon.png", data))
        finally:
            _site.SCAFFOLD_DEFAULTS = old

    @unittest.skipUnless(os.environ.get("BRAND_KIT_SCAFFOLD_PUBLIC"), "set BRAND_KIT_SCAFFOLD_PUBLIC to the public/ folder of a fresh create-astro --template minimal project")
    def test_against_a_real_scaffold(self):
        folder = os.environ["BRAND_KIT_SCAFFOLD_PUBLIC"]
        for rel in ("public/favicon.svg", "public/favicon.ico"):
            with open(os.path.join(folder, os.path.basename(rel)), "rb") as f:
                self.assertTrue(_site.is_scaffold_default(rel, f.read()), rel)


if __name__ == "__main__":
    unittest.main()
