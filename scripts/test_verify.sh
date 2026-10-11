#!/usr/bin/env bash
#
# test_verify.sh — drives the site template's scripts/verify.mjs (`npm run verify`, and what
# the pre-push hook runs) with a stubbed `npm`.
#
# Why it exists: verify.mjs decides when to reinstall packages (only when package.json or
# package-lock.json differs from the last install it made), hides `npm run check`'s output unless it fails, and
# must stop at the first red step. A wrong guess in the install step means tests run against
# stale packages, or a full `npm ci` on every push; neither shows as a red test. These cases
# pin which npm commands run, in which order, from which folder, and what each exit means.
#
# Usage: bash scripts/test_verify.sh
set -u
if ! command -v node >/dev/null 2>&1; then
  echo "SKIP: test_verify.sh needs node (verify.mjs is a Node script)"
  exit 0
fi
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
VERIFY="$HERE/../skills/new-website/templates/astro/scripts/verify.mjs"
T="$(mktemp -d "${TMPDIR:-/tmp}/verify-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
# The physical path: the stub npm logs `pwd` as the shell finds it, and where the temp folder
# sits behind a symlink (macOS: /var -> /private/var) the two spellings would never match.
phys="$(CDPATH= cd -- "$T" && pwd -P)" || exit 1
T="$phys"
# Run through `npm run`, npm would hand verify.mjs its own entry point in npm_execpath; this
# test starts it with node directly, as the hook does, so the stub below is what runs.
unset npm_execpath
fails=0
check() { if [ "$2" = "$3" ]; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s (expected %s, got %s)\n' "$1" "$2" "$3"; fails=$((fails+1)); fi; }

# A stub npm: logs each call as "<folder>|<args>" and fails the step NPM_FAIL names.
mkdir -p "$T/bin"
cat >"$T/bin/npm" <<'NPM'
#!/bin/sh
printf '%s|%s\n' "$(pwd)" "$*" >>"$CALLS"
case "$*" in
  ci\ *)                                 step=ci ;;
  "run --silent check")                  step=check; echo "CHECK-SAYS-SOMETHING"
                                         # More than Node's default 1 MiB pipe buffer.
                                         [ -n "${NPM_LOUD:-}" ] && head -c 2097152 /dev/zero | tr '\0' x ;;
  "run --silent test -- --reporter=dot") step=test; echo "TEST-SAYS-SOMETHING" ;;
  *)                                     step=other ;;
esac
[ "${NPM_FAIL:-}" = "$step" ] && { echo "$step went red"; exit 1; }
exit 0
NPM
chmod +x "$T/bin/npm"
export PATH="$T/bin:$PATH" CALLS="$T/calls"

SITE="$T/site"
mkdir -p "$SITE/scripts" "$T/elsewhere"
cp "$VERIFY" "$SITE/scripts/verify.mjs"
# go — runs verify.mjs from another folder (it must find the site from its own path); prints
# its output, then "@@rc=<status>". calls — the npm calls of the last run, one word each.
go() { : >"$CALLS"; (cd "$T/elsewhere" && node "$SITE/scripts/verify.mjs") 2>&1; printf '@@rc=%s\n' "$?"; }
calls() { sed 's/^[^|]*|//; s/^ci .*/ci/; s/^run --silent check$/check/; s/^run --silent test -- --reporter=dot$/test/' "$CALLS" | tr '\n' ' ' | sed 's/ $//'; }
rc() { printf '%s\n' "$1" | sed -n 's/^@@rc=//p'; }
has() { case "$1" in *"$2"*) echo yes ;; *) echo no ;; esac; }

out="$(go)"
check "no package-lock.json: fails"                         1 "$(rc "$out")"
check "... says why"                                        yes "$(has "$out" "no package-lock.json")"
check "... and runs no npm at all"                          "" "$(calls)"

echo '{"lockfileVersion": 3}' >"$SITE/package-lock.json"
out="$(go)"
check "first run (no node_modules): green"                  0 "$(rc "$out")"
check "... installs, then check, then tests"                "ci check test" "$(calls)"
check "... every npm call runs in the site's folder"        "$SITE" "$(cut -d'|' -f1 "$CALLS" | sort -u)"
check "... the check's output stays hidden when it passes"  no "$(has "$out" "CHECK-SAYS-SOMETHING")"
check "... the tests' output streams through"               yes "$(has "$out" "TEST-SAYS-SOMETHING")"
check "... and it says so"                                  yes "$(has "$out" "✓ verify: all green")"
check "... and leaves the lockfile's hash behind"           yes "$([ -s "$SITE/node_modules/.verify-lock-hash" ] && echo yes || echo no)"

out="$(go)"
check "second run, same lockfile: no install"               "check test" "$(calls)"

echo '{"lockfileVersion": 3, "changed": true}' >"$SITE/package-lock.json"
out="$(NPM_FAIL=ci go)"
check "lockfile changed, npm ci fails: fails"               1 "$(rc "$out")"
check "... nothing after the install runs"                  "ci" "$(calls)"
check "... and npm ci's output is shown"                    yes "$(has "$out" "ci went red")"
out="$(go)"
check "... so the next run installs again"                  "ci check test" "$(calls)"
out="$(go)"
check "... and once that worked, not again"                 "check test" "$(calls)"

echo '{"name": "site", "scripts": {"verify": "node scripts/verify.mjs"}}' >"$SITE/package.json"
out="$(go)"
check "package.json changed, lockfile not: installs"        "ci check test" "$(calls)"
out="$(go)"
check "... and once that worked, not again"                 "check test" "$(calls)"

out="$(NPM_LOUD=1 go)"
check "a passing check that prints 2 MiB: still green"      0 "$(rc "$out")"
check "... and its output stays hidden"                     no "$(has "$out" "xxxxxxxx")"

out="$(NPM_FAIL=check go)"
check "check fails: fails"                                  1 "$(rc "$out")"
check "... the tests do not run"                            "check" "$(calls)"
check "... and the check's output is shown"                 yes "$(has "$out" "CHECK-SAYS-SOMETHING")"

out="$(NPM_FAIL=test go)"
check "tests fail: fails"                                   1 "$(rc "$out")"
check "... after check and tests ran"                       "check test" "$(calls)"
check "... and never says green"                            no "$(has "$out" "all green")"

# Run as `npm run verify`, npm_execpath names npm's own JS entry: verify.mjs starts that
# with node instead of looking for npm on PATH (where Windows has only npm.cmd).
cat >"$T/npm-cli.js" <<'JS'
require('fs').appendFileSync(process.env.CALLS, process.cwd() + '|' + process.argv.slice(2).join(' ') + '\n');
JS
: >"$CALLS"
(cd "$T/elsewhere" && npm_execpath="$T/npm-cli.js" node "$SITE/scripts/verify.mjs") >/dev/null 2>&1
check "npm_execpath set: npm's entry runs through node"     "check test" "$(calls)"
out="$(cd "$T/elsewhere" && VERIFY_TRACE=1 npm_execpath="$T/npm-cli.js" node "$SITE/scripts/verify.mjs" 2>&1)"
check "VERIFY_TRACE names the npm_execpath branch"          yes "$(has "$out" "verify: npm via npm_execpath (npm-cli.js)")"
out="$(VERIFY_TRACE=1 go)"
check "VERIFY_TRACE names the PATH branch"                  yes "$(has "$out" "verify: npm from PATH")"
out="$(go)"
check "... and says nothing without VERIFY_TRACE"           no "$(has "$out" "verify: npm from PATH")"
# pnpm and yarn set npm_execpath to their own entry, which has no `npm ci`: npm on PATH runs.
cat >"$T/pnpm.cjs" <<'JS'
require('fs').appendFileSync(process.env.CALLS + '-pnpm', 'ran\n');
JS
: >"$CALLS"
(cd "$T/elsewhere" && npm_execpath="$T/pnpm.cjs" node "$SITE/scripts/verify.mjs") >/dev/null 2>&1
check "npm_execpath names pnpm: the npm on PATH runs"       "check test" "$(calls)"
check "... and pnpm's entry did not"                        no "$([ -e "$CALLS-pnpm" ] && echo yes || echo no)"

if [ $fails -ne 0 ]; then echo "$fails check(s) FAILED"; exit 1; fi
echo "all checks passed"
