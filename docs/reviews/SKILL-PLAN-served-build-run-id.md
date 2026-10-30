# Plan: the served-build spec checks this run's own id

Status: plan, 2026-10-29. Branch `fix/served-build-run-id`.

## What and why

`tests/served-build.spec.ts` in the starter checks that the server answering on the test port
serves this checkout's own build. It compares the id the server sends (`/test-build-id.txt`)
with the id in `dist/test-build-id.txt` on disk. Its failure message names three causes, the
third being "another build in this folder replaced dist/ during the run".

The spec cannot catch that third cause when the other build is a test build. The id is made
inside the build (`randomUUID()` in `scripts/build-marker.mjs`), and `astro preview` serves
`dist/` from disk, so a rebuild changes both sides of the compare at once and the spec passes.
The 2026-10-26 plan (`SKILL-PLAN-test-port-per-checkout.md`, Known limits) already says so; the
message does not. Codex raised it again in two sites' v0.34 updates. Every site copies the spec.

When it happens: two test runs started in one folder within one build's time of each other (two
assistants, or a person and an assistant). Both see the port free, both build into one `dist/`,
the later build wins, and the run whose server survives may be testing the other run's files.

## How

Make the id before the build, once per run, and compare against that.

1. **`playwright.config.ts`**: in the main process only (no `TEST_WORKER_INDEX`), set
   `process.env.SITE_TEST_BUILD = randomUUID()`. Workers load the config again but inherit the
   main process's environment, so they keep the same value; the web server gets it the same
   way. It is set fresh on every run, not taken from the shell, so a value left in a shell
   cannot make two runs share an id. `webServer.env` drops its `SITE_TEST_BUILD: '1'`.
   *Checked:* a probe on Playwright 1.62.1, then again on 1.64.1 (the starter's lockfile), with
   3 workers and a web server, printed one id in the main process, the web server and all three
   workers. Its config and output go in the review trail.
2. **`scripts/build-marker.mjs`**: write the value of `SITE_TEST_BUILD` into
   `dist/test-build-id.txt` instead of a new random id. Unset: delete the file, as now.
3. **`tests/served-build.spec.ts`**: the expected id is `process.env.SITE_TEST_BUILD`. It reads
   the disk id only to name the cause:
   - no run id: the spec runs under a config that does not set one;
   - served id missing: as now (marker step skipped, not this run's server, or a plain
     `npm run build` here deleted it);
   - served = disk ≠ run id: another build in this folder replaced `dist/` before this test ran;
   - disk = run id ≠ served: another server answers on this port (another checkout's preview,
     or an `astro dev`). This is the case the spec already catches, and it stays.
   - otherwise: both ids printed, both causes named.
4. Comments in the config and the marker script say what the id is now. `website-qa/SKILL.md`
   line 108 says "a random id per test build, from `scripts/build-marker.mjs`": it becomes
   "per test run, from `playwright.config.ts`". The README line stays true as it is.

## Limits, kept in the message

The spec checks once, when it runs. A rebuild that lands after it ran is not caught; the
message says "before this test ran", not "during the run". Checking again at the end of the run
(a teardown) would close that, at the cost of a second mechanism: not done here.

The id vouches for one file, not for every file beside it. The marker is the last step of a
build, so if two builds overlap, A's pages can be replaced by B's before A writes its id, and
A's check passes. Those pages can differ from A's even with no source edit (a build setting
such as `CF_PAGES_BRANCH` changes the analytics tag and email links), and a page missing only
for a moment between requests goes unseen. This plan accepts that: it is not caught. Giving each
run its own output folder would close it; that is a bigger change (Astro's `outDir`, the
preview, `ship.sh`) and not this fix. The spec's comment says the id vouches for one file only.

*Checked:* a running `astro preview` serves `dist/` from disk at each request. With one preview
up, the id it sent changed after the file was rewritten, and again after `dist/` was moved
aside and replaced by a copy (the home page still answered 200).

## How it is tested

1. **The production path, in each template-tests run that the path filter selects**
   (`template-tests.yml`, the `changes` job). The template's `npm test` runs config → web server
   env → build → spec. Pass: the spec passes, so the id reaches the build and the worker
   unchanged.
2. **Fixed setups, a new script `scripts/test_served_build.sh`**, run as a step in the same CI
   job after `npm test` (it needs the starter's `node_modules` and browser). The script is
   added to the path filter, so a change to it alone runs the job. It runs the real
   spec through `npx playwright test` with a scratch config that imports the starter's config,
   drops `webServer`, sets the run id to a known value and points `baseURL` at a small static
   server on 127.0.0.1 holding a chosen `test-build-id.txt`. The disk file is set per case.
   Each case checks the exit code and a phrase of the message:
   - all three agree: passes (the script can see a pass);
   - served = disk ≠ run id (the bug): fails, "another build in this folder";
   - disk = run id ≠ served (another checkout's server): fails, "another server";
   - served missing (404): fails, "sent no test-build id".
   Plus: `SITE_TEST_BUILD=<x> node scripts/build-marker.mjs` writes `x`, and with it unset the
   file is gone.
3. **It can fail.** With the spec's compare put back to disk vs served, case "served = disk ≠
   run id" passes and the script fails. Run once by hand, result in the PR.
4. **The exact guard, once by hand, on 1.64.1:** the starter's `npm test` twice, with
   `SITE_TEST_BUILD=stale` already exported in the shell, the spec run with
   `--repeat-each 4 --workers 3`, and a line in the spec printing the id each worker sees while
   it runs the spec (removed afterwards). Pass: both runs green, two different ids, neither
   `stale`, one id per run in every worker that ran the spec, and the same id on disk.
5. **The real race, once by hand:** two `npm test` started at once in one starter folder.
   Timing decides the outcome, so it is reported, not a gate.
6. `make check` (template coverage needs no change: no new template file).

Rollback: revert the PR. Sites take the three files together through `whats-new`, as with 0.34;
a BUGLOG "Next release notes" row says so.

## Judgment calls

- *Verified:* the rebuild passes today (both sides move); env inheritance (probe above).
- *Judgment:* a fix is worth it over just rewording the message; it is about 15 changed lines
  and keeps one mechanism. Counter-argument: the race is rare, and rewording costs nothing.
  But the spec's own message promises the check, two reviews flagged it independently, and the
  fix is small.
- *Judgment:* `TEST_WORKER_INDEX` to tell the main process from a worker. It is Playwright's
  documented worker variable; if a future Playwright stopped setting it at config load, each
  worker would make its own id and the spec would fail loudly on every run, not pass silently.
