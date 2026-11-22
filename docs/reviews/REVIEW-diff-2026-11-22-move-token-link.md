# DIFF review — move-token: `token-link` and the new token messages

Base `c0477040` (origin/main when the branch was cut) · depth: High (permissions and a token hand-off) ·
seats: Codex, GLM 5.3 on melious, and a fresh-eyes sub-agent (Claude Opus, read-only) · this session was
started by the Croftweaver manager and made the branch. Gate id 20261122T163024Z-44249.

Plan: the hub's `move-token/PLAN.md` (rows 1.1 and 1.2), plan-gated there. Artifact: each round
`git diff c0477040...HEAD -- . ':(exclude)docs/reviews/'`, with the plan's scenario list and the live look
(`move-token/evidence/LIVE-LOOK.md`) as evidence. Evidence per round: `make check`, and the 305-test
move suite.

| Round | Reviewers | BUG / RISK / NIT | What came back |
|---|---|---|---|
| 1 | Codex, melious, fresh-eyes | 2 / 1 / 8 | recovery advice missing on parser refusals; a help claim `token-link` breaks; an account-ID shape taken from one account |

Round 1 tokens: Codex 79,548 (146 s), melious 66,275 (440 s), fresh-eyes 146,685 (119 s).

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
