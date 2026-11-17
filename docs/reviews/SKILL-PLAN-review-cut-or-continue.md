# Plan: when a cut turns out to be a patch (independent-review, step 6)

Status: plan only; nothing built. Evidence: `EVIDENCE-review-cut-or-continue.md` (same folder).

## What

From round 4, a round needs `--earned-by`. Once a finding kind comes back, the script wants
`--cut "<what was removed or replaced>"`. But the host writes that text and grades its own cut, so
a patch can pass as a cut. This plan decides who notices that, and when. The owner may be asked to
decide, or not at all.

## Why

- On the 0.36 move-prep gate (branch `fix/move-prep-036`), the lastmod scan's kind earned rounds
  4 to 7. The `--cut` texts at rounds 5, 6 and 7 were patches (each changed one regex rule). The
  real cut was turning the scan into a warning; its manager session chose it after round 7, and it
  was reviewed in round 8. Rounds 6 and 7 cost 86,430 Codex tokens.
- In the cost log, from 2026-11-03 to 2026-11-17, 82 gates had a kind come back after a round
  that carried a `--cut`. From that round on they ran 204 rounds and logged 18.1M tokens, 6.3% of
  the 286M logged in those days (45 seat runs logged no tokens). The rounds after that first
  return are the most any change can save: 122 rounds, 10.7M tokens. In 31 of the 82, the round of
  the return was the last.
- The script can't tell a cut from a patch by counting lines. The lastmod cut added 33 lines and
  removed 25; the patches before it changed 5 or 6 lines each.

## The options

| | Who notices | When | Owner asked (14 days) | Most it can save (14 days) |
|---|---|---|---|---|
| 1 | the owner | first return after a cut | 82 times, about 6 a day | 122 rounds, 10.7M tokens |
| 2 | the owner | second return | 45 times, about 3 a day | 61 rounds, 5.4M tokens |
| 3 | the next round's reviewer | in the round that reviews the cut | no new question | as option 1, if the verdicts hold |

**What each leaves out.** Options 1 and 2 ask the owner about code logic, which the owner does not
judge. The only part the owner can answer in plain words is the scope part: take it out, make it a
warning, or keep fixing. And "keep fixing" is a bet on code. In 31 of option 1's 82 asks, the next
round would have ended the gate anyway. Option 2 comes one round late for the lastmod gate: it
saves round 7, not rounds 6 and 7. Option 3 trusts a model's verdict. It is wrong sometimes, both
ways, and a host can still rename a kind to dodge the check (the script already shows renames).

## Recommendation: option 3, the owner's 2026-10-22 rule unchanged

A round that carries `--cut` already reviews the fix that claims to be a cut. Ask its seats one
more question in that same round. No extra call and no question to the owner.

1. `independent_review.sh`: when `--cut` is given, the brief gets a labelled block holding the
   kinds, the `--cut` text, the rule sentence ("take the feature out, or replace it by a strict
   rule…; refusing the one input the last BUG used is a patch") and one demand: a line
   `CUT-CHECK: CUT` or `CUT-CHECK: PATCH — <why>`, judged on the diff, not on the claim.
2. The script prints each seat's verdict in its closing lines and in the running-total line the
   owner reads. It also logs the verdict in a new cost-log column 18, `cut_check`, written `-` where
   no verdict was given. A missing or garbled verdict prints "no cut verdict" and never fails the
   review: bookkeeping never fails a review.
3. `SKILL.md` step 6, beside "Cut, don't patch": a PATCH verdict is an earning RISK on the fix.
   Before the next round, the host either makes a real cut or refutes the verdict with evidence in
   the trail. A real cut is one of three, in plain words: take it out; make it a warning, or a
   report of what it could not read; or accept one named form and refuse the rest. If that cut
   changes what the change does for its Users (a stop becomes a warning, a check goes), it is the
   change of scope the step already sends to the owner. No new kind of question.
4. Nothing else changes. "Don't ask the owner whether to run the next round" stays, and the
   decision past round 8 stays.

**The probe (run once, 2026-11-17, Codex at medium, 38,597 tokens).** Seven real fixes, hand-labelled
before the run: the lastmod fixes of rounds 5, 6 and 7, two from the Antigravity test tool's heredoc
chain, the lastmod warning, and the ship.sh comment-scanner cut. Codex agreed with all seven labels.
Only two of the seven were cuts, so a judge that always says PATCH would score 5 of 7. The probe does
not yet show how often it calls a real cut a patch. Test T1 settles that before anything is built.

## Scenarios (real gates)

- **S1, lastmod (`fix/move-prep-036`).** Given round 5 reviews the fix "dropped the line-start
  regex-literal case" and finds the regex kind again, when its seat answers the cut question, then
  it says PATCH (probe case D did). The host must cut before round 6, so the warning could come at
  round 6 instead of round 8, and rounds 6 and 7 would not run.
- **S2, a real cut (ship.sh comment scanner, `5328e7d3`).** Given the fix deletes the scanner and
  refuses any second `site:` line, then the seat says CUT (probe case G did), and nothing changes.
- **S3, a scope cut (`plan/live-analytics-check`).** At round 6 the owner cut the build proof
  on 2026-11-09, and the gate ended at round 7. The existing scope question already works;
  option 3 keeps that path.
- **S4, a long chain (`fix/move-analytics-gap-035`).** Twelve rounds and 382,952 tokens. From round
  5 to round 12 each `--cut` narrowed what one config reader reads. T1 measures whether round 5's
  verdict would have said PATCH.
- **S5, a wrong verdict.** Given a seat calls a real cut a patch, the host refutes it in the trail
  with the diff lines that remove or refuse, like any other RISK, and the next round runs.

## How it is tested

- **T1, backtest, before any build (go/no-go).** Hand-label at least 20 cut rounds from this repo's
  own gates in the cost log, at least 6 of them real cuts, with each label written before the run.
  Run step 1's question on each one. Build only if no real cut is called PATCH more than once and
  at least 80% of the patches are called PATCH. Otherwise drop option 3, and the owner chooses
  between options 1 and 2.
- **T2, through the real entry point.** In `test_round_checks.sh`, run `independent_review.sh
  --round 5 --earned-by k --cut "…"` with a stub seat. Check that the brief holds the cut block,
  that each verdict form is printed and logged in column 18, and that a missing verdict prints "no
  cut verdict" with exit 0. A run without `--cut` gets no block.
- **T3.** `check_prompt_sync.sh` and `make check` pass.
- **After two weeks,** compare rounds after the first return per gate with this baseline (122
  rounds over 82 gates, about 1.5 per gate), from the cost log.

## Questions for the owner (through the manager)

1. **Your 2026-10-22 rule says: don't ask you whether to run another round. When the same problem
   comes back after a fix the session called a cut, should it stop and ask you anyway?**
   - (a) **No, keep the rule** (recommended). The next round's reviewer says whether the fix was a
     real cut, and a "patch" verdict must be answered by a real cut. You are asked only when that
     cut changes what Users get, as now. New questions: none. Saving: up to 10.7M tokens in 14 days,
     if test T1 passes.
   - (b) Yes, the first time it comes back. About 6 questions a day, 31 in 82 of them needless.
     Saving: up to 10.7M tokens.
   - (c) Yes, the second time. About 3 questions a day. Saving: up to 5.4M tokens.
2. **When the real cut turns a stop into a warning, or drops a check, who decides?**
   - (a) You, as the skill says now. How often this comes up has not been counted.
   - (b) The session's manager may decide and tell you in the PR, as on the lastmod gate.
   - (c) The session decides and says so in the PR's first lines.
