import { chromium, defineConfig, devices } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { existsSync, readdirSync, realpathSync, statSync } from 'node:fs';
import { cpus } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

// One stable preview port per site folder, so each checkout, worktree or clone of a site tests
// on its own server. Keyed on this file's resolved folder, which the main process and every
// worker work out the same way, from wherever Playwright starts. Two folders can, rarely, land
// on the same port; reuseExistingServer below and tests/served-build.spec.ts make that loud.
// Range 4330–4999, which leaves out 4321 (`astro dev`'s default). FNV-1a, 32-bit.
function portFor(key: string): number {
  let h = 2166136261;
  for (const ch of key) {
    h ^= ch.charCodeAt(0);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return 4330 + (h % 670);
}
const PORT = portFor(realpathSync(dirname(fileURLToPath(import.meta.url))));
const BASE = `http://localhost:${PORT}`;

// Claude Code cloud sessions ship one Chromium build under /opt/pw-browsers, and it is not always
// the build this Playwright version expects; then every browser test failed there with "Executable
// doesn't exist". A headless run launches the headless shell, not chromium.executablePath() (the
// full browser), so the shell is the build to look for: it sits beside the full one as
// chromium_headless_shell-<revision>. Only when the expected shell is missing, or its folder holds
// no executable (a partial install), launch the cloud's own build: its headless shell first (the
// full browser also fetches the favicon on its own). CI and anyone who ran
// `npx playwright install chromium` keep the pinned one.
const CLOUD_BROWSERS = process.env.SITE_TEST_CLOUD_BROWSERS ?? '/opt/pw-browsers'; // the variable is for the toolkit's own test
function expectedHeadlessBuild(): string {
  const full = chromium.executablePath();
  const m = /^(.*[\\/])chromium-(\d+)[\\/]/.exec(full);
  return m ? `${m[1]}chromium_headless_shell-${m[2]}` : full;
}
// The folder holds the shell when this platform's subfolder has the executable as a file. The names
// are Playwright's (its registry's paths, checked by the starter's test); an odd host counts as having none.
// The key follows Playwright's choice of folder, not Node's build: a Mac by its chip, so an Intel
// Node on an Apple chip (Rosetta) still finds the arm64 shell, and any Windows machine as x64.
const HOST_KEY = process.platform === 'darwin'
  ? (cpus().some((cpu) => cpu.model.includes('Apple')) ? 'darwin-arm64' : 'darwin-x64')
  : process.platform === 'win32' ? 'win32-x64' : `${process.platform}-${process.arch}`;
const SHELL_PATH: Record<string, [string, string]> = {
  'linux-x64': ['chrome-headless-shell-linux64', 'chrome-headless-shell'],
  'linux-arm64': ['chrome-headless-shell-linux-arm64', 'chrome-headless-shell'],
  'darwin-x64': ['chrome-headless-shell-mac-x64', 'chrome-headless-shell'],
  'darwin-arm64': ['chrome-headless-shell-mac-arm64', 'chrome-headless-shell'],
  'win32-x64': ['chrome-headless-shell-win64', 'chrome-headless-shell.exe'],
};
function hasHeadlessShell(folder: string): boolean {
  if (!existsSync(folder)) return false;
  if (!statSync(folder).isDirectory()) return true; // expectedHeadlessBuild() fell back to the full browser's file
  const [dir, exe] = SHELL_PATH[HOST_KEY] ?? [];
  const file = dir && join(folder, dir, exe);
  return !!file && existsSync(file) && statSync(file).isFile();
}
function cloudChromium(): string | undefined {
  if (hasHeadlessShell(expectedHeadlessBuild()) || !existsSync(CLOUD_BROWSERS)) return undefined;
  const shell = readdirSync(CLOUD_BROWSERS).filter((name) => name.startsWith('chromium_headless_shell-')).sort().pop();
  return [
    ...(shell ? [join(CLOUD_BROWSERS, shell, 'chrome-headless-shell-linux64', 'chrome-headless-shell')] : []),
    join(CLOUD_BROWSERS, 'chromium'),
  ].find((path) => existsSync(path));
}
const cloudExecutable = cloudChromium();
const launchOptions = cloudExecutable ? { executablePath: cloudExecutable } : {};

// One random id per test run, made here in the main process before the build. The web server
// (whose build writes it into dist/test-build-id.txt) and every worker inherit it; workers load
// this file again, so they keep the inherited value. tests/served-build.spec.ts checks the server
// sends this id, which catches another checkout's server and another build in this folder.
if (!process.env.TEST_WORKER_INDEX) process.env.SITE_TEST_BUILD = randomUUID();

// Tests run against a PRODUCTION build served by `astro preview` — the same static
// output Cloudflare serves. Never test a dev mock of the thing you ship.
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: { baseURL: BASE, trace: 'on-first-retry', launchOptions },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npm run build && npm run preview -- --port ${PORT}`,
    url: `${BASE}/`,
    timeout: 120_000,
    // Never reuse a server that already holds the port. Reusing skips the build and
    // runs the tests against whatever is listening — a stale build of this site, or an
    // orphaned preview of another one (seen live: a leftover `astro preview` held the
    // then-shared port for two days and a second site's tests passed against its build).
    // The honest outcome is Playwright's "<url> is already used, make sure that nothing
    // is running on the port/url or set reuseExistingServer:true": stop the stale
    // preview and re-run — do NOT take the message's second suggestion, that is the
    // silent-reuse bug this line exists to prevent. (A non-HTTP squatter is caught by
    // `strictPort` in astro.config.mjs instead: the preview refuses to start and this
    // run fails with "Process from config.webServer was not able to start".)
    reuseExistingServer: false,
    // Astro >=7.2's `astro preview` auto-daemonizes when it detects an AI coding
    // agent as its caller (isRunByAgent()), even without --background — the launcher
    // process then exits immediately and Playwright reports "exited early" even
    // though a server is listening. Astro only checks this var for truthiness
    // (plain `!`/`!!`, no special-casing of any string), so any non-empty value
    // short-circuits the check — use '1', not 'false': the string 'false' is
    // truthy too and "works", but reads as an off-switch and invites a future
    // edit that silently reintroduces this bug.
    // SITE_TEST_BUILD, set above, reaches the build through the inherited environment.
    env: { ASTRO_PREVIEW_BACKGROUND: '1' },
  },
});
