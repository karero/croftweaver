#!/usr/bin/env bash
# Publishes a release to the branch `directory`, which Anthropic's plugin directory follows:
# one commit holding scripts/build_directory_tree.sh's tree, whose message names the
# release's commit on a `Source:` line. The release-tag workflow runs it after `stable`
# moved; a person runs the same command when that step failed.
#
# usage: scripts/publish_directory.sh <release tag, e.g. v0.34>
#
# Refuses a tag not on main, a `directory` whose last commit names no source, and a
# release older than the one already published. Pushes without force.
set -euo pipefail

fail() { echo "::error::$*" >&2; exit 1; }
[ $# -eq 1 ] || { echo "usage: $0 <release tag>" >&2; exit 2; }
tag=$1
here=$(cd "$(dirname "$0")" && pwd)
commit=$(git rev-parse -q --verify "$tag^{commit}") || fail "no tag named $tag here"

git fetch -q origin main
git merge-base --is-ancestor "$commit" FETCH_HEAD || fail "$tag is not on main: directory stays where it is"

parent=
if git ls-remote --exit-code origin refs/heads/directory >/dev/null; then
  git fetch -q origin +refs/heads/directory:refs/remotes/origin/directory
  parent=$(git rev-parse refs/remotes/origin/directory)
  source=$(git log -1 --format=%B "$parent" | sed -n 's/^Source: \([0-9a-f]\{40\}\)$/\1/p' | tail -n 1)
  [ -n "$source" ] || fail "directory's last commit names no source (a 'Source: <commit>' line): publish by hand only after looking at it"
  git merge-base --is-ancestor "$source" "$commit" || fail "directory already holds a later release ($source): $tag is not published"
  if [ "$source" = "$commit" ]; then
    echo "directory already holds $tag: nothing to do"
    exit 0
  fi
else
  status=$?
  [ "$status" -eq 2 ] || fail "could not read origin's branches (git ls-remote exit $status)"
fi

tree=$("$here/build_directory_tree.sh" "$commit")
bot='github-actions[bot]'
mail='41898282+github-actions[bot]@users.noreply.github.com'
new=$(GIT_AUTHOR_NAME=$bot GIT_AUTHOR_EMAIL=$mail GIT_COMMITTER_NAME=$bot GIT_COMMITTER_EMAIL=$mail \
  git commit-tree "$tree" ${parent:+-p "$parent"} -m "Croftweaver $tag" -m "Source: $commit")
git push -q origin "$new:refs/heads/directory"
[ "$(git ls-remote origin refs/heads/directory | cut -f1)" = "$new" ] || fail "the push went through, but origin's directory is not $new"
echo "directory now holds $tag ($new)"
