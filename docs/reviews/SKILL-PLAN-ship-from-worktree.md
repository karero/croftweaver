# Plan: publish from a throwaway worktree, so a busy folder never blocks `npm run ship`

Plan only; nothing is built. It goes through the plan review gate and, because it changes
the script that publishes to a live site, one red-team pass, then waits for the maintainer's
go. Where this plan and the shipped files disagree, the files win.

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-10-20 | this file |
| 2 | Plan review gate (High depth: deploy code that deletes folders), then red team | ▶ round 6 | trail `REVIEW-plan-2026-10-21-plan-ship-from-worktree-f6266ac.md` |
| 3 | Template change (D3.1) | ⏸ | — |
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
  automatic housekeeping by default; one fetch can switch it off (`--no-auto-maintenance`,
  accepted by git 2.33).
- bash ran the exit trap on interrupt, terminate and hang-up, in 3.2 and 5.3, and skipped
  it after an `exec` that replaces the shell (not after a redirect-only `exec`). A hard kill
  or a power cut skips it too. With no trap for the signal itself, a terminate sent to the
  script's own process alone runs the exit trap at once while a child it waits on keeps
  running. With a trap for the signal, bash runs that trap only when the step in the
  foreground ends, both for a terminate sent to the script alone and for an interrupt sent to
  the whole group (as a terminal's Ctrl-C is), and the script then carries on; in the second
  case the child had the interrupt too and stopped at once. On bash 3.2 (the Mac's own), a
  trapped terminate that arrives during a pipeline resets the pipeline's per-command status:
  a step that exited 7 then read as 0 (bash 5.3 kept 7); a status the step wrote to a file
  itself read 7 on both. Inside a trap, `set +e` resets the exit status to 0, so the status
  must be saved before it.
- Playwright (1.63, Site A's copy) starts the test server in its own process group (its
  launcher's `detached` option, on macOS and Linux) and sets no terminate handler for it, so
  a terminate can leave the server holding its port; an interrupt to the group made
  Playwright stop it (a reviewer's reproduction). The template asks for 1.64, not checked.
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
folder. Uncommitted and untracked files never block: before the push they are listed (the
first 20, then a count) under "Not published: in this folder, not on GitHub's main", and the
last line of any run that printed the list, success or failure, repeats the count. Commits
on this computer's `main` that GitHub lacks never block either; the script gives their
number (none when there is no local `main`) and says to get them onto
GitHub's `main` if they should go live (a pull request, or a push where direct pushes to
`main` are allowed). The folder's branch does not matter, so a session can run ship from its
own worktree, as long as its `ship.sh` is the one on GitHub's `main` (D2).

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
  housekeeping off, so a publish never starts git's own prune (checked: with housekeeping due
  and set to prune at once, a plain fetch dropped a moved-away worktree's record, and the
  same fetch with the switch kept it). In worktree mode `origin/main` must exist (new
  message: no `main` on GitHub yet); in both modes `origin/production` must, as today.
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
  template-version lines. If they differ, it stops and names both template-versions, or,
  when those match, says the two files differ anyway; nothing is published, and the exit
  trap removes its lock. The folder may be on any branch, with edits, and a half-edited or
  outdated copy must not publish. The fix it names is to run ship from a checkout up to date
  with GitHub's `main`. Today's mode needs no such check: it already requires a clean folder
  equal to its upstream.
- **What the run touches in the clone.** It reads the folder's status with git's optional
  locks off, so it never takes the index lock another session's `git add` may need. It
  updates the clone's shared records: the fetched GitHub branches (as today), a lock and a
  worktree entry while it runs, and possibly the hooks path (below). It changes nothing in
  the folder itself. It resolves the clone's shared git folder to a full path first, since
  git prints a relative one in a primary checkout.
- **The install.** Before the push the script runs `npm ci` in the worktree, so the lockfile
  is never rewritten and the gate tests the commit. Every publish in this mode therefore needs
  the npm registry or a warm npm cache. A gate that runs `scripts/verify.mjs` installs a
  second time (its install stamp is missing), about 5 s more; accepted, rather than have ship
  write that file's private stamp. A failed install stops before the push. The install runs
  the packages' prepare step, which tries to set the clone's hooks path to `scripts/hooks`
  (as any install in that clone already does); if setting it fails, that step says so and
  the install carries on. So a gate switched off by unsetting the hooks path may be switched
  back on by this publish's install. Accepted: it errs toward testing. Site B's hook only
  refuses direct pushes to `main` and runs no step that needs packages, so its copy skips the
  install (D3.3). The list of what is not published is printed after the worktree is made,
  once the script's temp files exist, and before the install.
- **The gate.** After the install, from inside the worktree, the run reads the hooks path
  the push will use. If it is the relative `scripts/hooks`, the worktree's committed hook
  runs. If it is anything else, or unset, the run says before the push which hook will run,
  or that none will.
- **The hook's variables.** Every site's pre-push hook clears, before any step, the
  repository variables git hands a hook (the list git itself prints for that purpose; from a
  linked worktree it includes `GIT_DIR`). Then a gate step that runs git in a scratch repo,
  or from a subfolder, finds the right repository by itself.
- **After the push.** The live-build poll and any site's own smoke test run inside the
  worktree before it is removed, so they read the published copy's site address and expected
  text. A smoke test using only Node's built-ins and the network needs no packages. No `exec`
  in `ship.sh` may replace the shell, since the exit trap would then never run (one site's
  smoke-test retry does exactly that today). The test bans `exec` in the script outright, a
  deliberately wider rule: the script needs none.
- **One publish per clone at a time.** Before the fetch, the run takes a lock by creating a
  folder in the clone's shared git folder (creating a folder either succeeds or fails, at
  once), then writes its process id and start time into it. Any existing lock stops the run;
  a run never removes a lock it did not take. The stop message names the lock's process and
  start time when they are there, whether that process seems to be running, the lock's full
  path, and the command that removes it, to use only if no publish is running. So after a
  hard kill, the next publish needs that one command first. The exit trap removes the lock
  only if this run took it.
- **Leftovers.** The worktree is a fresh temp folder whose name only this script makes: a
  fixed prefix, the process id, a random tail. Holding the lock, the run looks for that name
  in git's worktree list wherever the folder is (the temp folder differs between sessions,
  and on macOS git prints `/private/var/…` for `/var/…`). Any such worktree is a leftover of
  an earlier run, since only the lock holder makes one: it is removed by its own path, forced
  twice, and the run says so. Ship never prunes, itself or through a fetch's housekeeping: a
  prune also drops a worktree whose folder is only away, and with it the only record of
  commits made there.
- **Signals.** The push stays in the foreground, as today, so a credential prompt still
  reaches the terminal, and a Ctrl-C still reaches every process there, git and the gate
  included, exactly as today; how the gate's own tools clean up on it is unchanged and not
  promised here. The script kills nothing itself. git's own exit status is written down by
  the push step itself, into a scratch file inside the same pipeline, and never read back
  from the pipeline afterwards: on bash 3.2 a stop noted the moment the pipeline ends resets
  that, and a failed push read as a success. A missing or empty status file (an interrupt
  can end the step before it writes one) means git's result is unknown, never a success.
  The script traps interrupt, terminate, hang-up
  and quit only to note that a stop was asked for; bash runs that note when the step in the
  foreground ends, so a terminate sent to the script alone lets the current step finish and
  the worktree is never removed under a running gate. After each step, and at each poll of
  the live check, the script looks at the note; if it is set, it stops there, says so, and
  exits with a failure status. Once git has reported a successful push, a stop at any later
  step says the publish went out and names what was skipped (the live check, a smoke test).
  If the push failed or its result is unknown, the push classifier reads git's output first,
  as today, and its message stands where it names the failure; where it would fall to "a
  reason this script can't name", the stop message says "nothing was published" only when
  the gate's start line is in the log and its pass line is not. Those two lines are the ones
  this kit's own pre-push hook prints, and that hook prints its pass line before it lets the
  push go on, so with them the push never reached the network. In every other case,
  including a hook that prints no such lines (Site B's), no hook, or another hook with other
  lines, it says the publish may or may not have landed and to run ship again, as for a
  dropped connection.
- **The exit trap.** One trap removes the worktree (by path, forced twice, from the starting
  folder), its own lock and the scratch log, skipping whatever this run did not make (a run
  in today's mode makes neither a worktree nor a lock). It saves the exit status first, then
  turns off stop-on-error, so a failing step neither skips the rest nor turns a success into
  a failure, and it exits with the saved status. If removal fails, it deletes the folder,
  removes the record by path, and says so.
- **The messages.** Every message that today says "you're still safely on 'main'" says, in
  worktree mode, that this folder was not touched; the script's own rule that each message
  states the state you are in now holds in both modes.
- **Known limit, not solved here (the maintainer's choice, 2026-10-21).** The gate's test
  server uses one port per site, derived from its address, so another session's test run or
  preview of the same site makes the gate fail (Playwright's error is printed, then "can't
  name"; nothing is published). A port per checkout, as Site C has, is a separate change.

**D3. Where it lands: in this order, one pull request each.**
1. Template: `ship.sh` and its test, template-version 0.21 → 0.22 in both, and the pre-push
   hook (clearing its variables), with a case in the hook's own test that pushes from a
   linked worktree. The push classifier also gains the remote's ref-lock refusal as
   "production moved", in both modes; its fixture uses stock git's wording, and GitHub's
   stays unchecked. `PUBLISHING.md` gets the new messages, `AGENTS.md` the setting (the
   folder check still applies without it), the README a note for shared machines, and a
   release-note row tells sites. The mktemp guard cannot test `ship.sh` (its probe runs
   outside a git repo and stops at the first git call), so `ship.sh` stays on its exempt list
   with the reason updated, and `check_ship_push.sh` covers a failing mktemp instead. No pipe
   ends early under pipefail. The CDPATH guard does not run `ship.sh` or its test, so review
   checks their `cd`s. Diff review at High depth.
2. Site A (byte-identical to 0.21): both files replaced with 0.22, and its pre-push hook
   clears its variables. The sites' hooks differ from the template's, so the template's hook
   test does not cover them: each site's copy of `check_ship_push.sh` checks that its own hook
   clears the variables before its first step.
3. Site B (0.20, plus a post-publish smoke test; its pre-push hook only refuses direct
   pushes to `main`): take
   0.22 without the install step, re-apply the smoke test as a marked site addition without
   `exec`, and its hook clears its variables too, for any step added later, with the same
   check. Its test copy drops S6 (no install), and its marker reads "0.22 plus site
   additions".
4. Site C (0.20, restructured, plus an analytics probe and a "no common history" arm), right
   after: take 0.22 and re-apply both as marked blocks, rather than graft the mode into its
   own structure: then one structure is tested everywhere. Its pre-push hook clears its
   variables, with the same check. Its marker reads "0.22 plus site additions". Its existing
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
| S8 | an earlier run was killed hard: its worktree is still registered (with or without its folder) and its lock is left (with or without a process id) | stops, naming the lock, its full path and the command to remove it; after that command, the next run removes the leftover worktree, says so, and publishes |
| S9 | a publish is already running in this clone | the second stops, naming the first; afterwards the lock still exists and names the first, which is unaffected |
| S10 | (a) Ctrl-C during the gate, an interrupt to the whole foreground group; (b) a terminate sent to the script alone during the gate; (c) Ctrl-C during the push with a hook that prints no gate lines, git failing; (d) a terminate sent to the script alone during the push with such a hook, git succeeding; (e) on the Mac's built-in bash 3.2, a terminate sent to the script alone during the push, git failing | (a) the gate stops; "stopped", "nothing was published"; exit non-zero; no worktree or lock left. (b) the gate and the push finish; the message says a stop was asked for and that the publish went out, live check skipped; production equals the id; exit non-zero; no worktree or lock left. (c) "may or may not have landed", run again; exit non-zero; no worktree or lock left. (d) "the publish went out", live check skipped; exit non-zero; no worktree or lock left. (e) the failed push is reported as failed, never as a success; production unchanged; exit non-zero; its deliberate break is reading git's result back from the pipeline, which on bash 3.2 then reads as a success |
| S11 | the folder's pre-push hook or tests are edited, not committed | the gate that runs is GitHub `main`'s |
| S12 | Site B's smoke test fails once, then passes | LIVE; no worktree left |
| S13 | GitHub's `main` already equals production | "Everything up-to-date"; live check passes; no worktree left |
| S14 | another session's worktree of this clone, its folder moved away; git's housekeeping set to prune at once and due to run | still registered, untouched, after the publish; its deliberate break is the fetch without the switch, which drops the record |
| S15 | setting on, one mktemp call fails (each of the script's calls in turn) | stops before any push; no worktree; folder and a committed sentinel file in it unchanged; the error is the last line |
| S16 | setting on, the folder's `ship.sh` differs from GitHub `main`'s (its body edited with the version line untouched, or an older branch) | stops before the worktree is made, naming both versions (or, when they match, saying the two files differ anyway); nothing published; its lock removed |

**How it is tested.** The existing stubbed-git test grows cases for the checks and messages
(S1, S3, S5, S16), the ref-lock refusal, and a check that `ship.sh` has no `exec`. Its pin
on today's push command becomes `push origin <id>:refs/heads/production`. A new section in
the same file (so no new wiring in the hook or CI) uses real git: a bare repo in a temp
folder as `origin`, a clone with `main` and `production`, and a tiny committed pre-push
gate, with only npm, curl, sleep and (for S15) mktemp stubbed. It shuts out the machine's
own git settings (no global or system config, its own name and email, branches created as
`main`) and clears the repository variables a hook hands it. It starts the real `ship.sh`
the way `npm run ship` does and asserts the exit status, production's commit, the printed
lists, the folder's branch, status and index, the lock, and the worktree list, for S2, S4,
S6, S7 (a second clone moves production from inside the gate), S8, S9, S10, S11, S13, S14
and S15. Cases that need two things at once wait on a marker file the tiny gate writes,
never on time, so they cannot flake in the pre-push gate where this file runs. S10 starts
the run under test in its own process group, checks that group differs from the test's own,
and only then signals it, so an interrupt can never reach a real publish the test runs
inside; its case (c) uses a tiny hook that prints no gate lines, and its case (e) runs only
where bash 3.2 is installed (the Mac's own `/bin/bash`), skipped with a printed note
elsewhere. On Windows, S10 is skipped with a
printed note. The hook's own test gains a push from a linked worktree: a step sees no
`GIT_DIR`, and the folder's top from a subfolder is the worktree's root. Each new case must
fail once on a deliberate break before it counts. S12 is tested in Site B's own copy.

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
