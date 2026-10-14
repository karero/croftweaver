"""_render.py: starts render.mjs inside the site and talks to it.

The renderer is the one part that needs Node and `sharp`. It is started with the site as its
working folder, so it loads the site's own `sharp` (D2: nothing is added to the site), and it is
given the cleaned SVG as text on standard input, never a path. If it cannot start or `sharp` will
not load, nothing has been written yet and the owner is told what to run. Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import shutil

import _proc
from _refusal import Refusal

HELPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render.mjs")
INTRINSIC = 1024  # the long side, in pixels, the drawing is given before it is scaled to each icon
# How long the renderer may take over one call: all the icons it is asked for at once (three at the most). For EVERY
# drawing, dashed or not, this is the one bound on how long it takes to draw. The check (_svg.py) bounds how many
# dashes a file's outlines are cut into, not the time they take: measured 2026-10-13, inside the check's caps, a
# dashed polygon with an outline 10 wide and round joins took 7.3 seconds of processor time for one icon at 240 sides
# and was stopped after 60 at 500 sides, and one outlined path of 40,000 to 50,000 short turns, with no dash in it,
# took 11 to 12 seconds for one 512-pixel icon at load 10. A drawing that passes the limit is refused with the
# sentence below.
RENDER_SECONDS = 180
_FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,60}$")
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

SHARP_MISSING = (
    "The image tool that draws the icons (sharp) cannot be loaded in this site: %s\n"
    "In the site's folder, run:\n"
    "  npm install --include=optional\n"
    "then check that it loads:\n"
    "  node -e \"require('sharp')\"\n"
    "If it still does not load, or there is no build of sharp for this computer, this tool cannot make the icons "
    "on this computer. It never adds sharp to the site's package.json. (Choosing colours needs no sharp.)"
)
NO_NODE = (
    "Node is not installed here, or is not on the path. The site needs it to build and test, so install it first "
    "(the version in the site's .nvmrc), then try again."
)
NO_SITE = "The site's folder (%s) is not there, so the icons cannot be drawn in it. Check the path to the site, then try again."


def _bad_job(why):
    return Refusal("bad-job", "An icon job was not allowed (%s)." % why)


def check_job(job):
    f, size, scale, bg = job.get("file"), job.get("size"), job.get("scale"), job.get("background")
    if not isinstance(f, str) or not _FILE.fullmatch(f):
        raise _bad_job("file name %r" % str(f)[:40])
    if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= 2048:
        raise _bad_job("size %r" % (size,))
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not 0 < scale <= 1:
        raise _bad_job("scale %r" % (scale,))
    # the key itself must be there (None for a see-through picture): render.mjs asks the same
    if "background" not in job or (bg is not None and not (isinstance(bg, str) and _HEX.fullmatch(bg))):
        raise _bad_job("background %r" % (bg,))


class Renderer(object):
    def __init__(self, site_dir, node=None):
        self.site = site_dir
        self.node = node if node is not None else shutil.which("node")

    def _run(self, args, request=None, timeout=RENDER_SECONDS):
        if not self.node:
            raise Refusal("no-node", NO_NODE)
        if not os.path.isdir(self.site):
            raise Refusal("no-site", NO_SITE % self.site)
        try:
            # Node is run as every other command of a run is (_proc._run), because a stop from outside can come
            # while it draws: it is started and waited for in a way a stop cannot break, the stop ends the wait at
            # once, and Node is stopped with it. Read as UTF-8 whatever the computer's own encoding is: a warning
            # may name a path with any letters in it.
            code, printed, errors = _proc._run([self.node, HELPER] + args, self.site, timeout, input=None if request is None else json.dumps(request))
        except FileNotFoundError:
            raise Refusal("no-node", NO_NODE) from None
        if code is None:
            # the one bound on a drawing that is slow to draw, dashed or not (see "nor how long a drawing takes to
            # draw" in _svg.py); with no drawing handed over, it is the computer
            raise Refusal(
                "render-failed",
                "The renderer took more than %d seconds and was stopped.%s"
                % (timeout, " The drawing is far more work to draw than a logo is. Ask the tool for a plainer drawing: fewer "
                            "shapes, and outlines turned into shapes." if request is not None else ""),
            )
        # a line ends at a line feed and nowhere else: splitlines() would also cut an answer in two at a
        # U+2028 or a U+0085 inside one of its texts
        lines = [l for l in printed.split("\n") if l.strip()]
        try:
            answer = json.loads(lines[-1])
            if not isinstance(answer, dict):
                raise ValueError("the answer is not a JSON object")
        except (IndexError, ValueError, RecursionError):  # no line, not JSON, or JSON nested too deep to read
            first = ([l for l in errors.strip().split("\n") if l.strip()] or ["no answer"])[0].strip()[:200]
            raise Refusal("render-failed", "The renderer did not answer (%s)." % first) from None
        if answer.get("ok") is not True:  # true itself: JSON's NaN, a 1 or a word would pass for it otherwise
            code, msg = answer.get("error", "render-failed"), str(answer.get("message", ""))[:300]
            if code == "sharp-missing":
                raise Refusal("sharp-missing", SHARP_MISSING % msg)
            if code == "bad-job":
                raise _bad_job(msg)
            raise Refusal("render-failed", "The drawing could not be rendered: %s" % msg)
        return answer

    def preflight(self):
        """Load sharp and draw one pixel; the versions, or a Refusal that says what to run."""
        return self._run(["--check"], timeout=60)

    def render(self, svg_text, view_box, jobs, out_dir):
        """Draw the cleaned SVG once per job into `out_dir`; the list of {name, file, width, height}."""
        for job in jobs:
            check_job(job)
        if not isinstance(svg_text, str) or not svg_text.lstrip().startswith("<svg "):
            raise Refusal("bad-job", "The renderer is only given cleaned SVG text.")
        try:
            vw, vh = float(view_box[2]), float(view_box[3])
        except (TypeError, ValueError, IndexError):
            vw = vh = 0.0
        if not (0 < vw < float("inf") and 0 < vh < float("inf")):
            raise Refusal("bad-job", "The renderer is only given a drawing whose box has a width and a height above zero.")
        # Measured 2026-10-11: a viewBox under one unit (0 0 0.5 0.25) is rounded to zero pixels
        # before the density can scale it ("bad dimensions"), so the drawing is given a size.
        w, h = (INTRINSIC, INTRINSIC * vh / vw) if vw >= vh else (INTRINSIC * vw / vh, INTRINSIC)
        sized = svg_text.replace("<svg ", '<svg width="%s" height="%s" ' % (round(w, 4), round(h, 4)), 1)
        request = {"svg": sized, "viewBox": list(view_box), "intrinsic": INTRINSIC, "outDir": os.path.abspath(out_dir), "jobs": jobs}
        results = self._run([], request, timeout=RENDER_SECONDS).get("results")
        if not isinstance(results, list):
            raise Refusal("render-failed", "The renderer did not say what it drew.")
        return results
