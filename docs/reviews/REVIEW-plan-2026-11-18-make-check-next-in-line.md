# PLAN review — branch `claude/make-check-next-in-line-9849f5` — a next-in-line entry for the make check lock

Plan: `docs/reviews/SKILL-PLAN-make-check-next-in-line.md`. Depth: Normal. Seats: Codex and GLM
5.3 on melious, per the seat rules for plans, plus fresh-eyes (Sonnet) in round 1. No red team:
the change touches no user data, logins, permissions, money or deletion; it changes how a local
test lock admits runs. Gate id `20261118T132435Z-63622`. This session (make-check-next-in-line)
created the branch and every commit.

The evidence sent with `--evidence` is kept outside the repo: it quotes the maintainer's session
transcripts and local paths, which this public repo must not hold. The plan's Why section gives
the dates and counts the evidence supports.

| Round | Head | Artifact | Reviewers | seconds, tokens | BUG/RISK/NIT |
|-------|------|----------|-----------|-----------------|--------------|
| 1 | `461ce101` | the whole plan | Codex; melious; fresh-eyes (Sonnet) | Codex 172 s, 87,230; melious 355 s, 25,392; fresh-eyes 87 s, 118,510 | 1 / 9 / 4 |
| 2 | `13e514d3` | the whole plan, `--verify` round 1's findings | Codex; melious | Codex 226 s, 58,937; melious 369 s, 30,168 | 2 / 4 / 3 |
| 3 | `01147a45` | the whole plan, `--verify` round 2's findings | Codex; melious | Codex 91 s, 52,445; melious 407 s, 37,085 | 1 / 0 / 4 |
| 4 | `57e31381` | the whole plan, `--verify` round 3's findings, `--earned-by make-exit-status` | Codex; melious | Codex 106 s, 48,488; melious 453 s, 36,831 | 0 / 0 / 6 |

Counts are after merging the seats: a finding two seats raised counts once, at the higher grade.

## Round 1 findings

| Id | Seat | Sev | Finding | Disposition |
|----|------|-----|---------|-------------|
| P1 | Codex; fresh-eyes as RISK | BUG | Emptying the entry after reading it could wipe an entry the manager set in the same moment | fixed: every read and write of the entry holds a flock on the entry file, waits up to 5 s, then refuses; emptied in place; N7 added |
| P2 | Codex | RISK | Checkouts cut before the merge ignore the entry | fixed: named under "Left as it is"; the manager tells sessions to rebase |
| P3 | Codex, fresh-eyes | RISK | Repository lists the new script must join were not named | fixed: step 8 names them; the script ships in the zip |
| P4 | Codex, melious | RISK | How a session proves it is the named one rested on an unchecked variable | fixed: checked that a subagent sees the same id; step 3 names the launch modes not checked |
| P5 | melious | RISK | The id pattern was miscounted | fixed: `local_` plus a lowercase UUID, from a real id |
| P6 | melious, fresh-eyes | RISK | Replacing `.lock` maps an odd lock path onto itself | fixed: `.next` is appended to the whole path |
| P7 | Codex | RISK | N5 did not check that a replaced entry admits the new session | fixed |
| P8 | fresh-eyes | RISK | A wrong but well-formed id blocks others for 10 minutes | fixed: `set` prints the id back; step 7 says where the id comes from |
| P9 | fresh-eyes | RISK | `show` during a run had no expiry rule | fixed: "10 minutes after the current run ends"; N5 checks it |
| P10 | fresh-eyes | NIT | The setter text with no session id; damaged-entry text sent every session to `clear` | fixed |
| P11 | melious, fresh-eyes | NIT | Which session was refused at 11:25 was inferred | fixed: the evidence shows it |
| P12 | melious | NIT | N4 covered only a missing tag | fixed: step 4 lists the damaged forms; N4 runs each |
| P13 | melious | NIT | The gap between the brief's count and the recount was unexplained | fixed: Why names the method and says the gap was not traced |
| P15 | Codex | RISK | The plan understated what macOS CI runs | fixed: the tested section names the macOS job's steps |

P14 was an UNVERIFIABLE item (whether the 17 Nov queue still held at 18:53), answered from the
evidence; it is not a finding.

## Round 2 findings

| Id | Seat | Sev | Finding | Disposition |
|----|------|-----|---------|-------------|
| Q1 | Codex | BUG | A `set` from a terminal with no session id had no valid setter value, so the reader would refuse it | fixed: the setter line is `none`, a valid value; N3 runs it |
| Q2 | Codex | RISK | N5 checked A after C had already used the entry | fixed: the order is A refused, C runs, then `set A` and `clear` |
| Q3 | Codex; melious as RISK | BUG | "the order of the code is the guard" was not a guard | fixed by narrowing: one helper does read, decision and write under one flock; N7 covers each path; the plan says the hold between read and emptying is not tested |
| Q4 | Codex | RISK | The id the manager names was not shown to equal what the lock compares | fixed: the id is the one the session's own shell prints |
| Q5 | melious | RISK | "Emptied in place, never unlinked" was in the record, not in the plan | fixed: step 1 |
| Q6 | melious | RISK | Any session can `set` another and hold others off | fixed: named under "Left as it is" as accepted |
| Q7 | melious | NIT | What's expiry sentence contradicted step 5 | fixed |
| Q8 | melious | NIT | "never waits" against the 5 s entry flock | fixed: "never waits for another run" |
| Q9 | melious | NIT | The exit code of the entry-flock timeout was not given | fixed in step 1 (corrected in round 3) |

## Round 3 findings

| Id | Seat | Sev | Finding | Disposition |
|----|------|-----|---------|-------------|
| R1 | Codex | BUG | `make check` exits 2 when its recipe exits 75, so "exits 75" for make check was wrong | fixed: `check_lock.sh` exits 75, `make check` fails with `Error 75` and exit 2, `check_next.sh` exits 1; N1 and N7 say so |
| R2 | melious | NIT | `clear` on a damaged entry was unspecified, though the refusal tells people to ask for it | fixed: `clear` empties any entry and says when it could not read the name |
| R3 | melious | NIT | "Sessions never write the entry" was too strong | fixed: a run never sets an entry, only empties one |
| R4 | melious | NIT | N7 did not cover the expired-entry and plain-refusal paths | fixed: N7 adds both |
| R5 | melious | NIT | A wrong first line was not named among the damaged forms | fixed: step 4 and N4 |

Round 4 ran with `--earned-by make-exit-status` for R1, a kind no earlier round named, so no cut
was owed.

## Round 4 findings

Codex found nothing and verified R1 to R5; it reproduced make's exit 2 for a recipe that exits 75.
Melious verified R1 to R5 and raised six NITs:

| Id | Seat | Sev | Finding | Disposition |
|----|------|-----|---------|-------------|
| S1 | melious | NIT | `show` had no rule for a dead pid with no `ended` line, and reads the lock file without its flock | fixed: it counts from the set time, and its expiry line is called advisory |
| S2 | melious | NIT | The entry-flock timeout had no message of its own; the busy text would be false | fixed: step 1 gives its own message, naming the `.next` path |
| S3 | melious | NIT | Too few or too many lines were not among the damaged forms | fixed: step 4 and N4 |
| S4 | melious | NIT | N4 did not assert the exit status | fixed: exit 2 with `Error 75` |
| S5 | melious | NIT | The round 3 record said N1 gave exit 2; N1 said only `Error 75` | fixed: N1 says both |
| S6 | melious | NIT | "5 rounds, 513,199 tokens on 14 Nov" had no support in the evidence | fixed: the plan cites `REVIEW-make-check-lock-2026-11-14.md`, whose line 21 gives the figure |

Melious's UNVERIFIABLE items (make's exit mapping, the wiring targets, the id shape, the Linux CI
job, the entry flock dropping on holder death) are either verified by Codex this round, read in
round 1, or properties of the build that its tests check; none is a finding.

## Verdict

**CLEAN, no BUG open.** Round 4 raised no BUG or RISK, so by the round budget no round 5 is
earned; its six NIT fixes were checked by hand, not by another round. 4 rounds, 34 findings
(4 BUG, 13 RISK, 17 NIT). 495,086 tokens logged, fresh-eyes's 118,510 included. No red team
(see the top). Nothing built; building waits for the owner's go.
