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

MAX_BYTES = 512 * 1024
MAX_DEPTH = 32
MAX_ELEMENTS = 5000
MAX_ATTRIBUTES = 64
MAX_STYLE_CHARS = 64 * 1024   # all the <style> text of one file together
MAX_SELECTORS = 200           # counted with the class and id names in them: each is one look at every element
MAX_DECLARATIONS = 1000
MAX_NOTES = 40
MAX_ASPECT = 20
MIN_BOX, MAX_BOX = 1e-3, 1e6   # a viewBox outside this is no logo, and would make the renderer misjudge its density

# --- elements --------------------------------------------------------------------------

DRAWING = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}
CONTAINERS = {"svg", "g", "defs", "clipPath"}
ALLOWED_ELEMENTS = DRAWING | CONTAINERS | {"style"}
# Left out without a word: they carry no picture.
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

# ASCII digits only, and no part of a number can be read two ways: every pattern built from it
# gives its answer in one pass, however long the value. A point is followed by a digit: the
# site's renderer reads `5.` as a number in path data only (measured 2026-10-12: a width of `5.`
# draws nothing, a stroke-width of `0.` draws one unit wide), and `d` is not read with this.
_NUM = r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
_NUMBER = re.compile(_NUM)
_LEN = re.compile(r"^%s(?:px|pt|pc|mm|cm|in|em|ex|%%)?$" % _NUM)
_BLANKS = " \t\r\n"  # what XML and CSS call white space; Python's strip(), split() and \s also take a no-break space
_LIST_ITEM = re.compile(r"[ \t\r\n,]+|%s" % _NUM)
_DASH_ITEM = re.compile(r"[ \t\r\n,]+|%s%%?" % _NUM)  # each dash may be a percentage of its own
_NOT_NEGATIVE = {"stroke-width", "r", "rx", "ry", "width", "height"}
_ID = re.compile(r"^[A-Za-z_][\w\-.:]{0,99}$")
_PX = {"": 1.0, "px": 1.0, "pt": 96 / 72, "pc": 16.0, "mm": 96 / 25.4, "cm": 96 / 2.54, "in": 96.0}

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
    "transform", "pathLength",
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
}
for _n in ("systemLanguage", "requiredExtensions", "requiredFeatures"):
    REFUSED_ATTRS[_n] = ("conditional", "A part of the drawing is shown only under a condition (%s), so one program draws it and another "
                                        "leaves it out. Ask the tool for a plain SVG without it." % _n)

_KEYWORDS = {
    "fill-rule": {"nonzero", "evenodd"},
    "clip-rule": {"nonzero", "evenodd"},
    "stroke-linecap": {"butt", "round", "square"},
    "stroke-linejoin": {"miter", "round", "bevel", "arcs", "miter-clip"},
    "visibility": {"visible", "hidden", "collapse"},
    "display": {"inline", "block", "none", "inherit"},
    "shape-rendering": {"auto", "optimizeSpeed", "crispEdges", "geometricPrecision"},
    "clipPathUnits": {"userSpaceOnUse", "objectBoundingBox"},
}
_PAINT_ORDER = {"fill", "stroke", "markers"}
_TRANSFORM = re.compile(r"^\s*(?:(?:matrix|translate|scale|rotate|skewX|skewY)\s*\([0-9eE+\-.,\s]*\)\s*(?:,\s*)?)*$", re.ASCII)
_TRANSFORM_ARGS = re.compile(r"\(([^)]*)\)")
_PATH_DATA = re.compile(r"^[MmZzLlHhVvCcSsQqTtAa0-9eE+\-.,\s]*$", re.ASCII)
_CLIP = re.compile(r"^(?:none|url\([ \t\r\n]*#[\w\-.:]+[ \t\r\n]*\))$")
# ASCII only: a renderer reads no other script's digits or letters in a colour, and no other kind of space
_PAINT_CHARS = re.compile(r"""^[#A-Za-z0-9_ \t\r\n().,%+\-/'"]{1,200}$""")
_BARE_POINT = re.compile(r"\.(?![0-9])")  # in a colour too, a point is followed by a digit: rgb(255.,0,0) is drawn black


def _bad(name, value):
    return Refusal("bad-value", "The file has a value this check cannot read (%s=%r). Ask the tool for a plainer export." % (name, str(value)[:40]))


def _number_list(text, item=_LIST_ITEM):
    """Numbers with spaces or commas between them (or nothing: `10-20` is two), read left to right."""
    pos = 0
    while pos < len(text):
        m = item.match(text, pos)
        if not m:
            return False
        pos = m.end()
    return True


def _validate(name, value):
    """Syntax-level check of one kept attribute or property value (colours are read later)."""
    v = value.strip(_BLANKS)
    if name == "d":
        ok = len(v) <= 200_000 and _PATH_DATA.match(v)
    elif name == "points":
        ok = _number_list(v)
    elif name in ("x", "y", "cx", "cy", "r", "rx", "ry", "x1", "y1", "x2", "y2", "width", "height",
                  "stroke-width", "stroke-miterlimit", "stroke-dashoffset", "pathLength"):
        ok = _LEN.match(v) or (name in ("rx", "ry") and v == "auto")
        if ok and name in _NOT_NEGATIVE and v.startswith("-"):
            # a renderer may fall back to its default (a stroke one unit wide) and paint what no check listed
            raise Refusal(
                "negative-size",
                "The file gives a shape a size below zero (%s=%r), which programs draw in different ways. Ask the "
                "tool for a plainer export." % (name, v[:40]),
            )
    elif name == "stroke-dasharray":
        ok = v == "none" or _number_list(v, _DASH_ITEM)
    elif name == "transform":
        ok = _TRANSFORM.match(v) and all(_number_list(args) for args in _TRANSFORM_ARGS.findall(v))
    elif name == "preserveAspectRatio":
        ok = re.match(r"^[A-Za-z\s]{0,40}$", v)
    elif name in ("opacity", "fill-opacity", "stroke-opacity"):
        ok = re.match(r"^%s%%?$" % _NUM, v)
    elif name in _KEYWORDS:
        ok = v in _KEYWORDS[name]
    elif name == "paint-order":
        parts = [p for p in re.split("[%s]+" % _BLANKS, v) if p]
        ok = v == "normal" or (parts and len(set(parts)) == len(parts) and set(parts) <= _PAINT_ORDER)
    elif name == "clip-path":
        ok = _CLIP.match(v)
    elif name in ("fill", "stroke", "color"):
        ok = _PAINT_CHARS.match(v) and not _BARE_POINT.search(v)
    elif name == "id":
        v = value  # as it is written: a renderer takes no blank off an id, so ` a` is not the `a` a rule names
        ok = _ID.fullmatch(v)
    elif name == "class":
        ok = re.match(r"^[\w\-. ]{0,200}$", v)
    else:
        ok = True
    if not ok:
        raise _bad(name, value)
    return v


def length_px(text):
    """An absolute length ('40', '4cm', '12pt') in CSS pixels, or None (a percentage, em, ex, junk)."""
    m = re.match(r"^(%s)(px|pt|pc|mm|cm|in)?$" % _NUM, (text or "").strip())
    if not m:
        return None
    n = float(m.group(1)) * _PX[m.group(2) or ""]
    return n if math.isfinite(n) else None


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
    state = {"depth": 0, "count": 0, "skip": 0, "root": None, "stack": [], "style": 0, "ns": ""}

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
        if state["skip"]:
            state["skip"] += 1
            return
        if len(attrs) > MAX_ATTRIBUTES:
            raise Refusal("too-many-attributes", "An element in the file has more than %d attributes, far more than a logo needs." % MAX_ATTRIBUTES)
        uri, local = _split(name)
        stack = state["stack"]
        if not stack:
            if local != "svg" or uri not in (SVG_NS, ""):
                raise Refusal("not-svg", "This is not an SVG drawing: the first element is <%s>, not <svg> in the SVG namespace." % local[:20])
            state["ns"] = uri
        else:
            if uri == XHTML_NS:
                raise Refusal("foreign-html", "The file has a web-page element (<%s>) inside the drawing. Ask the tool for a plain SVG." % local[:20])
            # no namespace counts only where the root has none either (pasted code): under an
            # SVG root, xmlns="" takes an element out of the drawing, and a renderer skips it
            if uri not in (SVG_NS, state["ns"]):
                _note(notes, "left out an element from another program (<%s>)" % local[:30])
                state["skip"] = 1
                return
            if local in REFUSED_ELEMENTS:
                code, msg = REFUSED_ELEMENTS[local]
                raise Refusal(code, msg)
        if local in SILENT_ELEMENTS:
            state["skip"] = 1
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
            node.attrs[local] = _validate(local, value)
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

def _box(root):
    vb = root.attrs.get("viewBox")
    if vb is not None:
        parts = [p for p in re.split(r"[ \t\r\n,]+", vb) if p]
        # plain numbers only: float() alone would also take 1_0, Arabic-Indic digits, "inf"
        nums = tuple(float(p) for p in parts) if all(_NUMBER.fullmatch(p) for p in parts) else ()
        if len(nums) != 4 or not all(math.isfinite(x) for x in nums) or nums[2] <= 0 or nums[3] <= 0:
            raise Refusal("bad-view-box", "The viewBox is not four numbers with a width and a height above zero (%r)." % vb[:40])
        if not all(MIN_BOX <= x <= MAX_BOX for x in nums[2:]) or not all(abs(x) <= MAX_BOX for x in nums[:2]):
            raise Refusal("bad-view-box", "The viewBox (%r) is far too small or too large to be a logo." % vb[:40])
        if max(nums[2:]) / min(nums[2:]) > MAX_ASPECT:
            raise Refusal("bad-view-box", "The drawing is more than %d times wider than it is tall (or the other way round): not a logo." % MAX_ASPECT)
        return nums
    w, h = length_px(root.attrs.get("width")), length_px(root.attrs.get("height"))
    if w is None or h is None or w <= 0 or h <= 0:
        raise Refusal(
            "no-size",
            "The drawing has no viewBox and no width and height in plain units (a percentage is no size), so it "
            "cannot be fitted into a square icon. Ask the tool for the SVG with a viewBox.",
        )
    if not (MIN_BOX <= w <= MAX_BOX and MIN_BOX <= h <= MAX_BOX):
        raise Refusal("bad-view-box", "The width and height are far too small or too large to be a logo.")
    if max(w, h) / min(w, h) > MAX_ASPECT:
        raise Refusal("bad-view-box", "The drawing is more than %d times wider than it is tall (or the other way round): not a logo." % MAX_ASPECT)
    return (0.0, 0.0, w, h)


def _fmt(n):
    return repr(round(n, 6)).rstrip("0").rstrip(".") if n != int(n) else str(int(n))


def _emit(node, out, view_box=None):
    attrs = []
    if node.tag == "svg":
        attrs.append(("xmlns", SVG_NS))
        attrs.append(("viewBox", " ".join(_fmt(x) for x in view_box)))
        if "preserveAspectRatio" in node.attrs:
            attrs.append(("preserveAspectRatio", node.attrs["preserveAspectRatio"]))
    else:
        if node.id:
            attrs.append(("id", node.id))
        attrs.extend((k, v) for k, v in sorted(node.attrs.items()))
    attrs.extend((k, v) for k, v in sorted(node.props.items()))
    out.append("<" + node.tag + "".join(" %s=%s" % (k, quoteattr(v)) for k, v in attrs))
    kids = [c for c in node.children if c.tag != "style"]
    if not kids:
        out.append("/>")
        return
    out.append(">")
    for c in kids:
        _emit(c, out)
    out.append("</" + node.tag + ">")


def _finish(root, notes, current=None):
    box = _box(root)
    _cascade(root, notes)
    colours = _paint.resolve_paints(root, DRAWING, current)
    out = []
    _emit(root, out, box)
    return Clean("".join(out), box, notes, root, colours)


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
