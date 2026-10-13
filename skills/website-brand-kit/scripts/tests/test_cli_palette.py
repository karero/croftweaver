"""Scenarios 7 and 9 through the door the assistant uses: `brand_intake.py palette`.

The check is read-only, runs at step 2b (before any project exists) and again in the intake before
anything is written. These tests run the real script as a program, on files in a folder, and look at
what it prints, its exit status, and that every file in the folder is byte for byte what it was.
Exit status: 0 every pair passes, 1 a pair fails, 2 it cannot judge (a row is missing or unreadable,
something was not read, the stylesheet given with --css holds something it could not take as it stands, or
its two dark blocks disagree),
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
import _palette
from test_palette import EVALS, HEAD, LABELS, STARTER_DARK, STARTER_LIGHT, brand_md, filled_guide, pasted, plain, table

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
        # round 4: it ended "pass", with 0, while it printed that the two blocks must carry the same values
        self.assertEqual(code, 2, out)
        data = json.loads(run("palette", self.write(brand_md()), "--css", css, "--json")[1])
        self.assertEqual((data["status"], data["exit"], data["dark_blocks_disagree"]), ("incomplete", 2, [{"row": "bg", "dark_block": "#0a0b1e", "media_block": "#000000"}]))
        # a failing pair and a proposal are still said first, and a document that only differs from the stylesheet still ends with 0 (the test above)
        self.assertEqual(run("palette", self.write(brand_md(dark=dict(STARTER_DARK, muted="#5c5f80")), name="bad.md"), "--css", css)[0], 1)
        self.assertEqual(run("palette", self.write(brand_md(dark=dict(STARTER_DARK, muted="#a6abce (proposed)")), name="proposed.md"), "--css", css)[0], 2)
        self.assertEqual(run("palette", self.write(brand_md(dark=dict(STARTER_DARK, bg="#000000")), name="other.md"), "--css", os.path.join(self.dir, "global.css"))[0], 2,
                         "the document agrees with one of the two blocks: the blocks still disagree")

    def test_json_for_the_assistant(self):
        code, out, _ = run("palette", self.write(brand_md(dark=dict(STARTER_DARK, muted="#5c5f80"))), "--json")
        data = json.loads(out)
        self.assertEqual(data["status"], "fail")
        self.assertEqual(data["exit"], code)
        self.assertEqual(len(data["pairs"]), 30)
        bad = [p for p in data["pairs"] if not p["ok"]]
        self.assertTrue(bad)
        self.assertEqual({"theme", "fg", "bg", "fg_hex", "bg_hex", "ratio", "need", "ok", "note"}, set(bad[0]))
        self.assertEqual(json.loads(run("palette", self.write(brand_md(dark={}), name="b.md"), "--json")[1])["status"], "incomplete")

    def test_json_carries_every_value_as_it_was_read_also_the_ones_no_pair_shows(self):
        # the Primary and the Hairline stand in no pair: whoever reads the JSON could not compare them with the file
        light = dict(STARTER_LIGHT, line="rgb(227, 231, 242)")
        data = json.loads(run("palette", self.write(brand_md(light=light, primary="#B4531A")), "--json")[1])
        self.assertEqual(data["values"], {"brand": {"brand": "#b4531a"}, "light": STARTER_LIGHT, "dark": STARTER_DARK})
        self.assertEqual((data["values"]["light"]["line"], data["form"]), ("#e3e7f2", ""))
        data = json.loads(run("palette", T.BRAND_TEMPLATE, "--json")[1])
        self.assertEqual(data["values"], {"brand": {}, "light": {}, "dark": {}})

    def test_json_says_of_a_pair_that_its_accent_came_from_the_brand_table(self):
        # the printed line said so; the JSON gave the same failing pair without the reason
        old_light = {k: v for k, v in STARTER_LIGHT.items() if k != "accent"}
        old_dark = {k: v for k, v in STARTER_DARK.items() if k != "accent"}
        md = ("### Brand (fixed, theme-independent)\n| Token | Hex | Use |\n|---|---|---|\n| Primary | `#000000` | x |\n| Accent | `#2b50e0` | links |\n\n"
              "### Light theme\n" + table([(l, old_light[k]) for k, l in LABELS if k in old_light])
              + "\n### Dark theme\n" + table([(l, old_dark[k]) for k, l in LABELS if k in old_dark]))
        data = json.loads(run("palette", self.write(md), "--json")[1])
        bad = [p for p in data["pairs"] if not p["ok"]]
        self.assertEqual({(p["theme"], p["fg"]) for p in bad}, {("dark", "accent")})
        for p in data["pairs"]:
            want = "taken from the Brand table's Accent; give the %s theme its own" % p["theme"] if p["fg"] == "accent" else ""
            self.assertEqual(p["note"], want)
        self.assertTrue(all(p["note"] == "" for p in json.loads(run("palette", self.write(brand_md(), name="own.md"), "--json")[1])["pairs"]))

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
        # | Background | Beige | #595959 |: read as beige it said 30 of 30 pass; the page would be dark grey. With the hex
        # left without its #, or see-through, the name was taken again. A column of names is now not read at all.
        for hex_cell in ("#595959", "595959", "#595959cc"):
            with self.subTest(hex_cell=hex_cell):
                body = "\n".join("| %s | %s | %s |" % (l, "Beige" if k == "bg" else "Ours", hex_cell if k == "bg" else STARTER_LIGHT[k]) for k, l in LABELS)
                md = "### Light theme\n| Token | Name | Hex |\n|---|---|---|\n" + body + "\n\n### Dark theme\n" + table([(l, STARTER_DARK[k]) for k, l in LABELS])
                code, out, _ = run("palette", self.write(md))
                self.assertEqual(code, 2, out)
                self.assertIn("15 of 15 pairs pass", out, "the dark theme's; no pair of the light theme is made up")
                self.assertNotIn("#f5f5dc", out)
                said = [l for l in out.splitlines() if l.startswith("Not read: The table")]
                self.assertEqual(len(said), 1, out)
                for part in ("under `### Light theme`", 'calls its second column "Name"', '"Hex"'):
                    self.assertIn(part, said[0])
                self.assertIn("  Light theme: Heading, Body (ink), Muted, Accent, Link, Hairline, Background, Soft background, Surface (cards)", out)

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

    def test_rows_under_a_name_it_does_not_know_are_named_with_their_lines_so_a_missing_row_explains_itself(self):
        md = brand_md().replace("| Heading | `#16162a` |", "| Headings: | `#16162a` |").replace("| Surface (cards) | `#ffffff` |", "| Surface / cards | `#ffffff` |")
        path = self.write(md)
        code, out, _ = run("palette", path)
        self.assertEqual(code, 2, out)
        self.assertIn("  Light theme: Heading, Surface (cards)", out, "the rows are missing, as before")
        said = [l for l in out.splitlines() if l.startswith("Not read: ")]
        self.assertEqual(len(said), 2, out)
        self.assertIn('Not read: Line 13, "| Headings: | `#16162a` |", holds a colour (#16162a) that was not read.', said[0])
        self.assertIn("the names are Primary under `### Brand`, and Heading, Body (ink), Muted, Accent, Link, Hairline, Background, Soft background, Surface (cards) under the two themes", said[0])
        self.assertIn('Not read: Line 21, "| Surface / cards | `#ffffff` |", holds a colour (#ffffff) that was not read either', said[1])
        data = json.loads(run("palette", path, "--json")[1])
        self.assertEqual([(x["theme"], x["row"], x["code"]) for x in data["problems"]], [("?", None, "palette-colour-not-read")] * 2)
        self.assertNotIn("unused_rows", data, "said once, as a problem")
        # a palette with no such row says nothing of the kind
        self.assertNotIn("Not read", run("palette", self.write(brand_md(), name="plain.md"))[1])

    # --- what the review of the rebuilt reader found (round 3) --------------------------------------

    def test_rows_are_called_not_filled_in_only_where_nothing_was_left_unread(self):
        # reversed columns under the light heading: its rows were printed as "not filled in" with the offer to propose values
        offer, mend = "The assistant can propose values for them", "First mend what is named below"
        reversed_ = brand_md(light={}).replace("### Light theme\n" + HEAD, "### Light theme\n| Hex | Token |\n|---|---|\n| `#16162a` | Heading |\n| #5a5a72 | Muted |\n")
        cases = (("columns the wrong way round", reversed_, 2), ("a list under the heading", brand_md(light={}) + "\n### Light theme\n- Heading: #16162a\n- Muted: #5a5a72\n", 2),
                 ("a value that could not be read", brand_md(light=dict(STARTER_LIGHT, muted="rgba(90, 90, 114, 0.9)")), 0),
                 ("a table under a label", brand_md(light={}) + "\n**Light theme**\n" + plain(STARTER_LIGHT), 1),
                 ("the word where it is not read as a mark", brand_md(dark={}) + "\nThe dark theme is still a proposal.\n", 1))
        for name, md, not_read in cases:
            with self.subTest(name=name):
                code, out, _ = run("palette", self.write(md))
                self.assertEqual(code, 2, out)
                self.assertIn("These rows have no value that this check could use:", out)
                self.assertIn(mend, out)
                self.assertNotIn("not filled in:", out)
                self.assertNotIn(offer, out, "a value that was not read is not one to propose anew")
                self.assertEqual(len([l for l in out.splitlines() if l.startswith("Not read: ")]), not_read, out)
                self.assertLess(out.index(mend), out.index("Not read: " if not_read else "Could not read a value: "), "the sentence points down at what it names")
        # the other side: rows that are only missing are not filled in, and values can be proposed for them
        for name, md in (("no dark theme", brand_md(dark={})), ("the template", T.read(T.BRAND_TEMPLATE)), ("two rows", T.read(os.path.join(EVALS, "own-colours.md")))):
            with self.subTest(name=name):
                code, out, _ = run("palette", self.write(md))
                self.assertEqual(code, 2, out)
                self.assertIn("These rows are not filled in:", out)
                self.assertIn(offer, out)
                self.assertNotIn(mend, out)

    def test_the_word_proposed_outside_a_mark_never_ends_in_a_pass(self):
        # each of these ended with 0: the dark values went in as confirmed. (A pasted answer: all of it is the palette.)
        full = pasted()
        for name, md in (("the plural in the heading's brackets", full.replace("### Dark theme", "### Dark theme (proposals)")),
                         ("a sentence under the heading above", "## Colours\n\nThe dark values below are proposed; the owner has not confirmed them.\n\n" + full),
                         ("a sentence before the first heading", "Here are three proposed palettes.\n\n" + full), ("a heading beside the three", "### Proposed dark values\n" + full),
                         ("a row under another name", full.replace("### Dark theme\n| Token | Hex |\n|---|---|\n", "### Dark theme\n| Token | Hex |\n|---|---|\n| Status | proposed |\n")),
                         ("a mark beside a placeholder", full + "| Muted | #[…] | proposed |\n"), ("a closing sentence", full + "\nTell me if I should change any of the proposed colours.\n")):
            with self.subTest(name=name):
                code, out, _ = run("palette", self.write(md))
                self.assertIn(code, (2, 3), out)
                self.assertEqual(code == 3, "(proposals)" in md, "only the heading's own mark makes them proposals; everywhere else the word is named")
                self.assertIn("30 of 30", out)
                if code == 2:
                    self.assertTrue([l for l in out.splitlines() if l.startswith(("Not read: Line", "Could not read a value: Muted (dark theme): the row is marked as a proposal"))], out)
        # inside a comment the word is not looked at, as the assistant's own notes may hold it
        self.assertEqual(run("palette", self.write("<!-- colours proposed on 3 October, confirmed on the 5th -->\n" + full))[0], 0)

    def test_a_brand_guide_filled_in_as_its_template_asks_passes_and_its_palette_in_the_wrong_place_does_not(self):
        # the shadow's rgba(), the share cards' colours and "proposed" in the logo's history are no business of the palette's
        guide = filled_guide()
        for needle in ("rgba(58, 29, 10, 0.06)", "#2a1f17 at the top", "was proposed by the studio", "## Colour palette"):
            self.assertIn(needle, guide)
        path = self.write(guide)
        before = snapshot(self.dir)
        code, out, err = run("palette", path)
        self.assertEqual((code, err), (0, ""), out)
        self.assertEqual(out.splitlines()[1:], ["30 of 30 pairs pass.", "This check only reads files: nothing was written."])
        data = json.loads(run("palette", path, "--json")[1])
        self.assertEqual((data["status"], data["problems"], data["missing"], data["proposed"]), ("pass", [], [], []))
        self.assertEqual(snapshot(self.dir), before)
        # the three tables moved under another heading of the guide: named, never "no palette here" without a word
        start, end = guide.index("### Brand (fixed"), guide.index("## Typography")
        code, out, _ = run("palette", self.write(guide[:start] + guide[end:] + "\n## Appendix\n\n" + guide[start:end], name="moved.md"))
        self.assertEqual(code, 2, out)
        said = [l for l in out.splitlines() if l.startswith("Not read: Line ")]
        self.assertEqual(len(said), 3, out)
        self.assertIn('the heading "### Brand (fixed, theme-independent)", has a table under it and stands outside the part of this text that the check reads', said[0])
        self.assertIn('the part under the heading "## Colour palette"', said[0])
        self.assertIn("No row of a palette was found where this check looks for one.", out)
        # the heading twice: nothing is read, and that is said
        code, out, _ = run("palette", self.write(guide + "\n## Colour palette\n", name="twice.md"))
        self.assertEqual(code, 2, out)
        self.assertIn('Not read: The heading "## Colour palette" stands 2 times in this text', out)
        self.assertIn("No pair could be checked.", out)

    def test_a_pasted_answer_with_its_own_palette_heading_is_read_like_a_guide(self):
        # the sentence above the heading stands outside the section and is not named; the values carry no mark and are read.
        # Intended (rule 0). With no such heading the same sentence stops the check, and so does a mark inside the section.
        tables = pasted()
        self.assertEqual(run("palette", "-", stdin="Here are three proposed palettes.\n\n## Colour palette\n\n" + tables)[0], 0)
        self.assertEqual(run("palette", "-", stdin="Here are three proposed palettes.\n\n" + tables)[0], 2)
        self.assertEqual(run("palette", "-", stdin="## Colour palette\n\nHere are three proposed palettes.\n\n" + tables)[0], 2)
        self.assertEqual(run("palette", "-", stdin="Here you are.\n\n## Colour palette\n\n" + tables.replace("### Dark theme", "### Dark theme (proposed)"))[0], 3)

    def test_a_file_that_starts_with_a_byte_order_mark_is_read_from_its_first_line(self):
        md = brand_md().partition("### Brand")
        code, out, _ = run("palette", self.write("\ufeff" + md[1] + md[2]))
        self.assertEqual(code, 0, out)
        self.assertIn("30 of 30", out)
        self.assertNotIn("Note: ", out, "the Primary under the first heading is read")

    def test_a_palette_without_a_primary_says_what_the_install_does_about_it(self):
        # it passed with not a word, and the install then used the accent as the theme colour
        note = "Note: the palette gives no Primary, so the install uses the light theme's Accent as the theme colour."
        path = self.write(brand_md().partition("### Light theme")[1] + brand_md().partition("### Light theme")[2])
        code, out, _ = run("palette", path)
        self.assertEqual(code, 0, out)
        self.assertIn(note, out.splitlines())
        self.assertEqual(json.loads(run("palette", path, "--json")[1])["notes"], [note[6:-1]])
        # with a Primary there is no such line, and neither where there is no Accent to use
        self.assertNotIn("Note: ", run("palette", self.write(brand_md(), name="full.md"))[1])
        self.assertEqual(json.loads(run("palette", self.write(brand_md(), name="full.md"), "--json")[1])["notes"], [])
        self.assertNotIn("Note: ", run("palette", T.BRAND_TEMPLATE)[1])

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
        # (it ended with 0, "pass", on a stylesheet it had not read in full)
        self.assertEqual(code, 2, "the palette passes, and the comparison with the stylesheet could not be made in full")
        self.assertIn("30 of 30", out)
        code, out, _ = run("palette", path, "--css", self.css(whole.replace("--muted: #5a5a72;", "--muted: rgba(90, 90, 114, 0.8);", 1), name="alpha.css"))
        said = [l for l in out.splitlines() if l.startswith("Could not read the stylesheet")]
        self.assertEqual(len(said), 1, out)
        for part in ("--muted", ":root block", "see-through"):
            self.assertIn(part, said[0])
        data = json.loads(run("palette", path, "--css", self.css(no_dark), "--json")[1])
        self.assertEqual([(x["block"], x["variable"]) for x in data["stylesheet_problems"]], [("dark", None)])
        self.assertEqual((data["status"], data["exit"]), ("incomplete", 2))
        data = json.loads(run("palette", path, "--json")[1])
        self.assertEqual((data["stylesheet_problems"], data["status"], data["exit"]), ([], "pass", 0), "without --css the stylesheet is not looked at")
        # a failing pair is still the first thing said: 1, not 2
        bad = self.write(brand_md(dark=dict(STARTER_DARK, muted="#5c5f80")), name="bad.md")
        self.assertEqual(run("palette", bad, "--css", os.path.join(self.dir, "edited.css"))[0], 1)

    def test_a_stylesheet_whose_braces_do_not_pair_up_is_refused_in_plain_words(self):
        whole = T.read(os.path.join(self.dir, "global.css"))
        path = self.write(brand_md())
        before = snapshot(self.dir)
        for name, text in (("a } too many", whole.replace("--radius: 12px;", "--radius: 12px; }", 1)), ("cut short", whole[:whole.index("--bg-soft: #11132c;")]),
                           # round 4: a value's own brackets count too (a browser reads on from `rgb(1,2;` to the end of the stylesheet)
                           ("a ( never closed in a value", whole.replace("--bg: #ffffff;", "--bg: rgb(1,2; --other: 3px;", 1)), ("a ] too many", whole.replace("--radius: 12px;", "--radius: 12px];", 1))):
            with self.subTest(name=name):
                code, out, err = run("palette", path, "--css", self.css(text, name="broken.css"))
                self.assertEqual((code, err), (2, ""), out)
                self.assertIn("Cannot check the palette: The stylesheet's brackets do not pair up: the `", out)
                self.assertIn("Nothing was written", out)
                os.remove(os.path.join(self.dir, "broken.css"))
        self.assertEqual(snapshot(self.dir), before)

    def test_a_variable_only_one_dark_block_has_is_named_as_a_disagreement(self):
        # scenario 29 as it happens: --surface dropped from the @media block alone
        whole = T.read(os.path.join(self.dir, "global.css"))
        at = whole.index("@media (prefers-color-scheme: dark)")
        code, out, _ = run("palette", self.write(brand_md()), "--css", self.css(whole[:at] + whole[at:].replace("    --surface: #161836;\n", "", 1)))
        self.assertIn("two dark", out.lower())
        self.assertIn('  Surface (cards): #161836 in the :root[data-theme="dark"] block, not set in the @media (prefers-color-scheme: dark) block', out)
        # and a row the document has that the stylesheet's block lacks
        code, out, _ = run("palette", self.write(brand_md()), "--css", self.css(whole.replace("  --surface: #ffffff;\n", "", 1), name="light.css"))
        self.assertIn("Light theme, Surface (cards): BRAND.md says #ffffff, the :root block of the stylesheet does not set it", out)
        self.assertNotIn("no value", out)
        data = json.loads(run("palette", self.write(brand_md()), "--css", os.path.join(self.dir, "light.css"), "--json")[1])
        self.assertEqual(data["drift"], [{"theme": "light", "row": "surface", "document": "#ffffff", "stylesheet": "not set in this block"}])

    # --- the one form the check reads, and what it says of everything else ---------------------

    def test_the_eval_fixtures_end_as_the_skill_says_they_do(self):
        code, out, err = run("palette", os.path.join(EVALS, "pasted-palette.md"))
        self.assertEqual((code, err), (1, ""), out)
        fails = [l for l in out.splitlines() if l.startswith("FAILS")]
        self.assertEqual(len(fails), 3, out)
        for line, ratio in zip(fails, ("3.58", "3.34", "3.11")):
            self.assertIn("FAILS dark: Muted #7d6a58 on ", line)
            self.assertIn("is %s to 1; text needs 4.5 to 1" % ratio, line)
        self.assertIn("27 of 30 pairs pass.", out)
        code, out, err = run("palette", os.path.join(EVALS, "own-colours.md"))
        self.assertEqual((code, err), (2, ""), out)
        self.assertIn("  Light theme: Link, Soft background\n", out)
        self.assertIn("  Dark theme: Heading, Body (ink), Muted, Accent, Link, Hairline, Background, Soft background, Surface (cards)\n", out)
        self.assertNotIn("Could not read", out)
        self.assertNotIn("Not read", out)

    def test_a_file_in_which_no_palette_row_was_found_is_told_the_form_once(self):
        another = ("## Color Palette\n\n### Light Mode\n| Role | Color | Hex |\n|------|-------|-----|\n| Background | White | `#FFFFFF` |\n"
                   "| Text | Near Black | `#16162A` |\n| Primary | Royal Blue | `#2B50E0` |\n")
        for name, text in (("another tool's answer", another), ("a sentence", "Our colours are warm and brown.\n"), ("nothing", "")):
            with self.subTest(name=name):
                path = self.write(text)
                before = snapshot(self.dir)
                code, out, err = run("palette", path)
                self.assertEqual((code, err), (2, ""), out)
                said = [l for l in out.splitlines() if l.startswith("No row of a palette was found")]
                self.assertEqual(len(said), 1, out)
                for part in ("`### Brand`", "`### Light theme`", "`### Dark theme`", "`| Token | Hex |`", "Soft background", "The assistant can write your colours in that form",
                             "In a file that holds more than the palette (a BRAND.md), the three tables stand under the heading `## Colour palette`",
                             "where a text has that heading, this check looks only at the part under it"):
                    self.assertIn(part, said[0])
                self.assertNotIn("These rows are not filled in", out, "eighteen rows that are not there are not eighteen rows to fill in")
                self.assertIn("nothing was written", out.lower())
                self.assertEqual(snapshot(self.dir), before)
                data = json.loads(run("palette", path, "--json")[1])
                self.assertEqual((data["status"], data["exit"], data["form"]), ("incomplete", 2, _palette.FORM))
        code, out, _ = run("palette", self.write(another))
        self.assertIn('Not read: A table with colours for Background and Primary stands under the heading "### Light Mode".', out)
        self.assertIn('Not read: Line 7, "| Text | Near Black | `#16162A` |", holds a colour (#16162A) that was not read.', out)
        # the template has its rows, not filled in: that is said as before, and the form is not explained to it
        self.assertNotIn("No row of a palette", run("palette", T.BRAND_TEMPLATE)[1])
        self.assertEqual(json.loads(run("palette", self.write(brand_md(), name="full.md"), "--json")[1])["form"], "")

    def test_a_mark_in_a_later_cell_of_the_row_waits_for_her(self):
        # "| Primary | #000000 | - | proposed |" passed with exit 0
        md = brand_md().replace("| Primary | `#000000` | buttons, brand surfaces |", "| Primary | #000000 | - | proposed |")
        code, out, _ = run("palette", self.write(md))
        self.assertEqual(code, 3, out)
        self.assertIn("  Brand table, Primary: #000000", out)

    def test_a_mark_where_the_check_does_not_read_one_stops_short_of_a_pass(self):
        for name, md in (("a line under the heading", brand_md().replace("### Dark theme\n", "### Dark theme\n\n*Proposed, not yet confirmed*\n\n")),
                         ("a heading above the tables", brand_md().replace("## Colour palette", "## Proposed palette"))):
            with self.subTest(name=name):
                code, out, _ = run("palette", self.write(md))
                self.assertEqual(code, 2, out)
                said = [l for l in out.splitlines() if l.startswith("Not read: ")]
                self.assertEqual(len(said), 1, out)
                self.assertIn('holds the word "proposed"', said[0])
                self.assertIn("`### Dark theme (proposed)`", said[0])
                self.assertIn("30 of 30", out)

    def test_a_row_after_a_blank_line_that_cannot_be_read_is_said(self):
        # a complete palette, a blank line, "| Accent | rgba(0,0,0,0.5) |": exit 0, and not a word
        code, out, _ = run("palette", self.write(brand_md() + "\n| Accent | rgba(0,0,0,0.5) |\n"))
        self.assertEqual(code, 2, out)
        self.assertIn("Could not read a value: Accent (dark theme): The colour 'rgba(0,0,0,0.5)' is see-through.", out)

    def test_a_sentence_under_a_heading_files_nothing_elsewhere_and_a_label_makes_no_second_palette(self):
        md = "### Light theme\nNot for dark mode\n" + plain(STARTER_LIGHT) + "\n### Dark theme\nNote: this is our brand\n" + plain(STARTER_DARK)
        code, out, _ = run("palette", self.write(md))
        self.assertEqual(code, 0, out)
        self.assertIn("30 of 30", out)
        # a bold line is not a heading: the table under it is not the light theme's second table
        code, out, _ = run("palette", self.write("### Light theme\n" + plain(STARTER_LIGHT) + "\n**Dark theme**\n" + plain(STARTER_DARK)))
        self.assertEqual(code, 2, out)
        self.assertNotIn("pasted together", out)
        self.assertIn('Not read: A table with colours for Heading, Body (ink), Muted, Accent, Link, Hairline, Background, Soft background and Surface (cards) '
                      'stands after the line "**Dark theme**", further down under `### Light theme`.', out)
        self.assertIn("  Dark theme: Heading, Body (ink)", out)

    def test_two_colours_in_one_row_are_not_chosen_between(self):
        # "| Muted | #767676 | #777777 |" took the first, which passes on white where the second fails
        md = brand_md().replace("| Muted | `#5a5a72` |", "| Muted | #767676 | #777777 |")
        code, out, _ = run("palette", self.write(md))
        self.assertEqual(code, 2, out)
        self.assertIn("Could not read a value: Muted (light theme): the row holds two different colours, #767676 in the second cell and #777777 further along.", out)
        self.assertIn("  Light theme: Muted", out)

    def test_a_table_with_a_light_and_a_dark_column_is_told_what_to_do_instead(self):
        md = "| Token | Light | Dark |\n|---|---|---|\n" + "\n".join("| %s | %s | %s |" % (l, STARTER_LIGHT[k], STARTER_DARK[k]) for k, l in LABELS) + "\n"
        code, out, _ = run("palette", self.write(md))
        self.assertEqual(code, 2, out)
        self.assertIn("names both themes", out)
        self.assertIn("give each theme its own table", out)
        self.assertIn("No pair could be checked.", out)

    def test_a_stylesheet_block_in_another_shape_or_twice_or_with_important_is_said_not_read_around(self):
        whole = T.read(os.path.join(self.dir, "global.css"))
        path = self.write(brand_md())
        for name, text, parts in (("a selector list", whole.replace(":root {", ":root, html {", 1), ("The stylesheet has no :root { ... } block", "The rule `:root, html { ... }`", "written in another way than the starter writes it")),
                                  ("a colour set on body", whole + "\nbody { --bg: #eeeeee; }\n", ("--bg is also set in the rule `body { ... }`", "the page may show another colour there than the block's")),
                                  ("a second block", whole + "\n:root { --accent: #c0392b; }\n", ("The stylesheet has 2 blocks", "the light theme's colours", "must stand once", "does not write to a stylesheet that has one of them twice")),
                                  ("important, in a dark block", whole.replace("  --bg: #0a0b1e;", "  --bg: #0a0b1e !important;", 1), ("--bg in the :root[data-theme=\"dark\"] block: The colour '#0a0b1e !important' is not one this check can read",)),
                                  # round 4: each of these was read without a word, and a browser shows something else (the reader's own tests say what)
                                  ("a ; after a block", whole.replace("}\n\n:root[data-theme", "};\n\n:root[data-theme", 1), ("Line 22 of the stylesheet has a `;` where a browser expects a rule", "drops that rule")),
                                  ("a name written with an escape", whole + "\nbody { --b\\67: #000000; }\n", ("Line 90 of the stylesheet writes a name with a backslash (`--b\\67:`)", "this check does not read a name written with one")),
                                  ("a rule that registers a colour", whole + "\n@property --bg { syntax: '<color>'; inherits: true; initial-value: #000; }\n", ("Line 90 of the stylesheet registers one of the palette's variables",)),
                                  ("a default namespace", "@namespace url(http://www.w3.org/2000/svg);\n" + whole, ("Line 1 of the stylesheet sets a default namespace",)),
                                  ("a value that points outside the palette", whole.replace("--bg: #ffffff;", "--page: #ffffff;\n  --bg: var(--page);", 1) + "\nhtml:root { --page: #000000; }\n",
                                   ("--bg in the :root block: It is written as var(--page), which points at a variable this check does not read", "Write the colour out.")),
                                  ("a colour set twice", whole.replace("  --bg: #ffffff;", "  --bg: #ffffff;\n  --bg: #fafafa;", 1), ("--bg in the :root block: It is set 2 times in this block (#ffffff and #fafafa)",))):
            with self.subTest(name=name):
                code, out, err = run("palette", path, "--css", self.css(text))
                self.assertEqual((code, err), (2, ""), out)
                said = [l for l in out.splitlines() if l.startswith("Could not read the stylesheet: ")]
                self.assertEqual(len(said), 1, out)
                for part in parts:
                    self.assertIn(part, said[0])
                self.assertNotIn("BRAND.md and the stylesheet disagree", out, "what was not read is not compared")
        # in the :root block an !important wins over both dark blocks' lines, so it is said of all three
        code, out, err = run("palette", path, "--css", self.css(whole.replace("--bg: #ffffff;", "--bg: #ffffff !important;", 1)))
        said = [l for l in out.splitlines() if l.startswith("Could not read the stylesheet: ")]
        self.assertEqual((code, err, len(said)), (2, "", 3), out)
        self.assertIn("--bg in the :root block: The colour '#ffffff !important' is not one this check can read", said[0])
        self.assertIn("--bg in the @media (prefers-color-scheme: dark) block: It is marked !important in the :root block, and that line wins over this block's", said[2])
        self.assertNotIn("The two dark blocks in the stylesheet disagree", out)

    # --- round 4: what the reader was mended for, through the command ----------------------------------

    def test_each_reading_that_round_4_found_wrong_ends_as_it_should_through_the_command(self):
        # each of these ended with 0 ("pass") before; the reader's own tests have the variants
        good = pasted()
        cases = (
            ("the mark between underscores in a later cell", good.replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | _proposed_ |"), 3, ("Dark theme, Muted: #a6abce",)),
            ("the mark between underscores in the value cell", good.replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` __proposed__ |"), 3, ("Dark theme, Muted: #a6abce",)),
            ("a mark in another language on a heading", good.replace("### Dark theme", "### Dark theme (vorgeschlagen)"), 2,
             ('Not read: Line 19, the heading "### Dark theme (vorgeschlagen)", names none of the three sections', "the mark `(proposed)`, written in English")),
            ("a line that starts with # and is no heading", "## Colour palette\n\n" + good + "\n#1: the dark values are still proposed\n", 2,
             ('Not read: Line 34, "#1: the dark values are still proposed", holds the word "proposed"',)),
            ("the palette's heading twice, once with emphasis inside a word", "## Colour palette\n\n" + good + "\n## Colour pal*ette\n", 2, ("stands 2 times in this text",)),
            ("a long label that names another section", good.replace("### Dark theme\n", "### Dark theme\n\nLight theme (%s)\n\n" % ("x" * 300)), 2,
             ("stands between the heading `### Dark theme` and its table, and it is the name of another section",)),
            ("a header row that names another section", good.replace("### Dark theme\n| Token | Hex |", "### Dark theme\n| Light theme | Hex |"), 2,
             ('Not read: Line 20, the header row "| Light theme | Hex |", calls its first column by the name of another section',)),
            ("the three headings with as many # as the palette's", "### Colour palette\n\n" + good, 2,
             ("ends at the next heading that has as many # as that one, or fewer: this heading", "Give the three headings with the tables more #")),
            ("a guide whose palette heading has another name", "# Guide\n\n## Colours\n\n" + good + "\n## Cards\n\nBackground #2a1f17.\n", 2,
             ("holds a colour (#2a1f17) that was not read", "put the three headings with their tables under a heading `## Colour palette`")),
        )
        for name, text, want, parts in cases:
            with self.subTest(name=name):
                code, out, err = run("palette", "-", stdin=text)
                self.assertEqual((code, err), (want, ""), out)
                for part in parts:
                    self.assertIn(part, out)
        # and what is fine stays fine: a string with backslashes in it that is closed on its line, and brackets that pair up
        # (round 5: a string carried over a line end and an escaped class name are named now: the test below)
        whole = T.read(os.path.join(self.dir, "global.css"))
        css = self.css(whole.replace(":root {\n", ':root {\n  --note: "a\\41 } --bg: #000000; \\\\";\n  --grid: [; --ink: #000000; ];\n', 1) + "\na::after { content: '\\201C' }\n")
        code, out, err = run("palette", self.write(brand_md()), "--css", css)
        self.assertEqual((code, err), (0, ""), out)
        self.assertNotIn("stylesheet", out.replace("the stylesheet given", ""))

    # --- round 5: what the two readers were mended for, through the command ----------------------------

    def test_each_reading_that_round_5_found_wrong_ends_as_it_should_through_the_command(self):
        # each of these ended with 0 ("pass") before, or (the last three) with a row that could not be read where it is a proposal
        good = pasted()
        swapped = good.replace("### Light theme", "### L").replace("### Dark theme", "### Light theme").replace("### L\n", "### Dark theme\n")
        cases = (
            ("the mark inside a strike-through after the colour", good.replace("| Muted | `#a6abce` |", "| Muted | #a6abce ~~proposed~~ |"), 3, ("Dark theme, Muted: #a6abce",)),
            ("the mark with a footnote figure after the colour", good.replace("| Muted | `#a6abce` |", "| Muted | #a6abce proposed\u00b2 |"), 3, ("Dark theme, Muted: #a6abce",)),
            ("the mark with a circled figure in a later cell", good.replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | proposed\u2460 |"), 3, ("Dark theme, Muted: #a6abce",)),
            ("the word with a soft hyphen inside it, in a later cell", good.replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | prop\u00adosed |"), 3, ("Dark theme, Muted: #a6abce",)),
            ("the word with a zero-width space inside it, in a sentence", good + "\nThe dark values are pro\u200bposed.\n", 2,
             ('Not read: Line 32, "The dark values are pro<U+200B>posed.", holds the word "proposed"', "is a character that does not show on the screen: take it out")),
            ("a label for the other theme under a theme's heading", swapped.replace("### Light theme\n", "### Light theme\n\nDark mode\n\n"), 2,
             ('Not read: Line 21, "Dark mode", stands between the heading `### Light theme` and its table, and it reads as a label for the other theme',)),
            ("a header row that says the other theme's word", good.replace("### Dark theme\n| Token | Hex |", "### Dark theme\n| Token (light) | Hex |"), 2,
             ('Not read: Line 20, the header row "| Token (light) | Hex |", says "light", and its table stands under `### Dark theme`', "take that word out of the header row")),
            ("a comment line in a code sample, and the word after it", "## Colour palette\n\n" + good + "\n```sh\n# build the cards\n```\n\nThe dark values are proposed.\n", 2,
             ('Not read: Line 38, "The dark values are proposed.", holds the word "proposed"',)),
            ("a saturation over 100%", good.replace("| Muted | `#a6abce` |", "| Muted | hsl(233 150% 73%) |"), 2,
             ('Could not read a value: Muted (dark theme): the second cell holds "hsl(233 150% 73%)". This check reads exactly one colour there',)),
        )
        for name, text, want, parts in cases:
            with self.subTest(name=name):
                code, out, err = run("palette", self.write(text, name="case.md"))
                self.assertEqual((code, err), (want, ""), out)
                for part in parts:
                    self.assertIn(part, out)
        # what is fine stays fine: a sentence on the mood that holds the other theme's word
        code, out, err = run("palette", self.write(good.replace("### Light theme\n", "### Light theme\n\nWarm paper, dark ink.\n\n"), name="mood.md"))
        self.assertEqual((code, err), (0, ""), out)
        # and the remedy for a whole guide is said once, however many lines are quoted
        guide = "# Guide\n\n## Colours\n\n" + good + "\n## Cards\n" + "".join("\nCard %d: #%06x.\n" % (n, n) for n in range(1, 9))
        code, out, err = run("palette", self.write(guide, name="guide.md"))
        self.assertEqual((code, err, out.count("under a heading `## Colour palette`")), (2, "", 1), out)

    def test_each_reading_that_round_6_found_wrong_ends_as_it_should_through_the_command(self):
        good = pasted()
        swapped = good.replace("### Light theme", "### L").replace("### Dark theme", "### Light theme").replace("### L\n", "### Dark theme\n")
        under_light = lambda line: swapped.replace("### Light theme\n", "### Light theme\n\n%s\n\n" % line)  # noqa: E731
        label = "stands between the heading `### Light theme` and its table, and it reads as a label for the other theme"
        cases = (
            # each of these ended with 0 ("pass"), the dark table read as the light theme
            ("a label for the other theme in brackets", under_light("(Dark theme)"), 2, ('Not read: Line 21, "(Dark theme)", ' + label,)),
            ("the label after another word, in brackets", under_light("Palette (dark)"), 2, ('Not read: Line 21, "Palette (dark)", ' + label,)),
            ("a label in one word", under_light("Darkmode"), 2, ('Not read: Line 21, "Darkmode", ' + label,)),
            ("night for dark", under_light("Night mode"), 2, ('Not read: Line 21, "Night mode", ' + label,)),
            ("a label word that the list lacked", under_light("Dark colour scheme"), 2, ('Not read: Line 21, "Dark colour scheme", ' + label,)),
            ("a label with a soft hyphen in the word", under_light("Dar\u00adk theme table"), 2,
             ('Not read: Line 21, "Dar<U+00AD>k theme table", ' + label, "is a character that does not show on the screen: take it out")),
            ("a header cell that is such a label in one word", swapped.replace("### Light theme\n| Token | Hex |", "### Light theme\n| Token | Hex | Darkmode |"), 2,
             ('Not read: Line 20, the header row "| Token | Hex | Darkmode |", says "darkmode", and its table stands under `### Light theme`', "take that word out of the header row")),
            # the word with a character nobody sees inside it, of the three categories round 6 added
            ("the word with a variation selector inside it, in a sentence", good + "\nThe dark values are pro\ufe0fposed.\n", 2, ('holds the word "proposed"',)),
            ("the word struck through by combining strokes, in a later cell", good.replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | p\u0336r\u0336o\u0336p\u0336o\u0336s\u0336e\u0336d\u0336 |"), 3,
             ("Dark theme, Muted: #a6abce",)),
            ("the word with a control character inside it, in a sentence", good + "\nThe dark values are pro\x01posed.\n", 2,
             ('Not read: Line 32, "The dark values are pro<U+0001>posed.", holds the word "proposed"',)),
            # only the line that opens a code block was copied: the sentence says what is there
            ("a palette after an opening fence line that nothing closes", "```markdown\n" + good, 2,
             ("(line 1 opens one with ``` or ~~~, and no line after it closes it)", "Take line 1, which opens the code block, out, so that the headings after it count.")),
            ("a palette between two fence lines", "```markdown\n" + good + "```\n", 2, ("Take the two lines that open and close the code block out, so that the headings inside it count.",)),
            # a heading's remark with a strike-through inside the word is another remark
            ("a strike-through inside the word of a heading's remark", good.replace("### Dark theme", "### Dark theme (pro~posed)"), 2,
             ('Not read: Line 19, the heading "### Dark theme (pro~posed)", names none of the three sections',)),
            ("currentColor in a cell", good.replace("| Muted | `#a6abce` |", "| Muted | currentColor |"), 2,
             ("Could not read a value: Muted (dark theme): The colour is written as currentColor, which is whatever colour the text around it has and no colour of its own. Write the "
              "colour itself, as #rrggbb.",)),
            ("a gradient in a cell", good.replace("| Muted | `#a6abce` |", "| Muted | url(#fade) |"), 2,
             ("Could not read a value: Muted (dark theme): The colour 'url(#fade)' is a gradient or a pattern. This check reads one flat colour: write it as #rrggbb.",)),
        )
        for name, text, want, parts in cases:
            with self.subTest(name=name):
                code, out, err = run("palette", self.write(text, name="case.md"))
                self.assertEqual((code, err), (want, ""), out)
                for part in parts:
                    self.assertIn(part, out)
                self.assertNotIn("The mark paints", out)
        # What is fine stays fine, with 0: a sentence on the mood that names the heading's own theme too, a header cell that is a note, and the
        # brand guide's own template filled in completely. And the limits rule 2 and rule 9 state end with 0 as well: a character reference, a
        # wide letter and emphasis inside the word are not seen through (resolving them was the traceback and the stall below).
        fine = (("a mood line that names both themes", good.replace("### Light theme\n", "### Light theme\n\nLight for day, dark for night.\n\n")),
                ("a mood line with the other theme's word", good.replace("### Light theme\n", "### Light theme\n\nWarm paper, dark ink.\n\n")),
                ("a header row with a comparison column", good.replace("### Light theme\n| Token | Hex |\n|---|---|", "### Light theme\n| Token | Hex | Contrast on dark ink |\n|---|---|---|")),
                ("the same under the dark theme", good.replace("### Dark theme\n| Token | Hex |\n|---|---|", "### Dark theme\n| Token | Hex | Light equivalent |\n|---|---|---|")),
                ("the guide's template, filled in", filled_guide()),
                ("the limit: a character reference inside the word", good + "\nThe dark values are prop&shy;osed, &#112;roposed.\n"),
                ("the limit: a label with a character reference", under_light("Dark&nbsp;mode")), ("the limit: a label with emphasis inside the word", under_light("The da**rk** theme")),
                ("the limit: a longer sentence", under_light("This table is for the dark theme of the site.")))
        for name, text in fine:
            with self.subTest(name=name):
                code, out, err = run("palette", self.write(text, name="fine.md"))
                self.assertEqual((code, err), (0, ""), out)

    def test_no_text_that_round_6_found_ends_in_a_traceback_or_stalls_the_command(self):
        # A character reference of more than 4,300 digits was a traceback on Python 3.13 (`palette - --json` printed no JSON) and 11 seconds of
        # processor time for a megabyte on 3.9; a long run of combining characters took 52 seconds for half a megabyte on 3.9; and rows of cells
        # that begin a colour and hold a letter beyond ASCII took 21 and 31 seconds. Each is read in about a second now, and ends as it should.
        # (Measured as the processor time of the command itself, where the system counts it for a child.)
        good, mb = pasted(), 1000 * 1000
        shapes = (("a reference of 5,000 digits", good + "\nA &#" + "9" * 5000 + ";roposed line.\n", 0),
                  ("a megabyte that is one reference", good + "\n&#" + "1" * mb + ";\n", 0),
                  ("a megabyte of two combining characters after a letter, and the word", good + "\nA" + "\u0315" * (mb // 4) + "\u0300" * (mb // 4) + " proposed\n", 2),
                  ("a megabyte of mixed combining characters around the word", good + "\n" + "pro\u0336\u0315\u0300\ufe0f\u20ddposed \u0301\n" * (mb // 26), 2),
                  ("a megabyte of rows whose cells begin a colour and hold a letter beyond ASCII", "### Light theme\n" + ("|#\u00e9" * 660 + "\n") * 375, 2),
                  ("the same with a character nobody sees", "### Light theme\n" + ("|#\ufe0f" * 400 + "\n") * 495, 2))
        for name, text, want in shapes:
            with self.subTest(name=name):
                self.assertLess(len(text.encode("utf-8")), 1024 * 1024, "under the megabyte the command reads")
                before = os.times()
                code, out, err = run("palette", "-", "--json", stdin=text)
                after = os.times()
                took = (after.children_user + after.children_system) - (before.children_user + before.children_system)
                self.assertEqual((code, err), (want, ""), out[:300])
                data = json.loads(out)
                self.assertEqual((data["exit"], data["status"]), (want, "pass" if want == 0 else "incomplete"))
                if "the word" in name:
                    self.assertIn('holds the word "proposed"', data["problems"][0]["message"])
                self.assertLess(took, 6.0, "the command took %.2f s of processor time" % took)

    def test_each_stylesheet_that_round_6_found_misread_ends_as_it_should_through_the_command(self):
        whole = T.read(os.path.join(self.dir, "global.css"))
        doc = self.write(brand_md())
        mark = "Could not read the stylesheet: Line %d of the stylesheet holds an HTML comment mark (`%s`). A browser passes over such a mark in some places of a stylesheet"
        cases = (
            # each of these ended with 0 before: "pass", no drift, and a page that showed #ff0000 or no colour at all
            ("an HTML comment mark before url( in a value", whole.replace("  --bg: #ffffff;", "  --bg: #ffffff;\n  --x: <!--url(a'b); --bg: #ff0000; /*'*/ );", 1), 2,
             (mark % (16, "<!--"), "Take the mark out. (A comment in a stylesheet is written `/* ... */`.)")),
            ("an HTML comment mark before a registration", '<!-- @property --bg { syntax: "<color>"; inherits: false; initial-value: #ff0000; }\n' + whole, 2, (mark % (1, "<!--"),)),
            ("the closing mark, last", whole + "-->\n", 2, (mark % (89, "-->"),)),
            ("a mark that leaves a bracket open to this reading", whole + "\na { b: <!--url(') }\n", 2,
             ("Cannot check the palette: Line 90 of the stylesheet holds an HTML comment mark (`<!--`).", "Nothing was written.")),
            ("a line of another rule whose value holds a block", whole + "\nhtml:root { --bg: #ff0000 {} }\n", 2,
             ("Could not read the stylesheet: --bg is also set in the rule `html:root { --bg: #ff0000 { ... } }`, outside the three blocks that hold the palette",)),
            ("the same on :root twice, with nothing before the block", whole + "\n:root:root { --accent: {} }\n", 2,
             ("Could not read the stylesheet: --accent is also set in the rule `:root:root { --accent: { ... } }`, outside the three blocks",)),
            # a sentence that spoke of a mark where there is none
            ("currentColor for a colour", whole.replace("  --muted: #a6abce;", "  --muted: currentColor;", 1), 2,
             ("Could not read the stylesheet: --muted in the :root[data-theme=\"dark\"] block: The colour is written as currentColor, which is whatever colour the text around it has and "
              "no colour of its own. Write the colour itself, as #rrggbb.",)),
            ("a picture for a colour", whole.replace("  --muted: #a6abce;", "  --muted: url(fade.png);", 1), 2,
             ("Could not read the stylesheet: --muted in the :root[data-theme=\"dark\"] block: The colour 'url(fade.png)' is a gradient or a pattern. This check reads one flat colour: "
              "write it as #rrggbb.",)),
            # what stays fine: a mark inside a comment or a string, and a block after something that only holds a colour's name
            ("the marks inside a comment and a string", whole + '\n/* <!-- --> */\na::before { content: "<!-- -->"; }\n', 0, ("30 of 30 pairs pass.",)),
            ("a feature query that names a colour", whole + "\n@supports (--bg: red) { a { color: red } }\n", 0, ("30 of 30 pairs pass.",)),
        )
        for name, text, want, parts in cases:
            with self.subTest(name=name):
                code, out, err = run("palette", doc, "--css", self.css(text))
                self.assertEqual((code, err), (want, ""), out)
                for part in parts:
                    self.assertIn(part, out)
                self.assertNotIn("The mark paints", out)
                if want == 0:
                    self.assertNotIn("stylesheet", out.replace("the stylesheet given", ""))
                data = json.loads(run("palette", doc, "--css", self.css(text), "--json")[1])
                self.assertEqual((data["exit"], data["status"]), (want, "pass" if want == 0 else "unreadable" if parts[0].startswith("Cannot") else "incomplete"))

    def test_the_install_stops_on_what_round_6_found_in_a_stylesheet(self):
        # the same stylesheets through the other door, as a dry run: the install does not write, with the check's own sentence
        script = [sys.executable, SCRIPT, "install", "--test-command", "true", "--dry-run", "--with-colours"]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        whole = T.starter_file("src/styles/global.css")
        cases = (("an HTML comment mark before url( in a value", whole.replace("  --bg: #ffffff;", "  --bg: #ffffff;\n  --x: <!--url(a'b); --bg: #ff0000; /*'*/ );", 1),
                  "Line 16 of the stylesheet holds an HTML comment mark (`<!--`)."),
                 ("an HTML comment mark before a registration", '<!-- @property --bg { syntax: "<color>"; inherits: false; initial-value: #ff0000; }\n' + whole,
                  "Line 1 of the stylesheet holds an HTML comment mark (`<!--`)."),
                 ("a line of another rule whose value holds a block", whole + "\nhtml:root { --bg: #ff0000 {} }\n", "--bg is also set in the rule `html:root { --bg: #ff0000 { ... } }`"),
                 ("the same on :root twice", whole + "\n:root:root { --accent: {} }\n", "--accent is also set in the rule `:root:root { --accent: { ... } }`"))
        for name, text, part in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                site = T.make_starter_site(os.path.join(tmp, "site"), with_modules=False)
                with open(os.path.join(site, "BRAND.md"), "w", encoding="utf-8") as f:
                    f.write(brand_md(light=T.BAKERY_LIGHT, dark=T.BAKERY_DARK, primary="#b4531a"))
                sheet = os.path.join(site, "src", "styles", "global.css")
                with open(sheet, "w", encoding="utf-8", newline="") as f:
                    f.write(text)
                before = T.read_bytes(sheet)
                r = subprocess.run(script + ["--site", site], capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
                self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout)
                self.assertIn(part, r.stdout)
                self.assertEqual(T.read_bytes(sheet), before, "a refusal writes nothing")

    def test_each_reading_that_round_7_found_wrong_ends_as_it_should_through_the_command(self):
        good = pasted()
        swapped = good.replace("### Light theme", "### L").replace("### Dark theme", "### Light theme").replace("### L\n", "### Dark theme\n")
        under_light = lambda line: swapped.replace("### Light theme\n", "### Light theme\n\n%s\n\n" % line)  # noqa: E731
        between = "stands between the heading `### Light theme` and its table, and it "
        brand, themes = good[:good.index("### Light theme")], good[good.index("### Light theme"):]
        last = len(good.splitlines()) + 2
        cases = (
            # R7-201: U+001F, which Python's split() takes for a blank, cut the word in two before the cleaning pass ran: each ended with 0
            ("U+001F inside the word, in a sentence", good + "\nAll dark values are pro\x1fposed.\n", 2,
             ('Not read: Line %d, "All dark values are pro<U+001F>posed.", holds the word "proposed"' % last, "is a character that does not show on the screen: take it out")),
            ("U+001F inside the word, in a note cell", good.replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | pro\x1fposed |"), 3, ("  Dark theme, Muted: #a6abce",)),
            ("U+001F inside the name of the other theme", under_light("Dar\x1fk theme"), 2, ('Not read: Line 21, "Dar<U+001F>k theme", ' + between + "is the name of another section",)),
            ("U+001F inside a label word", under_light("Dark mo\x1fde"), 2, ('Not read: Line 21, "Dark mo<U+001F>de", ' + between + "reads as a label for the other theme",)),
            # R7-202: the example rule 2 gave as passed over is named, as the name of another section
            ("emphasis inside the exact name", under_light("da**rk** theme"), 2, ('Not read: Line 21, "da**rk** theme", ' + between + "is the name of another section",)),
            # R7-209: a heading that counts above the code block; the sentence said the theme's heading "is not a heading"
            ("the two themes in a code block under the Brand table", brand + "```markdown\n" + themes + "```\n", 2,
             ('stands under the line "### Light theme", which stands inside a code block (between two lines of ``` or ~~~), where this check takes no line for a heading',
              "Take the two lines that open and close the code block out, so that the headings inside it count.")),
            ("the same with only the line that opens the block", brand + "```markdown\n" + themes, 2,
             ('stands under the line "### Dark theme", which stands inside a code block (line %d opens one with ``` or ~~~, and no line after it closes it)' % (len(brand.splitlines()) + 1),
              "Take line %d, which opens the code block, out, so that the headings after it count." % (len(brand.splitlines()) + 1))),
            # R7-208: a correct palette that round 6 refused, for a word that only begins with the other theme's word
            ("a Lightness column under the dark theme", good.replace("### Dark theme\n| Token | Hex |\n|---|---|", "### Dark theme\n| Token | Hex | Lightness |\n|---|---|---|"), 0, ("30 of 30 pairs pass.",)),
            ("a note on lightness under the dark theme", good.replace("### Dark theme\n", "### Dark theme\n\nLightness values\n\n"), 0, ("30 of 30 pairs pass.",)),
            ("a note on darkening under the light theme", good.replace("### Light theme\n", "### Light theme\n\nHex values (darkened 10%)\n\n"), 0, ("30 of 30 pairs pass.",)),
            ("a darker version under the light theme", good.replace("### Light theme\n", "### Light theme\n\nVersion 2 (darker)\n\n"), 0, ("30 of 30 pairs pass.",)),
            # and what stays a label: the theme's word whole, and the two closed compounds with a hyphen or with digits
            ("the compound with a hyphen and a digit", under_light("Dark-mode 2"), 2, ('Not read: Line 21, "Dark-mode 2", ' + between + "reads as a label for the other theme",)),
            ("the compound in one word, with digits", under_light("DarkTheme2"), 2, ('Not read: Line 21, "DarkTheme2", ' + between + "reads as a label for the other theme",)),
            # the limits rules 2 and 9 state: a character that ends a line to this reader, and one nobody sees that the pass does not take out
            ("the limit: U+001E inside the word", good + "\nAll dark values are pro\x1eposed.\n", 0, ("30 of 30 pairs pass.",)),
            ("the limit: a filler that Unicode files as a letter", good + "\nAll dark values are pro\u1160posed.\n", 0, ("30 of 30 pairs pass.",)),
        )
        for name, text, want, parts in cases:
            with self.subTest(name=name):
                self.assertNotEqual(text, good)
                path = self.write(text, name="round7.md")
                before = snapshot(self.dir)
                code, out, err = run("palette", path)
                self.assertEqual((code, err), (want, ""), out)
                for part in parts:
                    self.assertIn(part, out)
                data = json.loads(run("palette", path, "--json")[1])
                self.assertEqual((data["exit"], data["status"]), (want, {0: "pass", 2: "incomplete", 3: "needs-confirmation"}[want]))
                self.assertEqual(snapshot(self.dir), before)
        self.assertNotIn("is not a heading", run("palette", self.write(brand + "```markdown\n" + themes + "```\n", name="round7.md"))[1])

    def test_each_text_that_round_8_found_refused_for_a_no_break_space_is_read_again_through_the_command(self):
        # R8-201: round 7 folded a space and a tab only, so a no-break space (Option+Space on a Mac keyboard; a paste from a web page or a
        # chat) after a heading's #, before a row's first | or inside a value ended with 2, and `##<U+00A0>Colour palette` made the whole
        # brand guide the palette without the refusal ever quoting that line. Each ends as the same text with a plain space does.
        good, guide = pasted(), filled_guide()
        self.assertIn("| Muted | `#a6abce` |", good)
        nb = "\u00a0"
        cases = [
            ("after the # of one heading", good, good.replace("### Light theme", "###" + nb + "Light theme")),
            ("after the # of all three headings", good, good.replace("### ", "###" + nb)),
            ("a wide space (U+3000) there", good, good.replace("### ", "###\u3000")),
            ("before the first | of one row", good, good.replace("| Muted | `#a6abce` |", nb + "| Muted | `#a6abce` |")),
            ("before the first | of every row", good, "\n".join(nb + line if line.startswith("|") else line for line in good.split("\n"))),
            ("inside a value", good.replace("`#ffffff`", "rgb(255, 255, 255)"), good.replace("`#ffffff`", "rgb(255," + nb + "255," + nb + "255)")),
            ("a thin space (U+2009) inside a value", good.replace("`#ffffff`", "rgb(255 255 255)"), good.replace("`#ffffff`", "rgb(255\u2009255\u2009255)")),
            ("between a value and its mark", good.replace("| Muted | `#a6abce` |", "| Muted | #a6abce proposed |"), good.replace("| Muted | `#a6abce` |", "| Muted | #a6abce" + nb + "proposed |")),
            ("every space of the text (a paste from a rendered page)", good, good.replace(" ", nb)),
            ("a line that holds nothing else, inside a table", good.replace("| Muted | `#a6abce` |\n", "| Muted | `#a6abce` |\n \n"), good.replace("| Muted | `#a6abce` |\n", "| Muted | `#a6abce` |\n" + nb + "\n")),
            # the suite's own template, filled in as it asks (a shadow's rgba(), the share cards' colours and the word outside the section)
            ("the template's `## Colour palette`", guide, guide.replace("## Colour palette", "##" + nb + "Colour palette")),
            ("the same with the space between its two words", guide, guide.replace("## Colour palette", "## Colour" + nb + "palette")),
        ]
        for name, plain_text, typed in cases:
            with self.subTest(name=name):
                self.assertNotEqual(typed, plain_text)
                want = run("palette", self.write(plain_text, name="plain.md"))
                self.assertEqual(want[0], 3 if "mark" in name else 0, want[1])
                path = self.write(typed, name="round8.md")
                before = snapshot(self.dir)
                code, out, err = run("palette", path)
                self.assertEqual((code, out.replace("round8.md", "plain.md"), err), want)
                self.assertNotIn("U+", out)
                data, same = json.loads(run("palette", path, "--json")[1]), json.loads(run("palette", self.write(plain_text, name="round8.md"), "--json")[1])
                self.assertEqual(data, same)
                self.assertEqual((data["problems"], data["status"]), ([], "needs-confirmation" if "mark" in name else "pass"))
        self.assertIn("30 of 30 pairs pass.", run("palette", self.write(cases[-2][2], name="round8.md"))[1])
        # R7-201 stays mended (the test above has the rest): U+001F is no blank, in the word and after a heading's #
        code, out, _ = run("palette", self.write(good.replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | pro\x1fposed |"), name="round8.md"))
        self.assertEqual(code, 3, out)
        code, out, _ = run("palette", self.write(good.replace("### Light theme", "###\x1fLight theme"), name="round8.md"))
        self.assertEqual(code, 2, out)
        self.assertIn('"###<U+001F>Light theme"', out)

    def test_a_charset_written_with_another_of_the_names_a_browser_takes_for_utf8_stops_neither_the_check_nor_the_install(self):
        # R8-205: `@charset "utf8";` ended the check with 2 and stopped the install, with the untrue reason that the file "is written in
        # another encoding than UTF-8"
        whole = T.read(os.path.join(self.dir, "global.css"))
        path = self.write(brand_md())
        for statement in ('@charset "utf8";', '@charset "UTF8";', "@charset 'unicode-1-1-utf-8';", '@charset " x-unicode20utf8 ";'):
            with self.subTest(statement=statement):
                code, out, err = run("palette", path, "--css", self.css(statement + "\n" + whole))
                self.assertEqual((code, err), (0, ""), out)
                self.assertNotIn("encoding", out)
                data = json.loads(run("palette", path, "--css", self.css(statement + "\n" + whole), "--json")[1])
                self.assertEqual((data["status"], data["stylesheet_problems"], data["drift"]), ("pass", [], []))
        # the near-miss stays refused, with the sentence that is true of it
        code, out, _ = run("palette", path, "--css", self.css('@charset "utf-16";\n' + whole))
        self.assertEqual(code, 2, out)
        self.assertIn('says the file is written in another encoding than UTF-8 (`@charset "utf-16"`)', out)
        # and the install writes the palette into such a stylesheet, the line left as it stands
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            site = T.make_starter_site(os.path.join(tmp, "site"), with_modules=False)
            with open(os.path.join(site, "BRAND.md"), "w", encoding="utf-8") as f:
                f.write(brand_md(light=T.BAKERY_LIGHT, dark=T.BAKERY_DARK, primary="#b4531a"))
            sheet = os.path.join(site, "src", "styles", "global.css")
            with open(sheet, "w", encoding="utf-8", newline="") as f:
                f.write('@charset "utf8";\n' + T.starter_file("src/styles/global.css"))
            r = subprocess.run([sys.executable, SCRIPT, "install", "--test-command", "true", "--with-colours", "--site", site, "--json"],
                               capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
            self.assertEqual((r.returncode, r.stderr), (0, ""), r.stdout)
            self.assertIn("src/styles/global.css", json.loads(r.stdout)["written"])
            css = _palette.read_css(T.read(sheet))
            self.assertTrue(T.read(sheet).startswith('@charset "utf8";\n'))
            self.assertEqual((css.brand, css.light, css.dark, css.dark_media, css.problems), ("#b4531a", T.BAKERY_LIGHT, T.BAKERY_DARK, T.BAKERY_DARK, []))

    def test_each_stylesheet_that_round_7_found_misread_ends_as_it_should_through_the_command(self):
        whole = T.read(os.path.join(self.dir, "global.css"))
        aliased = whole.replace("  --brand: #000000;", "  --brand: var(--accent);", 1)
        self.assertNotEqual(aliased, whole)
        primary = ("Could not read the stylesheet: --brand in the :root block: It is written as var(--accent): the brand colour points at another variable, which each theme may set "
                   "differently, and the Primary is one colour for both themes. Write the colour out (`--brand: #1a2b3c;`, with your colour).")
        cases = (
            # R7-204: read as one colour, no problem and no drift (exit 0), while a dark page shows the dark Accent
            ("the Primary written as the accent, under a palette whose Primary is the light Accent", brand_md(primary=STARTER_LIGHT["accent"]), aliased, 2, (primary,)),
            ("the same under the starter's own palette", brand_md(), aliased, 2, (primary,)),
            # R7-205: a browser that loads the file as it is reads it in the encoding the line names
            ("a charset that names another encoding", brand_md(), '@charset "iso-2022-kr";\n' + whole, 2,
             ('Could not read the stylesheet: Line 1 of the stylesheet says the file is written in another encoding than UTF-8 (`@charset "iso-2022-kr"`).',
              "Save the file as UTF-8 and take that line out.")),
            # what stays fine: UTF-8 said in so many words, and the starter's own line from one theme colour to another
            ("a charset that says UTF-8", brand_md(), '@charset "UTF-8";\n' + whole, 0, ("30 of 30 pairs pass.",)),
            ("the starter's stylesheet, whose link is written as the accent", brand_md(), whole, 0, ("30 of 30 pairs pass.",)),
        )
        self.assertIn("  --link: var(--accent);", whole)
        for name, doc, text, want, parts in cases:
            with self.subTest(name=name):
                path = self.write(doc)
                code, out, err = run("palette", path, "--css", self.css(text))
                self.assertEqual((code, err), (want, ""), out)
                for part in parts:
                    self.assertIn(part, out)
                self.assertNotIn("BRAND.md and the stylesheet disagree", out, "the Primary is said once, as a line that cannot be read")
                if want == 0:
                    self.assertNotIn("stylesheet", out.replace("the stylesheet given", ""))
                data = json.loads(run("palette", path, "--css", self.css(text), "--json")[1])
                self.assertEqual((data["exit"], data["status"], data["drift"]), (want, "pass" if want == 0 else "incomplete", []))

    def test_the_install_stops_on_a_charset_that_names_another_encoding(self):
        # R7-205 through the other door, as a dry run and as a real one: the install does not write, with the check's own sentence
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        for extra in (["--dry-run"], []):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as tmp:
                site = T.make_starter_site(os.path.join(tmp, "site"), with_modules=False)
                with open(os.path.join(site, "BRAND.md"), "w", encoding="utf-8") as f:
                    f.write(brand_md(light=T.BAKERY_LIGHT, dark=T.BAKERY_DARK, primary="#b4531a"))
                sheet = os.path.join(site, "src", "styles", "global.css")
                with open(sheet, "w", encoding="utf-8", newline="") as f:
                    f.write('@charset "iso-2022-kr";\n' + T.starter_file("src/styles/global.css"))
                before = T.read_bytes(sheet)
                r = subprocess.run([sys.executable, SCRIPT, "install", "--test-command", "true", "--with-colours", "--site", site] + extra,
                                   capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
                self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout)
                self.assertIn('Line 1 of the stylesheet says the file is written in another encoding than UTF-8 (`@charset "iso-2022-kr"`).', r.stdout)
                self.assertEqual(T.read_bytes(sheet), before, "a refusal writes nothing")

    def test_each_stylesheet_that_round_5_found_misread_ends_as_it_should_through_the_command(self):
        whole = T.read(os.path.join(self.dir, "global.css"))
        doc = self.write(brand_md())
        dark = ':root[data-theme="dark"]'
        cases = (
            # each of these ended with 0 before: "pass", no drift, and a page that showed another colour or none
            ("a no-break space before a colour", whole.replace("  --bg: #ffffff;", "  --bg:\u00a0#ffffff;", 1), 2,
             ("Could not read the stylesheet: --bg in the :root block: The colour '#ffffff' has a character before or after it that looks like a space and is none to a browser",
              "Delete the blanks around the colour and type them again.")),
            ("a wide space after a colour in the media block", whole.replace("    --ink: #dce0f5;", "    --ink: #dce0f5\u2003;", 1), 2,
             ("Could not read the stylesheet: --ink in the @media (prefers-color-scheme: dark) block: The colour '#dce0f5' has a character before or after it",)),
            ("a vertical tab before a colour", whole.replace("  --muted: #a6abce;", "  --muted: \x0b#a6abce;", 1), 2,
             ("Could not read the stylesheet: --muted in the :root[data-theme=\"dark\"] block: The colour '#a6abce' has a character before or after it",)),
            ("url( spelt with a backslash", whole.replace("  --bg: #ffffff;", "  --bg: #ffffff;\n  --x: u\\72l(a'b); --bg: #ff0000; /*'*/ );", 1), 2,
             ("Could not read the stylesheet: Line 16 of the stylesheet writes a name with a backslash (`u\\72l(a'b)`).", "Write the name out without the backslash.")),
            ("a default namespace spelt with a backslash", "@n\\61mespace url(http://www.w3.org/2000/svg);\n" + whole, 2,
             ("Could not read the stylesheet: Line 1 of the stylesheet writes a name with a backslash (`@n\\61mespace`).",)),
            ("a registration spelt with a backslash", whole + "@\\70roperty --bg { syntax: '<length>'; inherits: false; initial-value: 0px; }\n", 2,
             ("Could not read the stylesheet: Line 89 of the stylesheet writes a name with a backslash (`@\\70roperty`).",)),
            ("a class name with an escaped colon", whole + "\n.sm\\:flex { display: flex }\n", 2,
             ("Line 90 of the stylesheet writes a name with a backslash (`.sm\\:flex`).", "(a class name with a colon in it), move that rule into another stylesheet.")),
            ("a string that a hex escape carries over a line end", whole.replace("  --bg: #ffffff;", '  --x: "a\\41\n; --bg: #111111; " ; /*"*/\n  --bg: #ffffff;', 1), 2,
             ('Could not read the stylesheet: Line 15 of the stylesheet has a string that runs over the end of its line (`"a\\41`:', "Write the string on one line.")),
            ("a string carried over a line end by a backslash", whole.replace(":root {\n", ':root {\n  --note: "a\\\nb";\n', 1), 2,
             ('Could not read the stylesheet: Line 8 of the stylesheet has a string that runs over the end of its line (`"a\\`:',)),
            ("the light block inside round brackets", "( a{} " + whole[:whole.index(dark)] + ") a{}\n" + whole[whole.index(dark):], 2,
             ("Cannot check the palette: The stylesheet's brackets do not pair up: the `(` on line 1 is still open where the `{` on line 1 opens a block", "Nothing was written.")),
            ("a string over a line end that leaves a brace open to this reading", whole + "\nb { c: 'y\\41\n' }\n", 2,
             ("Cannot check the palette: Line 90 of the stylesheet has a string that runs over the end of its line (`'y\\41`:", "Nothing was written.")),
            ("a saturation over 100%", whole.replace("  --muted: #a6abce;", "  --muted: hsl(233 150% 73%);", 1), 2,
             ("Could not read the stylesheet: --muted in the :root[data-theme=\"dark\"] block: The colour 'hsl(233 150% 73%)' is not one this check can read (the saturation or the lightness "
              "of hsl() is over 100%). Write it as #rrggbb, rgb(), hsl(), oklch() or a CSS colour name.",)),
            # what was "not there", or took twelve seconds
            ("a byte order mark first", "\ufeff" + whole, 0, ("30 of 30 pairs pass.",)),
            ("128 KB of blocks in brackets in a value", whole + "\nbody { --x:" + "(" * 32000 + "{}" * 32000 + ")" * 32000 + "; }\n", 0, ("30 of 30 pairs pass.",)),
        )
        for name, text, want, parts in cases:
            with self.subTest(name=name):
                code, out, err = run("palette", doc, "--css", self.css(text))
                self.assertEqual((code, err), (want, ""), out)
                for part in parts:
                    self.assertIn(part, out)
                if want == 0:
                    self.assertNotIn("stylesheet", out.replace("the stylesheet given", ""))
                data = json.loads(run("palette", doc, "--css", self.css(text), "--json")[1])
                self.assertEqual((data["exit"], data["status"]), (want, "pass" if want == 0 else "unreadable" if parts[0].startswith("Cannot") else "incomplete"))

    def test_neither_shape_that_round_5_found_slow_stalls_the_command(self):
        # 128 KB of blocks inside brackets in a value took 12 seconds of processor time, and a megabyte of value cells that are one run of
        # underscores 5.6: both far under the megabyte the command reads. Measured here as the processor time of the command itself
        # (where the system counts it for a child: elsewhere the two runs only have to end as they should).
        whole = T.read(os.path.join(self.dir, "global.css"))
        sheet = self.css(whole + "\nbody { --x:" + "(" * 64000 + "{}" * 64000 + ")" * 64000 + "; }\n")
        rows = self.write("### Light theme\n" + ("|x|" + "_" * 1990 + "\n") * 525, name="rows.md")  # (just under the megabyte the command reads)
        for name, args, want in (("256 KB of blocks in brackets in a value", (self.write(brand_md()), "--css", sheet), 0), ("a megabyte of cells that are runs of underscores", (rows,), 2)):
            with self.subTest(name=name):
                before = os.times()
                code, out, err = run("palette", *args)
                after = os.times()
                took = (after.children_user + after.children_system) - (before.children_user + before.children_system)
                self.assertEqual((code, err), (want, ""), out[:300])
                self.assertIn("30 of 30 pairs pass." if want == 0 else "No row of a palette was found where this check looks for one.", out)
                self.assertLess(took, 3.0, "the command took %.2f s of processor time" % took)

    def test_a_stylesheet_that_brings_in_another_one_is_told_so_in_a_note_and_the_exit_status_stays(self):
        # round 5: `@import url("data:text/css,html:root{--bg:%23ff0000}");` sets the page's background in a browser, and nothing said so
        whole = T.read(os.path.join(self.dir, "global.css"))
        doc = self.write(brand_md())
        note = ("line 1 of the stylesheet brings in another stylesheet (`@import url(\"./fonts.css\");`), which this check does not read. If that one sets the site's colours, "
                "the page can show other colours than these.")
        code, out, err = run("palette", doc, "--css", self.css('@import url("./fonts.css");\n' + whole))
        self.assertEqual((code, err), (0, ""), out)
        self.assertEqual([l for l in out.splitlines() if l.startswith("Note: ")], ["Note: " + note])
        self.assertNotIn("Could not read the stylesheet", out)
        data = json.loads(run("palette", doc, "--css", self.css('@import url("./fonts.css");\n' + whole), "--json")[1])
        self.assertEqual((data["exit"], data["status"], data["notes"], data["stylesheet_problems"]), (0, "pass", [note], []))
        # several: the first is named and the rest are counted; and the note stands beside whatever else is said, with that thing's exit status
        three = "@import url(\"./fonts.css\");\n@import 'a.css';\n@import 'b.css' screen;\n" + whole
        code, out, err = run("palette", doc, "--css", self.css(three))
        self.assertEqual((code, [l for l in out.splitlines() if l.startswith("Note: ")]), (0, ["Note: " + note, "Note: 2 more statements like it bring in other stylesheets; the next is on line 2."]), out)
        code, out, err = run("palette", self.write(brand_md(dark={}), name="half.md"), "--css", self.css(three.replace("  --bg: #ffffff;", "  --bg: #ffffff !important;", 1)))
        self.assertEqual(code, 2, out)
        self.assertIn("Note: " + note, out)
        self.assertIn("Could not read the stylesheet: --bg in the :root block:", out)
        data = json.loads(run("palette", self.write(brand_md(dark={}), name="half.md"), "--json")[1])
        self.assertEqual(data["notes"], [], "without --css there is no stylesheet to say it of")
        # with no Primary both notes are said, the palette's first
        code, out, err = run("palette", self.write("".join(brand_md().partition("### Light theme")[1:]), name="no-primary.md"), "--css", self.css('@import url("./fonts.css");\n' + whole), "--json")
        self.assertEqual(json.loads(out)["notes"][1:], [note], out)
        self.assertEqual(len(json.loads(out)["notes"]), 2)
        # a stylesheet without one has no such note
        self.assertNotIn("brings in", run("palette", doc, "--css", os.path.join(self.dir, "global.css"))[1])

    # --- round 4: no text in a cell or a stylesheet value ends in a traceback ------------------------

    BIG = ("oklch(0.5 10000000000e99 0)", "rgb(%s,0,0)" % ("9" * 400), "oklch(%s 0 0)" % ("9" * 200), "hsl(%s 50%% 50%%)" % ("9" * 1000), "rgb(0 0 %se99)" % ("9" * 310))

    def test_a_number_too_long_or_too_large_in_a_cell_or_in_the_stylesheet_is_a_value_that_cannot_be_read_never_a_traceback(self):
        whole = T.read(os.path.join(self.dir, "global.css"))
        for value in self.BIG:
            with self.subTest(value=value[:30], where="a cell"):
                code, out, err = run("palette", self.write(brand_md(dark=dict(STARTER_DARK, muted=value))))
                self.assertEqual((code, err), (2, ""), out)
                self.assertNotIn("Traceback", out)
                self.assertIn("Could not read a value: Muted (dark theme): ", out)
                self.assertRegex(out, "the second cell holds|lies outside the colours a screen can show")
            with self.subTest(value=value[:30], where="the stylesheet"):
                code, out, err = run("palette", self.write(brand_md()), "--css", self.css(whole.replace("--muted: #5a5a72;", "--muted: %s;" % value, 1)))
                self.assertEqual((code, err), (2, ""), out)
                self.assertIn("Could not read the stylesheet: --muted in the :root block: ", out)
            with self.subTest(value=value[:30], where="a line of text, a note and a heading"):
                text = brand_md().replace("| Muted | `#a6abce` |", "| Muted | `#a6abce` | was %s |" % value) + "\nOld: %s\n\n### Notes %s\n" % (value, value)
                code, out, err = run("palette", self.write(text))
                self.assertEqual((code, err), (2, ""), out)
                self.assertEqual(len([l for l in out.splitlines() if l.startswith("Not read: Line ")]), 2, out)

    def test_the_install_refuses_such_a_palette_and_such_a_stylesheet_in_words_too(self):
        script = [sys.executable, SCRIPT, "install", "--test-command", "true", "--dry-run"]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        for value in self.BIG:
            for where in ("BRAND.md", "the stylesheet"):
                with self.subTest(value=value[:30], where=where), tempfile.TemporaryDirectory() as tmp:
                    site = T.make_starter_site(os.path.join(tmp, "site"), with_modules=False)
                    with open(os.path.join(site, "BRAND.md"), "w", encoding="utf-8") as f:
                        f.write(brand_md(light=T.BAKERY_LIGHT, dark=dict(T.BAKERY_DARK, muted=value) if where == "BRAND.md" else T.BAKERY_DARK, primary="#b4531a"))
                    if where == "the stylesheet":
                        sheet = os.path.join(site, "src", "styles", "global.css")
                        with open(sheet, "w", encoding="utf-8") as f:
                            f.write(T.starter_file("src/styles/global.css").replace("--shadow: 0 1px 2px rgba(0, 0, 0, 0.06)", "--shadow: 0 1px 2px %s" % value, 1)
                                    .replace("  --muted: #a6abce;", "  --muted: %s;" % value, 1))
                    r = subprocess.run(script + ["--site", site, "--with-colours"], capture_output=True, text=True, encoding="utf-8", env=env)
                    self.assertEqual(r.stderr, "", "no traceback")
                    self.assertNotIn("Traceback", r.stdout)
                    # in BRAND.md it is a value that cannot be read; in the stylesheet the old value is written over, whatever it was
                    self.assertEqual(r.returncode, 2 if where == "BRAND.md" else 0, r.stdout)

    def test_the_install_stops_on_what_round_5_found_in_a_stylesheet_and_writes_over_a_value_that_only_looks_like_the_colour(self):
        # the same stylesheets through the other door, as a dry run: where the check names a problem of the stylesheet as a whole the
        # install does not write, with the check's own sentence; a value with a no-break space beside it is no colour, and is written over
        script = [sys.executable, SCRIPT, "install", "--test-command", "true", "--dry-run", "--with-colours"]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        whole = T.starter_file("src/styles/global.css")
        dark = ':root[data-theme="dark"]'
        cases = (("a class name with an escaped colon", whole + "\n.sm\\:flex { display: flex }\n", 2, "Line 90 of the stylesheet writes a name with a backslash (`.sm\\:flex`)."),
                 ("url( spelt with a backslash", whole.replace("  --bg: #ffffff;", "  --bg: #ffffff;\n  --x: u\\72l(a'b); --bg: #ff0000; /*'*/ );", 1), 2, "writes a name with a backslash (`u\\72l(a'b)`)."),
                 ("a string carried over a line end", whole.replace("  --bg: #ffffff;", '  --x: "a\\41\n; --bg: #111111; " ; /*"*/\n  --bg: #ffffff;', 1), 2,
                  "Line 15 of the stylesheet has a string that runs over the end of its line"),
                 ("the light block inside round brackets", "( a{} " + whole[:whole.index(dark)] + ") a{}\n" + whole[whole.index(dark):], 2,
                  "the `(` on line 1 is still open where the `{` on line 1 opens a block"),
                 ("128 KB of blocks in brackets in the :root block", whole.replace("  --bg: #ffffff;", "  --bg: #ffffff;\n  --x:" + "(" * 32000 + "{}" * 32000 + ")" * 32000 + ";", 1), 2,
                  "The :root block holds another block inside it"),
                 ("a no-break space before the light background", whole.replace("  --bg: #ffffff;", "  --bg:\u00a0#ffffff;", 1), 0, "src/styles/global.css"),
                 ("a byte order mark first", "\ufeff" + whole, 0, "src/styles/global.css"))
        for name, text, want, part in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                site = T.make_starter_site(os.path.join(tmp, "site"), with_modules=False)
                with open(os.path.join(site, "BRAND.md"), "w", encoding="utf-8") as f:
                    f.write(brand_md(light=T.BAKERY_LIGHT, dark=T.BAKERY_DARK, primary="#b4531a"))
                sheet = os.path.join(site, "src", "styles", "global.css")
                with open(sheet, "w", encoding="utf-8", newline="") as f:
                    f.write(text)
                before = T.read_bytes(sheet)
                r = subprocess.run(script + ["--site", site], capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
                self.assertEqual((r.returncode, r.stderr), (want, ""), r.stdout)
                self.assertIn(part, r.stdout)
                self.assertEqual(T.read_bytes(sheet), before, "a dry run, and a refusal, write nothing")


if __name__ == "__main__":
    unittest.main()
