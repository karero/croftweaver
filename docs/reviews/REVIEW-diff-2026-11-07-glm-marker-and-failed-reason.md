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

Gate total, reviewer seat runs: 346,796 tokens (the script's line, fresh-eyes included).

## Round 1 findings

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| A1 | BUG | Codex (melious RISK) | A summary after the second marker that starts like a finding (`- Totals: 1 BUG, 1 RISK`) makes that marker usable; both real findings are dropped | Not fixed: the plan names it (section 1) and T4 pins it KNOWN WRONG. It is not new: today's code does the same. The strict rule is the review check's own grep, which accepts that summary as well |
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

## State at the end

No BUG that the change introduced is open. A1 and B2 are old defects the plan names as "still wrong
after the fix"; they stay open and need an owner's call (a BUGLOG row, or a fix in a later change).
Round 2 was the verify round of fixes that are tests and comments, plus one grep: no further round.
