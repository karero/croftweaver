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

    def css(self, text, name="edited.css"):
        return self.write(text, name=name)

    def test_a_proposed_primary_waits_for_her_like_any_other_proposal(self):
        # it used to pass with exit 0, and the install then wrote a theme colour nobody had confirmed
        path = self.write(brand_md(primary="#000000 (proposed)"))
        code, out, err = run("palette", path)
        self.assertEqual((code, err), (3, ""), out)
        line = [l for l in out.splitlines() if "Primary" in l and "#000000" in l]
        self.assertTrue(line, out)
        self.assertIn("Brand table", line[0])
        self.assertIn("confirm", out.lower())
        data = json.loads(run("palette", path, "--json")[1])
        self.assertEqual((data["status"], data["exit"]), ("needs-confirmation", 3))
        self.assertEqual(data["proposed"], [{"theme": "brand", "row": "brand", "hex": "#000000"}])

    def test_a_dark_theme_proposed_as_a_whole_by_its_heading_waits_for_her(self):
        code, out, _ = run("palette", self.write(brand_md().replace("### Dark theme", "### Dark theme (proposed)")))
        self.assertEqual(code, 3, out)
        for label in ("Heading", "Background", "Surface (cards)"):
            self.assertIn("Dark theme, %s:" % label, out)
        self.assertNotIn("Light theme, ", out)

    def test_a_pair_that_fails_by_a_hair_is_not_printed_as_the_ratio_it_needed(self):
        # 4.499999999992 to 1: it fails, and the line read "is 4.5 to 1; text needs 4.5 to 1"
        code, out, _ = run("palette", self.write(brand_md(dark=dict(STARTER_DARK, bg="#060201", link="#2671e5"))))
        self.assertEqual(code, 1, out)
        line = [l for l in out.splitlines() if l.startswith("FAILS") and "Link #2671e5 on Background #060201" in l]
        self.assertEqual(len(line), 1, out)
        self.assertIn("is 4.49 to 1; text needs 4.5 to 1", line[0])

    def test_a_colour_name_beside_the_value_does_not_stand_in_for_it(self):
        # | Background | Beige | #595959 |: read as beige it said 30 of 30 pass; the page would be dark grey
        body = "\n".join("| %s | %s | %s |" % (l, "Beige" if k == "bg" else "Ours", "#595959" if k == "bg" else STARTER_LIGHT[k]) for k, l in LABELS)
        md = "### Light theme\n| Token | Name | Hex |\n|---|---|---|\n" + body + "\n\n### Dark theme\n" + table([(l, STARTER_DARK[k]) for k, l in LABELS])
        code, out, _ = run("palette", self.write(md))
        self.assertEqual(code, 1, out)
        self.assertIn("Background #595959", out)
        self.assertNotIn("#f5f5dc", out)

    def test_a_type_table_beside_the_palette_does_not_make_the_palette_incomplete(self):
        md = brand_md() + "\n## Typography\n| Style | Weight | Tracking |\n|---|---|---|\n| Heading | 700 | -0.02em |\n| Body | 400 | 0 |\n"
        code, out, _ = run("palette", self.write(md))
        self.assertEqual(code, 0, out)
        self.assertIn("30 of 30", out)
        self.assertNotIn("Could not read", out)

    def test_an_old_layout_accent_that_fails_in_the_dark_theme_says_where_it_came_from(self):
        old_light = {k: v for k, v in STARTER_LIGHT.items() if k != "accent"}
        old_dark = {k: v for k, v in STARTER_DARK.items() if k != "accent"}
        md = ("### Brand (fixed, theme-independent)\n| Token | Hex | Use |\n|---|---|---|\n| Primary | `#000000` | x |\n| Accent | `#2b50e0`%s | links |\n\n"
              "### Light theme\n" + table([(l, old_light[k]) for k, l in LABELS if k in old_light])
              + "\n### Dark theme\n" + table([(l, old_dark[k]) for k, l in LABELS if k in old_dark]))
        code, out, _ = run("palette", self.write(md % ""))
        self.assertEqual(code, 1, out)
        fails = [l for l in out.splitlines() if l.startswith("FAILS")]
        self.assertEqual(len(fails), 3, out)
        for line in fails:
            self.assertIn("FAILS dark: Accent #2b50e0", line)
            self.assertIn("taken from the Brand table's Accent; give the dark theme its own", line)
        # shown as a proposal, the same is said of it there
        code, out, _ = run("palette", self.write(md % " (proposed)", name="proposed.md"))
        shown = [l for l in out.splitlines() if l.startswith("  Dark theme, Accent: #2b50e0")]
        self.assertEqual(len(shown), 1, out)
        self.assertIn("taken from the Brand table's Accent; give the dark theme its own", shown[0])

    def test_rows_under_a_name_it_does_not_know_are_shown_so_a_missing_row_explains_itself(self):
        md = brand_md().replace("| Heading | `#16162a` |", "| Headings: | `#16162a` |").replace("| Surface (cards) | `#ffffff` |", "| Surface / cards | `#ffffff` |")
        path = self.write(md)
        code, out, _ = run("palette", path)
        self.assertEqual(code, 2, out)
        self.assertIn("Light theme: Heading, Surface (cards)", out, "the rows are missing, as before")
        self.assertIn("not used", out)
        self.assertIn("  Headings: (#16162a)", out)
        self.assertIn("  Surface / cards (#ffffff)", out)
        self.assertIn("Soft background", [l for l in out.splitlines() if l.startswith("The names it reads")][0])
        data = json.loads(run("palette", path, "--json")[1])
        self.assertEqual(data["unused_rows"], [{"label": "Headings:", "colours": ["#16162a"]}, {"label": "Surface / cards", "colours": ["#ffffff"]}])
        # a palette with no such row says nothing of the kind
        self.assertNotIn("not used", run("palette", self.write(brand_md(), name="plain.md"))[1])

    def test_a_stylesheet_that_starts_with_an_import_is_still_compared(self):
        # the light block went unread behind the @import, and the drift in it went unsaid
        path = self.write(brand_md(light=dict(STARTER_LIGHT, accent="#c0392b", link="#c0392b")))
        css = self.css('@import url("./fonts.css");\n' + T.read(os.path.join(self.dir, "global.css")))
        code, out, _ = run("palette", path, "--css", css)
        self.assertEqual(code, 0, out)
        self.assertIn("Light theme, Accent: BRAND.md says #c0392b, the stylesheet has #2b50e0", out)
        self.assertNotIn("Could not read the stylesheet", out)

    def test_a_block_the_stylesheet_lacks_is_said_and_so_is_a_value_in_it_that_cannot_be_read(self):
        whole = T.read(os.path.join(self.dir, "global.css"))
        no_dark = whole[:whole.index(':root[data-theme="dark"]')] + whole[whole.index("@media (prefers-color-scheme: dark)"):]
        path = self.write(brand_md())
        code, out, _ = run("palette", path, "--css", self.css(no_dark))
        said = [l for l in out.splitlines() if l.startswith("Could not read the stylesheet")]
        self.assertEqual(len(said), 1, out)
        self.assertIn('no :root[data-theme="dark"]', said[0])
        self.assertIn("dark theme", said[0])
        self.assertEqual(code, 0, "the palette itself passes; this command reads, it does not judge the stylesheet")
        code, out, _ = run("palette", path, "--css", self.css(whole.replace("--muted: #5a5a72;", "--muted: rgba(90, 90, 114, 0.8);", 1), name="alpha.css"))
        said = [l for l in out.splitlines() if l.startswith("Could not read the stylesheet")]
        self.assertEqual(len(said), 1, out)
        for part in ("--muted", ":root block", "see-through"):
            self.assertIn(part, said[0])
        data = json.loads(run("palette", path, "--css", self.css(no_dark), "--json")[1])
        self.assertEqual([(x["block"], x["variable"]) for x in data["stylesheet_problems"]], [("dark", None)])
        self.assertEqual(json.loads(run("palette", path, "--json")[1])["stylesheet_problems"], [])

    def test_a_stylesheet_whose_braces_do_not_pair_up_is_refused_in_plain_words(self):
        whole = T.read(os.path.join(self.dir, "global.css"))
        path = self.write(brand_md())
        before = snapshot(self.dir)
        for name, text in (("a } too many", whole.replace("--radius: 12px;", "--radius: 12px; }", 1)), ("cut short", whole[:whole.index("--bg-soft: #11132c;")])):
            with self.subTest(name=name):
                code, out, err = run("palette", path, "--css", self.css(text, name="broken.css"))
                self.assertEqual((code, err), (2, ""), out)
                self.assertIn("Cannot check the palette", out)
                self.assertIn("braces", out)
                self.assertIn("Nothing was written", out)
                os.remove(os.path.join(self.dir, "broken.css"))
        self.assertEqual(snapshot(self.dir), before)

    def test_a_variable_only_one_dark_block_has_is_named_as_a_disagreement(self):
        # scenario 29 as it happens: --surface dropped from the @media block alone
        whole = T.read(os.path.join(self.dir, "global.css"))
        at = whole.index("@media (prefers-color-scheme: dark)")
        code, out, _ = run("palette", self.write(brand_md()), "--css", self.css(whole[:at] + whole[at:].replace("    --surface: #161836;\n", "", 1)))
        self.assertIn("two dark", out.lower())
        self.assertIn("  Surface (cards): #161836 in one, no value in the other", out)
        # and a row the document has that the stylesheet's block lacks
        code, out, _ = run("palette", self.write(brand_md()), "--css", self.css(whole.replace("  --surface: #ffffff;\n", "", 1), name="light.css"))
        self.assertIn("Light theme, Surface (cards): BRAND.md says #ffffff, the stylesheet has no value", out)


if __name__ == "__main__":
    unittest.main()
