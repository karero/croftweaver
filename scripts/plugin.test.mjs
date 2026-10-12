// Tests for the Claude Code plugin (.claude-plugin/) and for what makes the skills work
// from a plugin's folder: no skill may send the assistant to ~/.claude/skills/<name>/ for
// its files, because a plugin's skills are not there. Run: make test-plugin (needs node and bash).
//
// Claude Code puts a skill's own folder in place of the name CLAUDE_SKILL_DIR in braces,
// in SKILL.md only. Other assistants leave it as written. The cases below hold both.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { after, test } from 'node:test';
import { fileURLToPath } from 'node:url';

const REPO = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const SKILLS = path.join(REPO, 'skills');
const VAR = '${CLAUDE_SKILL_DIR}';
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const scratch = [];
after(() => { for (const dir of scratch) fs.rmSync(dir, { recursive: true, force: true }); });

// Every text file under skills/, as [path relative to the repo, content].
function skillFiles() {
  return fs.readdirSync(SKILLS, { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile() && /\.(md|sh|mjs|js|ts|py|json|astro|txt|ya?ml)$/.test(entry.name))
    .map((entry) => path.join(entry.parentPath, entry.name))
    .map((file) => [path.relative(REPO, file).split(path.sep).join('/'), fs.readFileSync(file, 'utf8')]);
}

test('the plugin and the marketplace entry name the same plugin and the same release', () => {
  const plugin = JSON.parse(read('.claude-plugin', 'plugin.json'));
  const market = JSON.parse(read('.claude-plugin', 'marketplace.json'));
  assert.equal(plugin.name, 'croftweaver');
  assert.equal(market.plugins.length, 1);
  const [entry] = market.plugins;
  // Installing is by entry name, the skills' prefix is the plugin's: they must not differ.
  assert.equal(entry.name, plugin.name);
  assert.deepEqual({ source: entry.source.source, repo: entry.source.repo }, { source: 'github', repo: 'karero/croftweaver' });
  // Users get releases, not main: the entry points at a release tag, and the plugin carries
  // that release's number, which is also what tells Claude Code that there is an update.
  const tag = /^v(\d+)\.(\d+)$/.exec(entry.source.ref);
  assert.ok(tag, `the entry's ref ${JSON.stringify(entry.source.ref)} is not a release tag like v0.32`);
  assert.equal(plugin.version, `${tag[1]}.${tag[2]}.0`);
  // Set in one place only: with both, Claude Code takes plugin.json's without a word.
  assert.equal(entry.version, undefined);
});

test('no file of a skill sends the reader to the home skills folder for a skill\'s files', () => {
  const found = [];
  for (const [file, text] of skillFiles()) {
    text.split('\n').forEach((line, i) => {
      if (/(~|\$HOME)\/\.(claude|agents|gemini\/config)\/skills\/[A-Za-z]/.test(line)) found.push(`${file}:${i + 1}: ${line.trim().slice(0, 100)}`);
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
    for (const [, rest] of text.matchAll(/\$\{CLAUDE_SKILL_DIR\}((?:\/[A-Za-z0-9._-]+)*)/g)) {
      if (!fs.existsSync(path.join(skillDir, rest))) missing.push(`${file}: ${VAR}${rest}`);
    }
  }
  assert.deepEqual(misplaced, []);
  assert.deepEqual(missing, []);
});

// The lines new-website tells the assistant to run to find the installed suite, taken from
// SKILL.md itself: from the SKILLS_ROOT test to the end of the PROJECT_SKILLS_DIR one.
function lookup() {
  const lines = read('skills', 'new-website', 'SKILL.md').split('\n');
  const from = lines.findIndex((line) => line.includes('if [ -z "${SKILLS_ROOT:-}" ]; then'));
  const to = lines.findIndex((line, i) => i > from && line.trim() === 'mkdir <site> && cd <site> && git init');
  assert.ok(from > 0 && to > from, 'the lookup block in new-website/SKILL.md was not found');
  return lines.slice(from, to).join('\n');
}

// Runs the lookup as an assistant would: `filled` is what stands in place of the name in
// braces (Claude Code), or null to leave the text as written (any other assistant).
function runLookup({ filled, home, env = {} }) {
  const script = `${filled === null ? lookup() : lookup().replaceAll(VAR, filled)}\nprintf '%s\\n%s\\n' "$SKILLS_ROOT" "$PROJECT_SKILLS_DIR"\n`;
  const clean = { PATH: process.env.PATH, HOME: home, ...env };
  const out = execFileSync('bash', ['-c', script], { env: clean, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  const [root, project] = out.trim().split('\n');
  return { root, project };
}

function tmp() {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'croftweaver-plugin-test-')));
  scratch.push(dir);
  return dir;
}
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
  const plugin = path.join(tmp(), 'with space', 'skills');
  suiteAt(plugin);

  assert.equal(runLookup({ filled: path.join(plugin, 'new-website'), home }).root, plugin);
});

test('an assistant that fills nothing in still finds its own install, and the unfilled name does no harm', () => {
  const home = tmp();
  suiteAt(path.join(home, '.agents', 'skills'));

  assert.deepEqual(runLookup({ filled: null, home }), { root: path.join(home, '.agents', 'skills'), project: '.agents/skills' });

  // Claude Code's own folder still comes before the other two, as before.
  suiteAt(path.join(home, '.claude', 'skills'));
  assert.deepEqual(runLookup({ filled: null, home }), { root: path.join(home, '.claude', 'skills'), project: '.claude/skills' });
});

test('an explicit SKILLS_ROOT is honoured, and with nothing installed the default is unchanged', () => {
  const home = tmp();
  const plugin = path.join(tmp(), 'skills');
  suiteAt(plugin);

  assert.equal(runLookup({ filled: path.join(plugin, 'new-website'), home, env: { SKILLS_ROOT: '/somewhere/else' } }).root, '/somewhere/else');
  assert.equal(runLookup({ filled: null, home }).root, path.join(home, '.claude', 'skills'));
});
