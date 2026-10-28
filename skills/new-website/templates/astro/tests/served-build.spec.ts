import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// The server answering on this run's port must be serving this checkout's own build. Playwright
// checks the port once, before the build, then takes any server that answers as its own; another
// checkout's preview that starts during the build would otherwise get every test run against it.
// scripts/build-marker.mjs writes a fresh random id into dist/ for each test build (SITE_TEST_BUILD,
// set in playwright.config.ts); the server must send back the same id.
// The file is found from this spec's own location, so the working folder does not matter.
const ON_DISK = fileURLToPath(new URL('../dist/test-build-id.txt', import.meta.url));

const CAUSES =
  'Possible causes: this build skipped the build-marker step (is SITE_TEST_BUILD set in ' +
  "playwright.config.ts's webServer.env, and does `npm run build` end with scripts/build-marker.mjs?); " +
  "the server answering is not this run's (another checkout's preview, or an `astro dev`, on this port); " +
  'or another build in this folder replaced dist/ during the run.';

test("the server answering is this run's own build", async ({ request }) => {
  let mine: string | null = null;
  try {
    mine = readFileSync(ON_DISK, 'utf8').trim();
  } catch {
    mine = null;
  }
  const res = await request.get('/test-build-id.txt');
  const served = res.status() === 200 ? (await res.text()).trim() : null;

  expect(mine, `${ON_DISK} is missing. ${CAUSES}`).toBeTruthy();
  expect(served, `The server sent no test-build id (HTTP ${res.status()} for /test-build-id.txt). ${CAUSES}`).toBeTruthy();
  expect(
    served,
    `The server sent another build's id: it sent ${served}, this checkout's dist/ has ${mine}. ${CAUSES}`,
  ).toBe(mine);
});
