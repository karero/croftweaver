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


class ReviewRound1(Base):
    """Cases found by the DIFF review's first round; each fails on the script as first built."""

    PAGE_HEAD = ('<html><head><title>T</title><meta name="description" content="D"></head><body>')
    DOC = "## Draft\n\nTitle: T\nDescription: D\n\n# H\n\nHello there.\n"

    def test_an_empty_main_is_still_the_page_body(self):
        # Why: text outside <main> is site chrome. An empty <main> must not make the check read the
        # whole body, or a build that lost all the copy would pass on the chrome's own sentences.
        page = self.write("p.html", self.PAGE_HEAD + "<main></main><p>Hello there.</p></body></html>")
        code, out, _ = self.run_check(self.write("d.md", self.DOC), page, [])
        self.assertEqual(code, 1, out)
        self.assertIn('CHANGED (in the draft, not in the page): "Hello there."', out)

    def test_faq_schema_text_is_folded_like_the_page(self):
        # Why: a build may write the answer as HTML text: &#39; for an apostrophe and inline tags
        # around words. The reader sees the same words, so the check must not report a change.
        page = self.changed_page("A starter that's fed on time",
                                 "A <b>starter</b> that&#39;s fed on time")
        code, out, err = self.run_check(DRAFT, page)
        self.assertEqual((code, err), (0, ""), out)

    def test_inline_tags_join_words_and_block_tags_split_them_in_a_faq_answer(self):
        # Why: <b> inside a word shows the reader one word; <p> inside it shows two.
        page = self.changed_page("Pour off the grey liquid", "Pour off the gr<b>ey</b> liquid")
        self.assertEqual(self.run_check(DRAFT, page)[0], 0)
        page = self.changed_page("Pour off the grey liquid", "Pour off the gr<p>ey liquid")
        code, out, _ = self.run_check(DRAFT, page)
        self.assertEqual(code, 1, out)
        self.assertIn("FAQ schema", out)

    def test_a_comment_or_a_quoted_greater_than_in_a_faq_answer_is_not_text(self):
        # Why: markup in the schema's answer is not words; a quoted ">" must not cut a tag short.
        page = self.changed_page("Pour off the grey liquid",
                                 "Pour off the <b title='1 > 0'>grey</b><!-- note --> liquid")
        code, out, err = self.run_check(DRAFT, page)
        self.assertEqual((code, err), (0, ""), out)

    def test_markup_python_3_9_cannot_parse_never_ends_in_a_traceback(self):
        # Why: Python 3.9's HTMLParser raises NotImplementedError on a bogus <![...]>; the CI leg
        # on 3.9 is where this fails if the conversion goes. run_check calls main() in this process,
        # so a raise fails the test; any exit code is fine.
        page = self.changed_page("Pour off the grey liquid", "Pour off the <![bogus]> grey liquid")
        self.assertIn(self.run_check(DRAFT, page)[0], (0, 1, 2))
        html = read(PAGE).replace("<main", "<![bogus]><main", 1)
        self.assertIn("<![bogus]>", html)
        self.assertIn(self.run_check(DRAFT, self.write("p.html", html))[0], (0, 1, 2))

    def test_faq_shapes_the_script_cannot_read_exit_2(self):
        # Why: a FAQPage the script cannot read must not look like a page with no FAQ, and must
        # not crash with a traceback.
        html = read(PAGE)
        for old, new in (('"mainEntity":[{"@type":"Question","name":"How often',
                          '"mainEntity":[null,{"@type":"Question","name":"How often'),
                         ('"name":"How often should I feed my starter?"', '"name":7'),
                         ('"mainEntity":[{"@type":"Question","name":"How often',
                          '"mainEntity":false,"x":[{"@type":"Question","name":"How often'),
                         ('"acceptedAnswer":{"@type":"Answer","text":"Once a day',
                          '"acceptedAnswer":[],"y":{"@type":"Answer","text":"Once a day'),
                         ('"acceptedAnswer":{"@type":"Answer","text":"Once a day',
                          '"acceptedAnswer":[{"@type":"Answer","text":"Once a day')):
            self.assertIn(old, html)
            page = self.write("p.html", html.replace(old, new, 1))
            code, _, err = self.run_check(DRAFT, page)
            self.assertEqual(code, 2, (new, err))
            self.assertIn("JSON-LD", err)

    def test_a_single_question_object_is_one_question(self):
        found, bad = cpt.faq_from_ld(
            ['{"@type":"FAQPage","mainEntity":{"@type":"Question","name":"Q?",'
             '"acceptedAnswer":{"text":"A."}}}'])
        self.assertEqual((found, bad), ([("Q?", "A.")], 0))

    def test_table_cells_and_code_lines_in_a_faq_answer_belong_to_the_answer(self):
        doc = ("## Draft\n\nTitle: T\nDescription: D\n\n## FAQ\n\n### Q?\n\nFirst part.\n\n"
               "| Cell A | Cell B |\n|---|---|\n\n```\ncode line\n```\n")
        _, _, _, faq = cpt.draft_of(doc)
        self.assertEqual(faq, [("Q?", "First part. Cell A Cell B code line")])

    def test_a_closing_hash_run_goes_but_a_hash_in_the_words_stays(self):
        doc = "## Draft\n\nTitle: T\nDescription: D\n\n## Learn C# ##\n\n## Why C#\n"
        _, _, blocks, _ = cpt.draft_of(doc)
        self.assertEqual(blocks, ["Learn C#", "Why C#"])


class InlineElementsInsideASentence(Base):
    """An icon or a hidden "(opens in a new tab)" note inside a sentence must not cut it in two.

    The markup is written by hand, not captured from a build, in the structure of a real
    external-link component (the `a.ext` with an inline `svg` icon and a `span.vh` in
    skills/website-launch-check/scripts/tests/fixtures/live-home-older-tag-2026-11-09.html). The
    words are made up. Expected lines were written by hand from the draft.
    """

    HEAD = '<html><head><title>T</title><meta name="description" content="D"></head><body>'
    DOC = ("## Draft\n\nTitle: T\nDescription: D\n\n# Meetups\n\n"
           "Sam also runs Bread Club, a monthly meetup. Read the Flour Rules. Then go on.\n")
    EXT = ('<a class="ext" href="{href}" target="_blank" rel="noopener">{text}'
           '<svg class="ext-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
           '<path fill="none" stroke="currentColor" d="M14 5h5v5"></path></svg>'
           '<span class="vh" lang="en"> (opens in a new tab)</span></a>')

    def page_with_links(self):
        body = ("<p>Sam also runs " + self.EXT.format(href="https://events.example.com", text="Bread Club")
                + ", a monthly meetup. Read the " + self.EXT.format(href="https://rules.example.com", text="Flour Rules")
                + ". Then go on.</p>")
        return self.write("p.html", self.HEAD + "<main><h1>Meetups</h1>" + body + "</main></body></html>")

    def test_a_skipped_note_inside_a_sentence_leaves_the_sentence_whole(self):
        # Why: the owner reads the list as it is; a sentence cut at every link showed as CHANGED plus
        # ADDED fragments, false lines that teach owners to ignore the list.
        # Through the command line, as the builder runs it.
        draft, page = self.write("d.md", self.DOC), self.page_with_links()
        r = subprocess.run([sys.executable, "-I", SCRIPT, draft, page, "--skip", ".vh"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("draft: 4 sentences, 0 FAQ; built: 4 sentences, 0 FAQ in the schema", r.stdout)

    def test_the_same_in_process_with_other_skipped_tags_beside_it(self):
        code, out, err = self.run_check(self.write("d.md", self.DOC), self.page_with_links(), ["--skip", "nav,footer,.vh"])
        self.assertEqual((code, err), (0, ""), out)

    def test_without_skip_the_note_stays_in_its_sentence_one_changed_and_one_added_line_per_link(self):
        # Why: the owner sees the note the build added, once, in the sentence it sits in; not as
        # two halves cut at the icon.
        code, out, _ = self.run_check(self.write("d.md", self.DOC), self.page_with_links(), ["--skip", ""])
        self.assertEqual(code, 1)
        self.assertIn('ADDED (in the page, not in the draft): '
                      '"Sam also runs Bread Club (opens in a new tab), a monthly meetup."', out)
        self.assertIn('ADDED (in the page, not in the draft): "Read the Flour Rules (opens in a new tab)."', out)
        self.assertEqual(out.count("CHANGED"), 2)
        self.assertEqual(out.count("ADDED"), 2)

    def test_two_words_that_touch_across_a_skipped_element_are_one_word(self):
        # Why: the reader sees "Pancakes"; the skipped text takes no place in the word.
        doc = "## Draft\n\nTitle: T\nDescription: D\n\n# H\n\nPancakes are good.\n"
        page = self.write("p.html", self.HEAD + '<main><h1>H</h1><p>Pan<span class="vh">x</span>cakes are good.</p></main></body></html>')
        self.assertEqual(self.run_check(self.write("d.md", doc), page, ["--skip", ".vh"])[0], 0)

    def test_a_line_break_inside_a_skipped_note_adds_no_space(self):
        # Why: the note's text drops out; a <br> inside it must not leave a gap in the word around it.
        doc = "## Draft\n\nTitle: T\nDescription: D\n\n# H\n\nPancakes are good.\n"
        page = self.write("p.html", self.HEAD + '<main><h1>H</h1><p>Pan<span class="vh">x<br>y</span>cakes are good.</p></main></body></html>')
        code, out, _ = self.run_check(self.write("d.md", doc), page, ["--skip", ".vh"])
        self.assertEqual(code, 0, out)

    def test_a_block_inside_a_skipped_inline_element_does_not_cut_the_text_before_it(self):
        # Why: a tag inside skipped content never cuts; if it did, it would clear "a" from the buffer.
        doc = "## Draft\n\nTitle: T\nDescription: D\n\n# H\n\nab\n"
        page = self.write("p.html", self.HEAD + '<main><h1>H</h1><p>a<span class="vh"><div>q</div></span>b</p></main></body></html>')
        code, out, _ = self.run_check(self.write("d.md", doc), page, ["--skip", ".vh"])
        self.assertEqual(code, 0, out)

    def test_an_icon_between_words_does_not_cut_them_apart(self):
        # Why: an svg is inline in the page; only its (never shown) content is hidden.
        doc = "## Draft\n\nTitle: T\nDescription: D\n\n# H\n\nOpen the settings page.\n"
        page = self.write("p.html", self.HEAD + '<main><h1>H</h1><p>Open the <svg viewBox="0 0 1 1"><title>gear</title></svg>settings page.</p></main></body></html>')
        code, out, _ = self.run_check(self.write("d.md", doc), page, [])
        self.assertEqual(code, 0, out)

    def test_an_image_or_input_between_words_does_not_cut_the_sentence(self):
        # Why: an img or input sits inside a sentence; cutting there reads one sentence as two and
        # shows false CHANGED and ADDED lines for a build that kept the draft's words.
        doc = "## Draft\n\nTitle: T\nDescription: D\n\n# H\n\nSee this here.\n\nType your name now.\n"
        page = self.write("p.html", self.HEAD + '<main><h1>H</h1><p>See <img src="a.png" alt=""> this here.</p>'
                          '<p>Type your <input name="n"> name now.</p></main></body></html>')
        code, out, _ = self.run_check(self.write("d.md", doc), page, [])
        self.assertEqual(code, 0, out)

    def test_a_skipped_block_still_cuts_the_text_around_it(self):
        # Why: a nav sits between two blocks of copy; they must stay two blocks, or its removal would
        # glue "menu" to "after" and every sentence around a skipped block would show as changed.
        doc = "## Draft\n\nTitle: T\nDescription: D\n\n# H\n\nBefore the menu\n\nafter the menu.\n"
        page = self.write("p.html", self.HEAD + "<main><h1>H</h1><div>Before the menu<nav>Home</nav>after the menu.</div></main></body></html>")
        code, out, _ = self.run_check(self.write("d.md", doc), page, ["--skip", "nav"])
        self.assertEqual(code, 0, out)
        self.assertIn("built: 3 sentences", out)   # heading + 2; a glued "Before the menuafter the menu." would make 2

    def test_a_skipped_inline_element_that_is_left_open_ends_with_its_parent(self):
        # Why: sloppy markup must not swallow the rest of the page.
        doc = "## Draft\n\nTitle: T\nDescription: D\n\n# H\n\nFirst part.\n\nSecond part.\n"
        page = self.write("p.html", self.HEAD + '<main><h1>H</h1><p>First part.<span class="vh">note</p><p>Second part.</p></main></body></html>')
        code, out, _ = self.run_check(self.write("d.md", doc), page, ["--skip", ".vh"])
        self.assertEqual(code, 0, out)


class HiddenTextSkippedByDefault(Base):
    """Screen-reader-only text is never copy the owner approved, so a plain run ignores it.

    The default cases enter through the command line with no --skip; the override case passes one.
    The markup is written by hand in the shape of the external-link component (see
    InlineElementsInsideASentence).
    """

    HEAD = InlineElementsInsideASentence.HEAD
    DOC = InlineElementsInsideASentence.DOC

    def page(self, cls, tag="span"):
        link = ('<a href="{h}" target="_blank" rel="noopener">{t}<{tag} class="{c}"> (opens in a new tab)</{tag}></a>')
        body = ("<p>Sam also runs " + link.format(h="https://events.example.com", t="Bread Club", c=cls, tag=tag)
                + ", a monthly meetup. Read the " + link.format(h="https://rules.example.com", t="Flour Rules", c=cls, tag=tag)
                + ". Then go on.</p>")
        return self.write("p.html", self.HEAD + "<main><h1>Meetups</h1>" + body + "</main></body></html>")

    def cli(self, page, *flags, doc=None):
        draft = self.write("d.md", doc or self.DOC)
        return subprocess.run([sys.executable, "-I", SCRIPT, draft, page, *flags], capture_output=True, text=True)

    def test_each_hidden_class_leaves_the_sentence_as_approved(self):
        # Why: before, every external link gave one false CHANGED and one false ADDED line.
        for cls in ("vh", "sr-only", "visually-hidden"):
            with self.subTest(cls=cls):
                r = self.cli(self.page(cls))
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn("built: 4 sentences", r.stdout)

    def test_a_hidden_class_next_to_other_classes_is_skipped_too(self):
        r = self.cli(self.page("sr-only extra"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_hidden_block_between_paragraphs_is_skipped(self):
        doc = "## Draft\n\nTitle: T\nDescription: D\n\n# H\n\nFirst part.\n\nSecond part.\n"
        page = self.write("p.html", self.HEAD + '<main><h1>H</h1><p>First part.</p>'
                          '<div class="sr-only">Skip to the form</div><p>Second part.</p></main></body></html>')
        r = self.cli(page, doc=doc)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_class_that_only_starts_like_a_hidden_one_is_still_read(self):
        # Why: the match is on the whole class name; visible copy must never be skipped by accident.
        doc = "## Draft\n\nTitle: T\nDescription: D\n\n# H\n\nHello.\n"
        page = self.write("p.html", self.HEAD + '<main><h1>H</h1><p>Hello.</p><p class="vh-note">Extra copy.</p></main></body></html>')
        r = self.cli(page, doc=doc)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Extra copy.", r.stdout)

    def test_an_explicit_skip_replaces_the_default_list(self):
        # Why: documented behaviour; an owner who names only .byline gets only .byline, so the help
        # text and SKILL.md say to repeat the hidden classes.
        r = self.cli(self.page("vh"), "--skip", "nav,.byline")
        self.assertEqual(r.returncode, 1)
        self.assertIn("(opens in a new tab)", r.stdout)

    def test_the_help_names_the_default_hidden_classes(self):
        r = self.cli(self.page("vh"), "--help")
        self.assertEqual(r.returncode, 0)
        flat = " ".join(r.stdout.split())
        self.assertIn("nav,footer,aside,.vh,.sr-only,.visually-hidden", flat)


if __name__ == "__main__":
    unittest.main()
