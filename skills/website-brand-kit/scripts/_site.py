"""_site.py: the edits to a site's own files, and the journal that undoes them.

Each edit works on the text of one file and returns the new text. It changes the lines it must and no
others, and where the file is not laid out as the starter's is, it refuses and names the file and the
line it could not find (never guesses, never writes half). The Journal does the writing: it keeps what
was there, writes through a temporary file, and on rollback puts every file back, removes what the run
created (and only that), and leaves everything else alone. Standard library only.
"""

from __future__ import annotations

import errno
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

# The stylesheet's three colour blocks, as a refusal names them.
_PLACE = {"light": "`:root` block (the light theme)", "dark": '`:root[data-theme="dark"]` block (the dark theme)',
          "dark_media": "`:root:not([data-theme])` block inside the `@media (prefers-color-scheme: dark)` block"}


def edit_css(text, palette):
    """The palette in the stylesheet's three places: :root (light), :root[data-theme="dark"] and the
    :root:not([data-theme]) block inside @media (prefers-color-scheme: dark).

    It works from `_palette.scan_css`, the same reading of the stylesheet that `_palette.read_css` works
    from, and changes nothing but the values that scan found: each new value goes into exactly the place of
    the old one. Whatever that scan names as a problem for a block this edit has to write to, or for the
    stylesheet as a whole (a rule outside the three blocks that sets one of the colours, and the rest of the
    scan's list), is the reason it refuses, in the scan's own words, before anything is changed. So a
    stylesheet the reading takes without a word is one this edit can write to (or one that lacks a line for
    a colour, which is refused by name), and the other way round.

    A value that already IS the colour wanted is left as it stands, in whatever spelling the reading takes
    (`#FFF8EE`, `#fff`, `rgb(255, 248, 238)`, and `var(--accent)` where the accent of that block is, or
    is being set to, the colour wanted): a stylesheet that already holds the palette comes back byte for
    byte as it was."""
    import _palette as P
    sheet = P.scan_css(text)
    brand = P.VARIABLE["brand"]
    light = [(P.VARIABLE[k], palette.light[k]) for k in P.KEYS if k in palette.light]
    if palette.brand:
        light.append((brand, palette.brand))
    dark = [(P.VARIABLE[k], palette.dark[k]) for k in P.KEYS if k in palette.dark]
    writes = [(block, values) for block, values in (("light", light), ("dark", dark), ("dark_media", dark)) if values]
    stops = [t for t in sheet.problems if t.block is None or t.block in dict(writes)] if writes else []
    if stops:
        first = stops[0]
        if first.kind == "missing":
            head = "src/styles/global.css has no %s that this tool can write the colours into." % _PLACE[first.block]
        elif first.block is None or first.kind == "twice":
            head = "src/styles/global.css would not carry the palette after the colours were set."
        else:
            head = "src/styles/global.css: this tool cannot write the colours into the %s as it stands." % _PLACE[first.block]
        raise Refusal("css-layout", " ".join([head] + [t.message if t.variable is None else "%s in %s: %s" % (t.variable, P.BLOCK[t.block], t.message)
                                                       for t in stops] + ["Mend that in the stylesheet, or set the colours by hand."]))
    # the Primary is one colour for both themes and is set in `:root` alone: a dark block that sets it again
    # would show another, so it is refused by name
    for block, what in (("dark", "the " + _PLACE["dark"]), ("dark_media", "the dark block inside the `@media (prefers-color-scheme: dark)` block")):
        if brand in sheet.spans.get(block, ()) or brand in sheet.unsure.get(block, ()):
            raise Refusal("css-primary-in-dark", "src/styles/global.css sets %s (the Primary) inside %s. The Primary is one colour for both themes, and this tool sets it in the "
                                        "`:root` block only, so the dark theme would go on showing another. Take that line out of the dark block, then run this again."
                          % (brand, what))
    wanted = {(block, var): value for block, values in writes for var, value in values}

    def stays(block, var):
        """Does the line already show the colour wanted, as it stands? A `var()` shows what the variable it points at
        will hold once this edit is done."""
        now = sheet.value(block, var)
        m = P._VAR.fullmatch(now)
        if m and m.group(1) in P.KEY_OF_VARIABLE:
            home = block if m.group(1) in sheet.spans[block] else "light"
            at = P._points_at(sheet, block, m.group(1))[0]
            if at is None or P._VAR.fullmatch(at):
                return False  # it points at nothing the reading can follow, or at a line that points on: the reading follows one step only
            now = wanted.get((home, m.group(1)), at)
        return _same_colour(now, wanted[block, var])

    edits = []
    for block, values in writes:
        for var, value in values:
            if var not in sheet.spans[block]:
                raise Refusal("css-layout", "src/styles/global.css: the %s sets no %s. Add the line, or edit the colours by hand." % (_PLACE[block], var))
            if not stays(block, var):
                edits.append(sheet.spans[block][var] + (value,))
    out = text
    for a, b, value in sorted(edits, reverse=True):
        out = out[:a] + value + out[b:]
    return out


# --- src/config.ts, public/manifest.webmanifest, scripts/generate_og_cards.py ------------

CONFIG, MANIFEST, GENERATOR = "src/config.ts", "public/manifest.webmanifest", "scripts/generate_og_cards.py"
LOGO_ADDRESS = "/images/logo.png"
MANIFEST_COLOURS = ("theme_color", "background_color")

# The share cards are dark cards (light text on a deep background): the dark theme's colours. Title, subtitle
# and footer sit on a gradient between the dark surface and the dark background, and the palette check holds
# every one of these text colours to 4.5 to 1 on both. That says nothing of the rows in between (a grey that
# passes on white and on black is unreadable on the grey half way), so og_low_contrast looks at every row.
# The generator's LOGO line (an emblem on the cards) is not this tool's: it is neither read nor written here.
OG_COLOURS = (("BG_TOP", "surface"), ("BG_BOT", "bg"), ("TITLE_COL", "heading"), ("SUB_COL", "accent"),
              ("ACCENT", "accent"), ("FOOTER_COL", "muted"))
OG_TEXT = ("heading", "accent", "muted")  # the keys of TITLE_COL, SUB_COL and FOOTER_COL: what the cards write with
OG_ROWS = 630                             # the generator's H: its gradient has one colour per row of the card


def og_low_contrast(palette):
    """The cards' text colours that fall under 4.5 to 1 somewhere on the cards' background, as [(key, hex,
    its lowest ratio)]. The background is worked out row by row the way the generator's vgradient() draws
    it, from the dark surface at the top to the dark background at the bottom, and compared unrounded."""
    import _colour
    import _palette as P
    top, bot = (tuple(int(palette.dark[k][i:i + 2], 16) for i in (1, 3, 5)) for k in ("surface", "bg"))
    rows = {"#%02x%02x%02x" % tuple(round(top[i] + (bot[i] - top[i]) * y / (OG_ROWS - 1)) for i in range(3)) for y in range(OG_ROWS)}
    low = []
    for key in OG_TEXT:
        worst = min(_colour.ratio(palette.dark[key], row) for row in rows)
        if worst < P.NEED_TEXT:
            low.append((key, palette.dark[key], worst))
    return low


_HEX = r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})"
# name -> (the constant whose block holds it, what its quotes may hold, what it is called, whether it is a colour)
_CONFIG = {"themeColor": ("SITE", _HEX, "the theme colour", True),
           "logo": ("COMPANY", r"(?:(?!(?P=q))[^\\\n])*", "the address of the logo", False)}
_CODE = {CONFIG: "config-layout", MANIFEST: "manifest-layout", GENERATOR: "og-layout"}
# A plain line of a block in src/config.ts (see set_lines): blank, a `//` comment, or one whole entry on one line.
_PLAIN = re.compile(r"[ \t]*(?:(?P<key>[A-Za-z_$][\w$]*)[ \t]*:[ \t]*(?:'[^'\\]*'|\"[^\"\\]*\"|-?\d[\w.]*|true|false|null)[ \t]*,[ \t]*)?(?://.*)?$")
_TS_TYPE = r"[\w$.<>,|&\[\] \t]+"   # a type after a constant's name: nothing in it can open a text, a comment or a bracket of code
_MARKS = ("...", "[", "\\u", "\\x", "/*", "`")


def _same_colour(a, b):
    """Whether two values are one colour, however each is spelt (`#ABC`, `#aabbcc`, `#AABBCCFF`)."""
    import _colour
    try:
        return isinstance(a, str) and isinstance(b, str) and _colour.parse_colour(a) == _colour.parse_colour(b)
    except Refusal:
        return False


def _text_lines(text, ends=r"\n"):
    """[(a line without its line end, where it starts in the text)], whether the lines end in LF or CRLF."""
    out, at = [], 0
    for m in re.finditer(ends, text):
        raw = text[at:m.start()]
        out.append((raw[:-1] if raw.endswith("\r") else raw, at))
        at = m.end()
    out.append((text[at:], at))
    return out


def _at(numbers):
    """Line numbers as words: "line 4", "lines 4 and 9", "lines 4, 9 and 12"; a line that is there more than
    once is said once, with how often: "twice on line 4", "lines 4 and 9 (twice)"."""
    often = {}
    for n in numbers:
        often[n] = often.get(n, 0) + 1
    times = {1: "", 2: "twice"}
    if len(often) == 1:
        (n, count), = often.items()
        return "line %d" % (n + 1) if count == 1 else "%s on line %d" % (times.get(count, "%d times" % count), n + 1)
    words = ["%d%s" % (n + 1, " (%s)" % times.get(count, "%d times" % count) if count > 1 else "") for n, count in often.items()]
    return "lines %s and %s" % (", ".join(words[:-1]), words[-1])


def _quoted(line, most=70):
    line = " ".join(line.split())
    return "`%s`" % (line if len(line) <= most else line[:most] + " ...")


def _not_as_the_starter(rel, what, where, line, found, do=None):
    """The one kind of refusal set_lines makes: the line it looked for, what it found instead, what she can do.
    The line stands at the start of a line of its own, as it is to be written: nothing of the message is before it."""
    return Refusal(_CODE[rel], "%s: this tool sets %s only where the file has this one line%s:\n%s\nWhat it found instead: %s. %s, then run this again: a line "
                               "that already says this is left exactly as it is." % (rel, what, where, line, found, do or "Write that one line there yourself"))


def set_lines(rel, text, want, unchecked=None):
    """Set values in one of the three files that hold a colour, or the logo's address, beside the
    stylesheet: (the new text, [(name, what it said, what it says now)] for each value that changed).
    `want` is {name: value}: `themeColor` and `logo` in src/config.ts, `theme_color` and
    `background_color` in public/manifest.webmanifest, the six colour names in
    scripts/generate_og_cards.py (each colour as #rrggbb). `unchecked` is a list the caller hands in
    to be told of each value that was left as it stands without (b) and (c) of the rule below being
    met: (the file, the name, the number of the key's line, that line, the number of the line that
    (b) or (c) does not take). Line numbers count from 1.

    THE RULE. A value is edited only where the text leaves no doubt that the site reads it from that
    line. Everything else is refused, before anything is written. Colours are compared as colours
    (`#ABC`, `#aabbcc` and `#AABBCCFF` are one colour), and a value that already is the one wanted is
    no change and is not edited, however it is spelt.

    src/config.ts. This tool does not read TypeScript: it goes by lines. `themeColor` is set in the
    block of `SITE`, `logo` in the block of `COMPANY`.
    (a) The opening line. One line of the file starts `export const SITE`, and it is exactly
        `export const SITE = {`, with at most a type after the name (`export const SITE: Config = {`)
        and a `//` comment after the brace. A wrapper (`Object.freeze({`, `define({`) or anything else
        on that line is refused. The block ends with the first line below it that starts with `}`.
    (b) Above the key. The key's line is the one line of the block that begins, after blanks, with
        `themeColor:`. It holds the name, the value in quotes of either kind (a colour as `#hex`; no
        backslash), a comma (which only the block's last entry may leave out) and an optional `//`
        comment, and nothing else. EVERY line between the opening line and it is a PLAIN line: blank;
        a `//` comment; or one whole entry on one line, `name: <value>,`, whose value is a quoted text
        without a backslash, a number, `true`, `false` or `null`, with an optional `//` comment after
        the comma. Nothing else: no `{`, `[`, `(`, backtick, `/*`, spread, and no value that runs on
        to the next line. So the key's line is an entry of the block itself and is in no comment and
        no text, however it is indented. The refusal names the first line that is not plain, and says
        to move the key's line up to be the first line under the opening line.
    (c) Below the key, down to the closing line. A line that is not a plain line holds none of `...`,
        `[`, `\\u`, `\\x` (a spread, a computed key or a name spelt with an escape can set the value
        again without naming it), and none of `/*`, a backtick or a `\\` at its end (after those this
        tool can no longer tell a comment from code). Where moving the key's line up would not help
        (one of these would then stand below it), the refusal says that this tool cannot edit the
        block and that the value is to be set by hand. A key's line that already holds the value
        wanted is then taken as it stands, whatever (b) and (c) find above and below it: there is
        nothing to edit. That is never silent: where (b) or (c) would have refused an edit, the
        value goes on the caller's `unchecked` list, and the install says in a note that it did not
        check that the site reads the value from that line.
        The name a second time. Below the key's line the name does not stand again as a word, except
        in a `//` comment line and in the text or the comment of a plain line (`logoDark:
        '/images/logo-dark.png',` does not name `logo` again), and, once a line held `/*`, a backtick
        or a `\\` at its end, not there either. This is asked whatever the value is. Above the key the
        name may stand in a text or a comment: those lines are plain.
    (d) Above the opening line, a line that is not a `//` comment and holds `/*` or an odd number of
        backticks is refused: the block itself could be inside a comment or a text that runs over
        several lines. The refusal says to move the block to the top of the file.
    (e) Outside the block, its closing line included, a line that holds the constant's name and the
        key's name together (`SITE.themeColor`, `(SITE as any).themeColor = ...`), or `SITE[`, or
        `Object.assign(SITE`, is refused: the object can be changed there after it was written. A `//`
        comment line above the block does not count; one below it does, because there this tool
        cannot tell a comment from code. A file with a line end that TypeScript reads and this tool
        does not (a carriage return on its own, U+2028, U+2029) is refused.
    What this does not see (the file is taken for TypeScript that runs): code that changes the object
    without the constant's name and the key's name on one line (the object reached under another
    name, `const s = SITE;` and on a later line `s.themeColor = ...`; or through a function; or the
    key's name put together from pieces or held in a variable); a `}` at the start of a line that
    closes something inside the block and not the block; above the block, a backtick inside a quoted
    text or a regular expression, which is counted as a template string's; and a key's line that
    already holds the value wanted, in a block where (b) or (c) is not met, which is left as she set
    it and reported as not checked (the `unchecked` list, and the install's note).

    scripts/generate_og_cards.py. The file is read with Python's own parser (`ast`), by the Python
    this tool runs on; one it cannot read is refused by name with the parser's line. EVERY place that
    binds the colour's name is collected, anywhere in the module: the targets of an assignment
    (in a tuple and starred too), `+=` and the like, a name with a type, `:=`, the targets of `for`
    and `with` and of a comprehension, an import and its `as` name, a `def` or `class` of that name,
    a parameter, `except ... as`, `global` and `nonlocal`, `del`, and, where this Python has them,
    what a `match` captures and a type parameter. There must be exactly one, and it must be a plain
    assignment at the module's own level, alone on a line that starts with `NAME = (r, g, b)` (three
    whole numbers; a `# comment` after it is optional). A `from ... import *` anywhere is refused: it
    could bind the name. What this does not see: code that sets the name without writing it
    (`globals()[...]`, `exec`, `setattr` on the module).

    public/manifest.webmanifest. The file is read as JSON first; one that is not valid JSON is
    refused as that, and so is one that holds `NaN` or `Infinity`, which Python's reader takes and
    the site's `JSON.parse` does not. What its top level holds is the truth. Where that is not yet
    the value wanted, the text is edited only when the quoted name stands exactly once in the file
    with a quoted value after it, and the result, read back, is the same manifest with that one
    value changed.

    Three refusals are about a file as a whole and say so in a sentence of their own: a manifest that
    is not valid JSON, a generator this Python cannot read, a generator with `from ... import *`.
    Every other refusal is one kind of sentence: the line this tool looked for, in the starter's shape
    and with the value wanted, at the start of a line of its own exactly as it is to be written; what
    it found instead (with the line numbers); and the one thing the owner can do, after which the
    next run goes through or says the next thing, not the same thing again. A line of hers that
    already says the value is left as it is.
    """
    if rel == MANIFEST:
        return _set_manifest(text, want)
    if rel == GENERATOR:
        tree, lines = _python(text), _text_lines(text, r"\r\n|\r|\n")   # the lines as Python counts them
    else:
        lines = _text_lines(text)
    edits, changes = [], []
    for name, new in want.items():
        found = _config_line(lines, name, new, unchecked) if rel == CONFIG else _generator_line(tree, lines, name, new)
        if found:
            start, end, old, written = found
            edits.append((start, end, written))
            changes.append((name, old, new))
    for start, end, written in sorted(edits, reverse=True):
        text = text[:start] + written + text[end:]
    return text, changes


def _plain(line):
    """Whether a line of a block in src/config.ts is a plain one (see set_lines)."""
    return not line.endswith("\\") and bool(_PLAIN.match(line))


def _mark(line):
    """What a line holds that a line below the key may not hold unless it is plain, in words, or None."""
    for mark in _MARKS:
        if mark in line:
            return "a backtick" if mark == "`" else "`%s`" % mark
    return "a `\\` at its end" if line.endswith("\\") else None


def _config_line(lines, name, new, unchecked=None):
    """(start, end, the value now, the value to write) where the value of `name` must change; None where it
    already is `new`. Refuses whatever the rule in set_lines does not allow. A value that already is `new`
    in a block that (b) or (c) would not let this tool edit is noted on `unchecked` (see set_lines)."""
    const, value, what, colour = _CONFIG[name]
    opening = "export const %s" % const

    def no(found, do):
        return _not_as_the_starter(CONFIG, what, ", in the block between the line `%s = {` and the next line that starts with `}`" % opening, "%s: '%s'," % (name, new), found, do)

    odd = [i for i, (line, _s) in enumerate(lines) if re.search("[\r\u2028\u2029]", line)]
    if odd:
        raise no("line %d holds a line end that TypeScript reads and this tool does not (a carriage return on its own, or one of Unicode's line separators)" % (odd[0] + 1),
                 "Save the file with ordinary line ends")
    opens = [i for i, (line, _s) in enumerate(lines) if re.match(r"%s(?![\w$])" % re.escape(opening), line)]
    if not opens:
        raise no("no line that starts `%s`" % opening, "Write `%s = {` at the start of a line, that line below it, and the closing `}` at the start of a line below that" % opening)
    if len(opens) > 1:
        raise no("%d lines (%s), not one, that start `%s`" % (len(opens), _at(opens), opening), "Leave one `%s` in the file, with that line in it" % opening)
    top = opens[0]
    if lines[top][0].endswith("\\") or not re.match(r"%s(?:[ \t]*:[ \t]*%s)?[ \t]*=[ \t]*\{[ \t]*(?://.*)?$" % (re.escape(opening), _TS_TYPE), lines[top][0]):
        raise no("line %d opens the block another way: %s" % (top + 1, _quoted(lines[top][0])),
                 "Write the opening line as `%s = {` (a type after the name may stay, and a `//` comment after the brace), with that line as the first line under it" % opening)
    for i in range(top):
        line = lines[i][0]
        if not re.match(r"[ \t]*//", line) and ("/*" in line or line.count("`") % 2):
            raise no("line %d, above the block, holds %s, so this tool cannot tell from the text that the block is not inside a comment or a text that runs over several lines"
                     % (i + 1, "`/*`" if "/*" in line else "a backtick without its partner"), "Move the whole `%s` block to the top of the file" % opening)
    close = next((i for i in range(top + 1, len(lines)) if lines[i][0].startswith("}")), None)
    if close is None:
        raise no("no line after line %d that starts with `}`" % (top + 1), "Close the block with a `}` at the start of a line, with that line above it")
    word = re.compile(r"(?<![\w$])%s(?![\w$])" % name)
    for i, (line, _s) in enumerate(lines):   # (e): outside the block, its closing line included
        if top <= i < close or (i < top and re.match(r"[ \t]*//", line)):
            continue
        holds = ("`%s` and `%s`" % (const, name) if re.search(r"(?<![\w$])%s(?![\w$])" % const, line) and word.search(line) else
                 "`%s[`" % const if re.search(r"(?<![\w$.])%s[ \t]*\[" % const, line) else
                 "`Object.assign(%s`" % const if re.search(r"Object[ \t]*\.[ \t]*assign[ \t]*\([ \t]*%s(?![\w$])" % const, line) else None)
        if holds:
            raise no("line %d, outside the block, holds %s: there the object can be changed after it was written, so the block's own line need not be what the site reads" % (i + 1, holds),
                     "Take that out of line %d (the value belongs in the block itself)" % (i + 1))
    keys = [i for i in range(top + 1, close) if re.match(r"[ \t]*%s[ \t]*:" % name, lines[i][0])]
    first = "the first line under the opening line (line %d)" % (top + 1)
    if not keys:
        raise no("no line of the block (lines %d to %d) begins with `%s:`" % (top + 1, close + 1, name), "Write that one line as %s" % first)
    if len(keys) > 1:
        raise no("%d lines of the block begin with `%s:` (%s), so it cannot be known from the text which of them the site reads" % (len(keys), name, _at(keys)),
                 "Leave one of them, written as shown, and take the other%s out" % ("" if len(keys) == 2 else "s"))
    key = keys[0]
    line, start = lines[key]
    sure = True   # whether a line below the key that looks plain is one: not after `/*`, a backtick or a `\` at a line's end
    for j in range(key + 1, close):
        below = lines[j][0]
        if not (sure and _plain(below)):
            if word.search(below):
                raise no("line %d, below it in the same block, names `%s` again (%s), so it cannot be known from the text which value the site reads" % (j + 1, name, _quoted(below)),
                         "Take the name out of line %d" % (j + 1))
            sure = sure and not ("/*" in below or "`" in below or below.endswith("\\"))
    m = None if line.endswith("\\") else re.match(r"[ \t]*%s[ \t]*:[ \t]*(?P<q>['\"])(?P<v>%s)(?P=q)[ \t]*(?P<comma>,?)[ \t]*(?://.*)?$" % (name, value), line)
    if not m:
        raise no("line %d is written another way: %s" % (key + 1, _quoted(line)), "Write that one line in its place")
    if not m.group("comma") and any(lines[j][0].strip() and not re.match(r"[ \t]*//", lines[j][0]) for j in range(key + 1, close)):
        raise no("line %d is written another way: it has no comma after the value, so the value can run on to the line below it (%s)" % (key + 1, _quoted(line)), "Write that one line in its place")
    # (b) and (c): a refusal only where this tool has to edit the line; where it already says the value, a word to the caller
    other = [j for j in range(top + 1, close) if j != key and not _plain(lines[j][0])]
    marked = [j for j in other if _mark(lines[j][0])]
    cannot = bool(marked) and (marked[-1] > key or other[0] < key)
    at = next((j for j in marked if j > key), marked[0]) if cannot else other[0] if other and other[0] < key else None
    old = m.group("v")
    if _same_colour(old, new) if colour else old == new:
        if at is not None and unchecked is not None:
            unchecked.append((CONFIG, name, key + 1, line, at + 1))
        return None
    if cannot:
        raise no("line %d, in the same block, holds %s (%s). With that in the block this tool cannot be sure from the text which value the site reads, so it does not edit this block"
                 % (at + 1, _mark(lines[at][0]), _quoted(lines[at][0])), "Set the value by hand: write that one line in place of line %d" % (key + 1))
    if at is not None:
        raise no("line %d, above it in the block, is not one whole entry on one line (%s). Above the `%s` line this tool takes only blank lines, `//` comments and entries written "
                 "`name: 'text',` (or a number, true, false, null in place of the text), so that it is sure the line is the block's own" % (at + 1, _quoted(lines[at][0]), name),
                 "Move the `%s` line up to be %s" % (name, first))
    return start + m.start("v"), start + m.end("v"), old, new


def _python(text):
    """The generator as Python's parser reads it. Refuses a file this Python cannot read, and one with a
    `from ... import *` in it, which could bind any name."""
    import ast
    import sys
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError, MemoryError) as e:
        where = "line %d: " % e.lineno if getattr(e, "lineno", None) else ""
        raise Refusal("og-layout", "%s is not Python that this tool can read (Python %d.%d says: %s%s), so this tool does not edit it. Mend that so that the file runs under "
                                   "this Python, then run this again." % (GENERATOR, sys.version_info[0], sys.version_info[1], where, getattr(e, "msg", None) or str(e) or type(e).__name__)) from None
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
            raise Refusal("og-layout", "%s, line %d: `from %s import *` brings in names this tool cannot see, and one of them could be a colour of the share cards, so this "
                                       "tool does not edit the file. Name what is imported there in place of the `*`, then run this again."
                          % (GENERATOR, node.lineno, "." * node.level + (node.module or "")))
    return tree


def _bindings(tree, name):
    """Every node of the module that binds `name` (see set_lines for the list), in the order of the lines."""
    import ast
    kinds = tuple(getattr(ast, k) for k in ("MatchAs", "MatchStar", "MatchMapping", "TypeVar", "ParamSpec", "TypeVarTuple") if hasattr(ast, k))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            hit = node.id == name and not isinstance(node.ctx, ast.Load)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.ExceptHandler)):
            hit = node.name == name
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            hit = any((a.asname or a.name.split(".")[0]) == name for a in node.names)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            hit = name in node.names
        elif isinstance(node, ast.arg):
            hit = node.arg == name
        else:
            hit = isinstance(node, kinds) and name in (getattr(node, "name", None), getattr(node, "rest", None))
        if hit:
            found.append(node)
    return sorted(found, key=lambda n: (n.lineno, n.col_offset))


def _generator_line(tree, lines, name, new):
    """The same for one colour of the share-card generator: `new` is #rrggbb, the line holds three numbers."""
    import ast
    rgb = tuple(int(new[i:i + 2], 16) for i in (1, 3, 5))

    def no(found, do=None):
        return _not_as_the_starter(GENERATOR, "the share cards' colour %s" % name, ", beginning at the start of a line of its own, outside every function and `if`",
                                   "%s = (%d, %d, %d)" % ((name,) + rgb), found, do or "Write that one line there yourself, and set %s nowhere else in the file" % name)

    binds = _bindings(tree, name)
    if not binds:
        raise no("nothing in the file sets %s" % name, "Write that one line beside the generator's other colours")
    if len(binds) > 1:
        raise no("%s is set or bound %d times (%s), and Python uses the last one it runs" % (name, len(binds), _at([n.lineno - 1 for n in binds])))
    own = [s for s in tree.body if isinstance(s, ast.Assign) and len(s.targets) == 1 and s.targets[0] is binds[0]]
    at = binds[0].lineno - 1
    line, start = lines[at]
    m = re.match(r"%s[ \t]*=[ \t]*\((?P<v>[ \t]*(\d{1,9})[ \t]*,[ \t]*(\d{1,9})[ \t]*,[ \t]*(\d{1,9})[ \t]*)\)[ \t]*(?:#.*)?$" % name, line)
    if not own or own[0].col_offset or not m:
        # (a line can look right and be no assignment of the file's own: a parameter on a line by itself inside `def f(` ... `)`)
        raise no("line %d sets it another way: %s%s" % (at + 1, _quoted(line), ", which does not begin at the start of the line" if line[:1] in (" ", "\t") else
                                                         ", which is a part of something that runs over several lines" if m else ""))
    old = tuple(int(v) for v in m.group(2, 3, 4))
    if old == rgb:
        return None
    # a number over 255 is no colour: it is shown as it stands, and the line is set all the same
    return start + m.start("v"), start + m.end("v"), "#%02x%02x%02x" % old if max(old) < 256 else "(%d, %d, %d)" % old, "%d, %d, %d" % rgb


def _set_manifest(text, want):
    """The manifest's own colours, by the rule in set_lines."""
    def no(key, new, found, do):
        return _not_as_the_starter(MANIFEST, 'the manifest\'s own "%s"' % key, ", at the manifest's top level", '"%s": "%s",' % (key, new), found, do)

    def not_json(constant):
        raise ValueError("it holds %s, which JSON does not have" % constant)

    def read(source):
        try:
            return json.loads(source, parse_constant=not_json)   # NaN and the infinities: Python's reader takes them, the site's JSON.parse does not
        except (ValueError, RecursionError) as e:
            return e

    data = read(text)
    if isinstance(data, Exception):
        raise Refusal("manifest-layout", "public/manifest.webmanifest is not valid JSON (%s), so this tool does not edit it. Mend the file so that it is valid JSON "
                                         "(the starter's manifest shows the form), then run this again." % (str(data) or type(data).__name__))
    if not isinstance(data, dict):
        raise Refusal("manifest-layout", "public/manifest.webmanifest does not hold one object in braces at its top level, as a web manifest does, so this tool does not "
                                         "edit it. Write it as the starter's manifest is written, then run this again.")
    changes = []
    for key, new in want.items():
        now = data.get(key)
        if _same_colour(now, new):
            continue
        lines = _text_lines(text)
        stands = [i for i, (line, _s) in enumerate(lines) for _m in re.finditer(re.escape('"%s"' % key), line)]
        if not stands:
            raise no(key, new, 'the name "%s" is not in the file' % key, "Write that one line as the first line under the manifest's opening `{`")
        if len(stands) > 1:
            raise no(key, new, 'the name "%s" stands %d times in the file (%s), so the manifest\'s own line cannot be told from the text' % (key, len(stands), _at(stands)),
                     "Set the value yourself on the manifest's own line (the last line of that name at its top level)")
        edited, n = re.subn(r'("%s"[ \t]*:[ \t]*)"(?:[^"\\\n]|\\.)*"' % key, lambda m: m.group(1) + '"%s"' % new, text, count=1)
        if not n:
            raise no(key, new, "line %d is written another way: %s" % (stands[0] + 1, _quoted(lines[stands[0]][0])), "Write that one line in its place")
        after = read(edited)
        # compared as text: two readings of the same manifest are then the same whatever stands in them
        if isinstance(after, Exception) or json.dumps(after, sort_keys=True) != json.dumps(dict(data, **{key: new}), sort_keys=True):
            found = 'the one place where "%s" stands (line %d) is not the manifest\'s own entry: it belongs to something inside the manifest' % (key, stands[0] + 1)
            if key in data:   # the manifest has an entry of that name all the same: one whose name is not spelt in plain letters
                raise no(key, new, found + ", and the manifest's own entry spells its name another way (with a `\\u` escape)", "Write that one line in place of the manifest's own entry")
            raise no(key, new, found, "Write that one line as the first line under the manifest's opening `{`")
        changes.append((key, now, new))
        text, data = edited, after
    return text, changes


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
    # as the file's last line ends; one that has no end takes the end of the line before it
    end = "\r\n" if text[:text.rfind("\n") + 1].endswith("\r\n") else "\n"
    return (text if not text or text.endswith("\n") else text + end) + line + end


# --- the journal -------------------------------------------------------------------------

def _why(error):
    return getattr(error, "strerror", None) or str(error)


def _under(rel, folder):
    return rel == folder or rel.startswith(folder + "/")


MAX_KEPT = 200 * 1024 * 1024   # how much a folder that is kept as a whole may hold: its files are kept in memory
_LOCKS = getattr(stat, "UF_IMMUTABLE", 0) | getattr(stat, "SF_IMMUTABLE", 0) | getattr(stat, "UF_APPEND", 0) | getattr(stat, "SF_APPEND", 0)


def _locked(status):
    """Whether a file or folder is locked against change, as far as this platform says so in what stat
    returns: the `uchg` and `schg` flags of macOS and the BSDs (`chflags`). Linux's `chattr +i` is not in
    there, and Windows has no such flag: a file locked that way is found only when the write fails."""
    return bool(getattr(status, "st_flags", 0) & _LOCKS)


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
                raise Refusal("site-path", "%s is a link, and nothing is written through a link. Put the file or folder itself where the link is (or move the link "
                                           "away), then run this again." % rel)
        return os.path.join(self.site, *rel.split("/"))

    def read(self, rel):
        """The file's bytes, or None when no file is there. Only that is "not there": a file that is
        there and cannot be read raises OSError, and is never taken for a missing one."""
        path = self._path(rel)
        try:
            kind = os.lstat(path).st_mode
            if stat.S_ISDIR(kind):
                raise Refusal("site-path", "%s is a folder." % rel)
            if not stat.S_ISREG(kind):   # a pipe or a device: opening one can wait for ever
                raise Refusal("site-path", "%s is neither a file nor a folder (a pipe or a device, say), so it is not read." % rel)
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
        except BaseException as e:
            if os.path.lexists(tmp):
                os.remove(tmp)
            if isinstance(e, OSError) and e.filename:
                e.filename, e.filename2 = path, None   # the file that was to be written is the one to name, not the temporary one beside it
            raise

    def check(self, rel):
        """What can be known of a write before the first one is made, without opening anything: the path
        keeps the rules `write` holds it to; what stands at it now, if anything, is a plain file (not a
        folder, a pipe or a device) that is not locked; every folder above it that is there is a folder;
        and this account may write in the folder it goes into, which is not locked either. Refuses in
        words; changes nothing."""
        path = self._path(rel)

        def named(p):
            where = os.path.relpath(p, self.site).replace(os.sep, "/")
            return "the site's folder" if where == "." else where
        try:
            now = os.lstat(path)
        except (FileNotFoundError, NotADirectoryError):
            now = None
        if now is not None and stat.S_ISDIR(now.st_mode):
            raise Refusal("site-path", "%s is a folder, so a file of that name cannot be written. Move the folder away, then run this again." % rel)
        if now is not None and not stat.S_ISREG(now.st_mode):
            raise Refusal("site-path", "%s is neither a file nor a folder (a pipe or a device, say), so it cannot be replaced by the file this run writes. Take it out of "
                                       "the site, then run this again." % rel)
        if now is not None and _locked(now):
            raise Refusal("site-path", "%s cannot be written: the file is locked against change. Unlock it (on a Mac: chflags nouchg, or untick Locked in its Get Info "
                                       "window), then run this again." % rel)
        d = os.path.dirname(path)
        while not os.path.isdir(d):
            if os.path.lexists(d):
                raise Refusal("site-path", "%s cannot be written: %s is not a folder. Move it away, then run this again." % (rel, named(d)))
            d = os.path.dirname(d)
        if _locked(os.stat(d)):
            raise Refusal("site-path", "%s cannot be written: %s is locked against change. Unlock it (on a Mac: chflags nouchg, or untick Locked in its Get Info "
                                       "window), then run this again." % (rel, named(d)))
        if not os.access(d, os.W_OK | os.X_OK):
            raise Refusal("site-path", "%s cannot be written: this account is not allowed to write in %s. Change the folder's permissions, then run this again."
                          % (rel, named(d)))

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
        is put back, whoever changed it: this run, the share-card generator, or the site's tests.
        What stands at the path now is looked at before it is touched, and never opened unless it is a
        plain file: a link, a pipe or a device there is taken away (the link itself, not what it points
        at), and what was kept is put in its place."""
        data, mode = self._orig[rel]
        parent, _slash, name = rel.rpartition("/")
        folder = self._path(parent) if parent else self.site   # a folder above it that is now a link is refused: nothing is written through one
        path = os.path.join(folder, name)
        if not os.path.isdir(folder):
            if data is None:
                return
            raise OSError("its folder is no longer there")
        try:
            kind = os.lstat(path).st_mode
        except FileNotFoundError:
            kind = None
        if kind is not None and stat.S_ISDIR(kind):
            raise OSError("a folder now stands where the file was")
        if kind is not None and not stat.S_ISREG(kind):
            os.remove(path)
            kind = None
            if data is None:
                self.undone.append(rel)
        now = None if kind is None else self.read(rel)
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
        link, a folder that cannot be listed, a file that cannot be read, anything that is neither, a file
        or folder that is locked, and more than MAX_KEPT bytes in all (the files are kept in memory). A
        folder that is not there is kept as that: putting it back takes it away again."""
        path = self._path(rel)   # the folder itself, or one above it, being a link is refused here
        advice = "The share cards are made again in that folder, and this tool has to be able to put it back exactly as it was: %s, then run this again."
        dirs, files, missing = {}, set(), []
        total, largest = 0, (0, None)
        if not os.path.lexists(path):
            d = path
            while not os.path.lexists(d):
                missing.append(d)
                d = os.path.dirname(d)
            if not os.path.isdir(d):   # the folder cannot be made below something that is not a folder
                raise Refusal("site-path", "%s cannot be made: %s is a file, not a folder. %s" % (rel, os.path.relpath(d, self.site).replace(os.sep, "/"), advice % "move the file away"))
        elif not os.path.isdir(path):
            raise Refusal("site-path", "%s is a file, not a folder. %s" % (rel, advice % "move the file away"))
        todo = [""] if not missing else []
        while todo:
            sub = todo.pop()
            here = os.path.join(path, *sub.split("/")) if sub else path
            try:
                status = os.stat(here)
                if _locked(status):
                    raise Refusal("site-path", "%s is locked against change. %s" % ("/".join(filter(None, (rel, sub))), advice % "unlock it (on a Mac: chflags nouchg)"))
                dirs[sub] = stat.S_IMODE(status.st_mode)
                names = sorted(os.listdir(here))
            except OSError as e:
                raise Refusal("site-path", "%s cannot be listed (%s). %s" % ("/".join(filter(None, (rel, sub))), _why(e),
                                                                             advice % "open the folder to this account, or take it out")) from None
            for n in names:
                child = sub + "/" + n if sub else n
                p = os.path.join(here, n)
                try:
                    status = os.lstat(p)
                    kind = status.st_mode
                    if stat.S_ISREG(kind):
                        if _locked(status):
                            raise Refusal("site-path", "%s/%s is locked against change. %s" % (rel, child, advice % "unlock it (on a Mac: chflags nouchg)"))
                        total += status.st_size
                        if largest[1] is None or status.st_size > largest[0]:   # sizes only: two names are never compared, nor a name with none
                            largest = (status.st_size, child)
                        if total > MAX_KEPT:
                            raise Refusal("site-path", "%s holds more than %d MB, more than this tool keeps of a folder so that it can put it back (the largest file "
                                                       "it came to is %s, %d MB). Move what is not a share card out of that folder, then run this again."
                                          % (rel, MAX_KEPT // 1048576, rel + "/" + largest[1], largest[0] // 1048576))
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
                    elif name(child) not in files:   # one it held is put back in the files' turn, whatever stands there now
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
                    os.makedirs(p)   # with the folders above it, where the tests took those away too
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
        if missing:   # a folder that was not there goes again; the ones above it that were not there go last (see _prune)
            try:
                os.rmdir(path)
                self.undone.append(rel)
            except (FileNotFoundError, NotADirectoryError):
                pass   # it is not there, which is how it was
            except OSError as e:
                left.append((rel, _why(e)))
            self._prune(rel)
        return left

    def _prune(self, rel, left=None):
        """Take away the folders above a kept folder that were not there before the run, the deepest
        first, as far as they are empty. One that still holds something is left: while the run stands,
        that is a file this run wrote there (the logo, beside the share cards' folder). At the end of a
        rollback, when every file has been put back or removed, `left` is given, and a folder that is
        still there is named in it: it was not there, and what is in it is not this run's to delete."""
        for d in reversed(self._kept[rel][2][:-1]):
            try:
                os.rmdir(d)
                self.undone.append(os.path.relpath(d, self.site).replace(os.sep, "/"))
            except FileNotFoundError:
                pass
            except OSError as e:
                if left is not None:
                    left.append((os.path.relpath(d, self.site).replace(os.sep, "/"), _why(e)))

    def rollback(self):
        """Put every file back as it was, remove what the run made, leave the rest alone. Every file is
        tried, also after one could not be put back. Returns [(path, why)] for what could not be put back,
        each path once: empty when the site is as it was. A folder the run made and could not take away
        again is one of them (it was not there before), unless it only holds a file that is named already."""
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
            except FileNotFoundError:
                pass  # it is gone, which is how it was
            except OSError as e:
                # a folder this run made is still there: said, unless it only holds something that is named already
                rel = os.path.relpath(d, self.site).replace(os.sep, "/")
                if e.errno not in (errno.ENOTEMPTY, errno.EEXIST) or not any(_under(other, rel) for other, _why_not in left):
                    left.append((rel, _why(e)))
        for rel in self._kept:   # last, when nothing of this run is left in them: the folders above a kept folder that were not there
            self._prune(rel, left)
        named = set()
        return [(rel, why) for rel, why in left if not (rel in named or named.add(rel))]   # each path once
