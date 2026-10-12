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

    def test_nan_and_infinity_are_not_numbers(self):
        for text in ("rgb(nan, 0, 0)", "hsl(inf 50% 50%)", "oklch(nan 0 0)"):
            with self.subTest(text=text):
                with self.assertRaises(Refusal):
                    _colour.parse_colour(text)

    def test_a_number_so_large_that_the_arithmetic_overflows_is_refused_not_a_crash_and_not_a_colour(self):
        # each of these is a finite number as written; it is the unit conversion that overflows
        for text in ("hsl(1e308turn 50% 50%)", "hsl(1e308rad 50% 50%)", "hsl(-1e308turn 50% 50%)", "hsla(1e307turn, 50%, 50%, 1)",
                     "rgb(1e308% 0 0)", "rgb(0 -1e308% 0)", "rgba(0, 0, 1e307%, 1)",
                     "oklch(0.5 0.1 1e308turn)", "oklch(0.5 0.1 1e308rad)", "oklch(0.5 0 -1e308turn)"):
            with self.subTest(text=text):
                refused(self, text, "colour-unreadable")
                with self.assertRaises(Refusal) as cm:
                    _colour.parse_colour(text)
                self.assertIn("too large", str(cm.exception))

    def test_an_oklch_lightness_or_chroma_far_beyond_any_screen_is_outside_the_gamut_not_a_crash(self):
        for text in ("oklch(0.5 1e308 0)", "oklch(0.5 1e200 0)", "oklch(0.5 1e308% 0)", "oklch(1e308 0 0)", "oklch(1e200% 0 0)",
                     "oklch(-1e308 0 0)", "oklch(0.5 1e308 270)", "oklch(1 1e308 0.5turn)"):
            with self.subTest(text=text):
                refused(self, text, "colour-gamut")

    def test_no_chroma_however_large_and_no_hue_ever_gets_past_the_gamut_check_as_a_colour(self):
        # around 1e102 the cubes are still finite and their sums are not (inf - inf is not a number):
        # whichever way the arithmetic gives up, the answer is the named refusal
        for exponent in range(3, 309, 5):
            for hue in (0, 30, 90, 142, 180, 264, 270, 359):
                for lightness in ("0", "0.5", "1"):
                    text = "oklch(%s 1e%d %d)" % (lightness, exponent, hue)
                    with self.subTest(text=text):
                        refused(self, text, "colour-gamut")

    def test_an_oklch_chroma_below_zero_is_zero_as_css_has_it_not_the_opposite_hue(self):
        # CSS Color 4 clamps a negative chroma to 0 when the value is parsed: a browser shows a grey.
        # Read as it stood, -0.1 at hue 210 came out as +0.1 at hue 30, a brown the owner never saw.
        for text in ("oklch(0.5 -0.1 210)", "oklch(0.5 -0.1 30)", "oklch(50% -25% 30)", "oklch(0.5 -1e308 30)"):
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
