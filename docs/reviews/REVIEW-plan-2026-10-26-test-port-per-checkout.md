# Review trail: plan, one test port per checkout

Artifact: `docs/reviews/SKILL-PLAN-test-port-per-checkout.md`. PLAN gate, Normal depth (test
setup, a test-only build-script branch and a comment in the publish script; no High-row item).
Seats: Codex (`--seat codex`, effort high) and GLM 5.3 on melious (`--seat melious`), run as two
commands with the same `--round`.

| Round | Seats | Findings | Time, tokens |
|-------|-------|----------|--------------|
| 1 | Codex, GLM 5.3 | 2 BUG, 6 RISK, 3 NIT (after dedup); 9 UNVERIFIABLE asked, all looked at | Codex 450 s, 105,659; GLM 371 s, 26,309 |
| 2 | Codex, GLM 5.3 (`--verify`) | 0 BUG, 5 RISK, 4 NIT; 2 follow-ups; prior fixes confirmed by both, F10 questioned by GLM | Codex 748 s, 126,488; GLM 452 s, 36,643 |
| 3 | Codex, GLM 5.3 (`--verify`) | 1 BUG, 4 RISK, 2 NIT (after dedup); every round-2 disposition confirmed by both | Codex 494 s, 111,004; GLM 571 s, 40,811 |
| 4 | Codex, GLM 5.3 (`--verify`, `--earned-by test-pass-condition,ci-claim`, cut: test 1's second hash and test 2's exact-message condition) | 0 BUG, 3 RISK, 1 NIT, 1 follow-up; every round-3 disposition confirmed by both | Codex 872 s, 97,534; GLM 271 s, 27,320 |

## Round 1

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| F1 | BUG | Codex, GLM | Comparing only `/` with `dist/index.html` misses a build that differs on another page or file | fixed: B now compares a random id written per test build (`dist/test-build-id.txt`) | plan §B |
| F2 | BUG | Codex, GLM (NIT) | Test 1's control (A's key back to `SITE.url`) does not make the two runs share a port (4725 vs 4581), so it cannot show a failure | fixed: test 1 is the positive run only; test 2 forces one port and shows B failing | plan, tests 1–2 |
| F3 | RISK | Codex | `git rev-parse --show-toplevel` gives two sites in one repository one key | fixed: the key is the config file's folder via `import.meta.url`; test 4 puts two starters in one repository | probe: main and worker print the same folder, also from `tests/` with `-c` |
| F4 | RISK | Codex | "Publishes from two clones are serialised by git" overclaims | fixed: narrowed to what git refuses (non-fast-forward push) and what ship.sh already names | `ship.sh:281` plain push; "A newer publish followed" |
| F5 | RISK | Codex (BUG) | The plan said no held-lock test exists; S9 in `check_ship_push.sh` is one | fixed: plan cites S9; test 6 is extra coverage of the site's copy. Re-sorted to RISK: a wrong claim about coverage, no wrong behaviour | `check_ship_push.sh:1085` |
| F6 | RISK | GLM | Tests 3 and 6 may not exercise the real hook or ship if the remote is not `origin` or the hook reads its arguments | fixed: the bare copy is `origin` with `main` and `production`; the hook uses neither argument | grep of both pre-push hooks for `$1`, `$2`, `$@`, `$*`: no match |
| F7 | RISK | Codex | Incident 1's server was not traced | fixed: the plan says it was not recorded and points to test 2 for the mechanism | plan, case 1 |
| F8 | RISK | Codex | Astro, Playwright, path and checkout claims rest on probes the reviewer could not repeat | fixed where it mattered: each claim the plan relies on names its check and date; the probes go in round 2's evidence | evidence file |
| F9 | NIT | GLM | The config's own comments ("per site, derived from SITE.url") become false | fixed: §A rewrites them | plan §A |
| F10 | NIT | GLM | Test 6's message string may not match the script | refuted: `ship.sh:153` in both template and site prints "another publish holds this clone's lock" | grep |
| F11 | NIT | GLM | Why `wait.stdout` needs `url` removed is unsupported | fixed: the plan cites `Promise.race` in Playwright's wait code | E6 |

## Round 2

Both seats confirmed F1–F9 and F11 as fixed; Codex also confirmed F10. Round 3 is owed: R2-1 to
R2-4 changed tests and the build-marker design.

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| R2-1 | RISK | Codex | Test 3 can pass with the hook not wired | fixed: test 3 checks `core.hooksPath` after `npm ci` and requires the gate's "✓ pre-push gate passed" line | plan, test 3; `pre-push:93` |
| R2-2 | RISK | Codex | Test 4's brand-kit run can be green with both tests skipped (Codex reproduced `OK (skipped=2)`) | fixed: CI's recipe (`template-tests.yml:596`, `REQUIRE_SHARP=1`), pass only with no skip | plan, test 4 |
| R2-3 | RISK | Codex | "`astro build` empties `dist/`" is unsupported, and a production build could keep the id | fixed: build-marker deletes the file when the variable is absent, so the claim is no longer relied on | plan §B |
| R2-4 | RISK | Codex | `import.meta.url` in workers and the JSON reporter's shape rest on probes the reviewer cannot repeat | fixed: raw captures in round 3's evidence; tests 1 and 4 re-check both on the built change | evidence E8–E9; plan, Judgment |
| R2-5 | RISK | GLM | The second publish may print "a publish is under way" and ask, not "another publish holds this clone's lock" | refuted: for a live holder `take_lock` prints line 153 ("another publish holds this clone's lock") and then line 163 ("a publish is under way"), asks nothing, exits 1. Test 6 now asserts both lines and the lock's owner | `ship.sh:153`, `:163`, `:178` |
| R2-6 | NIT | GLM | The 15-port inventory was computed with the rejected git-root key | fixed: recomputed with the folder key, now 16 folders, 16 ports, 4827 | node one-off over `~/Devel` |
| R2-7 | NIT | GLM | `CROFTWEAVER_TEST_BUILD` is a brand name in a generic starter | fixed: `SITE_TEST_BUILD` | plan §B |
| R2-8 | NIT | GLM | Test 2 mixed two arms with different outcomes | fixed: three arms, each with its outcome | plan, test 2 |
| R2-9 | NIT | GLM | A missing id blames only the build-marker step | fixed: the message names both causes | plan §B |
| R2-10 | follow-up | GLM | The config's existing comment on Astro ≥7.2 daemonizing (`ASTRO_PREVIEW_BACKGROUND`) has no evidence here | follow-up: older comment, not touched by this plan | — |
| R2-11 | follow-up | GLM | Round 1's evidence said no held-lock case exists | follow-up: evidence only; corrected in round 3's evidence | E7 |

## Round 3

Both seats confirmed every round-2 disposition, R2-5's refutation included. Round 4 is owed:
R3-1 to R3-3 changed tests' pass conditions. R3-4 came back a second time, so it was tested
directly instead of argued (a full run with two workers from `tests/`).

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| R3-1 | BUG | Codex | "CI runs the same job on every pull request" is wrong: the brand-kit job runs only when watched paths change | fixed: the plan says when it runs, and that the toolkit change touches those paths | `template-tests.yml:70`, `:573` |
| R3-2 | RISK | Codex, GLM | Test 2's "names the two ids" depends on timing: B can answer before A has written its id | fixed: pass is "fails, naming a wrong or a missing id"; B listening before A's build ends is checked with `lsof` | plan, test 2 |
| R3-3 | RISK | Codex | Test 3 requires "▶ pre-push gate: tests…", which only the site's hook prints; the template's prints "check, build and tests" | fixed: pass needs Playwright's "passed" summary and "✓ pre-push gate passed", printed by both hooks | template `pre-push:102`, `:117` |
| R3-4 | RISK | Codex, GLM (NIT) | The worker-folder claim combined two separate probes; nothing retained checks it | fixed: one full run, two workers, started from `tests/` with `-c`: main and both workers print the config's folder; `served-build.spec.ts` fetches through the worker's `baseURL`, so it re-checks the port on every run | probe output in round 4's evidence |
| R3-5 | NIT | GLM | A second, hand-written hash in test 1 can only fail spuriously | fixed: test 1 checks two listeners on two ports, in the two worktrees | plan, test 1 |

## Round 4

Both seats confirmed R3-1 to R3-5. Round 5 is owed by R4-1 (a changed test). Its fix is a cut:
test 2's timing-dependent arm is gone, replaced by fixed setups.

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| R4-1 | RISK | Codex | With only the timing-dependent arm, a spec that checks for a missing id but never compares ids passes every test | fixed: test 2 now has a fixed wrong-id setup (A's `dist/` against B's server, A's `webServer` dropped by a scratch config) that must fail naming both ids, and passes with the compare removed; and a fixed missing-id setup | plan, test 2 |
| R4-2 | RISK | GLM | A worker's `baseURL` may be the main process's serialised value, so the spec could not catch a worker on another port | refuted: with `baseURL` built from `process.pid`, each worker's tests saw the worker's own pid, both in the `baseURL` fixture and `info.project.use.baseURL` | probe in round 5's evidence (E11) |
| R4-3 | RISK | GLM | Test 4's claim that the brand-kit stop test depends on the port it found is unsupported | refuted: it asserts nothing serves `port` first, waits `while not serving(port)`, then `assertTrue(serving(port), "the preview server never came up")`; a wrong port fails there | `test_e2e_site.py`, stop test (E11) |
| R4-4 | NIT | GLM | `lsof -iTCP -sTCP:LISTEN` does not print working folders | fixed: test 1 names `lsof -p <pid> -a -d cwd` for that | plan, test 1 |
| R4-5 | follow-up | GLM | `check_script` may depend on GitHub, not `origin` | closed: it compares `git rev-parse "$id:scripts/ship.sh"`, where `$id` is the fetched `origin/main`; a bare `origin` serves the same | `ship.sh:249–252` (E11) |
