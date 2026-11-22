# DIFF review — move-token: `token-link` and the new token messages

Base `c0477040` (origin/main when the branch was cut) · depth: High (permissions and a token hand-off) ·
seats: Codex, GLM 5.3 on melious, and a fresh-eyes sub-agent (Claude Opus, read-only) · this session was
started by the Croftweaver manager and made the branch. Gate id 20261122T163024Z-44249.

Plan: the hub's `move-token/PLAN.md` (rows 1.1 and 1.2), plan-gated there. Artifact: each round
`git diff c0477040...HEAD -- . ':(exclude)docs/reviews/'`, with the plan's scenario list and the live look
(`move-token/evidence/LIVE-LOOK.md`) as evidence. Evidence per round: `make check` and
`make test-cloudflare-check` (which holds the move suite).

| Round | Reviewers | BUG / RISK / NIT | What came back |
|---|---|---|---|
| 1 | Codex, melious, fresh-eyes | 2 / 1 / 8 | recovery advice missing on parser refusals; a help claim `token-link` breaks; an account-ID shape taken from one account |
| 2 | Codex, melious, fresh-eyes (round's change only) | 2 / 2 / 2 | `--confirm <word>` with no command had no advice; the footer's status-page promise; the new pointer named one file; a deletion pointer on the launch-first refusal |
| 3 | Codex, melious, fresh-eyes (round's change only) | 2 / 1 / 1 | a pasted word before a trailing `--confirm` got no advice (the round-2 exemption); the footer still promised a status page |

Round 1 tokens: Codex 79,548 (146 s), melious 66,275 (440 s), fresh-eyes 146,685 (119 s).
Round 3 tokens: Codex 49,442 (121 s), melious 29,096 (252 s), fresh-eyes 101,461 (81 s). Round 3 was `--verify` on `a43fe9a2..c96f1a38`.
Round 2 tokens: Codex 54,303 (152 s), melious 22,579 (178 s), fresh-eyes 105,426 (112 s). Round 2 was `--verify` on the delta `870e3381..a43fe9a2`.

## Round 1 findings

| Id | Sev | Source | Finding | Status |
|---|---|---|---|---|
| R1-01 | BUG | Codex | A pasted token in an extra word, a leading-dash word or an unknown command got no "delete it" advice | fixed: one `PASTED_TOKEN` line on every parser refusal that may hold a pasted word; test over all cases |
| R1-02 | BUG | Codex | The usage footer said every run updates the status page; `token-link` does not | fixed: footer says "after every run of the other commands" |
| R1-03 | RISK | melious | A real account ID that is not 32 lowercase hex is refused with no way on | fixed: the refusal points to the clicks in section 6 |
| R1-04 | NIT | melious | BUGLOG row said `check` refuses a token longer than 7 days; it allows 8 | fixed |
| R1-05 | NIT | melious | `cmdTokenLink` said "not found" for any read error | fixed: "could not be read here" |
| R1-06 | NIT | melious | `zoneRefusal` built a sentence by patching `NEW_TOKEN` | fixed: composed from the command text |
| R1-07 | NIT | melious | A second import of `parseArgs` | fixed |
| R1-08 | NIT | fresh-eyes | "It still works until you delete it" on the pages.dev refusal, which sends her to no new token | fixed; the test asserts the line is absent |
| R1-09 | NIT | fresh-eyes | The isolation probe never showed the recorder catching `spawn` | fixed |
| R1-10 | NIT | fresh-eyes | The S1 regex had a dead alternative | fixed: asserts `Zone policy: Zone: Read and DNS: Edit` |
| R1-11 | NIT | fresh-eyes | The clicks pointer named only `docs/MOVE-TO-WORKERS.md`, which is not in the skill bundle | fixed: names both files |

UNVERIFIABLE in round 1 (both seats): Cloudflare's form, key handling and account-ID shape, which rest on one
account's live look and one docs page, and the suite results, which a read-only seat could not rerun. Neither is
a finding; the PR says what was and was not seen live.

## Round 2 findings

| Id | Sev | Source | Finding | Status |
|---|---|---|---|---|
| R2-01 | BUG | Codex; melious NIT; fresh-eyes NIT | `--confirm <word>` with no command refused with no "delete it" advice; `move --confirm` with nothing after it carried the advice though nothing was given | fixed: advice on "give the command" when anything was given, left off `--confirm needs a value` when no value follows; both cases in the S5 loop |
| R2-02 | BUG | Codex; fresh-eyes NIT | The footer still promised a status page after every other run; none is written when the run stops at the command line or finds no checkout | fixed: "a run of the other commands that finds the site's folder writes move-run/status.html" |
| R2-03 | RISK | Codex, melious, fresh-eyes | The account-ID refusal's pointer named only `docs/MOVE-TO-WORKERS.md`, which an installed skill does not hold | fixed: names the guide's section 6 and CLOUDFLARE_MOVE.md's token section; the test pins the whole sentence |
| R2-04 | RISK | fresh-eyes | Leaving "still works" off the launch-first refusal also left no pointer to delete a live token | refuted: that refusal sends her to launch the site, not to a new token; the same token is the one she uses after the launch; plan S2 asks for the line only where she is sent to a new token; if the token ends first, `check` says so and names the page |
| R2-05 | NIT | melious | No test pinned the rewritten "Then make a new token with …" sentence | fixed: asserted in the S1 domain-not-listed test |
| R2-06 | NIT | fresh-eyes | The child-process argument runs repeat shapes the parser loop covers | declined: they enter through the real command line, which the parser loop does not (Rule 9) |

Codex noted that `make check` does not run the move suite. That is right: the suite is `make test-cloudflare-check`,
which `.github/workflows/clean.yml` runs. Both were run on the final head.

## Round 3 findings

| Id | Sev | Source | Finding | Status |
|---|---|---|---|---|
| R3-01 | BUG | Codex, melious, fresh-eyes | `token-link <word> --confirm` and `<word> --confirm` refused with no advice: the round-2 fix left the advice off whenever `--confirm` came last, and the test exempted every argument list ending in `--confirm` | fixed by removing the exemption: `--confirm needs a value` always carries the advice (it says "if what you gave was a token", so it is harmless when nothing was); the test exempts only `[]` and `['token-link']` and adds both shapes |
| R3-02 | BUG / RISK | Codex BUG; melious, fresh-eyes RISK | The footer still said every run that finds the folder writes the status page; one that stops at a non-GitHub remote does not | fixed: footer says "most runs … also write"; the line that prints the page's path when none was written is older than this change: BUGLOG row |
| R3-03 | NIT | melious | The test comment said "the two" with nothing pasted | fixed with R3-01 |
| R3-04 | NIT | fresh-eyes | The `--confirm` branch read as one long ternary | gone with R3-01 |

Rounds 1 to 3 each found the parser's advice incomplete in a new shape. Round 3's fix removes the special case that
caused the last two, so the rule is now: every refusal after any argument carries the advice.
