# DIFF review — bug sweep 3 of 2026-11-23 (two BUGLOG rows)

Base `ad5cc15f` (origin/main) · depth: Normal (shipped scripts, so not Light) · seats: Codex alone (REVIEW-RULES; no
High-row topic) and a fresh-eyes sub-agent (Claude Sonnet, read-only) · made by a sub-agent of the Croftweaver
manager's session. Artifact per round: the diff against the base (round 1) or since the last reviewed head (round 2),
with the brief as evidence.

Rows fixed: `move-to-workers.mjs` `after` last line (2026-11-10), `ship.sh` `noroute` arm unclear message (2026-11-13).
Rows left: `ship.sh` `notserved` (2026-11-14: a design choice, waits on the maintainer), `antigravity_release_test.py`
`CAPACITY`, `effects()`, `bypasses()` (each says "revisit if a real run shows one"; no capture exists; `bypasses()` needs
a policy choice), `phone-images.spec.ts` `goto` (the row says "if a real site hits it"; testing the fix through the
production flow needs a spec refactor).

| Round | Reviewers | BUG / RISK / NIT | What came back |
|---|---|---|---|
| 1 | Codex (base `ad5cc15f`, head `becb5c1c`); fresh-eyes | 2 / 0 / 0 (Codex); 0 / 2 / 4 (fresh-eyes) | the row's text claimed more than the patch did; a comment said "no HTTP status came back"; fresh-eyes: the hint on a pre-launch Worker, no release-notes row |
| 2 | Codex (`--verify`, base `becb5c1c`, head `feaa0f56`) | 0 / 0 / 0 | clean |

Tokens and time: round 1 Codex 52,499 (118 s); round 2 Codex 39,451 (102 s); fresh-eyes 118,768 tokens (43 s). Codex
alone (REVIEW-RULES); the script's warning that the standard pair was not met applies.

## Findings

| Id | Sev | Source | Finding | Status |
|---|---|---|---|---|
| R1-01 | BUG | Codex | BUGLOG row 2026-11-13 closed requirements the patch leaves open (keeping curl's code; hints in w12, w13, w15c, w15f) | fixed: the row says the smaller fix and its tests; w12 and w13 now check the hint; w15c and w15f share the path |
| R1-02 | BUG | Codex | Comment "No HTTP status came back" does not follow: `probe_site` drops curl's code on a failure | fixed: the comment says the probe names no status |
| R1-03 | RISK | fresh-eyes | The hint may send the owner of a pre-launch Worker to an empty `build.txt` | not fixed: said in the row ("may show no build.txt", not checked) |
| R1-04 | RISK | fresh-eyes | No "Next release notes" row for 0.36 to 0.37 | fixed: row added |
| R1-05 | NIT | fresh-eyes | Same comment wording as R1-02 | fixed with R1-02 |
| R1-06 | NIT | fresh-eyes | `has "    $m"` is a substring match | not fixed: the line sits under the build.txt line, and the test checks both |
| R1-07 | NIT | fresh-eyes | Coverage only in w11 and w16 | fixed with R1-01 |
| R1-08 | NIT | fresh-eyes | "until the Pages project is retired" (move script lines 2026, 2099) | not fixed: consistent with "not tested yet" |

Test evidence: with the `ship.sh` change reverted (marker kept), w11's two new checks failed; with the `move-to-workers.mjs`
texts reverted, the status-page assertion failed; both restored and passing (`check_ship_push.sh` 539 checks in a
`git archive` copy; `move-to-workers.test.mjs` 306 pass). Claims about those runs were UNVERIFIABLE for a read-only seat.
Round 2 ended with nothing open.
