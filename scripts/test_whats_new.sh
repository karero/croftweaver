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
put "$S/$A/tests/middleware.spec.ts" v1
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
put "$S/$A/scripts/deploy.sh" v1                    # added, a Workers-only file (0.35)
$git -C "$S" rm -q "$A/tests/middleware.spec.ts"    # a Pages-only spec, removed from the starter (0.35)
$git -C "$S" add -A && $git -C "$S" commit -qm later

# The site, stamped at the baseline and holding only the files it had then.
P="$T/site"
mkdir -p "$P/.claude/skills" "$P/tests" "$P/scripts/hooks"
stamp "$P/.claude/skills/SUITE-VERSION" "$BASE"
stamp "$P/tests/TESTS-VERSION" "$BASE"
echo v1 > "$P/scripts/hooks/pre-push"
echo v1 > "$P/tests/a.spec.ts"
echo v1 > "$P/tests/middleware.spec.ts"

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
# deploy.sh is for Workers sites: a site still on Pages must not be told to copy it.
has   "a Workers-only script is listed as drift"              "  templates/astro/scripts/deploy.sh (site copy: scripts/deploy.sh — Workers sites only; a site still on Cloudflare Pages must not take it until it has moved, and also needs wrangler.jsonc, the \"wrangler\" devDependency and the deploy:preview and deploy:live scripts in its package.json)"
hasnt "a Workers-only script is never MISSING"                "no scripts/deploy.sh"
# A spec removed with Pages Functions tells the site to keep its copy, not to delete it.
has   "a removed Pages-only spec says keep your copy"         "  tests/middleware.spec.ts (removed from the starter with Pages Functions and analytics server mode; keep your copy while the site keeps the functions/ file it imports, otherwise delete it)"
# The changed spec's import the site lacks is named (the full import cases are further down).
has   "a changed spec names an import the site lacks"         "    IMPORT NOT FOUND: src/lib/y (this spec imports it)"

# A site older than TESTS-VERSION falls back to its SUITE-VERSION baseline: the sites this
# check exists for, so the same file must be MISSING there too.
rm "$P/tests/TESTS-VERSION"
report "$S" "$P" "a site with no TESTS-VERSION"
has   "the SUITE-VERSION fallback marks MISSING too"          "    MISSING: the site has no scripts/verify.mjs"
stamp "$P/tests/TESTS-VERSION" "$BASE"

# A site with template-test copies and no stamp of either kind (no skills folder either) used to
# end in "not a site scaffolded by new-website?". It now says how to pick a baseline; following
# that, the report lists what the site lacks (BUGLOG 2026-11-16).
Q="$T/unstamped"; mkdir -p "$Q/tests"; echo v1 > "$Q/tests/a.spec.ts"
bash "$S/scripts/whats-new.sh" "$Q" > "$T/out" 2>&1; rc=$?
if [ "$rc" -ne 0 ]; then printf 'ok   %s\n' "unstamped copies: exits non-zero"; else printf 'FAIL %s\n' "unstamped copies: exits non-zero"; fails=$((fails+1)); fi
hasnt "unstamped copies: is not called a non-site"             "not a site scaffolded"
has   "unstamped copies: says there is no baseline"            "which suite commit the tests came from, so there is no baseline to compare with."
if grep -qF -- "\" log --format='%H %cs %s'" "$T/out"; then printf 'ok   %s\n' "unstamped copies: prints the command that lists the suite's commits"; else printf 'FAIL %s\n' "unstamped copies: prints the command that lists the suite's commits"; fails=$((fails+1)); fi
pick="$(grep -F "tests/TESTS-VERSION\"" "$T/out" | grep -F "<that commit>")"
if [ -n "$pick" ]; then printf 'ok   %s\n' "unstamped copies: prints the command that writes the stamp"; else printf 'FAIL %s\n' "unstamped copies: prints the command that writes the stamp"; fails=$((fails+1)); fi
eval "${pick//<that commit>/$BASE}"
report "$S" "$Q" "the site after the stamp is written as told"
has   "unstamped copies: then the report lists what is MISSING" "    MISSING: the site has no tests/b.spec.ts"
has   "unstamped copies: and says the skills were not compared" "note: no SUITE-VERSION stamp and no .claude/skills or .agents/skills dir found under $Q, so the bundled skills were not compared."

# BUGLOG 2026-11-19: a left_out or kept line the site wrote is not a file to copy, in either
# path form; a line the stamp added itself (the file is not in the site) still is.
L="$T/leftout"; cp -R "$P" "$L"
printf 'suite_commit: %s\ncopied: 2026-01-01\nleft_out: tests/b.spec.ts — not needed here\nleft_out: scripts/verify.mjs — not needed here\nleft_out: .claude/hooks/git-stand.mjs — not in the site when stamped 2026-01-01\n' "$BASE" > "$L/tests/TESTS-VERSION"
report "$S" "$L" "a site with left_out lines"
hasnt "a left_out line keeps its file off the MISSING list"      "    MISSING: the site has no tests/b.spec.ts"
hasnt "a left_out line, as the site has the path, keeps it off"  "    MISSING: the site has no scripts/verify.mjs"
has   "a line the stamp added does not hide a missing file"      "    MISSING: the site has no .claude/hooks/git-stand.mjs"
has   "a file no line names is still MISSING"                    "    MISSING: the site has no CROFTWEAVER-LICENSE.md"
# A kept line alone, in each path form (relative to tests/, and as the site has it).
K="$T/kept1"; cp -R "$P" "$K"
printf 'suite_commit: %s\ncopied: 2026-01-01\nkept: b.spec.ts — ours\n' "$BASE" > "$K/tests/TESTS-VERSION"
report "$S" "$K" "a site with a kept line relative to tests/"
hasnt "a kept line relative to tests/ keeps its file off"        "    MISSING: the site has no tests/b.spec.ts"
has   "and the other missing files are still listed"             "    MISSING: the site has no scripts/verify.mjs"
K="$T/kept2"; cp -R "$P" "$K"
printf 'suite_commit: %s\ncopied: 2026-01-01\nkept: scripts/verify.mjs — ours\n' "$BASE" > "$K/tests/TESTS-VERSION"
report "$S" "$K" "a site with a kept line as the site has the path"
hasnt "a kept line as the site has the path keeps it off"        "    MISSING: the site has no scripts/verify.mjs"
has   "and a file it does not name is still MISSING"             "    MISSING: the site has no tests/b.spec.ts"

# BUGLOG 2026-11-19: a tests stamp and a skills folder with no SUITE-VERSION (a folder that is
# local, not the kit's) must not fail the run: a note, and the tests-only branch's exit status
# (0 for stale tests, 1 when the tests report failed). With no tests stamp it still stops.
R="$T/localskills"; mkdir -p "$R/.claude/skills" "$R/tests"; echo v1 > "$R/tests/a.spec.ts"
stamp "$R/tests/TESTS-VERSION" "$BASE"
report "$S" "$R" "a tests stamp and an unstamped skills folder"
has   "the unstamped skills folder is a note"                    "note: $R/.claude/skills has no SUITE-VERSION stamp, so the bundled skills were not compared. If the folder is from the kit, stamp it: scripts/whats-new.sh --stamp $R/.claude/skills"
hasnt "and not an error"                                         "predates stamping"
printf 'suite_commit: unknown\n' > "$R/tests/TESTS-VERSION"
bash "$S/scripts/whats-new.sh" "$R" > "$T/out" 2>&1; rc=$?
if [ "$rc" -eq 1 ]; then printf 'ok   %s\n' "an unusable tests baseline with an unstamped skills folder exits 1"; else printf 'FAIL %s (exit %s)\n' "an unusable tests baseline with an unstamped skills folder exits 1" "$rc"; fails=$((fails+1)); fi
has   "the note is still printed when the tests report failed"  "note: $R/.claude/skills has no SUITE-VERSION stamp, so the bundled skills were not compared. If the folder is from the kit, stamp it: scripts/whats-new.sh --stamp $R/.claude/skills"
rm "$R/tests/TESTS-VERSION"
bash "$S/scripts/whats-new.sh" "$R" > "$T/out" 2>&1; rc=$?
if [ "$rc" -eq 1 ]; then printf 'ok   %s\n' "an unstamped skills folder and no tests stamp still exits 1"; else printf 'FAIL %s (exit %s)\n' "an unstamped skills folder and no tests stamp still exits 1" "$rc"; fails=$((fails+1)); fi
has   "and still says the project predates stamping"             "error: $R/.claude/skills exists but has no SUITE-VERSION stamp — the project predates stamping."

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
# translated PUBLISHING.md as PUBLISHING.de.md), or that only some sites take (deploy.sh,
# Workers sites only): their drift line must have no MISSING line.
NO_FIXED_PATH=" PUBLISHING.md scripts/deploy.sh "
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

# S11: a site made before the icon script gets both new files listed as MISSING, with the note
# for each kind of site, and the spec's import of the script named. The files are the real ones.
S5="$T/suite5" P5="$T/site5"
mkdir -p "$S5/scripts" "$S5/$A/scripts" "$S5/$A/tests" "$P5/.claude/skills" "$P5/tests"
cp "$HERE/whats-new.sh" "$S5/scripts/"
$git -C "$S5" init -q && $git -C "$S5" commit -qm base --allow-empty
BASE5="$($git -C "$S5" rev-parse HEAD)"
cp "$HERE/../$A/scripts/make-icons.mjs" "$S5/$A/scripts/"
cp "$HERE/../$A/tests/icons.spec.ts" "$S5/$A/tests/"
$git -C "$S5" add -A && $git -C "$S5" commit -qm later
stamp "$P5/.claude/skills/SUITE-VERSION" "$BASE5"
stamp "$P5/tests/TESTS-VERSION" "$BASE5"
report "$S5" "$P5" "S11 a site without the icon script"
has   "S11 the script is MISSING"                             "    MISSING: the site has no scripts/make-icons.mjs"
has   "S11 the spec is MISSING"                               "    MISSING: the site has no tests/icons.spec.ts"
has   "S11 the spec's import of the script is named"          "$(nf scripts/make-icons.mjs)"
for part in "runs \`node scripts/make-icons.mjs --setup\` before \`npm test\`" "a site with the brand kit's icons needs nothing more" \
            "tab-icon.md copies public/icon-512.png to public/images/logo.png"; do
  if grep -F "make-icons.mjs (site copy" "$T/out" | grep -qF -- "$part"; then printf 'ok   S11 the note says: %s\n' "$part"
  else printf 'FAIL S11 the note lacks: %s\n' "$part"; fails=$((fails+1)); fi
done

# S12: the orphan list moved to orphan-exempt.txt. A site made before it gets the spec, the module and
# the changed script listed, with the migration words, and never a MISSING line for orphan-exempt.txt
# (a site with no unlinked pages needs no file). The words are written out here, never read from
# whats-new.sh, so an arm that is deleted or moved behind the tests/* arm leaves nothing to match.
S7="$T/suite7" P7="$T/site7"
mkdir -p "$S7/scripts" "$S7/$A/scripts" "$S7/$A/tests" "$P7/.claude/skills" "$P7/tests"
cp "$HERE/whats-new.sh" "$S7/scripts/"
$git -C "$S7" init -q && $git -C "$S7" commit -qm base --allow-empty
BASE7="$($git -C "$S7" rev-parse HEAD)"
cp "$HERE/../$A/scripts/orphan-exempt.mjs" "$HERE/../$A/scripts/check_internal_links.sh" "$S7/$A/scripts/"
cp "$HERE/../$A/tests/orphans.spec.ts" "$S7/$A/tests/"
cp "$HERE/../$A/orphan-exempt.txt" "$S7/$A/"
$git -C "$S7" add -A && $git -C "$S7" commit -qm later
stamp "$P7/.claude/skills/SUITE-VERSION" "$BASE7"
stamp "$P7/tests/TESTS-VERSION" "$BASE7"
report "$S7" "$P7" "S12 a site without the orphan files"
has   "S12 the module is MISSING"                             "    MISSING: the site has no scripts/orphan-exempt.mjs"
has   "S12 the spec is MISSING"                               "    MISSING: the site has no tests/orphans.spec.ts"
has   "S12 the spec's import of the module is named"          "$(nf scripts/orphan-exempt.mjs)"
if grep -F "MISSING: the site has no orphan-exempt.txt" "$T/out" | grep -q .; then printf 'FAIL S12 orphan-exempt.txt is listed as MISSING\n'; fails=$((fails+1)); else printf 'ok   S12 orphan-exempt.txt is not listed as MISSING\n'; fi
orphan_note() {  # orphan_note <label> <the file's report line start> <words...>: each phrase is on that file's report line
  local label="$1" start="$2" part; shift 2
  for part in "$@"; do
    if grep -F -- "$start" "$T/out" | grep -qF -- "$part"; then printf 'ok   S12 %s says: %s\n' "$label" "$part"
    else printf 'FAIL S12 %s lacks: %s\n' "$label" "$part"; fails=$((fails+1)); fi
  done
}
orphan_note "the spec's line" "  tests/orphans.spec.ts (site copy" \
  "copy it together with scripts/orphan-exempt.mjs and scripts/check_internal_links.sh" \
  "write each on its own line in orphan-exempt.txt" \
  "you need no file"
orphan_note "the script's line" "  templates/astro/scripts/check_internal_links.sh (site copy" \
  "copy it with scripts/orphan-exempt.mjs, which it runs"
orphan_note "the module's line" "  templates/astro/scripts/orphan-exempt.mjs (site copy" \
  "copy it with tests/orphans.spec.ts"

# L1-L13: --stamp-tests keeps the site's record of files it did not take. It used to write two
# lines only, so a site's `left_out:` and `kept:` lines vanished, and a changed file the site
# lacks dropped out of every later report with no record. The report runs as an owner runs it,
# through make whats-new.
S6="$T/suite6" P6="$T/site6"
mkdir -p "$S6/scripts" "$P6/.claude/skills" "$P6/tests"
cp "$HERE/whats-new.sh" "$S6/scripts/"
put "$S6/$A/tests/a.spec.ts" v1
put "$S6/skills/new-website/templates/AGENTS.md" v1
$git -C "$S6" init -q && $git -C "$S6" add -A && $git -C "$S6" commit -qm base
BASE6="$($git -C "$S6" rev-parse HEAD)"
put "$S6/$A/tests/a.spec.ts" v2                     # changed, the site merges it
put "$S6/skills/new-website/templates/AGENTS.md" v2 # changed, the site leaves it out by hand
put "$S6/$A/tests/new.spec.ts" v1                   # added, the site does not take it
put "$S6/$A/tests/skip.spec.ts" v1                  # added, the owner's line already names it
$git -C "$S6" add -A && $git -C "$S6" commit -qm later
HEAD6="$($git -C "$S6" rev-parse HEAD)"
stamp "$P6/.claude/skills/SUITE-VERSION" "$HEAD6"
stamp "$P6/tests/TESTS-VERSION" "$BASE6"
OWN_KEPT="kept: legacy.spec.ts — not in the site when stamped by an old tool; the site keeps it"
printf '%s\n' "# the owner's note" "# tests/new.spec.ts waits on the designer" "left_out: AGENTS.md — the site keeps its own rules" "kept: old.spec.ts — the starter dropped it; the site still needs it" \
  "left_out: skip.spec.ts — the site has no forms" "$OWN_KEPT" >> "$P6/tests/TESTS-VERSION"
echo v2 > "$P6/tests/a.spec.ts"; echo v1 > "$P6/AGENTS.md"
bash "$S6/scripts/whats-new.sh" --stamp-tests "$P6/tests" > "$T/stamp-out" 2>&1 || { echo "FAIL L1 --stamp-tests exits non-zero"; fails=$((fails+1)); }
cp "$P6/tests/TESTS-VERSION" "$T/out"
TODAY="$(sed -n 's/^copied: //p' "$T/out")"   # the stamp's own date, so a run across midnight still matches
AUTO_NEW="left_out: tests/new.spec.ts — not in the site when stamped $TODAY"
has   "L1 the stamp moves to the suite's head"                "suite_commit: $HEAD6"
has   "L1 the site's left_out line is kept"                   "left_out: AGENTS.md — the site keeps its own rules"
has   "L1 the site's kept line is kept"                       "kept: old.spec.ts — the starter dropped it; the site still needs it"
has   "L1 the owner's comment line is kept"                   "# the owner's note"
has   "L1 an owner's line quoting the marker is kept"         "$OWN_KEPT"
has   "L2 a changed file the site lacks is recorded, though an owner's comment names it" "$AUTO_NEW"
hasnt "L2 a file the site has is not recorded"                "tests/a.spec.ts"
hasnt "L7 a file the owner's line names (tests/-relative) gets no second line" "left_out: tests/skip.spec.ts"
cp "$T/stamp-out" "$T/out"
hasnt "L1 a usable baseline prints no warning"                "warning:"
make -s --no-print-directory -C "$S6" -f "$HERE/../Makefile" whats-new PROJECT="$P6" > "$T/out" 2>&1; rc=$?
if [ "$rc" -eq 0 ]; then echo "ok   L3 make whats-new exits 0"; else echo "FAIL L3 make whats-new exits $rc"; fails=$((fails+1)); fi
has   "L3 the tests channel is up to date"                    "Up to date — no upstream changes to the template test suite / CONTENT_GUIDE / frozen root+infra files."
has   "L3 the report lists the site's record"                 "  left_out: AGENTS.md — the site keeps its own rules"
has   "L3 the report lists the kept file"                     "  kept: old.spec.ts — the starter dropped it; the site still needs it"
has   "L3 the report lists the file not taken"                "  $AUTO_NEW"
# A second stamp while the site still lacks the file keeps the line, once: the baseline has moved
# past the change, so the line is the only record left.
bash "$S6/scripts/whats-new.sh" --stamp-tests "$P6/tests" > /dev/null 2>&1
cp "$P6/tests/TESTS-VERSION" "$T/out"
has   "L6 a second stamp keeps the added line"                "$AUTO_NEW"
n="$(grep -c '^left_out: tests/new.spec.ts ' "$T/out")"
if [ "$n" -eq 1 ]; then echo "ok   L6 ... once"; else echo "FAIL L6 the line is there $n times"; fails=$((fails+1)); fi
has   "L6 the owner's quoting line is still kept"             "$OWN_KEPT"
# Once the site takes the file, the next stamp drops the line it added; the owner's lines stay.
echo v1 > "$P6/tests/new.spec.ts"
bash "$S6/scripts/whats-new.sh" --stamp-tests "$P6/tests" > /dev/null 2>&1
cp "$P6/tests/TESTS-VERSION" "$T/out"
hasnt "L4 a file the site now has loses its line"             "left_out: tests/new.spec.ts"
has   "L4 the owner's comment naming it stays"                "# tests/new.spec.ts waits on the designer"
has   "L4 the owner's line stays"                             "left_out: AGENTS.md — the site keeps its own rules"
# An added line for a file the suite later deletes goes too: nothing is left to take.
put "$S6/$A/tests/gone.spec.ts" v1; $git -C "$S6" add -A && $git -C "$S6" commit -qm "add gone"
bash "$S6/scripts/whats-new.sh" --stamp-tests "$P6/tests" > /dev/null 2>&1
cp "$P6/tests/TESTS-VERSION" "$T/out"
TODAY="$(sed -n 's/^copied: //p' "$T/out")"
has   "L9 a file added since is recorded"                     "left_out: tests/gone.spec.ts — not in the site when stamped $TODAY"
$git -C "$S6" rm -q "$A/tests/gone.spec.ts" && $git -C "$S6" commit -qm "drop gone"
bash "$S6/scripts/whats-new.sh" --stamp-tests "$P6/tests" > /dev/null 2>&1
cp "$P6/tests/TESTS-VERSION" "$T/out"
hasnt "L9 its line goes once the suite deletes the file"      "tests/gone.spec.ts"
# A scaffold stamps the skills, then the tests, at one commit: there is nothing to record.
P7="$T/site7"; mkdir -p "$P7/tests" "$P7/.claude/skills"
bash "$S6/scripts/whats-new.sh" --stamp "$P7/.claude/skills" > /dev/null 2>&1
(cd "$P7" && bash "$S6/scripts/whats-new.sh" --stamp-tests tests) > /dev/null 2>&1
cp "$P7/tests/TESTS-VERSION" "$T/out"
hasnt "L5 a scaffold's first stamp writes no left_out line"   "left_out:"
# A site made before TESTS-VERSION: the first --stamp-tests compares from its skills stamp, as
# the report does, so a file the site lacks is not passed over with no record.
P8="$T/site8"; mkdir -p "$P8/tests" "$P8/.claude/skills"
stamp "$P8/.claude/skills/SUITE-VERSION" "$BASE6"
echo v2 > "$P8/tests/a.spec.ts"; echo v1 > "$P8/tests/skip.spec.ts"; echo v1 > "$P8/AGENTS.md"
bash "$S6/scripts/whats-new.sh" --stamp-tests "$P8/tests" > /dev/null 2>&1
cp "$P8/tests/TESTS-VERSION" "$T/out"
TODAY="$(sed -n 's/^copied: //p' "$T/out")"
has   "L10 no TESTS-VERSION: a file the site lacks is recorded" "left_out: tests/new.spec.ts — not in the site when stamped $TODAY"
hasnt "L10 ... and not one it has"                             "tests/a.spec.ts"
# A baseline this clone does not have cannot be compared: the stamp says so instead of
# passing over the files in silence.
P9="$T/site9"; mkdir -p "$P9/tests"
stamp "$P9/tests/TESTS-VERSION" 0123456789abcdef0123456789abcdef01234567
bash "$S6/scripts/whats-new.sh" --stamp-tests "$P9/tests" > "$T/out" 2>&1; rc=$?
if [ "$rc" -eq 0 ]; then echo "ok   L11 an unknown baseline still stamps"; else echo "FAIL L11 --stamp-tests exits $rc"; fails=$((fails+1)); fi
has   "L11 ... and warns that it cannot list the files"       "warning: the old baseline in $P9/tests/TESTS-VERSION (0123456789abcdef0123456789abcdef01234567) is not a commit in this clone, so this"
cp "$P9/tests/TESTS-VERSION" "$T/out"; TODAY="$(sed -n 's/^copied: //p' "$T/out")"
has   "L11 ... and the stamp keeps a note of the gap"          "# $TODAY: not compared with the suite, so files the site lacks may be unlisted: the old baseline in $P9/tests/TESTS-VERSION (0123456789abcdef0123456789abcdef01234567) is not a commit in this clone"
# A stamp whose baseline is "unknown" compares from the skills stamp.
P10="$T/site10"; mkdir -p "$P10/tests" "$P10/.claude/skills"
stamp "$P10/.claude/skills/SUITE-VERSION" "$BASE6"
stamp "$P10/tests/TESTS-VERSION" unknown
bash "$S6/scripts/whats-new.sh" --stamp-tests "$P10/tests" > /dev/null 2>&1
cp "$P10/tests/TESTS-VERSION" "$T/out"; TODAY="$(sed -n 's/^copied: //p' "$T/out")"
has   "L12 suite_commit: unknown compares from the skills stamp" "left_out: tests/new.spec.ts — not in the site when stamped $TODAY"
# No TESTS-VERSION and no skills stamp this clone has: the stamp warns, as in L11.
P11="$T/site11"; mkdir -p "$P11/tests" "$P11/.claude/skills"
stamp "$P11/.claude/skills/SUITE-VERSION" 0123456789abcdef0123456789abcdef01234567
bash "$S6/scripts/whats-new.sh" --stamp-tests "$P11/tests" > "$T/out" 2>&1
has   "L13 no usable skills stamp either: the stamp warns"     "warning: no stamp in $P11 names a baseline this clone has, so this"
cp "$P11/tests/TESTS-VERSION" "$T/out"; TODAY="$(sed -n 's/^copied: //p' "$T/out")"
has   "L13 ... and keeps a note of the gap"                    "# $TODAY: not compared with the suite, so files the site lacks may be unlisted: no stamp in $P11 names a baseline this clone has"

# S13: a changed workers-config.spec.ts says that taking it can mean a wrangler.jsonc edit that
# changes the deploy (the BUGLOG row of 2026-11-16). The real spec is copied; the words are
# written out here, so a deleted arm, or one moved behind the tests/* arm, leaves the specifics
# nothing to match. The spec must still name each key the note lists and the rule that picks the
# configs it reads, or the note has drifted. This reads the spec's text; that the spec enforces them
# is the starter's own test run.
S13="$T/suite13" P13="$T/site13"
mkdir -p "$S13/scripts" "$S13/$A/tests" "$P13/.claude/skills" "$P13/tests"
cp "$HERE/whats-new.sh" "$S13/scripts/"
$git -C "$S13" init -q && $git -C "$S13" commit -qm base --allow-empty
BASE13="$($git -C "$S13" rev-parse HEAD)"
cp "$HERE/../$A/tests/workers-config.spec.ts" "$S13/$A/tests/"
$git -C "$S13" add -A && $git -C "$S13" commit -qm later
stamp "$P13/.claude/skills/SUITE-VERSION" "$BASE13"
stamp "$P13/tests/TESTS-VERSION" "$BASE13"
report "$S13" "$P13" "S13 a site without the Workers config spec"
for key in "conf.main" "conf.workers_dev" "conf.preview_urls" "'./dist'" "'assets' in conf" "'pages_build_output_dir' in conf" '/\.jsonc?$/'; do
  if grep -qF -- "$key" "$S13/$A/tests/workers-config.spec.ts"; then printf 'ok   S13 the spec still checks: %s\n' "$key"
  else printf 'FAIL S13 the spec no longer checks what the note names: %s\n' "$key"; fails=$((fails+1)); fi
done
for part in "tests/workers-config.spec.ts (site copy: tests/workers-config.spec.ts" "editing wrangler.jsonc" "changes the deploy" \
            "workers_dev: false" "preview_urls: true" "a Pages site skips it"; do
  if grep -F "  tests/workers-config.spec.ts (site copy" "$T/out" | grep -qF -- "$part"; then printf 'ok   S13 the note says: %s\n' "$part"
  else printf 'FAIL S13 the note lacks: %s\n' "$part"; fails=$((fails+1)); fi
done

[ "$fails" -eq 0 ] || { echo "$fails test(s) failed" >&2; exit 1; }
echo "all whats-new missing-file and import tests passed"
