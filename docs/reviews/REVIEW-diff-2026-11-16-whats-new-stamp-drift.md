# DIFF review — branch fix/whats-new-stamp-drift — whats-new: a refresh keeps a pinned skill's drift, and --stamp-tests keeps the site's record

Base `07211892` · depth: Normal (the suite's update report and its stamps; no user data, auth or
deploy path) · verdict: CLEAN after round 3, two wording passes and two confirmations of the record prose · authority used: WORKTREE-WRITE and BRANCH-COMMIT.
This session (the small BUGLOG sweep) created the worktree and the branch.

Artifact: round 1 `git diff 07211892...78859f51 -- . ':(exclude)docs/reviews/'`; round 2 `git diff
78859f51..4240b5cd` (same exclusion), with `--base 78859f51`; round 3 `git diff 4240b5cd..1e43be89`,
with `--base 4240b5cd`. Wording passes, Codex alone: the round 3 fixes `git diff 1e43be89 9a4e7fdc` with `--base 1e43be89`, and the record prose `git diff 2125aa79 6054595c -- docs/BUGLOG.md` with `--base 2125aa79` (2125aa79 merges origin/main, so one diff over both would mix two bases; the script refused it, at no cost). Confirmations: `git diff 6054595c 4dd93a2a` and `git diff 4dd93a2a a4704eef`, each with its first commit as `--base`. Evidence: each round runs the two
test scripts on its head and on the head before it (origin/main's `whats-new.sh` for round 1), with
that round's tests copied in.
Gate id 20261116T142727Z-57519.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `78859f51` | full, merge base with origin's HEAD | Codex (gpt-6.1-sol, read-only); melious (glm-5.3, HTTP API, text only); fresh-eyes (Claude Sonnet sub-agent, read-only) | codex 215 s, 49,665; melious 611 s, 39,077; fresh-eyes 188 s, 166,361 | 3 / 3 / 7 after dedup |
| 2 | `4240b5cd` | delta from `78859f51`, verify of F1-F13 | Codex (medium); melious | codex 151 s, 51,267; melious 358 s, 30,586 | 3 / 1 / 2 after dedup |
| 3 | `1e43be89` | delta from `4240b5cd`, verify of F14-F19 | Codex (medium); melious | codex 206 s, 57,600; melious 482 s, 36,186 | 1 / 1 / 2 after dedup |
| wording | `9a4e7fdc` | the round 3 fixes (two comments) | Codex (medium), `--wording-pass` | codex 41 s, 27,548 | 0 / 0 / 0 |
| wording | `6054595c` | the BUGLOG rows | Codex (medium), `--wording-pass` | codex 63 s, 44,403 | 3 / 0 / 0 |
| confirm | `4dd93a2a` | delta from `6054595c` | Codex (medium), `--wording-pass` | codex 69 s, 47,511 | 2 / 0 / 0 |
| confirm | `a4704eef` | delta from `4dd93a2a` | Codex (medium), `--wording-pass` | codex 60 s, 43,816 | 1 / 0 / 0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex, fresh-eyes | 1 | A site with no TESTS-VERSION got no `left_out:` lines: the stamp ignored the SUITE-VERSION fallback the report uses. | fixed in `4240b5cd` | One helper, `oldest_stamp_base`, now serves the report and the stamp. Test L10 fails on 78859f51. |
| F2 | BUG | Codex, melious, fresh-eyes | 1 | A baseline not in the clone skipped the record in silence and moved the stamp. | fixed in `4240b5cd` (a warning, not a refusal) | Codex asked for a refusal. The report's own error for that baseline tells the owner to reset with `--stamp-tests`, so refusing would leave no way out; the stamp warns and says to compare by hand. Test L11 fails on 78859f51. |
| F3 | BUG | Codex, melious | 1 | An added line was found by the marker as a substring, so an owner's line quoting it was dropped or treated as added. | fixed in `4240b5cd` | `AUTO_RE` matches the whole generated line. Tests "an owner's line quoting the marker is kept" (L1, L6) fail on 78859f51. |
| F4 | RISK | melious, fresh-eyes | 1 | `--stamp` dropped the `pinned:` lines, ending a fork's report with nobody deleting a line. | fixed in `4240b5cd` | Test "pinned drift: --stamp keeps the pinned line" fails on 78859f51. |
| F5 | RISK | melious | 1 | `--stamp-tests <site>/tests/` would set the site root to the tests folder. | refuted | `dirname 'a/site/tests/'` prints `a/site` in zsh and in /bin/bash 3.2; a test of it passed on 78859f51, so it was taken out again. |
| F6 | RISK | fresh-eyes | 1 | No test covered keeping an added line while the file is still missing, or the skip when the owner's line names the file. | fixed in `4240b5cd` | Tests L6 and L7. Both pass on 78859f51 too (the code was right). Mutations X1 (no retention) and X2 (no tests/-relative skip) are to show they fail with that code removed. The run queued on `4240b5cd` was stopped when round 2's fixes replaced that head; it runs again on the final head. |
| F7 | NIT | melious | 1 | Neither the README nor the stamp's message said which path form a line takes. | fixed in `4240b5cd` | Both say: the path as the site has it or would. |
| F8 | NIT | melious | 1 | A `#` line the owner wrote in TESTS-VERSION was dropped. | fixed in `4240b5cd` | Test "the owner's comment line is kept" fails on 78859f51. |
| F9 | NIT | melious | 1 | `pinned: alpha` with no commit was reported as a commit missing from the clone. | fixed in `4240b5cd` | Test "a line with no commit fails … names no commit" fails on 78859f51. |
| F10 | NIT | melious, fresh-eyes | 1 | The tests computed today's date apart from the stamp, so a run across midnight failed. | fixed in `4240b5cd` | The tests read the date from the stamp's `copied:` line. |
| F11 | NIT | fresh-eyes | 1 | An added line stayed after the suite deleted the file. | fixed in `4240b5cd` | Kept only while a tracked template file at HEAD maps to the path. Test L9 fails on 78859f51. |
| F12 | NIT | fresh-eyes | 1 | With only pinned skills stale, the report still offers a refresh. | refuted | The first refresh writes the pinned baselines and moves the stamp; the pinned paragraph above the offer says what a refresh does to them. |
| F13 | NIT | melious | 1 | L5's comment claimed the scaffold's order without support. | fixed in `4240b5cd` | L5 now runs `--stamp`, then `--stamp-tests tests` from the site folder, as new-website's SKILL.md (lines 643 to 647) does. |
| F14 | BUG | Codex | 2 | With no TESTS-VERSION and no skills stamp this clone has, the stamp still moved on in silence: F2 covered only a TESTS-VERSION baseline. | fixed in `1e43be89` | The warning now covers every case with nothing to compare from. Test L13 fails on 4240b5cd. |
| F15 | BUG | Codex | 2 | An owner's `#` line naming a path, such as `# tests/new.spec.ts waits on the designer`, stopped the stamp recording that file. | fixed in `1e43be89` | Only `left_out:` and `kept:` lines count as naming a file. L2, L3 and L6 fail on 4240b5cd with that comment in the fixture. |
| F16 | BUG | Codex, melious (NIT) | 2 | F10 was half done: L9 and L10 still used the first stamp's date, and the stamp itself read the date twice. | fixed in `1e43be89` | The stamp reads the date once for its lines and `copied:`; L9 to L13 read it from their own stamp. No test fails on 4240b5cd, as the suite cannot move the clock. |
| F17 | RISK | melious | 2 | The warning was the only record of the gap: an owner who missed it lost the files in silence. | fixed in `1e43be89` | The stamp also keeps a `#` line naming the gap, which later stamps keep. L11 and L13 fail on 4240b5cd. |
| F18 | NIT | melious | 2 | `suite_commit: unknown` (or no such line) in TESTS-VERSION got the warning's advice, though nothing names a baseline; it now falls back to the skills stamp, as the report does. | fixed in `1e43be89` | Test L12 fails on 4240b5cd. melious raised the missing line as a follow-up; the same fallback covers it. |
| F19 | NIT | melious | 2 | No test for a short or malformed `suite_commit:` value. | no change | Any value that is not a commit takes the one branch L11 tests; a second test would test the same line. |
| F20 | BUG | Codex, melious (RISK) | 3 | Two comments said the stamp's fallback for an `unknown` baseline is the report's; the report refuses `unknown` and falls back only when TESTS-VERSION is absent. | fixed in `9a4e7fdc` | Both comments now say only that. `process_tests_stamp` returns 1 for `unknown` (whats-new.sh, its first check). |
| F21 | RISK | melious | 3 | L1 to L6 might take their date from the clock, not the stamp, so a run across midnight could fail. | refuted | `AUTO_NEW` is built from `TODAY`, which test_whats_new.sh reads from the stamp's `copied:` line just above it. |
| F22 | NIT | melious | 3 | A malformed baseline other than `unknown`, such as `n/a`, gets the "not a commit in this clone" wording. | no change | The wording is true of any such value, and the advice (compare by hand, add `left_out:` lines) fits it. |
| F23 | NIT | melious | 3 | Two stamps on one day could write the gap note twice. | no change | Each stamp writes this clone's HEAD as `suite_commit:`, so the next one has a baseline to compare from and adds no note. |
| F24 | BUG | Codex | wording | The release-notes row said the report no longer calls a site up to date while it lacks changes; L3 expects "Up to date" with the site's records listed under it. | fixed in `4dd93a2a` | The row says the report lists the changes a site has not taken. |
| F25 | BUG | Codex | wording | "A `left_out:` line for each file changed" took in `PUBLISHING.md`, `scripts/deploy.sh` and files the suite deleted, which the stamp never lists (`site_copy_of`, the HEAD check). | fixed in `4dd93a2a`, cut in `a4704eef` | See F28. |
| F26 | BUG | Codex | wording | "Until the owner deletes the line" left out a pinned skill the suite removed, whose line a refresh drops. | fixed in `4dd93a2a`, cut in `a4704eef` | See F27. |
| F27 | BUG | Codex | confirm | "Until the suite drops the skill" was wrong too: the report keeps listing it until the next refresh drops the line. | cut in `a4704eef` | The kind came back (record prose wider than the code), so the qualifiers went: the row says the report lists the changes "while the line stays". |
| F28 | BUG | Codex | confirm | "Each changed starter file the site lacks" still took in deleted and site-owned files. | cut in `a4704eef` | The rows no longer count: the stamp adds lines "for frozen files it finds changed upstream and missing from the site". |
| F29 | BUG | Codex | confirm | "Each pinned skill's old baseline": a pinned skill the suite removed gets no `pinned:` line. | fixed in `d6ccc8fe` | Both rows take the reviewer's own words, "each pinned skill the suite still has". No further pass: a fix in the reviewer's words, to record prose only. |

Mutation check on `6054595c` (the code is unchanged since), base `07211892`, tests
`scripts/test_whats_new.sh` and `scripts/test_whats_new_removed_skill.sh`: 25 mutations (the fix's
hunks reverted one at a time, and ten hand-made breaks of its guards), 22 killed, 3 survived. M7 and
M19 drop advice the script prints on screen after a stamp and in the report, which no test reads;
the record itself (`TESTS-VERSION`) is tested. M20 puts back the report's own copy of the oldest-stamp
loop that `oldest_stamp_base` replaced, the same behaviour, so it cannot fail.
