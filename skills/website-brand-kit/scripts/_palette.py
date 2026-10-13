"""_palette.py: the palette as BRAND.md holds it and as the stylesheet holds it, and the contrast
check between text colours and backgrounds.

BRAND.md has a table per theme (`### Light theme`, `### Dark theme`) and a fixed "Brand" table;
the stylesheet has the same colours in three blocks (`:root`, `:root[data-theme="dark"]`, and
the same dark values again inside `@media (prefers-color-scheme: dark)`). This reads both, says
what is missing or unreadable, names where they disagree, and runs the matrix: every text colour
on every background colour, in both themes, at WCAG AA's 4.5 to 1 for body text. Nothing here
writes a file. Standard library only.

Both readers read ONE form, the one this skill itself defines, and name everything else: the three
tables of templates/palette-prompt.md (`parse_tables`), and the three blocks of the starter's
stylesheet (`read_css`). Neither guesses. An owner's colours in any other form are written into this
form by the assistant, not worked out here. Where the three blocks are, and where each value stands in
them, is found by ONE scan (`scan_css`), which the intake's editor (_site.edit_css) works from too: what
this reads is what that writes.
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

MAX_LINE = 2000  # a table row longer than this is not a palette row, and is not read; a heading longer than this names no section
HEADING = {"brand": "### Brand", "light": "### Light theme", "dark": "### Dark theme"}
# The names a row may have: the template's ten, and the two short forms the old template had. No others.
ROW_KEY = {label.lower(): key for key, label in LABEL.items()}
ROW_KEY.update({"body": "ink", "surface": "surface"})
# What `brand_intake.py palette` says when it found no palette row at all (rule 11).
FORM = (
    "This check reads the colours from three tables, each under its own heading on a line of its own: `### Brand` (one "
    "row, Primary), `### Light theme` and `### Dark theme` (the rows %s). Each table starts with the two lines "
    "`| Token | Hex |` and `|---|---|`, and each row is `| the row's name | the colour |`. In a file that holds more "
    "than the palette (a BRAND.md), the three tables stand under the heading `## Colour palette`: where a text has that "
    "heading, this check looks only at the part under it. The assistant can write your colours in that form."
    % ", ".join(t[1] for t in TOKENS)
)


class Palette(object):
    def __init__(self):
        self.light = {}
        self.dark = {}
        self.brand = None
        self.proposed = set()   # {(theme, key)} values marked "(proposed)": shown, never written
        self.problems = []      # [(theme, key or None, code, message)]: what could not be read, and why; key None: said of a whole table or line
        self.ignored = []       # names of palette rows that hold no colour and stand in a table that is not a table of colours
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
_PALETTE = re.compile(r"colou?r palette")  # rule 0: the heading of the part of a longer text that holds the palette
_MARK = re.compile(r"\bpropos(?:ed|als?)\b", re.I)
_MARK_AFTER = re.compile(r"(?: ?\( ?propos(?:ed|als?) ?\)| propos(?:ed|als?))$", re.I)
_SEPARATOR = re.compile(r":?-+:?")
_PLACEHOLDER = re.compile(r"#?\[([^\[\]#0-9]*)\]|#?(?:\.\.\.|…)|[-–—]+")
# A colour written as a value (rule 12): a # with 3, 4, 6 or 8 hex digits, with no letter, digit or & straight before
# it (a link's `page#fab`, an entity `&#123;`) and no letter or digit straight after it; or one of the five functions
# this check reads, with its brackets. An underscore beside it is emphasis (`_#16162a_`), not part of a word. Nothing
# in the pattern can match the same text in two ways, so no line makes the search slow.
_COLOUR = re.compile(r"(?<![^\W_])(?<!&)#(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{3,4})(?![^\W_])|(?<![^\W_])(?:rgba?|hsla?|oklch)\(([^()]*)\)", re.I)
_VALUE_FORM = re.compile(r"#|[A-Za-z-]+\(")
_BREAKS = "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"  # what str.splitlines() ends a line at
_NOT_A_BREAK = re.compile("[^%s]" % _BREAKS)
MOST_NAMED = 5  # how many lines one kind of "not read" problem quotes; the rest are counted

# What one cell holds. kind: "colour" (exactly one colour: `value` is its hex, `named` says it was written as a colour
# name, `form` that it was written as a hex or a function), "refused" (exactly one colour that is not taken: `err` says
# why), "like" (a colour written as a value, with something else beside it), "words", "empty", "placeholder".
Look = namedtuple("Look", "kind value text marked named form err")
Row = namedtuple("Row", "line label key cells looks above_separator long")


_EMPHASIS = re.compile(r"[*_`]")


def _plain(text):
    """A heading or a first cell as it is compared: without emphasis marks and backticks, in lower case."""
    return " ".join(_EMPHASIS.sub("", text).split()).lower()


def _visible(text):
    """The text with every character that does not show (a zero-width space, a no-break space, a control
    character) written as <U+200B>, so that a quote in a message shows what the file holds."""
    if text.isprintable():
        return text
    return "".join(c if c.isprintable() else "<U+%04X>" % ord(c) for c in text)


def _quoted(text, most=60, around=None):
    """`text` in quotation marks for a message, at most `most` characters of it: its beginning, or, where
    `around` says where the thing the sentence is about stands in it, the part around that."""
    if len(text) > most:
        start = 0
        if around:
            start = max(0, min(around[0] - max(0, most - (around[1] - around[0])) // 2, len(text) - most))
        text = ("..." if start else "") + text[start:start + most] + ("..." if start + most < len(text) else "")
    return '"%s"' % _visible(text)


def _unseen(text):
    """A sentence to put after a quote that holds a character written as <U+...>, or nothing."""
    if text.isprintable():
        return ""
    return " (What is written as <U+...> in the quote is a character that does not show on the screen: take it out.)"


def _level(line):
    """How many # a heading line starts with."""
    return len(line) - len(line.lstrip("#"))


def _heading(line):
    """The text of a heading line, without its # at either end."""
    return line.lstrip("#").strip().rstrip("#").strip()


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


def _colour_in(text):
    """The first colour written as a value in `text` (rule 12 says what that is), as a match, or None."""
    if "#" not in text and "(" not in text:
        return None
    for m in _COLOUR.finditer(text):
        inner = m.group(1)
        if inner is None or not ("..." in inner or "…" in inner):  # rgba(...,0.06) is a placeholder, as #... is
            return m
    return None


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
    named = text.lower() in _colour.NAMES
    if form or named or text.lower() in ("currentcolor", "transparent"):  # (nothing else is a colour: most cells are words)
        try:
            return Look("colour", _colour.parse_colour(text), text, marked, named, form, None)
        except Refusal as e:
            if e.code != "colour-unreadable":
                return Look("refused", None, text, marked, False, form, e)
    return Look("like" if _colour_in(cell) else "words", None, cell, marked, False, form, None)


_EMPTY = Look("empty", None, "", False, False, False, None)


def _holds_a_colour(row):
    """Does any cell after the first hold a colour, or a colour among other things?"""
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


def _without_comments(text):
    """(the text without a byte-order mark at its start and with every HTML comment blanked, the number of the
    line on which a comment opens that is never closed, or None). A blanked comment keeps its line breaks, so
    every line keeps its number."""
    if text.startswith("\ufeff"):
        text = text[1:]
    if "<!--" not in text:
        return text, None
    out, at, unclosed = [], 0, None
    while True:
        start = text.find("<!--", at)
        if start < 0:
            out.append(text[at:])
            break
        end = text.find("-->", start + 2)  # `<!-->` and `<!--->` are whole comments
        if end < 0:
            unclosed = len((text[:start] + "x").splitlines())
        end = len(text) if end < 0 else end + 3
        out.append(text[at:start])
        out.append(_NOT_A_BREAK.sub(" ", text[start:end]))
        at = end
    return "".join(out), unclosed


class _Reader(object):
    """parse_tables at work: the lines of one document, taken one at a time."""

    def __init__(self):
        self.p = Palette()
        self.fixed = {}       # the Brand table's rows: {"brand" or "accent": (hex, proposed)}
        self.section = None   # "brand", "light", "dark": the heading the lines stand under, or None
        self.marked = False   # that heading says (proposed)
        self.unmarked = None  # (its line number, the heading) while that mark has marked no value yet
        self.heading = None   # the last heading as written, when it is none of the three
        self.tables = 0       # how many tables have stood under this section's heading
        self.closed = None    # the line of text that followed a table of this section: no later table is filed under it
        self.label = None     # the line before this section's first table that names another section: no table is filed under it
        self.caption = None   # the last line of text above the table being collected
        self.rows = []        # the table being collected
        self.said = set()     # numbers of the lines whose colours were read, or are named by a problem of their row or table
        self.mark_read = set()  # numbers of the lines on which the word is read as a mark (rule 9)
        self.colours = []     # [(number, line)]: every line that holds a colour written as a value (rule 12)
        self.marks = []       # [(number, line)]: every line that holds the word (rule 9)

    # -- lines --

    def read(self, text):
        text, unclosed = _without_comments(text)
        lines = [" ".join(raw.split()) for raw in text.splitlines()]
        first, last = self.where_to_look(lines)
        if unclosed and first < unclosed <= last:
            self.problem("?", None, "palette-comment-open",
                         "Line %d opens a comment with `<!--` that is never closed with `-->`, so everything after it is part of the "
                         "comment and was not read. Close the comment, or take the `<!--` out." % unclosed)
        for number in range(first + 1, last + 1):
            line = lines[number - 1]
            if not line:
                self.end_table()
                continue
            if _MARK.search(line):
                self.marks.append((number, line))
            if _colour_in(line):
                self.colours.append((number, line))
            if line.startswith("|"):
                self.table_line(number, line)
                continue
            self.end_table()
            if line.startswith("#"):
                self.heading_line(number, line)
            else:
                self.text_line(number, line)
        self.end_table()
        self.end_section()
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
            if self.fixed["accent"][1] and not p.fixed_accent:
                self.problem("brand", "accent", "palette-mark-not-read",
                             "Accent (brand table): the row is marked as a proposal, and neither theme uses it, because each has an "
                             "Accent of its own. So the mark marked no value. Take the row out of the table under `### Brand`, or "
                             "take the mark out of it.")
        self.name_what_was_not_read()
        return p

    def where_to_look(self, lines):
        """Rule 0: (how many lines stand before the part of the text that is the palette, the number of its last
        line). The whole text, unless one heading says `Colour palette`: then the part under that heading."""
        found = [at for at, line in enumerate(lines)
                 if line.startswith("#") and len(line) <= MAX_LINE and "palette" in line.lower() and _PALETTE.fullmatch(_plain(_heading(line)))]
        if not found:
            return 0, len(lines)
        if len(found) > 1:
            self.problem("?", None, "palette-section-twice",
                         "The heading %s stands %d times in this text (on lines %s%s). This check reads the palette from the part of "
                         "the text under that heading and cannot tell which of them holds it, so it read nothing. Leave that "
                         "heading once, above the three tables."
                         % (_quoted(lines[found[0]]), len(found), _listed([str(at + 1) for at in found[:MOST_NAMED]]),
                            " and further down" if len(found) > MOST_NAMED else ""))
            return 0, 0
        first, level = found[0], _level(lines[found[0]])
        last = next((at for at in range(first + 1, len(lines)) if lines[at].startswith("#") and _level(lines[at]) <= level), len(lines))
        # Outside that part nothing is read and nothing is named, with one exception: one of the three headings with a
        # table under it is a palette (or a part of one) written in the wrong place, and is said to be
        stray, heading = [], None
        for at in list(range(first)) + list(range(last, len(lines))):
            line = lines[at]
            if line.startswith("#"):
                heading = at if len(line) <= MAX_LINE and _SECTION.fullmatch(_plain(_heading(line))) else None
            elif line.startswith("|") and heading is not None:
                stray.append(heading)
                heading = None
        for at in stray[:MOST_NAMED]:
            self.problem("?", None, "palette-outside-section",
                         "Line %d, the heading %s, has a table under it and stands outside the part of this text that the check "
                         "reads: the part under the heading %s (lines %d to %d). So that table was not read. Move the heading and "
                         "its table into that part." % (at + 1, _quoted(lines[at]), _quoted(lines[first]), first + 1, last))
        if len(stray) > MOST_NAMED:
            more = len(stray) - MOST_NAMED
            self.problem("?", None, "palette-outside-section",
                         "%d more heading%s with a table under %s outside that part; the next is on line %d."
                         % (more, "" if more == 1 else "s", "it stands" if more == 1 else "them stand", stray[MOST_NAMED] + 1))
        return first, last

    def heading_line(self, number, line):
        self.end_section()
        text = _heading(line)
        m = _SECTION.fullmatch(_plain(text)) if len(line) <= MAX_LINE else None
        if m:
            self.section, self.heading = m.group(1).split()[0], None  # "brand", "light", "dark"
            self.marked = bool(m.group(2) and _MARK.search(m.group(2)))
            if self.marked:
                self.mark_read.add(number)
                self.unmarked = (number, line)
        else:
            self.section, self.marked, self.heading = None, False, line
        self.tables, self.closed, self.label, self.caption = 0, None, None, None

    def end_section(self):
        """A heading's mark is read as the mark of the rows under it: where no row under it has a value, say so."""
        if self.unmarked:
            self.problem("?", None, "palette-mark-not-read",
                         "Line %d, the heading %s, carries the mark (proposed), but no row under it has a value that was read, so it "
                         "marked no value. Fill in the rows under it (they then count as proposals), or take the mark out of the "
                         "heading." % (self.unmarked[0], _quoted(self.unmarked[1])))
        self.unmarked = None

    def text_line(self, number, line):
        self.caption = line
        if not self.section:
            return
        if self.tables:
            if self.closed is None:
                self.closed = line
        elif self.label is None and len(line) < 200:
            other = _SECTION.fullmatch(_plain(line).rstrip(":").strip())
            if other and other.group(1).split()[0] != self.section:
                self.label = line
                here, there = HEADING[self.section], HEADING[other.group(1).split()[0]]
                self.problem("?", None, "palette-label",
                             "Line %d, %s, stands between the heading `%s` and its table, and it is the name of another section. A "
                             "line of text is not a heading, so this check cannot tell which of the two the table belongs to, and it "
                             "read no table under that heading. If the table belongs under `%s`, write that line as a heading (`%s`); "
                             "if it belongs under `%s`, take the line out." % (number, _quoted(line), here, there, there, here))

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

    def name_what_was_not_read(self):
        """Rules 9 and 12, over the whole text: the word where it is not read as a mark, and every colour written
        as a value that was not read and that no problem of its own row or table names."""
        marks = [(n, line) for n, line in self.marks if n not in self.mark_read]
        for at, (number, line) in enumerate(marks[:MOST_NAMED]):
            m = _MARK.search(line)
            said = "Line %d, %s, holds the word \"%s\"" % (number, _quoted(line, 80, m.span()), m.group().lower())
            if at == 0:
                said += (". This check reads that word as a mark only in a row whose colour it reads (`| Muted | #a6abce (proposed) |`) "
                         "and in brackets after one of the three headings (`### Dark theme (proposed)`), so here it marked no value. If "
                         "colours are still proposals, put the mark in one of those places; if they are not, take the word out of that "
                         "line, or put the line inside a comment (`<!-- ... -->`), which this check does not look at.")
            else:
                said += " where this check does not read it as a mark either, so it marked no value there."
            self.problem("?", None, "palette-mark-not-read", said + _unseen(line))
        if len(marks) > MOST_NAMED:
            more = len(marks) - MOST_NAMED
            self.problem("?", None, "palette-mark-not-read",
                         "The word \"proposed\" (or \"proposal\") stands on %d more line%s where it is not read as a mark; the next is "
                         "line %d." % (more, "" if more == 1 else "s", marks[MOST_NAMED][0]))
        colours = [(n, line) for n, line in self.colours if n not in self.said]
        for at, (number, line) in enumerate(colours[:MOST_NAMED]):
            m = _colour_in(line)
            said = "Line %d, %s, holds a colour (%s) that was not read" % (number, _quoted(line, 80, m.span()), _visible(m.group()[:40]))
            if at == 0:
                said += (". This check reads a colour only from the second cell of a named row (`| Muted | #5a5a72 |`) in a table "
                         "under `### Brand`, `### Light theme` or `### Dark theme`. If the colour belongs to the palette, write it in "
                         "such a row (the names are Primary under `### Brand`, and %s under the two themes). If it does not (a "
                         "shadow, a note), take it out of this file or put it inside a comment (`<!-- ... -->`), which this check "
                         "does not look at." % ", ".join(t[1] for t in TOKENS))
            else:
                said += " either: only the second cell of a named row under one of the three headings is read."
            self.problem("?", None, "palette-colour-not-read", said + _unseen(line))
        if len(colours) > MOST_NAMED:
            more = len(colours) - MOST_NAMED
            self.problem("?", None, "palette-colour-not-read",
                         "%d more line%s a colour that was not read; the next is line %d."
                         % (more, " holds" if more == 1 else "s hold", colours[MOST_NAMED][0]))

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
                self.said.add(row.line)
                self.problem("?", None, "palette-long-line",
                             "Line %d, a table row that begins %s, is longer than %d characters, far longer than any row of a palette. "
                             "It was not read." % (row.line, _quoted(row.label), MAX_LINE))
        filed = self.section if self.closed is None and self.label is None else None
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
        known = [row for row in body if row.key]
        claims = [row for row in known if _holds_a_colour(row)]
        names = _listed([LABEL[row.key] for row in claims]) if claims else ""
        second = header.cells[1] if header and len(header.cells) > 1 else ""
        hex_header = header is not None and _plain(second) == "hex"
        wrong_header = header is not None and not hex_header
        titles = _plain(" ".join(header.cells)) if header else ""
        both_themes = bool(re.search(r"\blight\b", titles) and re.search(r"\bdark\b", titles))
        if not (both_themes or filed is None or wrong_header):
            for row in known:
                self.row(row, filed, hex_header)
            return
        # the table is not read: one problem says so and names its rows that hold a colour
        if claims and both_themes:
            self.problem("?", None, "palette-combined-table",
                         "The table with colours for %s, %s, has a header row that names both themes (%s). This check reads one "
                         "theme from one table: give each theme its own table, one under `### Light theme` and one under `### Dark "
                         "theme`, each starting with the header row `| Token | Hex |`. The table was not read."
                         % (names, self.where(), _quoted(" | ".join(header.cells))))
        elif claims and filed is None and self.label is None:
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
        elif claims and filed is not None:
            self.problem("?", None, "palette-header",
                         "The table with colours for %s, %s, has a header row that calls its second column %s. This check reads each "
                         "colour from the second column, and only when the header row calls that column \"Hex\" (`| Token | Hex |`), "
                         "so the table was not read. Put the colours in the second column and head it \"Hex\"."
                         % (names, self.where(), _quoted(second)))
        # (under a line that names another section, rule 2's problem has said that no table there was read)
        self.said.update(row.line for row in claims)
        p.ignored.extend(row.label for row in known if not _holds_a_colour(row))

    def row(self, row, section, hex_header):
        p, key = self.p, row.key
        fits = section == "brand" if key == "brand" else (key == "accent" or section in THEMES)
        if not fits:
            if not _holds_a_colour(row):
                p.ignored.append(row.label)
                return
            self.said.add(row.line)
            if key == "brand":
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
        self.mark_read.add(row.line)  # rule 9: the word in any cell of this row is the row's mark
        name = LABEL[key] if key == "brand" else "%s (%s)" % (LABEL[key], "brand table" if section == "brand" else "%s theme" % section)
        value, rest = (row.looks[0] if row.looks else _EMPTY), row.looks[1:]
        marked = any(look.marked for look in row.looks)
        if value.kind in ("empty", "placeholder"):  # not filled in yet, which is not a mistake
            if marked:
                self.problem(section, key, "palette-proposal-empty",
                             "%s: the row is marked as a proposal, but its second cell is empty or still the placeholder, so there "
                             "is no value to confirm and the row is not filled in. Write the proposed colour in the second cell, "
                             "with the mark after it (`#a6abce (proposed)`)." % name)
            return  # a colour further along the row was not read: rule 12 names the line
        self.said.add(row.line)  # from here on the row's value is read, or a problem names the row and what it holds
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
                         "but the mark (proposed). A note belongs in a third cell.%s%s"
                         % (name, _quoted(value.text), _unseen(value.text),
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
        proposed = self.marked or marked
        if section == "brand":
            self.put_fixed(key, value.value, proposed)
        else:
            self.put(section, key, value.value, proposed)
        if self.marked:
            self.unmarked = None

    def shown(self, row):
        return "it holds %s" % _listed([l.value if l.kind == "colour" and l.form else _quoted(l.text, 40)
                                        for l in row.looks if l.kind in ("colour", "refused", "like")])


def parse_tables(text):
    """The palette in a BRAND.md, or in what the owner pasted. It reads ONE form, the three tables of
    templates/palette-prompt.md, by the rules below, and names everything else. Three promises, each
    of which can be checked on any text:

    (1) A value it returns is the colour in the SECOND cell of a row with one of rule 4's names, in a
        table under one of the three headings, in the part of the text the check looks at (rule 0).
        Nothing is guessed, and nothing is taken from anywhere else.
    (2) A colour written as a value anywhere else in that part is named in `problems` (rule 12, which
        also says what "written as a value" means, and where that stops).
    (3) The word `proposed`, `proposal` or `proposals`, wherever in that part it is not read as a
        mark, is named in `problems` (rule 9).

    0. WHERE THE CHECK LOOKS. (Comments are blanked first: rule 1.) If exactly one heading line of the
       text says `Colour palette` or `Color palette` and nothing else (at any level; emphasis marks and
       backticks taken out, case ignored), the palette is that SECTION: from that heading's line to the
       next heading of the same or a higher level (as many `#` or fewer), or to the end of the text.
       Rules 1 to 12 are about that part alone, and "the text" in them means that part. Everything
       outside it is not the palette's business: nothing there is read, and nothing there is named,
       neither a colour (rule 12) nor the word proposed (rule 9) nor a table, because a BRAND.md is a
       whole brand guide (a logo, type, a shadow's `rgba(0, 0, 0, 0.06)`, the share cards' colours).
       One thing outside it is named, so that a palette written in the wrong place of such a file is
       never silently "not there": a heading that rule 2 would read as `Brand`, `Light theme` or `Dark
       theme`, with a table under it (a line that starts with `|`, before the next heading). A problem
       quotes that heading and says where the three tables belong. Without a table under it such a
       heading is only a heading (a guide may be titled `# Brand`).
       If the text has NO such heading, the whole text is the palette (a pasted answer), and every
       rule below is about all of it. If it has that heading MORE THAN ONCE, which of them holds the
       palette cannot be told: a problem says so, and nothing is read.
       A pasted answer that carries its own `## Colour palette` heading above the three tables is
       read like a BRAND.md: a sentence above that heading ("Here are three proposed palettes") stands
       outside the section and is not named, and the values under the heading, which carry no mark,
       are read as they are. That is intended: what makes a value a proposal is a mark on its row or
       on its section's heading (rule 9), and those are inside the section.

    1. LINES. A byte-order mark at the very start is dropped. Every HTML comment (`<!--` up to the
       next `-->`) is blanked before anything else is looked at, its line breaks kept so that every
       line keeps its number: nothing inside a comment is read, and nothing inside one is named. A
       comment that is never closed runs to the end of the text, and a problem says on which line it
       opens. Then runs of spaces and tabs are made one space, so no input makes a pattern slow. A
       table row longer than 2,000 characters is not read, and a problem names it.

    2. SECTIONS. Only a heading line (one that starts with `#`) names a section, and only when its text
       (emphasis marks and backticks taken out, case ignored) is exactly `Brand`, `Light theme` or `Dark
       theme`, optionally followed by one bracketed remark (`(fixed, theme-independent)`, `(proposed)`).
       Every other heading ends the section, and so does a heading longer than 2,000 characters,
       whatever it begins with. No other line names a section: no label, no bold line, no sentence.
       One such line is not passed over, though. A line of text between a section's heading and its
       first table that would name ANOTHER section if it were a heading (`**Light theme**` or `Dark
       theme:` under `### Brand`; emphasis marks and a colon at its end are not counted) leaves open
       which of the two the table belongs to: a problem quotes the line, and no table under that
       heading is read. Any other line there (a sentence on the mood) is only text.

    3. TABLES. A table is a run of lines that start with `|`; a blank line, or any other line, ends it.
       Separator rows (`|---|`) are skipped. The first table under a section's heading belongs to that
       section, and so does each table that follows it with only blank lines between. A table that comes
       after a line of text further down belongs to NO section (the line may have been meant as a label
       for another theme, and labels are not read): rule 7 says what happens to it. A line that does
       not start with `|` is no row of a table, whatever else it holds (a row without its first `|`, a
       quoted table, a list): a colour on it is not read, and rule 12 names it.

    4. ROWS. The first cell is the row's name: with emphasis marks and backticks taken out and case
       ignored, it must be exactly one of the template's (`Primary`; `Heading`, `Body (ink)`, `Muted`,
       `Accent`, `Link`, `Hairline`, `Background`, `Soft background`, `Surface (cards)`) or one of the two
       short forms the old template had (`Body`, `Surface`). No other names. The SECOND cell is the value,
       always. The cells after it are notes: no value is ever taken from them.

    5. THE VALUE CELL holds exactly one colour and nothing else: backticks may stand around it, and the
       mark `(proposed)` after it. The colour is what `_colour.parse_colour` reads as a whole (a hex,
       rgb(), hsl(), oklch(), a CSS colour name).
       - Empty, or a placeholder (`#[…]`, `#...`, `[hex]`, one or more dashes): the row is not filled
         in, which is not a mistake. A colour written as a value further along such a row was not read,
         and rule 12 names the line.
       - Anything else (two colours, a colour among words, a colour that is refused, such as a
         see-through one): a problem that names the row, the theme and what the cell holds. The row has
         no value.
       - A colour NAME is a value only in a table whose header row calls the second column `Hex` (rule
         6). Without that header a name might stand in a column of names: a problem, no value.
       - A later cell that itself holds a second, different colour written the way a value is (a hex or
         a function), or one so written that is refused (see-through, outside the screen's colours): a
         problem ("two different colours"), no value; neither is chosen. A colour NAME in a later cell
         is a note ("white", "navy"), and so is the same colour said again.

    6. HEADER ROWS. The row directly above a separator row is the table's header row, unless its first
       cell is a row name. It is how the owner says which column holds the colours: its second cell must
       be `Hex` (case ignored). Under any other header the table is not read: if a row of it holds a
       colour, a problem says what the header calls the second column; if none does, it is no table of
       colours (type sizes, spacing) and is passed over. A header row that names both themes, in any of
       its cells and whatever its second cell says, is rule 10's problem instead. A table with no header
       row is read (rule 5 keeps colour names out of it). A row whose first cell is not a row name is no
       row of the palette: a colour written as a value on it was not read, and rule 12 names the line.

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

    9. PROPOSALS. The mark is the word `proposed`, `proposal` or `proposals` (a whole word, case
       ignored). It is read in three places, and only there:
       - in the value cell of a row that rules 3 to 7 read, and in any later cell of that row: the row's
         value is a proposal. The check errs towards asking: "not proposed" marks too. Where the value
         cell of such a row is empty or a placeholder, a problem says the row is marked as a proposal
         and is not filled in. Where the cell cannot be read, the row's own problem stands.
       - in the bracketed remark of a section's heading: every row with a value under that heading is a
         proposal, in every table of the section. Where no row under it has a value, a problem says the
         heading's mark marked no value.
       EVERYWHERE ELSE in the text (above the first heading, between headings, in any other heading at
       any level, in a line of text, a list or a label, in a header row, in the first cell of a row, in
       any cell of a row that is not read), the word is a problem: it quotes the line, cut so that the
       word shows, and says where the mark is read. The first five such lines are quoted, and the rest
       are counted. (One more mark marks nothing and is said to: on the old layout's Accent under
       `Brand`, where each theme has an Accent of its own.) There is no exception for a place or a kind
       of file: a text that holds the word outside a comment has a value marked as a proposal, or a
       problem, and `brand_intake.py palette` does not end with 0 on it.

    10. NOTHING IS READ FROM ANYWHERE ELSE. No table with a Light and a Dark column (a table whose header
        row names both themes is a problem: give each theme its own table). No column of names. No
        tolerance between two spellings of one colour. No labels. No names beyond rule 4's.

    11. WHEN NO ROW WAS FOUND AT ALL (no section heading, or no row under any), `rows_found` is 0 and
        `brand_intake.py palette` prints FORM: one plain sentence on the form this check reads. Rows
        that were found and have no value are listed by that command as "not filled in", with the offer
        that the assistant proposes values, only when `problems` is empty. While there is a problem
        they are listed as rows without a value, with one sentence instead: mend what is named first
        and check again, because a value that was not read also shows its row as missing.

    12. COLOURS THAT WERE NOT READ. "A colour written as a value" is, anywhere in the text: a `#`
        followed by 3, 4, 6 or 8 hex digits, with no letter or digit straight after them and no letter,
        digit or `&` straight before the `#` (a link's `page#fab` and an entity `&#123;` are no
        colours); or `rgb(`, `rgba(`, `hsl(`, `hsla(` or `oklch(`, not as the end of a longer word, with
        everything up to its closing bracket, unless an ellipsis stands between the brackets
        (`rgba(...,0.06)` is a placeholder, as `#...` is). Case is ignored. After the reading,
        every line that holds such a colour is one of three things: a row whose value was read (the
        colours in its later cells are notes); a row that a problem of rules 1 to 8 names, by its own
        name or as one of the rows of a table that was not read; or a line with a colour that was NOT
        READ. Each line of the third kind is a problem that quotes the line, cut so that the colour
        shows, and says that the check reads a colour only from the second cell of a named row under one
        of the three headings: a colour in the first cell (columns the wrong way round), in a row under
        another name, in a row whose value cell is empty, in a list, in a sentence, in a heading, in a
        table row without its first `|`. The first five such lines are quoted, and the rest are counted.
        The limit of this rule: a colour NAME (`navy`), hex digits without their `#` (`5a5a72`) and any
        other spelling (`#12345`, `hwb()`, `color()`, a function with another bracket inside its own)
        are seen only in a cell that is read; anywhere else they are passed over without a word. And
        the other way: a `#` with exactly 3, 4, 6 or 8 digits that is no colour (`issue #123`) is taken
        for one, and named.
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
        self.problems = []   # [(block or None, variable or None, message)]: a value it cannot read, a block it did not find or did not take, a colour set outside the three blocks
        self.found = set()   # which of "light", "dark", "dark_media" the stylesheet has in the starter's form, once


def _unpaired():
    return Refusal(
        "css-unreadable",
        "The stylesheet's braces do not pair up (a { is never closed, or there is a } too many), so this check cannot "
        "tell where its blocks begin and end. Mend the stylesheet, then run this again.",
    )


# The three places the stylesheet keeps the palette: what each is called, what it holds, how the starter writes it,
# and what is said when it is not found.
BLOCKS = ("light", "dark", "dark_media")
BLOCK = {"light": "the :root block", "dark": 'the :root[data-theme="dark"] block',
         "dark_media": "the @media (prefers-color-scheme: dark) block"}
_HOLDS = {"light": "the light theme's colours", "dark": "the dark theme's colours",
          "dark_media": "the dark colours for visitors without JavaScript"}
_STARTER = {"light": "`:root {`", "dark": '`:root[data-theme="dark"] {`',
            "dark_media": "`:root:not([data-theme]) {` inside `@media (prefers-color-scheme: dark) {`"}
_THREE = "%s, %s, and %s" % (_STARTER["light"], _STARTER["dark"], _STARTER["dark_media"])
_NOT_FOUND = {
    "light": "The stylesheet has no :root { ... } block that this check can find. That is where the light theme's colours are "
             "kept, so they could not be read.",
    "dark": 'The stylesheet has no :root[data-theme="dark"] { ... } block that this check can find. That is where the dark '
            "theme's colours are kept, so they could not be read.",
    "dark_media": "The stylesheet has no @media (prefers-color-scheme: dark) block with :root:not([data-theme]) { ... } inside "
                  "it that this check can find. That is where the dark colours are kept a second time, for visitors without "
                  "JavaScript, so they could not be read.",
}

# How each of the three is written: the whole of what stands before its {, comments and the space around it apart.
# (Space is what CSS takes for space: a no-break space is a character of a name there, not space.)
_CSS_SPACE = " \t\r\n\f"
_S = r"[ \t\r\n\f]*"
_IS_LIGHT = re.compile(r":root")
_IS_DARK = re.compile(r""":root\[{s}data-theme{s}={s}(["'])dark\1{s}\]""".format(s=_S))
_IS_MEDIA = re.compile(r"@media{s}\({s}prefers-color-scheme{s}:{s}dark{s}\)".format(s=_S))
_IS_MEDIA_ROOT = re.compile(r":root:not\({s}\[{s}data-theme{s}\]{s}\)".format(s=_S))
_DARK_MEDIA_LIKE = re.compile(r"@media\b.*prefers-color-scheme\s*:\s*dark", re.I | re.S)
_DARK_LIKE = re.compile(r"data-theme\s*=\s*[\"']?dark", re.I)
_SQUEEZE = re.compile("[%s]+" % _CSS_SPACE)

_CSS_SKIP = re.compile(r"""/\*|["']|\burl\(""", re.I)
# A string runs to its closing quote, or to the end of its line when it is never closed. Each character of it is
# taken by one alternative only, so the pattern cannot be made slow.
_CSS_STRING = {q: re.compile(r"%s(?:[^%s\\\n]|\\[\s\S]?)*(?:%s|(?=\n)|\Z)" % (q, q, q)) for q in "\"'"}
_CSS_STRUCTURE = re.compile(r"[{};]")
_CSS_PIECE = re.compile(r"[;()]")
_CSS_PROPERTY = re.compile(r"{s}(--[\w-]+){s}:".format(s=_S))
_IMPORTANT = re.compile(r"!{s}important{s}\Z".format(s=_S), re.I)
_VAR = re.compile(r"var\({s}(--[\w-]+){s}\)".format(s=_S))


def _squeeze(text):
    """The text with each run of space made one space, and none at its ends."""
    return _SQUEEZE.sub(" ", text).strip(_CSS_SPACE)

# One block: where what stands before its { begins, where its { and its } stand, and the blocks inside it.
Rule = namedtuple("Rule", "start open close children")
# One line of a block that sets a custom property: its name, where its value stands in the text (without the space,
# the comments and an !important around it), and whether it is marked !important.
Line = namedtuple("Line", "name start end important")
# One thing the scanner cannot take as it stands. `block` is the one of the three it is about, or None for a rule
# outside them; `variable` the custom property, or None; `kind` is "missing", "twice", "nested", "variable" or "elsewhere".
Trouble = namedtuple("Trouble", "block variable message kind")


class Sheet(object):
    """What scan_css found in a stylesheet (see there)."""

    def __init__(self, plain):
        self._plain = plain      # the stylesheet with its comments blanked
        self.spans = {}      # {block: {custom property: (start, end)}}
        self.unsure = {}     # {block: {custom property: ("twice" or "important", why it has no one value)}}
        self.problems = []   # [Trouble]

    def value(self, block, variable):
        """The value of a custom property of a block as it is written, comments left out."""
        start, end = self.spans[block][variable]
        return _squeeze(self._plain[start:end])


def _css_code(text):
    """Two copies of a stylesheet, each exactly as long as the text, so that a place in one is the same place in
    the text: `plain` has every comment blanked; `code` has the comments, the insides of strings and the insides
    of unquoted url(...) blanked, so that every { } ; ( ) : left in it is one the stylesheet means. A /* inside a
    string is part of the string, and a quote inside a comment is part of the comment."""
    if not _CSS_SKIP.search(text):
        return text, text
    plain, code, at, n = [], [], 0, len(text)
    while at < n:
        m = _CSS_SKIP.search(text, at)
        if not m:
            break
        start, token = m.start(), m.group()
        plain.append(text[at:start])
        code.append(text[at:start])
        if token == "/*":
            end = text.find("*/", start + 2)
            end = n if end < 0 else end + 2
            plain.append(" " * (end - start))
            code.append(" " * (end - start))
        elif token in _CSS_STRING:
            end = _CSS_STRING[token].match(text, start).end()
            plain.append(text[start:end])
            code.append(token + " " * (end - start - 1))
        else:  # url(
            inside = start + 4
            while inside < n and text[inside] in _CSS_SPACE:
                inside += 1
            if inside < n and text[inside] in "\"'":
                end = start + 4  # a quoted address: the string is taken on the next round
                code.append(text[start:end])
            else:
                end = text.find(")", inside)
                end = n if end < 0 else end
                code.append(text[start:start + 4] + " " * (end - start - 4))
            plain.append(text[start:end])
        at = end
    plain.append(text[at:])
    code.append(text[at:])
    return "".join(plain), "".join(code)


def _rules(code):
    """The blocks of a stylesheet at its top level, each with the blocks inside it. Braces that do not pair up
    are refused."""
    top, open_rules, start = [], [], 0
    for m in _CSS_STRUCTURE.finditer(code):
        at, ch = m.start(), m.group()
        if ch == "{":
            open_rules.append((start, at, []))
        elif ch == "}":
            if not open_rules:
                raise _unpaired()
            began, opened, children = open_rules.pop()
            (open_rules[-1][2] if open_rules else top).append(Rule(began, opened, at, children))
        # what ends in ; is a statement (@import, @charset) or a line of a block: the next block begins after it
        start = at + 1
    if open_rules:
        raise _unpaired()
    return top


def _selector(plain, rule):
    return _squeeze(plain[rule.start:rule.open])


def _lines(plain, code, rule):
    """The lines of a block that set a custom property, in order: [Line]. Lines of the blocks inside it are theirs."""
    out, begin = [], rule.open + 1
    for child in rule.children + [None]:
        end = rule.close if child is None else child.start
        if code.find("--", begin, end) >= 0:
            depth, piece = 0, begin
            for m in _CSS_PIECE.finditer(code, begin, end):
                ch = m.group()
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth = max(0, depth - 1)
                elif depth == 0:  # a ; inside brackets is part of the value
                    out.append(_line(plain, code, piece, m.start()))
                    piece = m.start() + 1
            out.append(_line(plain, code, piece, end))
        begin = end if child is None else child.close + 1
    return [line for line in out if line]


def _line(plain, code, begin, end):
    m = _CSS_PROPERTY.match(code, begin, end)
    if not m:
        return None
    start = m.end()
    while start < end and plain[start] in _CSS_SPACE:
        start += 1
    while end > start and plain[end - 1] in _CSS_SPACE:
        end -= 1
    important = _IMPORTANT.search(code, start, end)
    if important:
        end = important.start()
        while end > start and plain[end - 1] in _CSS_SPACE:
            end -= 1
    return Line(m.group(1), start, end, bool(important))


def _shown_rule(plain, rule, inside, deeper):
    """A rule as a message quotes it, inside the (at most two) rules it stands in: `@supports (a: b) { :root { ... } }`."""
    outer = (["..."] if deeper else []) + [_selector(plain, r) for r in inside]
    text = " { ".join(outer + [_selector(plain, rule)])
    return _visible(text if len(text) <= 100 else text[:100] + "...") + " { ... }" + " }" * len(outer)


def _some(names, most=3):
    names = list(dict.fromkeys(names))
    return _listed(names) if len(names) <= most else ", ".join(names[:most]) + " and others"


def scan_css(text):
    """Where a stylesheet keeps the palette: the one reading of it that both `read_css` and the intake's editor
    (`_site.edit_css`) work from, so that "the check reads it" and "the intake can write it" are one fact.
    It returns a Sheet:

    - `spans[block]`, for each of "light", "dark" and "dark_media" that the stylesheet has once and as a plain
      list of lines: {custom property: (start, end)}, the place in the text of the value of every custom
      property the block sets exactly once and without `!important`. The value is what stands between the
      colon and the `;` (or the end of the block), without the space and the comments around it.
    - `unsure[block]`: {custom property: (kind, why)}, the ones such a block sets more than once or marks `!important`.
    - `problems`: [Trouble(block, variable, message, kind)], everything about the palette's colours that cannot
      be taken as it stands. A block that is not there, or stands in another shape ("missing"). A block that
      stands more than once ("twice") or holds another block ("nested"): it has no spans. One of the palette's
      variables set twice in a block, or marked `!important` ("variable"). And any OTHER rule of the stylesheet,
      at any depth, that sets one of the palette's variables ("elsewhere", block None): the page may show
      that colour and not the block's.

    The three blocks are: at the top level, a rule whose selector is exactly `:root`; one whose selector is
    exactly `:root[data-theme="dark"]` (either kind of quote); and, inside a top-level `@media
    (prefers-color-scheme: dark)`, a rule whose selector is exactly `:root:not([data-theme])`. Space and
    comments around a selector do not count, and neither does what line it starts on.

    A comment is not text, and a `/*` inside a string is not a comment. A brace, a `;` or a `--name:` inside a
    string or an unquoted url(...) is not one. A statement before a block (`@import ...;`) does not hide it.
    Braces that do not pair up are refused (Refusal "css-unreadable"). The work grows with the length of the
    text and no faster."""
    plain, code = _css_code(text)
    sheet = Sheet(plain)
    taken = {block: [] for block in BLOCKS}
    elsewhere = []   # [(rule as a message shows it, its selector, in a block for the dark preference?, the variables it sets)]
    more = 0         # how many further rules set one of the variables, beyond the ones kept in `elsewhere`

    def others(rule, inside, in_dark_media):
        """Every rule that is none of the three blocks, at any depth: the ones that set one of the palette's variables."""
        nonlocal more
        todo = [(rule, inside, False, in_dark_media)]  # (a rule, the two rules nearest around it, are there more around those?, ...)
        while todo:
            rule, inside, deeper, in_dark_media = todo.pop()
            if plain[rule.start:rule.open].lstrip(_CSS_SPACE)[:1] == "@":
                in_dark_media = in_dark_media or bool(_DARK_MEDIA_LIKE.match(_selector(plain, rule)))
            set_here = [line.name for line in _lines(plain, code, rule) if line.name in KEY_OF_VARIABLE]
            if set_here and len(elsewhere) < 2 * MOST_NAMED:
                elsewhere.append((_shown_rule(plain, rule, inside, deeper), _selector(plain, rule), in_dark_media, set_here))
            elif set_here:
                more += 1
            around = (inside + [rule])[-2:]
            for child in reversed(rule.children):
                todo.append((child, around, deeper or len(inside) == 2, in_dark_media))

    for rule in _rules(code):
        selector = plain[rule.start:rule.open].strip(_CSS_SPACE)
        if _IS_LIGHT.fullmatch(selector):
            taken["light"].append(rule)
        elif _IS_DARK.fullmatch(selector):
            taken["dark"].append(rule)
        elif _IS_MEDIA.fullmatch(selector):
            for child in rule.children:
                if _IS_MEDIA_ROOT.fullmatch(plain[child.start:child.open].strip(_CSS_SPACE)):
                    taken["dark_media"].append(child)
                else:
                    others(child, [rule], True)
        else:
            others(rule, [], False)

    # a rule on :root that sets the colours where one of the three blocks is missing is most likely that block,
    # written in another way: it is said together with the block that is not there, once
    stand_in = {block: [] for block in BLOCKS}
    alone = []
    for found in elsewhere:
        _shown, selector, in_dark_media, set_here = found
        guesses = []
        for part in selector.split(","):
            if ":root" in part.lower():
                guesses.append("dark_media" if in_dark_media else "dark" if _DARK_LIKE.search(part) else "light")
        guesses = [block for block in dict.fromkeys(guesses) if not taken[block]]
        for block in guesses:
            stand_in[block].append(found)
        if not guesses:
            alone.append(found)

    def trouble(block, variable, kind, message):
        sheet.problems.append(Trouble(block, variable, message, kind))

    for block in BLOCKS:
        found = taken[block]
        if not found:
            message = _NOT_FOUND[block]
            if stand_in[block]:
                shown, _selector_text, _dark, set_here = stand_in[block][0]
                others_too = len(stand_in[block]) - 1
                message += (" The rule `%s` sets %s, but it is written in another way than the starter writes it (%s, at the top "
                            "level of the stylesheet), so this check did not read it and the intake does not write to it%s. Write it "
                            "as the starter does, or set the colours by hand."
                            % (shown, _some(set_here), _STARTER[block],
                               "" if not others_too else "; %d other rule%s like it too" % (others_too, " is" if others_too == 1 else "s are")))
            trouble(block, None, "missing", message)
        elif len(found) > 1:
            again = [line.name for rule in found[1:1 + 2 * MOST_NAMED] for line in _lines(plain, code, rule) if line.name in KEY_OF_VARIABLE]
            trouble(block, None, "twice",
                    "The stylesheet has %d blocks of the kind that holds %s (%s), and a later one sets %s. This check reads each of "
                    "the three colour blocks only where it stands once, as in the starter's stylesheet: the intake writes to the "
                    "first, and a browser lets a later one win. Fold them into one block."
                    % (len(found), _HOLDS[block], BLOCK[block], _some(again) if again else "no colour"))
        elif found[0].children:
            inner = _visible(_selector(plain, found[0].children[0]))
            trouble(block, None, "nested",
                    "%s holds another block inside it (`%s { ... }`), which the starter's does not. This check reads a colour block "
                    "only as a plain list of lines, so it was not read." % (BLOCK[block][0].upper() + BLOCK[block][1:], inner[:60]))
        else:
            by_name = {}
            for line in _lines(plain, code, found[0]):
                by_name.setdefault(line.name, []).append(line)
            sheet.spans[block], sheet.unsure[block] = {}, {}
            for name, lines in by_name.items():
                written = [_visible(_squeeze(plain[line.start:line.end])[:40]) + (" !important" if line.important else "") for line in lines[:4]]
                if len(lines) > 1:
                    sheet.unsure[block][name] = ("twice", "it is set %d times in %s" % (len(lines), BLOCK[block]))
                    if name in KEY_OF_VARIABLE:
                        trouble(block, name, "variable", "It is set %d times in this block (%s). This check does not pick one of them: "
                                                         "leave one line." % (len(lines), _some(written)))
                elif lines[0].important:
                    sheet.unsure[block][name] = ("important", "it is marked !important in %s" % BLOCK[block])
                    if name in KEY_OF_VARIABLE:
                        trouble(block, name, "variable", "The colour %r is not one this check can read: it is marked !important, and "
                                                         "this check does not work out which line wins where one is. Take the "
                                                         "!important off." % written[0])
                else:
                    sheet.spans[block][name] = (lines[0].start, lines[0].end)
    for shown, selector, _dark, set_here in alone[:MOST_NAMED]:
        on_root = ":root" in selector.lower()
        trouble(None, None, "elsewhere",
                "%s %s also set in the rule `%s`, %s (%s): the page may show another colour there than the block's. This check did "
                "not read that rule and the intake does not write to it. Move the line into the block it belongs to or take it "
                "out, or set the colours by hand."
                % (_some(set_here), "is" if len(set(set_here)) == 1 else "are", shown,
                   "a rule on :root that is written in another way than the starter writes it: the starter keeps the palette in "
                   "three blocks and nowhere else" if on_root else "outside the three blocks that hold the palette", _THREE))
    rest = max(0, len(alone) - MOST_NAMED) + more
    if rest > 0:
        trouble(None, None, "elsewhere", "%d more rule%s outside the three blocks set%s one of the palette's colours." % (
            rest, "" if rest == 1 else "s", "s" if rest == 1 else ""))
    return sheet


def read_css(text):
    """The colour tokens of a stylesheet's three blocks, as hex. It reads what the intake's editor
    (_site.edit_css) can write to and names the rest in `problems`; both work from `scan_css`, which says
    what the three blocks are and what is named:

    - A block that is not there, stands more than once or holds another block is not read: a problem
      names it. Nothing is merged, and no later line is taken to win. `found` holds the blocks that
      were read.
    - In a block, a colour variable set more than once, or marked `!important`, has no value: a problem
      names the variable.
    - Any other rule that sets one of the palette's variables (`body { --bg: ... }`, `:root.dark { ... }`,
      a `:root` rule inside another at-rule) is a problem that names the rule and the variable.
    - A value written as `var(--other)` is read as that variable's value where the block itself sets it
      once and plainly, or else (in a dark block) where the `:root` block does. Where the variable it
      points at is set twice or marked `!important`, in the block or in `:root`, that is a problem: it is
      never read from another block in its place.
    - A value that is no colour this check reads is a problem that names the variable.
    - Braces that do not pair up are refused."""
    sheet = scan_css(text)
    css = Css()
    css.problems = [(t.block, t.variable, t.message) for t in sheet.problems]
    css.found = set(sheet.spans)
    for block, target in (("light", css.light), ("dark", css.dark), ("dark_media", css.dark_media)):
        if block in sheet.spans:
            _fill(css, sheet, block, target)
    css.brand = css.light.pop("brand", None)
    return css


def _points_at(sheet, block, name):
    """(the value of the custom property a var() of this block points at, None) or (None, why it has none)."""
    if name in sheet.unsure[block]:
        return None, sheet.unsure[block][name][1]
    above = sheet.unsure.get("light", {}).get(name) if block != "light" else None  # a dark block is laid over the :root block
    if name in sheet.spans[block]:
        if above and above[0] == "important":
            return None, above[1] + ", which wins over this block's line"
        return sheet.value(block, name), None
    if above:
        return None, above[1]
    if block != "light" and name in sheet.spans.get("light", ()):
        return sheet.value("light", name), None
    return None, ""


def _fill(css, sheet, block, target):
    for var in sheet.spans[block]:
        key = KEY_OF_VARIABLE.get(var)
        if key is None:
            continue
        value = sheet.value(block, var)
        m = _VAR.fullmatch(value)
        if m:
            value, why = _points_at(sheet, block, m.group(1))
            if value is None:
                css.problems.append((block, var, "It is written as var(%s), and %s has no one value that this check can read here%s."
                                     % (m.group(1), m.group(1), " (%s)" % why if why else "")))
                continue
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
