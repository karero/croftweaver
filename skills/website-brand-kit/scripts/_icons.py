"""_icons.py: the seven icon files, made once from the one cleaned mark, and the preview sheet.

The starter links /favicon.svg, /favicon.ico, /apple-touch-icon.png, /icon-192.png, /icon-512.png,
/icon-maskable-512.png and COMPANY.logo (/images/logo.png) and ships none of them. This makes them
from the cleaned SVG with the site's own sharp (see _render.py), then looks at what it made:
nothing is trusted that was not looked at in Python (see _png.py).

The apple-touch and maskable icons sit on a solid background. It is chosen by arithmetic: the first
of the palette's light background, its dark background, white, black that keeps EVERY colour of the
mark at 3 to 1 or better (compared unrounded), never one of the mark's own colours. Where none
serves the colour version, the one-colour version is used and the owner is told; where none serves
that either, the owner is asked. Standard library only.
"""

from __future__ import annotations

import os
import struct
from collections import namedtuple

import _colour
import _png
from _refusal import Ask, Refusal

NEED = 3.0           # a graphic against its background (WCAG 1.4.11; BRAND.md's "3:1 large/UI")
PROBE = 256          # the size the mark is drawn at to see what it really paints
MIN_SOLID = 4        # fewer solid pixels than this and a colour is not really there
APPLE_SCALE = 0.8
MASKABLE_SCALE = 0.56   # corners of a mark filling its viewBox then sit at 0.396, inside the 0.4 safe circle

# The preview sheet: one panel per theme, 16 and 32 px at actual size on top, the same pixels
# blown up eight times (nearest neighbour, so the owner sees the pixels) below.
PANEL_W, PANEL_H = 432, 336
AT_16, AT_32 = (16, 16), (48, 16)
BIG_16, BIG_32 = (16, 64), (160, 64)
ZOOM = 8

Choice = namedtuple("Choice", "version background")
IconSet = namedtuple("IconSet", "files version background visible notes")


def backgrounds(palette):
    """The backgrounds worth trying, in order, each once."""
    out = []
    for theme in ("light", "dark"):
        bg = palette.theme(theme).get("bg")
        if bg and bg not in out:
            out.append(bg)
    for fallback in ("#ffffff", "#000000"):
        if fallback not in out:
            out.append(fallback)
    return out


def choose_background(colour_sets, candidates):
    """The first background that keeps every colour of a version at 3 to 1 or better. `colour_sets`
    is [("colour", colours)] or [("colour", colours), ("mono", colours)], in order of preference."""
    for version, colours in colour_sets:
        for bg in candidates:
            if all(_colour.ratio(c, bg) >= NEED for c in colours):
                return Choice(version, bg)
    have_mono = any(v == "mono" for v, _ in colour_sets)
    raise Ask(
        "no-background",
        "No background keeps every colour of the mark at 3 to 1 or better against it, so the app icons would lose part "
        "of the mark%s. Give the one-colour version of the mark (the file that holds the mark in a single colour), "
        "or ask the tool for a version whose colours are further apart in lightness." % (
            " (the one-colour version you gave does not serve either)" if have_mono else ""),
    )


def ico_from_png(png):
    """A .ico holding one 32 x 32 PNG: a 22-byte header, then the PNG as it is."""
    if _png.size(png) != (32, 32):
        raise Refusal("icon-bad", "The favicon.ico is made from a 32 x 32 picture only.")
    return b"\x00\x00\x01\x00\x01\x00" + struct.pack("<BBBBHHII", 32, 32, 0, 0, 1, 32, len(png), 22) + png


def _job(name, size, scale=1.0, background=None):
    return {"name": name, "file": name + ".png", "size": size, "scale": scale, "background": background}


def _read(path):
    with open(path, "rb") as f:
        return f.read()


def _visible(clean, renderer, workdir, label):
    """The colours of `clean` that really show, and a note for each that does not."""
    renderer.render(clean.text, clean.view_box, [_job("probe-" + label, PROBE)], workdir)
    pic = _png.decode(_read(os.path.join(workdir, "probe-%s.png" % label)))
    seen = [c for c in clean.colours if _png.count_colour(pic, c, tolerance=3) >= MIN_SOLID]
    if not seen:  # blank, or only faint edges: nothing solid of any colour
        raise Refusal(
            "blank-render",
            "The mark is blank when it is drawn: nothing solid shows on the canvas (it may sit outside its own box, or be "
            "too thin to see). Ask the tool for the SVG again.",
        )
    notes = ["the colour %s is painted in the file but never shows (something is drawn over it), so it is left out of the checks" % c
             for c in clean.colours if c not in seen]
    return seen, notes


def build(clean, mono, palette, renderer, workdir):
    """Everything the intake installs under public/: {relative path: bytes}, which version the app
    icons use and on what background, the colours that really show, and what to tell the owner."""
    os.makedirs(workdir, exist_ok=True)
    seen, notes = _visible(clean, renderer, workdir, "colour")
    sets = [("colour", seen)]
    mono_seen = None
    if mono is not None:
        mono_seen, mono_notes = _visible(mono, renderer, workdir, "mono")
        sets.append(("mono", mono_seen))
        notes += mono_notes
    choice = choose_background(sets, backgrounds(palette))
    chosen = mono if choice.version == "mono" else clean
    if choice.version == "mono":
        notes.append("no background keeps every colour of the colour version at 3 to 1, so the app icons (apple-touch and "
                     "maskable) are drawn from the one-colour version on %s" % choice.background)

    renderer.render(clean.text, clean.view_box, [_job("favicon-32", 32), _job("icon-192", 192), _job("icon-512", 512)], workdir)
    renderer.render(chosen.text, chosen.view_box, [_job("apple-touch", 180, APPLE_SCALE, choice.background),
                                                   _job("maskable", 512, MASKABLE_SCALE, choice.background)], workdir)
    png = {n: _read(os.path.join(workdir, n + ".png")) for n in ("favicon-32", "icon-192", "icon-512", "apple-touch", "maskable")}

    for name, side in (("favicon-32", 32), ("icon-192", 192), ("icon-512", 512), ("apple-touch", 180), ("maskable", 512)):
        if _png.size(png[name]) != (side, side):
            raise Refusal("icon-bad", "The %s icon did not come out %d x %d." % (name, side, side))
    if _png.is_blank(_png.decode(png["favicon-32"])):
        raise Refusal("blank-render", "The 32 pixel icon came out blank. Ask the tool for the SVG again.")
    for name in ("apple-touch", "maskable"):
        if not _png.is_opaque(_png.decode(png[name])):
            raise Refusal("icon-bad", "The %s icon is not fully opaque." % name)

    files = {
        "public/favicon.svg": clean.text.encode("utf-8"),
        "public/favicon.ico": ico_from_png(png["favicon-32"]),
        "public/apple-touch-icon.png": png["apple-touch"],
        "public/icon-192.png": png["icon-192"],
        "public/icon-512.png": png["icon-512"],
        "public/icon-maskable-512.png": png["maskable"],
        # the same 512 px picture as icon-512: the mark kept in its proportions and centred in a square
        # (the share-card generator stretches whatever it loads to 460 x 460, so it must be square)
        "public/images/logo.png": png["icon-512"],
    }
    return IconSet(files, choice.version, choice.background, seen, notes)


# --- the preview -----------------------------------------------------------------------

def _over(background, picture):
    """The picture's pixels composited on a solid background: RGBA rows of the picture's size."""
    w, h, rgba = picture
    br, bg_, bb = background
    out = bytearray(w * h * 4)
    for i in range(0, len(rgba), 4):
        a = rgba[i + 3]
        out[i] = (rgba[i] * a + br * (255 - a) + 127) // 255
        out[i + 1] = (rgba[i + 1] * a + bg_ * (255 - a) + 127) // 255
        out[i + 2] = (rgba[i + 2] * a + bb * (255 - a) + 127) // 255
        out[i + 3] = 255
    return w, h, out


def _hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def preview(svg_text, view_box, palette, renderer, workdir):
    """A PNG for the owner: the installed mark at 16 and 32 px, on the light and the dark
    background, at actual size and magnified (the pixels blown up, not smoothed)."""
    os.makedirs(workdir, exist_ok=True)
    renderer.render(svg_text, view_box, [_job("preview-16", 16), _job("preview-32", 32)], workdir)
    small = {s: _png.decode(_read(os.path.join(workdir, "preview-%d.png" % s))) for s in (16, 32)}
    themes = [t for t in ("light", "dark") if palette.theme(t).get("bg")]
    if not themes:
        raise Refusal("no-palette", "There is no background colour to show the mark on.")
    width = PANEL_W * len(themes)
    sheet = bytearray(width * PANEL_H * 4)
    for n, theme in enumerate(themes):
        bg = _hex_rgb(palette.theme(theme)["bg"])
        ox = n * PANEL_W
        for y in range(PANEL_H):
            row = (y * width + ox) * 4
            sheet[row:row + PANEL_W * 4] = bytes(bg + (255,)) * PANEL_W
        for size, at, big in ((16, AT_16, BIG_16), (32, AT_32, BIG_32)):
            w, h, px = _over(bg, small[size])
            for y in range(h):
                for x in range(w):
                    v = bytes(px[(y * w + x) * 4:(y * w + x) * 4 + 4])
                    i = ((at[1] + y) * width + ox + at[0] + x) * 4
                    sheet[i:i + 4] = v
                    for dy in range(ZOOM):
                        j = ((big[1] + y * ZOOM + dy) * width + ox + big[0] + x * ZOOM) * 4
                        sheet[j:j + ZOOM * 4] = v * ZOOM
    return _png.encode(width, PANEL_H, bytes(sheet))
