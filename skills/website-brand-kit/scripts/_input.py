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
    (b"BM", "BMP"),
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


def _text_head(data):
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data[:16384].decode("utf-16", "replace")
    return data[:16384].lstrip(b"\xef\xbb\xbf").decode("utf-8", "replace")


def _kind(data):
    for magic, label in _RASTER:
        if data.startswith(magic):
            raise Refusal("raster-logo", RASTER_MESSAGE % label)
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        raise Refusal("raster-logo", RASTER_MESSAGE % "WebP")
    if data.startswith((b"PK\x03\x04", b"PK\x05\x06")):
        return "zip"
    low = _text_head(data).lstrip().lower()
    if low.startswith(("<!doctype html", "<html", "<head", "<body")):
        return "html"
    if low.startswith(("<?xml", "<svg", "<!doctype svg", "<!--")) and "<svg" in low[:8192]:
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
            options = ["%d: %s" % (i + 1, re.sub(r"\s+", " ", s)[:70]) for i, s in enumerate(found)]
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
    if source.kind == "svg":
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
