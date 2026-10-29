#!/usr/bin/env bash
#
# test_template_coverage.sh — runs scripts/check_template_coverage.sh on throwaway copies of
# the templates and of whats-new.sh, each changed one way, and judges its exit status and what
# it names.
#
# Why it exists: the guard used to scan templates/astro/ only. The root templates beside it
# (AGENTS.md, SETUP.md and the rest) and the files under templates/claude/ were listed in
# whats-new.sh by hand, and nothing checked the list: with AGENTS.md dropped from it, or a new
# file at the templates root, the guard still passed, so sites were never told when that file
# changed. These cases pin that the guard now fails for a file left out at the root, under
# claude/ and (as before) under astro/, for a tracked or a site-owned root file dropped from
# its list, and for a folder it cannot read, and that it passes on the templates as they are.
#
# It enters the way make check and CI do: it runs the guard script, which finds its files from
# where it sits, so the copies are laid out as the repo is.
#
# Usage: bash scripts/test_template_coverage.sh
set -u
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(dirname -- "$HERE")"
T="$(mktemp -d "${TMPDIR:-/tmp}/template-coverage-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
fails=0; skips=0; n=0

# fresh — sets c to a new copy of what the guard reads. Not run in $(…), so a failed copy
# ends the test here instead of leaving c empty for the cases below.
fresh() {
  c="$T/repo.$n"; n=$((n+1))
  mkdir -p "$c/scripts" "$c/skills/new-website" \
    && cp "$ROOT/scripts/whats-new.sh" "$ROOT/scripts/check_template_coverage.sh" "$c/scripts/" \
    && cp -R "$ROOT/skills/new-website/templates" "$c/skills/new-website/" \
    && cp "$ROOT/LICENSE" "$c/" \
    || { echo "FAIL — could not copy the templates to $c."; exit 1; }
}

# drop <copy> <list> <path> — removes <path> from the <list>= line of the copy's whats-new.sh.
drop() {
  local wn="$1/scripts/whats-new.sh"
  sed "/^$2=/s# $3##" "$wn" >"$wn.new" && mv "$wn.new" "$wn"
  if grep -E "^$2=" "$wn" | grep -Fq -- " $3"; then
    echo "FAIL — could not drop $3 from $2 in the copy." >&2; exit 1
  fi
}

# expect <name> <copy> <pass|fail> [<text the output must hold>]
expect() {
  local out rc
  out="$(bash "$2/scripts/check_template_coverage.sh" 2>&1)"; rc=$?
  if [ "$3" = pass ] && [ "$rc" -ne 0 ]; then
    printf 'FAIL %s: the guard failed (exit %s):\n%s\n' "$1" "$rc" "$out"; fails=$((fails+1)); return
  fi
  if [ "$3" = fail ] && [ "$rc" -eq 0 ]; then
    printf 'FAIL %s: the guard passed:\n%s\n' "$1" "$out"; fails=$((fails+1)); return
  fi
  if [ -n "${4:-}" ] && ! grep -Fq -- "$4" <<<"$out"; then
    printf 'FAIL %s: the output does not name %s:\n%s\n' "$1" "$4" "$out"; fails=$((fails+1)); return
  fi
  printf 'ok   %s\n' "$1"
}

TPL=skills/new-website/templates

fresh
expect "the templates as they are pass" "$c" pass "accounted for"

LIC="$TPL/astro/CROFTWEAVER-LICENSE.md"
fresh; printf 'x' >>"$c/$LIC"
expect "a licence notice that differs from LICENSE by one byte fails" "$c" fail "$LIC differs from LICENSE"

fresh; rm "$c/$LIC"
expect "a missing licence notice fails" "$c" fail "$LIC"

fresh; rm "$c/LICENSE"
expect "a missing root LICENSE fails" "$c" fail "LICENSE is missing"

fresh; drop "$c" TEMPLATE_TRACKED "$TPL/AGENTS.md"
expect "a tracked root template dropped from TEMPLATE_TRACKED fails" "$c" fail "$TPL/AGENTS.md"

fresh; drop "$c" TEMPLATE_TRACKED "$TPL/CLAUDE.md"
expect "CLAUDE.md dropped from TEMPLATE_TRACKED fails" "$c" fail "$TPL/CLAUDE.md"

fresh; drop "$c" SITE_OWNED "$TPL/brand.md"
expect "a site-owned root template dropped from SITE_OWNED fails" "$c" fail "$TPL/brand.md"

fresh; echo new >"$c/$TPL/NEW.md"
expect "a new file at the templates root fails" "$c" fail "$TPL/NEW.md"

fresh; echo new >"$c/$TPL/claude/hooks/new-hook.mjs"
expect "a new file under templates/claude/ fails" "$c" fail "$TPL/claude/hooks/new-hook.mjs"

fresh; echo new >"$c/$TPL/astro/new-file.txt"
expect "a new file under templates/astro/ still fails" "$c" fail "$TPL/astro/new-file.txt"

# A folder find cannot read: the scan is incomplete, so the guard must stop, not pass on
# what it did see. Root reads any folder, so the case cannot be set up there.
if [ "$(id -u)" -ne 0 ]; then
  fresh; mkdir "$c/$TPL/unreadable" && echo x >"$c/$TPL/unreadable/f" && chmod 000 "$c/$TPL/unreadable"
  expect "a folder find cannot read fails" "$c" fail "find exited"
  chmod 755 "$c/$TPL/unreadable"
else
  echo "skip a folder find cannot read: running as root"; skips=$((skips+1))
fi

if [ "$fails" -ne 0 ]; then
  echo "test_template_coverage.sh: $fails case(s) failed"
  exit 1
fi
if [ "$skips" -ne 0 ]; then
  echo "test_template_coverage.sh: every case that ran passed ($skips skipped)"
else
  echo "test_template_coverage.sh: all cases passed"
fi
