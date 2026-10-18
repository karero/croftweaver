# Plan: one site's AI check at a time

One-page plan for the follow-up row of 2026-10-18 in `docs/BUGLOG.md` ("several sites' weekly
jobs", `track.sh`). Code written against origin/main `89f965b5`, branch `fix/gsc-ai-check-lock`.

## Status

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ revised after rounds 1 to 3 and the final full read | this file |
| 2 | PLAN gate (Normal) | ✅ clean: 3 rounds, final full read, wording pass; no BUG open | trail `REVIEW-plan-2026-10-18-ai-check-lock.md` |
| 3 | Stagger fix merged (it adds the BUGLOG row this closes and the SKILL.md sentence this edits) | ⏸ karero/croftweaver#354 open | — |
| 4 | Build the lock and tests T1 to T6 (the maintainer's go, asked in this session on 2026-10-18 after the PLAN gate: "Yes, go ahead") | ✅ built; `make check` and `make test` green | `ad40835f`, `a1933ba3` (`references/geo-check.md`'s note, moved here from step 5 because #354 does not touch that file) |
| 5 | After step 3: merge main in, then SKILL.md and the BUGLOG row | ⏸ waits for #354 | — |
| 6 | DIFF gate (Normal: shipped code) | ▶ 2 rounds, 12 findings, no BUG; rounds closed at `458af541`; step 5's prose still to be re-gated | trail `REVIEW-diff-2026-10-18-ai-check-lock.md` |
| 7 | Push and PR, after the maintainer says yes. Before the first push, the branch's earlier commits are folded into one, because one of them named the owner's sites; `git log -p 89f965b5..HEAD` must match no name `scripts/check_clean.sh` refuses | ⏸ | — |

Legend: ✅ done · ▶ in progress · ⏸ not started or blocked

## What and why

On 2026-10-12 one owner's sites all started their weekly jobs at Monday 09:00, and all three
runs ended "AI check: exit 1" from Anthropic and Perplexity HTTP 429s (the stagger fix's BUGLOG
row). The stagger fix gives each site its own start minute. But `man launchd.plist` says that,
unlike cron, launchd "will start the job the next time the computer wakes up", so every site
whose start time passed during sleep starts on the same wake. And sites at one day and hour start
15 minutes apart for the first four (:00, :15, :30, :45), at least 5 minutes apart up to twelve,
and a 13th shares :00; a full run takes 9 to 13 minutes (below), so a run can still reach the next
site's start. So two sites' AI checks can still run together.
This change makes them take turns.

## How

**Where.** In `geo_check.py`'s `run()`, not in `track.sh`: that is the code that calls the
engines, so a run by hand (`geo_check.py <site>`, with or without `--engines`) takes turns with a
scheduled one too. The lock is taken after the checks for keys and questions and before the
run's id and date are set (`new_run_id()`, `today`), so a run that waited is stamped with the time
it really ran; and only when at least one
engine the run will ask (all engines, or those `--engines` names) is usable for this site and
the site has at least one question. Then a site with the AI check not set up (exit 3), no key,
no question, or only engines it cannot use never waits. `--trend`, `--report` and the set-up
commands never reach `run()`.

**How it locks.** `fcntl.flock(LOCK_EX | LOCK_NB)` on `~/.config/gsc-insights/geo/ai-check.lock`,
opened with `open(path, "a")` after `geo_dir().mkdir(parents=True, exist_ok=True)`: the pattern
`append_history` and `fix_proposal.locked` already use (`geo_check.py` imports `fcntl` today). The
kernel drops the lock when the process ends, however it ends, so a crash or a kill leaves no stale
lock (T3 shows it). Held until `run()` returns. Lock order: this lock is always the outer one; it
is never waited for while another lock is held, and the history lock (`append_history`) is taken
only inside it, after the engine calls. A code comment states this.

**Waiting.** Only `BlockingIOError` means another run holds it. Then print one line, flushed at
once (the plist sends stdout to the site's log file, `StandardOutPath` in `schedule_tracking.sh`,
so Python would otherwise hold it back until the run ends):
"waiting for another AI check run to finish, one at a time (at most N min) …", with N the real
limit (in seconds when under a minute, as with the test knob; the same for every duration this
change prints). The run holding the lock may be another site's or this site's own. Retry every 5
seconds. Once it has the lock, print how long it waited. The wait is
counted with `time.monotonic()`. On this Mac's Python (3.13.16) `time.get_clock_info("monotonic")`
names `mach_absolute_time()`. Apple's page for it says "this clock does not increment while the
system is asleep" (https://developer.apple.com/documentation/kernel/1462446-mach_absolute_time,
read 2026-10-18 through the page's data file, `developer.apple.com/tutorials/data/documentation/kernel/1462446-mach_absolute_time.json`; its sister
`mach_continuous_time` says "including while the system is asleep"), so a wait does not run out
during sleep. (If it did count sleep, a waiter woken after a long sleep would give up at once and
run beside the other run; that is why the clock matters.)

**The longest wait: 90 minutes.** Measured on this Mac: first and last file times in each run's
answer folder (`~/.config/gsc-insights/geo/answers/<site>/<run id>/`), and the run's rows in
`geo/geo_history.csv` by status. Sites A to C are one owner's own sites, named only by letter in
this public repository.

| Run id (site) | Started → last answer | Rows by status | Ran beside |
|---|---|---|---|
| `20261018T065901Z-512486-24737-fb36` (croftweaver.com) | 10-18 08:59 → 09:11 | 27 ok | nothing (no other run that day) |
| `20261012T070011Z-870033-29353-9b5d` (site A) | 10-12 09:00 → 09:10 | 26 ok, 1 partly failed | sites B and C |
| `20261012T070010Z-174318-29336-a2f8` (site B) | 10-12 09:00 → 09:10 | 25 ok, 2 partly failed | sites A and C |
| `20261012T070009Z-388234-29332-848e` (site C) | 10-12 09:00 → 09:13 | 24 ok, 2 partly failed, 1 "no AI Overview shown" (an answer, not a failure) | sites A and B |
| `20261005T070010Z-474675-9741-f2a6` (site A) | 10-05 09:00 → 09:09 | 27 ok | sites B and C |
| `20261005T070010Z-469282-9740-c803` (site B) | 10-05 09:00 → 09:10 | 26 ok, 1 partly failed | sites A and C |
| `20261005T070009Z-087498-9733-6a8d` (site C) | 10-05 09:00 → 09:11 | 27 ok | sites A and B |
| `20261004T195238Z-361168-92352-bc4d` (site A) | 10-04 21:52 → 21:59 | 18 ok (fewer questions) | site C, and site B for its last 2 min |

So a full run takes about 9 to 13 minutes. 90 minutes lets six to nine such runs go first. A
slow week can take longer: each engine may use up to `ENGINE_BUDGET` (400 s) before its next call
is refused, about 27 minutes for the four chat engines and 40 with Google's two, so with four
sites on one wake the fourth could wait past 90 minutes and run anyway, which it reports (below).
And there is no hard upper bound on a run: `_send`'s timeout limits each read, not a whole
call, so a reply that trickles in can run past an engine's budget. The limit exists for that case
and for a hung run. The number is a judgment on those measurements.

**When the wait runs out.** The run goes ahead without the lock and adds "waited N min for
another AI check run, then ran anyway, so answers may hit the engines' rate limits" to its
problems. `run()` prints its problems at the end (once) and returns 1, so `track.sh` lists
"AI check: exit 1" under "This run needs attention". Going ahead keeps the week's data when the
other run is hung; skipping would lose it for sure. If the lock file cannot be opened or
`flock` fails with any other `OSError`, the same: go ahead, with a problem naming the error.

**Test-only knobs.** `GEO_LOCK_WAIT` (seconds) and a 0.1 s retry, honoured only with
`GEO_TEST_MODE=1`, like `override()`. No setting for owners.

## How it is tested

New file `tests/test_ai_lock.py`. It uses `_geo_stub` and the shim from `test_track_entry.py`
(both sites share one temporary HOME, so they share the lock). It imports only `SHIM` from
there, never the `TrackEntry` class, which would make unittest run those tests twice. The stub also records each engine
request's start time, end time and question in a new list (`STATE["spans"]`), leaving the `hits`
tuples as they are.

- **T1, the production call.** Two sites, each with its own question. Every engine reply waits
  for a gate the test opens only once one run prints the waiting line, so the two runs contend
  however slowly either starts (DIFF round 1). Start both sites' `track.sh` at once with `/bin/bash`, as the plist that
  `schedule_tracking.sh` writes does (`ProgramArguments`: `/bin/bash`, `track.sh`, the domain, …). Pass when every request of one site ends
  before the first request of the other starts, both runs exit 0, and one log says it waited.
  Shown to fail with the lock taken out (recorded in the review trail, not committed).
- **T2, the wait runs out.** The test holds the lock itself; `GEO_LOCK_WAIT=1`; `track.sh` still
  asks the engines, prints the problem line once, lists "AI check: exit 1" and exits 1.
- **T3, no stale lock.** A child process takes the lock and prints "locked"; the test waits for
  that line and checks that its own `LOCK_NB` try raises `BlockingIOError`, then kills the child
  with SIGKILL. The next run with `GEO_LOCK_WAIT=30` starts at once (no waiting line, done in well
  under 30 s).
- **T4, no wait for nothing.** The test holds the lock and sets `GEO_LOCK_WAIT=5` and a subprocess
  timeout, so a run that wrongly waits fails in seconds, not 90 minutes. Each of these exits at once without the
  waiting line: a site with no AI check set up (exit 3); a set-up site with no key; one with no
  question; and a site with a question and a usable key for one engine, run with `--engines`
  naming only another engine, which has no key. That last case fails if the check ignores
  `--engines` (the usable engine would make it wait), and the test is shown to fail that way.
- **T5, an unopenable lock file.** `ai-check.lock` is a directory (so `open(path, "a")` raises
  `IsADirectoryError`); with the same short wait and timeout as T4, the run asks the engines,
  lists the problem and exits 1.
- **T6, the waiting line reaches the log at once.** The test holds the lock and starts `track.sh`
  with stdout going to a file, as the plist's `StandardOutPath` does. The waiting line is in the file within a few
  seconds, while the test still holds the lock; the test then lets go and the run ends with exit
  0 and no problem.

`make check` and `make test` stay green.

## What else changes (step 5, after #354 merges)

- `SKILL.md`, "Weekly auto-tracking": #354's sentence about a sleeping Mac ("A Mac asleep at those
  times still starts every missed job together when it wakes") gains "their AI checks then take
  turns, each waiting up to 90 minutes".
- `references/geo-check.md`, Quick path item 2 and set-up step 5 ("Run it once"), where it tells
  the assistant to run `geo_check.py` on demand: start that run in the background, because it may
  wait behind a weekly job (the waiting line says so) longer than a tool call lasts. Do not start
  a second run of the same site while one is waiting: the first still runs, and a second costs
  the same engine calls again.
- `docs/BUGLOG.md`: the 2026-10-18 follow-up row is closed, naming the PR and the tests.
- `docs/WHAT-THE-SKILLS-RUN.md` needs no change: its table (line 306) lists `geo/`, where the
  lock file lives.

## Not in scope

GSC and Bing calls (the 429s came from the AI engines); a lock per engine (one lock is simpler);
retrying a 429 inside `geo_check.py`; a `--no-wait` flag for runs by hand.
