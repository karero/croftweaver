"""_input.py: what the owner handed over, decided by what the bytes ARE (never by the file name).

Three forms are read: an SVG file, SVG code pasted as text, and a zip of SVG files. A web page
is refused in this version (a drawing is not taken out of one), and so is a PNG, JPG or PDF,
each with the way out. Nothing is written here, and only the files the owner picked (the mark
and, in a package, its one-colour version) are ever handed on to be checked. Standard library only.
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
    "You have two ways forward: ask whoever made the logo for an SVG of it, or let the assistant help you get a new logo "
    "(it writes the question to put to a design tool, then checks what comes back)."
)
UNKNOWN_FILE = "This is not a file this check reads. Give it an SVG file, SVG code pasted as text, or a zip of SVG files."
MAX_BYTES = _zipin.MAX_ZIP_BYTES  # of anything handed over: nothing larger is looked at, whatever it is


class Source(object):
    def __init__(self, kind, data, package=None):
        self.kind = kind      # "svg" or "zip"
        self.data = data
        self.package = package


class Mark(object):
    def __init__(self, colour, mono, source, name):
        self.colour = colour  # the bytes of the mark that will be checked (from a package: a _svg.Member, which knows its name)
        self.mono = mono      # the one-colour twin the owner named, or None
        self.source = source  # always "svg": kept for the caller that still reads it
        self.name = name


_BLANK = re.compile(r"[\s\ufeff]*")
# The first element's whole name, as XML reads one: everything up to a blank, a slash or the end
# of the tag, whatever letters it is written in. Its prefix, if it has one, ends at the last colon.
_FIRST = re.compile(r"<(?:!doctype[ \t\r\n]+)?([^ \t\r\n/>!?][^ \t\r\n/>]*)", re.I)
# A drawing's own element somewhere in the text: the whole name `svg`, with a prefix or without, and then a blank, a
# slash, the end of the tag or the end of the text (`<svgx/>` is no drawing, `<s:svg>` is one). Searched as the text
# stands: no second copy of it in small letters.
_SVG_TAG = re.compile(r"<(?:[^ \t\r\n<>/!?:]+:)?svg(?:[ \t\r\n/>]|\Z)", re.I | re.ASCII)
# What a web page, or a piece copied out of one, starts with. Any other first element is some other
# kind of file (a feed, a stray <foo/>), and is not called a page.
_PAGE = frozenset(("html head body div span p a img section header footer main nav article aside figure picture table ul ol li "
                   "h1 h2 h3 h4 h5 h6 form button script style link meta title br hr iframe "
                   "pre label input select textarea canvas video audio object embed details summary font center").split())
_BMP_INFO_SIZES = (12, 40, 52, 56, 64, 108, 124)


def _is_bmp(data):
    # "BM" alone also starts ordinary text: a BMP goes on with its size, four zero bytes, where
    # the pixels start, and the size of its info header (one of a few known sizes), so it is
    # never shorter than the 18 bytes that hold those
    return (len(data) >= 18 and data.startswith(b"BM") and data[6:10] == b"\0\0\0\0"
            and int.from_bytes(data[14:18], "little") in _BMP_INFO_SIZES)


def _text(data):
    """The bytes as text, to find the first element in. UTF-16 is known the way the XML parser
    knows it: by its byte-order mark, or by the zero byte beside the first character; anything
    else is read as UTF-8 (in every encoding the parser reads, the tags are plain ASCII)."""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", "replace")
    if data[:1] == b"\0":
        return data.decode("utf-16-be", "replace")
    if data[1:2] == b"\0":
        return data.decode("utf-16-le", "replace")
    return data.decode("utf-8", "replace")


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
    # Before anything is made of it: a text is copied once to be read at all. Measured 2026-10-13: the most a text
    # may be (10 MB, one long name) is held three times over while its kind is decided (31.5 MB at the peak).
    if len(data) > MAX_BYTES:
        raise Refusal("too-large", "The file is larger than %d MB, far more than a logo needs." % (MAX_BYTES // 1048576))
    text = _text(data)
    first = _FIRST.match(text, _first_element(text))
    name = first.group(1).lower() if first else ""
    if name == "svg" or name.endswith(":svg"):  # the root's own name, whatever prefix it carries
        return "svg"
    if name.rsplit(":", 1)[-1] in _PAGE or _SVG_TAG.search(text):
        # a page's own element comes first, or a drawing stands somewhere inside: a page, or a piece of one.
        # Nothing of it is read beyond this.
        raise Refusal("web-page", _svg.WEB_PAGE)
    return None


def load(data):
    """Say what the bytes are. Raises Refusal for a picture or anything it does not read."""
    kind = _kind(data)
    if kind is None:
        raise Refusal("unknown-file", UNKNOWN_FILE)
    return Source(kind, data, _zipin.open_zip(data) if kind == "zip" else None)


def _member(package, name):
    """One .svg entry of a package, held to what its bytes ARE like any other file: a page or a
    picture that was only named .svg is refused as that, with its way out. The entry is the one
    the owner named, in whichever Unicode form the name was typed (ZipPackage.named), and its
    bytes come back knowing the package's own name for it: every refusal of a package's file, here
    and in the check, says which file it is."""
    held = package.named(name)
    data = package.read_svg(name if held is None else held)   # (a name that is not there is refused there, as it was typed)
    try:
        kind = _kind(data)
    except Refusal as r:
        raise _svg.in_package(held, r) from None
    if kind != "svg":
        raise Refusal(
            "unknown-file",
            "The file %r in the package is not an SVG drawing, whatever its name says. Pick another file, or ask for "
            "a package of SVG files." % held,   # the whole name (see _svg.in_package)
        )
    return _svg.Member(data, held)


def mark(source, pick=None, mono=None):
    """The file to check, as the owner picked it. Raises Ask when the owner must choose first."""
    if mono and source.kind != "zip":
        raise Refusal(
            "mono-needs-zip",
            "A one-colour version was named (%r), but this is one SVG file, which holds no second file. Leave it out, or "
            "put both SVG files into one zip." % str(mono)[:40],
        )
    if source.kind == "svg":
        if pick is not None:
            raise Refusal(
                "nothing-to-pick",
                "A pick was given (%r), but this is one SVG file, so there is nothing to pick from. Leave the pick "
                "out." % str(pick)[:40],
            )
        return Mark(source.data, None, "svg", "the SVG")
    pkg = source.package
    names = pkg.svg_names
    if not names:
        raise Refusal(
            "zip-no-svg",
            "There is no SVG file in the package. This version reads only an SVG: ask whoever made the logo for one, "
            "or let the assistant help you get a new logo.",
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
    colour = _member(pkg, pick)
    return Mark(colour, _member(pkg, mono) if mono else None, "svg", colour.name)
