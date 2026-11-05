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

Round 2 (head 85c2531c; artifact `git diff 56a9a87a..85c2531c`, `--verify` round 1, the same evidence plus READ D4-D5): Codex 107 s, 43,858; melious glm-5.3 244 s, 28,008; fresh-eyes (Opus) 339 s, 129,459. 2 BUG, 1 RISK, 9 NIT after dedup. Every round 1 fix was confirmed except the parts below.

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| R2-1 | BUG | codex | 2 | SETUP.md's "push commands for `main` and `production`" takes in the emergency publish, which asks | fixed | "the four exact push commands"; the emergency publish is named as asking |
| R2-2 | BUG | melious | 2 | "Only `production` is created and pushed without asking" ignores `git push -u origin main` | fixed | creation and first push are now two clauses; website-permissions §2 says the same |
| R2-3 | RISK | melious | 2 | "`:*` matches the command on its own" contradicts the docs | refuted | READ D6: the docs say a trailing space-star also matches the bare command |
| N10 | NIT | melious | 2 | the pull and fetch forms are not main/production-specific | fixed | SETUP.md splits fetch/pull from push |
| N11 | NIT | melious | 2 | `git checkout` runs no site script | fixed | "change which version of those files is on disk" |
| N12 | NIT | fresh | 2 | the paragraph after the "Now asks" list renders inside its last bullet | fixed | blank line restored |
| N13 | NIT | fresh | 2 | summary: "`node`" too broad, and "so" links the image tools to git | fixed | "`node` scripts"; "and" |
| N14 | NIT | fresh | 2 | the `--output` rule covers every git command, the docs say three | fixed | "any git command given `--output`" |
| N15 | NIT | fresh | 2 | §1: "that merge also removes" — the hooks merge removes nothing | fixed | "When merging, also delete" |
| N16 | NIT | fresh | 2 | "The test ran headless" is ambiguous now that two runs are named | fixed | "The push test" |

Round 3 (head 37776ab0; artifact `git diff 85c2531c..37776ab0`, `--verify` rounds 1-2, the same evidence): Codex 124 s, 63,948, no findings; melious glm-5.3 283 s, 32,891, 3 NIT; fresh-eyes (Opus) 180 s, 104,908, 4 NIT. 0 BUG, 0 RISK, 6 NIT after dedup.

| id | Sev | Source | Round | Finding — one line | Status | Evidence |
|---|---|---|---|---|---|---|
| N17 | NIT | fresh | 3 | SETUP.md ties all four push forms to `main` and `production`, but a plain `git push` follows the branch's upstream | fixed, closing edit | names the plain push and where it goes |
| N18 | NIT | fresh | 3 | website-permissions §2's "without asking" hangs off two clauses | fixed, closing edit | the wording WHAT-THE-SKILLS-RUN uses |
| N19 | NIT | fresh, melious | 3 | `git switch` also changes the files on disk, and checkout or switch can run a site's hooks | fixed, closing edit | "`git checkout`, `git switch` and `git pull` … can run git hooks the site carries" |
| N20 | NIT | fresh | 3 | the `--output` deny rule matches any later word starting `--output`, a commit message included | fixed, closing edit | "with a word starting `--output`"; it refuses, never runs |
| N21 | NIT | melious | 3 | SETUP.md's lists leave out `node` | fixed, closing edit | "`node` commands other than `node --version`" |
| N22 | NIT | melious | 3 | the `:*` sentence omits the docs' "only wildcard" caveat | refuted | every allow rule in the file has at most one `*`, at its end |

Verdict: CLEAN. Stop condition: High; round 3 found no BUG and no RISK. Its NIT fixes are closing edits, checked locally (`make check`, the plugin tests), not reviewed again.
Totals: 3 rounds; 17, 12 and 6 findings after dedup (6 BUG in all, none open). Seat runs logged 253,111 tokens; fresh-eyes 381,712 more.
Not run: no test of what the list refuses, by the owner's decision; the docs say so.
Follow-ups: the docs/BUGLOG.md row for the release notes.
