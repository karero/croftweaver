# DIFF review — branch docs/site-folder-follow-ups — define `<site>`, a home for the toolkit, a WSL2 buglog row
Base `0af174e`, merged with main `0006a6d` · depth: Normal (SKILL.md is an instruction file an assistant follows) · verdict: CLEAN (no open BUG or RISK) · authority used: WORKTREE-WRITE — atom A (this session created the worktree `website-builder-site-rule`); BRANCH-COMMIT — atom A (this session created the branch and made every commit). POST AUTHORITY: atom A once this session opens the PR.

| Round | Head | Artifact | Reviewers: model, effort, sandbox | seconds / tokens per seat | BUG/RISK/NIT (distinct, new) |
|---|---|---|---|---|---|
| 1 | 24c31f1 | full | fresh-eyes (host-family sub-agent, read-only); Codex (default effort, read-only); GLM 5.3 on melious (text only) | fresh-eyes 205 / 135,052; Codex 240 / 78,987; GLM 75 / 13,939 | 3 / 3 / 4 |
| 2 | 8785610 | delta since 24c31f1 | Codex (medium); GLM 5.3 | Codex 119 / 54,971; GLM 63 / 15,714 | 0 / 1 / 1 |
| 3 | 4ba3379 | delta since 8785610 | Codex (medium); GLM 5.3 | Codex 134 / 43,671; GLM 75 / 10,354 | 0 / 0 / 0 |
| wording pass | e1c80c4 | the BUGLOG row (prose only) | Codex alone | 92 / 41,826 | 1 / 0 / 0 |
| confirmation | 1c95118 | delta since e1c80c4 | Codex alone | 73 / 32,609 | 0 / 1 / 0 |
| narrow look 1 | 56b37c6 | delta since 1c95118 | Codex alone | 99 / 44,847 | 0 / 1 / 0 |
| narrow look 2 | b58afd1 | delta since 56b37c6 | Codex alone | 72 / 29,773 | 0 / 0 / 0 |
| merge link | 9e6a4e1 | `merge_link.sh 0af174e b58afd1 3f63db6`: docs/BUGLOG.md only | Codex alone | 202 / 77,646 | 0 / 0 / 0 |

Rounds 1-3 reported `reviewers: codex OK, melious OK`. 15 distinct findings from 20 raw seat findings.

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| G1 | BUG | Codex, fresh-eyes | 1 | README `unzip website-builder.zip && cd website-builder` does not match the zip (no top-level folder) | fixed; externally_reverified r2 | 8785610; `-d website-builder`; `scripts/package.sh` zips root entries; tried on the built zip |
| G2 | BUG | Codex | 1 | the brief says a BUGLOG row for the WSL2 path exists | refuted | the brief said the row comes after the last round, as the review skill asks; added in e1c80c4 |
| G3 | BUG | GLM | 1 | `<site>` pinned to the opening folder while the prompt allows another websites folder | fixed; externally_reverified r2 | 8785610; "inside the owner's websites folder, which is the folder this session was opened in" |
| G4 | RISK | fresh-eyes, GLM | 1 | a session opened in an existing site or in the toolkit folder nests the new site | fixed; see G11 | 8785610 |
| G5 | RISK | GLM, fresh-eyes | 1 | `mkdir <site>` resolves against the shell's folder; "full path" had no source | fixed; externally_reverified r2 | 8785610; "Start step 0 from the websites folder", `pwd` |
| G6 | RISK | fresh-eyes | 1 | `<site>` is a full path in `make whats-new PROJECT=<site>` and `--stamp-tests <site>/tests` | fixed; externally_reverified r2 | 8785610; `<site-dir>` |
| G7 | NIT | fresh-eyes, GLM | 1 | the prompt said "outside my websites folder" before introducing it | fixed; externally_reverified r2 | 8785610 |
| G8 | NIT | GLM | 1 | "don't move or delete them later" against a toolkit already in Downloads | fixed; externally_reverified r2 | 8785610 |
| G9 | NIT | fresh-eyes | 1 | nothing keeps the two starter-prompt copies identical | follow-up | compared by script every round |
| G10 | NIT | fresh-eyes | 1 | docs/CODEX.md describes the symlink install without "keep the folder" | fixed; externally_reverified r2 | 8785610 |
| G11 | RISK | Codex, GLM | 2 | the guard fires on two file markers only | fixed; externally_reverified r3 | 4ba3379; asks unconditionally unless confirmed, markers as backstop |
| G12 | NIT | GLM | 2 | "reopen you in my websites folder so the skills load" gives the wrong reason | fixed; externally_reverified r3 | 4ba3379 |
| G13 | BUG | Codex | wording pass | the BUGLOG row says the guide "recommends WSL2, so" the folder is on the Linux side; README says native Windows works too | fixed; externally_reverified | 1c95118; contradiction gone per the confirmation |
| G14 | RISK | Codex | confirmation | "a site built in WSL2 has its folder on the Linux side" is not enforced by the scaffold | fixed; externally_reverified | 56b37c6; "for a site kept in WSL2's Linux filesystem" |
| G15 | RISK | Codex | narrow look 1 | "reachable from Windows only under a `\\wsl$` path" asserts unsupported exclusivity | fixed; externally_reverified | b58afd1; claim dropped; narrow look 2 found nothing |

Waivers and deferrals: none.
Follow-ups: nothing keeps the two starter-prompt copies identical (G9); that Git Bash's `ln -s` makes real links, and that assistants follow the new folder question, are untested; the beginner cold test was left out by the owner ("1, 2 and 4 are enough"); the WSL2 folder question is open as a BUGLOG row.
Notes: depth Normal because SKILL.md is an instruction file. Rounds 2 and 3 were owed by fixes to instructions a reader and an assistant follow. The BUGLOG row was written after the last round, as the skill asks; its wording took the pass, a confirmation and two narrow looks, each by Codex alone. Codex's chain is unbroken to the merge link (9e6a4e1); main was merged once (3f63db6), and only docs/BUGLOG.md conflicted: both sides added rows at the end, and both were kept, the other session's four rows first; GLM's ends at round 3 and the fresh-eyes reader's at round 1, by design at this depth. Main was merged a second time (0006a6d; PR #246 corrected one `docs/BUGLOG.md` row just above this change's row): the lines this change adds and removes are identical before and after (compared by hash), only one context line differs, so no new look was run. The trail is the only change after the merge (docs/reviews/ is outside the reviewed artifact). No final full read: not required at this depth for a change this size. Not tested on a clean machine, in Codex, or in the desktop apps.
