"""_refusal.py: the one exception the brand-kit intake raises for input it will not use.

`code` is a short stable tag (the tests and the report read it); `str(error)` is the sentence
the owner is shown, in plain words, saying what was found and what to do about it.
"""

from __future__ import annotations


class Refusal(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class Ask(Exception):
    """Not a refusal: the intake needs the owner to decide before it goes on. The assistant asks
    the question in `str(error)`, offering `options` where there are any, and runs the intake
    again with the answer."""

    def __init__(self, code, message, options=None):
        super().__init__(message)
        self.code = code
        self.options = list(options or [])
