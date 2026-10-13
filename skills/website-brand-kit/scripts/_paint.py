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

# the same number as _svg._NUM (ASCII digits, a digit after a point, one or two digits in an exponent; no
# alternative that overlaps another), so the two cannot drift
_NUM = r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,2})?"
_NUMBER = re.compile(r"^\s*(%s)(%%?)\s*$" % _NUM)


def _is_one(value):
    m = _NUMBER.match(value)
    if not m:
        return False
    x = float(m.group(1))
    return (x / 100.0 if m.group(2) else x) == 1.0


def _positive(width):
    m = re.match(r"^\s*(%s)" % _NUM, width)
    return True if not m else float(m.group(1)) > 0


def _alpha():
    return Refusal(
        "colour-alpha",
        "The mark is partly see-through (an opacity is set). This check reads flat, solid colours only: ask the tool "
        "for the same mark without transparency.",
    )


def resolve_paints(root, drawing, current=None):
    """The colours of the painted shapes, in the order first used."""
    colours = []

    def add(hex_colour):
        if hex_colour not in colours:
            colours.append(hex_colour)

    # "current": which of fill and stroke were written as currentColor on this element or one above it
    base = {"fill": "#000000", "stroke": "none", "stroke-width": "1", "color": None, "visibility": "visible", "current": ()}
    stack = [(root, base, True)]
    while stack:
        node, inherited, painted = stack.pop()
        props = node.props
        for k in ("opacity", "fill-opacity", "stroke-opacity"):
            if k in props:
                if not _is_one(props[k]):
                    raise _alpha()
                del props[k]
        eff = dict(inherited)
        if "color" in props:
            v = props["color"].strip(_colour.SPACE)  # only what CSS takes for white space: a no-break space beside a colour makes it none
            if v.lower() == "inherit":
                del props["color"]
            else:
                props["color"] = eff["color"] = _colour.parse_colour(v, current=inherited["color"] or current, drawn=True)
        for k in ("fill", "stroke"):
            if k not in props or props[k].strip(_colour.SPACE).lower() == "inherit":
                props.pop(k, None)
                # A paint handed down as currentColor was written out above as the colour it had there. A
                # renderer may instead give it the colour `color` is changed to here (the site's own does):
                # where the two differ the installed file would not look like the one that was checked.
                if "color" in props and k in eff["current"] and eff["color"] != eff[k]:
                    raise Refusal(
                        "colour-current",
                        "The mark paints a group with currentColor and then changes `color` inside that group. Which of "
                        "the two colours the shapes inside get depends on the program that draws the file, so the mark's "
                        "colours cannot be known from it. Ask for the SVG with every colour written out.",
                    )
                continue
            v = props[k].strip(_colour.SPACE)
            eff["current"] = tuple(c for c in eff["current"] if c != k) + ((k,) if v.lower() == "currentcolor" else ())
            if v.lower() == "none":
                props[k] = eff[k] = "none"
            else:
                props[k] = eff[k] = _colour.parse_colour(v, current=eff["color"] or current, drawn=True)
        for k in ("stroke-width", "visibility"):
            if k in props:
                if props[k].strip(_colour.SPACE).lower() == "inherit":
                    del props[k]
                else:
                    eff[k] = props[k]
        shown = painted and props.get("display", "").strip(_colour.SPACE) != "none"
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
