# Review trail: the starter ships with analytics off (`claude/analytics-off-by-default-220712`)

Base `e4972c5` · depth: High (runtime code in the starter, a CI step, and a privacy claim: a site without analytics sends nothing the page does not need) · verdict: CLEAN (2026-10-16). Two rounds, a final full read and a wording pass; 12 findings (1 BUG in a shipped doc fixed, none open) · seen pair: base `e4972c5`, head `260f46d`; the commit after it adds only this trail · authority used: POST AUTHORITY, WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree, the branch and the PR); GATED-THIS-DIFF — atom A (Codex's chain: round 1 full, round 2 delta, wording pass delta)

## Rounds

| Round | Head | Scope | Seats | Time, tokens | Findings (BUG / RISK / NIT) |
|---|---|---|---|---|---|
| 1 | `fd2e258` | full (`e4972c5...fd2e258`, the BUGLOG row left out) | Codex (codex-cli 0.162.1, gpt-6.1-sol, config effort, read-only); Melious (glm-5.3, text only); fresh-eyes (Claude Opus, read-only) | Codex 211 s, 95,293 · Melious 206 s, 33,100 · fresh-eyes 109 s, 126,713 | 1 / 1 / 3 |
| 2 | `9def10e` | fixes since `fd2e258` | same | Codex 112 s, 70,686 · Melious 83 s, 13,160 · fresh-eyes 85 s, 111,756 | 0 / 1 / 3 |
| final full read (not a round) | `099f148` | full (`origin/main...HEAD`, the BUGLOG row included) | Claude Opus, a new reader; Kimi on ollama FAILED (quota) | 113 s, 129,003 | 0 / 0 / 3 |
| wording pass (not a round) | `260f46d` | prose and comments since `9def10e`, and the BUGLOG row | Codex (config effort) | 140 s, 68,809 | 0 / 0 / 0 |

## Findings

| Id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex; fresh-eyes (RISK) | 1 | `templates/PUBLISHING.md` said `CF_PAGES_BRANCH=` turns the visitor statistics on; false with analytics shipped off | fixed, externally_reverified (round 2) | "lets your visitor statistics run on the live site, once they are switched on (`USE_ANALYTICS = true` …; a new site has them off)" |
| F2 | RISK | Codex, Melious; fresh-eyes (NIT) | 1 | CI on-step's exact-string greps tied it to today's CSP word order | fixed, externally_reverified | greps removed; the gate checks the host as a whole token. Mutation: on, host not added → gate exit 1, "script-src does not list … as a token" (and connect-src) |
| F3 | NIT | fresh-eyes | 1 | website-team-setup "analytics fires only when the two agree" read as always on | fixed | "analytics, once switched on, fires …" |
| F4 | NIT | fresh-eyes | 1 | email.spec.ts comment "this build has none" | fixed | "runs only on a live build with analytics switched on …, so the builds this runs on have none" |
| F5 | NIT | Melious, fresh-eyes | 1 | CI comment "the suite below builds once and never as the live site" above the live email step | fixed | "The full suite (the last step) …" |
| U1 | — | fresh-eyes, Melious (UNVERIFIABLE) | 1 | does Playwright pass the step's `CF_PAGES_BRANCH` to the webServer build? | confirmed by observation | a local run with analytics ON and `CF_PAGES_BRANCH=production` saw `typeof window.plausible === "function"` (the stub, written only on the live build); the same state without it did not |
| U2 | — | Melious (UNVERIFIABLE) | 1 | the on-step's `npm run check` runs before the browser install | confirmed | `check` is `astro check`; green in the rehearsal |
| U3 | — | Melious (UNVERIFIABLE) | 1 | the gate's off mode fails with the host left in | confirmed | mutation: off, host back in connect-src → exit 1, "analytics is off … but connect-src still lists …" |
| G1 | RISK | Melious | 2 | without the greps, a silent perl miss could leave the step green | refuted | `check_analytics_gate.sh:603` runs `csp_host_problems` with analytics on and fails on a missing token; mutation in F2 |
| G2 | NIT | Melious | 2 | "builds once" is a claim about Playwright's config | refuted | `playwright.config.ts` webServer: one `npm run build && npm run preview`, `reuseExistingServer: false` |
| G3 | NIT | fresh-eyes | 2 | two lines wrapped long or short (team-setup, email.spec) | fixed | rewrapped |
| G4 | NIT | fresh-eyes (outside scope) | 2 | WEBSITE_ARCHITECTURE.md gave the gating as `CF_PAGES_BRANCH === 'production'` | fixed | "`USE_ANALYTICS && … === PROD_BRANCH`; ships off" |
| K1 | NIT | final full read | full | mail-form.spec.ts comment, config.ts's "changing scriptHost" sentence, PAGES-OR-WORKERS.md row still assumed analytics on | fixed | "with analytics switched on" / "With analytics on, changing scriptHost …" / "once switched on" |

## Checks run by the author

- Starter suite on a copy of the working tree, as template-tests.yml runs it, at `260f46d`: `npm ci`; the gate as shipped, "4 builds, off in every one"; the on-step (switch flipped, host added by the CI's perl line): `astro check` 0 errors, the gate "4 builds, on only when CF_PAGES_BRANCH is 'production'", both files put back; `tests/email.spec.ts` on the live build 9 passed; `npm run check` 0 errors; `npm run build`; `npx playwright test` 71 passed, 1 skipped (the positioning test waiting for a filled map).
- `make check`: green except `scripts/test_mktemp_guard.sh`'s self-test, which fails the same way on main on this Mac and passes in CI on Linux.

## Notes

- Data check: the diff carries no keys or customer data; this repo has gone to Codex and melious in earlier gates.
- Final full read: Kimi on ollama was out of quota; nothing else was sent to melious in its place. A new Claude Opus reader that had not seen the change ran instead (a host-family pass).
- Round 2 found no BUG and no RISK needing a fix: the rounds stopped (stop condition a2).
- The wording pass's segment (`9def10e..260f46d`) is Markdown and comment text only, plus the BUGLOG row.

Follow-ups: none.
