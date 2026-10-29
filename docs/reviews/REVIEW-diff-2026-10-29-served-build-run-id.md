# Review trail: diff, the served-build spec checks this run's own id

Plan: `docs/reviews/SKILL-PLAN-served-build-run-id.md` (PLAN gate closed after 3 rounds, trail
`REVIEW-plan-2026-10-29-served-build-run-id.md`). DIFF gate, Normal depth: a starter test, its
config and a test-only branch of the build marker, a CI step and test script; no High-row item.
Seats: Codex and GLM 5.3 on melious, one command; the diff sent leaves out `docs/reviews/`.

| Round | Seats | Findings | Time, tokens |
|-------|-------|----------|--------------|
| 1 | Codex alone. melious out of balance; no rerun owed | 2 BUG, 2 RISK | Codex 152 s, 53,057 |
| 2 | Codex alone (`--verify`, `--base 284d8f95`); melious still out of balance | 1 BUG (wording); D3, D4 confirmed; D1, D2 still marked unverifiable, no new evidence asked beyond the trail's | Codex 91 s, 35,939 |
| 3 | Codex alone (`--verify`); melious still out of balance | none; D3–D5 confirmed | Codex 74 s, 29,366 |

Total, rounds 1–3: 3 BUG, 2 RISK. Gate closed after round 3, clean. Codex kept marking D1 and D2
unverifiable from the diff alone (its sandbox had no installed packages); the evidence is in the
plan trail, where Codex traced both in the installed code.

## Round 1

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| D1 | RISK | Codex | Env inheritance and `TEST_WORKER_INDEX` at config load are unverified | refuted: probed on 1.64.1 with the exact guard and the real web server, two runs, a stale id in the shell; Codex traced the same in Playwright's code in plan round 3. CI's `npm test` fails every selected run if it breaks | plan trail, "Probes" and round 3 |
| D2 | RISK | Codex | Whether `astro preview` rereads a replaced `dist/` is unverified | refuted: probed on one running preview (file rewritten, then the folder swapped); Codex traced Vite's per-request lookup in plan round 3 | plan trail, "Probes" and round 3 |
| D3 | BUG | Codex | The spec read the disk id before the server's answer, so a rebuild between the two read as "another server" | fixed: the disk id is read after the answer; each cause says "Likely cause" | spec |
| D4 | BUG | Codex | The CI comment said the spec fails when dist/ holds another id; run = served ≠ disk passes | fixed: the comment says it fails on a wrong served id and dist/ only names the cause; that case is now a passing case in the script | `template-tests.yml`, `test_served_build.sh` |

## Round 2

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| D5 | BUG | Codex | D3's new comment promised a rebuild between the reads cannot look like another server; served = B then disk = C still does | fixed: the comment says reading in that order makes it less frequent, and the causes stay likely ones. The case "all three differ" already runs that pattern | spec, `test_served_build.sh` |

In round 1 Codex also marked the BUGLOG row's two mixed-version outcomes unverified. Both were run in a copy
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
- The real race (plan test 5), once, after D3: in a copy of the starter with this branch's three
  files, two `npx playwright test tests/served-build.spec.ts` started a second apart in one
  folder. Run B built into the shared `dist/`, then its preview lost the port ("Port 4957 is
  already in use", "was not able to start"). Run A, whose preview held the port, failed:
  "This folder's dist/ holds another build's id (a1135439-…), not this run's (1f4654c0-…).
  Likely cause: another build in this folder replaced dist/ before this test ran." Under the
  old spec both sides of its compare would have been B's id, and A would have passed. Timing
  decides this outcome, so it is a record, not a gate.
