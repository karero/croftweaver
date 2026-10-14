#!/usr/bin/env bash
#
# test_package_leak.sh — drives scripts/package.sh's zip integrity check against fake zip
# listings: a copy of package.sh runs in a throwaway dir with stub `zip` and `unzip` first on
# PATH, so nothing is built and the real dist/ is never touched.
#
# Why it exists: the leak checks used to read `grep … | head -5 | grep .` under pipefail. Once
# the leaked listing passed the pipe buffer (~64 KiB), head's early exit killed the first
# grep — SIGPIPE (141), or EPIPE (exit 2) where SIGPIPE is ignored, as on GitHub Actions
# runners — pipefail reported that, the `if` went false, and the guard missed exactly the
# large leak it exists for (20,000 node_modules paths shipped; 50 were caught). Each large
# case therefore runs twice: with SIGPIPE at its default, and ignored.
#
# Usage: bash scripts/test_package_leak.sh
set -u
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
T="$(mktemp -d "${TMPDIR:-/tmp}/package-leak-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/repo/scripts" "$T/bin"
cp "$HERE/package.sh" "$T/repo/scripts/package.sh"

# Stubs: zip writes one line where the zip would go (so there is a file to checksum); unzip -Z1
# prints the listing under test, unzip -l a total line.
cat >"$T/bin/zip" <<'EOF'
#!/bin/sh
printf 'stub zip\n' >"$3"
EOF
cat >"$T/bin/unzip" <<'EOF'
#!/bin/sh
case "$1" in
  -Z1) cat "$LISTING" ;;
  -l)  echo "  0  0 files" ;;
esac
EOF
chmod +x "$T/bin/zip" "$T/bin/unzip"

# Every listing starts from package.sh's own REQUIRED list, so only the leak decides.
awk '/^REQUIRED=\($/{p=1; next} p && /^\)$/{exit} p{print $1}' "$HERE/package.sh" >"$T/required"
fails=0
check() { if "${@:2}"; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s\n' "$1"; fails=$((fails+1)); fi; }
[ "$(grep -c . "$T/required")" -ge 5 ] || { echo "FAIL could not read package.sh's REQUIRED list"; exit 1; }

# listing <name> <count> <path prefix> — the REQUIRED files plus <count> leaked paths
listing() {
  { cat "$T/required"; awk -v n="$2" -v p="$3" 'BEGIN{for(i=1;i<=n;i++) print p i "/index.js"}'; } >"$T/$1.list"
}
# run <name> [perl-ignore] — runs the package.sh copy against $T/<name>.list
run() {
  local pre=()
  [ "${2:-}" = ignore ] && pre=(perl -e '$SIG{PIPE}="IGNORE"; exec @ARGV')
  PATH="$T/bin:$PATH" LISTING="$T/$1.list" ${pre[@]+"${pre[@]}"} bash "$T/repo/scripts/package.sh" \
    >"$T/$1${2:+.$2}.out" 2>&1
  echo $? >"$T/$1${2:+.$2}.rc"
}
rc_is() { [ "$(cat "$T/$1.rc")" = "$2" ]; }
has()   { grep -qF -- "$2" "$T/$1.out"; }
lines() { [ "$(grep -c -- "$2" "$T/$1.out")" = "$3" ]; }

# The checksum file a release uploads beside the zip. Why: a download is only worth comparing
# with a checksum that describes the zip that was built and checked, never an older one.
D="$T/repo/dist"
sums_match() {
  [ "$(grep -c . "$D/SHA256SUMS")" = 1 ] && grep -Eq '^[0-9a-f]{64}  croftweaver[.]zip$' "$D/SHA256SUMS" \
    && (cd "$D" && if command -v sha256sum >/dev/null 2>&1; then sha256sum -c --status SHA256SUMS
                   else shasum -a 256 -c -s SHA256SUMS; fi)
}
no_sums() { [ ! -e "$D/SHA256SUMS" ]; }

listing clean 0 x
run clean
check "clean listing: exit 0" rc_is clean 0
check "clean listing: integrity OK" has clean "zip integrity OK"
check "clean listing: SHA256SUMS names the zip and matches it" sums_match

listing small 50 skills/new-website/templates/astro/node_modules/pkg
printf 'stale\n' >"$D/SHA256SUMS"   # left from an earlier build
run small
check "a failed build leaves no SHA256SUMS, not even an earlier one" no_sums
check "50 node_modules paths: exit 1" rc_is small 1
check "50 node_modules paths: counted" has small "FAIL — 50 node_modules path(s) leaked"
check "50 node_modules paths: only the first 5 are listed" lines small '/node_modules/pkg' 5

# 20,000 paths is ~1 MiB of listing, far past any pipe buffer.
listing bignm 20000 skills/new-website/templates/astro/node_modules/pkg
listing bigrev 20000 docs/reviews/round
modes="default"
if command -v perl >/dev/null 2>&1; then modes="default ignore"
else echo "SKIP the SIGPIPE-ignored runs: they need perl to start bash with SIGPIPE ignored"; fi
for m in $modes; do
  if [ "$m" = ignore ]; then run bignm ignore; run bigrev ignore; n=bignm.ignore; r=bigrev.ignore; sfx=" (SIGPIPE ignored)"
  else run bignm; run bigrev; n=bignm; r=bigrev; sfx=""; fi
  check "20,000 node_modules paths: exit 1$sfx" rc_is "$n" 1
  check "20,000 node_modules paths: counted$sfx" has "$n" "FAIL — 20000 node_modules path(s) leaked"
  check "20,000 docs/reviews paths: exit 1$sfx" rc_is "$r" 1
  check "20,000 docs/reviews paths: counted$sfx" has "$r" "FAIL — 20000 internal review/plan artifact(s) leaked"
done

# The maintainer's trackers are repo-only: either one in the listing fails the build.
for f in BUGLOG DECISIONS_PENDING; do
  { cat "$T/required"; echo "docs/$f.md"; } >"$T/tracker-$f.list"
  run "tracker-$f"
  check "docs/$f.md in the zip: exit 1" rc_is "tracker-$f" 1
  check "docs/$f.md in the zip: named" has "tracker-$f" "FAIL — 1 maintainer tracker file(s) leaked"
done
# A shipped doc whose name only starts like a tracker's is not one.
{ cat "$T/required"; echo "docs/BUGLOG.md.html"; echo "skills/x/docs/BUGLOG.md"; } >"$T/lookalike.list"
run lookalike
check "look-alike names are not trackers: exit 0" rc_is lookalike 0

# A scan that errors must fail, not read as "nothing leaked": awk stubbed to fail, on a clean listing.
mkdir -p "$T/badawk"
printf '#!/bin/sh\nexit 2\n' >"$T/badawk/awk"; chmod +x "$T/badawk/awk"
PATH="$T/badawk:$T/bin:$PATH" LISTING="$T/clean.list" bash "$T/repo/scripts/package.sh" >"$T/badawk.out" 2>&1
echo $? >"$T/badawk.rc"
check "a scan that errors fails closed: exit 1" rc_is badawk 1
check "a scan that errors fails closed: says so" has badawk "FAIL — could not scan the zip listing"

listing missing 0 x
grep -vFx LICENSE "$T/missing.list" >"$T/missing.tmp" && mv "$T/missing.tmp" "$T/missing.list"
run missing
check "a missing required file still fails" has missing "MISSING from zip: LICENSE"

if [ "$fails" -eq 0 ]; then echo "all checks passed"; else echo "$fails check(s) FAILED"; exit 1; fi
