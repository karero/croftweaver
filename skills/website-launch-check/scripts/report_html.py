#!/usr/bin/env python3
"""report_html.py — turn a launch report's Markdown into one self-contained HTML page.

    python3 report_html.py <report.md> [--lang de]   # writes <report>.html beside it
    python3 report_html.py --rebuild <folder>        # rebuilds every <name>.html that has a <name>.md

The Markdown is the source; the page is rebuilt from it, never edited by hand. The page uses a
fixed set of elements and attributes and one constant <style>, so it loads and runs nothing.
It reads the Markdown the report templates use: headings, paragraphs, lists, task lists,
tables, quotes, fenced code, **bold**, *emphasis*, `code` and [links](target). Anything else
comes out as plain text. Standard library only.
"""
import argparse
import html
import re
import sys
from pathlib import Path

# A link keeps its target only if the whole target matches: http(s)/mailto/# with no space,
# control character, quote, angle bracket or backslash after it, or a relative path of ASCII
# letters, digits and / . - _ ~ % that does not start with //. Anything else is shown as text.
SAFE_TARGET = re.compile(
    r"(?:(?:https://|http://|mailto:|#)[^\s\x00-\x1f\x7f\"'<>\\]*"
    r"|(?!//)[A-Za-z0-9/._~%-]+)\Z"
)
LANG = re.compile(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*\Z")

# No url(), no @import: the page must not load anything (the tests check this constant).
STYLE = """
:root { color-scheme: light dark; --bg: #ffffff; --fg: #1d1d1f; --muted: #5f6368;
  --line: #d9d9de; --head: #f4f4f6; --link: #0b57d0; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #151517; --fg: #ececf0; --muted: #a8a8b3; --line: #3a3a40;
    --head: #222226; --link: #8ab4f8; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 52rem; margin: 0 auto; padding: 2rem 1rem 4rem; }
h1 { font-size: 1.8rem; line-height: 1.25; margin: 0 0 1rem; }
h2 { font-size: 1.35rem; margin: 2.2rem 0 .6rem; padding-top: .4rem; border-top: 1px solid var(--line); }
h3 { font-size: 1.1rem; margin: 1.6rem 0 .4rem; }
h4 { font-size: 1rem; margin: 1.2rem 0 .3rem; }
p, ul, ol, blockquote, pre { margin: 0 0 1rem; }
ul, ol { padding-left: 1.4rem; }
li { margin: .2rem 0; }
li.task { list-style: none; margin-left: -1.4rem; }
input[type=checkbox] { margin-right: .5rem; }
a { color: var(--link); }
code { font: .92em ui-monospace, SFMono-Regular, Menlo, monospace; background: var(--head);
  padding: .05rem .25rem; border-radius: 4px; }
pre { overflow-x: auto; background: var(--head); padding: .8rem; border-radius: 6px; }
pre code { background: none; padding: 0; }
blockquote { margin-left: 0; padding-left: 1rem; border-left: 3px solid var(--line); color: var(--muted); }
.table { overflow-x: auto; margin: 0 0 1rem; }
table { border-collapse: collapse; width: 100%; font-size: .95rem; }
th, td { text-align: left; vertical-align: top; padding: .4rem .55rem; border: 1px solid var(--line); }
th { background: var(--head); }
"""


def esc(text):
    return html.escape(text, quote=True)


def inline(text):
    """Escape text and render `code`, [links](target), **bold** and *emphasis*."""
    out = []
    for i, part in enumerate(re.split(r"(`[^`\n]+`)", text)):
        if i % 2:
            out.append("<code>" + esc(part[1:-1]) + "</code>")
        else:
            out.append(_links(part))
    return "".join(out)


def _links(text):
    out, pos = [], 0
    for m in re.finditer(r"\[([^\]\n]+)\]\(([^)\n]*)\)", text):
        out.append(_emphasis(esc(text[pos:m.start()])))
        label, target = m.group(1), m.group(2)
        if SAFE_TARGET.match(target):
            out.append('<a href="' + esc(target) + '">' + _emphasis(esc(label)) + "</a>")
        else:
            out.append(esc(m.group(0)))
        pos = m.end()
    out.append(_emphasis(esc(text[pos:])))
    return "".join(out)


def _emphasis(escaped):
    escaped = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", escaped)
    return re.sub(r"(?<![*\w])\*(?=\S)([^*]+?)(?<=\S)\*(?![*\w])", r"<em>\1</em>", escaped)


def _cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)]


TABLE_RULE = re.compile(r"\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*\Z")
LIST_ITEM = re.compile(r"\s*(?:[-*]|\d+[.)])\s+(.*)\Z")
TASK = re.compile(r"\[([ xX])\]\s+(.*)\Z", re.S)


def render_body(md):
    """The <main> content for a Markdown text, as a list of HTML blocks."""
    lines = md.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks, i = [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.lstrip().startswith("```"):
            body, i = [], i + 1
            while i < len(lines) and not lines[i].lstrip().startswith("```"):
                body.append(lines[i])
                i += 1
            blocks.append("<pre><code>" + esc("\n".join(body)) + "</code></pre>")
            i += 1
            continue
        m = re.match(r"(#{1,6})\s+(.*?)\s*#*\s*\Z", line)
        if m:
            level = min(len(m.group(1)), 4)
            blocks.append("<h%d>%s</h%d>" % (level, inline(m.group(2)), level))
            i += 1
            continue
        if "|" in line and i + 1 < len(lines) and TABLE_RULE.match(lines[i + 1]):
            head = _cells(line)
            rows, i = [], i + 2
            while i < len(lines) and lines[i].strip() and "|" in lines[i]:
                rows.append(_cells(lines[i]))
                i += 1
            parts = ['<div class="table"><table><thead><tr>']
            parts += ["<th>" + inline(c) + "</th>" for c in head]
            parts.append("</tr></thead><tbody>")
            for row in rows:
                row = (row + [""] * len(head))[: max(len(head), len(row))]
                parts.append("<tr>" + "".join("<td>" + inline(c) + "</td>" for c in row) + "</tr>")
            parts.append("</tbody></table></div>")
            blocks.append("".join(parts))
            continue
        if line.lstrip().startswith(">"):
            quote = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                quote.append(lines[i].lstrip()[1:].strip())
                i += 1
            blocks.append("<blockquote><p>" + inline(" ".join(quote)) + "</p></blockquote>")
            continue
        m = LIST_ITEM.match(line)
        if m:
            ordered = bool(re.match(r"\s*\d", line))
            items = []
            while i < len(lines) and lines[i].strip():
                m = LIST_ITEM.match(lines[i])
                if m:
                    items.append(m.group(1))
                elif items and lines[i].startswith((" ", "\t")):
                    items[-1] += " " + lines[i].strip()  # a wrapped line of the item above
                else:
                    break
                i += 1
            tag = "ol" if ordered else "ul"
            parts = ["<%s>" % tag]
            for item in items:
                t = TASK.match(item)
                if t:
                    box = '<input type="checkbox" disabled' + (" checked" if t.group(1) in "xX" else "") + ">"
                    parts.append('<li class="task">' + box + inline(t.group(2)) + "</li>")
                else:
                    parts.append("<li>" + inline(item) + "</li>")
            parts.append("</%s>" % tag)
            blocks.append("".join(parts))
            continue
        para = []
        while i < len(lines) and lines[i].strip() and not _starts_block(lines, i):
            para.append(lines[i].strip())
            i += 1
        if not para:  # a line that starts a block but did not parse as one: plain text
            para.append(lines[i].strip())
            i += 1
        blocks.append("<p>" + inline(" ".join(para)) + "</p>")
    return blocks


def _starts_block(lines, i):
    line = lines[i]
    return bool(
        line.lstrip().startswith(("```", ">", "#"))
        or LIST_ITEM.match(line)
        or ("|" in line and i + 1 < len(lines) and TABLE_RULE.match(lines[i + 1]))
    )


def render(md, lang="en", title=None):
    if not LANG.match(lang):
        raise ValueError("not a language tag: %r" % lang)
    if title is None:
        m = re.search(r"^#\s+(.*?)\s*#*\s*$", md, re.M)
        title = m.group(1) if m else "Report"
    return (
        "<!doctype html>\n"
        '<html lang="' + esc(lang) + '">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>" + esc(re.sub(r"[*`]", "", title)) + "</title>\n"
        "<style>" + STYLE + "</style>\n</head>\n<body>\n<main>\n"
        + "\n".join(render_body(md))
        + "\n</main>\n</body>\n</html>\n"
    )


def write(md_path, lang):
    md_path = Path(md_path)
    out = md_path.with_suffix(".html")
    out.write_text(render(md_path.read_text(encoding="utf-8"), lang=lang), encoding="utf-8")
    return out


def page_lang(html_path):
    m = re.search(r'<html lang="([^"]+)"', html_path.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m and LANG.match(m.group(1)) else "en"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Turn a launch report's Markdown into a self-contained HTML page.")
    ap.add_argument("source", help="a report .md, or with --rebuild a folder")
    ap.add_argument("--lang", default="en", help="the report's language tag (default en)")
    ap.add_argument("--rebuild", action="store_true",
                    help="rebuild every <name>.html in the folder that has a <name>.md, keeping its language")
    args = ap.parse_args(argv)
    src = Path(args.source)
    if args.rebuild:
        if not src.is_dir():
            sys.exit("report_html: not a folder: %s" % src)
        for page in sorted(src.glob("*.html")):
            md = page.with_suffix(".md")
            if md.is_file():
                write(md, page_lang(page))
                print("rebuilt %s" % page)
        return 0
    if src.suffix != ".md" or not src.is_file():
        sys.exit("report_html: not a .md file: %s" % src)
    if not LANG.match(args.lang):
        sys.exit("report_html: not a language tag: %s" % args.lang)
    print("wrote %s" % write(src, args.lang))
    return 0


if __name__ == "__main__":
    sys.exit(main())
