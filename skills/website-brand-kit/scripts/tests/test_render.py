"""The renderer: scenarios 19 and 11 (the sizes), and the rule that a mark is only ever drawn from
the cleaned text held in memory, never from a file path.

`render.mjs` is started inside the site, so `sharp` is the site's own (D2): no new dependency. The
intake checks it first and stops with the command to run when it is missing (scenario 19). These
tests run the real helper; the ones that draw need a `sharp` to borrow (see _testutil).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import _testutil as T
import _png
import _render
import _svg
from _refusal import Refusal

MARK = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<path fill="#b4531a" d="M10 34A22 22 0 0 1 54 34Z"/><rect x="10" y="38" width="44" height="5" fill="#6b2c0b"/></svg>')
WIDE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"><rect width="100" height="40" fill="#123456"/></svg>'


class Site(object):
    """A bare site folder with the borrowed node_modules, cleaned up afterwards."""

    def __init__(self, with_modules=True):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        T.make_site(self.dir, T.node_modules_dir() if with_modules else None)
        self.out = os.path.join(self.dir, "out")

    def close(self):
        self.tmp.cleanup()

    def read(self, name):
        with open(os.path.join(self.out, name), "rb") as f:
            return f.read()


def job(name, size, scale=1.0, background=None):
    return {"name": name, "file": name + ".png", "size": size, "scale": scale, "background": background}


class JobsAreChecked(unittest.TestCase):
    """The wrapper refuses a bad job before it starts anything (no node needed for this)."""

    BAD = [dict(file="../x.png"), dict(file="/tmp/x.png"), dict(file="a/b.png"), dict(file=""), dict(file=".hidden"),
           dict(file="x y.png"), dict(file=5), dict(size=0), dict(size=100000), dict(size=16.5), dict(size=True), dict(size="9"),
           dict(scale=0), dict(scale=1.5), dict(scale=-1), dict(scale="1"), dict(scale=True), dict(background="red"),
           dict(background="#12"), dict(background="#12345g"), dict(background=5),
           # a line break after a good value: Python's "$" lets it by, the helper's does not
           dict(file="a.png\n"), dict(background="#ffffff\n"), dict(file="a.png\n.."), dict(background="\n#ffffff")]

    def test_each_bad_field_is_refused_by_the_wrapper(self):
        for bad in self.BAD:
            with self.subTest(bad=bad):
                with self.assertRaises(Refusal) as cm:
                    _render.check_job(dict(job("a", 16), **bad))
                self.assertEqual(cm.exception.code, "bad-job")
        _render.check_job(job("a", 16))
        _render.check_job(job("a", 2048, 1, "#aBcDeF"))

    def test_only_cleaned_svg_text_is_handed_over(self):
        for bad in ("", "<?xml version='1.0'?><svg/>", "/etc/passwd", "file:///x.svg", b"<svg/>", None,
                    "<svgfoo xmlns='http://www.w3.org/2000/svg'/>", "<svg/>", "<svg>", "<svg\txmlns='http://www.w3.org/2000/svg'/>"):
            with self.subTest(bad=bad):
                with self.assertRaises(Refusal) as cm:
                    _render.Renderer("/nonexistent", node="/nonexistent/node").render(bad, (0, 0, 1, 1), [job("a", 16)], "/nonexistent/out")
                self.assertEqual(cm.exception.code, "bad-job")

    def test_a_box_without_a_width_and_a_height_is_refused_before_anything_is_divided_by_it(self):
        for box in ((0, 0, 0, 5), (0, 0, 5, 0), (0, 0, -1, 5), (0, 0, 5, -1), (0, 0), (), None, (0, 0, "a", 1), (0, 0, None, 1),
                    (0, 0, float("nan"), 1), (0, 0, 1, float("inf"))):
            with self.subTest(box=box):
                with self.assertRaises(Refusal) as cm:
                    _render.Renderer("/nonexistent", node="/nonexistent/node").render(MARK, box, [job("a", 16)], "/nonexistent/out")
                self.assertEqual(cm.exception.code, "bad-job")

    def test_a_job_says_its_background_even_when_it_has_none(self):
        # the helper refuses a job without the key; the wrapper let it through, so the two disagreed
        without = dict(job("a", 16))
        del without["background"]
        with self.assertRaises(Refusal) as cm:
            _render.check_job(without)
        self.assertEqual(cm.exception.code, "bad-job")
        self.assertIn("background", str(cm.exception))
        _render.check_job(dict(without, background=None))

    def test_a_site_folder_that_is_not_there_is_said_so_and_not_blamed_on_node(self):
        with tempfile.TemporaryDirectory() as d:
            a_file = os.path.join(d, "site.txt")
            with open(a_file, "w") as f:
                f.write("not a folder")
            for site in (os.path.join(d, "no-such-site"), a_file):
                with self.subTest(site=site):
                    with self.assertRaises(Refusal) as cm:
                        _render.Renderer(site, node=sys.executable).preflight()  # a program that is there, so only the folder is wrong
                    self.assertEqual(cm.exception.code, "no-site")
                    self.assertIn(site, str(cm.exception))
                    self.assertNotIn("Node is not installed", str(cm.exception))


class WhenTheHelperAnswersBadly(unittest.TestCase):
    """What the wrapper makes of an answer it did not expect. A shell script stands in for node, so
    these need neither node nor sharp."""

    def setUp(self):
        if os.name != "posix":
            self.skipTest("the stand-in for node is a shell script")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def renderer(self, script):
        path = os.path.join(self.tmp.name, "node")
        with open(path, "w") as f:
            f.write("#!/bin/sh\n" + script + "\n")
        os.chmod(path, 0o755)
        return _render.Renderer(self.tmp.name, node=path)

    def test_bytes_that_are_not_utf8_in_the_answer_are_read_not_a_crash(self):
        # a warning may name a path in the computer's own encoding (octal 374 is a Latin-1 u-umlaut)
        good = self.renderer("printf 'warning: D:/sites/m\\374ller\\n' >&2; printf 'caf\\351\\n{\"ok\":true,\"sharp\":\"1\"}\\n'")
        self.assertEqual(good.preflight(), {"ok": True, "sharp": "1"})
        bad = self.renderer("printf '{\"ok\":false,\"error\":\"render-failed\",\"message\":\"in m\\374ller\"}\\n'")
        with self.assertRaises(Refusal) as cm:
            bad.preflight()
        self.assertEqual(cm.exception.code, "render-failed")
        self.assertIn("in m\ufffdller", str(cm.exception))
        silent = self.renderer("printf 'm\\374ller broke\\n' >&2")
        with self.assertRaises(Refusal) as cm:
            silent.preflight()
        self.assertIn("m\ufffdller broke", str(cm.exception))

    def test_an_answer_that_is_json_but_not_an_object_is_a_refusal(self):
        for answer in ("[1,2]", '"ok"', "3", "null", "true", '[{"ok":true}]'):
            with self.subTest(answer=answer):
                with self.assertRaises(Refusal) as cm:
                    self.renderer("printf '%s\\n' '" + answer + "'").preflight()
                self.assertEqual(cm.exception.code, "render-failed")
        self.assertEqual(self.renderer("printf '%s\\n' '{\"ok\":true}'").preflight(), {"ok": True})

    def test_ok_is_the_word_true_and_nothing_that_only_counts_as_true(self):
        # JSON as Python reads it also has NaN, and a 1 or a word is as good as true to an `if`: a stand-in that
        # answered {"ok":NaN} passed for a renderer that had loaded sharp and drawn a pixel
        for answer in ('{"ok":NaN}', '{"ok":1}', '{"ok":"true"}', '{"ok":"yes"}', '{"ok":[true]}', '{"ok":{"a":1}}', '{"ok":Infinity}', '{"ok":1.0}'):
            with self.subTest(answer=answer):
                for call in (lambda r: r.preflight(), lambda r: r.render(MARK, (0, 0, 64, 64), [job("a", 16)], self.tmp.name)):
                    with self.assertRaises(Refusal) as cm:
                        call(self.renderer("printf '%s\\n' '" + answer + "'"))
                    self.assertEqual(cm.exception.code, "render-failed")
        self.assertEqual(self.renderer("printf '%s\\n' '{\"ok\":true}'").preflight(), {"ok": True})

    def test_an_answer_is_one_line_that_ends_at_a_line_feed_and_nowhere_else(self):
        # splitlines() also cuts at U+2028, U+2029, U+0085 and others: an answer that held one in a text (a path in a
        # warning, say) was cut in two there and came out as "did not answer". (Octal: 342 200 250 is U+2028, 302 205 is U+0085.)
        for name, inside, char in (("a line separator", "\\342\\200\\250", "\u2028"), ("a paragraph separator", "\\342\\200\\251", "\u2029"),
                                   ("a next-line character", "\\302\\205", "\x85"), ("a form feed", "\\014", None), ("a vertical tab", "\\013", None),
                                   ("a file separator", "\\034", None)):
            with self.subTest(name=name):
                if char:  # as a text inside the answer it is part of the answer
                    good = self.renderer("printf '{\"ok\":true,\"sharp\":\"a" + inside + "b\"}\\n'")
                    self.assertEqual(good.preflight(), {"ok": True, "sharp": "a%sb" % char})
                    bad = self.renderer("printf '{\"ok\":false,\"error\":\"render-failed\",\"message\":\"in a" + inside + "b\"}\\n'")
                    with self.assertRaises(Refusal) as cm:
                        bad.preflight()
                    self.assertIn("could not be rendered: in a", str(cm.exception))
                    self.assertNotIn(char, str(cm.exception), "and the refusal spells it out")
                # and standing between two answers it ends neither: the last LINE is not JSON
                with self.assertRaises(Refusal) as cm:
                    self.renderer("printf '{\"ok\":false,\"error\":\"bad-job\",\"message\":\"x\"}" + inside + "{\"ok\":true}\\n'").preflight()
                self.assertIn("did not answer", str(cm.exception))
        # a line feed does end a line, with a carriage return before it or without, and blank lines after it count for nothing
        for ending in ("\\n", "\\r\\n", "\\n\\n", "\\r\\n\\r\\n  \\n"):
            with self.subTest(ending=ending):
                self.assertEqual(self.renderer("printf 'a warning\\n{\"ok\":true}" + ending + "'").preflight(), {"ok": True})

    def test_a_message_that_is_no_text_or_a_very_long_one_is_still_one_short_sentence(self):
        for answer in ('{"ok":false,"error":[1],"message":{"a":1}}', '{"ok":false,"error":null,"message":null}', '{"ok":false,"message":7}', '{"ok":false}'):
            with self.subTest(answer=answer):
                with self.assertRaises(Refusal) as cm:
                    self.renderer("printf '%s\\n' '" + answer + "'").preflight()
                self.assertEqual(cm.exception.code, "render-failed")
        long = self.renderer("printf '{\"ok\":false,\"error\":\"render-failed\",\"message\":\"'; head -c 2000000 /dev/zero | tr '\\0' 'a'; printf '\"}\\n'")
        with self.assertRaises(Refusal) as cm:
            long.preflight()
        self.assertLess(len(str(cm.exception)), 400)

    def test_an_answer_that_does_not_say_what_was_drawn_is_a_refusal(self):
        for answer in ('{"ok":true}', '{"ok":true,"results":null}', '{"ok":true,"results":"a.png"}', '{"ok":true,"results":{}}'):
            with self.subTest(answer=answer):
                with self.assertRaises(Refusal) as cm:
                    self.renderer("printf '%s\\n' '" + answer + "'").render(MARK, (0, 0, 64, 64), [job("a", 16)], self.tmp.name)
                self.assertEqual(cm.exception.code, "render-failed")
        drawn = self.renderer("printf '%s\\n' '{\"ok\":true,\"results\":[]}'").render(MARK, (0, 0, 64, 64), [job("a", 16)], self.tmp.name)
        self.assertEqual(drawn, [])

    def test_an_answer_nested_too_deep_to_read_is_a_refusal(self):
        # Python gives up on JSON nested this deep with a RecursionError, which is no ValueError: it came out as a traceback
        many = "head -c %d /dev/zero | tr '\\0' '%s'"
        for name, script in (("an array never closed", many % (200000, "[")),
                             ("an array closed again", many % (100000, "[") + "; " + many % (100000, "]")),
                             ("after a good line", "printf '%s\\n' '{\"ok\":true}'; " + many % (200000, "[")),
                             ("objects", "i=0; while [ $i -lt 20000 ]; do printf '{\"a\":'; i=$((i+1)); done"),
                             ("inside a good answer", "printf '{\"ok\":true,\"results\":'; " + many % (200000, "["))):
            with self.subTest(name=name):
                for call in (lambda r: r.preflight(), lambda r: r.render(MARK, (0, 0, 64, 64), [job("a", 16)], self.tmp.name)):
                    with self.assertRaises(Refusal) as cm:
                        call(self.renderer(script))
                    self.assertEqual(cm.exception.code, "render-failed")
                    self.assertIn("did not answer", str(cm.exception))
        # nesting as deep as an honest answer goes is read
        deep = self.renderer("printf '%s\\n' '{\"ok\":true,\"results\":[[[[[[[[]]]]]]]]}'")
        self.assertEqual(deep.render(MARK, (0, 0, 64, 64), [job("a", 16)], self.tmp.name), [[[[[[[[]]]]]]]])


class WhenSharpIsMissing(unittest.TestCase):
    """Scenario 19. These need node, not sharp."""

    def setUp(self):
        if not shutil.which("node"):
            self.skipTest("no node on this machine")

    def test_no_sharp_stops_with_the_command_to_run_and_never_edits_package_json(self):
        s = Site(with_modules=False)
        self.addCleanup(s.close)
        before = T.read(os.path.join(s.dir, "package.json"))
        with self.assertRaises(Refusal) as cm:
            _render.Renderer(s.dir).preflight()
        self.assertEqual(cm.exception.code, "sharp-missing")
        msg = str(cm.exception)
        self.assertIn("npm install --include=optional", msg)
        self.assertIn("package.json", msg)
        self.assertEqual(T.read(os.path.join(s.dir, "package.json")), before)
        self.assertEqual(sorted(os.listdir(s.dir)), ["package.json"], "nothing may be written to the site")

    def test_a_sharp_that_is_there_but_cannot_load_is_the_same_case(self):
        s = Site(with_modules=False)
        self.addCleanup(s.close)
        os.makedirs(os.path.join(s.dir, "node_modules", "sharp"))
        with open(os.path.join(s.dir, "node_modules", "sharp", "package.json"), "w") as f:
            f.write('{"name":"sharp","version":"0.0.0","main":"index.js"}')
        with open(os.path.join(s.dir, "node_modules", "sharp", "index.js"), "w") as f:
            f.write('throw new Error("Could not load the sharp module using the darwin-arm64 runtime");')
        with self.assertRaises(Refusal) as cm:
            _render.Renderer(s.dir).preflight()
        self.assertEqual(cm.exception.code, "sharp-missing")
        self.assertIn("Could not load", str(cm.exception))
        self.assertIn("cannot make the icons on this computer", str(cm.exception))

    def test_no_node_at_all_is_said_in_words(self):
        s = Site(with_modules=False)
        self.addCleanup(s.close)
        with self.assertRaises(Refusal) as cm:
            _render.Renderer(s.dir, node="/nonexistent/node").preflight()
        self.assertEqual(cm.exception.code, "no-node")
        self.assertIn("Node", str(cm.exception))


class TheAnswerIsWholeBeforeTheHelperEnds(unittest.TestCase):
    """On Windows a line written to a pipe is still on its way when write() returns, and the helper used to call
    process.exit() right behind every answer. Here that delay is put on by hand (a small module loaded before the
    helper holds every write back for a moment): each way the helper can answer must still arrive whole."""

    SLOW_PIPE = ("const write = process.stdout.write.bind(process.stdout);\n"
                 "process.stdout.write = (chunk) => { setTimeout(() => write(chunk), 200); return true; };\n")

    def setUp(self):
        if not shutil.which("node"):
            self.skipTest("no node on this machine")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.slow = os.path.join(self.tmp.name, "slow-pipe.cjs")
        with open(self.slow, "w") as f:
            f.write(self.SLOW_PIPE)

    def answer(self, site, args=(), request=None):
        r = subprocess.run(["node", "--require", self.slow, _render.HELPER] + list(args), input=None if request is None else json.dumps(request),
                           cwd=site.dir, capture_output=True, text=True, timeout=120)
        lines = [line for line in r.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1, "one answer, whole: %r %r" % (r.stdout[:200], r.stderr[:300]))
        self.assertEqual(r.returncode, 0, r.stderr[:300])
        return json.loads(lines[0])

    def request(self, site, jobs, svg=None, **extra):
        req = {"svg": svg or MARK.replace("<svg ", '<svg width="1024" height="1024" ', 1), "viewBox": [0, 0, 64, 64], "intrinsic": 1024,
               "outDir": site.out, "jobs": jobs}
        req.update(extra)
        return req

    def test_the_helper_never_ends_itself(self):
        with open(_render.HELPER, encoding="utf-8") as f:
            code = "\n".join(line.split("//")[0] for line in f.read().splitlines())
        for call in ("process.exit(", "process.abort(", "process.kill(", "process.reallyExit("):
            self.assertNotIn(call, code)

    def test_no_sharp_is_answered_whole(self):
        s = Site(with_modules=False)
        self.addCleanup(s.close)
        for args, request in ((["--check"], None), ([], self.request(s, [job("a", 16)]))):
            answer = self.answer(s, args, request)
            self.assertEqual((answer["ok"], answer["error"]), (False, "sharp-missing"))

    def test_every_other_answer_is_whole_too(self):
        T.require_sharp(self)
        s = Site()
        self.addCleanup(s.close)
        self.assertEqual(sorted(self.answer(s, ["--check"])), ["node", "ok", "rsvg", "sharp"])
        drawn = self.answer(s, request=self.request(s, [job("a", 16), job("b", 32, 0.5, "#ffffff")]))
        self.assertEqual([(d["file"], d["width"]) for d in drawn["results"]], [("a.png", 16), ("b.png", 32)])
        self.assertTrue(os.path.exists(os.path.join(s.out, "b.png")))
        for name, request, error in (("a bad file name", self.request(s, [dict(job("a", 16), file="../x.png")]), "bad-job"),
                                     ("a bad size after a good job", self.request(s, [job("a", 16), dict(job("b", 16), size=0)]), "bad-job"),
                                     ("a bad box", self.request(s, [job("a", 16)], viewBox=[0, 0, 0, 5]), "bad-job"),
                                     ("a bad intrinsic size", self.request(s, [job("a", 16)], intrinsic=0), "bad-job"),
                                     ("text that is no drawing", self.request(s, [job("a", 16)], svg="<svg this is not xml"), "render-failed"),
                                     ("no jobs at all", self.request(s, None), "render-failed")):
            with self.subTest(name=name):
                answer = self.answer(s, request=request)
                self.assertEqual((answer["ok"], answer["error"]), (False, error), answer)
        # and a request that is not JSON at all
        r = subprocess.run(["node", "--require", self.slow, _render.HELPER], input="not json", cwd=s.dir, capture_output=True, text=True, timeout=120)
        self.assertEqual(json.loads(r.stdout)["error"], "render-failed")


def raw_request(site, jobs, svg=None, **extra):
    """Speak to render.mjs directly, past the wrapper: its own checks must hold alone."""
    req = {"svg": svg or MARK.replace("<svg ", '<svg width="1024" height="1024" ', 1), "viewBox": [0, 0, 64, 64], "intrinsic": 1024,
           "outDir": site.out, "jobs": jobs}
    req.update(extra)
    return subprocess.run(["node", _render.HELPER], input=json.dumps(req), cwd=site.dir, capture_output=True, text=True)


class Drawing(unittest.TestCase):
    def setUp(self):
        T.require_sharp(self)
        self.site = Site()
        self.addCleanup(self.site.close)
        self.r = _render.Renderer(self.site.dir)

    def draw(self, svg, view_box, jobs):
        return self.r.render(svg, view_box, jobs, self.site.out)

    def test_preflight_names_what_will_draw(self):
        info = self.r.preflight()
        self.assertTrue(info["sharp"] and info["rsvg"] and info["node"].startswith("v"))

    def test_the_sizes_asked_for_come_out(self):
        res = self.draw(MARK, (0, 0, 64, 64), [job("a", 32), job("b", 180, 0.8, "#fff8ee"), job("c", 512)])
        self.assertEqual({r["name"]: (r["width"], r["height"]) for r in res}, {"a": (32, 32), "b": (180, 180), "c": (512, 512)})
        for name, (w, h) in (("a", (32, 32)), ("b", (180, 180)), ("c", (512, 512))):
            self.assertEqual(_png.size(self.site.read(name + ".png")), (w, h))

    def test_a_background_makes_the_picture_opaque_and_none_leaves_it_see_through(self):
        res = self.draw(MARK, (0, 0, 64, 64), [job("solid", 64, 0.56, "#fff8ee"), job("clear", 64)])
        solid = _png.decode(self.site.read("solid.png"))
        clear = _png.decode(self.site.read("clear.png"))
        self.assertTrue(_png.is_opaque(solid))
        self.assertEqual(_png.at(solid, 0, 0), (0xff, 0xf8, 0xee, 255))
        self.assertEqual(_png.at(clear, 0, 0)[3], 0)
        self.assertFalse(_png.is_opaque(clear))

    def test_scale_sets_how_much_of_the_square_the_mark_takes(self):
        self.draw(MARK, (0, 0, 64, 64), [job("full", 256), job("small", 256, 0.5)])

        def extent(name):
            w, h, rgba = _png.decode(self.site.read(name + ".png"))
            xs = [i // 4 % w for i in range(3, len(rgba), 4) if rgba[i] > 128]
            return max(xs) - min(xs) + 1

        self.assertGreater(extent("full"), 2 * extent("small") - 12)
        self.assertLess(extent("small"), 0.5 * 256 + 2)

    def test_a_wide_mark_keeps_its_proportions_and_is_centred_in_the_square(self):
        # the OG generator stretches whatever it loads to 460 x 460, so logo.png is a square
        self.draw(WIDE, (0, 0, 100, 40), [job("logo", 512)])
        w, h, rgba = _png.decode(self.site.read("logo.png"))
        self.assertEqual((w, h), (512, 512))
        ys = [i // 4 // w for i in range(3, len(rgba), 4) if rgba[i] > 128]
        xs = [i // 4 % w for i in range(3, len(rgba), 4) if rgba[i] > 128]
        self.assertEqual((min(xs), max(xs)), (0, 511))
        self.assertAlmostEqual(max(ys) - min(ys) + 1, 205, delta=2)
        self.assertAlmostEqual((max(ys) + min(ys)) / 2, 255.5, delta=2)

    def test_the_marks_own_colours_come_out_exact(self):
        self.draw(MARK, (0, 0, 64, 64), [job("big", 256)])
        pic = _png.decode(self.site.read("big.png"))
        self.assertGreater(_png.count_colour(pic, "#b4531a"), 2000)
        self.assertGreater(_png.count_colour(pic, "#6b2c0b"), 500)

    def references(self):
        """Four drawings that each ask for another file, which is red: (name, svg text)."""
        red = os.path.join(self.site.dir, "red.png")
        with open(red, "wb") as f:
            f.write(T.make_png(20, 20, T.solid_rgba(20, 20, (255, 0, 0, 255))))
        css = os.path.join(self.site.dir, "red.css")
        with open(css, "w") as f:
            f.write("rect{fill:#ff0000}")
        base = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 20 20">%s</svg>'
        cases = {
            "href": '<image href="red.png" width="20" height="20"/>',
            "xlink": '<image xlink:href="red.png" width="20" height="20"/>',
            "file url": '<image href="file://%s" width="20" height="20"/>' % red,
            "import": '<style>@import url("red.css");</style><rect width="20" height="20" fill="#0000ff"/>',
        }
        return [(name, base % body) for name, body in cases.items()]

    def test_a_reference_to_another_file_is_never_followed(self):
        # measured on 2026-10-10 and again on 2026-10-11: from a PATH the renderer drew the
        # referenced file (400 red pixels of 400); from a BUFFER, none. The intake only ever
        # hands it a buffer, and these files are what a hostile SVG could ask for.
        for name, text in self.references():
            with self.subTest(name=name):
                self.draw(text, (0, 0, 20, 20), [job("probe", 20)])
                self.assertEqual(_png.count_colour(_png.decode(self.site.read("probe.png")), "#ff0000"), 0)

    def test_given_a_path_the_same_renderer_does_follow_each_of_those_references(self):
        # The control for the test above: without it, "no red pixel" could mean that this sharp never
        # follows a reference at all, and the test would prove nothing about buffers. Here the same four
        # drawings are read by the site's sharp from a file, the one thing render.mjs never does.
        from_a_path = "require('sharp')(process.argv[1]).png().toFile(process.argv[2]).catch((e) => { console.error(e.message); process.exit(1); })"
        for name, text in self.references():
            with self.subTest(name=name):
                probe, out = os.path.join(self.site.dir, "probe.svg"), os.path.join(self.site.dir, "followed.png")
                with open(probe, "w") as f:
                    f.write(text)
                r = subprocess.run(["node", "-e", from_a_path, probe, out], cwd=self.site.dir, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertGreater(_png.count_colour(_png.decode(T.read_bytes(out)), "#ff0000"), 300)

    def test_a_job_cannot_write_outside_the_folder_it_was_given(self):
        for bad in ("../x.png", "/tmp/x.png", "a/b.png", "x.png/..", "", ".hidden", "x y.png"):
            with self.subTest(file=bad):
                with self.assertRaises(Refusal) as cm:
                    self.draw(MARK, (0, 0, 64, 64), [dict(job("a", 16), file=bad)])
                self.assertEqual(cm.exception.code, "bad-job")
        self.assertFalse(os.path.exists(os.path.join(self.site.dir, "x.png")))

    def test_the_helper_itself_refuses_a_request_that_slips_past_the_wrapper(self):
        r = raw_request(self.site, [dict(job("a", 16), file="../escape.png")])
        self.assertIn('"ok":false', r.stdout.replace(" ", ""))
        self.assertIn("bad-job", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.site.dir, "escape.png")))
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.site.out), "escape.png")))
        # the same request with a good file name is fine, so the refusal was for the name
        ok = raw_request(self.site, [job("a", 16)])
        self.assertIn('"ok":true', ok.stdout.replace(" ", ""), ok.stdout + ok.stderr)

    def test_the_helper_checks_every_field_itself_not_only_the_wrapper(self):
        for bad in JobsAreChecked.BAD:
            with self.subTest(bad=bad):
                r = raw_request(self.site, [dict(job("a", 16), **bad)])
                self.assertIn('"ok":false', r.stdout.replace(" ", ""), r.stdout + r.stderr)
                self.assertIn("bad-job", r.stdout)
        for extra in (dict(intrinsic=0), dict(intrinsic=100000), dict(intrinsic="x"), dict(viewBox=[0, 0, 0, 5]), dict(viewBox=[0, 0, 5, -1])):
            with self.subTest(extra=extra):
                r = raw_request(self.site, [job("a", 16)], **extra)
                self.assertIn("bad-job", r.stdout, r.stdout + r.stderr)

    def test_a_job_without_a_background_is_refused_by_the_helper_as_by_the_wrapper(self):
        without = dict(job("a", 16))
        del without["background"]
        r = raw_request(self.site, [without])
        self.assertIn('"ok":false', r.stdout.replace(" ", ""), r.stdout + r.stderr)
        self.assertIn("bad-job", r.stdout)

    def test_the_mark_takes_the_share_of_its_square_that_was_asked_for_at_every_size(self):
        # The square always comes out the size asked for, so its size says nothing about the mark inside it.
        # Measured 2026-10-12 over 400 combinations: the mark's long side lands within half a pixel of
        # size x scale, except where that is under 14 pixels (sharp draws nothing smaller), where it stayed
        # 14 whatever the scale said. The helper now brings those down and fails if it ever misses by more than 1.
        asked = ((16, 1.0), (32, 1.0), (48, 0.25), (64, 0.1), (64, 0.5), (20, 0.5), (180, 0.8), (192, 0.56))
        for vb in ((0, 0, 64, 64), (0, 0, 100, 40), (0, 0, 3, 7)):
            svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s"><rect width="%s" height="%s" fill="#123456"/></svg>' % (vb[2:] + vb[2:])
            self.draw(svg, vb, [job("fit%d" % i, size, scale) for i, (size, scale) in enumerate(asked)])
            for i, (size, scale) in enumerate(asked):
                with self.subTest(vb=vb, size=size, scale=scale):
                    w, h, rgba = _png.decode(self.site.read("fit%d.png" % i))
                    self.assertEqual((w, h), (size, size))
                    # an edge pixel the mark half covers counts: a 100 x 40 mark at 16 is drawn 15 wide, centred
                    xs = [p // 4 % w for p in range(3, len(rgba), 4) if rgba[p] > 64]
                    ys = [p // 4 // w for p in range(3, len(rgba), 4) if rgba[p] > 64]
                    long_side = max(max(xs) - min(xs), max(ys) - min(ys)) + 1
                    self.assertAlmostEqual(long_side, size * scale, delta=1.5)

    def test_odd_shapes_always_fit_their_square(self):
        for vb in ((0, 0, 3, 7), (0, 0, 7, 3), (0, 0, 64.5, 64.5), (-5, -5, 33, 17), (0, 0, 0.5, 0.25), (0, 0, 1000, 999)):
            for size in (16, 32, 180, 192, 512):
                with self.subTest(vb=vb, size=size):
                    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s %s %s %s"><rect x="%s" y="%s" width="%s" height="%s" fill="#123456"/></svg>' % (
                        vb + (vb[0], vb[1], vb[2], vb[3]))
                    self.draw(svg, vb, [job("odd", size)])
                    self.assertEqual(_png.size(self.site.read("odd.png")), (size, size))

    def test_a_square_smaller_than_the_renderers_smallest_picture_still_comes_out_the_size_asked(self):
        # sharp will not draw below one dot per inch, so a 64-unit mark comes out 14 px wide first
        self.draw(MARK, (0, 0, 64, 64), [job("tiny", 8), job("one", 1)])
        self.assertEqual(_png.size(self.site.read("tiny.png")), (8, 8))
        self.assertEqual(_png.size(self.site.read("one.png")), (1, 1))

    def test_a_tall_mark_is_centred_across_as_well_as_down(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 40"><rect width="10" height="40" fill="#123456"/></svg>'
        self.draw(svg, (0, 0, 10, 40), [job("tall", 400)])
        w, h, rgba = _png.decode(self.site.read("tall.png"))
        xs = [i // 4 % w for i in range(3, len(rgba), 4) if rgba[i] > 128]
        self.assertAlmostEqual((min(xs) + max(xs)) / 2, 199.5, delta=1.5)
        self.assertAlmostEqual(max(xs) - min(xs) + 1, 100, delta=2)

    def test_the_opaque_ones_have_no_alpha_channel_and_the_see_through_ones_do(self):
        self.draw(MARK, (0, 0, 64, 64), [job("solid", 32, 1, "#fff8ee"), job("clear", 32)])
        self.assertEqual(self.site.read("solid.png")[25], 2, "colour type 2 is RGB: no alpha channel at all")
        self.assertEqual(self.site.read("clear.png")[25], 6, "colour type 6 is RGBA")

    def test_svg_text_that_is_not_xml_is_a_render_failure_not_a_crash(self):
        with self.assertRaises(Refusal) as cm:
            self.draw("<svg", (0, 0, 64, 64), [job("a", 16)])
        self.assertIn(cm.exception.code, ("render-failed", "bad-job"))


# Draws each SVG text it is given (a JSON list on standard input) from a Buffer, stretched onto 64 x 64 white, and
# prints for each the colours that cover at least 1 % of it: {"#rrggbb": pixels}, or {"error": ...}.
_COLOURS_DRAWN = r"""
const sharp = require('sharp');
(async () => {
  const out = [];
  for (const svg of JSON.parse(require('fs').readFileSync(0, 'utf8'))) {
    try {
      const data = await sharp(Buffer.from(svg, 'utf8')).resize(64, 64, { fit: 'fill' }).flatten({ background: '#ffffff' }).removeAlpha().raw().toBuffer();
      const seen = {};
      for (let i = 0; i < data.length; i += 3) {
        const hex = '#' + [data[i], data[i + 1], data[i + 2]].map((x) => x.toString(16).padStart(2, '0')).join('');
        seen[hex] = (seen[hex] || 0) + 1;
      }
      out.push(Object.fromEntries(Object.entries(seen).filter(([, n]) => n >= 41)));
    } catch (e) { out.push({ error: String(e.message).split('\n')[0].slice(0, 100) }); }
  }
  console.log(JSON.stringify(out));
})();
"""


# Draws SVG texts as icons and compares them pixel by pixel. Standard input: {sizes, same, far, rows: [{texts, pairs}]}.
# Each text is drawn from a Buffer at each size the way an icon is: its long side on `size` pixels, in the middle of a
# see-through square. A pair [i, j] of a row's texts is then compared pixel by pixel, each pixel as its colour times
# its opacity (so a see-through pixel is the same pixel whatever colour it carries). Standard output, for each row:
# {errors: [per text, per size: null or why it was not drawn], pairs: [per pair, per size: {max, over, far} or null]},
# where `max` is the largest difference in any channel of any pixel, `over` the pixels that differ by more than `same`
# and `far` those that differ by more than `far`.
_PICTURES = r"""
const sharp = require('sharp');
sharp.cache(false);
sharp.concurrency(1);
const longSide = async (buf, density) => { const m = await sharp(buf, { density }).metadata(); return Math.max(m.width, m.height); };
async function picture(svg, size) {
  const buf = Buffer.from(svg, 'utf8');
  // The density at which the long side is `size` pixels is found by measuring: a size is rounded to whole pixels, and
  // an outer svg sized in mm or in grows with the square of the density, not with the density. A very large or a
  // very small box cannot be measured at 72 dots an inch at all, and is measured at another density first.
  let density = null, got = null, failed = null;
  for (const at of [72, 1, 100000]) {
    try { got = await longSide(buf, at); density = at; break; } catch (e) { failed = e; }
  }
  if (density === null) throw failed;
  let power = 1;
  for (let turn = 0; turn < 6 && got !== size; turn++) {
    const next = Math.min(100000, Math.max(1, density * Math.pow(size / got, 1 / power)));
    if (next === density) break;
    const then = await longSide(buf, next);
    if (then !== got && got > 16 && Math.log(then / got) / Math.log(next / density) > 1.5) power = 2;
    density = next; got = then;
  }
  const { data, info } = await sharp(buf, { density }).resize(size, size, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  if (info.width !== size || info.height !== size) throw new Error('came out ' + info.width + ' by ' + info.height);
  for (let i = 0; i < data.length; i += 4) for (let c = 0; c < 3; c++) data[i + c] = Math.round((data[i + c] * data[i + 3]) / 255);
  return data;
}
(async () => {
  const req = JSON.parse(require('fs').readFileSync(0, 'utf8'));
  const out = req.rows.map((row) => ({ errors: row.texts.map(() => []), pairs: row.pairs.map(() => []) }));
  for (const size of req.sizes) {
    let known = new Map(); // the same text is drawn once: many rows share the text they are held against
    for (let r = 0; r < req.rows.length; r++) {
      const row = req.rows[r];
      const drawn = [];
      for (let t = 0; t < row.texts.length; t++) {
        let p = known.get(row.texts[t]);
        if (p === undefined) {
          try { p = await picture(row.texts[t], size); } catch (e) { p = String(e && e.message).split('\n')[0].slice(0, 120); }
          if (known.size > 40) known = new Map();
          known.set(row.texts[t], p);
        }
        drawn.push(p);
        out[r].errors[t].push(typeof p === 'string' ? p : null);
      }
      row.pairs.forEach(([i, j], n) => {
        const a = drawn[i], b = drawn[j];
        if (typeof a === 'string' || typeof b === 'string') { out[r].pairs[n].push(null); return; }
        let max = 0, over = 0, far = 0;
        for (let k = 0; k < a.length; k += 4) {
          const d = Math.max(Math.abs(a[k] - b[k]), Math.abs(a[k + 1] - b[k + 1]), Math.abs(a[k + 2] - b[k + 2]), Math.abs(a[k + 3] - b[k + 3]));
          if (d > max) max = d;
          if (d > req.same) over++;
          if (d > req.far) far++;
        }
        out[r].pairs[n].push({ max, over, far });
      });
    }
  }
  console.log(JSON.stringify(out));
})();
"""
SIZES = (32, 512)   # a small icon and a large one: the renderer sized some values by the icon it was drawing
SAME = 2            # two pictures are the same when no channel of any pixel differs by more than this (of 255): the
                    # rounding of a colour to a hex, and nothing that could be seen
FAR = 32            # and they differ when more than a quarter of the icon's side in pixels differ by more than this


def pictures(testcase, site_dir, rows):
    """Draw and compare `rows` ([{texts, pairs}]) at every size; see _PICTURES."""
    r = subprocess.run(["node", "-e", _PICTURES], input=json.dumps({"sizes": SIZES, "same": SAME, "far": FAR, "rows": rows}), cwd=site_dir,
                       capture_output=True, text=True, timeout=1800)
    testcase.assertEqual(r.returncode, 0, r.stderr[-400:])
    return json.loads(r.stdout)


def all_drawn(testcase, answer, what):
    for t, per_size in enumerate(answer["errors"]):
        for size, error in zip(SIZES, per_size):
            testcase.assertIsNone(error, "%s: text %d was not drawn at %d pixels (%s)" % (what, t, size, error))


def the_same(testcase, pair, what):
    for size, got in zip(SIZES, pair):
        testcase.assertEqual(got["over"], 0, "%s: at %d pixels %d pixels differ, by up to %d of 255" % (what, size, got["over"], got["max"]))


def not_the_same(testcase, pair, what):
    for size, got in zip(SIZES, pair):
        testcase.assertGreater(got["far"], size // 4, "%s: at %d pixels only %d pixels differ" % (what, size, got["far"]))


class WhatIsAcceptedIsDrawnAsItWas(unittest.TestCase):
    """The check reads a file with its own reader of numbers, colours and styles; the site draws it with a renderer
    that has its own. Wherever the two could read a value differently the check must refuse, because it writes ITS
    reading into the cleaned file and lists ITS colours. So for every way of writing a value: the file is refused, or
    the cleaned file is drawn as the original was (pixel for pixel, both of them drawn, at a small size and a large
    one) and no colour is drawn that the check did not list."""

    BOX = 'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"'
    RECT = '<rect width="10" height="10"/>'

    def setUp(self):
        T.require_sharp(self)
        self.site = Site()
        self.addCleanup(self.site.close)

    def drawn(self, texts):
        r = subprocess.run(["node", "-e", _COLOURS_DRAWN], input=json.dumps(texts), cwd=self.site.dir, capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        return json.loads(r.stdout)

    def judge(self, documents):
        """{name: "refused: code" or "accepted"}, after holding every accepted document to the rule above."""
        outcome, pairs = {}, []
        for name, text in documents.items():
            try:
                clean = _svg.clean_svg(text.encode("utf-8"))
            except Refusal as e:
                outcome[name] = "refused: " + e.code
            else:
                outcome[name] = "accepted"
                pairs.append((name, text, clean))
        # where each thing is, not only how much of each colour there is: a shape that had moved kept its colours
        compared = pictures(self, self.site.dir, [{"texts": [text, clean.text], "pairs": [[0, 1]]} for _n, text, clean in pairs])
        listed = self.drawn([clean.text for _n, _text, clean in pairs])
        for (name, _text, clean), answer, now in zip(pairs, compared, listed):
            with self.subTest(name=name):
                all_drawn(self, answer, name)
                the_same(self, answer["pairs"][0], name)
                self.assertNotIn("error", now, "the cleaned file must draw")
                for colour in now:
                    self.assertTrue(any(self.a_tint_of(colour, listed) for listed in clean.colours),
                                    "%s is drawn, and the check listed only %r" % (colour, clean.colours))
        return outcome

    @staticmethod
    def a_tint_of(colour, listed):
        """Is `colour` the listed colour, or that colour thinned towards the white paper (the soft edge of a shape)?"""
        c, l = [int(colour[i:i + 2], 16) for i in (1, 3, 5)], [int(listed[i:i + 2], 16) for i in (1, 3, 5)]
        if c == [255, 255, 255]:
            return True
        shares = [(255 - c[i]) / (255 - l[i]) for i in range(3) if l[i] != 255]
        share = shares[0] if shares else 0
        return 0 < share <= 1.01 and all(abs((255 - l[i]) * share - (255 - c[i])) <= 3 for i in range(3))

    def test_a_shape_that_has_moved_is_not_drawn_as_it_was(self):
        # the comparison itself: before 2026-10-12 it counted colours, so a red half that had changed sides passed
        b = self.BOX
        left = '<svg %s><rect fill="#f00" width="5" height="10"/></svg>' % b
        right = '<svg %s><rect fill="#f00" x="5" width="5" height="10"/></svg>' % b
        nudged = '<svg %s><rect fill="#f00" x="0.2" width="5" height="10"/></svg>' % b
        broken = '<svg %s><rect fill="#f00" width="5" height="10"></svg>' % b
        answer = pictures(self, self.site.dir, [{"texts": [left, right, nudged, left + " ", broken], "pairs": [[0, 1], [0, 2], [0, 3], [0, 4]]}])[0]
        self.assertEqual(self.drawn([left])[0], self.drawn([right])[0], "the two do hold the same colours")
        not_the_same(self, answer["pairs"][0], "left and right")
        for size, got in zip(SIZES, answer["pairs"][1]):
            self.assertGreater(got["over"], 0, "a fifth of a unit to the side is seen at %d pixels" % size)
        the_same(self, answer["pairs"][2], "the same drawing twice")
        self.assertEqual(answer["pairs"][3], [None, None], "what was not drawn is the same as nothing")
        with self.assertRaises(AssertionError):
            all_drawn(self, answer, "a drawing that is no XML")
        with self.assertRaises(AssertionError):
            the_same(self, answer["pairs"][0], "left and right")

    def test_every_way_of_writing_a_number(self):
        b = self.BOX
        forms = ["5", "5.0", ".5e1", "5e0", "+5", "05", "5.00e0", "5.", "5.e0", "+5.", "5.px", "5.0px", "5px", "5 ", " 5", "5\u00a0", "\u00a05", "\u0665", "5,"]
        zeros = ["0", "0.0", ".0", "0e0", "-0", "0.", "0.e0", "0.px", "+0.", "\u0660"]
        docs = {}
        for f in forms:
            docs["rect width=%r" % f] = '<svg %s><rect fill="#f00" width="%s" height="10"/></svg>' % (b, f)
            docs["rect x=%r" % f] = '<svg %s><rect x="%s" fill="#f00" width="10" height="10"/></svg>' % (b, f)
            docs["circle r=%r" % f] = '<svg %s><circle fill="#f00" cx="5" cy="5" r="%s"/></svg>' % (b, f)
            docs["ellipse rx=%r" % f] = '<svg %s><ellipse fill="#f00" cx="5" cy="5" rx="%s" ry="5"/></svg>' % (b, f)
            docs["line x2=%r" % f] = '<svg %s><line stroke="#f00" stroke-width="10" y1="5" y2="5" x2="%s"/></svg>' % (b, f)
            docs["stroke-width=%r" % f] = '<svg %s><path stroke="#f00" stroke-width="%s" d="M0 5h10"/></svg>' % (b, f)
            docs["style stroke-width:%r" % f] = '<svg %s><path stroke="#f00" style="stroke-width:%s" d="M0 5h10"/></svg>' % (b, f)
            docs["rule stroke-width:%r" % f] = '<svg %s><style>path{stroke-width:%s}</style><path stroke="#f00" d="M0 5h10"/></svg>' % (b, f)
            docs["points %r" % f] = '<svg %s><polygon fill="#f00" points="0,0 %s,0 %s,10 0,10"/></svg>' % (b, f, f)
            docs["translate(%r)" % f] = '<svg %s><rect transform="translate(%s 0)" fill="#f00" width="10" height="10"/></svg>' % (b, f)
            docs["scale(1 %r)" % f] = '<svg %s><rect transform="scale(.1 %s)" fill="#f00" width="100" height="1"/></svg>' % (b, f)
            docs["dasharray %r" % f] = '<svg %s><path stroke="#f00" stroke-width="10" stroke-dasharray="%s" d="M0 5h10"/></svg>' % (b, f)
            docs["dashoffset %r" % f] = '<svg %s><path stroke="#f00" stroke-width="10" stroke-dasharray="5" stroke-dashoffset="%s" d="M0 5h10"/></svg>' % (b, f)
            docs["miterlimit %r" % f] = '<svg %s><path fill="none" stroke="#f00" stroke-width="3" stroke-miterlimit="%s" d="M1 9L5 2L9 9"/></svg>' % (b, f)
            docs["viewBox width %r" % f] = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 %s 5"><rect fill="#f00" width="2.5" height="5"/></svg>' % f
            docs["no viewBox, width %r" % f] = '<svg xmlns="http://www.w3.org/2000/svg" width="%s" height="5"><rect fill="#f00" width="2.5" height="5"/></svg>' % f
            docs["path data h%r" % f] = '<svg %s><path fill="#f00" d="M0 0h%sv10h-5z"/></svg>' % (b, f.replace("px", ""))
        for z in zeros:
            docs["no stroke: stroke-width=%r" % z] = '<svg %s><path stroke="#f00" stroke-width="%s" d="M0 5h10"/><rect fill="#00f" width="3" height="3"/></svg>' % (b, z)
            docs["no stroke: style %r" % z] = '<svg %s><path stroke="#f00" style="stroke-width:%s" d="M0 5h10"/><rect fill="#00f" width="3" height="3"/></svg>' % (b, z)
            docs["opacity %r" % z] = '<svg %s><rect fill="#f00" opacity="%s" width="10" height="10"/><rect fill="#00f" width="3" height="3"/></svg>' % (b, z)
        for o in ["1", "1.0", "1.", "1.e0", "100%", "100.%", "+1", "1e0", "\u0661"]:
            docs["opacity %r" % o] = '<svg %s><rect fill="#f00" opacity="%s" width="10" height="10"/></svg>' % (b, o)
            docs["style fill-opacity %r" % o] = '<svg %s><rect fill="#f00" style="fill-opacity:%s" width="10" height="10"/></svg>' % (b, o)
        for d in ["5 1", "5,1", "50% 10%", "50%10%", "5.0 1.0", "5. 1", "5 1.", "5%%", "5-1", "5.5.5", ""]:
            docs["dasharray %r" % d] = '<svg %s><path stroke="#f00" stroke-width="10" stroke-dasharray="%s" d="M0 5h10"/></svg>' % (b, d)
        outcome = self.judge(docs)
        # the forms a renderer does not read as this check would are refused, not passed on
        for f in ("5.", "5.e0", "+5.", "5.px", "5\u00a0", "\u00a05", "\u0665"):
            for name in ("rect width=%r", "circle r=%r", "stroke-width=%r", "style stroke-width:%r", "rule stroke-width:%r", "points %r", "translate(%r)",
                         "dasharray %r", "viewBox width %r", "no viewBox, width %r"):
                self.assertTrue(outcome[name % f].startswith("refused"), (name % f, outcome[name % f]))
        for z in ("0.", "0.e0", "0.px", "+0.", "\u0660"):
            self.assertEqual(outcome["no stroke: stroke-width=%r" % z], "refused: bad-value")
            self.assertEqual(outcome["no stroke: style %r" % z], "refused: bad-value")
        # and the test is not empty-handed: the ordinary ways of writing a number are accepted and drawn alike
        for f in ("5", "5.0", ".5e1", "5e0", "+5", "05"):
            for name in ("rect width=%r", "rect x=%r", "circle r=%r", "stroke-width=%r", "style stroke-width:%r", "points %r", "translate(%r)",
                         "dasharray %r", "dashoffset %r", "viewBox width %r", "no viewBox, width %r", "path data h%r"):
                self.assertEqual(outcome[name % f], "accepted", name % f)
        for f in ("5.", "5.e0"):
            self.assertEqual(outcome["path data h%r" % f], "accepted", "in path data a renderer reads it, so it is kept")
        self.assertGreater(list(outcome.values()).count("accepted"), 100)

    def test_every_way_of_hiding_a_colour_from_the_check_or_from_the_renderer(self):
        b, rect = self.BOX, self.RECT
        sheets = {
            "a plain rule": "rect{fill:#f00}", "a font's name in quotes": 'g{font-family:"Helvetica Neue"} rect{fill:#f00}',
            "a comment": "/* red */ rect{fill:#f00}", "a rule in a quoted brace": 'g{font-family:"} rect{fill:#f00} g{font-family:"}',
            "single quotes": "g{font-family:'} rect{fill:#f00} g{font-family:'}", "an escaped quote": 'g{font-family:"a\\"} rect{fill:#f00} g{font-family:"}',
            "a line break in quotes": 'g{font-family:"a&#13;/*"} rect{fill:#f00} g{font-family:"*/"}',
            "a value in quotes": 'rect{font-family:"a;fill:#f00;cursor:b"}', "brackets": "g{cursor:x(} rect{fill:#f00} g{cursor:)}",
            "a value in brackets": "rect{cursor:x(a;fill:#f00;cursor:b)}", "square brackets": "rect{cursor:[a;fill:#f00;cursor:b]}",
            "an escaped hash": "rect{fill:\\23 f00}", "an escaped letter in a hash": "rect{fill:#\\66 00}", "escaped brackets": "rect{fill:rgb\\28 255,0,0\\29 }",
            "escaped commas": "rect{fill:rgb(255\\2c 0\\2c 0)}", "an escaped letter": "rect{fill:r\\65 d}", "an escaped property": "rect{f\\69ll:#f00}",
            "a no-break space before the property": "rect{\u00a0fill:#f00}", "a Kelvin sign": "rect{stro\u212ae:#f00;stroke-width:6}",
            "a no-break space before the selector": "\u00a0rect{fill:#f00}", "a no-break space before the value": "rect{fill:\u00a0red}",
            "another script's digits": "rect{fill:rgb(\u0662\u0665\u0665,0,0)}", "a name twice": ".a.a{fill:#f00} .b{fill:#00f}",
            "an id and a class": "#i{fill:#f00} .a.b{fill:#00f}", "the later of two": "rect{fill:#00f} rect{fill:#f00}",
            "a carriage return after an escape": "rect{fi\\6c&#13;&#10;l:#f00}", "capitals": "RECT{FILL:#F00}", "a capital property": "rect{FILL:#f00}",
        }
        docs = {"sheet: " + name: '<svg %s><style>%s</style><g>%s</g></svg>' % (b, css, rect.replace("<rect ", '<rect id="i" class="a b" ')) for name, css in sheets.items()}
        styles = {
            "plain": "fill:#f00", "quotes": 'font-family:"a;fill:#f00;cursor:b"', "single quotes": "font-family:&#39;a;fill:#f00;cursor:b&#39;",
            "an escaped quote": 'font-family:"a\\";fill:#f00;cursor:"', "brackets": "cursor:x(a;fill:#f00;cursor:b)", "square brackets": "cursor:[a;fill:#f00;cursor:b]",
            "braces": "cursor:{a;fill:#f00;cursor:b}", "an escaped hash": "fill:\\23 f00", "an escaped semicolon": "fill:#00f\\3b fill:#f00",
            "a no-break space": "fill:\u00a0red", "a no-break space before the property": "\u00a0fill:#f00", "a font's name": "font-family:&#39;Arial&#39;;fill:#f00", "capitals": "FILL:#f00",
        }
        for name, css in styles.items():
            docs["style: " + name] = "<svg %s><rect style='%s' width='10' height='10'/></svg>" % (b, css)
        attributes = {
            "plain": 'fill="red"', "a point with a digit": 'fill="rgb(255.0,.0,0.0)"', "a bare point": 'fill="rgb(255.,0,0)"', "a bare point in hsl": 'fill="hsl(0.,100%,50%)"',
            "a bare point before a percent": 'fill="rgb(100.%,0%,0%)"', "a name in capitals": 'fill="RED"', "a hex in capitals": 'fill="#F00"', "rgb in capitals": 'fill="RGB(255,0,0)"',
            "none in capitals": 'fill="NONE" stroke="#f00" stroke-width="20"', "inherit in capitals": 'fill="INHERIT"', "hidden in capitals": 'fill="#f00" visibility="HIDDEN"',
            "currentColor in small letters": 'fill="currentcolor" color="#f00"', "currentColor in capitals": 'fill="CURRENTCOLOR" color="#f00"',
            "a stroke of none in capitals": 'fill="#f00" stroke="None" stroke-width="20"', "display none in capitals": 'fill="#f00" display="None"',
            "a no-break space before": 'fill="\u00a0red"', "an em space after": 'fill="red\u2003"', "another script's digits": 'fill="rgb(\u0662\u0665\u0665,0,0)"',
            "full-width letters": 'fill="\uff52\uff45\uff44"', "plain spaces": 'fill=" red "', "an id with a space": 'id=" i" class="x"', "an id": 'id="i" class="x"',
            "a class after an em space": 'class="\u2003a" id="x"', "two classes round a no-break space": 'class="a\u00a0b" id="x"',
            "a clip": 'fill="#f00" clip-path="url(#c)"', "a clip after an em space": 'fill="#f00" clip-path="url(\u2003#c)"', "a clip in quotes": 'fill="#f00" clip-path="url(&quot;#c&quot;)"',
        }
        for name, attrs in attributes.items():
            docs["attribute: " + name] = ('<svg %s><style>#i{fill:#f00} .a{fill:#f00}</style><defs><clipPath id="c"><rect width="5" height="10"/></clipPath></defs>'
                                          '<rect %s width="10" height="10"/></svg>' % (b, attrs))
        boxes = {"plain": "0 0 20 20", "commas": "0,0,20,20", "an em space": "0\u20030 20 20", "a no-break space": "0 0\u00a020 20", "a point": "0 0 20. 20", "a tab": "0\t0 20 20"}
        for name, box in boxes.items():
            docs["viewBox: " + name] = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="%s"><rect fill="#f00" width="10" height="10"/></svg>' % box
        outcome = self.judge(docs)
        for name in ("sheet: a plain rule", "sheet: a font's name in quotes", "sheet: a comment", "sheet: a name twice", "sheet: an id and a class", "sheet: the later of two",
                     "style: plain", "style: a font's name", "attribute: plain", "attribute: plain spaces", "attribute: an id", "attribute: a clip", "attribute: a point with a digit", "viewBox: plain",
                     "viewBox: commas", "viewBox: a tab"):
            self.assertEqual(outcome[name], "accepted", name)
        for name in ("sheet: a rule in a quoted brace", "sheet: single quotes", "sheet: an escaped quote", "sheet: a line break in quotes", "sheet: a value in quotes",
                     "sheet: brackets", "sheet: a value in brackets", "sheet: square brackets", "sheet: an escaped hash", "sheet: an escaped letter in a hash",
                     "sheet: escaped brackets", "sheet: escaped commas", "sheet: an escaped letter", "sheet: an escaped property", "sheet: a no-break space before the property",
                     "sheet: a Kelvin sign", "sheet: a no-break space before the selector", "sheet: a carriage return after an escape", "style: quotes",
                     "style: single quotes", "style: an escaped quote", "style: brackets", "style: square brackets", "style: braces", "style: an escaped hash",
                     "style: an escaped semicolon", "style: a no-break space before the property", "style: capitals", "sheet: a capital property"):
            self.assertEqual(outcome[name], "refused: css-unreadable", name)
        for name in ("sheet: a no-break space before the value", "sheet: another script's digits", "style: a no-break space", "attribute: a no-break space before",
                     "attribute: an em space after", "attribute: another script's digits", "attribute: full-width letters", "attribute: an id with a space",
                     "attribute: a class after an em space", "attribute: two classes round a no-break space", "attribute: a clip in quotes"):
            self.assertEqual(outcome[name], "refused: bad-value", name)
        for name in ("attribute: a bare point", "attribute: a bare point in hsl", "attribute: a bare point before a percent"):
            self.assertEqual(outcome[name], "refused: colour-unreadable", name)  # the colour reader's own refusal, by name
        self.assertEqual(outcome["attribute: a clip after an em space"], "refused: css-url")
        for name in ("viewBox: an em space", "viewBox: a no-break space", "viewBox: a point"):
            self.assertEqual(outcome[name], "refused: bad-view-box", name)


# --- the value grammar, drawn ----------------------------------------------------------------------
# One row for every form of every line of the value grammar (_svg.py, at its top). A row is
# (line, what, the drawing with the form in it, the same drawing with the value written the plainest way or None,
#  the same drawing with another value or None).

B = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10" fill="#00f"/>%s</svg>'
GIVEN_A_SIZE = " (given a size, as the renderer is given the cleaned file)"
FIVE = ["5", "5.0", ".5e1", "5e0", "+5", "05", "5E0", "50e-1", "0.5e+1", "0.05e02", "5.00e00", " 5 ", "&#9;5&#10;"]   # the number five
FIVE_PX = ["5px", "5.0px", ".5e1px", "+5px", " 5px "]
HALF = ["50%", "50.0%", "+50%", "5e1%", ".5e2%", " 50% "]   # half of a box ten wide and ten high: five
ONE = ["1", "1.0", "+1", "1e0", "10e-1", "0.1e1", "1.00e00", "01", " 1 "]
SHAPES = {   # attribute: (the shape it is tried on, a value that is not five)
    "x": ('<rect x="%s" width="4" height="4" fill="#f00"/>', "1"), "y": ('<rect y="%s" width="4" height="4" fill="#f00"/>', "1"),
    "width": ('<rect width="%s" height="4" fill="#f00"/>', "1"), "height": ('<rect width="4" height="%s" fill="#f00"/>', "1"),
    "cx": ('<circle cx="%s" cy="5" r="3" fill="#f00"/>', "1"), "cy": ('<circle cx="5" cy="%s" r="3" fill="#f00"/>', "1"),
    "r": ('<circle cx="5" cy="5" r="%s" fill="#f00"/>', "1"),
    "rx": ('<rect width="10" height="10" rx="%s" fill="#f00"/>', "1"), "ry": ('<rect width="10" height="10" rx="2" ry="%s" fill="#f00"/>', "1"),
    "rx of an ellipse": ('<ellipse cx="5" cy="5" rx="%s" ry="2" fill="#f00"/>', "1"), "ry of an ellipse": ('<ellipse cx="5" cy="5" rx="2" ry="%s" fill="#f00"/>', "1"),
    "x1": ('<line x1="%s" y1="1" x2="9" y2="9" stroke="#f00" stroke-width="2"/>', "1"), "y1": ('<line x1="1" y1="%s" x2="9" y2="9" stroke="#f00" stroke-width="2"/>', "1"),
    "x2": ('<line x1="1" y1="1" x2="%s" y2="9" stroke="#f00" stroke-width="2"/>', "1"), "y2": ('<line x1="1" y1="1" x2="9" y2="%s" stroke="#f00" stroke-width="2"/>', "1"),
}
POSITIONS = ("x", "y", "cx", "cy", "x1", "y1", "x2", "y2", "width", "height")
# A property is tried the hard way: one rule sets another value first and the form after it. A renderer that cannot
# read the form keeps the other value, and the cleaned file (which holds the form alone) would then be drawn differently.
MITRE = '<path class="p" d="M1 9L5 2L9 9" fill="none" stroke="#f00" stroke-width="2"/>'
LINE = '<path class="p" d="M0 5H10" stroke="#f00" stroke-width="4"/>'
SQUARE = '<rect class="p" width="6" height="6" fill="#f00"/>'
HOLE = '<path class="p" d="M1 1h8v8h-8zM3 3h4v4h-4z" fill="#f00"/>'
CLIPS = ('<clipPath id="c"><rect width="3" height="10"/></clipPath><clipPath id="d-e.f:g_h"><rect width="3" height="10"/></clipPath>'
         '<rect class="p" width="10" height="10" fill="#f00"/>')
PROPERTIES = {   # property: (the shape, the other value)
    "stroke-width": ('<path class="p" d="M0 5H10" stroke="#f00"/>', "1"), "stroke-miterlimit": (MITRE, "1.5"),
    "stroke-dashoffset": ('<path class="p" d="M0 5H10" stroke="#f00" stroke-width="4" stroke-dasharray="7"/>', "1"),
    "opacity": (SQUARE, ".3"), "fill-opacity": (SQUARE, ".3"), "stroke-opacity": (LINE, ".3"), "stroke-dasharray": (LINE, "1 1"),
}


def in_a_rule(prop, shape, value, other):
    return B % ("<style>.p{%s:%s;%s:%s}</style>%s" % (prop, other, prop, value, shape))


def grammar_rows():
    rows = []

    def attribute(line, name, forms, plain="5"):
        shape, other = SHAPES[name]
        for form in forms:
            rows.append((line, "%s=%r" % (name, form), B % (shape % form), B % (shape % plain), B % (shape % other)))

    def rule(line, prop, forms, plain, other=None, shape=None):
        shape, other = shape or PROPERTIES[prop][0], other or PROPERTIES[prop][1]
        for form in forms:
            form, same_as = form if isinstance(form, tuple) else (form, plain)
            rows.append((line, "%s: %s" % (prop, form), in_a_rule(prop, shape, form, other),
                         in_a_rule(prop, shape, same_as, other) if same_as is not None else None, in_a_rule(prop, shape, other, other)))

    # --- number
    rule("number", "stroke-miterlimit", FIVE + ["100", ("1e9", None)], "5")
    rule("number", "stroke-miterlimit", ["1", "1.0", "1e0"], "1", other="8")   # the least there is
    for prop in ("opacity", "fill-opacity", "stroke-opacity"):
        rule("number", prop, ONE, "1")
    # --- length
    rule("length", "stroke-width", FIVE + FIVE_PX + [("0", "0"), ("0.0", "0"), ("0e9", "0"), ("0px", "0"), ("1e9", "1000000000")], "5")
    rule("length", "stroke-dashoffset", FIVE + FIVE_PX + [("-5", "9"), ("0", "14"), ("-.5e1px", "9")], "5")
    for name in ("r", "rx", "ry", "rx of an ellipse", "ry of an ellipse"):
        attribute("length", name, FIVE + FIVE_PX)
    rows.append(("length", "rx='auto' beside an ry", B % '<rect width="10" height="10" rx="auto" ry="3" fill="#f00"/>',
                 B % '<rect width="10" height="10" rx="3" ry="3" fill="#f00"/>', B % '<rect width="10" height="10" fill="#f00"/>'))
    rows.append(("length", "ry='auto' beside an rx", B % '<rect width="10" height="10" rx="3" ry="auto" fill="#f00"/>',
                 B % '<rect width="10" height="10" rx="3" ry="3" fill="#f00"/>', B % '<rect width="10" height="10" fill="#f00"/>'))
    # --- position
    for name in POSITIONS:
        attribute("position", name, FIVE + FIVE_PX + HALF)
    for name in ("x", "y", "cx", "x1"):
        shape, _other = SHAPES[name]
        for form in ("-5", "-.5e1", "-5px", "-50%"):
            rows.append(("position", "%s=%r" % (name, form), B % (shape % form), B % (shape % "-5"), B % (shape % "1")))
        rows.append(("position", "%s='1e9'" % name, B % (shape % "1e9"), B % (shape % "1000000000"), B % (shape % "1")))
    wide = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 10"><rect width="20" height="10" fill="#00f"/>%s</svg>'
    for name, plain in (("x", "10"), ("width", "10"), ("cx", "10"), ("x2", "10"), ("y", "5"), ("height", "5"), ("cy", "5"), ("y2", "5")):
        shape, _other = SHAPES[name]   # a share is of the box's width for x and of its height for y
        rows.append(("position", "%s='50%%' in a box 20 by 10" % name, wide % (shape % "50%"), wide % (shape % plain), wide % (shape % "1")))
    no_box = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10"><rect width="20" height="10" fill="#00f"/>%s</svg>'
    rows.append(("position", "a share where the box is the width and height", no_box % '<rect width="50%" height="50%" fill="#f00"/>',
                 no_box % '<rect width="10" height="5" fill="#f00"/>', no_box % '<rect width="1" height="1" fill="#f00"/>'))
    # --- number list
    poly, three = '<polygon points="%s" fill="#f00"/>', "1 1 9 1 5 9"
    for form in ("1 1 9 1 5 9", "1,1 9,1 5,9", "1,1,9,1,5,9", "1 , 1 9 , 1 5 , 9", " 1 1 9 1 5 9 ", "1&#10;1&#9;9&#13;1  5 9", "+1 +1 +9 +1 +5 +9", "1e0 1E0 .9e1 1.0 5 9",
                 "1 1 9 1 5 9 1 1"):
        rows.append(("number list", "points=%r" % form, B % (poly % form), B % (poly % three), B % (poly % "1 1 9 1 5 5")))
    rows.append(("number list", "points run together before a sign", B % (poly % "1 1 9 1 5-1"), B % (poly % "1 1 9 1 5 -1"), B % (poly % three)))
    rows.append(("number list", "points run together before a point", B % (poly % "1 1 9 1 5.5.9"), B % (poly % "1 1 9 1 5.5 .9"), B % (poly % three)))
    rows.append(("number list", "points='' draws nothing", B % (poly % ""), B % "", B % (poly % three)))
    rule("number list", "stroke-dasharray", ["3 1", "3,1", "3 , 1", "3  1", "3.0 1e0", "+3 +1", "3 1 3 1", ("3", "3 3"), ("3 1 2", "3 1 2 3 1 2"), ("3.5.5", "3.5 .5"),
                                             ("3+1", "3 1"), ("none", "none"), ("0 0", "none"), ("0", "none"), ("1e9", "none"), ("3 1 " * 8, "3 1")], "3 1")
    dashed = '<path d="M0 5H10" stroke="#f00" stroke-width="4" stroke-dasharray="%s"/>'
    for form in ("3&#9;1", "3&#10;1", "&#13;3 1 ", "3&#10;,&#9;1"):
        rows.append(("number list", "stroke-dasharray=%r" % form, B % (dashed % form), B % (dashed % "3 1"), B % (dashed % "1 1")))
    # --- transform
    moved = '<rect transform="%s" width="4" height="4" fill="#f00"/>'
    for form, plain in (("translate(2)", "translate(2 0)"), ("translate(2 3)", None), ("translate(2,3)", "translate(2 3)"), ("translate( 2 , 3 )", "translate(2 3)"),
                        ("translate(2-3)", "translate(2 -3)"), ("translate(.5.5)", "translate(.5 .5)"), ("translate(2e0 +3E0)", "translate(2 3)"),
                        ("translate(&#10;2&#9;3&#13;)", "translate(2 3)"), ("scale(2)", "scale(2 2)"), ("scale(2 1)", None), ("scale(-1) translate(-6 -6)", "translate(2 2)"),
                        ("rotate(30)", "rotate(30 0 0)"), ("rotate(30 5 5)", None), ("rotate(30,5,5)", "rotate(30 5 5)"), ("skewX(20)", None), ("skewY(20)", None),
                        ("matrix(1 0 0 1 2 3)", "translate(2 3)"), ("matrix(1,0,0,1,2,3)", "translate(2 3)"), ("matrix(2 0 0 2 0 0)", "scale(2)"),
                        ("translate(2) scale(2)", None), ("translate(2),scale(2)", "translate(2) scale(2)"), ("translate(2) , scale(2)", "translate(2) scale(2)"),
                        ("translate(2)scale(2)", "translate(2) scale(2)"), (" translate(2 3) ", "translate(2 3)"), ("translate(2)&#10;scale(2)", "translate(2) scale(2)"),
                        ("translate(.25) " * 16, "translate(4)"), ("translate(1e9)", "translate(1000000000)")):
        rows.append(("transform", "transform=%r" % form, B % (moved % form), B % (moved % plain) if plain else None, B % (moved % "translate(1 1)")))
    rows.append(("transform", "transform='' moves nothing", B % (moved % ""), B % '<rect width="4" height="4" fill="#f00"/>', B % (moved % "translate(1 1)")))
    # --- path data
    for form in ("M0 0h5v5z", "M0,0H5V5Z", "M0 0h5.v5.e0z", "M0 0h.5e1v+5z", "M0 0l5 0 0 5z", "m0 0 5 0 0 5z", "M0 0L5 0L5 5", "M 0 0 H 5 V 5 Z", "M0 0h5v5-5-5",
                 "M0 0Q5 0 5 0T5 5", "M0 0C5 0 5 0 5 0S5 5 5 5", "M0 0A9 9 0 0 0 5 0L5 5Z", "M0 0a9 9 0 005 0l0 5z"):
        row = [B % ('<path d="%s" fill="#f00"/>' % d) for d in (form, "M0 0h1v1z")]
        rows.append(("path data", "d=%r" % form, row[0], None, row[1]))
    rows.append(("path data", "a point with no digit, in path data only", B % '<path d="M0 0h5.v5.e0z" fill="#f00"/>', B % '<path d="M0 0h5v5z" fill="#f00"/>', None))
    # --- keyword
    for prop, shape, words in (
            ("fill-rule", HOLE, (("nonzero", "evenodd"), ("evenodd", "nonzero"))),
            ("stroke-linecap", '<path class="p" d="M3 5H7" stroke="#f00" stroke-width="4"/>', (("butt", "round"), ("round", "butt"), ("square", "butt"))),
            ("stroke-linejoin", '<path class="p" d="M2 8L5 2L8 8" fill="none" stroke="#f00" stroke-width="2"/>', (("miter", "round"), ("round", "miter"), ("bevel", "miter"))),
            ("visibility", SQUARE, (("visible", "hidden"), ("hidden", "visible"), ("collapse", "visible", "hidden"))),
            ("display", SQUARE, (("inline", "none"), ("block", "none", "inline"), ("inherit", "none", "inline"), ("none", "inline"))),
            ("shape-rendering", '<circle class="p" cx="5" cy="5" r="3.3" fill="#f00"/>',
             (("auto", "crispEdges"), ("geometricPrecision", "crispEdges", "auto"), ("crispEdges", "auto"), ("optimizeSpeed", "auto", "crispEdges"))),
            ("paint-order", '<rect class="p" x="2" y="2" width="6" height="6" fill="#0f0" stroke="#f00" stroke-width="3"/>',
             (("normal", "stroke"), ("fill", "stroke", "normal"), ("markers", "stroke", "normal"), ("fill stroke", "stroke", "normal"), ("fill stroke markers", "stroke", "normal"),
              ("fill markers stroke", "stroke", "normal"), ("markers fill", "stroke", "normal"), ("markers fill stroke", "stroke", "normal"),
              ("stroke", "normal"), ("stroke fill", "normal", "stroke"), ("stroke markers", "normal", "stroke"), ("stroke fill markers", "normal", "stroke"),
              ("stroke markers fill", "normal", "stroke"), ("markers stroke", "normal", "stroke"), ("markers stroke fill", "normal", "stroke"), ("stroke  fill", "normal", "stroke")))):
        for word in words:
            rule("keyword", prop, [(word[0], word[2] if len(word) > 2 else word[0])], None, other=word[1], shape=shape)
    clipped = '<clipPath id="c"><path class="p" d="M1 1h8v8h-8zM3 3h4v4h-4z"/></clipPath><rect clip-path="url(#c)" width="10" height="10" fill="#f00"/>'
    rule("keyword", "clip-rule", ["evenodd"], "evenodd", other="nonzero", shape=clipped)
    rule("keyword", "clip-rule", ["nonzero"], "nonzero", other="evenodd", shape=clipped)
    units = '<clipPath id="c" clipPathUnits="%s"><rect width=".5" height=".5"/></clipPath><rect clip-path="url(#c)" width="8" height="8" fill="#f00"/>'
    rows.append(("keyword", "clipPathUnits='objectBoundingBox'", B % (units % "objectBoundingBox"), None, B % (units % "userSpaceOnUse")))
    rows.append(("keyword", "clipPathUnits='userSpaceOnUse'", B % (units % "userSpaceOnUse"), None, B % (units % "objectBoundingBox")))
    # --- clip-path, id, class
    rule("clip-path", "clip-path", ["url(#c)", "url( #c )", "url(#d-e.f:g_h)", " url(#c) "], "url(#c)", other="none", shape=CLIPS)
    rule("clip-path", "clip-path", ["none"], "none", other="url(#c)", shape=CLIPS)
    for name in ("c", "_", "A", "a1", "clip0_12_34", "SVGID_1_", "a-b.c:d", "x" * 64):
        with_id = '<clipPath id="%s"><rect width="3" height="10"/></clipPath><rect clip-path="url(#%s)" width="10" height="10" fill="#f00"/>'
        rows.append(("id", "id=%r" % name, B % (with_id % (name, name)), B % (with_id % ("c", "c")), B % (with_id % (name, "other"))))
    for name in ("a", "_a", "A1", "a-b_c", "x" * 64):   # the letters a style rule can name an id with
        styled = '<style>#%s{fill:#f00}</style><rect id="%s" width="6" height="6"/>'
        rows.append(("id", "#%s in a rule" % name, B % (styled % (name, name)), B % (styled % ("a", "a")), B % (styled % (name, "other"))))
    for names in ("b", "a b", " a  b ", "b a", "a b c-d e_f 0", "b b"):
        classed = '<style>.b{fill:#f00}</style><rect class="%s" width="6" height="6"/>'
        rows.append(("class", "class=%r" % names, B % (classed % names), B % (classed % "b"), B % (classed % "a")))
    # --- the outer svg: viewBox, preserveAspectRatio, width and height
    tall = '<svg xmlns="http://www.w3.org/2000/svg" %s><rect width="10" height="20" fill="#00f"/><circle cx="5" cy="10" r="4.3" fill="#f00"/></svg>'
    for form in ("0 0 10 20", "0,0,10,20", "0, 0, 10, 20", "0 , 0 , 10 , 20", " 0 0 10 20 ", "0&#9;0&#10;10&#13;20", "0 0 1e1 2e1", "+0 -0 10.0 +20", "0 0 .1e2 20.00",
                 "0-0 10 20", ".0.0 10 20", "0 0 10 2E1"):
        rows.append(("viewBox", "viewBox=%r" % form, tall % ('viewBox="%s"' % form), tall % 'viewBox="0 0 10 20"', tall % 'viewBox="0 0 20 20"'))
    for form in ("-5 -5 20 30", "2.5 5 5 10", "0 0 1e6 1e6", "0 0 1000000 50000.5"):
        rows.append(("viewBox", "viewBox=%r" % form, tall % ('viewBox="%s"' % form), None, tall % 'viewBox="0 0 10 20"'))
    # the smallest box there is: under one unit the renderer rounds a drawing to no pixels at all unless it is given a size,
    # so _render.py gives the cleaned drawing one, and here the file as it came is given the same
    small = tall.replace('width="10" height="20"', 'width=".01" height=".02"').replace('cx="5" cy="10" r="4.3"', 'cx=".005" cy=".01" r=".0043"')
    rows.append(("viewBox", "viewBox='0 0 0.01 0.02'" + GIVEN_A_SIZE, small % 'viewBox="0 0 0.01 0.02"', small % 'viewBox="0 0 1e-2 .2e-1"', small % 'viewBox="0 0 0.02 0.02"'))
    for form in ("none", "xMidYMid", "xMinYMin", "xMaxYMax", "xMidYMin", "xMinYMax", "xMaxYMid", "xMidYMid meet", "xMidYMid slice", "xMinYMin slice", "none meet", "none slice",
                 " xMaxYMin  meet ", "xMidYMid&#10;slice"):
        for size in ("", ' width="10" height="20"', ' width="5px" height="10px"', ' width="100%" height="100%"', ' width="30"'):
            rows.append(("preserveAspectRatio", "%r%s" % (form, size), tall % ('viewBox="0 0 10 20" preserveAspectRatio="%s"%s' % (form, size)), tall % 'viewBox="0 0 10 20"', None))
    for width, height in (("10", "20"), ("5", "10"), ("20", "40"), ("+10", "+20"), ("1e1", "2e1"), ("10.0", "20.00"), ("10px", "20px"), ("64mm", "128mm"), ("1in", "2in"),
                          ("10pt", "20pt"), ("1cm", "2cm"), ("1pc", "2pc"), ("100%", "100%"), ("50%", "100%"), ("100%", "7%"), ("10", "100%"), ("100%", "20"), ("100%", "3"),
                          ("10", None), (None, "20"), ("33", None), (None, "7mm"), ("100%", None), ("10.00009", "20"), ("10", "20.00019"), ("9.99991", "20")):
        attrs = "".join(' %s="%s"' % (k, v) for k, v in (("width", width), ("height", height)) if v is not None)
        rows.append(("width and height of the outer svg", "a viewBox and%s" % attrs, tall % ('viewBox="0 0 10 20"' + attrs), tall % 'viewBox="0 0 10 20"', None))
    for width, height in (("10", "20"), ("10px", "20px"), ("1e1", "2e1"), ("+10.0", "20.00"), (" 10 ", "20px")):
        rows.append(("width and height of the outer svg", "no viewBox, %s by %s" % (width, height), tall % ('width="%s" height="%s"' % (width, height)),
                     tall % 'viewBox="0 0 10 20"', tall % 'viewBox="0 0 20 20"'))
    for attrs in ('x="5" y="6"', 'x="50%" y="-5px"', 'id="logo"', 'x="5" id="logo" width="10" height="20"'):   # left out, and said: nothing of the drawing
        rows.append(("width and height of the outer svg", "beside %s" % attrs, tall % ('viewBox="0 0 10 20" ' + attrs), tall % 'viewBox="0 0 10 20"', None))
    # --- what only says "nothing here"
    for attrs in ('filter="none"', 'mask="none"', 'vector-effect="none"', 'mix-blend-mode="normal"', 'style="filter:none"', 'style="mask:none;fill:#f00"',
                  'style="vector-effect:none"', 'style="mix-blend-mode:normal"', 'filter=" none "', 'style="filter: none ;mask:none"'):
        rows.append(("nothing here", attrs, B % ('<rect %s width="6" height="6" fill="#f00"/>' % attrs), B % '<rect width="6" height="6" fill="#f00"/>', None))
    for prop, word in (("filter", "none"), ("mask", "none"), ("vector-effect", "none"), ("mix-blend-mode", "normal")):
        rows.append(("nothing here", "%s:%s in a rule" % (prop, word), B % ('<style>rect.q{%s:%s}</style><rect class="q" width="6" height="6" fill="#f00"/>' % (prop, word)),
                     B % '<rect width="6" height="6" fill="#f00"/>', None))
    return rows


# Colours are the colour reader's (_colour.py): a paint is held here to "refused, or drawn as it is read". Each of these
# is written after another colour in one rule, so a renderer that cannot read it keeps the other colour.
COLOURS = [
    "#f00", "#F00", "#ff0000", "#FF0000", "#Ff0000", "#f00f", "#ff0000ff", "#FF0000FF", "red", "RED", "Red", "tomato", "rebeccapurple", "darkgrey", "GrEy",
    "rgb(255,0,0)", "rgb(255, 0, 0)", "rgb( 255 , 0 , 0 )", "RGB(255,0,0)", "Rgb(255,0,0)", "rgb(100%,0%,0%)", "rgb(255 0 0)", "rgb(100% 0% 0%)", "rgb(180 83 26)", "rgb(180, 83, 26)",
    "rgb(255,0,0,1)", "rgba(255,0,0,1)", "rgba(255,0,0,1.0)", "rgba(255,0,0,100%)", "rgb(255 0 0 / 1)", "rgb(255 0 0 / 100%)", "rgba(255 0 0 / 1)", "rgba(255,0,0)",
    "rgb(255.0,0.0,0.0)", "rgb(300,-5,0)", "rgb(254.6,0,0)", "rgb(254.4,0.5,0.4)", "rgb(2.55e2,0,0)", "rgb(+255,0,0)", "rgb(49.8%,50.2%,0.2%)", "rgb(127.5,0,0)",
    "hsl(0,100%,50%)", "hsl(0, 100%, 50%)", "hsl(0deg,100%,50%)", "hsl(0 100% 50%)", "hsl(0deg 100% 50%)", "hsla(0,100%,50%,1)", "hsl(0,100%,50%,1)", "hsl(0 100% 50% / 1)",
    "hsl(360,100%,50%)", "hsl(-360,100%,50%)", "hsl(1turn,100%,50%)", "hsl(400grad,100%,50%)", "hsl(6.2831853rad,100%,50%)", "hsl(720,100%,50%)", "hsl(0,200%,50%)",
    "hsl(120,100%,25%)", "hsl(210,50%,40%)", "hsl(210.5,50.5%,40.5%)", "hsl(22.2078 74.7573% 40.3922%)", "HSL(0,100%,50%)", "hsl(30,100%,50%)", "hsl(0.5turn 30% 60%)",
    # read by a browser and not by the site's renderer, or the other way round, or by neither
    "hsl(0,100,50)", "hsl(0,100%,50)", "hsl(0 100 50)", "rgb(255,0,0/1)", "hsl(0,100%,50%/1)", "rgb(50%,0,0)", "rgb(50% 0 0)", "rgb(255,0%,0)", "rgb(255.,0,0)", "rgb(1e2,0,0)",
    "rgb(0e309,0,0)", "rgb(1e100,0,0)", "oklch(0.627955 0.257683 29.2339)", "oklch(62.7955% 0.257683 29.2339)", "oklch(0.627955 0.257683 29.2339 / 1)", "rgb(1_0,0,0)", "#11_22",
    "#f000", "transparent", "rgba(255,0,0,.5)", "rgb(255 0 0 / 50%)", "red garbage", "rgb(255,0,0)garbage", "#ff00", "#ff00000", "color(srgb 1 0 0)", "lab(50% 40 59.5)",
    "rgb(255,,0,0)", "rgb(255,0,0,)", "rgb(,255,0,0)", "rgb(255 0,0)", "hsl(0 100%,50%)", "rgb(255;0;0)", "rgb (255,0,0)", "rgb(255,0,0) ", " rgb(255,0,0)", "0xff0000", "ff0000",
    "currentColor", "currentcolor", "CURRENTCOLOR", "inherit", "INHERIT", "none", "NONE", "None",
]


def refused_rows():
    """What the grammar leaves out BECAUSE of how it is drawn: (what, the code it is refused with, the drawing with the
    form, the drawing it is held against, how the two compare: "differs" where the form is not drawn as the value a
    browser reads in it, "same" where it is drawn as if the OTHER value stood there, so the renderer never read it)."""
    rows = []

    def after(prop, shape, form, other, code="bad-value"):
        rows.append(("%s: %s" % (prop, form), code, in_a_rule(prop, shape, form, other), in_a_rule(prop, shape, other, other), "same"))

    # a unit: the renderer sizes it by the icon it draws (a browser reads 3.75pt, 1.3229mm, .0520833in and 5px as one length)
    for name, form in (("width", "3.75pt"), ("height", "1.3229mm"), ("r", ".0520833in"), ("x", ".3125pc"), ("cx", ".13229cm"), ("rx", ".3125em"), ("y2", ".625ex")):
        shape, _other = SHAPES[name]
        rows.append(("%s=%r" % (name, form), "length-unit", B % (shape % form), B % (shape % "5"), "differs"))
    rows.append(("stroke-width: 3.75pt", "length-unit", in_a_rule("stroke-width", PROPERTIES["stroke-width"][0], "3.75pt", "1"),
                 in_a_rule("stroke-width", PROPERTIES["stroke-width"][0], "5", "1"), "differs"))
    after("stroke-miterlimit", MITRE, "5px", "1.5", "length-unit")
    after("stroke-miterlimit", MITRE, "500%", "1.5", "length-unit")
    # a number the renderer does not take for one
    after("stroke-width", PROPERTIES["stroke-width"][0], "0e309", "5")
    after("stroke-width", PROPERTIES["stroke-width"][0], "0e2147483648", "5")
    after("stroke-width", PROPERTIES["stroke-width"][0], "5.", "1")
    after("stroke-width", PROPERTIES["stroke-width"][0], "4e38", "1", "value-too-long")
    after("stroke-miterlimit", MITRE, "9e99", "1.5", "value-too-long")
    rows.append(("width='9e99'", "value-too-long", B % (SHAPES["width"][0] % "9e99"), B % (SHAPES["width"][0] % "0"), "same"))
    rows.append(("transform='scale(4e38)'", "value-too-long", B % '<rect transform="scale(4e38)" width="4" height="4" fill="#f00"/>', B % '<rect width="4" height="4" fill="#f00"/>', "same"))
    # a list with a comma too many, a dash below zero, a point without its partner
    for form in ("3,,1", ",3 1", "3 1,", "3 -1", "3-1"):
        after("stroke-dasharray", LINE, form, "1 1", "negative-size" if "-" in form else "bad-value")
    poly = '<polygon points="%s" fill="#f00"/>'
    for form in ("1,1 9,1 5,9,", ",1,1 9,1 5,9", "1,,1 9,1 5,9", "1,1 9,1 5,9 3", "1,1 9,1 5"):
        rows.append(("points=%r" % form, "bad-value", B % (poly % form), B % (poly % "1,1 9,1 5,9"), "differs"))
    moved = '<rect transform="%s" width="4" height="4" fill="#f00"/>'
    for form, meant in (("translate(2 3 4)", "translate(2 3)"), ("translate(2,,3)", "translate(2 3)"), ("translate(2,)", "translate(2)"), ("translate(,2)", "translate(2)"),
                        ("scale(2 1 1)", "scale(2 1)"), ("rotate(30 5)", "rotate(30)"), ("rotate(30 5 5 5)", "rotate(30 5 5)"), ("skewX(20 1)", "skewX(20)"),
                        ("matrix(1 0 0 1 2)", "translate(2)"), ("matrix(1 0 0 1 2 3 4)", "translate(2 3)")):
        rows.append(("transform=%r" % form, "bad-value", B % (moved % form), B % (moved % meant), "differs"))
    # a word the renderer does not know
    for word in ("arcs", "miter-clip"):
        after("stroke-linejoin", '<path class="p" d="M2 8L5 2L8 8" fill="none" stroke="#f00" stroke-width="2"/>', word, "round")
    # a made-up length the renderer does not read
    dashes = '<path d="M0 5H10" pathLength="%s" stroke="#f00" stroke-width="4" stroke-dasharray="10"/>'
    rows.append(("pathLength='20'", "path-length", B % (dashes % "20"), B % (dashes % "40"), "same"))
    # the outer svg
    tall = '<svg xmlns="http://www.w3.org/2000/svg" %s><rect width="10" height="20" fill="#00f"/><circle cx="5" cy="10" r="4.3" fill="#f00"/></svg>'
    for form in ("0,,0 10 20", "0 0 10 20,", ",0 0 10 20"):
        rows.append(("viewBox=%r" % form, "bad-view-box", tall % ('viewBox="%s"' % form), tall % 'viewBox="0 0 10 20"', "differs"))
    # a box so small that the renderer takes it for no box at all, and draws nothing where a browser draws the mark
    tiny = tall.replace('width="10" height="20"', 'width=".003" height=".006"').replace('cx="5" cy="10" r="4.3"', 'cx=".0015" cy=".003" r=".0013"')
    rows.append(("viewBox='0 0 0.003 0.006'" + GIVEN_A_SIZE, "bad-view-box", tiny % 'viewBox="0 0 0.003 0.006"', tall % 'viewBox="0 0 10 20"', "differs"))
    for attrs in ('width="40" height="20"', 'width="10" height="21"', 'width="10" height="20.1"', 'width="1in" height="192px"', 'width="5" height="20"',
                  'width="10" height="10" preserveAspectRatio="none"', 'width="40" height="20" preserveAspectRatio="xMinYMin slice"'):
        rows.append(("a viewBox and %s" % attrs, "root-size", tall % ('viewBox="0 0 10 20" ' + attrs), tall % 'viewBox="0 0 10 20"', "differs"))
    for width, height, as_px in (("7.5pt", "15pt", "10 20"), ("2.6458mm", "5.2917mm", "10 20"), (".10417in", ".20833in", "10 20")):
        rows.append(("no viewBox, %s by %s" % (width, height), "no-size", tall % ('width="%s" height="%s"' % (width, height)), tall % ('viewBox="0 0 %s"' % as_px), "differs"))
    # what stands where a browser draws nothing of it
    rect = '<rect width="6" height="6"/>'
    for what, code, inner in (("a style in a title", "misplaced-element", "<title><style>rect{fill:#f00}</style></title>" + rect),
                              ("a style in a desc", "misplaced-element", "<desc><style>rect{fill:#f00}</style></desc>" + rect),
                              ("a style in the metadata", "misplaced-element", "<metadata><style>rect{fill:#f00}</style></metadata>" + rect),
                              ("a style in another program's element", "misplaced-element", '<x:a xmlns:x="urn:x"><style>rect{fill:#f00}</style></x:a>' + rect),
                              ("a style with no namespace", "no-namespace", '<style xmlns="">rect{fill:#f00}</style>' + rect),
                              ("a shape with no namespace", "no-namespace", '<rect xmlns="" fill="#f00" width="6" height="6"/>'),
                              ("a group with no namespace", "no-namespace", '<g xmlns=""><rect fill="#f00" width="6" height="6"/></g>'),
                              ("a clip in the metadata", "misplaced-element",
                               '<metadata><clipPath id="c"><rect width="3" height="3"/></clipPath></metadata><rect clip-path="url(#c)" width="6" height="6"/>')):
        rows.append((what, code, B % inner, B % (rect if "clip" in what or "style" in what else ""), "differs"))
    return rows


class TheValueGrammarIsDrawnAsItIsRead(unittest.TestCase):
    """WHAT THE CHECK READS IS WHAT IS DRAWN. For every form of every line of the value grammar: the check takes it; the
    file as it came and the cleaned file are both drawn, and are the same picture pixel for pixel (no channel of any
    pixel further apart than SAME of 255) at 32 and at 512 pixels; the form is drawn as the plainest way of writing the
    same value is; and it is NOT drawn as another value is, so the renderer did read it. A form that fails one of
    these is not in the grammar: refused_rows() holds those, each with the picture that shows why."""

    def setUp(self):
        T.require_sharp(self)
        self.site = Site()
        self.addCleanup(self.site.close)

    def test_every_form_the_grammar_takes(self):
        rows = grammar_rows()
        lines = sorted(set(r[0] for r in rows))
        self.assertEqual(lines, sorted(["number", "length", "position", "number list", "transform", "path data", "keyword", "clip-path", "id", "class", "viewBox",
                                        "preserveAspectRatio", "width and height of the outer svg", "nothing here"]))
        cleaned = []
        for line, what, doc, _plain, _other in rows:
            try:
                cleaned.append(_svg.clean_svg(doc.encode("utf-8")))
            except Refusal as e:
                cleaned.append(None)
                with self.subTest(line=line, what=what):
                    self.fail("the grammar should take this: refused as %s (%s)" % (e.code, e))
        jobs, kept = [], []
        for (line, what, doc, plain, other), clean in zip(rows, cleaned):
            if clean is None:
                continue
            texts, pairs = [doc, clean.text], [[0, 1]]
            for extra in (plain, other):
                if extra is not None:
                    texts.append(extra)
                    pairs.append([0, len(texts) - 1])
            if what.endswith(GIVEN_A_SIZE):
                texts = [t.replace("<svg ", '<svg width="512" height="1024" ', 1) for t in texts]
            jobs.append({"texts": texts, "pairs": pairs})
            kept.append((line, what, plain, other))
        answers = pictures(self, self.site.dir, jobs)
        worst = 0
        for (line, what, plain, other), answer in zip(kept, answers):
            with self.subTest(line=line, what=what):
                all_drawn(self, answer, what)
                found = list(answer["pairs"])
                the_same(self, found.pop(0), "as it came, and cleaned")
                worst = max([worst] + [got["max"] for got in answer["pairs"][0]])
                if plain is not None:
                    the_same(self, found.pop(0), "as it is written, and written the plainest way")
                if other is not None:
                    not_the_same(self, found.pop(0), "this value, and another")
        self.assertGreater(len(kept), 600, "the table is the whole grammar")
        self.assertLessEqual(worst, SAME)

    def test_every_colour_is_refused_or_drawn_as_it_is_read(self):
        # the colour reader's own business (_colour.py): held here to the same rule, so that the two stay together
        shape = '<g color="#ff0"><rect class="p" width="6" height="6" stroke-width="2"/></g>'
        jobs, kept, outcome = [], [], {}
        for prop in ("fill", "stroke"):
            for form in COLOURS:
                doc = in_a_rule(prop, shape, form, "#0f0")
                try:
                    clean = _svg.clean_svg(doc.encode("utf-8"))
                except Refusal as e:
                    outcome[prop, form] = e.code
                    continue
                outcome[prop, form] = "read"
                # what the check says this form is: the value it wrote on the shape (`inherit` is written as nothing at all)
                wrote = re.search(r' %s="([^"]*)"' % prop, clean.text.rsplit("<rect ", 1)[1])
                mine = wrote.group(1) if wrote else "inherit"
                jobs.append({"texts": [doc, clean.text, in_a_rule(prop, shape, mine, "#0f0"), in_a_rule(prop, shape, "#0f0", "#0f0")], "pairs": [[0, 1], [0, 2], [0, 3]]})
                kept.append((prop, form, mine))
        answers = pictures(self, self.site.dir, jobs)
        for (prop, form, hexed), answer in zip(kept, answers):
            with self.subTest(prop=prop, form=form, read_as=hexed):
                all_drawn(self, answer, form)
                the_same(self, answer["pairs"][0], "as it came, and cleaned")
                the_same(self, answer["pairs"][1], "as it is written, and as the hex the check lists")
                not_the_same(self, answer["pairs"][2], "this colour, and the one the rule set before it")
        # the test is not empty-handed, and what a renderer draws black is not read
        for prop in ("fill", "stroke"):
            for form in ("#f00", "#ff0000", "red", "rgb(255,0,0)", "rgb(180, 83, 26)", "rgb(100%,0%,0%)", "hsl(0,100%,50%)", "currentColor", "none", "inherit"):
                self.assertEqual(outcome[prop, form], "read", form)
            for form in ("hsl(0,100,50)", "hsl(0,100%,50)", "hsl(0 100 50)", "rgb(255,0,0/1)", "hsl(0,100%,50%/1)", "rgb(50%,0,0)", "rgb(255.,0,0)", "rgb(0e309,0,0)",
                         "oklch(0.627955 0.257683 29.2339)", "rgb(1_0,0,0)", "#11_22", "#f000", "transparent", "red garbage", "0xff0000"):
                self.assertNotEqual(outcome[prop, form], "read", form)
        self.assertGreater(len(kept), 100)

    def test_what_the_grammar_leaves_out_is_what_would_be_drawn_differently(self):
        rows = refused_rows()
        for what, code, doc, _against, _how in rows:
            with self.subTest(what=what):
                with self.assertRaises(Refusal) as cm:
                    _svg.clean_svg(doc.encode("utf-8"))
                self.assertEqual(cm.exception.code, code, str(cm.exception))
        sized = lambda what, text: text.replace("<svg ", '<svg width="512" height="1024" ', 1) if what.endswith(GIVEN_A_SIZE) else text
        answers = pictures(self, self.site.dir, [{"texts": [sized(what, doc), sized(what, against)], "pairs": [[0, 1]]} for what, _code, doc, against, _how in rows])
        for (what, _code, _doc, _against, how), answer in zip(rows, answers):
            with self.subTest(what=what, how=how):
                all_drawn(self, answer, what)
                pair = answer["pairs"][0]
                if how == "same":   # drawn as if the other value stood there: the renderer did not read the form at all
                    the_same(self, pair, "the form, and the value it should have replaced")
                else:               # not drawn as the value a browser reads in it, at one size at least
                    self.assertTrue(any(got["far"] > size // 4 for size, got in zip(SIZES, pair)), "drawn as a browser would draw it: %r" % (pair,))


if __name__ == "__main__":
    unittest.main()
