# DIFF review — karero/croftweaver#271 — `new-website` asks once for a credit after the site is live; the README asks for the same

Base `origin/main` (`d382cbe`) · depth: **Normal** (`skills/new-website/SKILL.md` is an instruction file an assistant follows; the README sentences alone would be Light, and a mixed diff takes its riskiest file's depth) · verdict: **OPEN** · authority used: WORKTREE-WRITE, BRANCH-COMMIT and POST AUTHORITY — atom A, this session created the worktree, the branch and the PR

| Round | Head | Artifact | Reviewers: CLI version, model, effort, sandbox | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | pending | full, `origin/main...HEAD` without `docs/reviews/` | pending | pending | pending |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|

Waivers: none. Deferrals: none. Follow-ups: none yet.

## Test record, taken before round 1

- Command: `make check` in the worktree at head `7eeb4f5404d5a58c9db12759bb6fd8c555f440b7`, started 2026-10-12T18:56:47Z.
- Result: exit status 0; 1,083 lines of output; no line starting `not ok` or `FAIL`.
- Skipped, 7: the minimum-Perl check (`Perl::MinimumVersion` is not installed on this machine) and six shell tests that need `/proc`. CI runs both.
- An earlier complete run on `d4376c6` (the first commit, before the README sentences and the wording fix) also ended with exit status 0 and the same 7 skips.
- The whole output of the run on `7eeb4f5` is in the PR's review comment, collapsed.
- No test covers the wording of section 4b: it is prose an assistant follows, and the suite has no check of what an assistant asks.

## Files the change takes

`skills/new-website/SKILL.md` (52 lines added) and `README.md` (5 lines added), plus this trail. The README commit `fa4c94a` is a cherry-pick of `f8f035d`, written on 2026-10-10 by an earlier session on the local branch `docs/readme-credit-line` and never pushed.

Notes:
- Data check: the diff and the brief hold no credentials and no private names. Destinations: Codex, and GLM 5.3 on Melious, the owner's standing pair for this repository; the repository is public.
- The brief quotes 29 lines of `src/pages/partner-assets.astro` from the site's repository: the constants that produce the code shown on the public page croftweaver.com/partner-assets.
- Outside this repository: the badge code on that page links to the page itself today; the owner decided on 2026-10-12 that it will link to the home page. That change is not made yet.
