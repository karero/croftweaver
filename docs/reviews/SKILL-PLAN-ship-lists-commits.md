# Plan: `npm run ship` lists the commits that go live, before it pushes

Base `origin/main` 9fcce2cc · branch `claude/plan-ship-lists-commits-f5cfff` · review depth: High
(the starter's publish script: the skill's High row names deploy code) · red team: none (the change
only reads git and prints; it deletes, logs in to and moves nothing).

| Step | What | State | Evidence |
|---|---|---|---|
| 1 | This plan | written 2026-11-02 | this file |
| 2 | PLAN gate, High | rounds 1 to 4, final full read and wording pass done; open: the confirmation | trail `REVIEW-plan-2026-11-02-claude-plan-ship-lists-commits-f5cfff-5e9889f.md` |
| 3 | `ship.sh` prints the list; `check_ship_push.sh` cases; both markers 0.24 | waits for the owner's go | — |
| 4 | `PUBLISHING.md`: one sentence | waits for the owner's go | — |
| 5 | `docs/BUGLOG.md`: the release-notes row | waits for the owner's go | — |
| 6 | `make check`, mutation check, DIFF gate at High, then PR | waits for the owner's go | — |

## What and why

Today `npm run ship` prints "→ Publishing main → production. This goes LIVE." (or, with
`ship.fromGitHub` on, "→ Publishing GitHub's main as of the fetch (<id>) …"), runs the site's
checks and pushes. It never says which changes go live. On a site several people or assistants
work on, the owner can publish someone else's merged work without knowing it. No such surprise was
found; one near-miss was (2026-10-24, a session had to warn in prose that a publish would also
carry another pull request). A list printed before the push answers it for every owner, alone or
in a team.

Decided before this plan (owner, 2026-11-02): the list only. No line saying which session or
person made each commit (that belongs to the maintainer's own setup, not to every owner's site),
and no "continue?" prompt (it would break a publish run without a terminal).

## How

All in `skills/new-website/templates/astro/scripts/ship.sh`, in one place for both modes: right
after the divergence check (`git merge-base --is-ancestor origin/production "$id"`, line 552)
passes, before worktree mode makes its temporary copy. So the list is printed only when the
publish can go ahead, and in worktree mode it comes before the "Not published" lists: first what
goes, then what stays.

1. **Four reads, no pipe** (the repo's pipefail guard flags `| head`). New names only: `list`
   is taken (the path of the worktree list, `ship.sh` lines 381, 405, 572), and a `local` in
   `ship` would hide that global from the functions it calls (round 1, both seats).
   - `live_prod="$(git rev-parse --verify 'origin/production^{commit}')"`: production read once,
     so the three reads below agree even if another session's fetch moves it meanwhile. The
     divergence check at line 552 keeps its own read of the name, unchanged. If production moves
     after these reads, that one run's list may be off. What the push then does is unchanged by
     this plan, and the plan claims nothing about it (rounds 3 and 4: two earlier wordings went
     beyond what was measured).
   - `live_n="$(git rev-list --count --first-parent "$live_prod..$id")"`: how many lines.
   - `live_all="$(git rev-list --count "$live_prod..$id")"`: how many commits.
   - `live_lines="$(git -c log.showSignature=false log --first-parent --format='%h %s' -n 20 "$live_prod..$id")"`

   `$id` is the commit the run already reads once and pushes. `--first-parent` makes a merged
   pull request one line ("Merge pull request #12 from …"), not every commit on its branch.
   `--format` instead of `--oneline`: a format ignores the owner's `log.decorate` and colour
   settings (checked 2026-11-02, git 2.54, with `color.ui=always` and `log.decorate=full`: plain
   `e0020ea c3` lines). `-c log.showSignature=false`: with that setting on, git adds lines of
   its own for a signed commit (round 2, fresh-eyes, tested with an ssh-signed commit: a "No
   signature" line). No pager can start: git starts one only when its output is a terminal,
   and `$( )` captures it (checked 2026-11-02 under `script`, git 2.54: a captured `git log`
   left no pager mark, a direct one did). `-n 20` is the only cap: the printing loops over
   whatever `live_lines` holds.
2. **A Ctrl-C** during any of the reads: `stop_point "Nothing was published and $here."`, as
   after every other git call before the push.
3. **Any read fails** (both commits are known to exist, so this means a broken clone): the four
   reads and step 4's `tr` sit in one `if … && … && …; then` guard, and the run stops before anything else, "✗ Publish stopped — couldn't list the commits that would go live (git's
   error is above). Nothing was published and $here." It refuses rather than publishing unlisted,
   as the script's other checks before the push do.
4. **Control bytes are removed** from the lines before they are printed:
   `live_lines="$(LC_ALL=C tr -d '\001-\010\013-\037\177' <<<"$live_lines")"`, as the fifth step of
   step 3's guard, so a failing `tr` stops the run with that step's message too. It keeps tab and
   newline and removes the other C0 bytes and DEL. A commit subject is written by whoever
   committed it, and git prints it raw (checked: a subject holding `ESC[31m` comes out with the
   escape byte), so a subject could otherwise recolour or rewrite the owner's terminal.
   `LC_ALL=C`: macOS's `tr` in a UTF-8 locale stops with "Illegal byte sequence" on a byte that
   is not UTF-8 (round 1, fresh-eyes, tested).
5. **What it prints:**
   - `live_n` 1 or more: a blank line, then `Going live, newest first (a merge is one line):`,
     then each line indented four spaces, as the "Not published" list is.
   - `live_n` over 20: after the 20, `    … and <live_n − 20> more lines (git log
     --first-parent <live_prod, 12 characters>..<id, 12 characters> lists them all)`. Fixed ids,
     not `origin/production`: once the publish lands, the name points at `$id` and the command
     would list nothing (round 2, Codex).
   - `live_all` differs from `live_n`: last, `    <live_all> commits in all: the merges in this
     range bring in the rest.` ("in this range", not "above": past 20 lines the merges may be among
     those cut.) The number in the header would be wrong for every merged pull request,
     so the header has none (round 1, fresh-eyes). This line also matters in folder mode: after
     the script's own advice `git pull --no-rebase`, other people's merged pull requests sit
     behind one "Merge branch 'main' of …" line (checked 2026-11-02, git 2.54: a merged pull
     request and a local commit gave 2 first-parent lines, 4 commits).
   - After the list and its notes: a blank line, so the list ends before the gate's own output
     in both modes (final read: in folder mode the gate's output came straight after it).
   - `live_n` 0 (production already has this commit): `Nothing new goes live: 'production'
     already has this commit. The checks and the live-site check run as usual.` The run then
     goes on as today. (Checked 2026-11-02, git 2.54: a push with nothing new still runs the
     pre-push hook, then prints "Everything up-to-date" and exits 0.)
6. **Unchanged:** no `production` branch on GitHub still stops at line 489 with its own message,
   before this point; a diverged `production` still stops at line 552, also before. The first and
   last lines of a run stay as they are.
7. **Markers:** `template-version: 0.24` in `ship.sh` and in `tests/check_ship_push.sh` (the test
   asserts they agree). If `ship.sh` has moved on `main` by build time (the Workers starter, BUGLOG
   row of 2026-10-30, may touch it), rebase first and take the next version.

Also, at build:
- `skills/new-website/templates/PUBLISHING.md`, the paragraph under "4. Happy? Publish it": one
  sentence, "Before it uploads, it lists the commits that go live, newest first."
- `docs/BUGLOG.md`: a "Next release notes" row: `ship.sh` and `check_ship_push.sh` are 0.24, take
  them together; what the list shows; `PUBLISHING.md` changed one sentence.
- `scripts/whats-new.sh` needs no change: its `TEMPLATE_TRACKED` list (line 80) already names
  `ship.sh`, the tests folder and `PUBLISHING.md`, so a site's report lists all three.
- Not in this change: taking 0.24 into croftweaver-site and GenAI_site. Each site does that through
  `whats-new`, in its own pull request.

## How it is tested

In `tests/check_ship_push.sh`, through the real `ship.sh` as `npm run ship` runs it. Expected
values are written from each fixture's commit subjects and ids, never copied from a run's output.

**Stub half** (stubbed `git`):
- the stub's `rev-parse` learns one exact arm: `--verify origin/production^{commit}` answers a
  production id of its own, `PROD=3333…`, distinct from `$SHA`; the divergence check's
  `merge-base` arm matches the literal name `origin/production` and is unaffected. With two ids,
  a swapped range is visible to the stub (round 2, both seats: with one id it was not).
- new `rev-list` and `log` arms answer only the three exact invocations above, each on
  `$PROD..$SHA` (the two counts answer 0, the log nothing), and refuse anything else with exit 3,
  as its `merge-base` arm does. The stub's option loop (lines 60–67) moves every `-c` into
  `$FAKE_DIR/settings` before the arms see `$*`, so the `log` arm also refuses unless the last
  line of that file is `log.showSignature=false` (round 3, both seats). So a swapped range, a
  dropped `--first-parent`, a range not built from `live_prod`, or a dropped
  `-c log.showSignature=false` fails every case that reaches them. Each `rev-list` and `log`
  call is logged as its arm is entered, before the exact match, so a refused call is logged too
  (`prodfail` depends on it).
- every case that gets past the divergence check now prints "Nothing new goes live".
- every new text check here ("Nothing new goes live", "couldn't list the commits") goes through
  `expect`'s marker or honours `SHIP_GATE_SKIP_WORDING`, as the existing ones do (lines 230–240),
  so they add no failure on a translated site. (A few existing stub checks are English with no
  switch, such as lines 543 and 562; this change adds none. The real-git half is English-only.)
- new `prodfail`, `countfail`, `allfail` and `logfail`: one read fails, the ones before it
  succeed; each exits 1 with 0 pushes and "couldn't list the commits" (rounds 1 and 2,
  fresh-eyes: a read with no case of its own could fail unseen). `prodfail` also asserts that no
  `rev-list` or `log` call was logged: with its failure let go, `live_prod` is empty, the next
  read asks for `..$SHA`, the stub refuses it, and the run still ends with 0 pushes (round 3,
  fresh-eyes).
- new `stopat-revlist`: a terminate during the first count read; exit 1, 0 pushes, the stop
  message, and no "couldn't list the commits" line. Without the `stop_point` the EXIT trap still
  prints the stop message (`on_exit`, `ship.sh` 302–304), so only that absent line tells the two
  apart, as `stopverdict` does with its own text (round 3, fresh-eyes).
- the existing diverged case also asserts 0 list calls.

**Real-git half** (bare origin, clone, tiny gate, as today). The list block is every line of
standard output from the header to the next blank line; a list line is a block line matching
`^    [0-9a-f]{7} `:
- S2 (worktree mode, main 2 ahead): the header `Going live, newest first (a merge is one line):`;
  `    <id7> change 2` on a line before `    <id7> change 1`; no "commits in all" line; the
  header before "Not published" and before "▶ pre-push gate".
- S3 (this computer's main 1 commit ahead): one listed line, and the local commit's id is not in
  the output.
- P4 (folder mode, real domain): one listed line, `    <id7> site address`.
- new L1 (worktree mode): GitHub's main gains a `--no-ff` merge of a 3-commit branch: one listed
  line, the merge; none of the branch's three subjects; `    4 commits in all: the merges in this
  range bring in the rest.`
- new L2: 23 commits: exactly 20 listed lines, the first `change 23`, then `    … and 3 more
  lines`; no "commits in all" line.
- new L3: production already at main: "Nothing new goes live"; the gate still runs ("▶ pre-push
  gate" in the output); exits 0 on the LIVE line; production unchanged.
- new L4 (worktree mode): the clone sets `color.ui=always`, `log.decorate=full`, `format.pretty=fuller` and
  `log.showSignature=true`; one commit's subject holds `ESC[31m`, and another commit is signed
  with an ssh key the fixture makes with `ssh-keygen` (`-c gpg.format=ssh -c user.signingkey=…
  commit -S`); a third commit's subject holds a raw `\xff` byte, which is not UTF-8. L4 runs
  `ship.sh` with `LC_ALL=en_US.UTF-8` (`run_ship` takes settings, as `s9-second` does), so the
  Mac job's `tr` meets a UTF-8 locale whatever the runner inherits. The `\xff` line keeps its byte
  (on the Mac job only, this fails without `LC_ALL=C`: macOS `tr` stops with
  "Illegal byte sequence", GNU `tr` does not). The ESC line is exactly `    <id7> evil [31mred[0m end`; the block holds
  the header and the expected list lines and nothing else, so a stray line such as `No signature`,
  which is no list line, still fails it (round 4); no line of the block holds an escape byte, `(HEAD`, `refs/` or `ignature` (in worktree mode the clone's HEAD is
  outside the range, so a decoration would show as `refs/…`, round 3). Where `ssh-keygen` is missing or git is older than 2.34 (its first ssh signing), the signed commit
  is left out and the run says so.
- new L6 (folder mode, the sequence the script itself advises): GitHub's main gains a `--no-ff`
  merge of a one-commit branch, the folder commits one change of its own to a different file
  (the same file would make the pull stop on a conflict), runs `git pull -q
  --no-rebase --no-edit` (without `--no-edit` git waits for an editor when the file runs in a
  terminal, round 3) and `git push`, then, prepared for folder mode as P3 and P4 are (setting unset,
  files back-dated, `update-index --refresh`), ships: the listed lines are the "Merge branch 'main' of …" merge and the local change, then
  `    4 commits in all: the merges in this range bring in the rest.`
- the file's last line names the new checks.

**Mutation check** (the `mutation-check` skill, on the built commit), each must fail a case: drop
`--first-parent` from the log (L1); swap the range (S2, stub arms); use `origin/production`
instead of `live_prod` in a read (stub arms); drop `-c log.showSignature=false` (L4, the stub `log` arm's settings check); drop `-n 20` (L2); drop the
`tr` (L4); drop `LC_ALL=C` (L4, the Mac job); drop the "commits in all" line (L1, L6); name the lines `list` again (S2: the worktree
list goes wrong); move the list after the push (S2's order check); for each of the four reads, let its failure go on
(`prodfail`, `countfail`, `allfail`, `logfail`); drop the `stop_point` (`stopat-revlist`).

Then `make check`, the template-tests jobs that run this file (Linux, and the Mac's bash 3.2), and
the DIFF gate at High.

## Not covered

- Windows' Git Bash: the real-git half skips itself there today, so the new real-git cases do too;
  the stub cases run.
- Whether `%h` stays 7 characters: git lengthens it in a large repo. The tests use tiny repos,
  where it is 7.
- Behind a "Merge branch 'main' of …" line (L6), the list names no commit it brings in; the
  "commits in all" line says only that there are more. `git log origin/production..main` shows
  them.
- C1 control characters (0x80 to 0x9F, as raw bytes or written as UTF-8) pass the `tr`. Whether common
  terminals act on them in UTF-8 mode was not checked.
- With nothing new, the run still prints "✓ Pushed. Cloudflare is building the live site now."
  (`ship.sh` 835) before it checks the live site, unchanged here. The "Nothing new goes live" line
  before it says what is true; rewording that line for this case is a follow-up (final read).
