# Plan: round 2 refuses a gate whose fresh-eyes seat was never logged

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | written 2026-11-17 | this file |
| 2 | Plan review gate (Normal; no red team: it touches no server, user data, login, money, deletion or schema) | open | — |
| 3 | The change, in one pull request, with its DIFF gate | open | — |

## What and why

`SKILL.md`'s review depths owe a host fresh-eyes seat on top of the script's pair: at Normal in
round 1, and at High in rounds 1 to 3 (the "Review depth" table). The host runs it itself and logs
it with `review_log.sh add --seat fresh-eyes`; the script never sees it. Nothing checks that it
ran, so a host can forget it, as a plan review did on 2026-11-17: the seat was found missing only
after round 1's fixes, and was run late.

How often, from the cost log (`runs.tsv`, read 2026-11-17): from 1 to 17 November, 460 Normal
gates reached round 2, and 362 of them (79%) have no `fresh-eyes` line at round 1. The log cannot
say how many of those ran the seat and did not log it; either way, a seat that is not logged
cannot be told from one that did not run, and the gate's token total leaves it out. The seat name
is almost always exactly `fresh-eyes` (1,049 lines, against 19 lines across variants such as
`fresh-eyes-final-read`).

Prose rules like this one were met in 34 of 45 long gates before the round checks existed
(`test_round_checks.sh`, header); the script refusing the round is what changed that. So this is
a refusal, not a note.

## How

**A. `review_log.sh round-check`** prints one more record: `fresh` and the rounds below N, as a
comma list (`1,2`), at which the gate has a line with seat exactly `fresh-eyes`, any outcome; `-`
when none. Its header comment lists the record.

**B. `independent_review.sh`**, beside the cut check (rounds 2 and up, after round-check):
- `--depth normal`: refuse (exit 2, before any reviewer starts) unless round 1 is in the list.
- `--depth high`: refuse unless every round from 1 to the lower of N−1 and 3 is in it.
- `--depth light`, or no `--depth`: no check (Light owes no fresh-eyes; a run with no depth is
  already named in the trail note).
- The log cannot answer (off, missing, unreadable, no gate, or no round below N): warn in one
  line and go on, as the cut check does. Bookkeeping never fails a review.
- The refusal names the gate, the round with no line, and the command that settles it:
  `review_log.sh add --seat fresh-eyes --model <m> --gate <g> --depth <d> --round <r>`. A host
  that cannot run the seat (no sub-agent) logs it with `--outcome NOT-COUNTED --reason "<why>"`,
  which also settles it: the point is that the gate says, on the record, what happened.

**C. Round 1, at Normal or High:** after the round's summary, if the gate has no `fresh-eyes`
line at round 1 yet, one note: the seat is owed, and round 2 refuses until it is logged. The
host usually runs the seat while the script runs, so this is a reminder, not a fault.

**D. `SKILL.md`**: one sentence in step 3's **Cost log** paragraph: round 2 refuses a Normal or
High gate whose fresh-eyes seat is not logged, and the NOT-COUNTED line is how a host records
that it could not run it. The script header's ROUND CHECKS list gets the check.

Not done: matching seat names other than `fresh-eyes` (the refusal says the exact name, so a
host that logged a variant learns it once); checking the fresh-eyes seat's model or effort.

## How it is tested

In `test_round_checks.sh`, which runs the real `independent_review.sh` with
`INDEPENDENT_REVIEW_CHECKS_ONLY=1` (the checks production runs, then exit 5) against a throwaway
log and gate. Each case writes the gate's lines with `review_log.sh add`, as a host does:
1. Normal, round 2, round 1 has codex only: exit 2, and the message names `--seat fresh-eyes`
   and round 1. This is the case the change exists for.
2. Normal, round 2, round 1 has `fresh-eyes` (OK): exit 5.
3. Normal, round 2, round 1 has `fresh-eyes` with `NOT-COUNTED`: exit 5.
4. Normal, round 2, round 1 has `fresh-eyes-final-read` only: exit 2.
5. High, round 3, `fresh-eyes` at round 1 only: exit 2, naming round 2. High, round 5, lines
   at rounds 1 to 3: exit 5 (round 4 is not owed).
6. Light, round 2, no `fresh-eyes`: exit 5. No `--depth`: exit 5.
7. `REVIEW_LOG=off`, Normal, round 2: exit 5, with the warning line.
8. A fresh-eyes line of another gate does not count: exit 2.
9. `review_log.sh round-check` alone: the `fresh` record lists `1,3` for a gate with lines at
   rounds 1 and 3, and `-` for none.
10. Round 1 at Normal with the stub codex, no fresh-eyes line: the note prints; with one logged
    first, it does not.

Mutation check before the DIFF gate: revert B's comparison (always pass) and case 1 must fail;
make C print always and case 10's second half must fail.
