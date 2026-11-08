# Plan: `npm run ship` names the site first, and asks for a yes at a terminal

Base `origin/main` 6859448c (`ship.sh` and `check_ship_push.sh` at template-version 0.24) · branch
`claude/peaceful-gates-cde640` · review depth: High (the starter's publish script; the skill's High
row names deploy code) · red team: none (the change reads a config file, git's `origin` setting and
the keyboard; a "no" only stops earlier; nothing is deleted, logged in to or moved).

| Step | What | State | Evidence |
|---|---|---|---|
| 1 | This plan | written 2026-11-08 | this file |
| 2 | PLAN gate, High | not started | — |
| 3 | `ship.sh`: first line, the question, markers 0.25 | not started; waits for the owner's go | — |
| 4 | `check_ship_push.sh`: the cases below, marker 0.25 | not started | — |
| 5 | `PUBLISHING.md` sentence, BUGLOG release-notes row | not started | — |
| 6 | `make check`, mutation check, DIFF gate at High, then PR | not started | — |

## What and why

On 2026-11-07 the owner ran `npm run ship` in the wrong site's folder. It published that site's
`main`, which took a merged pull request live (only hidden attributes changed). The script printed
the site's address only after the push, in the live-site check. That is one incident. Anyone with
more than one site folder can do the same, so the change is right for every owner, not only this
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
  empty if none. It is today's read at line 753, moved into the function word for word, so the
  `check_pipefail_pipes.sh` allow-list entry for its `| head -1 || true)"` still matches its one
  site. Line 753 becomes `site="$(site_of "${wt:-.}")"`; the live check is unchanged.
- `repo_of_origin`: `git remote get-url origin`, then `.git` and a trailing `/` removed, then the
  last two path parts (`sed -nE 's#^.*[:/]([^/:]+/[^/:]+)$#\1#p'`). So
  `git@github.com:karero/site.git` and `https://user:token@github.com/karero/site.git` both give
  `karero/site`, and a token in the address is never printed. Empty when there is no `origin` or
  the address has no `owner/name` at its end.

**B. The first line** goes right after `self_blob` is read (that read must stay first, line 360),
before the `ship.fromGitHub` check, in both modes:

    → Site: https://example.com · GitHub repo: karero/site

With no address: `Site: (no site: address in astro.config.mjs)`. With no usable `origin`:
`GitHub repo: (no 'origin' remote with an owner/name address)`. The run goes on either way, as it
does today: a missing `origin` still stops at the fetch with that step's own message.

It reads this folder's `astro.config.mjs`. In worktree mode the published copy may differ; that
copy is still what the live check reads at line 753. What goes live is decided by `origin`, which
the line names exactly; the address is the name a person recognises. The address is already
printed today, unfiltered, by every run that reaches the live check, so the line adds no new
exposure.

The mode line ("→ Publishing main → production." or "→ Publishing GitHub's main as of the fetch
(<id>) …") becomes the second line. The comment at lines 531–532 ("so the first and the last line
name the commit") changes to "the mode line and the last line".

**C. The question.** It goes after the "Going live" list and its blank line (line 602), before
worktree mode makes its temporary copy, so before `npm ci`, the gate and the push, in both modes.
The answer rests on what goes: the site in the first line and the commits in the list. With nothing
new (`live_n` 0) it still asks, because the checks and the push still run; one rule is simpler.

- `stop_point "Nothing was published and $here."` first, as before every step.
- **When standard input and standard output are both terminals** (`[ -t 0 ] && [ -t 1 ]`): print,
  with no newline,

      Publish to https://example.com (karero/site)? Type y and press Enter to go on, anything else stops:

  (with the first line's fallbacks in place of either name). Read one line with `read -r answer`
  (default `IFS`, so spaces around the answer go). `y` or `yes`, in any case, goes on; anything
  else, an empty line, or the end of input (Ctrl-D) stops with
  `✗ Publish stopped — you did not answer y. Nothing was published and $here.` and exit 1.
- **Otherwise:** `→ No terminal to answer a question here (an assistant's or CI's run, or output
  sent to a file), so this run does not ask.` and the run goes on.
- **Why standard output too:** with output sent to a file the question would be invisible and the
  run would sit silent. Checked 2026-11-08: under `npm run` (npm 11.20.0) a terminal's standard
  input still reaches the script; Claude Code's shell and `codex exec` (0.167.0) both have no
  terminal on either.
- **A stop while it waits.** Measured 2026-11-08 under `script`, with bash 3.2.57 and 5.3.20: a
  terminate or interrupt sent to bash leaves a waiting `read` waiting, even with the run's trap
  set, until a line or the end of input arrives. A `read -t` loop does not help: bash 3.2 returns 1
  on a timeout, the same as the end of input. A trap that itself exits does work: it ran at once in
  both versions, and the EXIT trap ran after it. So, for the read only:
  `trap 'stop_asked=1; stop_point "Nothing was published and $here."' INT TERM HUP QUIT`, then
  `trap 'stop_asked=1' INT TERM HUP QUIT` again right after. `stop_point` prints the stop message
  and sets `stop_said`, so `on_exit` does not print it twice.
- The read sits in `if read -r answer; then :; else answer=""; fi`, so `set -e` never ends the run
  on the end of input.
- In worktree mode the run holds the clone's lock while it waits, so another run in that clone
  meanwhile stops with "another publish holds this clone's lock". That is true and needs no change.
  `on_exit` removes the lock and the empty temp folder after a "no", as after any early stop.

**D. Markers:** `template-version: 0.25` in `ship.sh` and in `tests/check_ship_push.sh`. The 0.24
release-notes row (BUGLOG, 2026-11-02) is still open; if no release comes between, the notes say
0.25 and cover both.

**Also, at build:**
- `skills/new-website/templates/PUBLISHING.md`, after "Before it uploads, it lists the commits that
  go live, newest first." (line 61): "It names the site first, and when you run it yourself it asks
  you to type y before it uploads."
- `docs/BUGLOG.md`: a "Next release notes" row: both files are 0.25 and go together; what the first
  line and the question do; an assistant's run is not asked and says so; `PUBLISHING.md` gained one
  sentence.
- `scripts/whats-new.sh` needs no change: `TEMPLATE_TRACKED` (line 80) already names `ship.sh`, the
  tests folder and `PUBLISHING.md`. Each site takes 0.25 through `whats-new`, in its own pull
  request; that is not part of this change.

**Not in this change:** a setting to skip the question, a timeout, or a check that the folder is
the one the owner meant. `AGENTS.md` needs nothing: an assistant still runs `npm run ship` only when
asked, and its run says it was not asked.

## How it is tested

All in `tests/check_ship_push.sh`, through the real `ship.sh` started as `npm run ship` starts it
(`bash scripts/ship.sh`). Expected values are written from each fixture's own address, `origin` and
commits, never copied from a run's output.

**The file's own standard input becomes `/dev/null`**, one line near its top (`exec </dev/null`;
the `exec` ban at line 818 reads `ship.sh`, not this file). Today every nested run (stub `expect`,
real-git `run_ship` and `start_bg`) inherits it; run by hand at a terminal, or from a site's
`npm run verify`, each would stop at the question and wait. One line covers every case, a new one
included. No mutation can show it (the check runs with no terminal), so at build the whole file is
also run once under `script` and must finish; the PR records that run.

**Three existing checks move.** `first_has` (lines 980, 1065, 1453, 1592) reads the first line,
which is now the site line. A `mode_has` helper reads the first line that starts with
`→ Publishing`, and the three checks use it; `first_has` stays for the new line-1 checks.

**Stub half.** The stub learns `remote get-url origin`, answering `git@github.com:owner/site.git`
(a `noorigin` marker makes it exit 2, an `originurl` file replaces the answer). `expect` asserts, for
every case: line 1 of the output is exactly
`→ Site: (no site: address in astro.config.mjs) · GitHub repo: owner/site` (the scratch folder has
no `astro.config.mjs`, on purpose); and every case that printed "Going live" or "Nothing new goes
live" also printed the no-terminal line, and no "Publish to". New cases:
- `noorigin`: line 1 ends `GitHub repo: (no 'origin' remote with an owner/name address)`.
- `tokenurl`: `https://user:s3cret@github.com/owner/site.git`: line 1 ends `owner/site`, and no line
  of the output holds `s3cret`.
- `oddurl`: `https://example.invalid`: the fallback text, and `example.invalid` in no line.

**Real-git half.** The fixtures already hold `site: 'https://ship-test.example.invalid'` (line 949)
and `origin` at `$D/origin.git`, so line 1 is
`→ Site: https://ship-test.example.invalid · GitHub repo: <case>/origin`. S2 asserts it as line 1
(worktree mode), P4 (folder mode) with its own domain; S2 also asserts the no-terminal line comes
after "Going live" and before "▶ pre-push gate".

**A fake terminal.** A helper `run_tty <case> <answer|--eof|--stop> [VAR=value…]` starts ship.sh
under `script`: macOS's BSD form `script -q /dev/null bash scripts/ship.sh`, util-linux's form
`script -qec 'bash scripts/ship.sh' /dev/null`, told apart by `script --version` (util-linux has it;
BSD prints "illegal option", measured). Measured on macOS: BSD `script` passes its input to the
program, and sends an end of input the moment its own input ends. So a feeder waits, with a limit,
until the question is in the log, writes the answer, then holds its input open until ship.sh exits
or 60 seconds pass, so a broken case fails instead of hanging. Output comes back with `\r\n`; the
helper strips `\r` before any check. Where `script` is missing the T cases are skipped with a
printed line; the CI steps that run this file (the playwright job and the Mac bash 3.2 step) set
`SHIP_TEST_REQUIRE_TTY=1`, so a skip fails there, as `SHIP_TEST_REQUIRE_BASH32` does for S10 (e).
On Windows' Git Bash the real-git half already skips itself.
- T1 (worktree mode) answers `y`: the "Going live" header comes before `Publish to
  https://ship-test.example.invalid (T1/origin)?`, which comes before "▶ pre-push gate"; the run
  ends on the LIVE line, exit 0; production is now main.
- T2 (worktree mode, one unsaved file in the folder) answers `n`: exit 1; `you did not answer y`
  and `Nothing was published`; production unchanged; no "▶ pre-push gate"; the stubbed `npm` was
  never called; no "Not published" line (that list prints only after the temporary copy is made, so
  this pins the question before it).
- T3 answers an empty line, T4 sends the end of input: each as T2.
- T5 `--stop`: once the question is in the log, a terminate to ship.sh's bash. Exit 1 within the
  limit, the stop message, `Nothing was published`, and no `you did not answer y` (without the
  prompt-time trap the run waits until the feeder closes its input, then prints that line).
- T6 (folder mode) answers ` YES `: goes on, ends on the LIVE line.
- T7: a terminal on standard input, output sent to a file (`script … bash -c 'bash scripts/ship.sh
  > out'`): no question, the no-terminal line in the file, the run goes on.
- Every T case also passes `run_ship`'s checks (folder unchanged, nothing left behind).
- The file's last line names the new checks.

**Mutation check** (the `mutation-check` skill, on the built commit); each must fail a case:
always take the no-terminal branch (T1, T2); ask on `[ -t 0 ]` alone (T7); accept any answer (T2);
accept only lower case (T6); drop the prompt-time trap (T5); move the question after `npm ci` (T2)
or after the push (T2); move the first line after the fetch (S2 line-1 check, stub `expect`);
print the raw `origin` address (`tokenurl`); drop `-n`/`p` from the `sed` (`oddurl`).

## Not covered, said plainly

- An assistant whose shell does have a terminal (Codex's interactive app may run commands in one;
  not checked) is asked, and may type `y` itself. The question guards against a person in the wrong
  folder, not against an assistant.
- Ctrl-C from a real keyboard through `npm` was not measured; the measurement sent the signal to
  bash's own process. The script's existing stops rely on the same delivery.
- util-linux `script`'s handling of its input was not measured on Linux; the feeder's design does not
  depend on it, and the CI step proves it at build.
- Windows: whether Git Bash reports a terminal was not checked. If it reports none, the run says so
  and goes on as today; if a session's shell reports one, the run waits and publishes nothing. Both
  wrong guesses are safe ones.
