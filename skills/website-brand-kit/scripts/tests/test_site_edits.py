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
        self.assertEqual([(b, v) for b, v, _m in said], [("light", "--bg-soft"), ("dark", "--bg-soft"), ("dark_media", "--bg-soft")],
                         "in the :root block it wins over the dark blocks' lines too")
        for block, _variable, message in said:
            self.assertIn("--bg-soft in %s: " % _palette.BLOCK[block] + message, str(cm.exception))
        self.assertIn("this tool cannot write the colours into the `:root` block (the light theme) as it stands", str(cm.exception))
        # round 4: a palette that writes the dark theme only was let through, and wrote a value the page never shows
        dark_only = bakery()
        dark_only.light, dark_only.brand = {}, None
        with self.assertRaises(Refusal) as cm:
            _site.edit_css(text, dark_only)
        self.assertIn("It is marked !important in the :root block, and that line wins over this block's", str(cm.exception))
        self.assertNotIn("the :root block: The colour", str(cm.exception), "what is wrong with a block it does not write to is not its reason")

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
        for part in ("would not carry the palette after the colours were set", "The stylesheet has 2 blocks of the kind that holds the dark theme's colours",
                     "the intake does not write to a stylesheet that has one of them twice"):
            self.assertIn(part, str(cm.exception))
        self.assertNotIn("writes to the first", str(cm.exception))

    def test_a_primary_that_a_dark_block_only_mentions_in_a_comment_or_under_another_name_is_no_reason_to_refuse(self):
        dark = ':root[data-theme="dark"] {\n'
        for extra in ("  /* --brand: #123456; */\n", "  --my-brand: #123456;\n", "  --brand-soft: #123456;\n"):
            with self.subTest(extra=extra):
                new = _site.edit_css(self.CSS.replace(dark, dark + extra, 1), bakery())
                self.assertIn(extra, new)
                self.assertEqual(_palette.read_css(new).brand, "#b4531a")


    # --- a value that already is the colour wanted ---------------------------------------------------

    def respelt(self):
        """The starter's stylesheet with the bakery's palette in it, every value in another spelling than the palette's."""
        text = _site.edit_css(self.CSS, bakery())
        spell = [lambda h: h.upper(), lambda h: "rgb(%d, %d, %d)" % tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)), lambda h: h + "ff", lambda h: h.upper() + "FF",
                 lambda h: "rgb(%d %d %d / 100%%)" % tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))]
        n = 0
        for value in sorted(set(re.findall(r"(?<=: )#[0-9a-f]{6}(?=;)", text))):
            short = "#" + value[1::2] if value[1::2] == value[2::2] else None
            text = text.replace(": %s;" % value, ": %s;" % (short.upper() if short else spell[n % len(spell)](value)))
            n += 1
        return text

    def test_a_value_that_already_is_the_colour_wanted_is_left_as_it_stands_in_whatever_spelling(self):
        # round 4: `#FFF8EE` or `#FFF` where the palette says `#fff8ee` or `#ffffff` was rewritten, so a run that changed no colour
        # reported the stylesheet as written, with no change to show for it. The other three files left such a value alone.
        text = self.respelt()
        for spelling in ("--bg-soft: #FEF5E8;", "--surface: #FFF;", "--bg: rgb(255, 248, 238);", "--link: #a14a14ff;", "--brand: #B4531AFF;", "--ink: rgb(58 42 30 / 100%);"):
            self.assertIn(spelling, text)
        self.assertNotRegex(text, r": #[0-9a-f]{6};", "no value is left in the palette's own spelling")
        css = _palette.read_css(text)
        self.assertEqual((css.light, css.dark, css.dark_media, css.brand, css.problems), (T.BAKERY_LIGHT, T.BAKERY_DARK, T.BAKERY_DARK, "#b4531a", []))
        self.assertEqual(_site.edit_css(text, bakery()), text, "byte for byte as it was")
        # one value that is another colour is set, and nothing else moves
        p = bakery()
        p.dark["muted"] = "#c0c0d0"
        self.assertEqual(changed_lines(text, _site.edit_css(text, p)), ["-  --muted: rgb(196 174 152 / 100%);", "+  --muted: #c0c0d0;", "-    --muted: rgb(196 174 152 / 100%);", "+    --muted: #c0c0d0;"])
        # the near-misses: a see-through spelling of it, a colour one step away and a value that is no colour are written over
        for value in ("#fff8ee80", "#fff8ef", "rgba(255, 248, 238, 0.5)", "var(--page)", "fff8ee", "inherit", ""):
            with self.subTest(value=value):
                new = _site.edit_css(text.replace("--bg: rgb(255, 248, 238);", "--bg: %s;" % value, 1), bakery())
                self.assertIn("  --bg: #fff8ee;", new)

    def test_a_value_written_as_another_of_the_colours_stays_where_that_one_is_or_becomes_the_colour_wanted(self):
        # the starter's own `--link: var(--accent)`: with a palette whose Link is its Accent's colour the line already says what is wanted
        self.assertIn("  --link: var(--accent);", self.CSS)
        same = bakery()
        same.light["link"] = same.light["accent"]
        new = _site.edit_css(self.CSS, same)
        self.assertIn("  --link: var(--accent);", new)
        self.assertEqual((_palette.read_css(new).light, _site.edit_css(new, same)), (same.light, new))
        # the starter's stylesheet with the starter's own palette comes back as it is
        starter = _palette.Palette()
        css = _palette.read_css(self.CSS)
        starter.light, starter.dark, starter.brand = dict(css.light), dict(css.dark), css.brand
        self.assertEqual(_site.edit_css(self.CSS, starter), self.CSS)
        # where the two differ the line gets its own value, as before
        self.assertIn("  --link: #a14a14;", _site.edit_css(self.CSS, bakery()))
        # in a dark block: what the line shows is the accent of that block, or of the :root block where the dark one sets none
        aliased = self.CSS.replace("  --link: #9fb0ff;", "  --link: var(--accent);", 1)
        dark = bakery()
        dark.dark["link"] = dark.dark["accent"]
        new = _site.edit_css(aliased, dark)
        self.assertIn('  --accent: #e2874a;          /* lighter on dark \u2014 keeps links \u2265 AA on --bg */\n  --link: var(--accent);', new)
        self.assertEqual(_palette.read_css(new).dark, dark.dark)
        only_link = _palette.Palette()
        only_link.dark = {"link": "#8aa0ff"}  # the accent the dark block has now, which this palette does not set
        self.assertEqual(_site.edit_css(aliased, only_link).count("--link: var(--accent);"), 2, "it points at a line that already holds that colour")
        only_link.dark = {"link": "#2b50e0"}  # the :root block's accent, which is not what the dark block's line shows
        self.assertIn('  --link: #2b50e0;\n  --heading: #e7e9fb;', _site.edit_css(aliased, only_link))
        # a line that points at a line that points on is written out: the reading follows one step, and must read the palette back
        chain = self.CSS.replace("  --accent: #2b50e0;", "  --accent: var(--brand);", 1)
        flat = bakery()
        flat.light["link"] = flat.light["accent"] = flat.brand
        new = _site.edit_css(chain, flat)
        self.assertIn("  --accent: var(--brand);", new, "one step from a colour that is being set: left")
        self.assertIn("  --link: #b4531a;", new, "two steps: written out")
        self.assertEqual((_palette.read_css(new).light, _palette.read_css(new).problems), (flat.light, []))
        gone = aliased.replace("  --accent: #8aa0ff;          /* lighter on dark \u2014 keeps links \u2265 AA on --bg */\n", "", 1)
        self.assertNotEqual(gone, aliased)
        self.assertEqual(_site.edit_css(gone, only_link).count("--link: var(--accent);"), 2, "with no accent of its own the dark block shows the :root block's")

    def test_an_install_on_a_site_that_already_holds_the_palette_in_another_spelling_writes_no_stylesheet_and_names_no_change(self):
        # the same through the door the assistant uses, as a dry run and as a real one: first a run that brings the site's other
        # files to the palette, then the stylesheet in other spellings, then the runs that must find nothing to do in it
        def install(*extra):
            r = subprocess.run([sys.executable, os.path.join(T.SCRIPTS, "brand_intake.py"), "install", "--site", site, "--with-colours", "--test-command", "true", "--json"] + list(extra),
                               capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8"))
            self.assertEqual(r.stderr, "")
            return json.loads(r.stdout)

        with tempfile.TemporaryDirectory() as tmp:
            site = T.make_starter_site(os.path.join(tmp, "site"), with_modules=False)
            sheet = os.path.join(site, "src", "styles", "global.css")
            rows = lambda theme: "".join("| %s | `%s` |\n" % (_palette.LABEL[k], theme[k]) for k in _palette.KEYS)  # noqa: E731
            with open(os.path.join(site, "BRAND.md"), "w", encoding="utf-8") as f:
                f.write("## Colour palette\n\n### Brand\n| Token | Hex |\n|---|---|\n| Primary | `#b4531a` |\n\n### Light theme\n| Token | Hex |\n|---|---|\n" + rows(T.BAKERY_LIGHT)
                        + "\n### Dark theme\n| Token | Hex |\n|---|---|\n" + rows(T.BAKERY_DARK))
            first = install()
            self.assertIn("src/styles/global.css", first["written"], first)
            self.assertEqual(T.read(sheet), _site.edit_css(self.CSS, bakery()))
            with open(sheet, "w", encoding="utf-8", newline="") as f:
                f.write(self.respelt())
            before = T.read_bytes(sheet)
            for extra in (("--dry-run",), ()):
                with self.subTest(extra=extra):
                    data = install(*extra)
                    self.assertEqual(data["changes"], [], data)
                    self.assertNotIn("src/styles/global.css", data["written"], data)
                    self.assertEqual(T.read_bytes(sheet), before)

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
            ("the three blocks in another order", lambda t: t[t.index(dark):t.index("*, *::before")] + t[:t.index(dark)] + t[t.index("*, *::before"):] if dark in t else t),
            # round 4: brackets, statements and strings that change nothing about the palette
            ("a ; inside square brackets in a value", once("--radius: 12px;", "--radius: 12px;\n  --grid: [; --ink: #000000; ];")),
            ("a ; inside round brackets, in the media block's rule", once(inner + "\n", inner + "\n    --x: (; --bg: #000000; );\n")),
            ("a function whose name ends in url", once("--radius: 12px;", "--radius: 12px;\n  --x: -url((;));")),
            ("statements that start with @ before the blocks", lambda t: '@charset "utf-8";\n@layer base, theme;\n@namespace svg url(http://www.w3.org/2000/svg);\n' + t),
            ("a rule that registers a variable that is no colour", lambda t: t + "\n@property --gap {\n  syntax: '<length>';\n  inherits: true;\n  initial-value: 0px;\n}\n"),
            ("a value that points at a variable that is not the palette's", once("  --bg: #ffffff;", "  --page: #ffffff;\n  --bg: var(--page);")),
            ("the same in the dark block, with the variable set in another rule", lambda t: t.replace("  --ink: #dce0f5;", "  --ink: var(--text);", 1) + "\nhtml { --text: #ffffff; }\n"),
            # round 4: a value that already is the palette's colour, in another spelling, is left as it stands
            ("the bakery's background already there, in capitals", once("  --bg: #ffffff;", "  --bg: #FFF8EE;")),
            ("the bakery's surface already there, in three digits and with an alpha of ff", lambda t: t.replace("  --surface: #ffffff;", "  --surface: #FFF;", 1).replace("    --surface: #161836;", "    --surface: #2a1f17ff;", 1)),
            ("the bakery's dark ink already there, as rgb()", once("  --ink: #dce0f5;", "  --ink: rgb(239, 226, 210);")),
            # round 5: what is read past or written over, and a backslash where it is ordinary
            ("a byte order mark first", lambda t: "\ufeff" + t),
            ("a no-break space before a value, which makes it no colour", once("  --bg: #ffffff;", "  --bg:\u00a0#ffffff;")),
            ("a wide space after a value in the media block", once("    --muted: #a6abce;", "    --muted: #a6abce\u2003;")),
            ("strings with backslashes in them, each closed on its line", once(":root {\n", ':root {\n  --note: "a\\41 b\\\\"; --quote: \'\\\'\';\n')),
            ("a block in brackets in a value of another rule", lambda t: t + "\nbody { --json: [{}]; }\n"),
            ("two imports", lambda t: "@import 'a.css';\n@import url(b.css) screen;\n" + t),
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
            # round 4: what makes a browser show another value than the block's line says
            ("a ; after the :root block", once("}\n\n" + dark, "};\n\n" + dark)),
            ("a line of a block before the first block", lambda t: "color: red;\n" + t),
            ("a ; at the start of the media block", once(media, media + ";")),
            ("a ; after the rule in the media block", once("  }\n}\n", "  };\n}\n")),
            ("a colour under a name written with an escape", once("  --bg: #ffffff;", "  --bg: #ffffff;\n  --b\\67: #000000;")),
            ("the same on body", lambda t: t + "\nbody { --b\\67 : #000000; }\n"),
            ("a colour set in a rule whose selector is written with an escape", lambda t: t + "\n:r\\6f ot { --bg: #000000; }\n"),
            ("a rule that registers a colour", lambda t: t + "\n@property --bg {\n  syntax: '<length>';\n  inherits: true;\n  initial-value: 0px;\n}\n"),
            ("a default namespace", lambda t: "@namespace url(http://www.w3.org/2000/svg);\n" + t),
            ("a colour set twice, once marked important", once("  --ink: #16162a;", "  --ink: #16162a !important;\n  --ink: #16162a;")),
            ("a colour marked important in the dark block", once("  --heading: #e7e9fb;", "  --heading: #e7e9fb !important;")),
            # what only the edit refuses, by name: a line that is not there, and a Primary in a dark block
            ("a colour's line gone from :root", once("  --muted: #5a5a72;", "")),
            ("a colour's line gone from the media block", once("    --line: #272c4d;\n", "")),
            ("a colour under a name in capitals", once("  --bg: #ffffff;", "  --BG: #ffffff;")),
            ("a Primary in the dark block", once(dark + "\n", dark + "\n  --brand: #123456;\n")),
            ("a Primary in the media block's rule", once(inner + "\n", inner + "\n    --brand: #123456;\n")),
            # round 5: no name written with a backslash is read, no string is followed over a line end, and a block in brackets is no rule
            ("a class name with an escaped colon, brackets and quotes", lambda t: t + "\n.before\\:content-\\[\\'\\'\\]::before { content: ''; }\n"),
            ("a class name with an escaped quote, before the blocks", lambda t: '.q\\" { color: red }\n' + t),
            ("an escaped ; and } in a value", once(":root {\n", ":root {\n  --odd: a\\;b\\};\n")),
            ("url( spelt with an escape, a quote inside it", once("  --bg: #ffffff;", "  --bg: #ffffff;\n  --x: u\\72l(a'b); --bg: #ff0000; /*'*/ );")),
            ("a default namespace spelt with an escape", lambda t: "@n\\61mespace url(http://www.w3.org/2000/svg);\n" + t),
            ("a registration spelt with an escape", lambda t: t + "\n@p\\72operty --bg { syntax: '<color>'; inherits: false; initial-value: #ff0000; }\n"),
            ("a string carried over a Windows line end", once(":root {\n", ':root {\n  --note: "a\\\r\nb } --bg: #000000;";\n')),
            ("a string that a hex escape carries over a line end", once("  --bg: #ffffff;", '  --x: "a\\41\n; --bg: #111111; " ; /*"*/\n  --bg: #ffffff;')),
            ("the same in another rule, where it leaves a brace open to this reading", lambda t: t + "\nb { c: 'y\\41\n' }\n"),
            # round 6: an HTML comment mark outside a string and a comment, and a line of another rule whose value holds a block
            ("an HTML comment mark before url( in a value", once("  --bg: #ffffff;", "  --bg: #ffffff;\n  --x: <!--url(a'b); --bg: #ff0000; /*'*/ );")),
            ("an HTML comment mark before a registration, first", lambda t: '<!-- @property --bg { syntax: "<color>"; inherits: false; initial-value: #ff0000; }\n' + t),
            ("a closing HTML comment mark, last", lambda t: t + "\n-->\n"),
            ("a line of another rule whose value holds a block", lambda t: t + "\nhtml:root { --bg: #ff0000 {} }\n"),
            ("the same on :root twice, with nothing before the block", lambda t: ":root:root { --accent: {} }\n" + t),
            # what neither can take
            ("the light block inside round brackets", lambda t: "( a{} " + t[:t.index(dark)] + ") a{}\n" + t[t.index(dark):] if dark in t else t),
            ("the rule of the media block inside square brackets", lambda t: t.replace(inner, "  [ a{}\n" + inner, 1).replace("  }\n}\n", "  }\n  ] a{}\n}\n", 1) if inner in t else t),
            ("a brace too many", once("--radius: 12px;", "--radius: 12px; }")),
            ("a ( never closed in a value", once("  --bg: #ffffff;", "  --bg: rgb(1,2; --other: 3px;")),
            ("a ] too many", once("--radius: 12px;", "--radius: 12px];")),
            ("a [ closed by a )", once(inner + "\n", inner + "\n    --grid: [a);\n")),
            ("cut short", lambda t: t[:t.index("--bg-soft: #11132c;")]),
        ]

    def palettes(self):
        whole, light, dark = bakery(), bakery(), bakery()
        light.dark, dark.light, dark.brand = {}, {}, None
        some, alias = bakery(), bakery()
        some.light, some.dark, some.brand = {"bg": "#fff8ee", "ink": "#3a2a1e"}, {"muted": "#c4ae98"}, None
        alias.light["link"] = alias.light["accent"]  # the starter's `--link: var(--accent)` then already says what is wanted
        return (("the whole palette", whole), ("the light theme and the Primary only", light), ("the dark theme only", dark), ("three colours", some),
                ("the whole palette, its link the accent's colour", alias))

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
        counts = {"written": 0, "refused with the scan's problem": 0, "refused: a line is not there": 0, "refused: a Primary in a dark block": 0, "refused: the scan refuses it": 0}
        left = 0  # values that already were the colour wanted, and were left as they stood
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
                        counts["refused: the scan refuses it"] += 1
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
                        if new[a:b] != value:
                            # round 4: a value that already is the colour wanted stays as it was written; the reading below takes it for that colour
                            self.assertEqual(new[a:b], text[slice(*sheet.spans[block][var])])
                            left += 1
                    after = _palette.read_css(new)
                    got = {"light": after.light, "dark": after.dark, "dark_media": after.dark_media}
                    for block, var, value in wanted:
                        self.assertEqual(after.brand if var == "--brand" else got[block][_palette.KEY_OF_VARIABLE[var]], value)
                    self.assertEqual([(t.block, t.variable) for t in after_scan.problems], [(t.block, t.variable) for t in sheet.problems], "and the edit made no new problem")
                    self.assertEqual(_site.edit_css(new, palette), new, "written a second time, nothing changes")
                    counts["written"] += 1
        self.assertEqual(sum(counts.values()), len(sheets) * len(self.palettes()))
        for outcome, n in counts.items():
            self.assertGreater(n, 8, "no stylesheet of the set ends as %r any more: %r" % (outcome, counts))
        self.assertGreater(left, 8, "no value of the set is left as it stands any more")
        # with the whole palette, every shape of the first group is written and every shape of the second is refused
        whole = bakery()
        first_refused = [name for name, _make in shapes].index("html, on the line before :root")
        self.assertEqual((first_refused, len(shapes) - first_refused), (39, 59), "a shape was added or taken out: say on which side")
        for (name, make), expect in zip(shapes, [True] * first_refused + [False] * (len(shapes) - first_refused)):
            with self.subTest(name=name):
                try:
                    _site.edit_css(make(self.CSS), whole)
                    self.assertTrue(expect, "written, though it should be refused")
                except Refusal:
                    self.assertFalse(expect, "refused, though it should be written")


# --- what the site reads: an edited file evaluated by the program that reads it on the site ---------------
# set_lines says "this value is now that". The tests below hold it to that sentence: Node imports the edited
# src/config.ts and parses the edited manifest, Python runs the edited generator's own top, and what they
# read is compared with what the tool reported. Where no Node is there (or one that does not read TypeScript
# files: before 22.18), those tests are skipped; the Python ones always run.

EVALUATED = {"config": 0, "manifest": 0, "generator": 0}   # how many files each program really read in this run of the tests
_NODE = {}


def node_problem(typescript=False):
    """Why Node cannot read an edited file here, or None."""
    if "node" not in _NODE:
        _NODE["node"] = shutil.which("node")
        _NODE["typescript"] = bool(_NODE["node"]) and subprocess.run(
            [_NODE["node"], "-e", "process.exit(process.features && process.features.typescript ? 0 : 1)"], capture_output=True).returncode == 0
    if not _NODE["node"]:
        return "no node on this machine"
    return None if _NODE["typescript"] or not typescript else "this Node does not read TypeScript files (22.18 and newer do)"


def _files(folder, texts, name):
    paths = []
    for n, text in enumerate(texts):
        os.makedirs(os.path.join(folder, str(n)))
        paths.append(os.path.join(folder, str(n), name))
        with open(paths[-1], "w", encoding="utf-8", newline="") as f:
            f.write(text)
    return paths


def config_as_node_reads_it(texts):
    """[{"themeColor": ..., "logo": ...}] as a site's code gets them from each src/config.ts: Node imports the file."""
    program = ("const { pathToFileURL } = await import('node:url'); const out = [];\n"
               "for (const file of process.argv.slice(1)) {\n"
               "  try { const m = await import(pathToFileURL(file).href); out.push({ themeColor: m.SITE.themeColor, logo: m.COMPANY ? m.COMPANY.logo : null }); }\n"
               "  catch (e) { out.push({ error: String(e) }); }\n}\nconsole.log(JSON.stringify(out));\n")
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "package.json"), "w") as f:
            f.write('{"type": "module"}\n')
        r = subprocess.run([_NODE["node"], "--input-type=module", "-e", program] + _files(d, texts, "config.ts"), capture_output=True, text=True, encoding="utf-8", cwd=d, timeout=120)
    EVALUATED["config"] += len(texts)
    return json.loads(r.stdout)


def manifest_as_node_reads_it(texts):
    """[{"theme_color": ..., "background_color": ...}] as JSON.parse reads each manifest, or {"error": ...}."""
    program = ("const fs = require('fs'); console.log(JSON.stringify(process.argv.slice(1).map((file) => {\n"
               "  try { const m = JSON.parse(fs.readFileSync(file, 'utf8')); return { theme_color: m.theme_color, background_color: m.background_color }; }\n"
               "  catch (e) { return { error: String(e) }; } })));\n")
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run([_NODE["node"], "-e", program] + _files(d, texts, "manifest.webmanifest"), capture_output=True, text=True, encoding="utf-8", timeout=120)
    EVALUATED["manifest"] += len(texts)
    return json.loads(r.stdout)


def generator_as_python_runs_it(texts):
    """[{colour name: [r, g, b]}] as each generator has them once its own top has run (everything but main(),
    with a stand-in for Pillow, which the top only imports), or {"error": ...}."""
    program = ("import json, sys, types\n"
               "class Anything(types.ModuleType):\n    def __getattr__(self, name):\n        return self\n    def __call__(self, *a, **k):\n        return self\n"
               "for name in ('PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont', 'PIL.ImageFilter'):\n    sys.modules[name] = Anything(name)\n"
               "out = []\nfor path in sys.argv[1:]:\n    space = {'__name__': 'generate_og_cards', '__file__': path}\n    try:\n"
               "        with open(path, encoding='utf-8', newline='') as f:\n            exec(compile(f.read(), path, 'exec'), space)\n"
               "        out.append({n: (space[n] if isinstance(space.get(n), tuple) and all(type(c) is int for c in space[n]) else repr(space.get(n))) for n in %r})\n"
               "    except BaseException as e:\n        out.append({'error': repr(e)})\nprint(json.dumps(out))\n"
               % (tuple(name for name, _key in _site.OG_COLOURS),))
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run([sys.executable, "-c", program] + _files(d, texts, "generate_og_cards.py"), capture_output=True, text=True, encoding="utf-8", timeout=120)
    EVALUATED["generator"] += len(texts)
    return json.loads(r.stdout)


# --- doing what a refusal says: the line it shows, character for character, and the one thing it says to do ---

def refusal_in(report):
    """The refusal of set_lines at the start of a report: its three lines, without what the report says after it."""
    return re.match(r"(?s).*?left exactly as it is\.", report).group()


def shown_line(message):
    """The line a refusal shows: exactly its characters, from the start of its line in the message to the end."""
    return re.search(r"only where the file has this one line[^\n]*:\n(.*)\nWhat it found instead: ", message).group(1)


def advice(message):
    """What a refusal says to do: its last sentence, up to ", then run this again"."""
    return re.search(r"(?s)What it found instead: .*\. ([^.]+), then run this again: a line that already says this is left exactly as it is\.$", message).group(1)


def follow_config(text, message):
    """src/config.ts after somebody did what the refusal says, and nothing else. The line it shows is written
    exactly as shown: no blanks before it that the message does not have."""
    line, do = shown_line(message), advice(message)
    name, const = line.split(":")[0], re.search(r"between the line `export const (\w+) = \{`", message).group(1)
    lines = text.split("\n")

    def number(pattern, where=None):
        return int(re.search(pattern, do if where is None else where).group(1)) - 1

    def block():
        top = next(i for i, l in enumerate(lines) if re.match(r"export const %s\b" % const, l))
        return top, next(i for i in range(top + 1, len(lines)) if lines[i].startswith("}"))

    def own():
        top, close = block()
        return [i for i in range(top + 1, close) if re.match(r"[ \t]*%s[ \t]*:" % name, lines[i])]
    if do == "Save the file with ordinary line ends":
        return re.sub("\r(?!\n)|[\u2028\u2029]", "\n", text)
    if do.startswith("Set the value by hand: write that one line in place of the block's own `%s` line, or as the first line under the opening line (line " % name):
        top, close = block()   # the block's own: the one that stands inside nothing (these files have no brace in a text)
        depth = [sum(l.count("{") - l.count("}") for l in lines[top + 1:i]) for i in own()]
        if 0 in depth:
            lines[own()[depth.index(0)]] = line
        else:
            lines.insert(top + 1, line)
    elif do.startswith("Write that one line as the first line under the opening line (line "):
        lines.insert(number(r"\(line (\d+)\)") + 1, line)
    elif do in ("Leave one of them, written as shown, and take the other out", "Leave one of them, written as shown, and take the others out"):
        first, rest = own()[0], own()[1:]
        lines[first] = line
        for i in reversed(rest):
            del lines[i]
    elif do == "Write that one line in its place":
        lines[number(r"line (\d+) is written another way", message)] = line
    elif do.startswith("Set the value by hand: write that one line in place of line "):
        lines[number(r"in place of line (\d+)")] = line
    elif do.startswith("Move the `%s` line up to be the first line under the opening line (line " % name):
        hers = lines.pop(own()[0])   # the line as it is: the next run then edits it
        lines.insert(number(r"\(line (\d+)\)") + 1, hers)
    else:
        raise AssertionError("a refusal these tests do not know how to follow: %s" % do)
    return "\n".join(lines)


def follow_manifest(text, message):
    """The manifest after somebody did what the refusal says, the shown line written exactly as shown."""
    line, do = shown_line(message), advice(message)
    key = re.match(r'"(\w+)"', line).group(1)
    last = " (with no comma after it, as shown: it is the manifest's last entry)"   # said of the line as it is shown: nothing more to do
    assert do.endswith(last) == (not line.endswith(",")), "the line is shown without its comma exactly where the refusal says so"
    do = do[:-len(last)] if do.endswith(last) else do
    end = "\r" if "\r" in text and "\n" not in text else "\n"   # as an editor shows the file's lines: one that ends its lines with a carriage return alone, too
    lines = text.split(end)
    several = re.match(r"Write that one line in place of lines (\d+) to (\d+), which it replaces together"
                       r"(, and keep what stands before the entry on line \1 \(`.*?`\) on a line of its own above it)?(, and keep what stands after the entry on line \2 \(`.*?`\) on a line of its own below it)?$", do)
    value = re.match(r'Set the value yourself on line (\d+): put ("[^"]*"), in its quotes, where the value of "%s" stands now$' % key, do)
    if do == "Write that one line in its place":
        lines[int(re.search(r"line (\d+) is written another way", message).group(1)) - 1] = line
    elif several:
        first, final = int(several.group(1)) - 1, int(several.group(2)) - 1
        # what stands beside the entry on its first and last line is kept, each on a line of its own: found in the
        # file itself, as she would (the entry is the name, its value, and the comma after it)
        whole = end.join(lines[first:final + 1])
        name = re.search(r'"%s"\s*:\s*' % key, whole)
        stop = json.JSONDecoder().raw_decode(whole, name.end())[1]
        stop += len(re.match(r"\s*,|", whole[stop:]).group())
        before, after = whole[:name.start()].strip(), whole[stop:].strip()
        assert (bool(several.group(3)), bool(several.group(4))) == (bool(before), bool(after)), "the refusal says what is to be kept exactly where something stands beside the entry"
        lines[first:final + 1] = [before] * bool(before) + [line] + [after] * bool(after)
    elif value:
        n = int(value.group(1)) - 1
        at = re.search(r'"%s"\s*:\s*' % key, lines[n]).end()
        lines[n] = lines[n][:at] + value.group(2) + lines[n][json.JSONDecoder().raw_decode(lines[n], at)[1]:]
    elif do in ("Write that one line on a line of its own between the manifest's `{` and its `}`", "Write that one line on a line of its own right after the manifest's opening `{`"):
        return text.replace("{", "{\n%s\n" % line, 1)
    elif do == "Write that one line as the first line under the manifest's opening `{`":
        lines.insert(next(i for i, l in enumerate(lines) if l.startswith("{")) + 1, line)
    elif do == "Set the value yourself on the manifest's own line (the last line of that name at its top level)":
        lines[[i for i, l in enumerate(lines) if re.match(r' {0,2}"%s"' % key, l)][-1]] = line   # these manifests indent their top level by two blanks
    else:
        raise AssertionError("a refusal these tests do not know how to follow: %s" % do)
    return end.join(lines)


def changed_outside_the_block(config):
    """[(what it is, a src/config.ts, what Node reads as SITE.themeColor once the block's own line says
    #b4531a)]: the object is changed by a line outside its block, or the block this tool finds is not the
    one the site reads. The line rule does not look outside the block. It edits the line, and what the
    site then reads is for the read-back to say (test_install.py runs each of these through the install)."""
    real = config.replace("export const SITE = {", "const REAL = {").replace("themeColor: '#000000'", "themeColor: '#111111'") + "export { REAL as SITE };\n"
    copy = "export const SITE = {\n  themeColor: '#000000',\n};\n"
    return [
        ("an assignment after the block, through a cast", config + "(SITE as { themeColor: string }).themeColor = '#111111';\n", "#111111"),
        ("a plain assignment after the block", config + "// @ts-ignore\nSITE.themeColor = '#111111';\n", "#111111"),
        ("the value counted up", config + "// @ts-ignore\nSITE.themeColor++;\n", "NaN"),
        ("the object indexed", "const KEY = 'theme' + 'Color';\n" + config + "// @ts-ignore\nSITE[KEY] = '#111111';\n", "#111111"),
        ("Object.assign on it", "const MORE = { themeColor: '#111111' };\n" + config + "Object.assign(SITE, MORE);\n", "#111111"),
        ("Object.defineProperty on it", config + "Object.defineProperty(SITE, 'themeColor', { value: '#111111' });\n", "#111111"),
        ("Reflect.set on it", "const KEY = 'theme' + 'Color';\n" + config + "Reflect.set(SITE, KEY, '#111111');\n", "#111111"),
        ("the value taken out of it", config + "// @ts-ignore\ndelete SITE.themeColor;\n", "nothing"),
        ("the block this tool finds inside a comment over several lines, and the object exported under the name further down", "/*\n" + copy + "*/\n" + real, "#111111"),
        ("the block this tool finds as text in a template string over several lines", "const doc = `\n" + copy + "`;\n" + real, "#111111"),
    ]


def follow_generator(text, message):
    """The generator after somebody did what the refusal says: the shown line written exactly as shown, at the
    start of a line of its own beside the generator's other settings, and the name set nowhere else (where
    another line set it, the name on that line is changed to another)."""
    line, do = shown_line(message), advice(message)
    name = line.split(" = ")[0]
    found = message.split("What it found instead: ")[1]
    lines = text.split("\n")
    if do == "Write that one line there yourself, and set %s nowhere else in the file" % name:
        said = re.search(r"times \((.*?)\), and Python|line (\d+) sets it another way", found)
        for n in {int(n) - 1 for n in re.findall(r"\b\d+\b(?! times)", said.group(1) or said.group(2))}:
            lines[n] = re.sub(r"(?<![\w.])%s(?!\w)" % name, name + "_WAS", lines[n])
    elif do != "Write that one line beside the generator's other colours":
        raise AssertionError("a refusal these tests do not know how to follow: %s" % do)
    lines.insert(next(i for i, l in enumerate(lines) if l.startswith("W, H = ")), line)
    return "\n".join(lines)


class LineRule(unittest.TestCase):
    """What Config, Manifest and ShareCards share: _site.set_lines edits a value only where the text leaves
    no doubt that the site reads it from there, refuses everything else in one kind of sentence, and that
    sentence can be followed to the letter."""
    rel = code = None
    follow = None

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
        self.assertEqual(len(message.split("\n")), 3, "the line it shows stands alone on the second line, with nothing of the message before it")
        return message

    def line_asked_for(self, message):
        """The line a refusal shows: the one she is told she may write herself."""
        return shown_line(message)

    def followed(self, text, rounds=6, **want):
        """Do what each refusal says until a run goes through: (the text then, the refusals on the way). The
        same refusal never comes a second time: doing what one says leads on."""
        said = []
        for _round in range(rounds):
            try:
                self.set(text, **want)
                return text, said
            except Refusal as r:
                self.assertNotIn(str(r), said, "the same refusal a second time: doing what it said did not help")
                said.append(str(r))
                text = type(self).follow(text, str(r))
        self.fail("still refused after %d rounds: %s" % (rounds, said[-1]))

    def need_node(self, typescript=False):
        why = node_problem(typescript)
        if why:
            self.skipTest(why)


class Config(LineRule):
    rel, code = "src/config.ts", "config-layout"
    follow = staticmethod(follow_config)
    CONFIG = T.starter_file("src/config.ts")
    OWN = "  themeColor: '#000000',               // matches the brand primary + manifest\n"
    LOGO = "  logo: '/images/logo.png',            // resolved against SITE.url for schema\n"
    HERS = "  logo: '/images/hers.png',\n"                      # COMPANY.logo pointing at a file of her own: a logo run sets it
    BASE = CONFIG.replace(LOGO, HERS)
    WANT = {"themeColor": "#b4531a", "logo": "/images/logo.png"}

    def test_the_starter_has_each_of_the_two_lines_once(self):
        self.assertEqual((self.CONFIG.count(self.OWN), self.CONFIG.count(self.LOGO), self.BASE.count(self.HERS)), (1, 1, 1))

    def test_the_theme_colour_is_the_primary_and_nothing_else_moves(self):
        new, changes = self.set(self.CONFIG, themeColor="#b4531a")
        self.assertEqual(changes, [("themeColor", "#000000", "#b4531a")])
        self.assertEqual(len(changed_lines(self.CONFIG, new)), 2)
        self.assertEqual(new, self.CONFIG.replace("themeColor: '#000000'", "themeColor: '#b4531a'"), "the comment after the value is kept")

    def test_company_logo_is_set_to_the_derived_png_and_only_what_was_asked_for_is_touched(self):
        new, changes = self.set(self.BASE, logo="/images/logo.png")
        self.assertEqual((new, changes), (self.BASE.replace("'/images/hers.png'", "'/images/logo.png'"), [("logo", "/images/hers.png", "/images/logo.png")]))
        self.unchanged(self.CONFIG, logo="/images/logo.png")
        self.assertIn("logo: '/images/hers.png',", self.set(self.BASE, themeColor="#b4531a")[0], "a run about colours leaves COMPANY.logo alone")
        self.assertIn("themeColor: '#000000'", self.set(self.BASE, logo="/images/logo.png")[0], "and a run about the logo leaves the theme colour alone")
        both, changes = self.set(self.BASE, **self.WANT)
        self.assertEqual(both, self.BASE.replace("themeColor: '#000000'", "themeColor: '#b4531a'").replace("'/images/hers.png'", "'/images/logo.png'"))
        self.assertEqual([name for name, _old, _new in changes], ["themeColor", "logo"])
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

    # --- every shape the rule takes, and what the site then reads --------------------------------------

    def accepted(self):
        """[(what it is, a src/config.ts in that shape)]: each must be edited, both values, and read back by Node."""
        B, own, hers = self.BASE, self.OWN, self.HERS
        typed = B.replace("export const SITE = {", "export const SITE: Record<string, string> = {").replace("export const COMPANY = {", "export const COMPANY: Record<string, string> = {")
        return [
            ("the starter's own file", B),
            ("double quotes throughout, as a formatter writes them", B.replace("'", '"')),
            ("windows line ends", B.replace("\n", "\r\n")),
            ("no comma after the last entry of either block", B.replace(hers, "  logo: '/images/hers.png'\n").replace("character window.',\n} as const;", "character window.'\n} as const;")),
            ("`satisfies` after the closing brace", B.replace("} as const;", "} as const satisfies Record<string, string>;")),
            ("no `as const` after the closing brace", B.replace("} as const;", "};")),
            ("a type after the constant's name", typed),
            ("a comment after the opening brace", B.replace("export const SITE = {", "export const SITE = { // what the whole site reads")),
            ("tabs for indentation", re.sub(r"(?m)^  ", "\t", B)),
            ("the two lines not indented at all", B.replace("  themeColor:", "themeColor:").replace("  logo:", "logo:")),
            ("the two lines indented more than the lines around them", B.replace("  themeColor:", "        themeColor:").replace("  logo:", "      logo:")),
            ("the theme colour first under the opening line", B.replace(own, "").replace("export const SITE = {\n", "export const SITE = {\n" + own)),
            ("the logo as its block's last entry, with no comma, and a comment and a blank line under it", B.replace(hers, "  logo: '/images/hers.png' // hers\n  // (no comma: nothing comes after it)\n\n")),
            ("blanks before the colon and none after", B.replace("themeColor: '#000000'", "themeColor :'#000000'").replace("logo: '/images", "logo  :'/images")),
            ("a short colour", B.replace("'#000000'", "'#000'")),
            ("a colour with an alpha", B.replace("'#000000'", "'#000000ff'")),
            ("longer names that hold the name, above the key and below it",
             B.replace(own, "  darkthemeColor: '#111111',\n  themeColor2: '#222222',\n  $themeColor: '#333333',\n" + own + "  themeColorDark: '#444444',\n")),
            ("the name in its own line's comment, in a text above and in a comment above the block",
             "// SITE.themeColor is the brand's primary; COMPANY.logo is the mark\n" + B.replace("// matches the brand primary", "// themeColor matches the brand primary")
             .replace("  locale: 'en',\n", "  locale: 'en',\n  key: 'themeColor', // themeColor\n")),
            ("a copy of the line in a comment above it and below it", B.replace(own, "  // themeColor: '#111111',\n" + own + "  // themeColor: '#222222',\n")),
            ("entries whose names and texts begin with the name, and comments that say it",
             B.replace(hers, "  logoDark: '/images/logo-dark.png',\n  // the logo, resolved against SITE.url\n" + hers + "  logoAlt: 'the logo', // the logo again\n  // the logo\n")),
            ("the same keys in other objects above and below",
             "export const PRINT = {\n  themeColor: '#111111',\n  logo: '/print.png',\n} as const;\n" + B + "export const SCREEN = { themeColor: '#222222', logo: '/screen.png' };\n"),
            ("numbers, true, false, null and a blank line above the key", B.replace("  locale: 'en',\n", "  locale: 'en',\n  port: 8080,\n  ratio: -1.5,\n  draft: false,\n  live: true,\n  parent: null,\n\n")),
            ("dots and brackets in the texts and comments of plain lines, above and below the key",
             B.replace("  locale: 'en',\n", "  locale: 'en...', // see [1]\n").replace("  tagline: 'One-line positioning.',\n", "  tagline: 'Wait...', // see [2]\n  first: 'a[0]',\n")),
            ("an object and a function below the key", B.replace("  tagline:", "  social: {\n    mastodon: 'https://example.social/@us',\n  },\n  short: (s: string) => s.trim(),\n  tagline:")),
            # round 5: what cannot set a value is taken out of a line before it is looked at
            ("comments that open and close on one line, above the key and below it, alone and after an entry",
             B.replace("  locale: 'en',\n", "  locale: 'en', /* the language */\n  /* brand */\n").replace("  tagline:", "  /** the title * and / more */\n  tagline:")),
            ("ordinary copy in the description: dots and brackets in texts that run over two lines",
             B.replace("'Example is a short, specific description of what this site offers and who ' +", "'We bake... every day [and more], for people who ' + // see [1] ...")),
            ("texts below the key that hold what would be a mark as code, on lines that are not plain",
             B.replace("  tagline:", "  social: f('...', \"[x]\", '/* a', 'b */', 'a // b'),\n  tagline:").replace("export const SITE", "const f = (...a: string[]) => a;\nexport const SITE")),
            ("a text over two lines, in COMPANY, that says the key's name", B.replace(hers, hers + "  about:\n    'our logo, drawn by hand',\n")),
            # round 5: a line outside the block that only reads the object is no write
            ("lines outside the block that read the values, and a comment below it that names them",
             B + "export const THEME = SITE.themeColor;\nexport function at(k: 'name' | 'url') { return SITE[k]; }\nexport const SAME = SITE.themeColor === COMPANY.logo;\n"
             "export const ARROW = () => SITE.themeColor;\n// SITE.themeColor is the brand's primary; COMPANY.logo the mark\n"),
            ("above the block: comments that end on their line, a backtick in a text and one in a comment after code",
              "/* the site's settings; don't remove */\n/** @type {object} */ const tick = '`'; // a ` here\n" + B),
            ("regular expressions and template strings above the block that hold quotes and braces",
             "const APOS = /'/g;\nconst QUOTES = /['\"]/g;\nconst n = 1;\nconst T = `a${n ? '}' : \"{\"}b`;\nconst U = `a${n ? `x'` : 'y'}b`;\nconst half = 4 / 2; const q = '/';\n" + B),
            # round 6: nothing outside the block is looked at. What these hold was refused, and none of it changes what the site reads.
            ("a licence header over several lines at the top of the file", "/*\n * Copyright (c) the owner of the site.\n * Don't remove this header.\n */\n" + B),
            ("a comment over several lines above each of the two blocks",
             B.replace("export const SITE", "/**\n * What the whole site reads.\n */\nexport const SITE").replace("export const COMPANY", "/**\n * The company, for the schema.\n * @see SITE\n */\nexport const COMPANY")),
            ("a template string over several lines above the block, with a copy of the line in it", "const notes = `\n  themeColor: '#111111',\n`;\n" + B),
            ("lines outside the block that read the object beside a write to something else",
             B + "const cache: Record<string, number> = {};\nexport function reset() { delete cache[SITE.url]; delete cache[SITE.themeColor]; }\n"
             "const other = { themeColor: '' }; const s = SITE; other.themeColor = s.name;\nlet i = 0; export const v = [SITE, COMPANY][i++].themeColor;\n"
             "export const TITLE = SITE['name']; export const X: string[] = [];\n"),
            ("comments that speak of a write to the object, after code above the block and below it",
             "const x = 1; // SITE.themeColor = '#111'\n" + B + "// SITE.themeColor = '#111111';\n// delete this note once SITE has its real url\n"),
            ("an assignment below the block that sets only what is not set yet", B + "// @ts-ignore\nSITE.themeColor ||= '#111111';\n"),
        ]

    def test_every_shape_the_rule_takes_is_edited_on_its_two_lines_and_nothing_else_changes(self):
        for label, text in self.accepted():
            with self.subTest(label=label):
                self.assertNotEqual(text, self.CONFIG)
                new, changes = self.set(text, **self.WANT)
                self.assertEqual([(name, value) for name, _old, value in changes], [("themeColor", "#b4531a"), ("logo", "/images/logo.png")])
                self.assertEqual(len(changed_lines(text, new)), 4, "two lines, each once as it was and once as it is")
                self.unchanged(new, **self.WANT)
        self.assertEqual(self.set(self.CONFIG, **self.WANT)[1], [("themeColor", "#000000", "#b4531a")], "the starter as it stands: its logo line already says it")

    def test_what_the_tool_reports_for_every_shape_it_takes_is_what_node_reads_from_the_file(self):
        self.need_node(typescript=True)
        shapes = self.accepted() + [("the starter as it stands", self.CONFIG)]
        edits = [self.set(text, **self.WANT) for _label, text in shapes]
        before = config_as_node_reads_it([text for _label, text in shapes])
        after = config_as_node_reads_it([new for new, _changes in edits])
        for (label, _text), (_new, changes), was, now in zip(shapes, edits, before, after):
            with self.subTest(label=label):
                self.assertEqual(now, {"themeColor": "#b4531a", "logo": "/images/logo.png"}, "what the site reads after the edit is what the tool was asked to set")
                for name, old, _value in changes:
                    self.assertEqual(was[name], old, "and what the tool says it was is what the site read before")
                for name in set(self.WANT) - {name for name, _old, _value in changes}:
                    self.assertEqual(was[name], self.WANT[name], "a value it reports no change for was already the one wanted")

    # --- what the rule refuses, the sentence it says, and where doing what the sentence says leads -------

    def refusals(self):
        """[(what it is, a src/config.ts, what the first refusal says, whether Node reads the value wanted from the
        file once the refusals were followed)] for the theme colour. Where it does not, the line she wrote by hand
        says the value and something else in the file decides it: that is for the read-back to say (test_install.py)."""
        B, own = self.BASE, self.OWN
        first = "the first line under the opening line (line 5)"
        cannot = "With that in the block this tool cannot be sure from the text which value the site reads, so it does not edit this block. Set the value by hand: write that one line in place of line "
        up = "Move the `themeColor` line up to be " + first

        def below(more):
            return B.replace("  tagline:", more + "  tagline:")
        return [
            # (b) above the key
            ("an object inside the block whose lines are indented like the block's own", B.replace(own, "  social: {\n  themeColor: '#111111',\n  },\n"),
             "line 10, above it in the block, is not one whole entry on one line (`social: {`)", True),
            ("an object inside the block, indented as a formatter does", B.replace(own, "  print: {\n    themeColor: '#000000',\n  },\n"), "line 10, above it in the block, is not one whole entry on one line (`print: {`). Above the `themeColor` line this tool takes only blank lines, comments and "
             "entries written `name: 'text',` (or a number, true, false, null in place of the text), so that it is sure the line is the block's own. " + up, True),
            ("a value above it that runs on to the next line", B.replace("  locale: 'en',\n", "  locale:\n    'en',\n"), "line 9, above it in the block, is not one whole entry on one line (`locale:`)", True),
            ("a call above it", B.replace("  locale: 'en',\n", "  locale: String('en'),\n"), "line 9, above it in the block, is not one whole entry on one line", True),
            ("a text with a backslash above it", B.replace("name: 'Example',", "name: 'The Baker\\'s',"), "line 7, above it in the block, is not one whole entry on one line (`name: 'The Baker\\'s',`)", True),
            ("a quoted key above it", B.replace("  locale: 'en',\n", "  'og:type': 'website',\n"), "line 9, above it in the block, is not one whole entry on one line", True),
            ("two entries on one line above it", B.replace("  locale: 'en',\n", "  locale: 'en', region: 'GB',\n"), "line 9, above it in the block, is not one whole entry on one line", True),
            ("a comment above it in the block that does not end on its line", B.replace("  locale: 'en',\n", "  locale: 'en',\n  /* brand\n  colours */\n"), "line 10, in the same block, holds `/*` (`/* brand`). " + cannot + "12", True),
            ("a comment above it that ends on its line, and another that opens after it", B.replace("  locale: 'en',\n", "  locale: 'en',\n  /* a */ /* b\n  */\n"), "line 10, in the same block, holds `/*`", True),
            ("the line inside a block comment in the block, under a spread that sets it",
             "const BRAND = { themeColor: '#111111' };\n" + B.replace("export const SITE = {\n", "export const SITE = {\n  ...BRAND,\n  /*\n").replace(own, own + "  */\n"),
             "line 7, in the same block, holds `...` (`...BRAND,`). " + cannot + "13", False),
            ("a spread above it", "const BRAND = { other: 1 };\n" + B.replace("export const SITE = {\n", "export const SITE = {\n  ...BRAND,\n"), "line 7, in the same block, holds `...` (`...BRAND,`). " + cannot + "12", True),
            ("a list above it", B.replace("  locale: 'en',\n", "  tags: ['a', 'b'],\n"), "line 9, in the same block, holds `[`", True),
            ("a template string above it", B.replace("  locale: 'en',\n", "  locale: `en`,\n"), "line 9, in the same block, holds a backtick", True),
            # (c) below the key
            ("a spread below it", "const MORE = { other: 1 };\n" + below("  ...MORE,\n"), "line 14, in the same block, holds `...` (`...MORE,`). " + cannot + "11", True),
            ("a spread after another entry on a line below it", "const MORE = { other: 1 };\n" + below("  extra: 1, ...MORE,\n"), "line 14, in the same block, holds `...`", True),
            ("a computed key below it", "const KEY = 'other';\n" + below("  [KEY]: '#111111',\n"), "line 14, in the same block, holds `[`", True),
            ("a getter with a computed name below it", "const KEY = 'other';\n" + below("  get [KEY]() { return '#111111'; },\n"), "line 14, in the same block, holds `[`", True),
            ("a list below it, which this tool cannot tell from a computed key", below("  tags: ['a', 'b'],\n"), "line 13, in the same block, holds `[` (`tags: ['a', 'b'],`)", True),
            ("another name spelt with an escape below it", below("  'caf\\u00e9': 1,\n"), "line 13, in the same block, holds `\\u`", True),
            ("another name spelt with the other escape below it", below("  'caf\\xe9': 1,\n"), "line 13, in the same block, holds `\\x`", True),
            ("a comment below it that does not end on its line", below("  /* the\n  title */\n"), "line 13, in the same block, holds `/*` (`/* the`)", True),
            ("a text with a backslash below it, so that this tool cannot tell where the line's texts end", below("  motto: 'it\\'s here... [x]' +\n    'more',\n"), "line 13, in the same block, holds `...`", True),
            ("a spread behind a text on a line below it", "const MORE = { other: 1 };\n" + below("  extra: 'x', ...MORE,\n"), "line 14, in the same block, holds `...`", True),
            ("a template string below it", below("  greeting: `hello`,\n"), "line 13, in the same block, holds a backtick", True),
            ("a text below it that runs on behind a backslash", below("  motto: 'one \\\n  two',\n"), "line 13, in the same block, holds a `\\` at its end", True),
            ("a spread above it and one below it", "const A = { a: 1 };\nconst Z = { z: 1 };\n" + (below("  ...Z,\n")).replace("export const SITE = {\n", "export const SITE = {\n  ...A,\n"),
             "line 16, in the same block, holds `...` (`...Z,`). " + cannot + "13", True),
            # the name a second time
            ("the key a second time", B.replace(own, own + "  themeColor: '#111111',\n"), "2 lines of the block begin with `themeColor:` (lines 10 and 11), so it cannot be known from the text which of them the site reads. "
             "Leave one of them, written as shown, and take the other out", True),
            ("the key three times", B.replace(own, own + "  themeColor: '#111111',\n  themeColor: '#222222',\n"), "3 lines of the block begin with `themeColor:` (lines 10, 11 and 12)", True),
            ("the key a second time, quoted", below("  'themeColor': '#111111',\n"), "line 13, in the same block, holds the name `themeColor` again (`'themeColor': '#111111',`). " + cannot + "10", False),
            ("the key a second time, computed", below("  ['themeColor']: '#111111',\n"), "line 13, in the same block, holds `[`", False),
            ("the key a second time after another entry on the line", below("  extra: 1, themeColor: '#111111',\n"), "line 13, in the same block, holds the name `themeColor` again", False),
            ("the name alone below it (a shorthand entry, which wins)", "const themeColor = '#111111';\n" + below("  themeColor,\n"), "line 14, in the same block, holds the name `themeColor` again (`themeColor,`)", False),
            ("a getter of that name below it", below("  get themeColor() { return '#111111'; },\n"), "line 13, in the same block, holds the name `themeColor` again", False),
            ("the key again on a line that looks like a comment and stands in a block comment", below("  note: 1, /* was:\n  // */ themeColor: '#111111', /*\n  */\n"), "line 13, in the same block, holds `/*` (`note: 1, /* was:`)", False),
            ("the key again on a line that looks like a comment and stands in a template string", below("  note: `\n  // ${0}`, themeColor: '#111111', other: `\n  `,\n"), "line 13, in the same block, holds a backtick", False),
            # a key of the same name in an object inside the block (round 6): hers, and never to be taken out
            ("the key in an object inside the block below it, on one line", below("  print: { themeColor: '#111111' },\n"), "line 13, in the same block, holds the name `themeColor` again (`print: { themeColor: '#111111' },`). " + cannot + "10", True),
            ("the key in an object inside the block below it, on lines of its own", B.replace(own, own + "  pwa: {\n    themeColor: '#00ff00',\n  },\n"),
             "line 12, in the same block, holds the name `themeColor` again (`themeColor: '#00ff00',`). " + cannot + "10", True),
            ("the key in an object inside the block above it, on lines of its own", B.replace(own, "  pwa: {\n    themeColor: '#00ff00',\n  },\n" + own),
             "2 lines of the block begin with `themeColor:` (lines 11 and 13), each below a line that is not one whole entry on one line (line 10: `pwa: {`), so any of them may belong to something inside the block. "
             "With that in the block this tool cannot be sure from the text which value the site reads, so it does not edit this block. Set the value by hand: write that one line in place of the block's own `themeColor` line, or as the first line under the opening line (line 5) where the block has none of its own", True),
            ("the key in two objects inside the block and not in the block itself", B.replace(own, "  pwa: {\n    themeColor: '#00ff00',\n  },\n  print: {\n    themeColor: '#00ff00',\n  },\n"),
             "2 lines of the block begin with `themeColor:` (lines 11 and 14), each below a line that is not one whole entry on one line (line 10: `pwa: {`)", False),
            # the key's own line
            ("no such line", B.replace(own, ""), "no line of the block (lines 5 to 17) begins with `themeColor:`. Write that one line as " + first, True),
            ("under another name", B.replace("themeColor:", "colour:"), "no line of the block (lines 5 to 18) begins with `themeColor:`", True),
            ("the line below the block", B.replace(own, "").replace("} as const;\n", "} as const;\n// themeColor: '#000000',\n", 1), "no line of the block (lines 5 to 17) begins with `themeColor:`", True),
            ("a quoted key", B.replace(own, "  'themeColor': '#000000',\n"), "line 10 is written another way: its key is in quotes (`'themeColor': '#000000',`), and this tool takes the key as the starter writes it, "
             "without them. Write that one line in its place", True),
            ("a key in double quotes", B.replace(own, '  "themeColor": "#000000",\n'), "line 10 is written another way: its key is in quotes", True),
            ("every key of the block in quotes, as some formatters leave them", re.sub(r"(?m)^  (\w+):", r"  '\1':", B.split("} as const;")[0]) + "} as const;" + B.split("} as const;", 1)[1],
             "line 10 is written another way: its key is in quotes (`'themeColor': '#000000', // matches the brand primary + manifest`)", True),
            ("the key in quotes twice", B.replace(own, "  'themeColor': '#000000',\n  \"themeColor\": '#111111',\n"), "no line of the block (lines 5 to 19) begins with `themeColor:`", False),
            ("another entry before it on the line", B.replace(own, "  locale2: 'en', themeColor: '#000000',\n"), "no line of the block (lines 5 to 18) begins with `themeColor:`", False),
            ("a choice between two values", "const dark = false;\n" + B.replace(own, "  themeColor: dark ? '#111111' : '#000000',\n"), "line 11 is written another way: `themeColor: dark ? '#111111' : '#000000',`. Write that one line in its place", True),
            ("a value joined from two", B.replace(own, "  themeColor: '#000000' + '',\n"), "line 10 is written another way: `themeColor: '#000000' + '',`", True),
            ("a value with a type after it", B.replace(own, "  themeColor: '#000000' as string,\n"), "line 10 is written another way", True),
            ("a name in place of the value", "const BRAND = '#000000';\n" + B.replace(own, "  themeColor: BRAND,\n"), "line 11 is written another way: `themeColor: BRAND,`", True),
            ("a colour by name", B.replace(own, "  themeColor: 'black',\n"), "line 10 is written another way", True),
            ("five digits", B.replace(own, "  themeColor: '#00000',\n"), "line 10 is written another way", True),
            ("another entry after it on the line", B.replace(own, "  themeColor: '#000000', locale2: 'en',\n"), "line 10 is written another way", True),
            ("a block comment after it on the line", B.replace(own, "  themeColor: '#000000', /* brand */\n"), "line 10 is written another way", True),
            ("a template string for the value", B.replace(own, "  themeColor: `#000000`,\n"), "line 10 is written another way", True),
            ("no comma after the value, which runs on to the next line", B.replace(own, "  themeColor: '#000000'\n    + 'ff',\n"),
             "line 10 is written another way: it has no comma after the value, so the value can run on to the line below it (`themeColor: '#000000'`). Write that one line in its place", False),
            ("no comma after the value and a comment between it and what it runs on to", B.replace(own, "  themeColor: '#000000' // the primary\n  // and its alpha\n    + 'ff',\n"),
             "line 10 is written another way: it has no comma after the value", False),
            # the closing line (round 5): what stands after the brace can decide the value
            ("another object joined on to the closing line", B.replace("} as const;", "} && { themeColor: '#111111' };", 1), "line 18 closes the block with more than its `}` (`} && { themeColor: '#111111' };`): after the brace "
             "this tool takes `as const`, a `satisfies` clause, a `;` and a `//` comment, and nothing else. With that on the closing line this tool cannot be sure from the text which value the site reads, so it "
             "does not edit this block. Set the value by hand: write that one line in place of line 10", False),
            ("something the block falls back on, after the closing brace", "const base = { themeColor: '#111111' };\n" + B.replace("} as const;", "}.missing ?? base;", 1), "line 19 closes the block with more than its `}` (`}.missing ?? base;`)", False),
            ("a choice after the closing brace", B.replace("} as const;", "} ? { themeColor: '#111111' } : {};", 1), "line 18 closes the block with more than its `}`", False),
            ("a type other than `const` after the closing brace", B.replace("} as const;", "} as Record<string, string>;", 1), "line 18 closes the block with more than its `}`", True),
            # line ends
            ("a second key behind a carriage return that TypeScript reads as a line end", B.replace(own, own[:-1] + "\r  themeColor: '#111111',\n"), "line 10 holds a line end that TypeScript reads and this tool does not", True),
            ("a second key behind one of Unicode's line separators", B.replace(own, own[:-1] + "\u2028  themeColor: '#111111',\n"), "line 10 holds a line end that TypeScript reads and this tool does not", True),
        ]

    def test_what_the_rule_does_not_take_is_refused_in_the_one_sentence_naming_the_line(self):
        for label, text, saying, _reads in self.refusals():
            with self.subTest(label=label):
                message = self.refused(text, saying, themeColor="#b4531a")
                self.assertEqual(self.line_asked_for(message), "themeColor: '#b4531a',")
        for label, value in (("an escaped single quote", "'/it\\'s.png'"), ("an escaped double quote", '"/say-\\"hi\\".png"'), ("an escaped backslash", "'/a\\\\b.png'"),
                             ("a name in place of the value", "LOGO"), ("a template string", "`/images/logo.png`")):
            with self.subTest(label=label):
                message = self.refused(self.CONFIG.replace(self.LOGO, "  logo: %s,\n" % value), "is written another way: `logo: ", logo="/images/logo.png")
                self.assertEqual(self.line_asked_for(message), "logo: '/images/logo.png',")
        self.refused(self.BASE.replace("} as const;", "} as const; (SITE as any).themeColor = '#111111';", 1), "line 18 closes the block with more than its `}`", themeColor="#b4531a")
        for label, text, saying in (("the key twice in COMPANY", self.BASE.replace(self.HERS, self.HERS + "  logo: '/other.png',\n"), "2 lines of the block begin with `logo:` (lines 34 and 35)"),
                                    ("the key again in an object inside COMPANY, below it", self.BASE.replace(self.HERS, self.HERS + "  parent: { logo: '/images/parent.png' },\n"), "line 35, in the same block, holds the name `logo` again"),
                                    ("the key again, in quotes, below it", self.BASE.replace(self.HERS, self.HERS + "  'logo': '/other.png',\n"), "line 35, in the same block, holds the name `logo` again"),
                                    ("the name as a text of its own on a line that is not plain", self.BASE.replace(self.HERS, self.HERS + "  ['logo']: '/other.png',\n"), "line 35, in the same block, holds `[`"),
                                    ("not there", self.BASE.replace(self.HERS, ""), "no line of the block (lines 32 to 34) begins with `logo:`")):
            with self.subTest(label=label):
                self.refused(text, saying, logo="/images/logo.png")

    def test_doing_what_a_refusal_says_leads_to_a_run_that_goes_through_and_never_to_the_same_refusal_again(self):
        # the line is written exactly as the refusal shows it, with no blanks before it; what the site reads
        # at the end is asked of Node in the test below
        for label, text, _saying, _reads in self.refusals():
            with self.subTest(label=label):
                mended, said = self.followed(text, themeColor="#b4531a")
                self.assertTrue(said, "it was refused at first")
                self.assertLessEqual(len(said), 3)
                new, changes = self.set(mended, themeColor="#b4531a")
                self.assertEqual(len(re.findall(r"(?m)^[ \t]*themeColor[ \t]*:[ \t]*'#b4531a',", new)), 1, "one line says it, and it says the value wanted")
                if not changes:
                    self.assertIn("\nthemeColor: '#b4531a',\n", mended, "her line is as the refusal showed it, and was left as it is")
        for label, text in (("logo escaped", self.CONFIG.replace(self.LOGO, "  logo: '/it\\'s.png',\n")), ("logo twice", self.BASE.replace(self.HERS, self.HERS + "  logo: '/other.png',\n")),
                            ("logo not there", self.BASE.replace(self.HERS, "")), ("logo named again below", self.BASE.replace(self.HERS, self.HERS + "  parent: { logo: '/images/parent.png' },\n")),
                            ("a list below the logo", self.BASE.replace(self.HERS, self.HERS + "  sameAs: ['https://example.org/us'],\n"))):
            with self.subTest(label=label):
                mended, said = self.followed(text, logo="/images/logo.png")
                self.assertTrue(said)
                self.assertEqual(len(re.findall(r"(?m)^[ \t]*logo:[ \t]*'/images/logo.png',", self.set(mended, logo="/images/logo.png")[0])), 1)

    def test_after_the_refusals_were_followed_node_reads_the_value_the_tool_says_the_file_holds(self):
        self.need_node(typescript=True)
        cases = [(label, text) for label, text, _saying, reads in self.refusals() if reads]
        ends = [self.set(self.followed(text, themeColor="#b4531a")[0], themeColor="#b4531a")[0] for _label, text in cases]
        for (label, _text), got in zip(cases, config_as_node_reads_it(ends)):
            with self.subTest(label=label):
                self.assertEqual(got.get("themeColor"), "#b4531a", got)

    # what a developer may have put into the block: entries, comments and texts of every kind, each on lines of its own
    AWKWARD = ("  ...A,\n", "  [K]: '#111111',\n", "  'themeColor': '#111111',\n", '  "themeColor": "#111111",\n', "  themeColor: '#111111',\n", "  themeColor,\n", "  get themeColor() { return '#111111'; },\n",
               "  themeColor() { return 1; },\n", "  nested: { themeColor: '#111111' },\n", "  nested: {\n  themeColor: '#111111',\n  },\n", "  nested: {\n    a: 1,\n  },\n", "  // themeColor: '#111111',\n",
               "  /* x */\n", "  /** doc */\n", "  /*\n  themeColor: '#111111',\n  */\n", "  t: `x`,\n", "  t: `\n  themeColor: '#111111',\n  `,\n", "  s: 'a\\\n  themeColor: b',\n", "  'theme\\u0043olor': '#111111',\n",
               "  theme\\u0043olor: '#111111',\n", "  ['themeColor']: '#111111',\n", "  x: 1, themeColor: '#111111',\n", "  fn() { return 1; },\n", "  arr: [1, 2],\n", "  r: /'/,\n", "  r: /`/,\n", '  q: "it\'s",\n',
               "  u: undefined,\n", "  __proto__: { themeColor: '#111111' },\n", "  ok: 'plain', // themeColor\n", "  n: 1, /*\n  // */ themeColor: '#111111', /*\n  */\n",
               "  t: `\n  // ${0}`, themeColor: '#111111', u: `\n  `,\n", "  y: 'x' +\n    'themeColor',\n", "  z: 'x' +\n    'y',\n", "  w: '#111111'\n    + '',\n", "\n", "  // a comment `\n", "  'a-b': 1,\n",
               "  1: 'x',\n", "  a: 1, b: 2,\n", "  c: (1),\n", "  d: -1,\n", "  e: +1,\n", "  f: 1e3,\n", "  g: 0x1f,\n", "  h: 1n,\n")

    def test_whatever_pair_of_awkward_lines_stands_above_and_below_the_key_what_the_tool_then_edits_is_what_node_reads(self):
        # the sentence "what the tool reports is what the site reads", asked of every pair: one thing above the
        # key's line and one below it (or nothing). Most are refused; of each one that is edited and is a file
        # Node can run, Node must read the old value the tool reported before, and the new value after.
        self.need_node(typescript=True)
        head = "const A = { themeColor: '#111111' };\nconst K = 'themeColor';\nconst themeColor = '#111111';\n"
        taken = []
        for above in ("",) + self.AWKWARD:
            for below in ("",) + self.AWKWARD:
                text = head + self.CONFIG.replace(self.OWN, above + self.OWN + below)
                try:
                    taken.append((above, below, text) + self.set(text, themeColor="#b4531a"))
                except Refusal:
                    pass
        self.assertEqual(len(taken), len({text for _a, _b, text, _new, _changes in taken}))
        before = config_as_node_reads_it([text for _a, _b, text, _new, _changes in taken])
        after = config_as_node_reads_it([new for _a, _b, _text, new, _changes in taken])
        ran = 0
        for (above, below, _text, _new, changes), was, now in zip(taken, before, after):
            if "error" in was or "error" in now:
                continue   # not a file that runs (the same key twice under `as const`, say): nothing is promised of those
            ran += 1
            with self.subTest(above=above, below=below):
                self.assertEqual(changes, [("themeColor", was["themeColor"], "#b4531a")], "what it says the value was is what Node read before")
                self.assertEqual(now["themeColor"], "#b4531a", "and what it says it set is what Node reads now")
        self.assertGreater(ran, 150, "of %d pairs" % (len(self.AWKWARD) + 1) ** 2)
        self.assertLess(len(taken), (len(self.AWKWARD) + 1) ** 2 // 4, "most of them are refused")

    def test_a_block_this_tool_cannot_edit_is_said_to_be_that_and_a_value_set_by_hand_in_it_is_taken_as_it_stands(self):
        # a spread above the key and one below it: the line can move neither up nor down. The refusal says so
        # in plain words, once, and the value she then writes by hand is accepted: (b) and (c) are not asked
        # of a line that needs no edit, the name a second time among them. Nothing outside the block is looked at.
        text = "const A = { a: 1 };\nconst Z = { z: 1 };\n" + self.BASE.replace("export const SITE = {\n", "export const SITE = {\n  ...A,\n").replace("  tagline:", "  ...Z,\n  tagline:")
        message = self.refused(text, "this tool cannot be sure from the text which value the site reads, so it does not edit this block. Set the value by hand: write that one line in place of line 13", themeColor="#b4531a")
        self.assertNotIn("Move the", message, "moving the line would only lead to the other refusal")
        by_hand = follow_config(text, message)
        self.assertIn("\nthemeColor: '#b4531a',\n", by_hand)
        self.unchanged(by_hand, themeColor="#b4531a")
        # Taken as it stands: whether the site reads it from there is for the read-back to say (test_install.py), and
        # the caller is told the line each value stands on, set or left, so that the read-back can name it.
        where = {}
        self.assertEqual(_site.set_lines(self.rel, by_hand, {"themeColor": "#b4531a", "logo": "/images/hers.png"}, where), (by_hand, []))
        self.assertEqual(where, {"themeColor": 13, "logo": 38}, "the lines of two values that were left as they are")
        where = {}
        self.assertEqual(len(_site.set_lines(self.rel, self.BASE, self.WANT, where)[1]), 2)
        self.assertEqual(where, {"themeColor": 10, "logo": 34}, "and of two that were set")
        nested = self.BASE.replace(self.OWN, "  social: {\n  themeColor: '#b4531a',\n  },\n")
        self.unchanged(nested, themeColor="#b4531a")
        closing = self.BASE.replace("} as const;", "} && { themeColor: '#111111' };", 1)
        self.unchanged(follow_config(closing, self.refused(closing, "closes the block with more than its `}`", themeColor="#b4531a")), themeColor="#b4531a")
        self.unchanged(by_hand.replace("themeColor: '#b4531a',", "  themeColor: \"#B4531A\",  // by hand"), themeColor="#b4531a")
        self.refused(by_hand, "holds `...`", themeColor="#000000")   # another value wanted is an edit again, and is refused again
        self.unchanged(by_hand.replace("  ...Z,\n", "  ...Z,\n  'themeColor': '#111111',\n"), themeColor="#b4531a")   # which of the two the site reads, the read-back says
        self.unchanged(by_hand + "Object.assign(SITE, Z);\n", themeColor="#b4531a")
        self.refused(by_hand.replace("themeColor: '#b4531a',", "themeColor: '#b4531a', other: 1,"), "is written another way", themeColor="#b4531a")
        if not node_problem(typescript=True):
            self.assertEqual(config_as_node_reads_it([by_hand])[0]["themeColor"], "#b4531a")
            # the stated limit: where the spread below it sets the key, the site reads that, and the tool has said it cannot know
            limit = by_hand.replace("const Z = { z: 1 };", "const Z = { themeColor: '#111111' };")
            self.unchanged(limit, themeColor="#b4531a")
            self.assertEqual(config_as_node_reads_it([limit])[0]["themeColor"], "#111111")

    def test_what_a_line_outside_the_block_does_to_the_object_is_not_looked_for_the_line_is_edited_and_only_the_site_can_say_what_it_reads(self):
        # Round 5 refused these from the text, and with them working code (a licence header, a line that only reads
        # the value). The rule now stops at the block: the line is edited, and the read-back asks the site.
        cases = changed_outside_the_block(self.CONFIG)
        edits = [self.set(text, themeColor="#b4531a") for _label, text, _reads in cases]
        for (label, text, _reads), (new, changes) in zip(cases, edits):
            with self.subTest(label=label):
                self.assertEqual(changes, [("themeColor", "#000000", "#b4531a")])
                self.assertEqual(len(changed_lines(text, new)), 2, "one line, once as it was and once as it is")
        if not node_problem(typescript=True):
            for (label, _text, reads), got in zip(cases, config_as_node_reads_it([new for new, _changes in edits])):
                with self.subTest(label=label):
                    self.assertEqual(got.get("themeColor"), {"NaN": None, "nothing": None}.get(reads, reads), "(Node's answer as JSON has neither NaN nor a value that is not there)")
                    self.assertNotEqual(got.get("themeColor"), "#b4531a", "the site does not read what the block's line says, and only asking it shows that")

    def test_a_block_that_cannot_be_found_once_or_is_opened_or_closed_another_way_is_refused_and_can_be_mended_as_the_refusal_says(self):
        B = self.BASE
        cases = (
            ("declared with let", B.replace("export const SITE = {", "export let SITE = {"), "no line that starts `export const SITE`. Write `export const SITE = {` at the start of a line",
             lambda t: t.replace("export let SITE", "export const SITE")),
            ("exported further down", B.replace("export const SITE = {", "const SITE = {") + "export { SITE };\n", "no line that starts `export const SITE`",
             lambda t: t.replace("const SITE = {", "export const SITE = {").replace("export { SITE };\n", "")),
            ("two blanks in the declaration", B.replace("export const SITE = {", "export const  SITE = {"), "no line that starts `export const SITE`", lambda t: t.replace("const  SITE", "const SITE")),
            ("the block twice, one of them in a comment", "/*\nexport const SITE = {\n  url: 'old',\n};\n*/\n" + B, "2 lines (lines 2 and 10), not one, that start `export const SITE`. Leave one `export const SITE` in the file",
             lambda t: t.split("*/\n", 1)[1]),
            ("no closing brace at the start of a line", B.split("} as const;")[0].rstrip("\n") + " };\n", "no line after line 5 that starts with `}`. Close the block with a `}` at the start of a line",
             lambda t: t.replace(" };\n", "\n};\n")),
            ("a wrapper on the opening line", B.replace("export const SITE = {", "export const SITE = Object.freeze({").replace("} as const;", "} as const);", 1),
             "line 5 opens the block another way: `export const SITE = Object.freeze({`. Write the opening line as `export const SITE = {`",
             lambda t: t.replace("export const SITE = Object.freeze({", "export const SITE = {").replace("} as const);", "} as const;")),
            ("another wrapper", "const define = <T>(x: T) => x;\n" + B.replace("export const SITE = {", "export const SITE = define({").replace("} as const;", "});", 1), "line 6 opens the block another way",
             lambda t: t.replace("export const SITE = define({", "export const SITE = {").replace("});", "};", 1)),
            ("the first entry on the opening line", B.replace("export const SITE = {\n  url:", "export const SITE = { url:"), "line 5 opens the block another way", lambda t: t.replace("export const SITE = { url:", "export const SITE = {\n  url:")),
            ("a block comment after the opening brace", B.replace("export const SITE = {", "export const SITE = { /* site */"), "line 5 opens the block another way", lambda t: t.replace(" /* site */", "")),
            ("a type with braces after the name", B.replace("export const SITE = {", "export const SITE: { [key: string]: string } = {"), "line 5 opens the block another way",
             lambda t: t.replace("export const SITE: { [key: string]: string } = {", "export const SITE: Record<string, string> = {")),
        )
        mended = []
        for label, text, saying, mend in cases:
            with self.subTest(label=label):
                self.refused(text, saying, themeColor="#b4531a")
                mended.append(self.set(mend(text), themeColor="#b4531a"))
                self.assertEqual(mended[-1][1], [("themeColor", "#000000", "#b4531a")])
        # a longer name that starts the same is another constant
        other = "export const SITE_URL = 'https://example.com';\nexport const SITE$ = {\n};\n" + B
        self.assertEqual(self.set(other, themeColor="#b4531a")[1], [("themeColor", "#000000", "#b4531a")])
        if not node_problem(typescript=True):
            for got in config_as_node_reads_it([new for new, _changes in mended]):
                self.assertEqual(got.get("themeColor"), "#b4531a", got)

    def test_a_byte_order_mark_at_the_start_of_the_file_is_read_past_and_kept(self):
        # an editor may save the file with one: it cannot be seen, so no refusal could say how to take it out
        marked = "\ufeff" + self.BASE.split("// Central site configuration.")[1]   # the mark right before `export const SITE` too
        for label, text in (("before a comment", "\ufeff" + self.BASE), ("right before the block", "\ufeff" + self.BASE[self.BASE.index("export const SITE"):]),
                            ("with windows line ends", "\ufeff" + self.BASE.replace("\n", "\r\n"))):
            with self.subTest(label=label):
                new, changes = self.set(text, **self.WANT)
                self.assertEqual((new, [name for name, _old, _value in changes]), (text.replace("'#000000'", "'#b4531a'").replace("'/images/hers.png'", "'/images/logo.png'"), ["themeColor", "logo"]))
                self.assertTrue(new.startswith("\ufeffexport const SITE" if "right before" in label else "\ufeff//"))
                self.unchanged(new, **self.WANT)
        self.assertTrue(marked.startswith("\ufeff"))
        self.refused("// a mark that is not at the start of the file is no mark\n\ufeff" + self.BASE[self.BASE.index("export const SITE"):], "no line that starts `export const SITE`", themeColor="#b4531a")

    def test_a_name_twice_on_one_line_is_said_as_that_and_not_as_two_lines(self):
        self.assertEqual([_site._at(n) for n in ([3], [3, 8], [3, 8, 11], [2, 2], [2, 2, 2], [9, 73, 73], [1, 1, 5])],
                         ["line 4", "lines 4 and 9", "lines 4, 9 and 12", "twice on line 3", "3 times on line 3", "lines 10 and 74 (twice)", "lines 2 (twice) and 6"])


class Manifest(LineRule):
    rel, code = "public/manifest.webmanifest", "manifest-layout"
    follow = staticmethod(follow_manifest)
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

    def not_json(self):
        return [("a comma too many", self.MANIFEST.replace('"standalone",', '"standalone",,')),
                ("a comma before the closing brace", self.MANIFEST.replace('  ]\n}', '  ],\n}')),
                ("a comment", "// the manifest\n" + self.MANIFEST), ("empty", ""), ("cut short", self.MANIFEST[:200]),
                ("nested deeper than can be read", "[" * 100000),
                # what Python's reader takes and the site's JSON.parse does not
                ("NaN", self.MANIFEST.replace('"lang": "en",', '"lang": "en", "ratio": NaN,')),
                ("Infinity", self.MANIFEST.replace('"lang": "en",', '"lang": "en", "big": Infinity,')),
                ("-Infinity", self.MANIFEST.replace('"lang": "en",', '"lang": "en", "small": -Infinity,')),
                ("NaN inside an entry", self.MANIFEST.replace('"purpose": "maskable"', '"purpose": "maskable", "weight": NaN')),
                ("a byte order mark that is not at the start of the file", "\n\ufeff" + self.MANIFEST)]

    def test_a_manifest_that_is_not_valid_json_is_refused_as_that_before_anything_is_edited(self):
        # also when both colours stand in it as lines that could be edited: what a browser makes of it is not known
        for name, text in self.not_json():
            with self.subTest(name=name):
                with self.assertRaises(Refusal) as cm:
                    self.set(text, **self.BOTH)
                self.assertEqual(cm.exception.code, "manifest-layout")
                self.assertIn("public/manifest.webmanifest is not valid JSON (", str(cm.exception))
                self.assertIn("so this tool does not edit it. Mend the file so that it is valid JSON", str(cm.exception))
                self.assertNotIn("after the colours were set", str(cm.exception))
                with self.assertRaises(Refusal, msg="and also when it already holds both colours: it is not a manifest the site can read"):
                    self.set(text.replace("#000000", "#b4531a").replace("#ffffff", "#fff8ee"), **self.BOTH)
        with self.assertRaises(Refusal) as cm:
            self.set(self.MANIFEST.replace('"lang": "en",', '"ratio": NaN,'), **self.BOTH)
        self.assertIn("is not valid JSON (it holds NaN, which JSON does not have)", str(cm.exception))
        with self.assertRaises(Refusal) as cm:
            self.set('[{"background_color": "#ffffff", "theme_color": "#000000"}]', **self.BOTH)
        self.assertIn("does not hold one object in braces at its top level", str(cm.exception))

    def test_what_this_tool_refuses_as_not_json_the_sites_own_reader_refuses_too_and_what_it_takes_that_reader_takes(self):
        self.need_node()
        refused = [(name, text) for name, text in self.not_json() if name != "nested deeper than can be read"]
        for (name, _text), got in zip(refused, manifest_as_node_reads_it([text for _name, text in refused])):
            with self.subTest(name=name):
                self.assertIn("error", got, "JSON.parse reads what this tool refused as not valid JSON")

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
        one_line = self.MANIFEST.replace('  "theme_color": "#000000",', '  "theme_color": "#111111", "theme_color": "#000000",')
        for name, text, key, lines in (("another entry's colour before the manifest's own", self.nested(), "theme_color", "2 times in the file (lines 6 and 10)"),
                                       ("another entry's colour after the manifest's own", after_own, "theme_color", "2 times in the file (lines 9 and 10)"),
                                       ("only the background still to set", self.nested(theme_color="#b4531a"), "background_color", "2 times in the file (lines 6 and 9)"),
                                       ("only the theme colour still to set", self.nested(background_color="#fff8ee"), "theme_color", "2 times in the file (lines 6 and 10)"),
                                       ("the manifest's own key twice", twice, "theme_color", "2 times in the file (lines 6 and 10)"),
                                       ("the manifest's own key twice on one line", one_line, "theme_color", "2 times in the file (twice on line 9)")):
            with self.subTest(name=name):
                message = self.refused(text, 'the name "%s" stands %s' % (key, lines), **self.BOTH)
                self.assertIn("Set the value yourself on the manifest's own line (the last line of that name at its top level), then run this again", message)

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

    def refusals(self):
        """[(what it is, a manifest, what the first refusal says)]: each can be followed to a run that goes through."""
        hidden = self.MANIFEST.replace('"theme_color": "#000000"', '"theme\\u005fcolor": "#000000"').replace('  "lang": "en",', '  "lang": "en",\n  "related": { "theme_color": "#111111" },')
        self.assertEqual(json.loads(hidden)["theme_color"], "#000000")
        only_inside = self.MANIFEST.replace('  "theme_color": "#000000",\n', "").replace('  "lang": "en",', '  "lang": "en",\n  "related": { "theme_color": "#111111" },')
        self.hidden = hidden
        return [("a number", self.MANIFEST.replace('"theme_color": "#000000"', '"theme_color": 0'), 'line 9 is written another way: `"theme_color": 0,`. Write that one line in its place'),
                ("nothing", self.MANIFEST.replace('"theme_color": "#000000"', '"theme_color": null'), 'line 9 is written another way: `"theme_color": null'),
                ("a list", self.MANIFEST.replace('"theme_color": "#000000"', '"theme_color": ["#000000"]'), 'line 9 is written another way: `"theme_color": ["#0'),
                ("not there", self.MANIFEST.replace('  "theme_color": "#000000",\n', ""), 'the name "theme_color" is not in the file. Write that one line as the first line under the manifest\'s opening `{`'),
                ("in another entry too", self.nested(), 'the name "theme_color" stands 2 times in the file (lines 6 and 10)'),
                ("the manifest's own key twice", self.MANIFEST.replace('  "lang": "en",', '  "lang": "en",\n  "theme_color": "#111111",'), 'the name "theme_color" stands 2 times in the file (lines 6 and 10)'),
                ("the name only inside another entry", only_inside, 'the one place where "theme_color" stands (line 6) is not the manifest\'s own entry: it belongs to something inside the manifest. '
                 "Write that one line as the first line under the manifest's opening `{`")]

    def test_a_value_that_is_no_text_or_a_name_that_is_not_the_manifests_own_entry_is_refused(self):
        for name, text, saying in self.refusals():
            with self.subTest(name=name):
                self.refused(text, saying, **self.BOTH)
        split = self.MANIFEST.replace('"theme_color": "#000000"', '"theme_color":\n    "#000000"')
        self.refused(split, 'line 9 is written another way: `"theme_color":`', **self.BOTH)
        # the manifest's own key spelt with an escape, and the plain name once, inside another entry: the refusal
        # says which entry to write the line in place of, and with that done the run goes through
        message = self.refused(self.hidden, 'the one place where "theme_color" stands (line 6) is not the manifest\'s own entry: it belongs to something inside the manifest, and the '
                               "manifest's own entry spells its name another way (with a `\\u` escape). Write that one line in place of the manifest's own entry", **self.BOTH)
        mended = self.hidden.replace('  "theme\\u005fcolor": "#000000",', self.line_asked_for(message))
        self.assertNotEqual(mended, self.hidden)
        self.assertEqual(self.set(mended, **self.BOTH)[1], [("background_color", "#ffffff", "#fff8ee")])

    def where_a_comma_would_break_it(self):
        """[(what it is, a manifest, what the first refusal says, the line it shows)]: shapes in which the line a
        refusal shows, written where the refusal says, makes a manifest that is not valid JSON unless the refusal
        gets the comma and the lines right."""
        M = self.MANIFEST
        no_own = M.replace('  "theme_color": "#000000",\n', "")
        last = " (with no comma after it, as shown: it is the manifest's last entry)"
        bare, comma = '"theme_color": "#b4531a"', '"theme_color": "#b4531a",'
        return [
            ("its own entry is the manifest's last, and holds a number", no_own.replace('  ]\n}', '  ],\n  "theme_color": 0\n}'), 'line 14 is written another way: `"theme_color": 0`. Write that one line in its place' + last, bare),
            ("an empty manifest on one line", "{}", 'the name "theme_color" is not in the file. Write that one line on a line of its own between the manifest\'s `{` and its `}`' + last, bare),
            ("an empty manifest on two lines", "{\n}\n", "Write that one line on a line of its own between the manifest's `{` and its `}`" + last, bare),
            ("the name on one line and a value that is no text on the next", M.replace('"theme_color": "#000000"', '"theme_color":\n    0'),
             'line 9 is written another way: `"theme_color":`, and its value runs on to line 10. Write that one line in place of lines 9 to 10, which it replaces together', comma),
            ("the name on one line and its text on the next", M.replace('"theme_color": "#000000"', '"theme_color":\n    "#000000"'), "Write that one line in place of lines 9 to 10, which it replaces together", comma),
            ("a value that runs over four lines", M.replace('"theme_color": "#000000"', '"theme_color": [\n    0,\n    0\n  ]'), "and its value runs on to line 12. Write that one line in place of lines 9 to 12, which it replaces together", comma),
            ("a value over two lines that is the manifest's last entry", no_own.replace('  ]\n}', '  ],\n  "theme_color":\n    0\n}'), "Write that one line in place of lines 14 to 15, which it replaces together" + last, bare),
            ("a comma on a line of its own after the value", M.replace('"theme_color": "#000000",', '"theme_color": 0\n  ,'), "Write that one line in place of lines 9 to 10, which it replaces together", comma),
            ("a manifest on one line, the value a number", '{"name":"X","background_color":"#ffffff","theme_color":0}',
             'line 1 is written another way: `{"name":"X","background_color":"#ffffff","theme_color":0}`, with something else before or after the entry on its line. '
             'Set the value yourself on line 1: put "#b4531a", in its quotes, where the value of "theme_color" stands now', comma),
            ("another entry after it on its line", M.replace('"theme_color": "#000000",', '"theme_color": 0, "x": 1,'), 'Set the value yourself on line 9: put "#b4531a", in its quotes, where the value of "theme_color" stands now', comma),
            ("a manifest on one line without the name", '{"name":"X"}', 'the name "theme_color" is not in the file. Write that one line on a line of its own right after the manifest\'s opening `{`', comma),
            ("the first entry on the line of the opening brace", "{ " + no_own[1:].lstrip("\n"), "Write that one line on a line of its own right after the manifest's opening `{`", comma),
            ("the name only as a text", no_own.replace('"short_name": "[SHORT NAME]"', '"short_name": "theme_color"'),
             'the name "theme_color" stands in the file (line 3) only as a text, not as the name of an entry. Write that one line as the first line under the manifest\'s opening `{`', comma),
            ("the name twice, inside two other entries, and no entry of the manifest's own",
             no_own.replace('  "lang": "en",', '  "lang": "en",\n  "related": { "theme_color": "#111111" },\n  "other": { "theme_color": "#222222" },'),
             'the name "theme_color" stands 2 times in the file (lines 6 and 7), and none of them is an entry of the manifest\'s own. Write that one line as the first line under the manifest\'s opening `{`', comma),
            ("its own entry twice, the second one the manifest's last", no_own.replace('  "lang": "en",', '  "lang": "en",\n  "theme_color": "#111111",').replace('  ]\n}', '  ],\n  "theme_color": "#000000"\n}'),
             "Set the value yourself on the manifest's own line (the last line of that name at its top level)" + last, bare),
            ("its own entry the last, its name spelt with an escape, and the plain name inside another entry",
             no_own.replace('  "lang": "en",', '  "lang": "en",\n  "related": { "theme_color": "#111111" },').replace('  ]\n}', '  ],\n  "theme\\u005fcolor": "#000000"\n}'),
             "Write that one line in place of the manifest's own entry" + last, bare),
            # round 6: an entry over several lines that shares its first or its last line with something else, which is kept
            ("the name on one line, its value over the next three, and another entry after it on the last", M.replace('"theme_color": "#000000",', '"theme_color":\n    [\n      0\n    ], "x": 1,'),
             'line 9 is written another way: `"theme_color":`, and its value runs on to line 12. Write that one line in place of lines 9 to 12, which it replaces together, '
             'and keep what stands after the entry on line 12 (`"x": 1,`) on a line of its own below it', comma),
            ("another entry before the name on its line, and the value on the next", M.replace('  "theme_color": "#000000",', '  "y": 2, "theme_color":\n    0,'),
             'Write that one line in place of lines 9 to 10, which it replaces together, and keep what stands before the entry on line 9 (`"y": 2,`) on a line of its own above it', comma),
            ("an entry before it on its first line and the manifest's closing brace after it on its last", no_own.replace('  ]\n}', '  ], "theme_color":\n    0 }'),
             "Write that one line in place of lines 13 to 14, which it replaces together, and keep what stands before the entry on line 13 (`],`) on a line of its own above it, "
             "and keep what stands after the entry on line 14 (`}`) on a line of its own below it" + last, bare),
            # lines counted as an editor counts them, whatever ends them
            ("a manifest whose lines end with a carriage return alone, the value a number", M.replace('"theme_color": "#000000"', '"theme_color": 0').replace("\n", "\r"),
             'line 9 is written another way: `"theme_color": 0,`. Write that one line in its place', comma),
            ("a manifest whose lines end with a carriage return alone, the value on the line after the name", M.replace('"theme_color": "#000000"', '"theme_color":\n    0').replace("\n", "\r"),
             'line 9 is written another way: `"theme_color":`, and its value runs on to line 10. Write that one line in place of lines 9 to 10, which it replaces together', comma),
            ("windows line ends, the value over three lines and another entry after it", M.replace('"theme_color": "#000000",', '"theme_color": [\n    0\n  ], "x": 1,').replace("\n", "\r\n"),
             "Write that one line in place of lines 9 to 11, which it replaces together, and keep what stands after the entry on line 11", comma),
        ]

    def test_a_byte_order_mark_at_the_start_of_the_manifest_is_read_past_and_kept_as_in_the_other_two_files(self):
        # it cannot be seen, so "is not valid JSON" could not say what to mend (a browser reads past it too)
        marked = "\ufeff" + self.MANIFEST
        new, changes = self.set(marked, **self.BOTH)
        self.assertEqual((new, changes), ("\ufeff" + self.set(self.MANIFEST, **self.BOTH)[0], [("theme_color", "#000000", "#b4531a"), ("background_color", "#ffffff", "#fff8ee")]))
        self.unchanged(new, **self.BOTH)
        number = marked.replace('"theme_color": "#000000"', '"theme_color": 0')
        message = self.refused(number, 'line 9 is written another way: `"theme_color": 0,`. Write that one line in its place', **self.BOTH)
        mended = follow_manifest(number, message)
        self.assertEqual(self.set(mended, **self.BOTH), (mended.replace("#ffffff", "#fff8ee"), [("background_color", "#ffffff", "#fff8ee")]))
        self.assertTrue(mended.startswith("\ufeff{") and mended.count("\ufeff") == 1)

    def test_the_line_a_refusal_shows_written_where_it_says_never_makes_a_manifest_that_is_not_valid_json(self):
        # the invariant: what a refusal says to do, done to the character, leads on. A comma after the manifest's
        # last entry, or a line written in place of half an entry, made a manifest the next run refused as not JSON.
        ends = []
        for label, text, saying, shown in self.where_a_comma_would_break_it():
            with self.subTest(label=label):
                message = self.refused(text, saying, **self.BOTH)
                self.assertEqual(self.line_asked_for(message), shown)
                if label.endswith("an escape, and the plain name inside another entry"):
                    mended = text.replace('  "theme\\u005fcolor": "#000000"', shown)   # "in place of the manifest's own entry"
                    self.assertNotEqual(mended, text)
                else:
                    mended = follow_manifest(text, message)
                json.loads(mended)   # valid JSON right after the first refusal was followed, whatever the next run says
                mended, said = self.followed(mended, **self.BOTH)
                for later in said:
                    self.assertNotIn("is not valid JSON", later)
                new, changes = self.set(mended, **self.BOTH)
                self.assertNotIn("theme_color", [key for key, _old, _value in changes], "the line she wrote already says it")
                self.assertEqual({key: json.loads(new)[key] for key in self.BOTH}, self.BOTH)
                ends.append(new)
        if not node_problem():
            for got in manifest_as_node_reads_it(ends):
                self.assertEqual(got, self.BOTH, "and the site's own JSON.parse reads both colours from each of them")
        # the comma stays where the line is not the last entry: the starter's shape, a number in place of the text
        message = self.refused(self.MANIFEST.replace('"theme_color": "#000000"', '"theme_color": 0'), 'line 9 is written another way: `"theme_color": 0,`. Write that one line in its place, then', **self.BOTH)
        self.assertEqual(self.line_asked_for(message), '"theme_color": "#b4531a",')

    def accepted(self):
        """[(what it is, a manifest)]: each is edited, both colours, and read back by JSON.parse."""
        return [("the starter's own file", self.MANIFEST), ("windows line ends", self.MANIFEST.replace("\n", "\r\n")), ("tabs", self.MANIFEST.replace("  ", "\t")),
                ("on one line", '{"name":"X","background_color":"#ffffff","theme_color":"#000000"}'),
                ("the name inside a text", self.MANIFEST.replace('"lang": "en",', '"description": "set \\"theme_color\\": here",')),
                ("a number too large to hold, which is JSON all the same", self.MANIFEST.replace('"lang": "en",', '"big": 1e999, "small": -1e999,')),
                ("the colour as the last entry, with no comma after it", self.MANIFEST.replace('  "theme_color": "#000000",\n', "").replace('  ]\n}', '  ],\n  "theme_color": "#000000"\n}')),
                ("the colours in capitals and short", self.MANIFEST.replace('"#000000"', '"#000"').replace('"#ffffff"', '"#FFFFFF"')),
                ("a value with an escaped quote", self.MANIFEST.replace('"theme_color": "#000000"', '"theme_color": "bl\\"ack"')),
                ("colours of other names and in other entries that are not these", self.MANIFEST.replace('"lang": "en",', '"x_theme_color": "#111111", "related": { "colour": "#222222" },'))]

    def test_every_shape_the_rule_takes_is_set_where_the_name_stands_once(self):
        one = '{"name":"X","background_color":"#ffffff","theme_color":"#000000"}'
        self.assertEqual(self.set(one, **self.BOTH)[0], '{"name":"X","background_color":"#fff8ee","theme_color":"#b4531a"}')
        said = self.MANIFEST.replace('"lang": "en",', '"description": "set \\"theme_color\\": here",')
        self.assertEqual(json.loads(self.set(said, **self.BOTH)[0])["description"], 'set "theme_color": here')
        for label, text in self.accepted():
            with self.subTest(label=label):
                new, changes = self.set(text, **self.BOTH)
                self.assertEqual([(key, value) for key, _old, value in changes], [("theme_color", "#b4531a"), ("background_color", "#fff8ee")])
                self.unchanged(new, **self.BOTH)

    def test_what_the_tool_reports_for_every_shape_it_takes_is_what_json_parse_reads_from_the_file(self):
        self.need_node()
        shapes = self.accepted()
        edits = [self.set(text, **self.BOTH) for _label, text in shapes]
        before = manifest_as_node_reads_it([text for _label, text in shapes])
        after = manifest_as_node_reads_it([new for new, _changes in edits])
        for (label, _text), (_new, changes), was, now in zip(shapes, edits, before, after):
            with self.subTest(label=label):
                self.assertEqual(now, self.BOTH, "what the site reads after the edit is what the tool was asked to set")
                for key, old, _value in changes:
                    self.assertEqual(was[key], old, "and what the tool says it was is what the site read before")

    def test_doing_what_a_refusal_says_makes_the_next_run_go_through_and_leaves_the_file_as_she_wrote_it(self):
        ends = []
        for label, text, _saying in self.refusals():
            with self.subTest(label=label):
                mended, said = self.followed(text, **self.BOTH)
                self.assertTrue(said, "it was refused at first")
                new, changes = self.set(mended, **self.BOTH)
                ends.append(new)
                data = json.loads(new)
                self.assertEqual((data["theme_color"], data["background_color"]), ("#b4531a", "#fff8ee"))
                self.assertNotIn("theme_color", [key for key, _old, _value in changes], "her line already says it")
                self.assertIn('\n"theme_color": "#b4531a",\n', mended, "written exactly as the refusal showed it, and left so")
                self.unchanged(new, **self.BOTH)
        if not node_problem():
            for got in manifest_as_node_reads_it(ends):
                self.assertEqual(got, self.BOTH)
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
    follow = staticmethod(follow_generator)
    OG = T.starter_file("scripts/generate_og_cards.py")
    NAMES = ("BG_TOP", "BG_BOT", "TITLE_COL", "SUB_COL", "ACCENT", "FOOTER_COL")
    WANT = {"BG_TOP": "#2a1f17", "BG_BOT": "#1a120d", "TITLE_COL": "#fbeedd", "SUB_COL": "#e2874a", "ACCENT": "#e2874a", "FOOTER_COL": "#c4ae98"}
    RGB = {name: [int(h[i:i + 2], 16) for i in (1, 3, 5)] for name, h in WANT.items()}
    HOME = "# Home + fallback card"

    def want(self, palette):
        return {name: palette.dark[key] for name, key in _site.OG_COLOURS}

    def further_down(self, more):
        """The starter's generator with `more` on lines of its own below the colours."""
        self.assertEqual(self.OG.count(self.HOME), 1)
        return self.OG.replace(self.HOME, more + "\n\n" + self.HOME, 1)

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
                           ("twice", self.further_down('LOGO = ROOT / "public/mine.png"')),
                           ("not there", self.OG.replace("LOGO = None", "EMBLEM = None")),
                           ("something that is no path", self.OG.replace("LOGO = None", "LOGO = pick_one()"))):
            with self.subTest(name=name):
                new, _changes = self.set(text, **self.WANT)
                self.assertEqual([l for l in new.splitlines() if "LOGO" in l or "EMBLEM" in l], [l for l in text.splitlines() if "LOGO" in l or "EMBLEM" in l])
                self.assertEqual(len(changed_lines(text, new)), 12)
        self.assertFalse([name for name in dir(_site) if "logo" in name.lower() and name != "LOGO_ADDRESS" or "emblem" in name.lower()], "nothing in the module reads or writes it")

    # --- every shape the rule takes, and what Python then has under each name -------------------------

    def accepted(self):
        """[(what it is, a generator)]: each has its six colours set, and Python, running its top, has them."""
        return [
            ("the starter's own file", self.OG),
            ("windows line ends", self.OG.replace("\n", "\r\n")),
            ("no comment after the numbers, and the numbers spaced otherwise", re.sub(r"(?m)^(BG_TOP|ACCENT) = \((\d+), (\d+), (\d+)\).*$", r"\1 = ( \2,\3 ,  \4 )", self.OG)),
            ("numbers that are no colour", self.OG.replace("BG_TOP = (30, 33, 64)", "BG_TOP = (300, 33, 64)")),
            ("the name set in a comment and in a text that runs over lines, which set nothing",
             self.further_down('# BG_TOP = (1, 2, 3)\nNOTE = """\nBG_TOP = (1, 2, 3)\nBG_BOT += (4,)\n"""')),
            ("lines that only read a colour, or set a longer name, an entry or a keyword of that name",
             self.further_down("# BG_TOP is the top of the gradient\nimport types\ncard = types.SimpleNamespace()\nprint(BG_TOP == BG_BOT, TITLE_COL, file=sys.stderr)\nspare = dict(top=BG_TOP, BG_TOP=(9, 9, 9))\n"
                               "MY_BG_TOP = (9, 9, 9)\nBG_TOP2 = (8, 8, 8)\ncard.BG_TOP = (7, 7, 7)\nspare['BG_TOP'] = (6, 6, 6)\nif BG_TOP != BG_BOT:\n    lighter = [c + 1 for c in BG_TOP]")),
            ("a colour set above the others and one below them", re.sub(r"(?m)^(ACCENT = .*)\n", "", self.OG).replace("W, H = 1200, 630", "ACCENT = (138, 160, 255)\nW, H = 1200, 630")),
        ]

    def test_every_shape_the_rule_takes_gets_its_six_colours_on_six_lines(self):
        for label, text in self.accepted():
            with self.subTest(label=label):
                new, changes = self.set(text, **self.WANT)
                self.assertEqual([name for name, _old, _value in changes], list(self.NAMES))
                self.assertEqual(len(changed_lines(text, new)), 12)
                self.unchanged(new, **self.WANT)
        odd = self.OG.replace("BG_TOP = (30, 33, 64)", "BG_TOP = (300, 33, 64)").replace("BG_BOT = (10, 11, 30)", "BG_BOT = ( 10,11 , 999 )")
        new, changes = self.set(odd, **self.WANT)
        self.assertEqual(changes[:2], [("BG_TOP", "(300, 33, 64)", "#2a1f17"), ("BG_BOT", "(10, 11, 999)", "#1a120d")], "numbers that are no colour are shown as they stood")
        self.assertIn("\nBG_TOP = (42, 31, 23) ", new)
        self.assertIn("\nBG_BOT = (26, 18, 13) ", new)

    def test_what_the_tool_reports_for_every_shape_it_takes_is_what_python_has_when_the_generators_top_has_run(self):
        shapes = self.accepted()
        edits = [self.set(text, **self.WANT) for _label, text in shapes]
        before = generator_as_python_runs_it([text for _label, text in shapes])
        after = generator_as_python_runs_it([new for new, _changes in edits])
        for (label, _text), (_new, changes), was, now in zip(shapes, edits, before, after):
            with self.subTest(label=label):
                self.assertEqual(now, self.RGB, "what the generator draws with after the edit is what the tool was asked to set")
                for name, old, _value in changes:
                    self.assertIn(old, ("#%02x%02x%02x" % tuple(c % 256 for c in was[name]), "(%d, %d, %d)" % tuple(was[name])), "and what the tool says it was is what the generator had before")

    def test_a_colour_that_already_stands_there_is_not_edited_however_its_numbers_are_spaced(self):
        done = self.set(self.OG, **self.WANT)[0].replace("BG_TOP = (42, 31, 23)", "BG_TOP = ( 42,31 ,  23 )")
        self.assertIn("BG_TOP = ( 42,31 ,  23 )", done)
        self.unchanged(done, **self.WANT)

    # --- what the rule refuses: every way Python binds a name, counted by Python's own parser -----------

    def refusals(self):
        """[(what it is, a generator, the name it is about, what the refusal says)]: each is valid Python, and
        each can be followed to a run that goes through."""
        own = "BG_TOP = (30, 33, 64)"
        down = self.further_down
        twice = "BG_TOP is set or bound 2 times (lines 52 and %d), and Python uses the last one it runs. Write that one line there yourself, and set BG_TOP nowhere else in the file"
        cases = [
            ("set again further down", down("BG_TOP = (200, 200, 200)   # my override"), twice % 59),
            ("set again right below", self.OG.replace(own, own + "\nBG_TOP = (10, 10, 10)", 1), "BG_TOP is set or bound 2 times (lines 52 and 53)"),
            ("set again, indented, under a condition", down("if True:\n    BG_TOP = (1, 2, 3)"), twice % 60),
            ("set again after another statement on the line", down("x = 1; BG_TOP = (1, 2, 3)"), twice % 59),
            ("set again as one of several names in a tuple", down("spare, BG_TOP, other = None, (1, 2, 3), None"), twice % 59),
            ("set again behind a star", down("first, *BG_TOP = 1, 2, 3"), twice % 59),
            ("set again in brackets", down("[BG_TOP, spare] = (1, 2, 3), 4"), twice % 59),
            ("set again with a type", down("BG_TOP: tuple = (1, 2, 3)"), twice % 59),
            ("named with a type and no value", down("BG_TOP: tuple"), twice % 59),
            ("added to", down("BG_TOP += (1,)"), twice % 59),
            ("set inside an expression", down("print((BG_TOP := (1, 2, 3)), file=sys.stderr)"), twice % 59),
            ("the name a loop runs over", down("for BG_TOP in ((1, 2, 3),): pass"), twice % 59),
            ("the name a `with` gives", down("with open(__file__) as BG_TOP: pass"), twice % 59),
            ("the name a comprehension runs over", down("spare = [BG_TOP for BG_TOP in range(3)]"), "BG_TOP is set or bound 2 times (lines 52 and 59)"),
            ("imported under that name", down("import os as BG_TOP"), twice % 59),
            ("imported from a module under that name", down("from os import sep as BG_TOP"), twice % 59),
            ("a function of that name", down("def BG_TOP(): return (1, 2, 3)"), twice % 59),
            ("a class of that name", down("class BG_TOP: pass"), twice % 59),
            ("a parameter of that name", down("def lighter(BG_TOP=(1, 2, 3)): return BG_TOP"), twice % 59),
            ("the parameter of a lambda", down("lighter = lambda BG_TOP: BG_TOP"), twice % 59),
            ("the name an `except` gives", down("try:\n    raise ValueError\nexcept ValueError as BG_TOP: pass"), twice % 61),
            ("set in a function that calls it global", down("def reset():\n    global BG_TOP\n    BG_TOP = (1, 2, 3)"), "BG_TOP is set or bound 3 times (lines 52, 60 and 61)"),
            ("deleted", down("del BG_TOP"), twice % 59),
            ("set twice on one line", self.OG.replace(own, "BG_TOP = (30, 33, 64); BG_TOP = (1, 2, 3)", 1), "BG_TOP is set or bound 2 times (twice on line 52)"),
            ("set once, together with another name", self.OG.replace(own, "BG_TOP = SPARE = (30, 33, 64)", 1), "line 52 sets it another way: `BG_TOP = SPARE = (30, 33, 64)"),
            ("set once, with a type", self.OG.replace(own, "BG_TOP: tuple = (30, 33, 64)", 1), "line 52 sets it another way: `BG_TOP: tuple = (30, 33, 64)"),
            ("set once, under a condition", self.OG.replace(own, "if True:\n    BG_TOP = (30, 33, 64)", 1), "line 53 sets it another way: `BG_TOP = (30, 33, 64) # background gradient, top (deep brand tone)`, which does not begin at the start of the line"),
            ("set once, after another statement on the line", self.OG.replace(own, "spare = 1; BG_TOP = (30, 33, 64)", 1), "line 52 sets it another way: `spare = 1; BG_TOP = (30, 33, 64)"),
            ("set once, over two lines", self.OG.replace(own, "BG_TOP = (30, 33,\n          64)", 1), "line 52 sets it another way: `BG_TOP = (30, 33,`"),
            ("set once, with another statement after it", self.OG.replace(own, "BG_TOP = (30, 33, 64); spare = 1", 1), "line 52 sets it another way"),
            # a line that reads exactly as the line asked for, and is a parameter of a function or a lambda written over several lines
            ("a parameter on a line by itself", self.OG.replace(own, "def top(\nBG_TOP = (30, 33, 64)\n): return BG_TOP", 1),
             "line 53 sets it another way: `BG_TOP = (30, 33, 64)`, which is a part of something that runs over several lines"),
            ("a lambda's parameter on a line by itself", self.OG.replace(own, "top = (lambda\nBG_TOP = (30, 33, 64)\n: BG_TOP)", 1),
             "line 53 sets it another way: `BG_TOP = (30, 33, 64)`, which is a part of something that runs over several lines"),
            ("a hex text", self.OG.replace(own, 'BG_TOP = "#1e2140"', 1), 'line 52 sets it another way: `BG_TOP = "#1e2140"'),
            ("worked out", self.OG.replace(own, "BG_TOP = tuple([30, 33, 64])", 1), "line 52 sets it another way: `BG_TOP = tuple([30, 33, 64])"),
            ("a sum", self.OG.replace(own, "BG_TOP = (30, 33, 64) + ()", 1), "line 52 sets it another way"),
            ("two numbers", self.OG.replace(own, "BG_TOP = (30, 33)", 1), "line 52 sets it another way"),
            ("four numbers", self.OG.replace(own, "BG_TOP = (30, 33, 64, 255)", 1), "line 52 sets it another way"),
            ("a decimal", self.OG.replace(own, "BG_TOP = (30.0, 33, 64)", 1), "line 52 sets it another way"),
            ("a number below nought", self.OG.replace(own, "BG_TOP = (-30, 33, 64)", 1), "line 52 sets it another way"),
            ("a list", self.OG.replace(own, "BG_TOP = [30, 33, 64]", 1), "line 52 sets it another way"),
            ("not there", re.sub(r"(?m)^BG_TOP = .*\n", "", self.OG), "nothing in the file sets BG_TOP. Write that one line beside the generator's other colours"),
            ("only as an entry of something else", re.sub(r"(?m)^BG_TOP = .*\n", "import types\ncard = types.SimpleNamespace()\ncard.BG_TOP = (30, 33, 64)\n", self.OG), "nothing in the file sets BG_TOP"),
        ]
        if sys.version_info >= (3, 10):
            cases.append(("the name a `match` catches", down("match (1, 2, 3):\n    case BG_TOP: pass"), twice % 60))
            cases.append(("the rest a `match` catches", down("match [1, 2, 3]:\n    case [first, *BG_TOP]: pass"), twice % 60))
        return [(label, text, "BG_TOP", saying) for label, text, saying in cases]

    def test_a_name_that_is_set_or_bound_anywhere_else_or_another_way_is_refused_with_the_lines(self):
        # Python uses the last one it runs: an edit of the first would change nothing and be reported as done
        for label, text, name, saying in self.refusals():
            with self.subTest(label=label):
                compile(text, "generate_og_cards.py", "exec")   # each of these is Python that runs
                message = self.refused(text, saying, **{name: self.WANT[name]})
                self.assertEqual(self.line_asked_for(message), "BG_TOP = (42, 31, 23)")
        self.refused("import BG_TOP.colours\n" + self.OG, "BG_TOP is set or bound 2 times (lines 1 and 53)", BG_TOP="#2a1f17")   # a module imported by a dotted name binds its first part
        for name in self.NAMES:
            with self.subTest(name=name):
                text = re.sub(r"(?m)^%s = \(.*\)" % name, "%s = pick_a_colour()" % name, self.OG)
                message = self.refused(text, "sets it another way: `%s = pick_a_colour()" % name, **self.WANT)
                self.assertEqual(self.line_asked_for(message), "%s = (%d, %d, %d)" % ((name,) + tuple(self.RGB[name])))

    def test_doing_what_a_refusal_says_makes_the_next_run_go_through_and_python_then_has_the_colour(self):
        ends = []
        for label, text, name, _saying in self.refusals():
            with self.subTest(label=label):
                mended, said = self.followed(text, **self.WANT)
                self.assertEqual(len(said), 1, "one refusal, then it goes through")
                new, changes = self.set(mended, **self.WANT)
                self.assertNotIn(name, [n for n, _old, _value in changes], "her line already says it")
                self.assertIn("\nBG_TOP = (42, 31, 23)\n", new, "written exactly as the refusal showed it, and left so")
                ends.append((label, new))
        for (label, _new), got in zip(ends, generator_as_python_runs_it([new for _label, new in ends])):
            with self.subTest(label=label):
                self.assertEqual(got, self.RGB, "what the generator draws with is what the tool says the file holds")

    def test_a_refused_shape_is_one_where_python_has_another_colour_than_an_edit_of_the_starters_line_would_give(self):
        # why the count matters: for each shape that names the colour a second time and runs, the generator's top is
        # run with the starter's own line edited by hand, and what Python then has is NOT the colour written there
        again = [(label, text) for label, text, _name, saying in self.refusals() if "set or bound" in saying and "BG_TOP = (30, 33, 64)" in text and label not in (
            "named with a type and no value", "the name a comprehension runs over", "a parameter of that name", "the parameter of a lambda", "set in a function that calls it global")]
        self.assertGreater(len(again), 15)
        for (label, _text), got in zip(again, generator_as_python_runs_it([text.replace("BG_TOP = (30, 33, 64)", "BG_TOP = (42, 31, 23)", 1) for _label, text in again])):
            with self.subTest(label=label):
                self.assertNotEqual(got.get("BG_TOP"), [42, 31, 23], got)

    def test_the_caller_is_told_the_line_each_colour_stands_on_set_or_left(self):
        where = {}
        new, changes = _site.set_lines(self.rel, self.OG, self.WANT, where)
        self.assertEqual(len(changes), 6)
        self.assertEqual(where, {name: 52 + n for n, (name, _key) in enumerate(_site.OG_COLOURS)})
        again = {}
        self.assertEqual(_site.set_lines(self.rel, new, self.WANT, again), (new, []))
        self.assertEqual(again, where, "a line that already says the colour is told as well")
        marked = {}
        with_mark = _site.set_lines(self.rel, "\ufeff" + self.OG, self.WANT, marked)[0]
        self.assertEqual((with_mark, marked), ("\ufeff" + new, where), "a byte order mark at the start of the file is read past and kept")

    def test_a_file_python_cannot_read_and_one_that_imports_every_name_of_a_module_are_refused_by_name(self):
        own = "BG_TOP = (30, 33, 64)"
        for label, text, line, mend in (
                ("a number written with a nought in front, which Python does not take", self.OG.replace("BG_BOT = (10, 11, 30)", "BG_BOT = ( 010,11 , 30 )"), 53, lambda t: t.replace("( 010,11 , 30 )", "(10, 11, 30)")),
                ("a bracket that is never closed", self.OG.replace(own, "BG_TOP = (30, 33, 64"), None, lambda t: t.replace("BG_TOP = (30, 33, 64", own)),
                ("a line indented for no reason", self.OG.replace(own, "  " + own), 52, lambda t: t.replace("  " + own, own)),
                ("a null byte", self.OG.replace(own, own + "\x00"), None, lambda t: t.replace("\x00", ""))):
            with self.subTest(label=label):
                with self.assertRaises(Refusal) as cm:
                    self.set(text, **self.WANT)
                message = str(cm.exception)
                self.assertEqual(cm.exception.code, "og-layout")
                self.assertTrue(message.startswith("scripts/generate_og_cards.py is not Python that this tool can read (Python %d.%d says: " % sys.version_info[:2]), message)
                if line:
                    self.assertIn("says: line %d: " % line, message)
                self.assertIn("so this tool does not edit it. Mend that so that the file runs under this Python, or run this tool with the Python the site uses, then run this again.", message)
                self.assertEqual(len(self.set(mend(text), **self.WANT)[1]), 6)
        if sys.version_info < (3, 10):   # what a newer Python reads and this one does not is refused, not guessed at
            with self.assertRaises(Refusal) as cm:
                self.set(self.further_down("match (1, 2, 3):\n    case BG_TOP: pass"), **self.WANT)
            self.assertIn("is not Python that this tool can read (Python 3.%d says: line 59: " % sys.version_info[1], str(cm.exception))
        huge = self.OG.replace(own, "BG_TOP = (%s, 33, 64)" % ("9" * 5000))   # Python 3.11 and newer do not read it; before that it is a number, and no colour
        with self.assertRaises(Refusal) as cm:
            self.set(huge, **self.WANT)
        self.assertRegex(str(cm.exception), r"is not Python that this tool can read|line 52 sets it another way")
        for label, text, said in (("at the top", "from os.path import *\n" + self.OG, "line 1: `from os.path import *`"),
                                  ("further down", self.further_down("from os import *"), "line 59: `from os import *`"),
                                  ("from the folder itself", self.further_down("from . import *"), "line 59: `from . import *`")):
            with self.subTest(label=label):
                with self.assertRaises(Refusal) as cm:
                    self.set(text, **self.WANT)
                self.assertEqual(cm.exception.code, "og-layout")
                self.assertIn("scripts/generate_og_cards.py, %s brings in names this tool cannot see" % said, str(cm.exception))
                self.assertIn("Name what is imported there in place of the `*`, then run this again.", str(cm.exception))
                self.assertEqual(len(self.set(text.replace("import *", "import sep"), **self.WANT)[1]), 6, "mended as the refusal says, it is edited like any other")

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
        left = self.j.rollback()
        self.assertTrue(os.path.isfile(os.path.join(self.site, "brand-handoff", "someone-elses.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.site, "brand-handoff", "pack.zip")))
        self.assertEqual([rel for rel, _why in left], ["brand-handoff"], "and the folder, which was not there before the run, is named: the site is not as it was")
        self.assertEqual([rel for rel, _why in self.j.rollback()], ["brand-handoff"], "asked again, it says the same, once")

    def test_a_folder_the_run_made_and_cannot_take_away_again_is_named_whatever_keeps_it_there(self):
        # the site's tests made the site's folder read-only: the files in the new folder go, the folder cannot
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root may write anywhere, so nothing can be closed to it")
        self.j.write("brand-handoff/deep/pack.zip", b"zip")
        self.j.write("public/favicon.svg", b"<svg>new</svg>")
        os.chmod(self.site, 0o555)
        self.addCleanup(os.chmod, self.site, 0o755)
        left = self.j.rollback()
        self.assertEqual([rel for rel, _why in left], ["brand-handoff"], "named once; the folder inside it could be removed and is not named")
        self.assertEqual(os.listdir(os.path.join(self.site, "brand-handoff")), [], "what the run wrote into it is gone")
        self.assertEqual(T.read_bytes(os.path.join(self.site, "public", "favicon.svg")), b"<svg/>", "and every file is put back all the same")
        os.chmod(self.site, 0o755)
        self.assertEqual(self.j.rollback(), [], "once the folder can be written in again, it goes")
        self.assertEqual(tree(self.site), self.before)

    def test_a_folder_that_only_holds_what_is_named_already_is_not_named_a_second_time(self):
        self.j.write("brand-handoff/pack.zip", b"zip")
        real = os.remove

        def refusing(path, *a, **k):
            if path.endswith("pack.zip"):
                raise PermissionError(13, "Permission denied", path)
            return real(path, *a, **k)
        os.remove = refusing
        try:
            left = self.j.rollback()
        finally:
            os.remove = real
        self.assertEqual(left, [("brand-handoff/pack.zip", "Permission denied")], "the file that keeps the folder there says it all")

    def test_a_folder_that_holds_something_nobody_named_beside_what_is_named_is_named_itself(self):
        # after a run that failed, everything that is not as before is named: one thing in a folder being named
        # says nothing of the other things in it
        def refusing(real, ends):
            def remove(path, *a, **k):
                if str(path).endswith(ends):
                    raise PermissionError(13, "Permission denied", path)
                return real(path, *a, **k)
            return remove

        def rollback(ends, listdir=None):
            real, really = os.remove, os.listdir
            os.remove = refusing(real, ends)
            os.listdir = listdir or really
            try:
                return self.j.rollback()
            finally:
                os.remove, os.listdir = real, really
        self.j.write("brand-handoff/pack.zip", b"zip")
        self.j.write("brand-handoff/deep/down/preview.png", b"png")
        with open(os.path.join(self.site, "brand-handoff", "someone-elses.txt"), "wb") as f:
            f.write(b"put there while the run was going")
        left = rollback("pack.zip")
        self.assertEqual(sorted(rel for rel, _why in left), ["brand-handoff", "brand-handoff/pack.zip"], "the file that could not be removed, and the folder, which also holds a file nobody named")
        os.remove(os.path.join(self.site, "brand-handoff", "someone-elses.txt"))
        self.assertEqual([rel for rel, _why in rollback("pack.zip")], ["brand-handoff/pack.zip"], "with the other file gone, the named file says it all")
        # two files in two folders, one inside the other: each folder holds only what is named, or a folder of which that is true
        self.j.write("brand-handoff/deep/down/preview.png", b"png")
        self.assertEqual(sorted(rel for rel, _why in rollback((".zip", ".png"))), ["brand-handoff/deep/down/preview.png", "brand-handoff/pack.zip"])
        with open(os.path.join(self.site, "brand-handoff", "deep", "down", "stray.txt"), "wb") as f:
            f.write(b"stray")
        self.assertEqual(sorted(rel for rel, _why in rollback((".zip", ".png"))), ["brand-handoff/deep/down", "brand-handoff/deep/down/preview.png", "brand-handoff/pack.zip"],
                         "a file nobody named, two folders down: the folder that holds it is named, and the folders above that one hold nothing but what is named")
        os.remove(os.path.join(self.site, "brand-handoff", "deep", "down", "stray.txt"))
        # a folder that cannot be listed is not known to hold only what is named

        def closed(path):
            if str(path).endswith("brand-handoff"):
                raise PermissionError(13, "Permission denied", path)
            return os_listdir(path)
        os_listdir = os.listdir
        self.assertEqual(sorted(rel for rel, _why in rollback((".zip", ".png"), closed)), ["brand-handoff", "brand-handoff/deep/down/preview.png", "brand-handoff/pack.zip"])
        self.assertEqual(self.j.rollback(), [], "and once nothing is in the way, everything goes")
        self.assertEqual(tree(self.site), self.before)

    def test_a_kept_folder_whose_folder_above_was_taken_away_comes_back_with_it(self):
        # the site's tests removed public/images altogether: the cards come back, their folder and the one above it too
        self.j.snapshot_dir("public/images/og")
        self.j.write("public/favicon.ico", b"ico")
        self.j.write("public/favicon.svg", b"<svg>new</svg>")
        shutil.rmtree(os.path.join(self.site, "public", "images"))
        self.assertEqual(self.j.rollback(), [])
        self.assertEqual(tree(self.site), self.before)
        shutil.rmtree(os.path.join(self.site, "public"))        # and with everything above it gone
        self.assertEqual(self.j.rollback(), [])
        self.assertEqual(sorted(os.listdir(self.og())), ["default.jpg", "other.jpg"], "the kept cards are back")
        self.assertEqual(tree(self.site), self.before, "and so is the file this run had replaced beside them, now that its folder is there again")

    def test_a_folder_to_keep_whose_first_last_or_only_file_is_empty_is_kept_like_any_other(self):
        # the largest file is looked for by size: an empty file beside it is no reason to compare two names, or a name with none
        for label, names in (("an empty file first", (".gitkeep", "a.jpg")), ("an empty file last", ("a.jpg", "z-empty")), ("an empty file alone", (".gitkeep",)),
                             ("two empty files", (".gitkeep", "z-empty")), ("an empty file between two", ("a.jpg", "m-empty", "z.jpg")), ("an empty folder", ())):
            with self.subTest(label=label):
                shutil.rmtree(self.og())
                os.makedirs(self.og())
                for name in names:
                    with open(self.og(name), "wb") as f:
                        f.write(b"" if "empty" in name or name == ".gitkeep" else b"card")
                before = tree(self.site)
                j = _site.Journal(self.site)
                j.snapshot_dir("public/images/og")
                for name in names:
                    os.remove(self.og(name))
                self.assertEqual(j.rollback(), [])
                self.assertEqual(tree(self.site), before)
        with open(self.og("big.jpg"), "wb") as f:
            f.write(b"x" * 4096)
        real = _site.MAX_KEPT
        _site.MAX_KEPT = 1024
        try:
            with self.assertRaises(Refusal) as cm:
                _site.Journal(self.site).snapshot_dir("public/images/og")
        finally:
            _site.MAX_KEPT = real
        self.assertIn("the largest file it came to is public/images/og/big.jpg", str(cm.exception))

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
        self.assertIn("public/images/og is a link, and nothing is written through a link. Put", str(cm.exception))
        os.remove(self.og())
        os.rename(elsewhere, self.og())
        images = os.path.join(self.tmp.name, "images-kept-elsewhere")
        os.rename(os.path.join(self.site, "public", "images"), images)
        os.symlink(images, os.path.join(self.site, "public", "images"))
        with self.assertRaises(Refusal) as cm:
            self.j.snapshot_dir("public/images/og")
        self.assertIn("public/images is a link, and nothing is written through a link (public/images/og is below it). Put", str(cm.exception), "the link is the path that is named")
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
                    # the path that IS the link is named, with what would have gone below it where that is another path
                    self.assertIn("%s is a link, and nothing is written through a link%s. Put the file or folder itself where the link is"
                                  % (("linked", " (%s is below it)" % rel) if rel.startswith("linked/") else (rel, "")), str(cm.exception))
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
