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
stands), 3 it needs the owner to decide something first.

Usage:
  python3 brand_intake.py palette BRAND.md [--css src/styles/global.css] [--json]
  python3 brand_intake.py palette -            # the palette on standard input
  python3 brand_intake.py install --site my-site [--input logo.zip --pick a.svg --mono a-mono.svg] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _colour  # noqa: E402
import _install  # noqa: E402
import _palette  # noqa: E402
from _refusal import Ask, Refusal  # noqa: E402

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

    if bad:
        status, code = "fail", 1
    elif missing or problems or unread:
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
            "notes": [NO_PRIMARY] if no_primary else [],
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
    ap = argparse.ArgumentParser(prog="brand_intake.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("palette", help="check a palette for contrast in both themes (read-only)")
    p.add_argument("file", help="BRAND.md or a pasted palette; - for standard input")
    p.add_argument("--css", help="the site's global.css, to compare it with the palette")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    i = sub.add_parser("install", help="put a palette and a logo into a site (checks everything first; puts everything back if the site's tests go red)")
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
        out.extend("  - %s" % o for o in a.options)
        code = 3
    except Refusal as r:
        out.append(str(r))
        code = 2
    print("\n".join(out))
    return code


if __name__ == "__main__":
    sys.exit(main())
