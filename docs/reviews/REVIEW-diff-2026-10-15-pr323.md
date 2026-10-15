# DIFF review — karero/croftweaver#323 — Dependabot: astro 7.3.5→7.3.8, @playwright/test 1.63.0→1.64.0, @types/node 24.19.1→24.19.2 in the starter

Base `8cbb637` · depth: Normal (a dependency change) · verdict: CLEAN · authority used: WORKTREE-WRITE and BRANCH-COMMIT on the local branch `review/pr323` — atom A (this session created that worktree and branch); GATED-THIS-DIFF — atom A (captured inputs below)

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `a9894e7` | full, `8cbb637...a9894e7` without docs/reviews | Codex CLI 0.162.1 (gpt-6.1-sol, config effort, read-only); GLM 5.3 on melious (text only); fresh-eyes Sonnet sub-agent | codex 180 s, 64,159; melious 128 s, 24,379; fresh-eyes 99 s, 110,578 | 1 / 4 / 4 |
| 2 (verify) | `1e4d8fd` | delta `a9894e7..1e4d8fd` | Codex CLI 0.162.1 (medium); GLM 5.3 on melious | codex 75 s, 30,698; melious 143 s, 13,322 | 0 / 2 / 1 (+1 outside scope) |
| wording pass | `e1e48d6` | delta `1e4d8fd..e1e48d6` | Codex CLI 0.162.1 | codex 112 s, 43,585 | 0 / 1 / 0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | fresh-eyes (as RISK), codex (as NIT) | 1 | templates/SETUP.md and templates/astro/README.md told new owners to run `npm approve-scripts esbuild`; astro 7.3.8 no longer installs esbuild, so it fails | fixed `1e4d8fd`, locally_verified, externally_reverified (round 2, codex clean) | `npm ci` of the updated lockfile, npm 11.20.0: `npm approve-scripts esbuild` → `ENOMATCH No installed packages match: esbuild`; lockfile `hasInstallScript`: before esbuild + fsevents, after fsevents@2.3.3 only; install prints no install-scripts warning |
| F2 | NIT | fresh-eyes, codex | 1 | allowScripts still named `esbuild@0.28.2` | fixed `1e4d8fd` | entry removed; `npm ci` clean with and without it |
| F3 | NIT | fresh-eyes | 1 | docs/UPGRADING.md named the floor `^7.3.5` | fixed `1e4d8fd` | now `^7.3.8` |
| F4 | NIT | fresh-eyes | 1 | website-motion said the lockfile resolves Playwright 1.63.0 | fixed `1e4d8fd` | now 1.64.0 |
| F5 | RISK | melious | 1 | no rolldown entry for astro 7.3.8 | refuted | 17 rolldown entries; `npm ls rolldown` → rolldown@1.2.11 under astro and vite |
| F6 | RISK | melious | 1 | astro's raised floors lack entry changes | refuted | `npm ls --all` exit 0 after `npm ci`; vite 8.3.1, devalue 5.9.4, zod 4.6.5, magic-string 1.4.2, picomatch 4.0.7 |
| F7 | RISK | melious | 1 | removing esbuild breaks `npm ci` if anything needs it | refuted | `npm ci` exit 0, `npm ls --all` exit 0; CI's build and Playwright jobs green on `a9894e7` |
| F8 | RISK | melious | 1 | @axe-core/playwright 4.13.0 may not accept Playwright 1.64 | refuted | its peerDependencies: `{"playwright-core":">= 1.0.0"}` |
| F9 | NIT | fresh-eyes | 1 | test_install.py and an old trail mention 1.63 | refuted (no change) | dated records of past runs |
| F10 | RISK | melious | 2 | "already approves the one package … nothing to approve" unsupported | refuted | the lockfile's only `hasInstallScript` package is fsevents@2.3.3, which allowScripts names; `npm ci` on npm 11.20.0 printed no warning |
| F11 | RISK | melious | 2 | `npm approve-scripts` may not exist at npm 11.16 | refuted | sentence predates this PR; npm v11.17.0's release notes (2026-06-11) fix approve-scripts, so it existed before; ran on 11.20.0 |
| F12 | NIT | melious | 2 | the version clause did not read as a sentence about Astro and sharp | fixed `e1e48d6`, locally_verified; read by the wording pass | — |

Follow-ups: npm's advisory-only behaviour and version-pinned approvals, as both guides state them since before this PR, are not traced to npm's code or docs here (wording pass, codex, marked UNVERIFIABLE). Playwright 1.64.1 exists; this PR ships 1.64.0.
Notes: round 2 found no BUG and no in-scope RISK needing a fix, so the rounds stopped (step 6, a2). The base has not changed these files: `git diff 8cbb637 origin/main` on all six paths is empty at `da86dfb`. Playwright 1.64's screen change: no starter test or CSS uses screen-size media queries (fresh-eyes, by search).
