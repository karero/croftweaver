"""_css.py: the small part of CSS the brand-kit intake reads, and nothing else.

An SVG that comes from outside may style itself with a <style> element or a style
attribute. This reads those the way the intake needs: simple selectors (`*`, a tag, `.class`,
`#id`, and those joined, in a comma list) with plain `property: value` declarations. It refuses,
by name, everything that could fetch or run something (an @import or any other @-rule, a url()
that is not a #fragment, an image(), image-set() or src()) and everything it does not read (a
combinator, a pseudo-class, an attribute selector, !important, a property in capital letters, a
backslash escape outside quotes, and any quoted text or bracket that could hide where a rule or
a value ends). Standard library only.
"""

from __future__ import annotations

import re

from _refusal import Refusal

# One blank after a hex escape belongs to it, and a carriage return with its line feed is one blank.
_ESCAPE = re.compile(r"\\([0-9a-fA-F]{1,6})(?:\r\n|[ \t\r\n\f])?|\\(.)", re.S)
# An escaped character or a string (kept as it is: a `/*` inside quotes starts no comment), or a comment.
_COMMENT = re.compile(r"""(\\.|"[^"\\\n]*(?:\\.[^"\\\n]*)*"?|'[^'\\\n]*(?:\\.[^'\\\n]*)*'?)|/\*.*?(?:\*/|\Z)""", re.S)
_URL = re.compile(r"url\s*\(", re.I)
# Blanks are the ones CSS knows: any other kind of space would be part of the address. The name is
# there and is plain ASCII: `url(#)` points at nothing, and \w would take any script's letters and digits.
_FRAGMENT = re.compile(r"""[ \t\r\n]*(?:#NAME|"#NAME"|'#NAME')[ \t\r\n]*\)""".replace("NAME", r"[A-Za-z0-9_\-.:]+"))
# The three functions themselves, bare or with a browser's own prefix (-webkit-image-set), not a
# longer word that ends in one of them (background-image, mask-image).
_FETCH = re.compile(r"(?<![A-Za-z0-9_\-])(?:-[a-z]+-)?(?:image-set|image|src)\(", re.I)
_IDENT = r"-?[A-Za-z_][A-Za-z0-9_\-]*"
_SIMPLE = re.compile(r"^(\*|%s)?((?:[.#]%s)*)$" % (_IDENT, _IDENT))
_NAME = re.compile(_IDENT)
_PART = re.compile(r"([.#])(%s)" % _IDENT)
_PROPERTY = re.compile(r"-?[a-z][a-z0-9\-]*")
MAX_PARTS = 8   # the .class and #id names one selector may join
_BLANKS = " \t\r\n"   # what CSS calls white space; Python's strip() would also take a no-break space
# A whole quoted text, or one character that opens, closes or ends something for a renderer.
_TOKEN = re.compile(r'''"[^"\\\n\r\f]*(?:\\.[^"\\\n\r\f]*)*"|'[^'\\\n\r\f]*(?:\\.[^'\\\n\r\f]*)*'|["'\\()\[\]{};]''', re.S)


def _chr(m):
    if m.group(1):
        n = int(m.group(1), 16)
        return chr(n) if 0 < n < 0x110000 and not 0xD800 <= n < 0xE000 else "�"
    return m.group(2)


def unescape(text):
    """Decode CSS escapes (`u\\72l(` is `url(`), so a check sees what a renderer would."""
    return _ESCAPE.sub(_chr, text)


def _name_chr(m):
    c = _chr(m)
    return c if c.isalnum() or c in "-_" else "\ufffd"


def is_name(text):
    """Could a selector this reader takes name `text`, as a class or as an id?"""
    return _NAME.fullmatch(text) is not None


def strip_comments(text):
    """Each comment as blanks, as many as it had characters: where a comment stood inside a value,
    the value is as long as it stands in the file (a cap on its length counts them)."""
    return _COMMENT.sub(lambda m: m.group(1) or " " * len(m.group()), text)


def check_urls(text):
    """Refuse any url() that is not a same-document #fragment. `text` is any CSS value, with its
    escapes already decoded."""
    for m in _URL.finditer(text):
        if not _FRAGMENT.match(text, m.end()):
            raise Refusal(
                "css-url",
                "A style in the file points to something outside the drawing (a url() that is not "
                "a #fragment with a plain name). Ask the tool for a plainer export.",
            )


def check_text(text):
    """The checks every piece of CSS text passes, whatever it will be used for. Returns the text
    with blanks where its comments were, its escapes still in place: a caller decodes the values
    it keeps, never the text it is about to split."""
    bare = strip_comments(text)
    # Checked with the comments and without them: wherever a renderer thinks a comment starts
    # (`"/*" url(x) "*/"`, `\2f * url(x)`), it sees no more than was checked. And each of those
    # decoded two ways: every escape as the character it stands for, and as a renderer reads one
    # (an escaped letter is that letter; an escaped bracket, quote or space opens and closes
    # nothing, so `url(#a\29 x)` and `url(\22#a\22)` are not the fragments they decode to).
    # A comment that only mentions @import or image( is refused with the rest: kept, deliberately
    # (it fails closed, and a logo's style sheet has no reason to say either).
    for t in (unescape(text), unescape(bare), _ESCAPE.sub(_name_chr, text), _ESCAPE.sub(_name_chr, bare)):
        if re.search(r"@\s*import", t, re.I):
            raise Refusal("css-import", "A style in the file imports another file (@import). Ask the tool for a plainer export.")
        check_urls(t)
        if _FETCH.search(t):
            raise Refusal(
                "css-url",
                "A style in the file loads a picture from outside the drawing (image(), image-set() or src()). "
                "Ask the tool for a plainer export.",
            )
        if re.search(r"expression\s*\(|javascript\s*:|-moz-binding|behaviou?r\s*:", t, re.I):
            raise Refusal("css-script", "A style in the file can run code. Ask the tool for a plainer export.")
    return bare


def check_split(text, sheet=False):
    """Refuse CSS text that this reader would cut up in other places than a renderer does. This
    reader cuts at every brace and semicolon it sees; a renderer does not cut inside quotes or
    inside brackets, and reads an escaped character as a letter of a name (`\\23 f00` is no
    colour to it, `\\3b ` ends nothing). So outside quotes there is no backslash, no square bracket
    and no quote left open; round brackets pair up and hold no brace or semicolon; and a quoted
    text holds neither. `text` has no comments; braces belong in a style sheet only."""
    depth = 0
    for m in _TOKEN.finditer(text):
        s = m.group()
        if len(s) > 1:  # a whole quoted text: a font's name, say
            why = "a brace or a semicolon inside quotes" if any(c in s for c in "{};") else None
        elif s == "(":
            depth, why = depth + 1, None
        elif s == ")":
            depth, why = depth - 1, None if depth else "a bracket that closes nothing"
        elif s in "{};" and depth:
            why = "a brace or a semicolon inside brackets"
        elif s in "{}":
            why = None if sheet else "a brace"
        elif s == ";":
            why = None
        else:
            why = {"\\": "a backslash", "[": "a square bracket", "]": "a square bracket"}.get(s, "a quote that is never closed")
        if why:
            raise Refusal(
                "css-unreadable",
                "A style in the file holds %s, which programs read in different ways, so this check does not read "
                "it. Ask the tool for a plainer export." % why,
            )
    if depth:
        raise Refusal(
            "css-unreadable",
            "A style in the file holds a bracket that is never closed, which programs read in different ways, so this "
            "check does not read it. Ask the tool for a plainer export.",
        )


def parse_declarations(text):
    """`a: b; c: d` into [(prop, value)]. A property is written in small letters and a value is
    handed on as it is written: nothing is put into lower case, nothing is decoded, and the blanks
    round it still stand (who keeps the value takes them off, and holds its length with them)."""
    t = check_text(text)
    check_split(t)
    out = []
    for part in t.split(";"):
        if not part.strip(_BLANKS):
            continue
        if ":" not in part:
            raise Refusal("css-unreadable", "A style in the file is not written as property: value.")
        prop, raw = part.split(":", 1)
        prop, value = prop.strip(_BLANKS), raw.strip(_BLANKS)
        if re.search(r"!\s*important", value, re.I):
            raise Refusal("css-unreadable", "A style in the file uses !important, which this check does not read.")
        if prop != prop.lower() and prop.isascii() and _PROPERTY.fullmatch(prop.lower()) and value:
            # measured 2026-10-12: a browser reads FILL as fill, the site's renderer does not read it at all
            raise Refusal(
                "css-unreadable",
                "A style in the file writes a property in capital letters (%r), which programs read in different ways, "
                "so this check does not read it. Ask the tool for a plainer export." % prop[:30],
            )
        if not _PROPERTY.fullmatch(prop) or not value:
            raise Refusal("css-unreadable", "A style in the file is not written as property: value.")
        out.append((prop, raw))
    return out


def parse_stylesheet(text):
    """The rules of a <style> element: [(selectors, declarations, order)], where a selector
    is (tag_or_None, [ids], [classes]) and the specificity is read from those."""
    t = check_text(text)
    if "@" in t:
        raise Refusal("css-at-rule", "A style in the file uses an @-rule (@media, @font-face and the like). Ask the tool for a plainer export.")
    check_split(t, sheet=True)
    rules = []
    pos = 0
    while True:
        o = t.find("{", pos)
        if o < 0:
            if t[pos:].strip(_BLANKS):
                raise Refusal("css-unreadable", "A style in the file is cut short.")
            break
        c = t.find("}", o)
        if c < 0 or "{" in t[o + 1:c]:
            raise Refusal("css-unreadable", "A style in the file is nested or cut short, which this check does not read.")
        selectors = []
        for sel in t[pos:o].split(","):
            sel = sel.strip(_BLANKS)
            m = _SIMPLE.match(sel)
            if not sel or not m:
                raise Refusal(
                    "css-unreadable",
                    "A style rule in the file uses a selector this check does not read (%r). Only a tag, "
                    ".class or #id, alone or joined, is read." % sel[:40],
                )
            tag = m.group(1) if m.group(1) not in (None, "*") else None
            ids, classes = [], []
            for kind, name in _PART.findall(m.group(2)):
                (ids if kind == "#" else classes).append(name)
            if len(ids) + len(classes) > MAX_PARTS:
                raise Refusal(
                    "selector-too-long",
                    "A style rule in the file joins more than %d class and id names in one selector (%r...), far more "
                    "than a logo needs. Ask the tool for a plainer export." % (MAX_PARTS, sel[:40]),
                )
            selectors.append((tag, ids, classes))
        rules.append((selectors, parse_declarations(t[o + 1:c]), len(rules)))
        pos = c + 1
    return rules


def specificity(selector):
    tag, ids, classes = selector
    return (len(ids), len(classes), 1 if tag else 0)
