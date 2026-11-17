# Plan: round 2 refuses a gate whose fresh-eyes seat was never logged

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | written 2026-11-17 | this file |
| 2 | Plan review gate (Normal; no red team: it touches no server, user data, login, money, deletion or schema) | done 2026-11-17: 3 rounds, round 3 clean; Codex alone (melious out of balance) plus fresh-eyes in round 1 | `REVIEW-plan-2026-11-17-fresh-eyes-seat-check.md` |
| 3 | The change, in one pull request, with its DIFF gate | done 2026-11-17: DIFF gate 1 round, clean (2 NIT); Codex alone plus fresh-eyes | this PR; `REVIEW-diff-2026-11-17-fresh-eyes-seat-check.md` |

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
comma list (`1,2`), at which the gate has a line with seat exactly `fresh-eyes` and a round
number, any outcome; `-` when none. When the log exists but cannot be written, the record is
`fresh ?` instead: `add` only warns on a failed write (`review_log.sh`, "bookkeeping never fails
a review"), so a host's line may be missing through no fault of the host. Its header comment
lists the record.

**B. `independent_review.sh`**, beside the cut check (rounds 2 and up, after round-check):
- `--depth normal`: refuse (exit 2, before any reviewer starts) unless round 1 is in the list.
- `--depth high`: refuse unless every round from 1 to the lower of N−1 and 3 is in it.
- `--depth light`: no check (Light owes no fresh-eyes).
- No `--depth`: no check, and one warning line that the seat check was skipped for want of
  `--depth`, beside the trail note such a run already gets.
- The log cannot answer (off, missing, unreadable, unwritable, no gate, or no round below N):
  warn in one line and go on, as the cut check does. Bookkeeping never fails a review.
- The refusal names the gate id, the rounds with no line, and the command that settles it:
  `review_log.sh add --seat fresh-eyes --model <m> --gate <plan|diff> --depth <d> --round <r>`,
  run in this worktree, or from anywhere with `--gate-id <id>` (which `add` accepts). It also
  says that a `--round 1` re-run starts a new gate, so a seat logged before the re-run belongs to
  the old one and is logged again. A host that cannot run the seat (no sub-agent) logs it with
  `--outcome NOT-COUNTED --reason "<why>"`, which also settles it: the point is that the gate
  says, on the record, what happened. A FAILED line settles it too, for the same reason.

**C. Round 1, at Normal or High:** at the end of the run (after `new-gate` and the round's
summary), the script calls `review_log.sh round-check --round 2` itself, since its usual call
does not run at round 1. If the `fresh` record lacks round 1, one note: the seat is owed, and
round 2 refuses until it is logged with `--gate-id <id>` (this gate's id, printed in the note).
The gate is minted late in the run, after the artifact is read (`new-gate` in
`independent_review.sh`), so the note gives the id rather than "after the run started". The host
usually runs the seat while the script runs, so this is a reminder, not a fault. A `?` record
prints nothing.

**D. `SKILL.md`**: in step 3's **Cost log** paragraph: round 2 refuses a Normal or High gate
whose fresh-eyes seat is not logged; log it with `--gate-id`, taking the id from the gate line
round 1 prints at its end (a line logged before round 1 mints its gate goes to the previous
one); any outcome
counts, and NOT-COUNTED with a reason is how a host records that it could not run it. The script
header's ROUND CHECKS list gets the check.

**What first use costs, and what the log cannot say.** At today's habits the refusal stops about
four Normal gates in five once, at round 2. Whether those hosts ran the seat and did not log it,
or never ran it, the log cannot tell (UNVERIFIABLE here; the observation that settles it is a
sample of host transcripts against the log). Either way the cost of a refusal is one `add` command,
or one fresh-eyes pass that was owed; no review is lost.

Not done: matching seat names other than `fresh-eyes` (the refusal says the exact name, so a
host that logged a variant learns it once); taking a missing `--depth` from the gate's earlier
lines; checking the fresh-eyes seat's model or effort.

## How it is tested

In `test_round_checks.sh`, which runs the real `independent_review.sh` with
`INDEPENDENT_REVIEW_CHECKS_ONLY=1` (the checks production runs, then exit 5) against a throwaway
log and gate. Each case writes the gate's lines with `review_log.sh add`, as a host does:
1. Normal, round 2, round 1 has codex only: exit 2, and the message names `--seat fresh-eyes`,
   round 1 and the gate id. This is the case the change exists for.
2. Normal, round 2, round 1 has `fresh-eyes` (OK): exit 5. The same with `NOT-COUNTED`, and
   with `FAILED`: exit 5.
3. Normal, round 2, the line logged from another directory with `--gate-id <id>`: exit 5.
4. Normal, round 2, round 1 has `fresh-eyes-final-read` only: exit 2.
5. High, round 3, `fresh-eyes` at round 1 only: exit 2, naming round 2. High, round 5, lines
   at rounds 1 to 3: exit 5 (round 4 is not owed).
6. Light, round 2, no `fresh-eyes`: exit 5, no warning. No `--depth`: exit 5, with the
   skipped-check warning.
7. `REVIEW_LOG=off`, Normal, round 2: exit 5, with the warning line. A log made read-only
   (`chmod a-w`) after round 1's codex line: exit 5, with the warning line.
8. A fresh-eyes line of another gate does not count: exit 2. So does a line logged before a
   `--round 1` re-run (the re-run started a new gate): exit 2.
9. `review_log.sh round-check` alone: the `fresh` record lists `1,3` for a gate with lines at
   rounds 1 and 3, `-` for none, and `?` for a read-only log.
10. Round 1 at Normal with the stub codex (the whole script, as the file's last cases already
    run it): with no fresh-eyes line, the note prints; with the stub codex logging a
    `fresh-eyes` line through `review_log.sh add` during the run (so after `new-gate`), it does
    not.

Mutation check before the DIFF gate: revert B's comparison (always pass) and case 1 must fail;
make C print always and case 10's second half must fail; drop the seat match's gate filter
(count every gate's `fresh-eyes` lines) and case 8 must fail.
