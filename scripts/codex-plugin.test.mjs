// Opt-in test of the Codex plugin as users get it: from GitHub, from the branch `stable`, in
// a throwaway Codex home. Run: make test-codex-plugin (needs node 20 or newer, git, the Codex
// CLI on PATH and a connection to GitHub; no sign-in). Without Codex it skips.
//
// make test-plugin checks our files. It cannot see what Codex does with them: which
// marketplace file it reads, where it keeps the plugin, whether an update leaves one copy.
// Codex calls the .claude-plugin/ files "legacy-compatible", so a later Codex may change any
// of that. This test asks Codex itself. It tests the release on `stable`, not this checkout.
// With no new release since the install, the update step can only show that an update runs
// cleanly and leaves one copy; that it moves to a new release shows only after the next one.
import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { after, test } from 'node:test';

const URL = 'https://github.com/karero/croftweaver.git';
// Skip only when there is no Codex at all. A codex that is there but does not run fails the
// test: a skip would hide a broken install.
const probe = spawnSync('codex', ['--version'], { encoding: 'utf8' });
const noCodex = probe.error?.code === 'ENOENT' && 'the Codex CLI is not on PATH';
const home = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-plugin-test-'));
after(() => fs.rmSync(home, { recursive: true, force: true }));
const codexHome = path.join(home, 'codex home');
const cwd = path.join(home, 'project');
fs.mkdirSync(codexHome);
fs.mkdirSync(cwd);
const cache = path.join(codexHome, 'plugins', 'cache', 'croftweaver', 'croftweaver');

// A clean environment: no sign-in and no settings of the person running it.
function codex(...args) {
  const run = spawnSync('codex', args, { cwd, encoding: 'utf8', env: { ...process.env, CODEX_HOME: codexHome }, timeout: 180_000 });
  assert.equal(run.status, 0, `codex ${args.join(' ')} failed:\n${run.stdout}\n${run.stderr}`);
  return run.stdout;
}

const versions = () => fs.readdirSync(cache);
const skillsIn = (dir) => fs.readdirSync(dir).filter((name) => fs.existsSync(path.join(dir, name, 'SKILL.md'))).sort();
const stableNow = () => execFileSync('git', ['ls-remote', URL, 'refs/heads/stable'], { encoding: 'utf8' }).split('\t')[0];

// The skills Codex offers from one folder. Its prompt input is a JSON list of messages; one
// holds a table of skill roots, one line each (- `r2` = `<folder>`), then the skills, one line
// each (- <name>: <description> (file: r2/<skill>/SKILL.md)). Codex also offers the skills in
// ~/.agents/skills and other places outside CODEX_HOME, under the same names when the suite is
// installed there too, so only the lines under the plugin's own root count.
function offeredFrom(promptInput, folder) {
  const text = JSON.parse(promptInput).flatMap((m) => m.content ?? []).map((c) => c.text ?? '').find((t) => t.includes('### Available skills'));
  assert.ok(text, 'Codex printed no list of available skills');
  const real = fs.realpathSync(folder);
  const roots = [...text.matchAll(/^- `(r\d+)` = `([^`]+)`$/gm)].filter(([, , dir]) => fs.existsSync(dir) && fs.realpathSync(dir) === real).map(([, id]) => id);
  assert.equal(roots.length, 1, `Codex lists the plugin's folder ${roots.length} times among its skill roots`);
  return [...text.matchAll(/^- croftweaver:([a-z0-9-]+): .*\(file: (r\d+)\/([^/]+)\/SKILL\.md\)$/gm)]
    .filter(([, , root]) => root === roots[0]).map(([, name]) => name).sort();
}

test('Codex installs the plugin from GitHub: the release on stable, and every skill in it', { skip: noCodex }, () => {
  assert.equal(probe.status, 0, `codex --version failed:\n${probe.stdout}\n${probe.stderr}\n${probe.error ?? ''}`);
  const before = stableNow();
  codex('plugin', 'marketplace', 'add', URL);
  codex('plugin', 'add', 'croftweaver@croftweaver');
  // One copy, in the folder named for the number in the release's own plugin.json.
  assert.equal(versions().length, 1, `copies: ${versions()}`);
  const [version] = versions();
  const root = path.join(cache, version);
  assert.equal(JSON.parse(fs.readFileSync(path.join(root, '.claude-plugin', 'plugin.json'), 'utf8')).version, version);
  // From `stable`, not main: the copy is the commit the branch points to. A release that
  // moves the branch during the install makes that unknowable; run the test again.
  const stable = stableNow();
  assert.equal(stable, before, 'stable moved while the test ran; run it again');
  assert.equal(execFileSync('git', ['-C', root, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(), stable);
  // Codex offers every skill in the copy under the plugin's prefix. The prompt is built
  // locally, so this needs no sign-in.
  const skills = skillsIn(path.join(root, 'skills'));
  assert.ok(skills.includes('new-website'), 'the copy has no new-website skill');
  assert.deepEqual(offeredFrom(codex('debug', 'prompt-input', 'new website'), path.join(root, 'skills')), skills);
});

test('an update runs cleanly and leaves one copy of the plugin', { skip: noCodex }, () => {
  assert.equal(versions().length, 1, 'the install test did not leave one copy');
  codex('plugin', 'marketplace', 'upgrade', 'croftweaver');
  assert.equal(versions().length, 1, `copies after the update: ${versions()}`);
  assert.match(codex('plugin', 'list'), /croftweaver@croftweaver\s+installed, enabled/);
});
