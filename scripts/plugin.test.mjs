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
  // By its full https address, not as "github" with owner/repo: that form is fetched over
  // SSH where it can, and Claude Code's documentation says an update does not fall back to
  // https, so a user without a GitHub key would never get one.
  assert.deepEqual({ source: entry.source.source, url: entry.source.url }, { source: 'url', url: 'https://github.com/karero/croftweaver.git' });
  // Users get releases, not main: the entry installs from the branch `stable`, which a
  // release moves to its tag once the tag exists. main therefore never names something
  // that is not there yet. The plugin carries the release's number (0.32 is 0.32.0), which
  // is what tells Claude Code that there is an update.
  assert.equal(entry.source.ref, 'stable');
  assert.match(plugin.version, /^\d+\.\d+\.0$/);
  // Set in one place only: with both, Claude Code takes plugin.json's without a word.
  assert.equal(entry.version, undefined);
});

// Codex reads its own marketplace file first, and the plugin's number from the same
// .claude-plugin/plugin.json as Claude Code (seen with Codex CLI 0.162.1). Its entry must
// install what Claude Code's installs: the same plugin, from the same address and branch.
test('the Codex marketplace offers the same plugin from the same place, with the fields Codex asks for', () => {
  const plugin = JSON.parse(read('.claude-plugin', 'plugin.json'));
  const claude = JSON.parse(read('.claude-plugin', 'marketplace.json'));
  const codex = JSON.parse(read('.agents', 'plugins', 'marketplace.json'));
  // Users install it as croftweaver@croftweaver in both.
  assert.equal(codex.name, claude.name);
  assert.equal(codex.plugins.length, 1);
  const [entry] = codex.plugins;
  assert.equal(entry.name, plugin.name);
  assert.deepEqual(entry.source, claude.plugins[0].source);
  // OpenAI's documentation says every entry carries these three. The CLI installed from the
  // Claude Code entry, which has none of them; the documentation is what asks.
  assert.deepEqual(entry.policy, { installation: 'AVAILABLE', authentication: 'ON_INSTALL' });
  assert.equal(typeof entry.category, 'string');
  // The number lives in plugin.json only, as for Claude Code.
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
// SKILL.md itself: from where Codex's folder is set to the end of the PROJECT_SKILLS_DIR test.
const lookup = () => block(['skills', 'new-website', 'SKILL.md'], 'codex_home="$(', 'mkdir <site> && cd <site> && git init');

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

// A stand-in for an installed suite: the folder the lookup tests for.
const suiteAt = (skillsDir) => fs.mkdirSync(path.join(skillsDir, 'new-website', 'templates'), { recursive: true });

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

// Codex fills nothing in, so a Codex plugin is found where Codex keeps it:
// <CODEX_HOME or ~/.codex>/plugins/cache/<marketplace>/<plugin>/<version>/skills. An update
// replaced the version folder (seen with Codex CLI 0.162.1); should there be more than one,
// the last by name is taken.
const codexPlugin = (codexHome, version = '0.32.0') => path.join(codexHome, 'plugins', 'cache', 'croftweaver', 'croftweaver', version, 'skills');

test('an assistant that fills nothing in finds the suite installed as a Codex plugin, and bundles for Codex', () => {
  const home = tmp();
  const plugin = codexPlugin(path.join(home, '.codex'));
  suiteAt(plugin);
  for (const strict of [false, true]) {
    assert.deepEqual(runLookup({ filled: null, home, strict }), { root: plugin, project: '.agents/skills' });
  }

  // CODEX_HOME moves Codex's folder: the lookup follows it, however it is written (slashes
  // at the end or doubled, relative to the folder the assistant runs in, an exported
  // CDPATH), none of which may send the site's skills to .claude/skills.
  const elsewhere = tmp();
  const moved = codexPlugin(path.join(elsewhere, 'codex home'));
  suiteAt(moved);
  const decoy = tmp();
  suiteAt(codexPlugin(path.join(decoy, 'codex home')));
  for (const codexHome of [path.join(elsewhere, 'codex home'), `${path.join(elsewhere, 'codex home')}/`, `${elsewhere}//codex home//`, 'codex home']) {
    const found = runLookup({ filled: null, home: tmp(), cwd: elsewhere, env: { CODEX_HOME: codexHome, CDPATH: decoy } });
    assert.deepEqual(found, { root: moved, project: '.agents/skills' }, codexHome);
  }

  // Two versions left behind: the last by name, whatever order the folder lists them in.
  const two = tmp();
  suiteAt(codexPlugin(path.join(two, '.codex'), '0.33.0'));
  suiteAt(codexPlugin(path.join(two, '.codex'), '0.32.0'));
  assert.equal(runLookup({ filled: null, home: two }).root, codexPlugin(path.join(two, '.codex'), '0.33.0'));

  // It comes last: a suite in one of the home folders still wins, as before.
  suiteAt(path.join(home, '.claude', 'skills'));
  assert.equal(runLookup({ filled: null, home }).root, path.join(home, '.claude', 'skills'));
  // And the copy that is running wins over it.
  const running = path.join(tmp(), 'skills');
  suiteAt(running);
  assert.equal(runLookup({ filled: path.join(running, 'new-website'), home }).root, running);
});

// On a Mac the shell may be zsh, for Claude Code and Codex alike. There a file pattern that
// matches nothing is an error that stops the command, so the lookup must not use one.
test('in zsh the lookup runs without an error, with and without a Codex plugin',
  { skip: spawnSync('zsh', ['-c', 'true']).status === 0 ? false : 'zsh is not installed here' }, () => {
    const zsh = (home) => spawnSync('zsh', ['-c', `${lookup()}\nprintf '%s\\n%s\\n' "$SKILLS_ROOT" "$PROJECT_SKILLS_DIR"\n`],
      { env: { PATH: process.env.PATH, HOME: home }, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    const empty = tmp();
    const none = zsh(empty);
    assert.deepEqual([none.status, none.stderr, none.stdout], [0, '', `${path.join(empty, '.claude', 'skills')}\n.claude/skills\n`]);
    const home = tmp();
    suiteAt(codexPlugin(path.join(home, '.codex')));
    const found = zsh(home);
    assert.deepEqual([found.status, found.stderr, found.stdout], [0, '', `${codexPlugin(path.join(home, '.codex'))}\n.agents/skills\n`]);
  });

// An assistant or a person may run the lines under `set -euo pipefail`. Before the Codex
// plugin the lookup passed there; a search that finds no Codex folder must not stop it,
// whether a candidate matches or none does.
test('under set -euo pipefail the lookup still runs to the end, in bash and in zsh', () => {
  const shells = ['bash', ...(spawnSync('zsh', ['-c', 'true']).status === 0 ? ['zsh'] : [])];
  const strict = (shell, home, filled) => spawnSync(shell, ['-c', `set -euo pipefail\n${filled === null ? lookup() : lookup().replaceAll(VAR, filled)}\nprintf '%s\\n' "$SKILLS_ROOT"\n`],
    { env: { PATH: process.env.PATH, HOME: home }, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  for (const shell of shells) {
    const running = path.join(tmp(), 'skills');
    suiteAt(running);
    const found = strict(shell, tmp(), path.join(running, 'new-website'));
    assert.deepEqual([found.status, found.stderr, found.stdout], [0, '', `${running}\n`], shell);
    const empty = tmp();
    const none = strict(shell, empty, null);
    assert.deepEqual([none.status, none.stderr, none.stdout], [0, '', `${path.join(empty, '.claude', 'skills')}\n`], shell);
  }
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
  const loop = lookup().split('\n').filter((line) => /^\s*(codex_home=|: "\$\{CLAUDE_SKILL_DIR:=\}"|codex_plugin=|for d in|\[ "\$d" != \/\.\. \])/.test(line)).map((line) => line.trim());
  assert.equal(loop.length, 5);
  for (const guide of ['CODEX-TEST.md', 'ANTIGRAVITY-TEST.md']) {
    const lines = read('docs', guide).split('\n').map((line) => line.trim());
    for (const line of loop) assert.ok(lines.includes(line), `docs/${guide} lacks: ${line}`);
  }
});

// The lines website-permissions gives to copy the allowlist and its hook into a site.
function copySettings() {
  const lines = read('skills', 'website-permissions', 'SKILL.md').split('\n');
  const hits = lines.map((line, i) => (line === ': "${CLAUDE_SKILL_DIR:=}"' ? i : -1)).filter((i) => i >= 0);
  assert.equal(hits.length, 1, 'the copy commands in website-permissions/SKILL.md were not found exactly once');
  const end = lines.findIndex((line, i) => i > hits[0] && line.startsWith('```'));
  return lines.slice(hits[0], end).join('\n');
}

test('website-permissions copies the allowlist and the hook from its own folder, wherever that is', () => {
  const own = (file) => read('skills', 'website-permissions', 'templates', 'claude', file);
  // A site carries a copy of this skill and no new-website beside it: "Sam's Bakery" stands
  // for a folder name with a space and an apostrophe.
  const siteCopy = path.join(tmp(), "Sam's Bakery", '.claude', 'skills', 'website-permissions');
  fs.cpSync(path.join(REPO, 'skills', 'website-permissions'), siteCopy, { recursive: true });

  for (const strict of [false, true]) {
    const site = tmp();
    const run = bash(copySettings(), { filled: siteCopy, home: tmp(), cwd: site, strict });
    assert.equal(run.status, 0, run.stderr);
    assert.equal(fs.readFileSync(path.join(site, '.claude', 'settings.json'), 'utf8'), own('settings.json'));
    assert.equal(fs.readFileSync(path.join(site, '.claude', 'hooks', 'git-stand.mjs'), 'utf8'), own('hooks/git-stand.mjs'));
  }
});

test('left as written, the copy fails for want of the files, not on an unset name, and writes nothing', () => {
  for (const strict of [false, true]) {
    const site = tmp();
    const run = bash(copySettings(), { filled: null, home: tmp(), cwd: site, strict });
    assert.notEqual(run.status, 0);
    assert.doesNotMatch(run.stderr, /unbound variable/);
    assert.ok(!fs.existsSync(path.join(site, '.claude', 'settings.json')) && !fs.existsSync(path.join(site, '.claude', 'hooks', 'git-stand.mjs')));
  }
});

test('the two files website-permissions carries are new-website\'s, byte for byte', () => {
  // They exist twice so that the skill needs nothing outside its own folder. The scaffold
  // installs new-website's; a site repaired from this skill must get the same.
  for (const file of [['settings.json'], ['hooks', 'git-stand.mjs']]) {
    const mine = fs.readFileSync(path.join(REPO, 'skills', 'website-permissions', 'templates', 'claude', ...file));
    const theirs = fs.readFileSync(path.join(REPO, 'skills', 'new-website', 'templates', 'claude', ...file));
    assert.ok(mine.equals(theirs), `${file.join('/')} differs between website-permissions and new-website`);
  }
});

test('the release steps in the README take the tag\'s name from the plugin\'s number', () => {
  const line = read('README.md').split('\n').filter((l) => l.startsWith('v="v$(node -p '));
  assert.equal(line.length, 1);
  const plugin = JSON.parse(read('.claude-plugin', 'plugin.json'));
  const out = execFileSync('bash', ['-c', `${line[0]}\nprintf '%s' "$v"`], { cwd: REPO, encoding: 'utf8' });
  assert.equal(out, `v${plugin.version.replace(/\.0$/, '')}`);
  assert.match(out, /^v\d+\.\d+$/);
});

// The release-tag workflow's two shell steps, taken from the workflow file itself: the lines
// under `run: |` of the step with that name.
function workflowStep(name) {
  const lines = read('.github', 'workflows', 'release-tag.yml').split('\n');
  const at = lines.findIndex((line) => line.trim() === `- name: ${name}`);
  assert.ok(at >= 0, `no step named ${JSON.stringify(name)} in release-tag.yml`);
  const run = lines.findIndex((line, i) => i > at && line.trim() === 'run: |');
  const next = lines.findIndex((line, i) => i > at && line.trimStart().startsWith('- '));
  assert.ok(run > at && (next < 0 || run < next), `the step ${JSON.stringify(name)} has no run block`);
  const body = [];
  for (const line of lines.slice(run + 1)) {
    if (line.trim() !== '' && !line.startsWith('          ')) break;
    body.push(line.slice(10));
  }
  return body.join('\n');
}

// A throwaway repository with a bare `origin`, as the workflow's checkout would have it.
function releaseRepo() {
  const dir = tmp();
  const origin = path.join(dir, 'origin.git');
  const work = path.join(dir, 'work');
  const env = { PATH: process.env.PATH, HOME: dir, GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_SYSTEM: '/dev/null',
    GIT_AUTHOR_NAME: 't', GIT_AUTHOR_EMAIL: 't@example.com', GIT_COMMITTER_NAME: 't', GIT_COMMITTER_EMAIL: 't@example.com' };
  const git = (...args) => execFileSync('git', args, { cwd: work, env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  fs.mkdirSync(work);
  execFileSync('git', ['init', '-q', '--bare', '-b', 'main', origin], { env });
  git('init', '-q', '-b', 'main');
  git('remote', 'add', 'origin', origin);
  const commit = (message) => { git('commit', '-q', '--allow-empty', '-m', message); return git('rev-parse', 'HEAD'); };
  const stable = () => execFileSync('git', ['--git-dir', origin, 'rev-parse', '-q', '--verify', 'refs/heads/stable'], { env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  const step = (name, vars) => {
    const out = path.join(dir, `output-${Math.random().toString(36).slice(2)}`);
    fs.writeFileSync(out, '');
    const run = spawnSync('bash', ['-c', `set -e\n${workflowStep(name)}`], { cwd: work, env: { ...env, GITHUB_OUTPUT: out, ...vars }, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    return { status: run.status, log: run.stdout + run.stderr, output: fs.readFileSync(out, 'utf8') };
  };
  return { git, commit, stable, step };
}

test('the workflow takes only a release\'s tag for a release', () => {
  const { commit, git, step } = releaseRepo();
  commit('release 0.32');
  git('tag', 'v0.32');
  const find = (vars) => step('Find the release this run is about', vars);

  assert.deepEqual([find({ PUSHED: 'tag', NAME: 'v0.32' }).status, find({ PUSHED: 'tag', NAME: 'v0.32' }).output], [0, 'tag=v0.32\n']);
  assert.equal(find({ PUSHED: 'tag', NAME: 'v10.2' }).output, 'tag=v10.2\n');
  // Not releases: the run ends well and does nothing, as the later steps ask for a tag.
  for (const name of ['v0.33-rc1', 'v1', 'v0.3.1', 'vnext', 'v0.32a']) {
    const found = find({ PUSHED: 'tag', NAME: name });
    assert.deepEqual([found.status, found.output], [0, 'tag=\n'], name);
    assert.match(found.log, /::notice::/);
  }
  // `stable` moved by hand: the commit has to be a release's. A trial tag beside the
  // release's does not count, here either.
  git('tag', 'v0.32-rc1');
  assert.equal(find({ PUSHED: 'branch', NAME: 'stable' }).output, 'tag=v0.32\n');
  commit('only a trial');
  git('tag', 'v0.33-rc1');
  const untagged = find({ PUSHED: 'branch', NAME: 'stable' });
  assert.equal(untagged.status, 1);
  assert.match(untagged.log, /::error::stable was moved to a commit that carries no release tag/);
  git('tag', 'v0.33');
  git('tag', 'v0.34');
  const two = find({ PUSHED: 'branch', NAME: 'stable' });
  assert.equal(two.status, 1);
  assert.match(two.log, /::error::the commit stable points at carries more than one release tag/);
});

test('the workflow moves stable to a release that is on main, forward only', () => {
  const { commit, git, stable, step } = releaseRepo();
  const move = (name) => step('Move stable to the release', { NAME: name });
  const first = commit('release 0.32');
  git('tag', '-a', 'v0.32', '-m', 'Croftweaver 0.32');
  // What the README's release steps rest on: a number that was not raised names this tag
  // again, and git does not make a tag that exists.
  assert.throws(() => git('tag', '-a', 'v0.32', '-m', 'Croftweaver 0.32'), /already exists/);
  git('push', '-q', 'origin', 'main', 'v0.32');

  // The first release creates the branch.
  git('checkout', '-q', 'v0.32');
  assert.equal(move('v0.32').status, 0);
  assert.equal(stable(), first);

  git('checkout', '-q', 'main');
  const second = commit('release 0.33');
  git('tag', 'v0.33');
  git('push', '-q', 'origin', 'main', 'v0.33');
  git('checkout', '-q', 'v0.33');
  assert.equal(move('v0.33').status, 0);
  assert.equal(stable(), second);

  // A tag on a commit that never reached main does not move it.
  git('checkout', '-q', '-b', 'side', 'v0.32');
  commit('a release cut from a side branch');
  git('tag', 'v0.34');
  const side = move('v0.34');
  assert.equal(side.status, 1);
  assert.match(side.log, /::error::v0\.34 is not on main: stable stays where it is/);
  assert.equal(stable(), second);

  // An older release pushed again does not move it back.
  git('checkout', '-q', 'v0.32');
  assert.notEqual(move('v0.32').status, 0);
  assert.equal(stable(), second);
});
