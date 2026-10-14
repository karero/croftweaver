#!/usr/bin/env python3
"""
brand_intake.py: check a palette and a logo that came from outside, and put them into a site.

The words that matter, so the rest reads easily:
  palette  read-only. Checks a pasted palette (or a site's BRAND.md) for contrast in both themes
           and names every failing pair and every missing row. Writes nothing. It runs at step
           2b, before the project exists, and again before the intake writes.
  install  puts the palette and the logo into a site, or stops and says why. Every check and every
           file is made before the site is touched; if the site's own tests are red afterwards,
           everything is put back.

Every check that decides something is plain Python (standard library only, 3.9 or newer); the one
small Node file that renders pictures runs later, with the site's own `sharp`. Nothing here asks a
model for judgement.

Exit status: 0 all good, 1 a check failed, 2 it cannot judge or cannot go on (something is missing,
unreadable or refused; for `palette --css`, also something in the stylesheet that it could not take as it
stands, or its two dark blocks disagree), 3 it needs the owner to decide something first.

Usage:
  python3 brand_intake.py palette BRAND.md [--css src/styles/global.css] [--json]
  python3 brand_intake.py palette -            # the palette on standard input
  python3 brand_intake.py install --site my-site [--input logo.zip --pick a.svg --mono a-mono.svg] [--dry-run]
"""

# (No `from __future__ import annotations` here, as the other files have it: on Python 3.9 that line loads a
# module, it cannot stand inside the guard below, and a Ctrl-C during it was a traceback. This file has no
# annotations. `os` and `sys` are loaded before any file is run.)
import os
import sys

STOPPED = "Stopped (Ctrl-C). Nothing was written."
_OUTCOME = []   # the run's exit status, from the moment main hands its report over to be said (see command_line)


def _stopped(argv):
    """The one line of a stop before anything was written: as JSON where the run was asked for JSON. (Written
    out by hand: the stop may have come while `json` was being loaded.)"""
    return '{"status": "stopped", "exit": 2, "message": "%s"}' % STOPPED if "--json" in argv else STOPPED


def _say(text):
    """Print what the command has to say (its report, or the one line of an early stop) and hand it over
    at once. Nothing that goes wrong with standard output changes how the command ends: a reader that has
    gone (`... | head`, a terminal that closed), an output that was closed (`>&-`: Python then has no
    sys.stdout at all), one that cannot be written to. The run has its outcome by then and ends with that
    status. Standard output is pointed at the null device in that case, so that Python does not complain
    about the same stream once more when it closes it.

    What this does not answer: a terminal empties its output when the interrupt key is typed, so a Ctrl-C
    typed while the report is handed to a terminal can make the terminal discard what it has not shown
    yet. The site and the exit status are right all the same, and `install --dry-run` shows the state
    again. Nothing here changes a terminal's settings to prevent that: the terminal is the owner's, and a
    run that is killed half way would leave it changed."""
    try:
        print(text)
        sys.stdout.flush()
    except (OSError, ValueError, AttributeError):
        try:
            null = os.open(os.devnull, os.O_WRONLY)
            try:
                os.dup2(null, sys.stdout.fileno())
            finally:
                os.close(null)
        except (OSError, ValueError, AttributeError):
            pass


def _leave(code):
    """End the process now, with this status. Python puts every signal back to what it does by default while
    it shuts down, the ones an install watches too: a SIGTERM or a Ctrl-C that arrived in that moment ended
    the process with the signal's status, after a report that said `done` (or `stopped`, or anything else)
    with a status of its own. So nothing is left between the report and the end that a signal could change:
    both streams are handed over, and the process ends without Python's shutting down. Nothing else waits
    to be cleared up: a run removes its temporary folder and files itself."""
    try:
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
            except (OSError, ValueError, AttributeError):
                pass
    finally:
        os._exit(code)


def _stop_early(argv):
    """The end of a run that Ctrl-C stopped before anything was written: its one line, and status 2. Ctrl-C
    is ignored first, so that a second press can neither cut the line short nor end the process another
    way. A press that comes before it is ignored raises KeyboardInterrupt once more: both callers call
    this in a loop that takes that, until this has ended the process."""
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    _say(_stopped(argv))
    _leave(2)


try:
    # Under the same guard as main() (see command_line): loading these takes a moment at the start of every run,
    # and a Ctrl-C in that moment is a stop before anything was written, not a traceback.
    import argparse
    import json

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    import _colour  # noqa: E402
    import _install  # noqa: E402
    import _palette  # noqa: E402
    from _refusal import Ask, Refusal  # noqa: E402
except KeyboardInterrupt:
    if __name__ != "__main__":
        raise
    while True:   # (see _stop_early: it ends the process)
        try:
            _stop_early(sys.argv[1:])
        except KeyboardInterrupt:
            pass

MAX_TEXT = 1024 * 1024


def _read_text(path):
    if path == "-":
        data = sys.stdin.buffer.read(MAX_TEXT + 1)
    else:
        with open(path, "rb") as f:
            data = f.read(MAX_TEXT + 1)
    if len(data) > MAX_TEXT:
        raise Refusal("too-large", "%s is larger than %d KB, far more than a palette needs." % (path, MAX_TEXT // 1024))
    return data.decode("utf-8", "replace")


# What the install does with a palette that gives no Primary (_install.py says so in its report): said by the check
# too, so that it is no surprise there.
NO_PRIMARY = "the palette gives no Primary, so the install uses the light theme's Accent as the theme colour"


def _theme_name(theme):
    return {"light": "Light theme", "dark": "Dark theme", "brand": "Brand table", "?": "No theme heading"}.get(theme, theme)


def cmd_palette(args, out):
    try:
        text = _read_text(args.file)
        palette = _palette.parse_tables(text)
        css = _palette.read_css(_read_text(args.css)) if args.css else None
    except (OSError, Refusal) as e:
        msg = str(e) if isinstance(e, Refusal) else "%s: %s" % (getattr(e, "filename", args.file), e.strerror or e)
        if args.json:
            out.append(json.dumps({"status": "unreadable", "exit": 2, "message": msg}, ensure_ascii=True))
        else:
            out.append("Cannot check the palette: %s" % msg)
            out.append("Nothing was written.")
        return 2

    pairs = _palette.matrix(palette)
    bad = [p for p in pairs if not p.ok]
    missing = palette.missing()
    problems = palette.problems
    drift = _palette.drift(palette, css) if css else []
    disagree = _palette.dark_blocks_disagree(css) if css else []
    proposed = sorted(palette.proposed)
    unread = css.problems if css else []  # what the stylesheet holds and this check could not take as it stands
    no_primary = not palette.brand and "accent" in palette.light
    notes = ([NO_PRIMARY] if no_primary else []) + (css.notes if css else [])  # said, and no reason for another exit status

    if bad:
        status, code = "fail", 1
    elif missing or problems or unread or disagree:  # (two dark blocks that disagree are a stylesheet that cannot be taken as it stands)
        status, code = "incomplete", 2
    elif proposed:
        status, code = "needs-confirmation", 3
    else:
        status, code = "pass", 0

    if args.json:
        out.append(json.dumps({
            "status": status,
            "exit": code,
            "pairs": [{"theme": p.theme, "fg": p.fg, "bg": p.bg, "fg_hex": p.fg_hex, "bg_hex": p.bg_hex,
                       "ratio": p.ratio, "need": p.need, "ok": p.ok, "note": p.note} for p in pairs],
            # every value as it was read, the ones no pair shows too (Primary, Hairline)
            "values": {"brand": palette.theme("brand"), "light": palette.light, "dark": palette.dark},
            "form": "" if palette.rows_found else _palette.FORM,
            "missing": [{"theme": t, "row": k, "label": _palette.LABEL[k]} for t, k in missing],
            "problems": [{"theme": t, "row": k, "code": c, "message": m} for t, k, c, m in problems],
            "proposed": [{"theme": t, "row": k, "hex": palette.theme(t)[k]} for t, k in proposed],
            "drift": [{"theme": t, "row": k, "document": d, "stylesheet": c} for t, k, d, c in drift],
            "dark_blocks_disagree": [{"row": k, "dark_block": a, "media_block": b} for k, a, b in disagree],
            "stylesheet_problems": [{"block": b, "variable": v, "message": m} for b, v, m in unread],
            "notes": notes,
        }, ensure_ascii=True))
        return code

    out.append("Palette check: every text colour on every background colour, in both themes, at WCAG AA "
               "(%s to 1 for text)." % _colour.shown(_palette.NEED_TEXT))
    for p in bad:
        out.append(_palette.describe(p))
    out.append("%d of %d pairs pass." % (len(pairs) - len(bad), len(pairs)) if pairs else "No pair could be checked.")
    if not palette.rows_found:
        out.append("No row of a palette was found where this check looks for one. %s" % _palette.FORM)
    elif missing:
        by = {}
        for t, k in missing:
            by.setdefault(t, []).append(_palette.LABEL[k])
        # "not filled in" is said only where nothing else is wrong: a value that was not read shows its row here too
        out.append("These rows have no value that this check could use:" if problems else "These rows are not filled in:")
        for t in _palette.THEMES:
            if t in by:
                out.append("  %s: %s" % (_theme_name(t), ", ".join(by[t])))
        if problems:
            out.append("Some of them may be filled in and only not read. First mend what is named below (\"Not read:\", \"Could not read a "
                       "value:\") and check again: a value that was not read also shows its row as missing here. Rows that are still "
                       "listed after that are the ones to fill in.")
        else:
            out.append("The assistant can propose values for them; you confirm or change each one before anything is used.")
    for problem in problems:  # said of one row's value, or of a whole table or line
        out.append(("Could not read a value: %s" if _palette.is_about_a_value(problem) else "Not read: %s") % problem[3])
    if no_primary:
        out.append("Note: %s." % NO_PRIMARY)
    if proposed:
        out.append("Proposed values, waiting for your confirmation (a proposal is shown, never written until you agree):")
        for t, k in proposed:
            line = ["  %s, %s: %s" % (_theme_name(t), _palette.LABEL[k], palette.theme(t)[k])]
            ratios = [(bg, _colour.ratio(palette.theme(t)[k], palette.theme(t)[bg])) for bg in _palette.BACKGROUNDS
                      if bg in palette.theme(t)] if k in _palette.TEXT else []
            if ratios:
                line.append("(" + ", ".join("%s on %s" % (_colour.shown(r), _palette.LABEL[bg]) for bg, r in ratios) + ")")
            if _palette.fixed_accent_note(palette, t, k):
                line.append("(%s)" % _palette.fixed_accent_note(palette, t, k))
            out.append(" ".join(line))
        out.append("Ask the owner to confirm or change them, then check again without the (proposed) marks.")
    if drift:
        out.append("BRAND.md and the stylesheet disagree (the stylesheet is what the site uses):")
        for t, k, d, c in drift:
            has = "the stylesheet has %s" % c if c != _palette.MISSING else "%s of the stylesheet does not set it" % _palette.BLOCK["dark" if t == "dark" else "light"]
            out.append("  %s, %s: BRAND.md says %s, %s" % (_theme_name(t), _palette.LABEL[k], d, has))
    if disagree:
        out.append("The two dark blocks in the stylesheet disagree (they must carry the same values):")
        for k, a, b in disagree:
            sides = ["%s in %s" % (v, _palette.BLOCK[block]) if v != _palette.MISSING else "not set in %s" % _palette.BLOCK[block]
                     for v, block in ((a, "dark"), (b, "dark_media"))]
            out.append("  %s: %s" % (_palette.LABEL[k], ", ".join(sides)))
    for block, variable, m in unread:
        out.append("Could not read the stylesheet: %s" % (m if variable is None else "%s in %s: %s" % (variable, _palette.BLOCK[block], m)))
    for note in css.notes if css else []:  # (a stylesheet it brings in, which was not read)
        out.append("Note: %s" % note)
    out.append("This check only reads files: nothing was written.")
    return code


def cmd_install(args, out):
    lines = []
    code, status, data = _install.install(args, lines)
    if args.json:
        data = dict(data, status=status, exit=code, report=lines)
        out.append(json.dumps(data, ensure_ascii=True))
    else:
        out.extend(lines)
    return code


def main(argv=None):
    del _OUTCOME[:]   # (a caller may run main more than once)
    if sys.stderr is None:   # closed (`2>&-`): argparse on Python 3.9 writes its word on a bad argument there without looking
        sys.stderr = open(os.devnull, "w")
    # (allow_abbrev: `--js` is not `--json`. An early stop looks for the word itself among the arguments.)
    ap = argparse.ArgumentParser(prog="brand_intake.py", description=__doc__.split("\n\n")[0], allow_abbrev=False)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("palette", allow_abbrev=False, help="check a palette for contrast in both themes (read-only)")
    p.add_argument("file", help="BRAND.md or a pasted palette; - for standard input")
    p.add_argument("--css", help="the site's global.css, to compare it with the palette")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    i = sub.add_parser("install", allow_abbrev=False, help="put a palette and a logo into a site (checks everything first; puts everything back if the site's tests go red)")
    i.add_argument("--site", required=True, help="the site's folder")
    i.add_argument("--palette", help="the palette to apply (default: BRAND.md, or docs/BRAND.md, in the site)")
    i.add_argument("--input", help="the logo: an SVG file, a zip of SVG files, or a folder holding one of them")
    i.add_argument("--pick", help="which file of a zip is the mark")
    i.add_argument("--mono", help="which file of the zip is the mark's one-colour version")
    i.add_argument("--with-colours", action="store_true", help="stop unless a complete palette is applied; with --input or --with-logo, also the answer that the palette should go in together with the logo")
    i.add_argument("--keep-colours", action="store_true", help="leave the site's colours as they are, although BRAND.md holds a palette: the logo is installed, or its icons drawn again, against the colours the site has")
    i.add_argument("--with-logo", action="store_true", help="stop unless a logo is applied; without --input, draw the icons again from the logo already installed")
    i.add_argument("--accept-colours", action="store_true", help="use the mark's colours even where the palette does not hold them")
    i.add_argument("--accept-low-contrast", default="", help="light, dark or both: use the mark although it falls under 3 to 1 on that theme's background")
    i.add_argument("--replace-icons", action="store_true", help="replace icon files that are already in the site and are not the scaffold's placeholders")
    i.add_argument("--test-command", help="what to run to see that the site is still green (default: npm run build && npm test)")
    i.add_argument("--dry-run", action="store_true", help="check everything and say what would be written; write nothing")
    i.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    out = []
    try:
        code = {"palette": cmd_palette, "install": cmd_install}[args.command](args, out)
    except Ask as a:
        out.append(str(a))
        out.extend("  - %s" % o for o in a.shown)   # as a person can read them; an answer is matched against a.options
        code = 3
    except Refusal as r:
        out.append(str(r))
        code = 2
    report = "\n".join(out)
    import signal
    import threading
    came = []
    main = threading.current_thread() is threading.main_thread()   # (only the main thread may set a handler: elsewhere the report is said unheld)
    was = signal.signal(signal.SIGINT, lambda _signum, frame: came.append(frame)) if main else None   # a Ctrl-C until the report's end is held, then raised if it would have been (see command_line)
    _OUTCOME[:] = [code]
    _say(report)
    if main:
        signal.signal(signal.SIGINT, was)
    if came and was is signal.default_int_handler:
        raise KeyboardInterrupt
    if came and callable(was):   # a program that runs main() with its own handler gets the press it would have had
        was(signal.SIGINT, came[0])
    return code


def command_line(argv=None):
    """What `python3 brand_intake.py ...` runs: main(), and then the end of the process, at once, with
    main's status (see _leave): also where main ends through argparse (`--help`, an argument it does not
    take), which leaves by sys.exit. A Ctrl-C before `install` began to watch for it, or during `palette`
    before its report is said, is said in one line (one JSON object where `--json` was asked for): neither
    had written anything. From the moment main keeps the run's status (_OUTCOME), a Ctrl-C changes nothing:
    main holds it until the report is said whole, and the command ends with that status and says nothing
    after the report, so a check that passed does not end with the stop's line and status 2.
    What argparse has to say it prints itself, not through _say: the limit stated there for a terminal
    holds for those lines too.

    What no line of this file can answer: a Ctrl-C while Python itself is still starting ends the process
    before this file is reached, or at this file's first instruction, and then with Python's own traceback,
    which names this file (13 of 1,440 runs that were stopped in their first moments at a terminal). And
    until `install` watches the signals (the tool's first moments, while its modules are loaded and the
    arguments read), a SIGTERM, or a SIGHUP from a terminal that was closed, ends the process with the
    signal's own status and no line.
    Nothing is written by then."""
    try:
        try:
            code = main(argv)
        except SystemExit as e:   # argparse has printed what it had to say
            code = e.code if type(e.code) is int else 0 if e.code is None else 1
        _leave(code)   # (inside: a Ctrl-C before the process has ended is taken below, with the status kept)
    except KeyboardInterrupt:
        while True:   # (see _stop_early: it ends the process)
            try:
                if _OUTCOME:   # the report is said (main held the Ctrl-C until it was): it stands, with its status
                    import signal
                    signal.signal(signal.SIGINT, signal.SIG_IGN)
                    _leave(_OUTCOME[0])
                _stop_early(sys.argv[1:] if argv is None else argv)
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    command_line()
