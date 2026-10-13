"""_install.py: put a palette and a logo into a site, or stop and say why.

Order matters, and it is the point of this file. Everything that can be checked is checked, and every
file is built in memory or in a temporary folder, BEFORE the site is touched: the palette's contrast, the
mark's safety and colours, the sharp preflight, the seven icons, each edit. Where the owner must decide
something (a colour outside the palette, a mark that vanishes on a theme, an icon that is not a
placeholder), it asks and writes nothing. Only then does it write, through a journal. If the site's own
tests are red afterwards, the journal puts every file back and the report names the failing check.

Two parts, each from her own material or the assistant's: the palette (BRAND.md, the stylesheet, the
theme colour, the manifest's colours, the share cards' colours) and the logo (the seven icon files and
COMPANY.logo). A part she has no material for stays as the site has it. The share cards' emblem (the
generator's LOGO line) is not set here: a logo run says so and names the skill that does it. Standard
library only.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import time

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
GRACE = 5   # seconds a command and what it started get to clear up after themselves once they are told to stop, before they are killed
MAX_TEXT = 1024 * 1024
CARDS = "public/images/og"
HANDOFF = "brand-handoff"
MASTER = "public/favicon.svg"
# The first line of the favicon this tool installs, and how a later run knows the file as its own: a favicon
# that somebody wrote by hand may be a cleaned SVG too, so that alone does not show who wrote it.
MARK = "<!-- Installed by the website-brand-kit skill (brand_intake.py install) from the logo it was given. When the site's colours change, the icons are drawn again from this file. -->\n"
BOM = "﻿"
STYLESHEET = "src/styles/global.css"
OTHER_FILES = (_site.CONFIG, _site.MANIFEST, _site.GENERATOR)  # the colours' other three homes
PILLOW_MISSING = "Pillow, the image library the generator draws with, is not installed"
NO_EMBLEM = ("the share cards get no emblem from this tool (the logo, shown faintly on each card): it leaves the LOGO line in scripts/generate_og_cards.py exactly as it is. "
             "The og-images skill says how to put the logo on the cards")


class Stop(Exception):
    """Not an error in the program: the run ends here with this exit status and these lines."""

    def __init__(self, code, lines, status):
        super().__init__("\n".join(lines))
        self.code, self.lines, self.status = code, lines, status


class Interrupted(BaseException):
    """The run was told to stop from outside (SIGTERM, SIGHUP, or Ctrl-C's SIGINT). A BaseException, as
    KeyboardInterrupt is, so that nothing between the signal and the rollback takes it for an ordinary error."""


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

SIGNALS = ("SIGTERM", "SIGHUP", "SIGINT")  # Windows has no SIGHUP
_HOLD = {"depth": 0, "pending": None}


class _held(object):
    """A few lines during which a stop from outside is kept back, and raised as soon as they are over: the
    lines that make something (a temporary folder, a process) and only then have a name for it, and the
    lines that stop what a command started. A stop in the middle of those would leave something behind
    that nothing knows of. Outside a run that watches the signals this changes nothing."""

    def __enter__(self):
        _HOLD["depth"] += 1

    def __exit__(self, kind, _value, _trace):
        _HOLD["depth"] -= 1
        if not _HOLD["depth"] and _HOLD["pending"] is not None and kind is None:
            signum, _HOLD["pending"] = _HOLD["pending"], None
            _ignore_signals()
            raise Interrupted(signum)


def _watch_signals():
    """From here on a SIGTERM, a SIGHUP or a Ctrl-C raises Interrupted inside the run, which then puts
    back what it wrote and says so, instead of the process ending with the site half installed or with a
    traceback. One stop is enough: from the first signal on, all of them are ignored until the process
    ends, so that a second one cuts short neither the putting back nor the report. A signal that was
    already being ignored (a run started with nohup ignores SIGHUP) is left ignored."""
    _HOLD.update(depth=0, pending=None)

    def stop(signum, _frame):
        if _HOLD["depth"]:
            _HOLD["pending"] = signum   # raised when the lines that must not be cut short are over
            return
        _ignore_signals()
        raise Interrupted(signum)
    for name in SIGNALS:
        sig = getattr(signal, name, None)
        try:
            if sig is not None and signal.getsignal(sig) != signal.SIG_IGN:
                signal.signal(sig, stop)
        except (ValueError, OSError):
            pass  # not the main thread, where no signal arrives anyway


def _ignore_signals():
    for name in SIGNALS:
        try:
            signal.signal(getattr(signal, name), signal.SIG_IGN)
        except (AttributeError, ValueError, OSError):
            pass


# --- running a command, and stopping everything it started --------------------------------------

def _listing():
    """What is running, as far as `ps` says: {process id: (its parent, its group, when it started)},
    processes that have ended and only wait to be collected left out. None where `ps` cannot be asked
    (Windows; a system whose `ps` does not know these columns)."""
    try:
        r = subprocess.run(["ps", "-Ao", "pid=,ppid=,pgid=,stat=,lstart="], capture_output=True, text=True, errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    table = {}
    for line in r.stdout.splitlines():
        parts = line.split(None, 4)
        if len(parts) >= 4 and all(v.isdigit() for v in parts[:3]) and not parts[3].startswith("Z"):
            table[int(parts[0])] = (int(parts[1]), int(parts[2]), parts[4].strip() if len(parts) > 4 else "")
    return table or None


def _wait(p, timeout):
    """Wait until a command has ended, or `timeout` seconds are over: whether it ended. Where the system
    can, the command is looked at without being collected (os.waitid with WNOWAIT), so that its process
    id, which is also the number of its group, stays its own until _stop_all has stopped the group. Where
    it cannot (Windows; macOS before Python 3.13, which has no os.waitid there), the command is collected
    here. That leaves a moment, between this and the stop that follows at once, in which the system could
    hand the number to a new process: _stop_all then signals the group only when `ps` shows a process in
    it, so a number that went to nobody, or to a process in somebody else's group, is not touched. One
    that went to a process which made itself the leader of a new group within that moment would be, and
    that cannot be closed from here."""
    waitid = getattr(os, "waitid", None)
    if waitid is None or not hasattr(os, "WNOWAIT"):
        try:
            p.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            return False
    end, pause = time.monotonic() + timeout, 0.0005
    while True:
        try:
            if waitid(os.P_PID, p.pid, os.WEXITED | os.WNOWAIT | os.WNOHANG) is not None:
                return True
        except ChildProcessError:
            return True
        left = end - time.monotonic()
        if left <= 0:
            return False
        pause = min(pause * 2, left, 0.05)
        time.sleep(pause)


def _stop_all(p):
    """Stop everything a command started that is still running, whether the command itself has ended or
    not, and collect the command. In two steps, so that what was started can clear up after itself
    (Playwright stops the preview server it started when it is told to end, and a server that is killed
    with it keeps the site's port): first everything is asked to end (SIGTERM), then, after GRACE seconds
    at most, what is still there is killed.

    What is reached, on macOS and Linux: every process in the command's own group (it is started in a
    group of its own, and what it starts stays there unless it leaves on purpose); and every process that
    descends from the command by parent at the moment the stopping begins, wherever it has moved (a
    preview server started in a session of its own is still its starter's child). A process outside the
    group is signalled by its own number, and only while `ps` shows that number with the same start time.

    What is not reached: a process that left the group AND whose parent had already ended when the
    stopping began (a program that makes itself a daemon; a child in a session of its own whose starter
    ended without stopping it). Nothing ties such a process to this run any more. On Windows only what
    the command started while it still runs is reached (taskkill with /T), all at once; once the command
    has ended there, nothing can be asked about what it left."""
    if os.name != "posix":
        if p.poll() is None:
            try:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
            except OSError:
                pass
            try:
                p.kill()
            except OSError:
                pass
        p.wait()
        return

    table = _listing()
    family, todo = {}, [p.pid]
    while todo and table:   # everything that descends from the command, noted before anything is stopped: afterwards the parents are gone
        parent = todo.pop()
        for pid, (its_parent, _group, started) in table.items():
            if its_parent == parent and pid not in family:
                family[pid] = started
                todo.append(pid)

    def running(now):
        return {pid: group for pid, (_parent, group, started) in now.items() if group == p.pid or family.get(pid) == started}

    def tell(sig, pids):
        if pids is None or p.pid in pids.values():   # somebody is in the group (or `ps` cannot say): the group as a whole
            try:
                os.killpg(p.pid, sig)
            except OSError:
                pass
        for pid, group in (pids or {}).items():
            if group != p.pid:
                try:
                    os.kill(pid, sig)
                except OSError:
                    pass

    def gone():
        """Whether nothing of it is left, when `ps` cannot say: the group is asked instead."""
        p.poll()
        try:
            os.killpg(p.pid, 0)
            return False
        except OSError:
            return True

    pids = running(table) if table else None
    if pids != {}:
        tell(signal.SIGTERM, pids)
        end = time.monotonic() + GRACE
        while time.monotonic() < end:
            time.sleep(0.05)
            now = _listing() if table else None
            pids = running(now) if now else None
            if pids == {} or (pids is None and gone()):
                break
        if pids != {} and not (pids is None and gone()):
            tell(signal.SIGKILL, pids)
            end = time.monotonic() + GRACE   # killed is not gone at once: nothing of it may still be writing when the files are put back
            while time.monotonic() < end:
                time.sleep(0.05)
                now = _listing() if table else None
                if (running(now) == {}) if now else gone():
                    break
    p.wait()


def _run(command, cwd, timeout, shell=False, env=None, encoding="utf-8"):
    """Run a command and wait for it: (its exit status, what it printed, its error output). The status
    is None when it took longer than `timeout` seconds. The wait is for the command itself: its output
    goes to two temporary files, not to pipes, so that something it left running and that still holds
    the output open (a preview server) does not keep this waiting. However the wait ends (the command is
    done, the timeout, Ctrl-C, a signal), what the command started is stopped with it (see _stop_all), so
    that none of it is still running when the site's files are put back or the tests are run a second
    time; only then is the output read."""
    group = {"start_new_session": True} if os.name == "posix" else {}
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        p = None
        try:
            with _held():   # a stop between the start of the command and its name being known here would leave it running
                p = subprocess.Popen(command, shell=shell, cwd=cwd, env=env, stdout=out, stderr=err, **group)
            ended = _wait(p, timeout)
        finally:
            if p is not None:
                with _held():   # the stopping is not cut short either; a stop that comes meanwhile is raised when it is done
                    _stop_all(p)
        printed = []
        for f in (out, err):
            f.seek(0)
            printed.append(f.read().decode(encoding or "utf-8", "replace"))
        return (p.returncode if ended else None), printed[0], printed[1]


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
    neither a pass nor a failing check. The output is read as UTF-8, which is what Node and Playwright
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


class Plan(object):
    """What the run has decided, with nothing yet written."""

    def __init__(self):
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

    Once the run has its outcome (done, a question, a dry run, a refusal, red tests, a stop), the signals
    are ignored, and they stay ignored when this returns: the report is still to be printed, and a signal
    in that moment would end the process after "Done" was decided, with no report or half of one. The
    command line ends right after printing. A caller that goes on living (a test) sets its own handlers
    again."""
    site = os.path.abspath(a.site)
    data = {"written": [], "notes": [], "cards": None, "tests": None, "changes": []}
    _watch_signals()
    try:
        code, status = _outcome(a, site, out, data)
    except (Interrupted, KeyboardInterrupt) as e:
        _ignore_signals()  # also when the stop did not come through the handler, which does this itself
        name = signal.Signals(e.args[0]).name if isinstance(e, Interrupted) else "SIGINT"
        lines = ["The run was stopped from outside (%s) before it had finished, and what it had started was stopped with it." % name] + _aftermath(data)
        del out[:]   # every way the run can end ignores the signals before it writes its first line, so there is none; were there one, it would not be true any more
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
        out.extend("    * " + o for o in k.options)
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
            if new is None or block.get(k) == new or (block is css.dark_media and css.dark.get(k) == block.get(k)):
                continue
            out.append(("%s, %s" % (_palette.LABEL[k], where), block.get(k), new))
        if theme == "dark" and pal.brand and block.get("brand") not in (None, pal.brand):
            out.append(("%s, %s" % (_palette.LABEL["brand"], where), block.get("brand"), pal.brand))
    return out


def _css_problems(css):
    """What _palette.read_css could not find or could not read in a stylesheet, as sentences. One that is
    about no block of the three (a rule elsewhere that sets one of the colours) names its own place."""
    return [m if variable is None else "%s in %s: %s" % (variable, _palette.BLOCK.get(block, "a rule outside the three colour blocks"), m) for block, variable, m in css.problems]


def _own_master(master, primary):
    """Whose the installed favicon is: ("ours", the cleaned mark) when it is this tool's own file, as this
    tool wrote it; ("changed", None) when it starts with this tool's line and is not as this tool wrote
    it; ("other", None) when it does not start with that line. Either sign alone shows nothing: a favicon
    somebody wrote by hand may be clean, and one that was edited afterwards still has the line. Line ends
    are not held against it: a checkout that turns them into CRLF leaves the file this tool's own."""
    text = master.replace(b"\r\n", b"\n")
    if not text.startswith(MARK.encode("utf-8")):
        return "other", None
    body = text[len(MARK.encode("utf-8")):]
    try:
        again = _svg.clean_svg(body, current=primary)
    except Refusal:
        return "changed", None
    return ("ours", again) if again.text.encode("utf-8") == body else ("changed", None)


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
    primary = pal.brand or pal.light.get("accent")
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
    whose, kept = _own_master(master_bytes, primary) if master_bytes is not None else (None, None)
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

    # --- the colours, set in memory in all four files that hold one ---------------------------
    # What the palette changes, as she reads it: said in every report from here on, and asked about
    # (below) when she came for the logo and did not say the colours should change too.
    card_colours = want_colours
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
                texts[rel], changed = _site.set_lines(rel, text(rel), want)
            except Refusal as r:
                refused = refused or r
                continue
            changes.extend("%s, %s: %s becomes %s" % (rel, name, old, new) for name, old, new in changed)
        if refused is not None:
            raise refused

    # --- what she handed over, read and checked; then, and only then, the question about the colours ---
    # A file that is not there, or will not do, is said before she is asked anything: an answer to the
    # question would not have helped. The question is asked on every run that she asked the logo of,
    # with a file (--input) or without one (--with-logo).
    clean = mono_clean = None
    src_name = src_bytes = None
    if a.input:
        src_bytes, src_path = read_input(a.input)
        mk = _input.mark(_input.load(src_bytes), pick=a.pick, mono=a.mono)
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
    redraw = a.with_logo and not a.input
    renderer = None
    if master_bytes is not None and want_colours and not asked_for_logo:
        now = palette_from_css(css)
        moves = _icons.backgrounds(pal) != _icons.backgrounds(now)
        if moves and kept is not None:
            was, will = _sits_on(kept.colours, now), _sits_on(kept.colours, pal)
            moves = was is None or was != will
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
    want_logo = bool(a.input) or redraw

    plan = Plan()
    workdir = None
    try:
        with _held():   # a stop between the making of the folder and its name being known here would leave it behind
            workdir = tempfile.mkdtemp(prefix="brand-kit-")
        if want_logo:
            if not a.input:
                clean = kept or _svg.clean_svg(master_bytes, current=primary)
            # COMPANY.logo, by the same rule as the colours' lines: refused here, before anything is drawn
            texts[_site.CONFIG], repointed = _site.set_lines(_site.CONFIG, text(_site.CONFIG), {"logo": _site.LOGO_ADDRESS})
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
            files[MASTER] = MARK.encode("utf-8") + files[MASTER]
            # Two questions, two sets of colours. Every colour an installed file paints with is held against
            # the palette. Only the colour version ever stands on the page (the favicon, the logo); the
            # one-colour version sits on the app icons' own background, so its colours are not asked about there.
            report = _palette.check_mark(icons.visible, pal)
            on_page = _palette.check_mark(clean.colours, pal)
            if report.outside and not a.accept_colours:
                plan.asks.append(Ask("outside-palette", "These colours of the mark are not in the palette: %s. Nothing is recoloured without your say-so. Use the mark as it is "
                                     "(--accept-colours), or ask the tool for the mark in the palette's colours." % ", ".join(report.outside)))
            for theme, under in on_page.low.items():
                if theme not in accepted:
                    what = "; ".join("%s is %s to 1" % (c, _colour.shown(r)) for c, r in under)
                    plan.asks.append(Ask("low-contrast", "On %s the mark falls under 3 to 1 against the background (%s). %s Accept it as it is (--accept-low-contrast %s), "
                                         "or choose a different mark." % (_theme_label(theme), what,
                                         "Use its one-colour version where it sits on that background." if mono_clean is None else
                                         "The one-colour version you gave can be used where it sits on that background.", theme)))
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
        if plan.asks:
            lines = ["I need your decision before I go on. Nothing was written."]
            for k in plan.asks:
                lines.append("- " + str(k))
                lines.extend("    * " + o for o in k.options)
            lines.extend(_changes_lines(changes, "would change"))
            lines.extend(_notes_lines(data))
            data["asks"] = [{"code": k.code, "question": str(k), "options": k.options} for k in plan.asks]
            raise Stop(3, lines, "needs-decision")
        if plan.placeholders:
            one = len(plan.placeholders) == 1
            what = "%s %%s the scaffold's placeholder%s (the Astro logo)" % (" and ".join(plan.placeholders), "" if one else "s")
            plan.pending.insert(0, (what % ("is" if one else "are") + ", which this run would replace", what % ("was" if one else "were") + ", now replaced",
                                    what % ("is" if one else "are") + ": this run replaced %s and then put %s back" % (("it", "it") if one else ("them", "them")),
                                    plan.placeholders))
        notes.extend(would for would, _did, _back, _rels in plan.pending)

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
            out.append("  the share cards under %s would be made again" % CARDS)
            out.extend(_changes_lines(changes, "would change"))
            out.extend(_notes_lines(data))
            data["written"] = would
            return 0, "dry-run", data

        return _apply(a, site, out, data, plan, j, writes, want_colours, want_logo, card_colours, pal, brand_path)
    finally:
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
            data["tests"] = "failed"
            data["failing"] = names
            if green is None:
                data["tests_timed_out"] = True
                lines = ["The site's own tests ran for more than %d minutes after the install and were stopped%%s." % (TEST_TIMEOUT // 60)]
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
            raise Stop(1, lines, "rollback-incomplete" if left else "tests-failed")
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
    if want_colours:
        out.append("Colours: the palette in %s is now in src/styles/global.css (the light theme, the dark theme, and the dark values for visitors without JavaScript), "
                   "in the theme colour and the manifest%s" % (os.path.basename(brand_path), ", and in the share cards." if card_colours and data["cards"] == "regenerated" else
                                                               ". The share cards do not have it: see below."))
        out.extend(_changes_lines(changes, "changed"))
    if want_logo:
        out.append("Logo: the seven icon files are in public/ (the app icons sit on %s, drawn from the %s version), and COMPANY.logo points at public/images/logo.png." % (
            plan.background, plan.version))
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
