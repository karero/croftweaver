"""Scenario 13 (and 14, 33): an SVG comes from outside and is served from the owner's own
address, so the intake accepts only drawing elements and attributes on an allowlist and
refuses, by name, what could run or fetch.

Every hostile case is a pair. The hostile file must be refused FOR ITS OWN REASON (a test
that only says "refused" passes when a typo makes the XML unreadable), and the same file
without the hostile part must be accepted (a check that refuses everything passes the
hostile half too). The real SVG from a design tool's handoff package must pass.

Run:  python3 -m unittest discover -s skills/website-brand-kit/scripts/tests
"""

import base64
import encodings.aliases
import json
import subprocess
import sys
import unittest

import _testutil as T
import _css
import _input
import _svg

NS = 'xmlns="http://www.w3.org/2000/svg"'
XLINK = 'xmlns:xlink="http://www.w3.org/1999/xlink"'
PATH = '<path fill="#b4531a" d="M10 34A22 22 0 0 1 54 34Z"/>'


def svg(extra="", root="", ns=NS):
    """A small valid mark, with `extra` placed before the path and `root` on the root."""
    return ('<svg %s %s viewBox="0 0 64 64" %s>%s%s</svg>' % (ns, XLINK, root, extra, PATH)).encode()


def bare(inner, root=""):
    """Like svg(), but `inner` is all the drawing holds."""
    return ('<svg %s %s viewBox="0 0 64 64" %s>%s</svg>' % (NS, XLINK, root, inner)).encode()


def refused(testcase, data, code):
    with testcase.assertRaises(_svg.Refusal) as cm:
        _svg.clean_svg(data)
    testcase.assertEqual(cm.exception.code, code, "refused, but for %r: %s" % (cm.exception.code, cm.exception))
    testcase.assertTrue(len(str(cm.exception)) > 10, "a refusal must say why, in words")
    return cm.exception


# A check that hangs cannot be caught from inside its own process (a regular expression gone
# wrong never hands control back), so the tests about time judge their documents in a child
# process and stop it when the time is up. Each judgement is timed by the work it took (the
# processor's seconds, not the clock's): on a machine busy with other things the clock ran five
# times as long for the same work, and a judgement that hangs is busy the whole time anyway.
_JUDGE = r"""
import base64, json, sys, time
sys.path.insert(0, sys.argv[1])
import _input, _svg
from _refusal import Ask, Refusal
for line in sys.stdin:
    how, data = json.loads(line)
    data = base64.b64decode(data)
    start = time.process_time()
    try:
        if how == "intake":  # the way the intake reads what it is given: say what it is, take the mark out, check it
            clean = _svg.clean_svg(_input.mark(_input.load(data)).colour)
        else:
            clean = _svg.clean_svg(data)
        out = {"code": "ok", "text": clean.text, "notes": clean.notes}
    except (Refusal, Ask) as e:
        out = {"code": e.code}
    except Exception as e:
        out = {"code": "crash: %s: %s" % (type(e).__name__, e)}
    out["seconds"] = time.process_time() - start
    print(json.dumps(out), flush=True)
"""


def judged(testcase, documents, how="svg", each=2.0):
    """What became of each document ({"code": "ok" or the refusal's code, ...}), every one of
    them judged in under `each` seconds: far more than the milliseconds a judgement takes, far
    less than a hang."""
    lines = "".join(json.dumps([how, base64.b64encode(d).decode("ascii")]) + "\n" for d in documents)
    try:
        r = subprocess.run([sys.executable, "-c", _JUDGE, T.SCRIPTS], input=lines.encode("ascii"), capture_output=True,
                           timeout=30 + 5 * each * len(documents))
    except subprocess.TimeoutExpired as e:
        done = len((e.stdout or b"").splitlines())
        testcase.fail("document %d of %d was still being judged when the time ran out" % (done + 1, len(documents)))
    outcomes = [json.loads(line) for line in r.stdout.decode("utf-8").splitlines()]
    testcase.assertEqual(len(outcomes), len(documents), r.stderr.decode("utf-8", "replace")[-400:])
    for i, out in enumerate(outcomes):
        testcase.assertLess(out["seconds"], each, "document %d took %.1f seconds" % (i + 1, out["seconds"]))
    return outcomes


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

    def test_a_refusal_shows_what_it_found_without_the_files_hidden_characters(self):
        # the sentence goes to the owner's terminal: a mark that turns the line round, or a control
        # character, must arrive spelled out, never as itself
        for hidden in ("&#x202e;", "&#x9b;", "&#x7f;", "&#x2066;", "\u200f", "\u200b", "\u200d", "\u2060", "\ufeff", "\u00ad", "\u2062",
                       "\u180e", "\ufff9", "\ue000", "\U000e0041\U000e0042", "\u0378", "\u2028", "\u2029", "\U000f0000"):
            for attrs in ('href="%sgpj.elif//:ptth"', 'stroke-width="%s1"', 'transform="%s"', 'fill="%s"', 'style="fill:%s"'):
                with self.subTest(hidden=hidden, attrs=attrs):
                    with self.assertRaises(_svg.Refusal) as cm:
                        _svg.clean_svg(svg().replace(b"<path ", ("<path %s " % (attrs % hidden)).encode("utf-8")))
                    self.assertTrue(str(cm.exception).isprintable(), ascii(str(cm.exception)))

    def test_a_colour_with_a_number_too_large_to_work_with_is_refused_by_name(self):
        # each of these once ended in a traceback from the arithmetic, not in a sentence
        for value in ("oklch(1e200 0 0)", "hsl(1e308turn 50% 50%)", "rgb(1e308% 0 0)"):
            for shape in ('<path fill="%s" d="M0 0h9v9z"/>', '<path style="fill:%s" d="M0 0h9v9z"/>'):
                with self.subTest(value=value, shape=shape):
                    with self.assertRaises(_svg.Refusal) as cm:
                        _svg.clean_svg(svg(shape % value))
                    self.assertTrue(cm.exception.code.startswith("colour-"), cm.exception.code)
                    self.assertIn(value[:10], str(cm.exception))


class Bombs(unittest.TestCase):
    def test_a_file_over_the_size_cap_is_refused_before_it_is_parsed(self):
        big = svg("<!--" + "a" * (_svg.MAX_BYTES + 1) + "-->")
        refused(self, big, "too-large")

    def test_a_file_just_under_the_cap_is_read(self):
        # both sides of the line: a file of exactly the cap is read, one byte more is not
        room = _svg.MAX_BYTES - len(svg("<!---->"))
        at_cap = svg("<!--" + "a" * room + "-->")
        self.assertEqual(len(at_cap), _svg.MAX_BYTES)
        self.assertEqual(_svg.clean_svg(at_cap).colours, ["#b4531a"])
        over = svg("<!--" + "a" * (room + 1) + "-->")
        self.assertEqual(len(over), _svg.MAX_BYTES + 1)
        refused(self, over, "too-large")

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

    def test_the_cleaned_file_says_its_size_by_its_viewbox_alone(self):
        # width and height would give the renderer a second idea of the size; one is enough
        for tag in ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">',
                    '<svg xmlns="http://www.w3.org/2000/svg" width="4cm" height="3cm">'):
            clean = _svg.clean_svg((tag + '<path fill="#111111" d="M0 0h9v9z"/></svg>').encode())
            root = clean.text.split(">", 1)[0]
            self.assertIn("viewBox=", root)
            self.assertNotIn("width=", root)
            self.assertNotIn("height=", root)
        self.assertIn('viewBox="0 0 151.181102 113.385827"', clean.text)

    def test_a_box_too_small_or_too_big_to_be_a_logo_is_refused(self):
        for vb in ("0 0 1e9 1e9", "0 0 0.0000001 0.0000001", "0 0 1e7 5"):
            with self.subTest(vb=vb):
                refused(self, ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s"><path fill="#111111" d="M0 0"/></svg>' % vb).encode(), "bad-view-box")

    def test_a_box_far_wider_than_it_is_tall_is_no_logo(self):
        # the renderer sizes a drawing in whole pixels: a hair-thin box would come out zero pixels tall
        ok = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 5"><path fill="#111111" d="M0 0h9v9z"/></svg>'
        _svg.clean_svg(ok.encode())
        _svg.clean_svg(ok.replace("0 0 100 5", "0 0 5 100").encode())
        for vb in ("0 0 100 4", "0 0 4 100", "0 0 1000 0.001"):
            with self.subTest(vb=vb):
                refused(self, ok.replace("0 0 100 5", vb).encode(), "bad-view-box")

    def test_a_viewbox_with_a_non_finite_number_is_refused(self):
        refused(self, b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 nan 10"><path d="M0 0"/></svg>', "bad-view-box")

    def test_a_viewbox_is_four_plain_numbers_not_whatever_python_would_read_as_one(self):
        # a renderer reads none of these as a number, so the box this check works with would not be the renderer's
        doc = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s"><path fill="#111111" d="M0 0h9v9z"/></svg>'
        for vb in ("0 0 1_0 1_0", "0 0 \u0661\u0660 \u0661\u0660", "0 0 \uff11\uff10 10", "0 0 1e1_0 10", "0 0 0x10 10",
                   "0 0 infinity 10", "0 0 Infinity 10", "0 0 1e999 10", "0 0 10 10 10", "0 0 10;10",
                   # a point with no digit after it, or a space that is not a plain one: the site's renderer then
                   # drops the whole viewBox (measured 2026-10-12), so the box read here would not be the one drawn
                   "+0 -0 10. 10", "0. 0 10 10", "0 0 10 10.e0", "0\u20030 10 10", "0 0\u00a010 10", "\u30000 0 10 10", "0 0 10 10\u2028"):
            with self.subTest(vb=vb):
                refused(self, (doc % vb).encode("utf-8"), "bad-view-box")
        for vb, box in (("0,0,10,10", (0, 0, 10, 10)), (" 0  0 1e1 .5e1 ", (0, 0, 10, 5)), ("+0 -0 10.0 10", (0, 0, 10, 10)),
                        ("0 0\t10\n10", (0, 0, 10, 10)), ("-5 -5.5 2.5E1 25", (-5, -5.5, 25, 25))):
            with self.subTest(vb=vb):
                self.assertEqual(_svg.clean_svg((doc % vb).encode("utf-8")).view_box, box)


class Numbers(unittest.TestCase):
    """A number is read as a renderer reads it, left to right in one pass. A value that is almost
    a number must be refused at once however long it is (before 2026-10-12 some of these hung
    the check and the rest took seconds), and what is kept is plain ASCII, with no sign where a
    size cannot have one."""

    def shape(self, attrs):
        return svg("<rect %s/>" % attrs)

    def test_a_value_that_is_almost_a_number_is_refused_at_once_however_long_it_is(self):
        hostile = [
            'points="%sx"' % ("1" * 40),
            'points="100,200 300,400 500,600 700,800 900,1000 1100,1200px"',
            'points="%sx"' % ("1" * 200000),
            'points="%sx"' % ("1." * 30),
            'points="%s-"' % ("-1e1" * 30),
            'stroke-dasharray="%sx"' % ("1" * 24),
            'stroke-dasharray="%sx"' % ("1%" * 30),
            'style="stroke-dasharray:%sx"' % ("1 " * 30),
            'width="%sx"' % ("1" * 16000),
            'stroke-width="%sx"' % ("1" * 100000),
            'style="stroke-width:%sx"' % ("1" * 100000),
            'x="1.%sx"' % ("1" * 16000),
            'r="1e%sx"' % ("1" * 16000),
            'opacity="%sx"' % ("1" * 16000),
            'fill-opacity="%s%%x"' % ("1" * 16000),
            'stroke-miterlimit="%s-"' % ("1" * 16000),
            'transform="matrix()%sx"' % (" " * 16000),
            'transform="%sx"' % ("scale(1) " * 40000),
            'transform="rotate(%s"' % ("1 " * 100000),
            'd="M0 0%sx"' % (" 1" * 50000),
        ]
        outcomes = judged(self, [self.shape(attrs) for attrs in hostile])
        for attrs, out in zip(hostile, outcomes):
            self.assertEqual(out["code"], "bad-value", attrs[:60])

    def test_a_long_honest_value_is_read_just_as_fast(self):
        honest = ['points="%s"' % ("1.5,-2e1 " * 40000), 'stroke-dasharray="%s"' % ("4 2 " * 50000), 'transform="%s"' % ("scale(1) " * 40000),
                  'd="M0 0%s"' % (" 1" * 90000), 'width="%s"' % ("1" * 100000)]
        for attrs, out in zip(honest, judged(self, [self.shape(attrs) for attrs in honest])):
            self.assertEqual(out["code"], "ok", attrs[:60])

    def test_numbers_written_the_ways_tools_write_them_are_still_read(self):
        # run together without a space, a bare dot, a sign, an exponent: all of it is SVG
        fine = ['points="10-20,3.5.5 1e2,4"', 'points=""', 'stroke-dasharray="4 2"', 'stroke-dasharray="4,2"', 'stroke-dasharray="none"',
                'stroke-dasharray="50% 2"', 'width="1.0" height=".5"', 'x="+3" y="-3"', 'width="1e2"', 'width="4.5px"', 'rx="auto"',
                'transform="translate(1,2) scale(2)"', 'transform="rotate(45 1 1),scale(2)"', 'transform="translate(-1.5e1-2)"',
                'transform="matrix(1 0 0 1 0 0)"', 'stroke-miterlimit="4"', 'stroke-dashoffset="-2"']
        for attrs in fine:
            with self.subTest(attrs=attrs):
                self.assertIn(attrs.split('" ')[0].rstrip('"') + '"', _svg.clean_svg(self.shape(attrs)).text)
        self.assertIn('points="1 2,3 4"', _svg.clean_svg(self.shape('points=" 1 2,3 4 "')).text)

    def test_only_ascii_digits_are_numbers(self):
        # "٠" is ARABIC-INDIC DIGIT ZERO: Python's \d and float() take it, a renderer does not, and
        # then falls back to its default (a stroke one unit wide) while this check read "no stroke"
        for attrs in ('stroke-width="٠"', 'stroke-width="٣"', 'style="stroke-width:٠"', 'width="１０"', 'x="١"',
                      'r="۵"', 'points="١,٢"', 'stroke-dasharray="٤ ٢"', 'opacity="١"',
                      'stroke-miterlimit="٤"', 'stroke-width="1٠"', 'width="1e٢"'):
            with self.subTest(attrs=attrs):
                refused(self, self.shape(attrs + ' stroke="#ff0000"'), "bad-value")

    def test_a_point_is_followed_by_a_digit_everywhere_but_in_path_data(self):
        # Measured with the site's renderer on 2026-10-12: it reads `5.` as a number in path data only. A width or
        # a radius of `5.` draws nothing, a stroke-width of `0.` (read here as "no stroke") draws one unit wide,
        # a viewBox with one is dropped whole. So what a renderer does not read is not read here either.
        for form in ("5.", "0.", "5.e0", "0.e0", "+5.", "5.px", "5.%", "-.", ".", "5..0", "5.e", ".e1"):
            for attrs in ('stroke-width="%s"', 'style="stroke-width:%s"', 'width="%s"', 'height="%s"', 'x="%s"', 'y="%s"', 'rx="%s"',
                          'stroke-miterlimit="%s"', 'stroke-dashoffset="%s"', 'style="stroke-dashoffset:%s"', 'pathLength="%s"',
                          'opacity="%s"', 'fill-opacity="%s"', 'style="stroke-opacity:%s"', 'stroke-dasharray="%s"',
                          'stroke-dasharray="4 %s"', 'style="stroke-dasharray:%s 4"', 'transform="translate(%s)"',
                          'transform="rotate(45) scale(1 %s)"', 'transform="matrix(1 0 0 1 %s 0)"'):
                with self.subTest(form=form, attrs=attrs):
                    refused(self, self.shape(attrs % form + ' stroke="#ff0000"'), "bad-value")
            for inner in ('<circle r="%s"/>', '<circle cx="%s" r="3"/>', '<ellipse rx="3" ry="%s"/>', '<line x2="%s"/>',
                          '<polygon points="0,0 %s,0 9,9"/>', '<polyline points="%s,%s 9.,9."/>', "<style>rect{stroke-width:%s}</style><rect/>"):
                with self.subTest(form=form, inner=inner):
                    refused(self, svg(inner.replace("%s", form)), "bad-value")
        refused(self, b'<svg xmlns="http://www.w3.org/2000/svg" width="40." height="30"><path d="M0 0h1v1z"/></svg>', "bad-value")
        # in a colour as well: `rgb(255.,0,0)` was read as red, and the renderer paints it black
        for value in ("rgb(255.,0,0)", "rgb(255. 0 0)", "rgb(100.%,0%,0%)", "rgba(255,0,0,1.)", "hsl(0.,100%,50%)", "rgb(0,0,255.)", "rgb(1.e2,0,0)", "red."):
            for attrs in ('fill="%s"', 'stroke="%s"', 'color="%s"', 'style="fill:%s"'):
                with self.subTest(value=value, attrs=attrs):
                    refused(self, self.shape(attrs % value), "bad-value")
        self.assertEqual(_svg.clean_svg(bare('<rect fill="rgb(255.0,.0,0.0)" width="9" height="9"/>')).colours, ["#ff0000"])
        # in path data it is a number, to the renderer and so to this check, and is kept as it is written
        self.assertIn('d="M0. 0.h5.v5.e0z"', _svg.clean_svg(svg('<path fill="#111111" d="M0. 0.h5.v5.e0z"/>')).text)
        # and every other way of writing a number is still read
        for attrs in ('width="5.0"', 'height="05"', 'stroke-width="5e0"', 'stroke-width=".5e1"', 'x="+5"', 'y="-.5"', 'transform="translate(5.0,.5)"',
                      'stroke-dasharray="5.0 .5"', 'stroke-miterlimit="4.0"'):
            with self.subTest(attrs=attrs):
                self.assertIn(attrs, _svg.clean_svg(self.shape(attrs)).text)
        _svg.clean_svg(self.shape('opacity="1.0" fill-opacity="100.0%"'))

    def test_each_dash_is_a_number_or_a_percentage_of_its_own(self):
        # every "%" used to be taken out before the list was read, so `5%10%` was checked as the number 510
        for value in ("5%%", "%", "%5", "5 %", "5%%10", "1 2 %", "5%px", "%%", "5%.", "5.%"):
            with self.subTest(value=value):
                refused(self, self.shape('stroke-dasharray="%s" stroke="#ff0000"' % value), "bad-value")
                refused(self, self.shape('style="stroke-dasharray:%s" stroke="#ff0000"' % value), "bad-value")
        # the site's renderer reads `50%10%` as the two dashes it reads in `50% 10%` (measured 2026-10-12)
        for value in ("5%10%", "5% 10%", "5%,10%", "50% 2", "1%2", ".5%", "4 2", "4,2", "none", ""):
            with self.subTest(value=value):
                self.assertIn('stroke-dasharray="%s"' % value, _svg.clean_svg(self.shape('stroke-dasharray="%s" stroke="#ff0000"' % value)).text)

    def test_only_a_plain_space_is_a_space(self):
        # Python's strip(), split() and \s take a no-break space, an em space, a line separator; a renderer does not.
        # Taken off here, each of these gave a value the check read one way and the renderer another: a fill of
        # "(no-break space)red" was read as red and is drawn black.
        for space in ("\u00a0", "\u2003", "\u3000", "\u2028", "\u0085", "\u1680", "\u202f"):
            for attrs in ('fill="%sred"', 'fill="red%s"', 'stroke="#ff0000%s"', 'fill="rgb(255,%s0,0)"', 'style="fill:%sred"',
                          'style="fill:red%s"', 'stroke-width="%s2"', 'stroke-width="2%s"', 'width="9%s"', 'opacity="%s1"',
                          'visibility="%shidden"', 'display="none%s"', 'fill-rule="%sevenodd"', 'clip-path="%snone"', 'stroke-dasharray="4%s2"',
                          'transform="translate(1%s2)"', 'transform="%sscale(2)"', 'transform="scale%s(2)"', 'class="%sa"',
                          'class="a%sb"', 'id="%sa"', 'id="a%s"', 'paint-order="stroke%sfill"'):
                with self.subTest(space=ascii(space), attrs=attrs):
                    refused(self, self.shape(attrs % space), "bad-value")
            for inner in ('<polygon points="0,0%s9,0 9,9"/>', '<polygon points="%s0,0 9,0 9,9"/>', '<path d="M0%s0h9v9z"/>', '<path d="%sM0 0h9v9z"/>'):
                with self.subTest(space=ascii(space), inner=inner):
                    refused(self, svg(inner % space), "bad-value")
            # inside url() such a space is part of an address: the link would no longer be one into the drawing
            for attrs in ('clip-path="url(%s#c)"', 'clip-path="url(#c%s)"', 'style="clip-path:url(%s#c)"', 'fill="url(%s#c)"'):
                with self.subTest(space=ascii(space), attrs=attrs):
                    refused(self, self.shape(attrs % space), "css-url")
        # the plain ones, around a value and inside it, are read as before
        for attrs in ('fill=" red "', 'fill="rgb(255, 0,\t0)"', 'stroke-width=" 2 "', 'transform=" translate(1 2) "', 'class=" a  b "',
                      'clip-path=" none "', 'visibility=" hidden "'):
            with self.subTest(attrs=attrs):
                _svg.clean_svg(self.shape(attrs))
        refused(self, self.shape('fill=" &#10;&#13;&#9;"'), "bad-value")
        self.assertEqual(_svg.clean_svg(bare('<rect fill="&#10;red&#13;&#9;" width="9" height="9"/>')).colours, ["#ff0000"])

    def test_a_colour_is_written_in_ascii(self):
        # Python's \w takes any script's letters and digits: `rgb(١٢٣,0,0)` reached the colour reader and came
        # back as #7b0000, where the site's renderer reads no colour at all and paints black
        for value in ("rgb(\u0661\u0662\u0663,0,0)", "rgb(\uff11,0,0)", "\uff52\uff45\uff44", "r\u00e9d", "#\uff11\uff12\uff13", "#12345\u0666",
                      "re\u0434", "hsl(\u0968 50% 50%)", "\u00b2", "red\u0301", "\u212aed"):
            for shape in ('fill="%s"', 'stroke="%s"', 'color="%s"', 'style="fill:%s"', 'style="stroke:%s"'):
                with self.subTest(value=ascii(value), shape=shape):
                    refused(self, self.shape(shape % value), "bad-value")
            refused(self, svg("<style>rect{fill:%s}</style><rect/>" % value), "bad-value")
        for value, colour in (("red", "#ff0000"), ("RED", "#ff0000"), ("rgb(1,2,3)", "#010203"), ("#123", "#112233")):
            self.assertIn(colour, _svg.clean_svg(bare('<rect fill="%s" width="9" height="9"/>' % value)).colours)

    def test_a_size_below_zero_is_refused_by_name(self):
        for name in ("stroke-width", "r", "rx", "ry", "width", "height"):
            for value in ("-1", "-0.5", " -2 ", "-1e3", "-.5px", "-0"):
                with self.subTest(name=name, value=value):
                    err = refused(self, self.shape('%s="%s" stroke="#ff0000"' % (name, value)), "negative-size")
                    self.assertIn(name, str(err))
        refused(self, self.shape('style="stroke-width:-1" stroke="#ff0000"'), "negative-size")
        refused(self, svg("<style>rect{stroke-width:-1}</style><rect/>"), "negative-size")
        # a position may be below zero, and a size may be nothing or carry a plus
        for attrs in ('x="-5" y="-5"', 'cx="-1" cy="-1"', 'x1="-1" y2="-3"', 'stroke-width="0"', 'stroke-width="+1"', 'r="0"', 'width="+9" height="9"'):
            with self.subTest(attrs=attrs):
                _svg.clean_svg(self.shape(attrs))


class OuterSvg(unittest.TestCase):
    """The cleaned file's outer <svg> carries its namespace, its viewBox and its paint, nothing
    else. Whatever that leaves behind must not change the drawing without a word."""

    def test_a_transform_on_the_outer_svg_is_refused_because_the_cleaned_file_would_lose_it(self):
        for value in ("translate(20 20)", "scale(2)", " rotate(45) ", "matrix(1 0 0 1 5 5)", "translate(0)"):
            with self.subTest(value=value):
                err = refused(self, svg(root='transform="%s"' % value), "root-transform")
                self.assertIn("outer", str(err))
                self.assertIn(value.strip(), str(err))
        # the same transform on a group inside is part of the drawing and is kept
        self.assertIn('<g transform="translate(20 20)">', _svg.clean_svg(svg('<g transform="translate(20 20)"><path d="M0 0h1v1z"/></g>')).text)
        # and an empty one loses nothing
        self.assertEqual(_svg.clean_svg(svg(root='transform=" "')).notes, [])

    def test_x_y_and_id_on_the_outer_svg_are_left_out_and_said(self):
        clean = _svg.clean_svg(svg(root='x="5" y="6" id="logo"'))
        root = clean.text.split(">", 1)[0]
        for attr in (" x=", " y=", " id="):
            self.assertNotIn(attr, root)
        for word in ("x of the outer", "y of the outer", "id of the outer"):
            self.assertEqual(len([n for n in clean.notes if word in n]), 1, clean.notes)
        self.assertEqual(_svg.clean_svg(svg()).notes, [], "a file that loses nothing has nothing to say")


class Encodings(unittest.TestCase):
    """The XML parser reads a few encodings itself and asks Python for the rest; what Python
    cannot give it came back as a ValueError, a LookupError or a UnicodeError, not as a sentence."""

    def doc(self, encoding):
        return ('<?xml version="1.0" encoding="%s"?>' % encoding).encode("ascii") + svg()

    def test_an_encoding_the_parser_cannot_read_is_a_refusal_not_a_crash(self):
        for encoding in ("utf-7", "UTF-7", "big5", "shift_jis", "utf-32", "x-nope", "rot13", "idna", "hex", "base64", "undefined", "punycode"):
            with self.subTest(encoding=encoding):
                refused(self, self.doc(encoding), "not-xml")
        self.assertIn("UTF-8", str(refused(self, self.doc("utf-7"), "not-xml")))
        for encoding in ("utf-8", "UTF-8", "iso-8859-1", "us-ascii", "windows-1252"):
            with self.subTest(encoding=encoding):
                self.assertEqual(_svg.clean_svg(self.doc(encoding)).colours, ["#b4531a"])

    def test_every_encoding_python_knows_ends_in_a_result_or_a_refusal(self):
        for encoding in sorted(set(encodings.aliases.aliases.values())):
            with self.subTest(encoding=encoding):
                try:
                    _svg.clean_svg(self.doc(encoding))
                except _svg.Refusal as e:
                    self.assertTrue(len(str(e)) > 10)


class Notes(unittest.TestCase):
    """What is left out is said, but a file cannot make the list long: before 2026-10-12 every
    element said it again for every declaration (a 22 KB file made four million notes)."""

    def test_the_same_thing_left_out_many_times_is_said_once(self):
        shape = '<path style="font-family:Arial;cursor:pointer" extra="1" fill="#111111" d="M0 0h9v9z"/><x:guide xmlns:x="urn:editor"/>'
        clean = _svg.clean_svg(svg(shape * 50))
        self.assertEqual(len(clean.notes), len(set(clean.notes)))
        self.assertEqual(len(clean.notes), 4, clean.notes)
        for word in ("font-family", "cursor", "extra", "guide"):
            self.assertEqual(len([n for n in clean.notes if word in n]), 1, clean.notes)

    def test_a_rule_every_element_matches_is_said_once_not_once_for_each_element(self):
        rule = "path{%s}" % ";".join("cursor:c%d" % i for i in range(_svg.MAX_DECLARATIONS))
        clean = _svg.clean_svg(svg("<style>%s</style>" % rule + '<path d="M0 0"/>' * 2000))
        self.assertEqual(len(clean.notes), 1, clean.notes[:3])

    def test_the_list_of_notes_stays_short_however_much_a_file_leaves_out(self):
        many = "".join('<x:e%d xmlns:x="urn:editor"/>' % i for i in range(500))
        clean = _svg.clean_svg(svg(many))
        self.assertEqual(len(clean.notes), _svg.MAX_NOTES + 1)
        self.assertIn("more was left out", clean.notes[-1])
        # nor can one note be made long by a long name
        clean = _svg.clean_svg(svg().replace(b"<path ", ("<path %s='1' " % ("a" * 100000)).encode()))
        self.assertEqual(len(clean.notes), 1)
        self.assertLess(len(clean.notes[0]), 200)


class Css(unittest.TestCase):
    """This reader of CSS and a renderer must agree where a comment, a string and an escape begin
    and end. Where they could disagree, the file is refused: the text is checked both with its
    comments and without them, and it is split before its escapes are decoded, never after."""

    OUTSIDE = "url(https://x.example/a)"

    def css_refused(self, text, code):
        with self.assertRaises(_svg.Refusal) as cm:
            _css.check_text(text)
        self.assertEqual(cm.exception.code, code, text)
        return cm.exception

    def test_a_url_cannot_hide_where_only_this_reader_sees_a_comment(self):
        for text in ("\\2f * %s", "\\2f\\2a %s", "\\2F  * %s", '"/*" %s "*/"', "'/*' %s '*/'", '\\" " /* " %s "*/', '"a\\"/*" %s "*/"',
                     "url(#a/*) %s /**/)", "u\\72l(#a/*) %s /**/)", "/* a */ %s /* b */", "/* a %s"):
            with self.subTest(text=text):
                self.css_refused(text % self.OUTSIDE, "css-url")
        # and through the whole check, in a style element and in a style attribute
        refused(self, svg('<style>path{font-family:"/*";fill:%s;font-size:"*/"}</style>' % self.OUTSIDE), "css-url")
        refused(self, svg().replace(b"<path ", b'<path style="stroke:\\2f * url(https://x.example/a)" '), "css-url")
        for text in ("/* a plain comment */ #b4531a", "url(#a)", 'url("#a")', "url( '#a-b.c:d' )", '"a /* b" red', "/* url(#a) */", "a \\"):
            with self.subTest(text=text):
                _css.check_text(text)

    def test_a_url_is_a_plain_fragment_and_nothing_else(self):
        for text in ("url(#a b)", "url(#a", "url(#a/*x*/)", 'url("#a" x)', 'url("#a)', "url()", "url( )", "URL(https://x.example/a)",
                     "url (https://x.example/a)", "url(//x.example/a#a)", "url\\28 https://x.example/a)",
                     # an escaped bracket or quote is part of the address, so none of these is the fragment it decodes to
                     "url(#a\\29 https://x.example/a)", "url(\\22#a\\22)", "u\\72l(\\22#a\\22)", "url('#a\\27 x')"):
            with self.subTest(text=text):
                self.css_refused(text, "css-url")
        for text in ("url(#\\61 )", "u\\72 l(#a)", "URL( #Ebene_1 )"):
            with self.subTest(text=text):
                _css.check_text(text)

    def test_a_carriage_return_with_its_line_feed_after_an_escape_is_one_blank(self):
        # CSS takes CR LF for one line break, and one blank after a hex escape belongs to the escape. Read as
        # "escape, CR" with a line feed left over, the word was cut in two here and whole to a renderer.
        end = "\r\n"
        for text, code in (("u\\72%sl(https://x.example/a)", "css-url"), ("@im\\70%sort 'https://x.example/a'", "css-import"),
                           ("image-\\73%set('https://x.example/a' 1x)", "css-url"), ("java\\73%script:alert(1)", "css-script"),
                           ("\\75%srl(https://x.example/a)", "css-url"), ("ur\\6c%s(https://x.example/a)", "css-url"),
                           ("ur\\6C%s(https://x.example/a)", "css-url"), ("U\\52%sL(https://x.example/a)", "css-url"),
                           ("u\\000072%sl(https://x.example/a)", "css-url"), ("u\\72%s\\6c%s(https://x.example/a)", "css-url"),
                           ("@\\69%smport url(a.css)", "css-import"), ("@\\000049%sMPORT 'a.css'", "css-import"),
                           ("s\\72%sc('a.png')", "css-url"), ("im\\61%sge('a.png')", "css-url"), ("-webkit-im\\000061%sge-set('a.png' 1x)", "css-url"),
                           ("expr\\65%sssion(1)", "css-script"), ("-moz-bindin\\67%s:url(#a)", "css-script"), ("behavio\\72%s:x", "css-script"),
                           ("url(#a\\29%shttps://x.example/a)", "css-url")):
            for blank in (end, "\n", "\r", " ", "\t", "\f"):  # each of them is the one blank that belongs to the escape
                with self.subTest(text=text, blank=ascii(blank)):
                    self.css_refused(text.replace("%s", blank), code)
        # through the whole check: a character reference is how a file carries a carriage return past the XML parser
        refused(self, svg().replace(b"<path ", b'<path style="fill:u\\72&#13;&#10;l(https://x.example/a)" '), "css-url")
        refused(self, svg("<style>path{fill:u\\72&#13;&#10;l(https://x.example/a)}</style>"), "css-url")
        refused(self, svg("<style>@im\\70&#13;&#10;ort 'a.css';</style>"), "css-import")
        # one blank, not two: a second line break does end the word
        for text in ("@im\\70\r\n\nort 'a.css'", "java\\73\r\n\r\ncript:alert(1)", "url(#\\61\r\n)", "u\\72\r\nl(#a)"):
            with self.subTest(text=ascii(text)):
                _css.check_text(text)

    def test_a_picture_loaded_without_url_is_refused_by_name(self):
        for text in ('image-set("https://x.example/a" 1x)', "image(https://x.example/a)", 'src("https://x.example/a")', 'IMAGE-SET("a.png" 1x)',
                     '-webkit-image-set("a.png" 1x)', 'image\\28 "a.png")', 'i\\6d age("a.png")', 'fill:image("a.png")', "/* x */src('a')"):
            with self.subTest(text=text):
                self.assertIn("image()", str(self.css_refused(text, "css-url")))
        refused(self, svg('<style>path{fill:image-set("https://x.example/a" 1x)}</style>'), "css-url")
        refused(self, svg().replace(b"<path ", b'<path style="fill:image(a.png)" '), "css-url")
        # a word that only looks like one of them is not one
        for text in ("Image (2)", "feImage", "an image, (old)", "mysrc(1)", "bgimage(2)", "src"):
            with self.subTest(text=text):
                _css.check_text(text)
        # nor is a longer word that ends in one: these were refused as "loads a picture", which they do not
        for text in ("background-image(#a)", "mask-image(", "border-image(1)", "x-src(1)", "list-style-image(2)", "--image(1)",
                     "-image(1)", "a-image-set(1)", "my_image(1)", "data-src(1)", "BACKGROUND-IMAGE(1)"):
            with self.subTest(text=text):
                _css.check_text(text)
        # the three themselves stay refused wherever they stand, with a browser's own prefix too
        for text in ("image(a)", " image-set(a 1x)", ":src(a)", ",image(a)", "(image(a))", "-webkit-image-set(a 1x)", "-moz-image-set(a)",
                     "-webkit-image(a)", "-o-src(a)", "fill:-WEBKIT-IMAGE-SET(a)", "a -webkit-image-set(a)", "background-image:image(a)",
                     "mask-image: image-set(a 1x)"):
            with self.subTest(text=text):
                self.css_refused(text, "css-url")

    def test_a_comment_that_names_an_import_or_a_picture_is_refused_with_the_rest(self):
        # kept, deliberately: it fails closed, and a logo's style sheet has no reason to say either
        self.css_refused("/* @import */ fill:red", "css-import")
        self.css_refused("/* image(x) */", "css-url")
        refused(self, svg("<style>/* no @import here */ path{fill:#b4531a}</style>"), "css-import")
        _css.check_text("/* a plain comment about the import of flour */")

    def test_a_rule_that_matches_no_element_is_checked_all_the_same(self):
        refused(self, svg("<style>.unused{behavior-x:1}</style>"), "css-property")
        refused(self, svg("<style>.unused{fill:nonsense!!}</style>"), "bad-value")
        refused(self, svg("<style>#nobody{mix-blend-mode:multiply}</style>"), "blend")
        refused(self, svg("<style>circle{stroke-width:-1}</style>"), "negative-size")
        self.assertEqual(len([n for n in _svg.clean_svg(svg("<style>.unused{font-family:Arial}</style>")).notes if "font-family" in n]), 1)
        clean = _svg.clean_svg(svg("<style>.unused{fill:#123456}</style>"))
        self.assertEqual((clean.colours, clean.notes), (["#b4531a"], []))

    def test_a_backslash_cannot_change_which_elements_a_rule_matches_or_which_property_it_sets(self):
        two = '<rect class="a" width="9" height="9"/><rect class="b" width="9" height="9"/>'
        for rule in (".a\\2e b{fill:#f00}", ".a\\,b{fill:#f00}", "\\2e a{fill:#f00}", "re\\63t{fill:#f00}", "#\\61{fill:#f00}",
                     "rect\\7b fill:#f00\\7d", ".a{fill:#f00\\7d .b{fill:#00f}"):
            with self.subTest(rule=rule):
                with self.assertRaises(_svg.Refusal) as cm:
                    _svg.clean_svg(bare("<style>%s</style>" % rule + two))
                self.assertIn(cm.exception.code, ("css-unreadable", "bad-value"), str(cm.exception))
        for rule in (".a\\2e b{fill:#f00}", ".a\\,b{fill:#f00}"):
            refused(self, bare("<style>%s</style>" % rule + two), "css-unreadable")
        for style in ("fi\\6cl:#f00", "fill\\3a #f00", "\\66ill:#f00", "fill:#f00;str\\6fke:#00f"):
            with self.subTest(style=style):
                refused(self, bare('<rect style="%s" width="9" height="9"/>' % style), "css-unreadable")
        # a ";" hidden in an escape ends no declaration: the rule is refused whole, the second fill never applied
        refused(self, bare('<style>rect{fill:red\\3b fill:#00f}</style><rect width="9" height="9"/>'), "css-unreadable")

    def test_a_backslash_in_a_value_is_refused_not_decoded(self):
        # Decoded, an escaped "#", bracket, comma or digit became structure: `fill:\23 f00` was read as #ff0000 and
        # written into the cleaned file, where the site's renderer reads no colour in it and paints black (and
        # `clip-path:url\28 #c\29 ` clipped a shape the original leaves whole). So no value is decoded any more.
        clip = '<defs><clipPath id="c"><rect width="4" height="9"/></clipPath></defs>'
        for value in ("fill:\\23 f00", "fill:rgb\\28 255,0,0\\29 ", "fill:rgb(255\\2c 0\\2c 0)", "stroke-width:\\30 ", "clip-path:url\\28 #c\\29 ",
                      "fill:#\\66 00", "fill:r\\65 d", "fill:\\72 ed", "fill:red\\", "fill:re\\d", "fill:#f\\30 0", "opacity:\\31 ", "display:n\\6f ne",
                      "visibility:hidd\\65 n", "stroke:#00f\\20 ", "stroke-dasharray:4\\20 2", "fill-rule:even\\6f dd", "color:\\23 f00",
                      "paint-order:str\\6f ke", "font-family:Ari\\61 l", "cursor:\\70ointer", "fill:#f00;font-family:a\\,b"):
            for doc in (bare(clip + "<style>rect{%s}</style>" % value + '<rect width="9" height="9"/>'),
                        bare(clip + '<rect style="%s" width="9" height="9"/>' % value)):
                with self.subTest(value=value, doc=doc[-60:]):
                    self.assertIn("backslash", str(refused(self, doc, "css-unreadable")))
        # inside quotes a backslash changes nothing this check reads: a font's name is left out as before
        for value in ('font-family:"A\\42 C"', "font-family:'it\\'s'", 'font-family:"a\\\\"', '-inkscape-font-specification:"a\\"b"'):
            with self.subTest(value=value):
                clean = _svg.clean_svg(bare("<style>rect{%s;fill:#00f}</style>" % value + '<rect width="9" height="9"/>'))
                self.assertEqual(clean.colours, ["#0000ff"])
                self.assertEqual(_svg.clean_svg(bare("<rect style='%s;fill:#00f' width='9' height='9'/>" % value.replace("'", "&#39;"))).colours, ["#0000ff"])

    def test_quotes_and_brackets_cannot_hide_where_a_rule_or_a_value_ends(self):
        # This reader cuts a style sheet at every brace and a rule at every semicolon. A renderer does not cut inside
        # quotes or brackets, so `g{font-family:"} path{fill:#f00} g{font-family:"}` is ONE rule on g to it (the path
        # stays as it was) and was three rules here: the cleaned path came out red.
        shape = '<g><rect width="9" height="9"/></g>'
        sheets = ['g{font-family:"} rect{fill:#f00} g{font-family:"}', "g{font-family:'} rect{fill:#f00} g{font-family:'}",
                  'g{font-family:"a\\"} rect{fill:#f00} g{font-family:"}', "g{font-family:'a\\'} rect{fill:#f00} g{font-family:'}",
                  'rect{font-family:"a;fill:#f00;cursor:b"}', "rect{font-family:'a;fill:#f00;cursor:b'}", 'rect{font-family:"a\\";fill:#f00;cursor:"}',
                  'g{font-family:"a&#13;/*"} rect{fill:#f00} g{font-family:"*/"}', 'g{font-family:"a&#10;"} rect{fill:#f00}',
                  'rect{font-family:"abc;fill:#f00}', "rect{font-family:abc';fill:#f00}", 'g{font-family:"}"} rect{fill:#f00}',
                  "g{cursor:x(} rect{fill:#f00} g{cursor:)}", "rect{cursor:x(a;fill:#f00;cursor:b)}", "rect{cursor:x((a);fill:#f00;cursor:b)}",
                  "rect{cursor:[a;fill:#f00;cursor:b]}", "g{cursor:[} rect{fill:#f00} g{cursor:]}", "rect{cursor:x(a;fill:#f00}",
                  "rect{cursor:a);fill:#f00}", "rect{fill:#f00;cursor:x(}", 'g{cursor:x("} rect{fill:#f00} g{cursor:")}']
        for sheet in sheets:
            with self.subTest(sheet=sheet):
                refused(self, bare("<style>%s</style>" % sheet + shape), "css-unreadable")
        styles = ['font-family:"a;fill:#f00;cursor:b"', "font-family:'a;fill:#f00;cursor:b'", 'font-family:"a\\";fill:#f00;cursor:"',
                  'font-family:"a;fill:#f00', "font-family:a';fill:#f00", "cursor:x(a;fill:#f00;cursor:b)", "cursor:[a;fill:#f00;cursor:b]",
                  "cursor:{a;fill:#f00;cursor:b}", "cursor:x(a;fill:#f00", "fill:#f00;cursor:a)", "cursor:a};fill:#f00", "cursor:{;fill:#f00",
                  'font-family:"a{b"', "font-family:'a}b'"]
        for style in styles:
            with self.subTest(style=style):
                attr = "style='%s'" % style.replace("'", "&#39;")
                refused(self, bare("<rect %s width='9' height='9'/>" % attr), "css-unreadable")
        # quotes and brackets that hide nothing are read as before: a font's name is left out and said, a colour is read
        for style in ('font-family:"Helvetica Neue"', "-inkscape-font-specification:'DejaVu Sans, Bold'", 'font-family:"a:b (c) [d], e"',
                      "font-family:'Caf\u00e9 \u2013 \u65e5\u672c'", 'font-family:""', "font-family:Arial, sans-serif"):
            with self.subTest(style=style):
                attr = "style='fill:rgb(0, 0, 255);%s'" % style.replace("'", "&#39;")
                self.assertEqual(_svg.clean_svg(bare("<rect %s width='9' height='9'/>" % attr)).colours, ["#0000ff"])
                clean = _svg.clean_svg(bare("<style>g{%s} rect{fill:rgb(0, 0, 255)}</style>" % style + shape))
                self.assertEqual(clean.colours, ["#0000ff"])
                self.assertEqual(len(clean.notes), 1, clean.notes)

    def test_only_plain_letters_and_plain_spaces_make_a_property_or_a_selector(self):
        # Python's strip() takes a no-break space and its lower() turns a Kelvin sign into a k: `(nbsp)fill` was read
        # as fill and `stro(Kelvin)e` as stroke, where a renderer sees a property it does not know and paints nothing
        for sheet in ("rect{\u00a0fill:#f00}", "rect{fill\u00a0:#f00}", "rect{stro\u212ae:#f00;stroke-width:3}", "\u00a0rect{fill:#f00}",
                      "rect\u2003{fill:#f00}", "rect{fill:#00f;\u3000fill:#f00}", "rect,\u00a0g{fill:#f00}", "rect{FILL\u0131:#f00}"):
            with self.subTest(sheet=ascii(sheet)):
                refused(self, bare("<style>%s</style>" % sheet + '<rect width="9" height="9"/>'), "css-unreadable")
        for style in ("\u00a0fill:#f00", "fill\u2003:#f00", "stro\u212ae:#f00", "fill:#00f;\u00a0fill:#f00"):
            with self.subTest(style=ascii(style)):
                refused(self, bare('<rect style="%s" width="9" height="9"/>' % style), "css-unreadable")
        # nor capitals: a browser reads FILL as fill, the site's renderer does not read it at all (measured 2026-10-12)
        for style in ("FILL:#f00", "Fill:#f00", "fill:#00f;strokE:#f00", "-Inkscape-font-specification:x"):
            with self.subTest(style=style):
                self.assertIn("capital", str(refused(self, bare('<rect style="%s" width="9" height="9"/>' % style), "css-unreadable")))
                refused(self, bare("<style>rect{%s}</style>" % style + '<rect width="9" height="9"/>'), "css-unreadable")
        for style in (" fill : #f00 ", "\tfill:#f00;\n", "fill:#F00", "fill:RED"):
            with self.subTest(style=style):
                self.assertEqual(_svg.clean_svg(bare('<rect style="%s" width="9" height="9"/>' % style)).colours, ["#ff0000"])

    def test_a_comment_opener_inside_a_string_does_not_swallow_the_rules_after_it(self):
        sheet = '<style>g{font-family:"/*"} rect{fill:#0000ff} g{font-family:"*/"}</style><rect width="9" height="9"/>'
        self.assertEqual(_svg.clean_svg(bare(sheet)).colours, ["#0000ff"])
        sheet = "<style>g{font-family:'\\\\'} /* a comment */ rect{fill:#0000ff}</style><rect width=\"9\" height=\"9\"/>"
        self.assertEqual(_svg.clean_svg(bare(sheet)).colours, ["#0000ff"])


class Styles(unittest.TestCase):
    """Settings that change the drawing are kept or refused by name, never dropped with a vague
    note; and a file's styles are held to a budget, so applying them cannot take long."""

    SHAPE = '<path %s fill="#111111" stroke="#222222" d="M0 0h9v9z"/>'

    def test_paint_order_is_kept_because_it_changes_the_drawing(self):
        for value in ("stroke", "stroke fill", "normal", "markers stroke fill", "fill"):
            for attrs in ('paint-order="%s"', 'style="paint-order:%s"'):
                with self.subTest(value=value, attrs=attrs):
                    clean = _svg.clean_svg(bare(self.SHAPE % (attrs % value)))
                    self.assertIn('paint-order="%s"' % value, clean.text)
                    self.assertEqual(clean.notes, [])
        for value in ("stroke stroke", "sideways", "fill stroke markers fill", "normal fill", "url(#a)"):
            with self.subTest(value=value):
                refused(self, bare(self.SHAPE % ('paint-order="%s"' % value)), "bad-value")

    def test_clip_path_units_are_kept_on_a_clip_path(self):
        inner = '<defs><clipPath id="c" clipPathUnits="%s"><rect width="1" height="1"/></clipPath></defs>' + self.SHAPE % 'clip-path="url(#c)"'
        for value in ("objectBoundingBox", "userSpaceOnUse"):
            clean = _svg.clean_svg(bare(inner % value))
            self.assertIn('<clipPath id="c" clipPathUnits="%s">' % value, clean.text)
            self.assertEqual(clean.notes, [])
        refused(self, bare(inner % "somethingElse"), "bad-value")
        # on any other element it means nothing: left out, and said
        clean = _svg.clean_svg(bare(self.SHAPE % 'clipPathUnits="objectBoundingBox"'))
        self.assertNotIn("clipPathUnits", clean.text)
        self.assertEqual(len([n for n in clean.notes if "clipPathUnits" in n]), 1)

    def test_a_style_for_print_or_in_another_language_is_refused_not_applied(self):
        rule = "path{fill:#ff0000}"
        for media in ("print", "PRINT", "screen and (min-width: 100px)", "(prefers-color-scheme: dark)", "speech", "not all"):
            with self.subTest(media=media):
                self.assertIn(media, str(refused(self, svg('<style media="%s">%s</style>' % (media, rule)), "style-media")))
        for kind in ("text/x-scss", "text/less", "text/javascript", "application/json"):
            with self.subTest(kind=kind):
                self.assertIn(kind, str(refused(self, svg('<style type="%s">%s</style>' % (kind, rule)), "style-type")))
        # a browser takes no blank off a type, and only plain blanks off a media: with one left on, it does not apply the style
        for attrs, code in (('type=" text/css"', "style-type"), ('type="text/css "', "style-type"), ('type="\u00a0text/css"', "style-type"),
                            ('type="text/css&#10;"', "style-type"), ('media="\u00a0all"', "style-media"), ('media="screen\u2003"', "style-media"),
                            ('media="\u3000"', "style-media")):
            with self.subTest(attrs=ascii(attrs)):
                refused(self, svg("<style %s>%s</style>" % (attrs, rule)), code)
        for attrs in ("", 'media="all"', 'media="screen"', 'media=" Screen "', 'media=""', 'type="text/css"', 'type="TEXT/CSS"', 'type="text/css" media="all"'):
            with self.subTest(attrs=attrs):
                clean = _svg.clean_svg(svg("<style %s>%s</style>" % (attrs, rule)))
                self.assertEqual((clean.colours, clean.notes), (["#ff0000"], []))

    def test_all_the_styles_of_a_file_share_one_budget(self):
        half = "path{fill:#b4531a}" + " " * (_svg.MAX_STYLE_CHARS // 2)
        refused(self, svg("<style>%s</style><style>%s</style>" % (half, half)), "too-large")
        refused(self, svg("<g><style>%s</style></g>" % half * 2), "too-large")
        _svg.clean_svg(svg("<style>%s</style>" % half))

    def test_more_selectors_or_values_than_a_logo_needs_are_refused_by_name(self):
        def sheet(selectors, values):
            return "<style>%s{%s}</style>" % (",".join(".c%d" % i for i in range(selectors)), ";".join("fill:#b4531a" for _ in range(values)))

        refused(self, svg(sheet(_svg.MAX_SELECTORS + 1, 1)), "too-many-selectors")
        refused(self, svg(sheet(_svg.MAX_SELECTORS // 2 + 1, 1) * 2), "too-many-selectors")  # counted over every <style> together
        refused(self, svg(sheet(1, _svg.MAX_DECLARATIONS + 1)), "too-many-declarations")
        refused(self, svg(sheet(1, _svg.MAX_DECLARATIONS // 2 + 1) * 2), "too-many-declarations")
        _svg.clean_svg(svg(sheet(_svg.MAX_SELECTORS, _svg.MAX_DECLARATIONS)))

    def test_a_selector_joins_a_handful_of_names_and_each_of_them_counts(self):
        # The caps counted selectors, not what one selector holds: 200 selectors of 155 names each stayed inside every
        # cap and took 79 seconds to apply (and one selector of 32,000 names took 6).
        def joined(parts, tag=""):
            return "<style>%s%s{fill:#111111}</style>" % (tag, "".join(parts))

        most = _css.MAX_PARTS
        for parts in ([".k"] * (most + 1), ["#k"] * (most + 1), [".a", "#b"] * (most // 2) + [".c"], [".k%d" % i for i in range(most + 1)]):
            for tag in ("", "path", "*"):
                with self.subTest(parts="".join(parts), tag=tag):
                    err = refused(self, svg(joined(parts, tag)), "selector-too-long")
                    self.assertIn(str(most), str(err))
                    self.assertIn("plainer export", str(err))
        refused(self, svg("<style>.ok{fill:#111111} g, path%s, rect{fill:#222222}</style>" % (".k" * (most + 1))), "selector-too-long")
        for parts in ([".k"] * most, ["#k"] * most, [".a", "#b"] * (most // 2), [".k"]):
            for tag in ("", "path", "*"):
                with self.subTest(parts="".join(parts), tag=tag):
                    _svg.clean_svg(svg(joined(parts, tag)))
        # every name is one look at every element, so every name counts toward the selectors a file may have
        def many(selectors, names):
            return "<style>%s{fill:#111111}</style>" % ",".join("".join(".c%d-%d" % (i, j) for j in range(names)) for i in range(selectors))

        for names in (2, 5, most):
            fit = _svg.MAX_SELECTORS // names
            with self.subTest(names=names):
                _svg.clean_svg(svg(many(fit, names)))
                refused(self, svg(many(fit, names) + many(1, names)), "too-many-selectors")
                refused(self, svg(many(fit + 1, names)), "too-many-selectors")
        _svg.clean_svg(svg("<style>%s{fill:#111111}</style>" % ",".join(["path"] * _svg.MAX_SELECTORS)))  # a bare tag is one look
        refused(self, svg("<style>%s{fill:#111111}</style>" % ",".join(["path"] * (_svg.MAX_SELECTORS + 1))), "too-many-selectors")

    def test_a_name_written_twice_in_a_selector_still_counts_twice_as_a_renderer_counts_it(self):
        # `.a.a` outranks `.b` (measured with the site's renderer, 2026-10-12): the names of a selector are capped, not merged
        two = '<rect class="a b" width="9" height="9"/>'
        self.assertEqual(_svg.clean_svg(bare("<style>.a.a{fill:#ff0000} .b{fill:#0000ff}</style>" + two)).colours, ["#ff0000"])
        self.assertEqual(_svg.clean_svg(bare("<style>.a{fill:#ff0000} .b{fill:#0000ff}</style>" + two)).colours, ["#0000ff"])
        self.assertEqual(_svg.clean_svg(bare("<style>#i#i{fill:#ff0000} #i.a.b{fill:#0000ff}</style>" + two.replace("<rect ", '<rect id="i" '))).colours, ["#ff0000"])

    def test_the_most_styles_a_file_may_carry_are_applied_in_bounded_time(self):
        # elements x selectors is the cost: 4,990 x 30,000 took most of a minute before the caps
        shapes = '<path class="k" d="M0 0"/>' * (_svg.MAX_ELEMENTS - 10)
        worst = [
            svg("<style>%s</style>" % "".join("path.k{fill:#111111}" for _ in range(_svg.MAX_SELECTORS)) + shapes),
            svg("<style>path{%s}</style>" % ";".join("fill:#111111" for _ in range(_svg.MAX_DECLARATIONS)) + shapes),
        ]
        for out in judged(self, worst, each=5.0):
            self.assertEqual(out["code"], "ok")
        over = svg("<style>%s{fill:#111111}</style>" % ",".join(".c%d" % i for i in range(9000)) + shapes)
        self.assertEqual(judged(self, [over])[0]["code"], "too-many-selectors")

    def test_no_selector_however_it_is_built_makes_the_styles_slow_to_apply(self):
        most, names = _svg.MAX_ELEMENTS - 10, _css.MAX_PARTS
        paths = '<path class="k" id="k" d="M0 0"/>' * most
        # the very file that took 79 seconds: 200 selectors of 155 names on 2,230 groups of 94 classes each, and one rect
        groups = '<g class="%s a"/>' % " ".join(["x"] * 93) * 2230 + '<rect width="9" height="9"/>'
        slow = svg("<style>%s{fill:#f00}</style>" % ",".join([".a" * 155] * 200) + groups)
        self.assertLess(len(slow), _svg.MAX_BYTES)
        over = [
            slow,
            svg("<style>%s{fill:#111111}</style>" % (".k" * 32000) + paths),                      # one selector, 32,000 classes
            svg("<style>%s{fill:#111111}</style>" % ("#k" * 20000) + paths),                      # the same with ids
            svg("<style>path%s{fill:#111111}</style>" % (".k" * 20000) + paths),                  # a tag and a long chain
            svg("<style>%s{fill:#111111}</style>" % ",".join(["#a" * 155] * 200) + '<g id="a"/>' * most),
            svg("<style>%s{fill:#111111}</style>" % ",".join([".k" * (names + 1)] * 200) + paths),  # many short ones, one name too long
        ]
        for i, out in enumerate(judged(self, over)):
            self.assertEqual(out["code"], "selector-too-long", i)
        budget = svg("<style>%s{fill:#111111}</style>" % ",".join([".k.k.k"] * 200) + paths)        # each short enough, too many together
        self.assertEqual(judged(self, [budget])[0]["code"], "too-many-selectors")
        # and the most that IS allowed, built each way, is applied in bounded time
        fit = _svg.MAX_SELECTORS // names
        inside = [
            svg("<style>%s</style>" % "".join("path%s{fill:#111111}" % (".k" * names) for _ in range(fit)) + paths),
            svg("<style>%s</style>" % "".join("%s{fill:#111111}" % ("#k" * names) for _ in range(fit)) + paths),
            svg("<style>%s{fill:#111111}</style>" % ",".join([".k"] * _svg.MAX_SELECTORS) + paths),
            svg("<style>%s</style>" % "".join(".a{fill:#111111}" for _ in range(_svg.MAX_SELECTORS)) + groups),
            svg("<style>%s</style>" % "".join("#a{fill:#111111}" for _ in range(_svg.MAX_SELECTORS)) + '<g id="a"/>' * most + '<rect width="9" height="9"/>'),
            svg("<style>%s</style>" % "".join(".k{%s}" % ";".join(["fill:#111111"] * 5) for _ in range(_svg.MAX_SELECTORS)) + paths),
        ]
        for i, out in enumerate(judged(self, inside, each=5.0)):
            self.assertEqual(out["code"], "ok", i)


class Structure(unittest.TestCase):
    """What a renderer does not draw must not be counted as the mark's, and must not come out as
    part of it either."""

    def test_an_element_where_nothing_is_drawn_is_refused_so_its_colours_are_never_counted(self):
        for inner in ('<style><rect fill="#0000ff" width="9" height="9"/></style>',
                      '<rect width="9" height="9"><circle fill="#ff0000" r="3"/></rect>',
                      '<path d="M0 0h9v9z"><g><path fill="#ff0000" d="M0 0h9v9z"/></g></path>',
                      '<line x2="9"><rect width="9" height="9"/></line>',
                      '<circle r="3"><style>circle{fill:#ff0000}</style></circle>',
                      "<style><style>path{fill:#ff0000}</style></style>",
                      '<polygon points="0,0 9,0 9,9"><defs/></polygon>',
                      '<ellipse rx="3" ry="2"><clipPath id="c"/></ellipse>',
                      '<polyline points="0,0 9,9"><polyline points="0,0 9,9" stroke="#ff0000"/></polyline>'):
            with self.subTest(inner=inner):
                self.assertIn("nothing is drawn", str(refused(self, svg(inner), "misplaced-element")))
        # a title, or an editor's own element, inside a shape draws nothing and is left out as before
        inner = '<rect width="9" height="9" fill="#111111"><title>x</title><desc>y</desc><x:note xmlns:x="urn:editor"><x:deep/></x:note></rect>'
        clean = _svg.clean_svg(svg(inner))
        self.assertEqual(clean.colours, ["#111111", "#b4531a"])
        self.assertIn('<rect height="9" width="9" fill="#111111"/>', clean.text)

    def test_an_element_taken_out_of_the_svg_namespace_is_left_out_as_a_renderer_leaves_it(self):
        for inner in ('<rect xmlns="" fill="#ff0000" width="9" height="9"/>',
                      '<g xmlns=""><rect fill="#ff0000" width="9" height="9"/></g>',
                      '<g xmlns=""><rect xmlns="http://www.w3.org/2000/svg" fill="#ff0000" width="9" height="9"/></g>',
                      '<x:rect xmlns:x="urn:other" fill="#ff0000" width="9" height="9"/>'):
            with self.subTest(inner=inner):
                clean = _svg.clean_svg(svg(inner))
                self.assertEqual(clean.colours, ["#b4531a"])
                self.assertNotIn("rect", clean.text)
                self.assertEqual(len(clean.notes), 1, clean.notes)
        # pasted code that names no namespace anywhere is still a drawing
        pasted = b'<svg viewBox="0 0 8 8"><g><path fill="#111111" d="M0 0h9v9z"/></g></svg>'
        self.assertEqual(_svg.clean_svg(pasted).colours, ["#111111"])
        self.assertEqual(_svg.clean_svg(pasted.replace(b"<path ", b'<path xmlns="http://www.w3.org/2000/svg" ')).colours, ["#111111"])

    def test_a_class_nothing_styles_is_only_a_word(self):
        clean = _svg.clean_svg(svg('<path class="leftover other" fill="#111111" d="M0 0h9v9z"/>'))
        self.assertEqual((clean.colours, clean.notes), (["#111111", "#b4531a"], []))
        self.assertNotIn("class", clean.text)

    def test_an_id_is_the_id_as_it_is_written(self):
        # a renderer takes no blank off an id: ` a` is not the `a` that `#a` names (measured 2026-10-12: the rect stays black)
        for value in (" a", "a ", " a ", "&#9;a", "a&#10;", "a b", ""):
            with self.subTest(value=value):
                refused(self, bare('<style>#a{fill:#ff0000}</style><rect id="%s" width="9" height="9"/>' % value), "bad-value")
        self.assertEqual(_svg.clean_svg(bare('<style>#a{fill:#ff0000}</style><rect id="a" width="9" height="9"/>')).colours, ["#ff0000"])

    def test_what_changes_the_drawing_in_one_program_and_not_in_another_is_refused_by_name(self):
        # Each of these was left out with the general note. A browser honours it and the site's renderer does not,
        # so `<g systemLanguage="xx-none">` with a red rect inside came out with the red rect in it.
        red = '<rect fill="#ff0000" width="9" height="9"/>'
        for attr, code, word in (('systemLanguage="xx-none"', "conditional", "systemLanguage"), ('systemLanguage=""', "conditional", "systemLanguage"),
                                 ('requiredExtensions="http://example.com/none"', "conditional", "requiredExtensions"),
                                 ('requiredFeatures="http://example.com/none"', "conditional", "requiredFeatures"),
                                 ('transform-origin="5 5"', "transform-origin", "transform-origin"), ('transform-origin="center"', "transform-origin", "flattened"),
                                 ('vector-effect="non-scaling-stroke"', "vector-effect", "vector-effect"), ('vector-effect="none"', "vector-effect", "outlines into shapes")):
            for doc in (svg("<g %s>%s</g>" % (attr, red)), svg(red.replace("<rect ", "<rect %s " % attr)), svg(red, root=attr),
                        svg('<defs><clipPath id="c" %s><rect width="4" height="4"/></clipPath></defs>' % attr)):
                with self.subTest(attr=attr, doc=doc[100:160]):
                    err = refused(self, doc, code)
                    self.assertIn(word, str(err))
                    self.assertIn("Ask the tool", str(err))
        for prop, code in (("transform-origin:5px 5px", "transform-origin"), ("vector-effect:non-scaling-stroke", "vector-effect")):
            with self.subTest(prop=prop):
                refused(self, svg(red.replace("<rect ", '<rect style="%s" ' % prop)), code)
                refused(self, svg("<style>rect{%s}</style>" % prop + red), code)
                refused(self, svg("<style>.unused{%s}</style>" % prop), code)
        # with a prefix it is another program's attribute, left out and said as any such is; without the attribute the file is fine
        clean = _svg.clean_svg(svg('<g x:systemLanguage="xx" xmlns:x="urn:editor">%s</g>' % red))
        self.assertEqual((clean.colours, len(clean.notes)), (["#ff0000", "#b4531a"], 1))
        self.assertEqual(_svg.clean_svg(svg("<g>%s</g>" % red)).notes, [])

    def test_an_attribute_with_a_prefix_is_not_the_plain_attribute(self):
        doc = '<svg %s xmlns:s="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><path %%s d="M0 0h9v9z"/></svg>' % NS
        for attrs in ('s:fill="#ff0000"', 's:style="fill:#ff0000"', 's:stroke="#ff0000" s:stroke-width="3"', 's:class="x" s:id="y"'):
            with self.subTest(attrs=attrs):
                clean = _svg.clean_svg((doc % attrs).encode())
                self.assertEqual(clean.colours, ["#000000"], "a renderer paints this path black: s:fill is not fill")
                self.assertNotIn("ff0000", clean.text)
                self.assertEqual(len(clean.notes), 1, clean.notes)
        self.assertEqual(_svg.clean_svg((doc % 'fill="#ff0000"').encode()).colours, ["#ff0000"])
        # what is refused wherever it stands still is
        refused(self, (doc % 's:onload="x()"').encode(), "event-attribute")
        refused(self, (doc % 's:href="https://x.example/a"').encode(), "external-link")


class NoWebPages(unittest.TestCase):
    """A drawing is no longer taken out of a web page (decided 2026-10-12): the page's own style sheet may colour
    it, and that is nowhere in the drawing. A page is refused by name with the way out, and nothing of it is read.
    The intake's side of this is in test_input_forms.py."""

    PAGE = ('<!doctype html><html><head><style>path{fill:#ff0000}</style></head><body>'
            '<svg viewBox="0 0 8 8"><path d="M0 0h8v8z"/></svg></body></html>')

    def test_the_check_reads_an_svg_and_says_so_for_anything_else(self):
        for data in (self.PAGE.encode(), svg()):
            for source in ("html", "html-svg", "page", "zip", "", None, "SVG", 0):
                with self.subTest(source=source, data=data[:20]):
                    with self.assertRaises(_svg.Refusal) as cm:
                        _svg.clean_svg(data, source=source)
                    self.assertEqual(cm.exception.code, "web-page")
                    for word in ("web page", "SVG file", "pasted", "zip", "<svg", "</svg>", "Ask the tool"):
                        self.assertIn(word, str(cm.exception))
        self.assertEqual(_svg.clean_svg(svg(), source="svg").colours, ["#b4531a"])
        self.assertEqual(_svg.clean_svg(svg(), source="svg", current="#123456").colours, ["#b4531a"])
        with self.assertRaises(TypeError):
            _svg.clean_svg(self.PAGE.encode(), pick=0)  # there is nothing to pick from any more

    def test_a_page_handed_to_the_check_itself_is_not_an_svg(self):
        for page in (self.PAGE, self.PAGE.replace("<!doctype html>", ""), "<div>%s</div>" % self.PAGE.split("<body>")[1].split("</body>")[0]):
            with self.subTest(page=page[:30]):
                with self.assertRaises(_svg.Refusal) as cm:
                    _svg.clean_svg(page.encode())
                self.assertIn(cm.exception.code, ("doctype", "not-svg", "not-xml"))

    def test_the_drawings_own_code_copied_out_of_the_page_is_read(self):
        # the way on: from <svg to </svg>, with no namespace named anywhere, as a page writes it
        copied = self.PAGE.split("<body>")[1].split("</body>")[0].encode()
        self.assertEqual(_svg.clean_svg(_input.mark(_input.load(copied)).colour).colours, ["#000000"])

    def test_a_page_built_to_be_slow_is_one_refusal_at_once_on_every_python(self):
        # Each of these cost the page reader seconds or minutes (the parser of Python 3.9 goes back over the rest of a
        # page for every "<" that never closes). Nothing of a page is read now beyond its first element's name.
        pieces = ("<a ", "<svg ", "<svg\n", '<svg a="', "<svg a='", '<a b="c" ', "<a b=c ", "<a/b ", "<!--", "<svg><!--", "</", "<?",
                  "<![if x]", "<!doctype ", "<svg/>", "<svg></svg>", "<g></b>", "<![ ", "<![CDATA[", "<!ENTITY % x>")
        pages = [("<html><body>" + piece * (300000 // len(piece))).encode() for piece in pieces]
        pages += [("<html><body><svg>" + "<g>" * 40000 + "</b>" * 40000).encode(), ("<html><body><svg viewBox='0 0 1 1'>" + "<g>" * 150000).encode(),
                  ("<html><body><svg viewBox='0 0 1 1'><path d='M0 0'/>" + "x" * 2000000 + "</svg>").encode(),
                  b"<html><body>" + b"<svg/>" * (10 * 1024 * 1024 // 6),                    # 10 MB, 1.7 million drawings
                  b"<!--" + b"-" * 5000000 + b"--><!doctype html>" + b"<svg/>" * 800000,
                  (u"\ufeff<html>" + "<svg/>" * 500000).encode("utf-16")]
        for i, out in enumerate(judged(self, pages, how="intake")):
            self.assertEqual(out["code"], "web-page", i)
        # the same pieces with no page around them are not pages, and are still judged at once
        bare_pieces = [(piece * (300000 // len(piece))).encode() for piece in pieces] + [b"<svg/>" * (10 * 1024 * 1024 // 6)]
        for piece, out in zip(pieces + ("10 MB",), judged(self, bare_pieces, how="intake")):
            self.assertIn(out["code"], ("web-page", "unknown-file", "not-xml", "too-large", "no-size"), piece)


if __name__ == "__main__":
    unittest.main()
