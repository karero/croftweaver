# Review trail: ship-from-worktree plan, row 3 after #376 merged (branch docs/ship-plan-row3-merged)

Base `f680e440` · depth: Normal (status text in a plan: one row and the plan's opening; a plan is never Light) · verdict: in progress · authority used: WORKTREE-WRITE and BRANCH-COMMIT, each by atom A (the app made this worktree for this session, `get_session("self")`: worktreePath; this session made the branch in it). No PR yet: POST AUTHORITY not held.

Destinations: Codex and melious.ai, as for #376 (`REVIEW-diff-2026-10-22-claude-ship-from-worktree-3b24ce-0aaeb44.md`); this public repository's content has gone to both before. Artifact: `git diff f680e440...HEAD -- docs/reviews/SKILL-PLAN-ship-from-worktree.md` (named, since the usual `docs/reviews/` exclusion would drop it), with a context note quoting `gh pr view 376` and `git rev-parse 001c68b7^2`. `make check` exit 0 at `b4fe913c` (the Perl minimum-version check skipped here, Perl::MinimumVersion not installed; CI runs it).

**Degraded round 1.** Melious answered "Insufficient balance for request. Required: 76, Available: 0"; its ollama stand-in had reached its weekly limit (429). Round 1 counted one cross-model seat, Codex, plus the fresh-eyes pass.

## Rounds

| Round | Head | Scope | Seats | Time, tokens | Findings (BUG / RISK / NIT) |
|---|---|---|---|---|---|
| 1 | `b4fe913c` | full: the plan's change since `f680e440` (4.7 KB with the note) | Codex CLI 0.164.0, gpt-6.1-sol, config effort, read-only; fresh-eyes (Claude Sonnet 5.5, read-only); Melious and ollama FAILED (see above) | Codex 231 s, 51,150 · fresh-eyes 192 s, 146,945 | 0 / 0 / 1. Codex: no findings |

UNVERIFIABLE entries: 7 asked (Codex 4, fresh-eyes 3), none confirmed as a finding. The two that row 3 and the opening rest on were looked at:
- the branch's deletion on GitHub: the PR's events list `head_ref_deleted` at 2026-10-22T16:22:21Z, three seconds after `merged`;
- the site copies not built: every site checkout on the maintainer's Mac carries `ship.sh` at template-version 0.20 or 0.21, none at 0.22.

## Findings

| Id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| R1-01 | NIT | fresh-eyes | 1 | Row 3's "deleted after the merge" held for GitHub's branch only; this clone still had a local branch of that name at `283fa0a8` | fixed, locally_verified | row 3 says "deleted on GitHub after the merge"; the local branch is deleted too (`git branch -d`, it was at `283fa0a8`, merged) |
