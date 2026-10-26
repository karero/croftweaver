# Review trail: plan, one test port per checkout

Artifact: `docs/reviews/SKILL-PLAN-test-port-per-checkout.md`. PLAN gate, Normal depth (test
setup, a test-only build-script branch and a comment in the publish script; no High-row item).
Seats: Codex (`--seat codex`, effort high) and GLM 5.3 on melious (`--seat melious`), run as two
commands with the same `--round`.

| Round | Seats | Findings | Time, tokens |
|-------|-------|----------|--------------|
| 1 | Codex, GLM 5.3 | 2 BUG, 6 RISK, 3 NIT (after dedup); 9 UNVERIFIABLE asked, all looked at | Codex 450 s, 105,659; GLM 371 s, 26,309 |

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
