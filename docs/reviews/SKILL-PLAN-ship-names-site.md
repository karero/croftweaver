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

On 2026-11-07 the owner ran `npm run ship` in the wrong site's folder, typed at his own terminal
(the output he pasted into the session shows his shell prompt in that folder). This time it did no
harm: that site's live branch already held its `main` (GitHub's record shows the last push to it 90
minutes earlier), so the push printed `Everything up-to-date`. Had that `main` held unpublished
work, the run would have taken it live. The script printed the site's address only at the end, in
the live-site check. That is one incident, with no damage, and the question below would have
stopped it. Anyone with
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
- `site_lines <folder>`: how many lines of that file match the same pattern
  (`grep -cE … 2>/dev/null || true`, no pipe). The starter has one. When an owner keeps an old
  address in a comment there are two, and `site_of` may return the commented one, so the first
  line and the question name no address then (fallback below) rather than a possibly wrong one.
- `repo_of_origin`: the address `git push origin` uses, which is `origin`'s push address when one is
  set: `git remote get-url --push --all origin 2>/dev/null || true`. More than one line (several
  push addresses) gives a fallback. Otherwise a trailing `/` is removed, then `.git`, then the end
  is matched with `sed -nE 's#^.*[:/]([A-Za-z0-9._-]+/[A-Za-z0-9._-]+)$#\1#p' <<<"$url"` (a
  here-string, not a pipe). Only `owner/name` made of those characters is printed, so
  `git@github.com:owner/site.git`, `ssh://git@github.com/owner/site.git` and an `https` address
  with a user name and token before the host all give `owner/site`. Anything else gives the
  fallback and prints nothing of the address: a token in a query string, a user part with no
  owner after the host, no `owner/name` at the end, or no `origin`.

**B. The first line** goes right after `self_blob` is read (that read must stay first, line 360),
before the `ship.fromGitHub` check, in both modes:

    → Site: https://example.com · GitHub repo: owner/site

With no address: `Site: (no site: address in astro.config.mjs)`. With more than one `site:` line:
`Site: (more than one site: line in astro.config.mjs — check which one is live)`. With no usable
push address: `GitHub repo: (no 'origin' remote with a plain owner/name address)`. The run goes on either way, as it
does today: a missing `origin` still stops at the fetch with that step's own message.

It reads this folder's `astro.config.mjs`. In worktree mode the published copy may differ (only if
the address itself changed on GitHub's `main` and not here); that copy is still what the live check
reads at line 753. What goes live is decided by the push address, which the line names; the site
address is the name a person recognises. The address is already
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

      Publish to https://example.com (owner/site)? Type y and press Enter to go on, anything else stops:

  (with the first line's fallbacks in place of either name). Read one line with `read -r answer`
  (default `IFS`, so spaces around the answer go). `y` or `yes`, in any case, goes on, matched with
  `case "$answer" in [yY]|[yY][eE][sS])`, since bash 3.2 has no `${answer,,}`; anything
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
  meanwhile stops with "another publish holds this clone's lock". Its line "That process is still
  running, so a publish is under way. Let it finish" (line 163) gains "(it may be waiting for a yes
  in another window)". `on_exit` removes the lock and the empty temp folder after a "no", as after
  any early stop.

**D. Markers:** `template-version: 0.25` in `ship.sh` and in `tests/check_ship_push.sh`. The 0.24
release-notes row (BUGLOG, 2026-11-02) is still open; if no release comes between, the notes say
0.25 and cover both.

**Also, at build:**
- `skills/new-website/templates/PUBLISHING.md`, after "Before it uploads, it lists the commits that
  go live, newest first." (line 61): "It names the site first. Run in a terminal window with its
  output on screen, it then asks you to type y before it uploads; run by an assistant, or with its
  output sent to a file, it says it is not asking and goes on."
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

Every nested run today (stub `expect`, real-git `run_ship` and `start_bg`) sends its output to a
log, so none is asked, even when the file is run by hand at a terminal; the file needs no change for
that.

**Three existing checks move.** `first_has` (lines 980, 1065, 1453, 1592) reads the first line,
which is now the site line. A `mode_has` helper reads the first line that starts with
`→ Publishing`, and the three checks use it; `first_has` stays for the new line-1 checks.

**Stub half.** The stub learns `remote get-url --push --all origin`, answering
`git@github.com:owner/site.git` (a `noorigin` marker makes it and the fetch fail as a missing remote
does; an `originurl` file replaces the answer, one address per line). `expect` takes the case's
expected line 1 as an argument, default
`→ Site: (no site: address in astro.config.mjs) · GitHub repo: owner/site` (the scratch folder has
no `astro.config.mjs`, on purpose), and asserts it for every case; every case that printed "Going
live" or "Nothing new goes live" also printed the no-terminal line, and no "Publish to". New cases:
- `noorigin`: stops at the fetch; line 1 still the site line, ending in the repo fallback.
- `tokenurl1`: an `https` address with `user:s3cret` before the host and `owner/site.git` after:
  line 1 ends `owner/site`; no line of the output holds `s3cret`.
- `tokenurl2`: the user part with `s3cret` and only `site.git` after the host: the fallback, no
  `s3cret`.
- `queryurl`: `https://example.invalid/owner/site.git?token=s3cret`: the fallback, no `s3cret`.
- `twopush`: two addresses in `originurl`: the fallback.
- `oddurl`: `https://example.invalid`: the fallback, and `example.invalid` in no line.
- `twosite`: a scratch `astro.config.mjs` holding `// site: 'https://old.example.invalid',` and then
  `site: 'https://new.example.invalid',`: the more-than-one fallback, and `old.example` in no line.

**Real-git half.** The fixtures already hold `site: 'https://ship-test.example.invalid'` (line 949)
and `origin` at `$D/origin.git`, so line 1 is
`→ Site: https://ship-test.example.invalid · GitHub repo: <case>/origin`, with the case's own
lowercase name (`s2/origin`). S2 asserts it as line 1 (worktree mode), P4 (folder mode) with its
own domain; S2 also asserts the no-terminal line comes
after "Going live" and before "▶ pre-push gate".

**A fake terminal.** A helper `run_tty <case> <answer|--eof|--stop> [VAR=value…]` starts ship.sh
under `script`: macOS's BSD form `script -q /dev/null bash scripts/ship.sh`, util-linux's form
`script -qec 'bash scripts/ship.sh' /dev/null`, told apart by `script --version` (util-linux has it;
BSD prints "illegal option", measured). Measured on macOS: BSD `script` passes its input to the
program, and sends an end of input the moment its own input ends. So a feeder waits, with a limit,
until the question is in the log, writes the answer, then holds its input open until ship.sh exits.
ship.sh is started through the wrapper `start_bg` already uses (`bash -c 'echo "$$" > pid; exec
bash "$0"'`), so the helper knows its pid. A watchdog gives each case 60 seconds: past that it sends
a terminate to that pid and to `script`, waits for both, and fails the case as timed out, so a
broken case neither hangs nor leaves a run behind. Output comes back with `\r\n`; the helper strips
`\r` before any check. Where `script` is missing the T cases are skipped with a
printed line; the CI steps that run this file (the playwright job and the Mac bash 3.2 step) set
`SHIP_TEST_REQUIRE_TTY=1`, so a skip fails there, as `SHIP_TEST_REQUIRE_BASH32` does for S10 (e).
On Windows' Git Bash the real-git half already skips itself.
- T1 (worktree mode) answers `y`: the "Going live" header comes before `Publish to
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
  prompt-time trap the run waits until the feeder closes its input, then prints that line).
- T6 (folder mode) answers ` YES `: goes on, ends on the LIVE line.
- T7: a terminal on standard input, output sent to a file outside the clone (`script … bash -c
  'bash scripts/ship.sh > "$G/t7.out"'`); its feeder waits for no question and only holds the input
  open: no question, the no-terminal line in the file, the run goes on.
- Every T case also passes `run_ship`'s checks (folder unchanged, nothing left behind).
- The file's last line names the new checks.

**Mutation check** (the `mutation-check` skill, on the built commit); each must fail a case:
always take the no-terminal branch (T1, T2); ask on `[ -t 0 ]` alone (T7); accept any answer (T2);
accept only lower case (T6); drop the prompt-time trap (T5); move the question after `npm ci` (T2)
or after the push (T2); move the first line after the fetch (`noorigin`, which stops there); read
the fetch address, not the push address (a stub case whose push and fetch addresses differ, added
with this mutation); print the raw address (`tokenurl1`, `queryurl`); widen the class to `[^/:]`
(`tokenurl2`, `queryurl`); drop `-n`/`p` from the `sed` (`oddurl`); drop the line count
(`twosite`); drop the lock message's addition (the "under way" cases at lines 1169 and 1209, which
gain a check for the new words).

## Not covered, said plainly

- An assistant whose shell does have a terminal (Codex's interactive app may run commands in one;
  not checked) is asked. It may type `y` itself, or it may not be able to type and wait until its
  tool's time limit stops the run, which the prompt-time trap ends with "Nothing was published".
  Both are safe. The question guards against a person in the wrong folder, not against an
  assistant.
- A config whose only `site:` line is a comment gives that commented address; Astro then has no
  `site`, and the live check at line 753 already reads the same line today.
- Ctrl-C from a real keyboard through `npm` was not measured; the measurement sent the signal to
  bash's own process. The script's existing stops rely on the same delivery.
- util-linux `script`'s handling of its input was not measured on Linux; the feeder's design does not
  depend on it, and the CI step proves it at build.
- Windows: whether Git Bash reports a terminal was not checked. If it reports none, the run says so
  and goes on as today; if a session's shell reports one, the run waits and publishes nothing. Both
  wrong guesses are safe ones.
