# DIFF review — ship.sh live check: an answer is an answer (branch `fix/ship-live-check-answered`)

Base `51309e60` · depth: Normal (shipped template code that publishes; not auth, data or deploy
wiring) · verdict: CLEAN after 2 rounds, 5 findings · authority used: WORKTREE-WRITE and
BRANCH-COMMIT — this session created the worktree and the branch.

The fix for S1, S2 and S3 of `REVIEW-diff-2026-11-13-pr540.md`, with S5. Gate id
20261113T122727Z-66430. Evidence sent to every seat: real curl 8.7.1 against a local test server
(a 503 cut short gives exit 18 with status 503; a 200 that stalls gives exit 28 with status 200; a
dead port gives exit 7 with status 000), and the template's test suite under `/bin/bash` 3.2.57.

The second seat, GLM 5.3 on melious, failed in both rounds and in one retry (round 1: the reply
stopped mid-stream; round 2, twice: "Hold not found or expired"). Both rounds count on Codex
alone, with fresh-eyes beside it in round 1.

| Round | Head | Artifact | Reviewers | seconds, tokens per seat | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `15c1f457` | full, `--base 51309e60` | Codex (gpt-6.1-sol, config effort, read-only); fresh-eyes (Claude Sonnet sub-agent, read-only); melious FAILED | codex 182 s, 47,734; fresh-eyes 39 s, 92,712; melious 567 s, no figure | 2 / 0 / 2 |
| 2 | `6be34630` | the round's change, `--base 15c1f457`, `--verify` | Codex (medium effort); melious FAILED twice | codex 97 s, 33,555; melious 929 s and 733 s, no figure | 1 / 0 / 0 |

| id | Sev | Source | Round | Finding | Status | Evidence |
|---|---|---|---|---|---|---|
| P1 | BUG | Codex | 1 | The new case for an answer curl failed on led into "Cloudflare didn't build" and the dashboard steps. | fixed | The dashboard steps follow only a look that showed another build. Every other verdict ends "could not confirm the deploy; it does not mean the build failed" and points to build.txt. L3f to L3j assert that the verdict lacks "Cloudflare". Codex ran the extracted loop in round 2. |
| P2 | BUG | Codex | 1 | Another commit id was called "an OLD build"; a later publish from another clone would be newer. Older than this change. | fixed | The verdict names the build served and says "most likely the OLD build". L3c asserts it. |
| P3 | NIT | fresh-eyes | 1 | The comment above the loop still described three outcomes. | fixed | Reworded. |
| P4 | NIT | fresh-eyes | 1 | A build.txt holding `dev` now reads "not with a commit id". | refuted | Intended: `dev` is no build's id. |
| P5 | BUG | Codex | 2 | A new comment said "no look showed another build"; the code knows the last look only. Output unaffected. | fixed | The comment says "the last look". |

Notes:
- No round 3: round 2 called for no fix that changes what runs (P5 is one comment).
- The tests: `/bin/bash tests/check_ship_push.sh` at `6be34630` passed (82 publish outcomes, 521
  checks on real git; T1 to T8 skipped, `SHIP_TEST_TTY` not set). Run against `ship.sh` from
  before the fix, round 1's new cases fail (8 checks, L3g to L3j).
- UNVERIFIABLE: 6 asked (Codex, both rounds), 0 confirmed. Not tested: a real Cloudflare site, and
  a site that answers early looks and gives no reply on the last (the stub answers every look
  alike). "Most likely the OLD build" is a judgment, not a measurement.
- `template-version` 0.30 to 0.31 in `ship.sh` and `tests/check_ship_push.sh`.
