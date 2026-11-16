#!/usr/bin/env bash
#
# test_config_lines.sh — runs the starter's tests/check_analytics_gate.sh and tests/check_deploy.sh
# on sites whose src/config.ts predates their lines, and `make whats-new` on a site whose copies
# of those two tests are behind.
#
# Why it exists: both tests read src/config.ts, which is the site's own file, so `whats-new`
# never lists a line the site lacks. A site made before 0.35 then failed the new gate with a
# pointer to release notes that did not name the line (one with no PROD_BRANCH export failed
# outright), and check_deploy.sh named four lines without saying which one was missing. These
# cases pin that the failures before a build name the missing line as the starter writes it,
# and that the report says the two tests read src/config.ts.
#
# Usage: bash scripts/test_config_lines.sh
set -u
for tool in git node make; do
  command -v "$tool" >/dev/null 2>&1 || { echo "FAIL test_config_lines.sh needs $tool"; exit 1; }
done
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
A="skills/new-website/templates/astro"
T="$(mktemp -d "${TMPDIR:-/tmp}/config-lines-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git="git -c user.name=t -c user.email=t@t -c init.defaultBranch=main -c commit.gpgsign=false -c core.hooksPath=/dev/null"
fails=0
# run <dir> <command...>: runs it in <dir>, keeps its output in $T/out and its status in $rc.
run() { local d="$1"; shift; (cd "$d" && "$@") >"$T/out" 2>&1; rc=$?; }
check() { if [ "$2" = "$3" ]; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s (expected %s, got %s)\n' "$1" "$2" "$3"; fails=$((fails+1)); fi; }
has()   { if grep -qF -- "$2" "$T/out"; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s (no text: %s)\n' "$1" "$2"; sed 's/^/     | /' "$T/out"; fails=$((fails+1)); fi; }
hasnt() { if grep -qF -- "$2" "$T/out"; then printf 'FAIL %s (found: %s)\n' "$1" "$2"; fails=$((fails+1)); else printf 'ok   %s\n' "$1"; fi; }
ENABLED="enabled: USE_ANALYTICS && (process.env.CF_PAGES_BRANCH ?? process.env.WORKERS_CI_BRANCH) === PROD_BRANCH,"
# The starter's own line must be the one the messages give, or they would send a site wrong.
check "the starter's config.ts has the line the messages give" 1 "$(grep -cF "  $ENABLED" "$HERE/../$A/src/config.ts")"

# The gate on a site with no PROD_BRANCH export, as one made before the line existed.
G="$T/gate"
mkdir -p "$G/tests" "$G/src"
cp "$HERE/../$A/tests/check_analytics_gate.sh" "$G/tests/"
cat >"$G/src/config.ts" <<'TS'
export const ANALYTICS = {
  scriptHost: 'https://stats.example.com',
  scriptId: 'pa-x',
  enabled: process.env.CF_PAGES_BRANCH === 'main',
};
TS
run "$G" bash tests/check_analytics_gate.sh
check "gate, no PROD_BRANCH: fails"                         1 "$rc"
has   "... names the line to add"                           "export const PROD_BRANCH = 'production';"
has   "... and the enabled: line that compares against it"  "$ENABLED"
has   "... and, with no USE_ANALYTICS line, says to add one" "add export const USE_ANALYTICS = true; as well"

# The gate on a site that has the export but an enabled: line reading CF_PAGES_BRANCH only.
cat >"$G/src/config.ts" <<'TS'
export const PROD_BRANCH = 'production';
export const USE_ANALYTICS = true;
export const ANALYTICS = {
  scriptHost: 'https://stats.example.com',
  scriptId: 'pa-x',
  enabled: USE_ANALYTICS && process.env.CF_PAGES_BRANCH === PROD_BRANCH,
};
TS
run "$G" bash tests/check_analytics_gate.sh
check "gate, enabled: without WORKERS_CI_BRANCH: fails"     1 "$rc"
has   "... says what the line reads"                        "it reads: none"
has   "... and gives the starter's line"                    "$ENABLED"
hasnt "... with no pointer to release notes"                "release notes"
hasnt "... nor a USE_ANALYTICS line the site already has"   "add export const USE_ANALYTICS"

# The gate on a site made before the switch: no USE_ANALYTICS line, an enabled: line reading
# CF_PAGES_BRANCH only. The starter's line reads USE_ANALYTICS, so pasting it alone breaks the build.
cat >"$G/src/config.ts" <<'TS'
export const PROD_BRANCH = 'production';
export const ANALYTICS = {
  scriptHost: 'https://stats.example.com',
  scriptId: 'pa-x',
  enabled: process.env.CF_PAGES_BRANCH === PROD_BRANCH,
};
TS
run "$G" bash tests/check_analytics_gate.sh
check "gate, no USE_ANALYTICS line: fails"                  1 "$rc"
has   "... gives the starter's line"                        "$ENABLED"
has   "... and the USE_ANALYTICS line it needs"             "add export const USE_ANALYTICS = true; as well"

# check_deploy.sh on a Workers site whose config.ts lacks PROD_BRANCH and USE_ANALYTICS.
D="$T/deploy"
mkdir -p "$D/tests" "$D/src" "$D/scripts" "$D/node_modules"
cp "$HERE/../$A/tests/check_deploy.sh" "$D/tests/"
: >"$D/scripts/deploy.sh"
echo '{"name": "site", "assets": {"directory": "./dist"}}' >"$D/wrangler.jsonc"
cat >"$D/src/config.ts" <<'TS'
export const ANALYTICS = {
  scriptHost: 'https://stats.example.com',
  scriptId: 'pa-x',
};
TS
run "$D" bash tests/check_deploy.sh
check "check_deploy, two lines missing: fails"              1 "$rc"
has   "... names PROD_BRANCH"                               "export const PROD_BRANCH = 'production';"
has   "... names USE_ANALYTICS"                             "export const USE_ANALYTICS = true;"
hasnt "... and not the lines that are there"                "scriptHost: '…'"

# `make whats-new` on a site whose copies of both tests are behind a throwaway suite.
S="$T/suite" SITE="$T/site"
mkdir -p "$S/scripts" "$S/$A/tests" "$SITE/tests"
cp "$HERE/whats-new.sh" "$S/scripts/"
for f in check_analytics_gate.sh check_deploy.sh other.spec.ts; do echo v1 >"$S/$A/tests/$f"; cp "$S/$A/tests/$f" "$SITE/tests/"; done
$git -C "$S" init -q && $git -C "$S" add -A && $git -C "$S" commit -qm base
printf 'suite_commit: %s\ncopied: 2026-01-01\n' "$($git -C "$S" rev-parse HEAD)" >"$SITE/tests/TESTS-VERSION"
mkdir -p "$SITE/.claude/skills" && cp "$SITE/tests/TESTS-VERSION" "$SITE/.claude/skills/SUITE-VERSION"
for f in check_analytics_gate.sh check_deploy.sh other.spec.ts; do echo v2 >"$S/$A/tests/$f"; done
$git -C "$S" commit -qam later
run "$S" make -s --no-print-directory -f "$HERE/../Makefile" whats-new PROJECT="$SITE"
check "make whats-new exits 0"                              0 "$rc"
for f in check_analytics_gate.sh check_deploy.sh; do
  has "whats-new: tests/$f says it reads src/config.ts"     "tests/$f (site copy: tests/$f — it reads src/config.ts, the site's own file, which this report never lists"
done
has   "... and another test keeps the plain line"           "tests/other.spec.ts (site copy: tests/other.spec.ts)"

if [ $fails -ne 0 ]; then echo "$fails check(s) FAILED"; exit 1; fi
echo "all checks passed"
