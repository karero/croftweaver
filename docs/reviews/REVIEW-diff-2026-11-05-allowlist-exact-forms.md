# DIFF review — branch security/allowlist-exact-forms — the starter's permission list narrowed to exact forms
Base `01a9fc5b` · depth: High (permissions) · authority used: WORKTREE-WRITE, BRANCH-COMMIT — this session made the branch and its worktree. Plan: PLAN-allowlist.md v4 in the maintainer's private hub, PLAN gate closed after 7 rounds.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | 56a9a87a | `git diff origin/main...56a9a87a`, evidence of the routine run, mutation check and repo checks | Codex (gpt-6.1-sol, `CODEX_EFFORT=config`) + melious glm-5.3; Opus fresh-eyes | codex 149 s, 43,394; melious 355 s, 41,012; fresh-eyes 321 s, 147,345 | 4 / 4 / 9 after dedup |

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| R1-1 | BUG | codex, fresh | 1 | website-permissions §1's migration never adds `Bash(node --version)` | fixed | §1 names it |
| R1-2 | BUG | codex, fresh | 1 | "about two more questions" leaves out making the branch | fixed | now three: the branch, the commit, the first push |
| R1-3 | BUG | codex, melious, fresh | 1 | "the list holds only the exact git commands" ignores the six git `:*` rules | fixed | the summary says the branch and publish commands are exact |
| R1-4 | BUG | melious, fresh | 1 | "a new branch asks" is false for `git checkout -b production` | fixed | "a new working branch"; "Now asks" says `production` is the exception |
| R1-5 | RISK | codex, melious | 1 | the deny and ask paths of the engine are not tested with this list | out of scope by owner decision | the owner, 2026-11-05: "Exact forms, no attack runs"; the doc says the refusals were read, not tested |
| R1-6 | RISK | melious | 1 | a new deny rule may refuse a routine command | refuted | READ D4: no git command in skills or docs uses `--output` or `--pathspec` |
| R1-7 | RISK | fresh | 1 | the §3 example `git push -u origin content` matches no real branch | fixed | example is `Bash(git remote -v)`; a sentence says a first push cannot be approved ahead |
| R1-8 | RISK | fresh | 1 | SETUP.md sends owners to `/fewer-permission-prompts` with no caveat | fixed | keep exact commands only, never re-add a removed rule |
| N1 | NIT | melious | 1 | `:*` wording misses the space | fixed | "on its own or followed by a space and anything" |
| N2 | NIT | melious, fresh | 1 | SETUP.md and website-permissions §2 say "a new branch" unqualified | fixed | qualified; BUGLOG row too |
| N3 | NIT | melious | 1 | "turned on the pre-push hook" is more than the check shows | fixed | "pointed git's hooks at `scripts/hooks`, where the pre-push hook lives" (READ D5) |
| N4 | NIT | fresh | 1 | the by-hand publish command asked before too | fixed | item removed from "Now asks" |
| N5 | NIT | fresh | 1 | "the two" deny rules: there are three | fixed | |
| N6 | NIT | fresh | 1 | SETUP.md "the exact pull and push commands these docs use" includes ones that ask | fixed | "for `main` and `production`" |
| N7 | NIT | fresh | 1 | the "runs the site's own code" list is short | fixed | widened |
| N8 | NIT | fresh | 1 | "What was not checked" ignores the 2026-11-05 run | fixed | |
| N9 | NIT | codex, melious | 1 | evidence READ 9 says 57 allow | fixed in evidence | a note gives 54, the file in the diff |
