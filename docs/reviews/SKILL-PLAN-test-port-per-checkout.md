# Plan: one test port per checkout, not per site

Nothing is built yet. The plan goes through the plan review gate (Normal depth: test setup and
one comment in the publish script; no red team, since it touches no server, user data, login,
money, deletion or schema), then waits for the maintainer's go.

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-10-26 | this file |
| 2 | Plan review gate | ⏳ | — |
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
   another checkout's preview took the port in that minute. Playwright then saw *a* server
   answer and ran the tests against it, while its own preview failed. That is a silent wrong
   result: green or red for a build that is not this checkout's.
2. The maintainer's `npm run ship` failed its pre-push tests with Playwright's
   `http://localhost:4725/ is already used`. `lsof` showed the holder: an `astro preview`
   whose working folder was `~/Devel/croftweaver-site` itself, under another session's
   `bash scripts/ship.sh` in the same folder (the process list showed its push, pre-push hook,
   `npm test` and preview). Nothing was published.

Case 1 is two checkouts sharing a port. Case 2 is two publishes in **one** folder, so a port
per checkout alone does not fix it. The ship-from-worktree plan (D2, O5) left "a port per
checkout, as Site C has" as a separate change; this is that change.

## How

**A. Port per checkout (toolkit template, then croftweaver-site).** In `playwright.config.ts`,
key `portFor` on the checkout's root folder, from `git rev-parse --show-toplevel`, falling back
to `process.cwd()` when the folder is not a git checkout (a fresh copy of the starter). Same
hash, same range, same `strictPort` and `reuseExistingServer: false`. `SITE.url` leaves the key:
two sites already live in two folders. Site C (GenAI-Wednesday) already keys its port this way;
its SHA-256 hash, its 4400–4899 range and its `PW_PORT` override are not taken (see Judgment).
Checked 2026-10-26: git prints the resolved folder through a symlink, and Node's `process.cwd()`
in `/tmp` prints `/private/tmp`, so one folder always gives one key. Under the new key, the 15
checkouts in `~/Devel` that have a `playwright.config.ts` get 15 different ports; the primary
croftweaver-site checkout gets 4827.

**B. A test that the server answering is this checkout's build.** New spec
`tests/served-build.spec.ts`: fetch `/` from the test server and compare it, byte for byte,
with this checkout's `dist/index.html`. Checked 2026-10-26: `astro preview` serves
`dist/index.html` unchanged, and two checkouts' builds differ (`build.txt` 64952c83 vs
48995b72). If another checkout's server answers (a port clash during the build, case 1),
this test goes red, so the run cannot pass for someone else's build. A server of an identical
build passes, which is harmless: it serves the same files.

**C. Two publishes at once.** `scripts/ship.sh` already takes a lock, `ship.lock` in the clone's
shared git folder (`git rev-parse --git-common-dir`), so it covers every worktree of a clone. But
only the `ship.fromGitHub` mode takes it; the default mode, publishing the folder itself, takes
none. croftweaver-site runs the default mode (`git config --local ship.fromGitHub` is empty),
which is why case 2 could happen. No new guard: the maintainer switches the existing mode on,

```bash
cd /Users/matt/Devel/croftweaver-site && git config ship.fromGitHub true
```

after which a second publish stops at once with "another publish holds this clone's lock", and
each publish tests in its own temporary worktree, so it has its own port too. Its prerequisites
hold: the site's `prepare` runs `scripts/wire-hooks.mjs`, and its `scripts/ship.sh` must match
GitHub's `main` (the mode refuses an edited copy). Publishes from two separate clones are
already serialised by git: the second push is refused or has nothing to send.

**D. Words that become wrong.** `scripts/ship.sh`'s comment above the "test port was taken"
message says the port "comes from the site's address, so it is the same in every copy"; it now
comes from the checkout's folder. Comment only, but the file's own rule bumps `template-version`
to 0.24, with `tests/check_ship_push.sh`'s marker in step. The message itself stays true.
`skills/website-brand-kit/scripts/tests/test_e2e_site.py` re-computes the old hash from
`SITE.url` to find the port; it instead reads `config.webServer.url` from
`npx playwright test --list --reporter=json`, run in the site (checked: that output carries
`http://localhost:4725/` today), so it no longer copies the formula. `PUBLISHING.md` and the
brand-kit `SKILL.md` stay true. One `docs/BUGLOG.md` row carries the release-notes line.

**Repos and order.** karero/croftweaver first (A, B, D in one pull request), then
karero/croftweaver-site (the same `playwright.config.ts` and spec, which are identical to the
template today; its own `ship.sh` comment, keeping its 0.22 marker, as Site C did with a
comment-only edit; a note in its README's template-sync row). Each pull request gets the DIFF
gate. Then C. Other sites take A and B through `whats-new` at their next update.

## How it is tested

1. **The production entry point, two real checkouts at once (rule 9).** Two worktrees of
   croftweaver-site, B one empty commit ahead of A. Run `npm test` (what the pre-push gate
   runs) in both at the same moment. Pass: both exit 0, neither log has "already used" or
   "already in use", and while they run `lsof` shows two `astro preview` listeners whose working
   folders are the two worktrees, on the ports a hand-written FNV-1a in Python gives for each
   folder. Then once more with A's key put back to `SITE.url`: one of the two runs must fail,
   which shows the test can fail.
2. **The race of case 1, made on purpose.** Start `npm test` in A; during its build, start a
   preview of B's build on A's port. Without the new spec: A's tests run against B's server
   and A's preview logs "already in use" (a reproduction of case 1). With it:
   `served-build.spec.ts` fails, naming the mismatch.
3. **A real push.** One `git push` from a worktree to a throwaway bare repo on this Mac, so the
   real pre-push hook runs the whole gate, while the other worktree runs `npm test`.
4. **The starter.** Two copies of the template starter (one a git repo, one not), `npm ci`,
   `npm test` in both at once: green, two ports. Then the brand-kit end-to-end test
   (`BRAND_KIT_E2E_SITE`) on the non-git copy, green, which proves its port lookup.
5. **Repo checks.** Toolkit `make check`; site `npm run check`, its full suite, and
   `tests/check_ship_push.sh` (marker agreement).
6. **Two publishes at once, for real.** In a throwaway clone of croftweaver-site whose
   `origin` is a bare copy on this Mac (so nothing reaches GitHub or the live site), with
   `ship.fromGitHub` on: start `npm run ship`, and during its gate start a second one. Pass: the
   second stops at once with "another publish holds this clone's lock"; the first's gate runs on
   its temporary worktree's own port. The first is then stopped after its push, since the live
   site will never serve that commit. `check_ship_push.sh` has no held-lock case today (only a
   lock that cannot be made), so this is the only test of it.

Rollback: revert either pull request; `git config --unset ship.fromGitHub` undoes step 5.

## Known limits

- **Two runs in one folder** still share a port and a `dist/`, so one run's build can change
  the files under the other's server. Step 5 moves publishes out of the folder; other runs in
  one folder stay a matter of working in separate worktrees.
- **Hash clash.** 670 ports. With n checkouts, the chance that some pair shares a port is about
  n(n−1)/1340 (15 checkouts: about one in six). It matters only when both run at once, and then it
  is loud: Playwright's "already used" before the build, or `served-build.spec.ts` during it.
- A port is now per folder, so docs and logs can no longer name one port for a site (two
  croftweaver-site handover notes in `input/` say "4725"; they are dated notes and stay).

## Judgment calls

- **Verified:** the port formula and both incidents' causes (logs, `lsof`, process list), the
  lock's location and mode, git's and Node's path forms, byte-identical serving, the JSON port.
- **Judgment:** a test that fails (B) instead of making Playwright wait for its own server's
  "Local http://localhost:…" line (`webServer.wait.stdout`, Playwright 1.64). That option needs
  `url` removed, which removes the check before the build, so a second run in one folder would
  rebuild `dist/` under a running one instead of stopping at once. No `PW_PORT` override:
  nothing needs one once ports are per checkout. No lock for the default publish mode: a
  single owner would pay for it with a lock to remove by hand after a hard stop.
- **Strongest counter-argument:** the clash in the build window is still possible, and B only
  makes it fail; a clash between two long-lived worktrees fails every time both run, and
  without an override the only fix is to rename a folder. If that shows up, an override is
  the next step.
