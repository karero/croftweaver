# Review trail: diff, the served-build spec checks this run's own id

Plan: `docs/reviews/SKILL-PLAN-served-build-run-id.md` (PLAN gate closed after 3 rounds, trail
`REVIEW-plan-2026-10-29-served-build-run-id.md`). DIFF gate, Normal depth: a starter test, its
config and a test-only branch of the build marker, a CI step and test script; no High-row item.
Seats: Codex and GLM 5.3 on melious, one command; the diff sent leaves out `docs/reviews/`.

| Round | Seats | Findings | Time, tokens |
|-------|-------|----------|--------------|
| 1 | Codex alone. melious out of balance; no rerun owed | 2 BUG, 2 RISK | Codex 152 s, 53,057 |

## Round 1

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| D1 | RISK | Codex | Env inheritance and `TEST_WORKER_INDEX` at config load are unverified | refuted: probed on 1.64.1 with the exact guard and the real web server, two runs, a stale id in the shell; Codex traced the same in Playwright's code in plan round 3. CI's `npm test` fails every selected run if it breaks | plan trail, "Probes" and round 3 |
| D2 | RISK | Codex | Whether `astro preview` rereads a replaced `dist/` is unverified | refuted: probed on one running preview (file rewritten, then the folder swapped); Codex traced Vite's per-request lookup in plan round 3 | plan trail, "Probes" and round 3 |
| D3 | BUG | Codex | The spec read the disk id before the server's answer, so a rebuild between the two read as "another server" | fixed: the disk id is read after the answer; each cause says "Likely cause" | spec |
| D4 | BUG | Codex | The CI comment said the spec fails when dist/ holds another id; run = served ≠ disk passes | fixed: the comment says it fails on a wrong served id and dist/ only names the cause; that case is now a passing case in the script | `template-tests.yml`, `test_served_build.sh` |

Codex also marked the BUGLOG row's two mixed-version outcomes unverified. Both were run in a copy
of the starter with the old files (before D3's rewording):

```
== new spec, old config + old marker
    Error: SITE_TEST_BUILD is not set: playwright.config.ts sets it for each run. Is this spec running under another config?
  1 failed
== new spec + new config, old marker
    Error: This folder's dist/ holds another build's id (389d9f60-…), not this run's (2dfb6b25-…): another build in this folder replaced dist/ before this test ran.
  1 failed
```

## Checks on the built change

- `bash scripts/test_served_build.sh`: every case passed (9 after D4).
- Mutation: with the spec's compare put back to disk vs served, the case "another build in this
  folder" passed and the script failed (1 case failed); the others still passed.
- `make check`: all checks passed.
- The real race (plan test 5, two `npm test` at once in one folder): not run. It depends on
  timing and is not a gate.
