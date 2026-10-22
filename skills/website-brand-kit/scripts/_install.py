"""_install.py: put a palette and a logo into a site, or stop and say why.

Order matters, and it is the point of this file. Everything that can be checked is checked, and every
file is built in memory or in a temporary folder, BEFORE the site is touched: the palette's contrast, the
mark's safety and colours, the sharp preflight, the seven icons, each edit. Where the owner must decide
something (a colour outside the palette, a mark that vanishes on a theme, an icon that is not a
placeholder), it asks and writes nothing. Only then does it write, through a journal. Once the files are
written it asks the site's own Node and Python what they read from the two files it edits by line (the
read-back), and then runs the site's own tests. If the site reads something else than was set, or the
tests are red, the journal puts every file back and the report says which.

Two parts, each from her own material or the assistant's: the palette (BRAND.md, the stylesheet, the
theme colour, the manifest's colours, the share cards' colours) and the logo (the seven icon files and
COMPANY.logo). A part she has no material for stays as the site has it. The share cards' emblem (the
generator's LOGO line) is not set here: a logo run says so and names the skill that does it. Standard
library only.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import stat
import tempfile

import _colour
import _icons
import _input
import _palette
import _render
import _site
import _svg
import _zipin
from _proc import Interrupted, _HOLD, _held, _listing, _run   # noqa: F401 (_listing: the tests ask it by this name too)
from _refusal import Ask, Refusal

DEFAULT_TEST_COMMAND = "npm run build && npm test"
TEST_TIMEOUT = 30 * 60
CARDS_TIMEOUT = 5 * 60
READ_BACK_SECONDS = 60   # how long Node, and Python, may take to say what they read from one file
MAX_TEXT = 1024 * 1024
CARDS = "public/images/og"
HANDOFF = "brand-handoff"
MASTER = "public/favicon.svg"
# The first line of the favicon this tool installs, and how a later run knows the file as its own: a favicon
# that somebody wrote by hand may be a cleaned SVG too, so that alone does not show who wrote it.
MARK = "<!-- Installed by the website-brand-kit skill (brand_intake.py install) from the logo it was given. When the site's colours change, the icons are drawn again from this file. -->\n"
# The same line for a mark that was given in `currentColor`: it also names the colour the mark is drawn in here, the
# Primary of the day. The line above means a mark with colours of its own (and so does every file installed before
# this second form was there).
MARK_CURRENT = MARK[:-5] + " The logo was given in currentColor and is drawn here in %s. -->\n"
# That line with one sentence more, for a mark that as it was given also holds that very colour as a colour of its own (a
# part in `currentColor` beside a part written in the Primary of the day). In this file the two parts have one colour,
# and only the line tells a later run that one of them keeps it whatever colour the package is drawn in.
MARK_CURRENT_OWN = MARK_CURRENT[:-5] + " A part of it has that colour as its own. -->\n"
_MARK_LINE = re.compile(re.escape(MARK[:-5].encode("utf-8")) + rb"(?: The logo was given in currentColor and is drawn here in (#[0-9a-f]{6})\.( A part of it has that colour as its own\.)?)? -->\n")
BOM = "﻿"
STYLESHEET = "src/styles/global.css"
OTHER_FILES = (_site.CONFIG, _site.MANIFEST, _site.GENERATOR)  # the colours' other three homes
PILLOW_MISSING = "Pillow, the image library the generator draws with, is not installed"
ONE_COLOUR_ICONS = ("this tool cannot tell what the installed app icons sit on, or which version of the logo they were drawn from (it keeps the colour version only), so "
                    "this run left them as they are. To draw them for the new colours, run this again with the package the logo came in: --input, with --pick and "
                    "--mono as before")
# A logo this tool installed keeps the colours it was drawn in when the palette changes. What can be done about it
# depends on how the mark was given: one in `currentColor` is drawn in the new Primary from its package (in the light
# theme's Accent where the palette gives no Primary); one with colours of its own is the same drawing whenever it is
# installed, and this tool recolours nothing. A mark with both kinds of colour can get both notes.
KEPT_CURRENT = ("the logo was given in `currentColor` and was drawn in %s. It keeps that colour: this tool draws it in %s only from the package it came in. For that, run "
                "this again with the package: --input, with --pick and --mono as before")
KEPT_FOR = ("the Primary the palette has now (%s)", "the light theme's Accent the palette has now (%s: it gives no Primary)",
            "the stylesheet's `--brand` (%s)")   # (the third: there is no palette in BRAND.md to ask, and the stylesheet's `--brand` is the Primary)
# A run that leaves BRAND.md's palette out (--keep-colours, or a palette that is not complete) goes by the site's own
# colours. Where BRAND.md names no Primary, a mark given in `currentColor` is then drawn in the light theme's Accent
# as the site has it, not in the stylesheet's `--brand`: said on the run that draws it (BRAND.md's name, the colour).
DRAWN_IN_ACCENT = ("the mark (or the part of it given without a colour of its own, in `currentColor`) is drawn in the light theme's Accent the site has now (%s), "
                   "because %s names no Primary. The site's own colours were not changed")
KEPT_COLOURS = ("the logo keeps %s it was installed with (%s), which the palette no longer holds: this run changes the site's colours and leaves the logo's files as they "
                "are, and this tool recolours nothing. For the logo in the new colours, ask the design tool for the mark in them, then run this again with that package: --input")
NO_EMBLEM = ("the share cards get no emblem from this tool (the logo, shown faintly on each card): it leaves the LOGO line in scripts/generate_og_cards.py exactly as it is. "
             "The og-images skill says how to put the logo on the cards")


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


def _is_file(path):
    """Whether a file is at `path`. "No" means nothing is there, or something that is not a file. A path
    that cannot be looked at (its folder is closed to this account) raises OSError instead, and the run
    stops with the path and the reason: a file that is there is never taken for one that is not."""
    try:
        return stat.S_ISREG(os.stat(path).st_mode)
    except (FileNotFoundError, NotADirectoryError, ValueError):
        return False


def _find_brand_md(site):
    for rel in ("BRAND.md", "docs/BRAND.md"):
        if _is_file(os.path.join(site, *rel.split("/"))):
            return os.path.join(site, *rel.split("/"))
    return None


def _palette_trouble(parsed, name):
    """Why a palette that was found is not applied, as lines for the report: what it lacks, then each
    thing the reading of it could not use, one to a line (they are whole sentences), then the form the
    reading takes when it found no row at all."""
    by = {}
    for t, k in parsed.missing():
        by.setdefault(t, []).append(_palette.LABEL[k])
    if not (parsed.light or parsed.dark or parsed.brand):
        lines = ["No colour could be read from the palette in %s." % name]
    elif by:
        lines = ["The palette in %s is not complete. Rows without a colour: %s." % (name, "; ".join("%s: %s" % (_theme_label(t), ", ".join(v)) for t, v in by.items()))]
    else:
        lines = ["The palette in %s could not be read in full." % name]
    lines.extend(m for _t, _k, _c, m in parsed.problems)
    if not parsed.rows_found:
        lines.append(_palette.FORM)
    return lines


def _no_bom(text):
    """The text without the byte order mark some editors put at the start of a file. It is read past, and
    the file keeps it when it is written back."""
    return text[len(BOM):] if text.startswith(BOM) else text


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
        names = sorted(n for n in os.listdir(path) if n.lower().endswith((".zip", ".svg")) and _is_file(os.path.join(path, n)))
        if not names:
            raise Refusal("no-input", "Nothing arrived at %s: that folder holds no .zip or .svg file. Ask for the path again; this tool does not "
                                      "search other folders (your Downloads, say) on its own." % path)
        if len(names) > 1:
            raise Ask("which-package", "The folder %s holds %d files that could be the package. Which one is it? (Give its full path as the input.)" % (path, len(names)),
                      [os.path.join(path, n) for n in names])
        path = os.path.join(path, names[0])
    if not _is_file(path):
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


# --- a stop from outside ---------------------------------------------------------------------

SIGNALS = ("SIGTERM", "SIGHUP", "SIGINT", "SIGQUIT")  # Windows has neither SIGHUP nor SIGQUIT
# (The flag these set, the lines during which a stop is kept back, and the running of commands are in _proc.py: the
# renderer runs Node by the same rules, and does not know this file.)


def _stop(signum, _frame):
    """The one handler for all the watched signals. It never changes how a signal is handled (doing that
    from inside a handler, while a second signal is on its way, makes Python raise an error of its own):
    whether a signal still counts is a flag that this handler reads."""
    if _HOLD["deaf"]:
        return
    if _HOLD["depth"]:
        _HOLD["pending"] = signum   # raised when the lines that must not be cut short are over
        return
    _HOLD["deaf"] = True
    raise Interrupted(signum)


def _watch_signals():
    """From here on a SIGTERM, a SIGHUP, a SIGQUIT or a Ctrl-C raises Interrupted inside the run, which
    then puts back what it wrote and says so, instead of the process ending with the site half installed
    or with a traceback. One stop is enough: the first signal sets a flag, and from then on the handler
    does nothing, whichever signal comes and however close behind, so that a second one cuts short neither
    the putting back nor the report. The handler is set once, here, and this file does not take it away
    again. (Python does, while it shuts down: it puts every signal back to its default. So the command
    line ends the process without that, see brand_intake._leave.) A signal that was already being ignored
    (a run started with nohup ignores SIGHUP) is left ignored. The caller holds the stop back while this
    runs (_held): a signal that comes after the first handler is set is raised when all of them are."""
    for name in SIGNALS:
        sig = getattr(signal, name, None)
        try:
            if sig is not None and signal.getsignal(sig) != signal.SIG_IGN:
                signal.signal(sig, _stop)
        except (ValueError, OSError):
            pass  # not the main thread, where no signal arrives anyway


def _ignore_signals():
    """From here on the watched signals do nothing (see _stop): the run has its outcome, or is putting back."""
    _HOLD["deaf"] = True


_ESCAPES = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]")
_CONTROLS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def _plain(output):
    """What a command printed, without the codes a terminal would turn into colours and cursor moves, and
    without any other control character: what goes into a report is text and nothing else."""
    return _CONTROLS.sub("", _ESCAPES.sub("", output.replace("\r\n", "\n").replace("\r", "\n")))


def regenerate_cards(site):
    """`npm run og` without npm: the same launcher, which finds python3, py or python. Returns (ok, a
    sentence saying why not)."""
    node = shutil.which("node")
    if not node:
        return False, "Node is not available"
    # the generator prints an arrow and a multiplication sign, which the encoding its output gets by default
    # (cp1252 on Windows) may not hold: it is told to write UTF-8, and its output is read as UTF-8
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        code, out, err = _run([node, os.path.join(site, "scripts", "run_og.mjs")], site, CARDS_TIMEOUT, env=env)
    except OSError as e:
        return False, "the generator could not be started: %s" % (e.strerror or e)
    if code is None:
        return False, "the generator took more than %d minutes and was stopped" % (CARDS_TIMEOUT // 60)
    if code == 0:
        return True, ""
    if "Pillow is required" in err + out or "No module named 'PIL'" in err + out:
        return False, PILLOW_MISSING
    lines = [l.strip() for l in _plain(err + "\n" + out).splitlines() if l.strip()]
    return False, (lines[-1] if lines else "it stopped without saying why")[:200]


def run_tests(site, command):
    """(green, what it printed). Green is None when the tests took too long and were stopped: that is
    neither a pass nor a failing check, and the run then ends with a status of its own ("tests-timed-out"). The output is read as UTF-8, which is what Node and Playwright
    write, whatever this computer's own encoding is; a byte that is not UTF-8 is shown as the mark that
    stands for one, and stops nothing."""
    code, out, err = _run(command, site, TEST_TIMEOUT, shell=True)
    if code is None:
        return None, out + "\n" + err
    return code == 0, (out + "\n" + err)


def failing_checks(output):
    """The names of what failed, from Playwright's list reporter ("  1) [chromium] › tests/a.spec.ts:8:5 › name"),
    read past the colours a terminal would show them in. Empty when the output names none in that form: see last_lines."""
    names = []
    for line in _plain(output).splitlines():
        m = re.match(r"^\s*\d+\)\s+\[[^\]]+\]\s+›\s+(.*?)(?:\s+─+)?\s*$", line)
        if m:
            names.append(m.group(1))
    return names[:6]


def last_lines(output):
    """The last lines a command printed, for when its output does not name what failed."""
    return [l.strip()[:200] for l in _plain(output).splitlines() if l.strip()][-6:]


# --- the read-back: what the site reads, asked of the programs that read it --------------------
# _site.set_lines goes by the text of src/config.ts and of the share-card generator, and a rule that reads
# lines can be wrong about what the site reads. So the report's word on those two files rests on this: once
# they are written, the site's own Node imports src/config.ts and says what SITE.themeColor and COMPANY.logo
# are, and Python loads the generator (as a module, so that it draws nothing) and says what the colours'
# names are bound to. Each program answers in one line of JSON that starts with a mark made for this run (the
# file may print lines of its own, before and after), and ends the process as soon as it has printed it. An
# answer that has arrived counts, also where the process then did not end in time and was stopped (Node still
# runs the file's `exit` listeners). Node is also asked before anything is written, where set_lines refuses
# src/config.ts as it stands: see _set_config.

_ASK_NODE = """
import { pathToFileURL } from 'node:url';
const [file, mark] = process.argv.slice(1);
// (what JSON cannot carry is sent as JavaScript writes it: NaN after `SITE.themeColor++`, say)
const shown = (value) => (value === undefined || value === null ? null : ['string', 'boolean', 'object'].includes(typeof value) || Number.isFinite(value) ? value : String(value));
let said;
try {
  const m = await import(pathToFileURL(file).href);
  said = { read: { themeColor: shown(m.SITE?.themeColor), logo: shown(m.COMPANY?.logo) } };
} catch (e) {
  said = { code: String((e && e.code) || ''), why: String((e && e.message) || e), node: process.version };
}
console.log('\\n' + mark + JSON.stringify(said));
process.exit(0);   // at once: a timer the file left running neither holds the answer back nor prints after it
"""
_ASK_PYTHON = """
import importlib.util, json, os, sys
sys.dont_write_bytecode = True   # nothing is written into the site: no __pycache__ beside the file
path, mark, names = sys.argv[1], sys.argv[2], sys.argv[3:]
out = sys.stdout                 # the answer goes where this was started to write, whatever the file does with sys.stdout
sys.argv = [path]                # as when the file is run: its own name, and none of this script's arguments
sys.path.insert(0, os.path.dirname(path))   # as when the file is run: what stands beside it can be imported
try:
    spec = importlib.util.spec_from_file_location('brand_kit_read_back', path)
    module = sys.modules[spec.name] = importlib.util.module_from_spec(spec)   # known by its name, as a file that is run is
    spec.loader.exec_module(module)
    said = {'read': {}}
    for name in names:
        value = getattr(module, name, None)
        said['read'][name] = list(value) if isinstance(value, (tuple, list)) and all(type(c) is int for c in value) else repr(value)
except SystemExit as e:
    said = {'ended': e.code if type(e.code) is int else 0 if e.code is None else 1, 'why': '' if type(e.code) is int or e.code is None else str(e.code)}
except BaseException as e:
    said = {'why': '%s: %s' % (type(e).__name__, e)}
out.write('\\n' + mark + json.dumps(said) + '\\n')
out.flush()
os._exit(0)   # at once: nothing the file set up to run at the end (atexit, a thread) follows the answer or holds the process
"""


def _answer(printed, mark):
    """What a program answered: the JSON object on the last line it printed that starts with this run's mark,
    wherever that line stands in its output; None when there is no such line, or it is not one."""
    for line in reversed(printed.split("\n")):
        if line.startswith(mark):
            try:
                said = json.loads(line[len(mark):])
            except (ValueError, RecursionError):
                return None
            return said if isinstance(said, dict) else None
    return None


def _first_line(text, site, none="it did not say why"):
    """The first line of what a program said, for a note: with the site's folder written as `.`, so that a long
    path is not what the 200 characters are spent on. Only the folder's full path is taken for it (the path
    from the root, as `install` works it out from the folder it was given, and the same with links followed;
    another spelling of the folder, a relative one say, is left as it stands), where no letter of a longer
    name stands right before or after it; also where it is written as a `file://` address with characters as
    %XX, as Node writes it."""
    for folder in sorted({os.path.realpath(site), os.path.abspath(site)}, key=len, reverse=True):
        spelt = "".join(r"[/\\]" if c in "/\\" else "(?:%s|%s)" % (re.escape(c), "".join("%%%02X" % b for b in os.fsencode(c))) for c in folder)
        text = re.sub(r"(?<![\w.%-])(?:file:///?)?" + spelt + r"(?![\w.%-])", lambda _m: ".", text)
    return ([l.strip() for l in _plain(text).splitlines() if l.strip()] or [none])[0][:200].rstrip(".")


def _unanswered(who, code, errors, site):
    """Why there is no answer from a program that ran and ended: said as that, not as a file it could not load."""
    said = _first_line(errors, site, "")
    return "%s ended without answering (its exit status was %s%s)" % (who, code, ": " + said if said else "")


def _reads_config(site):
    """What the site's own Node reads from src/config.ts: ({"themeColor": ..., "logo": ...}, None), or
    (None, why it could not be asked). Node 22.18 and newer read a TypeScript file as it stands. One before
    that says it does not know the file's own extension (`.ts`; another is a file it could not load), and is
    asked once more with --experimental-strip-types (an existing site may still allow Node from 22.12, which reads
    TypeScript only with that). Where that second asking fails too, its reason is the one given; a Node that
    does not know the flag (before 22.6: it ends with status 9, and one line of its error output is its own
    sentence for that: the program's name, from the line's start and not a blank, `: bad option: `, the
    flag) is said to read no TypeScript. Status 9 without that line is said like any other ending without
    an answer: the file may have ended the program with it."""
    node = shutil.which("node")
    if not node:
        return None, "Node is not installed here, or is not on the path"
    mark, version = "read-back-%s:" % os.urandom(8).hex(), "its version is not known"
    for more in ([], ["--experimental-strip-types"]):
        try:
            code, printed, errors = _run([node] + more + ["--input-type=module", "-e", _ASK_NODE, os.path.join(site, "src", "config.ts"), mark], site, READ_BACK_SECONDS)
        except OSError as e:
            return None, "Node could not be started (%s)" % (e.strerror or e)
        said = _answer(printed, mark)
        if said is None and code is None:
            return None, "Node took more than %d seconds over the file and was stopped" % READ_BACK_SECONDS
        # Node's own sentence on an option it does not know, a line of its own: `<the program as it was started>: bad option: <the option>`
        tail = ": bad option: " + " ".join(more)
        if said is None and more and code == 9 and any(line.endswith(tail) and line[:-len(tail)][:1].strip() for line in errors.replace("\r", "").split("\n")):
            break
        if said is None:
            return None, _unanswered("Node", code, errors, site)
        if isinstance(said.get("read"), dict):
            return said["read"], None
        if said.get("code") != "ERR_UNKNOWN_FILE_EXTENSION" or not str(said.get("why")).startswith('Unknown file extension ".ts" '):
            return None, "Node could not load the file (%s)" % _first_line(str(said.get("why") or ""), site)
        version = str(said.get("node") or version)
    return None, "the Node on this computer (%s) does not read a TypeScript file" % _first_line(version, site)


def _reads_generator(site, names):
    """What Python has the generator's names bound to once the file's own top has run: ({name: [r, g, b], or
    the value as Python writes it}, None), or (None, why it could not be asked). The file is loaded as a
    module under another name than `__main__`, so it draws no card; by the Python that `npm run og` runs it
    with (scripts/run_og.mjs takes the first of python3, py -3 and python that is there)."""
    for name, more in (("python3", []), ("py", ["-3"]), ("python", [])):
        if shutil.which(name):
            python = [shutil.which(name)] + more
            break
    else:
        return None, "no Python was found on the path (python3, py or python)"
    mark = "read-back-%s:" % os.urandom(8).hex()
    try:
        code, printed, errors = _run(python + ["-c", _ASK_PYTHON, os.path.join(site, "scripts", "generate_og_cards.py"), mark] + list(names), site, READ_BACK_SECONDS,
                                     env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    except OSError as e:
        return None, "Python could not be started (%s)" % (e.strerror or e)
    said = _answer(printed, mark)
    if said is None and code is None:
        return None, "Python took more than %d seconds over the file and was stopped" % READ_BACK_SECONDS
    if said is None:
        return None, _unanswered("Python", code, errors, site)
    if isinstance(said.get("read"), dict):
        return said["read"], None
    why = str(said.get("why") or "")
    if "Pillow is required" in why or "No module named 'PIL'" in why:
        return None, PILLOW_MISSING
    if "ended" in said:   # the file's own top ended the program (sys.exit): it was read, and did not get as far as its colours being asked
        return None, "the file ended with status %s while it was loaded%s" % (said["ended"], " (%s)" % _first_line(why, site) if why else "")
    return None, "Python could not load the file (%s)" % _first_line(why, site)


def _as_read(rel, value):
    """A value as one of the two programs read it, in the form the report shows."""
    if rel == _site.GENERATOR:
        return "#%02x%02x%02x" % tuple(value) if isinstance(value, list) and len(value) == 3 and all(0 <= c < 256 for c in value) else str(value)
    return "nothing" if value is None else value if isinstance(value, str) else json.dumps(value)


def read_back(site, wanted):
    """Ask Node and Python what they read from the files this run set values in. `wanted` is {file: {name:
    the value wanted}} for src/config.ts and the generator. Returns {file: {"status": ...}}, the status being
    "ok" (every value is read as wanted, colours compared as colours; a colour of the generator is a tuple or
    a list of three whole numbers), "differs" (with "values": [{"name", "reads", "wanted"}] for each that is
    not), or "not-checked" (with "why": the program could not be asked, or did not answer).

    What this does not show:
    - Each file is asked once, in this run's environment. A value that depends on the build's environment,
      the date or the branch can be another in the built site.
    - The generator is loaded as a module. What its `if __name__ == "__main__":` part does to the names
      afterwards (`globals().update(BG_TOP=...)` there) is not seen, and the cards are drawn with that.
    - A file that sets out to forge the answer can: it is handed the mark with the rest of the arguments.
    - Asking runs the site's own code. What that code writes while it is asked (a config that writes a file
      when it is imported) is the site's doing: this tool neither puts it back nor names it.
    No card is looked at, and nothing is asked a second time under another environment."""
    out = {}
    for rel, want in wanted.items():
        if not want:
            continue
        read, why = _reads_config(site) if rel == _site.CONFIG else _reads_generator(site, list(want))
        if read is None:
            out[rel] = {"status": "not-checked", "why": why}
            continue
        off = []
        for name, value in want.items():
            got = read.get(name)
            same = got == [int(value[i:i + 2], 16) for i in (1, 3, 5)] if rel == _site.GENERATOR else _site._same_colour(got, value) if name == "themeColor" else got == value
            if not same:
                off.append({"name": name, "reads": _as_read(rel, got), "wanted": value})
        out[rel] = {"status": "differs", "values": off} if off else {"status": "ok"}
    return out


def _set_config(site, text, want, where, notes):
    """_site.set_lines for src/config.ts. Where that refuses, the site's own Node is asked first what it reads from the file
    as it stands (before anything is written, in a dry run too: asking only reads). Where that is every value wanted, the
    file is left as it is, with a note; else the refusal stands, and says what Node reads or why it could not be asked.
    Where Node cannot be asked, the one way on that needs no Node is said too: the line shown, written as the block's
    own entry, which the line rule takes as it stands (a key's line that already says the value is never edited).
    Asking runs the site's own config code, as the read-back after writing does; a config that writes a file when it
    is imported writes it, in a dry run too (this tool itself writes nothing then)."""
    try:
        return _site.set_lines(_site.CONFIG, text, want, where)
    except Refusal as r:
        got = read_back(site, {_site.CONFIG: want})[_site.CONFIG]
        if got["status"] != "ok":
            raise Refusal(r.code, " ".join([str(r)] + (["This tool could not ask the site's Node what it reads: %s. Without the site's Node, this tool takes the value only from the line shown above, "
                                                     "written as the block's own entry in a block laid out as the starter lays it out." % got["why"]] if "why" in got else
                                                    ["The site reads %s now." % ("no value" if v["reads"] == "nothing" else v["reads"]) for v in got["values"]])))
    for name, value in want.items():
        where.pop(name, None)   # (no line of the file is the place of the value)
        notes.append("src/config.ts does not set %s.%s as the starter writes it, and the site reads %s there already (this tool asked the site's Node), so this run "
                     "leaves that value as it is" % (_site._CONFIG[name][0], name, value))
    return text, []


def _not_read_back(rel, names, where, why):
    """The one note about a file whose values could not be read back. `names` are the values asked about, `where`
    the lines they stand on: a line is named only where each of them has one (see _site.set_lines)."""
    lines = sorted({where[n] for n in names}) if all(n in where for n in names) else []
    at = "" if not lines else "line %d of " % lines[0] if len(lines) == 1 else "lines %s and %d of " % (", ".join(str(n) for n in lines[:-1]), lines[-1])
    if rel == _site.GENERATOR:
        return "this tool could not check that Python reads the share cards' colours from %s%s, where they are set: %s" % (at, rel, why)
    return "this tool could not check that the site reads %s from %s%s, where %s set: %s" % (" and ".join("`%s`" % n for n in names), at, rel, "it is" if len(names) == 1 else "they are", why)


def _read_differently(rel, off):
    """The one sentence for a value that the site reads otherwise than this run wanted it (the report's next line says
    what was put back)."""
    if rel == _site.GENERATOR:
        return ("%s: Python has %s bound to %s once the file's own top has run (this tool asked Python), not to %s as this run wanted. Set the value in the file "
                "yourself so that Python reads it, then run this again." % (rel, off["name"], off["reads"], off["wanted"]))
    return ("%s: the site reads %s as %s.%s (this tool asked the site's own Node), not %s as this run wanted. Set the value in the file yourself so that the site "
            "reads it, then run this again." % (rel, off["reads"], _site._CONFIG[off["name"]][0], off["name"], off["wanted"]))


class Plan(object):
    """What the run has decided, with nothing yet written."""

    def __init__(self):
        self.wanted = {}      # file -> {name: value} of what this run sets, or finds already set, in src/config.ts and the generator
        self.where = {}       # file -> {name: the number of the line it stands on, where that is known}
        self.texts = {}       # relative path -> (old text, new text)
        self.files = {}       # relative path -> bytes (icons)
        self.asks = []
        self.placeholders = []
        self.copy = None      # (relative path in brand-handoff, bytes) of the package, or None
        self.preview = None   # bytes of the preview sheet, or None
        self.changed_icons = []
        self.background = self.version = None  # what the app icons sit on, and which version of the mark they show
        # Notes about something this run changes read differently before, after, and once it was put back:
        # (as it reads while nothing is written, once it is done, once it was put back, the files it is about)
        self.pending = []


def _aftermath(data):
    """What is true of the site's files after a run that stopped, as lines for the report."""
    left = data.get("not_restored")
    if left:
        return (["Not everything could be put back. These are NOT as they were before this run; look at each of them:"]
                + ["  %s (%s)" % (l["file"], l["why"]) for l in left] + ["Everything else it had written was put back."])
    return ["Everything it had written was put back." if data.get("rolled_back") else "Nothing was written."]


def _changes_lines(changes, how):
    """The colours the palette changes, as lines for the report. `how` says what became of them: "would
    change" (nothing is written yet), "changed", or "would have changed" (the run ended without them)."""
    elsewhere = [c for c in changes if c.startswith(tuple(f + ", " for f in OTHER_FILES))]
    lines = []
    for where, some in ((STYLESHEET, [c for c in changes if c not in elsewhere]), ("the site's other files", elsewhere)):
        if some:
            lines.append("Colours that %s in %s:" % (how, where))
            lines.extend("  " + c for c in some)
    return lines


def _notes_lines(data):
    return ["Note: " + n for n in data["notes"]]


def install(a, out):
    """Everything. `a` has: site, palette, input, pick, mono, with_colours, keep_colours, with_logo,
    accept_colours, accept_low_contrast, replace_icons, test_command, dry_run. Returns (exit code, status,
    data) and appends the report's lines to `out`. Raises nothing it can say in words, a stop from outside
    included: the signals are watched from the first step on, the planning too.

    A dry run does everything a real run does up to the first write, and stops there. So the two can differ
    in one way: after writing, a real run asks Node and Python what the site reads (read_back). Where that
    is not what it set, it ends with exit status 1 and everything put back; where it could not ask, it goes
    on and says so in a note that no dry run shows. A dry run writes nothing, so it cannot ask what the
    site reads from what it would write; its report says so.

    Once the run has its outcome (done, a question, a dry run, a refusal, red tests, a stop), the signals
    do nothing any more, and that stays so when this returns: the report is still to be printed, and a
    signal in that moment would end the process after "Done" was decided, with no report or half of one.
    The command line ends right after printing. A caller that goes on living (a test) sets its own
    handlers again."""
    site = os.path.abspath(a.site)
    data = {"written": [], "notes": [], "cards": None, "tests": None, "changes": [], "read_back": {}}
    mine = len(out)   # where this run's lines begin: what the caller had in `out` before is the caller's
    _HOLD.update(depth=0, pending=None, unlisted=False)
    try:
        with _held():   # a signal that comes while the handlers are being set is raised when they all are: here, inside the part that turns a stop into a report
            _HOLD["deaf"] = False
            _watch_signals()
        code, status = _outcome(a, site, out, data)
    except (Interrupted, KeyboardInterrupt) as e:
        _ignore_signals()  # also when the stop did not come through the handler, which sets the flag itself
        name = signal.Signals(e.args[0]).name if isinstance(e, Interrupted) else "SIGINT"
        # said of what was stopped: no more than _proc._stop_all could know
        lines = ["The run was stopped from outside (%s) before it had finished%s" % (name, (
            ". This tool could not read the list of running processes: it stopped the command it had started, with that command's own group, and cannot say whether "
            "anything else the command had started is still running (a preview server, say). Look for one before the next run." if _HOLD["unlisted"] else
            ", and what it had started was stopped with it as far as this tool could find it."))] + _aftermath(data)
        del out[mine:]   # every way the run can end stops listening before it writes its first line, so there is none of this run's; were there one, it would not be true any more
        out.extend(lines + _changes_lines(data["changes"], "would have changed") + _notes_lines(data))
        data["message"] = "\n".join(lines)
        code, status = 2, "rollback-incomplete" if data.get("not_restored") else "stopped"
    _ignore_signals()
    return code, status, data


def _outcome(a, site, out, data):
    """(exit code, status) of the run, with every way it can end said in the report's lines. Each way
    ignores the signals first and writes its lines after: a stop that comes before is a stop (nothing
    of this report is written yet), and one that comes after changes nothing."""
    def rest():
        return _changes_lines(data["changes"], "would have changed") + _notes_lines(data)
    try:
        code, status, _data = _install(a, site, out, data)
        return code, status
    except Stop as s:
        _ignore_signals()
        out.extend(s.lines)
        if s.code != 3:  # a question lists them itself
            out.extend(rest())
        data.update({"message": "\n".join(s.lines)})
        return s.code, s.status
    except Ask as k:
        _ignore_signals()
        out.append("I need your decision before I go on. Nothing was written.")
        out.append("- " + str(k))
        out.extend("    * " + o for o in k.shown)   # spelled out for the eye; the JSON keeps k.options, which an answer is matched against
        if k.code != "colours-too":  # that question is about them, and lists them as what it asks
            out.extend(_changes_lines(data["changes"], "would change"))
        out.extend(_notes_lines(data))
        data["asks"] = [{"code": k.code, "question": str(k), "options": k.options}]
        return 3, "needs-decision"
    except Refusal as r:
        _ignore_signals()
        out.append(str(r))
        out.extend(_aftermath(data) + rest())
        data.update({"code": r.code, "message": str(r)})
        return 2, "rollback-incomplete" if data.get("not_restored") else "refused"
    except OSError as e:
        # a file or folder that could not be read or written, or a program that could not be started
        _ignore_signals()
        message = "The run had to stop: %s." % ("%s could not be read or written (%s)" % (e.filename, e.strerror or e) if e.filename else (e.strerror or e))
        out.append(message)
        out.extend(_aftermath(data) + rest())
        data.update({"code": "os-error", "message": message})
        return 2, "rollback-incomplete" if data.get("not_restored") else "refused"


def _differences(css, pal):
    """Where a stylesheet, as _palette.read_css read it, does not hold the palette: [(the row and its
    place, what the stylesheet has there or None, what the palette has)]. The Primary and all three
    blocks are compared; a dark row that both dark blocks have alike is named once. The Primary is one
    colour for both themes, kept in the light block: a dark block that sets another is named too."""
    out = []
    if pal.brand and css.brand != pal.brand:
        out.append((_palette.LABEL["brand"], css.brand, pal.brand))
    for theme, block, where in (("light", css.light, "light theme"), ("dark", css.dark, "dark theme"),
                                ("dark", css.dark_media, "dark theme for visitors without JavaScript")):
        for k in _palette.KEYS:
            new = pal.theme(theme).get(k)
            if new is None or block.get(k) == new or (block is css.dark_media and block.get(k) is not None and css.dark.get(k) == block.get(k)):
                continue   # (a row that neither dark block has is named for each: nothing is alike about two rows that are not there)
            out.append(("%s, %s" % (_palette.LABEL[k], where), block.get(k), new))
        if theme == "dark" and pal.brand and block.get("brand") not in (None, pal.brand):
            out.append(("%s, %s" % (_palette.LABEL["brand"], where), block.get("brand"), pal.brand))
    return out


def _css_problems(css):
    """What _palette.read_css could not find or could not read in a stylesheet, as sentences. One that is
    about no block of the three (a rule elsewhere that sets one of the colours) names its own place."""
    return [m if variable is None else "%s in %s: %s" % (variable, _palette.BLOCK.get(block, "a rule outside the three colour blocks"), m) for block, variable, m in css.problems]


def _own_master(master, primary):
    """Whose the installed favicon is: ("ours", the cleaned mark, the colour its line says it is drawn in
    where it was given in `currentColor`, else None, whether its line says that a part of it has that
    colour as its own) when it is this tool's own file, as this tool wrote it; ("changed", None, None,
    False) when it starts with this tool's line and is not as this tool wrote it; ("other", None, None,
    False) when it does not start with that line. Either sign alone shows nothing: a favicon
    somebody wrote by hand may be clean, and one that was edited afterwards still has the line. Line ends
    and a byte order mark in front are not held against it: a checkout that turns the line ends into CRLF,
    or an editor that saves the file with the mark, leaves the file this tool's own."""
    text = master[len(BOM.encode("utf-8")):] if master.startswith(BOM.encode("utf-8")) else master
    text = text.replace(b"\r\n", b"\n")
    line = _MARK_LINE.match(text)
    if not line:
        return "other", None, None, False
    body = text[line.end():]
    try:
        again = _svg.clean_svg(body, current=primary)
    except Refusal:
        return "changed", None, None, False
    if again.text.encode("utf-8") != body:
        return "changed", None, None, False
    return "ours", again, line.group(1).decode("ascii") if line.group(1) else None, bool(line.group(2))


def _given_in_current(source, clean, primary):
    """Whether a mark was given in `currentColor` (cleaned with another colour for it, it is another
    drawing), and whether as it was given it also holds `primary` as a colour of its own (that colour
    is then still among its colours)."""
    try:
        other = _svg.clean_svg(source, current="#000000" if primary != "#000000" else "#ffffff")
    except Refusal:
        # (refused with the other colour only: inside a group painted with `currentColor`, a part sets `color` to this very colour, written out)
        return True, True
    return other.text != clean.text, primary in other.colours


def _sits_on(colours, palette):
    """The background the app icons get under a palette for a mark of these colours, or None when none serves."""
    try:
        return _icons.choose_background([("colour", colours)], _icons.backgrounds(palette)).background
    except Ask:
        return None


def _install(a, site, out, data):
    # --- what she asked for, before anything is read ---------------------------------------
    accepted = _accepted(a.accept_low_contrast)
    if not a.input and (a.pick or a.mono):
        flags = " and ".join(f for f, v in (("--pick", a.pick), ("--mono", a.mono)) if v)
        raise Refusal("bad-argument", "%s can only be used with a package to choose from, and none was given. Give the logo with --input, or leave %s out." % (flags, flags))
    if a.with_colours and a.keep_colours:
        raise Refusal("bad-argument", "--with-colours and --keep-colours ask for opposite things (apply the palette; leave the site's colours as they are). Give one of them.")
    if a.test_command is not None and not a.test_command.strip():
        raise Refusal("bad-argument", "--test-command was given with no command in it. Give the command that shows the site is still green, or leave --test-command out to run "
                                      "the site's own: %s" % DEFAULT_TEST_COMMAND)
    missing = _site.missing_files(site)
    if missing:
        raise Refusal("site-layout", "%s does not look like a site made from the starter: it lacks %s." % (site, ", ".join(missing)))

    # each file this run edits: as it is in the site, and (without a byte order mark) as this run would write it
    raws, texts = {}, {}

    def text(rel):
        if rel not in texts:
            raws[rel] = _read_text(os.path.join(site, *rel.split("/")), rel)
            texts[rel] = _no_bom(raws[rel])
        return texts[rel]
    css = _palette.read_css(text(STYLESHEET))

    # --- the palette, from BRAND.md (or the file she named) ---------------------------------
    notes = data["notes"]
    notes.extend(css.notes)   # what the reading of the stylesheet has to say that stops nothing (a stylesheet it brings in, which nobody read): in every report from here on
    changes = data["changes"]   # filled as each file is looked at, and never emptied: a run that ends half way still lists what it knew
    parsed, state = None, "none"
    brand_path = a.palette or _find_brand_md(site)
    if a.palette and not _is_file(a.palette):
        raise Refusal("no-input", "There is no palette file at %s." % a.palette)
    if brand_path:
        parsed = _palette.parse_tables(_read_text(brand_path))
        has_any = bool(parsed.light or parsed.dark or parsed.brand)
        # a palette the reading names but could not use (its tables under other headings, its colours in a list
        # or in a sentence) is not "no palette": it is one that is not applied, and every report says why
        state = "none" if not has_any and not parsed.problems else ("complete" if not parsed.missing() and not parsed.problems else "partial")
    want_colours = state == "complete" and not a.keep_colours
    if state == "complete" and a.keep_colours:
        notes.append("the palette in %s was not applied (--keep-colours): the site keeps the colours it has" % os.path.basename(brand_path))
    if a.with_colours and not want_colours:
        if state == "partial":
            raise Refusal("palette-incomplete", "\n".join(_palette_trouble(parsed, os.path.basename(brand_path)) + [
                "Fill in or mend what is named here (the assistant can propose values for you to confirm), then run this again."]))
        raise Refusal("palette-missing", "There are no colours to apply: %s." % ("BRAND.md has no filled-in colour rows" if brand_path else "no BRAND.md was found next to the site"))
    if state == "partial" and not want_colours:
        by = [_palette.LABEL[k] for _t, k in parsed.missing()]
        why = _palette_trouble(parsed, os.path.basename(brand_path))
        notes.append("the colours were not changed: %s" % "\n  ".join(
            ["%s does not hold a complete palette (rows not filled in: %s)" % (os.path.basename(brand_path), ", ".join(sorted(set(by))))
             if has_any and by else why[0][0].lower() + why[0][1:].rstrip(".")] + why[1:]))
    pal = parsed if want_colours else palette_from_css(css)
    # The colour that stands for the brand where one colour is wanted (the theme colour, a mark given in `currentColor`):
    # the Primary, or the light theme's Accent where the palette gives none. That is asked of BRAND.md also on a run that
    # goes by the site's own colours: a palette there with no Primary leaves the stylesheet's `--brand` as it was (the
    # starter's black, say), and that leftover is not the palette's Primary. With no palette in BRAND.md to ask, the
    # stylesheet's `--brand` is the Primary.
    brand = None if parsed is not None and not parsed.brand and (parsed.light or parsed.dark) else pal.brand
    primary = brand or pal.light.get("accent")
    low = []
    if want_colours:
        pairs = _palette.matrix(parsed)
        bad = [p for p in pairs if not p.ok]
        if bad:
            lines = [_palette.describe(p) for p in bad] + ["%d of %d pairs pass. Nothing was written." % (len(pairs) - len(bad), len(pairs))]
            raise Stop(1, lines, "contrast-failed")
        if parsed.proposed:
            names = ", ".join(_palette.LABEL[k] if t == "brand" else "%s (%s)" % (_palette.LABEL[k], t) for t, k in sorted(parsed.proposed))
            raise Ask("confirm-proposals", "These colours are still proposals, marked (proposed): %s. Ask the owner to confirm or change each one, take the marks out, then run this again." % names)
        if not pal.brand:
            # (the reading does not say whether the row is not there or stands there empty: this is true of both)
            notes.append("the palette gives no Primary (the row is not there, or holds no colour), so the light theme's Accent (%s) is used as the theme colour" % primary)

    # --- the logo: whether there is one to work with at all -----------------------------------
    master_bytes = _read_bytes(site, MASTER)
    if master_bytes is not None and _site.is_scaffold_default(MASTER, master_bytes):
        master_bytes = None
    if a.with_logo and not a.input and master_bytes is None:
        raise Refusal("logo-missing", "There is no logo to apply: no file was given, and the site has no logo of its own installed yet (%s is the scaffold's placeholder or missing)." % MASTER)
    asked_for_logo = bool(a.input) or a.with_logo   # she asked for the logo's files; a run about colours may still draw them again (below)
    if not want_colours and not asked_for_logo:
        why = ("--keep-colours leaves the palette in %s out" % os.path.basename(brand_path) if state == "complete" else
               "no complete palette was found%s" % (" in " + os.path.basename(brand_path) if brand_path else ""))
        raise Refusal("nothing-to-do", "\n".join(["There is nothing to do: %s, and no logo file was given." % why]
                                                 + (_palette_trouble(parsed, os.path.basename(brand_path)) if state == "partial" else [])))
    if asked_for_logo and not want_colours and css.problems:
        # the logo is held against the site's own colours (which background the app icons sit on, whether the
        # mark shows on each theme's page): with some of them unread, those checks would pass or fail on less
        # than the site has, and say nothing of it
        raise Refusal("site-colours-unread", "\n".join(
            ["The logo is checked against the colours the site has now (the backgrounds it has to show on), and this tool could not read all of them from "
             "src/styles/global.css:"] + _css_problems(css) +
            ["Mend that in the stylesheet (the three colour blocks as the starter writes them, each colour once), then run this again."]))
    # whose the installed favicon is: asked only now, when the colours it is held against are known to be all there
    whose, kept, drawn, own_too = _own_master(master_bytes, primary) if master_bytes is not None else (None, None, None, False)

    # --- the colours, set in memory in all four files that hold one ---------------------------
    # What the palette changes, as she reads it: said in every report from here on, and asked about
    # (below) when she came for the logo and did not say the colours should change too.
    card_colours = want_colours
    # the values this run sets (or finds set) in src/config.ts and the generator, and the lines they stand on: what the
    # read-back asks Node and Python about once the files are written
    wanted, where = {}, {}
    if want_colours:
        low = _site.og_low_contrast(pal)
        changes.extend("%s: %s becomes %s" % (where, old or "a value this tool cannot read", new) for where, old, new in _differences(css, parsed))
        css_new = _site.edit_css(text(STYLESHEET), pal)   # it refuses in the words of the same scan the reading works from: they stand as they are
        # the stylesheet as it would be written, read back: with a rule that sets one of the colours again
        # somewhere else, the site may show something else than the palette, so that is refused too
        after = _palette.read_css(css_new)
        off = _differences(after, pal)
        unread = [m for _block, variable, m in after.problems if variable is None]
        if unread:
            # what the reading says of the block says more than a list of every row in it
            raise Refusal("css-layout", "src/styles/global.css would not carry the palette after the colours were set. %s Nothing in the stylesheet was "
                          "changed." % " ".join(unread))
        if off:
            raise Refusal("css-layout", "src/styles/global.css would not carry the palette after the colours were set: %s. %s Take that out or set the colours "
                          "by hand, then run this again." % ("; ".join("%s would be %s, not %s" % (where, got or "unreadable", want) for where, got, want in off),
                                                           " ".join(_css_problems(after)) or "Something else in the stylesheet sets that again (a second block "
                                                           "of the same kind, say)."))
        texts[STYLESHEET] = css_new
        others = [(_site.CONFIG, {"themeColor": primary}), (_site.MANIFEST, dict(zip(_site.MANIFEST_COLOURS, (primary, pal.light["bg"]))))]
        if low:
            card_colours = False
            notes.append("the share cards keep the colours they have. Their background runs from the dark theme's %s (%s) at the top to its %s (%s) at the "
                         "bottom, and somewhere on the way %s; text needs %s to 1. This is about the cards alone, not the site's own colours. To recolour "
                         "the cards, set the colours in the BRAND block of scripts/generate_og_cards.py by hand" % (
                             _palette.LABEL["surface"], pal.dark["surface"], _palette.LABEL["bg"], pal.dark["bg"],
                             " and ".join("%s %s falls to %s to 1" % (_palette.LABEL[k], h, _colour.shown(r)) for k, h, r in low), _colour.shown(_palette.NEED_TEXT)))
        else:
            others.append((_site.GENERATOR, {name: pal.dark[key] for name, key in _site.OG_COLOURS}))
        refused = None
        for rel, want in others:   # all three are looked at, also after one of them was refused: the report lists every change it could work out
            try:
                texts[rel], changed = (_set_config(site, text(rel), want, where.setdefault(rel, {}), notes) if rel == _site.CONFIG else
                                       _site.set_lines(rel, text(rel), want, where.setdefault(rel, {})))
            except Refusal as r:
                refused = refused or r
                continue
            changes.extend("%s, %s: %s becomes %s" % (rel, name, old, new) for name, old, new in changed)
            if rel != _site.MANIFEST:   # (the manifest is JSON: set_lines reads it back itself)
                wanted[rel] = dict(want)
        if refused is not None:
            raise refused

    # --- what she handed over, read and checked; then, and only then, the question about the colours ---
    # A file that is not there, or will not do, is said before she is asked anything: an answer to the
    # question would not have helped. The question is asked on every run that she asked the logo of,
    # with a file (--input) or without one (--with-logo).
    clean = mono_clean = None
    src_name = src_bytes = None
    source = master_bytes   # what the favicon is drawn from: her file, or the favicon the site has
    if a.input:
        src_bytes, src_path = read_input(a.input)
        mk = _input.mark(_input.load(src_bytes), pick=a.pick, mono=a.mono)
        source = mk.colour
        clean = _svg.clean_svg(mk.colour, current=primary)
        mono_clean = _svg.clean_svg(mk.mono, current=primary) if mk.mono else None
        src_name = _safe_name(src_path)
        if os.path.realpath(src_path).startswith(os.path.realpath(os.path.join(site, HANDOFF)) + os.sep):
            src_name = None  # already kept there
        notes.extend(clean.notes)
    if asked_for_logo and changes and not a.with_colours:
        raise Ask("colours-too", "%s holds a palette that is not what the site shows now, so this run would also change the colours listed here. Should it? "
                  "Run this again with --with-colours to apply the palette together with the logo, or with --keep-colours to leave the site's colours as "
                  "they are and have only the logo done." % os.path.basename(brand_path), list(changes))

    # --- without a file from her: are the icons drawn again from the installed master? --------------
    # When she asks for it (--with-logo), yes. On a run about colours, only when the background the app icons
    # sit on would change, and only from a master that is this tool's own: any other favicon.svg is a file she
    # never handed over, and a run about colours neither judges it nor stops over it. Where the background
    # stays as it is, the logo's files are left alone and nothing is asked about them. Nor does a run about
    # colours stop over the image library: where the icons cannot be drawn, the colours go in and the icons wait.
    # Where the master has no background of its own under the colours the site has now, this tool cannot tell
    # what the installed icons sit on: they were drawn from a one-colour version, or on a background the site
    # has changed since, and it keeps a record of neither. Such icons are left as they are, with a note, and nothing is asked.
    redraw = a.with_logo and not a.input
    renderer = None
    # A mark given in `currentColor` was drawn in that colour as it was on the day, and no run without its package draws it in another.
    # (Where neither a Primary nor an Accent is to be had, there is no colour to name, and the note is not given.)
    if kept is not None and not a.input and primary and drawn not in (None, primary):
        notes.append(KEPT_CURRENT % (drawn, KEPT_FOR[2 if brand and state == "none" else not brand] % primary))
    if master_bytes is not None and want_colours and not asked_for_logo:
        now = palette_from_css(css)
        moves = _icons.backgrounds(pal) != _icons.backgrounds(now)
        if moves and kept is not None:
            was, will = _sits_on(kept.colours, now), _sits_on(kept.colours, pal)
            if was is None:
                moves = False
                notes.append(ONE_COLOUR_ICONS)
            else:
                moves = was != will
        if moves and kept is None:
            notes.append("the icons were left as they are: %s is not %s, so the app icons were not drawn again on the new background. "
                         "To make them again from that file, run this again with --with-logo; to install a logo, give it with --input" % (
                             MASTER, "a file this tool wrote" if whose == "other" else "as this tool wrote it (it starts with this tool's line and was changed since)"))
        elif moves:
            renderer = _render.Renderer(site)
            try:
                renderer.preflight()
                redraw = True
            except Refusal as r:
                notes.append("the icons were left as they are, so the app icons still sit on the background they had: they could not be drawn again here. %s "
                             "That does not hold the colours back. Once it is put right%s, run this again with --with-logo to draw the icons again" % (
                                 str(r).strip().splitlines()[0].rstrip(".:") + ".",
                                 " (in the site's folder: npm install --include=optional)" if r.code == "sharp-missing" else ""))
        if kept is not None and not redraw:
            # The logo's files stay as they are, in the colours they were drawn in. Where the palette drops one of those
            # colours, that is said: nothing is recoloured. (The colour a mark given in `currentColor` is drawn in has the
            # note above, with another way out: said here are the mark's own colours, and a mark with both gets both notes.
            # Where a colour of its own is the very colour the other part is drawn in, the favicon's line says so, and that
            # colour is said here too: the package draws only the other part in another colour.)
            lost = [c for c in _palette.check_mark(kept.colours, pal).outside if c not in _palette.check_mark(kept.colours, now).outside and (c != drawn or own_too)]
            if lost:
                notes.append(KEPT_COLOURS % ("the colour" if len(lost) == 1 else "the colours", ", ".join(lost)))
    want_logo = bool(a.input) or redraw

    plan = Plan()
    plan.wanted, plan.where = wanted, where
    workdir = None
    try:
        with _held():   # a stop between the making of the folder and its name being known here would leave it behind
            workdir = tempfile.mkdtemp(prefix="brand-kit-")
        if want_logo:
            if not a.input:
                clean = kept or _svg.clean_svg(master_bytes, current=primary)
            # COMPANY.logo, by the same rule as the colours' lines: refused here, before anything is drawn
            texts[_site.CONFIG], repointed = _set_config(site, text(_site.CONFIG), {"logo": _site.LOGO_ADDRESS}, where.setdefault(_site.CONFIG, {}), notes)
            wanted.setdefault(_site.CONFIG, {})["logo"] = _site.LOGO_ADDRESS
            for _name, logo_was, _new in repointed:
                plan.pending.append((
                    "COMPANY.logo in src/config.ts points at %s; this run would point it at /images/logo.png, the picture made from this logo, and leave the file it "
                    "points at where it is" % logo_was,
                    "COMPANY.logo in src/config.ts pointed at %s; it now points at /images/logo.png, the picture made from this logo. The file it pointed at is left "
                    "where it is" % logo_was,
                    "COMPANY.logo in src/config.ts points at %s, as before: this run pointed it at /images/logo.png and then put that back" % logo_was,
                    [_site.CONFIG]))
            if renderer is None:
                renderer = _render.Renderer(site)
                renderer.preflight()
            icons = _icons.build(clean, mono_clean, pal, renderer, workdir)
            notes.extend(icons.notes)
            files = dict(icons.files)
            if clean is kept:   # drawn again from this tool's own favicon: its line is written back as it was read
                given, its_own = drawn, own_too
            else:
                in_current, its_own = _given_in_current(source, clean, primary)
                given = primary if in_current else None
            if given and clean is not kept and not want_colours and parsed is not None and not parsed.brand and (parsed.light or parsed.dark):
                notes.append(DRAWN_IN_ACCENT % (given, os.path.basename(brand_path)))
            files[MASTER] = ((MARK_CURRENT_OWN if its_own else MARK_CURRENT) % _colour.parse_colour(given) if given else MARK).encode("utf-8") + files[MASTER]   # (as #rrggbb: the line is read again by the next run)
            # Two questions, two sets of colours. Every colour an installed file paints with is held against
            # the palette. Only the colour version ever stands on the page (the favicon, the logo); the
            # one-colour version sits on the app icons' own background, so its colours are not asked about there.
            # Both versions are held against the same backgrounds: those of `pal`, which is what the pages show when
            # this run is done (the palette it applies, or the colours the site has where it applies none).
            report = _palette.check_mark(icons.visible, pal)
            on_page = _palette.check_mark(clean.colours, pal)
            if report.outside and not a.accept_colours:
                plan.asks.append(Ask("outside-palette", "These colours of the mark are not in the palette: %s. Nothing is recoloured without your say-so. Use the mark as it is "
                                     "(--accept-colours), or ask the tool for the mark in the palette's colours." % ", ".join(report.outside)))
            mono_low = _palette.check_mark(mono_clean.colours, pal).low if mono_clean is not None else {}
            for theme, under in on_page.low.items():
                if theme not in accepted:
                    what = "; ".join("%s is %s to 1" % (c, _colour.shown(r)) for c, r in under)
                    # said of the one-colour version only what was worked out: whether it reaches 3 to 1 on that same background
                    way = ("A one-colour version may read better there: give one with --mono (in a package) to have it checked." if mono_clean is None else
                           "The one-colour version you gave can be used where it sits on that background." if theme not in mono_low else
                           "The one-colour version you gave does not reach 3 to 1 on that background either (%s)."
                           % "; ".join("%s is %s to 1" % (c, _colour.shown(r)) for c, r in mono_low[theme]))
                    plan.asks.append(Ask("low-contrast", "On %s the mark falls under 3 to 1 against the background (%s). %s Accept it as it is (--accept-low-contrast %s), "
                                         "or choose a different mark." % (_theme_label(theme), what, way, theme)))
            for rel, new in files.items():
                current = _read_bytes(site, rel)
                if current is None or current == new:
                    continue
                (plan.placeholders if _site.is_scaffold_default(rel, current) else plan.changed_icons).append(rel)
            if plan.changed_icons and not a.replace_icons:
                plan.asks.append(Ask("replace-icons", "These icon files are already in the site, and are not the scaffold's placeholders: %s. Replace them (--replace-icons)?"
                                     % ", ".join(plan.changed_icons), plan.changed_icons))
            plan.files = files
            plan.background, plan.version = icons.background, icons.version
            plan.preview = _icons.preview(clean.text, clean.view_box, pal, renderer, workdir)
            if src_name:
                plan.copy = (HANDOFF + "/" + _free_name(site, src_name, src_bytes), src_bytes)
            notes.append(NO_EMBLEM)
        if plan.placeholders:
            one = len(plan.placeholders) == 1
            what = "%s %%s the scaffold's placeholder%s (the Astro logo)" % (" and ".join(plan.placeholders), "" if one else "s")
            plan.pending.insert(0, (what % ("is" if one else "are") + ", which this run would replace", what % ("was" if one else "were") + ", now replaced",
                                    what % ("is" if one else "are") + ": this run replaced %s and then put %s back" % (("it", "it") if one else ("them", "them")),
                                    plan.placeholders))
        notes.extend(would for would, _did, _back, _rels in plan.pending)
        # the question comes after every note of what the run would do, so its report says all of it
        if plan.asks:
            lines = ["I need your decision before I go on. Nothing was written."]
            for k in plan.asks:
                lines.append("- " + str(k))
                lines.extend("    * " + o for o in k.shown)
            lines.extend(_changes_lines(changes, "would change"))
            lines.extend(_notes_lines(data))
            data["asks"] = [{"code": k.code, "question": str(k), "options": k.options} for k in plan.asks]
            raise Stop(3, lines, "needs-decision")

        # --- what the run writes, and only that: a file that is already as it should be is left out ---
        for rel in texts:
            bom = raws[rel][:len(raws[rel]) - len(_no_bom(raws[rel]))]   # a byte order mark stays where it was
            if bom + texts[rel] != raws[rel]:
                plan.texts[rel] = (raws[rel], bom + texts[rel])
        if plan.copy or plan.preview:
            gi_old = _read_text(os.path.join(site, ".gitignore"), ".gitignore") if _is_file(os.path.join(site, ".gitignore")) else ""
            ignore_new = _site.add_ignore(gi_old)
            if ignore_new is not None:
                plan.texts[".gitignore"] = (gi_old, ignore_new)
        writes = [(rel, new) for rel, new in plan.files.items() if _read_bytes(site, rel) != new]
        writes += [(rel, new.encode("utf-8")) for rel, (_old, new) in plan.texts.items()]
        if plan.copy and _read_bytes(site, plan.copy[0]) != plan.copy[1]:
            writes.append(plan.copy)
        if plan.preview and _read_bytes(site, HANDOFF + "/preview.png") != plan.preview:
            writes.append((HANDOFF + "/preview.png", plan.preview))
        # the last checks that can be made before the site is touched: every path, and the share cards' folder,
        # every file of which is kept so that it can be put back like any other file
        j = _site.Journal(site)
        for rel, _new in writes:
            j.check(rel)
        j.snapshot_dir(CARDS)
        if a.dry_run:
            would = sorted(rel for rel, _new in writes)
            _ignore_signals()   # the dry run has its outcome: its report is not cut short
            out.append("Dry run: nothing was written. This is what would be written:")
            out.extend("  " + w for w in would)
            if not would:
                out.append("  nothing: every file is already as this run would write it")
            out.append("  then the share-card generator would run again (a dry run does not check that it can)")
            if any(wanted.values()):
                out.append("A real run then asks %s what the site reads from %s: it puts everything back if that is not what it set, and adds a note where it could not ask. "
                           "A dry run writes nothing, so it cannot ask what the site reads from what it would write." % (
                    " and ".join(who for who, rel in (("the site's Node", _site.CONFIG), ("Python", _site.GENERATOR)) if wanted.get(rel)),
                    " and ".join(rel for rel in (_site.CONFIG, _site.GENERATOR) if wanted.get(rel))))
            out.extend(_changes_lines(changes, "would change"))
            out.extend(_notes_lines(data))
            data["written"] = would
            return 0, "dry-run", data

        return _apply(a, site, out, data, plan, j, writes, want_colours, want_logo, card_colours, pal, brand_path)
    finally:
        # However the run got here (done, a question, a refusal, red tests, a stop), it has its outcome: from
        # here on a signal does nothing, so that none cuts short the clearing up and leaves the folder behind.
        _ignore_signals()
        if workdir is not None:
            shutil.rmtree(workdir, ignore_errors=True)


def _read_bytes(site, rel):
    """What a file of the site holds, or None when no file of that name is there. Only that is "not
    there": a file that is there and cannot be read raises OSError, which stops the run with the path and
    the reason before anything is written. A folder of that name is no file either; the check of every
    path before the first write refuses it by name. Something that is neither (a pipe, a device) is
    refused here, by name, and never opened: opening one can wait for ever."""
    path = os.path.join(site, *rel.split("/"))
    try:
        kind = os.stat(path).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return None
    if stat.S_ISDIR(kind):
        return None
    if not stat.S_ISREG(kind):
        raise Refusal("site-path", "%s is neither a file nor a folder (a pipe or a device, say), so it is not read. Take it out of the site, then run this again." % rel)
    try:
        with open(path, "rb") as f:
            return f.read()
    except (FileNotFoundError, NotADirectoryError):
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


def _apply(a, site, out, data, plan, j, writes, want_colours, want_logo, card_colours, pal, brand_path):
    notes = data["notes"]
    changes = data["changes"]

    def reword(index, left=()):
        """The notes about what this run changes, said as it now is: done (1) or put back (2). One about a
        file that could not be put back stays as it reads for a change that was made."""
        for forms in plan.pending:
            for form in forms[:3]:
                if form in notes:
                    notes[notes.index(form)] = forms[1] if index == 1 or set(forms[3]) & {rel for rel, _why in left} else forms[2]
                    break

    def undo():
        """Put everything back, note in `data` what is then true of the site, and return what could not be
        put back. It can be asked again (after the tests were run a second time): a file that is as it was
        is left alone, and what is said is what is true after the last time."""
        left = j.rollback()
        data["rolled_back"] = bool(j.undone or left)
        data["written"] = []
        data.pop("not_restored", None)
        if left:
            data["not_restored"] = [{"file": rel, "why": why} for rel, why in left]
        if data["rolled_back"]:
            reword(2, left)
        if any(rel == CARDS or rel.startswith(CARDS + "/") for rel, _why in left):
            data["cards"] = "not-restored"   # whatever the generator did or did not do before
        elif data["cards"] in ("regenerated", "not-restored"):
            data["cards"] = "restored"
        return left

    try:
        for rel, new in writes:
            j.write(rel, new)

        # what the site reads from the files as they now are (see read_back): asked before the site's tests are run
        data["read_back"] = checked = read_back(site, plan.wanted)
        differ = [_read_differently(rel, off) for rel, got in checked.items() for off in got.get("values", ())]
        if differ:
            left = undo()
            raise Stop(1, ["A check failed after the files were written: what the site reads is not what this run set."] + differ + _aftermath(data),
                       "rollback-incomplete" if left else "read-back-failed")
        notes.extend(_not_read_back(rel, list(plan.wanted[rel]), plan.where[rel], got["why"]) for rel, got in checked.items() if got["status"] == "not-checked")

        ok, why = regenerate_cards(site)
        if ok:
            data["cards"] = "regenerated"
        else:
            data["cards"] = "failed"
            data["cards_why"] = why
            if j.restore_dir(CARDS):  # undone below with everything else, which names each card that could not be put back
                raise Refusal("cards-not-restored", "The share-card generator failed (%s), and the share cards could not all be put back as they were before it "
                                                    "ran, so nothing of this run was kept." % why)
        if want_colours:
            after = _palette.read_css(_no_bom(_read_text(os.path.join(site, "src", "styles", "global.css"), STYLESHEET)))
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
            data["tests"] = "timed-out" if green is None else "failed"
            data["failing"] = names
            if green is None:
                data["tests_timed_out"] = True
                lines = ["The site's own tests ran for more than %d minutes after the install and were stopped%%s." % (TEST_TIMEOUT // 60)]
                if names:
                    lines.append("Before they were stopped, %s had failed: %s" % ("this check" if len(names) == 1 else "these checks", "; ".join(names)))
            else:
                lines = ["The site's own tests failed after the install%s."]
                if names:
                    lines.append("The failing check%s: %s" % ("" if len(names) == 1 else "s", "; ".join(names)))
                elif last_lines(output):
                    data["output_tail"] = last_lines(output)
                    lines.append("What the test command printed does not name the failing checks in a form this tool reads. Its last lines: %s. Run it "
                                 "yourself to see all of it: %s" % ("; ".join(data["output_tail"]), command))
                else:
                    lines.append("The test command printed nothing, so it is not known which check failed. Run it yourself to see: %s" % command)
            if green is None:
                lines.append("They were not run a second time with the install taken out again, which could take as long, so it is not known whether they "
                             "pass without it. Run them yourself to see: %s" % command)
            elif not left:
                # what was seen, and no more: nothing here says how the site was before this run, or why
                baseline, _ = run_tests(site, command)
                lines.append("With the install taken out again, the same tests pass." if baseline else
                             "With the install taken out again, the same tests ran for more than %d minutes and were stopped." % (TEST_TIMEOUT // 60)
                             if baseline is None else "With the install taken out again, the same tests still fail.")
                left = undo()   # the second run may have written to the site as the first did (the share cards, say): put back once more
            else:
                lines.append("They were not run a second time with the install taken out again, because not everything could be put back.")
            lines[0] %= "" if left else ", so everything was put back (every file, the share cards included)"
            if left:
                lines.extend(_aftermath(data))
            raise Stop(1, lines, "rollback-incomplete" if left else "tests-timed-out" if green is None else "tests-failed")
        data["tests"] = "passed"
        # From here the install stands, and a stop can no longer take it back: it is not listened to while
        # the report is made and printed, so that no report says "stopped, nothing was written" of an install that is in.
        _ignore_signals()
    except Stop:
        raise
    except BaseException:
        _ignore_signals()  # nothing stops the putting back half way, nor the report that follows it
        undo()
        raise

    data["written"] = sorted(set(j.written))
    reword(1)
    out.append("Done. The site's own tests pass afterwards.")
    read = {rel: got["status"] == "ok" for rel, got in data["read_back"].items()}   # what Node and Python read back as this run set it
    if want_colours:
        # the theme colour and the share cards are claimed only where the read-back said so: one that could not
        # be made has its own note, and the value is named here as written and not checked
        in_cards = card_colours and data["cards"] == "regenerated"
        out.append("Colours: the palette in %s is now in src/styles/global.css (the light theme, the dark theme, and the dark values for visitors without JavaScript), "
                   "%s the manifest%s%s%s" % (os.path.basename(brand_path), "in the theme colour and" if read.get(_site.CONFIG) else "and in",
                                              ", and in the share cards." if in_cards and read.get(_site.GENERATOR) else "." if in_cards else ". The share cards do not have it: see below.",
                                              "" if read.get(_site.CONFIG) else
                                              " The theme colour is written in src/config.ts, and this tool could not check that the site reads it from there: see the note about it.",
                                              "" if not in_cards or read.get(_site.GENERATOR) else
                                              " The share cards were made again with their colours set in scripts/generate_og_cards.py, and this tool could not check that Python "
                                              "reads them from there: see the note about it."))
        out.extend(_changes_lines(changes, "changed"))
    if want_logo:
        out.append("Logo: the seven icon files are in public/ (the app icons sit on %s, drawn from the %s version)%s" % (
            plan.background, plan.version, ", and COMPANY.logo points at public/images/logo.png." if read.get(_site.CONFIG) else
            ". COMPANY.logo is written in src/config.ts, and this tool could not check that the site reads it from there: see the note about it."))
    out.append("Written:")
    out.extend("  " + w for w in data["written"])
    if not data["written"]:
        out.append("  nothing: every file was already as this run writes it")
    if data["cards"] == "regenerated":
        out.append("  the share cards under %s, made again" % CARDS)
    out.extend(_notes_lines(data))
    if data["cards"] == "regenerated":
        out.append("Share cards: regenerated%s." % (" with the new colours" if card_colours else " in the colours they had"))
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
