#!/usr/bin/env python3
"""Did the build keep the approved text?

Compares a page document's draft (markdown, the part under "## Draft") with the page as built
(an HTML file): the title, the description, the FAQ schema and every sentence of the visible text.
Both sides are folded first: whitespace (non-breaking spaces too), HTML entities, Unicode
composition (NFC) and typographic quotes. Nothing else is folded, so a changed dash or word shows up.

  python3 check_page_text.py PAGE-DOCUMENT.md BUILT.html [--title-suffix " | Site"] [--skip nav,footer,.byline]

Exit 0: the build kept the text. Exit 1: it differs, and every changed sentence is listed.
Exit 2: the input could not be read or is not shaped as this script expects (said on stderr).
Standard library only; Python 3.9 or newer.
"""
import argparse
import html
import json
import re
import sys
import unicodedata
from html.parser import HTMLParser

# Tags whose content is never visible text. "head" is read separately for the title/description.
HIDDEN = {"script", "style", "noscript", "template", "svg", "head", "title"}
# Tags that do not end a text block; any other tag does.
INLINE = {"a", "abbr", "b", "bdi", "bdo", "cite", "code", "data", "del", "dfn", "em", "i", "ins",
          "kbd", "mark", "q", "s", "samp", "small", "span", "strong", "sub", "sup", "time", "u",
          "var", "wbr", "label"}
VOID = {"br", "hr", "img", "input", "meta", "link", "wbr", "source", "col", "area", "base", "embed"}

QUOTES = str.maketrans({"‘": "'", "’": "'", "‚": "'", "‛": "'",
                        "“": '"', "”": '"', "„": '"', "‟": '"'})


def fold(text, entities=False):
    """Typographic quotes straightened, whitespace collapsed; entities unescaped where the
    text still holds them (the draft). The HTML parser has already decoded the page's."""
    if entities:
        text = html.unescape(text)
    text = unicodedata.normalize("NFC", text).translate(QUOTES)
    return " ".join(text.split())


def sentences(block):
    """Split one folded block into sentences; a piece with no letter or digit is not text."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])", block)
    return [p for p in parts if re.search(r"[^\W_]", p)]


class Page(HTMLParser):
    """Collects title, description, FAQ schema and the visible text blocks of a built page."""

    def __init__(self, skip):
        super().__init__(convert_charrefs=True)
        self.skip = skip
        self.title = None
        self.description = None
        self.ld = []
        self.blocks = []
        self._buf = []
        self._hidden = 0       # depth inside a HIDDEN tag
        self._skipped = 0      # depth inside a --skip tag
        self._stack = []       # open tags, to match end tags
        self._in_title = False
        self._ld_script = False
        self._ld_text = []
        self._main = 0
        self._has_main = False
        self._main_blocks = []

    def _flush(self):
        text = fold("".join(self._buf))
        self._buf = []
        if text and not self._hidden and not self._skipped:
            self.blocks.append(text)
            if self._main:
                self._main_blocks.append(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and (a.get("name") or "").lower() == "description" and self.description is None:
            self.description = a.get("content") or ""
        if tag == "title" and self.title is None:
            self._in_title = True
            self._title_buf = []
        if tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
            self._ld_script = True
            self._ld_text = []
        if tag in VOID:
            if tag == "br":
                self._buf.append(" ")
            elif tag not in INLINE:
                self._flush()
            return
        classes = set((a.get("class") or "").split())
        hidden = tag in HIDDEN
        skipped = tag in self.skip or any("." + c in self.skip for c in classes)
        if tag not in INLINE or skipped:     # a skipped inline element is cut off from its neighbours too
            self._flush()
        self._stack.append((tag, hidden, skipped))
        self._hidden += hidden
        self._skipped += skipped
        if tag == "main":
            self._main += 1
            self._has_main = True

    def handle_endtag(self, tag):
        if tag in VOID or all(t != tag for t, _, _ in self._stack):
            return
        # close any tags the markup left open inside this one
        while self._stack:
            top, hidden, skipped = self._stack.pop()
            if top not in INLINE or skipped:   # flush while the element still counts as open
                self._hidden += hidden
                self._skipped += skipped
                self._flush()
                self._hidden -= hidden
                self._skipped -= skipped
            self._hidden -= hidden
            self._skipped -= skipped
            if top == "main":
                self._main -= 1
            if top == "title" and self._in_title:
                self.title = fold("".join(self._title_buf))
                self._in_title = False
            if top == "script" and self._ld_script:
                self._ld_script = False
                self.ld.append("".join(self._ld_text))
            if top == tag:
                break

    def handle_data(self, data):
        if self._in_title:
            self._title_buf.append(data)
        elif self._ld_script:
            self._ld_text.append(data)
        elif not self._hidden:
            self._buf.append(data)

    def close(self):
        super().close()
        self._flush()

    def body_blocks(self):
        """The blocks inside <main> if the page has one (even an empty one), else all visible blocks."""
        return self._main_blocks if self._has_main else self.blocks


class _SchemaText(HTMLParser):
    """The text of an HTML string as the reader sees it: tags and comments dropped, entities
    decoded, an inline tag leaving no gap in the words around it and any other tag a break."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def _break(self, tag):
        if tag not in INLINE:
            self.parts.append(" ")

    def handle_starttag(self, tag, attrs):
        self._break(tag)

    def handle_startendtag(self, tag, attrs):
        self._break(tag)

    def handle_endtag(self, tag):
        self._break(tag)

    def handle_data(self, data):
        self.parts.append(data)


def ld_text(value):
    """A schema string as the reader sees it, folded. Only a missing value (None) is empty."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("FAQ name or answer text is not a string")
    p = _SchemaText()
    p.feed(value)
    p.close()
    return fold("".join(p.parts))


def faq_from_ld(scripts):
    """(question, answer) pairs of every FAQPage in the page's JSON-LD, folded. A block that is
    not JSON, or a FAQPage whose mainEntity is not a question object or a list of them, or whose
    answer is not one object, counts in the second value: the script cannot read it."""
    found, bad = [], 0

    def walk(node):
        if isinstance(node, list):
            for n in node:
                walk(n)
        elif isinstance(node, dict):
            kind = node.get("@type")
            kinds = kind if isinstance(kind, list) else [kind]
            if "FAQPage" in kinds:
                entities = node.get("mainEntity")
                if entities is None:
                    entities = []
                if isinstance(entities, dict):
                    entities = [entities]
                if not isinstance(entities, list):
                    raise ValueError("FAQPage mainEntity is not a list")
                for q in entities:
                    if not isinstance(q, dict):
                        raise ValueError("FAQPage question is not an object")
                    accepted = q.get("acceptedAnswer")
                    if accepted is None:
                        accepted = {}
                    if not isinstance(accepted, dict):
                        raise ValueError("acceptedAnswer is not an object")
                    found.append((ld_text(q.get("name")), ld_text(accepted.get("text"))))
            for v in node.values():
                walk(v)

    for raw in scripts:
        try:
            walk(json.loads(raw))
        except ValueError:
            bad += 1
    return found, bad


# ---- the draft ---------------------------------------------------------------------------

def inline_md(text):
    """Markdown inline syntax to the text a reader sees."""
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)              # an image shows no text
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)            # a link shows its words
    text = re.sub(r"<(https?://[^>\s]+)>", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", text)
    text = re.sub(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", r"\1", text)
    text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|>])", r"\1", text)
    return text


def draft_of(doc):
    """(title, description, blocks, faq) from a page document's "## Draft" section."""
    doc = re.sub(r"<!--.*?-->", "", doc, flags=re.S)
    m = re.search(r"^##[ \t]+Draft[ \t]*$", doc, re.M)
    if not m:
        raise ValueError('no "## Draft" heading in the page document')
    lines = doc[m.end():].splitlines()
    meta, i = {}, 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        mm = re.match(r"(Title|Description):[ \t]*(.*)$", s)
        if not mm:
            break
        meta[mm.group(1).lower()] = fold(inline_md(mm.group(2)), True)
        i += 1
    for key in ("title", "description"):
        if not meta.get(key):
            raise ValueError('the draft must start with "Title: ..." and "Description: ..." lines')
    blocks, faq = [], []
    para, fence = [], False
    faq_level, question, answer = None, None, []

    def add_block(text):
        blocks.append(text)
        if question is not None:
            answer.append(text)

    def end_para():
        if para:
            add_block(fold(inline_md(" ".join(para)), True))
        para.clear()

    def end_question():
        nonlocal question, answer
        if question is not None:
            faq.append((question, fold(" ".join(answer))))
        question, answer = None, []

    for raw in lines[i:]:
        line = raw.rstrip()
        if line.lstrip().startswith("```"):
            end_para()
            fence = not fence
            continue
        if fence:
            if line.strip():
                add_block(fold(line, True))
            continue
        if not line.strip():
            end_para()
            continue
        h = re.match(r"(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$", line)
        if h:
            end_para()
            level, text = len(h.group(1)), fold(inline_md(h.group(2)), True)
            if faq_level is not None and level <= faq_level:
                end_question()
                faq_level = None
            if faq_level is not None:           # inside the FAQ section every heading is a question
                end_question()
                question = text
            elif re.fullmatch(r"(?i)faq|frequently asked questions", text):
                faq_level = level
            blocks.append(text)
            continue
        if re.match(r"\s*(?:[-*+]|\d+[.)])[ \t]+", line):              # a list item starts a block
            end_para()
            para.append(re.sub(r"^\s*(?:[-*+]|\d+[.)])[ \t]+", "", line))
            continue
        if re.match(r"\s*\|", line):                                   # a table row: one block per cell
            end_para()
            if not re.fullmatch(r"[\s|:\-]+", line):
                for cell in line.strip().strip("|").split("|"):
                    if cell.strip():
                        add_block(fold(inline_md(cell), True))
            continue
        para.append(re.sub(r"^\s*>[ \t]?", "", line).strip())
    end_para()
    end_question()
    return meta["title"], meta["description"], blocks, faq


# ---- the comparison ----------------------------------------------------------------------

def tally(blocks):
    out = {}
    for b in blocks:
        for s in sentences(b):
            out[s] = out.get(s, 0) + 1
    return out


def missing(a, b):
    """Sentences of tally a that tally b lacks, with the surplus count, in a's order."""
    return [s for s, n in a.items() for _ in range(max(0, n - b.get(s, 0)))]


def main(argv):
    ap = argparse.ArgumentParser(description="Check that a built page kept the approved draft's text.")
    ap.add_argument("document", help="the page document (markdown); its '## Draft' section is the approved text")
    ap.add_argument("built", help="the built page (HTML)")
    ap.add_argument("--title-suffix", default="", help="text the site adds to every <title>, e.g. ' | Site'")
    ap.add_argument("--skip", default="nav,footer,aside",
                    help="tags, or .classes, whose text is site chrome, not page copy "
                         "(default: nav,footer,aside; '' for none), e.g. nav,footer,.byline")
    args = ap.parse_args(argv)
    try:
        with open(args.document, encoding="utf-8") as f:
            title, desc, d_blocks, d_faq = draft_of(f.read())
        with open(args.built, encoding="utf-8") as f:
            page = Page({t.strip() for t in args.skip.split(",") if t.strip()})
            page.feed(f.read())
            page.close()
    except (OSError, ValueError) as e:
        print(f"check_page_text: {e}", file=sys.stderr)
        return 2
    if page.title is None or page.description is None:
        print("check_page_text: the built page has no <title> or no meta description", file=sys.stderr)
        return 2
    b_faq, bad_ld = faq_from_ld(page.ld)
    if bad_ld:
        print(f"check_page_text: {bad_ld} JSON-LD block(s) in the built page could not be read (not JSON, or a FAQPage in a shape this script does not read)", file=sys.stderr)
        return 2

    diffs = []
    built_title = page.title
    suffix = fold(args.title_suffix)
    if suffix and built_title.endswith(suffix):
        built_title = built_title[: -len(suffix)].rstrip()
    if built_title != title:
        diffs.append(f'title: draft "{title}" / built "{built_title}"')
    if fold(page.description) != desc:
        diffs.append(f'description: draft "{desc}" / built "{fold(page.description)}"')
    if d_faq != b_faq:
        d_set, b_set = set(d_faq), set(b_faq)
        for q, a in d_faq:
            if (q, a) not in b_set:
                diffs.append(f'FAQ schema: draft has "{q}" / "{a}", built does not')
        for q, a in b_faq:
            if (q, a) not in d_set:
                diffs.append(f'FAQ schema: built has "{q}" / "{a}", draft does not')
        if not diffs or not any(x.startswith("FAQ schema") for x in diffs):
            diffs.append("FAQ schema: same questions, different order or repeats")
    d_tally, b_tally = tally(d_blocks), tally(page.body_blocks())
    changed, added = missing(d_tally, b_tally), missing(b_tally, d_tally)

    print(f"page text: {args.document} against {args.built}")
    print(f"  draft: {sum(d_tally.values())} sentences, {len(d_faq)} FAQ; "
          f"built: {sum(b_tally.values())} sentences, {len(b_faq)} FAQ in the schema")
    for d in diffs:
        print("  DIFFERENT " + d)
    for s in changed:
        print(f'  CHANGED (in the draft, not in the page): "{s}"')
    for s in added:
        print(f'  ADDED (in the page, not in the draft): "{s}"')
    if diffs or changed or added:
        print("The build did not keep the text: list each line above in the PR for the owner to read.")
        return 1
    print("The build kept the approved text.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
