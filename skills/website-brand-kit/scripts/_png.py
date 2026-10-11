"""_png.py: read the pictures the renderer writes, so every judgement about them is made in Python.

Only decoding, and only what the renderer produces: 8-bit PNGs, not interlaced, grey, grey with
alpha, RGB, RGBA or palette. A picture comes back as (width, height, RGBA bytes). The caps stop a
file that claims to be enormous before anything is inflated. Standard library only.
"""

from __future__ import annotations

import struct
import zlib

from _refusal import Refusal

SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_SIDE = 8192
MAX_PIXELS = 16 * 1024 * 1024
_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def _bad(why="it is not a readable PNG"):
    return Refusal("png-bad", "A picture the renderer wrote cannot be read (%s)." % why)


def _chunks(data):
    if data[:8] != SIGNATURE:
        raise _bad("no PNG signature")
    pos, n = 8, len(data)
    while pos + 12 <= n:
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        if length > n - pos - 12:
            raise _bad("a chunk runs past the end")
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
        if zlib.crc32(kind + body) & 0xFFFFFFFF != crc:
            raise _bad("a chunk's checksum is wrong")
        yield kind, body
        if kind == b"IEND":
            return
        pos += 12 + length
    raise _bad("no end chunk")


def _header(body):
    if len(body) != 13:
        raise _bad("the header is the wrong length")
    w, h, depth, colour, _comp, _filt, interlace = struct.unpack(">IIBBBBB", body)
    return w, h, depth, colour, interlace


def size(data):
    """(width, height) from the header alone."""
    for kind, body in _chunks(data):
        if kind == b"IHDR":
            w, h, *_ = _header(body)
            return w, h
        break
    raise _bad("no header")


def decode(data):
    ihdr = plte = trns = None
    idat = []
    for kind, body in _chunks(data):
        if kind == b"IHDR" and ihdr is None:
            ihdr = _header(body)
        elif kind == b"PLTE":
            plte = body
        elif kind == b"tRNS":
            trns = body
        elif kind == b"IDAT":
            idat.append(body)
    if ihdr is None or not idat:
        raise _bad("the header or the picture data is missing")
    w, h, depth, colour, interlace = ihdr
    if depth != 8 or interlace != 0 or colour not in _CHANNELS:
        raise Refusal("png-unsupported", "A picture the renderer wrote is in a form this check does not read.")
    if not (0 < w <= MAX_SIDE and 0 < h <= MAX_SIDE and w * h <= MAX_PIXELS):
        raise Refusal("png-too-large", "A picture the renderer wrote is far larger than an icon.")
    bpp = _CHANNELS[colour]
    stride = w * bpp
    expected = (stride + 1) * h
    try:
        raw = zlib.decompressobj().decompress(b"".join(idat), expected + 1)
    except zlib.error:
        raise _bad("the picture data is damaged") from None
    if len(raw) != expected:
        raise _bad("the picture data is the wrong length")
    rows, prev = [], bytearray(stride)
    for y in range(h):
        f = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        if f == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
        elif f != 0:
            raise _bad("an unknown row filter")
        rows.append(line)
        prev = line
    out = bytearray(w * h * 4)
    o = 0
    for line in rows:
        if colour == 6:
            out[o:o + stride] = line
            o += stride
        elif colour == 2:
            for i in range(0, stride, 3):
                out[o:o + 4] = line[i:i + 3] + b"\xff"
                o += 4
        elif colour == 0:
            for v in line:
                out[o:o + 4] = bytes((v, v, v, 255))
                o += 4
        elif colour == 4:
            for i in range(0, stride, 2):
                v = line[i]
                out[o:o + 4] = bytes((v, v, v, line[i + 1]))
                o += 4
        else:  # palette
            if plte is None:
                raise _bad("a palette picture with no palette")
            for v in line:
                if v * 3 + 3 > len(plte):
                    raise _bad("a palette index out of range")
                alpha = trns[v] if trns is not None and v < len(trns) else 255
                out[o:o + 4] = plte[v * 3:v * 3 + 3] + bytes((alpha,))
                o += 4
    return w, h, bytes(out)


# --- looking at a decoded picture --------------------------------------------------------

def at(picture, x, y):
    w, _h, rgba = picture
    i = (y * w + x) * 4
    return tuple(rgba[i:i + 4])


def count_colour(picture, hex_colour, tolerance=0, min_alpha=250):
    """How many pixels are this colour and solid. A half see-through pixel is an edge of the shape,
    not the colour."""
    _w, _h, rgba = picture
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    n = 0
    for i in range(0, len(rgba), 4):
        if rgba[i + 3] >= min_alpha and abs(rgba[i] - r) <= tolerance and abs(rgba[i + 1] - g) <= tolerance and abs(rgba[i + 2] - b) <= tolerance:
            n += 1
    return n


def is_blank(picture, min_pixels=4, min_alpha=64):
    """Nothing to see: fewer than `min_pixels` pixels are even half there."""
    _w, _h, rgba = picture
    n = 0
    for i in range(3, len(rgba), 4):
        if rgba[i] >= min_alpha:
            n += 1
            if n >= min_pixels:
                return False
    return True


def is_opaque(picture):
    _w, _h, rgba = picture
    return all(rgba[i] == 255 for i in range(3, len(rgba), 4))
