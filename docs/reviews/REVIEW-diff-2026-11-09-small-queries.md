# DIFF review — four-week check: page total and small queries

Plan: `website-new-page/PLAN-small-queries.md` in the private hub (PLAN gate: 5 rounds, Codex alone,
no BUG open; the owner chose the page-total finding after a fresh-eyes check of the plan's numbers).
Depth: Normal (skill text a builder follows, and a test of the review script; no box, user data,
login, money, deletion or schema). Seats: Codex gpt-6.1-sol alone, `--seat codex`: GLM 5.3 on
melious was out of balance when checked in this session's PLAN gate, so by the owner's rule of
2026-10-27 the gate stands on Codex alone. Round 1 also had a fresh-eyes pass on Sonnet.
Gate 20261109T193508Z-81844.

## Rounds

| Round | Head | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|
| 1 | `67d7b738` | Codex 135 s, 43,564 · fresh-eyes 70 s, 105,612 | 1 / 1 / 3 |
| 2 | `ed4b89e3` (delta from `67d7b738`) | Codex 110 s, 33,731 | 0 / 0 / 0 |

Two rounds, 5 findings, 182,907 tokens. Then the wording pass (Codex, 42,944 tokens) over the trail
and the release-notes row: one contradiction, the row still said the page total holds the hidden
clicks; fixed to the step's own words, and its confirmation (Codex, 35,133 tokens) found nothing.
Gate total 260,984 tokens.

## Round 1

| Seat | Kind | Finding | Disposition |
|---|---|---|---|
| Codex | BUG | Adding the old and the new address's rows counts a kept address twice, hiding a loss | Fixed: the old address's row is added only where the page moved; a kept address is one row, counted once |
| Codex | RISK | That page rows keep the clicks of queries Search Console hides lacks support | Fixed by a cut: Google's docs do not say so (READ in the evidence); the text now says only that the page row often counts many more clicks than the query rows add up to, which the measurement shows |
| Fresh-eyes | NIT | `<window>-pages.csv` lets two after pulls write one file | Fixed: `before`, `after`, `old-after` |
| Fresh-eyes | NIT | "For information only" beside "still count" reads as "ignore it" | Fixed: "never judged on its own" |
| Fresh-eyes | NIT | The guard's strings fail if the quoted block is rewrapped | No change: such a failure is loud, and each string is one line today |

## Round 2

No BUG/RISK/NIT findings.

Unverifiable, not counted: why page rows count more clicks than query rows (Google's docs say only
that grouping by page or query "may drop some data"); the subagent runs of step 9, whose reports are
a client's data and went to no seat.

## The guard can fail

Point 4 cut from a copy of `references/content-review.md`; `test_failed_tier_report.sh` in that copy
printed six FAIL lines, the three new checks for each stub seat, and exited 1.
