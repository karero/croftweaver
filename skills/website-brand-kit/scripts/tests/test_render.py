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
           dict(background="#12"), dict(background="#12345g"), dict(background=5)]

    def test_each_bad_field_is_refused_by_the_wrapper(self):
        for bad in self.BAD:
            with self.subTest(bad=bad):
                with self.assertRaises(Refusal) as cm:
                    _render.check_job(dict(job("a", 16), **bad))
                self.assertEqual(cm.exception.code, "bad-job")
        _render.check_job(job("a", 16))
        _render.check_job(job("a", 2048, 1, "#aBcDeF"))

    def test_only_cleaned_svg_text_is_handed_over(self):
        for bad in ("", "<?xml version='1.0'?><svg/>", "/etc/passwd", "file:///x.svg", b"<svg/>", None):
            with self.subTest(bad=bad):
                with self.assertRaises(Refusal) as cm:
                    _render.Renderer("/nonexistent", node="/nonexistent/node").render(bad, (0, 0, 1, 1), [job("a", 16)], "/nonexistent/out")
                self.assertEqual(cm.exception.code, "bad-job")


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

    def test_a_reference_to_another_file_is_never_followed(self):
        # measured on 2026-10-10 and again on 2026-10-11: from a PATH the renderer drew the
        # referenced file (400 red pixels of 400); from a BUFFER, none. The intake only ever
        # hands it a buffer, and these files are what a hostile SVG could ask for.
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
        for name, body in cases.items():
            with self.subTest(name=name):
                self.draw(base % body, (0, 0, 20, 20), [job("probe", 20)])
                self.assertEqual(_png.count_colour(_png.decode(self.site.read("probe.png")), "#ff0000"), 0)

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
