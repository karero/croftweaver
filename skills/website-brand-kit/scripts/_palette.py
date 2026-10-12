"""_palette.py: the palette as BRAND.md holds it and as the stylesheet holds it, and the contrast
check between text colours and backgrounds.

BRAND.md has a table per theme (`### Light theme`, `### Dark theme`) and a fixed "Brand" table;
the stylesheet has the same colours in three blocks (`:root`, `:root[data-theme="dark"]`, and
the same dark values again inside `@media (prefers-color-scheme: dark)`). This reads both, says
what is missing or unreadable, names where they disagree, and runs the matrix: every text colour
on every background colour, in both themes, at WCAG AA's 4.5 to 1 for body text. Nothing here
writes a file. Standard library only.
"""

from __future__ import annotations

import re
from collections import namedtuple

import _colour
from _refusal import Refusal

# key, the row's label in BRAND.md, its CSS variable. The one written map from a row to a variable.
TOKENS = (
    ("heading", "Heading", "--heading"),
    ("ink", "Body (ink)", "--ink"),
    ("muted", "Muted", "--muted"),
    ("accent", "Accent", "--accent"),
    ("link", "Link", "--link"),
    ("line", "Hairline", "--line"),
    ("bg", "Background", "--bg"),
    ("bg_soft", "Soft background", "--bg-soft"),
    ("surface", "Surface (cards)", "--surface"),
)
BRAND_TOKEN = ("brand", "Primary", "--brand")
KEYS = tuple(t[0] for t in TOKENS)
LABEL = {t[0]: t[1] for t in TOKENS}
LABEL["brand"] = BRAND_TOKEN[1]
VARIABLE = {t[0]: t[2] for t in TOKENS}
VARIABLE["brand"] = BRAND_TOKEN[2]
KEY_OF_VARIABLE = {v: k for k, v in VARIABLE.items()}

TEXT = ("heading", "ink", "muted", "link", "accent")
BACKGROUNDS = ("bg", "bg_soft", "surface")
NEED_TEXT = 4.5  # WCAG AA, body text; BRAND.md's "4.5:1 body, 3:1 large"
THEMES = ("light", "dark")

_ALIASES = {
    "heading": ("heading", "headings", "heading text"),
    "ink": ("body", "body (ink)", "ink", "text", "body text"),
    "muted": ("muted", "muted text", "secondary text"),
    "accent": ("accent", "accent colour", "accent color"),
    "link": ("link", "links", "link colour", "link color"),
    "line": ("hairline", "line", "border", "borders", "divider"),
    "bg": ("background", "bg", "page background", "background (page)"),
    "bg_soft": ("soft background", "background soft", "soft bg", "bg soft", "background (soft)", "alt background"),
    "surface": ("surface", "surface (cards)", "cards", "card", "card surface"),
    "brand": ("primary", "brand", "brand primary", "primary colour", "primary color"),
}
_KEY_OF_ALIAS = {a: k for k, names in _ALIASES.items() for a in names}

_PROPOSED = re.compile(r"\(?\s*\bpropos(?:ed|al)\b\s*\)?", re.I)  # "(proposed)", "proposed", "(proposal)"
_PLACEHOLDER = re.compile(r"^#?\[[^\]]*\]$")  # "#[...]", "[hex]": the template's not-filled-in-yet
_INNER = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch)\([^)]*\)", re.I)
MISSING = "no value"  # stands where a hex would, in drift() and dark_blocks_disagree(), when one side has none


class Palette(object):
    def __init__(self):
        self.light = {}
        self.dark = {}
        self.brand = None
        self.proposed = set()   # {(theme, key)} values marked "(proposed)": shown, never written
        self.problems = []      # [(theme, key, code, message)] cells that could not be read
        self.ignored = []       # row labels this check has no use for
        self.unused = []        # [(label, [hex])] rows that hold a colour under a label this check does not know
        self.fixed_accent = set()  # themes whose Accent is the Brand table's one fixed Accent (the old layout)

    def theme(self, name):
        if name == "brand":  # the Primary is no theme's row; a proposed one is listed as ("brand", "brand")
            return {"brand": self.brand} if self.brand else {}
        return self.light if name == "light" else self.dark

    def missing(self):
        return [(t, k) for t in THEMES for k in KEYS if k not in self.theme(t)]


# --- reading BRAND.md or a pasted palette ----------------------------------------------

def _key(label):
    t = re.sub(r"[`*_]", "", label).strip().lower()
    t = re.sub(r"\s+", " ", t)
    if t in _KEY_OF_ALIAS:
        return _KEY_OF_ALIAS[t]
    return _KEY_OF_ALIAS.get(re.sub(r"\s*\(.*?\)\s*", "", t).strip())


def _cell(cell):
    """(hex or None, proposed, refusal or None, kind) for one table cell. `kind` is "colour" (a hex or
    a functional colour, alone or among words), "name" (a bare colour name), "empty", "placeholder"
    (not filled in yet) or "unread"."""
    t = re.sub(r"[`*]", "", cell).strip()
    proposed = bool(_PROPOSED.search(t))
    t = _PROPOSED.sub("", t).strip()
    if not t:
        return None, proposed, None, "empty"
    if t in ("-", "—", "–") or (_PLACEHOLDER.match(t) and not _INNER.search(t)):
        return None, proposed, None, "placeholder"
    try:
        return _colour.parse_colour(t), proposed, None, "name" if t.lower() in _colour.NAMES else "colour"
    except Refusal as first:
        inner = None
        for m in _INNER.finditer(t):
            try:
                return _colour.parse_colour(m.group(0)), proposed, None, "colour"
            except Refusal as e:
                inner = inner or e  # a see-through colour among words is named as that, not as unknown words
        return None, proposed, inner or first, "unread"


def _same_but_rounded(a, b):
    """Two six-digit hex colours no more than two steps apart in any channel."""
    return all(abs(int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) <= 2 for i in (1, 3, 5))


def _row(cells):
    """What the value cells of one row hold: (hex or None, proposed, refusal or None, clash). A cell
    with a hex or a functional colour is taken before one with a bare colour name (a "Name" column
    beside the value). Where two such cells hold different colours none is picked: `clash` is those
    colours. Reading stops at a placeholder: the row is not filled in yet, which is not a mistake."""
    exact, named, err, proposed = [], [], None, False
    for c in cells:
        v, pr, e, kind = _cell(c)
        proposed = proposed or pr
        if v:
            (named if kind == "name" else exact).append(v)
        elif kind == "placeholder":
            if not exact and not named:
                err = None
            break
        else:
            err = err or e
    values = list(dict.fromkeys(exact or named))
    if len(values) > 1 and all(_same_but_rounded(values[0], v) for v in values[1:]):
        values = values[:1]  # one colour written twice (a hex beside its rgb or hsl), a rounding step apart
    if len(values) > 1:
        return None, proposed, None, values
    if values:
        return values[0], proposed, None, []
    return None, proposed, err, []


def _cells(line):
    parts = line.strip().strip("|").split("|")
    return [c.strip() for c in parts]


def _section_of(text):
    """The theme (or the Brand table) a heading names, by whole words: "Highlights" names no theme."""
    t = re.sub(r"[#*_`:]", " ", text).lower()
    light, dark = bool(re.search(r"\blight\b", t)), bool(re.search(r"\bdark\b", t))
    if light and not dark:
        return "light"
    if dark and not light:
        return "dark"
    if re.search(r"\bbrand\b", t) and not light and not dark:
        return "brand"
    return None


_LABEL_LINE = re.compile(r"(?:^|[\s,;:/-])(?:light|dark|brand)(?:[ -](?:theme|mode|palette|colours|colors|scheme|table|version))?$")


def _label_of(line):
    """The theme a line that is not a heading names, when the whole line is a label for the table
    under it: without its emphasis marks, a closing colon and a bracketed remark, it ends in the
    theme's name ("**Palette 2, light theme**", "Dark theme:", "Brand (fixed)"). A sentence that only
    mentions a theme ("(pairs with the dark theme below)") is not a label."""
    t = re.sub(r"[*_`]", "", line).strip().lower().rstrip(":").strip()
    t = re.sub(r"\s*\([^()]*\)$", "", t).rstrip(":").strip()
    if len(t) > 60 or not _LABEL_LINE.search(t):
        return None
    return _section_of(t)


def parse_tables(text):
    """The palette in a BRAND.md, or in whatever the owner pasted. Raises Refusal("palette-ambiguous")
    when it holds two different values for one row (two palettes pasted together)."""
    p = Palette()
    fixed = {}           # the rows that are one colour in both themes: {"brand" or "accent": (hex, proposed)}
    section = None
    marked = False       # the heading or label over the table says "proposed": so is every row under it
    columns = None       # None: a plain Token | Hex table; else {"light": i, "dark": j}
    header_marked = False  # the table's own header row says "proposed"
    in_table = False
    # This table: has it begun; does any row hold a colour; its rows that hold none; is it the table a
    # heading or label announced by naming a theme (or the Brand table); and was that a heading naming
    # light or dark, whose table no line of text may file elsewhere.
    table = {"begun": False, "colour": False, "unread": [], "named": False, "heading": False}

    def clash(label, where, old, new):
        return Refusal(
            "palette-ambiguous",
            "The palette gives two different values for %s%s (%s and %s). Two palettes look to have "
            "been pasted together: paste only the one you chose." % (label, where, old, new),
        )

    def put(theme, key, value, proposed):
        target = p.theme(theme)
        if key in target and target[key] != value:
            raise clash(LABEL[key], " in the %s theme" % theme, target[key], value)
        target[key] = value
        if proposed:
            p.proposed.add((theme, key))

    def put_fixed(key, value, proposed):
        if key in fixed and fixed[key][0] != value:
            raise clash(LABEL[key], ", the one colour both themes share", fixed[key][0], value)
        fixed[key] = (value, proposed or (key in fixed and fixed[key][1]))

    def unread(theme, key, code, message, label, err):
        # A cell that is no colour at all ("700", "Inter") is a mistake in a table of colours and nothing
        # in any other table (type sizes, spacing). Which it is shows when the table ends.
        if err.code == "colour-unreadable":
            table["unread"].append(((theme, key, code, message), label))
        else:
            table["colour"] = True
            p.problems.append((theme, key, code, message))

    def end_table():
        if not table["begun"]:
            return
        if table["colour"] or table["named"]:  # a table of colours: one a row shows to be, or one a heading says is
            p.problems.extend(entry for entry, _label in table["unread"])
        else:
            p.ignored.extend(label for _entry, label in table["unread"])
        table.update(begun=False, colour=False, unread=[], named=False, heading=False)

    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            in_table = False
            if not s:
                continue  # a blank line inside a table does not end it: its columns stay as they were
            end_table()
            columns, header_marked = None, False
            if s.startswith("#"):
                section, marked = _section_of(s), bool(_PROPOSED.search(s))
                table.update(named=section is not None, heading=section in THEMES)
            elif _label_of(s) and not table["heading"]:
                section, marked = _label_of(s), bool(_PROPOSED.search(s))
                table.update(named=True)
            continue
        cells = _cells(s)
        if all(re.match(r"^:?-{2,}:?$|^$", c) for c in cells):
            continue
        if not in_table:
            in_table = True
            if not any(_cell(c)[0] for c in cells[1:]):  # the header row; a first row that holds a colour is a row
                end_table()  # after a blank line, a header starts another table
                table["begun"] = True
                li = next((i for i, c in enumerate(cells) if i > 0 and _section_of(c) == "light"), None)
                di = next((i for i, c in enumerate(cells) if i > 0 and _section_of(c) == "dark"), None)
                columns = {"light": li, "dark": di} if li is not None and di is not None else None
                header_marked = any(_PROPOSED.search(c) for c in cells)
                continue
        table["begun"] = True
        label = re.sub(r"[`*]", "", cells[0]).strip()
        key = _key(_PROPOSED.sub("", cells[0]))
        aside = marked or header_marked or bool(_PROPOSED.search(cells[0]))  # "proposed" said of the whole row
        if key is None:
            found, _proposed, _err, both = _row(cells[1:])
            p.ignored.append(label)
            if found or both:
                table["colour"] = True
                p.unused.append((label, [found] if found else both))
            continue
        if columns and key != "brand":
            aside = aside or any(_PROPOSED.search(c) for i, c in enumerate(cells) if i > 0 and i not in columns.values())
            for theme in THEMES:
                v, proposed, err, _kind = _cell(cells[columns[theme]] if columns[theme] < len(cells) else "")
                if v:
                    table["colour"] = True
                    put(theme, key, v, proposed or aside)
                elif err:
                    unread(theme, key, err.code, "%s (%s theme): %s" % (LABEL[key], theme, err), label, err)
            continue
        found, proposed, err, both = _row(cells[1:])
        proposed = proposed or aside
        one = key == "brand" or (section == "brand" and key == "accent")  # a colour that is the same in both themes
        theme = "brand" if one else section if section in THEMES else "?"
        name = LABEL[key] + (" (brand table)" if section == "brand" else "" if one or theme == "?" else " (%s theme)" % theme)
        if found or both:
            table["colour"] = True
        if both:
            p.problems.append((theme, key, "palette-two-values", "%s: the row holds two different colours (%s). Leave only the one "
                               "you mean in it." % (name, " and ".join(both))))
        elif one:  # the Primary wherever it stands, and the Brand table's Accent
            if found:
                put_fixed(key, found, proposed)
            elif err:
                unread(theme, key, err.code, "%s: %s" % (name, err), label, err)
        elif section in THEMES:
            if found:
                put(section, key, found, proposed)
            elif err:
                unread(theme, key, err.code, "%s: %s" % (name, err), label, err)
        elif section != "brand" and (found or err):
            no_theme = "%s has a value but no heading says which theme it belongs to (light or dark)." % LABEL[key]
            if found:
                p.problems.append(("?", key, "palette-no-theme", no_theme))
            else:
                unread("?", key, "palette-no-theme", no_theme, label, err)
    end_table()
    if "brand" in fixed:
        p.brand = fixed["brand"][0]
        if fixed["brand"][1]:
            p.proposed.add(("brand", "brand"))
    if "accent" in fixed:
        for theme in THEMES:
            if "accent" not in p.theme(theme):
                put(theme, "accent", fixed["accent"][0], fixed["accent"][1])
                p.fixed_accent.add(theme)
    return p


# --- the matrix ------------------------------------------------------------------------

Pair = namedtuple("Pair", "theme fg bg fg_hex bg_hex ratio need ok note", defaults=("",))


def matrix(palette):
    """Every text colour on every background colour, in both themes, for the rows the palette has."""
    out = []
    for theme in THEMES:
        t = palette.theme(theme)
        for fg in TEXT:
            for bg in BACKGROUNDS:
                if fg in t and bg in t:
                    r = _colour.ratio(t[fg], t[bg])
                    note = fixed_accent_note(palette, theme, fg)
                    out.append(Pair(theme, fg, bg, t[fg], t[bg], r, NEED_TEXT, r >= NEED_TEXT, note))
    return out


def fixed_accent_note(palette, theme, key):
    """What to say of a value that is not the theme's own: the old layout's one Accent, used in both."""
    if key == "accent" and theme in palette.fixed_accent:
        return "taken from the Brand table's Accent; give the %s theme its own" % theme
    return ""


def describe(pair):
    verdict = "passes" if pair.ok else "FAILS"
    return "%s %s: %s %s on %s %s is %s to 1; text needs %s to 1%s" % (
        verdict, pair.theme, LABEL[pair.fg], pair.fg_hex, LABEL[pair.bg], pair.bg_hex,
        _colour.shown(pair.ratio), _colour.shown(pair.need), " (%s)" % pair.note if pair.note else "")


# --- the stylesheet --------------------------------------------------------------------

class Css(object):
    def __init__(self):
        self.light, self.dark, self.dark_media = {}, {}, {}
        self.brand = None
        self.problems = []   # [(block, variable or None, message)]: a value it cannot read, or a block it did not find
        self.found = set()   # which of "light", "dark", "dark_media" the stylesheet has


def _unpaired():
    return Refusal(
        "css-unreadable",
        "The stylesheet's braces do not pair up (a { is never closed, or there is a } too many), so this check cannot "
        "tell where its blocks begin and end. Mend the stylesheet, then run this again.",
    )


def _after_string(css, j):
    """The index after the string that opens at css[j]."""
    quote, j = css[j], j + 1
    while j < len(css) and css[j] != quote:
        j += 2 if css[j] == "\\" else 1
    return j + 1


def _blocks(css, depth=0):
    """[(selector, body, children)] for the top level of `css`; nested blocks (an @media) in children.
    A brace inside a string is text, not a brace; braces that do not pair up are refused."""
    if depth > 6:
        raise Refusal("css-unreadable", "The stylesheet nests its blocks too deeply for this check to read.")
    out, i, n = [], 0, len(css)
    while i < n:
        o = i
        while o < n and css[o] != "{":
            if css[o] == "}":
                raise _unpaired()
            o = _after_string(css, o) if css[o] in "\"'" else o + 1
        if o >= n:
            break
        level, j = 1, o + 1
        while j < n and level:
            if css[j] in "\"'":
                j = _after_string(css, j)
                continue
            level += (css[j] == "{") - (css[j] == "}")
            j += 1
        if level:
            raise _unpaired()
        body = css[o + 1:j - 1]
        selector = css[i:o].rsplit(";", 1)[-1].strip()  # what stands before it and ends in ; is a statement (@import, @charset)
        children = _blocks(body, depth + 1) if "{" in body else []
        out.append((selector, "" if children else body, children))
        i = j
    return out


_DECL = re.compile(r"(--[\w-]+)\s*:\s*([^;{}]*)")
_ROOT = re.compile(r"^(?i::root)$")
_ROOT_DARK = re.compile(r"""^(?i::root\[\s*data-theme)\s*=\s*["']dark["']\s*\]$""")
_ROOT_MEDIA = re.compile(r"^(?i::root:not\(\s*\[\s*data-theme\s*\]\s*\))$")
_MEDIA_DARK = re.compile(r"^(?i:@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\))$")
# The three places the stylesheet keeps the palette: what each is called, and what is said when it is not found.
BLOCK = {"light": "the :root block", "dark": 'the :root[data-theme="dark"] block',
         "dark_media": "the @media (prefers-color-scheme: dark) block"}
_NOT_FOUND = (
    ("light", "The stylesheet has no :root { ... } block that this check can find. That is where the light theme's colours are "
              "kept, so they could not be read."),
    ("dark", 'The stylesheet has no :root[data-theme="dark"] { ... } block that this check can find. That is where the dark '
             "theme's colours are kept, so they could not be read."),
    ("dark_media", "The stylesheet has no @media (prefers-color-scheme: dark) block with :root:not([data-theme]) { ... } inside "
                   "it that this check can find. That is where the dark colours are kept a second time, for visitors without "
                   "JavaScript, so they could not be read."),
)


def _declared(body):
    return {m.group(1): m.group(2).strip() for m in _DECL.finditer(body)}


def _names(pattern, selector):
    """Is one of the selectors of a rule (`:root, html`) the one looked for?"""
    return any(pattern.match(part.strip()) for part in selector.split(","))


def _resolve(value, declared, fallback):
    m = re.match(r"^var\(\s*(--[\w-]+)\s*\)$", value.strip())
    if m:
        name = m.group(1)
        value = declared.get(name, fallback.get(name, ""))
        if re.match(r"^var\(", value.strip()):
            return value
    return value


def read_css(text):
    """The colour tokens of a stylesheet's three blocks, as hex. A block it does not find is named in
    `problems`; a stylesheet whose braces do not pair up is refused."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    css = Css()
    raw = {"light": {}, "dark": {}, "dark_media": {}}  # a block written twice is one block: the later lines win, as in a browser

    def take(block, body):
        css.found.add(block)
        raw[block].update(_declared(body))

    for selector, body, children in _blocks(text):
        if _names(_ROOT, selector):
            take("light", body)
        elif _names(_ROOT_DARK, selector):
            take("dark", body)
        elif _MEDIA_DARK.match(selector):
            for sel2, body2, _ in children:
                if _names(_ROOT_MEDIA, sel2):
                    take("dark_media", body2)
    _fill(css, "light", css.light, raw["light"], {})
    _fill(css, "dark", css.dark, raw["dark"], raw["light"])
    _fill(css, "dark_media", css.dark_media, raw["dark_media"], raw["light"])
    css.problems.extend((block, None, message) for block, message in _NOT_FOUND if block not in css.found)
    css.brand = css.light.pop("brand", None)
    return css


def _fill(css, block, target, declared, fallback):
    for var, raw in declared.items():
        key = KEY_OF_VARIABLE.get(var)
        if key is None:
            continue
        value = _resolve(raw, declared, fallback)
        try:
            target[key] = _colour.parse_colour(value)
        except Refusal as e:
            css.problems.append((block, var, str(e)))


def _said(css, block, key):
    """Has css.problems already said that this block's value for the row could not be read?"""
    return (block, VARIABLE[key]) in {(b, v) for b, v, _m in css.problems}


def drift(palette, css):
    """Where BRAND.md and the stylesheet say different things: [(theme, key, doc_hex, css_hex)]. A row
    BRAND.md has and the block lacks counts, with MISSING for the stylesheet's side. What css.problems
    names is not said again here: a block that is not there at all, a value that could not be read."""
    out = []
    for theme, c in (("light", css.light), ("dark", css.dark)):
        for key in KEYS:
            doc = palette.theme(theme).get(key)
            if doc and theme in css.found and doc != c.get(key) and not _said(css, theme, key):
                out.append((theme, key, doc, c.get(key, MISSING)))
    if palette.brand and "light" in css.found and palette.brand != css.brand and not _said(css, "light", "brand"):
        out.append(("brand", "brand", palette.brand, css.brand or MISSING))
    return out


def dark_blocks_disagree(css):
    """The two dark blocks must carry the same values: [(key, dark_block_hex, media_block_hex)], with
    MISSING on the side that lacks a variable the other has. What css.problems names (a block that is
    not there, a value that could not be read) is not said again here."""
    if not {"dark", "dark_media"} <= css.found:
        return []
    return [(k, css.dark.get(k, MISSING), css.dark_media.get(k, MISSING)) for k in KEYS
            if css.dark.get(k) != css.dark_media.get(k) and not _said(css, "dark", k) and not _said(css, "dark_media", k)]


# --- a mark against the palette --------------------------------------------------------

NEED_UI = 3.0  # a graphic (the mark) against the page behind it; BRAND.md's "3:1 large/UI"
MarkReport = namedtuple("MarkReport", "colours outside low")


def check_mark(colours, palette):
    """The colours of a mark against the palette: `outside` are colours the palette does not hold
    (never recoloured, the owner decides); `low` maps a theme to the (colour, ratio) pairs that
    fall under 3 to 1 on that theme's background."""
    held = {v for t in THEMES for v in palette.theme(t).values()}
    if palette.brand:
        held.add(palette.brand)
    outside = [c for c in colours if c not in held]
    low = {}
    for theme in THEMES:
        bg = palette.theme(theme).get("bg")
        if not bg:
            continue
        bad = [(c, _colour.ratio(c, bg)) for c in colours if _colour.ratio(c, bg) < NEED_UI]
        if bad:
            low[theme] = bad
    return MarkReport(list(colours), outside, low)
