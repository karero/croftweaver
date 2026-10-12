#!/usr/bin/env bash
# Guard: the skill suite is a handoff artifact — no personal names, contact info, or
# credentials may enter it. Scans skills/ + root docs (and scripts/, for names only) and
# exits 1 (with file:line) on any hit. Wired into `make check` and CI (.github/workflows/clean.yml).
#
# Two kinds of check:
#   • DENYLIST — specific known-private identifiers, read from an OPTIONAL gitignored
#     file (scripts/.clean-denylist) so the public suite never enumerates private names.
#     Catches our own info regressing back in; skipped if the file is absent. CI writes
#     the file from the CLEAN_DENYLIST repo secret (`make push-denylist` sets it) and runs
#     with CLEAN_MASK_NAMES=1, which prints no scanned text at all, only counts, since a
#     public repo's CI logs are public (section 0 below).
#   • GENERIC  — any real email, plus credential/secret formats and secret-looking
#     assignments. Catches things no denylist could enumerate.
# A real false positive should be fixed by narrowing the pattern here, never by
# loosening it to "match nothing".
set -uo pipefail
export LC_ALL=C   # unlocalized grep output — filter_ignored parses "Binary file … matches"
CDPATH= cd -- "$(dirname -- "$0")/.."

# The private-name list (section 1 uses it; section 0 needs it first).
DENYLIST_FILE="scripts/.clean-denylist"
# A linked worktree has no copy of the gitignored list, so the check used to skip itself in
# exactly the checkouts where commits are made (2026-09-27: a client name reached main that
# way). Use the main checkout's list then, asking git where that is: the first entry of
# `git worktree list`. For a main checkout made with --separate-git-dir, git records no such
# path (it names the git folder), so the list is not found there and the skip below says so.
# No git (the handoff zip) or no list anywhere → skip, loudly. A list saved with Windows line
# endings would end every name in a carriage return that never matches; drop them.
if [ ! -f "$DENYLIST_FILE" ]; then
  main="$(git worktree list --porcelain 2>/dev/null | sed -n '1s/^worktree //p')"
  [ -n "$main" ] && [ -f "$main/$DENYLIST_FILE" ] && DENYLIST_FILE="$main/$DENYLIST_FILE"
fi
# A name's edges. In the C locale, \b can miss a name that starts or ends with a non-ASCII
# letter (an é, an Ö), with a space beside it for one (GNU grep, CI's, and this Mac's grep
# alike). So each name pattern below tries both: edges of anything but an ASCII letter, digit
# or _ (a byte of a non-ASCII letter counts, so a listed "Caf" also matches inside "Café"), OR
# the old \b match, which alone finds an entry that starts or ends with punctuation next to a
# letter (a trailing hyphen, say). Two separate alternatives: on BSD grep, (^|\b)-name and
# name-($|\b) miss an entry whose punctuation edge touches a letter. More reports than either
# alone, never fewer: a name with a non-ASCII letter at an edge is also found inside a longer
# word.
E='[^A-Za-z0-9_]'
NAMES=""
[ -f "$DENYLIST_FILE" ] && NAMES="$(tr -d '\r' <"$DENYLIST_FILE" | grep -vE '^[[:space:]]*(#|$)' | paste -sd'|' -)"

# 0. CI's logs are public. With CLEAN_MASK_NAMES=1 this script runs itself again and prints
#    that run's own lines only: each block of scan lines (the 4-space-indented lines, which
#    hold every hit and grep's own errors) becomes a count. A hit's text, its file name, an
#    email around it or a grep error naming a file can each hold a name, and blanking names
#    inside them missed one case after another in review (#189); so nothing scanned is
#    printed, with a name list or without. Run the check locally to see the lines. The exit
#    code is the inner run's. The script's own lines never hold a whole listed name; if one
#    ever does, nothing is printed and the run fails. That check keeps every pipeline
#    stage's status: under pipefail, a failed stage before a grep that found nothing reads
#    like "none".
if [ -n "${CLEAN_MASK_NAMES:-}" ]; then
  out="$(CLEAN_MASK_NAMES= CLEAN_INNER=1 bash scripts/check_clean.sh 2>&1)"; rc=$?
  whole="$(printf '0\n0 1')"
  [ -n "$NAMES" ] && whole="$(printf '%s\n' "$out" | grep -ciE -- "^ {0,3}(([^ ].*$E|[^ A-Za-z0-9_])?(${NAMES})($E|\$)|([^ ].*)?\\b(${NAMES})\\b)" 2>/dev/null; echo "${PIPESTATUS[*]}")"
  # grep's own status, the last field: when grep dies on a bad pattern without reading, a
  # long output can kill printf with SIGPIPE first ("141 2").
  if [ "${whole##* }" = 2 ]; then
    echo "FAIL — this run's output is withheld: the name list does not compile as a pattern."
    echo "Run the check where the logs are private to see grep's error: bash scripts/check_clean.sh"
    exit 1
  elif [ "$whole" != "$(printf '0\n0 1')" ]; then
    echo "FAIL — this run's output is withheld: one of its own lines holds a listed name."
    echo "Run the check where the logs are private to see the lines: bash scripts/check_clean.sh"
    echo "If none of them holds a listed name, a list entry matches a word of this script's"
    echo "own text (such as skills or docs): narrow that entry."
    exit 1
  fi
  printf '%s\n' "$out" | awk '
    /^    / { n++; next }
    n { printf "    (%d line(s) withheld: CI logs are public; run bash scripts/check_clean.sh locally to see them)\n", n; n = 0 }
    { print }
    END { if (n) printf "    (%d line(s) withheld: CI logs are public; run bash scripts/check_clean.sh locally to see them)\n", n }'
  exit "$rc"
fi
SCAN="skills"   # the arch doc now lives in skills/new-website/references/, so skills/ covers it
# Generic checks (email / home-path / secret) also cover the root docs that ship in the
# handoff, including LICENSE. NOT the scripts (they DEFINE the secret regexes — would
# self-match). The name denylist covers the same docs EXCEPT LICENSE, which legitimately
# carries the owner's real name + clone URLs (2026-07-17: widened from skills/-only after
# docs/reviews/*.md review artifacts slipped a client name past a skills/-only scan).
# It DOES cover scripts/: the names live in the gitignored list, not in any script, so
# nothing there can match itself; the list's own lines are dropped below. (2026-10-06: a
# client site's name sat in a comment in a script that ships in the handoff zip.)
SCAN_BASE="$SCAN README.md THIRD-PARTY-LICENSES.md SECURITY.md Makefile docs"
SCAN_NAMES_ALL="$SCAN_BASE scripts"
SCAN_DOCS_ALL="$SCAN_BASE LICENSE"
# Every target must be here. A missing path makes grep print a diagnostic and exit 2,
# which this script used to send to /dev/null and read as "no hits" — so the final OK line
# named files nobody had looked at, an OK that could not fail (found in the handoff zip,
# which shipped no SECURITY.md while this check claimed to scan it). The zip now ships
# every target, so a missing one means something is broken, not a legitimate subset.
# The lists stay space-separated and unquoted on purpose — every entry is a fixed,
# space-free path in this repo.
SCAN_NAMES="$SCAN_NAMES_ALL"
SCAN_DOCS="$SCAN_DOCS_ALL"
# `set -f` so a target is never pathname-expanded — the loop wants the literal list.
missing() { local t out=""; set -f; for t in $1; do [ -e "$t" ] || out="${out:+$out }$t"; done; set +f; printf '%s' "$out"; }
MISSING="$(missing "$SCAN_DOCS_ALL $SCAN_NAMES_ALL")"
if [ -n "$MISSING" ]; then
  echo "FAIL — these scan targets are missing, so nothing checked them: $MISSING"
  echo "All of them ship in the handoff zip and exist in a checkout. If a copy should"
  echo "legitimately lack one, drop it from SCAN_NAMES_ALL/SCAN_DOCS_ALL deliberately."
  exit 1
fi
fail=0
names_checked=0 names_skipped=""
# grep prints a hit as file:line:text, and the filters below read the first ":<digits>:" as
# where the file name ends. A file name holding a newline splits that line into pieces that
# can pass for other files (an ignored one, or the list itself). One holding a colon, a digit
# and later another colon can hold ":<digits>:", which moves the text's start into the name,
# where an exemption ("example.com") then drops a real hit. Refuse both kinds of name (the
# second rule is broader than ":<digits>:" itself, so some harmless names are refused too).
# They print 4-space-indented, so masked mode withholds them like any scan line. Gitignored
# files are refused too: they are on disk, where grep reads them. If find fails, the names
# were not checked: fail too.
odd_paths="$(find $SCAN_BASE scripts LICENSE \( -name "*"$'\n'"*" -o -name '*:[0-9]*:*' \) -print 2>/dev/null)" \
  || { fail=1; echo "✗ scan error (find failed) — file names were not checked"; }
if [ -n "$odd_paths" ]; then
  fail=1
  echo "✗ file names holding a newline, or a colon, a digit and later another colon (rename them; grep's file:line: output cannot name them reliably):"
  printf '%s\n' "$odd_paths" | sed 's/^/    /'
fi
# Hits in gitignored files (__pycache__, local caches…) never ship in the handoff —
# drop them. Outside a git checkout (e.g. a tarball) check-ignore fails → keep the hit.
filter_ignored() { # stdin: grep output → stdout minus gitignored files
  local line f rest keep
  while IFS= read -r line; do
    case "$line" in
      "Binary file "*" matches") f="${line#Binary file }"; f="${f% matches}"
        git check-ignore -q -- "$f" 2>/dev/null || printf '%s\n' "$line"; continue ;;
    esac
    # A file name may hold a colon, so the name is not simply the text before the first
    # one: try each prefix that ends at a colon, and drop the line only when every prefix
    # naming an existing file is gitignored. In doubt, the hit is reported.
    keep=1 f="" rest="$line"
    while [ "${rest#*:}" != "$rest" ]; do
      f="${f:+$f:}${rest%%:*}"; rest="${rest#*:}"
      [ -e "$f" ] || continue
      if git check-ignore -q -- "$f" 2>/dev/null; then keep=0; else keep=1; break; fi
    done
    if [ "$keep" = 1 ]; then printf '%s\n' "$line"; fi
  done
}
# grep wrapper: existence filtering says the paths are there, not that they were read.
# grep exits 1 for "no hits" but >1 for a real failure (unreadable file, bad regex), and
# discarding that difference is how an unscanned tree still prints OK.
g() { # <grep args…> → matches on stdout; a scan ERROR fails the run instead of reading as clean
  local out rc err bin split
  # Without a file for grep's errors, the redirect fails, grep never runs, and the status
  # reads like "no hits": every scan would pass unread.
  err="$(mktemp)" || { echo "✗ scan error (mktemp failed) — this check did NOT run"; return 0; }
  out="$(command grep "$@" 2>"$err")"; rc=$?
  # GNU grep 3.5+ (CI's) reports a matching binary file on stderr with exit 0, where BSD grep
  # prints "Binary file X matches" on stdout. Turn the GNU form into the BSD one, or the hit
  # would be thrown away with the rest of stderr and a binary file holding a name would pass.
  # Any other stderr line from a grep that did not fail is a scan error: a newline in a file
  # name splits that message. Its header line survives every filter and fails the run; the
  # lines under it may be filtered. (Such file names are refused outright too.)
  bin="$(sed -n 's/^grep: \(.*\): binary file matches$/Binary file \1 matches/p' "$err")"
  [ -n "$bin" ] && out="${out:+$out$'\n'}$bin"
  split="$(sed '/^grep: .*: binary file matches$/d' "$err")"
  if [ "$rc" -le 1 ] && [ -n "$split" ]; then
    echo "✗ scan error (grep wrote to stderr; a file name may hold a newline) — its hits were not filtered:"
    printf '%s\n' "$split" | sed 's/^/    /'
  fi
  if [ "$rc" -gt 1 ]; then
    fail=1
    echo "✗ scan error (grep exit $rc) — this check did NOT run:"
    sed 's/^/    /' "$err"
  fi
  rm -f "$err"
  printf '%s' "$out"
}
# grep as a filter on stdin: like grep, but an error (exit > 1) becomes a scan-error line at
# the top of its output, which every later filter keeps, instead of hits silently lost.
gf() {
  local out rc
  out="$(command grep "$@")"; rc=$?
  if [ "$rc" -gt 1 ]; then echo "✗ scan error (filter grep exit $rc) — hits may be missing"; fi
  if [ -n "$out" ]; then printf '%s\n' "$out"; fi
  return 0
}
report() { # <label> <grep-output>
  [ -z "$2" ] && return 0
  local hits
  hits="$(printf '%s\n' "$2" | filter_ignored)"
  [ -z "$hits" ] && return 0
  fail=1
  echo "✗ $1:"
  printf '%s\n' "$hits" | sed 's/^/    /'
}

# 1. Personal / site / org identifiers (denylist, word-boundaried). Patterns live in a
#    gitignored local file — one extended-regex pattern per line, '#' comments allowed —
#    so private names never ship in the repo. Absent (e.g. a fresh clone) → skipped;
#    the generic checks below still run.
if [ -f "$DENYLIST_FILE" ]; then
  # make push-denylist keeps a checksum of the names it sent (comments and blank lines left
  # out) beside the list. Names that have changed since are not the ones CI checks (CI reads
  # the secret), so fail until they are pushed again, an emptied list included. CI has no
  # such file. A push from another checkout, of another copy of the list, cannot be seen
  # from here: gh never reads a secret back.
  if [ -f "$DENYLIST_FILE.pushed" ]; then
    if [ "$(tr -d '\r' <"$DENYLIST_FILE" | grep -vE '^[[:space:]]*(#|$)' | cksum)" != "$(cat "$DENYLIST_FILE.pushed")" ]; then
      fail=1
      if [ -n "$NAMES" ]; then
        echo "✗ the name list changed since the last make push-denylist: CI still checks the old one; run make push-denylist"
      else   # push-denylist refuses an empty list, and CI fails on a secret with no names
        echo "✗ the name list has no names left, but CI still checks the ones last pushed; an empty list cannot be pushed: add a name back, then run make push-denylist"
      fi
    fi
  elif [ -z "${CI:-}" ] && [ -z "${CLEAN_INNER:-}" ]; then
    echo "· the name list has not been pushed from this checkout (no .pushed file beside it): if CI checks names, it may hold an older list; maintainers: make push-denylist"
  fi
  # karero/croftweaver is this project's OWN public repo, and karero/website-builder is what
  # it was called before the rename — self-links to either (README badges, clone
  # instructions, the security policy) and the short form in issue and PR references
  # (karero/croftweaver#131) are the point, not a leak. The old name stays allowed for good:
  # docs/reviews/ keeps its historical links, and docs/ is scanned. The allowance goes by
  # name, not by what the link leads to: a different repo later created under the old name
  # would pass too. That is accepted, to keep the history readable. Blank out exactly that
  # reference, in lowercase, and not inside a longer name (one with an extra prefix like
  # `other-` or suffix like `-x`), then look again: dropping every line that held one also hid
  # any private name beside it. One reference at a time, until none is left: a global
  # replace consumes the character after one reference that the next needs before it
  # (karero/croftweaver,karero/croftweaver). Binary-file lines pass through for
  # filter_ignored. A scan error (g's "✗ scan error" block, first in its output) goes to
  # report whole: the filter would compile the same broken pattern, fail too, and turn the
  # error into a clean pass. The list itself sits in the scanned scripts/ and holds every
  # name, so its own lines are dropped, by exact path: a file of that name anywhere else
  # (docs/ ships whole in the zip) is scanned like any other. A line from a file named
  # like the list plus a colon (scripts/.clean-denylist:1:x) starts the same way, so with
  # such a file present nothing is dropped: the list then reports itself, loudly.
  if [ -n "$NAMES" ]; then
    # An entry anchored with ^ finds its lines but is never reported: the post-filter below
    # looks for it after "file:line:", where ^ cannot match. Refuse such entries (a count
    # only: the entries are private). A ^ right after [ negates a class, and is fine.
    anchored="$(tr -d '\r' <"$DENYLIST_FILE" | grep -vE '^[[:space:]]*(#|$)' | grep -cE '(^|[^[])\^')"
    if [ "${anchored:-0}" != 0 ]; then
      fail=1
      echo "✗ $anchored list entr(ies) holding ^ (other than right after [): the check finds a name anywhere in a line, and an anchor makes it miss; drop it (a literal \\^ is refused too)"
    fi
    self='^scripts/\.clean-denylist:[0-9]+:'
    compgen -G 'scripts/.clean-denylist:*' >/dev/null && self='^$'
    hits="$(g -rinE "(^|$E)(${NAMES})($E|\$)|\\b(${NAMES})\\b" $SCAN_NAMES)"
    case "$hits" in
      "✗ scan error"*) ;;
      # gf() never fails, so under pipefail a failure here is sed's, and its hits are lost.
      *) hits="$(printf '%s\n' "$hits" \
           | gf -vE "$self" \
           | sed -E -e ':a' \
               -e 's#(^|[^A-Za-z0-9_.-])karero/croftweaver(\.git)?([^A-Za-z0-9_.-]|\.[^A-Za-z0-9_.-]|\.?$)#\1SELF-REPO\3#' -e 'ta' \
               -e 's#(^|[^A-Za-z0-9_.-])karero/website-builder(\.git)?([^A-Za-z0-9_.-]|\.[^A-Za-z0-9_.-]|\.?$)#\1SELF-REPO\3#' -e 'ta' \
           | gf -iE "^✗ scan error|^Binary file |:[0-9]+:((.*$E)?(${NAMES})($E|\$)|.*\\b(${NAMES})\\b)")" \
           || hits="✗ scan error (the name filter failed) — hits may be missing" ;;
    esac
    report "personal/site identifier" "$hits"
    names_checked=1
  else
    names_skipped="$DENYLIST_FILE lists no names"
    echo "· personal-name denylist skipped ($names_skipped) — generic checks still run"
  fi
else
  names_skipped="no $DENYLIST_FILE"
  echo "· personal-name denylist skipped ($names_skipped) — generic checks still run"
fi

# 2. Personal home paths (non-portable + identifying).
report "home path" "$(g -rnE '/(Users|home)/[A-Za-z0-9._-]+' $SCAN_DOCS)"

# 3. Real email addresses (anything that is not an obvious placeholder/markup token).
EMAIL='[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
# The exemptions here and in check 5 match a hit's text after "file:line:", never its file
# name: a binary file's hit is its name alone, and docs/example.com.bin holds no placeholder.
report "email address" "$(g -rinE "$EMAIL" $SCAN_DOCS \
  | gf -viE ':[0-9]+:.*(@(example|test|domain|yoursite|site|company)\b|example\.(com|org)|@(type|id|context|media|import|2x|3x|font-face|keyframes)|(you|user|name|email|first\.last|hello|info|team)@|git@(github|gitlab)\.com)')"

# 4. Credential / secret formats + private keys + JWTs.
# sk-/pplx- cover OpenAI (incl. sk-proj-), Anthropic (sk-ant-) and Perplexity keys for the
# AI check; they must start a word, or hyphenated prose ("risk-free-and-...") would match.
SECRETS='(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|(^|[^A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}|(^|[^A-Za-z0-9_-])pplx-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})'
# Self-test, both directions: a pattern that stops matching real key shapes passes silently, and
# one that starts matching prose fails every docs change. The samples are built at run time so
# this file never holds a key-shaped literal of its own.
x20=aaaaaaaaaaaaaaaaaaaa; x36="${x20}aaaaaaaaaaaaaaaa"
for k in "AKIA""ABCDEFGHIJKLMNOP" "ghp_$x36" "github_pat_$x20" "glpat-$x20" "xoxb-$x20" \
         "sk-""proj-$x20" "sk-""ant-api03-$x20" "key: sk-$x20" "pplx-$x20" "AIza$x36" \
         "-----BEGIN RSA PRIVATE KEY-----"; do
  grep -qE -- "$SECRETS" <<<"$k" || { echo "FAIL — the secret pattern no longer matches a key shaped like: ${k:0:12}…"; exit 1; }
done
for k in "a risk-free-and-clear-guarantee-for-everyone" "ask-me-anything-about-your-website-today" \
         "task-sk-$x20" "the pplx-style answer"; do
  if grep -qE -- "$SECRETS" <<<"$k"; then echo "FAIL — the secret pattern matches plain prose: $k"; exit 1; fi
done
report "credential/secret" "$(g -rnE "$SECRETS" $SCAN_DOCS)"

# 5. Secret-looking assignments:  (api_key|secret|token|password|...) = "longish-literal"
ASSIGN='(api[_-]?key|secret|client[_-]?secret|access[_-]?token|auth[_-]?token|password|passwd|bearer)["'"'"' ]*[:=]["'"'"' ]*["'"'"'][^"'"'"' ]{8,}'
report "secret-looking assignment" "$(g -rinE "$ASSIGN" $SCAN_DOCS \
  | gf -viE ':[0-9]+:.*(placeholder|example|your[_-]|<[a-z]|x{4,}|\.\.\.|process\.env|import\.meta\.env|REPLACE|TODO|\[bracket\])')"

if [ "$fail" -ne 0 ]; then
  echo ""
  echo "FAIL — personal info or credentials found in the skill suite. Skills are handoff"
  echo "artifacts: keep them generic. Remove the content, or (if a genuine false positive)"
  echo "tighten the pattern in scripts/check_clean.sh."
  exit 1
fi
# The OK line says itself whether names were checked: CI once had no list, and a bare OK there
# read as "no private names" while the same tree failed `make check` locally.
if [ "$names_checked" -eq 1 ]; then
  echo "OK — no private names in: $SCAN_NAMES; no contact info or credentials in: $SCAN_DOCS"
else
  echo "OK — no contact info or credentials in: $SCAN_DOCS (private-name check SKIPPED: $names_skipped)"
fi
