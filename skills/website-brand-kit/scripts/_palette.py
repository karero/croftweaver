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
import unicodedata
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

_HEADING_LINE = re.compile(r"#{1,6}(?: |\Z)")  # a heading: one to six # and then a blank or the line's end (a line's blanks are single spaces by then)
_SECTION = re.compile(r"(brand|light theme|dark theme)(?: ?\(([^()]*)\))?")
_REMARK_BRAND = "fixed, theme-independent"  # the template's own remark on `### Brand`
_REMARK_MARK = re.compile(r"propos(?:ed|als?)")
_PALETTE = re.compile(r"colou?r palette")  # rule 0: the heading of the part of a longer text that holds the palette
_WORD = re.compile(r"propos(?:ed|als?)", re.I)  # the mark (rule 9); _mark_in says where it stands as a whole word
_MARK_WORDS = ("proposals", "proposed", "proposal")
_AROUND_MARK = "*_`~"  # what may stand around the mark and is not counted: emphasis marks, backticks, a strike-through
_OTHER_THEME = {"light": "dark", "dark": "light"}
_ALSO_SAID = {"dark": "night", "light": "day"}
# Rule 2: a theme's word is its name whole, or one of two closed compounds, each with or without digits after it
# (`dark`, `dark2`, `darkmode`, `darktheme3`). Any other word that begins so is an ordinary word (`darker`, `lightness`).
_THEME_WORD = {theme: re.compile(r"%s(?:mode|theme)?\d*" % theme) for theme in ("light", "dark")}
# Rule 2: the words a label for a theme may be made of beside the theme's own ("Dark mode", "These are the dark values").
_LABEL_WORDS = frozenset("theme mode the values value colours colors colour color tokens token palette scheme variant version table hex set "
                         "for in use these are".split())
_TAG = re.compile(r"</?[A-Za-z][^<>]*>")
_WORDS = re.compile(r"[^\W_]+")
_FENCE = re.compile(r"(`{3,})[^`]*|(~{3,}).*")  # the line that opens a fenced code block
_SEPARATOR = re.compile(r":?-+:?")
_PLACEHOLDER = re.compile(r"#?\[([^\[\]#0-9]*)\]|#?(?:\.\.\.|…)|[-–—]+")
# A colour written as a value (rule 12): a # with 3, 4, 6 or 8 hex digits, with no letter, digit or & straight before
# it (a link's `page#fab`, an entity `&#123;`) and no letter or digit straight after it; or one of the five functions
# this check reads, with its brackets. An underscore beside it is emphasis (`_#16162a_`), not part of a word. Nothing
# in the pattern can match the same text in two ways, so no line makes the search slow.
_COLOUR = re.compile(r"(?<![^\W_])(?<!&)#(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{3,4})(?![^\W_])|(?<![^\W_])(?:rgba?|hsla?|oklch)\(([^()]*)\)", re.I)
_VALUE_FORM = re.compile(r"#|[A-Za-z-]+\(")
_BREAKS = "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"  # what str.splitlines() ends a line at
# A line's blanks (rule 1): what a person sees as a space. The space, the tab, and Unicode's category Zs: the no-break
# space, U+1680, U+2000 to U+200A, U+202F, U+205F, U+3000. Nothing else: no U+001C to U+001F, no U+0085.
_BLANKS = re.compile("[ \t\u00a0\u1680\u2000-\u200a\u202f\u205f\u3000]+")
_NOT_A_BREAK = re.compile("[^%s]" % _BREAKS)
# Rule 9's refusal: the eight of _BREAKS that are no line feed and no carriage return. A text that holds one is not read.
_OTHER_BREAK = re.compile("[\v\f\x1c\x1d\x1e\x85\u2028\u2029]")
_PLAIN_BREAK = re.compile("\r\n|[\n\r]")  # where a line ends in an editor and to a Markdown reader
MOST_NAMED = 5  # how many lines one kind of "not read" problem quotes; the rest are counted

# What one cell holds. kind: "colour" (exactly one colour: `value` is its hex, `named` says it was written as a colour
# name, `form` that it was written as a hex or a function), "refused" (exactly one colour that is not taken: `err` says
# why), "like" (a colour written as a value, with something else beside it), "words", "empty", "placeholder".
Look = namedtuple("Look", "kind value text marked named form err")
Row = namedtuple("Row", "line label key cells looks above_separator long")


_EMPHASIS = re.compile(r"[*_`]")


def _figure(ch):
    """Is this a figure that is no digit of a number: a raised or lowered one (`²`), a circled one, a fraction
    (Unicode's category No)? Beside the mark it is a footnote mark, and joins nothing."""
    return ch > "\x7f" and unicodedata.category(ch) == "No"


def _seen(text):
    """A line as the searches for a word look at it (the mark, rule 9; a label, rule 2), so that a character
    nobody sees does not hide the word. ONE pass takes out every character of four of Unicode's categories, and
    does nothing else: Cf (a soft hyphen, a zero-width space or joiner, a byte-order mark), Cc (a control
    character; a tab stays), Mn and Me (a variation selector, a combining stroke or accent)."""
    if text.isascii() and text.isprintable():
        return text
    return "".join(c for c in text if c == "\t" or unicodedata.category(c) not in ("Cf", "Cc", "Mn", "Me"))


def _mark_in(text):
    """Where the mark stands in `text` as a whole word (rule 9): (start, end, the word in lower case), or None.
    The places are in the text as _seen gives it, which is the text itself unless it holds a character nobody
    sees. No letter and no digit is joined to the word; an underscore beside it is emphasis (`_proposed_`), and
    a figure that is no digit a footnote mark (`proposed²`, `proposed①`)."""
    text = _seen(text)
    m = _WORD.search(text)
    while m:
        before, after = text[m.start() - 1:m.start()], text[m.end():m.end() + 1]
        if not (before.isalnum() and not _figure(before)) and not (after.isalnum() and not _figure(after)):
            return m.start(), m.end(), m.group().lower()
        m = _WORD.search(text, m.end())
    return None


def _mark_after(text):
    """Where the mark after the colour of a value cell begins (rule 5), or None: the word at the end of the cell,
    in round brackets or after a space. Emphasis marks, backticks and a strike-through around it are not
    counted, and neither is a footnote figure after it (`#a6abce ~~proposed~~`, `#a6abce (**proposed**)`,
    `#a6abce proposed²`, `#a6abce (proposed²)`). Every character is looked at once, from the end, so no cell
    makes this slow."""
    def back(at, takes):
        while at and takes(text[at - 1]):
            at -= 1
        return at

    def word(at):
        return next((at - len(w) for w in _MARK_WORDS if text[max(0, at - len(w)):at].lower() == w), None)

    around = _AROUND_MARK.__contains__
    after = lambda ch: ch in _AROUND_MARK or _figure(ch)  # noqa: E731
    at = back(len(text), after)
    if text[at - 1:at] == ")":
        at -= 1
        start = word(back(at - 1 if text[at - 1:at] == " " else at, after))
        if start is None:
            return None
        at = back(start, around)
        at = at - 1 if text[at - 1:at] == " " else at
        if text[at - 1:at] != "(":
            return None
        at = back(at - 1, around)
        return at - 1 if text[at - 1:at] == " " else at
    start = word(at)
    if start is None:
        return None
    at = back(start, around)
    return at - 1 if text[at - 1:at] == " " else None


def _label_for_other(text, theme):
    """Rule 2: the word that makes a line of text, or one cell of a header row, under `theme`'s heading a label for
    the OTHER theme, or None. The text is cleaned (_seen), HTML tags, markers, emphasis, brackets and punctuation
    are taken out, and what is left is words: it is such a label when one of them is the other theme's word
    (_THEME_WORD: `dark`, `darkmode` or `darktheme`, with or without digits after it, and the same for light; or
    `night` for dark, `day` for light, whole) and every other one is one of _LABEL_WORDS or a number. (Its own
    theme's word is no such word: a line that holds it is no label. Neither is `darker` or `lightness`.)"""
    other = _OTHER_THEME[theme]
    words = _WORDS.findall(_TAG.sub(" ", _seen(text)).lower())
    theirs = [w for w in words if _THEME_WORD[other].fullmatch(w) or w == _ALSO_SAID[other]]
    return theirs[0] if theirs and all(w in _LABEL_WORDS or w.isdigit() for w in words if w not in theirs) else None


def _fenced(lines):
    """(the places, counted from 0, of the lines that stand inside a fenced code block; the place of the line that
    opens a block that is never closed, or None). A block runs from after a line that begins with three or more
    backticks (and has no backtick after them) or three or more tildes, up to the next line that is nothing but
    that many of the same mark, or more; or to the end of the text."""
    inside, fence, opened = set(), None, None
    for at, line in enumerate(lines):
        if fence is None:
            m = _FENCE.fullmatch(line) if line[:3] in ("```", "~~~") else None
            fence, opened = m and (m.group(1) or m.group(2)), at
        elif line.startswith(fence) and not line.strip(fence[0]):
            fence = None
        else:
            inside.add(at)
    return inside, opened if fence else None


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


_UNSEEN_NOTE = " (What is written as <U+...> in the quote is a character that does not show on the screen: take it out.)"


def _unseen(text):
    """A sentence to put after a quote that holds a character written as <U+...>, or nothing."""
    if text.isprintable():
        return ""
    return _UNSEEN_NOTE


def _css_shown(text):
    """A piece of a stylesheet as a message quotes it: a tab, a line end or a form feed is a blank to CSS and is shown
    as one; any other character that does not show is written as <U+...> (see _noted)."""
    return _visible(re.sub("[\t\r\n\f]", " ", text))


_HIDDEN_IN_QUOTE = re.compile(r"<U\+(?!000[9ACD]>)[0-9A-F]{4,6}>")   # a <U+...> that is not one of CSS's own blanks


_BLANK_NAMES = (("\n", "a line end"), ("\r", "a carriage return"), ("\t", "a tab"), ("\f", "a form feed"))


def _blanks_named(raw):
    """A sentence that names what each of CSS's own blanks in the piece `raw` is, as its quote shows it (<U+0009> and
    so on), or nothing. Read from the characters themselves, not from the quote, where the same six letters could be
    written in the file. Said where a quote shows them exactly (after a backslash, where the character is the one the
    backslash stands before): none of them is a character to take out, so _noted's sentence would be the wrong advice."""
    named = ["<U+%04X> is %s" % (ord(c), what) for c, what in _BLANK_NAMES if c in raw]
    return " (In the quote, %s: the character after the backslash, as the file has it.)" % ", ".join(named) if named else ""


def _noted(message):
    """A stylesheet message with the sentence that says what <U+...> is, where a quote in it holds a character that does
    not show. A tab, line end or form feed written so (after a backslash, where it matters) is no such character."""
    return message + _UNSEEN_NOTE if _HIDDEN_IN_QUOTE.search(message) and _UNSEEN_NOTE not in message else message


def _is_heading(line):
    """Is this line a heading? One to six # at its start, then a blank or the end of the line. `#1: ...`, `#Brand`
    and a hex colour at the start of a line are text."""
    return bool(_HEADING_LINE.match(line))


def _section(plain):
    """What the text of a heading names, given as _plain() makes it: (None, None) when it is not `Brand`, `Light theme`
    or `Dark theme`, alone or with one bracketed remark; else (that section, what its remark is: "" for none or the
    template's own on Brand, "proposed" for the mark, "other" for any other, which rule 2 does not read)."""
    m = _SECTION.fullmatch(plain)
    if not m:
        return None, None
    name, remark = m.group(1).split()[0], m.group(2)  # "brand", "light", "dark"
    if remark is None or (name == "brand" and remark.strip() == _REMARK_BRAND):
        return name, ""
    # `(~~proposed~~)`, `(proposed²)`: a strike-through and a footnote figure are taken off beside the word only (rule 9)
    bare = remark.rstrip("".join(c for c in set(remark) if c in " ~" or _figure(c))).lstrip(" ~")
    return name, "proposed" if _REMARK_MARK.fullmatch(bare) else "other"


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
        if inner is None or not ("..." in inner or "…" in inner):  # rule 12: the template's rgba(...,0.06) is passed over
            return m
    return None


def _look(cell):
    """What one cell holds (see Look). A colour is a colour only when it is the whole cell: backticks may stand
    around it and the mark `(proposed)` after it, and nothing else."""
    marked = bool(_mark_in(cell))
    text = _unwrap(cell)
    after = _mark_after(text) if marked else None  # (the mark after a colour is the word, whole: without the word there is none)
    if after is not None:
        text = _unwrap(text[:after].strip())
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


_COMMENT_END = re.compile("-->|--!>")


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
        # A comment ends at the first `-->` (`<!-->` and `<!--->` are whole comments) or `--!>`, as a browser ends one
        # (HTML's comment states; `<!--!>` and `<!---!>` do not end there, so a `--!>` counts from after `<!--`). One
        # search finds whichever comes first and stops there, so the reading stays linear in the text.
        m = _COMMENT_END.search(text, start + 2)
        while m and m.group() == "--!>" and m.start() < start + 4:
            m = _COMMENT_END.search(text, m.start() + 1)
        if not m:
            unclosed = len((text[:start] + "x").splitlines())
        end = m.end() if m else len(text)
        out.append(text[at:start])
        out.append(_NOT_A_BREAK.sub(" ", text[start:end]))
        at = end
    return "".join(out), unclosed


def _other_line_end(text):
    """Rule 9's refusal as a sentence, or None: said of a text that holds a character at which str.splitlines()
    ends a line and a Markdown reader does not (_OTHER_BREAK). The line's number is counted by line feeds and
    carriage returns alone, as an editor counts it."""
    found = _OTHER_BREAK.findall(text)
    if not found:
        return None
    number, line = next((n, l) for n, l in enumerate(_PLAIN_BREAK.split(text), 1) if _OTHER_BREAK.search(l))
    at, more = _OTHER_BREAK.search(line).start(), len(found) - 1
    code, kinds = "U+%04X" % ord(found[0]), ", ".join("U+%04X" % ord(c) for c in dict.fromkeys(found[1:]))
    return ("Line %d, %s, holds a character that this check takes for the end of a line and a Markdown reader does not (%s, written as <%s> in the "
            "quote). This check would begin a new line there where the text has none, which can cut a word or a value in two, so it read nothing of "
            "this text: its tables were not looked at, and may be fine as they are.%s Delete each such character, or put a plain new line in its "
            "place, then check again."
            % (number, _quoted(line, 80, (at, at + 1)), code, code, " The text holds %d more character%s of that kind%s." % (
                more, "" if more == 1 else "s", "" if kinds == code else " (%s)" % kinds) if more else ""))


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
        self.label = None     # the line that leaves open which section the tables here belong to (a line before the first table that
                              # names another section, or the heading itself with a remark that is not read): no table is filed under it
        self.whole = True     # no heading says `Colour palette`: the whole text is the palette (rule 0)
        self.foreign = False  # a heading that names none of the three sections was met: the text holds more than the three tables
        self.caption = None   # the last line of text above the table being collected
        self.caption_at = 0   # its number
        self.fenced = set()   # the places (from 0) of the lines inside a fenced code block: none of them is a heading (rule 0)
        self.open_fence = None  # the place of the line that opens a code block that is never closed
        self.rows = []        # the table being collected
        self.said = set()     # numbers of the lines whose colours were read, or are named by a problem of their row or table
        self.mark_read = set()  # numbers of the lines on which the word is read as a mark (rule 9)
        self.colours = []     # [(number, line)]: every line that holds a colour written as a value (rule 12)
        self.marks = []       # [(number, line)]: every line that holds the word (rule 9)

    # -- lines --

    def read(self, text):
        refused = _other_line_end(text[1:] if text[:1] == "\ufeff" else text)  # the text as written, comments too: the quote shows what the file holds
        if refused:
            self.problem("?", None, "palette-line-end", refused)
            return self.p
        text, unclosed = _without_comments(text)
        # (not `raw.split()`: that takes U+001F for a blank too, and a character nobody sees must still be in the line
        # when _seen cleans it for a search)
        lines = [_BLANKS.sub(" ", raw).strip(" ") for raw in text.splitlines()]
        if "```" in text or "~~~" in text:
            self.fenced, self.open_fence = _fenced(lines)
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
            if _mark_in(line):
                self.marks.append((number, line))
            if _colour_in(line):
                self.colours.append((number, line))
            if line.startswith("|"):
                self.table_line(number, line)
                continue
            self.end_table()
            if self.is_heading(number - 1, line):
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

    def is_heading(self, at, line):
        """Is the line at this place (counted from 0) a heading? Inside a fenced code block no line is."""
        return _is_heading(line) and at not in self.fenced

    def where_to_look(self, lines):
        """Rule 0: (how many lines stand before the part of the text that is the palette, the number of its last
        line). The whole text, unless one heading says `Colour palette`: then the part under that heading."""
        heads = [at for at, line in enumerate(lines) if self.is_heading(at, line)]
        found = [at for at in heads if len(lines[at]) <= MAX_LINE and _PALETTE.fullmatch(_plain(_heading(lines[at])))]
        if not found:
            return 0, len(lines)
        self.whole = False
        if len(found) > 1:
            self.problem("?", None, "palette-section-twice",
                         "The heading %s stands %d times in this text (on lines %s%s). This check reads the palette from the part of "
                         "the text under that heading and cannot tell which of them holds it, so it read nothing. Leave that "
                         "heading once, above the three tables."
                         % (_quoted(lines[found[0]]), len(found), _listed([str(at + 1) for at in found[:MOST_NAMED]]),
                            " and further down" if len(found) > MOST_NAMED else ""))
            return 0, 0
        first, level = found[0], _level(lines[found[0]])
        last = next((at for at in heads if at > first and _level(lines[at]) <= level), len(lines))
        # Outside that part nothing is read and nothing is named, with one exception: one of the three headings with a
        # table under it is a palette (or a part of one) written in the wrong place, and is said to be
        stray, heading = [], None
        for at in list(range(first)) + list(range(last, len(lines))):
            line = lines[at]
            if self.is_heading(at, line):
                heading = at if len(line) <= MAX_LINE and _section(_plain(_heading(line)))[0] else None
            elif line.startswith("|") and heading is not None:
                stray.append(heading)
                heading = None
        ended_by_one = last in stray  # the part ends at one of the three headings: they have as many # as `Colour palette`, or fewer
        for at in stray[:MOST_NAMED]:
            if ended_by_one and at >= last:
                deep = min(level, 5)
                self.problem("?", None, "palette-outside-section",
                             "Line %d, the heading %s, has a table under it and stands outside the part of this text that the check "
                             "reads. That part begins at the heading %s (line %d) and ends at the next heading that has as many # as "
                             "that one, or fewer: %s. So that table was not read. Give the three headings with the tables more # than "
                             "the `Colour palette` heading has (`%s Brand` under `%s Colour palette`)."
                             % (at + 1, _quoted(lines[at]), _quoted(lines[first]), first + 1,
                                "this heading" if at == last else "line %d, %s" % (last + 1, _quoted(lines[last])),
                                "#" * (deep + 1), "#" * deep))
                continue
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
        name, remark = _section(_plain(_heading(line))) if len(line) <= MAX_LINE else (None, None)
        self.tables, self.closed, self.label, self.caption = 0, None, None, None
        if name and remark != "other":
            self.section, self.heading = name, None
            self.marked = remark == "proposed"
            if self.marked:
                self.mark_read.add(number)
                self.unmarked = (number, line)
            return
        self.section, self.marked, self.heading = None, False, line
        if not name:
            self.foreign = True
            return
        self.label = line
        plain = HEADING[name]
        self.problem("?", None, "palette-heading-remark",
                     "Line %d, the heading %s, names none of the three sections, so no table under it was read. After `%s` a "
                     "heading may carry one remark in brackets and no other: the mark `(proposed)`, written in English%s. Write the "
                     "heading as `%s`, or as `%s (proposed)` if the values under it are still proposals.%s"
                     % (number, _quoted(line), plain[4:], " (or, on this one, the template's `(%s)`)" % _REMARK_BRAND if name == "brand" else "",
                        plain, plain, _unseen(line)))

    def end_section(self):
        """A heading's mark is read as the mark of the rows under it: where no row under it has a value, say so."""
        if self.unmarked:
            self.problem("?", None, "palette-mark-not-read",
                         "Line %d, the heading %s, carries the mark (proposed), but no row under it has a value that was read, so it "
                         "marked no value. Fill in the rows under it (they then count as proposals), or take the mark out of the "
                         "heading." % (self.unmarked[0], _quoted(self.unmarked[1])))
        self.unmarked = None

    def text_line(self, number, line):
        self.caption, self.caption_at = line, number
        if not self.section:
            return
        if self.tables:
            if self.closed is None:
                self.closed = line
        elif self.label is None and len(line) <= MAX_LINE:
            other = _section(_plain(_seen(line)).rstrip(":").strip())[0]
            what = "is the name of another section"
            if not other and self.section in THEMES and _label_for_other(line, self.section):
                other, what = _OTHER_THEME[self.section], "reads as a label for the other theme"
            if other and other != self.section:
                self.label = line
                here, there = HEADING[self.section], HEADING[other]
                self.problem("?", None, "palette-label",
                             "Line %d, %s, stands between the heading `%s` and its table, and it %s. A "
                             "line of text is not a heading, so this check cannot tell which of the two the table belongs to, and it "
                             "read no table under that heading. If the table belongs under `%s`, write that line as a heading (`%s`); "
                             "if it belongs under `%s`, take the line out.%s" % (number, _quoted(line), here, what, there, there, here, _unseen(line)))

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
            start, end, word = _mark_in(line)  # (where it stands in the line as _seen gives it: near enough for a quote cut around it)
            said = "Line %d, %s, holds the word \"%s\"" % (number, _quoted(line, 80, (min(start, len(line)), min(end, len(line)))), word)
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
                if self.whole and self.foreign:
                    said += (" Or, if this text is a whole brand guide and the palette is one part of it: put the three headings "
                             "with their tables under a heading `## Colour palette`. This check then looks only at that part, and "
                             "a colour in the rest of the guide is not named.")
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
        if self.in_a_fence():  # asked before `self.section`: a heading that counts may stand above the code block
            opened = self.never_closed()
            return "under the line %s, which stands inside a code block (%s), where this check takes no line for a heading" % (
                _quoted(self.caption), "line %d opens one with ``` or ~~~, and no line after it closes it" % opened if opened else "between two lines of ``` or ~~~")
        if self.section:
            return "after the line %s, further down under `%s`" % (_quoted(self.caption or self.closed), HEADING[self.section])
        if self.caption:
            return "under the line %s, which is not a heading (a heading is one to six # and then a space: `### Light theme`)" % _quoted(self.caption)
        if self.heading is None:
            return "above the first heading"
        return "under the heading %s" % _quoted(self.heading)

    def in_a_fence(self):
        """Is the line above the table being read one that would be a heading, were it not inside a fenced code block?"""
        return bool(self.caption) and self.caption_at - 1 in self.fenced and _is_heading(self.caption)

    def never_closed(self):
        """The number of the line that opens the code block around the line above the table, where no line closes that block; or None."""
        return self.open_fence + 1 if self.open_fence is not None and self.caption_at - 1 > self.open_fence else None

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
        # a header row whose first cell is the name of another section than the one the table stands under (rule 2)
        other = _section(_plain(_seen(header.cells[0])).rstrip(":").strip())[0] if header and filed else None
        other = other if other != filed else None
        # or one of whose cells is a label for the other theme: `word` is the word that makes it one
        word = None
        if header and filed in THEMES and not other:
            word = next(filter(None, (_label_for_other(cell, filed) for cell in header.cells)), None)
        if not (both_themes or filed is None or wrong_header or other or word):
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
        elif (other or word) and not both_themes:
            here, there = HEADING[filed], HEADING[other or _OTHER_THEME[filed]]
            self.problem("?", None, "palette-label",
                         "Line %d, the header row %s, %s, and its table stands "
                         "under `%s`. This check cannot tell which of the two the table belongs to, so it did not read the table. If "
                         "the table belongs under `%s`, write that heading on a line of its own above it; if it belongs under `%s`, "
                         "%s (`| Token | Hex |`).%s"
                         % (header.line, _quoted("| %s |" % " | ".join(header.cells)),
                            "calls its first column by the name of another section" if other else "says \"%s\"" % word, here, there, here,
                            "call the first column \"Token\"" if other else "take that word out of the header row", _unseen(titles)))
        elif claims and filed is None and self.label is None:
            if self.in_a_fence():
                opened = self.never_closed()
                advice = ("Take line %d, which opens the code block, out, so that the headings after it count." % opened if opened else
                          "Take the two lines that open and close the code block out, so that the headings inside it count.")
            elif self.section:
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
        # (under a line that names another section, or a heading with a remark that is not read, rule 2's problem has
        # said that no table there was read)
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
            self.problem(section, key, value.err.code, "%s: %s" % (name, value.err))
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

    0. WHERE THE CHECK LOOKS. (Comments are blanked first: rule 1. And a text that holds a line-end
       character other than a plain new line is not read at all, wherever in it that character
       stands: rule 9.) A HEADING, here and in every rule
       below, is a line that starts with one to six `#` followed by a blank or by the end of the line.
       A line that starts with `#` in any other way (`#1: ...`, `#Brand`, a hex colour, seven `#`) is a
       line of text like any other: it ends no section, and rules 9 and 12 hold for it. So is every line
       INSIDE A FENCED CODE BLOCK: after a line that begins with three or more backticks (and has no
       backtick after them) or with three or more tildes, up to the next line that is nothing but that
       mark again, as many or more; or to the end of the text. A `# comment` in a code sample ends no
       section, and a table under a `### Light theme` written inside a fence stands under no heading
       (rule 7's problem says so, and says what to take out: the two fence lines, or, where no line
       closes the block, the one line that opens it, by its number).
       If exactly one heading line of the text says `Colour palette` or `Color palette` and nothing
       else (at any level; emphasis marks and backticks taken out, wherever in the words they stand,
       case ignored), the palette is that SECTION: from that heading's line to the next heading of
       the same or a higher level (as many `#` or fewer), or to the end of the text.
       Rules 1 to 12 are about that part alone, and "the text" in them means that part. Everything
       outside it is not the palette's business: nothing there is read, and nothing there is named,
       neither a colour (rule 12) nor the word proposed (rule 9) nor a table, because a BRAND.md is a
       whole brand guide (a logo, type, a shadow's `rgba(0, 0, 0, 0.06)`, the share cards' colours).
       Two things outside it are named: rule 9's line-end characters, and, so that a palette written in
       the wrong place of such a file is never silently "not there", a heading that says `Brand`, `Light theme` or `Dark theme`, alone or
       with a bracketed remark, with a table under it (a line that starts with `|`, before the next
       heading). A problem quotes that heading and says where the three tables belong; where the
       section ended at such a heading (it has as many `#` as `Colour palette`, or fewer), the problem
       says that, and that the three headings need more `#`. Without a table under it such a
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
       line keeps its number: nothing inside a comment is read, and nothing inside one is named
       (but for rule 9's line-end characters, which are line breaks inside a comment too). A
       comment that is never closed runs to the end of the text, and a problem says on which line it
       opens. Then each run of blanks is made one space, and those at a line's ends are dropped,
       so no input makes a pattern slow. A line's blanks are what a person sees as a space: the
       space, the tab, and every character of Unicode's category Zs (the no-break space, the wide
       and thin spaces U+2000 to U+200A, U+1680, U+202F, U+205F, U+3000). So a `#` with a
       no-break space after it, or before it (as with a tab or four spaces), starts a heading, a line
       with one before its first `|` is a row of a table, and one inside a value is the blank there
       (`rgb(255,<U+00A0>248,<U+00A0>238)`).
       No other character is a blank: not the information separators (U+001C to U+001F), not
       U+0085. U+001F stays in its line as a character nobody sees (rule 9). A table row longer
       than 2,000 characters is not read, and a problem names it.

    2. SECTIONS. Only a heading line (rule 0 says what one is) names a section, and only when its text
       (emphasis marks and backticks taken out, case ignored) is exactly `Brand`, `Light theme` or `Dark
       theme`, with no remark or with one of these two in round brackets after it: the mark
       (`(proposed)`, `(proposal)` or `(proposals)`, in English: rule 9; a strike-through and a
       footnote figure beside the word are not counted, and inside the word they make it another
       remark: `(pro~posed)`), or, on `Brand` only, the template's own `(fixed, theme-independent)`.
       One of the three names with ANY OTHER bracketed remark (`### Dark theme (vorgeschlagen)`, `###
       Light theme (draft)`, `### Brand (proposed by the studio)`) names NO section: a problem quotes
       the heading and says which remark is read there, and no table under it is read. (A mark in
       another language would otherwise pass as a remark, and its values as confirmed.)
       Every other heading ends the section, and so does a heading longer than 2,000 characters,
       whatever it begins with. No other line names a section: no label, no bold line, no sentence.
       Two such lines are not passed over, though, because each leaves open which section a table
       belongs to; a problem quotes the line (`palette-label`), and the table is not read:
       - a line of text of at most 2,000 characters between a section's heading and its first table
         that is the name of ANOTHER section, alone or with a bracketed remark (`**Light theme**`,
         `Dark theme:` or `Light theme (hell)` under `### Brand`; emphasis marks, a colon at its end
         and the characters nobody sees, rule 9, are not counted): no table under that heading is
         read.
       - such a line under `### Light theme` or `### Dark theme` that reads as a label for the OTHER
         theme. The test, with the characters nobody sees taken out (rule 9 says which) and then HTML
         tags, list and quote markers, emphasis, brackets and punctuation (the words inside brackets
         stay): (a) one of its words is the other theme's word. Under Light that is `dark` whole,
         or one of the two compounds `darkmode` and `darktheme`, each with or without digits after
         it (`Dark`, `Dark2`, `Darkmode`, `DarkTheme3`), or `night` whole; under Dark the same
         with `light`, `lightmode`, `lighttheme` and `day`. A hyphen or an underscore makes two
         words of a compound, which reads the same (`dark-mode`, `dark_theme`: the word `dark`
         and one of (c)'s words), but not with digits joined to its second word: `dark-mode2`,
         `dark_theme3` and `Dark mode2` are no labels, because `mode2` is none of (c)'s words
         (`Dark-mode 2` is one, and so is `darkmode2`). Any other word that begins so is an
         ordinary word (`Darker`, `Darkened`, `Darkness`, `Lightness`, `Lighten`, `Lighting`): a
         `Lightness` column under `### Dark theme` is a note. (b) none of its words is its own
         theme's word, by the same test;
         and (c) every other word is one of theme, mode, the, values, value, colours, colors, colour,
         color, tokens, token, palette, scheme, variant, version, table, hex, set, for, in, use,
         these, are, or a number. So `Dark mode`, `(Dark theme)`, `Palette (dark)`, `- Dark theme
         values`, `Table 2: dark theme`, `These are the dark values` and `Night` are such labels: no
         table under that heading is read. Any other line there is only text (a sentence on the
         mood: "Warm paper, dark ink.", "Light for day, dark for night.").
       - a header row (rule 6) whose first cell is such a name of another section (`| Dark theme |
         Hex |` under `### Light theme`), or, under a theme's heading, a header row ONE OF WHOSE
         CELLS is such a label for the other theme, by the same test, each cell on its own (`| Token
         (dark) | Hex |`, `| Token | Hex | Dark theme |`, `| Darkmode | Hex |` under `### Light
         theme`): that table is not read. A cell with other words in it is a note (`| Token | Hex |
         Contrast on dark ink |`). (A header row that holds both words is rule 10's.)
       THE LIMITS of the label test. Each of these is passed over without a word, and the table is
       read under its heading: a longer sentence, or any word outside the list ("This table is for
       the dark theme of the site.", `Dark theme: see the note`, `Dark theme v2`); another language
       (`Dunkel`); a compound in two words with digits joined to the second (`dark-mode2`, point
       (a) above); a caption AFTER the table, and a note in a cell of a row; the other theme's name
       in a row in FRONT of the table (a title row `| Dark theme |` above the header row), or in
       a header row with no `|---|---|` line under it (a table without its separator line has no
       header row to this check: rule 6); a character reference (`&#68;ark theme`,
       `Dark&nbsp;mode`); full-width or look-alike letters; emphasis or a tag INSIDE the word
       (`da**rk** mode`, `<b>Da</b>rk mode`); and a character nobody sees that the one pass does
       not take out (rule 9 lists them).
       Two things go the other way, and the line is named. The three exact names are compared
       with emphasis marks taken out wherever they stand (the first point above), so `da**rk**
       theme` under `### Light theme` IS named, as the name of another section. And an accent
       written as a separate mark is one of the characters taken out, so the same line can be a
       label written that way and text written with the one accented letter (Vietnamese `Dãy 2`
       under `### Dark theme`, which is `Day 2` without the mark).

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
       mark after it (`(proposed)`, or the word after a space; emphasis marks, a strike-through and a
       footnote figure around the mark are not counted: `#a6abce _proposed_`, `#a6abce
       (**proposed**)`, `#a6abce ~~proposed~~`, `#a6abce proposed²`, `#a6abce (proposed²)`). The
       mark after the colour is the word as it is written. The limit: with a character nobody sees
       inside it, or a blank between it and a footnote figure, it is something else beside the
       colour, and the cell is a value that cannot be read (below): a problem, never a colour taken
       as confirmed. The colour is what `_colour.parse_colour` reads as a whole (a hex, rgb(), hsl(),
       oklch(), a CSS colour name).
       - Empty, or a placeholder (`#[…]`, `#...`, `[hex]`, one or more dashes): the row is not filled
         in, which is not a mistake. A colour written as a value further along such a row was not read,
         and rule 12 names the line. Square brackets are a placeholder only around words that could
         not themselves be a colour: around a colour name (`[red]`), around three to eight letters
         that are all hex digits (`[bad]`, `[facade]`) or around anything with a digit or a `#` in it,
         they are a value that cannot be read (the next point), since a colour may have been meant.
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

    9. PROPOSALS. The mark is the word `proposed`, `proposal` or `proposals`, case ignored, as a whole
       word: no letter and no digit joined to it (`unproposed` and `proposed1` are other words). What
       else stands beside it does not make it another word: emphasis marks and backticks (`*proposed*`,
       `__proposals__`, `` `proposed` ``), an underscore (`_proposed_`, `proposed_palette`), a
       strike-through (`~~proposed~~`), brackets, a footnote figure (`proposed²`, `proposed①`: any
       figure that is no digit of a number, raised, lowered, circled or a fraction).
       The search for the word looks at each line with the characters nobody sees taken out, in one
       pass that does nothing else. Those are Unicode's categories Cf (a soft hyphen, a zero-width
       space or joiner, a byte-order mark), Cc (a control character: a NUL, U+001F), Mn and Me (a
       variation selector, the combining stroke that "strike-through text" tools write).
       A WHOLE text that holds, anywhere (outside the part rule 0 names and inside a comment
       too), a character that this reader takes for the end of a line and a Markdown reader
       does not (a vertical tab U+000B, a form feed U+000C, U+001C, U+001D, U+001E, U+0085,
       U+2028, U+2029), which would cut a line in two and a word on it, is not read: ONE problem
       (`palette-line-end`) quotes the first line that holds one, with its number as an editor
       counts it (by line feeds and carriage returns alone), names the character by its code
       point, says how many more the text holds (by code point, where another is among them) and
       what to do (delete each, or put a plain new line in its place), and no row and no value is
       returned.
       THE LIMITS. Each of these inside the word makes it another word, which is passed over without
       a word: a character reference (`&#112;roposed`, `prop&shy;osed`); a full-width, mathematical
       or look-alike letter (a Cyrillic `р` for the `p`); emphasis or a tag (`**pro**posed`,
       `pro<b>posed</b>`); a blank of rule 1, also a thin one (U+2009, U+200A, U+202F), which makes
       two words of it; and a character nobody sees that Unicode files under another category
       than those four: a filler it files as a letter (U+115F, U+1160, U+3164, U+FFA0), a private-use
       character (U+E000) or one it has not assigned (U+2065). The pass follows the Unicode
       tables of the Python that runs it, so a character a newer Unicode added is taken out by a
       newer Python only (U+180F: by Python 3.13, not by 3.9). (In a section's heading, rule 2
       takes emphasis marks out wherever they stand: `### Dark theme (**pro**posed)` is the mark.)
       The mark is read in three places, and only there:
       - in the value cell of a row that rules 3 to 7 read, and in any later cell of that row: the row's
         value is a proposal. The check errs towards asking: "not proposed" marks too. Where the value
         cell of such a row is empty or a placeholder, a problem says the row is marked as a proposal
         and is not filled in. Where the cell cannot be read, the row's own problem stands.
       - as the bracketed remark of a section's heading, where it is the whole remark (rule 2: `###
         Dark theme (proposed)`; emphasis marks around it are not counted): every row with a value
         under that heading is a proposal, in every table of the section. Where no row under it has a
         value, a problem says the heading's mark marked no value.
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
        everything up to its closing bracket, unless an ellipsis stands between the brackets: this
        search passes over such a function (the template's `rgba(...,0.06)`). (That is this rule's
        search only: in a value cell a function with an ellipsis is a value that cannot be read, rule
        5, and no placeholder.) Case is ignored. After the reading,
        every line that holds such a colour is one of three things: a row whose value was read (the
        colours in its later cells are notes); a row that a problem of rules 1 to 8 names, by its own
        name or as one of the rows of a table that was not read; or a line with a colour that was NOT
        READ. Each line of the third kind is a problem that quotes the line, cut so that the colour
        shows, and says that the check reads a colour only from the second cell of a named row under one
        of the three headings: a colour in the first cell (columns the wrong way round), in a row under
        another name, in a row whose value cell is empty, in a list, in a sentence, in a heading, in a
        table row without its first `|`. The first five such lines are quoted, and the rest are counted.
        Where the text has no `Colour palette` heading and has a heading that is none of the three (a
        whole guide, its palette under `## Colours`), the first of these problems also says the remedy
        that fits: put the three tables under a heading `## Colour palette` (rule 0).
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
        self.notes = []      # what the owner should know and is no problem: a stylesheet this one brings in, which was not read


_CSS_BREAK = re.compile(r"\r\n|[\n\r\f]")
_CLOSES = {"}": "{", ")": "(", "]": "["}


def _line_number(text, at):
    """The number of the line of a stylesheet that the place `at` stands on."""
    return len(_CSS_BREAK.findall(text, 0, at)) + 1


def _unpaired(text, opened, closer):
    """The refusal for brackets that do not pair up. `opened` is where the innermost bracket stands that is still
    open, or None when no bracket of the closing one's kind is open at all; `closer` is where a closing bracket
    stands that does not close it (or a `{` that opens a block inside round or square brackets, where a browser
    expects a rule), or None at the end of the text."""
    if closer is not None and text[closer] == "{":
        what = ("the `%s` on line %d is still open where the `{` on line %d opens a block, so a browser takes that block for a part of "
                "what the bracket holds and for no rule" % (text[opened], _line_number(text, opened), _line_number(text, closer)))
    elif opened is None:
        what = "the `%s` on line %d closes nothing: no `%s` is open there" % (text[closer], _line_number(text, closer), _CLOSES[text[closer]])
    elif closer is None:
        what = "the `%s` on line %d is never closed" % (text[opened], _line_number(text, opened))
    else:
        what = "the `%s` on line %d is still open where the `%s` on line %d closes something else" % (
            text[opened], _line_number(text, opened), text[closer], _line_number(text, closer))
    return Refusal(
        "css-unreadable",
        "The stylesheet's brackets do not pair up: %s. So this check cannot tell where the stylesheet's blocks and values "
        "begin and end, and a browser may take everything after that place for something else than it looks like. Mend the "
        "stylesheet, then run this again." % what,
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

# What is no plain text of a stylesheet: a comment, a string, an unquoted url(...), and a backslash. `url(` is the
# word `url` itself: where a letter, a digit, `_`, `-`, `@`, `#`, a backslash, a character beyond ASCII or a NUL
# (which a browser reads as one) stands straight before it, it is the end of a longer name (`-url(`, `@url(`), which
# is a function like any other.
_CSS_SKIP = re.compile("/\\*|[\"']|(?<![\\w\\-@#\\\\\\x00\u0080-\U0010ffff])url\\(|\\\\", re.I)
# A string runs to its closing quote (group 1), or to the end of its line when it is never closed (a line ends at a
# line feed, a carriage return or a form feed). A backslash takes the character after it with it, but no line end:
# no string is followed over a line end (_runs_over says which a browser would follow). Each character is taken by
# one alternative only, so the pattern cannot be made slow.
_CSS_STRING = {q: re.compile(r"%s(?:[^%s\\\n\r\f]|\\[^\n\r\f])*(?:(%s)|\\?(?=[\n\r\f]|\Z))" % (q, q, q)) for q in "\"'"}
_CSS_URL = re.compile(r"(?:[^)\\]|\\[\s\S]?)*")  # what an unquoted url( holds, up to its )
_CSS_STRUCTURE = re.compile(r"[{};()\[\]]")
_CSS_PIECE = re.compile(r"[;()\[\]]")
_CSS_PROPERTY = re.compile(r"{s}(--[\w-]+){s}:".format(s=_S))
# The start of an @-statement: `@` and the first character of a name straight after it. (An `@` before anything else
# is a character on its own, and what follows it is no statement.)
_AT_NAME = "(?:-?[A-Za-z_\\x00\u0080-\U0010ffff]|--)"
_AT_STATEMENT = re.compile("%s@%s" % (_S, _AT_NAME))
_AT_MEDIA = re.compile(r"{s}@media(?![\w-])".format(s=_S), re.I)
_AT_NAMESPACE = re.compile(r"""{s}@namespace{s}(?:url\(|["'])""".format(s=_S), re.I)  # one without a prefix: the default namespace
_AT_IMPORT = re.compile(r"{s}@import(?![\w-])".format(s=_S), re.I)
_AT_CHARSET = re.compile(r"@charset(?![\w-])", re.I)
# The names a browser takes for UTF-8 in an `@charset` (the Encoding Standard's labels for it), in lower case.
_UTF8_NAMES = frozenset(("utf-8", "utf8", "unicode-1-1-utf-8", "unicode11utf8", "unicode20utf8", "x-unicode20utf8"))
_CHARSET_NAME = re.compile(r"""{s}(["'])([^"'\n\r\f]*)\1""".format(s=_S))  # the quoted name after it, read from the text with its strings
_AT_PROPERTY = re.compile(r"@property(?![\w-]){s}(.*)".format(s=_S), re.I | re.S)
_IMPORTANT = re.compile(r"!{s}important{s}\Z".format(s=_S), re.I)
_VAR = re.compile(r"var\({s}(--[\w-]+){s}\)".format(s=_S))
_HTML_MARK = re.compile("<!--|-->")  # the two marks of an HTML comment, which a browser passes over in some places of a stylesheet
_HEX_DIGITS = "0123456789abcdefABCDEF"


def _squeeze(text):
    """The text with each run of space made one space, and none at its ends."""
    return _SQUEEZE.sub(" ", text).strip(_CSS_SPACE)

# One block: where what stands before its { begins, where its { and its } stand, and the blocks inside it.
Rule = namedtuple("Rule", "start open close children")
# One line of a block that sets a custom property: its name, where its value stands in the text (without the space,
# the comments and an !important around it), and whether it is marked !important.
Line = namedtuple("Line", "name start end important")
# One thing the scanner cannot take as it stands. `block` is the one of the three it is about, or None for something
# outside them; `variable` the custom property, or None; `kind` is "missing", "twice", "nested" or "variable" (of a
# block), or "elsewhere", "statement", "namespace", "charset", "escape", "string", "html-comment" or "registered" (of the
# stylesheet: block None).
Trouble = namedtuple("Trouble", "block variable message kind")


class Sheet(object):
    """What scan_css found in a stylesheet (see there)."""

    def __init__(self, plain):
        self._plain = plain      # the stylesheet with its comments blanked
        self.spans = {}      # {block: {custom property: (start, end)}}
        self.unsure = {}     # {block: {custom property: ("twice" or "important", why it has no one value)}}
        self.problems = []   # [Trouble]
        self.notes = []      # sentences for the owner that are no problem and stop nothing: a stylesheet this one brings in

    def value(self, block, variable):
        """The value of a custom property of a block as it is written, comments left out."""
        start, end = self.spans[block][variable]
        return _squeeze(self._plain[start:end])


def _runs_over(body):
    """Does a string that stops at a line end go on in a browser? `body` is what stands between its opening quote
    and that line end. It does where a backslash stands last (the line end is then no part of the string, and the
    string goes on), or a backslash and one to six hex digits (they spell one character, and that takes one blank
    after it with it, a line end too). The backslash must itself be one that is not taken by a backslash before it."""
    at, digits = len(body), 0
    while at and digits < 6 and body[at - 1] in _HEX_DIGITS:
        at, digits = at - 1, digits + 1
    slashes = 0
    while at and body[at - 1] == "\\":
        at, slashes = at - 1, slashes + 1
    return slashes % 2 == 1


def _css_code(text):
    """(plain, code, escape, string). `plain` and `code` are two copies of a stylesheet, each exactly as long as the
    text, so that a place in one is the same place in the text: `plain` has every comment blanked; `code` has the
    comments, the insides of strings and the insides of unquoted url(...) blanked, and a backslash outside a string
    written, with the character after it, as two backslashes (so that `\\{` opens nothing). A /* inside a string is
    part of the string, and a quote inside a comment is part of the comment.

    `escape` is where the first backslash stands that is outside a string and outside a comment, or None; `string`
    is where the first string begins that a browser reads on over the end of its line (_runs_over), or None. Up to
    the first of the two, and up to the first `<!--` or `-->` left in `code`, every { } ; ( ) [ ] : and quote left
    in `code` is one the stylesheet means; after it this reading and a browser's may part, which is why scan_css
    makes each of the three a problem that stops the editor."""
    if not _CSS_SKIP.search(text):
        return text, text, None, None
    plain, code, at, n, escape, string = [], [], 0, len(text), None, None
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
            m = _CSS_STRING[token].match(text, start)
            end = m.end()
            if string is None and not m.group(1) and end < n and _runs_over(text[start + 1:end]):
                string = start
            plain.append(text[start:end])
            code.append(token + " " * (end - start - 1))
        elif token == "\\":
            end = min(n, start + 2)
            escape = start if escape is None else escape
            plain.append(text[start:end])
            code.append("\\" * (end - start))
        else:  # url(
            inside = start + 4
            while inside < n and text[inside] in _CSS_SPACE:
                inside += 1
            if inside < n and text[inside] in "\"'":
                end = start + 4  # a quoted address: the string is taken on the next round
                code.append(text[start:end])
            else:
                end = _CSS_URL.match(text, inside).end()  # (a bracket behind a backslash does not end it)
                code.append(text[start:start + 4] + " " * (end - start - 4))
                if escape is None and text.find("\\", inside, end) >= 0:
                    escape = text.find("\\", inside, end)
            plain.append(text[start:end])
        at = end
    plain.append(text[at:])
    code.append(text[at:])
    return "".join(plain), "".join(code), escape, string


def _rules(text, code):
    """(the blocks of a stylesheet at its top level, each with the blocks inside it; [(start, end)] of every piece
    that ends in `;` where a browser expects a rule and that is no @-statement; [(start, end)] of every top-level
    `@namespace` statement that sets a default namespace; [(start, end)] of every top-level `@import` statement).
    The three kinds of bracket, { ( and [, must pair up and nest, each closed by its own kind: anything else is
    refused, because a browser reads on from an unclosed bracket to wherever it is closed, through the end of the
    block and of every block after it.

    A `;` inside round or square brackets is part of a value. Elsewhere it ends a statement (`@import ...;`) or a
    line of a block, and the next block begins after it. Where a browser expects rules and not lines (at the top
    level, and directly inside a top-level `@media { }`), only a statement that starts with `@` ends at its `;`:
    after anything else (`color: red;`, a `;` alone after a `}`) a browser reads on and takes the `;` and what
    follows for the selector of the next rule, which it then drops. Those are the pieces returned.

    In those same two places a `{` inside round or square brackets is refused like a bracket that does not pair
    up: a browser takes `( a{} :root { ... } ) a{}` for ONE rule, whose selector is everything up to the last `{`,
    so the block inside the brackets is no rule to it. (Inside any other block, such a `{ }` is taken for a block
    in that block, as before: in one of the three colour blocks that is "nested", which stops the editor.)"""
    # stack: every bracket that is open, as (bracket, where it stands) and, for a {, also (where its rule begins, its
    # children, holds rules?); braces: the { among them, so that the block around a block is found without a search
    top, stack, braces, start, loose, namespaces, imports = [], [], [], 0, [], [], []
    for m in _CSS_STRUCTURE.finditer(code):
        at, ch = m.start(), m.group()
        if ch in "([":
            stack.append((ch, at))
            continue
        if ch == "{":
            if stack and stack[-1][0] != "{" and (not braces or braces[-1][4]):
                raise _unpaired(text, stack[-1][1], at)
            entry = (ch, at, start, [], not stack and bool(_AT_MEDIA.match(code, start, at)))
            stack.append(entry)
            braces.append(entry)
        elif ch == ";":
            if stack and stack[-1][0] != "{":
                continue
            if (not stack or stack[-1][4]) and not _AT_STATEMENT.match(code, start, at):
                loose.append((start, at + 1))
            elif not stack and _AT_NAMESPACE.match(code, start, at):
                namespaces.append((start, at + 1))
            elif not stack and _AT_IMPORT.match(code, start, at):
                imports.append((start, at + 1))
        else:
            if not stack or stack[-1][0] != _CLOSES[ch]:
                raise _unpaired(text, stack[-1][1] if any(entry[0] == _CLOSES[ch] for entry in stack) else None, at)
            opened = stack.pop()
            if ch != "}":
                continue
            braces.pop()
            (braces[-1][3] if braces else top).append(Rule(opened[2], opened[1], at, opened[3]))
        start = at + 1
    if stack:
        raise _unpaired(text, stack[-1][1], None)
    return top, loose, namespaces, imports


def _selector(plain, rule):
    return _squeeze(plain[rule.start:rule.open])


def _pieces(code, rule):
    """Where each piece of a block's own text begins and ends: what stands between two `;`, a `;` inside round or
    square brackets being part of a value. The blocks inside it, with what stands before their {, are theirs. Only
    the stretches that hold a `--` are looked at."""
    begin = rule.open + 1
    for child in rule.children + [None]:
        end = rule.close if child is None else child.start
        if code.find("--", begin, end) >= 0:
            depth, piece = 0, begin
            for m in _CSS_PIECE.finditer(code, begin, end):
                ch = m.group()
                if ch in "([":
                    depth += 1
                elif ch in ")]":
                    depth = max(0, depth - 1)  # (one that closes a bracket of the stretch before a block inside)
                elif depth == 0:
                    yield piece, m.start()
                    piece = m.start() + 1
            yield piece, end
        begin = end if child is None else child.close + 1


def _lines(plain, code, rule):
    """The lines of a block that set a custom property, in order: [Line]. Lines of the blocks inside it are theirs."""
    return [line for line in (_line(plain, code, begin, end) for begin, end in _pieces(code, rule)) if line]


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
    return _css_shown(text if len(text) <= 100 else text[:100] + "...") + " { ... }" + " }" * len(outer)


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
    - `unsure[block]`: {custom property: (kind, why)}, the ones such a block sets more than once or marks
      `!important` (or that the `:root` block marks `!important`, which wins over a dark block's line).
    - `problems`: [Trouble(block, variable, message, kind)], everything about the palette's colours that cannot
      be taken as it stands: the list below says what, and `kind` says which.
    - `notes`: sentences for the owner about something that is no problem and stops nothing (point 15).

    THE PROMISE is the value of the palette's ten variables on the page's root element, as this one file sets
    it: what a clean scan reads for a variable is what a browser has for it there, and what the editor writes
    is what a browser then has. It is not a promise about what each rule of the stylesheet does with the
    variables: a rule that paints with a colour of its own (`body { background: #ff0000 }`) is outside it.

    The three blocks are: at the top level, a rule whose selector is exactly `:root`; one whose selector is
    exactly `:root[data-theme="dark"]` (either kind of quote); and, inside a top-level `@media
    (prefers-color-scheme: dark)`, a rule whose selector is exactly `:root:not([data-theme])`. Space and
    comments around a selector do not count, and neither does what line it starts on. A byte order mark at the
    very start of the text is read past (every place in the text stays where it is).

    A comment is not text, and a `/*` inside a string is not a comment. A brace, a bracket, a `;` or a `--name:`
    inside a string or an unquoted url(...) is not one. A string ends at its closing quote, or at the end of
    its line.

    This is a scanner of the starter's shape, not a browser. It does not work out which rule wins; it names
    WHAT COULD MAKE THE PAGE SHOW ANOTHER VALUE THAN THE BLOCK'S LINE SAYS, and the editor refuses on each
    (a problem of a block stops the editor when it has to write to that block; a problem of the stylesheet,
    block None, stops it always). Where it cannot be sure it does not try harder: it stops, with a sentence
    that says what to change.

     1. One of the three blocks is not there, or stands in another shape ("missing").
     2. One of them stands more than once ("twice"), also where the second sets no colour: no spans.
     3. One of them holds another block ("nested"): no spans.
     4. A palette variable is set more than once in its block, or marked `!important` there (on any of its
        lines), or marked `!important` in the `:root` block and set in a dark block as well, where the
        `:root` line wins ("variable").
     5. Any OTHER rule, at any depth, sets a palette variable ("elsewhere", block None): `body { --bg: ... }`,
        `:root.dark { ... }`, a `:root` rule inside another at-rule, a step of `@keyframes`. A block counts as
        one that sets the variable where what stands before its `{` begins with the variable's name and a
        colon: `html:root { --bg: #ff0000 {} }` is a line to a browser, whose value holds a block.
     6. A BACKSLASH ANYWHERE outside a string and outside a comment ("escape", block None; the first one is
        named). A backslash spells a character, and this scanner reads no name written with one: `--b\\67` is
        `--bg` to a browser, `:r\\6f ot` is `:root`, `u\\72l(` is `url(` (what follows, up to the `)`, is then
        no code), and an at-rule's name may be written with one too: Chromium 153 makes an `@property` rule
        of `@\\70roperty --bg { ... }` and of `@p\\72operty --bg { ... }`, a default namespace of `@\\6e
        amespace url(urn:x);` and of `@n\\61mespace url(urn:x);`, and an import of `@\\69mport ...` (round
        5: the page then showed another colour, or none of the palette). So also a class name with an
        escaped colon (`.sm\\:flex`) stops the editor. Inside a string a backslash is ordinary (`content:
        "\\201C"`), with point 7.
     7. A string in which a backslash, or a backslash and one to six hex digits, stands directly before the
        end of the line, and that is not closed on that line ("string", block None; the first one is named).
        A browser reads such a string on over the line end; this scanner follows no string over a line end,
        so from there on the two would read different things.
     8. An HTML comment mark, `<!--` or `-->`, ANYWHERE outside a string, an unquoted url(...) and a comment
        ("html-comment", block None; the first one is named). A browser passes over the two at the top level
        of a stylesheet and reads on straight after them (`<!-- @property --bg { ... }` registers the
        variable), and reads `<!--url(` as the start of a url(...) wherever it stands; this scanner follows
        neither. A stylesheet's own comment is `/* ... */`. (The three characters are named wherever they
        stand: also in `.a-->.b`, which is a class name and a `>` to a browser.)
     9. A piece that ends in `;`, is no @-statement and stands where a browser expects a rule: at the top
        level or directly inside a top-level `@media` ("statement", block None). A browser drops the rule
        after it (`};` before a block, `color: red;` before `:root`, `@media (...) {;`). An @-statement before
        a block (`@import ...;`) does not hide it.
    10. An `@property` rule registers a palette variable ("registered", block None): the variable then has a
        type and a start value of its own.
    11. A top-level `@namespace` statement without a prefix ("namespace", block None): with a default
        namespace, `:root` matches only a root element of that namespace, which a web page's may not be.
    12. An `@charset` with a quoted name that is none of the names a browser takes for UTF-8: `utf-8`,
        `utf8`, `unicode-1-1-utf-8`, `unicode11utf8`, `unicode20utf8`, `x-unicode20utf8`, as written
        between the quotes, case ignored ("charset", block None; the first one is named, wherever it
        stands). This tool reads stylesheets written in UTF-8 only. `@charset "utf-8";` and `@charset
        "utf8";` are ordinary and stop nothing.
    13. Brackets that do not pair up, each `{`, `(` and `[` closed by its own kind in the right order: refused
        as a whole (Refusal "css-unreadable"), because a browser reads on from a bracket that is not closed
        through the end of the block and of the blocks after it. The same refusal for a `{` inside round or
        square brackets where a browser expects a rule (at the top level, or directly inside a top-level
        `@media`): `( a{} :root { ... } ) a{}` is one rule to a browser, and its `:root` block sets nothing.
    14. A value written as `var(--other)`: see `read_css`, which reads it only where it points at another
        palette variable, and never for `--brand`. The editor writes over such a value like over any other
        (and refuses where `--brand` is written so and the palette gives no Primary to write there).
    15. Not a problem, a NOTE: a top-level `@import` statement. The stylesheet it brings in is not read, and
        it can set the colours too, so `notes` says on which line the first one stands and how many more
        there are. An import is ordinary (fonts): it stops nothing.

    What it cannot see, and does not name: anything outside this one file (another stylesheet, what one
    brought in by `@import` holds, a `style` attribute, a script).
    The work grows with the length of the text and no faster."""
    plain, code, escape, string = _css_code(text)
    if text[:1] == "\ufeff":  # a byte order mark: read past, and left in the text, so that every place stays where it is
        plain, code = " " + plain[1:], " " + code[1:]
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
            m = _CSS_PROPERTY.match(code, rule.start, rule.open)  # `--bg: #ff0000 {}`: a line to a browser, whose value holds this block
            if m and m.group(1) in KEY_OF_VARIABLE:
                set_here.insert(0, m.group(1))
            if set_here and len(elsewhere) < 2 * MOST_NAMED:
                elsewhere.append((_shown_rule(plain, rule, inside, deeper), _selector(plain, rule), in_dark_media, set_here))
            elif set_here:
                more += 1
            around = (inside + [rule])[-2:]
            for child in reversed(rule.children):
                todo.append((child, around, deeper or len(inside) == 2, in_dark_media))

    early = []  # what this reading does not follow: from the first of them on, it and a browser may read different things
    if escape is not None:
        end = escape + 2
        while end < len(plain) and end - escape < 30 and plain[end] not in _CSS_SPACE + "{};":
            end += 1
        start = escape
        while start and escape - start < 30 and plain[start - 1] not in _CSS_SPACE + "{};":
            start -= 1
        early.append(("escape", "Line %d of the stylesheet writes a name with a backslash (`%s`). A backslash can spell any character "
                                "(`--b\\67` is `--bg` to a browser, and `u\\72l(` is `url(`), and this check does not read a name written "
                                "with one, so it cannot tell what the stylesheet says from there on. Write the name out without the "
                                "backslash. Where a name cannot be written without one (a class name with a colon in it), move that rule "
                                "into another stylesheet.%s"
                      % (_line_number(text, escape), _visible(plain[start:end]), _blanks_named(plain[start:end]))))   # (a line end after the backslash is the point: shown)
    if string is not None:
        end = string
        while end < len(text) and text[end] not in "\n\r\f":
            end += 1
        early.append(("string", "Line %d of the stylesheet has a string that runs over the end of its line (`%s`: a backslash, or a "
                                "backslash and a number, stands last on the line). A browser reads the next line as a part of that "
                                "string, and this check does not follow a string over a line end, so it cannot tell what the stylesheet "
                                "says from there on. Write the string on one line."
                      % (_line_number(text, string), _css_shown(("..." if end - string > 40 else "") + text[max(string, end - 40):end]))))
    mark = _HTML_MARK.search(code)
    if mark:
        early.append(("html-comment", "Line %d of the stylesheet holds an HTML comment mark (`%s`). A browser passes over such a mark in some places of a stylesheet and reads on "
                                      "straight after it, and this check does not follow that, so it cannot tell what the stylesheet says from there on. Take the mark out. (A "
                                      "comment in a stylesheet is written `/* ... */`.)" % (_line_number(text, mark.start()), mark.group())))
    try:
        top, loose, namespaces, imports = _rules(text, code)
    except Refusal:
        if early:  # the brackets may well pair up to a browser: the reason this cannot tell is the one already found
            raise Refusal("css-unreadable", _noted(" ".join(message for _kind, message in early))) from None
        raise
    for rule in top:
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
        sheet.problems.append(Trouble(block, variable, _noted(message), kind))

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
            trouble(block, None, "twice",
                    "The stylesheet has %d blocks of the kind that holds %s (%s). Each of the three colour blocks must stand once, "
                    "as in the starter's stylesheet: this check does not choose which of several holds the colours, and the intake "
                    "does not write to a stylesheet that has one of them twice. Fold them into one block."
                    % (len(found), _HOLDS[block], BLOCK[block]))
        elif found[0].children:
            inner = _css_shown(_selector(plain, found[0].children[0]))
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
                    important = any(line.important for line in lines)  # on any of them: a browser takes that line, wherever it stands
                    sheet.unsure[block][name] = ("important" if important else "twice", "it is set %d times in %s%s" % (
                        len(lines), BLOCK[block], ", and marked !important there" if important else ""))
                    if name in KEY_OF_VARIABLE:
                        trouble(block, name, "variable", "It is set %d times in this block (%s)%s. This check does not pick one of "
                                                         "them: leave one line%s."
                                % (len(lines), _some(written), ", and marked !important there" if important else "",
                                   ", without !important" if important else ""))
                elif lines[0].important:
                    sheet.unsure[block][name] = ("important", "it is marked !important in %s" % BLOCK[block])
                    if name in KEY_OF_VARIABLE:
                        trouble(block, name, "variable", "The colour %r is not one this check can read: it is marked !important, and "
                                                         "this check does not work out which line wins where one is. Take the "
                                                         "!important off." % written[0])
                else:
                    sheet.spans[block][name] = (lines[0].start, lines[0].end)
    # a line of the :root block that is marked !important wins over the same variable's line in a dark block
    for name, (kind, _why) in sheet.unsure.get("light", {}).items():
        for block in ("dark", "dark_media"):
            if kind == "important" and block in sheet.spans and (name in sheet.spans[block] or name in sheet.unsure[block]):
                sheet.spans[block].pop(name, None)
                sheet.unsure[block][name] = ("important", "it is marked !important in %s, which wins over the line in %s" % (BLOCK["light"], BLOCK[block]))
                if name in KEY_OF_VARIABLE:
                    trouble(block, name, "variable", "It is marked !important in %s, and that line wins over this block's: the page shows "
                                                     "the colour of %s here too. Take the !important off there." % (BLOCK["light"], BLOCK["light"]))
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

    def more_like_it(found, kind, one, several):
        if len(found) > 1:
            trouble(None, None, kind, "%d more %s; the next is on line %d." % (len(found) - 1, one if len(found) == 2 else several, _line_number(text, found[1][0])))

    if loose:
        start, end = loose[0]
        piece = _squeeze(plain[start:end])
        trouble(None, None, "statement",
                "Line %d of the stylesheet has a `;` where a browser expects a rule (%s), and what it ends is no statement that "
                "starts with `@`. A browser reads on from there, takes the `;` and what follows for the selector of the next rule, "
                "and drops that rule: the page would not show what the block after it says. %s"
                % (_line_number(text, end - 1), _quoted(piece),
                   "Take that `;` out." if piece == ";" else "Take that piece out, or move it into the block it belongs to."))
        more_like_it([(end - 1, end) for _start, end in loose], "statement", "piece like it", "pieces like it")
    if namespaces:
        start, end = namespaces[0]
        trouble(None, None, "namespace",
                "Line %d of the stylesheet sets a default namespace (%s). With one, the three colour blocks apply only where the "
                "page's own root element is in that namespace, so a web page may show none of the palette, and this check does not "
                "work that out. Take the statement out, or give the namespace a prefix (`@namespace svg url(...);`)."
                % (_line_number(text, end - 1), _quoted(_squeeze(plain[start:end]))))
    for m in _AT_CHARSET.finditer(code):  # wherever it stands: a browser takes it only as the file's first bytes, and this does not weigh that
        name = _CHARSET_NAME.match(plain, m.end())
        if name and name.group(2).lower() not in _UTF8_NAMES:
            trouble(None, None, "charset", "Line %d of the stylesheet says the file is written in another encoding than UTF-8 (`%s`). This tool reads "
                                           "stylesheets written in UTF-8 only. Save the file as UTF-8 and take that line out."
                    % (_line_number(text, m.start()), _visible(_squeeze(plain[m.start():name.end()])[:60])))
            break
    for kind, message in early:
        trouble(None, None, kind, message)
    registered, todo = [], list(top)
    while todo:  # every rule of the stylesheet, at any depth (each looks at its own text only, so the work stays linear)
        rule = todo.pop()
        todo.extend(rule.children)
        if code.find("@", rule.start, rule.open) >= 0:
            m = _AT_PROPERTY.fullmatch(_squeeze(code[rule.start:rule.open]))
            if m and m.group(1) in KEY_OF_VARIABLE:
                registered.append((rule.open - len(code[rule.start:rule.open].lstrip(_CSS_SPACE)), rule.open))
    registered.sort()
    if registered:
        start, end = registered[0]
        trouble(None, None, "registered",
                "Line %d of the stylesheet registers one of the palette's variables with an `@property` rule (`%s`). A registered "
                "variable has a type and a starting value of its own, so the page may show another colour than the block's line "
                "says, and this check does not read that rule. Take the rule out, or set the colours by hand."
                % (_line_number(text, start), _visible(_squeeze(plain[start:end])[:60])))
        more_like_it(registered, "registered", "rule like it", "rules like it")
    if imports:
        start, end = imports[0]
        start += len(plain[start:end]) - len(plain[start:end].lstrip(_CSS_SPACE))
        shown = _squeeze(plain[start:end])
        sheet.notes.append(_noted("line %d of the stylesheet brings in another stylesheet (`%s`), which this check does not read. If that one "
                                  "sets the site's colours, the page can show other colours than these."
                                  % (_line_number(text, start), _visible(shown if len(shown) <= 60 else shown[:60] + "..."))))
        if len(imports) > 1:
            n = len(imports) - 1
            sheet.notes.append("%d more statement%s like it bring%s in %s; the next is on line %d."
                               % (n, "" if n == 1 else "s", "s" if n == 1 else "", "another stylesheet" if n == 1 else "other stylesheets",
                                  _line_number(text, imports[1][1] - 1)))
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
    - Whatever else `scan_css` lists (a `;` that makes a browser drop the next rule, a backslash outside a
      string, a string that runs over a line end, an HTML comment mark, an `@property` rule for a colour, a
      default namespace, an `@charset` that names another encoding than UTF-8) is a problem too.
    - A value written as `var(--other)` is read ONLY where `--other` is another of the palette's variables
      (the starter's `--link: var(--accent)`): those are the variables the scan holds to "once in its block,
      nowhere else, not `!important`". It is read as that variable's value where the block itself sets it
      once and plainly, or else (in a dark block) where the `:root` block does. Where the variable it
      points at is set twice or marked `!important`, in the block or in `:root`, that is a problem: it is
      never read from another block in its place. A `var()` that points at any other variable is a problem
      that says to write the colour out: nothing holds such a variable to one value (another rule may set
      it, and this check would not know).
    - `--brand` written as a `var()` is never read, whatever it points at: the Primary is one colour for
      both themes, and a `var()` shows each theme's own value of the variable it points at (`--brand:
      var(--accent)` is the light Accent on a light page and the dark Accent on a dark one). A problem
      names the variable and says to write the colour out.
    - A value that is no colour this check reads is a problem that names the variable.
    - Brackets that do not pair up are refused.
    - `notes` holds what the owner should know and is no problem: a stylesheet this one brings in with
      `@import`, which was not read."""
    sheet = scan_css(text)
    css = Css()
    css.problems = [(t.block, t.variable, t.message) for t in sheet.problems]
    css.notes = list(sheet.notes)
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
    if name in sheet.spans[block]:
        return sheet.value(block, name), None
    above = sheet.unsure.get("light", {}).get(name) if block != "light" else None  # a dark block is laid over the :root block
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
        if m and key == "brand":
            css.problems.append((block, var, "It is written as var(%s): the brand colour points at another variable, which each theme may set "
                                             "differently, and the Primary is one colour for both themes. Write the colour out (`%s: #1a2b3c;`, "
                                             "with your colour)." % (m.group(1), var)))
            continue
        if m and m.group(1) not in KEY_OF_VARIABLE:
            css.problems.append((block, var, "It is written as var(%s), which points at a variable this check does not read (it reads "
                                             "the palette's own variables and no others, because nothing holds another one to one "
                                             "value). Write the colour out." % m.group(1)))
            continue
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
