"""The renderer: scenarios 19 and 11 (the sizes), and the rule that a mark is only ever drawn from
the cleaned text held in memory, never from a file path.

`render.mjs` is started inside the site, so `sharp` is the site's own (D2): no new dependency. The
intake checks it first and stops with the command to run when it is missing (scenario 19). These
tests run the real helper; the ones that draw need a `sharp` to borrow (see _testutil).
"""

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
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

    def test_a_renderer_that_takes_too_long_is_stopped_and_the_refusal_says_what_to_ask_for(self):
        # the backstop behind the check: a drawing that keeps the renderer busy is stopped, and the owner is told what to
        # ask the tool for (it said only that the renderer was stopped)
        slow = self.renderer("sleep 30")
        before = _render.RENDER_SECONDS
        self.assertEqual(before, 180)
        _render.RENDER_SECONDS = 1
        try:
            with self.assertRaises(Refusal) as cm:
                slow.render(MARK, (0, 0, 64, 64), [job("a", 16)], self.tmp.name)
        finally:
            _render.RENDER_SECONDS = before
        self.assertEqual(cm.exception.code, "render-failed")
        for word in ("took more than 1 seconds", "was stopped", "Ask the tool for a plainer drawing", "outlines turned into shapes"):
            self.assertIn(word, str(cm.exception))
        # where no drawing was handed over (the first check that the renderer starts at all), nothing is said about a drawing
        with self.assertRaises(Refusal) as cm:
            slow._run(["--check"], timeout=1)
        self.assertIn("took more than 1 seconds and was stopped.", str(cm.exception))
        self.assertNotIn("drawing", str(cm.exception))

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
# and `far` those that differ by more than `far`. Asked for with `edges`, also {edges: [per text, per size: null or
# {drawn, red}]}: where the picture's edges are, as the box [left, top, right, bottom] (in whole pixels) round the
# pixels that are more than half there, and round the red ones among them (the mark of these tests' drawings).
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
function edges(data, size) {
  const drawn = [size, size, -1, -1], red = [size, size, -1, -1];
  const grow = (box, x, y) => { if (x < box[0]) box[0] = x; if (y < box[1]) box[1] = y; if (x > box[2]) box[2] = x; if (y > box[3]) box[3] = y; };
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const i = 4 * (y * size + x);
    if (data[i + 3] >= 128) grow(drawn, x, y);
    if (data[i + 3] >= 128 && data[i] >= 128 && data[i + 2] < 128) grow(red, x, y);
  }
  return { drawn: drawn[2] < 0 ? null : drawn, red: red[2] < 0 ? null : red };
}
(async () => {
  const req = JSON.parse(require('fs').readFileSync(0, 'utf8'));
  const out = req.rows.map((row) => ({ errors: row.texts.map(() => []), pairs: row.pairs.map(() => []), edges: row.texts.map(() => []) }));
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
        if (req.edges) out[r].edges[t].push(typeof p === 'string' ? null : edges(p, size));
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


def pictures(testcase, site_dir, rows, edges=False):
    """Draw and compare `rows` ([{texts, pairs}]) at every size; see _PICTURES."""
    r = subprocess.run(["node", "-e", _PICTURES], input=json.dumps({"sizes": SIZES, "same": SAME, "far": FAR, "rows": rows, "edges": edges}), cwd=site_dir,
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
            docs["dasharray %r" % f] = '<svg %s><line stroke="#f00" stroke-width="10" stroke-dasharray="%s" y1="5" x2="10" y2="5"/></svg>' % (b, f)
            docs["dashoffset %r" % f] = '<svg %s><line stroke="#f00" stroke-width="10" stroke-dasharray="5" stroke-dashoffset="%s" y1="5" x2="10" y2="5"/></svg>' % (b, f)
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
            docs["dasharray %r" % d] = '<svg %s><line stroke="#f00" stroke-width="10" stroke-dasharray="%s" y1="5" x2="10" y2="5"/></svg>' % (b, d)
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
                     "style: plain", "style: a font's name", "attribute: plain", "attribute: plain spaces", "attribute: an id", "attribute: an id with a space", "attribute: a clip",
                     "attribute: a point with a digit", "viewBox: plain",
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
                     "attribute: an em space after", "attribute: another script's digits", "attribute: full-width letters",
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
DASHED = '<line class="p" y1="5" x2="10" y2="5" stroke="#f00" stroke-width="4"/>'   # a dashed outline stands on a shape whose length its numbers tell
SQUARE = '<rect class="p" width="6" height="6" fill="#f00"/>'
HOLE = '<path class="p" d="M1 1h8v8h-8zM3 3h4v4h-4z" fill="#f00"/>'
CLIPS = ('<clipPath id="c"><rect width="3" height="10"/></clipPath><clipPath id="d-e.f:g_h"><rect width="3" height="10"/></clipPath>'
         '<rect class="p" width="10" height="10" fill="#f00"/>')
PROPERTIES = {   # property: (the shape, the other value)
    "stroke-width": ('<path class="p" d="M0 5H10" stroke="#f00"/>', "1"), "stroke-miterlimit": (MITRE, "1.5"),
    "stroke-dashoffset": ('<line class="p" y1="5" x2="10" y2="5" stroke="#f00" stroke-width="4" stroke-dasharray="7"/>', "1"),
    "opacity": (SQUARE, ".3"), "fill-opacity": (SQUARE, ".3"), "stroke-opacity": (LINE, ".3"), "stroke-dasharray": (DASHED, "1 1"),
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
    # (1010 is as far as a number may be in this box: a hundred times its side of 10, beyond its far edge)
    rule("length", "stroke-width", FIVE + FIVE_PX + [("0", "0"), ("0.0", "0"), ("0e9", "0"), ("0px", "0"), ("1.01e3", "1010")], "5")
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
        rows.append(("position", "%s='1.01e3'" % name, B % (shape % "1.01e3"), B % (shape % "1010"), B % (shape % "1")))
        rows.append(("position", "%s='-10100%%'" % name, B % (shape % "-10100%"), B % (shape % "-1010"), B % (shape % "1")))
    wide = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 10"><rect width="20" height="10" fill="#00f"/>%s</svg>'
    for name, plain in (("x", "10"), ("width", "10"), ("cx", "10"), ("x2", "10"), ("y", "5"), ("height", "5"), ("cy", "5"), ("y2", "5")):
        shape, _other = SHAPES[name]   # a share is of the box's width for x and of its height for y
        rows.append(("position", "%s='50%%' in a box 20 by 10" % name, wide % (shape % "50%"), wide % (shape % plain), wide % (shape % "1")))
    # the dash budget counts a line by its ends as a program works them out (a share of the width for x, of the height for y):
    # a dashed line with one end a share and the other a plain number is drawn from the one to the other
    high = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 20"><rect width="10" height="20" fill="#00f"/>%s</svg>'
    dashed_line = '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#f00" stroke-width="2" stroke-dasharray="2 1"/>'
    for box, what, form, plain in ((wide, "20 by 10", ("50%", "50%", "20", "10"), ("10", "5", "20", "10")), (wide, "20 by 10", ("0", "100%", "100%", "0"), ("0", "10", "20", "0")),
                                   (wide, "20 by 10", ("10", "100%", "10", "1"), ("10", "10", "10", "1")), (high, "10 by 20", ("100%", "5", "1", "5"), ("10", "5", "1", "5")),
                                   (high, "10 by 20", ("50%", "50%", "10", "20"), ("5", "10", "10", "20")), (high, "10 by 20", ("0", "100%", "100%", "0"), ("0", "20", "10", "0"))):
        rows.append(("position", "a dashed line from %s,%s to %s,%s in a box %s" % (form + (what,)), box % (dashed_line % form), box % (dashed_line % plain), box % (dashed_line % ("1", "1", "2", "2"))))
    no_box = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10"><rect width="20" height="10" fill="#00f"/>%s</svg>'
    rows.append(("position", "a share where the box is the width and height", no_box % '<rect width="50%" height="50%" fill="#f00"/>',
                 no_box % '<rect width="10" height="5" fill="#f00"/>', no_box % '<rect width="1" height="1" fill="#f00"/>'))
    # --- number list
    poly, three = '<polygon points="%s" fill="#f00"/>', "1 1 9 1 5 9"
    for form in ("1 1 9 1 5 9", "1,1 9,1 5,9", "1,1,9,1,5,9", "1 , 1 9 , 1 5 , 9", " 1 1 9 1 5 9 ", "1&#10;1&#9;9&#13;1  5 9", "+1 +1 +9 +1 +5 +9", "1e0 1E0 .9e1 1.0 5 9",
                 "1 1 9 1 5 9 1 1", "1 1 9 1" + " " * 3000 + "5 9", "1" + "&#10;" * 500 + "1,9,1," + "&#9;" * 500 + "5 9",
                 # between two points: blanks, or a comma with or without blanks after it
                 "1 1,9 1,5 9", "1 1, 9 1,&#10;5 9", "1,1,&#9;9,1, 5,9", "1 , 1&#10;9 , 1&#9;5 , 9", "1+1 9+1 5+9", "1.0.1e1 9 1,.5e1.9e1"):
        rows.append(("number list", "points=%r" % form[:40], B % (poly % form), B % (poly % three), B % (poly % "1 1 9 1 5 5")))
    rows.append(("number list", "points as far out as a number may be", B % (poly % "1 1 1010 1 5 -1010"), B % (poly % "1 1 1.01e3 1 5 -1.01e3"), B % (poly % three)))
    rows.append(("number list", "points run together before a sign", B % (poly % "1 1 9 1 5-1"), B % (poly % "1 1 9 1 5 -1"), B % (poly % three)))
    rows.append(("number list", "points run together before a point", B % (poly % "1 1 9 1 5.5.9"), B % (poly % "1 1 9 1 5.5 .9"), B % (poly % three)))
    rows.append(("number list", "points='' draws nothing", B % (poly % ""), B % "", B % (poly % three)))
    rule("number list", "stroke-dasharray", ["3 1", "3,1", "3 , 1", "3  1", "3.0 1e0", "+3 +1", "3 1 3 1", ("3", "3 3"), ("3 1 2", "3 1 2 3 1 2"), ("3.5.5", "3.5 .5"),
                                             ("3+1", "3 1"), ("none", "none"), ("0 0", "none"), ("0", "none"), ("1e9", "none"), ("3 1 " * 8, "3 1")], "3 1")
    dashed = '<line y1="5" x2="10" y2="5" stroke="#f00" stroke-width="4" stroke-dasharray="%s"/>'
    for form in ("3&#9;1", "3&#10;1", "&#13;3 1 ", "3&#10;,&#9;1", "3" + " " * 3000 + "1", "3" + "&#10;" * 300 + "," + "&#9;" * 300 + "1"):   # written out as `3 1`, however it is spaced
        rows.append(("number list", "stroke-dasharray=%r" % form[:40], B % (dashed % form), B % (dashed % "3 1"), B % (dashed % "1 1")))
    # the smallest dash there is in this box (a thousandth of its side), and the shapes a dashed outline may stand on
    rows.append(("number list", "stroke-dasharray='0.01 1' (the smallest dash)", B % (dashed % "0.01 1"), B % (dashed % ".01 1 .01 1"), B % (dashed % "1 1")))
    rows.append(("number list", "stroke-dasharray='0 2' (dots)", B % (dashed.replace("<line ", '<line stroke-linecap="round" ') % "0 2"), None, B % (dashed.replace("<line ", '<line stroke-linecap="round" ') % "1 1")))
    for shape in ('<rect x="1" y="1" width="8" height="8" rx="2" fill="none" stroke="#f00" stroke-dasharray="%s"/>', '<circle cx="5" cy="5" r="4" fill="none" stroke="#f00" stroke-dasharray="%s"/>',
                  '<ellipse cx="5" cy="5" rx="4" ry="2" fill="none" stroke="#f00" stroke-dasharray="%s"/>', '<polyline points="1 1 9 1 5 9" fill="none" stroke="#f00" stroke-dasharray="%s"/>',
                  '<polygon points="1,1 9,1 5,9" fill="none" stroke="#f00" stroke-dasharray="%s"/>', '<g stroke="#f00" stroke-dasharray="%s"><line x1="1" y1="1" x2="9" y2="9"/></g>'):
        rows.append(("number list", "a dashed %s" % shape[1:9].split()[0], B % (shape % "2,1"), B % (shape % "2 1"), B % (shape % "none")))
    # --- transform
    moved = '<rect transform="%s" width="4" height="4" fill="#f00"/>'
    for form, plain in (("translate(2)", "translate(2 0)"), ("translate(2 3)", None), ("translate(2,3)", "translate(2 3)"), ("translate( 2 , 3 )", "translate(2 3)"),
                        ("translate(2-3)", "translate(2 -3)"), ("translate(.5.5)", "translate(.5 .5)"), ("translate(2e0 +3E0)", "translate(2 3)"),
                        ("translate(&#10;2&#9;3&#13;)", "translate(2 3)"), ("scale(2)", "scale(2 2)"), ("scale(2 1)", None), ("scale(-1) translate(-6 -6)", "translate(2 2)"),
                        ("rotate(30)", "rotate(30 0 0)"), ("rotate(30 5 5)", None), ("rotate(30,5,5)", "rotate(30 5 5)"), ("skewX(20)", None), ("skewY(20)", None),
                        ("matrix(1 0 0 1 2 3)", "translate(2 3)"), ("matrix(1,0,0,1,2,3)", "translate(2 3)"), ("matrix(2 0 0 2 0 0)", "scale(2)"),
                        ("translate(2) scale(2)", None), ("translate(2),scale(2)", "translate(2) scale(2)"), ("translate(2) , scale(2)", "translate(2) scale(2)"),
                        ("translate(2)scale(2)", "translate(2) scale(2)"), (" translate(2 3) ", "translate(2 3)"), ("translate(2)&#10;scale(2)", "translate(2) scale(2)"),
                        ("translate(.25) " * 16, "translate(4)"), ("translate(1.01e3)", "translate(1010)"),
                        # a blank before the bracket: SVG allows it, and the site's renderer reads it as a browser does (measured 2026-10-13)
                        ("translate (2 3)", "translate(2 3)"), ("translate&#9;(2,3)", "translate(2 3)"), ("rotate &#10; (30 5 5)", "rotate(30 5 5)"), ("skewX (20)", "skewX(20)"),
                        ("matrix  (1 0 0 1 2 3)", "translate(2 3)"), ("translate(2) scale (2)", "translate(2) scale(2)"), ("scale (2)translate (1)", "scale(2) translate(1)"),
                        # a transform is written out with one blank between two of anything, however it is spaced
                        ("translate(2)" + " " * 3000 + "scale(2)", "translate(2) scale(2)"), ("translate(2" + "&#9;" * 500 + "3)", "translate(2 3)"),
                        ("rotate(3e1&#10;,&#10;5,5)&#10;,&#10;translate(1-1)", "rotate(30 5 5) translate(1 -1)")):
        rows.append(("transform", "transform=%r" % form[:60], B % (moved % form), B % (moved % plain) if plain else None, B % (moved % "translate(1 1)")))
    rows.append(("transform", "transform='' moves nothing", B % (moved % ""), B % '<rect width="4" height="4" fill="#f00"/>', B % (moved % "translate(1 1)")))
    # A transform leaves a shape its form: none squashes it flat, or all but flat (those are refused: refused_rows). What
    # stays, up to the line: a small scale, a stretch one way, a steep skew, and several that together stay inside it.
    # Measured 2026-10-13 against Chromium, each on one of two shapes inside a clip path, where a flat one is drawn
    # differently: every one of these is drawn alike by the two (at most 2 pixels of 10,000 apart).
    for form, plain in (("scale(.001)", "scale(.001 .001)"), ("scale(1e-9)", "scale(1e-9 1e-9)"), ("scale(1 .001)", None), ("scale(.001 1)", None), ("scale(2 .001)", None),
                        ("skewX(80)", None), ("skewX(89.4)", None), ("skewX(-89.4)", None), ("skewY(89.4)", None), ("skewX(269.4)", "skewX(89.4)"), ("skewX(90.6)", "skewX(-89.4)"),
                        ("matrix(1 0 99 1 0 0)", None), ("matrix(1 99 0 1 0 0)", None), ("matrix(1 2 2 5 0 0)", None), ("matrix(1e-9 0 0 1e-9 0 0)", "scale(1e-9)"),
                        ("skewX(45) skewY(45) skewX(45)", None), ("scale(100 1) rotate(45) scale(100 1)", None), ("scale(.1) scale(.1) scale(.1)", "scale(.001)")):
        rows.append(("transform", "transform=%r, which leaves a shape its form" % form[:40], B % (moved % form), B % (moved % plain) if plain else None, B % (moved % "translate(1 1)")))
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
            ("display", SQUARE, (("inline", "none"), ("block", "none", "inline"), ("none", "inline"))),
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
    # a clip path is measured in the drawing's own units, written or left out (measured by the box of what it clips it is
    # refused: refused_rows). The other value is only drawn here, to see that the renderer does read the word.
    units = '<clipPath id="c"%s><rect width=".5" height=".5"/></clipPath><rect clip-path="url(#c)" width="8" height="8" fill="#f00"/>'
    in_the_box = B % (units % ' clipPathUnits="objectBoundingBox"')
    for form in ("userSpaceOnUse", " userSpaceOnUse ", "&#9;userSpaceOnUse&#10;"):
        rows.append(("keyword", "clipPathUnits=%r" % form, B % (units % (' clipPathUnits="%s"' % form)), B % (units % ""), in_the_box))
    line = '<clipPath id="c"%s><rect width="5" height="10"/></clipPath><line clip-path="url(#c)" y1="5" x2="10" y2="5" stroke="#f00" stroke-width="4"/>'
    rows.append(("keyword", "clipPathUnits='userSpaceOnUse' with a transform on the clip path", B % (units % ' clipPathUnits="userSpaceOnUse" transform="translate(.6) scale(8)"'),
                 B % '<rect x=".6" width="4" height="4" fill="#f00"/>', in_the_box))
    rows.append(("keyword", "clipPathUnits='userSpaceOnUse' on a straight line", B % (line % ' clipPathUnits="userSpaceOnUse"'), B % (line % ""), B % (line % ' clipPathUnits="objectBoundingBox"')))
    # --- clip-path, id, class
    rule("clip-path", "clip-path", ["url(#c)", "url( #c )", "url(#d-e.f:g_h)", " url(#c) "], "url(#c)", other="none", shape=CLIPS)
    rule("clip-path", "clip-path", ["none"], "none", other="url(#c)", shape=CLIPS)
    # a clip path is a plain outline that clips shapes: what it may hold, and where it may stand
    one, used = '<clipPath id="c"%s><rect%s width="3" height="10"/></clipPath>', '<rect clip-path="url(#c)" width="10" height="10" fill="#f00"/>'
    unclipped = B % '<rect width="10" height="10" fill="#f00"/>'
    for what, doc, plain in (
            ("several plain shapes", B % ('<clipPath id="c"><rect width="3" height="10"/><circle cx="7" cy="5" r="2"/><polygon points="4 0 6 0 5 3"/><path d="M4 9h2v1h-2z"/></clipPath>' + used), None),
            ("a transform on the clip path", B % (one % (' transform="translate(2 0) scale(1 .5)"', "") + used), B % ('<clipPath id="c"><rect x="2" width="3" height="5"/></clipPath>' + used)),
            ("a transform on a shape inside", B % (one % ("", ' transform="translate(2)"') + used), B % ('<clipPath id="c"><rect x="2" width="3" height="10"/></clipPath>' + used)),
            ("used by two shapes and a group", B % (one % ("", "") + used + '<rect clip-path="url(#c)" y="2" width="10" height="2" fill="#0f0"/><g clip-path="url(#c)"><rect y="6" width="10" height="2" fill="#ff0"/></g>'), None),
            ("clip-path: none on the clip path", B % (one % (' clip-path="none"', "") + used), B % (one % ("", "") + used)),
            ("clip-path: none on a shape inside", B % (one % ("", ' style="clip-path:none"') + used), B % (one % ("", "") + used)),
            ("clip-path: none by a rule for everything", B % ("<style>*{clip-path:none}</style>" + one % ("", "") + used.replace("clip-path=", "style=").replace('"url(#c)"', '"clip-path:url(#c)"')), B % (one % ("", "") + used)),
            ("a group that is not shown round the clip path", B % ('<g display="none">%s</g>' % (one % ("", "")) + used), B % (one % ("", "") + used)),
            ("a group that is not shown round its defs", B % ('<g display="none"><defs>%s</defs></g>' % (one % ("", "")) + used), B % (one % ("", "") + used)),
            ("the clip path inside a group that is clipped", B % ('<clipPath id="k"><rect width="10" height="5"/></clipPath><g clip-path="url(#k)">%s</g>' % (one % ("", "") + used)),
             B % '<rect width="3" height="5" fill="#f00"/>'),
            ("a shape inside that is not shown", B % ('<clipPath id="c"><rect display="none" width="3" height="10"/><rect x="6" width="2" height="10"/></clipPath>' + used),
             B % '<rect x="6" width="2" height="10" fill="#f00"/>')):
        rows.append(("clip-path", what, doc, plain, unclipped))
    # one of two shapes inside a clip path, made small or sheared steeply by a transform that is NOT flat: what is clipped
    # is drawn, clipped by the other shape (and by what is left of this one)
    two = '<clipPath id="c"><rect width="3" height="10" transform="%s"/><rect x="5" width="2" height="10"/></clipPath>' + used
    other_alone = B % '<rect x="5" width="2" height="10" fill="#f00"/>'
    for form, plain in (("scale(.001)", None), ("scale(1e-9)", other_alone), ("scale(1 .001)", None), ("skewX(89.4)", None), ("skewY(89.4)", None), ("matrix(1 0 99 1 0 0)", None),
                        ("scale(.1) scale(.1) scale(.1)", None), ("skewX(45) skewY(45) skewX(45)", None)):
        rows.append(("clip-path", "one of two shapes inside with transform=%r" % form[:40], B % (two % form), plain, unclipped))
    # THE ROWS THE LINES OF THE FLAT-TRANSFORM RULE REST ON (_svg._flattens), on the kept side of each line: the least
    # area, the steepest skew, the longest stretch. Each of these, and each row of the loop above, was drawn by the
    # site's renderer AND by headless Chromium, by hand, on 2026-10-13 (100 by 100 pixels, the pixels of each colour
    # counted, the file as it came and cleaned): the two programs were at most 2 pixels of 10,000 apart on every one.
    # THIS SUITE HAS NO BROWSER AND DOES NOT MAKE THAT COMPARISON AGAIN. What it holds is the renderer's half: the file
    # as it came is drawn as the cleaned file is, at 32 and at 512 pixels, and (where the shape with the transform has
    # all but gone) as if the other shape stood in the clip path alone.
    for form, plain in (("scale(1e-9 1e-9)", other_alone), ("scale(-1e-9 1e-9)", other_alone), ("matrix(1e-9 0 0 1e-9 0 0)", other_alone), ("matrix(0 1e-9 -1e-9 0 0 0)", other_alone),
                        ("skewX(89.42)", None), ("skewX(-89.4)", None), ("skewY(-89.4)", None), ("skewX(269.4)", None),
                        # the least area with a turn beside it, which multiplies out to a rounding hair under the line and is kept (round 8)
                        ("scale(1e-9) rotate(6)", other_alone), ("rotate(6) scale(1e-9)", other_alone), ("scale(.001) scale(.001) scale(.001) rotate(6)", other_alone),
                        ("rotate(17) scale(1e-9) rotate(-17)", other_alone)):
        rows.append(("clip-path", "measured against a browser: one of two shapes inside with transform=%r" % form, B % (two % form), plain, unclipped))
    for form in ("scale(100 1) rotate(45) scale(100 1)", "scale(10 1) rotate(45) scale(10 1)"):   # (these two all but fill the box: not held against the unclipped picture)
        rows.append(("clip-path", "measured against a browser: one of two shapes inside with transform=%r" % form, B % (two % form), None, None))
    for name in ("c", "_", "A", "a1", "clip0_12_34", "SVGID_1_", "a-b.c:d", "x" * 64,
                 # an id may start with a digit (one common design tool names its clip paths in hex digits)
                 "8ce47d5fb1", "4a5b6c7d8e", "0", "007", "1e5", "9-9", "0x1f", "1.5", "7:a", "4" * 64):
        with_id = '<clipPath id="%s"><rect width="3" height="10"/></clipPath><rect clip-path="url(#%s)" width="10" height="10" fill="#f00"/>'
        rows.append(("id", "id=%r" % name, B % (with_id % (name, name)), B % (with_id % ("c", "c")), B % (with_id % (name, "other"))))
    for name in ("8ce47d5fb1", "0", "1e5"):   # and is named so from a style and from a rule
        clip = '<clipPath id="%s"><rect width="3" height="10"/></clipPath>' % name
        for what, use in (("a style", '<rect style="clip-path: url( #%s )" width="10" height="10" fill="#f00"/>' % name),
                          ("a rule", '<style>.k{clip-path:url(#%s)}</style><rect class="k" width="10" height="10" fill="#f00"/>' % name)):
            rows.append(("id", "id=%r named from %s" % (name, what), B % (clip + use), B % (with_id % ("c", "c")), unclipped))
    for name in ("a", "_a", "A1", "a-b_c", "layer-1", "x" * 64):   # the letters a style rule can name an id with (the id is then left out: the rule has applied)
        styled = '<style>#%s{fill:#f00}</style><rect id="%s" width="6" height="6"/>'
        rows.append(("id", "#%s in a rule" % name, B % (styled % (name, name)), B % (styled % ("a", "a")), B % (styled % (name, "other"))))
    # an id nothing is named by is left out, whatever it is written in: the drawing is the one without it
    shape = '<g %s><rect %s width="6" height="6" fill="#f00"/></g>'
    for value in ("Frame 1", "Gr\u00f6\u00dfe", "8ce47d5fb1", "icon/logo", " a ", "", "c", "x" * 300, "expression(layer)", "javascript:logo", "url(logo.png)", "@import a"):
        rows.append(("id", "an id nothing is named by: %r" % value[:20], B % (shape % ('id="%s"' % value, 'id="%s"' % value)), B % (shape % ("", "")), None))
    rows.append(("id", "attributes that are left out, whatever they say", B % (shape % ('aria-label="JavaScript: the logo" data-name="expression(layer)"', 'label="url(logo.png)" role="@import a"')),
                 B % (shape % ("", "")), None))
    rows.append(("id", "ids on what is left out and on the outer svg", (B % ('<title id="t">x</title><metadata id="m"/>' + shape % ("", ""))).replace("<svg ", '<svg id="s" ', 1), B % (shape % ("", "")), None))
    rows.append(("id", "a rule names an id written with a blank: it does not apply", B % ('<style>#a{fill:#0f0}</style>' + shape % ("", 'id=" a"')), B % (shape % ("", "")),
                 B % ('<style>#a{fill:#0f0}</style>' + shape % ("", 'id="a"'))))
    clip = '<clipPath id="c"><rect width="3" height="10"/></clipPath><clipPath id="unused"><rect width="1" height="1"/></clipPath><g id="g"><rect id="r" clip-path="url(%s)" width="10" height="10" fill="#f00"/></g>'
    for form in ("#c", " #c ", "&#9;#c&#10;"):
        rows.append(("id", "a clip path named by its id, among ids nothing is named by: url(%s)" % form, B % (clip % form), B % (clip % "#c"), B % (clip % "#unused")))
    # `inherit` in a paint is written as nothing at all. Measured 2026-10-13 in the places where `display: inherit` was drawn
    # differently (on a shape inside a clip path, and by a rule every element matches): a paint's is drawn as it is read
    clipped = '<clipPath id="c"><rect %s width="3" height="10"/></clipPath><g fill="#0f0" stroke="#f00" color="#f00"><rect %s clip-path="url(#c)" x="1" y="1" width="8" height="8" stroke-width="2"/></g>'
    for prop in ("fill", "stroke", "color"):
        for what, doc, plain in (("on a shape inside a clip path", B % (clipped % ('%s="inherit"' % prop, "")), B % (clipped % ("", ""))),
                                 ("in a style inside a clip path", B % (clipped % ('style="%s:inherit"' % prop, "")), B % (clipped % ("", ""))),
                                 ("on the shape that is clipped", B % (clipped % ("", '%s="inherit"' % prop)), B % (clipped % ("", ""))),
                                 # (a rule every shape matches also takes the colour off the square behind: held as it came against cleaned)
                                 ("by a rule every element matches", B % ("<style>*{%s:inherit}</style>" % prop + clipped % ("", "")), None),
                                 ("by a rule for the clip path and one for its shapes", B % ("<style>clipPath{%s:#00f}rect{%s:inherit}</style>" % (prop, prop) + clipped % ("", "")), None)):
            rows.append(("paint", "%s: inherit %s" % (prop, what), doc, plain, None))
    rows.append(("paint", "fill: inherit after another fill in one rule", B % ('<style>.p{fill:#00f;fill:inherit}</style><g fill="#f00">%s</g>' % SQUARE.replace(' fill="#f00"', "")),
                 B % ('<g fill="#f00">%s</g>' % SQUARE.replace(' fill="#f00"', "")), B % ('<g fill="#f00">%s</g>' % SQUARE.replace('fill="#f00"', 'fill="#00f"'))))
    for names in ("b", "a b", " a  b ", "b a", "a b c-d e_f 0", "b b",
                  # a name no rule can name is passed over, wherever it stands among the others
                  "h-6 w-6 md:h-8 hover:text-gray-500 b", "b md:h-8", "w-1/2 b top-0.5", "!mt-0 b [&amp;&gt;path]:x", "b.c b #b .b b,c"):
        classed = '<style>.b{fill:#f00}</style><rect class="%s" width="6" height="6"/>'
        rows.append(("class", "class=%r" % names, B % (classed % names), B % (classed % "b"), B % (classed % "a")))
    for names in ("md:h-8", "hover:b", "b.c", ".b", "#b", "b,c", "b:hover", "w-1/2 [b]", "b/b b:b", "0b", "-"):   # and names nothing by any piece of itself
        classed = '<style>.b{fill:#f00} .md{fill:#0f0} .h-8{fill:#0f0} .hover{fill:#0f0} .c{fill:#0f0} .w-1{fill:#0f0}</style><rect class="%s" width="6" height="6"/>'
        rows.append(("class", "class=%r, which no rule names" % names, B % (classed % names), B % (classed % "a"), B % (classed % "b")))
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
                          ("10", None), (None, "20"), ("33", None), (None, "7mm"), ("100%", None), ("10.00009", "20"), ("10", "20.00019"), ("9.99991", "20"),
                          # the units a letter's size is measured in: `1em` by `1em` round a square viewBox is the commonest size of an icon export
                          ("1em", "2em"), ("10em", "20em"), ("1.5ex", "3ex"), (".5em", "1e0em"), ("1em", None), (None, "3ex"), ("1em", "100%"), ("100%", "2ex"),
                          # a share of the page is no size, whatever the share (a share of nothing is refused: a browser draws nothing for it)
                          ("1%", "1%"), ("1000%", "1000%"), ("0.5%", None), (None, "250%"), ("12.5%", "20"), ("10", "0.01%"), ("1e-9%", "1e9%"), ("50%", "2em")):
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
    # an editor's leftovers, on a shape that could carry markers: no markers, no group of its own, no way of drawing pictures,
    # and the editor's own properties (which no program draws)
    bent = '<polyline %s points="1 1 6 1 6 6" fill="none" stroke="#f00" stroke-width="2"/>'
    for attrs in ('marker="none"', 'marker-start="none" marker-mid="none" marker-end="none"', 'marker-start=" none "', 'style="marker:none"', 'style="marker-start:none;marker-mid:none;marker-end:none"',
                  'isolation="auto"', 'image-rendering="auto"', 'style="isolation:auto"', 'style="image-rendering:auto"', 'style="isolation: auto ;image-rendering:auto;marker:none"',
                  'style="-inkscape-stroke:none"', 'style="-inkscape-stroke:hairline;-inkscape-font-specification:Sans"',
                  "style=\"fill:none;fill-opacity:1;stroke:#f00;stroke-width:2;marker:none;-inkscape-stroke:none;paint-order:normal;isolation:auto;mix-blend-mode:normal\""):
        rows.append(("nothing here", attrs, B % (bent % attrs), B % (bent % ""), None))
    for prop, word in (("marker", "none"), ("marker-start", "none"), ("marker-mid", "none"), ("marker-end", "none"), ("isolation", "auto"), ("image-rendering", "auto"), ("-inkscape-stroke", "none")):
        rows.append(("nothing here", "%s:%s in a rule" % (prop, word), B % (('<style>polyline.q{%s:%s}</style>' % (prop, word)) + bent % 'class="q"'), B % (bent % ""), None))
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
    # between two points the renderer reads no comma after a blank, and no number run on to the one before: it draws nothing
    for form, meant in (("1,1 ,9,1 5,9", "1 1 9 1 5 9"), ("1 1 , 9 1 5 9", "1 1 9 1 5 9"), ("1 1 9 1&#9;,&#10;5 9", "1 1 9 1 5 9"), ("1 1 9 1  ,  5 9", "1 1 9 1 5 9"),
                        ("5 5+9 1 5 9", "5 5 9 1 5 9"), ("1 1.5.5 9 5 9", "1 1.5 .5 9 5 9"), ("1 1 9 1-5-9", "1 1 9 1 -5 -9")):
        rows.append(("points=%r between two points" % form, "bad-value", B % (poly % form), B % (poly % meant), "differs"))
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
    for attrs in ('width="40" height="20"', 'width="10" height="21"', 'width="10" height="20.5"', 'width="1in" height="192px"', 'width="5" height="20"',
                  'width="10" height="10" preserveAspectRatio="none"', 'width="40" height="20" preserveAspectRatio="xMinYMin slice"',
                  'width="1em" height="32px"', 'width="16px" height="2em"', 'width="4em" height="1ex"', 'width="4em" height="2em"'):
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
    # A reference finds another element once the file is cleaned: a program takes the FIRST element that carries an id,
    # whatever it is, so the file as it came is not clipped (the red covers the box) and the cleaned file would be
    clip = '<clipPath id="c"><rect width="3" height="10"/></clipPath><rect clip-path="url(#c)" width="10" height="10" fill="#f00"/>'
    for what, doc in (("an id on a title that is also a clip path's", B % ('<title id="c">x</title>' + clip)), ("an id on the metadata that is also a clip path's", B % ('<metadata id="c"/>' + clip)),
                      ("an id on a desc that is also a clip path's", B % ('<desc id="c"/>' + clip)), ("an id on a group that is also a clip path's", B % ('<g id="c"/>' + clip)),
                      ("an id on the outer svg that is also a clip path's", (B % clip).replace("<svg ", '<svg id="c" ', 1))):
        rows.append((what, "shared-id", doc, B % clip, "differs"))
    # A clip path that is more than a plain outline, held against what a browser draws of it (Chromium, measured 2026-10-13).
    # Two shapes inside, each clipped by a clip path of its own: the renderer draws nothing, a browser the two quarters.
    halves = '<clipPath id="d"><rect width="10" height="5"/></clipPath><clipPath id="e"><rect y="5" width="10" height="5"/></clipPath>'
    red = '<rect clip-path="url(#c)" width="10" height="10" fill="#f00"/>'
    quarters = B % '<rect width="4" height="5" fill="#f00"/><rect x="6" y="5" width="4" height="5" fill="#f00"/>'
    rows.append(("two shapes in a clip path, each clipped by another", "clip-in-clip",
                 B % (halves + '<clipPath id="c"><rect width="4" height="10" clip-path="url(#d)"/><rect x="6" width="4" height="10" clip-path="url(#e)"/></clipPath>' + red), quarters, "differs"))
    rows.append(("the same, set by a style and by a rule", "clip-in-clip",
                 B % ("<style>.k{clip-path:url(#e)}</style>" + halves + '<clipPath id="c"><rect width="4" height="10" style="clip-path:url(#d)"/><rect class="k" x="6" width="4" height="10"/></clipPath>' + red),
                 quarters, "differs"))
    # two clip paths that clip each other: the renderer clips by both, a browser leaves the way back out
    strip = B % '<rect width="3" height="10" fill="#f00"/>'
    rows.append(("two clip paths that clip each other", "clip-in-clip",
                 B % ('<clipPath id="d" clip-path="url(#c)"><rect width="10" height="3"/></clipPath><clipPath id="c" clip-path="url(#d)"><rect width="3" height="10"/></clipPath>' + red), strip, "differs"))
    rows.append(("two clip paths whose shapes are clipped by each other", "clip-in-clip",
                 B % ('<clipPath id="d"><rect width="10" height="3" clip-path="url(#c)"/></clipPath><clipPath id="c"><rect width="3" height="10" clip-path="url(#d)"/></clipPath>' + red), strip, "differs"))
    # display on a clip path or on its defs: the renderer clips all the same, a browser does not clip at all
    whole = B % '<rect width="10" height="10" fill="#f00"/>'
    for what, doc in (("display='none' on a clip path", B % ('<clipPath id="c" display="none"><rect width="3" height="10"/></clipPath>' + red)),
                      ("style='display:none' on a clip path", B % ('<clipPath id="c" style="display:none"><rect width="3" height="10"/></clipPath>' + red)),
                      ("clipPath{display:none}", B % ('<style>clipPath{display:none}</style><clipPath id="c"><rect width="3" height="10"/></clipPath>' + red)),
                      ("#c{display:none} for a clip path", B % ('<style>#c{display:none}</style><clipPath id="c"><rect width="3" height="10"/></clipPath>' + red)),
                      ("display='none' on the defs round a clip path", B % ('<defs display="none"><clipPath id="c"><rect width="3" height="10"/></clipPath></defs>' + red)),
                      ("defs{display:none}", B % ('<style>defs{display:none}</style><defs><clipPath id="c"><rect width="3" height="10"/></clipPath></defs>' + red))):
        rows.append((what, "clip-display", doc, whole, "differs"))
    # a clip-path on the outer svg is measured in the picture's pixels: a clip 100 wide leaves a small icon whole and cuts a large one
    for what, root in (("clip-path on the outer svg", 'clip-path="url(#c)"'), ("style='clip-path' on the outer svg", 'style="clip-path:url(#c)"')):
        rows.append((what, "root-clip-path", (B % '<clipPath id="c"><rect width="100" height="1000"/></clipPath><rect width="10" height="10" fill="#f00"/>').replace("<svg ", "<svg %s " % root, 1), whole, "differs"))
    rows.append(("svg{clip-path} for the outer svg", "root-clip-path", B % '<style>svg{clip-path:url(#c)}</style><clipPath id="c"><rect width="100" height="1000"/></clipPath><rect width="10" height="10" fill="#f00"/>',
                 whole, "differs"))
    # `display: inherit` on a shape inside a clip path, however it gets there: the renderer draws nothing of what is clipped
    inside = '<clipPath id="c"><rect %s width="3" height="10"/></clipPath><rect clip-path="url(#c)" width="10" height="10" fill="#f00"/>'
    for what, doc in (("display='inherit' on a shape inside a clip path", B % (inside % 'display="inherit"')), ("*{display:inherit} beside a clip path", B % ("<style>*{display:inherit}</style>" + inside % "")),
                      ("rect{display:inherit} under clipPath{display:inline}", B % ("<style>clipPath{display:inline}rect{display:inherit}</style>" + inside % "")),
                      ("style='display:inherit' under clipPath{display:block}", B % ("<style>clipPath{display:block}</style>" + inside % 'style="display:inherit"'))):
        rows.append((what, "bad-value", doc, B % (inside % ""), "differs"))
    # A clip path measured by the box of the shape it clips, held against what a browser draws of it (Chromium, measured
    # 2026-10-13). With a transform on the clip path as well, the renderer moves the clip by six tenths of the SHAPE
    # and a browser by six tenths of a unit; and a straight line, whose box has no height (or no width), is drawn
    # whole by the renderer and not at all by a browser.
    in_the_box = '<clipPath id="c" clipPathUnits="objectBoundingBox"%s><rect width="%s" height="%s"/></clipPath>'
    nothing = B % ""
    for what, doc, browser in (
            ("a clip in the box's units with a transform on the clip path", B % (in_the_box % (' transform="translate(.6)"', ".5", "1") + red), B % '<rect x=".6" width="5" height="10" fill="#f00"/>'),
            ("a clip in the box's units on a straight line", B % (in_the_box % ("", ".5", "1") + '<line clip-path="url(#c)" x1="0" y1="5" x2="10" y2="5" stroke="#f00" stroke-width="4"/>'), nothing),
            ("a clip in the box's units on an upright line of two points", B % (in_the_box % ("", "1", ".5") + '<polyline clip-path="url(#c)" points="5 0 5 10" fill="none" stroke="#f00" stroke-width="4"/>'), nothing),
            ("a clip in the box's units on a group that holds a line", B % (in_the_box % ("", ".5", "1") + '<g clip-path="url(#c)"><line x1="0" y1="5" x2="10" y2="5" stroke="#f00" stroke-width="4"/></g>'), nothing)):
        rows.append((what, "clip-units", doc, browser, "differs"))
    # A transform that squashes one of two shapes inside a clip path flat (Chromium, measured 2026-10-13). For a scale of
    # nothing, however it comes about, the renderer draws nothing at all of what is clipped, and a browser clips by the
    # other shape. For a skew of a quarter turn, or nearly, it is the browser that draws nothing.
    two = '<clipPath id="c"><rect width="3" height="10" transform="%s"/><rect x="5" width="2" height="10"/></clipPath>' + red
    other_alone = B % '<rect x="5" width="2" height="10" fill="#f00"/>'
    for form in ("scale(0)", "scale(1 0)", "scale(0 1)", "matrix(0 0 0 0 0 0)", "matrix(1 2 2 4 0 0)", "matrix(1 0 0 0 0 5)", "scale(1e-46)", "scale(1e-40) " * 5, "translate(1) scale(0)",
                 "rotate(45) scale(1 0)", "skewX(89.4) skewY(89.4) " * 8):
        rows.append(("one of two shapes in a clip path with transform=%r" % form[:40], "flat-transform", B % (two % form), other_alone, "differs"))
    for form in ("skewX(90)", "skewX(89.99999)", "skewX(270)"):
        rows.append(("one of two shapes in a clip path with transform=%r" % form, "flat-transform", B % (two % form), nothing, "differs"))
    # An angle too large for single precision: written, it is 90.9 degrees on from whole turns; both programs read 90 on
    # from them, the skew of a quarter turn of the rows above (Chromium, measured 2026-10-13: it draws nothing).
    rows.append(("one of two shapes in a clip path with transform='skewX(20000070.9)'", "angle-too-large", B % (two % "skewX(20000070.9)"), nothing, "differs"))
    # an include: the renderer fetches what it names (here, what the address itself holds) and draws it, or applies its styles
    xi = 'xmlns:xi="http://www.w3.org/2001/XInclude"'
    red = "data:image/svg+xml;base64," + base64.b64encode(b'<rect xmlns="http://www.w3.org/2000/svg" width="10" height="10" fill="#f00"/>').decode("ascii")
    sheet = "data:text/xml;base64," + base64.b64encode(b'<style xmlns="http://www.w3.org/2000/svg">rect{fill:#f00}</style>').decode("ascii")
    for what, inner in (("an include of a shape", '<xi:include %s href="%s"/>' % (xi, red)), ("an include of a style, in the metadata", '<metadata><xi:include %s href="%s"/></metadata>' % (xi, sheet)),
                        ("an include of a style, in a title", '<title><xi:include %s href="%s"/></title>' % (xi, sheet))):
        rows.append((what, "xinclude", B % inner, B % "", "differs"))
    # a number far outside the box: drawn in a small icon and not in a large one (so not as a browser draws it, which fills the box)
    rows.append(("stroke-width='1000000' in a box of 10", "too-far", B % '<path d="M0 5H10" stroke="#f00" stroke-width="1000000"/>', B % '<rect width="10" height="10" fill="#f00"/>', "differs"))
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
        self.assertEqual(lines, sorted(["number", "length", "position", "number list", "transform", "path data", "keyword", "paint", "clip-path", "id", "class", "viewBox",
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

    def edges_hold(self, came, cleaned, what, share=0.01):
        """THE BOUND ITSELF: every edge of the drawing lies at most a hundredth of the icon's side (`share`) from where the
        file as it came had it. `came` and `cleaned` are where the edges are in the two pictures (per size: the box
        round the drawn pixels and the box round the red mark). An edge is found in whole pixels, so one pixel is
        allowed for that. The furthest any edge has moved, as a share of the side."""
        furthest = 0.0
        for size, before, after in zip(SIZES, came, cleaned):
            for part in ("drawn", "red"):
                self.assertTrue(before[part] and after[part], "%s: at %d pixels nothing of the %s part is there" % (what, size, part))
                for edge, a, b in zip(("left", "top", "right", "bottom"), before[part], after[part]):
                    self.assertLessEqual(abs(a - b), size * share + 1, "%s: at %d pixels the %s edge of the %s part has moved by %d pixels" % (what, size, edge, part, abs(a - b)))
                    furthest = max(furthest, abs(a - b) / size)
        return furthest

    def test_a_size_a_tool_rounded_apart_from_its_viewbox_moves_an_edge_by_no_more_than_a_hundredth_of_the_icons_side(self):
        # The outer svg's width and height may be up to one part in a hundred from the shape of its viewBox (an export of
        # 283.46px by 141.73px round a viewBox of 283.5 by 141.7 was refused). The cleaned file keeps the viewBox alone, so
        # within that line it is NOT the file as it came pixel for pixel: the drawing is set a little smaller in its room,
        # and where the room is left over is said by preserveAspectRatio. In the middle (the default) every edge moves by
        # up to half a hundredth of the icon's side; pushed to one side (xMinYMin, xMaxYMax, xMidYMax) the far edge moves
        # by up to a whole hundredth. What is held here is THAT: where the edges are (edges_hold), at every size and for
        # every way of setting the drawing in its room, at the line. Measured 2026-10-13: at the line no edge moves by
        # more than 4 pixels of 512 (2 in the middle), and none of a 32-pixel icon's moves at all. Until then the test
        # counted the pixels that differ, and a drawing moved down by 20 pixels passed it (15,124 pixels differ, and
        # the count allowed 15,861): the controls below are that drawing and five more. The counts, for the record, of
        # the 262,144 pixels of a 512-pixel icon at the line itself: 3,348 in the middle, up to 3,756 pushed to a
        # side, none of a 32-pixel icon's; past the line (10 by 20.5) 8,548. A bound on how far an edge moves is NOT
        # one on how many pixels differ: a mark of a hundred fine lines differs in 98,240 to 113,226 of them.
        tall = '<svg xmlns="http://www.w3.org/2000/svg" %s><rect width="10" height="20" fill="#00f"/><circle cx="5" cy="10" r="4.3" fill="#f00"/></svg>'
        sizes = [("10", "20.19"), ("10", "19.81"), ("10.09", "20"), ("9.91", "20"), ("283.46px", "566.93px"), ("10mm", "20.19mm"), ("1em", "2.019em"), ("10", "20.1"), ("10.05pt", "20pt")]
        aspects = ("", "xMidYMid", "xMinYMin", "xMaxYMax", "xMidYMax", "xMidYMin", "xMinYMid", "xMaxYMin meet", "xMidYMid slice", "xMinYMin slice", "xMaxYMax slice", "none")
        within = [(width, height, "") for width, height in sizes] + [(width, height, aspect) for width, height in sizes[:4] for aspect in aspects[1:]]
        # (a size that is too WIDE for its viewBox only adds room at the sides, which a square icon has anyway: too tall is what shows)
        beyond = [("10", "20.5"), ("10", "21"), ("10", "24"), ("10mm", "20.5mm"), ("1em", "2.05em")]
        attrs = lambda width, height, aspect: 'viewBox="0 0 10 20" width="%s" height="%s"%s' % (width, height, ' preserveAspectRatio="%s"' % aspect if aspect else "")
        jobs = []
        for row in within:
            doc = tall % attrs(*row)
            jobs.append({"texts": [doc, _svg.clean_svg(doc.encode()).text], "pairs": [[0, 1]]})
        for width, height in beyond:
            for aspect in ("", "xMinYMin", "xMidYMax"):
                doc = tall % attrs(width, height, aspect)
                with self.assertRaises(Refusal) as cm:
                    _svg.clean_svg(doc.encode())
                self.assertEqual(cm.exception.code, "root-size")
            jobs.append({"texts": [tall % attrs(width, height, ""), tall % 'viewBox="0 0 10 20"'], "pairs": [[0, 1]]})
        # a mark of a hundred fine lines, at the line itself: an edge moves by no more, and that is the whole of a line's width
        stripes = '<svg xmlns="http://www.w3.org/2000/svg" %%s><path d="%s" stroke="#f00" stroke-width=".1"/></svg>' % "".join("M0 %.2fh10" % (0.05 + 0.2 * i) for i in range(100))
        fine = [("10", "20.19", "xMidYMax"), ("10", "20.19", "xMinYMin"), ("10", "20.19", "")]
        for row in fine:
            doc = stripes % attrs(*row)
            jobs.append({"texts": [doc, _svg.clean_svg(doc.encode()).text], "pairs": [[0, 1]]})
        # The control: the drawing as it came, held against itself moved. By 4 hundredths of its height (20 pixels of 512)
        # the bound must NOT hold, by a third of a hundredth it must; and so that the control is about the bound and not
        # about one picture, moved each way.
        plain = tall % 'viewBox="0 0 10 20"'
        moved = [("down, too far", tall % 'viewBox="0 -0.8 10 20"', False), ("up, too far", tall % 'viewBox="0 0.8 10 20"', False), ("to the side, too far", tall % 'viewBox="0.8 0 10 20"', False),
                 ("smaller, too far", tall % 'viewBox="-0.6 -1.2 11.2 22.4"', False), ("down, a little", tall % 'viewBox="0 -0.06 10 20"', True), ("smaller, a little", tall % 'viewBox="-0.03 -0.06 10.06 20.12"', True)]
        for _what, text, _holds in moved:
            jobs.append({"texts": [plain, text], "pairs": [[0, 1]]})
        answers = pictures(self, self.site.dir, jobs, edges=True)
        seen, middle, furthest, furthest_in_the_middle = 0, 0, 0.0, 0.0
        for (width, height, aspect), answer in zip(within, answers):
            with self.subTest(width=width, height=height, aspect=aspect):
                all_drawn(self, answer, "%s by %s %s" % (width, height, aspect))
                in_the_middle = aspect in ("", "xMidYMid")   # set in the middle of its room, an edge moves by half as much at most
                gone = self.edges_hold(answer["edges"][0], answer["edges"][1], "%s by %s %s" % (width, height, aspect), share=0.005 if in_the_middle else 0.01)
                furthest = max(furthest, gone)
                furthest_in_the_middle = max(furthest_in_the_middle, gone if in_the_middle else 0.0)
                for got in answer["pairs"][0]:
                    seen = max(seen, got["over"])
                    middle = max(middle, got["over"] if aspect in ("", "xMidYMid") else 0)
        self.assertGreater(middle, 0, "within the line the two are not the same picture, and this test says so")
        self.assertGreater(furthest_in_the_middle, 0, "and its edges are not where they were")
        self.assertGreater(furthest, furthest_in_the_middle, "pushed to one side an edge moves further than set in the middle")
        for (width, height), answer in zip(beyond, answers[len(within):]):
            with self.subTest(width=width, height=height):
                all_drawn(self, answer, "%s by %s" % (width, height))
                self.assertGreater(answer["pairs"][0][-1]["over"], seen, "past the line more differs in a large icon than anywhere at the line")
        for row, answer in zip(fine, answers[len(within) + len(beyond):len(within) + len(beyond) + len(fine)]):
            with self.subTest(fine=row):
                all_drawn(self, answer, "fine lines, %s by %s %s" % row)
                self.assertGreater(answer["pairs"][0][-1]["over"], SIZES[-1] * SIZES[-1] // 8, "a mark of fine lines differs all over in a large icon")
                self.edges_hold(answer["edges"][0], answer["edges"][1], "fine lines, %s by %s %s" % row)   # and its edges are where they were, to the hundredth
        for (what, _text, holds), answer in zip(moved, answers[len(answers) - len(moved):]):
            with self.subTest(moved=what):
                all_drawn(self, answer, what)
                if holds:
                    self.edges_hold(answer["edges"][0], answer["edges"][1], what)
                else:
                    with self.assertRaises(AssertionError, msg="a drawing moved %s passed for one whose edges are where they were" % what):
                        self.edges_hold(answer["edges"][0], answer["edges"][1], what)

    def test_a_file_as_it_came_may_be_one_the_renderer_cannot_draw_small_where_the_cleaned_file_is_drawn(self):
        # A search with generated files (2026-10-13) reported "zero-sized image" for a file as it came, at 32 pixels, with
        # an outer size in pc or %: the renderer works such a size out by the icon it is drawing, and for a small icon it
        # comes to no pixels at all. That is the file as it came failing to draw, not the cleaned file (which says its size
        # by its viewBox alone and is drawn at every size): no finding, and pinned here so that the reason stays known.
        tall = '<svg xmlns="http://www.w3.org/2000/svg" %s><rect width="10" height="20" fill="#00f"/><circle cx="5" cy="10" r="4.3" fill="#f00"/></svg>'
        doc = tall % 'viewBox="0 0 10 20" width="200pc" height="400pc"'
        clean = _svg.clean_svg(doc.encode())
        answer = pictures(self, self.site.dir, [{"texts": [doc, clean.text, tall % 'viewBox="0 0 10 20"'], "pairs": [[0, 1], [1, 2]]}])[0]
        self.assertEqual(SIZES, (32, 512))
        self.assertIn("zero-sized image", answer["errors"][0][0] or "", "at 32 pixels the file as it came is not drawn")
        self.assertIsNone(answer["errors"][0][1], "at 512 pixels it is")
        self.assertEqual(answer["errors"][1], [None, None], "the cleaned file is drawn at both")
        self.assertIsNone(answer["pairs"][0][0])
        self.assertEqual(answer["pairs"][0][1]["over"], 0, "and where both are drawn they are one picture")
        the_same(self, answer["pairs"][1], "the cleaned file, and the drawing by its viewBox alone")

    def test_the_dash_budget_counts_the_dashes_of_these_drawings_and_the_renderer_draws_each_of_them(self):
        # A REGRESSION FOR THE DASH COUNT, and no promise about time. The budget of the check (_svg._reach) bounds the
        # NUMBER of dashes a file's outlines are cut into. Before it, a dashed path of 3,652 characters that ran a hundred
        # boxes out and back took the renderer 33 seconds of processor time for one icon, and one of 25,152 characters
        # inside its box 10 (measured 2026-10-13, load average 3 to 12). Each drawing below is cut into as many dashes as
        # the budget takes, or nearly, with an outline 2 wide and plain joins; the slowest of them was measured at 0.8
        # seconds on a quiet machine, 2.2 at load 10 and 3.2 at load 90 to 460. The line held here, ten seconds of
        # processor time, lies between the two: a budget that has stopped counting is caught by it, and that is all it
        # is for.
        # It is NOT a bound on how long a dashed drawing takes. The renderer's time also grows with how wide and how
        # round each dash is: inside every cap, a dashed polygon with an outline 10 wide and round joins took 7.3 seconds
        # at 240 sides and was stopped after 60 at 500 sides, and 159 dashed circles with round caps 10 wide took 14.2.
        # For every drawing, dashed or not, how long it takes is bounded by the time limit of the renderer's call alone
        # (_render.RENDER_SECONDS: see test_a_renderer_that_takes_too_long_is_stopped_and_the_refusal_says_what_to_ask_for).
        dashes = 'fill="none" stroke="#f00" stroke-width="2" stroke-dasharray="%s"'
        inside = {
            "100 lines across the box, dashes a thousandth of it": '<line y1="5" x2="10" y2="5" %s/>' % (dashes % "0.01") * 100,
            "one line a hundred boxes long": '<line y1="5" x2="1000" y2="5" %s/>' % (dashes % "0.01"),
            "50 diagonals of the box": '<line x2="10" y2="10" %s/>' % (dashes % "0.01") * 50,
            "159 small circles": '<circle cx="5" cy="5" r="1" %s/>' % (dashes % "0.01") * 159,
            "dots along 100 lines": '<line y1="5" x2="10" y2="5" stroke-linecap="round" %s/>' % (dashes % "0 0.02") * 100,
            "a polygon of 1,000 slanted sides": '<polygon points="%s" %s/>' % ("0 0 10 10 0 10 10 0 " * 250, dashes % "0.2"),
            "100 lines, each begun a hundred boxes into its dashes": '<line y1="5" x2="10" y2="5" stroke-dashoffset="1010" %s/>' % (dashes % "0.01") * 100,
            "100 lines with one end a share and one a plain number": '<line x1="100%%" y1="50%%" x2="0" y2="5" %s/>' % (dashes % "0.01") * 100,
            "111 rects with one side a share": '<rect width="45%%" height="0" %s/>' % (dashes % "0.01") * 111,
        }
        renderer = _render.Renderer(self.site.dir)
        for what, inner in inside.items():
            clean = _svg.clean_svg((B % inner).encode())   # each of them is inside the budget: the check takes it
            for size in SIZES:
                with self.subTest(what=what, size=size):
                    started, clock = os.times(), time.time()
                    renderer.render(clean.text, clean.view_box, [job("icon", size)], self.site.out)   # the call the intake makes
                    ended = os.times()
                    used = (ended.children_user + ended.children_system) - (started.children_user + started.children_system)
                    self.assertLess(used or (time.time() - clock), 10.0, "%s took the renderer %.1f seconds at %d pixels" % (what, used, size))
        # one step past the budget, or past the rule it stands on, each of these is refused, so the renderer never meets it
        for inner, code in (('<line y1="5" x2="10" y2="5" %s/>' % (dashes % "0.01") * 101, "too-many-dashes"), ('<line y1="5" x2="10" y2="5" %s/>' % (dashes % "0.0099"), "dash-too-small"),
                            ('<path d="M0 5%s" %s/>' % ("H1010H0" * 500, dashes % "0.01"), "dashed-path"), ('<path d="M0 5%s" %s/>' % ("H10H0" * 5000, dashes % "0.01"), "dashed-path"),
                            ('<path d="M0 5H60000H0" fill="none" stroke="#f00"/>', "too-far"), ('<line y1="5" x2="10" y2="5" stroke-dashoffset="1e9" %s/>' % (dashes % "0.01"), "too-far"),
                            ('<line x1="100%%" y1="50%%" x2="0" y2="5" %s/>' % (dashes % "0.01") * 101, "too-many-dashes"), ('<rect width="45%%" height="0" %s/>' % (dashes % "0.01") * 112, "too-many-dashes")):
            with self.subTest(inner=inner[:60]):
                with self.assertRaises(Refusal) as cm:
                    _svg.clean_svg((B % inner).encode())
                self.assertEqual(cm.exception.code, code)

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
