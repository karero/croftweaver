# PLAN review — branch `plan/cut-or-continue` — when a cut turns out to be a patch

Plan: `docs/reviews/SKILL-PLAN-review-cut-or-continue.md`. Evidence sent every round with
`--evidence`: `docs/reviews/EVIDENCE-review-cut-or-continue.md`. Depth: Normal (a plan for the
review tool's own rules; no High-row item, so no red team). Seats: Codex and GLM 5.3 on melious,
per the seat rules for plans. Melious was out of balance in every round ("Insufficient balance for
request"), so each round stands on Codex alone. By the owner's rule (2026-10-27) no rerun of
melious is owed. Gate id `20261117T103119Z-61696`. This session (the cut-or-continue plan) created
the worktree, the branch and every commit.

Checks before round 1: `scripts/check_clean.sh` passed. The change adds three files under
`docs/reviews/` and nothing else; the full `make check` runs in CI on the PR.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|-------|------|----------|-----------|-----------------|--------------|
| 1 | `b82f1f99` | the whole plan | Codex alone; melious out of balance | 279 s, 82,165 | 4 / 3 / 0 |
| 2 | `f4d5e525` | the whole plan, `--verify` round 1's findings | Codex alone; melious out of balance | 194 s, 61,978 | 1 / 2 / 0 |
| 3 | `327ce368` | the whole plan, `--verify` round 2's findings | Codex alone; melious out of balance | 125 s, 65,347 | 0 / 3 / 0 |

## Round 1 findings

| Id | Sev | Finding | Disposition |
|----|-----|---------|-------------|
| A1 | BUG | T1's bar "no real cut is called PATCH more than once" let an always-PATCH judge pass, since each case runs once | fixed: at most one real cut in all may be called PATCH; a missing or garbled verdict counts as wrong |
| A2 | RISK | A PLAN round sends only the current plan, so a seat has no change to judge a cut by | fixed: the cut block carries the plan's own diff since the previous round (made exact in round 2, B1); T1 includes plan cuts |
| A3 | BUG | S5 said the next round runs after a refuted verdict, against the stop rule | fixed: another round runs only if owed or earned for another reason |
| A4 | RISK | The count settled every kind of a round when any line carried a cut; `review_log.sh` settles only the kinds on that line | fixed: recounted per line, as the script does; every figure came out the same (evidence §1) |
| A5 | RISK | The two-week check looked only at gates that still had a return, so it hid the gates a cut check saves | fixed: all gates that reach round 4 are compared, and the return count is reported apart |
| A6 | BUG | S4 gave the tokens from round 6 on as the whole gate's | fixed: both figures, each labelled (704,651 for the gate, 382,952 from round 6) |
| A7 | BUG | S2 said the ship.sh cut refuses any second `site:` line; it counts quoted http(s) addresses only | fixed: S2 now says what the commit does |

Codex marked the cost-log figures and the probe UNVERIFIABLE: it could not read the log or the
probe files. Round 2 added the per-gate table (evidence §4b) so the sums can be checked, and the
probe files' times.

## Round 2 findings

| Id | Sev | Finding | Disposition |
|----|-----|---------|-------------|
| B1 | BUG | The logged head doesn't pin the plan a round reviewed: with edits not yet committed, the diff against it runs back past the previous round | fixed: each `--plan --round N` keeps a copy of the plan it sent beside the cost log; the block diffs against the copy of the highest round below N; T2 checks an edit not yet committed between two rounds |
| B2 | RISK | T1 tested the block alone, not the whole request a seat gets in a round | fixed: T1a (block alone, go/no-go before any build) and T1b (6 cases through the built script with each round's own options, before merge); costs named |
| B3 | RISK | The baseline counted `max round − 3`, which counts a skipped round number | fixed: distinct logged round numbers above 3 (584 became 577) |

Round 2 confirmed the round-1 fixes A1, A3, A4 (the code), A5, A6 and A7.

## Round 3 findings

No BUG. All three RISKs are test guards that could pass while the thing they guard is broken, so
each changed what a builder builds. They earn round 4 (`--earned-by`).

| Id | Sev | Finding | Disposition |
|----|-----|---------|-------------|
| C1 | RISK | T1b could pass with every verdict missing | fixed: every seat must give a valid verdict in every case; a missing or garbled one fails T1b |
| C2 | RISK | T1b does not pin the seats, models and settings, so it may pass on a setup production does not use | the same kind as A2 and B2, its third time, so it got a cut, not a patch: T1b no longer claims to match production. It runs on the day's seats and settings and keeps its commands and raw output; the logged verdicts (column 18) and the two-week check cover later changes |
| C3 | RISK | T2's fixture (committed plan, then one edit) gives the same diff from the copy and from the head, so it cannot tell them apart | fixed: commit, edit, round 4, edit again, round 5; round 5's block must show only the second edit |

Codex marked the log figures and the probe UNVERIFIABLE for the third time. Following the rule
that a concern raised twice is tested directly, round 4's tree commits the probe's files and a
redacted copy of the 81 gates' log lines, with a script that recounts the figures from that file
alone (evidence §4c, §6).

While doing that, the recount from the redacted copy came out a little different. The first count
kept a gate's lines by their own date, so it held part of a gate that started on 2026-11-02 and
dropped that gate's earlier lines. Counting whole gates by their start leaves that gate out, and
every figure was recomputed:
82 gates became 81, 6.3% became 7.0% (of 258M, not 286M), 31 became 30, and the baseline became 234
gates, 574 rounds and 46.0M tokens. The ceilings, 10.7M and 5.4M, did not change.

The trail file was written during round 3, while Codex read the checkout. It was the only change
in the tree, and Codex noted it as untracked.
