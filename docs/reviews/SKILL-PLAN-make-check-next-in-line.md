# Plan: a "next in line" entry for the `make check` lock

Status: plan only; nothing built. Building waits for the owner's go.

## What

`scripts/check_lock.sh` lets one `make check` run at a time on a Mac and refuses the rest (exit
75). After this change the manager session that hands out slots can name the session whose turn
is next. While that entry is live, the lock refuses every other session, even when no run holds
it. The named session runs, and its run removes the entry. An entry the named session does not
use expires 10 minutes after the last run ended, and the next run removes it and says so.

The lock still never waits. Sessions never write the entry. A session that only runs `make check`
sees nothing new unless the manager has named someone else.

## Why

The manager keeps an order, but the lock cannot see it: whoever runs first after a run ends wins.
From session transcripts, 14 to 18 Nov, 14 refusals in all; 6 came within 2 minutes of the
holder's start, over 5 freed slots:

| Freed slot (CET) | Winner | Held the manager's slot? |
|---|---|---|
| 14 Nov 20:00, 20:10 | a run in the lock's own build folder | no manager yet (it started 15 Nov) |
| 16 Nov 15:27 | the manager's own run | yes |
| 17 Nov 18:53 | a session outside the manager's queue | no: the queue was move-token-clicks, kit-four-fixes, pages-by-command-fix |
| 18 Nov 11:24 | a clean-plate session | no: the manager wrote to it, "your 11:24 run went ahead of kit-four-fixes, which the queue puts first" |

So the race is real, twice in two days. On 18 Nov kit-four-fixes was refused at 11:25 and ran
at 12:06. (The brief counted 19 refusals, 7 fast, over 6 slots; this recount found fewer and did
not find where the gap lies.)

## How

1. **The entry.** One file beside the lock: `~/.cache/croftweaver/make-check.next` (the lock's
   path with `.lock` replaced by `.next`, so `CROFTWEAVER_CHECK_LOCK` moves both in tests). Four
   lines: the named session, the session that set it, the time it was set (epoch seconds), and a
   fixed tag line so a damaged file is recognized. Mode 0600, as the lock file.
2. **The manager's command.** A new `scripts/check_next.sh`:
   - `set <session>` writes the entry (temp file, then `mv`, so a reader never sees half of it).
     It refuses an id that is not `local_` plus 36 hex digits and dashes, and it refuses an id
     equal to the caller's own `CLAUDE_CODE_HOST_SESSION_ID`: "a session cannot put itself next;
     ask the manager". Replacing a live entry is allowed and prints the session it replaced.
   - `show` prints the entry and when it expires, or "no entry".
   - `clear` removes it and prints whose entry it was.
   It does not take the lock, so the manager can name the next session while a run is going.
3. **Proof of identity.** The desktop app sets `CLAUDE_CODE_HOST_SESSION_ID` in each session's
   shell, and the lock already writes it as the holder: every one of the 14 refusals names its
   holder by such an id (and `echo $CLAUDE_CODE_HOST_SESSION_ID` in this session printed its own). A run counts as the named session when that variable equals the entry.
   A subagent inherits it and counts as its session. This guards against mistakes, not against a
   session that sets the variable on purpose.
4. **The check in `check_lock.sh`.** After it takes the flock and before it writes its own details,
   the lock reads the old details (for the last run's end time) and the entry:
   - no entry: runs, as today;
   - entry names this session: removes the entry, runs;
   - entry names another session, or this run has no session id, and the entry is live: refuses,
     exit 75, the flock released by the exit;
   - entry has expired: removes it, prints one line ("an expired next-in-line entry for X was
     removed"), runs;
   - entry cannot be read (no tag line, a bad id): refuses, exit 75, and says to run
     `check_next.sh clear`. A run never guesses at a damaged entry.
   Reading under the flock means two runs that start together cannot both pass the check.
5. **Expiry.** An entry is live until 10 minutes after the later of the time it was set and the
   time the last run ended. So an entry set while a long run goes stays live through that run, and
   a named session that died or never comes blocks others for 10 minutes at most. One fixed
   constant, no option. To know the end time, the holder writes a fifth line, `ended <epoch>`, into
   the lock file after its command ends (it still holds the lock then). A holder killed with
   `kill -9` writes none; the expiry then counts from the time the entry was set. That rare case
   falls back to today's race, and nothing worse.
6. **What a refused session sees** (made-up ids):
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
   yours", it also runs `bash scripts/check_next.sh set <that session's id>` from a checkout of
   this repo. For its own run it clears the entry first: it cannot name itself.
8. **Docs.** `README.md`'s two script rows and `docs/WHAT-THE-SKILLS-RUN.md`'s lock row gain the
   new file and command. A comment in each script says what the entry is and why.

Left as it is: if the manager sets a new entry in the same moment the named run removes the old
one, the new entry is lost; `show` would show it gone. Two things at once, so no code for it.

Not adopted: a lock that waits, or a queue sessions join themselves (on 9 Nov the owner turned
down a waiting lock: "No, slots via you"; the lock built on 14 Nov refuses and points to the
manager instead); a stored manager id that `set` would check (nothing trusted could write it, and a
convention printed in every refusal costs less); an option for the 10 minutes.

Who it affects: anyone running `make check`, `make package` or `make smoke` on that Mac while an
entry is live, the owner in his own terminal included (no session id: refused). He can wait the
10 minutes or run `check_next.sh clear`. CI runners have no entry and see no change.

## Scenarios

- **S1, the 18 Nov race.** A clean-plate run holds the lock. At 11:25 the manager runs
  `check_next.sh set` with kit-four-fixes' id. The run ends at 11:40. At 11:41 another session
  runs `make check`: refused, and the message names kit-four-fixes. At 11:42 kit-four-fixes runs
  `make check`: it runs, and `check_next.sh show` says "no entry".
- **S2, the named session never comes.** As S1, but kit-four-fixes has died. At 11:49 another
  session is refused. At 11:51 (11 minutes after the run ended) it runs, with one line saying the
  entry for kit-four-fixes expired and was removed.
- **S3, the manager changes its mind.** It runs `set` with another id: the old entry is replaced,
  and the command names the session it replaced. `clear` removes the entry at once.
- **S4, a session tries to put itself next.** `check_next.sh set` with its own id is refused
  and nothing is written.
- **S5, no entry.** Everything behaves exactly as today.

## How it is tested

New cases in `scripts/test_check_lock.sh`, entering through `make check` in a copy of the real
Makefile, as T1 does. The copy gains `check_next.sh`. Ids are made up.

- **N1** (S1): holder runs; `check_next.sh set A`; holder ends; `make check` as B is refused with
  Error 75 and the stub guard never runs; `make check` as A runs, and the entry file is gone.
- **N2** (S2): an entry set 11 minutes ago (the test writes the epoch into the file) and a lock
  file whose `ended` line is 11 minutes old: B runs, its output has the expiry line, the file is
  gone. With the `ended` line 2 minutes old instead, B is refused: the grace counts from the end
  of the run, not from the set time.
- **N3**: a live entry and no `CLAUDE_CODE_HOST_SESSION_ID`: refused.
- **N4**: a damaged entry (no tag line): refused, and the output names `check_next.sh clear`.
- **N5** (S3, S4): `set` with the caller's own id, and with a malformed id: refused, no file.
  `set` over a live entry names the old one. `show` and `clear` print what the plan says.
- **N6**: after a run ends, the lock file's fifth line is `ended` and an epoch no older than the
  run.
- T1 to T9 stay as they are and must still pass (S5). Mutations, run by hand before review:
  remove the check from step 4 (N1 must fail); count the grace from the set time only (N2's
  second half must fail); drop the self-name refusal (N5 must fail).

The lock test runs on macOS by hand and on Linux in the `check-lock` CI job, as today.

## Cost and risk

Code that other runs depend on, so the DIFF gate runs at Normal with Codex and GLM 5.3, as the lock
itself had (5 rounds, 513,199 tokens on 14 Nov; a smaller change, so likely fewer). Worst case of a
bug: `make check` refused when it should run. The owner clears it with `check_next.sh clear` or by
deleting the `.next` file; the lock itself is untouched.
