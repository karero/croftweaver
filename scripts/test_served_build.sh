#!/usr/bin/env bash
#
# test_served_build.sh — runs the site template's tests/served-build.spec.ts through
# `playwright test` in fixed setups: which id the run expects, which id dist/ holds, which id
# the server sends.
#
# Why it exists: the spec must fail when the server is not this run's build, and say why. A
# normal `npm test` only ever shows it passing. Its old version compared the served id with the
# one on disk, so a second build in the same folder changed both and passed; the second case
# below is that build, and would pass again under that version.
#
# Needs the template's packages (`npm ci` in skills/new-website/templates/astro), node and
# python3 (a static server on 127.0.0.1). No browser: the spec only makes HTTP requests.
#
# Usage: bash scripts/test_served_build.sh
set -u
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
SITE="$HERE/../skills/new-website/templates/astro"
PW="$SITE/node_modules/.bin/playwright"
[ -x "$PW" ] || { echo "FAIL — no $PW: run npm ci in skills/new-website/templates/astro first."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "FAIL — test_served_build.sh needs python3."; exit 1; }
T="$(mktemp -d "${TMPDIR:-/tmp}/served-build-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
server=
trap '[ -n "$server" ] && kill "$server" 2>/dev/null; rm -rf "$T"' EXIT

# A copy of the site holding only what the spec and the marker need; packages come from the
# template through a link, so the copy resolves @playwright/test the same way.
mkdir -p "$T/site/tests" "$T/site/scripts" "$T/site/dist" "$T/www"
cp "$SITE/tests/served-build.spec.ts" "$T/site/tests/"
cp "$SITE/playwright.config.ts" "$SITE/package.json" "$T/site/"
cp "$SITE/scripts/build-marker.mjs" "$T/site/scripts/"
ln -s "$SITE/node_modules" "$T/site/node_modules"

port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')"
# The site's own config, minus its web server, pointed at the static server. The run id is set
# after the site's config has set its own, in the main process only, as the site's config does.
cat >"$T/site/run.config.ts" <<EOF
import base from './playwright.config';
if (!process.env.TEST_WORKER_INDEX) process.env.SITE_TEST_BUILD = process.env.CASE_RUN_ID;
export default { ...base, webServer: undefined, retries: 0, use: { ...base.use, baseURL: 'http://127.0.0.1:$port' } };
EOF
python3 -m http.server --bind 127.0.0.1 --directory "$T/www" "$port" >/dev/null 2>&1 &
server=$!
for _ in $(seq 1 50); do
  python3 -c "import urllib.request as u; u.urlopen('http://127.0.0.1:$port/')" 2>/dev/null && break
  sleep 0.2
done

fails=0
# case <name> <run id> <disk id|-> <served id|-> <expected exit> [phrase in the output]
case_() {
  local name="$1" run="$2" disk="$3" served="$4" want="$5" phrase="${6:-}" out code
  rm -f "$T/site/dist/test-build-id.txt" "$T/www/test-build-id.txt"
  [ "$disk" = - ] || printf '%s\n' "$disk" >"$T/site/dist/test-build-id.txt"
  [ "$served" = - ] || printf '%s\n' "$served" >"$T/www/test-build-id.txt"
  out="$(cd "$T/site" && CASE_RUN_ID="$run" CI= "$PW" test -c run.config.ts --reporter=line 2>&1)"
  code=$?
  if [ "$code" -ne "$want" ]; then
    printf 'FAIL %s (exit %s, expected %s)\n%s\n' "$name" "$code" "$want" "$(printf '%s\n' "$out" | tail -n 25)"; fails=$((fails+1))
  elif [ -n "$phrase" ] && ! printf '%s' "$out" | grep -qF -- "$phrase"; then
    printf 'FAIL %s (no "%s" in the output)\n%s\n' "$name" "$phrase" "$(printf '%s\n' "$out" | tail -n 25)"; fails=$((fails+1))
  else
    printf 'ok   %s\n' "$name"
  fi
}

case_ "run, disk and server agree: passes" run-a run-a run-a 0
case_ "another build in this folder (disk = served, not the run's): fails" \
  run-a build-b build-b 1 "another build in this folder replaced dist/"
case_ "another checkout's server (disk = run, served differs): fails" \
  run-a run-a other-c 1 "another server answers on this port"
case_ "all three differ: fails, both causes" \
  run-a build-b other-c 1 "another server answers on this port, and another build"
case_ "the server sends no id: fails" run-a run-a - 1 "The server sent no test-build id (HTTP 404"
case_ "no run id: fails" "" run-a run-a 1 "SITE_TEST_BUILD is not set"

# The marker writes the run's id, and with none set removes the file.
(cd "$T/site" && SITE_TEST_BUILD=marker-id node scripts/build-marker.mjs >/dev/null 2>&1)
got="$(cat "$T/site/dist/test-build-id.txt" 2>/dev/null)"
if [ "$got" = marker-id ]; then echo "ok   the marker writes SITE_TEST_BUILD"
else echo "FAIL the marker wrote '$got', expected marker-id"; fails=$((fails+1)); fi
(cd "$T/site" && env -u SITE_TEST_BUILD node scripts/build-marker.mjs >/dev/null 2>&1)
if [ ! -e "$T/site/dist/test-build-id.txt" ]; then echo "ok   the marker removes the id when unset"
else echo "FAIL the marker left dist/test-build-id.txt with SITE_TEST_BUILD unset"; fails=$((fails+1)); fi

if [ "$fails" -ne 0 ]; then echo "✗ served-build spec: $fails case(s) failed"; exit 1; fi
echo "✓ served-build spec: every case passed"
