"""_site.py: the edits to a site's own files, and the journal that undoes them.

Each edit works on the text of one file and returns the new text. It changes the lines it must and no
others, and where the file is not laid out as the starter's is, it refuses and names the file and the
line it could not find (never guesses, never writes half). The Journal does the writing: it keeps what
was there, writes through a temporary file, and on rollback puts every file back, removes what the run
created (and only that), and leaves everything else alone. Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat

from _refusal import Refusal

REQUIRED_FILES = ("src/styles/global.css", "src/config.ts", "public/manifest.webmanifest", "scripts/generate_og_cards.py")

# The scaffold's own placeholder icons (the Astro logo). create-astro 5.2.6, `--template minimal`, run on
# 2026-10-11, wrote exactly these two files; they are replaced with a word to the owner, and an icon that is
# anything else is asked about. Nothing checks these hashes against a newer create-astro. One that changes
# the logo makes its placeholders "something else": a run that installs a logo then asks before it replaces
# them, instead of replacing them with a word, and a run that only changes colours leaves them alone and says
# so (it redraws public/favicon.svg only when that file is one this tool wrote).
SCAFFOLD_DEFAULTS = {
    "public/favicon.svg": {"2d7a310283d6f9cc753210d83224cd6db6348cb82a5536348884e5831d46203f"},
    "public/favicon.ico": {"09d2ac08d8cca9b6e1f90221f345a8c4dd0371c64a0dc52b6f96fc589b1e3d67"},
}


def is_scaffold_default(rel, data):
    return hashlib.sha256(data).hexdigest() in SCAFFOLD_DEFAULTS.get(rel, ())


def missing_files(site):
    """What a site must have for the intake to write into it, and lacks. Only a path with no file at it
    counts as lacking: one that cannot be looked at (a folder closed to this account) raises OSError."""
    out = []
    for r in REQUIRED_FILES:
        try:
            if not stat.S_ISREG(os.stat(os.path.join(site, *r.split("/"))).st_mode):
                out.append(r)
        except (FileNotFoundError, NotADirectoryError):
            out.append(r)
    return out


# --- global.css --------------------------------------------------------------------------

_ROOT = re.compile(r"(?m)^[ \t]*:root[ \t\n]*\{")
_DARK = re.compile(r"""(?m)^[ \t]*:root\[\s*data-theme\s*=\s*["']dark["']\s*\][ \t\n]*\{""")
_MEDIA = re.compile(r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)\s*\{")
_MEDIA_ROOT = re.compile(r":root:not\(\s*\[\s*data-theme\s*\]\s*\)\s*\{")


def _mask(text):
    """The same text with comments blanked (same length), so a selector in a comment is never found."""
    return re.sub(r"/\*.*?(\*/|\Z)", lambda m: " " * len(m.group()), text, flags=re.S)


def _block_end(masked, o):
    """Where the block that opened just before `o` closes (the end of the text when it never does)."""
    depth = 1
    for i in range(o, len(masked)):
        depth += (masked[i] == "{") - (masked[i] == "}")
        if not depth:
            return i
    return len(masked)


def _body(masked, opener, start, what, end=None):
    m = opener.search(masked, start, len(masked) if end is None else end)
    if not m:
        raise Refusal("css-layout", "src/styles/global.css has no %s, which the starter's stylesheet has. Edit the colours by hand, or restore that block." % what)
    o = m.end()
    c = masked.find("}", o)
    nested = masked.find("{", o)
    if c < 0 or 0 <= nested < c:
        raise Refusal("css-layout", "src/styles/global.css: %s is not a plain list of declarations." % what)
    return o, c


def _set(text, masked, span, values, what):
    o, c = span
    edits = []
    for var, value in values:
        # the value alone: a comment (blank in `masked`) or an `!important` between it and the `;` stays
        m = re.search(r"(?<![\w-])%s\s*:\s*(?P<v>[^;{}]*?)\s*(?:!\s*(?i:important)\s*)?(?=;)" % re.escape(var), masked[o:c])
        if not m:
            raise Refusal("css-layout", "src/styles/global.css: %s sets no %s. Add the line, or edit the colours by hand." % (what, var))
        edits.append((o + m.start("v"), o + m.end("v"), value))
    return edits


def edit_css(text, palette):
    """The palette in the stylesheet's three places: :root (light), :root[data-theme="dark"] and the
    :root:not([data-theme]) block inside @media (prefers-color-scheme: dark)."""
    import _palette as P
    masked = _mask(text)
    light = _body(masked, _ROOT, 0, "`:root` block (the light theme)")
    dark = _body(masked, _DARK, 0, "`:root[data-theme=\"dark\"]` block (the dark theme)")
    # each such @media block from its opening brace to its closing one: the dark block is looked for inside
    # one of them, never after it
    medias = [(m.end(), _block_end(masked, m.end())) for m in _MEDIA.finditer(masked)]
    if not medias:
        raise Refusal("css-layout", "src/styles/global.css has no `@media (prefers-color-scheme: dark)` block (the dark theme for visitors without JavaScript), which the starter's stylesheet has. Edit the colours by hand, or restore that block.")
    media_open, media_close = next(((o, c) for o, c in medias if _MEDIA_ROOT.search(masked, o, c)), medias[0])
    media = _body(masked, _MEDIA_ROOT, media_open, "`:root:not([data-theme])` block inside the `@media (prefers-color-scheme: dark)` block", media_close)
    # the Primary is one colour for both themes and is set in `:root` alone: a dark block that sets it again
    # (any such block, not only the one the dark values go into) would show another, so it is refused by name
    again = [(m.end(), 'the `:root[data-theme="dark"]` block (the dark theme)') for m in _DARK.finditer(masked)]
    again += [(m.end(), "the dark block inside the `@media (prefers-color-scheme: dark)` block") for o, c in medias for m in _MEDIA_ROOT.finditer(masked, o, c)]
    for o, what in again:
        if re.search(r"(?<![\w-])%s\s*:" % re.escape(P.VARIABLE["brand"]), masked[o:_block_end(masked, o)]):
            raise Refusal("css-primary-in-dark", "src/styles/global.css sets %s (the Primary) inside %s. The Primary is one colour for both themes, and this tool sets it in the "
                                        "`:root` block only, so the dark theme would go on showing another. Take that line out of the dark block, then run this again."
                          % (P.VARIABLE["brand"], what))
    edits = []
    light_vals = [(P.VARIABLE[k], palette.light[k]) for k in P.KEYS if k in palette.light]
    if palette.brand:
        light_vals.append((P.VARIABLE["brand"], palette.brand))
    dark_vals = [(P.VARIABLE[k], palette.dark[k]) for k in P.KEYS if k in palette.dark]
    edits += _set(text, masked, light, light_vals, "the `:root` block (the light theme)")
    edits += _set(text, masked, dark, dark_vals, "the `:root[data-theme=\"dark\"]` block (the dark theme)")
    edits += _set(text, masked, media, dark_vals, "the dark block inside the `@media (prefers-color-scheme: dark)` block")
    out = text
    for a, b, value in sorted(edits, reverse=True):
        out = out[:a] + value + out[b:]
    return out


# --- src/config.ts -----------------------------------------------------------------------

def _skip(text, i):
    """Where the comment or the string that opens at text[i] ends (the end of the text when it never
    does); i itself when neither opens there."""
    n = len(text)
    if text.startswith("//", i):
        j = text.find("\n", i)
        return n if j < 0 else j
    if text.startswith("/*", i):
        j = text.find("*/", i + 2)
        return n if j < 0 else j + 2
    if text[i] in "'\"`":
        j = i + 1
        while j < n and text[j] != text[i]:
            j += 2 if text[j] == "\\" else 1
        return min(j + 1, n)
    return i


def _blank(piece):
    return "".join("\n" if c == "\n" else " " for c in piece)


def _code(text):
    """The same text (same length, same line breaks) with comments and strings blanked: what is found in
    it is the program's own, not a copy of it that somebody commented out or quoted."""
    out, i, n = [], 0, len(text)
    while i < n:
        j = _skip(text, i)
        out.append(_blank(text[i:j]) if j > i else text[i])
        i = max(j, i + 1)
    return "".join(out)


def _own_level(block):
    """The same text (same length, same line breaks) with comments, strings and everything inside a nested
    {...}, [...] or (...) blanked: what is left is the object's own keys, each where it stands. A quoted
    name at the object's own level stays, because it may be a key ('themeColor': ...)."""
    out, depth, i, n = [], 0, 0, len(block)
    while i < n:
        ch, j = block[i], _skip(block, i)
        if j > i:
            name = depth == 1 and ch in "'\"" and re.fullmatch(r"[A-Za-z_$][\w$]*", block[i + 1:j - 1])
            out.append(block[i:j] if name else _blank(block[i:j]))
        else:
            j = i + 1
            if ch in "{[(":
                depth += 1
            elif ch in "}])":
                depth -= 1
            out.append(ch if depth <= 1 else _blank(ch))
        i = j
    return "".join(out)


def _own_value(text, const, key, value):
    """Where the quoted value of `key` stands in `export const <const> = {...}`, as (start, end) without
    the quotes, or None. The declaration is looked for outside comments and strings, and only the object's
    own key counts: not one of an object nested in it, of another object, or in a comment. A declaration or
    a key that stands twice is refused, because which one the site reads cannot be known from the text;
    `key` and 'key' are the same key."""
    code = _code(text)
    found = list(re.finditer(r"export const %s(?:[ \t]*:[^=\n]+)?\s*=\s*\{" % const, code))
    if len(found) > 1:
        raise Refusal("config-layout", "src/config.ts has `export const %s` twice, so it cannot be known which one the site reads. Leave one of them, then run this again." % const)
    if not found:
        return None
    start = found[0].end() - 1
    own = _own_level(text[start:_block_end(code, start + 1) + 1])
    # a key stands where an entry begins: straight after the object's opening brace or after a comma
    keys = [k for k in re.finditer(r"""(?<![\w$'"])(['"]?)%s\1\s*:""" % key, own) if own[:k.start()].rstrip()[-1:] in ("{", ",")]
    if len(keys) > 1:
        raise Refusal("config-layout", "src/config.ts sets `%s` twice in %s, so it cannot be known which line counts. Leave one of them, then run this again." % (key, const))
    m = re.compile(r"""[ \t]*(?=['"])""").match(text, start + keys[0].end()) if keys else None
    if not m:
        return None
    q, close = m.end(), _skip(text, m.end())
    inside = text[q + 1:close - 1]
    if "\\" in inside:
        raise Refusal("config-layout", "src/config.ts: the value of `%s` in %s has a backslash in it (an escaped quote, say), which this tool does not edit, because it "
                                       "could not be sure where the value ends. Write the value without it, then run this again." % (key, const))
    if close - 1 <= q or text[close - 1] != text[q] or "\n" in inside or not re.fullmatch(value, inside):
        return None
    return q + 1, close - 1


def company_logo(text):
    """What COMPANY.logo says now, or None when the line is not there."""
    span = _own_value(text, "COMPANY", "logo", r"[^\n]*")
    return text[span[0]:span[1]] if span else None


def theme_colour(text):
    """What SITE.themeColor says now, or None when the line is not there."""
    span = _own_value(text, "SITE", "themeColor", r"#[0-9a-fA-F]{3,8}")
    return text[span[0]:span[1]] if span else None


def edit_config(text, primary, logo=False):
    """SITE.themeColor is the primary (None: the colours are not being changed); with a logo,
    COMPANY.logo is the derived square PNG."""
    new = text
    if primary is not None:
        span = _own_value(new, "SITE", "themeColor", r"#[0-9a-fA-F]{3,8}")
        if not span:
            raise Refusal("config-layout", "src/config.ts has no `themeColor: '#...'` line in SITE. Set it by hand to %s." % primary)
        new = new[:span[0]] + primary + new[span[1]:]
    if logo:
        span = _own_value(new, "COMPANY", "logo", r"[^\n]*")
        if not span:
            raise Refusal("config-layout", "src/config.ts has no `logo: '...'` line in COMPANY. Set it by hand to '/images/logo.png'.")
        new = new[:span[0]] + "/images/logo.png" + new[span[1]:]
    return new


# --- public/manifest.webmanifest ---------------------------------------------------------

MANIFEST_COLOURS = ("theme_color", "background_color")


def manifest_colours(text):
    """The manifest's own "theme_color" and "background_color" as they are now, each a string, or None
    where the manifest cannot be read or does not hold one."""
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    return tuple(data.get(k) if isinstance(data, dict) and isinstance(data.get(k), str) else None for k in MANIFEST_COLOURS)


def edit_manifest(text, theme, background):
    """The manifest's own two colours. One that already says the right thing is not edited at all. One
    that must change is found by its name, and the name must stand once in the file: where another entry
    (a shortcut, say) has a colour of the same name, which line is the manifest's own cannot be known from
    the text, so it is refused and never edited by its place in the file."""
    now = dict(zip(MANIFEST_COLOURS, manifest_colours(text)))
    for key, value in zip(MANIFEST_COLOURS, (theme, background)):
        if now[key] == value:
            continue
        if len(re.findall(r'"%s"\s*:' % key, text)) > 1:
            raise Refusal("manifest-layout", "public/manifest.webmanifest has \"%s\" more than once (in another entry of it, a shortcut say, or twice in the manifest "
                                             "itself), so which line is the manifest's own cannot be known from the text. Set the manifest's own \"%s\" by hand to %s, "
                                             "then run this again." % (key, key, value))
        text, n = re.subn(r'("%s"\s*:\s*)"(?:[^"\\\n]|\\.)*"' % key, lambda m: m.group(1) + '"' + value + '"', text, count=1)
        if not n:
            raise Refusal("manifest-layout", "public/manifest.webmanifest has no \"%s\" line. Set it by hand to %s." % (key, value))
    # read back: what the manifest's own two colours are is known only from the file as a whole
    if manifest_colours(text) != (theme, background):
        try:
            json.loads(text)
        except ValueError:
            raise Refusal("manifest-layout", "public/manifest.webmanifest is not valid JSON after the colours were set, so it was not changed.") from None
        raise Refusal("manifest-layout", "public/manifest.webmanifest: its own \"theme_color\" and \"background_color\" could not be set. Set the manifest's own two "
                                         "by hand to %s and %s." % (theme, background))
    return text


# --- scripts/generate_og_cards.py --------------------------------------------------------

# The share cards are dark cards (light text on a deep background): the dark theme's colours. Title, subtitle
# and footer sit on a gradient between the dark surface and the dark background, and the palette check holds
# every one of these text colours to 4.5 to 1 on both. That says nothing of the rows in between (a grey that
# passes on white and on black is unreadable on the grey half way), so og_low_contrast looks at every row.
OG_COLOURS = (("BG_TOP", "surface"), ("BG_BOT", "bg"), ("TITLE_COL", "heading"), ("SUB_COL", "accent"),
              ("ACCENT", "accent"), ("FOOTER_COL", "muted"))
OG_TEXT = ("heading", "accent", "muted")  # the keys of TITLE_COL, SUB_COL and FOOTER_COL: what the cards write with
OG_ROWS = 630                             # the generator's H: its gradient has one colour per row of the card
OG_LOGO = 'ROOT / "public/images/logo.png"'


# With a logo the generator also draws an emblem: the logo, 460 pixels square, at a fifth of its strength
# (`a * 20 // 100`), from x = W - 460 + 70 = 810 and y = (H - 460) // 2 = 85. With it, the title and the
# subtitles may run to x = 64 + (W - 2 * 64 - 120) = 1016, so their right-hand end can lie on the emblem. The
# footer cannot: it is drawn at y = H - 52 = 578, below the emblem's last row (544). The wordmark is drawn in
# the title's colour at y = 54, with no limit to its width.
OG_EMBLEM_ROWS = (85, 545)                # the rows the emblem lies on (the last one not included)
OG_EMBLEM_STRENGTH = 0.2
OG_EMBLEM_TEXT = ("heading", "accent")    # the keys of TITLE_COL and SUB_COL: what can be written across the emblem


def _og_rows(palette, first=0, last=OG_ROWS):
    """The colours of the cards' background on the rows from `first` up to `last`, as (r, g, b), the way the
    generator's vgradient() draws them: from the dark surface at the top to the dark background at the bottom."""
    top, bot = (tuple(int(palette.dark[k][i:i + 2], 16) for i in (1, 3, 5)) for k in ("surface", "bg"))
    return {tuple(round(top[i] + (bot[i] - top[i]) * y / (OG_ROWS - 1)) for i in range(3)) for y in range(first, last)}


def og_low_contrast(palette):
    """The cards' text colours that fall under 4.5 to 1 somewhere on the cards' background, as [(key, hex,
    its lowest ratio)]. The background is worked out row by row the way the generator's vgradient() draws
    it, from the dark surface at the top to the dark background at the bottom, and compared unrounded."""
    import _colour
    import _palette as P
    rows = {"#%02x%02x%02x" % row for row in _og_rows(palette)}
    low = []
    for key in OG_TEXT:
        worst = min(_colour.ratio(palette.dark[key], row) for row in rows)
        if worst < P.NEED_TEXT:
            low.append((key, palette.dark[key], worst))
    return low


def og_emblem_low(palette, mark):
    """The same question where the emblem lies under the text: [(key, hex, its lowest ratio, the colour of
    the mark it is lowest over)] for the title's and the subtitles' colour, against each row the emblem
    covers mixed with each colour of the mark (`mark`, as hex) at the emblem's strength. Every row of the
    emblem is taken, a few more than text can stand on, and a colour of the mark counts as if it lay under
    the text at full strength: the check is a little stricter than the picture, never laxer."""
    import _colour
    import _palette as P
    paints = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in mark]
    low = []
    for key in OG_EMBLEM_TEXT:
        worst = min(((_colour.ratio(palette.dark[key], "#%02x%02x%02x" % tuple(round(row[i] + (paint[i] - row[i]) * OG_EMBLEM_STRENGTH) for i in range(3))), c)
                     for row in _og_rows(palette, *OG_EMBLEM_ROWS) for paint, c in zip(paints, mark)), default=None)
        if worst and worst[0] < P.NEED_TEXT:
            low.append((key, palette.dark[key], worst[0], worst[1]))
    return low


def og_colours(text):
    """The colours the generator's BRAND block holds now, as {name: "#rrggbb"}. A line that is not there,
    or is not three numbers from 0 to 255, is left out."""
    out = {}
    for name, _key in OG_COLOURS:
        m = re.search(r"(?m)^%s[ \t]*=[ \t]*\([ \t]*(\d+)[ \t]*,[ \t]*(\d+)[ \t]*,[ \t]*(\d+)[ \t]*\)" % name, text)
        if m and all(int(v) < 256 for v in m.groups()):
            out[name] = "#%02x%02x%02x" % tuple(int(v) for v in m.groups())
    return out


def _og_logo(text):
    return re.search(r"(?m)^LOGO[ \t]*=[ \t]*(?P<v>[^#\n]*?)[ \t]*(?:#.*)?$", text)


def og_logo(text):
    """What the generator's LOGO line says now: "none" (no emblem), "ours" (the picture this tool
    installs), "other" (a picture somebody pointed it at), or None when there is no such line."""
    m = _og_logo(text)
    if not m:
        return None
    value = m.group("v").strip()
    if value == "None":
        return "none"
    return "ours" if re.sub(r"\s+", "", value).replace("'", '"') == re.sub(r"\s+", "", OG_LOGO) else "other"


def edit_og(text, palette, logo, unwire=False):
    """The share-card generator's BRAND block: the dark theme's colours (palette None: the colours are
    not being changed) and, with a logo, the emblem. `unwire` takes the emblem out again where it is the
    picture this tool installs; an emblem that somebody pointed elsewhere is left as it is."""
    import _palette as P
    for name, key in (OG_COLOURS if palette is not None else ()):
        if key not in palette.dark:
            raise Refusal("palette-incomplete", "The share cards need the dark theme's %s colour, which the palette does not give." % P.LABEL[key])
    for name, key in (OG_COLOURS if palette is not None else ()):
        h = palette.dark[key]
        rgb = "(%d, %d, %d)" % tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        text, n = re.subn(r"(?m)^(%s[ \t]*=[ \t]*)\([ \t]*\d+[ \t]*,[ \t]*\d+[ \t]*,[ \t]*\d+[ \t]*\)" % name, lambda m: m.group(1) + rgb, text, count=1)
        if not n:
            raise Refusal("og-layout", "scripts/generate_og_cards.py has no `%s = (r, g, b)` line, so the share cards cannot be recoloured. Edit its BRAND block by hand." % name)
    if unwire:
        if og_logo(text) == "ours":
            m = _og_logo(text)
            text = text[:m.start("v")] + "None" + text[m.end("v"):]
    elif logo:
        m, now = _og_logo(text), og_logo(text)
        if not m:
            raise Refusal("og-layout", "scripts/generate_og_cards.py has no `LOGO = ...` line, so the emblem cannot be set. Edit its BRAND block by hand.")
        if now == "none":
            text = text[:m.start("v")] + OG_LOGO + text[m.end("v"):]
        elif now == "other":
            raise Refusal("og-layout", "scripts/generate_og_cards.py already points LOGO somewhere else (%s). Change it by hand if the new logo should be the emblem." % m.group("v").strip()[:60])
    return text


# --- .gitignore --------------------------------------------------------------------------

def add_ignore(text, line="brand-handoff/"):
    """The text with the folder's line added, or None when the folder is already ignored. In a .gitignore
    a later line that starts with `!` can take an earlier one back, and it need not name the folder to do
    so (`!*.svg`, `!*`, `!brand-*/`): the folder's own rule counts only when no such line comes after it,
    whatever that line spells; otherwise a fresh line goes at the end, where it wins. A rule is read the
    way git reads it: spaces before it are part of it, spaces after it are not. The added line ends as the
    file's own lines end."""
    ignored = False
    for existing in text.lstrip("\ufeff").splitlines():  # a byte order mark is not part of the first rule
        rule = existing.rstrip(" ")
        if re.fullmatch(r"/?brand-handoff(?:/\*?)?", rule):
            ignored = True
        elif rule.startswith("!"):
            ignored = False
    if ignored:
        return None
    end = "\r\n" if "\r\n" in text else "\n"
    return (text if not text or text.endswith("\n") else text + end) + line + end


# --- the journal -------------------------------------------------------------------------

def _why(error):
    return getattr(error, "strerror", None) or str(error)


def _under(rel, folder):
    return rel == folder or rel.startswith(folder + "/")


class Journal(object):
    """Everything the run changes in the site goes through here, and everything it may have to put back is
    noted here BEFORE it is changed, so that a run stopped at any moment still knows what to undo."""

    def __init__(self, site):
        self.site = os.path.realpath(site)
        self._orig = {}      # relative path -> (its bytes, or None when no file was there; its mode)
        self._made = []      # folders this run makes
        self._temps = []     # the temporary files it writes through
        self._kept = {}      # a folder kept as a whole -> ({its folders: mode}, {its files}, [folders that were not there])
        self.written = []
        self.undone = []     # what a putting back really changed

    def _path(self, rel):
        if (not isinstance(rel, str) or not rel or rel.startswith("/") or "\\" in rel or "\x00" in rel
                or os.path.isabs(rel) or ".." in rel.split("/")):
            raise Refusal("site-path", "The path %r is not inside the site." % str(rel)[:60])
        here = self.site
        for part in rel.split("/"):
            here = os.path.join(here, part)
            if os.path.islink(here):
                raise Refusal("site-path", "%s is a link, and nothing is written through a link." % rel)
        return os.path.join(self.site, *rel.split("/"))

    def read(self, rel):
        """The file's bytes, or None when no file is there. Only that is "not there": a file that is
        there and cannot be read raises OSError, and is never taken for a missing one."""
        path = self._path(rel)
        if os.path.isdir(path):
            raise Refusal("site-path", "%s is a folder." % rel)
        try:
            with open(path, "rb") as f:
                return f.read()
        except (FileNotFoundError, NotADirectoryError):
            return None

    def _mkdirs(self, path):
        todo = []
        d = path
        while not os.path.isdir(d):
            todo.append(d)
            d = os.path.dirname(d)
        for d in reversed(todo):
            self._made.append(d)   # noted first: a run stopped between the two lines still knows the folder is its own
            os.mkdir(d)

    def _put(self, path, data, mode=0o644):
        # through a temporary file beside it, whose name is noted before the file is made
        tmp = os.path.join(os.path.dirname(path), ".write-" + os.urandom(6).hex())
        self._temps.append(tmp)
        try:
            with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600), "wb") as f:
                f.write(data)
            os.chmod(tmp, mode)
            os.replace(tmp, path)
        except BaseException:
            if os.path.lexists(tmp):
                os.remove(tmp)
            raise

    def check(self, rel):
        """What can be known of a write before the first one is made: the path keeps the rules `write`
        holds it to, no file stands where a folder is needed (nor a folder where the file goes), and this
        account may write in the folder it goes into. Refuses in words; changes nothing."""
        path = self._path(rel)
        if os.path.isdir(path):
            raise Refusal("site-path", "%s is a folder, so a file of that name cannot be written." % rel)
        d = os.path.dirname(path)
        while not os.path.isdir(d):
            if os.path.lexists(d):
                raise Refusal("site-path", "%s cannot be written: %s is a file, not a folder." % (rel, os.path.relpath(d, self.site).replace(os.sep, "/")))
            d = os.path.dirname(d)
        if not os.access(d, os.W_OK | os.X_OK):
            where = os.path.relpath(d, self.site).replace(os.sep, "/")
            raise Refusal("site-path", "%s cannot be written: this account is not allowed to write in %s. Change the folder's permissions, then run this again."
                          % (rel, "the site's folder" if where == "." else where))

    def _note(self, rel):
        """Keep what a file is before the run first touches it: its bytes and its mode, or that it is not there."""
        if rel not in self._orig:
            path = self._path(rel)
            data = self.read(rel)
            self._orig[rel] = (data, 0o644 if data is None else stat.S_IMODE(os.stat(path).st_mode))

    def write(self, rel, data):
        path = self._path(rel)
        # the original is kept before the write, so that a run stopped half way through one still knows
        # it; rollback leaves alone a file that is as it was, so a write that failed costs nothing there
        self._note(rel)
        self._mkdirs(os.path.dirname(path))
        self._put(path, data, self._orig[rel][1])
        self.written.append(rel)

    def _restore(self, rel):
        """Put one file back as it was when the run first touched it: the same bytes and the same mode,
        or gone when no file was there. One that is already so is left alone. This is the one way a file
        is put back, whoever changed it: this run, the share-card generator, or the site's tests."""
        data, mode = self._orig[rel]
        path = self._path(rel)
        if not os.path.isdir(os.path.dirname(path)):
            if data is None:
                return
            raise OSError("its folder is no longer there")
        now = self.read(rel)
        if data is None:
            if now is not None:
                os.remove(path)
                self.undone.append(rel)
        elif now != data:
            self._put(path, data, mode)
            self.undone.append(rel)
        elif stat.S_IMODE(os.stat(path).st_mode) != mode:
            os.chmod(path, mode)
            self.undone.append(rel)

    def snapshot_dir(self, rel):
        """Keep a folder as it is, so that it can be put back to exactly that whatever is done to it
        (the share-card generator writes there without the journal). Each file in it goes on the same list
        of originals as a file this run writes, with its bytes and its mode; each folder in it (an empty one
        too) is noted with its mode. What cannot be kept is refused by name, before anything is written: a
        link, a folder that cannot be listed, a file that cannot be read, anything that is neither. A folder
        that is not there is kept as that: putting it back takes it away again."""
        path = self._path(rel)   # the folder itself, or one above it, being a link is refused here
        advice = "The share cards are made again in that folder, and this tool has to be able to put it back exactly as it was: %s, then run this again."
        dirs, files, missing = {}, set(), []
        if not os.path.lexists(path):
            d = path
            while not os.path.lexists(d):
                missing.append(d)
                d = os.path.dirname(d)
        elif not os.path.isdir(path):
            raise Refusal("site-path", "%s is a file, not a folder. %s" % (rel, advice % "move the file away"))
        todo = [""] if not missing else []
        while todo:
            sub = todo.pop()
            here = os.path.join(path, *sub.split("/")) if sub else path
            try:
                dirs[sub] = stat.S_IMODE(os.stat(here).st_mode)
                names = sorted(os.listdir(here))
            except OSError as e:
                raise Refusal("site-path", "%s cannot be listed (%s). %s" % ("/".join(filter(None, (rel, sub))), _why(e),
                                                                             advice % "open the folder to this account, or take it out")) from None
            for n in names:
                child = sub + "/" + n if sub else n
                p = os.path.join(here, n)
                try:
                    kind = os.lstat(p).st_mode
                    if stat.S_ISLNK(kind):
                        raise Refusal("site-path", "%s holds a link (%s). The share cards are made again in that folder, and nothing is written through a link: "
                                                   "replace the link with the file itself, or take it out." % (rel, child))
                    if stat.S_ISDIR(kind):
                        todo.append(child)
                    elif stat.S_ISREG(kind):
                        self._note(rel + "/" + child)
                        files.add(rel + "/" + child)
                    else:
                        raise Refusal("site-path", "%s/%s is neither a file nor a folder. %s" % (rel, child, advice % "take it out"))
                except OSError as e:
                    raise Refusal("site-path", "%s/%s cannot be read (%s). %s" % (rel, child, _why(e), advice % "open the file to this account, or take it out")) from None
        self._kept[rel] = (dirs, files, list(reversed(missing)))

    def _remove_tree(self, path, rel, left):
        """Remove a folder the kept folder did not have, with all that is in it. A link in it is removed
        as a link and never followed. Carries on after an error, and names in `left` what it could not remove."""
        try:
            os.chmod(path, stat.S_IMODE(os.stat(path).st_mode) | 0o700)
            names = os.listdir(path)
        except OSError as e:
            left.append((rel, _why(e)))
            return
        for n in names:
            p = os.path.join(path, n)
            if os.path.isdir(p) and not os.path.islink(p):
                self._remove_tree(p, rel + "/" + n, left)
            else:
                try:
                    os.remove(p)
                except OSError as e:
                    left.append((rel + "/" + n, _why(e)))
        try:
            os.rmdir(path)
            self.undone.append(rel)
        except OSError as e:
            left.append((rel, _why(e)))

    def restore_dir(self, rel):
        """Put a kept folder back to exactly what snapshot_dir saw, in place: the folder itself is never
        deleted and made again. Its folders are made where they are missing, what it did not hold is removed,
        each of its files is put back the way any other file is, and the folders get their modes back.
        Carries on after an error; returns [(path, why)] for what could not be put back."""
        path = self._path(rel)
        dirs, files, missing = self._kept[rel]
        left = []

        def here(sub):
            return os.path.join(path, *sub.split("/")) if sub else path

        def name(sub):
            return "/".join(filter(None, (rel, sub)))

        def not_a_folder(p):
            return os.path.islink(p) or (os.path.lexists(p) and not os.path.isdir(p))

        def clear(sub):
            # what the kept folder did not hold goes; what it held is looked into (a folder) or left for the files' turn
            for n in sorted(os.listdir(here(sub))):
                child = sub + "/" + n if sub else n
                p = os.path.join(here(sub), n)
                try:
                    if os.path.isdir(p) and not os.path.islink(p):
                        if child in dirs:
                            clear(child)
                        else:
                            self._remove_tree(p, name(child), left)
                    elif name(child) not in files or os.path.islink(p):
                        os.remove(p)
                        self.undone.append(name(child))
                except OSError as e:
                    left.append((name(child), _why(e)))

        for sub in sorted(dirs, key=lambda s: s.count("/") + bool(s)):   # the folder itself first, then down
            p = here(sub)
            try:
                if not_a_folder(p):
                    os.remove(p)
                if not os.path.isdir(p):
                    os.mkdir(p)
                    self.undone.append(name(sub))
                elif stat.S_IMODE(os.stat(p).st_mode) & 0o700 != 0o700:
                    os.chmod(p, stat.S_IMODE(os.stat(p).st_mode) | 0o700)   # one made read-only could not be worked in
            except OSError as e:
                left.append((name(sub), _why(e)))
        try:
            if not_a_folder(path):
                os.remove(path)
                self.undone.append(rel)
            elif os.path.isdir(path):
                clear("")
        except OSError as e:
            left.append((rel, _why(e)))
        for file in sorted(files):
            try:
                self._restore(file)
            except (OSError, Refusal) as e:
                left.append((file, _why(e)))
        for sub in sorted(dirs, key=lambda s: s.count("/") + bool(s), reverse=True):   # the deepest first, the folder itself last
            try:
                if os.path.isdir(here(sub)) and stat.S_IMODE(os.stat(here(sub)).st_mode) != dirs[sub]:
                    os.chmod(here(sub), dirs[sub])
                    self.undone.append(name(sub))
            except OSError as e:
                left.append((name(sub), _why(e)))
        for d in reversed(missing):   # a folder that was not there goes again, and so do the ones above it that were not there
            try:
                os.rmdir(d)
                self.undone.append(os.path.relpath(d, self.site).replace(os.sep, "/"))
            except FileNotFoundError:
                pass
            except OSError as e:
                left.append((os.path.relpath(d, self.site).replace(os.sep, "/"), _why(e)))
        return left

    def rollback(self):
        """Put every file back as it was, remove what the run made, leave the rest alone. Every file is
        tried, also after one could not be put back. Returns [(path, why)] for what could not be put back:
        empty when the site is as it was."""
        left = []
        for rel in list(self._kept):
            try:
                left.extend(self.restore_dir(rel))
            except (OSError, Refusal) as e:
                left.append((rel, _why(e)))
        for rel in reversed(list(self._orig)):
            if any(_under(rel, folder) for folder in self._kept):
                continue  # put back with its folder, above
            try:
                self._restore(rel)
            except (OSError, Refusal) as e:
                left.append((rel, _why(e)))
        for tmp in self._temps:
            try:
                os.remove(tmp)   # there only when a write was stopped before it could clear up after itself
            except OSError:
                pass
        for d in reversed(self._made):
            try:
                os.rmdir(d)
            except OSError:
                pass  # something that is not ours is in it, or it is gone
        return left
