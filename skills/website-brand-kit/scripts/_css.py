"""_css.py: the small part of CSS the brand-kit intake reads, and nothing else.

An SVG that comes from outside may style itself with a <style> element or a style
attribute. This reads those the way the intake needs: simple selectors (`*`, a tag, `.class`,
`#id`, and those joined, in a comma list) with plain `property: value` declarations. It refuses,
by name, everything that could fetch or run something (an @import or any other @-rule, a url()
that is not a #fragment, an image(), image-set() or src()) and everything it does not read (a
combinator, a pseudo-class, an attribute selector, !important, a backslash escape in a selector
or a property name). Standard library only.
"""

from __future__ import annotations

import re

from _refusal import Refusal

_ESCAPE = re.compile(r"\\([0-9a-fA-F]{1,6})[ \t\r\n\f]?|\\(.)", re.S)
# An escaped character or a string (kept as it is: a `/*` inside quotes starts no comment), or a comment.
_COMMENT = re.compile(r"""(\\.|"[^"\\\n]*(?:\\.[^"\\\n]*)*"?|'[^'\\\n]*(?:\\.[^'\\\n]*)*'?)|/\*.*?(?:\*/|\Z)""", re.S)
_URL = re.compile(r"url\s*\(", re.I)
_FRAGMENT = re.compile(r"""\s*(?:#[\w\-.:]*|"#[\w\-.:]*"|'#[\w\-.:]*')\s*\)""")
_FETCH = re.compile(r"(?<![A-Za-z0-9_])(?:image-set|image|src)\(", re.I)
_IDENT = r"-?[A-Za-z_][A-Za-z0-9_\-]*"
_SIMPLE = re.compile(r"^(\*|%s)?((?:[.#]%s)*)$" % (_IDENT, _IDENT))
_PART = re.compile(r"([.#])(%s)" % _IDENT)


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


def strip_comments(text):
    return _COMMENT.sub(lambda m: m.group(1) or " ", text)


def check_urls(text):
    """Refuse any url() that is not a same-document #fragment. `text` is any CSS value, with its
    escapes already decoded."""
    for m in _URL.finditer(text):
        if not _FRAGMENT.match(text, m.end()):
            raise Refusal(
                "css-url",
                "A style in the file points to something outside the drawing (a url() that is not "
                "a #fragment). Ask the tool for a plainer export.",
            )


def check_text(text):
    """The checks every piece of CSS text passes, whatever it will be used for. Returns the text
    without its comments, its escapes still in place: a caller decodes the values it keeps, never
    the text it is about to split."""
    bare = strip_comments(text)
    # Checked with the comments and without them: wherever a renderer thinks a comment starts
    # (`"/*" url(x) "*/"`, `\2f * url(x)`), it sees no more than was checked. And each of those
    # decoded two ways: every escape as the character it stands for, and as a renderer reads one
    # (an escaped letter is that letter; an escaped bracket, quote or space opens and closes
    # nothing, so `url(#a\29 x)` and `url(\22#a\22)` are not the fragments they decode to).
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


def parse_declarations(text):
    """`a: b; c: d` into [(prop, value)], lower-case property names."""
    t = check_text(text)
    out = []
    for part in t.split(";"):
        if not part.strip():
            continue
        if ":" not in part:
            raise Refusal("css-unreadable", "A style in the file is not written as property: value.")
        prop, value = part.split(":", 1)
        prop, value = prop.strip().lower(), unescape(value).strip()
        if re.search(r"!\s*important", value, re.I):
            raise Refusal("css-unreadable", "A style in the file uses !important, which this check does not read.")
        if not re.match(r"^-?[a-z][a-z0-9\-]*$", prop) or not value:
            raise Refusal("css-unreadable", "A style in the file is not written as property: value.")
        out.append((prop, value))
    return out


def parse_stylesheet(text):
    """The rules of a <style> element: [(selectors, declarations, order)], where a selector
    is (tag_or_None, [ids], [classes]) and the specificity is read from those."""
    t = check_text(text)
    if "@" in t:
        raise Refusal("css-at-rule", "A style in the file uses an @-rule (@media, @font-face and the like). Ask the tool for a plainer export.")
    rules = []
    pos = 0
    while True:
        o = t.find("{", pos)
        if o < 0:
            if t[pos:].strip():
                raise Refusal("css-unreadable", "A style in the file is cut short.")
            break
        c = t.find("}", o)
        if c < 0 or "{" in t[o + 1:c]:
            raise Refusal("css-unreadable", "A style in the file is nested or cut short, which this check does not read.")
        selectors = []
        for sel in t[pos:o].split(","):
            sel = sel.strip()
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
            selectors.append((tag, ids, classes))
        rules.append((selectors, parse_declarations(t[o + 1:c]), len(rules)))
        pos = c + 1
    return rules


def specificity(selector):
    tag, ids, classes = selector
    return (len(ids), len(classes), 1 if tag else 0)
