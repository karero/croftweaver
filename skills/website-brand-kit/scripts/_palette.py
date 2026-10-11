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
    "muted": ("muted", "muted text", "secondary", "secondary text"),
    "accent": ("accent", "accent colour", "accent color"),
    "link": ("link", "links", "link colour", "link color"),
    "line": ("hairline", "line", "border", "borders", "divider"),
    "bg": ("background", "bg", "page background", "background (page)"),
    "bg_soft": ("soft background", "background soft", "soft bg", "bg soft", "background (soft)", "alt background"),
    "surface": ("surface", "surface (cards)", "cards", "card", "card surface"),
    "brand": ("primary", "brand", "brand primary", "primary colour", "primary color"),
}
_KEY_OF_ALIAS = {a: k for k, names in _ALIASES.items() for a in names}

_PROPOSED = re.compile(r"\(\s*proposed\s*\)", re.I)
_INNER = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch)\([^)]*\)", re.I)


class Palette(object):
    def __init__(self):
        self.light = {}
        self.dark = {}
        self.brand = None
        self.proposed = set()   # {(theme, key)} values marked "(proposed)": shown, never written
        self.problems = []      # [(theme, key, code, message)] cells that could not be read
        self.ignored = []       # row labels this check has no use for

    def theme(self, name):
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
    """(hex or None, proposed, refusal or None) for one table cell."""
    t = re.sub(r"[`*]", "", cell).strip()
    proposed = bool(_PROPOSED.search(t))
    t = _PROPOSED.sub("", t).strip()
    if not t or "[" in t or t in ("-", "—", "–"):
        return None, proposed, None  # not filled in yet
    try:
        return _colour.parse_colour(t), proposed, None
    except Refusal as first:
        for m in _INNER.finditer(t):
            try:
                return _colour.parse_colour(m.group(0)), proposed, None
            except Refusal:
                pass
        return None, proposed, first


def _cells(line):
    parts = line.strip().strip("|").split("|")
    return [c.strip() for c in parts]


def _section_of(text):
    t = re.sub(r"[#*_`:]", " ", text).lower()
    light, dark = "light" in t, "dark" in t
    if light and not dark:
        return "light"
    if dark and not light:
        return "dark"
    if "brand" in t and not light and not dark:
        return "brand"
    return None


def parse_tables(text):
    """The palette in a BRAND.md, or in whatever the owner pasted. Raises Refusal("palette-ambiguous")
    when it holds two different values for one row (two palettes pasted together)."""
    p = Palette()
    fixed = {}
    section = None
    columns = None       # None: a plain Token | Hex table; else {"light": i, "dark": j}
    in_table = False

    def put(theme, key, value, proposed):
        target = p.theme(theme)
        if key in target and target[key] != value:
            raise Refusal(
                "palette-ambiguous",
                "The palette gives two different values for %s in the %s theme (%s and %s). Two palettes look to have "
                "been pasted together: paste only the one you chose." % (LABEL[key], theme, target[key], value),
            )
        target[key] = value
        if proposed:
            p.proposed.add((theme, key))

    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            in_table, columns = False, None
            if s.startswith("#"):
                section = _section_of(s)
            elif s:
                plain = re.sub(r"[#*_`:]", "", s).strip()
                if len(plain) <= 60 and _section_of(plain):
                    section = _section_of(plain)
            continue
        cells = _cells(s)
        if all(re.match(r"^:?-{2,}:?$|^$", c) for c in cells):
            continue
        if not in_table:
            in_table = True
            low = [re.sub(r"[`*_]", "", c).strip().lower() for c in cells]
            li = next((i for i, c in enumerate(low) if i > 0 and "light" in c), None)
            di = next((i for i, c in enumerate(low) if i > 0 and "dark" in c), None)
            columns = {"light": li, "dark": di} if li is not None and di is not None else None
            continue  # the header row
        key = _key(cells[0])
        if key is None:
            p.ignored.append(re.sub(r"[`*]", "", cells[0]).strip())
            continue
        if columns:
            for theme in THEMES:
                v, proposed, err = _cell(cells[columns[theme]] if columns[theme] < len(cells) else "")
                if key == "brand":
                    continue
                if v:
                    put(theme, key, v, proposed)
                elif err:
                    p.problems.append((theme, key, err.code, "%s (%s theme): %s" % (LABEL[key], theme, err)))
            continue
        found, err, proposed = None, None, False
        for c in cells[1:]:
            v, pr, e = _cell(c)
            if v:
                found, proposed = v, pr
                break
            if e is None and c.strip():
                err = None  # a placeholder such as #[...]: the row is not filled in yet, which is not a mistake
                break
            err = err or e
        if section == "brand":
            if found and key == "brand":
                p.brand = found
            elif found and key == "accent":
                fixed["accent"] = (found, proposed)
            elif err and key in ("brand", "accent"):
                p.problems.append(("brand", key, err.code, "%s (brand table): %s" % (LABEL[key], err)))
        elif section in THEMES and key != "brand":
            if found:
                put(section, key, found, proposed)
            elif err:
                p.problems.append((section, key, err.code, "%s (%s theme): %s" % (LABEL[key], section, err)))
        elif found or err:
            p.problems.append(("?", key, "palette-no-theme",
                               "%s has a value but no heading says which theme it belongs to (light or dark)." % LABEL[key]))
    if "accent" in fixed:
        for theme in THEMES:
            if "accent" not in p.theme(theme):
                put(theme, "accent", fixed["accent"][0], fixed["accent"][1])
    return p


# --- the matrix ------------------------------------------------------------------------

Pair = namedtuple("Pair", "theme fg bg fg_hex bg_hex ratio need ok")


def matrix(palette):
    """Every text colour on every background colour, in both themes, for the rows the palette has."""
    out = []
    for theme in THEMES:
        t = palette.theme(theme)
        for fg in TEXT:
            for bg in BACKGROUNDS:
                if fg in t and bg in t:
                    r = _colour.ratio(t[fg], t[bg])
                    out.append(Pair(theme, fg, bg, t[fg], t[bg], r, NEED_TEXT, r >= NEED_TEXT))
    return out


def describe(pair):
    verdict = "passes" if pair.ok else "FAILS"
    return "%s %s: %s %s on %s %s is %s to 1; text needs %s to 1" % (
        verdict, pair.theme, LABEL[pair.fg], pair.fg_hex, LABEL[pair.bg], pair.bg_hex,
        _colour.shown(pair.ratio), _colour.shown(pair.need))


# --- the stylesheet --------------------------------------------------------------------

class Css(object):
    def __init__(self):
        self.light, self.dark, self.dark_media = {}, {}, {}
        self.brand = None
        self.problems = []   # [(block, variable, message)]
        self.found = set()   # which of "light", "dark", "dark_media" the stylesheet has


def _blocks(css, depth=0):
    """[(selector, body, children)] for the top level of `css`; nested blocks (an @media) in children."""
    if depth > 6:
        raise Refusal("css-unreadable", "The stylesheet nests its blocks too deeply for this check to read.")
    out, i, n = [], 0, len(css)
    while i < n:
        o = css.find("{", i)
        if o < 0:
            break
        level, j = 1, o + 1
        while j < n and level:
            level += (css[j] == "{") - (css[j] == "}")
            j += 1
        if level:
            break
        body = css[o + 1:j - 1]
        selector = css[i:o].strip()
        if "{" in body:
            out.append((selector, "", _blocks(body, depth + 1)))
        else:
            out.append((selector, body, []))
        i = j
    return out


_DECL = re.compile(r"(--[\w-]+)\s*:\s*([^;{}]*)")
_ROOT = re.compile(r"^:root$")
_ROOT_DARK = re.compile(r"""^:root\[\s*data-theme\s*=\s*["']dark["']\s*\]$""")
_ROOT_MEDIA = re.compile(r"^:root:not\(\s*\[\s*data-theme\s*\]\s*\)$")
_MEDIA_DARK = re.compile(r"^@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)$")


def _declared(body):
    return {m.group(1): m.group(2).strip() for m in _DECL.finditer(body)}


def _resolve(value, declared, fallback):
    m = re.match(r"^var\(\s*(--[\w-]+)\s*\)$", value.strip())
    if m:
        name = m.group(1)
        value = declared.get(name, fallback.get(name, ""))
        if re.match(r"^var\(", value.strip()):
            return value
    return value


def read_css(text):
    """The colour tokens of a stylesheet's three blocks, as hex."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    css = Css()
    light_raw = {}
    for selector, body, children in _blocks(text):
        if _ROOT.match(selector):
            light_raw = _declared(body)
            _fill(css, "light", css.light, light_raw, {})
        elif _ROOT_DARK.match(selector):
            _fill(css, "dark", css.dark, _declared(body), light_raw)
        elif _MEDIA_DARK.match(selector):
            for sel2, body2, _ in children:
                if _ROOT_MEDIA.match(sel2):
                    _fill(css, "dark_media", css.dark_media, _declared(body2), light_raw)
    css.brand = css.light.pop("brand", None)
    return css


def _fill(css, block, target, declared, fallback):
    css.found.add(block)
    for var, raw in declared.items():
        key = KEY_OF_VARIABLE.get(var)
        if key is None:
            continue
        value = _resolve(raw, declared, fallback)
        try:
            target[key] = _colour.parse_colour(value)
        except Refusal as e:
            css.problems.append((block, var, str(e)))


def drift(palette, css):
    """Where BRAND.md and the stylesheet say different things: [(theme, key, doc_hex, css_hex)]."""
    out = []
    for theme, c in (("light", css.light), ("dark", css.dark)):
        for key in KEYS:
            if key in palette.theme(theme) and key in c and palette.theme(theme)[key] != c[key]:
                out.append((theme, key, palette.theme(theme)[key], c[key]))
    if palette.brand and css.brand and palette.brand != css.brand:
        out.append(("brand", "brand", palette.brand, css.brand))
    return out


def dark_blocks_disagree(css):
    """The two dark blocks must carry the same values: [(key, dark_block_hex, media_block_hex)]."""
    return [(k, css.dark[k], css.dark_media[k]) for k in KEYS if k in css.dark and k in css.dark_media and css.dark[k] != css.dark_media[k]]
