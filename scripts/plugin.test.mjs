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
import zlib from 'node:zlib';
import { after, test } from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

const REPO = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const { crc32 } = await import(pathToFileURL(path.join(REPO, 'scripts', 'check_directory_files.mjs')).href);
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
    // The directory branch's pointer carries the number too: the listing shows what it says.
    for (const file of [['.claude-plugin', 'plugin.json'], ['pointer', 'plugin.json']]) {
      const plugin = JSON.parse(read(...file));
      assert.equal(`v${plugin.version.replace(/\.0$/, '')}`, process.env.RELEASE_TAG, file.join('/'));
    }
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

test('the starter\'s permission list is exactly the reviewed one', () => {
  // A drift check: any edit to the list fails here until this copy is edited on purpose.
  // It cannot tell whether a new rule is safe; a change should also repeat the routine run
  // in docs/WHAT-THE-SKILLS-RUN.md. Allow rules without `*` match one command exactly.
  const { permissions } = JSON.parse(read('skills', 'new-website', 'templates', 'claude', 'settings.json'));
  assert.deepEqual(Object.keys(permissions), ['allow', 'deny'], 'an ask list or another key was added');
  assert.deepEqual(permissions.allow, [
    'Bash(npm install)', 'Bash(npm ci)', 'Bash(npm run:*)', 'Bash(npm test:*)',
    'Bash(npx astro:*)', 'Bash(npx keystatic:*)', 'Bash(npx playwright:*)',
    'Bash(npx wrangler pages dev:*)', 'Bash(npx wrangler whoami:*)',
    'Bash(wrangler pages dev:*)', 'Bash(wrangler whoami:*)', 'Bash(astro:*)', 'Bash(playwright:*)',
    'Bash(bash scripts/check_external_links.sh:*)',
    'Bash(git status:*)', 'Bash(git diff:*)', 'Bash(git log:*)', 'Bash(git show:*)', 'Bash(git add:*)',
    'Bash(git checkout -b production)', 'Bash(git checkout main)', 'Bash(git checkout -- .gitignore)',
    'Bash(git switch main)', 'Bash(git switch -)', 'Bash(git init)',
    'Bash(git fetch)', 'Bash(git fetch origin)',
    'Bash(git pull)', 'Bash(git pull --ff-only)', 'Bash(git pull --no-rebase)',
    'Bash(git push)', 'Bash(git push -u origin main)', 'Bash(git push -u origin production)',
    'Bash(git push --dry-run origin HEAD:main)', 'Bash(git rev-parse:*)', 'Bash(node --version)',
    'Bash(gh auth status:*)', 'Bash(gh repo view:*)', 'Bash(gh repo create:*)', 'Bash(gh pr view:*)', 'Bash(gh pr list:*)',
    'Bash(ls:*)', 'Bash(cat:*)', 'Bash(head:*)', 'Bash(tail:*)', 'Bash(wc:*)', 'Bash(grep:*)',
    'Bash(mkdir:*)', 'Bash(cp:*)', 'Bash(touch:*)', 'Bash(echo:*)',
    'WebFetch(domain:docs.astro.build)', 'WebFetch(domain:developers.cloudflare.com)', 'WebFetch(domain:keystatic.com)',
  ]);
  assert.deepEqual(permissions.deny, [
    'Bash(rm -rf:*)', 'Bash(git push --force:*)', 'Bash(git push -f:*)', 'Bash(git push *--force*)',
    'Bash(git push * -f*)', 'Bash(git push * +*)', 'Bash(git reset --hard:*)', 'Bash(gh repo delete:*)',
    'Bash(npx wrangler pages delete:*)', 'Bash(npx wrangler delete:*)',
    'Bash(wrangler pages delete:*)', 'Bash(wrangler delete:*)',
    'Bash(git * --output*)', 'Bash(git add --pathspec*)', 'Bash(git add * --pathspec*)',
  ]);
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
// The branch holds a pointer plugin of four text files and a PNG icon (pointer/ on main), never the kit's
// code. The lists below are written here, not read from the scripts, so a wrong list in a
// script fails.
const POINTER_MAP = [['pointer/plugin.json', '.claude-plugin/plugin.json'], ['.claude-plugin/icon.png', '.claude-plugin/icon.png'],
  ['pointer/README.md', 'README.md'], ['LICENSE', 'LICENSE'], ['pointer/get-croftweaver.md', 'skills/get-croftweaver/SKILL.md']];
const DIRECTORY_FILES = ['.claude-plugin/icon.png', '.claude-plugin/plugin.json', 'LICENSE', 'README.md', 'skills/get-croftweaver/SKILL.md'];
const PRIVACY_URL = 'https://github.com/karero/croftweaver#what-the-directory-plugin-sends';
const RELEASES_URL = 'https://github.com/karero/croftweaver/releases/latest';
// The publish script must keep working under the system bash (3.2 on a Mac).
const SYSTEM_BASH = fs.existsSync('/bin/bash') ? '/bin/bash' : 'bash';
const pngChunk = (type, data) => {
  const body = Buffer.concat([Buffer.from(type, 'latin1'), data]);
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(body));
  return Buffer.concat([len, body, crc]);
};
// A real 1x1 PNG; the tail goes in a text chunk, so one icon can differ from another.
const PNG = (tail = '') => Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
  pngChunk('IHDR', Buffer.from([0, 0, 0, 1, 0, 0, 0, 1, 8, 6, 0, 0, 0])), pngChunk('tEXt', Buffer.from(`Comment\0${tail}`, 'latin1')),
  pngChunk('IDAT', zlib.deflateSync(Buffer.from([0, 0, 0, 0, 0]))), pngChunk('IEND', Buffer.alloc(0))]);

const flipByte = (buf, at) => { const b = Buffer.from(buf); b[at] ^= 0xff; return b; };
// The 1x1 PNG with its IDAT data replaced.
const pngWith = (type, data) => Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
  pngChunk('IHDR', Buffer.from([0, 0, 0, 1, 0, 0, 0, 1, 8, 6, 0, 0, 0])), pngChunk(type, data), pngChunk('IEND', Buffer.alloc(0))]);

const lsTree = (treeish) => execFileSync('git', ['ls-tree', '-r', '-z', treeish], { cwd: REPO, encoding: 'utf8' })
  .split('\0').filter(Boolean).map((entry) => { const [meta, file] = entry.split('\t'); return { meta, file }; });

let builtTree;
function directoryTree() {
  builtTree ??= execFileSync('bash', [path.join(REPO, 'scripts', 'build_directory_tree.sh'), 'HEAD'], { cwd: REPO, encoding: 'utf8' }).trim();
  return lsTree(builtTree);
}

test('the directory tree is the five pointer files (four text, one PNG) as plain files, each the commit\'s own blob of its source', () => {
  const expected = [...POINTER_MAP].sort((x, y) => (x[1] < y[1] ? -1 : 1))
    .map(([src, dst]) => `100644 blob ${execFileSync('git', ['rev-parse', `HEAD:${src}`], { cwd: REPO, encoding: 'utf8' }).trim()}\t${dst}`);
  assert.deepEqual(directoryTree().map(({ meta, file }) => `${meta}\t${file}`), expected);
  assert.deepEqual(directoryTree().map(({ file }) => file), DIRECTORY_FILES);
});

test('the real pointer tree passes the publish script\'s check of its five files', () => {
  directoryTree();
  const run = spawnSync(SYSTEM_BASH, [path.join(REPO, 'scripts', 'publish_directory.sh'), '--check-tree', builtTree], { cwd: REPO, encoding: 'utf8' });
  assert.equal(run.status, 0, run.stdout + run.stderr);
});

test('the content checker checks when run through a symlink, and says ok only for a file it passed', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cw-checker-'));
  const link = path.join(dir, 'check.mjs');
  fs.symlinkSync(path.join(REPO, 'scripts', 'check_directory_files.mjs'), link);
  try {
    const run = (input) => spawnSync('node', [link, 'README.md'], { input, encoding: 'utf8' });
    assert.deepEqual([run('#!/bin/sh\n').status, run('#!/bin/sh\n').stdout.trim()], [1, 'starts with #!: the directory takes text, not scripts']);
    assert.deepEqual([run('plain text\n').status, run('plain text\n').stdout.trim()], [0, 'ok']);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('the pointer plugin carries the kit\'s name and number, metadata only, and a privacy link to a heading the README has', () => {
  const kit = JSON.parse(read('.claude-plugin', 'plugin.json'));
  const pointer = JSON.parse(read('pointer', 'plugin.json'));
  // Metadata only: a component path (commands, hooks, agents…) could point at a file the branch leaves out.
  assert.deepEqual(Object.keys(pointer).filter((k) => !['name', 'displayName', 'version', 'description', 'author', 'homepage', 'repository', 'license', 'privacyPolicyUrl'].includes(k)), []);
  assert.equal(pointer.name, kit.name);
  // A release that raises one number and not the other would show the listing an old version.
  assert.equal(pointer.version, kit.version);
  assert.equal(pointer.privacyPolicyUrl, PRIVACY_URL);
  const anchor = new URL(pointer.privacyPolicyUrl).hash.slice(1);
  const headings = read('README.md').split('\n').filter((l) => l.startsWith('## ')).map((l) => l.slice(3).trim().toLowerCase().replace(/[^a-z0-9 -]/g, '').replace(/ /g, '-'));
  assert.ok(headings.includes(anchor), `README has no heading for #${anchor}`);
  // What the branch will hold is this file, not another.
  const built = directoryTree().find(({ file }) => file === '.claude-plugin/plugin.json');
  assert.equal(built.meta.split(' ')[2], execFileSync('git', ['rev-parse', 'HEAD:pointer/plugin.json'], { cwd: REPO, encoding: 'utf8' }).trim());
});

// The install commands live once, in the README's marked blocks; the pointer repeats them.
// A command the pointer got wrong would send an owner to a route that does not work.
function markedCommands() {
  const blocks = [];
  let open = null;
  read('README.md').split('\n').forEach((line, i) => {
    const start = /^<!-- pointer-commands (\w+) -->$/.exec(line);
    if (start) { assert.equal(open, null, `README line ${i + 1}: a pointer-commands block inside another`); open = { label: start[1], lines: [] }; return; }
    if (line === '<!-- /pointer-commands -->') { assert.notEqual(open, null, `README line ${i + 1}: a block end with no start`); blocks.push(open); open = null; return; }
    if (!open) return;
    const text = line.trim();
    if (text === '' || text.startsWith('```')) return;
    assert.match(text, /^(claude|npm) /, `README line ${i + 1}: a marked block holds only claude and npm command lines`);
    open.lines.push(text);
  });
  assert.equal(open, null, 'README: a pointer-commands block is never closed');
  return blocks;
}

test('the pointer\'s command lines are the README\'s marked ones, exactly, and the routes they name exist', () => {
  const byLabel = {};
  for (const { label, lines } of markedCommands()) {
    assert.ok(lines.length > 0, `an empty ${label} block`);
    if (byLabel[label]) assert.deepEqual(lines, byLabel[label], `two ${label} blocks in the README differ`);
    byLabel[label] = lines;
  }
  assert.deepEqual(Object.keys(byLabel).sort(), ['claude', 'npm']);
  const expected = [...new Set(Object.values(byLabel).flat())].sort();
  for (const file of ['README.md', 'get-croftweaver.md']) {
    const text = read('pointer', file);
    const got = [...new Set(text.split('\n').map((l) => l.trim()).filter((l) => /^(claude|npm) /.test(l)))].sort();
    assert.deepEqual(got, expected, `pointer/${file} and the README's marked blocks differ`);
    assert.ok(text.includes(RELEASES_URL), `pointer/${file} lacks ${RELEASES_URL}`);
  }
  // The flags the npm lines carry are the installer's own.
  const installer = read('packages', 'create-croftweaver', 'index.mjs');
  for (const flag of ['--codex', '--antigravity']) assert.ok(installer.includes(`'${flag}'`), `the installer has no ${flag}`);
  // The checklist blocks a plugin whose README is under 40 words.
  assert.ok(read('pointer', 'README.md').split(/\s+/).filter(Boolean).length >= 40);
});

test('the pointer\'s skill is the one skill, text only, with the name its folder will carry', () => {
  const skill = read('pointer', 'get-croftweaver.md');
  assert.match(skill, /^---\nname: get-croftweaver\ndescription: [^\n]+\n---\n/);
  assert.ok(!skill.startsWith('#!'));
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

test('the tree is the same from any folder of the clone, and a commit missing any pointer source is refused', () => {
  // A person runs the publish script by hand from wherever their shell is.
  const fromSub = execFileSync('bash', [path.join(REPO, 'scripts', 'build_directory_tree.sh'), 'HEAD'], { cwd: path.join(REPO, 'skills'), encoding: 'utf8' }).trim();
  directoryTree();
  assert.equal(fromSub, builtTree);
  // --out, given relative to that folder, gets the whole tree there.
  const rel = path.relative(path.join(REPO, 'skills'), path.join(tmp(), 'out'));
  execFileSync('bash', [path.join(REPO, 'scripts', 'build_directory_tree.sh'), 'HEAD', '--out', rel], { cwd: path.join(REPO, 'skills') });
  const unpacked = execFileSync('find', [path.join(REPO, 'skills', rel), '-type', 'f'], { encoding: 'utf8' }).trim().split('\n').map((f) => path.relative(path.join(REPO, 'skills', rel), f)).sort();
  assert.deepEqual(unpacked, DIRECTORY_FILES);
  // Each source missing in turn: the build names it and prints no tree.
  for (const [src] of POINTER_MAP) {
    const { git, release } = directoryRepo();
    const files = pointerFiles();
    delete files[src];
    release('v0.1', files);
    const work = git('rev-parse', '--show-toplevel');
    const run = spawnSync('bash', [path.join(REPO, 'scripts', 'build_directory_tree.sh'), 'v0.1'], { cwd: work, encoding: 'utf8' });
    assert.equal(run.status, 1, src);
    assert.ok(run.stderr.includes(`has no ${src}`), `${src}: ${run.stderr}`);
    assert.equal(run.stdout, '');
  }
});

test('the publish script pushes without force', () => {
  const pushes = read('scripts', 'publish_directory.sh').split('\n').filter((line) => /\bgit\s+push\b/.test(line));
  assert.equal(pushes.length, 1);
  // A literal-text check: the real guard against a force push is the branch rule on GitHub.
  for (const line of pushes) assert.doesNotMatch(line, /(\s-f\b|--force|\s["']?\+)/, line);
});

// A throwaway repository with an `origin`, holding the pointer's sources and files the branch never takes.
function directoryRepo() {
  const { git, commit: _empty, step: _step, ...rest } = releaseRepo();
  const work = git('rev-parse', '--show-toplevel');
  const origin = path.join(path.dirname(work), 'origin.git');
  const env = { PATH: process.env.PATH, HOME: path.dirname(work), GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_SYSTEM: '/dev/null' };
  const write = (file, text) => { fs.mkdirSync(path.dirname(path.join(work, file)), { recursive: true }); fs.writeFileSync(path.join(work, file), text); };
  // `executable` lists files recorded at mode 100755, whatever the platform's file modes are.
  const release = (tag, files, { executable = [] } = {}) => {
    for (const [file, text] of Object.entries(files)) write(file, text);
    git('add', '-A');
    for (const file of executable) git('update-index', '--chmod=+x', file);
    git('commit', '-q', '-m', tag);
    git('tag', tag);
    return git('rev-parse', 'HEAD');
  };
  const run = (script, ...args) => spawnSync(SYSTEM_BASH, [script, ...args], { cwd: work, encoding: 'utf8', env });
  const publish = (tag) => { const r = run(path.join(REPO, 'scripts', 'publish_directory.sh'), tag); return { status: r.status, log: r.stdout + r.stderr }; };
  const script = (...args) => { const r = run(path.join(REPO, 'scripts', 'publish_directory.sh'), ...args); return { status: r.status, log: r.stdout + r.stderr, out: r.stdout.trim() }; };
  // A tree of exactly these entries, [mode, path, text or bytes], written into the repository's objects.
  const makeTree = (entries) => {
    const index = path.join(path.dirname(work), `index-${Math.random().toString(36).slice(2)}`);
    const withIndex = { ...env, GIT_INDEX_FILE: index };
    const lines = entries.map(([mode, file, text]) => `${mode} ${execFileSync('git', ['hash-object', '-w', '--stdin'], { cwd: work, env, input: text, encoding: 'utf8' }).trim()}\t${file}`);
    execFileSync('git', ['update-index', '--index-info'], { cwd: work, env: withIndex, input: `${lines.join('\n')}\n` });
    return execFileSync('git', ['write-tree'], { cwd: work, env: withIndex, encoding: 'utf8' }).trim();
  };
  // The publish script beside a builder that prints `tree` whatever the commit holds, and the
  // real content checker or, given `checker`, that text in its place.
  const publishWithStubBuilder = (tag, tree, checker) => {
    const dir = tmp();
    for (const f of ['publish_directory.sh', 'check_directory_files.mjs']) fs.copyFileSync(path.join(REPO, 'scripts', f), path.join(dir, f));
    if (checker !== undefined) fs.writeFileSync(path.join(dir, 'check_directory_files.mjs'), checker);
    fs.writeFileSync(path.join(dir, 'build_directory_tree.sh'), `#!/usr/bin/env bash\necho ${tree}\n`, { mode: 0o755 });
    const r = run(path.join(dir, 'publish_directory.sh'), tag);
    return { status: r.status, log: r.stdout + r.stderr };
  };
  const remote = (...args) => execFileSync('git', ['--git-dir', origin, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  const directory = () => { try { return remote('rev-parse', '-q', '--verify', 'refs/heads/directory'); } catch { return ''; } };
  return { git, release, publish, script, makeTree, publishWithStubBuilder, remote, directory, ...rest };
}

// What a release holds: the pointer's five sources, and kit files the branch must never take.
const pointerFiles = (more = {}) => ({ 'pointer/plugin.json': '{"name":"x","version":"0.1.0"}\n', '.claude-plugin/icon.png': PNG('icon-1'), 'pointer/README.md': 'readme',
  'LICENSE': 'MIT', 'pointer/get-croftweaver.md': 'the skill', 'skills/a/SKILL.md': 'kit skill', 'scripts/tool.sh': '#!/bin/sh\n', Makefile: 'm', ...more });

test('a release reaches directory as one commit of the five pointer files naming its source; a re-run adds nothing', () => {
  const { git, release, publish, remote, directory } = directoryRepo();
  const c1 = release('v0.1', pointerFiles());
  git('push', '-q', 'origin', 'main', 'v0.1');
  // The first run: no `directory` yet, so a commit with no parent.
  const first = publish('v0.1');
  assert.equal(first.status, 0, first.log);
  const d1 = directory();
  assert.equal(remote('rev-list', '--parents', '-n', '1', d1), d1);
  assert.equal(remote('log', '-1', '--format=%an%n%B', d1), `github-actions[bot]\nCroftweaver v0.1\n\nSource: ${c1}`);
  assert.deepEqual(remote('ls-tree', '-r', '--name-only', d1).split('\n'), DIRECTORY_FILES);
  assert.equal(remote('show', `${d1}:skills/get-croftweaver/SKILL.md`), 'the skill');
  // A re-run of the same release: nothing to push.
  const again = publish('v0.1');
  assert.equal(again.status, 0, again.log);
  assert.match(again.log, /already holds v0\.1/);
  assert.equal(directory(), d1);
  // A newer release whose pointer files did not change still advances the source, so an older
  // release run late cannot pass as newer.
  const c2 = release('v0.2', { Makefile: 'm2', 'skills/a/SKILL.md': 'kit skill 2' });
  git('push', '-q', 'origin', 'main', 'v0.2');
  assert.equal(publish('v0.2').status, 0);
  const d2 = directory();
  assert.equal(remote('rev-parse', `${d2}^`), d1);
  assert.equal(remote('rev-parse', `${d2}^{tree}`), remote('rev-parse', `${d1}^{tree}`));
  assert.match(remote('log', '-1', '--format=%B', d2), new RegExp(`Source: ${c2}$`));
});

test('the first release after the pointer replaces the code tree that directory holds, keeping its history', () => {
  const { git, release, publish, remote, directory } = directoryRepo();
  // What the October release published: the kit's code tree, with a source line.
  const c1 = release('v0.1', { '.claude-plugin/plugin.json': '{"name":"kit"}', 'README.md': 'kit readme', 'skills/a/SKILL.md': 'a', 'skills/b/scripts/run.sh': '#!/bin/sh\n' });
  git('push', '-q', 'origin', 'main', 'v0.1');
  const old = git('commit-tree', `${c1}^{tree}`, '-m', 'Croftweaver v0.1', '-m', `Source: ${c1}`);
  git('push', '-q', 'origin', `${old}:refs/heads/directory`);
  const c2 = release('v0.2', pointerFiles({ 'README.md': 'kit readme 2' }));
  git('push', '-q', 'origin', 'main', 'v0.2');
  const run = publish('v0.2');
  assert.equal(run.status, 0, run.log);
  const d = directory();
  assert.equal(remote('rev-parse', `${d}^`), old);
  assert.deepEqual(remote('ls-tree', '-r', '--name-only', d).split('\n'), DIRECTORY_FILES);
  assert.equal(remote('show', `${d}:README.md`), 'readme');
  assert.match(remote('log', '-1', '--format=%B', d), new RegExp(`Source: ${c2}$`));
});

test('a release that would put anything but the five plain files (four text, one PNG) on directory is refused, and directory stays', () => {
  const { git, release, publish, script, makeTree, publishWithStubBuilder, remote, directory } = directoryRepo();
  release('v0.1', pointerFiles());
  git('push', '-q', 'origin', 'main', 'v0.1');
  assert.equal(publish('v0.1').status, 0);
  let held = directory();
  const refused = (run, message) => { assert.equal(run.status, 1, run.log); assert.match(run.log, message); assert.equal(directory(), held); };

  // Through the real builder: a script as the skill, and a file kept executable.
  release('v0.2', { 'pointer/get-croftweaver.md': '#!/bin/sh\necho hi\n' });
  git('push', '-q', 'origin', 'main', 'v0.2');
  refused(publish('v0.2'), /::error::skills\/get-croftweaver\/SKILL\.md in the directory tree starts with #!/);
  release('v0.3', { 'pointer/get-croftweaver.md': 'the skill again' }, { executable: ['pointer/get-croftweaver.md'] });
  git('push', '-q', 'origin', 'main', 'v0.3');
  refused(publish('v0.3'), /::error::skills\/get-croftweaver\/SKILL\.md in the directory tree has mode 100755/);

  release('v0.4', { 'pointer/get-croftweaver.md': 'fine' });
  git('push', '-q', 'origin', 'main', 'v0.4');
  assert.equal(publish('v0.4').status, 0, 'a clean release publishes');
  held = directory();
  release('v0.5', { 'pointer/get-croftweaver.md': 'next' });
  git('push', '-q', 'origin', 'main', 'v0.5');
  // Past the builder (a builder changed to take more, or the test of its list edited with it):
  // the script's own list of five still stands. Each stub tree must be a real tree first, so
  // the refusal below cannot be a broken stub failing later at commit-tree.
  const five = [['100644', '.claude-plugin/icon.png', PNG('i')], ['100644', '.claude-plugin/plugin.json', '{}'], ['100644', 'LICENSE', 'l'],
    ['100644', 'README.md', 'r\tcaf\u00e9\r\n'], ['100644', 'skills/get-croftweaver/SKILL.md', 's']];
  const cases = [
    ['a sixth path', [...five, ['100644', 'hooks/hooks.json', '{}']], /::error::the directory tree is not exactly the five pointer files: got .*hooks\/hooks\.json/],
    ['a missing path', five.slice(1), /::error::the directory tree is not exactly the five pointer files/],
    ['another path in place of one', [...five.slice(1), ['100644', 'commands/go.md', 'x']], /::error::the directory tree is not exactly the five pointer files/],
    ['an executable file', five.map((e) => (e[1] === 'LICENSE' ? ['100755', e[1], e[2]] : e)), /::error::LICENSE in the directory tree has mode 100755/],
    ['a symlink', five.map((e) => (e[1] === 'README.md' ? ['120000', e[1], 'LICENSE'] : e)), /::error::README\.md in the directory tree has mode 120000/],
    ['a script', five.map((e) => (e[1] === 'README.md' ? [e[0], e[1], '#!/usr/bin/env node\n'] : e)), /::error::README\.md in the directory tree starts with #!/],
    ['a binary blob as the README', five.map((e) => (e[1] === 'README.md' ? [e[0], e[1], Buffer.from([0x4d, 0x5a, 0x00, 0x01, 0x02])] : e)), /::error::README\.md in the directory tree holds a control character/],
    ['binary with no NUL as the README', five.map((e) => (e[1] === 'README.md' ? [e[0], e[1], Buffer.from([0x01, 0x02, 0x03, 0x04, 0xff, 0xfe])] : e)), /::error::README\.md in the directory tree holds a control character/],
    ['Latin-1 text as the README', five.map((e) => (e[1] === 'README.md' ? [e[0], e[1], Buffer.from('caf\u00e9\n', 'latin1')] : e)), /::error::README\.md in the directory tree is not valid UTF-8/],
    ['a text file as the icon', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], 'not a png'] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: no PNG signature/],
    ['the PNG signature alone as the icon', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], PNG().subarray(0, 8)] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: cut short: no IEND chunk/],
    ['a cut-short icon', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], PNG('i').subarray(0, 40)] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: cut short/],
    ['UTF-8 above U+10FFFF as the README', five.map((e) => (e[1] === 'README.md' ? [e[0], e[1], Buffer.from([0xf4, 0x90, 0x80, 0x80])] : e)), /::error::README\.md in the directory tree is not valid UTF-8/],
    ['a 5-byte UTF-8 sequence as the README', five.map((e) => (e[1] === 'README.md' ? [e[0], e[1], Buffer.from([0xf8, 0x88, 0x80, 0x80, 0x80])] : e)), /::error::README\.md in the directory tree is not valid UTF-8/],
    ['U+0080 as the README', five.map((e) => (e[1] === 'README.md' ? [e[0], e[1], Buffer.from([0xc2, 0x80])] : e)), /::error::README\.md in the directory tree holds a control character/],
    ['an icon whose IHDR overruns the file', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], Buffer.from('89504e470d0a1a0a0000000d494844520000000049454e44ae426082', 'hex')] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: /],
    ['an icon with one checksum byte flipped', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], flipByte(PNG('i'), 8 + 12 + 13 - 1)] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: the IHDR chunk fails its checksum/],
    ['an icon with bytes after IEND', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], Buffer.concat([PNG('i'), Buffer.from('x')])] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: bytes after IEND/],
    ['an icon whose image data is not zlib', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], pngWith('IDAT', Buffer.from('not zlib at all'))] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: the image data is not valid zlib/],
    ['an icon whose image data inflates to nothing', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], pngWith('IDAT', zlib.deflateSync(Buffer.alloc(0)))] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: the image data does not fill its rows/],
    ['an icon with more image data than its rows', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], pngWith('IDAT', zlib.deflateSync(Buffer.alloc(10)))] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: the image data is not valid zlib, or too long/],
    ['an icon with a row filter PNG lacks', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], pngWith('IDAT', zlib.deflateSync(Buffer.from([5, 0, 0, 0, 0])))] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: a row has a filter PNG does not define/],
    ['an icon with bytes after its compressed data', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], pngWith('IDAT', Buffer.concat([zlib.deflateSync(Buffer.from([0, 0, 0, 0, 0])), Buffer.from('xx')]))] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: bytes after the image data/],
    ['an interlaced icon', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], Buffer.concat([PNG().subarray(0, 8), pngChunk('IHDR', Buffer.from([0, 0, 0, 1, 0, 0, 0, 1, 8, 6, 0, 0, 1])),
      pngChunk('IDAT', zlib.deflateSync(Buffer.from([0, 0, 0, 0, 0]))), pngChunk('IEND', Buffer.alloc(0))])] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: interlaced/],
    ['a palette icon', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], Buffer.concat([PNG().subarray(0, 8), pngChunk('IHDR', Buffer.from([0, 0, 0, 1, 0, 0, 0, 1, 8, 3, 0, 0, 0])), pngChunk('PLTE', Buffer.from([0, 0, 0])), pngChunk('IDAT', zlib.deflateSync(Buffer.from([0, 0]))), pngChunk('IEND', Buffer.alloc(0))])] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: not an 8-bit RGB or RGBA image/],
    ['a 16-bit icon', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], Buffer.concat([PNG().subarray(0, 8), pngChunk('IHDR', Buffer.from([0, 0, 0, 1, 0, 0, 0, 1, 16, 6, 0, 0, 0])), pngChunk('IDAT', zlib.deflateSync(Buffer.alloc(9))), pngChunk('IEND', Buffer.alloc(0))])] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: not an 8-bit RGB or RGBA image/],
    ['an RGBA icon with a PLTE chunk', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], Buffer.concat([PNG().subarray(0, 8), pngChunk('IHDR', Buffer.from([0, 0, 0, 1, 0, 0, 0, 1, 8, 6, 0, 0, 0])), pngChunk('PLTE', Buffer.from([0, 0, 0])), pngChunk('IDAT', zlib.deflateSync(Buffer.from([0, 0, 0, 0, 0]))), pngChunk('IEND', Buffer.alloc(0))])] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: a PLTE chunk, which the icon may not have/],
    ['an icon whose IDAT chunks are split by another chunk', five.map((e) => (e[1] === '.claude-plugin/icon.png' ? [e[0], e[1], Buffer.concat([PNG().subarray(0, 8), pngChunk('IHDR', Buffer.from([0, 0, 0, 1, 0, 0, 0, 1, 8, 6, 0, 0, 0])), pngChunk('IDAT', zlib.deflateSync(Buffer.from([0, 0, 0, 0, 0])).subarray(0, 4)), pngChunk('tEXt', Buffer.from('a\0b', 'latin1')), pngChunk('IDAT', zlib.deflateSync(Buffer.from([0, 0, 0, 0, 0])).subarray(4)), pngChunk('IEND', Buffer.alloc(0))])] : e)), /::error::\.claude-plugin\/icon\.png in the directory tree is not a whole PNG: its IDAT chunks are not consecutive/],
  ];
  for (const [what, entries, message] of cases) {
    const tree = makeTree(entries);
    assert.equal(git('cat-file', '-t', tree), 'tree', what);
    refused(publishWithStubBuilder('v0.5', tree), message);
    // The same check, alone, as the trial runs it.
    const alone = script('--check-tree', tree);
    assert.equal(alone.status, 1, what);
    assert.match(alone.log, message, what);
  }
  assert.deepEqual(remote('ls-tree', '-r', '--name-only', held).split('\n'), DIRECTORY_FILES);

  // A checker that prints nothing, or prints ok and then fails, is not a pass, even for good files.
  for (const checker of ['', "console.log('ok'); process.exit(7);"]) {
    refused(publishWithStubBuilder('v0.5', makeTree(five), checker), /::error::\S+ in the directory tree could not be checked: reading it or check_directory_files\.mjs failed, or printed nothing/);
  }

  // A tree of the five files, UTF-8 text with a tab and CRLF and a whole PNG, passes.
  const good = script('--check-tree', makeTree(five));
  assert.deepEqual([good.status, good.out.startsWith('ok:')], [0, true], good.log);
  // A name that is no tree is refused, not passed.
  assert.equal(script('--check-tree', 'no-such-thing').status, 1);
});

test('--compare tells a new version number from every other change of the five files', () => {
  const { makeTree, script } = directoryRepo();
  const manifest = (version, description = 'd') => `{\n  "name": "croftweaver",\n  "version": "${version}",\n  "description": "${description}"\n}\n`;
  const tree = ({ version = '0.36.0', description, icon = PNG('icon'), license = 'MIT', readme = 'r', skill = 's' } = {}) => makeTree([
    ['100644', '.claude-plugin/icon.png', icon], ['100644', '.claude-plugin/plugin.json', manifest(version, description)],
    ['100644', 'LICENSE', license], ['100644', 'README.md', readme], ['100644', 'skills/get-croftweaver/SKILL.md', skill]]);
  const base = tree();
  const compare = (other) => { const r = script('--compare', base, other); assert.equal(r.status, 0, r.log); return r.out.split('\n'); };
  assert.deepEqual(compare(tree()), ['same']);
  assert.deepEqual(compare(tree({ version: '0.37.0' })), ['version only']);
  // A new description is a change the trial must see, even beside a new number.
  assert.deepEqual(compare(tree({ description: 'new words' })), ['.claude-plugin/plugin.json']);
  assert.deepEqual(compare(tree({ version: '0.37.0', description: 'new words' })), ['.claude-plugin/plugin.json']);
  assert.deepEqual(compare(tree({ icon: PNG('icon, new') })), ['.claude-plugin/icon.png']);
  // A mode alone is a change the trial must see: no version exception for it.
  const execManifest = makeTree([['100644', '.claude-plugin/icon.png', PNG('icon')], ['100755', '.claude-plugin/plugin.json', manifest('0.36.0')],
    ['100644', 'LICENSE', 'MIT'], ['100644', 'README.md', 'r'], ['100644', 'skills/get-croftweaver/SKILL.md', 's']]);
  assert.deepEqual(compare(execManifest), ['.claude-plugin/plugin.json']);
  const execNewVersion = makeTree([['100644', '.claude-plugin/icon.png', PNG('icon')], ['100755', '.claude-plugin/plugin.json', manifest('0.37.0')],
    ['100644', 'LICENSE', 'MIT'], ['100644', 'README.md', 'r'], ['100644', 'skills/get-croftweaver/SKILL.md', 's']]);
  assert.deepEqual(compare(execNewVersion), ['.claude-plugin/plugin.json']);
  assert.deepEqual(compare(tree({ license: 'MIT 2' })), ['LICENSE']);
  assert.deepEqual(compare(tree({ readme: 'r2', skill: 's2' })), ['README.md', 'skills/get-croftweaver/SKILL.md']);
  // A new number does not hide another change.
  assert.deepEqual(compare(tree({ version: '0.37.0', license: 'MIT 2' })), ['.claude-plugin/plugin.json', 'LICENSE']);
  // A file gone, a file added.
  const without = makeTree([['100644', '.claude-plugin/plugin.json', manifest('0.36.0')], ['100644', 'LICENSE', 'MIT']]);
  assert.ok(script('--compare', base, without).out.split('\n').includes('README.md'));
  assert.notEqual(script('--compare', base, 'no-such-thing').status, 0);
});

test('directory refuses an older release, a tag not on main, and a last commit that names no source', () => {
  const { git, release, publish, directory } = directoryRepo();
  release('v0.1', pointerFiles());
  release('v0.2', { 'pointer/get-croftweaver.md': 'b' });
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
  release('v0.3', { 'pointer/get-croftweaver.md': 'side' });
  git('push', '-q', 'origin', 'v0.3');
  const side = publish('v0.3');
  assert.equal(side.status, 1);
  assert.match(side.log, /::error::v0\.3 is not on main: directory stays where it is/);
  assert.equal(directory(), d2);
  // Someone pushed a commit with no `Source:` line.
  git('checkout', '-q', 'main');
  const bare = git('commit-tree', `${d2}^{tree}`, '-p', d2, '-m', 'by hand');
  git('push', '-q', 'origin', `${bare}:refs/heads/directory`);
  release('v0.4', { 'pointer/get-croftweaver.md': 'c' });
  git('push', '-q', 'origin', 'main', 'v0.4');
  const nosource = publish('v0.4');
  assert.equal(nosource.status, 1);
  assert.match(nosource.log, /::error::directory's last commit names no source/);
  assert.equal(directory(), bare);
});
