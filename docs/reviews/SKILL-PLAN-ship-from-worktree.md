# Plan: publish from a throwaway worktree, so a busy folder never blocks `npm run ship`

The template change (row 3) is built and merged; the three site copies (row 4) are not. Before
any build, the plan went through the plan review gate and, because it changes the script that
publishes to a live site, one red-team pass, both closed by the maintainer (row 2). Where this
plan and the shipped files disagree, the files win.

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-10-20 | this file |
| 2 | Plan review gate (High depth: deploy code that deletes folders), then red team | ✅ closed by the maintainer 2026-10-21 after 8 rounds, a final full read, a wording pass and a red team; about 133 findings, every BUG fixed; round 8's fixes not re-checked by a reviewer | trail `REVIEW-plan-2026-10-21-plan-ship-from-worktree-f6266ac.md` |
| 3 | Template change (D3.1) | ✅ merged 2026-10-22 as karero/croftweaver#376. DIFF gate at High depth: 6 rounds, a final full read, a re-gate of its closing edits, a merge link after each merge of `main`, and re-gates of a fix the PR's CI asked for (newer git words a refusal differently); 67 findings, every BUG fixed or refuted (the emergency recipe took a cut, then a redesign). On Windows the test's real-git half skips itself (the maintainer's choice, 2026-10-22; follow-up in `docs/BUGLOG.md`) | merge commit `001c68b7` (head `283fa0a8`); branch `claude/ship-from-worktree-3b24ce` (deleted on GitHub after the merge): commits `d831de2e` to `230fe4da` and `52db3b54`, `9d2aa97b`, `2a3421f1` (code), merges of `main` `ca63e8fe`, `117773ff`, `713bcb24`; trail `REVIEW-diff-2026-10-22-claude-ship-from-worktree-3b24ce-0aaeb44.md` |
| 4 | The three site copies (D3.2 to D3.4) | ⏸ | — |

## What and why

`npm run ship` stops unless the site folder is on `main` and has no uncommitted or
untracked files. Where several people or AI sessions share one checkout, the folder is
seldom clean: someone's draft note, a data folder, a feature branch left checked out. Files
that have nothing to do with the publish block it.

Relaxing the check in place would be wrong. The push sends commits, so stray files can
never reach the live site, but the pre-push gate builds and tests the *folder*. In a dirty
folder, or on a feature branch, the gate tests files that are not being published. The
clean check keeps the gate honest as well as catching the owner's forgotten edit.

So: an opt-in mode that publishes GitHub's `main` from a throwaway git worktree, created
detached at the exact commit and removed on every exit. The gate then tests exactly the
commit that goes live. Nothing in the shared folder is built, tested, published or changed;
D2 lists what the run reads there and what it updates in the clone's shared records.

## Checked 2026-10-20 and 2026-10-21 (scratch repos, git 2.33, bash 3.2 and 5.3)

- A second worktree cannot check out `main` while another has it ("'main' is already
  checked out at …"). A detached one at the fetched commit can.
- Detached, the branch name reads `HEAD` and the upstream lookup fails ("HEAD does not
  point to a branch"), so today's branch and upstream checks cannot run there unchanged.
- A push from the worktree runs the worktree's own committed pre-push hook, not the shared
  folder's edited copy, because the clone's hooks path is the relative `scripts/hooks` (so
  in all three sites' shared config; session worktrees may carry their own absolute value,
  which a throwaway worktree made from them does not inherit). Pushing a commit id to
  `refs/heads/production` works.
- Removing a worktree that holds untracked files needs the force option; ignored files
  alone, such as installed packages, do not. A locked one needs it twice. Removing one
  record by its path works even when its folder is gone.
- A worktree's HEAD, index and reflog live in the clone's git folder, not in its own
  folder. A repo-wide prune dropped the record of a worktree whose folder had only been
  moved away (as an unmounted disk would be): a commit made there was left reachable from
  nothing, and the folder, once back, was no longer a git checkout. A fetch starts git's
  automatic housekeeping by default. Two settings given to that one fetch turn it off
  (`maintenance.auto=false`, `gc.auto=0`): with housekeeping due and set to prune at once,
  a plain fetch dropped a moved-away worktree's record and the same fetch with the settings
  kept it; the `--no-auto-maintenance` switch did the same. An older git that lacks the
  switch would refuse the fetch, while it ignores a setting it does not know (not checked on
  an older git).
- bash ran the exit trap on interrupt, terminate and hang-up, in 3.2 and 5.3, and skipped
  it after an `exec` that replaces the shell (not after a redirect-only `exec`). A hard kill
  or a power cut skips it too. With no trap for the signal itself, a terminate sent to the
  script's own process alone runs the exit trap at once while a child it waits on keeps
  running. With a trap for the signal, bash runs that trap only when the step in the
  foreground ends, both for a terminate sent to the script alone and for an interrupt sent to
  the whole group (as a terminal's Ctrl-C is), and the script then carries on; in the second
  case the child had the interrupt too and stopped at once. A trapped quit behaves like a
  trapped terminate. Started as a background job without job control, the script has
  interrupt and quit ignored from the start, and no trap can catch them, as today. bash runs
  an edit made to a running script file in place, unless the body is a function called on
  the same line as `exit`. A plain command's exit status survived a deferred terminate on
  both versions (it read 7); only a pipeline's per-command status was lost. On bash 3.2 (the
  Mac's own), a trapped terminate that arrives during a pipeline resets the pipeline's
  per-command status: a step that exited 7 then read as 0 (bash 5.3 kept 7); a status the
  step wrote to a file itself read 7 on both. Inside a trap, `set +e` resets the exit status
  to 0, so the status must be saved before it.
- From a linked worktree, a push given the hooks folder `scripts/hooks` for that one command
  ran the worktree's committed hook while the clone's shared setting named another folder.
- `npm ci` hands an environment variable set for it through to the package's prepare step
  (a probe package's prepare printed it when set, and "(unset)" when not).
- Playwright (1.63, Site A's copy) starts the test server in its own process group (its
  launcher's `detached` option, on macOS and Linux) and sets no terminate handler for it, so
  a terminate can leave the server holding its port; an interrupt to the group made
  Playwright stop it (a reviewer's reproduction). When the port is taken, its runner prints
  "… is already used, make sure that nothing is running on the port/url or set
  reuseExistingServer:true". The template asks for 1.64, not checked; the run matches on
  "is already used".
- From a linked worktree, git hands the pre-push hook `GIT_DIR` set to that worktree's git
  folder (from the primary checkout, it does not). Gate steps today call git only to read
  the current commit, to set the hooks path, or (Site C's test config) to find the folder's
  top, which with `GIT_DIR` set returns the current folder: right at the worktree's root,
  where the tests start, wrong from a subfolder.
- Plain `git status` rewrote the index, which takes its lock for a moment; with git's
  optional locks turned off it did not.
- Production moving on the remote while the pre-push hook ran: stock git refused the push
  with `! [remote rejected] … (failed to update ref)`, after `remote: error: cannot lock
  ref …: is at … but expected …`. Today's classifier knows only `! [rejected]`, so it says
  "a reason this script can't name" (nothing is published). Production moving before the
  push starts gives `! [rejected] … (fetch first)`, which it does know. GitHub's wording
  for the first case is not checked.
- A fresh install of the template's packages took 4.6 s with a warm npm cache (286 packages).
- The template's test server never reuses a server already on its own port: a server left
  on that port makes the gate fail rather than answer its tests.

## Decisions

**D1. Who gets it, and what happens to uncommitted files.** The script cannot tell whose
files are in the folder; only the person running it knows. So the mode is opt-in, through
one git setting, `ship.fromGitHub`, kept in the clone's own git config. That config is
shared by all of the clone's worktrees, on purpose: every session working in the clone gets
the mode. There is no per-run switch (decided 2026-10-21, below). The script reads the
setting from the clone's config only, never the user's global one, so a fresh clone (a
beginner, a new owner) keeps today's behaviour, block included: "I edited a page and forgot
to commit" still stops the publish with today's message, which does not mention the setting.

With the setting on, the first line says the run publishes GitHub's `main` and ignores this
folder, naming the commit it fetched (D2 "The messages"). Uncommitted and untracked files
never block: before the push they are listed (the first 20, then a count) under "Not
published: in this folder, not on GitHub's main", and the last line of any run that printed
the list, success or failure, repeats the count. Commits on this computer's `main` that
GitHub lacks never block either; the script gives their number (none when there is no local
`main`) and says to get them onto GitHub's `main` if they should go live (a pull request, or
a push where direct pushes to `main` are allowed). The folder's branch does not matter, so a
session can run ship from its own worktree, as long as its `ship.sh` is the one on GitHub's
`main` (D2).

Any session in the clone can switch the setting on or off; switching it on brings only the
trade-off below, which every run's first line names.

*Counter-argument:* with the setting on, the maintainer's own forgotten edit stays
unpublished while the script reports success. Accepted: on a shared machine GitHub's `main`
is the only state everyone agrees on, and the list says what was left out. A per-run flag
would be more visible, but every session has to remember it, and one that forgets hits
today's block again.

**D2. The checks in worktree mode.** With the setting off, the script runs in the folder as
today and takes no lock and makes no worktree. Of the changes below, these apply in both
modes: the fetch without housekeeping, the commit id, the "production moved" message for a
refusal during the gate, the signals, the exit trap, the ban on `exec`, and every site's hook
clearing its variables.
- The fetch keeps today's classifier, and in both modes runs with git's automatic
  housekeeping off, through the two settings rather than the switch, so a publish never
  starts git's own prune and an older git does not refuse the fetch. In worktree mode the
  fetch names its two branches, `main` and `production`, each forced into its remote-tracking
  ref as git's default fetch setting does, so a narrowed fetch setting in the shared config
  cannot leave `origin/main` stale; today's mode keeps today's fetch. If either branch is
  missing on GitHub, that explicit fetch fails, and today's fetch message prints git's own
  error, which names the branch (checked: "couldn't find remote ref refs/heads/production");
  there is no separate setup message for it in worktree mode. Today's mode keeps today's
  "No 'production' branch on GitHub yet".
- **The commit id.** In worktree mode it is `origin/main`'s id, read once after the fetch.
  In today's mode it is the folder's own commit, once today's checks have shown it is on
  `main`, clean and equal to its upstream; that upstream need not be `origin/main`, so
  today's mode must not switch to `origin/main`'s id. Everything after uses the id: the
  worktree is created detached at it, the divergence check asks whether `origin/production`
  is its ancestor, the push sends it to `refs/heads/production`, and the live check waits for
  it. Today the push and the live check read local `main` again; both modes switch to the id,
  so a commit landing on local `main` mid-publish cannot change what is pushed or verified.
  In today's mode the gate still builds the folder, so a change made there mid-publish can
  still change what is tested, as today; only worktree mode closes that.
- "Main is pushed" holds by construction: the commit came from GitHub. The branch check and
  the upstream check are skipped; D1's two lists replace them.
- **The publishing script.** In worktree mode, holding the lock, right after the commit id
  is read and before the worktree is made, the run compares the running `ship.sh` with the
  commit's `scripts/ship.sh` by content (git's hash of each file), not by their
  template-version lines. The running file is hashed as the script's very first step, before
  the lock and the fetch, so a file another session replaces meanwhile cannot pass for the
  one bash read; only the instant between bash reading the file and that first step is left.
  If they differ, it stops and names both template-versions, or, when those match, says the
  two files differ anyway; nothing is published, and the exit trap removes its lock. The
  folder may be on any branch, with edits, and a half-edited or outdated copy must not
  publish. The fix it names is to run ship from a checkout up to date with GitHub's `main`.
  Today's mode needs no such check: it already requires a clean folder equal to its
  upstream. In both modes the script's body is one function, called on the same line as
  `exit`, so bash has read all of it before it runs any of it: an edit another session makes
  to the file mid-run changes nothing (without that, bash runs such an edit).
- **What the run touches in the clone.** It reads the folder's status with git's optional
  locks off, so it never takes the index lock another session's `git add` may need. It
  updates the clone's shared records: the fetched GitHub branches (as today), a lock, a list
  of its worktrees and a worktree entry while it runs. It never changes the clone's hooks
  setting (below). It changes nothing in the folder itself. It resolves the clone's shared
  git folder to a full path first, since git prints a relative one in a primary checkout.
- **The install.** Before the push the script runs `npm ci` in the worktree, so the lockfile
  is never rewritten and the gate tests the commit. Every publish in this mode therefore
  needs the npm registry or a warm npm cache. A gate that runs `scripts/verify.mjs` installs
  a second time (its install stamp is missing), about 5 s more; accepted, rather than have
  ship write that file's private stamp. A failed install stops before the push. An install
  runs the packages' prepare step, which wires the hooks by writing the clone's shared hooks
  setting, and another session may rely on a different value. So in worktree mode ship sets
  an environment variable for its install and its push (the gate's own second install
  inherits it), and the template's `scripts/wire-hooks.mjs` leaves the setting alone when it
  is set. Sites A and C replace their older inline prepare line with that script (D3.2,
  D3.4). The setting is therefore never changed during a publish, not even for a moment. Site
  B's hook only refuses direct pushes to `main` and runs no step that needs packages, so its
  copy skips the install (D3.3). The list of what is not published is printed after the
  worktree is made, once the script's temp files exist, and before the install.
- **The gate.** In worktree mode the push pins the hook: git is told for that one command
  that the hooks folder is `scripts/hooks`, so the worktree's committed `pre-push` runs
  whatever the clone's shared setting says, and a setting changed by another session between
  a check and the push cannot change it. Before the push the run checks that the worktree has
  an executable `scripts/hooks/pre-push` and stops if not: nothing goes live in this mode
  without the commit's own hook having run (what that hook checks is the site's own choice;
  Site B's runs no tests). Today's mode keeps today's behaviour, where the clone's setting
  decides.
- **The hook's variables.** Every site's pre-push hook clears, before any step, the
  repository variables git hands a hook (the list git itself prints for that purpose; from a
  linked worktree it includes `GIT_DIR`). Then a gate step that runs git in a scratch repo,
  or from a subfolder, finds the right repository by itself.
- **After the push.** The live-build poll and any site's own smoke test run inside the
  worktree before it is removed, so they read the published copy's site address and expected
  text. A smoke test using only Node's built-ins and the network needs no packages. Once the
  live site serves the id, the run reads `production` on GitHub once more, with `git
  ls-remote`, which starts no housekeeping (checked). If `production` has moved past the id,
  it says a newer publish followed and that which of the two builds the live site ends on
  depends on Cloudflare, not checked here, so to look at the commit it serves. No `exec` in
  `ship.sh` may replace the shell, since the exit trap would then never run (one site's
  smoke-test retry does exactly that today). The test bans `exec` in the script outright, a
  deliberately wider rule: the script needs none.
- **One publish per clone at a time.** Before the fetch, the run takes a lock by creating a
  folder in the clone's shared git folder (creating a folder either succeeds or fails, at
  once), then writes its process id and that process's start time, as `ps` reports it, into
  it. A process counts as still running only if that id exists with that same start time,
  so a reused id does not; where `ps` cannot report a start time (Windows' Git Bash), the run
  says it cannot tell. Any existing lock stops the run; a run never removes a lock it did not
  take. The stop message names the lock's process and start time, and its full path. If that
  process is still running, it says a publish is under way and gives no removal command. If
  not, or if it cannot tell, it gives the command that removes the lock, saying first that a
  push the stopped run had started may still be running in its worktree (a killed script's
  push and gate can outlive it), so to check that none is before running it. The exit trap
  removes the lock only if the lock still names this run's process id and start time.
- **Leftovers.** Before it creates its worktree, the run adds the worktree's path, its own
  process id and start time to a list kept beside the lock in the clone's shared git folder,
  and takes the line off once its own worktree is removed. Ship never removes a worktree it
  did not make in that same run. Holding the lock, and before adding its own line, it reads
  the list: each entry left by an earlier run (a hard kill) is reported with its path and the
  command that removes it, to use once no process is working in that folder. A leftover
  never blocks a publish, since every run makes a new folder. A worktree that is not on the
  list is never touched or reported, whatever its name or lock. Ship never prunes, itself or
  through a fetch's housekeeping: a prune also drops a worktree whose folder is only away,
  and with it the only record of commits made there.
- **Signals.** The push stays in the foreground, as today, so a credential prompt still
  reaches the terminal, and a Ctrl-C still reaches every process there, git and the gate
  included, exactly as today; how the gate's own tools clean up on it is unchanged and not
  promised here. The script kills nothing itself. It traps interrupt, terminate, hang-up and
  quit only to note that a stop was asked for; bash runs that note when the step in the
  foreground ends, so a terminate sent to the script alone lets the current step finish and
  the worktree is never removed under a running gate. After each step, and at each poll of
  the live check, the script looks at the note; if it is set, it stops there, says so, and
  exits with a failure status. The live check's waits are guarded against stop-on-error, so
  a Ctrl-C during one ends the wait, not the script, and the note is read.
- **The push's result.** git's own exit status is written down by the push step itself, into
  a scratch file inside the same pipeline, and never read back from the pipeline afterwards:
  on bash 3.2 a stop noted the moment the pipeline ends resets that, and a failed push read
  as a success. The log, by contrast, can miss lines after an interrupt, since its writer
  stops too. So a line found in the log counts, a line missing from it proves nothing after
  a stop. The result is reported like this:
  - git succeeded: the publish went out (after a stop, the message also names what was
    skipped: the live check, a smoke test).
  - git failed and no stop was noted: today's classifier, unchanged.
  - git failed after a stop: the classifier's arms that rest on git's own words in the log
    stand (production moved; GitHub unreachable at connect time; a login or host-key failure,
    which says nothing was published and to read git's error, not to try again). Anything
    else says the publish may or may not have landed and to run ship again, as for a dropped
    connection; a stopped run never says "nothing was published" because a line is missing.
  - no status at all (an empty or missing file: an interrupt ended the step before it wrote
    one, or the disk was full): the same "may or may not have landed", stop or not; never a
    success, never "nothing was published".
- **The exit trap.** One trap removes the worktree (by path, forced twice, from the starting
  folder), this run's own line in the leftovers list, its own lock and the status file, and
  the scratch log only on a success exit, skipping whatever this run did not make (a run in
  today's mode makes neither a worktree nor a lock). It saves the exit status first, then
  turns off stop-on-error and ignores the stop signals while it cleans up, so neither a
  failing step nor a second Ctrl-C skips the rest or turns a success into a failure, and it
  exits with the saved status. If git's removal of its own worktree fails, it deletes that
  folder, the one this run made (its path comes from this run's own temp- folder call, never
  from a list or a name), removes the record by path, and says so. On a failure exit it
  keeps the log and prints its path, since that log is the evidence for a "may or may not
  have landed".
- **The messages.** Every message that today says "you're still safely on 'main'" says, in
  worktree mode, that this folder was not touched; the script's own rule that each message
  states the state you are in now holds in both modes. In worktree mode the first and the
  last line name the commit, as "GitHub's `main` as of the fetch" with its first 12
  characters, since `main` may move on during the run.
- **Other steps' status.** Every step other than the push has its status read from a plain
  command, never from a pipeline's per-command status: on bash 3.2 only a pipeline's lost its
  status to a deferred stop; a plain command's survived.
- **Known limit, not solved here (the maintainer's choice, 2026-10-21).** The gate's test
  server uses one port per site, derived from its address, so another session's test run or
  preview of the same site makes the gate fail; nothing is published. The run names that
  case when Playwright's "is already used" line is in the log (the gate's own output reaches
  the log as it is; only the nested output of `check_ship_push.sh`'s own failing cases is
  prefixed and left out, D3.1): another test run, a preview,
  or a test server left behind by a stopped run holds the site's test port. A port per
  checkout, as Site C has, is a separate change.

**D3. Where it lands: in this order, one pull request each.**
1. Template: `ship.sh` and its test, template-version 0.21 → 0.22 in both, `wire-hooks.mjs`
   (leaving the hooks setting alone when ship's variable is set, with a case in its test),
   and the pre-push hook (clearing its variables), with a case in the hook's own test that
   pushes from a linked worktree. The push classifier also gains the remote's ref-lock
   refusal as "production moved", in both modes; its fixture uses stock git's wording, and
   GitHub's stays unchecked. `PUBLISHING.md` gets the new messages and an emergency section
   (to undo a bad publish: revert the change on `main`, then ship; if ship itself is broken:
   a push of `main` to `production` by hand, skipping the pre-push hook on purpose (its own
   test runs `ship.sh`, which may be the broken part), then a look at the live site's
   `/build.txt` to see the commit it serves; how to check the clone's hooks setting),
   `AGENTS.md` the setting (the folder check still applies without it), the README a note
   for shared machines, and a release-note row tells sites. The toolkit's template tests
   also run `check_ship_push.sh` on the macOS leg of their existing any-shell job, where
   `/bin/bash` is 3.2 and a skipped case S10 (e) fails the step. That job already feeds the
   combined check that `main`'s ruleset requires before a merge, so the bash 3.2 case runs
   before any release and not first in a site's gate; it adds no job, permission, trigger or
   secret. In the gate output that `check_ship_push.sh` prints for one of its own failing
   cases, every nested line starts with a `|` after two spaces; nothing else in the gate's
   output is prefixed. Every check `ship.sh` makes on its log (the gate lines, the port line
   and all of the push classifier's patterns) reads the log with those lines taken out, and
   the gate-line checks are anchored at the start of a line, so a red gate's nested lines
   are never read as the outer publish's own; a stubbed case puts a nested login failure,
   refusal, port line and pass line in a red gate's log and asserts they change nothing. The
   mktemp guard cannot test `ship.sh` (its probe runs outside a git repo and stops at the
   first git call), so `ship.sh` stays on its exempt list with the reason updated, and
   `check_ship_push.sh` covers a failing mktemp instead. No pipe ends early under pipefail.
   The CDPATH guard does not run `ship.sh` or its test, so review checks their `cd`s. Diff
   review at High depth.
2. Site A (byte-identical to 0.21): both files replaced with 0.22, and its pre-push hook
   clears its variables. Its inline prepare line becomes the template's `wire-hooks.mjs`
   (copied in), so a publish's install leaves the hooks setting alone. The sites' hooks
   differ from the template's, so the template's hook test does not cover them: each site's
   copy of `check_ship_push.sh` checks that its own hook clears the variables before its
   first step.
3. Site B (0.20, plus a post-publish smoke test; its pre-push hook only refuses direct
   pushes to `main`): take 0.22 without the install step, re-apply the smoke test as a
   marked site addition without `exec`, and its hook clears its variables too, for any step
   added later, with the same check. Its test copy drops S6 (no install), and its marker
   reads "0.22 plus site additions".
4. Site C (0.20, restructured, plus an analytics probe and a "no common history" arm), right
   after: take 0.22 and re-apply both as marked blocks, rather than graft the mode into its
   own structure: then one structure is tested everywhere. Its pre-push hook clears its
   variables, with the same check, and its inline prepare line becomes the template's
   `wire-hooks.mjs`, as for Site A. Its marker reads "0.22 plus site additions". Its existing
   no-common-history test case carries over. Nothing tests the probe today; this plan does
   not change that.
5. The setting is switched on per clone by the maintainer after each site merges. It is not
   part of any pull request.

## D4. Scenarios: given / when `npm run ship` runs / then

| # | Given | Then |
|---|-------|------|
| S1 | setting off, a page edited but not committed | stops exactly as today; nothing published |
| S2 | setting on, folder on a feature branch, one edited file, an untracked data folder; GitHub's `main` two commits ahead of production | names the mode; lists the two as not published; production equals GitHub's `main`; last line "✓ LIVE … 2 not published"; no message claims this folder is on `main`; folder's branch, files and index unchanged; no worktree or lock left; exit 0 |
| S3 | setting on, this computer's `main` one commit ahead of GitHub | publishes GitHub's `main`; says 1 commit is not on GitHub and was not published |
| S4 | GitHub's `main` has a broken page | tests fail inside the worktree; "Nothing was published", and this folder was not touched; no worktree left; exit 1 |
| S5 | GitHub unreachable on both tries | today's message, with "this folder was not touched"; no worktree left |
| S6 | the package install fails | stops before the push; nothing published; no worktree left |
| S7 | another clone moves production while the gate runs | on stock git, "production moved", run again; nothing published; no worktree left. On GitHub, the same if GitHub words it alike, else "can't name" (nothing published either way) |
| S8 | an earlier run was killed hard: its worktree is still registered (with or without its folder) and on ship's list, and its lock is left (with or without a process id) | stops, naming the lock, its full path, that its process is not running (or, without a process id, that it cannot tell, with the warning), that a push the killed run started may still be running, and the command to remove the lock; after that command, the next run reports the leftover worktree with its path and removal command, publishes, and leaves the leftover registered and untouched |
| S9 | a publish is already running in this clone | the second stops, naming the first and saying a publish is under way, with no removal command; afterwards the lock still exists and names the first, whose worktree and run are unaffected |
| S10 | (a) Ctrl-C during the gate, an interrupt to the whole foreground group; (b) a terminate sent to the script alone during the gate; (c) Ctrl-C during the push with a hook that prints no gate lines, git failing; (d) a terminate sent to the script alone during the push with such a hook, git succeeding; (e) on the Mac's built-in bash 3.2, started as `/bin/bash`, a terminate sent to the script alone while the gate fails; (f) Ctrl-C during the live check | (a) the gate stops; "stopped", "may or may not have landed", run again; production unchanged; exit non-zero; no worktree or lock left. (b) the gate, which runs inside the push step, and the push finish; the message says a stop was asked for and that the publish went out, live check skipped; production equals the id; exit non-zero; no worktree or lock left. (c) "may or may not have landed", run again; exit non-zero; no worktree or lock left. (d) "the publish went out", live check skipped; exit non-zero; no worktree or lock left. (e) the run's bash is 3.2; the failed push is never reported as a success ("may or may not have landed"); production unchanged; exit non-zero; its deliberate break is reading git's result back from the pipeline, which on bash 3.2 then reads as a success. (f) "the publish went out", the live check stopped; exit non-zero; no worktree or lock left |
| S11 | the folder's pre-push hook or tests are edited, not committed | the gate that runs is GitHub `main`'s |
| S12 | Site B's smoke test fails once, then passes | LIVE; no worktree left |
| S13 | GitHub's `main` already equals production | "Everything up-to-date"; live check passes; no worktree left |
| S14 | another session's worktree of this clone, its folder moved away; git's housekeeping set to prune at once and due to run | still registered, untouched, after the publish; its deliberate break is the fetch without the two settings, which drops the record |
| S15 | setting on, one mktemp call fails (each of the script's calls in turn) | stops before any push; no worktree and no lock left; folder and a committed sentinel file in it unchanged; the error is the last line |
| S16 | setting on, the folder's `ship.sh` differs from GitHub `main`'s (its body edited with the version line untouched, or an older branch) | stops before the worktree is made, naming both versions (or, when they match, saying the two files differ anyway); nothing published; its lock removed |
| S17 | setting on, the push succeeds but its status file cannot be written (a full disk) | "may or may not have landed", run again; never a success, never "nothing was published"; no worktree or lock left |
| S18 | setting on, the clone's shared hooks setting names another folder, or is unset, or another session changes it during the gate | the worktree's committed hook still runs; with no executable `scripts/hooks/pre-push` in the commit, the run stops before the push and nothing is published |
| S19 | a worktree of this clone that ship did not make, named like ship's own, locked, with uncommitted files in it | untouched after a publish: still registered, still locked, its files unchanged |
| S20 | the clone's fetch setting narrowed to `production` only, and GitHub's `main` ahead of the clone's `origin/main` | the run still fetches `main`; production equals GitHub's `main` as of the fetch, and the first and last lines name that commit |
| S21 | another session set the clone's hooks setting to its own folder before the publish | the setting is that folder throughout: the tiny gate reads the clone's hooks setting during the push and records it, and the test reads it after; both installs run the real `wire-hooks.mjs` (the stubbed npm calls it as the prepare step, in ship's install and in an install the tiny gate starts); its deliberate break is leaving the variable off the push, which must make the case fail |

**How it is tested.** The existing stubbed-git test grows cases for the checks and messages
(S1, S3, S5, S16), the ref-lock refusal, the nested-lines case of D3.1, and a check that
`ship.sh` has no `exec`. Its pin on today's push command becomes `push origin
<id>:refs/heads/production`. A new section in the same file uses real git: a bare repo in a
temp folder as `origin`, a clone with `main` and `production`, and a tiny committed pre-push
gate that prints this kit's own two gate lines, with only npm, curl, sleep and (for S15,
S17) mktemp stubbed. It shuts out the machine's own git settings (no global or system
config, its own name and email, branches created as `main`) and clears the repository
variables a hook hands it. It starts the real `ship.sh` the way `npm run ship` does (except
S10 (e), below) and asserts the exit status, production's commit, the printed lists, ship's
own leftovers list (empty after every run that was not killed hard), the folder's branch,
status and index, the lock, and the worktree list, for S2, S4, S6, S7 (a second clone moves
production from inside the gate), S8, S9, S10, S11, S13, S14, S15, S17, S18, S19, S20 and
S21. Cases that need two things at once wait on a marker file the tiny gate writes, not on a
fixed delay, so they cannot flake in the pre-push gate where this file runs; each wait still
has a generous time limit measured with the real `sleep`, so a broken case fails instead of
hanging a publish. S10 starts the run under test with perl in a process group of its own,
with interrupt and quit set back to their defaults (a background job of a script starts with
them ignored, and macOS has no `setsid`), checks that group differs from the test's own, and
only then signals it, so an interrupt can never reach a real publish the test runs inside;
on exit the test ends every group it started. Its case (c) uses a tiny hook that prints no
gate lines; its case (e) starts `/bin/bash scripts/ship.sh` and checks the run's bash is 3.2
before signalling, and runs only where that bash is installed, skipped with a printed note
elsewhere (the toolkit's macOS leg runs it, D3.1). On Windows, S10 is skipped with a printed
note. A failing case's nested output is printed behind a "  | " prefix. The hook's own test
gains a push from a linked worktree: a step sees no `GIT_DIR`, and the folder's top from a
subfolder is the worktree's root. Each new case must fail once on a deliberate break before
it counts. S12 is tested in Site B's own copy.

## Decided by the maintainer, 2026-10-21

- O1. A saved setting only, no per-run switch: a switch is one more path to test, and a
  helper could use it to get past a beginner's block.
- O2. With the setting on, unsaved page edits do not block; they are listed like any other
  file. The script cannot tell one session's page edit from another's.
- O3. Site C is ported right after Sites A and B, not left on 0.20: left, it keeps today's
  block.
- O4. Stopping a publish halfway: after its fix had needed a cut and then failed again in
  review, the maintainer chose the simple fix (the push step writes down git's own result)
  and one more review round on that part.
- O5. The shared test port stays a known limit (D2); a port per checkout is a separate
  change.
