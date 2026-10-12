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
import subprocess

from _refusal import Refusal

HELPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render.mjs")
INTRINSIC = 1024  # the long side, in pixels, the drawing is given before it is scaled to each icon
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

    def _run(self, args, request=None, timeout=180):
        if not self.node:
            raise Refusal("no-node", NO_NODE)
        if not os.path.isdir(self.site):
            raise Refusal("no-site", NO_SITE % self.site)
        try:
            # read as UTF-8 whatever the computer's own encoding is: a warning may name a path with any letters in it
            r = subprocess.run([self.node, HELPER] + args, input=None if request is None else json.dumps(request),
                               cwd=self.site, capture_output=True, encoding="utf-8", errors="replace", timeout=timeout)
        except FileNotFoundError:
            raise Refusal("no-node", NO_NODE) from None
        except subprocess.TimeoutExpired:
            raise Refusal("render-failed", "The renderer took more than %d seconds and was stopped." % timeout) from None
        lines = [l for l in r.stdout.splitlines() if l.strip()]
        try:
            answer = json.loads(lines[-1])
            if not isinstance(answer, dict):
                raise ValueError("the answer is not a JSON object")
        except (IndexError, ValueError, RecursionError):  # no line, not JSON, or JSON nested too deep to read
            first = (r.stderr.strip().splitlines() or ["no answer"])[0][:200]
            raise Refusal("render-failed", "The renderer did not answer (%s)." % first) from None
        if not answer.get("ok"):
            code, msg = answer.get("error", "render-failed"), answer.get("message", "")
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
        results = self._run([], request).get("results")
        if not isinstance(results, list):
            raise Refusal("render-failed", "The renderer did not say what it drew.")
        return results
