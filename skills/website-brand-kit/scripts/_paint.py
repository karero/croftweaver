"""_paint.py: which colours a mark really paints with, and its paint values rewritten as plain hex.

Read from the file's own paint values after the cascade (see _svg._cascade), the way a renderer
reads them: `fill` and `stroke`, inherited through groups, an unset fill is black, an unset
stroke is nothing, a stroke of no width paints nothing, hidden and clipping shapes paint nothing.
Every fill, stroke and color is rewritten as one hex (or `none`), so the file that is installed
says exactly what was checked. What cannot be resolved is refused by name (see _colour.py):
gradients and patterns, see-through colours, colours it does not know, and `currentColor` it was
not told the meaning of. Standard library only.
"""

from __future__ import annotations

import re

import _colour
from _refusal import Refusal

_NUMBER = re.compile(r"^\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)(%?)\s*$")


def _is_one(value):
    m = _NUMBER.match(value)
    if not m:
        return False
    x = float(m.group(1))
    return (x / 100.0 if m.group(2) else x) == 1.0


def _positive(width):
    m = re.match(r"^\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)", width)
    return True if not m else float(m.group(1)) > 0


def _alpha():
    return Refusal(
        "colour-alpha",
        "The mark is partly see-through (an opacity is set). This check reads flat, solid colours only: ask the tool "
        "for the same mark without transparency.",
    )


def resolve_paints(root, drawing, current=None, used_classes=None):
    """The colours of the painted shapes, in the order first used. `used_classes`, when given
    (a drawing taken out of a web page), is the set of class names the drawing's own styles
    mention: any other class is styled by the page, which this check cannot see."""
    colours = []

    def add(hex_colour):
        if hex_colour not in colours:
            colours.append(hex_colour)

    base = {"fill": "#000000", "stroke": "none", "stroke-width": "1", "color": None, "visibility": "visible"}
    stack = [(root, base, True)]
    while stack:
        node, inherited, painted = stack.pop()
        props = node.props
        for k in ("opacity", "fill-opacity", "stroke-opacity"):
            if k in props:
                if not _is_one(props[k]):
                    raise _alpha()
                del props[k]
        if used_classes is not None:
            for name in node.classes:
                if name not in used_classes:
                    raise Refusal(
                        "page-css",
                        "The drawing is styled by the web page around it (the class %r has no rule inside the drawing), "
                        "so its colours cannot be known from the drawing alone. Ask for the SVG file itself." % name[:30],
                    )
        eff = dict(inherited)
        if "color" in props:
            v = props["color"].strip()
            if v.lower() == "inherit":
                del props["color"]
            else:
                props["color"] = eff["color"] = _colour.parse_colour(v, current=inherited["color"] or current)
        for k in ("fill", "stroke"):
            if k not in props:
                continue
            v = props[k].strip()
            if v.lower() == "inherit":
                del props[k]
            elif v.lower() == "none":
                props[k] = eff[k] = "none"
            else:
                props[k] = eff[k] = _colour.parse_colour(v, current=eff["color"] or current)
        if "stroke-width" in props:
            eff["stroke-width"] = props["stroke-width"]
        if "visibility" in props:
            eff["visibility"] = props["visibility"]
        shown = painted and props.get("display", "").strip() != "none"
        if shown and node.tag in drawing and eff["visibility"] not in ("hidden", "collapse"):
            if node.tag != "line" and eff["fill"] != "none":
                add(eff["fill"])
            if eff["stroke"] != "none" and _positive(eff["stroke-width"]):
                add(eff["stroke"])
        below = shown and node.tag not in ("defs", "clipPath")
        for child in reversed(node.children):
            stack.append((child, eff, below))
    if not colours:
        raise Refusal(
            "blank-mark",
            "Nothing in the file is drawn with a visible colour, so there is no mark to use. Ask the tool for the SVG "
            "again.",
        )
    return colours
