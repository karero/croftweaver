#!/usr/bin/env bash
#
# test_orphan_exempt.sh — the starter's scripts/orphan-exempt.mjs, which reads orphan-exempt.txt
# (the pages a site leaves unlinked on purpose) for tests/orphans.spec.ts and check_internal_links.sh.
#
# The list used to sit in TypeScript, read by grep and awk. A text file has one way to be written
# and one reader. These cases pin that reader: what it accepts, and that every line it cannot read
# stops the run, naming the file and the line, rather than being guessed at. Bytes a keyboard
# cannot type are written with printf octal escapes; cases that give a hex string check them with od.
#
# Usage: bash scripts/test_orphan_exempt.sh
set -u
command -v node >/dev/null 2>&1 || { echo "SKIP: test_orphan_exempt.sh needs node (orphan-exempt.mjs is a Node script)"; exit 0; }
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(dirname -- "$HERE")"
ASTRO="$ROOT/skills/new-website/templates/astro"
MOD="$ASTRO/scripts/orphan-exempt.mjs"
T="$(mktemp -d "${TMPDIR:-/tmp}/orphan-exempt-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
fails=0; n=0
ok()   { printf 'ok   %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; fails=$((fails+1)); }

# put <printf format> [<hex the file must hold>]: a fresh site folder $D whose orphan-exempt.txt is the
# printf output; the hex (od, no spaces) proves the bytes are the ones meant, not what an editor made of them.
put() {
  n=$((n+1)); D="$T/c$n"; mkdir "$D" || { echo "FAIL — could not make $D"; exit 1; }
  # shellcheck disable=SC2059
  printf "$1" >"$D/orphan-exempt.txt"
  if [ -n "${2:-}" ] && ! od -An -v -tx1 "$D/orphan-exempt.txt" | tr -d ' \n' | grep -qF -- "$2"; then
    fail "fixture $n does not hold the bytes $2"
  fi
}
# go: run the program on $D; rc, out (stdout), err (stderr).
go() { out="$(node "$MOD" "$D" 2>"$T/err")"; rc=$?; err="$(cat "$T/err")"; }
# good <name> <printf format> <expected addresses, one per line, "" for none> [hex]
good() {
  put "$2" "${4:-}"; go
  if [ "$rc" -eq 0 ] && [ "$out" = "$3" ] && [ -z "$err" ]; then ok "$1"; else fail "$1: exit $rc, list [$out], stderr [$err]"; fi
}
# bad <name> <printf format> <line number> <text the message holds> [hex]
bad() {
  put "$2" "${5:-}"; go
  if [ "$rc" -eq 1 ] && [ -z "$out" ] && printf '%s' "$err" | grep -qF -- "orphan-exempt.txt line $3: " \
     && printf '%s' "$err" | grep -qF -- "$4"; then ok "$1"; else fail "$1: exit $rc, list [$out], stderr [$err]"; fi
}

# --- a list that comes out whole -------------------------------------------------------------------
good "plain list, comments, a blank line and a trailing comment" \
  '# why\n/lp/a  # ad only\n\n/lp/b\n  # indented comment\n' "$(printf '/lp/a\n/lp/b')"
# Characters that broke the old reader: ]) // quotes and a star inside an address.
good "an address holding ]) // ' \" and *" \
  "/a])b\n/c//d\n/e'f\n/g\"h\n/i*j\n" "$(printf '%s\n' '/a])b' '/c//d' "/e'f" '/g"h' '/i*j')"
good "a # after white space starts a comment: /a #b is /a" '/a #b\n' '/a'
good "CRLF at every line end" '# c\r\n/a\r\n/b  # why\r\n' "$(printf '/a\n/b')"
good "a trailing space and a trailing tab with no comment" '/a \n/b\t\n' "$(printf '/a\n/b')"
good "a tab before a comment" '/a\t# why\n' '/a' "2f61092320776879"
good "one BOM at the very start" '\357\273\277/a\n' '/a' "efbbbf2f610a"
good "no final newline" '/a\n/b' "$(printf '/a\n/b')"
good "an empty file" '' ''

# --- lines that stop the run, with the line number --------------------------------------------------
bad "a leading tab"                    '# c\n/ok\n\t/a\n' 3 'white space'
bad "a tab inside an address"          '/ok\n/a\t/b\n' 2 'white space'
bad "two words"                        '/ok\n/a /b\n' 2 'white space'
bad "a leading space"                  '/ok\n /a\n' 2 'white space'
bad "no leading slash"                 '# c\n/ok\na\n' 3 'must start with /'
bad "a trailing slash"                 '/ok\n/a/\n' 2 'must not end with /'
bad "the home page"                    '/ok\n/\n' 2 'home page'
bad "a # inside an address"            '/ok\n/a#b\n' 2 'must not hold ? or #'
bad "a ? inside an address"            '/ok\n/a?b\n' 2 'must not hold ? or #'
bad "a no-break space is named"        '/ok\n/a\302\240b\n' 2 'U+00A0' "2f61c2a062"
bad "a no-break space after an address" '/ok\n/a\302\240\n' 2 'U+00A0' "2f61c2a00a"
bad "a line separator is named"        '/ok\n/a\342\200\250b\n' 2 'U+2028' "2f61e280a862"
bad "an ideographic space is named"    '/ok\n/a\343\200\200b\n' 2 'U+3000' "e38080"
bad "a control character is named"     '/ok\n/a\001b\n' 2 'U+0001'
bad "a zero-width space is named"      '/ok\n/a\342\200\213b\n' 2 'U+200B' "2f61e2808b62"
bad "a soft hyphen is named"           '/ok\n/\302\255a\n' 2 'U+00AD' "2fc2ad61"
bad "a word joiner is named"           '/ok\n/a\342\201\240b\n' 2 'U+2060' "2f61e281a062"
bad "a byte that is not UTF-8 is named" '/ok\n/a\377b\n' 2 'U+FFFD' "2f61ff62"
bad "a second BOM at the start"        '\357\273\277\357\273\277/a\n' 1 'U+FEFF' "efbbbfefbbbf"
bad "a BOM on a later line"            '/ok\n\357\273\277/a\n' 2 'U+FEFF'
# A CR belongs to the line end only right before the LF.
bad "a CR in the middle of an address" '/ok\n/a\rb\n' 2 'U+000D'
bad "a CR inside a comment"            '/ok\n/a  # x\ry\n' 2 'U+000D'
bad "a CR at the end of the last line, no LF" '/ok\n/a\r' 2 'U+000D'
bad "CRLF on some lines does not hide a lone CR" '/ok\r\n/a\r/b\r\n' 2 'U+000D'
bad "a lone CR does not hide the next entry in a comment" '# c\r/hidden\n/ok\n' 1 'U+000D'

# --- reading the file ----------------------------------------------------------------------------
n=$((n+1)); D="$T/c$n"; mkdir "$D"; go
if [ "$rc" -eq 0 ] && [ -z "$out" ] && [ -z "$err" ]; then ok "no orphan-exempt.txt: an empty list, exit 0"; else fail "missing file: exit $rc [$out] [$err]"; fi
n=$((n+1)); D="$T/c$n"; mkdir -p "$D/orphan-exempt.txt"; go
if [ "$rc" -eq 1 ] && printf '%s' "$err" | grep -qF 'orphan-exempt.txt: cannot be read'; then ok "a folder named orphan-exempt.txt: exit 1, says so"; else fail "folder: exit $rc [$out] [$err]"; fi
# The exports, as the spec uses them: the same answers as the program.
n=$((n+1)); D="$T/c$n"; mkdir "$D"; printf '/a  # x\n' >"$D/orphan-exempt.txt"
fn="$(node --input-type=module -e "
import { readOrphanExempt, parseOrphanExempt } from 'file://$MOD';
console.log(JSON.stringify([readOrphanExempt('$D'), readOrphanExempt('$T/nowhere'), parseOrphanExempt('/b\n')]));" 2>&1)"
if [ "$fn" = '[["/a"],[],["/b"]]' ]; then ok "readOrphanExempt and parseOrphanExempt give the lists the program prints"; else fail "exports: $fn"; fi
# The program needs its path.
out="$(node "$MOD" 2>"$T/err")"; rc=$?; err="$(cat "$T/err")"
if [ "$rc" -eq 1 ] && [ -z "$out" ] && printf '%s' "$err" | grep -qF 'usage:'; then ok "no path argument: exit 1 with usage"; else fail "no path: exit $rc [$out] [$err]"; fi

# --- the property check_internal_links.sh relies on ----------------------------------------------
# The old-form detection looks for the old name in the spec; the shipped spec must not hold it.
if ! grep -q 'ORPHAN_EXEMPT' "$ASTRO/tests/orphans.spec.ts"; then ok "the shipped starter spec holds no ORPHAN_EXEMPT"; else fail "the shipped starter spec still holds ORPHAN_EXEMPT"; fi
# The shipped file lists nothing (a comment-only file), so a new site starts with no exemption.
n=$((n+1)); D="$T/c$n"; mkdir "$D"; cp "$ASTRO/orphan-exempt.txt" "$D/"; go
if [ "$rc" -eq 0 ] && [ -z "$out" ] && [ -z "$err" ]; then ok "the shipped orphan-exempt.txt reads as an empty list"; else fail "shipped file: exit $rc [$out] [$err]"; fi

if [ "$fails" -ne 0 ]; then echo "$fails check(s) FAILED"; exit 1; fi
echo "all checks passed"
