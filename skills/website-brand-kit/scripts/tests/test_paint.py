"""Scenarios 10 (the mark's side), 15, 17 (what is left of it) and 21: which colours a mark paints
with, read from the file's own paint values and not guessed from a picture.

A mark paints with `fill` and `stroke`, set as attributes, in a style attribute, or in a <style>
rule, and inherited through groups. The reader applies the cascade a renderer does, turns every
colour into one hex, and refuses by name what it cannot resolve: gradients and patterns, alpha,
a colour it does not know, `currentColor` it was not told the meaning of, and (for a drawing taken
out of a web page) class names that only the page's own CSS defines.
"""

import unittest

import _testutil as T
import _colour
import _palette
import _svg
from _refusal import Refusal

NS = 'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"'
D = 'd="M10 34A22 22 0 0 1 54 34Z"'


def svg(body, root=""):
    return ('<svg %s %s>%s</svg>' % (NS, root, body)).encode()


def colours(body, root="", **kw):
    return _svg.clean_svg(svg(body, root), **kw).colours


def refused(testcase, body, code, root="", **kw):
    with testcase.assertRaises(Refusal) as cm:
        _svg.clean_svg(svg(body, root), **kw)
    testcase.assertEqual(cm.exception.code, code, "refused for %r: %s" % (cm.exception.code, cm.exception))
    return cm.exception


class Resolving(unittest.TestCase):
    def test_every_way_of_writing_a_colour_ends_up_as_the_same_hex_in_the_cleaned_file(self):
        for value in ("#B4531A", "#b4531a", "rgb(180, 83, 26)", "rgb(180 83 26)", "hsl(22.2078 74.7573% 40.3922%)"):
            with self.subTest(value=value):
                clean = _svg.clean_svg(svg('<path fill="%s" %s/>' % (value, D)))
                self.assertEqual(clean.colours, ["#b4531a"])
                self.assertIn('fill="#b4531a"', clean.text)
        clean = _svg.clean_svg(svg('<path fill="tomato" %s/>' % D))
        self.assertEqual(clean.colours, ["#ff6347"])

    def test_the_real_marks_and_their_colours(self):
        self.assertEqual(_svg.clean_svg(T.real_svg(T.REAL_COLOUR)).colours, ["#b4531a", "#6b2c0b"])
        self.assertEqual(_svg.clean_svg(T.real_svg(T.REAL_MONO)).colours, ["#b4531a"])

    def test_an_unset_fill_is_black_and_an_unset_stroke_is_nothing(self):
        self.assertEqual(colours('<path %s/>' % D), ["#000000"])
        self.assertEqual(colours('<path fill="none" stroke="#123456" stroke-width="2" %s/>' % D), ["#123456"])
        self.assertEqual(colours('<path fill="#abcdef" %s/>' % D), ["#abcdef"])

    def test_a_stroke_of_no_width_paints_nothing(self):
        self.assertEqual(colours('<path fill="#111111" stroke="#222222" stroke-width="0" %s/>' % D), ["#111111"])
        self.assertEqual(colours('<path fill="#111111" stroke="#222222" %s/>' % D), ["#111111", "#222222"])

    def test_a_line_has_no_fill(self):
        self.assertEqual(colours('<line x1="0" y1="0" x2="9" y2="9" stroke="#222222"/>'), ["#222222"])

    def test_colours_come_in_the_order_they_are_first_used_each_once(self):
        body = '<path fill="#111111" %s/><rect width="2" height="2" fill="#222222"/><circle r="1" fill="#111111"/>' % D
        self.assertEqual(colours(body), ["#111111", "#222222"])

    def test_a_shape_does_not_hand_its_fill_to_the_next_one(self):
        self.assertEqual(colours('<path fill="#aa0000" %s/><path %s/>' % (D, D)), ["#aa0000", "#000000"])
        self.assertEqual(colours('<g><path fill="#aa0000" %s/></g><path %s/>' % (D, D)), ["#aa0000", "#000000"])

    def test_a_group_passes_its_fill_down_and_a_child_can_change_it(self):
        body = '<g fill="#aa0000"><path %s/><path fill="#00aa00" %s/><g><rect width="1" height="1"/></g></g>' % (D, D)
        self.assertEqual(colours(body), ["#aa0000", "#00aa00"])

    def test_the_cascade_is_the_one_a_renderer_applies(self):
        # presentation attribute < style rule < style attribute; id beats class beats tag; later beats earlier
        style = "<style>path{fill:#111111} .a{fill:#222222} #p{fill:#333333} .b{fill:#444444} .c{fill:#555555}</style>"
        cases = [
            ('<path %s/>' % D, "#111111"),
            ('<path class="a" %s/>' % D, "#222222"),
            ('<path class="a" id="p" %s/>' % D, "#333333"),
            ('<path class="a b" %s/>' % D, "#444444"),
            ('<path class="b c" %s/>' % D, "#555555"),
            ('<path fill="#999999" %s/>' % D, "#111111"),
            ('<path fill="#999999" style="fill:#666666" class="a" %s/>' % D, "#666666"),
        ]
        for body, want in cases:
            with self.subTest(body=body):
                self.assertEqual(colours(style + body), [want])

    def test_a_more_specific_rule_wins_even_when_it_comes_first(self):
        style = "<style>#q{fill:#777777} .k{fill:#888888} path{fill:#111111}</style>"
        self.assertEqual(colours(style + '<path id="q" class="k" %s/>' % D), ["#777777"])
        self.assertEqual(colours(style + '<path class="k" %s/>' % D), ["#888888"])

    def test_a_rule_with_several_selectors_and_a_compound_one(self):
        style = "<style>.x, rect{fill:#123456} path.y{fill:#654321}</style>"
        self.assertEqual(colours(style + '<rect width="1" height="1"/><path class="y" %s/><path class="x" %s/>' % (D, D)),
                         ["#123456", "#654321"])

    def test_a_selector_the_reader_does_not_know_is_refused_not_ignored(self):
        for sel in ("g path", "g > path", "path:first-child", "path[fill]", "path + path", "*::before"):
            with self.subTest(sel=sel):
                refused(self, "<style>%s{fill:#111111}</style><path %s/>" % (sel, D), "css-unreadable")

    def test_a_property_it_does_not_know_is_refused_by_name(self):
        err = refused(self, '<path style="mix-blend-mode:multiply" %s/>' % D, "blend")
        err = refused(self, "<style>path{transform:rotate(9deg)}</style><path %s/>" % D, "css-property")
        self.assertIn("transform", str(err))

    def test_hidden_things_do_not_count(self):
        self.assertEqual(colours('<path fill="#111111" %s/><g display="none"><path fill="#999999" %s/></g>' % (D, D)), ["#111111"])
        body = '<g visibility="hidden"><path fill="#999999" %s/><path visibility="visible" fill="#222222" %s/></g>' % (D, D)
        self.assertEqual(colours('<path fill="#111111" %s/>' % D + body), ["#111111", "#222222"])
        self.assertEqual(colours('<path fill="#111111" %s/><path style="display:none" fill="#999999" %s/>' % (D, D)), ["#111111"])

    def test_shapes_that_only_clip_or_sit_in_defs_are_not_painted(self):
        body = ('<defs><clipPath id="c"><rect width="9" height="9" fill="#999999"/></clipPath><circle r="1" fill="#888888"/></defs>'
                '<path clip-path="url(#c)" fill="#111111" %s/>' % D)
        self.assertEqual(colours(body), ["#111111"])

    def test_the_cleaned_file_is_a_fixed_point(self):
        for data in (svg("<style>.a{fill:tomato}</style><path class=\"a\" %s/>" % D), T.real_svg(T.REAL_COLOUR)):
            once = _svg.clean_svg(data)
            twice = _svg.clean_svg(once.text.encode("utf-8"))
            self.assertEqual(once.text, twice.text)
            self.assertEqual(once.colours, twice.colours)
            self.assertNotIn("<style", once.text)
            self.assertNotIn("class=", once.text)


class CurrentColour(unittest.TestCase):
    def test_it_is_the_colour_the_intake_supplies(self):
        clean = _svg.clean_svg(svg('<path fill="currentColor" %s/>' % D), current="#b4531a")
        self.assertEqual(clean.colours, ["#b4531a"])
        self.assertNotIn("currentColor", clean.text)
        self.assertIn('fill="#b4531a"', clean.text)

    def test_color_can_itself_be_inherited_or_be_currentcolor(self):
        body = '<g color="#123456"><path color="inherit" fill="currentColor" %s/><path color="currentColor" fill="currentColor" stroke="#654321" %s/></g>' % (D, D)
        self.assertEqual(colours(body), ["#123456", "#654321"])

    def test_a_colour_set_in_the_file_wins(self):
        clean = _svg.clean_svg(svg('<g color="#123456"><path fill="currentColor" %s/></g>' % D), current="#b4531a")
        self.assertEqual(clean.colours, ["#123456"])
        clean = _svg.clean_svg(svg('<path style="color:#654321" stroke="currentColor" fill="none" %s/>' % D))
        self.assertEqual(clean.colours, ["#654321"])

    def test_with_no_meaning_given_it_is_refused(self):
        err = refused(self, '<path fill="currentColor" %s/>' % D, "colour-current")
        self.assertIn("currentColor", str(err))


class Refusals(unittest.TestCase):
    def test_gradients_and_patterns_in_the_paint(self):
        for fill in ("url(#g)", "url('#p')", "URL( #g )"):
            with self.subTest(fill=fill):
                refused(self, '<path fill="%s" %s/>' % (fill, D), "colour-gradient")

    def test_see_through_in_every_spelling(self):
        for attr in ('fill="rgba(180,83,26,0.5)"', 'fill="#b4531a80"', 'fill="transparent"', 'opacity="0.5"',
                     'fill-opacity="0.4"', 'stroke-opacity=".9"', 'style="opacity:.5"', 'fill="hsl(0 100% 50% / 30%)"', 'opacity="0"'):
            with self.subTest(attr=attr):
                refused(self, '<path %s %s/>' % (attr, D), "colour-alpha")

    def test_full_opacity_is_not_alpha_and_leaves_no_trace(self):
        clean = _svg.clean_svg(svg('<path opacity="1" fill-opacity="100%%" fill="#111111" %s/>' % D))
        self.assertEqual(clean.colours, ["#111111"])
        self.assertNotIn("opacity", clean.text)

    def test_alpha_on_a_group_is_alpha(self):
        refused(self, '<g opacity="0.5"><path fill="#111111" %s/></g>' % D, "colour-alpha")

    def test_a_colour_it_cannot_read(self):
        for fill in ("notacolour", "rgb(1,2)", "lab(50% 40 59)", "var(--brand)"):
            with self.subTest(fill=fill):
                refused(self, '<path fill="%s" %s/>' % (fill, D), "colour-unreadable")

    def test_a_mark_with_nothing_visible_in_it(self):
        for body in ('<path fill="none" %s/>' % D, '<path fill="none" stroke="#111111" stroke-width="0" %s/>' % D,
                     '<g display="none"><path %s/></g>' % D, '<path visibility="hidden" %s/>' % D, "", "<defs/>"):
            with self.subTest(body=body):
                err = refused(self, body, "blank-mark")
                self.assertIn("drawn", str(err))


class FromAPage(unittest.TestCase):
    def page(self, inner):
        return ('<!doctype html><html><head><style>.logo path{fill:#b4531a}</style></head><body>%s</body></html>' % inner).encode()

    def test_a_class_only_the_pages_own_css_defines_is_refused(self):
        with self.assertRaises(Refusal) as cm:
            _svg.clean_svg(self.page('<svg viewBox="0 0 64 64"><path class="logo" %s/></svg>' % D), source="html")
        self.assertEqual(cm.exception.code, "page-css")
        self.assertIn("logo", str(cm.exception))

    def test_the_same_class_with_the_rule_inside_the_svg_is_fine(self):
        data = self.page('<svg viewBox="0 0 64 64"><style>.logo{fill:#b4531a}</style><path class="logo" %s/></svg>' % D)
        self.assertEqual(_svg.clean_svg(data, source="html").colours, ["#b4531a"])

    def test_a_plain_svg_file_may_carry_a_class_nothing_styles(self):
        self.assertEqual(colours('<path class="leftover" fill="#111111" %s/>' % D), ["#111111"])

    def test_the_inline_svg_of_a_page_taken_out_and_given_on_its_own_keeps_the_rule(self):
        data = _svg.html_svgs(self.page('<svg viewBox="0 0 64 64"><path class="logo" %s/></svg>' % D))[0].encode()
        with self.assertRaises(Refusal) as cm:
            _svg.clean_svg(data, source="html-svg")
        self.assertEqual(cm.exception.code, "page-css")

    def test_currentcolor_in_a_page_is_refused_unless_told_what_it_means(self):
        data = self.page('<svg viewBox="0 0 64 64"><path fill="currentColor" %s/></svg>' % D)
        with self.assertRaises(Refusal) as cm:
            _svg.clean_svg(data, source="html")
        self.assertEqual(cm.exception.code, "colour-current")
        self.assertEqual(_svg.clean_svg(data, source="html", current="#b4531a").colours, ["#b4531a"])


def bakery():
    p = _palette.Palette()
    p.light, p.dark, p.brand = dict(T.BAKERY_LIGHT), dict(T.BAKERY_DARK), "#b4531a"
    return p


class AgainstThePalette(unittest.TestCase):
    """Scenario 21: colours of the mark that the palette does not hold are listed, never recoloured."""

    def test_the_real_mark_against_the_bakerys_palette(self):
        report = _palette.check_mark(_svg.clean_svg(T.real_svg(T.REAL_COLOUR)).colours, bakery())
        self.assertEqual(report.colours, ["#b4531a", "#6b2c0b"])
        self.assertEqual(report.outside, ["#6b2c0b"], "the trial's second, darker brown is not in the palette")

    def test_a_colour_counts_as_in_the_palette_in_either_theme_or_as_the_primary(self):
        p = bakery()
        report = _palette.check_mark(["#e2874a", "#3a1d0a", "#b4531a", "#abcdef"], p)
        self.assertEqual(report.outside, ["#abcdef"])
        p.brand = "#abcdef"  # the primary alone, which no theme row holds
        self.assertEqual(_palette.check_mark(["#abcdef"], p).outside, [])

    def test_the_one_colour_twin_is_inside(self):
        self.assertEqual(_palette.check_mark(_svg.clean_svg(T.real_svg(T.REAL_MONO)).colours, bakery()).outside, [])

    def test_a_mark_dark_on_the_dark_theme_is_named_with_the_theme_and_the_ratio(self):
        # Scenario 15: the brown rows vanish on the dark background (1.75 to 1)
        report = _palette.check_mark(["#b4531a", "#6b2c0b"], bakery())
        self.assertEqual(sorted(report.low), ["dark"])
        self.assertEqual([c for c, _r in report.low["dark"]], ["#6b2c0b"])
        self.assertTrue(1.7 < report.low["dark"][0][1] < 1.8)
        self.assertEqual(_palette.check_mark(["#b4531a"], bakery()).low, {})

    def test_three_to_one_is_the_line_and_it_is_not_rounded(self):
        p = bakery()
        # 2.9999 to 1 on the dark background prints as 3.00 when rounded, and is still under
        self.assertTrue(2.999 < _colour.ratio("#46676a", p.dark["bg"]) < 3.0)
        self.assertEqual("%.2f" % _colour.ratio("#46676a", p.dark["bg"]), "3.00")
        self.assertIn("dark", _palette.check_mark(["#46676a"], p).low)
        self.assertNotIn("dark", _palette.check_mark(["#31639e"], p).low)  # 3.0003 to 1 passes

    def test_with_no_palette_rows_for_a_theme_nothing_is_said_about_it(self):
        p = _palette.Palette()
        p.light = dict(T.BAKERY_LIGHT)
        report = _palette.check_mark(["#6b2c0b", "#000000"], p)
        self.assertEqual(report.low, {})
        self.assertEqual(report.outside, ["#6b2c0b", "#000000"])


if __name__ == "__main__":
    unittest.main()
