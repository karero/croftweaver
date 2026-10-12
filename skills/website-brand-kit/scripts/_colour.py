"""_colour.py: read any colour the way a browser would, as one six-digit hex, and compare two.

One helper for everything that meets a colour (the pasted palette, the stylesheet, the paint
values of a mark), so that the same colour is always the same hex. It reads #rgb, #rgba, #rrggbb,
#rrggbbaa, rgb()/rgba(), hsl()/hsla(), oklch(), the 148 CSS colour names and currentColor (when the
caller says what that is). It refuses, by name, what it cannot resolve: alpha, a gradient or
pattern, a colour outside the screen's range, and any other format. Standard library only.
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

_NUM = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
_VALUE = re.compile(r"^(%s)(%%|deg|grad|rad|turn)?$" % _NUM)
_HEX = re.compile(r"^#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_FUNC = re.compile(r"^([a-zA-Z]+)\((.*)\)$", re.S)
_GAMUT_EPS = 0.0005


def _unreadable(text, why="a colour format this check does not read"):
    return Refusal(
        "colour-unreadable",
        "The colour %r is not one this check can read (%s). Write it as #rrggbb, rgb(), hsl(), oklch() or a "
        "CSS colour name." % (text.strip()[:40], why),
    )


def _alpha(text):
    return Refusal(
        "colour-alpha",
        "The colour %r is see-through. This check reads flat, solid colours only: ask for the same colour without "
        "transparency." % text.strip()[:40],
    )


def _half_up(x):
    return int(math.floor(x + 0.5))


def _byte(x):
    return max(0, min(255, _half_up(x)))


def _hex(r, g, b):
    return "#%02x%02x%02x" % (_byte(r), _byte(g), _byte(b))


def _num(token, text, allow=("", "%")):
    """One number with an optional unit, as (value, unit)."""
    m = _VALUE.match(token.strip())
    if not m or (m.group(2) or "") not in allow:
        raise _unreadable(text)
    v = float(m.group(1))
    if not math.isfinite(v):
        raise _unreadable(text)
    return v, m.group(2) or ""


def _finite(x, text):
    """`x`, unless the arithmetic on a huge number overflowed: then it is no colour, and is refused."""
    if not math.isfinite(x):
        raise _unreadable(text, "a number in it is too large")
    return x


def _angle(token, text):
    v, unit = _num(token, text, ("", "deg", "grad", "rad", "turn"))
    return _finite(v * {"": 1.0, "deg": 1.0, "grad": 0.9, "rad": 180 / math.pi, "turn": 360.0}[unit], text) % 360.0


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
        if not legacy_ok:
            raise _unreadable(text)
        parts = [p for p in body.split(",")]
        if len(parts) == 4 and alpha is None:
            alpha = parts.pop()
    else:
        parts = body.split()
    parts = [p.strip() for p in parts]
    if len(parts) != 3 or not all(parts):
        raise _unreadable(text)
    if alpha is not None:
        _check_alpha(alpha, text)
    return parts


def _hsl(parts, text):
    h = _angle(parts[0], text)
    s, _ = _num(parts[1], text)
    l, _ = _num(parts[2], text)
    s, l = max(0.0, min(100.0, s)) / 100.0, max(0.0, min(100.0, l)) / 100.0
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
    except OverflowError:  # a lightness or chroma so large that the arithmetic gives up: far outside any screen
        lin = (math.inf,) * 3
    if not all(-_GAMUT_EPS <= c <= 1 + _GAMUT_EPS for c in lin) or not 0 <= L <= 1:
        raise Refusal(
            "colour-gamut",
            "The colour %r lies outside the colours a screen can show (sRGB), so it has no exact hex. Ask for it again "
            "as #rrggbb." % text.strip()[:40],
        )
    enc = [12.92 * c if c <= 0.0031308 else 1.055 * max(c, 0.0) ** (1 / 2.4) - 0.055 for c in (max(0.0, min(1.0, c)) for c in lin)]
    return _hex(*(c * 255 for c in enc))


def parse_colour(text, current=None):
    """`text` as '#rrggbb' (lower case). `current` is what currentColor means here, if anything."""
    t = (text or "").strip()
    if not t:
        raise _unreadable(text or "", "it is empty")
    low = t.lower()
    if low == "currentcolor":
        if current:
            return parse_colour(current)
        raise Refusal(
            "colour-current",
            "The mark paints with currentColor, which takes the colour of the page around it, so its colour cannot be "
            "known from the file. Ask for the SVG with the colour written out.",
        )
    if low == "transparent":
        raise _alpha(t)
    if low.startswith("url("):
        raise Refusal(
            "colour-gradient",
            "The mark paints with %r, a gradient or a pattern. This check reads flat colours only: ask the tool for the "
            "same mark in flat colours." % t[:40],
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
            for p in parts:
                v, unit = _num(p, t)
                ch.append(_finite(v * 255 / 100.0, t) if unit == "%" else v)
            return _hex(*ch)
        if name in ("hsl", "hsla"):
            return _hsl(_split_args(body, t, True), t)
        if name == "oklch":
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
