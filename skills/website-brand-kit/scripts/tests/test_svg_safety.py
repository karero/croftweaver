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
import _refusal
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
                       "\u180e", "\ufff9", "\ue000", "\U000e0041\U000e0042", "\u0378", "\u2028", "\u2029", "\U000f0000",
                       # drawn as nothing as well, though Python calls them printable: repr() let these through as they are
                       "\ufe0f", "\ufe00", "\U000e0100", "\U000e01ef", "\u034f", "\u115f", "\u1160", "\u3164", "\uffa0", "\u180b", "\u17b4", "\u2800",
                       # and every blank that is not the plain space
                       "\u00a0", "\u2003", "\u3000", "\u202f", "\u1680"):
            for attrs in ('href="%sgpj.elif//:ptth"', 'stroke-width="%s1"', 'transform="%s"', 'fill="%s"', 'style="fill:%s"', 'id="a%s"', 'points="1 1%s"',
                          'stroke-dasharray="4%s"', 'clip-path="none%s"', 'style="cursor%s:a"', 'display="no%sne"', 'width="5%spx"',
                          # on the outer svg
                          '>viewBox="0 0 %s 9"', '>preserveAspectRatio="none%s"', '>transform="scale(2)%s"', '>width="9%smm"'):
                with self.subTest(hidden=ascii(hidden), attrs=attrs):
                    place = b"<svg " if attrs[0] == ">" else b"<path "
                    with self.assertRaises(_svg.Refusal) as cm:
                        _svg.clean_svg(svg().replace(place, place + (attrs.lstrip(">") % hidden).encode("utf-8") + b" ", 1))
                    self.assertTrue(str(cm.exception).isprintable(), ascii(str(cm.exception)))
                    self.assertFalse([c for c in str(cm.exception) if _refusal.unseen(c)], ascii(str(cm.exception)))
        # the one place that does it: whatever a sentence is made of, it is shown in characters a person can see
        for hidden, spelled in (("\ufe0f", "\\ufe0f"), ("\u200b", "\\u200b"), ("\x9b", "\\x9b"), ("\u00a0", "\\xa0"), ("\U000e0100", "\\U000e0100"),
                                ("\u2800", "\\u2800"), ("\t", "\\t"), ("\r", "\\r"), ("\x00", "\\x00")):
            for error in (_refusal.Refusal("a-code", "found a%sb in the file" % hidden), _refusal.Ask("a-code", "which of a%sb?" % hidden, ["x"])):
                self.assertIn("a%sb" % spelled, str(error))
                self.assertNotIn(hidden, str(error))
        plain = "A sentence with caf\u00e9, \u65e5\u672c, a dash \u2013 and\ntwo lines stays as it is."
        self.assertEqual(str(_refusal.Refusal("a-code", plain)), plain)

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

    def test_plain_numbers_and_px_count_and_no_other_unit_does(self):
        doc = '<svg xmlns="http://www.w3.org/2000/svg" width="%s" height="%s"><path d="M0 0h1v1z"/></svg>'
        for w, h, box in (("40px", "30px", "0 0 40 30"), ("40", "30", "0 0 40 30"), ("4e1", "3e1", "0 0 4e1 3e1"), ("40", "30px", "0 0 40 30"), (" 40.0 ", "+30", "0 0 40.0 +30")):
            with self.subTest(w=w, h=h):
                clean = _svg.clean_svg((doc % (w, h)).encode())
                self.assertEqual(clean.view_box, (0.0, 0.0, 40.0, 30.0))
                self.assertIn('viewBox="%s"' % box, clean.text)
        # Measured 2026-10-12: the site's renderer sizes cm, in and pt by the icon it is drawing, so the box worked out
        # here (at a browser's 96 to the inch) was not the box it drew in: the mark came out at another size
        for w, h in (("4cm", "3cm"), ("1in", "1in"), ("12pt", "12pt"), ("40mm", "30mm"), ("4pc", "3pc"), ("40", "3cm"), ("1in", "96")):
            with self.subTest(w=w, h=h):
                err = refused(self, (doc % (w, h)).encode(), "no-size")
                self.assertIn("viewBox", str(err))
        # beside a viewBox of the same shape such a width and height change nothing, and are left out as before
        for w, h, box in (("4cm", "3cm", "0 0 64 48"), ("1in", "1in", "0 0 7 7"), ("12pt", "12pt", "0 0 7 7"), ("40mm", "30mm", "0 0 4 3"), ("4pc", "3pc", "0 0 8 6")):
            with self.subTest(w=w, h=h, box=box):
                clean = _svg.clean_svg((doc % (w, h)).replace("<svg ", '<svg viewBox="%s" ' % box).encode())
                self.assertIn('viewBox="%s">' % box, clean.text)
        for w, h in (("4em", "3em"), ("4ex", "3ex"), ("40vw", "30vh"), ("4rem", "3rem")):
            with self.subTest(w=w, h=h):
                refused(self, (doc % (w, h)).encode(), "length-unit")

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
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 48" width="4cm" height="3cm">',
                    '<svg xmlns="http://www.w3.org/2000/svg" width="151.181102px" height="113.385827">'):
            clean = _svg.clean_svg((tag + '<path fill="#111111" d="M0 0h9v9z"/></svg>').encode())
            root = clean.text.split(">", 1)[0]
            self.assertIn("viewBox=", root)
            self.assertNotIn("width=", root)
            self.assertNotIn("height=", root)
        self.assertIn('viewBox="0 0 151.181102 113.385827"', clean.text)

    def test_the_box_is_written_as_it_was_read_with_nothing_rounded(self):
        # the cleaned box was the numbers worked out from the file, rounded to six places: in a small box that is
        # another box, and the drawing sat a fraction of a pixel away from where the file had it
        doc = '<svg xmlns="http://www.w3.org/2000/svg" %s><path fill="#111111" d="M0 0h9v9z"/></svg>'
        for attrs, written, box in (('viewBox="0 0 0.0100004 0.0100009"', "0 0 0.0100004 0.0100009", (0, 0, 0.0100004, 0.0100009)),
                                    ('viewBox=" -0.33333333333 +.5e1,10.0000000001 , 1E1 "', "-0.33333333333 +.5e1 10.0000000001 1E1", (-0.33333333333, 5, 10.0000000001, 10)),
                                    ('viewBox="0,0,64,64"', "0 0 64 64", (0, 0, 64, 64)), ('viewBox="0-0 64.50 64"', "0 -0 64.50 64", (0, 0, 64.5, 64)),
                                    ('width="12.3456789012" height="+9.87654321e0"', "0 0 12.3456789012 +9.87654321e0", (0, 0, 12.3456789012, 9.87654321))):
            with self.subTest(attrs=attrs):
                clean = _svg.clean_svg((doc % attrs).encode())
                self.assertIn('viewBox="%s"' % written, clean.text)
                self.assertEqual(clean.view_box, box)
                again = _svg.clean_svg(clean.text.encode())
                self.assertEqual((again.text, again.view_box), (clean.text, clean.view_box), "and the cleaned file is read as the same box")

    def test_a_box_too_small_or_too_big_to_be_a_logo_is_refused(self):
        for vb in ("0 0 1e9 1e9", "0 0 0.0000001 0.0000001", "0 0 1e7 5", "0 0 1000001 1000001", "0 0 0.0099 0.0099", "0 0 0.003 0.003", "0 0 0.001 0.001",
                   "1000001 0 9 9", "0 -1000001 9 9", "0 0 1e10 1e10", "0 0 1e99 1e99"):
            with self.subTest(vb=vb):
                refused(self, ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s"><path fill="#111111" d="M0 0"/></svg>' % vb).encode(), "bad-view-box")
        # both sides of each line (measured 2026-10-13: under 0.004 the site's renderer draws nothing at all in the box)
        for vb in ("0 0 0.01 0.01", "0 0 1e-2 .01", "0 0 1000000 1000000", "0 0 1e6 1e6", "1000000 -1e6 9 9"):
            with self.subTest(vb=vb):
                _svg.clean_svg(('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s"><path fill="#111111" d="M0 0h9v9z"/></svg>' % vb).encode())
        for w, h, code in (("0.0099", "0.0099", "bad-view-box"), ("1000001", "1000001", "bad-view-box"), ("0", "9", "no-size"), ("9", "0.0", "no-size")):
            with self.subTest(w=w, h=h):
                refused(self, ('<svg xmlns="http://www.w3.org/2000/svg" width="%s" height="%s"><path fill="#111111" d="M0 0"/></svg>' % (w, h)).encode(), code)

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

    def test_a_long_honest_value_is_read_just_as_fast_and_kept_only_as_long_as_a_logo_needs(self):
        # as much as the grammar keeps of each kind is read at once ...
        most = ['points="%s"' % ("1.5,-2e1 " * (_svg.MAX_POINTS // 2)), 'stroke-dasharray="%s"' % ("4 2 " * (_svg.MAX_DASHES // 2)),
                'transform="%s"' % ("scale(1) " * _svg.MAX_TRANSFORMS), 'd="M0 0%s"' % (" 1" * 90000), 'width="%s"' % ("1" * 9 + "." + "0" * (_svg.MAX_VALUE - 10))]
        for attrs, out in zip(most, judged(self, [self.shape(attrs) for attrs in most])):
            self.assertEqual(out["code"], "ok", attrs[:60])
        # ... and a value that is the right form and far longer is refused by name, just as fast (each of these was read
        # and kept whole before 2026-10-12: one rule's value is written onto every element, so the cleaned file grew without end)
        over = ['points="%s"' % ("1.5,-2e1 " * 40000), 'stroke-dasharray="%s"' % ("4 2 " * 50000), 'transform="%s"' % ("scale(1) " * 40000),
                'd="M0 0%s"' % (" 1" * 190000), 'width="%s"' % ("1" * 100000), 'stroke-width="%s1"' % ("0" * 200000), 'style="stroke-dasharray:%s"' % ("1 " * 30000),
                'points="%s"' % ("1 " * 250000), 'transform="translate(%s)"' % ("0" * 100000 + "1")]
        for attrs, out in zip(over, judged(self, [self.shape(attrs) for attrs in over])):
            self.assertEqual(out["code"], "value-too-long", attrs[:60])

    def test_numbers_written_the_ways_tools_write_them_are_still_read(self):
        # run together without a space, a bare dot, a sign, an exponent: all of it is SVG
        fine = ['points="10-20,3.5.5 1e2,4"', 'points=""', 'stroke-dasharray="4 2"', 'stroke-dasharray="4,2"', 'stroke-dasharray="none"',
                'width="1.0" height=".5"', 'x="+3" y="-3"', 'width="1e2"', 'width="4.5px"', 'rx="auto"',
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
                          'stroke-miterlimit="%s"', 'stroke-dashoffset="%s"', 'style="stroke-dashoffset:%s"',
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
        # in a colour as well: `rgb(255.,0,0)` was read as red, and the renderer paints it black. The colour reader says
        # so by name (it holds what a colour is; this check no longer has a rule of its own beside it)
        for value in ("rgb(255.,0,0)", "rgb(255. 0 0)", "rgb(100.%,0%,0%)", "rgba(255,0,0,1.)", "hsl(0.,100%,50%)", "rgb(0,0,255.)", "rgb(1.e2,0,0)", "red."):
            for attrs in ('fill="%s"', 'stroke="%s"', 'color="%s"', 'style="fill:%s"'):
                with self.subTest(value=value, attrs=attrs):
                    refused(self, self.shape(attrs % value), "colour-unreadable")
        self.assertEqual(_svg.clean_svg(bare('<rect fill="rgb(255.0,.0,0.0)" width="9" height="9"/>')).colours, ["#ff0000"])
        # in path data it is a number, to the renderer and so to this check, and is kept as it is written
        self.assertIn('d="M0. 0.h5.v5.e0z"', _svg.clean_svg(svg('<path fill="#111111" d="M0. 0.h5.v5.e0z"/>')).text)
        # and every other way of writing a number is still read
        for attrs in ('width="5.0"', 'height="05"', 'stroke-width="5e0"', 'stroke-width=".5e1"', 'x="+5"', 'y="-.5"', 'transform="translate(5.0,.5)"',
                      'stroke-dasharray="5.0 .5"', 'stroke-miterlimit="4.0"'):
            with self.subTest(attrs=attrs):
                self.assertIn(attrs, _svg.clean_svg(self.shape(attrs)).text)
        _svg.clean_svg(self.shape('opacity="1.0" fill-opacity="1.00e0"'))

    def test_a_dash_is_a_plain_number_and_a_percent_sign_makes_none(self):
        # every "%" used to be taken out before the list was read, so `5%10%` was checked as the number 510. Since
        # 2026-10-12 a dash is a plain number: a share of the box's diagonal is no length a logo needs.
        for value in ("5%%", "%", "%5", "5 %", "5%%10", "1 2 %", "5%px", "%%", "5%.", "5.%", "5%10%", "5% 10%", "5%,10%", "50% 2", "1%2", ".5%", "4px 2px", "4 2px"):
            with self.subTest(value=value):
                refused(self, self.shape('stroke-dasharray="%s" stroke="#ff0000"' % value), "bad-value")
                refused(self, self.shape('style="stroke-dasharray:%s" stroke="#ff0000"' % value), "bad-value")
        for value in ("4 2", "4,2", "none", "4", "0.5 .5e1"):
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

    def test_a_part_that_is_left_out_holds_words_and_nothing_of_a_drawing(self):
        # `<metadata><style>rect{fill:#f00}</style></metadata><rect/>` was accepted with no note and listed as black. The
        # site's renderer applies that style (and clips with a clipPath that stands in such a place): the file as it
        # came was drawn red, the cleaned file black. Measured 2026-10-12 for each of the places below.
        rdf = 'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"'
        places = ("<title>%s</title>", "<desc>%s</desc>", "<metadata>%s</metadata>", '<x:note xmlns:x="urn:editor">%s</x:note>',
                  "<metadata><rdf:RDF %s>%%s</rdf:RDF></metadata>" % rdf, '<sodipodi:namedview xmlns:sodipodi="urn:sodipodi"><sodipodi:a>%s</sodipodi:a></sodipodi:namedview>',
                  "<g><title>%s</title></g>", "<defs><desc>%s</desc></defs>", '<path d="M0 0h9v9z"><title>%s</title></path>',
                  '<x:title xmlns:x="urn:editor">%s</x:title>', '<x:style xmlns:x="urn:editor">%s</x:style>')
        things = ("<style>path{fill:#ff0000}</style>", "<style>path{display:none}</style>", '<rect fill="#ff0000" width="9" height="9"/>',
                  '<clipPath id="c"><rect width="4" height="4"/></clipPath>', "<g/>", "<defs/>", '<path d="M0 0"/>', "<script>x</script>", "<nonsense/>",
                  "<title>a title in a title</title>", '<svg viewBox="0 0 1 1"/>', '<b xmlns="">bold</b>', '<rect xmlns="http://www.w3.org/2000/svg" width="9" height="9"/>')
        for place in places:
            for thing in things:
                with self.subTest(place=place, thing=thing):
                    err = refused(self, svg(place % thing), "misplaced-element")
                    self.assertIn("left out", str(err))
                    self.assertIn("Ask the tool", str(err))
        self.assertIn("<style>", str(refused(self, svg("<metadata><style>path{fill:#f00}</style></metadata>"), "misplaced-element")))
        self.assertIn("<metadata>", str(refused(self, svg("<metadata><style>path{fill:#f00}</style></metadata>"), "misplaced-element")))
        # what such a part does hold is left out as before: words, and another program's own elements however deep
        for place in places:
            for thing in ("", "A bakery's mark", "a &lt;style&gt; in words", "<!-- <style>path{fill:#f00}</style> -->", "<![CDATA[<style>path{fill:#f00}</style>]]>",
                          '<cc:Work xmlns:cc="urn:cc"><dc:format xmlns:dc="urn:dc">image/svg+xml</dc:format></cc:Work>', '<x:style xmlns:x="urn:other">path{fill:#f00}</x:style>',
                          '<h:p xmlns:h="http://www.w3.org/1999/xhtml">words</h:p>'):
                with self.subTest(place=place, thing=thing):
                    clean = _svg.clean_svg(svg(place % thing))
                    self.assertEqual(clean.colours[-1], "#b4531a")
                    self.assertNotIn("f00", clean.text)
        # pasted code that names no namespace: its title holds words only as well
        refused(self, b'<svg viewBox="0 0 8 8"><title><style>path{fill:#f00}</style></title><path d="M0 0h9v9z"/></svg>', "misplaced-element")
        self.assertEqual(_svg.clean_svg(b'<svg viewBox="0 0 8 8"><title>Logo</title><path d="M0 0h9v9z"/></svg>').colours, ["#000000"])

    def test_an_element_taken_out_of_the_svg_namespace_is_refused_because_the_renderer_draws_it_all_the_same(self):
        # Each of these was left out with a note, "as a renderer leaves it". Measured 2026-10-12: a browser leaves it out,
        # the site's renderer draws the rect red and applies the style: the cleaned file was not the file as it came.
        for inner in ('<rect xmlns="" fill="#ff0000" width="9" height="9"/>',
                      '<g xmlns=""><rect fill="#ff0000" width="9" height="9"/></g>',
                      '<g xmlns=""><rect xmlns="http://www.w3.org/2000/svg" fill="#ff0000" width="9" height="9"/></g>',
                      '<style xmlns="">path{fill:#ff0000}</style>', '<title xmlns="">x</title>', '<metadata xmlns=""/>', '<anything xmlns=""/>',
                      '<g><g><path xmlns="" d="M0 0h9v9z"/></g></g>', '<defs><clipPath xmlns="" id="c"/></defs>'):
            with self.subTest(inner=inner):
                err = refused(self, svg(inner), "no-namespace")
                self.assertIn('xmlns=""', str(err))
                self.assertIn("Ask the tool", str(err))
        # another program's own element is left out, and said, as before: neither a browser nor the renderer draws it
        clean = _svg.clean_svg(svg('<x:rect xmlns:x="urn:other" fill="#ff0000" width="9" height="9"/>'))
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
                                 ('vector-effect="non-scaling-stroke"', "vector-effect", "vector-effect"), ('vector-effect="inherit"', "vector-effect", "outlines into shapes"),
                                 ('pathLength="20"', "path-length", "pathLength"), ('pathLength="1"', "path-length", "outlines into shapes")):
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


class Line(unittest.TestCase):
    """One line of the value grammar (the top of _svg.py), from both sides: every form the line takes is kept as it
    is written, and every near miss is refused, with the code that says what kind of miss it is. A property is tried
    in each place a file can set it: as an attribute, in a style attribute and in a rule of a style sheet."""

    def places(self, name, value, tag="rect", more='width="9" height="9"'):
        # svg() draws a path of its own after the shape: a value that hides the shape still leaves a mark to check
        escaped = value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
        docs = [svg('<%s %s="%s" %s/>' % (tag, name, escaped, more))]
        if name in _svg.PROPS and value.strip(" \t\r\n") and ";" not in value:
            docs.append(svg('<%s style="%s:%s" %s/>' % (tag, name, escaped, more)))
            docs.append(svg("<style>%s{%s:%s}</style><%s %s/>" % (tag, name, escaped.replace("&quot;", '"'), tag, more)))
        return docs

    def takes(self, name, values, **where):
        for value in values:
            for doc in self.places(name, value, **where):
                with self.subTest(name=name, value=value, doc=doc[150:210]):
                    clean = _svg.clean_svg(doc)
                    written = value.strip(" \t\r\n")
                    if not any(c in written for c in "\t\r\n") and name not in ("opacity", "fill-opacity", "stroke-opacity", "fill", "stroke", "color", "class"):
                        self.assertIn(' %s="%s"' % (name, written), clean.text)
                    self.assertEqual(_svg.clean_svg(clean.text.encode()).text, clean.text, "what is written is read again as the same")

    def turns_down(self, name, values, code, **where):
        for value in values:
            for doc in self.places(name, value, **where):
                with self.subTest(name=name, value=value, doc=doc[150:210]):
                    err = refused(self, doc, code)
                    self.assertIn("sk the tool", str(err))   # every refusal ends with what to ask the design tool for
        return err


# what is not a number at all, however it is dressed
NOT_NUMBERS = ["", "5.", ".", "+", "-", "5e", "5e+", "5e-", ".e1", "5.e1", "e5", "5e1.5", "5e100", "5e+100", "0e309", "5e0001", "0x5", "5f", "1_0", "5 5", "5,", ",5", "--5",
               "+-5", "5-", "5e 1", "5 e1", "inf", "Infinity", "NaN", "five", "\uff15", "\u0665", "5\u00a0", "\u00a05", "5\u2028", "5;", "5!", "(5)", "5/1", "5*1", "#5", "1,000", "1.000,5",
               "5.5.5", "5 px", "5PX", "5Px", "px", "%", "5%%", "5px px", "5pxx", "calc(5)", "5e1e1", "+.", "-.e1"]


class ANumber(Line):
    """number: stroke-miterlimit (1 or more), and the three opacities (which the paint reader then holds to exactly 1)."""

    FORMS = ["5", "5.0", "+5", ".5e1", "5e0", "5E0", "5E+00", "50e-1", "0.05e02", "05", " 5 ", "\t5\n", "5.000000000000000000000000000000000000000000000000000000000000"]

    def test_what_it_takes(self):
        self.takes("stroke-miterlimit", self.FORMS + ["1", "1.0", "1e0", "100", "1e9", "1000000000", "0" * 63 + "4"], tag="path", more='d="M0 0h9v9"')
        for name in ("opacity", "fill-opacity", "stroke-opacity"):
            self.takes(name, ["1", "1.0", "+1", "1e0", "1E0", "10e-1", "0.1e1", "01", " 1 ", "1.000000"])

    def test_what_is_no_number(self):
        for name in ("stroke-miterlimit", "opacity", "fill-opacity", "stroke-opacity"):
            self.turns_down(name, [v for v in NOT_NUMBERS if ";" not in v and "!" not in v and "/*" not in v and "(" not in v], "bad-value")
        self.turns_down("stroke-miterlimit", ["0", "0.5", ".999", "-4", "0e5", "+0.99", "1e-1"], "bad-value")   # there is no mitre limit below 1

    def test_a_number_with_a_unit_is_refused_as_that(self):
        for name in ("stroke-miterlimit", "opacity", "fill-opacity", "stroke-opacity"):
            err = self.turns_down(name, ["5px", "5pt", "5mm", "5cm", "5in", "5pc", "5em", "5ex", "5rem", "5vw", "100%", "5%", "1e0px", "+.5e1%"], "length-unit")
            self.assertIn("plain numbers for its sizes", str(err))

    def test_a_number_too_long_or_too_large_is_refused_as_that(self):
        self.turns_down("stroke-miterlimit", ["0" * 64 + "4", "4." + "0" * 63, "1e10", "1000000001", "9e99", "1.0000001e9", "4e38"], "value-too-long")
        self.turns_down("opacity", ["0" * 64 + "1", "1." + "0" * 63, "1e10", "9e99"], "value-too-long")

    def test_an_opacity_in_the_grammar_that_is_not_one_is_the_paint_readers_to_refuse(self):
        self.turns_down("opacity", ["0", "0.5", ".999", "0.99999", "1.5", "-1", "1e-1", "2"], "colour-alpha")


class ALength(Line):
    """length: a number, or a number and px. stroke-dashoffset; and, not below zero, stroke-width, r, rx, ry (rx and ry
    also `auto`)."""

    FORMS = ANumber.FORMS[:-1] + ["5px", "5.0px", "+5px", ".5e1px", "5e0px", " 5px ", "0", "0px", "0.0", "1e9", "1e9px"]

    def test_what_it_takes(self):
        self.takes("stroke-dashoffset", self.FORMS + ["-5", "-5px", "-.5e1", "-0", "-1e9"], tag="path", more='d="M0 0h9v9"')
        self.takes("stroke-width", self.FORMS, tag="path", more='d="M0 0h9v9" stroke="#ff0000"')
        self.takes("r", self.FORMS, tag="circle", more="")
        for name in ("rx", "ry"):
            self.takes(name, self.FORMS + ["auto", " auto "])

    def test_what_is_no_length(self):
        for name, where in (("stroke-dashoffset", dict(tag="path", more='d="M0 0h9v9"')), ("stroke-width", dict(tag="path", more='d="M0 0h9v9"')),
                            ("r", dict(tag="circle", more="")), ("rx", {}), ("ry", {})):
            self.turns_down(name, [v for v in NOT_NUMBERS if not set(v) & set(";!()")] + ["Auto", "AUTO", "auto auto", "none", "inherit", "5 auto"], "bad-value", **where)
        self.turns_down("r", ["auto"], "bad-value", tag="circle", more="")   # a word for the corners of a rect only
        self.turns_down("stroke-width", ["auto"], "bad-value")

    def test_any_unit_but_px_is_refused_as_a_unit(self):
        # Measured 2026-10-12: the site's renderer draws 1in, 72pt and 25.4mm at a size that depends on the icon it is
        # drawing (nothing of the box at 32 pixels, a seventh of it at 512, where a browser fills it); em and ex are
        # 12 units to it and 16 to a browser. And a share of the box's diagonal is no length a logo needs.
        units = ["5pt", "5pc", "5mm", "5cm", "5in", "5em", "5ex", "5rem", "5ch", "5vw", "5vh", "5vmin", "5vmax", "5Q", "50%", "5e0mm", "+.5e1pt", "-5mm", "0pt", "0%"]
        for name, where in (("stroke-dashoffset", dict(tag="path", more='d="M0 0h9v9"')), ("stroke-width", dict(tag="path", more='d="M0 0h9v9"')),
                            ("r", dict(tag="circle", more="")), ("rx", {}), ("ry", {})):
            err = self.turns_down(name, units, "length-unit", **where)
            self.assertIn("plain numbers for its sizes", str(err))
            self.assertIn(name, str(err))

    def test_a_size_below_zero_is_refused_as_that_and_an_offset_may_be(self):
        for name, where in (("stroke-width", dict(tag="path", more='d="M0 0h9v9"')), ("r", dict(tag="circle", more="")), ("rx", {}), ("ry", {})):
            self.turns_down(name, ["-5", "-5px", "-.5e1", "-0", "-0px", " -5 ", "-1e9"], "negative-size", **where)

    def test_a_length_too_long_or_too_large_is_refused_as_that(self):
        for name, where in (("stroke-dashoffset", dict(tag="path", more='d="M0 0h9v9"')), ("stroke-width", dict(tag="path", more='d="M0 0h9v9"')), ("r", dict(tag="circle", more=""))):
            self.turns_down(name, ["0" * 64 + "5", "0" * 64 + "5px", "1e10", "1e10px", "9e99", "1000000001", "4e38px"], "value-too-long", **where)
        self.takes("r", ["0" * 63 + "5", "0" * 63 + "5px"], tag="circle", more="")


class APosition(Line):
    """position: a length, or a number and % (a share of the drawing's box). x, y, cx, cy, x1, y1, x2, y2; and, not
    below zero, width and height."""

    FORMS = ALength.FORMS + ["50%", "50.0%", "+50%", "5e1%", ".5e2%", " 50% ", "0%", "100%", "150%", "1e9%"]
    NAMES = (("x", {}), ("y", {}), ("width", dict(more='height="9"')), ("height", dict(more='width="9"')), ("cx", dict(tag="circle", more='r="3"')),
             ("cy", dict(tag="circle", more='r="3"')), ("x1", dict(tag="line", more='stroke="#ff0000"')), ("y1", dict(tag="line", more='stroke="#ff0000"')),
             ("x2", dict(tag="line", more='stroke="#ff0000"')), ("y2", dict(tag="line", more='stroke="#ff0000"')))

    def test_what_it_takes(self):
        for name, where in self.NAMES:
            self.takes(name, self.FORMS + ([] if name in ("width", "height") else ["-5", "-5px", "-50%", "-.5e1", "-0", "-1e9"]), **where)

    def test_what_is_no_position(self):
        for name, where in self.NAMES:
            self.turns_down(name, NOT_NUMBERS + ["auto", "50 %", "%50", "50%px", "50px%", "5%5", "center", "left"], "bad-value", **where)

    def test_any_unit_but_px_and_percent_is_refused_as_a_unit(self):
        for name, where in self.NAMES:
            err = self.turns_down(name, ["5pt", "5pc", "5mm", "5cm", "5in", "5em", "5ex", "5rem", "5vw", "5vh", "5Q", "5e0mm", "0pt"], "length-unit", **where)
            self.assertIn("plain numbers for its sizes", str(err))

    def test_a_width_or_a_height_below_zero_is_refused_as_that(self):
        for name, where in (("width", dict(more='height="9"')), ("height", dict(more='width="9"'))):
            self.turns_down(name, ["-5", "-5px", "-50%", "-.5e1", "-0", "-0%"], "negative-size", **where)

    def test_a_position_too_long_or_too_large_is_refused_as_that(self):
        for name, where in self.NAMES:
            self.turns_down(name, ["0" * 64 + "5", "0" * 64 + "5%", "1e10", "1e10%", "9e99", "1000000001px"], "value-too-long", **where)
            self.takes(name, ["0" * 63 + "5", "0" * 63 + "5%"], **where)


class ANumberList(Line):
    """number list: numbers with blanks between them, or one comma, or nothing where the next number begins with a sign
    or a point. points (an even count, 2,000 at most); stroke-dasharray (`none`, or 1 to 16 numbers, none below zero)."""

    def test_what_points_takes(self):
        self.takes("points", ["", "1 2", "1,2", "1 , 2", "1  2", "1\t2\n3\r4", "1,2 3,4 5,6", "1,2,3,4", " 1 2 ", "10-20", "10-20,3.5.5 1e2,4", "1+2", ".5.5", "-1-2-3-4", "1e1-2",
                               "1e2.5", "+1 -2", "1E0 2e-1", "0 0 1e9 -1e9", "1 2 " * (_svg.MAX_POINTS // 2), "0" * 63 + "1 2"], tag="polygon", more="")

    def test_what_is_no_list_of_points(self):
        self.turns_down("points", ["1", "1 2 3", "1,2,3", "1,2 3", ",1 2", "1 2,", "1,,2", "1 ,, 2", "1, ,2", ",", "1;2", "1 2;", "1.2.", "1 2.", "1px 2px", "1% 2%", "1 2 x", "x", "1 2e",
                                    "1e100 2", "1e123", "1 2e100", "0e309 1", "1_0 2", "\u0661 \u0662", "1\u00a02", "1\u20032", "(1 2)", "1 2)", "none", "auto", "1 2 3 4 5",
                                    "1,2 3,4 5", "M1 2", "1-", "1 -", "1 +", "1 .", "1..2", "1,2,"], "bad-value", tag="polygon", more="")

    def test_points_past_what_a_logo_needs_are_refused_as_that(self):
        self.turns_down("points", ["1 2 " * (_svg.MAX_POINTS // 2 + 1), "1 " * 100000, "0" * 64 + "1 2", "1e10 2", "1 9e99", "1 -1e10"], "value-too-long", tag="polygon", more="")

    def test_what_a_dash_list_takes(self):
        self.takes("stroke-dasharray", ["none", " none ", "4", "4 2", "4,2", "4 , 2", "4  2", "4\t2", "4.5.5", "4+2", "+4 +2", ".5 .5e1", "4 2 1", "0", "0 0", "1e9",
                                        "4 2 " * (_svg.MAX_DASHES // 2), "4 " * _svg.MAX_DASHES, "0" * 63 + "4"], tag="path", more='d="M0 0h9" stroke="#ff0000"')

    def test_what_is_no_dash_list(self):
        self.turns_down("stroke-dasharray", [" ", "4,,2", ",4 2", "4 2,", "4, ,2", "4;2", "4 2 x", "x", "None", "NONE", "none 4", "4 none", "auto", "inherit", "4.", "4 2.", "4e100",
                                             "0e309", "1_0", "\u0664 \u0662", "4\u00a02", "4px", "4px 2px", "50%", "5% 10%", "5%10%", "4 2%", "4mm", "(4 2)", "4/2", "4e"], "bad-value",
                        tag="path", more='d="M0 0h9" stroke="#ff0000"')
        refused(self, bare('<path stroke-dasharray="" d="M0 0h9" stroke="#ff0000"/>'), "bad-value")   # a list that names no dash, and is not `none`

    def test_a_dash_below_zero_is_refused_as_that(self):
        self.turns_down("stroke-dasharray", ["-4", "4 -2", "4-2", "4,-2", "-0", "4 2 -.5e1", "-1e-9"], "negative-size", tag="path", more='d="M0 0h9" stroke="#ff0000"')

    def test_more_dashes_than_a_logo_needs_are_refused_as_that(self):
        # with no cap, one rule's dash list was written onto every element: 228 KB in, a favicon of 20 MB out
        self.turns_down("stroke-dasharray", ["4 " * (_svg.MAX_DASHES + 1), "1 " * 30000, "0" * 64 + "4", "4 1e10", "9e99"], "value-too-long",
                        tag="path", more='d="M0 0h9" stroke="#ff0000"')


class ATransform(Line):
    """transform: at most 16 of matrix(6) translate(1 or 2) scale(1 or 2) rotate(1 or 3) skewX(1) skewY(1), each with a
    number list of exactly that many numbers; blanks, one comma or nothing between two of them."""

    def test_what_it_takes(self):
        self.takes("transform", ["", " ", "translate(1)", "translate(1 2)", "translate(1,2)", "translate( 1 , 2 )", "translate(1-2)", "translate(.5.5)", "translate(-1.5e1-2)",
                                 "scale(2)", "scale(2 3)", "scale(-1)", "rotate(45)", "rotate(45 1 1)", "rotate(45,1,1)", "rotate(-45.5 1e1 .5)", "skewX(10)", "skewY(-10)",
                                 "matrix(1 0 0 1 0 0)", "matrix(1,0,0,1,0,0)", "matrix(1 0 0 1-5 3)", "matrix(.5.5.5.5.5.5)", "translate(1,2) scale(2)", "rotate(45 1 1),scale(2)",
                                 "translate(1) , scale(2)", "translate(1)scale(2)", "translate(1)\nscale(2)\trotate(3)", " translate(1 2) ", "translate(1e9)", "scale(1e-9)",
                                 "scale(1) " * _svg.MAX_TRANSFORMS, "translate(" + "0" * 63 + "1)"], tag="g", more="")

    def test_what_is_no_transform(self):
        self.turns_down("transform", [
            "translate()", "scale()", "rotate()", "matrix()", "skewX()", "translate( )",                                # a function with nothing in it
            "translate(1 2 3)", "scale(1 2 3)", "rotate(1 2)", "rotate(1 2 3 4)", "skewX(1 2)", "skewY(1 2)", "matrix(1 0 0 1 0)", "matrix(1 0 0 1 0 0 0)",   # not the count it takes
            "translate(1,,2)", "translate(,1)", "translate(1,)", "translate(1 2),", ",translate(1)", "translate(1),,scale(2)", "translate(1), ,scale(2)", "translate(1) ,",
            "translate (1)", "translate\t(1)", "scale (2)", "Translate(1)", "TRANSLATE(1)", "translateX(1)", "translate3d(1,2,3)", "perspective(1)", "rotateZ(4)", "skew(1)",
            "none", "inherit", "translate", "translate(", "translate(1", "translate 1)", "translate(1))", "(1)", "translate(1) x", "x translate(1)", "translate(1);scale(2)",
            "translate(1px)", "translate(50%)", "rotate(45deg)", "rotate(1turn)", "scale(2x)", "translate(1.)", "translate(1e100)", "translate(0e309)", "translate(1_0)",
            "translate(\u0661)", "translate(1\u00a02)", "\u00a0translate(1)", "translate(1)\u2003scale(2)", "translate(translate(1))", "translate(1 scale(2))"], "bad-value",
                        tag="g", more="")

    def test_more_than_a_logo_needs_is_refused_as_that(self):
        self.turns_down("transform", ["scale(1) " * (_svg.MAX_TRANSFORMS + 1), "scale(1)" * 40000, "translate(1e10)", "translate(1 9e99)", "matrix(1 0 0 1 4e38 0)",
                                      "translate(" + "0" * 64 + "1)"], "value-too-long", tag="g", more="")


class PathData(Line):
    """path data: the command letters, digits, + - . , e E and blanks; 200,000 characters at most. It stays as it was:
    the renderer reads path data with a reader of its own, which does take `5.` for a number."""

    def test_what_it_takes(self):
        self.takes("d", ["", "M0 0", "M0 0h9v9z", "M0,0H9V9Z", "m0 0l9 0 0 9z", "M0 0L9 9", "M0. 0.h5.v5.e0z", "M10 34A22 22 0 0 1 54 34Z", "M0 0a9 9 0 005 0l0 5z", "M0 0C1 2 3 4 5 6S7 8 9 9",
                         "M0 0Q1 2 3 4T5 6", "M-1-2+3.5.5e1-2E-1", " M0 0 ", "M0\n0\tL9\r9", "M0 0" + " 1" * 99998], tag="path", more="")
        self.assertEqual(len("M0 0" + " 1" * 99998), _svg.MAX_PATH)

    def test_what_is_no_path_data(self):
        self.turns_down("d", ["M0 0x", "M0 0;", "M0 0 url(#a)", "M0 0\u00a09", "M\u0660 0", "M0 0 /* */", "M0 0 B1", "M0 0 path('M0 0')", "N0 0", "M0 0'", "M0_0", "M0 0%", "M0 0px",
                              "M0 0 #", "M0 0 (1)", "none", "M0 0\u2028"], "bad-value", tag="path", more="")

    def test_more_than_a_logo_needs_is_refused_as_that(self):
        self.turns_down("d", ["M0 0" + " 1" * 99999, "M0 0" + " 1" * 150000], "value-too-long", tag="path", more="")


class AKeyword(Line):
    """keyword: exactly one of the words the renderer and a browser both read."""

    WORDS = {"fill-rule": ["nonzero", "evenodd"], "clip-rule": ["nonzero", "evenodd"], "stroke-linecap": ["butt", "round", "square"], "stroke-linejoin": ["miter", "round", "bevel"],
             "visibility": ["visible", "hidden", "collapse"], "display": ["inline", "block", "none", "inherit"],
             "shape-rendering": ["auto", "optimizeSpeed", "crispEdges", "geometricPrecision"]}

    def test_the_words_are_the_ones_in_the_table(self):
        self.assertEqual({k: sorted(v) for k, v in _svg._KEYWORDS.items() if k != "clipPathUnits"}, {k: sorted(v) for k, v in self.WORDS.items()})
        self.assertEqual(sorted(_svg._KEYWORDS["clipPathUnits"]), ["objectBoundingBox", "userSpaceOnUse"])

    def test_what_it_takes(self):
        for name, words in self.WORDS.items():
            self.takes(name, words + [" %s " % words[0], "\t%s\n" % words[-1]])
        self.takes("paint-order", ["normal", "fill", "stroke", "markers", "fill stroke", "stroke fill", "stroke fill markers", "markers stroke fill", "stroke  markers", " stroke ",
                                   "fill\tmarkers\nstroke"])

    def test_what_is_no_word_of_its_property(self):
        for name, words in self.WORDS.items():
            near = ["", words[0].upper(), words[0].capitalize(), words[0] + "x", "x" + words[0], words[0] + " " + words[-1], words[0] + ",", words[0][:-1], "initial", "unset",
                    "revert", "0", "1", "true", words[0] + "\u00a0", "\u00a0" + words[0], words[0].replace("o", "\u03bf")]
            self.turns_down(name, [v for v in near + ([] if name == "display" else ["inherit"]) if v not in words], "bad-value")
        # measured 2026-10-12: the site's renderer reads neither of these two joins and keeps the join it had; a browser reads both
        self.turns_down("stroke-linejoin", ["arcs", "miter-clip", "miter clip", "crop", "fallback"], "bad-value")
        self.turns_down("display", ["inline-block", "flex", "grid", "contents", "table", "list-item", "run-in", "None", "NONE", "Inline"], "bad-value")
        self.turns_down("visibility", ["visible hidden", "Hidden", "show", "hide", "0"], "bad-value")
        self.turns_down("shape-rendering", ["optimizespeed", "crispedges", "geometricprecision", "optimizeQuality", "crisp-edges", "pixelated"], "bad-value")
        self.turns_down("paint-order", ["", "stroke stroke", "fill stroke markers fill", "normal fill", "fill normal", "sideways", "Stroke", "stroke,fill", "fill/stroke", "inherit",
                                        "stroke\u00a0fill", "stroke" + " " * _svg.MAX_VALUE + "fill", "markers markers"], "bad-value")

    def test_clip_path_units_on_a_clip_path(self):
        inner = '<defs><clipPath id="c" clipPathUnits="%s"><rect width="1" height="1"/></clipPath></defs><rect clip-path="url(#c)" width="9" height="9"/>'
        for word in ("objectBoundingBox", "userSpaceOnUse", " userSpaceOnUse "):
            self.assertIn('clipPathUnits="%s"' % word.strip(), _svg.clean_svg(bare(inner % word)).text)
        for word in ("", "objectboundingbox", "userspaceonuse", "ObjectBoundingBox", "strokeWidth", "userSpace", "userSpaceOnUse objectBoundingBox", "inherit", "userSpaceOnUse\u00a0"):
            with self.subTest(word=word):
                refused(self, bare(inner % word), "bad-value")


class APaint(Line):
    """paint: fill, stroke, color: at most 64 of the characters a colour is written in, or a url(#id). What a colour IS
    belongs to the colour reader (_colour.py, tests/test_colour.py and test_paint.py); this line only keeps out what
    no colour is written with."""

    def test_what_it_hands_on_to_the_colour_reader(self):
        self.takes("fill", ["#f00", "#FF0000", "#ff0000ff", "red", "RED", "rgb(255,0,0)", "rgb( 255 , 0 , 0 )", "rgb(100%,0%,0%)", "rgb(255 0 0 / 1)", "hsl(0,100%,50%)",
                            "hsl(0deg 100% 50%)", "rgb(+255,-0,0.0)", "rgb(2.55e2,0,0)", " red ", "\tred\n", "none", "NONE", "inherit", "rgba(255.000000, 255.000000, 255.000000, 1.000000)"])
        self.takes("stroke", ["#f00", "red", "rgb(255,0,0)", "none", "inherit"], tag="path", more='d="M0 0h9"')
        self.takes("color", ["#f00", "red", "rgb(255,0,0)", "inherit"])
        self.assertEqual(_svg.clean_svg(bare('<g color="#ff0000"><rect fill="currentColor" width="9" height="9"/></g>')).colours, ["#ff0000"])

    def test_what_no_colour_is_written_with(self):
        for name in ("fill", "stroke", "color"):
            for value in ("", "rgb(1_0,0,0)", "#11_22", "hsl(1_0 50% 50%)", "oklch(50% 0.1 3_0)", "re_d", "_", "red!", "red;", "#f00;", "{red}", "[red]", "r\u00e9d", "\uff52ed",
                          "red\u00a0", "rgb(\u0661,0,0)", "rgb(255,0,0)\u2028", "@red", "$red", "red&amp;blue", "red|blue", "red=1", "red?", "~red", "`red`", "\\72 ed", "red*",
                          "a" * 65, "#" + "f" * 64, "rgb(" + "1" * 62 + ")", "rgb(" + " " * 80 + "255,0,0)", "'red'", "&quot;red&quot;", "red'"):
                with self.subTest(name=name, value=ascii(value)):
                    refused(self, svg('<rect %s="%s" width="9" height="9"/>' % (name, value)), "bad-value")
                    # in a style the style reader may turn it down first, under its own name (and there a `;` only ends the value)
                    for doc in (svg('<rect style="%s:%s" width="9" height="9"/>' % (name, value)), svg("<style>rect{%s:%s}</style>" % (name, value))) if ";" not in value else ():
                        with self.assertRaises(_svg.Refusal) as cm:
                            _svg.clean_svg(doc)
                        self.assertIn(cm.exception.code, ("bad-value", "css-unreadable", "css-at-rule"), str(cm.exception))

    def test_an_underscore_is_part_of_an_id_and_of_nothing_else_in_a_colour(self):
        # R1-22: the class of characters let `_` through (an id needs it), so `rgb(1_0,0,0)` reached the colour reader:
        # Python's own number reader takes 1_0 for ten. It did refuse it; now it never sees it.
        for value in ("rgb(1_0,0,0)", "#11_22", "hsl(1_0 50% 50%)", "hsl(120 5_0% 50%)", "oklch(50% 0.1 3_0)", "rgb(255,0,0_)", "_red", "re_d", "rgb(1__0,0,0)", "1_0", "#_"):
            for doc in (bare('<rect fill="%s" width="9" height="9"/>' % value), bare('<rect style="stroke:%s" width="9" height="9"/>' % value),
                        bare('<style>rect{color:%s}</style><rect width="9" height="9"/>' % value)):
                with self.subTest(value=value, doc=doc[110:160]):
                    refused(self, doc, "bad-value")
        # in the name a url() points at it is a letter like any other: a gradient is still called a gradient
        for value in ("url(#paint0_linear_1_2)", "url( #a_b )", 'url("#a_b")', "url('#a_b')", "url(#SVGID_1_)", "url(#a) red", "url(#a-b.c:d)"):
            with self.subTest(value=value):
                refused(self, bare("<rect fill=\"%s\" width='9' height='9'/>" % value.replace('"', "&quot;")), "colour-gradient")
        refused(self, bare('<rect fill="url(#paint0_linear_1_2)" width="9" height="9"/><linearGradient id="paint0_linear_1_2"/>'), "gradient")
        for value in ("url(#)", "url()", "url(#a b)", "url(#" + "a" * 65 + ")", "url(#a" + " " * 80 + ")"):
            with self.subTest(value=value):
                with self.assertRaises(_svg.Refusal) as cm:
                    _svg.clean_svg(bare('<rect fill="%s" width="9" height="9"/>' % value))
                self.assertIn(cm.exception.code, ("css-url", "bad-value"))


class AnId(Line):
    """id: an ASCII letter or `_`, then letters, digits and `_ - . :`; 64 characters at most. Taken as it is written:
    a renderer takes no blank off an id."""

    def test_what_it_takes(self):
        for value in ("a", "A", "_", "a1", "Layer_1", "clip0_12_34", "SVGID_1_", "a-b", "a.b", "a:b", "_-.:", "a" * 64, "Ebene_1", "path111"):
            with self.subTest(value=value):
                clean = _svg.clean_svg(bare('<rect id="%s" width="9" height="9"/>' % value))
                self.assertIn('<rect id="%s"' % value, clean.text)
                clip = '<defs><clipPath id="%s"><rect width="4" height="4"/></clipPath></defs><rect clip-path="url(#%s)" width="9" height="9"/>' % (value, value)
                self.assertIn('clip-path="url(#%s)"' % value, _svg.clean_svg(bare(clip)).text)

    def test_what_is_no_id(self):
        for value in ("", " ", " a", "a ", "a b", "1a", "-a", ".a", ":a", "a/b", "a,b", "a;b", "a#b", "#a", "a(b)", "a" * 65, "Frame 1", "brand/logo/mark", "1a2b3c4d5e",
                      "\u00e9", "a\u00e9", "Gr\u00f6\u00dfe", "\u65e5\u672c", "a\u0661", "a\u00a0", "a\u200b", "&#9;a", "a&#10;", "a\ufe0f", "a'b", "a&quot;b", "a&lt;b", "a&amp;b",
                      "a\\62", "a%b", "a+b", "a=b", "a@b", "a*b", "a!b"):
            with self.subTest(value=value):
                refused(self, bare('<rect id="%s" width="9" height="9"/>' % value), "bad-value")


class AClass(Line):
    """class: names of ASCII letters, digits and `_ - .` with spaces between them; 200 characters at most. It is read
    (a rule may name it) and never written."""

    def test_what_it_takes(self):
        for value, names in (("a", {"a"}), ("a b", {"a", "b"}), (" a  b ", {"a", "b"}), ("cls-1 st0", {"cls-1", "st0"}), ("a.b _c -d 0", {"a.b", "_c", "-d", "0"}),
                             ("", set()), (" ", set()), ("a a", {"a"}), ("x" * 200, {"x" * 200}), (" ".join(["ab"] * 66), {"ab"})):
            with self.subTest(value=value):
                clean = _svg.clean_svg(bare("<style>.a{fill:#ff0000}</style>" + '<rect class="%s" width="9" height="9"/>' % value))
                self.assertEqual(clean.colours, ["#ff0000"] if "a" in names else ["#000000"])
                self.assertNotIn("class", clean.text)

    def test_what_is_no_class(self):
        for value in ("a,b", "a;b", "a/b", "a#b", "a:b", "a(b)", "x" * 201, "a&#9;b", "a&#10;b", "a\u00a0b", "\u2003a", "\u00e9", "gr\u00f6\u00dfe", "a\u0661", "a\u200bb", "a'b",
                      "a&quot;b", "a&lt;b", "a*", "a+b", "a%", "a\\62", "a!", "a@b", "a=b", "a\ufe0f"):
            with self.subTest(value=ascii(value)):
                refused(self, bare('<rect class="%s" width="9" height="9"/>' % value), "bad-value")


class AClipPath(Line):
    """clip-path: `none`, or url(#id) with an id of the grammar, 80 characters at most; blanks may stand inside the brackets."""

    CLIP = '<defs><clipPath id="c"><rect width="4" height="4"/></clipPath><clipPath id="a-b.c:d_e"><rect width="4" height="4"/></clipPath></defs>'

    def places(self, name, value, **where):
        escaped = value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
        docs = [bare(self.CLIP + '<rect clip-path="%s" width="9" height="9"/>' % escaped), bare(self.CLIP + '<rect style="clip-path:%s" width="9" height="9"/>' % escaped)]
        return docs + [bare(self.CLIP + "<style>rect{clip-path:%s}</style><rect width='9' height='9'/>" % escaped.replace("&quot;", '"'))]

    def test_what_it_takes(self):
        self.takes("clip-path", ["none", " none ", "url(#c)", "url( #c )", "url(\t#c\n)", " url(#c) ", "url(#a-b.c:d_e)", "url(#" + "a" * 64 + ")", "url(#nobody)"])

    def test_what_is_no_clip_path(self):
        self.turns_down("clip-path", ["None", "NONE", "auto", "inherit", "#c", "c", "URL(#c)", "Url(#c)", "url (#c)", "url(#c) none", "none url(#c)", "url(#c) url(#c)",
                                      "url(#c)x", "url(#1c)", "url(#-c)", "url(#" + "a" * 65 + ")", "url(#c" + " " * 80 + ")", "circle(5)", "inset(1)",
                                      "polygon(0 0,9 0,9 9)", "path('M0 0')", "border-box", "url(#c) border-box"], "bad-value")
        for value in ('url("#c")', "url('#c')"):   # in quotes it is a fragment to the style check, and no clip-path of this grammar
            refused(self, bare(self.CLIP + "<rect clip-path=\"%s\" width='9' height='9'/>" % value.replace('"', "&quot;")), "bad-value")

    def test_a_name_that_is_none_or_not_plain_is_refused_before_it_is_a_clip_path(self):
        # `url(#)` points at nothing, and \w took any script's letters and digits for part of a name
        for value in ("url(c)", "url(#)", "url( # )", "url()", "url( )", "url(#\u00e9)", "url(#c\u00e9)", "url(#\u0661)", "url(#c\u0661)", "url(#\u65e5\u672c)", "url(#c d)", "url(#c/d)",
                      "url(#c,d)", "url(#c)url(https://x.example/a)", "url(https://x.example/a#c)", "url(a.svg#c)", "url(\u00a0#c)", "url(#c\u2003)"):
            with self.subTest(value=ascii(value)):
                refused(self, bare(self.CLIP + '<rect clip-path="%s" width="9" height="9"/>' % value), "css-url")
                refused(self, bare(self.CLIP + '<rect style="clip-path:%s" width="9" height="9"/>' % value), "css-url")
                refused(self, bare(self.CLIP + '<rect style="fill:%s" width="9" height="9"/>' % value), "css-url")
                with self.assertRaises(_svg.Refusal):
                    _css.check_urls(value)
        for value in ("url(#c)", "url(#C_1-2.3:4)", 'url("#c")', "url('#c')", "url( #c )"):
            _css.check_urls(value)


class TheViewBox(Line):
    """viewBox: four numbers, as a number list; the width and the height from 0.01 to 1,000,000 and neither more than
    20 times the other. It is written into the cleaned file as it was read."""

    DOC = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s"><path fill="#111111" d="M0 0h9v9z"/></svg>'

    def test_what_it_takes(self):
        for value, box in (("0 0 10 20", (0, 0, 10, 20)), ("0,0,10,20", (0, 0, 10, 20)), ("0, 0, 10, 20", (0, 0, 10, 20)), ("0 , 0 , 10 , 20", (0, 0, 10, 20)),
                           (" 0  0 10 20 ", (0, 0, 10, 20)), ("0\t0\n10\r20", (0, 0, 10, 20)), ("+0 -0 10.0 2e1", (0, 0, 10, 20)), ("-5 -5.5 2.5E1 25", (-5, -5.5, 25, 25)),
                           ("0-0 10 20", (0, 0, 10, 20)), (".0.0 10 20", (0, 0, 10, 20)), ("0 0 .01 0.01", (0, 0, 0.01, 0.01)), ("1e6 -1e6 1e6 1000000", (1e6, -1e6, 1e6, 1e6)),
                           ("0 0 100 5", (0, 0, 100, 5)), ("0 0 5 100", (0, 0, 5, 100))):
            with self.subTest(value=value):
                clean = _svg.clean_svg((self.DOC % value).encode())
                self.assertEqual(clean.view_box, box)
                self.assertIn('viewBox="%s"' % " ".join(clean.text.split('viewBox="')[1].split('"')[0].split()), clean.text)

    def test_what_is_no_view_box(self):
        for value in ("", " ", "0 0 10", "0 0 10 20 30", "0,,0 10 20", "0 0 10 20,", ",0 0 10 20", "0 0 10,,20", "0, ,0 10 20", "0;0;10;20", "0 0 10 20;", "0 0 10px 20px", "0 0 100% 100%",
                      "0 0 10. 20", "0. 0 10 20", "0 0 10 20.e0", "0 0 1e100 20", "0 0 10 0e309", "0 0 1e999 10", "0 0 1_0 20", "0 0 \u0661\u0660 20", "0\u20030 10 20", "0 0\u00a010 20",
                      "0 0 10 20\u2028", "0 0 infinity 10", "0 0 nan 10", "0 0 0x10 10", "0 0 0 20", "0 0 10 0", "0 0 -10 20", "0 0 10 -20", "0 0 10-20", "none", "auto", "0 0 ten 20",
                      "(0 0 10 20)", "0 0 10 20 ,", "0 0 0.009 0.009", "0 0 1000001 1000001", "0 0 10 201", "0 0 201 10", "1000001 0 10 20", "0 -1e7 10 20", "0 0 " + "0" * 64 + "9 9",
                      "0 0 1e10 1e10", "0 0 9e99 9e99"):
            with self.subTest(value=ascii(value)):
                refused(self, (self.DOC % value).encode("utf-8"), "bad-view-box")


class TheAspect(Line):
    """preserveAspectRatio (on the outer svg): none, or one of the nine alignments, then optionally meet or slice."""

    def test_what_it_takes(self):
        aligns = ["x%sY%s" % (x, y) for x in ("Min", "Mid", "Max") for y in ("Min", "Mid", "Max")]
        for value in ["none", " none ", "none meet", "none slice"] + aligns + [a + " meet" for a in aligns] + [a + " slice" for a in aligns] + ["xMidYMid  meet", "xMidYMid\tslice"]:
            with self.subTest(value=value):
                clean = _svg.clean_svg(svg(root='preserveAspectRatio="%s"' % value))
                self.assertIn('viewBox="0 0 64 64" preserveAspectRatio=', clean.text)
        self.assertNotIn("preserveAspectRatio", _svg.clean_svg(svg()).text)

    def test_what_is_none_of_its_values(self):
        for value in ("", "None", "NONE", "xmidymid", "XMIDYMID", "xMidyMid", "xMid", "YMid", "xMidYMid meet slice", "meet", "slice", "meet xMidYMid", "defer xMidYMid",
                      "xMidYMid defer", "xMidYMid,meet", "xMidYMid;", "xMidYMidmeet", "xMidYMid Meet", "xMinYMin xMaxYMax", "xMidYMid\u00a0meet", "\u2003xMidYMid", "xMidYMid\u2028",
                      "xM\u0131dYMid", "x\u039cidYMid", "xMidYMid" + " " * 80 + "meet", "auto", "inherit", "contain", "cover", "1", "xMidYMid 1"):
            with self.subTest(value=ascii(value)):
                refused(self, svg(root='preserveAspectRatio="%s"' % value), "bad-value")


class TheOuterSize(Line):
    """width and height of the outer svg: never kept. A number above zero with px, pt, pc, mm, cm, in or nothing, or
    a number and %. With a viewBox, two lengths are in one unit and of the viewBox's own shape (to one part in a
    hundred thousand); without one, both are plain or px, and they are the box."""

    DOC = '<svg xmlns="http://www.w3.org/2000/svg" %s><path fill="#111111" d="M0 0h9v9z"/></svg>'

    def test_what_stands_beside_a_view_box(self):
        for attrs in ('width="64" height="32"', 'width="128" height="64"', 'width="6.4" height="3.2"', 'width="64px" height="32px"', 'width="64" height="32px"',
                      'width="64mm" height="32mm"', 'width="2in" height="1in"', 'width="64pt" height="32pt"', 'width="2cm" height="1cm"', 'width="2pc" height="1pc"',
                      'width="100%" height="100%"', 'width="50%" height="7%"', 'width="64"', 'height="32"', 'width="7"', 'height="7mm"', 'width="100%"', 'width="64" height="100%"',
                      'width="100%" height="5"', 'width="+64" height="3.2e1"', 'width=" 64 " height="&#10;32&#9;"', 'width="64.0006" height="32"', 'width="64" height="32.0003"',
                      'width="63.9994" height="32"', 'width="375" height="187.4999955"', 'width="1e9" height="5e8"', 'width="0.0001" height="0.00005"'):
            with self.subTest(attrs=attrs):
                clean = _svg.clean_svg((self.DOC % ('viewBox="0 0 64 32" ' + attrs)).encode())
                self.assertIn('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 32">', clean.text)
                self.assertEqual(clean.notes, [])

    def test_a_width_and_a_height_of_another_shape_than_the_view_box_are_refused_by_name(self):
        # The cleaned file keeps the viewBox alone. Measured 2026-10-12: an svg of 40 by 20 round a viewBox of 10 by 20
        # is drawn at half the size the cleaned file is, and with preserveAspectRatio="none" it is stretched.
        for attrs in ('width="64" height="64"', 'width="32" height="64"', 'width="64" height="33"', 'width="64" height="32.1"', 'width="64.1" height="32"', 'width="1" height="1000"',
                      'width="64.001" height="32"', 'width="64" height="32.0005"', 'width="63.999" height="32"',   # a part in a hundred thousand is the line
                      'width="64px" height="64px"', 'width="64mm" height="64mm"', 'width="64" height="64" preserveAspectRatio="none"',
                      'width="640" height="32" preserveAspectRatio="xMinYMin slice"',
                      # in two units the two are one shape to a browser and another to a renderer that reads an inch its own way
                      'width="2in" height="96px"', 'width="64mm" height="32pt"', 'width="64" height="32mm"', 'width="64pt" height="32"'):
            with self.subTest(attrs=attrs):
                err = refused(self, (self.DOC % ('viewBox="0 0 64 32" ' + attrs)).encode(), "root-size")
                for word in ("viewBox", "width", "height", "Ask the tool"):
                    self.assertIn(word, str(err))
        for attrs in ('width="0" height="32"', 'width="64" height="0"', 'width="0"', 'height="0.0"', 'width="0e5" height="0"', 'width="0px"', 'height="0mm"'):
            with self.subTest(attrs=attrs):
                self.assertIn("nothing", str(refused(self, (self.DOC % ('viewBox="0 0 64 32" ' + attrs)).encode(), "root-size")))

    def test_what_is_no_width_or_height_of_the_outer_svg(self):
        for value, code in (("", "bad-value"), ("auto", "bad-value"), ("64.", "bad-value"), ("64 px", "bad-value"), ("64PX", "bad-value"), ("64MM", "bad-value"), ("6e100", "bad-value"),
                            ("64,", "bad-value"), ("64 32", "bad-value"), ("\u0666\u0664", "bad-value"), ("64\u00a0", "bad-value"), ("100 %", "bad-value"), ("%", "bad-value"),
                            ("64em", "length-unit"), ("64ex", "length-unit"), ("64rem", "length-unit"), ("64vw", "length-unit"), ("64vh", "length-unit"), ("64ch", "length-unit"),
                            ("-64", "negative-size"), ("-64mm", "negative-size"), ("-100%", "negative-size"), ("-0", "negative-size"),
                            ("0" * 64 + "9", "value-too-long"), ("1e10", "value-too-long"), ("9e99mm", "value-too-long")):
            for doc in (self.DOC % ('viewBox="0 0 64 32" width="%s"' % value), self.DOC % ('viewBox="0 0 64 32" height="%s"' % value), self.DOC % ('width="%s" height="32"' % value)):
                with self.subTest(value=ascii(value), doc=doc[40:80]):
                    refused(self, doc.encode("utf-8"), code)

    def test_without_a_view_box_the_width_and_height_are_the_box_and_are_plain(self):
        for attrs, box in (('width="64" height="32"', "0 0 64 32"), ('width="64px" height="32px"', "0 0 64 32"), ('width="6.4e1" height="+32.0"', "0 0 6.4e1 +32.0"),
                           ('width="0.01" height=".2"', "0 0 0.01 .2"), ('width=" 64 " height="32"', "0 0 64 32")):
            with self.subTest(attrs=attrs):
                self.assertIn('viewBox="%s"' % box, _svg.clean_svg((self.DOC % attrs).encode()).text)
        for attrs in ("", 'width="64"', 'height="32"', 'width="100%" height="100%"', 'width="64" height="50%"', 'width="64mm" height="32mm"', 'width="2in" height="1in"',
                      'width="64pt" height="32pt"', 'width="2cm" height="1cm"', 'width="2pc" height="1pc"', 'width="64" height="32mm"', 'width="0" height="32"', 'width="64" height="0"'):
            with self.subTest(attrs=attrs):
                refused(self, (self.DOC % attrs).encode(), "no-size")


class NothingHere(Line):
    """Three values that only say "nothing here" are left out without a word: filter, mask and vector-effect of
    `none`, and mix-blend-mode of `normal`. Before 2026-10-12 each was refused with a sentence that said the effect
    was used."""

    def test_the_one_value_of_each_that_does_nothing_is_left_out_and_nothing_is_said(self):
        for name, word in _svg.NO_EFFECT.items():
            for doc in (bare('<rect %s="%s" width="9" height="9"/>' % (name, word)), bare('<rect %s=" %s&#10;" width="9" height="9"/>' % (name, word)),
                        bare('<rect style="%s:%s" width="9" height="9"/>' % (name, word)), bare('<rect style="fill:#111111; %s : %s ;stroke:none" width="9" height="9"/>' % (name, word)),
                        bare("<style>rect{%s:%s}</style><rect width='9' height='9'/>" % (name, word)), bare("<style>.unused{%s:%s}</style><rect width='9' height='9'/>" % (name, word)),
                        bare('<g %s="%s"><rect width="9" height="9"/></g>' % (name, word)), svg(root='%s="%s"' % (name, word))):
                with self.subTest(name=name, doc=doc[110:170]):
                    clean = _svg.clean_svg(doc)
                    self.assertEqual(clean.notes, [])
                    self.assertNotIn(name, clean.text)
        self.assertEqual(sorted(_svg.NO_EFFECT.items()), [("filter", "none"), ("mask", "none"), ("mix-blend-mode", "normal"), ("vector-effect", "none")])

    def test_every_other_value_is_refused_by_name_as_before(self):
        for name, code, values in (("filter", "filter", ["url(#f)", "blur(2px)", "None", "NONE", "none none", "", "inherit", "normal", "drop-shadow(0 0 1px red)"]),
                                   ("mask", "mask", ["url(#m)", "None", "", "inherit", "normal", "none url(#m)"]),
                                   ("vector-effect", "vector-effect", ["non-scaling-stroke", "None", "", "inherit", "normal", "non-scaling-size"]),
                                   ("mix-blend-mode", "blend", ["multiply", "screen", "Normal", "NORMAL", "", "none", "inherit", "normal multiply"])):
            for value in values:
                with self.subTest(name=name, value=value):
                    with self.assertRaises(_svg.Refusal) as cm:
                        _svg.clean_svg(bare('<rect %s="%s" width="9" height="9"/>' % (name, value)))
                    self.assertIn(cm.exception.code, (code, "css-url"))
                    if value and "(" not in value:
                        refused(self, bare('<rect style="%s:%s" width="9" height="9"/>' % (name, value)), code)
                        refused(self, bare("<style>.unused{%s:%s}</style><rect width='9' height='9'/>" % (name, value)), code)
        # the markers have no such value in this grammar: `none` there is refused as any marker is
        for name in ("marker-start", "marker-mid", "marker-end"):
            refused(self, bare('<path %s="none" d="M0 0h9"/>' % name), "marker")


class TheGrammarIsTheTable(unittest.TestCase):
    """The grammar is one table: every name the cleaned file can carry, and every name this check reads to decide
    something, has a line in it, and nothing is kept that has none."""

    def test_every_kept_name_has_its_line_and_no_line_is_left_over(self):
        kept = _svg.PROPS | _svg.GEOMETRY | _svg.ROOT_ONLY | {"id", "class", "clipPathUnits"}
        self.assertEqual(set(_svg.GRAMMAR), kept)
        self.assertEqual(set(_svg.ROOT_GRAMMAR), kept)
        self.assertEqual({n for n in kept if _svg.ROOT_GRAMMAR[n] is not _svg.GRAMMAR[n]}, {"width", "height"}, "the outer svg has its own line for these two only")
        self.assertFalse(kept & set(_svg.REFUSED_ATTRS), "what is refused by name is not also kept")
        self.assertFalse(kept & _svg.PROPS_DROP)
        self.assertNotIn("pathLength", kept)

    def test_a_line_answers_none_or_why_not_and_nothing_else(self):
        for name, line in sorted(_svg.GRAMMAR.items()):
            for value in ("", "5", "-5", "5px", "5mm", "50%", "none", "auto", "a", "url(#a)", "0 0 9 9", "translate(1)", "M0 0", "x" * 300, "1 " * 5000, "9e99", "\u00a0"):
                with self.subTest(name=name, value=value[:20]):
                    why = line(value)
                    self.assertTrue(why is None or why in ("bad", "unit", "below zero") or (isinstance(why, tuple) and why[0] == "long" and why[1]), why)

    def test_the_cleaned_text_holds_only_what_the_grammar_wrote(self):
        # every attribute of a cleaned file is in the table, and its value passes its own line again
        import xml.etree.ElementTree as ET
        docs = [svg(), T.real_svg(T.REAL_COLOUR), T.real_svg(T.REAL_MONO),
                bare('<style>.a{stroke:#00f;stroke-width:2px;stroke-dasharray:4 2;stroke-linejoin:round;paint-order:stroke}</style><defs><clipPath id="c" clipPathUnits="userSpaceOnUse">'
                     '<rect width="50%" height="9"/></clipPath></defs><g class="a" transform="translate(1 2) scale(.5)" clip-path="url(#c)"><circle cx="50%" cy="5" r="3" fill="red"/>'
                     '<polygon points="1,1 9,1 5,9" fill-rule="evenodd"/><ellipse rx="2" ry="auto"/><line x2="9" y2="9"/></g>', root='preserveAspectRatio="xMidYMid meet" width="64" height="64"')]
        for doc in docs:
            root = ET.fromstring(_svg.clean_svg(doc).text)
            for element in root.iter():
                tag = element.tag.split("}")[1]
                self.assertIn(tag, _svg.DRAWING | _svg.CONTAINERS)
                for name, value in element.attrib.items():
                    with self.subTest(tag=tag, name=name, value=value[:40]):
                        if tag == "svg" and name == "viewBox":
                            continue
                        self.assertIn(name, _svg.GRAMMAR)
                        self.assertEqual(_svg._validate(name, value), value)


class WrittenOut(unittest.TestCase):
    """The cleaned text is never larger than a file that may come in. One rule's value is checked once and then written
    onto every element the rule applies to: before 2026-10-12 a file of 228 KB was installed as a favicon of 20 MB, and
    one of 285 KB took 143 seconds and 5.57 GB to be listed as a favicon of 300 MB."""

    def test_a_file_whose_cleaned_text_would_be_too_large_is_refused_by_name(self):
        rule = "<style>*{fill:#111111;stroke:#222222;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:4;stroke-dasharray:4 2;paint-order:stroke}</style>"
        paths = '<path d="M0 0"/>' * 4990
        small = svg(rule + paths)
        self.assertLess(len(small), 90 * 1024)
        err = refused(self, small, "output-too-large")
        for word in ("far larger", "logo", "512 KB", "Ask the tool"):
            self.assertIn(word, str(err))
        # the same rule on as many elements as do fit is written out whole
        clean = _svg.clean_svg(svg(rule + '<path d="M0 0"/>' * 2000))
        self.assertLessEqual(len(clean.text), _svg.MAX_OUTPUT)
        self.assertEqual(clean.text.count("<path"), 2000 + 1)

    def test_the_cap_is_the_size_of_a_file_that_may_come_in_and_both_sides_of_it_are_held(self):
        self.assertEqual(_svg.MAX_OUTPUT, _svg.MAX_BYTES)

        def doc(first, second):   # 4,900 paths that a rule gives two colours each, and two more that fill the room that is left
            return bare("<style>path{fill:#111111;stroke:#222222}</style>" + '<path d="M0 0"/>' * 4900 + '<path d="%s"/><path d="%s"/>' % ("M" * first, "M" * second))

        room = _svg.MAX_OUTPUT - len(_svg.clean_svg(doc(0, 0)).text)
        at_cap = doc(room // 2, room - room // 2)
        self.assertLess(len(at_cap), _svg.MAX_BYTES)
        clean = _svg.clean_svg(at_cap)
        self.assertEqual(len(clean.text), _svg.MAX_OUTPUT)
        self.assertEqual(len(clean.text.encode("utf-8")), _svg.MAX_OUTPUT, "every character of a cleaned file is one byte")
        self.assertEqual(_svg.clean_svg(clean.text.encode()).text, clean.text, "and what came out can go in again")
        refused(self, doc(room // 2 + 1, room - room // 2), "output-too-large")

    def test_the_files_that_grew_without_end_are_refused_at_once(self):
        # each of these is inside every cap on what comes in (the sizes in kilobytes are the ones that were reported)
        dash = lambda chars, elements, shape='<rect width="10" height="10" fill="#b4531a"/>': bare(
            "<style>*{stroke-dasharray:%s}</style>" % ("1 " * chars)[:chars].strip() + shape * elements)
        files = [dash(4000, 4990), dash(60000, 4990, '<path d="M0 0h1"/>'), dash(30, 4990), dash(120, 4990, "<g/>"),
                 bare("<style>*{stroke-width:%s1}</style>" % ("0" * 60000) + "<path/>" * 4990),
                 bare("<style>*{fill:%s#111111}</style>" % (" " * 60000) + "<path/>" * 4990),
                 bare("<style>*{clip-path:url(%s#c)}</style>" % (" " * 60000) + "<path/>" * 4990),
                 bare("<style>*{paint-order:stroke%sfill}</style>" % (" " * 60000) + "<path/>" * 4990),
                 bare("<style>%s</style>" % "".join("*{stroke-dasharray:%s}" % " ".join([str(i)] * 16) for i in range(190)) + "<path/>" * 4990)]
        outcomes = judged(self, files)
        for i, (data, out) in enumerate(zip(files, outcomes)):
            with self.subTest(file=i):
                self.assertLessEqual(len(data), _svg.MAX_BYTES)
                if out["code"] == "ok":   # a value that is short once its blanks are off, on as many elements as fit
                    self.assertLessEqual(len(out["text"]), _svg.MAX_OUTPUT)
                else:
                    self.assertIn(out["code"], ("value-too-long", "bad-value", "output-too-large"))
        self.assertEqual([out["code"] for out in outcomes], ["value-too-long", "value-too-long", "ok", "value-too-long", "value-too-long", "ok", "bad-value", "bad-value", "ok"])

    def test_the_slowest_files_a_search_inside_every_cap_found_are_judged_in_bounded_time(self):
        # Searched 2026-10-13 with generated files (by hand, at random and by climbing from the slowest): the work is
        # elements x (selectors + values), and it is the same work whether the file comes out whole, is found blank
        # at the end or is too large written out. On a quiet machine each of these takes under a second.
        most = _svg.MAX_ELEMENTS - 40
        five = "fill:#111;stroke:#222;stroke-width:2;opacity:1;fill-rule:evenodd"
        long = "stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:4;stroke-dashoffset:1;stroke-dasharray:4 2"
        files = [
            # 200 rules that every element matches, on groups 30 deep that draw nothing: a blank mark, found last of all
            bare("<style>%s</style>" % ("g{%s}" % five * _svg.MAX_SELECTORS) + "<g>" * 30 + '<g id="k" style="fill:red;color:red;stroke:red"/>' * most + "</g>" * 30),
            # the same on shapes with a style and some attributes of their own: written out whole
            bare("<style>%s</style>" % ("path{%s}" % five * _svg.MAX_SELECTORS) + '<path id="k" class="k" style="fill:red;color:red;stroke:red" data-a="" data-b=""/>' * most
                 + '<path d="M0 0h9v9z"/>'),
            # and with values enough on every element to pass the cap: refused only when it is written out
            bare("<style>%s</style>" % ("*{%s;%s}" % (five, long) * (_svg.MAX_DECLARATIONS // 10)) + "".join('<rect id="k%d" style="fill:red;color:red;stroke:red;display:block;opacity:1"/>' % i for i in range(most))),
        ]
        for data in files:
            self.assertLessEqual(len(data), _svg.MAX_BYTES)
        outcomes = judged(self, files, each=5.0)
        self.assertEqual([out["code"] for out in outcomes], ["blank-mark", "ok", "output-too-large"])
        self.assertLessEqual(len(outcomes[1]["text"]), _svg.MAX_OUTPUT)

    def test_whatever_is_accepted_comes_out_no_larger_than_the_cap_and_in_plain_ascii(self):
        rules = ["fill:#111111", "stroke:#222222", "stroke-width:2px", "stroke-dasharray:" + " ".join(["1234567.5"] * 16), "stroke-linecap:round", "stroke-linejoin:bevel",
                 "stroke-miterlimit:4", "stroke-dashoffset:-1.5", "fill-rule:evenodd", "clip-rule:evenodd", "opacity:1", "fill-opacity:1", "stroke-opacity:1", "color:#333333",
                 "display:inline", "visibility:visible", "clip-path:url(#%s)" % ("c" * 64), "shape-rendering:geometricPrecision", "paint-order:markers stroke fill"]
        sheet = "<style>*{%s}</style>" % ";".join(rules)
        seen = set()
        for elements in (1, 10, 100, 700, 800, 900, 1000, 1500, 4990):
            for shape in ('<circle r="1"/>', '<path d="M0 0"/>', '<rect id="%s" width="9" height="9"/>' % ("i" * 64), '<polygon points="%s"/>' % ("1 2 " * 20)):
                data = bare(sheet + shape * elements)
                if len(data) > _svg.MAX_BYTES:
                    continue
                try:
                    clean = _svg.clean_svg(data)
                except _svg.Refusal as e:
                    seen.add(e.code)
                    self.assertEqual(e.code, "output-too-large", "%d of %s: %s" % (elements, shape[:20], e))
                else:
                    seen.add("ok")
                    self.assertLessEqual(len(clean.text), _svg.MAX_OUTPUT)
                    self.assertTrue(clean.text.isascii() and clean.text.isprintable())
        self.assertEqual(seen, {"ok", "output-too-large"})


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
                  b"<html><body>" + b"<svg/>" * ((_input.MAX_BYTES - 12) // 6),             # 10 MB, 1.7 million drawings
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
