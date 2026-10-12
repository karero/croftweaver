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
