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

    # what Python's strip() and split() take for a blank and CSS does not
    NOT_CSS_SPACE = ("\u00a0", "\u2003", "\u3000", "\u2028", "\u2029", "\u0085", "\x0b", "\x1c", "\x1d", "\x1e", "\x1f", "\u1680", "\u202f", "\ufeff")

    def test_only_what_css_takes_for_white_space_is_taken_off_a_colour_or_stands_between_its_numbers(self):
        # round 5, checked in a browser: `--bg:` + a no-break space + `#ffffff` (a line pasted from a web page) is no colour to Chromium, and
        # Python's strip() read past the no-break space, so the check said #ffffff and the editor left the line "as it stands"
        self.assertEqual(_colour.SPACE, " \t\r\n\f")
        for blank in self.NOT_CSS_SPACE:
            for text in (blank + "#7b0000", "#7b0000" + blank, blank + "#7b0000" + blank, " " + blank + " #7b0000", "#7b0000\n" + blank, blank + "red", "rgb(123, 0, 0)" + blank,
                         "rgb(123" + blank + "0 0)", "rgb(123," + blank + "0, 0)", "rgb(123 0 0 /" + blank + "1)", "hsl(0" + blank + "100% 50%)", "oklch(0.5 0.1" + blank + "30)",
                         "rgb" + blank + "(123, 0, 0)", "rgb(" + blank + "123, 0, 0)", "#7b" + blank + "0000"):
                with self.subTest(text=text):
                    for kw in ({}, {"drawn": True}):
                        with self.assertRaises(Refusal) as cm:
                            _colour.parse_colour(text, **kw)
                        self.assertEqual(cm.exception.code, "colour-unreadable")
                    with self.assertRaises(Refusal):
                        _colour.parse_colour("currentColor", current=text)
        # where the blank stands before or after the colour, the sentence says so and says what to do
        for text in ("\u00a0#7b0000", "#7b0000\u2003", " \x0b#7b0000 "):
            message = _unreadable_message(text)
            for part in ("The colour '#7b0000' has a character before or after it that looks like a space and is none to a browser", "a no-break space",
                         "a browser takes the whole value for no colour", "Delete the blanks around the colour and type them again."):
                self.assertIn(part, message)
        # the five that CSS takes, around the colour and between its numbers, in any number
        for text in (" #7b0000", "\t#7b0000\n", "\r\n#7b0000\f", "\f \t#7B0000 \r", "rgb(123\t0\n0)", "rgb(\f123,\r\n0,\t0 )", "rgb(123 \n\t 0 0 /\f1)", "hsl(0\n100%\f50% )",
                     "\n\nrgb(\t123,0,0\t)\n"):
            with self.subTest(text=text):
                self.assertEqual(_colour.parse_colour(text), "#ff0000" if "hsl" in text else "#7b0000")

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

    BIG = ("oklch(0.5 10000000000e99 0)", "rgb(%s,0,0)" % ("9" * 400), "oklch(%s 0 0)" % ("9" * 200))  # round 4: each ended in OverflowError

    def test_a_number_is_at_most_64_characters_long_as_the_svg_check_has_it_and_a_longer_one_is_refused_by_name(self):
        # round 3 took the overflow guards out, reasoning that two digits of exponent cannot overflow. The mantissa had no limit:
        # 400 digits in rgb() and 200 in oklch() ended in a traceback from the palette check, the stylesheet reading and the install.
        import _paint
        import _svg
        self.assertEqual((_colour._NUM, _colour.MAX_NUMBER_CHARS), (_svg._NUM, _svg.MAX_VALUE), "one grammar for a number, and one limit on its length, in both files")
        self.assertEqual(_colour._NUM, _paint._NUM)
        for text in self.BIG[1:] + ("hsl(%s 50%% 50%%)" % ("1" * 65), "rgb(0 0 %s)" % ("0" * 62 + "255"), "rgb(0, 0, 0, %s)" % ("1." + "0" * 63), "oklch(0.5 0.1 %sdeg)" % ("0" * 64 + "9"),
                                 "rgb(%s%% 0%% 0%%)" % ("5" * 65), "rgb(.%s 0 0)" % ("5" * 64), "rgb(-%s 0 0)" % ("5" * 64), "hsl(0 %se-99%% 50%%)" % ("5" * 61)):
            with self.subTest(text=text[:24], length=len(text)):
                refused(self, text, "colour-unreadable")
                self.assertIn("it holds a number of more than 64 characters", _unreadable_message(text))
        # 64 characters are read, sign, point and exponent counted, the unit not
        for text, want in (("rgb(%s 0 0)" % ("0" * 61 + "255"), "#ff0000"), ("rgb(0 0 %s)" % ("9" * 64), "#0000ff"), ("rgb(0, 0, 0, %s)" % ("1." + "0" * 62), "#000000"),
                           ("hsl(%sdeg 100%% 50%%)" % ("0" * 61 + "120"), "#00ff00"), ("rgb(%s%% 0%% 0%%)" % ("0" * 62 + "50"), "#800000"), ("rgb(-%s 0 0)" % ("5" * 63), "#000000"),
                           ("rgb(%se99 0 0)" % ("9" * 60), "#ff0000"), ("rgb(.%s 0 0)" % ("0" * 62 + "9"), "#000000")):
            with self.subTest(text=text[:24], length=len(text)):
                self.assertEqual(_colour.parse_colour(text), want)
        # the largest numbers the two limits allow are outside any screen in oklch(), and are said to be, whatever the sums do with them
        for text in (self.BIG[0], "oklch(%se99 0 0)" % ("9" * 60), "oklch(0.5 %se99 0)" % ("9" * 60), "oklch(-%se99 %se99 90)" % ("9" * 59, "9" * 60), "oklch(%se99%% %se99%% 1)" % ("9" * 60, "9" * 60)):
            with self.subTest(text=text[:24]):
                refused(self, text, "colour-gamut")

    def test_no_colour_text_ends_in_anything_but_a_colour_or_a_refusal(self):
        # the property the three above are cases of: a few thousand colours with long whole parts, long fractions and extreme exponents in every function
        import random
        rng = random.Random(20261013)
        digits = lambda n: "".join(rng.choice("0123456789") for _ in range(n))  # noqa: E731

        def number(unit=""):
            """A number for one place of a function: mostly long or extreme, sometimes an everyday one, with the unit the place takes or, now and then, another."""
            whole, fraction = digits(rng.choice((1, 1, 2, 3, 17, 60, 63, 64, 65, 200, 400))), digits(rng.choice((1, 2, 6, 60, 64, 300)))
            mantissa = rng.choice((whole, "." + fraction, whole + "." + fraction, "0." + fraction, "0." + fraction, "1", digits(2), digits(1)))
            exponent = rng.choice(("", "", "", "", "e0", "e1", "e2", "e-2", "e9", "e99", "e-99", "E+99", "e308", "e-400", "e999"))
            unit = unit if rng.random() < 0.85 else rng.choice(("", "%", "deg", "turn", "rad", "grad", "px"))
            return rng.choice(("", "", "", "", "-", "+")) + mantissa + exponent + unit

        outcomes = {}
        for _ in range(4000):
            name = rng.choice(("rgb", "rgba", "hsl", "hsla", "oklch", "oklch", "oklch", "OKLCH", "Rgb", "lab", "color"))
            units = {"rgb": rng.choice((("", "", ""), ("%", "%", "%"))), "hsl": (rng.choice(("", "deg", "turn")), "%", "%"), "okl": (rng.choice(("", "%")), "", rng.choice(("", "deg")))}.get(name.lower()[:3], ("", "", ""))
            parts = [number(unit) for unit in units]
            alpha = rng.choice(("", "", "", ", 1", " / 1", "/100%", ", 0.5", " / " + number(), ", " + number()))
            text = "%s(%s%s)" % (name, rng.choice((", ", " ", " ", ",", "  ")).join(parts), alpha)
            for kw in ({}, {"drawn": True}, {"current": "#123456"}):
                try:
                    outcome = "a colour" if self.assertRegex(_colour.parse_colour(text, **kw), "^#[0-9a-f]{6}$") is None else ""
                except Refusal as r:
                    outcome = r.code
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
            try:  # and where the text is what currentColor stands for
                self.assertRegex(_colour.parse_colour("currentColor", current=text), "^#[0-9a-f]{6}$")
            except Refusal:
                pass
        for outcome in ("a colour", "colour-unreadable", "colour-gamut", "colour-alpha"):
            self.assertGreater(outcomes.get(outcome, 0), 60, "the texts tried no longer end as %r: %r" % (outcome, outcomes))

    def test_the_largest_numbers_it_reads_end_in_a_colour_or_a_named_refusal_never_in_a_crash(self):
        # with two digits in the exponent and 64 characters in all, a chroma or lightness far beyond any screen is outside the gamut
        for exponent in range(3, 100, 4):
            for hue in (0, 30, 90, 142, 180, 264, 270, 359):
                for lightness in ("0", "0.5", "1", "9e99", "-9e99"):
                    text = "oklch(%s 1e%d %d)" % (lightness, exponent, hue)
                    with self.subTest(text=text):
                        refused(self, text, "colour-gamut")
        for text in ("oklch(9e99 0 0)", "oklch(9e99% 9e99% 1000turn)", "oklch(-9e99 0 0)"):
            with self.subTest(text=text):
                refused(self, text, "colour-gamut")
        for text in ("hsl(0 9e99% 50%)", "hsl(0 100% 9e99%)"):
            with self.subTest(text=text):
                refused(self, text, "colour-unreadable")
        for text, want in (("rgb(9e99% -9e99% 0%)", "#ff0000"), ("rgb(-9e99, 9e99, 0)", "#00ff00"), ("hsl(0 -9e99% 50%)", "#808080"), ("hsl(0 100% -9e99%)", "#000000")):
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
        for text in ("hsl(0,100%,50%)", "hsl(0 100% 50%)", "hsl(0deg, 100%, 50%)", "hsl(360 100% 50%)", "hsl(0 100.0% 5e1%)"):
            with self.subTest(text=text):
                self.assertEqual(_colour.parse_colour(text), "#ff0000")

    def test_a_saturation_or_a_lightness_over_100_percent_is_not_read(self):
        # round 5, compared with Chromium: `hsl(270deg 150% 33.333%)` is #5500d4 there, and #5500aa with the saturation cut to 100% as this
        # check cut it; 42 of 12,000 spellings differed, each with a saturation over 100%
        for text in ("hsl(270deg 150% 33.333%)", "hsl(0 150% 50%)", "hsl(0, 100.001%, 50%)", "hsla(0, 101%, 50%, 1)", "hsl(0 100% 100.5%)", "hsl(0 50% 200%)", "hsl(0 1e3% 50%)",
                     "hsl(120 300% 300% / 1)"):
            with self.subTest(text=text):
                refused(self, text, "colour-unreadable")
                self.assertIn("the saturation or the lightness of hsl() is over 100%", _unreadable_message(text))
                with self.assertRaises(Refusal):
                    _colour.parse_colour(text, drawn=True)
        # exactly 100% is read, and so is what lies under 0%, which a browser takes for 0% as this check does
        for text, want in (("hsl(0 100% 50%)", "#ff0000"), ("hsl(0 100.0% 100.0%)", "#ffffff"), ("hsl(270deg 100% 33.333%)", "#5500aa"), ("hsl(0 1e2% 5e1%)", "#ff0000"),
                           ("hsl(0 -50% 50%)", "#808080"), ("hsl(0 100% -5%)", "#000000")):
            with self.subTest(text=text):
                self.assertEqual(_colour.parse_colour(text), want)

    def test_what_currentcolor_stands_for_is_read_through_the_same_guarded_door(self):
        # round 5: the text that currentColor stands for is read by parse_colour itself, so that nothing it holds ends in anything but a
        # colour or a refusal that names it. No number the grammar takes overflows outside oklch() (rgb() multiplies by 2.55 and hsl() cuts
        # to 0..1, with at most 1e160 going in), so the overflow is made here by hand.
        from unittest import mock
        for text in self.BIG + ("rgb(%se99 0 0)" % ("9" * 60), "hsl(%se99 50%% 50%%)" % ("9" * 60), "rgb(%se99%% 0%% 0%%)" % ("9" * 60), "oklch(%se99 %se99 0)" % ("9" * 60, "9" * 60)):
            with self.subTest(text=text[:24]):
                try:
                    direct = _colour.parse_colour(text)
                except Refusal as r:
                    direct = r.code
                try:
                    through = _colour.parse_colour("currentColor", current=text)
                except Refusal as r:
                    through = r.code
                self.assertEqual(through, direct)
        with mock.patch.object(_colour, "_hex", side_effect=OverflowError):
            for kw in ({}, {"drawn": True}):
                with self.assertRaises(Refusal) as cm:
                    _colour.parse_colour("currentColor", current="rgb(1, 2, 3)", **kw)
                self.assertEqual(cm.exception.code, "colour-unreadable")
                self.assertIn("'rgb(1, 2, 3)'", str(cm.exception), "and it names the colour that currentColor stands for, not the word")

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

    def test_a_refusal_speaks_of_a_mark_only_where_there_is_one_and_names_only_the_spellings_its_caller_reads(self):
        # round 6: `--bg: currentColor` in a stylesheet was answered with "The mark paints with currentColor", where there is no mark; and a
        # mark's paint that could not be read was told to write it "as ... oklch()", which is refused for a mark
        def message(text, **kw):
            with self.assertRaises(Refusal) as cm:
                _colour.parse_colour(text, **kw)
            return str(cm.exception)

        for text in ("currentColor", "CurrentColor", "url(#g)", "URL(x.png)", " url( 'a' ) "):
            with self.subTest(text=text):
                written, drawn = message(text), message(text, drawn=True)
                self.assertNotIn("mark", written, "a cell of the palette, or a line of the stylesheet")
                self.assertIn("as #rrggbb.", written)
                self.assertIn("The mark paints with", drawn)
        self.assertEqual(message("currentColor"), "The colour is written as currentColor, which is whatever colour the text around it has and no colour of its own. Write the colour "
                                                  "itself, as #rrggbb.")
        self.assertEqual(message("url(#g)"), "The colour 'url(#g)' is a gradient or a pattern. This check reads one flat colour: write it as #rrggbb.")
        for text in ("lab(50% 40 59)", "rgb(1,2)", "notacolour", "hsl(0 150% 50%)", "rgb(%s,0,0)" % ("9" * 400), "", "#12345", "rgb(50%, 0, 0)", "hsl(1e9 100% 50%)", "\u00e9", "255."):
            with self.subTest(text=text[:20]):
                self.assertTrue(message(text).endswith(" Write it as #rrggbb, rgb(), hsl(), oklch() or a CSS colour name."), message(text))
                self.assertTrue(message(text, drawn=True).endswith(" Write it as #rrggbb, rgb(), hsl() or a CSS colour name."), message(text, drawn=True))
                self.assertNotIn("oklch", message(text, drawn=True), "a mark's paint is not read from oklch(), so it is not told to be written so")
                self.assertEqual(message(text, drawn=True).replace("hsl() or", "hsl(), oklch() or"), message(text), "the two differ in that and in nothing else")
                # and what currentColor stands for is told the same
                self.assertNotIn("oklch", message("currentColor", current=text or "x y", drawn=True))
                self.assertIn("oklch() or a CSS colour name.", message("currentColor", current=text or "x y"))

    def test_the_sentence_of_a_refusal_is_spelled_out_in_one_pass_and_reads_as_it_did(self):
        # round 6: a megabyte of cells that begin a colour and hold a letter beyond ASCII took 21 seconds, because each built a refusal whose
        # sentence was looked at character by character, a table lookup and a pattern each. Now a sentence without anything unseen in it is
        # passed through, and in any other only the characters that are not plain ASCII are looked at.
        from _refusal import spelled, unseen

        def one_by_one(text):
            return "".join(c.encode("unicode_escape").decode("ascii") if c != "\n" and unseen(c) else c for c in text)

        samples = ["", "plain", "two\nlines", "caf\u00e9", "a\u200bb", "a\ufe0fb", "a\u00a0b", "\x00\x1f\x7f\x9b", "tab\tand\rreturn", "\u2028\u2029", "\U000e0041\U000e0100", "\ud800",
                   "\u3164\u115f\u2800", "e\u0301", "\U0001f600", "a b", "\ufeff", "\u0378", "\ue000", "~ {}|", "\u00e9\n\u200b\n"]
        samples += ["The colour %r is not one this check can read." % s for s in samples] + [a + b for a in samples for b in samples]
        for text in samples:
            self.assertEqual(spelled(text), one_by_one(text), ascii(text))
        self.assertEqual(spelled("a\u200bb\u00e9\n\ufe0f"), "a\\u200bb\u00e9\n\\ufe0f")
        # counted, not timed: how many characters are looked up for one sentence (the megabyte itself is timed in test_palette and test_cli_palette)
        import _refusal
        looked = []
        real, _refusal.unseen = _refusal.unseen, lambda c: looked.append(c) or real(c)
        try:
            for text, most in (("#12345", 0), ("#\u00e9", 0), ("#\u00e9\u00e8 caf\u00e9", 0), ("#\ufe0f", 1), ("#\u200b", 0), ("#\ufe0f\u00e9\u3164", 3), ("#" + "\ufe0f\u00e9" * 30, 40)):
                with self.subTest(text=ascii(text)):
                    del looked[:]
                    with self.assertRaises(Refusal) as cm:
                        _colour.parse_colour(text)
                    self.assertEqual(cm.exception.code, "colour-unreadable")
                    self.assertGreater(len(str(cm.exception)), 100)
                    self.assertLessEqual(len(looked), most, "only what is not plain ASCII is looked up, and nothing at all in a sentence without a character nobody sees")
                    self.assertFalse([c for c in str(cm.exception) if real(c)])
        finally:
            _refusal.unseen = real

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
