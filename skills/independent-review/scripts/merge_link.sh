#!/usr/bin/env bash
#
# merge_link.sh — the artifact of a MERGE LINK (SKILL.md step 6): after the base was merged into a
# change, or the change rebased, what changed in the change's own files since the last reviewed
# head, merge effects included — reviewed instead of a full round.
#
#   merge_link.sh [--suggest-callees] <old-merge-base> <last-reviewed-head> <new-merge-base> [-- <extra path>...]
#
# Run inside the repository; the new head is HEAD. Prints the diff on stdout (empty: nothing of the
# change moved). Extra paths — files the merge changed that the change's code calls — are added.
#
# --suggest-callees helps find those extra paths: it lists on stderr each file the merge changed
# on the base side (old-merge-base to new-merge-base) whose module name — its basename without the
# last extension, which the basename contains — appears in one of the change's own files at HEAD
# (a plain fixed-string git grep). Suggestions only, never added to the diff: a short or common
# name (index, utils) matches text that is no call, and a call by any other name is missed.
#
# The change's own files are taken from BOTH pairs, the old (old-merge-base...last-reviewed-head)
# and the new (new-merge-base...HEAD): a file whose merge resolution threw the change's edit away
# matches the new base again, drops out of the new pair's list, and would otherwise never show
# (final full read, 2026-09-26). Both lists are built with --no-renames: a rename is listed by its
# new name alone, so a merge that brought the old name back left it out (Codex, round 4). The lists
# are NUL-separated and the paths passed literally
# (--literal-pathspecs), so a space, '*', '?', '[' or a leading ':' in a name is just a character;
# docs/reviews/ is dropped from the list itself, since a literal pathspec cannot carry :(exclude).
set -euo pipefail
usage() { echo "usage: merge_link.sh [--suggest-callees] <old-merge-base> <last-reviewed-head> <new-merge-base> [-- <extra path>...]" >&2; exit 2; }
suggest=0
if [ "${1:-}" = --suggest-callees ]; then suggest=1; shift; fi
[ $# -ge 3 ] || usage
old_base="$1" reviewed="$2" new_base="$3"; shift 3
if [ $# -gt 0 ]; then [ "$1" = -- ] || usage; shift; fi
for rev in "$old_base" "$reviewed" "$new_base" HEAD; do
  git rev-parse --verify --quiet "$rev^{commit}" >/dev/null || { echo "merge_link.sh: not a commit: $rev" >&2; exit 2; }
done
tmp="$(mktemp -d "${TMPDIR:-/tmp}/merge_link.XXXXXX")"; trap 'rm -rf "$tmp"' EXIT
own="$tmp/own" list="$tmp/list"
{ git diff -z --no-renames --name-only "$old_base...$reviewed"
  git diff -z --no-renames --name-only "$new_base...HEAD"
} | perl -0 -ne 'print unless m{^docs/reviews/} or $seen{$_}++' >"$own"
{ cat "$own"; for p in "$@"; do printf '%s\0' "$p"; done
} | perl -0 -ne 'print unless m{^docs/reviews/} or $seen{$_}++' >"$list"
# An empty list must print nothing: xargs with no input runs git diff unfiltered on GNU (the whole
# tree) and not at all on BSD — neither is the merge link.
if [ "$suggest" = 1 ] && [ ! -s "$own" ]; then
  echo "merge_link.sh: no suggestions — the change has no files of its own outside docs/reviews/ to search." >&2
fi
[ -s "$list" ] || exit 0
if [ "$suggest" = 1 ] && [ -s "$own" ]; then
  # Candidates: the base side's changed files, less those already in the list.
  git diff -z --no-renames --name-only "$old_base" "$new_base" |
    perl -0 -e 'open my $f, "<", shift or die "$!\n"; my %in = map { $_ => 1 } <$f>;
      while (<STDIN>) { print unless m{^docs/reviews/} or $in{$_} }' "$list" >"$tmp/cand"
  own_files=(); while IFS= read -r -d '' p; do own_files+=("$p"); done <"$own"
  found=0
  while IFS= read -r -d '' p; do
    name="${p##*/}"; stem="${name%.*}"; [ -n "$stem" ] || stem="$name"
    rc=0; git --literal-pathspecs grep -q -F -e "$stem" HEAD -- "${own_files[@]}" || rc=$?
    case $rc in
      0) [ "$found" = 1 ] || echo "merge_link.sh: files the merge changed on the base side whose name the change's own files mention — check each, and pass the ones its code calls after --:" >&2
         found=1; printf '  %s\n' "$p" >&2 ;;
      1) ;;
      *) echo "merge_link.sh: git grep failed (exit $rc) for: $p" >&2; exit 2 ;;
    esac
  done <"$tmp/cand"
  [ "$found" = 1 ] || echo "merge_link.sh: no file the merge changed on the base side is named in the change's own files." >&2
fi
xargs -0 git --literal-pathspecs diff "$reviewed" HEAD -- <"$list"
