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

## Round 1

| Id | Sev | Finding | Disposition | Evidence |
|----|-----|---------|-------------|----------|
| D1-1 | BUG | The config comment said each folder gets its own port and runs "never share a server"; a 670-port hash can clash (Codex found two folders of this repo on 4831) | fixed: "one stable port per site folder … two folders can, rarely, land on the same port; reuseExistingServer and served-build.spec.ts make that loud" | `playwright.config.ts:6–9` |
| D1-2 | BUG | The analytics-gate comment said the post-build steps touch the id "test builds only"; a plain build removes it | fixed: "written in test builds, removed otherwise" | `check_analytics_gate.sh:56–57` |
| D1-3 | RISK | Worker ESM loading, the build env and the JSON shape rest on reported runs | fixed by runs on the built change: two starter copies and two croftweaver-site worktrees passed at once on their own ports; a config loaded as CommonJS stops with "Cannot use 'import.meta' outside a module"; the brand-kit e2e passed with nothing skipped and failed when the lookup was off by one | round 2's evidence |
| D1-4 | RISK | Nothing shown rejects a wrong or a missing id | fixed by runs on the built change (plan test 2, croftweaver-site): a wrong id fails naming both ids; with the compare removed that setup passes; a missing id fails naming the three causes; case 1 reproduced (passes against another checkout's server without the spec, fails with it) | round 2's evidence |
