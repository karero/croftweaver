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
import shutil
import tempfile

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
    """What a site must have for the intake to write into it, and lacks."""
    return [r for r in REQUIRED_FILES if not os.path.isfile(os.path.join(site, *r.split("/")))]


# --- global.css --------------------------------------------------------------------------

_ROOT = re.compile(r"(?m)^[ \t]*:root[ \t\n]*\{")
_DARK = re.compile(r"""(?m)^[ \t]*:root\[\s*data-theme\s*=\s*["']dark["']\s*\][ \t\n]*\{""")
_MEDIA = re.compile(r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)\s*\{")
_MEDIA_ROOT = re.compile(r":root:not\(\s*\[\s*data-theme\s*\]\s*\)\s*\{")


def _mask(text):
    """The same text with comments blanked (same length), so a selector in a comment is never found."""
    return re.sub(r"/\*.*?(\*/|\Z)", lambda m: " " * len(m.group()), text, flags=re.S)


def _block_end(masked, o):
    """Where the block that opened just before `o` closes (the end of the text when it never does)."""
    depth = 1
    for i in range(o, len(masked)):
        depth += (masked[i] == "{") - (masked[i] == "}")
        if not depth:
            return i
    return len(masked)


def _body(masked, opener, start, what, end=None):
    m = opener.search(masked, start, len(masked) if end is None else end)
    if not m:
        raise Refusal("css-layout", "src/styles/global.css has no %s, which the starter's stylesheet has. Edit the colours by hand, or restore that block." % what)
    o = m.end()
    c = masked.find("}", o)
    nested = masked.find("{", o)
    if c < 0 or 0 <= nested < c:
        raise Refusal("css-layout", "src/styles/global.css: %s is not a plain list of declarations." % what)
    return o, c


def _set(text, masked, span, values, what):
    o, c = span
    edits = []
    for var, value in values:
        # the value alone: a comment (blank in `masked`) or an `!important` between it and the `;` stays
        m = re.search(r"(?<![\w-])%s\s*:\s*(?P<v>[^;{}]*?)\s*(?:!\s*(?i:important)\s*)?(?=;)" % re.escape(var), masked[o:c])
        if not m:
            raise Refusal("css-layout", "src/styles/global.css: %s sets no %s. Add the line, or edit the colours by hand." % (what, var))
        edits.append((o + m.start("v"), o + m.end("v"), value))
    return edits


def edit_css(text, palette):
    """The palette in the stylesheet's three places: :root (light), :root[data-theme="dark"] and the
    :root:not([data-theme]) block inside @media (prefers-color-scheme: dark)."""
    import _palette as P
    masked = _mask(text)
    light = _body(masked, _ROOT, 0, "`:root` block (the light theme)")
    dark = _body(masked, _DARK, 0, "`:root[data-theme=\"dark\"]` block (the dark theme)")
    # each such @media block from its opening brace to its closing one: the dark block is looked for inside
    # one of them, never after it
    medias = [(m.end(), _block_end(masked, m.end())) for m in _MEDIA.finditer(masked)]
    if not medias:
        raise Refusal("css-layout", "src/styles/global.css has no `@media (prefers-color-scheme: dark)` block (the dark theme for visitors without JavaScript), which the starter's stylesheet has. Edit the colours by hand, or restore that block.")
    media_open, media_close = next(((o, c) for o, c in medias if _MEDIA_ROOT.search(masked, o, c)), medias[0])
    media = _body(masked, _MEDIA_ROOT, media_open, "`:root:not([data-theme])` block inside the `@media (prefers-color-scheme: dark)` block", media_close)
    edits = []
    light_vals = [(P.VARIABLE[k], palette.light[k]) for k in P.KEYS if k in palette.light]
    if palette.brand:
        light_vals.append((P.VARIABLE["brand"], palette.brand))
    dark_vals = [(P.VARIABLE[k], palette.dark[k]) for k in P.KEYS if k in palette.dark]
    edits += _set(text, masked, light, light_vals, "the `:root` block (the light theme)")
    edits += _set(text, masked, dark, dark_vals, "the `:root[data-theme=\"dark\"]` block (the dark theme)")
    edits += _set(text, masked, media, dark_vals, "the dark block inside the `@media (prefers-color-scheme: dark)` block")
    out = text
    for a, b, value in sorted(edits, reverse=True):
        out = out[:a] + value + out[b:]
    return out


# --- src/config.ts -----------------------------------------------------------------------

def _own_level(block):
    """The same text (same length, same line breaks) with comments, strings and everything inside a nested
    {...}, [...] or (...) blanked: what is left is the object's own keys, each where it stands."""
    out, depth, i, n = [], 0, 0, len(block)
    while i < n:
        ch, j = block[i], i + 1
        if block.startswith("//", i):
            j = block.find("\n", i)
            j = n if j < 0 else j
        elif block.startswith("/*", i):
            j = block.find("*/", i + 2)
            j = n if j < 0 else j + 2
        elif ch in "'\"`":
            while j < n and block[j] != ch:
                j += 2 if block[j] == "\\" else 1
            j = min(j + 1, n)
        elif ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
        if j == i + 1 and depth <= 1 and ch not in "'\"`":
            out.append(ch)
        else:
            out.append("".join("\n" if c == "\n" else " " for c in block[i:j]))
        i = j
    return "".join(out)


def _own_value(text, const, key, value):
    """Where the quoted value of `key` stands in `export const <const> = {...}`, as (start, end) without
    the quotes, or None. Only the object's own line counts: not one of an object nested in it, of another
    object, or in a comment. Two such lines are refused, because which one counts cannot be known."""
    block = re.search(r"export const %s(?:[ \t]*:[^=\n]+)?\s*=\s*\{.*?\n\}" % const, text, re.S)
    if not block:
        return None
    found = []
    for k in re.finditer(r"(?m)^[ \t]*%s:" % key, _own_level(block.group(0))):
        m = re.compile(r"""[ \t]*(['"])(%s)\1""" % value).match(block.group(0), k.end())
        if m:
            found.append((block.start() + m.start(2), block.start() + m.end(2)))
    if len(found) > 1:
        raise Refusal("config-layout", "src/config.ts sets `%s` twice in %s, so it cannot be known which line counts. Leave one of them, then run this again." % (key, const))
    return found[0] if found else None


def company_logo(text):
    """What COMPANY.logo says now, or None when the line is not there."""
    span = _own_value(text, "COMPANY", "logo", r"""[^'"\n]*""")
    return text[span[0]:span[1]] if span else None


def edit_config(text, primary, logo=False):
    """SITE.themeColor is the primary (None: the colours are not being changed); with a logo,
    COMPANY.logo is the derived square PNG."""
    new = text
    if primary is not None:
        span = _own_value(new, "SITE", "themeColor", r"#[0-9a-fA-F]{3,8}")
        if not span:
            raise Refusal("config-layout", "src/config.ts has no `themeColor: '#...'` line in SITE. Set it by hand to %s." % primary)
        new = new[:span[0]] + primary + new[span[1]:]
    if logo:
        span = _own_value(new, "COMPANY", "logo", r"""[^'"\n]*""")
        if not span:
            raise Refusal("config-layout", "src/config.ts has no `logo: '...'` line in COMPANY. Set it by hand to '/images/logo.png'.")
        new = new[:span[0]] + "/images/logo.png" + new[span[1]:]
    return new


# --- public/manifest.webmanifest ---------------------------------------------------------

def edit_manifest(text, theme, background):
    for key, value in (("theme_color", theme), ("background_color", background)):
        text, n = re.subn(r'("%s"\s*:\s*)"[^"\n]*"' % key, lambda m: m.group(1) + '"' + value + '"', text, count=1)
        if not n:
            raise Refusal("manifest-layout", "public/manifest.webmanifest has no \"%s\" line. Set it by hand to %s." % (key, value))
    try:
        data = json.loads(text)
    except ValueError:
        raise Refusal("manifest-layout", "public/manifest.webmanifest is not valid JSON after the colours were set, so it was not changed.") from None
    # each line above is the first of its name in the file, which need not be the manifest's own
    if not isinstance(data, dict) or (data.get("theme_color"), data.get("background_color")) != (theme, background):
        raise Refusal("manifest-layout", "public/manifest.webmanifest: its own \"theme_color\" and \"background_color\" could not be set, because the first line of "
                                         "one of those names in the file belongs to another entry. Set the manifest's own two by hand to %s and %s." % (theme, background))
    return text


# --- scripts/generate_og_cards.py --------------------------------------------------------

# The share cards are dark cards (light text on a deep background): the dark theme's colours. Title, subtitle
# and footer sit on a gradient between the dark surface and the dark background, and the palette check holds
# every one of these text colours to 4.5 to 1 on both. That says nothing of the rows in between (a grey that
# passes on white and on black is unreadable on the grey half way), so og_low_contrast looks at every row.
OG_COLOURS = (("BG_TOP", "surface"), ("BG_BOT", "bg"), ("TITLE_COL", "heading"), ("SUB_COL", "accent"),
              ("ACCENT", "accent"), ("FOOTER_COL", "muted"))
OG_TEXT = ("heading", "accent", "muted")  # the keys of TITLE_COL, SUB_COL and FOOTER_COL: what the cards write with
OG_ROWS = 630                             # the generator's H: its gradient has one colour per row of the card
OG_LOGO = 'ROOT / "public/images/logo.png"'


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


def edit_og(text, palette, logo):
    """The share-card generator's BRAND block: the dark theme's colours (palette None: the colours are
    not being changed) and, with a logo, the emblem."""
    import _palette as P
    for name, key in (OG_COLOURS if palette is not None else ()):
        if key not in palette.dark:
            raise Refusal("palette-incomplete", "The share cards need the dark theme's %s colour, which the palette does not give." % P.LABEL[key])
    for name, key in (OG_COLOURS if palette is not None else ()):
        h = palette.dark[key]
        rgb = "(%d, %d, %d)" % tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        text, n = re.subn(r"(?m)^(%s[ \t]*=[ \t]*)\([ \t]*\d+[ \t]*,[ \t]*\d+[ \t]*,[ \t]*\d+[ \t]*\)" % name, lambda m: m.group(1) + rgb, text, count=1)
        if not n:
            raise Refusal("og-layout", "scripts/generate_og_cards.py has no `%s = (r, g, b)` line, so the share cards cannot be recoloured. Edit its BRAND block by hand." % name)
    if logo:
        m = re.search(r"(?m)^LOGO[ \t]*=[ \t]*(?P<v>[^#\n]*?)[ \t]*(?:#.*)?$", text)
        if not m:
            raise Refusal("og-layout", "scripts/generate_og_cards.py has no `LOGO = ...` line, so the emblem cannot be set. Edit its BRAND block by hand.")
        value = m.group("v").strip()
        if value == "None":
            text = text[:m.start("v")] + OG_LOGO + text[m.end("v"):]
        elif re.sub(r"\s+", "", value).replace("'", '"') != re.sub(r"\s+", "", OG_LOGO):
            raise Refusal("og-layout", "scripts/generate_og_cards.py already points LOGO somewhere else (%s). Change it by hand if the new logo should be the emblem." % value[:60])
    return text


# --- .gitignore --------------------------------------------------------------------------

def add_ignore(text, line="brand-handoff/"):
    """The text with the folder's line added, or None when it is already ignored. In a .gitignore a later
    line takes back an earlier one (`!brand-handoff/logo.svg`), so the folder's rule counts only when no
    line after it that starts with `!` names the folder; otherwise the line goes at the end, where it wins."""
    ignored = False
    for existing in text.lstrip("﻿").splitlines():  # a byte order mark is not part of the first rule
        rule = existing.strip()
        if re.fullmatch(r"/?brand-handoff(?:/\*?)?", rule):
            ignored = True
        elif rule.startswith("!") and "brand-handoff" in rule:
            ignored = False
    if ignored:
        return None
    if not text:
        return line + "\n"
    return (text if text.endswith("\n") else text + "\n") + line + "\n"


# --- the journal -------------------------------------------------------------------------

class Journal(object):
    def __init__(self, site):
        self.site = os.path.realpath(site)
        self._orig = {}
        self._made = []
        self._snapshots = {}
        self.written = []

    def _path(self, rel):
        if (not isinstance(rel, str) or not rel or rel.startswith("/") or "\\" in rel or "\x00" in rel
                or os.path.isabs(rel) or ".." in rel.split("/")):
            raise Refusal("site-path", "The path %r is not inside the site." % str(rel)[:60])
        here = self.site
        for part in rel.split("/"):
            here = os.path.join(here, part)
            if os.path.islink(here):
                raise Refusal("site-path", "%s is a link, and nothing is written through a link." % rel)
        return os.path.join(self.site, *rel.split("/"))

    def read(self, rel):
        path = self._path(rel)
        if os.path.isdir(path):
            raise Refusal("site-path", "%s is a folder." % rel)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    def _mkdirs(self, path):
        todo = []
        d = path
        while not os.path.isdir(d):
            todo.append(d)
            d = os.path.dirname(d)
        for d in reversed(todo):
            os.mkdir(d)
            self._made.append(d)

    def _put(self, path, data, mode=0o644):
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".write-")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.chmod(tmp, mode)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def check(self, rel):
        """What can be known of a write before the first one is made: the path keeps the rules `write`
        holds it to, no file stands where a folder is needed (nor a folder where the file goes), and this
        account may write in the folder it goes into. Refuses in words; changes nothing."""
        path = self._path(rel)
        if os.path.isdir(path):
            raise Refusal("site-path", "%s is a folder, so a file of that name cannot be written." % rel)
        d = os.path.dirname(path)
        while not os.path.isdir(d):
            if os.path.lexists(d):
                raise Refusal("site-path", "%s cannot be written: %s is a file, not a folder." % (rel, os.path.relpath(d, self.site).replace(os.sep, "/")))
            d = os.path.dirname(d)
        if not os.access(d, os.W_OK | os.X_OK):
            where = os.path.relpath(d, self.site).replace(os.sep, "/")
            raise Refusal("site-path", "%s cannot be written: this account is not allowed to write in %s. Change the folder's permissions, then run this again."
                          % (rel, "the site's folder" if where == "." else where))

    def write(self, rel, data):
        path = self._path(rel)
        # the original is kept before the write, so that a run stopped half way through one still knows
        # it; rollback leaves alone a file that is as it was, so a write that failed costs nothing there
        if rel not in self._orig:
            self._orig[rel] = self.read(rel)
        mode = (os.stat(path).st_mode & 0o777) if os.path.exists(path) else 0o644
        self._mkdirs(os.path.dirname(path))
        self._put(path, data, mode)
        self.written.append(rel)

    def snapshot_dir(self, rel):
        """Keep a folder as it is: every file with its bytes and its mode, every folder (an empty one
        too) with its mode. A link in it is refused: restoring would turn it into an ordinary file."""
        path = self._path(rel)
        snap = None
        if os.path.isdir(path):
            dirs, files = {}, {}
            for base, subdirs, names in os.walk(path):
                for n in subdirs + names:
                    if os.path.islink(os.path.join(base, n)):
                        raise Refusal("site-path", "%s holds a link (%s). The share cards are made again in that folder, and nothing is written through a link: "
                                                   "replace the link with the file itself, or take it out." % (rel, os.path.relpath(os.path.join(base, n), path).replace(os.sep, "/")))
                dirs[os.path.relpath(base, path)] = os.stat(base).st_mode & 0o777
                for n in names:
                    p = os.path.join(base, n)
                    with open(p, "rb") as f:
                        files[os.path.relpath(p, path)] = (f.read(), os.stat(p).st_mode & 0o777)
            snap = (dirs, files)
        self._snapshots[rel] = snap

    def restore_dir(self, rel):
        path = self._path(rel)
        snap = self._snapshots[rel]
        if os.path.isdir(path):
            for base, subdirs, _names in os.walk(path):  # a folder kept read-only could not be emptied
                for d in [base] + [os.path.join(base, s) for s in subdirs]:
                    os.chmod(d, (os.stat(d).st_mode & 0o777) | 0o700)
            shutil.rmtree(path)
        if snap is not None:
            dirs, files = snap
            for d in sorted(dirs):
                os.makedirs(os.path.join(path, d), exist_ok=True)
            for name, (data, mode) in files.items():
                self._put(os.path.join(path, name), data, mode)
            for d in sorted(dirs, key=lambda d: (d != ".", d.count(os.sep)), reverse=True):  # the deepest first, the folder itself last
                os.chmod(os.path.join(path, d), dirs[d])

    def rollback(self):
        """Put every file back as it was, remove what the run made, leave the rest alone. Every file is
        tried, also after one could not be put back. Returns [(path, why)] for what could not be put back:
        empty when the site is as it was."""
        left = []
        for rel in list(self._snapshots):
            try:
                self.restore_dir(rel)
            except (OSError, Refusal) as e:
                left.append((rel, getattr(e, "strerror", None) or str(e)))
        for rel, orig in reversed(list(self._orig.items())):
            try:
                path = self._path(rel)
                gone = not os.path.isdir(os.path.dirname(path))
                if (orig is None and gone) or (not gone and self.read(rel) == orig):
                    continue  # as it was: never written, or already put back
                if orig is None:
                    os.remove(path)
                elif gone:
                    left.append((rel, "its folder is no longer there"))
                else:
                    self._put(path, orig, (os.stat(path).st_mode & 0o777) if os.path.exists(path) else 0o644)
            except (OSError, Refusal) as e:
                left.append((rel, getattr(e, "strerror", None) or str(e)))
        for d in reversed(self._made):
            try:
                os.rmdir(d)
            except OSError:
                pass  # something that is not ours is in it, or it is gone
        return left
