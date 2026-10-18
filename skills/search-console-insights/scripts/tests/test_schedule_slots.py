"""schedule_tracking.sh — each site's weekly job starts in its own minute.

Why: every job used to start Mondays at 09:00. With several sites, their AI checks ran at the
same moment and the providers refused the extra connections: on 2026-10-12 all three of one
owner's runs ended "AI check: exit 1" from Anthropic and Perplexity HTTP 429. So install gives
a new site the first free slot (:00, :15, :30, :45) at its day and hour, and re-installing a
site (to change its keywords, say) keeps the slot it has, including one the owner set by hand,
unless another site's job has that slot too: then it moves, so sites installed before this
change, all at :00, spread out as each is re-installed.

This runs the real install and remove commands, as a user does, with HOME in a temp folder
(so nothing touches the real ~/Library/LaunchAgents) and a stand-in launchctl that loads
nothing. Off macOS there is no plutil, so a small stand-in reads the plist with plistlib.

Run:  python3 -m unittest discover -s skills/search-console-insights/scripts/tests
"""
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent

# Only what the script asks of plutil: `plutil -extract <key.path> raw -o - <file>`.
PLUTIL_STANDIN = f"""#!{sys.executable}
import plistlib, sys
_, key, _, _, _, path = sys.argv[1:]
try:
    v = plistlib.load(open(path, "rb"))
    for k in key.split("."):
        v = v[int(k)] if isinstance(v, list) else v[k]
except Exception:
    sys.exit(1)
print(str(v).lower() if isinstance(v, bool) else v)
"""


class StartSlots(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        shims = self.home / "bin"
        shims.mkdir()
        (shims / "launchctl").write_text("#!/bin/sh\nexit 0\n")
        (shims / "launchctl").chmod(0o755)
        if shutil.which("plutil") is None:
            (shims / "plutil").write_text(PLUTIL_STANDIN)
            (shims / "plutil").chmod(0o755)
        self.env = {"HOME": str(self.home), "PATH": f"{shims}:{os.environ.get('PATH', '/usr/bin:/bin')}"}
        self.agents = self.home / "Library/LaunchAgents"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, *args):
        r = subprocess.run(["/bin/bash", str(SCRIPTS / "schedule_tracking.sh"), *args],
                           env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def install(self, domain, *when):
        return self.run_cmd("install", domain, "k", *when)

    def old_plists(self, *label_minutes):
        """Plists that install did not write, as after a hand edit."""
        self.agents.mkdir(parents=True, exist_ok=True)
        for label, minute in label_minutes:
            with open(self.agents / f"com.gsc-insights.{label}.plist", "wb") as f:
                plistlib.dump({"Label": f"com.gsc-insights.{label}",
                               "ProgramArguments": ["/bin/bash", "track.sh", label.replace("-", "."), "k"],
                               "StartCalendarInterval": {"Weekday": 1, "Hour": 9, "Minute": minute}}, f)

    def when(self, domain):
        label = domain.replace(".", "-")
        with open(self.agents / f"com.gsc-insights.{label}.plist", "rb") as f:
            s = plistlib.load(f)["StartCalendarInterval"]
        return s["Weekday"], s["Hour"], s["Minute"]

    def test_sites_on_the_same_day_and_hour_get_their_own_minutes(self):
        sites = ["a.example", "b.example", "c.example", "d.example", "e.example"]
        for d in sites:
            self.install(d)
        self.assertEqual([self.when(d) for d in sites],
                         [(1, 9, 0), (1, 9, 15), (1, 9, 30), (1, 9, 45), (1, 9, 5)])

    def test_the_install_message_names_the_minute(self):
        self.install("a.example")
        self.assertIn("weekday 1 at 9:15.", self.install("b.example"))

    def test_reinstalling_a_site_keeps_its_minute(self):
        """Re-installing used to put a site back to :00, onto another site's slot."""
        self.install("a.example")
        self.install("b.example")
        self.run_cmd("remove", "a.example")
        self.install("b.example")                       # :00 is free now, but b keeps :15
        self.assertEqual(self.when("b.example"), (1, 9, 15))
        self.install("c.example")                       # a new site takes the freed :00
        self.assertEqual(self.when("c.example"), (1, 9, 0))

    def test_a_slot_set_by_hand_is_kept_and_respected(self):
        """The owner staggered jobs by hand."""
        self.old_plists(("old-example", 0), ("hand-example", 15))
        self.install("hand.example")
        self.assertEqual(self.when("hand.example"), (1, 9, 15))
        self.install("new.example")
        self.assertEqual(self.when("new.example"), (1, 9, 30))

    def test_sites_from_before_the_change_spread_out_when_reinstalled(self):
        """Every job installed before this change starts at :00; keeping that would keep the bug."""
        sites = ["a.example", "b.example", "c.example"]
        self.old_plists(*((d.replace(".", "-"), 0) for d in sites))
        for d in sites:
            self.install(d)
        self.assertEqual(sorted(self.when(d)[2] for d in sites), [0, 15, 30])

    def test_a_thirteenth_site_at_one_hour_is_told_to_pick_another(self):
        sites = [f"s{i}.example" for i in range(12)]
        for d in sites:
            self.install(d)
        self.assertEqual(sorted(self.when(d)[2] for d in sites), list(range(0, 60, 5)))
        out = self.install("s12.example")
        self.assertIn("every slot at this day and hour is taken", out)
        self.assertEqual(self.when("s12.example"), (1, 9, 0))

    def test_only_jobs_at_the_same_day_and_hour_take_a_slot(self):
        self.install("a.example", "1", "9")
        self.install("b.example", "1", "10")
        self.install("c.example", "2", "9")
        self.assertEqual([self.when(d)[2] for d in ("b.example", "c.example")], [0, 0])
        self.install("sun.example", "0", "9")
        self.install("sun2.example", "7", "09")         # Sunday is 0 or 7; 09 is 9
        self.assertEqual(self.when("sun2.example"), (7, 9, 15))

    def test_moving_a_site_to_another_hour_finds_a_free_minute_there(self):
        self.install("a.example", "1", "10")
        self.install("b.example", "1", "9")
        self.install("c.example", "1", "9")             # c is at 9:15
        self.install("c.example", "1", "10")            # 10:00 is a's, so c takes 10:15
        self.assertEqual(self.when("c.example"), (1, 10, 15))


if __name__ == "__main__":
    unittest.main()
