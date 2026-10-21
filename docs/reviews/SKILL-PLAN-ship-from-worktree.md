# Plan: publish from a throwaway worktree, so a busy folder never blocks `npm run ship`

Plan only; nothing is built. It goes through the plan review gate and, because it changes
the script that publishes to a live site, one red-team pass, then waits for the maintainer's
go. Where this plan and the shipped files disagree, the files win.

| # | Step | State | Evidence |
|---|------|-------|----------|
| 1 | This plan | ✅ written 2026-10-20 | this file |
| 2 | Plan review gate (High depth: deploy code that deletes folders), then red team | ▶ round 1 | — |
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
commit that goes live, and the shared folder is neither read nor changed.

## Checked 2026-10-20 (a scratch repo, git 2.33, bash 3.2 and 5.3)

- A second worktree cannot check out `main` while another has it ("'main' is already
  checked out at …"). A detached one at the fetched commit can.
- Detached, the branch name reads `HEAD` and the upstream lookup fails ("HEAD does not
  point to a branch"), so today's branch and upstream checks cannot run there unchanged.
- A push from the worktree runs the worktree's own committed pre-push hook, not the shared
  folder's edited copy. Pushing a commit id to `refs/heads/production` works.
- Removing a worktree holding untracked files (packages, build output) needs the force
  option. A worktree whose folder has vanished is listed as prunable; pruning drops it.
- bash ran the exit trap on interrupt, terminate and hang-up, in 3.2 and 5.3, and skipped
  it after `exec`. A hard kill or a power cut skips it too.
- From a linked worktree, git hands the pre-push hook `GIT_DIR` set to that worktree's git
  folder (from the primary checkout, none). A gate step that runs git in a scratch repo would
  then hit the site instead. None does today: in the template and the three sites, gate
  steps call git only to read the current commit or to set the hooks path.
- A fresh install of the template's packages took 4.6 s with a warm npm cache (286 packages).
- The template's test server never reuses a server already on its port, so a dev server
  left running elsewhere cannot answer the gate's tests.

## Decisions

**D1. Who gets it, and what happens to uncommitted files.** The script cannot tell whose
files are in the folder; only the person running it knows. So the mode is opt-in, through a
per-checkout git setting, `ship.fromGitHub`, set once on a shared machine; there is no
per-run switch (decided 2026-10-21, below). It lives in the local git config, never in the repo, so a fresh clone (a beginner,
a new owner) keeps today's behaviour, block included: "I edited a page and forgot to
commit" still stops the publish with today's message, which does not mention the setting.

With the setting on, the first line says the run publishes GitHub's `main` and ignores this
folder. Uncommitted and untracked files never block: before the push they are listed (the
first 20, then a count) under "Not published: in this folder, not on GitHub's main", and the
last line, success or failure, repeats the count. Commits on this computer's `main` that
GitHub lacks never block either; the script gives their number and says to push them if
they should go live. The folder's branch does not matter, so a session can run ship from its
own worktree.

*Counter-argument:* with the setting on, the maintainer's own forgotten edit stays
unpublished while the script reports success. Accepted: on a shared machine GitHub's `main`
is the only state everyone agrees on, and the list says what was left out. A per-run flag
would be more visible, but every session has to remember it, and one that forgets hits
today's block again.

**D2. The checks in worktree mode.** With the setting off, the script runs in the folder as
today; of the changes below, only the switch to the commit id applies.
- The fetch is unchanged (same classifier). `origin/main` must exist (new message: no `main`
  on GitHub yet), and so must `origin/production`, as today.
- The commit to publish is `origin/main`'s id, read once after the fetch. Everything after
  uses that id: the worktree is created detached at it, the divergence check asks whether
  `origin/production` is its ancestor, the push sends it to `refs/heads/production`, and the
  live check waits for it. Today the push and the live check read local `main`; both modes
  switch to the id, so a commit landing on local `main` mid-publish changes nothing.
- "Main is pushed" holds by construction: the commit came from GitHub. The branch check and
  the upstream check are skipped; D1's two lists replace them.
- Before the push the script installs the packages in the worktree, because the gate builds
  and tests there. A gate that runs `scripts/verify.mjs` installs a second time (its install
  stamp is missing), costing about 5 s; accepted, rather than have ship write that file's
  private stamp. A failed install stops before the push.
- The post-publish checks (the live-build poll, and any site's own smoke test) run inside
  the worktree before it is removed, so they read the published copy's site address and
  expected text. A smoke test using only Node's built-ins and the network needs no packages.
  No `exec` is allowed in the post-publish path: it replaces the shell, and the exit trap
  never runs. One site's smoke-test retry does exactly that today.
- The worktree folder is a fresh temp folder whose name only this script makes: a fixed
  prefix, the process id, a random tail. At start the script lists the repo's worktrees and
  touches only those matching that name under the temp folder. If the process it names is alive,
  another publish is running: stop, nothing published. If not, it is a leftover: remove it
  and say so. If its folder is gone: prune. (Pruning drops every unlocked record whose
  folder is gone, not only ours; git's own housekeeping does the same once such a record is
  three months old, and a record without its folder holds no files.) A reused
  process id makes a leftover look alive; the message names the folder and how to remove it
  by hand, so the error is on the side of not publishing.
- One exit trap removes the worktree (forced, run from the starting folder) and the scratch
  log. If removal fails, it deletes the folder, prunes, and says so. The trap covers success,
  every failure arm, a failed install and an interrupt.

**D3. Where it lands: in this order, one pull request each.**
1. Template: `ship.sh` and its test, template-version 0.21 → 0.22 in both. `PUBLISHING.md`
   gets the new messages, `AGENTS.md` the setting (the folder check still applies without
   it), the README a note for shared machines, and a release-note row tells sites. The temp
   folder follows the repo's mktemp-guard pattern and joins that guard's list. No pipe ends
   early under pipefail, and every `cd` is CDPATH-safe. Diff review at Normal or above: the
   code publishes to a live site.
2. Site A (byte-identical to 0.21): both files replaced with 0.22.
3. Site B (0.20, plus a post-publish smoke test; its pre-push hook runs no build): take
   0.22, re-apply the smoke test as a marked site addition with the `exec` fix.
4. Site C (0.20, restructured, plus an analytics probe and a "no common history" arm):
   last. Take 0.22 and re-apply both as marked blocks, rather than graft the mode into its
   own structure: then one structure is tested everywhere. Its marker reads "0.22 plus site
   additions". Its existing no-common-history test case carries over. Nothing tests the
   probe today; this plan does not change that.
5. The setting is switched on per checkout by the maintainer after each site merges. It is
   not part of any pull request.

## D4. Scenarios: given / when `npm run ship` runs / then

| # | Given | Then |
|---|-------|------|
| S1 | setting off, a page edited but not committed | stops exactly as today; nothing published |
| S2 | setting on, folder on a feature branch, one edited file, an untracked data folder; GitHub's `main` two commits ahead of production | names the mode; lists the two as not published; production equals GitHub's `main`; last line "✓ LIVE … 2 not published"; folder's branch and files unchanged; no worktree left |
| S3 | setting on, this computer's `main` one commit ahead of GitHub | publishes GitHub's `main`; says 1 commit is not on GitHub and was not published |
| S4 | GitHub's `main` has a broken page | tests fail inside the worktree; "Nothing was published"; no worktree left; folder unchanged |
| S5 | GitHub unreachable on both tries | today's message; no worktree left |
| S6 | the package install fails | stops before the push; nothing published; no worktree left |
| S7 | production moves while the gate runs | today's "production moved" message; no worktree left; a re-run starts fresh from the new state |
| S8 | an earlier run was killed hard; its worktree is still registered | says it removed a leftover from an earlier run, then publishes; if the system already deleted the folder, the record is pruned |
| S9 | a publish is already running for this site | the second stops, names the running one's folder; the first is unaffected |
| S10 | Ctrl-C during the build | nothing published; no worktree left |
| S11 | the folder's pre-push hook or tests are edited, not committed | the gate that runs is GitHub `main`'s |
| S12 | Site B's smoke test fails once, then passes | LIVE; no worktree left |
| S13 | GitHub's `main` already equals production | "Everything up-to-date"; live check passes; no worktree left |

**How it is tested.** The existing stubbed-git test grows cases for the checks and
messages (S1, S3, S5, S9's message); its stub learns the new git calls. A new section in
the same file (so no new wiring in the hook or CI) uses real git: a bare repo in a temp
folder as `origin`, a clone with `main` and `production`, and a tiny committed pre-push
gate, with only npm, curl and sleep stubbed. It starts the real `ship.sh` the way
`npm run ship` does and asserts production's commit, the printed lists, the folder's branch
and status, and the worktree list, for S2, S4, S6, S7 (a second clone moves production from
inside the gate), S8 (a registered worktree with a dead process id), S10 (an interrupt sent
mid-gate), S11 and S13. It first clears the repository variables git hands a hook (from a
linked worktree, `GIT_DIR`, as checked above): inherited, they would aim its git calls at
the real site. Each new case must fail once on a deliberate break before it counts. S12 is tested in
Site B's own copy.

## Decided by the maintainer, 2026-10-21

- O1. A saved setting only, no per-run switch: a switch is one more path to test, and a
  helper could use it to get past a beginner's block.
- O2. With the setting on, unsaved page edits do not block; they are listed like any other
  file. The script cannot tell one session's page edit from another's.
- O3. Site C is ported right after Sites A and B, not left on 0.20: left, it keeps today's
  block.
