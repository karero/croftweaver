# DIFF review — `npm run ship`'s live check with more than one `site:` address, and its ✓ line (0.35)

BUGLOG row of 2026-11-08 (ship.sh, the first line and the live-site check), plus two items the
release manager added to this PR: the test's ✓ line names only the checks that ran, and ship.sh's
marker comment no longer calls the marker a toolkit release. Depth: Normal (code a site's owner
runs; no box, user data, login, money, deletion or schema). No plan: a fix that restores intended
behaviour. Seats: Codex 0.167.0 gpt-6.1-sol and GLM 5.3 on melious in one command
(`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`), fresh-eyes Sonnet in round 1. Session "0.35 B"
made the branch, the worktree and the PR. The artifact leaves out `docs/reviews/`; the evidence
files sit in the session's scratchpad. Gate 20261108T215704Z-35225.

## Rounds

| Round | Head | Artifact | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|
| 1 | `9321fab5` | whole change; evidence READ 1–6 | Codex 116 s, 75,715 · melious 363 s, 45,503 · fresh-eyes 61 s, 110,163 | 3 / 1 / 5 |
| 2 | `2658a91a` | verify: delta since `9321fab5`; evidence READ 1–10 | Codex 121 s, 43,569 · melious 196 s, 21,238 | 2 / 0 / 1 |
| 3 | `d7958f28` | verify: delta since `2658a91a`; evidence READ 11–13 | Codex 115 s, 43,058 · melious 181 s, 22,289 | 1 / 0 / 2 |
| 4 | `5328e7d3` | verify: delta since `d7958f28`; evidence READ 14–15; `--earned-by site-comment-scan --cut "removed the comment scanner…"` | Codex 106 s, 39,892 · melious 133 s, 19,770 | 0 / 1 / 2, and one outside scope |
| merge link and wording pass (not a round) | `627037e0` | `merge_link.sh e3739bbe 5328e7d3 <new merge base>`, `--wording-pass` | Codex 92 s, 62,524 | 2 / 0 / 0, outside this change |
| second merge link (not a round) | `ca8ffdd3` | `merge_link.sh a2365d4e 627037e0 e1a56252` (#494): 18 lines, #494's two BUGLOG rows only | no seat run: the diff holds none of this change's lines | — |

Four rounds, 18 findings; with the merge link, 10 seat runs, 483,721 tokens (the script's running
total, fresh-eyes included).

## Findings

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| A1 | BUG | Codex; GLM as RISK | 1 | The comment rule needed a space before `//`, so `};// site: …` kept the old address | fixed, then cut (D1) | `2658a91a`; the scanner is gone in `5328e7d3` |
| A2 | BUG | Codex | 1 | The `/* */` rule cut text inside an address | fixed, then cut (D1) | as A1 |
| A3 | BUG | Codex | 1 | BUGLOG row 228 says 0.26 yet "No prompt follows" | refuted | row 257 says the 0.24 line no longer holds; the push-lines sentence is conditional on nothing new |
| B1 | RISK | GLM | 1 | ship.sh might set `site` again between the gate and the live check | refuted | `grep -nE '(^\|[^_a-z])site=' scripts/ship.sh` finds only the gate's lines |
| B2 | NIT | GLM | 1 | Test comment "with the same configs" | fixed, externally_reverified | `2658a91a` |
| B3 | NIT | GLM | 1 | Row 257 "0.26 covers the 0.24 row above" | fixed, externally_reverified | `2658a91a` |
| B4 | NIT | GLM | 1 | No TTY run at the reviewed head | fixed, externally_reverified | READ 7 |
| F1 | NIT | fresh-eyes | 1 | The marker comment rewrite is outside the fix | refuted | the release manager asked for it in this PR, 2026-11-08 |
| F2 | NIT | fresh-eyes | 1 | The version rows agree with the markers | not a finding | — |
| C1 | BUG | Codex | 2 | The lead-character rule still cut `a;/*…*/` and `a;//…` addresses | fixed, then cut (D1) | `d7958f28` (quote-aware scanner) |
| C2 | BUG | Codex | 2 | `const old = []// site: …` kept the old address | fixed, then cut (D1) | as C1 |
| C3 | NIT | GLM | 2 | The comments overclaimed what the rule kept | fixed, then cut (D1) | as C1 |
| D1 | BUG | Codex | 3 | The scanner reset its quote state on each line, so a `/*` in a template literal spanning lines hid the real address | fixed by a cut, externally_reverified | `5328e7d3`: no comment-stripping; any second `site:` match means the live check checks none and says why; P6, P7; mutations M12, M13 killed |
| D2 | NIT | GLM | 3 | The same reset, and "Quotes are tracked" | fixed (gone with the scanner) | `5328e7d3` |
| D3 | NIT | GLM | 3 | Row 258's test list left out a case | fixed, externally_reverified | `5328e7d3`: the row names P6 and P7 only |
| E1 | RISK | GLM | 4 | The address regex is in `site_of` and `site_count` both, and could drift | refuted | not introduced: both lines are main's byte for byte (`git show e3739bbe:…/ship.sh`, lines 71 and 79) |
| E2 | NIT | GLM | 4 | The test comment undersold what P6 and P7 assert | fixed, externally_reverified | `da93dc57`; the merge link's wording pass verified it |
| E3 | NIT | GLM | 4 | P6's third argument is asserted by nothing | refuted | `site_case` takes it; a fourth argument replaces the config by design |
| L1 | BUG | Codex | link | Main's Impressum-swap lines in `template-tests.yml` are code in a wording pass | outside this change | #493's code, reviewed there; unchanged here |

D1 was the third round running in which the comment scanner was wrong on a new input (A1/A2,
C1/C2, D1). Under the skill's "cut, don't patch" rule the fix replaced it with a strict rule
rather than another patch, the BUGLOG row's own first suggestion: the live check runs only when
`astro.config.mjs` has exactly one `site:` match, commented or not.

## Follow-ups

- Round 4, GLM, outside scope: with exactly one `site:` match and that one inside a comment, the
  first line names it and the live check checks it. Main's behaviour, unchanged; a config whose
  only address is commented out has no `site` for the build either. Sent to the release manager.

## Notes

- The ✓ line (the manager's item 1): it names the question's checks only when T1–T8 ran, and says
  why they were skipped. The CI step "Publish classifier as a site runs it (no SHIP_TEST_TTY)"
  fails on the old line: run locally against the old line, its check refused it. The no-TTY run
  adds about 1.5 minutes to the playwright job.
- Mutation check at the final code, by hand (the scratchpad's `mutate-cut.sh`): M12 (the live check
  reads the first address whatever the count) and M13 (the warning without its comment hint), both
  killed by P6 and P7 only. The scanner's mutations M1–M11 tested code that is gone.
- awk portability, asked in rounds 2 and 3, is moot: the final code uses no awk.
- After round 4 `origin/main` was merged (`627037e0`; #493 and others). The BUGLOG union kept no
  row twice (`check_buglog_rows.sh`: 257 rows). The merge link covered the change's own files.
- Then `origin/main` took #494 and was merged again (`ca8ffdd3`). GitHub could not merge
  `docs/BUGLOG.md`; locally the union driver kept base copies of this change's two edited rows,
  which were deleted (`check_buglog_rows.sh`: 258 rows).
