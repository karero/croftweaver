"""The PNG reader. The renderer writes the pictures; every judgement about them (blank, opaque,
is this colour really visible) is made here, in plain Python, so it can be tested without Node.
These tests build PNGs by hand, with every filter type a real encoder uses.
"""

import unittest
import zlib

import _testutil as T
import _png
from _refusal import Refusal


def pixel(decoded, x, y):
    w, _h, rgba = decoded
    i = (y * w + x) * 4
    return tuple(rgba[i:i + 4])


class Decoding(unittest.TestCase):
    def rows(self):
        # a 3 x 4 picture whose pixels all differ, so a wrong filter gives a wrong value somewhere
        return [bytes((10 * y + 7 * x + c * 31) % 256 for x in range(3) for c in range(4)) for y in range(4)]

    def test_every_filter_type_gives_the_same_picture_back(self):
        rows = self.rows()
        want = b"".join(rows)
        for f in range(5):
            with self.subTest(filter=f):
                w, h, rgba = _png.decode(T.make_png(3, 4, rows, filters=[f] * 4))
                self.assertEqual((w, h, rgba), (3, 4, want))
        mixed = _png.decode(T.make_png(3, 4, rows, filters=[1, 2, 3, 4]))
        self.assertEqual(mixed[2], want)

    def test_a_busy_picture_through_every_filter_so_that_no_branch_of_paeth_is_left_out(self):
        import random
        rnd = random.Random(7)
        rows = [bytes(rnd.randrange(256) for _ in range(16 * 4)) for _ in range(16)]
        want = b"".join(rows)
        for f in range(5):
            with self.subTest(filter=f):
                self.assertEqual(_png.decode(T.make_png(16, 16, rows, filters=[f] * 16))[2], want)

    def test_rgb_grey_grey_alpha_and_palette_come_back_as_rgba(self):
        rgb = _png.decode(T.make_png(2, 1, [bytes([1, 2, 3, 4, 5, 6])], colour_type=2))
        self.assertEqual(pixel(rgb, 1, 0), (4, 5, 6, 255))
        grey = _png.decode(T.make_png(2, 1, [bytes([9, 200])], colour_type=0))
        self.assertEqual(pixel(grey, 1, 0), (200, 200, 200, 255))
        ga = _png.decode(T.make_png(2, 1, [bytes([9, 50, 200, 255])], colour_type=4))
        self.assertEqual((pixel(ga, 0, 0), pixel(ga, 1, 0)), ((9, 9, 9, 50), (200, 200, 200, 255)))
        pal = _png.decode(T.make_png(2, 1, [bytes([1, 0])], colour_type=3, palette=[(255, 0, 0), (0, 255, 0)], trns=[128, 255]))
        self.assertEqual((pixel(pal, 0, 0), pixel(pal, 1, 0)), ((0, 255, 0, 255), (255, 0, 0, 128)))

    def test_size_without_decoding(self):
        self.assertEqual(_png.size(T.make_png(5, 2, T.solid_rgba(5, 2, (1, 2, 3, 4)))), (5, 2))

    def test_what_is_not_a_png_is_refused(self):
        good = T.make_png(2, 2, T.solid_rgba(2, 2, (1, 2, 3, 255)))
        for name, data in (("empty", b""), ("signature", b"\x89PNG\r\n\x1b\n" + good[8:]), ("truncated", good[:-20]),
                           ("text", b"not a png at all")):
            with self.subTest(name=name):
                with self.assertRaises(Refusal) as cm:
                    _png.decode(data)
                self.assertEqual(cm.exception.code, "png-bad")

    def test_a_chunk_whose_checksum_is_wrong_is_refused(self):
        good = bytearray(T.make_png(2, 2, T.solid_rgba(2, 2, (1, 2, 3, 255))))
        good[20] ^= 0xFF  # inside IHDR
        with self.assertRaises(Refusal) as cm:
            _png.decode(bytes(good))
        self.assertEqual(cm.exception.code, "png-bad")

    def test_interlaced_and_deep_pictures_are_not_read(self):
        for kw in ({"interlace": 1}, {"bit_depth": 16}):
            with self.subTest(kw=kw):
                with self.assertRaises(Refusal) as cm:
                    _png.decode(T.make_png(2, 1, [bytes(16)], **kw))
                self.assertEqual(cm.exception.code, "png-unsupported")

    def test_a_picture_that_claims_to_be_enormous_is_refused_before_it_is_inflated(self):
        bomb = T.make_png(1, 1, [bytes(4)])
        head = bytearray(bomb)
        head[16:20] = (100000).to_bytes(4, "big")
        head[20:24] = (100000).to_bytes(4, "big")
        # fix the checksum so only the size is wrong
        head[29:33] = (zlib.crc32(bytes(head[12:29])) & 0xFFFFFFFF).to_bytes(4, "big")
        with self.assertRaises(Refusal) as cm:
            _png.decode(bytes(head))
        self.assertEqual(cm.exception.code, "png-too-large")

    def test_a_row_that_stops_short_is_refused(self):
        raw = zlib.compress(b"\x00" + bytes(16) * 2)  # two rows, not four
        data = b"\x89PNG\r\n\x1a\n" + T._chunk(b"IHDR", bytes([0, 0, 0, 4, 0, 0, 0, 4, 8, 6, 0, 0, 0])) + T._chunk(b"IDAT", raw) + T._chunk(b"IEND", b"")
        with self.assertRaises(Refusal) as cm:
            _png.decode(data)
        self.assertEqual(cm.exception.code, "png-bad")


class Looking(unittest.TestCase):
    def picture(self):
        # 4 x 4: left half opaque red, right half transparent, one half-see-through blue pixel
        rows = []
        for y in range(4):
            row = bytes((255, 0, 0, 255)) * 2 + bytes((0, 0, 0, 0)) * 2
            rows.append(row)
        rows[0] = bytes((255, 0, 0, 255)) * 2 + bytes((0, 0, 255, 128)) + bytes((0, 0, 0, 0))
        return _png.decode(T.make_png(4, 4, rows))

    def test_count_of_a_colour_is_of_solid_pixels_not_antialiased_edges(self):
        d = self.picture()
        self.assertEqual(_png.count_colour(d, "#ff0000"), 8)
        self.assertEqual(_png.count_colour(d, "#0000ff"), 0, "a half see-through pixel is an edge, not the colour")
        self.assertEqual(_png.count_colour(d, "#fe0101", tolerance=4), 8)
        self.assertEqual(_png.count_colour(d, "#f00000", tolerance=4), 0)

    def test_blank_means_almost_nothing_visible(self):
        self.assertFalse(_png.is_blank(self.picture()))
        empty = _png.decode(T.make_png(8, 8, T.solid_rgba(8, 8, (0, 0, 0, 0))))
        self.assertTrue(_png.is_blank(empty))
        faint = _png.decode(T.make_png(8, 8, T.solid_rgba(8, 8, (0, 0, 0, 20))))
        self.assertTrue(_png.is_blank(faint), "a mark at alpha 20 is not a mark")
        three = [bytes((9, 9, 9, 255)) * 3 + bytes(4) * 5] + [bytes(32)] * 7
        self.assertTrue(_png.is_blank(_png.decode(T.make_png(8, 8, three))), "three pixels are not a mark")
        four = [bytes((9, 9, 9, 255)) * 4 + bytes(4) * 4] + [bytes(32)] * 7
        self.assertFalse(_png.is_blank(_png.decode(T.make_png(8, 8, four))))

    def test_opaque_means_every_pixel(self):
        self.assertTrue(_png.is_opaque(_png.decode(T.make_png(3, 3, T.solid_rgba(3, 3, (1, 2, 3, 255))))))
        rows = T.solid_rgba(3, 3, (1, 2, 3, 255))
        rows[1] = rows[1][:-1] + b"\xfe"
        self.assertFalse(_png.is_opaque(_png.decode(T.make_png(3, 3, rows))))

    def test_the_colour_at_a_point(self):
        self.assertEqual(_png.at(self.picture(), 0, 3), (255, 0, 0, 255))
        self.assertEqual(_png.at(self.picture(), 3, 3), (0, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()
