"""_svg.py: read an SVG that comes from outside, and hand back text that is safe to serve.

The file may come from a design tool, code the owner pasted, or a zip. It is served from the
owner's own address once installed, so it is never copied: it is parsed as XML, checked
against an allowlist of drawing elements and attributes, and a NEW file is written from the
nodes that passed. Anything that could fetch or run something is refused by name, with the
reason in words the owner can act on. Harmless extras (a title, editor metadata) are left
out and listed in `notes`.

What is refused and why is in the plan (docs/reviews/SKILL-PLAN-website-brand-kit.md, "SVG
safety"). The parser is expat, used directly: it reports a DOCTYPE before it reads what the
DOCTYPE defines, and every DOCTYPE is refused, so no entity is ever declared, let alone expanded.
Nothing here recurses deeper than MAX_DEPTH. Standard library only (Python 3.9+).

THE VALUE GRAMMAR. What this check reads is what is drawn: every value it keeps, and every value
it reads to decide something, is written in one of the forms below, and a value in any other
form is refused by name. Each form is one the site's renderer draws the same in the file as it
came and in the cleaned file, in a small icon and in a large one (tests/test_render.py draws
every one of them both ways, at 32 and at 512 pixels). GRAMMAR, further down, is this list as a
table: attribute or property, and the line it is held to.

Everywhere: plain ASCII. A blank is a space, a tab or a line break, and blanks around a value
are taken off (not around an id). A cap on a value's length counts the whole value, its sign,
its unit and its percent sign included; and as it stands in the file, its blanks and all, no
value is longer than 8,192 characters (`d` and `points`: 200,000), whether it stands in an
attribute, in a style or in a rule (there a comment inside a value counts as so many blanks).

  number         an optional sign, digits, optionally a point FOLLOWED by digits, optionally e or
                 E with an optional sign and one or two digits: 5  -5  +.5  0.5  5e1  5E-02. Not
                 5. or .5.e1 or 5e100 or 0x5 or 1_0. At most 64 characters, and no larger than
                 a thousand million either way (the renderer takes a larger one for no number).
                   stroke-miterlimit (1 or more); opacity, fill-opacity, stroke-opacity (the
                   paint reader then asks for exactly 1)
  length         a number, or a number and `px`; 64 characters at most. No other unit: the
                 renderer sizes pt, pc, mm, cm, in, em and ex by the icon it is drawing, so one
                 file gave two pictures.
                   stroke-dashoffset; with no minus sign (`-0` too is refused): stroke-width, r,
                   rx, ry (those two also `auto`)
  position       a length, or a number and `%` (a share of the drawing's box: of its width for
                 x, of its height for y).
                   x, y, cx, cy, x1, y1, x2, y2; with no minus sign: width, height
  number list    numbers with blanks between them, or ONE comma (blanks may stand around it), or
                 nothing at all where the next number begins with a sign or a point (10-5, .5.5).
                 No comma first, last or twice. Written into the cleaned file with one blank
                 between two numbers, however the file spaced it.
                   points (an even count, 2,000 numbers at most; it may be empty). Between two
                   POINTS, that is after every second number: blanks, or a comma with or without blanks after it,
                   and nothing else (the renderer reads no comma after a blank there, and no
                   number run on to the one before)
                   stroke-dasharray (`none`, or 1 to 16 numbers, none with a minus sign; see
                   "how many dashes" below)
  transform      at most 16 of matrix(a b c d e f), translate(x) or (x y), scale(s) or (x y),
                 rotate(a) or (a x y), skewX(a), skewY(a): the name, blanks if any, `(`, a
                 number list of exactly that many numbers, `)`. Between two of them: blanks, one
                 comma, or nothing. It may be empty. Written into the cleaned file as
                 `name(a b c) name(d)`.
                 An angle (the first number of rotate, skewX and skewY) is no further from zero
                 than 100,000 degrees (refused by name). Both programs read a number in single
                 precision, which keeps a larger angle only roughly: skewX(20000070.9) was read
                 here as 90.9 degrees on from whole turns, and drawn as 90. The way out is the
                 same angle between 0 and 360.
                 None of them, nor all of them together, squashes what it is applied to flat,
                 or all but flat: one program then draws nothing of a shape that another still
                 draws (refused by name). Flat is a square squashed to a ten-thousandth as thick
                 as it is long, or thinner: for matrix(a b c d e f), a times d less b times c
                 comes to less than a ten-thousandth of a, b, c and d each squared and added up.
                 (Those squares come to a little more than the length squared, so a square left
                 exactly 10,000 times as long as it is thick is flat already: scale(1 .0001) is
                 refused, scale(1 .00011) is kept.) A scale and a skew are matrices too:
                 scale(0), and skewX and skewY from about 89.43 degrees to 90.57 (a tangent of
                 100 or more) and at every half turn on from there. And none of them, nor all of
                 them together, leaves of an area less than 1e-18 of it (not scale(1e-10): a
                 thousand million times smaller each way is the least. And not six of
                 scale(1e-9), nor two, which multiply to less). That line has room for rounding,
                 one part in a thousand million: a turn keeps an area, and scale(1e-9) rotate(6)
                 multiplies out to a hair under 1e-18 of it and is kept.
                 "All of them together" is the list multiplied from its first function to each
                 one in turn: a list that goes under one of the two lines on its way is refused,
                 though it may end above it (scale(1e-6) scale(1e-6) scale(1000) scale(1000)).
                 The list is held where it goes UNDER a line on its way, not where it goes far
                 above on its way and comes back: scale(1e8) five times, then scale(1e-9) four
                 times and scale(.01), is kept, and past a running scale of about 3.4e38 each way (the
                 largest number single precision holds) the renderer draws the shape and a browser
                 does not (made by hand, in a box of a million; see _flattens).
                 The rule looks at ONE transform attribute at a time. Transforms on elements that
                 stand inside one another (a group's and its shape's, a clip path's and that of a
                 shape in it) are not multiplied: where only together they squash a shape, scale
                 it to nothing, or undo each other, this check does not see it, the file is kept,
                 and one program may draw nothing of a shape that another draws (_flattens says
                 what was measured; nesting that goes so far was only ever made by hand).
  path data      d: the letters MmZzLlHhVvCcSsQqTtAa, digits, `+ - . ,`, e and E, and blanks;
                 200,000 characters at most. (Read by the renderer's own reader, as it was.)
  keyword        exactly one of the words the renderer and a browser both read:
                   fill-rule, clip-rule: nonzero evenodd
                   stroke-linecap: butt round square      stroke-linejoin: miter round bevel
                   visibility: visible hidden collapse    display: inline block none
                   shape-rendering: auto optimizeSpeed crispEdges geometricPrecision
                   clipPathUnits (on a clipPath): userSpaceOnUse, which is what it means left
                   out as well. `objectBoundingBox` is refused by name: the clip is then measured
                   by the box of the shape it clips, and programs work that out in different ways.
                   (On any other element the attribute means nothing: it is left out there, with
                   a note, whatever it says.)
                   paint-order: normal, or one to three of fill stroke markers, each once
                   (written with one blank between two of them)
  paint          fill, stroke, color: at most 64 of the characters a colour is written in
                 (letters, digits, `# ( ) . , % + - /` and blanks), or a url(#id). The colour reader
                 (_colour.py) holds what a colour is, and refuses by name what it does not read.
  clip-path      `none`, or url(#id) (blanks may stand inside the brackets; 80 characters at
                 most; written as `url(#id)`). The id is that of a <clipPath> in the file, and
                 stands on no other element of the file as it came: not on a second clip path,
                 not on the outer svg, not on anything that is left out (as `id` or as `xml:id`).
                 A clip path is a plain outline that clips shapes, and no more (_plain_clips).
                 Refused by name, however it is set (an attribute, a style, a rule): a clip-path
                 other than `none` on a <clipPath>, on anything inside one, or on the outer <svg>;
                 and display, whatever it says, on a <clipPath> or on a <defs>.
                 Nor do clip paths hold so much, for how often they are used, that a browser has
                 far more work with the file than a logo gives it (a browser has no time limit,
                 and the cleaned file is the site's favicon.svg): for each clip path, the numbers
                 its shapes hold times the elements clipped by it, summed over the file, come to
                 200,000 at most (_references). That keeps out the files that took a browser
                 longest; it is no bound on a browser's time (see "nor how long", below).
  id             an ASCII letter, a digit or `_`, then letters, digits and `_ - . :`; 64 characters
                 at most. This is the id a clip-path names, the one id that is kept. (A style
                 rule names an id as CSS names anything: no digit first.) Every other id is left
                 out without a word and is not read at all, as a piece of a style either: nothing
                 in the cleaned file is named by it (a style rule that named it has been written
                 out as the values it gave).
  class          names of visible ASCII characters with spaces between them; 200 characters at
                 most. A name a style rule can name (letters, digits and `_ -`, begun as a CSS
                 name is) is read for the style rules; any other (`md:h-8`, `w-1/2`) is passed
                 over. Never written.
  viewBox        four numbers, as a number list; the third and fourth (the box's width and height)
                 from 0.01 to 1,000,000 and neither more than 20 times the other.
  preserveAspectRatio   none, or xMinYMin, xMidYMin ... xMaxYMax, then optionally meet or slice.
  width, height of the outer <svg>   never kept: the cleaned file says its size by its viewBox
                 alone. A number above zero with px, pt, pc, mm, cm, in, em, ex or nothing after
                 it, or a number above zero and `%` (a share of the page: no size). With a
                 viewBox the two, when both are lengths, are in ONE unit and of the viewBox's own
                 shape to one part in a hundred: tools round the two apart, and within that line
                 an edge of the drawing lies at most a hundredth of the icon's side from where the
                 file as it came had it (half of that where the drawing is set in the middle of
                 its room, as it is unless preserveAspectRatio says otherwise). That bounds how
                 far an edge moves, not how many pixels change: a mark of fine lines can differ
                 all over. Two units, or another shape, would be a drawing the cleaned file sets
                 differently in its icon. Without a viewBox both are plain or px, and they are
                 the box.

The values that only say "nothing here" are left out without a word: filter, mask, vector-effect,
marker, marker-start, marker-mid or marker-end of `none`, mix-blend-mode of `normal`, and
isolation or image-rendering of `auto`. A property whose name starts `-inkscape-` (one editor's
own, which no program draws) is left out of a style, all of them with one note.

What is left out is not read. An attribute this check does not use (an `aria-label`, a
`data-name`, another program's own), like an id that nothing names, is never written, so it can
fetch and run nothing; it is not held to the grammar and not read as a piece of a style, whatever
it says. (An event attribute and a link are refused by what they are, before that.)

HOW FAR, AND HOW MANY DASHES. These rules are held once the box is known, on the values the
cleaned file writes (_reach). They keep the picture one picture, and keep out the two kinds of
file that took the renderer longest when they were measured (they do not bound its time: see
"nor how long a drawing takes to draw", below).

  how far        a number that places or sizes a shape is no further from zero than the box's own
                 farthest edge and a hundred times its larger side beyond it (in a box of 10 from
                 0: 1,010 either way; a share is taken of the larger side). Held: x, y, cx, cy,
                 x1, y1, x2, y2, width, height, r, rx, ry, every number of `points`, every number
                 of path data (an arc's two flags are no numbers), stroke-width,
                 stroke-dashoffset, and in a transform every number but an angle (the first of
                 rotate, skewX and skewY: an angle has its own line, under `transform`).
                 Each number is held as it is written, not as a transform leaves it: a drawing
                 made far larger than its box and scaled down to fit by a group (a font's letter
                 1,700 units tall in a box of 16) is refused as well, though nothing of it lies
                 outside the box. The refusal names that way too.
  how many dashes   where a dash list is set (stroke-dasharray, not `none`), no dash or gap is
                 smaller than a thousandth of the box's larger side, unless it is 0. Where it
                 applies to a shape that paints an outline (set on it, handed down, or from a
                 rule), the shape is a line, rect, circle, ellipse, polyline or polygon, not a
                 <path>: its outline is then no longer than its numbers say (_outline: each
                 number worked out as a program does, a share of the box's width for x and of
                 its height for y, before one is taken from another). And all such outlines of a
                 file together are cut into at most 100,000 dashes and gaps.

Refused by name wherever they stand, beside what the element and attribute lists further down
refuse: an element of the XInclude namespaces (the renderer fetches what it names), and a
`title` on a <style> (a browser then takes the style for one of several to choose between).

What the grammar does not close: where a drawing ends up. Each number is held to the box, and
what the numbers make together is not worked out: a transform multiplies (16 of them, on groups
32 deep), a path's small steps add up, and an arc or a run of smooth curves can swing far out
from near numbers. So a shape can still lie far outside the box, where the renderer's own
arithmetic runs out (measured 2026-10-13: in a box of 10, a stroke a million wide is drawn in a
32-pixel icon and not in a 512-pixel one; that stroke is refused now, the same reach built from a
transform is not). Such a file is cleaned as it is written and is drawn as the file that came is
drawn, which need not be how a browser draws it. The icons step looks at what was really drawn:
at the 32-pixel favicon and at one 256-pixel picture, not at every size, so a mark that came out
blank at 512 pixels only would pass it.

Nor how long a drawing takes to draw. The dash budget above bounds the NUMBER of dashes a file's
outlines are cut into, and no more than that: how long the renderer takes also grows with how
wide and how round each dash is (measured 2026-10-13 at load 90 to 460: a dashed polygon inside
every cap, its outline 10 wide with round joins, took 7.3 seconds of processor time for one icon
at 240 sides and was stopped after 60 at 500 sides, a file of 2,702 characters). Drawings with no
dash in them are slow inside every cap as well (one 512-pixel icon at load 10: 11 to 12 seconds
for one outlined path of 40,000 to 50,000 short turns, 4 for 4,990 circles with wide outlines).
So for EVERY drawing, dashed or not, how long it takes is bounded by one thing: the time limit of
the renderer's call (_render.RENDER_SECONDS, for all the icons of that call). A file that passes
it is refused there, with the sentence that says what to ask for.

A browser has no such limit, and nothing here bounds how long one takes over the cleaned file.
The count of clip work (see `clip-path`) keeps out what took one longest: 11.9 seconds at 512
pixels for 4,900 shapes clipped by one path of 400 turns (Chromium, load 10 to 13). Under that
count a browser's time still grows with the number of clipped shapes alone, unless the clip path
is one plain rect. Measured 2026-10-13 (Chromium, wall clock, load 13): 4,990 shapes clipped by
one path of 19 turns, a count of 199,600, took 4.2 seconds at 512 pixels and 0.4 at 32, the size a
favicon is drawn at; clipped by one circle, 1.6 and 0.1; by one rect, 0.2 and 0.1; and 249 shapes
clipped by one path of 400 turns, 199,698, took 0.2. (On the same machine at load 110 to 135 the
first of those took 5.0 to 7.3 seconds. The renderer's processor time for one 512-pixel icon of
the four: 0.8 to 1.1 seconds, 0.3, 0.1 and 1.4.)
"""

from __future__ import annotations

import math
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
_XML_ID = XML_NS + " id"   # `xml:id`, as the parser names it
XINCLUDE_NS = ("http://www.w3.org/2001/XInclude", "http://www.w3.org/2003/XInclude")  # the standard's, and its draft's

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
# How far the outer svg's width and height may be from the shape of its viewBox: one part in a hundred. Tools round
# the two apart (an export of 283.46px by 141.73px round a viewBox of 283.5 by 141.7), and the cleaned file, which
# keeps the viewBox alone, then has an edge of the drawing up to a hundredth of the icon's side from where the file as
# it came had it: half a hundredth where the drawing is set in the middle of its room (the default), a whole one where
# preserveAspectRatio pushes it to a side (xMinYMin, xMaxYMax, xMidYMax). Measured 2026-10-13 at the line itself (10
# by 20.19 round 10 by 20), of the 262,144 pixels of a 512-pixel icon: 3,348 differ in the middle and up to 3,756 at a
# side, all of them along the edges of the shapes, and none of a 32-pixel icon's; no edge has moved by more than 4
# pixels of the 512, or 2 in the middle (tests/test_render.py finds the edges and holds them to the hundredth). That
# is how far an edge moves, not how much of a picture changes: of a mark of a hundred fine lines 98,240 to 113,226
# pixels differ.
ROOT_SLACK = 1e-2
# the caps of the value grammar (see the top of this file)
MAX_VALUE = 64                 # characters in one number, length, paint or id
MAX_RAW = 8192                 # characters of any other value as it stands in the file, its blanks and all
MAX_NUMBER = 1e9               # the size of one number, either way
MAX_FAR = 100                  # how many times the box's larger side a number that places or sizes a shape may be from the box
MIN_DASH = 1e-3                # the smallest dash or gap, as a share of the box's larger side
MAX_DASH_PIECES = 100000       # dashes and gaps in all the dashed outlines of one file together
MAX_POINTS = 2000              # numbers in `points`
MAX_DASHES = 16                # numbers in `stroke-dasharray`
MAX_TRANSFORMS = 16            # functions in `transform`
MAX_PATH = 200_000             # characters of path data, and of `points`
MAX_CLASS = 200                # characters of `class`
MAX_URL = 80                   # characters of a url(#id), its brackets and blanks included
# What squashes a shape flat (see `transform` at the top, and _flattens).
MAX_SQUASH = 10000             # a transform leaves a square LESS than this many times as long as it is thick (exactly this many is flat)
MIN_AREA = 1e-18               # the least a transform leaves of an area, one function of it or all of them multiplied: a thousand million times smaller each way
AREA_ROUNDING = 1e-9           # the room that line leaves for rounding, as a share of it: a turn keeps an area, and multiplied out it comes a hair short
MAX_ANGLE = 100000             # degrees, either way, in rotate, skewX and skewY: single precision keeps an angle up to here to a hundredth of a degree
# A browser's work on clip paths: for each one, the numbers its shapes hold times the elements clipped by it, summed.
MAX_CLIP_WORK = 200000

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
    "cursor", "pointer-events", "enable-background",
}
# One editor's own properties, which no program draws (-inkscape-stroke, -inkscape-font-specification): any
# property whose name starts so is dropped from a style, all of them with the one note.
EDITOR_PREFIX = "-inkscape-"
GEOMETRY = {
    "d", "points", "x", "y", "cx", "cy", "r", "rx", "ry", "x1", "y1", "x2", "y2", "width", "height",
    "transform",
}
ROOT_ONLY = {"viewBox", "preserveAspectRatio"}
SILENT_ATTRS = {"version", "baseProfile", "role", "focusable", "tabindex", "xml:space", "enable-background", "overflow"}
REFUSED_ATTRS = {
    "filter": ("filter", "The mark uses a filter effect, such as a blur or a shadow. Ask the tool for flat shapes only."),
    "mask": ("mask", "The mark uses a mask. Ask the tool for flat shapes only."),
    "marker": ("marker", "The mark uses markers. Ask the tool for flat shapes only."),
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
# The one value of each that says "nothing here": left out without a word, where any other value is refused
# (another value of `isolation` or `image-rendering` is refused in a style, as any property this check does not
# read is, and as an attribute it is left out with a note, as any attribute this check does not use is).
NO_EFFECT = {
    "filter": "none", "mask": "none", "vector-effect": "none", "mix-blend-mode": "normal",
    "marker": "none", "marker-start": "none", "marker-mid": "none", "marker-end": "none",
    "isolation": "auto", "image-rendering": "auto",
}

# --- the value grammar -----------------------------------------------------------------
# Each line of the grammar (see the top of this file) is one function: given the value with its
# blanks taken off, it answers None when the value is in the grammar, and otherwise why not:
# "bad" (not the form), "unit" (a number with a unit this line does not take), "below zero",
# ("long", what there is too much of), ("flat", the function of a transform that squashes a
# shape flat), or ("angle", the function of a transform whose angle is too large to be read
# exactly). GRAMMAR says which line each name is held to.

_BLANKS = " \t\r\n"  # what XML and CSS call white space; Python's strip(), split() and \s also take a no-break space
# ASCII digits only, and no part of a number can be read two ways: every pattern built from it
# gives its answer in one pass, however long the value. A point is followed by a digit and an
# exponent has one or two digits: the site's renderer reads `5.` as a number in path data only
# (measured 2026-10-12: a width of `5.` draws nothing, a stroke-width of `0.` draws one unit
# wide), and it does not take `0e309` for a number at all. The same number as _paint._NUM and _colour._NUM, with
# the same limit on its length (MAX_VALUE here, _colour.MAX_NUMBER_CHARS there): the tests hold the three to each other.
_NUM = r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,2})?"
_NUMBER = re.compile(_NUM)
_LENGTH = re.compile(r"(%s)(?:px)?" % _NUM)
_PERCENT = re.compile(r"(%s)%%" % _NUM)
# a number with a unit, whatever the unit: said by name, since the way out is not the same as for a slip of the pen
_WITH_UNIT = re.compile(r"%s(?:px|pt|pc|mm|cm|in|em|ex|rem|ch|vw|vh|vmin|vmax|Q|%%)" % _NUM)
# what stands between two numbers of a list, and the second of them: each alternative begins with another character
_NEXT = re.compile(r"(?:[ \t\r\n]+(?:,[ \t\r\n]*)?|,[ \t\r\n]*|(?=[+\-.]))(%s)" % _NUM)
# What stands between two POINTS of `points`, and the first number of the second: blanks, or a comma with or without
# blanks after it (`0,0,10,10` and `0,0, 10,10` both read).
# Measured 2026-10-13: the site's renderer reads no comma after a blank there and no number run on to the one before
# (`1,1 ,9,1` and `1 1-9 1` draw nothing), though it reads both between the two numbers of one point.
_NEXT_POINT = re.compile(r"(?:[ \t\r\n]+|,[ \t\r\n]*)(%s)" % _NUM)
_NOT_NEGATIVE = {"stroke-width", "r", "rx", "ry", "width", "height"}
# Measured 2026-10-13: the site's renderer and a browser both find a clip path by an id that starts with a digit
# (one common design tool writes such ids on nearly every shape). A style rule cannot name one (`#8c` is no selector).
_IDENT = r"[A-Za-z0-9_][A-Za-z0-9_\-.:]{0,%d}" % (MAX_VALUE - 1)
_ID = re.compile(_IDENT)
_CLASS = re.compile(r"(?:[!-~]+(?: +[!-~]+)*)?")   # names of visible ASCII characters, spaces between them
_KEYWORDS = {
    "fill-rule": {"nonzero", "evenodd"},
    "clip-rule": {"nonzero", "evenodd"},
    "stroke-linecap": {"butt", "round", "square"},
    # measured 2026-10-12: the site's renderer reads neither `arcs` nor `miter-clip`, and keeps the join it had
    "stroke-linejoin": {"miter", "round", "bevel"},
    "visibility": {"visible", "hidden", "collapse"},
    # measured 2026-10-13: `inherit` on a shape inside a clip path makes the site's renderer draw nothing of what is
    # clipped, where a browser clips as if the word were not there
    "display": {"inline", "block", "none"},
    "shape-rendering": {"auto", "optimizeSpeed", "crispEdges", "geometricPrecision"},
    # `objectBoundingBox` is refused by name before this line is asked (_read_attrs): measured 2026-10-13, with a
    # transform on the clip path as well the site's renderer and a browser clip differently (4,000 against 5,000 of
    # 10,000 pixels), and a straight line clipped so is drawn whole by the one and not at all by the other
    "clipPathUnits": {"userSpaceOnUse"},
}
_PAINT_ORDER = {"fill", "stroke", "markers"}
_FUNCTION = re.compile(r"(matrix|translate|scale|rotate|skewX|skewY)[ \t\r\n]*\(([^()]*)\)")
_TAKES = {"matrix": (6,), "translate": (1, 2), "scale": (1, 2), "rotate": (1, 3), "skewX": (1,), "skewY": (1,)}
_ANGLE_FIRST = ("rotate", "skewX", "skewY")   # their first number is an angle, which places nothing by its size
_BETWEEN = re.compile(r"[ \t\r\n]*(?:,[ \t\r\n]*)?")
_PATH_DATA = re.compile(r"[MmZzLlHhVvCcSsQqTtAa0-9eE+\-.,\s]*", re.ASCII)
_URL = r"url\([ \t\r\n]*%s[ \t\r\n]*\)"
_CLIP = re.compile(_URL % ("#(" + _IDENT + ")"))
# ASCII only: a renderer reads no other script's digits or letters in a colour, and no other kind of space. An
# underscore is part of an id and of nothing else in a colour (`rgb(1_0,0,0)` is no colour to any renderer).
_PAINT = re.compile(r"""[#A-Za-z0-9 \t\r\n().,%%+\-/]{1,%d}|%s""" % (MAX_VALUE, _URL % r"""(?:#ID|"#ID"|'#ID')""".replace("ID", _IDENT)))
_ASPECT = re.compile(r"(?:none|x(?:Min|Mid|Max)Y(?:Min|Mid|Max))(?:[ \t\r\n]+(?:meet|slice))?")
_ROOT_SIZE = re.compile(r"(%s)(px|pt|pc|mm|cm|in|em|ex|%%)?" % _NUM)
# Path data is the renderer's own to read (see `path data` at the top). These find its numbers, to see how far they
# reach: a number as that reader takes one (a point may end it, an exponent may be long), and what stands between two.
_PATH_NUMBER = re.compile(r"[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
_PATH_GAP = re.compile(r"[ \t\r\n,]*")
_COMMANDS = "MmZzLlHhVvCcSsQqTtAa"


def _numbers(text, points=False):
    """The numbers of a number list, as they are written, or None when `text` is not one. Read left
    to right in one pass: a value that is almost a list is turned down as fast as a list is read.
    In a list of `points` every second gap is the one between two points."""
    out, pos, item = [], 0, _NUMBER
    while pos < len(text):
        m = item.match(text, pos)
        if not m:
            return None
        out.append(m.group(m.lastindex or 0))
        pos, item = m.end(), _NEXT if len(out) % 2 or not points else _NEXT_POINT
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
    """A number, or one written as `pattern` or (where `percent` says so) as a share. The cap on its
    length counts the whole value, its sign, its unit and its percent sign included."""
    m = pattern.fullmatch(v) or (percent and _PERCENT.fullmatch(v))
    if not m:
        return "unit" if _WITH_UNIT.fullmatch(v) else "bad"
    if len(v) > MAX_VALUE:
        return ("long", "more than %d characters" % MAX_VALUE)
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
    numbers = _numbers(v, points=True)
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


def _linear(name, numbers):
    """What one function of a transform does to a shape's form: the a, b, c and d of its matrix (where it moves the
    shape to changes nothing here)."""
    n = [float(x) for x in numbers]
    if name == "matrix":
        return n[0], n[1], n[2], n[3]
    if name == "scale":
        return n[0], 0.0, 0.0, n[-1]
    if name == "rotate":
        turn = math.radians(n[0])
        return math.cos(turn), math.sin(turn), -math.sin(turn), math.cos(turn)
    if name == "skewX":
        return 1.0, 0.0, math.tan(math.radians(n[0])), 1.0
    if name == "skewY":
        return 1.0, math.tan(math.radians(n[0])), 0.0, 1.0
    return 1.0, 0.0, 0.0, 1.0


def _flattens(matrix):
    """Does a transform squash what it is applied to flat, or all but flat? Measured 2026-10-13, on one of two
    shapes inside a clip path. scale(0), scale(1 0), a matrix whose a times d is its b times c: the site's renderer
    draws nothing at all of what is clipped, a browser clips by the other shape. The same for a scale so small
    that the renderer, which reads a number in single precision, takes it for 0 (scale(1e-46)); for small scales
    that multiply to nothing (five of scale(1e-40)); and for sixteen steep skews, none of them flat, that multiply
    to a matrix too lopsided to work with (skewX(89.4) skewY(89.4), eight times over). A skew near a quarter turn
    the other way round: the renderer clips by the other shape and a browser draws less (skewX(89.999)) or nothing
    (skewX(89.99999), skewX(90)); at 89.99 degrees, a tangent of 5,730, the two still agree.
    Where these were measured: by hand, each file drawn by the site's renderer and by headless Chromium at 100 by 100
    pixels and the pixels of each colour counted, as the file came and cleaned. The tests have no browser and do not
    draw that comparison again: tests/test_render.py draws the rows it rests on with the renderer alone (the file as
    it came against the cleaned file, on the kept side of each line), and holds the refused ones against the picture
    the browser drew.
    So the line is not "exactly 0". It is how flat a square comes out, about as thin for its length as a times d
    less b times c is for a, b, c and d squared and added up: that share is no smaller than one in MAX_SQUASH. A
    square left exactly MAX_SQUASH times as long as it is thick is refused already, since the squares added up come
    to a little more than its length squared (scale(10000 1) and scale(1 .0001) are refused, scale(1 .00011) is
    kept; a skew's tangent stays under 100). And of an area no less is left than MIN_AREA of it, to one part in a
    thousand million (AREA_ROUNDING), which is room for rounding and no more: a turn keeps an area, and
    scale(1e-9) rotate(6), like scale(.001) three times and then rotate(6), multiplies out to 9.999999999999999e-19
    of it. Both were refused for that hair for one round; scale(1e-9) scale(.99999999), a hundred-millionth under
    each way, still is.

    _transform asks this of each function of a `transform`, and of the list multiplied from its first function to
    each one in turn, so the list is held to the same two lines as one function. Two of scale(1e-9), or six, each
    exactly at the least area, were kept until 2026-10-13 (the list was held to the first line alone). Measured that
    day: a group whose list multiplies to a scale of 1e-39 each way (scale(.001) thirteen times), round a group that
    scales up again by as much, is drawn by the site's renderer and not by a browser (twelve times, 1e-36: by both).
    And ONE list that goes down to 1e-45 or 1e-54 each way and comes up again (scale(1e-9) five or six times, then
    scale(1e8) six or seven times, in a box of a million) is drawn by the renderer, and by a browser wrongly or not
    at all (down to 1e-36 and up again: alike by both). So the list is held on its way, not only at its end.
    It is held where it goes UNDER a line on its way, not where it goes far above on its way and comes back: there
    is no line above. Made by hand and measured 2026-10-13, in a box of a million: scale(1e8) five times or more,
    then scales down again till the list ends at a scale of 100 (scale(1e-9) four times and scale(.01)), is kept, and
    past a running scale of about 3.4e38 each way (the largest number single precision holds) the renderer draws the
    shape and a browser draws nothing of it (measured: at 1e39 the two part, at 1e38 both draw it).

    What this does NOT see: it looks at ONE `transform` attribute at a time. The transforms of elements that stand
    inside one another (a group's and its shape's, a clip path's and that of a shape in it) are not multiplied.
    Where only together they squash a shape, or scale it to nothing, or where one undoes what another did, each
    attribute passes and the file is kept, though one of the two programs may draw nothing of the shape. Made by
    hand and measured 2026-10-13: four groups of steep skews (89.4 degrees, across and down in turn) round four that
    undo them are drawn by a browser and not by the renderer; three round three are drawn by both. (Groups scaled
    down by 1,000, fourteen deep, round fourteen scaled up again were drawn alike by both.) No export of a design
    tool was seen to nest so."""
    a, b, c, d = matrix
    area = abs(a * d - b * c)
    return not (area >= MIN_AREA * (1 - AREA_ROUNDING) and area * MAX_SQUASH >= a * a + b * b + c * c + d * d)   # (`not`: a number too large to work with is turned down too)


def _transform(v):
    pos, count, why, all_of_them = 0, 0, None, (1.0, 0.0, 0.0, 1.0)
    while pos < len(v):
        m = _FUNCTION.match(v, _BETWEEN.match(v, pos).end() if count else pos)
        numbers = _numbers(m.group(2).strip(_BLANKS)) if m else None
        if numbers is None or len(numbers) not in _TAKES[m.group(1)]:
            return "bad"
        why, pos, count = why or _too_much(numbers), m.end(), count + 1
        if why is None and m.group(1) in _ANGLE_FIRST and not abs(float(numbers[0])) <= MAX_ANGLE:
            why = ("angle", m.group())
        if why is None and count <= MAX_TRANSFORMS:
            (a, b, c, d), (e, f, g, h) = all_of_them, _linear(m.group(1), numbers)
            all_of_them = (a * e + c * f, b * e + d * f, a * g + c * h, b * g + d * h)
            why = ("flat", m.group()) if _flattens((e, f, g, h)) else ("flat", v) if _flattens(all_of_them) else None
    return ("long", "more than %d transforms" % MAX_TRANSFORMS) if count > MAX_TRANSFORMS else why


def _path_data(v):
    return None if _PATH_DATA.fullmatch(v) else "bad"   # how long it may be: see _validate


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


def _classes(v):
    """The names of a class value a style rule can name. Any other (`md:h-8`, `w-1/2`: the names of a
    style library, on a pasted icon) is passed over: no selector this check reads could name it, a
    program splits a class value at its blanks and nowhere else, and a class is never written."""
    return frozenset(name for name in v.split(" ") if _css.is_name(name))


def _root_size(v):
    return _one(v, _ROOT_SIZE)


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


def _too_long(name, what):
    return Refusal(
        "value-too-long",
        "The file has a value far beyond what a logo needs (%s holds %s). Ask the tool for a plainer export." % (name, what),
    )


def _written(name, v):
    """A value of the grammar as the cleaned file writes it: a list with one blank between two of its
    entries and nothing else, however the file spaced it (it may have put 400,000 blanks there)."""
    if name in ("points", "stroke-dasharray") and v != "none":
        return " ".join(_numbers(v))   # (a list of points that is one is a number list too)
    if name == "transform":
        return " ".join("%s(%s)" % (m.group(1), " ".join(_numbers(m.group(2).strip(_BLANKS)))) for m in _FUNCTION.finditer(v))
    if name in ("paint-order", "preserveAspectRatio"):
        return " ".join(part for part in re.split("[%s]+" % _BLANKS, v) if part)
    if name == "clip-path" and v != "none":
        return "url(#%s)" % _CLIP.fullmatch(v).group(1)
    return v


def _validate(name, value, grammar=GRAMMAR):
    """One kept attribute or property value, held to its line of the value grammar (a colour's own
    grammar is the colour reader's, later). The value as the cleaned file writes it (its blanks
    taken off, a list set out plainly), or a Refusal."""
    v = value if name == "id" else value.strip(_BLANKS)  # a renderer takes no blank off an id, so ` a` is not the `a` a clip path is named by
    line = grammar.get(name)
    if line is None:
        # every kept name has its line (tests/test_svg_safety.py holds the lists to the table); should one ever lack it, it is not kept
        raise Refusal("no-grammar", "The file sets %s, which this check has no rule for. Ask the tool for a plainer export." % name[:30])
    why = line(v)
    if why is None and name in _NOT_NEGATIVE and v.startswith("-"):
        why = "below zero"
    most = MAX_PATH if name in ("d", "points") else MAX_RAW
    if why is None and len(value) > most:  # as it stands in the file: the blanks round it and inside it count
        why = ("long", "more than %s characters" % "{:,}".format(most))
    if why is None:
        return _written(name, v)
    if why == "below zero":
        # a renderer may fall back to its default (a stroke one unit wide) and paint what no check listed
        raise Refusal(
            "negative-size",
            "The file gives a shape a size written with a minus sign (%s=%r), which programs draw in different ways. "
            "Ask the tool for a plainer export." % (name, v[:40]),
        )
    if why == "unit":
        raise Refusal("length-unit", UNIT % (name, v[:40]))
    if why == "bad":
        raise _bad(name, value)
    if why[0] == "flat":
        raise Refusal(
            "flat-transform",
            "The file has a transform that squashes what it is applied to flat, or all but flat, at its end or at a step "
            "on its way (%s). Programs do not agree on what is left to draw then: one draws nothing of a shape that "
            "another still draws. Ask the tool "
            "for the SVG without that part, or with its transforms applied to the shapes." % " ".join(why[1].split())[:40],
        )
    if why[0] == "angle":
        raise Refusal(
            "angle-too-large",
            "The file turns or slants a shape by an angle of more than %s degrees (%s). Programs keep so large a number "
            "only roughly, so the shape is not drawn as the angle says, and not the same by every program. Ask the tool "
            "for the same angle written between 0 and 360." % ("{:,}".format(MAX_ANGLE), " ".join(why[1].split())[:40]),
        )
    raise _too_long(name, why[1])


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


class Member(bytes):
    """The bytes of one file of a package, which know the file's name: clean_svg says the name in
    every refusal of such a file (a package may hand over two files, the mark and its one-colour
    version, and a refusal that names neither leaves the owner to guess)."""

    def __new__(cls, data, name):
        self = super().__new__(cls, data)
        self.name = name
        return self


def in_package(name, refusal):
    """The same refusal, said of one file of a package by its name: the whole name, as the package holds it (it is one
    that _zipin.open_zip has passed: _zipin.MAX_NAME characters at most, and nothing in it that cannot be seen). Cut
    short, two files whose names begin alike were called the same."""
    return Refusal(refusal.code, "In the package, the file %r: %s" % (name, refusal))


class Clean(object):
    """The result: the cleaned text, the box, what was left out, and the tree for the next step."""

    def __init__(self, text, view_box, notes, root, colours):
        self.text = text
        self.view_box = view_box
        self.notes = notes
        self.root = root
        self.colours = colours  # the colours the mark paints with, as hex, in the order first used


# The two forms of a DOCTYPE, each with the way out that exists for it. A declaration can stand on a line of its
# own, run over several lines, or share its line with the <svg that follows: what is deleted is the declaration, from
# its `<!DOCTYPE` to the `>` that ends it, not "the line", and not up to the line's last `>` (said as "its last >", an
# owner could take that one, and with it the <svg). An address in quotes may hold a `>` of its own, which does not end
# the declaration: only a file made by hand has one, and the sentence is true of it as well. One that defines
# names of its own (one common tool's "save as" writes the addresses of its namespaces so, and the outer <svg> then
# uses them) cannot be deleted: without the definitions the rest of the file is not readable (measured 2026-10-13).
# A declaration without square brackets can bring names in as well, from the outside file it names (SYSTEM "brand.dtd",
# and then fill="&brand;"): so the first sentence does not promise that the file reads once the declaration is gone.
# It says what to do if it does not, and NO_SUCH_NAME, the refusal such a file then meets, says the same.
NEEDS_AN_EXPORT = "drawing needs what the declaration brought in: ask the tool for an export without a DOCTYPE."
DOCTYPE = (
    "The file has a DOCTYPE declaration. That is how a file asks for other files to be pulled in, so it is refused. "
    "Open the file in a text editor and delete the declaration: everything from <!DOCTYPE up to and including the > that "
    "ends the declaration, wherever the lines break, and nothing else (an <svg that comes after it stays). If the file cannot "
    "be read after that, the " + NEEDS_AN_EXPORT
)
DOCTYPE_DEFINES = (
    "The file has a DOCTYPE declaration that holds definitions of its own (the part in square brackets). That is "
    "how a file asks for other files to be pulled in, so it is refused. This one cannot simply be deleted: the rest "
    "of the file may use the names it defines, and is then not readable without them. Ask the tool for an export "
    "without a DOCTYPE (a plain SVG, without the tool's own editing data)."
)
# A file with no DOCTYPE (none is ever read: see start_doctype) that uses a name nothing defines. Two kinds of file meet
# this, and the sentence gives each its own way on, the commoner first. Pasted code that never had a DOCTYPE and holds a
# web page's name for a character (&nbsp; in a title, &copy; in a label: XML itself defines five names, and a web page
# many more): "ask for an export without a DOCTYPE" alone asked its owner for the file she had. And a file whose
# DOCTYPE was deleted as the sentence above says, where the declaration had defined the name.
NO_SUCH_NAME = (
    "The file is not readable as an SVG: it uses a name that nothing in it defines (a name written between & and ;, "
    "for example &nbsp;). Where the name stands for a character, as it does on a web page, open the file in a text "
    "editor and put the character itself in its place (but write & as &amp; and < as &lt;, in small letters: those two "
    "cannot stand alone), or take the name out, its & and its ; too. Where the file had "
    "a DOCTYPE declaration that was deleted, the " + NEEDS_AN_EXPORT
)


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
    ids = {}   # every id in the file as it came, and how often it stands there: see _references
    state = {"depth": 0, "count": 0, "skip": 0, "skipped": "", "root": None, "stack": [], "style": 0, "ns": ""}

    def start_doctype(_name, _system, _public, defines):
        # called before anything the declaration defines itself (the part in square brackets) is read
        raise Refusal("doctype", DOCTYPE_DEFINES if defines else DOCTYPE)

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
        if uri in XINCLUDE_NS:
            # Measured 2026-10-13: the site's renderer fetches what such an element names and draws it, or applies the
            # styles in it, wherever the element stands (inside <metadata> too). It is only ever given the cleaned
            # text, which holds no such element; the file as it came would still be another drawing than the cleaned one.
            raise Refusal(
                "xinclude",
                "The file pulls in another file (an include element, <%s>), so not all of what it draws is in the file "
                "itself. Ask the tool for a plain SVG with everything in the one file." % local[:20],
            )
        for attr, value in attrs.items():
            if attr in ("id", _XML_ID):   # on any element, a left-out one and the outer svg too
                ids[value] = ids.get(value, 0) + 1
        if state["skip"]:
            # Measured 2026-10-12: the site's renderer applies a <style> that stands inside a <title>, a
            # <metadata> or another program's element, and clips with a <clipPath> that stands there. So a
            # part that is left out holds words and another program's own elements, and nothing of a drawing.
            if uri in (SVG_NS, ""):
                raise Refusal(
                    "misplaced-element",
                    "The file has an element of the drawing (<%s>) inside <%s>, a part that holds notes about the drawing "
                    "and is left out. One program draws such an element, or uses its styles, and another does not. Ask "
                    "the tool for a plainer export." % (local[:30], state["skipped"]),
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
        why = expat.errors.messages.get(e.code, "bad XML")
        raise Refusal("not-xml", NO_SUCH_NAME if why == expat.errors.XML_ERROR_UNDEFINED_ENTITY else "The file is not readable as an SVG (%s)." % why) from None
    except (ValueError, LookupError):
        # the parser asks Python for an encoding it does not know itself: utf-7, big5, one that does not exist
        raise Refusal(
            "not-xml",
            "The file is not readable as an SVG (it names a text encoding this check does not read). Ask the tool "
            "to save it as UTF-8.",
        ) from None
    if state["root"] is None:
        raise Refusal("not-xml", "The file is empty or is not readable as an SVG.")
    return state["root"], notes, ids


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
        if NO_EFFECT.get(local) == value.strip(_BLANKS):
            continue
        if local in REFUSED_ATTRS:
            code, msg = REFUSED_ATTRS[local]
            raise Refusal(code, msg)
        if local == "id":
            # As it is written, and not read at all, by the style check either: a layer may be called `javascript:logo`.
            # It is kept only where a clip path is named by it (_references), and then it is a name of the grammar.
            node.id = value
            continue
        if local == "class":   # read for the style rules and never written: not a text the style check has to pass
            node.classes = _classes(_validate("class", value))
            continue
        if local in SILENT_ATTRS or local.startswith(("data-", "aria-")):
            continue
        if not (local == "style" or local in PROPS or local in GEOMETRY or (is_root and local in ROOT_ONLY)
                or (local == "clipPathUnits" and node.tag == "clipPath") or (node.tag == "style" and local in ("type", "media", "title"))):
            dropped.append(local)
            continue
        # What is left out above is not read, as a piece of a style either: it is never written, so it can fetch and run
        # nothing, and a label may well say `JavaScript: the logo`. What is kept, or read to decide something, is.
        _css.check_text(value)
        if local == "style":
            node.style_decls = _css.parse_declarations(value)
        elif local in PROPS:
            node.props[local] = _validate(local, value)
        elif is_root and local == "transform" and value.strip():
            raise Refusal(
                "root-transform",
                "The outer <svg> element has a transform (%r). The cleaned file would lose it and the drawing would "
                "shift or change size: ask the tool for the SVG without a transform on the outer svg element."
                % value.strip()[:40],
            )
        elif local == "clipPathUnits" and node.tag == "clipPath" and value.strip(_BLANKS) == "objectBoundingBox":   # (anywhere else it means nothing, and was left out above)
            raise Refusal(
                "clip-units",
                "A clip path in the file is measured by the box of the shape it clips (clipPathUnits=\"objectBoundingBox\"). "
                "Programs work that box out in different ways, so the mark would not be cut the same everywhere. Ask the tool "
                "for the clip in the drawing's own units (clipPathUnits=\"userSpaceOnUse\"), or for the SVG with the clips "
                "applied to the shapes.",
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
        elif node.tag == "style" and local == "title":
            # measured 2026-10-13: of two styles with a title each, a browser applies the first alone (it takes them
            # for a choice of style sheets), and the site's renderer applies both
            raise Refusal(
                "style-title",
                "A style in the file has a title (title=%r). A browser takes a style with a title for one of several to "
                "choose between and may leave it out, and other programs apply it all the same. Ask the tool for a "
                "plainer export." % value.strip()[:40],
            )
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
    """One declaration of a style (the value with the blanks still round it): the value as the
    cleaned file writes it, or None for a declaration that is left out."""
    if prop in PROPS:
        return _validate(prop, value)
    if prop in PROPS_DROP:
        _note(notes, "left out a style that only matters for text or an editor (%s)" % prop)
        return None
    if prop.startswith(EDITOR_PREFIX):
        _note(notes, "left out styles that only an editor reads (their names start %s)" % EDITOR_PREFIX)
        return None
    if NO_EFFECT.get(prop) == value.strip(_BLANKS):
        return None
    if prop in REFUSED_ATTRS:
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
    None when it is not there. No unit is px; the unit `%` is a share of the page, which is no size."""
    m = _ROOT_SIZE.fullmatch(text) if text is not None else None
    return (float(m.group(1)), m.group(2) or "px", m.group(1)) if m else None


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
    if parts is not None and len(parts) == 4 and any(len(p) > MAX_VALUE for p in parts):
        raise _too_long("viewBox", "a number of more than %d characters" % MAX_VALUE)
    nums = tuple(float(p) for p in parts) if parts is not None and len(parts) == 4 else ()
    if len(nums) != 4 or nums[2] <= 0 or nums[3] <= 0:
        raise Refusal("bad-view-box", "The viewBox is not four numbers with a width and a height above zero (%r)." % vb[:40])
    if not all(MIN_BOX <= x <= MAX_BOX for x in nums[2:]) or not all(abs(x) <= MAX_BOX for x in nums[:2]):
        raise Refusal("bad-view-box", "The viewBox (%r) is far too small or too large to be a logo." % vb[:40])
    if max(nums[2:]) / min(nums[2:]) > MAX_ASPECT:
        raise Refusal("bad-view-box", "The drawing is more than %d times wider than it is tall (or the other way round): not a logo." % MAX_ASPECT)
    # The cleaned file keeps the viewBox and leaves the width and height out. That draws the same picture only
    # where the two say the same shape (measured 2026-10-12: a 40 by 20 svg round a 10 by 20 viewBox is drawn at
    # half the size, and a width of 1in beside a height of 192px is one shape in a small icon and another in a large
    # one; 2026-10-13: so is 1em beside 32px). A size of nothing is refused whatever its unit: a browser draws
    # nothing for `0%` either.
    if (w is not None and w[0] <= 0) or (h is not None and h[0] <= 0):
        raise Refusal(
            "root-size",
            "The outer <svg> element gives the drawing a width or a height of nothing, so a program draws nothing at "
            "all. Ask the tool for the SVG with a viewBox and no width and height.",
        )
    if w is not None and h is not None and "%" not in (w[1], h[1]):
        if w[1] != h[1]:
            raise Refusal(
                "root-size",
                "The outer <svg> element gives the drawing a width and a height in two different units (%s%s by %s%s), "
                "which programs work out in different ways, so the drawing would sit differently in its icons than in "
                "the file that came. Ask the tool for the SVG with a viewBox and no width and height."
                % (w[2], w[1], h[2], h[1]),
            )
        if abs(w[0] * nums[3] / (h[0] * nums[2]) - 1) > ROOT_SLACK:
            raise Refusal(
                "root-size",
                "The outer <svg> element gives the drawing one shape with its width and height (%s%s by %s%s) and another "
                "with its viewBox (%r). The cleaned file keeps the viewBox alone, so the drawing would sit differently in "
                "its icons. Ask the tool for the SVG with a width and a height that fit its viewBox, or with a viewBox "
                "and no width and height." % (w[2], w[1], h[2], h[1], vb[:40]),
            )
    return nums, " ".join(parts)


def _plain_clips(root):
    """A clip path is a plain outline that clips shapes, and that is all a logo needs of one. What goes
    beyond it is refused by name, however it is set (an attribute, a style, a rule), because programs
    do not draw it alike. Measured 2026-10-13, the site's renderer against a browser:
    a clip-path on a <clipPath>, or on a shape inside one: two shapes inside, each clipped by a clip
      path of its own, are drawn as nothing by the one and as 4,000 of 10,000 pixels by the other; two
      clip paths that clip each other, 900 against 3,000; and a chain of them, each holding two shapes
      clipped by the next, doubles a browser's work with every link (a cleaned file of 3,228
      characters took one 26 seconds).
    display on a <clipPath>, or on a <defs>: with `none` there the one still clips (3,000 of 10,000
      pixels) and the other does not (10,000). Every value is refused there, `inline` and `block`
      too, though both programs draw those alike: one rule, and no export was seen to need them.
      A <g display="none"> round a clip path is drawn alike by both, and stays.
    a clip-path on the outer <svg>: both measure that clip in the picture's pixels, not in the
      drawing's units, so one file is whole at 32 pixels and a fifth of itself at 512."""
    todo = [(root, False)]   # an element, and whether it stands inside a clip path
    while todo:
        node, inside = todo.pop()
        clip = node.props.get("clip-path", "none")
        if clip != "none" and node is root:
            raise Refusal(
                "root-clip-path",
                "The outer <svg> element is clipped (clip-path=%r). Programs measure such a clip in the picture's pixels, "
                "not in the drawing's own units, so the mark would be cut differently in a small icon and in a large one. "
                "Ask the tool for the SVG without a clip on the outer svg element (it can stand on a group round the "
                "shapes instead)." % clip[:40],
            )
        inside = inside or node.tag == "clipPath"
        if clip != "none" and inside:
            raise Refusal(
                "clip-in-clip",
                "A clip path in the file is clipped itself, or a shape inside it is (clip-path=%r on a <%s>). Programs "
                "draw that in different ways, and some of them very slowly. Ask the tool for the SVG with each clip path "
                "as one plain outline: with the clips applied to the shapes (flattened)." % (clip[:40], node.tag),
            )
        if "display" in node.props and node.tag in ("clipPath", "defs"):
            raise Refusal(
                "clip-display",
                "The file sets display (%r) on a <%s>. Where that says `none`, one program clips with the clip paths there "
                "all the same and another does not clip at all, so this check reads no display there, whatever it says. Ask "
                "the tool for the SVG with no display set on its clip paths and on its <defs>." % (node.props["display"], node.tag),
            )
        todo.extend((child, inside) for child in node.children)


def _references(root, ids):
    """A reference finds the same element in the cleaned file as in the file that came. The one
    reference this check keeps is a clip path's, `url(#name)`, and a program takes the FIRST element
    that carries the name, whatever it is: a <title id="c"> before the <clipPath id="c"> made the
    file that came unclipped and the cleaned file clipped (measured 2026-10-13). So the name stands
    once in the whole file as it came (`ids`: on what is left out and on the outer svg too), and on a
    clip path. Every other id is left out, unchecked: nothing in the cleaned file is named by it.

    And the clip paths do not hold more, for how often they are used, than MAX_CLIP_WORK (below)."""
    clips = set(n.id for n in _walk(root) if n.tag == "clipPath" and n.id is not None)
    used = {}   # each clip path that is used, and how many elements are clipped by it
    for n in _walk(root):
        value = n.props.get("clip-path", "none")
        if value == "none":
            continue
        name = value[len("url(#"):-1]
        if ids.get(name, 0) > 1:
            raise Refusal(
                "shared-id",
                "Two parts of the file carry the same id (%r), and a shape is clipped by whatever carries it. One program "
                "takes the first of them and another the clip path, so the drawing would not come out the same "
                "everywhere. Ask the tool for the SVG again, with each id used once." % name[:40],
            )
        if name not in clips:
            raise Refusal(
                "clip-target",
                "A shape in the file is clipped by something that is not a clip path, or is not in the file at all "
                "(clip-path=%r). Programs draw that in different ways. Ask the tool for a plainer export." % value[:40],
            )
        used[name] = used.get(name, 0) + 1
    # A browser's work grows with (the elements clipped by a clip path) times (what the clip path holds), and a
    # browser has no time limit: the cleaned file is installed as favicon.svg. Measured 2026-10-13 in Chromium at 512
    # pixels (load 10 to 13): 11.9 seconds for 4,900 shapes clipped by one path of 400 turns, a file inside every
    # other cap. So that product is counted, by the numbers the clip path's shapes hold, and capped. What the cap
    # leaves is said at the top of this file ("nor how long a drawing takes to draw"): a browser's time for many
    # shapes clipped by a small path, which this product does not see.
    work = sum(used[n.id] * _clip_numbers(n) for n in _walk(root) if n.tag == "clipPath" and n.id in used)
    if work > MAX_CLIP_WORK:
        raise Refusal(
            "clip-work",
            "The file uses its clip paths so often, and they hold so much, that drawing it is far more work for a browser "
            "than a logo is (the numbers in each clip path times the shapes clipped by it come to %s; this check takes up "
            "to %s). Ask the tool for the SVG with the clips applied to the shapes." % ("{:,}".format(work), "{:,}".format(MAX_CLIP_WORK)),
        )
    for n in _walk(root):
        if n.tag != "clipPath" or n.id not in used:
            n.id = None


def _clip_numbers(clip):
    """How many numbers the shapes inside a clip path hold: those of path data and of `points`, and one for each
    other attribute that places or sizes a shape. What a clip path costs a program to clip by, near enough."""
    count = 0
    for n in _walk(clip):
        if n.tag in DRAWING:
            for name, value in n.attrs.items():
                count += len(_path_numbers(value)) if name == "d" else len(value.split()) if name == "points" else name != "transform"
    return count


def _path_numbers(d):
    """The numbers in path data, to see how far they reach (the path itself is not worked out). An
    arc's two flags are one digit each and are no numbers: `a5 5 0 11100 0` ends 100 across."""
    out, pos, command, count = [], 0, "", 0
    while True:
        pos = _PATH_GAP.match(d, pos).end()
        if pos >= len(d):
            return out
        if d[pos] in _COMMANDS:
            command, count, pos = d[pos], 0, pos + 1
        elif command in ("A", "a") and count % 7 in (3, 4) and d[pos] in "01":
            count, pos = count + 1, pos + 1
        else:
            m = _PATH_NUMBER.match(d, pos)
            if m:
                out.append(m.group())
                count += 1
            pos = m.end() if m else pos + 1


def _amount(v, whole):
    """A length, or a share of `whole`, as a number of the drawing's own units."""
    if v.endswith("%"):
        return float(v[:-1]) * whole / 100
    return float(v[:-2] if v.endswith("px") else v)


def _whole(name, box):
    """What a share in `name` is a share of, as a program works it out: the box's width for what
    lies across, its height for what lies down, and for `r` the diagonal over the root of two."""
    if name == "r":
        return math.hypot(box[2], box[3]) / math.sqrt(2)
    return box[2] if name in ("x", "x1", "x2", "cx", "rx", "width") else box[3]


def _outline(node, box):
    """No less than the length of a shape's outline, from its numbers alone: a rectangle's four
    sides, a circle's or an ellipse's round, and each side of a line, a polyline or a polygon as its
    way across and its way down together (a polyline is counted closed). Each number is worked out
    as a program works it out BEFORE two of them are taken from each other: a share of the box's
    width for x and of its height for y. (Until 2026-10-13 every share was taken of the larger
    side, so in a box 10 by 1 a line from y1="100%" to y2="10" counted as no length at all.)"""
    def of(name):
        v = node.attrs.get(name, "auto")
        return 0.0 if v == "auto" else _amount(v, _whole(name, box))

    if node.tag == "rect":
        return 2 * (abs(of("width")) + abs(of("height")))
    if node.tag == "circle":
        return 2 * math.pi * abs(of("r"))
    if node.tag == "ellipse":
        return 2 * math.pi * max(abs(of("rx")), abs(of("ry")))
    if node.tag == "line":
        return abs(of("x2") - of("x1")) + abs(of("y2") - of("y1"))
    numbers = [float(n) for n in node.attrs.get("points", "").split()]
    xs, ys = numbers[0::2], numbers[1::2]
    return sum(abs(xs[i] - xs[i - 1]) + abs(ys[i] - ys[i - 1]) for i in range(len(xs)))


def _reach(root, box):
    """How far a drawing reaches, as far as its numbers say, and how many dashes its outlines are
    cut into (see "how far, and how many dashes" at the top of this file). Both are about the
    renderer's time as much as about the picture. Measured 2026-10-13, in a box of 10 and with
    dashes of 0.01: a path of 3,652 characters that went a hundred boxes out and back 500 times
    took the site's renderer 33 seconds of processor time for one icon, and one of 25,152
    characters that crossed its own box 10,000 times took 10. Both are refused now.

    What the budget bounds is the NUMBER of dashes, and that is all it bounds. It does not bound
    how long a drawing takes: the renderer's time also grows with how wide and how round each dash
    is (inside every cap, a dashed polygon with an outline 10 wide and round joins was stopped
    after 60 seconds), and a drawing with no dash in it can be slow as well. How long a drawing
    takes is bounded for every drawing, dashed or not, by the time limit of the renderer's call
    (_render.RENDER_SECONDS), and a file that passes it is refused there: see "nor how long a
    drawing takes to draw" at the top of this file."""
    side = max(box[2], box[3])
    far = MAX_FAR * side + max(abs(box[0]), abs(box[1]), abs(box[0] + box[2]), abs(box[1] + box[3]))

    def held(name, value, numbers):
        for n in numbers:
            if not abs(n) <= far:
                raise Refusal(
                    "too-far",
                    "The file places or sizes something far outside the drawing's own box (%s holds %s, and the box is "
                    "%s by %s). Programs draw such a shape in different ways, and slowly. Ask the tool for the drawing "
                    "with nothing outside its frame. Or the drawing is made far larger or far smaller than its box and "
                    "scaled to fit: then ask for it in the box's own units, with the scaling applied to the shapes."
                    % (name, ("the number %g" % n) if len(numbers) > 1 else repr(value[:40]), "%g" % box[2], "%g" % box[3]),
                )

    pieces = 0.0
    todo = [(root, None, False)]   # an element, and what it is handed down: a dash list, and whether an outline is painted
    while todo:
        node, dashes, stroked = todo.pop()
        for name, value in sorted(node.attrs.items()) if node is not root else ():
            if name == "d":
                held(name, value, [float(n) for n in _path_numbers(value)])
            elif name == "points":
                held(name, value, [float(n) for n in value.split()])
            elif name == "transform":
                for m in _FUNCTION.finditer(value):
                    held(name, value, [float(n) for n in m.group(2).split()][1 if m.group(1) in _ANGLE_FIRST else 0:])
            elif name != "clipPathUnits" and value != "auto":
                held(name, value, [_amount(value, side)])   # a share of the larger side: never less than what it is a share of
        for name in ("stroke-width", "stroke-dashoffset"):
            if name in node.props:
                held(name, node.props[name], [_amount(node.props[name], side)])
        if "stroke-dasharray" in node.props:
            value = node.props["stroke-dasharray"]
            dashes = [] if value == "none" else [float(n) for n in value.split()]
            if any(0 < n < MIN_DASH * side for n in dashes):
                raise Refusal(
                    "dash-too-small",
                    "The file draws an outline with dashes far too small to see (stroke-dasharray=%r, in a drawing %s "
                    "across). Ask the tool for a plain outline, or to turn the dashed outline into shapes."
                    % (value[:40], "%g" % side),
                )
            if not any(dashes):
                dashes = None   # `none`, or nothing but zeros: a plain outline
        if "stroke" in node.props:
            stroked = node.props["stroke"] != "none"
        if dashes and stroked and node.tag in DRAWING:
            if node.tag == "path":
                raise Refusal(
                    "dashed-path",
                    "The file draws a shape (<path>) with a dashed outline, and this check cannot tell from the file how "
                    "long that outline is, and so how many dashes it is cut into. Ask the tool to turn the dashed outline "
                    "into shapes.",
                )
            pieces += _outline(node, box) * len(dashes) / sum(dashes)
            if pieces > MAX_DASH_PIECES:
                raise Refusal(
                    "too-many-dashes",
                    "The dashed outlines in the file are cut into more than %s dashes, far more than a logo needs and "
                    "more than can be drawn in good time. Ask the tool for plain outlines, or to turn the dashed "
                    "outlines into shapes." % "{:,}".format(MAX_DASH_PIECES),
                )
        todo.extend((child, dashes, stroked) for child in node.children)


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


def _finish(root, notes, ids, current=None):
    box, written = _box(root)
    _cascade(root, notes)
    _plain_clips(root)
    _references(root, ids)
    colours = _paint.resolve_paints(root, DRAWING, current)
    _reach(root, box)
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
    if the caller says. Where `data` is a file of a package (a Member), a refusal names the file."""
    try:
        if source != "svg":
            raise Refusal("web-page", WEB_PAGE)
        if len(data) > MAX_BYTES:
            raise Refusal("too-large", "The file is larger than %d KB, far more than a logo needs." % (MAX_BYTES // 1024))
        root, notes, ids = _parse(data)
        return _finish(root, notes, ids, current)
    except Refusal as r:
        if not isinstance(data, Member):
            raise
        raise in_package(data.name, r) from None
