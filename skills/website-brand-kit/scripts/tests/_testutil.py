"""Shared helpers for the website-brand-kit tests (standard library only)."""

import io
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..")
FIXTURES = os.path.join(HERE, "fixtures")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
STARTER = os.path.join(REPO, "skills", "new-website", "templates", "astro")
BRAND_TEMPLATE = os.path.join(REPO, "skills", "new-website", "templates", "brand.md")
sys.path.insert(0, SCRIPTS)

# A real handoff package from a design tool (2,000 bytes; a made-up bakery): one top-level
# folder holding README.txt, the colour mark and its one-colour twin. See the plan, D3.
REAL_ZIP = os.path.join(FIXTURES, "baeckerei-example-logo-furrows.zip")
REAL_COLOUR = "baeckerei-example-logo-furrows/baeckerei-mark-3-furrows.svg"
REAL_MONO = "baeckerei-example-logo-furrows/baeckerei-mark-3-furrows-mono.svg"


def real_zip_bytes():
    with open(REAL_ZIP, "rb") as f:
        return f.read()


def real_svg(name=REAL_COLOUR):
    with zipfile.ZipFile(io.BytesIO(real_zip_bytes())) as z:
        return z.read(name)


def build_zip(entries, compression=zipfile.ZIP_DEFLATED):
    """A zip in memory. entries: list of (name, bytes) or (ZipInfo, bytes)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression) as z:
        for name, data in entries:
            if isinstance(name, zipfile.ZipInfo):
                z.writestr(name, data, compress_type=compression)
            else:
                z.writestr(name, data)
    return buf.getvalue()


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def starter_file(rel):
    return read(os.path.join(STARTER, *rel.split("/")))


# The made-up bakery's palette: warm cream and brown, one accent, passes the whole matrix.
BAKERY_LIGHT = {"heading": "#3a1d0a", "ink": "#3a2a1e", "muted": "#6b5744", "accent": "#b4531a", "link": "#a14a14",
                "line": "#e8d9c4", "bg": "#fff8ee", "bg_soft": "#fef5e8", "surface": "#ffffff"}
BAKERY_DARK = {"heading": "#fbeedd", "ink": "#efe2d2", "muted": "#c4ae98", "accent": "#e2874a", "link": "#eaa072",
               "line": "#3d2f24", "bg": "#1a120d", "bg_soft": "#231912", "surface": "#2a1f17"}


# --- a tiny PNG writer, so the tests can make pictures without any renderer ---------------

import struct  # noqa: E402
import zlib  # noqa: E402


def _chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else (b if pb <= pc else c)


def make_png(width, height, rows, colour_type=6, filters=None, palette=None, trns=None, interlace=0, bit_depth=8):
    """A PNG from `rows`: a list of rows, each a bytes object of raw samples. `filters` is a list
    of filter types (0 to 4), one per row, applied the way a real encoder does."""
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colour_type]
    bpp = channels * (bit_depth // 8 if bit_depth >= 8 else 1)
    raw, prev = b"", bytes(len(rows[0]))
    for i, row in enumerate(rows):
        f = (filters or [0] * len(rows))[i]
        out = bytearray()
        for x, v in enumerate(row):
            a = row[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            pred = (0, a, b, (a + b) // 2, _paeth(a, b, c))[f]
            out.append((v - pred) & 0xFF)
        raw += bytes([f]) + bytes(out)
        prev = row
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, bit_depth, colour_type, 0, 0, interlace))
    if palette:
        png += _chunk(b"PLTE", b"".join(bytes(c) for c in palette))
    if trns:
        png += _chunk(b"tRNS", bytes(trns))
    return png + _chunk(b"IDAT", zlib.compress(raw)) + _chunk(b"IEND", b"")


def solid_rgba(width, height, rgba):
    return [bytes(rgba) * width for _ in range(height)]


# --- a site folder to render in -----------------------------------------------------------
# The renderer loads `sharp` from the folder it is started in, as it does in a real site. Tests
# borrow the node_modules of an install of the starter (CI installs it; locally, point
# BRAND_KIT_NODE_MODULES at one). Without it the tests that render are skipped, and with
# REQUIRE_SHARP=1 (CI) a skip is a failure, so a job that tested less cannot stay green.

import shutil  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402


def node_modules_dir():
    env = os.environ.get("BRAND_KIT_NODE_MODULES")
    for c in ([env] if env else [os.path.join(STARTER, "node_modules")]):
        if c and os.path.isdir(os.path.join(c, "sharp")):
            return os.path.abspath(c)
    return None


def sharp_problem():
    """Why the tests that render cannot run here, or None."""
    node = shutil.which("node")
    if not node:
        return "no node on this machine"
    nm = node_modules_dir()
    if not nm:
        return "no install of the starter to borrow sharp from (set BRAND_KIT_NODE_MODULES)"
    with tempfile.TemporaryDirectory() as d:
        make_site(d, nm)
        r = subprocess.run([node, "-e", "require('sharp')"], cwd=d, capture_output=True, text=True)
        if r.returncode:
            return "sharp does not load from %s: %s" % (nm, (r.stderr.strip().splitlines() or ["?"])[-1][:120])
    return None


def require_sharp(testcase):
    why = sharp_problem()
    if why:
        if os.environ.get("REQUIRE_SHARP"):
            testcase.fail("REQUIRE_SHARP is set but the render tests cannot run: " + why)
        testcase.skipTest(why)


def make_site(folder, node_modules=None):
    """A bare 'site': a package.json and, when given, a link to a node_modules folder."""
    with open(os.path.join(folder, "package.json"), "w", encoding="utf-8") as f:
        f.write('{"name": "site", "version": "1.0.0", "type": "module", "private": true}\n')
    if node_modules:
        os.symlink(node_modules, os.path.join(folder, "node_modules"))
    return folder


# --- a whole site, made from the starter ------------------------------------------------------

TEMPLATES_GITIGNORE = os.path.join(REPO, "skills", "new-website", "templates", ".gitignore")


def make_starter_site(folder, with_modules=True):
    """The starter as a site folder: its files, the site's .gitignore, and (when there is one to borrow)
    a link to an install's node_modules. No git, no npm run: the tests that need those say so."""
    shutil.copytree(STARTER, folder, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("node_modules", "dist", ".astro", "test-results", "playwright-report"))
    shutil.copy(TEMPLATES_GITIGNORE, os.path.join(folder, ".gitignore"))
    nm = node_modules_dir()
    if with_modules and nm:
        os.symlink(nm, os.path.join(folder, "node_modules"))
    return folder


def pillow_problem():
    import importlib.util
    py = shutil.which("python3") or shutil.which("python")
    if not py:
        return "no python3 on the path"
    r = subprocess.run([py, "-c", "import PIL"], capture_output=True)
    return None if r.returncode == 0 else "Pillow is not installed for %s" % py


def require_pillow(testcase):
    why = pillow_problem()
    if why:
        if os.environ.get("REQUIRE_SHARP"):
            testcase.fail("REQUIRE_SHARP is set but the share-card tests cannot run: " + why)
        testcase.skipTest(why)
