"""Scenarios 7 and 9 through the door the assistant uses: `brand_intake.py palette`.

The check is read-only, runs at step 2b (before any project exists) and again in the intake before
anything is written. These tests run the real script as a program, on files in a folder, and look at
what it prints, its exit status, and that every file in the folder is byte for byte what it was.
Exit status: 0 every pair passes, 1 a pair fails, 2 it cannot judge (a row is missing or unreadable),
3 only the owner's confirmation of proposed values is outstanding.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

import _testutil as T
from test_palette import LABELS, STARTER_DARK, STARTER_LIGHT, brand_md, table

SCRIPT = os.path.join(T.SCRIPTS, "brand_intake.py")


def run(*args, cwd=None, stdin=None):
    r = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True, cwd=cwd, input=stdin,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8"))
    return r.returncode, r.stdout, r.stderr


def snapshot(folder):
    out = {}
    for base, _dirs, files in os.walk(folder):
        for f in files:
            p = os.path.join(base, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, folder)] = hashlib.sha256(fh.read()).hexdigest()
    return out


class PaletteCommand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        with open(os.path.join(self.dir, "global.css"), "w", encoding="utf-8") as f:
            f.write(T.starter_file("src/styles/global.css"))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, text, name="BRAND.md"):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_a_palette_that_passes_everywhere(self):
        path = self.write(brand_md())
        before = snapshot(self.dir)
        code, out, err = run("palette", path)
        self.assertEqual((code, err), (0, ""), out)
        self.assertIn("30 of 30", out)
        self.assertEqual(snapshot(self.dir), before)

    def test_scenario_7_a_failing_pair_is_named_and_nothing_is_written(self):
        path = self.write(brand_md(dark=dict(STARTER_DARK, muted="#5c5f80")))
        before = snapshot(self.dir)
        code, out, err = run("palette", path, "--css", os.path.join(self.dir, "global.css"))
        self.assertEqual(code, 1, out + err)
        fails = [l for l in out.splitlines() if l.startswith("FAILS")]
        self.assertTrue(fails, out)
        line = [l for l in fails if "Background #0a0b1e" in l][0]
        for part in ("dark", "Muted #5c5f80", "Background #0a0b1e", "3.15 to 1", "4.5 to 1"):
            self.assertIn(part, line)
        self.assertIn("nothing was written", out.lower())
        self.assertEqual(snapshot(self.dir), before, "the check must leave BRAND.md and global.css alone")

    def test_every_failing_pair_is_listed_not_just_the_first(self):
        path = self.write(brand_md(dark=dict(STARTER_DARK, muted="#5c5f80"), light=dict(STARTER_LIGHT, link="#8a9bd6", accent="#8a9bd6")))
        code, out, _ = run("palette", path)
        self.assertEqual(code, 1)
        n = sum(1 for l in out.splitlines() if l.startswith("FAILS"))
        self.assertGreaterEqual(n, 3 + 6)
        self.assertIn("%d of 30" % (30 - n), out)

    def test_scenario_9_no_dark_theme_is_incomplete_and_says_which_rows(self):
        path = self.write(brand_md(dark={}))
        code, out, _ = run("palette", path)
        self.assertEqual(code, 2, out)
        self.assertIn("Dark theme", out)
        for label in ("Link", "Soft background", "Surface (cards)"):
            self.assertIn(label, out)
        self.assertIn("propose", out.lower())  # what happens next: the assistant proposes values, she confirms

    def test_a_row_the_old_layout_lacks_is_named(self):
        light = {k: v for k, v in STARTER_LIGHT.items() if k not in ("link", "bg_soft")}
        code, out, _ = run("palette", self.write(brand_md(light=light)))
        self.assertEqual(code, 2)
        self.assertIn("Light theme", out)
        self.assertIn("Soft background", out)
        self.assertNotIn("Dark theme: ", out)

    def test_a_pair_that_fails_is_reported_even_when_a_row_is_also_missing(self):
        light = {k: v for k, v in STARTER_LIGHT.items() if k != "link"}
        code, out, _ = run("palette", self.write(brand_md(light=light, dark=dict(STARTER_DARK, muted="#5c5f80"))))
        self.assertEqual(code, 1)
        self.assertIn("FAILS dark", out)
        self.assertIn("Link", out)

    def test_proposed_values_are_shown_with_their_ratios_and_wait_for_her(self):
        dark = dict(STARTER_DARK, muted="#a6abce (proposed)", link="#9fb0ff (proposed)")
        code, out, _ = run("palette", self.write(brand_md(dark=dark)))
        self.assertEqual(code, 3, out)
        self.assertIn("#a6abce", out)
        self.assertIn("confirm", out.lower())
        self.assertIn("proposed", out.lower())
        # once she has confirmed them the marker goes and the same palette passes
        self.assertEqual(run("palette", self.write(brand_md(), name="confirmed.md"))[0], 0)

    def test_a_proposal_that_fails_is_still_a_failure(self):
        code, out, _ = run("palette", self.write(brand_md(dark=dict(STARTER_DARK, muted="#5c5f80 (proposed)"))))
        self.assertEqual(code, 1)
        self.assertIn("FAILS dark", out)

    def test_colours_in_other_formats_are_checked_as_their_hex(self):
        dark = dict(STARTER_DARK, muted="hsl(232 25% 40%)")  # a dim grey-blue on a near-black page
        code, out, _ = run("palette", self.write(brand_md(dark=dark)))
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"Muted #[0-9a-f]{6}")

    def test_two_palettes_pasted_together_are_refused_in_plain_words(self):
        other = dict(STARTER_LIGHT, accent="#c0392b")
        pasted = brand_md() + "\n### Light theme\n" + table([(l, other[k]) for k, l in LABELS])
        code, out, _ = run("palette", self.write(pasted))
        self.assertEqual(code, 2, out)
        self.assertIn("pasted together", out)

    def test_drift_between_the_document_and_the_stylesheet_is_named_but_does_not_block(self):
        path = self.write(brand_md(light=dict(STARTER_LIGHT, accent="#c0392b", link="#c0392b")))
        code, out, _ = run("palette", path, "--css", os.path.join(self.dir, "global.css"))
        self.assertEqual(code, 0, out)
        self.assertIn("stylesheet", out)
        self.assertIn("Accent", out)

    def test_the_two_dark_blocks_disagreeing_is_named(self):
        css = os.path.join(self.dir, "global.css")
        text = T.read(css).replace("--bg: #0a0b1e;\n    --bg-soft", "--bg: #000000;\n    --bg-soft")
        with open(css, "w", encoding="utf-8") as f:
            f.write(text)
        code, out, _ = run("palette", self.write(brand_md()), "--css", css)
        self.assertIn("two dark", out.lower())
        self.assertIn("Background", out)

    def test_json_for_the_assistant(self):
        code, out, _ = run("palette", self.write(brand_md(dark=dict(STARTER_DARK, muted="#5c5f80"))), "--json")
        data = json.loads(out)
        self.assertEqual(data["status"], "fail")
        self.assertEqual(data["exit"], code)
        self.assertEqual(len(data["pairs"]), 30)
        bad = [p for p in data["pairs"] if not p["ok"]]
        self.assertTrue(bad)
        self.assertEqual({"theme", "fg", "bg", "fg_hex", "bg_hex", "ratio", "need", "ok"}, set(bad[0]))
        self.assertEqual(json.loads(run("palette", self.write(brand_md(dark={}), name="b.md"), "--json")[1])["status"], "incomplete")

    def test_a_palette_from_standard_input(self):
        code, out, _ = run("palette", "-", stdin=brand_md())
        self.assertEqual(code, 0, out)

    def test_an_unreadable_primary_colour_is_named_and_stops_short_of_a_pass(self):
        code, out, _ = run("palette", self.write(brand_md(primary="rgba(0, 0, 0, 0.5)")))
        self.assertEqual(code, 2, out)
        self.assertIn("see-through", out)
        self.assertIn("Primary", out)

    def test_a_palette_far_bigger_than_any_palette_is_refused(self):
        code, out, _ = run("palette", self.write(brand_md() + "x" * (1024 * 1024)))
        self.assertEqual(code, 2)
        self.assertIn("larger than", out)
        self.assertIn("Nothing was written", out)

    def test_a_file_that_is_not_there_or_not_text(self):
        code, out, err = run("palette", os.path.join(self.dir, "nope.md"))
        self.assertEqual(code, 2)
        self.assertIn("nope.md", out + err)
        binary = os.path.join(self.dir, "x.bin")
        with open(binary, "wb") as f:
            f.write(b"\xff\xfe\x00\x01" * 100)
        self.assertEqual(run("palette", binary)[0], 2)

    def test_the_template_as_shipped_says_nothing_is_filled_in_yet(self):
        code, out, _ = run("palette", T.BRAND_TEMPLATE)
        self.assertEqual(code, 2)
        self.assertIn("not filled in", out)


if __name__ == "__main__":
    unittest.main()
