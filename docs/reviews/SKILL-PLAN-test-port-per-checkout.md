# Plan: one test port per checkout, not per site

Nothing is built yet. The plan goes through the plan review gate (Normal depth: test setup, a
test-only branch in the build-marker script, one comment in the publish script; no red team,
since it touches no server, user data, login, money, deletion or schema), then waits for the
maintainer's go.

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-10-26 | this file |
| 2 | Plan review gate | ⏳ round 1: 2 BUGs, 6 RISKs, 3 NITs; round 2: no BUG, 5 RISKs, 4 NITs; all taken into this text | `REVIEW-plan-2026-10-26-test-port-per-checkout.md` |
| 3 | Toolkit change (one pull request) | ⬜ | — |
| 4 | croftweaver-site copy (one pull request) | ⬜ | — |
| 5 | `ship.fromGitHub` switched on in the maintainer's croftweaver-site clone | ⬜ the maintainer's step | — |

## What and why

The starter's `playwright.config.ts` derives the test server's port from `SITE.url`
(`portFor`, FNV-1a, 4330–4999). Every checkout of one site therefore uses the same port:
4725 for croftweaver.com. Sessions work in parallel worktrees, and on 2026-10-26 that broke
two things in croftweaver-site:

1. A test run logged `[WebServer] Error: Port 4725 is already in use` partway through and kept
   going. Playwright checks the port once, before the build; the build takes about a minute;
   another server can take the port in that minute. Playwright then sees *a* server answer and
   runs the tests against it, while its own preview fails (Playwright's code, evidence E6: the
   check is made once, and any answer on the URL counts as ready). Which server took the port
   in this incident was not recorded; the mechanism is reproduced in test 2 below. The result
   is silent: green or red for a build that is not this checkout's.
2. The maintainer's `npm run ship` failed its pre-push tests with Playwright's
   `http://localhost:4725/ is already used`. `lsof` showed the holder: an `astro preview`
   whose working folder was `~/Devel/croftweaver-site` itself, under another session's
   `bash scripts/ship.sh` in the same folder (the process list showed its push, pre-push hook,
   `npm test` and preview). Nothing was published.

Case 1 is two servers on one port. Case 2 is two publishes in **one** folder, so a port per
checkout alone does not fix it. The ship-from-worktree plan (D2, O5) left "a port per checkout,
as Site C has" as a separate change; this is that change.

## How

**A. Port per site folder (toolkit template, then croftweaver-site).** In `playwright.config.ts`,
key `portFor` on the resolved folder that holds the config file:
`realpathSync(dirname(fileURLToPath(import.meta.url)))`. Same hash, same range, same
`strictPort` and `reuseExistingServer: false`; `SITE.url` leaves the key. Each worktree and
each clone is its own folder, and so is each site when one repository holds several. Checked
2026-10-26 with Playwright 1.64.1 and `"type": "module"` (the starter's): the main process and
its workers print the same folder, also when Playwright is started from `tests/` with
`-c ../playwright.config.ts`, where `process.cwd()` differs. A config loaded as CommonJS would
stop at `import.meta` with a syntax error, which is loud. Site C (GenAI-Wednesday) keys on
`git rev-parse --show-toplevel` instead; that gives two sites in one repository one key, so it
is not taken, nor its SHA-256 hash, 4400–4899 range or `PW_PORT` override. The config's
comments ("One preview port per site, derived from SITE.url", "same site → same port") are
rewritten to match. For the record, computed 2026-10-26 with this key: the 16 folders in
`~/Devel` (and their `.claude/worktrees/`) that hold a `playwright.config.ts` get 16 different
ports; the primary croftweaver-site checkout gets 4827.

**B. A test that the server answering is this run's own build.** `scripts/build-marker.mjs`
gets one branch: when `SITE_TEST_BUILD` is set, it writes `dist/test-build-id.txt` with a
fresh random id (`crypto.randomUUID()`); when it is not set, it deletes that file if present,
so a production build never carries one, whether or not `astro build` cleared `dist/`. The
config sets the variable in `webServer.env` only. New spec `tests/served-build.spec.ts`: fetch
`/test-build-id.txt` from the test server and compare it with this checkout's
`dist/test-build-id.txt` on disk. Another checkout's server serves another id, whatever its
commit or pages. When either side is missing, the message names both causes: this build skipped
the marker step, or the server answering is not this run's (another checkout's preview, or an
`astro dev`). Checked 2026-10-26: `astro preview` serves `dist/` files byte for byte.

**C. Two publishes at once.** `scripts/ship.sh` already takes a lock, `ship.lock` in the clone's
shared git folder (`git rev-parse --git-common-dir`), so it covers every worktree of a clone,
and `check_ship_push.sh` case S9 tests a second publish against a held lock. But only the
`ship.fromGitHub` mode takes it; the default mode, publishing the folder itself, takes none.
croftweaver-site runs the default mode (`git config --local ship.fromGitHub` is empty), which
is why case 2 could happen. No new guard: the maintainer switches the existing mode on,

```bash
cd /Users/matt/Devel/croftweaver-site && git config ship.fromGitHub true
```

after which a second publish from that clone stops at once ("another publish holds this
clone's lock", `ship.sh` line 153), and each publish tests in its own temporary worktree, so it
gets its own port. Prerequisites, checked: the site's `prepare` runs `scripts/wire-hooks.mjs`;
the mode refuses a `scripts/ship.sh` whose content differs from GitHub's `main` (`check_script`,
by git's hash), so the clone's copy must be up to date. Publishes from two separate clones are
not serialised by anything beyond git itself: the push is a plain `git push origin
<commit>:refs/heads/production`, which git refuses unless it is a fast-forward, and the live
check names a newer publish ("A newer publish followed"). That stays as it is.

**D. Words that become wrong.** `scripts/ship.sh`'s comment above the "test port was taken"
message says the port "comes from the site's address, so it is the same in every copy"; it now
comes from the site's folder. Comment only, but the file's own rule bumps `template-version`
to 0.24, with `tests/check_ship_push.sh`'s marker in step. The message itself stays true.
`skills/website-brand-kit/scripts/tests/test_e2e_site.py` re-computes the old hash from
`SITE.url` to find the port; it instead reads `config.webServer.url` from
`npx playwright test --list --reporter=json`, run in the site (checked: that output carries
`http://localhost:4725/` today), so it no longer copies the formula. `PUBLISHING.md` line 229
("Another test run, or a preview of the site … is using the port the checks need") and the
brand-kit `SKILL.md` line 290 ("the killed run's tests may still hold the site's preview port")
stay true. One `docs/BUGLOG.md` row carries the release-notes line.

**Repos and order.** karero/croftweaver first (A, B, D in one pull request), then
karero/croftweaver-site (the same `playwright.config.ts`, `build-marker.mjs` branch and spec,
whose current copies are identical to the template's; its own `ship.sh` comment, keeping its
0.22 marker, as Site C did with a comment-only edit; a note in its README's template-sync row).
Each pull request gets the DIFF gate. Then C. Other sites take A and B through `whats-new` at
their next update.

## How it is tested

1. **The production entry point, two real checkouts at once (rule 9).** Two worktrees of
   croftweaver-site. Run `npm test` (what the pre-push gate runs) in both at the same moment.
   Pass: both exit 0, neither log has "already used" or "already in use", and while they run
   `lsof` shows two `astro preview` listeners whose working folders are the two worktrees, on
   the ports a hand-written FNV-1a in Python gives for each folder.
2. **Case 1, made on purpose, to show B can fail.** Force one port: in worktree A, start
   `npm test`; during its build, start `astro preview` of worktree B's `dist/` on A's port.
   Without the new spec: A's tests run against B's server and A's preview logs "already in
   use", which reproduces case 1. With it, and B built with the marker branch:
   `served-build.spec.ts` fails, and its message names the two ids. With it, and B built
   without the branch: the spec fails on the missing id, naming both causes.
3. **A real push.** In a throwaway clone whose `origin` is a bare copy on this Mac (with `main`
   and `production`), after `npm ci` (whose `prepare` wires the hook; pass only if
   `git config core.hooksPath` then prints `scripts/hooks`), one `git push origin
   <commit>:refs/heads/production` while a worktree runs `npm test`. Pass: the push log shows
   "▶ pre-push gate: tests…" and "✓ pre-push gate passed", and both exit 0. The hook takes no
   notice of the remote's name or address (it uses neither argument).
4. **The starter.** Two copies of the template starter as two subfolders of one git repository,
   `npm ci`, `npm test` in both at once: green, two ports, which also shows two sites in one
   repository no longer share a key. Then the brand-kit end-to-end test on one copy, with CI's
   recipe (`template-tests.yml` line 596: `BRAND_KIT_E2E_SITE`, `BRAND_KIT_NODE_MODULES` at its
   `node_modules`, `REQUIRE_SHARP=1`). Pass: no test skipped, which proves its port lookup; CI
   runs the same job on every pull request.
5. **Repo checks.** Toolkit `make check`; site `npm run check`, its full suite, and
   `tests/check_ship_push.sh` (S9 and marker agreement).
6. **The publish mode in croftweaver-site.** In the throwaway clone of test 3, with
   `ship.fromGitHub` on: start `npm run ship`, and during its gate start a second one. Pass: the
   second exits 1 at once, printing "another publish holds this clone's lock" and "a publish is
   under way" (both lines print for a live holder, `ship.sh` lines 153 and 163; it asks
   nothing), and the lock still names the first; the first's gate runs on its temporary
   worktree's own port. The first is stopped after its push, since the live site will
   never serve that commit. This adds to S9: it runs croftweaver-site's own copy and checks its
   prerequisites.

Rollback: revert either pull request; `git config --unset ship.fromGitHub` undoes step 5.

## Known limits

- **Two runs in one folder** still share a port and a `dist/`, so one run's build can change
  the files under the other's server, and B cannot see it (both read the same `dist/`). Step 5
  moves publishes out of the folder; other runs in one folder stay a matter of working in
  separate worktrees.
- **Hash clash.** 670 ports. With n folders, the chance that some pair shares a port is about
  n(n−1)/1340 (16 folders: about one in six). It matters only when both run at once, and then
  it is loud: Playwright's "already used" before the build, or B's spec during it.
- A port is now per folder, so docs and logs can no longer name one port for a site (two
  croftweaver-site handover notes in `input/` say "4725"; they are dated notes and stay).

## Judgment calls

- **Verified:** the port formula and case 2's cause (log, `lsof`, process list), the race in
  Playwright's code, the lock's location and mode, S9, `import.meta.url` in main and workers,
  byte-identical serving, the JSON port, the push command, the hook ignoring its arguments.
  Each of these is a probe run once on this Mac; tests 1 and 4 run the two that the build
  depends on (workers on their own port, the brand-kit lookup) again on the built change.
- **Judgment:** a test that fails (B) instead of making Playwright wait for its own server's
  "Local http://localhost:…" line (`webServer.wait.stdout`). Playwright starts the tests when
  either the URL answers or that line appears (`Promise.race`, E6), so the line only helps with
  `url` removed, and that removes the check before the build: a second run in one folder would
  rebuild `dist/` under a running one instead of stopping at once. No `PW_PORT` override:
  nothing needs one once ports are per folder. No lock for the default publish mode: a single
  owner would pay for it with a lock to remove by hand after a hard stop.
- **Strongest counter-argument:** B adds a test-only branch to a script that runs in every
  production build, for a clash that per-folder ports make rare. And a clash between two
  long-lived folders fails every time both run; without an override the only fix is to rename
  a folder. If that shows up, an override is the next step.
