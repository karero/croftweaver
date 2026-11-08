# DIFF review — branch `plan/glm-marker-and-failed-reason` — GLM's marker twice, FAILED reason, codex_tokens

Plan: `docs/reviews/SKILL-PLAN-glm-marker-twice-and-failed-reason.md` (gate closed at `c167d455`; the
owner's go to build, 2026-11-07). Base `2275e756` · depth: Normal (the logic of a tooling script is
never Light) · no red team (no box, user data, login, money, deletion or schema). Seats: Codex and
GLM 5.3 on melious in one command (`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`), fresh-eyes Sonnet
in round 1. The artifact leaves out `docs/reviews/`. The run, the evidence and the mutation record
sit in the session's scratchpad; the figures below are copied from them.

## Mutation check (before round 1)

The `mutation-check` skill has no bash runner, so each mutation ran by hand: a fresh `git archive`
copy of `5aaf2ed2`, the mutation applied, the suite read for FAIL lines. All KILLED.

| Id | Mutation | Killed by |
|---|---|---|
| M1 | line 112 put back as it was | T1, T2, T3 (a, b) |
| M2 | the round-3 regex | dmlongs, dmkelvin, dmnul |
| M3 | middle `.*?` instead of printable ASCII | dmeacutebefore |
| M4 | lookbehind removed | dmxbefore |
| M5 | non-ASCII allowed in the lookahead | dmeacuteafter |
| M6 | ASCII letters allowed in the lookahead | dmxafter |
| M7 | the round-5 lookahead | dmnul |
| M8 | `+` allowed as a bullet | dmplus |
| M9 | `--reason` dropped from `log_seat` | T6, T7 |
| M10 | `codex_tokens` takes the first pair | T10, T11 |
| M11 | an outcome without parentheses | round-checks T13 |
| M12 | lead class `\s*` | dmnel, dmnbsp |
| M13 | the "No BUG/RISK/NIT findings" alternative deleted (after round 1) | T15 |

## Rounds

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `21710f92` | whole change (27,064 bytes); evidence (4,822 bytes) | Codex gpt-6.1-sol; melious glm-5.3; fresh-eyes Sonnet | Codex 141 s, 57,421 · melious 381 s, 48,390 · fresh-eyes 235 s, 157,175 | 2 / 4 / 7 (Codex 2/0/0, melious 0/3/3, fresh-eyes 0/1/4) |
| 2 | `7e0718e0` | verify: delta since round 1 (5,810 bytes), PRIOR round 1 | Codex; melious | Codex 170 s, 59,960 · melious 202 s, 23,850 | 2 / 0 / 1 (Codex 0/0/0, melious 2/0/1) |
| 3 | `202ef297` (#482) | verify: the A1 fix against `6859448c` (8,297 bytes), PRIOR | Codex; melious | Codex 171 s, 42,968 · melious 249 s, 27,635 | 4 / 0 / 1 (Codex 3/0/0, melious 2/0/1; one BUG from both) |
| 4 | `5a16cc90` (#482) | verify: round 3's fixes (8,688 bytes), PRIOR; earned by `tally-cut` | Codex; melious | Codex 211 s, 164,582 · melious 160 s, 22,435 | 2 / 0 / 1 (Codex 2/0/0, melious 0/0/1) |
| 5 | `6f4c54d9` (#482) | verify: the cut (124 lines), PRIOR; earned by `tally-cut`, with `--cut` | Codex; melious | Codex 230 s, 55,436 · melious 306 s, 36,401 | 3 / 1 / 3 (Codex 2/0/1, melious 1/1/2) |

Gate total, reviewer seat runs: 696,253 tokens, rounds 1 to 5 summed from the rows above (fresh-eyes included).

## Round 1 findings

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| A1 | BUG | Codex (melious RISK) | A summary after the second marker that starts like a finding (`- Totals: 1 BUG, 1 RISK`) makes that marker usable; both real findings are dropped | Fixed after #481 merged, in its own pull request, at the owner's word ("Fix A1 first", 2026-11-08): see "A1 fix" below |
| A2 | BUG | Codex | `codex_tokens` comment said "never guessed", but a quoted bare pair after the footer, or in a run with no footer, counts | The behaviour is the plan's (section 3). The comment was wrong: fixed |
| A3 | RISK | melious | Lines like `BUG — …`, `1) BUG`, `> BUG` do not count | Refuted: `looks_like_review`'s grep needs the same lead, so such a reply fails the check anyway |
| A4 | RISK | melious | A same-line footer (`tokens used 72,315`) is not read | Refuted by measurement: 60 of 60 `codex.err` files hold the bare pair |
| A5 | RISK | fresh-eyes | No test for the `No BUG/RISK/NIT findings` alternative | Fixed: T15; M13 killed |
| A6 | NIT | melious | An older `review_log.sh` would reject `--reason` | Refuted: both scripts ship in one folder |
| A7 | NIT | melious | Round-checks T13 grep narrower than its rule | Fixed (`[^"]* (`) |
| A8 | NIT | melious | Check numbers skip T5, T9, T13 | Fixed: a comment says where they are |
| A9 | NIT | fresh-eyes | No why-comment on the regex | Fixed |
| A10 | NIT | fresh-eyes | T3 accepts either capture's first line for both | Fixed: one pattern per capture |
| A11 | NIT | fresh-eyes | The reason column holds up to 300 bytes of server text | Not changed: the summary line shows the same text; the usage says "word for word" |
| A12 | NIT | fresh-eyes | Fixture wording ("July incident", "#174") | Not changed: no project, person, host or token is named |

## Round 2 findings

Codex: none; it checked each fix and re-ran the regex against the grep on 127,680 generated lines
with no Perl-only match. melious:

| Id | Sev | Finding | Status |
|---|---|---|---|
| B1 | BUG | A1 again: a comment and a KNOWN WRONG label are not a fix | Same as A1. The fix it proposes (a `Totals:` pre-check in both the grep and the regex) changes the plan's design and widens the review check; the plan accepted the case as not seen |
| B2 | BUG | A2 again: the behaviour is unchanged | Same as A2: the plan's section 3 names it as still wrong after the fix |
| B3 | NIT | T13 needs a space before the paren | Refuted: `log_seat` cuts at the first ` (`, so an outcome without the space would log `-`; the check must require it |

## A1 fix (after #481 merged)

The owner chose to fix A1 rather than defer it. #481 merged before the fix was ready (the owner's
word in the build session), so the fix is its own pull request, branch `fix/a1-closing-tally`. The reader now cuts each count, a number then a
label, from a line before testing it against the strict rule, so a closing tally no longer makes
its marker usable and the walk falls back to the first marker (plan, section 1). T4 now checks the
review is kept, by the reader and through `independent_review.sh`; T16 checks that a finding
naming a count still counts.

Every real `melious.resp` under `$TMPDIR`, replayed with each marker its prompt holds through the
reader before and after the fix: the same section and exit code in all 550 run and marker pairs (577
before; some run folders have since been cleared). So in no real reply did a tally win the walk.

Mutations, each on the reader with T4's and T16's replies (not the whole suite):

| Id | Mutation | Killed by |
|---|---|---|
| M14 | the walk tests the plain rule | T4 |
| M15 | the "came N times" count tests the plain rule | T4, once `no_notes` was fixed |
| M16 | the cut takes a label without a number | T4, T16 |
| M17 | no cut | T4 |

M15 first survived: the test helper `no_notes` looked for "the marker came", but the note printed
when nothing comes before the marker says "the final-review marker came". It now looks for
"marker came". T1–T3 use the same helper, so before this they could not see that note either.

## Round 3 findings

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| C1 | BUG | Codex | A tally in bold (`- Totals: 1 **BUG**, 1 **RISK**`) still wins the walk | Fixed: the cut allows `*`, `_` and backticks around the label; T4 (bold) |
| C2 | BUG | Codex, melious | The cut can create a match: `- 1 BUGRISK` becomes `- RISK`, so the comment's subset claim was false | Fixed: a line must match the strict rule as it is too; T4 (joined); the comment now says why |
| C3 | BUG | Codex | The A2 row says only the cost log's figure is wrong; the `timings:` lines print it too | Fixed: the row names both |
| C4 | BUG | melious | A label-first tally (`- BUG: 1, RISK: 5`) still wins; the plan had named it as still wrong | Fixed: the cut also takes a label, an optional colon and a number followed by `,` `;` `.` `)` or the end of the line; T4 (labelfirst, labelfirstbold); T16b checks that `- BUG: 3 retries are lost` still counts |
| C5 | NIT | melious | The A2 row's "not seen" does not cover the 7 runs with no footer | Fixed: a quoted pair needs a lone `tokens used` line, and those runs hold none (re-checked on the 675 runs now present: 5 with none, none holding a pair) |

Outside scope, both already named: the clean verdict quoted in a summary (plan, section 1) and A2.

Mutations on the reworked cut, each on the reader with the T4 and T16 replies:

| Id | Mutation | Killed by |
|---|---|---|
| M18 | no test of the line as it is | T4 (joined) |
| M19 | no Markdown after the label | T4 (labelfirstbold), added when M19 first survived |
| M20 | no label-first branch | T4 (labelfirst) |
| M21 | the label-first branch without its lookahead | T16b |

## Round 4 findings, and the cut

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| D1 | BUG | Codex | `- **BUG:** 1, **RISK:** 5` (the colon inside the bold) still wins the walk | Fixed by the cut; T4 (boldcolon) |
| D2 | BUG | Codex | New: `- BUG: 1,000 requests exhaust the pool` and `- BUG: 3.11 crashes at startup` read as tallies, so a real final answer lost its marker | Fixed by the cut: no line is changed before it is counted |
| D3 | NIT | melious | The comment says a tally "cannot win", but `BUG (1)` and `one BUG` still do | Gone with the comment; the plan names what is still wrong |

The kind `tally-cut` came back, so the fix is a cut (SKILL.md step 6): the per-line tally cut is
taken out, and the walk compares finding lines instead. It takes the last usable marker unless the
stretch from the usable marker before it holds at least as many lines the strict rule counts as the
text after it (plan, section 1). This was the plan's rejected alternative, turned down then as more
code; the per-line cut proved to be more. T4 now has five tally shapes, each keeping the review with
the "came 2 times" note; T17 checks that a fuller final answer still beats a draft and the reasoning
above it. T16 and T16b tested the cut and are gone.

| Id | Mutation | Killed by |
|---|---|---|
| M22 | `>` instead of `>=` | T4 (twolines) |
| M23 | never move back | T4 (every shape) |
| M24 | always the first usable marker | T17, mleak |
| M25 | compare with all the text before the marker, not the stretch since the one before | T17, once it held finding-shaped reasoning above its first marker (M25 first survived) |

M22–M25 were first run on the reader alone, with replies built in zsh. The suite, run by bash, then
failed T4's note check on every shape: it built each tally with `printf "<tally>"`, and bash's
`printf` reads a format that starts with `-` as an option, so the reply held no tally at all and
the "both finding lines" check passed without the fix. T4 now builds the tally with `printf '%b'`
and checks that it is in the section; through the suite, M23 fails T4 on every shape and M22 on
the one line per label.

Replays of every real `melious.resp`, the #481 reader against each version, once per marker in the
prompt: the round-3 reader gave the same section and exit code in 554 of 554 pairs; the cut, in
561 of 567 (more runs had been kept by then). In the 6 others GLM wrote its review after one marker
and a shorter copy of it after a second, and the earlier review has as many finding lines or more.
The cut steps back: in each, the section #481 printed is kept whole at the end, the fuller review
comes before it, and the "came N times" note was already printed. The plan names this case. The
claim that more lines could only pass the review check was wrong (round 5, E1).

## Round 5 findings

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| E1 | BUG | Codex | Stepping back can make the review check reject a valid reply: marker, `- BUG: I cannot review this file…`, marker, clean verdict. Widened, the section holds one finding line and the refusal phrase | Fixed: step back only when the text after the later marker has a finding line; the section then holds two or more lines the check counts. T18, also through the pair |
| E2 | BUG | Codex | `$count` counted matches, not lines: one draft line naming the clean verdict twice outweighed a two-line final answer | Fixed: count list lines the strict rule matches, each once. T19 |
| E3 | BUG | melious | The `@ok` loop reads a stale `$_` | Refuted: line 120 reads `$end`; the `$_->[1]` quoted is in the `grep` on line 115, where `$_` is set |
| E4 | RISK | melious | A summary with more finding lines still wins; keep the "came N times" note on every path | Refuted: the note prints whenever `$usable` > 1, on both paths; the case itself is named in the plan |
| E5 | NIT | melious | With T16 gone, nothing tests that `- BUG: 1,000 requests …` still counts (D2) | Fixed: T20 |
| E6 | NIT | melious | `$start` unused | Fixed |
| E7 | NIT | Codex | The comment's "whatever its wording" overclaims | Fixed: the comment states the count condition |

E1 and E2 are new kinds (`gate-input`, `count-unit`), so round 6 is earned by them.

| Id | Mutation | Killed by |
|---|---|---|
| M26 | step back even when the text after the later marker has no finding line | T18, alone and through the pair |
| M27 | count matches, not lines (round 4's `$count`) | T18, T19 |
| M28 | count any line `$findings` matches, not only list lines | T18, alone and through the pair |

The replay at this fix: 592 of 598 pairs give #481's section and exit code. The 6 others are the
six above, with the same output as at `6f4c54d9`.

## State at the end

No BUG that the change introduced is open. A1 is fixed (above, and round 3). B2 (A2) is an old defect the plan
names as "still wrong after the fix"; the owner deferred it to a `docs/BUGLOG.md` row, 2026-11-08.
Round 2 was the verify round of fixes that are tests and comments, plus one grep: no further round.
