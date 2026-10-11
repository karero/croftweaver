# Why PR #230 needed 16 review rounds

PR #230 (`facts-check`) went through 16 rounds of independent review on 2026-10-09. Rounds 2 to 16
ran from about 11:40 to 20:50 UTC; the owner merged after round 15 with the gap stated, and round
16's findings were fixed in #239. This page explains where the rounds came from and what would have
saved most of them. The numbers come from the trail, `docs/reviews/REVIEW-diff-2026-10-09-pr230.md`.

## The numbers

92 findings, 34 of them confirmed BUGs. Where the 34 came from:

| Origin | BUGs | Findings |
|---|---|---|
| The first full read by Codex (round 2) | 8 | F7 to F14 |
| Caused, or left half done, by the previous round's fix | 15 | F16, F17, F18, F31, F32, F33, F45, F46, F51, F56, F59, F60, F68, F78, F85 |
| Older code of the same PR, found late | 11 | F20, F21, F30, F34, F43, F52, F57, F58, F83, F89, F90 |

Only 8 of the 34 came out of a read of the whole change. The other 26 came one or two per round.
Meanwhile the script grew from 1,183 to 1,471 lines and the tests from 50 to 102.

## The loop that kept the rounds going

1. A fix lands, so a verification round is owed.
2. The reviewer reads the fix and the code around it. It finds a hole in the fix, or an older
   bug nearby.
3. That is fixed, so the next round is owed.

Every round from 4 to 15 followed from one of these two sources, except round 14, which reviewed
the redesigned robots.txt matcher. They feed each other: each extra round looks at a little more of
the old code, and each fix adds new code to look at. The loop ends only when both run dry. One
Codex pass over 2,150 lines (412 s) was not enough to exhaust code that reads HTML, addresses and
robots.txt from the open web.

## Three spots: 27 of the 34 BUGs, and 24 of the 26 late ones

| Code | BUGs | What happened |
|---|---|---|
| Address checks | 11 | A copy of urllib's rules written by hand. Differences from the real thing (which `#` ends the address, where spaces are stripped, an empty host, letters beyond ASCII) surfaced one round at a time. |
| robots.txt | 10, plus most RISKs and NITs from round 10 on | Python's parser misreads some rules. A warning instead of a fix needed a file scanner, and the scanner had its own edge cases (rounds 11 to 13). The matcher that replaced both (round 13) needed three more fixes (F78, F83, F89). |
| Numbers split across tags | 6, plus 2 RISKs | Whether a tag boundary shows a gap depends on CSS, which the script cannot see. Each new regex rule moved the line; in round 7 a fix broke a number that read correctly before (F45). |

All three are code that guesses at, or copies, behaviour defined somewhere else. A reviewer can
usually build one more input where the guess and the real thing differ.

## Why nothing stopped the loop

- **A wrong output counted as a BUG**, however unlikely the input: `http://@/`,
  `Q2</span><span>-5`, `#section 2#end`, a robots.txt split by bare CR, 16 KB of blank lines.
- **The skill's own brakes were applied late.** The convergence check (step 7) says to stop
  patching when a fix re-breaks earlier work; F45 did that in round 7. Past round 8, further
  rounds are the owner's decision; until round 15 each verdict set "open until round N+1", and
  only then did the owner decide to merge with the gap stated.
- **Fixes were tested against the reported input, not the class.** One `#` was tested and two
  broke (F51); two pieces of a number were tested and three broke (F45).
- **Friction:** GLM timeouts and Ollama quotas left several rounds with one reviewer, two
  sessions ran round 8 in parallel, and the refuted `actions/*@v7` claim came back three times
  (F3, F15, F19).

## What worked

The robots.txt matcher in round 13 (`9898b24`) was built the way that breaks the loop: tests
first, from RFC 9309 and Google's documented tables; 24 mutants, 23 caught and one equivalent; a
fuzz of 400,000 cases against a regex reference; a comparison with Python 3.13 on nine real
files. It removed the code that rounds 10 to 13 kept finding holes in, and its first review
(round 14) found no wrong allow or deny decision in the documented cases.

## What round 16 showed

Round 16 ran after the merge decision, on about 40 lines. It found F90: a page whose address has
letters beyond ASCII (`/über-uns`, as many CMS sitemaps write it) was never read, because
`http.client` refuses such a character raw. The flaw was in the code from the start. Fifteen rounds
had chased inputs such as `http://@/` and missed one that a German site serves every day: the
argument for items 1 and 4 below.

## What to do next time

1. **Read each risky component on its own before the delta rounds start**: the HTML reader,
   number matching, addresses, robots.txt, sitemaps. Ask "which inputs break this?" for each,
   starting with the inputs real sites serve.
2. **Test the class before pushing a fix.** Write five to ten variants of the reported input. Where
   code copies another component's rules, compare it with that component (real requests, a
   fuzz against a reference), as the round 8 address tests and the round 13 matcher did.
3. **Prefer the standard library to a guess.** Where a guess cannot be avoided, write the rule
   down, pin it with a table of inputs, and list what it does not handle as a known limit.
4. **Grade by a realistic input.** A BUG needs an input a real site could serve, or a crash, or a
   page read against robots.txt. An input only an adversary would build is a RISK at most.
5. **Apply the brakes the skill already has**: stop patching when a fix re-breaks earlier work,
   and from round 9 on, take the open items to the owner as one decision.
6. **Run every round with Codex**, and only one session at a time per gate.

Items 1, 4 and 5 are proposals for `skills/independent-review/SKILL.md`; nothing there has
changed yet.
