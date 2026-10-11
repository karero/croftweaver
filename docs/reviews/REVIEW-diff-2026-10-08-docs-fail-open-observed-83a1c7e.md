# DIFF review — docs/fail-open-observed — the Fail open path and default, as seen live

Base `origin/main` (`f812647`) · depth: **Light** (one paragraph of a reference doc, recording an owner's dashboard observation; no code) · verdict: **CLEAN** — the one RISK refuted with the owner's first-hand report. Authority used: WORKTREE-WRITE and BRANCH-COMMIT (this session created the worktree and branch after the owner passed on the live test's result); GATED

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `83a1c7e` | `origin/main...83a1c7e` | Codex `gpt-6.1-sol` (config effort), `--seat codex` | codex 191 s/65,307 | 0 / 1 / 0 |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | RISK | codex | 1 | "path checked in the dashboard 2026-10-07" has no captured UI observation | refuted | the owner's report of the live form test, in chat: "The path in CLOUDFLARE_FIRST_DEPLOY.md is correct: Workers & Pages → <project> → Settings → Runtime → Fail open / closed." and "A new project starts with Fail open. Seen on a project created that day with `wrangler pages project create`; a project made in the dashboard or connected to GitHub was not checked." The text claims no more than that, and still says to look rather than assume |

Waivers: none. Deferrals: none. Follow-ups: whether the setting is one per project or one each for Production and Preview was not reported by the live test (the Pages API stores `fail_open` under both).

Notes: a Light gate, with a cross-model seat rather than the host's own review. Codex otherwise found the wording scoped to what was observed.
