# Plan: `npm run ship` names the site first, and asks for a yes at a terminal

Base `origin/main` 6859448c (`ship.sh` and `check_ship_push.sh` at template-version 0.24) · branch
`claude/peaceful-gates-cde640` · review depth: High (the starter's publish script; the skill's High
row names deploy code) · red team: none (the change reads a config file, git's `origin` setting and
the keyboard; a "no" only stops earlier; nothing is deleted, logged in to or moved).

| Step | What | State | Evidence |
|---|---|---|---|
| 1 | This plan | written 2026-11-08 | this file |
| 2 | PLAN gate, High | CLEAN 2026-11-08: 9 rounds, a final full read, a closing re-gate | `docs/reviews/REVIEW-plan-2026-11-08-claude-peaceful-gates-cde640-3ecc8f6.md` |
| 3 | `ship.sh`: first line, the question, markers 0.25 | built in the build session; fromGitHub reads the site from GitHub's commit (DIFF r1, Codex BUG) | see step 6 |
| 4 | `check_ship_push.sh`: the cases below, marker 0.25; `template-tests.yml`: `SHIP_TEST_TTY` | built; T8 bound 30 s (15 s missed under load) | see step 6 |
| 5 | `PUBLISHING.md` sentence, BUGLOG release-notes row | not started | — |
| 6 | `make check`, mutation check, DIFF gate at High, then PR | not started | — |

## What and why

On 2026-11-07 the owner ran `npm run ship` in the wrong site's folder, typed by hand at a terminal
(the output pasted into the session shows the shell prompt in that folder). This time it did no
harm: that site's live branch already held its `main` (GitHub's record shows its last push came at least 85
minutes before the run), so the push printed `Everything up-to-date`. Had that `main` held unpublished
work, the run would have taken it live. The script printed the site's address only at the end, in
the live-site check. That is one incident, with no damage; the question below would have
named that site and waited for a yes. Anyone with more than one site folder can do the same, so the change is right for every owner, not only this
one.

Two changes, both in `skills/new-website/templates/astro/scripts/ship.sh`:

1. **The first line names the site**, before any check, fetch or lock.
2. **At a terminal, the run asks for a yes before anything is published.** Without one (an
   assistant's run, CI), it does not ask: it prints one line saying so, and goes on as today.

**This reverses part of an earlier decision.** The 2026-11-02 plan
(`docs/reviews/SKILL-PLAN-ship-lists-commits.md`, line 29) refused a "continue?" prompt because "it
would break a publish run without a terminal". This plan keeps that reason intact: a run without a
terminal is never asked and never waits. But it does add the prompt that plan turned down, for
every run at a terminal. The owner decided it on 2026-11-08 ("Start it and add it", on the verdict
"ship names the site and asks for a yes only at a terminal").

## How

**A. Two reads, as functions**, next to `log_view`:
- `site_of <folder>`: the `site:` address in `<folder>/astro.config.mjs`, trailing slash removed,
  empty if none. It is today's read at line 753, moved into the function word for word and kept
  as an assignment, `s="$(grep … | head -1 || true)"`, then `printf '%s\n' "${s%/}"`. The
  `check_pipefail_pipes.sh` allow-list entry matches the fixed text ` | head -1 || true)"` on the
  flagged line, so it still matches its one site; a bare pipeline as the function's body would
  lose the `)"` and fail the entry as stale. Line 753 becomes `site="$(site_of "${wt:-.}")"`, and
  the slash strip after it (line 758) goes, its comment (754–757) moving into `site_of` with the
  strip, so one slash is stripped as today: `site: 'https://a//'` still asks for
  `https://a//build.txt`. The comment's last clause, "same as the llms-coverage guard applies",
  is dropped in the move: that guard strips every trailing slash, this one strips one. The live
  check is otherwise unchanged.
- `site_count <folder>`: `none`, `one` or `many`, from every match of the same pattern in that
  file (`h="$(grep -oE … 2>/dev/null || true)"`, no pipe), read with
  `case "$h" in '') none;; *$'\n'*) many;; *) one;; esac`. It counts matches, not lines, so an old
  address kept in a comment counts whether it sits on its own line or beside the live one. The
  starter's own `astro.config.mjs` gives `one`, `https://example.com` (READ 18). With `many`, `site_of` may return the commented one, so the first line and the
  question name no address then (fallback below) rather than a possibly wrong one.
- `repo_of_origin`: the address `git push origin` uses, which is `origin`'s push address when one is
  set: `git remote get-url --push --all origin 2>/dev/null || true`. More than one line (several
  push addresses) gives a fallback, and so does an address holding `?` or `#` (a query or fragment
  can carry a token, and a token can hold `/`). Otherwise a trailing `/` is removed, then `.git`,
  then the end
  is matched with `sed -nE 's#^.*[:/]([A-Za-z0-9._-]+/[A-Za-z0-9._-]+)$#\1#p' <<<"$url"` (a
  here-string, not a pipe). Only `owner/name` made of those characters is printed, so
  `git@github.com:owner/site.git`, `ssh://git@github.com/owner/site.git` and an `https` address
  with a user name and token before the host all give `owner/site`. Anything else gives the
  fallback and prints nothing of the address: a query or fragment, a user part with no owner after
  the host, no `owner/name` at the end, or no `origin`.

**B. The first line** goes right after `self_blob` is read (that read must stay first, line 360),
before the `ship.fromGitHub` check, in both modes:

    → Site: https://example.com · GitHub repo: owner/site

With no address: `Site: (no site: address in astro.config.mjs)`. With more than one `site:` address:
`Site: (more than one site: address in astro.config.mjs — check which one is live)`. With no usable
push address: `GitHub repo: (no 'origin' remote with a plain owner/name address)`. The run goes on either way, as it
does today: a missing `origin` still stops at the fetch with that step's own message.

**Superseded in worktree mode (DIFF r1, Codex BUG; planner's call):** with `ship.fromGitHub` on, the
line waits for the fetch and reads GitHub's commit (`git show <id>:astro.config.mjs`, through the
same `site_of`), because that is the copy that goes live; with no site there, the fallback text, never
this folder's file. Folder mode is as written below.

It reads this folder's `astro.config.mjs`; the line does not say which copy it read. In worktree
mode the published copy differs whenever the `site:` line differs between this folder and GitHub's
`main` (for example an edit here, committed or not, that is not on GitHub's `main`, or a change on
GitHub not yet pulled here); the live check at line 753 still reads the published copy. What goes live is decided by the push address, which the line names; the site
address is the name a person recognises. The address is already
printed today, unfiltered, by every run that reaches the live check. A run that stops earlier now
prints it too, with `owner/name`, on the owner's own screen or log; nothing else is printed.

The mode line ("→ Publishing main → production." or "→ Publishing GitHub's main as of the fetch
(<id>) …") now follows the first line, with anything that prints before it today (a lock
refusal, a fetch retry) still before it, and the leftovers report still after it (line 539);
the new `mode_has` helper (below) finds it as the
first line starting `→ Publishing`, wherever it sits. The comment at lines 531–532 ("so the first and the last line
name the commit") changes to "the mode line and the last line".

**C. The question.** It goes after the "Going live" list or the "Nothing new goes live" line,
right after the `fi` that ends them (line 602), before
worktree mode makes its temporary copy, so before `npm ci`, the gate and the push, in both modes.
The answer rests on the repo in the first line and the commits in the list, which are what goes;
the site address is this folder's copy of it, which in worktree mode may differ (B). With nothing
new (`live_n` 0) it still asks, because the checks and the push still run; one rule is simpler.

- **When standard input and standard output are both terminals** (`[ -t 0 ] && [ -t 1 ]`): print,
  with no newline,

      Publish to https://example.com (owner/site)? Type y and press Enter to go on, anything else stops:

  (with the first line's fallback text, without its own parentheses, in place of either name). Read one line with `read -r answer`
  (default `IFS`, so spaces around the answer go). `y` or `yes`, in any case, goes on, matched with
  `case "$answer" in [yY]|[yY][eE][sS])`, since bash 3.2 has no `${answer,,}`; anything
  else, an empty line, or the end of input (Ctrl-D) stops with
  `✗ Publish stopped — you did not answer y. Nothing was published and $here.` and exit 1.
- **Otherwise:** `→ No terminal to answer a question here (input or output is not a terminal
  window), so this run does not ask.` and the run goes on.
- **Why standard output too:** with output sent to a file the question would be invisible and the
  run would sit silent. Checked 2026-11-08: under `npm run` (npm 11.20.0) a terminal's standard
  input and output both still reach the script as terminals, and with `> file` only output stops
  being one (READ 16); Claude Code's shell and `codex exec` (0.167.0) both have no terminal on
  either.
- **A stop while it waits.** Measured 2026-11-08 under `script`, with bash 3.2.57 and 5.3.20: a
  terminate or interrupt sent to bash leaves a waiting `read` waiting, even with the run's trap
  set, until a line or the end of input arrives. A `read -t` loop does not help: bash 3.2 returns 1
  on a timeout, the same as the end of input. A trap that itself exits does work: it ran at once in
  both versions, and the EXIT trap ran after it. So, for the question only, in this order:
  `trap 'stop_asked=1; stop_point "Nothing was published and $here."' INT TERM HUP QUIT`; then
  `stop_point "Nothing was published and $here."`, as before every step, for a stop that came
  earlier; then the question and the read; then `trap 'stop_asked=1' INT TERM HUP QUIT` again.
  Setting the trap first leaves no moment in which a stop lands and the read still waits. `stop_point` prints the stop message
  and sets `stop_said`, so `on_exit` does not print it twice.
- The read sits in `if read -r answer; then :; else answer=""; fi`, so `set -e` never ends the run
  on the end of input.
- In worktree mode the run holds the clone's lock while it waits, so another run in that clone
  meanwhile stops with "another publish holds this clone's lock". Its line "That process is still
  running, so a publish is under way. Let it finish" (line 163) gains "(it may be waiting for a yes
  in another window: answer or stop it there)". `on_exit` removes the lock and the empty temp folder after a "no", as after
  any early stop.

**D. Markers:** `template-version: 0.25` in `ship.sh` and in `tests/check_ship_push.sh`. The 0.24
release-notes row (BUGLOG, 2026-11-02) is still open; if no release comes between, the notes say
0.25 and cover both.

**Also, at build:**
- `skills/new-website/templates/PUBLISHING.md`, after "Before it uploads, it lists the commits that
  go live, newest first." (line 61): "It names the site first. Run in a terminal window with its
  output on screen, it then asks you to type y before it uploads. Where it has no terminal window
  to ask in, or its output goes to a file, it says it is not asking and goes on."
- `docs/BUGLOG.md`: a "Next release notes" row: both files are 0.25 and go together; what the first
  line and the question do; a run with no terminal window, or with its output in a file, is not
  asked and says so; `PUBLISHING.md` gained one
  sentence.
- `scripts/whats-new.sh` needs no change: `TEMPLATE_TRACKED` (line 80) already names `ship.sh`, the
  tests folder and `PUBLISHING.md`. Each site takes 0.25 through `whats-new`, in its own pull
  request; that is not part of this change.

**Not in this change:** a setting to skip the question, a timeout, or a check that the folder is
the one the owner meant. `AGENTS.md` needs nothing: an assistant still runs `npm run ship` only when
asked, and a run without a terminal says it was not asked.

## How it is tested

All in `tests/check_ship_push.sh`, through the real `ship.sh` started as `npm run ship` starts it
(`bash scripts/ship.sh`). Expected values are written from each fixture's own address, `origin` and
commits, never copied from a run's output.

Every nested run today (stub `expect`, real-git `run_ship` and `start_bg`) sends its output to a
log, so none is asked, even when the file is run by hand at a terminal; the file needs no change for
that.

**Three existing checks move.** `first_has` (lines 980, 1065, 1453, 1592) reads the first line,
which is now the site line. A `mode_has` helper reads the first line that starts with
`→ Publishing`, and the three checks use it; `first_has` stays for the new line-1 checks.

**Stub half.** The stub learns `remote get-url --push --all origin`, answering
`git@github.com:owner/site.git`, and refuses any other `remote` form loudly, as it already refuses
commands it does not know (a `noorigin` marker makes it and the fetch fail as a missing remote
does; an `originurl` file replaces the answer, one address per line). A variable `want_line1`,
set before each `expect` call (its fifth argument is already the extra-PATH folder), holds the
case's expected line 1, default
`→ Site: (no site: address in astro.config.mjs) · GitHub repo: owner/site` (the scratch folder has
no `astro.config.mjs`, on purpose), and asserts it for every case; every case that printed "Going
live" or "Nothing new goes live" also printed the no-terminal line, and no "Publish to". The line-1
and no-terminal-line checks are wording checks, so `SHIP_GATE_SKIP_WORDING` skips them as it skips
the others. Exit codes, push counts and the leak checks (no `s3cret`, no `old.example`, no
`example.invalid`) are asserted either way. Each new case that gets past the fetch gives its one
push an `attempt` (line 198) of `Everything up-to-date`, exit 0, and expects exit 0 and one push.
New cases:
- `noorigin`: stops at the fetch; line 1 still the site line, ending in the repo fallback.
- `tokenurl1`: an `https` address with `user:s3cret` before the host and `owner/site.git` after:
  line 1 ends `owner/site`; no line of the output holds `s3cret`.
- `tokenurl2`: the user part with `s3cret` and only `site.git` after the host: the fallback, no
  `s3cret`.
- `queryurl`: `https://example.invalid/owner/site.git?token=/s3cret/value`: the fallback, no
  `s3cret`.
- `fragurl`: `https://example.invalid/owner/site.git#/s3cret/value` (the `/` after `#` matters:
  without it the address falls back even with the refusal gone): the fallback, no `s3cret`.
- `twopush`: two addresses in `originurl`: the fallback.
- `oddurl`: `https://example.invalid`: the fallback, and `example.invalid` in no line.
- `twosite1`, `twosite2`: an `astro.config.mjs` holding an old address in a comment, first, and
  the live one after it, on two lines and on one line (`/* site: '…old…' */ export default { site: '…new…' };`). Each
  also carries the `noorigin` marker, so it stops at the fetch and never reaches the live check,
  which would read the old address; the file is written for the case and removed after it, since
  the other cases rely on the folder having none. Line 1 is both fallbacks; `old.example` in no
  line.

**Real-git half.** The fixtures already hold `site: 'https://ship-test.example.invalid'` (line 949)
and `origin` at `$D/origin.git`, so line 1 is
`→ Site: https://ship-test.example.invalid · GitHub repo: <case>/origin`, with the case's own
lowercase name (`s2/origin`). S2 asserts it as line 1 (worktree mode), P4 (folder mode) with its
own domain; S2 also asserts the no-terminal line comes
after "Going live" and before "▶ pre-push gate".

**A fake terminal.** A helper `run_tty <case> <answer|--eof|--stop|--none> [--prog FILE] [--out FILE]
[--limit S] [VAR=value…]` starts ship.sh, with the same stub `bin` folder first on `PATH` as `run_ship`
(line 1009),
under `script`: macOS's BSD form `script -q /dev/null <command>`, util-linux's form
`script -qec 'exec <command>' /dev/null`, told apart by `script --version` (util-linux has it;
BSD prints "illegal option", measured). Measured: both forms pass their input to the program, and the
program reads an end of input once `script`'s own input ends (BSD on macOS, READ 1; util-linux
2.38.1 on Debian 12, READ 13). So a feeder waits, with a limit,
until the question is in the log, writes the answer, then holds its input open until ship.sh exits;
its waits use `$SHIP_T_REAL_SLEEP`, never a `sleep` found on `PATH`, which in these cases may be
the stub that returns at once (an answer written before the read is lost under BSD `script`,
READ 1).
ship.sh is started through the same pattern as `expect`'s wrapper (line 236), with the pid file
passed as an argument so it lands outside the clone: `bash -c 'echo "$$" > "$1"; exec bash "$0"'
scripts/ship.sh "$G/<case>.pid"` (`--prog FILE` puts another script in place of
`scripts/ship.sh`; `--out FILE` adds `> "$2"` to the `exec` and passes FILE as a second argument,
so standard output goes to that file and not to `script`). A file in the clone would fail the folder-unchanged check and, in
folder mode, stop the run as unsaved. Under `script` the program leads its own process group, so the
pid is also the group: BSD `script` runs the command itself (READ 11), and util-linux runs it
through `sh -c`, so that form starts with `exec` (READ 13: with it, pid and group match; without
it, the group is the shell's). A watchdog gives each case 60 seconds (`--limit` changes it), and bounds
the feeder's wait too: past the limit it sends a terminate to the group and to `script`, polls
`kill -0` on both for up to 5 seconds, then kills what is left outright, the group and `script`
(util-linux `script` outlives a terminate, READ 13; BSD's exits on it), waits for `script`
(ship.sh is not the test shell's child, so it is polled, not waited for), and returns 124. A
broken case cannot hang the file. `run_tty` sets `fail` only for a misuse of its own options: T1 to T7 count 124 as a fail,
and T8 expects it. Output comes back with `\r\n`; the helper strips
`\r` before any check. The T cases run only when `SHIP_TEST_TTY=1` is set, and there a missing
`script` fails the file with one line naming the T cases and `SHIP_TEST_TTY`, as S10 (e) does for
`SHIP_TEST_REQUIRE_BASH32` (line 841). The build PR's own CI run shows whether `ubuntu-latest` has
`script` (not checked here) before anything merges. The build changes `.github/workflows/template-tests.yml` so that the two
steps that run the file directly set it: the playwright job's (line 94, Linux; its comment's
"fails within a minute or so" is dropped, since each hung T case takes its 60-second limit) and the Mac bash 3.2
step (lines 303–311, in prepare-any-shell's macOS leg). Everywhere else the file runs, the T cases
print one line saying they are skipped and run nothing: a copied site's pre-push hook
(verify-windows' pushes and each owner's own pushes) and each site's own CI
(`templates/astro/.github/workflows/ci.yml` line 129). So an owner's push never depends on their
machine's `script`, and the T cases add no time to it; the question itself needs no `script`, only the T cases do.
The toolkit's CI tests the same `ship.sh` every site gets through `whats-new`.
- T1 (worktree mode, `advance 1`, so something new goes live) answers `y`: the "Going live" header comes before `Publish to
  https://ship-test.example.invalid (t1/origin)?`, which comes before "▶ pre-push gate"; the run
  ends on the LIVE line, exit 0; production is now main.
- T2 (worktree mode, one unsaved file in the folder) answers `n`: exit 1; `you did not answer y`
  and `Nothing was published`; production unchanged; no "▶ pre-push gate"; the stubbed `npm` was
  never called; no "Not published" line (that list prints only after the temporary copy is made, so
  this pins the question before it).
- T3 answers an empty line, T4 sends the end of input: each as T2.
- T5 `--stop`: once the question is in the log, a terminate to ship.sh's bash (the pid from the
  wrapper, then polled with `kill -0` until it is gone). Exit 1 within the
  limit, the stop message, `Nothing was published`, and no `you did not answer y` (without the
  prompt-time trap the run keeps waiting, and the case fails as timed out).
- T6 (folder mode) answers ` YES `: goes on, ends on the LIVE line. Its files are dated in the past
  and the index refreshed first, as the folder-mode site case does (lines 1583–1586), so ship.sh's
  own `git status` leaves the index unchanged.
- T7: `run_tty t7 --none --out "$G/t7.out"`, a terminal on standard input and output sent to a
  file outside the clone (`G` is not exported, so the path goes as an argument): its feeder waits for no question and
  only holds the input open. No question, the no-terminal line in the file, the run goes on.
- T8, the watchdog itself: `run_tty t8 --none --prog "$G/t8-stand.sh" --limit 3`, the stand-in a
  script under `$G` (outside the clone) that ignores terminate and hang-up, starts a child that
  sleeps and writes the child's pid to `$G/t8-child.pid`, and sleeps, both through `$SHIP_T_REAL_SLEEP` (the stub `sleep` first on `PATH` returns at
  once, line 896); the watchdog times with the real `sleep` too: `run_tty` returns 124
  within 30 seconds, and both the stand-in and its child are gone.
- Under `SHIP_GATE_SKIP_WORDING` the T cases cannot find the question by its text, so they print
  that they are skipped; no CI step sets it.
- Every T case also passes `run_ship`'s checks (folder unchanged, nothing left behind).
- The file's last line names the new checks.

**Mutation check**, on the built commit, as the 0.24 build ran it: a small script applies each
mutation to a copy and runs this file, with `SHIP_TEST_TTY=1`, under a time limit (the `mutation-check` skill has no runner
for a bash test file). Each must fail a case:
always take the no-terminal branch (T1, T2); ask on `[ -t 0 ]` alone (T7); accept any answer (T2);
accept only lower case (T6); drop the prompt-time trap (T5); move the question after `npm ci` (T2)
or after the push (T2); move the first line after the fetch (`noorigin`, which stops there); read
the fetch address, not the push address (every stub case: the stub refuses that form); accept
several push addresses (`twopush`); drop the `?`/`#` refusal (`queryurl`, `fragurl`); print the raw address (`tokenurl1`); widen the
class to `[^/:]` (`tokenurl2`); drop `-n`/`p` from the `sed` (`oddurl`); count lines, not matches (`twosite2`); drop the count
(`twosite1`, `twosite2`); drop the watchdog's outright kill (T8: the stand-in is still running; BSD `script` exits on
terminate, so nothing hangs); kill the pid, not the group (T8, with the stand-in starting a child
that sleeps, which must be gone too); drop the lock message's addition (the "under way" cases at lines 1169 and 1209, which
gain a check for the new words).

## Not covered, said plainly

- An assistant whose shell does have a terminal (Codex's interactive app may run commands in one;
  not checked) is asked. It may type `y` itself, or it may not be able to type and wait until its
  tool stops the run. Stopped with a signal, the prompt-time trap ends it with "Nothing was
  published"; killed outright, it leaves the worktree-mode lock, which the next run reports as
  stopped hard. Either way the question comes before the push, so nothing is published; how each
  assistant stops a command was not checked. The question guards against a person in the wrong folder, not against an
  assistant.
- A config whose only matching `site:` text is a comment (the live address set from a variable,
  or none) gives that commented address; the live check at line 753 already reads the same text
  today.
- Ctrl-C from a real keyboard through `npm` was not measured; the measurement sent the signal to
  bash's own process. The script's existing stops rely on the same delivery.
- util-linux `script` was measured offline on Debian 12's 2.38.1 (READ 13), not on the CI image's
  own version; the CI step that sets `SHIP_TEST_TTY` shows it at build. The T cases do not run on
  owners' machines or in site CI, so a `ship.sh` a site edits by hand loses their cover there.
- Windows: whether Git Bash reports a terminal was not checked. If it reports none, the run says so
  and goes on as today; if a session's shell reports one, the run waits and publishes nothing. Both
  wrong guesses are safe ones.
