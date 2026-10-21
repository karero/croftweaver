// Run by the "prepare" script in package.json, so on every `npm install`: points git's
// core.hooksPath at scripts/hooks, which turns on the pre-push gate in scripts/hooks/pre-push.
//
// Why a Node script instead of a line of shell in package.json: npm hands a script line to
// a shell, by default sh on macOS and Linux and cmd.exe on Windows. The line this replaces
// (`unset …; git rev-parse … 2>/dev/null | grep -q . || git config … || true`) is sh
// syntax; `node scripts/wire-hooks.mjs` holds no shell syntax at all.
//
// What it does, and must keep doing:
//  - site at the root of its git repo: set core.hooksPath to scripts/hooks;
//  - site in a subfolder of a bigger repo: change nothing. Pointed at a scripts/hooks the
//    bigger repo does not have, git runs none of that repo's hooks, and says nothing;
//  - no git repo around the site, or no git on this machine: nothing to do;
//  - SHIP_KEEP_HOOKS_PATH set (by scripts/ship.sh): change nothing (below);
//  - never fail the install: every case above exits 0, without a word. If git refuses the
//    write at a repo's root, that is one line on stderr and still exit 0.
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

// The site is the folder that holds scripts/ — found from this file, not from the current
// folder: `scripts/hooks` means the hooks next to this file only where that folder is the
// top of the repo, wherever the script was started from.
const site = join(dirname(fileURLToPath(import.meta.url)), '..');

// `npm run ship`, publishing GitHub's main from a throwaway worktree (ship.fromGitHub), installs
// the packages there, and the pre-push gate it runs may install again. Each install would write
// core.hooksPath, which every worktree of the clone shares and another session may have set its
// own way. ship.sh sets this variable for both, so the setting is never changed by a publish.
if (process.env.SHIP_KEEP_HOOKS_PATH) process.exit(0);

// A git hook that runs `npm install` can hand down GIT_DIR (in a linked worktree git
// exports an absolute one), and a git started with --git-dir and --work-tree hands its
// hooks GIT_WORK_TREE as well. Either one can make git take the site's folder for the top
// of the working tree, so a site in a subfolder would pass for the root. Without the two, git
// finds the repo from the site's folder.
delete process.env.GIT_DIR;
delete process.env.GIT_WORK_TREE;

// No shell here either. stderr is dropped: outside a repo git's "fatal: not a git
// repository" is the expected answer, not news for whoever runs the install.
const git = (...args) =>
  spawnSync('git', args, { cwd: site, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });

// The path from the top of the repo down to the site: empty when the site is the top.
// A git that is missing or finds no repo has no status 0, and nothing is written.
const prefix = git('rev-parse', '--show-prefix');
if (prefix.status === 0 && prefix.stdout.trim() === '') {
  const set = git('config', 'core.hooksPath', 'scripts/hooks');
  // The one case that says a word: git is here, the site is the top of its repo, and git
  // refused the write (a locked or read-only config). The gate is off and nothing else
  // would tell.
  if (set.status !== 0) {
    console.error('pre-push hook NOT wired: `git config core.hooksPath scripts/hooks` failed. Run it in the site\'s folder to see why.');
  }
}
