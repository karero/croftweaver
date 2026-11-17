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
- In the cost log, 81 gates that started from 2026-11-03 to 2026-11-17 had a kind come back after
  a round that carried a `--cut`. From that round on they ran 203 rounds and logged 18.0M tokens,
  7.0% of the 258M those days' gates logged (45 seat runs logged no tokens). The rounds after that
  first return are the most any change can save: 122 rounds, 10.7M tokens. In 30 of the 81, the
  round of the return was the last.
- The script can't tell a cut from a patch by counting lines. The lastmod cut added 33 lines and
  removed 25; the patches before it changed 5 or 6 lines each.

## The options

| | Who notices | When | Owner asked (14 days) | Most it can save (14 days) |
|---|---|---|---|---|
| 1 | the owner | first return after a cut | 81 times, about 6 a day | 122 rounds, 10.7M tokens |
| 2 | the owner | second return | 45 times, about 3 a day | 61 rounds, 5.4M tokens |
| 3 | the next round's reviewer | in the round that reviews the cut | no new question | as option 1, if the verdicts hold |

**What each leaves out.** Options 1 and 2 ask the owner about code logic, which the owner does not
judge. The only part the owner can answer in plain words is the scope part: take it out, make it a
warning, or keep fixing. And "keep fixing" is a bet on code. In 30 of option 1's 81 asks, the next
round would have ended the gate anyway. Option 2 comes one round late for the lastmod gate: it
saves round 7, not rounds 6 and 7. Option 3 trusts a model's verdict. It is wrong sometimes, both
ways, and a host can still rename a kind to dodge the check (the script already shows renames).

## Recommendation: option 3, the owner's 2026-10-22 rule unchanged

A round that carries `--cut` already reviews the fix that claims to be a cut. Ask its seats one
more question in that same round. No extra call and no question to the owner.

1. `independent_review.sh`: when `--cut` is given, the brief gets a labelled block holding the
   kinds, the `--cut` text, the rule sentence ("take the feature out, or replace it by a strict
   rule…; refusing the one input the last BUG used is a patch") and one demand: a line
   `CUT-CHECK: CUT` or `CUT-CHECK: PATCH — <why>`, judged on the change, not on the claim. A DIFF
   round already sends the change. A PLAN round sends only the current plan, and 44 of the 81
   gates were plans, so for `--plan` the block also holds the plan's own diff since the previous
   round. The logged head can't give that diff, because the plan may hold edits not yet committed.
   So each `--plan --round N` run keeps a copy of the plan it sent, as `plans/<gate id>/round-N.md`
   beside the cost log, and the block shows the diff from the copy of the highest round below N to
   the file being sent. Where there is no copy, the
   block says "no diff" and the verdict is printed as judged on text alone.
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
not yet show how often it calls a real cut a patch. Tests T1a and T1b settle that.

## Scenarios (real gates)

- **S1, lastmod (`fix/move-prep-036`).** Given round 5 reviews the fix "dropped the line-start
  regex-literal case" and finds the regex kind again, when its seat answers the cut question, then
  it says PATCH (probe case D did; that run was the probe's brief, not the built one). The host must cut before round 6, so the warning could come at
  round 6 instead of round 8, and rounds 6 and 7 would not run.
- **S2, a real cut (ship.sh comment scanner, `5328e7d3`).** Given the fix deletes the scanner and
  checks no address when it finds two quoted `site:` http(s) addresses, then the seat says CUT (probe case G did), and nothing changes.
- **S3, a scope cut (`plan/live-analytics-check`).** At round 6 the owner cut the build proof
  on 2026-11-09, and the gate ended at round 7. The existing scope question already works;
  option 3 keeps that path.
- **S4, a long chain (`fix/move-analytics-gap-035`).** Twelve rounds, 704,651 tokens, 382,952 of
  them from round 6 on. From round 5 to round 12 each `--cut` narrowed what one config reader reads. T1a measures whether round 5's
  verdict would have said PATCH.
- **S5, a wrong verdict.** Given a seat calls a real cut a patch, the host refutes it in the trail
  with the diff lines that remove or refuse, like any other RISK. Another round runs
  only if it is owed or earned for another reason; a refuted RISK earns none.

## How it is tested

- **T1a, backtest, before any build (go/no-go).** Hand-label at least 20 cut rounds from this
  repo's own gates in the cost log, at least 6 of them real cuts and at least 6 from PLAN gates,
  each label written to a file before the run. Send each one as step 1 would: the block's exact
  text (written into the T1a file first) and the change a round sends (the delta diff; for a plan,
  the plan and its diff, rebuilt from git; a case whose plan text git cannot rebuild is replaced).
  Build only if at most one of the real cuts, in all, is called PATCH, and at least 80% of the
  patches are called PATCH. A missing or garbled verdict counts as a wrong one. Otherwise drop
  option 3, and the owner chooses between options 1 and 2. Cost: about 20 Codex calls, near 100k
  tokens, going by the probe's 38,597 for 7 cases.
- **T1b, through the built script, before merge.** The block alone is not the whole request a
  seat gets in a round. Once steps 1 and 2 are built, send 6 of T1a's cases (3 cuts, 3 patches, at
  least 2 from plans) through `independent_review.sh` itself, in a scratch worktree with
  `REVIEW_LOG` set to a scratch log, and with each round's own options (`--round`, `--earned-by`,
  `--cut`, `--verify` with the answered finding, `--plan` for a plan, its earlier round run first
  so the copy exists). It runs on the seats and settings the script and the seat rules choose on
  the day, and it keeps each command and the script's raw output folder. Pass only if every seat
  gives a valid verdict in every case, no real cut is called PATCH, and at most one patch is called
  CUT; a missing or garbled verdict fails it. If it fails, the same choice as T1a goes to the
  owner. It does not cover a later change of seat, model or effort; the verdicts logged in column
  18 and the two-week check cover what runs after that. Cost: about 6 rounds, near 300k tokens.
- **T2, through the real entry point.** In `test_round_checks.sh`, run `independent_review.sh
  --round 5 --earned-by k --cut "…"` with a stub seat. Check that the brief holds the cut block,
  and that the block's text is the one T1a used. For a `--plan` gate: commit the plan, edit it
  without committing, run round 4, edit it again, run round 5, and check that round 5's block shows
  only the second edit (a diff against the logged head would show both). Check that each verdict
  form is printed and logged in column 18, and that a missing verdict prints "no
  cut verdict" with exit 0. A run without `--cut` gets no block.
- **T3.** `check_prompt_sync.sh` and `make check` pass.
- **After two weeks,** compare all gates that reach round 4, not only those with a return: rounds
  past round 3 per gate and their tokens (baseline: 234 gates, 574 rounds past round 3, 46.0M
  tokens). Apart from that, count how many have a return after a cut (baseline: 81 of 234).

## Questions for the owner (through the manager)

1. **Your 2026-10-22 rule says: don't ask you whether to run another round. When the same problem
   comes back after a fix the session called a cut, should it stop and ask you anyway?**
   - (a) **No, keep the rule** (recommended). The next round's reviewer says whether the fix was a
     real cut, and a "patch" verdict must be answered by a real cut. You are asked only when that
     cut changes what Users get, as now. New questions: none. Saving: up to 10.7M tokens in 14 days,
     if tests T1a and T1b pass.
   - (b) Yes, the first time it comes back. About 6 questions a day, 30 in 81 of them needless.
     Saving: up to 10.7M tokens.
   - (c) Yes, the second time. About 3 questions a day. Saving: up to 5.4M tokens.
2. **When the real cut turns a stop into a warning, or drops a check, who decides?**
   - (a) You, as the skill says now. How often this comes up has not been counted.
   - (b) The session's manager may decide and tell you in the PR, as on the lastmod gate.
   - (c) The session decides and says so in the PR's first lines.
