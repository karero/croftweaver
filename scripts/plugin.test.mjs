// Tests for the Claude Code plugin (.claude-plugin/) and for what makes the skills work
// from a plugin's folder: no skill may send the assistant to ~/.claude/skills/<name>/ for
// its files, because a plugin's skills are not there. Run: make test-plugin (needs node 20
// or newer, git and bash).
//
// Claude Code puts a skill's own folder in place of the name CLAUDE_SKILL_DIR in braces,
// in SKILL.md only. Other assistants leave it as written. The cases below hold both.
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { after, test } from 'node:test';
import { fileURLToPath } from 'node:url';

const REPO = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const VAR = '${CLAUDE_SKILL_DIR}';
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const scratch = [];
after(() => { for (const dir of scratch) fs.rmSync(dir, { recursive: true, force: true }); });

// Every tracked text file under skills/, whatever its name, as [path, content].
function skillFiles() {
  return execFileSync('git', ['ls-files', '-z', 'skills'], { cwd: REPO, encoding: 'utf8' })
    .split('\0').filter(Boolean)
    .map((file) => [file, fs.readFileSync(path.join(REPO, file))])
    .filter(([, data]) => !data.includes(0))
    .map(([file, data]) => [file, data.toString('utf8')]);
}

test('the plugin and the marketplace entry name the same plugin, and the entry installs releases', () => {
  const plugin = JSON.parse(read('.claude-plugin', 'plugin.json'));
  const market = JSON.parse(read('.claude-plugin', 'marketplace.json'));
  assert.equal(plugin.name, 'croftweaver');
  assert.equal(market.plugins.length, 1);
  const [entry] = market.plugins;
  // Installing is by entry name, the skills' prefix is the plugin's: they must not differ.
  assert.equal(entry.name, plugin.name);
  assert.deepEqual({ source: entry.source.source, repo: entry.source.repo }, { source: 'github', repo: 'karero/croftweaver' });
  // Users get releases, not main: the entry installs from the branch `stable`, which a
  // release moves to its tag once the tag exists. main therefore never names something
  // that is not there yet. The plugin carries the release's number (0.32 is 0.32.0), which
  // is what tells Claude Code that there is an update.
  assert.equal(entry.source.ref, 'stable');
  assert.match(plugin.version, /^\d+\.\d+\.0$/);
  // Set in one place only: with both, Claude Code takes plugin.json's without a word.
  assert.equal(entry.version, undefined);
});

// Nothing on a pull request can tell that a release forgot to raise the number: the last
// one is as well-formed as the next. The release-tag workflow runs this with the tag a
// release pushed, and with the tag `stable` was moved to.
test('the plugin carries the number of the release it is in',
  { skip: process.env.RELEASE_TAG ? false : 'no RELEASE_TAG: this runs when a release tag is pushed or stable moves' }, () => {
    const plugin = JSON.parse(read('.claude-plugin', 'plugin.json'));
    assert.equal(`v${plugin.version.replace(/\.0$/, '')}`, process.env.RELEASE_TAG);
  });

test('no file of a skill sends the reader to the home skills folder for a skill\'s files', () => {
  const found = [];
  for (const [file, text] of skillFiles()) {
    text.split('\n').forEach((line, i) => {
      // The folder followed by a path: also behind the closing brace of a default, as in
      // "${SKILLS_ROOT:-$HOME/.claude/skills}/name".
      if (/(~|\$\{?HOME\}?)\/\.(claude|agents|gemini\/config)\/skills\}?\//.test(line)) found.push(`${file}:${i + 1}: ${line.trim().slice(0, 100)}`);
    });
  }
  assert.deepEqual(found, [], 'a plugin\'s skills are not in that folder: name the file relative to the skill ("this skill\'s templates/…")');
});

test('the name Claude Code fills in stands only where it is filled in, and every path built on it exists', () => {
  const misplaced = [];
  const missing = [];
  for (const [file, text] of skillFiles()) {
    if (!text.includes(VAR)) continue;
    // Only a skill's SKILL.md is rewritten: anywhere else the name would reach the reader as it is.
    if (!/^skills\/[^/]+\/SKILL\.md$/.test(file)) { misplaced.push(file); continue; }
    const skillDir = path.join(REPO, path.dirname(file));
    // The path runs to the next quote, backtick, bracket or space.
    for (const [, rest] of text.matchAll(/\$\{CLAUDE_SKILL_DIR\}([^\s"'`)]*)/g)) {
      if (!fs.existsSync(path.join(skillDir, rest))) missing.push(`${file}: ${VAR}${rest}`);
    }
  }
  assert.deepEqual(misplaced, []);
  assert.deepEqual(missing, []);
});

// Lines of a SKILL.md from the one holding `first` to the one before the one holding `end`.
// Each marker must be there exactly once, so the test cannot run a different block.
function block(file, first, end) {
  const lines = read(...file).split('\n');
  const at = (marker) => {
    const hits = lines.map((line, i) => (line.includes(marker) ? i : -1)).filter((i) => i >= 0);
    assert.equal(hits.length, 1, `${file.join('/')}: ${JSON.stringify(marker)} is there ${hits.length} times`);
    return hits[0];
  };
  return lines.slice(at(first), at(end)).join('\n');
}

// The lines new-website tells the assistant to run to find the installed suite, taken from
// SKILL.md itself: from the SKILLS_ROOT test to the end of the PROJECT_SKILLS_DIR one.
const lookup = () => block(['skills', 'new-website', 'SKILL.md'], 'if [ -z "${SKILLS_ROOT:-}" ]; then', 'mkdir <site> && cd <site> && git init');

// Runs lines of a skill as an assistant would: `filled` is what stands in place of the name
// in braces (Claude Code), or null to leave the text as written (any other assistant).
// `strict` runs the lines with unset variables as errors. That is set in the script, not
// by `bash -u`: Debian's bash reads /etc/bash.bashrc when its input is a socket, as it is
// here on a CI runner, and that file itself trips over an unset PS1 under -u.
function bash(script, { filled, home, env = {}, cwd, strict = false }) {
  const text = `${strict ? 'set -u\n' : ''}${filled === null ? script : script.replaceAll(VAR, filled)}`;
  return spawnSync('bash', ['-c', text], { env: { PATH: process.env.PATH, HOME: home, ...env }, cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
}

function runLookup(options) {
  const run = bash(`${lookup()}\nprintf '%s\\n%s\\n' "$SKILLS_ROOT" "$PROJECT_SKILLS_DIR"\n`, options);
  assert.equal(run.status, 0, run.stderr);
  assert.equal(run.stderr, '');
  const [root, project] = run.stdout.trim().split('\n');
  return { root, project };
}

function tmp() {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'croftweaver-plugin-test-')));
  scratch.push(dir);
  return dir;
}

// A stand-in for an installed suite: the folders and the two files the cases need.
function suiteAt(skillsDir, mark = 'suite') {
  const claude = path.join(skillsDir, 'new-website', 'templates', 'claude');
  fs.mkdirSync(path.join(claude, 'hooks'), { recursive: true });
  fs.writeFileSync(path.join(claude, 'settings.json'), `settings from ${mark}`);
  fs.writeFileSync(path.join(claude, 'hooks', 'git-stand.mjs'), `hook from ${mark}`);
  fs.mkdirSync(path.join(skillsDir, 'website-permissions'), { recursive: true });
}

test('new-website finds the suite where it was loaded from: a plugin\'s folder, which is none of the home folders', () => {
  const home = tmp();
  const plugin = path.join(tmp(), 'plugins', 'cache', 'croftweaver', 'croftweaver', '0.32.0', 'skills');
  suiteAt(plugin);

  const found = runLookup({ filled: path.join(plugin, 'new-website'), home });

  assert.deepEqual(found, { root: plugin, project: '.claude/skills' });
});

test('the copy that is running wins over another install of the suite on the same computer', () => {
  const home = tmp();
  suiteAt(path.join(home, '.claude', 'skills'));
  // A folder name with a space and an apostrophe: both are common in "Documents" folders.
  const plugin = path.join(tmp(), "owner's suite", 'skills');
  suiteAt(plugin);

  assert.equal(runLookup({ filled: path.join(plugin, 'new-website'), home }).root, plugin);
  assert.equal(runLookup({ filled: path.join(plugin, 'new-website'), home, strict: true }).root, plugin);
});

test('an assistant that fills nothing in still finds its own install, and the unfilled name does no harm', () => {
  const home = tmp();
  suiteAt(path.join(home, '.agents', 'skills'));

  assert.deepEqual(runLookup({ filled: null, home }), { root: path.join(home, '.agents', 'skills'), project: '.agents/skills' });
  // Also in a shell that takes an unset variable as an error: the name must not be read as one.
  assert.deepEqual(runLookup({ filled: null, home, strict: true }), { root: path.join(home, '.agents', 'skills'), project: '.agents/skills' });

  // Claude Code's own folder still comes before the other two, as before.
  suiteAt(path.join(home, '.claude', 'skills'));
  assert.deepEqual(runLookup({ filled: null, home }), { root: path.join(home, '.claude', 'skills'), project: '.claude/skills' });
});

test('left as written, the name is an empty value, not an unset variable, and its candidate is passed over', () => {
  // Claude Code leaves the form with := alone (seen in a live session), so this line reaches
  // every assistant; without it a strict shell stops at the unset name.
  assert.ok(lookup().includes(': "${CLAUDE_SKILL_DIR:=}"\n'));
  // The candidate is in double quotes: a folder with an apostrophe in its name, filled in
  // between single quotes, ends the string early and the shell cannot read the line.
  assert.match(lookup(), /for d in "\$\{CLAUDE_SKILL_DIR\}\/\.\." "\$HOME\/\.claude\/skills"/);
  // Empty, the candidate is "/..", the root of the disk: without this test a folder
  // /new-website there would pass for the suite.
  assert.ok(lookup().includes('[ "$d" != /.. ] && [ -d "$d/new-website" ]'));
  assert.equal(lookup().split(VAR).length, 2, 'the name must stand in the lookup exactly once');
});

test('an explicit SKILLS_ROOT is honoured, and with nothing installed the default is unchanged', () => {
  const home = tmp();
  const plugin = path.join(tmp(), 'skills');
  suiteAt(plugin);

  assert.equal(runLookup({ filled: path.join(plugin, 'new-website'), home, env: { SKILLS_ROOT: '/somewhere/else' } }).root, '/somewhere/else');
  assert.equal(runLookup({ filled: null, home }).root, path.join(home, '.claude', 'skills'));
  assert.equal(runLookup({ filled: null, home, strict: true }).root, path.join(home, '.claude', 'skills'));
});

test('the two guides that repeat the lookup for testers repeat it as it is', () => {
  const loop = lookup().split('\n').filter((line) => /^\s*(: "\$\{CLAUDE_SKILL_DIR:=\}"|for d in|\[ "\$d" != \/\.\. \])/.test(line)).map((line) => line.trim());
  assert.equal(loop.length, 3);
  for (const guide of ['CODEX-TEST.md', 'ANTIGRAVITY-TEST.md']) {
    const lines = read('docs', guide).split('\n').map((line) => line.trim());
    for (const line of loop) assert.ok(lines.includes(line), `docs/${guide} lacks: ${line}`);
  }
});

// The lines website-permissions gives to copy the allowlist and its hook into a site.
const copySettings = () => block(['skills', 'website-permissions', 'SKILL.md'], ': "${CLAUDE_SKILL_DIR:=}"', 'If both `cp` lines fail');

function runCopy(options) {
  const site = tmp();
  const run = bash(copySettings().replace(/^```\s*$/m, ''), { cwd: site, ...options });
  const got = (file) => (fs.existsSync(path.join(site, file)) ? fs.readFileSync(path.join(site, file), 'utf8') : null);
  return { status: run.status, settings: got('.claude/settings.json'), hook: got('.claude/hooks/git-stand.mjs') };
}

test('website-permissions copies the allowlist from the suite it is part of', () => {
  const plugin = path.join(tmp(), 'cache', "owner's suite", 'skills');
  suiteAt(plugin, 'the plugin');

  const copied = runCopy({ filled: path.join(plugin, 'website-permissions'), home: tmp() });

  assert.deepEqual(copied, { status: 0, settings: 'settings from the plugin', hook: 'hook from the plugin' });
});

test('from the copy inside a site, which has no new-website beside it, it takes the installed suite', () => {
  const home = tmp();
  suiteAt(path.join(home, '.claude', 'skills'), 'the home install');
  const siteCopy = path.join(tmp(), '.claude', 'skills', 'website-permissions');
  fs.mkdirSync(siteCopy, { recursive: true });

  assert.deepEqual(runCopy({ filled: siteCopy, home }), { status: 0, settings: 'settings from the home install', hook: 'hook from the home install' });

  // And where SKILLS_ROOT says where the suite is, that one, in a strict shell too.
  const elsewhere = path.join(tmp(), 'skills');
  suiteAt(elsewhere, 'SKILLS_ROOT');
  for (const strict of [false, true]) {
    assert.deepEqual(runCopy({ filled: null, home, env: { SKILLS_ROOT: elsewhere }, strict }), { status: 0, settings: 'settings from SKILLS_ROOT', hook: 'hook from SKILLS_ROOT' });
  }
});

test('from a site\'s copy on a computer that has the suite only as a plugin, it takes the plugin\'s', () => {
  const home = tmp();
  const config = path.join(home, '.claude');
  suiteAt(path.join(config, 'plugins', 'cache', 'croftweaver', 'croftweaver', '0.32.0', 'skills'), 'the plugin cache');
  const siteCopy = path.join(tmp(), "Sam's Bakery", '.claude', 'skills', 'website-permissions');
  fs.mkdirSync(siteCopy, { recursive: true });

  for (const strict of [false, true]) {
    assert.deepEqual(runCopy({ filled: siteCopy, home, strict }), { status: 0, settings: 'settings from the plugin cache', hook: 'hook from the plugin cache' });
  }
  // The same where Claude Code's configuration folder is not the default one.
  const moved = path.join(tmp(), 'claude-config');
  suiteAt(path.join(moved, 'plugins', 'cache', 'croftweaver', 'croftweaver', '0.33.0', 'skills'), 'the moved config');
  assert.equal(runCopy({ filled: siteCopy, home: tmp(), env: { CLAUDE_CONFIG_DIR: moved } }).settings, 'settings from the moved config');
});

test('with no suite to copy from it fails, and writes neither file', () => {
  const copied = runCopy({ filled: null, home: tmp(), strict: true });

  assert.notEqual(copied.status, 0);
  assert.deepEqual([copied.settings, copied.hook], [null, null]);
});
