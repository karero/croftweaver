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

    def test_a_comment_between_a_value_and_its_semicolon_stays_and_so_does_important(self):
        # only the value is replaced: what the owner wrote after it is hers
        text = self.CSS.replace("  --bg: #ffffff;", "  --bg: #ffffff /* the page */;", 1).replace("  --bg-soft: #f5f7fb;", "  --bg-soft: #f5f7fb !important;", 1)
        self.assertNotEqual(text, self.CSS)
        new = _site.edit_css(text, bakery())
        self.assertIn("  --bg: #fff8ee /* the page */;", new)
        self.assertIn("  --bg-soft: #fef5e8 !important;", new)
        self.assertEqual(_palette.read_css(new).light["bg"], T.BAKERY_LIGHT["bg"])

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
        later = self.CSS + '\n:root[data-theme="dark"] {\n  --brand: #123456;\n}\n'
        for name, text, block in (("the dark block", self.CSS.replace(dark, dark + "  --brand: #123456;\n", 1), '`:root[data-theme="dark"]` block'),
                                  ("the block for visitors without JavaScript", self.CSS.replace(media, media + "    --brand: #123456;\n", 1), "inside the `@media (prefers-color-scheme: dark)` block"),
                                  ("the palette's own value there", self.CSS.replace(dark, dark + "  --brand: #b4531a;\n", 1), '`:root[data-theme="dark"]` block'),
                                  ("a second dark block further down", later, '`:root[data-theme="dark"]` block')):
            with self.subTest(name=name):
                self.assertNotEqual(text, self.CSS)
                with self.assertRaises(Refusal) as cm:
                    _site.edit_css(text, bakery())
                self.assertEqual(cm.exception.code, "css-primary-in-dark")
                self.assertIn("--brand (the Primary) inside", str(cm.exception))
                self.assertIn(block, str(cm.exception))

    def test_a_primary_that_a_dark_block_only_mentions_in_a_comment_or_under_another_name_is_no_reason_to_refuse(self):
        dark = ':root[data-theme="dark"] {\n'
        for extra in ("  /* --brand: #123456; */\n", "  --my-brand: #123456;\n", "  --brand-soft: #123456;\n"):
            with self.subTest(extra=extra):
                new = _site.edit_css(self.CSS.replace(dark, dark + extra, 1), bakery())
                self.assertIn(extra, new)
                self.assertEqual(_palette.read_css(new).brand, "#b4531a")


class Config(unittest.TestCase):
    CONFIG = T.starter_file("src/config.ts")

    def test_the_theme_colour_is_the_primary_and_nothing_else_moves(self):
        new = _site.edit_config(self.CONFIG, "#b4531a")
        self.assertEqual(len(changed_lines(self.CONFIG, new)), 2)
        self.assertEqual(new.replace("themeColor: '#b4531a'", "themeColor: '#000000'"), self.CONFIG)

    def test_company_logo_is_set_to_the_derived_png(self):
        new = _site.edit_config(self.CONFIG.replace("logo: '/images/logo.png',", "logo: '/images/other.png',"), "#b4531a", logo=True)
        self.assertIn("logo: '/images/logo.png',", new)
        self.assertEqual(_site.edit_config(self.CONFIG, "#b4531a", logo=True), _site.edit_config(self.CONFIG, "#b4531a"))

    def test_with_no_colours_to_set_the_theme_colour_stays(self):
        new = _site.edit_config(self.CONFIG.replace("logo: '/images/logo.png',", "logo: '/images/x.png',"), None, logo=True)
        self.assertIn("themeColor: '#000000'", new)
        self.assertIn("logo: '/images/logo.png',", new)
        self.assertEqual(_site.edit_config(self.CONFIG, None), self.CONFIG)

    def test_without_a_logo_company_logo_is_left_as_the_starter_has_it(self):
        other = self.CONFIG.replace("logo: '/images/logo.png',", "logo: '/images/other.png',")
        self.assertIn("logo: '/images/other.png',", _site.edit_config(other, "#b4531a"))

    def test_a_config_without_the_line_is_refused(self):
        with self.assertRaises(Refusal) as cm:
            _site.edit_config(self.CONFIG.replace("themeColor:", "colour:"), "#b4531a")
        self.assertEqual(cm.exception.code, "config-layout")
        self.assertIn("themeColor", str(cm.exception))
        with self.assertRaises(Refusal) as cm:
            _site.edit_config(self.CONFIG.replace("logo: '/images/logo.png',", ""), "#b4531a", logo=True)
        self.assertIn("logo", str(cm.exception))

    def test_a_logo_line_outside_the_company_block_is_not_the_one(self):
        # SAME_AS etc. may carry a logo-looking string; only COMPANY.logo is set
        text = self.CONFIG.replace("export const SAME_AS: string[] = [", "export const SAME_AS: string[] = [\n  // logo: '/x.png',")
        new = _site.edit_config(text, "#b4531a", logo=True)
        self.assertIn("// logo: '/x.png',", new)

    def test_a_theme_colour_in_another_object_before_site_is_not_the_one(self):
        other = "export const PRINT = {\n  themeColor: '#111111',\n} as const;\n\n"
        new = _site.edit_config(other + self.CONFIG, "#b4531a")
        self.assertTrue(new.startswith(other), "the other object is left exactly as it was")
        self.assertEqual(new[len(other):], _site.edit_config(self.CONFIG, "#b4531a"))

    def test_a_key_of_an_object_nested_in_the_block_is_not_the_blocks_own(self):
        nested = self.CONFIG.replace("export const COMPANY = {\n", "export const COMPANY = {\n  parent: {\n    logo: '/images/parent.png',\n  },\n", 1) \
                            .replace("export const SITE = {\n", "export const SITE = {\n  print: {\n    themeColor: '#111111',\n  },\n", 1)
        new = _site.edit_config(nested.replace("logo: '/images/logo.png',", "logo: '/images/own.png',"), "#b4531a", logo=True)
        self.assertIn("    logo: '/images/parent.png',", new)
        self.assertIn("    themeColor: '#111111',", new)
        self.assertIn("  logo: '/images/logo.png',", new)
        self.assertIn("  themeColor: '#b4531a',", new)

    def test_a_key_that_stands_twice_at_the_blocks_own_level_is_refused_as_ambiguous(self):
        twice = self.CONFIG.replace("  locale: 'en',\n", "  locale: 'en',\n  themeColor: '#111111',\n", 1)
        with self.assertRaises(Refusal) as cm:
            _site.edit_config(twice, "#b4531a")
        self.assertEqual(cm.exception.code, "config-layout")
        self.assertIn("twice", str(cm.exception))

    def test_what_company_logo_says_now_can_be_asked(self):
        self.assertEqual(_site.company_logo(self.CONFIG), "/images/logo.png")
        self.assertEqual(_site.company_logo(self.CONFIG.replace("logo: '/images/logo.png',", 'logo: "/brand/mine.svg",')), "/brand/mine.svg")
        self.assertIsNone(_site.company_logo(self.CONFIG.replace("logo: '/images/logo.png',", "")))

    # the starter's config with the comments after its two lines taken off, so that a test can swap the whole line
    PLAIN = re.sub(r"(?m)^(  (?:themeColor|logo): '[^']*',)[^\n]*$", r"\1", CONFIG)

    def block(self, const):
        """The starter's `export const <const> = {...}`, with other values in it: what an old copy looks like."""
        start = self.CONFIG.index("export const %s" % const)
        text = self.CONFIG[start:self.CONFIG.index("\n}", start) + 2]
        return text.replace("themeColor: '#000000'", "themeColor: '#111111'").replace("logo: '/images/logo.png'", "logo: '/old/logo.png'")

    def test_a_copy_of_the_block_in_a_comment_or_in_a_string_is_not_the_block(self):
        # an edit changes the value the site reads, or nothing: the first text that looks like the block may
        # be one the program never sees
        config = self.CONFIG.replace("logo: '/images/logo.png',", "logo: '/images/mine.png',")
        want = _site.edit_config(config, "#b4531a", logo=True)
        for const in ("SITE", "COMPANY"):
            old = self.block(const)
            self.assertNotIn(old, self.CONFIG)
            for name, copy in (("a block comment", "/*\n" + old + "\n*/\n"),
                               ("line comments", "".join("// " + line + "\n" for line in old.splitlines())),
                               ("a template string", "const notes = `\n" + old + "\n`;\n"),
                               ("a string", "const before = \"export const %s = { themeColor: '#111111', logo: '/old/logo.png' }\";\n" % const)):
                for where in ("above", "below"):
                    with self.subTest(const=const, name=name, where=where):
                        text = copy + config if where == "above" else config + copy
                        new = _site.edit_config(text, "#b4531a", logo=True)
                        self.assertEqual(new, copy + want if where == "above" else want + copy, "the real block is set and the copy is left exactly as it was")
                        self.assertEqual((_site.theme_colour(text), _site.company_logo(text)), ("#000000", "/images/mine.png"), "and it is the real block that is read")

    def test_a_block_that_is_declared_twice_is_refused_because_which_one_the_site_reads_cannot_be_known(self):
        for const, call in (("SITE", lambda t: _site.edit_config(t, "#b4531a")), ("COMPANY", lambda t: _site.edit_config(t, None, logo=True)),
                            ("SITE", _site.theme_colour), ("COMPANY", _site.company_logo)):
            for where in ("above", "below"):
                with self.subTest(const=const, where=where):
                    text = self.block(const) + "\n" + self.CONFIG if where == "above" else self.CONFIG + "\n" + self.block(const) + "\n"
                    with self.assertRaises(Refusal) as cm:
                        call(text)
                    self.assertEqual(cm.exception.code, "config-layout")
                    self.assertIn("`export const %s` twice" % const, str(cm.exception))

    def test_a_key_written_with_quotes_is_the_same_key(self):
        for quoted in ("'themeColor': '#000000'", '"themeColor": "#000000"', "'themeColor' : '#000000'"):
            with self.subTest(quoted=quoted):
                text = self.CONFIG.replace("themeColor: '#000000'", quoted)
                self.assertNotEqual(text, self.CONFIG)
                self.assertEqual(_site.edit_config(text, "#b4531a"), text.replace("#000000", "#b4531a"))
        self.assertEqual(_site.company_logo(self.CONFIG.replace("logo: '/images/logo.png'", "'logo': '/mine.png'")), "/mine.png")

    def test_a_key_set_twice_is_refused_however_each_is_spelt_whatever_its_value_and_wherever_on_the_line_it_stands(self):
        # the last one wins in the browser; the edit must not pick one by its place or by how its value is written
        own = "  themeColor: '#000000',\n"
        self.assertIn(own, self.PLAIN)
        for name, lines in (("quoted, then plain", "  'themeColor': '#111111',\n" + own), ("plain, then quoted", own + "  'themeColor': '#111111',\n"),
                            ("double quotes", own + '  "themeColor": "#111111",\n'),
                            ("a value that is no colour, first", "  themeColor: OLD_COLOUR,\n" + own), ("a value that is no colour, last", own + "  themeColor: OLD_COLOUR,\n"),
                            ("both on one line", "  themeColor: '#000000', themeColor: '#111111',\n"),
                            ("after another entry on its line", own + "  locale2: 'en', themeColor: '#111111',\n")):
            with self.subTest(name=name):
                with self.assertRaises(Refusal) as cm:
                    _site.edit_config(self.PLAIN.replace(own, lines), "#b4531a")
                self.assertEqual(cm.exception.code, "config-layout")
                self.assertIn("sets `themeColor` twice in SITE", str(cm.exception))
        self.assertIn("  logo: '/images/logo.png',\n", self.PLAIN)
        twice = self.PLAIN.replace("  logo: '/images/logo.png',\n", "  logo: '/images/logo.png',\n  'logo': '/other.png',\n")
        with self.assertRaises(Refusal) as cm:
            _site.edit_config(twice, None, logo=True)
        self.assertIn("sets `logo` twice in COMPANY", str(cm.exception))

    def test_a_key_is_found_wherever_on_its_line_it_stands_and_a_word_that_only_looks_like_one_is_not_a_key(self):
        own = "  themeColor: '#000000',\n"
        for name, lines, after in (("after a nested object on the same line", "  nav: { themeColor: '#111111' }, themeColor: '#000000',\n", "  nav: { themeColor: '#111111' }, themeColor: '#b4531a',\n"),
                                   ("a space before the colon", "  themeColor : '#000000',\n", "  themeColor : '#b4531a',\n"),
                                   ("the name as a value", "  key: 'themeColor',\n" + own, "  key: 'themeColor',\n  themeColor: '#b4531a',\n"),
                                   ("the name in a choice", "  tint: dark ? themeColor : '#111111',\n" + own, "  tint: dark ? themeColor : '#111111',\n  themeColor: '#b4531a',\n"),
                                   ("the name in a longer name", "  darkthemeColor: '#111111',\n" + own, "  darkthemeColor: '#111111',\n  themeColor: '#b4531a',\n")):
            with self.subTest(name=name):
                self.assertEqual(_site.edit_config(self.PLAIN.replace(own, lines), "#b4531a"), self.PLAIN.replace(own, after))

    def test_a_value_with_a_backslash_in_it_is_refused_by_name_and_never_cut_at_the_escaped_quote(self):
        line = "  logo: '/images/logo.png',\n"
        for name, value in (("an escaped single quote", "'/it\\'s.png'"), ("an escaped double quote", '"/say-\\"hi\\".png"'), ("an escaped backslash", "'/a\\\\b.png'")):
            with self.subTest(name=name):
                text = self.PLAIN.replace(line, "  logo: %s,\n" % value)
                self.assertNotEqual(text, self.PLAIN)
                for call in (lambda: _site.edit_config(text, None, logo=True), lambda: _site.company_logo(text)):
                    with self.assertRaises(Refusal) as cm:
                        call()
                    self.assertEqual(cm.exception.code, "config-layout")
                    self.assertIn("the value of `logo` in COMPANY has a backslash in it", str(cm.exception))
        # the other quote inside the value needs no backslash, and is part of the value
        text = self.PLAIN.replace(line, '  logo: "/it\'s.png",\n')
        self.assertEqual(_site.company_logo(text), "/it's.png")
        self.assertEqual(_site.edit_config(text, None, logo=True), self.PLAIN.replace(line, '  logo: "/images/logo.png",\n'))

    def test_what_the_theme_colour_says_now_can_be_asked(self):
        self.assertEqual(_site.theme_colour(self.CONFIG), "#000000")
        self.assertIsNone(_site.theme_colour(self.CONFIG.replace("themeColor: '#000000'", "themeColor: BRAND")))


class Manifest(unittest.TestCase):
    MANIFEST = T.starter_file("public/manifest.webmanifest")

    def test_theme_is_the_primary_and_background_the_light_page_colour(self):
        new = _site.edit_manifest(self.MANIFEST, "#b4531a", "#fff8ee")
        data = json.loads(new)
        self.assertEqual((data["theme_color"], data["background_color"]), ("#b4531a", "#fff8ee"))
        self.assertEqual(len(changed_lines(self.MANIFEST, new)), 4)
        self.assertEqual(data["icons"], json.loads(self.MANIFEST)["icons"])

    def test_a_manifest_that_was_not_valid_json_to_begin_with_is_not_touched(self):
        with self.assertRaises(Refusal) as cm:
            _site.edit_manifest(self.MANIFEST.replace('"standalone",', '"standalone",,'), "#b4531a", "#fff8ee")
        self.assertEqual(cm.exception.code, "manifest-layout")
        self.assertIn("JSON", str(cm.exception))

    def test_a_manifest_without_the_keys_is_refused(self):
        for key in ("theme_color", "background_color"):
            with self.subTest(key=key):
                with self.assertRaises(Refusal) as cm:
                    _site.edit_manifest(self.MANIFEST.replace('"%s"' % key, '"x_%s"' % key), "#b4531a", "#fff8ee")
                self.assertEqual(cm.exception.code, "manifest-layout")
                self.assertIn(key, str(cm.exception))

    def test_a_colour_of_the_same_name_inside_another_entry_before_the_manifests_own_is_refused(self):
        # the edit sets the first line of each name; when that is not the manifest's own, its own stays
        # as it was, which only reading the result back can show
        for key in ("theme_color", "background_color"):
            with self.subTest(key=key):
                nested = self.MANIFEST.replace('  "lang": "en",', '  "lang": "en",\n  "shortcuts": [{ "name": "x", "url": "/x", "%s": "#111111" }],' % key, 1)
                self.assertEqual(json.loads(nested)["shortcuts"][0][key], "#111111")
                with self.assertRaises(Refusal) as cm:
                    _site.edit_manifest(nested, "#b4531a", "#fff8ee")
                self.assertEqual(cm.exception.code, "manifest-layout")
                self.assertIn("by hand", str(cm.exception))

    NESTED = '  "lang": "en",\n  "shortcuts": [{ "name": "x", "url": "/x", "theme_color": "#111111", "background_color": "#222222" }],'

    def nested(self, **own):
        text = self.MANIFEST.replace('  "lang": "en",', self.NESTED, 1)
        for key, value in own.items():
            was = json.loads(self.MANIFEST)[key]
            self.assertEqual(text.count('"%s": "%s"' % (key, was)), 1)
            text = text.replace('"%s": "%s"' % (key, was), '"%s": "%s"' % (key, value))
        self.assertEqual(json.loads(text)["shortcuts"][0]["theme_color"], "#111111")
        return text

    def test_a_manifest_that_already_holds_both_colours_is_not_edited_at_all_whatever_else_in_it_has_a_colour_of_that_name(self):
        # what she is told to do after the refusal below: set the manifest's own two by hand. The next run
        # must then leave the file alone, not edit the first line of that name and call it done.
        done = self.nested(theme_color="#b4531a", background_color="#fff8ee")
        self.assertEqual(_site.edit_manifest(done, "#b4531a", "#fff8ee"), done)

    def test_a_colour_that_must_change_is_never_set_by_its_place_in_the_file(self):
        after_own = self.MANIFEST.replace('  "icons"', '  "related": { "theme_color": "#111111" },\n  "icons"', 1)
        self.assertEqual(json.loads(after_own)["related"]["theme_color"], "#111111")
        for name, text, key in (("another entry's colour before the manifest's own", self.nested(), "theme_color"),
                                ("another entry's colour after the manifest's own", after_own, "theme_color"),
                                ("only the background still to set", self.nested(theme_color="#b4531a"), "background_color"),
                                ("only the theme colour still to set", self.nested(background_color="#fff8ee"), "theme_color")):
            with self.subTest(name=name):
                with self.assertRaises(Refusal) as cm:
                    _site.edit_manifest(text, "#b4531a", "#fff8ee")
                self.assertEqual(cm.exception.code, "manifest-layout")
                self.assertIn('has "%s" more than once' % key, str(cm.exception))
                self.assertIn("by hand", str(cm.exception))

    def test_a_colour_that_is_already_right_is_left_alone_and_the_other_is_set(self):
        half = self.MANIFEST.replace('"theme_color": "#000000"', '"theme_color": "#b4531a"')
        new = _site.edit_manifest(half, "#b4531a", "#fff8ee")
        self.assertEqual(len(changed_lines(half, new)), 2)
        self.assertEqual(_site.manifest_colours(new), ("#b4531a", "#fff8ee"))

    def test_a_value_with_an_escaped_quote_is_replaced_whole(self):
        text = self.MANIFEST.replace('"theme_color": "#000000"', '"theme_color": "bl\\"ack"')
        self.assertEqual(json.loads(text)["theme_color"], 'bl"ack')
        self.assertEqual(_site.edit_manifest(text, "#b4531a", "#fff8ee"), _site.edit_manifest(self.MANIFEST, "#b4531a", "#fff8ee"))

    def test_what_the_manifest_says_now_can_be_asked(self):
        self.assertEqual(_site.manifest_colours(self.MANIFEST), ("#000000", "#ffffff"))
        self.assertEqual(_site.manifest_colours(self.nested()), ("#000000", "#ffffff"), "the manifest's own, not the first of that name")
        self.assertEqual(_site.manifest_colours("not json"), (None, None))
        self.assertEqual(_site.manifest_colours('{"theme_color": null, "background_color": 7}'), (None, None))


class ShareCards(unittest.TestCase):
    OG = T.starter_file("scripts/generate_og_cards.py")

    def test_the_cards_take_the_dark_themes_colours(self):
        new = _site.edit_og(self.OG, bakery(), logo=False)
        want = {"BG_TOP": "#2a1f17", "BG_BOT": "#1a120d", "TITLE_COL": "#fbeedd", "SUB_COL": "#e2874a", "ACCENT": "#e2874a", "FOOTER_COL": "#c4ae98"}
        for name, h in want.items():
            rgb = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
            self.assertRegex(new, r"(?m)^%s = \(%d, %d, %d\)" % ((name,) + rgb))
        self.assertEqual(len(changed_lines(self.OG, new)), 12)

    def test_the_card_colours_read_well_on_the_cards_own_background(self):
        # title, subtitle and footer sit on a gradient between the dark surface and the dark background
        p = bakery()
        from _colour import ratio
        for fg in ("heading", "accent", "muted"):
            for bg in ("surface", "bg"):
                self.assertGreaterEqual(ratio(p.dark[fg], p.dark[bg]), 4.5)

    def test_the_emblem_is_wired_only_when_there_is_a_logo(self):
        self.assertIn("LOGO = None", self.OG)
        self.assertIn("LOGO = None", _site.edit_og(self.OG, bakery(), logo=False))
        self.assertIn('LOGO = ROOT / "public/images/logo.png"', _site.edit_og(self.OG, bakery(), logo=True))

    def test_with_no_colours_to_set_only_the_emblem_is_touched(self):
        new = _site.edit_og(self.OG, None, logo=True)
        self.assertEqual(len(changed_lines(self.OG, new)), 2)
        self.assertIn('LOGO = ROOT / "public/images/logo.png"', new)
        self.assertIn("BG_BOT = (10, 11, 30)", new)
        self.assertEqual(_site.edit_og(self.OG, None, logo=False), self.OG)

    def test_an_emblem_already_wired_is_left_as_it_is_and_another_one_is_not_replaced(self):
        wired = self.OG.replace("LOGO = None", 'LOGO = ROOT / "public/images/logo.png"')
        new = _site.edit_og(wired, bakery(), logo=True)
        self.assertEqual(new.count('LOGO = ROOT / "public/images/logo.png"'), 1)
        self.assertEqual(_site.edit_og(new, bakery(), logo=True), new)
        other = self.OG.replace("LOGO = None", 'LOGO = ROOT / "public/mine.png"')
        with self.assertRaises(Refusal) as cm:
            _site.edit_og(other, bakery(), logo=True)
        self.assertEqual(cm.exception.code, "og-layout")
        self.assertIn("LOGO", str(cm.exception))

    def test_a_generator_edited_past_recognition_is_refused_naming_the_line(self):
        for name in ("BG_TOP", "BG_BOT", "TITLE_COL", "SUB_COL", "ACCENT", "FOOTER_COL"):
            with self.subTest(name=name):
                text = re.sub(r"(?m)^%s = \(.*\)" % name, "%s = pick_a_colour()" % name, self.OG)
                with self.assertRaises(Refusal) as cm:
                    _site.edit_og(text, bakery(), logo=False)
                self.assertEqual(cm.exception.code, "og-layout")
                self.assertIn(name, str(cm.exception))

    def test_a_palette_without_the_dark_rows_the_cards_need_is_refused(self):
        p = bakery()
        del p.dark["muted"]
        with self.assertRaises(Refusal) as cm:
            _site.edit_og(self.OG, p, logo=False)
        self.assertEqual(cm.exception.code, "palette-incomplete")

    def test_an_emblem_wired_with_single_quotes_is_the_same_emblem(self):
        wired = self.OG.replace("LOGO = None", "LOGO = ROOT / 'public/images/logo.png'")
        self.assertEqual(_site.edit_og(wired, None, logo=True), wired)

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
        new = _site.edit_og(self.OG, p, logo=False)
        for line in ("TITLE_COL = (255, 238, 221)", "FOOTER_COL = (196, 174, 152)", "SUB_COL = (255, 99, 71)", "ACCENT = (255, 99, 71)", "BG_BOT = (26, 18, 13)"):
            self.assertIn(line, new)
        self.assertRegex(new, r"(?m)^BG_TOP = \(\d+, \d+, \d+\)")

    def test_the_emblem_is_where_and_as_faint_as_the_generator_draws_it(self):
        # the arithmetic the emblem check stands on, read from the starter's generator: if that changes, this says so
        for line in ("em = Image.open(LOGO).convert(\"RGBA\").resize((460, 460), Image.LANCZOS)",
                     "em.putalpha(em.getchannel(\"A\").point(lambda a: a * 20 // 100))",
                     "card.alpha_composite(em, (W - 460 + 70, (H - 460) // 2))",
                     "return W - 2 * 64 - 120  # leave clearance from the emblem",
                     "MARGIN = 64", "text_w = _emblem(card)", "fnt, lines, size = fit_title(draw, title, text_w)",
                     "draw.text((MARGIN, H - 52), SITE_URL_LABEL, font=font(False, 22), fill=FOOTER_COL)"):
            self.assertIn(line, self.OG)
        W, H = 1200, _site.OG_ROWS
        first, last = _site.OG_EMBLEM_ROWS
        self.assertEqual((first, last), ((H - 460) // 2, (H - 460) // 2 + 460))
        self.assertEqual(_site.OG_EMBLEM_STRENGTH, 20 / 100)
        self.assertGreater(64 + (W - 2 * 64 - 120), W - 460 + 70, "the text's right-hand end can lie on the emblem (x 1016 against 810): they are not kept apart")
        self.assertGreaterEqual(H - 52, last, "the footer is written below the emblem's last row, so its colour is not held against it")
        self.assertEqual(_site.OG_EMBLEM_TEXT, ("heading", "accent"))

    def test_text_that_reads_on_the_gradient_can_still_fail_where_the_emblem_lies_under_it(self):
        p = bakery()
        self.assertEqual(_site.og_low_contrast(p), [])
        self.assertEqual(_site.og_emblem_low(p, ["#b4531a", "#6b2c0b"]), [], "the bakery's own mark")
        self.assertEqual(_site.og_emblem_low(p, []), [], "no colour, nothing to lie under the text")
        low = _site.og_emblem_low(p, ["#6b2c0b", "#ffffff"])
        self.assertEqual([(k, h, c) for k, h, _r, c in low], [("accent", "#e2874a", "#ffffff")])
        # by hand, for the top row of the emblem: the gradient there, a fifth of the way to white
        from _colour import ratio
        top, bot = (42, 31, 23), (26, 18, 13)
        row = tuple(round(top[i] + (bot[i] - top[i]) * 85 / 629) for i in range(3))
        mixed = "#%02x%02x%02x" % tuple(round(row[i] + (255 - row[i]) * 0.2) for i in range(3))
        self.assertEqual(low[0][2], ratio("#e2874a", mixed), "the lightest row under the emblem is its first")
        self.assertLess(low[0][2], 4.5)
        self.assertGreaterEqual(ratio("#e2874a", "#%02x%02x%02x" % row), 4.5, "on the gradient alone it passes")

    def test_the_colours_and_the_emblem_the_generator_holds_now_can_be_asked(self):
        self.assertEqual(_site.og_colours(self.OG), {"BG_TOP": "#1e2140", "BG_BOT": "#0a0b1e", "TITLE_COL": "#ffffff", "SUB_COL": "#8aa0ff",
                                                     "ACCENT": "#8aa0ff", "FOOTER_COL": "#9696aa"})
        odd = self.OG.replace("BG_TOP = (30, 33, 64)", "BG_TOP = pick()").replace("BG_BOT = (10, 11, 30)", "BG_BOT = (10, 11, 300)")
        self.assertEqual(sorted(_site.og_colours(odd)), ["ACCENT", "FOOTER_COL", "SUB_COL", "TITLE_COL"])
        self.assertEqual(_site.og_logo(self.OG), "none")
        self.assertEqual(_site.og_logo(self.OG.replace("LOGO = None", "LOGO = ROOT / 'public/images/logo.png'")), "ours")
        self.assertEqual(_site.og_logo(self.OG.replace("LOGO = None", 'LOGO = ROOT / "public/mine.png"')), "other")
        self.assertIsNone(_site.og_logo(self.OG.replace("LOGO = None", "EMBLEM = None")))

    def test_the_emblem_this_tool_set_can_be_taken_out_again_and_nobody_elses_is_touched(self):
        wired = _site.edit_og(self.OG, None, logo=True)
        self.assertEqual(_site.edit_og(wired, None, logo=False, unwire=True), self.OG, "back to the starter's line, its comment kept")
        self.assertEqual(_site.edit_og(self.OG, None, logo=False, unwire=True), self.OG)
        other = self.OG.replace("LOGO = None", 'LOGO = ROOT / "public/mine.png"')
        self.assertEqual(_site.edit_og(other, None, logo=False, unwire=True), other)
        self.assertEqual(_site.edit_og(wired, None, logo=False), wired, "and without being asked, the line is left alone")


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
        for rel, mention in (("linked/a.png", "link"), ("../escape.png", "not inside"), ("brand-handoff/logo.zip", "brand-handoff is a file"),
                             ("brand-handoff/deep/logo.zip", "brand-handoff is a file"), ("public/images", "is a folder")):
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
