# Review trail: plan, the served-build spec checks this run's own id

Artifact: `docs/reviews/SKILL-PLAN-served-build-run-id.md`. PLAN gate, Normal depth (test setup,
a test-only branch of a build script, a CI step; no High-row item). Seats: Codex and GLM 5.3 on
melious, one command (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`).

| Round | Seats | Findings | Time, tokens |
|-------|-------|----------|--------------|
| 1 | Codex alone. melious out of balance ("Insufficient balance … Available: 0"); no rerun owed | 1 BUG, 2 RISK | Codex 142 s, 80,020 |
| 2 | Codex alone (`--verify`); melious still out of balance | 1 BUG (P2's fix overclaimed); P1, P3 confirmed | Codex 78 s, 37,980 |
| 3 | Codex alone (`--verify`); melious still out of balance | 1 RISK; P1–P4 confirmed, and Codex traced the Playwright and Astro claims in their code | Codex 124 s, 53,704 |

Total, rounds 1–3: 2 BUG, 3 RISK. Gate closed after round 3: no BUG open, P5 fixed.

## Round 1

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| P1 | BUG | Codex | "Every CI run" is wrong: `template-tests.yml` skips the job when no listed path changed, and the new script is not listed | fixed: test 1 says "each run the path filter selects"; test 2 adds the script to the filter | `template-tests.yml:70,82` |
| P2 | RISK | Codex | The id vouches for the marker, not the pages: overlapping builds can leave B's pages under A's id | fixed: written down as a limit, with why it is mostly harmless (one folder, one source) and what would close it | plan, "Limits" |
| P3 | RISK | Codex | The env-inheritance probe ran on 1.62.1, the lockfile has 1.64.1, and the probe is not recorded | fixed: rerun on 1.64.1, recorded below | below |

## Round 2

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| P4 | BUG | Codex | P2's fix said overlapping builds leave the same pages; a build setting (`CF_PAGES_BRANCH`) changes the analytics tag and email links with no source edit, and a page missing between requests goes unseen | fixed: the plan drops the assurance and states the limit as accepted, not caught | `src/config.ts:116`, `src/components/EmailLink.astro:31–44` |

Codex asked again for a probe of the exact guard (`TEST_WORKER_INDEX`, a value already in the shell, two runs): added as test 4, run on the built change.

## Round 3

| Id | Sev | Seat | Finding | Disposition | Evidence |
|----|-----|------|---------|-------------|----------|
| P5 | RISK | Codex | Test 4 claims every worker, but a log line inside one test sees only the worker running it | fixed: test 4 runs the spec `--repeat-each 4 --workers 3` and claims only the workers that ran it | test 4 output below |

Codex verified in round 3, from the installed code: Playwright 1.64.1 forwards the environment to
workers and sets the worker index before loading the config; `astro preview` looks files up on
disk per request.

## Notes

In round 1 Codex also asked whether a running `astro preview` serves a replaced `dist/` (marked
UNVERIFIABLE). Checked on the starter: yes, see below.

## Probes

Env inheritance, Playwright 1.64.1, a scratch folder with the starter's `node_modules`. Config:

```ts
process.env.PROBE_ID ??= randomUUID();
console.log(`config pid=${process.pid} worker=${process.env.TEST_WORKER_INDEX ?? '-'} id=${process.env.PROBE_ID}`);
// workers: 3; webServer: a node http server answering with process.env.PROBE_ID
```

Output (four one-line specs, each fetching `/` and comparing with its own `process.env.PROBE_ID`):

```
config pid=83999 worker=- id=b916e925-2d5c-42c7-b452-d3ba08be5366
[WebServer] server sees b916e925-2d5c-42c7-b452-d3ba08be5366
config pid=85433 worker=1 id=b916e925-2d5c-42c7-b452-d3ba08be5366
config pid=85411 worker=2 id=b916e925-2d5c-42c7-b452-d3ba08be5366
config pid=85410 worker=0 id=b916e925-2d5c-42c7-b452-d3ba08be5366
  4 passed (11.0s)
```

`astro preview` and a replaced `dist/`: the starter built with `SITE_TEST_BUILD=1`, one
`astro preview --port 4777`, then:

```
before: aa167c1d-0c53-4078-8d18-f24bce8637d7
after-file: replaced-file          # dist/test-build-id.txt rewritten
after-dir-swap: whole-dir-swap home=200   # dist/ moved aside, a copy put in its place
```

Test 4, on the built change (the starter in this branch, Playwright 1.64.1, real web server),
with `export SITE_TEST_BUILD=stale` first and a temporary `console.log` in the spec:

```
== run 1
PROBE worker=2 run=cc8c7e1d-1756-4eb5-aef2-e05eb5f1d26f
PROBE worker=1 run=cc8c7e1d-1756-4eb5-aef2-e05eb5f1d26f
PROBE worker=0 run=cc8c7e1d-1756-4eb5-aef2-e05eb5f1d26f
PROBE worker=3 run=cc8c7e1d-1756-4eb5-aef2-e05eb5f1d26f
  4 passed (36.3s)
disk: cc8c7e1d-1756-4eb5-aef2-e05eb5f1d26f
== run 2
PROBE worker=0 run=838ac6c3-fe01-4c00-a6ce-01e02681c0af
PROBE worker=2 run=838ac6c3-fe01-4c00-a6ce-01e02681c0af
PROBE worker=1 run=838ac6c3-fe01-4c00-a6ce-01e02681c0af
PROBE worker=3 run=838ac6c3-fe01-4c00-a6ce-01e02681c0af
  4 passed (15.4s)
disk: 838ac6c3-fe01-4c00-a6ce-01e02681c0af
```
