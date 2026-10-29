import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

// The server answering on this run's port must be serving this run's own build. Playwright
// checks the port once, before the build, then takes any server that answers as its own; another
// checkout's preview that starts during the build would otherwise get every test run against it.
// playwright.config.ts makes a random id per run (SITE_TEST_BUILD) before the build, and
// scripts/build-marker.mjs writes it into dist/; the server must send back that same id. The id
// is fixed before the build, so a second build in this folder (its own id) is caught too, if it
// landed before this test ran. It vouches for that one file, not for every page beside it.
// The id on disk only names the cause. It is found from this spec's own location.
const ON_DISK = fileURLToPath(new URL('../dist/test-build-id.txt', import.meta.url));

test("the server answering is this run's own build", async ({ request }) => {
  const run = process.env.SITE_TEST_BUILD;
  expect(
    run,
    'SITE_TEST_BUILD is not set: playwright.config.ts sets it for each run. Is this spec running under another config?',
  ).toBeTruthy();

  let disk: string | null = null;
  try {
    disk = readFileSync(ON_DISK, 'utf8').trim();
  } catch {
    disk = null;
  }
  const res = await request.get('/test-build-id.txt');
  const served = res.status() === 200 ? (await res.text()).trim() : null;
  if (served === run) return;

  let cause: string;
  if (served === null) {
    cause =
      `The server sent no test-build id (HTTP ${res.status()} for /test-build-id.txt). Possible causes: ` +
      "this build skipped the build-marker step (does `npm run build` end with scripts/build-marker.mjs?); " +
      "the server answering is not this run's (another checkout's preview, or an `astro dev`, on this port); " +
      'or a plain `npm run build` in this folder replaced dist/ before this test ran.';
  } else if (served === disk) {
    cause =
      `This folder's dist/ holds another build's id (${served}), not this run's (${run}): ` +
      'another build in this folder replaced dist/ before this test ran.';
  } else if (disk === run) {
    cause =
      `The server sent another build's id (${served}), while this run's build in dist/ has ${run}: ` +
      "another server answers on this port (another checkout's preview, or an `astro dev`).";
  } else {
    cause =
      `The server sent ${served}, dist/ has ${disk ?? 'no id'}, this run's id is ${run}: ` +
      'another server answers on this port, and another build in this folder replaced dist/.';
  }
  expect(served, cause).toBe(run);
});
