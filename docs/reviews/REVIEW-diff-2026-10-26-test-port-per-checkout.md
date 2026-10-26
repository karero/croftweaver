# Review trail: diff, one test port per checkout (toolkit)

Change: the starter's `playwright.config.ts`, `scripts/build-marker.mjs`, new
`tests/served-build.spec.ts`, comment fixes, the brand-kit port lookup and its capture test.
Plan: `SKILL-PLAN-test-port-per-checkout.md` (its own gate is in
`REVIEW-plan-2026-10-26-test-port-per-checkout.md`). DIFF gate, Normal depth: `build-marker.mjs`
runs in every production build. Artifact: `git diff <merge-base>...HEAD -- . ':(exclude)docs/reviews/'`.
Seats: Codex (`--seat codex`, effort high) and GLM 5.3 on melious (`--seat melious`).

| Round | Seats | Findings | Time, tokens |
|-------|-------|----------|--------------|
| 1 | Codex (GLM 5.3 failed: melious "Insufficient balance … Available: 0") | 2 BUG, 2 RISK | Codex 381 s, 74,232 |
| 2 | Codex (`--verify`; melious still out) | 1 RISK; D1-1 and D1-2 confirmed | Codex 200 s, 46,491 |

## Round 1

| Id | Sev | Finding | Disposition | Evidence |
|----|-----|---------|-------------|----------|
| D1-1 | BUG | The config comment said each folder gets its own port and runs "never share a server"; a 670-port hash can clash (Codex found two folders of this repo on 4831) | fixed: "one stable port per site folder … two folders can, rarely, land on the same port; reuseExistingServer and served-build.spec.ts make that loud" | `playwright.config.ts:6–9` |
| D1-2 | BUG | The analytics-gate comment said the post-build steps touch the id "test builds only"; a plain build removes it | fixed: "written in test builds, removed otherwise" | `check_analytics_gate.sh:56–57` |
| D1-3 | RISK | Worker ESM loading, the build env and the JSON shape rest on reported runs | fixed by runs on the built change: two starter copies and two croftweaver-site worktrees passed at once on their own ports; a config loaded as CommonJS stops with "Cannot use 'import.meta' outside a module"; the brand-kit e2e passed with nothing skipped and failed when the lookup was off by one | round 2's evidence |
| D1-4 | RISK | Nothing shown rejects a wrong or a missing id | fixed by runs on the built change (plan test 2, croftweaver-site): a wrong id fails naming both ids; with the compare removed that setup passes; a missing id fails naming the three causes; case 1 reproduced (passes against another checkout's server without the spec, fails with it) | round 2's evidence |

## Round 2

Codex confirmed D1-1 and D1-2 (it also executed the hash and the marker's two branches). No
fix in round 2 changes what runs, so no round 3 is owed.

| Id | Sev | Finding | Disposition | Evidence |
|----|-----|---------|-------------|----------|
| D2-1 | RISK | D1-3 and D1-4 stay unverifiable to the reviewer: its sandbox cannot run Playwright, so the worker loading, the env reaching the build, the JSON shape and the wrong/missing-id failures rest on reported runs | refuted: each was run on the built change, outside the sandbox: two croftweaver-site worktrees at once (472 passed each, own ports and folders), the env reaching the build (each test build wrote its id), the JSON lookup (brand-kit e2e green with nothing skipped, red with the lookup off by one), a wrong id failing with both ids and passing with the compare removed, a missing id failing with the three causes, and case 1 reproduced with and without the spec. The runs' outputs are below | round 2's evidence |

Melious was out of balance for both rounds, so this gate ran on Codex alone.

## Runs on the built change (2026-10-26)

Copied from the evidence sent with rounds 1 and 2; private paths shortened.

```text
Test runs on the built change, 2026-10-26 (this Mac, load average about 60)
- Two copies of the template starter as subfolders a/ and b/ of one git repo, npm ci in each.
  Ports from 'npx playwright test --list --reporter=json' config.webServer.url: a -> http://localhost:4602/, b -> http://localhost:4379/
- npm test in a/ and b/ started at the same moment. While running:
    pid 48052 port [::1]:4379 cwd .../t4/b
    pid 48094 port [::1]:4602 cwd .../t4/a
  Both: '1 skipped, 114 passed (14.2s)', exit 0; 'already used'/'already in use' count 0 in both logs.
  The skip is positioning.spec.ts 'no positioning terms declared yet' (the starter's own, as shipped).
  Line in a's log: ✓ 92 [chromium] › tests/served-build.spec.ts:19:1 › the server answering is this run's own build
  dist/test-build-id.txt: a = a7a06153-f19c-426f-be46-2a2bf55109e3, b = 12c59824-28e9-43d0-9b37-aa28f2f66cf2
- Then 'npm run build' in a/ (no SITE_TEST_BUILD): exit 0; 'ls dist/test-build-id.txt' -> No such file or directory.
- Brand-kit e2e, CI recipe (BRAND_KIT_E2E_SITE=a, BRAND_KIT_NODE_MODULES=a/node_modules, REQUIRE_SHARP=1, Pillow 12.2.0): Ran 4 tests, OK, none skipped.
- Mutation: port_from_list_json(...) + 1 in preview_port -> FAILED (failures=1): the stop test ('the run ended before the site's tests served the build'). Restored.
- npm run check (astro check) in b/: 0 errors, 0 warnings, 1 hint; exit 0.
- bash tests/check_ship_push.sh in b/: exit 0; '✓ ship push gate: 48 publish outcomes classified correctly (...), and 252 checks on real git (...)', no 'not run', no 'skipped'.
- make check in the toolkit: 'all checks passed'; one SKIP: Perl::MinimumVersion not installed (CI checks it).
- git grep build-marker: called only by the template package.json 'build' script (astro build && node scripts/anchor-ids.mjs && node scripts/build-marker.mjs); check_analytics_gate.sh runs astro build alone into a temp folder.
- The fixture is 'npx playwright test --list --reporter=json' from croftweaver-site on Playwright 1.64.1, trimmed: config keys cut to configFile/rootDir/version/workers/webServer, suites cut to one spec; paths replaced by /srv/site. Values not edited otherwise.


Added for round 2: runs on the built change in croftweaver-site (same files as the template), 2026-10-26
- Test 1: worktree A (~/Devel/croftweaver-site-test-port) and worktree B (scratch site-b), same commit, npm test at once. Ports 4982 and 4722.
    pid 14646 [::1]:4982 cwd .../croftweaver-site-test-port ; pid 14677 [::1]:4722 cwd .../site-b
    A: 472 passed (1.5m), exit 0 ; B: 472 passed (1.5m), exit 0 ; 'already used'/'already in use': 0 and 0
    (An earlier run of the same pair failed only on the site's deck tests, because the new /checks card changed what the decks read; the decks were remade.)
- Test 2, fixed setups, scratch config {...base, testDir: A/tests, webServer: undefined}:
    In a folder without package.json type module the config failed: 'SyntaxError: Cannot use 'import.meta' outside a module'.
    Wrong id (B's preview on A's port; A id a155efaa-..., B id 0dc70f62-...): exit 1, 'Error: The server sent another build's id: it sent 0dc70f62-16a4-408d-a31f-1d03c2489c6b, this checkout's dist/ has a155efaa-4c0d-455d-ae12-65018b62bdb3. Possible causes: ...'
    Mutant, the toBe(mine) compare removed: '1 passed', exit 0. Spec restored (git diff empty).
    Missing id (A's dist/test-build-id.txt moved away): exit 1, 'Error: .../dist/test-build-id.txt is missing. Possible causes: this build skipped the build-marker step (...); the server answering is not this run's (...); or another build in this folder replaced dist/ during the run.'
- Test 2, case 1 reproduced: A runs npx playwright test (webServer builds); B's preview started on A's port the moment A's 'astro build' appeared:
    without the spec (navigation.spec.ts): B log 'Local http://localhost:4982/'; A log: 2 'already in use'; 106 passed; exit 0   <- A tested B's build, silently
    with the spec (navigation + served-build): A log: 2 'already in use'; 1 failed, 106 passed; exit 1; 'The server sent another build's id: it sent 0dc70f62-..., this checkout's dist/ has c15dabcd-...'
- Test 3: throwaway clone, origin = bare copy with main and production; npm ci; core.hooksPath = scripts/hooks; git push origin <commit>:refs/heads/production while A ran npm test:
    push log: '✓ ship push gate: 48 publish outcomes ..., and 218 checks of the mode that publishes GitHub's main, on real git' (no 'not run', no 'skipped'); '472 passed (42.9s)'; '✓ pre-push gate passed — pushing.'; push exit 0; peer: 472 passed, exit 0.
- Test 6: same clone, ship.fromGitHub true, a commit ahead: first npm run ship, then a second during its gate:
    second: exit 1; '✗ Publish stopped — another publish holds this clone's lock: ... It names process 35024 ... That process is still running, so a publish is under way. ... Nothing was published and this folder was not touched.'
    first's gate preview: pid 48099, cwd <tmp>/ship-worktree.l4EeKp, '--port 4419', LISTEN [::1]:4419; '472 passed (1.2m)'; '✓ pre-push gate passed'; '✓ Pushed.'; bare production moved to fd937c9.
    first stopped with SIGINT in its live check: 'Stopped during the live-site check. The publish went out ...'; afterwards .git/ship.lock gone and the temp worktree gone (git worktree list shows only the clone).
- croftweaver-site npm run check: 0 errors, 0 warnings, 0 hints.
```

## Wording pass

Codex, `--wording-pass --seat codex --base 09089ec1`, over this trail (77 s, 61,731 tokens). One RISK, the follow-up
that the runs had no inspectable record: closed by the section above. Its unsupported
phrase ("once per change, as the gate asks") was cut. Gate closed: no open BUG or RISK.
