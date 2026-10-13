"""Scenarios 4, 5, 6, 25, 26 and 27: what the three prompts and the words around them must hold.

The prompts are judgement, written by the assistant from these templates; what a test can hold on to is the
part that must never drift: the slots, the counts (three palettes, five variations), the table the check
reads, the lines an owner must be told, and that no tool is named outside the one dated file.
"""

import os
import re
import unittest

import _testutil as T
import _palette

SKILL = os.path.join(T.SCRIPTS, "..")
TOOL_NAMES = re.compile(
    r"\b(claude|anthropic|chatgpt|openai|gpt|gemini|copilot|midjourney|dall-?e|firefly|canva|figma|adobe|"
    r"illustrator|recraft|ideogram|leonardo|stable diffusion|looka|inkscape)\b", re.I)


def skill_file(*rel):
    return T.read(os.path.join(SKILL, *rel))


def prompt_of(text):
    """The part the owner is given: what stands between the two markers."""
    parts = re.findall(r"<!-- prompt:start -->\n(.*?)<!-- prompt:end -->", text, re.S)
    assert len(parts) == 1, "a template has exactly one prompt, between prompt:start and prompt:end"
    return parts[0]


def words_of(text):
    return text.split("<!-- prompt:end -->", 1)[1]


def slots(text):
    return set(re.findall(r"\[([A-Z][A-Z ]*)\]", text))


class Palette(unittest.TestCase):
    def setUp(self):
        self.text = skill_file("templates", "palette-prompt.md")
        self.prompt = prompt_of(self.text)
        self.tables = self.prompt[self.prompt.index("### Brand"):self.prompt.index("Rules for every palette")]

    def test_scenario_4_it_asks_for_three_palettes_and_carries_the_business_and_her_likes(self):
        self.assertIn("THREE different colour palettes", self.prompt)
        self.assertEqual(slots(self.prompt), {"WHAT THE BUSINESS DOES", "WHO IT IS FOR", "WHAT MAKES IT DIFFERENT", "THE FEEL",
                                              "COLOURS I LIKE", "COLOURS TO AVOID", "A BRAND OR PLACE"})

    def test_the_table_it_asks_for_is_the_table_the_check_reads(self):
        # filled in with any colour, the prompt's own tables are a complete palette: nothing missing, nothing ignored
        # what a tool hands back, and she pastes: the three tables, not the prompt's own sentences
        filled = self.tables.replace("`#...`", "`#123456`")
        p = _palette.parse_tables(filled)
        self.assertEqual(p.missing(), [])
        self.assertEqual(p.problems, [])
        self.assertEqual(p.ignored, [])
        self.assertEqual(p.brand, "#123456")
        self.assertEqual(set(p.light), set(_palette.KEYS))
        self.assertEqual(set(p.dark), set(_palette.KEYS))

    def test_every_row_is_named_as_the_check_names_it(self):
        rows = re.findall(r"(?m)^\| ([A-Z][^|]*?) \| `#\.\.\.` \|", self.prompt)
        self.assertEqual(rows, [_palette.LABEL["brand"]] + [_palette.LABEL[k] for k in _palette.KEYS] * 2)

    def test_the_doc_template_an_owner_fills_has_the_same_tables_row_for_row(self):
        # BRAND.md is where the chosen palette is pasted, and what the intake reads
        template = T.read(T.BRAND_TEMPLATE)
        rows = re.findall(r"(?m)^\| ([A-Z][^|]*?) \| `#\[…\]` \|", template)
        self.assertEqual(rows, [_palette.LABEL["brand"]] + [_palette.LABEL[k] for k in _palette.KEYS] * 2)
        headings = re.findall(r"(?m)^### (.+)$", template[template.index("## Colour palette"):template.index("## Typography")])
        self.assertEqual(headings, re.findall(r"(?m)^### (.+)$", self.prompt))

    def test_the_headings_and_row_names_stay_in_english_whatever_language_the_prompt_is_written_in(self):
        # the check reads those words: with "Helles Design" for "Light theme" every row counts as missing
        self.assertIn("Keep the three headings, the header row of each table (`| Token | Hex |`) and the row names exactly as they are, in English", self.prompt)
        self.assertIn("EXCEPT the three table headings, the header row `| Token | Hex |`", self.text)
        self.assertIn("**Translate the sentences, never the table:**", skill_file("SKILL.md"))
        german = self.tables.replace("`#...`", "`#123456`").replace("### Light theme", "### Helles Design").replace("### Dark theme", "### Dunkles Design")
        self.assertEqual(len(_palette.parse_tables(german).missing()), 18)
        # and a header row in another language loses the table too
        hexwert = _palette.parse_tables(self.tables.replace("`#...`", "`#123456`").replace("| Token | Hex |", "| Token | Hexwert |"))
        self.assertEqual(len(hexwert.missing()), 18)

    def test_the_prompt_states_the_threshold_the_check_holds_it_to(self):
        self.assertIn("at least 4.5 to 1", self.prompt)
        self.assertEqual(_palette.NEED_TEXT, 4.5)
        for label in ("Heading", "Body", "Muted", "Accent", "Link", "Background", "Soft background", "Surface"):
            self.assertIn(label, self.prompt.split("Rules for every palette")[1])


class Logo(unittest.TestCase):
    def setUp(self):
        self.text = skill_file("templates", "logo-prompt.md")
        self.prompt = prompt_of(self.text)

    def test_scenario_5_five_variations_with_the_chosen_colours_inside(self):
        self.assertIn("FIVE different variations", self.prompt)
        self.assertLessEqual({"PRIMARY", "ACCENT", "LIGHT BACKGROUND", "DARK BACKGROUND"}, slots(self.prompt))
        self.assertIn("Draw the mark with these colours and no others", self.prompt)

    def test_the_two_pages_are_what_the_mark_sits_on_not_colours_to_paint_with(self):
        # a shape painted in a page's own colour cannot be seen on that page: the intake would question it
        draw, sits = self.prompt.split("The mark will sit on two pages")
        self.assertIn("[PRIMARY]", draw)
        self.assertIn("[ACCENT]", draw)
        self.assertNotIn("BACKGROUND]", draw)
        self.assertIn("Do not paint any shape in those two colours", sits)
        self.assertIn("do not put a background shape behind the mark", sits)

    def test_it_asks_for_what_the_intake_can_read_and_nothing_it_refuses(self):
        for clause in ("each one written out", "no masks", "no reused shapes", "as a plain number (no mm, pt or em)", "as a hex value"):
            self.assertIn(clause, self.prompt)

    def test_scenario_5_what_each_variation_must_be(self):
        for clause in ("SVG", "16 pixels", "a single colour", "viewBox", "No text of any kind", "no gradients", "no transparency"):
            self.assertIn(clause, self.prompt)

    def test_scenario_5_it_says_what_to_do_if_the_tool_cannot_draw_a_vector(self):
        self.assertIn("If you cannot draw a vector (SVG), tell me so now instead of making a picture", self.prompt)
        self.assertIn("cannot draw a vector", words_of(self.text))

    def test_scenario_6_the_owner_is_told_about_rights_and_lookalikes_and_that_it_is_not_legal_advice(self):
        words = words_of(self.text)
        self.assertIn("terms for commercial use", words)
        self.assertIn("lookalike", words)
        self.assertIn("not legal advice", words)


class Handover(unittest.TestCase):
    def setUp(self):
        self.text = skill_file("templates", "handover-prompt.md")
        self.prompt = prompt_of(self.text)

    def test_scenario_26_it_asks_for_a_package_of_the_one_variation_she_picked(self):
        self.assertEqual(slots(self.prompt), {"N"})
        self.assertIn("that one variation only", self.prompt)
        for clause in ("zip", "SVG file in the colours", "single colour", "README"):
            self.assertIn(clause, self.prompt)

    def test_scenario_26_she_saves_it_where_she_likes_and_can_paste_the_code_instead(self):
        words = words_of(self.text)
        self.assertIn("wherever she likes", words)
        self.assertIn("full path", words)
        self.assertIn("paste the code", words)

    def test_scenario_27_nothing_is_ever_searched_for(self):
        self.assertIn("Never search her Downloads folder", words_of(self.text))
        self.assertIn("Never search her Downloads folder", skill_file("SKILL.md"))


class NoToolIsNamed(unittest.TestCase):
    def test_the_prompts_the_skill_file_and_the_scripts_messages_name_no_tool(self):
        for rel in (("templates", "palette-prompt.md"), ("templates", "logo-prompt.md"), ("templates", "handover-prompt.md"), ("SKILL.md",)):
            with self.subTest(file="/".join(rel)):
                text = skill_file(*rel).replace(".claude/skills/", "")  # where a skill is installed, not a tool to paste into
                self.assertIsNone(TOOL_NAMES.search(text), TOOL_NAMES.search(text))

    def test_the_one_file_that_names_a_tool_says_when_it_was_checked(self):
        text = skill_file("references", "where-to-paste.md")
        self.assertRegex(text, r"\*\*Checked on \d{4}-\d{2}-\d{2}\.\*\*")
        self.assertIsNotNone(TOOL_NAMES.search(text))


class TheSkillFile(unittest.TestCase):
    def setUp(self):
        self.text = skill_file("SKILL.md")

    def test_scenario_25_she_is_asked_what_she_likes_before_any_palette_prompt(self):
        ask, palette = self.text.index("## 2. Ask what colours she likes"), self.text.index("## 3. The palette")
        self.assertLess(ask, palette)
        section = self.text[ask:palette]
        self.assertIn("Write no prompt until she has", section)
        self.assertIn("Surprise me", section)

    def test_the_question_is_asked_in_one_place_and_never_as_a_pitch(self):
        self.assertEqual(self.text.count("Do you already have a logo"), 1)
        self.assertIn("This text lives here, once.", self.text)

    def test_every_flag_and_command_it_names_is_one_the_script_has(self):
        import brand_intake
        source = T.read(brand_intake.__file__)
        for flag in set(re.findall(r"(?<![\w-])--[a-z][a-z-]+", self.text)):
            with self.subTest(flag=flag):
                if flag == "--include" or flag in _palette.VARIABLE.values():
                    continue  # npm's own flag; the stylesheet's variables
                self.assertIn('"%s"' % flag, source, "SKILL.md names a flag the script does not have")
        for command in re.findall(r"brand_intake\.py (\w+)", self.text):
            self.assertIn(command, ("palette", "install"))

    def test_every_command_names_the_script_where_it_is_not_in_the_sites_own_scripts_folder(self):
        # the site has a scripts/ folder of its own, and the intake is not in it
        calls = re.findall(r"(\S*)brand_intake\.py[`\"]? (?:palette|install)", self.text)
        self.assertGreaterEqual(len(calls), 5)
        for prefix in calls:
            self.assertEqual(prefix, '"$KIT/scripts/', prefix)

    def test_the_starters_colours_it_names_are_the_starters_colours(self):
        # §0 gives them for a logo made before the project exists; a starter that changes its colours
        # must change this sentence too
        css = _palette.read_css(T.starter_file("src/styles/global.css"))
        row = [l for l in self.text.splitlines() if l.startswith("| no colours | a logo only |")]
        self.assertEqual(len(row), 1)
        self.assertEqual(css.problems, [])
        self.assertIn("`%s` and `%s`, on a white page and on `%s`" % (css.brand, css.light["accent"], css.dark["bg"]), row[0])
        self.assertEqual(css.light["bg"], "#ffffff")

    def test_the_header_row_is_named_wherever_the_words_that_stay_english_are(self):
        self.assertIn("the header\nrow `| Token | Hex |` and the row names stay in English", self.text)
        self.assertIn("the header row `| Token | Hex |`", skill_file("templates", "palette-prompt.md"))

    def test_the_seven_files_it_lists_are_the_seven_the_intake_makes(self):
        # the same seven test_icons.TheSevenFiles holds the intake to
        section = self.text[self.text.index("the seven icon files under `public/`"):]
        listed = re.findall(r"`([\w./-]+\.(?:svg|ico|png))`", section.split(")", 1)[0])
        self.assertEqual(sorted(listed), sorted(("favicon.svg", "favicon.ico", "apple-touch-icon.png", "icon-192.png", "icon-512.png",
                                                 "icon-maskable-512.png", "images/logo.png")))


if __name__ == "__main__":
    unittest.main()
