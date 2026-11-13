#!/usr/bin/env python3
"""Tests for the font choice in the starter's scripts/generate_og_cards.py (needs Pillow).

    python3 skills/new-website/scripts/tests/test_og_fonts.py

Why: with none of its fonts installed the generator once fell back to Pillow's default font,
which Pillow 12.2.0 draws ä, ö, ü, ß and — with as empty boxes, on cards that passed --check.
It must stop instead, before it writes a card, and name the files it looked for. Every run here
works on a copy of the generator in a temporary folder, so no card in the repo is touched.
OG_FONTS_REQUIRE_FONT=1 (CI) turns the one skip, "no font on this machine", into a failure.
"""
import contextlib, importlib.util, io, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

GENERATOR = Path(__file__).resolve().parents[2] / "templates/astro/scripts/generate_og_cards.py"

# The script run as `npm run og` runs it (as __main__), with every font file reported missing.
NO_FONTS_RUN = """
import pathlib, runpy, sys
real = pathlib.Path.exists
pathlib.Path.exists = lambda p: False if str(p).lower().endswith((".ttf", ".ttc")) else real(p)
sys.argv = [sys.argv[1], "--check"]
runpy.run_path(sys.argv[0], run_name="__main__")
"""


def site_copy(d: Path) -> Path:
    """The generator in a throwaway site folder: its ROOT, and so its OUT, is `d`."""
    (d / "scripts").mkdir()
    return Path(shutil.copy(GENERATOR, d / "scripts"))


def load(path: Path):
    spec = importlib.util.spec_from_file_location("generate_og_cards", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def exit_message(call):
    """What `call` passes to sys.exit; None if it returns or fails another way."""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            call()
    except SystemExit as e:
        return str(e.code)
    except Exception:
        return None
    return None


class NoFont(unittest.TestCase):
    def test_the_run_stops_names_every_file_and_writes_no_card(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            script = site_copy(d)
            r = subprocess.run([sys.executable, "-c", NO_FONTS_RUN, str(script)],
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("none of the fonts this script knows is installed", r.stderr)
            # The brand-kit installer reports only the last line, so it must say what to do on its own.
            last = r.stderr.strip().splitlines()[-1]
            self.assertTrue(last.startswith("No font for the share cards: install "), last)
            for reg, _, bold, _ in load(script)._FONT_CANDIDATES:
                self.assertIn(reg, r.stderr)
                self.assertIn(bold, r.stderr)
            self.assertFalse((d / "public").exists(), "a card was written before the stop")

    def test_font_stops_rather_than_return_a_default(self):
        with tempfile.TemporaryDirectory() as d:
            og = load(site_copy(Path(d)))
            og._REG = og._BOLD = None
            msg = exit_message(lambda: og.font(True, 40))
            self.assertIsNotNone(msg, "font() returned a font with nothing installed")
            self.assertIn("none of the fonts", msg)


class Resolver(unittest.TestCase):
    def test_the_first_pair_with_both_files_wins(self):
        with tempfile.TemporaryDirectory() as d:
            og = load(site_copy(Path(d)))
            f = {n: str(Path(d) / n) for n in ("a-reg", "a-bold", "b-reg", "b-bold", "c-reg")}
            for n in ("b-reg", "b-bold", "c-reg"):
                Path(f[n]).write_bytes(b"")
            og._FONT_CANDIDATES = [(f["a-reg"], 0, f["a-bold"], 1), (f["b-reg"], 0, f["b-bold"], 2)]
            self.assertEqual(og._resolve_fonts(), ((f["b-reg"], 0), (f["b-bold"], 2)))
            og._FONT_CANDIDATES = [(f["c-reg"], 0, f["a-bold"], 0)]
            self.assertEqual(og._resolve_fonts(), (None, None), "a regular file with no bold is no pair")


class WithAFont(unittest.TestCase):
    def test_a_run_says_which_font_it_used(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            og = load(site_copy(d))
            if og._REG is None:
                if os.environ.get("OG_FONTS_REQUIRE_FONT") == "1":
                    self.fail("no font of the generator's list is installed here")
                self.skipTest("no font of the generator's list is installed here")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                og.main()
            self.assertIn(f"  font: {og._REG[0]}", out.getvalue())
            self.assertTrue((d / "public/images/og/default.jpg").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
