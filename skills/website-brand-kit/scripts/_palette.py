"""_palette.py: the palette as BRAND.md holds it and as the stylesheet holds it, and the contrast
check between text colours and backgrounds.

BRAND.md has a table per theme (`### Light theme`, `### Dark theme`) and a fixed "Brand" table;
the stylesheet has the same colours in three blocks (`:root`, `:root[data-theme="dark"]`, and
the same dark values again inside `@media (prefers-color-scheme: dark)`). This reads both, says
what is missing or unreadable, names where they disagree, and runs the matrix: every text colour
on every background colour, in both themes, at WCAG AA's 4.5 to 1 for body text. Nothing here
writes a file. Standard library only.

Both readers read ONE form, the one this skill itself defines, and name everything else: the three
tables of templates/palette-prompt.md, and the three blocks of the starter's stylesheet as the
intake's own editor finds them. Neither guesses. An owner's colours in any other form are written
into this form by the assistant, not worked out here.
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

MISSING = "not set in this block"  # stands where a hex would, in drift() and dark_blocks_disagree(), when one side has none

MAX_LINE = 2000  # a table row longer than this is not a palette row, and is not read
HEADING = {"brand": "### Brand", "light": "### Light theme", "dark": "### Dark theme"}
# The names a row may have: the template's ten, and the two short forms the old template had. No others.
ROW_KEY = {label.lower(): key for key, label in LABEL.items()}
ROW_KEY.update({"body": "ink", "surface": "surface"})
# What `brand_intake.py palette` says when it found no palette row at all (rule 11).
FORM = (
    "This check reads the colours from three tables, each under its own heading on a line of its own: `### Brand` (one "
    "row, Primary), `### Light theme` and `### Dark theme` (the rows %s). Each table starts with the two lines "
    "`| Token | Hex |` and `|---|---|`, and each row is `| the row's name | the colour |`. The assistant can write "
    "your colours in that form." % ", ".join(t[1] for t in TOKENS)
)


class Palette(object):
    def __init__(self):
        self.light = {}
        self.dark = {}
        self.brand = None
        self.proposed = set()   # {(theme, key)} values marked "(proposed)": shown, never written
        self.problems = []      # [(theme, key or None, code, message)]: what could not be read, and why; key None: said of a whole table or line
        self.ignored = []       # names of palette rows that hold no colour and stand in a table that is not a table of colours
        self.unused = []        # [(label, [what its cells hold])] rows that hold a colour under a name this check does not know
        self.fixed_accent = set()  # themes whose Accent is the Brand table's one fixed Accent (the old layout)
        self.rows_found = 0     # palette rows found where they are read, filled in or not

    def theme(self, name):
        if name == "brand":  # the Primary is no theme's row; a proposed one is listed as ("brand", "brand")
            return {"brand": self.brand} if self.brand else {}
        return self.light if name == "light" else self.dark

    def missing(self):
        return [(t, k) for t in THEMES for k in KEYS if k not in self.theme(t)]


# --- reading BRAND.md or a pasted palette ----------------------------------------------

_SECTION = re.compile(r"(brand|light theme|dark theme)(?: ?\(([^()]*)\))?")
_MARK = re.compile(r"\bpropos(?:ed|al)\b", re.I)
_MARK_AFTER = re.compile(r"(?: ?\( ?propos(?:ed|al) ?\)| propos(?:ed|al))$", re.I)
_SEPARATOR = re.compile(r":?-+:?")
_PLACEHOLDER = re.compile(r"#?\[([^\[\]#0-9]*)\]|#?(?:\.\.\.|…)|[-–—]")
# What looks like a colour inside a longer text: a # with letters or digits after it, a colour function, six or eight hex digits.
_COLOUR_LIKE = re.compile(r"#[0-9a-z]{3}|\b(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb|color)\(|(?<![0-9a-z#])[0-9a-f]{6}(?:[0-9a-f]{2})?(?![0-9a-z])", re.I)
_VALUE_FORM = re.compile(r"#|[A-Za-z-]+\(")

# What one cell holds. kind: "colour" (exactly one colour: `value` is its hex, `named` says it was written as a colour
# name, `form` that it was written as a hex or a function), "refused" (exactly one colour that is not taken: `err` says
# why), "like" (something that looks like a colour, with something else or misspelt), "words", "empty", "placeholder".
Look = namedtuple("Look", "kind value text marked named form err")
Row = namedtuple("Row", "line label key cells looks above_separator long")


_EMPHASIS = re.compile(r"[*_`]")


def _plain(text):
    """A heading or a first cell as it is compared: without emphasis marks and backticks, in lower case."""
    return " ".join(_EMPHASIS.sub("", text).split()).lower()


def _quoted(text, most=60):
    return '"%s"' % (text if len(text) <= most else text[:most] + "...")


def _listed(names):
    names = list(dict.fromkeys(names))
    return names[0] if len(names) == 1 else "%s and %s" % (", ".join(names[:-1]), names[-1])


def _unwrap(text):
    if len(text) >= 2 and text[0] == "`" == text[-1] and "`" not in text[1:-1]:
        return text[1:-1].strip()
    return text


def _is_placeholder(text):
    m = _PLACEHOLDER.fullmatch(text)
    if not m:
        return False
    inner = (m.group(1) or "").strip().lower()
    return inner not in _colour.NAMES and not re.fullmatch(r"[0-9a-f]{3,8}", inner)


def _look(cell):
    """What one cell holds (see Look). A colour is a colour only when it is the whole cell: backticks may stand
    around it and the mark `(proposed)` after it, and nothing else."""
    marked = bool(_MARK.search(cell))
    text = _unwrap(cell)
    after = _MARK_AFTER.search(text)
    if after:
        text = _unwrap(text[:after.start()].strip())
    if not text:
        return Look("empty", None, cell, marked, False, False, None)
    if _is_placeholder(text):
        return Look("placeholder", None, cell, marked, False, False, None)
    form = bool(_VALUE_FORM.match(text))
    try:
        return Look("colour", _colour.parse_colour(text), text, marked, text.lower() in _colour.NAMES, form, None)
    except Refusal as e:
        if e.code != "colour-unreadable":
            return Look("refused", None, text, marked, False, form, e)
        return Look("like" if _COLOUR_LIKE.search(cell) else "words", None, cell, marked, False, form, e)


_EMPTY = Look("empty", None, "", False, False, False, None)


def _holds_a_colour(row):
    """Does any cell after the first hold a colour, or something that looks like one?"""
    return any(look.kind in ("colour", "refused", "like") for look in row.looks)


def _written_as_a_value(look):
    """A colour in a cell after the value cell that was written the way a value is (a hex or a function), read or
    refused. A colour name there is a note ("white", "navy")."""
    return look.form and (look.kind == "colour" or (look.kind == "refused" and look.err.code in ("colour-alpha", "colour-gamut")))


def _cells(line):
    line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


class _Reader(object):
    """parse_tables at work: the lines of one document, taken one at a time."""

    def __init__(self):
        self.p = Palette()
        self.fixed = {}       # the Brand table's rows: {"brand" or "accent": (hex, proposed)}
        self.section = None   # "brand", "light", "dark": the heading the lines stand under, or None
        self.marked = False   # that heading says (proposed)
        self.heading = None   # the last heading as written, when it is none of the three
        self.tables = 0       # how many tables have stood under this section's heading
        self.closed = None    # the line of text that followed a table of this section: no later table is filed under it
        self.caption = None   # the last line of text above the table being collected
        self.loose = False    # a line that looks like a table row without its first | has been named under this heading
        self.above = []       # [(level, heading)]: headings above that hold the word "proposed" and name no section
        self.rows = []        # the table being collected

    # -- lines --

    def read(self, text):
        for number, raw in enumerate(text.splitlines(), 1):
            line = " ".join(raw.split())
            if line.startswith("|"):
                self.table_line(number, line)
                continue
            self.end_table()
            if line.startswith("#"):
                self.heading_line(line)
            elif line:
                self.text_line(line)
        self.end_table()
        p = self.p
        if "brand" in self.fixed:
            p.brand = self.fixed["brand"][0]
            if self.fixed["brand"][1]:
                p.proposed.add(("brand", "brand"))
        if "accent" in self.fixed:
            for theme in THEMES:
                if "accent" not in p.theme(theme):
                    self.put(theme, "accent", self.fixed["accent"][0], self.fixed["accent"][1])
                    p.fixed_accent.add(theme)
        return p

    def heading_line(self, line):
        level = len(line) - len(line.lstrip("#"))
        text = line.lstrip("#").strip().rstrip("#").strip()
        m = _SECTION.fullmatch(_plain(text[:MAX_LINE]))
        self.above = [(l, t) for l, t in self.above if l < level]
        if m:
            section = m.group(1).split()[0]  # "brand", "light", "dark"
            for _level, other in self.above:
                self.mark_not_read("The heading %s, above `%s`," % (_quoted(other), HEADING[section]))
            self.above = []
            self.section, self.marked, self.heading = section, bool(m.group(2) and _MARK.search(m.group(2))), None
        else:
            if _MARK.search(text):
                self.above.append((level, line))
            self.section, self.marked, self.heading = None, False, line
        self.tables, self.closed, self.caption, self.loose = 0, None, None, False

    def text_line(self, line):
        self.caption = line
        if not self.section:
            return
        if self.tables and self.closed is None:
            self.closed = line
        if _MARK.search(line):
            self.mark_not_read("The line %s, under `%s`," % (_quoted(line), HEADING[self.section]))
        if "|" in line and not self.loose and _COLOUR_LIKE.search(line):
            self.loose = True
            self.problem("?", None, "palette-not-a-row",
                         "The line %s, under `%s`, holds a | and what looks like a colour, but it does not start with |, so it is "
                         "no row of a table and was not read (nor any line like it under that heading). Write each row as "
                         "`| the row's name | the colour |`, starting at the beginning of the line." % (_quoted(line), HEADING[self.section]))

    def table_line(self, number, line):
        if len(line) > MAX_LINE:
            self.rows.append(Row(number, line[:40], None, [], [], False, True))
            return
        cells = _cells(line)
        if all(_SEPARATOR.fullmatch(c) for c in cells):
            if self.rows and self.rows[-1].line == number - 1 and not self.rows[-1].long:
                self.rows[-1] = self.rows[-1]._replace(above_separator=True)
            return
        self.rows.append(Row(number, cells[0], ROW_KEY.get(_plain(cells[0])), cells, [_look(c) for c in cells[1:]], False, False))

    # -- what is said --

    def problem(self, theme, key, code, message):
        self.p.problems.append((theme, key, code, message))

    def mark_not_read(self, what):
        self.problem("?", None, "palette-mark-not-read",
                     "%s holds the word \"proposed\" (or \"proposal\"). This check reads that mark only in a row (`#a6abce (proposed)`) "
                     "or in the heading of a table (`### Dark theme (proposed)`), so it marked no value. Put the mark in one of those "
                     "places if the colours are still proposals, or take the word out of that line." % what)

    def where(self):
        """Where the table being read stands, in words."""
        if self.section and self.closed is None:
            return "under `%s`" % HEADING[self.section]
        if self.section:
            return "after the line %s, further down under `%s`" % (_quoted(self.caption or self.closed), HEADING[self.section])
        if self.caption:
            return "under the line %s, which is not a heading (a heading starts with #)" % _quoted(self.caption)
        if self.heading is None:
            return "above the first heading"
        return "under the heading %s" % _quoted(self.heading)

    def clash(self, label, where, old, new):
        return Refusal(
            "palette-ambiguous",
            "The palette gives two different values for %s%s (%s and %s). Two palettes look to have "
            "been pasted together: paste only the one you chose." % (label, where, old, new),
        )

    def put(self, theme, key, value, proposed):
        target = self.p.theme(theme)
        if key in target and target[key] != value:
            raise self.clash(LABEL[key], " in the %s theme" % theme, target[key], value)
        target[key] = value
        if proposed:
            self.p.proposed.add((theme, key))

    def put_fixed(self, key, value, proposed):
        fixed = self.fixed
        if key in fixed and fixed[key][0] != value:
            raise self.clash(LABEL[key], ", the one colour both themes share", fixed[key][0], value)
        fixed[key] = (value, proposed or (key in fixed and fixed[key][1]))

    # -- tables --

    def end_table(self):
        rows, self.rows = self.rows, []
        if not rows:
            return
        for row in rows:
            if row.long:
                self.problem("?", None, "palette-long-line",
                             "Line %d, a table row that begins %s, is longer than %d characters, far longer than any row of a palette. "
                             "It was not read." % (row.line, _quoted(row.label), MAX_LINE))
        filed = self.section if self.closed is None else None
        parts = []  # [(header row or None, rows)]: a table, or several that stand together without a blank line
        for row in rows:
            if row.long:
                continue
            if row.above_separator and row.key is None:
                parts.append((row, []))
            else:
                if not parts:
                    parts.append((None, []))
                parts[-1][1].append(row)
        for header, body in parts:
            self.part(header, body, filed)
        self.caption = None
        if self.section:
            self.tables += 1

    def part(self, header, body, filed):
        p = self.p
        for row in ([header] if header else []) + body:
            if row.key is None and _holds_a_colour(row):
                p.unused.append((row.label, list(dict.fromkeys(l.value if l.kind == "colour" and l.form else l.text[:40]
                                                               for l in row.looks if l.kind in ("colour", "refused", "like")))))
        known = [row for row in body if row.key]
        claims = [row for row in known if _holds_a_colour(row)]
        names = _listed([LABEL[row.key] for row in claims]) if claims else ""
        second = header.cells[1] if header and len(header.cells) > 1 else ""
        hex_header = header is not None and _plain(second) == "hex"
        wrong_header = header is not None and not hex_header
        if header and claims and any(_MARK.search(c) for c in header.cells):
            self.mark_not_read("The header row %s of the table %s" % (_quoted(" | ".join(header.cells)), self.where()))
        if wrong_header and re.search(r"\blight\b", _plain(" ".join(header.cells))) and re.search(r"\bdark\b", _plain(" ".join(header.cells))):
            if claims:
                self.problem("?", None, "palette-combined-table",
                             "The table with colours for %s, %s, has a header row that names both themes (%s). This check reads one "
                             "theme from one table: give each theme its own table, one under `### Light theme` and one under `### Dark "
                             "theme`, each starting with the header row `| Token | Hex |`. The table was not read."
                             % (names, self.where(), _quoted(" | ".join(header.cells))))
            p.ignored.extend(row.label for row in known if row not in claims)
            return
        if claims and filed is None:
            if self.section:
                advice = ("A line of text is not a heading, and this check does not guess whether it was meant as one. If the table "
                          "belongs to another theme, write that theme's heading above it; if it carries on the table before it, take "
                          "the line out from between the two.")
            else:
                advice = "Write the heading the table belongs to on a line of its own above it."
            if wrong_header:
                advice += (" (Its header row also calls the second column %s: this check reads the colours from the second column, "
                           "and only when the header row calls it \"Hex\".)" % _quoted(second))
            self.problem("?", None, "palette-no-section",
                         "A table with colours for %s stands %s. This check reads a table only under one of the three headings "
                         "`### Brand`, `### Light theme` and `### Dark theme`, so those colours were not used. %s" % (names, self.where(), advice))
        elif claims and wrong_header:
            self.problem("?", None, "palette-header",
                         "The table with colours for %s, %s, has a header row that calls its second column %s. This check reads each "
                         "colour from the second column, and only when the header row calls that column \"Hex\" (`| Token | Hex |`), "
                         "so the table was not read. Put the colours in the second column and head it \"Hex\"."
                         % (names, self.where(), _quoted(second)))
        if filed is None or wrong_header:
            p.ignored.extend(row.label for row in known if row not in claims)
            return
        for row in known:
            self.row(row, filed, hex_header)

    def row(self, row, section, hex_header):
        p, key = self.p, row.key
        fits = section == "brand" if key == "brand" else (key == "accent" or section in THEMES)
        if not fits:
            if not _holds_a_colour(row):
                p.ignored.append(row.label)
            elif key == "brand":
                self.problem(section, key, "palette-wrong-section",
                             "Primary: this row stands under `%s` (%s). Primary is the one colour both themes share, and it is read "
                             "only under `### Brand`, so it was not used." % (HEADING[section], self.shown(row)))
            else:
                self.problem(section, key, "palette-wrong-section",
                             "%s: this row stands under `### Brand` (%s). Under that heading this check reads Primary; %s is read "
                             "under `### Light theme` and under `### Dark theme`, so it was not used."
                             % (LABEL[key], self.shown(row), LABEL[key]))
            return
        p.rows_found += 1
        name = LABEL[key] if key == "brand" else "%s (%s)" % (LABEL[key], "brand table" if section == "brand" else "%s theme" % section)
        value, rest = (row.looks[0] if row.looks else _EMPTY), row.looks[1:]
        further = next((look for look in rest if _written_as_a_value(look)), None)
        if value.kind in ("empty", "placeholder"):  # not filled in yet, which is not a mistake
            if further:
                self.problem(section, key, "palette-wrong-cell",
                             "%s: the second cell is empty or still the placeholder, and a colour (%s) stands further along the row. "
                             "This check reads the colour from the second cell: write it there." % (name, further.text))
            return
        if value.kind == "refused":
            said = {"colour-current": "The second cell says currentColor, which is whatever colour the text around it has and no colour of "
                                      "its own. Write the colour itself, as #rrggbb.",
                    "colour-gradient": "The second cell holds a gradient or a pattern (%s). This check reads one flat colour: write it "
                                       "as #rrggbb." % _quoted(value.text, 40)}.get(value.err.code, str(value.err))
            self.problem(section, key, value.err.code, "%s: %s" % (name, said))
            return
        if value.kind != "colour":
            self.problem(section, key, "palette-not-one-colour" if value.kind == "like" else "colour-unreadable",
                         "%s: the second cell holds %s. This check reads exactly one colour there, written as #rrggbb (rgb(), hsl(), "
                         "oklch() and, under a `| Token | Hex |` header row, a CSS colour name are read too), with nothing beside it "
                         "but the mark (proposed). A note belongs in a third cell.%s"
                         % (name, _quoted(value.text),
                            "" if value.kind == "like" else " If this row is part of another table (type sizes, say), give that table a "
                                                            "heading of its own."))
            return
        other = next((look for look in rest if _written_as_a_value(look) and look.value != value.value), None)
        if other:
            self.problem(section, key, "palette-two-colours",
                         "%s: the row holds two different colours, %s in the second cell and %s further along. This check reads the "
                         "second cell and does not choose between two: leave one colour in the row." % (name, value.text, other.text))
            return
        if value.named and not hex_header:
            self.problem(section, key, "palette-name-no-header",
                         "%s: the second cell holds the colour name %s, and the table has no header row that says the second column "
                         "holds the colours. Write the colour as #rrggbb, or start the table with the two lines `| Token | Hex |` and "
                         "`|---|---|`." % (name, _quoted(value.text)))
            return
        proposed = self.marked or any(look.marked for look in row.looks)
        if section == "brand":
            self.put_fixed(key, value.value, proposed)
        else:
            self.put(section, key, value.value, proposed)

    def shown(self, row):
        return "it holds %s" % _listed([l.value if l.kind == "colour" and l.form else _quoted(l.text, 40)
                                        for l in row.looks if l.kind in ("colour", "refused", "like")])


def parse_tables(text):
    """The palette in a BRAND.md, or in what the owner pasted. It reads ONE form, the three tables of
    templates/palette-prompt.md, by the rules below, and names everything else. A value it returns is
    the value written in the value cell of a row with a known name under one of the three headings:
    nothing is guessed, and nothing that holds a colour is passed over without a word.

    1. LINES. Runs of spaces and tabs are made one space before anything is looked at, so no input makes
       a pattern slow. A table row longer than 2,000 characters is not read, and a problem names it.

    2. SECTIONS. Only a heading line (one that starts with `#`) names a section, and only when its text
       (emphasis marks and backticks taken out, case ignored) is exactly `Brand`, `Light theme` or `Dark
       theme`, optionally followed by one bracketed remark (`(fixed, theme-independent)`, `(proposed)`).
       Every other heading ends the section. No other line names a section: no label, no bold line, no
       sentence.

    3. TABLES. A table is a run of lines that start with `|`; a blank line, or any other line, ends it.
       Separator rows (`|---|`) are skipped. The first table under a section's heading belongs to that
       section, and so does each table that follows it with only blank lines between. A table that comes
       after a line of text further down belongs to NO section (the line may have been meant as a label
       for another theme, and labels are not read): rule 7 says what happens to it. A line under one of
       the three headings that holds a `|` and something that looks like a colour, but does not start
       with `|` (a row without its first `|`, a quoted table), is no row: a problem quotes the first.

    4. ROWS. The first cell is the row's name: with emphasis marks and backticks taken out and case
       ignored, it must be exactly one of the template's (`Primary`; `Heading`, `Body (ink)`, `Muted`,
       `Accent`, `Link`, `Hairline`, `Background`, `Soft background`, `Surface (cards)`) or one of the two
       short forms the old template had (`Body`, `Surface`). No other names. The SECOND cell is the value,
       always. The cells after it are notes: no value is ever taken from them.

    5. THE VALUE CELL holds exactly one colour and nothing else: backticks may stand around it, and the
       mark `(proposed)` after it. The colour is what `_colour.parse_colour` reads as a whole (a hex,
       rgb(), hsl(), oklch(), a CSS colour name).
       - Empty, or a placeholder (`#[…]`, `#...`, `[hex]`, a dash): the row is not filled in, which is
         not a mistake.
       - Anything else (two colours, a colour among words, a colour that is refused, such as a
         see-through one): a problem that names the row, the theme and what the cell holds. The row has
         no value.
       - A colour NAME is a value only in a table whose header row calls the second column `Hex` (rule
         6). Without that header a name might stand in a column of names: a problem, no value.
       - A later cell that itself holds a second, different colour written the way a value is (a hex or
         a function), or one so written that is refused (see-through, outside the screen's colours): a
         problem ("two different colours"), no value; neither is chosen. Where the value cell is empty
         and such a colour stands further along: a problem too, and the colour is not taken from there.
         A colour NAME in a later cell is a note ("white", "navy").

    6. HEADER ROWS, AND ROWS UNDER OTHER NAMES. The row directly above a separator row is the table's
       header row, unless its first cell is a row name. It is how the owner says which column holds the
       colours: its second cell must be `Hex` (case ignored). Under any other header the table is not
       read: if a row of it holds a colour, a problem says what the header calls the second column (or,
       for a header that names both themes, rule 10's problem); if none does, it is no table of colours
       (type sizes, spacing) and is passed over. A table with no header row is read (rule 5 keeps colour
       names out of it). Any other row whose first cell is not a row name: if a cell of it holds a
       colour, it goes to `unused` and is printed, so that a missing row explains itself; if none does,
       it is passed over without a word.

    7. WHERE A ROW MAY STAND. `Primary` under `Brand` only. The nine theme rows under `Light theme` or
       `Dark theme` only. One exception, the old layout: an `Accent` row under `Brand` is the accent of
       each theme that has none of its own, and the check says so wherever it shows that value. A table
       that belongs to no section and holds a colour under a row name: one problem that names the rows,
       says where the table stands and what the check reads instead. A row with a colour under the
       wrong heading (a `Primary` in a theme's table, a `Heading` in the Brand table): a problem on that
       row; the rest is read. Never dropped silently, never filed by guess. A named row WITHOUT a colour
       in such a place is passed over (a type table's `| Heading | 700 |`) and listed in `ignored`.

    8. THE SAME ROW TWICE in one section with two different values: Refusal("palette-ambiguous") (two
       palettes pasted together), for the nine theme rows, for Primary and for the Brand table's Accent
       alike. The same value twice is fine.

    9. PROPOSALS. A row is a proposal when the word `proposed` or `proposal` (a whole word, case ignored)
       stands in its value cell or in any later cell of it, or in the bracketed remark of its section's
       heading (then every row under that heading is one, in every table of the section). Every cell of
       the row is looked at. The check errs towards asking: "not proposed" marks too. The mark is read
       nowhere else; where the word stands in a place it is not read from (a line of text under one of
       the three headings, a heading above them that names no section, the header row of a table of
       colours), a problem quotes the line, so a mark is never lost without a word.

    10. NOTHING IS READ FROM ANYWHERE ELSE. No table with a Light and a Dark column (a table whose header
        row names both themes is a problem: give each theme its own table). No column of names. No
        tolerance between two spellings of one colour. No labels. No names beyond rule 4's.

    11. WHEN NO ROW WAS FOUND AT ALL (no section heading, or no row under any), `rows_found` is 0 and
        `brand_intake.py palette` prints FORM: one plain sentence on the form this check reads.
    """
    return _Reader().read(text)


def is_about_a_value(problem):
    """Is this entry of `Palette.problems` about one row's value (and not about a whole table or a line)?"""
    return problem[1] is not None


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
        self.problems = []   # [(block, variable or None, message)]: a value it cannot read, or a block it did not find or did not take
        self.found = set()   # which of "light", "dark", "dark_media" the stylesheet has in the starter's form, once


def _unpaired():
    return Refusal(
        "css-unreadable",
        "The stylesheet's braces do not pair up (a { is never closed, or there is a } too many), so this check cannot "
        "tell where its blocks begin and end. Mend the stylesheet, then run this again.",
    )


def _mask(text):
    """The same text with comments blanked (same length), as the intake's editor sees it."""
    return re.sub(r"/\*.*?(\*/|\Z)", lambda m: " " * len(m.group()), text, flags=re.S)


def _after_string(css, j, end):
    """The index after the string that opens at css[j]. A line break ends a string that was never closed."""
    quote, j = css[j], j + 1
    while j < end and css[j] != quote:
        if css[j] == "\n":
            return j
        j += 2 if css[j] == "\\" else 1
    return min(j + 1, end)


# One block: its selector (or at-rule), where that starts, where its { and its } stand, and the blocks inside it.
Rule = namedtuple("Rule", "selector start open close children")


def _rules(css, lo, hi, depth=0):
    """The blocks of css[lo:hi] at one level. A brace inside a string is text, not a brace; braces that do not
    pair up are refused."""
    if depth > 6:
        raise Refusal("css-unreadable", "The stylesheet nests its blocks too deeply for this check to read.")
    out, i = [], lo
    while i < hi:
        o, start = i, i
        while o < hi and css[o] != "{":
            if css[o] == "}":
                raise _unpaired()
            if css[o] in "\"'":
                o = _after_string(css, o, hi)
                continue
            if css[o] == ";":
                start = o + 1  # what stands before the block and ends in ; is a statement (@import, @charset) or a declaration
            o += 1
        if o >= hi:
            break
        level, j = 1, o + 1
        while j < hi and level:
            if css[j] in "\"'":
                j = _after_string(css, j, hi)
                continue
            level += (css[j] == "{") - (css[j] == "}")
            j += 1
        if level:
            raise _unpaired()
        while start < o and css[start].isspace():
            start += 1
        out.append(Rule(css[start:o].strip(), start, o, j - 1, _rules(css, o + 1, j - 1, depth + 1)))
        i = j
    return out


def _declarations(css, rule):
    """[(custom property, its value as written)] for the lines the block itself holds, in order."""
    body = list(css[rule.open + 1:rule.close])
    for child in rule.children:
        for i in range(child.start - rule.open - 1, child.close - rule.open):
            body[i] = " "
    body = "".join(body)
    pieces, depth, last, i = [], 0, 0, 0
    while i < len(body):
        ch = body[i]
        if ch in "\"'":
            i = _after_string(body, i, len(body))
            continue
        depth += (ch == "(") - (ch == ")")
        if ch == ";" and depth <= 0:
            pieces.append(body[last:i])
            last, depth = i + 1, 0
        i += 1
    pieces.append(body[last:])
    out = []
    for piece in pieces:
        m = re.match(r"\s*(--[\w-]+)\s*:(.*)\Z", piece, re.S)
        if m:
            out.append((m.group(1), " ".join(m.group(2).split())))
    return out


# The three blocks exactly as the intake's editor finds them (_site.py: _ROOT, _DARK, _MEDIA, _MEDIA_ROOT). The first two
# start a line; a test (tests/test_palette.py) holds these to the editor's own patterns and to what the editor does.
_EDIT_ROOT = re.compile(r"[ \t]*:root[ \t\n]*\{")
_EDIT_DARK = re.compile(r"""[ \t]*:root\[\s*data-theme\s*=\s*["']dark["']\s*\][ \t\n]*\{""")
_EDIT_MEDIA = re.compile(r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)\s*\{")
_EDIT_MEDIA_ROOT = re.compile(r":root:not\(\s*\[\s*data-theme\s*\]\s*\)\s*\{")
_VAR = re.compile(r"var\(\s*(--[\w-]+)\s*\)")
_IMPORTANT = re.compile(r"!\s*important$", re.I)
_DARK_MEDIA_LIKE = re.compile(r"@media\b.*prefers-color-scheme\s*:\s*dark", re.I | re.S)
_DARK_LIKE = re.compile(r"data-theme\s*=\s*[\"']?dark", re.I)

# The three places the stylesheet keeps the palette: what each is called, what it holds, how the starter writes it,
# and what is said when it is not found.
BLOCK = {"light": "the :root block", "dark": 'the :root[data-theme="dark"] block',
         "dark_media": "the @media (prefers-color-scheme: dark) block"}
_HOLDS = {"light": "the light theme's colours", "dark": "the dark theme's colours",
          "dark_media": "the dark colours for visitors without JavaScript"}
_STARTER = {"light": "`:root {` at the start of a line", "dark": '`:root[data-theme="dark"] {` at the start of a line',
            "dark_media": "`:root:not([data-theme]) {` inside `@media (prefers-color-scheme: dark) {`"}
_NOT_FOUND = (
    ("light", "The stylesheet has no :root { ... } block that this check can find. That is where the light theme's colours are "
              "kept, so they could not be read."),
    ("dark", 'The stylesheet has no :root[data-theme="dark"] { ... } block that this check can find. That is where the dark '
             "theme's colours are kept, so they could not be read."),
    ("dark_media", "The stylesheet has no @media (prefers-color-scheme: dark) block with :root:not([data-theme]) { ... } inside "
                   "it that this check can find. That is where the dark colours are kept a second time, for visitors without "
                   "JavaScript, so they could not be read."),
)


def _is(pattern, css, rule, starts_a_line=False):
    """Is this block written the way the editor's pattern finds it?"""
    at = css.rfind("\n", 0, rule.start) + 1 if starts_a_line else rule.start
    m = pattern.match(css, at)
    return bool(m) and m.end() == rule.open + 1


def _colours_set(css, rule):
    return [var for var, _value in _declarations(css, rule) if var in KEY_OF_VARIABLE]


def read_css(text):
    """The colour tokens of a stylesheet's three blocks, as hex. It reads what the intake's editor
    (_site.edit_css) can write to, and names the rest in `problems`:

    - The three blocks are read in the starter's form only, which is the form the editor finds: `:root {`
      and `:root[data-theme="dark"] {`, each at the start of a line and at the top level, and
      `:root:not([data-theme]) {` inside a top-level `@media (prefers-color-scheme: dark) {`. A rule that
      names `:root` in any other form and sets one of the colours (`:root, html {`, `:ROOT {`, a rule that
      names both `:root` and `:root[data-theme="dark"]`, a block inside another at-rule) is not read: a
      problem says which block it would be and that it is written in another way than the starter writes it.
    - A block that stands more than once is not read, and neither is one that holds another block inside
      it: a problem names it. Nothing is merged, and no later line is taken to win.
    - In a block, a colour variable set more than once, or marked `!important`, has no value: a problem
      names the variable.
    - A block that is not there is named. `found` holds the blocks that were read.
    - A comment is not text. A brace inside a string is not a brace. A statement before a block (`@import
      ...;`, `@charset ...;`) does not hide it. Braces that do not pair up are refused."""
    masked = _mask(text)
    rules = _rules(masked, 0, len(masked))
    css = Css()
    taken = {"light": [], "dark": [], "dark_media": []}
    elsewhere = []  # [(rule, in a block for the dark preference?, the blocks it stands inside)]: every other rule, at any depth

    def others(rule, in_dark_media, inside=()):
        if rule.selector.startswith("@"):
            in_dark_media = in_dark_media or bool(_DARK_MEDIA_LIKE.match(rule.selector))
        else:
            elsewhere.append((rule, in_dark_media, inside))
        for child in rule.children:
            others(child, in_dark_media, inside + (rule.selector,))

    for rule in rules:
        if _is(_EDIT_ROOT, masked, rule, True):
            taken["light"].append(rule)
        elif _is(_EDIT_DARK, masked, rule, True):
            taken["dark"].append(rule)
        elif _is(_EDIT_MEDIA, masked, rule):
            for child in rule.children:
                if _is(_EDIT_MEDIA_ROOT, masked, child):
                    taken["dark_media"].append(child)
                else:
                    others(child, True, (rule.selector,))
        else:
            others(rule, False)

    said = set()  # the blocks something has been said about: not also "not found"
    for rule, in_dark_media, inside in elsewhere:
        if ":root" not in rule.selector.lower() or not _colours_set(masked, rule):
            continue
        blocks = []
        for part in rule.selector.split(","):
            if ":root" in part.lower():
                blocks.append("dark_media" if in_dark_media else "dark" if _DARK_LIKE.search(part) else "light")
        shown = " ".join(" { ".join(inside + (rule.selector,)).split())
        shown = (shown if len(shown) <= 100 else shown[:100] + "...") + " { ... }" + " }" * len(inside)
        for block in dict.fromkeys(blocks):
            said.add(block)
            css.problems.append((block, None, "The rule `%s` sets %s, but it is written in another way than the starter "
                                              "writes it (%s, and inside no other block), so this check did not read it and the intake "
                                              "does not write to it. Write it as the starter does, or set the colours by hand."
                                 % (shown, _HOLDS[block], _STARTER[block])))

    raw = {}
    for block in ("light", "dark", "dark_media"):
        found = taken[block]
        if len(found) > 1:
            said.add(block)
            again = [v for rule in found[1:] for v in _colours_set(masked, rule)]
            css.problems.append((block, None, "The stylesheet has %d blocks of the kind that holds %s (%s), and a later one sets %s. "
                                              "This check reads each of the three colour blocks only where it stands once, as in the "
                                              "starter's stylesheet: the intake writes to the first, and a browser lets a later one win. "
                                              "Fold them into one block." % (len(found), _HOLDS[block], BLOCK[block],
                                                                             _listed(again) if again else "no colour")))
        elif found and found[0].children:
            said.add(block)
            inner = " ".join(found[0].children[0].selector.split())
            css.problems.append((block, None, "%s holds another block inside it (`%s { ... }`), which the starter's does not. This "
                                              "check reads a colour block only as a plain list of lines, so it was not read."
                                 % (BLOCK[block][0].upper() + BLOCK[block][1:], inner[:60])))
        elif found:
            css.found.add(block)
            raw[block] = _own(css, block, _declarations(masked, found[0]))
    for block, target in (("light", css.light), ("dark", css.dark), ("dark_media", css.dark_media)):
        if block in raw:
            _fill(css, block, target, raw[block], {} if block == "light" else raw.get("light", {}))
    css.problems.extend((block, None, message) for block, message in _NOT_FOUND if block not in css.found and block not in said)
    css.brand = css.light.pop("brand", None)
    return css


def _own(css, block, declarations):
    """{variable: value as written} for the lines of one block that can be taken as they stand. A colour variable
    set more than once, or marked !important, is named and left out."""
    written = {}
    for var, value in declarations:
        written.setdefault(var, []).append(value)
    out = {}
    for var, values in written.items():
        if len(values) > 1:
            if var in KEY_OF_VARIABLE:
                css.problems.append((block, var, "It is set %d times in this block (%s). This check does not pick one of them: "
                                                 "leave one line." % (len(values), _listed(values))))
        elif _IMPORTANT.search(values[0]):
            if var in KEY_OF_VARIABLE:
                css.problems.append((block, var, "The colour %r is not one this check can read: it is marked !important, and this "
                                                 "check does not work out which line wins where one is. Take the !important off."
                                     % values[0][:40]))
        else:
            out[var] = values[0]
    return out


def _fill(css, block, target, declared, fallback):
    for var, value in declared.items():
        key = KEY_OF_VARIABLE.get(var)
        if key is None:
            continue
        m = _VAR.fullmatch(value)
        if m:
            name = m.group(1)
            if name not in declared and name not in fallback:
                css.problems.append((block, var, "It is written as var(%s), and %s has no one value that this check can read "
                                                 "here." % (name, name)))
                continue
            value = declared.get(name, fallback.get(name))
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
    names is not said again here: a block that is not there or was not read, a value that could not be read."""
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
    not there or was not read, a value that could not be read) is not said again here."""
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
