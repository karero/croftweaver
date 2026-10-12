# DIFF review — PR #270 — website-tagline: an optional skill for the short line under the logo
Base `d382cbe` · depth: Normal (a new instruction file an agent loads, and edits to three other skills' instruction files) · verdict: OPEN · authority used: POST AUTHORITY — atom A (this session opened #270); WORKTREE-WRITE — atom A (this session created the worktree); BRANCH-COMMIT — atom A (this session created the branch)

Normal gate: Codex and GLM 5.3 on melious.ai as the pair, and a fresh-eyes pass on a mid-tier host-family model in round 1.

Data check before round 1: the diff holds no key, token or password (searched for `api key`, `secret`, `token`, `passw`, `PRIVATE`; no hit). Destinations: Codex and melious.ai. The owner approved a plan in this session whose third step read "run the Normal review (Codex plus GLM 5.3 on melious)", with the words "go with steps 1 and 2 then push & merge".

Test record, taken at `169ad0a` before round 1: `make check`, exit status 0, 1,084 lines of output, ending
`all checks passed` / `LF checkout OK — every text file checks out LF even with core.autocrlf=true`.
The whole output is in the gate's PR comment. The three evals in `skills/website-tagline/evals/` are written and have not been run; nothing in the Makefile or in CI runs evals.

Before the gate, not a round: Codex and a second model each answered four design questions on head `1f26d1f` (offer or on request, how long a liked line stays, evals now or later, scope). Four defects they named were fixed in `ae82914`; their answers changed two decisions (`d6b78d4`). A claims sweep (`sweep_claims.sh --base origin/main`) then led to `169ad0a`, which turns seven general claims the skill could not back into instructions.

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `169ad0a` | full: `origin/main...169ad0a` without `docs/reviews/`, 8 files | running | | |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
