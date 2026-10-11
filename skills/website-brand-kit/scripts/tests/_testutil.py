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


def starter_file(rel):
    return read(os.path.join(STARTER, *rel.split("/")))


# The made-up bakery's palette: warm cream and brown, one accent, passes the whole matrix.
BAKERY_LIGHT = {"heading": "#3a1d0a", "ink": "#3a2a1e", "muted": "#6b5744", "accent": "#b4531a", "link": "#a14a14",
                "line": "#e8d9c4", "bg": "#fff8ee", "bg_soft": "#fef5e8", "surface": "#ffffff"}
BAKERY_DARK = {"heading": "#fbeedd", "ink": "#efe2d2", "muted": "#c4ae98", "accent": "#e2874a", "link": "#eaa072",
               "line": "#3d2f24", "bg": "#1a120d", "bg_soft": "#231912", "surface": "#2a1f17"}
