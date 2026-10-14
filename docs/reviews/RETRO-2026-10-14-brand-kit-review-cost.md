# Why the brand-kit review took 31 hours, and what was changed because of it

PR #283 (`website-brand-kit`) went through a High-depth review gate. It ran from 2026-10-12 18:55
to 2026-10-14 01:30 CEST for its first nine rounds, about 31 hours. Two more rounds, a final full
read and a wording pass followed, and the PR merged on 2026-10-14 at 14:28 CEST. The reviewers and
the fixers used about 40 million tokens.

This page answers the maintainer's question, asked after round 9: why did it take so long? It also
records what a check of every earlier long gate showed, and what was changed in the review skill
(PR #288). The numbers come from the gate's trail,
`docs/reviews/REVIEW-diff-2026-10-12-feat-website-brand-kit-4e83f4a.md`, from git, and from the
local cost log of the review script.

## The numbers

| Round | Finished (CEST) | Findings after merging duplicates |
|---|---|---|
| 1 | 10-12 20:46 | 102 |
| 2 | 10-12 23:00 | 102 |
| 3 | 10-13 02:00 | about 105 |
| 4 | 10-13 06:50 | 93 |
| 5 | 10-13 11:09 | 72 |
| 6 | 10-13 15:18 | 58 |
| 7 | 10-13 18:46 | 49 |
| 8 | 10-13 22:07 | 39 |
| 9 | 10-14 01:30 | 45 |
| 10 (lean: the changed code only) | 10-14 morning | 1 ordinary BUG, a few NITs |
| 11 (Codex alone, on round 10's fix) | 10-14 | clean |

- **Time.** Round 1 took under 2 hours and round 2 a little over 2; rounds 3 to 9 took 3 to 5 hours
  each. A round was the seats (9 to 18 seat runs), consolidation, the fixes, the whole test suite,
  and the record.
- **Tokens, rounds 1 to 9.** Reviewer seats about 21.5 million, of which fresh-eyes about 11 million,
  Codex about 7 million and GLM about 2.7 million. Fixers about 16 million. Rounds 10 and 11, their
  fixers, the final full read and the wording pass added about 2 million.
- **What the gate caught that matters.** A crash on a crafted zip; a 228 KB file installed as a
  20 MB favicon, reported as done; a hang while stopping the site's tests; a stylesheet edit written
  to the wrong place; an install that said "Done" with a value the site did not read. All of these
  would have reached users.

## Why it took so long

The causes, most important first. Each is the author's judgment, laid on the measured numbers above.

1. **One PR read outside files of five kinds and edited four of the owner's own files.** An SVG
   check, a zip reader, a Markdown palette reader, a stylesheet scanner and a line editor for a
   TypeScript config: each is a parser fed untrusted input. At High depth every round had three
   seats per part, one of them a sub-agent that fuzzes with hundreds of thousands of inputs. A
   fuzzer run against five parsers never comes back empty, and the gate stops only on a round
   with no BUG.
2. **Fixes made the next round's findings.** At least five fixes from rounds 3 to 7 added a
   mechanism that the next round found broken, and each was taken out again: a dropped size guard
   (a crash), an HTML unescape (a crash and a stall), a terminal setting (left changed), a new way
   of folding blanks (ordinary pastes refused), and a sentence for one refusal. Round 8 alone has
   six findings marked as caused by round 7's fixes.
3. **One kind of finding kept coming back.** The tool's advice on which line of a reshaped
   `src/config.ts` to write, and where, drew BUGs in rounds 3 to 9, each time for another shape of
   file. The round-3 cuts held: a feature dropped, and a scanner replaced by a strict rule. Neither
   kind came back. The later rounds patched, and the patches did not hold, until the advice itself
   was cut in round 10.
4. **Open-ended promises in the code.** Docstrings said things like "no colour is lost without a
   word" and "every refusal can be followed". A reviewer can test each such promise with one more
   input, and every promise became a target.
5. **Plumbing, which about doubled each round.** The whole suite (about 1,070 tests on two Pythons)
   ran three or four times a round: once per fixer and once by the host. Under the machine's load,
   up to 667 from other sessions, one run took 15 to 40 minutes. From round 2 on every round sent all four
   parts (round 1: three) to all three seats, each part with its change since the last round: a part with a small change still
   cost a full set of seat runs, and the fresh-eyes seats read widely in the tree around it. On top
   came melious timeouts and three merges of a main that had moved 167 commits.
6. **One PR for everything.** About 7,500 lines of new code and tests at round 1, 32,000 by round 9.
   A kind of defect fixed in one reader was found again in the next.

## What the review skill already said

The skill had a rule that should have stopped this: step 7's "STOP patching when a verified fix
re-breaks something an earlier round fixed (even once)", on main since July 2026. In this gate its
trigger was met in every round from 2 to 8. The trail first wrote "stopped: not converging" at
round 8, the end of the round budget, and the maintainer then granted a round 9.

Two outlets in the same text let every round through. "Redesign" counted as complying when one part
inside the same PR was redesigned. And the round budget says "a chain of fixes that each expose the
next real defect is the gate working".

## A check of every earlier long gate

Before changing the skill, two checks were run on the first draft of the change.

**A replay.** Every gate with four rounds or more in `docs/reviews/` was read again: 45 gates, 303
rounds, 168 of them round 4 or later. For each late round the reader asked what earned it, and
what the proposed rules would have done to it.

| Gate | Rounds | Reviewer tokens | Rounds a severity bar would have saved |
|---|---|---|---|
| brand-kit DIFF, High | 9 (11 in the end) | 21.5M | 0 |
| brand-kit plan | 10 | 1.78M | 0 (1 if round 10 counts as citation-only) |
| PR #230 | 16 | 1.59M | 0 |
| PR #165 | 21 | 1.57M | 0 |
| PR #189 | 10 | 2.60M | 0 |
| Cloudflare check | 8 | 1.24M | 0 |
| PR #281 | 8 | 0.96M | 0 |
| mechanism claims | 16 | not recorded | 0 |
| PR #227 | 9 | 0.78M | 1, already saved by the old clean-round rule |
| mail-form sign-off | 5 | 0.49M | 1 |
| the other 35 gates | | | 0 |

What it showed:

- **The proposed severity bar would have saved 1 round of 303.** That bar would have made a BUG
  found only with hand-made input a NIT where the tool stops safely. On code, late rounds were
  earned by tracebacks, hangs, a wrong "Done", files changed and bypasses, not by safe stops. Under
  a looser reading it saves about 12 rounds, and that reading turns a check that wrongly passes
  hand-made input into a NIT. Read strictly, no real defect would have shipped; read loosely, at
  most one runbook BUG and one plan RISK would have. The per-round marks are in the replay's working
  notes, not in this repository, so these counts are the replay's word.
- **The old stop rule's trigger was met in 34 of the 45 gates,** usually by round 2 or 3. The rounds
  went on in about 30 of them.
- **17% of the late rounds were earned by findings about sentences,** mostly in the gates on the
  skill files themselves. On code gates, late rounds were earned by behaviour almost every time.
- **Cutting instead of patching might have saved 15 to 25 rounds** over the 45 gates. This is an
  estimate from the chains of same-kind BUGs, the least certain number here. In several gates the
  authors cut on their own, at about the point the rule would have forced.
- **Fresh-eyes was the largest single cost, and its late yield was low.** In the brand-kit gate,
  fresh-eyes alone found 34 BUGs: 9 in round 1, then 6, 5 and 4 in rounds 2 to 4, then 10 in rounds
  5 to 9, at about 1.2 million tokens a round.

**A design critique.** A sub-agent on the host's strongest model judged the first draft. It found
that the severity bar re-opened a filter the skill had rejected five days earlier: "the author who
wants rounds to stop is the wrong judge". It found that limiting fresh-eyes to changed parts would
skip almost nothing in this gate, because every part had a fix every round. And it found that rules
in prose had not been followed. The skill's SKILL.md had grown from 93 lines in July to 385, and the
draft added 50 more.

## What was changed (PR #288)

The maintainer chose to replace the first draft by checks in the review script and a shorter skill:

- **The script asks what earned each late round.** From round 4, `--earned-by <kinds>` names every
  kind of finding that earned the round. A kind that earned an earlier round too, with no cut since,
  is refused without `--cut "<what was removed or replaced>"`, where the cost log can tell. With the
  log off or unreadable, or with no record of the earlier round, the script warns and goes on. A cut is taking the feature out, or
  replacing it by a strict rule that accepts only the input it names. Refusing the one input the last
  BUG used is a patch.
- **The script prints a running cost line after every run.** It shows rounds, seat runs, tokens
  logged, the kinds and cuts per round, runs without a round number, and which gate a restart
  follows. It also says what it does not count: the fixers, the host, and fresh-eyes unless logged.
  From round 4 the host gives this line to the owner. With no log, there is no line.
- **Fresh-eyes at High depth runs in rounds 1 to 3.** The final full read still reads the whole.
- **A plan for more than about 2,000 lines of code, or for several readers of outside input,** names
  its components, and each is gated in its own PR.
- **SKILL.md came out shorter than before:** 376 lines against 385.

Left out: the severity bar, and moving the owner's decision from round 8 to round 5. The
`--earned-by` check can be satisfied dishonestly, for instance by naming another kind from the same
round. The script does not stop that; its cost line makes it visible to the owner.

## What this does not show

- That the gate finds the same real defects with fresh-eyes only in rounds 1 to 3. In this gate,
  14 of the 34 BUGs that fresh-eyes alone found came in rounds 4 to 9. They would have been left to
  the pair and the final full read.
- How many rounds the cut check saves. The estimate above is not a measurement.
- Whether a host names kinds honestly. The log keeps every kind and cut, and nothing checks them
  against the findings.

Judge the change by the cost log's rounds and tokens per gate over the next long gates:
`skills/independent-review/scripts/review_log.sh gate --id <gate>` gives one gate's line, and
`review_log.sh summary` compares depths and seats across all logged runs.

## Smaller lessons for the next skill of this kind

- Ship a smaller first version. Check and refuse in the tool, and leave edits of a developer's own
  files (a config, a script) to the assistant, with a checklist.
- Review each reader of outside input as soon as it is built, not the whole skill at once.
- Write no open-ended promise into a docstring that the code cannot keep for every input.
- Fixers run their own tests; the host runs the whole suite once a round.
