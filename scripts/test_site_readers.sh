#!/usr/bin/env bash
#
# test_site_readers.sh — every reader of `site:` in the starter's astro.config.mjs, run the way a site runs them.
#
# Why it exists: the readers were separate greps that did not all agree. scripts/ship.sh and
# scripts/deploy.sh carry the same three functions (each file stands alone in a site, so they
# cannot share one); the two link reports had their own, without ship's left edge, so a key
# that ends in `site:` (`website:`) was read as the site's address. A non-ASCII letter before
# `site:` was read as a name break in one locale and as the key in another.
#
# What it checks:
#   - the copies of site_of, site_count and js_state in ship.sh and deploy.sh are the same text, and
#     the extraction it compares by does see a change (so an empty extraction cannot pass);
#   - a no-break space, BOM or other Unicode space before `site:` ends the name before it;
#   - those functions give the same answer in the C locale and in a UTF-8 one, for an address
#     with letters above ASCII, a key that follows such a letter and a byte that is not UTF-8;
#   - the external and internal link reports take the site's host from the `site:` key, not
#     from `website:`.
#
# Usage: bash scripts/test_site_readers.sh
set -u
command -v git >/dev/null 2>&1 || { echo "FAIL test_site_readers.sh needs git"; exit 1; }
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(dirname -- "$HERE")"
SC="$ROOT/skills/new-website/templates/astro/scripts"
T="$(mktemp -d "${TMPDIR:-/tmp}/site-readers-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
fails=0
ok()   { printf 'ok   %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; fails=$((fails+1)); }

# --- 1. The two copies are one text -------------------------------------------------------------
# The same extraction tests/check_deploy.sh uses: from the readers' first comment line to the end
# of js_state.
reader() { awk '/^# The `site:` address in the astro.config.mjs text given/{p=1} p{print} p&&/^js_state\(\)/{j=1} j&&/^}$/{exit}' "$1"; }
reader "$SC/ship.sh" >"$T/ship.readers"; reader "$SC/deploy.sh" >"$T/deploy.readers"
if [ "$(grep -c '^site_count()' "$T/ship.readers")" = 1 ] && [ "$(grep -c '^js_state()' "$T/ship.readers")" = 1 ] \
   && cmp -s "$T/ship.readers" "$T/deploy.readers"; then
  ok "ship.sh and deploy.sh hold the same site_of, site_count and js_state"
else
  fail "ship.sh and deploy.sh differ in site_of, site_count or js_state (diff below): copy them from one file to the other"
  diff "$T/ship.readers" "$T/deploy.readers" | head -20
fi
# The comparison must fail when one copy gains a line inside the readers: change the source, then extract again.
awk '{print} /^# The `site:` address in the astro.config.mjs text given/{print "# drift"}' "$SC/deploy.sh" >"$T/deploy.drifted.sh"
reader "$T/deploy.drifted.sh" >"$T/drifted.readers"
if [ -s "$T/drifted.readers" ] && grep -q '^# drift$' "$T/drifted.readers" && ! cmp -s "$T/ship.readers" "$T/drifted.readers"; then ok "the comparison sees a change in one copy"; else fail "the comparison did not see a change in one copy"; fi

# --- 2. The same answer in every locale ---------------------------------------------------------
utf8_loc=""
locales="$(locale -a 2>/dev/null || true)"
for l in C.UTF-8 en_US.UTF-8 en_US.utf8 C.utf8; do
  if printf '%s\n' "$locales" | grep -qix "$l"; then utf8_loc="$l"; break; fi
done
# answer <locale> <config text>: "<site_count>|<site_of>" with the readers sourced into a fresh bash in that locale.
answer() {
  LC_ALL="$1" bash -c '. "$1"; printf "%s|%s" "$(site_count "$2")" "$(site_of "$2")"' _ "$T/ship.readers" "$2"
}
# check_locales <label> <config text> <expected answer, by hand>
check_locales() {
  local label="$1" text="$2" want="$3" loc got
  for loc in C ${utf8_loc:+"$utf8_loc"}; do
    got="$(answer "$loc" "$text")"
    if [ "$got" = "$want" ]; then ok "$label, in the $loc locale: $want"; else fail "$label, in the $loc locale: wanted [$want], got [$got]"; fi
  done
}
[ -n "$utf8_loc" ] || echo "  note: the UTF-8 half of the locale cases is skipped: no UTF-8 locale (C.UTF-8 or en_US.UTF-8) on this machine."
check_locales "an address with letters above ASCII" "export default { site: 'https://müller-bäckerei.de/' };
" "one|https://müller-bäckerei.de"
check_locales "a key that follows a letter above ASCII is another key" "export default { 日本site: 'https://wrong.example' };
" "none|"
check_locales "that key beside the real one" "export default { üsite: 'https://wrong.example', site: 'https://right.example' };
" "one|https://right.example"
# JavaScript white space that is not ASCII ends a name: no-break space, BOM, line separator, ideographic space.
for ws in '\302\240' '\357\273\277' '\342\200\250' '\343\200\200'; do
  check_locales "a Unicode space ($(printf "$ws" | od -An -tx1 | tr -d ' \n')) before site:" "$(printf "export default { ${ws}site: 'https://right.example' };\n")" "one|https://right.example"
done
# A // comment ends at a Unicode line separator (U+2028, U+2029): the key after it is code, not comment.
for sep in '\342\200\250' '\342\200\251'; do
  check_locales "a key after a // comment and a line separator ($(printf "$sep" | od -An -tx1 | tr -d ' \n'))" "$(printf "export default { // note${sep}site: 'https://right.example' };\n")" "one|https://right.example"
done
# A byte that is not UTF-8 (Latin-1 ü) in the address: read as bytes, so both locales keep it.
latin1="$(printf "export default { site: 'https://m\374ller.de/' };\n")"
check_locales "a byte that is not UTF-8 in the address" "$latin1" "$(printf 'one|https://m\374ller.de')"

# --- 3. The link reports read the site's own key ------------------------------------------------
# A stub npm that fails and a stub curl that records the URL it was asked for, as in test_link_reports.sh.
mkdir "$T/stub" \
  && printf '#!/bin/sh\necho "npm: stub: build failed" >&2\nexit 1\n' >"$T/stub/npm" \
  && printf '#!/bin/sh\nfor a in "$@"; do u="$a"; done\necho "$u" >>"$CURL_LOG"\nprintf "200 %%s" "$u"\n' >"$T/stub/curl" \
  && chmod +x "$T/stub/npm" "$T/stub/curl" \
  || { echo "FAIL — could not build the stubs."; exit 1; }
# site <name> <astro.config.mjs text> — a fresh site repo in $S.
site() {
  S="$T/$1"
  mkdir "$S" && git init -q "$S" && printf '%s\n' "$2" >"$S/astro.config.mjs" || { echo "FAIL — could not build the $1 fixture."; exit 1; }
}
# A key that only ends in `site:` comes first; the real key is second. Expected by hand: the site is example.com.
# Another decoy sits before them: a key that follows a letter above ASCII, which the C locale must not take for `site:`.
# The real key follows a no-break space, which is white space.
CONF="$(printf "export default { üsite: 'https://decoy2.example', website: 'https://decoy.example', \302\240site: 'https://example.com' };")"

# External report: links to the site's own host are not fetched; the decoys' are.
site extern "$CONF"
mkdir "$S/dist"
printf '<a href="https://example.com/own">o</a><a href="https://decoy.example/x">d</a><a href="https://decoy2.example/y">d</a>\n' >"$S/dist/index.html"
for loc in C ${utf8_loc:+"$utf8_loc"}; do
  : >"$T/curl.log"
  out="$(cd "$S" && LC_ALL="$loc" CURL_LOG="$T/curl.log" PATH="$T/stub:$PATH" bash "$SC/check_external_links.sh" 2>&1 </dev/null)"; rc=$?
  urls="$(sort "$T/curl.log")"
  if [ "$rc" -eq 0 ] && [ "$urls" = "$(printf 'https://decoy.example/x\nhttps://decoy2.example/y')" ]; then
    ok "external links, in the $loc locale: the site's own host comes from site:, not from website: or üsite:"
  else
    fail "external links, in the $loc locale: exit $rc, curl was asked for [$urls] (wanted the two decoys only), out: $out"
  fi
done

# Internal report: an absolute link to the site's own host counts as a link to that page.
site intern "$CONF"
mkdir "$S/dist" "$S/tests" "$S/scripts"
cp "$SC/orphan-exempt.mjs" "$S/scripts/"   # the report reads orphan-exempt.txt through it
printf '<a href="https://example.com/about">a</a>\n' >"$S/dist/index.html"
printf '<p>x</p>\n' >"$S/dist/about.html"
for loc in C ${utf8_loc:+"$utf8_loc"}; do
  out="$(cd "$S" && LC_ALL="$loc" bash "$SC/check_internal_links.sh" 2>&1 </dev/null)"; rc=$?
  orph="$(printf '%s\n' "$out" | sed -n '/^## ORPHANS/,/^## THIN/p')"
  if [ "$rc" -eq 0 ] && ! printf '%s' "$orph" | grep -q '^/about$' && printf '%s' "$out" | grep -q 'ORPHANS.*(0)'; then
    ok "internal links, in the $loc locale: an absolute link to the site's own host reaches the page, whatever the decoys say"
  else
    fail "internal links, in the $loc locale: exit $rc, orphans: $orph"
  fi
done

if [ "$fails" -ne 0 ]; then echo "$fails check(s) FAILED"; exit 1; fi
echo "all checks passed"
