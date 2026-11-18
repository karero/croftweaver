# Plan: a "next in line" entry for the `make check` lock

Status: plan only; nothing built. Building waits for the owner's go.

## What

`scripts/check_lock.sh` lets one `make check` run at a time on a Mac and refuses the rest (exit
75). After this change the manager session that hands out slots can name the session whose turn
is next. While that entry is live, the lock refuses every other session, even when no run holds
it. The named session runs, and its run empties the entry. An entry the named session does not
use expires 10 minutes after the later of the time it was set and the end of the last run, and
the next run empties it and says so.

The `make check` lock still never waits for another run. Sessions never write the entry. A session that only runs
`make check` sees nothing new unless the manager has named someone else.

## Why

The manager keeps an order, but the lock cannot see it: whoever runs first after a run ends wins.
A recount from local session transcripts, 14 to 18 Nov (every tool result holding the refusal
text), found 14 refusals; 6 came within 2 minutes of the holder's start, over 5 freed slots:

| Freed slot (CET) | Winner | Held the manager's slot? |
|---|---|---|
| 14 Nov 20:00, 20:10 | a run in the lock's own build folder | no manager yet (it started 15 Nov) |
| 16 Nov 15:27 | the manager's own run | yes |
| 17 Nov 18:53 | a session outside the manager's queue | no: the queue was move-token-clicks, kit-four-fixes, pages-by-command-fix, and no later message changed it |
| 18 Nov 11:24 | a clean-plate session | no: the manager wrote to it, "your 11:24 run went ahead of kit-four-fixes, which the queue puts first" |

So the race is real, twice in two days. On 18 Nov kit-four-fixes was refused at 11:25 and ran at
12:06. (The brief that started this plan counted 19 refusals, 7 fast, over 6 slots, by another
method; the gap was not traced.)

## How

1. **The entry.** One file beside the lock, named by adding `.next` to the lock's path:
   `~/.cache/croftweaver/make-check.lock.next` (so `CROFTWEAVER_CHECK_LOCK` moves both in tests,
   and no lock path can map onto itself). Empty means no entry. Otherwise four lines: a fixed tag
   line, the named session, the session that set it, and the time it was set (epoch seconds).
   Mode 0600, as the lock file. The file is never unlinked or recreated: writing and emptying
   rewrite it in place and truncate it, as the lock does its own file. Every command that reads
   or writes it goes through one helper that holds a flock on the entry file itself for that
   moment only (microseconds), across the whole read, decision and write: `set`, `clear`, `show`
   and the lock's check below. So no read can see half an entry, and a run that empties the entry
   cannot wipe one the manager set in the same moment. That short flock waits up to 5 s, then the
   command refuses loudly: `make check` with exit 75 (so callers need no change), `check_next.sh`
   with exit 1. The `make check` lock itself stays non-waiting.
2. **The manager's command.** A new `scripts/check_next.sh`, Perl inside as `check_lock.sh` has:
   - `set <session>` writes the entry and prints the id back, to be checked against the
     session's own. It refuses an id that is not `local_` and a lowercase UUID (8-4-4-4-12 hex
     digits, as the app's ids are), and an id equal to the caller's own
     `CLAUDE_CODE_HOST_SESSION_ID`: "a session cannot put itself next; ask the manager". With no
     session id (the owner's own terminal), the setter line is the single word `none`, a valid
     value, and `show` and refusals print it as "none (CLAUDE_CODE_HOST_SESSION_ID not set)", as
     the lock does. Replacing a live entry is allowed and prints the session replaced.
   - `show` prints the entry and when it expires: a time, or "10 minutes after the current run
     ends" while a run holds the lock (the lock file names a live pid and has no `ended` line).
     With no entry, "no entry".
   - `clear` empties it and prints whose entry it was.
   It never takes the `make check` lock, so the manager can name the next session while a run goes.
3. **Proof of identity.** The desktop app sets `CLAUDE_CODE_HOST_SESSION_ID` in each session's
   shell, and the lock already writes it as the holder. Checked on 18 Nov: this session's shell
   and a subagent it started both printed the same `local_…` id, and all 14 refusals name their
   holder by an id of that form. A run counts as the named session when that variable equals the
   entry. Not checked: sessions started other ways (a terminal `claude`, a scheduled task); one
   without the variable is refused while an entry is live, and if it is the named one, its entry
   expires after the usual 10 minutes. This guards against mistakes, not against a session that
   sets the variable on purpose.
4. **The check in `check_lock.sh`.** After it takes the `make check` flock and before it writes
   its own details, the lock reads the old details (for the last run's end time) and, under the
   entry's flock, the entry:
   - no entry: runs, as today;
   - entry names this session: empties the entry, runs;
   - entry names another session, or this run has no session id, and the entry is live: refuses,
     exit 75; the exit releases both flocks;
   - entry has expired: empties it, prints one line ("an expired next-in-line entry for X was
     removed"), runs;
   - entry cannot be read (no tag line, a malformed named id, a setter line that is neither an id
     nor `none`, a time that is not a number): refuses, exit 75, and says to ask the manager to clear it. A run never guesses at a
     damaged entry.
   Reading under the `make check` flock means two runs that start together cannot both pass.
5. **Expiry.** An entry is live until 10 minutes after the later of the time it was set and the
   time the last run ended. So an entry set while a long run goes stays live through that run, and
   a named session that died or never comes blocks others for 10 minutes at most. One fixed
   constant, no option. To know the end time, the holder writes a fifth line, `ended <epoch>`, into
   the lock file after its command ends (it still holds the lock then). A holder killed with
   `kill -9` writes none; the expiry then counts from the time the entry was set, which can end it
   early. That rare case falls back to today's race.
6. **What a refused session sees** (made-up ids, the times of S1):
   ```
   make check refused: the manager has given the next make check slot to another session.
     next:    local_00000000-0000-0000-0000-0000000000aa
     set by:  local_00000000-0000-0000-0000-0000000000bb at 11:25 CET
     expires: 11:50 CET, if that session has not started its run by then
   Wait, or ask the manager for a slot. Do not set or clear the entry yourself, and do not retry
   in a loop.
   ```
   The busy refusal stays as it is, so callers that handle exit 75 need no change.
7. **The manager's practice** (outside this repo): when it tells a session "the next slot is
   yours", it also runs `bash scripts/check_next.sh set <id>` from a checkout of this repo. The id
   is the one that session's own shell prints (`echo $CLAUDE_CODE_HOST_SESSION_ID`), which the
   session sends when it asks for a slot: the same value the lock compares, never a shortened one
   or one read from elsewhere. `set` prints it back. For its own run the manager clears
   the entry first: it cannot name itself. It tells sessions to rebase before their slot (see "Left as it is").
8. **Repository wiring.** `check_next.sh` ships in the handoff zip as `check_lock.sh` does, since
   the lock in the zip reads the entry too: `scripts/package.sh` (the `zip -r` line and
   `REQUIRED`), `scripts/check_cdpath_safe.sh` (an entry with its reason: run bare it prints usage
   and exits 2), `scripts/test_mktemp_guard.sh` if the script uses `mktemp`, the Makefile's guard
   comment, `README.md`'s script rows and `docs/WHAT-THE-SKILLS-RUN.md`'s lock row (the new file
   and command). A comment in each script says what the entry is and why.

Left as it is:
- A worktree cut before the merge runs its own old `check_lock.sh`: it ignores the entry and
  writes no `ended` line. Until such worktrees are rebased, the race stays for them, and an entry
  set before one of their runs may expire early. The manager's rebase rule (step 7) covers it.
- A guard in the lock against a stale checkout was not adopted: the old copy cannot run new code.
- Any session can run `check_next.sh set` with another session's id and so hold every other run
  off for 10 minutes at a time. Nothing stops it; the rule is in every refusal, and the setter
  line shows who did it. Accepted, as with the rest of this design: it guards against mistakes.

Not adopted: a lock that waits, or a queue sessions join themselves (on 9 Nov the owner turned
down a waiting lock: "No, slots via you"; the lock built on 14 Nov refuses and points to the
manager instead); a stored manager id that `set` would check (nothing trusted could write it, and a
convention printed in every refusal costs less); an option for the 10 minutes.

Who it affects: anyone running `make check`, `make package` or `make smoke` on that Mac while an
entry is live, the owner in his own terminal included (no session id: refused). He can wait the
10 minutes or run `check_next.sh clear`. CI runners start with no entry and see no change.

## Scenarios

- **S1, the 18 Nov race.** A clean-plate run holds the lock. At 11:25 the manager runs
  `check_next.sh set` with kit-four-fixes' id. The run ends at 11:40. At 11:41 another session
  runs `make check`: refused, and the message names kit-four-fixes. At 11:42 kit-four-fixes runs
  `make check`: it runs, and `check_next.sh show` says "no entry".
- **S2, the named session never comes.** As S1, but kit-four-fixes has died. At 11:49 another
  session is refused. At 11:51 (11 minutes after the run ended) it runs, with one line saying the
  entry for kit-four-fixes expired and was removed.
- **S3, the manager changes its mind.** It runs `set` with another id: the old entry is replaced,
  and the command names the session it replaced. `clear` empties the entry at once.
- **S4, a session tries to put itself next.** `check_next.sh set` with its own id is refused
  and nothing is written.
- **S5, no entry.** Everything behaves exactly as today.

## How it is tested

New cases in `scripts/test_check_lock.sh`, entering through `make check` in a copy of the real
Makefile, as T1 does. The copy gains `check_next.sh`. Ids are made up, in the app's format.

- **N1** (S1): holder runs; `check_next.sh set A`; holder ends; `make check` as B is refused with
  Error 75 and the stub guard never runs; `make check` as A runs, and the entry is empty.
- **N2** (S2): an entry set 11 minutes ago (the test writes the epoch into the file) and a lock
  file whose `ended` line is 11 minutes old: B runs, its output has the expiry line, the entry is
  empty. With the `ended` line 2 minutes old instead, B is refused: the grace counts from the end
  of the run, not from the set time.
- **N3**: a live entry and no `CLAUDE_CODE_HOST_SESSION_ID`: refused. And `set A` with no session
  id (the owner's terminal): the setter line is `none`, B is refused, A runs.
- **N4**: damaged entries, one at a time (no tag line; a malformed named id; a malformed setter id;
  a setter line that is neither an id nor `none`; a time that is not a number): each refused, and
  the output says to ask the manager to clear it.
- **N5** (S3, S4): `set` with the caller's own id, and with a malformed id: refused, the entry
  unchanged. `set A`, then `set C`: the output names A; `make check` as A is then refused and the
  refusal names C; then `make check` as C runs. Then `set A` again, `clear`: the output names A,
  the entry is empty, and `make check` as B runs. `show` with no entry, with an
  entry and an `ended` line, and while a holder runs: each prints what step 2 says.
- **N6**: after a run ends, the lock file's fifth line is `ended` and an epoch no older than the
  run.
- **N7**: a holder of the entry's flock (a test process holding it 7 s): `set`, `clear`, `show`,
  and `make check` as the named session each refuse after about 5 s, loudly, with the exit codes
  of step 1, and the entry is unchanged afterwards. So the emptying path waits on the flock too.
- T1 to T9 stay as they are and must still pass (S5). Mutations, run by hand before review:
  remove the check from step 4 (N1 must fail); count the grace from the set time only (N2's second
  half must fail); drop the self-name refusal (N5 must fail); drop the `ended` write (N6 must fail;
  N2 writes its own `ended` line). Not tested: that the helper keeps its flock between the read
  and the emptying. Forcing that interleaving would need a pause hook in the lock's code, which is
  not added; one helper doing both under one flock is the design, and the DIFF review checks it.

Not tested: a run from a checkout cut before the merge (see "Left as it is"). The lock test
runs on macOS by hand and on Linux in the `check-lock` CI job, as today; the macOS CI job's
`make smoke` and its `make check` in the unzipped handoff go through the lock with no entry.

## Cost and risk

Code that other runs depend on, so the DIFF gate runs at Normal with Codex and GLM 5.3, as the lock
itself had (5 rounds, 513,199 tokens on 14 Nov; a smaller change, so likely fewer). Worst cases:
`make check` refused when it should run (the owner runs `check_next.sh clear`, or empties the
`.next` file; the lock itself is untouched), or, for a checkout cut before the merge, the race as
today.
