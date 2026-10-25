"""Tests for report_html.py: the page a launch report becomes must load and run nothing, keep
every block's text, and keep only safe link targets. Standard library only.

    python3 -m unittest discover -s skills/website-launch-check/scripts/tests
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "report_html.py"
TEMPLATES = sorted((HERE.parent.parent / "references").glob("*-template.md"))
sys.path.insert(0, str(HERE.parent))
import report_html  # noqa: E402

# The allowed set lives here, not in the script, so widening the script's set fails this test
# until the test is changed too.
ALLOWED = {
    "html": {"lang"}, "head": set(), "meta": {"charset", "name", "content", "http-equiv"}, "title": set(),
    "style": set(), "body": set(), "main": set(),
    "h1": set(), "h2": set(), "h3": set(), "h4": set(), "p": set(),
    "ul": set(), "ol": {"start"}, "li": {"class"}, "input": {"type", "disabled", "checked"},
    "div": {"class"}, "table": set(), "thead": set(), "tbody": set(), "tr": set(),
    "th": set(), "td": set(), "blockquote": set(), "pre": set(), "code": set(),
    "strong": set(), "em": set(), "a": {"href"},
}
SAFE = re.compile(
    r"(?:(?:https://|http://|mailto:|#)[^\s\x00-\x1f\x7f\"'<>\\]*|(?!//)[A-Za-z0-9/._~%-]+(?:#[A-Za-z0-9._~%-]*)?)\Z")


class Page(HTMLParser):
    """Collects every element with its attributes, and the visible text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements, self.text, self._skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, attrs))
        if tag in ("style", "title"):
            self._skip += 1

    def handle_startendtag(self, tag, attrs):
        self.elements.append((tag, attrs))

    def handle_endtag(self, tag):
        if tag in ("style", "title"):
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.text.append(data)


def parse(page_html):
    p = Page()
    p.feed(page_html)
    return p


def norm(s):
    return " ".join(s.split())


def block_texts(md):
    """The text of each block of the MD, with its Markdown marks taken off."""
    out = []
    for line in md.splitlines():
        line = line.strip()
        if not line or set(line) <= set("|-: ") or line.startswith("```"):
            continue
        line = re.sub(r"^(#{1,6}\s+|[-*]\s+(\[[ xX]\]\s+)?|\d+[.)]\s+|>\s*)", "", line)
        for cell in (line.strip("|").split("|") if "|" in line else [line]):
            cell = re.sub(r"\[([^\]\n]+)\]\(([^)\n]*)\)", lambda m: m.group(1) if SAFE.match(m.group(2)) else m.group(0), cell)
            cell = cell.replace("**", "").replace("`", "")
            cell = re.sub(r"(?<![*\w])\*(?=\S)([^*]+?)(?<=\S)\*(?![*\w])", r"\1", cell)
            if cell.strip():
                out.append(norm(cell))
    return out


class Structure(unittest.TestCase):
    def assert_safe(self, page_html):
        page = parse(page_html)
        for tag, attrs in page.elements:
            self.assertIn(tag, ALLOWED, "element not allowed: <%s>" % tag)
            for name, value in attrs:
                self.assertIn(name, ALLOWED[tag], "attribute not allowed: <%s %s>" % (tag, name))
                self.assertFalse(name == "src" or name.startswith("on"), "loading/handler attribute: %s" % name)
                if name == "href":
                    self.assertRegex(value, SAFE)
        return page

    def test_templates_render_safe_and_keep_their_text(self):
        self.assertGreaterEqual(len(TEMPLATES), 3, TEMPLATES)
        for path in TEMPLATES:
            with self.subTest(template=path.name):
                md = path.read_text(encoding="utf-8")
                page = self.assert_safe(report_html.render(md, lang="de"))
                text = norm("".join(page.text))
                for block in block_texts(md):
                    self.assertIn(block, text)

    def test_the_browser_is_told_to_load_nothing(self):
        page_html = report_html.render("# T")
        self.assertIn('<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">', page_html)

    def test_one_constant_style_that_loads_nothing(self):
        page_html = report_html.render("# T\n\nx")
        styles = re.findall(r"<style>(.*?)</style>", page_html, re.S)
        self.assertEqual(styles, [report_html.STYLE])
        self.assertNotIn("url(", report_html.STYLE)
        self.assertNotIn("@import", report_html.STYLE)
        self.assertIn("prefers-color-scheme: dark", report_html.STYLE)
        self.assertIn("color-scheme: light dark", report_html.STYLE)


class Links(unittest.TestCase):
    def links(self, target):
        page = parse(report_html.render("# T\n\nsee [here](%s) now" % target))
        return [dict(a)["href"] for t, a in page.elements if t == "a"], norm("".join(page.text))

    def test_ordinary_links_keep_their_target(self):
        for target in ("https://pagespeed.web.dev/", "#verdict", "launch-todos-2026-11-20.md", "%C3%BCber.md",
                       "launch-comparison-2026-11-20.md#redirects",
                       "mailto:owner@example.com", "http://example.com/a?b=1"):
            with self.subTest(target=target):
                hrefs, _ = self.links(target)
                self.assertEqual(hrefs, [target])

    def test_a_target_with_parentheses_is_kept_whole(self):
        hrefs, _ = self.links("https://example.org/Guide_(launch)")
        self.assertEqual(hrefs, ["https://example.org/Guide_(launch)"])

    def test_unsafe_targets_come_out_as_text(self):
        for target in ("//x", "\\/x", "\\\\x", "\t//x", "JaVaScRiPt:x", "jav\tascript:x", "javascript:alert(1)",
                       "data:text/html,x", "https://a b", 'https://a"b', "über.md", "HTTPS://x"):
            with self.subTest(target=target):
                hrefs, text = self.links(target)
                self.assertEqual(hrefs, [])
                self.assertIn("[here](", text)


class Escaping(unittest.TestCase):
    def test_a_hostile_payload_is_text_in_every_construct(self):
        bad = '</title><script>x()</script>"onerror=y'
        md = ("# " + bad + "\n\n## " + bad + "\n\n" + bad + "\n\n- " + bad + "\n- [ ] " + bad + "\n\n1. " + bad +
              "\n\n> " + bad + "\n\n```\n" + bad + "\n```\n\n| " + bad + " | b |\n|---|---|\n| " + bad + " | `" + bad + "` |\n\n" +
              "[" + bad + "](javascript:z) and [ok " + bad + "](#a) and **" + bad + "**\n")
        page_html = report_html.render(md)
        Structure().assert_safe(page_html)
        page = parse(page_html)
        self.assertEqual([t for t, _ in page.elements if t in ("script", "title")], ["title"])
        self.assertGreaterEqual(norm("".join(page.text)).count(norm(bad)), 12)

    def test_raw_html_is_text(self):
        md = "# T\n\n<script>alert(1)</script>\n\n<img src=\"https://x/x.png\">\n\n<meta http-equiv=\"refresh\" content=\"0\">\n\n<svg onload=\"alert(1)\"></svg>"
        page_html = report_html.render(md)
        Structure().assert_safe(page_html)
        text = norm("".join(parse(page_html).text))
        for s in ("<script>alert(1)</script>", '<img src="https://x/x.png">', '<svg onload="alert(1)"></svg>'):
            self.assertIn(s, text)

    def test_special_characters_are_escaped(self):
        page_html = report_html.render("# A & B\n\nx < y > z \"q\" 'a' [l](#a&b)")
        body = page_html.split("<main>")[1]
        for raw in ("&amp;", "&lt;", "&gt;", "&quot;", "&#x27;"):
            self.assertIn(raw, body)
        self.assertNotIn(" < y ", body)
        self.assertIn('href="#a&amp;b"', body)

    def test_code_keeps_markdown_and_links_literal(self):
        page_html = report_html.render("# T\n\nrun `[x](https://a) **b**` here")
        self.assertIn("<code>[x](https://a) **b**</code>", page_html)


class Blocks(unittest.TestCase):
    def test_each_block_kind(self):
        md = ("# Title\n\n## Part\n\npara one\ncontinues\n\n- [ ] open task\n- [x] done task\n- plain\n\n"
              "1. first\n2. second\n\n> a quote\n\n```\ncode <b>\n```\n\n| A | B |\n|---|---|\n| 1 | 2 \\| 3 |\n")
        page_html = report_html.render(md)
        for frag in ("<h1>Title</h1>", "<h2>Part</h2>", "<p>para one continues</p>",
                     '<li class="task"><input type="checkbox" disabled>open task</li>',
                     '<input type="checkbox" disabled checked>done task', "<li>plain</li>", "<ol><li>first</li>",
                     "<blockquote><p>a quote</p></blockquote>", "<pre><code>code &lt;b&gt;</code></pre>",
                     "<th>A</th>", "<td>2 | 3</td>"):
            self.assertIn(frag, page_html)

    def test_list_start_tables_need_a_pipe_and_images_are_text(self):
        page_html = report_html.render("# T\n\n3. three\n4. four\n\na | b\n---\n\n![shot](shot.png)\n")
        self.assertIn('<ol start="3"><li>three</li>', page_html)
        self.assertNotIn("<table>", page_html)
        self.assertNotIn("<a ", page_html)
        self.assertIn("![shot](shot.png)", page_html)

    def test_a_heading_keeps_a_closing_hash_that_is_part_of_it(self):
        page_html = report_html.render("# Using C#\n\n## Closed ##\n")
        self.assertIn("<title>Using C#</title>", page_html)
        self.assertIn("<h1>Using C#</h1>", page_html)
        self.assertIn("<h2>Closed</h2>", page_html)

    def test_language_and_title(self):
        page_html = report_html.render("# Launch-Check: Schreinerei\n\nText", lang="de")
        self.assertIn('<html lang="de">', page_html)
        self.assertIn("<title>Launch-Check: Schreinerei</title>", page_html)
        with self.assertRaises(ValueError):
            report_html.render("# T", lang='de"><script>')


STARTER_TESTS = HERE.parents[2] / "new-website" / "templates" / "astro" / "tests"
# In the toolkit's repository (make test-launch-check sets this) the starter must be there; in a
# site's copy of the skill it is not, and the check is skipped with this reason.
REQUIRE_STARTER = os.environ.get("LAUNCH_CHECK_REQUIRE_STARTER") == "1"


@unittest.skipUnless(STARTER_TESTS.is_dir() or REQUIRE_STARTER,
                     "the starter's tests are not beside this skill (a copy in a site): "
                     "this check runs in the toolkit's own repository")
class StarterTitles(unittest.TestCase):
    """references/test-coverage.md names the starter's test titles and warning lines; this fails
    when a spec renames one, so the mapping is read again."""

    def test_the_titles_and_warnings_the_mapping_names_exist(self):
        coverage = (HERE.parent.parent / "references" / "test-coverage.md").read_text(encoding="utf-8")
        specs = {p.name: p.read_text(encoding="utf-8") for p in STARTER_TESTS.glob("*.spec.ts")}
        # Each mapping row names its spec and a per-page title: the title must be in that spec.
        rows = re.findall(r"^\| [^|]+ \| `([a-z]+\.spec\.ts)` \| `([^`]*<page>[^`]*)` \|", coverage, re.M)
        self.assertGreaterEqual(len(rows), 3, rows)
        self.assertEqual(len(rows), len(re.findall(r"^\|[^\n]*`[^`\n]*<page>[^`\n]*`", coverage, re.M)),
                         "a mapping row whose spec or title this test cannot read")
        for spec, title in rows:
            self.assertIn(spec, specs, spec)
            self.assertIn(title.replace("<page>", "${path}"), specs[spec], title)
        # Every warning prefix the file names, in the spec that prints it.
        warnings = set(re.findall(r"`(⚠[^`]+:)`", coverage))
        self.assertGreaterEqual(len(warnings), 2, warnings)
        for warning in warnings:
            self.assertTrue(any("'" + warning + " '" in t for t in specs.values()), warning)
        self.assertIn("is not ready to launch", specs["placeholders.spec.ts"])
        self.assertIn("reporter: 'list'", (STARTER_TESTS.parent / "playwright.config.ts").read_text(encoding="utf-8"))


class Cli(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)

    def test_writes_beside_the_md_and_rebuild_follows_an_edit(self):
        with tempfile.TemporaryDirectory() as d:
            md = Path(d) / "launch-check-2026-11-20-prelaunch.md"
            md.write_text("# Bericht\n\nErste Fassung.\n", encoding="utf-8")
            r = self.run_script(str(md), "--lang", "de")
            self.assertEqual(r.returncode, 0, r.stderr)
            page = md.with_suffix(".html")
            self.assertIn("Erste Fassung.", page.read_text(encoding="utf-8"))
            md.write_text("# Bericht\n\nZweite Fassung.\n", encoding="utf-8")
            (Path(d) / "notes.md").write_text("# no page for this one\n", encoding="utf-8")
            r = self.run_script(d, "--rebuild")
            self.assertEqual(r.returncode, 0, r.stderr)
            rebuilt = page.read_text(encoding="utf-8")
            self.assertIn("Zweite Fassung.", rebuilt)
            self.assertIn('<html lang="de">', rebuilt)
            self.assertFalse((Path(d) / "notes.html").exists())

    def test_refuses_a_bad_language_and_a_non_md_file(self):
        with tempfile.TemporaryDirectory() as d:
            md = Path(d) / "r.md"
            md.write_text("# R\n", encoding="utf-8")
            self.assertNotEqual(self.run_script(str(md), "--lang", "x y").returncode, 0)
            other = Path(d) / "r.txt"
            other.write_text("x", encoding="utf-8")
            self.assertNotEqual(self.run_script(str(other)).returncode, 0)
            self.assertFalse((Path(d) / "r.html").exists())


if __name__ == "__main__":
    unittest.main()
