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
import struct
import unicodedata
import warnings
import zipfile
import zlib

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
# The package's own list of its files (the central directory): a kilobyte for each file there may be, counted
# over what the zip reader read of it (each entry's name, its "extra" notes and its comment, and the package's
# comment). It is counted AFTER the reader has gone through the list, so the reading is paid once whatever the
# list holds, and what bounds it is the 10 MB a package may be. Measured 2026-10-13 (processor time, best of
# three, load average 6 to 12): the slowest package found inside 10 MB, 150 to 159 entries with 64 KB of empty
# notes each, is read and refused in 1.4 to 1.5 seconds on Python 3.13 and 1.5 to 1.9 on Python 3.9; a list of
# 100,000 empty entries in 0.1 and 0.2.
MAX_DIRECTORY_BYTES = MAX_ENTRIES * 1024
_LOCAL_HEADER = 30                      # bytes of the header that stands before an entry's data
_SECOND_NAME = 0x7075                   # the note that gives an entry a second, "Unicode" name


class ZipPackage(object):
    def __init__(self, zf, infos, svg_names, other_names, ignored):
        self._zf = zf
        self._infos = infos   # the entry itself for each .svg name: the zip's own look-up goes by its own reading of the name
        self.svg_names = svg_names
        self.other_names = other_names
        self.ignored = ignored

    def read_svg(self, name):
        """The bytes of one `.svg` entry, never more than the entry says it holds."""
        if name not in self.svg_names:
            raise Refusal("no-such-file", "There is no SVG called %r in the package." % name[:80])
        info = self._infos[name]
        try:
            with warnings.catch_warnings():   # as in open_zip
                warnings.simplefilter("ignore")
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


def _second_names(zi):
    """The second names an entry carries in its notes (the "Unicode path" note, which tools write beside a name
    with letters beyond ASCII), each as (the checksum it gives, the bytes of the name), or None for one that
    cannot be read."""
    extra, pos, out = zi.extra, 0, []
    while pos + 4 <= len(extra):
        kind, size = struct.unpack_from("<HH", extra, pos)
        note = extra[pos + 4:pos + 4 + size]
        if kind == _SECOND_NAME:
            # one byte for the version (there is only version 1), four for a checksum, then the name
            out.append((struct.unpack_from("<L", note, 1)[0], note[5:]) if len(note) == size and size >= 5 and note[0] == 1 else None)
        pos += 4 + size
    return out


def _name(zi):
    """The one name an entry is shown, picked and checked by, the same on every version of the zip reader (a newer
    one goes by a second name where an older one does not know the note at all). `zi.orig_filename` is the entry's
    own name field as the reader read it: as UTF-8 where the entry is marked so, and otherwise in the old DOS letters
    (cp437), which gives every byte a letter, so the bytes of the field are had back from it.

    A second name is the entry's name where it belongs to it: its bytes are the name field's own bytes again (the way
    one common tool writes it), or its checksum is the checksum of the name field (what the note is for: the field
    in the old letters, the name in UTF-8 beside it, the checksum saying which field it was written for). It is UTF-8,
    it is not empty, and several of them say one name. Anything else refuses the package: before the rule, an entry
    called `plain.svg` with a second name of `a.svg<NUL>hidden` was listed as `a.svg` by a newer reader.

    With no second name, a name field that is not marked as UTF-8 and is not plain ASCII is read as UTF-8 where it
    is UTF-8: tools on a Mac write it so, and in the old letters `m<a umlaut>rk.svg` was shown as box-drawing signs."""
    held = zi.orig_filename
    marked = bool(zi.flag_bits & 0x800)
    field = held.encode("utf-8" if marked else "cp437", "replace")
    names = set()
    for note in _second_names(zi):
        try:
            if note is None or not note[1] or (note[1] != field and note[0] != zlib.crc32(field)):
                raise ValueError("not this entry's name")
            names.add(note[1].decode("utf-8"))
        except ValueError:   # (a name that is no UTF-8 is one too)
            names.add(None)
    if None in names or len(names) > 1:
        raise Refusal(
            "zip-second-name",
            "The package has a file with two names that do not belong together (it is listed as %s; a note beside it gives "
            "a second name that is not marked as this file's, or cannot be read), so the whole package is refused. Ask for "
            "a package saved again as a plain zip, with plain file names." % ascii(held[:60]),
        )
    if names:
        return names.pop()
    if not marked and not field.isascii():
        try:
            return field.decode("utf-8")
        except ValueError:
            pass
    return held


def open_zip(data):
    if len(data) > MAX_ZIP_BYTES:
        raise Refusal("zip-too-large", "The package is larger than %d MB, far more than a logo needs." % (MAX_ZIP_BYTES // 1048576))
    try:
        with warnings.catch_warnings():   # what the zip reader has to say about odd bytes is not the owner's to read
            warnings.simplefilter("ignore")
            zf = zipfile.ZipFile(io.BytesIO(data))
            infos = zf.infolist()
            listed = len(zf.comment) + sum(len(zi.orig_filename) + len(zi.extra) + len(zi.comment) for zi in infos)
    except Exception:  # see read_svg: whatever the zip reader raises for bytes that are no zip
        raise Refusal("zip-bad", "The package is not a readable zip file.") from None
    if len(infos) > MAX_ENTRIES:
        raise Refusal(
            "zip-too-many",
            "The package holds more than %d files, far more than a logo needs. Ask for a package with only the logo's own "
            "files in it." % MAX_ENTRIES,
        )
    if listed > MAX_DIRECTORY_BYTES:
        raise Refusal(
            "zip-list-too-large",
            "The package's own list of its files is far larger than a logo package's (more than %d KB of names and notes "
            "for %d files). Ask for a package with only the logo's own files in it, saved again as a plain zip."
            % (MAX_DIRECTORY_BYTES // 1024, len(infos)),
        )

    seen, total = set(), 0
    svg_names, other_names, ignored, by_name = [], [], [], {}
    for zi in infos:
        # The name is the whole name, as the entry holds it (see _name), never the reader's `filename`: the reader cuts
        # that at its first NUL (so `a.svg\0hidden` would be shown as `a.svg`) and turns this computer's own path
        # separator into a slash. `held` is the entry's own name field: a NUL or a backslash there refuses the
        # package too, whichever name the entry goes by.
        name, held = _name(zi), zi.orig_filename
        if _unseen(name) or "\0" in held:  # first: every later message shows the name
            raise Refusal(
                "zip-path",
                "The package has a file whose name holds something that cannot be seen: a hidden character, or a blank "
                "at its start, at its end or twice in a row (spelled out, the name starts %s). So the whole package is "
                "refused. Ask for a package with plain file names." % ascii((name if _unseen(name) else held)[:60]),
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
