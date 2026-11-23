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
# The internal-link report is run on built pages too: a page orphan-exempt.txt names is not an
# orphan, an unlisted one still is, and a bad line in the file stops the run.
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

# The site's own links are dropped whatever their case, and by plain string: with site: 'https://Example.COM',
# a link to EXAMPLE.com, www.example.com or example.com:8080 is the site's own, but example-com is another host.
site own
printf "export default { site: 'https://Example.COM' };\n" >"$S/astro.config.mjs"
mkdir "$S/dist"
printf '<a href="https://EXAMPLE.com/x">a</a>\n<a href="https://www.example.com/y">b</a>\n<a href="https://example.com:8080/z">c</a>\n<a href="https://example-com/o">d</a>\n<a href="https://a.invalid/p">e</a>\n' >"$S/dist/index.html"
run
if [ "$rc" -eq 0 ] && [ "$urls" = "$(printf 'https://a.invalid/p\nhttps://example-com/o')" ]; then
  ok "own links are dropped in any case; a host that differs by one character is not"
else
  fail "own host: exit $rc, curl was asked for [$urls], out: $out"
fi

# check_internal_links.sh on a built dist/ of six pages: "/", /about and /team (linked from "/" and
# from each other, so /about and /team have 2 inbound links each), /lp/spring and /lp/summer
# (exempt in orphan-exempt.txt) and /lost (not exempt); the last three have no inbound link.
# Plus the starter's 404 page, which nothing links to and which is never an orphan. /lost is built
# as lost/index.html (a page in a folder), and the file holds a commented-out '/lost' line,
# which exempts nothing. The site holds the real starter's spec and orphan-exempt.mjs, as a site
# built from the starter does.
# Expected by hand: orphans = /lost only; 2 pages with >=2 inbound links; exempt pages and /404 in neither list.
ASTRO="$ROOT/skills/new-website/templates/astro"
IL="$ASTRO/scripts/check_internal_links.sh"
# il — runs the report from $S; sets rc, out (stdout), ilerr (stderr) and orph (the ORPHANS section).
il() {
  out="$(cd "$S" && bash "$IL" 2>"$T/il.err" </dev/null)"; rc=$?; ilerr="$(cat "$T/il.err")"
  orph="$(printf '%s\n' "$out" | sed -n '/^## ORPHANS/,/^## THIN/p')"
}
# Both words of the old-form warning, so a quiet run can be told from a warned one.
warned() { printf '%s' "$ilerr" | grep -q 'orphan-exempt.txt' && printf '%s' "$ilerr" | grep -q 'are not read'; }
site intlinks
mkdir -p "$S/dist" "$S/tests" "$S/scripts"
cp "$ASTRO/scripts/orphan-exempt.mjs" "$S/scripts/"
cp "$ASTRO/tests/orphans.spec.ts" "$S/tests/"
printf '<a href="/about">a</a><a href="/team">t</a>\n' >"$S/dist/index.html"
printf '<a href="/team">t</a>\n' >"$S/dist/about.html"
printf '<a href="/about">a</a>\n' >"$S/dist/team.html"
for pg in lp-spring lp-summer 404; do printf '<p>x</p>\n' >"$S/dist/$pg.html"; done
mkdir -p "$S/dist/lp" "$S/dist/lost" && mv "$S/dist/lp-spring.html" "$S/dist/lp/spring.html" && mv "$S/dist/lp-summer.html" "$S/dist/lp/summer.html" \
  && printf '<p>x</p>\n' >"$S/dist/lost/index.html"
printf '# unlinked on purpose\n/lp/spring  # the ad page\n/lp/summer\n# /lost\n' >"$S/orphan-exempt.txt"
il
if [ "$rc" -eq 0 ] && printf '%s' "$orph" | grep -q '^/lost$' && ! printf '%s' "$orph" | grep -q '/lp/\|/404' \
   && printf '%s' "$out" | grep -q 'ORPHANS.*(1)' && printf '%s' "$out" | grep -q '^## OK: 2 page(s)' && ! warned; then
  ok "internal links: pages in orphan-exempt.txt and /404 are no orphans; /lost (named only in a comment) is the one orphan; no warning"
else
  fail "internal links: exit $rc, out: $out, stderr: $ilerr"
fi

# A whole address, not a prefix: /x is exempt, but /x/y (an unlinked page under it) is still an orphan.
site prefix
mkdir -p "$S/dist/x" "$S/scripts"
cp "$ASTRO/scripts/orphan-exempt.mjs" "$S/scripts/"
printf '<p>home</p>\n' >"$S/dist/index.html"; printf '<p>x</p>\n' >"$S/dist/x.html"; printf '<p>y</p>\n' >"$S/dist/x/y.html"
printf '/x\n' >"$S/orphan-exempt.txt"
il
if [ "$rc" -eq 0 ] && printf '%s' "$orph" | grep -q '^/x/y$' && ! printf '%s' "$orph" | grep -q '^/x$' && printf '%s' "$out" | grep -q 'ORPHANS.*(1)'; then
  ok "internal links: /x in orphan-exempt.txt exempts /x only, not /x/y"
else
  fail "internal links, whole-line match: exit $rc, orphans: $orph"
fi

# Back to the first site, for the cases that change its list or its spec.
S="$T/intlinks"
# A bad line stops the run, naming file and line, whatever form the spec is in (new, old or none).
printf '/lp/spring\nnope\n' >"$S/orphan-exempt.txt"
spec_new="$S/tests/orphans.spec.ts"; spec_save="$T/orphans.spec.ts.real"; cp "$spec_new" "$spec_save"
for form in new old none; do
  case "$form" in
    new)  cp "$spec_save" "$spec_new" ;;
    old)  printf "const ORPHAN_EXEMPT = new Set<string>(['/lp/old']);\n" >"$spec_new" ;;
    none) rm -f "$spec_new" ;;
  esac
  il
  if [ "$rc" -eq 1 ] && printf '%s' "$ilerr" | grep -qF 'orphan-exempt.txt line 2: ' && ! printf '%s' "$out" | grep -q '^## ORPHANS'; then
    ok "internal links: a bad line in orphan-exempt.txt stops the run with file and line (spec: $form)"
  else
    fail "internal links, bad line, spec $form: exit $rc, out: $out, stderr: $ilerr"
  fi
done

# No file: no exemptions, exit 0 (a site with no unlinked pages needs none).
rm -f "$S/orphan-exempt.txt"; cp "$spec_save" "$spec_new"
il
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q 'ORPHANS.*(3)' && printf '%s' "$orph" | grep -q '^/lp/spring$' && ! warned; then
  ok "internal links: no orphan-exempt.txt means no exemptions, exit 0"
else
  fail "internal links, no file: exit $rc, out: $out, stderr: $ilerr"
fi

# A spec still in the old form (it holds ORPHAN_EXEMPT): a warning, exit 0, its list is not read,
# and the file, if there is one, still applies.
printf "const ORPHAN_EXEMPT = new Set<string>(['/lost', '/lp/summer']);\n" >"$spec_new"
printf '/lp/spring\n' >"$S/orphan-exempt.txt"
il
if [ "$rc" -eq 0 ] && warned && printf '%s' "$orph" | grep -q '^/lost$' && printf '%s' "$orph" | grep -q '^/lp/summer$' \
   && ! printf '%s' "$orph" | grep -q '^/lp/spring$'; then
  ok "internal links: an old-form spec warns on stderr, exit 0, its list is not read, the file still applies"
else
  fail "internal links, old-form spec: exit $rc, orphans: $orph, stderr: $ilerr"
fi

# No spec and no file: no exemptions, exit 0, no warning. No spec and a file: the entries apply.
rm -f "$spec_new" "$S/orphan-exempt.txt"
il
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q 'ORPHANS.*(3)' && ! warned; then
  ok "internal links: no spec and no file: no exemptions, exit 0, no warning"
else
  fail "internal links, no spec and no file: exit $rc, out: $out, stderr: $ilerr"
fi
printf '/lp/spring\n/lp/summer\n' >"$S/orphan-exempt.txt"
il
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q 'ORPHANS.*(1)' && printf '%s' "$orph" | grep -q '^/lost$' && ! warned; then
  ok "internal links: no spec, a file with entries: the entries apply"
else
  fail "internal links, no spec and a file: exit $rc, out: $out, stderr: $ilerr"
fi

# The script found without scripts/orphan-exempt.mjs (a site that took only the script): stops with
# a message that names the three files, not node's MODULE_NOT_FOUND.
cp "$spec_save" "$spec_new"; mv "$S/scripts/orphan-exempt.mjs" "$T/orphan-exempt.mjs.held"
il
if [ "$rc" -eq 1 ] && printf '%s' "$ilerr" | grep -qF 'scripts/orphan-exempt.mjs is missing' && ! printf '%s' "$ilerr$out" | grep -q 'MODULE_NOT_FOUND'; then
  ok "internal links: without scripts/orphan-exempt.mjs it stops and names the file"
else
  fail "internal links, module missing: exit $rc, out: $out, stderr: $ilerr"
fi
mv "$T/orphan-exempt.mjs.held" "$S/scripts/orphan-exempt.mjs"

# No node on PATH (an existing dist/ never builds, so nothing else would notice): stops and says so.
# The script runs by its absolute bash, with a PATH holding git and nothing else.
mkdir "$T/gitonly" && ln -s "$(command -v git)" "$T/gitonly/git"
out="$(cd "$S" && PATH="$T/gitonly" /bin/bash "$IL" 2>"$T/il.err" </dev/null)"; rc=$?; ilerr="$(cat "$T/il.err")"
if [ "$rc" -eq 1 ] && printf '%s' "$ilerr" | grep -qF 'node is not on PATH' && ! printf '%s' "$out" | grep -q '^## ORPHANS'; then
  ok "internal links: no node on PATH stops with a message, before any report"
else
  fail "internal links, no node: exit $rc, out: $out, stderr: $ilerr"
fi

# An exempt page that other pages do link to is a healthy page: it counts as OK.
printf '/lp/spring\n' >"$S/orphan-exempt.txt"
printf '<a href="/lp/spring">s</a>\n' >"$S/dist/about.html"; printf '<a href="/lp/spring">s</a><a href="/about">a</a>\n' >"$S/dist/team.html"
il
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q '^## OK: 2 page(s)'; then
  ok "internal links: an exempt page with two inbound links counts as OK"
else
  fail "internal links, exempt page with inbound links: exit $rc, out: $out"
fi

if [ "$fails" -ne 0 ]; then echo "$fails check(s) FAILED"; exit 1; fi
echo "all checks passed"
