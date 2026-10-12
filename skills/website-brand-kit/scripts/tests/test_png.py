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

    def picture_data(self, cut=0, extra=b""):
        # a 2 x 2 picture whose compressed data loses its last `cut` bytes, or gains `extra` ones
        raw = b"".join(b"\x00" + bytes((1, 2, 3, 255)) * 2 for _ in range(2))
        packed = zlib.compress(raw)
        packed = packed[:len(packed) - cut] + extra
        return (b"\x89PNG\r\n\x1a\n" + T._chunk(b"IHDR", bytes([0, 0, 0, 2, 0, 0, 0, 2, 8, 6, 0, 0, 0])) + T._chunk(b"IDAT", packed)
                + T._chunk(b"IEND", b""))

    def test_one_colour_named_as_see_through_in_a_grey_or_rgb_picture_is_refused_not_read_as_solid(self):
        # a tRNS chunk beside colour type 0 or 2 makes every pixel of that one colour transparent; read
        # without it, a picture with holes in it would pass for fully opaque
        for name, data in (("rgb", T.make_png(2, 1, [bytes([1, 2, 3, 4, 5, 6])], colour_type=2, trns=[0, 1, 0, 2, 0, 3])),
                           ("grey", T.make_png(2, 1, [bytes([9, 200])], colour_type=0, trns=[0, 9])),
                           ("grey, a colour the picture does not use", T.make_png(2, 1, [bytes([9, 200])], colour_type=0, trns=[0, 77]))):
            with self.subTest(name=name):
                with self.assertRaises(Refusal) as cm:
                    _png.decode(data)
                self.assertEqual(cm.exception.code, "png-unsupported")
                self.assertIn("see-through", str(cm.exception))
        # the same chunk beside a palette is how a palette picture carries its alpha, and is read
        pal = _png.decode(T.make_png(1, 1, [bytes([0])], colour_type=3, palette=[(255, 0, 0)], trns=[128]))
        self.assertEqual(pixel(pal, 0, 0), (255, 0, 0, 128))

    def test_picture_data_cut_off_before_its_own_checksum_is_refused(self):
        # every pixel is there, so the length is right; only the end of the compressed stream is missing
        self.assertEqual(_png.decode(self.picture_data())[:2], (2, 2))
        for cut in (1, 2, 3, 4):
            with self.subTest(cut=cut):
                with self.assertRaises(Refusal) as cm:
                    _png.decode(self.picture_data(cut=cut))
                self.assertEqual(cm.exception.code, "png-bad")
                self.assertIn("cut short", str(cm.exception))

    def test_bytes_after_the_end_of_the_picture_data_are_refused(self):
        for extra in (b"\x00", b"junk", zlib.compress(b"a second stream")):
            with self.subTest(extra=extra):
                with self.assertRaises(Refusal) as cm:
                    _png.decode(self.picture_data(extra=extra))
                self.assertEqual(cm.exception.code, "png-bad")

    def test_a_header_that_is_not_the_first_chunk_is_refused_by_decode_as_it_is_by_size(self):
        good = T.make_png(2, 2, T.solid_rgba(2, 2, (1, 2, 3, 255)))
        for name, first in (("text", T._chunk(b"tEXt", b"a\x00b")), ("data", T._chunk(b"IDAT", zlib.compress(b"\x00" * 18))),
                            ("end", T._chunk(b"IEND", b""))):
            with self.subTest(first=name):
                late = good[:8] + first + good[8:]
                for read in (_png.decode, _png.size):
                    with self.assertRaises(Refusal) as cm:
                        read(late)
                    self.assertEqual(cm.exception.code, "png-bad")
                    self.assertIn("no header", str(cm.exception))

    def test_a_picture_of_no_width_or_no_height_is_said_to_be_that_not_far_too_large(self):
        for w, h in ((0, 2), (2, 0), (0, 0)):
            with self.subTest(w=w, h=h):
                data = (b"\x89PNG\r\n\x1a\n" + T._chunk(b"IHDR", bytes([0, 0, 0, w, 0, 0, 0, h, 8, 6, 0, 0, 0]))
                        + T._chunk(b"IDAT", zlib.compress(b"")) + T._chunk(b"IEND", b""))
                with self.assertRaises(Refusal) as cm:
                    _png.decode(data)
                self.assertEqual(cm.exception.code, "png-bad")
                self.assertIn("no width or no height", str(cm.exception))
                self.assertNotIn("larger", str(cm.exception))


class Encoding(unittest.TestCase):
    def test_what_is_encoded_decodes_to_the_same_picture(self):
        import random
        rnd = random.Random(3)
        rgba = bytes(rnd.randrange(256) for _ in range(5 * 3 * 4))
        data = _png.encode(5, 3, rgba)
        self.assertEqual(_png.decode(data), (5, 3, rgba))
        self.assertEqual(_png.size(data), (5, 3))

    def test_a_wrong_length_is_refused_not_padded(self):
        for n in (0, 59, 61):
            with self.assertRaises(ValueError):
                _png.encode(5, 3, bytes(n))


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

    def test_a_pixel_counts_as_there_from_a_quarter_solid_as_the_docstring_says(self):
        # pins the line the docstring names (it said "half", the number was always a quarter: 64 of 255)
        for alpha, blank in ((63, True), (64, False), (127, False)):
            with self.subTest(alpha=alpha):
                self.assertEqual(_png.is_blank(_png.decode(T.make_png(8, 8, T.solid_rgba(8, 8, (0, 0, 0, alpha))))), blank)
        self.assertIn("a quarter there", _png.is_blank.__doc__)

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
