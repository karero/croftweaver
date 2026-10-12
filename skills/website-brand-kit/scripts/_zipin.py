"""_zipin.py: read a zip of SVG files that came from outside, in memory, and never extract it.

The owner saves a package from a design tool and hands over its path. The package is data, not
a place to run anything: it is read from bytes, its central directory is checked against caps
before any entry is inflated, only `.svg` entries are ever opened (a README beside them is
listed by name and never read), and anything odd refuses the whole zip with the reason.
Standard library only.
"""

from __future__ import annotations

import io
import re
import stat
import unicodedata
import zipfile
import zlib

from _refusal import Refusal
import _svg

MAX_ZIP_BYTES = 10 * 1024 * 1024
MAX_ENTRIES = 200
MAX_OTHER_BYTES = 64 * 1024 * 1024      # declared size of an entry that is never read
MAX_TOTAL_BYTES = 128 * 1024 * 1024     # declared size of all entries together
MAX_RATIO = 100                         # declared size over compressed size ...
RATIO_FROM = 64 * 1024                  # ... for any entry this big (tiny files compress unevenly)
_METHODS = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
MAX_NAME = 120                          # characters in an entry's whole path: it is shown to the owner as it is
# What Unicode files as a control, a format mark (the ones that turn the reading order round, the
# zero-width ones, the invisible "tag" letters), a private or unassigned character, half a pair, or
# a line or paragraph break: none of it can be seen in a name, and a name is shown as it is.
_UNSEEN = ("Cc", "Cf", "Co", "Cn", "Cs", "Zl", "Zp")
# Drawn as nothing too, though Unicode files them as marks or letters: the variation selectors
# (256 of them: enough to spell out a hidden text) and the blank fillers.
_UNSEEN_TOO = re.compile("[\u034f\u115f\u1160\u17b4\u17b5\u180b-\u180f\u3164\ufe00-\ufe0f\uffa0\U000e0100-\U000e01ef]")


class ZipPackage(object):
    def __init__(self, zf, svg_names, other_names, ignored):
        self._zf = zf
        self.svg_names = svg_names
        self.other_names = other_names
        self.ignored = ignored

    def read_svg(self, name):
        """The bytes of one `.svg` entry, never more than the entry says it holds."""
        if name not in self.svg_names:
            raise Refusal("no-such-file", "There is no SVG called %r in the package." % name[:80])
        info = self._zf.getinfo(name)
        try:
            with self._zf.open(info) as f:
                data = f.read(info.file_size + 1)
        except (zipfile.BadZipFile, zlib.error, EOFError, OSError, ValueError, NotImplementedError, RuntimeError):
            raise Refusal("zip-bad", "The package is damaged: %r cannot be read." % name[:80]) from None
        if len(data) != info.file_size:
            raise Refusal("zip-bad", "The package is damaged: %r is not the size it says." % name[:80])
        return data


def _same_name(name):
    return unicodedata.normalize("NFC", name).casefold()


def _unseen(name):
    return _UNSEEN_TOO.search(name) or any(unicodedata.category(c) in _UNSEEN for c in name)


def open_zip(data):
    if len(data) > MAX_ZIP_BYTES:
        raise Refusal("zip-too-large", "The package is larger than %d MB, far more than a logo needs." % (MAX_ZIP_BYTES // 1048576))
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        infos = zf.infolist()
    except (zipfile.BadZipFile, EOFError, OSError, ValueError, NotImplementedError, RuntimeError):
        raise Refusal("zip-bad", "The package is not a readable zip file.") from None
    if len(infos) > MAX_ENTRIES:
        raise Refusal("zip-too-many", "The package holds more than %d files, far more than a logo needs." % MAX_ENTRIES)

    seen, total = set(), 0
    svg_names, other_names, ignored = [], [], []
    for zi in infos:
        name = zi.filename
        if _unseen(name):  # first: every later message shows the name
            raise Refusal(
                "zip-path",
                "The package has a file whose name holds a character that cannot be seen (spelled out, the name starts "
                "%s), so the whole package is refused. Ask for a package with plain file names." % ascii(name[:60]),
            )
        if (
            not name
            or name.startswith("/")
            or "\\" in name
            or re.match(r"[A-Za-z]:", name)  # a drive letter
            or ".." in name.split("/")
        ):
            raise Refusal("zip-path", "The package has a file with an unsafe path (%r), so the whole package is refused." % name[:60])
        if len(name) > MAX_NAME:
            raise Refusal(
                "zip-name",
                "The package has a file whose name is longer than %d characters (it starts %r), so the whole package "
                "is refused. Ask for a package with short, plain file names." % (MAX_NAME, name[:40]),
            )
        if stat.S_ISLNK(zi.external_attr >> 16):
            raise Refusal("zip-symlink", "The package holds a shortcut (symbolic link, %r), so the whole package is refused." % name[:60])
        if zi.flag_bits & 0x1:
            raise Refusal("zip-encrypted", "The package is password-protected, which this check cannot read. Ask for one without a password.")
        is_dir = name.endswith("/")
        key = _same_name(name.rstrip("/"))
        if key in seen:
            raise Refusal("zip-duplicate", "The package holds two files with the same name (%r), so the whole package is refused." % name[:60])
        seen.add(key)
        if is_dir:
            continue
        if zi.compress_type not in _METHODS:
            raise Refusal("zip-method", "The package uses a compression this check does not read (only stored and deflated are).")
        is_svg = name.lower().endswith(".svg")
        if zi.file_size > (_svg.MAX_BYTES if is_svg else MAX_OTHER_BYTES):
            raise Refusal("zip-entry-too-large", "A file in the package (%r) is far larger than a logo needs, so the whole package is refused." % name[:60])
        if zi.file_size >= RATIO_FROM and zi.file_size > zi.compress_size * MAX_RATIO:
            raise Refusal("zip-ratio", "A file in the package (%r) is packed far tighter than real files are, so the whole package is refused." % name[:60])
        total += zi.file_size
        if total > MAX_TOTAL_BYTES:
            raise Refusal("zip-total-too-large", "The package unpacks to far more than a logo needs, so the whole package is refused.")
        parts = name.split("/")
        base = parts[-1]
        if parts[0] == "__MACOSX" or base.startswith("._") or base == ".DS_Store":
            ignored.append(name)
            continue
        if len(parts) > 2:
            raise Refusal("zip-nested", "The package has files more than one folder deep (%r). Ask for a flatter package." % name[:60])
        (svg_names if is_svg else other_names).append(name)
    return ZipPackage(zf, svg_names, other_names, ignored)
