# Plan: when a cut turns out to be a patch (independent-review, step 6)

Status: the owner chose option (e) on 2026-11-17: at a kind's second return after a cut, the
session asks its manager. This plan is rewritten for it; building waits for his go. Nothing built.
Evidence: `EVIDENCE-review-cut-or-continue.md` (same folder). The first version of this plan
(option 3, a seat's cut verdict) is in git history; its backtest failed (evidence §7).

## What

From round 4, a round needs `--earned-by`, naming the finding kinds that earned it. When a kind
already earned a round since its last cut, the round that names it again needs `--cut "<what was
removed or replaced>"`; the first round after a cut runs without one. But the host writes that text and grades its own cut, so
a patch can pass as a cut, round after round. This plan decides who stops that chain, and when.

## Why

- On the 0.36 move-prep gate (branch `fix/move-prep-036`), the lastmod scan's kind earned rounds
  4 to 7. The `--cut` texts at rounds 5, 6 and 7 were patches (each changed one regex rule). The
  real cut was turning the scan into a warning; its manager session chose it after round 7, and it
  was reviewed in round 8. Rounds 6 and 7 cost 86,430 Codex tokens.
- In the cost log, 81 gates that started from 2026-11-03 to 2026-11-17 had a kind come back after
  a round that carried a `--cut`. From that round on they ran 203 rounds and logged 18.0M tokens,
  7.0% of the 258M those days' gates logged (45 seat runs logged no tokens). The rounds after that
  first return are the most any change can save: 122 rounds, 10.7M tokens. In 30 of the 81, the
  round of the return was the last.
- Nothing in the script can tell a cut from a patch. Line counts can't: the lastmod cut added 33
  lines and removed 25, and the patches before it changed 5 or 6 lines each. Nor could a seat in
  the backtest: Codex called 3 of 11 real cuts patches and 3 of 11 patches cuts (evidence §7).

## What the owner chose (2026-11-17, relayed by the manager, his picks word for word)

- His 2026-10-22 rule stays: "Keep my rule (Recommended)". He is not asked whether to run a round.
- Scope cuts (a stop becomes a warning, a check goes): "The manager". The session's manager
  decides and tells him in the PR.
- The test of option 3: "Yes, run the test". It ran and failed, so option 3 was dropped.
- Who is asked at a second return: "The manager (Recommended)", option (e) below. He gets no new
  questions.

## The options he chose from (14 days of the cost log)

| | Who is asked | When | Asks | Most it can save |
|---|---|---|---|---|
| (b) | the owner | the first return after a cut | 81 gates | 122 rounds, 10.7M tokens |
| (c) | the owner | the second return | 45 gates | 61 rounds, 5.4M tokens |
| **(e)** | **the session's manager** | **a kind's second return** | **39 gates, 78 rounds** | **57 rounds, 5.0M tokens** |
| (f) | nobody | — | none | none |

(b) and (c) count returns per gate, of any kind, as the first version did. (e) counts per kind: a
round asks when its `--earned-by` names a kind that two earlier rounds of the gate settled with a
cut. In 39 of the 81 gates a round would ask; 78 rounds would ask in all, since "keep fixing" asks
again at the next return. `evidence-cut-or-continue/recount_per_kind.py` recounts this from the
redacted log alone (evidence §8). The closing reminder of design 2 prints more often than that:
after 172 rounds, in all 81 gates, since a host that passes `--cut` on a kind's first return has
two cut rounds on it at once. The saving is a ceiling: it assumes every first ask ends the
kind's chain, which "keep fixing" does not.

## Design

1. `review_log.sh round-check`: a new record, `ask <kind> <cut rounds> <kind as logged>`, for each
   kind given with `--kinds` that two or more earlier rounds of this gate settled with a cut. It
   counts distinct round numbers, not lines: each seat logs its own line, so a round with two
   seats would otherwise count two cuts. Kinds compare normalised, as `owed` does.
2. `independent_review.sh`, at the end of a round run with `--cut`, counts the same way, this
   round included, before the host has read the findings. For each kind with two or more cut rounds it prints, in its closing lines and
   in the running-total line the owner reads: "Kind K was cut in rounds X and Y. If this round
   found it again, ask your manager before the next fix: take it out, make it a warning, or keep
   fixing?" That is when the host sorts the findings, before it writes the next fix.
3. `independent_review.sh`, at the start of a round: when round-check gives an `ask` record and
   the run has no `--manager-said "<kind>: <answer>"` for that kind, it prints a warning naming the
   kind and goes on, and the gate line shows "manager not asked" for it. The flag is given once per
   kind: in 17 of the 78 rounds that would ask, two or more kinds were due at once. The answers are
   logged in a new column 18, `manager_said`, joined with "; " (`-` when none), and shown in the
   gate line.
   Nothing refuses: the owner prefers notices to refusals in the review process. A notice is also
   what failed before, so the two-week check counts how often hosts ask.
4. `SKILL.md` step 6, after "Cut, don't patch": when a kind comes back after two cuts, the host
   asks its manager, the session or person that started it and directs it, "take it out, make it
   a warning, or keep fixing?", with the kind, the two cut texts and the finding. Where nobody
   started the session, it asks the owner. It records the answer in the trail and passes it as
   `--manager-said "<kind>: <answer>"` on the next round. "Take it out" and "make it a warning" are scope cuts: the
   manager decides them and tells the owner in the PR's first lines. "Keep fixing" asks again at
   the next return. This replaces the sentence in step 6 that sends scope changes to the owner.
5. Nothing else changes: the rule that wants `--cut` stays as it is, so does the 2026-10-22 rule, and so does the owner's decision past round 8.

The log: `add` takes `--manager-said` and writes 18 fields. An existing log keeps its header, as
it did when columns 15 to 17 came; every reader takes a missing field 18 as `-`.

## Scenarios (real gates)

- **S1, lastmod (`fix/move-prep-036`).** Cut rounds 5 and 6. Given round 6 found the regex kind
  again, when round 6 ends, then its closing lines name the kind and tell the host to ask its
  manager. The manager says "make it a warning", which is what it chose after round 7, and round 7
  reviews the warning. If the rest goes as it did, the gate ends one round earlier: round 7's
  patch review, 49,061 tokens, does not run (evidence §5).
- **S2, a long chain (`fix/move-analytics-gap-035`).** Twelve rounds; cuts at rounds 5 to 12 each
  narrowed what one config reader reads. The ask comes at the end of round 6. Round 7 still reviews
  whatever the manager chose, so rounds 8 to 12 (269,860 tokens) are the most "take it out" or
  "make it a warning" there can save; a different round 7 would have cost something else.
- **S3, a cut that held.** Given a kind cut once whose next round does not find it again, then
  nothing is printed and nobody is asked. In 42 of the 81 gates no round would ask.
- **S4, keep fixing.** Given the manager says "keep fixing", then the answer goes in the trail and
  in column 18, and if the kind comes back after the next cut, the closing lines ask again.
- **S5, a host that does not ask.** Given round 7 runs with `--earned-by K` after two cuts on K
  and no `--manager-said`, then it prints a warning and runs, and the gate line the owner reads
  shows "K: manager not asked". Nothing stops.
- **S6, a rotating kind (`plan/live-analytics-check`, its plan gate).** One kind was cut in
  rounds 4 and 5, so round 5's closing lines remind the host; round 6 did not name it, so nobody is
  asked. Rounds 6 and 7 named new kinds, and the owner cut scope at round 6 himself. (e) does not
  see a chain whose kinds change names, and the script's rename notice sees only names where one
  starts the other.
- **S7, two seats.** Given a round where Codex and the second seat both log the cut for K, then it
  counts as one cut round, and one earlier cut round plus this one makes the first ask.

## How it is tested

- **T1, through the real entry point.** In `test_round_checks.sh`, with a stub seat and
  `REVIEW_LOG` on a scratch log: `--round 1`; `--round 4 --earned-by k`; `--round 5 --earned-by k
  --cut a`; `--round 6 --earned-by k --cut b`. Round 5's closing lines hold no ask; round 6's hold
  the ask for k, naming rounds 5 and 6, in the running-total line too. Then `--round 7 --earned-by
  K` (case changed) `--cut c` without `--manager-said`: the warning is printed, the run goes on
  with its usual exit status, and the gate line shows "manager not asked". The same round with
  `--manager-said "k: keep fixing"`: no warning, column 18 holds the answer, and the gate line
  shows it. A round due for two kinds with an answer for one warns for the other only. A second
  fixture logs two seat lines per round: one cut round must not ask. A third: a kind
  cut once never asks.
- **T1 can fail.** Count lines instead of rounds, and the two-seat fixture asks after one cut;
  drop the normalising, and `K` does not match `k`; drop the warning, and the third run's output
  check fails; key the answer to the round instead of the kind, and the two-kind round gives no
  warning. Each is tried once by hand before the review, as a mutation check.
- **T2.** `check_prompt_sync.sh` and `make check` pass. The old-header test of
  `test_round_checks.sh` (a 14-column log) now expects `add` to append 18 fields, and a new fixture
  with a 17-column header checks that round-check and the gate line read a missing field 18 as
  `-`.
- **After two weeks,** compare all gates that reach round 4 with the baseline (234 gates, 574
  rounds past round 3, about 2.45 a gate, 46.0M tokens; evidence §4c). Count the asks, how many
  carried `--manager-said`, and each answer. If fewer than three quarters of the asks carried an
  answer, the session that runs the check proposes to the owner, through its manager, that the
  script refuse such a round, as it refuses a missing `--cut`. If rounds past round 3 per gate are
  not lower, it says so, and the owner decides.

T1a, the backtest of option 3, ran on 2026-11-17 for 350,196 tokens (evidence §7). Option (e)
has no model in its loop to test: the script counts, and a manager decides.
