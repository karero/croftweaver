// Tests for the starter's playwright.config.ts cloud fallback: which browser a headless run
// launches when Claude Code's cloud sessions ship their own Chromium under /opt/pw-browsers.
// Run on the starter with its real node_modules:
//   MAKE_ICONS_NODE_MODULES=<the starter's node_modules> node --test skills/new-website/scripts/tests/playwright-config.test.mjs
// template-tests.yml runs it. The config is loaded as a program (node strips its types) in a
// folder of its own, with Playwright's browser folder and the cloud folder made by hand.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { chmodSync, cpSync, existsSync, mkdirSync, mkdtempSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TEMPLATE = path.resolve(HERE, '..', '..', 'templates', 'astro');
const NODE_MODULES = process.env.MAKE_ICONS_NODE_MODULES;
assert.ok(NODE_MODULES && existsSync(path.join(NODE_MODULES, '@playwright', 'test')),
  'set MAKE_ICONS_NODE_MODULES to the starter\'s node_modules (npm ci in templates/astro)');

// The launch options the config gives a run, with Playwright's browsers in `ms` and the cloud's in `cloud`.
function launchOptions(ms, cloud) {
  const site = mkdtempSync(path.join(tmpdir(), 'pwconf-'));
  cpSync(path.join(TEMPLATE, 'playwright.config.ts'), path.join(site, 'playwright.config.ts'));
  symlinkSync(NODE_MODULES, path.join(site, 'node_modules'));
  const env = { ...process.env, PLAYWRIGHT_BROWSERS_PATH: ms, SITE_TEST_CLOUD_BROWSERS: cloud };
  const r = spawnSync(process.execPath, ['--input-type=module', '-e',
    "const m = await import('./playwright.config.ts'); console.log(JSON.stringify(m.default.use.launchOptions));"],
  { cwd: site, encoding: 'utf8', env });
  assert.equal(r.status, 0, r.stderr);
  return JSON.parse(r.stdout);
}

// The folder name Playwright expects for the headless shell, read from where it puts the full browser.
function expectedShell(ms) {
  const r = spawnSync(process.execPath, ['-e', "console.log(require('@playwright/test').chromium.executablePath())"],
    { cwd: NODE_MODULES, encoding: 'utf8', env: { ...process.env, PLAYWRIGHT_BROWSERS_PATH: ms } });
  const m = /chromium-(\d+)[\\/]/.exec(r.stdout);
  assert.ok(m, `no chromium-<revision> in ${r.stdout}`);
  return path.join(ms, `chromium_headless_shell-${m[1]}`);
}

function world() {
  const root = mkdtempSync(path.join(tmpdir(), 'pwworld-'));
  const ms = path.join(root, 'ms');
  const cloud = path.join(root, 'cloud');
  mkdirSync(ms);
  const cloudShell = path.join(cloud, 'chromium_headless_shell-9999', 'chrome-headless-shell-linux64', 'chrome-headless-shell');
  mkdirSync(path.dirname(cloudShell), { recursive: true });
  writeFileSync(cloudShell, '');
  chmodSync(cloudShell, 0o755);
  return { ms, cloud, cloudShell, shell: expectedShell(ms) };
}

test('the pinned shell is installed: the config keeps it', () => {
  const w = world();
  mkdirSync(path.join(w.shell, 'chrome-headless-shell-linux64'), { recursive: true });
  writeFileSync(path.join(w.shell, 'chrome-headless-shell-linux64', 'chrome-headless-shell'), '');
  assert.deepEqual(launchOptions(w.ms, w.cloud), {});
});

test('the pinned shell is missing: the config launches the cloud\'s own', () => {
  const w = world();
  assert.deepEqual(launchOptions(w.ms, w.cloud), { executablePath: w.cloudShell });
});

test('the pinned shell\'s folder is there but holds no executable (a partial install): the config launches the cloud\'s own', () => {
  const w = world();
  mkdirSync(path.join(w.shell, 'chrome-headless-shell-linux64'), { recursive: true });
  writeFileSync(path.join(w.shell, 'INSTALLATION_COMPLETE'), '');
  assert.deepEqual(launchOptions(w.ms, w.cloud), { executablePath: w.cloudShell });
});

test('the pinned shell is missing and there is no cloud folder: nothing changes', () => {
  const w = world();
  assert.deepEqual(launchOptions(w.ms, path.join(path.dirname(w.cloud), 'none')), {});
});
