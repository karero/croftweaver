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
    stylesheet in which the scan has such a problem is one this edit refuses, and one in which it has none
    is one this edit writes to, with the three exceptions below. That is said of the scan (`scan_css`), not
    of the reading (`read_css`). The reading names more than the scan does, and this edit does not refuse on
    what the reading alone names (a value that is no colour it reads, a `var()` it does not follow): it
    writes over such a value, where the palette gives that colour.

    The three things this edit refuses, by name, where the scan has no such problem:

    - a line for a colour the palette gives that is not there (the reading has no value for it);
    - a Primary (`--brand`) set again in a dark block. The reading says nothing of it either, so `palette
      --css` can end with 0 on a stylesheet this edit refuses;
    - under a palette that gives no Primary, a Primary that the reading of what this edit wrote names (a
      `var()`, a value that is no colour, the line set twice): it is refused, not written.

    A value that already IS the colour wanted is left as it stands, in whatever spelling the reading takes
    (`#FFF8EE`, `#fff`, `rgb(255, 248, 238)`, and `var(--accent)` where the accent of that block is, or
    is being set to, the colour wanted): a stylesheet that already holds the palette comes back byte for
    byte as it was. One exception: the Primary (`--brand`) is one colour for both themes, and a `var()`
    there shows each theme's own value of the variable it points at, so it is never left standing: the
    palette's Primary is written out as a colour over it, and where the palette gives no Primary this edit
    refuses and says so. A value the reading does not take for a colour is written
    over, also where it only looks like the colour wanted (a no-break space pasted beside it makes it none
    to a browser). A byte order mark at the start of the text stays where it is."""
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
    # the Primary is one colour for both themes and is kept in `:root` alone: a dark block that sets it again
    # shows one of its own, so it is refused by name (whether or not this palette gives a Primary to set)
    for block, what in (("dark", "the " + _PLACE["dark"]), ("dark_media", "the dark block inside the `@media (prefers-color-scheme: dark)` block")):
        if brand in sheet.spans.get(block, ()) or brand in sheet.unsure.get(block, ()):
            raise Refusal("css-primary-in-dark", "src/styles/global.css sets %s (the Primary) inside %s. The Primary is one colour for both themes and is kept in the "
                                        "`:root` block only: a line in a dark block gives the dark theme a Primary of its own, whatever the `:root` block says. Take "
                                        "that line out of the dark block, then run this again." % (brand, what))
    wanted = {(block, var): value for block, values in writes for var, value in values}

    def stays(block, var):
        """Does the line already show the colour wanted, as it stands? A `var()` shows what the variable it points at
        will hold once this edit is done."""
        now = sheet.value(block, var)
        m = P._VAR.fullmatch(now)
        if m and var == brand:
            return False  # the Primary is one colour for both themes: a `var()` shows each theme's own, so the colour is written out
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
    # with no Primary to set, its line stays: where the check cannot read it, the install would end "done" and the check name it
    said = [] if palette.brand else ["%s in %s: %s" % (v, P.BLOCK[b], m) for b, v, m in P.read_css(out).problems if (b, v) == ("light", brand)]
    if said:
        raise Refusal("css-primary-unreadable", " ".join(["src/styles/global.css: the brand colour (%s, the Primary) is not written as a colour this tool can read, and this palette "
                      "names no Primary to put in its place." % brand] + said + ["Write it out as a colour (`%s: #1a2b3c;`, with your colour), or give the palette a Primary (the `Primary` row in the table under `### Brand`), then run this again." % brand]))
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
# What set_lines goes by in src/config.ts (see its rule).
_COMMENT = r"/\*(?:[^*]|\*(?!/))*\*/"   # a comment that opens and closes on one line
_TEXT = r"'[^'\\]*'|\"[^\"\\]*\""       # a quoted text of the simple kind: no backslash in it, so it ends at its second quote
# A plain line of a block: blank, a comment, or one whole entry on one line.
_PLAIN = re.compile(r"[ \t]*(?:(?P<key>[A-Za-z_$][\w$]*)[ \t]*:[ \t]*(?:%s|-?\d[\w.]*|true|false|null)[ \t]*,[ \t]*)?(?:%s[ \t]*)*(?://.*)?$" % (_TEXT, _COMMENT))
_NOT_CODE = re.compile(r"(%s)|//.*|%s" % (_TEXT, _COMMENT))
_TS_TYPE = r"[\w$.<>,|&\[\] \t]+"   # a type after a constant's name: nothing in it can open a text, a comment or a bracket of code
_CLOSING = re.compile(r"\}[ \t]*(?:as[ \t]+const)?[ \t]*(?:satisfies[ \t]+%s)?[ \t]*;?[ \t]*(?://.*)?$" % _TS_TYPE)
_MARKS = ("...", "[", "\\u", "\\x", "/*", "`")
BOM = "\ufeff"


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


def _not_as_the_starter(rel, what, where, line, found, do=None, then="a line that already says this is left exactly as it is"):
    """The one kind of refusal set_lines makes: the line it looked for, what it found instead, what she can do.
    The line stands at the start of a line of its own, as it is to be written: nothing of the message is before it."""
    return Refusal(_CODE[rel], "%s: this tool sets %s only where the file has this one line%s:\n%s\nWhat it found instead: %s. %s, then run this again: %s."
                   % (rel, what, where, line, found, do or "Write that one line there yourself", then))


def set_lines(rel, text, want, where=None):
    """Set values in one of the three files that hold a colour, or the logo's address, beside the
    stylesheet: (the new text, [(name, what it said, what it says now)] for each value that changed).
    `want` is {name: value}: `themeColor` and `logo` in src/config.ts, `theme_color` and
    `background_color` in public/manifest.webmanifest, the six colour names in
    scripts/generate_og_cards.py (each colour as #rrggbb). `where`, a dict the caller hands in, is
    told the line each value of src/config.ts or of the generator stands on, set or left as it is:
    {name: the line's number, counted from 1}. A value of src/config.ts that is left as it stands on a
    line which is not surely the block's own (see below) gets no entry.

    A value is edited only on a line written as the starter writes it, and everything else is refused
    before anything is written. That keeps this tool from editing where it plainly should not; it does
    not show what the site reads. The read-back (_install.read_back) does: once the files are written
    it asks the site's own Node and Python, and a value that is not the one wanted ends the run with
    everything put back. Colours are compared as colours (`#ABC`, `#aabbcc` and `#AABBCCFF` are one),
    and a value that already is the one wanted is not edited, however it is spelt. A byte order mark at
    the start of a file is read past and kept.

    src/config.ts, by lines (this tool does not read TypeScript): `themeColor` in the block of `SITE`,
    `logo` in the block of `COMPANY`. What stands outside the block is not looked into: what it does to
    the value, the read-back sees.
    - The opening line: the one line of the file that starts `export const SITE`. It is `export const
      SITE = {`, with at most a type after the name and a `//` comment after the brace.
    - The closing line: the first line below it that starts with `}`. After the brace it holds at most
      `as const`, a `satisfies` clause, a `;` and a `//` comment.
    - The key, once: one line of the block begins with `themeColor:`. It holds the value in quotes (a
      colour as `#hex`; no backslash), a comma (only the block's last entry may leave it out) and at
      most a `//` comment.
    - Flat lines around it. A plain line is blank, a comment, or one whole entry `name: <value>,` (a
      quoted text without a backslash, a number, `true`, `false` or `null`). Every line above the
      key's line is plain. A line below it that is not plain holds none of `...`, `[`, `\\u`, `\\x`, a
      `/*` without its end, a backtick, a `\\` at its end, nor the key's name again: looked for
      outside quoted texts without a backslash and comments that end on the line.
    A second line that begins with the key, with only plain lines above it, is refused. A line that
    begins with the key below a line that is not plain may belong to something inside the block
    (`pwa: {`, then `themeColor: ...`): where every line of the key stands so, the block is not
    edited. A line end that TypeScript reads and this tool does not (a carriage return on its own,
    U+2028, U+2029) is refused. A key's line that already holds the value wanted is left as it stands,
    whatever stands around it, unless it has no comma after the value and more below it in the block.

    scripts/generate_og_cards.py, read with Python's own parser (`ast`) by the Python this tool runs
    on; a file it cannot read is refused with the parser's line, and so is a `from ... import *`.
    Every place that binds the colour's name is collected, anywhere in the module: an assignment's
    targets, `+=`, a name with a type, `:=`, `for`, `with`, a comprehension, an import, `def`,
    `class`, a parameter, `except ... as`, `global`, `nonlocal`, `del`, and where this Python has
    them a `match` capture and a type parameter. There must be exactly one: a plain assignment at the
    module's own level, alone on a line that starts with `NAME = (r, g, b)` (three whole numbers; a
    `# comment` may follow). A write the parser does not show as a binding (`globals()`, `setattr`,
    `exec`) is left to the read-back.

    public/manifest.webmanifest, read as JSON; a file that is not valid JSON is refused as that, and
    so is `NaN` or `Infinity`, which the site's `JSON.parse` does not take. What its top level holds
    is the truth. Where that is not yet the value wanted, the text is edited only when the quoted name
    stands exactly once in the file with a quoted value after it, and the result, read again, is the
    same manifest with that one value changed. Where the top level has no entry of the name, the advice
    is to add the line there, never to write over an entry of that name inside something else. Lines
    are counted as an editor counts them (LF, CRLF or a carriage return on its own), in the word on a
    file that is not valid JSON too.

    A refusal about a file as a whole (not JSON, not Python, `import *`) says so in a sentence of its
    own. Every other refusal is one kind of sentence: the line this tool looked for, with the value
    wanted, at the start of a line of its own exactly as it is to be written (for the manifest,
    without its comma where it would be the last entry); what it found instead, with the line
    numbers; and the one thing the owner can do, after which the next run goes through or says the
    next thing, not the same thing again. In src/config.ts that thing is the same for every refusal: to
    set the value in the file so that the site reads it. Whether it does, the caller asks the site's
    Node before it refuses (_install); where Node cannot be asked, the refusal comes again, with why.
    """
    mark, text = (BOM, text[len(BOM):]) if text.startswith(BOM) else ("", text)   # read past, and kept
    if rel == MANIFEST:
        text, changes = _set_manifest(text, want)
        return mark + text, changes
    if rel == GENERATOR:
        tree, lines = _python(text), _text_lines(text, r"\r\n|\r|\n")   # the lines as Python counts them
    else:
        lines = _text_lines(text)
    edits, changes = [], []
    for name, new in want.items():
        found = _config_line(lines, name, new, where) if rel == CONFIG else _generator_line(tree, lines, name, new, where)
        if found:
            start, end, old, written = found
            edits.append((start, end, written))
            changes.append((name, old, new))
    for start, end, written in sorted(edits, reverse=True):
        text = text[:start] + written + text[end:]
    return mark + text, changes


def _plain(line):
    """Whether a line of a block in src/config.ts is a plain one (see set_lines)."""
    return not line.endswith("\\") and bool(_PLAIN.match(line))


def _code(line):
    """(what of a line can be code, the quoted texts taken out of it): the line without its quoted texts of
    the simple kind, a `//` comment at its end, and comments that open and close on it. Where a quote is left
    over after that, this tool cannot tell where the line's texts end: the whole line then counts as code."""
    texts = []

    def out(m):
        if m.group(1):
            texts.append(m.group(1)[1:-1])
        return " "
    code = _NOT_CODE.sub(out, line)
    return (line, []) if "'" in code or '"' in code else (code, texts)


def _mark(code, texts, line, name):
    """What a line that is not plain holds that keeps this tool from editing the block, in words, or None.
    `code` is what of the line can be code, `texts` the quoted texts taken out of it (see _code)."""
    for mark in _MARKS:
        if mark in code:
            return "a backtick" if mark == "`" else "`%s`" % mark
    if line.endswith("\\"):
        return "a `\\` at its end"
    return "the name `%s` again" % name if name in texts or re.search(r"(?<![\w$])%s(?![\w$])" % name, code) else None


def _config_line(lines, name, new, where=None):
    """(start, end, the value now, the value to write) where the value of `name` must change; None where it
    already is `new`. Refuses whatever the rule in set_lines does not allow. `where` is told the number of the
    key's line (see set_lines)."""
    const, value, what, colour = _CONFIG[name]
    opening = "export const %s" % const

    def no(found):   # (the same thing to do for every refusal: _install asks the site's Node what it reads before it refuses)
        return _not_as_the_starter(CONFIG, what, ", in the block between the line `%s = {` and the next line that starts with `}`" % opening, "%s: '%s'," % (name, new), found,
                                   "Set the value in the file yourself so that the site reads it (keep every other entry as it is)", "this tool then asks the site's Node what the site reads")

    odd = [i for i, (line, _s) in enumerate(lines) if re.search("[\r\u2028\u2029]", line)]
    if odd:
        raise no("line %d holds a line end that TypeScript reads and this tool does not (a carriage return on its own, or one of Unicode's line separators)" % (odd[0] + 1))
    opens = [i for i, (line, _s) in enumerate(lines) if re.match(r"%s(?![\w$])" % re.escape(opening), line)]
    if not opens:
        raise no("no line that starts `%s`" % opening)
    if len(opens) > 1:
        raise no("%d lines (%s), not one, that start `%s`" % (len(opens), _at(opens), opening))
    top = opens[0]
    if lines[top][0].endswith("\\") or not re.match(r"%s(?:[ \t]*:[ \t]*%s)?[ \t]*=[ \t]*\{[ \t]*(?://.*)?$" % (re.escape(opening), _TS_TYPE), lines[top][0]):
        raise no("line %d opens the block another way: %s" % (top + 1, _quoted(lines[top][0])))
    close = next((i for i in range(top + 1, len(lines)) if lines[i][0].startswith("}")), None)
    if close is None:
        raise no("no line after line %d that starts with `}`" % (top + 1))
    # Each line of the block: what of it can be code, the texts taken out of it, whether it is plain. From the first
    # `/*` without its end, backtick or `\` at a line's end on, a line is taken as it stands, and is not plain.
    code, sure = {}, True
    for j in range(top + 1, close):
        raw = lines[j][0]
        code[j] = _code(raw) + (_plain(raw),) if sure else (raw, [], False)
        sure = sure and not ("/*" in code[j][0] or "`" in code[j][0] or raw.endswith("\\"))
    shape = re.compile(r"[ \t]*%s[ \t]*:[ \t]*(?P<q>['\"])(?P<v>%s)(?P=q)[ \t]*(?P<comma>,?)[ \t]*(?://.*)?$" % (name, value))

    def written(i):
        """A line of the block as the key's line is written, read: the match, or None."""
        return None if lines[i][0].endswith("\\") else shape.match(lines[i][0])

    def wanted(i):
        return bool(written(i)) and (_same_colour(written(i).group("v"), new) if colour else written(i).group("v") == new)

    cannot = "this tool cannot be sure from the text which value the site reads, so it does not edit this block"
    keys = [i for i in range(top + 1, close) if re.match(r"[ \t]*%s[ \t]*:" % name, lines[i][0])]
    # A line that begins with the key is surely the block's own where every line above it is plain: below a line that
    # is not, it may belong to something inside the block (`pwa: {` and, under it, `themeColor: ...`).
    deep = next((j for j in range(top + 1, close) if not code[j][2]), close)

    def inside(at, begins):
        """The refusal for lines that begin with the key below a line that is not plain."""
        one = len(at) == 1
        return no("%s `%s` (%s)%s below a line that is not one whole entry on one line (line %d: %s), so %s may belong to something inside the block. With that in the block %s"
                  % ("the one line of the block that begins with" if one else "%d lines of the block begin with" % len(at), begins, _at(at), " stands" if one else ", each",
                     deep + 1, _quoted(lines[deep][0]), "it" if one else "any of them", cannot))

    def runs_on(i):
        """Whether a line that `written` reads has no comma after the value while something stands below it in the
        block other than blank lines and comments: the value can then run on to the line below. (Asked only of such a
        line: one in `said`, which `wanted` read, and the key's line once `written` has read it.)"""
        return not written(i).group("comma") and any(not code[j][2] or _PLAIN.match(lines[j][0]).group("key") for j in range(i + 1, close))

    if not keys:
        quoted = [i for i in range(top + 1, close) if re.match(r"[ \t]*(['\"])%s\1[ \t]*:" % name, lines[i][0])]
        if len(quoted) == 1 and quoted[0] > deep:
            raise inside(quoted, lines[quoted[0]][0].split(":")[0].strip() + ":")
        if len(quoted) == 1:
            raise no("line %d is written another way: its key is in quotes (%s), and this tool takes the key as the starter writes it, without them" % (quoted[0] + 1, _quoted(lines[quoted[0]][0])))
        raise no("no line of the block (lines %d to %d) begins with `%s:`" % (top + 1, close + 1, name))
    own = [i for i in keys if i <= deep]
    if len(own) > 1:
        raise no("%d lines of the block begin with `%s:` (%s), so it cannot be known from the text which of them the site reads" % (len(own), name, _at(own)))
    said = [i for i in keys if wanted(i)]   # (asked where none is the block's own: one that she set by hand is taken as it stands, like any other line that needs no edit)
    if not own and (not said or runs_on(said[0])):   # (one that says the value with no comma after it, where the value can run on, is not taken as it stands)
        raise inside(keys, name + ":")
    key = (own or said)[0]
    line, start = lines[key]
    m = written(key)
    if not m:
        raise no("line %d is written another way: %s" % (key + 1, _quoted(line)))
    if runs_on(key):
        raise no("line %d is written another way: it has no comma after the value, so the value can run on to the line below it (%s)" % (key + 1, _quoted(line)))
    if where is not None and own:   # (a line that is not surely the block's own is not named as the place of the value)
        where[name] = key + 1
    old = m.group("v")
    if wanted(key):
        return None   # left as it stands, whatever the closing line and the lines around it are: the read-back is what says whether the site reads it
    if not _CLOSING.match(lines[close][0]):
        raise no("line %d closes the block with more than its `}` (%s): after the brace this tool takes `as const`, a `satisfies` clause, a `;` and a `//` comment, and nothing else. "
                 "With that on the closing line %s" % (close + 1, _quoted(lines[close][0]), cannot))
    # The flat lines below the key: asked only where this tool has to edit the line. (Every line above it is plain: the
    # line is the block's own.)
    marked = [j for j in range(key + 1, close) if (j in keys or not code[j][2]) and _mark(code[j][0], code[j][1], lines[j][0], name)]   # (a plain line names the key only as its own key)
    if marked:
        at = marked[0]
        raise no("line %d, in the same block, holds %s (%s). With that in the block %s" % (at + 1, _mark(code[at][0], code[at][1], lines[at][0], name), _quoted(lines[at][0]), cannot))
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
                                   "this Python, or run this tool with the Python the site uses, then run this again." % (GENERATOR, sys.version_info[0], sys.version_info[1], where, getattr(e, "msg", None) or str(e) or type(e).__name__)) from None
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


def _generator_line(tree, lines, name, new, where=None):
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
    if where is not None:
        where[name] = at + 1
    old = tuple(int(v) for v in m.group(2, 3, 4))
    if old == rgb:
        return None
    # a number over 255 is no colour: it is shown as it stands, and the line is set all the same
    return start + m.start("v"), start + m.end("v"), "#%02x%02x%02x" % old if max(old) < 256 else "(%d, %d, %d)" % old, "%d, %d, %d" % rgb


def _set_manifest(text, want):
    """The manifest's own colours, by the rule in set_lines. The line a refusal shows is the line as it can
    be written: without its comma where it would be the manifest's last entry (JSON takes no comma there),
    and with a word on which lines it replaces where the entry it replaces is not one line of its own (as
    far as the parser says the entry's value runs), and on what stands beside the entry there and is kept."""
    def no(key, new, found, do, last=False):
        return _not_as_the_starter(MANIFEST, 'the manifest\'s own "%s"' % key, ", at the manifest's top level", '"%s": "%s"%s' % (key, new, "" if last else ","), found,
                                   do + (" (with no comma after it, as shown: it is the manifest's last entry)" if last else ""))

    def not_json(constant):
        raise ValueError("it holds %s, which JSON does not have" % constant)

    def read(source, tops=None):
        try:   # NaN and the infinities: Python's reader takes them, the site's JSON.parse does not
            return json.loads(source, parse_constant=not_json, object_pairs_hook=None if tops is None else lambda pairs: tops.append(pairs) or dict(pairs))
        except (ValueError, RecursionError) as e:
            return e

    def first(key, new, found):
        """The refusal that says to write the line as a new entry, at the top of the manifest."""
        if not data:
            return no(key, new, found, "Write that one line on a line of its own between the manifest's `{` and its `}`", last=True)
        if not re.match(r"\s*\{[ \t]*[\r\n]", text):   # the opening brace has something after it on its line: there is no "first line under" it
            return no(key, new, found, "Write that one line on a line of its own right after the manifest's opening `{`")
        return no(key, new, found, "Write that one line as the first line under the manifest's opening `{`")

    data = read(text)
    if isinstance(data, Exception):
        said = str(data) or type(data).__name__
        if isinstance(data, json.JSONDecodeError):   # the parser counts lines by LF alone: its place is said in the lines an editor shows
            starts = [s for _line, s in _text_lines(text, r"\r\n|\r|\n") if s <= data.pos]
            said = "%s: line %d column %d (char %d)" % (data.msg, len(starts), data.pos - starts[-1] + 1, data.pos)
        raise Refusal("manifest-layout", "public/manifest.webmanifest is not valid JSON (%s), so this tool does not edit it. Mend the file so that it is valid JSON "
                                         "(the starter's manifest shows the form), then run this again." % said)
    if not isinstance(data, dict):
        raise Refusal("manifest-layout", "public/manifest.webmanifest does not hold one object in braces at its top level, as a web manifest does, so this tool does not "
                                         "edit it. Write it as the starter's manifest is written, then run this again.")
    changes = []
    for key, new in want.items():
        now = data.get(key)
        if _same_colour(now, new):
            continue
        lines = _text_lines(text, r"\r\n|\r|\n")   # every line number below is counted on these
        stands = [i for i, (line, _s) in enumerate(lines) for _m in re.finditer(re.escape('"%s"' % key), line)]
        tops = []
        read(text, tops)
        ends = bool(tops and tops[-1]) and tops[-1][-1][0] == key   # the manifest's own entry of that name is its last one
        if not stands:
            raise first(key, new, 'the name "%s" is not in the file' % key)
        if len(stands) > 1 and key not in data:   # none of them is the manifest's own: there is no line of its own to set the value on
            raise first(key, new, 'the name "%s" stands %d times in the file (%s), and none of them is an entry of the manifest\'s own' % (key, len(stands), _at(stands)))
        if len(stands) > 1:
            raise no(key, new, 'the name "%s" stands %d times in the file (%s), so the manifest\'s own line cannot be told from the text' % (key, len(stands), _at(stands)),
                     "Set the value yourself on the manifest's own line (the last line of that name at its top level)", last=ends)
        edited, n = re.subn(r'("%s"[ \t]*:[ \t]*)"(?:[^"\\\n]|\\.)*"' % key, lambda m: m.group(1) + '"%s"' % new, text, count=1)
        inside = 'the one place where "%s" stands (line %d) is not the manifest\'s own entry: it belongs to something inside the manifest' % (key, stands[0] + 1)
        if not n:
            at = stands[0]
            entry = re.search(r'"%s"\s*:\s*' % key, text)
            try:
                stop = json.JSONDecoder(parse_constant=not_json).raw_decode(text, entry.end())[1]   # where the entry's value ends
            except (AttributeError, ValueError):   # the name stands there as a text, not as the name of an entry: nothing is to be written in its place
                raise first(key, new, 'the name "%s" stands in the file (line %d) only as a text, not as the name of an entry' % (key, at + 1)) from None
            if key not in data:   # an entry of something inside the manifest (a number, or a value over several lines): hers, and left as it is
                raise first(key, new, inside)
            comma = re.match(r"\s*,", text[stop:])
            end = stop + (comma.end() if comma else 0)
            to = max(i for i, (_line, s) in enumerate(lines) if s < end)   # the line its value ends on, or the comma after it
            beside = [(word, n, part.strip(), side) for word, n, part, side in (("before", at, text[lines[at][1]:entry.start()], "above"), ("after", to, lines[to][0][end - lines[to][1]:], "below"))
                      if part.strip()]   # what shares the entry's first line and its last: the shown line cannot take the place of that
            found = "line %d is written another way: %s" % (at + 1, _quoted(lines[at][0]))
            last = not comma and text[stop:].lstrip()[:1] == "}"
            if to == at and beside:
                raise no(key, new, found + ", with something else before or after the entry on its line",
                         'Set the value yourself on line %d: put "%s", in its quotes, where the value of "%s" stands now' % (at + 1, new, key))
            if to == at:
                raise no(key, new, found, "Write that one line in its place", last=last)
            raise no(key, new, found + ", and its value runs on to line %d" % (to + 1), "Write that one line in place of lines %d to %d, which it replaces together%s" % (
                at + 1, to + 1, "".join(", and keep what stands %s the entry on line %d (%s) on a line of its own %s it" % (word, n + 1, _quoted(part), side) for word, n, part, side in beside)), last=last)
        after = read(edited)
        # compared as text: two readings of the same manifest are then the same whatever stands in them
        if isinstance(after, Exception) or json.dumps(after, sort_keys=True) != json.dumps(dict(data, **{key: new}), sort_keys=True):
            if key in data:   # the manifest has an entry of that name all the same: one whose name is not spelt in plain letters
                raise no(key, new, inside + ", and the manifest's own entry spells its name another way (with a `\\u` escape)", "Write that one line in place of the manifest's own entry", last=ends)
            raise first(key, new, inside)
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
        here, parts = self.site, rel.split("/")
        for n, part in enumerate(parts):
            here = os.path.join(here, part)
            if os.path.islink(here):   # the link is named, not what would have gone below it
                raise Refusal("site-path", "%s is a link, and nothing is written through a link%s. Put the file or folder itself where the link is (or move the link "
                                           "away), then run this again." % ("/".join(parts[:n + 1]), "" if n + 1 == len(parts) else " (%s is below it)" % rel))
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

    def _all_named(self, path, rel, named):
        """Whether a folder holds something, and nothing but what is named already: a path in `named`, or a
        folder of which the same is true. An empty folder, and one that cannot be listed, is not that."""
        try:
            names = os.listdir(path)
        except OSError:
            return False
        return bool(names) and all(
            rel + "/" + n in named or (os.path.isdir(os.path.join(path, n)) and not os.path.islink(os.path.join(path, n))
                                       and self._all_named(os.path.join(path, n), rel + "/" + n, named)) for n in names)

    def rollback(self):
        """Put every file back as it was, remove what the run made, leave the rest alone. Every file is
        tried, also after one could not be put back. Returns [(path, why)] for what could not be put back,
        each path once: empty when the site is as it was. A folder the run made and could not take away
        again is one of them (it was not there before), unless everything that is still in it is named
        already: one thing in it that nobody named, or a folder that cannot be listed, and it is named."""
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
                # a folder this run made is still there: said, unless all that it holds is named already
                rel = os.path.relpath(d, self.site).replace(os.sep, "/")
                if not self._all_named(d, rel, {other for other, _why_not in left}):
                    left.append((rel, _why(e)))
        for rel in self._kept:   # last, when nothing of this run is left in them: the folders above a kept folder that were not there
            self._prune(rel, left)
        named = set()
        return [(rel, why) for rel, why in left if not (rel in named or named.add(rel))]   # each path once
