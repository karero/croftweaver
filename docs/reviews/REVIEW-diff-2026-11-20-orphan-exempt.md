# DIFF review — fix/038-orphan-exempt — the unlinked-pages list moves to `orphan-exempt.txt`

Base `b07d04f3` (origin/main when the branch was cut) · depth: Normal, a starter change with a new reader and a
shipped file · verdict: no BUG and no counted RISK open after round 2, and one wording confirmation · 2 rounds
and the confirmation · Codex alone (REVIEW-RULES), plus a fresh-eyes pass in round 1 · this session was started by the
Croftweaver manager and made the branch. Gate id 20261120T141737Z-63255.
Plan: `PLAN-orphan-exempt-list-v6.md` (reviewed before the build; the owner gave the go).

Artifact: each round `git diff origin/main..HEAD`, with the evidence file the script was given (runs, mutations, what was
not run). The last reviewed code head is `dfdce5f1`.

| Round | Reviewers | BUG / RISK / NIT | What came back |
|---|---|---|---|
| 1 | fresh-eyes (Claude Sonnet sub-agent, read-only); Codex | 0 / 2 / 3 | Codex: the S12 "never MISSING" check in `test_whats_new.sh` could not fail. Fresh-eyes: `orphan-exempt.txt` missing from the scorecard's `TESTED` list; invisible characters (U+200B, U+00AD, U+FFFD) accepted; a CI grep that matched static hint text; the test header overclaimed |
| 2 | Codex (`--verify`) | 1 / 0 / 0 | all five round-1 fixes verified; one comment called U+FFFD "a byte that is not UTF-8" |
| confirm | Codex (`--wording-pass --verify`) | 0 / 0 / 0 | the comment fix, over its delta only: clean |

Token cost: round 1 Codex 69,243 and fresh-eyes 155,930; round 2 Codex 67,436; confirmation Codex 25,761; 318,370 in all.

## Disposition

- All five round-1 findings were fixed. The two RISKs (the S12 check, the scorecard list) each come from an ordinary change:
  tracking the file by mistake, and adding an exemption after a scorecard run. The S12 fix has a mutation: with the file
  added to `TEMPLATE_TRACKED`, `test_whats_new.sh` goes red (2 FAIL) and is green again when restored. The four new character
  cases fail against the round-1 module.
- Round 1's fresh-eyes NIT on invisible characters is a cheap extension of the same refusal, so it was made, not deferred.
- Both reviewers called the Playwright, CI and Linux-bash claims unverifiable from their seat. They were run by hand
  (evidence items 1, 2, 3); the CI step itself runs only on GitHub.
- `make check` ran green on `a21078bc` and, after the fixes, on the head the PR names. Its first run after the fixes
  stopped at `check_clean.sh`, which found a personal name in this file; it was removed and the whole check run again.
