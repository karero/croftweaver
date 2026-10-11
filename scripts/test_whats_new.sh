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
put "$S/$C/hooks/git-stand.mjs" v1                  # added, the site lacks it
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
has   "the closing summary lists the missing files"           "  scripts/verify.mjs"
hasnt "a changed file the site has is not MISSING"            "no scripts/hooks/pre-push"
hasnt "a changed test the site has is not MISSING"            "no tests/a.spec.ts"
has   "a file deleted upstream is still listed as drift"      "  templates/astro/scripts/set_pdf_title.py (site copy: scripts/set_pdf_title.py)"
hasnt "a file deleted upstream is not MISSING"                "no scripts/set_pdf_title.py"

# A site older than TESTS-VERSION falls back to its SUITE-VERSION baseline: the sites this
# check exists for, so the same file must be MISSING there too.
rm "$P/tests/TESTS-VERSION"
report "$S" "$P" "a site with no TESTS-VERSION"
has   "the SUITE-VERSION fallback marks MISSING too"          "    MISSING: the site has no scripts/verify.mjs"
stamp "$P/tests/TESTS-VERSION" "$BASE"

# Once the site has every file, nothing is MISSING, though the drift report still runs.
echo v1 > "$P/scripts/verify.mjs"; echo v1 > "$P/tests/b.spec.ts"
mkdir -p "$P/.claude/hooks" && echo v1 > "$P/.claude/hooks/git-stand.mjs"
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

[ "$fails" -eq 0 ] || { echo "$fails test(s) failed" >&2; exit 1; }
echo "all whats-new missing-file tests passed"
