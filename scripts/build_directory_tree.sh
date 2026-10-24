#!/usr/bin/env bash
# Prints the git tree of the `directory` branch for a commit: the plugin and nothing else,
# for Anthropic's plugin directory (docs/reviews/SKILL-PLAN-directory-plugin-folder.md).
# The tree holds the commit's own blobs, so nothing is converted on the way.
#
# usage: scripts/build_directory_tree.sh <commit> [--out <empty dir>]
#   --out also unpacks the tree into that folder.
set -euo pipefail

# What the branch holds. The test in scripts/plugin.test.mjs writes the same list itself.
KEEP=(.claude-plugin/plugin.json .claude-plugin/icon.png skills
  docs/CLOUDFLARE-CHECKLIST.md docs/PAGES-OR-WORKERS.md docs/WHAT-THE-SKILLS-RUN.md
  README.md LICENSE THIRD-PARTY-LICENSES.md SECURITY.md .gitattributes)
# Left out: the toolkit's own tests that no skill runs, and independent-review (a review
# tool, not one that builds sites; the maintainer's decision, 2026-10-24).
DROP=$'\t''skills/(independent-review|(facts-check|new-website|search-console-insights|website-brand-kit)/scripts/tests)/'

usage() { echo "usage: $0 <commit> [--out <empty dir>]" >&2; exit 2; }
[ $# -eq 1 ] || [ $# -eq 3 ] || usage
commit=$1
out=
if [ $# -eq 3 ]; then
  [ "$2" = --out ] || usage
  out=$3
fi
git rev-parse -q --verify "$commit^{commit}" >/dev/null || { echo "$0: no commit named $commit" >&2; exit 1; }

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
export GIT_INDEX_FILE="$work/index"
git read-tree --empty
git ls-tree -r -z "$commit" -- "${KEEP[@]}" | { grep -zvE "$DROP" || true; } | git update-index -z --index-info
tree=$(git write-tree)
unset GIT_INDEX_FILE

if [ -n "$out" ]; then
  mkdir -p "$out"
  [ -z "$(ls -A "$out")" ] || { echo "$0: $out is not empty" >&2; exit 1; }
  git archive "$tree" | tar -x -C "$out"
fi
echo "$tree"
