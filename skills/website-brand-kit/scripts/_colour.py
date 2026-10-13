"""_colour.py: read a colour as one six-digit hex, and compare two.

One helper for everything that meets a colour (the pasted palette, the stylesheet, the paint
values of a mark), so that the same colour is always the same hex. It reads #rgb, #rgba, #rrggbb,
#rrggbbaa, rgb()/rgba(), hsl()/hsla(), oklch(), the 148 CSS colour names and currentColor (when the
caller says what that is). It refuses, by name, what it cannot resolve: alpha, a gradient or
pattern, a colour outside the screen's range, and any other format.

It reads fewer spellings than a browser does, on purpose. A mark's paint is drawn twice: by a
browser, and by the site's renderer (sharp), which makes the icons from the file. Where the two
draw a spelling differently, or where it is not known that they agree, the spelling is refused for
EVERY caller, so that one colour has one hex whoever asks:
  - rgb() with percentages and plain numbers mixed. The renderer draws the comma form
    (`rgb(50%, 0, 0)`) black and the space form as a browser does; every mixed form is refused.
  - a number with no digit after its point (`255.`): the renderer does not take it for a number and
    draws black.
  - a number with more than two digits in its exponent (`255e000`, `0e309`). This is the SVG check's
    rule for a number (_svg._NUM), kept the same here so that the tool has one grammar for a number;
    inside a colour the renderer does read such a number.
  - a number of more than 64 characters (`rgb(` and four hundred digits): the SVG check's limit for
    one number (_svg.MAX_VALUE), for the same reason. No colour needs one, and arithmetic with it
    has no result a screen can show.
  - a hue of more than a thousand turns either way (`hsl(1e9 100% 50%)`): the renderer works with
    less exact numbers and draws another colour for it, and black beyond what it can hold.
  - hsl() or hsla() whose saturation or lightness has no % sign: the renderer draws black.
  - hsl() or hsla() with a saturation or a lightness over 100%. The renderer cuts each down to 100%
    (it draws `hsl(200 300% 20%)` as #004466). Chromium 153 does that in the comma form only: in a
    stylesheet it shows `hsl(200 300% 20%)` as #0066cc and `hsl(270deg 150% 33.333%)` as #5500d4
    (cut: #5500aa), and `hsl(0 100% 1e99%)` as #00ffff where the renderer draws white. So such a
    colour has no one hex. (Below 0% both take 0%, and it is read.)
  - an alpha written after a slash in the comma form (`rgb(255,0,0/1)`): the renderer draws black. An
    alpha of exactly 1 (or 100%) is read in the two forms the renderer draws as the solid colour: as
    a fourth value after commas, and after a slash in the space form.
One rule is for one caller only: with `drawn=True` (the paint of a mark, _paint.py) oklch() is
refused, because the renderer does not read it and draws black, so the file as it came would not
show the colour this check lists. A palette table and a stylesheet are never drawn by that
renderer (a browser reads the stylesheet, and the table is only turned into hex), so there oklch()
is read as CSS has it. tests/test_paint.py holds a picture of each of these, drawn by the renderer.
A blank around a colour, or between its numbers, is one CSS takes for white space: a space, a tab, a
line feed, a carriage return or a form feed (SPACE). Python's own strip() and split() also take a
no-break space, a wide space, a line separator and a few control characters, which no browser reads
past: `--bg:` with a no-break space pasted before `#ffffff` is no colour to a browser, and none here.
Standard library only.
"""

from __future__ import annotations

import math
import re
from decimal import ROUND_DOWN, Decimal

from _refusal import Refusal

# The 148 CSS colour names (CSS Color 4), "name:rrggbb". Checked against a second source in
# tests/test_colour.py whenever Pillow is installed.
_NAMES_TEXT = """
    aliceblue:f0f8ff antiquewhite:faebd7 aqua:00ffff aquamarine:7fffd4 azure:f0ffff
    beige:f5f5dc bisque:ffe4c4 black:000000 blanchedalmond:ffebcd blue:0000ff blueviolet:8a2be2
    brown:a52a2a burlywood:deb887 cadetblue:5f9ea0 chartreuse:7fff00 chocolate:d2691e
    coral:ff7f50 cornflowerblue:6495ed cornsilk:fff8dc crimson:dc143c cyan:00ffff
    darkblue:00008b darkcyan:008b8b darkgoldenrod:b8860b darkgray:a9a9a9 darkgreen:006400
    darkgrey:a9a9a9 darkkhaki:bdb76b darkmagenta:8b008b darkolivegreen:556b2f darkorange:ff8c00
    darkorchid:9932cc darkred:8b0000 darksalmon:e9967a darkseagreen:8fbc8f darkslateblue:483d8b
    darkslategray:2f4f4f darkslategrey:2f4f4f darkturquoise:00ced1 darkviolet:9400d3
    deeppink:ff1493 deepskyblue:00bfff dimgray:696969 dimgrey:696969 dodgerblue:1e90ff
    firebrick:b22222 floralwhite:fffaf0 forestgreen:228b22 fuchsia:ff00ff gainsboro:dcdcdc
    ghostwhite:f8f8ff gold:ffd700 goldenrod:daa520 gray:808080 green:008000 greenyellow:adff2f
    grey:808080 honeydew:f0fff0 hotpink:ff69b4 indianred:cd5c5c indigo:4b0082 ivory:fffff0
    khaki:f0e68c lavender:e6e6fa lavenderblush:fff0f5 lawngreen:7cfc00 lemonchiffon:fffacd
    lightblue:add8e6 lightcoral:f08080 lightcyan:e0ffff lightgoldenrodyellow:fafad2
    lightgray:d3d3d3 lightgreen:90ee90 lightgrey:d3d3d3 lightpink:ffb6c1 lightsalmon:ffa07a
    lightseagreen:20b2aa lightskyblue:87cefa lightslategray:778899 lightslategrey:778899
    lightsteelblue:b0c4de lightyellow:ffffe0 lime:00ff00 limegreen:32cd32 linen:faf0e6
    magenta:ff00ff maroon:800000 mediumaquamarine:66cdaa mediumblue:0000cd mediumorchid:ba55d3
    mediumpurple:9370db mediumseagreen:3cb371 mediumslateblue:7b68ee mediumspringgreen:00fa9a
    mediumturquoise:48d1cc mediumvioletred:c71585 midnightblue:191970 mintcream:f5fffa
    mistyrose:ffe4e1 moccasin:ffe4b5 navajowhite:ffdead navy:000080 oldlace:fdf5e6 olive:808000
    olivedrab:6b8e23 orange:ffa500 orangered:ff4500 orchid:da70d6 palegoldenrod:eee8aa
    palegreen:98fb98 paleturquoise:afeeee palevioletred:db7093 papayawhip:ffefd5
    peachpuff:ffdab9 peru:cd853f pink:ffc0cb plum:dda0dd powderblue:b0e0e6 purple:800080
    rebeccapurple:663399 red:ff0000 rosybrown:bc8f8f royalblue:4169e1 saddlebrown:8b4513
    salmon:fa8072 sandybrown:f4a460 seagreen:2e8b57 seashell:fff5ee sienna:a0522d silver:c0c0c0
    skyblue:87ceeb slateblue:6a5acd slategray:708090 slategrey:708090 snow:fffafa
    springgreen:00ff7f steelblue:4682b4 tan:d2b48c teal:008080 thistle:d8bfd8 tomato:ff6347
    turquoise:40e0d0 violet:ee82ee wheat:f5deb3 white:ffffff whitesmoke:f5f5f5 yellow:ffff00
    yellowgreen:9acd32
"""
NAMES = dict(w.split(":") for w in _NAMES_TEXT.split())

# ASCII digits only (\d would take any script's digits), a digit after the point, and one or two digits in
# an exponent (the top of this file says why). The same number as _svg._NUM and _paint._NUM, and the same
# limit on its length as _svg.MAX_VALUE: tests/test_colour.py holds the two files to each other.
_NUM = r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,2})?"
MAX_NUMBER_CHARS = 64
_VALUE = re.compile(r"^(%s)(%%|deg|grad|rad|turn)?$" % _NUM)
_HEX = re.compile(r"^#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_FUNC = re.compile(r"^([a-zA-Z]+)\((.*)\)$", re.S)
_GAMUT_EPS = 0.0005
SPACE = " \t\r\n\f"  # what CSS takes for white space, and all that is taken off a colour or stands between its numbers
_SPACES = re.compile("[%s]+" % SPACE)
# How an unreadable colour is told to be written: in a palette or a stylesheet, and as the paint of a mark (`drawn`),
# where oklch() is refused.
_WRITE = "Write it as #rrggbb, rgb(), hsl(), oklch() or a CSS colour name."
_WRITE_DRAWN = "Write it as #rrggbb, rgb(), hsl() or a CSS colour name."


def _unreadable(text, why="a colour format this check does not read"):
    return Refusal("colour-unreadable", "The colour %r is not one this check can read (%s). %s" % (text.strip(SPACE)[:40], why, _WRITE))


def _alpha(text):
    return Refusal(
        "colour-alpha",
        "The colour %r is see-through. This check reads flat, solid colours only: ask for the same colour without "
        "transparency." % text.strip(SPACE)[:40],
    )


def _half_up(x):
    return int(math.floor(x + 0.5))


def _byte(x):
    return max(0, min(255, _half_up(x)))


def _hex(r, g, b):
    return "#%02x%02x%02x" % (_byte(r), _byte(g), _byte(b))


def _num(token, text, allow=("", "%")):
    """One number with an optional unit, as (value, unit)."""
    m = _VALUE.match(token.strip(SPACE))
    if not m or (m.group(2) or "") not in allow:
        raise _unreadable(text)
    if len(m.group(1)) > MAX_NUMBER_CHARS:
        raise _unreadable(text, "it holds a number of more than %d characters" % MAX_NUMBER_CHARS)
    value = float(m.group(1))
    if not math.isfinite(value):  # (cannot happen within the two limits above; kept so that no later sum meets an infinity)
        raise _unreadable(text, "it holds a number too large to work with")
    return value, m.group(2) or ""


MAX_TURNS = 1000  # a hue further round than this is not read: the renderer's less exact numbers give another colour


def _angle(token, text):
    v, unit = _num(token, text, ("", "deg", "grad", "rad", "turn"))
    degrees = v * {"": 1.0, "deg": 1.0, "grad": 0.9, "rad": 180 / math.pi, "turn": 360.0}[unit]
    if abs(degrees) > MAX_TURNS * 360:
        raise _unreadable(text, "its hue is more than a thousand turns round")
    return degrees % 360.0


def _check_alpha(token, text):
    v, unit = _num(token, text)
    if (v if unit == "" else v / 100.0) != 1.0:
        raise _alpha(text)


def _split_args(body, text, legacy_ok):
    """Channels and alpha, from `a, b, c`, `a, b, c, d` or `a b c / d`."""
    alpha = None
    if "/" in body:
        body, alpha = body.rsplit("/", 1)
        if "," in body:
            # rgb(255,0,0/1): the site's renderer draws black for it
            raise _unreadable(text, "it has commas and a slash; write the alpha after a comma, or leave it out")
    if "," in body:
        if not legacy_ok:
            raise _unreadable(text)
        parts = [p for p in body.split(",")]
        if len(parts) == 4 and alpha is None:
            alpha = parts.pop()
    else:
        parts = [p for p in _SPACES.split(body) if p]
    parts = [p.strip(SPACE) for p in parts]
    if len(parts) != 3 or not all(parts):
        raise _unreadable(text)
    if alpha is not None:
        _check_alpha(alpha, text)
    return parts


def _hsl(parts, text):
    h = _angle(parts[0], text)
    for part in parts[1:]:
        if not part.endswith("%"):
            # hsl(0, 100, 50): the site's renderer draws black for it
            raise _unreadable(text, "the saturation and the lightness of hsl() each need a % sign")
    s, _ = _num(parts[1], text, ("%",))
    l, _ = _num(parts[2], text, ("%",))
    if s > 100.0 or l > 100.0:
        # hsl(270deg 150% 33.333%): #5500aa with the saturation cut to 100% (so the renderer draws it), #5500d4 in Chromium
        raise _unreadable(text, "the saturation or the lightness of hsl() is over 100%")
    s, l = max(0.0, s) / 100.0, max(0.0, l) / 100.0
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60.0) % 2 - 1))
    m = l - c / 2
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][int(h // 60) % 6]
    return _hex((r + m) * 255, (g + m) * 255, (b + m) * 255)


def _oklch(parts, text):
    L, unit = _num(parts[0], text)
    if unit == "%":
        L /= 100.0
    C, unit = _num(parts[1], text)
    if unit == "%":
        C = C / 100.0 * 0.4
    C = max(0.0, C)  # CSS Color 4: a chroma below zero is zero (a grey), not the opposite hue
    h = math.radians(_angle(parts[2], text))
    a, b = C * math.cos(h), C * math.sin(h)
    try:
        l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
        m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
        s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
        lin = (
            +4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
            -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
            -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
        )
    except OverflowError:  # a lightness or a chroma too large to cube: far outside any screen
        lin = (math.inf,) * 3
    # (an infinity, and the not-a-number that two of them make, fail this comparison like any other colour outside)
    if not all(-_GAMUT_EPS <= c <= 1 + _GAMUT_EPS for c in lin) or not 0 <= L <= 1:
        raise Refusal(
            "colour-gamut",
            "The colour %r lies outside the colours a screen can show (sRGB), so it has no exact hex. Ask for it again "
            "as #rrggbb." % text.strip(SPACE)[:40],
        )
    enc = [12.92 * c if c <= 0.0031308 else 1.055 * max(c, 0.0) ** (1 / 2.4) - 0.055 for c in (max(0.0, min(1.0, c)) for c in lin)]
    return _hex(*(c * 255 for c in enc))


def parse_colour(text, current=None, drawn=False):
    """`text` as '#rrggbb' (lower case). `current` is what currentColor means here, if anything.
    `drawn` says the colour is a paint of a file the site's renderer draws as it came (a mark): then
    oklch(), which that renderer does not read, is refused (see the top of this file), and a refusal
    speaks of the mark; without it a refusal speaks of a colour that somebody wrote (a cell of the
    palette, a line of the stylesheet). Whatever the text is, this returns a colour or raises Refusal,
    and nothing else."""
    try:
        return _parse(text, current, drawn)
    except OverflowError:  # no number the grammar lets through gets here (tests/test_colour.py tries); if one ever does, it is refused by name
        refusal = _unreadable((text or "")[:40], "it holds a number too large to work with")
    except Refusal as e:
        if not drawn:
            raise  # as it is, at no cost: a megabyte of cells that are no colour builds one refusal each
        refusal = e
    if drawn and str(refusal).endswith(_WRITE):
        refusal = Refusal(refusal.code, str(refusal)[:-len(_WRITE)] + _WRITE_DRAWN)
    raise refusal from None


def _parse(text, current, drawn):
    t = (text or "").strip(SPACE)
    if not t:
        raise _unreadable(text or "", "it is empty")
    if t != t.strip():
        raise Refusal(
            "colour-unreadable",
            "The colour %r has a character before or after it that looks like a space and is none to a browser (a "
            "no-break space, as a line copied from a web page can have), so a browser takes the whole value for no "
            "colour. Delete the blanks around the colour and type them again." % t.strip()[:40],
        )
    if not t.isascii():
        # digits of another script would be read as numbers, and a letter such as the Kelvin sign lower-cases to a plain "k"
        raise _unreadable(t, "it holds a letter, a digit or a space that is not a plain one")
    low = t.lower()
    if low == "currentcolor":
        if current:
            return parse_colour(current, None, drawn)  # through the guarded entry, like any other text
        raise Refusal(
            "colour-current",
            "The mark paints with currentColor, which takes the colour of the page around it, so its colour cannot be "
            "known from the file. Ask for the SVG with the colour written out." if drawn else
            "The colour is written as currentColor, which is whatever colour the text around it has and no colour of its "
            "own. Write the colour itself, as #rrggbb.",
        )
    if low == "transparent":
        raise _alpha(t)
    if low.startswith("url("):
        raise Refusal(
            "colour-gradient",
            ("The mark paints with %r, a gradient or a pattern. This check reads flat colours only: ask the tool for the "
             "same mark in flat colours." if drawn else
             "The colour %r is a gradient or a pattern. This check reads one flat colour: write it as #rrggbb.") % t[:40],
        )
    m = _HEX.match(t)
    if m:
        h = m.group(1).lower()
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) == 8:
            if h[6:] != "ff":
                raise _alpha(t)
            h = h[:6]
        return "#" + h
    m = _FUNC.match(t)
    if m:
        name, body = m.group(1).lower(), m.group(2)
        if name in ("rgb", "rgba"):
            parts = _split_args(body, t, True)
            ch = []
            units = set()
            for p in parts:
                v, unit = _num(p, t)
                units.add(unit)
                ch.append(v * 255 / 100.0 if unit == "%" else v)
            if len(units) > 1:
                # the site's renderer draws rgb(50%, 0, 0) black and rgb(50% 0 0) as a browser does: no mixed
                # form is read, whichever of the two it is
                raise _unreadable(t, "it mixes percentages and plain numbers")
            return _hex(*ch)
        if name in ("hsl", "hsla"):
            return _hsl(_split_args(body, t, True), t)
        if name == "oklch":
            if drawn:
                raise Refusal(
                    "colour-unreadable",
                    "The mark paints with %r. The program that makes the site's icons does not read oklch() and would paint "
                    "black in its place, so the colour cannot be taken from the file as it is. Ask the tool for the SVG with "
                    "that colour written as #rrggbb." % t[:40],
                )
            return _oklch(_split_args(body, t, False), t)
        raise _unreadable(t)
    if low in NAMES:
        return "#" + NAMES[low]
    raise _unreadable(t, "it is not a colour name it knows")


# --- contrast --------------------------------------------------------------------------

def _channel(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def ratio(a, b):
    """WCAG contrast ratio of two hex colours, not rounded."""
    la, lb = luminance(a), luminance(b)
    hi, lo = (la, lb) if la >= lb else (lb, la)
    return (hi + 0.05) / (lo + 0.05)


def passes(a, b, need):
    return ratio(a, b) >= need


def shown(r):
    """The ratio as the owner reads it: cut, never rounded up, so a pair that fails never prints as
    the number it needed (4.4998 shows as 4.49)."""
    cut = Decimal(repr(float(r))).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    return ("%s" % cut).rstrip("0").rstrip(".")
