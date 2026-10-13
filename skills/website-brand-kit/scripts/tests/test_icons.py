"""Scenarios 11, 23 and 32 (and the blank-render half of 17): the seven icon files the starter links
and the manifest declares, made from the one cleaned mark, and the preview the owner looks at.

The starter links /favicon.svg, /favicon.ico, /apple-touch-icon.png, /icon-192.png, /icon-512.png,
/icon-maskable-512.png and COMPANY.logo (/images/logo.png). The maskable and apple-touch icons sit
on a solid background chosen by contrast with the mark's colours, never the mark's own colour
(the spike's test mark vanished on it). Which background is a decision of plain arithmetic and is
tested without a renderer; making the files needs the site's sharp.
"""

import os
import struct
import tempfile
import unittest

import _testutil as T
import _colour
import _icons
import _palette
import _png
import _render
import _svg
from _refusal import Ask, Refusal


def bakery():
    p = _palette.Palette()
    p.light, p.dark, p.brand = dict(T.BAKERY_LIGHT), dict(T.BAKERY_DARK), "#b4531a"
    return p


class Candidates(unittest.TestCase):
    def test_the_light_background_then_the_dark_then_white_then_black_each_once(self):
        self.assertEqual(_icons.backgrounds(bakery()), ["#fff8ee", "#1a120d", "#ffffff", "#000000"])
        p = bakery()
        p.light["bg"] = "#ffffff"
        self.assertEqual(_icons.backgrounds(p), ["#ffffff", "#1a120d", "#000000"])

    def test_two_themes_with_the_same_background_give_it_once(self):
        p = bakery()
        p.dark["bg"] = p.light["bg"]
        self.assertEqual(_icons.backgrounds(p), ["#fff8ee", "#ffffff", "#000000"])

    def test_a_palette_with_one_theme_still_has_candidates(self):
        p = _palette.Palette()
        p.light = {"bg": "#fff8ee"}
        self.assertEqual(_icons.backgrounds(p), ["#fff8ee", "#ffffff", "#000000"])
        self.assertEqual(_icons.backgrounds(_palette.Palette()), ["#ffffff", "#000000"])


class ChoosingABackground(unittest.TestCase):
    cream, brand, brown = "#fff8ee", "#b4531a", "#6b2c0b"

    def choose(self, colours, mono=None, palette=None):
        sets = [("colour", colours)] + ([("mono", mono)] if mono else [])
        return _icons.choose_background(sets, _icons.backgrounds(palette or bakery()))

    def test_the_real_mark_sits_on_cream(self):
        # brand colour on cream is 4.75 to 1 and the dark brown 10.01 to 1 (the plan, scenario 32)
        c = self.choose([self.brand, self.brown])
        self.assertEqual((c.version, c.background), ("colour", self.cream))
        self.assertAlmostEqual(_colour.ratio(self.brand, self.cream), 4.75, delta=0.01)
        self.assertAlmostEqual(_colour.ratio(self.brown, self.cream), 10.01, delta=0.01)

    def test_the_brand_colour_as_the_background_would_hide_the_rows_so_it_is_never_a_candidate(self):
        self.assertAlmostEqual(_colour.ratio(self.brown, self.brand), 2.11, delta=0.01)
        self.assertNotIn(self.brand, _icons.backgrounds(bakery()))
        # and even offered, a mark's own colour is ratio 1 against itself and never serves
        c = _icons.choose_background([("colour", [self.brand])], [self.brand, self.cream])
        self.assertEqual(c.background, self.cream)

    def test_a_mark_with_a_cream_part_leaves_cream_and_takes_the_near_black_one(self):
        # the spike's test mark: a brand-colour circle with a cream triangle. No light background
        # serves both (the cream triangle vanishes on cream); only a near-black one does.
        c = self.choose([self.brand, self.cream])
        self.assertEqual((c.version, c.background), ("colour", "#1a120d"))
        self.assertLess(_colour.luminance("#1a120d"), 0.019881)
        # a dark background that is not dark enough is passed over for black
        p = bakery()
        p.dark["bg"] = "#4a4a5a"
        c = self.choose([self.brand, self.cream], palette=p)
        self.assertEqual(c.background, "#000000")

    def test_the_ceiling_is_the_exact_number_not_a_rounded_one(self):
        # the brand colour needs a background of relative luminance 0.019881 or less to stay at 3 to 1
        # (the plan states 0.019881 as the exact ceiling, 0.01988 rounded the wrong way)
        ceiling = (_colour.luminance(self.brand) + 0.05) / 3 - 0.05
        self.assertAlmostEqual(ceiling, 0.019881, places=6)
        over, under = "#20291f", "#202916"  # 0.019919 and 0.019509
        self.assertGreater(_colour.luminance(over), ceiling)
        self.assertLess(_colour.luminance(under), ceiling)
        for bg, serves in ((under, True), (over, False)):
            p = bakery()
            p.dark["bg"] = bg
            c = self.choose([self.brand, self.cream], palette=p)
            self.assertEqual(c.background == bg, serves, (bg, c.background))

    def test_three_to_one_is_the_line_and_is_not_rounded(self):
        for colour, serves in (("#31639e", True), ("#46676a", False)):  # 3.00025 and 2.99988 to 1 on #1a120d
            with self.subTest(colour=colour):
                try:
                    c = _icons.choose_background([("colour", [colour])], ["#1a120d"])
                    self.assertTrue(serves)
                    self.assertEqual(c.background, "#1a120d")
                except Ask:
                    self.assertFalse(serves)

    def test_where_no_background_serves_the_colour_version_the_one_colour_version_is_used(self):
        colours = ["#767676", "#cccccc", "#444444"]  # nothing serves all three, light or dark
        with self.assertRaises(Ask) as cm:
            self.choose(colours)
        self.assertEqual(cm.exception.code, "no-background")
        self.assertIn("one-colour", str(cm.exception))
        # what helps, said the right way round: the question is asked BECAUSE the colours are far apart in lightness
        for part in ("both a very light and a very dark colour", "Give the one-colour version of the mark", "whose colours are closer to one another in lightness"):
            self.assertIn(part, str(cm.exception))
        self.assertNotIn("further apart", str(cm.exception))
        with self.assertRaises(Ask) as cm:
            self.choose(colours, mono=colours)
        self.assertIn("(the one-colour version you gave does not serve either)", str(cm.exception))
        self.assertNotIn("Give the one-colour version", str(cm.exception), "she gave one: only the other way out is left")
        self.assertIn("closer to one another in lightness", str(cm.exception))
        c = self.choose(colours, mono=[self.brand])
        self.assertEqual((c.version, c.background), ("mono", self.cream))

    def test_of_the_colours_that_hardly_show_only_those_that_block_a_background_are_named(self):
        # every one of them used to be named, also one that stood in the way of nothing
        black, grey3 = "#000000", ["#767676", "#cccccc", "#444444"]
        candidates = _icons.backgrounds(bakery())
        way = lambda sets, hardly: _icons.in_the_way(sets, hardly, candidates)  # noqa: E731
        # dark brown shows and would sit on cream; cream hardly shows and vanishes on cream; black hardly shows and is plain on cream
        self.assertEqual(way([("colour", [self.brown, self.cream, black])], {"colour": [self.cream, black]}), [self.cream])
        self.assertEqual(way([("colour", [self.brown, black, self.cream])], {"colour": [black, self.cream]}), [self.cream])
        # two that both vanish on it are both named
        self.assertEqual(way([("colour", [self.brown, self.cream, "#fffdf5"])], {"colour": [self.cream, "#fffdf5"]}), [self.cream, "#fffdf5"])
        # the background is the one the colours that show would have had: of the one-colour version here, and only its own colour is named
        self.assertEqual(way([("colour", grey3 + [black]), ("mono", [self.brand, self.cream])], {"colour": [black], "mono": [self.cream]}), [self.cream])
        # a colour that hardly shows in one version and shows in the other is only left out of the first
        self.assertIsNone(way([("colour", grey3), ("mono", grey3 + [self.cream])], {"mono": [self.cream]}))
        # where the colours that show have no background either, nothing is named
        self.assertIsNone(way([("colour", grey3 + [self.cream])], {"colour": [self.cream]}))
        for sets, hardly in (([("colour", [self.brown, self.cream, black])], {"colour": [self.cream, black]}),):
            with self.assertRaises(Ask):
                _icons.choose_background(sets, candidates)  # the question is asked; in_the_way only says of what

    def test_an_answer_that_still_serves_nothing_is_not_accepted(self):
        with self.assertRaises(Ask):
            self.choose(["#767676", "#cccccc", "#444444"], mono=["#767676", "#cccccc", "#444444"])


class IcoContainer(unittest.TestCase):
    def test_a_png_inside_a_22_byte_header(self):
        png = T.make_png(32, 32, T.solid_rgba(32, 32, (1, 2, 3, 255)))
        ico = _icons.ico_from_png(png)
        self.assertEqual(ico[:6], b"\x00\x00\x01\x00\x01\x00", "reserved, type 1 (icon), one image")
        width, height, colours, reserved, planes, bpp, size, offset = struct.unpack("<BBBBHHII", ico[6:22])
        self.assertEqual((width, height, colours, reserved, planes, bpp), (32, 32, 0, 0, 1, 32))
        self.assertEqual((size, offset), (len(png), 22))
        self.assertEqual(ico[22:], png)

    def test_only_a_32_by_32_png_is_wrapped(self):
        for w, h in ((16, 16), (32, 31), (256, 256)):
            with self.assertRaises(Refusal):
                _icons.ico_from_png(T.make_png(w, h, T.solid_rgba(w, h, (1, 2, 3, 255))))
        with self.assertRaises(Refusal):
            _icons.ico_from_png(b"not a png")


class SolidPixels(unittest.TestCase):
    """Which colour a solid pixel is counted for. The renderer may land a shade off the colour the file
    names, so a pixel within 3 of a colour counts for it: for one colour, never for two."""

    def picture(self, *pixels):
        return _png.decode(T.make_png(len(pixels), 1, [b"".join(bytes(p) for p in pixels)]))

    def test_a_pixel_between_two_near_colours_counts_for_the_nearer_one_only(self):
        pic = self.picture(*[(3, 3, 3, 255)] * 5)
        self.assertEqual(_icons._solid(pic, ["#000000", "#030303"]), {"#000000": 0, "#030303": 5},
                         "five pixels of #030303 are not also five pixels of #000000")
        self.assertEqual(_icons._solid(pic, ["#030303", "#000000"]), {"#030303": 5, "#000000": 0}, "whichever is listed first")
        pic = self.picture((1, 1, 1, 255), (2, 2, 2, 255), (0, 0, 0, 255), (3, 3, 3, 255))
        self.assertEqual(_icons._solid(pic, ["#000000", "#030303"]), {"#000000": 2, "#030303": 2})

    def test_a_pixel_as_near_to_one_as_to_the_other_goes_to_the_first_listed_and_is_counted_once(self):
        pic = self.picture(*[(2, 2, 2, 255)] * 4)
        counts = _icons._solid(pic, ["#000000", "#040404"])
        self.assertEqual(counts, {"#000000": 4, "#040404": 0})
        self.assertEqual(sum(counts.values()), 4)

    def test_a_pixel_near_no_colour_or_not_solid_counts_for_none(self):
        pic = self.picture((9, 9, 9, 255), (0, 0, 0, 249), (0, 0, 4, 255), (0, 0, 0, 250))
        self.assertEqual(_icons._solid(pic, ["#000000"]), {"#000000": 1})

    def test_a_colour_on_its_own_is_counted_as_before(self):
        pic = self.picture((0xb4, 0x53, 0x1a, 255), (0xb5, 0x52, 0x1c, 255), (0xb8, 0x53, 0x1a, 255))
        self.assertEqual(_icons._solid(pic, ["#b4531a"]), {"#b4531a": _png.count_colour(pic, "#b4531a", tolerance=3)})
        self.assertEqual(_icons._solid(pic, ["#b4531a"]), {"#b4531a": 2})


class WithTheSitesSharp(unittest.TestCase):
    def setUp(self):
        T.require_sharp(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.site = T.make_site(os.path.join(self.tmp.name), T.node_modules_dir())
        self.work = os.path.join(self.tmp.name, "work")
        self.renderer = _render.Renderer(self.site)

    def build(self, data=None, mono=None, palette=None, **kw):
        clean = _svg.clean_svg(data or T.real_svg(T.REAL_COLOUR))
        mono_clean = _svg.clean_svg(mono) if mono else None
        return clean, _icons.build(clean, mono_clean, palette or bakery(), self.renderer, self.work, **kw)


class TheSevenFiles(WithTheSitesSharp):
    PATHS = ["public/favicon.svg", "public/favicon.ico", "public/apple-touch-icon.png", "public/icon-192.png",
             "public/icon-512.png", "public/icon-maskable-512.png", "public/images/logo.png"]

    def test_scenario_11_the_seven_files_at_the_sizes_the_site_links_and_declares(self):
        clean, icons = self.build()
        self.assertEqual(sorted(icons.files), sorted(self.PATHS))
        sizes = {p: _png.size(icons.files[p]) for p in self.PATHS if p.endswith(".png")}
        self.assertEqual(sizes, {"public/apple-touch-icon.png": (180, 180), "public/icon-192.png": (192, 192),
                                 "public/icon-512.png": (512, 512), "public/icon-maskable-512.png": (512, 512),
                                 "public/images/logo.png": (512, 512)})
        self.assertEqual(icons.files["public/favicon.svg"], clean.text.encode("utf-8"))

    def test_the_manifest_sizes_are_what_the_starters_manifest_declares(self):
        import json
        manifest = json.loads(T.starter_file("public/manifest.webmanifest"))
        declared = {i["src"].lstrip("/"): i["sizes"] for i in manifest["icons"]}
        _clean, icons = self.build()
        for src, sizes in declared.items():
            with self.subTest(src=src):
                w, h = (int(n) for n in sizes.split("x"))
                self.assertEqual(_png.size(icons.files["public/" + src]), (w, h))

    def test_the_favicon_ico_holds_a_32_pixel_picture_that_is_not_blank(self):
        _clean, icons = self.build()
        ico = icons.files["public/favicon.ico"]
        png = ico[22:]
        self.assertEqual(_png.size(png), (32, 32))
        self.assertFalse(_png.is_blank(_png.decode(png)))

    def test_apple_touch_is_opaque_with_no_alpha_channel_and_so_is_the_maskable_one(self):
        _clean, icons = self.build()
        for p in ("public/apple-touch-icon.png", "public/icon-maskable-512.png"):
            with self.subTest(p=p):
                data = icons.files[p]
                self.assertEqual(data[25], 2)
                self.assertTrue(_png.is_opaque(_png.decode(data)))
                self.assertEqual(_png.at(_png.decode(data), 0, 0), (0xff, 0xf8, 0xee, 255))

    def test_the_icons_that_may_be_see_through_are(self):
        _clean, icons = self.build()
        for p in ("public/icon-192.png", "public/icon-512.png", "public/images/logo.png"):
            with self.subTest(p=p):
                self.assertEqual(_png.at(_png.decode(icons.files[p]), 0, 0)[3], 0)

    def test_the_marks_colours_are_in_the_big_icons_exactly(self):
        _clean, icons = self.build()
        pic = _png.decode(icons.files["public/icon-512.png"])
        self.assertGreater(_png.count_colour(pic, "#b4531a"), 5000)
        self.assertGreater(_png.count_colour(pic, "#6b2c0b"), 2000)

    def test_the_maskable_icon_keeps_the_whole_mark_inside_the_safe_circle(self):
        # radius 40% of the icon (Web Application Manifest, "Icon masks and safe zone"). A mark that
        # fills its viewBox has its corners at 0.396: inside by construction, whatever it looks like.
        full = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#123456"/></svg>').encode()
        for data in (T.real_svg(T.REAL_COLOUR), full):
            _clean, icons = self.build(data)
            w, h, rgba = _png.decode(icons.files["public/icon-maskable-512.png"])
            bg = _png.at((w, h, rgba), 0, 0)
            far = 0.0
            for y in range(h):
                for x in range(0, w):
                    i = (y * w + x) * 4
                    if abs(rgba[i] - bg[0]) + abs(rgba[i + 1] - bg[1]) + abs(rgba[i + 2] - bg[2]) > 24:
                        far = max(far, ((x + 0.5 - w / 2) ** 2 + (y + 0.5 - h / 2) ** 2) ** 0.5)
            self.assertGreater(far, 0.2 * 512, "the mark is there")
            self.assertLessEqual(far, 0.4 * 512 + 1, "and it stays inside the circle")

    def test_scenario_32_the_real_marks_rows_do_not_vanish_on_the_maskable_background(self):
        _clean, icons = self.build()
        self.assertEqual((icons.version, icons.background), ("colour", "#fff8ee"))
        pic = _png.decode(icons.files["public/icon-maskable-512.png"])
        self.assertGreater(_png.count_colour(pic, "#6b2c0b"), 2000, "the dark rows are there")
        self.assertGreater(_png.count_colour(pic, "#b4531a"), 5000, "and so is the loaf")

    def test_scenario_32_a_mark_with_a_cream_part_gets_the_dark_background_and_keeps_both_colours(self):
        circle_and_triangle = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="28" fill="#b4531a"/>'
                               b'<path d="M32 14 50 46H14z" fill="#fff8ee"/></svg>')
        _clean, icons = self.build(circle_and_triangle)
        self.assertEqual((icons.version, icons.background), ("colour", "#1a120d"))
        pic = _png.decode(icons.files["public/icon-maskable-512.png"])
        self.assertGreater(_png.count_colour(pic, "#b4531a"), 3000)
        self.assertGreater(_png.count_colour(pic, "#fff8ee"), 1000)
        self.assertEqual(_png.at(pic, 0, 0)[:3], (0x1a, 0x12, 0x0d))

    def test_scenario_32_with_nothing_that_serves_the_one_colour_version_is_drawn_and_she_is_told(self):
        grey3 = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="20" fill="#767676"/>'
                 b'<rect y="22" width="64" height="20" fill="#cccccc"/><rect y="44" width="64" height="20" fill="#444444"/></svg>')
        with self.assertRaises(Ask) as cm:
            self.build(grey3)
        self.assertEqual(cm.exception.code, "no-background")
        _clean, icons = self.build(grey3, mono=T.real_svg(T.REAL_MONO))
        self.assertEqual((icons.version, icons.background), ("mono", "#fff8ee"))
        self.assertTrue([n for n in icons.notes if "one-colour" in n])
        pic = _png.decode(icons.files["public/icon-maskable-512.png"])
        self.assertGreater(_png.count_colour(pic, "#b4531a"), 5000)
        # the big see-through icons and the favicon are still the colour version
        self.assertGreater(_png.count_colour(_png.decode(icons.files["public/icon-512.png"]), "#767676"), 1000)

    def test_the_apple_touch_icon_leaves_the_mark_a_margin_and_the_maskable_one_a_wider_one(self):
        full = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#123456"/></svg>'
        _clean, icons = self.build(full)

        def side(path):
            w, h, rgba = _png.decode(icons.files[path])
            xs = [i // 4 % w for i in range(0, len(rgba), 4) if rgba[i + 2] == 0x56 and rgba[i] == 0x12]
            return max(xs) - min(xs) + 1

        self.assertAlmostEqual(side("public/apple-touch-icon.png"), 0.8 * 180, delta=2)
        self.assertAlmostEqual(side("public/icon-maskable-512.png"), 0.56 * 512, delta=2)
        self.assertAlmostEqual(side("public/icon-512.png"), 512, delta=1)

    def test_a_wide_mark_is_padded_to_a_square_logo_with_its_proportions_kept(self):
        wide = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"><rect width="100" height="40" fill="#123456"/></svg>'
        _clean, icons = self.build(wide)
        w, h, rgba = _png.decode(icons.files["public/images/logo.png"])
        self.assertEqual((w, h), (512, 512))
        ys = [i // 4 // w for i in range(3, len(rgba), 4) if rgba[i] > 128]
        self.assertAlmostEqual(max(ys) - min(ys) + 1, 205, delta=2)


class LyingRenderer(object):
    """A renderer that hands back what it likes: the checks on what it made must not take its word."""

    def __init__(self, real, wrong):
        self.real, self.wrong = real, wrong

    def render(self, svg, view_box, jobs, out_dir):
        res = self.real.render(svg, view_box, jobs, out_dir)
        for job in jobs:
            self.wrong(job, os.path.join(out_dir, job["file"]))
        return res


class WhatIsMadeIsLookedAt(WithTheSitesSharp):
    def lie(self, wrong):
        clean = _svg.clean_svg(T.real_svg(T.REAL_COLOUR))
        return _icons.build(clean, None, bakery(), LyingRenderer(self.renderer, wrong), self.work)

    def test_a_picture_of_the_wrong_size_is_not_installed(self):
        def wrong(job, path):
            if job["name"] == "icon-192":
                with open(path, "wb") as f:
                    f.write(T.make_png(191, 192, T.solid_rgba(191, 192, (1, 2, 3, 255))))
        with self.assertRaises(Refusal) as cm:
            self.lie(wrong)
        self.assertEqual(cm.exception.code, "icon-bad")
        self.assertIn("icon-192", str(cm.exception))

    def test_an_icon_whose_file_stops_after_its_header_is_not_installed(self):
        # the header alone says 192 x 192 (or 512 x 512, which is images/logo.png too): the size check passes on it
        for name in ("icon-192", "icon-512", "apple-touch", "maskable", "favicon-32"):
            for what, keep in (("the header and nothing else", lambda data: data[:33]), ("its end cut off", lambda data: data[:-20])):
                with self.subTest(name=name, what=what):
                    def wrong(job, path, name=name, keep=keep):
                        if job["name"] == name:
                            data = T.read_bytes(path)
                            with open(path, "wb") as f:
                                f.write(keep(data))
                    with self.assertRaises(Refusal) as cm:
                        self.lie(wrong)
                    self.assertEqual(cm.exception.code, "png-bad")

    def test_a_blank_32_pixel_icon_is_not_installed(self):
        def wrong(job, path):
            if job["name"] == "favicon-32":
                with open(path, "wb") as f:
                    f.write(T.make_png(32, 32, T.solid_rgba(32, 32, (0, 0, 0, 0))))
        with self.assertRaises(Refusal) as cm:
            self.lie(wrong)
        self.assertEqual(cm.exception.code, "blank-render")

    def test_an_app_icon_that_is_not_opaque_is_not_installed(self):
        for name in ("apple-touch", "maskable"):
            with self.subTest(name=name):
                size = 180 if name == "apple-touch" else 512

                def wrong(job, path, name=name, size=size):
                    if job["name"] == name:
                        with open(path, "wb") as f:
                            f.write(T.make_png(size, size, T.solid_rgba(size, size, (1, 2, 3, 254))))
                with self.assertRaises(Refusal) as cm:
                    self.lie(wrong)
                self.assertEqual(cm.exception.code, "icon-bad")
                self.assertIn(name, str(cm.exception))


class WhatTheRenderShows(WithTheSitesSharp):
    def test_a_colour_painted_but_hardly_showing_is_named_in_a_note_and_still_counted_in_the_checks(self):
        # It may be covered (as here) or only too thin to leave a solid pixel at the probe's size, and the
        # picture cannot tell the two apart: so it stays in what the palette check is handed, and she is told.
        covered = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#aa0000"/>'
                   b'<rect width="64" height="64" fill="#b4531a"/></svg>')
        clean, icons = self.build(covered)
        self.assertEqual(clean.colours, ["#aa0000", "#b4531a"], "the file paints with both")
        self.assertEqual(icons.visible, ["#aa0000", "#b4531a"])
        note = [n for n in icons.notes if "#aa0000" in n]
        self.assertEqual(len(note), 1)
        for part in ("hardly shows", "covered", "too thin", "outside the box", "still count"):
            self.assertIn(part, note[0])
        self.assertFalse([n for n in icons.notes if "#b4531a" in n], "the colour that shows gets no note")

    def test_a_shape_wholly_covered_by_one_a_shade_away_is_not_taken_for_showing(self):
        # every pixel is the top shape's #030303, within the tolerance of the covered #000000 as well
        for under, over in (("#000000", "#030303"), ("#030303", "#000000"), ("#b4531a", "#b5541b")):
            with self.subTest(under=under, over=over):
                data = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="%s"/>'
                        '<rect width="64" height="64" fill="%s"/></svg>' % (under, over)).encode()
                _clean, icons = self.build(data)
                self.assertTrue([n for n in icons.notes if under in n and "hardly shows" in n], icons.notes)
                self.assertFalse([n for n in icons.notes if over in n and "hardly shows" in n], icons.notes)

    def test_a_hairline_too_thin_to_leave_solid_pixels_still_keeps_its_own_colour_from_being_the_background(self):
        # the cream line is under a pixel wide at the probe's size: no solid pixel of it, and it is there all the same.
        # Left out of the choice, the first candidate (the light background, cream) hid it in both app icons.
        hairline = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#b4531a"/>'
                    b'<path d="M0 32H64" stroke="#fff8ee" stroke-width="0.2" fill="none"/></svg>')
        _clean, icons = self.build(hairline)
        self.assertTrue([n for n in icons.notes if "#fff8ee" in n and "hardly shows" in n], icons.notes)
        self.assertNotEqual(icons.background, "#fff8ee")
        self.assertEqual((icons.version, icons.background), ("colour", "#1a120d"))
        for c in ("#b4531a", "#fff8ee"):
            self.assertGreaterEqual(_colour.ratio(c, icons.background), 3.0)
        self.assertEqual(icons.visible, ["#b4531a", "#fff8ee"], "and the palette check is handed the hairline's colour too")

    def test_where_only_a_colour_that_hardly_shows_stands_in_the_way_of_a_background_she_is_asked_and_told_which(self):
        # dark brown has a background (cream), cream has one (near black), the two together have none
        for name, extra in (("a hairline", '<path d="M0 32H64" stroke="#fff8ee" stroke-width="0.2" fill="none"/>'),
                            ("outside the box", '<rect x="100" y="100" width="9" height="9" fill="#fff8ee"/>'),
                            ("covered", "")):
            with self.subTest(name=name):
                body = '<rect width="64" height="64" fill="#6b2c0b"/>' + extra
                if name == "covered":
                    body = '<rect width="64" height="64" fill="#fff8ee"/>' + body
                with self.assertRaises(Ask) as cm:
                    self.build(('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">%s</svg>' % body).encode())
                self.assertEqual(cm.exception.code, "no-background")
                self.assertIn("#fff8ee", str(cm.exception))
                self.assertIn("hardly shows", str(cm.exception))
        # a second colour that hardly shows and stands in the way of no background is not named with it
        body = ('<rect width="64" height="64" fill="#6b2c0b"/><rect x="100" y="100" width="9" height="9" fill="#fff8ee"/>'
                '<rect x="120" y="100" width="9" height="9" fill="#000000"/>')
        with self.assertRaises(Ask) as cm:
            self.build(('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">%s</svg>' % body).encode())
        self.assertIn("What stands in the way is #fff8ee: the file paints with it, although it hardly shows when the mark is drawn", str(cm.exception))
        self.assertNotIn("#000000", str(cm.exception))
        self.assertIn("A version of that file without it would do too.", str(cm.exception))
        # two colours that both stand in the way are "them", and with a one-colour version in play the file is named
        body = ('<rect width="64" height="64" fill="#6b2c0b"/><rect x="100" y="100" width="9" height="9" fill="#fff8ee"/>'
                '<rect x="120" y="100" width="9" height="9" fill="#fffdf5"/>')
        two = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">%s</svg>' % body).encode()
        with self.assertRaises(Ask) as cm:
            self.build(two)
        self.assertIn("What stands in the way is #fff8ee and #fffdf5: the file paints with them, although they hardly show when the mark is drawn", str(cm.exception))
        self.assertIn("A version of that file without them would do too.", str(cm.exception))
        grey3 = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="20" fill="#767676"/>'
                 b'<rect y="22" width="64" height="20" fill="#cccccc"/><rect y="44" width="64" height="20" fill="#444444"/></svg>')
        for colour, mono, where in ((two, grey3, "the colour file paints with them"), (grey3, two, "the one-colour file paints with them")):
            with self.assertRaises(Ask) as cm:
                self.build(colour, mono=mono)
            self.assertIn("What stands in the way is #fff8ee and #fffdf5: " + where, str(cm.exception))
        # where the colours that show have no background either, nothing is blamed on a colour that hardly shows
        grey3 = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="20" fill="#767676"/>'
                 b'<rect y="22" width="64" height="20" fill="#cccccc"/><rect y="44" width="64" height="20" fill="#444444"/>'
                 b'<rect x="100" y="100" width="9" height="9" fill="#fff8ee"/></svg>')
        with self.assertRaises(Ask) as cm:
            self.build(grey3)
        self.assertNotIn("hardly shows", str(cm.exception))

    def test_a_mark_that_paints_but_draws_nothing_on_the_canvas_is_refused(self):
        # painted as far as the file says, but outside the box: the render is blank (scenario 17)
        off = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect x="100" y="100" width="20" height="20" fill="#b4531a"/></svg>'
        with self.assertRaises(Refusal) as cm:
            self.build(off)
        self.assertEqual(cm.exception.code, "blank-render")
        self.assertIn("nothing", str(cm.exception).lower())

    def test_a_mark_too_thin_to_leave_a_single_solid_pixel_is_refused_too(self):
        thin = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><path d="M0 32H64" stroke="#b4531a" stroke-width="0.01" fill="none"/></svg>'
        with self.assertRaises(Refusal) as cm:
            self.build(thin)
        self.assertEqual(cm.exception.code, "blank-render")

    def test_a_blank_one_colour_version_is_named_as_the_file_that_was_blank(self):
        off = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect x="100" y="100" width="20" height="20" fill="#b4531a"/></svg>'
        with self.assertRaises(Refusal) as cm:
            self.build(mono=off)
        self.assertEqual(cm.exception.code, "blank-render")
        self.assertIn("one-colour version", str(cm.exception))
        # and a blank colour version is not blamed on a one-colour file, given or not
        for mono in (None, T.real_svg(T.REAL_MONO)):
            with self.assertRaises(Refusal) as cm:
                self.build(off, mono=mono)
            self.assertEqual(cm.exception.code, "blank-render")
            self.assertNotIn("one-colour", str(cm.exception))
            self.assertTrue(str(cm.exception).startswith("The mark is blank"))


class WhatThePaletteCheckIsHanded(WithTheSitesSharp):
    """`visible` is what the intake checks against the palette: it must hold the colours of every
    version that ends up in a file, the one-colour version's too when the app icons are drawn from it."""

    GREY3 = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="20" fill="#767676"/>'
             b'<rect y="22" width="64" height="20" fill="#cccccc"/><rect y="44" width="64" height="20" fill="#444444"/></svg>')
    PURPLE = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#5b2d8e"/></svg>'

    def test_the_one_colour_versions_colours_are_handed_over_when_the_app_icons_are_drawn_from_it(self):
        _clean, icons = self.build(self.GREY3, mono=self.PURPLE)
        self.assertEqual(icons.version, "mono")
        self.assertGreater(_png.count_colour(_png.decode(icons.files["public/icon-maskable-512.png"]), "#5b2d8e"), 5000, "it is in a file")
        self.assertEqual(icons.visible, ["#767676", "#cccccc", "#444444", "#5b2d8e"])
        report = _palette.check_mark(icons.visible, bakery())
        self.assertIn("#5b2d8e", report.outside, "a purple the palette does not hold is asked about, not installed unseen")

    def test_a_colour_both_versions_share_is_handed_over_once(self):
        _clean, icons = self.build(self.GREY3, mono=self.GREY3.replace(b"#cccccc", b"#767676").replace(b"#444444", b"#767676"))
        self.assertEqual(icons.version, "mono")
        self.assertEqual(icons.visible, ["#767676", "#cccccc", "#444444"])

    def test_a_one_colour_version_that_is_given_but_not_drawn_into_any_file_is_not_handed_over(self):
        _clean, icons = self.build(mono=self.PURPLE)
        self.assertEqual(icons.version, "colour")
        self.assertEqual(icons.visible, ["#b4531a", "#6b2c0b"])


class ThePreview(WithTheSitesSharp):
    def test_sixteen_and_thirty_two_pixels_on_the_light_and_the_dark_background_and_magnified(self):
        clean = _svg.clean_svg(T.real_svg(T.REAL_COLOUR))
        data = _icons.preview(clean.text, clean.view_box, bakery(), self.renderer, self.work)
        w, h, rgba = _png.decode(data)
        self.assertEqual((w, h), (2 * _icons.PANEL_W, _icons.PANEL_H))
        self.assertEqual(_png.at((w, h, rgba), 2, 2), (0xff, 0xf8, 0xee, 255), "the left panel is the light theme's background")
        self.assertEqual(_png.at((w, h, rgba), _icons.PANEL_W + 2, 2), (0x1a, 0x12, 0x0d, 255), "the right one the dark theme's")
        # what the renderer draws at 16 and 32 px, composited by hand, is what is in the sheet at actual size
        self.renderer.render(clean.text, clean.view_box, [{"name": "a", "file": "a.png", "size": 16, "scale": 1.0, "background": None},
                                                          {"name": "b", "file": "b.png", "size": 32, "scale": 1.0, "background": None}], self.work)
        for size, name, (x0, y0) in ((16, "a", _icons.AT_16), (32, "b", _icons.AT_32)):
            with open(os.path.join(self.work, name + ".png"), "rb") as f:
                pic = _png.decode(f.read())
            for (px, py) in ((size // 2, size // 2), (size // 4, size // 2), (size // 2, size // 4)):
                r, g, b, a = _png.at(pic, px, py)
                for panel, bg in ((0, (0xff, 0xf8, 0xee)), (_icons.PANEL_W, (0x1a, 0x12, 0x0d))):
                    want = tuple((c * a + k * (255 - a) + 127) // 255 for c, k in zip((r, g, b), bg))
                    got = _png.at((w, h, rgba), panel + x0 + px, y0 + py)[:3]
                    self.assertTrue(all(abs(g_ - w_) <= 1 for g_, w_ in zip(got, want)), (size, px, py, got, want))

    def test_the_magnified_ones_are_the_actual_pixels_blown_up_not_smoothed(self):
        clean = _svg.clean_svg(T.real_svg(T.REAL_COLOUR))
        w, h, rgba = _png.decode(_icons.preview(clean.text, clean.view_box, bakery(), self.renderer, self.work))
        pic = (w, h, rgba)
        for (ax, ay), (mx, my), size in ((_icons.AT_16, _icons.BIG_16, 16), (_icons.AT_32, _icons.BIG_32, 32)):
            for py in range(size):
                for px in range(size):
                    want = _png.at(pic, ax + px, ay + py)
                    for dy, dx in ((0, 0), (7, 7), (3, 5), (0, 7), (7, 0)):
                        self.assertEqual(_png.at(pic, mx + px * 8 + dx, my + py * 8 + dy), want, (size, px, py, dx, dy))

    def test_a_preview_picture_of_the_wrong_size_is_refused_not_pasted_into_the_sheet(self):
        clean = _svg.clean_svg(T.real_svg(T.REAL_COLOUR))
        # too large for its place it used to end in a ValueError; too small, in a sheet with a hole in it
        for name, size, side in (("preview-32", 64, 32), ("preview-16", 8, 16), ("preview-16", 32, 16), ("preview-32", 16, 32)):
            with self.subTest(name=name, size=size):
                def wrong(job, path, name=name, size=size):
                    if job["name"] == name:
                        with open(path, "wb") as f:
                            f.write(T.make_png(size, size, T.solid_rgba(size, size, (1, 2, 3, 255))))
                with self.assertRaises(Refusal) as cm:
                    _icons.preview(clean.text, clean.view_box, bakery(), LyingRenderer(self.renderer, wrong), self.work)
                self.assertEqual(cm.exception.code, "icon-bad")
                self.assertIn("%d x %d" % (side, side), str(cm.exception))
        with self.assertRaises(Refusal) as cm:  # not square either
            def wide(job, path):
                if job["name"] == "preview-16":
                    with open(path, "wb") as f:
                        f.write(T.make_png(16, 15, T.solid_rgba(16, 15, (1, 2, 3, 255))))
            _icons.preview(clean.text, clean.view_box, bakery(), LyingRenderer(self.renderer, wide), self.work)
        self.assertEqual(cm.exception.code, "icon-bad")

    def test_a_theme_without_a_background_gets_no_panel(self):
        clean = _svg.clean_svg(T.real_svg(T.REAL_COLOUR))
        p = bakery()
        del p.dark["bg"]
        w, h, _ = _png.decode(_icons.preview(clean.text, clean.view_box, p, self.renderer, self.work))
        self.assertEqual((w, h), (_icons.PANEL_W, _icons.PANEL_H))
        with self.assertRaises(Refusal):
            _icons.preview(clean.text, clean.view_box, _palette.Palette(), self.renderer, self.work)

    def test_the_sheet_is_the_installed_mark_so_it_is_not_blank_and_not_just_background(self):
        clean = _svg.clean_svg(T.real_svg(T.REAL_COLOUR))
        pic = _png.decode(_icons.preview(clean.text, clean.view_box, bakery(), self.renderer, self.work))
        self.assertGreater(_png.count_colour(pic, "#b4531a"), 1000)
        self.assertGreater(_png.count_colour(pic, "#6b2c0b"), 300)


if __name__ == "__main__":
    unittest.main()
