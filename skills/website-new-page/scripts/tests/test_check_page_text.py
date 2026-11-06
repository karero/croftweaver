"""Tests for check_page_text.py: did the build keep the approved text?

The fixture pair is a real Astro 7.4.2 build's markup (head, JSON-LD, sections, byline, entities,
footer) with every word of its text replaced by made-up copy, and the draft written by hand from
that copy: see fixtures/README.md. Expected lines below were written by hand from the draft, not
copied from the script's output.

Run: python3 -m unittest discover -s skills/website-new-page/scripts/tests
"""
import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "check_page_text.py")
FIX = os.path.join(HERE, "fixtures")
DRAFT = os.path.join(FIX, "astro-7.4.2_built-page_approved-draft.md")
PAGE = os.path.join(FIX, "astro-7.4.2_built-page_shape-capture.html")
FLAGS = ["--title-suffix", " | Corner Loaf", "--skip", "nav,footer,aside,.byline,.btn-row"]

spec = importlib.util.spec_from_file_location("check_page_text", SCRIPT)
cpt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cpt)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, text):
        p = os.path.join(self.tmp.name, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def run_check(self, draft, page, flags=FLAGS):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cpt.main([draft, page] + flags)
        return code, out.getvalue(), err.getvalue()

    def changed_page(self, old, new):
        html = read(PAGE)
        self.assertIn(old, html, "the test's edit does not apply to the fixture")
        return self.write("page.html", html.replace(old, new, 1))

    def changed_draft(self, old, new):
        doc = read(DRAFT)
        self.assertIn(old, doc, "the test's edit does not apply to the draft")
        return self.write("draft.md", doc.replace(old, new, 1))


class KeptText(Base):
    def test_the_real_build_keeps_the_text(self):
        # Why: the owner's list of changed sentences must be empty when nothing changed. Typographic
        # apostrophe, &#39;, &amp;, &deg;, &ndash;, indentation and line breaks all differ in form.
        code, out, err = self.run_check(DRAFT, PAGE)
        self.assertEqual((code, err), (0, ""), out)
        self.assertIn("draft: 25 sentences, 2 FAQ; built: 25 sentences, 2 FAQ in the schema", out)
        self.assertIn("The build kept the approved text.", out)

    def test_command_line_entry_point(self):
        # Why: SKILL.md tells the builder to run the script from a shell; the exit code is the contract.
        r = subprocess.run([sys.executable, "-I", SCRIPT, DRAFT, PAGE] + FLAGS, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_site_chrome_the_draft_never_held_is_listed_unless_skipped(self):
        # Why: byline and button are page parts the owner did not approve as copy; without
        # --skip they must show, so the owner can see them.
        code, out, _ = self.run_check(DRAFT, PAGE, flags=["--title-suffix", " | Corner Loaf"])
        self.assertEqual(code, 1)
        self.assertIn('ADDED (in the page, not in the draft): "By Jo Baker · Published 1 July 2026"', out)
        self.assertIn('ADDED (in the page, not in the draft): "Buy a starter kit"', out)
        self.assertNotIn("CHANGED", out)
        self.assertNotIn("Home", out)   # nav, footer and head text are never body copy

    def test_a_separator_with_no_letters_is_not_a_sentence(self):
        # Why: a lone "·" or "|" between components is decoration; listing it buries the real changes.
        page = self.changed_page("<h2 id=\"signs\">", "<p>&middot;</p><p>|</p><h2 id=\"signs\">")
        self.assertEqual(self.run_check(DRAFT, page)[0], 0)

    def test_head_and_style_text_is_not_page_text(self):
        # Why: a <style> or <script> body read as copy would flood every report.
        page = self.changed_page("<style>.hero", "<style>This is css and not copy. .hero")
        self.assertEqual(self.run_check(DRAFT, page)[0], 0)


class ChangedText(Base):
    def test_a_changed_word_lists_both_sentences(self):
        page = self.changed_page("Most starters are lively again in three days.",
                                 "Most starters are lively again in a week.")
        code, out, _ = self.run_check(DRAFT, page)
        self.assertEqual(code, 1)
        self.assertIn('CHANGED (in the draft, not in the page): "Most starters are lively again in three days."', out)
        self.assertIn('ADDED (in the page, not in the draft): "Most starters are lively again in a week."', out)
        self.assertEqual(out.count("CHANGED"), 1)
        self.assertEqual(out.count("ADDED"), 1)

    def test_a_dropped_sentence_is_only_changed(self):
        page = self.changed_page(" A sharp smell of nail polish means\n        it is very hungry.", "")
        code, out, _ = self.run_check(DRAFT, page)
        self.assertEqual(code, 1)
        self.assertIn('"A sharp smell of nail polish means it is very hungry."', out)
        self.assertNotIn("ADDED", out)

    def test_a_dash_is_not_folded(self):
        # Why: only whitespace, entities and quotes are folded; a swapped dash is a real change.
        page = self.changed_page("A clean jar &ndash; never", "A clean jar - never")
        code, out, _ = self.run_check(DRAFT, page)
        self.assertEqual(code, 1)
        self.assertIn('"A clean jar – never a tight lid"', out)
        self.assertIn('"A clean jar - never a tight lid"', out)

    def test_a_sentence_the_draft_has_twice_must_be_built_twice(self):
        doc = read(DRAFT).replace("## Signs it is unhappy\n", "## Signs it is unhappy\n\nPatience pays.\n\nPatience pays.\n", 1)
        draft = self.write("draft.md", doc)
        page = self.changed_page("<h2 id=\"signs\">Signs it is unhappy</h2>",
                                 "<h2 id=\"signs\">Signs it is unhappy</h2><p>Patience pays.</p>")
        code, out, _ = self.run_check(draft, page)
        self.assertEqual(code, 1)
        self.assertEqual(out.count('CHANGED (in the draft, not in the page): "Patience pays."'), 1)

    def test_title_description_and_faq_schema(self):
        page = self.changed_page("<title>How to Keep", "<title>How To Keep")
        self.assertIn('DIFFERENT title: draft "How to Keep a Sourdough Starter Alive" / built "How To Keep a Sourdough Starter Alive"',
                      self.run_check(DRAFT, page)[1])
        page = self.changed_page("how to bring it back.\"", "how to bring it back soon.\"")
        self.assertIn("DIFFERENT description:", self.run_check(DRAFT, page)[1])
        page = self.changed_page("feed it twice a day for three days.\"}", "feed it daily.\"}")
        code, out, _ = self.run_check(DRAFT, page)
        self.assertEqual(code, 1)
        self.assertIn('DIFFERENT FAQ schema: draft has "Can a neglected starter be saved?"', out)
        self.assertIn('DIFFERENT FAQ schema: built has "Can a neglected starter be saved?" / "Usually yes. Pour off the grey liquid, discard most of it, and feed it daily."', out)

    def test_a_page_without_faq_schema_differs_from_a_draft_with_one(self):
        html = read(PAGE)
        start = html.index('<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage"')
        page = self.write("page.html", html[:start] + html[html.index("</script>", start) + 9:])
        code, out, _ = self.run_check(DRAFT, page)
        self.assertEqual(code, 1)
        self.assertEqual(out.count("DIFFERENT FAQ schema: draft has"), 2)


class Folding(Base):
    def test_folds_whitespace_entities_and_quotes_but_nothing_else(self):
        draft = self.write("d.md", "## Draft\n\nTitle: Tom's \"Best\" Bread\nDescription: Rye &amp; wheat, no fuss.\n\n# It’s   a  “loaf”\n")
        page = self.write("p.html", "<html><head><title>Tom&#39;s &quot;Best&quot; Bread</title>"
                          "<meta name=\"description\" content=\"Rye &amp;amp; wheat, no fuss.\"></head>"
                          "<body><main><h1>It's\n a &quot;loaf&quot;</h1></main></body></html>")
        # The description's attribute holds the text "Rye &amp; wheat" (an escaped ampersand
        # shown literally), so it must differ from the draft's "Rye & wheat".
        code, out, _ = self.run_check(draft, page, flags=[])
        self.assertEqual(code, 1)
        self.assertIn('DIFFERENT description: draft "Rye & wheat, no fuss." / built "Rye &amp; wheat, no fuss."', out)
        self.assertNotIn("title", out)
        self.assertNotIn("CHANGED", out)

    def test_markdown_syntax_is_not_text(self):
        draft = self.write("d.md", "## Draft\n\nTitle: T\nDescription: D\n\n# H\n\nSome *quiet* and **loud** words, `code`, [a link](/x), ![alt text](/i.png) end.\n")
        page = self.write("p.html", "<html><head><title>T</title><meta name=\"description\" content=\"D\"></head>"
                          "<body><main><h1>H</h1><p>Some <em>quiet</em> and <strong>loud</strong> words, <code>code</code>, <a href=\"/x\">a link</a>,  end.</p></main></body></html>")
        code, out, _ = self.run_check(draft, page, flags=[])
        self.assertEqual(code, 0, out)


class RefusesWhatItCannotRead(Base):
    def test_exit_2_and_a_stderr_line(self):
        cases = {
            "no Draft heading": ("# Plan\n\nTitle: T\n", "no \"## Draft\" heading"),
            "no title line": ("## Draft\n\nDescription: D\n\n# H\n", "must start with"),
            "no description line": ("## Draft\n\nTitle: T\n\n# H\n", "must start with"),
        }
        for name, (doc, why) in cases.items():
            with self.subTest(name):
                code, out, err = self.run_check(self.write("d.md", doc), PAGE)
                self.assertEqual(code, 2)
                self.assertIn(why, err)
                self.assertEqual(out, "")

    def test_unreadable_built_page_and_missing_head_parts(self):
        code, _, err = self.run_check(DRAFT, os.path.join(self.tmp.name, "nope.html"))
        self.assertEqual(code, 2)
        self.assertIn("nope.html", err)
        page = self.write("p.html", "<html><body><main><h1>H</h1></main></body></html>")
        code, _, err = self.run_check(DRAFT, page)
        self.assertEqual(code, 2)
        self.assertIn("no <title> or no meta description", err)

    def test_broken_json_ld_is_not_read_as_no_faq(self):
        # Why: a FAQ block the script cannot parse must not look like a page with no FAQ.
        page = self.changed_page('"@type":"FAQPage","mainEntity":[', '"@type":"FAQPage","mainEntity":[,')
        code, _, err = self.run_check(DRAFT, page)
        self.assertEqual(code, 2)
        self.assertIn("JSON-LD", err)


if __name__ == "__main__":
    unittest.main()
