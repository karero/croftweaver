"""Tests for scripts/antigravity_release_test.py, entered the way the release runbook calls it.

Each test runs the tool as a program from a small fixture release (its own git repo, zip and
SHA256SUMS) with a stub `agy` first on PATH and HOME set to a fixture folder, so nothing spends
Antigravity credits, needs a network, or reads the runner's real ~/.gemini. The stub replays
events in the shape the real agy 1.4.2 wrote in the 0.32 trial, and for a full run builds the
site the way the scaffold does. Needs git, node and npm.

Run: python3 -m unittest discover -s scripts/tests -p 'test_antigravity*.py'
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import importlib.util
import zipfile

TOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "antigravity_release_test.py")

SKILL_MD = '''# New website (fixture)

3. Skills travel with the repo:
   ```bash
   mkdir -p "$PROJECT_SKILLS_DIR"
   cp -RL "$SKILLS_ROOT"/website-a \\
         "$SKILLS_ROOT"/website-brand-kit \\
         "$PROJECT_SKILLS_DIR"/
   rm -rf "$PROJECT_SKILLS_DIR"/website-brand-kit/scripts/tests
   ```
'''
PACKAGE = {"name": "site", "private": True, "scripts": {
    "build": "node -e \"0\"",
    "test": "node -e \"process.exit(require('fs').existsSync('FAIL') ? 1 : 0)\""}}
HELPERS = ("export const PAGES = [\n  '/',\n  '/impressum',  // non-DE/AT/CH sites delete it\n"
           "  // '/about',\n] as const;\nexport const THEMES = ['light', 'dark'];\n")

STUB = r'''#!/usr/bin/env python3
import json, os, shutil, sys
log = os.environ["STUB_LOG"]
with open(log, "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
args = sys.argv[1:]
if args == ["--version"]:
    print("1.4.2"); sys.exit(0)
if args[:2] == ["-p", "/usage"]:
    print("Gemini Models\tWeekly Limit Remaining\t90%\t2026-10-31T00:00:00Z"); sys.exit(0)
scenario = os.environ["STUB_SCENARIO"]
turns = [json.loads(l) for l in sys.stdin if l.strip()]
ws = os.getcwd()
skill = os.path.join(ws, ".agents", "skills", "new-website", "SKILL.md")
step = [0]
def emit(ev):
    print(json.dumps(ev), flush=True)
def tool(name, params, state="DONE", output="", error=None):
    step[0] += 1
    info = {"name": name, "parameters": params, "output": output}
    if error:
        info["error"] = {"type": "TOOL_ERROR", "message": error}
    emit({"event": "step_update", "step_update": {"conversation_id": "c1", "step_index": step[0],
          "state": state, "step_type": "tool", "tool_name": name, "tool_info": info}})
def result(status, response="", error=None):
    r = {"conversation_id": "c1", "status": status, "response": response,
         "usage": {"total_tokens": 1000 * (step[0] + 1)}}
    if error:
        r["error"] = error
    emit({"event": "result", "result": r})
emit({"event": "init", "conversation_id": "c1"})
if scenario == "not_run":
    result("ERROR", error="Your AI credits balance is too low to continue."); sys.exit(3)
if scenario != "reply_only":
    tool("view_file", {"AbsolutePath": skill})
if scenario == "global_read":
    tool("view_file", {"AbsolutePath": os.path.join(os.environ["HOME"], ".gemini", "config", "skills", "new-website", "SKILL.md")})
if scenario == "error_after_tool":
    result("ERROR", error="model error"); sys.exit(3)
reply = ("I loaded %s. Is this your websites folder? 1. Pages: what does the sitemap look like? "
         "2. Server: Tier 1 static or more? 3. Who edits content, CMS or not? 4. Language? "
         "5. Analytics? 6. Domain and publish model?" % skill)
if scenario == "secret":
    reply += " token ghp_" + "a" * 30
if scenario == "one_question":
    reply = "Is %s your websites folder? First question: what pages should the site have?" % ws
result("SUCCESS", reply)
if len(turns) == 1:
    sys.exit(7 if scenario == "exit7" else 0)
# full run: scaffold the site as new-website section 3 does
site = os.path.join(ws, "linden-bakery")
tpl = os.path.join(ws, ".agents", "skills", "new-website", "templates")
os.makedirs(os.path.join(site, ".agents", "skills"))
import subprocess
subprocess.run(["git", "init", "-q", site], check=True)
for f in (".gitignore", "SETUP.md", "PUBLISHING.md", "AGENTS.md", "CLAUDE.md"):
    shutil.copy(os.path.join(tpl, f), site)
names = ["website-a", "website-brand-kit"]
if scenario == "missing_skill":
    names.remove("website-a")
for n in names:
    shutil.copytree(os.path.join(ws, ".agents", "skills", n), os.path.join(site, ".agents", "skills", n))
shutil.rmtree(os.path.join(site, ".agents", "skills", "website-brand-kit", "scripts", "tests"))
for f in ("package.json", "playwright.config.ts"):
    shutil.copy(os.path.join(tpl, "astro", f), site)
shutil.copytree(os.path.join(tpl, "astro", "tests"), os.path.join(site, "tests"))
with open(os.path.join(site, "tests", "_helpers.ts")) as f:
    helpers = f.read().replace("  '/',\n", "  '/',\n  '/about',\n")
if scenario == "drop_impressum":
    helpers = "\n".join(l for l in helpers.split("\n") if "/impressum" not in l)
with open(os.path.join(site, "tests", "_helpers.ts"), "w") as f:
    f.write(helpers)
if scenario == "tamper":
    p = json.load(open(os.path.join(site, "package.json")))
    p["scripts"]["test"] = "true"
    json.dump(p, open(os.path.join(site, "package.json"), "w"))
if scenario == "npm_fail":
    open(os.path.join(site, "FAIL"), "w").close()
if scenario == "stray":
    open(os.path.join(ws, "package.json"), "w").close()
tool("run_command", {"CommandLine": 'cp -RL "$SKILLS_ROOT"/website-a "$PROJECT_SKILLS_DIR"/'})
tool("run_command", {"CommandLine": "git commit -m init"}, "ERROR", error="Permission denied for unsandboxed(git commit -m init). Matches user-configured deny rule.")
first = "  1 failed\n  2 passed (1.0s)" if scenario == "first_fail" else "  3 passed (1.0s)"
tool("run_command", {"CommandLine": "npm test"}, output=first)
if scenario == "first_fail":
    tool("run_command", {"CommandLine": "npm test"}, output="  3 passed (1.0s)")
result("SUCCESS", "Site at %s. Nothing failed." % site)
result("SUCCESS", "Done.")
'''


def sh(*cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True).stdout.decode().strip()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


HAVE_TOOLS = bool(shutil.which("git") and shutil.which("npm") and shutil.which("node"))
if not HAVE_TOOLS and os.environ.get("REQUIRE_AGY_TEST_TOOLS"):
    raise SystemExit("git, node and npm are required here (REQUIRE_AGY_TEST_TOOLS is set)")


class RealTranscript(unittest.TestCase):
    """The checks read events in the shape agy 1.4.2 really wrote: an excerpt of the 0.32 trial."""

    def setUp(self):
        spec = importlib.util.spec_from_file_location("agytest", TOOL)
        self.t = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.t)
        here = os.path.dirname(os.path.abspath(__file__))
        self.results, self.tools = self.t.parse(os.path.join(here, "fixtures", "agy-1.4.2-excerpt.ndjson"))

    def test_the_trial_reads_as_it_happened(self):
        self.assertEqual([r.get("status") for r in self.results], ["SUCCESS"] * 3)
        ok, _ = self.t.check_discovery(self.results, self.tools, "/W/websites/.agents/skills/new-website/SKILL.md")
        self.assertTrue(ok, "agy read the workspace copy")
        self.assertTrue(self.t.check_interview(self.results)[0])
        ok, detail = self.t.first_npm_test(self.tools)
        self.assertFalse(ok, "the trial's first npm test failed on robots.txt")
        self.assertIn("1 failed", detail)
        self.assertEqual(self.t.workarounds(self.tools), [], "a deny-rule refusal is not a workaround")


class Checks(unittest.TestCase):
    """The checks on their own, for the cases a stubbed run makes awkward."""

    def setUp(self):
        spec = importlib.util.spec_from_file_location("agytest", TOOL)
        self.t = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.t)

    @staticmethod
    def cmd(line, state="DONE", output="", error=None):
        info = {"parameters": {"CommandLine": line}, "output": output}
        if error:
            info["error"] = {"message": error}
        return {"tool_name": "run_command", "state": state, "tool_info": info}

    def test_first_npm_test_skips_a_deny_refusal(self):
        refused = self.cmd("cd site && npm test", "ERROR", error="Matches user-configured deny rule.")
        self.assertTrue(self.t.first_npm_test([refused, self.cmd("npm test", output="3 passed")])[0])

    def test_first_npm_test_sees_a_command_on_its_own_line(self):
        ok, detail = self.t.first_npm_test([self.cmd("cd site\nnpm test", output="1 failed\n2 passed")])
        self.assertFalse(ok)
        self.assertIn("1 failed", detail)

    def test_an_unfinished_first_npm_test_is_not_green(self):
        self.assertFalse(self.t.first_npm_test([self.cmd("npm test", "RUNNING"), self.cmd("npm test", output="3 passed")])[0])

    def test_no_passes_is_not_green(self):
        self.assertFalse(self.t.first_npm_test([self.cmd("npm test", output="0 passed")])[0])

    def test_a_folder_question_alone_does_not_start_the_interview(self):
        r = [{"status": "SUCCESS", "response": "I loaded the skill and can build static pages. Is this your websites folder?"}]
        self.assertFalse(self.t.check_interview(r)[0])

    def test_pages_entries_must_stay_as_written(self):
        tpl = "export const PAGES = [\n  '/',\n  '/impressum',  // delete it outside DE\n  // '/about',\n] as const;"
        self.assertEqual(self.t.required_pages(tpl), ["'/',"])
        for site in ("export const PAGES = [\n  '/' + 'x',\n] as const;", "export const PAGES = [\n  /* '/', */\n] as const;"):
            self.assertNotIn("'/',", self.t.pages_lines(site))


@unittest.skipUnless(HAVE_TOOLS, "needs git, node and npm")
class ReleaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="agy-release-test.")
        cls.repo = os.path.join(cls.tmp, "repo")
        r = cls.repo
        os.makedirs(os.path.join(r, "scripts"))
        shutil.copy(TOOL, os.path.join(r, "scripts"))
        nw = os.path.join(r, "skills", "new-website")
        write(os.path.join(nw, "SKILL.md"), SKILL_MD)
        for f in (".gitignore", "SETUP.md", "PUBLISHING.md", "AGENTS.md", "CLAUDE.md"):
            write(os.path.join(nw, "templates", f), "fixture %s\n" % f)
        astro = os.path.join(nw, "templates", "astro")
        write(os.path.join(astro, "package.json"), json.dumps(PACKAGE, indent=2) + "\n")
        write(os.path.join(astro, "playwright.config.ts"), "export default {};\n")
        write(os.path.join(astro, "tests", "a.spec.ts"), "// a fixture spec\n")
        write(os.path.join(astro, "tests", "_helpers.ts"), HELPERS)
        write(os.path.join(r, "skills", "website-a", "SKILL.md"), "# a\n")
        write(os.path.join(r, "skills", "website-brand-kit", "SKILL.md"), "# brand kit\n")
        write(os.path.join(r, "skills", "website-brand-kit", "scripts", "tests", "big.txt"), "suite tests\n")
        write(os.path.join(r, "skills", "other", "SKILL.md"), "# other\n")
        g = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]
        sh("git", "init", "-q", "-b", "main", cwd=r)
        sh(*g, "add", "-A", cwd=r)
        sh(*g, "commit", "-qm", "base", cwd=r)
        sh("git", "tag", "v0.1", cwd=r)
        write(os.path.join(r, "skills", "other", "SKILL.md"), "# other, changed\n")
        sh(*g, "commit", "-qam", "unwatched change", cwd=r)
        sh("git", "tag", "v0.2", cwd=r)
        write(os.path.join(nw, "SKILL.md"), SKILL_MD + "\nA watched change.\n")
        sh(*g, "commit", "-qam", "watched change", cwd=r)
        cls.head = sh("git", "rev-parse", "HEAD", cwd=r)
        cls.bin = os.path.join(cls.tmp, "bin")
        write(os.path.join(cls.bin, "agy"), STUB)
        os.chmod(os.path.join(cls.bin, "agy"), 0o755)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.case = tempfile.mkdtemp(dir=self.tmp)
        self.home = os.path.join(self.case, "home")
        write(os.path.join(self.home, ".gemini", "antigravity-cli", "settings.json"),
              json.dumps({"permissions": {"deny": ["command(git commit)", "command(rm)"]}}))
        self.log = os.path.join(self.case, "agy-calls.log")
        open(self.log, "w").close()

    def zip_of(self, rev):
        """A release zip of skills/ at rev, with SHA256SUMS beside it, as `make package` leaves them."""
        dist = os.path.join(self.case, "dist-" + rev)
        os.makedirs(dist)
        raw = subprocess.run(["git", "archive", rev, "skills"], cwd=self.repo, check=True, capture_output=True).stdout
        zpath = os.path.join(dist, "croftweaver.zip")
        with tarfile.open(fileobj=io.BytesIO(raw)) as t, zipfile.ZipFile(zpath, "w") as z:
            for m in t.getmembers():
                if m.isfile():
                    z.writestr(m.name, t.extractfile(m).read())
        with open(zpath, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        write(os.path.join(dist, "SHA256SUMS"), "%s  croftweaver.zip\n" % digest)
        return zpath

    def run_tool(self, *extra, scenario="short_pass", rev=None, zip_path=None):
        rev = rev or self.head
        self.out = os.path.join(self.case, "out")
        env = dict(os.environ, HOME=self.home, PATH=self.bin + os.pathsep + os.environ["PATH"],
                   STUB_LOG=self.log, STUB_SCENARIO=scenario, npm_config_audit="false",
                   npm_config_fund="false", npm_config_update_notifier="false")
        cmd = [sys.executable, "-I", os.path.join(self.repo, "scripts", "antigravity_release_test.py"),
               "--zip", zip_path or self.zip_of(rev), "--sha", rev, "--out", self.out] + list(extra)
        p = subprocess.run(cmd, env=env, capture_output=True, timeout=600)
        self.stdout, self.stderr = p.stdout.decode(), p.stderr.decode()
        return p.returncode

    def calls(self):
        with open(self.log) as f:
            return [json.loads(l) for l in f if l.strip()]

    def report(self):
        with open(os.path.join(self.out, "REPORT.md")) as f:
            return f.read()

    def credited(self, depth, scenario):
        return self.run_tool("--" + depth, "--yes-spend-agy-credits", scenario=scenario)

    # --- before any spend (S3, S7)

    def test_no_mode_flag_refuses_without_calling_agy(self):
        self.assertEqual(self.run_tool("--short"), 2, self.stderr)
        self.assertEqual(self.calls(), [])

    def test_dry_run_picks_short_when_no_watched_file_changed(self):
        self.assertEqual(self.run_tool("--auto", "--since", "v0.1", "--dry-run", rev="v0.2"), 0, self.stderr)
        self.assertIn("depth: short", self.stdout)
        self.assertIn("deny rules: git commit denied, rm denied", self.stdout)
        self.assertEqual(self.calls(), [["--version"]], "a dry run may only ask agy its version")

    def test_dry_run_picks_full_when_new_website_changed(self):
        self.assertEqual(self.run_tool("--auto", "--since", "v0.2", "--dry-run"), 0, self.stderr)
        self.assertIn("depth: full", self.stdout)

    def test_zip_not_matching_sha256sums_is_exit_4(self):
        z = self.zip_of(self.head)
        write(os.path.join(os.path.dirname(z), "SHA256SUMS"), "%s  croftweaver.zip\n" % ("0" * 64))
        self.assertEqual(self.run_tool("--short", "--yes-spend-agy-credits", zip_path=z), 4, self.stderr)
        self.assertEqual(self.calls(), [])

    def test_zip_from_another_commit_is_exit_4(self):
        z = self.zip_of("v0.2")
        self.assertEqual(self.run_tool("--short", "--yes-spend-agy-credits", zip_path=z), 4, self.stderr)
        self.assertIn("not skills/ at", self.stderr)

    def test_a_running_test_blocks_a_second(self):
        os.makedirs(os.path.join(self.home, ".croftweaver-agy-test.lock"))
        self.assertEqual(self.credited("short", "short_pass"), 2, self.stderr)
        self.assertNotIn("stream-json", json.dumps(self.calls()))

    # --- the short check (S1, S4, S5)

    def test_short_check_passes_in_the_sandbox_and_cleans_up(self):
        self.assertEqual(self.credited("short", "short_pass"), 0, self.stderr + self.stdout)
        run = [c for c in self.calls() if "stream-json" in c][0]
        self.assertIn("--sandbox", run)
        self.assertIn("--dangerously-skip-permissions", run)
        rep = self.report()
        self.assertIn("2. Discovery (sees new-website):   PASS", rep)
        self.assertIn("5. Scaffold cp paths (no errors):  not run (short check)", rep)
        self.assertIn("Allowance before: Gemini Models", rep)
        self.assertTrue(os.path.isfile(os.path.join(self.out, "transcript.ndjson")))
        self.assertEqual([d for d in os.listdir(self.home) if d.startswith("Croftweaver-agy-test.")], [],
                         "a passing run deletes its test folder")

    def test_reading_the_global_copy_fails_discovery(self):
        self.assertEqual(self.credited("short", "global_read"), 1, self.stdout)
        self.assertIn("2. Discovery (sees new-website):   FAIL", self.report())

    def test_a_path_only_named_in_the_reply_is_not_a_read(self):
        self.assertEqual(self.credited("short", "reply_only"), 1, self.stdout)
        self.assertIn("no successful read of the workspace copy", self.report())

    def test_an_interview_that_starts_with_one_question_passes(self):
        self.assertEqual(self.credited("short", "one_question"), 0, self.stdout)

    def test_agy_failing_after_its_turns_is_a_failure(self):
        self.assertEqual(self.credited("short", "exit7"), 1, self.stdout)
        self.assertIn("exit 7", self.report())

    def test_no_turn_and_no_tool_is_not_run(self):
        self.assertEqual(self.credited("short", "not_run"), 3, self.stdout)
        self.assertIn("credits balance is too low", self.report())

    def test_an_error_after_a_tool_step_is_a_failure_not_not_run(self):
        self.assertEqual(self.credited("short", "error_after_tool"), 1, self.stdout)
        self.assertIn("agy stopped after 0 of 1 turns", self.report())

    def test_a_possible_secret_stops_the_copy(self):
        self.assertEqual(self.credited("short", "secret"), 2, self.stdout)
        self.assertFalse(os.path.exists(self.out) and os.listdir(self.out), "nothing may reach --out")

    # --- the full test (S2, S6, S8, S9)

    def test_full_test_passes_and_marks_the_commit_untested(self):
        self.assertEqual(self.credited("full", "full_pass"), 0, self.stdout + self.stderr)
        rep = self.report()
        self.assertIn("5. Scaffold cp paths (no errors):  PASS — 2 skills checked", rep)
        self.assertIn("6. Generated site build + tests:   PASS", rep)
        self.assertIn("Green from the first try:       PASS", rep)
        self.assertIn("not tested (deny rule: git commit)", rep)
        self.assertNotIn("git commit -m init", rep, "a deny-rule refusal is not a failed command")
        run = [c for c in self.calls() if "stream-json" in c][0]
        self.assertNotIn("--sandbox", run, "the full test runs unsandboxed: a real site's npm install needs the network")

    def test_a_first_npm_test_that_failed_fails_even_when_repaired(self):
        self.assertEqual(self.credited("full", "first_fail"), 1, self.stdout)
        self.assertIn("Green from the first try:       FAIL", self.report())

    def test_weakened_test_script_is_not_trusted(self):
        self.assertEqual(self.credited("full", "tamper"), 5, self.stdout)
        self.assertIn("NOT TRUSTED — agy changed: package.json scripts", self.report())

    def test_failing_site_tests_fail_the_run(self):
        self.assertEqual(self.credited("full", "npm_fail"), 1, self.stdout)
        rep = self.report()
        self.assertIn("6. Generated site build + tests:   FAIL — npm test exit 1", rep)
        kept = [d for d in os.listdir(self.home) if d.startswith("Croftweaver-agy-test.")]
        self.assertEqual(len(kept), 1, "a failed run keeps its test folder")

    def test_files_written_beside_the_site_fail_the_scaffold(self):
        self.assertEqual(self.credited("full", "stray"), 1, self.stdout)
        self.assertIn("not one new folder", self.report())

    def test_dropping_a_page_the_template_marks_deletable_is_allowed(self):
        self.assertEqual(self.credited("full", "drop_impressum"), 0, self.stdout)

    def test_a_skill_left_out_of_the_copy_fails_the_scaffold(self):
        self.assertEqual(self.credited("full", "missing_skill"), 1, self.stdout)
        self.assertIn("website-a not copied", self.report())


if __name__ == "__main__":
    unittest.main()
