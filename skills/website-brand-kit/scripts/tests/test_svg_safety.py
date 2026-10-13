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
import contextlib
import encodings.aliases
import io
import json
import math
import os
import re
import signal
import subprocess
import sys
import tempfile
import unittest

import _testutil as T
import brand_intake
import _css
import _input
import _install
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


def through_the_command(testcase, data, *extra, name="logo.svg"):
    """What the intake's own command makes of a file: `brand_intake.py install --site SITE --input FILE --dry-run
    --json`, the call the assistant makes, on a site made from the starter (with no image tool in it: a file the
    check has read is stopped at the next step, where the icons would be drawn). The command's answer, as a dict."""
    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    site = T.make_starter_site(os.path.join(tmp.name, "site"), with_modules=False)
    path = os.path.join(tmp.name, name)
    with open(path, "wb") as f:
        f.write(data)
    out = io.StringIO()
    stops = [getattr(signal, n) for n in _install.SIGNALS if hasattr(signal, n)]
    before = [(s, signal.getsignal(s)) for s in stops]   # an install leaves the stop signals handled: a test goes on living
    try:
        with contextlib.redirect_stdout(out):
            brand_intake.main(["install", "--site", site, "--input", path, "--dry-run", "--json"] + list(extra))
    finally:
        for s, handler in before:
            signal.signal(s, handler)
    return json.loads(out.getvalue())


READ = ("sharp-missing", "no-node")   # where the command stops a file that the check has read, in a site with no image tool


def without_doctype(data):
    """What the DOCTYPE sentence says to do, done: the declaration deleted, from its `<!DOCTYPE` up to the `>` that ends
    it (a `>` inside an address in quotes does not end it), and nothing else: an `<svg` after it stays."""
    start, quote = data.index(b"<!DOCTYPE"), None
    for pos in range(start, len(data)):
        c = data[pos:pos + 1]
        if quote:
            quote = None if c == quote else quote
        elif c in (b'"', b"'"):
            quote = c
        elif c == b">":
            return data[:start] + data[pos + 1:]
    raise ValueError("a declaration that never closes")


class ThroughTheCommand(unittest.TestCase):
    """The rules of 2026-10-13, each through the one door production has: the intake's own command, given a file."""

    def test_what_the_check_refuses_the_command_refuses_with_the_same_sentence_and_what_it_reads_goes_on_to_the_icons(self):
        clip = '<clipPath id="c"><rect width="4" height="4"/></clipPath>'
        big_clip = '<clipPath id="c"><polygon points="%s"/></clipPath>' % ("1 2 " * 1000)   # 2,000 numbers
        dashed = 'stroke="#111111" stroke-dasharray="0.01"'
        rows = (
            ("a dashed line with one end a share, past the budget", ('<svg %s viewBox="0 0 10 1">%s<path fill="#111111" d="M0 0h1v1z"/></svg>' % (NS, '<line y1="100%%" y2="10" %s/>' % dashed * 112)).encode(), "too-many-dashes"),
            ("the same line, as many as the budget holds", ('<svg %s viewBox="0 0 10 1">%s<path fill="#111111" d="M0 0h1v1z"/></svg>' % (NS, '<line y1="100%%" y2="10" %s/>' % dashed * 111)).encode(), None),
            ("ids that read like a piece of a style", bare('<g id="javascript:logo"><rect id="expression(layer)" width="9" height="9" fill="#111111"/></g>'), None),
            ("a style's value padded past the cap", svg('<rect style="fill:%sred" width="9" height="9"/>' % (" " * 9000)), "value-too-long"),
            ("the same value, not padded", svg('<rect style="fill: red " width="9" height="9"/>'), None),
            ("a paint that names an id", bare(clip + '<rect fill="url(#c)" width="9" height="9"/>'), "colour-gradient"),
            ("a shape inside a clip path that is clipped", bare(clip + '<clipPath id="d"><rect clip-path="url(#c)" width="9" height="9"/></clipPath><rect clip-path="url(#d)" width="9" height="9"/>'), "clip-in-clip"),
            ("display on a clip path", bare(clip.replace("<clipPath ", '<clipPath display="none" ') + '<rect clip-path="url(#c)" width="9" height="9"/>'), "clip-display"),
            ("a clip-path on the outer svg", bare(clip + '<rect width="9" height="9"/>', root='clip-path="url(#c)"'), "root-clip-path"),
            ("a plain clip path whose id starts with a digit", bare(clip.replace('"c"', '"8ce47d5fb1"') + '<g clip-path="url(#8ce47d5fb1)"><rect width="9" height="9"/></g>'), None),
            ("a DOCTYPE on a line of its own", b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n' + svg(), "doctype"),
            ("an editor's leftovers in a style", bare('<path style="fill:#111111;marker:none;isolation:auto;image-rendering:auto;-inkscape-stroke:none" d="M0 0h9v9z"/>'), None),
            ("the class names of a style library", svg(root='class="h-6 w-6 md:h-8 hover:text-gray-500"'), None),
            ("a label that reads like a piece of a style", svg(root='role="img" aria-label="JavaScript: the logo" data-name="expression(layer)"'), None),
            # the rules of round 6
            ("a DOCTYPE over two lines", b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n' + svg(), "doctype"),
            ("a DOCTYPE on the line of the svg", b'<?xml version="1.0"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">' + svg(), "doctype"),
            ("a DOCTYPE with definitions of its own", b'<!DOCTYPE svg [\n<!ENTITY ns_svg "http://www.w3.org/2000/svg">\n]>\n' + svg(ns='xmlns="&ns_svg;"'), "doctype"),
            ("a clip path measured by the box of what it clips", bare(clip.replace("<clipPath ", '<clipPath clipPathUnits="objectBoundingBox" ') + '<rect clip-path="url(#c)" width="9" height="9"/>'), "clip-units"),
            ("the same clip path in the drawing's own units", bare(clip.replace("<clipPath ", '<clipPath clipPathUnits="userSpaceOnUse" ') + '<rect clip-path="url(#c)" width="9" height="9"/>'), None),
            ("a shape inside a clip path scaled to nothing", bare(clip.replace("<rect ", '<rect transform="scale(0)" ') + '<rect clip-path="url(#c)" width="9" height="9"/>'), "flat-transform"),
            ("the same shape scaled to a half", bare(clip.replace("<rect ", '<rect transform="scale(.5)" ') + '<rect clip-path="url(#c)" width="9" height="9"/>'), None),
            ("clip paths used so often and so large that a browser draws for seconds", bare(big_clip + '<rect clip-path="url(#c)" width="9" height="9"/>' * 101), "clip-work"),
            ("the same clip path, used as often as the cap takes", bare(big_clip + '<rect clip-path="url(#c)" width="9" height="9"/>' * 100), None),
            # the rules of round 7
            ("six scales in one transform, each the smallest there is", bare('<g transform="%s"><rect width="9" height="9"/></g>' % " ".join(["scale(1e-9)"] * 6)), "flat-transform"),
            ("three ordinary small scales in one transform", bare('<g transform="scale(.1) scale(.1) scale(.1)"><rect width="900" height="900"/></g>'), None),
            ("a skew by an angle too large to be read exactly", bare('<rect transform="skewX(20000070.9)" width="9" height="9"/>'), "angle-too-large"),
            ("the same skew, its angle between 0 and 360", bare('<rect transform="skewX(270.9)" width="9" height="9"/>'), None),
            ("a clip in the box's units named on a group, where it means nothing", bare('<g clipPathUnits="objectBoundingBox"><rect width="9" height="9"/></g>'), None),
            # the rule of round 8: a turn keeps an area, so the smallest scale there is stays kept with a turn beside it
            ("the smallest scale there is, then a turn", bare('<g transform="scale(1e-9) rotate(6)"><rect width="9" height="9"/></g>'), None),
            ("a turn, then the smallest scale there is", bare('<g transform="rotate(6) scale(1e-9)"><rect width="9" height="9"/></g>'), None),
            ("three small scales that come to the least area, then a turn", bare('<g transform="scale(.001) scale(.001) scale(.001) rotate(6)"><rect width="9" height="9"/></g>'), None),
            ("the same with a scale that takes it under the least area", bare('<g transform="scale(1e-9) rotate(6) scale(.99)"><rect width="9" height="9"/></g>'), "flat-transform"),
        )
        for what, data, code in rows:
            with self.subTest(what=what):
                answer = through_the_command(self, data)
                said = str(refused(self, data, code)) if code else None   # what the check itself says of it
                self.assertEqual(answer["status"], "refused", answer)
                if code:
                    self.assertEqual((answer["code"], answer["message"]), (code, said))
                else:
                    self.assertIn(answer["code"], READ, answer["message"])   # read: the run went on to the image tool
                    self.assertEqual(answer["notes"], _svg.clean_svg(data).notes)
                self.assertEqual(answer["written"], [])
        by_name = dict((what, data) for what, data, _code in rows)
        for what in ("a DOCTYPE on a line of its own", "a DOCTYPE over two lines", "a DOCTYPE on the line of the svg"):
            self.assertEqual(through_the_command(self, by_name[what])["message"], _svg.DOCTYPE)
            self.assertIn(through_the_command(self, without_doctype(by_name[what]))["code"], READ, "with the declaration deleted, as the sentence says, the file is read")
        self.assertEqual(through_the_command(self, by_name["a DOCTYPE with definitions of its own"])["message"], _svg.DOCTYPE_DEFINES)
        # the rule of round 7: a declaration without brackets can bring in a name the drawing uses, from the file it names.
        # Deleted as the sentence says, the file meets a second refusal, and that one says the same way on.
        needs_it = b'<!DOCTYPE svg SYSTEM "brand.dtd">\n' + svg().replace(b'fill="#b4531a"', b'fill="&brand;"')
        first, second = through_the_command(self, needs_it), through_the_command(self, without_doctype(needs_it))
        self.assertEqual((first["code"], first["message"]), ("doctype", _svg.DOCTYPE))
        self.assertEqual((second["status"], second["code"], second["message"], second["written"]), ("refused", "not-xml", _svg.NO_SUCH_NAME, []))
        self.assertTrue(first["message"].endswith("the " + _svg.NEEDS_AN_EXPORT) and second["message"].endswith(", the " + _svg.NEEDS_AN_EXPORT))
        answer = through_the_command(self, by_name["an editor's leftovers in a style"])
        self.assertEqual(answer["notes"], ["left out styles that only an editor reads (their names start -inkscape-)"])

    def test_a_name_nothing_defines_is_told_a_way_on_that_the_file_in_hand_can_take(self):
        # Two kinds of file meet NO_SUCH_NAME, and each can act on its half of the sentence.
        # (1) Pasted code that never had a DOCTYPE and holds a web page's name for a character. Round 7 told it "the drawing
        # needs what the declaration brought in: ask the tool for an export without a DOCTYPE": no declaration brought
        # anything, and the export asked for is the file in hand. Its way on is the character itself, or the name gone.
        characters = {b"&nbsp;": " ", b"&copy;": "©", b"&reg;": "®", b"&mdash;": "—"}
        pasted = {
            "a no-break space in a title": svg("<title>A&nbsp;B</title>"),
            "two names in a label": svg(root='role="img" aria-label="&copy; 2026 A&nbsp;B"'),
            "a registered mark in a description": svg("<desc>Mark&reg;</desc>"),
            "the same name twice, and blanks round it": svg("<title> &nbsp; &nbsp; </title>"),
            "a dash in a title, the file over several lines": svg("<title>A &mdash; B</title>").replace(b"><", b">\n<"),
        }
        for what, data in pasted.items():
            with self.subTest(what=what):
                self.assertNotIn(b"DOCTYPE", data)
                answer = through_the_command(self, data)
                self.assertEqual((answer["status"], answer["code"], answer["message"], answer["written"]), ("refused", "not-xml", _svg.NO_SUCH_NAME, []))
                with_the_character, without_the_name = data, data
                for name, character in characters.items():
                    with_the_character, without_the_name = with_the_character.replace(name, character.encode("utf-8")), without_the_name.replace(name, b"")
                self.assertNotEqual(with_the_character, data)
                for done in (with_the_character, without_the_name):   # what the first half says to do, done: the file is read
                    self.assertIn(through_the_command(self, done)["code"], READ)
        self.assertIn("Where the name stands for a character, as it does on a web page, open the file in a text editor and put the character itself in its place, or take the name out",
                      _svg.NO_SUCH_NAME)
        # in a package the sentence is the same, said of the file by its name
        answer = through_the_command(self, T.build_zip([("pack/logo.svg", pasted["a no-break space in a title"])]), name="pack.zip")
        self.assertEqual((answer["code"], answer["message"]), ("not-xml", "In the package, the file 'pack/logo.svg': " + _svg.NO_SUCH_NAME))
        # (2) A file whose DOCTYPE was deleted, as the DOCTYPE sentence says, and whose drawing uses a name the declaration
        # had brought in. Its way on is the second half: an export without a DOCTYPE, where the tool writes out what the
        # name stood for. That file is read.
        needs_it = b'<!DOCTYPE svg SYSTEM "brand.dtd">\n' + svg().replace(b'fill="#b4531a"', b'fill="&brand;"')
        answer = through_the_command(self, without_doctype(needs_it))
        self.assertEqual((answer["status"], answer["code"], answer["message"], answer["written"]), ("refused", "not-xml", _svg.NO_SUCH_NAME, []))
        self.assertTrue(answer["message"].endswith("Where the file had a DOCTYPE declaration that was deleted, the drawing needs what the declaration brought in: "
                                                   "ask the tool for an export without a DOCTYPE."))
        self.assertIn(through_the_command(self, svg())["code"], READ)   # the export: no DOCTYPE, and the colour written out
        # other XML that cannot be read is not told about names or declarations
        for data in (svg("<title>Smith & Sons</title>"), svg("<title>A&nbsp B</title>"), svg("<title>A&;B</title>")):
            answer = through_the_command(self, data)
            self.assertEqual((answer["status"], answer["code"]), ("refused", "not-xml"))
            self.assertNotIn("a name that nothing in it defines", answer["message"])

    def test_a_refusal_of_a_file_in_a_package_says_which_file_it_is(self):
        # a package hands over two files, the mark and its one-colour version: a refusal that named neither left the owner
        # to open both (and the assistant's instructions said so)
        doctype = b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n' + svg()
        package = T.build_zip([("pack/mark.svg", svg()), ("pack/mark-mono.svg", doctype), ("pack/gr\u00f6\u00dfe.svg", svg("<text>x</text>"))])
        for pick, mono, code, about, sentence in (("pack/mark.svg", "pack/mark-mono.svg", "doctype", "pack/mark-mono.svg", _svg.DOCTYPE),
                                                  ("pack/mark-mono.svg", "pack/mark.svg", "doctype", "pack/mark-mono.svg", _svg.DOCTYPE),
                                                  ("pack/gr\u00f6\u00dfe.svg", "pack/mark-mono.svg", "text", "pack/gr\u00f6\u00dfe.svg", str(refused(self, svg("<text>x</text>"), "text"))),
                                                  ("pack/mark-mono.svg", None, "doctype", "pack/mark-mono.svg", _svg.DOCTYPE)):
            with self.subTest(pick=pick, mono=mono):
                answer = through_the_command(self, package, "--pick", pick, *(["--mono", mono] if mono else []), name="pack.zip")
                self.assertEqual((answer["status"], answer["code"]), ("refused", code))
                self.assertEqual(answer["message"], "In the package, the file %r: %s" % (about, sentence))
        self.assertIn(through_the_command(self, package, "--pick", "pack/mark.svg", name="pack.zip")["code"], READ)
        # one SVG alone in a package is named as well, and a file that is no package is not called one
        answer = through_the_command(self, T.build_zip([("only.svg", doctype)]), name="pack.zip")
        self.assertEqual(answer["message"], "In the package, the file 'only.svg': " + _svg.DOCTYPE)
        self.assertEqual(through_the_command(self, doctype)["message"], _svg.DOCTYPE)


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
            ("an include of another file", svg('<xi:include xmlns:xi="http://www.w3.org/2001/XInclude" href="other.svg"/>'), "xinclude",
             svg('<x:include xmlns:x="urn:not-an-include" href="other.svg"/>')),
            ("an include in the metadata", svg('<metadata><xi:include xmlns:xi="http://www.w3.org/2001/XInclude" href="data:text/xml,%3Cstyle/%3E"/></metadata>'), "xinclude",
             svg("<metadata>xi:include href=other.svg</metadata>")),
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

    def test_a_file_that_pulls_in_another_file_is_refused_wherever_the_include_stands(self):
        # Measured 2026-10-13: the site's renderer resolves <xi:include href="data:...">, inside <metadata> too, and draws
        # the shapes or applies the styles it holds. The check left the element out as another program's, so the file as
        # it came (10,000 red pixels of 10,000) was another drawing than the cleaned one (5,000 blue).
        std, draft = "http://www.w3.org/2001/XInclude", "http://www.w3.org/2003/XInclude"
        rect = "data:image/svg+xml;base64," + base64.b64encode(b'<rect xmlns="http://www.w3.org/2000/svg" width="10" height="10" fill="#f00"/>').decode()
        include = '<xi:include xmlns:xi="%s" href="%s"/>' % (std, rect)
        for what, doc in (
                ("in the drawing", svg(include)), ("in a group", svg("<g>%s</g>" % include)), ("in the defs", svg("<defs>%s</defs>" % include)),
                ("in a clip path", svg('<clipPath id="c">%s</clipPath>' % include)), ("in a shape", svg('<rect width="9" height="9">%s</rect>' % include)),
                ("in a style", svg("<style>%s</style>" % include)), ("in the metadata", svg("<metadata>%s</metadata>" % include)), ("in a title", svg("<title>%s</title>" % include)),
                ("in a desc", svg("<desc>%s</desc>" % include)), ("in another program's element", svg('<x:a xmlns:x="urn:editor">%s</x:a>' % include)),
                ("deep in what is left out", svg('<metadata><x:a xmlns:x="urn:editor"><x:b><x:c>%s</x:c></x:b></x:a></metadata>' % include)),
                ("in an include", svg('<xi:include xmlns:xi="%s" href="a.svg"><xi:fallback>%s</xi:fallback></xi:include>' % (std, include))),
                ("its fallback alone", svg('<xi:fallback xmlns:xi="%s">words</xi:fallback>' % std)), ("any element of that namespace", svg('<xi:other xmlns:xi="%s"/>' % std)),
                ("under the draft's namespace", svg('<xi:include xmlns:xi="%s" href="a.svg"/>' % draft)), ("under another prefix", svg('<q:include xmlns:q="%s" href="a.svg"/>' % std)),
                ("as the default namespace", svg('<include xmlns="%s" href="a.svg"/>' % std)), ("declared on the outer svg", svg('<xi:include href="a.svg"/>', root='xmlns:xi="%s"' % std)),
                ("with no address", svg('<xi:include xmlns:xi="%s"/>' % std)), ("of a text", svg('<xi:include xmlns:xi="%s" href="a.txt" parse="text"/>' % std)),
                ("of a part of the file itself", svg('<xi:include xmlns:xi="%s" xpointer="c"/>' % std)), ("twice", svg(include + include)),
                ("as the outer element", ('<xi:include xmlns:xi="%s" href="a.svg"/>' % std).encode()),
                ("pasted code without a namespace of its own", ('<svg viewBox="0 0 8 8"><path d="M0 0h9v9z"/><metadata>%s</metadata></svg>' % include).encode())):
            with self.subTest(what=what):
                err = refused(self, doc, "xinclude")
                for word in ("pulls in another file", "Ask the tool", "everything in the one file"):
                    self.assertIn(word, str(err))
                # and through the door the intake uses
                with self.assertRaises(_svg.Refusal) as cm:
                    _svg.clean_svg(_input.mark(_input.load(doc)).colour)
                self.assertIn(cm.exception.code, ("xinclude", "unknown-file"))   # (an outer element that is no <svg> is no drawing to the intake)
        # an element that is only called include, or the word in a text, pulls nothing in
        for doc in (svg('<x:include xmlns:x="urn:editor" href="a.svg"/>'), svg('<metadata><include xmlns="urn:editor" href="a.svg"/></metadata>'), svg("<title>xi:include</title>"),
                    svg("<desc>http://www.w3.org/2001/XInclude</desc>"), svg(root='xmlns:xi="%s"' % std), svg('<g data-ns="%s"/>' % std)):
            with self.subTest(doc=doc[150:220]):
                self.assertEqual(_svg.clean_svg(doc).colours, ["#b4531a"])

    def test_a_doctype_is_refused_with_the_way_out_that_exists(self):
        # Three common drawing programs write a DOCTYPE into every file, and one of them cannot leave it out: "export again
        # without it" was no way out. The declaration can be taken out by hand.
        # What is taken out is the DECLARATION, not "the line that starts <!DOCTYPE": that sentence deleted the whole
        # drawing where the declaration shares its line with the <svg, and left half a declaration where it runs over two.
        public = b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
        xml = b'<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
        plain = {
            "on a line of its own": xml + b"\n" + public + b"\n" + svg(),
            "first in the file": public + svg(),
            "over two lines": xml + b"\n" + public.replace(b'" "', b'"\n  "') + b"\n" + svg(),
            "over three lines, as a Windows program breaks them": xml + b"\r\n" + public.replace(b" PUBLIC ", b"\r\n\tPUBLIC ").replace(b'" "', b'"\r\n\t"') + b"\r\n" + svg(),
            "on the line of the svg": xml + public + svg(),
            "the whole file on one line, no declaration of XML": public + svg(),
            "after a comment": b"<!-- made by a tool -->\n" + public + b"\n" + svg(),
            "the shortest there is": b"<!DOCTYPE svg>" + svg(),
            "with a blank before it closes": b'<!DOCTYPE svg SYSTEM "svg11.dtd" >\n' + svg(),
            "an address with a square bracket in it": b'<!DOCTYPE svg SYSTEM "a[1].dtd">' + svg(),
        }
        for what, data in plain.items():
            with self.subTest(what=what):
                err = refused(self, data, "doctype")
                self.assertEqual(str(err), _svg.DOCTYPE)
                # what the sentence says to do works, wherever the lines break: the declaration deleted, and nothing else
                self.assertNotIn(b"<!DOCTYPE", without_doctype(data))
                self.assertEqual(_svg.clean_svg(_input.mark(_input.load(without_doctype(data))).colour).colours, ["#b4531a"])
        for word in ("DOCTYPE declaration", "text editor", "delete the declaration: everything from <!DOCTYPE up to the > that ends the declaration", "wherever the lines break",
                     "and nothing else (an <svg that comes after it stays)", "If the file cannot be read after that", "ask the tool for an export without a DOCTYPE"):
            self.assertIn(word, _svg.DOCTYPE)
        # (no promise that the drawing is the same, or that the file reads, with the declaration gone: see the next test)
        # "its last >" (round 7): where the declaration shares its line with the <svg, an owner could take the LINE's last
        # `>`, and delete the <svg with it. The sentence names the declaration's own end, and says what stays.
        for word in ("export again", "the line that starts", "DOCTYPE line", "square brackets", "the drawing is the same", "the > that closes it", "its last >"):
            self.assertNotIn(word, _svg.DOCTYPE)
        for what in ("on the line of the svg", "the whole file on one line, no declaration of XML"):
            with self.subTest(what=what, cut="to the line's last >"):
                data = plain[what]
                start = data.index(b"<!DOCTYPE")
                self.assertNotIn(b"<svg", data[:start] + data[data.rindex(b">") + 1:], "cut to the line's last >, the drawing went with the declaration")
                self.assertTrue(without_doctype(data)[start:].startswith(b"<svg"), "the <svg that comes after the declaration stays")
        # the old sentence, done to the letter, on the two shapes it failed for
        lines_gone = lambda data: b"\n".join(line for line in data.split(b"\n") if not line.startswith(b"<!DOCTYPE"))
        self.assertEqual(refused(self, lines_gone(plain["over two lines"]), "not-xml").code, "not-xml")
        self.assertNotIn(b"<svg", lines_gone(plain["the whole file on one line, no declaration of XML"]))

        # A declaration that holds definitions of its own (the part in square brackets) is the other form: the file
        # may use the names it defines (one common tool writes the addresses of its namespaces so), and is then not
        # readable once the declaration is gone. Its sentence does not say to delete it.
        entities = b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd" [\n\t<!ENTITY ns_extend "http://ns.example/Extensibility/1.0/">\n\t<!ENTITY ns_svg "http://www.w3.org/2000/svg">\n]>\n'
        uses_them = xml + b"\n" + entities + svg(ns='xmlns:x="&ns_extend;" xmlns="&ns_svg;"')
        defines = {
            "definitions the svg then uses": uses_them,
            "one definition, on one line": b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "x">]>' + svg(),
            "a definition that names a file": b'<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]>' + svg(),
            "definitions nothing uses": xml + b"\n" + entities + svg(),
            "empty brackets": b"<!DOCTYPE svg []>" + svg(),
            "brackets on a line of their own": b"<!DOCTYPE svg\n[\n]\n>\n" + svg(),
        }
        for what, data in defines.items():
            with self.subTest(what=what):
                self.assertEqual(str(refused(self, data, "doctype")), _svg.DOCTYPE_DEFINES)
        for word in ("DOCTYPE declaration", "definitions of its own", "square brackets", "cannot simply be deleted", "Ask the tool for an export without a DOCTYPE"):
            self.assertIn(word, _svg.DOCTYPE_DEFINES)
        for word in ("text editor", "delete the declaration", "the drawing is the same"):
            self.assertNotIn(word, _svg.DOCTYPE_DEFINES)
        # and that is true of the file that uses its names: with the whole declaration deleted it cannot be read
        gone = uses_them.replace(entities, b"")
        self.assertNotIn(b"DOCTYPE", gone)
        self.assertEqual(str(refused(self, gone, "not-xml")), _svg.NO_SUCH_NAME)   # (and that refusal leads to the same end)

        # through the door the intake uses, as a file and inside a package (where the refusal says which file)
        for form, data in ((_svg.DOCTYPE, plain["over two lines"]), (_svg.DOCTYPE, plain["on the line of the svg"]), (_svg.DOCTYPE_DEFINES, uses_them)):
            with self.assertRaises(_svg.Refusal) as cm:
                _svg.clean_svg(_input.mark(_input.load(data)).colour)
            self.assertEqual((cm.exception.code, str(cm.exception)), ("doctype", form))
            with self.assertRaises(_svg.Refusal) as cm:
                _svg.clean_svg(_input.mark(_input.load(T.build_zip([("pack/logo.svg", data)]))).colour)
            self.assertEqual((cm.exception.code, str(cm.exception)), ("doctype", "In the package, the file 'pack/logo.svg': " + form))
        # in small letters it is no DOCTYPE to XML at all: not this refusal, and not a file that is read
        for data in (b"<!doctype svg>\n" + svg(), T.build_zip([("logo.svg", b"<!doctype svg>\n" + svg())])):
            with self.assertRaises(_svg.Refusal) as cm:
                _svg.clean_svg(_input.mark(_input.load(data)).colour)
            self.assertEqual(cm.exception.code, "not-xml")

    def test_a_file_that_needs_what_its_doctype_brought_in_is_led_to_one_end_by_both_refusals(self):
        # A declaration WITHOUT square brackets can define names too: in the outside file it names. The sentence promised
        # that the drawing is the same with the declaration deleted; such a file was then "not readable (undefined entity)",
        # which named no way on. Now the first sentence says what to do if the file cannot be read after that, and the
        # refusal that file meets says the same: both end with the export.
        public = b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
        coloured = svg().replace(b'fill="#b4531a"', b'fill="&brand;"')
        self.assertIn(b"&brand;", coloured)
        needs_it = {
            "a colour named in an outside file": b'<!DOCTYPE svg SYSTEM "brand.dtd">' + coloured,
            "the same, the declaration over two lines": b'<?xml version="1.0"?>\n<!DOCTYPE svg\n  SYSTEM "brand.dtd">\n' + coloured,
            "the public form, and the name is the namespace's": public + svg(ns='xmlns="&ns_svg;"'),
            "a name in a title, which is left out": public + svg("<title>A&nbsp;B</title>"),
            "a name in an attribute that is left out": public + svg(root='data-made-by="&tool;"'),
            "two names": b'<!DOCTYPE svg SYSTEM "brand.dtd" >' + svg("<desc>&one; &two;</desc>"),
            "an address with a > in it": b'<!DOCTYPE svg SYSTEM "a>b.dtd">' + coloured,
        }
        for what, data in needs_it.items():
            with self.subTest(what=what):
                self.assertEqual(str(refused(self, data, "doctype")), _svg.DOCTYPE)
                gone = without_doctype(data)   # the declaration deleted, as the sentence says
                self.assertNotIn(b"DOCTYPE", gone)
                self.assertEqual(str(refused(self, gone, "not-xml")), _svg.NO_SUCH_NAME)
                # through the door the intake uses, as a file and inside a package (where the refusal says which file)
                for packed, before in ((gone, ""), (T.build_zip([("pack/logo.svg", gone)]), "In the package, the file 'pack/logo.svg': ")):
                    with self.assertRaises(_svg.Refusal) as cm:
                        _svg.clean_svg(_input.mark(_input.load(packed)).colour)
                    self.assertEqual((cm.exception.code, str(cm.exception)), ("not-xml", before + _svg.NO_SUCH_NAME))
        # the two sentences lead to one end, in the same words
        self.assertTrue(_svg.DOCTYPE.endswith(" If the file cannot be read after that, the " + _svg.NEEDS_AN_EXPORT))
        self.assertTrue(_svg.NO_SUCH_NAME.endswith(" Where the file had a DOCTYPE declaration that was deleted, the " + _svg.NEEDS_AN_EXPORT))
        self.assertTrue(_svg.NEEDS_AN_EXPORT.endswith("ask the tool for an export without a DOCTYPE."))
        for word in ("not readable as an SVG", "a name that nothing in it defines", "between & and ;", "for example &nbsp;", "DOCTYPE declaration",
                     "Where the name stands for a character, as it does on a web page", "put the character itself in its place, or take the name out"):
            self.assertIn(word, _svg.NO_SUCH_NAME)
        # (round 7 said of every such file that a DOCTYPE defines such names and that the drawing needs what it brought in:
        # untrue of pasted code that never had one. See the test after this one.)
        for word in ("Such names are defined by a DOCTYPE", "this file has none, or has it no longer"):
            self.assertNotIn(word, _svg.NO_SUCH_NAME)
        self.assertLess(_svg.NO_SUCH_NAME.index("stands for a character"), _svg.NO_SUCH_NAME.index("that was deleted"), "the commoner file's way on is said first")
        # "the > that ends the declaration": where an address in quotes holds a > of its own, the declaration ends at the later one. Deleted to
        # there, a file that needs nothing of the declaration is read; deleted to the first, it is not.
        quoted = {"a > in the address": b'<!DOCTYPE svg SYSTEM "a>b.dtd">' + svg(), "in single quotes, with a double quote too": b"<!DOCTYPE svg SYSTEM 'a>\"b.dtd'>\n" + svg(),
                  "two of them": b'<!DOCTYPE svg SYSTEM "a>>b.dtd" >' + svg()}
        for what, data in quoted.items():
            with self.subTest(what=what):
                self.assertEqual(str(refused(self, data, "doctype")), _svg.DOCTYPE)
                self.assertEqual(without_doctype(data).strip(), svg())
                self.assertEqual(_svg.clean_svg(_input.mark(_input.load(without_doctype(data))).colour).colours, ["#b4531a"])
                start = data.index(b"<!DOCTYPE")
                to_the_first = data[:start] + data[data.index(b">", start) + 1:]
                with self.assertRaises(_svg.Refusal):
                    _svg.clean_svg(_input.mark(_input.load(to_the_first)).colour)
        # a name nothing defines in a file that never had a DOCTYPE (pasted code with a web page's &nbsp;) gets the same
        # sentence, whose first half is the one for it; any other XML that cannot be read keeps the sentence it had
        self.assertEqual(str(refused(self, svg("<title>A&nbsp;B</title>"), "not-xml")), _svg.NO_SUCH_NAME)
        for data, said in ((b"<svg><path></svg>", "mismatched tag"), (svg(root='data-x="a & b"'), "not well-formed"), (svg(root='data-x="&#xFFFFFFF;"'), "invalid character number")):
            err = refused(self, data, "not-xml")
            self.assertIn(said, str(err))
            self.assertNotIn("DOCTYPE", str(err))
        # the names XML itself defines are no such name
        self.assertEqual(_svg.clean_svg(svg(root='data-x="&amp;&lt;&gt;&quot;&apos;&#38;"')).colours, ["#b4531a"])

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
            for attrs in ('href="%sgpj.elif//:ptth"', 'stroke-width="%s1"', 'transform="%s"', 'fill="%s"', 'style="fill:%s"', 'clip-path="url(#a%s)"', 'points="1 1%s"',
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
        # what an Ask offers to choose from is spelled out where it is SHOWN; as it is stored it stays what her answer is matched against
        given = ["plain.svg", "caf\u00e9 2.svg", "a\u200bb.svg", "a\x00b", "\u202egvs.exe", "a\u00a0b", "a\ufe0f", "two\nlines"]
        ask = _refusal.Ask("a-code", "which one?", given)
        self.assertEqual(ask.options, given)
        self.assertEqual(ask.shown, ["plain.svg", "caf\u00e9 2.svg", "a\\u200bb.svg", "a\\x00b", "\\u202egvs.exe", "a\\xa0b", "a\\ufe0f", "two\nlines"])
        self.assertFalse([c for o in ask.shown for c in o if c != "\n" and _refusal.unseen(c)])
        self.assertEqual((_refusal.Ask("a-code", "which?").shown, _refusal.Ask("a-code", "which?", [1, None]).shown), ([], ["1", "None"]))
        names = ["a.svg", "b c.svg", "caf\u00e9.svg"]
        with self.assertRaises(_refusal.Ask) as cm:   # the question the intake really asks: nothing in it to spell out, and nothing changed
            _input.mark(_input.load(T.build_zip([(n, svg()) for n in names])))
        self.assertEqual((cm.exception.options, cm.exception.shown), (names, names))

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
        for w, h in (("4cm", "3cm"), ("1in", "1in"), ("12pt", "12pt"), ("40mm", "30mm"), ("4pc", "3pc"), ("40", "3cm"), ("1in", "96"), ("4em", "3em"), ("4ex", "3ex"),
                     ("1em", "1em"), ("40", "3em")):
            with self.subTest(w=w, h=h):
                err = refused(self, (doc % (w, h)).encode(), "no-size")
                self.assertIn("viewBox", str(err))
        # beside a viewBox of the same shape such a width and height change nothing, and are left out as before. The
        # commonest size an icon is exported with is 1em by 1em: refused until 2026-10-13, for its unit
        for w, h, box in (("4cm", "3cm", "0 0 64 48"), ("1in", "1in", "0 0 7 7"), ("12pt", "12pt", "0 0 7 7"), ("40mm", "30mm", "0 0 4 3"), ("4pc", "3pc", "0 0 8 6"),
                          ("1em", "1em", "0 0 24 24"), ("4em", "3em", "0 0 64 48"), ("1.2ex", "1.2ex", "0 0 24 24"), ("2em", "1em", "0 0 48 24")):
            with self.subTest(w=w, h=h, box=box):
                clean = _svg.clean_svg((doc % (w, h)).replace("<svg ", '<svg viewBox="%s" ' % box).encode())
                self.assertIn('viewBox="%s">' % box, clean.text)
                self.assertEqual(clean.notes, [])
        # a unit that is a share of the window or of some other element's letters is no size of a drawing anywhere
        for w, h in (("40vw", "30vh"), ("4rem", "3rem"), ("4ch", "3ch"), ("40vmin", "30vmin")):
            with self.subTest(w=w, h=h):
                refused(self, (doc % (w, h)).encode(), "length-unit")
                refused(self, (doc % (w, h)).replace("<svg ", '<svg viewBox="0 0 4 3" ').encode(), "length-unit")

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
        doc = '<svg xmlns="http://www.w3.org/2000/svg" %s><path fill="#111111" d="M0 0h.009v.009z"/></svg>'
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
                _svg.clean_svg(('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s"><path fill="#111111" d="M0 0h.009v.009z"/></svg>' % vb).encode())
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
                'transform="%s"' % ("scale(1) " * _svg.MAX_TRANSFORMS), 'd="M0 0%s"' % (" 1" * 90000), 'width="%s"' % ("1." + "0" * (_svg.MAX_VALUE - 2)), 'x="%s%%"' % ("5." + "0" * (_svg.MAX_VALUE - 3)),
                'stroke-width="%spx"' % ("0" * (_svg.MAX_VALUE - 3) + "5"), 'transform="%s"' % ("translate(1\t2)\n" * _svg.MAX_TRANSFORMS + " " * (_svg.MAX_RAW - 16 * 16))]
        for attrs, out in zip(most, judged(self, [self.shape(attrs) for attrs in most])):
            self.assertEqual(out["code"], "ok", attrs[:60])
        # ... and a value that is the right form and far longer is refused by name, just as fast (each of these was read
        # and kept whole before 2026-10-12: one rule's value is written onto every element, so the cleaned file grew without end)
        over = ['points="%s"' % ("1.5,-2e1 " * 40000), 'stroke-dasharray="%s"' % ("4 2 " * 50000), 'transform="%s"' % ("scale(1) " * 40000),
                'd="M0 0%s"' % (" 1" * 190000), 'width="%s"' % ("1" * 100000), 'stroke-width="%s1"' % ("0" * 200000), 'style="stroke-dasharray:%s"' % ("1 " * 30000),
                'points="%s"' % ("1 " * 250000), 'transform="translate(%s)"' % ("0" * 100000 + "1"),
                # the cap on one value counts the whole of it, its unit and its sign too: `0`, 63 times, and `5px` was kept
                'stroke-width="%s5px"' % ("0" * (_svg.MAX_VALUE - 1)), 'width="%spx"' % ("0" * (_svg.MAX_VALUE - 2) + "5"), 'x="%s%%"' % ("0" * (_svg.MAX_VALUE - 1) + "5"),
                'x="+%s5"' % ("0" * (_svg.MAX_VALUE - 1)), 'style="stroke-width:%s5px"' % ("0" * (_svg.MAX_VALUE - 1)), 'r="%s"' % ("5." + "0" * (_svg.MAX_VALUE - 1)),
                # and a list may not be padded out with blanks: 400,000 of them in a transform were written out as they came
                'transform="translate(1)%sscale(2)"' % (" " * 400000), 'transform="translate(1%s2)"' % ("\t" * (_svg.MAX_RAW - 12)), 'transform="%sscale(2)"' % (" " * _svg.MAX_RAW),
                'stroke-dasharray="4%s2"' % (" " * _svg.MAX_RAW), 'style="stroke-dasharray:4%s2"' % (" " * _svg.MAX_RAW), 'points="1%s2"' % (" " * _svg.MAX_PATH),
                'd="M0 0%sh1"' % (" " * _svg.MAX_PATH), 'points="%s1 2"' % (" " * _svg.MAX_PATH), 'paint-order="stroke%s"' % (" " * _svg.MAX_RAW)]
        for attrs, out in zip(over, judged(self, [self.shape(attrs) for attrs in over])):
            self.assertEqual(out["code"], "value-too-long", attrs[:60])

    def test_the_cap_on_a_value_as_it_stands_is_one_cap_however_the_value_reaches_the_element(self):
        # `style="fill:` + 9,000 blanks + `red"` was read where the attribute fill=" ... red" was refused: a style's values
        # had their blanks taken off before they were counted. One cap: the attribute, a style, a rule, a rule nothing matches.
        cap = _svg.MAX_RAW
        for prop, value in (("fill", "#111111"), ("stroke", "red"), ("stroke-width", "2"), ("stroke-dasharray", "4 2"), ("stroke-linecap", "round"), ("opacity", "1"),
                            ("paint-order", "stroke"), ("clip-path", "none"), ("display", "inline"), ("stroke-dashoffset", "1px")):
            room = cap - len(value)
            for pad in (lambda n: (" " * n, ""), lambda n: ("", " " * n), lambda n: (" " * (n // 2), " " * (n - n // 2)), lambda n: ("\t" * n, ""), lambda n: ("", "\n" * n),
                        lambda n: ("/*" + "x" * (n - 4) + "*/", ""), lambda n: ("", "/*" + "*" * (n - 4) + "*/"), lambda n: (" /**/" * (n // 5) + " " * (n % 5), "")):
                before, after = pad(room)
                over_before, over_after = pad(room + 1)
                is_comment = "/*" in before + after
                places = [('<rect style="%s:%s" width="9" height="9"/>', True), ('<rect style="fill:#222222;%s:%s;stroke:none" width="9" height="9"/>', True),
                          ("<style>rect{%s:%s}</style><rect width='9' height='9'/>", True), ("<style>.unused{%s:%s}</style><rect width='9' height='9'/>", True),
                          ("<style>rect{%s:%s;}\n</style><rect width='9' height='9'/>", True), ('<rect %s="%s" width="9" height="9"/>', False)]
                for shape, is_style in places:
                    if is_comment and not is_style:
                        continue   # a comment is one in a style only
                    if not is_style and "\t" in before + after or "\n" in before + after and not is_style:
                        before, after, over_before, over_after = (t.replace("\t", "&#9;").replace("\n", "&#10;") for t in (before, after, over_before, over_after))
                    with self.subTest(prop=prop, shape=shape[:24], pad=(before[:6], after[:6])):
                        _svg.clean_svg(svg(shape % (prop, before + value + after)))
                        err = refused(self, svg(shape % (prop, over_before + value + over_after)), "value-too-long")
                        for word in (prop + " holds", "more than 8,192 characters", "Ask the tool"):
                            self.assertIn(word, str(err))
        # a value that is no value is refused as that, however long it is, and one that is left out is not counted at all
        refused(self, svg('<rect style="fill:%sno_colour" width="9" height="9"/>' % (" " * 9000)), "bad-value")
        refused(self, svg('<rect style="stroke-width:%s5 5" width="9" height="9"/>' % (" " * 9000)), "bad-value")
        self.assertEqual(len(_svg.clean_svg(svg('<rect style="font-family:%sArial;filter:%snone" width="9" height="9"/>' % (" " * 9000, " " * 9000))).notes), 1)
        # through the door the intake uses, as a file and inside a package
        doc = svg('<rect style="fill:%sred" width="9" height="9"/>' % (" " * 9000))
        self.assertEqual(refused(self, _input.mark(_input.load(doc)).colour, "value-too-long").code, "value-too-long")
        self.assertEqual(refused(self, _input.mark(_input.load(T.build_zip([("logo.svg", doc)]))).colour, "value-too-long").code, "value-too-long")
        # what is kept is written with one blank between two entries, however the file spaced it
        spaced = _svg.clean_svg(self.shape('transform="translate(1)%sscale(2\t,\n3)" points="1%s2\r\n3,4" stroke-dasharray="4%s2" stroke="#111111" paint-order=" stroke\t\tfill "'
                                           % (" " * 4000, " " * 4000, "\n" * 4000)))
        for written in ('transform="translate(1) scale(2 3)"', 'points="1 2 3 4"', 'stroke-dasharray="4 2"', 'paint-order="stroke fill"'):
            self.assertIn(written, spaced.text)
        self.assertLess(len(spaced.text), 400)

    def test_numbers_written_the_ways_tools_write_them_are_still_read(self):
        # run together without a space, a bare dot, a sign, an exponent: all of it is SVG
        # (a list is written out with one blank between its numbers: the second of each pair is what the cleaned file holds)
        fine = [('points="10-20,3.5.5 1e2,4"', 'points="10 -20 3.5 .5 1e2 4"'), ('points=""', None), ('stroke-dasharray="4 2"', None), ('stroke-dasharray="4,2"', 'stroke-dasharray="4 2"'),
                ('stroke-dasharray="none"', None), ('width="1.0" height=".5"', None), ('x="+3" y="-3"', None), ('width="1e2"', None), ('width="4.5px"', None), ('rx="auto"', None),
                ('transform="translate(1,2) scale(2)"', 'transform="translate(1 2) scale(2)"'), ('transform="rotate(45 1 1),scale(2)"', 'transform="rotate(45 1 1) scale(2)"'),
                ('transform="translate(-1.5e1-2)"', 'transform="translate(-1.5e1 -2)"'), ('transform="matrix(1 0 0 1 0 0)"', None), ('stroke-miterlimit="4"', None),
                ('stroke-dashoffset="-2"', None)]
        for attrs, written in fine:
            with self.subTest(attrs=attrs):
                self.assertIn(written or (attrs.split('" ')[0].rstrip('"') + '"'), _svg.clean_svg(self.shape(attrs)).text)
        self.assertIn('points="1 2 3 4"', _svg.clean_svg(self.shape('points=" 1 2,3 4 "')).text)

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
        for attrs in ('width="5.0"', 'height="05"', 'stroke-width="5e0"', 'stroke-width=".5e1"', 'x="+5"', 'y="-.5"', 'transform="translate(5.0 .5)"',
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
        for value, written in (("4 2", "4 2"), ("4,2", "4 2"), ("none", "none"), ("4", "4"), ("0.5 .5e1", "0.5 .5e1"), ("4 , 2", "4 2")):
            with self.subTest(value=value):
                self.assertIn('stroke-dasharray="%s"' % written, _svg.clean_svg(self.shape('stroke-dasharray="%s" stroke="#ff0000"' % value)).text)

    def test_only_a_plain_space_is_a_space(self):
        # Python's strip(), split() and \s take a no-break space, an em space, a line separator; a renderer does not.
        # Taken off here, each of these gave a value the check read one way and the renderer another: a fill of
        # "(no-break space)red" was read as red and is drawn black.
        for space in ("\u00a0", "\u2003", "\u3000", "\u2028", "\u0085", "\u1680", "\u202f"):
            for attrs in ('fill="%sred"', 'fill="red%s"', 'stroke="#ff0000%s"', 'fill="rgb(255,%s0,0)"', 'style="fill:%sred"',
                          'style="fill:red%s"', 'stroke-width="%s2"', 'stroke-width="2%s"', 'width="9%s"', 'opacity="%s1"',
                          'visibility="%shidden"', 'display="none%s"', 'fill-rule="%sevenodd"', 'clip-path="%snone"', 'stroke-dasharray="4%s2"',
                          'transform="translate(1%s2)"', 'transform="%sscale(2)"', 'transform="scale%s(2)"', 'class="%sa"',
                          'class="a%sb"', 'paint-order="stroke%sfill"'):
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
                    self.assertIn("minus sign", str(err))   # what is there to see: `-0` is not below zero, and is refused all the same
                    self.assertNotIn("below zero", str(err))
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

    def test_x_and_y_on_the_outer_svg_are_left_out_and_said_and_its_id_goes_as_any_unused_id_does(self):
        clean = _svg.clean_svg(svg(root='x="5" y="6" id="logo"'))
        root = clean.text.split(">", 1)[0]
        for attr in (" x=", " y=", " id="):
            self.assertNotIn(attr, root)
        for word in ("x of the outer", "y of the outer"):
            self.assertEqual(len([n for n in clean.notes if word in n]), 1, clean.notes)
        self.assertEqual(len(clean.notes), 2, "an id nothing is named by is no part of the drawing: nothing is said of it")
        self.assertEqual(_svg.clean_svg(svg()).notes, [], "a file that loses nothing has nothing to say")
        self.assertEqual(_svg.clean_svg(svg(root='id="Ebene 1"')).notes, [])


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

    def test_what_is_left_out_is_not_read_and_cannot_change_what_becomes_of_the_drawing(self):
        # An attribute that is left out is never written, so it can fetch and run nothing. Until 2026-10-13 it was still
        # read as a piece of a style: a drawing whose label said "JavaScript: the logo" was refused as one that "can run
        # code", and so was one whose layer was called `expression(layer)` (an editor writes the layer's name as data-name).
        words = ("JavaScript: the logo", "expression(layer)", "url(logo.png)", "url(https://x.example/a)", "@import a", "image(x)", "-moz-binding", "behavior: none", "a\\62 c", "/* x */", "{}")
        for word in words:
            for attrs, noted in (('aria-label="%s"', None), ('data-name="%s"', None), ('data-anything="%s"', None), ('role="%s"', None), ('version="%s"', None),
                                 ('label="%s"', "label"), ('sketch-type="%s"', "sketch-type"), ('x:label="%s" xmlns:x="urn:editor"', "label"), ('viewBox-x="%s"', "viewBox-x")):
                for doc in (svg(root=attrs % word), svg().replace(b"<path ", ("<path %s " % (attrs % word)).encode()), svg("<g %s/>" % (attrs % word)),
                            svg('<clipPath %s/><defs %s/>' % (attrs % word, attrs % word))):
                    with self.subTest(word=word, attrs=attrs, doc=doc[100:140]):
                        clean = _svg.clean_svg(doc)
                        self.assertEqual(clean.colours, ["#b4531a"])
                        self.assertEqual(clean.notes, ["left out attributes this check does not use: " + noted] if noted else [])
                        self.assertNotIn(word.split("(")[0].split(":")[0], clean.text)
        # the same words where they are kept, or read to decide something, are what they were
        for attrs, code in (('fill="expression(layer)"', "css-script"), ('style="fill:url(https://x.example/a)"', "css-url"), ('stroke="url(logo.png)"', "css-url"),
                            ('d="@import a"', "css-import"), ('transform="javascript:x"', "css-script"), ('stroke-width="image(x)"', "css-url"), ('points="-moz-binding"', "css-script")):
            with self.subTest(attrs=attrs):
                refused(self, svg("<polygon %s/>" % attrs), code)
        refused(self, svg('<clipPath clipPathUnits="url(x)"/>'), "css-url")
        refused(self, svg('<style type="url(x)">path{fill:#111111}</style>'), "css-url")
        refused(self, svg(root='preserveAspectRatio="expression(1)"'), "css-script")
        # and what runs or fetches by being an attribute at all is refused whatever it says
        refused(self, svg(root='onload="x"'), "event-attribute")
        refused(self, svg().replace(b"<path ", b'<path href="https://x.example/a" '), "external-link")
        # through the door the intake uses, as a file and inside a package
        doc = svg(root='role="img" aria-label="JavaScript: the logo" data-name="expression(layer)" id="javascript:logo"')
        self.assertEqual(_svg.clean_svg(_input.mark(_input.load(doc)).colour).notes, [])
        self.assertEqual(_svg.clean_svg(_input.mark(_input.load(T.build_zip([("logo.svg", doc)]))).colour).colours, ["#b4531a"])

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
        clean = _svg.clean_svg(bare(inner % "userSpaceOnUse"))
        self.assertIn('<clipPath id="c" clipPathUnits="userSpaceOnUse">', clean.text)
        self.assertEqual(clean.notes, [])
        refused(self, bare(inner % "objectBoundingBox"), "clip-units")   # by name: see AKeyword
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

    def test_a_style_with_a_title_is_refused_because_a_browser_may_leave_it_out(self):
        # Measured 2026-10-13: of <style title="a"> and <style title="b"> a browser applies the first alone (a title makes a
        # style one of several to choose between); the site's renderer, and this check, applied both: red in a browser's
        # tab, blue in the icons.
        rule = "path{fill:#ff0000}"
        for inner in ('<style title="a">%s</style>', '<style title="a">path{fill:#0000ff}</style><style title="b">%s</style>', '<style title="">%s</style>', '<style title=" ">%s</style>',
                      '<style type="text/css" media="all" title="default">%s</style>', '<defs><style title="a">%s</style></defs>', '<g><style title="a">%s</style></g>',
                      '<style>%s</style><style title="b">path{fill:#0000ff}</style>', '<style title="a"/><style>%s</style>'):
            with self.subTest(inner=inner):
                err = refused(self, svg(inner % rule), "style-title")
                for word in ("title", "browser", "Ask the tool"):
                    self.assertIn(word, str(err))
        self.assertEqual(refused(self, _input.mark(_input.load(svg('<style title="a">%s</style>' % rule))).colour, "style-title").code, "style-title")
        # a title on anything else is a word about it: left out with the attributes this check does not use (or without
        # a word, where it is another program's own), and the <title> element is left out as ever
        for inner, notes in (('<style>%s</style><g title="a"/>', 1), ('<style>%s</style><rect title="a" width="9" height="9" fill="#ff0000"/>', 1), ("<style>%s</style><title>a</title>", 0),
                             ('<style xlink:title="a">%s</style>', 0), ('<style data-title="a">%s</style>', 0)):
            with self.subTest(inner=inner):
                clean = _svg.clean_svg(svg(inner % rule))
                self.assertEqual((clean.colours, len(clean.notes)), (["#ff0000"], notes), clean.notes)

    def test_display_inherit_is_refused_wherever_it_is_set(self):
        # Measured 2026-10-13: on a shape inside a clip path (set there, or by a rule every element matches) it makes the
        # site's renderer draw nothing of what is clipped, where a browser clips as if the word were not there; and for
        # three of four spellings the renderer drew the file as it came (blank) and the cleaned file (drawn) differently.
        clip = '<clipPath id="c"><rect %s width="4" height="4"/></clipPath><rect clip-path="url(#c)" width="9" height="9"/>'
        for doc in (bare(clip % 'display="inherit"'), bare(clip % 'style="display:inherit"'), bare("<style>*{display:inherit}</style>" + clip % ""),
                    bare("<style>clipPath{display:inline}rect{display:inherit}</style>" + clip % ""), bare("<style>clipPath{display:block}</style>" + clip % 'style="display:inherit"'),
                    bare('<rect display="inherit" width="9" height="9"/>'), bare('<g display=" inherit "><rect width="9" height="9"/></g>'), svg(root='display="inherit"'),
                    svg("<style>.unused{display:inherit}</style>"), bare('<clipPath id="c" display="inherit"><rect width="4" height="4"/></clipPath><rect clip-path="url(#c)" width="9" height="9"/>')):
            with self.subTest(doc=doc[110:190]):
                err = refused(self, doc, "bad-value")
                self.assertIn("display", str(err))
                self.assertIn("inherit", str(err))
        self.assertEqual(refused(self, _input.mark(_input.load(bare(clip % 'display="inherit"'))).colour, "bad-value").code, "bad-value")
        for word in ("inline", "block"):
            self.assertEqual(_svg.clean_svg(bare(clip % ('display="%s"' % word))).colours, ["#000000"])

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
                    self.assertIn("an element of the drawing (<", str(err))   # a <title>, a <g>, a <defs>: none of them is "a drawing element"
                    self.assertNotIn("a drawing element", str(err))
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
        # a renderer takes no blank off an id: ` a` is not the `a` that `#a` names (measured 2026-10-12: the rect stays black).
        # So the rule does not apply to it here either, and the id itself, which nothing is named by, is left out.
        for value in (" a", "a ", " a ", "&#9;a", "a&#10;", "a b", "", "A", "a\u00a0"):
            with self.subTest(value=value):
                clean = _svg.clean_svg(bare('<style>#a{fill:#ff0000}</style><rect id="%s" width="9" height="9"/>' % value))
                self.assertEqual((clean.colours, clean.notes), (["#000000"], []))
                self.assertNotIn("id=", clean.text)
        clean = _svg.clean_svg(bare('<style>#a{fill:#ff0000}</style><rect id="a" width="9" height="9"/>'))
        self.assertEqual(clean.colours, ["#ff0000"])
        self.assertNotIn("id=", clean.text, "the rule is written out as the colour it gives: the id has done its work")

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
        """Each value is kept: as it is written with its blanks taken off, or, given as (value, written), as the cleaned
        file writes it (a list is set out with one blank between two of its entries)."""
        for value in values:
            value, written = value if isinstance(value, tuple) else (value, value.strip(" \t\r\n"))
            for doc in self.places(name, value, **where):
                with self.subTest(name=name, value=value[:60], doc=doc[150:210]):
                    clean = _svg.clean_svg(doc)
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


def spaced(value):
    """A number list as the cleaned file writes it: its numbers, one blank between two of them."""
    return (value, " ".join(re.findall(r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", value)))


def set_out(value):
    """A transform as the cleaned file writes it: each function with its numbers, one blank between two of anything."""
    return (value, " ".join("%s(%s)" % (name, spaced(numbers)[1]) for name, numbers in re.findall(r"([A-Za-z]+)[ \t\r\n]*\(([^()]*)\)", value)))


# The box of svg() and bare() is 64 by 64, from 0: a number that places or sizes a shape may be 100 times 64 from
# the box's far edge, and no further (see HowFarADrawingReaches).
FAR = 6464

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

    FORMS = ANumber.FORMS[:-1] + ["5px", "5.0px", "+5px", ".5e1px", "5e0px", " 5px ", "0", "0px", "0.0", str(FAR), "%dpx" % FAR, "6.464e3"]

    def test_what_it_takes(self):
        self.takes("stroke-dashoffset", self.FORMS + ["-5", "-5px", "-.5e1", "-0", "-%d" % FAR], tag="path", more='d="M0 0h9v9"')
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
            # the cap counts the whole value: `0` 63 times and `5px` is 66 characters, and was kept until 2026-10-13
            self.turns_down(name, ["0" * 64 + "5", "0" * 64 + "5px", "0" * 63 + "5px", "0" * 62 + "5px", "+" + "0" * 63 + "5", "1e10", "1e10px", "9e99", "1000000001", "4e38px"],
                            "value-too-long", **where)
        self.takes("r", ["0" * 63 + "5", "0" * 61 + "5px", "+" + "0" * 62 + "5", "  " + "0" * 63 + "5  "], tag="circle", more="")
        self.assertEqual((len("0" * 63 + "5"), len("0" * 61 + "5px")), (_svg.MAX_VALUE, _svg.MAX_VALUE))


class APosition(Line):
    """position: a length, or a number and % (a share of the drawing's box). x, y, cx, cy, x1, y1, x2, y2; and, not
    below zero, width and height."""

    FORMS = ALength.FORMS + ["50%", "50.0%", "+50%", "5e1%", ".5e2%", " 50% ", "0%", "100%", "150%", "10100%"]
    NAMES = (("x", {}), ("y", {}), ("width", dict(more='height="9"')), ("height", dict(more='width="9"')), ("cx", dict(tag="circle", more='r="3"')),
             ("cy", dict(tag="circle", more='r="3"')), ("x1", dict(tag="line", more='stroke="#ff0000"')), ("y1", dict(tag="line", more='stroke="#ff0000"')),
             ("x2", dict(tag="line", more='stroke="#ff0000"')), ("y2", dict(tag="line", more='stroke="#ff0000"')))

    def test_what_it_takes(self):
        for name, where in self.NAMES:
            self.takes(name, self.FORMS + ([] if name in ("width", "height") else ["-5", "-5px", "-50%", "-.5e1", "-0", "-%d" % FAR]), **where)

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
            self.turns_down(name, ["0" * 64 + "5", "0" * 64 + "5%", "0" * 63 + "5%", "0" * 62 + "5px", "1e10", "1e10%", "9e99", "1000000001px"], "value-too-long", **where)
            self.takes(name, ["0" * 63 + "5", "0" * 62 + "5%", "0" * 61 + "5px"], **where)


class ANumberList(Line):
    """number list: numbers with blanks between them, or one comma, or nothing where the next number begins with a sign
    or a point. points (an even count, 2,000 at most); stroke-dasharray (`none`, or 1 to 16 numbers, none below zero)."""

    def test_what_points_takes(self):
        values = ["", "1 2", "1,2", "1 , 2", "1  2", "1\t2\n3\r4", "1,2 3,4 5,6", "1,2,3,4", " 1 2 ", "10-20", "10-20,3.5.5 1e2,4", "1+2", ".5.5", "-1-2 -3-4", "1e1-2",
                  "1e2.5", "+1 -2", "1E0 2e-1", "0 0 %d -%d" % (FAR, FAR), "1 2 " * (_svg.MAX_POINTS // 2), "0" * 63 + "1 2",
                  # between two points: blanks, or a comma and then blanks
                  "1 2,3 4", "1 2, 3 4", "1,2,\t3,4", "1-2\n\n3-4", "1 , 2,3 , 4", "1.5.5 2+3", "1 2,-3 4", "1 2,.5.5"]
        self.takes("points", [spaced(v) for v in values], tag="polygon", more="")
        # the helper of this test, held to the letter for a few: a list is written with one blank between two numbers
        for value, written in (("1,2", "1 2"), ("10-20,3.5.5 1e2,4", "10 -20 3.5 .5 1e2 4"), ("1\t2\n3\r4", "1 2 3 4"), ("-1-2,-3-4", "-1 -2 -3 -4"), (" 1  ,  2 ", "1 2"), ("", "")):
            self.assertEqual(spaced(value)[1], written)
            self.assertIn(' points="%s"' % written, _svg.clean_svg(svg('<polygon points="%s"/>' % value)).text)

    def test_between_two_points_stand_blanks_or_a_comma_and_nothing_else(self):
        # Measured 2026-10-13: between the two numbers of one point the site's renderer reads a comma after a blank and
        # a number run on to the one before; between two POINTS it reads neither, and draws nothing of the shape. A
        # browser reads both everywhere. (Found when the cleaned file began to write a list with plain blanks: the file as
        # it came was then another drawing than the cleaned one.)
        self.turns_down("points", ["1 2 ,3 4", "1 2 , 3 4", "1,2 ,3,4", "1,2\t,\n3,4", "1 2  ,  3 4", "1 2-3 4", "1 2+3 4", "1 2.5.5 4", "-1-2-3-4", "1,2-3,4", "1 2 3 4 ,5 6",
                                    "1 2 3 4-5 6", "1e1 2e1.5 3"], "bad-value", tag="polygon", more="")
        self.turns_down("points", ["1 2 ,3 4", "1 2-3 4"], "bad-value", tag="polyline", more='stroke="#ff0000"')
        self.assertIsNone(_svg.GRAMMAR["stroke-dasharray"]("1 2 ,3 4"), "in any other list a comma may stand after a blank anywhere")
        self.assertEqual(_svg.clean_svg(svg('<g transform="matrix(1 0 ,0 1-2.5.5)"/>')).text.count('transform="matrix(1 0 0 1 -2.5 .5)"'), 1)

    def test_what_is_no_list_of_points(self):
        self.turns_down("points", ["1", "1 2 3", "1,2,3", "1,2 3", ",1 2", "1 2,", "1,,2", "1 ,, 2", "1, ,2", ",", "1;2", "1 2;", "1.2.", "1 2.", "1px 2px", "1% 2%", "1 2 x", "x", "1 2e",
                                    "1e100 2", "1e123", "1 2e100", "0e309 1", "1_0 2", "\u0661 \u0662", "1\u00a02", "1\u20032", "(1 2)", "1 2)", "none", "auto", "1 2 3 4 5",
                                    "1,2 3,4 5", "M1 2", "1-", "1 -", "1 +", "1 .", "1..2", "1,2,"], "bad-value", tag="polygon", more="")

    def test_points_past_what_a_logo_needs_are_refused_as_that(self):
        self.turns_down("points", ["1 2 " * (_svg.MAX_POINTS // 2 + 1), "1 " * 100000, "0" * 64 + "1 2", "1e10 2", "1 9e99", "1 -1e10"], "value-too-long", tag="polygon", more="")

    def test_what_a_dash_list_takes(self):
        values = ["4", "4 2", "4,2", "4 , 2", "4  2", "4\t2", "4.5.5", "4+2", "+4 +2", ".5 .5e1", "4 2 1", "0", "0 0", "1e9", "4 2 " * (_svg.MAX_DASHES // 2),
                  "4 " * _svg.MAX_DASHES, "0" * 63 + "4"]
        self.takes("stroke-dasharray", ["none", (" none ", "none")] + [spaced(v) for v in values], tag="line", more='x2="9" stroke="#ff0000"')
        for value, written in (("4,2", "4 2"), ("4.5.5", "4.5 .5"), ("4+2", "4 +2"), ("4 , 2", "4 2")):
            self.assertEqual(spaced(value)[1], written)

    def test_what_is_no_dash_list(self):
        self.turns_down("stroke-dasharray", [" ", "4,,2", ",4 2", "4 2,", "4, ,2", "4;2", "4 2 x", "x", "None", "NONE", "none 4", "4 none", "auto", "inherit", "4.", "4 2.", "4e100",
                                             "0e309", "1_0", "\u0664 \u0662", "4\u00a02", "4px", "4px 2px", "50%", "5% 10%", "5%10%", "4 2%", "4mm", "(4 2)", "4/2", "4e"], "bad-value",
                        tag="line", more='x2="9" stroke="#ff0000"')
        refused(self, bare('<line stroke-dasharray="" x2="9" stroke="#ff0000"/>'), "bad-value")   # a list that names no dash, and is not `none`

    def test_a_dash_below_zero_is_refused_as_that(self):
        self.turns_down("stroke-dasharray", ["-4", "4 -2", "4-2", "4,-2", "-0", "4 2 -.5e1", "-1e-9"], "negative-size", tag="line", more='x2="9" stroke="#ff0000"')

    def test_more_dashes_than_a_logo_needs_are_refused_as_that(self):
        # with no cap, one rule's dash list was written onto every element: 228 KB in, a favicon of 20 MB out
        self.turns_down("stroke-dasharray", ["4 " * (_svg.MAX_DASHES + 1), "1 " * 30000, "0" * 64 + "4", "4 1e10", "9e99"], "value-too-long",
                        tag="line", more='x2="9" stroke="#ff0000"')


class ATransform(Line):
    """transform: at most 16 of matrix(6) translate(1 or 2) scale(1 or 2) rotate(1 or 3) skewX(1) skewY(1), each with a
    number list of exactly that many numbers; blanks, one comma or nothing between two of them."""

    def test_what_it_takes(self):
        values = ["", " ", "translate(1)", "translate(1 2)", "translate(1,2)", "translate( 1 , 2 )", "translate(1-2)", "translate(.5.5)", "translate(-1.5e1-2)",
                  "scale(2)", "scale(2 3)", "scale(-1)", "rotate(45)", "rotate(45 1 1)", "rotate(45,1,1)", "rotate(-45.5 1e1 .5)", "skewX(10)", "skewY(-10)",
                  "matrix(1 0 0 1 0 0)", "matrix(1,0,0,1,0,0)", "matrix(1 0 0 1-5 3)", "matrix(.5.5-.5.5.5.5)", "translate(1,2) scale(2)", "rotate(45 1 1),scale(2)",
                  "translate(1) , scale(2)", "translate(1)scale(2)", "translate(1)\nscale(2)\trotate(3)", " translate(1 2) ", "translate(%d)" % FAR, "scale(1e-9)",
                  "scale(1) " * _svg.MAX_TRANSFORMS, "translate(" + "0" * 63 + "1)",
                  # a blank before the bracket: SVG allows it, and the site's renderer reads it as a browser does (measured 2026-10-13)
                  "translate (1)", "translate\t(1 2)", "scale (2)", "rotate \n (45 1 1)", "translate (1)scale  (2)", "matrix  (1 0 0 1 2 3)", "skewX (10) , skewY\r(10)"]
        self.takes("transform", [set_out(v) for v in values], tag="g", more="")
        for value, written in (("translate(1,2) scale(2)", "translate(1 2) scale(2)"), ("matrix(.5.5-.5.5.5.5)", "matrix(.5 .5 -.5 .5 .5 .5)"), ("translate(1)scale(2)", "translate(1) scale(2)"),
                               ("rotate(45 1 1),scale(2)", "rotate(45 1 1) scale(2)"), ("translate (1)scale  (2)", "translate(1) scale(2)"), (" ", ""),
                               ("translate( 1 , 2 )", "translate(1 2)"), ("translate(1)\nscale(2)\trotate(3)", "translate(1) scale(2) rotate(3)")):
            self.assertEqual(set_out(value)[1], written)
            self.assertIn(' transform="%s"' % written, _svg.clean_svg(svg('<g transform="%s"/>' % value)).text)

    def test_what_is_no_transform(self):
        self.turns_down("transform", [
            "translate()", "scale()", "rotate()", "matrix()", "skewX()", "translate( )",                                # a function with nothing in it
            "translate(1 2 3)", "scale(1 2 3)", "rotate(1 2)", "rotate(1 2 3 4)", "skewX(1 2)", "skewY(1 2)", "matrix(1 0 0 1 0)", "matrix(1 0 0 1 0 0 0)",   # not the count it takes
            "translate(1,,2)", "translate(,1)", "translate(1,)", "translate(1 2),", ",translate(1)", "translate(1),,scale(2)", "translate(1), ,scale(2)", "translate(1) ,",
            "trans late(1)", "translate( (1)", "translate ()", "Translate(1)", "TRANSLATE(1)", "translateX(1)", "translate3d(1,2,3)", "perspective(1)", "rotateZ(4)", "skew(1)",
            "none", "inherit", "translate", "translate(", "translate(1", "translate 1)", "translate(1))", "(1)", "translate(1) x", "x translate(1)", "translate(1);scale(2)",
            "translate(1px)", "translate(50%)", "rotate(45deg)", "rotate(1turn)", "scale(2x)", "translate(1.)", "translate(1e100)", "translate(0e309)", "translate(1_0)",
            "translate(\u0661)", "translate(1\u00a02)", "\u00a0translate(1)", "translate(1)\u2003scale(2)", "translate(translate(1))", "translate(1 scale(2))"], "bad-value",
                        tag="g", more="")

    def test_more_than_a_logo_needs_is_refused_as_that(self):
        self.turns_down("transform", ["scale(1) " * (_svg.MAX_TRANSFORMS + 1), "scale(1)" * 40000, "translate(1e10)", "translate(1 9e99)", "matrix(1 0 0 1 4e38 0)",
                                      "translate(" + "0" * 64 + "1)", "translate(1)" + " " * _svg.MAX_RAW, "translate" + " " * _svg.MAX_RAW + "(1)",
                                      "scale(0) " * (_svg.MAX_TRANSFORMS + 1)], "value-too-long", tag="g", more="")

    # NO TRANSFORM SQUASHES WHAT IT IS APPLIED TO FLAT, OR ALL BUT FLAT. Measured 2026-10-13, on one of two shapes inside
    # a clip path: for a scale of nothing the site's renderer draws nothing at all of what is clipped, where a browser
    # clips by the other shape; for a skew of a quarter turn it is the browser that draws nothing (the pictures are in
    # test_render.py). The line is how flat a square comes out: thicker than a ten-thousandth of its length.
    FLAT = [
        # a scale with a nothing in it, however the nothing is written; and one the renderer reads as nothing (it reads a number in single precision)
        "scale(0)", "scale(0 0)", "scale(1 0)", "scale(0 1)", "scale(0,5)", "scale(-0)", "scale(+0.0)", "scale(0e5)", "scale(.0 1)", "scale( 0 )", "scale (0)", "scale(1e-46)", "scale(1e-99)",
        "scale(1 1e-46)", "scale(1e-10)", "scale(-1e-10 1e-10)",
        # a matrix whose a times d is its b times c, or all but
        "matrix(0 0 0 0 0 0)", "matrix(0 0 0 0 5 5)", "matrix(1 2 2 4 0 0)", "matrix(1 0 0 0 0 5)", "matrix(0 1 0 0 0 0)", "matrix(.1 .3 .1 .3 0 0)", "matrix(.1 .3 .7 2.1 0 0)", "matrix(-1 2 2 -4 1 1)",
        "matrix(1 2 2 4.0000000000000009 0 0)", "matrix(1 2 2 4.0001 0 0)", "matrix(1e-99 0 0 1e-99 0 0)", "matrix(1e-46 0 0 1 0 0)", "matrix(1 0 100 1 0 0)", "matrix(1,0,0,1e-4,0,0)",
        # a skew of a quarter turn, or within about half a degree of one, and any number of half turns on from there
        "skewX(90)", "skewY(90)", "skewX(-90)", "skewY(-90)", "skewX(270)", "skewY(450)", "skewX(-270)", "skewX(9e1)", "skewX(90.0)", "skewX(+90)", "skewX(89.999999)", "skewX(90.0000001)",
        "skewX(89.5)", "skewY(90.5)", "skewX(89.43)", "skewX(990)", "skewY(630)",
        # one of several, wherever it stands in the list
        "translate(1) scale(0)", "scale(0) scale(1)", "rotate(45) scale(1 0) rotate(-45)", "scale(2),skewX(90)", "translate(1)matrix(1 2 2 4 0 0)translate(2)", "scale(1) " * 15 + "scale(0)",
        # all of them together, none of them flat alone: steep skews, stretches at an angle
        "skewX(89.4) skewX(89.4)", "skewX(89.4) skewY(89.4) " * 8, "skewX(60) skewY(60) " * 8, "scale(100 1) rotate(45) " * 8, "matrix(1 1 1 1.01 0 0) matrix(1 1 1 1.01 0 0) matrix(1 1 1 1.01 0 0)",
        "scale(1 .001) rotate(45) scale(1 .001)",
        # all of them together leave too little of an area, each of them at the least or above it (until round 7 the list was held to its thinness alone)
        "scale(1e-9) scale(1e-9)", "scale(1e-9) " * 6, "scale(1e-9) " * 16, "matrix(1e-9 0 0 1e-9 0 0) matrix(0 1e-9 -1e-9 0 0 0)", "scale(1e-9) rotate(30) scale(.5)", "scale(.001) " * 4,
        "scale(1e-5) scale(1e-5)", "scale(-1e-9) scale(-1e-9)", "scale(1e-9 1e-8) scale(1e-8 1e-9)", "translate(1) scale(1e-9) translate(1) scale(.99)",
        # truly under the least area, with a turn in the list, in either order (the room for rounding is a thousand-millionth, not more)
        "scale(1e-9) rotate(6) scale(.99)", "scale(.99) rotate(6) scale(1e-9)", "rotate(6) scale(.999e-9)", "scale(.999e-9) rotate(6)", "scale(1e-9) rotate(6) scale(.9999995)",
        "scale(1e-9) scale(.99999999)", "scale(.001) scale(.001) scale(.001) rotate(6) scale(.999)", "rotate(6) scale(.001) scale(.001) scale(.001) scale(.999)", "scale(.999999999e-9)",
        # and a list that goes under the line on its way is refused, though it ends above it
        "scale(1e-6) scale(1e-6) scale(1000) scale(1000)", "scale(.001) " * 8 + "scale(1000) " * 8,
    ]
    NOT_FLAT = [
        "scale(1)", "scale(-1)", "scale(-1 1)", "scale(.001)", "scale(1e-9)", "scale(1e-9 1e-9)", "scale(1 .001)", "scale(.001 1)", "scale(100 1)", "scale(%d .7)" % FAR,
        # small scales that multiply to no less than the least: nested ordinary ones, and the smallest beside what changes no area
        "scale(.1) scale(.1) scale(.1)", "scale(.1) " * 9, "scale(.5) " * 16, "scale(.001) scale(.001) scale(.001)", "scale(1e-9) scale(1)", "scale(1e-9) translate(5) rotate(30)", "scale(-1) scale(1e-9)",
        "scale(1e-6) scale(1000) scale(1e-6) scale(1000)", "scale(1e-9) scale(2) scale(.5)",
        # a turn keeps an area: multiplied out, the least area with a turn beside it comes to 9.999999999999999e-19, and for
        # that hair round 7 refused these (round 6 kept them). In both orders, and with a turn on each side.
        "scale(1e-9) rotate(6)", "rotate(6) scale(1e-9)", "scale(.001) scale(.001) scale(.001) rotate(6)", "rotate(6) scale(.001) scale(.001) scale(.001)",
        "rotate(17) scale(1e-9) rotate(-17)", "scale(1e-9) rotate(6 3 3)", "scale(1e-9) " + "rotate(7) " * 14 + "rotate(7)", "rotate(7) " * 15 + "scale(1e-9)",
        "matrix(1 0 0 1 0 0)", "matrix(0 1 -1 0 0 0)", "matrix(.866 .5 -.5 .866 3 4)", "matrix(1 0 99 1 0 0)", "matrix(1 2 2 5 0 0)", "matrix(1e-9 0 0 1e-9 0 0)", "matrix(0 1e-9 -1e-9 0 0 0)",
        "matrix(-1 0 0 1 64 0)", "matrix(1.3333 0 0 -1.3333 0 64)",
        "skewX(0)", "skewX(45)", "skewY(-30)", "skewX(80)", "skewX(89)", "skewX(89.4)", "skewX(-89.4)", "skewY(89.4)", "skewX(90.6)", "skewX(180)", "skewX(269.4)", "skewY(360)", "skewX(91)",
        "rotate(90)", "rotate(89.999999)", "rotate(1e5)", "rotate(-100000 5 5)", "skewX(100000)", "skewY(-99999.5)", "rotate(90 5 5)", "translate(0)", "translate(0 0)", "translate(%d)" % FAR,
        "skewX(45) skewY(45) skewX(45)", "scale(100 1) rotate(45) scale(100 1)", "rotate(30) scale(2 1) rotate(-30)", "translate(1) " * 16, "rotate(22.5) " * 16, "scale(1 .01) rotate(90) scale(1 .01)",
    ]

    def test_a_transform_that_squashes_what_it_is_applied_to_flat_is_refused_by_name(self):
        for value in self.FLAT:
            for doc in (svg('<g transform="%s"/>' % value), svg('<rect transform="%s" width="9" height="9"/>' % value),
                        svg('<clipPath id="c"><rect transform="%s" width="3" height="9"/><rect x="5" width="2" height="9"/></clipPath><rect clip-path="url(#c)" width="9" height="9"/>' % value),
                        svg('<clipPath id="c" transform="%s"><rect width="3" height="9"/></clipPath>' % value), svg('<defs><g transform="%s"><path d="M0 0h1v1z"/></g></defs>' % value)):
                with self.subTest(value=value[:50], doc=doc[150:190]):
                    err = refused(self, doc, "flat-transform")
                    for said in ("a transform", "flat", "what is left to draw", "Ask the tool", "transforms applied to the shapes"):
                        self.assertIn(said, str(err))
                    # true of a list that ends flat and of one that only goes under a line on its way and comes back
                    self.assertIn("squashes what it is applied to flat, or all but flat, at its end or at a step on its way (", str(err))
        # the sentence shows the one function that does it, or (where only all of them together do) where the list starts
        self.assertIn("(scale(0))", str(refused(self, svg('<g transform="translate(1)  scale(0) rotate(5)"/>'), "flat-transform")))
        self.assertIn("(skewX( 90 ))", str(refused(self, svg('<g transform="rotate(5),skewX( 90 )"/>'), "flat-transform")))
        self.assertIn("(skewX(89.4) skewX(89.4))", str(refused(self, svg('<g transform="skewX(89.4)\nskewX(89.4)"/>'), "flat-transform")))
        self.assertIn("(scale(1e-9) scale(1e-9))", str(refused(self, svg('<g transform="scale(1e-9)\n scale(1e-9)"/>'), "flat-transform")))
        self.assertLess(len(str(refused(self, svg('<g transform="%s"/>' % ("skewX(60) skewY(60) " * 8)), "flat-transform"))), 400)
        # on the outer svg a transform is refused as that, whatever it does
        refused(self, svg(root='transform="scale(0)"'), "root-transform")
        # and it is a transform that is held so: a size of nothing is a shape that draws nothing, in every program
        self.assertEqual(_svg.clean_svg(svg('<rect width="0" height="0" fill="#111111"/><circle r="0"/>')).colours[-1], "#b4531a")

    def test_a_transform_that_leaves_a_shape_its_form_is_kept(self):
        self.takes("transform", [set_out(v) for v in self.NOT_FLAT], tag="g", more="")
        for value in self.NOT_FLAT:   # and inside a clip path, on the clip path and on what it clips
            with self.subTest(value=value[:50]):
                doc = svg('<clipPath id="c" transform="%s"><rect transform="%s" width="3" height="9"/><rect x="5" width="2" height="9"/></clipPath><rect transform="%s" clip-path="url(#c)" width="9" height="9"/>'
                          % (value, value, value))
                self.assertEqual(_svg.clean_svg(doc).text.count(' transform="%s"' % set_out(value)[1]), 3)

    def test_the_line_between_flat_and_not_is_how_thin_a_square_comes_out(self):
        self.assertEqual((_svg.MAX_SQUASH, _svg.MIN_AREA), (10000, 1e-18))
        # a skew: its tangent stays under 100, which is 89.427 degrees and a little
        line = math.degrees(math.atan(math.sqrt(_svg.MAX_SQUASH - 2)))
        self.assertAlmostEqual(line, 89.427, places=3)
        for turns in (0, 1, 2, -1, -3):
            for name in ("skewX", "skewY"):
                for sign in (1, -1):
                    inside, outside = sign * (line - 0.001) + 180 * turns, sign * (line + 0.001) + 180 * turns
                    with self.subTest(name=name, inside=inside):
                        _svg.clean_svg(svg('<g transform="%s(%.6f)"/>' % (name, inside)))
                        refused(self, svg('<g transform="%s(%.6f)"/>' % (name, outside)), "flat-transform")
        # a stretch one way: a ten-thousandth as thick as it is long is where it ends
        for kept, flat in (("scale(1 .00011)", "scale(1 .0001)"), ("scale(.00011 1)", "scale(.0001 1)"), ("scale(9000 1)", "scale(10001 1)"), ("matrix(1 0 99.9 1 0 0)", "matrix(1 0 100 1 0 0)"),
                           ("matrix(1 99.9 0 1 0 0)", "matrix(1 100 0 1 0 0)"), ("matrix(1 2 2 4.01 0 0)", "matrix(1 2 2 4.001 0 0)"),
                           # and an area: a thousand million times smaller each way is the least one function leaves
                           ("scale(1e-9)", "scale(.99e-9)"), ("scale(1e-8 2e-10)", "scale(1e-8 .5e-10)"), ("matrix(0 1e-9 -1e-9 0 0 0)", "matrix(0 1e-9 -.99e-9 0 0 0)")):
            with self.subTest(kept=kept, flat=flat):
                _svg.clean_svg(bare('<g transform="%s"><rect width="9" height="9"/></g>' % kept).replace(b'viewBox="0 0 64 64"', b'viewBox="0 0 640 640"'))
                refused(self, svg('<g transform="%s"/>' % flat), "flat-transform")
        # exactly 10,000 times as long as thick is flat already (the comment, the grammar and the docstring said it was kept)
        for flat in ("scale(10000 1)", "scale(1 10000)", "scale(1 .0001)", "scale(1 1e-4)", "scale(1e-4 1)", "matrix(1 0 0 .0001 0 0)"):
            with self.subTest(flat=flat):
                refused(self, svg('<g transform="%s"/>' % flat).replace(b'viewBox="0 0 64 64"', b'viewBox="0 0 640 640"'), "flat-transform")
        for said in (_svg.__doc__, _svg._flattens.__doc__):
            self.assertIn("scale(1 .0001)", said)
            self.assertNotIn("squashed to less than a ten-thousandth", said)
            self.assertNotIn("no thinner than one to MAX_SQUASH", said)
        self.assertIn("exactly 10,000 times as long as it is thick is flat already", " ".join(_svg.__doc__.split()))
        # THE LIST IS HELD TO THE SAME TWO LINES AS ONE FUNCTION. Six of the smallest scale there is each passed, and the
        # list was held to its thinness alone: they multiplied to a scale of 1e-54 each way and were kept.
        for kept, flat in (("scale(1e-9)", "scale(1e-9) scale(1e-9)"), ("scale(1e-9) scale(1)", "scale(1e-9) scale(.99)"), ("scale(.001) " * 3, "scale(.001) " * 4),
                           ("scale(.1) " * 9, "scale(.1) " * 10), ("scale(1e-3 1e-3) scale(1e-3 1e-3) scale(1e-3)", "scale(1e-3 1e-3) scale(1e-3 1e-3) scale(.99e-3 1e-3)"),
                           ("scale(1e-6) scale(1000) scale(1e-6) scale(1000)", "scale(1e-6) scale(1e-6) scale(1000) scale(1000)")):
            with self.subTest(kept=kept, flat=flat):
                _svg.clean_svg(svg('<g transform="%s"/>' % kept))
                err = refused(self, svg('<g transform="%s"/>' % flat), "flat-transform")
                self.assertIn("(%s" % " ".join(flat.split())[:40], str(err))   # the list is shown from where it starts: no one function does it
        self.assertEqual(_svg._transform(" ".join(["scale(1e-9)"] * 6)), ("flat", " ".join(["scale(1e-9)"] * 6)))
        self.assertIsNone(_svg._transform("scale(.1) scale(.1) scale(.1)"))

    def test_a_turn_beside_the_least_area_is_kept_whichever_way_the_rounding_falls(self):
        # A turn keeps an area. Multiplied out, scale(1e-9) rotate(6) leaves 9.999999999999999e-19 of one, a rounding hair
        # under the least, and the list was refused for it (kept until round 7 held the list on its way). The line has
        # room for rounding now, one part in a thousand million, and what is truly under it is refused as before.
        self.assertEqual(_svg.AREA_ROUNDING, 1e-9)
        turn = math.radians(6)
        self.assertLess(1e-9 * math.cos(turn) * 1e-9 * math.cos(turn) + 1e-9 * math.sin(turn) * 1e-9 * math.sin(turn), _svg.MIN_AREA, "the hair this is about")
        least = ("scale(1e-9)", "scale(.001) scale(.001) scale(.001)", "scale(1e-8 1e-10)", "matrix(0 1e-9 -1e-9 0 0 0)")
        for tenth in range(0, 3600, 7):   # every angle, not the one that was found
            for small in least:
                for value in ("%s rotate(%g)" % (small, tenth / 10.0), "rotate(%g) %s" % (tenth / 10.0, small), "rotate(%g) %s rotate(-%g)" % (tenth / 10.0, small, tenth / 10.0)):
                    self.assertIsNone(_svg._transform(value), value)
        for kept, flat in (("scale(1e-9) rotate(6)", "scale(1e-9) rotate(6) scale(.99)"), ("rotate(6) scale(1e-9)", "rotate(6) scale(.999e-9)"),
                           ("scale(.001) scale(.001) scale(.001) rotate(6)", "scale(.001) scale(.001) scale(.001) rotate(6) scale(.999)"),
                           ("rotate(6) scale(.001) scale(.001) scale(.001)", "rotate(6) scale(.001) scale(.001) scale(.00099)"),
                           # the room is a thousand-millionth of the area and no more: a hundred-millionth under each way is refused
                           ("rotate(17) scale(1e-9) rotate(-17)", "scale(1e-9) scale(.99999999)"), ("scale(1e-9) rotate(6)", "scale(1e-9) rotate(6) scale(.99999999)")):
            with self.subTest(kept=kept, flat=flat):
                self.assertEqual(_svg.clean_svg(svg('<g transform="%s"/>' % kept)).colours, ["#b4531a"])
                self.assertIn("flat, or all but flat", str(refused(self, svg('<g transform="%s"/>' % flat), "flat-transform")))
        for said in (_svg.__doc__, _svg._flattens.__doc__):
            self.assertIn("scale(1e-9) rotate(6)", said)
            self.assertIn("one part in a thousand million", " ".join(said.split()))

    def test_a_list_is_held_where_it_goes_under_a_line_on_its_way_and_not_where_it_goes_far_above(self):
        # A STATED LIMIT, not a rule: there is no line above. A list that goes far up on its way and comes back is kept, and
        # from a running scale of 1e40 each way on the site's renderer draws the shape and a browser does not (made by hand
        # and measured 2026-10-13, in a box of a million, where numbers of a hundred million pass the "how far" line). The
        # grammar and _flattens say so; if a line above is ever drawn, this test and those two sentences change together.
        in_a_large_box = lambda value: ('<svg %s viewBox="0 0 1000000 1000000"><g transform="%s"><rect width="4000" height="4000" fill="#111111"/></g></svg>' % (NS, value)).encode()
        for up, down in ((3, "scale(1e-9) " * 2 + "scale(1e-4)"), (5, "scale(1e-9) " * 4 + "scale(.01)"), (7, "scale(1e-9) " * 6), (8, "scale(1e-9) " * 7 + "scale(.1)")):
            value = "scale(1e8) " * up + down
            with self.subTest(value=value):
                self.assertIn(' transform="%s"' % set_out(value)[1], _svg.clean_svg(in_a_large_box(value)).text)
        # the mirror of it, down on its way and up again, is refused as it was
        refused(self, in_a_large_box("scale(1e-9) " * 5 + "scale(1e8) " * 6), "flat-transform")
        for said in (_svg.__doc__, _svg._flattens.__doc__):
            self.assertIn("not where it goes far above on its way and comes back", " ".join(said.split()))
        self.assertIn("nesting that goes so far was only ever made by hand", " ".join(_svg.__doc__.split()))
        self.assertNotIn("such nesting was only ever made by hand", " ".join(_svg.__doc__.split()))

    def test_an_angle_too_large_to_be_read_exactly_is_refused_by_name(self):
        # Both programs read a number in single precision. The check worked an angle out in double: skewX(20000070.9) was
        # 90.9 degrees on from whole turns to the check (kept), and 90 on from them to both programs, which is the skew of
        # a quarter turn that flat-transform refuses. Up to 100,000 degrees single precision keeps an angle to a hundredth.
        self.assertEqual(_svg.MAX_ANGLE, 100000)
        far = ["skewX(20000070.9)", "skewY(20000070.9)", "rotate(999999990 5 5)", "rotate(123456789 4 4)", "rotate(1e9)", "rotate(100000.01)", "rotate(-100000.01)", "rotate(100001 5 5)",
               "skewX(100001)", "skewX(-100001)", "skewY(1e6)", "skewY(-1.1e5)", "rotate( 1e8 )", "rotate (16777217 5 5)", "translate(1) rotate(200000)", "rotate(200000),scale(2)",
               "rotate(30) " * 15 + "skewX(1e7)"]
        for value in far:
            for doc in (svg('<g transform="%s"/>' % value), svg('<rect transform="%s" width="9" height="9"/>' % value),
                        svg('<clipPath id="c" transform="%s"><rect width="3" height="9"/></clipPath><rect clip-path="url(#c)" width="9" height="9"/>' % value)):
                with self.subTest(value=value[:40], doc=doc[150:190]):
                    err = refused(self, doc, "angle-too-large")
                    for said in ("turns or slants", "more than 100,000 degrees", "only roughly", "Ask the tool", "between 0 and 360"):
                        self.assertIn(said, str(err))
        # the sentence shows the function that holds the angle
        self.assertIn("(rotate( 200000 5 5 ))", str(refused(self, svg('<g transform="translate(1)  rotate( 200000\n5 5 ) scale(2)"/>'), "angle-too-large")))
        # the line is 100,000 either way, and it is about an angle alone: a number that places something has its own line
        for kept in ("rotate(100000)", "rotate(-100000)", "rotate(1e5 5 5)", "skewX(100000)", "skewY(-100000)", "rotate(99999.99)", "rotate(360)", "rotate(720.5)", "rotate(0)", "skewX(-0)",
                     "rotate(30 %d 5)" % FAR, "translate(%d)" % FAR, "scale(100 1)", "matrix(1 0 0 1 %d 0)" % FAR):
            with self.subTest(kept=kept):
                self.assertIn(' transform="%s"' % set_out(kept)[1], _svg.clean_svg(svg('<g transform="%s"/>' % kept)).text)
        refused(self, svg('<g transform="rotate(30 100001 5)"/>'), "too-far")
        refused(self, svg('<g transform="translate(100001)"/>'), "too-far")
        # whichever fault comes first in the list is the one that is said; a number that is no number at all stays that
        refused(self, svg('<g transform="scale(0) rotate(200000)"/>'), "flat-transform")
        refused(self, svg('<g transform="rotate(200000) scale(0)"/>'), "angle-too-large")
        refused(self, svg('<g transform="rotate(2e10)"/>'), "value-too-long")
        refused(self, svg('<g transform="rotate(200000 5)"/>'), "bad-value")
        # through the door the intake uses, as a file and inside a package (where the refusal says which file)
        doc = bare('<rect transform="skewX(20000070.9)" width="9" height="9"/>')
        self.assertEqual(refused(self, _input.mark(_input.load(doc)).colour, "angle-too-large").code, "angle-too-large")
        err = refused(self, _input.mark(_input.load(T.build_zip([("pack/logo.svg", doc)]))).colour, "angle-too-large")
        self.assertTrue(str(err).startswith("In the package, the file 'pack/logo.svg': The file turns or slants a shape"), str(err))
        # the grammar at the top of the file says the line and the way out
        said = " ".join(_svg.__doc__.split())
        for words in ("no further from zero than 100,000 degrees", "skewX(20000070.9)", "between 0 and 360"):
            self.assertIn(words, said)

    def test_the_rule_looks_at_one_transform_attribute_at_a_time_and_says_so(self):
        # A STATED LIMIT, not a rule: transforms on elements inside one another are not multiplied. Each of these files
        # is kept, though the transforms of its nested groups come to nothing together (the first) or undo each other
        # (the second); made by hand and measured 2026-10-13, one of the two programs draws nothing of each. The grammar
        # and the docstring say so. If nesting is ever held, this test is the one to turn round.
        small, large = " ".join(["scale(.001)"] * 3), " ".join(["scale(1000)"] * 3)
        nested = '<g transform="%s"><g transform="%s"><g transform="%s"><g transform="%s"><rect width="9" height="9"/></g></g></g></g>'
        for what, doc, kept in (("down and down, and up and up", svg(nested % (small, small, large, large)), 4),
                                ("steep skews and back", svg(nested % ("skewX(89.4)", "skewY(89.4)", "skewY(-89.4)", "skewX(-89.4)")), 4),
                                ("a clip path's and its shape's", svg('<clipPath id="c" transform="%s"><rect transform="%s" width="3" height="9"/></clipPath><rect clip-path="url(#c)" width="9" height="9"/>' % (small, small)), 2)):
            with self.subTest(what=what):
                self.assertEqual(_svg.clean_svg(doc).text.count(" transform="), kept)
        # the same functions in ONE attribute are held
        refused(self, svg('<g transform="%s %s %s %s"/>' % (small, small, large, large)), "flat-transform")
        refused(self, svg('<g transform="skewX(89.4) skewY(89.4) skewY(-89.4) skewX(-89.4)"/>'), "flat-transform")
        for said in (" ".join(_svg.__doc__.split()), " ".join(_svg._flattens.__doc__.split())):
            for words in ("ONE", "attribute at a time", "inside one another", "are not multiplied"):
                self.assertIn(words, said)

    def test_a_flat_transform_is_refused_through_the_door_the_intake_uses(self):
        doc = bare('<clipPath id="c"><rect transform="scale(0)" width="3" height="9"/><rect x="5" width="2" height="9"/></clipPath><rect clip-path="url(#c)" width="9" height="9"/>')
        self.assertEqual(refused(self, _input.mark(_input.load(doc)).colour, "flat-transform").code, "flat-transform")
        err = refused(self, _input.mark(_input.load(T.build_zip([("pack/logo.svg", doc)]))).colour, "flat-transform")
        self.assertTrue(str(err).startswith("In the package, the file 'pack/logo.svg': The file has a transform"), str(err))


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
             "visibility": ["visible", "hidden", "collapse"], "display": ["inline", "block", "none"],
             "shape-rendering": ["auto", "optimizeSpeed", "crispEdges", "geometricPrecision"]}

    def test_the_words_are_the_ones_in_the_table(self):
        self.assertEqual({k: sorted(v) for k, v in _svg._KEYWORDS.items() if k != "clipPathUnits"}, {k: sorted(v) for k, v in self.WORDS.items()})
        self.assertEqual(sorted(_svg._KEYWORDS["clipPathUnits"]), ["userSpaceOnUse"])

    def test_what_it_takes(self):
        for name, words in self.WORDS.items():
            self.takes(name, words + [" %s " % words[0], "\t%s\n" % words[-1]])
        self.takes("paint-order", ["normal", "fill", "stroke", "markers", "fill stroke", "stroke fill", "stroke fill markers", "markers stroke fill", ("stroke  markers", "stroke markers"),
                                   " stroke ", ("fill\tmarkers\nstroke", "fill markers stroke")])

    def test_what_is_no_word_of_its_property(self):
        for name, words in self.WORDS.items():
            near = ["", words[0].upper(), words[0].capitalize(), words[0] + "x", "x" + words[0], words[0] + " " + words[-1], words[0] + ",", words[0][:-1], "initial", "unset",
                    "revert", "0", "1", "true", words[0] + "\u00a0", "\u00a0" + words[0], words[0].replace("o", "\u03bf")]
            self.turns_down(name, [v for v in near + ["inherit", "Inherit", " inherit "] if v not in words], "bad-value")
        # measured 2026-10-12: the site's renderer reads neither of these two joins and keeps the join it had; a browser reads both
        self.turns_down("stroke-linejoin", ["arcs", "miter-clip", "miter clip", "crop", "fallback"], "bad-value")
        self.turns_down("display", ["inline-block", "flex", "grid", "contents", "table", "list-item", "run-in", "None", "NONE", "Inline"], "bad-value")
        self.turns_down("visibility", ["visible hidden", "Hidden", "show", "hide", "0"], "bad-value")
        self.turns_down("shape-rendering", ["optimizespeed", "crispedges", "geometricprecision", "optimizeQuality", "crisp-edges", "pixelated"], "bad-value")
        self.turns_down("paint-order", ["", "stroke stroke", "fill stroke markers fill", "normal fill", "fill normal", "sideways", "Stroke", "stroke,fill", "fill/stroke", "inherit",
                                        "stroke\u00a0fill", "stroke" + " " * _svg.MAX_VALUE + "fill", "markers markers"], "bad-value")

    def test_clip_path_units_on_a_clip_path(self):
        # A clip path is measured in the drawing's own units: `userSpaceOnUse`, written or left out. Measured by the box
        # of the shape it clips (`objectBoundingBox`) it is refused by name. Measured 2026-10-13: where the clip path
        # also carries a transform, the site's renderer draws 4,000 of 10,000 pixels and a browser 5,000; a straight
        # line clipped so (a box with no height) is drawn whole by the one and not at all by the other. No export seen
        # uses that unit (64 files in the styles of design tools).
        inner = '<defs><clipPath id="c" %s><rect width="1" height="1"/></clipPath></defs><rect clip-path="url(#c)" width="9" height="9"/>'
        for word in ("userSpaceOnUse", " userSpaceOnUse ", "&#9;userSpaceOnUse&#10;"):
            self.assertIn('<clipPath id="c" clipPathUnits="userSpaceOnUse">', _svg.clean_svg(bare(inner % ('clipPathUnits="%s"' % word))).text)
        left_out = _svg.clean_svg(bare(inner % ""))
        self.assertIn('<clipPath id="c">', left_out.text)
        self.assertEqual(left_out.notes, [])
        for word in ("objectBoundingBox", " objectBoundingBox ", "&#9;objectBoundingBox&#10;", "\nobjectBoundingBox"):
            for more in ("", ' transform="translate(.6)"', ' transform=""'):
                for used in ('<rect clip-path="url(#c)" width="9" height="9"/>', '<line clip-path="url(#c)" y1="5" x2="9" y2="5" stroke="#111111"/>', '<g clip-path="url(#c)"/>', ""):
                    with self.subTest(word=word, more=more, used=used[:20]):
                        doc = bare('<clipPath id="c" clipPathUnits="%s"%s><rect width="1" height="1"/></clipPath>' % (word, more) + used + '<rect width="9" height="9"/>')
                        err = refused(self, doc, "clip-units")
                        for said in ("clip path", "the box of the shape it clips", 'clipPathUnits="objectBoundingBox"', "different ways", "Ask the tool", "the drawing's own units",
                                     'clipPathUnits="userSpaceOnUse"', "clips applied to the shapes"):
                            self.assertIn(said, str(err))
        for word in ("", "objectboundingbox", "userspaceonuse", "ObjectBoundingBox", "strokeWidth", "userSpace", "userSpaceOnUse objectBoundingBox", "objectBoundingBox userSpaceOnUse", "inherit",
                     "userSpaceOnUse\u00a0", "objectBoundingBox\u00a0", "objectBoundingBoxx"):
            with self.subTest(word=word):
                refused(self, bare(inner % ('clipPathUnits="%s"' % word)), "bad-value")
        # with a prefix it is not the attribute a program reads (left out, as any prefixed attribute is); on anything but a clip path it means nothing
        self.assertNotIn("clipPathUnits", _svg.clean_svg(bare(inner.replace("<defs>", '<defs xmlns:x="urn:editor">') % 'x:clipPathUnits="objectBoundingBox"')).text)
        self.assertNotIn("clipPathUnits", _svg.clean_svg(bare('<g clipPathUnits="objectBoundingBox"><rect width="9" height="9"/></g>')).text)
        # on any element that is no <clipPath> the attribute means nothing: left out with the note every such attribute gets
        for doc in (bare('<g clipPathUnits="objectBoundingBox"><rect width="9" height="9"/></g>'), bare('<rect clipPathUnits="objectBoundingBox" width="9" height="9"/>'),
                    bare('<defs clipPathUnits=" objectBoundingBox "/><path clipPathUnits="objectBoundingBox" d="M0 0h9v9z"/>'), bare('<rect width="9" height="9"/>', root='clipPathUnits="objectBoundingBox"'),
                    bare('<clipPath id="c"><rect clipPathUnits="objectBoundingBox" width="3" height="9"/></clipPath><rect clip-path="url(#c)" width="9" height="9"/>'),
                    bare('<g clipPathUnits="objectBoundingBox"/><circle clipPathUnits="objectBoundingBox" r="3"/>'), bare('<g clipPathUnits="no such word"><rect width="9" height="9"/></g>')):
            with self.subTest(doc=doc[150:210]):
                clean = _svg.clean_svg(doc)
                self.assertNotIn("clipPathUnits", clean.text)
                self.assertEqual(clean.notes, ["left out attributes this check does not use: clipPathUnits"])
        # through the door the intake uses, as a file and inside a package
        doc = bare(inner % 'clipPathUnits="objectBoundingBox"')
        self.assertEqual(refused(self, _input.mark(_input.load(doc)).colour, "clip-units").code, "clip-units")
        self.assertEqual(refused(self, _input.mark(_input.load(T.build_zip([("pack/logo.svg", doc)]))).colour, "clip-units").code, "clip-units")


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
    """id: an ASCII letter, a digit or `_`, then letters, digits and `_ - . :`; 64 characters at most. Taken as it is
    written: a renderer takes no blank off an id. This is the id a clip path is named by, the one id the cleaned file
    keeps; every other id is left out, whatever it is written in (see Ids)."""

    CLIP = '<defs><clipPath id="%s"><rect width="4" height="4"/></clipPath></defs><rect clip-path="url(#%s)" width="9" height="9"/>'

    def test_what_it_takes(self):
        for value in ("a", "A", "_", "a1", "Layer_1", "clip0_12_34", "SVGID_1_", "a-b", "a.b", "a:b", "_-.:", "a" * 64, "Ebene_1", "path111",
                      # one common design tool names its clip paths in hex digits, and most of those names start with a digit
                      "1a", "1a2b3c4d5e", "8ce47d5fb1", "0", "007", "9-9", "1.5", "1e5", "0x1f", "7:a", "4" * 64):
            with self.subTest(value=value):
                for use in ('<rect clip-path="url(#%s)" width="9" height="9"/>', '<rect clip-path=" url( #%s ) " width="9" height="9"/>', '<rect style="clip-path:url(#%s)" width="9" height="9"/>',
                            '<style>.k{clip-path:url(#%s)}</style><rect class="k" width="9" height="9"/>', '<g clip-path="url(#%s)"><rect width="9" height="9"/></g>'):
                    clean = _svg.clean_svg(bare('<defs><clipPath id="%s"><rect width="4" height="4"/></clipPath></defs>' % value + use % value))
                    self.assertIn('<clipPath id="%s">' % value, clean.text)
                    self.assertIn('clip-path="url(#%s)"' % value, clean.text)
                    self.assertEqual(_svg.clean_svg(clean.text.encode()).text, clean.text)
                self.assertEqual(_svg._validate("id", value), value)
                # through the door the intake uses
                self.assertEqual(_svg.clean_svg(_input.mark(_input.load(bare(self.CLIP % (value, value)))).colour).colours, ["#000000"])

    def test_a_style_rule_names_an_id_by_the_rule_for_a_css_name_and_not_one_that_starts_with_a_digit(self):
        # `#8c{...}` is no selector to a program: the rule is refused as one this check does not read, and the id itself is fine
        clip = '<clipPath id="8c"><rect width="4" height="4"/></clipPath><rect clip-path="url(#8c)" width="9" height="9"/>'
        for selector in ("#8c", "rect#8c", "#8c.a", ".a#8c", "#-8c", "#1"):
            with self.subTest(selector=selector):
                refused(self, bare("<style>%s{fill:#ff0000}</style>" % selector + clip), "css-unreadable")
        self.assertEqual(_svg.clean_svg(bare("<style>#c8{fill:#ff0000}</style>" + clip)).colours, ["#000000"])
        self.assertEqual(_svg.clean_svg(bare('<style>#c8{fill:#ff0000}</style><rect id="c8" width="9" height="9"/>')).colours, ["#ff0000"])

    def test_what_is_no_id(self):
        # none of these names a clip path: the reference is refused where it stands (as a value this check does not read,
        # or as an address that is no plain #name)
        for value in ("", " ", " a", "a ", "a b", "-a", ".a", ":a", "-1", ".5", "a/b", "a,b", "a;b", "a#b", "#a", "a(b)", "a" * 65, "1" * 65, "Frame 1", "brand/logo/mark", "1 a",
                      "\u0661a", "\uff11a", "\u00e9", "a\u00e9", "Gr\u00f6\u00dfe", "\u65e5\u672c", "a\u0661", "a\u00a0", "a\u200b", "&#9;a", "a&#10;", "a\ufe0f", "a'b", "a&quot;b", "a&lt;b", "a&amp;b",
                      "a\\62", "a%b", "a+b", "a=b", "a@b", "a*b", "a!b"):
            with self.subTest(value=value):
                with self.assertRaises(_svg.Refusal) as cm:
                    _svg.clean_svg(bare(self.CLIP % (value, value)))
                # (`url(#a )` names `a`, which the clip path called `a ` is not)
                self.assertIn(cm.exception.code, ("bad-value", "css-url", "css-unreadable", "clip-target"), str(cm.exception))
                if value not in ("", " "):
                    self.assertIsNotNone(_svg.GRAMMAR["id"](value.replace("&#9;", "\t").replace("&#10;", "\n").replace("&quot;", '"').replace("&lt;", "<").replace("&amp;", "&")))
        # the same names on something no clip path is named by are no business of the grammar: see Ids
        self.assertEqual(_svg.clean_svg(bare('<g id="Frame 1"><rect id="1a" width="9" height="9"/></g>')).notes, [])


class Ids(unittest.TestCase):
    """A REFERENCE FINDS THE SAME ELEMENT IN THE CLEANED FILE AS IN THE FILE THAT CAME. A program looks a clip path up
    by its id and takes the first element that carries it, whatever that element is. Measured 2026-10-13 (the site's
    renderer and Chromium agree): with <title id="c"> before <clipPath id="c"> the file as it came is drawn unclipped,
    and the cleaned file, which leaves the title out, clipped. So an id a clip-path names stands once in the whole
    file, on a clip path; and an id nothing is named by is left out unread."""

    CLIP = '<clipPath id="c"><rect width="4" height="4"/></clipPath>'
    USE = '<rect clip-path="url(#c)" width="9" height="9"/>'

    def test_an_id_that_a_clip_path_is_named_by_stands_once_in_the_whole_file(self):
        rdf = '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description id="c"/></rdf:RDF>'
        for what, doc in (
                ("a title before the clip path", bare('<title id="c">x</title>' + self.CLIP + self.USE)),
                ("a title after it", bare(self.CLIP + self.USE + '<title id="c">x</title>')),
                ("a desc", bare('<desc id="c"/>' + self.CLIP + self.USE)),
                ("the metadata", bare('<metadata id="c"/>' + self.CLIP + self.USE)),
                ("another program's element in the metadata", bare("<metadata>%s</metadata>" % rdf + self.CLIP + self.USE)),
                ("another program's element", bare('<x:note xmlns:x="urn:editor" id="c"/>' + self.CLIP + self.USE)),
                ("an element deep in what is left out", bare('<x:a xmlns:x="urn:editor"><x:b><x:c id="c"/></x:b></x:a>' + self.CLIP + self.USE)),
                ("the outer svg", bare(self.CLIP + self.USE, root='id="c"')),
                ("a group", bare('<g id="c"/>' + self.CLIP + self.USE)),
                ("a shape", bare(self.CLIP + self.USE.replace("<rect ", '<rect id="c" '))),
                ("a style", bare('<style id="c">rect{fill:#111111}</style>' + self.CLIP + self.USE)),
                ("the defs round it", bare('<defs id="c">%s</defs>' % self.CLIP + self.USE)),
                ("a second clip path", bare(self.CLIP + self.CLIP + self.USE)),
                ("a second clip path, empty and first", bare('<clipPath id="c"/>' + self.CLIP + self.USE)),
                ("three of them", bare('<title id="c"/><g id="c"/>' + self.CLIP + self.USE)),
                ("the same id as xml:id", bare('<title xml:id="c">x</title>' + self.CLIP + self.USE)),
                ("a reference from a style attribute", bare('<title id="c"/>' + self.CLIP + '<rect style="clip-path:url(#c)" width="9" height="9"/>')),
                ("a reference from a rule", bare('<title id="c"/><style>.k{clip-path:url( #c )}</style>' + self.CLIP + '<rect class="k" width="9" height="9"/>')),
                ("a reference on a group", bare('<title id="c"/>' + self.CLIP + '<g clip-path="url(#c)"><rect width="9" height="9"/></g>')),
                ("an id that names nothing a style check likes", bare('<title id="c"/>' + self.CLIP + self.USE + '<g id="javascript:logo"/><g id="c"/>'))):
            with self.subTest(what=what):
                err = refused(self, doc, "shared-id")
                for word in ("same id", "'c'", "Ask the tool"):
                    self.assertIn(word, str(err))
        # the control: once, on a clip path, wherever the clip path stands and however the reference is written
        for doc in (bare(self.CLIP + self.USE), bare(self.USE + self.CLIP), bare("<defs>%s</defs>" % self.CLIP + self.USE), bare("<title>c</title><desc>id=\"c\"</desc>" + self.CLIP + self.USE),
                    bare(self.CLIP + '<rect style="clip-path: url( #c )" width="9" height="9"/>'), bare("<style>.k{clip-path:url(#c)}</style>" + self.CLIP + '<rect class="k" width="9" height="9"/>'),
                    bare('<title id="d"/><g id="e"/>' + self.CLIP + self.USE, root='id="f"')):
            with self.subTest(doc=doc[110:170]):
                clean = _svg.clean_svg(doc)
                self.assertEqual(clean.text.count('id="c"'), 1)
                self.assertEqual(clean.text.count(' id='), 1, "and no other id is written")
                self.assertIn('clip-path="url(#c)"', clean.text)

    def test_what_a_shape_is_clipped_by_is_a_clip_path_in_the_file(self):
        for what, doc in (("nothing in the file", bare(self.USE)), ("nothing: another name", bare(self.CLIP.replace('"c"', '"d"') + self.USE)),
                          ("a group", bare('<g id="c"><rect width="4" height="4"/></g>' + self.USE)), ("a shape", bare('<rect id="c" width="4" height="4"/>' + self.USE)),
                          ("itself", bare(self.USE.replace("<rect ", '<rect id="c" '))), ("a title", bare('<title id="c">x</title>' + self.USE)),
                          ("the outer svg", bare(self.USE, root='id="c"')), ("another program's element", bare('<x:clipPath xmlns:x="urn:editor" id="c"/>' + self.USE)),
                          ("a clip path named in other letters", bare(self.CLIP.replace('"c"', '"C"') + self.USE)), ("a clip path with a blank in its id", bare(self.CLIP.replace('"c"', '" c"') + self.USE)),
                          ("a clip path with an xml:id only", bare(self.CLIP.replace(" id=", " xml:id=") + self.USE)),
                          ("a clip path with a prefixed id only", bare(self.CLIP.replace(" id=", " x:id=").replace("<clipPath ", '<clipPath xmlns:x="urn:editor" ') + self.USE))):
            with self.subTest(what=what):
                err = refused(self, doc, "clip-target")
                for word in ("not a clip path", "url(#c)", "Ask the tool"):
                    self.assertIn(word, str(err))
        # a reference that no element ends up with is not followed, so nothing is asked of its name
        clean = _svg.clean_svg(bare("<style>.unused{clip-path:url(#nobody)} .r{clip-path:url(#nobody)}</style>" + self.CLIP
                                    + '<rect class="r" style="clip-path:url(#c)" width="9" height="9"/><rect class="r" clip-path="url(#gone)" style="clip-path:none" width="9" height="9"/>'))
        self.assertNotIn("nobody", clean.text)
        self.assertNotIn("gone", clean.text)

    def test_an_id_nothing_is_named_by_is_left_out_whatever_it_is_written_in(self):
        # ordinary exports were refused for an id nobody uses: a layer called "Frame 1" or "Größe", an id that starts with a digit
        for value in ("Frame 1", "Rectangle 1", "Gr\u00f6\u00dfe", "\u65e5\u672c\u8a9e", "brand/logo/mark", "1a2b3c4d5e", "8ce47d5fb1", "icon/logo", "Layer-1", "a" * 300, "", " ",
                      "a b c", "&#9;x&#10;", "x\u00a0y", "\u200b", "a&amp;b", "a&lt;b&gt;", "a'b", "#a", "url", "none", "c",
                      # nor is it read as a piece of a style: a layer may be called any of these (each refused the drawing until 2026-10-13)
                      "expression(layer)", "javascript:logo", "JavaScript: the logo", "url(https://x.example/a)", "url(logo.png)", "@import a", "image(x)", "src(x)", "behavior: none",
                      "-moz-binding", "a\\62 c", "/* layer */", "a{b}", "x(", "&quot;", "[1]"):
            with self.subTest(value=ascii(value)):
                for doc in (bare('<g id="%s"><rect id="%s" width="9" height="9" fill="#111111"/></g>' % (value, value)), svg(root='id="%s"' % value),
                            bare('<title id="%s">x</title><defs id="%s"/><rect width="9" height="9" fill="#111111"/>' % (value, value)),
                            bare('<clipPath id="%s"><rect width="4" height="4"/></clipPath><rect width="9" height="9" fill="#111111"/>' % value)):
                    clean = _svg.clean_svg(doc.decode().encode("utf-8"))
                    self.assertNotIn(" id=", clean.text)
                    self.assertEqual(clean.notes, [])
        # the same words where they ARE a piece of a style are refused as before: an id is not read, a style is
        refused(self, bare('<rect id="a" style="fill:url(https://x.example/a)" width="9" height="9"/>'), "css-url")
        refused(self, bare('<rect id="a" fill="expression(layer)" width="9" height="9"/>'), "css-script")
        # through the door the intake uses, as a file and inside a package
        doc = bare('<g id="javascript:logo"><rect id="expression(layer)" width="9" height="9" fill="#111111"/></g>')
        self.assertEqual(_svg.clean_svg(_input.mark(_input.load(doc)).colour).text.count(" id="), 0)
        self.assertEqual(_svg.clean_svg(_input.mark(_input.load(T.build_zip([("logo.svg", doc)]))).colour).colours, ["#111111"])

    def test_an_id_that_is_left_out_is_still_the_id_a_style_rule_names_and_still_counts_as_standing_there(self):
        # a rule that names an id applies before the id is left out: red in the file that came, red in the cleaned file
        for name in ("layer-1", "a", "_a", "Layer_1"):
            with self.subTest(name=name):
                clean = _svg.clean_svg(bare('<style>#%s{fill:#ff0000}</style><g id="expression(layer)"><rect id="%s" width="9" height="9"/></g>' % (name, name)))
                self.assertEqual(clean.colours, ["#ff0000"])
                self.assertIn('fill="#ff0000"', clean.text)
                self.assertNotIn(" id=", clean.text)
        # and an id nothing refers to still counts where something does refer to it: twice in the file is twice
        refused(self, bare('<g id="c"/>' + self.CLIP + self.USE), "shared-id")
        self.assertEqual(_svg.clean_svg(bare('<g id="c"/><g id="c"/><g id="javascript:c"/>' + self.CLIP.replace('"c"', '"d"') + self.USE.replace("#c", "#d"))).text.count(" id="), 1)

    def test_a_paint_that_names_an_id_is_refused_wherever_it_reaches_an_element_so_no_kept_reference_loses_its_id(self):
        # The value grammar takes `url(#id)` in fill, stroke and color, and every id but a clip path's is left out. No
        # cleaned file holds such a paint all the same: the colour reader refuses it by name (a gradient or a pattern)
        # on whatever element it ends up, drawn or not, before anything is written.
        path = '<path fill="#111111" d="M0 0h9v9z"/>'
        for what, inner in (("fill on a shape, the id a clip path's", self.CLIP + '<rect fill="url(#c)" width="9" height="9"/>'),
                            ("stroke on a shape, the id a group's", '<g id="g"/><rect stroke="url(#g)" width="9" height="9"/>'),
                            ("stroke on a shape, the id nowhere", '<rect stroke="url( #nowhere )" width="9" height="9"/>'),
                            ("color", '<rect color="url(#c)" fill="#111111" width="9" height="9"/>' + self.CLIP),
                            ("an id that starts with a digit", '<clipPath id="8c"/><rect fill="url(#8c)" width="9" height="9"/>'),
                            ("on an empty group", '<g fill="url(#c)"/>' + self.CLIP + path), ("on a group round a shape with a fill of its own", '<g fill="url(#c)">%s</g>' % path + self.CLIP),
                            ("on a shape in defs", '<defs><rect fill="url(#c)" width="9" height="9"/></defs>' + self.CLIP + path),
                            ("on a shape inside a clip path", '<clipPath id="k"><rect fill="url(#c)" width="9" height="9"/></clipPath>' + self.CLIP + path),
                            ("on a shape that is not shown", '<rect display="none" fill="url(#c)" width="9" height="9"/>' + self.CLIP + path),
                            ("on the clip path itself", self.CLIP.replace("<clipPath ", '<clipPath stroke="url(#c)" ') + path),
                            ("in a style", '<rect style="fill:url(#c)" width="9" height="9"/>' + self.CLIP), ("by a rule", "<style>rect{stroke:url(#c)}</style>" + self.USE + self.CLIP),
                            ("an outline of no width", '<rect stroke="url(#c)" stroke-width="0" fill="#111111" width="9" height="9"/>' + self.CLIP)):
            with self.subTest(what=what):
                err = refused(self, bare(inner), "colour-gradient")
                self.assertIn("ask the tool", str(err))
        refused(self, bare(self.CLIP + path, root='fill="url(#c)"'), "colour-gradient")
        # a rule that no element ends up with is not written, so its paint is nowhere in the cleaned file
        clean = _svg.clean_svg(bare("<style>.unused{fill:url(#c)}</style>" + self.CLIP + self.USE + path))
        self.assertNotIn("fill=\"url(", clean.text)
        self.assertEqual(clean.text.count("url(#"), 1, "the one reference a cleaned file holds is a clip path's")
        # through the door the intake uses
        self.assertEqual(refused(self, _input.mark(_input.load(bare(self.CLIP + '<rect fill="url(#c)" width="9" height="9"/>'))).colour, "colour-gradient").code, "colour-gradient")

    def test_a_clip_path_nothing_refers_to_keeps_no_id_and_one_that_is_referred_to_keeps_its_own(self):
        clean = _svg.clean_svg(bare('<clipPath id="unused 1"><rect width="4" height="4"/></clipPath><clipPath id="used"><rect width="4" height="4"/></clipPath>'
                                    '<clipPath id="also"><rect width="4" height="4"/></clipPath><g id="used too" clip-path="url(#used)"><rect id="r" clip-path="url( #also )" width="9" height="9"/></g>'))
        self.assertEqual(re.findall(r'<(\w+) id="([^"]*)"', clean.text), [("clipPath", "used"), ("clipPath", "also")])
        self.assertEqual(_svg.clean_svg(clean.text.encode()).text, clean.text)

    def test_the_intake_refuses_a_shared_id_as_the_check_does(self):
        # through the door production uses: what the bytes are, the mark, the check
        doc = bare('<title id="c">x</title>' + self.CLIP + self.USE)
        with self.assertRaises(_svg.Refusal) as cm:
            _svg.clean_svg(_input.mark(_input.load(doc)).colour)
        self.assertEqual(cm.exception.code, "shared-id")
        package = T.build_zip([("pack/logo.svg", doc)])
        with self.assertRaises(_svg.Refusal) as cm:
            _svg.clean_svg(_input.mark(_input.load(package)).colour)
        self.assertEqual(cm.exception.code, "shared-id")
        self.assertEqual(_svg.clean_svg(_input.mark(_input.load(bare('<g id="Frame 1">' + self.CLIP + self.USE + "</g>"))).colour).colours, ["#000000"])


class APlainClipPath(unittest.TestCase):
    """A CLIP PATH IS A PLAIN OUTLINE THAT CLIPS SHAPES. What goes beyond that is refused by name, however it is set,
    because programs do not draw it alike (measured 2026-10-13, the site's renderer against a browser; the pictures are
    in test_render.py): a clip-path on a <clipPath> or on anything inside one, display on a <clipPath> or a <defs>, and
    a clip-path on the outer <svg>."""

    CLIP = '<clipPath id="c"><rect width="4" height="4"/></clipPath>'
    OTHER = '<clipPath id="d"><rect width="6" height="6"/><circle cx="3" cy="3" r="2"/></clipPath>'
    USE = '<rect clip-path="url(#c)" width="9" height="9"/>'

    def test_a_clip_path_is_not_clipped_and_nothing_inside_one_is_however_that_is_set(self):
        inner = '<clipPath id="c"%s><rect%s width="4" height="4"/><circle%s r="2"/></clipPath>'
        ways = {
            "an attribute on the clip path": inner % (' clip-path="url(#d)"', "", ""),
            "a style on the clip path": inner % (' style="clip-path:url(#d)"', "", ""),
            "an attribute on a shape inside": inner % ("", ' clip-path="url(#d)"', ""),
            "a style on a shape inside": inner % ("", "", ' style="fill:#111111;clip-path: url( #d )"'),
            "a rule for clip paths": "<style>clipPath{clip-path:url(#d)}</style>" + inner % ("", "", ""),
            "a rule for the clip path's id": "<style>#c{clip-path:url(#d)}</style>" + inner % ("", "", ""),
            "a rule for a class on a shape inside": "<style>.k{clip-path:url(#d)}</style>" + inner % ("", ' class="k"', ""),
            "a rule for every circle": "<style>circle{clip-path:url(#c)}</style>" + inner % ("", "", ""),
            "a rule for every rect, which the clip path's own shape is": "<style>rect{clip-path:url(#c)}</style>" + inner % ("", "", ""),
            "a rule for everything but the outer svg": "<style>g,defs,clipPath,rect,circle{clip-path:url(#d)}</style>" + inner % ("", "", ""),
            "a group inside the clip path": '<clipPath id="c"><g clip-path="url(#d)"><rect width="4" height="4"/></g></clipPath>',
            "a shape in a group inside the clip path": '<clipPath id="c"><g><g><rect clip-path="url(#d)" width="4" height="4"/></g></g></clipPath>',
            "a clip path inside a clip path": '<clipPath id="c"><clipPath id="e" clip-path="url(#d)"/><rect width="4" height="4"/></clipPath>',
            "by itself": inner % (' clip-path="url(#c)"', "", ""),
            "a shape inside by the clip path it stands in": inner % ("", ' clip-path="url(#c)"', ""),
            "a clip path nothing is clipped by": '<clipPath id="unused" clip-path="url(#d)"><rect width="4" height="4"/></clipPath>' + self.CLIP,
            "an empty clip path": '<clipPath id="e" clip-path="url(#d)"/>' + self.CLIP,
            "by something that is not in the file": inner % (' clip-path="url(#nowhere)"', "", ""),
            "an id that starts with a digit": inner.replace('"c"', '"8c"') % ("", ' clip-path="url(#d)"', "") + self.CLIP,
        }
        for what, clip in ways.items():
            for doc in (bare(clip + self.OTHER + self.USE), bare("<defs>%s%s</defs>" % (self.OTHER, clip) + self.USE), bare(self.USE + "<g><defs>%s</defs></g>" % (clip + self.OTHER))):
                with self.subTest(what=what, doc=doc[110:150]):
                    err = refused(self, doc, "clip-in-clip")
                    for word in ("clip path", "clipped itself", "clip-path='url(#", "different ways", "Ask the tool", "one plain outline"):
                        self.assertIn(word, str(err))
        # two that clip each other, with a tail leading in; and a chain, each link holding two shapes clipped by the next
        ring = ('<clipPath id="a" clip-path="url(#b)"><rect width="9" height="9"/></clipPath><clipPath id="b" clip-path="url(#a)"><rect width="6" height="6"/></clipPath>'
                '<clipPath id="c" clip-path="url(#a)"><rect width="4" height="4"/></clipPath>')
        refused(self, bare(ring + self.USE), "clip-in-clip")
        chain = "".join('<clipPath id="k%d"><rect clip-path="url(#k%d)" width="9" height="9"/><rect clip-path="url(#k%d)" width="8" height="8"/></clipPath>' % (i, i + 1, i + 1) for i in range(22))
        refused(self, bare(chain + '<clipPath id="k22"><rect width="4" height="4"/></clipPath><rect clip-path="url(#k0)" width="9" height="9"/>'), "clip-in-clip")
        # through the door the intake uses, as a file and inside a package
        doc = bare(ways["an attribute on a shape inside"] + self.OTHER + self.USE)
        self.assertEqual(refused(self, _input.mark(_input.load(doc)).colour, "clip-in-clip").code, "clip-in-clip")
        self.assertEqual(refused(self, _input.mark(_input.load(T.build_zip([("pack/logo.svg", doc)]))).colour, "clip-in-clip").code, "clip-in-clip")

    def test_a_plain_clip_path_is_kept_whatever_plain_shapes_it_holds_and_wherever_it_stands(self):
        for what, doc in (
                ("one shape", bare(self.CLIP + self.USE)),
                ("several plain shapes", bare(self.OTHER + self.USE.replace("#c", "#d"))),
                ("a transformed clip path", bare(self.CLIP.replace("<clipPath ", '<clipPath transform="translate(2 0) scale(1 .5)" ') + self.USE)),
                ("a transformed shape inside", bare(self.CLIP.replace("<rect ", '<rect transform="rotate(20 5 5)" ') + self.USE)),
                ("used by two shapes and a group", bare(self.CLIP + self.USE + self.USE + '<g clip-path="url(#c)"><rect width="9" height="2"/></g>')),
                ("two clip paths, one for a group and one for a shape in it", bare(self.CLIP + self.OTHER + '<g clip-path="url(#d)">%s</g>' % self.USE)),
                ("a clip path that stands in a clipped group", bare(self.OTHER + '<g clip-path="url(#d)">%s%s</g>' % (self.CLIP, self.USE))),
                ("in defs in a clipped group", bare(self.OTHER + '<g clip-path="url(#d)"><defs>%s</defs>%s</g>' % (self.CLIP, self.USE))),
                ("clip-path none on the clip path", bare(self.CLIP.replace("<clipPath ", '<clipPath clip-path="none" ') + self.USE)),
                ("clip-path none on a shape inside", bare(self.CLIP.replace("<rect ", '<rect style="clip-path:none" ') + self.USE)),
                ("a rule that sets none everywhere", bare("<style>*{clip-path:none}</style>" + self.CLIP + '<rect style="clip-path:url(#c)" width="9" height="9"/>')),
                ("a rule for clip paths that a later one takes back", bare("<style>clipPath{clip-path:url(#d)} #c{clip-path:none}</style>" + self.CLIP + self.USE)),
                ("a group that is not shown round the clip path", bare('<g display="none">%s</g>' % self.CLIP + self.USE)),
                ("a group that is not shown round its defs", bare('<g display="none"><defs>%s</defs></g>' % self.CLIP + self.USE)),
                ("clip-path none on the outer svg", bare(self.CLIP + self.USE, root='clip-path="none"'))):
            with self.subTest(what=what):
                clean = _svg.clean_svg(doc)
                self.assertIn(' clip-path="url(#', clean.text)
                self.assertEqual(_svg.clean_svg(clean.text.encode()).text, clean.text)

    def test_display_is_not_set_on_a_clip_path_or_on_defs_however_that_is_set(self):
        for value in ("none", "inline", "block"):
            for what, inner in (
                    ("an attribute on the clip path", self.CLIP.replace("<clipPath ", '<clipPath display="%s" ' % value) + self.USE),
                    ("a style on the clip path", self.CLIP.replace("<clipPath ", '<clipPath style="display: %s" ' % value) + self.USE),
                    ("a rule for clip paths", "<style>clipPath{display:%s}</style>" % value + self.CLIP + self.USE),
                    ("a rule for the clip path's id", "<style>#c{display:%s}</style>" % value + self.CLIP + self.USE),
                    ("a rule for everything", "<style>*{display:%s}</style>" % value + self.CLIP + self.USE),
                    ("a clip path nothing is clipped by", '<clipPath id="unused" display="%s"/>' % value + self.CLIP + self.USE),
                    ("an attribute on the defs round it", '<defs display="%s">%s</defs>' % (value, self.CLIP) + self.USE),
                    ("a style on the defs", '<defs style="display:%s">%s</defs>' % (value, self.CLIP) + self.USE),
                    ("a rule for defs", "<style>defs{display:%s}</style><defs>%s</defs>" % (value, self.CLIP) + self.USE),
                    ("defs that hold no clip path", '<defs display="%s"><rect width="4" height="4"/></defs>' % value + self.CLIP + self.USE),
                    ("empty defs, in a group", '<g><defs display="%s"/></g>' % value + self.CLIP + self.USE)):
                with self.subTest(value=value, what=what):
                    err = refused(self, bare(inner), "clip-display")
                    for word in ("display (%r)" % value, "does not clip at all", "Ask the tool", "<defs>"):
                        self.assertIn(word, str(err))
        # display anywhere else is read as before: on a group round a clip path, on a shape, on a shape inside a clip path
        for inner in ('<g display="none">%s</g>' % self.CLIP + self.USE, '<g style="display:inline"><defs>%s</defs></g>' % self.CLIP + self.USE, self.CLIP + self.USE.replace("<rect ", '<rect display="block" '),
                      "<style>g,rect{display:inline}</style><g>%s</g>" % self.CLIP + self.USE, self.CLIP.replace("<rect ", '<rect display="none" ') + self.USE):
            with self.subTest(inner=inner[:50]):
                self.assertIn('clip-path="url(#c)"', _svg.clean_svg(bare(inner)).text)
        # through the door the intake uses, as a file and inside a package
        doc = bare('<defs style="display:none">%s</defs>' % self.CLIP + self.USE)
        self.assertEqual(refused(self, _input.mark(_input.load(doc)).colour, "clip-display").code, "clip-display")
        self.assertEqual(refused(self, _input.mark(_input.load(T.build_zip([("logo.svg", doc)]))).colour, "clip-display").code, "clip-display")

    def test_the_outer_svg_is_not_clipped_however_that_is_set(self):
        shape = '<rect width="9" height="9"/>'
        for what, doc in (("an attribute", bare(self.CLIP + shape, root='clip-path="url(#c)"')), ("an attribute, spaced", bare(self.CLIP + shape, root='clip-path=" url( #c ) "')),
                          ("a style", bare(self.CLIP + shape, root='style="clip-path:url(#c)"')), ("a rule for svg", bare("<style>svg{clip-path:url(#c)}</style>" + self.CLIP + shape)),
                          ("a rule for everything", bare("<style>*{clip-path:url(#c)}</style>" + self.CLIP + shape)), ("a rule for its class", bare("<style>.k{clip-path:url(#c)}</style>" + self.CLIP + shape, root='class="k"')),
                          ("a rule for its id", bare("<style>#logo{clip-path:url(#c)}</style>" + self.CLIP + shape, root='id="logo"')),
                          ("by something that is not in the file", bare(shape, root='clip-path="url(#nowhere)"')), ("by an id that stands twice", bare('<title id="c"/>' + self.CLIP + shape, root='clip-path="url(#c)"')),
                          ("an id that starts with a digit", bare(self.CLIP.replace('"c"', '"8c"') + shape, root='clip-path="url(#8c)"'))):
            with self.subTest(what=what):
                err = refused(self, doc, "root-clip-path")
                for word in ("outer <svg>", "clip-path='url(#", "picture's pixels", "a small icon and in a large one", "Ask the tool", "group round the shapes"):
                    self.assertIn(word, str(err))
        # the same clip on a group round the shapes is what the sentence asks for, and is read
        self.assertIn('<g clip-path="url(#c)">', _svg.clean_svg(bare(self.CLIP + '<g clip-path="url(#c)">%s</g>' % shape)).text)
        self.assertEqual(_svg.clean_svg(bare(shape, root='clip-path=" none "')).colours, ["#000000"])   # `none` clips nothing, there as anywhere
        # through the door the intake uses, as a file and inside a package
        doc = bare(self.CLIP + shape, root='clip-path="url(#c)"')
        self.assertEqual(refused(self, _input.mark(_input.load(doc)).colour, "root-clip-path").code, "root-clip-path")
        self.assertEqual(refused(self, _input.mark(_input.load(T.build_zip([("logo.svg", doc)]))).colour, "root-clip-path").code, "root-clip-path")


class ClipWork(unittest.TestCase):
    """CLIP PATHS DO NOT HOLD SO MUCH, FOR HOW OFTEN THEY ARE USED, THAT A BROWSER HAS FAR MORE WORK THAN A LOGO GIVES IT.
    A browser's work grows with (the elements clipped by a clip path) times (what the clip path holds), a browser has
    no time limit, and the cleaned file is the site's favicon.svg. Measured 2026-10-13 in Chromium at 512 pixels: 11.9
    seconds for 4,900 shapes clipped by one path of 400 turns, a file inside every other cap. So that product is
    counted, by the numbers the clip path's shapes hold, summed over the file, and capped at MAX_CLIP_WORK. It is a
    count, and what is held here is the count: it is no bound on a browser's time (the top of _svg.py says what a
    file just under it took one)."""

    USE = '<rect clip-path="url(#c)" width="9" height="9"/>'

    @staticmethod
    def polygon(numbers, name="c"):
        return '<clipPath id="%s"><polygon points="%s"/></clipPath>' % (name, "1 2 " * (numbers // 2))

    def at_the_cap_and_one_step_over(self, what, at, over):
        with self.subTest(what=what):
            self.assertIn(' clip-path="url(#', _svg.clean_svg(bare(at)).text)
            err = refused(self, bare(over), "clip-work")
            for said in ("clip paths", "so often", "hold so much", "far more work for a browser than a logo is", "{:,}".format(_svg.MAX_CLIP_WORK), "Ask the tool", "clips applied to the shapes"):
                self.assertIn(said, str(err))

    def test_the_numbers_of_each_clip_path_times_the_elements_it_clips_come_to_no_more_than_the_cap(self):
        self.assertEqual(_svg.MAX_CLIP_WORK, 200000)
        both = self.at_the_cap_and_one_step_over
        # one clip path of 2,000 numbers, used by 100 shapes; one of 40 numbers, used by 5,000 less the few elements round them
        both("many numbers, a hundred uses", self.polygon(2000) + self.USE * 100, self.polygon(2000) + self.USE * 101)
        both("a few numbers, thousands of uses", self.polygon(40) + self.USE * 4990, self.polygon(42) + self.USE * 4990)
        # what is counted: the numbers of path data (an arc's flags are no numbers), of points, and one for each other number that places or sizes a shape
        path = '<clipPath id="c"><path d="M0 0%s"/></clipPath>'
        both("the numbers of path data", path % ("L1 1" * 999) + self.USE * 100, path % ("L1 1" * 1000) + self.USE * 100)
        both("an arc's flags are no numbers", path % ("a5 5 0 1 1 1 1" * 399 + "h1h1h1") + self.USE * 100, path % ("a5 5 0 1 1 1 1" * 399 + "h1h1h1h1") + self.USE * 100)
        shapes = '<clipPath id="c">%s</clipPath>'
        both("a rect of four numbers", shapes % ('<rect x="1" y="1" width="4" height="4"/>' * 20) + self.USE * 2500, shapes % ('<rect x="1" y="1" width="4" height="4"/>' * 20) + self.USE * 2501)
        # a circle of three numbers, a line of four, an ellipse of four, a rect of two, a polyline of eight: 21, forty times over
        mixed = shapes % ('<circle cx="1" cy="1" r="1"/><line x1="1" y1="1" x2="2" y2="2"/><ellipse cx="1" cy="1" rx="2" ry="1"/><rect width="9" height="9"/><polyline points="1 1 2 2 3 3 4 4"/>' * 40)
        both("every kind of shape, by its own numbers", mixed + self.USE * 238, mixed + self.USE * 239)
        # a transform is no number of a shape; a shape inside a group inside the clip path is one of its shapes
        both("a transform's numbers are not counted, a shape in a group is", '<clipPath id="c" transform="matrix(1 0 0 1 2 3)"><g><polygon transform="matrix(1 0 0 1 2 3)" points="%s"/></g></clipPath>' % ("1 2 " * 1000)
             + self.USE * 100, '<clipPath id="c"><g><polygon points="%s"/></g></clipPath>' % ("1 2 " * 1000) + self.USE * 101)
        # every element clipped by it is one use, however the clip is set: an attribute, a style, a rule; a group is one use, whatever it holds
        clip = self.polygon(2000)
        both("set by a style", clip + '<rect style="clip-path:url(#c)" width="9" height="9"/>' * 100, clip + '<rect style="clip-path: url( #c )" width="9" height="9"/>' * 101)
        both("set by a rule", "<style>.k{clip-path:url(#c)}</style>" + clip + '<rect class="k" width="9" height="9"/>' * 100, "<style>.k{clip-path:url(#c)}</style>" + clip + '<rect class="k" width="9" height="9"/>' * 101)
        both("set by a rule for every rect", "<style>rect{clip-path:url(#c)}</style>" + clip + '<rect width="9" height="9"/>' * 100, "<style>rect{clip-path:url(#c)}</style>" + clip + '<rect width="9" height="9"/>' * 101)
        both("groups, each one use whatever it holds", clip + ('<g clip-path="url(#c)">%s</g>' % ('<rect width="9" height="9"/>' * 20)) * 100, clip + ('<g clip-path="url(#c)"><rect width="9" height="9"/></g>') * 101)
        both("a group and the shapes in it", clip + '<g clip-path="url(#c)">%s</g>' % (self.USE * 99), clip + '<g clip-path="url(#c)">%s</g>' % (self.USE * 100))
        both("shapes that are not shown are uses too", clip + self.USE * 99 + self.USE.replace("<rect ", '<rect display="none" '), clip + self.USE * 100 + self.USE.replace("<rect ", '<rect display="none" '))
        # summed over the file: many clip paths, each used once; two, each used fifty times
        both("a hundred clip paths", "".join(self.polygon(2000, "c%d" % i) + self.USE.replace("#c", "#c%d" % i) for i in range(100)),
             "".join(self.polygon(2000, "c%d" % i) + self.USE.replace("#c", "#c%d" % i) for i in range(101)))
        both("two clip paths", self.polygon(2000) + self.polygon(2000, "d") + (self.USE + self.USE.replace("#c", "#d")) * 50, self.polygon(2000) + self.polygon(2000, "d") + (self.USE + self.USE.replace("#c", "#d")) * 50 + self.USE)

    def test_a_clip_path_nothing_is_clipped_by_costs_nothing_and_ordinary_files_are_far_from_the_cap(self):
        unused = "".join(self.polygon(2000, "u%d" % i) for i in range(40))
        self.assertEqual(_svg.clean_svg(bare(unused + '<rect width="9" height="9" fill="#111111"/>')).colours, ["#111111"])
        self.assertIn('clip-path="url(#c)"', _svg.clean_svg(bare(unused + self.polygon(2000) + self.USE * 100)).text)
        # what exports hold: a frame clipped once by a rect; an icon set, every icon clipped by its own small frame
        frame = '<clipPath id="c"><rect width="64" height="64" rx="8"/></clipPath><g clip-path="url(#c)">%s</g>' % ('<path d="M1 1h9v9z"/>' * 200)
        icons = "".join('<clipPath id="i%d"><path d="M0 0h24v24H0z"/></clipPath><g clip-path="url(#i%d)"><path d="M1 1h9v9z"/></g>' % (i, i) for i in range(1000))
        for doc in (frame, icons):
            self.assertIn(" clip-path=", _svg.clean_svg(bare(doc)).text)

    def test_the_largest_files_at_the_cap_are_judged_in_bounded_time_through_the_door_the_intake_uses(self):
        docs = [bare(self.polygon(2000) + self.USE * 100), bare(self.polygon(2000) + self.USE * 101), bare(self.polygon(40) + self.USE * 4990), bare(self.polygon(42) + self.USE * 4990),
                bare("".join(self.polygon(2000, "c%d" % i) + self.USE.replace("#c", "#c%d" % i) for i in range(101)))]
        got = [out["code"] for out in judged(self, docs, how="intake", each=5.0)]
        self.assertEqual(got, ["ok", "clip-work", "ok", "clip-work", "clip-work"])
        err = refused(self, _input.mark(_input.load(T.build_zip([("pack/logo.svg", docs[1])]))).colour, "clip-work")
        self.assertTrue(str(err).startswith("In the package, the file 'pack/logo.svg': The file uses its clip paths so often"), str(err))
        self.assertIn("come to 202,000;", str(err))   # 2,000 numbers, 101 times: the sentence says what was counted


class AClass(Line):
    """class: names of visible ASCII characters with spaces between them; 200 characters at most. A name a style rule
    can name (letters, digits, `_ -`, begun as a CSS name is) is read for the rules; any other is passed over. Never written."""

    def test_what_it_takes(self):
        for value, names in (("a", {"a"}), ("a b", {"a", "b"}), (" a  b ", {"a", "b"}), ("cls-1 st0", {"cls-1", "st0"}), ("a.b _c -d 0", {"_c", "-d"}),
                             ("", set()), (" ", set()), ("a a", {"a"}), ("x" * 200, {"x" * 200}), (" ".join(["ab"] * 66), {"ab"})):
            with self.subTest(value=value):
                clean = _svg.clean_svg(bare("<style>.a{fill:#ff0000}</style>" + '<rect class="%s" width="9" height="9"/>' % value))
                self.assertEqual(clean.colours, ["#ff0000"] if "a" in names else ["#000000"])
                self.assertNotIn("class", clean.text)
                self.assertEqual(_svg._classes(_svg._validate("class", value)), names)

    def test_a_name_no_style_rule_can_name_is_passed_over(self):
        # A pasted icon carries the names of a style library (`h-6 w-6 md:h-8 hover:text-gray-500`): the drawing was refused
        # for the colon. No selector this check reads can name such a class, and a class is never written.
        odd = ("md:h-8", "hover:text-gray-500", "w-1/2", "top-0.5", "!mt-0", "[&amp;&gt;path]:fill-current", "text-[#b4531a]", "bg-[url(/hero.png)]", "sm:max-w-[200px]",
               "a,b", "a;b", "a#b", "#a", ".a", "a.b", "a(b)", "a'b", "a&quot;b", "a&lt;b", "a*", "a+b", "a%", "a\\62", "a!", "a@b", "a=b", "0", "1a", "-", "--", "-1", "a{b}",
               "javascript:a", "expression(a)", "@import")
        sheet = "<style>.a{fill:#ff0000} .b{stroke:#00ff00} .md{fill:#0000ff} .h-8{fill:#0000ff} .hover{fill:#0000ff} .w-1{fill:#0000ff} .mt-0{fill:#0000ff}</style>"
        for name in odd:
            with self.subTest(name=name):
                for value, colours in ((name, ["#000000"]), ("a " + name, ["#ff0000"]), (name + " a", ["#ff0000"]), ("%s a %s" % (name, name), ["#ff0000"]), ("%s  %s" % (name, name), ["#000000"])):
                    clean = _svg.clean_svg(bare(sheet + '<rect class="%s" width="9" height="9"/>' % value))
                    self.assertEqual(clean.colours, colours, value)
                    self.assertEqual(clean.notes, [])
                    self.assertNotIn("class", clean.text)
        clean = _svg.clean_svg(bare(sheet + '<rect class="%s" width="9" height="9"/>' % "h-6 w-6 md:h-8 hover:text-gray-500 a", root='class="h-6 w-6 md:h-8 hover:text-gray-500"'))
        self.assertEqual(clean.colours, ["#ff0000"])
        self.assertEqual(_svg._classes("a md:h-8 b.c -d  _e 0 a"), {"a", "-d", "_e"})
        # a rule cannot name one of them: written so that a browser would, it is a selector this check does not read
        for selector in (".md\\:h-8", ".w-1\\/2", ".\\31 a", ".0", ".a\\.b"):
            with self.subTest(selector=selector):
                refused(self, bare("<style>%s{fill:#ff0000}</style>" % selector + '<rect class="md:h-8" width="9" height="9"/>'), "css-unreadable")
        # through the door the intake uses, as a file and inside a package
        doc = ('<svg %s class="h-6 w-6 md:h-8 hover:text-gray-500" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="#111111">'
               '<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15"/></svg>' % NS).encode()
        self.assertEqual(_svg.clean_svg(_input.mark(_input.load(doc)).colour).colours, ["#111111"])
        self.assertEqual(_svg.clean_svg(_input.mark(_input.load(T.build_zip([("icon.svg", doc)]))).colour).colours, ["#111111"])

    def test_what_is_no_class(self):
        # a name with anything in it that one program may take for a blank and another for a letter, or that is not ASCII
        for value in ("x" * 201, "a:b " * 50 + "c", "a&#9;b", "a&#10;b", "a&#13;b", "a\u00a0b", "\u2003a", "\u00e9", "gr\u00f6\u00dfe", "a\u0661", "a\u200bb", "a\ufe0f", "a&#127;b",
                      "md:h-8\u00a0a", "a\u3000b", "a\u2028b"):
            with self.subTest(value=ascii(value)):
                refused(self, bare("<style>.a{fill:#ff0000}</style>" + '<rect class="%s" width="9" height="9"/>' % value), "bad-value")


class AClipPath(Line):
    """clip-path: `none`, or url(#id) with an id of the grammar, 80 characters at most; blanks may stand inside the brackets."""

    CLIP = ('<defs><clipPath id="c"><rect width="4" height="4"/></clipPath><clipPath id="a-b.c:d_e"><rect width="4" height="4"/></clipPath>'
            '<clipPath id="1c"><rect width="4" height="4"/></clipPath><clipPath id="8ce47d5fb1"><rect width="4" height="4"/></clipPath>'
            '<clipPath id="%s"><rect width="4" height="4"/></clipPath></defs>' % ("a" * 64))

    def places(self, name, value, **where):
        # (the rule names the shape by a class: one for every <rect> would clip the shapes inside the clip paths too)
        escaped = value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
        docs = [bare(self.CLIP + '<rect clip-path="%s" width="9" height="9"/>' % escaped), bare(self.CLIP + '<rect style="clip-path:%s" width="9" height="9"/>' % escaped)]
        return docs + [bare(self.CLIP + "<style>.k{clip-path:%s}</style><rect class='k' width='9' height='9'/>" % escaped.replace("&quot;", '"'))]

    def test_what_it_takes(self):
        self.takes("clip-path", ["none", " none ", "url(#c)", ("url( #c )", "url(#c)"), ("url(\t#c\n)", "url(#c)"), (" url(#c) ", "url(#c)"), "url(#a-b.c:d_e)", "url(#" + "a" * 64 + ")",
                                 "url(#1c)", "url(#8ce47d5fb1)", ("url( #8ce47d5fb1 )", "url(#8ce47d5fb1)")])

    def test_what_is_no_clip_path(self):
        self.turns_down("clip-path", ["None", "NONE", "auto", "inherit", "#c", "c", "URL(#c)", "Url(#c)", "url (#c)", "url(#c) none", "none url(#c)", "url(#c) url(#c)",
                                      "url(#c)x", "url(#-c)", "url(#.c)", "url(#:c)", "url(#" + "a" * 65 + ")", "url(#c" + " " * 80 + ")", "circle(5)", "inset(1)",
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

    DOC = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s"><path fill="#111111" d="M0 0h.009v.009z"/></svg>'

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
                      "(0 0 10 20)", "0 0 10 20 ,", "0 0 0.009 0.009", "0 0 1000001 1000001", "0 0 10 201", "0 0 201 10", "1000001 0 10 20", "0 -1e7 10 20", "0 0 1e10 1e10", "0 0 9e99 9e99"):
            with self.subTest(value=ascii(value)):
                refused(self, (self.DOC % value).encode("utf-8"), "bad-view-box")
        # a number longer than a number may be is refused as that, as it is in every other value (it was called "not four numbers")
        for value in ("0 0 " + "0" * 64 + "9 9", "0" * 65 + " 0 9 9", "0 0 9 9." + "0" * 63, "+" + "0" * 64 + ",0,9,9"):
            with self.subTest(value=value[:20]):
                err = refused(self, (self.DOC % value).encode("utf-8"), "value-too-long")
                self.assertIn("viewBox", str(err))
                self.assertIn("64 characters", str(err))
        self.assertEqual(_svg.clean_svg((self.DOC % ("0 0 " + "0" * 63 + "9 9")).encode()).view_box, (0, 0, 9, 9))


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
    """width and height of the outer svg: never kept. A number above zero with px, pt, pc, mm, cm, in, em, ex or
    nothing, or a number and %. With a viewBox, two lengths are in one unit and of the viewBox's own shape (to one
    part in a hundred); without one, both are plain or px, and they are the box."""

    DOC = '<svg xmlns="http://www.w3.org/2000/svg" %s><path fill="#111111" d="M0 0h9v9z"/></svg>'

    def test_what_stands_beside_a_view_box(self):
        for attrs in ('width="64" height="32"', 'width="128" height="64"', 'width="6.4" height="3.2"', 'width="64px" height="32px"', 'width="64" height="32px"',
                      'width="64mm" height="32mm"', 'width="2in" height="1in"', 'width="64pt" height="32pt"', 'width="2cm" height="1cm"', 'width="2pc" height="1pc"',
                      'width="100%" height="100%"', 'width="50%" height="7%"', 'width="64"', 'height="32"', 'width="7"', 'height="7mm"', 'width="100%"', 'width="64" height="100%"',
                      'width="100%" height="5"', 'width="+64" height="3.2e1"', 'width=" 64 " height="&#10;32&#9;"', 'width="64.0006" height="32"', 'width="64" height="32.0003"',
                      'width="63.9994" height="32"', 'width="375" height="187.4999955"', 'width="1e9" height="5e8"', 'width="0.0001" height="0.00005"',
                      # the units a letter's size is measured in: `1em` by `1em` is the commonest size of an icon export
                      'width="2em" height="1em"', 'width="1ex" height=".5ex"', 'width="1em"', 'height="3ex"', 'width="2em" height="100%"', 'width="100%" height="1ex"',
                      # sizes a tool has rounded apart from its viewBox, up to one part in a hundred either way
                      'width="64.1" height="32"', 'width="64" height="32.1"', 'width="64.63" height="32"', 'width="63.37" height="32"', 'width="64" height="32.31"',
                      'width="64" height="31.69"', 'width="283.46px" height="141.6px"', 'width="64.63mm" height="32mm"', 'width="2.019em" height="1em"'):
            with self.subTest(attrs=attrs):
                clean = _svg.clean_svg((self.DOC % ('viewBox="0 0 64 32" ' + attrs)).encode())
                self.assertIn('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 32">', clean.text)
                self.assertEqual(clean.notes, [])

    def test_a_width_and_a_height_of_another_shape_than_the_view_box_are_refused_by_name(self):
        # The cleaned file keeps the viewBox alone. Measured 2026-10-12: an svg of 40 by 20 round a viewBox of 10 by 20
        # is drawn at half the size the cleaned file is, and with preserveAspectRatio="none" it is stretched.
        for attrs in ('width="64" height="64"', 'width="32" height="64"', 'width="64" height="33"', 'width="64" height="32.4"', 'width="65" height="32"', 'width="1" height="1000"',
                      'width="64.65" height="32"', 'width="64" height="32.33"', 'width="63.35" height="32"', 'width="64" height="31.67"',   # a part in a hundred is the line
                      'width="64px" height="64px"', 'width="64mm" height="64mm"', 'width="64" height="64" preserveAspectRatio="none"', 'width="1em" height="1em"',
                      'width="640" height="32" preserveAspectRatio="xMinYMin slice"', 'width="2.03em" height="1em"'):
            with self.subTest(attrs=attrs):
                err = refused(self, (self.DOC % ('viewBox="0 0 64 32" ' + attrs)).encode(), "root-size")
                for word in ("viewBox", "width", "height", "one shape", "Ask the tool"):
                    self.assertIn(word, str(err))
        # in two units the two are one shape to a browser and another to a renderer that reads an inch, or a letter's size, its own way
        for attrs in ('width="2in" height="96px"', 'width="64mm" height="32pt"', 'width="64" height="32mm"', 'width="64pt" height="32"', 'width="2em" height="16px"', 'width="64" height="2em"',
                      'width="2em" height="1ex"', 'width="64px" height="32pt"'):
            with self.subTest(attrs=attrs):
                err = refused(self, (self.DOC % ('viewBox="0 0 64 32" ' + attrs)).encode(), "root-size")
                for word in ("viewBox", "width", "height", "two different units", "Ask the tool"):
                    self.assertIn(word, str(err))
        # a size of nothing, whatever its unit: `0%` was accepted and left out, and a browser draws nothing for it
        for attrs in ('width="0" height="32"', 'width="64" height="0"', 'width="0"', 'height="0.0"', 'width="0e5" height="0"', 'width="0px"', 'height="0mm"',
                      'width="0%"', 'height="0%"', 'width="0%" height="0%"', 'width="0.0%" height="32"', 'width="64" height="0e0%"', 'width="100%" height="+0%"', 'width="0em"',
                      'height="0ex"', 'width=" 0% "'):
            with self.subTest(attrs=attrs):
                self.assertIn("nothing", str(refused(self, (self.DOC % ('viewBox="0 0 64 32" ' + attrs)).encode(), "root-size")))

    def test_what_is_no_width_or_height_of_the_outer_svg(self):
        for value, code in (("", "bad-value"), ("auto", "bad-value"), ("64.", "bad-value"), ("64 px", "bad-value"), ("64PX", "bad-value"), ("64MM", "bad-value"), ("6e100", "bad-value"),
                            ("64,", "bad-value"), ("64 32", "bad-value"), ("\u0666\u0664", "bad-value"), ("64\u00a0", "bad-value"), ("100 %", "bad-value"), ("%", "bad-value"),
                            ("64rem", "length-unit"), ("64vw", "length-unit"), ("64vh", "length-unit"), ("64ch", "length-unit"), ("64Q", "length-unit"),
                            ("-64", "negative-size"), ("-64mm", "negative-size"), ("-100%", "negative-size"), ("-0", "negative-size"), ("-1em", "negative-size"), ("-0%", "negative-size"),
                            ("0" * 64 + "9", "value-too-long"), ("1e10", "value-too-long"), ("9e99mm", "value-too-long"),
                            ("0" * 62 + "9mm", "value-too-long"), ("0" * 63 + "9%", "value-too-long"), ("0" * 62 + "9em", "value-too-long")):
            for doc in (self.DOC % ('viewBox="0 0 64 32" width="%s"' % value), self.DOC % ('viewBox="0 0 64 32" height="%s"' % value), self.DOC % ('width="%s" height="32"' % value)):
                with self.subTest(value=ascii(value), doc=doc[40:80]):
                    refused(self, doc.encode("utf-8"), code)

    def test_without_a_view_box_the_width_and_height_are_the_box_and_are_plain(self):
        for attrs, box in (('width="64" height="32"', "0 0 64 32"), ('width="64px" height="32px"', "0 0 64 32"), ('width="6.4e1" height="+32.0"', "0 0 6.4e1 +32.0"),
                           ('width="0.01" height=".2"', "0 0 0.01 .2"), ('width=" 64 " height="32"', "0 0 64 32")):
            with self.subTest(attrs=attrs):
                self.assertIn('viewBox="%s"' % box, _svg.clean_svg((self.DOC % attrs).encode()).text)
        for attrs in ("", 'width="64"', 'height="32"', 'width="100%" height="100%"', 'width="64" height="50%"', 'width="64mm" height="32mm"', 'width="2in" height="1in"',
                      'width="64pt" height="32pt"', 'width="2cm" height="1cm"', 'width="2pc" height="1pc"', 'width="64" height="32mm"', 'width="0" height="32"', 'width="64" height="0"',
                      'width="2em" height="1em"', 'width="2ex" height="1ex"', 'width="1em"', 'width="64" height="1em"', 'width="0%" height="0%"'):
            with self.subTest(attrs=attrs):
                refused(self, (self.DOC % attrs).encode(), "no-size")


class NothingHere(Line):
    """The values that only say "nothing here" are left out without a word: filter, mask, vector-effect and the four
    marker properties of `none`, mix-blend-mode of `normal`, isolation and image-rendering of `auto`. Before 2026-10-12
    the first four were refused with a sentence that said the effect was used, and until 2026-10-13 the rest were
    (an editor writes `marker:none` into the style of every shape)."""

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
        self.assertEqual(sorted(_svg.NO_EFFECT.items()), [("filter", "none"), ("image-rendering", "auto"), ("isolation", "auto"), ("marker", "none"), ("marker-end", "none"),
                                                          ("marker-mid", "none"), ("marker-start", "none"), ("mask", "none"), ("mix-blend-mode", "normal"), ("vector-effect", "none")])
        # an editor's long style, as it is written: nothing of it is drawn, and nothing is said but the one note
        long = ("fill:#111111;fill-opacity:1;stroke:none;marker:none;marker-start:none;marker-mid:none;marker-end:none;isolation:auto;image-rendering:auto;"
                "-inkscape-stroke:none;-inkscape-font-specification:'Sans Bold';mix-blend-mode:normal;paint-order:normal")
        doc = bare('<path style="%s" d="M0 0h9v9z"/>' % long)
        clean = _svg.clean_svg(_input.mark(_input.load(doc)).colour)   # through the door the intake uses
        self.assertEqual(clean.colours, ["#111111"])
        self.assertEqual(clean.notes, ["left out styles that only an editor reads (their names start -inkscape-)"])
        self.assertEqual(_svg.clean_svg(_input.mark(_input.load(T.build_zip([("logo.svg", doc)]))).colour).notes, clean.notes)

    def test_an_editors_own_properties_are_left_out_with_one_note_whatever_they_are_called(self):
        for style in ("-inkscape-stroke:none", "-inkscape-stroke:hairline", "-inkscape-font-specification:'DejaVu Sans, Bold'", "-inkscape-anything-at-all:x(1 2)", "-inkscape-:0",
                      "-inkscape-stroke:none;-inkscape-font-specification:Sans;-inkscape-stroke:hairline"):
            for doc in (bare('<path style="%s;fill:#111111" d="M0 0h9v9z"/>' % style), bare("<style>path{%s}</style>" % style + '<path fill="#111111" d="M0 0h9v9z"/>'),
                        bare("<style>.unused{%s}</style>" % style + '<path fill="#111111" d="M0 0h9v9z"/>')):
                with self.subTest(style=style, doc=doc[110:150]):
                    clean = _svg.clean_svg(doc)
                    self.assertEqual(clean.notes, ["left out styles that only an editor reads (their names start -inkscape-)"])
                    self.assertNotIn("inkscape", clean.text)
        # another program's prefix is not this one, and what such a value holds is still a piece of a style
        for style, code in (("-webkit-print-color-adjust:exact", "css-property"), ("-moz-inkscape-stroke:none", "css-property"), ("inkscape-stroke:none", "css-property"),
                            ("-inkscape-stroke:url(https://x.example/a)", "css-url"), ("-inkscape-stroke:expression(1)", "css-script"), ("-Inkscape-stroke:none", "css-unreadable")):
            with self.subTest(style=style):
                refused(self, bare('<path style="%s" d="M0 0h9v9z"/>' % style), code)

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
        for name in ("marker", "marker-start", "marker-mid", "marker-end"):
            for value in ("url(#m)", "None", "NONE", "", "inherit", "auto", "none none"):
                with self.subTest(name=name, value=value):
                    refused(self, bare('<path %s="%s" d="M0 0h9"/>' % (name, value)), "marker")
                    if value:
                        refused(self, bare('<path style="%s:%s" d="M0 0h9"/>' % (name, value)), "marker")
                        refused(self, bare("<style>.unused{%s:%s}</style><path d='M0 0h9'/>" % (name, value)), "marker")
        # isolation and image-rendering are no attributes of a shape: another value is refused in a style, and as an
        # attribute it is left out with a note, like any attribute this check does not use
        for name, value in (("isolation", "isolate"), ("isolation", "Auto"), ("image-rendering", "pixelated"), ("image-rendering", "optimizeQuality"), ("image-rendering", "auto auto")):
            with self.subTest(name=name, value=value):
                refused(self, bare('<rect style="%s:%s" width="9" height="9"/>' % (name, value)), "css-property")
                refused(self, bare("<style>.unused{%s:%s}</style><rect width='9' height='9'/>" % (name, value)), "css-property")
                self.assertEqual(_svg.clean_svg(bare('<rect %s="%s" width="9" height="9"/>' % (name, value))).notes, ["left out attributes this check does not use: " + name])


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

    def test_a_kept_name_without_a_line_is_a_refusal_by_name_never_a_crash(self):
        # every name has its line today (the test above); should a name ever be kept without one, the file is refused
        # with a sentence, where it once would have ended in a KeyError
        for name in ("no-such-name", "x-new", ""):
            with self.assertRaises(_svg.Refusal) as cm:
                _svg._validate(name, "5")
            self.assertEqual(cm.exception.code, "no-grammar")
        for name in ("stroke-linecap", "x", "points", "clipPathUnits", "viewBox"):
            line = _svg.GRAMMAR.pop(name)
            root_line = _svg.ROOT_GRAMMAR.pop(name)
            try:
                doc = (svg('<clipPath id="c" clipPathUnits="userSpaceOnUse"><polygon points="1 2 3 4" x="1" stroke-linecap="round"/></clipPath>') if name != "stroke-linecap"
                       else svg("<style>.unused{stroke-linecap:round}</style>"))
                err = refused(self, doc, "no-grammar")
                self.assertIn(name, str(err))
                self.assertIn("Ask the tool", str(err))
            finally:
                _svg.GRAMMAR[name], _svg.ROOT_GRAMMAR[name] = line, root_line
        self.assertEqual(_svg.clean_svg(svg("<style>.unused{stroke-linecap:round}</style>")).colours, ["#b4531a"])

    def test_a_line_answers_none_or_why_not_and_nothing_else(self):
        for name, line in sorted(_svg.GRAMMAR.items()):
            for value in ("", "5", "-5", "5px", "5mm", "50%", "none", "auto", "a", "url(#a)", "0 0 9 9", "translate(1)", "scale(0)", "skewX(90)", "M0 0", "x" * 300, "1 " * 5000, "9e99", "\u00a0"):
                with self.subTest(name=name, value=value[:20]):
                    why = line(value)
                    self.assertTrue(why is None or why in ("bad", "unit", "below zero") or (isinstance(why, tuple) and why[0] in ("long", "flat") and why[1]), why)
        self.assertEqual(_svg.GRAMMAR["transform"]("translate(1) scale(0)"), ("flat", "scale(0)"))

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


class HowFarADrawingReaches(unittest.TestCase):
    """A number that places or sizes a shape is no further from zero than the box's own farthest edge and a hundred
    times its larger side beyond it. Until 2026-10-13 it could be a thousand million: such a file was drawn by the
    site's renderer one way in a small icon and another in a large one, and slowly."""

    def doc(self, inner, box='viewBox="0 0 10 10"'):
        return ('<svg %s %s>%s<path fill="#111111" d="M0 0h1v1z"/></svg>' % (NS, box, inner)).encode()

    def near_and_far(self, shape, near, far, box='viewBox="0 0 10 10"', name=None):
        with self.subTest(shape=shape, near=near):
            _svg.clean_svg(self.doc(shape % near, box))
        with self.subTest(shape=shape, far=far):
            err = refused(self, self.doc(shape % far, box), "too-far")
            for word in ("far outside", "Ask the tool") + ((name,) if name else ()):
                self.assertIn(word, str(err))

    def test_every_number_that_places_or_sizes_a_shape_is_held_both_ways(self):
        # the box is 10 by 10 from 0: 100 times 10, beyond its far edge at 10
        shapes = {"x": '<rect x="%s" width="4" height="4"/>', "y": '<rect y="%s" width="4" height="4"/>', "width": '<rect width="%s" height="4"/>', "height": '<rect width="4" height="%s"/>',
                  "rx": '<rect width="4" height="4" rx="%s"/>', "ry": '<rect width="4" height="4" ry="%s"/>', "cx": '<circle cx="%s" r="3"/>', "cy": '<circle cy="%s" r="3"/>',
                  "r": '<circle r="%s"/>', "x1": '<line x1="%s" stroke="#111111"/>', "y1": '<line y1="%s" stroke="#111111"/>', "x2": '<line x2="%s" stroke="#111111"/>',
                  "y2": '<line y2="%s" stroke="#111111"/>'}
        for name, shape in shapes.items():
            for near, far in (("1010", "1011"), ("1010.0", "1010.5"), ("1.01e3", "1.011e3"), ("1010px", "1011px"), ("+1010", "+1e9"), ("5", "1e4")):
                self.near_and_far(shape, near, far, name=name)
            if name not in ("r", "rx", "ry"):
                self.near_and_far(shape, "10100%", "10101%", name=name)   # a share of the box: 101 times 10
            if name not in ("width", "height", "r", "rx", "ry"):
                for near, far in (("-1010", "-1011"), ("-1010px", "-1010.01px"), ("-10100%", "-10110%")):
                    self.near_and_far(shape, near, far, name=name)
        for shape in ('<rect rx="%s" ry="auto" width="4" height="4"/>', '<ellipse rx="%s" ry="2"/>', '<ellipse rx="2" ry="%s"/>'):
            self.near_and_far(shape, "1010", "1011")
        for shape, name in (('<polygon points="0 0 %s 0 5 5"/>', "points"), ('<polyline points="0,0 5,%s" stroke="#111111"/>', "points"), ('<polygon points="%s-5.5,.5 9 9 9"/>', "points")):
            for near, far in (("1010", "1011"), ("-1010", "-1011"), ("1.01e3", "1.011e3"), ("0", "1e9")):
                self.near_and_far(shape, near, far, name=name)
        for name, shape in (("stroke-width", '<rect stroke="#111111" stroke-width="%s" width="4" height="4"/>'), ("stroke-width", '<rect stroke="#111111" style="stroke-width:%s" width="4" height="4"/>'),
                            ("stroke-width", '<style>rect{stroke-width:%s}</style><rect stroke="#111111" width="4" height="4"/>'), ("stroke-width", '<g stroke-width="%s"><rect width="4" height="4"/></g>'),
                            ("stroke-dashoffset", '<rect stroke-dashoffset="%s" width="4" height="4"/>'), ("stroke-dashoffset", '<rect style="stroke-dashoffset:%s" width="4" height="4"/>'),
                            ("stroke-dashoffset", '<style>*{stroke-dashoffset:%s}</style><rect width="4" height="4"/>')):
            self.near_and_far(shape, "1010", "1011", name=name)
            self.near_and_far(shape, "1010px", "1e9", name=name)
        self.near_and_far('<rect stroke-dashoffset="%s" width="4" height="4"/>', "-1010", "-1011", name="stroke-dashoffset")
        self.near_and_far('<path fill="#111111" d="M0 0h9v9z" stroke-width="%s"/>', "1010", "1011", box='viewBox="0 0 10 10" stroke="#111111"')
        # a value no element ends up with is not written, and so is not held: the rule's other value is
        _svg.clean_svg(self.doc('<style>.unused{stroke-width:1e9} rect{stroke-width:1e9}</style><rect style="stroke-width:2" stroke="#111111" width="4" height="4"/>'))
        # and what neither places nor sizes anything is not held to the box at all
        for inner in ('<path d="M1 9L5 2L9 9" fill="none" stroke="#111111" stroke-miterlimit="1e9"/>', '<line x2="9" stroke="#111111" stroke-dasharray="1e9"/>',
                      '<rect width="4" height="4" opacity="1.0"/>', '<g transform="scale(1e-9)"/>'):
            with self.subTest(inner=inner):
                _svg.clean_svg(self.doc(inner))

    def test_path_data_is_held_by_its_numbers_and_an_arcs_flags_are_no_numbers(self):
        path = '<path fill="#111111" d="%s"/>'
        for near, far in (("M0 0H1010", "M0 0H1011"), ("M0 0L1010-1010", "M0 0L1010-1011"), ("M-1010 0h9", "M-1011 0h9"), ("m0 0l1010 0 0 1010z", "m0 0l1010 0 0 1010.5z"),
                          ("M0,0C1,2,3,4,5,1010", "M0,0C1,2,3,4,5,1011"), ("M0 0Q5 5 1.01e3 0", "M0 0Q5 5 1.011e3 0"), ("M0 0h1010.", "M0 0h1011."), ("M0 0h.101e4", "M0 0h.1011e4"),
                          ("M0 0h1e3", "M0 0h1e4"), ("M0 0h1E+3", "M0 0h1E+4"), ("M0 0h10e2", "M0 0h1e9"), ("M0 0h101e1", "M0 0h1e300"), ("M0 0h1e-300", "M0 0h1e999"),
                          ("M0 0T5 5T9 1010", "M0 0T5 5T9 -1011"), ("M0 0S1 2 3 1010", "M0 0s1 2 3 1011"), ("M0 0V1010", "M0 0v1011"),
                          # an arc: rx ry turn, two flags of one digit each, then where it ends
                          ("M0 0A1010 1010 0 0 1 9 9", "M0 0A1011 5 0 0 1 9 9"), ("M0 0a5 5 0 1 1 1010 0", "M0 0a5 5 0 1 1 1011 0"), ("M0 0a5 5 1010 1 1 9 0", "M0 0a5 5 1011 1 1 9 0"),
                          # written without blanks, the flags run into the number: `111000` is a 1, a 1 and 1000, not 111,000
                          ("M0 0a5 5 0 111000 0", "M0 0a5 5 0 111011 0"), ("M0 0a5 5 0 011010 0", "M0 0a5 5 0 011011 0"), ("M0 0a5 5 0 1 11010 0", "M0 0a5 5 0 1 11011 0"),
                          ("M0 0a5 5 0 1,1,1010,0", "M0 0a5 5 0 1,1,1011,0"), ("M0 0a5 5 0 00.5 9", "M0 0a5 5 0 001011 9"), ("M0 0A5 5 0 111000 0 5 5 0 001010 9", "M0 0A5 5 0 111000 0 5 5 0 001011 9"),
                          ("M0 0a5 5 0 119-1010", "M0 0a5 5 0 119-1011"), ("M0 0a5 5 0 11-1010 9", "M0 0a5 5 0 11-1011 9"), ("M0 0a5 5 0 11.5 1010", "M0 0a5 5 0 111011.5 9")):
            self.near_and_far(path, near, far, name="d")
        # a real export, written the short way: a ring 100 across in a box of 100, whose arcs end `1 1 100 0`
        ring = '<svg %s viewBox="0 0 100 100"><path fill="#111111" d="M0 50a50 50 0 11100 0a50 50 0 11-100 0z"/></svg>' % NS
        self.assertEqual(_svg.clean_svg(ring.encode()).colours, ["#111111"])
        self.assertEqual(_svg._path_numbers("M0 50a50 50 0 11100 0a50 50 0 11-100 0z"), ["0", "50", "50", "50", "0", "100", "0", "50", "50", "0", "-100", "0"])
        self.assertEqual(_svg._path_numbers("M1-2.5.5e1L3,4 5 6zA1 2 3 0 1 4 5 6 7 8 109 10"), ["1", "-2.5", ".5e1", "3", "4", "5", "6", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])
        self.assertEqual(_svg._path_numbers(""), [])
        # however long the path is, its numbers are found in one pass
        long = [self.doc(path % ("M0 0" + "h1" * 60000)), self.doc(path % ("M0 0" + " 1" * 90000 + " 1011")), self.doc(path % ("M0 0" + "a1 1 0 111 1" * 15000)),
                self.doc(path % ("M0 0" + "e" * 150000)), self.doc(path % ("M0 0" + "." * 150000)), self.doc(path % ("M0 0" + "-" * 150000)), self.doc(path % ("M" + "1e" * 90000))]
        self.assertEqual([out["code"] for out in judged(self, long)], ["ok", "too-far", "ok", "ok", "ok", "ok", "ok"])

    def test_a_transform_is_held_by_what_it_moves_and_scales_by_and_not_by_its_angles(self):
        moved = '<g transform="%s"><rect width="4" height="4"/></g>'
        for near, far in (("translate(1010)", "translate(1011)"), ("translate(0 -1010)", "translate(0 -1011)"), ("translate(5,5) translate(-1010)", "translate(5,5) translate(-1011)"),
                          ("scale(1010)", "scale(1011)"), ("scale(1 -1010)", "scale(1 -1011)"), ("matrix(1 0 0 1 1010 -1010)", "matrix(1 0 0 1 0 1011)"),
                          ("matrix(1010 0 0 1 0 0)", "matrix(1 1011 -1011 1 0 0)"), ("rotate(45 1010 0)", "rotate(45 1011 0)"), ("rotate(45,0,-1010)", "rotate(45,0,-1011)"),
                          ("rotate(100000)", "rotate(100000 0 1e9)"), ("rotate(1e5) skewX(5000) skewY(-1e5)", "rotate(1e5) skewX(5000) skewY(-1e5) translate (1011)"),
                          ("translate (1010)", "scale  (1011)")):
            self.near_and_far(moved, near, far, name="transform")
        self.near_and_far('<rect transform="%s" width="4" height="4"/>', "translate(1010)", "translate(1e9)", name="transform")
        self.near_and_far('<clipPath id="c" transform="%s"><rect width="4" height="4"/></clipPath>', "translate(1010)", "translate(1011)", name="transform")

    def test_the_bound_is_counted_from_the_box_wherever_and_however_large_the_box_is(self):
        rect = '<rect x="%s" width="4" height="4"/>'
        # an icon cut out of a large sheet keeps its place on the sheet: its numbers are far from zero and inside its box
        self.near_and_far(rect, "6010", "6011", box='viewBox="5000 -5000 10 10"')
        self.near_and_far(rect, "-5010", "-6011", box='viewBox="5000 -5000 10 10"')
        self.near_and_far('<path d="M240-200h120v-240h240v240h120v-360L480-740 240-560v%sZ"/>', "360", "98000", box='viewBox="0 -960 960 960"')
        self.near_and_far('<rect x="%s" width=".004" height=".004"/>', "2.02", "2.03", box='viewBox="0 0 0.01 0.02"')
        self.near_and_far(rect, "4040", "4041", box='width="40" height="30"')
        self.near_and_far(rect, "101000000", "101000001", box='viewBox="0 0 1e6 1e6"')
        self.near_and_far(rect, "2020", "2021", box='viewBox="0 0 20 1"')
        self.near_and_far(rect, "10100%", "10101%", box='viewBox="0 0 100 100" width="1em" height="1em"')   # a share of the box's 100: 100 times it beyond the far edge
        # in the smallest box there is, a turn is still a turn
        _svg.clean_svg(self.doc('<g transform="rotate(180) skewX(45)"><rect width=".004" height=".004"/></g>', 'viewBox="0 0 0.01 0.01"').replace(b"M0 0h1v1z", b"M0 0h.01v.01z"))

    def test_the_refusal_says_what_was_found_and_how_large_the_box_is(self):
        err = refused(self, self.doc('<circle cx="5" cy="5" r="80000"/>'), "too-far")
        for word in ("r holds '80000'", "the box is 10 by 10", "nothing outside its frame"):
            self.assertIn(word, str(err))
        err = refused(self, self.doc('<path d="M0 0L5 5 123456 7"/>', 'viewBox="0 0 24 12"'), "too-far")
        for word in ("d holds the number 123456", "the box is 24 by 12"):
            self.assertIn(word, str(err))
        # through the door the intake uses, as a file and inside a package
        doc = self.doc('<circle cx="5" cy="5" r="80000"/>')
        self.assertEqual(refused(self, _input.mark(_input.load(doc)).colour, "too-far").code, "too-far")
        self.assertEqual(refused(self, _input.mark(_input.load(T.build_zip([("logo.svg", doc)]))).colour, "too-far").code, "too-far")

    def test_a_drawing_made_far_larger_than_its_box_and_scaled_down_is_told_its_own_way_out(self):
        # A font's letter of 1,700 units in a box of 16, or an artboard of 10,000 in a box of 24, scaled down to fit by one
        # transform: nothing of it lies outside its frame, and "ask for the drawing with nothing outside its frame" asked for
        # the file in hand. It is refused as it was (a number is held as it is written); the sentence names this way too.
        letter = self.doc('<path fill="#111111" transform="translate(0 14) scale(0.0078125 -0.0078125)" d="M200 0h1600v1700h-1600z"/>', 'viewBox="0 0 16 16"')
        artboard = self.doc('<g transform="scale(.0024)"><path fill="#1a1a1a" d="M1000 1000h8000v8000h-8000z"/></g>', 'viewBox="0 0 24 24"')
        placed_outside = self.doc('<circle cx="5" cy="5" r="80000"/>')
        for what, doc, found in (("a letter", letter, "d holds the number 1700, and the box is 16 by 16"), ("an artboard", artboard, "d holds the number 8000, and the box is 24 by 24"),
                                 ("a shape placed far outside", placed_outside, "r holds '80000', and the box is 10 by 10")):
            with self.subTest(what=what):
                said = str(refused(self, doc, "too-far"))
                for word in (found, "Ask the tool for the drawing with nothing outside its frame.", "Or the drawing is made far larger than its box and scaled down to fit",
                             "ask for it in the box's own units, with the scaling applied to the shapes."):
                    self.assertIn(word, said)
                answer = through_the_command(self, doc)   # the door production has
                self.assertEqual((answer["status"], answer["code"], answer["message"], answer["written"]), ("refused", "too-far", said, []))
        # and what the sentence asks for is read: the same two drawings in the box's own units, the scaling applied
        for doc in (self.doc('<path fill="#111111" d="M1.5625 14h12.5v-13.28125h-12.5z"/>', 'viewBox="0 0 16 16"'), self.doc('<path fill="#1a1a1a" d="M2.4 2.4h19.2v19.2h-19.2z"/>', 'viewBox="0 0 24 24"')):
            self.assertIn(through_the_command(self, doc)["code"], READ)
        self.assertIn("scaled down to fit by a group", " ".join(_svg.__doc__.split()))


class Dashes(unittest.TestCase):
    """A dashed outline costs the renderer one step for every dash and gap. Measured 2026-10-13 (processor time for one
    icon): a zigzag of 25 KB inside its own box, with dashes a thousandth of the box long, 10 seconds; one of 3.6 KB
    that ran a hundred boxes out and back, 33. So no dash is smaller than a thousandth of the box, a dashed outline
    stands on a shape whose length this check can tell from its numbers (not on a <path>), and all the dashed
    outlines of a file together are cut into no more than 100,000 dashes and gaps."""

    LINE = '<line x2="9" stroke="#111111" %s/>'

    def doc(self, inner, box="0 0 10 10", root=""):
        return ('<svg %s viewBox="%s" %s>%s<path fill="#111111" d="M0 0h1v1z"/></svg>' % (NS, box, root, inner)).encode()

    def test_no_dash_or_gap_is_smaller_than_a_thousandth_of_the_box_unless_it_is_nothing(self):
        for value in ("0.0099", "0.01 0.0099", "0.0099 5", "5 5 5 0.009", "0 0.0099", "1e-9", "1e-99", ".00999", "9.9e-3", "5,0.001", "0.005 0", "5 5 1e-3"):
            for inner in (self.LINE % ('stroke-dasharray="%s"' % value), self.LINE % ('style="stroke-dasharray:%s"' % value), "<style>line{stroke-dasharray:%s}</style>" % value + self.LINE % "",
                          '<g stroke-dasharray="%s">%s</g>' % (value, self.LINE % ""), '<g stroke-dasharray="%s"/>' % value, '<rect stroke-dasharray="%s" width="4" height="4"/>' % value,
                          '<clipPath id="c" stroke-dasharray="%s"/>' % value):
                with self.subTest(value=value, inner=inner[:40]):
                    err = refused(self, self.doc(inner), "dash-too-small")
                    for word in ("too small to see", "stroke-dasharray", "10 across", "Ask the tool"):
                        self.assertIn(word, str(err))
            with self.subTest(value=value, where="the outer svg"):
                refused(self, self.doc(self.LINE % "", root='stroke-dasharray="%s"' % value), "dash-too-small")
        for value, written in (("0.01", "0.01"), ("0.01 0.01", "0.01 0.01"), ("1e-2", "1e-2"), (".01,5", ".01 5"), ("0 0.01", "0 0.01"), ("0.01 0", "0.01 0"), ("5 0 5", "5 0 5"),
                               ("0", "0"), ("0 0", "0 0"), ("0.0 0e0 .0", "0.0 0e0 .0"), ("none", "none"), ("3 1", "3 1"), ("1e9", "1e9")):
            with self.subTest(value=value):
                self.assertIn('stroke-dasharray="%s"' % written, _svg.clean_svg(self.doc(self.LINE % ('stroke-dasharray="%s"' % value))).text)
        # the box sets the line: a dash of 1 is a thousandth of a box 1,000 across, and one of 0.5 is not
        for box, near, far in (("0 0 1000 1000", "1", "0.999"), ("0 0 1000 50", "1 1", "1 .5"), ("0 0 0.01 0.02", "0.00002", "0.000019"), ("-5 -5 24 24", "0.024", "0.0239"),
                               ("0 0 1e6 1e6", "1000", "999")):
            with self.subTest(box=box):
                _svg.clean_svg(self.doc(self.LINE.replace("9", ".005") % ('stroke-dasharray="%s"' % near), box).replace(b"M0 0h1v1z", b"M0 0h.01v.01z"))
                refused(self, self.doc(self.LINE.replace("9", ".005") % ('stroke-dasharray="%s"' % far), box).replace(b"M0 0h1v1z", b"M0 0h.01v.01z"), "dash-too-small")
        # a rule no element ends up with is not written, and so is not held
        _svg.clean_svg(self.doc("<style>.unused{stroke-dasharray:1e-9}</style>" + self.LINE % ""))

    def test_a_dashed_outline_stands_on_a_shape_whose_length_the_numbers_tell(self):
        path = '<path d="M0 5H9" %s/>'
        for inner in (path % 'stroke="#111111" stroke-dasharray="3 1"', path % 'style="stroke:#111111;stroke-dasharray:3 1"', "<style>path{stroke:#111111;stroke-dasharray:3,1}</style>" + path % "",
                      '<g stroke-dasharray="3 1">%s</g>' % (path % 'stroke="#111111"'), '<g stroke="#111111">%s</g>' % (path % 'stroke-dasharray="3"'),
                      '<g stroke="#111111" stroke-dasharray="3 1"><g><g>%s</g></g></g>' % (path % ""), '<g stroke-dasharray="none"><g stroke-dasharray="0 3">%s</g></g>' % (path % 'stroke="red"'),
                      '<clipPath id="c">%s</clipPath>' % (path % 'stroke="#111111" stroke-dasharray="3 1"'), path % 'stroke="#111111" stroke-width="0" stroke-dasharray="3 1"',
                      path % 'stroke="currentColor" color="#111111" stroke-dasharray="3 1"', "<style>*{stroke-dasharray:1}</style>" + path % 'stroke="#111111"'):
            with self.subTest(inner=inner[:70]):
                err = refused(self, self.doc(inner), "dashed-path")
                for word in ("<path>", "dashed outline", "turn the dashed outline into shapes"):
                    self.assertIn(word, str(err))
        with self.subTest(where="the outer svg"):
            refused(self, self.doc("", root='stroke="#111111" stroke-dasharray="3 1"'), "dashed-path")
            refused(self, self.doc(path % "", root='style="stroke:#111111;stroke-dasharray:3 1"').replace(b'<path fill="#111111" d="M0 0h1v1z"/>', b""), "dashed-path")
        # a path that paints no outline, or whose dashes are none after all, is no dashed outline
        for inner in (path % 'stroke-dasharray="3 1" fill="#111111"', '<g stroke-dasharray="3 1">%s</g>' % (path % 'fill="#111111"'), path % 'stroke="#111111" stroke-dasharray="none"',
                      path % 'stroke="#111111" stroke-dasharray="0 0"', path % 'stroke="#111111" stroke-dasharray="0"', path % 'stroke="none" stroke-dasharray="3 1"',
                      '<g stroke="#111111" stroke-dasharray="3 1">%s</g>' % (path % 'stroke="none"'), '<g stroke="#111111" stroke-dasharray="3 1">%s</g>' % (path % 'stroke-dasharray="none"'),
                      '<g stroke="#111111" stroke-dasharray="3 1">%s</g>' % (path % 'style="stroke-dasharray:0 0 0"'), "<style>path{stroke-dasharray:none}</style>" + path % 'stroke="#111111" stroke-dasharray="3 1"'):
            with self.subTest(inner=inner[:70]):
                _svg.clean_svg(self.doc(inner))
        # and on every other shape a dashed outline is kept
        for shape in ('<line x2="9" y2="9" %s/>', '<rect width="8" height="8" rx="2" %s/>', '<circle cx="5" cy="5" r="4" %s/>', '<ellipse cx="5" cy="5" rx="4" ry="2" %s/>',
                      '<polyline points="1 1 9 1 5 9" %s/>', '<polygon points="1,1 9,1 5,9" %s/>'):
            for attrs in ('stroke="#111111" stroke-dasharray="3 1"', 'style="stroke:#111111;stroke-dasharray:0 2"', 'stroke="#111111" stroke-dasharray="1" stroke-dashoffset="-.5"'):
                with self.subTest(shape=shape, attrs=attrs):
                    self.assertIn("stroke-dasharray=", _svg.clean_svg(self.doc(shape % attrs)).text)
            self.assertIn('stroke-dasharray="3 1"', _svg.clean_svg(self.doc('<g stroke="#111111" stroke-dasharray="3,1">%s</g>' % (shape % ""))).text)

    def test_all_the_dashed_outlines_of_a_file_together_are_cut_into_no_more_than_the_budget(self):
        self.assertEqual(_svg.MAX_DASH_PIECES, 100000)
        dashed = 'stroke="#111111" stroke-dasharray="%s"'
        # with dashes and gaps of 0.01, an outline is cut into 100 for each unit of its length: 1,000 units are the budget
        for near, far in (('<line x2="1000" %s/>', '<line x2="1000.1" %s/>'), ('<line x1="-250" y1="250" x2="250" y2="-250" %s/>', '<line x1="-250" y1="250" x2="250" y2="-251" %s/>'),
                          ('<rect width="250" height="250" %s/>', '<rect width="250" height="250.1" %s/>'), ('<rect x="900" y="-900" width="499" height="1" %s/>', '<rect x="900" y="-900" width="501" height="1" %s/>'),
                          ('<rect width="2500%" height="2500%" %s/>', '<rect width="2500%" height="2501%" %s/>'), ('<rect width="250px" height="250px" rx="5" %s/>', '<rect width="251px" height="250px" rx="5" %s/>'),
                          ('<circle r="159" %s/>', '<circle r="160" %s/>'), ('<ellipse rx="159" ry="1" %s/>', '<ellipse rx="1" ry="160" %s/>'), ('<ellipse rx="159" ry="auto" %s/>', '<ellipse rx="auto" ry="160" %s/>'),
                          ('<polyline points="0 0 500 0" %s/>', '<polyline points="0 0 500.1 0" %s/>'), ('<polygon points="0,0 250,0 250,250 0,250" %s/>', '<polygon points="0,0 250,0 250,250 0,250.1" %s/>'),
                          ('<polygon points="-100,100 100,-100 50 50" %s/>', '<polygon points="-100,100 100,-100 50 50 -100,100 100,-100" %s/>'),
                          ('<line x2="10" %s/>' * 100, '<line x2="10" %s/>' * 101), ('<circle r="1" %s/>' * 159, '<circle r="1" %s/>' * 160),
                          ('<line x2="500" %s/><rect width="125" height="125" %s/>', '<line x2="500" %s/><rect width="125" height="126" %s/>')):
            with self.subTest(near=near[:50]):
                _svg.clean_svg(self.doc(near.replace("%s", dashed % "0.01")))
                err = refused(self, self.doc(far.replace("%s", dashed % "0.01")), "too-many-dashes")
                for word in ("100,000", "dashed outlines", "Ask the tool"):
                    self.assertIn(word, str(err))
        # a list is counted by its dashes and gaps as they come round: `0.02 0.01 0.03` is three in 0.06 units, 500 in a line of 10
        for dashes, near, far in (("0.01 0.01", 100, 101), ("0.01", 100, 101), ("0 0.02", 100, 101), ("0.02 0.01 0.03", 200, 201), ("0.05", 500, 501), ("0.02,0.03", 250, 251),
                                  ("0.01 0.01 0.01 0.01", 100, 101), ("5", 4900, None), ("0 0", 4900, None), ("none", 4900, None)):
            with self.subTest(dashes=dashes):
                _svg.clean_svg(self.doc('<line x2="10" %s/>' % (dashed % dashes) * near))
                if far:
                    refused(self, self.doc('<line x2="10" %s/>' % (dashed % dashes) * far), "too-many-dashes")
        # however the dash list reaches the shapes, and only where an outline is painted
        for inner, code in (('<g %s>%s</g>' % (dashed % "0.01", '<line x2="10"/>' * 101), "too-many-dashes"), ('<g %s>%s</g>' % (dashed % "0.01", '<line x2="10"/>' * 100), None),
                            ("<style>line{stroke:#111111;stroke-dasharray:0.01}</style>" + '<line x2="10"/>' * 101, "too-many-dashes"),
                            ('<g stroke-dasharray="0.01">%s</g>' % ('<line x2="10"/>' * 300), None), ('<g %s>%s</g>' % (dashed % "0.01", '<line stroke="none" x2="1000"/>' * 300), None),
                            ('<g %s>%s</g>' % (dashed % "0.01", '<line stroke-dasharray="none" x2="1000"/>' * 300), None), ('<g %s>%s</g>' % (dashed % "0.01", '<g/>' * 300), None),
                            ('<g %s>%s</g>' % (dashed % "0.01", '<line stroke-dasharray="0" x2="1000"/><line stroke-dasharray="1" x2="1000"/>' * 5), None)):
            with self.subTest(inner=inner[:60]):
                if code:
                    refused(self, self.doc(inner), code)
                else:
                    _svg.clean_svg(self.doc(inner))
        # through the door the intake uses
        doc = self.doc('<circle r="160" %s/>' % (dashed % "0.01"))
        self.assertEqual(refused(self, _input.mark(_input.load(doc)).colour, "too-many-dashes").code, "too-many-dashes")
        self.assertEqual(refused(self, _input.mark(_input.load(self.doc('<path d="M0 5H9" %s/>' % (dashed % "1")))).colour, "dashed-path").code, "dashed-path")

    def test_the_length_the_budget_counts_is_never_less_than_the_length_that_is_drawn(self):
        # A share is a share of the box's width for x and of its height for y. Until 2026-10-13 every share was taken of
        # the larger side BEFORE the two ends of a line were taken from each other: in a box 10 by 1, y1="100%" (which is 1)
        # counted as 10, and a line from there to y2="10" as no length at all. 4,900 such lines were read without a word
        # (4.4 million dashes where the budget is 100,000), and 4,990 in a box 1 by 20 kept the renderer 30 seconds an icon.
        dashed = 'stroke="#111111" stroke-dasharray="%s"'
        wide, tall = "0 0 10 1", "0 0 1 20"   # the smallest dash there is: 0.01 in the one, 0.02 in the other
        for box, dash, shape, each, what in (
                (wide, "0.01", '<line y1="100%%" y2="10" %s/>', 9, "the reported line: from 1 down to 10"),
                (wide, "0.01", '<line y1="10" y2="100%%" %s/>', 9, "the same, its ends changed round"),
                (wide, "0.01", '<line x1="100%%" x2="1" %s/>', 9, "across: from 10 back to 1"),
                (wide, "0.01", '<line x1="10%%" y1="100%%" x2="10" y2="10" %s/>', 18, "both ways at once"),
                (wide, "0.01", '<line x1="10%%" y1="100%%" x2="100%%" y2="1000%%" %s/>', 18, "four shares"),
                (wide, "0.01", '<line y1="-100%%" y2="10px" %s/>', 11, "a share below zero"),
                (wide, "0.01", '<rect width="50%%" height="5" %s/>', 20, "a rect: 5 across (half of 10) and 5 down"),
                (wide, "0.01", '<rect width="5" height="500%%" %s/>', 20, "a rect: 5 across and 5 down (five times 1)"),
                (wide, "0.01", '<rect x="100%%" y="100%%" width="100%%" height="100%%" %s/>', 22, "a rect of the box's own size"),
                (wide, "0.01", '<circle cx="100%%" cy="100%%" r="1" %s/>', 6.2832, "a circle is counted by its radius, wherever it stands"),
                (wide, "0.01", '<ellipse cx="50%%" cy="900%%" rx="1" ry=".5" %s/>', 6.2832, "an ellipse by its larger radius"),
                (tall, "0.02", '<line x1="100%%" x2="20" %s/>', 19, "from 1 across to 20"),
                (tall, "0.02", '<line x1="10100%%" x2="2020" %s/>', 1919, "the measured line: from 101 across to 2,020"),
                (tall, "0.02", '<line y1="100%%" y2="1" %s/>', 19, "from 20 up to 1"),
                (tall, "0.02", '<line x1="100%%" y1="5%%" x2="20" y2="20" %s/>', 38, "both ways at once"),
                (tall, "0.02", '<rect width="100%%" height="50%%" %s/>', 22, "a rect 1 across and 10 down"),
                (tall, "0.02", '<rect width="1" height="50%%" %s/>', 22, "the same, its width a plain number"),
                (tall, "0.02", '<rect width="1000%%" height="1" %s/>', 22, "a rect 10 across and 1 down"),
                (tall, "0.02", '<polyline points="0 0 1 19" %s/>', 40, "a polyline, counted closed (it takes no share)"),
                (tall, "0.02", '<polygon points="0 0 1 0 1 9 0 9" %s/>', 20, "a polygon")):
            pieces = each * 2 / (2 * float(dash))                # dashes and gaps in one such outline
            near = int(_svg.MAX_DASH_PIECES // pieces)           # as many of them as the budget holds
            with self.subTest(what=what, near=near):
                self.assertGreater(near, 0)
                _svg.clean_svg(self.doc(shape % (dashed % dash) * near, box))
                refused(self, self.doc(shape % (dashed % dash) * (near + 1), box), "too-many-dashes")
        # the reported files themselves, as they came
        refused(self, self.doc('<line y1="100%%" y2="10" %s/>' % (dashed % "0.01") * 4900, wide), "too-many-dashes")
        refused(self, self.doc('<line x1="10100%%" x2="2020" %s/>' % (dashed % "0.02") * 4990, tall), "too-many-dashes")
        # through the door the intake uses, as a file and inside a package
        doc = self.doc('<line y1="100%%" y2="10" %s/>' % (dashed % "0.01") * 4900, wide)
        self.assertEqual(refused(self, _input.mark(_input.load(doc)).colour, "too-many-dashes").code, "too-many-dashes")
        doc = self.doc('<line y1="100%%" y2="10" %s/>' % (dashed % "0.01") * 112, wide)   # (a package of 4,900 of them is packed too tight to be read at all)
        self.assertEqual(refused(self, _input.mark(_input.load(T.build_zip([("logo.svg", doc)]))).colour, "too-many-dashes").code, "too-many-dashes")

    def test_for_lines_made_at_random_the_count_is_at_least_the_true_count(self):
        # each end of each line a plain number, a number in px or a share, in boxes of every shape: what the budget counts
        # for it is no less than its true length (a share of the width for x, of the height for y; the render table holds
        # the renderer to that reading), and no more than its way across and its way down together
        import random
        rng = random.Random(20261013)

        def number(of):
            value = rng.choice((0, 1, -1)) * rng.random() * 3 * of
            form = rng.choice(("plain", "px", "share"))
            return ("%.4f%%" % (value * 100 / of), float("%.4f" % (value * 100 / of)) * of / 100) if form == "share" else ("%.4f%s" % (value, "px" if form == "px" else ""), float("%.4f" % value))

        for box in ((0, 0, 10, 1), (0, 0, 1, 20), (0, 0, 10, 10), (-5, 7, 3, 60), (100, 100, 0.5, 0.025), (0, 0, 2000, 100)):
            lines, true = [], []
            for _ in range(60):
                (x1, ax1), (y1, ay1), (x2, ax2), (y2, ay2) = number(box[2]), number(box[3]), number(box[2]), number(box[3])
                lines.append('<line x1="%s" y1="%s" x2="%s" y2="%s"/>' % (x1, y1, x2, y2))
                true.append((((ax2 - ax1) ** 2 + (ay2 - ay1) ** 2) ** 0.5, abs(ax2 - ax1) + abs(ay2 - ay1)))
            clean = _svg.clean_svg(('<svg %s viewBox="%s %s %s %s" stroke="#111111">%s</svg>' % ((NS,) + box + ("".join(lines),))).encode())
            counted = [_svg._outline(node, clean.view_box) for node in clean.root.children]
            self.assertEqual(len(counted), 60)
            for line, got, (length, both) in zip(lines, counted, true):
                with self.subTest(box=box, line=line):
                    self.assertGreaterEqual(got, length - 1e-9)
                    self.assertLessEqual(got, both + 1e-9)
            self.assertGreater(sum(length for length, _both in true), 0)
            # and the file's own count is the sum of them: as many dashed copies as the true lengths allow are never over-admitted
            dash = max(box[2], box[3]) / 1000
            total = sum(counted) * 2 / (2 * dash)
            doc = ('<svg %s viewBox="%s %s %s %s" stroke="#111111" stroke-dasharray="%r">%s</svg>' % ((NS,) + box + (dash, "".join(lines)))).encode()
            if total > _svg.MAX_DASH_PIECES:
                refused(self, doc, "too-many-dashes")
            else:
                _svg.clean_svg(doc)


class WrittenOut(unittest.TestCase):
    """The cleaned text is never larger than a file that may come in. One rule's value is checked once and then written
    onto every element the rule applies to: before 2026-10-12 a file of 228 KB was installed as a favicon of 20 MB, and
    one of 285 KB took 143 seconds and 5.57 GB to be listed as a favicon of 300 MB."""

    def test_a_file_whose_cleaned_text_would_be_too_large_is_refused_by_name(self):
        rule = "<style>*{fill:#111111;stroke:#222222;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;stroke-miterlimit:4;stroke-dasharray:4 2;paint-order:stroke}</style>"
        lines = '<line x2="1"/>' * 4990
        small = bare(rule + lines)
        self.assertLess(len(small), 90 * 1024)
        err = refused(self, small, "output-too-large")
        for word in ("far larger", "logo", "512 KB", "Ask the tool"):
            self.assertIn(word, str(err))
        # the same rule on as many elements as do fit is written out whole
        clean = _svg.clean_svg(bare(rule + '<line x2="1"/>' * 2000))
        self.assertLessEqual(len(clean.text), _svg.MAX_OUTPUT)
        self.assertEqual(clean.text.count("<line"), 2000)

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
        self.assertEqual([out["code"] for out in outcomes], ["value-too-long", "value-too-long", "ok", "value-too-long", "value-too-long", "value-too-long", "bad-value", "bad-value", "ok"])

    def test_the_slowest_files_a_search_inside_every_cap_found_are_judged_in_bounded_time(self):
        # Searched 2026-10-13 with generated files (by hand, at random and by climbing from the slowest): the work is
        # elements x (selectors + values), and it is the same work whether the file comes out whole, is found blank
        # at the end or is too large written out. On a quiet machine each of these takes under a second. The slowest
        # known is the last, found by a reviewer (200 rules of 5 values each on 4,990 shapes, 156 KB): 1.07 to 1.25 seconds
        # of processor time on Python 3.13 and 1.32 to 1.56 on Python 3.9, on a machine at load 11 to 13, before it is
        # refused as too large written out.
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
            bare("<style>%s</style>" % ("*{fill:#f00;stroke:#00f;stroke-width:1;stroke-linecap:round;stroke-linejoin:round}" * _svg.MAX_SELECTORS) + '<rect width="1" height="1"/>' * (_svg.MAX_ELEMENTS - 10)),
        ]
        for data in files:
            self.assertLessEqual(len(data), _svg.MAX_BYTES)
        outcomes = judged(self, files, each=5.0)
        self.assertEqual([out["code"] for out in outcomes], ["blank-mark", "ok", "output-too-large", "output-too-large"])
        self.assertLessEqual(len(outcomes[1]["text"]), _svg.MAX_OUTPUT)

    def test_whatever_is_accepted_comes_out_no_larger_than_the_cap_and_in_plain_ascii(self):
        rules = ["fill:#111111", "stroke:#222222", "stroke-width:2px", "stroke-dasharray:" + " ".join(["1234567.5"] * 16), "stroke-linecap:round", "stroke-linejoin:bevel",
                 "stroke-miterlimit:4", "stroke-dashoffset:-1.5", "fill-rule:evenodd", "clip-rule:evenodd", "opacity:1", "fill-opacity:1", "stroke-opacity:1", "color:#333333",
                 "display:inline", "visibility:visible", "clip-path:url(#%s)" % ("c" * 64), "shape-rendering:geometricPrecision", "paint-order:markers stroke fill"]
        # (the rule names the shapes: one for every element would clip the clip path by itself, and set display on it)
        sheet = "<style>circle,line,rect,polygon{%s}</style><clipPath id=\"%s\"/>" % (";".join(rules), "c" * 64)
        seen = set()
        for elements in (1, 10, 100, 700, 800, 900, 1000, 1500, 4990):
            for shape in ('<circle r="1"/>', '<line x2="1"/>', '<rect id="%s" width="9" height="9"/>' % ("i" * 64), '<polygon points="%s"/>' % ("1 2 " * 20)):
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
