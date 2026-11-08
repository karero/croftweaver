#!/usr/bin/env bash
#
# test_whats_new.sh — runs scripts/whats-new.sh <site> against a throwaway suite repo and a
# throwaway site, and checks which frozen template files it reports as MISSING.
#
# Why it exists: the report listed every frozen file that changed upstream the same way,
# whether the site had a copy or not. A site made before scripts/verify.mjs existed read
# "verify.mjs changed upstream" as one more file to merge some day, and so ran with no local
# `astro check` gate until a broken page reached main. A file the site lacks is now marked
# MISSING and listed again at the end. These cases pin what counts: a file the site has is
# not missing, and neither is one deleted upstream. The last case checks every file in the
# real TEMPLATE_TRACKED list: the path the report shows as its site copy must be the path the
# MISSING check looks for, so the two mappings cannot drift apart or lose a file.
# A changed spec can also import a file the site never had (functions/_middleware on a site
# without functions/): taking the spec alone then fails when it loads. The import cases pin
# that each such file is named, that a file the site has in any lookup form is not, and that
# the real template specs raise no false alarm against the starter they ship with.
#
# Usage: bash scripts/test_whats_new.sh
set -u
if ! command -v git >/dev/null 2>&1; then
  echo "SKIP: test_whats_new.sh needs git (whats-new.sh compares a clone's history)"
  exit 0
fi
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
T="$(mktemp -d "${TMPDIR:-/tmp}/whats-new-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
phys="$(CDPATH= cd -- "$T" && pwd -P)" || exit 1
T="$phys"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git="git -c user.name=t -c user.email=t@t -c init.defaultBranch=main -c commit.gpgsign=false -c core.hooksPath=/dev/null"
fails=0
has()    { if grep -qxF -- "$2" "$T/out"; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s (no line: %s)\n' "$1" "$2"; fails=$((fails+1)); fi; }
hasnt()  { if grep -qF -- "$2" "$T/out"; then printf 'FAIL %s (found: %s)\n' "$1" "$2"; fails=$((fails+1)); else printf 'ok   %s\n' "$1"; fi; }
# report <suite> <site> <label>: run the report; stale template files are a report, not an
# error, so it must still exit 0 (an aborted run could print the right lines and fail).
report() {
  local rc
  bash "$1/scripts/whats-new.sh" "$2" > "$T/out" 2>&1; rc=$?
  if [ "$rc" -eq 0 ]; then printf 'ok   %s: exits 0\n' "$3"; else printf 'FAIL %s: exits %s\n' "$3" "$rc"; fails=$((fails+1)); fi
}
stamp() { printf 'suite_commit: %s\ncopied: 2026-01-01\n' "$2" > "$1"; }

# The suite: whats-new.sh plus template files, at a baseline commit and one later commit.
S="$T/suite" A="skills/new-website/templates/astro" C="skills/new-website/templates/claude"
# put <file> <version>: each file gets its own content, or git would pair a deletion with an
# addition as a rename and the deleted-upstream case would never be exercised.
put() { mkdir -p "$(dirname "$1")" && printf '%s %s\n' "$2" "$(printf '%s' "$1" | cksum)" > "$1"; }
mkdir -p "$S/scripts"
cp "$HERE/whats-new.sh" "$S/scripts/"
put "$S/$A/scripts/hooks/pre-push" v1
put "$S/$A/scripts/set_pdf_title.py" v1
put "$S/$A/tests/a.spec.ts" v1
$git -C "$S" init -q && $git -C "$S" add -A && $git -C "$S" commit -qm base
BASE="$($git -C "$S" rev-parse HEAD)"
put "$S/$A/scripts/hooks/pre-push" v2               # changed, the site has it
put "$S/$A/scripts/verify.mjs" v1                   # added, the site lacks it
$git -C "$S" rm -q "$A/scripts/set_pdf_title.py"    # deleted upstream, the site lacks it
put "$S/$A/tests/a.spec.ts" v2                      # changed, the site has it
put "$S/$A/tests/b.spec.ts" v1                      # added, the site lacks it
echo "import { y } from '../src/lib/y';" >> "$S/$A/tests/b.spec.ts"  # a site file it imports
put "$S/$C/hooks/git-stand.mjs" v1                  # added, the site lacks it
put "$S/$A/CROFTWEAVER-LICENSE.md" v1               # added, the site lacks it (0.35)
$git -C "$S" add -A && $git -C "$S" commit -qm later

# The site, stamped at the baseline and holding only the files it had then.
P="$T/site"
mkdir -p "$P/.claude/skills" "$P/tests" "$P/scripts/hooks"
stamp "$P/.claude/skills/SUITE-VERSION" "$BASE"
stamp "$P/tests/TESTS-VERSION" "$BASE"
echo v1 > "$P/scripts/hooks/pre-push"
echo v1 > "$P/tests/a.spec.ts"

report "$S" "$P" "a site missing files"
has   "a file added upstream that the site lacks is MISSING" "    MISSING: the site has no scripts/verify.mjs"
has   "a template test the site lacks maps to tests/"         "    MISSING: the site has no tests/b.spec.ts"
has   "a claude template the site lacks maps to .claude/"     "    MISSING: the site has no .claude/hooks/git-stand.mjs"
has   "the licence notice the site lacks is MISSING at its top" "    MISSING: the site has no CROFTWEAVER-LICENSE.md"
has   "the closing summary lists the missing files"           "  scripts/verify.mjs"
hasnt "a changed file the site has is not MISSING"            "no scripts/hooks/pre-push"
hasnt "a changed test the site has is not MISSING"            "no tests/a.spec.ts"
has   "a file deleted upstream is still listed as drift"      "  templates/astro/scripts/set_pdf_title.py (site copy: scripts/set_pdf_title.py)"
hasnt "a file deleted upstream is not MISSING"                "no scripts/set_pdf_title.py"
# The changed spec's import the site lacks is named (the full import cases are further down).
has   "a changed spec names an import the site lacks"         "    IMPORT NOT FOUND: src/lib/y (this spec imports it)"

# A site older than TESTS-VERSION falls back to its SUITE-VERSION baseline: the sites this
# check exists for, so the same file must be MISSING there too.
rm "$P/tests/TESTS-VERSION"
report "$S" "$P" "a site with no TESTS-VERSION"
has   "the SUITE-VERSION fallback marks MISSING too"          "    MISSING: the site has no scripts/verify.mjs"
stamp "$P/tests/TESTS-VERSION" "$BASE"

# Once the site has every file, nothing is MISSING, though the drift report still runs.
echo v1 > "$P/scripts/verify.mjs"; echo v1 > "$P/tests/b.spec.ts"
mkdir -p "$P/.claude/hooks" && echo v1 > "$P/.claude/hooks/git-stand.mjs"
echo v1 > "$P/CROFTWEAVER-LICENSE.md"
report "$S" "$P" "a site with every file"
has   "drift is still reported when nothing is missing"       "  templates/astro/scripts/verify.mjs (site copy: scripts/verify.mjs — the pre-push hook runs it once it is there; \`npm run verify\` also needs \"verify\": \"node scripts/verify.mjs\" in the site's package.json)"
hasnt "a site with every file shows no MISSING line"          "MISSING: the site has no"
hasnt "a site with every file shows no MISSING summary"       "MISSING from the site"

# Every TEMPLATE_TRACKED file, added upstream to a site that has none of them. Each drift
# line's "(site copy: X" must be followed by "MISSING: the site has no X". The tests entry
# is a directory; its file sits in a subfolder, which must keep its path on the site.
# NO_FIXED_PATH names the site copies that may live under another name (an owner may save a
# translated PUBLISHING.md as PUBLISHING.de.md): their drift line must have no MISSING line.
NO_FIXED_PATH=" PUBLISHING.md "
TRACKED="$(sed -n "s/^TEMPLATE_TRACKED='\(.*\)'\$/\1/p" "$HERE/whats-new.sh")"
S2="$T/suite2" P2="$T/site2" n=0
mkdir -p "$S2/scripts" "$P2/.claude/skills" "$P2/tests"
cp "$HERE/whats-new.sh" "$S2/scripts/"
$git -C "$S2" init -q && $git -C "$S2" add -A && $git -C "$S2" commit -qm base
BASE2="$($git -C "$S2" rev-parse HEAD)"
for f in $TRACKED; do
  [ "$f" = "$A/tests" ] && f="$f/sub/x.spec.ts"
  put "$S2/$f" v1; n=$((n+1))
done
$git -C "$S2" add -A && $git -C "$S2" commit -qm later
stamp "$P2/.claude/skills/SUITE-VERSION" "$BASE2"
stamp "$P2/tests/TESTS-VERSION" "$BASE2"
report "$S2" "$P2" "a site with no tracked file"
# One "shown|checked" row per drift line: the site copy the line names, and the path of the
# MISSING line right after it ("-" when there is none).
awk '
  pending != "" { m = "-"; if (index($0, "    MISSING: the site has no ") == 1) m = substr($0, 30); print pending "|" m; pending = "" }
  /^  [^ ].*\(site copy: / { x = $0; sub(/.*\(site copy: /, "", x); match(x, /^[^ ),]+/); pending = substr(x, RSTART, RLENGTH) }
' "$T/out" > "$T/pairs"
rows="$(wc -l < "$T/pairs" | tr -d ' ')"
if [ "$rows" = "$n" ]; then printf 'ok   every tracked file has a drift line (%s)\n' "$n"; else printf 'FAIL drift lines: expected %s, got %s\n' "$n" "$rows"; fails=$((fails+1)); fi
while IFS='|' read -r shown checked; do
  case "$NO_FIXED_PATH" in
    *" $shown "*)
      if [ "$checked" = "-" ]; then printf 'ok   %s: no fixed site path, never MISSING\n' "$shown"
      else printf 'FAIL %s has no fixed site path, but was checked as %s\n' "$shown" "$checked"; fails=$((fails+1)); fi ;;
    *)
      if [ "$shown" = "$checked" ]; then printf 'ok   %s: shown and checked alike\n' "$shown"
      else printf 'FAIL drift line names %s, MISSING check looked for %s\n' "$shown" "$checked"; fails=$((fails+1)); fi ;;
  esac
done < "$T/pairs"
has   "a template test in a subfolder keeps its path"        "    MISSING: the site has no tests/sub/x.spec.ts"

# Imports of changed specs. Each spec is one case; the site lacks every file unless noted.
IS="$T/isuite" IP="$T/isite"
mkdir -p "$IS/scripts"
cp "$HERE/whats-new.sh" "$IS/scripts/"
spec() { local dest="$IS/$A/tests/$1"; mkdir -p "$(dirname "$dest")"; shift; printf '%s\n' "$@" > "$dest"; }  # spec <path> <line>...
spec keep.spec.ts "import { n } from '../never/there';"     # unchanged: never checked
spec gone.spec.ts "import { g } from '../gone/thing';"      # deleted upstream
$git -C "$IS" init -q && $git -C "$IS" add -A && $git -C "$IS" commit -qm base
IBASE="$($git -C "$IS" rev-parse HEAD)"
$git -C "$IS" rm -q "$A/tests/gone.spec.ts"
spec t1.spec.ts  "import { onRequest } from '../functions/_middleware';"
spec t3.spec.ts  "import { site } from '../src/config';" "import { obfuscate } from '../src/lib/obfuscate';" "import { o } from '../src/lib/other';"
spec t4.spec.ts  'import { d } from "../dq/a";' "import '../bare/b';"
spec t6.spec.ts  "import x from '../../outside';"
spec t8.spec.ts  "import a from '../m/a';" "import b from '../m/b';" "import c from '../m/c';" "import d from '../m/d';" "import e from '../m/e.json';"
spec sub/n.spec.ts "import { h } from '../_helpers';"
spec t12.spec.ts "import { e } from './_extra';"
spec t14.spec.ts "// was: import theme from '../v1/theme'" "import x from'../x14';"
spec t15.spec.ts 'import x /* was "../src/config" */ from "../missing-module";' "import { read } from 'node:fs'; load('../fixture');" \
  'import/* glued */g from "../glued";' "import { w } from 'node:fs'; // from '../fixture2'" \
  'import { "from" as f } from "../named-from";' "import 'node:fs'; // from '../fixture3'"
spec t16.spec.ts "import r from '../';"
$git -C "$IS" add -A && $git -C "$IS" commit -qm later
mkdir -p "$IP/.claude/skills" "$IP/tests" "$IP/src/lib" "$IP/m/d"
stamp "$IP/.claude/skills/SUITE-VERSION" "$IBASE"
stamp "$IP/tests/TESTS-VERSION" "$IBASE"
echo v1 > "$IP/tests/keep.spec.ts"
echo v1 > "$IP/src/config.ts"
for x in a.tsx b.js c.mjs d/index.ts e.json; do echo v1 > "$IP/m/$x"; done

report "$IS" "$IP" "a site lacking imported files"
nf() { printf '    IMPORT NOT FOUND: %s (this spec imports it)' "$1"; }
has   "T1 a missing import is named"                          "$(nf functions/_middleware)"
has   "T1 the closing block names spec and import"            "  tests/t1.spec.ts → functions/_middleware"
has   "T1 the closing block has its heading"                  "Specs that import a file this site lacks. Before taking one, take the file too, change"
has   "T3 the second missing import is named"                 "$(nf src/lib/obfuscate)"
has   "T3 the third missing import is named"                  "$(nf src/lib/other)"
has   "T3 each has its own closing line"                      "  tests/t3.spec.ts → src/lib/obfuscate"
has   "T3 each has its own closing line (2)"                  "  tests/t3.spec.ts → src/lib/other"
hasnt "T3 a file the site has is not named"                   "NOT FOUND: src/config"
has   "T4 a double-quoted import is read"                     "$(nf dq/a)"
has   "T4 a bare import is read"                              "$(nf bare/b)"
hasnt "T5 a spec deleted upstream is not checked"             "gone/thing"
if grep -q '^fatal:' "$T/out"; then echo "FAIL T5 git printed an error"; fails=$((fails+1)); else echo "ok   T5 no git error"; fi
has   "T6 an import leaving the site is said, not skipped"    "    IMPORT NOT CHECKED: ../../outside points outside the site or at its top folder"
has   "T6 an import of the site's top folder is said too"     "    IMPORT NOT CHECKED: ../ points outside the site or at its top folder"
hasnt "T7 an unchanged spec is not checked"                   "never/there"
hasnt "T8 every lookup form counts as present"                "NOT FOUND: m/"
has   "T10 a nested spec resolves from its own folder"        "$(nf tests/_helpers)"
has   "T12 a sibling import is checked"                       "$(nf tests/_extra)"
hasnt "T14 a commented-out import is not read"                "v1/theme"
has   "T14 an import with no blank before its quote is read"  "$(nf x14)"
has   "T15 the path after from is read, not one in a comment" "$(nf missing-module)"
hasnt "T15 a relative string after a package import is not"   "fixture"
has   "T15 a comment right after import is a blank"           "$(nf glued)"
has   "T15 a string named from is not the keyword"           "$(nf named-from)"
# Every IMPORT line follows the spec's git log lines (or another IMPORT line), so the pairing
# check above never reads one as a drift line's MISSING line.
if awk '/^    IMPORT / && prev !~ /^    ([0-9a-f]+ |IMPORT )/ { bad = 1 } { prev = $0 } END { exit !bad }' "$T/out"; then
  echo "FAIL an IMPORT line does not follow its spec's log lines"; fails=$((fails+1))
else echo "ok   every IMPORT line follows its spec's log lines"; fi
NOTICE="Import check: reads one-line \"import … from './…'\" and \"import '../…'\" lines only (the path after the first 'from', or a bare import's own; relative paths only); other forms are not checked."
has   "T13 the import check states its limit"                 "$NOTICE"
if awk -v n="$NOTICE" '/^Specs that import a file this site lacks/ { h = NR } $0 == n { m = NR } END { exit !(h && m > h) }' "$T/out"; then
  echo "ok   T13 the notice comes after the closing block"
else echo "FAIL T13 the notice is not after the closing block"; fails=$((fails+1)); fi

# T8: each lookup form, removed in turn, is then named.
for x in a.tsx:m/a b.js:m/b c.mjs:m/c d/index.ts:m/d e.json:m/e.json; do
  mv "$IP/m/${x%%:*}" "$T/moved"
  report "$IS" "$IP" "T8 without m/${x%%:*}"
  has "T8 without m/${x%%:*} it is named" "$(nf "${x#*:}")"
  mv "$T/moved" "$IP/m/${x%%:*}"
done

# T9 then T2: an empty folder of the import's name is not the file; the file itself is.
mkdir -p "$IP/functions/_middleware"
report "$IS" "$IP" "T9 an empty folder of that name"
has   "T9 an empty folder does not count"                     "$(nf functions/_middleware)"
echo v1 > "$IP/functions/_middleware.ts"
report "$IS" "$IP" "T2 the site has the file"
hasnt "T2 a file the site has is not named"                   "NOT FOUND: functions/_middleware"
hasnt "T2 nor in the closing block"                           "→ functions/_middleware"

# T13: with no changed spec there is no import check, and so no notice.
S3="$T/suite3" P3="$T/site3"
mkdir -p "$S3/scripts" "$P3/.claude/skills" "$P3/tests" "$P3/scripts/hooks"
cp "$HERE/whats-new.sh" "$S3/scripts/"
put "$S3/$A/scripts/hooks/pre-push" v1
$git -C "$S3" init -q && $git -C "$S3" add -A && $git -C "$S3" commit -qm base
BASE3="$($git -C "$S3" rev-parse HEAD)"
put "$S3/$A/scripts/hooks/pre-push" v2
$git -C "$S3" add -A && $git -C "$S3" commit -qm later
stamp "$P3/.claude/skills/SUITE-VERSION" "$BASE3"
stamp "$P3/tests/TESTS-VERSION" "$BASE3"
echo v1 > "$P3/scripts/hooks/pre-push"
report "$S3" "$P3" "T13 no changed spec"
hasnt "T13 no changed spec, no notice"                        "Import check:"

# T11: the real template specs, every one counted as changed, against a copy of the starter
# they ship with: today's real imports must raise no false alarm.
S4="$T/suite4" P4="$T/site4"
mkdir -p "$S4/scripts" "$S4/$A" "$P4/.claude/skills"
cp "$HERE/whats-new.sh" "$S4/scripts/"
$git -C "$S4" init -q && $git -C "$S4" add -A && $git -C "$S4" commit -qm base
BASE4="$($git -C "$S4" rev-parse HEAD)"
cp -R "$HERE/../$A/tests" "$S4/$A/"
$git -C "$S4" add -A && $git -C "$S4" commit -qm later
cp -R "$HERE/../$A/." "$P4/"
stamp "$P4/.claude/skills/SUITE-VERSION" "$BASE4"
stamp "$P4/tests/TESTS-VERSION" "$BASE4"
report "$S4" "$P4" "T11 the real specs against the starter"
has   "T11 the real specs were checked"                       "$NOTICE"
hasnt "T11 no false alarm on the real imports"                "IMPORT NOT"
# And the check really read them: a file the starter's specs import, removed, is named.
rm "$P4/src/lib/obfuscate.ts"
report "$S4" "$P4" "T11 the starter without src/lib/obfuscate.ts"
has   "T11 a real spec's import is read and resolved"         "$(nf src/lib/obfuscate)"

[ "$fails" -eq 0 ] || { echo "$fails test(s) failed" >&2; exit 1; }
echo "all whats-new missing-file and import tests passed"
