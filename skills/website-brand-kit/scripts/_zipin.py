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

from _refusal import Refusal, unseen
import _svg

MAX_ZIP_BYTES = 10 * 1024 * 1024
MAX_ENTRIES = 200
MAX_OTHER_BYTES = 64 * 1024 * 1024      # declared size of an entry that is never read
MAX_TOTAL_BYTES = 128 * 1024 * 1024     # declared size of all entries together
MAX_RATIO = 100                         # declared size over compressed size ...
RATIO_FROM = 64 * 1024                  # ... for any entry this big (tiny files compress unevenly)
_METHODS = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
MAX_NAME = 120                          # characters in an entry's whole path: it is shown to the owner as it is
# The package's own list of its files (the central directory): a kilobyte for each file there may be. The zip
# reader works through all of it before it hands back one name, and through each entry's "extra" notes one
# small step at a time: measured 2026-10-13, a package of 9.8 MB whose 150 entries each carried 64 KB of
# empty notes took 4 seconds to open.
MAX_DIRECTORY_BYTES = MAX_ENTRIES * 1024
_LOCAL_HEADER = 30                      # bytes of the header that stands before an entry's data


class ZipPackage(object):
    def __init__(self, zf, infos, svg_names, other_names, ignored):
        self._zf = zf
        self._infos = infos   # the entry itself for each .svg name: the zip's own look-up goes by a name it has cut short
        self.svg_names = svg_names
        self.other_names = other_names
        self.ignored = ignored

    def read_svg(self, name):
        """The bytes of one `.svg` entry, never more than the entry says it holds."""
        if name not in self.svg_names:
            raise Refusal("no-such-file", "There is no SVG called %r in the package." % name[:80])
        info = self._infos[name]
        try:
            with self._zf.open(info) as f:
                data = f.read(info.file_size + 1)
        except Exception:
            # Whatever the zip reader makes of a damaged entry (a bad zip, a zlib error, an OverflowError from
            # an offset of 2 to the 64th, a struct error ...): the list of what it may raise is not this
            # module's to keep, and every one of them means the same to the owner.
            raise Refusal("zip-bad", "The package is damaged: %r cannot be read." % name[:80]) from None
        if len(data) != info.file_size:
            raise Refusal("zip-bad", "The package is damaged: %r is not the size it says." % name[:80])
        return data


def _same_name(name):
    return unicodedata.normalize("NFC", name).casefold()


def _unseen(name):
    """Does the name hold anything a reader cannot see? A character that is drawn as nothing or as a
    blank (see _refusal.unseen), or a plain space where it does not show as a gap between two visible
    things: at the start or the end of a folder's or a file's name, or two in a row."""
    return (any(unseen(c) for c in name)
            or any(part != part.strip(" ") or "  " in part for part in name.split("/")))


def _directory_bytes(data):
    """How large the package says its list of files is, found the way the zip reader itself finds it (so
    that this is the list it would go on to read), or 0 where that cannot be asked: then the reader decides."""
    find = getattr(zipfile, "_EndRecData", None)  # the reader's own first step; not part of what it promises to keep
    try:
        end = find(io.BytesIO(data)) if find else None
        return int(end[getattr(zipfile, "_ECD_SIZE", 5)]) if end else 0
    except Exception:
        return 0


def open_zip(data):
    if len(data) > MAX_ZIP_BYTES:
        raise Refusal("zip-too-large", "The package is larger than %d MB, far more than a logo needs." % (MAX_ZIP_BYTES // 1048576))
    too_many = Refusal(
        "zip-too-many",
        "The package holds more than %d files, far more than a logo needs. Ask for a package with only the logo's own "
        "files in it." % MAX_ENTRIES,
    )
    if _directory_bytes(data) > MAX_DIRECTORY_BYTES:  # before the reader is let loose on it
        raise too_many
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        infos = zf.infolist()
    except Exception:  # see read_svg: whatever the zip reader raises for bytes that are no zip
        raise Refusal("zip-bad", "The package is not a readable zip file.") from None
    if len(infos) > MAX_ENTRIES:
        raise too_many

    seen, total = set(), 0
    svg_names, other_names, ignored, by_name = [], [], [], {}
    for zi in infos:
        # `filename` is the name the reader goes by, and `orig_filename` the name as the entry holds it: the reader
        # cuts that at its first NUL (so `a.svg\0hidden` would be shown as `a.svg`) and turns this computer's own
        # path separator into a slash. What it cuts off or turns round is checked here all the same.
        name, held = zi.filename, zi.orig_filename
        if _unseen(name) or "\0" in held:  # first: every later message shows the name
            raise Refusal(
                "zip-path",
                "The package has a file whose name holds something that cannot be seen: a hidden character, or a blank "
                "at its start, at its end or twice in a row (spelled out, the name starts %s). So the whole package is "
                "refused. Ask for a package with plain file names." % ascii((held if "\0" in held else name)[:60]),
            )
        if (
            not name
            or name.startswith("/")
            or "\\" in name
            or "\\" in held
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
        if not 0 <= zi.header_offset <= len(data) - _LOCAL_HEADER:
            # where the entry is said to start is not inside the package (an offset of 2 to the 64th once ended in a traceback)
            raise Refusal("zip-bad", "The package is damaged: %r is not where the package says it is. Download or save the package again." % name[:60])
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
        if is_svg:
            by_name[name] = zi
    return ZipPackage(zf, by_name, svg_names, other_names, ignored)
