# DIFF review — docs/buglog-whats-new-followups — two BUGLOG rows (release note for #221, root-template gap in the coverage guard)
Base `4fb78d6` · depth: Light (two docs rows nobody executes), with one cross-model seat because the rows' claims are about code and a site owner will act on them · verdict: CLEAN · authority used: WORKTREE-WRITE and BRANCH-COMMIT — atom A (this session created the worktree and the branch); POST AUTHORITY — atom A (this session opens the PR, on the owner's "ok lets add the buglog rows"); GATED-THIS-DIFF — atom A (round 1 saw `4fb78d6...99a1e03` in full, round 2 the delta `99a1e03..7ea85ac`, round 3 the delta `7ea85ac..fc6893c`; codex counted in all three)

Consent to send this repo to Codex, this session: "Yes, both (Recommended)". This review used Codex only.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `99a1e03` | full, `4fb78d6...99a1e03` | codex-cli 0.161.0, gpt-6.1-sol, config effort, `--seat codex`, read-only | codex 184 s, 68,925 | 2 / 0 / 0 |
| 2 | `7ea85ac` | delta since `99a1e03` (`--verify`) | codex-cli 0.161.0, gpt-6.1-sol, effort medium, `--seat codex`, read-only | codex 81 s, 47,885 | 1 / 0 / 0 |
| 3 | `fc6893c` | delta since `7ea85ac` (confirmation of one fix) | codex-cli 0.161.0, gpt-6.1-sol, effort medium, `--seat codex`, read-only | codex 43 s, 31,435 | 0 / 0 / 0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| B1 | BUG | codex | 1 | Row 1 said "the fix is to copy it in" for a MISSING `verify.mjs`; a hook from before the verify gate never calls it, and `npm run verify` needs a `package.json` entry | fixed `7ea85ac`, locally_verified, externally_reverified r2 | the hook one commit before `878cbd4` mentions `verify.mjs` 0 times; the current hook calls it |
| B2 | BUG | codex | 1 | Row 1 said `git-stand.mjs` comes "only with `website-team-setup`"; the scaffold also copies it for Claude Code sites | fixed `7ea85ac`, locally_verified, externally_reverified r2 | `skills/new-website/SKILL.md:306-309`, under "Claude Code only" |
| B3 | BUG | codex | 2 | The B1 fix said "an older hook never does" (call `verify.mjs`); the hook at `878cbd4` already does | fixed `fc6893c`, locally_verified, externally_reverified r3 | the hook at `878cbd4` mentions `verify.mjs` 4 times, its parent 0; `878cbd4` also created `verify.mjs` |

Waivers and deferrals: none.
Follow-ups: none.
Notes: before round 1 I tried each row's claims: the coverage guard still passes with `AGENTS.md` dropped from the list, with a new root template and with a third `claude/` file, and fails for a new `astro/` file; the baseline limit shows MISSING, then nothing after `--stamp-tests`, then MISSING again when upstream changes the file. The claims sweep also made me narrow "nothing checks that list" to "nothing checks that the list is complete" (the guard checks that each entry exists and has a report arm).
Light gate, one cross-model seat by choice: the script warned that fewer than two reviewers counted. B3 came from the wording of B1's fix, so round 3 was the wording pass's confirmation, not a new round. Raw reviewer output is in the PR comment.
