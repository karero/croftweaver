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


if __name__ == "__main__":
    unittest.main()
