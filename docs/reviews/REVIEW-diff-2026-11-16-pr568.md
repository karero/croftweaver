# DIFF review — karero/croftweaver#568 — independent_review.sh: the Codex seat refuses a prompt that is not UTF-8, and says where

Base `36229c9d` · depth: Normal (the review script's own seat code and its tests; no user data,
auth or deploy path) · verdict: CLEAN after round 3 by stop condition (a2) (3 rounds, 20 findings
after dedup; gate total 339,399 seat tokens logged, fresh-eyes included) · authority used:
WORKTREE-WRITE and BRANCH-COMMIT. This session (the bug sweep before 0.36) created the worktree
and the branch `fix/codex-seat-not-utf8`.

Artifact: round 1 `git diff 36229c9d...10887bbd -- . ':(exclude)docs/reviews/'`; round 2 the delta
`10887bbd...af00b0b1`; round 3 the delta `af00b0b1...977fa27f`. Evidence file, the same file
every round, grown each round: READs 1 and 2 (a real run on a Latin-1 diff, the suite), READs 3 to
5 in round 2 (codex-cli 0.169.0 on Latin-1, a surrogate, an overlong and U+FFFF; the validator on
the same; the suite), READs 6 to 8 in round 3 (codex-cli on U+FDD0 and U+FFFE; the suite with each
round 2 fix reverted; the suite on CI's ubuntu-latest), READ 9 after round 3 (codex-cli and the
validator on all 66 noncharacters and four refused kinds; a header ending in a lead byte). Gate id
20261116T001355Z-83433.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `10887bbd` | full, merge base with origin's HEAD | Codex (gpt-6.1-sol, config effort, read-only); melious (glm-5.3, HTTP API, text only); fresh-eyes (Claude Sonnet sub-agent, read-only) | codex 171 s, 63,727; melious 223 s, 29,313; fresh-eyes 51 s, 115,693 | 3 / 3 / 5 after dedup |
| 2 | `af00b0b1` | the round 1 fixes, `--base 10887bbd`, `--verify` | Codex (effort medium); melious (glm-5.3) | codex 151 s, 36,277; melious 180 s, 29,568 | 1 / 1 / 4 after dedup |
| 3 | `977fa27f` | the round 2 fixes, `--base af00b0b1`, `--verify` | Codex (effort medium); melious (glm-5.3) | codex 212 s, 44,498; melious 135 s, 20,323 | 0 / 2 / 1 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| F1 | BUG | Codex | 1 | `--where` copied the `diff --git` header into the reason line with its control bytes (ESC[2J reached the terminal). | fixed in `af00b0b1`, then R2-3 and R3-3 | Test "a header's control bytes print as ?". Round 2 confirmed. |
| F2 | BUG | Codex | 1 | The locator and the validator disagreed: U+FFFF alone gave "could not be found"; U+FFFF then Latin-1 named the later line. | fixed in `af00b0b1` | With `--where` one RFC 3629 scan decides both. Round 2 reproduced both cases. |
| F3 | RISK | Codex, fresh-eyes | 1 | Encode strict refuses noncharacters that Codex may accept, so the check could fail a usable seat. | fixed in `af00b0b1` and `977fa27f` (R2-1) | READ 3, 6 and 9: codex-cli 0.169.0 accepts all 66 noncharacters and refuses what the validator refuses. Test "noncharacters are UTF-8: Codex runs". |
| F4 | BUG | Codex | 1 | The test comment said Melious's builder "replaces each bad byte". | fixed in `af00b0b1` | Now "replaces what is not UTF-8 with U+FFFD". Round 2 confirmed. |
| F5 | RISK | melious | 1 | The UTF-8 check ran after seat_fits, so a Latin-1 prompt could fail on size with the wrong remedy. | fixed in `af00b0b1` | The check runs first; t11k asserts the UTF-8 reason and not the size one. |
| F6 | RISK | melious, fresh-eyes | 1 | Codex's refusal was not observed on the installed version. | fixed (settled) | READ 3: codex-cli 0.169.0, exit 1, "input is not valid UTF-8". |
| F7 | NIT | melious | 1 | The t11n label described only the Melious half. | fixed in `af00b0b1` | Relabelled; it also greps the Codex UTF-8 failure. |
| F8 | NIT | melious | 1 | BUGLOG row 169's status omitted the perl condition. | fixed in `af00b0b1` | The row says what happens without perl. |
| F9 | NIT | melious | 1 | A perl failure left the reason reading "not valid UTF-8 ()". | fixed in `af00b0b1` | The seat fails only when `--where` printed a line; test "a file it cannot read prints nothing". |
| F10 | NIT | melious | 1 | Without iconv the u8 cases cascade. | refuted | The first FAIL line names iconv; READ 8 shows the iconv-made case passing on CI's ubuntu-latest. |
| F11 | NIT | melious | 1 | A "diff --git" line in a hunk body could be named as the part. | refuted | Body lines start with "+", "-", " " or "\", never "d"; both seats agreed in round 2. |
| R2-1 | BUG | Codex, melious | 2 | F3 half fixed: seat_fits still asked Encode, so a Codex prompt holding U+FFFF counted at three times its bytes. | fixed in `977fa27f` | seat_fits passes `--where` for codex. Test t11q; READ 7: it fails with the change reverted. Round 3 confirmed. |
| R2-2 | RISK | melious | 2 | U+FDD0 was never run through codex-cli. | fixed (settled) | READ 6, then READ 9 for all 66. |
| R2-3 | NIT | melious | 2 | The cleaning turned valid letters (café) into "?". | fixed in `977fa27f` | Only control characters are replaced; READ 7: the new test fails with the old `tr`. |
| R2-4 | NIT | melious | 2 | The run_codex comment misstated seat_fits's count. | fixed in `977fa27f` | Round 3 confirmed. |
| R2-6 | NIT | melious | 2 | t11p's label says "(T11m)". | refuted | It names the case whose input t11p reuses; Codex agreed in round 3. |
| R2-7 | NIT | melious | 2 | READ 1 shows the summary lines twice. | refuted | The script prints its summary to stdout and stderr; READ 1 joined them. Codex traced it in round 3. |
| R3-1 | RISK | Codex | 3 | Codex's acceptance of noncharacters rests on supplied measurements; test the real CLI on all 66. | refuted | READ 9: the real codex-cli 0.169.0 on all 66 answered "ok", exit 0, and the validator agrees; it refuses the four other kinds both refuse. A test against the real CLI cannot run in CI: no workflow under `.github/` installs or signs in to Codex. |
| R3-2 | RISK | melious | 3 | `$before` could end inside a malformed sequence, so a raw lead byte could reach the terminal. | refuted | `$at` is where the scan of whole well-formed sequences stopped, so `$before` holds only complete ones. READ 9: a header ending in `\303` prints ASCII only. |
| R3-3 | NIT | melious | 3 | Bidi controls (U+202A–U+202E, U+2066–U+2069) in a header could reorder the FAILED line. | fixed in `db54bd63`, locally_verified | Replaced with "?"; test "a header's bidi controls print as ?", which fails with the regex before this fix. Closing edit not externally re-verified. |

Notes:
- F3, F6 and R2-1 were each raised by both seats or by a seat and fresh-eyes.
- UNVERIFIABLE, round 1: Codex 2, melious 6, 2 confirmed (Codex's refusal, as F6; Encode against
  the regex, as F3). Round 2: Codex 3, melious 4, 1 confirmed (U+FDD0, as R2-2); iconv on CI was
  answered by READ 8. Round 3: Codex 3, melious 2; READ 9 answered the CLI's rule and the lead
  byte, and Codex asked again for READ 7 and 8, which it could not rerun read-only.
- Stop: round 3 had no BUG, and its two RISKs were refuted, so no round 4 was owed (stop
  condition (a2)); its NIT was fixed without one.
- The record-prose re-gate: the BUGLOG row changed in round 1 and both seats read it in rounds 1
  and 2; nothing in it changed after.
- `make check` passed before each round and after the last edit.
