#!/usr/bin/env python3
"""A scripted run of the docs/ANTIGRAVITY-TEST.md checklist through the agy CLI, unattended, against a release zip.

Maintainer tool for the release runbook; not shipped in the zip. Standard library only.

  python3 -I scripts/antigravity_release_test.py --zip dist/croftweaver.zip --sha <commit> \\
      --out <dir> (--short | --full | --auto --since <tag>) \\
      (--dry-run | --yes-spend-agy-credits) [--model <id>] [--keep]

--short: checklist steps 1, 2 and 4 (install, discovery, the interview starts), in agy's sandbox.
--full:  adds steps 3 and 5 to 7 (the scaffold, the site's build and tests, permissions).
--auto:  full when <since>..<sha> changes skills/new-website/ or the two Antigravity docs.

Exit codes: 0 every checked step passed; 1 a step failed; 2 usage or setup error, or refused;
3 agy did not run (no turn succeeded and no tool step ran); 4 the zip is not the release;
5 the result cannot be trusted (agy changed a file the test protects).
"""
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import zipfile

TESTED_AGY_VERSION = "1.4.2"  # the version the transcript parser was written against
DEFAULT_MODEL = "gemini-3.8-flash-high"
WATCHED = ("skills/new-website/", "docs/ANTIGRAVITY.md", "docs/ANTIGRAVITY-TEST.md")
ROOT_FILES = (".gitignore", "SETUP.md", "PUBLISHING.md", "AGENTS.md", "CLAUDE.md")
PRINT_TIMEOUT = {"short": "5m", "full": "30m"}
NPM_DEADLINE = 600  # seconds for each of npm install, npm run build, npm test
SECRET = re.compile(r"ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
                    r"|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
                    r"|://[^/\s\"'@:]+:[^/\s\"'@]+@")
EXIT_TEXT = {0: "every checked step passed", 1: "a step failed", 2: "usage or setup error",
             3: "agy did not run", 4: "the zip is not the release", 5: "result cannot be trusted"}

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HOME = os.path.expanduser("~")
AGY_SETTINGS = os.path.join(HOME, ".gemini", "antigravity-cli", "settings.json")
GLOBAL_NEW_WEBSITE = os.path.join(HOME, ".gemini", "config", "skills", "new-website", "SKILL.md")
LOCK = os.path.join(HOME, ".croftweaver-agy-test.lock")


class Stop(Exception):
    """Ends the run with an exit code and a message."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def say(msg):
    print(msg, flush=True)


def git(*args):
    r = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    if r.returncode != 0:
        raise Stop(2, "git %s failed: %s" % (" ".join(args), r.stderr.decode(errors="replace").strip()))
    return r.stdout


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def tree(root, exclude=()):
    """Map each file under root (relative path) to its SHA-256, skipping excluded prefixes."""
    out = {}
    for d, _, files in os.walk(root):
        for name in files:
            p = os.path.join(d, name)
            rel = os.path.relpath(p, root)
            if any(rel == e or rel.startswith(e.rstrip("/") + "/") for e in exclude):
                continue
            out[rel] = sha256(p)
    return out


def differences(a, b):
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def copy_block(skill_md_text):
    """The always-copied skill names and the removed paths of new-website's §3 step 3 cp block."""
    names = re.findall(r'^\s*(?:cp -RL\s+)?"\$SKILLS_ROOT"/([A-Za-z0-9._-]+)\s*\\\s*$', skill_md_text, re.M)
    removed = re.findall(r'^\s*rm -rf "\$PROJECT_SKILLS_DIR"/(\S+)\s*$', skill_md_text, re.M)
    return names, removed


def deny_rules():
    """Which of git commit and rm the agy CLI settings deny."""
    try:
        with open(AGY_SETTINGS) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {"git commit": False, "rm": False}
    found = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "deny" and isinstance(v, list):
                    found.extend(str(i) for i in v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for i in x:
                walk(i)
    walk(data)
    return {"git commit": "command(git commit)" in found, "rm": "command(rm)" in found}


# ---------------------------------------------------------------- preflight


def check_release(zip_path, sha, work):
    """Exit 4 unless the zip matches SHA256SUMS and its skills/ equals skills/ at sha."""
    sums = os.path.join(os.path.dirname(zip_path), "SHA256SUMS")
    want = None
    try:
        for line in open(sums):
            m = re.match(r"^([0-9a-f]{64}) [ *](.+)$", line.strip())
            if m and m.group(2) == os.path.basename(zip_path):
                want = m.group(1)
    except OSError:
        raise Stop(4, "no SHA256SUMS next to the zip: %s" % sums)
    digest = sha256(zip_path)
    if want != digest:
        raise Stop(4, "the zip does not match SHA256SUMS (%s)" % ("no line for it" if want is None else "checksum differs"))
    release = os.path.join(work, "release")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(release)
    archived = os.path.join(work, "archived")
    os.makedirs(archived)
    with tarfile.open(fileobj=io.BytesIO(git("archive", sha, "skills"))) as t:
        try:
            t.extractall(archived, filter="data")
        except TypeError:  # a Python without extraction filters (before 3.9.17)
            t.extractall(archived)
    diff = differences(tree(os.path.join(release, "skills")), tree(os.path.join(archived, "skills")))
    if diff:
        raise Stop(4, "the zip's skills/ is not skills/ at %s: %s" % (sha, ", ".join(diff[:5])))
    return release, digest


def pick_depth(args):
    if not args.auto:
        return ("full" if args.full else "short"), "chosen with --%s" % ("full" if args.full else "short")
    changed = git("diff", "--name-only", "%s..%s" % (args.since, args.sha)).decode().split()
    hits = [p for p in changed if any(p == w or (w.endswith("/") and p.startswith(w)) for w in WATCHED)]
    if hits:
        return "full", "%s..%s changes %d watched file(s), e.g. %s" % (args.since, args.sha, len(hits), hits[0])
    return "short", "%s..%s changes no watched file" % (args.since, args.sha)


# ---------------------------------------------------------------- the run


def turns(depth, websites):
    t = ["new website\n\n(Before anything else, tell me the full path of the new-website SKILL.md file you loaded.)"]
    if depth == "full":
        t.append(
            "This is an unattended compatibility test of the Croftweaver suite under Antigravity; nobody "
            "is watching, so do not wait for replies. Answers to everything you would ask:\n\n"
            "- Websites folder: yes, %s is my websites folder. Create the site in a new folder there "
            "called linden-bakery.\n"
            "- Use the workspace install: run from the websites folder, export "
            "SKILLS_ROOT=\"$PWD/.agents/skills\" and PROJECT_SKILLS_DIR=.agents/skills before step 0.\n"
            "- Skip pipeline steps 1-4 (research, positioning, story, colours, content guide, site "
            "architecture), and decline the story-layer and colours/logo offers. Use placeholder copy.\n"
            "- Q1: a handful of fixed pages (home, about, contact, imprint, privacy). Plain pages, no collections.\n"
            "- Q2: visitors only read; contact is an email link. Tier 1 static.\n"
            "- Q3: the owner edits files in git. No CMS.\n"
            "- Q4: one language. Q4a: English. Keep locale 'en'.\n"
            "- Q5: no analytics; Google Search Console later. Leave USE_ANALYTICS = false.\n"
            "- Q6: a new domain, linden-bakery.example. Two-stage publish model.\n"
            "- No GitHub repo and no Cloudflare: do not push, add remotes, create repositories or "
            "deploy. Work only inside the websites folder.\n\n"
            "Do this now: the section 3 scaffold, steps 0 to 3, then the green baseline: npm install, "
            "npm run build, npm test. If a step fails, say exactly what failed and carry on with the "
            "next one. Stop after npm test. Finish with: the full path of the new site (pwd inside "
            "it), every command that failed with its error, and whether .claude/settings.json was "
            "copied." % websites)
        t.append("Carry on with what you were told above, without asking anything more. If you are "
                 "finished, give the final summary I asked for.")
    return t


def run_group(cmd, cwd, stdin_path, stdout_path, stderr_path, deadline):
    """Run cmd in its own process group; kill the whole group at the deadline."""
    with open(stdin_path, "rb") if stdin_path else open(os.devnull, "rb") as i, \
            open(stdout_path, "wb") as o, open(stderr_path, "wb") as e:
        p = subprocess.Popen(cmd, cwd=cwd, stdin=i, stdout=o, stderr=e, start_new_session=True)
        try:
            return p.wait(timeout=deadline)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
            p.wait()
            return None


def usage_text(agy, cwd):
    try:
        r = subprocess.run([agy, "-p", "/usage"], cwd=cwd, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        return "unknown (/usage timed out)"
    return (r.stdout + r.stderr).decode(errors="replace").strip()


def parse(transcript):
    """Results in order, and every tool step in the order first seen, with its last state."""
    results, tools = [], {}
    with open(transcript, errors="replace") as f:
        for line in f:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("event") == "result":
                results.append(ev.get("result") or {})
            su = ev.get("step_update")
            if ev.get("event") == "step_update" and isinstance(su, dict) and su.get("step_type") == "tool":
                key = (su.get("conversation_id"), su.get("step_index"))
                tools[key] = su
    return results, list(tools.values())  # first-seen order; each step holds its last state


def tool_param(step, name):
    info = step.get("tool_info") or {}
    return str((info.get("parameters") or {}).get(name, ""))


def tool_output(step):
    info = step.get("tool_info") or {}
    return str(info.get("output", "")) + (json.dumps(info["error"]) if info.get("error") else "")


# ---------------------------------------------------------------- checks


def check_discovery(results, tools, ws_skill):
    seen = set()
    for s in tools:
        p = tool_param(s, "AbsolutePath")
        if s.get("tool_name") == "view_file" and s.get("state") == "DONE" and p.endswith("/new-website/SKILL.md"):
            seen.add(p)
    reply = (results[0].get("response") or "") if results else ""
    for p in re.findall(r"(?:file://)?(/[^\s`'\"()\[\]]*?/new-website/SKILL\.md)", reply):
        seen.add(p)
    shell = [tool_param(s, "CommandLine") for s in tools
             if s.get("tool_name") == "run_command" and ".gemini/config/skills" in tool_param(s, "CommandLine")]
    real = os.path.realpath(ws_skill)
    other = sorted(p for p in seen if os.path.realpath(p) != real)
    read = any(s.get("tool_name") == "view_file" and s.get("state") == "DONE"
               and os.path.realpath(tool_param(s, "AbsolutePath")) == real for s in tools)
    ok = read and not other and not shell
    detail = "read %s" % (", ".join(sorted(seen)) or "no new-website/SKILL.md")
    if shell:
        detail += "; a shell command named .gemini/config/skills"
    if not read:
        detail += "; no successful read of the workspace copy"
    return ok, detail


TOPICS = {"pages": r"page|sitemap", "server": r"tier|server|backend|static|dynamic",
          "editing": r"edit|cms", "language": r"language", "analytics": r"analytic|search console|plausible",
          "domain": r"domain|publish"}


def check_interview(results):
    """The interview has started: turn 1 succeeded and one of its questions is on an interview topic."""
    if not results or results[0].get("status") != "SUCCESS":
        return False, "turn 1 did not succeed"
    reply = (results[0].get("response") or "").lower()
    questions = re.findall(r"[^?.!\n]*\?", reply)
    found = [k for k, rx in TOPICS.items() if any(re.search(rx, q) for q in questions)]
    return bool(found), "%d of 6 interview topics asked about (%s)" % (len(found), ", ".join(found) or "none")


def check_scaffold(websites, release, since):
    """The site folder, its root files and its skills; returns (ok, detail, site, deviations)."""
    entries = sorted(e for e in os.listdir(websites) if e != ".agents")
    if len(entries) != 1 or not os.path.isdir(os.path.join(websites, entries[0])):
        return False, "the websites folder holds %s, not one new folder" % (entries or "nothing"), None, []
    site = os.path.join(websites, entries[0])
    problems, deviations = [], []
    problems += ["%s missing" % f for f in ROOT_FILES if not os.path.isfile(os.path.join(site, f))]
    names, removed = copy_block(open(os.path.join(release, "skills", "new-website", "SKILL.md")).read())
    rel_skills = os.path.join(release, "skills")
    if not names:
        problems.append("no skill name read from new-website's cp block")
    for n in names:
        src, dst = os.path.join(rel_skills, n), os.path.join(site, ".agents", "skills", n)
        if not os.path.isdir(src):
            problems.append("cp block names %s, which the zip lacks" % n)
        elif not os.path.isdir(dst):
            problems.append("%s not copied" % n)
        else:
            excl = [r[len(n) + 1:] for r in removed if r.startswith(n + "/")]
            diff = differences(tree(src, excl), tree(dst))
            if diff:
                problems.append("%s differs from the release (%s)" % (n, ", ".join(diff[:3])))
    bundled = os.path.join(site, ".agents", "skills")
    extra = sorted(d for d in (os.listdir(bundled) if os.path.isdir(bundled) else [])
                   if os.path.isdir(os.path.join(bundled, d)) and d not in names)
    if extra:
        deviations.append("skill folders not in the cp block: %s" % ", ".join(extra))
    if since:
        try:
            old, _ = copy_block(git("show", "%s:skills/new-website/SKILL.md" % since).decode())
            gone = sorted(set(old) - set(names))
            if gone:
                deviations.append("names the cp block had at %s and lacks now (confirm by hand): %s" % (since, ", ".join(gone)))
        except Stop:
            deviations.append("could not read the cp block at %s" % since)
    detail = "%d skills checked against the release" % len(names)
    return not problems, detail + ("; " + "; ".join(problems) if problems else ""), site, deviations


def pages_lines(text):
    """The stripped lines inside tests/_helpers.ts's PAGES array (None when there is none)."""
    m = re.search(r"export const PAGES\s*=\s*\[(.*?)\]", text, re.S)
    return [l.strip() for l in m.group(1).splitlines() if l.strip()] if m else None


def required_pages(text):
    """Template PAGES lines a site must keep unchanged: not comments, not marked to delete."""
    return [l for l in pages_lines(text) or [] if not l.startswith("//") and "delete" not in l]


def check_untouched(site, release):
    """Files the test relies on must be the template's; returns the list of changes."""
    tpl = os.path.join(release, "skills", "new-website", "templates", "astro")
    changes = []
    try:
        a = json.load(open(os.path.join(site, "package.json")))
        b = json.load(open(os.path.join(tpl, "package.json")))
        for k in ("scripts", "dependencies", "devDependencies"):
            if a.get(k) != b.get(k):
                changes.append("package.json %s" % k)
    except (OSError, ValueError) as e:
        changes.append("package.json unreadable (%s)" % e)
    for f in ("playwright.config.ts",):
        if not os.path.isfile(os.path.join(site, f)) or sha256(os.path.join(site, f)) != sha256(os.path.join(tpl, f)):
            changes.append(f)
    specs = lambda d: sorted(x for x in os.listdir(d) if x.endswith(".spec.ts")) if os.path.isdir(d) else []
    st, tt = specs(os.path.join(site, "tests")), specs(os.path.join(tpl, "tests"))
    if st != tt:
        changes.append("spec files differ in name (%s)" % ", ".join(sorted(set(st) ^ set(tt))))
    for x in tt:
        p = os.path.join(site, "tests", x)
        if os.path.isfile(p) and sha256(p) != sha256(os.path.join(tpl, "tests", x)):
            changes.append("tests/" + x)
    try:
        sh, th = open(os.path.join(site, "tests", "_helpers.ts")).read(), open(os.path.join(tpl, "tests", "_helpers.ts")).read()
        strip = lambda t: re.sub(r"export const PAGES\s*=\s*\[.*?\]", "", t, count=1, flags=re.S)
        if strip(sh) != strip(th):
            changes.append("tests/_helpers.ts outside PAGES")
        site_lines = pages_lines(sh) or []
        missing = [l for l in required_pages(th) if l not in site_lines]
        if pages_lines(sh) is None or missing:
            changes.append("tests/_helpers.ts PAGES lacks or changed: %s" % (", ".join(missing) or "the whole list"))
    except OSError:
        changes.append("tests/_helpers.ts missing")
    return changes


def first_npm_test(tools):
    """agy's first finished npm test: it passed when it reports passes and no failures."""
    for s in tools:
        cmd = tool_param(s, "CommandLine")
        if s.get("tool_name") != "run_command" or "deny rule" in tool_output(s):
            continue
        if not re.search(r"(?:^|&&|;|\|\||\n)\s*(?:npm (?:run )?test|npx playwright test)\b", cmd):
            continue
        if s.get("state") not in ("DONE", "ERROR"):
            return False, "agy's first npm test did not finish (%s)" % s.get("state")
        out = tool_output(s)
        failed = sum(int(n) for n in re.findall(r"\b(\d+) failed\b", out))
        passed = sum(int(n) for n in re.findall(r"\b(\d+) passed\b", out))
        if s.get("state") == "DONE" and not failed and passed:
            return True, "agy's first npm test passed"
        return False, "agy's first npm test failed (%s)" % ("%d failed" % failed if failed else "no passing summary")
    return False, "agy never ran npm test"


def workarounds(tools):
    return [tool_param(s, "CommandLine")[:160] or s.get("tool_name", "?") for s in tools
            if s.get("state") == "ERROR" and "deny rule" not in tool_output(s)]


def npm_runs(site, staging):
    for step, cmd in (("install", ["npm", "install"]), ("build", ["npm", "run", "build"]), ("test", ["npm", "test"])):
        log = os.path.join(staging, "npm-%s.txt" % step)
        rc = run_group(cmd, site, None, log, log + ".err", NPM_DEADLINE)
        if rc != 0:
            tail = open(log, errors="replace").read()[-1500:] + open(log + ".err", errors="replace").read()[-500:]
            return False, "npm %s %s" % (step, "timed out" if rc is None else "exit %d" % rc), tail
    out = open(os.path.join(staging, "npm-test.txt"), errors="replace").read()
    summary = ", ".join(re.findall(r"\b\d+ (?:passed|failed|skipped)\b", out)) or "exit 0"
    return True, "build exit 0; npm test %s" % summary, ""


def leftovers(root):
    """Kill processes whose working folder is inside root; return what was found."""
    try:
        r = subprocess.run(["lsof", "-d", "cwd", "-Fpn"], capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return ["not checked (lsof failed)"]
    found, pid = [], None
    for line in r.stdout.decode(errors="replace").splitlines():
        if line.startswith("p"):
            pid = int(line[1:])
        elif line.startswith("n") and len(line) > 1 and pid and pid != os.getpid():
            base, cwd = os.path.realpath(root), os.path.realpath(line[1:])
            if os.path.commonpath([base, cwd]) == base:
                found.append(pid)
    for p in found:
        try:
            os.kill(p, signal.SIGKILL)
        except OSError:
            pass
    return found


def scan_secrets(folder):
    hits = []
    for rel in tree(folder):
        with open(os.path.join(folder, rel), errors="replace") as f:
            if SECRET.search(f.read()):
                hits.append(rel)
    return hits


# ---------------------------------------------------------------- main


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--zip", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--out", required=True)
    depth = ap.add_mutually_exclusive_group(required=True)
    depth.add_argument("--short", action="store_true")
    depth.add_argument("--full", action="store_true")
    depth.add_argument("--auto", action="store_true")
    ap.add_argument("--since")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--yes-spend-agy-credits", action="store_true")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args(argv)
    if args.auto and not args.since:
        ap.error("--auto needs --since <tag>")
    if not (args.dry_run or args.yes_spend_agy_credits):
        raise Stop(2, "refused: pass --dry-run, or --yes-spend-agy-credits once the run is approved")
    agy = shutil.which("agy")
    if not agy:
        raise Stop(2, "agy is not on PATH")
    out = os.path.abspath(args.out)
    if os.path.exists(out) and (not os.path.isdir(out) or os.listdir(out)):
        raise Stop(2, "--out must be a new or empty folder: %s" % out)
    sha = git("rev-parse", "--verify", args.sha + "^{commit}").decode().strip()
    args.sha = sha

    check = tempfile.mkdtemp(prefix="agy-release-check.")
    try:
        release, digest = check_release(os.path.abspath(args.zip), sha, check)
        level, why = pick_depth(args)
        version = subprocess.run([agy, "--version"], capture_output=True).stdout.decode(errors="replace").strip()
        deny = deny_rules()
        global_note = "none"
        if os.path.isfile(GLOBAL_NEW_WEBSITE):
            same = sha256(GLOBAL_NEW_WEBSITE) == sha256(os.path.join(release, "skills", "new-website", "SKILL.md"))
            global_note = "present, %s the release's new-website/SKILL.md" % ("same as" if same else "differs from")
        say("depth: %s (%s)" % (level, why))
        say("agy version: %s (%s)" % (version or "unknown", "tested" if version == TESTED_AGY_VERSION else "differs from the tested %s" % TESTED_AGY_VERSION))
        say("deny rules: git commit %s, rm %s" % ("denied" if deny["git commit"] else "NOT denied", "denied" if deny["rm"] else "NOT denied"))
        say("global copy: %s" % global_note)
        if args.dry_run:
            return 0
        try:
            os.mkdir(LOCK)
        except FileExistsError:
            raise Stop(2, "another release test is running (lock %s; remove it if none is)" % LOCK)
        try:
            return run(args, agy, level, why, version, deny, global_note, release, digest, out)
        finally:
            os.rmdir(LOCK)
    finally:
        shutil.rmtree(check, ignore_errors=True)


def run(args, agy, level, why, version, deny, global_note, release_src, digest, out):
    root = tempfile.mkdtemp(prefix="Croftweaver-agy-test.", dir=HOME)
    websites = os.path.join(root, "websites")
    staging = os.path.join(root, "out")
    os.makedirs(os.path.join(websites, ".agents"))
    os.makedirs(staging)
    release = os.path.join(root, "release")
    shutil.copytree(release_src, release)
    shutil.copytree(os.path.join(release, "skills"), os.path.join(websites, ".agents", "skills"))
    ws_skill = os.path.join(websites, ".agents", "skills", "new-website", "SKILL.md")

    sent = turns(level, websites)
    with open(os.path.join(staging, "turns.ndjson"), "w") as f:
        for t in sent:
            f.write(json.dumps({"event": "user", "message": {"role": "user", "content": t}}) + "\n")
    before = usage_text(agy, websites)
    cmd = [agy, "-p=", "--input-format", "stream-json", "--output-format", "stream-json",
           "--model", args.model, "--dangerously-skip-permissions", "--new-project",
           "--print-timeout", PRINT_TIMEOUT[level]] + (["--sandbox"] if level == "short" else [])
    deadline = (5 if level == "short" else 30) * 60 + 300
    transcript = os.path.join(staging, "transcript.ndjson")
    rc = run_group(cmd, websites, os.path.join(staging, "turns.ndjson"), transcript,
                   os.path.join(staging, "agy-stderr.txt"), deadline)
    after = usage_text(agy, websites)
    results, tools = parse(transcript)
    succeeded = sum(1 for r in results if r.get("status") == "SUCCESS")

    lines, fails, code = [], [], 0
    if succeeded == 0 and not tools:
        err = ([r.get("error") for r in results if r.get("error")] or [open(os.path.join(staging, "agy-stderr.txt"), errors="replace").read().strip()[-300:]])[-1]
        code, lines = 3, ["Not run: %s" % (err or "agy exit %s" % rc)]
    else:
        lines.append("1. Install (all skill folders):    PASS — zip matches SHA256SUMS; skills/ identical to git archive %s" % args.sha)
        ok, d = check_discovery(results, tools, ws_skill)
        lines.append("2. Discovery (sees new-website):   %s — %s" % ("PASS" if ok else "FAIL", d))
        fails += [] if ok else ["discovery"]
        site = None
        if level == "full":
            ok_s, d_s, site, deviations = check_scaffold(websites, release, args.since)
            lines.append("3. $SKILLS_ROOT resolved to:       %s (the site's skills %s the release's; the copy's source is not claimed)"
                         % (websites + "/.agents/skills", "match" if ok_s else "do not all match"))
        else:
            lines.append("3. $SKILLS_ROOT resolved to:       not run (short check)")
        ok, d = check_interview(results)
        lines.append("4. \"new website\" starts interview: %s — %s" % ("PASS" if ok else "FAIL", d))
        fails += [] if ok else ["interview"]
        if level == "full":
            lines.append("5. Scaffold cp paths (no errors):  %s — %s" % ("PASS" if ok_s else "FAIL", d_s))
            fails += [] if ok_s else ["scaffold"]
            changed = check_untouched(site, release) if site else []
            if not site:
                lines.append("6. Generated site build + tests:   FAIL — no site to test")
                fails.append("build/tests")
            elif changed:
                code = 5
                lines.append("6. Generated site build + tests:   NOT TRUSTED — agy changed: %s" % "; ".join(changed))
            else:
                ok_n, d_n, tail = npm_runs(site, staging)
                lines.append("6. Generated site build + tests:   %s — %s" % ("PASS" if ok_n else "FAIL", d_n))
                if tail:
                    lines += ["   | " + t for t in tail.strip().splitlines()[-8:]]
                fails += [] if ok_n else ["build/tests"]
            ok_f, d_f = first_npm_test(tools)
            lines.append("   Green from the first try:       %s — %s" % ("PASS" if ok_f else "FAIL", d_f))
            fails += [] if ok_f else ["first try"]
            perm = site and not os.path.exists(os.path.join(site, ".claude", "settings.json"))
            lines.append("   Permissions sanity:             %s — .claude/settings.json %s; website-permissions not tested"
                         % ("PASS" if perm else "FAIL", "not copied" if perm else "copied"))
            fails += [] if perm else ["permissions"]
            g = subprocess.run(["git", "-C", site or root, "rev-parse", "--show-toplevel"], capture_output=True)
            n = subprocess.run(["git", "-C", site or root, "rev-list", "--count", "HEAD"], capture_output=True)
            unborn = n.returncode != 0 and re.search(r"ambiguous argument 'HEAD'|unknown revision", n.stderr.decode())
            count = n.stdout.decode().strip() if n.returncode == 0 else "0"
            if not site or g.returncode != 0 or os.path.realpath(g.stdout.decode().strip()) != os.path.realpath(site):
                commit = "FAIL — the site is not a git repository"
                fails.append("git")
            elif n.returncode != 0 and not unborn:
                commit = "FAIL — could not count commits (%s)" % n.stderr.decode().strip()[:120]
                fails.append("git")
            elif count == "0" and deny["git commit"]:
                commit = "not tested (deny rule: git commit)"
            else:
                commit = "%s commit(s)" % count
            lines.append("   Commit:                         %s" % commit)
            for dv in deviations:
                lines.append("   Deviation:                      %s" % dv)
        else:
            lines += ["5. Scaffold cp paths (no errors):  not run (short check)",
                      "6. Generated site build + tests:   not run (short check)"]
        sub = any(s.get("tool_name") in ("invoke_subagent", "browser_subagent") for s in tools)
        lines.append("7. Subagents (async research/seo): %s" % ("YES" if sub else "NO"))
        for w in workarounds(tools):
            lines.append("   Command that failed:            %s" % w)
        if succeeded < len(sent) or rc != 0:
            fails.append("agy %d of %d turns, %s" % (succeeded, len(sent), "timed out" if rc is None else "exit %s" % rc))
            how = "timed out" if rc is None else "exit %s" % rc
            if succeeded < len(sent):
                lines.append("   agy stopped after %d of %d turns (%s)" % (succeeded, len(sent), how))
            else:
                lines.append("   agy finished all %d turns but ended with %s" % (len(sent), how))
        if code == 0 and fails:
            code = 1

    killed = leftovers(root)
    usage = (results[-1].get("usage") or {}) if results else {}
    report = ["# Antigravity test, %s check" % level, "",
              "Release zip SHA-256: %s, commit %s. Depth: %s (%s)." % (digest, args.sha, level, why), "",
              "```", "Antigravity version: agy %s (%s)%s" % (version, args.model,
                                                          "" if version == TESTED_AGY_VERSION else " — differs from the tested %s" % TESTED_AGY_VERSION)]
    report += lines + ["```", "",
                       "Global copy in ~/.gemini/config/skills: %s." % global_note,
                       "Allowance before: %s" % before.replace("\n", "; "),
                       "Allowance after: %s" % after.replace("\n", "; "),
                       "agy's token count (running total): %s" % (json.dumps(usage) if usage else "none"),
                       "Processes left in the test folder and killed: %s" % (killed or "none"),
                       "Test folder: %s (%s)" % (root, "deleted" if code == 0 and not args.keep else "kept"),
                       "", "Exit %d: %s%s." % (code, EXIT_TEXT[code], (" (" + ", ".join(fails) + ")") if fails else "")]
    with open(os.path.join(staging, "REPORT.md"), "w") as f:
        f.write("\n".join(report) + "\n")
    hits = scan_secrets(staging)
    if hits:
        raise Stop(2, "possible secret in %s; nothing copied to --out (staging kept in %s)" % (", ".join(hits), staging))
    os.makedirs(out, exist_ok=True)
    for rel in tree(staging):
        dst = os.path.join(out, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(staging, rel), dst)
    say("\n".join(report))
    if code == 0 and not args.keep and os.path.basename(root).startswith("Croftweaver-agy-test."):
        shutil.rmtree(root, ignore_errors=True)
    return code


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Stop as s:
        print("%s (exit %d: %s)" % (s, s.code, EXIT_TEXT[s.code]), file=sys.stderr)
        sys.exit(s.code)
