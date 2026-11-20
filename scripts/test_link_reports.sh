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
# The internal-link report is run on built pages too: a page ORPHAN_EXEMPT names (either quote
# style) is not an orphan and is not counted as having two inbound links, and an unlisted one still is.
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

# check_internal_links.sh on a built dist/ of five pages. /about and /team link to each other and
# to /lp/a; /lp/spring, /lp/summer (exempt, one in each quote style) and /lost (not exempt) have
# no inbound link. Expected by hand: orphans = /lost only; 2 pages with >=2 inbound links
# (/about and /team are linked from "/" and from each other); the exempt pages are in neither list.
IL="$ROOT/skills/new-website/templates/astro/scripts/check_internal_links.sh"
site intlinks
mkdir -p "$S/dist" "$S/tests"
printf '<a href="/about">a</a><a href="/team">t</a>\n' >"$S/dist/index.html"
printf '<a href="/team">t</a>\n' >"$S/dist/about.html"
printf '<a href="/about">a</a>\n' >"$S/dist/team.html"
for pg in lp-spring lp-summer lost; do printf '<p>x</p>\n' >"$S/dist/$pg.html"; done
mkdir -p "$S/dist/lp" && mv "$S/dist/lp-spring.html" "$S/dist/lp/spring.html" && mv "$S/dist/lp-summer.html" "$S/dist/lp/summer.html"
printf "const ORPHAN_EXEMPT = new Set<string>([\n  '/lp/spring',  // single quotes\n  \"/lp/summer\",  // double quotes\n]);\n" >"$S/tests/orphans.spec.ts"
out="$(cd "$S" && bash "$IL" 2>&1 </dev/null)"; rc=$?
orph="$(printf '%s\n' "$out" | sed -n '/^## ORPHANS/,/^## THIN/p')"
if [ "$rc" -eq 0 ] && printf '%s' "$orph" | grep -q '^/lost$' && ! printf '%s' "$orph" | grep -q '/lp/' \
   && printf '%s' "$out" | grep -q 'ORPHANS.*(1)' && printf '%s' "$out" | grep -q '^## OK: 2 page(s)'; then
  ok "internal links: exempt pages (both quote styles) are no orphans and not counted OK; /lost is the one orphan"
else
  fail "internal links: exit $rc, out: $out"
fi

# The set written on one line: only its own entry is exempt, and a '/x' literal further down the
# file is not (the range of lines that is read ends at the first "])").
printf "const ORPHAN_EXEMPT = new Set<string>(['/lp/spring']);\nconst ROOT = '/lost';\n" >"$S/tests/orphans.spec.ts"
out="$(cd "$S" && bash "$IL" 2>&1 </dev/null)"; rc=$?
orph="$(printf '%s\n' "$out" | sed -n '/^## ORPHANS/,/^## THIN/p')"
if [ "$rc" -eq 0 ] && printf '%s' "$orph" | grep -q '^/lost$' && printf '%s' "$orph" | grep -q '^/lp/summer$' \
   && ! printf '%s' "$orph" | grep -q '^/lp/spring$'; then
  ok "internal links: a one-line ORPHAN_EXEMPT exempts its own entry only"
else
  fail "internal links, one-line set: exit $rc, out: $out"
fi

if [ "$fails" -ne 0 ]; then echo "$fails check(s) FAILED"; exit 1; fi
echo "all checks passed"
