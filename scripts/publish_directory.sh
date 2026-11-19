#!/usr/bin/env bash
# Publishes a release to the branch `directory`, which Anthropic's plugin directory follows:
# one commit holding scripts/build_directory_tree.sh's tree (the pointer plugin, five files),
# whose message names the release's commit on a `Source:` line. The release-tag workflow runs
# it after `stable` moved; a person runs the same command when that step failed.
#
# usage: scripts/publish_directory.sh <release tag, e.g. v0.34>
#        scripts/publish_directory.sh --check-tree <tree>
#        scripts/publish_directory.sh --compare <tree> <tree>
#
# Refuses a tag not on main, a `directory` whose last commit names no source, a release
# older than the one already published, and a tree that is not exactly the five files, as
# plain files. check_directory_files.mjs refuses a text file that is not UTF-8, holds a control
# character but tab and line breaks, or starts with `#!`, and an icon that is not an 8-bit RGB or
# RGBA PNG with whole chunks and rows (its own header says exactly what). Pushes without
# force. --check-tree runs that last check alone. --compare prints `same`, `version
# only` (the trees differ only in plugin.json's version) or the changed paths, one per line.
set -euo pipefail

fail() { echo "::error::$*" >&2; exit 1; }
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)

# The branch holds exactly these paths. Written out here, apart from the tree builder's map,
# so a change to one alone is refused.
ALLOWED=$'.claude-plugin/icon.png\n.claude-plugin/plugin.json\nLICENSE\nREADME.md\nskills/get-croftweaver/SKILL.md'

tree_arg() {
  [ "$(git cat-file -t "$1^{tree}" 2>/dev/null)" = tree ] || fail "no tree named $1 here"
  git rev-parse "$1^{tree}"
}

check_tree() {
  local tree=$1 mode type sha path paths= msg
  command -v node >/dev/null || fail "node is needed to check the directory tree and is not on PATH"
  while IFS= read -r -d '' entry; do
    path=${entry#*$'\t'}
    read -r mode type sha <<<"${entry%%$'\t'*}"
    paths+="$path"$'\n'
    [ "$mode" = 100644 ] || fail "$path in the directory tree has mode $mode: only plain files (100644) go to the directory"
    git cat-file -e "$sha" || fail "cannot read $path in the directory tree"
    # A pass needs both: the pipeline succeeded (pipefail) and the checker printed ok.
    if ! msg=$(git cat-file blob "$sha" | node "$here/check_directory_files.mjs" "$path") || [ "$msg" != ok ]; then
      [ -n "$msg" ] && [ "$msg" != ok ] || msg="could not be checked: reading it or check_directory_files.mjs failed, or printed nothing"
      fail "$path in the directory tree $msg"
    fi
  done < <(git ls-tree -r -z --full-tree "$tree")
  [ "$(printf '%s' "$paths" | LC_ALL=C sort)" = "$ALLOWED" ] \
    || fail "the directory tree is not exactly the five pointer files: got $(printf '%s' "$paths" | LC_ALL=C sort | tr '\n' ' ')"
}

# Paths that differ (a blob, a mode, or present in one tree only); `version only` when that is
# plugin.json, of the same mode and type in both, and it differs only in its root `version`.
compare_trees() {
  local a=$1 b=$2 changed pa pb la lb rc=0 out ma mb same
  [ "$a" != "$b" ] || { echo same; return; }
  la=$(git ls-tree -r --full-tree "$a") || fail "cannot list $a"
  lb=$(git ls-tree -r --full-tree "$b") || fail "cannot list $b"
  out=$(diff <(printf '%s\n' "$la") <(printf '%s\n' "$lb")) || rc=$?
  [ "$rc" -le 1 ] || fail "diff failed (exit $rc) comparing $a and $b"
  changed=$(printf '%s\n' "$out" | awk -F'\t' '/^[<>] /{print $2}' | LC_ALL=C sort -u)
  ma=$(git ls-tree --full-tree "$a" .claude-plugin/plugin.json | cut -f1 | cut -d' ' -f1,2)
  mb=$(git ls-tree --full-tree "$b" .claude-plugin/plugin.json | cut -f1 | cut -d' ' -f1,2)
  if [ "$changed" = .claude-plugin/plugin.json ] && [ "$ma" = "$mb" ]; then
    pa=$(git cat-file blob "$a:.claude-plugin/plugin.json") || fail "cannot read plugin.json in $a"
    pb=$(git cat-file blob "$b:.claude-plugin/plugin.json") || fail "cannot read plugin.json in $b"
    # Only the root "version" may differ. Both texts are parsed, and one that does not read back as
    # written (a repeated key, a number past 2^53, 1.0 for 1) counts as changed, never as equal.
    command -v node >/dev/null || fail "node is needed to compare plugin.json and is not on PATH"
    same=$(PA=$pa PB=$pb node -e '
      const d = (s) => {
        const o = JSON.parse(s);
        if (s.replace(/"(?:[^"\\]|\\.)*"|\s+/g, (m) => (m[0] === "\"" ? m : "")) !== JSON.stringify(o)) return null;
        delete o.version;
        return JSON.stringify(o);
      };
      const x = d(process.env.PA), y = d(process.env.PB);
      process.stdout.write(x !== null && x === y ? "yes" : "no");') \
      || fail "cannot parse plugin.json in $a or $b"
    if [ "$same" = yes ]; then
      echo "version only"; return
    fi
  fi
  [ -n "$changed" ] || fail "the trees $a and $b differ but no path does: cannot compare"
  printf '%s\n' "$changed"
}

case "${1:-}" in
  --check-tree)
    [ $# -eq 2 ] || { echo "usage: $0 --check-tree <tree>" >&2; exit 2; }
    t1=$(tree_arg "$2")
    check_tree "$t1"
    echo "ok: $2 is exactly the five pointer files"
    exit 0 ;;
  --compare)
    [ $# -eq 3 ] || { echo "usage: $0 --compare <tree> <tree>" >&2; exit 2; }
    t1=$(tree_arg "$2")
    t2=$(tree_arg "$3")
    compare_trees "$t1" "$t2"
    exit 0 ;;
esac
[ $# -eq 1 ] || { echo "usage: $0 <release tag> | --check-tree <tree> | --compare <tree> <tree>" >&2; exit 2; }
tag=$1
commit=$(git rev-parse -q --verify "$tag^{commit}") || fail "no tag named $tag here"

git fetch -q origin main
git merge-base --is-ancestor "$commit" FETCH_HEAD || fail "$tag is not on main: directory stays where it is"

parent=
if git ls-remote --exit-code origin refs/heads/directory >/dev/null; then
  git fetch -q origin +refs/heads/directory:refs/remotes/origin/directory
  parent=$(git rev-parse refs/remotes/origin/directory)
  source=$(git log -1 --format=%B "$parent" | sed -n 's/^Source: \([0-9a-f]\{40\}\)$/\1/p' | tail -n 1)
  [ -n "$source" ] || fail "directory's last commit names no source (a 'Source: <commit>' line): publish by hand only after looking at it"
  git cat-file -e "$source^{commit}" 2>/dev/null || fail "directory's source $source is not in this clone: fetch it first"
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
check_tree "$tree"
bot='github-actions[bot]'
mail='41898282+github-actions[bot]@users.noreply.github.com'
new=$(GIT_AUTHOR_NAME=$bot GIT_AUTHOR_EMAIL=$mail GIT_COMMITTER_NAME=$bot GIT_COMMITTER_EMAIL=$mail \
  git -c commit.gpgSign=false commit-tree "$tree" ${parent:+-p "$parent"} -m "Croftweaver $tag" -m "Source: $commit")
git push -q origin "$new:refs/heads/directory"
[ "$(git ls-remote origin refs/heads/directory | cut -f1)" = "$new" ] || fail "the push went through, but origin's directory is not $new"
echo "directory now holds $tag ($new)"
