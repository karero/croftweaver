# DIFF review — bug sweep 5 of 2026-11-23 (two BUGLOG rows)

Base `5152f2df` (origin/main) · depth: Normal (a shipped script, so not Light) · seat: Codex alone (REVIEW-RULES; no
High-row topic) · fresh-eyes not run: made by a sub-agent of the Croftweaver manager's session, which may not start
subagents (logged NOT-COUNTED; the manager decides). Artifact per round: the diff against the base (round 1) or since
the last reviewed head (rounds 2 and 3, `--verify`), with a brief as evidence.

Rows fixed: `scripts/check_clean.sh` does not read `.claude-plugin/` (2026-10-12); a new top-level path is not read until
listed (2026-10-13).
Rows in the sweep's brief that were already closed on `origin/main`, so not touched: the `^`-anchored name entry
(2026-10-06, fixed in #189), `packages/` (2026-10-12, fixed in #277), and the two `website-forms` rows (2026-10-06,
dropped 2026-10-08: `skills/website-forms` no longer exists).

| Round | Reviewers | BUG / RISK / NIT | What came back |
|---|---|---|---|
| 1 | Codex (base `5152f2df`, head `b7dbb9cd`) | 1 / 1 / 0 | a comment said the new paths are not in the handoff zip (`.gitattributes` is); git quotes a name holding a double quote, so a covered folder was reported |
| 2 | Codex (`--verify`, base `b7dbb9cd`, head `8b3b9299`) | 2 / 0 / 0 | a name made of two listed names (`docs scripts`) matched as a substring; a name of newlines vanished in command substitution |
| 3 | Codex (`--verify`, base `8b3b9299`, head `a96874a7`) | 0 / 1 / 0 | both new cases staged both names, so one could pass for the other |

Tokens and time: round 1 Codex 56,699 (159 s); round 2 35,552 (87 s); round 3 29,180 (75 s). Fresh-eyes: none. Codex
alone (REVIEW-RULES); the script's warning that the standard pair was not met applies.
The fix for round 3's RISK is after the last round: it is unreviewed (a test-only change; see R3-01).

## Findings

| Id | Sev | Source | Finding | Status |
|---|---|---|---|---|
| R1-01 | RISK | Codex | a tracked name with a double quote is quoted by git; `cut` then named a folder that does not exist | fixed: the guard reads `git ls-files -z` and takes the part before the first `/`; test: a tracked `docs/a"b.md` passes (fails with the round-1 guard) |
| R1-02 | BUG | Codex | the comment said the optional paths are not in the zip; `.gitattributes` is | fixed: "not all in" |
| R2-01 | BUG | Codex | membership was a substring test on the joined lists: a root file named `docs scripts` passed the guard and was scanned by nothing | fixed: exact equality against each list entry; test: that file fails (fails with the round-2 guard) |
| R2-02 | BUG | Codex | a name made only of newlines vanished in command substitution, so the guard stayed silent | fixed: a flag, not the collected text, decides the failure; names print through `printf %q`; test: such a file fails (fails with the round-2 guard) |
| R3-01 | RISK | Codex | the two new cases staged both names, so the space case satisfied the newline case | fixed; round 4 (manager's session) clean: each name is staged alone and the newline case requires its escaped line (`$'\n'`); with the round-2 guard restored both cases fail |

## Test evidence

Every run is `/bin/bash scripts/test_clean_denylist.sh` unless named. All runs are in this worktree; the fixed script
was restored after each mutation and compared with `cmp`.

- Round 1 head: exit 0, "all passed", 126 cases. Whole `check_clean.sh` reverted to `origin/main`: 9 FAIL (the three OK-line
  cases, `.claude-plugin` clean, name and email, a name in `.gitignore`, a new tracked folder, a new tracked root
  file). Guard disabled (`if false`): 2 FAIL (the folder and root-file cases). `.claude-plugin` left out of
  `PRESENT_PATHS`: 3 FAIL (its clean, name and email cases).
- Round 2 head: 127 cases, exit 0; with the round-1 guard restored, the double-quote case failed.
- Round 3 head: 129 cases, exit 0; with the round-2 guard restored, the two new cases failed.
- After R3-01: 129 cases, exit 0; with the round-2 guard restored, both separately staged cases failed.
- `bash scripts/check_clean.sh` on the repository: exit 0 at each head; its OK line lists `.claude-plugin`, `.agents`,
  `.github`, `.gitignore` and `.gitattributes` among the paths scanned. `bash scripts/check_buglog_rows.sh`: ok.
- Not run: `make check`, CI, and the other callers of `check_clean.sh` (`package.sh`; `test_check_lock.sh` stubs it).
  Git's own serialization of odd names was exercised through the test fixtures only, not byte-compared.

## Manager's rounds (Croftweaver manager session)

- Round 4: Codex, `--verify`, base `a96874a7`, head `ae327724`, `--earned-by test-isolation`: clean. `codex 59s (20904 tokens)`.
- Fresh-eyes: a read-only Sonnet sub-agent on the whole diff (113,898 tokens): no BUG, no RISK; 3 NIT. Fixed: both scripts' header comments now name the new paths; the BUGLOG row no longer says tests cover `.agents/`. Left: no test runs the guard under `CLEAN_MASK_NAMES=1` (checked by hand: the folder-name line is withheld). Rare cases it listed (the zip unpacked inside another repo that tracks it; a tracked top-level symlink) are not counted.
- The NIT fixes are comment and BUGLOG text only; no further round.
- Manager's runs on `ae327724`: `test_clean_denylist.sh` all passed (129 cases); `check_clean.sh` exit 0; run time 27.2 s against 22.8 s for main's script in the same tree.
