# DIFF review — branch docs/starter-prompt-copies-note — a "change both" note above each starter-prompt copy
Base `dbd6134` · depth: Light — Codex alone, medium effort, one round (every changed file is README text for people: two hidden comments, no command, step or prompt word edited) · verdict: CLEAN (no BUG, RISK or NIT) · authority used: WORKTREE-WRITE — atom A (this session created the worktree `website-builder-prompt-copies-note`); BRANCH-COMMIT — atom A (this session created the branch `docs/starter-prompt-copies-note`); POST AUTHORITY — not used yet, no PR exists

| Round | Head | Artifact | Reviewers: CLI, model, effort, sandbox | seconds / tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | c8ede65 | full (`git diff dbd6134...HEAD`, 26 lines, trail excluded) | Codex CLI 0.162.0, gpt-6.1-sol, medium, read-only | 39 / 21,591 | 0 / 0 / 0 |

No findings, so there are no dispositions, waivers or deferrals.

Before the round:
- Data check: a grep of the diff for tokens, secrets, passwords and private keys found nothing. The owner's OK to send it to Codex: "Run a review".
- Claims sweep (`sweep_claims.sh --base origin/main`): 0 sentences to check. The notes claim no automated enforcement.
- `make check`: exit 0, "all checks passed".
- Both prompt copies compared byte for byte after the edit: identical, 13 lines each.

What Codex reported clean: each note names the other copy correctly (`README.md:61`, `docs/GETTING-STARTED.md:80`); the two 13-line prompt blocks match; the commit changes only the comments and the blank lines beside them; the comments are well formed and sit outside the prompt blocks; `scripts/package.sh` ships both files; `check_prompt_sync.sh` covers the independent-review prompts, not these.

Notes:
- Light gate: one seat by the owner's standing choice for prose no assistant loads as instructions and no person runs. The script warned that one seat is fewer than the standard pair; that is the choice, not a degraded round.
- Main moved while the branch waited (7 commits, none in `README.md` or `docs/GETTING-STARTED.md`). It was merged in as `1ea3065` before the PR opened. The diff against the new base `d204c75`, trail excluded, is byte-identical to round 1's, so no new round was owed and the stamp covers the merged head (closeout, clerk item 2: only the SHA moved).
- No check script was added. The two copies never differed across the last 60 commits that touched either file; the first time they differ, add one.
