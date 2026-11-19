#!/usr/bin/env bash
# Prints the git tree of the `directory` branch for a commit: the pointer plugin of
# pointer/ (five files) and nothing else, for Anthropic's plugin directory. The tree holds
# the commit's own blobs, so nothing is converted on the way. scripts/publish_directory.sh
# checks the result again before it publishes.
#
# usage: scripts/build_directory_tree.sh <commit> [--out <empty dir>]
#   --out also unpacks the tree into that folder.
set -euo pipefail

# Source path on main, then its path on the branch. The test in scripts/plugin.test.mjs
# writes the same map itself.
MAP=(pointer/plugin.json:.claude-plugin/plugin.json
  .claude-plugin/icon.png:.claude-plugin/icon.png
  pointer/README.md:README.md
  LICENSE:LICENSE
  pointer/get-croftweaver.md:skills/get-croftweaver/SKILL.md)

usage() { echo "usage: $0 <commit> [--out <empty dir>]" >&2; exit 2; }
[ $# -eq 1 ] || [ $# -eq 3 ] || usage
commit=$1
out=
if [ $# -eq 3 ]; then
  [ "$2" = --out ] || usage
  out=$3
fi
git rev-parse -q --verify "$commit^{commit}" >/dev/null || { echo "$0: no commit named $commit" >&2; exit 1; }

work=$(mktemp -d) || { echo "$0: could not make a temporary folder" >&2; exit 1; }
trap 'rm -rf "$work"' EXIT
export GIT_INDEX_FILE="$work/index"
git read-tree --empty
for pair in "${MAP[@]}"; do
  src=${pair%%:*}
  dst=${pair#*:}
  # --full-tree: paths count from the top of the clone, wherever this was started.
  entry=$(git ls-tree --full-tree "$commit" -- "$src")
  [ -n "$entry" ] || { echo "$0: $commit has no $src" >&2; exit 1; }
  mode=${entry%% *}
  sha=${entry#* blob }
  [ "$sha" != "$entry" ] || { echo "$0: $src in $commit is not a file" >&2; exit 1; }
  sha=${sha%%$'\t'*}
  printf '%s %s\t%s\n' "$mode" "$sha" "$dst" | git update-index --index-info
done
tree=$(git write-tree)
unset GIT_INDEX_FILE

if [ -n "$out" ]; then
  mkdir -p "$out"
  [ -z "$(ls -A "$out")" ] || { echo "$0: $out is not empty" >&2; exit 1; }
  # Run from the top: from a subfolder, git archive would write only that folder's part.
  top=$(git rev-parse --show-toplevel 2>/dev/null) || top=.
  git -C "$top" archive --format=tar "$tree" | tar -x -C "$out"
fi
echo "$tree"
