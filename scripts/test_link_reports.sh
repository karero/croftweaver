#!/usr/bin/env bash
#
# test_link_reports.sh — runs the starter's scripts/check_external_links.sh the way a site runs
# it (bash from the site's repo), with a stub npm and a stub curl, so it needs no network.
#
# Why it exists: a failed build was swallowed and the report said "0 links healthy", and a URL
# written with &amp; in the HTML went to the server with the entity in it. These cases pin that
# a build the script cannot audit stops it with exit 1 and a message, and that the URL it
# fetches has & where the HTML has &amp;.
#
# Usage: bash scripts/test_link_reports.sh
set -u
command -v git >/dev/null 2>&1 || { echo "FAIL test_link_reports.sh needs git"; exit 1; }
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(dirname -- "$HERE")"
LS="$ROOT/skills/new-website/templates/astro/scripts/check_external_links.sh"
T="$(mktemp -d "${TMPDIR:-/tmp}/link-reports-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
fails=0
ok()   { printf 'ok   %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; fails=$((fails+1)); }

# npm fails (a build that cannot finish); curl records the URL it was given and answers 200.
mkdir "$T/stub" \
  && printf '#!/bin/sh\necho "npm: stub: build failed" >&2\nexit 1\n' >"$T/stub/npm" \
  && printf '#!/bin/sh\nfor a in "$@"; do u="$a"; done\necho "$u" >>"$CURL_LOG"\nprintf "200 %%s" "$u"\n' >"$T/stub/curl" \
  && chmod +x "$T/stub/npm" "$T/stub/curl" \
  || { echo "FAIL — could not build the stubs."; exit 1; }

# site <name> — a fresh site repo; its path is in $S.
site() {
  S="$T/$1"
  mkdir "$S" && git init -q "$S" \
    && printf "export default { site: 'https://example.com' };\n" >"$S/astro.config.mjs" \
    || { echo "FAIL — could not build the $1 fixture."; exit 1; }
}
# run — runs the script from $S; sets rc, out (stdout and stderr), urls (what curl was asked for).
run() {
  : >"$T/curl.log"
  out="$(cd "$S" && CURL_LOG="$T/curl.log" PATH="$T/stub:$PATH" bash "$LS" 2>&1 </dev/null)"; rc=$?
  urls="$(cat "$T/curl.log")"
}

# No dist/ and a build that fails: exit 1, a message, no report.
site nodist
run
if [ "$rc" -eq 1 ] && [ -z "$urls" ] && printf '%s' "$out" | grep -q 'build failed' \
   && ! printf '%s' "$out" | grep -q 'links healthy'; then
  ok "no dist/ and a failing build: exit 1, says so, prints no report"
else
  fail "no dist/ and a failing build: exit $rc, out: $out"
fi

# A dist/ with no page in it: exit 1, a message, no report.
site emptydist
mkdir "$S/dist"
run
if [ "$rc" -eq 1 ] && printf '%s' "$out" | grep -q 'holds no HTML page' \
   && ! printf '%s' "$out" | grep -q 'links healthy'; then
  ok "a dist/ with no page: exit 1, says so, prints no report"
else
  fail "a dist/ with no page: exit $rc, out: $out"
fi

# A real dist/: the link is fetched with & for &amp;, and the run still exits 0.
site amp
mkdir "$S/dist"
printf '<a href="https://a.invalid/p?x=1&amp;y=2">a</a>\n<a href="https://b.invalid/q?x=1&#x26;y=2">b</a>\n' >"$S/dist/index.html"
run
if [ "$rc" -eq 0 ] && [ "$urls" = "$(printf 'https://a.invalid/p?x=1&y=2\nhttps://b.invalid/q?x=1&y=2')" ] \
   && printf '%s' "$out" | grep -q 'OK: 2 links healthy'; then
  ok "&amp; and &#x26; in a link reach the server as &; exit 0, 2 links healthy"
else
  fail "&amp; decoding: exit $rc, curl was asked for [$urls], out: $out"
fi

if [ "$fails" -ne 0 ]; then echo "$fails check(s) FAILED"; exit 1; fi
echo "all checks passed"
