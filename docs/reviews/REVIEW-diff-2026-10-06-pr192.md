# DIFF review — karero/website-builder#192 — SETUP: turn on Dependabot alerts and security updates for a new site

Base `origin/main` · depth: **Normal** (owner-facing setup commands that change repo settings; no code) · verdict: **CLEAN — no BUG or RISK open** after round 5's NIT was fixed; rounds 1, 2 and 4 were one-model rounds.

| Round | Head | Artifact | Reviewers | BUG/RISK/NIT |
|---|---|---|---|---|
| 1 | `f73c22e` | the SETUP.md commit | Codex `gpt-6.1-sol`, read-only; **ollama `kimi-k2.7-code:cloud` FAILED** (429) — degraded | 1 / 2 / 0 |
| 2 | `3004683` | the SETUP.md commit, with round 1's dispositions (`--seat codex`) | Codex | 0 / 2 / 0 |
| 3 | `27eb3ec` | approach brief (options A–E, the problem, the diff), `--plan` | Codex; ollama `kimi-k3:cloud` | 3 / 5 / 2 |
| 4 | `acbef1d` | `origin/main...acbef1d`, with round 3's dispositions | Codex; **ollama `kimi-k3:cloud` FAILED** (429, session usage limit) — degraded | 0 / 1 / 0 |
| 5 | `c2b2880` | final full read: `origin/main...HEAD`, `docs/reviews/` excluded, with this trail (`--seat melious`) | melious `glm-5.3`, HTTP API | 0 / 0 / 1 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| R1-1 | RISK | codex | 1 | the two PUTs' effect is unverified | fixed `3004683`, `9a5ae92` | read-back added; both lines run on an on repo (`on`) and an off private repo (404, `off`) |
| R1-2 | RISK | codex | 1 | Dependabot PRs may not run the site's CI | refuted | #173 ran this repo's `pull_request` CI (run 37425353110); the site's `ci.yml` triggers on `pull_request` and uses no secrets |
| R1-3 | BUG | codex | 1 | commit message credited Dependabot with the `http-cache-semantics` fix | fixed (amended before push) | `4604102` is a manual bump after alert #11 |
| R2-1 | RISK | codex | 2 | the read-back proved only one of the two settings | fixed `27eb3ec` | both settings read back |
| R2-2 | RISK | codex | 2 | R1-2's refutation lacked traceable evidence | refuted | run link above, now in the PR description |
| R3-1 | RISK | codex | 3 | the step sat in SETUP.md, walked only "if needed" | fixed `9a5ae92` | required launch-checklist item in `new-website/SKILL.md` |
| R3-2 | RISK/BUG | codex, kimi | 3 | existing sites get only a release note, with no completion signal | deferred by the owner | `docs/BUGLOG.md` row: a read-only `whats-new` check, after #153 (same file) |
| R3-3 | RISK | codex | 3 | security updates may not fix indirect packages | refuted, text qualified `3d9a907` | GitHub: for npm, a security update bumps the parent when needed; #173 fixed indirect `source-map-js` (no `allow:` in the config, so not a version update); SETUP now promises a PR only "where a fixed version exists" |
| R3-4 | BUG | codex | 3 | brief: "Dependabot fixed two" | fixed | PR description wording |
| R3-5 | BUG | codex | 3 | brief: team-setup "only" runs when a second person joins | fixed | PR description: "mainly" |
| R3-6 | RISK | kimi | 3 | add `npm audit` to the site's CI | rejected by the owner | a blocking audit would block an owner's text edits over packages they cannot fix; needs the registry |
| R3-7 | RISK | kimi | 3 | the lines never name the repo they change | fixed `9a5ae92` | first line prints it; outside a repo it exits 1 and names none |
| R3-8 | NIT | kimi | 3 | read-back ignores `paused` | fixed `9a5ae92` | prints `paused` / `on` / `off` |
| R3-9 | NIT | kimi | 3 | "free on every plan" goes stale | refuted | GitHub security features: "Available for all GitHub plans" |
| R4-1 | RISK | codex | 4 | R3-3 still lacks a parent-bump example | fixed `3d9a907` | the promise is qualified rather than proven |
| R5-1 | NIT | glm-5.3 | 5 | the alerts read-back prints only gh's raw 404 when off, never `off` | fixed | `\|\| echo "alerts: off"`; run on an on repo (`on`) and an off private repo (`off`) |

Waivers: none. Deferrals: R3-2 (owner). Follow-ups: R3-2; the flaky `merge_link` case (BUGLOG); the live run on a real site repo, done 2026-10-08 with the owner's OK: the lines named the repo and turned both settings on, the first alerts appeared within seconds, and Dependabot opened lockfile-only fix pull requests within two minutes, which the site's CI ran. An advisory with no patched version got an alert but no pull request, as SETUP.md says.

Notes: rounds 1 and 4 are degraded (the second seat failed); round 2 was Codex alone by choice; round 5 is the final full read by a second model, GLM 5.3 (owner's consent to send this repo to melious, this session).
