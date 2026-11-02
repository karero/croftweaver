# Plan: `npm run ship` lists the commits that go live, before it pushes

Base `origin/main` 9fcce2cc · branch `claude/plan-ship-lists-commits-f5cfff` · review depth: High
(the starter's publish script: the skill's High row names deploy code) · red team: none (the change
only reads git and prints; it deletes, logs in to and moves nothing).

| Step | What | State | Evidence |
|---|---|---|---|
| 1 | This plan | written 2026-11-02 | this file |
| 2 | PLAN gate, High | not started | trail `REVIEW-plan-2026-11-02-ship-lists-commits.md` |
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

1. **Two reads, no pipe** (the repo's pipefail guard bans `| head`):
   - `count="$(git rev-list --count --first-parent "origin/production..$id")"`
   - `list="$(git --no-pager -c log.showSignature=false log --first-parent --format='%h %s' -n 20 "origin/production..$id")"`

   `$id` is the commit the run already reads once and pushes. `origin/production` is spelled as the
   divergence check spells it, so both answer about the same ref, fresh from this run's fetch.
   `--first-parent` makes a merged pull request one line ("Merge pull request #12 from …"), not
   every commit on its branch. `--format` instead of `--oneline`: a format ignores the owner's
   `log.decorate` and colour settings (checked 2026-11-02, git 2.54, with `color.ui=always` and
   `log.decorate=full`: plain `e0020ea c3` lines). `--no-pager` is load-bearing: in a terminal
   `git log` would otherwise open a pager and the publish would wait for a key.
2. **A Ctrl-C** during either read: `stop_point "Nothing was published and $here."`, as after
   every other git call before the push.
3. **Either read fails** (both commits are known to exist, so this means a broken clone): stop
   before anything else, "✗ Publish stopped — couldn't list the commits that would go live (git's
   error is above). Nothing was published and $here." It refuses rather than publishing unlisted,
   as the script's other checks before the push do.
4. **Control characters are removed** from the list before it is printed:
   `list="$(tr -d '\001-\010\013-\037\177' <<<"$list")"`. A commit subject is written by whoever
   committed it, and git prints it raw (checked: a subject holding `ESC[31m` comes out with the
   escape byte), so a subject could otherwise recolour or rewrite the owner's terminal.
5. **What it prints:**
   - one or more: a blank line, then `Going live: 3 commits that 'production' doesn't have yet,
     newest first:` (`1 commit` for one), then each line indented four spaces, as the "Not
     published" list is.
   - more than 20: the first 20, then `    … and 4 more (git log --first-parent
     origin/production..<id, 12 characters> lists them all)`. 20 is the cap the "Not published"
     list already uses.
   - none (`count` is 0: production already has this commit): `Nothing new goes live:
     'production' already has this commit. The checks and the live-site check run as usual.`
     The run then goes on as today. (Checked 2026-11-02, git 2.54: a push with nothing new still
     runs the pre-push hook, then prints "Everything up-to-date" and exits 0.)
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

**Stub half** (stubbed `git`; there `origin/production` and `$id` are the same commit):
- the stub's option loop learns `--no-pager`; new `rev-list` and `log` arms answer only the exact
  two invocations above and refuse anything else with exit 3, as its `merge-base` arm does, so a
  swapped range or a dropped `--first-parent` fails every case that reaches them. Each call is
  logged.
- every case that gets past the divergence check now prints "Nothing new goes live" (count 0).
- new `listfail`: the count read fails; exit 1, 0 pushes, "couldn't list the commits".
- new `stopat-revlist`: a terminate during the count read; exit 1, 0 pushes, the stop message.
- the existing diverged case also asserts 0 list calls.

**Real-git half** (bare origin, clone, tiny gate, as today):
- S2 (worktree mode, main 2 ahead): "Going live: 2 commits"; `    <id7> change 2` on a line before
  `    <id7> change 1`; the list before "Not published" and before "▶ pre-push gate".
- S3 (this computer's main 1 commit ahead): "Going live: 1 commit", and the local commit's id is
  not in the output.
- P4 (folder mode, real domain): "Going live: 1 commit" and `    <id7> site address`.
- new L1: GitHub's main gains a `--no-ff` merge of a 3-commit branch: one listed line, the merge;
  none of the branch's three subjects.
- new L2: 23 commits: "23 commits", exactly 20 listed lines starting with `change 23`, then
  "… and 3 more".
- new L3: production already at main: "Nothing new goes live"; exits 0; production unchanged.
- new L4: the clone sets `color.ui=always`, `log.decorate=full`, `format.pretty=fuller` and
  `log.showSignature=true`, and a commit subject holds `ESC[31m`: the listed line is exactly
  `    <id7> evil [31mred[0m end`, and no listed line holds an escape byte or `(HEAD`.
- new L5 (pager): folder mode run under `script`, so git sees a terminal, with `GIT_PAGER` set to
  a stub that passes its input through and writes a mark: no mark. Where `script` is missing or of
  an unknown kind, L5 is skipped and the run says so, as the file's other skips do.
- the file's last line names the new checks.

**Mutation check** (the `mutation-check` skill, on the built commit), each must fail a case: drop
`--first-parent` (L1); swap the range (S2, stub arms); drop `-n 20` (L2); drop `--no-pager` (L5);
drop the `tr` (L4); move the list after the push (S2's order check); let a failed read go on
(`listfail`).

Then `make check`, the template-tests jobs that run this file (Linux, and the Mac's bash 3.2), and
the DIFF gate at High.

## Not covered

- Windows' Git Bash: the real-git half skips itself there today, so the new real-git cases do too;
  the stub cases run.
- Whether `%h` stays 7 characters: git lengthens it in a large repo. The tests use tiny repos,
  where it is 7.
- A local `main` made with `git pull --no-rebase` in folder mode puts GitHub's commits on the
  second-parent side of a merge: the list then shows that merge as one line. That is the
  first-parent view, and it is what the header says ("newest first", one line per merge).
