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
// here on a CI runner, and that file itself trips over an unset PS1 under -u. `errexit`
// adds `set -eo pipefail`; `shell` runs the lines in another shell (zsh) instead of bash.
function bash(script, { filled, home, env = {}, cwd, strict = false, errexit = false, shell = 'bash' }) {
  const text = `${errexit ? 'set -eo pipefail\n' : ''}${strict ? 'set -u\n' : ''}${filled === null ? script : script.replaceAll(VAR, filled)}`;
  return spawnSync(shell, ['-c', text], { env: { PATH: process.env.PATH, HOME: home, ...env }, cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
}

// The shells the lookup is run in: bash always, zsh where it is installed (a Mac's default).
const SHELLS = ['bash', ...(spawnSync('zsh', ['-c', 'true']).status === 0 ? ['zsh'] : [])];

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
  for (const shell of SHELLS) {
    for (const codexHome of [path.join(elsewhere, 'codex home'), `${path.join(elsewhere, 'codex home')}/`, `${elsewhere}//codex home//`, 'codex home']) {
      const found = runLookup({ filled: null, home: tmp(), cwd: elsewhere, env: { CODEX_HOME: codexHome, CDPATH: decoy }, shell });
      assert.deepEqual(found, { root: moved, project: '.agents/skills' }, `${shell}: ${codexHome}`);
    }
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
  const strict = (shell, home, filled) => bash(`${lookup()}\nprintf '%s\\n' "$SKILLS_ROOT"\n`, { filled, home, strict: true, errexit: true, shell });
  for (const shell of SHELLS) {
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

// --- The branch `directory`, which Anthropic's plugin directory follows ---------------------
// docs/reviews/SKILL-PLAN-directory-plugin-folder.md. The lists below are written here, not
// read from scripts/build_directory_tree.sh, so a wrong list in the script fails.
const DIRECTORY_FILES = ['.claude-plugin/icon.png', '.claude-plugin/plugin.json', '.gitattributes', 'LICENSE', 'README.md', 'SECURITY.md',
  'THIRD-PARTY-LICENSES.md', 'docs/CLOUDFLARE-CHECKLIST.md', 'docs/PAGES-OR-WORKERS.md', 'docs/WHAT-THE-SKILLS-RUN.md'];
const DIRECTORY_DROPS = ['skills/independent-review/', 'skills/facts-check/scripts/tests/', 'skills/new-website/scripts/tests/',
  'skills/search-console-insights/scripts/tests/', 'skills/website-brand-kit/scripts/tests/'];
const TEST_FOLDERS = DIRECTORY_DROPS.filter((d) => d.endsWith('/scripts/tests/')).map((d) => d.split('/')[1]);

const lsTree = (treeish) => execFileSync('git', ['ls-tree', '-r', '-z', treeish], { cwd: REPO, encoding: 'utf8' })
  .split('\0').filter(Boolean).map((entry) => { const [meta, file] = entry.split('\t'); return { meta, file }; });

let builtTree;
function directoryTree() {
  builtTree ??= execFileSync('bash', [path.join(REPO, 'scripts', 'build_directory_tree.sh'), 'HEAD'], { cwd: REPO, encoding: 'utf8' }).trim();
  return lsTree(builtTree);
}
const blobText = (meta) => execFileSync('git', ['cat-file', 'blob', meta.split(' ')[2]], { cwd: REPO, encoding: 'utf8', maxBuffer: 1 << 26 });

test('the directory tree is the plugin, its icon, the nine root files and nothing else, with the commit\'s own blobs', (t) => {
  const keep = ({ file }) => DIRECTORY_FILES.includes(file) || (file.startsWith('skills/') && !DIRECTORY_DROPS.some((d) => file.startsWith(d)));
  const expected = lsTree('HEAD').filter(keep).map(({ meta, file }) => `${meta}\t${file}`);
  const built = directoryTree().map(({ meta, file }) => `${meta}\t${file}`);
  assert.deepEqual(built, expected);
  for (const file of DIRECTORY_FILES) assert.ok(built.some((e) => e.endsWith(`\t${file}`)), `${file} is missing from HEAD`);
  // The checklist's reviewer-hold limits: a warning here, not a failure.
  const big = directoryTree().filter(({ meta, file }) => !/\.(png|jpe?g|gif|webp|woff2?|ttf|otf)$/i.test(file)
    && Number(execFileSync('git', ['cat-file', '-s', meta.split(' ')[2]], { cwd: REPO, encoding: 'utf8' })) > 256 * 1024);
  t.diagnostic(`directory: ${built.length} files (held for review above 512); non-image files over 256 KiB: ${big.map((b) => b.file).join(', ') || 'none'}`);
});

test('every path a kept SKILL.md builds on the name Claude Code fills in is in the directory tree', () => {
  const files = directoryTree().map(({ file }) => file);
  const has = (p) => files.includes(p) || files.some((f) => f.startsWith(`${p}/`));
  const missing = [];
  for (const { meta, file } of directoryTree()) {
    if (!/^skills\/[^/]+\/SKILL\.md$/.test(file)) continue;
    for (const [, rest] of blobText(meta).matchAll(/\$\{CLAUDE_SKILL_DIR\}([^\s"'`)]*)/g)) {
      const target = path.posix.normalize(`${path.posix.dirname(file)}/${rest}`).replace(/\/$/, '');
      if (!has(target)) missing.push(`${file}: ${VAR}${rest}`);
    }
  }
  assert.deepEqual(missing, []);
});

test('the directory\'s plugin.json declares no components, and no kept .gitattributes holds an attribute the checklist refuses', () => {
  const entry = directoryTree().find(({ file }) => file === '.claude-plugin/plugin.json');
  // Metadata only: a component path (commands, hooks, agents…) could point at a file the branch leaves out.
  const keys = Object.keys(JSON.parse(blobText(entry.meta)));
  assert.deepEqual(keys.filter((k) => !['name', 'displayName', 'version', 'description', 'author', 'homepage', 'repository', 'license', 'privacyPolicyUrl'].includes(k)), []);
  // The privacy link points at a heading the README has (GitHub's anchor: lower case, spaces to hyphens).
  const { privacyPolicyUrl } = JSON.parse(blobText(entry.meta));
  const anchor = new URL(privacyPolicyUrl).hash.slice(1);
  const headings = read('README.md').split('\n').filter((l) => l.startsWith('## ')).map((l) => l.slice(3).trim().toLowerCase().replace(/[^a-z0-9 -]/g, '').replace(/ /g, '-'));
  assert.ok(headings.includes(anchor), `README has no heading for #${anchor}`);
  for (const { meta, file } of directoryTree().filter(({ file }) => path.posix.basename(file) === '.gitattributes')) {
    assert.doesNotMatch(blobText(meta), /export-ignore|export-subst|filter/, file);
  }
});

// Lines of the kept files under skills/ (what an assistant follows) that name `needle`, as [file, line].
function keptLinesNaming(test) {
  const hits = [];
  for (const { meta, file } of directoryTree()) {
    if (!file.startsWith('skills/')) continue;
    const text = blobText(meta);
    if (text.includes('\0')) continue;
    for (const line of text.split('\n')) if (test(file, line)) hits.push([file, line]);
  }
  return hits;
}

test('the kept skills name no toolkit docs or scripts file the directory leaves out, except five known lines', () => {
  const inTree = new Set(directoryTree().map(({ file }) => file));
  const rootFiles = lsTree('HEAD').map(({ file }) => file)
    .filter((f) => (/^docs\/[^/]+\.md$/.test(f) || f.startsWith('scripts/')) && !inTree.has(f));
  const found = keptLinesNaming((file, line) => rootFiles.some((f) => line.includes(f)));
  // Each checked by hand: the whats-new lines run only behind an [ -f ] check (the next test
  // runs them without the script), the other two are comments.
  assert.deepEqual(found, [
    ['skills/new-website/SKILL.md', '   # The suite\'s scripts/whats-new.sh is the ONLY writer of the stamp format. Resolve'],
    ['skills/new-website/SKILL.md', '   if [ -n "$SUITE_REPO" ] && [ -f "$SUITE_REPO/scripts/whats-new.sh" ] \\'],
    ['skills/new-website/SKILL.md', '     bash "$SUITE_REPO/scripts/whats-new.sh" --stamp "$PROJECT_SKILLS_DIR"'],
    ['skills/new-website/SKILL.md', '     bash "$SUITE_REPO/scripts/whats-new.sh" --stamp-tests tests'],
    ['skills/website-contact-form/templates/mail-form-text.ts', '// not measured (docs/BUGLOG.md), so this cap is not tied to any program\'s limit. The'],
  ]);
});

test('the kept skills name none of the left-out test folders, except three known lines', () => {
  const found = keptLinesNaming((file, line) => TEST_FOLDERS.some((skill) =>
    line.includes(`${skill}/scripts/tests`) || (file.startsWith(`skills/${skill}/`) && line.includes('scripts/tests'))));
  assert.deepEqual(found, [
    ['skills/new-website/SKILL.md', '   # The brand kit\'s scripts/tests is the toolkit\'s own test suite (about 1.7 MB). No site'],
    ['skills/new-website/SKILL.md', '   rm -rf "$PROJECT_SKILLS_DIR"/website-brand-kit/scripts/tests'],
    ['skills/search-console-insights/references/geo-check.md', 'Tests: `scripts/tests/test_geo_check.py` (the pieces) and `test_track_entry.py` (the weekly'],
  ]);
});

test('without scripts/whats-new.sh beside it, new-website\'s stamp step records an unknown baseline and succeeds', () => {
  const stamp = block(['skills', 'new-website', 'SKILL.md'], 'SUITE_SRC="$(readlink', '4. **Docs** — copy')
    .split('\n').filter((line) => !line.trim().startsWith('```')).join('\n');
  // A plugin folder that is not a git clone, and one that is a clone without the toolkit's scripts.
  for (const asClone of [false, true]) {
    const root = tmp();
    fs.mkdirSync(path.join(root, 'skills', 'new-website'), { recursive: true });
    if (asClone) execFileSync('git', ['init', '-q', root]);
    const project = tmp();
    const run = spawnSync('bash', ['-c', stamp], { cwd: tmp(), encoding: 'utf8',
      env: { PATH: process.env.PATH, HOME: tmp(), SKILLS_ROOT: path.join(root, 'skills'), PROJECT_SKILLS_DIR: project } });
    assert.equal(run.status, 0, run.stderr);
    assert.match(fs.readFileSync(path.join(project, 'SUITE-VERSION'), 'utf8'), /^suite_commit: unknown\ncopied: \d{4}-\d{2}-\d{2}\n$/);
  }
});

test('the workflow publishes to directory last, after stable moved or on a hand-moved stable, one run at a time', () => {
  const text = read('.github', 'workflows', 'release-tag.yml');
  const lines = text.split('\n');
  const names = lines.filter((line) => /^ {6}- name: /.test(line)).map((line) => line.trim());
  assert.equal(names.at(-1), '- name: Publish the release to the directory branch');
  const publish = lines.slice(lines.findIndex((line) => line.trim() === names.at(-1))).map((line) => line.trim());
  assert.ok(publish.includes("if: steps.release.outputs.tag != '' && (steps.move.outcome == 'success' || github.ref_type == 'branch')"));
  assert.ok(publish.includes('TAG: ${{ steps.release.outputs.tag }}'));
  assert.ok(publish.includes('run: scripts/publish_directory.sh "$TAG"'));
  const move = lines.findIndex((line) => line.trim() === '- name: Move stable to the release');
  assert.equal(lines[move + 1].trim(), 'id: move');
  assert.match(text, /\n {4}concurrency:\n {6}group: plugin-release\n {6}cancel-in-progress: false\n/);
});

test('the tree is the same from any folder of the clone, and a commit without the plugin is refused', () => {
  // A person runs the publish script by hand from wherever their shell is.
  const fromSub = execFileSync('bash', [path.join(REPO, 'scripts', 'build_directory_tree.sh'), 'HEAD'], { cwd: path.join(REPO, 'skills'), encoding: 'utf8' }).trim();
  directoryTree();
  assert.equal(fromSub, builtTree);
  // --out, given relative to that folder, gets the whole tree there.
  const rel = path.relative(path.join(REPO, 'skills'), path.join(tmp(), 'out'));
  execFileSync('bash', [path.join(REPO, 'scripts', 'build_directory_tree.sh'), 'HEAD', '--out', rel], { cwd: path.join(REPO, 'skills') });
  const unpacked = execFileSync('find', [path.join(REPO, 'skills', rel), '-type', 'f'], { encoding: 'utf8' }).trim().split('\n').length;
  assert.equal(unpacked, directoryTree().length);
  const { git, release } = directoryRepo();
  release('v0.1', { 'README.md': 'no plugin here' });
  const work = git('rev-parse', '--show-toplevel');
  const run = spawnSync('bash', [path.join(REPO, 'scripts', 'build_directory_tree.sh'), 'v0.1'], { cwd: work, encoding: 'utf8' });
  assert.equal(run.status, 1);
  assert.match(run.stderr, /has no \.claude-plugin\/plugin\.json/);
  // A grep that fails (not one that finds nothing) stops the build instead of leaving an empty tree.
  const stubs = tmp();
  fs.writeFileSync(path.join(stubs, 'grep'), '#!/bin/sh\ncat >/dev/null\necho stub grep failed >&2\nexit 2\n', { mode: 0o755 });
  const broken = spawnSync('bash', [path.join(REPO, 'scripts', 'build_directory_tree.sh'), 'HEAD'], { cwd: REPO, encoding: 'utf8',
    env: { ...process.env, PATH: `${stubs}:${process.env.PATH}` } });
  // The stub reads all its input first, so the build cannot stop on a broken pipe instead.
  assert.equal(broken.status, 1, broken.stderr);
  assert.match(broken.stderr, /stub grep failed/);
  assert.equal(broken.stdout, '');
});

test('the publish script pushes without force', () => {
  const pushes = read('scripts', 'publish_directory.sh').split('\n').filter((line) => /\bgit\s+push\b/.test(line));
  assert.equal(pushes.length, 1);
  // A literal-text check: the real guard against a force push is the branch rule on GitHub.
  for (const line of pushes) assert.doesNotMatch(line, /(\s-f\b|--force|\s["']?\+)/, line);
});

// A throwaway repository with an `origin`, holding a few files the tree keeps and one it drops.
function directoryRepo() {
  const { git, commit: _empty, step: _step, ...rest } = releaseRepo();
  const work = git('rev-parse', '--show-toplevel');
  const origin = path.join(path.dirname(work), 'origin.git');
  const write = (file, text) => { fs.mkdirSync(path.dirname(path.join(work, file)), { recursive: true }); fs.writeFileSync(path.join(work, file), text); };
  const release = (tag, files) => {
    for (const [file, text] of Object.entries(files)) write(file, text);
    git('add', '-A');
    git('commit', '-q', '-m', tag);
    git('tag', tag);
    return git('rev-parse', 'HEAD');
  };
  const publish = (tag) => {
    const run = spawnSync('bash', [path.join(REPO, 'scripts', 'publish_directory.sh'), tag], { cwd: work, encoding: 'utf8',
      env: { PATH: process.env.PATH, HOME: path.dirname(work), GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_SYSTEM: '/dev/null' } });
    return { status: run.status, log: run.stdout + run.stderr };
  };
  const remote = (...args) => execFileSync('git', ['--git-dir', origin, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  const directory = () => { try { return remote('rev-parse', '-q', '--verify', 'refs/heads/directory'); } catch { return ''; } };
  return { git, release, publish, remote, directory, ...rest };
}

test('a release reaches directory as one commit naming its source; a re-run adds nothing', () => {
  const { git, release, publish, remote, directory } = directoryRepo();
  const c1 = release('v0.1', { '.claude-plugin/plugin.json': '{"name":"x"}', 'README.md': 'r', 'skills/a/SKILL.md': 'a',
    'skills/new-website/scripts/tests/t.sh': 't', 'skills/independent-review/SKILL.md': 'i', 'Makefile': 'm' });
  git('push', '-q', 'origin', 'main', 'v0.1');
  // The first run: no `directory` yet, so a commit with no parent.
  const first = publish('v0.1');
  assert.equal(first.status, 0, first.log);
  const d1 = directory();
  assert.equal(remote('rev-list', '--parents', '-n', '1', d1), d1);
  assert.equal(remote('log', '-1', '--format=%an%n%B', d1), `github-actions[bot]\nCroftweaver v0.1\n\nSource: ${c1}`);
  assert.deepEqual(remote('ls-tree', '-r', '--name-only', d1).split('\n'), ['.claude-plugin/plugin.json', 'README.md', 'skills/a/SKILL.md']);
  // A re-run of the same release: nothing to push.
  const again = publish('v0.1');
  assert.equal(again.status, 0, again.log);
  assert.match(again.log, /already holds v0\.1/);
  assert.equal(directory(), d1);
  // A newer release whose kept files did not change still advances the source, so an older
  // release run late cannot pass as newer.
  const c2 = release('v0.2', { 'skills/new-website/scripts/tests/t.sh': 't2' });
  git('push', '-q', 'origin', 'main', 'v0.2');
  assert.equal(publish('v0.2').status, 0);
  const d2 = directory();
  assert.equal(remote('rev-parse', `${d2}^`), d1);
  assert.equal(remote('rev-parse', `${d2}^{tree}`), remote('rev-parse', `${d1}^{tree}`));
  assert.match(remote('log', '-1', '--format=%B', d2), new RegExp(`Source: ${c2}$`));
});

test('directory refuses an older release, a tag not on main, and a last commit that names no source', () => {
  const { git, release, publish, directory } = directoryRepo();
  release('v0.1', { '.claude-plugin/plugin.json': '{}', 'skills/a/SKILL.md': 'a' });
  release('v0.2', { 'skills/a/SKILL.md': 'b' });
  git('push', '-q', 'origin', 'main', '--tags');
  assert.equal(publish('v0.2').status, 0);
  const d2 = directory();
  // v0.1 run late, after v0.2 was published.
  const late = publish('v0.1');
  assert.equal(late.status, 1);
  assert.match(late.log, /::error::directory already holds a later release/);
  assert.equal(directory(), d2);
  // A tag cut from a side branch, on either kind of run.
  git('checkout', '-q', '-b', 'side');
  release('v0.3', { 'skills/a/SKILL.md': 'side' });
  git('push', '-q', 'origin', 'v0.3');
  const side = publish('v0.3');
  assert.equal(side.status, 1);
  assert.match(side.log, /::error::v0\.3 is not on main: directory stays where it is/);
  assert.equal(directory(), d2);
  // Someone pushed a commit with no `Source:` line.
  git('checkout', '-q', 'main');
  const bare = git('commit-tree', `${d2}^{tree}`, '-p', d2, '-m', 'by hand');
  git('push', '-q', 'origin', `${bare}:refs/heads/directory`);
  release('v0.4', { 'skills/a/SKILL.md': 'c' });
  git('push', '-q', 'origin', 'main', 'v0.4');
  const nosource = publish('v0.4');
  assert.equal(nosource.status, 1);
  assert.match(nosource.log, /::error::directory's last commit names no source/);
  assert.equal(directory(), bare);
});
