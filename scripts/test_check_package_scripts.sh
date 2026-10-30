#!/usr/bin/env bash
#
# test_check_package_scripts.sh — runs scripts/check_package_scripts.sh on throwaway copies of
# scripts/, each changed one way, and judges its exit status and what it names.
#
# Why it exists: on #445 a new script went into check_cdpath_safe.sh's NOT_RUN but not into
# package.sh. `make check` passed in the checkout; inside the unzipped zip the CDPATH guard
# named a script the zip lacked, and only CI found it, after the push. These cases pin that the
# guard fails on that, on a script in only one of package.sh's two lists, on a -x pattern that
# drops a script (quoted or not) or is written in a way it cannot read, on either list naming a script that is gone, and on a
# package.sh it cannot read, and that it passes on the scripts as they are.
#
# It enters the way make check does: it runs the guard script, which finds its files from where
# it sits. The copies are in no git repo, so the listing falls back to find, as in the zip.
#
# Usage: bash scripts/test_check_package_scripts.sh
set -u
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(dirname -- "$HERE")"
T="$(mktemp -d "${TMPDIR:-/tmp}/package-scripts-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
fails=0; n=0
scripts="$(cd "$ROOT" && bash scripts/list_shell_scripts.sh)" \
  || { printf '%s\n' "$scripts"; exit 1; }
scripts="$(grep '^scripts/' <<<"$scripts")"

# fresh — sets c to a new copy of every shell script under scripts/. Not run in $(…), so a
# failed copy ends the test here instead of leaving c empty for the cases below.
fresh() {
  c="$T/repo.$n"; n=$((n+1))
  mkdir -p "$c/scripts" || { echo "FAIL — could not create $c."; exit 1; }
  while IFS= read -r f; do
    mkdir -p "$c/$(dirname -- "$f")" && cp "$ROOT/$f" "$c/$f" \
      || { echo "FAIL — could not copy $f to $c."; exit 1; }
  done <<<"$scripts"
}

# edit <copy> <sed script> — runs sed on the copy's package.sh; fails the test if nothing changed.
edit() {
  local p="$1/scripts/package.sh"
  sed "$2" "$p" >"$p.new" || { echo "FAIL — sed failed on $p." >&2; exit 1; }
  if cmp -s "$p" "$p.new"; then echo "FAIL — sed '$2' changed nothing in $p." >&2; exit 1; fi
  mv "$p.new" "$p"
}

# insert_after <file> <line> <new line> — adds <new line> after each line equal to <line>.
# awk, not sed: BSD sed takes no \n in a replacement. Fails the test if nothing was added.
insert_after() {
  awk -v at="$2" -v add="$3" '{ print } $0 == at { print add }' "$1" >"$1.new" \
    || { echo "FAIL — awk failed on $1." >&2; exit 1; }
  if cmp -s "$1" "$1.new"; then echo "FAIL — no line '$2' in $1." >&2; exit 1; fi
  mv "$1.new" "$1"
}

# add_script <copy> — a new script, listed in the CDPATH guard's NOT_RUN as #445's was.
add_script() {
  printf '#!/usr/bin/env bash\necho new\n' >"$1/scripts/test_new.sh"
  insert_after "$1/scripts/check_cdpath_safe.sh" 'NOT_RUN=(' '  scripts/test_new.sh  # new'
}
ZIP_LINE='s|^  scripts/check_package_scripts.sh |  scripts/check_package_scripts.sh scripts/test_new.sh |'
add_required() {
  insert_after "$1/scripts/package.sh" '  scripts/check_package_scripts.sh' '  scripts/test_new.sh'
}

# expect <name> <copy> <pass|fail> [<text the output must hold>]
expect() {
  local out rc
  out="$(bash "$2/scripts/check_package_scripts.sh" 2>&1)"; rc=$?
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

fresh
expect "the scripts as they are pass" "$c" pass "ship in the handoff zip"

fresh; add_script "$c"
expect "#445: a new script in the CDPATH guard's NOT_RUN but not in package.sh fails" "$c" fail "scripts/test_new.sh"

fresh; add_script "$c"; edit "$c" "$ZIP_LINE"
expect "a script in the zip -r line but not REQUIRED fails" "$c" fail "not in REQUIRED"

fresh; add_script "$c"; add_required "$c"
expect "a script in REQUIRED but not the zip -r line fails" "$c" fail "not in scripts/package.sh's zip -r line"

fresh; add_script "$c"; edit "$c" "$ZIP_LINE"; add_required "$c"
expect "a script in both lists passes" "$c" pass "ship in the handoff zip"

fresh; edit "$c" "s#-x '\*.DS_Store'#-x '*/test_served_build.sh' '*.DS_Store'#"
expect "a quoted -x pattern that drops a script fails" "$c" fail "scripts/test_served_build.sh (by -x"

fresh; edit "$c" "s#-x '\*.DS_Store'#-x scripts/test_served_build.sh '*.DS_Store'#"
expect "an unquoted -x pattern that drops a script fails" "$c" fail "scripts/test_served_build.sh (by -x"

fresh; edit "$c" "s#-x '\*.DS_Store'#-x scripts/test_\\\\*.sh '*.DS_Store'#"
expect "a -x pattern with a backslash fails" "$c" fail "cannot read"

fresh; edit "$c" "s#-x '\*.DS_Store'#-x 'scripts/[ t]est_served_build.sh' '*.DS_Store'#"
expect "a -x pattern with a space inside quotes fails" "$c" fail "cannot read"

fresh; edit "$c" "s#-x '\*.DS_Store'#-x \"scripts/\"\"test_served_build.sh\" '*.DS_Store'#"
expect "a -x pattern made of two quoted parts fails" "$c" fail "cannot read"

fresh; rm "$c/scripts/test_served_build.sh"; edit "$c" '/^  scripts\/test_served_build.sh$/d'
expect "a zip -r line naming a script that is gone fails" "$c" fail "zip -r line names these"

fresh; rm "$c/scripts/test_served_build.sh"; edit "$c" 's| scripts/test_served_build.sh | |'
expect "REQUIRED naming a script that is gone fails" "$c" fail "REQUIRED in scripts/package.sh names these"

fresh; edit "$c" 's|^  -x |  |'
expect "a zip -r line with no -x patterns the guard can read fails" "$c" fail "could not read"

fresh; edit "$c" 's#^zip -r#zip  -r#'
expect "a package.sh the guard cannot read fails" "$c" fail "could not read"

if [ "$fails" -ne 0 ]; then
  echo "test_check_package_scripts.sh: $fails case(s) failed"
  exit 1
fi
echo "test_check_package_scripts.sh: all cases passed"
