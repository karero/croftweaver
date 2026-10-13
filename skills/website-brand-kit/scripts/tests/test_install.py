"""Scenarios 8, 16, 19, 21, 26 (the path), 27, 30, 31, 34, 35, 36 to 39 and the rest of 7, 9, 15, 29: the
intake as a whole, through the door the assistant uses (`brand_intake.main`, the same function the
command line calls), on a real copy of the starter.

The site's own tests are stood in for by a command that prints what Playwright prints, so that red can be
made on demand; the one run that uses `npm test` for real is test_e2e_site.py.
"""

import contextlib
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest

import _testutil as T
import brand_intake
import _colour
import _install
import _palette
import _proc
import _render
import _site
import _svg
from test_palette import LABELS, STARTER_DARK, STARTER_LIGHT, table
from test_site_edits import (bakery, tree, advice, shown_line, refusal_in, follow_config, follow_manifest, follow_generator, node_problem,
                             config_as_node_reads_it, manifest_as_node_reads_it, generator_as_python_runs_it, changed_outside_the_block)

GREEN = "true"
# what Playwright's list reporter prints for a failure (octal escapes: every sh's printf reads them)
RED = ("printf '  1) [chromium] \\342\\200\\272 tests/a11y.spec.ts:8:5 \\342\\200\\272 a11y \\342\\200\\224 / [dark] \\342\\224\\200\\342\\224\\200\\n"
       "  2) [chromium] \\342\\200\\272 tests/seo.spec.ts:20:3 \\342\\200\\272 theme colour\\n'; exit 1")
BAKERY_BRAND_MD = (
    "# Bäckerei Example: brand & style guide\n\n## Colour palette\n\n### Brand (fixed, theme-independent)\n"
    "| Token | Hex | Use |\n|---|---|---|\n| Primary | `#b4531a` | buttons, brand surfaces |\n\n"
    "### Light theme\n" + table([(l, T.BAKERY_LIGHT[k]) for k, l in LABELS]) + "\n"
    "### Dark theme\n" + table([(l, T.BAKERY_DARK[k]) for k, l in LABELS]))
# A dark theme that passes all its pairs and still cannot be read on a share card: grey text that reads on
# the white surface and on the black background, and not on the greys the card's gradient runs through.
GREY_DARK = dict(T.BAKERY_DARK, heading="#767676", ink="#767676", muted="#767676", accent="#767676", link="#767676",
                 bg="#000000", bg_soft="#000000", surface="#ffffff")
LOGO_ARGS = ("--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both")
# What `npm test` printed on an installed copy of the starter with public/llms.txt moved away (Playwright
# 1.63, the list reporter the starter configures), 2026-10-12: the lines around the four failures, with the
# folder's path shortened to /site. The first three headings end in a space, the fourth in a rule.
PLAYWRIGHT_RED = "\n".join((
    "  \u2713  68 [chromium] \u203a tests/seo.spec.ts:428:1 \u203a seo \u2014 hosted PDFs carry a descriptive doc-title (1ms)",
    "  \u2718  60 [chromium] \u203a tests/seo.spec.ts:329:1 \u203a robots.txt stays open and llms.txt exists (5ms)",
    "",
    "",
    "  1) [chromium] \u203a tests/llms-coverage.spec.ts:59:1 \u203a every PAGES route is listed in public/llms.txt ",
    "",
    "    Error: ENOENT: no such file or directory, open '/site/public/llms.txt'",
    "",
    "      37 | // is exactly how false positives creep in \u2014 so they don't.",
    "      38 | function linkedPaths(): string[] {",
    "    > 39 |   const txt = readFileSync(join(process.cwd(), 'public', 'llms.txt'), 'utf8');",
    "         |               ^",
    "        at linkedPaths (/site/tests/llms-coverage.spec.ts:39:15)",
    "",
    "    Error Context: test-results/llms-coverage-every-PAGES-route-is-listed-in-public-llms-txt-chromium/error-context.md",
    "",
    "  2) [chromium] \u203a tests/llms-coverage.spec.ts:72:1 \u203a no stale llms.txt entry \u2014 every same-site page link is a PAGES route ",
    "",
    "    Error: ENOENT: no such file or directory, open '/site/public/llms.txt'",
    "",
    "  3) [chromium] \u203a tests/llms-coverage.spec.ts:91:1 \u203a LLMS_EXEMPT routes stay out of public llms.txt ",
    "",
    "    Error: ENOENT: no such file or directory, open '/site/public/llms.txt'",
    "",
    "  4) [chromium] \u203a tests/seo.spec.ts:329:1 \u203a robots.txt stays open and llms.txt exists " + "\u2500" * 14,
    "",
    "    Error: public/llms.txt (the AI answer-engine index) must be served",
    "",
    "    Expected: 200",
    "    Received: 404",
    "",
    "  4 failed",
    "    [chromium] \u203a tests/llms-coverage.spec.ts:59:1 \u203a every PAGES route is listed in public/llms.txt \u2500",
    "    [chromium] \u203a tests/seo.spec.ts:329:1 \u203a robots.txt stays open and llms.txt exists " + "\u2500" * 15,
    "  1 skipped",
    "  63 passed (5.9s)",
    ""))
PLAYWRIGHT_RED_NAMES = ["tests/llms-coverage.spec.ts:59:1 \u203a every PAGES route is listed in public/llms.txt",
                        "tests/llms-coverage.spec.ts:72:1 \u203a no stale llms.txt entry \u2014 every same-site page link is a PAGES route",
                        "tests/llms-coverage.spec.ts:91:1 \u203a LLMS_EXEMPT routes stay out of public llms.txt",
                        "tests/seo.spec.ts:329:1 \u203a robots.txt stays open and llms.txt exists"]


def rects(*shapes):
    """A small SVG of rectangles, each (x, y, width, height, fill), later ones over earlier ones."""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            + "".join('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>' % shape for shape in shapes) + "</svg>").encode("utf-8")


STOP_SIGNALS = [getattr(signal, n) for n in _install.SIGNALS if hasattr(signal, n)]


def follow_read_back(text, sentence, put_back=None):
    """src/config.ts after somebody did what the read-back says of a block that has no line of the key of its own, and
    nothing else: the line it shows, in its characters, as the first line under the block's opening line. `put_back`
    is (a line as it stands now, what it said before) where "that other line" was changed."""
    shown, opening = re.search(r"has no `\w+` of its own: the line that says it belongs to something inside the block\. Write `([^`]+)` as the first line under the block's opening line "
                               r"\(it starts `([^`]+)`\), and where that other line was changed to say \S+, put back what it said before\. Then run this again\.$", sentence).groups()
    lines = text.split("\n")
    if put_back:
        lines[lines.index(put_back[0])] = put_back[1]
    lines.insert(next(i for i, line in enumerate(lines) if line.startswith(opening)) + 1, shown)
    return "\n".join(lines)


def run(*argv):
    """The command line, in this process. An install ends with the stop signals handled and doing nothing,
    as the command line wants them until it has printed its report and ended; a test goes on living, so
    what handled them before is set again here."""
    out = io.StringIO()
    before = [(s, signal.getsignal(s)) for s in STOP_SIGNALS]
    try:
        with contextlib.redirect_stdout(out):
            code = brand_intake.main(list(argv))
    finally:
        for s, handler in before:
            signal.signal(s, handler)
    return code, out.getvalue()


class SiteCase(unittest.TestCase):
    modules = True

    def setUp(self):
        if self.modules:
            T.require_sharp(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.site = T.make_starter_site(os.path.join(self.tmp.name, "site"), with_modules=self.modules)
        self.pack = os.path.join(self.tmp.name, "pack")
        os.makedirs(self.pack)

    def p(self, rel):
        return os.path.join(self.site, *rel.split("/"))

    def read(self, rel):
        return T.read(self.p(rel))

    def bytes(self, rel):
        return T.read_bytes(self.p(rel))

    def exists(self, rel):
        return os.path.exists(self.p(rel))

    def brand_md(self, text=BAKERY_BRAND_MD):
        with open(self.p("BRAND.md"), "w", encoding="utf-8") as f:
            f.write(text)

    def package(self, name="logo.zip", data=None):
        path = os.path.join(self.pack, name)
        with open(path, "wb") as f:
            f.write(data if data is not None else T.real_zip_bytes())
        return path

    def intake(self, *extra, command=GREEN, brand=True):
        if brand and not self.exists("BRAND.md"):
            self.brand_md()
        return run("install", "--site", self.site, "--test-command", command, *extra)

    def snapshot(self):
        return tree(self.site)

    def put(self, rel, data):
        with open(self.p(rel), "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode("utf-8"))

    def not_as_root(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root may read and write anywhere, so nothing can be closed to it")

    def closed(self, rel, mode=0):
        """Close a file or folder of the site to this account until the test is over; returns the mode it had."""
        was = stat.S_IMODE(os.stat(self.p(rel)).st_mode)
        os.chmod(self.p(rel), mode)
        self.addCleanup(lambda: os.path.lexists(self.p(rel)) and os.chmod(self.p(rel), was))
        return was

    def both_runs(self, *extra, **kwargs):
        """A dry run and then a real run of the same command: [(code, what it printed)]. They must agree on
        every refusal, so most tests of one ask both."""
        return [self.intake(*extra, "--dry-run", **kwargs), self.intake(*extra, **kwargs)]

    def links(self):
        """Every link in the site (node_modules aside) with what it points at: a link must stay a link."""
        out = {}
        for base, dirs, files in os.walk(self.site):
            for n in dirs + files:
                if os.path.islink(os.path.join(base, n)) and n != "node_modules":
                    out[os.path.relpath(os.path.join(base, n), self.site)] = os.readlink(os.path.join(base, n))
        return out

    def drive(self, patch, *extra, command=GREEN, ignored=(), tmpdir=None, timeout=180):
        """The whole command line as a process of its own, because a signal ends a process that does not
        catch it. `patch` is Python run before the command line is: it puts a signal at an exact moment.
        The process starts with each signal as a shell would hand it over, or ignored when `ignored` names it."""
        def signals():
            for name in ("SIGINT", "SIGHUP", "SIGTERM", "SIGQUIT"):
                signal.signal(getattr(signal, name), signal.SIG_IGN if name in ignored else signal.SIG_DFL)
        program = "import os, signal, sys\nsys.path.insert(0, %r)\nimport brand_intake, _install, _proc, _render, _site, _icons\n%s\nsys.exit(brand_intake.main(sys.argv[1:]))\n" % (T.SCRIPTS, patch)
        env = dict(os.environ, TMPDIR=tmpdir) if tmpdir else None
        return subprocess.run([sys.executable, "-c", program, "install", "--site", self.site, "--test-command", command] + list(extra),
                              capture_output=True, text=True, encoding="utf-8", timeout=timeout, preexec_fn=signals, env=env)

    def gone(self, pid, wait=5.0):
        """Whether a process has ended (given a moment: one that was killed is not gone at once)."""
        end = time.time() + wait
        while time.time() < end:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            except PermissionError:
                return False
            time.sleep(0.05)
        return False

    def sleeper(self):
        """A command that would run for five minutes, told apart from every other by its length, and a
        way to ask afterwards whether it is still running."""
        length = "300.%06d" % (int.from_bytes(os.urandom(3), "big") % 1000000)

        def running():
            listing = subprocess.run(["ps", "-Ao", "pid=,command="], capture_output=True, text=True).stdout
            return [int(line.split()[0]) for line in listing.splitlines() if line.strip().endswith("sleep " + length)]

        def stop():
            for pid in running():
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
        self.addCleanup(stop)
        return "sleep " + length, running

    def none_left(self, running, wait=5.0):
        end = time.time() + wait
        while running() and time.time() < end:
            time.sleep(0.05)
        return running() == []

    def stop_leftovers(self, pid_file):
        """Tidy up after a test that expects the intake to stop what a command started: whatever it left."""
        if os.path.exists(pid_file):
            for pid in T.read(pid_file).split():
                try:
                    os.kill(int(pid), signal.SIGKILL)
                except OSError:
                    pass


    def need_read_back(self):
        """The read-back asks a Node that reads TypeScript, and a Python that has Pillow (the generator imports
        it). Without them it says "not checked", which has a test of its own."""
        why = node_problem(typescript=True)
        if why and os.environ.get("REQUIRE_SHARP"):
            self.fail("REQUIRE_SHARP is set but the read-back cannot be made: " + why)
        if why:
            self.skipTest(why)
        T.require_pillow(self)

    def old_node(self, with_the_flag):
        """A stand-in `node` in a folder of its own, first on the path until the test is over: asked to import a
        TypeScript file, it answers as a Node before 22.18 does (it does not know the extension). Asked again
        with --experimental-strip-types it does what `with_the_flag` says: "unknown", it ends as a Node before
        22.6 does (it does not know the flag: status 9, and Node's own word, which names the flag); "ends
        with 9", it ends with that status and a word of the file's own (a Node that takes the flag, and a
        config that ended the program); "reads", it hands over to the real Node, as a 22.12 would read the
        file; a list is the lines it writes to its error output before it ends with status 9, whoever is
        to have said them; any other text is the JSON it answers with (a Node that knows the flag and
        still cannot load the file). Everything else goes to the real Node. An answer starts with the mark
        the tool handed over, its last argument. Returns the file it notes each of those calls in."""
        self.path = getattr(self, "path", os.environ["PATH"])   # as it was before the first stand-in: the real Node is found there
        folder, real = tempfile.mkdtemp(dir=self.tmp.name), shutil.which("node", path=self.path)
        asked = os.path.join(folder, "asked")
        flagged = "printf '%%s\\n' %s >&2; exit 9" % " ".join(shlex.quote(line) for line in with_the_flag) if isinstance(with_the_flag, list) else {
            "unknown": "echo 'node: bad option: --experimental-strip-types' >&2; exit 9", "ends with 9": "echo 'no settings for this branch' >&2; exit 9", "reads": "exec '%s' \"$@\"" % real}.get(
            with_the_flag, "printf '\\n%%s%%s\\n' \"$mark\" '%s'; exit 0" % with_the_flag)
        with open(os.path.join(folder, "node"), "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\nfor mark; do :; done\ncase \" $* \" in\n  \" --experimental-strip-types \"*) echo flag >> '%s'; %s ;;\n"
                    "  \" --input-type=module \"*) echo plain >> '%s'; printf '\\n%%s{\"code\":\"ERR_UNKNOWN_FILE_EXTENSION\",\"why\":\"Unknown file extension .ts\",\"node\":\"v20.11.0\"}\\n' \"$mark\"; exit 0 ;;\nesac\nexec '%s' \"$@\"\n"
                    % (asked, flagged, asked, real))
        os.chmod(os.path.join(folder, "node"), 0o755)
        os.environ["PATH"] = folder + os.pathsep + self.path
        self.addCleanup(os.environ.__setitem__, "PATH", self.path)
        return asked

    def begin(self, *extra, patch="", command=GREEN, own_group=False):
        """The command line as a process that is not waited for: brand_intake.command_line, which is all the
        file itself runs, after `patch` (Python that changes a limit of the tool, say). The four signals are
        as a shell hands them over. With `own_group` the process leads a process group of its own, as a
        command started from a terminal does: a Ctrl-C there goes to that whole group."""
        def as_from_a_shell():
            for name in ("SIGINT", "SIGHUP", "SIGTERM", "SIGQUIT"):
                signal.signal(getattr(signal, name), signal.SIG_DFL)
            if own_group:
                os.setsid()
        program = "import os, signal, sys\nsys.path.insert(0, %r)\nimport brand_intake, _install, _proc\n%s\nbrand_intake.command_line(sys.argv[1:])\n" % (T.SCRIPTS, patch)
        return subprocess.Popen([sys.executable, "-c", program, "install", "--site", self.site, "--test-command", command] + list(extra),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", preexec_fn=as_from_a_shell)

    def until(self, there, p, limit=120):
        """Wait until `there()` says yes, for as long as the process `p` runs: whether it came to that."""
        end = time.time() + limit
        while not there() and p.poll() is None and time.time() < end:
            time.sleep(0.005)
        return bool(there())


class OnlyColours(SiteCase):
    """Scenarios 38 and 8: she has a palette and wants no help with a logo."""
    modules = False  # a run with only colours needs no sharp (scenario 19)

    def test_a_dry_run_says_what_it_would_do_and_writes_nothing(self):
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("Dry run", out)
        self.assertIn("src/styles/global.css", out)
        self.assertEqual(self.snapshot(), before)

    def test_the_palette_is_written_everywhere_it_belongs_and_the_logo_things_stay(self):
        T.require_pillow(self)
        og_before = self.bytes("public/images/og/default.jpg")
        config_before = self.read("src/config.ts")
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        css = _palette.read_css(self.read("src/styles/global.css"))
        self.assertEqual((css.light, css.dark, css.dark_media, css.brand), (T.BAKERY_LIGHT, T.BAKERY_DARK, T.BAKERY_DARK, "#b4531a"))
        self.assertIn("themeColor: '#b4531a'", self.read("src/config.ts"))
        manifest = json.loads(self.read("public/manifest.webmanifest"))
        self.assertEqual((manifest["theme_color"], manifest["background_color"]), ("#b4531a", "#fff8ee"))
        self.assertRegex(self.read("scripts/generate_og_cards.py"), r"(?m)^BG_BOT = \(26, 18, 13\)")
        self.assertIn("LOGO = None", self.read("scripts/generate_og_cards.py"))
        self.assertEqual(self.read("src/config.ts").replace("'#b4531a'", "'#000000'"), config_before, "COMPANY.logo is as the starter has it")
        for gone in ("public/favicon.svg", "public/favicon.ico", "public/apple-touch-icon.png", "public/icon-192.png",
                     "public/icon-512.png", "public/icon-maskable-512.png", "public/images/logo.png", "brand-handoff"):
            self.assertFalse(self.exists(gone), gone)
        self.assertNotIn("brand-handoff", self.read(".gitignore"))
        self.assertNotEqual(self.bytes("public/images/og/default.jpg"), og_before, "the share card has the new colours")
        self.assertEqual(self.read("BRAND.md"), BAKERY_BRAND_MD, "BRAND.md is the source; the run leaves it alone")

    def test_the_share_cards_are_real_pictures_at_the_size_the_tests_demand(self):
        T.require_pillow(self)
        self.intake()
        data = self.bytes("public/images/og/default.jpg")
        self.assertEqual(data[:3], b"\xff\xd8\xff")
        self.assertLessEqual(len(data), 300 * 1024)

    def test_the_document_and_the_stylesheet_agree_afterwards(self):
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        css = _palette.read_css(self.read("src/styles/global.css"))
        self.assertEqual(_palette.drift(_palette.parse_tables(self.read("BRAND.md")), css), [])
        self.assertEqual(_palette.dark_blocks_disagree(css), [])

    def test_a_failing_pair_stops_it_before_anything_is_written(self):
        # scenario 7, the second time it is checked: inside the intake
        self.brand_md(BAKERY_BRAND_MD.replace(T.BAKERY_DARK["muted"], "#5c5f80"))
        before = self.snapshot()
        code, out = self.intake()
        self.assertEqual(code, 1, out)
        self.assertIn("FAILS dark: Muted #5c5f80", out)
        self.assertIn("4.5 to 1", out)
        self.assertEqual(self.snapshot(), before)

    def test_proposed_values_stop_it_until_she_has_confirmed_them(self):
        # scenario 9: the intake writes only values she confirmed
        self.brand_md(BAKERY_BRAND_MD.replace("`%s`" % T.BAKERY_DARK["muted"], "`%s (proposed)`" % T.BAKERY_DARK["muted"]))
        before = self.snapshot()
        code, out = self.intake()
        self.assertEqual(code, 3, out)
        self.assertIn("confirm", out.lower())
        self.assertEqual(self.snapshot(), before)

    def test_an_incomplete_palette_is_not_applied_and_asking_for_colours_says_so(self):
        self.brand_md(BAKERY_BRAND_MD.replace("| Soft background | `#fef5e8` |\n", ""))
        before = self.snapshot()
        code, out = self.intake("--with-colours")
        self.assertEqual(code, 2, out)
        self.assertIn("Soft background", out)
        self.assertEqual(self.snapshot(), before)

    def test_with_neither_colours_nor_a_logo_there_is_nothing_to_do_and_it_says_so(self):
        before = self.snapshot()
        code, out = self.intake(brand=False)
        self.assertEqual(code, 2, out)
        self.assertIn("nothing to do", out.lower())
        self.assertEqual(self.snapshot(), before)

    def test_red_tests_put_everything_back_and_name_the_failing_check(self):
        # scenario 31
        T.require_pillow(self)
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake(command=RED)
        self.assertEqual(code, 1, out)
        self.assertEqual(self.snapshot(), before, "every file, the share cards included, is as it was")
        self.assertIn("a11y.spec.ts", out)
        self.assertIn("put back", out)
        # the same suite is red with the install taken out again, and the report says that and no more:
        # it did not see the site before this run, so it does not say how the site was then
        self.assertIn("With the install taken out again, the same tests still fail.", out)
        self.assertNotIn("before this run", out)

    def test_when_the_tests_are_red_with_the_install_and_green_once_it_is_taken_out_the_report_says_what_it_saw_and_blames_nothing(self):
        # a second run that passes shows the tests pass now, not that the install was the cause (a test
        # that fails every other time looks the same)
        self.brand_md()
        marker = os.path.join(self.tmp.name, "ran-once")
        flip = "if [ -e %s ]; then exit 0; else touch %s; printf '  1) [chromium] x tests/a11y.spec.ts\\n'; exit 1; fi" % (marker, marker)
        code, out = self.intake(command=flip)
        self.assertEqual(code, 1, out)
        self.assertIn("With the install taken out again, the same tests pass.", out)
        self.assertNotIn("it was the install", out)

    def test_a_generator_that_fails_leaves_the_old_cards_and_says_what_to_run(self):
        # scenario 35: the generator writes the cards one after another and can stop on a later one
        self.brand_md()
        gen = self.read("scripts/generate_og_cards.py")
        self.assertIn("def main():", gen)
        broken = gen.replace("def main():\n", "def main():\n    (OUT / 'default.jpg').write_bytes(b'half way')\n    raise SystemExit('simulated: a later card failed')\n", 1)
        with open(self.p("scripts/generate_og_cards.py"), "w", encoding="utf-8") as f:
            f.write(broken)
        old = self.bytes("public/images/og/default.jpg")
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.bytes("public/images/og/default.jpg"), old, "the whole folder is restored")
        self.assertIn("still show the old colours", out)
        self.assertIn("npm run og", out)
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT, "the colours themselves are in")

    def test_a_palette_alone_leaves_the_scaffolds_placeholder_icons_where_they_are(self):
        # scenario 38: the placeholder is not a logo, so a run with only colours makes no icons from it
        # (without sharp, as here, it could not; it must not even try)
        placeholder = b"<svg>placeholder</svg>"
        with open(self.p("public/favicon.svg"), "wb") as f:
            f.write(placeholder)
        old = _site.SCAFFOLD_DEFAULTS
        _site.SCAFFOLD_DEFAULTS = {"public/favicon.svg": {hashlib.sha256(placeholder).hexdigest()}}
        try:
            code, out = self.intake()
        finally:
            _site.SCAFFOLD_DEFAULTS = old
        self.assertEqual(code, 0, out)
        self.assertEqual(self.bytes("public/favicon.svg"), placeholder)
        self.assertFalse(self.exists("public/images/logo.png"))
        self.assertIn("LOGO = None", self.read("scripts/generate_og_cards.py"))

    def test_a_palette_that_gives_no_primary_uses_the_accent_as_the_theme_colour_and_says_what_is_true_whether_the_row_is_missing_or_empty(self):
        row = "| Primary | `#b4531a` | buttons, brand surfaces |\n"
        self.assertIn(row, BAKERY_BRAND_MD)
        for name, md in (("no such row", BAKERY_BRAND_MD.replace(row, "")), ("the row is there and empty", BAKERY_BRAND_MD.replace(row, "| Primary | | buttons, brand surfaces |\n")),
                         ("the row still holds the template's placeholder", BAKERY_BRAND_MD.replace(row, "| Primary | `#[hex]` | buttons, brand surfaces |\n"))):
            with self.subTest(name=name):
                for rel in ("src/styles/global.css",) + _install.OTHER_FILES:
                    self.put(rel, T.starter_file(rel))
                self.brand_md(md)
                (dry_code, dry), (code, out) = self.both_runs()
                self.assertEqual((dry_code, code), (0, 0), out)
                for report in (dry, out):
                    self.assertIn("Note: the palette gives no Primary (the row is not there, or holds no colour), so the light theme's Accent (%s) is used as the theme colour"
                                  % T.BAKERY_LIGHT["accent"], report.splitlines())
                    self.assertNotIn("has no Primary row", report, "said of a row that is there, that was untrue")
                self.assertIn("themeColor: '%s'" % T.BAKERY_LIGHT["accent"], self.read("src/config.ts"))

    def test_scenario_29_a_stylesheet_that_does_not_carry_the_palette_in_all_three_places_is_not_kept(self):
        # the check on the file the intake wrote, the last guard after the same check on the planned text:
        # here the writing is broken on purpose, so that what lands in the file is not what was planned.
        # Once it is the block for visitors without JavaScript (which the site's own a11y test never
        # exercises) that keeps an old value, once the Primary.
        self.brand_md()
        before = self.snapshot()
        real = _site.Journal.write
        for name, planned, landed, found in (("the block for visitors without JavaScript", "--bg: %s;" % T.BAKERY_DARK["bg"], "--bg: #0a0b1e;",
                                              "Background, dark theme for visitors without JavaScript is #0a0b1e, not #1a120d"),
                                             ("the Primary", "--brand: #b4531a;", "--brand: #000000;", "Primary is #000000, not #b4531a"),
                                             ("a value that cannot be read", "--brand: #b4531a;", "--brand: bakery-brown;", "--brand in the :root block: The colour 'bakery-brown'")):
            with self.subTest(name=name):
                def broken(journal, rel, data, planned=planned, landed=landed):
                    if rel == "src/styles/global.css":
                        head, found, tail = data.decode("utf-8").rpartition(planned)
                        self.assertTrue(found)
                        data = (head + landed + tail).encode("utf-8")
                    return real(journal, rel, data)
                _site.Journal.write = broken
                try:
                    code, out = self.intake()
                finally:
                    _site.Journal.write = real
                self.assertEqual(code, 2, out)
                self.assertIn("all three places", out)
                self.assertIn(found, out)
                self.assertIn("put back", out)
                self.assertNotIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)

    def test_asking_for_a_logo_when_there_is_none_stops_and_says_so(self):
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--with-logo")
        self.assertEqual(code, 2, out)
        self.assertIn("no logo to apply", out)
        self.assertEqual(self.snapshot(), before)

    def test_a_site_that_is_not_the_starters_layout_is_refused_whole(self):
        self.brand_md()
        with open(self.p("src/styles/global.css"), "w", encoding="utf-8") as f:
            f.write(self.read("src/styles/global.css").replace(':root[data-theme="dark"] {', ":root.night {"))
        before = self.snapshot()
        code, out = self.intake()
        self.assertEqual(code, 2, out)
        self.assertIn("global.css", out)
        self.assertEqual(self.snapshot(), before)

    def test_a_folder_that_is_not_a_site_is_named(self):
        empty = os.path.join(self.tmp.name, "empty")
        os.makedirs(empty)
        code, out = run("install", "--site", empty, "--test-command", GREEN)
        self.assertEqual(code, 2)
        self.assertIn("generate_og_cards.py", out)

    def test_json_for_the_assistant(self):
        T.require_pillow(self)
        self.brand_md()
        code, out = self.intake("--json")
        data = json.loads(out)
        self.assertEqual((data["status"], data["exit"]), ("done", 0))
        self.assertIn("src/styles/global.css", data["written"])
        self.assertEqual(data["tests"], "passed")
        self.assertEqual(data["cards"], "regenerated")
        before = self.snapshot()
        code, out = self.intake("--json", "--dry-run")
        self.assertEqual(json.loads(out)["status"], "dry-run")
        self.assertEqual(self.snapshot(), before)

    # --- what is said -------------------------------------------------------------------------

    def test_every_report_the_dry_run_too_lists_the_stylesheet_values_that_change(self):
        self.brand_md()
        self.assertIn("Primary: #000000 becomes #b4531a", json.loads(self.intake("--json", "--dry-run")[1])["changes"])
        for extra, heading in ((("--dry-run",), "Colours that would change in src/styles/global.css:"), ((), "Colours that changed in src/styles/global.css:")):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 0, out)
                self.assertIn(heading, out)
                for line in ("  Primary: #000000 becomes #b4531a", "  Accent, light theme: #2b50e0 becomes #b4531a", "  Link, light theme: #2b50e0 becomes #a14a14",
                             "  Background, dark theme: #0a0b1e becomes #1a120d"):
                    self.assertIn(line, out.splitlines())
                self.assertNotIn("without JavaScript: #", out, "a dark row that both dark blocks have alike is named once")
        code, out = self.intake("--json")
        self.assertEqual(json.loads(out)["changes"], [], "and a second run changes no value")

    def test_a_dark_value_that_only_the_block_for_visitors_without_javascript_has_differently_is_named_for_that_block(self):
        self.brand_md()
        head, sep, media = self.read("src/styles/global.css").partition("@media (prefers-color-scheme: dark)")
        self.put("src/styles/global.css", head + sep + media.replace("--muted: #a6abce;", "--muted: #999999;", 1))
        code, out = self.intake("--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("  Muted, dark theme: #a6abce becomes #c4ae98", out.splitlines())
        self.assertIn("  Muted, dark theme for visitors without JavaScript: #999999 becomes #c4ae98", out.splitlines())

    def test_when_the_generator_fails_the_report_does_not_say_the_palette_is_in_the_share_cards_and_names_pillow_only_when_that_is_what_is_missing(self):
        T.require_pillow(self)   # without it every failure here would be the missing library
        self.brand_md()
        gen = self.read("scripts/generate_og_cards.py")
        for name, said, pillow in (("the library is missing", "Pillow is required: pip3 install Pillow  (one-time, local only)", True),
                                   ("something else", "simulated: a title is too long", False)):
            with self.subTest(name=name):
                self.put("scripts/generate_og_cards.py", gen.replace("def main():\n", "def main():\n    raise SystemExit(%r)\n" % said, 1))
                code, out = self.intake()
                self.assertEqual(code, 0, out)
                self.assertIn("in the theme colour and the manifest. The share cards do not have it: see below.", out)
                self.assertNotIn("and in the share cards", out)
                self.assertIn("still show the old colours", out)
                self.assertIn("run: npm run og", out)
                self.assertEqual("pip3 install Pillow" in out, pillow, out)
                self.assertEqual("Pillow" in out, pillow, out)

    def test_the_card_generator_is_told_to_write_utf8_whatever_the_shell_around_it_says(self):
        # the generator prints an arrow, which the encoding a Windows pipe gets (cp1252) does not hold
        T.require_pillow(self)
        self.brand_md()
        old = os.environ.get("PYTHONIOENCODING")
        os.environ["PYTHONIOENCODING"] = "cp1252"
        try:
            code, out = self.intake("--json")
        finally:
            if old is None:
                del os.environ["PYTHONIOENCODING"]
            else:
                os.environ["PYTHONIOENCODING"] = old
        data = json.loads(out)
        self.assertEqual((code, data["cards"], data.get("cards_why")), (0, "regenerated", None))

    def test_a_node_that_cannot_be_started_is_a_card_failure_said_in_words(self):
        self.brand_md()
        real = _install.shutil.which
        _install.shutil.which = lambda name, *a, **k: os.path.join(self.tmp.name, "no-such-node") if name == "node" else real(name, *a, **k)
        try:
            code, out = self.intake()
        finally:
            _install.shutil.which = real
        self.assertEqual(code, 0, out)
        self.assertIn("the generator could not be started", out)
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT, "the colours themselves are in")

    def test_red_tests_that_print_nothing_are_said_so_and_the_cards_are_reported_as_put_back(self):
        T.require_pillow(self)
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--json", command="exit 1")
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["tests"], data["failing"]), (1, "tests-failed", "failed", []))
        self.assertEqual(data["cards"], "restored", "they were regenerated, and then put back with everything else")
        self.assertEqual([l for l in data["report"] if l.startswith("The failing check")], [])
        self.assertTrue(any("printed nothing" in l and "exit 1" in l for l in data["report"]), data["report"])
        self.assertEqual(self.snapshot(), before)

    def test_the_failing_checks_are_read_from_what_playwrights_list_reporter_really_prints(self):
        self.assertEqual(_install.failing_checks(PLAYWRIGHT_RED), PLAYWRIGHT_RED_NAMES)
        self.brand_md()
        log = os.path.join(self.tmp.name, "npm-test.log")
        with open(log, "w", encoding="utf-8") as f:
            f.write(PLAYWRIGHT_RED)
        code, out = self.intake("--json", command="cat '%s'; exit 1" % log)
        self.assertEqual(code, 1, out)
        self.assertEqual(json.loads(out)["failing"], PLAYWRIGHT_RED_NAMES)

    # --- what she asked for, checked before anything else ---------------------------------------

    def test_an_unknown_theme_to_accept_is_refused_on_a_run_with_only_colours_too(self):
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--accept-low-contrast", "purple")
        self.assertEqual(code, 2, out)
        self.assertIn("purple", out)
        self.assertEqual(self.snapshot(), before)

    def test_pick_or_mono_without_a_package_is_refused_by_name_not_ignored(self):
        self.brand_md()
        before = self.snapshot()
        for flags, said in ((("--pick", "a.svg"), "--pick can only be used with a package"), (("--mono", "a-mono.svg"), "--mono can only be used with a package"),
                            (("--pick", "a.svg", "--mono", "a-mono.svg"), "--pick and --mono can only be used with a package")):
            with self.subTest(flags=flags):
                code, out = self.intake(*flags)
                self.assertEqual(code, 2, out)
                self.assertIn(said, out)
                self.assertIn("--input", out)
                self.assertEqual(self.snapshot(), before)

    def test_asking_to_apply_the_colours_and_to_keep_the_colours_at_once_is_refused(self):
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--with-colours", "--keep-colours")
        self.assertEqual(code, 2, out)
        self.assertIn("--with-colours and --keep-colours", out)
        self.assertEqual(self.snapshot(), before)

    def test_keeping_the_colours_with_no_logo_leaves_nothing_to_do(self):
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--keep-colours")
        self.assertEqual(code, 2, out)
        self.assertIn("nothing to do", out.lower())
        self.assertEqual(self.snapshot(), before)

    def test_a_primary_colour_still_marked_proposed_stops_it_until_she_has_confirmed_it(self):
        # scenario 9, for the one colour outside the two theme tables
        self.brand_md(BAKERY_BRAND_MD.replace("| Primary | `#b4531a` |", "| Primary | `#b4531a (proposed)` |"))
        before = self.snapshot()
        code, out = self.intake()
        self.assertEqual(code, 3, out)
        self.assertIn("Primary", out)
        self.assertNotIn("(brand)", out, "she is told the row's name, not the program's word for its table")
        self.assertIn("confirm", out.lower())
        self.assertEqual(self.snapshot(), before)

    # --- files that cannot be edited safely are refused whole, before anything is written -------

    def test_a_stylesheet_too_large_to_be_read_whole_is_refused_by_name_and_never_cut_short(self):
        self.brand_md()
        self.put("src/styles/global.css", self.read("src/styles/global.css") + "/* " + "x" * (1200 * 1024) + " */\n.last-rule { color: red; }\n")
        before = self.snapshot()
        for extra in ((), ("--dry-run",)):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 2, out)
                self.assertIn("src/styles/global.css is larger than 1024 KB", out)
                self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)

    def test_a_file_to_edit_that_is_not_utf8_is_refused_by_name_and_its_letters_stay_as_they_are(self):
        self.brand_md()
        latin1 = self.bytes("src/config.ts").replace(b"legalName: 'Example GmbH'", "legalName: 'Müller GmbH'".encode("latin-1"))
        self.assertNotEqual(latin1, self.bytes("src/config.ts"))
        self.put("src/config.ts", latin1)
        before = self.snapshot()
        for extra in ((), ("--dry-run",)):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 2, out)
                self.assertIn("src/config.ts is not saved as UTF-8", out)
                self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)

    def test_a_colour_that_a_later_block_sets_again_is_refused_before_anything_is_written_and_the_dry_run_says_the_same(self):
        # the edit lands on the first `:root` block; the browser takes the last. Checked on the text as it
        # would be written, so that neither run touches the site (the Primary too, which the check on the
        # written file did not look at: such a run ended "Done")
        self.brand_md()
        # (the reading of the stylesheet takes each colour block only where it stands once, so what is said is
        # which block stands twice and that the two are to be folded into one, not what the colour would be)
        twice = "The stylesheet has 2 blocks of the kind that holds %s. Each of the three colour blocks must stand once"
        for name, again, said in (("the accent", ":root { --accent: #123456; }", twice % "the light theme's colours (the :root block)"),
                                  ("the primary", ":root { --brand: #111111; }", twice % "the light theme's colours (the :root block)"),
                                  ("a dark value", ':root[data-theme="dark"] { --bg: #222222; }', twice % 'the dark theme\'s colours (the :root[data-theme="dark"] block)')):
            with self.subTest(name=name):
                self.put("src/styles/global.css", T.starter_file("src/styles/global.css") + "\n" + again + "\n")
                before = self.snapshot()
                for extra in (("--dry-run",), ()):
                    code, out = self.intake(*extra)
                    self.assertEqual(code, 2, out)
                    self.assertIn("src/styles/global.css would not carry the palette after the colours were set", out)
                    self.assertIn(said, out)
                    self.assertNotIn("would be unreadable", out, "not a list of every row of a block that was not read")
                    self.assertIn("Nothing was written", out)
                    self.assertEqual(self.snapshot(), before)

    def test_a_dark_block_that_stands_after_its_media_block_instead_of_in_it_is_refused_before_anything_is_written(self):
        self.brand_md()
        head, sep, tail = T.starter_file("src/styles/global.css").partition("@media (prefers-color-scheme: dark) {")
        inner, _close, rest = tail.partition("\n}\n")
        self.put("src/styles/global.css", head + sep + "\n  img { opacity: 0.9; }\n}\n" + inner.replace("  :root:not", ":root:not") + "\n" + rest)
        before = self.snapshot()
        code, out = self.intake()
        self.assertEqual(code, 2, out)
        self.assertIn("inside the `@media (prefers-color-scheme: dark)` block", out)
        self.assertIn("Nothing was written", out)
        self.assertEqual(self.snapshot(), before)

    def test_a_colour_block_spelt_in_a_way_the_reading_knows_and_the_edit_does_not_is_refused_by_name_before_anything_is_written(self):
        # the edit knows the starter's spelling of each block, and the reading names a block that is spelt in
        # another way. Such a stylesheet must end in a refusal that says so, never in an edit of some blocks
        # and not others.
        self.brand_md()
        starter = T.starter_file("src/styles/global.css")
        for name, old, new in (("a selector list", ":root {", ":root, html {"), ("capitals", ":root {", ":ROOT {"),
                               ("a selector list for the dark block", ':root[data-theme="dark"] {', ':root[data-theme="dark"], html.dark {'),
                               ("capitals in the media block", ":root:not([data-theme]) {", ":ROOT:not([data-theme]) {")):
            with self.subTest(name=name):
                self.assertEqual(starter.count(old), 1)
                css = starter.replace(old, new)
                read = _palette.read_css(css)
                self.assertEqual((len(read.problems), len(read.found)), (1, 2), "the reading names the one block that is spelt in another way")
                self.put("src/styles/global.css", css)
                before = self.snapshot()
                for extra in (("--dry-run",), ()):
                    code, out = self.intake(*extra)
                    self.assertEqual(code, 2, out)
                    self.assertIn("src/styles/global.css has no", out)
                    self.assertIn("written in another way than the starter writes it", out)
                    self.assertIn("Nothing was written", out)
                    self.assertEqual(self.snapshot(), before)

    def test_what_the_reading_of_the_stylesheet_could_not_find_is_given_as_the_reason_for_refusing_to_edit_it(self):
        # the edit stops at the first block it misses; the reading names every one that is not there
        self.brand_md()
        css = T.starter_file("src/styles/global.css").replace("@media (prefers-color-scheme: dark)", "@media (min-width: 40em)").replace(
            ':root[data-theme="dark"] {', ':root[data-theme="night"] {')
        self.put("src/styles/global.css", css)
        before = self.snapshot()
        code, out = self.intake()
        self.assertEqual(code, 2, out)
        self.assertIn('src/styles/global.css has no `:root[data-theme="dark"]` block', out)
        self.assertIn('The stylesheet has no :root[data-theme="dark"] { ... } block that this check can find.', out)
        self.assertIn("The stylesheet has no @media (prefers-color-scheme: dark) block with :root:not([data-theme]) { ... } inside it", out)
        self.assertIn("Nothing was written", out)
        self.assertEqual(self.snapshot(), before)

    def test_a_comment_after_a_value_is_kept_when_the_value_changes(self):
        self.brand_md()
        self.put("src/styles/global.css", self.read("src/styles/global.css").replace("  --bg: #ffffff;", "  --bg: #ffffff /* the page */;", 1))
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        self.assertIn("  --bg: #fff8ee /* the page */;", self.read("src/styles/global.css"))

    def test_important_after_a_value_is_not_dropped_and_as_it_cannot_be_read_back_nothing_is_written(self):
        self.brand_md()
        self.put("src/styles/global.css", self.read("src/styles/global.css").replace("  --bg-soft: #f5f7fb;", "  --bg-soft: #f5f7fb !important;", 1))
        before = self.snapshot()
        code, out = self.intake()
        self.assertEqual(code, 2, out)
        # (the sentence is the stylesheet edit's, which is being rebuilt beside this round: what is held here is that the
        # value is named with the reading's own reason, once, and that nothing is written)
        self.assertEqual(out.count("--bg-soft in the :root block: The colour '#f5f7fb !important' is not one this check can read"), 1, out)
        self.assertIn("Nothing was written", out)
        self.assertEqual(self.snapshot(), before)

    def test_a_theme_colour_in_another_object_before_site_is_not_sites_and_sites_own_is_the_one_that_is_set(self):
        # the key is looked for in SITE's own block, line by line: the same name in another object is nothing to it
        self.brand_md()
        other = "export const PRINT = {\n  themeColor: '#111111',\n} as const;\n\n"
        config = self.read("src/config.ts")
        self.put("src/config.ts", other + config)
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code), (0, 0), out)
        for report in (dry, out):
            self.assertIn("src/config.ts, themeColor: #000000 becomes #b4531a", json.loads(report)["changes"])
        self.assertEqual(self.read("src/config.ts"), other + config.replace("themeColor: '#000000'", "themeColor: '#b4531a'"), "that one value, and not a byte else")
        if not node_problem(typescript=True):
            self.assertEqual(config_as_node_reads_it([self.read("src/config.ts")])[0]["themeColor"], "#b4531a", "and that is what the site reads")

    def test_a_manifest_colour_inside_another_entry_before_the_manifests_own_is_refused_before_anything_is_written(self):
        self.brand_md()
        self.put("public/manifest.webmanifest", self.read("public/manifest.webmanifest").replace(
            '  "lang": "en",', '  "lang": "en",\n  "shortcuts": [{ "name": "x", "url": "/x", "theme_color": "#111111" }],', 1))
        before = self.snapshot()
        for extra in (("--dry-run",), ()):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 2, out)
                self.assertIn('public/manifest.webmanifest: this tool sets the manifest\'s own "theme_color" only where', out)
                self.assertIn('the name "theme_color" stands 2 times in the file (lines 6 and 10)', out)
                self.assertIn("Set the value yourself on the manifest's own line (the last line of that name at its top level), then run this again", out)
                self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)

    def test_a_file_to_write_that_is_a_link_is_refused_before_anything_is_written_and_the_dry_run_says_the_same(self):
        self.brand_md()
        elsewhere = os.path.join(self.tmp.name, "manifest-kept-elsewhere.json")
        os.replace(self.p("public/manifest.webmanifest"), elsewhere)
        os.symlink(elsewhere, self.p("public/manifest.webmanifest"))
        before, target = self.snapshot(), T.read_bytes(elsewhere)
        for extra in (("--dry-run",), ()):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 2, out)
                self.assertIn("public/manifest.webmanifest is a link", out)
                self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(T.read_bytes(elsewhere), target)

    def test_a_link_in_the_share_cards_folder_is_refused_before_anything_is_written(self):
        # the generator writes that folder and a rollback rebuilds it, which would turn the link into a file
        self.brand_md()
        elsewhere = os.path.join(self.tmp.name, "about-card.jpg")
        with open(elsewhere, "wb") as f:
            f.write(b"a card kept somewhere else")
        os.symlink(elsewhere, self.p("public/images/og/about.jpg"))
        before = self.snapshot()
        for extra in (("--dry-run",), ()):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 2, out)
                self.assertIn("public/images/og holds a link (about.jpg)", out)
                self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)
                self.assertTrue(os.path.islink(self.p("public/images/og/about.jpg")))

    @unittest.skipUnless(os.name == "posix", "folder permissions as POSIX has them")
    def test_a_folder_this_account_may_not_write_in_is_found_before_anything_is_written(self):
        self.not_as_root()
        self.brand_md()
        before = self.snapshot()
        os.chmod(self.p("public"), 0o555)
        self.addCleanup(os.chmod, self.p("public"), 0o755)
        for extra in (("--dry-run",), ()):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 2, out)
                self.assertIn("public/manifest.webmanifest cannot be written: this account is not allowed to write in public", out)
                self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)

    # --- when the computer says no: words, the right exit status, and the truth about the files ----

    @unittest.skipUnless(os.name == "posix", "file permissions as POSIX has them")
    def test_a_file_that_may_not_be_read_is_said_in_words_with_its_path_and_json_stays_json(self):
        self.not_as_root()
        self.brand_md()
        before = self.snapshot()
        os.chmod(self.p("src/config.ts"), 0)
        try:
            code, out = self.intake("--json")
            code_plain, out_plain = self.intake()
        finally:
            os.chmod(self.p("src/config.ts"), 0o644)
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["exit"], data["code"]), (2, "refused", 2, "os-error"))
        self.assertIn(self.p("src/config.ts"), data["message"])
        self.assertIn("ermission", data["message"])
        self.assertIn("Nothing was written.", data["report"])
        self.assertEqual(code_plain, 2, out_plain)
        self.assertIn("The run had to stop", out_plain)
        self.assertEqual(self.snapshot(), before)

    def test_a_write_that_fails_half_way_is_said_in_words_and_what_was_written_before_it_is_put_back(self):
        # a file the disk refuses, which no check beforehand can see: stood in for at the journal's last step
        self.brand_md()
        before = self.snapshot()
        real = _site.Journal._put

        def refusing(journal, path, data, mode=0o644):
            if path.endswith("manifest.webmanifest"):
                raise PermissionError(13, "Permission denied", path)
            return real(journal, path, data, mode)
        _site.Journal._put = refusing
        try:
            code, out = self.intake("--json")
        finally:
            _site.Journal._put = real
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["written"]), (2, "refused", []))
        self.assertIn("manifest.webmanifest could not be read or written (Permission denied)", data["message"])
        self.assertIn("Everything it had written was put back.", data["report"])
        self.assertNotIn("not_restored", data)
        self.assertEqual(self.snapshot(), before, "the stylesheet, written before the manifest, is as it was")

    @unittest.skipUnless(os.name == "posix", "folder permissions as POSIX has them")
    def test_a_file_that_cannot_be_put_back_is_named_and_every_other_file_is_put_back_all_the_same(self):
        self.not_as_root()
        self.brand_md()
        before = self.snapshot()
        self.addCleanup(os.chmod, self.p("public"), 0o755)
        code, out = self.intake("--json", command="chmod 555 public; exit 1")
        os.chmod(self.p("public"), 0o755)
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["tests"], data["written"]), (1, "rollback-incomplete", "failed", []))
        self.assertEqual([l["file"] for l in data["not_restored"]], ["public/manifest.webmanifest"])
        report = "\n".join(data["report"])
        self.assertIn("NOT as they were", report)
        self.assertIn("  public/manifest.webmanifest (", report)
        self.assertNotIn("everything was put back", report)
        self.assertNotIn("With the install taken out", report, "it was not all taken out, so the tests are not run a second time")
        after = self.snapshot()
        self.assertNotEqual(after["public/manifest.webmanifest"], before["public/manifest.webmanifest"], "the one file it says it could not put back")
        after["public/manifest.webmanifest"] = before["public/manifest.webmanifest"]
        self.assertEqual(after, before, "every other file is as it was")

    def test_a_file_whose_folder_the_tests_moved_away_is_named_as_not_put_back_instead_of_skipped(self):
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--json", command="mv src/styles src/styles.moved; exit 1")
        data = json.loads(out)
        self.assertEqual((code, data["status"]), (1, "rollback-incomplete"))
        self.assertEqual(data["not_restored"], [{"file": "src/styles/global.css", "why": "its folder is no longer there"}])
        self.assertIn("  src/styles/global.css (its folder is no longer there)", data["report"])
        self.assertNotIn("everything was put back", "\n".join(data["report"]))
        after = self.snapshot()
        for rel in ("src/config.ts", "public/manifest.webmanifest", "scripts/generate_og_cards.py", "public/images/og/default.jpg"):
            self.assertEqual(after[rel], before[rel], rel)

    # --- what the run started is stopped before the files are put back ---------------------------

    @unittest.skipUnless(os.name == "posix", "the stand-in command is a shell's")
    def test_tests_that_run_too_long_are_stopped_with_everything_they_started(self):
        # a preview server left running would hold the site's port for the next run
        self.brand_md()
        before = self.snapshot()
        pids = os.path.join(self.tmp.name, "started")
        self.addCleanup(self.stop_leftovers, pids)
        old = _install.TEST_TIMEOUT
        _install.TEST_TIMEOUT = 2
        try:
            code, out = self.intake(command="sleep 300 & echo $! >> '%s'; wait" % pids)
        finally:
            _install.TEST_TIMEOUT = old
        self.assertEqual(code, 1, out)
        self.assertIn("were stopped", out)
        self.assertNotIn("The failing check", out, "tests that were stopped named no failing check")
        self.assertNotIn("had failed", out)
        self.assertEqual(self.snapshot(), before)
        started = [int(pid) for pid in T.read(pids).split()]
        # the second run, with the install taken out again, would wait the same time over: it is left out, and that is said
        self.assertEqual(len(started), 1, "the tests are not run a second time after they ran too long")
        self.assertIn("They were not run a second time with the install taken out again", out)
        for pid in started:
            self.assertTrue(self.gone(pid), "the process the test command started (%d) is still running" % pid)

    @unittest.skipUnless(os.name == "posix", "process groups as POSIX has them")
    def test_a_card_generator_that_runs_too_long_is_stopped_with_the_python_its_launcher_started(self):
        # the launcher is Node, the generator a Python it starts: stopping the launcher alone leaves the
        # generator writing into the share cards' folder while that folder is put back
        T.require_pillow(self)
        self.brand_md()
        pids = os.path.join(self.tmp.name, "started")
        self.addCleanup(self.stop_leftovers, pids)
        cards = self.bytes("public/images/og/default.jpg")
        gen = self.read("scripts/generate_og_cards.py")
        self.put("scripts/generate_og_cards.py", gen.replace(
            "def main():\n", "def main():\n    import os, time\n    with open(%r, 'a') as f:\n        f.write('%%d\\n' %% os.getpid())\n    time.sleep(300)\n" % pids, 1))
        old = _install.CARDS_TIMEOUT
        _install.CARDS_TIMEOUT = 6   # long enough for Node, Python and the image library to start
        try:
            code, out = self.intake()
        finally:
            _install.CARDS_TIMEOUT = old
        self.assertEqual(code, 0, out)
        self.assertIn("the generator took more than", out)
        self.assertIn("and was stopped", out)
        self.assertEqual(self.bytes("public/images/og/default.jpg"), cards)
        started = [int(pid) for pid in T.read(pids).split()]
        self.assertEqual(len(started), 1)
        self.assertTrue(self.gone(started[0]), "the generator (%d) is still running" % started[0])

    def test_once_a_run_has_its_outcome_the_stop_signals_do_nothing_and_go_on_doing_nothing_however_it_ended(self):
        # the report is printed after `install` has returned: a signal in that moment must not end the process
        # with the outcome decided and nothing, or half of it, said. (What a signal then does to the whole
        # command line is in StoppedFromOutside; this is every way a run can end.) The signals are not set to
        # "ignore": the one handler stays, and a flag tells it to do nothing.
        self.brand_md()
        self.assertIn("SIGQUIT", _install.SIGNALS)
        before = [(s, signal.getsignal(s)) for s in STOP_SIGNALS]
        self.assertNotIn(signal.SIG_IGN, [h for _s, h in before], "the test itself is not run with them ignored")
        for command, extra, code_wanted in ((GREEN, (), 0), (RED, (), 1), (GREEN, ("--dry-run",), 0), (GREEN, ("--with-logo",), 2), (GREEN, ("--with-colours", "--keep-colours"), 2),
                                            (GREEN, ("--input", self.package(), "--keep-colours"), 3)):
            with self.subTest(command=command, extra=extra):
                out = io.StringIO()
                try:
                    with contextlib.redirect_stdout(out):
                        code = brand_intake.main(["install", "--site", self.site, "--test-command", command] + list(extra))
                    after = [signal.getsignal(s) for s in STOP_SIGNALS]
                    if after == [_install._stop] * len(STOP_SIGNALS):
                        for s in STOP_SIGNALS * 2:   # each of them, sent to this very process, twice over: nothing happens
                            os.kill(os.getpid(), s)
                            time.sleep(0.01)
                finally:
                    for s, handler in before:
                        signal.signal(s, handler)
                self.assertEqual(code, code_wanted, out.getvalue())
                self.assertEqual(after, [_install._stop] * len(STOP_SIGNALS), "the run's own handler, set once and left")
                self.assertTrue(_install._HOLD["deaf"])
                self.put("src/styles/global.css", T.starter_file("src/styles/global.css"))

    @unittest.skipUnless(os.name == "posix" and hasattr(signal, "SIGHUP"), "signals as POSIX has them")
    def test_a_run_stopped_from_outside_while_the_tests_run_puts_everything_back_and_stops_what_it_started(self):
        # an assistant's shell tool stops a command that runs for minutes. The whole command line is run
        # here, as a process of its own, because the signal ends a process that does not catch it.
        self.brand_md()
        before = self.snapshot()
        pids = os.path.join(self.tmp.name, "started")
        self.addCleanup(self.stop_leftovers, pids)
        # Ctrl-C (SIGINT) and SIGQUIT are stops like the other two: the same words, the same exit status, no traceback
        for name in ("TERM", "HUP", "INT", "QUIT"):
            with self.subTest(signal=name):
                command = "sleep 300 & echo $! >> '%s'; kill -%s $PPID; wait" % (pids, name)
                r = self.drive("", command=command)
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertIn("stopped from outside (SIG%s)" % name, r.stdout)
                self.assertIn("Everything it had written was put back.", r.stdout)
                self.assertEqual(r.stderr, "", "no traceback")
                self.assertEqual(self.snapshot(), before)
        # a stop in the very instant the command starts something: that, too, is not left running
        sleep, running = self.sleeper()
        r = self.drive("", "--json", command="kill -INT $PPID; " + sleep)
        data = json.loads(r.stdout)
        self.assertEqual((r.returncode, data["status"], data["exit"], data["rolled_back"], data["written"]), (2, "stopped", 2, True, []))
        self.assertIn("stopped from outside (SIGINT)", data["message"])
        self.assertEqual((r.stderr, self.snapshot()), ("", before))
        self.assertTrue(self.none_left(running), "what the test command was just starting is still running")
        started = [int(pid) for pid in T.read(pids).split()]
        self.assertEqual(len(started), 4)
        for pid in started:
            self.assertTrue(self.gone(pid), "the process the test command started (%d) is still running" % pid)

    def test_red_tests_put_the_share_cards_folder_back_with_its_empty_folders_and_its_modes(self):
        self.brand_md()
        os.makedirs(self.p("public/images/og/drafts"))
        os.chmod(self.p("public/images/og/default.jpg"), 0o600)
        before = self.snapshot()
        self.assertIn(os.path.join("public", "images", "og", "drafts") + "/", before)
        code, out = self.intake(command=RED)
        self.assertEqual(code, 1, out)
        self.assertEqual(self.snapshot(), before, "the empty folder too")
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(os.stat(self.p("public/images/og/default.jpg")).st_mode), 0o600)

    # --- the share cards --------------------------------------------------------------------

    def test_text_that_would_not_read_half_way_down_the_share_cards_leaves_their_colours_alone_and_says_so(self):
        # all thirty pairs pass: the grey reads on the white surface and on the black background. The card's
        # background is the gradient between those two, and half way down it is the grey itself.
        self.brand_md(BAKERY_BRAND_MD.partition("### Dark theme\n")[0] + "### Dark theme\n" + table([(l, GREY_DARK[k]) for k, l in LABELS]))
        generator = self.read("scripts/generate_og_cards.py")
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read("scripts/generate_og_cards.py"), generator, "the cards' colours are as they were")
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).dark, GREY_DARK, "the site itself has the palette")
        self.assertIn("the share cards keep the colours they have", out)
        self.assertIn("Heading #767676 falls to 1 to 1", out)
        self.assertIn("text needs 4.5 to 1", out)
        self.assertNotIn("and in the share cards", out)
        self.assertNotIn("with the new colours", out)

    def test_however_the_palette_writes_a_colour_the_share_cards_get_its_three_numbers(self):
        # BRAND.md may say rgb(), a short hex, upper case or a name; the palette holds each as #rrggbb
        md = BAKERY_BRAND_MD
        for old, new in (("| Heading | `#fbeedd` |", "| Heading | `rgb(251, 238, 221)` |"), ("| Accent | `#e2874a` |", "| Accent | `tomato` |"),
                         ("| Background | `#1a120d` |", "| Background | `#1A120D` |"), ("| Muted | `#c4ae98` |", "| Muted | `#CBA` |")):
            self.assertIn(old, md)
            md = md.replace(old, new)
        self.brand_md(md)
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        generator = self.read("scripts/generate_og_cards.py")
        for line in ("TITLE_COL = (251, 238, 221)", "SUB_COL = (255, 99, 71)", "ACCENT = (255, 99, 71)", "BG_BOT = (26, 18, 13)", "FOOTER_COL = (204, 187, 170)"):
            self.assertIn(line, generator)

    # --- an icon she did not hand over --------------------------------------------------------

    def test_a_palette_alone_leaves_a_favicon_this_tool_did_not_write_as_it_is_and_says_why(self):
        # no sharp here, and none is needed: her own favicon is not a logo she handed over. One has <text>
        # (a logo given with --input would be refused for it), one is a clean drawing that the cleaning
        # would still rewrite; neither is judged, redrawn, or a reason to stop.
        self.brand_md()
        clean = _svg.clean_svg(T.real_svg(T.REAL_COLOUR)).text.encode("utf-8")
        self.assertEqual(_svg.clean_svg(clean).text.encode("utf-8"), clean, "a drawing that comes out of the cleaning as it went in")
        for name, own in (("with text", b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><text x="4" y="24">B</text></svg>'),
                          ("a drawing as a design tool exported it", T.real_svg(T.REAL_COLOUR)),
                          ("a drawing she wrote by hand as cleanly as the cleaning would", clean),
                          ("this tool's own file, edited by hand since", _install.MARK.encode("utf-8") + clean.replace(b"#b4531a", b"#B4531A")),
                          ("this tool's line, moved down a line", b"\n" + _install.MARK.encode("utf-8") + clean)):
            with self.subTest(name=name):
                self.put("public/favicon.svg", own)
                self.put("src/styles/global.css", T.starter_file("src/styles/global.css"))
                code, out = self.intake()
                self.assertEqual(code, 0, out)
                self.assertEqual(self.bytes("public/favicon.svg"), own)
                for absent in ("public/favicon.ico", "public/images/logo.png", "public/icon-192.png", "brand-handoff"):
                    self.assertFalse(self.exists(absent), absent)
                self.assertIn("LOGO = None", self.read("scripts/generate_og_cards.py"))
                # a file that carries this tool's line and was changed since is said to be that, not "not this tool's"
                self.assertIn("the icons were left as they are: public/favicon.svg is not %s, so the app icons were not drawn again on the new background" % (
                    "as this tool wrote it (it starts with this tool's line and was changed since)" if "edited by hand since" in name else "a file this tool wrote"), out)
                self.assertIn("--with-logo", out)
                self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT, "the colours are in")


class OnlyALogo(SiteCase):
    """Scenarios 39, 11 and 34: she has a logo and wants no help with colours."""

    def test_the_seven_files_come_from_her_zip_and_the_colours_stay_as_the_site_has_them(self):
        T.require_pillow(self)
        css_before, manifest_before = self.read("src/styles/global.css"), self.read("public/manifest.webmanifest")
        zip_path = self.package()
        code, out = self.intake("--input", zip_path, "--pick", T.REAL_COLOUR, "--mono", T.REAL_MONO, "--accept-colours",
                                "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        for rel in ("public/favicon.svg", "public/favicon.ico", "public/apple-touch-icon.png", "public/icon-192.png",
                    "public/icon-512.png", "public/icon-maskable-512.png", "public/images/logo.png"):
            self.assertTrue(self.exists(rel), rel)
        self.assertEqual(self.read("src/styles/global.css"), css_before)
        self.assertEqual(self.read("public/manifest.webmanifest"), manifest_before)
        self.assertEqual(self.read("scripts/generate_og_cards.py"), T.starter_file("scripts/generate_og_cards.py"), "the generator is not touched: the emblem is not this tool's to set")
        self.assertIn("logo: '/images/logo.png'", self.read("src/config.ts"))

    def test_the_package_is_kept_in_a_folder_git_ignores_with_a_preview_beside_it(self):
        zip_path = self.package("furrows.zip")
        code, out = self.intake("--input", zip_path, "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.bytes("brand-handoff/furrows.zip"), T.real_zip_bytes())
        self.assertTrue(self.exists("brand-handoff/preview.png"))
        self.assertEqual(self.read(".gitignore").splitlines()[-1], "brand-handoff/")
        self.assertEqual(T.read_bytes(zip_path), T.real_zip_bytes(), "her own copy is untouched")

    def test_the_preview_is_the_installed_mark_and_the_report_leaves_whether_it_reads_to_her(self):
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        import _png
        w, h = _png.size(self.bytes("brand-handoff/preview.png"))
        self.assertEqual((w, h), (2 * 432, 336))
        self.assertIn("brand-handoff/preview.png", out)
        self.assertIn("your call", out)
        for verdict in ("looks good", "too small", "unreadable", "is fine", "passes the legibility"):
            self.assertNotIn(verdict, out.lower())

    def test_two_files_in_the_zip_are_asked_about_and_nothing_is_written(self):
        before = self.snapshot()
        code, out = self.intake("--input", self.package(), brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn(T.REAL_COLOUR, out)
        self.assertIn(T.REAL_MONO, out)
        self.assertEqual(self.snapshot(), before)

    def test_names_that_differ_only_by_a_character_nobody_can_see_are_refused_or_shown_spelled_out_never_printed_alike(self):
        # in a package: two SVG files whose names differ by a zero-width space are no choice anybody can make,
        # and the whole package is refused, with the name spelled out
        before = self.snapshot()
        for label, names, spelt in (("a zero-width space", ("mark.svg", "mark\u200b.svg"), "mark\\u200b.svg"), ("a no-break space for a blank", ("my mark.svg", "my\u00a0mark.svg"), "my\\xa0mark.svg")):
            with self.subTest(label=label):
                pack = self.package("two.zip", T.build_zip([(n, rects((2, 2, 28, 28, "#b4531a"))) for n in names]))
                for code, out in self.both_runs("--input", pack, brand=False):
                    self.assertEqual(code, 2, out)
                    self.assertIn("holds something that cannot be seen", out)
                    self.assertIn("(spelled out, the name starts '%s')" % spelt, out)
                    self.assertNotIn(names[1], out, "the name is nowhere printed with the character in it")
                    self.assertEqual(self.snapshot(), before)
        # in a folder: two packages whose names differ that way are asked about, and what the owner is shown tells
        # them apart; the JSON keeps each path as it is, because her answer is matched against that
        folder = os.path.join(self.pack, "two")
        os.makedirs(folder)
        plain, hidden = os.path.join(folder, "logo.zip"), os.path.join(folder, "logo\u200b.zip")
        for path in (plain, hidden):
            with open(path, "wb") as f:
                f.write(T.real_zip_bytes())
        for code, out in self.both_runs("--input", folder, brand=False):
            self.assertEqual(code, 3, out)
            shown = [l[len("    * "):] for l in out.splitlines() if l.startswith("    * ")]
            self.assertEqual(shown, [plain, os.path.join(folder, "logo\\u200b.zip")], "the second one is spelled out")
            self.assertNotIn("\u200b", out, "nothing a person cannot see is printed")
        data = json.loads(self.intake("--input", folder, "--json", brand=False)[1])
        self.assertEqual(data["asks"][0]["options"], [plain, hidden], "as they are: an answer is one of these")
        self.assertEqual([l for l in data["report"] if l.startswith("    * ")], ["    * " + plain, "    * " + os.path.join(folder, "logo\\u200b.zip")])
        code, out = self.intake("--input", data["asks"][0]["options"][1], "--json", brand=False)   # her answer, given back as the JSON had it
        self.assertEqual(([k["code"] for k in json.loads(out)["asks"]], code), (["which-file"], 3), "the hidden-named package is the one that is opened")
        self.assertEqual(self.snapshot(), before)

    def test_a_package_that_will_not_do_is_refused_with_nothing_written(self):
        before = self.snapshot()
        for name, data in (("raster.png", b"\x89PNG\r\n\x1a\n" + b"\0" * 30),
                           ("evil.svg", b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><script>x</script></svg>'),
                           ("nosvg.zip", T.build_zip([("a.png", b"\x89PNG..."), ("README.txt", b"hi")]))):
            with self.subTest(name=name):
                code, out = self.intake("--input", self.package(name, data), brand=False)
                self.assertEqual(code, 2, out)
                self.assertEqual(self.snapshot(), before)
        code, out = self.intake("--input", self.package("raster.png", b"\x89PNG\r\n\x1a\n" + b"\0" * 30), brand=False)
        self.assertIn("SVG", out)

    def test_scenario_27_a_path_that_holds_nothing_is_said_so_and_nothing_is_searched_for(self):
        before = self.snapshot()
        for path in (os.path.join(self.pack, "missing.zip"), self.pack):
            with self.subTest(path=path):
                code, out = self.intake("--input", path, brand=False)
                self.assertEqual(code, 2, out)
                self.assertIn("nothing", out.lower())
                self.assertIn("path", out.lower())
                self.assertEqual(self.snapshot(), before)

    def test_a_folder_holding_one_package_is_the_package(self):
        # a later run: the package is in brand-handoff
        os.makedirs(self.p("brand-handoff"))
        with open(self.p("brand-handoff/furrows.zip"), "wb") as f:
            f.write(T.real_zip_bytes())
        code, out = self.intake("--input", self.p("brand-handoff"), brand=False)
        self.assertEqual(code, 3, out)   # it is the real zip with two SVGs: asked which
        self.assertIn(T.REAL_COLOUR, out)

    def test_a_folder_holding_several_packages_asks_which(self):
        self.package("a.zip")
        self.package("b.svg", T.real_svg(T.REAL_COLOUR))
        code, out = self.intake("--input", self.pack, brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("a.zip", out)
        self.assertIn("b.svg", out)

    def test_scenario_21_a_colour_outside_the_palette_is_listed_and_never_recoloured(self):
        self.brand_md()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--with-colours", "--accept-low-contrast", "both")
        self.assertEqual(code, 3, out)
        self.assertIn("#6b2c0b", out)
        self.assertIn("not in", out)
        self.assertFalse(self.exists("public/favicon.svg"))
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--with-colours", "--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(code, 0, out)
        self.assertIn("#6b2c0b", self.read("public/favicon.svg"))

    def test_scenario_15_a_colour_that_vanishes_on_a_theme_is_named_with_the_theme_and_the_one_colour_way_out(self):
        self.brand_md()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--mono", T.REAL_MONO, "--with-colours", "--accept-colours")
        self.assertEqual(code, 3, out)
        self.assertIn("dark", out)
        self.assertIn("1.7", out)
        self.assertIn("one-colour", out)
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--mono", T.REAL_MONO, "--with-colours", "--accept-colours",
                                "--accept-low-contrast", "dark")
        self.assertEqual(code, 0, out)

    def test_the_mark_is_checked_against_the_sites_own_colours_when_no_palette_is_given(self):
        # scenario 39: on a fresh scaffold those are the starter's; on a site whose colours were customised, its own
        css = self.read("src/styles/global.css").replace("--bg: #0a0b1e;", "--bg: #6b2c0b;").replace("#0a0b1e", "#6b2c0b")
        with open(self.p("src/styles/global.css"), "w", encoding="utf-8") as f:
            f.write(css)
        code, out = self.intake("--input", self.package("one.svg", T.real_svg(T.REAL_MONO)), "--accept-colours", brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("dark", out)

    def test_scenario_30_the_scaffolds_placeholders_are_replaced_with_a_word(self):
        placeholder_svg, placeholder_ico = b"<svg>placeholder</svg>", b"placeholder-ico"
        for rel, data in (("public/favicon.svg", placeholder_svg), ("public/favicon.ico", placeholder_ico)):
            with open(self.p(rel), "wb") as f:
                f.write(data)
        old = _site.SCAFFOLD_DEFAULTS
        _site.SCAFFOLD_DEFAULTS = {"public/favicon.svg": {hashlib.sha256(placeholder_svg).hexdigest()},
                                   "public/favicon.ico": {hashlib.sha256(placeholder_ico).hexdigest()}}
        try:
            args = ("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both")
            dry_code, dry_out = self.intake(*args, "--dry-run", brand=False)
            code, out = self.intake(*args, brand=False)
        finally:
            _site.SCAFFOLD_DEFAULTS = old
        self.assertEqual(dry_code, 0, dry_out)
        self.assertIn("would replace", dry_out)
        self.assertNotIn("now replaced", dry_out, "a dry run has replaced nothing")
        self.assertEqual(code, 0, out)
        self.assertIn("now replaced", out)
        self.assertNotEqual(self.read("public/favicon.svg"), placeholder_svg.decode())

    def test_scenario_16_an_icon_that_is_not_a_placeholder_is_asked_about(self):
        with open(self.p("public/apple-touch-icon.png"), "wb") as f:
            f.write(b"somebody's own icon")
        before = self.snapshot()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("public/apple-touch-icon.png", out)
        self.assertEqual(self.snapshot(), before)
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both",
                                "--replace-icons", brand=False)
        self.assertEqual(code, 0, out)
        self.assertNotEqual(self.bytes("public/apple-touch-icon.png"), b"somebody's own icon")

    def test_running_it_again_with_the_same_mark_asks_nothing_and_changes_nothing_more(self):
        args = ("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(self.intake(*args, brand=False)[0], 0)
        after_first = self.snapshot()
        code, out = self.intake(*args, brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.snapshot(), after_first)

    def test_a_later_run_with_no_palette_and_no_file_has_nothing_to_do(self):
        # the installed mark alone starts nothing: the logo is redone only when a file is given or the colours change
        args = ("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(self.intake(*args, brand=False)[0], 0)
        after_first = self.snapshot()
        code, out = self.intake(brand=False)
        self.assertEqual(code, 2, out)
        self.assertIn("nothing to do", out.lower())
        self.assertEqual(self.snapshot(), after_first)

    def test_a_package_already_in_brand_handoff_is_not_copied_a_second_time(self):
        # its name has a space, which a copy would turn into an underscore: a second file would show
        os.makedirs(self.p("brand-handoff"))
        kept = self.p("brand-handoff/my logo.zip")
        with open(kept, "wb") as f:
            f.write(T.real_zip_bytes())
        code, out = self.intake("--input", kept, "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(os.listdir(self.p("brand-handoff"))), ["my logo.zip", "preview.png"])
        self.assertNotIn("is kept in", out)
        self.assertEqual(self.read(".gitignore").splitlines()[-1], "brand-handoff/", "the preview alone is reason to ignore the folder")

    def test_a_different_file_of_the_same_name_in_brand_handoff_is_kept_and_the_new_one_gets_its_own_name(self):
        os.makedirs(self.p("brand-handoff"))
        with open(self.p("brand-handoff/logo.zip"), "wb") as f:
            f.write(b"an earlier package")
        code, out = self.intake("--input", self.package("logo.zip"), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.bytes("brand-handoff/logo.zip"), b"an earlier package")
        self.assertEqual(self.bytes("brand-handoff/logo-2.zip"), T.real_zip_bytes())
        self.assertIn("brand-handoff/logo-2.zip", out)

    def test_an_unknown_theme_to_accept_is_refused_not_ignored(self):
        before = self.snapshot()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "purple", brand=False)
        self.assertEqual(code, 2, out)
        self.assertIn("purple", out)
        self.assertEqual(self.snapshot(), before)

    def test_a_half_filled_palette_beside_a_logo_is_named_and_the_colours_stay(self):
        # never silent: she may think her colours went in with the logo
        self.brand_md(BAKERY_BRAND_MD.replace("| Soft background | `#fef5e8` |\n", ""))
        css_before = self.read("src/styles/global.css")
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(code, 0, out)
        self.assertIn("the colours were not changed", out)
        self.assertIn("Soft background", out)
        self.assertEqual(self.read("src/styles/global.css"), css_before)

    def test_a_logo_alone_leaves_the_theme_colour_and_the_share_cards_colours_as_the_site_has_them(self):
        # scenario 39, on a site whose config and card colours no longer match the stylesheet's
        for rel, old, new in (("src/config.ts", "themeColor: '#000000'", "themeColor: '#123456'"),
                              ("scripts/generate_og_cards.py", "BG_TOP = (30, 33, 64)", "BG_TOP = (1, 2, 3)")):
            text = self.read(rel)
            self.assertIn(old, text)
            with open(self.p(rel), "w", encoding="utf-8") as f:
                f.write(text.replace(old, new))
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        self.assertIn("themeColor: '#123456'", self.read("src/config.ts"))
        self.assertIn("BG_TOP = (1, 2, 3)", self.read("scripts/generate_og_cards.py"))
        self.assertIn("\nLOGO = None ", self.read("scripts/generate_og_cards.py"))

    def test_scenario_31_red_tests_remove_the_package_copy_the_ignore_line_and_the_folder(self):
        before = self.snapshot()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both",
                                command=RED, brand=False)
        self.assertEqual(code, 1, out)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.exists("brand-handoff"))

    def test_scenario_31_in_a_brand_handoff_that_was_already_there_only_this_runs_copy_goes(self):
        os.makedirs(self.p("brand-handoff"))
        with open(self.p("brand-handoff/earlier.zip"), "wb") as f:
            f.write(b"earlier")
        with open(self.p(".gitignore"), "a") as f:
            f.write("brand-handoff/\n")
        before = self.snapshot()
        code, out = self.intake("--input", self.package("this.zip"), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both",
                                command=RED, brand=False)
        self.assertEqual(code, 1, out)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.exists("brand-handoff/earlier.zip"))

    def test_an_existing_ignore_line_is_not_added_twice(self):
        with open(self.p(".gitignore"), "a") as f:
            f.write("/brand-handoff\n")
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read(".gitignore").count("brand-handoff"), 1)

    def test_an_ignore_rule_that_a_later_line_takes_back_does_not_count_and_the_line_is_added_at_the_end(self):
        with open(self.p(".gitignore"), "a") as f:
            f.write("brand-handoff/*\n!brand-handoff/logo.zip\n")
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read(".gitignore").splitlines()[-3:], ["brand-handoff/*", "!brand-handoff/logo.zip", "brand-handoff/"])
        self.assertIn(".gitignore", out)

    def test_a_logo_beside_a_palette_that_would_change_the_sites_colours_asks_first_and_names_every_value(self):
        # she came with a logo; BRAND.md holds a palette the site does not show. Colours she set by hand in
        # the stylesheet are not overwritten on the way without one of them being named.
        self.brand_md()
        before = self.snapshot()
        for extra in ((), ("--dry-run",)):
            with self.subTest(extra=extra):
                code, out = self.intake("--input", self.package(), *LOGO_ARGS, *extra)
                self.assertEqual(code, 3, out)
                for said in ("Nothing was written", "--with-colours", "--keep-colours", "    * Primary: #000000 becomes #b4531a",
                             "    * Accent, light theme: #2b50e0 becomes #b4531a", "    * Surface (cards), dark theme: #161836 becomes #2a1f17"):
                    self.assertIn(said, out)
                self.assertEqual(self.snapshot(), before)
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, "--json")
        asks = json.loads(out)["asks"]
        self.assertEqual([k["code"] for k in asks], ["colours-too"])
        self.assertIn("Primary: #000000 becomes #b4531a", asks[0]["options"])

    def test_keep_colours_installs_the_logo_and_leaves_every_colour_as_the_site_has_it(self):
        self.brand_md()
        kept = {rel: self.read(rel) for rel in ("src/styles/global.css", "public/manifest.webmanifest")}
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, "--keep-colours")
        self.assertEqual(code, 0, out)
        for rel, text in kept.items():
            self.assertEqual(self.read(rel), text, rel)
        self.assertIn("themeColor: '#000000'", self.read("src/config.ts"))
        self.assertIn("BG_TOP = (30, 33, 64)", self.read("scripts/generate_og_cards.py"))
        self.assertTrue(self.exists("public/images/logo.png"))
        self.assertIn("the palette in BRAND.md was not applied (--keep-colours)", out)
        self.assertNotIn("Colours:", out)
        import _png
        self.assertEqual(_png.at(_png.decode(self.bytes("public/icon-maskable-512.png")), 0, 0)[:3], (0xff, 0xff, 0xff), "the icons sit on the site's own background")

    def test_a_logo_beside_a_palette_the_site_already_shows_asks_nothing(self):
        self.brand_md()
        self.assertEqual(self.intake()[0], 0)   # the colours first, on their own
        code, out = self.intake("--input", self.package(), *LOGO_ARGS)
        self.assertEqual(code, 0, out)
        self.assertTrue(self.exists("public/images/logo.png"))

    def test_a_favicon_that_is_not_the_recorded_placeholder_is_asked_about_before_a_logo_replaces_it(self):
        # what a newer scaffold's placeholder is to this tool, whose two hashes nothing keeps up to date: an
        # icon it does not know. She is asked; it is never replaced with only a word.
        self.put("public/favicon.svg", b"<svg>the placeholder of a scaffold newer than the recorded one</svg>")
        before = self.snapshot()
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("public/favicon.svg", out)
        self.assertIn("--replace-icons", out)
        self.assertEqual(self.snapshot(), before)
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, "--replace-icons", brand=False)
        self.assertEqual(code, 0, out)
        self.assertNotIn("placeholder", out)

    def test_asking_for_the_logo_with_no_file_draws_the_icons_again_from_the_installed_master(self):
        self.assertEqual(self.intake("--input", self.package(), *LOGO_ARGS, brand=False)[0], 0)
        after_first = self.snapshot()
        os.remove(self.p("public/icon-192.png"))
        code, out = self.intake("--with-logo", "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.snapshot(), after_first, "the icon that was missing is back, and nothing else moved")

    def test_a_dry_run_lists_what_the_real_run_would_write_and_nothing_it_would_leave_alone(self):
        args = ("--input", self.package(), *LOGO_ARGS, "--json")
        dry = json.loads(self.intake(*args, "--dry-run", brand=False)[1])
        real = json.loads(self.intake(*args, brand=False)[1])
        self.assertEqual((dry["status"], real["status"]), ("dry-run", "done"))
        self.assertEqual(dry["written"], real["written"])
        self.assertIn("brand-handoff/preview.png", dry["written"])
        again = json.loads(self.intake(*args, "--dry-run", brand=False)[1])
        self.assertEqual(again["written"], [], "the site holds all of it already, as the real run finds too")
        self.assertEqual(json.loads(self.intake(*args, brand=False)[1])["written"], [])
        code, out = self.intake(*args[:-1], "--dry-run", brand=False)
        self.assertIn("  nothing: every file is already as this run would write it", out)
        os.remove(self.p("public/icon-512.png"))
        self.assertEqual(json.loads(self.intake(*args, "--dry-run", brand=False)[1])["written"], ["public/icon-512.png"])

    def test_a_package_called_preview_png_does_not_take_the_preview_sheets_name(self):
        # what a file is, is read from its content, so an SVG may be called anything
        path = self.package("preview.png", T.real_svg(T.REAL_MONO))
        code, out = self.intake("--input", path, "--accept-colours", "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 0, out)
        import _png
        self.assertEqual(_png.size(self.bytes("brand-handoff/preview.png")), (2 * 432, 336), "the preview sheet")
        self.assertEqual(self.bytes("brand-handoff/preview-2.png"), T.real_svg(T.REAL_MONO), "her file, under the next name")
        self.assertIn("is kept in brand-handoff/preview-2.png", out)

    def test_a_company_logo_that_pointed_at_her_own_file_is_repointed_with_a_note_that_names_it(self):
        self.put("src/config.ts", self.read("src/config.ts").replace("logo: '/images/logo.png',", "logo: '/brand/own-logo.svg',"))
        # said by what happened: a dry run has pointed it nowhere
        for extra, said in ((("--dry-run",), "Note: COMPANY.logo in src/config.ts points at /brand/own-logo.svg; this run would point it at /images/logo.png"),
                            ((), "Note: COMPANY.logo in src/config.ts pointed at /brand/own-logo.svg; it now points at /images/logo.png")):
            with self.subTest(extra=extra):
                code, out = self.intake("--input", self.package(), *LOGO_ARGS, *extra, brand=False)
                self.assertEqual(code, 0, out)
                self.assertIn(said, out)
                self.assertEqual("it now points at" in out, not extra, out)
        self.assertIn("logo: '/images/logo.png',", self.read("src/config.ts"))
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, brand=False)
        self.assertNotIn("COMPANY.logo in src/config.ts pointed at", out, "once it points there, there is nothing to say")


    def test_a_note_that_explains_a_question_is_printed_with_the_question(self):
        # the question names a colour she cannot see in her mark; the note says why it is counted
        hidden = self.package("hidden.svg", rects((2, 2, 28, 28, "#123456"), (2, 2, 28, 28, "#16162a")))
        note = "the colour #123456 is painted in the file but hardly shows when it is drawn"
        before = self.snapshot()
        code, out = self.intake("--input", hidden, "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("not in the palette: #123456", out)
        self.assertIn("Note: " + note, out)
        data = json.loads(self.intake("--input", hidden, "--accept-low-contrast", "both", "--json", brand=False)[1])
        self.assertEqual(data["status"], "needs-decision")
        self.assertTrue(any(n.startswith(note) for n in data["notes"]), data["notes"])
        self.assertTrue(any(l.startswith("Note: " + note) for l in data["report"]), data["report"])
        self.assertEqual(self.snapshot(), before)

    def test_a_question_asked_before_the_mark_is_drawn_carries_the_notes_made_so_far(self):
        # two packages in the folder, and a palette that is half filled in: she is told both at once
        self.brand_md(BAKERY_BRAND_MD.replace("| Soft background | `#fef5e8` |\n", ""))
        self.package("a.zip")
        self.package("b.svg", T.real_svg(T.REAL_COLOUR))
        code, out = self.intake("--input", self.pack)
        self.assertEqual(code, 3, out)
        self.assertIn("Which one is it?", out)
        self.assertIn("Note: the colours were not changed: BRAND.md does not hold a complete palette", out)

    def test_a_question_does_not_say_a_placeholder_was_replaced_when_nothing_was_written(self):
        placeholder = b"<svg>placeholder</svg>"
        self.put("public/favicon.svg", placeholder)
        self.put("public/apple-touch-icon.png", b"somebody's own icon")
        old = _site.SCAFFOLD_DEFAULTS
        _site.SCAFFOLD_DEFAULTS = {"public/favicon.svg": {hashlib.sha256(placeholder).hexdigest()}}
        try:
            code, out = self.intake("--input", self.package(), *LOGO_ARGS, brand=False)
            self.assertEqual(code, 3, out)
            self.assertIn("public/apple-touch-icon.png", out)
            self.assertNotIn("now replaced", out)
            code, out = self.intake("--input", self.package(), *LOGO_ARGS, "--replace-icons", brand=False)
        finally:
            _site.SCAFFOLD_DEFAULTS = old
        self.assertEqual(code, 0, out)
        self.assertIn("public/favicon.svg was the scaffold's placeholder (the Astro logo), now replaced", out)

    def test_the_one_colour_version_is_held_against_the_palette_but_never_asked_about_on_the_page(self):
        # the colour version cannot sit on any background whole (one half is near white, the other near
        # black), so the app icons are drawn from the one-colour version, on white. That version's navy would
        # vanish on the dark page, but it never stands there: only the colour version does.
        pack = self.package("two.zip", T.build_zip([("mark.svg", rects((2, 2, 12, 28, "#fefefe"), (18, 2, 12, 28, "#050505"))),
                                                    ("mark-mono.svg", rects((2, 2, 28, 28, "#222244")))]))
        args = ("--input", pack, "--pick", "mark.svg", "--mono", "mark-mono.svg")
        code, out = self.intake(*args, "--accept-colours", brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("drawn from the one-colour version on #ffffff", out)
        # what is said of the one-colour version as a way out is worked out, theme by theme: navy reads on the
        # light page and not on the dark one
        self.assertIn("On the light theme the mark falls under 3 to 1 against the background (#fefefe is 1 to 1). The one-colour version you gave can be used where it sits "
                      "on that background. Accept it as it is (--accept-low-contrast light)", out)
        self.assertIn("On the dark theme the mark falls under 3 to 1 against the background (#050505 is 1.04 to 1). The one-colour version you gave does not reach 3 to 1 on "
                      "that background either (#222244 is 1.27 to 1). Accept it as it is (--accept-low-contrast dark)", out)
        self.assertEqual(out.count("#222244"), 1, "said in that one sentence: the one-colour version is not asked about as a mark on the page")
        self.assertEqual([k["code"] for k in json.loads(self.intake(*args, "--accept-colours", "--json", brand=False)[1])["asks"]], ["low-contrast", "low-contrast"])
        for name, mono, light, dark in (("black", "#000000", "can be used where it sits on that background.", "does not reach 3 to 1 on that background either (#000000 is 1.07 to 1)."),
                                        ("white", "#ffffff", "does not reach 3 to 1 on that background either (#ffffff is 1 to 1).", "can be used where it sits on that background."),
                                        ("a grey that reads on both pages", "#767676", "can be used where it sits on that background.", "can be used where it sits on that background.")):
            with self.subTest(mono=name):
                other = self.package("two-%s.zip" % mono[1:], T.build_zip([("mark.svg", rects((2, 2, 12, 28, "#fefefe"), (18, 2, 12, 28, "#050505"))), ("mark-mono.svg", rects((2, 2, 28, 28, mono)))]))
                code, out = self.intake("--input", other, "--pick", "mark.svg", "--mono", "mark-mono.svg", "--accept-colours", brand=False)
                self.assertEqual(code, 3, out)
                self.assertIn("(#fefefe is 1 to 1). The one-colour version you gave " + light, out)
                self.assertIn("(#050505 is 1.04 to 1). The one-colour version you gave " + dark, out)
        # with no one-colour version given, nothing is said of one that was not looked at
        alone = self.package("alone.svg", rects((2, 2, 28, 28, "#fefefe")))
        code, out = self.intake("--input", alone, "--accept-colours", brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("(#fefefe is 1 to 1). A one-colour version may read better there: give one with --mono (in a package) to have it checked. Accept it as it is (--accept-low-contrast light)", out)
        self.assertNotIn("Use its one-colour version", out, "no file is spoken of that may not exist, and nothing is said to be usable that was not checked")
        # what the sentence says to do, done: a package with a one-colour version, named with --mono, gets that version checked
        both = self.package("alone-and-mono.zip", T.build_zip([("mark.svg", rects((2, 2, 28, 28, "#fefefe"))), ("mark-mono.svg", rects((2, 2, 28, 28, "#222244")))]))
        code, out = self.intake("--input", both, "--pick", "mark.svg", "--mono", "mark-mono.svg", "--accept-colours", brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("(#fefefe is 1 to 1). The one-colour version you gave can be used where it sits on that background. Accept it as it is (--accept-low-contrast light)", out)
        code, out = self.intake(*args, "--accept-low-contrast", "both", brand=False)
        self.assertEqual(code, 3, out)
        self.assertIn("not in the palette: #fefefe, #050505, #222244", out, "and it is still held against the palette")

    def test_what_is_said_of_the_one_colour_version_is_worked_out_on_the_background_the_page_will_have_not_on_brand_mds(self):
        # "that background" in the question is the page's own once the run is done. Where the palette in BRAND.md
        # is not applied (--keep-colours, or no BRAND.md at all), that is the background the site has now, and
        # the one-colour version's ratio has to be worked out on it too. #606060 reaches 3 to 1 on the starter's
        # dark background (#0a0b1e: 3.09) and not on the bakery's (#1a120d: 2.93).
        self.assertEqual((STARTER_DARK["bg"], T.BAKERY_DARK["bg"]), ("#0a0b1e", "#1a120d"))
        self.assertEqual((_colour.shown(_colour.ratio("#606060", "#0a0b1e")), _colour.shown(_colour.ratio("#606060", "#1a120d"))), ("3.09", "2.93"))
        pack = self.package("grey.zip", T.build_zip([("mark.svg", rects((2, 2, 12, 28, "#fefefe"), (18, 2, 12, 28, "#050505"))), ("mark-mono.svg", rects((2, 2, 28, 28, "#606060")))]))
        args = ("--input", pack, "--pick", "mark.svg", "--mono", "mark-mono.svg", "--accept-colours")
        site = ("On the dark theme the mark falls under 3 to 1 against the background (#050505 is 1.04 to 1). The one-colour version you gave can be used where it sits on that background. "
                "Accept it as it is (--accept-low-contrast dark)")
        palette = ("On the dark theme the mark falls under 3 to 1 against the background (#050505 is 1.1 to 1). The one-colour version you gave does not reach 3 to 1 on that background either "
                   "(#606060 is 2.93 to 1). Accept it as it is (--accept-low-contrast dark)")
        self.brand_md()
        before = self.snapshot()
        for label, more, said, not_said in (("the palette is left out", ("--keep-colours",), site, palette), ("the palette goes in with the logo", ("--with-colours",), palette, site)):
            with self.subTest(label=label):
                for code, out in self.both_runs(*args, *more):
                    self.assertEqual(code, 3, out)
                    self.assertIn(said, out)
                    self.assertNotIn(not_said, out)
                self.assertEqual(self.snapshot(), before)
        os.remove(self.p("BRAND.md"))
        code, out = self.intake(*args, brand=False)   # a run about the logo alone, on a site with no BRAND.md
        self.assertEqual(code, 3, out)
        self.assertIn(site, out)

    def test_brand_handoff_that_is_a_file_is_refused_in_words_before_anything_is_written(self):
        self.put("brand-handoff", b"a file where the folder would go")
        before = self.snapshot()
        code, out = self.intake("--input", self.package(), *LOGO_ARGS, brand=False)
        self.assertEqual(code, 2, out)
        self.assertIn("brand-handoff/logo.zip cannot be written: brand-handoff is not a folder. Move it away, then run this again.", out)
        self.assertIn("Nothing was written", out)
        self.assertEqual(self.snapshot(), before)
        os.remove(self.p("brand-handoff"))   # what it says to do, done
        self.assertEqual(self.intake("--input", self.package(), *LOGO_ARGS, brand=False)[0], 0)


OTHER_HEADINGS = BAKERY_BRAND_MD.replace("### Light theme", "### Light").replace("### Dark theme", "### Dark").replace("### Brand (fixed, theme-independent)", "### Brand colours")
NESTED_SHORTCUT = '  "lang": "en",\n  "shortcuts": [{ "name": "x", "url": "/x", "theme_color": "#111111", "background_color": "#222222" }],'
POSIX = unittest.skipUnless(os.name == "posix", "signals, permissions and the stand-in commands as POSIX has them")


class ColoursOnASiteAsSheLeftIt(SiteCase):
    """The second round of the review: a run about colours on a site that somebody has worked on since
    the starter. What it reads is what the site reads; what it cannot be sure of it refuses, the dry run in
    the same words; a file that is there is never taken for one that is not. No sharp is needed here."""
    modules = False

    def fresh(self):
        shutil.rmtree(self.site)
        T.make_starter_site(self.site, with_modules=self.modules)
        self.brand_md()

    # --- an edit changes the value the site reads, or nothing ---------------------------------

    # --- src/config.ts, the manifest and the generator are edited by line, strictly ----------------
    # One rule (_site.set_lines): a value is edited only on its one line in the starter's shape; whatever
    # else is found is refused before anything is written, in a sentence that can be followed.

    def follow(self, rel, text, out):
        """Do to a file exactly what the refusal printed in `out` says, and nothing else: the line it shows is
        written character for character as it stands in the report (test_site_edits has the three followers)."""
        if "Mend the file so that it is valid JSON" in out:
            return text.replace(",,", ",").replace(' "ratio": NaN,', "")
        if "Leave one `export const SITE` in the file" in out:
            return re.sub(r"/\*.*?\*/\n", "", text, flags=re.S)   # the copy in the comment goes
        if "Mend that so that the file runs under this Python" in out:
            return text.replace("( 010,", "(10,")
        if "Name what is imported there in place of the `*`" in out:
            return text.replace("import *", "import sep")
        return {"src/config.ts": follow_config, "public/manifest.webmanifest": follow_manifest, "scripts/generate_og_cards.py": follow_generator}[rel](text, refusal_in(out))

    def as_the_site_reads(self, rel):
        """The values of one of the three files as the program that reads it on the site gets them (None where
        that program is not there to ask)."""
        if rel == "scripts/generate_og_cards.py":
            return generator_as_python_runs_it([self.read(rel)])[0]
        if node_problem(typescript=rel == "src/config.ts"):
            return None
        return (config_as_node_reads_it if rel == "src/config.ts" else manifest_as_node_reads_it)([self.read(rel)])[0]

    def test_nothing_above_the_site_block_can_hide_it_a_regex_literal_holding_a_quote_least_of_all(self):
        # the scanner of the round before read strings and comments, took the quote in `/'/` for the start of a
        # string, and no longer found the block below it: a config that round 1 edited was refused, for good
        config = T.starter_file("src/config.ts")
        for name, above in (("a regex literal holding an apostrophe", "const APOS = /'/g;\n"), ("a regex literal holding both quotes", "const QUOTES = /['\"]/g;\n"),
                            ("a template string nested in a template string", "const n = 1;\nconst T = `a${n ? `x'` : 'y'}b`;\n"),
                            ("a template string with a quoted brace", "const n = 1;\nconst T = `a${n ? '}' : \"{\"}b`;\n")):
            with self.subTest(name=name):
                self.fresh()
                self.put("src/config.ts", above + config)
                (dry_code, dry), (code, out) = self.both_runs("--json")
                self.assertEqual((dry_code, code), (0, 0), out)
                self.assertEqual(json.loads(dry)["written"], json.loads(out)["written"])
                self.assertIn("src/config.ts", json.loads(out)["written"])
                self.assertIn("src/config.ts, themeColor: #000000 becomes #b4531a", json.loads(dry)["changes"])
                self.assertEqual(self.read("src/config.ts"), above + config.replace("themeColor: '#000000'", "themeColor: '#b4531a'"), "that one value, and not a byte else")
                (dry_code, dry), (code, out) = self.both_runs("--json")   # and once the value is there, it is seen to be there
                self.assertEqual((dry_code, code), (0, 0), out)
                self.assertNotIn("src/config.ts", json.loads(dry)["written"] + json.loads(out)["written"])

    def test_what_is_not_written_as_the_starter_writes_it_is_refused_before_anything_is_written_and_doing_what_the_refusal_says_makes_the_next_run_go_through(self):
        config, manifest, generator = (T.starter_file(rel) for rel in _install.OTHER_FILES)
        own = "  themeColor: '#000000',               // matches the brand primary + manifest\n"
        self.assertEqual(config.count(own), 1)
        home = "# Home + fallback card"
        cases = (
            # src/config.ts: a file a developer has reshaped, where the tool edited a line and the site read another value
            # (round 7) the key only in an object inside the block: the advice names no line to write over or to move, and her value stays
            ("src/config.ts", "an object inside the block whose lines are indented like the block's own", config.replace(own, "  social: {\n  themeColor: '#00ff00',\n  },\n"),
             "the one line of the block that begins with `themeColor:` (line 11) stands below a line that is not one whole entry on one line (line 10: `social: {`), so it may belong to something inside the block. "
             "With that in the block this tool cannot be sure from the text which value the site reads, so it does not edit this block. Set the value by hand: write that one line in place of the block's own "
             "`themeColor` line, or as the first line under the opening line (line 5) where the block has none of its own"),
            ("src/config.ts", "an object inside the block that holds the key as its last entry, with no comma", config.replace(own, "  pwa: {\n    themeColor: '#00ff00'\n  },\n"),
             "the one line of the block that begins with `themeColor:` (line 11) stands below a line that is not one whole entry on one line (line 10: `pwa: {`)"),
            # (round 7) the block's own line as its last entry, without a comma: "move the line up" left a file that was no TypeScript
            ("src/config.ts", "the key as the block's last entry, with no comma after it", config.replace(own, "").replace("} as const;", "  themeColor: '#000000'\n} as const;", 1),
             "the one line of the block that begins with `themeColor:` (line 17) stands below a line that is not one whole entry on one line (line 14: `description:`)"),
            ("src/config.ts", "a list above the key", config.replace(own, "  tags: ['bread', 'cake'],\n" + own),
             "the one line of the block that begins with `themeColor:` (line 11) stands below a line that is not one whole entry on one line (line 10: `tags: ['bread', 'cake'],`)"),
            ("src/config.ts", "the key a second time, with a value that is no colour", "const BRAND_COLOUR = '#111111';\n" + config.replace(own, own + "  themeColor: BRAND_COLOUR,\n"),
             "2 lines of the block begin with `themeColor:` (lines 11 and 12)"),
            ("src/config.ts", "the key again in an object inside the block, below it", config.replace(own, own + "  pwa: {\n    themeColor: '#00ff00',\n  },\n"),
             "line 12, in the same block, holds the name `themeColor` again (`themeColor: '#00ff00',`). With that in the block this tool cannot be sure from the text which value the site reads, so it does "
             "not edit this block. Set the value by hand: write that one line in place of line 10"),
            ("src/config.ts", "the key again in an object inside the block, above it", config.replace(own, "  pwa: {\n    themeColor: '#00ff00',\n  },\n" + own),
             "2 lines of the block begin with `themeColor:` (lines 11 and 13), each below a line that is not one whole entry on one line (line 10: `pwa: {`), so any of them may belong to something inside the block"),
            ("src/config.ts", "the key twice on one line", config.replace(own, "  themeColor: '#000000', themeColor: '#111111',\n"), "line 10 is written another way"),
            ("src/config.ts", "a value that is worked out", "const dark = false;\n" + config.replace(own, "  themeColor: dark ? '#111111' : '#000000',\n"),
             "line 11 is written another way: `themeColor: dark ? '#111111' : '#000000',`"),
            ("src/config.ts", "a quoted key under a regex with a quote", "const APOS = /'/g;\n" + config.replace(own, "  'themeColor': '#000000',\n"), "line 11 is written another way: its key is in quotes (`'themeColor': '#000000',`)"),
            # (round 8: every line above it has its key in quotes and is not plain, so the line is not named as the one to write over)
            ("src/config.ts", "every key of the block in quotes", re.sub(r"(?m)^  (\w+):", r"  '\1':", config.split("} as const;")[0]) + "} as const;" + config.split("} as const;", 1)[1],
             "the one line of the block that begins with `'themeColor':` (line 10) stands below a line that is not one whole entry on one line (line 6: `'url': 'https://example.com', // production origin, no trailing slash`)"),
            ("src/config.ts", "a key in quotes inside an object of the block, and none in the block itself", config.replace(own, "  pwa: {\n    'themeColor': '#00ff00',\n  },\n"),
             "the one line of the block that begins with `'themeColor':` (line 11) stands below a line that is not one whole entry on one line (line 10: `pwa: {`)"),
            ("src/config.ts", "another entry after the key's on its line", config.replace(own, "  themeColor: '#000000', region: 'eu',\n"),
             "Write that one line in place of the entry, and keep what stands after the entry on line 10 (`region: 'eu',`) on a line of its own below it"),
            ("src/config.ts", "a comment that does not end on its line, in the block", config.replace(own, own + "  /* the titles:\n     how each page is called */\n"), "line 11, in the same block, holds `/*`"),
            ("src/config.ts", "a list further down, which this tool cannot tell from a computed key", config.replace("} as const;\n", "  tags: ['bread', 'cake'],\n} as const;\n", 1),
             "line 18, in the same block, holds `[` (`tags: ['bread', 'cake'],`). With that in the block this tool cannot be sure from the text which value the site reads, so it does not edit this block"),
            ("src/config.ts", "a copy of the whole block in a comment", "/*\nexport const SITE = {\n  url: 'https://old.example',\n};\n*/\n" + config, "2 lines (lines 2 and 10), not one, that start `export const SITE`"),
            ("public/manifest.webmanifest", "its own entry the manifest's last, with a value that is no text", manifest.replace('  "theme_color": "#000000",\n', "").replace('  ]\n}', '  ],\n  "theme_color": 0\n}'),
             'line 14 is written another way: `"theme_color": 0`. Write that one line in its place (with no comma after it, as shown: it is the manifest\'s last entry)'),
            ("public/manifest.webmanifest", "an empty manifest", "{}\n", "Write that one line on a line of its own between the manifest's `{` and its `}` (with no comma after it, as shown: it is the manifest's last entry)"),
            ("public/manifest.webmanifest", "the name on one line and the value on the next", manifest.replace('"theme_color": "#000000"', '"theme_color":\n    "#000000"'),
             "Write that one line in place of lines 9 to 10, which it replaces together"),
            ("public/manifest.webmanifest", "the name on one line, its value over the next three, and another entry after it on the last", manifest.replace('"theme_color": "#000000",', '"theme_color":\n    [\n      0\n    ], "x": 1,'),
             'Write that one line in place of lines 9 to 12, which it replaces together, and keep what stands after the entry on line 12 (`"x": 1,`) on a line of its own below it'),
            ("public/manifest.webmanifest", "a manifest on one line", '{"name":"X","background_color":"#ffffff","theme_color":0}\n', 'Set the value yourself on line 1: put "#b4531a", in its quotes, where the value of "theme_color" stands now'),
            ("public/manifest.webmanifest", "another entry with colours of the same names", manifest.replace('  "lang": "en",', NESTED_SHORTCUT, 1), 'the name "theme_color" stands 2 times in the file (lines 6 and 10)'),
            ("public/manifest.webmanifest", "no theme colour of its own", manifest.replace('  "theme_color": "#000000",\n', ""), 'the name "theme_color" is not in the file'),
            # (round 7) an entry of that name inside another entry, and none of the manifest's own: hers is never the one to write over
            ("public/manifest.webmanifest", "a number of that name inside another entry, and none of the manifest's own",
             manifest.replace('  "theme_color": "#000000",\n', "").replace('  "lang": "en",', '  "lang": "en",\n  "related": { "theme_color": 0 },'),
             'the one place where "theme_color" stands (line 6) is not the manifest\'s own entry: it belongs to something inside the manifest. Write that one line as the first line under the manifest\'s opening `{`'),
            ("public/manifest.webmanifest", "a value over two lines of that name inside another entry, and none of the manifest's own",
             manifest.replace('  "theme_color": "#000000",\n', "").replace('  "lang": "en",', '  "lang": "en",\n  "related": {\n    "theme_color":\n      "#111111"\n  },'),
             'the one place where "theme_color" stands (line 7) is not the manifest\'s own entry: it belongs to something inside the manifest. Write that one line as the first line under the manifest\'s opening `{`'),
            ("public/manifest.webmanifest", "a manifest that is not valid JSON", manifest.replace('"standalone",', '"standalone",,'), "public/manifest.webmanifest is not valid JSON ("),
            ("public/manifest.webmanifest", "a value that Python's reader takes and the site's does not", manifest.replace('"lang": "en",', '"lang": "en", "ratio": NaN,'),
             "public/manifest.webmanifest is not valid JSON (it holds NaN, which JSON does not have)"),
            # the generator: every way Python binds a name is counted, by Python's own parser
            ("scripts/generate_og_cards.py", "a colour set again further down", generator.replace(home, "BG_BOT = (200, 200, 200)   # my override\n\n" + home, 1), "BG_BOT is set or bound 2 times (lines 53 and 59)"),
            ("scripts/generate_og_cards.py", "a colour set again in a tuple with other names", generator.replace(home, "spare, BG_TOP, other = None, (1, 2, 3), None\n\n" + home, 1),
             "BG_TOP is set or bound 2 times (lines 52 and 59)"),
            ("scripts/generate_og_cards.py", "a colour added to further down", generator.replace(home, "BG_TOP += (1,)\n\n" + home, 1), "BG_TOP is set or bound 2 times (lines 52 and 59)"),
            ("scripts/generate_og_cards.py", "a colour set inside an expression", generator.replace(home, "print((BG_TOP := (1, 2, 3)), file=sys.stderr)\n\n" + home, 1), "BG_TOP is set or bound 2 times (lines 52 and 59)"),
            ("scripts/generate_og_cards.py", "a colour with a type", generator.replace("BG_TOP = (30, 33, 64)", "BG_TOP: tuple = (30, 33, 64)", 1), "line 52 sets it another way: `BG_TOP: tuple = (30, 33, 64)"),
            ("scripts/generate_og_cards.py", "a colour that is worked out", generator.replace("BG_TOP = (30, 33, 64)", "BG_TOP = tuple([30, 33, 64])", 1), "line 52 sets it another way: `BG_TOP = tuple([30, 33, 64])"),
            ("scripts/generate_og_cards.py", "two names set at once", generator.replace("BG_TOP = (30, 33, 64)", "BG_TOP = BG_BOT = (30, 33, 64)", 1), "line 52 sets it another way"),
            ("scripts/generate_og_cards.py", "a number Python does not read", generator.replace("BG_BOT = (10, 11, 30)", "BG_BOT = ( 010, 11, 30)", 1),
             "scripts/generate_og_cards.py is not Python that this tool can read (Python %d.%d says: line 53: " % sys.version_info[:2]),
            ("scripts/generate_og_cards.py", "every name of a module imported", generator.replace(home, "from os import *\n\n" + home, 1), "scripts/generate_og_cards.py, line 59: `from os import *` brings in names this tool cannot see"),
        )
        for rel, name, text, said in cases:
            with self.subTest(rel=rel, name=name):
                self.assertNotEqual(text, T.starter_file(rel))
                self.fresh()
                self.put(rel, text)
                refusals, hers = [], []
                for _round in range(6):
                    before = self.snapshot()
                    (dry_code, dry), (code, out) = self.both_runs()
                    if (dry_code, code) == (0, 0):
                        break
                    self.assertEqual((dry_code, code), (2, 2), out)
                    head = out.split("\nNothing was written.")[0]
                    self.assertEqual(dry.split("\nNothing was written.")[0], head, "the dry run refuses in the same words")
                    self.assertIn("Nothing was written.", out)
                    self.assertEqual(self.snapshot(), before, "a refusal leaves every file as it was")
                    self.assertNotIn(head, refusals, "the same refusal a second time: doing what it said did not help")
                    refusals.append(head)
                    if head.startswith("%s: this tool sets " % rel):
                        self.assertEqual(len(head.split("\n")), 3, "the line it shows stands alone on a line of the report, with nothing before it")
                        if advice(head).startswith(("Write that one line", "Set the value by hand", "Set the value yourself on the manifest's own line", "Leave one of them")):
                            hers.append(shown_line(head))
                    self.put(rel, self.follow(rel, self.read(rel), out))
                self.assertEqual((dry_code, code), (0, 0), out)
                self.assertTrue(refusals, "it was refused at first")
                self.assertIn(said, refusals[0])
                for line in hers:
                    self.assertIn(line, self.read(rel).split("\n"), "the line she wrote stands as the refusal showed it, to the letter, and was left so")
                # and what the site now reads from that file is the palette: asked of Node and of Python, not of this tool
                reads = self.as_the_site_reads(rel)
                if rel == "src/config.ts":
                    self.assertEqual(len(re.findall(r"(?m)^[ \t]*themeColor: '#b4531a',", self.read(rel))), 1)
                    self.assertEqual(self.read(rel).count("themeColor: '#00ff00'"), text.count("themeColor: '#00ff00'"), "a value of hers inside the block is where it was: nothing said to take it out, to move it or to write over it")
                    if reads is not None:
                        self.assertEqual(reads.get("themeColor"), "#b4531a", reads)
                elif rel == "public/manifest.webmanifest":
                    data = json.loads(self.read(rel))
                    self.assertEqual((data["theme_color"], data["background_color"]), ("#b4531a", "#fff8ee"))
                    self.assertEqual(data.get("related"), json.loads(text).get("related") if "related" in text else None, "what stands inside another entry is hers, and as it was")
                    if reads is not None:
                        self.assertEqual(reads, {"theme_color": "#b4531a", "background_color": "#fff8ee"})
                else:
                    self.assertEqual((reads.get("BG_TOP"), reads.get("BG_BOT")), ([42, 31, 23], [26, 18, 13]), reads)

    def test_every_file_of_the_starter_and_the_same_files_as_a_formatter_leaves_them_are_edited_and_read_back_by_the_site(self):
        # the starter's own three files, and the same after a formatter's ordinary changes: nothing is refused, each
        # value changes once, and what Node and Python then read is what the report says
        config, manifest, generator = (T.starter_file(rel) for rel in _install.OTHER_FILES)
        formatted = config.replace("'", '"').replace("export const SITE = {", "export const SITE: Record<string, string> = {").replace("} as const;", "} as const satisfies Record<string, string>;", 1) \
                          .replace('character window.",\n}', 'character window."\n}')
        shapes = (("the starter as it stands", {}),
                  ("as a formatter leaves them", {"src/config.ts": formatted, "public/manifest.webmanifest": manifest.replace("  ", "\t"),
                                                  "scripts/generate_og_cards.py": generator.replace("BG_TOP = (30, 33, 64)  ", "BG_TOP = (30,33,64)")}),
                  ("with windows line ends", {rel: T.starter_file(rel).replace("\n", "\r\n") for rel in _install.OTHER_FILES}))
        for name, files in shapes:
            with self.subTest(name=name):
                self.fresh()
                for rel, text in files.items():
                    self.assertNotEqual(text, T.starter_file(rel))
                    with open(self.p(rel), "w", encoding="utf-8", newline="") as f:
                        f.write(text)
                (dry_code, dry), (code, out) = self.both_runs("--json")
                self.assertEqual((dry_code, code), (0, 0), out)
                changes = json.loads(out)["changes"]
                self.assertEqual(json.loads(dry)["changes"], changes)
                for line in ("src/config.ts, themeColor: #000000 becomes #b4531a", "public/manifest.webmanifest, theme_color: #000000 becomes #b4531a",
                             "public/manifest.webmanifest, background_color: #ffffff becomes #fff8ee", "scripts/generate_og_cards.py, BG_TOP: #1e2140 becomes #2a1f17",
                             "scripts/generate_og_cards.py, FOOTER_COL: #9696aa becomes #c4ae98"):
                    self.assertIn(line, changes)
                self.assertEqual(self.as_the_site_reads("scripts/generate_og_cards.py"), {n: [int(bakery().dark[k][i:i + 2], 16) for i in (1, 3, 5)] for n, k in _site.OG_COLOURS})
                if not node_problem(typescript=True):
                    self.assertEqual(self.as_the_site_reads("src/config.ts"), {"themeColor": "#b4531a", "logo": "/images/logo.png"})
                    self.assertEqual(self.as_the_site_reads("public/manifest.webmanifest"), {"theme_color": "#b4531a", "background_color": "#fff8ee"})
                self.assertEqual(json.loads(self.intake("--json", "--dry-run")[1])["changes"], [], "and a second run finds every value there")

    def test_a_value_she_wrote_in_capitals_or_in_another_spelling_is_the_same_colour_no_change_and_not_edited(self):
        self.brand_md()
        self.assertEqual(self.intake()[0], 0)
        by_hand = {"src/config.ts": self.read("src/config.ts").replace("'#b4531a'", "'#B4531A'"),
                   "public/manifest.webmanifest": self.read("public/manifest.webmanifest").replace('"#b4531a"', '"#B4531AFF"').replace('"#fff8ee"', '"#FFF8EE"'),
                   "scripts/generate_og_cards.py": self.read("scripts/generate_og_cards.py").replace("BG_TOP = (42, 31, 23)", "BG_TOP = ( 42,31 ,23 )")}
        for rel, text in by_hand.items():
            self.assertNotEqual(text, self.read(rel))
            self.put(rel, text)
        before = self.snapshot()
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code), (0, 0), out)
        for report in (dry, out):
            self.assertEqual(json.loads(report)["changes"], [], "the same colours, spelt her way, are no change")
            self.assertEqual(json.loads(report)["written"], [])
        after = self.snapshot()
        cards = {k for k in after if k.startswith(os.path.join("public", "images", "og"))}
        self.assertEqual({k: v for k, v in after.items() if k not in cards}, {k: v for k, v in before.items() if k not in cards}, "every file but the cards, which are made again")
        # one that is another colour is a change, shown as it stood
        self.put("public/manifest.webmanifest", by_hand["public/manifest.webmanifest"].replace('"#B4531AFF"', '"#B4531B"'))
        self.assertEqual(json.loads(self.intake("--json", "--dry-run")[1])["changes"], ["public/manifest.webmanifest, theme_color: #B4531B becomes #b4531a"])

    # --- round 4 ---------------------------------------------------------------------------------------

    def test_an_empty_file_in_the_share_cards_folder_is_kept_like_any_other_and_stops_no_run(self):
        # the largest file of the folder was looked for by comparing (size, name) pairs, and an empty `.gitkeep`
        # met first was compared with no name at all: the planning stopped with a TypeError, the dry run too
        for label, names, alone in (("first in the folder", (".gitkeep",), False), ("last in the folder", ("zz-placeholder",), False),
                                    ("alone in the folder", (".gitkeep",), True), ("two of them", (".gitkeep", "zz-placeholder"), False)):
            with self.subTest(label=label):
                self.fresh()
                if alone:
                    for n in os.listdir(self.p(_install.CARDS)):
                        os.remove(os.path.join(self.p(_install.CARDS), n))
                for n in names:
                    self.put(_install.CARDS + "/" + n, b"")
                (dry_code, dry), (code, out) = self.both_runs("--json")
                self.assertEqual((dry_code, code), (0, 0), out)
                self.assertEqual((json.loads(dry)["status"], json.loads(out)["status"]), ("dry-run", "done"))
                for n in names:
                    self.assertEqual(self.bytes(_install.CARDS + "/" + n), b"", "the empty file is still there, and still empty")
        self.fresh()
        self.put(_install.CARDS + "/.gitkeep", b"")
        before = self.snapshot()
        code, out = self.intake(command="rm -f public/images/og/.gitkeep public/images/og/default.jpg; exit 1")
        self.assertEqual(code, 1, out)
        self.assertEqual(self.snapshot(), before, "and when the run is taken back, it is put back like any other file")

    def test_a_dark_value_that_neither_dark_block_holds_once_the_stylesheet_is_written_is_named_for_each_block(self):
        # two rows that are both not there are not "alike": the read-back held `None == None` for agreement and
        # named the row once at most, for the first block only
        real = _site.edit_css

        def dropping(text, palette):
            seen, kept = 0, []
            for line in real(text, palette).split("\n"):
                muted = bool(re.match(r"\s*--muted:", line))
                seen += muted
                if not (muted and seen > 1):   # the light theme's stays; both dark blocks lose theirs
                    kept.append(line)
            return "\n".join(kept)
        both = "Muted, dark theme %s unreadable, not #c4ae98; Muted, dark theme for visitors without JavaScript %s unreadable, not #c4ae98"
        self.brand_md()
        before = self.snapshot()
        _site.edit_css = dropping
        try:
            runs = self.both_runs("--json")
        finally:
            _site.edit_css = real
        for code, out in runs:
            data = json.loads(out)
            self.assertEqual((code, data["status"], data["code"]), (2, "refused", "css-layout"), out)
            self.assertIn(both % ("would be", "would be"), data["message"])
        self.assertEqual(self.snapshot(), before)
        # and the reading after the write, which is the last look before the tests run: the stylesheet as it is
        # read back from the site then lacks the row in both blocks
        dropped = dropping(self.read("src/styles/global.css"), bakery())
        real_read, reads = _install._read_text, []

        def read_back(path, rel=None):
            if rel == _install.STYLESHEET:
                reads.append(path)
                if len(reads) > 1:
                    return dropped
            return real_read(path, rel)
        _install._read_text = read_back
        try:
            code, out = self.intake("--json")
        finally:
            _install._read_text = real_read
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["code"], len(reads)), (2, "refused", "check-failed", 2), out)
        self.assertIn(both % ("is", "is"), data["message"])
        self.assertEqual(self.snapshot(), before, "and everything it had written was put back")
        css = type("Css", (), {"brand": "#b4531a", "light": dict(T.BAKERY_LIGHT), "dark": dict(T.BAKERY_DARK, muted="#111111"), "dark_media": dict(T.BAKERY_DARK, muted="#111111")})()
        self.assertEqual(_install._differences(css, bakery()), [("Muted, dark theme", "#111111", "#c4ae98")], "a value that both blocks do hold, and hold alike, is still named once")

    def test_a_colour_under_a_name_the_palette_check_does_not_know_is_said_not_to_be_read_and_never_passed_over(self):
        # (the reader names every colour that stands under a name it does not know: nothing is "unused" in silence)
        self.brand_md(BAKERY_BRAND_MD + "| Fancy | `#123456` |\n")
        code, out = run("palette", self.p("BRAND.md"))
        self.assertEqual(code, 2, out)
        self.assertRegex(out, r'Not read: Line \d+, "\| Fancy \| `#123456` \|", holds a colour \(#123456\) that was not read')
        data = json.loads(run("palette", self.p("BRAND.md"), "--json")[1])
        self.assertEqual((data["exit"], data["status"], [x["code"] for x in data["problems"]]), (2, "incomplete", ["palette-colour-not-read"]))
        self.assertNotIn("unused", json.dumps(data))
        before = self.snapshot()
        for code, out in self.both_runs("--with-colours"):
            self.assertEqual(code, 2, out)
            self.assertIn("holds a colour (#123456) that was not read", out)
            self.assertEqual(self.snapshot(), before)

    def test_an_empty_test_command_is_refused_by_name_and_the_sites_own_command_is_not_run_in_its_place(self):
        self.brand_md()
        before = self.snapshot()
        for command in ("", "   ", "\t\n"):
            with self.subTest(command=command):
                for code, out in self.both_runs("--json", command=command):
                    data = json.loads(out)
                    self.assertEqual((code, data["status"], data["code"]), (2, "refused", "bad-argument"), out)
                    self.assertTrue(data["message"].startswith("--test-command was given with no command in it."), data["message"])
                    self.assertIn("leave --test-command out to run the site's own: npm run build && npm test", data["message"])
                    self.assertIn("Nothing was written.", data["report"])
                    self.assertEqual(self.snapshot(), before)

    def test_a_stop_takes_this_runs_lines_out_of_the_report_and_leaves_what_the_caller_had_written_there(self):
        import argparse
        self.brand_md()
        a = argparse.Namespace(site=self.site, palette=None, input=None, pick=None, mono=None, with_colours=False, keep_colours=False, with_logo=False, accept_colours=False,
                               accept_low_contrast="", replace_icons=False, test_command=GREEN, dry_run=False)
        real = _site.edit_css

        def stopped(text, palette):
            raise _install.Interrupted(signal.SIGTERM)
        out = ["a line the caller had written before the run", "and a second one"]
        handlers = [(sig, signal.getsignal(sig)) for sig in STOP_SIGNALS]
        _site.edit_css = stopped
        try:
            code, status, _data = _install.install(a, out)
        finally:
            _site.edit_css = real
            for sig, handler in handlers:
                signal.signal(sig, handler)
        self.assertEqual((code, status), (2, "stopped"))
        self.assertEqual(out[:2], ["a line the caller had written before the run", "and a second one"])
        self.assertTrue(out[2].startswith("The run was stopped from outside (SIGTERM)"), out)
        self.assertIn("Nothing was written.", out)

    @POSIX
    def test_cards_whose_folder_the_tests_took_away_with_the_folder_above_it_are_put_back_all_the_same(self):
        self.brand_md()
        before = self.snapshot()
        for command in ("rm -rf public/images/og; exit 1", "rm -rf public/images; exit 1"):
            with self.subTest(command=command):
                code, out = self.intake("--json", command=command)
                data = json.loads(out)
                self.assertEqual((code, data["status"], data.get("not_restored")), (1, "tests-failed", None), out)
                self.assertIn("so everything was put back (every file, the share cards included)", data["report"][0])
                self.assertEqual(self.snapshot(), before)

    # --- round 5: the read-back ------------------------------------------------------------------------
    # Three rounds each found a src/config.ts on which a rule that reads lines was wrong about what the site
    # reads. So the report's word on src/config.ts and on the generator rests on asking: once the files are
    # written, and before the site's tests run, the site's Node says what it reads and Python what the
    # generator's names are bound to.

    READ_OK = {"src/config.ts": {"status": "ok"}, "scripts/generate_og_cards.py": {"status": "ok"}}
    ASKS = ("A real run then asks the site's Node and Python what the site reads from src/config.ts and scripts/generate_og_cards.py: it puts everything back if that is not "
            "what it set, and adds a note where it could not ask. A dry run writes nothing, so it cannot ask.")
    ELSE = ", so something else in the file decides the value. Set it by hand where the file decides it, or have the developer mend the file, then run this again."
    # (round 8) where the site reads no value at all and the line that says it is not surely the block's own: nothing else decides the value, the block has none
    NO_OWN = (", but the `SITE` block has no `themeColor` of its own: the line that says it belongs to something inside the block. Write `themeColor: '#b4531a',` as the first line under the "
              "block's opening line (it starts `export const SITE`), and where that other line was changed to say #b4531a, put back what it said before. Then run this again.")

    def test_the_starter_as_it_stands_is_read_back_by_node_and_python_and_no_note_is_needed(self):
        self.need_read_back()
        self.fresh()
        (dry_code, dry), (code, out) = self.both_runs("--json")
        dry, done = json.loads(dry), json.loads(out)
        self.assertEqual((dry_code, code, dry["status"], done["status"]), (0, 0, "dry-run", "done"), out)
        self.assertEqual((dry["read_back"], done["read_back"]), ({}, self.READ_OK), "a dry run writes nothing and so reads nothing back; the real run asked both, and both read what it set")
        self.assertEqual((self.ASKS in dry["report"], self.ASKS in done["report"]), (True, False), "the one way the two differ is said by the dry run, in one line")
        self.assertEqual([n for n in dry["notes"] + done["notes"] if "could not check" in n], [])
        self.assertIn("in the theme colour and the manifest, and in the share cards.", [l for l in done["report"] if l.startswith("Colours: ")][0])
        # a second run: every value is there, none is edited, and each is read back all the same. Python is asked as
        # the owner's shell would start it, and still writes nothing into the site (no __pycache__ beside the generator).
        kept = os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
        try:
            code, out = self.intake("--json")
        finally:
            if kept is not None:
                os.environ["PYTHONDONTWRITEBYTECODE"] = kept
        again = json.loads(out)
        self.assertEqual((code, again["written"], again["read_back"]), (0, [], self.READ_OK), out)
        self.assertEqual([n for n in os.listdir(self.p("scripts")) if "pycache" in n], [], "asking Python left something in the site")
        self.assertIn(self.ASKS, self.intake("--dry-run")[1].splitlines())
        # a byte order mark at the start of both files (and windows line ends in one): read past, kept, and read back
        self.fresh()
        marked = {"src/config.ts": "\ufeff" + T.starter_file("src/config.ts").replace("\n", "\r\n"), "scripts/generate_og_cards.py": "\ufeff" + T.starter_file("scripts/generate_og_cards.py")}
        for rel, text in marked.items():
            with open(self.p(rel), "w", encoding="utf-8", newline="") as f:
                f.write(text)
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, json.loads(out)["read_back"]), (0, 0, self.READ_OK), out)
        self.assertEqual(json.loads(dry)["changes"], json.loads(out)["changes"])
        self.assertIn("src/config.ts, themeColor: #000000 becomes #b4531a", json.loads(out)["changes"])
        for rel in marked:
            with open(self.p(rel), encoding="utf-8", newline="") as f:
                now = f.read()
            self.assertTrue(now.startswith("\ufeff") and now.count("\ufeff") == 1, "the mark is still there, once")
        self.assertIn("themeColor: '#b4531a',", self.read("src/config.ts"))
        self.assertIn("\nBG_TOP = (42, 31, 23) ", self.read("scripts/generate_og_cards.py"))

    def test_what_stands_outside_the_block_and_changes_nothing_stops_no_run_a_licence_header_or_a_line_that_reads_the_value_least_of_all(self):
        # Round 5 refused each of these from the text: a comment over several lines above a block ("move the block to
        # the top of the file", for a licence header), a line that reads the object beside a write to something else
        # ("take that out of line N": working code). All of them in one file: the run goes through, and Node reads
        # what it set.
        self.need_read_back()
        config = T.starter_file("src/config.ts")
        hers = ("/*\n * Copyright (c) the owner of the site.\n * Don't remove this header.\n */\nconst notes = `\n  themeColor: '#111111',\n`;\nconst x = 1; // SITE.themeColor = '#111'\n"
                + config.replace("export const SITE", "/**\n * What the whole site reads.\n */\nexport const SITE").replace("export const COMPANY", "/**\n * The company, for the schema.\n * @see SITE\n */\nexport const COMPANY")
                + "const cache: Record<string, number> = {};\nexport function reset() { delete cache[SITE.url]; delete cache[SITE.themeColor]; }\n"
                "const other = { themeColor: '' }; const s = SITE; other.themeColor = s.name;\nlet i = 0; export const v = [SITE, COMPANY][i++].themeColor;\n"
                "export const TITLE = SITE['name']; export const X: string[] = [];\n// @ts-ignore\nSITE.themeColor ||= '#111111';\n"
                "// SITE.themeColor = '#111111';\n// delete this note once SITE has its real url\n")
        self.fresh()
        self.put("src/config.ts", hers)
        (dry_code, dry), (code, out) = self.both_runs("--json")
        data = json.loads(out)
        self.assertEqual((dry_code, code, data["status"], data["read_back"]), (0, 0, "done", self.READ_OK), out)
        self.assertEqual([n for n in data["notes"] if "could not check" in n], [])
        self.assertEqual(self.read("src/config.ts"), hers.replace("themeColor: '#000000'", "themeColor: '#b4531a'"), "that one value, and not a byte else")
        self.assertIn("in the theme colour and the manifest, and in the share cards.", [l for l in data["report"] if l.startswith("Colours: ")][0])

    def test_a_value_the_site_does_not_read_from_where_it_stands_ends_the_run_with_everything_put_back_and_set_by_hand_it_passes(self):
        # The counterexamples of round 5, and their kind: the text says one thing and the site reads another. Each
        # ends at the read-back (or at the closing line's refusal, and then at the read-back): exit status 1,
        # the site as before, a sentence that names what the site reads, what this run set and on which line.
        # Doing what the sentence says (the value set by hand where the file decides it) makes the next run pass.
        self.need_read_back()
        config, generator = T.starter_file("src/config.ts"), T.starter_file("scripts/generate_og_cards.py")
        own = "  themeColor: '#000000',               // matches the brand primary + manifest\n"
        home = "# Home + fallback card"
        node, python = "(this tool asked the site's own Node). ", "once the file's own top has run (this tool asked Python). "
        # a template string that runs over lines and holds another: two backticks on its first line, and what looks
        # like the block is text inside it. The object the site reads is exported under the name further down.
        in_a_text = ("const n = 1;\nconst doc = `how to set it ${n ? `like this:\nexport const SITE = {\n  themeColor: '#000000',\n};\n` : ''} and so on`;\n"
                     + config.replace("export const SITE = {", "const REAL = {").replace("'#000000'", "'#111111'") + "export { REAL as SITE };\n")
        # the block's own closing brace is indented, so the tool takes a later `}` at a line's start for the close,
        # and what stands between the two is seen neither as the block's nor as outside it
        indented = "const changes = { themeColor: '#111111' };\n" + config.replace("} as const;", "  } as const;\nObject.assign(SITE, changes);\nexport function half(n: number) {\n  return n / 2;\n}", 1)
        cases = (
            ("another object joined on to the closing line", "src/config.ts", config.replace("} as const;", "} && { themeColor: '#111111' };", 1), "line 18 closes the block with more than its `}`",
             {"name": "themeColor", "reads": "#111111", "wanted": "#b4531a"}, "the site reads #111111 as SITE.themeColor " + node + "Line 10 already says #b4531a, and this run left it",
             lambda t: t.replace("} && { themeColor: '#111111' };", "} && { themeColor: '#b4531a' };")),
            ("the key a second time below it, in quotes, which is the one the site reads", "src/config.ts", config.replace(own, own + "  'themeColor': '#111111',\n"), "line 11, in the same block, holds the name `themeColor` again",
             {"name": "themeColor", "reads": "#111111", "wanted": "#b4531a"}, "the site reads #111111 as SITE.themeColor " + node + "Line 10 already says #b4531a, and this run left it",
             lambda t: t.replace("'themeColor': '#111111'", "'themeColor': '#b4531a'")),
            ("the block as a text inside a template string that holds another", "src/config.ts", in_a_text, None,
             {"name": "themeColor", "reads": "#111111", "wanted": "#b4531a"}, "the site reads #111111 as SITE.themeColor " + node + "This run set #b4531a on line 4", lambda t: t.replace("'#111111'", "'#b4531a'")),
            ("the block's closing brace indented, and the object changed before the next brace at a line's start", "src/config.ts", indented, None,
             {"name": "themeColor", "reads": "#111111", "wanted": "#b4531a"}, "the site reads #111111 as SITE.themeColor " + node + "This run set #b4531a on line 11", lambda t: t.replace("'#111111'", "'#b4531a'")),
            # (round 7) A line that already says the value below a line that is not one whole entry is left as it stands with no
            # other guard: it may be a part of something inside the block. The read-back is the guard, and names no line.
            ("the key only in an object inside the block, with the colour wanted", "src/config.ts", config.replace(own, "  social: {\n  themeColor: '#b4531a',\n  },\n"), None,
             {"name": "themeColor", "reads": "nothing", "wanted": "#b4531a"}, "the site reads nothing as SITE.themeColor " + node + "The file already says #b4531a, and this run left it" + self.NO_OWN,
             lambda t: follow_read_back(t, "src/config.ts: the site reads nothing as SITE.themeColor " + node + "The file already says #b4531a, and this run left it" + self.NO_OWN)),   # (round 8: the sentence, to the character)
            ("the colour wanted in an object inside the block, on one line of its own, and the block's own line below it says another", "src/config.ts", config.replace(own, "  pwa: {\n    themeColor: '#b4531a',\n  },\n" + own), None,
             {"name": "themeColor", "reads": "#000000", "wanted": "#b4531a"}, "the site reads #000000 as SITE.themeColor " + node + "The file already says #b4531a, and this run left it",
             lambda t: t.replace("themeColor: '#000000'", "themeColor: '#b4531a'")),
            ("the colour wanted in an object inside the block, written on one line, and the block's own line says another", "src/config.ts", config.replace(own, own + "  pwa: { themeColor: '#b4531a' },\n"),
             "line 11, in the same block, holds the name `themeColor` again (`pwa: { themeColor: '#b4531a' },`)", None, None, None),
            # the generator: a write that Python's parser does not show as a binding of the name
            ("a colour set through globals() further down", "scripts/generate_og_cards.py", generator.replace(home, "globals().update(BG_TOP=(1, 2, 3))\n\n" + home, 1), None,
             {"name": "BG_TOP", "reads": "#010203", "wanted": "#2a1f17"}, "Python has BG_TOP bound to #010203 " + python + "This run set #2a1f17 on line 52", lambda t: t.replace("BG_TOP=(1, 2, 3)", "BG_TOP=[42, 31, 23]")),   # (a list of the three numbers is the colour too)
            ("a colour set on the module itself further down", "scripts/generate_og_cards.py", generator.replace(home, "sys.modules[__name__].FOOTER_COL = 'grey'\n\n" + home, 1), None,
             {"name": "FOOTER_COL", "reads": "'grey'", "wanted": "#c4ae98"}, "Python has FOOTER_COL bound to 'grey' " + python + "This run set #c4ae98 on line 57", lambda t: t.replace("sys.modules[__name__].FOOTER_COL = 'grey'\n", "")),
        )
        for label, rel, text, refused_first, value, saying, by_hand in cases:
            with self.subTest(label=label):
                self.fresh()
                self.put(rel, text)
                if refused_first:   # the rule's own refusal comes first, and what it says to do (the line written by hand) leads to the read-back
                    (dry_code, dry), (code, out) = self.both_runs()
                    self.assertEqual((dry_code, code), (2, 2), out)
                    self.assertIn(refused_first, out)
                    self.put(rel, self.follow(rel, self.read(rel), out))
                if value is None:   # ... or to a run that passes: the block's own line is the one the site reads
                    code, out = self.intake("--json")
                    self.assertEqual((code, json.loads(out)["status"], json.loads(out)["read_back"]), (0, "done", self.READ_OK), out)
                    self.assertIn("pwa: { themeColor: '#b4531a' },", self.read(rel))
                    continue
                before = self.snapshot()
                (dry_code, dry), (code, out) = self.both_runs("--json")
                dry, data = json.loads(dry), json.loads(out)
                self.assertEqual((dry_code, dry["status"], self.ASKS in dry["report"]), (0, "dry-run", True), "the dry run cannot know, and says that a real run asks")
                self.assertEqual((code, data["status"], data["exit"], data.get("not_restored")), (1, "read-back-failed", 1, None), out)
                self.assertEqual(data["read_back"][rel], {"status": "differs", "values": [value]})
                self.assertEqual(data["report"][0], "A check failed after the files were written: what the site reads is not what this run set.")
                self.assertEqual(data["report"][1], "%s: %s%s" % (rel, saying, "" if saying.endswith(self.NO_OWN) else self.ELSE))
                self.assertEqual(data["report"][2], "Everything it had written was put back.")
                self.assertEqual((data["written"], data["tests"], data["cards"]), ([], None, None), "the site's tests were not run on it, nor the cards made")
                self.assertEqual(self.snapshot(), before, "the site is as it was before the run")
                self.put(rel, by_hand(self.read(rel)))   # what the sentence says to do: the value set by hand where the file decides it
                self.assertNotEqual(self.read(rel), text)
                code, out = self.intake("--json")
                self.assertEqual((code, json.loads(out)["status"], json.loads(out)["read_back"]), (0, "done", self.READ_OK), out)
        # What rules (d) and (e) of round 5 refused from the text (a write to the object outside its block; a block
        # that stands inside a comment or a text): the line is edited, the site is asked, and the run ends here.
        for label, text, reads in changed_outside_the_block(config):
            with self.subTest(label=label):
                self.fresh()
                self.put("src/config.ts", text)
                before = self.snapshot()
                code, out = self.intake("--json")
                data = json.loads(out)
                self.assertEqual((code, data["status"], data["written"], data.get("not_restored")), (1, "read-back-failed", [], None), out)
                self.assertEqual(data["read_back"]["src/config.ts"], {"status": "differs", "values": [{"name": "themeColor", "reads": reads, "wanted": "#b4531a"}]})
                at = text.split("\n").index(own.rstrip("\n") if own in text else "  themeColor: '#000000',") + 1
                self.assertEqual(data["report"][1:3], ["src/config.ts: the site reads %s as SITE.themeColor %sThis run set #b4531a on line %d%s" % (reads, node, at, self.ELSE), "Everything it had written was put back."])
                self.assertEqual(self.snapshot(), before, "the site is as it was before the run")
        # where Node is not there to ask, the same file goes in, and the note says what nobody checked
        self.fresh()
        self.put("src/config.ts", config + "// @ts-ignore\nSITE.themeColor = '#111111';\n")
        real = shutil.which
        shutil.which = lambda name, *a, **k: None if name == "node" else real(name, *a, **k)
        try:
            code, out = self.intake("--json")
        finally:
            shutil.which = real
        self.assertEqual((code, json.loads(out)["status"]), (0, "done"), out)
        self.assertIn("this tool could not check that the site reads `themeColor` from line 10 of src/config.ts, where it is set: Node is not installed here, or is not on the path", json.loads(out)["notes"])
        # the same for a value that is left as it stands inside the block: the note names the file, and no line (round 7)
        for label, block in (("no line of the block's own", "  pwa: {\n    themeColor: '#b4531a',\n  },\n"), ("the block's own line says another value", "  pwa: {\n    themeColor: '#b4531a',\n  },\n" + own)):
            with self.subTest(label=label, node="not there"):
                self.fresh()
                self.put("src/config.ts", config.replace(own, block))
                shutil.which = lambda name, *a, **k: None if name == "node" else real(name, *a, **k)
                try:
                    code, out = self.intake("--json")
                finally:
                    shutil.which = real
                self.assertEqual((code, json.loads(out)["status"]), (0, "done"), out)
                self.assertEqual([n for n in json.loads(out)["notes"] if "could not check" in n],
                                 ["this tool could not check that the site reads `themeColor` from src/config.ts, where it is set: Node is not installed here, or is not on the path"])
                self.assertEqual(self.read("src/config.ts"), config.replace(own, block), "not a byte of the file was changed")
        # in words too, and both values of src/config.ts when both are read otherwise
        self.fresh()
        self.put("src/config.ts", config.replace("} as const;", "} && { themeColor: '#B4531A' };", 1).replace("themeColor: '#000000'", "themeColor: '#b4531a'"))
        code, out = self.intake()
        self.assertEqual(code, 0, "the same colour in another spelling is the same colour: " + out)
        self.put("src/config.ts", self.read("src/config.ts").replace("'#B4531A'", "'#111111'"))
        before = self.snapshot()
        code, out = self.intake()   # every file already holds the palette: the run has nothing to write, and the check is made all the same
        self.assertEqual((code, out.splitlines()[:3]), (1, ["A check failed after the files were written: what the site reads is not what this run set.",
                                                             "src/config.ts: the site reads #111111 as SITE.themeColor " + node + "Line 10 already says #b4531a, and this run left it" + self.ELSE,
                                                             "Nothing was written."]), out)
        self.assertEqual(self.snapshot(), before)

    def site_object(self):
        """The whole SITE object as the site's own Node reads it from src/config.ts."""
        program = "const { pathToFileURL } = await import('node:url'); const m = await import(pathToFileURL(process.argv[1]).href); console.log(JSON.stringify(m.SITE));"
        r = subprocess.run([shutil.which("node"), "--input-type=module", "-e", program, self.p("src/config.ts")], capture_output=True, text=True, encoding="utf-8", cwd=self.site, timeout=120)
        return json.loads(r.stdout)

    def test_a_key_that_stands_only_inside_something_is_not_lost_whichever_way_the_advice_is_read_and_each_sentence_on_the_way_leads_on(self):
        # (round 8) INVARIANT: no sequence of doing what the tool says ends with her value inside the block written over
        # AND a sentence that does not say what to do next. Three things were short of that. A key in quotes inside
        # `pwa: {` (and a value with no comma there) was named as the line to write over. The two-way sentence, read
        # the first way where the only key stands inside something, writes her value over, and the read-back then said
        # "something else in the file decides the value", though nothing does. Now: no refusal names such a line, and
        # the read-back says the block has no key of its own, shows the line, and says to put her line back.
        self.need_read_back()
        config = T.starter_file("src/config.ts")
        own = "  themeColor: '#000000',               // matches the brand primary + manifest\n"
        sentence = "src/config.ts: the site reads nothing as SITE.themeColor (this tool asked the site's own Node). The file already says #b4531a, and this run left it" + self.NO_OWN
        shapes = (   # (what it is, the object inside the block, her line of the key in it, what the refusal says that line begins with)
            ("the key in quotes", "  pwa: {\n    'themeColor': '#00ff00',\n    'theme-colour-dark': '#003300',\n  },\n", "    'themeColor': '#00ff00',", "'themeColor':"),
            ("the key in double quotes", '  pwa: {\n    "themeColor": "#00ff00",\n  },\n', '    "themeColor": "#00ff00",', '"themeColor":'),
            ("the key as the starter writes it", "  pwa: {\n    themeColor: '#00ff00',\n    display: 'standalone',\n  },\n", "    themeColor: '#00ff00',", "themeColor:"),
            ("the colour wanted as the object's last entry, with no comma", "  pwa: {\n    display: 'standalone',\n    themeColor: '#b4531a'\n  },\n", "    themeColor: '#b4531a'", "themeColor:"),
            ("the key in quotes, two levels down", "  app: {\n    pwa: {\n      'themeColor': '#00ff00',\n    },\n  },\n", "      'themeColor': '#00ff00',", "'themeColor':"),
        )
        for label, inside, hers, begins in shapes:
            text = config.replace(own, inside)
            for way in ("in place of the line inside the object, taken for the block's own", "as the first line under the opening line"):
                with self.subTest(label=label, way=way):
                    self.fresh()
                    self.put("src/config.ts", text)
                    before = self.snapshot()
                    (dry_code, dry), (code, out) = self.both_runs()
                    self.assertEqual((dry_code, code, self.snapshot()), (2, 2, before), out)
                    said = refusal_in(out)
                    self.assertIn("the one line of the block that begins with `%s` (line %d) stands below a line that is not one whole entry on one line (line 10: `%s`), so it may belong to something inside the block."
                                  % (begins, text.split("\n").index(hers) + 1, inside.split("\n")[0].strip()), said)
                    self.assertEqual(advice(said), "Set the value by hand: write that one line in place of the block's own `themeColor` line, or as the first line under the opening line (line 5) where the block has none of its own")
                    self.assertNotIn("in its place", said, "no advice names her line as the one to write over")
                    if way.startswith("as the first line"):
                        self.put("src/config.ts", text.replace("export const SITE = {\n", "export const SITE = {\n" + shown_line(said) + "\n"))
                    else:   # her line is written over; the next run ends at the read-back, whose sentence is then done to the character
                        self.put("src/config.ts", text.replace(hers, shown_line(said)))
                        before = self.snapshot()
                        code, out = self.intake("--json")
                        data = json.loads(out)
                        self.assertEqual((code, data["status"], data["report"][1:3]), (1, "read-back-failed", [sentence, "Everything it had written was put back."]), out)
                        self.assertEqual(self.snapshot(), before)
                        self.put("src/config.ts", follow_read_back(self.read("src/config.ts"), data["report"][1], put_back=(shown_line(said), hers)))
                    self.assertEqual(self.read("src/config.ts"), text.replace("export const SITE = {\n", "export const SITE = {\nthemeColor: '#b4531a',\n"), "the line under the opening line, and her object as she wrote it")
                    code, out = self.intake("--json")
                    self.assertEqual((code, json.loads(out)["status"], json.loads(out)["read_back"]), (0, "done", self.READ_OK), out)
                    self.assertEqual((self.site_object()["themeColor"], json.dumps(self.site_object()).count('"themeColor"')), ("#b4531a", 2), "the site reads the block's own, and hers is still inside its object")
        # A line that holds more than the entry: "Write that one line in its place", done to the character, took `region` out
        # of the site without a word, and the run passed. The advice keeps what stands after the entry.
        for label, line in (("another entry after it on the line", "  themeColor: '#000000', region: 'eu',"), ("the key in quotes", "  'themeColor': '#000000', region: 'eu',"),
                            ("a name in place of the value", "  themeColor: BRAND, region: 'eu',")):
            with self.subTest(label=label):
                self.fresh()
                text = "const BRAND = '#000000';\n" + config.replace(own, line + "\n")
                self.put("src/config.ts", text)
                self.assertEqual(self.site_object()["region"], "eu")
                before = self.snapshot()
                (dry_code, dry), (code, out) = self.both_runs()
                self.assertEqual((dry_code, code, self.snapshot()), (2, 2, before), out)
                self.assertEqual(advice(refusal_in(out)), "Write that one line in place of the entry, and keep what stands after the entry on line 11 (`region: 'eu',`) on a line of its own below it")
                self.put("src/config.ts", self.follow("src/config.ts", text, out))
                self.assertEqual(self.read("src/config.ts"), text.replace(line, "themeColor: '#b4531a',\nregion: 'eu',"))
                code, out = self.intake("--json")
                self.assertEqual((code, json.loads(out)["status"], json.loads(out)["read_back"]), (0, "done", self.READ_OK), out)
                self.assertEqual((self.site_object()["themeColor"], self.site_object()["region"]), ("#b4531a", "eu"), "what stood after the entry is still read by the site")

    @POSIX
    def test_where_node_or_python_cannot_say_what_the_site_reads_the_run_goes_on_and_says_so_in_one_note_for_the_file(self):
        self.need_read_back()
        config, generator = T.starter_file("src/config.ts"), T.starter_file("scripts/generate_og_cards.py")
        no_theme = " The theme colour is written in src/config.ts, and this tool could not check that the site reads it from there: see the note about it."
        of_config = "this tool could not check that the site reads `themeColor` from line %d of src/config.ts, where it is set: "
        of_cards = "this tool could not check that Python reads the share cards' colours from lines %s of scripts/generate_og_cards.py, where they are set: "

        def run(files, limit=None):
            self.fresh()
            for rel, text in files.items():
                self.put(rel, text)
            was = _install.READ_BACK_SECONDS
            _install.READ_BACK_SECONDS = limit or was
            try:
                (dry_code, dry), (code, out) = self.both_runs("--json")
            finally:
                _install.READ_BACK_SECONDS = was
            data = json.loads(out)
            self.assertEqual((dry_code, code, data["status"], data["tests"]), (0, 0, "done", "passed"), out)
            self.assertEqual([n for n in json.loads(dry)["notes"] if "could not check" in n], [], "the dry run asks nobody, and says so in its own line")
            return data, [n for n in data["notes"] if "could not check" in n], [l for l in data["report"] if l.startswith("Colours: ")][0]

        # no Node on a run about colours alone: the colours go in, the cards wait (they are made through Node), and one note says what was not checked
        real = shutil.which
        shutil.which = lambda name, *a, **k: None if name == "node" else real(name, *a, **k)
        try:
            data, notes, colours = run({})
        finally:
            shutil.which = real
        self.assertEqual(data["read_back"], {"src/config.ts": {"status": "not-checked", "why": "Node is not installed here, or is not on the path"}, "scripts/generate_og_cards.py": {"status": "ok"}})
        self.assertEqual(notes, [of_config % 10 + "Node is not installed here, or is not on the path"])
        self.assertIn("Note: " + notes[0], data["report"])
        self.assertTrue(colours.endswith("and in the manifest. The share cards do not have it: see below." + no_theme), colours)
        self.assertIn("themeColor: '#b4531a',", self.read("src/config.ts"), "the value is written all the same")
        # a Node that reads no TypeScript, with the flag or without: asked twice, the second time with the flag, then the note
        asked = self.old_node("unknown")
        data, notes, colours = run({})
        self.assertEqual(T.read(asked).split(), ["plain", "flag"])
        self.assertEqual(data["read_back"]["src/config.ts"], {"status": "not-checked", "why": "the Node on this computer (v20.11.0) does not read a TypeScript file"})
        self.assertEqual(notes, [of_config % 10 + "the Node on this computer (v20.11.0) does not read a TypeScript file"])
        self.assertIn("and in the manifest, and in the share cards." + no_theme, colours)
        # a Node that reads TypeScript only with the flag (22.12, the oldest the starter allows): asked again with it, and the answer counts
        asked = self.old_node("reads")
        data, notes, colours = run({})
        self.assertEqual((T.read(asked).split(), data["read_back"], notes), (["plain", "flag"], self.READ_OK, []))
        self.assertIn("in the theme colour and the manifest, and in the share cards.", colours)
        # a Node that knows the flag and still cannot load the file: the reason is the second asking's own, not "reads no TypeScript"
        # (and the site's folder is written as `.` in it, in whichever of its two spellings it comes)
        asked = self.old_node('{"code":"ERR_MODULE_NOT_FOUND","why":"Cannot find module %s/src/nav imported from %s/src/config.ts","node":"v22.12.0"}' % (os.path.realpath(self.site), self.site))
        data, notes, colours = run({})
        self.assertEqual((T.read(asked).split(), notes), (["plain", "flag"], [of_config % 10 + "Node could not load the file (Cannot find module ./src/nav imported from ./src/config.ts)"]))
        # (round 7) a Node that takes the flag, and a config that ends the program with status 9 itself: said as that. Status 9 alone
        # was taken for Node's word on an option it does not know, and the note said this Node reads no TypeScript.
        asked = self.old_node("ends with 9")
        data, notes, colours = run({})
        self.assertEqual((T.read(asked).split(), notes), (["plain", "flag"], [of_config % 10 + "Node ended without answering (its exit status was 9: no settings for this branch)"]))
        os.environ["PATH"] = self.path   # the real Node again
        # (round 7) Node runs the file's `exit` listeners when the asking script ends the process. One that takes long holds the
        # process until the time limit: the answer had arrived by then, and was thrown away with it. It counts.
        data, notes, colours = run({"src/config.ts": "process.on('exit', () => { while (Date.now() > 0) { } });\n" + config}, limit=12)
        self.assertEqual((data["read_back"], notes), (self.READ_OK, []))
        self.assertIn("in the theme colour and the manifest, and in the share cards.", colours)
        # a file that imports what only the site's build knows; one Node does not come back from
        data, notes, colours = run({"src/config.ts": "import more from 'a-package-nobody-installed';\n" + config})
        self.assertEqual(data["read_back"]["src/config.ts"]["status"], "not-checked")
        self.assertTrue(notes[0].startswith(of_config % 11 + "Node could not load the file (Cannot find package 'a-package-nobody-installed'"), notes)
        self.assertEqual(len(notes), 1)
        # an import without its ending, which the build takes and Node does not: the reason names the two files from the site's folder,
        # so that a long path to the site is not what the reason's 200 characters are spent on
        data, notes, colours = run({"src/config.ts": "import more from './navigation-for-the-whole-site';\n" + config})
        self.assertEqual(len(notes), 1)
        self.assertRegex(notes[0], re.escape(of_config % 11) + r"Node could not load the file \(Cannot find module '\./src/navigation-for-the-whole-site' imported from \./src/config\.ts\)$")
        self.assertNotIn(os.path.basename(self.tmp.name), notes[0], "nothing of the path to the site is in the reason")
        data, notes, colours = run({"src/config.ts": config + "while (Date.now() > 0) { }\n"}, limit=2)
        self.assertEqual(notes, [of_config % 10 + "Node took more than 2 seconds over the file and was stopped"])
        # (round 7) Node names a file as a `file://` address, with a blank or a letter outside ASCII written as %XX: that spelling
        # of the site's folder is written `.` too, so that the reason is not cut in the middle of a long path
        self.site = T.make_starter_site(os.path.join(self.tmp.name, "My B\u00e4ckerei (new) & more", "a very long folder name for the site " * 4, "site"), with_modules=self.modules)
        data, notes, colours = run({"src/config.ts": "import pack from '../package.json';\n" + config})
        self.assertEqual(len(notes), 1)
        self.assertRegex(notes[0], re.escape(of_config % 11) + r'Node could not load the file \(Module "\./package\.json" needs an import attribute of "?type: json"?\)$')
        self.site = os.path.join(self.tmp.name, "site")
        # the generator: Pillow not there (the file's own top says so and ends), and a top that fails
        data, notes, colours = run({"scripts/generate_og_cards.py": generator.replace("from __future__ import annotations\nimport sys\n", "from __future__ import annotations\nimport sys\nsys.modules['PIL'] = None\n", 1)})
        self.assertEqual(data["read_back"], {"src/config.ts": {"status": "ok"}, "scripts/generate_og_cards.py": {"status": "not-checked", "why": _install.PILLOW_MISSING}})
        self.assertEqual(notes, [of_cards % "53, 54, 55, 56, 57 and 58" + _install.PILLOW_MISSING])
        self.assertIn("in the theme colour and the manifest. The share cards do not have it: see below.", colours)
        data, notes, colours = run({"scripts/generate_og_cards.py": generator + "\nraise RuntimeError('no fonts on this computer')\n"})
        self.assertEqual(notes, [of_cards % "52, 53, 54, 55, 56 and 57" + "Python could not load the file (RuntimeError: no fonts on this computer)"])
        # a top that ends the program: the file was loaded, and the note says what happened, not that it could not be loaded
        data, notes, colours = run({"scripts/generate_og_cards.py": generator.replace("# Home + fallback card", "if not sys.argv[1:]:\n    sys.exit(2)\n\n# Home + fallback card", 1)})
        self.assertEqual(notes, [of_cards % "52, 53, 54, 55, 56 and 57" + "the file ended with status 2 while it was loaded"])
        # both files at once: one note each
        real = shutil.which
        shutil.which = lambda name, *a, **k: None if name in ("node", "python3", "py", "python") else real(name, *a, **k)
        try:
            data, notes, colours = run({})
        finally:
            shutil.which = real
        self.assertEqual(notes, [of_config % 10 + "Node is not installed here, or is not on the path",
                                 of_cards % "52, 53, 54, 55, 56 and 57" + "no Python was found on the path (python3, py or python)"])

    @POSIX
    def test_a_node_is_said_to_read_no_typescript_only_where_node_itself_said_it_does_not_know_the_flag(self):
        # (round 9) INVARIANT: the tool says that this Node does not know the flag only when Node said so. Status 9 and the
        # flag's name anywhere in the error output were taken for that: a config that ended the program with status 9 and
        # named the flag in a message of its own was reported as a Node that reads no TypeScript. What counts now is Node's
        # own sentence, a line of its own: the program as it was started, `: bad option: `, the flag.
        self.need_read_back()
        flag, config = "--experimental-strip-types", T.starter_file("src/config.ts")
        no_typescript = "the Node on this computer (v20.11.0) does not read a TypeScript file"
        of_config = "this tool could not check that the site reads `themeColor` from line %d of src/config.ts, where it is set: "
        # the sentence as the Node here says it of an option it does not know, with the status it ends with
        node = shutil.which("node")
        real = subprocess.run([node, "--no-such-option-of-node", "-e", "0"], capture_output=True, text=True)
        self.assertEqual((real.returncode, real.stdout, real.stderr), (9, "", "%s: bad option: --no-such-option-of-node\n" % node))
        said_by_node = (["node: bad option: " + flag], ["%s: bad option: %s" % (node, flag)], ["/opt/node 20/bin/node: bad option: " + flag],
                        ["D:\\Program Files\\nodejs\\node.exe: bad option: %s\r" % flag], ["a line of the wrapper that starts Node", "node: bad option: " + flag, ""])
        said_by_the_file = (["this site is not built with " + flag], [flag], ["the settings name a bad option: %s, which this branch does not take" % flag],
                            ["node: bad option: %s is what a Node before 22.6 says" % flag], ["node: bad option: %s-and-more" % flag], ["node: bad option: --no" + flag[1:]],
                            ["node: bad option:", flag], ["bad option: " + flag], ["node: bad option: %s " % flag], [], [""])
        for lines in said_by_node + said_by_the_file:
            with self.subTest(lines=lines):
                asked = self.old_node(lines)
                read, why = _install._reads_config(self.site)
                first = ([l.strip() for l in lines if l.strip()] or [""])[0]
                self.assertEqual((read, why, T.read(asked).split()), (None, no_typescript if lines in said_by_node else "Node ended without answering (its exit status was 9%s)" % (
                    ": " + first.rstrip(".") if first else ""), ["plain", "flag"]))

        def notes(files, node):   # a run about colours, as the command line makes it: what it notes about the read-back
            self.fresh()
            for rel, text in files.items():
                self.put(rel, text)
            asked = self.old_node(node)
            code, out = self.intake("--json")
            data = json.loads(out)
            self.assertEqual((code, data["status"], data["tests"], T.read(asked).split()), (0, "done", "passed", ["plain", "flag"]), out)
            return [n for n in data["notes"] if "could not check" in n]
        self.assertEqual(notes({}, ["%s: bad option: %s" % (node, flag)]), [of_config % 10 + no_typescript])
        self.assertEqual(notes({}, ["this site is not built with " + flag]), [of_config % 10 + "Node ended without answering (its exit status was 9: this site is not built with %s)" % flag])
        # the real Node, which takes the flag, and a config that names the flag in a message of its own and sets status 9: one that
        # ends the program there, and one that never gets to its end (Node then ends with the status that was set)
        for ending in ("process.exit();", "await new Promise(() => {});"):
            with self.subTest(ending=ending):
                ends = "console.error('this site is not built with %s');\nprocess.exitCode = 9;\n%s\n" % (flag, ending)
                direct = subprocess.run([node, flag, "--input-type=module", "-e", ends], capture_output=True, text=True)
                self.assertEqual((direct.returncode, flag in direct.stderr, "bad option" in direct.stderr), (9, True, False), direct.stderr)
                said = notes({"src/config.ts": ends + config}, "reads")
                self.assertEqual(len(said), 1, said)
                self.assertTrue(said[0].startswith(of_config % 13 + "Node ended without answering (its exit status was 9: "), said)
                self.assertNotIn("does not read a TypeScript file", said[0])
                if direct.stderr.strip().splitlines() == ["this site is not built with " + flag]:   # (a Node that warns about the flag says that first)
                    self.assertEqual(said, [of_config % 13 + "Node ended without answering (its exit status was 9: this site is not built with %s)" % flag])

    def test_only_the_sites_whole_folder_is_written_as_a_dot_in_a_reason_in_whichever_way_a_program_spells_it(self):
        # (round 7) the folder's name was replaced wherever its letters stood: a site in a folder called `site` or `app` scarred
        # other words of the reason. And Node's own spelling of a folder, a `file://` address with %XX in it, was not replaced.
        said = _install._first_line
        for folder in ("/srv/site", "/srv/app", "/srv/My B\u00e4ckerei (new) & 100%/site"):
            with self.subTest(folder=folder):
                address = "file://" + "".join(c if c.isascii() and (c.isalnum() or c in "/()&") else "".join("%%%02X" % b for b in c.encode("utf-8")) for c in folder)
                self.assertEqual(said("Cannot find module '%s/src/nav' imported from %s/src/config.ts" % (folder, folder), folder), "Cannot find module './src/nav' imported from ./src/config.ts")
                self.assertEqual(said('Module "%s/package.json" needs an import attribute of "type: json"' % address, folder), 'Module "./package.json" needs an import attribute of "type: json"')
                self.assertEqual(said("%s/src/config.ts:3 and %s too" % (address, folder), folder), "./src/config.ts:3 and . too")
                for other in ("No module named 'sitemaps' for the application, opposite", "%s-old/src/config.ts" % folder, "%ss/src/config.ts" % folder, "/backup%s/src/config.ts" % folder,
                              "%s.bak/x" % folder, "file:///elsewhere%s" % address[len("file://"):]):
                    self.assertEqual(said(other, folder), other, "a word that only holds the folder's letters, or a longer path, is left as it is")
        self.assertEqual(said("site: No module named 'sitemaps' in site/x", "site"), "site: No module named 'sitemaps' in site/x", "a folder given by its name alone is looked for by its whole path")
        self.assertEqual(said("x" * 300 + ".", "/srv/site"), "x" * 200)
        self.assertEqual((said("\n\n  first.  \nsecond", "/srv/site"), said("", "/srv/site"), said("", "/srv/site", "")), ("first", "it did not say why", ""))

    @POSIX
    def test_the_answer_is_the_line_that_carries_this_runs_mark_whatever_else_the_file_prints_and_however_it_ends(self):
        # _install.read_back is what the install calls once the files are written. Before round 6 the answer was the
        # LAST line the program printed, and the program ended when the file's own code let it: a line printed later
        # made the note "could not load the file (it did not say why)", a timer left running cost the whole 60
        # seconds and the answer, a line of the answer's shape printed by the file itself was taken for the answer,
        # and the generator's top saw this tool's arguments as its own.
        self.need_read_back()
        config, generator = T.starter_file("src/config.ts"), T.starter_file("scripts/generate_og_cards.py")
        home, ok = "# Home + fallback card", {"status": "ok"}
        forged = "console.log('\\n' + JSON.stringify({ read: { themeColor: '#000000', logo: '/images/logo.png' } }));\n"

        def top(code):
            return generator.replace(home, code + "\n\n" + home, 1)

        def unasked(why):
            return {"status": "not-checked", "why": why}
        cases = (
            ("src/config.ts", "a line printed later, from a timer", config + "setTimeout(() => console.log('still here'), 20);\n", ok),
            ("src/config.ts", "a timer that never ends", config + "setInterval(() => {}, 1000);\n", ok),
            ("src/config.ts", "lines of its own before the answer, one of them of the answer's shape", "console.log('loading');\n" + forged + config, ok),
            ("src/config.ts", "a forged answer at the top and again when the process ends, over a value the site reads otherwise",
             forged + "process.on('exit', () => { " + forged.strip() + " });\n" + config + "// @ts-ignore\nSITE.themeColor = '#111111';\n",
             {"status": "differs", "values": [{"name": "themeColor", "reads": "#111111", "wanted": "#000000"}]}),
            ("src/config.ts", "a file that ends the program itself", "process.exit(0);\n" + config, unasked("Node ended without answering (its exit status was 0)")),
            ("src/config.ts", "a file that ends the program with a status and a word", "console.error('no settings for this branch');\nprocess.exit(3);\n" + config,
             unasked("Node ended without answering (its exit status was 3: no settings for this branch)")),
            ("scripts/generate_og_cards.py", "a top that reads the program's arguments", top("import argparse\nargparse.ArgumentParser().parse_args()\nassert sys.argv == [__file__], sys.argv"), ok),
            ("scripts/generate_og_cards.py", "something printed when Python ends, and standard output pointed elsewhere", top("import atexit, os\natexit.register(print, 'bye')\nsys.stdout = open(os.devnull, 'w')"), ok),
            ("scripts/generate_og_cards.py", "a thread left running, which Python would wait for when it ends", top("import threading, time\nthreading.Thread(target=time.sleep, args=(600,)).start()"), ok),
            ("scripts/generate_og_cards.py", "the colour as a list of its three numbers", generator.replace("BG_TOP = (30, 33, 64)", "BG_TOP = [30, 33, 64]", 1), ok),
            ("scripts/generate_og_cards.py", "the colour as a list of three texts", generator.replace("BG_TOP = (30, 33, 64)", "BG_TOP = ['30', '33', '64']", 1),
             {"status": "differs", "values": [{"name": "BG_TOP", "reads": "['30', '33', '64']", "wanted": "#1e2140"}]}),
            ("scripts/generate_og_cards.py", "a top that ends the program with a status", top("sys.exit(2)"), unasked("the file ended with status 2 while it was loaded")),
            ("scripts/generate_og_cards.py", "a top that ends the program with a word", top("sys.exit('no fonts on this computer')"), unasked("the file ended with status 1 while it was loaded (no fonts on this computer)")),
            ("scripts/generate_og_cards.py", "a top that ends the program and says nothing", top("sys.exit()"), unasked("the file ended with status 0 while it was loaded")),
            ("scripts/generate_og_cards.py", "a top that ends the process at once", top("import os\nos._exit(4)"), unasked("Python ended without answering (its exit status was 4)")),
        )
        wanted = {"src/config.ts": {"themeColor": "#000000"}, "scripts/generate_og_cards.py": {"BG_TOP": "#1e2140"}}
        for rel, label, text, said in cases:
            with self.subTest(rel=rel, label=label):
                self.put(rel, text)
                began = time.time()
                self.assertEqual(_install.read_back(self.site, {rel: wanted[rel]}), {rel: said})
                self.assertLess(time.time() - began, _install.READ_BACK_SECONDS / 2, "the answer was there at once, and was waited for until the limit")
                self.put(rel, T.starter_file(rel))
        # (round 7) An answer that has arrived counts, also where the program then does not end before the time limit (Node runs a
        # file's `exit` listeners; the install's own test of that is in the test above). Python's side, with a stand-in that
        # answers and stays; and one that stays without an answer is still said to have taken too long.
        folder = tempfile.mkdtemp(dir=self.tmp.name)
        was, path = _install.READ_BACK_SECONDS, os.environ["PATH"]
        _install.READ_BACK_SECONDS, os.environ["PATH"] = 3, folder + os.pathsep + path
        try:
            for label, answers, said in (("an answer, and then it stays", "printf '\\n%s{\"read\": {\"BG_TOP\": [30, 33, 64]}}\\n' \"$4\"; ", ok),
                                         ("no answer, and it stays", "", unasked("Python took more than 3 seconds over the file and was stopped"))):
                with self.subTest(label=label):
                    with open(os.path.join(folder, "python3"), "w", encoding="utf-8") as f:
                        f.write("#!/bin/sh\n%sexec sleep 600\n" % answers)   # (its arguments: -c, the asking script, the file, the mark, the names)
                    os.chmod(os.path.join(folder, "python3"), 0o755)
                    self.assertEqual(_install.read_back(self.site, {"scripts/generate_og_cards.py": wanted["scripts/generate_og_cards.py"]}), {"scripts/generate_og_cards.py": said})
        finally:
            _install.READ_BACK_SECONDS, os.environ["PATH"] = was, path

    def test_what_the_reading_of_the_stylesheet_notes_and_stops_for_nothing_is_in_the_installs_report_too(self):
        # the stylesheet's reader hands out notes beside its problems (a stylesheet brought in with @import, which
        # nobody read and which can set the colours too). The palette check printed them; the install said nothing.
        sheet = '@import url("./fonts.css");\n@import "more.css";\n' + T.starter_file("src/styles/global.css")
        said = _palette.read_css(sheet).notes
        self.assertTrue(len(said) == 2 and said[0].startswith("line 1 of the stylesheet brings in another stylesheet (`@import url(\"./fonts.css\");`), which this check does not read."), said)
        self.fresh()
        self.put("src/styles/global.css", sheet)
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code), (0, 0), out)
        for report in (json.loads(dry), json.loads(out)):
            self.assertEqual(report["notes"][:2], said, "first among the notes, in the dry run as in the real one")
            for note in said:
                self.assertIn("Note: " + note, report["report"])
        self.assertTrue(self.read("src/styles/global.css").startswith('@import url("./fonts.css");\n@import "more.css";\n'), "and the lines themselves are left as they are")
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT)
        # in words, and in a run that ends another way: a question, a refusal, red tests
        self.fresh()
        self.put("src/styles/global.css", sheet)
        for label, extra, command, code_wanted in (("a dry run", ("--dry-run",), GREEN, 0), ("a refusal", ("--with-logo",), GREEN, 2), ("red tests", (), RED, 1), ("done", (), GREEN, 0)):
            with self.subTest(label=label):
                code, out = self.intake(*extra, command=command)
                self.assertEqual(code, code_wanted, out)
                for note in said:
                    self.assertEqual(out.splitlines().count("Note: " + note), 1, out)
        self.fresh()   # a stylesheet that brings nothing in has no such note
        self.assertEqual([n for n in json.loads(self.intake("--json")[1])["notes"] if "brings in" in n], [])

    def test_a_manifest_whose_lines_end_with_a_carriage_return_alone_is_refused_by_the_lines_an_editor_shows_and_keeps_its_line_ends(self):
        # the lines of a refusal were counted two ways (the name's by one rule, its value's end by another): one way
        # now, the one an editor shows, whatever ends the lines
        rel = "public/manifest.webmanifest"
        hers = T.starter_file(rel).replace('"theme_color": "#000000"', '"theme_color":\n    0').replace("\n", "\r")
        self.fresh()
        self.put(rel, hers)
        (dry_code, dry), (code, out) = self.both_runs()
        self.assertEqual((dry_code, code), (2, 2), out)
        self.assertEqual(refusal_in(dry), refusal_in(out))
        self.assertIn('line 9 is written another way: `"theme_color":`, and its value runs on to line 10. Write that one line in place of lines 9 to 10, which it replaces together, then run this again', out)
        self.put(rel, follow_manifest(self.bytes(rel).decode("utf-8"), refusal_in(out)))
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        now = self.bytes(rel).decode("utf-8")
        self.assertEqual((now.count("\n"), now.count("\r"), json.loads(now)["theme_color"], json.loads(now)["background_color"]), (0, hers.count("\r") - 1, "#b4531a", "#fff8ee"))

    def test_a_manifest_that_never_was_valid_json_is_refused_as_that_and_not_as_something_the_edit_did(self):
        self.brand_md()
        self.put("public/manifest.webmanifest", self.read("public/manifest.webmanifest").replace('  ]\n}', '  ],\n}'))
        before = self.snapshot()
        for code, out in self.both_runs():
            self.assertEqual(code, 2, out)
            self.assertIn("public/manifest.webmanifest is not valid JSON (", out)
            self.assertIn("so this tool does not edit it", out)
            self.assertNotIn("after the colours were set", out)
            self.assertEqual(self.snapshot(), before)

    def test_every_value_that_changes_is_listed_old_and_new_also_numbers_that_were_no_colour(self):
        self.brand_md()
        self.put("scripts/generate_og_cards.py", self.read("scripts/generate_og_cards.py").replace("BG_TOP = (30, 33, 64)", "BG_TOP = (300, 33, 64)"))
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code), (0, 0), out)
        for report in (dry, out):
            self.assertIn("scripts/generate_og_cards.py, BG_TOP: (300, 33, 64) becomes #2a1f17", json.loads(report)["changes"])
        self.assertIn("\nBG_TOP = (42, 31, 23) ", self.read("scripts/generate_og_cards.py"))

    def test_a_refusal_over_one_file_does_not_take_the_changes_already_worked_out_from_the_report(self):
        # the stylesheet's changes, and those of the files that could be read, are said in words and in JSON
        self.brand_md()
        config = self.read("src/config.ts")
        self.put("src/config.ts", config.replace("  locale: 'en',\n", "  locale: 'en',\n  themeColor: '#111111',\n"))
        before = self.snapshot()
        for extra in (("--dry-run",), ()):
            with self.subTest(extra=extra):
                code, out = self.intake(*extra)
                self.assertEqual(code, 2, out)
                self.assertIn("2 lines of the block begin with `themeColor:` (lines 10 and 11)", out)
                for line in ("Colours that would have changed in src/styles/global.css:", "  Primary: #000000 becomes #b4531a", "Colours that would have changed in the site's other files:",
                             "  public/manifest.webmanifest, theme_color: #000000 becomes #b4531a", "  scripts/generate_og_cards.py, BG_TOP: #1e2140 becomes #2a1f17"):
                    self.assertIn(line, out.splitlines())
                data = json.loads(self.intake("--json", *extra)[1])
                self.assertEqual((data["status"], data["code"]), ("refused", "config-layout"))
                self.assertIn("Primary: #000000 becomes #b4531a", data["changes"])
                self.assertIn("Surface (cards), dark theme: #161836 becomes #2a1f17", data["changes"])
                self.assertIn("public/manifest.webmanifest, background_color: #ffffff becomes #fff8ee", data["changes"])
                self.assertIn("scripts/generate_og_cards.py, FOOTER_COL: #9696aa becomes #c4ae98", data["changes"])
                self.assertEqual([c for c in data["changes"] if c.startswith("src/config.ts")], [], "the file that was refused has none to list")
                self.assertEqual(self.snapshot(), before)

    def test_a_primary_that_a_dark_block_sets_again_is_refused_before_anything_is_written_naming_the_block(self):
        css = T.starter_file("src/styles/global.css")
        dark, media = ':root[data-theme="dark"] {\n', "  :root:not([data-theme]) {\n"
        for name, text, said in (
                ("the dark block", css.replace(dark, dark + "  --brand: #123456;\n", 1), '--brand (the Primary) inside the `:root[data-theme="dark"]` block'),
                ("the block for visitors without JavaScript", css.replace(media, media + "    --brand: #123456;\n", 1), "--brand (the Primary) inside the dark block inside the `@media (prefers-color-scheme: dark)` block"),
                ("a value no colour can be read from", css.replace(dark, dark + "  --brand: var(--accent);\n", 1), "--brand (the Primary) inside the `:root[data-theme=\"dark\"]` block"),
                ("a rule further down that names the dark theme among others", css + '\n.print, :root[data-theme="dark"] {\n  --brand: #123456;\n}\n', "written in another way than the starter writes it")):
            with self.subTest(name=name):
                self.assertNotEqual(text, css)
                self.fresh()
                self.put("src/styles/global.css", text)
                before = self.snapshot()
                for code, out in self.both_runs():
                    self.assertEqual(code, 2, out)
                    self.assertIn(said, out)
                    self.assertIn("Nothing was written", out)
                    self.assertEqual(self.snapshot(), before)
        self.fresh()   # a comment that only mentions it is no reason to stop
        self.put("src/styles/global.css", css.replace(dark, dark + "  /* --brand: #123456; */\n", 1))
        self.assertEqual(self.intake()[0], 0)

    def test_a_file_saved_with_a_byte_order_mark_is_read_past_the_mark_and_keeps_it(self):
        mark = chr(0xFEFF)
        self.brand_md()
        self.assertEqual(self.intake()[0], 0)
        plain = {rel: self.read(rel) for rel in _site.REQUIRED_FILES}
        for rel in _site.REQUIRED_FILES:
            with self.subTest(rel=rel):
                self.fresh()
                self.put(rel, mark + T.starter_file(rel))
                (dry_code, dry), (code, out) = self.both_runs("--json")
                self.assertEqual((dry_code, code), (0, 0), out)
                self.assertIn(rel, json.loads(dry)["written"])
                self.assertEqual(self.read(rel), mark + plain[rel], "the same edit as without the mark, and the mark is still there")

    # --- a palette that is there and is not used is never taken for no palette -----------------

    def test_a_palette_the_reading_names_but_does_not_use_is_said_with_the_reason_one_thing_to_a_line(self):
        cases = (("its tables under other headings", OTHER_HEADINGS, True),
                 ("a header row that does not call the column Hex", BAKERY_BRAND_MD.replace("| Token | Hex |", "| Token | Value |"), True),
                 ("one of its tables under another heading", BAKERY_BRAND_MD.replace("### Dark theme", "### Night"), False),
                 ("a value among words", BAKERY_BRAND_MD.replace("| Muted | `#c4ae98` |", "| Muted | about `#c4ae98` |"), False))
        for name, text, no_row in cases:
            with self.subTest(name=name):
                self.brand_md(text)
                read = _palette.parse_tables(text)
                problems = [m for _theme, _row, _code, m in read.problems]
                self.assertTrue(problems)
                self.assertEqual(not read.rows_found, no_row)
                before = self.snapshot()
                for flags, first in ((("--with-colours",), None), ((), "There is nothing to do: no complete palette was found in BRAND.md, and no logo file was given.")):
                    for code, out in self.both_runs(*flags):
                        self.assertEqual(code, 2, out)
                        lines = out.splitlines()
                        for said in problems:
                            self.assertIn(said, lines, "each thing the reading could not use, on a line of its own")
                        self.assertEqual(_palette.FORM in lines, no_row, "the form it reads is given when it found no row at all")
                        self.assertIn(first or lines[0], lines)
                        for untrue in ("has no filled-in colour rows", "no BRAND.md was found"):
                            self.assertNotIn(untrue, out)
                        self.assertIn("Nothing was written.", lines)
                        self.assertEqual(self.snapshot(), before)
                data = json.loads(self.intake("--with-colours", "--json")[1])
                self.assertEqual((data["status"], data["code"]), ("refused", "palette-incomplete"))
                self.assertEqual(data["message"].splitlines()[1:1 + len(problems)], problems)
        first = {name: self.intake_with(text)[1].splitlines()[0] for name, text, _no_row in cases}
        self.assertEqual(first["its tables under other headings"], "No colour could be read from the palette in BRAND.md.")
        self.assertEqual(first["one of its tables under another heading"], "The palette in BRAND.md is not complete. Rows without a colour: the dark theme: Heading, Body (ink), Muted, "
                         "Accent, Link, Hairline, Background, Soft background, Surface (cards).")
        self.brand_md(T.read(T.BRAND_TEMPLATE))   # the template, not filled in: no colour and nothing wrong with it
        code, out = self.intake("--with-colours")
        self.assertEqual(code, 2, out)
        self.assertIn("There are no colours to apply: BRAND.md has no filled-in colour rows.", out)

    def intake_with(self, text):
        self.brand_md(text)
        return self.intake("--with-colours")

    # --- the Primary and the rest of the palette, said in every report --------------------------

    def test_a_run_that_ends_without_the_colours_still_lists_the_ones_it_would_have_changed(self):
        self.brand_md()
        lines = ("Colours that would have changed in src/styles/global.css:", "  Primary: #000000 becomes #b4531a",
                 "Colours that would have changed in the site's other files:", "  src/config.ts, themeColor: #000000 becomes #b4531a")
        code, out = self.intake(command=RED)                              # red tests: all of it was put back
        self.assertEqual(code, 1, out)
        for line in lines:
            self.assertIn(line, out.splitlines())
        self.assertIn("Primary: #000000 becomes #b4531a", json.loads(self.intake("--json", command=RED)[1])["changes"])
        self.put("public/manifest.webmanifest", self.read("public/manifest.webmanifest").replace('  "lang": "en",', NESTED_SHORTCUT, 1))
        for code, out in self.both_runs():                                # a refusal after the colours were worked out
            self.assertEqual(code, 2, out)
            for line in lines:
                self.assertIn(line, out.splitlines())
        data = json.loads(self.intake("--json")[1])
        self.assertEqual(data["status"], "refused")
        self.assertIn("scripts/generate_og_cards.py, BG_TOP: #1e2140 becomes #2a1f17", data["changes"])

    def test_every_colour_the_palette_changes_outside_the_stylesheet_is_listed_with_its_file(self):
        self.brand_md()
        other = ["src/config.ts, themeColor: #000000 becomes #b4531a", "public/manifest.webmanifest, theme_color: #000000 becomes #b4531a",
                 "public/manifest.webmanifest, background_color: #ffffff becomes #fff8ee", "scripts/generate_og_cards.py, BG_TOP: #1e2140 becomes #2a1f17",
                 "scripts/generate_og_cards.py, BG_BOT: #0a0b1e becomes #1a120d", "scripts/generate_og_cards.py, TITLE_COL: #ffffff becomes #fbeedd",
                 "scripts/generate_og_cards.py, SUB_COL: #8aa0ff becomes #e2874a", "scripts/generate_og_cards.py, ACCENT: #8aa0ff becomes #e2874a",
                 "scripts/generate_og_cards.py, FOOTER_COL: #9696aa becomes #c4ae98"]
        (_c, dry), (_c2, out) = self.both_runs("--json")
        for report in (dry, out):
            changes = json.loads(report)["changes"]
            self.assertEqual(changes[-len(other):], other)
            self.assertEqual(changes[0], "Primary: #000000 becomes #b4531a", "the stylesheet's own come first, as they did")
        self.assertEqual(json.loads(self.intake("--json")[1])["changes"], [], "and once they are in, nothing changes")
        self.fresh()
        code, out = self.intake("--dry-run")
        at = out.splitlines().index("Colours that would change in the site's other files:")
        self.assertEqual(out.splitlines()[at + 1:at + 1 + len(other)], ["  " + line for line in other])
        # cards that keep their colours (the text would not read on them) have no colour of theirs listed
        self.brand_md(BAKERY_BRAND_MD.partition("### Dark theme\n")[0] + "### Dark theme\n" + table([(l, GREY_DARK[k]) for k, l in LABELS]))
        changes = json.loads(self.intake("--json", "--dry-run")[1])["changes"]
        self.assertEqual([c for c in changes if c.startswith("scripts/")], [])
        self.assertIn("src/config.ts, themeColor: #000000 becomes #b4531a", changes)

    # --- a file that is there is never taken for one that is not --------------------------------

    @POSIX
    def test_a_file_or_a_folder_that_is_there_and_closed_to_this_account_stops_the_run_with_its_path_and_the_reason(self):
        self.not_as_root()
        for name, rel, make, named in (("a folder of the site", "src", None, "src/styles/global.css"),
                                       ("the palette", "BRAND.md", None, "BRAND.md"),
                                       ("the folder the palette is kept in", "docs", "docs/BRAND.md", "docs/BRAND.md"),
                                       ("the installed logo", "public/favicon.svg", "public/favicon.svg", "public/favicon.svg"),
                                       ("a file it would write", "public/manifest.webmanifest", None, "public/manifest.webmanifest")):
            with self.subTest(name=name):
                self.fresh()
                if make == "docs/BRAND.md":
                    os.makedirs(self.p("docs"))
                    os.replace(self.p("BRAND.md"), self.p("docs/BRAND.md"))
                elif make:
                    self.put(make, _install.MARK.encode("utf-8") + _svg.clean_svg(T.real_svg()).text.encode("utf-8"))
                before = self.snapshot()
                was = self.closed(rel)
                try:
                    runs = self.both_runs(brand=False)
                finally:
                    os.chmod(self.p(rel), was)
                for code, out in runs:
                    self.assertEqual(code, 2, out)
                    self.assertIn("%s could not be read or written (Permission denied)" % self.p(named), out)
                    self.assertIn("Nothing was written.", out)
                    for untrue in ("does not look like a site", "nothing to do", "no complete palette"):
                        self.assertNotIn(untrue, out)
                self.assertEqual(self.snapshot(), before)

    # --- the share cards' folder is put back the way every other file is ---------------------------

    @POSIX
    def test_something_in_the_share_cards_folder_that_cannot_be_read_is_refused_by_name_before_anything_is_written(self):
        # left out of what is kept, it would be gone once the folder was put back, under "everything was put back"
        self.not_as_root()
        self.brand_md()
        os.makedirs(self.p("public/images/og/drafts"))
        self.put("public/images/og/drafts/note.txt", b"a note")
        before = self.snapshot()
        for rel, said in (("public/images/og/drafts", "public/images/og/drafts cannot be listed (Permission denied)"),
                          ("public/images/og/default.jpg", "public/images/og/default.jpg cannot be read (Permission denied)"),
                          ("public/images/og/drafts/note.txt", "public/images/og/drafts/note.txt cannot be read (Permission denied)")):
            with self.subTest(rel=rel):
                was = self.closed(rel)
                try:
                    runs = self.both_runs() + [self.intake(command=RED)]
                finally:
                    os.chmod(self.p(rel), was)
                for code, out in runs:
                    self.assertEqual(code, 2, out)
                    self.assertIn(said, out)
                    self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)

    def test_a_share_cards_folder_that_is_a_link_or_lies_behind_one_is_refused_before_anything_is_written(self):
        for rel in ("public/images/og", "public/images"):
            with self.subTest(rel=rel):
                self.fresh()
                elsewhere = os.path.join(self.tmp.name, "kept-elsewhere-" + os.path.basename(rel))
                os.rename(self.p(rel), elsewhere)
                os.symlink(elsewhere, self.p(rel))
                kept, links = tree(elsewhere), self.links()
                modes = {base: os.stat(base).st_mode for base, _dirs, _files in os.walk(elsewhere)}
                for code, out in self.both_runs() + [self.intake(command=RED)]:
                    self.assertEqual(code, 2, out)
                    self.assertIn("public/images/og is a link, and nothing is written through a link. Put" if rel == "public/images/og" else
                                  "public/images is a link, and nothing is written through a link (public/images/og is below it). Put", out)   # the link itself is named
                    self.assertIn("Nothing was written", out)
                    self.assertEqual((tree(elsewhere), self.links()), (kept, links))
                    self.assertEqual({base: os.stat(base).st_mode for base, _dirs, _files in os.walk(elsewhere)}, modes, "no mode was changed through the link")

    def test_on_a_site_that_had_no_images_folder_none_is_left_behind_when_the_run_is_taken_back(self):
        T.require_pillow(self)
        self.brand_md()
        shutil.rmtree(self.p("public/images"))
        before = self.snapshot()
        code, out = self.intake("--json", command=RED)
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["cards"]), (1, "tests-failed", "restored"), out)
        self.assertEqual(self.snapshot(), before, "the folder the generator made is gone again, and the one above it")
        # and when the generator itself stops after it made the folder
        gen = self.read("scripts/generate_og_cards.py")
        self.put("scripts/generate_og_cards.py", gen.replace("def main():\n", "def main():\n    OUT.mkdir(parents=True, exist_ok=True)\n    (OUT / 'default.jpg').write_bytes(b'half way')\n"
                                                             "    raise SystemExit('simulated: a later card failed')\n", 1))
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        self.assertIn("the generator failed (simulated: a later card failed)", out)
        self.assertFalse(self.exists("public/images"))

    @POSIX
    def test_whatever_the_tests_did_to_the_share_cards_folder_it_is_put_back_in_place_file_by_file(self):
        T.require_pillow(self)
        self.not_as_root()
        self.brand_md()
        os.makedirs(self.p("public/images/og/drafts/empty"))
        self.put("public/images/og/drafts/note.txt", b"a note")
        self.put("public/images/og/about.jpg", b"the about card")
        before, folder = self.snapshot(), os.stat(self.p("public/images/og")).st_ino
        once = os.path.join(self.tmp.name, "wrecked-once")   # the tests are run a second time, and must not undo the putting back
        wreck = "; ".join(("if [ -e '%s' ]; then exit 1; fi" % once, "touch '%s'" % once, "cd public/images/og", "rm about.jpg", "mkdir about.jpg",
                           "echo x > extra.jpg", "mkdir -p new/deeper", "echo y > new/deeper/card.jpg", "chmod 000 new/deeper", "rm -r drafts", "echo z > drafts",
                           "ln -s ../logo.png linked.png", "chmod 555 . ..", "exit 1"))
        for rel in ("public/images", "public/images/og"):
            self.addCleanup(os.chmod, self.p(rel), 0o755)
        code, out = self.intake("--json", command=wreck)
        os.chmod(self.p("public/images"), 0o755)   # the folder above is not the run's to change, and it did not need it
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["cards"], data.get("not_restored")), (1, "tests-failed", "restored", None), out)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(os.stat(self.p("public/images/og")).st_ino, folder, "the folder itself was never deleted")
        self.assertEqual(stat.S_IMODE(os.stat(self.p("public/images/og")).st_mode), 0o755)

    def test_a_card_that_cannot_be_put_back_is_named_by_its_own_name_and_the_cards_around_it_are_put_back(self):
        T.require_pillow(self)
        self.brand_md()
        for name in ("about.jpg", "zebra.jpg"):
            self.put("public/images/og/" + name, b"a card of her own")
        before = self.snapshot()
        real = _site.Journal._put

        def refusing(journal, path, data, mode=0o644):
            if path.endswith(os.path.join("og", "default.jpg")):
                raise PermissionError(13, "Permission denied", path)
            return real(journal, path, data, mode)
        _site.Journal._put = refusing
        try:
            code, out = self.intake("--json", command="echo x > public/images/og/about.jpg; echo x > public/images/og/zebra.jpg; exit 1")
        finally:
            _site.Journal._put = real
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["cards"]), (1, "rollback-incomplete", "not-restored"), out)
        self.assertEqual(data["not_restored"], [{"file": "public/images/og/default.jpg", "why": "Permission denied"}])
        self.assertIn("  public/images/og/default.jpg (Permission denied)", data["report"])
        after = self.snapshot()
        card = os.path.join("public", "images", "og", "default.jpg")
        self.assertNotEqual(after[card], before[card])
        after[card] = before[card]
        self.assertEqual(after, before, "the card before it and the card after it are back, and every other file")

    def test_a_generator_that_fails_leaves_cards_that_cannot_be_put_back_named_and_nothing_else_of_the_run(self):
        T.require_pillow(self)   # without it the generator stops before it writes anything
        self.brand_md()
        gen = self.read("scripts/generate_og_cards.py")
        self.put("scripts/generate_og_cards.py", gen.replace("def main():\n", "def main():\n    (OUT / 'default.jpg').write_bytes(b'half way')\n    raise SystemExit('simulated: a later card failed')\n", 1))
        before = self.snapshot()
        real = _site.Journal._put

        def refusing(journal, path, data, mode=0o644):
            if path.endswith(os.path.join("og", "default.jpg")):
                raise PermissionError(13, "Permission denied", path)
            return real(journal, path, data, mode)
        _site.Journal._put = refusing
        try:
            code, out = self.intake("--json")
        finally:
            _site.Journal._put = real
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["code"]), (2, "rollback-incomplete", "cards-not-restored"), out)
        self.assertEqual([l["file"] for l in data["not_restored"]], ["public/images/og/default.jpg"])
        after = self.snapshot()
        after[os.path.join("public", "images", "og", "default.jpg")] = before[os.path.join("public", "images", "og", "default.jpg")]
        self.assertEqual(after, before)

    # --- what is said ----------------------------------------------------------------------------

    def test_keeping_the_colours_with_no_logo_says_that_and_does_not_say_no_palette_was_found(self):
        self.brand_md()
        code, out = self.intake("--keep-colours")
        self.assertEqual(code, 2, out)
        self.assertIn("There is nothing to do: --keep-colours leaves the palette in BRAND.md out, and no logo file was given.", out)
        self.assertNotIn("no complete palette was found", out)
        self.brand_md(BAKERY_BRAND_MD.replace("| Soft background | `#fef5e8` |\n", ""))   # where that is the reason, it is still the reason given
        for extra in ((), ("--keep-colours",)):
            self.assertIn("There is nothing to do: no complete palette was found in BRAND.md, and no logo file was given.", self.intake(*extra)[1])
        os.remove(self.p("BRAND.md"))
        self.assertIn("There is nothing to do: no complete palette was found, and no logo file was given.", self.intake(brand=False)[1])

    def test_the_share_cards_are_named_in_the_dry_run_and_under_written_also_when_no_file_is_written(self):
        T.require_pillow(self)
        self.brand_md()
        code, out = self.intake("--dry-run")
        self.assertIn("  the share cards under public/images/og would be made again", out.splitlines())
        code, out = self.intake()
        self.assertEqual(out.splitlines()[out.splitlines().index("Written:") + 5], "  the share cards under public/images/og, made again")
        code, out = self.intake("--dry-run")   # everything is in already: no file would be written, and the cards would still be made again
        at = out.splitlines().index("  nothing: every file is already as this run would write it")
        self.assertEqual(out.splitlines()[at + 1], "  the share cards under public/images/og would be made again")
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        at = out.splitlines().index("Written:")
        self.assertEqual(out.splitlines()[at + 1:at + 3], ["  nothing: every file was already as this run writes it", "  the share cards under public/images/og, made again"])

    def test_red_tests_whose_output_names_no_check_in_a_form_this_tool_reads_are_said_to_be_that_with_their_last_lines(self):
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake("--json", command="echo 'FAIL src/a.test.js'; echo '  expected 1, got 2' >&2; exit 1")
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["failing"], data["output_tail"]), (1, "tests-failed", [], ["FAIL src/a.test.js", "expected 1, got 2"]))
        said = [l for l in data["report"] if "does not name the failing checks in a form this tool reads" in l]
        self.assertEqual(len(said), 1, data["report"])
        self.assertIn("Its last lines: FAIL src/a.test.js; expected 1, got 2.", said[0])
        for untrue in ("printed nothing", "The failing check"):
            self.assertEqual([l for l in data["report"] if untrue in l], [])
        self.assertEqual(self.snapshot(), before)

    def test_what_the_tests_print_is_read_as_utf8_whatever_this_computers_own_encoding_is(self):
        self.brand_md()
        real, seen = _install._run, []

        def watching(command, cwd, timeout, **how):
            if how.get("shell"):
                seen.append(how.get("encoding", "utf-8"))   # what is read is bytes from a file, decoded as UTF-8 unless a caller asks otherwise
            return real(command, cwd, timeout, **how)
        _install._run = watching
        try:
            code, out = self.intake("--json", command=RED)
            raw_code, raw = self.intake("--json", command="printf 'caf\\351 \\377\\376 failed\\n'; exit 1")
        finally:
            _install._run = real
        self.assertEqual(seen, ["utf-8"] * 4, "the tests with the install and with it taken out again, both times")
        self.assertEqual(json.loads(out)["failing"], ["tests/a11y.spec.ts:8:5 \u203a a11y \u2014 / [dark]", "tests/seo.spec.ts:20:3 \u203a theme colour"])
        self.assertEqual((raw_code, json.loads(raw)["output_tail"]), (1, ["caf\ufffd \ufffd\ufffd failed"]), "bytes that are no UTF-8 are shown as that, and stop nothing")

    @POSIX
    def test_what_a_test_command_left_running_is_stopped_once_the_command_has_ended(self):
        # a preview server it started and did not stop would hold the site's port for the second run and after
        self.brand_md()
        pids = os.path.join(self.tmp.name, "started")
        self.addCleanup(self.stop_leftovers, pids)
        for ending, code_wanted, runs in (("exit 1", 1, 2), ("exit 0", 0, 1)):
            with self.subTest(ending=ending):
                if os.path.exists(pids):
                    os.remove(pids)
                code, out = self.intake(command="(sleep 300 > /dev/null 2>&1 & echo $! >> '%s'); %s" % (pids, ending))
                self.assertEqual(code, code_wanted, out)
                started = [int(pid) for pid in T.read(pids).split()]
                self.assertEqual(len(started), runs)
                for pid in started:
                    self.assertTrue(self.gone(pid), "what the test command started (%d) is still running" % pid)

    def test_a_web_page_is_not_taken_for_a_logo_and_the_refusal_says_what_to_hand_over_instead(self):
        page = (b'<!doctype html><html><body><h1>Logo</h1><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8">'
                b'<rect width="8" height="8" fill="#b4531a"/></svg></body></html>')
        before = self.snapshot()
        for name in ("logo.html", "logo.svg"):   # what a file is, is read from its content
            with self.subTest(name=name):
                path = self.package(name, page)
                for code, out in self.both_runs("--input", path, brand=False):
                    self.assertEqual(code, 2, out)
                    self.assertIn("This looks like a web page", out)
                    self.assertIn("Ask the tool for the SVG file itself", out)
                    self.assertIn("Nothing was written", out)
                    self.assertEqual(self.snapshot(), before)
                data = json.loads(self.intake("--input", path, "--json", brand=False)[1])
                self.assertEqual((data["status"], data["exit"], data["code"], data["written"]), ("refused", 2, "web-page", []))
                self.assertIn(data["message"], data["report"])
        only = os.path.join(self.tmp.name, "only-a-page")   # a folder is looked through for a zip or an SVG, and for nothing else
        os.makedirs(only)
        with open(os.path.join(only, "logo.html"), "wb") as f:
            f.write(page)
        code, out = self.intake("--input", only, brand=False)
        self.assertEqual(code, 2, out)
        self.assertIn("that folder holds no .zip or .svg file", out)
        self.assertEqual(self.snapshot(), before)


class TheIconsWaitForTheImageLibrary(SiteCase):
    """A run about colours on a site whose logo this tool installed, on a computer where sharp does not load."""
    modules = False

    def setUp(self):
        super().setUp()
        self.brand_md()
        self.clean = _svg.clean_svg(T.real_svg(T.REAL_COLOUR)).text.encode("utf-8")
        self.installed = _install.MARK.encode("utf-8") + self.clean

    def test_the_colours_go_in_the_icons_are_left_and_the_report_says_what_to_run_later(self):
        self.put("public/favicon.svg", self.installed)
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code), (0, 0), out)
        self.assertEqual(json.loads(dry)["written"], json.loads(out)["written"])
        self.assertEqual(json.loads(dry)["notes"], json.loads(out)["notes"])
        note = [n for n in json.loads(out)["notes"] if n.startswith("the icons were left as they are")]
        self.assertEqual(len(note), 1, json.loads(out)["notes"])
        for said in ("they could not be drawn again here", "sharp", "That does not hold the colours back", "npm install --include=optional", "--with-logo"):
            self.assertIn(said, note[0])
        self.assertNotIn("is not a file this tool wrote", note[0])
        self.assertEqual([w for w in json.loads(out)["written"] if w.startswith(("public/favicon", "public/icon", "public/apple", "public/images/logo", "brand-handoff"))], [])
        self.assertEqual(self.bytes("public/favicon.svg"), self.installed)
        self.assertFalse(self.exists("public/favicon.ico"))
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT, "the colours are in")

    def test_asked_for_outright_the_icons_cannot_wait_and_the_run_stops_with_what_to_install(self):
        self.put("public/favicon.svg", self.installed)
        before = self.snapshot()
        for code, out in self.both_runs("--with-logo", "--with-colours"):   # (without --with-colours she is asked about the colours first)
            self.assertEqual(code, 2, out)
            self.assertIn("npm install --include=optional", out)
            self.assertIn("Nothing was written", out)
            self.assertEqual(self.snapshot(), before)

    def test_a_clean_favicon_without_this_tools_line_is_hers_and_the_image_library_is_not_even_asked_for(self):
        self.put("public/favicon.svg", self.clean)
        asked = []
        real = _install._render.Renderer.preflight
        _install._render.Renderer.preflight = lambda renderer: asked.append(renderer) or real(renderer)
        try:
            (dry_code, dry), (code, out) = self.both_runs()
        finally:
            _install._render.Renderer.preflight = real
        self.assertEqual((dry_code, code, asked), (0, 0, []), out)
        for report in (dry, out):
            self.assertIn("the icons were left as they are: public/favicon.svg is not a file this tool wrote", report)
            self.assertNotIn("sharp", report)
        self.assertEqual(self.bytes("public/favicon.svg"), self.clean)


class StoppedFromOutside(SiteCase):
    """A stop is a signal: SIGTERM (an assistant's shell tool ends a command), SIGHUP (the terminal is
    closed), SIGINT (Ctrl-C), SIGQUIT (Ctrl-\\). Whenever it comes, and however many of them come together, the run ends in words with exit status 2, the site as it
    was, and nothing of its own left running or lying about."""
    modules = False

    def setUp(self):
        if os.name != "posix":
            self.skipTest("signals as POSIX has them")
        super().setUp()
        self.brand_md()

    AT = "real = %s\ndef stopped_here(*args, **kwargs):\n    os.kill(os.getpid(), signal.%s)\n    return real(*args, **kwargs)\n%s = stopped_here\n"
    STOPPED_JSON = '{"status": "stopped", "exit": 2, "message": "Stopped (Ctrl-C). Nothing was written."}\n'

    def test_a_stop_while_the_run_is_still_planning_ends_in_words_with_nothing_written_and_no_temporary_folder_left(self):
        before = self.snapshot()
        for name in ("SIGTERM", "SIGHUP", "SIGINT", "SIGQUIT"):
            for extra in ((), ("--json",), ("--dry-run",)):
                with self.subTest(signal=name, extra=extra):
                    scratch = tempfile.mkdtemp(dir=self.tmp.name)
                    r = self.drive(self.AT % ("_site.edit_css", name, "_site.edit_css"), *extra, tmpdir=scratch)
                    self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout + r.stderr)
                    said = "\n".join(json.loads(r.stdout)["report"]) if extra == ("--json",) else r.stdout
                    self.assertIn("The run was stopped from outside (%s) before it had finished" % name, said)
                    self.assertIn("Nothing was written.", said)
                    self.assertIn("Colours that would have changed in src/styles/global.css:", said)
                    if extra == ("--json",):
                        data = json.loads(r.stdout)
                        self.assertEqual((data["status"], data["exit"], data["written"], data.get("rolled_back")), ("stopped", 2, [], None))
                    self.assertEqual(os.listdir(scratch), [], "the folder the icons are drawn in is gone again")
                    self.assertEqual(self.snapshot(), before)

    def test_a_stop_at_any_step_of_the_writing_leaves_the_site_as_it_was(self):
        before = self.snapshot()
        moments = (("just before the first file is replaced", "os.replace"), ("just after a folder was looked at", "os.path.isdir"),
                   ("while the share cards are made", "_install.regenerate_cards"), ("while the stylesheet is read back", "_install._palette.read_css"))
        for moment, where in moments:
            with self.subTest(moment=moment):
                patch = ("real_write = _site.Journal.write\ndef write(journal, rel, data):\n    global armed\n    armed = True\n    return real_write(journal, rel, data)\n"
                         "_site.Journal.write = write\narmed = False\nreal = %s\ndef stopped_here(*args, **kwargs):\n    global armed\n    if armed:\n        armed = False\n"
                         "        os.kill(os.getpid(), signal.SIGTERM)\n    return real(*args, **kwargs)\n%s = stopped_here\n" % (where, where))
                r = self.drive(patch)
                self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout + r.stderr)
                self.assertIn("stopped from outside (SIGTERM)", r.stdout)
                self.assertTrue("Everything it had written was put back." in r.stdout or "Nothing was written." in r.stdout, r.stdout)
                self.assertEqual(self.snapshot(), before)

    def test_a_stop_that_comes_once_the_install_stands_does_not_make_the_report_say_that_nothing_was_written(self):
        # the tests have passed and nothing will be put back any more: the report must say what is in the site
        r = self.drive(self.AT % ("_install._changes_lines", "SIGTERM", "_install._changes_lines"))
        self.assertEqual((r.returncode, r.stderr), (0, ""), r.stdout + r.stderr)
        self.assertIn("Done. The site's own tests pass afterwards.", r.stdout)
        self.assertNotIn("stopped from outside", r.stdout)
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT, "and it is in")

    def test_more_signals_while_the_files_are_put_back_and_while_the_report_is_made_change_nothing(self):
        # one stop is enough: a second Ctrl-C, or a shell that sends SIGTERM and then SIGHUP, must neither cut
        # the putting back short nor the report
        before = self.snapshot()
        again = "    for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT):\n        os.kill(os.getpid(), s)\n"
        patch = ("real_rollback = _site.Journal.rollback\ndef rollback(journal):\n" + again + "    return real_rollback(journal)\n_site.Journal.rollback = rollback\n"
                 "real_install = _install.install\ndef install(a, out):\n    result = real_install(a, out)\n" + again + "    return result\n_install.install = install\n")
        for first in ("TERM", "INT"):
            with self.subTest(first=first):
                sleep, running = self.sleeper()
                r = self.drive(patch, command="kill -%s $PPID; %s" % (first, sleep))
                self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout + r.stderr)
                self.assertIn("stopped from outside (SIG%s)" % first, r.stdout)
                self.assertIn("Everything it had written was put back.", r.stdout)
                self.assertEqual(self.snapshot(), before)
                self.assertTrue(self.none_left(running), "what the test command was just starting is still running")
        r = self.drive(patch, command=RED)   # the first signal arrives while red tests are being undone
        self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout + r.stderr)
        self.assertIn("stopped from outside (SIGINT)", r.stdout)
        self.assertIn("Everything it had written was put back.", r.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_a_signal_that_comes_once_the_outcome_is_decided_changes_neither_the_exit_status_nor_one_line_of_the_report(self):
        # the report is printed after `install` has returned. With the signals given back in between, a stop in
        # that moment ended the process (status -15) with the install in and nothing said: 5 runs of 80.
        again = "    for s in (signal.SIGTERM, signal.SIGINT, signal.SIGQUIT, signal.SIGHUP):\n        os.kill(os.getpid(), s)\n"
        patch = ("real_install = _install.install\ndef install(a, out):\n    result = real_install(a, out)\n" + again + "    return result\n_install.install = install\n"
                 "import builtins\nreal_print = builtins.print\ndef printed(*args, **kwargs):\n" + again + "    real_print(*args, **kwargs)\n" + again + "builtins.print = printed\n")
        proposed = BAKERY_BRAND_MD.replace("| Primary | `#b4531a` |", "| Primary | `#b4531a` (proposed) |")
        for name, extra, command, md, code_wanted, first, last in (
                ("done", (), GREEN, BAKERY_BRAND_MD, 0, "Done. The site's own tests pass afterwards.", "Share cards: "),
                ("a dry run", ("--dry-run",), GREEN, BAKERY_BRAND_MD, 0, "Dry run: nothing was written.", "  scripts/generate_og_cards.py, FOOTER_COL: #9696aa becomes #c4ae98"),
                ("a question", (), GREEN, proposed, 3, "I need your decision before I go on. Nothing was written.", "- These colours are still proposals"),
                ("a refusal", ("--with-colours", "--keep-colours"), GREEN, BAKERY_BRAND_MD, 2, "--with-colours and --keep-colours ask for opposite things", "Nothing was written."),
                ("red tests", (), RED, BAKERY_BRAND_MD, 1, "The site's own tests failed after the install, so everything was put back", "  scripts/generate_og_cards.py, FOOTER_COL: #9696aa becomes #c4ae98")):
            with self.subTest(name=name):
                for rel in ("src/styles/global.css",) + _install.OTHER_FILES:
                    self.put(rel, T.starter_file(rel))
                self.brand_md(md)
                before = self.snapshot()
                r = self.drive(patch, *extra, command=command)
                self.assertEqual((r.returncode, r.stderr), (code_wanted, ""), r.stdout + r.stderr)
                lines = r.stdout.splitlines()
                self.assertTrue(lines[0].startswith(first), r.stdout)
                self.assertTrue(lines[-1].startswith(last), r.stdout)
                self.assertNotIn("stopped from outside", r.stdout)
                if name == "done":
                    self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT, "and it is in")
                else:
                    self.assertEqual(self.snapshot(), before)
                data = json.loads(self.drive(patch, *extra, "--json", command=command).stdout)   # the JSON is whole too
                self.assertEqual(data["exit"], code_wanted)

    def test_a_stop_in_the_instant_the_temporary_folder_is_made_does_not_leave_it_behind(self):
        # between the making of the folder and the line that remembers its name, nothing knew of it: 1 stop in 170 left it
        before = self.snapshot()
        made = ("real = _install.tempfile.mkdtemp\ndef stopped_here(*args, **kwargs):\n    path = real(*args, **kwargs)\n    os.kill(os.getpid(), signal.%s)\n    return path\n"
                "_install.tempfile.mkdtemp = stopped_here\n")
        for name in ("SIGTERM", "SIGINT", "SIGHUP", "SIGQUIT"):
            with self.subTest(signal=name):
                scratch = tempfile.mkdtemp(dir=self.tmp.name)
                r = self.drive(made % name, tmpdir=scratch)
                self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout + r.stderr)
                self.assertIn("The run was stopped from outside (%s) before it had finished" % name, r.stdout)
                self.assertIn("Nothing was written.", r.stdout)
                self.assertEqual(os.listdir(scratch), [], "the folder it had just made is gone again")
                self.assertEqual(self.snapshot(), before)

    def test_a_signal_the_run_was_started_to_ignore_stays_ignored(self):
        # `nohup` starts a command with SIGHUP ignored, a shell starts a background job with SIGINT ignored:
        # the run must not begin to listen to what it was told to ignore
        for name in ("HUP", "INT"):
            with self.subTest(signal=name):
                self.put("src/styles/global.css", T.starter_file("src/styles/global.css"))
                r = self.drive("", ignored=("SIG" + name,), command="kill -%s $PPID; sleep 1" % name)
                self.assertEqual((r.returncode, r.stderr), (0, ""), r.stdout + r.stderr)
                self.assertIn("Done.", r.stdout)
                self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT)
        before = self.snapshot()
        sleep, running = self.sleeper()
        r = self.drive("", ignored=("SIGHUP",), command="kill -TERM $PPID; " + sleep)   # and the others still stop it
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.none_left(running))


    TIMES = 2     # how often each order of signals is tried (the measurement with 20 of each is in the review's records)
    LIMIT = 60    # seconds a stopped run gets to end, on however loaded a machine; an unloaded one takes half a second

    def test_two_or_more_different_stop_signals_with_no_gap_between_them_end_the_run_as_one_stop_does(self):
        # SIGTERM and SIGINT in the same instant (a tool that ends a command while Ctrl-C is pressed, a shell that
        # sends two): the handler of the first set the others to "ignore", which Python refuses to do while a
        # second signal is on its way, and the run ended with a traceback, 10 times of 10. Every ordered pair of
        # the watched signals, the three older ones in every order, and all four, each TIMES times, as real
        # processes stopped from outside while the site's tests run, a few at a time.
        import concurrent.futures
        import itertools
        names = [n for n in _install.SIGNALS if hasattr(signal, n)]
        orders = list(itertools.permutations(names, 2)) + list(itertools.permutations(("SIGTERM", "SIGHUP", "SIGINT"), 3)) + [tuple(names), tuple(reversed(names))]
        self.assertEqual(len(orders), 12 + 6 + 2)
        trials = [order for order in orders for _n in range(self.TIMES)]
        workers = 4

        def fresh(n):
            site = os.path.join(self.tmp.name, "site-%d" % n)
            shutil.rmtree(site, ignore_errors=True)
            T.make_starter_site(site, with_modules=False)
            shutil.copy(self.p("BRAND.md"), os.path.join(site, "BRAND.md"))
            return site
        tag = "300.%06d" % (int.from_bytes(os.urandom(3), "big") % 1000000)

        def running():
            listing = subprocess.run(["ps", "-Ao", "pid=,command="], capture_output=True, text=True).stdout
            return [int(line.split()[0]) for line in listing.splitlines() if line.strip().endswith("sleep " + tag)]

        def tidy():
            for pid in running():
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
        self.addCleanup(tidy)
        # the share cards are not made in these runs (that is seconds of Node and Python each time): the stop comes
        # while the tests run, which is after them either way
        program = ("import os, signal, sys\nfor name in %r:\n    signal.signal(getattr(signal, name), signal.SIG_DFL)\nsys.path.insert(0, %r)\nimport brand_intake, _install\n"
                   "_install.regenerate_cards = lambda site: (False, 'not made in this test')\nsys.exit(brand_intake.main(sys.argv[1:]))\n" % (tuple(names), T.SCRIPTS))

        def work(n):
            site, wrong, stuck = fresh(n), [], 0
            before = tree(site)
            for i, order in enumerate(trials[n::workers]):
                marker = os.path.join(self.tmp.name, "tests-run-%d-%d" % (n, i))
                p = subprocess.Popen([sys.executable, "-c", program, "install", "--site", site, "--json", "--test-command", "touch '%s'; exec sleep %s" % (marker, tag)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
                end = time.time() + self.LIMIT
                while not os.path.exists(marker) and p.poll() is None and time.time() < end:
                    time.sleep(0.002)
                for name in order:   # one after the other, as fast as this process can send them
                    os.kill(p.pid, getattr(signal, name))
                try:
                    out, err = p.communicate(timeout=self.LIMIT)
                except subprocess.TimeoutExpired:
                    # it is ended here, and the next run of this worker gets a site of its own again: one run that
                    # hangs is one failure, not one for every run after it
                    p.kill()
                    p.communicate()
                    stuck += 1
                    wrong.append((order, "still running %d seconds after the signals" % self.LIMIT))
                    site = fresh(n)
                    continue
                try:
                    data = json.loads(out)
                except ValueError:
                    data = {}
                whole = data.get("status") == "stopped" and data.get("exit") == 2 and data.get("report", [""])[0].startswith("The run was stopped from outside (SIG") \
                    and "Everything it had written was put back." in data.get("report", [])
                if p.returncode != 2 or err or not whole or tree(site) != before:
                    wrong.append((order, p.returncode, err[-600:], out[:300]))
            return wrong, stuck
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            found = list(pool.map(work, range(workers)))
        wrong, stuck = [w for some, _n in found for w in some], sum(n for _some, n in found)
        self.assertEqual(wrong[:3], [], "%d of %d runs did not end as a stop does (exit status 2, a whole report, nothing on the error output, the site as it was); %d of them were "
                         "still running %d seconds after the signals and were ended by this test" % (len(wrong), len(trials), stuck, self.LIMIT))
        self.assertTrue(self.none_left(running), "something the stopped runs had started is still running")

    # What Popen keeps to ask about its process: a lock, taken with `if lock.acquire(False): try: ...`. This stands in
    # for it in one command's Popen (the third value says which) and sends the stop (the second) in the very instant
    # the lock is taken for the n-th time (the first) and not yet guarded.
    LOCK = ("import subprocess\nif hasattr(os, 'waitid'):\n    del os.waitid   # so that every Python asks Popen, as the Python of a Mac before 3.13 does\n"
            "class Lock(object):\n    def __init__(self, real):\n        self.real, self.taken = real, 0\n"
            "    def acquire(self, *args, **kwargs):\n        got = self.real.acquire(*args, **kwargs)\n        self.taken += bool(got)\n        if got and self.taken == %d:\n"
            "            for s in (%s):\n                os.kill(os.getpid(), s)\n        return got\n"
            "    def release(self):\n        return self.real.release()\n    def locked(self):\n        return self.real.locked()\n"
            "    def __enter__(self):\n        return self.acquire()\n    def __exit__(self, *args):\n        self.release()\n"
            "class Watched(subprocess.Popen):\n    def __init__(self, *args, **kwargs):\n        super().__init__(*args, **kwargs)\n        if %s:\n"
            "            self._waitpid_lock = Lock(self._waitpid_lock)\nsubprocess.Popen = Watched\n")

    def test_a_stop_in_the_instant_popen_is_asked_whether_the_command_has_ended_does_not_leave_the_run_waiting_for_ever(self):
        # On a Python without os.waitid (macOS before 3.13: the Python every Mac comes with) the run waited for
        # its command with Popen.wait(timeout). A stop raised between Popen taking its lock and guarding it left
        # the lock taken, and the wait after the stopping never came back: the run hung with its command dead
        # and every file of the install still in the site. Seen in about 1 stop of 100 when several suites ran
        # at once; here the stop is put into that very instant.
        with subprocess.Popen(["true"]) as probe:
            self.assertTrue(hasattr(probe, "_waitpid_lock"), "this Python's Popen has the lock the test stands in for")
        before = self.snapshot()
        for label, signals in (("one stop", "signal.SIGTERM,"), ("two different ones at once", "signal.SIGINT, signal.SIGTERM")):
            with self.subTest(label=label):
                sleep, running = self.sleeper()
                try:
                    r = self.drive(self.LOCK % (3, signals, "kwargs.get('shell')"), "--json", command=sleep, timeout=60)
                except subprocess.TimeoutExpired:
                    self.fail("the run was still going a minute after the stop: it waits for a lock that the stop left taken")
                data = json.loads(r.stdout)
                self.assertEqual((r.returncode, r.stderr, data["status"]), (2, "", "stopped"), r.stdout + r.stderr)
                self.assertIn("Everything it had written was put back.", data["report"])
                self.assertEqual(self.snapshot(), before)
                self.assertTrue(self.none_left(running), "the test command is still running")

    def test_a_command_that_ps_does_not_show_is_still_ended_and_never_waited_for_without_an_end(self):
        # the stopping goes by what `ps` shows; the command itself is this run's own child, and is ended whatever
        # `ps` shows or does not show, so that the wait for it always has an end
        before = self.snapshot()
        sleep, running = self.sleeper()
        try:
            r = self.drive("_proc._listing = lambda: {1: (0, 1, 'long ago')}\n", "--json", command="kill -TERM $PPID; exec " + sleep, timeout=60)
        except subprocess.TimeoutExpired:
            self.fail("the run was still going a minute after the stop: it waits for a command it never told to end")
        self.assertEqual((r.returncode, r.stderr, json.loads(r.stdout)["status"]), (2, "", "stopped"), r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.none_left(running), "the test command is still running")

    def test_a_list_of_processes_that_ps_did_not_finish_is_not_taken_for_the_list(self):
        # a second Ctrl-C reaches the `ps` that the stopping runs, too: what it had printed by then is a part of
        # the list, and "nothing of the command is left" must not be read from a part
        import types
        real = _proc.subprocess.run
        line = "%d     1 %d Ss   Mon Oct 12 10:00:00 2026\n" % (os.getpid(), os.getpid())
        listed = {os.getpid(): (1, os.getpid(), "Mon Oct 12 10:00:00 2026")}
        asked = []

        def answering(*codes):
            left = list(codes)

            def run(*args, **kwargs):
                asked.append(kwargs)
                return types.SimpleNamespace(returncode=left.pop(0) if len(left) > 1 else left[0], stdout=line, stderr="")
            return run
        try:
            for codes, whole, times in (((0,), True, 1), ((-2,), False, _proc.LOOKS), ((1,), False, _proc.LOOKS), ((-2, 0), True, 2), ((-2, -2, 0), True, 3)):
                del asked[:]
                _proc.subprocess.run = answering(*codes)
                self.assertEqual(_proc._listing(), listed if whole else None)
                self.assertEqual(len(asked), times, "one that did not end well is asked again, %d times in all at most" % _proc.LOOKS)
                # round 5: in a session of its own, so that a Ctrl-C to this program's whole group does not end it
                self.assertTrue(all(kwargs.get("start_new_session") for kwargs in asked))

            def none(*args, **kwargs):
                asked.append(kwargs)
                raise FileNotFoundError(2, "No such file or directory", "ps")
            del asked[:]
            _proc.subprocess.run = none
            self.assertEqual((_proc._listing(), len(asked)), (None, 1), "where there is no `ps`, asking again would not help")
        finally:
            _proc.subprocess.run = real
        self.assertIn(os.getpid(), _proc._listing() or {os.getpid(): None}, "and the real one lists this very process")

    def test_where_the_list_of_processes_cannot_be_read_the_report_says_what_was_stopped_and_what_it_cannot_know(self):
        before = self.snapshot()
        sleep, running = self.sleeper()
        r = self.drive("_proc._listing = lambda: None\n", "--json", command="kill -TERM $PPID; exec " + sleep, timeout=60)
        data = json.loads(r.stdout)
        self.assertEqual((r.returncode, r.stderr, data["status"]), (2, "", "stopped"), r.stdout + r.stderr)
        self.assertEqual(data["report"][0], "The run was stopped from outside (SIGTERM) before it had finished. This tool could not read the list of running processes: it stopped the command it had started, "
                         "with that command's own group, and cannot say whether anything else the command had started is still running (a preview server, say). Look for one before the next run.")
        self.assertIn("Everything it had written was put back.", data["report"])
        self.assertTrue(self.none_left(running), "the command itself, which is in its own group, is stopped all the same")
        self.assertEqual(self.snapshot(), before)

    def test_a_signal_while_the_folder_the_icons_are_drawn_in_is_cleared_away_neither_leaves_it_behind_nor_changes_the_outcome(self):
        # after red tests, a question or a late refusal the signals were still listened to while that folder was
        # removed: a stop in that moment left it in the temporary folder (1 timed stop of 60) and turned the
        # outcome into "stopped". The run has its outcome by then: it is said, and the folder goes.
        late = ("real = _install.shutil.rmtree\ndef stopped_here(path, *args, **kwargs):\n    if 'brand-kit-' in str(path):\n        for s in (signal.SIGTERM, signal.SIGQUIT, signal.SIGINT):\n"
                "            os.kill(os.getpid(), s)\n    return real(path, *args, **kwargs)\n_install.shutil.rmtree = stopped_here\n")
        manifest = self.read("public/manifest.webmanifest")
        elsewhere = os.path.join(self.tmp.name, "manifest-elsewhere")
        with open(elsewhere, "w", encoding="utf-8") as f:
            f.write(manifest)

        def linked():
            os.remove(self.p("public/manifest.webmanifest"))
            os.symlink(elsewhere, self.p("public/manifest.webmanifest"))

        def unlinked():
            os.remove(self.p("public/manifest.webmanifest"))
            self.put("public/manifest.webmanifest", manifest)
        for name, extra, command, make, unmake, code_wanted, first in (
                ("red tests", (), RED, None, None, 1, "The site's own tests failed after the install, so everything was put back"),
                ("a refusal that comes late, when every path is looked at", (), GREEN, linked, unlinked, 2, "public/manifest.webmanifest is a link, and nothing is written through a link."),
                ("a dry run", ("--dry-run",), GREEN, None, None, 0, "Dry run: nothing was written."),
                ("done", (), GREEN, None, None, 0, "Done. The site's own tests pass afterwards.")):
            with self.subTest(name=name):
                if make:
                    make()
                before = self.snapshot()
                scratch = tempfile.mkdtemp(dir=self.tmp.name)
                r = self.drive(late, *extra, command=command, tmpdir=scratch)
                self.assertEqual((r.returncode, r.stderr), (code_wanted, ""), r.stdout + r.stderr)
                self.assertTrue(r.stdout.startswith(first), r.stdout)
                self.assertNotIn("stopped from outside", r.stdout)
                self.assertEqual(os.listdir(scratch), [], "the folder the icons are drawn in is gone again")
                if name != "done":
                    self.assertEqual(self.snapshot(), before)
                if unmake:
                    unmake()

    # --- round 5 ---------------------------------------------------------------------------------------

    def test_a_stop_in_the_instant_the_signals_begin_to_be_watched_is_a_stop_with_a_report_and_no_traceback(self):
        # the handlers were set before the part that turns a stop into a report was entered: a signal that came
        # after the first handler was set, and before that part, ended the run with a traceback and exit status 1.
        # Sent here from inside the setting: after the first handler is in, and after the last.
        at = ("real = signal.signal\nseen = []\ndef stopped_here(sig, handler):\n    was = real(sig, handler)\n    if handler is _install._stop:\n        seen.append(sig)\n"
              "        if len(seen) == %d:\n            os.kill(os.getpid(), signal.%s)\n    return was\nsignal.signal = stopped_here\n")
        before = self.snapshot()
        watched = [n for n in _install.SIGNALS if hasattr(signal, n)]
        # (after the first handler only SIGTERM is watched; a Ctrl-C then is Python's own KeyboardInterrupt, and a stop like any other)
        for nth, names in ((1, ("SIGTERM", "SIGINT")), (len(watched), watched)):
            for name in names:
                with self.subTest(handlers_set=nth, signal=name):
                    r = self.drive(at % (nth, name), "--json")
                    self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout + r.stderr)
                    data = json.loads(r.stdout)
                    self.assertEqual((data["status"], data["exit"], data["report"][:2]), ("stopped", 2, ["The run was stopped from outside (%s) before it had finished, and what it had started was stopped with it as far as this tool could find it." % name, "Nothing was written."]))
                    self.assertEqual(self.snapshot(), before)

    def test_a_stop_while_node_is_asked_what_the_site_reads_ends_as_every_other_stop_does(self):
        # the read-back runs Node as every other command is run: a stop ends the wait at once, Node is stopped with
        # it, and what the run had written by then is put back
        why = node_problem(typescript=True)
        if why:
            self.skipTest(why)
        reading = os.path.join(self.tmp.name, "node-is-reading")
        self.put("src/config.ts", "import { writeFileSync } from 'node:fs';\nwriteFileSync(%s, String(process.pid));\n%swhile (Date.now() > 0) { }\n" % (json.dumps(reading), T.starter_file("src/config.ts")))
        before = self.snapshot()
        for name in ("SIGTERM", "SIGINT"):
            with self.subTest(signal=name):
                p = self.begin("--json")
                try:
                    self.assertTrue(self.until(lambda: os.path.exists(reading) and T.read(reading), p), "Node never came to read the file: " + (p.stdout.read() if p.poll() is not None else ""))
                    node = int(T.read(reading))
                    p.send_signal(getattr(signal, name))
                    out, err = p.communicate(timeout=120)
                finally:
                    if p.poll() is None:
                        p.kill()
                data = json.loads(out)
                self.assertEqual((p.returncode, err, data["status"], data["written"]), (2, "", "stopped", []), out + err)
                self.assertEqual(data["report"][:2], ["The run was stopped from outside (%s) before it had finished, and what it had started was stopped with it as far as this tool could find it." % name, "Everything it had written was put back."])
                self.assertTrue(self.gone(node), "the Node that was reading the file is still running")
                self.assertEqual(self.snapshot(), before)
                os.remove(reading)

    def test_a_signal_that_comes_when_the_report_is_out_and_the_process_is_ending_does_not_change_the_exit_status(self):
        # Python puts every signal back to what it does by default while it shuts down. A SIGTERM in that moment
        # ended the process with status -15 after a report that said "done" and "exit": 0 (4 to 8 of 180 runs
        # with the signal swept over the end). The command line now ends the process itself, at once.
        # (1) What Python's shutting down would do is stood in for by something registered to run then: it is not run.
        late = "import atexit\ndef at_the_end():\n    signal.signal(signal.SIGTERM, signal.SIG_DFL)\n    os.kill(os.getpid(), signal.SIGTERM)\natexit.register(at_the_end)\n"
        for label, extra, command, wanted in (("done", (), GREEN, (0, "done")), ("a dry run", ("--dry-run",), GREEN, (0, "dry-run")), ("red tests", (), RED, (1, "tests-failed")),
                                              ("a refusal", ("--with-colours", "--keep-colours"), GREEN, (2, "refused"))):
            with self.subTest(label=label):
                for rel in ("src/styles/global.css",) + _install.OTHER_FILES:
                    self.put(rel, T.starter_file(rel))
                p = self.begin("--json", *extra, patch=late, command=command)
                out, err = p.communicate(timeout=300)
                data = json.loads(out)
                self.assertEqual((p.returncode, data["exit"], data["status"], err), wanted[:1] + wanted + ("",), out + err)
        # (2) The real thing: each watched signal sent the moment the report has arrived, several times over. Whenever
        # it lands, the status is the report's own.
        for rel in ("src/styles/global.css",) + _install.OTHER_FILES:
            self.put(rel, T.starter_file(rel))
        ends = []
        for name in [n for n in _install.SIGNALS if hasattr(signal, n)] * 4:
            p = self.begin("--json", "--dry-run")
            line = p.stdout.readline()
            try:
                p.send_signal(getattr(signal, name))
            except ProcessLookupError:
                pass
            p.communicate(timeout=120)
            ends.append((name, p.returncode, json.loads(line)["exit"], json.loads(line)["status"]))
        self.assertEqual([e for e in ends if e[1:] != (0, 0, "dry-run")], [], "a run whose report said one status ended with another")

    def test_whatever_is_wrong_with_standard_output_the_command_ends_with_the_runs_own_status_and_says_nothing_on_the_error_output(self):
        # one guarded print for every line the command prints. Standard output closed (`>&-`: Python then has no
        # sys.stdout at all) ended an install that stood with AttributeError and status 1; opened for reading
        # only (`1</dev/null`), with OSError and 120; and the one line of an early Ctrl-C was printed outside the
        # guard altogether.
        script = os.path.abspath(os.path.join(T.SCRIPTS, "brand_intake.py"))
        early = ("import argparse, os, runpy, signal, sys\nsignal.signal(signal.SIGINT, signal.default_int_handler)\nreal = argparse.ArgumentParser.parse_args\n"
                 "def stopped_here(self, *args, **kwargs):\n    os.kill(os.getpid(), signal.SIGINT)\n    return real(self, *args, **kwargs)\n"
                 "argparse.ArgumentParser.parse_args = stopped_here\nsys.argv = [%r] + sys.argv[1:]\nrunpy.run_path(%r, run_name='__main__')\n" % (script, script))
        install = ["install", "--site", self.site, "--test-command", GREEN]
        runs = (("an install that stands", [sys.executable, script] + install, 0), ("a refusal", [sys.executable, script] + install + ["--with-colours", "--keep-colours"], 2),
                ("a dry run in JSON", [sys.executable, script] + install + ["--dry-run", "--json"], 0), ("the palette check", [sys.executable, script, "palette", self.p("BRAND.md")], 0),
                ("a Ctrl-C before the install began", [sys.executable, "-c", early] + install, 2))
        for how, redirect in (("closed", ">&-"), ("open for reading only", "1</dev/null"), ("closed, and the error output too", ">&- 2>&-")):
            for label, argv, code_wanted in runs:
                with self.subTest(standard_output=how, run=label):
                    r = subprocess.run(["/bin/sh", "-c", 'exec "$@" ' + redirect, "sh"] + argv, capture_output=True, timeout=300)
                    self.assertEqual((r.returncode, r.stdout, r.stderr), (code_wanted, b"", b""))
        for label, argv, code_wanted in runs:   # a pipe whose reader has gone
            with self.subTest(standard_output="a pipe nobody reads", run=label):
                p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p.stdout.close()
                err = p.stderr.read()
                p.stderr.close()
                self.assertEqual((p.wait(timeout=300), err), (code_wanted, b""))
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT, "and the install is in")

    def test_ctrl_c_while_the_tools_own_modules_are_loaded_ends_in_the_same_one_line_and_no_traceback(self):
        # the tool's own imports stood outside the part that catches a Ctrl-C: one in the first tenth of a second
        # of a run (a third of the runs it was swept over) ended in a traceback
        script = os.path.abspath(os.path.join(T.SCRIPTS, "brand_intake.py"))
        program = ("import builtins, os, runpy, signal, sys\nsignal.signal(signal.SIGINT, signal.default_int_handler)\nreal = builtins.__import__\nsent = []\n"
                   "def stopped_here(name, *args, **kwargs):\n    if name == %r and not sent:\n        sent.append(name)\n        os.kill(os.getpid(), signal.SIGINT)\n    return real(name, *args, **kwargs)\n"
                   "builtins.__import__ = stopped_here\nsys.argv = [%r] + sys.argv[1:]\nrunpy.run_path(%r, run_name='__main__')\n")
        before = self.snapshot()
        for module in ("argparse", "json", "_colour", "_install", "_palette", "_refusal", "_site", "_proc"):
            for argv in (["install", "--site", self.site, "--test-command", GREEN], ["palette", self.p("BRAND.md")]):
                with self.subTest(module=module, command=argv[0]):
                    r = subprocess.run([sys.executable, "-c", program % (module, script, script)] + argv, capture_output=True, text=True, encoding="utf-8", timeout=120)
                    self.assertEqual((r.returncode, r.stdout, r.stderr), (2, "Stopped (Ctrl-C). Nothing was written.\n", ""))
        # a run that was asked for JSON says it as JSON: one object on one line, also when the stop came while `json` itself was loaded
        for module, argv in (("json", ["install", "--site", self.site, "--test-command", GREEN, "--json"]), ("_install", ["install", "--json", "--site", self.site]), ("_palette", ["palette", self.p("BRAND.md"), "--json"])):
            with self.subTest(module=module, command=argv[0], json=True):
                r = subprocess.run([sys.executable, "-c", program % (module, script, script)] + argv, capture_output=True, text=True, encoding="utf-8", timeout=120)
                self.assertEqual((r.returncode, r.stdout, r.stderr), (2, self.STOPPED_JSON, ""))
                self.assertEqual(json.loads(r.stdout), {"status": "stopped", "exit": 2, "message": "Stopped (Ctrl-C). Nothing was written."})
        self.assertEqual(self.snapshot(), before)
        # imported by another program (a test, say), the same Ctrl-C is that program's to deal with
        r = subprocess.run([sys.executable, "-c", (program % ("_install", script, script)).replace("runpy.run_path(%r, run_name='__main__')" % script, "sys.path.insert(0, %r)\ntry:\n    import brand_intake\n"
                            "except KeyboardInterrupt:\n    print('left to the caller')\n" % T.SCRIPTS)], capture_output=True, text=True, timeout=120)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "left to the caller\n", ""))

    def test_ctrl_c_before_the_install_has_begun_to_watch_for_it_ends_in_one_line_with_status_2_and_no_traceback(self):
        # the command line itself, run as the file it is, with a Ctrl-C in the moment its arguments are read
        script = os.path.abspath(os.path.join(T.SCRIPTS, "brand_intake.py"))
        program = ("import argparse, os, runpy, signal, sys\nsignal.signal(signal.SIGINT, signal.default_int_handler)\nreal = argparse.ArgumentParser.parse_args\n"
                   "def stopped_here(self, *args, **kwargs):\n    os.kill(os.getpid(), signal.SIGINT)\n    return real(self, *args, **kwargs)\n"
                   "argparse.ArgumentParser.parse_args = stopped_here\nsys.argv = [%r] + sys.argv[1:]\nrunpy.run_path(%r, run_name='__main__')\n" % (script, script))
        before = self.snapshot()
        for argv in (["install", "--site", self.site, "--test-command", GREEN], ["palette", self.p("BRAND.md")], ["palette", self.p("BRAND.md"), "--json"],
                     ["install", "--site", self.site, "--test-command", GREEN, "--json"]):
            with self.subTest(argv=argv[0], json="--json" in argv):
                r = subprocess.run([sys.executable, "-c", program] + argv, capture_output=True, text=True, encoding="utf-8", timeout=120)
                self.assertEqual((r.returncode, r.stdout, r.stderr), (2, self.STOPPED_JSON if "--json" in argv else "Stopped (Ctrl-C). Nothing was written.\n", ""))
        self.assertEqual(self.snapshot(), before)

    def test_help_and_an_argument_the_command_does_not_take_end_the_process_as_a_report_does_at_once_and_with_everything_printed(self):
        # argparse leaves by sys.exit, through Python's shutting down: the moment in which a signal ends the process
        # with the signal's status, which the command line closes for every other way out. What Python's shutting
        # down would do is stood in for by something registered to run then, as in the test above: it is not run.
        late = "import atexit\ndef at_the_end():\n    signal.signal(signal.SIGTERM, signal.SIG_DFL)\n    os.kill(os.getpid(), signal.SIGTERM)\natexit.register(at_the_end)\n"
        program = "import os, signal, sys\nsys.path.insert(0, %r)\nimport brand_intake\n%sbrand_intake.command_line(sys.argv[1:])\n" % (T.SCRIPTS, late)
        usage = "usage: brand_intake.py [-h] {palette,install} ..."
        for argv, code, printed, said in ((["--help"], 0, usage, ""), (["install", "--help"], 0, "usage: brand_intake.py install [-h] --site SITE", ""), ([], 2, "", usage),
                                          (["install"], 2, "", "brand_intake.py install: error: the following arguments are required: --site"), (["palette", "BRAND.md", "--colour"], 2, "", "unrecognized arguments: --colour")):
            with self.subTest(argv=argv):
                r = subprocess.run([sys.executable, "-c", program] + argv, capture_output=True, text=True, encoding="utf-8", timeout=120)
                self.assertEqual(r.returncode, code, r.stdout + r.stderr)
                self.assertIn(printed, r.stdout)
                self.assertIn(said, r.stderr)
                self.assertTrue((r.stdout + r.stderr).endswith("\n"), "what argparse had to say arrived whole")
        # (round 7) with the error output closed, argparse on Python 3.9 had nothing to write its word to, and the run ended with 1
        script = os.path.abspath(os.path.join(T.SCRIPTS, "brand_intake.py"))
        for argv in (["install", "--bogus"], ["palette"], []):
            with self.subTest(argv=argv, error_output="closed"):
                r = subprocess.run(["/bin/sh", "-c", 'exec "$@" 2>&-', "sh", sys.executable, script] + argv, capture_output=True, timeout=120)
                self.assertEqual((r.returncode, r.stdout, r.stderr), (2, b"", b""))
        # (round 7) a flag cut short is no flag: `--js` was taken for `--json`, and the line of an early stop, which looks for the word itself, was then not JSON
        for argv in (["install", "--site", self.site, "--js"], ["install", "--site", self.site, "--dry"], ["palette", self.p("BRAND.md"), "--js"]):
            with self.subTest(argv=argv[2:]):
                r = subprocess.run([sys.executable, script] + argv, capture_output=True, text=True, encoding="utf-8", timeout=120)
                self.assertEqual((r.returncode, r.stdout), (2, ""))
                self.assertIn("unrecognized arguments: " + argv[-1], r.stderr)
        whole = subprocess.run([sys.executable, "-c", "import sys\nsys.path.insert(0, %r)\nimport brand_intake\nbrand_intake.main(['install', '--help'])\n" % T.SCRIPTS], capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertEqual(subprocess.run([sys.executable, "-c", program, "install", "--help"], capture_output=True, text=True, encoding="utf-8", timeout=120).stdout, whole.stdout, "not a line of the help is lost on the way out")

    def test_a_second_ctrl_c_can_neither_cut_the_early_stop_short_nor_end_the_process_another_way(self):
        # (round 7) The line of an early stop is said with Python's own handling of Ctrl-C still in place: a second
        # press while it was said was a traceback. Ctrl-C is ignored before the line is said, and a press that comes
        # before it is ignored begins the stop again. The second press is put at each of the two moments, for both
        # places the line is said from: a stop while the tool's modules are loaded, and one while its arguments are read.
        script = os.path.abspath(os.path.join(T.SCRIPTS, "brand_intake.py"))
        first = {"while the modules are loaded": "real = builtins.__import__\nsent = []\ndef stopped_here(name, *args, **kwargs):\n    if name == '_install' and not sent:\n        sent.append(name)\n"
                                                 "        os.kill(os.getpid(), signal.SIGINT)\n    return real(name, *args, **kwargs)\nbuiltins.__import__ = stopped_here\n",
                 "while the arguments are read": "real = argparse.ArgumentParser.parse_args\ndef stopped_here(self, *args, **kwargs):\n    os.kill(os.getpid(), signal.SIGINT)\n    return real(self, *args, **kwargs)\n"
                                                 "argparse.ArgumentParser.parse_args = stopped_here\n"}
        second = {"while the line is said": "said = builtins.print\ndef pressed_again(*args, **kwargs):\n    os.kill(os.getpid(), signal.SIGINT)\n    return said(*args, **kwargs)\nbuiltins.print = pressed_again\n",
                  "before Ctrl-C is ignored": "sets, again = signal.signal, []\ndef pressed_again(number, handler):\n    if handler == signal.SIG_IGN and not again:\n        again.append(number)\n"
                                              "        os.kill(os.getpid(), signal.SIGINT)\n    return sets(number, handler)\nsignal.signal = pressed_again\n"}
        before = self.snapshot()
        for when, stop in first.items():
            for then, press in second.items():
                for argv in (["install", "--site", self.site, "--test-command", GREEN], ["palette", self.p("BRAND.md"), "--json"]):
                    with self.subTest(first=when, second=then, command=argv[0]):
                        program = ("import argparse, builtins, os, runpy, signal, sys\nsignal.signal(signal.SIGINT, signal.default_int_handler)\n" + press + stop
                                   + "sys.argv = [%r] + sys.argv[1:]\nrunpy.run_path(%r, run_name='__main__')\n" % (script, script))
                        r = subprocess.run([sys.executable, "-c", program] + argv, capture_output=True, text=True, encoding="utf-8", timeout=120)
                        self.assertEqual((r.returncode, r.stdout, r.stderr), (2, self.STOPPED_JSON if "--json" in argv else "Stopped (Ctrl-C). Nothing was written.\n", ""))
        self.assertEqual(self.snapshot(), before)

    # --- at a terminal (round 7) ---
    # The program below is the terminal's own, as a shell is: it runs the command, says how it ended and how the
    # terminal's settings were before and after, and stays (a shell waits for the next command) until the test ends it.
    TERMINAL = ("import json, os, signal, subprocess, sys, termios\nsignal.signal(signal.SIGINT, lambda *a: None)\nbefore = repr(termios.tcgetattr(0))\n"
                "p = subprocess.Popen(sys.argv[1:])\n_pid, status = os.waitpid(p.pid, 0)\n"
                "ended = os.WEXITSTATUS(status) if os.WIFEXITED(status) else 'ended by signal %d' % os.WTERMSIG(status)\n"
                "sys.stderr.write('\\n' + json.dumps({'ended': ended, 'before': before, 'after': repr(termios.tcgetattr(0))}) + '\\n')\nsys.stderr.flush()\nwhile True:\n    signal.pause()\n")

    def at_a_terminal(self, command, keeps):
        """Start a command at a terminal of this test's own (a pty), in the foreground of it: (the process of the
        terminal's own program, the end of the terminal that a terminal window holds). Nothing typed is printed
        back. `keeps` says whether the terminal keeps what it has not shown yet when the interrupt key is typed
        (NOFLSH); a terminal as it comes throws that away. Skips where no terminal is to be had."""
        try:
            import fcntl
            import pty
            import termios
            window, inside = pty.openpty()
        except (ImportError, OSError) as e:
            self.skipTest("no terminal to be had here: %s" % e)
        self.addCleanup(os.close, window)
        now = termios.tcgetattr(inside)
        now[3] = (now[3] & ~(termios.ECHO | termios.NOFLSH)) | (termios.NOFLSH if keeps else 0)
        termios.tcsetattr(inside, termios.TCSANOW, now)

        def as_the_terminals_own():
            for name in ("SIGINT", "SIGHUP", "SIGTERM", "SIGQUIT"):
                signal.signal(getattr(signal, name), signal.SIG_DFL)
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        try:
            p = subprocess.Popen([sys.executable, "-c", self.TERMINAL] + list(command), stdin=inside, stdout=inside, stderr=subprocess.PIPE, preexec_fn=as_the_terminals_own)
        finally:
            os.close(inside)
        self.addCleanup(p.stderr.close)
        self.addCleanup(p.wait)
        self.addCleanup(p.kill)   # (the terminal's own program stays until it is ended, as a shell does)
        return p, window

    def test_ctrl_c_typed_twice_at_a_terminal_in_the_tools_first_moments_ends_in_the_one_line_and_leaves_the_terminal_as_it_was(self):
        # Round 6 changed a terminal's settings around every line the command says, the line of an early stop too: a
        # second Ctrl-C a few milliseconds after an early first one was a traceback (35 of 300 runs at 4 ms apart),
        # in some of them with the terminal left changed for the commands that follow. Nothing sets a terminal's
        # modes any more. Here the keys are typed at a terminal: the first when the tool loads its modules, the second
        # 1 to 40 ms later. Every run ends with status 2 and nothing on the error output, and the terminal's
        # settings are as they were. The line arrives on a terminal that keeps its output. One as it comes may throw
        # the line away at the second press (the limit brand_intake._say states): there it is the line, or nothing.
        import select
        script, there = os.path.abspath(os.path.join(T.SCRIPTS, "brand_intake.py")), os.path.join(self.tmp.name, "loading")
        program = ("import builtins, os, runpy, signal, sys, time\nreal = builtins.__import__\ndef waits_here(name, *args, **kwargs):\n    if name == '_install' and not os.path.exists(%r):\n"
                   "        open(%r, 'w').close()\n        time.sleep(300)\n    return real(name, *args, **kwargs)\nbuiltins.__import__ = waits_here\n"
                   "sys.argv = [%r] + sys.argv[1:]\nrunpy.run_path(%r, run_name='__main__')\n" % (there, there, script, script))
        before = self.snapshot()
        for n, gap in enumerate((0.001, 0.002, 0.004, 0.008, 0.015, 0.025, 0.040) * 4):
            keeps, argv = bool(n % 2), ["palette", self.p("BRAND.md"), "--json"] if n % 4 > 1 else ["install", "--site", self.site, "--test-command", GREEN]
            with self.subTest(gap=gap, keeps=keeps, command=argv[0]):
                p, window = self.at_a_terminal([sys.executable, "-c", program] + argv, keeps)
                self.assertTrue(self.until(lambda: os.path.exists(there), p, limit=300), "the tool never came to load its modules")
                os.write(window, b"\x03")
                time.sleep(gap)
                os.write(window, b"\x03")
                shown, said, end = b"", b"", time.time() + 300
                while not said.endswith(b"}\n") and time.time() < end:   # until the terminal's own program has said how the command ended
                    for ready in select.select([window, p.stderr], [], [], 0.05)[0]:
                        if ready is window:
                            shown += os.read(window, 65536)
                        else:
                            said += os.read(p.stderr.fileno(), 65536)
                while select.select([window], [], [], 0.2)[0]:
                    shown += os.read(window, 65536)
                p.kill()
                os.remove(there)
                errors, _newline, ended = said.rpartition(b"\n")[0].rpartition(b"\n")
                ended = json.loads(ended.decode("utf-8"))
                self.assertEqual((ended["ended"], errors.decode("utf-8")), (2, ""), "status 2, and no traceback")
                self.assertEqual(ended["after"], ended["before"], "the terminal's settings are as they were before the run")
                line = self.STOPPED_JSON if "--json" in argv else "Stopped (Ctrl-C). Nothing was written.\n"
                self.assertIn(shown.decode("utf-8").replace("\r\n", "\n"), (line,) if keeps else (line, ""))
        self.assertEqual(self.snapshot(), before)

    def test_a_report_that_nobody_reads_any_more_changes_neither_the_runs_status_nor_puts_an_error_out(self):
        # `... | head -1`, a terminal that went away: the write of the report fails, and Python said so twice over
        # (exit status 120, "Exception ignored ... BrokenPipeError") after an install that stood
        script = os.path.abspath(os.path.join(T.SCRIPTS, "brand_intake.py"))
        for name, extra, code_wanted in (("an install that stands", (), 0), ("a refusal", ("--with-colours", "--keep-colours"), 2), ("a dry run in JSON", ("--dry-run", "--json"), 0)):
            with self.subTest(name=name):
                p = subprocess.Popen([sys.executable, script, "install", "--site", self.site, "--test-command", GREEN] + list(extra), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p.stdout.close()   # the reader is gone before the report is written
                err = p.stderr.read()
                p.stderr.close()
                self.assertEqual((p.wait(timeout=120), err), (code_wanted, b""))
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).light, T.BAKERY_LIGHT, "and the install is in")

    def test_a_ctrl_c_once_the_palette_report_is_being_said_changes_neither_the_report_nor_the_status(self):
        # (round 8) INVARIANT: a run says one report, and ends with that report's status. `palette` listens to Ctrl-C to its
        # end: a press that came once the report was handed over and before the command left gave the whole report, then
        # the stop's line (two JSON objects where JSON was asked for), and status 2 for a check that had passed. main now
        # keeps the status before it says the report, and from then on a Ctrl-C ends the command with that status and
        # says nothing more. The press is put at each moment from the report's first write to the end of its flush.
        script = os.path.abspath(os.path.join(T.SCRIPTS, "brand_intake.py"))
        passes, fails = os.path.join(self.tmp.name, "passes.md"), os.path.join(self.tmp.name, "fails.md")
        for path, text in ((passes, BAKERY_BRAND_MD), (fails, BAKERY_BRAND_MD.replace("| Muted | `%s` |" % T.BAKERY_LIGHT["muted"], "| Muted | `#f0e6d8` |"))):
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        program = ("import builtins, os, runpy, signal, sys\nsignal.signal(signal.SIGINT, signal.default_int_handler)\nWHEN, sent = %r, []\n"
                   "def press(when):\n    if when == WHEN and not sent:\n        sent.append(when)\n        os.kill(os.getpid(), signal.SIGINT)\n"
                   "class Pressed(object):\n    def __init__(self, real):\n        self.real = real\n"
                   "    def write(self, text):\n        n = self.real.write(text)\n        press('when the report is written and its line end is not')\n        return n\n"
                   "    def flush(self):\n        press('before the report is handed over')\n        self.real.flush()\n        press('when the report is handed over')\n"
                   "    def __getattr__(self, name):\n        return getattr(self.real, name)\n"
                   "say = builtins.print\ndef said(*args, **kwargs):\n    press('as the report reaches print')\n    return say(*args, **kwargs)\nbuiltins.print = said\n"
                   "sys.stdout = Pressed(sys.stdout)\nsys.argv = [%r] + sys.argv[1:]\nrunpy.run_path(%r, run_name='__main__')\n")
        statuses = set()
        for argv in (["palette", passes], ["palette", passes, "--json"], ["palette", fails], ["palette", fails, "--json"], ["palette", passes, "--css", self.p("src/styles/global.css"), "--json"]):
            plain = subprocess.run([sys.executable, script] + argv, capture_output=True, text=True, encoding="utf-8", timeout=120)
            self.assertEqual((plain.returncode in (0, 1), plain.stderr), (True, ""), plain.stdout)
            statuses.add(plain.returncode)
            for when in ("when the report is written and its line end is not", "before the report is handed over", "when the report is handed over"):
                with self.subTest(argv=[os.path.basename(a) for a in argv], press=when):
                    r = subprocess.run([sys.executable, "-c", program % (when, script, script)] + argv, capture_output=True, text=True, encoding="utf-8", timeout=120)
                    self.assertEqual((r.returncode, r.stderr), (plain.returncode, ""), r.stdout)
                    self.assertEqual(r.stdout, plain.stdout[:-1] if when.endswith("is not") else plain.stdout, "the report, once, and nothing after it")
                    self.assertNotIn("Stopped", r.stdout)
                    if "--json" in argv:
                        self.assertEqual((json.loads(r.stdout)["exit"], len(r.stdout.strip().splitlines())), (plain.returncode, 1), "one JSON object, and its status is the command's")
            # A press before the report is said is a stop, as before: its one line, status 2. (The press is made to arrive while the palette is read.)
            early = program.replace("builtins.print = said\n", "builtins.print = said\nreal_open = builtins.open\ndef opened(*args, **kwargs):\n    press('while the palette is read')\n    return real_open(*args, **kwargs)\nbuiltins.open = opened\n")
            r = subprocess.run([sys.executable, "-c", early % ("while the palette is read", script, script)] + argv, capture_output=True, text=True, encoding="utf-8", timeout=120)
            self.assertEqual((r.returncode, r.stdout, r.stderr), (2, self.STOPPED_JSON if "--json" in argv else "Stopped (Ctrl-C). Nothing was written.\n", ""))
            # The limit command_line states: a press in the instant between the status being kept and the report reaching
            # `print` ends the command with the report's status and no report. (Never two reports, and never the stop's line with another status.)
            r = subprocess.run([sys.executable, "-c", program % ("as the report reaches print", script, script)] + argv, capture_output=True, text=True, encoding="utf-8", timeout=120)
            self.assertEqual((r.returncode, r.stdout, r.stderr), (plain.returncode, "", ""))
        self.assertEqual(statuses, {0, 1}, "a check that passes and one that fails were both stopped")
        # No caller's handling of Ctrl-C is changed by main: it is as it was once main has returned, and a second call starts with no status kept.
        before = signal.getsignal(signal.SIGINT)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(brand_intake.main(["palette", fails]), 1)
        self.assertEqual((signal.getsignal(signal.SIGINT), brand_intake._OUTCOME), (before, [1]))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            brand_intake.main(["palette"])
        self.assertEqual(brand_intake._OUTCOME, [], "a run that ended before it had a report keeps no status from the run before")


class ALogoOnASiteAsSheLeftIt(SiteCase):
    """The same round, for a run that installs a logo (sharp is needed)."""

    WHITE = rects((4, 4, 24, 24, "#ffffff"))

    def fresh(self):
        shutil.rmtree(self.site)
        T.make_starter_site(self.site, with_modules=self.modules)

    def logo(self, *more):
        return ("--input", self.package()) + LOGO_ARGS + more

    # --- what the logo is checked against --------------------------------------------------------

    def test_a_logo_beside_a_palette_the_reading_does_not_use_goes_in_and_the_report_says_why_the_colours_stayed(self):
        night = BAKERY_BRAND_MD.replace("### Dark theme", "### Night")
        for name, text, head in (("no colour read", OTHER_HEADINGS, "Note: the colours were not changed: no colour could be read from the palette in BRAND.md"),
                                 ("one table read and one not", night, "Note: the colours were not changed: BRAND.md does not hold a complete palette (rows not filled in: "
                                  "Accent, Background, Body (ink), Hairline, Heading, Link, Muted, Soft background, Surface (cards))")):
            with self.subTest(name=name):
                self.fresh()
                self.brand_md(text)
                read = _palette.parse_tables(text)
                stylesheet = self.read("src/styles/global.css")
                for code, out in self.both_runs(*self.logo()):
                    self.assertEqual(code, 0, out)
                    lines = out.splitlines()
                    at = lines.index(head)
                    self.assertEqual(lines[at + 1:at + 1 + len(read.problems)], ["  " + m for _theme, _row, _code, m in read.problems])
                    self.assertEqual("  " + _palette.FORM in lines, not read.rows_found)
                self.assertEqual(self.read("src/styles/global.css"), stylesheet)
                self.assertTrue(self.exists("public/images/logo.png"))

    def test_a_logo_is_not_checked_against_the_sites_own_colours_when_this_tool_could_not_read_all_of_them(self):
        css = T.starter_file("src/styles/global.css")
        for name, text in (("a colour block written in another way than the starter's", css.replace(":root {", ":root, html {", 1)),
                           ("a colour that points at a variable nothing sets", css.replace("  --bg: #ffffff;", "  --bg: var(--paper);", 1)),
                           ("a dark block that stands twice", css + '\n:root[data-theme="dark"] {\n  --bg: #222222;\n}\n'),
                           ("a colour marked important", css.replace("  --bg-soft: #f5f7fb;", "  --bg-soft: #f5f7fb !important;", 1))):
            for keep in (False, True):   # a logo alone, and a logo beside a palette she said to leave out
                with self.subTest(name=name, keep=keep):
                    self.assertNotEqual(text, css)
                    self.fresh()
                    self.put("src/styles/global.css", text)
                    if keep:
                        self.brand_md()
                    problems = _install._css_problems(_palette.read_css(text))
                    self.assertTrue(problems)
                    before = self.snapshot()
                    for code, out in self.both_runs(*self.logo(*(("--keep-colours",) if keep else ())), brand=keep):
                        self.assertEqual(code, 2, out)
                        self.assertIn("this tool could not read all of them from src/styles/global.css:", out)
                        for said in problems:
                            self.assertIn(said, out.splitlines())
                        self.assertIn("Nothing was written.", out.splitlines())
                        self.assertEqual(self.snapshot(), before)
                    self.assertEqual(json.loads(self.intake(*self.logo("--json", *(("--keep-colours",) if keep else ())), brand=keep)[1])["code"], "site-colours-unread")

    def test_company_logo_is_read_back_by_node_and_claimed_in_the_report_only_where_node_read_it(self):
        # the same read-back for COMPANY.logo, on a run about the logo alone: Node is asked, Python is not (no colour of the generator is set)
        self.need_read_back()
        config = T.starter_file("src/config.ts")
        listed = config.replace("            // resolved against SITE.url for schema\n", "\n  sameAs: ['https://example.org/us'],\n")
        self.assertIn("  logo: '/images/logo.png',\n  sameAs: ['https://example.org/us'],\n} as const;", listed)
        points = ", and COMPANY.logo points at public/images/logo.png."
        asks = ("A real run then asks the site's Node what the site reads from src/config.ts: it puts everything back if that is not what it set, and adds a note where it could not ask. "
                "A dry run writes nothing, so it cannot ask.")
        for label, text in (("the starter's own block", config), ("a list below the logo's line, which makes the block one this tool does not edit: the line already says the address", listed),
                            ("an address of her own, which the run sets", config.replace("logo: '/images/logo.png'", "logo: '/images/hers.png'"))):
            with self.subTest(label=label):
                self.fresh()
                self.put("src/config.ts", text)
                (dry_code, dry), (code, out) = self.both_runs(*self.logo("--json"), brand=False)
                self.assertEqual((dry_code, code), (0, 0), out)
                self.assertEqual((json.loads(dry)["read_back"], json.loads(out)["read_back"]), ({}, {"src/config.ts": {"status": "ok"}}))
                self.assertIn(asks, json.loads(dry)["report"])
                self.assertEqual([n for n in json.loads(dry)["notes"] + json.loads(out)["notes"] if "could not check" in n], [])
                logo = [l for l in json.loads(out)["report"] if l.startswith("Logo: ")]
                self.assertTrue(len(logo) == 1 and logo[0].endswith(points), logo)
        # the address the site reads is another: everything is put back, the icons too
        self.fresh()
        self.put("src/config.ts", config.replace("            // resolved against SITE.url for schema\n} as const;", "\n} && { logo: '/images/other.png' };"))
        before = self.snapshot()
        (dry_code, dry), (code, out) = self.both_runs(*self.logo("--json"), brand=False)
        data = json.loads(out)
        self.assertEqual((dry_code, code, data["status"], data["written"]), (0, 1, "read-back-failed", []), out)
        self.assertEqual(data["read_back"], {"src/config.ts": {"status": "differs", "values": [{"name": "logo", "reads": "/images/other.png", "wanted": "/images/logo.png"}]}})
        self.assertEqual(data["report"][1], "src/config.ts: the site reads /images/other.png as COMPANY.logo (this tool asked the site's own Node). Line 34 already says /images/logo.png, and this run "
                         "left it, so something else in the file decides the value. Set it by hand where the file decides it, or have the developer mend the file, then run this again.")
        self.assertEqual(data["report"][2], "Everything it had written was put back.")
        self.assertEqual(self.snapshot(), before)
        self.put("src/config.ts", self.read("src/config.ts").replace("'/images/other.png'", "'/images/logo.png'"))   # set by hand where the file decides it
        self.assertEqual(self.intake(*self.logo(), brand=False)[0], 0)
        # the address set again by a line below the block, which round 5 refused from the text: the line is edited, Node is asked, everything is put back
        self.fresh()
        self.put("src/config.ts", config.replace("logo: '/images/logo.png'", "logo: '/images/hers.png'") + "// @ts-ignore\nCOMPANY.logo = '/images/other.png';\n")
        before = self.snapshot()
        code, out = self.intake(*self.logo("--json"), brand=False)
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["read_back"]), (1, "read-back-failed", {"src/config.ts": {"status": "differs", "values": [{"name": "logo", "reads": "/images/other.png", "wanted": "/images/logo.png"}]}}), out)
        self.assertTrue(data["report"][1].startswith("src/config.ts: the site reads /images/other.png as COMPANY.logo (this tool asked the site's own Node). This run set /images/logo.png on line 34, so something else"), data["report"][1])
        self.assertEqual(self.snapshot(), before)
        # (round 8) the address only in an object inside the block: the site reads nothing as COMPANY.logo, and nothing else in the file
        # decides it. The sentence says the block has no `logo` of its own and shows the line; done to the character, the next run passes.
        self.fresh()
        inside = config.replace("  logo: '/images/logo.png',            // resolved against SITE.url for schema\n", "  parent: {\n    logo: '/images/logo.png',\n  },\n")
        self.put("src/config.ts", inside)
        before = self.snapshot()
        code, out = self.intake(*self.logo("--json"), brand=False)
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["written"]), (1, "read-back-failed", []), out)
        self.assertEqual(data["report"][1], "src/config.ts: the site reads nothing as COMPANY.logo (this tool asked the site's own Node). The file already says /images/logo.png, and this run left it, but the "
                         "`COMPANY` block has no `logo` of its own: the line that says it belongs to something inside the block. Write `logo: '/images/logo.png',` as the first line under the block's opening "
                         "line (it starts `export const COMPANY`), and where that other line was changed to say /images/logo.png, put back what it said before. Then run this again.")
        self.assertEqual(self.snapshot(), before)
        self.put("src/config.ts", follow_read_back(self.read("src/config.ts"), data["report"][1]))
        self.assertEqual(self.read("src/config.ts"), inside.replace("export const COMPANY = {\n", "export const COMPANY = {\nlogo: '/images/logo.png',\n"))
        code, out = self.intake(*self.logo("--json"), brand=False)
        self.assertEqual((code, json.loads(out)["status"], json.loads(out)["read_back"]), (0, "done", {"src/config.ts": {"status": "ok"}}), out)
        # a Node that draws the icons and reads no TypeScript: the logo goes in, and the report claims no more than it knows
        if os.name == "posix":
            self.fresh()
            self.old_node("unknown")
            code, out = self.intake(*self.logo("--json"), brand=False)
            data = json.loads(out)
            self.assertEqual((code, data["status"]), (0, "done"), out)
            note = "this tool could not check that the site reads `logo` from line 34 of src/config.ts, where it is set: the Node on this computer (v20.11.0) does not read a TypeScript file"
            self.assertEqual([n for n in data["notes"] if "could not check" in n], [note])
            logo = [l for l in data["report"] if l.startswith("Logo: ")]
            self.assertTrue(logo[0].endswith(". COMPANY.logo is written in src/config.ts, and this tool could not check that the site reads it from there: see the note about it."), logo)
            self.assertNotIn("COMPANY.logo points at", logo[0])

    def test_whose_the_favicon_is_is_asked_only_once_the_sites_colours_are_known_to_be_all_there(self):
        # the favicon was cleaned against the site's Primary before the run was refused over colours it could
        # not read: on exactly those runs there may be no Primary at all
        css = T.starter_file("src/styles/global.css")
        unread = re.sub(r"(?m)^  --(?:brand|accent): [^\n]*\n", "", css, count=2)
        read = _palette.read_css(unread)
        self.assertEqual((read.brand, read.light.get("accent")), (None, None))
        self.assertTrue(read.problems)
        self.put("src/styles/global.css", unread)
        self.put("public/favicon.svg", _install.MARK.encode("utf-8") + b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="currentColor"/></svg>\n')
        before = self.snapshot()
        asked, real = [], _install._own_master

        def noted(master, primary):
            asked.append(primary)
            return real(master, primary)
        _install._own_master = noted
        try:
            runs = self.both_runs("--with-logo", "--json", brand=False)
        finally:
            _install._own_master = real
        for code, out in runs:
            data = json.loads(out)
            self.assertEqual((code, data["status"], data["code"]), (2, "refused", "site-colours-unread"), out)
            self.assertIn("this tool could not read all of them from src/styles/global.css:", data["message"])
        self.assertEqual(asked, [], "the refusal comes first: the favicon is not looked into with colours that are not all there")
        self.assertEqual(self.snapshot(), before)
        # with the stylesheet mended, the same run does look, with the Primary the site has
        self.put("src/styles/global.css", css)
        _install._own_master = noted
        try:
            self.intake("--with-logo", "--dry-run", brand=False)
        finally:
            _install._own_master = real
        self.assertEqual(asked, ["#000000"])

    # --- the favicon this tool installed is known by its own line ---------------------------------

    def test_the_installed_favicon_starts_with_this_tools_line_is_still_one_svg_and_is_known_again_by_the_next_run(self):
        import xml.dom.minidom
        self.assertEqual(self.intake(*self.logo(), brand=False)[0], 0)
        data, line = self.bytes("public/favicon.svg"), _install.MARK.encode("utf-8")
        self.assertTrue(data.startswith(line))
        self.assertRegex(_install.MARK, r"^<!-- [^\n]* -->\n$")
        self.assertNotIn("--", _install.MARK[4:-4], "two hyphens would end the comment early")
        body = data[len(line):]
        self.assertEqual(_svg.clean_svg(body).text.encode("utf-8"), body, "the rest is the cleaned drawing")
        self.assertEqual(_svg.clean_svg(data).text.encode("utf-8"), body, "and the line is no part of the drawing")
        self.assertEqual(xml.dom.minidom.parseString(data).documentElement.tagName, "svg")
        after_first = self.snapshot()
        self.assertEqual(self.intake(*self.logo(), brand=False)[0], 0)
        self.assertEqual(self.snapshot(), after_first, "a second run sees its own file and writes nothing")
        self.brand_md()   # the colours change: the file is known as this tool's own, and the icons are drawn again
        code, out = self.intake("--accept-colours", "--accept-low-contrast", "both", "--replace-icons")
        self.assertEqual(code, 0, out)
        self.assertNotIn("is not a file this tool wrote", out)
        self.assertEqual(self.bytes("public/favicon.svg"), data)
        import _png
        self.assertEqual(_png.at(_png.decode(self.bytes("public/icon-maskable-512.png")), 0, 0)[:3], (0xff, 0xf8, 0xee), "on the palette's background")

    # --- the share cards' emblem is not this tool's -------------------------------------------------
    # The generator's LOGO line is neither set nor taken out, and nothing is judged about text over an
    # emblem: whatever the line says, it is hers. A run that does the logo says so in one line.

    def logo_lines(self):
        return [l for l in self.read("scripts/generate_og_cards.py").splitlines() if "LOGO" in l or "EMBLEM" in l]

    def test_no_run_sets_takes_out_or_judges_the_generators_logo_line_whatever_it_says(self):
        starter = T.starter_file("scripts/generate_og_cards.py")
        again = ("--with-logo", "--with-colours", "--accept-colours", "--accept-low-contrast", "both")
        for name, generator in (("as the starter has it", starter),
                                ("the picture this tool installs, as its own earlier rounds set it", starter.replace("LOGO = None", 'LOGO = ROOT / "public/images/logo.png"')),
                                ("the same, as the generator's own comment spells a path", starter.replace("LOGO = None", "LOGO = ROOT/'public/images/logo.png'")),
                                ("a picture of her own", starter.replace("LOGO = None", 'LOGO = ROOT / "public/mine.png"')),
                                ("the line twice", starter.replace("# Home + fallback card", 'LOGO = ROOT / "public/images/logo.png"\n\n# Home + fallback card', 1)),
                                ("no such line", starter.replace("LOGO = None", "EMBLEM = None"))):
            with self.subTest(name=name):
                self.assertTrue(name == "as the starter has it" or generator != starter)
                self.fresh()
                self.put("scripts/generate_og_cards.py", generator)
                hers = self.logo_lines()
                redrawn = ("--accept-colours", "--accept-low-contrast", "both", "--replace-icons")
                for step, args, brand in (("a logo alone", self.logo(), False), ("then the colours, and the icons drawn again on the new background", redrawn, True),
                                          ("then the colours alone", (), True), ("then the icons again", again, True)):
                    if brand:
                        self.brand_md()
                    for code, out in self.both_runs(*args, brand=brand):
                        self.assertEqual(code, 0, "%s: %s" % (step, out))
                        self.assertEqual(self.logo_lines(), hers, "%s: the line is as she left it" % step)
                        for untrue in ("go without the emblem", "would fall to", "goes back to None", "an earlier run set", "the emblem is a picture", "emblem point at"):
                            self.assertNotIn(untrue, out)
                        said = [l for l in out.splitlines() if "emblem" in l]
                        if step == "then the colours alone":
                            self.assertEqual(said, [], "a run about colours has nothing to say of the emblem")
                        else:
                            self.assertEqual(said, ["Note: the share cards get no emblem from this tool (the logo, shown faintly on each card): it leaves the LOGO line in "
                                                    "scripts/generate_og_cards.py exactly as it is. The og-images skill says how to put the logo on the cards"])
                    if step == "a logo alone":
                        self.assertEqual(self.read("scripts/generate_og_cards.py"), generator, "a logo alone changes not a byte of the generator")
                self.assertRegex(self.read("scripts/generate_og_cards.py"), r"(?m)^BG_BOT = \(26, 18, 13\)", "the colours went in around the line")

    def test_a_line_she_set_by_hand_after_a_logo_run_is_still_there_after_the_next_run_about_colours(self):
        # the round before told her she could set LOGO by hand, and its next colours run set it back to None,
        # saying "an earlier run set" it
        self.brand_md()
        self.assertEqual(self.intake(*self.logo("--with-colours"))[0], 0)
        self.assertEqual(self.logo_lines()[0].split("#")[0].strip(), "LOGO = None")
        by_hand = self.read("scripts/generate_og_cards.py").replace("LOGO = None", 'LOGO = ROOT / "public/images/logo.png"', 1)
        self.put("scripts/generate_og_cards.py", by_hand)
        self.brand_md(BAKERY_BRAND_MD.replace("| Accent | `#e2874a` |", "| Accent | `#d47c44` |"))   # the colours under the emblem change
        (dry_code, dry), (code, out) = self.both_runs("--json", "--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual((dry_code, code), (0, 0), out)
        self.assertEqual(json.loads(dry)["written"], json.loads(out)["written"])
        generator = self.read("scripts/generate_og_cards.py")
        self.assertIn('\nLOGO = ROOT / "public/images/logo.png" ', generator)
        self.assertIn("\nSUB_COL = (212, 124, 68) ", generator)
        self.assertEqual(generator.replace("(212, 124, 68)", "(226, 135, 74)"), by_hand, "the two accent lines changed, and nothing else")

    def test_a_mark_is_installed_whatever_its_colours_would_do_under_the_cards_text(self):
        # a white mark, over which the cards' accent would not read were it their emblem: not this tool's question any more
        self.brand_md()
        args = ("--input", self.package("white.svg", self.WHITE), "--with-colours", "--accept-colours", "--accept-low-contrast", "both")
        (dry_code, dry), (code, out) = self.both_runs(*args)
        self.assertEqual((dry_code, code), (0, 0), out)
        self.assertIn("\nLOGO = None ", self.read("scripts/generate_og_cards.py"))
        self.assertRegex(self.read("scripts/generate_og_cards.py"), r"(?m)^BG_BOT = \(26, 18, 13\)")
        self.assertIn("and COMPANY.logo points at public/images/logo.png.", out)
        self.assertIn("Share cards: regenerated with the new colours.", out)
        self.assertTrue(self.exists("public/images/logo.png"))
        self.assertIn("logo: '/images/logo.png'", self.read("src/config.ts"))

    # --- the colours a logo run would change, in all four files ---------------------------------

    def test_a_logo_run_asks_before_it_changes_a_colour_she_set_by_hand_in_any_of_the_four_files(self):
        # the stylesheet already shows the palette, so it has nothing to say; the other three hold colours too
        self.brand_md()
        self.assertEqual(self.intake()[0], 0)
        settled = {rel: self.read(rel) for rel in _install.OTHER_FILES}
        hand = (("src/config.ts", "themeColor: '#b4531a'", "themeColor: '#123456'", "src/config.ts, themeColor: #123456 becomes #b4531a"),
                ("public/manifest.webmanifest", '"theme_color": "#b4531a"', '"theme_color": "#123456"', "public/manifest.webmanifest, theme_color: #123456 becomes #b4531a"),
                ("public/manifest.webmanifest", '"background_color": "#fff8ee"', '"background_color": "#654321"', "public/manifest.webmanifest, background_color: #654321 becomes #fff8ee"),
                ("scripts/generate_og_cards.py", "BG_TOP = (42, 31, 23)", "BG_TOP = (1, 2, 3)", "scripts/generate_og_cards.py, BG_TOP: #010203 becomes #2a1f17"),
                ("scripts/generate_og_cards.py", "FOOTER_COL = (196, 174, 152)", "FOOTER_COL = (200, 200, 200)", "scripts/generate_og_cards.py, FOOTER_COL: #c8c8c8 becomes #c4ae98"))
        for rel, old, new, line in hand:
            with self.subTest(line=line):
                for other, text in settled.items():
                    self.put(other, text)
                self.assertEqual(settled[rel].count(old), 1)
                self.put(rel, settled[rel].replace(old, new))
                before = self.snapshot()
                for code, out in self.both_runs(*self.logo()):
                    self.assertEqual(code, 3, out)
                    self.assertIn("    * " + line, out.splitlines())
                    self.assertIn("--with-colours", out)
                    self.assertIn("--keep-colours", out)
                    self.assertIn("Nothing was written", out)
                    self.assertEqual(self.snapshot(), before)
                data = json.loads(self.intake(*self.logo("--json"))[1])
                self.assertEqual(([k["code"] for k in data["asks"]], data["asks"][0]["options"], data["changes"]), (["colours-too"], [line], [line]))
                code, out = self.intake(*self.logo("--keep-colours"))
                self.assertEqual(code, 0, out)
                self.assertIn(new, self.read(rel), "kept, as she said")
                self.put(rel, settled[rel].replace(old, new))
                code, out = self.intake(*self.logo("--with-colours"))
                self.assertEqual(code, 0, out)
                self.assertIn(old, self.read(rel))
                at = out.splitlines().index("Colours that changed in the site's other files:")
                self.assertEqual(out.splitlines()[at + 1], "  " + line)
                self.assertNotIn("Colours that changed in src/styles/global.css:", out)

    def test_a_question_about_something_else_still_lists_the_colours_the_run_would_change_and_the_question_about_them_lists_them_once(self):
        self.brand_md()
        self.put("public/apple-touch-icon.png", b"somebody's own icon")
        before = self.snapshot()
        for code, out in self.both_runs(*self.logo("--with-colours")):
            self.assertEqual(code, 3, out)
            self.assertIn("public/apple-touch-icon.png", out)
            for line in ("Colours that would change in src/styles/global.css:", "  Primary: #000000 becomes #b4531a",
                         "Colours that would change in the site's other files:", "  src/config.ts, themeColor: #000000 becomes #b4531a"):
                self.assertIn(line, out.splitlines())
            self.assertEqual(self.snapshot(), before)
        data = json.loads(self.intake(*self.logo("--with-colours", "--json"))[1])
        self.assertEqual([k["code"] for k in data["asks"]], ["replace-icons"])
        self.assertIn("Primary: #000000 becomes #b4531a", data["changes"])
        self.assertIn("public/manifest.webmanifest, background_color: #ffffff becomes #fff8ee", data["changes"])
        code, out = self.intake("--input", self.package(), "--with-colours")   # two drawings in the zip: which one is asked first
        self.assertEqual(code, 3, out)
        self.assertIn(T.REAL_MONO, out)
        self.assertIn("  Primary: #000000 becomes #b4531a", out.splitlines())
        code, out = self.intake(*self.logo())   # the question about the colours themselves names each once
        self.assertEqual(code, 3, out)
        self.assertEqual(out.count("Primary: #000000 becomes #b4531a"), 1)

    # --- a file that is there is never taken for one that is not --------------------------------

    @POSIX
    def test_a_file_the_run_would_replace_or_draw_from_that_is_closed_to_this_account_stops_it_before_anything_is_written(self):
        self.not_as_root()
        master = _install.MARK.encode("utf-8") + _svg.clean_svg(T.real_svg()).text.encode("utf-8")
        for name, rel, data, args in (("an icon it would replace", "public/favicon.ico", b"an icon of her own", self.logo("--replace-icons")),
                                      ("a package kept from an earlier run", "brand-handoff/logo.zip", b"an earlier package", self.logo()),
                                      ("the preview sheet of an earlier run", "brand-handoff/preview.png", b"an earlier preview", self.logo()),
                                      ("the installed logo, asked for outright", "public/favicon.svg", master, ("--with-logo", "--accept-colours", "--accept-low-contrast", "both")),
                                      ("the installed logo, with a new one given", "public/favicon.svg", master, self.logo("--replace-icons"))):
            with self.subTest(name=name):
                self.fresh()
                os.makedirs(os.path.dirname(self.p(rel)), exist_ok=True)
                self.put(rel, data)
                before = self.snapshot()
                was = self.closed(rel)
                try:
                    runs = self.both_runs(*args, brand=False)
                finally:
                    os.chmod(self.p(rel), was)
                for code, out in runs:
                    self.assertEqual(code, 2, out)
                    self.assertIn("%s could not be read or written (Permission denied)" % self.p(rel), out)
                    self.assertIn("Nothing was written.", out)
                    self.assertNotIn("no logo to apply", out)
                self.assertEqual(self.snapshot(), before)

    def test_a_planned_file_that_is_a_link_or_lies_behind_one_is_refused_before_anything_is_written_whatever_the_link_points_at(self):
        outside = os.path.join(self.tmp.name, "outside")
        os.makedirs(os.path.join(outside, "folder"))
        with open(os.path.join(outside, "file.ico"), "wb") as f:
            f.write(b"an icon kept elsewhere")
        for name, rel, target in (("a link to a file", "public/favicon.ico", os.path.join(outside, "file.ico")),
                                  ("a link to a folder", "public/favicon.ico", os.path.join(outside, "folder")),
                                  ("a link to nothing", "public/favicon.ico", os.path.join(outside, "nothing-here")),
                                  ("a link where a folder above the file would be", "brand-handoff", os.path.join(outside, "folder"))):
            with self.subTest(name=name):
                self.fresh()
                os.symlink(target, self.p(rel))
                links, kept = self.links(), tree(outside)
                before = None if name == "a link to nothing" else self.snapshot()   # a link to nothing cannot be read to compare it
                for code, out in self.both_runs(*self.logo("--replace-icons"), brand=False):
                    self.assertEqual(code, 2, out)
                    self.assertIn("%s is a link, and nothing is written through a link%s. Put the file or folder itself where the link is" % (rel, " (brand-handoff/logo.zip is below it)" if rel == "brand-handoff" else ""), out)
                    self.assertIn("Nothing was written", out)
                    self.assertEqual((self.links(), tree(outside)), (links, kept))
                    if before is not None:
                        self.assertEqual(self.snapshot(), before)
                    self.assertFalse(self.exists("public/images/logo.png"))

    # --- what is said, by what happened ----------------------------------------------------------

    def test_a_note_about_something_the_run_changes_says_would_before_was_after_and_put_back_when_it_was_taken_back(self):
        placeholder = b"<svg>placeholder</svg>"
        self.put("public/favicon.svg", placeholder)
        self.put("src/config.ts", self.read("src/config.ts").replace("logo: '/images/logo.png',", "logo: '/brand/own-logo.svg',"))
        before = self.snapshot()
        old = _site.SCAFFOLD_DEFAULTS
        _site.SCAFFOLD_DEFAULTS = {"public/favicon.svg": {hashlib.sha256(placeholder).hexdigest()}}
        try:
            dry = json.loads(self.intake(*self.logo("--json", "--dry-run"), brand=False)[1])
            red = json.loads(self.intake(*self.logo("--json"), command=RED, brand=False)[1])
            self.put("brand-handoff", b"a file where the folder would go")   # refused by the check of every path: nothing is written
            refused = json.loads(self.intake(*self.logo("--json"), brand=False)[1])
            os.remove(self.p("brand-handoff"))
            done = json.loads(self.intake(*self.logo("--json"), brand=False)[1])
        finally:
            _site.SCAFFOLD_DEFAULTS = old
        self.assertEqual((dry["status"], red["status"], refused["status"], done["status"]), ("dry-run", "tests-failed", "refused", "done"))
        would = ["public/favicon.svg is the scaffold's placeholder (the Astro logo), which this run would replace",
                 "COMPANY.logo in src/config.ts points at /brand/own-logo.svg; this run would point it at /images/logo.png, the picture made from this logo, and leave "
                 "the file it points at where it is"]
        for data in (dry, refused):
            self.assertEqual([n for n in data["notes"] if "placeholder" in n or "COMPANY.logo" in n], would)
        self.assertEqual([n for n in red["notes"] if "placeholder" in n or "COMPANY.logo" in n],
                         ["public/favicon.svg is the scaffold's placeholder (the Astro logo): this run replaced it and then put it back",
                          "COMPANY.logo in src/config.ts points at /brand/own-logo.svg, as before: this run pointed it at /images/logo.png and then put that back"])
        self.assertEqual([n for n in done["notes"] if "placeholder" in n or "COMPANY.logo" in n],
                         ["public/favicon.svg was the scaffold's placeholder (the Astro logo), now replaced",
                          "COMPANY.logo in src/config.ts pointed at /brand/own-logo.svg; it now points at /images/logo.png, the picture made from this logo. The file it "
                          "pointed at is left where it is"])
        for data in (dry, red, refused):
            for note in data["notes"]:
                for untrue in ("now replaced", "it now points at", "has the palette"):
                    self.assertNotIn(untrue, note)

    def test_a_company_logo_with_an_escaped_quote_in_it_is_refused_by_name_and_a_run_that_does_not_touch_it_goes_through(self):
        self.put("src/config.ts", self.read("src/config.ts").replace("logo: '/images/logo.png',", "logo: '/it\\'s.png',"))
        self.assertIn("logo: '/it\\'s.png',", self.read("src/config.ts"))
        before = self.snapshot()
        for code, out in self.both_runs(*self.logo(), brand=False):
            self.assertEqual(code, 2, out)
            self.assertIn("src/config.ts: this tool sets the address of the logo only where the file has this one line", out)
            self.assertIn(":\nlogo: '/images/logo.png',\nWhat it found instead: line 34 is written another way: `logo: '/it\\'s.png', // resolved against SITE.url for schema`. "
                          "Write that one line in its place, then run this again", out)
            self.assertIn("Nothing was written", out)
            self.assertNotIn("Note: the share cards get no emblem", out, "a run that was refused before the logo was drawn has nothing to say of the cards")
            self.assertEqual(self.snapshot(), before)
        self.brand_md()   # the colours alone do not touch that line
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        self.assertIn("logo: '/it\\'s.png',", self.read("src/config.ts"))
        self.assertIn("themeColor: '#b4531a'", self.read("src/config.ts"))
        # what the refusal says to do, done: that one line, written as the starter writes it
        mended = self.read("src/config.ts").replace("logo: '/it\\'s.png',", "logo: '/images/logo.png',")
        self.put("src/config.ts", mended)
        (dry_code, _dry), (code, out) = self.both_runs(*self.logo())
        self.assertEqual((dry_code, code), (0, 0), out)
        self.assertEqual(self.read("src/config.ts"), mended, "her line is left as she wrote it")

    def test_the_folders_line_goes_to_the_end_of_gitignore_whenever_a_later_line_could_take_it_back_and_ends_as_the_files_lines_end(self):
        starter = self.bytes(".gitignore").decode("utf-8")
        self.assertNotIn("\r", starter)
        for name, text, end in (("a later line that names no folder", starter + "brand-handoff/*\n!*.svg\n", "\n"),
                                ("the same in a file with Windows line ends", (starter + "brand-handoff/\n!*\n").replace("\n", "\r\n"), "\r\n"),
                                ("a rule with spaces before it, which git reads as part of the name", starter + "  brand-handoff/\n", "\n")):
            with self.subTest(name=name):
                self.fresh()
                self.put(".gitignore", text.encode("utf-8"))
                code, out = self.intake(*self.logo(), brand=False)
                self.assertEqual(code, 0, out)
                self.assertEqual(self.bytes(".gitignore").decode("utf-8"), text + "brand-handoff/" + end)
                self.assertIn("(git ignores that folder)", out)
                self.assertEqual(self.intake(*self.logo(), brand=False)[0], 0)
                self.assertEqual(self.bytes(".gitignore").decode("utf-8"), text + "brand-handoff/" + end, "and it is not added a second time")

    # --- stopped from outside while a logo goes in ------------------------------------------------

    @POSIX
    def test_a_stop_in_the_instant_popen_is_asked_whether_node_has_ended_does_not_leave_the_run_waiting_for_ever(self):
        # the renderer ran Node with subprocess.run(timeout=...): the same lock, taken and only then guarded, in the
        # moment Node is collected. A stop raised there left it taken, and the wait that subprocess itself does on
        # the way out never came back. Node is now run as every other command is (_proc._run); here the stop is put
        # into the first instant the lock is taken for Node, on every Python as on a Mac's (no os.waitid).
        before = self.snapshot()
        for label, signals in (("one stop", "signal.SIGTERM,"), ("two different ones at once", "signal.SIGQUIT, signal.SIGTERM")):
            with self.subTest(label=label):
                scratch = tempfile.mkdtemp(dir=self.tmp.name)
                try:
                    r = self.drive(StoppedFromOutside.LOCK % (1, signals, "'render.mjs' in str(args[0])"), "--json", *self.logo(), tmpdir=scratch, timeout=60)
                except subprocess.TimeoutExpired:
                    self.fail("the run was still going a minute after the stop: it waits for a lock that the stop left taken")
                data = json.loads(r.stdout)
                self.assertEqual((r.returncode, r.stderr, data["status"], data["written"]), (2, "", "stopped", []), r.stdout + r.stderr)
                self.assertIn("Nothing was written.", data["report"])
                self.assertEqual(os.listdir(scratch), [], "the folder the icons are drawn in is gone")
                self.assertEqual(self.snapshot(), before)

    def test_a_stop_during_a_drawing_that_takes_long_ends_the_run_at_once_and_leaves_no_node_behind(self):
        # a stand-in for render.mjs that answers the first check and then, asked to draw, never comes back: the
        # renderer's own limit is three minutes. A stop must not wait for that limit, and Node must go with it.
        if not shutil.which("node"):
            self.skipTest("no node on this machine")
        slow = os.path.join(self.tmp.name, "slow-render-%s.mjs" % os.urandom(4).hex())
        drawing = os.path.join(self.tmp.name, "drawing")
        with open(slow, "w", encoding="utf-8") as f:
            f.write("import { writeFileSync } from 'node:fs';\nif (process.argv.includes('--check')) {\n  console.log(JSON.stringify({ ok: true, sharp: 'stand-in' }));\n} else {\n"
                    "  writeFileSync(%s, 'x');\n  setInterval(() => {}, 1000);\n}\n" % json.dumps(drawing))

        def nodes():
            listing = subprocess.run(["ps", "-Ao", "pid=,command="], capture_output=True, text=True).stdout
            return [int(line.split()[0]) for line in listing.splitlines() if line.strip().endswith(slow)]   # `node <the stand-in>`, not the run that names it

        def tidy():
            for pid in nodes():
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
        self.addCleanup(tidy)
        self.assertEqual(_render.RENDER_SECONDS, 180)
        before = self.snapshot()
        program = ("import os, signal, sys\nfor name in %r:\n    signal.signal(getattr(signal, name), signal.SIG_DFL)\nsys.path.insert(0, %r)\nimport brand_intake, _render\n"
                   "_render.HELPER = %r\nsys.exit(brand_intake.main(sys.argv[1:]))\n" % (tuple(n for n in _install.SIGNALS if hasattr(signal, n)), T.SCRIPTS, slow))
        for name in ("SIGTERM", "SIGINT"):
            with self.subTest(signal=name):
                if os.path.exists(drawing):
                    os.remove(drawing)
                scratch = tempfile.mkdtemp(dir=self.tmp.name)
                p = subprocess.Popen([sys.executable, "-c", program, "install", "--site", self.site, "--test-command", GREEN, "--json"] + list(self.logo()),
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=dict(os.environ, TMPDIR=scratch))
                end = time.time() + 60
                while not os.path.exists(drawing) and p.poll() is None and time.time() < end:
                    time.sleep(0.01)
                drawing_now = len(nodes())
                sent = time.time()
                p.send_signal(getattr(signal, name))
                try:
                    out, err = p.communicate(timeout=60)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.communicate()
                    self.fail("the run was still going a minute after the stop")
                took = time.time() - sent
                self.assertTrue(os.path.exists(drawing), "the stand-in was asked to draw: " + out + err)
                self.assertEqual(drawing_now, 1, "Node was drawing when the stop came")
                data = json.loads(out)
                self.assertEqual((p.returncode, err, data["status"], data["written"]), (2, "", "stopped", []), out + err)
                self.assertEqual(data["report"][0], "The run was stopped from outside (%s) before it had finished, and what it had started was stopped with it as far as this tool could find it." % name)
                self.assertIn("Nothing was written.", data["report"])
                self.assertLess(took, 30, "at once, not when the renderer's own limit of %d seconds is over" % _render.RENDER_SECONDS)
                end = time.time() + 5
                while nodes() and time.time() < end:
                    time.sleep(0.05)
                self.assertEqual(nodes(), [], "Node was stopped with the run")
                self.assertEqual(os.listdir(scratch), [], "the folder the icons are drawn in is gone")
                self.assertEqual(self.snapshot(), before)

    def test_a_stop_while_the_icons_are_drawn_or_just_after_a_folder_was_made_leaves_nothing_behind(self):
        before = self.snapshot()
        drawn = StoppedFromOutside.AT % ("_icons.build", "SIGTERM", "_icons.build")
        made = ("real = os.mkdir\ndef stopped_here(path, *args, **kwargs):\n    real(path, *args, **kwargs)\n    if os.path.basename(path) == 'brand-handoff':\n"
                "        os.kill(os.getpid(), signal.SIGTERM)\nos.mkdir = stopped_here\n")
        for moment, patch, said in (("while the icons are drawn", drawn, "Nothing was written."), ("just after brand-handoff was made", made, "Everything it had written was put back.")):
            with self.subTest(moment=moment):
                scratch = tempfile.mkdtemp(dir=self.tmp.name)
                r = self.drive(patch, *self.logo(), tmpdir=scratch)
                self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout + r.stderr)
                self.assertIn("stopped from outside (SIGTERM)", r.stdout)
                self.assertIn(said, r.stdout)
                self.assertEqual(os.listdir(scratch), [], "the folder the icons were drawn in is gone")
                self.assertEqual(self.snapshot(), before)
                self.assertFalse(self.exists("brand-handoff"))


# A stand-in for a test runner that starts a server in a session of its own (as Playwright starts the preview
# server: `detached: true`) and, like Playwright, stops it itself when it ends or is told to end. Arguments:
# how it behaves ("tidy" or "deaf"), the file it notes things in, how long its server sleeps (that length tells
# the server apart in `ps`), how long it runs itself, its exit status.
# A stand-in for the site's tests whose server, in a session of its own, does not end when it is told to. With
# "at-once" the server is started right away and the runner ends as soon as it is told to, without stopping it.
# With "when-told" the server is only started once the runner is told to end; the runner then stays for the
# seconds given, and goes without stopping it.
LEAVER = r'''
import os, signal, subprocess, sys, time
notes, when, stays = sys.argv[1], sys.argv[2], float(sys.argv[3])
DEAF = ("import os, signal, sys, time\nfor s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):\n    signal.signal(s, signal.SIG_IGN)\n"
        "open(sys.argv[1], 'a').write('server %d\\n' % os.getpid())\ntime.sleep(300)\n")
def server():
    subprocess.Popen([sys.executable, "-c", DEAF, notes], start_new_session=True)
def told(signum, _frame):
    server()
    time.sleep(stays)
    os._exit(1)
with open(notes, "a") as f:
    f.write("runner %d\n" % os.getpid())
if when == "at-once":
    server()
else:
    signal.signal(signal.SIGTERM, told)
time.sleep(300)
'''
RUNNER = r'''
import os, signal, subprocess, sys, time
how, notes, length, lasts, status = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), int(sys.argv[5])
server = subprocess.Popen(["sleep", length], start_new_session=True)
def note(text):
    with open(notes, "a") as f:
        f.write(text + "\n")
note("runner %d" % os.getpid())
note("server %d" % server.pid)
def stop_server():
    server.terminate()
    server.wait()
    note("the runner stopped its server")
def told(signum, _frame):
    note("the runner was told to end")
    stop_server()
    sys.exit(1)
signal.signal(signal.SIGTERM, signal.SIG_IGN if how == "deaf" else told)
time.sleep(lasts)
stop_server()
sys.exit(status)
'''


@POSIX
class WhatACommandStartedIsStopped(SiteCase):
    """Round 3: the site's tests are a command that starts other things. After a normal end, a timeout and a
    stop from outside, `ps` shows nothing the run started; what was started gets the chance to clear up after
    itself first; and a command that has ended is not waited for because something it left holds its output."""
    modules = False

    def setUp(self):
        super().setUp()
        self.brand_md()
        self.notes = os.path.join(self.tmp.name, "runner-notes")
        self.runner_file = os.path.join(self.tmp.name, "runner.py")
        with open(self.runner_file, "w", encoding="utf-8") as f:
            f.write(RUNNER)
        self.addCleanup(self.stop_noted)

    def noted(self):
        return T.read(self.notes).splitlines() if os.path.exists(self.notes) else []

    def pids(self, what):
        return [int(l.split()[1]) for l in self.noted() if l.startswith(what + " ")]

    def stop_noted(self):
        for pid in self.pids("runner") + self.pids("server"):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass

    def runner(self, how, length, lasts, status):
        return "'%s' '%s' %s '%s' %s %s %d" % (sys.executable, self.runner_file, how, self.notes, length.split()[1], lasts, status)

    def with_limits(self, call, timeout=None, grace=None):
        old = _install.TEST_TIMEOUT, _proc.GRACE
        _install.TEST_TIMEOUT, _proc.GRACE = timeout or old[0], grace or old[1]
        try:
            started = time.time()
            return call() + (time.time() - started,)
        finally:
            _install.TEST_TIMEOUT, _proc.GRACE = old

    def all_gone(self, running):
        self.assertTrue(self.none_left(running), "the server that was started in a session of its own is still running")
        for pid in self.pids("runner") + self.pids("server"):
            self.assertTrue(self.gone(pid), "process %d, which the run started, is still running" % pid)

    def test_a_command_that_has_ended_is_not_waited_for_because_something_it_left_running_holds_its_output(self):
        # `(sleep 30 &); exit 1`: the command is gone at once, and what it left has its output still open. Waiting
        # for the output to end waited for that: a green run that left a preview server took the whole timeout
        # and was then put back as "ran too long".
        for name, leaves in (("both its outputs", "(%s &);"), ("its output", "(%s 2>/dev/null &);"), ("its error output", "(%s >/dev/null &);"), ("neither", "(%s >/dev/null 2>&1 &);"),
                             ("both, as a job of the shell", "%s &")):
            for ending, code_wanted in (("exit 1", 1), ("exit 0", 0)):
                with self.subTest(holds=name, ending=ending):
                    for rel in ("src/styles/global.css",) + _install.OTHER_FILES:
                        self.put(rel, T.starter_file(rel))
                    before = self.snapshot()
                    sleep, running = self.sleeper()
                    code, out, took = self.with_limits(lambda: self.intake(command="echo started; %s %s" % (leaves % sleep, ending)), timeout=30)
                    self.assertEqual(code, code_wanted, out)
                    self.assertNotIn("were stopped", out, "it ended; nothing ran too long")
                    self.assertLess(took, 25, "the run waited for what the command left behind")
                    self.assertIn("With the install taken out again, the same tests still fail." if code_wanted else "Done. The site's own tests pass afterwards.", out)
                    self.assertTrue(self.none_left(running), "what the command left running is still running")
                    if code_wanted:
                        self.assertEqual(self.snapshot(), before)

    def test_what_a_command_printed_is_read_after_it_ended_and_what_it_left_running_adds_nothing_to_it(self):
        sleep, running = self.sleeper()
        started = time.time()
        code, out, err = _install._run("echo before; echo oops >&2; (%s; echo late) & echo after; exit 3" % sleep, self.site, 60, shell=True)
        self.assertEqual((code, out, err), (3, "before\nafter\n", "oops\n"))
        self.assertLess(time.time() - started, 45)
        self.assertTrue(self.none_left(running))
        code, out, err = _install._run("printf 'caf\\351\\n'; exit 0", self.site, 60, shell=True)
        self.assertEqual((code, out), (0, "caf" + chr(0xfffd) + "\n"), "bytes that are no UTF-8 are shown as that")
        sleep, running = self.sleeper()
        started = time.time()
        code, out, _err = _install._run("echo begun; " + sleep, self.site, 2, shell=True)
        self.assertEqual((code, out), (None, "begun\n"), "one that runs too long has no status, and what it printed until then is kept")
        self.assertTrue(self.none_left(running))
        self.assertEqual(subprocess.run(["ps", "-p", "1"], capture_output=True).returncode, 0, "`ps` can be asked here, as the stopping asks it")

    def test_a_runner_that_ends_by_itself_and_stops_its_own_server_leaves_nothing_and_is_not_disturbed(self):
        for status, code_wanted in ((0, 0), (1, 1)):
            with self.subTest(status=status):
                self.put("src/styles/global.css", T.starter_file("src/styles/global.css"))
                if os.path.exists(self.notes):
                    os.remove(self.notes)
                sleep, running = self.sleeper()
                code, out = self.intake(command=self.runner("tidy", sleep, 0.5, status))
                self.assertEqual(code, code_wanted, out)
                self.assertEqual(self.noted().count("the runner stopped its server"), 2 if status else 1, "each run of it ended in its own way")
                self.assertNotIn("the runner was told to end", self.noted())
                self.all_gone(running)

    def test_tests_that_run_too_long_are_told_to_end_before_they_are_killed_so_that_they_can_stop_what_they_started(self):
        # killed at once, Playwright cannot stop the preview server it started in a session of its own, and
        # that server keeps the site's port: the next `npm test` fails with "already used"
        before = self.snapshot()
        sleep, running = self.sleeper()
        code, out, took = self.with_limits(lambda: self.intake(command=self.runner("tidy", sleep, 300, 0)), timeout=3)
        self.assertEqual(code, 1, out)
        self.assertIn("were stopped", out)
        self.assertEqual(self.noted()[2:], ["the runner was told to end", "the runner stopped its server"], "it was asked first, and had the time to clear up")
        self.all_gone(running)
        self.assertEqual(self.snapshot(), before)
        self.assertLess(took, 60)

    def test_what_does_not_end_when_told_to_is_killed_after_the_grace_with_the_server_it_started_in_a_session_of_its_own(self):
        # the server left the command's group; it is reached as a descendant of the command, by its own number
        before = self.snapshot()
        sleep, running = self.sleeper()
        code, out, took = self.with_limits(lambda: self.intake(command=self.runner("deaf", sleep, 300, 0)), timeout=3, grace=2)
        self.assertEqual(code, 1, out)
        self.assertIn("were stopped", out)
        self.assertEqual(len(self.noted()), 2, "it neither ended nor stopped its server by itself")
        self.all_gone(running)
        self.assertEqual(self.snapshot(), before)
        self.assertGreaterEqual(took, 3 + 2, "it had its grace")

    def test_a_stop_from_outside_reaches_the_server_in_a_session_of_its_own_too_whether_the_runner_clears_up_or_not(self):
        before = self.snapshot()
        for how, said in (("tidy", ["the runner was told to end", "the runner stopped its server"]), ("deaf", [])):
            with self.subTest(how=how):
                if os.path.exists(self.notes):
                    os.remove(self.notes)
                sleep, running = self.sleeper()
                # the shell starts the runner, waits until it has noted its server, then has the intake stopped as from outside
                command = "%s & while [ ! -s '%s' ] || [ $(wc -l < '%s') -lt 2 ]; do sleep 0.1; done; kill -TERM $PPID; wait" % (self.runner(how, sleep, 300, 0), self.notes, self.notes)
                r = self.drive("_proc.GRACE = 2\n", command=command)
                self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout + r.stderr)
                self.assertIn("stopped from outside (SIGTERM)", r.stdout)
                self.assertIn("Everything it had written was put back.", r.stdout)
                self.assertEqual(self.noted()[2:], said)
                self.all_gone(running)
                self.assertEqual(self.snapshot(), before)

    def test_a_stop_in_the_instant_a_command_is_started_or_while_it_is_being_stopped_leaves_nothing_running(self):
        before = self.snapshot()
        started = ("real = _proc.subprocess.Popen\ndef stopped_here(*args, **kwargs):\n    p = real(*args, **kwargs)\n    if kwargs.get('shell'):\n"
                   "        os.kill(os.getpid(), signal.SIGTERM)\n    return p\n_proc.subprocess.Popen = stopped_here\n")
        stopping = ("real = _proc._listing\ndef stopped_here():\n    global sent\n    if not sent:\n        sent = True\n        os.kill(os.getpid(), signal.SIGTERM)\n"
                    "    return real()\nsent = False\n_proc._listing = stopped_here\n_install.regenerate_cards = lambda site: (False, 'left out of this test')\n")
        for moment, patch in (("the command is started", started), ("the command has ended and what it left is being stopped", stopping)):
            with self.subTest(moment=moment):
                sleep, running = self.sleeper()
                r = self.drive(patch, command="(%s &); exit 0" % sleep if "left" in moment else sleep)
                self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout + r.stderr)
                self.assertIn("stopped from outside (SIGTERM)", r.stdout)
                self.assertTrue(self.none_left(running), "the command, or what it left, is still running")
                self.assertEqual(self.snapshot(), before)

    # --- round 5 ---------------------------------------------------------------------------------------

    def leaver(self, when, stays=0):
        path = os.path.join(self.tmp.name, "leaver.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(LEAVER)
        return "'%s' '%s' '%s' %s %s" % (sys.executable, path, self.notes, when, stays)

    QUICK = "_proc.GRACE = 1\n_install.regenerate_cards = lambda site: (False, 'not made in this test')\n"   # (the cards are seconds of Node and Python; the stop comes after them either way)

    def test_ctrl_c_twice_as_a_terminal_sends_it_still_ends_a_server_in_a_session_of_its_own_that_does_not_end_when_told(self):
        # A terminal sends Ctrl-C to every process of the tool's group: the tool, and the `ps` that its stopping
        # runs. A second Ctrl-C a few milliseconds after the first ended that `ps`; the stopping took "no list"
        # for "ps cannot be asked", stopped the command's own group only, and the site's preview server (in a
        # session of its own) stayed, holding the site's port: with the real `npm test`, 3 times of 3. A second
        # one a third of a second later ended the `ps` of a later look, and the server was never killed.
        before = self.snapshot()
        for gap in (0.005, 0.03, 0.3, 0.55):
            with self.subTest(seconds_between_the_two=gap):
                if os.path.exists(self.notes):
                    os.remove(self.notes)
                p = self.begin("--json", patch=self.QUICK, command=self.leaver("at-once"), own_group=True)
                try:
                    self.assertTrue(self.until(lambda: self.pids("server"), p), "the stand-in never started its server")
                    for wait in (gap, 0):
                        try:
                            os.killpg(p.pid, signal.SIGINT)
                        except ProcessLookupError:
                            pass
                        time.sleep(wait)
                    out, err = p.communicate(timeout=120)
                finally:
                    if p.poll() is None:
                        os.killpg(p.pid, signal.SIGKILL)
                data = json.loads(out)
                self.assertEqual((p.returncode, err, data["status"], data.get("not_restored")), (2, "", "stopped", None), out + err)
                self.assertEqual(data["report"][:2], ["The run was stopped from outside (SIGINT) before it had finished, and what it had started was stopped with it as far as this tool could find it.",
                                                      "Everything it had written was put back."])
                self.assertEqual((len(self.pids("runner")), len(self.pids("server"))), (1, 1))
                for pid in self.pids("runner") + self.pids("server"):
                    self.assertTrue(self.gone(pid), "process %d, which the run started, is still running" % pid)
                self.assertEqual(self.snapshot(), before)

    def test_a_look_that_could_not_be_made_while_stopping_is_not_taken_for_nothing_being_left(self):
        # where one look at the processes fails (a `ps` that was ended), the command's own group being empty says
        # nothing of a server outside it that an earlier look showed: the stopping went on to "nothing is left"
        # and never killed it. It now looks again, and where it could not look at the end, the report says so.
        failing = ("real, looks = _proc._listing, []\ndef listing():\n    looks.append(1)\n    return None if %s else real()\n_proc._listing = listing\n")
        normal = "The run was stopped from outside (SIGTERM) before it had finished, and what it had started was stopped with it as far as this tool could find it."
        before = self.snapshot()
        # (the first looks belong to the two commands of the read-back; the stopping's own begin after them)
        for label, when, sentence, ends in (("the second look of the stopping", "len(looks) == stopping + 2", normal, True),
                                            ("every look after the first", "len(looks) > stopping + 1", None, None)):
            with self.subTest(failed=label):
                if os.path.exists(self.notes):
                    os.remove(self.notes)
                patch = self.QUICK + "stopping = None\n" + failing % ("stopping is not None and " + when) + "real_tests = _install.run_tests\ndef run_tests(site, command):\n    global stopping\n    stopping = len(looks)\n    return real_tests(site, command)\n_install.run_tests = run_tests\n"
                p = self.begin("--json", patch=patch, command=self.leaver("at-once"))
                try:
                    self.assertTrue(self.until(lambda: self.pids("server"), p), "the stand-in never started its server")
                    p.send_signal(signal.SIGTERM)
                    out, err = p.communicate(timeout=120)
                finally:
                    if p.poll() is None:
                        p.kill()
                data = json.loads(out)
                self.assertEqual((p.returncode, err, data["status"]), (2, "", "stopped"), out + err)
                self.assertEqual(self.snapshot(), before)
                self.assertTrue(self.gone(self.pids("runner")[0]))
                if ends:
                    self.assertEqual(data["report"][0], sentence)
                    self.assertTrue(self.gone(self.pids("server")[0]), "the server outside the group, which the first look had shown, is still running")
                else:   # it could not look at the end: it says what it stopped and what it cannot know, and claims nothing of the server
                    self.assertIn("This tool could not read the list of running processes: it stopped the command it had started, with that command's own group, and cannot say", data["report"][0])

    def test_a_server_that_is_started_while_its_starter_is_being_stopped_is_found_at_the_next_look_and_stopped_too(self):
        # what descends from the command was noted once, when the stopping began: a child started in a session of
        # its own after that, by a starter that was just being told to end, was in neither the group nor the
        # note, and stayed (3 of 360 stops at random moments). It is looked for again at every look.
        before = self.snapshot()
        for name in ("SIGTERM", "SIGINT"):
            with self.subTest(signal=name):
                if os.path.exists(self.notes):
                    os.remove(self.notes)
                p = self.begin("--json", patch=self.QUICK, command=self.leaver("when-told", 0.8))
                try:
                    self.assertTrue(self.until(lambda: self.pids("runner"), p), "the stand-in never started")
                    self.assertEqual(self.pids("server"), [], "no server yet: it is started when the runner is told to end")
                    p.send_signal(getattr(signal, name))
                    out, err = p.communicate(timeout=120)
                finally:
                    if p.poll() is None:
                        p.kill()
                data = json.loads(out)
                self.assertEqual((p.returncode, err, data["status"]), (2, "", "stopped"), out + err)
                self.assertEqual(len(self.pids("server")), 1, "the server was started during the stopping")
                for pid in self.pids("runner") + self.pids("server"):
                    self.assertTrue(self.gone(pid), "process %d, which the run started, is still running" % pid)
                self.assertEqual(self.snapshot(), before)

    def test_a_second_run_of_the_tests_that_writes_to_the_site_as_the_first_did_is_put_back_too(self):
        # the tests are run a second time after everything was put back; what THAT run does to the share cards
        # (or to any file the first run was put back from) must not stay under "everything was put back"
        before = self.snapshot()
        code, out = self.intake("--json", command="echo x >> public/images/og/default.jpg; echo y > public/images/og/extra.jpg; echo z >> src/config.ts; exit 1")
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["cards"], data.get("not_restored")), (1, "tests-failed", "restored", None), out)
        self.assertIn("With the install taken out again, the same tests still fail.", data["report"])
        self.assertEqual(self.snapshot(), before)

    def test_tests_that_ran_too_long_are_said_not_to_have_been_run_again_also_when_not_everything_could_be_put_back(self):
        real = _site.Journal._put
        sleep, running = self.sleeper()

        def go():
            # the manifest is written (the journal has written nothing yet), then the putting back of it is refused
            first = []

            def once(journal, path, data, mode=0o644):
                if path.endswith("manifest.webmanifest") and first:
                    raise PermissionError(13, "Permission denied", path)
                if path.endswith("manifest.webmanifest"):
                    first.append(path)
                return real(journal, path, data, mode)
            _site.Journal._put = once
            try:
                return self.intake("--json", command=sleep)
            finally:
                _site.Journal._put = real
        code, out, _took = self.with_limits(go, timeout=2)
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["tests"], data.get("tests_timed_out")), (1, "rollback-incomplete", "timed-out", True), out)
        self.assertEqual([l["file"] for l in data["not_restored"]], ["public/manifest.webmanifest"])
        report = "\n".join(data["report"])
        self.assertIn("They were not run a second time with the install taken out again", report)
        self.assertIn("NOT as they were", report)
        self.assertNotIn("everything was put back", report)
        self.assertTrue(self.none_left(running))
        self.put("public/manifest.webmanifest", T.starter_file("public/manifest.webmanifest"))

    def test_what_goes_into_a_report_from_the_tests_output_is_text_without_a_terminals_colour_codes_or_other_control_characters(self):
        esc, arrow, dash = chr(27), chr(0x203a), chr(0x2014)
        coloured = "printf '\\033[31m  1) [chromium] \\342\\200\\272 tests/a.spec.ts:8:5 \\342\\200\\272 a11y \\342\\200\\224 / [dark]\\033[39m \\033[2K\\r\\n'; exit 1"
        code, out = self.intake("--json", command=coloured)
        data = json.loads(out)
        self.assertEqual((code, data["failing"]), (1, ["tests/a.spec.ts:8:5 %s a11y %s / [dark]" % (arrow, dash)]), "the failing check is read past the colour it is printed in")
        unnamed = "printf '\\033[1m\\033[31mFAIL\\033[0m src/a.test.js\\007\\n\\033]0;title\\007  expected 1,\\010 got 2\\033[K\\n\\0\\n'; exit 1"
        code, out = self.intake("--json", command=unnamed)
        data = json.loads(out)
        self.assertEqual((code, data["output_tail"]), (1, ["FAIL src/a.test.js", "expected 1, got 2"]))
        for line in data["report"] + data["output_tail"]:
            self.assertFalse([c for c in line if ord(c) < 32 and c != "\t" or 127 <= ord(c) < 160], repr(line))
        self.assertNotIn(esc, out)
        text = self.intake(command=unnamed)[1]
        self.assertFalse([c for c in text if ord(c) < 32 and c not in "\t\n" or 127 <= ord(c) < 160], repr(text))

    def test_tests_that_ran_too_long_end_with_a_status_of_their_own_and_what_had_failed_by_then_is_in_the_words_too(self):
        # a timed-out run ended as "tests-failed", and the checks that had failed before the hang were in the
        # JSON alone
        names = ["tests/a11y.spec.ts:8:5 \u203a a11y \u2014 / [dark]", "tests/seo.spec.ts:20:3 \u203a theme colour"]
        before = self.snapshot()
        sleep, running = self.sleeper()
        code, out, _took = self.with_limits(lambda: self.intake("--json", command=RED.replace("; exit 1", "; " + sleep)), timeout=2)
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["tests"], data.get("tests_timed_out"), data["failing"]), (1, "tests-timed-out", "timed-out", True, names), out)
        self.assertEqual(data["report"][1], "Before they were stopped, these checks had failed: " + "; ".join(names))
        self.assertNotIn("The failing check", "\n".join(data["report"]))
        self.assertTrue(self.none_left(running))
        self.assertEqual(self.snapshot(), before)
        sleep, running = self.sleeper()
        one = RED.split("\\n")[0] + "\\n'; " + sleep
        code, out, _took = self.with_limits(lambda: self.intake(command=one), timeout=2)
        self.assertEqual(code, 1, out)
        self.assertIn("\nBefore they were stopped, this check had failed: %s\n" % names[0], out)
        self.assertTrue(self.none_left(running))
        # red tests that ended by themselves keep the status they had
        data = json.loads(self.intake("--json", command=RED)[1])
        self.assertEqual((data["status"], data["tests"], data.get("tests_timed_out"), data["failing"]), ("tests-failed", "failed", None, names))
        self.assertEqual(self.snapshot(), before)

    @POSIX
    def test_what_is_being_stopped_is_looked_at_four_times_a_second_while_it_is_given_time_to_end(self):
        # every look runs `ps`: twenty of them a second, through both waits, was more than the question needs
        self.assertEqual(_proc.POLL, 0.25)
        looks, real = [], _proc._listing

        def counted():
            looks.append(time.monotonic())
            return real()
        sleep, running = self.sleeper()
        _proc._listing = counted
        try:
            # a command that does not end when it is told to: it is waited for through the whole grace, then killed
            code, out, _took = self.with_limits(lambda: self.intake(command="trap '' TERM; " + sleep + "; true"), timeout=1, grace=2)
        finally:
            _proc._listing = real
        self.assertEqual(code, 1, out)
        self.assertTrue(self.none_left(running))
        stopping = [t for t in looks if t - looks[-1] > -4.5]   # the looks of the last stop: one before it, eight or so in the grace, one or two after the kill
        self.assertLessEqual(len(stopping), 14, "about four looks a second")
        self.assertGreaterEqual(len(stopping), 6)
        gaps = sorted(b - a for a, b in zip(stopping, stopping[1:]))
        self.assertGreaterEqual(gaps[len(gaps) // 2], 0.2, "and a quarter of a second between two of them")

@POSIX
class WhatStandsInTheSite(SiteCase):
    """Round 3: every planned path, and what stands above it, is looked at before anything is opened or
    written; what a run leaves when it is taken back is exactly what was there, also on a site that had no
    folder for its images; and a dry run refuses whatever the real run would refuse."""

    WHITE = rects((4, 4, 24, 24, "#ffffff"))

    def logo(self, *more):
        return ("--input", self.package()) + LOGO_ARGS + more

    def command_line(self, *extra, command=GREEN, timeout=120):
        """The command line as a process of its own with a time limit: for runs that once waited for ever."""
        self.brand_md()
        program = "import sys\nsys.path.insert(0, %r)\nimport brand_intake\nsys.exit(brand_intake.main(sys.argv[1:]))\n" % T.SCRIPTS
        try:
            r = subprocess.run([sys.executable, "-c", program, "install", "--site", self.site, "--test-command", command] + list(extra),
                               capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        except subprocess.TimeoutExpired:
            self.fail("the run did not end within %d seconds: it waits on something it opened" % timeout)
        return r.returncode, r.stdout + r.stderr

    def test_a_logo_run_on_a_site_without_an_images_folder_is_taken_back_whole_and_says_so(self):
        # the run writes public/images/logo.png and the generator makes public/images/og beside it. Putting the
        # cards' folder back tried to take public/images away while the logo was still in it, and counted that
        # as "not put back" although the tree ended up as it was.
        T.require_pillow(self)
        shutil.rmtree(self.p("public/images"))
        self.brand_md()
        before = self.snapshot()
        code, out = self.intake(*self.logo("--with-colours", "--json"), command=RED)
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["cards"], data.get("not_restored")), (1, "tests-failed", "restored", None), "\n".join(data["report"]))
        self.assertIn("The site's own tests failed after the install, so everything was put back (every file, the share cards included).", data["report"])
        self.assertEqual(self.snapshot(), before)
        text_code, text = self.intake(*self.logo("--with-colours"), command=RED)
        self.assertEqual(text_code, 1)
        self.assertNotIn("Directory not empty", text)
        self.assertNotIn("NOT as they were", text)
        self.assertEqual(self.snapshot(), before)

    def test_a_generator_that_fails_on_a_site_without_an_images_folder_does_not_take_a_good_install_back(self):
        shutil.rmtree(self.p("public/images"))
        self.brand_md()
        gen = self.read("scripts/generate_og_cards.py")
        for name, fails in (("after it made the cards' folder", "def main():\n    OUT.mkdir(parents=True, exist_ok=True)\n    (OUT / 'default.jpg').write_bytes(b'half way')\n    raise SystemExit('simulated: a later card failed')\n"),
                            ("before it made anything", "def main():\n    raise SystemExit('simulated: nothing was made')\n")):
            with self.subTest(name=name):
                shutil.rmtree(self.site)
                T.make_starter_site(self.site, with_modules=self.modules)
                shutil.rmtree(self.p("public/images"))
                self.brand_md()
                self.put("scripts/generate_og_cards.py", gen.replace("def main():\n", fails, 1))
                (dry_code, dry), (code, out) = self.both_runs(*self.logo("--with-colours", "--json"))
                data = json.loads(out)
                self.assertEqual((dry_code, code, data["status"], data["cards"], data["tests"]), (0, 0, "done", "failed", "passed"), "\n".join(data["report"]))
                self.assertEqual(json.loads(dry)["written"], data["written"])
                self.assertEqual(sorted(os.listdir(self.p("public/images"))), ["logo.png"], "the logo is in; the folder the generator made for the cards is gone again")
                self.assertIn("public/images/logo.png", data["written"])
                self.assertNotIn("not_restored", data)

    def test_cards_that_could_not_be_put_back_after_the_generator_failed_are_said_to_be_that_in_the_json_too(self):
        T.require_pillow(self)   # without it the generator stops before it writes anything
        self.brand_md()
        gen = self.read("scripts/generate_og_cards.py")
        self.put("scripts/generate_og_cards.py", gen.replace("def main():\n", "def main():\n    (OUT / 'default.jpg').write_bytes(b'half way')\n    raise SystemExit('simulated: a later card failed')\n", 1))
        real = _site.Journal._put

        def refusing(journal, path, data, mode=0o644):
            if path.endswith(os.path.join("og", "default.jpg")):
                raise PermissionError(13, "Permission denied", path)
            return real(journal, path, data, mode)
        _site.Journal._put = refusing
        try:
            code, out = self.intake("--json")
        finally:
            _site.Journal._put = real
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["code"], data["cards"]), (2, "rollback-incomplete", "cards-not-restored", "not-restored"), out)
        self.assertEqual(data["cards_why"], "simulated: a later card failed")

    def test_a_pipe_or_a_link_the_tests_left_where_a_file_was_is_taken_away_and_the_file_put_back_and_the_run_ends(self):
        # a saved card that the test command replaced by a pipe was opened for reading when the cards were put
        # back, and the run waited there for ever; a dangling link where a new file had been was left in place
        # under "everything was put back"
        self.brand_md()
        before = self.snapshot()
        wrecks = (("a pipe where a card was", "rm public/images/og/default.jpg; mkfifo public/images/og/default.jpg"),
                  ("a pipe where a file of the run was", "rm public/manifest.webmanifest; mkfifo public/manifest.webmanifest"),
                  ("a dangling link where a file of the run was", "rm src/config.ts; ln -s nowhere src/config.ts"),
                  ("a link to a file where a card was", "rm public/images/og/default.jpg; ln -s ../../manifest.webmanifest public/images/og/default.jpg"),
                  ("a dangling link where a new card was made", "ln -s nowhere public/images/og/new.jpg"))
        once = os.path.join(self.tmp.name, "wrecked-once")
        for name, wreck in wrecks:
            with self.subTest(name=name):
                if os.path.exists(once):
                    os.remove(once)
                code, out = self.command_line("--json", command="if [ -e '%s' ]; then exit 1; fi; touch '%s'; %s; exit 1" % (once, once, wreck))
                data = json.loads(out)
                self.assertEqual((code, data["status"], data.get("not_restored")), (1, "tests-failed", None), "\n".join(data["report"]))
                self.assertEqual(self.links(), {})
                self.assertEqual(self.snapshot(), before)

    def test_a_file_where_the_folder_for_the_images_would_be_is_refused_by_the_dry_run_as_by_the_real_one(self):
        # the cards' folder looked merely absent, the dry run passed, and the real run failed in the generator
        shutil.rmtree(self.p("public/images"))
        self.put("public/images", b"a file where the folder would go")
        self.brand_md()
        before = self.snapshot()
        for code, out in self.both_runs():
            self.assertEqual(code, 2, out)
            self.assertIn("public/images/og cannot be made: public/images is a file, not a folder.", out)
            self.assertIn("move the file away, then run this again", out)
            self.assertIn("Nothing was written", out)
            self.assertEqual(self.snapshot(), before)
        os.remove(self.p("public/images"))   # what it says to do, done
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code), (0, 0), out)
        self.assertEqual(json.loads(dry)["written"], json.loads(out)["written"])

    def test_a_pipe_at_a_path_the_run_would_read_or_write_is_refused_by_name_and_never_opened(self):
        master = _install.MARK.encode("utf-8") + _svg.clean_svg(T.real_svg()).text.encode("utf-8")
        cases = (("the installed logo, on a run about colours", "public/favicon.svg", (), "public/favicon.svg is neither a file nor a folder"),
                 ("the installed logo, asked for outright", "public/favicon.svg", ("--with-logo", "--with-colours"), "public/favicon.svg is neither a file nor a folder"),
                 ("an icon it would replace", "public/favicon.ico", self.logo("--with-colours", "--replace-icons"), "public/favicon.ico is neither a file nor a folder"),
                 ("the logo's picture", "public/images/logo.png", self.logo("--with-colours"), "public/images/logo.png is neither a file nor a folder"),
                 ("the preview sheet of an earlier run", "brand-handoff/preview.png", self.logo("--with-colours"), "brand-handoff/preview.png is neither a file nor a folder"),
                 ("the package kept from an earlier run", "brand-handoff/logo.zip", self.logo("--with-colours"), "brand-handoff/logo.zip is neither a file nor a folder"),
                 ("where the folder for the package would be", "brand-handoff", self.logo("--with-colours"), "brand-handoff is not a folder"))
        for name, rel, args, said in cases:
            with self.subTest(name=name):
                shutil.rmtree(self.site)
                T.make_starter_site(self.site, with_modules=self.modules)
                os.makedirs(os.path.dirname(self.p(rel)), exist_ok=True)
                os.mkfifo(self.p(rel))
                for extra in (("--dry-run",), ()):
                    code, out = self.command_line(*args, *extra)
                    self.assertEqual(code, 2, out)
                    self.assertIn(said, out)
                    self.assertIn("Nothing was written.", out)
                    self.assertTrue(stat.S_ISFIFO(os.lstat(self.p(rel)).st_mode), "it is left where it was")
                    self.assertEqual(sorted(n for n in os.listdir(self.p("public")) if n not in ("favicon.svg", "favicon.ico")), sorted(n for n in os.listdir(os.path.join(T.STARTER, "public"))))
                os.remove(self.p(rel))   # what the refusal says to do: taken out of the site
                if "favicon.svg" in rel:
                    self.put("public/favicon.svg", master)
                code, out = self.command_line(*args, "--accept-colours", "--accept-low-contrast", "both")
                self.assertEqual(code, 0, out)

    def test_a_cards_folder_that_holds_more_than_is_kept_to_put_it_back_is_refused_by_name_before_anything_is_written(self):
        self.brand_md()
        self.put("public/images/og/film.mov", b"x" * 300000)
        before = self.snapshot()
        old = _site.MAX_KEPT
        _site.MAX_KEPT = 250000
        try:
            for code, out in self.both_runs():
                self.assertEqual(code, 2, out)
                self.assertIn("public/images/og holds more than 0 MB, more than this tool keeps of a folder so that it can put it back", out)
                self.assertIn("the largest file it came to is public/images/og/film.mov", out)
                self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)
            os.rename(self.p("public/images/og/film.mov"), os.path.join(self.tmp.name, "film.mov"))   # what it says to do, done
            self.assertEqual([code for code, _out in self.both_runs()], [0, 0])
        finally:
            _site.MAX_KEPT = old

    @unittest.skipUnless(sys.platform == "darwin" and shutil.which("chflags"), "the lock that macOS shows in what stat returns (chflags uchg)")
    def test_a_locked_file_or_folder_is_refused_by_the_dry_run_as_by_the_real_one_naming_the_planned_file(self):
        self.brand_md()
        for rel, said in (("public/manifest.webmanifest", "public/manifest.webmanifest cannot be written: the file is locked against change."),
                          ("src", "src/config.ts cannot be written"), ("public/images/og", "public/images/og is locked against change."),
                          ("public/images/og/default.jpg", "public/images/og/default.jpg is locked against change.")):
            with self.subTest(rel=rel):
                self.put("src/styles/global.css", T.starter_file("src/styles/global.css"))
                before = self.snapshot()
                subprocess.run(["chflags", "uchg", self.p(rel)], check=True)
                self.addCleanup(subprocess.run, ["chflags", "nouchg", self.p(rel)], capture_output=True)
                try:
                    runs = self.both_runs()
                finally:
                    subprocess.run(["chflags", "nouchg", self.p(rel)], check=True)
                for code, out in runs:
                    self.assertEqual(code, 2, out)
                    self.assertIn(said, out)
                    self.assertNotIn(".write-", out, "the temporary file beside it is not what is named")
                    self.assertIn("Nothing was written", out)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(self.intake("--dry-run")[0], 0, "unlocked, as the refusal says, it goes through")


    @POSIX
    def test_a_folder_the_run_made_and_could_not_take_away_again_is_named_as_not_put_back(self):
        # the site's tests closed the site's folder to writing and failed: the new brand-handoff/ could be
        # emptied and not removed, and was left without a word under "Everything else it had written was put back"
        self.not_as_root()
        self.brand_md()
        self.addCleanup(lambda: os.chmod(self.site, 0o755))
        code, out = self.intake(*self.logo("--with-colours", "--json"), command="chmod 555 .; exit 1")
        os.chmod(self.site, 0o755)
        data = json.loads(out)
        self.assertEqual((code, data["status"]), (1, "rollback-incomplete"), out)
        self.assertIn("brand-handoff", [l["file"] for l in data["not_restored"]])
        self.assertEqual(os.listdir(self.p("brand-handoff")), [], "what the run wrote into it is gone; the folder is what is left, and it is named")
        report = "\n".join(data["report"])
        self.assertIn("Not everything could be put back. These are NOT as they were before this run", report)
        self.assertRegex(report, r"\n  brand-handoff \(.+\)\n")
        self.assertNotIn("so everything was put back", report)

    def test_a_folder_or_a_link_where_a_file_or_a_folder_of_the_run_must_stand_is_refused_with_what_to_do_about_it(self):
        elsewhere = os.path.join(self.tmp.name, "elsewhere")
        os.makedirs(elsewhere)
        way_out = " is a link, and nothing is written through a link%s. Put the file or folder itself where the link is (or move the link away), then run this again."

        def gitignore_folder():
            os.remove(self.p(".gitignore"))
            os.mkdir(self.p(".gitignore"))

        def handoff_link():
            os.symlink(elsewhere, self.p("brand-handoff"))

        def cards_link():
            shutil.move(self.p("public/images/og"), os.path.join(elsewhere, "og"))
            os.symlink(os.path.join(elsewhere, "og"), self.p("public/images/og"))
        for name, make, said in ((".gitignore is a folder", gitignore_folder, ".gitignore is a folder, so a file of that name cannot be written. Move the folder away, then run this again."),
                                 ("brand-handoff is a link", handoff_link, "brand-handoff" + way_out % " (brand-handoff/logo.zip is below it)"),   # the link is the path that is named, not the file that would go below it
                                 ("the share cards' folder is a link", cards_link, "public/images/og" + way_out % "")):
            with self.subTest(name=name):
                shutil.rmtree(self.site)
                T.make_starter_site(self.site, with_modules=self.modules)
                self.brand_md()
                make()
                before, links = self.snapshot(), self.links()
                for code, out in self.both_runs(*self.logo("--with-colours")):
                    self.assertEqual(code, 2, out)
                    self.assertTrue(out.startswith(said), out)
                    self.assertIn("Nothing was written.", out.splitlines())
                self.assertEqual((self.snapshot(), self.links()), (before, links))


class WhatIsAskedAndWhen(SiteCase):
    """Round 3: the question whether the colours should change too is asked on every run that she asked the
    logo of, after what she handed over was read; and a later run about colours leaves the logo's files, and
    its questions, alone unless the background the app icons sit on would change."""

    def logo(self, *more):
        return ("--input", self.package()) + LOGO_ARGS + more

    def installed(self, *more):
        """A site with the bakery's palette and logo in."""
        self.brand_md()
        code, out = self.intake(*self.logo("--with-colours", *more))
        self.assertEqual(code, 0, out)

    ICONS = ("public/favicon.svg", "public/favicon.ico", "public/apple-touch-icon.png", "public/icon-192.png", "public/icon-512.png",
             "public/icon-maskable-512.png", "public/images/logo.png")

    def icons(self):
        return {rel: self.bytes(rel) for rel in self.ICONS}

    def sits_on(self):
        import _png
        return "#%02x%02x%02x" % _png.at(_png.decode(self.bytes("public/icon-maskable-512.png")), 0, 0)[:3]

    # --- the question about the colours ------------------------------------------------------------

    def test_asking_for_the_icons_again_without_a_file_asks_about_the_colours_just_as_a_file_does(self):
        # --with-logo (no --input) went past the question: a dry run planned to overwrite a theme colour she had set by hand
        self.installed()
        for rel, old, new, line in (("src/config.ts", "themeColor: '#b4531a'", "themeColor: '#123456'", "src/config.ts, themeColor: #123456 becomes #b4531a"),
                                    ("public/manifest.webmanifest", '"background_color": "#fff8ee"', '"background_color": "#654321"', "public/manifest.webmanifest, background_color: #654321 becomes #fff8ee"),
                                    ("scripts/generate_og_cards.py", "BG_TOP = (42, 31, 23)", "BG_TOP = (1, 2, 3)", "scripts/generate_og_cards.py, BG_TOP: #010203 becomes #2a1f17")):
            with self.subTest(rel=rel):
                settled = self.read(rel)
                self.assertEqual(settled.count(old), 1)
                self.put(rel, settled.replace(old, new))
                before = self.snapshot()
                for how in (("--with-logo",), self.logo()):
                    for code, out in self.both_runs(*how, "--accept-colours", "--accept-low-contrast", "both"):
                        self.assertEqual(code, 3, out)
                        self.assertIn("    * " + line, out.splitlines())
                        self.assertIn("--with-colours", out)
                        self.assertIn("--keep-colours", out)
                        self.assertIn("Nothing was written", out)
                        self.assertEqual(self.snapshot(), before)
                data = json.loads(self.intake("--with-logo", "--json", "--dry-run")[1])
                self.assertEqual(([k["code"] for k in data["asks"]], data["asks"][0]["options"], data["changes"], data["written"]), (["colours-too"], [line], [line], []))
                code, out = self.intake("--with-logo", "--keep-colours", "--accept-colours", "--accept-low-contrast", "both")
                self.assertEqual(code, 0, out)
                self.assertIn(new, self.read(rel), "kept, as she said")
                code, out = self.intake("--with-logo", "--with-colours", "--accept-colours", "--accept-low-contrast", "both")
                self.assertEqual(code, 0, out)
                self.assertEqual(self.read(rel), settled, "set, as she said")

    def test_what_she_handed_over_is_read_and_checked_before_she_is_asked_about_the_colours(self):
        # asked first, she answered --with-colours or --keep-colours only to be told then that nothing had arrived
        self.brand_md()
        before = self.snapshot()
        nothing = os.path.join(self.pack, "not-there.zip")
        page = os.path.join(self.pack, "saved.svg")
        with open(page, "wb") as f:
            f.write(b"<!doctype html><html><body><svg xmlns='http://www.w3.org/2000/svg'/></body></html>")
        broken = self.package("broken.zip", b"PK\x03\x04 not a zip at all")
        empty = os.path.join(self.pack, "empty")
        os.makedirs(empty)
        for name, given, status, said in (("a path that holds nothing", nothing, 2, "Nothing arrived at that path"), ("a web page saved as .svg", page, 2, None),
                                          ("a file that is no zip", broken, 2, None), ("a folder that holds no package", empty, 2, "holds no .zip or .svg file")):
            with self.subTest(name=name):
                for code, out in self.both_runs("--input", given):
                    self.assertEqual(code, status, out)
                    self.assertNotIn("Should it? Run this again with --with-colours", out, "the question was asked before the input was looked at")
                    if said:
                        self.assertIn(said, out)
                    self.assertEqual(self.snapshot(), before)
        two = os.path.join(self.pack, "two")
        os.makedirs(two)
        for n in ("a.zip", "b.zip"):
            with open(os.path.join(two, n), "wb") as f:
                f.write(T.real_zip_bytes())
        data = json.loads(self.intake("--input", two, "--json")[1])
        self.assertEqual([k["code"] for k in data["asks"]], ["which-package"], "which file it is comes before whether the colours change")
        data = json.loads(self.intake("--input", self.package(), "--json")[1])
        self.assertEqual([k["code"] for k in data["asks"]], ["which-file"], "which drawing of the zip it is comes first too")
        data = json.loads(self.intake(*self.logo("--json"))[1])
        self.assertEqual([k["code"] for k in data["asks"]], ["colours-too"], "and with a file that will do, the question is asked")
        self.assertEqual(self.snapshot(), before)

    # --- a rule outside the three colour blocks that sets one of the colours ---------------------------

    def test_a_rule_outside_the_three_blocks_that_sets_one_of_the_colours_is_refused_before_anything_is_written_whatever_the_run_is_about(self):
        # the page may then show another colour than the block's: the palette would go in and not show (a run about
        # colours), or the logo would be checked against a background the page does not have (a run about the logo)
        starter = T.starter_file("src/styles/global.css")
        for name, rule, said in (("on body", "\nbody {\n  --bg: #eeeeee;\n}\n", "--bg is also set in the rule `body { ... }`, outside the three blocks that hold the palette"),
                                 ("on :root inside another at-rule", "\n@media print {\n  :root {\n    --ink: #000000;\n  }\n}\n", "--ink is also set in the rule `@media print { :root { ... } }`"),
                                 ("on :root with a class", "\n:root.dark {\n  --surface: #010101;\n}\n", "--surface is also set in the rule `:root.dark { ... }`")):
            for run_name, args, brand in (("the colours", (), True), ("a logo alone", self.logo(), False), ("a logo, the colours kept", self.logo("--keep-colours"), True),
                                          ("a logo and the colours", self.logo("--with-colours"), True), ("a logo, the question about the colours not yet answered", self.logo(), True)):
                with self.subTest(rule=name, run=run_name):
                    shutil.rmtree(self.site)
                    T.make_starter_site(self.site, with_modules=self.modules)
                    self.put("src/styles/global.css", starter + rule)
                    if brand:
                        self.brand_md()
                    before = self.snapshot()
                    for code, out in self.both_runs(*args, brand=brand):
                        self.assertEqual(code, 2, out)
                        self.assertIn(said, out)
                        self.assertIn("Nothing was written.", out.splitlines())
                        self.assertEqual(self.snapshot(), before)
                    data = json.loads(self.intake(*args, "--json", brand=brand)[1])
                    self.assertEqual((data["status"], data["written"], data["code"]), ("refused", [], "css-layout" if "--keep-colours" not in args and brand else "site-colours-unread"))
                    self.put("src/styles/global.css", starter)   # what the refusal says to do: the line taken out
                    (dry_code, dry), (code, out) = self.both_runs(*args, brand=brand)
                    self.assertEqual((dry_code, code), (3, 3) if run_name.endswith("not yet answered") else (0, 0), out)
        self.assertEqual(_install._css_problems(type("Css", (), {"problems": [(None, None, "A sentence of its own."), (None, "--bg", "is set elsewhere"), ("light", "--bg", "is odd")]})()),
                         ["A sentence of its own.", "--bg in a rule outside the three colour blocks: is set elsewhere", "--bg in the :root block: is odd"],
                         "one that is about no block of the three is said without a block being looked up for it")

    # --- the tool's own favicon, and the icons drawn from it ------------------------------------------

    def test_a_run_about_colours_draws_the_icons_again_from_its_own_favicon_under_another_primary_and_other_backgrounds(self):
        # the file is known as this tool's own by cleaning it again and comparing: that must not depend on the
        # palette the run has, or the promise in the file's first line ("drawn again from this file") fails silently
        self.installed()
        favicon, icons = self.bytes("public/favicon.svg"), self.icons()
        self.assertEqual(self.sits_on(), "#fff8ee")
        light = dict(T.BAKERY_LIGHT, bg="#fdf6ff", bg_soft="#f6ecfa", accent="#7a2a8f", link="#6a2380")
        dark = dict(T.BAKERY_DARK, bg="#150d1a", bg_soft="#1d1324", surface="#261a2e")
        other = ("# Brand\n\n### Brand (fixed, theme-independent)\n| Token | Hex |\n|---|---|\n| Primary | `#7a2a8f` |\n\n### Light theme\n" + table([(l, light[k]) for k, l in LABELS])
                 + "\n### Dark theme\n" + table([(l, dark[k]) for k, l in LABELS]))
        self.brand_md(other)
        (dry_code, dry), (code, out) = self.both_runs("--json", "--accept-colours", "--accept-low-contrast", "both", "--replace-icons")
        data = json.loads(out)
        self.assertEqual((dry_code, code), (0, 0), "\n".join(data["report"]))
        self.assertEqual(json.loads(dry)["written"], data["written"])
        for note in data["notes"]:
            self.assertNotIn("the icons were left as they are", note)
            self.assertNotIn("is not a file this tool wrote", note)
            self.assertNotIn("is not as this tool wrote it", note)
        self.assertEqual(self.bytes("public/favicon.svg"), favicon, "the master itself is as it was")
        self.assertEqual(self.sits_on(), "#fdf6ff", "the app icons sit on the new background")
        self.assertIn("public/icon-maskable-512.png", data["written"])
        self.assertNotEqual(self.icons()["public/apple-touch-icon.png"], icons["public/apple-touch-icon.png"])
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).brand, "#7a2a8f")

    def test_a_later_run_about_colours_leaves_the_logos_files_and_its_questions_alone_while_the_background_under_the_icons_stays(self):
        # the mark was accepted once (a colour outside the palette, low contrast on one theme): a run that
        # changes no colour, or only colours the icons do not sit on, has nothing to ask about it again
        self.installed()
        icons, before = self.icons(), self.snapshot()
        self.assertEqual(json.loads(self.intake(*self.logo("--with-colours", "--json", "--dry-run", "--accept-low-contrast", ""))[1])["status"], "needs-decision",
                         "this mark is one that questions are asked about")
        for name, md in (("nothing changed", BAKERY_BRAND_MD), ("a text colour changed", BAKERY_BRAND_MD.replace("| Accent | `#e2874a` |", "| Accent | `#d47c44` |")),
                         ("the dark background changed, which the icons do not sit on", BAKERY_BRAND_MD.replace("| Background | `#1a120d` |", "| Background | `#1b130e` |"))):
            with self.subTest(name=name):
                self.brand_md(md)
                (dry_code, dry), (code, out) = self.both_runs("--json")
                data = json.loads(out)
                self.assertEqual((dry_code, code, data["status"]), (0, 0, "done"), "\n".join(data["report"]))
                self.assertNotIn("asks", data)
                self.assertEqual([w for w in data["written"] + json.loads(dry)["written"] if w.startswith(("public/favicon", "public/icon", "public/apple", "public/images/logo", "brand-handoff"))], [])
                self.assertEqual(self.icons(), icons, "not a byte of the logo's files")
                self.assertEqual([n for n in data["notes"] if "icons" in n or "emblem" in n or "one-colour" in n], [])
        self.assertNotEqual(self.snapshot(), before, "the colours did go in")
        # the background they sit on changes: now they are drawn again, and the questions are due
        self.brand_md(BAKERY_BRAND_MD.replace("| Background | `#fff8ee` |", "| Background | `#fffdf7` |"))
        still = self.snapshot()
        for code, out in self.both_runs("--json"):
            data = json.loads(out)
            self.assertEqual((code, data["status"]), (3, "needs-decision"), "\n".join(data["report"]))
            self.assertEqual(self.snapshot(), still)
        code, out = self.intake("--accept-colours", "--accept-low-contrast", "both", "--replace-icons")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.sits_on(), "#fffdf7")
        self.assertNotIn("cannot tell what the installed app icons sit on", out, "these icons were drawn from the colour version, on a background the site still has: they are drawn again")
        # and with both backgrounds changed at once
        self.brand_md(BAKERY_BRAND_MD.replace("| Background | `#fff8ee` |", "| Background | `#fffcf5` |").replace("| Background | `#1a120d` |", "| Background | `#1b130e` |"))
        self.assertEqual(self.intake()[0], 3)
        code, out = self.intake("--accept-colours", "--accept-low-contrast", "both", "--replace-icons")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.sits_on(), "#fffcf5")
        self.assertNotIn("cannot tell what the installed app icons sit on", out)

    def mono_installed(self):
        """A site whose app icons were drawn from the one-colour version: the colour version, white beside
        black, has no background that keeps both. Returns the package's path."""
        pack = self.package("two.zip", T.build_zip([("p/mark.svg", rects((2, 2, 14, 28, "#ffffff"), (16, 2, 14, 28, "#000000"))), ("p/mark-mono.svg", rects((2, 2, 28, 28, "#b4531a")))]))
        self.brand_md()
        code, out = self.intake("--input", pack, "--pick", "p/mark.svg", "--mono", "p/mark-mono.svg", "--with-colours", "--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(code, 0, out)
        self.assertIn("drawn from the one-colour version", out)
        return pack

    def test_icons_that_were_drawn_from_the_one_colour_version_are_left_as_they_are_by_a_run_about_colours_with_a_note_and_no_question(self):
        # the installed favicon is the colour version, and from it alone these icons cannot have been drawn: a
        # run about colours drew "again" from it, found no background, and asked `no-background` over a change
        # of the dark background that the icons never sat on. It keeps no record of what they were drawn from,
        # so it leaves them, says so, and names the run that draws them.
        pack = self.mono_installed()
        icons = self.icons()
        dark, light = ("| Background | `#1a120d` |", "| Background | `#1b130e` |"), ("| Background | `#fff8ee` |", "| Background | `#fffdf7` |")
        for name, changes in (("only the dark background", (dark,)), ("only the light background", (light,)), ("both", (dark, light))):
            with self.subTest(name=name):
                md = BAKERY_BRAND_MD
                for old, new in changes:
                    md = md.replace(old, new)
                self.brand_md(md)
                (dry_code, dry), (code, out) = self.both_runs("--json")
                data = json.loads(out)
                self.assertEqual((dry_code, code, data["status"]), (0, 0, "done"), "\n".join(data["report"]))
                self.assertEqual(self.icons(), icons, "not a byte of the logo's files")
                for report in (json.loads(dry), data):
                    self.assertNotIn("asks", report)
                    self.assertEqual([n for n in report["notes"] if "app icons" in n], [_install.ONE_COLOUR_ICONS])
                    self.assertIn("Note: " + _install.ONE_COLOUR_ICONS, report["report"])
                    self.assertEqual([w for w in report["written"] if w.startswith(("public/favicon", "public/icon", "public/apple", "public/images/logo", "brand-handoff"))], [])
                self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).dark["bg"] == "#1b130e", dark in changes, "and the colours went in")
        self.assertEqual(_install.ONE_COLOUR_ICONS, "this tool cannot tell what the installed app icons sit on, or which version of the logo they were drawn from (it keeps the colour version only), so this run "
                         "left them as they are. To draw them for the new colours, run this again with the package the logo came in: --input, with --pick and --mono as before")
        # a change that moves no background says nothing of the icons
        self.brand_md(md.replace("| Accent | `#e2874a` |", "| Accent | `#d47c44` |"))
        data = json.loads(self.intake("--json")[1])
        self.assertEqual((data["status"], [n for n in data["notes"] if "app icons" in n]), ("done", []))
        # asked for outright, the redraw from the favicon alone is tried, and its question stands as before
        data = json.loads(self.intake("--with-logo", "--accept-colours", "--accept-low-contrast", "both", "--replace-icons", "--json")[1])
        self.assertEqual((data["status"], [k["code"] for k in data["asks"]]), ("needs-decision", ["no-background"]))
        self.assertEqual(self.icons(), icons)
        # what the note says to do, done: her package again, and the icons are drawn for the colours the site has now
        code, out = self.intake("--input", pack, "--pick", "p/mark.svg", "--mono", "p/mark-mono.svg", "--accept-colours", "--accept-low-contrast", "both", "--replace-icons")
        self.assertEqual(code, 0, out)
        self.assertIn("drawn from the one-colour version", out)

    def test_icons_drawn_from_the_colour_version_on_a_background_the_site_no_longer_has_get_the_same_note_and_it_claims_no_more_than_is_known(self):
        # (round 7) The note said "the app icons were drawn with a one-colour version of the logo". What the tool knows is less:
        # the colour version has no background among the colours the site has now. Here the icons WERE drawn from the colour
        # version, white beside black on a grey page, and the stylesheet's colours were set by hand since.
        grey = dict(T.BAKERY_LIGHT, bg="#808080", bg_soft="#858585", surface="#8a8a8a", heading="#000000", ink="#000000", muted="#000000", accent="#000000", link="#000000", line="#6f6f6f")
        self.brand_md("# Brand\n\n### Brand (fixed, theme-independent)\n| Token | Hex |\n|---|---|\n| Primary | `#000000` |\n\n### Light theme\n" + table([(l, grey[k]) for k, l in LABELS])
                      + "\n### Dark theme\n" + table([(l, T.BAKERY_DARK[k]) for k, l in LABELS]))
        pack = self.package("two.svg", rects((2, 2, 14, 28, "#ffffff"), (16, 2, 14, 28, "#000000")))
        code, out = self.intake("--input", pack, "--with-colours", "--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(code, 0, out)
        self.assertIn("(the app icons sit on #808080, drawn from the colour version)", out)
        icons = self.icons()
        self.put("src/styles/global.css", _site.edit_css(self.read("src/styles/global.css"), _palette.parse_tables(BAKERY_BRAND_MD)))   # by hand: the tool was not asked, and drew nothing again
        self.brand_md(BAKERY_BRAND_MD.replace("| Background | `#fff8ee` |", "| Background | `#fffdf7` |"))
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code), (0, 0), out)
        for report in (json.loads(dry), json.loads(out)):
            self.assertEqual([n for n in report["notes"] if "app icons" in n], [_install.ONE_COLOUR_ICONS])
        self.assertEqual(self.icons(), icons, "not a byte of the logo's files")
        # what the note says to do: the package again. This mark has no one-colour version, so what comes next is the question about its background.
        data = json.loads(self.intake("--input", pack, "--accept-colours", "--accept-low-contrast", "both", "--replace-icons", "--json")[1])
        self.assertEqual((data["status"], [k["code"] for k in data["asks"]]), ("needs-decision", ["no-background"]))

    def test_the_tools_own_favicon_is_known_again_when_a_checkout_turned_its_line_ends_into_crlf_and_one_that_was_edited_is_said_to_be_that(self):
        self.installed()
        favicon = self.bytes("public/favicon.svg")
        moved = BAKERY_BRAND_MD.replace("| Background | `#fff8ee` |", "| Background | `#fffdf7` |")
        self.assertNotIn(b"\r", favicon)
        self.put("public/favicon.svg", favicon.replace(b"\n", b"\r\n"))
        self.brand_md(moved)
        code, out = self.intake("--json", "--accept-colours", "--accept-low-contrast", "both", "--replace-icons")
        data = json.loads(out)
        self.assertEqual((code, data["status"]), (0, "done"), "\n".join(data["report"]))
        self.assertEqual([n for n in data["notes"] if "the icons were left as they are" in n], [], "it is this tool's own file, whatever its line ends")
        self.assertEqual(self.sits_on(), "#fffdf7")
        self.assertEqual(self.bytes("public/favicon.svg"), favicon, "and it is written again as this tool writes it")
        # an editor saved it with a byte order mark in front (and the checkout's line ends): still this tool's own
        for mark, background in ((b"\xef\xbb\xbf" + favicon, "#fffcf5"), (b"\xef\xbb\xbf" + favicon.replace(b"\n", b"\r\n"), "#fffbf2")):
            with self.subTest(background=background):
                self.put("public/favicon.svg", mark)
                self.brand_md(BAKERY_BRAND_MD.replace("| Background | `#fff8ee` |", "| Background | `%s` |" % background))
                code, out = self.intake("--json", "--accept-colours", "--accept-low-contrast", "both", "--replace-icons")
                data = json.loads(out)
                self.assertEqual((code, data["status"]), (0, "done"), "\n".join(data["report"]))
                self.assertEqual([n for n in data["notes"] if "the icons were left as they are" in n], [], "it is this tool's own file, with or without the mark")
                self.assertEqual(self.sits_on(), background)
                self.assertEqual(self.bytes("public/favicon.svg"), favicon, "and it is written again as this tool writes it, without the mark")
        self.assertEqual(_install._own_master(b"\xef\xbb\xbf" + favicon, "#b4531a")[0], "ours")
        self.assertEqual(_install._own_master(b"\xef\xbb\xbf" + favicon[len(_install.MARK.encode("utf-8")):], "#b4531a")[0], "other", "the mark in front does not make a file this tool's")
        # edited since: it still starts with this tool's line, and is not what this tool wrote
        self.put("public/favicon.svg", favicon.replace(b"#6b2c0b", b"#6B2C0B"))
        self.brand_md()
        code, out = self.intake()
        self.assertEqual(code, 0, out)
        self.assertIn("the icons were left as they are: public/favicon.svg is not as this tool wrote it (it starts with this tool's line and was changed since)", out)
        self.assertNotIn("is not a file this tool wrote", out)
        self.assertEqual(self.sits_on(), "#fffbf2", "left on the background they had")

    # --- a palette that was named and not read, and the notes of a run that ends badly ------------------

    def test_a_palette_that_is_there_and_not_in_the_form_the_reading_takes_ends_like_any_other_that_was_named_and_not_read(self):
        # colours in a list or in a sentence, with or without the `## Colour palette` heading above them, and the
        # three tables under another heading than that one: the reading names each (it never comes back as "no
        # palette"), and every run says so: the note beside a logo, the refusal with the form the reading takes
        listed = "- Primary: `#b4531a`\n" + "".join("- %s (light): `%s`\n" % (l, T.BAKERY_LIGHT[k]) for k, l in LABELS)
        tables = BAKERY_BRAND_MD.split("## Colour palette\n\n", 1)[1]
        self.assertTrue(tables.startswith("### Brand"))
        not_read = "holds a colour (#b4531a) that was not read"
        for name, md, said in (("a list", "# Brand\n\n## Colours\n" + listed, not_read),
                               ("a sentence", "# Brand\n\nOur colour is #b4531a on cream #fff8ee, with dark brown #3a1d0a text.\n", not_read),
                               ("a list under the palette's own heading", "# Brand\n\n## Colour palette\n\n" + listed + "\n## Logo\n\nThe mark.\n", not_read),
                               ("a sentence under the palette's own heading", "# Brand\n\n## Colour palette\n\nOur colour is #b4531a on cream #fff8ee.\n\n## Logo\n", not_read),
                               ("the three tables under another heading than the palette's", "# Brand\n\n## Colour palette\n\nSee below.\n\n## Our colours\n\n" + tables,
                                'the heading "### Brand (fixed, theme-independent)", has a table under it and stands outside the part')):
            with self.subTest(name=name):
                parsed = _palette.parse_tables(md)
                self.assertTrue(parsed.problems and not (parsed.light or parsed.dark or parsed.brand), "the reading names it and takes no colour from it")
                shutil.rmtree(self.site)
                T.make_starter_site(self.site, with_modules=self.modules)
                self.brand_md(md)
                before = self.snapshot()
                for code, out in self.both_runs():   # nothing to do, and why
                    self.assertEqual(code, 2, out)
                    self.assertIn("There is nothing to do: no complete palette was found in BRAND.md, and no logo file was given.", out)
                    self.assertIn("No colour could be read from the palette in BRAND.md.", out)
                    self.assertIn(said, out)
                    self.assertIn(_palette.FORM, out)
                    self.assertEqual(self.snapshot(), before)
                for code, out in self.both_runs("--with-colours"):
                    self.assertEqual(code, 2, out)
                    self.assertIn("No colour could be read from the palette in BRAND.md.", out)
                    self.assertIn(said, out)
                    self.assertIn(_palette.FORM, out)
                    self.assertIn("Fill in or mend what is named here", out)
                    self.assertEqual(self.snapshot(), before)
                (dry_code, dry), (code, out) = self.both_runs(*self.logo())   # the logo goes in, and the report says why the colours stayed
                self.assertEqual((dry_code, code), (0, 0), out)
                for report in (dry, out):
                    self.assertIn("Note: the colours were not changed: no colour could be read from the palette in BRAND.md", report)
                    self.assertIn(said, report)
                    self.assertIn(_palette.FORM, report)
                self.assertEqual(self.read("src/styles/global.css"), T.starter_file("src/styles/global.css"))
        # what the refusal says to do, done: the colours written in the form it names, under the palette's heading
        shutil.rmtree(self.site)
        T.make_starter_site(self.site, with_modules=self.modules)
        self.brand_md(BAKERY_BRAND_MD)
        self.assertEqual([code for code, _out in self.both_runs("--with-colours")], [0, 0])

    def test_the_notes_are_in_the_words_too_when_the_tests_are_red_or_the_run_is_refused_not_in_the_json_alone(self):
        partial = BAKERY_BRAND_MD.replace("| Muted | `#6b5744` |\n", "", 1)
        self.assertNotEqual(partial, BAKERY_BRAND_MD)
        self.brand_md(partial)
        note = "Note: the colours were not changed: BRAND.md does not hold a complete palette (rows not filled in: Muted)"
        code, out = self.intake(*self.logo(), command=RED)
        self.assertEqual(code, 1, out)
        self.assertIn(note, out.splitlines())
        self.assertTrue(json.loads(self.intake(*self.logo("--json"), command=RED)[1])["notes"][0].startswith(note[len("Note: "):]))
        self.put("brand-handoff", b"a file where the folder would go")
        for code, out in self.both_runs(*self.logo()):
            self.assertEqual(code, 2, out)
            self.assertIn(note, out.splitlines())
        os.remove(self.p("brand-handoff"))
        r = self.drive(StoppedFromOutside.AT % ("_icons.build", "SIGTERM", "_icons.build"), *self.logo()) if os.name == "posix" else None
        if r is not None:
            self.assertEqual((r.returncode, r.stderr), (2, ""), r.stdout)
            self.assertIn(note, r.stdout.splitlines())


    # --- a logo this tool installed keeps the colours it was drawn in (rounds 5 and 6) ---------------------
    # Nothing is recoloured. What the owner can do about it depends on how the mark was given, and the favicon's
    # first line says which: a mark in `currentColor` was drawn in the Primary of the day, and its package draws
    # it in today's; a mark with colours of its own is the same drawing whenever it is installed.

    CURRENT = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect x="2" y="2" width="28" height="28" fill="currentColor"/></svg>'
    DAY_ONE = BAKERY_BRAND_MD.replace("| Primary | `#b4531a` |", "| Primary | `#7a2e0b` |")
    LATER = DAY_ONE.replace("| Primary | `#7a2e0b` |", "| Primary | `#5c2208` |")
    ACCEPT = ("--accept-colours", "--accept-low-contrast", "both")
    IN_CURRENT = ("the logo was given in `currentColor` and was drawn in %s. It keeps that colour: this tool draws it in the Primary the palette has now (%s) only from the package it came "
                  "in. For that, run this again with the package: --input, with --pick and --mono as before")
    IN_ACCENT = IN_CURRENT.replace("the Primary the palette has now (%s)", "the light theme's Accent the palette has now (%s: it gives no Primary)")
    ITS_OWN = ("the logo keeps the colour it was installed with (%s), which the palette no longer holds: this run changes the site's colours and leaves the logo's files as they are, and "
               "this tool recolours nothing. For the logo in the new colours, ask the design tool for the mark in them, then run this again with that package: --input")

    def kept(self, report):
        """What a report in JSON notes about a logo that keeps its colours: (of a mark given in currentColor, of one with colours of its own)."""
        notes = json.loads(report)["notes"]
        return [n for n in notes if n.startswith("the logo was given in")], [n for n in notes if n.startswith("the logo keeps")]

    # (round 8) what a run that leaves BRAND.md's palette out says when it draws a mark given in `currentColor`, and BRAND.md names no Primary
    IN_SITE_ACCENT = ("the mark was given without a colour of its own (in `currentColor`) and is drawn in the light theme's Accent the site has now (%s), because BRAND.md names no Primary. "
                      "The site's own colours were not changed")
    IN_STYLESHEET = IN_CURRENT.replace("the Primary the palette has now (%s)", "the stylesheet's `--brand` (%s)")

    def in_accent(self, report):
        return [n for n in json.loads(report)["notes"] if n.startswith("the mark was given without a colour of its own")]

    def test_a_mark_given_in_currentcolor_keeps_the_primary_it_was_drawn_in_until_its_package_is_given_again_and_every_run_says_so(self):
        self.brand_md(self.DAY_ONE)
        mark = self.package("current.svg", self.CURRENT)
        code, out = self.intake("--input", mark, "--with-colours", *self.ACCEPT)
        self.assertEqual(code, 0, out)
        favicon, line = self.bytes("public/favicon.svg"), _install.MARK_CURRENT % "#7a2e0b"
        self.assertEqual(line, _install.MARK[:-5] + " The logo was given in currentColor and is drawn here in #7a2e0b. -->\n")
        self.assertTrue(favicon.startswith(line.encode("utf-8")) and b'fill="#7a2e0b"' in favicon, favicon[:400])
        self.assertNotIn("--", line[4:-4], "two hyphens would end the comment early")
        self.assertEqual(_install._own_master(favicon, "#7a2e0b")[::2], ("ours", "#7a2e0b"))
        self.assertEqual(_install._own_master(favicon.replace(b"\n", b"\r\n"), "#5c2208")[::2], ("ours", "#7a2e0b"), "whatever the Primary is now, and with a checkout's line ends")
        self.assertEqual(_install._own_master(favicon.replace(b"in #7a2e0b.", b"in brown."), "#7a2e0b")[0], "other", "a line that is not this tool's, to the letter, makes no file this tool's")
        icons = self.icons()
        # only the Muted row changes: the logo's colour is still the palette's Primary, and nothing is said
        self.brand_md(self.DAY_ONE.replace(T.BAKERY_LIGHT["muted"], "#6a5643"))
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, ([], []), ([], [])), out)
        # the Primary changes: said in the dry run as in the real one, in the JSON and in words, and not beside the other note (the mark has no colour of its own)
        note = self.IN_CURRENT % ("#7a2e0b", "#5c2208")
        self.brand_md(self.LATER)
        self.assertIn("Note: " + note, self.intake("--dry-run")[1].splitlines())
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, ([note], []), ([note], [])), out)
        self.assertEqual(self.icons(), icons, "the logo's files are as they were: nothing is recoloured")
        self.assertIn("themeColor: '#5c2208',", self.read("src/config.ts"))
        # a Primary that changes while the colour of the day stays in the palette under another row: before round 6 nothing was said
        self.brand_md(self.LATER.replace(T.BAKERY_DARK["line"], "#7a2e0b"))
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, ([note], []), ([note], [])), out)
        # the icons drawn again from the installed favicon (no package): still in the colour of the day, the line as it was, and the note again
        code, out = self.intake("--with-logo", "--json", "--replace-icons", *self.ACCEPT)
        self.assertEqual((code, self.kept(out), self.bytes("public/favicon.svg")), (0, ([note], []), favicon), out)
        # what the note says to do: the package again, and the mark is drawn in the Primary of today. Nothing is left to say.
        code, out = self.intake("--input", mark, "--json", "--replace-icons", *self.ACCEPT)
        self.assertEqual((code, self.kept(out)), (0, ([], [])), out)
        self.assertTrue(self.bytes("public/favicon.svg").startswith((_install.MARK_CURRENT % "#5c2208").encode("utf-8")) and b'fill="#5c2208"' in self.bytes("public/favicon.svg"))
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, ([], []), ([], [])), out)

    def test_a_mark_with_colours_of_its_own_keeps_them_and_is_not_sent_back_to_the_package_that_would_draw_the_same_again(self):
        # the note of round 5 said "run this again with the package it came in" of every mark. For a mark with colours
        # of its own that run changes nothing: the same drawing, in the same colours.
        self.brand_md(self.DAY_ONE)
        mark = self.package("own.svg", rects((2, 2, 28, 28, "#7a2e0b")))
        code, out = self.intake("--input", mark, "--with-colours", *self.ACCEPT)
        self.assertEqual(code, 0, out)
        favicon = self.bytes("public/favicon.svg")
        self.assertTrue(favicon.startswith(_install.MARK.encode("utf-8")) and b"currentColor" not in favicon, "the line without the second part: colours of its own")
        self.assertEqual(_install._own_master(favicon, "#7a2e0b")[::2], ("ours", None))
        icons, note = self.icons(), self.ITS_OWN % "#7a2e0b"
        self.brand_md(self.LATER)
        self.assertIn("Note: " + note, self.intake("--dry-run")[1].splitlines())
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, ([], [note]), ([], [note])), out)
        self.assertEqual(self.icons(), icons)
        # the next run about colours: the colour was dropped before, not by this run, and it is not said again
        self.brand_md(self.LATER.replace(T.BAKERY_LIGHT["muted"], "#6a5643"))
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, ([], []), ([], [])), out)
        # the same package again: the same files, to the byte (which is why the note no longer says to do that)
        code, out = self.intake("--input", mark, "--replace-icons", *self.ACCEPT)
        self.assertEqual((code, self.icons()), (0, icons), out)
        # what the note says to do: the mark in the new colours, as a package of its own
        code, out = self.intake("--input", self.package("new.svg", rects((2, 2, 28, 28, "#5c2208"))), "--json", "--replace-icons", *self.ACCEPT)
        self.assertEqual((code, self.kept(out)), (0, ([], [])), out)
        self.assertIn(b'fill="#5c2208"', self.bytes("public/favicon.svg"))
        # A favicon installed before the line said how the mark was given: its line is the first form, whatever the
        # mark was. It is taken as a mark with colours of its own.
        self.put("public/favicon.svg", _install.MARK.encode("utf-8") + _svg.clean_svg(self.CURRENT, current="#5c2208").text.encode("utf-8"))
        self.brand_md(BAKERY_BRAND_MD)
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, ([], [self.ITS_OWN % "#5c2208"]), ([], [self.ITS_OWN % "#5c2208"])), out)

    def test_a_mark_with_a_part_in_currentcolor_and_a_colour_of_its_own_gets_each_note_when_it_is_true_and_both_when_both_are(self):
        # (round 7) "Never both" was a rule for a mark of one kind. For a mark with both, a Primary that changed kept the
        # note about the mark's own colour back, though no run with the package brings that colour into the palette.
        def mixed(own):
            return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect x="2" y="2" width="14" height="28" fill="currentColor"/>'
                    '<rect x="16" y="2" width="14" height="28" fill="%s"/></svg>' % own).encode("utf-8")
        link = ("| Link | `#a14a14` |", "| Link | `#96440f` |")   # the light theme's Link, which is the colour of the mark's own
        self.assertEqual(self.DAY_ONE.count(link[0]), 1)
        mark = self.package("mixed.svg", mixed("#a14a14"))
        current, own = self.IN_CURRENT % ("#7a2e0b", "#5c2208"), self.ITS_OWN % "#a14a14"

        def day_one():
            self.brand_md(self.DAY_ONE)
            code, out = self.intake("--input", mark, "--with-colours", "--replace-icons", *self.ACCEPT)
            self.assertEqual(code, 0, out)
            favicon = self.bytes("public/favicon.svg")
            self.assertTrue(favicon.startswith((_install.MARK_CURRENT % "#7a2e0b").encode("utf-8")) and b'fill="#7a2e0b"' in favicon and b'fill="#a14a14"' in favicon, favicon[:500])
            return self.icons()
        for label, md, notes in (("both change", self.LATER.replace(*link), ([current], [own])), ("only the Primary changes", self.LATER, ([current], [])),
                                 ("only the colour of its own leaves the palette", self.DAY_ONE.replace(*link), ([], [own]))):
            with self.subTest(label=label):
                icons = day_one()
                self.brand_md(md)
                for note in notes[0] + notes[1]:
                    self.assertIn("Note: " + note, self.intake("--dry-run")[1].splitlines())
                (dry_code, dry), (code, out) = self.both_runs("--json")
                self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, notes, notes), out)
                self.assertEqual(self.icons(), icons, "the logo's files are as they were: nothing is recoloured")
        # After "both change": the colour of its own was dropped by that run and is not said again; the other note stays
        # true until the package is given again.
        day_one()
        self.brand_md(self.LATER.replace(*link))
        self.assertEqual(self.intake()[0], 0)
        code, out = self.intake("--json")
        self.assertEqual((code, self.kept(out)), (0, ([current], [])), out)
        # what the first note says to do: the package again. The part in currentColor is drawn in the Primary of today; the
        # colour of its own is as it was, and is asked about as any colour outside the palette is (answered here).
        code, out = self.intake("--input", mark, "--json", "--replace-icons", *self.ACCEPT)
        favicon = self.bytes("public/favicon.svg")
        self.assertEqual((code, self.kept(out), b'fill="#5c2208"' in favicon, b'fill="#a14a14"' in favicon), (0, ([], []), True, True), out)
        self.assertEqual(json.loads(self.intake("--input", mark, "--json", "--replace-icons", "--accept-low-contrast", "both")[1])["asks"][0]["code"], "outside-palette")
        # what the second note says to do: the mark in the new colours, as a package of its own. Nothing is left to say.
        code, out = self.intake("--input", self.package("new.svg", mixed("#96440f")), "--json", "--replace-icons", "--accept-low-contrast", "both")
        self.assertEqual((code, self.kept(out)), (0, ([], [])), out)
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, ([], []), ([], [])), out)

    # (round 9) INVARIANT: every colour the installed logo keeps that the new palette drops is named by a note whose way out
    # works for it. A part in `currentColor` beside a part written in the Primary of the day: in the installed file the two
    # are one colour, and a later run about colours gave the note about `currentColor` alone. Its way out, the package
    # again, draws only the first part in the new Primary. The favicon's line now says that a part has the colour as its
    # own, and such a mark gets both notes.

    @staticmethod
    def two_parts(second, first='fill="currentColor"'):
        """A mark of two rectangles, each with the attributes given: the first in `currentColor` unless said otherwise."""
        return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect x="2" y="2" width="14" height="28" %s/>'
                '<rect x="16" y="2" width="14" height="28" %s/></svg>' % (first, second)).encode("utf-8")

    def test_a_colour_of_its_own_that_is_the_very_colour_the_currentcolor_part_was_drawn_in_is_said_in_the_favicons_line_and_gets_its_note_too(self):
        own_line, plain_line = _install.MARK_CURRENT_OWN % "#7a2e0b", _install.MARK_CURRENT % "#7a2e0b"
        self.assertEqual(own_line, _install.MARK[:-5] + " The logo was given in currentColor and is drawn here in #7a2e0b. A part of it has that colour as its own. -->\n")
        self.assertNotIn("--", own_line[4:-4], "two hyphens would end the comment early")
        current, own = self.IN_CURRENT % ("#7a2e0b", "#5c2208"), self.ITS_OWN % "#7a2e0b"
        link = ("| Link | `#a14a14` |", "| Link | `#96440f` |")   # the light theme's Link
        self.assertEqual(self.LATER.count(link[0]), 1)
        group = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><g fill="currentColor"><rect x="2" y="2" width="14" height="28"/>'
                 b'<rect color="#7a2e0b" x="16" y="2" width="14" height="28"/></g></svg>')
        kinds = (   # (what the mark is, the mark, the line its favicon gets, the palette of the later run, what that run notes)
            ("a part in currentColor and a part written in the Primary of the day", self.two_parts('fill="#7a2e0b"'), own_line, self.LATER, ([current], [own])),
            ("the same, with a stroke in another colour of its own, which leaves the palette too", self.two_parts('fill="#7a2e0b" stroke="#a14a14"'), own_line, self.LATER.replace(*link),
             ([current], [self.ITS_OWN.replace("keeps the colour it", "keeps the colours it") % "#7a2e0b, #a14a14"])),
            ("inside a group in currentColor, a part that sets `color` to the Primary of the day (cleaned with another colour, that mark is refused)", group, own_line, self.LATER,
             ([current], [own])),
            # as before round 9: the three kinds of mark that hold no colour twice
            ("a part in currentColor and a part in another colour of its own", self.two_parts('fill="#a14a14"'), plain_line, self.LATER.replace(*link), ([current], [self.ITS_OWN % "#a14a14"])),
            ("in currentColor alone", self.CURRENT, plain_line, self.LATER, ([current], [])),
            ("colours of its own alone", self.two_parts('fill="#7a2e0b"', 'fill="#7a2e0b"'), _install.MARK, self.LATER, ([], [own])),
        )
        for label, svg, line, later, notes in kinds:
            with self.subTest(label=label):
                self.brand_md(self.DAY_ONE)
                code, out = self.intake("--input", self.package("mark.svg", svg), "--with-colours", "--replace-icons", *self.ACCEPT)
                self.assertEqual(code, 0, out)
                favicon, icons = self.bytes("public/favicon.svg"), self.icons()
                self.assertTrue(favicon.startswith(line.encode("utf-8")) and b"currentColor" not in favicon[len(line):] and b'fill="#7a2e0b"' in favicon, favicon[:500])
                whose, _kept, drawn, own_too = _install._own_master(favicon, "#5c2208")
                self.assertEqual((whose, drawn, own_too), ("ours", None if line == _install.MARK else "#7a2e0b", line == own_line))
                self.brand_md(later)
                for note in notes[0] + notes[1]:
                    self.assertIn("Note: " + note, self.intake("--dry-run")[1].splitlines())
                (dry_code, dry), (code, out) = self.both_runs("--json")
                self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, notes, notes), out)
                self.assertEqual(self.icons(), icons, "the logo's files are as they were: nothing is recoloured")
        # however the colour of its own is written, and wherever it stands: it is that colour, and the line says so
        for attributes in ('fill="#7A2E0B"', 'fill="rgb(122, 46, 11)"', 'fill=" #7a2e0b "', 'style="fill:#7a2e0b"', 'fill="none" stroke="#7a2e0b"', 'fill="currentColor" stroke="#7a2e0b"'):
            with self.subTest(attributes=attributes):
                svg = self.two_parts(attributes)
                self.assertEqual(_install._given_in_current(svg, _svg.clean_svg(svg, current="#7a2e0b"), "#7a2e0b"), (True, True))
        for label, svg, primary, said in (("another colour of its own", self.two_parts('fill="#a14a14"'), "#7a2e0b", (True, False)), ("in currentColor alone", self.CURRENT, "#7a2e0b", (True, False)),
                                          ("both parts in currentColor", self.two_parts('fill="currentColor"'), "#7a2e0b", (True, False)),
                                          ("a part with no colour written, which is black, under a black Primary", self.two_parts(""), "#000000", (True, True)),
                                          ("the same under another Primary", self.two_parts(""), "#7a2e0b", (True, False))):
            with self.subTest(label=label):
                self.assertEqual(_install._given_in_current(svg, _svg.clean_svg(svg, current=primary), primary), said)
        self.assertFalse(_install._given_in_current(self.two_parts('fill="#7a2e0b"', 'fill="#7a2e0b"'), _svg.clean_svg(self.two_parts('fill="#7a2e0b"', 'fill="#7a2e0b"'), current="#7a2e0b"), "#7a2e0b")[0])

    def test_the_reviewers_mark_of_round_8_gets_both_notes_when_the_palette_drops_its_colour_and_each_way_out_does_what_its_note_says(self):
        # both parts are #b4531a on the day: the bakery's Primary, and its light theme's Accent too
        mark = self.package("mixed.svg", self.two_parts('fill="#b4531a"'))
        self.brand_md(BAKERY_BRAND_MD)
        code, out = self.intake("--input", mark, "--with-colours", *self.ACCEPT)
        self.assertEqual(code, 0, out)
        favicon, icons = self.bytes("public/favicon.svg"), self.icons()
        self.assertTrue(favicon.startswith((_install.MARK_CURRENT_OWN % "#b4531a").encode("utf-8")) and favicon.count(b'fill="#b4531a"') == 2, favicon[:500])
        current, own = self.IN_CURRENT % ("#b4531a", "#7a2e0b"), self.ITS_OWN % "#b4531a"
        # another Primary, and the palette still holds the colour (as the light theme's Accent): the part of its own is in the palette, and has no note
        primary = BAKERY_BRAND_MD.replace("| Primary | `#b4531a` |", "| Primary | `#7a2e0b` |")
        self.assertEqual((primary.count("#b4531a"), primary.count("| Accent | `#b4531a` |")), (1, 1))
        self.brand_md(primary)
        code, out = self.intake("--dry-run", "--json")
        self.assertEqual((code, self.kept(out)), (0, ([current], [])), out)
        # another Primary and another Accent: the palette holds the colour no longer, and both notes are given, in the dry run as in the real one
        dropped = primary.replace("| Accent | `#b4531a` |", "| Accent | `#a84c16` |")
        self.brand_md(dropped)
        for note in (current, own):
            self.assertIn("Note: " + note, self.intake("--dry-run")[1].splitlines())
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, ([current], [own]), ([current], [own])), out)
        self.assertEqual(self.icons(), icons, "the logo's files are as they were: nothing is recoloured")
        # the next run about colours: the colour of its own was dropped by the run before and is not said again; the other note stays true
        code, out = self.intake("--json")
        self.assertEqual((code, self.kept(out)), (0, ([current], [])), out)
        # what the first note says to do: the package again. The part in currentColor is drawn in the Primary of today. The part of
        # its own keeps its colour, which is why it had a note of its own: it is asked about as any colour outside the palette is.
        self.assertEqual([k["code"] for k in json.loads(self.intake("--input", mark, "--json", "--replace-icons", "--accept-low-contrast", "both")[1])["asks"]], ["outside-palette"])
        code, out = self.intake("--input", mark, "--json", "--replace-icons", *self.ACCEPT)
        favicon = self.bytes("public/favicon.svg")
        self.assertEqual((code, self.kept(out)), (0, ([], [])), out)
        self.assertTrue(favicon.startswith((_install.MARK_CURRENT % "#7a2e0b").encode("utf-8")) and b'fill="#7a2e0b"' in favicon and b'fill="#b4531a"' in favicon, favicon[:500])
        # what the second note says to do: the mark in the new colours, as a package of its own. Nothing is left to say.
        code, out = self.intake("--input", self.package("new.svg", self.two_parts('fill="#7a2e0b"')), "--json", "--replace-icons", "--accept-low-contrast", "both")
        self.assertEqual((code, self.kept(out)), (0, ([], [])), out)
        self.assertTrue(self.bytes("public/favicon.svg").startswith((_install.MARK_CURRENT_OWN % "#7a2e0b").encode("utf-8")))
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, ([], []), ([], [])), out)

    def test_the_favicons_line_is_written_back_as_it_was_read_when_the_icons_are_drawn_again_and_a_line_in_a_form_this_tool_does_not_write_makes_no_file_its_own(self):
        moved = ("| Background | `#fff8ee` |", "| Background | `#fffdf7` |")
        self.assertEqual(self.DAY_ONE.count(moved[0]), 1)
        self.brand_md(self.DAY_ONE)
        mark = self.package("mixed.svg", self.two_parts('fill="#7a2e0b"'))
        code, out = self.intake("--input", mark, "--with-colours", *self.ACCEPT)
        self.assertEqual(code, 0, out)
        favicon = self.bytes("public/favicon.svg")
        self.assertTrue(favicon.startswith((_install.MARK_CURRENT_OWN % "#7a2e0b").encode("utf-8")), favicon[:400])
        self.assertEqual(self.sits_on(), "#fff8ee")
        # a run about colours that draws the icons again (the background they sit on changes): the line is as it was
        self.brand_md(self.DAY_ONE.replace(*moved))
        code, out = self.intake("--json", "--replace-icons", *self.ACCEPT)
        self.assertEqual((code, self.kept(out), self.sits_on(), self.bytes("public/favicon.svg")), (0, ([], []), "#fffdf7", favicon), out)
        # the icons again because she asks for them: the line is as it was
        code, out = self.intake("--with-logo", "--json", "--replace-icons", *self.ACCEPT)
        self.assertEqual((code, self.kept(out), self.bytes("public/favicon.svg")), (0, ([], []), favicon), out)
        icons = self.icons()
        # the second run about colours: the Primary changes, and the line that came through both drawings still gets the mark both notes
        notes = ([self.IN_CURRENT % ("#7a2e0b", "#5c2208")], [self.ITS_OWN % "#7a2e0b"])
        self.brand_md(self.LATER.replace(*moved))
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, notes, notes), out)
        self.assertEqual(self.icons(), icons)
        # a checkout's line ends and an editor's byte order mark are not held against the longer line either
        whose, _kept, drawn, own_too = _install._own_master(b"\xef\xbb\xbf" + favicon.replace(b"\n", b"\r\n"), "#5c2208")
        self.assertEqual((whose, drawn, own_too), ("ours", "#7a2e0b", True))
        # a drawing that was changed under the line: not as this tool wrote it, and nothing is read from its line
        self.assertEqual(_install._own_master(favicon.replace(b'fill="#7a2e0b"', b'fill="#7A2E0B"'), "#5c2208"), ("changed", None, None, False))
        # a line in a form this tool does not write: the file is not this tool's, as with any other line that is not this tool's to the letter
        sentence, body = b" A part of it has that colour as its own.", favicon[len(_install.MARK_CURRENT_OWN % "#7a2e0b"):]
        self.assertEqual(favicon.count(sentence), 1)
        edited = (favicon.replace(b"that colour as", b"that color as"), favicon.replace(sentence, sentence * 2), favicon.replace(sentence, sentence + b" "), favicon.replace(sentence, sentence[:-1]),
                  favicon.replace(sentence, b" A part of it has #7a2e0b as its own."), favicon.replace(b"in #7a2e0b.", b"in #7A2E0B."),
                  _install.MARK[:-5].encode("utf-8") + sentence + b" -->\n" + body)
        for other in edited:
            with self.subTest(line=other[len(_install.MARK) - 5:len(other) - len(body)]):
                self.assertEqual(_install._own_master(other, "#5c2208"), ("other", None, None, False))
        self.put("public/favicon.svg", edited[0])
        self.brand_md(self.LATER.replace(moved[0], "| Background | `#fffcf5` |").replace("| Primary | `#5c2208` |", "| Primary | `#6b2c0b` |"))
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, ([], []), ([], [])), out)
        for report in (dry, out):
            self.assertEqual([n for n in json.loads(report)["notes"] if "the icons were left as they are" in n],
                             ["the icons were left as they are: public/favicon.svg is not a file this tool wrote, so the app icons were not drawn again on the new background. "
                              "To make them again from that file, run this again with --with-logo; to install a logo, give it with --input"])
        self.assertEqual((self.sits_on(), self.bytes("public/favicon.svg")), ("#fffdf7", edited[0]), "left on the background they had, and the file as she edited it")

    def test_where_the_palette_gives_no_primary_a_mark_in_currentcolor_is_drawn_in_the_light_accent_by_every_kind_of_run_and_the_note_comes_when_that_colour_changed(self):
        # (round 7) A palette without a Primary row: the mark is drawn in the light theme's Accent, and the stylesheet's
        # `--brand` stays the starter's black. A later run that went by the site's own colours took that black for the
        # Primary: it said the Primary had changed, and with the package it drew the logo black.
        no_primary = BAKERY_BRAND_MD.replace("| Primary | `#b4531a` | buttons, brand surfaces |\n", "")
        self.assertEqual((no_primary.count("Primary"), no_primary.count("| Accent | `#b4531a` |")), (0, 1))
        self.brand_md(no_primary)
        mark = self.package("current.svg", self.CURRENT)
        code, out = self.intake("--input", mark, "--with-colours", *self.ACCEPT)
        self.assertEqual(code, 0, out)
        favicon = self.bytes("public/favicon.svg")
        self.assertTrue(favicon.startswith((_install.MARK_CURRENT % "#b4531a").encode("utf-8")) and b'fill="#b4531a"' in favicon, favicon[:400])
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).brand, "#000000", "the palette gives no Primary, so the stylesheet's is the starter's still")
        half = no_primary.replace("| Muted | `#6b5744` |\n", "")
        for label, md, extra in (("the icons again, the site's colours kept", no_primary, ("--with-logo", "--keep-colours")), ("the package again, the site's colours kept", no_primary, ("--input", mark, "--keep-colours")),
                                 ("the package again beside a palette that is not complete", half, ("--input", mark)), ("the icons again beside a palette that is not complete", half, ("--with-logo",)),
                                 ("a run about colours", no_primary, ())):
            with self.subTest(label=label):
                self.brand_md(md)
                (dry_code, dry), (code, out) = self.both_runs("--json", "--replace-icons", *(self.ACCEPT + extra))
                self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, ([], []), ([], [])), out)
                self.assertEqual(self.bytes("public/favicon.svg"), favicon, "drawn in the light theme's Accent, as on the day")
                # (round 8) a run that leaves the palette out and draws the mark from its package says which colour it took, and why;
                # one that draws the icons again from the installed favicon draws nothing in a colour it chose, and a run about colours has its own note
                said = [self.IN_SITE_ACCENT % "#b4531a"] if "--input" in extra else []
                self.assertEqual((self.in_accent(dry), self.in_accent(out)), (said, said), out)
        # the light theme's Accent changes: that is the colour the mark was drawn in, and now the note is true
        self.brand_md(no_primary.replace("| Accent | `#b4531a` |", "| Accent | `#a84c16` |"))
        note = self.IN_ACCENT % ("#b4531a", "#a84c16")
        self.assertIn("Note: " + note, self.intake("--dry-run")[1].splitlines())
        (dry_code, dry), (code, out) = self.both_runs("--json")
        self.assertEqual((dry_code, code, self.kept(dry), self.kept(out)), (0, 0, ([note], []), ([note], [])), out)
        code, out = self.intake("--with-logo", "--keep-colours", "--json", "--replace-icons", *self.ACCEPT)
        self.assertEqual((code, self.kept(out), self.bytes("public/favicon.svg")), (0, ([note], []), favicon), out)
        # what the note says to do, with the site's colours kept or not: the package again, and the mark is drawn in the Accent of today
        for extra in (("--keep-colours",), ()):
            code, out = self.intake("--input", mark, "--json", "--replace-icons", *(self.ACCEPT + extra))
            self.assertEqual((code, self.kept(out)), (0, ([], [])), out)
            self.assertTrue(self.bytes("public/favicon.svg").startswith((_install.MARK_CURRENT % "#a84c16").encode("utf-8")) and b'fill="#a84c16"' in self.bytes("public/favicon.svg"))
        # a Primary row added later: the note names the Primary
        self.brand_md(BAKERY_BRAND_MD.replace("| Primary | `#b4531a` |", "| Primary | `#7a2e0b` |").replace("| Accent | `#b4531a` |", "| Accent | `#a84c16` |"))
        code, out = self.intake("--json")
        self.assertEqual((code, self.kept(out)), (0, ([self.IN_CURRENT % ("#a84c16", "#7a2e0b")], [])), out)

    def test_a_run_that_leaves_brand_md_out_and_draws_a_mark_in_the_sites_accent_because_brand_md_names_no_primary_says_so(self):
        # (round 8) INVARIANT: a run that draws the logo in a colour it chose names that colour and says why. The site had a
        # Primary of this tool's making (in `--brand`, the theme colour and the favicon); BRAND.md then lost its Primary
        # row. A logo run that left BRAND.md out (--keep-colours, or a palette that is not complete) drew the mark in the
        # light theme's Accent and said nothing, in a report that said the palette was not applied.
        self.brand_md(self.DAY_ONE)
        mark = self.package("current.svg", self.CURRENT)
        code, out = self.intake("--input", mark, "--with-colours", *self.ACCEPT)
        self.assertEqual(code, 0, out)
        self.assertIn(b'fill="#7a2e0b"', self.bytes("public/favicon.svg"))
        stylesheet = self.read("src/styles/global.css")
        self.assertEqual((_palette.read_css(stylesheet).brand, _palette.read_css(stylesheet).light["accent"]), ("#7a2e0b", "#b4531a"))
        # BRAND.md without its Primary row, and with another Accent than the site has: the colour taken, and named, is the site's
        no_primary = self.DAY_ONE.replace("| Primary | `#7a2e0b` | buttons, brand surfaces |\n", "").replace("| Accent | `#b4531a` |", "| Accent | `#a84c16` |")
        self.assertEqual((no_primary.count("Primary"), no_primary.count("#a84c16")), (0, 1))
        note = self.IN_SITE_ACCENT % "#b4531a"
        for label, md, extra in (("--keep-colours", no_primary, ("--keep-colours",)), ("a palette that is not complete", no_primary.replace("| Muted | `#6b5744` |\n", ""), ()),
                                 ("--keep-colours, and the palette named with --palette", no_primary, ("--keep-colours", "--palette", self.p("BRAND.md")))):
            with self.subTest(label=label):
                self.brand_md(md)
                self.assertIn("Note: " + note, self.intake("--input", mark, "--dry-run", "--replace-icons", *(self.ACCEPT + extra))[1].splitlines())
                (dry_code, dry), (code, out) = self.both_runs("--input", mark, "--json", "--replace-icons", *(self.ACCEPT + extra))
                self.assertEqual((dry_code, code, self.in_accent(dry), self.in_accent(out), self.kept(out)), (0, 0, [note], [note], ([], [])), out)
                self.assertTrue(self.bytes("public/favicon.svg").startswith((_install.MARK_CURRENT % "#b4531a").encode("utf-8")) and b'fill="#b4531a"' in self.bytes("public/favicon.svg"), "drawn in the colour the note names")
                self.assertEqual(self.read("src/styles/global.css"), stylesheet, "the site's own colours were not changed, as the note says")
        # where the note is not true it is not given: BRAND.md names a Primary; the mark has a colour of its own; the icons
        # are drawn again from the installed favicon (its own note says what it keeps); no BRAND.md at all
        own = self.package("own.svg", rects((2, 2, 28, 28, "#b4531a")))
        for label, md, extra in (("BRAND.md names a Primary", self.DAY_ONE, ("--input", mark, "--keep-colours")), ("a mark with a colour of its own", no_primary, ("--input", own, "--keep-colours")),
                                 ("the icons again from the installed favicon", no_primary, ("--with-logo", "--keep-colours")), ("no BRAND.md", None, ("--input", mark))):
            with self.subTest(label=label):
                if md is None:
                    os.remove(self.p("BRAND.md"))
                else:
                    self.brand_md(md)
                (dry_code, dry), (code, out) = self.both_runs("--json", "--replace-icons", *(self.ACCEPT + extra), brand=False)
                self.assertEqual((dry_code, code, self.in_accent(dry), self.in_accent(out)), (0, 0, [], []), out)

    def test_with_no_palette_to_ask_the_note_names_the_stylesheets_brand_and_with_no_colour_to_name_it_is_not_given(self):
        # (round 8) BRAND.md deleted after an install from a palette without a Primary: the note said "the Primary the palette
        # has now (#000000)" where there is no palette, and #000000 is the starter's `--brand`, which no palette ever set.
        no_primary = BAKERY_BRAND_MD.replace("| Primary | `#b4531a` | buttons, brand surfaces |\n", "")
        self.brand_md(no_primary)
        mark = self.package("current.svg", self.CURRENT)
        code, out = self.intake("--input", mark, "--with-colours", *self.ACCEPT)
        self.assertEqual(code, 0, out)
        favicon = self.bytes("public/favicon.svg")
        self.assertTrue(favicon.startswith((_install.MARK_CURRENT % "#b4531a").encode("utf-8")), favicon[:300])
        self.assertEqual(_palette.read_css(self.read("src/styles/global.css")).brand, "#000000")
        note = self.IN_STYLESHEET % ("#b4531a", "#000000")
        self.assertEqual(note, "the logo was given in `currentColor` and was drawn in #b4531a. It keeps that colour: this tool draws it in the stylesheet's `--brand` (#000000) only from the package it came in. "
                               "For that, run this again with the package: --input, with --pick and --mono as before")
        for label, md in (("BRAND.md deleted", None), ("a BRAND.md with no row of a palette in it", "# Brand\n\nThe colours are still to come.\n")):
            with self.subTest(label=label):
                if md is None:
                    os.remove(self.p("BRAND.md"))
                else:
                    self.brand_md(md)
                self.assertIn("Note: " + note, self.intake("--with-logo", "--dry-run", "--replace-icons", *self.ACCEPT, brand=False)[1].splitlines())
                (dry_code, dry), (code, out) = self.both_runs("--with-logo", "--json", "--replace-icons", *self.ACCEPT, brand=False)
                self.assertEqual((dry_code, code, self.kept(dry), self.kept(out), self.bytes("public/favicon.svg")), (0, 0, ([note], []), ([note], []), favicon), out)
                self.assertNotIn("palette has now", dry + out, "there is no palette to speak of")
        # what the note says to do: the package again, and the mark is drawn in the stylesheet's `--brand`. Nothing is left to say.
        code, out = self.intake("--input", mark, "--json", "--replace-icons", *self.ACCEPT, brand=False)
        self.assertEqual((code, self.kept(out), self.in_accent(out)), (0, ([], []), []), out)
        self.assertTrue(self.bytes("public/favicon.svg").startswith((_install.MARK_CURRENT % "#000000").encode("utf-8")) and b'fill="#000000"' in self.bytes("public/favicon.svg"))
        code, out = self.intake("--with-logo", "--json", "--replace-icons", *self.ACCEPT, brand=False)
        self.assertEqual((code, self.kept(out)), (0, ([], [])), out)
        # Neither a Primary nor an Accent to be had: BRAND.md has rows and names no Primary (so the stylesheet's `--brand` is not
        # asked), and the stylesheet's `:root` block sets no `--accent`. The note would have said "None" for the colour: it is not given.
        self.put("public/favicon.svg", favicon)
        self.brand_md(no_primary)
        css = self.read("src/styles/global.css")
        light = re.search(r"(?m)^  --accent: #b4531a;.*\n", css)
        self.assertTrue(light and css.count("--accent: #b4531a;") == 1 and "--link: var(" not in css, "the light theme's Accent on a line of its own, and no colour written as another")
        self.put("src/styles/global.css", css[:light.start()] + css[light.end():])
        read = _palette.read_css(self.read("src/styles/global.css"))
        self.assertEqual((read.light.get("accent"), read.problems), (None, []), "the reading takes the stylesheet, and finds no Accent for the light theme")
        for extra in (("--with-logo", "--keep-colours"), ("--with-logo", "--keep-colours", "--dry-run")):
            with self.subTest(extra=extra):
                code, out = self.intake("--json", "--replace-icons", *(self.ACCEPT + extra))
                self.assertEqual((self.kept(out), self.in_accent(out)), (([], []), []), out)
                self.assertNotIn("None", out)
                self.assertNotIn("Traceback", out)


class NoSharp(SiteCase):
    """Scenario 19, the half that stops."""
    modules = False

    def test_a_logo_without_sharp_stops_before_writing_with_the_command_to_run(self):
        before = self.snapshot()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--accept-colours", brand=False)
        self.assertEqual(code, 2, out)
        self.assertIn("npm install --include=optional", out)
        self.assertIn("package.json", out)
        self.assertEqual(self.snapshot(), before)


class BothParts(SiteCase):
    def test_the_whole_run_and_what_it_leaves_behind(self):
        T.require_pillow(self)
        self.brand_md()
        code, out = self.intake("--input", self.package(), "--pick", T.REAL_COLOUR, "--mono", T.REAL_MONO, "--with-colours", "--accept-colours",
                                "--accept-low-contrast", "dark")
        self.assertEqual(code, 0, out)
        css = _palette.read_css(self.read("src/styles/global.css"))
        self.assertEqual((css.light, css.dark, css.dark_media), (T.BAKERY_LIGHT, T.BAKERY_DARK, T.BAKERY_DARK))
        self.assertTrue(self.exists("public/images/logo.png"))
        self.assertTrue(self.exists("brand-handoff/logo.zip"))
        self.assertIn("Done", out)
        self.assertIn("src/styles/global.css", out)
        self.assertIn("public/icon-maskable-512.png", out)

    def test_a_palette_after_launch_starts_from_the_installed_master_not_the_placeholder(self):
        # scenario 16: the logo is already installed; only the colours change
        self.brand_md()
        args = ("--input", self.package(), "--pick", T.REAL_COLOUR, "--with-colours", "--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(self.intake(*args)[0], 0)
        master = self.read("public/favicon.svg")
        warmer = BAKERY_BRAND_MD.replace(T.BAKERY_LIGHT["bg"], "#fffaf2")
        self.brand_md(warmer)
        code, out = self.intake("--accept-colours", "--accept-low-contrast", "both")
        self.assertEqual(code, 3, out)
        self.assertIn("public/apple-touch-icon.png", out, "the icons that depend on the background are asked about")
        code, out = self.intake("--accept-colours", "--accept-low-contrast", "both", "--replace-icons")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.read("public/favicon.svg"), master, "the master is what it was")
        import _png
        pic = _png.decode(self.bytes("public/icon-maskable-512.png"))
        self.assertEqual(_png.at(pic, 0, 0), (0xff, 0xfa, 0xf2, 255), "the new light background is under the maskable icon")


if __name__ == "__main__":
    unittest.main()
