"""One AI check at a time — the lock in geo_check.run() (docs/reviews/SKILL-PLAN-ai-check-lock.md).

Why: when a Mac wakes, launchd starts every weekly job whose time passed during sleep, so several
sites' AI checks start together; on 2026-10-12 their engine calls together hit Anthropic's and
Perplexity's HTTP 429s and every site's AI check failed. The lock makes them take turns. These
tests run the real track.sh under /bin/bash (what the launchd plist runs), as test_track_entry.py
does, with two sites in one HOME so they share the lock. T1 to T6 are the plan's test ids.

Run:  python3 -m unittest discover -s skills/search-console-insights/scripts/tests
"""
import fcntl
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import _geo_stub as stub  # noqa: E402
from test_track_entry import SHIM  # noqa: E402  (only SHIM: importing TrackEntry would run it twice)

SCRIPTS = Path(__file__).resolve().parent.parent
GKEY = "test-gemini-placeholder"
# Both sites read the stub's one homepage, which must name the business, so they share its name;
# their questions (ASCII, as they appear in the JSON request bodies) tell their calls apart.
SITES = {"example-bakery.de": ("Bäckerei Example", "Where can I buy sourdough bread in Schwabing?"),
         "example-pretzels.de": ("Bäckerei Example", "Where can I buy fresh pretzels in Haidhausen?")}
WAITING = "waiting for another AI check run to finish"
RAN_ANYWAY = "for another AI check run, then ran anyway"
UNUSABLE = "could not use the lock that keeps AI checks one at a time"


def stop(proc):
    """A test's cleanup: end a child it started, and reap it."""
    if proc.poll() is None:
        proc.kill()
    proc.wait()


class AiCheckLock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.base = stub.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        stub.reset()
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cfg = self.home / ".config/gsc-insights"
        (self.cfg / "venv/bin").mkdir(parents=True)
        shim = self.cfg / "venv/bin/python"
        shim.write_text(SHIM.replace("@PYTHON@", sys.executable))
        shim.chmod(0o755)
        (self.cfg / ".env").write_text("")
        self.lock_path = self.cfg / "geo/ai-check.lock"
        self.env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.home),
                    "SHIM_LOG": str(self.home / "shim.log"), "GEO_GEMINI_API_KEY": GKEY,
                    **stub.env_for(self.base), "GEO_TEST_MODE": "1"}   # GEO_LOCK_WAIT needs it
        stub.engine_reply("gemini", "Bäckerei Example is the place.")

    def tearDown(self):
        self.tmp.cleanup()

    def geo(self, domain, *args, stdin=None, check=True, timeout=60, **env):
        r = subprocess.run([sys.executable, str(SCRIPTS / "geo_check.py"), domain, *args],
                           env={**self.env, **env}, input=stdin, capture_output=True, text=True,
                           timeout=timeout)
        if check:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def set_up_site(self, domain, question=True):
        name, text = SITES[domain]
        self.geo(domain, "--init", "--name", name, "--lang", "en", "--country", "DE")
        if not question:
            return
        self.geo(domain, "--set-question", "--slot", "broad", "--text-file", "-", stdin=text)
        code = re.search(r"Page code: (\w+)", self.geo(domain, "--check-drift", check=False).stdout).group(1)
        self.geo(domain, "--confirm", "--expect", code)

    def track_cmd(self, domain):
        return ["/bin/bash", str(SCRIPTS / "track.sh"), domain, "sourdough munich"]

    def track(self, domain, **env):
        r = subprocess.run(self.track_cmd(domain), env={**self.env, **env},
                           capture_output=True, text=True, timeout=120)
        return r.returncode, r.stdout + r.stderr

    def hold_lock(self):
        """The test itself holds the lock, as a run that is still asking the engines would."""
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        f = open(self.lock_path, "a")
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.addCleanup(f.close)
        return f

    def engine_spans(self, domain):
        question = SITES[domain][1]
        return [(s, e) for path, body, s, e in stub.STATE["spans"] if question in body]

    def test_t1_two_weekly_jobs_started_together_take_turns(self):
        """The wake case: both sites' track.sh start at the same moment. Every engine call of one
        site must end before the other site's first call starts."""
        for d in SITES:
            self.set_up_site(d)
        # Every engine reply waits for the gate, so the first run to reach the engines holds the
        # lock inside its first call however slowly the other starts: the other must then reach
        # the lock and wait. Only after that are the replies let through.
        gate = stub.STATE["gate"] = threading.Event()
        self.addCleanup(gate.set)
        logs = {d: self.home / f"{d}.log" for d in SITES}
        procs = {}
        for d in SITES:
            with open(logs[d], "w") as out:
                procs[d] = subprocess.Popen(self.track_cmd(d), env=self.env, stdout=out,
                                            stderr=subprocess.STDOUT)
            self.addCleanup(stop, procs[d])
        deadline = time.monotonic() + 30
        while not any(WAITING in f.read_text() for f in logs.values()) and time.monotonic() < deadline:
            time.sleep(0.1)
        gate.set()
        outs = {d: (p.wait(timeout=120), logs[d].read_text())[1] for d, p in procs.items()}
        for d, p in procs.items():
            self.assertEqual(p.returncode, 0, outs[d])
        self.assertEqual(sum(WAITING in o for o in outs.values()), 1, outs)
        a, b = (self.engine_spans(d) for d in SITES)
        self.assertTrue(a and b, "an engine was never asked")
        first, second = (a, b) if min(s for s, _ in a) < min(s for s, _ in b) else (b, a)
        self.assertLessEqual(max(e for _, e in first), min(s for s, _ in second),
                             "the two sites' engine calls overlapped")

    def test_t2_a_wait_that_runs_out_still_asks_and_reports(self):
        """A hung run must not cost every other site its week: the waiter goes ahead and the
        run is listed as needing attention."""
        d = next(iter(SITES))
        self.set_up_site(d)
        self.hold_lock()
        rc, out = self.track(d, GEO_LOCK_WAIT="1")
        self.assertEqual(rc, 1, out)
        self.assertEqual(out.count(RAN_ANYWAY), 1, out)
        self.assertIn("waited 1 s " + RAN_ANYWAY, out)
        self.assertIn("AI check: exit 1", out)
        self.assertIn("This run needs attention", out)
        self.assertTrue(self.engine_spans(d), "the engines were not asked after the wait ran out")

    def test_t3_a_killed_run_leaves_no_lock_behind(self):
        """A crash or a kill must never block next week's runs."""
        d = next(iter(SITES))
        self.set_up_site(d)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        child = subprocess.Popen(
            [sys.executable, "-c", "import fcntl, sys, time; f = open(sys.argv[1], 'a'); "
             "fcntl.flock(f, fcntl.LOCK_EX); print('locked', flush=True); time.sleep(120)",
             str(self.lock_path)], stdout=subprocess.PIPE, text=True)
        self.addCleanup(stop, child)
        self.assertEqual(child.stdout.readline().strip(), "locked")
        with open(self.lock_path, "a") as probe, self.assertRaises(BlockingIOError):
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)      # the child really holds it
        os.kill(child.pid, signal.SIGKILL)
        child.wait(timeout=10)
        child.stdout.close()
        t = time.monotonic()
        rc, out = self.track(d, GEO_LOCK_WAIT="30")
        self.assertEqual(rc, 0, out)
        self.assertNotIn(WAITING, out)
        self.assertLess(time.monotonic() - t, 25, out)

    def test_t4_a_run_that_asks_no_engine_never_waits(self):
        """Only a run that will call an engine waits: the rest have nothing to keep apart."""
        d, other = SITES
        self.hold_lock()
        quick = {"GEO_LOCK_WAIT": "5"}
        r = self.geo(d, check=False, **quick)                     # not set up
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertNotIn(WAITING, r.stdout)
        self.set_up_site(d)
        r = self.geo(d, check=False, GEO_GEMINI_API_KEY="", **quick)   # no key
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("has no engine key", r.stdout)
        self.assertNotIn(WAITING, r.stdout)
        self.set_up_site(other, question=False)                   # no question
        r = self.geo(other, check=False, **quick)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("has no questions yet", r.stdout)
        self.assertNotIn(WAITING, r.stdout)
        # A usable key for gemini, but this run asks only openai, which has none: the gemini key
        # must not make it wait.
        r = self.geo(d, "--engines", "openai", check=False, **quick)
        self.assertIn("openai: skipped", r.stdout)
        self.assertNotIn(WAITING, r.stdout)
        self.assertNotIn(RAN_ANYWAY, r.stdout)
        self.assertFalse(self.engine_spans(d))

    def test_t5_a_lock_file_that_cannot_be_opened_is_reported(self):
        d = next(iter(SITES))
        self.set_up_site(d)
        self.lock_path.mkdir(parents=True)              # open(path, "a") raises IsADirectoryError
        rc, out = self.track(d, GEO_LOCK_WAIT="5")
        self.assertEqual(rc, 1, out)
        self.assertIn(UNUSABLE, out)
        self.assertIn("AI check: exit 1", out)
        self.assertTrue(self.engine_spans(d), "the engines were not asked")

    def test_t6_the_waiting_line_reaches_the_log_while_it_waits(self):
        """Under launchd stdout is the site's log file (StandardOutPath). Whoever reads it during
        the wait must see why the job is idle, not an empty log until it ends."""
        d = next(iter(SITES))
        self.set_up_site(d)
        holder = self.hold_lock()
        log = self.home / "site.log"
        with open(log, "w") as out:
            proc = subprocess.Popen(self.track_cmd(d), env={**self.env, "GEO_LOCK_WAIT": "60"},
                                    stdout=out, stderr=subprocess.STDOUT)
        self.addCleanup(stop, proc)
        deadline = time.monotonic() + 20
        while WAITING not in log.read_text() and time.monotonic() < deadline and proc.poll() is None:
            time.sleep(0.1)
        self.assertIn(WAITING, log.read_text(), "the waiting line was not in the log during the wait")
        self.assertIsNone(proc.poll(), "the run did not wait")
        self.assertFalse(self.engine_spans(d), "the engines were asked while another run held the lock")
        holder.close()                                   # the other run ends
        self.assertEqual(proc.wait(timeout=60), 0, log.read_text())
        text = log.read_text()
        self.assertIn("… waited", text)
        self.assertNotIn(RAN_ANYWAY, text)
        self.assertTrue(self.engine_spans(d))


if __name__ == "__main__":
    unittest.main()
