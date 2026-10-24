#!/usr/bin/env node
// `npm run verify` — the one check before a pull request, and what the pre-push hook runs.
// CI's install, check, build and test steps (.github/workflows/ci.yml), in one command, with
// short output. Two differences from CI, both on purpose: an unfilled "[MISSING: …]"
// placeholder only warns here (CI fails on it, so a draft pull request can still be pushed;
// AGENTS.md §2), and CI also runs tests/check_ship_push.sh, which the pre-push hook runs too.
//  1. `npm ci`, only on the first run here or when package.json or package-lock.json changed
//     since the last install it made (a hash in node_modules/.verify-lock-hash). Every other
//     run keeps node_modules. package.json counts too: edited without the lockfile, the two
//     disagree, and CI's `npm ci` fails on that, so this one must as well.
//  2. `npm run check` (astro check). Its output is shown only when it fails.
//  3. `npm test` with Playwright's dot reporter: one dot per passed test, the warnings the
//     tests print (placeholders, positioning), then each failure in full and a summary.
//     Playwright builds the site itself (webServer in playwright.config.ts), so nothing
//     here runs `npm run build` separately: one build per run, not two.
// Exit 0 only when every step is green. The pre-push hook calls this file directly
// (`node scripts/verify.mjs`), so the hook works even where package.json has no
// "verify" line; `npm run verify` needs "verify": "node scripts/verify.mjs" there.
//
// Why a Node script and not a line in package.json: npm hands a script line to sh on
// macOS and Linux and to cmd.exe on Windows, and the conditional install in step 1 is not
// something both read the same way.
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

// The site is the folder that holds scripts/, wherever this was started from.
const site = join(dirname(fileURLToPath(import.meta.url)), '..');

// Run through npm (`npm run verify`), npm_execpath names npm's own entry, npm-cli.js: start
// that with this node, no shell. Under pnpm or yarn it names theirs, which has no `npm ci`,
// so only npm's counts. Started directly (the hook), use the npm on PATH; on Windows that is
// npm.cmd, which Node starts only through a shell.
// maxBuffer: captured output past Node's default (1 MiB) kills the step with ENOBUFS, and a
// passing check with many hints would then read as red.
function npm(args, capture) {
  const opts = {
    cwd: site,
    encoding: 'utf8',
    stdio: capture ? ['ignore', 'pipe', 'pipe'] : 'inherit',
    maxBuffer: 256 * 1024 * 1024,
  };
  const entry = process.env.npm_execpath;
  const viaEntry = Boolean(entry && /[\\/]npm-cli\.c?js$/.test(entry));
  // VERIFY_TRACE=1 names the branch once, so a test (CI on Windows) can prove which one ran.
  if (process.env.VERIFY_TRACE && !npm.traced) {
    npm.traced = true;
    const viaShell = process.platform === 'win32' ? ' (through a shell)' : '';
    console.log(viaEntry ? 'verify: npm via npm_execpath (npm-cli.js)' : `verify: npm from PATH${viaShell}`);
  }
  if (viaEntry) return spawnSync(process.execPath, [entry, ...args], opts);
  if (process.platform !== 'win32') return spawnSync('npm', args, opts);
  // On Windows: one command string, not an args array. Node deprecates args with
  // shell: true (DEP0190, printed on every run). Joining is safe only for plain words, so
  // anything else (a space, a quote, one of cmd.exe's & | ^ < > %) stops here, not in cmd.exe.
  const unsafe = args.find((a) => !/^[\w@/.:=-]+$/.test(a));
  if (unsafe !== undefined) throw new Error(`verify.mjs: npm argument not safe for cmd.exe: ${unsafe}`);
  return spawnSync(['npm', ...args].join(' '), { ...opts, shell: true });
}

// Print what a captured step wrote (it stayed hidden while the step ran), then stop.
// astro check colours its output even into a pipe; read by an assistant or a log, the
// colour codes are only noise, so they go unless a person is watching a terminal.
const plain = (text, stream) => (stream.isTTY ? text : text.replace(/\x1b\[[0-9;]*m/g, ''));
function fail(what, res, after = ' Nothing after it ran.') {
  if (res?.error) console.error(String(res.error.message || res.error));
  if (res?.stdout) process.stdout.write(plain(res.stdout, process.stdout));
  if (res?.stderr) process.stderr.write(plain(res.stderr, process.stderr));
  console.error(`✗ verify: ${what} failed (output above).${after}`);
  process.exit(1);
}

// 1. Packages. CI installs with `npm ci` from the committed lockfile, so this does too,
// but only when package.json or the lockfile differs from what the last install here used.
const lock = join(site, 'package-lock.json');
if (!existsSync(lock)) {
  console.error('✗ verify: no package-lock.json. CI installs with `npm ci`, which needs it: run `npm install` and commit the file.');
  process.exit(1);
}
const modules = join(site, 'node_modules');
const stamp = join(modules, '.verify-lock-hash');
const manifest = join(site, 'package.json');
const hash = createHash('sha256').update(readFileSync(lock));
if (existsSync(manifest)) hash.update('\0').update(readFileSync(manifest));
const want = hash.digest('hex');
const have = existsSync(stamp) ? readFileSync(stamp, 'utf8').trim() : '';
if (want !== have) {
  console.log('▶ verify: installing the exact packages (first run, or package.json or package-lock.json changed)…');
  const res = npm(['ci', '--no-audit', '--no-fund', '--loglevel=error'], true);
  if (res.error || res.status !== 0) fail('npm ci', res);
  mkdirSync(modules, { recursive: true });
  writeFileSync(stamp, want + '\n');
}

// 2. Types and templates.
const check = npm(['run', '--silent', 'check'], true);
if (check.error || check.status !== 0) fail('npm run check (astro check)', check);
console.log('✓ verify: npm run check');

// 3. Build and tests, streamed: a run takes a while and the dots show it is moving.
console.log('▶ verify: build and tests…');
const test = npm(['run', '--silent', 'test', '--', '--reporter=dot'], false);
if (test.error || test.status !== 0) fail('npm test', test.error ? test : null, '');
console.log('✓ verify: all green');
