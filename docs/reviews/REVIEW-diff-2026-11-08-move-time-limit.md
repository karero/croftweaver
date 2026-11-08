# DIFF review: branch `fix/move-time-limit-words`, the move script's time-limit stop

Plan: `workers-for-new-sites/PLAN-move-time-limit.md` in the maintainer's planning hub (PLAN gate
clean at round 5: 5 rounds, 33 findings, 664,441 tokens; the owner's go to build, 2026-11-08).
Base `6859448c` · depth: Normal (a tooling script's logic is never Light) · no red team (no box,
user data, login, money, deletion or schema). Seats: Codex and GLM 5.3 on melious in one command
(`SECOND_SEAT=melious MELIOUS_MODEL=glm-5.3`), fresh-eyes Sonnet in round 1. The artifact leaves out
`docs/reviews/`. The runs, the evidence and the mutation record sit in the session's scratchpad;
the figures below are copied from them.

**Verdict: CLEAN at round 1** (no BUG; the one RISK refuted by a READ; both NITs fixed in
`7fd0aff3`, not externally re-verified). Gate `20261108T134852Z-97193`, 1 round, 3 findings,
207,976 tokens logged.

## Mutation check (before round 1)

Each mutation ran in a throwaway copy of `skills/new-website/scripts`, with the plan's tests
picked by name. All KILLED. M8 ran again on `7fd0aff3` after the round-1 fix to the same lines.

| Id | Mutation | Killed by |
|---|---|---|
| M0 | the script as on main | T1, T1b, T2, T3 (6.2), T4 |
| M1 | no place on makeApi's deadline | T2 |
| M2 | no place on makeSiteFetch's deadline | T1 |
| M3 | no label in `ctx.run` | T4 |
| M4 | no label in `ctx.gitNet` | T3 |
| M5 | `waiting` true before a site call | T1 |
| M6 | `waiting` false after a Cloudflare call | T2 |
| M7 | `waiting` false when a program is killed | T3, T4 |
| M8 | `fetchAll` stops at once, as on main | T1b |
| M9 | no count | T1 |
| M10 | the fixed "55 seconds" | T1 |

Not covered by a test, as the plan says: the build's `sh` label, and `waiting` before a Cloudflare
call, after a site call and before a program starts.

## Rounds

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|---|---|---|---|---|---|
| 1 | `1ecdd4d7` | whole change; evidence (49,211 bytes) | Codex gpt-6.1-sol; melious glm-5.3; fresh-eyes Sonnet | Codex 146 s, 51,164 · melious 138 s, 35,480 · fresh-eyes 56 s, 121,332 | 0 / 1 / 2 (Codex 0/0/0, melious 0/1/2, fresh-eyes 0/0/0) |

## Round 1 findings

| Id | Sev | From | Finding | Status |
|---|---|---|---|---|
| A1 | RISK | melious | The guide says every time-limit stop names its call; a deadline made without a place elsewhere would break that | Refuted by READ: `grep -n "new Deadline\|runProgram)(\|io\.run\b\|runProgram("` finds six `new Deadline` (four with a place, two in `runProgram`) and three places that run `runProgram`, each labelling its deadline (lines 599, 608, 1217). `Deadline` is not exported |
| A2 | NIT | melious | A checkpoint `save()` that throws sits outside the worker's `try`, so the other workers go on | Fixed: the save is inside the `try` |
| A3 | NIT | melious | T1b waits for call 41 by polling with a 10-second budget | Fixed: it waits on a promise the 41st call resolves |

Fresh-eyes: no findings. Its one UNVERIFIABLE entry (no run of the whole test file with the new
tests in it) is settled by the full run on `7fd0aff3`: 188 tests, 187 pass.

## The one test that failed in full runs

"an undo whose added domain is missing from the project's own list for a while finishes without
adding it twice" failed in both full runs (on `1ecdd4d7` before the new tests, on `7fd0aff3`). It
runs against the real clock, and another program held the machine's load average near 400 through
both runs. The first failure said "Reading what the move needs took 11 seconds of this run's 55";
the second was a `move --confirm` that ended with 1 inside `movedAndPassed`. Neither path makes a
`Deadline` or calls `fetchAll`. Run alone, it passed once on `1ecdd4d7`, then 3 of 3 times on
`7fd0aff3` and 3 of 3 on main, the two run side by side (load 56 to 94). Not shown: whether main
fails a full run under the same load.
