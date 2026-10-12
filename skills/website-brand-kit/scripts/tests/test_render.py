"""The renderer: scenarios 19 and 11 (the sizes), and the rule that a mark is only ever drawn from
the cleaned text held in memory, never from a file path.

`render.mjs` is started inside the site, so `sharp` is the site's own (D2): no new dependency. The
intake checks it first and stops with the command to run when it is missing (scenario 19). These
tests run the real helper; the ones that draw need a `sharp` to borrow (see _testutil).
"""

import json
import os
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


class WhatIsAcceptedIsDrawnAsItWas(unittest.TestCase):
    """The check reads a file with its own reader of numbers, colours and styles; the site draws it with a renderer
    that has its own. Wherever the two could read a value differently the check must refuse, because it writes ITS
    reading into the cleaned file and lists ITS colours. So for every way of writing a value: the file is refused, or
    the cleaned file is drawn as the original was and no colour is drawn that the check did not list."""

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
        pictures = self.drawn([t for _n, text, clean in pairs for t in (text, clean.text)])
        for i, (name, _text, clean) in enumerate(pairs):
            was, now = pictures[2 * i], pictures[2 * i + 1]
            with self.subTest(name=name):
                self.assertNotIn("error", now, "the cleaned file must draw")
                for colour in set(was) | set(now):
                    self.assertLess(abs(was.get(colour, 0) - now.get(colour, 0)), 82, "%s: drawn %r, cleaned %r" % (colour, was, now))
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
                     "attribute: a class after an em space", "attribute: two classes round a no-break space", "attribute: a clip in quotes",
                     "attribute: a bare point", "attribute: a bare point in hsl", "attribute: a bare point before a percent"):
            self.assertEqual(outcome[name], "refused: bad-value", name)
        self.assertEqual(outcome["attribute: a clip after an em space"], "refused: css-url")
        for name in ("viewBox: an em space", "viewBox: a no-break space", "viewBox: a point"):
            self.assertEqual(outcome[name], "refused: bad-view-box", name)


if __name__ == "__main__":
    unittest.main()
