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
# anything else is asked about. A newer create-astro that changes the logo makes them "something else",
# which only means the owner is asked.
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


def _body(masked, opener, start, what):
    m = opener.search(masked, start)
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
        m = re.search(r"(?<![\w-])%s\s*:\s*(?P<v>[^;{}]*)(?=;)" % re.escape(var), masked[o:c])
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
    media_open = _MEDIA.search(masked)
    if not media_open:
        raise Refusal("css-layout", "src/styles/global.css has no `@media (prefers-color-scheme: dark)` block (the dark theme for visitors without JavaScript), which the starter's stylesheet has. Edit the colours by hand, or restore that block.")
    media = _body(masked, _MEDIA_ROOT, media_open.end(), "`:root:not([data-theme])` block inside the `@media (prefers-color-scheme: dark)` block")
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

def edit_config(text, primary, logo=False):
    """SITE.themeColor is the primary (None: the colours are not being changed); with a logo,
    COMPANY.logo is the derived square PNG."""
    new = text
    if primary is not None:
        new, n = re.subn(r"""(?m)^([ \t]*themeColor:[ \t]*)(['"])#[0-9a-fA-F]{3,8}\2""", lambda m: m.group(1) + m.group(2) + primary + m.group(2), text, count=1)
        if not n:
            raise Refusal("config-layout", "src/config.ts has no `themeColor: '#...'` line in SITE. Set it by hand to %s." % primary)
    if logo:
        block = re.search(r"export const COMPANY\s*=\s*\{.*?\n\}", new, re.S)
        inner = re.search(r"""(?m)^([ \t]*logo:[ \t]*)(['"])[^'"\n]*\2""", block.group(0)) if block else None
        if not inner:
            raise Refusal("config-layout", "src/config.ts has no `logo: '...'` line in COMPANY. Set it by hand to '/images/logo.png'.")
        a = block.start() + inner.start()
        new = new[:a] + inner.group(1) + inner.group(2) + "/images/logo.png" + inner.group(2) + new[block.start() + inner.end():]
    return new


# --- public/manifest.webmanifest ---------------------------------------------------------

def edit_manifest(text, theme, background):
    for key, value in (("theme_color", theme), ("background_color", background)):
        text, n = re.subn(r'("%s"\s*:\s*)"[^"\n]*"' % key, lambda m: m.group(1) + '"' + value + '"', text, count=1)
        if not n:
            raise Refusal("manifest-layout", "public/manifest.webmanifest has no \"%s\" line. Set it by hand to %s." % (key, value))
    try:
        json.loads(text)
    except ValueError:
        raise Refusal("manifest-layout", "public/manifest.webmanifest is not valid JSON after the colours were set, so it was not changed.") from None
    return text


# --- scripts/generate_og_cards.py --------------------------------------------------------

# The share cards are dark cards (light text on a deep background): the dark theme's colours. Title, subtitle
# and footer sit on a gradient between the dark surface and the dark background, and the palette check holds
# every one of these text colours to 4.5 to 1 on both.
OG_COLOURS = (("BG_TOP", "surface"), ("BG_BOT", "bg"), ("TITLE_COL", "heading"), ("SUB_COL", "accent"),
              ("ACCENT", "accent"), ("FOOTER_COL", "muted"))
OG_LOGO = 'ROOT / "public/images/logo.png"'


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
        elif re.sub(r"\s+", "", value) != re.sub(r"\s+", "", OG_LOGO).replace("'", '"'):
            raise Refusal("og-layout", "scripts/generate_og_cards.py already points LOGO somewhere else (%s). Change it by hand if the new logo should be the emblem." % value[:60])
    return text


# --- .gitignore --------------------------------------------------------------------------

def add_ignore(text, line="brand-handoff/"):
    """The text with the folder's line added, or None when it is already ignored."""
    for existing in text.splitlines():
        if re.fullmatch(r"/?brand-handoff(?:/\*?)?", existing.strip()):
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

    def write(self, rel, data):
        path = self._path(rel)
        if rel not in self._orig:
            self._orig[rel] = self.read(rel)
        mode = (os.stat(path).st_mode & 0o777) if os.path.exists(path) else 0o644
        self._mkdirs(os.path.dirname(path))
        self._put(path, data, mode)
        self.written.append(rel)

    def snapshot_dir(self, rel):
        path = self._path(rel)
        files = None
        if os.path.isdir(path):
            files = {}
            for base, _dirs, names in os.walk(path):
                for n in names:
                    p = os.path.join(base, n)
                    with open(p, "rb") as f:
                        files[os.path.relpath(p, path)] = f.read()
        self._snapshots[rel] = files

    def restore_dir(self, rel):
        path = self._path(rel)
        files = self._snapshots[rel]
        if os.path.isdir(path):
            shutil.rmtree(path)
        if files is not None:
            os.makedirs(path)
            for name, data in files.items():
                p = os.path.join(path, name)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                self._put(p, data)

    def rollback(self):
        """Put every file back as it was, remove what the run made, leave the rest alone."""
        for rel in list(self._snapshots):
            self.restore_dir(rel)
        for rel, orig in reversed(list(self._orig.items())):
            path = self._path(rel)
            if orig is None:
                if os.path.isfile(path):
                    os.remove(path)
            elif os.path.isdir(os.path.dirname(path)):
                self._put(path, orig, (os.stat(path).st_mode & 0o777) if os.path.exists(path) else 0o644)
        for d in reversed(self._made):
            try:
                os.rmdir(d)
            except OSError:
                pass  # something that is not ours is in it, or it is gone
