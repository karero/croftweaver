"""_install.py: put a palette and a logo into a site, or stop and say why.

Order matters, and it is the point of this file. Everything that can be checked is checked, and every
file is built in memory or in a temporary folder, BEFORE the site is touched: the palette's contrast, the
mark's safety and colours, the sharp preflight, the seven icons, each edit. Where the owner must decide
something (a colour outside the palette, a mark that vanishes on a theme, an icon that is not a
placeholder), it asks and writes nothing. Only then does it write, through a journal. If the site's own
tests are red afterwards, the journal puts every file back and the report names the failing check.

Two parts, each from her own material or the assistant's: the palette (BRAND.md, the stylesheet, the
manifest's colours, the share cards' colours) and the logo (the seven icon files, COMPANY.logo, the share
cards' emblem). A part she has no material for stays as the site has it. Standard library only.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import tempfile

import _colour
import _icons
import _input
import _palette
import _render
import _site
import _svg
import _zipin
from _refusal import Ask, Refusal

DEFAULT_TEST_COMMAND = "npm run build && npm test"
TEST_TIMEOUT = 30 * 60
CARDS_TIMEOUT = 5 * 60
MAX_TEXT = 1024 * 1024
CARDS = "public/images/og"
HANDOFF = "brand-handoff"
MASTER = "public/favicon.svg"
PILLOW_MISSING = "Pillow, the image library the generator draws with, is not installed"


class Stop(Exception):
    """Not an error in the program: the run ends here with this exit status and these lines."""

    def __init__(self, code, lines, status):
        super().__init__("\n".join(lines))
        self.code, self.lines, self.status = code, lines, status


class Interrupted(BaseException):
    """The run was told to stop from outside (SIGTERM, SIGHUP). A BaseException, as KeyboardInterrupt
    is, so that nothing between the signal and the rollback takes it for an ordinary error."""


def _theme_label(theme):
    return {"light": "the light theme", "dark": "the dark theme"}.get(theme, theme)


def palette_from_css(css):
    p = _palette.Palette()
    p.light, p.dark, p.brand = dict(css.light), dict(css.dark), css.brand
    return p


def _find_brand_md(site):
    for rel in ("BRAND.md", "docs/BRAND.md"):
        if os.path.isfile(os.path.join(site, *rel.split("/"))):
            return os.path.join(site, *rel.split("/"))
    return None


def _read_text(path, rel=None):
    """The file's text, never a part of it. `rel` names a file of the site that the run edits and writes
    back: that one must also be read exactly, so one that is not UTF-8 is refused by name instead of
    having its letters changed in passing."""
    with open(path, "rb") as f:
        data = f.read(MAX_TEXT + 1)
    if len(data) > MAX_TEXT:
        raise Refusal("too-large", "%s is larger than %d KB, more than this tool reads of one file, so it was not used." % (rel or path, MAX_TEXT // 1024))
    if rel is None:
        return data.decode("utf-8", "replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refusal("not-utf8", "%s is not saved as UTF-8: a letter in it (an ü or an é, say) is stored in another encoding, and writing the file back would "
                                  "damage it. Save the file as UTF-8, then run this again." % rel) from None


def read_input(path):
    """(bytes, the file's own path) of what the owner handed over. A folder holding one package is that
    package; several are asked about; none is said so. Nothing else is looked at: this never searches."""
    if os.path.isdir(path):
        names = sorted(n for n in os.listdir(path) if n.lower().endswith((".zip", ".svg", ".html", ".htm")) and os.path.isfile(os.path.join(path, n)))
        if not names:
            raise Refusal("no-input", "Nothing arrived at %s: that folder holds no .zip, .svg or .html file. Ask for the path again; this tool does not "
                                      "search other folders (your Downloads, say) on its own." % path)
        if len(names) > 1:
            raise Ask("which-package", "The folder %s holds %d files that could be the package. Which one is it? (Give its full path as the input.)" % (path, len(names)),
                      [os.path.join(path, n) for n in names])
        path = os.path.join(path, names[0])
    if not os.path.isfile(path):
        raise Refusal("no-input", "Nothing arrived at that path (%s). Ask for the path again; this tool does not search other folders (your Downloads, "
                                  "say) on its own." % path)
    with open(path, "rb") as f:
        data = f.read(_zipin.MAX_ZIP_BYTES + 1)
    if len(data) > _zipin.MAX_ZIP_BYTES:
        raise Refusal("too-large", "The file at %s is larger than %d MB, far more than a logo needs." % (path, _zipin.MAX_ZIP_BYTES // 1048576))
    return data, path


def _safe_name(path):
    name = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(path))
    return ("_" + name if name.startswith(".") else name) or "package"


def _accepted(value):
    got = {t.strip().lower() for t in (value or "").replace(";", ",").split(",") if t.strip()}
    if "both" in got or "all" in got:
        got |= {"light", "dark"}
    unknown = got - {"light", "dark", "both", "all"}
    if unknown:
        raise Refusal("bad-argument", "--accept-low-contrast takes light, dark or both, not %s." % ", ".join(sorted(unknown)))
    return got


def _stop(p):
    """Stop a command and everything it started (a preview server on the site's port, say), and wait
    until the command itself is gone."""
    try:
        if os.name == "posix":
            os.killpg(p.pid, signal.SIGKILL)  # started in a group of its own, whose number is its own
        else:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
    except OSError:
        pass  # already gone
    try:
        p.kill()
    except OSError:
        pass
    try:
        return p.communicate(timeout=10)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return "", ""  # something that left the group still holds its output open: not waited for


def _run(command, cwd, timeout, shell=False, env=None, encoding=None):
    """Run a command and wait for it: (its exit status, what it printed, its error output). The status
    is None when it took longer than `timeout` seconds. However the wait ends early (the timeout, Ctrl-C,
    a signal), the command is stopped first with everything it started, so that none of it is still
    running when the site's files are put back."""
    group = {"start_new_session": True} if os.name == "posix" else {}
    p = subprocess.Popen(command, shell=shell, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding=encoding, errors="replace", **group)
    try:
        out, err = p.communicate(timeout=timeout)
        return p.returncode, out, err
    except subprocess.TimeoutExpired:
        out, err = _stop(p)
        return None, out or "", err or ""
    except BaseException:
        _stop(p)
        raise


def regenerate_cards(site):
    """`npm run og` without npm: the same launcher, which finds python3, py or python. Returns (ok, a
    sentence saying why not)."""
    node = shutil.which("node")
    if not node:
        return False, "Node is not available"
    # the generator prints an arrow and a multiplication sign, which the encoding a pipe gets by default
    # (cp1252 on Windows) may not hold: it is told to write UTF-8, and its output is read as UTF-8
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        code, out, err = _run([node, os.path.join(site, "scripts", "run_og.mjs")], site, CARDS_TIMEOUT, env=env, encoding="utf-8")
    except OSError as e:
        return False, "the generator could not be started: %s" % (e.strerror or e)
    if code is None:
        return False, "the generator took more than %d minutes and was stopped" % (CARDS_TIMEOUT // 60)
    if code == 0:
        return True, ""
    if "Pillow is required" in err + out or "No module named 'PIL'" in err + out:
        return False, PILLOW_MISSING
    lines = [l.strip() for l in (err + "\n" + out).splitlines() if l.strip()]
    return False, (lines[-1] if lines else "it stopped without saying why")[:200]


def run_tests(site, command):
    """(green, the tail of its output)."""
    code, out, err = _run(command, site, TEST_TIMEOUT, shell=True)
    if code is None:
        return False, "the tests took more than %d minutes and were stopped" % (TEST_TIMEOUT // 60)
    return code == 0, (out + "\n" + err)


def _watch_signals():
    """From here on a SIGTERM or a SIGHUP raises Interrupted inside the run, where the rollback catches
    it, instead of ending the process with the site half installed. Returns what handled them before."""
    def stop(signum, _frame):
        raise Interrupted(signum)
    before = {}
    for name in ("SIGTERM", "SIGHUP"):  # Windows has no SIGHUP
        sig = getattr(signal, name, None)
        try:
            if sig is not None:
                before[sig] = signal.signal(sig, stop) or signal.SIG_DFL
        except (ValueError, OSError):
            pass  # not the main thread, where no signal arrives anyway
    return before


def _set_signals(handlers):
    for sig, handler in handlers.items():
        try:
            signal.signal(sig, handler)
        except (ValueError, OSError):
            pass


def failing_checks(output):
    """The names of what failed, from Playwright's list reporter ("  1) [chromium] › tests/a.spec.ts:8:5 › name")."""
    names = []
    for line in output.splitlines():
        m = re.match(r"^\s*\d+\)\s+\[[^\]]+\]\s+›\s+(.*?)(?:\s+─+)?\s*$", line)
        if m:
            names.append(m.group(1))
    if names:
        return names[:6]
    tail = [l.strip() for l in output.splitlines() if l.strip()]
    return tail[-6:]


class Plan(object):
    """What the run has decided, with nothing yet written."""

    def __init__(self):
        self.texts = {}       # relative path -> (old text, new text)
        self.files = {}       # relative path -> bytes (icons)
        self.notes = []
        self.asks = []
        self.placeholders = []
        self.copy = None      # (relative path in brand-handoff, bytes) of the package, or None
        self.preview = None   # bytes of the preview sheet, or None
        self.changed_icons = []
        self.background = self.version = None  # what the app icons sit on, and which version of the mark they show


def _aftermath(data):
    """What is true of the site's files after a run that stopped, as lines for the report."""
    left = data.get("not_restored")
    if left:
        return (["Not everything could be put back. These are NOT as they were before this run; look at each of them:"]
                + ["  %s (%s)" % (l["file"], l["why"]) for l in left] + ["Everything else it had written was put back."])
    return ["Everything it had written was put back." if data.get("rolled_back") else "Nothing was written."]


def install(a, out):
    """Everything. `a` has: site, palette, input, pick, mono, with_colours, keep_colours, with_logo,
    accept_colours, accept_low_contrast, replace_icons, test_command, dry_run. Returns (exit code, status,
    data) and appends the report's lines to `out`. Raises nothing it can say in words: those are Stops."""
    site = os.path.abspath(a.site)
    data = {"written": [], "notes": [], "cards": None, "tests": None}
    try:
        return _install(a, site, out, data)
    except Stop as s:
        out.extend(s.lines)
        data.update({"message": "\n".join(s.lines)})
        return s.code, s.status, data
    except Ask as k:
        out.append("I need your decision before I go on. Nothing was written.")
        out.append("- " + str(k))
        out.extend("    * " + o for o in k.options)
        out.extend("Note: " + n for n in data["notes"])
        data["asks"] = [{"code": k.code, "question": str(k), "options": k.options}]
        return 3, "needs-decision", data
    except Refusal as r:
        out.append(str(r))
        out.extend(_aftermath(data))
        data.update({"code": r.code, "message": str(r)})
        return 2, "rollback-incomplete" if data.get("not_restored") else "refused", data
    except OSError as e:
        # a file or folder that could not be read or written, or a program that could not be started
        message = "The run had to stop: %s." % ("%s could not be read or written (%s)" % (e.filename, e.strerror or e) if e.filename else (e.strerror or e))
        out.append(message)
        out.extend(_aftermath(data))
        data.update({"code": "os-error", "message": message})
        return 2, "rollback-incomplete" if data.get("not_restored") else "refused", data


def _differences(css, pal):
    """Where a stylesheet, as _palette.read_css read it, does not hold the palette: [(the row and its
    place, what the stylesheet has there or None, what the palette has)]. The Primary and all three
    blocks are compared; a dark row that both dark blocks have alike is named once."""
    out = []
    if pal.brand and css.brand != pal.brand:
        out.append((_palette.LABEL["brand"], css.brand, pal.brand))
    for theme, block, where in (("light", css.light, "light theme"), ("dark", css.dark, "dark theme"),
                                ("dark", css.dark_media, "dark theme for visitors without JavaScript")):
        for k in _palette.KEYS:
            new = pal.theme(theme).get(k)
            if new is None or block.get(k) == new or (block is css.dark_media and css.dark.get(k) == block.get(k)):
                continue
            out.append(("%s, %s" % (_palette.LABEL[k], where), block.get(k), new))
    return out


def _css_problems(css):
    """What _palette.read_css could not find or could not read in a stylesheet, as sentences."""
    return [m if variable is None else "%s in %s: %s" % (variable, _palette.BLOCK[block], m) for block, variable, m in css.problems]


def _install(a, site, out, data):
    # --- what she asked for, before anything is read ---------------------------------------
    accepted = _accepted(a.accept_low_contrast)
    if not a.input and (a.pick or a.mono):
        flags = " and ".join(f for f, v in (("--pick", a.pick), ("--mono", a.mono)) if v)
        raise Refusal("bad-argument", "%s can only be used with a package to choose from, and none was given. Give the logo with --input, or leave %s out." % (flags, flags))
    if a.with_colours and a.keep_colours:
        raise Refusal("bad-argument", "--with-colours and --keep-colours ask for opposite things (apply the palette; leave the site's colours as they are). Give one of them.")
    missing = _site.missing_files(site)
    if missing:
        raise Refusal("site-layout", "%s does not look like a site made from the starter: it lacks %s." % (site, ", ".join(missing)))
    css_text = _read_text(os.path.join(site, "src", "styles", "global.css"), "src/styles/global.css")
    css = _palette.read_css(css_text)

    # --- the palette, from BRAND.md (or the file she named) ---------------------------------
    notes = data["notes"]
    parsed, state = None, "none"
    brand_path = a.palette or _find_brand_md(site)
    if a.palette and not os.path.isfile(a.palette):
        raise Refusal("no-input", "There is no palette file at %s." % a.palette)
    if brand_path:
        parsed = _palette.parse_tables(_read_text(brand_path))
        has_any = bool(parsed.light or parsed.dark or parsed.brand)
        state = "none" if not has_any else ("complete" if not parsed.missing() and not parsed.problems else "partial")
    want_colours = state == "complete" and not a.keep_colours
    if state == "complete" and a.keep_colours:
        notes.append("the palette in %s was not applied (--keep-colours): the site keeps the colours it has" % os.path.basename(brand_path))
    if a.with_colours and not want_colours:
        if state == "partial":
            by = {}
            for t, k in parsed.missing():
                by.setdefault(t, []).append(_palette.LABEL[k])
            rows = "; ".join("%s: %s" % (_theme_label(t), ", ".join(v)) for t, v in by.items())
            raise Refusal("palette-incomplete", "The palette in %s is not complete (%s%s). Fill those rows (the assistant can propose values for you to confirm), then run this again."
                          % (os.path.basename(brand_path), rows or "unreadable values", "; " + "; ".join(m for _t, _k, _c, m in parsed.problems) if parsed.problems else ""))
        raise Refusal("palette-missing", "There are no colours to apply: %s." % ("BRAND.md has no filled-in colour rows" if brand_path else "no BRAND.md was found next to the site"))
    if state == "partial" and not want_colours:
        by = [_palette.LABEL[k] for _t, k in parsed.missing()]
        notes.append("the colours were not changed: %s does not hold a complete palette (rows not filled in: %s)" % (os.path.basename(brand_path), ", ".join(sorted(set(by)))))
    changes = []
    if want_colours:
        pairs = _palette.matrix(parsed)
        bad = [p for p in pairs if not p.ok]
        if bad:
            lines = [_palette.describe(p) for p in bad] + ["%d of %d pairs pass. Nothing was written." % (len(pairs) - len(bad), len(pairs))]
            raise Stop(1, lines, "contrast-failed")
        if parsed.proposed:
            names = ", ".join(_palette.LABEL[k] if t == "brand" else "%s (%s)" % (_palette.LABEL[k], t) for t, k in sorted(parsed.proposed))
            raise Ask("confirm-proposals", "These colours are still proposals, marked (proposed): %s. Ask the owner to confirm or change each one, take the marks out, then run this again." % names)
        # what the palette changes in the stylesheet, as she reads it: said in every report, and asked
        # about first when she came with a logo and did not say the colours should change too
        changes = ["%s: %s becomes %s" % (where, old or "a value this tool cannot read", new) for where, old, new in _differences(css, parsed)]
        if a.input and changes and not a.with_colours:
            raise Ask("colours-too", "%s holds a palette that is not what the site shows now, so this run would also change the colours listed here, in "
                      "src/styles/global.css. Should it? Run this again with --with-colours to apply the palette together with the logo, or with "
                      "--keep-colours to install the logo and leave the site's colours as they are." % os.path.basename(brand_path), changes)
    pal = parsed if want_colours else palette_from_css(css)
    primary = pal.brand or pal.light.get("accent")
    if want_colours and not pal.brand:
        notes.append("the palette has no Primary row, so the accent colour is used as the theme colour")

    # --- the logo, from her input or the installed master ---------------------------------
    master_bytes = None
    try:
        with open(os.path.join(site, *MASTER.split("/")), "rb") as f:
            master_bytes = f.read()
    except OSError:
        pass
    if master_bytes is not None and _site.is_scaffold_default(MASTER, master_bytes):
        master_bytes = None
    # Without a file from her, the installed master is drawn again only when she asks for it (--with-logo),
    # or when the colours change and the master is one this tool wrote: a cleaned SVG comes out of the
    # cleaning as it went in. Any other favicon.svg is a file she never handed over, and a run about
    # colours neither judges it nor stops over it.
    redraw = master_bytes is not None and a.with_logo
    if master_bytes is not None and want_colours and not a.input and not a.with_logo:
        try:
            redraw = _svg.clean_svg(master_bytes, current=primary).text.encode("utf-8") == master_bytes
        except Refusal:
            redraw = False
        if not redraw:
            notes.append("the icons were left as they are: %s is not a file this tool wrote, so the app icons were not drawn again on the new background. "
                         "To make them again from that file, run this again with --with-logo; to install a logo, give it with --input" % MASTER)
    want_logo = bool(a.input) or redraw
    if a.with_logo and not want_logo:
        raise Refusal("logo-missing", "There is no logo to apply: no file was given, and the site has no logo of its own installed yet (%s is the scaffold's placeholder or missing)." % MASTER)
    if not want_colours and not want_logo:
        raise Refusal("nothing-to-do", "There is nothing to do: no complete palette was found%s, and no logo file was given."
                      % (" in " + os.path.basename(brand_path) if brand_path else ""))

    plan = Plan()
    clean = mono_clean = icons = None
    src_name = src_bytes = None
    workdir = tempfile.mkdtemp(prefix="brand-kit-")
    try:
        if want_logo:
            if a.input:
                raw, src_path = read_input(a.input)
                mk = _input.mark(_input.load(raw), pick=a.pick, mono=a.mono)
                source = "html-svg" if mk.source == "html" else "svg"
                clean = _svg.clean_svg(mk.colour, source=source, current=primary)
                mono_clean = _svg.clean_svg(mk.mono, source=source, current=primary) if mk.mono else None
                src_name, src_bytes = _safe_name(src_path), raw
                if os.path.realpath(src_path).startswith(os.path.realpath(os.path.join(site, HANDOFF)) + os.sep):
                    src_name = None  # already kept there
                notes.extend(clean.notes)
            else:
                clean = _svg.clean_svg(master_bytes, current=primary)
            renderer = _render.Renderer(site)
            renderer.preflight()
            icons = _icons.build(clean, mono_clean, pal, renderer, workdir)
            notes.extend(icons.notes)
            # Two questions, two sets of colours. Every colour an installed file paints with is held against
            # the palette. Only the colour version ever stands on the page (the favicon, the logo); the
            # one-colour version sits on the app icons' own background, so its colours are not asked about there.
            report = _palette.check_mark(icons.visible, pal)
            on_page = _palette.check_mark(clean.colours, pal)
            if report.outside and not a.accept_colours:
                plan.asks.append(Ask("outside-palette", "These colours of the mark are not in the palette: %s. Nothing is recoloured without your say-so. Use the mark as it is "
                                     "(--accept-colours), or ask the tool for the mark in the palette's colours." % ", ".join(report.outside)))
            for theme, low in on_page.low.items():
                if theme not in accepted:
                    what = "; ".join("%s is %s to 1" % (c, _colour.shown(r)) for c, r in low)
                    plan.asks.append(Ask("low-contrast", "On %s the mark falls under 3 to 1 against the background (%s). %s Accept it as it is (--accept-low-contrast %s), "
                                         "or choose a different mark." % (_theme_label(theme), what,
                                         "Use its one-colour version where it sits on that background." if mono_clean is None else
                                         "The one-colour version you gave can be used where it sits on that background.", theme)))
            for rel, new in icons.files.items():
                current = _read_bytes(site, rel)
                if current is None or current == new:
                    continue
                (plan.placeholders if _site.is_scaffold_default(rel, current) else plan.changed_icons).append(rel)
            if plan.changed_icons and not a.replace_icons:
                plan.asks.append(Ask("replace-icons", "These icon files are already in the site, and are not the scaffold's placeholders: %s. Replace them (--replace-icons)?"
                                     % ", ".join(plan.changed_icons), plan.changed_icons))
            plan.files = icons.files
            plan.background, plan.version = icons.background, icons.version
            plan.preview = _icons.preview(clean.text, clean.view_box, pal, renderer, workdir)
            if src_name:
                plan.copy = (HANDOFF + "/" + _free_name(site, src_name, src_bytes), src_bytes)
        if plan.asks:
            lines = ["I need your decision before I go on. Nothing was written."]
            for k in plan.asks:
                lines.append("- " + str(k))
                lines.extend("    * " + o for o in k.options)
            lines.extend("Note: " + n for n in notes)
            data["asks"] = [{"code": k.code, "question": str(k), "options": k.options} for k in plan.asks]
            raise Stop(3, lines, "needs-decision")
        if plan.placeholders:
            notes.append("%s %s the scaffold's placeholder%s (the Astro logo), %s" % (
                " and ".join(plan.placeholders), "was" if len(plan.placeholders) == 1 else "were", "" if len(plan.placeholders) == 1 else "s",
                "which this run would replace" if a.dry_run else "now replaced"))

        # --- every edit, in memory, before anything is written ---------------------------------
        def edit(rel, fn):
            old = _read_text(os.path.join(site, *rel.split("/")), rel)
            new = fn(old)
            if new != old:
                plan.texts[rel] = (old, new)
            return old, new
        card_colours = want_colours
        if want_colours:
            try:
                _old, css_new = edit("src/styles/global.css", lambda t: _site.edit_css(t, pal))
            except Refusal as r:
                if r.code != "css-layout":
                    raise
                # why, as far as the reading of the same stylesheet can say: what it could not find or read
                # there, or that it read all three blocks, which are then written in a way the edit does not know
                why = _css_problems(css) or (["The colours themselves can be read, so one of the three blocks is written in another way than the starter "
                                              "writes it (`:root, html {` or `:ROOT {` for `:root {`, say): write it as the starter does, or set the colours by "
                                              "hand."] if len(css.found) == 3 else [])
                raise Refusal(r.code, " ".join([str(r)] + why)) from None
            # the stylesheet as it would be written, read back: an edit lands on the first block of each
            # kind, and a block further down that sets a colour again would leave the site showing the old one
            after = _palette.read_css(css_new)
            off = _differences(after, pal)
            if off:
                raise Refusal("css-layout", "src/styles/global.css would not carry the palette after the colours were set: %s. %s Take that out or set the colours "
                              "by hand, then run this again." % ("; ".join("%s would be %s, not %s" % (where, got or "unreadable", want) for where, got, want in off),
                                                               " ".join(_css_problems(after)) or "Something else in the stylesheet sets that again (a second block "
                                                               "of the same kind, say)."))
            edit("public/manifest.webmanifest", lambda t: _site.edit_manifest(t, primary, pal.light["bg"]))
            low = _site.og_low_contrast(pal)
            if low:
                card_colours = False
                notes.append("the share cards keep the colours they have. Their background runs from the dark theme's %s (%s) at the top to its %s (%s) at the "
                             "bottom, and somewhere on the way %s; text needs %s to 1. The site itself has the palette. To recolour the cards, set the colours "
                             "in the BRAND block of scripts/generate_og_cards.py by hand" % (
                                 _palette.LABEL["surface"], pal.dark["surface"], _palette.LABEL["bg"], pal.dark["bg"],
                                 " and ".join("%s %s falls to %s to 1" % (_palette.LABEL[k], h, _colour.shown(r)) for k, h, r in low), _colour.shown(_palette.NEED_TEXT)))
        config_old, _new = edit("src/config.ts", lambda t: _site.edit_config(t, primary if want_colours else None, logo=want_logo))
        logo_was = _site.company_logo(config_old) if want_logo else None
        if logo_was not in (None, "/images/logo.png"):
            notes.append("COMPANY.logo in src/config.ts pointed at %s; it now points at /images/logo.png, the picture made from this logo. The file it pointed "
                         "at is left where it is" % logo_was)
        edit("scripts/generate_og_cards.py", lambda t: _site.edit_og(t, pal if card_colours else None, logo=want_logo))
        ignore_new = None
        if plan.copy or plan.preview:
            gi_old = _read_text(os.path.join(site, ".gitignore"), ".gitignore") if os.path.isfile(os.path.join(site, ".gitignore")) else ""
            ignore_new = _site.add_ignore(gi_old)
            if ignore_new is not None:
                plan.texts[".gitignore"] = (gi_old, ignore_new)

        # --- what the run writes, and only that: a file that is already as it should be is left out ---
        writes = [(rel, new) for rel, new in plan.files.items() if _read_bytes(site, rel) != new]
        writes += [(rel, new.encode("utf-8")) for rel, (_old, new) in plan.texts.items()]
        if plan.copy and _read_bytes(site, plan.copy[0]) != plan.copy[1]:
            writes.append(plan.copy)
        if plan.preview and _read_bytes(site, HANDOFF + "/preview.png") != plan.preview:
            writes.append((HANDOFF + "/preview.png", plan.preview))
        # the last checks that can be made before the site is touched: every path, and the share cards' folder
        j = _site.Journal(site)
        for rel, _new in writes:
            j.check(rel)
        j.snapshot_dir(CARDS)
        data["changes"] = changes
        if a.dry_run:
            would = sorted(rel for rel, _new in writes)
            out.append("Dry run: nothing was written. This is what would be written:")
            out.extend("  " + w for w in would)
            if not would:
                out.append("  nothing: every file is already as this run would write it")
            if changes:
                out.append("Colours that would change in src/styles/global.css:")
                out.extend("  " + c for c in changes)
            out.extend("Note: " + n for n in notes)
            data["written"] = would
            return 0, "dry-run", data

        return _apply(a, site, out, data, plan, j, writes, want_colours, want_logo, card_colours, pal, brand_path, changes)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _read_bytes(site, rel):
    try:
        with open(os.path.join(site, *rel.split("/")), "rb") as f:
            return f.read()
    except OSError:
        return None


def _free_name(site, name, content):
    """Where in brand-handoff this package goes: its own name, or the same name with -2, -3 ... when
    a different file is already called that. The same content under the same name is not copied twice.
    preview.png is the preview sheet's name in that folder, so a package called that gets the next one."""
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    candidate, n = name, 1
    while True:
        existing = _read_bytes(site, HANDOFF + "/" + candidate)
        if candidate.lower() != "preview.png" and (existing is None or existing == content):
            return candidate
        n += 1
        candidate = "%s-%d%s" % (stem, n, ("." + ext) if ext else "")


def _apply(a, site, out, data, plan, j, writes, want_colours, want_logo, card_colours, pal, brand_path, changes):
    notes = data["notes"]
    touched = []

    def undo():
        """Put everything back, note in `data` what is then true of the site, and return what could not be put back."""
        left = j.rollback()
        data["rolled_back"] = bool(j.written or touched)
        data["written"] = []
        if left:
            data["not_restored"] = [{"file": rel, "why": why} for rel, why in left]
        if data["cards"] == "regenerated":
            data["cards"] = "not-restored" if CARDS in [rel for rel, _why in left] else "restored"
        return left

    watched = _watch_signals()
    try:
        for rel, new in writes:
            j.write(rel, new)

        touched.append(CARDS)
        ok, why = regenerate_cards(site)
        if ok:
            data["cards"] = "regenerated"
        else:
            j.restore_dir(CARDS)
            data["cards"] = "failed"
            data["cards_why"] = why
        if want_colours:
            after = _palette.read_css(_read_text(os.path.join(site, "src", "styles", "global.css"), "src/styles/global.css"))
            off = _differences(after, pal)
            if off:
                raise Refusal("check-failed", "After writing, the stylesheet does not carry the palette in all three places (an internal check), so nothing was kept. "
                              "What was read back: %s.%s" % ("; ".join("%s is %s, not %s" % (where, got or "unreadable", want) for where, got, want in off),
                                                             "".join(" " + p for p in _css_problems(after))))

        command = a.test_command or DEFAULT_TEST_COMMAND
        green, output = run_tests(site, command)
        if not green:
            names = failing_checks(output)
            left = undo()
            data["tests"] = "failed"
            data["failing"] = names
            lines = ["The site's own tests failed after the install." if left else
                     "The site's own tests failed after the install, so everything was put back (every file, the share cards included).",
                     "The failing check%s: %s" % ("" if len(names) == 1 else "s", "; ".join(names)) if names else
                     "The test command printed nothing, so it is not known which check failed. Run it yourself to see: %s" % command]
            if left:
                lines.extend(_aftermath(data))
            else:
                # what was seen, and no more: nothing here says how the site was before this run, or why
                baseline, _ = run_tests(site, command)
                lines.append("With the install taken out again, the same tests pass." if baseline else
                             "With the install taken out again, the same tests still fail.")
            raise Stop(1, lines, "rollback-incomplete" if left else "tests-failed")
        data["tests"] = "passed"
    except Stop:
        raise
    except BaseException as e:
        _set_signals({sig: signal.SIG_IGN for sig in watched})  # nothing stops the putting back half way
        undo()
        if isinstance(e, Interrupted):
            lines = ["The run was stopped from outside (%s) before it had finished, and what it had started was stopped with it." % signal.Signals(e.args[0]).name]
            raise Stop(2, lines + _aftermath(data), "rollback-incomplete" if data.get("not_restored") else "stopped") from None
        raise
    finally:
        _set_signals(watched)

    data["written"] = sorted(set(j.written))
    out.append("Done. The site's own tests pass afterwards.")
    if want_colours:
        out.append("Colours: the palette in %s is now in src/styles/global.css (the light theme, the dark theme, and the dark values for visitors without JavaScript), "
                   "in the theme colour and the manifest%s" % (os.path.basename(brand_path), ", and in the share cards." if card_colours and data["cards"] == "regenerated" else
                                                               ". The share cards do not have it: see below."))
        if changes:
            out.append("Colours that changed in src/styles/global.css:")
            out.extend("  " + c for c in changes)
    if want_logo:
        out.append("Logo: the seven icon files are in public/ (the app icons sit on %s, drawn from the %s version), COMPANY.logo and the share cards' emblem point at "
                   "public/images/logo.png." % (plan.background, plan.version))
    out.append("Written:")
    out.extend("  " + w for w in data["written"])
    for n in notes:
        out.append("Note: " + n)
    if data["cards"] == "regenerated":
        what = " and ".join(w for w, on in (("the new colours", card_colours), ("the emblem", want_logo)) if on)
        out.append("Share cards: regenerated%s." % (" with " + what if what else " in the colours they had"))
    else:
        out.append("Share cards: %s: the generator failed (%s). Everything else is in. %s" % (
            "the cards still show the old colours" if card_colours else "the cards are as they were before this run", data.get("cards_why", "no reason given"),
            "Install it (pip3 install Pillow), then run: npm run og" if data.get("cards_why") == PILLOW_MISSING else "When that is put right, run: npm run og"))
    if plan.preview:
        out.append("Preview: %s/preview.png shows the installed mark at 16 and 32 pixels, on the light theme (left) and the dark theme (right), at actual size and "
                   "enlarged. Whether it is legible at that size is your call." % HANDOFF)
    if plan.copy:
        out.append("The package you gave is kept in %s (git ignores that folder)." % plan.copy[0])
    return 0, "done", data
