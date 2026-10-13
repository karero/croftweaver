"""Scenario 10: a colour arrives as #FFF, rgb(255, 255, 255), a colour name, hsl() or oklch(), and
every one of them is read as the same six-digit hex by ONE helper (the contrast check and the
mark's own colours both use it). What it cannot resolve (alpha, a gradient, a format it does not
know) is refused by name, never guessed.

Also the contrast arithmetic itself, because every other check stands on it.
"""

import os
import unittest

import _testutil as T  # noqa: F401  (puts the scripts folder on the path)
import _colour
from _refusal import Refusal


def refused(testcase, text, code, **kw):
    with testcase.assertRaises(Refusal) as cm:
        _colour.parse_colour(text, **kw)
    testcase.assertEqual(cm.exception.code, code, "%r refused for %r: %s" % (text, cm.exception.code, cm.exception))
    testcase.assertIn(text.strip()[:12], str(cm.exception), "a refusal names the colour it could not read")


def _unreadable_message(text):
    try:
        _colour.parse_colour(text)
    except Refusal as e:
        return str(e)
    return ""


class Formats(unittest.TestCase):
    def test_the_same_colour_in_every_format_is_the_same_hex(self):
        white = ["#FFF", "#fff", "#FFFFFF", "#ffffff", "rgb(255, 255, 255)", "rgb(255 255 255)", "rgb(100%, 100%, 100%)",
                 "RGB(255,255,255)", "white", "WHITE", "hsl(0, 0%, 100%)", "hsl(200 50% 100%)", "oklch(1 0 0)",
                 "oklch(100% 0 0)", "rgba(255, 255, 255, 1)", "rgb(255 255 255 / 1)", "rgb(255 255 255 / 100%)", "#ffffffff",
                 "  white  ", "hsl(0deg 0% 100%)", "hsl(0turn 0% 100%)"]
        for text in white:
            with self.subTest(text=text):
                self.assertEqual(_colour.parse_colour(text), "#ffffff")

    def test_each_format_against_known_values(self):
        known = {
            "#abc": "#aabbcc", "#ABCDEF": "#abcdef", "rgb(10, 20, 30)": "#0a141e", "rgb(100%, 0%, 0%)": "#ff0000",
            "rgb(127.5 0 0)": "#800000", "rgb(126.5 0 0)": "#7f0000",  # a half rounds up, never to even
            "rgb(300, -5, 0)": "#ff0000",  # CSS clamps
            "tomato": "#ff6347", "rebeccapurple": "#663399", "cornflowerblue": "#6495ed", "gray": "#808080", "grey": "#808080",
            "lightgoldenrodyellow": "#fafad2", "black": "#000000", "red": "#ff0000",
            "hsl(0, 100%, 50%)": "#ff0000", "hsl(120, 100%, 25%)": "#008000", "hsl(240 100% 50%)": "#0000ff",
            "hsl(210, 50%, 50%)": "#4080bf", "hsl(60 100% 50%)": "#ffff00", "hsl(-120 100% 50%)": "#0000ff", "hsl(480 100% 50%)": "#00ff00",
            "hsl(0.5turn 100% 50%)": "#00ffff", "hsl(3.14159rad 100% 50%)": "#00ffff", "hsl(200grad 100% 50%)": "#00ffff",
            # the three sRGB primaries, as CSS Color 4 gives them in oklch
            "oklch(0.6279553606145516 0.25768330773615683 29.2338851923426)": "#ff0000",
            "oklch(62.79553606145516% 0.25768330773615683 29.2338851923426)": "#ff0000",
            "oklch(0.8664396115356694 0.2948272403370167 142.49533888780996)": "#00ff00",
            "oklch(0.4520137183853429 0.31321437166460125 264.052020638055)": "#0000ff",
            "oklch(0 0 0)": "#000000", "oklch(0 0 0 / 1)": "#000000",
            # mid-tones, worked out another way (OKLab to XYZ to sRGB, with the CSS Color 4 matrices)
            "oklch(0.7 0.1 150)": "#6fb07d", "oklch(0.5 0.15 30)": "#a8372a", "oklch(0.9 0.05 250)": "#c6e1ff",
            "oklch(0.6 50% 30)": "#de3e2d",  # 50% chroma is 0.2
        }
        for text, want in known.items():
            with self.subTest(text=text):
                self.assertEqual(_colour.parse_colour(text), want)

    def test_oklch_grey_ramp_stays_grey(self):
        for L in (0.1, 0.3, 0.5, 0.7, 0.9):
            with self.subTest(L=L):
                h = _colour.parse_colour("oklch(%s 0 0)" % L)
                self.assertEqual(h[1:3], h[3:5])
                self.assertEqual(h[3:5], h[5:7])

    def test_current_colour_is_the_one_the_caller_supplies(self):
        self.assertEqual(_colour.parse_colour("currentColor", current="#123456"), "#123456")
        self.assertEqual(_colour.parse_colour("CURRENTCOLOR", current="#123456"), "#123456")
        refused(self, "currentColor", "colour-current")

    def test_every_css_colour_name_matches_a_second_source(self):
        try:
            from PIL import ImageColor
        except ImportError:
            if os.environ.get("REQUIRE_SHARP"):
                self.fail("REQUIRE_SHARP is set but Pillow is not installed for the Python that runs these tests")
            self.skipTest("Pillow is not installed here (the CI job installs it for the share-card test)")
        names = {n: c for n, c in ImageColor.colormap.items() if c.startswith("#") and len(c) == 7}
        self.assertGreaterEqual(len(names), 140)
        for name, hexv in names.items():
            if name == "rebeccapurple" and hexv != "#663399":
                continue
            with self.subTest(name=name):
                self.assertEqual(_colour.parse_colour(name), hexv)


class Refused(unittest.TestCase):
    def test_alpha_in_any_spelling(self):
        for text in ("rgba(0, 0, 0, 0.5)", "rgb(0 0 0 / 50%)", "hsla(0, 100%, 50%, 0.3)", "hsl(0 100% 50% / .3)",
                     "#0000007f", "#000a", "oklch(0.5 0.1 100 / 0.5)", "transparent", "rgba(0,0,0,0)"):
            with self.subTest(text=text):
                refused(self, text, "colour-alpha")

    def test_what_it_does_not_know_is_named_not_guessed(self):
        for text in ("notacolour", "rgb(1, 2)", "rgb(a, b, c)", "#12", "#12345", "#ggg", "color(display-p3 1 0 0)",
                     "lab(50% 40 59)", "hwb(0 0% 0%)", "var(--brand)", "calc(1 + 2)", "", "rgb(1,2,3", "1 2 3", "oklch(0.5, 0.1, 100)"):
            with self.subTest(text=text):
                with self.assertRaises(Refusal) as cm:
                    _colour.parse_colour(text)
                self.assertEqual(cm.exception.code, "colour-unreadable")

    def test_a_gradient_or_pattern_is_named_as_one(self):
        for text in ("url(#g)", "url(#paint0_linear)", "URL( '#p' )"):
            with self.subTest(text=text):
                with self.assertRaises(Refusal) as cm:
                    _colour.parse_colour(text)
                self.assertEqual(cm.exception.code, "colour-gradient")
                self.assertIn("flat", str(cm.exception))

    def test_oklch_outside_the_screen_colours_is_refused_not_clipped(self):
        # chroma 0.4 at this hue has no sRGB equivalent: the hex would not be what the owner saw
        refused(self, "oklch(0.7 0.4 150)", "colour-gamut")

    def test_an_rgb_that_mixes_percentages_and_plain_numbers_is_refused(self):
        # the site's renderer draws black for these, so the hex this check would give is not what shows
        for text in ("rgb(50%,0,0)", "rgb(255,0%,0)", "rgb(100% 0 0)", "rgba(0, 50%, 0, 1)"):
            with self.subTest(text=text):
                refused(self, text, "colour-unreadable")
        self.assertEqual(_colour.parse_colour("rgb(100%, 0%, 0%)"), "#ff0000")
        self.assertEqual(_colour.parse_colour("rgb(255, 0, 0)"), "#ff0000")

    def test_a_point_with_no_digit_after_it_is_not_a_number(self):
        for text in ("rgb(255.,0,0)", "hsl(120. 50% 50%)", "oklch(0.5 0.1 30.)", "rgb(1.e2,0,0)"):
            with self.subTest(text=text):
                refused(self, text, "colour-unreadable")
        self.assertEqual(_colour.parse_colour("rgb(255.0, 0, 0)"), "#ff0000")
        self.assertEqual(_colour.parse_colour("rgb(.5, 0, 0)"), _colour.parse_colour("rgb(0.5, 0, 0)"))

    def test_digits_and_letters_of_another_script_are_not_read_as_plain_ones(self):
        # \d took any script's digits and float() read them: rgb(١٢٣,0,0) was #7b0000, a colour nobody can see in the file.
        # The Kelvin sign lower-cases to a plain k, so "blac" + that sign was black.
        for text in ("rgb(١٢٣,0,0)", "rgb(１２, 0, 0)", "rgb(1२3 0 0)", "hsl(٢٤٠ 30% 12%)", "hsl(240 ３0% 12%)", "oklch(0.5 0.0٤ 280)", "rgb(1 2 3 / ١)", "rgb(1e१ 0 0)",
                     "rgb(1e٢ 0 0)", "blac\u212a", "dar\u212ablue", "#١٢٣٤٥٦", "#１２３", "ＲＧＢ(1,2,3)", "réd"):
            with self.subTest(text=text):
                refused(self, text, "colour-unreadable")
        for text in ("rgb(1,\u00a02,3)", "rgb(1,2,3)\u200b", "#7b\u200b0000"):  # a space that is no plain space, inside the colour or stuck to it
            with self.subTest(text=text):
                with self.assertRaises(Refusal) as cm:
                    _colour.parse_colour(text)
                self.assertEqual(cm.exception.code, "colour-unreadable")
        self.assertIn("not a plain one", _unreadable_message("rgb(١٢٣,0,0)"))
        # the same in plain digits and letters is read, as before
        self.assertEqual(_colour.parse_colour("rgb(123,0,0)"), "#7b0000")
        self.assertEqual(_colour.parse_colour("BLACK"), "#000000")
        self.assertEqual(_colour.parse_colour("\u00a0#7b0000\u2003"), "#7b0000", "a space of any kind around the colour is only a space")

    def test_nan_and_infinity_are_not_numbers(self):
        for text in ("rgb(nan, 0, 0)", "hsl(inf 50% 50%)", "oklch(nan 0 0)"):
            with self.subTest(text=text):
                with self.assertRaises(Refusal):
                    _colour.parse_colour(text)

    def test_an_exponent_has_one_or_two_digits_and_more_is_no_number(self):
        # the site's renderer does not take 0e309 for a number and draws black; these once overflowed the arithmetic too
        for text in ("rgb(0e309,0,0)", "rgb(1e100, 0, 0)", "hsl(1e308turn 50% 50%)", "hsl(1e308rad 50% 50%)", "hsla(1e307turn, 50%, 50%, 1)", "rgb(1e308% 0% 0%)",
                     "rgba(0%, 0%, 1e307%, 1)", "oklch(0.5 0.1 1e308turn)", "oklch(0.5 1e308 0)", "oklch(1e200% 0 0)", "rgb(1e+100 0 0)", "rgb(1e-100 0 0)", "rgb(255e000,0,0)"):
            with self.subTest(text=text):
                refused(self, text, "colour-unreadable")
        for text, want in (("rgb(2.55e2, 0, 0)", "#ff0000"), ("rgb(255e0,0,0)", "#ff0000"), ("rgb(255e-0 0 0)", "#ff0000"), ("rgb(1E2 0 0)", "#640000"), ("rgb(25500e-02 0 0)", "#ff0000"),
                           ("rgb(1e99, 0, 0)", "#ff0000"), ("rgb(1e-99, 0, 0)", "#000000"), ("rgb(.5e3, 0, 0)", "#ff0000")):
            with self.subTest(text=text):
                self.assertEqual(_colour.parse_colour(text), want)

    def test_the_largest_numbers_it_reads_end_in_a_colour_or_a_named_refusal_never_in_a_crash(self):
        # with two digits in the exponent nothing overflows: a chroma or lightness far beyond any screen is outside the gamut
        for exponent in range(3, 100, 4):
            for hue in (0, 30, 90, 142, 180, 264, 270, 359):
                for lightness in ("0", "0.5", "1", "9e99", "-9e99"):
                    text = "oklch(%s 1e%d %d)" % (lightness, exponent, hue)
                    with self.subTest(text=text):
                        refused(self, text, "colour-gamut")
        for text in ("oklch(9e99 0 0)", "oklch(9e99% 9e99% 1000turn)", "oklch(-9e99 0 0)"):
            with self.subTest(text=text):
                refused(self, text, "colour-gamut")
        for text, want in (("rgb(9e99% -9e99% 0%)", "#ff0000"), ("rgb(-9e99, 9e99, 0)", "#00ff00"), ("hsl(0 9e99% 50%)", "#ff0000"), ("hsl(0 100% 9e99%)", "#ffffff"),
                           ("hsl(0 -9e99% 50%)", "#808080")):
            with self.subTest(text=text):
                self.assertEqual(_colour.parse_colour(text), want)

    def test_a_hue_of_more_than_a_thousand_turns_is_not_read(self):
        # the site's renderer draws hsl(1e9 100% 50%) as another colour than CSS has it, and hsl(1e39 ...) black (test_paint.py holds the pictures)
        for text in ("hsl(1e9 100% 50%)", "hsl(360001 100% 50%)", "hsl(-360001deg 100% 50%)", "hsl(1000.1turn 100% 50%)", "hsl(6284rad 100% 50%)", "hsl(400001grad 100% 50%)",
                     "hsl(9e99turn 50% 50%)", "hsl(-9.9e99rad 50% 50%)", "oklch(0.5 0.1 1e9)", "oklch(0.5 0.1 9e99turn)"):
            with self.subTest(text=text):
                refused(self, text, "colour-unreadable")
                self.assertIn("more than a thousand turns", _unreadable_message(text))
        for text, want in (("hsl(360000 100% 50%)", "#ff0000"), ("hsl(-360000 100% 50%)", "#ff0000"), ("hsl(1000turn 100% 50%)", "#ff0000"), ("hsl(36030 100% 50%)", "#ff8000"),
                           ("hsl(100.25turn 100% 50%)", "#80ff00"), ("hsl(400000grad 100% 50%)", "#ff0000")):
            with self.subTest(text=text):
                self.assertEqual(_colour.parse_colour(text), want)

    def test_hsl_needs_a_percent_sign_on_its_saturation_and_its_lightness(self):
        # the site's renderer draws black for hsl(0,100,50): the hex this check would give is not what shows (test_paint.py holds the picture)
        for text in ("hsl(0,100,50)", "hsl(0 100 50)", "hsl(0,100%,50)", "hsl(0 100 50%)", "hsla(0, 100, 50, 1)", "hsl(0deg 1 0.5)", "hsl(0 100% 50 / 1)"):
            with self.subTest(text=text):
                refused(self, text, "colour-unreadable")
                self.assertIn("each need a % sign", _unreadable_message(text))
        for text in ("hsl(0,100%,50%)", "hsl(0 100% 50%)", "hsl(0deg, 100%, 50%)", "hsl(360 100% 50%)", "hsl(0 150% 50%)", "hsl(0 100.0% 5e1%)"):
            with self.subTest(text=text):
                self.assertEqual(_colour.parse_colour(text), "#ff0000")

    def test_an_alpha_of_one_is_read_after_a_comma_or_in_the_space_form_after_a_slash_and_nowhere_else(self):
        # rgb(255,0,0/1): commas and a slash. The site's renderer draws black for it.
        for text in ("rgb(255,0,0/1)", "rgb(255,0,0/100%)", "hsl(0,100%,50%/1)", "rgba(255, 0, 0 / 1)", "hsla(0, 100%, 50% / 100%)", "rgb(255,0,0,1/1)", "rgb(255 0 0 1)", "rgb(255 0 0, 1)"):
            with self.subTest(text=text):
                refused(self, text, "colour-unreadable")
        self.assertIn("commas and a slash", _unreadable_message("rgb(255,0,0/1)"))
        for text in ("rgba(255,0,0,1)", "rgba(255, 0, 0, 100%)", "rgb(255,0,0,1.0)", "hsla(0,100%,50%,1)", "hsl(0, 100%, 50%, 100%)", "rgb(255 0 0 / 1)", "rgb(255 0 0/100%)",
                     "rgba(255 0 0 / 1.0)", "hsl(0 100% 50% / 1)", "hsla(0 100% 50% / 100%)", "rgb(100% 0% 0% / 1)", "rgba(255,0,0)"):
            with self.subTest(text=text):
                self.assertEqual(_colour.parse_colour(text), "#ff0000")
        # and an alpha below one is see-through in the forms that are read
        for text in ("rgba(255,0,0,0.99)", "rgb(255 0 0 / 99%)", "hsl(0 100% 50% / 0)"):
            with self.subTest(text=text):
                refused(self, text, "colour-alpha")

    def test_oklch_is_read_for_a_palette_and_refused_for_the_paint_of_a_file_the_renderer_draws(self):
        # the site's renderer does not read oklch() and draws black: a mark's own paint is not taken from it. A palette's value
        # is only turned into hex and written, and a stylesheet is read by a browser, so there it is read as CSS has it.
        self.assertEqual(_colour.parse_colour("oklch(0.5 0.15 30)"), "#a8372a")
        for text in ("oklch(0.5 0.15 30)", "OKLCH(50% 0 0)", "oklch(0.7 0.4 150)", "oklch(0 0 0 / 1)"):
            with self.subTest(text=text):
                with self.assertRaises(Refusal) as cm:
                    _colour.parse_colour(text, drawn=True)
                self.assertEqual(cm.exception.code, "colour-unreadable")
                for part in ("The mark paints with %r" % text, "does not read oklch()", "would paint black", "written as #rrggbb"):
                    self.assertIn(part, str(cm.exception))
        # what currentColor stands for is held to the same rule; everything else is read the same for both
        with self.assertRaises(Refusal):
            _colour.parse_colour("currentColor", current="oklch(0.5 0.15 30)", drawn=True)
        self.assertEqual(_colour.parse_colour("currentColor", current="oklch(0.5 0.15 30)"), "#a8372a")
        for text in ("#B4531A", "rgb(180, 83, 26)", "hsl(22.2078 74.7573% 40.3922%)", "tomato", "rgba(180,83,26,1)"):
            with self.subTest(text=text):
                self.assertEqual(_colour.parse_colour(text, drawn=True), _colour.parse_colour(text))

    def test_an_oklch_chroma_below_zero_is_zero_as_css_has_it_not_the_opposite_hue(self):
        # CSS Color 4 clamps a negative chroma to 0 when the value is parsed: a browser shows a grey.
        # Read as it stood, -0.1 at hue 210 came out as +0.1 at hue 30, a brown the owner never saw.
        for text in ("oklch(0.5 -0.1 210)", "oklch(0.5 -0.1 30)", "oklch(50% -25% 30)", "oklch(0.5 -1e99 30)"):
            with self.subTest(text=text):
                self.assertEqual(_colour.parse_colour(text), _colour.parse_colour("oklch(0.5 0 0)"))
        self.assertEqual(_colour.parse_colour("oklch(0.5 0.1 30)"), "#944b40", "a chroma above zero is left alone")
        self.assertEqual(_colour.parse_colour("oklch(0.5 -0 30)"), _colour.parse_colour("oklch(0.5 0 30)"))


class Contrast(unittest.TestCase):
    def test_the_two_ends_and_a_well_known_pair(self):
        self.assertAlmostEqual(_colour.ratio("#000000", "#ffffff"), 21.0, places=6)
        self.assertAlmostEqual(_colour.ratio("#ffffff", "#ffffff"), 1.0, places=6)
        # #767676 on white is the lightest grey that passes AA for body text; #777777 is not
        self.assertGreaterEqual(_colour.ratio("#767676", "#ffffff"), 4.5)
        self.assertLess(_colour.ratio("#777777", "#ffffff"), 4.5)

    def test_order_does_not_matter(self):
        self.assertEqual(_colour.ratio("#123456", "#fedcba"), _colour.ratio("#fedcba", "#123456"))

    def test_the_ratio_is_never_rounded_before_it_is_compared(self):
        # 4.4998 to 1: it prints as 4.50 when rounded to two places, and it must still fail
        h = "#7c7480"
        r = _colour.ratio(h, "#ffffff")
        self.assertTrue(4.4995 < r < 4.5, r)
        self.assertEqual("%.2f" % r, "4.50")
        self.assertFalse(_colour.passes(h, "#ffffff", 4.5))
        self.assertNotIn(_colour.shown(r), ("4.5", "4.50"))

    def test_shown_never_rounds_up_to_a_pass(self):
        self.assertEqual(_colour.shown(4.4999), "4.49")
        self.assertEqual(_colour.shown(4.5), "4.5")
        self.assertEqual(_colour.shown(3.1), "3.1")
        self.assertEqual(_colour.shown(21.0), "21")
        self.assertEqual(_colour.shown(4.5601), "4.56")

    def test_a_pair_a_hair_under_the_line_never_prints_as_the_number_it_needed(self):
        # these fail by less than a billionth, and the line the owner reads said "is 4.5 to 1; text needs 4.5 to 1"
        for fg, bg, need, want in (("#2671e5", "#060201", 4.5, "4.49"), ("#1c5f98", "#190102", 3.0, "2.99")):
            with self.subTest(fg=fg, bg=bg):
                r = _colour.ratio(fg, bg)
                self.assertTrue(need - 1e-9 < r < need, r)
                self.assertFalse(_colour.passes(fg, bg, need))
                self.assertEqual(_colour.shown(r), want)
                self.assertNotEqual(_colour.shown(r), _colour.shown(need))

    def test_shown_cuts_the_number_as_written_so_a_ratio_of_exactly_two_places_keeps_them(self):
        # 4.6 is stored as 4.5999999999999996...: cut from the float it would print as 4.59
        for r, want in ((4.6, "4.6"), (4.56, "4.56"), (4.57, "4.57"), (1.15, "1.15"), (8.2, "8.2"), (16.99, "16.99"),
                        (2.9999999999, "2.99"), (4.4999999999999, "4.49"), (4.999, "4.99"), (1.0, "1"), (3, "3"), (0.07, "0.07"),
                        (1e-7, "0"), (20.999999999999996, "20.99")):
            with self.subTest(r=r):
                self.assertEqual(_colour.shown(r), want)
        self.assertEqual(_colour.shown(_colour.ratio("#000000", "#ffffff")), "21")
        self.assertEqual(_colour.shown(_colour.ratio("#123456", "#123456")), "1")

    def test_luminance_of_the_channels_below_the_cut(self):
        # 8-bit values never fall between 0.03928 and 0.04045, so the two published
        # thresholds give the same answer; pin the segment boundary values around them
        self.assertAlmostEqual(_colour.luminance("#0a0a0a"), 0.003035, places=6)
        self.assertAlmostEqual(_colour.luminance("#0b0b0b"), 0.003347, places=6)


if __name__ == "__main__":
    unittest.main()
