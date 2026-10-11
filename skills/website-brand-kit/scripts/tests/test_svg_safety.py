"""Scenario 13 (and 14, 33): an SVG comes from outside and is served from the owner's own
address, so the intake accepts only drawing elements and attributes on an allowlist and
refuses, by name, what could run or fetch.

Every hostile case is a pair. The hostile file must be refused FOR ITS OWN REASON (a test
that only says "refused" passes when a typo makes the XML unreadable), and the same file
without the hostile part must be accepted (a check that refuses everything passes the
hostile half too). The real SVG from a design tool's handoff package must pass.

Run:  python3 -m unittest discover -s skills/website-brand-kit/scripts/tests
"""

import unittest

import _testutil as T
import _svg

NS = 'xmlns="http://www.w3.org/2000/svg"'
XLINK = 'xmlns:xlink="http://www.w3.org/1999/xlink"'
PATH = '<path fill="#b4531a" d="M10 34A22 22 0 0 1 54 34Z"/>'


def svg(extra="", root="", ns=NS):
    """A small valid mark, with `extra` placed before the path and `root` on the root."""
    return ('<svg %s %s viewBox="0 0 64 64" %s>%s%s</svg>' % (ns, XLINK, root, extra, PATH)).encode()


def refused(testcase, data, code, source="svg"):
    with testcase.assertRaises(_svg.Refusal) as cm:
        _svg.clean_svg(data, source=source)
    testcase.assertEqual(cm.exception.code, code, "refused, but for %r: %s" % (cm.exception.code, cm.exception))
    testcase.assertTrue(len(str(cm.exception)) > 10, "a refusal must say why, in words")
    return cm.exception


class RealMark(unittest.TestCase):
    def test_the_real_colour_mark_and_its_one_colour_twin_pass(self):
        for name in (T.REAL_COLOUR, T.REAL_MONO):
            with self.subTest(name=name):
                clean = _svg.clean_svg(T.real_svg(name))
                self.assertIn("<path", clean.text)
                self.assertIn('viewBox="0 0 64 64"', clean.text)
                self.assertNotIn("<title", clean.text)

    def test_the_cleaned_text_is_what_the_next_step_reads_not_the_original(self):
        # Rebuilt from the allowlisted nodes only: a comment in the original is gone.
        data = svg('<!-- keep out --><metadata>x</metadata>')
        clean = _svg.clean_svg(data)
        self.assertNotIn("keep out", clean.text)
        self.assertNotIn("metadata", clean.text)


class Hostile(unittest.TestCase):
    """Each row: (what it is, the hostile document, the code it must be refused with, a
    control: the same document without the hostile part, which must pass)."""

    def cases(self):
        return [
            ("script element", svg("<script>alert(1)</script>"), "script", svg()),
            ("script in the svg namespace with a src", svg('<script xlink:href="https://x.example/a.js"/>'), "script", svg()),
            ("event attribute on the root", svg(root='onload="alert(1)"'), "event-attribute", svg()),
            ("event attribute on a shape", svg().replace(b"<path ", b'<path onclick="x()" '), "event-attribute", svg()),
            ("an on* attribute in another namespace", svg(root='xlink:onbegin="x()"'), "event-attribute", svg()),
            ("DOCTYPE with an internal entity",
             b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "x">]>' + svg(), "doctype", svg()),
            ("DOCTYPE with an external entity",
             b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]>' + svg(), "doctype", svg()),
            ("a plain public DOCTYPE with no entity at all",
             b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">' + svg(),
             "doctype", svg()),
            ("xml-stylesheet instruction", b'<?xml-stylesheet href="https://x.example/a.css"?>' + svg(), "xml-stylesheet", svg()),
            ("another processing instruction", b'<?php echo 1 ?>' + svg(), "processing-instruction", svg()),
            ("CSS @import with url()", svg('<style>@import url(https://x.example/a.css);</style>'), "css-import", svg('<style>path{fill:#b4531a}</style>')),
            ("CSS @import with a string", svg('<style>@import "a.css";</style>'), "css-import", svg('<style>path{fill:#b4531a}</style>')),
            ("CSS url() to another host", svg('<style>path{fill:url(https://x.example/a)}</style>'), "css-url", svg('<style>path{fill:#b4531a}</style>')),
            ("CSS url() to a local path in a style attribute", svg().replace(b"<path ", b'<path style="fill:url(../a.png)" '), "css-url", svg()),
            ("CSS url() with data:", svg('<style>path{fill:url(data:image/svg+xml;base64,AAAA)}</style>'), "css-url", svg('<style>path{fill:#b4531a}</style>')),
            ("CSS url() with quotes and escapes", svg('<style>path{fill:u\\72l("https://x.example/a")}</style>'), "css-url", svg('<style>path{fill:#b4531a}</style>')),
            ("a link to another host", svg().replace(b"<path ", b'<path xlink:href="https://x.example/a" '), "external-link", svg()),
            ("a link with javascript:", svg().replace(b"<path ", b'<path xlink:href="javascript:alert(1)" '), "external-link", svg()),
            ("a link with an entity-hidden javascript:", svg().replace(b"<path ", b'<path href="&#106;avascript:alert(1)" '), "external-link", svg()),
            ("a link with data:", svg().replace(b"<path ", b'<path href="data:text/html,x" '), "external-link", svg()),
            ("a link to a local path", svg().replace(b"<path ", b'<path href="../secret.svg#a" '), "external-link", svg()),
            ("a link with file://", svg().replace(b"<path ", b'<path href="file:///etc/passwd" '), "external-link", svg()),
            ("a protocol-relative link", svg().replace(b"<path ", b'<path href="//x.example/a" '), "external-link", svg()),
            ("foreignObject", svg('<foreignObject width="10" height="10"><div xmlns="http://www.w3.org/1999/xhtml">x</div></foreignObject>'),
             "foreignObject", svg()),
            ("an XHTML element inside the svg", svg('<html:script xmlns:html="http://www.w3.org/1999/xhtml">x</html:script>'),
             "foreign-html", svg()),
            ("an image element", svg('<image href="#a" width="1" height="1"/>'), "image", svg()),
            ("an anchor element", svg('<a href="#a"><circle r="1"/></a>'), "link-element", svg()),
            ("an animate element that sets href", svg('<animate attributeName="href" values="javascript:alert(1)"/>'), "animation", svg()),
            ("a set element", svg('<set attributeName="href" to="https://x.example"/>'), "animation", svg()),
            ("an animation of colour", svg('<animate attributeName="fill" values="red;blue" dur="1s"/>'), "animation", svg()),
            ("a filter", svg('<filter id="f"><feImage href="https://x.example/a"/></filter>'), "filter", svg()),
            ("a use element", svg('<defs><circle id="c" r="1"/></defs><use href="#c"/>'), "use", svg('<defs><clipPath id="c"><circle r="1"/></clipPath></defs>')),
            ("an unknown element", svg('<blink/>'), "unknown-element", svg()),
            ("a root that is not svg", b'<html xmlns="http://www.w3.org/1999/xhtml"><body/></html>', "not-svg", svg()),
            ("a root in another namespace", svg(ns='xmlns="http://example.com/other"'), "not-svg", svg()),
            ("not XML at all", b"<svg><path></svg>", "not-xml", svg()),
            ("an undefined entity", svg().replace(b"<path ", b'<path data-x="&nope;" '), "not-xml", svg()),
            ("empty input", b"", "not-xml", svg()),
        ]

    def test_each_hostile_file_is_refused_for_its_own_reason_and_its_twin_passes(self):
        for name, hostile, code, control in self.cases():
            with self.subTest(name=name):
                refused(self, hostile, code)
                _svg.clean_svg(control)  # the same document without the hostile part is fine

    def test_text_is_refused_with_the_way_out(self):
        # Scenario 14: the owner is told what to ask the tool for.
        err = refused(self, svg('<text x="0" y="10">Bakery</text>'), "text")
        self.assertIn("shapes", str(err))
        refused(self, svg('<g><tspan>x</tspan></g>'), "text")

    def test_a_fragment_only_link_is_not_an_external_link(self):
        # The rule is "not a same-document #fragment", so a bare fragment on a shape is not
        # the link rule's business (the shape is just given an attribute it drops).
        _svg.clean_svg(svg().replace(b"<path ", b'<path href="#a" '))


class Bombs(unittest.TestCase):
    def test_a_file_over_the_size_cap_is_refused_before_it_is_parsed(self):
        big = svg("<!--" + "a" * (_svg.MAX_BYTES + 1) + "-->")
        refused(self, big, "too-large")

    def test_a_file_just_under_the_cap_is_read(self):
        pad = "<!--" + "a" * 1000 + "-->"
        _svg.clean_svg(svg(pad))

    def test_deep_nesting_is_refused_without_recursing(self):
        deep = svg("<g>" * (_svg.MAX_DEPTH + 5) + "</g>" * (_svg.MAX_DEPTH + 5))
        refused(self, deep, "too-deep")
        # far past anything recursion could survive: still a refusal, not a crash
        refused(self, svg("<g>" * 20000 + "</g>" * 20000), "too-deep")

    def test_a_flood_of_elements_is_refused(self):
        flood = svg('<path d="M0 0"/>' * (_svg.MAX_ELEMENTS + 1))
        refused(self, flood, "too-many-elements")

    def test_a_long_run_of_attributes_on_one_element_is_refused(self):
        many = " ".join('a%d="x"' % i for i in range(_svg.MAX_ATTRIBUTES + 1))
        refused(self, svg().replace(b"<path ", ("<path %s " % many).encode()), "too-many-attributes")


class Size(unittest.TestCase):
    """Scenario 33. Measured on 2026-10-11: with neither a viewBox nor a size the renderer
    cuts the picture (or draws nothing) when the drawing does not start at the origin."""

    def test_a_viewbox_is_enough(self):
        clean = _svg.clean_svg(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 20"><path d="M0 0h1v1z"/></svg>')
        self.assertEqual(clean.view_box, (0.0, 0.0, 10.0, 20.0))

    def test_a_width_and_a_height_without_a_viewbox_are_accepted(self):
        clean = _svg.clean_svg(b'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="30"><path d="M0 0h1v1z"/></svg>')
        self.assertEqual(clean.view_box, (0.0, 0.0, 40.0, 30.0))

    def test_absolute_units_count(self):
        for w, h in (("40px", "30px"), ("4cm", "3cm"), ("1in", "1in"), ("12pt", "12pt"), ("40", "30"), ("4e1", "3e1")):
            with self.subTest(w=w, h=h):
                _svg.clean_svg(('<svg xmlns="http://www.w3.org/2000/svg" width="%s" height="%s"><path d="M0 0h1v1z"/></svg>' % (w, h)).encode())

    def test_neither_is_refused_with_the_reason(self):
        err = refused(self, b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M10 10h5v5z"/></svg>', "no-size")
        self.assertIn("viewBox", str(err))

    def test_a_percentage_is_no_size(self):
        refused(self, b'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><path d="M0 0h1v1z"/></svg>', "no-size")

    def test_only_one_of_width_and_height_is_no_size(self):
        refused(self, b'<svg xmlns="http://www.w3.org/2000/svg" width="64"><path d="M0 0h1v1z"/></svg>', "no-size")

    def test_a_zero_or_negative_box_is_refused(self):
        for vb in ("0 0 0 10", "0 0 10 0", "0 0 -5 5", "0 0 5"):
            with self.subTest(vb=vb):
                refused(self, ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s"><path d="M0 0"/></svg>' % vb).encode(), "bad-view-box")

    def test_a_viewbox_with_a_non_finite_number_is_refused(self):
        refused(self, b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 nan 10"><path d="M0 0"/></svg>', "bad-view-box")


class FromHtml(unittest.TestCase):
    """The same checks apply to an inline <svg> taken out of an HTML page (scenario 17); the
    hostile parts of the page around it are never run, only parsed."""

    def page(self, inner):
        return ('<!doctype html><html><head><script>alert(1)</script></head><body>%s</body></html>' % inner).encode()

    def test_an_inline_svg_without_xmlns_is_serialised_with_it(self):
        html = self.page('<svg viewBox="0 0 64 64"><path fill="#b4531a" d="M10 34A22 22 0 0 1 54 34Z"/></svg>')
        clean = _svg.clean_svg(html, source="html")
        self.assertIn('xmlns="http://www.w3.org/2000/svg"', clean.text)
        self.assertIn('viewBox="0 0 64 64"', clean.text)

    def test_the_hostile_parts_inside_the_svg_are_still_refused(self):
        refused(self, self.page('<svg viewBox="0 0 64 64"><script>alert(1)</script></svg>'), "script", source="html")
        refused(self, self.page('<svg viewBox="0 0 64 64" onload="x()"><path d="M0 0"/></svg>'), "event-attribute", source="html")

    def test_scripts_outside_the_svg_are_not_our_business(self):
        # the page above already carries a <script> in <head>
        _svg.clean_svg(self.page('<svg viewBox="0 0 64 64"><path d="M0 0h1v1z"/></svg>'), source="html")


if __name__ == "__main__":
    unittest.main()
