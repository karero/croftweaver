"""_svg.py: read an SVG that comes from outside, and hand back text that is safe to serve.

The file may come from a design tool, code the owner pasted, or a zip. It is served from the
owner's own address once installed, so it is never copied: it is parsed as XML, checked
against an allowlist of drawing elements and attributes, and a NEW file is written from the
nodes that passed. Anything that could fetch or run something is refused by name, with the
reason in words the owner can act on. Harmless extras (a title, editor metadata) are left
out and listed in `notes`.

What is refused and why is in the plan (docs/reviews/SKILL-PLAN-website-brand-kit.md, "SVG
safety"). The parser is expat, used directly: it reports a DOCTYPE before it expands
anything, and every DOCTYPE is refused, so no entity is ever declared, let alone expanded.
Nothing here recurses deeper than MAX_DEPTH. Standard library only (Python 3.9+).

THE VALUE GRAMMAR. What this check reads is what is drawn: every value it keeps, and every value
it reads to decide something, is written in one of the forms below, and a value in any other
form is refused by name. Each form is one the site's renderer draws the same in the file as it
came and in the cleaned file, in a small icon and in a large one (tests/test_render.py draws
every one of them both ways, at 32 and at 512 pixels). GRAMMAR, further down, is this list as a
table: attribute or property, and the line it is held to.

Everywhere: plain ASCII. A blank is a space, a tab or a line break, and blanks around a value
are taken off (not around an id).

  number         an optional sign, digits, optionally a point FOLLOWED by digits, optionally e or
                 E with an optional sign and one or two digits: 5  -5  +.5  0.5  5e1  5E-02. Not
                 5. or .5.e1 or 5e100 or 0x5 or 1_0. At most 64 characters, and no larger than
                 a thousand million either way (the renderer takes a larger one for no number).
                   stroke-miterlimit (1 or more); opacity, fill-opacity, stroke-opacity (the
                   paint reader then asks for exactly 1)
  length         a number, or a number and `px`. No other unit: the renderer sizes pt, pc, mm,
                 cm, in, em and ex by the icon it is drawing, so one file gave two pictures.
                   stroke-dashoffset; not below zero: stroke-width, r, rx, ry (those two also
                   `auto`)
  position       a length, or a number and `%` (a share of the drawing's box: of its width for
                 x, of its height for y).
                   x, y, cx, cy, x1, y1, x2, y2; not below zero: width, height
  number list    numbers with blanks between them, or ONE comma (blanks may stand around it), or
                 nothing at all where the next number begins with a sign or a point (10-5, .5.5).
                 No comma first, last or twice.
                   points (an even count, 2,000 numbers at most; it may be empty)
                   stroke-dasharray (`none`, or 1 to 16 numbers, none below zero)
  transform      at most 16 of matrix(a b c d e f), translate(x) or (x y), scale(s) or (x y),
                 rotate(a) or (a x y), skewX(a), skewY(a): the name, `(`, a number list of
                 exactly that many numbers, `)`. Between two of them: blanks, one comma, or
                 nothing. It may be empty.
  path data      d: the letters MmZzLlHhVvCcSsQqTtAa, digits, `+ - . ,`, e and E, and blanks;
                 200,000 characters at most. (Read by the renderer's own reader, as it was.)
  keyword        exactly one of the words the renderer and a browser both read:
                   fill-rule, clip-rule: nonzero evenodd
                   stroke-linecap: butt round square      stroke-linejoin: miter round bevel
                   visibility: visible hidden collapse    display: inline block none inherit
                   shape-rendering: auto optimizeSpeed crispEdges geometricPrecision
                   clipPathUnits (on a clipPath): userSpaceOnUse objectBoundingBox
                   paint-order: normal, or one to three of fill stroke markers, each once
  paint          fill, stroke, color: at most 64 of the characters a colour is written in
                 (letters, digits, `# ( ) . , % + - /` and blanks), or a url(#id). The colour reader
                 (_colour.py) holds what a colour is, and refuses by name what it does not read.
  id             an ASCII letter or `_`, then letters, digits and `_ - . :`; 64 characters at most.
  class          names of ASCII letters, digits and `_ - .` with spaces between them; 200
                 characters at most.
  clip-path      `none`, or url(#id) with an id as above (blanks may stand inside the brackets;
                 80 characters at most).
  viewBox        four numbers, as a number list; the third and fourth (the box's width and height)
                 from 0.01 to 1,000,000 and neither more than 20 times the other.
  preserveAspectRatio   none, or xMinYMin, xMidYMin ... xMaxYMax, then optionally meet or slice.
  width, height of the outer <svg>   never kept: the cleaned file says its size by its viewBox
                 alone. A number above zero with px, pt, pc, mm, cm, in or nothing after it, or a
                 number and `%`. With a viewBox the two, when both are lengths, are in one unit
                 and of the viewBox's own shape (to one part in a hundred thousand): any other
                 pair would be a drawing the cleaned file sets differently in its icon. Without
                 a viewBox both are plain or px, and they are the box.

Three values that only say "nothing here" are left out without a word: filter, mask or
vector-effect of `none`, and mix-blend-mode of `normal`.

What the grammar does not close: how FAR a drawing reaches. A number may be as large as a
thousand million, and the renderer's own arithmetic runs out some eight million pixels from the
icon it is drawing (measured 2026-10-13: in a box of 10, a stroke a million wide is drawn in a
32-pixel icon and not in a 512-pixel one). Such a file is cleaned as it is written and is drawn
as the file that came is drawn, which need not be how a browser draws it. Keeping it out would
take working out where every shape lands; the icons step looks at what was really drawn instead.
"""

from __future__ import annotations

import re
from xml.parsers import expat
from xml.sax.saxutils import quoteattr

import _css
import _paint
from _refusal import Refusal  # noqa: F401  (re-exported: callers catch _svg.Refusal)

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
XHTML_NS = "http://www.w3.org/1999/xhtml"
XML_NS = "http://www.w3.org/XML/1998/namespace"

MAX_BYTES = 512 * 1024
MAX_OUTPUT = MAX_BYTES        # characters of the cleaned text (all of them ASCII): what goes in can come out again
MAX_DEPTH = 32
MAX_ELEMENTS = 5000
MAX_ATTRIBUTES = 64
MAX_STYLE_CHARS = 64 * 1024   # all the <style> text of one file together
MAX_SELECTORS = 200           # counted with the class and id names in them: each is one look at every element
MAX_DECLARATIONS = 1000
MAX_NOTES = 40
MAX_ASPECT = 20
# A viewBox outside this is no logo, and would make the renderer misjudge its density. Measured 2026-10-13: the
# renderer draws nothing at all in a box with a side under 0.004 (it takes anything below 1/256 for zero).
MIN_BOX, MAX_BOX = 1e-2, 1e6
# How far the outer svg's width and height may be from the shape of its viewBox. Measured 2026-10-13: one part in
# ten thousand already moves the drawing by a pixel's edge in a 512-pixel icon; tools write the two alike to the last digit.
ROOT_SLACK = 1e-5
# the caps of the value grammar (see the top of this file)
MAX_VALUE = 64                 # characters in one number, length, paint or id
MAX_NUMBER = 1e9               # the size of one number, either way
MAX_POINTS = 2000              # numbers in `points`
MAX_DASHES = 16                # numbers in `stroke-dasharray`
MAX_TRANSFORMS = 16            # functions in `transform`
MAX_PATH = 200_000             # characters of path data
MAX_CLASS = 200                # characters of `class`
MAX_URL = 80                   # characters of a url(#id), its brackets and blanks included

# --- elements --------------------------------------------------------------------------

DRAWING = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}
CONTAINERS = {"svg", "g", "defs", "clipPath"}
ALLOWED_ELEMENTS = DRAWING | CONTAINERS | {"style"}
# Left out without a word: they carry no picture. They hold words only (see _parse).
SILENT_ELEMENTS = {"title", "desc", "metadata"}

_ANIMATION = ["animate", "set", "animateTransform", "animateMotion", "animateColor", "mpath", "discard"]
_GRADIENT = ["linearGradient", "radialGradient", "meshgradient", "meshGradient", "pattern", "hatch", "solidcolor", "stop"]
_FILTER = ["filter"] + ["fe" + n for n in (
    "Blend ColorMatrix ComponentTransfer Composite ConvolveMatrix DiffuseLighting DisplacementMap DropShadow "
    "Flood GaussianBlur Image Merge MergeNode Morphology Offset SpecularLighting Tile Turbulence FuncR FuncG "
    "FuncB FuncA DistantLight PointLight SpotLight").split()]
REFUSED_ELEMENTS = {}
for _n in ("text", "tspan", "textPath", "tref", "altGlyph"):
    REFUSED_ELEMENTS[_n] = ("text", "The mark contains text (<%s>), which draws with whatever font the visitor has. Ask the tool to turn the letters into shapes." % _n)
for _n in _ANIMATION:
    REFUSED_ELEMENTS[_n] = ("animation", "The mark is animated (<%s>). A logo must be still: ask the tool for a version without animation." % _n)
for _n in _GRADIENT:
    REFUSED_ELEMENTS[_n] = ("gradient", "The mark uses a gradient or a pattern (<%s>). Ask the tool for flat colours only." % _n)
for _n in _FILTER:
    REFUSED_ELEMENTS[_n] = ("filter", "The mark uses a filter effect (<%s>), such as a blur or a shadow. Ask the tool for flat shapes only." % _n)
REFUSED_ELEMENTS.update({
    "script": ("script", "The file contains a script (<script>). A logo has no use for one: ask the tool for a plain SVG."),
    "foreignObject": ("foreignObject", "The file embeds a web page inside the drawing (<foreignObject>). Ask the tool for a plain SVG."),
    "image": ("image", "The file embeds a picture (<image>). Ask the tool for an SVG drawn with shapes only."),
    "a": ("link-element", "The file contains a link (<a>). Ask the tool for a plain SVG."),
    "use": ("use", "The file reuses shapes with <use>, which this check does not read. Ask the tool for a version with every shape written out."),
    "symbol": ("symbol", "The file holds a <symbol> sprite, which this check does not read. Ask the tool for one plain drawing."),
    "mask": ("mask", "The mark uses a mask. Ask the tool for flat shapes only."),
    "marker": ("marker", "The mark uses markers. Ask the tool for flat shapes only."),
    "switch": ("switch", "The file uses <switch>. Ask the tool for a plain SVG."),
    "svg": ("nested-svg", "The file has an <svg> inside an <svg>. Ask the tool for one plain drawing."),
})

# --- attributes ------------------------------------------------------------------------

# Presentation properties kept (as attributes, resolved through the cascade).
PROPS = {
    "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-miterlimit",
    "stroke-dasharray", "stroke-dashoffset", "fill-rule", "clip-rule", "opacity", "fill-opacity",
    "stroke-opacity", "color", "display", "visibility", "clip-path", "shape-rendering", "paint-order",
}
# Properties that only matter for text or the editor: dropped from a style with a note.
PROPS_DROP = {
    "font", "font-family", "font-size", "font-weight", "font-style", "font-variant", "font-stretch",
    "letter-spacing", "word-spacing", "line-height", "text-anchor", "text-decoration", "text-rendering",
    "cursor", "pointer-events", "enable-background", "-inkscape-font-specification",
}
GEOMETRY = {
    "d", "points", "x", "y", "cx", "cy", "r", "rx", "ry", "x1", "y1", "x2", "y2", "width", "height",
    "transform",
}
ROOT_ONLY = {"viewBox", "preserveAspectRatio"}
SILENT_ATTRS = {"version", "baseProfile", "role", "focusable", "tabindex", "xml:space", "enable-background", "overflow"}
REFUSED_ATTRS = {
    "filter": ("filter", "The mark uses a filter effect, such as a blur or a shadow. Ask the tool for flat shapes only."),
    "mask": ("mask", "The mark uses a mask. Ask the tool for flat shapes only."),
    "marker-start": ("marker", "The mark uses markers. Ask the tool for flat shapes only."),
    "marker-mid": ("marker", "The mark uses markers. Ask the tool for flat shapes only."),
    "marker-end": ("marker", "The mark uses markers. Ask the tool for flat shapes only."),
    "mix-blend-mode": ("blend", "The mark uses a blend mode. Ask the tool for flat shapes only."),
    "transform-origin": ("transform-origin", "The file turns or scales a shape around a point of its own (transform-origin), which not every "
                                             "program reads, so the shape would land in different places. Ask the tool for the SVG with its "
                                             "transforms applied to the shapes (flattened)."),
    "vector-effect": ("vector-effect", "The file uses vector-effect (an outline that keeps its width however the drawing is scaled), which "
                                       "not every program draws. Ask the tool to turn the outlines into shapes."),
    # measured 2026-10-12: a browser measures the dashes of an outline against it, the site's renderer does not read it
    "pathLength": ("path-length", "The file gives a shape a made-up length to measure its dashes against (pathLength), which not every "
                                  "program reads, so a dashed outline would come out differently. Ask the tool to turn the outlines into shapes."),
}
for _n in ("systemLanguage", "requiredExtensions", "requiredFeatures"):
    REFUSED_ATTRS[_n] = ("conditional", "A part of the drawing is shown only under a condition (%s), so one program draws it and another "
                                        "leaves it out. Ask the tool for a plain SVG without it." % _n)
# The one value of each that says "nothing here": left out without a word, where any other value is refused.
NO_EFFECT = {"filter": "none", "mask": "none", "vector-effect": "none", "mix-blend-mode": "normal"}

# --- the value grammar -----------------------------------------------------------------
# Each line of the grammar (see the top of this file) is one function: given the value with its
# blanks taken off, it answers None when the value is in the grammar, and otherwise why not:
# "bad" (not the form), "unit" (a number with a unit this line does not take), "below zero",
# or ("long", what there is too much of). GRAMMAR says which line each name is held to.

_BLANKS = " \t\r\n"  # what XML and CSS call white space; Python's strip(), split() and \s also take a no-break space
# ASCII digits only, and no part of a number can be read two ways: every pattern built from it
# gives its answer in one pass, however long the value. A point is followed by a digit and an
# exponent has one or two digits: the site's renderer reads `5.` as a number in path data only
# (measured 2026-10-12: a width of `5.` draws nothing, a stroke-width of `0.` draws one unit
# wide), and it does not take `0e309` for a number at all. The same number as _paint._NUM.
_NUM = r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,2})?"
_NUMBER = re.compile(_NUM)
_LENGTH = re.compile(r"(%s)(?:px)?" % _NUM)
_PERCENT = re.compile(r"(%s)%%" % _NUM)
# a number with a unit, whatever the unit: said by name, since the way out is not the same as for a slip of the pen
_WITH_UNIT = re.compile(r"%s(?:px|pt|pc|mm|cm|in|em|ex|rem|ch|vw|vh|vmin|vmax|Q|%%)" % _NUM)
# what stands between two numbers of a list, and the second of them: each alternative begins with another character
_NEXT = re.compile(r"(?:[ \t\r\n]+(?:,[ \t\r\n]*)?|,[ \t\r\n]*|(?=[+\-.]))(%s)" % _NUM)
_NOT_NEGATIVE = {"stroke-width", "r", "rx", "ry", "width", "height"}
_IDENT = r"[A-Za-z_][A-Za-z0-9_\-.:]{0,%d}" % (MAX_VALUE - 1)
_ID = re.compile(_IDENT)
_CLASS = re.compile(r"(?:[A-Za-z0-9_\-.]+(?: +[A-Za-z0-9_\-.]+)*)?")
_KEYWORDS = {
    "fill-rule": {"nonzero", "evenodd"},
    "clip-rule": {"nonzero", "evenodd"},
    "stroke-linecap": {"butt", "round", "square"},
    # measured 2026-10-12: the site's renderer reads neither `arcs` nor `miter-clip`, and keeps the join it had
    "stroke-linejoin": {"miter", "round", "bevel"},
    "visibility": {"visible", "hidden", "collapse"},
    "display": {"inline", "block", "none", "inherit"},
    "shape-rendering": {"auto", "optimizeSpeed", "crispEdges", "geometricPrecision"},
    "clipPathUnits": {"userSpaceOnUse", "objectBoundingBox"},
}
_PAINT_ORDER = {"fill", "stroke", "markers"}
_FUNCTION = re.compile(r"(matrix|translate|scale|rotate|skewX|skewY)\(([^()]*)\)")
_TAKES = {"matrix": (6,), "translate": (1, 2), "scale": (1, 2), "rotate": (1, 3), "skewX": (1,), "skewY": (1,)}
_BETWEEN = re.compile(r"[ \t\r\n]*(?:,[ \t\r\n]*)?")
_PATH_DATA = re.compile(r"[MmZzLlHhVvCcSsQqTtAa0-9eE+\-.,\s]*", re.ASCII)
_URL = r"url\([ \t\r\n]*%s[ \t\r\n]*\)"
_CLIP = re.compile(_URL % ("#" + _IDENT))
# ASCII only: a renderer reads no other script's digits or letters in a colour, and no other kind of space. An
# underscore is part of an id and of nothing else in a colour (`rgb(1_0,0,0)` is no colour to any renderer).
_PAINT = re.compile(r"""[#A-Za-z0-9 \t\r\n().,%%+\-/]{1,%d}|%s""" % (MAX_VALUE, _URL % r"""(?:#ID|"#ID"|'#ID')""".replace("ID", _IDENT)))
_ASPECT = re.compile(r"(?:none|x(?:Min|Mid|Max)Y(?:Min|Mid|Max))(?:[ \t\r\n]+(?:meet|slice))?")
_ROOT_SIZE = re.compile(r"(%s)(px|pt|pc|mm|cm|in|%%)?" % _NUM)


def _numbers(text):
    """The numbers of a number list, as they are written, or None when `text` is not one. Read left
    to right in one pass: a value that is almost a list is turned down as fast as a list is read."""
    out, pos, item = [], 0, _NUMBER
    while pos < len(text):
        m = item.match(text, pos)
        if not m:
            return None
        out.append(m.group(m.lastindex or 0))
        pos, item = m.end(), _NEXT
    return out


def _too_much(numbers, most=None, of="numbers"):
    """Why a list of numbers that is one is still not kept, or None."""
    if most is not None and len(numbers) > most:
        return ("long", "more than %s %s" % ("{:,}".format(most), of))
    for n in numbers:
        if len(n) > MAX_VALUE:
            return ("long", "a number of more than %d characters" % MAX_VALUE)
        if abs(float(n)) > MAX_NUMBER:
            return ("long", "a number larger than a thousand million")
    return None


def _one(v, pattern=_NUMBER, percent=False):
    """A number, or one written as `pattern` or (where `percent` says so) as a share."""
    m = pattern.fullmatch(v) or (percent and _PERCENT.fullmatch(v))
    if not m:
        return "unit" if _WITH_UNIT.fullmatch(v) else "bad"
    return _too_much([m.group(1) if m.lastindex else m.group()])


def _number(v):
    return _one(v)


def _miter(v):
    # below 1 there is no such limit: one program takes 1 for it and another its default
    return _one(v) or (None if float(v) >= 1 else "bad")


def _length(v):
    return _one(v, _LENGTH)


def _radius(v):
    return None if v == "auto" else _one(v, _LENGTH)


def _position(v):
    return _one(v, _LENGTH, percent=True)


def _points(v):
    numbers = _numbers(v)
    if numbers is None or len(numbers) % 2:
        return "bad"
    return _too_much(numbers, MAX_POINTS)


def _dashes(v):
    if v == "none":
        return None
    numbers = _numbers(v)
    if not numbers:
        return "bad"
    return _too_much(numbers, MAX_DASHES, "dashes") or ("below zero" if any(n.startswith("-") for n in numbers) else None)


def _transform(v):
    pos, count, why = 0, 0, None
    while pos < len(v):
        m = _FUNCTION.match(v, _BETWEEN.match(v, pos).end() if count else pos)
        numbers = _numbers(m.group(2).strip(_BLANKS)) if m else None
        if numbers is None or len(numbers) not in _TAKES[m.group(1)]:
            return "bad"
        why, pos, count = why or _too_much(numbers), m.end(), count + 1
    return ("long", "more than %d transforms" % MAX_TRANSFORMS) if count > MAX_TRANSFORMS else why


def _path_data(v):
    if not _PATH_DATA.fullmatch(v):
        return "bad"
    return ("long", "more than %s characters of path data" % "{:,}".format(MAX_PATH)) if len(v) > MAX_PATH else None


def _keyword(words):
    return lambda v: None if v in words else "bad"


def _paint_order(v):
    parts = [p for p in re.split("[%s]+" % _BLANKS, v[:MAX_VALUE + 1]) if p]
    fine = v == "normal" or (parts and len(set(parts)) == len(parts) and set(parts) <= _PAINT_ORDER)
    return None if fine and len(v) <= MAX_VALUE else "bad"


def _matches_whole(pattern, most=MAX_VALUE):
    return lambda v: None if len(v) <= most and pattern.fullmatch(v) else "bad"


def _clip_path(v):
    return None if v == "none" else _matches_whole(_CLIP, MAX_URL)(v)


def _class(v):
    return None if len(v) <= MAX_CLASS and _CLASS.fullmatch(v) else "bad"


def _root_size(v):
    m = _ROOT_SIZE.fullmatch(v)
    if not m:
        return "unit" if _WITH_UNIT.fullmatch(v) else "bad"
    return _too_much([m.group(1)])


def _later(_v):
    return None  # the viewBox is read, and refused under its own name, by _box


GRAMMAR = {
    # a number
    "stroke-miterlimit": _miter, "opacity": _number, "fill-opacity": _number, "stroke-opacity": _number,
    # a length
    "stroke-dashoffset": _length, "stroke-width": _length, "r": _length, "rx": _radius, "ry": _radius,
    # a position
    "x": _position, "y": _position, "cx": _position, "cy": _position, "x1": _position, "y1": _position, "x2": _position,
    "y2": _position, "width": _position, "height": _position,
    # a number list, a transform, path data
    "points": _points, "stroke-dasharray": _dashes, "transform": _transform, "d": _path_data,
    # a keyword
    "paint-order": _paint_order,
    # a paint, an id, a class, a clip-path
    "fill": _matches_whole(_PAINT, MAX_URL), "stroke": _matches_whole(_PAINT, MAX_URL), "color": _matches_whole(_PAINT, MAX_URL),
    "id": _matches_whole(_ID), "class": _class, "clip-path": _clip_path,
    # the outer svg
    "viewBox": _later, "preserveAspectRatio": _matches_whole(_ASPECT),
}
GRAMMAR.update((_name, _keyword(_words)) for _name, _words in _KEYWORDS.items())
ROOT_GRAMMAR = dict(GRAMMAR, width=_root_size, height=_root_size)  # what the outer svg's width and height are held to

UNIT = (
    "The file writes a number with a unit or a percent sign where this check reads a plain number (%s=%r). Programs "
    "work such a value out in different ways, so the drawing would not come out the same everywhere. Ask the tool for "
    "the drawing with plain numbers for its sizes."
)


def _bad(name, value):
    return Refusal("bad-value", "The file has a value this check cannot read (%s=%r). Ask the tool for a plainer export." % (name, str(value)[:40]))


def _validate(name, value, grammar=GRAMMAR):
    """One kept attribute or property value, held to its line of the value grammar (a colour's own
    grammar is the colour reader's, later). The value with its blanks taken off, or a Refusal."""
    v = value if name == "id" else value.strip(_BLANKS)  # a renderer takes no blank off an id, so ` a` is not the `a` a rule names
    why = grammar[name](v)
    if why is None and name in _NOT_NEGATIVE and v.startswith("-"):
        why = "below zero"
    if why is None:
        return v
    if why == "below zero":
        # a renderer may fall back to its default (a stroke one unit wide) and paint what no check listed
        raise Refusal(
            "negative-size",
            "The file gives a shape a size below zero (%s=%r), which programs draw in different ways. Ask the "
            "tool for a plainer export." % (name, v[:40]),
        )
    if why == "unit":
        raise Refusal("length-unit", UNIT % (name, v[:40]))
    if why == "bad":
        raise _bad(name, value)
    raise Refusal(
        "value-too-long",
        "The file has a value far beyond what a logo needs (%s holds %s). Ask the tool for a plainer export." % (name, why[1]),
    )


# --- the tree --------------------------------------------------------------------------

class Node(object):
    __slots__ = ("tag", "attrs", "classes", "id", "style_decls", "children", "text", "props", "parent")

    def __init__(self, tag, parent=None):
        self.tag = tag
        self.attrs = {}        # kept geometry / root attributes
        self.classes = frozenset()
        self.id = None
        self.style_decls = []  # from the style attribute
        self.children = []
        self.text = ""         # only used by <style>
        self.props = {}        # presentation properties after the cascade (not inherited)
        self.parent = parent


class Clean(object):
    """The result: the cleaned text, the box, what was left out, and the tree for the next step."""

    def __init__(self, text, view_box, notes, root, colours):
        self.text = text
        self.view_box = view_box
        self.notes = notes
        self.root = root
        self.colours = colours  # the colours the mark paints with, as hex, in the order first used


def _split(name):
    if " " in name:
        uri, local = name.rsplit(" ", 1)
        return uri, local
    return "", name


def _note(notes, text):
    """Each thing left out is said once, and the list stays short however often a file repeats it."""
    if text in notes or len(notes) > MAX_NOTES:
        return
    notes.append(text if len(notes) < MAX_NOTES else "more was left out than is listed here")


def _parse(data):
    """expat, event by event: refusals happen in document order, before anything is built that
    a later step could trip over."""
    notes = []
    state = {"depth": 0, "count": 0, "skip": 0, "skipped": "", "root": None, "stack": [], "style": 0, "ns": ""}

    def start_doctype(*_a):
        raise Refusal(
            "doctype",
            "The file has a DOCTYPE line. That is how a file asks for other files to be pulled in, so it is "
            "refused: ask the tool to export again without it, or send a different file.",
        )

    def pi(target, _data):
        if target.lower() == "xml-stylesheet":
            raise Refusal("xml-stylesheet", "The file asks for an outside style sheet (xml-stylesheet). Ask the tool for a plain SVG.")
        raise Refusal("processing-instruction", "The file contains a processing instruction (<?%s ...?>). Ask the tool for a plain SVG." % target[:20])

    def start(name, attrs):
        state["count"] += 1
        state["depth"] += 1
        if state["count"] > MAX_ELEMENTS:
            raise Refusal("too-many-elements", "The drawing has more than %d elements, far more than a logo needs." % MAX_ELEMENTS)
        if state["depth"] > MAX_DEPTH:
            raise Refusal("too-deep", "The drawing nests its elements more than %d deep, far more than a logo needs." % MAX_DEPTH)
        uri, local = _split(name)
        if state["skip"]:
            # Measured 2026-10-12: the site's renderer applies a <style> that stands inside a <title>, a
            # <metadata> or another program's element, and clips with a <clipPath> that stands there. So a
            # part that is left out holds words and another program's own elements, and nothing of a drawing.
            if uri in (SVG_NS, ""):
                raise Refusal(
                    "misplaced-element",
                    "The file has a drawing element (<%s>) inside <%s>, a part that holds notes about the drawing and "
                    "is left out. One program draws such an element, or uses its styles, and another does not. Ask the "
                    "tool for a plainer export." % (local[:30], state["skipped"]),
                )
            state["skip"] += 1
            return
        if len(attrs) > MAX_ATTRIBUTES:
            raise Refusal("too-many-attributes", "An element in the file has more than %d attributes, far more than a logo needs." % MAX_ATTRIBUTES)
        stack = state["stack"]
        if not stack:
            if local != "svg" or uri not in (SVG_NS, ""):
                raise Refusal("not-svg", "This is not an SVG drawing: the first element is <%s>, not <svg> in the SVG namespace." % local[:20])
            state["ns"] = uri
        else:
            if uri == XHTML_NS:
                raise Refusal("foreign-html", "The file has a web-page element (<%s>) inside the drawing. Ask the tool for a plain SVG." % local[:20])
            # no namespace counts only where the root has none either (pasted code). Under an SVG root,
            # xmlns="" takes an element out of the drawing for a browser, and the site's renderer draws
            # it all the same (measured 2026-10-12): so it is refused, not left out.
            if uri == "" and state["ns"]:
                raise Refusal(
                    "no-namespace",
                    "The file takes an element (<%s>) out of the drawing with xmlns=\"\". One program draws it all the "
                    "same and another leaves it out. Ask the tool for a plainer export." % local[:30],
                )
            if uri not in (SVG_NS, state["ns"]):
                _note(notes, "left out an element from another program (<%s>)" % local[:30])
                state["skip"], state["skipped"] = 1, local[:30]
                return
            if local in REFUSED_ELEMENTS:
                code, msg = REFUSED_ELEMENTS[local]
                raise Refusal(code, msg)
        if local in SILENT_ELEMENTS:
            state["skip"], state["skipped"] = 1, local
            return
        if stack and local not in ALLOWED_ELEMENTS:
            raise Refusal("unknown-element", "The file has an element this check does not know (<%s>). Ask the tool for a plainer export." % local[:30])
        if stack and (stack[-1].tag in DRAWING or stack[-1].tag == "style"):
            # never drawn there, so its colours must not be counted as the mark's
            raise Refusal(
                "misplaced-element",
                "The file has an element (<%s>) inside a <%s>, where nothing is drawn. Ask the tool for a plainer "
                "export." % (local, stack[-1].tag),
            )
        node = Node(local, stack[-1] if stack else None)
        _read_attrs(node, attrs, notes, is_root=not stack)
        if stack:
            stack[-1].children.append(node)
        else:
            state["root"] = node
        stack.append(node)

    def end(_name):
        state["depth"] -= 1
        if state["skip"]:
            state["skip"] -= 1
            return
        state["stack"].pop()

    def chars(text):
        stack = state["stack"]
        if stack and not state["skip"] and stack[-1].tag == "style":
            state["style"] += len(text)
            if state["style"] > MAX_STYLE_CHARS:
                raise Refusal("too-large", "The styles in the file are far longer than a logo needs.")
            stack[-1].text += text

    parser = expat.ParserCreate(namespace_separator=" ")
    parser.buffer_text = True
    parser.StartDoctypeDeclHandler = start_doctype
    parser.ProcessingInstructionHandler = pi
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = chars
    try:
        parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
        parser.UseForeignDTD(False)
        parser.Parse(data, True)
    except expat.ExpatError as e:
        raise Refusal("not-xml", "The file is not readable as an SVG (%s)." % expat.errors.messages.get(e.code, "bad XML")) from None
    except (ValueError, LookupError):
        # the parser asks Python for an encoding it does not know itself: utf-7, big5, one that does not exist
        raise Refusal(
            "not-xml",
            "The file is not readable as an SVG (it names a text encoding this check does not read). Ask the tool "
            "to save it as UTF-8.",
        ) from None
    if state["root"] is None:
        raise Refusal("not-xml", "The file is empty or is not readable as an SVG.")
    return state["root"], notes


def _read_attrs(node, attrs, notes, is_root):
    dropped = []
    for name, value in attrs.items():
        uri, local = _split(name)
        if local.lower().startswith("on"):
            raise Refusal("event-attribute", "The file has an event attribute (%s), which runs code. Ask the tool for a plain SVG." % local[:20])
        if local == "href":
            if not value.strip().startswith("#"):
                raise Refusal(
                    "external-link",
                    "The file has a link to something outside the drawing (%r). Ask the tool for a plain SVG." % value.strip()[:40],
                )
            continue
        if uri:  # an attribute with a prefix, the SVG one included, is not the plain one a renderer reads
            if uri not in (XLINK_NS, XML_NS):
                dropped.append(local)
            continue
        if local in REFUSED_ATTRS:
            if NO_EFFECT.get(local) == value.strip(_BLANKS):
                continue
            code, msg = REFUSED_ATTRS[local]
            raise Refusal(code, msg)
        _css.check_text(value)
        if local == "style":
            node.style_decls = _css.parse_declarations(value)
        elif local == "id":
            node.id = _validate("id", value)
            if is_root:
                _note(notes, "left out the id of the outer <svg> element")
        elif local == "class":
            node.classes = frozenset(_validate("class", value).split())
        elif local in PROPS:
            node.props[local] = _validate(local, value)
        elif is_root and local == "transform" and value.strip():
            raise Refusal(
                "root-transform",
                "The outer <svg> element has a transform (%r). The cleaned file would lose it and the drawing would "
                "shift or change size: ask the tool for the SVG without a transform on the outer svg element."
                % value.strip()[:40],
            )
        elif local in GEOMETRY or (is_root and local in ROOT_ONLY) or (local == "clipPathUnits" and node.tag == "clipPath"):
            node.attrs[local] = _validate(local, value, ROOT_GRAMMAR if is_root else GRAMMAR)
            if is_root and local in ("x", "y"):
                _note(notes, "left out %s of the outer <svg> element (where it is placed on a page, not part of the drawing)" % local)
        elif node.tag == "style" and local == "type":
            if value.lower() not in ("", "text/css"):  # as it is written: a browser takes no blank off it
                raise Refusal(
                    "style-type",
                    "A style in the file is not written in CSS (type=%r), so this check cannot read it. Ask the "
                    "tool for a plainer export." % value.strip()[:40],
                )
        elif node.tag == "style" and local == "media":
            if value.strip(_BLANKS).lower() not in ("", "all", "screen"):
                raise Refusal(
                    "style-media",
                    "A style in the file is meant for some screens or for print only (media=%r), which this check "
                    "does not read. Ask the tool for a plainer export." % value.strip()[:40],
                )
        elif local in SILENT_ATTRS or local.startswith(("data-", "aria-")):
            continue
        else:
            dropped.append(local)
    if dropped:
        _note(notes, "left out attributes this check does not use: " + ", ".join(sorted(set(d[:30] for d in dropped))[:8]))


# --- cascade ---------------------------------------------------------------------------

def _walk(node):
    """Every node, parents before children, without recursion."""
    todo = [node]
    while todo:
        n = todo.pop()
        yield n
        todo.extend(reversed(n.children))


def _matches(sel, node):
    tag, ids, classes = sel
    return (tag is None or tag == node.tag) and all(i == node.id for i in ids) and all(c in node.classes for c in classes)


def _accept(prop, value, notes):
    if prop in PROPS:
        return _validate(prop, value)
    if prop in PROPS_DROP:
        _note(notes, "left out a style that only matters for text or an editor (%s)" % prop)
        return None
    if prop in REFUSED_ATTRS:
        if NO_EFFECT.get(prop) == value.strip(_BLANKS):
            return None
        code, msg = REFUSED_ATTRS[prop]
        raise Refusal(code, msg)
    raise Refusal(
        "css-property",
        "A style in the file sets %s, which this check does not read. Ask the tool for a plainer export." % prop[:30],
    )


def _cascade(root, notes):
    """Apply the style rules and style attributes to every element's properties."""
    rules, selectors_seen, declarations_seen = [], 0, 0
    for n in _walk(root):
        if n.tag != "style":
            continue
        for selectors, decls, _order in _css.parse_stylesheet(n.text):
            # what a selector costs is one look at every element for each name in it (_css caps the names of one)
            selectors_seen += sum(max(1, len(ids) + len(classes)) for _tag, ids, classes in selectors)
            declarations_seen += len(decls)
            if selectors_seen > MAX_SELECTORS:
                raise Refusal(
                    "too-many-selectors",
                    "The styles in the file name more than %d things for their rules to apply to (tags, classes and ids), "
                    "far more than a logo needs. Ask the tool for a plainer export." % MAX_SELECTORS,
                )
            if declarations_seen > MAX_DECLARATIONS:
                raise Refusal("too-many-declarations", "The styles in the file set more than %d values, far more than a logo needs." % MAX_DECLARATIONS)
            # every rule is checked here, once, whether or not it matches an element
            kept = [(prop, _accept(prop, value, notes)) for prop, value in decls]
            rules.append((selectors, [(prop, v) for prop, v in kept if v is not None]))
    for n in _walk(root):
        if n.tag == "style":
            continue
        fixed = {}
        matched = []
        for selectors, decls in rules:
            best = None
            for sel in selectors:
                if _matches(sel, n):
                    sp = _css.specificity(sel)
                    best = sp if best is None or sp > best else best
            if best is not None:
                matched.append((best, decls))
        for _sp, decls in sorted(matched, key=lambda t: t[0]):  # stable: equal specificity keeps source order
            fixed.update(decls)
        for prop, value in n.style_decls:
            v = _accept(prop, value, notes)
            if v is not None:
                fixed[prop] = v
        n.props.update(fixed)


# --- the result ------------------------------------------------------------------------

def _root_length(text):
    """One of the outer svg's width and height as (number, unit, the number as it is written), or
    None when it is not there or is a share of the page (`100%`), which is no size."""
    m = _ROOT_SIZE.fullmatch(text) if text is not None else None
    if not m or m.group(2) == "%":
        return None
    return float(m.group(1)), m.group(2) or "px", m.group(1)


def _box(root):
    """The drawing's box: its four numbers, and the same four as the cleaned file writes them (as
    they stand in the file: nothing is rounded, so the cleaned box is the one that was read)."""
    vb = root.attrs.get("viewBox")
    w, h = _root_length(root.attrs.get("width")), _root_length(root.attrs.get("height"))
    if vb is None:
        # in px or in nothing: the renderer sizes every other unit by the icon it draws, and then the
        # box worked out here would not be the one it draws in
        if w is None or h is None or w[1] != "px" or h[1] != "px" or w[0] <= 0 or h[0] <= 0:
            raise Refusal(
                "no-size",
                "The drawing has no viewBox and no width and height in plain numbers (a percentage, or a size in mm "
                "or another unit, is no size here), so it cannot be fitted into a square icon. Ask the tool for the "
                "SVG with a viewBox.",
            )
        if not (MIN_BOX <= w[0] <= MAX_BOX and MIN_BOX <= h[0] <= MAX_BOX):
            raise Refusal("bad-view-box", "The width and height are far too small or too large to be a logo.")
        if max(w[0], h[0]) / min(w[0], h[0]) > MAX_ASPECT:
            raise Refusal("bad-view-box", "The drawing is more than %d times wider than it is tall (or the other way round): not a logo." % MAX_ASPECT)
        return (0.0, 0.0, w[0], h[0]), "0 0 %s %s" % (w[2], h[2])
    parts = _numbers(vb)
    # four numbers of the grammar and nothing else: float() alone would also take 1_0, Arabic-Indic digits, "inf"
    nums = tuple(float(p) for p in parts) if parts is not None and len(parts) == 4 and not _too_much(parts) else ()
    if len(nums) != 4 or nums[2] <= 0 or nums[3] <= 0:
        raise Refusal("bad-view-box", "The viewBox is not four numbers with a width and a height above zero (%r)." % vb[:40])
    if not all(MIN_BOX <= x <= MAX_BOX for x in nums[2:]) or not all(abs(x) <= MAX_BOX for x in nums[:2]):
        raise Refusal("bad-view-box", "The viewBox (%r) is far too small or too large to be a logo." % vb[:40])
    if max(nums[2:]) / min(nums[2:]) > MAX_ASPECT:
        raise Refusal("bad-view-box", "The drawing is more than %d times wider than it is tall (or the other way round): not a logo." % MAX_ASPECT)
    # The cleaned file keeps the viewBox and leaves the width and height out. That draws the same picture only
    # where the two say the same shape (measured 2026-10-12: a 40 by 20 svg round a 10 by 20 viewBox is drawn at
    # half the size, and a width of 1in beside a height of 192px is one shape in a small icon and another in a large one).
    if (w is not None and w[0] <= 0) or (h is not None and h[0] <= 0):
        raise Refusal(
            "root-size",
            "The outer <svg> element gives the drawing a width or a height of nothing, so a program draws nothing at "
            "all. Ask the tool for the SVG with a viewBox and no width and height.",
        )
    if w is not None and h is not None and (w[1] != h[1] or abs(w[0] * nums[3] / (h[0] * nums[2]) - 1) > ROOT_SLACK):
        raise Refusal(
            "root-size",
            "The outer <svg> element gives the drawing one shape with its width and height (%s%s by %s%s) and another "
            "with its viewBox (%r). The cleaned file keeps the viewBox alone, so the drawing would sit differently in "
            "its icons. Ask the tool for the SVG with a width and a height that fit its viewBox, or with a viewBox "
            "and no width and height." % (w[2], w[1], h[2], h[1], vb[:40]),
        )
    return nums, " ".join(parts)


class _Written(object):
    """The cleaned text as it is written, refused the moment it passes MAX_OUTPUT. One rule's value
    is written onto every element the rule applies to, so a small file can ask for a very large one
    (before 2026-10-12 a file of 228 KB was installed as a favicon of 20 MB)."""

    def __init__(self):
        self.parts, self.size = [], 0

    def add(self, text):
        self.size += len(text)
        if self.size > MAX_OUTPUT:
            raise Refusal(
                "output-too-large",
                "Written out, the drawing is far larger than a logo needs (more than %d KB): its styles put the same "
                "values on a great many elements. Ask the tool for a plainer export." % (MAX_OUTPUT // 1024),
            )
        self.parts.append(text)


def _emit(node, out, view_box=None):
    attrs = []
    if node.tag == "svg":
        attrs.append(("xmlns", SVG_NS))
        attrs.append(("viewBox", view_box))
        if "preserveAspectRatio" in node.attrs:
            attrs.append(("preserveAspectRatio", node.attrs["preserveAspectRatio"]))
    else:
        if node.id:
            attrs.append(("id", node.id))
        attrs.extend((k, v) for k, v in sorted(node.attrs.items()))
    attrs.extend((k, v) for k, v in sorted(node.props.items()))
    out.add("<" + node.tag + "".join(" %s=%s" % (k, quoteattr(v)) for k, v in attrs))
    kids = [c for c in node.children if c.tag != "style"]
    if not kids:
        out.add("/>")
        return
    out.add(">")
    for c in kids:
        _emit(c, out)
    out.add("</" + node.tag + ">")


def _finish(root, notes, current=None):
    box, written = _box(root)
    _cascade(root, notes)
    colours = _paint.resolve_paints(root, DRAWING, current)
    out = _Written()
    _emit(root, out, written)
    return Clean("".join(out.parts), box, notes, root, colours)


# --- entry point -----------------------------------------------------------------------

WEB_PAGE = (
    "This looks like a web page, or a piece of one, not an SVG drawing on its own. This version of the logo step "
    "reads an SVG file, SVG code pasted as text, or a zip of SVG files: it does not take a drawing out of a page. "
    "Ask the tool for the SVG file itself, or copy the drawing's own code, from <svg to </svg>, and paste that."
)


def clean_svg(data, source="svg", current=None):
    """Check `data` (bytes) and return a Clean, or raise Refusal.

    `data` is an .svg file or pasted SVG code, and `source` says so: "svg" is the one value there
    is (a drawing is no longer taken out of a web page). `current` is what `currentColor` means,
    if the caller says."""
    if source != "svg":
        raise Refusal("web-page", WEB_PAGE)
    if len(data) > MAX_BYTES:
        raise Refusal("too-large", "The file is larger than %d KB, far more than a logo needs." % (MAX_BYTES // 1024))
    root, notes = _parse(data)
    return _finish(root, notes, current)
