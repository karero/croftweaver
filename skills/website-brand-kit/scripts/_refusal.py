"""_refusal.py: the one exception the brand-kit intake raises for input it will not use.

`code` is a short stable tag (the tests and the report read it); `str(error)` is the sentence
the owner is shown, in plain words, saying what was found and what to do about it. The sentence
often quotes what the file held, so it is made here, in one place, of characters a person can
see: every other one is spelled out as its code point.
"""

from __future__ import annotations

import re
import unicodedata

# What Unicode files as a control, a format mark (the ones that turn the reading order round, the
# zero-width ones, the invisible "tag" letters), a private or unassigned character, half a pair, a
# line or paragraph break, or a space (every kind but the plain one): none of it can be seen.
_UNSEEN = ("Cc", "Cf", "Co", "Cn", "Cs", "Zl", "Zp", "Zs")
# Drawn as nothing too, though Unicode files them as marks, letters or symbols: the variation
# selectors (256 of them: enough to spell out a hidden text), the blank fillers, the empty braille cell.
_UNSEEN_TOO = re.compile("[\u034f\u115f\u1160\u17b4\u17b5\u180b-\u180f\u2800\u3164\ufe00-\ufe0f\uffa0\U000e0100-\U000e01ef]")


def unseen(char):
    """Is this one character something a reader cannot see? (The plain space is seen: it is a gap.)"""
    return char != " " and (unicodedata.category(char) in _UNSEEN or bool(_UNSEEN_TOO.match(char)))


def spelled(text):
    """`text` with every character that cannot be seen spelled out (`\\u200b`, `\\xa0`), so that
    what is shown is what is there. A line break stays one: a message may have several lines."""
    if text.isascii() and text.isprintable():
        return text
    return "".join(c.encode("unicode_escape").decode("ascii") if c != "\n" and unseen(c) else c for c in text)


class Refusal(Exception):
    def __init__(self, code, message):
        super().__init__(spelled(str(message)))
        self.code = code


class Ask(Exception):
    """Not a refusal: the intake needs the owner to decide before it goes on. The assistant asks
    the question in `str(error)`, offering `options` where there are any, and runs the intake
    again with the answer."""

    def __init__(self, code, message, options=None):
        super().__init__(spelled(str(message)))
        self.code = code
        self.options = list(options or [])
