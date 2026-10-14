"""_proc.py: running a command so that a stop from outside can come at any moment.

The install runs the site's own tests and the share-card generator; the renderer runs Node. While any
of them runs, the run may be told to stop (SIGTERM, SIGHUP, SIGQUIT, Ctrl-C): _install.py turns that
into the exception Interrupted, raised wherever the run happens to be. This file holds what must be the
same for every command that is run meanwhile: the few lines during which a stop is kept back (_held),
the wait that a stop cannot leave in a broken state (_wait), and the stopping of everything a command
started (_stop_all). It knows neither the install nor the renderer. Standard library only.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import tempfile
import time

GRACE = 5   # seconds a command and what it started get to clear up after themselves once they are told to stop, before they are killed
POLL = 0.25  # seconds between two looks at what is still running while it is being stopped (each look runs `ps`)
LOOKS = 3   # how often `ps` is asked for one look when it did not end well, before that look does without the list
# What the handler of the watched signals (_install._stop) and the lines below share: how deep the run is in lines
# that must not be cut short, a stop that came meanwhile, and whether a stop still counts. And one word for the
# report: whether the last stopping had to do without the list of processes (see _stop_all), so that no report
# says more was stopped than this file could know.
_HOLD = {"depth": 0, "pending": None, "deaf": False, "unlisted": False}


class Interrupted(BaseException):
    """The run was told to stop from outside (SIGTERM, SIGHUP, SIGQUIT, or Ctrl-C's SIGINT). A BaseException, as
    KeyboardInterrupt is, so that nothing between the signal and the rollback takes it for an ordinary error."""


class _held(object):
    """A few lines during which a stop from outside is kept back, and raised as soon as they are over: the
    lines that make something (a temporary folder, a process) and only then have a name for it, and the
    lines that stop what a command started. A stop in the middle of those would leave something behind
    that nothing knows of. Outside a run that watches the signals this changes nothing."""

    def __enter__(self):
        _HOLD["depth"] += 1

    def __exit__(self, kind, _value, _trace):
        _HOLD["depth"] -= 1
        if not _HOLD["depth"] and _HOLD["pending"] is not None and kind is None and not _HOLD["deaf"]:
            signum, _HOLD["pending"] = _HOLD["pending"], None
            _HOLD["deaf"] = True
            raise Interrupted(signum)


def _listing():
    """What is running, as far as `ps` says: {process id: (its parent, its group, when it started)},
    processes that have ended and only wait to be collected left out. None where `ps` cannot be asked
    (Windows; a system whose `ps` does not know these columns), and where it did not end well: a `ps`
    that was stopped half way has printed a part of the list, and a part of the list is not taken for
    the list.

    `ps` is started in a session of its own. A Ctrl-C in a terminal goes to every process of this
    program's group, and a second one, pressed while the first is being answered, would otherwise end
    the `ps` that the stopping runs: the stopping would then know less than it could. One that still
    did not end well is asked again, LOOKS times in all."""
    apart = {"start_new_session": True} if os.name == "posix" else {}
    for _look in range(LOOKS):
        try:
            r = subprocess.run(["ps", "-Ao", "pid=,ppid=,pgid=,stat=,lstart="], capture_output=True, text=True, errors="replace", timeout=60, **apart)
        except (OSError, subprocess.SubprocessError):
            return None   # no `ps` here, or one that does not come back: asking again would not help
        table = {}
        for line in r.stdout.splitlines() if not r.returncode else ():
            parts = line.split(None, 4)
            if len(parts) >= 4 and all(v.isdigit() for v in parts[:3]) and not parts[3].startswith("Z"):
                table[int(parts[0])] = (int(parts[1]), int(parts[2]), parts[4].strip() if len(parts) > 4 else "")
        if table:
            return table
    return None


def _wait(p, timeout):
    """Wait until a command has ended, or `timeout` seconds are over: whether it ended. Where the system
    can, the command is looked at without being collected (os.waitid with WNOWAIT), so that its process
    id, which is also the number of its group, stays its own until _stop_all has stopped the group. Where
    it cannot (Windows; macOS before Python 3.13, which has no os.waitid there), the command is collected
    here. That leaves a moment, between this and the stop that follows at once, in which the system could
    hand the number to a new process: _stop_all then signals the group only when `ps` shows a process in
    it, so a number that went to nobody, or to a process in somebody else's group, is not touched. One
    that went to a process which made itself the leader of a new group within that moment would be, and
    that cannot be closed from here.

    The waiting is done here, in small sleeps, and never by Popen.wait(timeout): a stop from outside is an
    exception raised wherever the run happens to be, and Popen asks about its process under a lock that
    it takes and only then guards (`if lock.acquire(False): try: ...`). A stop raised between those two
    left the lock taken for good, and the wait that follows the stopping (in _stop_all) then never
    returned: the run hung with its command dead and nothing put back. So where Popen has to be asked,
    the stop is kept back for that moment (_held) and raised right after."""
    waitid = getattr(os, "waitid", None)
    look = waitid is not None and hasattr(os, "WNOWAIT")
    end, pause = time.monotonic() + timeout, 0.0005
    while True:
        if look:
            try:
                if waitid(os.P_PID, p.pid, os.WEXITED | os.WNOWAIT | os.WNOHANG) is not None:
                    return True
            except ChildProcessError:
                return True
        else:
            with _held():
                if p.poll() is not None:
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
    `ps` shows as descending from the command by parent, wherever it has moved (a preview server started
    in a session of its own is still its starter's child). That family is collected again at every look,
    POLL seconds apart, for as long as the stopping lasts: a child that is started while its starter is
    being stopped joins it, is told to end, and is killed with the rest. A process outside the group is
    signalled by its own number, and only while `ps` shows that number with the same start time.

    What is not reached: a process that left the group AND whose parent had already ended when it was
    first looked for. That is a program that makes itself a daemon; a child in a session of its own whose
    starter ended without stopping it before the stopping began; and one that was started in a session of
    its own during the stopping, by a starter that ended before the next look (POLL seconds at most).
    Nothing ties such a process to this run any more. Where `ps` cannot be asked, or did not answer at the
    first look or the last, no more than the command's own group is known to be stopped, and
    _HOLD["unlisted"] says so for the report. On Windows only what the command started while it still runs is reached (taskkill with /T),
    all at once; once the command has ended there, nothing can be asked about what it left."""
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

    family = {}   # every process a look found to descend from the command: {its number: when it started}

    def look():
        """What of it is running now, {process id: its group}; None where the list could not be read.
        A child of the command, or of a process that is in the family and still running, joins the family."""
        table = _listing()
        if table is None:
            return None
        grew = True
        while grew:
            grew = False
            for pid, (parent, _group, started) in table.items():
                if pid not in family and (parent == p.pid or (parent in table and family.get(parent) == table[parent][2])):
                    family[pid] = started
                    grew = True
        return {pid: group for pid, (_parent, group, started) in table.items() if group == p.pid or family.get(pid) == started}

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

    pids = look()
    unlisted = pids is None   # what descended from the command when the stopping began was not seen
    outside = False           # whether the last list that could be read showed any of it outside the command's own group

    def nothing_left():
        # a look that could not be made says nothing of a process outside the group: the group's word is taken only where none was seen
        return pids == {} or (pids is None and not outside and gone())

    for sig in (signal.SIGTERM, signal.SIGKILL):
        if nothing_left():
            break
        told, end = set(), time.monotonic() + GRACE   # (killed is not gone at once: nothing of it may still be writing when the files are put back)
        while True:
            if pids is None:
                if None not in told:
                    told.add(None)
                    tell(sig, None)
            else:
                tell(sig, {pid: group for pid, group in pids.items() if pid not in told})   # at the first look everything; later what has joined since
                told.update(pids)
                outside = any(group != p.pid for group in pids.values())
            if time.monotonic() >= end:
                break
            time.sleep(POLL)
            pids = look()
            if nothing_left():
                break
    _HOLD["unlisted"] = unlisted or pids is None   # said of this stopping, the last one: it is the one a stop from outside ends in
    if p.poll() is None:   # whatever `ps` showed: the command itself is never waited for without an end
        try:
            p.kill()
        except OSError:
            pass
    p.wait()


def _run(command, cwd, timeout, shell=False, env=None, encoding="utf-8", input=None):
    """Run a command and wait for it: (its exit status, what it printed, its error output). The status
    is None when it took longer than `timeout` seconds. The wait is for the command itself: its output
    goes to two temporary files, not to pipes, so that something it left running and that still holds
    the output open (a preview server) does not keep this waiting. `input` is text the command is given
    on its standard input (from a temporary file too; without it the command has this program's own).
    However the wait ends (the command is done, the timeout, Ctrl-C, a signal), what the command started
    is stopped with it (see _stop_all), so that none of it is still running when the site's files are put
    back or the tests are run a second time; only then is the output read."""
    group = {"start_new_session": True} if os.name == "posix" else {}
    with contextlib.ExitStack() as files:   # each file is closed, also one made before a later one could not be
        with _held():   # a stop between the making of a file and its name being taken away would leave the file behind
            out, err, given = [files.enter_context(tempfile.TemporaryFile()) for _ in range(3)]
        if input is not None:
            given.write(input.encode(encoding or "utf-8"))
            given.seek(0)
        p = None
        try:
            with _held():   # a stop between the start of the command and its name being known here would leave it running
                p = subprocess.Popen(command, shell=shell, cwd=cwd, env=env, stdin=given if input is not None else None, stdout=out, stderr=err, **group)
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
