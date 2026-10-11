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
CARDS = "public/images/og"
HANDOFF = "brand-handoff"
MASTER = "public/favicon.svg"


class Stop(Exception):
    """Not an error in the program: the run ends here with this exit status and these lines."""

    def __init__(self, code, lines, status):
        super().__init__("\n".join(lines))
        self.code, self.lines, self.status = code, lines, status


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


def _read_text(path):
    with open(path, "rb") as f:
        return f.read(1024 * 1024 + 1).decode("utf-8", "replace")


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


def regenerate_cards(site):
    """`npm run og` without npm: the same launcher, which finds python3, py or python. (ok, a sentence)."""
    node = shutil.which("node")
    if not node:
        return False, "Node is not available"
    try:
        r = subprocess.run([node, os.path.join("scripts", "run_og.mjs")], cwd=site, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return False, "the generator took more than five minutes"
    if r.returncode == 0:
        return True, ""
    lines = [l.strip() for l in (r.stderr + "\n" + r.stdout).splitlines() if l.strip()]
    return False, (lines[-1] if lines else "it stopped without saying why")[:200]


def run_tests(site, command):
    """(green, the tail of its output)."""
    try:
        r = subprocess.run(command, shell=True, cwd=site, capture_output=True, text=True, timeout=TEST_TIMEOUT, errors="replace")
    except subprocess.TimeoutExpired:
        return False, "the tests took more than %d minutes and were stopped" % (TEST_TIMEOUT // 60)
    return r.returncode == 0, (r.stdout + "\n" + r.stderr)


def failing_checks(output):
    """The names of what failed, from Playwright's list reporter ("  1) [chromium] > tests/a.spec.ts:8:5 > name")."""
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


def install(a, out):
    """Everything. `a` has: site, palette, input, pick, mono, with_colours, with_logo, accept_colours,
    accept_low_contrast, replace_icons, test_command, dry_run. Returns (exit code, status, data) and
    appends the report's lines to `out`. Raises nothing it can say in words: those are Stops."""
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
        data["asks"] = [{"code": k.code, "question": str(k), "options": k.options}]
        return 3, "needs-decision", data
    except Refusal as r:
        out.append(str(r))
        out.append("Nothing was written." if not data["written"] else "Everything it had written was put back.")
        data.update({"code": r.code, "message": str(r)})
        return 2, "refused", data


def _install(a, site, out, data):
    missing = _site.missing_files(site)
    if missing:
        raise Refusal("site-layout", "%s does not look like a site made from the starter: it lacks %s." % (site, ", ".join(missing)))
    css_text = _read_text(os.path.join(site, "src", "styles", "global.css"))
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
    want_colours = state == "complete"
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
    if want_colours:
        pairs = _palette.matrix(parsed)
        bad = [p for p in pairs if not p.ok]
        if bad:
            lines = [_palette.describe(p) for p in bad] + ["%d of %d pairs pass. Nothing was written." % (len(pairs) - len(bad), len(pairs))]
            raise Stop(1, lines, "contrast-failed")
        if parsed.proposed:
            names = ", ".join("%s (%s)" % (_palette.LABEL[k], t) for t, k in sorted(parsed.proposed))
            raise Ask("confirm-proposals", "These colours are still proposals, marked (proposed): %s. Ask the owner to confirm or change each one, take the marks out, then run this again." % names)
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
    want_logo = bool(a.input) or (want_colours and master_bytes is not None)
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
            report = _palette.check_mark(icons.visible, pal)
            if report.outside and not a.accept_colours:
                plan.asks.append(Ask("outside-palette", "These colours of the mark are not in the palette: %s. Nothing is recoloured without your say-so. Use the mark as it is "
                                     "(--accept-colours), or ask the tool for the mark in the palette's colours." % ", ".join(report.outside)))
            accepted = _accepted(a.accept_low_contrast)
            for theme, low in report.low.items():
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
            if plan.placeholders:
                notes.append("%s %s the scaffold's placeholder%s (the Astro logo), now replaced" % (
                    " and ".join(plan.placeholders), "was" if len(plan.placeholders) == 1 else "were", "" if len(plan.placeholders) == 1 else "s"))
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
            data["asks"] = [{"code": k.code, "question": str(k), "options": k.options} for k in plan.asks]
            raise Stop(3, lines, "needs-decision")

        # --- every edit, in memory, before anything is written ---------------------------------
        def edit(rel, fn):
            old = _read_text(os.path.join(site, *rel.split("/")))
            new = fn(old)
            if new != old:
                plan.texts[rel] = (old, new)
        if want_colours:
            edit("src/styles/global.css", lambda t: _site.edit_css(t, pal))
            edit("public/manifest.webmanifest", lambda t: _site.edit_manifest(t, primary, pal.light["bg"]))
        edit("src/config.ts", lambda t: _site.edit_config(t, primary if want_colours else None, logo=want_logo))
        edit("scripts/generate_og_cards.py", lambda t: _site.edit_og(t, pal if want_colours else None, logo=want_logo))
        ignore_new = None
        if plan.copy or plan.preview:
            gi_old = _read_text(os.path.join(site, ".gitignore")) if os.path.isfile(os.path.join(site, ".gitignore")) else ""
            ignore_new = _site.add_ignore(gi_old)
            if ignore_new is not None:
                plan.texts[".gitignore"] = (gi_old, ignore_new)

        would = sorted(set(list(plan.texts) + list(plan.files) + ([plan.copy[0]] if plan.copy else []) + (["%s/preview.png" % HANDOFF] if plan.preview else [])))
        if a.dry_run:
            out.append("Dry run: nothing was written. This is what would be written:")
            out.extend("  " + w for w in would)
            out.extend("Note: " + n for n in notes)
            data["written"] = would
            return 0, "dry-run", data

        return _apply(a, site, out, data, plan, would, want_colours, want_logo, pal, parsed, brand_path, css)
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
    a different file is already called that. The same content under the same name is not copied twice."""
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    candidate, n = name, 1
    while True:
        existing = _read_bytes(site, HANDOFF + "/" + candidate)
        if existing is None or existing == content:
            return candidate
        n += 1
        candidate = "%s-%d%s" % (stem, n, ("." + ext) if ext else "")


def _apply(a, site, out, data, plan, would, want_colours, want_logo, pal, parsed, brand_path, css_before):
    j = _site.Journal(site)
    notes = data["notes"]
    try:
        j.snapshot_dir(CARDS)
        for rel, data_ in plan.files.items():
            if _read_bytes(site, rel) != data_:
                j.write(rel, data_)
        for rel, (_old, new) in plan.texts.items():
            j.write(rel, new.encode("utf-8"))
        if plan.copy and _read_bytes(site, plan.copy[0]) != plan.copy[1]:
            j.write(plan.copy[0], plan.copy[1])
        if plan.preview and _read_bytes(site, HANDOFF + "/preview.png") != plan.preview:
            j.write(HANDOFF + "/preview.png", plan.preview)

        ok, why = regenerate_cards(site)
        if ok:
            data["cards"] = "regenerated"
        else:
            j.restore_dir(CARDS)
            data["cards"] = "failed"
            data["cards_why"] = why
        if want_colours:
            after = _palette.read_css(_read_text(os.path.join(site, "src", "styles", "global.css")))
            if after.light != {k: v for k, v in pal.light.items() if k in _palette.KEYS} or after.dark != after.dark_media or \
                    after.dark != {k: v for k, v in pal.dark.items() if k in _palette.KEYS}:
                raise Refusal("check-failed", "After writing, the stylesheet does not carry the palette in all three places (an internal check), so nothing was kept.")

        command = a.test_command or DEFAULT_TEST_COMMAND
        green, output = run_tests(site, command)
        if not green:
            names = failing_checks(output)
            j.rollback()
            data["tests"] = "failed"
            data["failing"] = names
            baseline, _ = run_tests(site, command)
            lines = ["The site's own tests failed after the install, so everything was put back (every file, the share cards included).",
                     "The failing check%s: %s" % ("" if len(names) == 1 else "s", "; ".join(names))]
            lines.append("They pass without the install, so it was the install." if baseline else
                         "The same tests fail without the install too: the site was already red before this run.")
            data["written"] = []
            raise Stop(1, lines, "tests-failed")
        data["tests"] = "passed"
    except Stop:
        raise
    except BaseException:
        j.rollback()
        raise

    data["written"] = sorted(set(j.written))
    out.append("Done. The site's own tests pass afterwards.")
    if want_colours:
        out.append("Colours: the palette in %s is now in src/styles/global.css (the light theme, the dark theme, and the dark values for visitors without JavaScript), "
                   "in the theme colour and the manifest, and in the share cards." % os.path.basename(brand_path))
    if want_logo:
        out.append("Logo: the seven icon files are in public/ (the app icons sit on %s, drawn from the %s version), COMPANY.logo and the share cards' emblem point at "
                   "public/images/logo.png." % (plan.background, plan.version))
    out.append("Written:")
    out.extend("  " + w for w in data["written"])
    for n in notes:
        out.append("Note: " + n)
    if data["cards"] == "regenerated":
        out.append("Share cards: regenerated%s." % (" with the new colours and the emblem" if want_colours and want_logo else
                                                      " with the new colours" if want_colours else " with the emblem"))
    else:
        out.append("Share cards: the cards still show the old colours: the generator failed (%s). Everything else is in. When Python and its image library "
                   "are available (pip3 install Pillow), run: npm run og" % data.get("cards_why", "no reason given"))
    if plan.preview:
        out.append("Preview: %s/preview.png shows the installed mark at 16 and 32 pixels, on the light theme (left) and the dark theme (right), at actual size and "
                   "enlarged. Whether it is legible at that size is your call." % HANDOFF)
    if plan.copy:
        out.append("The package you gave is kept in %s (git ignores that folder)." % plan.copy[0])
    return 0, "done", data
