#!/usr/bin/env bash
# Symlink every suite skill into the Codex skills dir (~/.agents/skills) so Codex loads
# them. Mirror of install.sh (which targets Claude Code's ~/.claude/skills). Idempotent:
# re-running just refreshes the links. An existing REAL directory with the same name is
# backed up to <name>.pre-website-builder.bak rather than clobbered.
# A symlink already pointing into ANOTHER WORKTREE of this repo is left alone: that is
# a deliberate pin to a vetted commit, and relinking it would silently undo someone's
# decision about which version of a skill runs. Pass --force to relink those too.
# Pin protection is best effort: where git cannot verify a target — an old git, no git,
# or a copy that is not a repo — links are refreshed, and a note says so.
set -euo pipefail

FORCE=0
case "${1:-}" in
  --force) FORCE=1 ;;
  "")      ;;
  *)       echo "usage: install-codex.sh [--force]" >&2; exit 2 ;;
esac
[ "$#" -le 1 ] || { echo "usage: install-codex.sh [--force]" >&2; exit 2; }

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
DEST="${CODEX_SKILLS_DIR:-$HOME/.agents/skills}"
mkdir -p "$DEST"
# Absolute from here on, as the Node installer resolves it: a relative DEST would let an
# exported CDPATH send the link checks below elsewhere and clobber a pin.
DEST="$(CDPATH= cd -- "$DEST" && pwd)"

# A pin is a link into a LINKED worktree of this repo, at the same skill. Every test
# below has to hold, because none of them alone means "pinned": worktrees of one repo
# share a git common dir, but so does this checkout itself (a link to the main checkout
# is what a previous install left, and must still refresh), and a link may point at a
# different skill entirely.
# `git rev-parse` echoes an option it does not understand and still exits 0, so a value
# counts only when it is a single absolute directory; otherwise the guard turns itself
# off and the old always-relink behaviour applies.
one_abs_dir() {
  # Git for Windows prints drive-letter paths (C:/…); the two sides are always compared
  # with each other, so either shape is fine as long as it is one absolute directory.
  case "$1" in
    /*|[A-Za-z]:/*) case "$1" in *"
"*) return 1 ;; esac; [ -d "$1" ] ;;
    *)  return 1 ;;
  esac
}
rp() { git -C "$1" rev-parse --path-format=absolute "$2" 2>/dev/null || true; }

repo_common="$(rp "$REPO_DIR" --git-common-dir)"
one_abs_dir "$repo_common" || repo_common=""
relinked_foreign=0

for src in "$REPO_DIR"/skills/*/; do
  name="$(basename "$src")"
  link="$DEST/$name"
  own="$(cd -P "$src" && pwd)"
  if [ -L "$link" ]; then
    # cd -P through the link resolves a relative target and fails on a dangling one.
    target="$(cd -P "$link" 2>/dev/null && pwd || true)"
    keep=0
    if [ "$FORCE" = 0 ] && [ -n "$repo_common" ] && [ -n "$target" ] && [ "$target" != "$own" ]; then
      link_common="$(rp "$target" --git-common-dir)"
      link_git="$(rp "$target" --git-dir)"
      link_top="$(rp "$target" --show-toplevel)"
      if one_abs_dir "$link_common" && one_abs_dir "$link_git" && one_abs_dir "$link_top"; then
        # Physical on both sides: a textual compare would miss a pin reached through a
        # symlinked path, and failing there silently relinks it.
        wt="$(cd -P "$link_top/skills/$name" 2>/dev/null && pwd || true)"
        if [ "$link_common" = "$repo_common" ] &&     # this repo
           [ "$link_git" != "$link_common" ] &&       # a linked worktree, not the checkout
           [ -n "$wt" ] && [ "$target" = "$wt" ]; then # and the same skill
          keep=1
        fi
      fi
    fi
    if [ "$keep" = 1 ]; then
      echo "kept pinned $name → $target (linked worktree of this repo; --force relinks)"
      continue
    fi
    # Never move a link away from somewhere else in silence — including a pin whose
    # worktree git can no longer read, which is exactly when silence would hurt.
    if [ -n "$target" ] && [ "$target" != "$own" ]; then
      echo "relinking $name (was → $target)"
      relinked_foreign=$((relinked_foreign + 1))
    fi
    rm "$link"                                   # stale/our symlink → refresh
  elif [ -e "$link" ]; then
    mv "$link" "$link.pre-website-builder.bak"   # real dir → keep a backup
    echo "backed up existing $name → $name.pre-website-builder.bak"
  fi
  ln -s "$REPO_DIR/skills/$name" "$link"
  echo "linked $name"
done
# Guard off AND links moved: say why, so a lost pin is never a silent surprise.
if [ -z "$repo_common" ] && [ "$relinked_foreign" -gt 0 ]; then
  if command -v git >/dev/null 2>&1; then
    echo "note: this checkout's git metadata could not be read (an old git, or not a repo), so pin detection was off and the links above were refreshed"
  else
    echo "note: git was not found, so pin detection was off and the links above were refreshed"
  fi
fi
echo "done → $DEST"
