#!/usr/bin/env bash
#
# test_install_pin.sh — drives scripts/install.sh and its Codex mirror against a
# throwaway repo, one of whose skills is symlinked into a SIBLING WORKTREE of the same
# repo (a pin: that skill runs at a vetted commit, not at whatever the checkout holds).
#
# Why it exists: both installers removed any existing symlink and re-pointed it at the
# checkout, so re-running one silently undid such a pin — the pinned skill quietly went
# back to following the checkout, with nothing said. A pin is now kept, and these cases
# pin all three parts of that: what counts as a pin (a linked worktree of this repo, at
# the same skill), what does not (the main checkout, another skill, another repo), and
# that every case where the guard cannot run says so instead of clobbering in silence.
#
# Usage: bash scripts/test_install_pin.sh
set -u
if ! command -v git >/dev/null 2>&1; then
  # A zip recipient without git should not fail `make check` over an installer test.
  echo "SKIP: test_install_pin.sh needs git (it builds a throwaway repo and worktree)"
  exit 0
fi
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
T="$(mktemp -d "${TMPDIR:-/tmp}/install-pin-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
# Hermetic: a developer's global commit.gpgsign, hooksPath or templateDir must not decide
# whether this test passes (round 3, both reviewers).
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git="git -c user.name=t -c user.email=t@t -c init.defaultBranch=main -c commit.gpgsign=false -c core.hooksPath=/dev/null"
fails=0
check() { if "${@:2}"; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s\n' "$1"; fails=$((fails+1)); fi; }
# Both sides must exist AND resolve: two unresolvable paths would otherwise compare equal
# and turn a broken fixture into a passing assertion (rounds 2 and 3).
same_dir() {
  local a b
  [ -d "$1" ] && [ -d "$2" ] || return 1
  a="$(cd -P "$1" 2>/dev/null && pwd)" ; b="$(cd -P "$2" 2>/dev/null && pwd)"
  [ -n "$a" ] && [ -n "$b" ] && [ "$a" = "$b" ]
}

# build_repo <dir> <installer> — a repo with skills, alpha differing between two commits.
# The installer is committed BEFORE both, so a worktree at the first commit can run it
# (that is how the "installing from a linked worktree" cases work).
build_repo() {
  local R="$1" script="$2" first
  mkdir -p "$R/scripts" "$R/skills/alpha" "$R/skills/beta" "$R/skills/gamma" "$R/skills/delta"
  cp "$HERE/$script" "$R/scripts/$script"
  printf 'v2\n' >"$R/skills/alpha/SKILL.md"
  for s in beta gamma delta; do printf 'v2\n' >"$R/skills/$s/SKILL.md"; done
  $git init -q "$R"; $git -C "$R" add -A; $git -C "$R" commit -qm two
  first="$($git -C "$R" rev-parse HEAD)"
  printf 'v3\n' >"$R/skills/alpha/SKILL.md"; $git -C "$R" commit -qam three
  printf '%s' "$first"
}

# one_installer <script name> <skills-dir env var> <case label>
one_installer() {
  local script="$1" var="$2" label="$3" R O DEST DEST2 PIN PIN2 BROKEN out rc first
  R="$T/$label/repo"; O="$T/$label/other"; DEST="$T/$label/dest"; DEST2="$T/$label/dest2"
  PIN="$T/$label/pin"; PIN2="$T/$label/pin2"; BROKEN="$T/$label/broken"
  mkdir -p "$O/skills/beta" "$DEST" "$DEST2" "$BROKEN/skills/epsilon"
  first="$(build_repo "$R" "$script")"
  # Pins: two sibling LINKED worktrees of the same repo.
  $git -C "$R" worktree add -q --detach "$PIN" "$first"
  $git -C "$R" worktree add -q --detach "$PIN2" "$first"
  # A stale link: an unrelated copy in a DIFFERENT repo.
  printf 'other\n' >"$O/skills/beta/SKILL.md"; $git init -q "$O"; $git -C "$O" add -A; $git -C "$O" commit -qm other
  # A directory that looks like a worktree but whose metadata git cannot read.
  printf 'gitdir: /nowhere/that/exists\n' >"$BROKEN/.git"; printf 'x\n' >"$BROKEN/skills/epsilon/SKILL.md"
  mkdir -p "$R/skills/epsilon"; printf 'v2\n' >"$R/skills/epsilon/SKILL.md"
  $git -C "$R" add -A; $git -C "$R" commit -qm epsilon

  ln -s "$PIN/skills/alpha" "$DEST/alpha"           # a pin (absolute)
  ln -s "$O/skills/beta" "$DEST/beta"               # stale: another repo
  ln -s "$PIN/skills/alpha" "$DEST/gamma"           # same repo, WRONG skill
  ln -s "$PIN/skills/nowhere" "$DEST/delta"         # dangling
  ln -s "$BROKEN/skills/epsilon" "$DEST/epsilon"    # unreadable worktree metadata

  out="$(env "$var=$DEST" bash "$R/scripts/$script" 2>&1)"; rc=$?
  check "$label: install succeeds" [ "$rc" = 0 ]
  check "$label: the pin is kept" same_dir "$DEST/alpha" "$PIN/skills/alpha"
  check "$label: it says the pin was kept" grep -q "kept pinned alpha" <<<"$out"
  check "$label: the pinned skill still reads its own commit" [ "$(cat "$DEST/alpha/SKILL.md")" = v2 ]
  check "$label: a stale link to another repo is refreshed" same_dir "$DEST/beta" "$R/skills/beta"
  check "$label: a link to the WRONG skill is refreshed" same_dir "$DEST/gamma" "$R/skills/gamma"
  check "$label: a dangling link is refreshed" same_dir "$DEST/delta" "$R/skills/delta"
  check "$label: an unreadable worktree is refreshed" same_dir "$DEST/epsilon" "$R/skills/epsilon"
  check "$label: and moving it away is not silent" grep -q "relinking epsilon (was → " <<<"$out"
  check "$label: nor is moving a stale link away" grep -q "relinking beta (was → " <<<"$out"
  check "$label: no guard-off note when the guard ran" [ "$(grep -c 'pin detection was off' <<<"$out")" = 0 ]

  out="$(env "$var=$DEST" bash "$R/scripts/$script" --force 2>&1)"; rc=$?
  check "$label: --force succeeds" [ "$rc" = 0 ]
  check "$label: --force relinks the pin" same_dir "$DEST/alpha" "$R/skills/alpha"
  check "$label: --force keeps nothing back" [ "$(grep -c 'kept pinned' <<<"$out")" = 0 ]

  # A RELATIVE link into the pin is a pin too (the installer resolves it).
  rm -f "$DEST/alpha"; ( cd "$DEST" && ln -s "../pin/skills/alpha" alpha )
  out="$(env "$var=$DEST" bash "$R/scripts/$script" 2>&1)"; rc=$?
  check "$label: a relative-link run succeeds" [ "$rc" = 0 ]
  check "$label: a relative link into the pin is kept" same_dir "$DEST/alpha" "$PIN/skills/alpha"

  # Installing FROM a linked worktree: a link to the main checkout must refresh (that is
  # what a previous install left), while a link to ANOTHER linked worktree is a pin.
  ln -s "$R/skills/alpha" "$DEST2/alpha"; ln -s "$PIN2/skills/beta" "$DEST2/beta"
  out="$(env "$var=$DEST2" bash "$PIN/scripts/$script" 2>&1)"; rc=$?
  check "$label: installing from a worktree succeeds" [ "$rc" = 0 ]
  check "$label: a link to the main checkout is refreshed" same_dir "$DEST2/alpha" "$PIN/skills/alpha"
  check "$label: and it is not called a pin" [ "$(grep -c 'kept pinned alpha' <<<"$out")" = 0 ]
  check "$label: a link to another linked worktree is kept" same_dir "$DEST2/beta" "$PIN2/skills/beta"

  # A real directory is still backed up, not clobbered (pre-existing behaviour).
  rm -f "$DEST/alpha"; mkdir -p "$DEST/alpha"; printf 'mine\n' >"$DEST/alpha/SKILL.md"
  env "$var=$DEST" bash "$R/scripts/$script" >/dev/null 2>&1; rc=$?
  check "$label: the backup run succeeds" [ "$rc" = 0 ]
  check "$label: a real directory is backed up" [ "$(cat "$DEST/alpha.pre-website-builder.bak/SKILL.md")" = mine ]
  check "$label: and the skill is linked to the checkout" same_dir "$DEST/alpha" "$R/skills/alpha"

  env "$var=$DEST" bash "$R/scripts/$script" --nope >/dev/null 2>&1; rc=$?
  check "$label: an unknown flag exits 2" [ "$rc" = 2 ]
  env "$var=$DEST" bash "$R/scripts/$script" --force --nope >/dev/null 2>&1; rc=$?
  check "$label: a trailing argument exits 2" [ "$rc" = 2 ]
}

# A git too old for `rev-parse --path-format` cannot tell a pin from a stale link, so the
# installer must relink everything rather than trust junk — and must SAY the guard was off.
# Old rev-parse does one of two things with an option it does not know: fail, or echo it
# back and still exit 0. Both are simulated, and the fixture itself is asserted, because a
# stub that merely errors would test the failing variant twice (round 2, both reviewers).
old_git() {
  local script="$1" var="$2" variant="$3" R DEST BIN first rc probe out
  R="$T/oldgit-$variant-$script/repo"; DEST="$T/oldgit-$variant-$script/dest"; BIN="$T/oldgit-$variant-$script/bin"
  mkdir -p "$DEST" "$BIN"
  first="$(build_repo "$R" "$script")"
  $git -C "$R" worktree add -q --detach "$T/oldgit-$variant-$script/pin" "$first"
  ln -s "$T/oldgit-$variant-$script/pin/skills/alpha" "$DEST/alpha"
  if [ "$variant" = fails ]; then
    printf '#!/bin/sh\nfor a in "$@"; do [ "$a" = "--path-format=absolute" ] && { echo "error: unknown option" >&2; exit 129; }; done\nexec %s "$@"\n' \
      "$(command -v git)" >"$BIN/git"
  else
    # The installer always calls: git -C <dir> rev-parse --path-format=absolute <what>.
    # Echo the unknown option, drop it, run the rest — exit status comes from real git.
    printf '#!/bin/sh\nif [ "$4" = "--path-format=absolute" ]; then echo "$4"; exec %s "$1" "$2" "$3" "$5"; fi\nexec %s "$@"\n' \
      "$(command -v git)" "$(command -v git)" >"$BIN/git"
  fi
  chmod +x "$BIN/git"
  # The fixture must behave as advertised before it can prove anything about the installer.
  probe="$(PATH="$BIN:$PATH" git -C "$R" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"; rc=$?
  if [ "$variant" = echoes ]; then
    check "old git ($variant, $script): the stub exits 0" [ "$rc" = 0 ]
    check "old git ($variant, $script): the stub echoes the option" grep -q -- '--path-format=absolute' <<<"$probe"
    check "old git ($variant, $script): its output is not one path" [ "$(printf '%s\n' "$probe" | wc -l | tr -d ' ')" -gt 1 ]
  else
    check "old git ($variant, $script): the stub fails" [ "$rc" != 0 ]
  fi
  out="$(PATH="$BIN:$PATH" env "$var=$DEST" bash "$R/scripts/$script" 2>&1)"; rc=$?
  check "old git ($variant, $script): install still succeeds" [ "$rc" = 0 ]
  check "old git ($variant, $script): falls back to relinking" same_dir "$DEST/alpha" "$R/skills/alpha"
  check "old git ($variant, $script): says the guard was off" grep -q "pin detection was off" <<<"$out"
}

# No git at all: same fallback, and it must name that cause rather than blaming an old git.
no_git() {
  local R DEST BIN first rc out b
  R="$T/nogit/repo"; DEST="$T/nogit/dest"; BIN="$T/nogit/bin"
  mkdir -p "$DEST" "$BIN"
  first="$(build_repo "$R" install.sh)"
  $git -C "$R" worktree add -q --detach "$T/nogit/pin" "$first"
  ln -s "$T/nogit/pin/skills/alpha" "$DEST/alpha"
  # A PATH holding everything the installer needs except git.
  for b in bash basename dirname mkdir ln rm; do ln -s "$(command -v "$b")" "$BIN/$b"; done
  out="$(env -i PATH="$BIN" CLAUDE_SKILLS_DIR="$DEST" bash "$R/scripts/install.sh" 2>&1)"; rc=$?
  check "no git: install still succeeds" [ "$rc" = 0 ]
  check "no git: falls back to relinking" same_dir "$DEST/alpha" "$R/skills/alpha"
  check "no git: names git's absence" grep -q "git was not found" <<<"$out"
}

one_installer install.sh CLAUDE_SKILLS_DIR claude
one_installer install-codex.sh CODEX_SKILLS_DIR codex
old_git install.sh CLAUDE_SKILLS_DIR fails
old_git install.sh CLAUDE_SKILLS_DIR echoes
old_git install-codex.sh CODEX_SKILLS_DIR fails
old_git install-codex.sh CODEX_SKILLS_DIR echoes
no_git

if [ $fails -ne 0 ]; then echo "$fails check(s) FAILED"; exit 1; fi
echo "all checks passed"
