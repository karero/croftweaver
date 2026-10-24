import { defineConfig, devices } from '@playwright/test';
import { SITE } from './src/config';

// One preview port per site, derived from SITE.url, so two sites on the same machine
// never test against each other's server. Deliberately stable (same site → same
// port) rather than random: the port appears in baseURL and in error messages.
// Range 4330–4999, which leaves out 4321 (`astro dev`'s default). FNV-1a, 32-bit.
function portFor(key: string): number {
  let h = 2166136261;
  for (const ch of key) {
    h ^= ch.charCodeAt(0);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return 4330 + (h % 670);
}
const PORT = portFor(SITE.url);
const BASE = `http://localhost:${PORT}`;

// Tests run against a PRODUCTION build served by `astro preview` — the same static
// output Cloudflare serves. Never test a dev mock of the thing you ship.
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: { baseURL: BASE, trace: 'on-first-retry' },
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
    env: { ASTRO_PREVIEW_BACKGROUND: '1' },
  },
});
