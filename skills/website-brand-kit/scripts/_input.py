"""_input.py: what the owner handed over, decided by what the bytes ARE (never by the file name).

Four forms are read: an SVG file or pasted SVG code, an HTML page with an inline <svg>, and a
zip of SVG files. A PNG, JPG or PDF is refused in this version, with the two ways out. Nothing
is written here, and only the one file the owner picked is ever handed on to be checked.
Standard library only.
"""

from __future__ import annotations

import re

import _svg
import _zipin
from _refusal import Ask, Refusal

_RASTER = (
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"\xff\xd8\xff", "JPG"),
    (b"%PDF", "PDF"),
    (b"GIF87a", "GIF"),
    (b"GIF89a", "GIF"),
    (b"II*\x00", "TIFF"),
    (b"MM\x00*", "TIFF"),
)

RASTER_MESSAGE = (
    "This looks like a %s file. This version of the logo step reads only an SVG: it cannot use a PNG, JPG or PDF. "
    "You have two ways forward: ask whoever made the logo for an SVG of it, or have the assistant make you a new logo "
    "(it writes the question to put to a design tool, then checks what comes back)."
)


class Source(object):
    def __init__(self, kind, data, package=None):
        self.kind = kind      # "svg", "html" or "zip"
        self.data = data
        self.package = package


class Mark(object):
    def __init__(self, colour, mono, source, name):
        self.colour = colour  # the bytes of the mark that will be checked
        self.mono = mono      # the one-colour twin the owner named, or None
        self.source = source  # "svg" or "html" (an inline svg: the stricter rules for a page)
        self.name = name


_BLANK = re.compile(r"[\s\ufeff]*")
_FIRST = re.compile(r"<(?:!doctype\s+)?(?:[a-z_][\w.\-]*:)?([a-z_][\w.\-]*)")
_BMP_INFO_SIZES = (12, 40, 52, 56, 64, 108, 124)


def _is_bmp(data):
    # "BM" alone also starts ordinary text: a BMP goes on with its size, four zero bytes, where
    # the pixels start, and the size of its info header (one of a few known sizes)
    return data.startswith(b"BM") and data[6:10] == b"\0\0\0\0" and int.from_bytes(data[14:18], "little") in _BMP_INFO_SIZES


def _first_element(text):
    """Where the first element (or DOCTYPE) starts: past the XML declaration and any comments
    before it, however long they are."""
    pos = 0
    while True:
        pos = _BLANK.match(text, pos).end()
        if text.startswith("<!--", pos):
            end, closer = text.find("-->", pos + 4), 3
        elif text[pos:pos + 5].lower() == "<?xml":
            end, closer = text.find("?>", pos + 5), 2
        else:
            return pos
        if end < 0:  # never closed
            return pos
        pos = end + closer


def _kind(data):
    for magic, label in _RASTER:
        if data.startswith(magic):
            raise Refusal("raster-logo", RASTER_MESSAGE % label)
    if _is_bmp(data):
        raise Refusal("raster-logo", RASTER_MESSAGE % "BMP")
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        raise Refusal("raster-logo", RASTER_MESSAGE % "WebP")
    if data.startswith((b"PK\x03\x04", b"PK\x05\x06")):
        return "zip"
    text = _svg.page_text(data)
    start = _first_element(text)
    low = text[start:start + 16384].lower()
    first = _FIRST.match(low)
    name = first.group(1) if first else ""  # the root's own name, whatever prefix it carries
    if name in ("html", "head", "body"):
        return "html"
    if name == "svg":
        return "svg"
    if "<svg" in low:
        return "html"  # a piece of a page, not a whole one
    return None


def load(data):
    """Say what the bytes are. Raises Refusal for a picture or anything it does not read."""
    kind = _kind(data)
    if kind is None:
        raise Refusal(
            "unknown-file",
            "This is not a file this check reads. Give it an SVG file, SVG code pasted as text, a web page that holds "
            "the logo as an inline <svg>, or a zip of SVG files.",
        )
    return Source(kind, data, _zipin.open_zip(data) if kind == "zip" else None)


def _which_svg(found, pick):
    if pick is None:
        if len(found) > 1:
            # shown to the owner: no character that could move the cursor or turn the line round
            options = ["%d: %s" % (i + 1, "".join(c if c.isprintable() else "?" for c in re.sub(r"\s+", " ", s)[:70]))
                       for i, s in enumerate(found)]
            raise Ask("which-svg", "The page holds %d inline SVG drawings: which one is the mark?" % len(found), options)
        return 0
    try:
        i = int(str(pick).split(":")[0]) - 1
    except ValueError:
        i = -1
    if not 0 <= i < len(found):
        raise Refusal("no-such-file", "There is no inline SVG number %r on the page (it holds %d)." % (str(pick)[:20], len(found)))
    return i


def mark(source, pick=None, mono=None):
    """The file to check, as the owner picked it. Raises Ask when the owner must choose first."""
    if mono and source.kind != "zip":
        raise Refusal(
            "mono-needs-zip",
            "A one-colour version was named (%r), but this is %s, which holds no second file. Leave it out, or "
            "put both SVG files into one zip." % (str(mono)[:40], "one SVG file" if source.kind == "svg" else "a web page"),
        )
    if source.kind == "svg":
        if pick is not None:
            raise Refusal(
                "nothing-to-pick",
                "A pick was given (%r), but this is one SVG file, so there is nothing to pick from. Leave the pick "
                "out." % str(pick)[:40],
            )
        return Mark(source.data, None, "svg", "the SVG")
    if source.kind == "html":
        found = _svg.html_svgs(source.data)
        if not found:
            raise Refusal(
                "no-svg",
                "The page holds no inline <svg>. If the mark is drawn with CSS or an <img>, ask whoever made it for the "
                "SVG file.",
            )
        i = _which_svg(found, pick)
        return Mark(found[i].encode("utf-8"), None, "html", "inline SVG %d" % (i + 1))
    pkg = source.package
    names = pkg.svg_names
    if not names:
        raise Refusal(
            "zip-no-svg",
            "There is no SVG file in the package. This version reads only an SVG: ask whoever made the logo for one, "
            "or ask the assistant for a new logo.",
        )
    if pick is None:
        if len(names) > 1:
            raise Ask(
                "which-file",
                "The package holds %d SVG files. Which one is the mark? (Say too, if you like, which one is its "
                "one-colour version.)" % len(names),
                names,
            )
        pick = names[0]
    return Mark(pkg.read_svg(pick), pkg.read_svg(mono) if mono else None, "svg", pick)
