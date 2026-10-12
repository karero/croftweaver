# DIFF review — PR #275 — website-tagline: an opt-in test for the line on the page
Base `6905a21` · depth: Normal (a test that is copied into users' sites, a new CI job, and an instruction file) · verdict: OPEN · authority used: POST AUTHORITY — atom A (this session opened #275); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch)

Normal gate: Codex and GLM 5.3 on melious.ai as the pair, and a fresh-eyes pass on a mid-tier host-family model in round 1.

Data check before round 1: the diff holds no key, token or password (searched for `api key`, `secret`, `token`, `passw`, `PRIVATE`; no hit). Destinations: Codex and melious.ai, as for #270 earlier in this session, where the owner approved a plan naming both; the owner then asked for this PR to be merged after being told the Normal review with the same pair came first.

Test records, taken before round 1:
- The new CI job's three steps, read out of the workflow file as committed, run on a Mac against a site built from the starter: 4 skipped (unconfigured); type check passed, the whole suite 71 passed and 1 skipped (a correct site); six times "red as expected", one per mistake; exit status 0. The whole log (140 lines) is in the gate's PR comment.
- CI on head `7dbc7e1`: 39 checks passed, among them `tagline-skill` (1 m 15 s, on Linux) and `template-tests-ok`.
- `make check` on a tree identical to `7dbc7e1`: exit status 0. Its output was not kept; the same guards ran in CI on that head.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `7dbc7e1` | full: `origin/main...7dbc7e1` without `docs/reviews/`, 5 files | running | | |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
