#!/usr/bin/env bash
#
# test_node_floor.sh — runs scripts/check_node_floor.sh on throwaway copies of the files it reads, each
# changed one way, and judges its exit status and what it names. The plan is
# docs/reviews/SKILL-PLAN-node-floor-guard.md; the case numbers below are its scenarios.
#
# Why it exists: the starter's Node floor sat in several places, a Dependabot bump of Astro changed none
# of them, and nothing noticed (Astro 7.4.0 and 7.4.2 each raised its minimum). These cases pin that the
# guard goes red for Astro raising any line, for a floor looser than Astro's, for a range it cannot read,
# for a lockfile root that differs, for a missing Astro entry, a missing file or a JSON file that is not
# an object, for a phrase that is missing, doubled or split over lines, for an .nvmrc or CI major no
# alternative admits, and for a change of the set of Node lines (one more, one fewer, or one widened with
# ">="), and that it stays green when the starter is stricter than Astro and the docs follow. It enters
# the way make check and CI do: it runs the guard script, which finds its files from where it sits, so
# each copy is laid out as the handoff zip is (no repo-root .github/, no packages/, no git).
#
# The versions in the cases are read from the real package.json, so a Node security release that moves a
# version in the range changes ONE line here, EXPECTED_RANGE, which pins the real range on purpose (a
# stale range cannot pass by being stale everywhere at once): after moving engines and the docs, change
# it too. A change in the number of Node lines is a different move: the cases and the version
# plumbing that assume three lines (V22, V24, V26; cases 12, 19 and 20) change with it.
#
# It also compares the guard's --admits answers with npm's own semver (found at
# $(npm root -g)/npm/node_modules/semver) for the edges of every line, runs one real npm install on a
# dependency-free fixture (an unmet engines gives EBADENGINE and exit 0, with no engine-strict), and runs
# the guard and this script with no node on PATH (a skip, or with REQUIRE_NODE_FLOOR=1 a failure).
#
# Without node it prints one SKIP line and exits 0; with REQUIRE_NODE_FLOOR=1 (both CI jobs set it) it
# exits 1. A case that skips for want of npm or its semver module counts the same way.
#
# Usage: bash scripts/test_node_floor.sh
set -u
if ! command -v node >/dev/null 2>&1; then
  echo "SKIP: test_node_floor.sh needs node (the guard reads JSON, and the cases edit it)"
  if [ "${REQUIRE_NODE_FLOOR:-}" = 1 ]; then
    echo "FAIL — REQUIRE_NODE_FLOOR=1: a skip counts as a failure."
    exit 1
  fi
  exit 0
fi
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(dirname -- "$HERE")"
T="$(mktemp -d "${TMPDIR:-/tmp}/node-floor-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
fails=0; skips=0; n=0

TPL=skills/new-website/templates
ASTRO=$TPL/astro
PKG=$ASTRO/package.json
LOCK=$ASTRO/package-lock.json
README=$ASTRO/README.md
SETUP=$TPL/SETUP.md
SKILL=skills/new-website/SKILL.md
UPG=docs/UPGRADING.md
ASTRO_ENG='["packages","node_modules/astro","engines","node"]'
# The real range, pinned on purpose: change it here when a Node security release moves it.
EXPECTED_RANGE='^22.23.4 || ^24.22.1 || >=26.12.1'

# The real range and its three versions, read from package.json: V22 (the lowest), V24 and V26.
RANGE="$(node -e 'console.log(JSON.parse(require("fs").readFileSync(process.argv[1],"utf8")).engines.node)' "$ROOT/$PKG")" \
  || { echo "FAIL — could not read engines.node from $PKG."; exit 1; }
vers="$(node -e 'console.log(process.argv[1].split("||").map(s=>s.trim().replace(/^[\^>=]+\s*/,"")).join(" "))' "$RANGE")" \
  || { echo "FAIL — could not read the versions in \"$RANGE\"."; exit 1; }
set -- $vers
V22=${1:-}; V24=${2:-}; V26=${3:-}
[ -n "$V22" ] && [ -n "$V24" ] && [ -n "$V26" ] \
  || { echo "FAIL — the real range \"$RANGE\" does not name three lines; this test reads V22, V24 and V26 from it."; exit 1; }
bump() { echo "${1%.*}.$(( ${1##*.} + 1 ))"; }   # the patch one higher
# drop — the version just below: the patch one lower, or when the patch is 0 the last of the minor before
# (a release at 24.23.0 gives 24.22.999), and of the major before when the minor is 0 too.
drop() {
  local x=${1%%.*} r=${1#*.}; local y=${r%%.*} z=${r#*.}
  if [ "$z" -gt 0 ]; then echo "$x.$y.$((z-1))"
  elif [ "$y" -gt 0 ]; then echo "$x.$((y-1)).999"
  else echo "$((x-1)).999.999"; fi
}
NEW22="$(bump "$V22")"; NEW24="$(bump "$V24")"; NEW26="$(bump "$V26")"

# fresh — sets c to a new copy of what the guard reads, laid out as the handoff zip is.
fresh() {
  c="$T/repo.$n"; n=$((n+1))
  mkdir -p "$c/scripts" "$c/$ASTRO/.github/workflows" "$c/skills/new-website" "$c/docs" \
    && cp "$ROOT/scripts/check_node_floor.sh" "$c/scripts/" \
    && cp "$ROOT/$PKG" "$ROOT/$LOCK" "$ROOT/$ASTRO/.nvmrc" "$ROOT/$README" "$c/$ASTRO/" \
    && cp "$ROOT/$ASTRO/.github/workflows/ci.yml" "$c/$ASTRO/.github/workflows/" \
    && cp "$ROOT/$SETUP" "$c/$TPL/" \
    && cp "$ROOT/$SKILL" "$c/skills/new-website/" \
    && cp "$ROOT/$UPG" "$c/docs/" \
    || { echo "FAIL — could not copy the files to $c."; exit 1; }
}

# jset <file> <path as JSON> <value as JSON, or __delete__> — edits a JSON file of the copy.
jset() {
  node -e 'const fs=require("fs");const [f,p,v]=process.argv.slice(1);const d=JSON.parse(fs.readFileSync(f,"utf8"));const path=JSON.parse(p);let o=d;for(const k of path.slice(0,-1))o=o[k];if(v==="__delete__")delete o[path[path.length-1]];else o[path[path.length-1]]=JSON.parse(v);fs.writeFileSync(f,JSON.stringify(d,null,2)+"\n")' "$1" "$2" "$3" \
    || { echo "FAIL — could not edit $1."; exit 1; }
}
# tsub <file> <from> <to> — replaces every occurrence of a literal string; fails if there is none.
tsub() {
  node -e 'const fs=require("fs");const [f,a,b]=process.argv.slice(1);const t=fs.readFileSync(f,"utf8");if(!t.includes(a)){console.error("not found: "+a);process.exit(3)}fs.writeFileSync(f,t.split(a).join(b))' "$1" "$2" "$3" \
    || { echo "FAIL — could not edit $1 (looking for: $2): the real text moved, change this test with it."; exit 1; }
}
# set_engines <copy> <range> — the same range in package.json and the lockfile root.
set_engines() {
  jset "$1/$PKG" '["engines","node"]' "\"$2\""
  jset "$1/$LOCK" '["packages","","engines","node"]' "\"$2\""
}

# expect <name> <copy> <pass|fail> [<text the output must hold> [<a second text>]]
expect() {
  local out rc
  out="$(bash "$2/scripts/check_node_floor.sh" 2>&1)"; rc=$?
  if [ "$3" = pass ] && [ "$rc" -ne 0 ]; then
    printf 'FAIL %s: the guard failed (exit %s):\n%s\n' "$1" "$rc" "$out"; fails=$((fails+1)); return
  fi
  if [ "$3" = fail ] && [ "$rc" -eq 0 ]; then
    printf 'FAIL %s: the guard passed:\n%s\n' "$1" "$out"; fails=$((fails+1)); return
  fi
  if [ -n "${4:-}" ] && ! grep -Fq -- "$4" <<<"$out"; then
    printf 'FAIL %s: the output does not name %s:\n%s\n' "$1" "$4" "$out"; fails=$((fails+1)); return
  fi
  if [ -n "${5:-}" ] && ! grep -Fq -- "$5" <<<"$out"; then
    printf 'FAIL %s: the output does not name %s:\n%s\n' "$1" "$5" "$out"; fails=$((fails+1)); return
  fi
  printf 'ok   %s\n' "$1"
}

# -- the tree as it is, and the pinned range --------------------------------------------------------
fresh
expect "the files as they are pass" "$c" pass "Node floor holds"
if [ "$RANGE" = "$EXPECTED_RANGE" ]; then echo "ok   the starter's real range is the pinned one"
else printf 'FAIL the starter range is "%s", the test pins "%s": change EXPECTED_RANGE on purpose.\n' "$RANGE" "$EXPECTED_RANGE"; fails=$((fails+1)); fi

# -- scenarios 1 and 2: Astro raises a line (case 2 moves only the 24 line, so only it is refused) ---
fresh; jset "$c/$LOCK" "$ASTRO_ENG" "\">=$NEW22\""
expect "1 Astro raises its floor above the starter's: red, names Astro's range" "$c" fail "refuses" "\">=$NEW22\""
fresh; jset "$c/$LOCK" "$ASTRO_ENG" "\"^$V22 || ^$NEW24 || >=$V26\""
expect "2 Astro raises only the 24 line: red, names the 24 alternative" "$c" fail "alternative \"^$V24\""
out="$(bash "$c/scripts/check_node_floor.sh" 2>&1)"
if [ "$(grep -c 'which Astro' <<<"$out")" -eq 1 ]; then echo "ok   2 only the 24 alternative is flagged"
else printf 'FAIL 2 expected exactly one alternative flagged:\n%s\n' "$out"; fails=$((fails+1)); fi

# -- green G1 cases that reach the containment edges ----------------------------------------------
fresh; jset "$c/$LOCK" "$ASTRO_ENG" "\"$RANGE\""
expect "G1 Astro's range equal to the starter's: green" "$c" pass "Node floor holds"
fresh; jset "$c/$LOCK" "$ASTRO_ENG" "\"^$V22 || ^24.0.0 || >=26.0.0\""
expect "G1 Astro's range wider on 24 and 26 (a caret inside a caret, a lower open range): green" "$c" pass "Node floor holds"

# -- scenarios 3, 4, 6: the starter moves its floor ------------------------------------------------
fresh; set_engines "$c" "^$NEW22 || ^$V24 || >=$V26"
expect "3 engines moved, the docs still name $V22: red, names SETUP.md" "$c" fail "SETUP.md"
for f in "$README" "$SETUP" "$SKILL" "$UPG"; do tsub "$c/$f" "$V22" "$NEW22"; done
expect "4+6 engines stricter than Astro's on the 22 line, docs follow: green" "$c" pass "Node floor holds"
# the 24 line and the 26 line alone: the half of G3 that exists because Astro skips its own check there
fresh; set_engines "$c" "^$V22 || ^$NEW24 || >=$V26"
expect "3 engines moves only the 24 version, the docs do not: red, names SETUP.md and SKILL.md" "$c" fail "SETUP.md: says" "SKILL.md: says"
fresh; set_engines "$c" "^$V22 || ^$V24 || >=$NEW26"
expect "3 engines moves only the 26 version, the docs do not: red, names SETUP.md and SKILL.md" "$c" fail "SETUP.md: says" "SKILL.md: says"

# -- scenario 5: looser than Astro's ---------------------------------------------------------------
fresh; set_engines "$c" '>=22.12.0'
expect "5 engines looser than Astro's: red" "$c" fail "refuses"

# -- scenario 7: ranges it cannot read -------------------------------------------------------------
for r in '22.x' '~22.23' '20 || >=22'; do
  fresh; set_engines "$c" "$r"
  expect "7 engines \"$r\" is refused as unreadable" "$c" fail "cannot read this range"
done

# -- scenario 8: Astro's range spelled other ways ----------------------------------------------------
for r in ">= $V22" '>=22.23' '>=22'; do
  fresh; jset "$c/$LOCK" "$ASTRO_ENG" "\"$r\""
  expect "8 Astro's range spelled \"$r\" is read" "$c" pass "Node floor holds"
done

# -- scenarios 9 to 11, and files that are not what they should be ------------------------------------
fresh; jset "$c/$LOCK" '["packages","","engines","node"]' '">=22.12.0"'
expect "9 the lockfile root differs from package.json: red" "$c" fail "differs from package.json"
fresh; jset "$c/$LOCK" '["packages","node_modules/astro","engines"]' '__delete__'
expect "10 the astro entry has no engines: red, says so (not the next entry's)" "$c" fail "node_modules/astro entry has no engines.node"
fresh; jset "$c/$PKG" '["engines"]' '__delete__'
expect "11 package.json has no engines: red" "$c" fail "no engines.node"
fresh; printf 'null\n' >"$c/$PKG"
expect "11 package.json holding null: red, not a silent OK" "$c" fail "package.json: not a JSON object"
fresh; printf 'null\n' >"$c/$LOCK"
expect "11 the lockfile holding null: red, not a silent OK" "$c" fail "package-lock.json: not a JSON object"
fresh; printf '[]\n' >"$c/$PKG"
expect "11 package.json holding an array: red" "$c" fail "package.json: not a JSON object"

# -- scenario 12: files and phrases ------------------------------------------------------------------
fresh; rm "$c/$SETUP"
expect "12 a listed file is missing: red, names it" "$c" fail "SETUP.md: cannot read the file"
pairs="$README|the starter needs >=|the starter wants >=|the starter needs >=$V22 (Cloudflare Pages reads it)
$SETUP|current security fixes are in|current fixes are in|> current security fixes are in **$V22, $V24 and $V26**
$SKILL|This starter needs Node|This starter wants Node|**This starter needs Node ≥$V22**, and Node's current security fixes are in $V22, $V24 and $V26
$UPG|or newer on Node 24|or newer on Node 25|must be $V22 or newer on Node 22, $V24 or newer on Node 24, or $V26 or newer"
while IFS='|' read -r f from to dup; do
  fresh; tsub "$c/$f" "$from" "$to"
  expect "12 a phrase broken in ${f##*/}: red, names the file" "$c" fail "${f}: phrase not on one line, or missing"
  fresh; printf '\n%s\n' "$dup" >>"$c/$f"
  expect "12 a phrase doubled in ${f##*/}: red, names the file" "$c" fail "${f}: phrase found 2 times"
done <<<"$pairs"
fresh; tsub "$c/$SETUP" "**$V22, $V24 and $V26**" "**$V22,"$'\n'"> $V24 and $V26**"
expect "12 a blockquote rewrapped inside the phrase: red, \"not on one line\"" "$c" fail "SETUP.md: phrase not on one line"
fresh; tsub "$c/$SETUP" "> **Node ≥$V22 required**" "   >   **Node ≥$V22 required**"
expect "12 a blockquote marker and spaces before a phrase do not matter" "$c" pass "Node floor holds"

# -- scenarios 13 and 21: .nvmrc and the CI major --------------------------------------------------
fresh; printf '25\n' >"$c/$ASTRO/.nvmrc"
expect "13 .nvmrc says 25: red, no alternative admits it" "$c" fail "which no alternative"
for v in 'v24' 'lts/*'; do
  fresh; printf '%s\n' "$v" >"$c/$ASTRO/.nvmrc"
  expect "21 .nvmrc says \"$v\": red, cannot read" "$c" fail "cannot read the Node version"
done
fresh; tsub "$c/$ASTRO/.github/workflows/ci.yml" "node-version: 24" "node-version: 25"
expect "13 ci.yml node-version 25: red" "$c" fail "node-version is Node 25"
fresh; tsub "$c/$ASTRO/.github/workflows/ci.yml" "node-version: 24" "node-version: '24'"
expect "ci.yml node-version quoted '24' is read" "$c" pass "Node floor holds"

# -- G6: setup-node must ask for the latest release of the major (CI once ran 24.21.0 under ^24.22.1) ----
CL='          check-latest: true  # a cached older Node of that major is not enough: engines needs its security release'
fresh; tsub "$c/$ASTRO/.github/workflows/ci.yml" "$CL"$'\n' ""
expect "G6 ci.yml without check-latest: red, names the line" "$c" fail 'ci.yml:127: this setup-node step has no "check-latest: true"'
fresh; tsub "$c/$ASTRO/.github/workflows/ci.yml" "check-latest: true " "check-latest: false "
expect "G6 ci.yml check-latest: false: red" "$c" fail 'has no "check-latest: true"'
fresh; tsub "$c/$ASTRO/.github/workflows/ci.yml" "$CL"$'\n' ""
printf '      - run: echo later\n        env:\n          check-latest: true\n' >>"$c/$ASTRO/.github/workflows/ci.yml"
expect "G6 check-latest in a later step does not count for the setup-node step" "$c" fail 'has no "check-latest: true"'
fresh; tsub "$c/$ASTRO/.github/workflows/ci.yml" "      - uses: actions/setup-node@v7" "      - name: Node"$'\n'"        uses: actions/setup-node@v7"
expect "G6 a named setup-node step with check-latest: green" "$c" pass "asks setup-node for the latest release"

# -- scenario 14: an unlisted place is a known limit -------------------------------------------------
fresh; printf 'Node 22.12 or newer.\n' >"$c/docs/NEWDOC.md"
expect "14 a new doc states an old floor and is not in the table: green (a known limit)" "$c" pass "Node floor holds"

# -- scenarios 19 and 20, and G5's shape: the set of lines is pinned ----------------------------------
fresh; set_engines "$c" "^$V22 || ^$V24 || ^25.9.0 || >=$V26"
expect "19 engines gains ^25.9.0: red, 4 lines against 3 listed" "$c" fail "names 4 lines, the docs list 3"
fresh; set_engines "$c" "^$V22 || >=$V26"
expect "20 engines drops the 24 line: red" "$c" fail "names 2 lines, the docs list 3"
fresh; set_engines "$c" "^$V22 || ^$NEW22 || >=$V26"
expect "G5 engines names the 22 line twice: red" "$c" fail "names a Node line twice"
fresh; set_engines "$c" "^$V22 || >=$V24 || >=$V26"
expect "G5 a middle alternative widened from ^ to >=: red (it would admit 25), docs unchanged" "$c" fail "is open above but is not the highest"

# -- the range reader against npm's own semver ------------------------------------------------------
SEMVER="$(npm root -g 2>/dev/null)/npm/node_modules/semver"
if [ -f "$SEMVER/package.json" ]; then
  bad=0; checked=0
  cands="22.12.0 $(drop "$V22") $V22 22.99.99 23.0.0 23.11.0 24.0.0 $(drop "$V24") $V24 24.99.99 25.0.0 25.9.0 26.0.0 $(drop "$V26") $V26 27.0.0"
  for v in $cands; do
    want="$(node -e 'const s=require(process.argv[1]);console.log(s.satisfies(process.argv[2],process.argv[3])?"yes":"no")' "$SEMVER" "$v" "$RANGE")"
    got="$(bash "$ROOT/scripts/check_node_floor.sh" --admits "$RANGE" "$v")"
    checked=$((checked+1))
    [ "$want" = "$got" ] || { printf 'FAIL --admits "%s" for %s says %s, npm semver says %s\n' "$RANGE" "$v" "$got" "$want"; bad=1; }
  done
  # the edges that matter, stated and not only compared: each fixed version in, the patch below out,
  # the top of a caret in (X.99.99) and the next major out (X+1.0.0), the lines with no fixes out
  for pair in "$V22 yes" "$V24 yes" "$V26 yes" "$(drop "$V22") no" "$(drop "$V24") no" "$(drop "$V26") no" \
              "22.99.99 yes" "24.99.99 yes" "23.0.0 no" "25.0.0 no" "27.0.0 yes"; do
    set -- $pair
    got="$(bash "$ROOT/scripts/check_node_floor.sh" --admits "$RANGE" "$1")"
    [ "$got" = "$2" ] || { printf 'FAIL --admits "%s" for %s says %s, expected %s\n' "$RANGE" "$1" "$got" "$2"; bad=1; }
  done
  if [ "$bad" -eq 0 ]; then
    echo "ok   --admits agrees with npm's semver ($(node -e 'console.log(require(process.argv[1]+"/package.json").version)' "$SEMVER")) for $checked versions, edges included"
  else
    fails=$((fails+1))
  fi
else
  echo "SKIP: the range table (npm's bundled semver not found at $SEMVER)"; skips=$((skips+1))
fi

# -- one real npm run: an unmet engines warns and exits 0 --------------------------------------------
if command -v npm >/dev/null 2>&1; then
  fx="$T/npmfx"; mkdir "$fx" && mkdir "$T/home" && : >"$T/npmrc.user" && : >"$T/npmrc.global" \
    && printf '{ "name": "site", "version": "1.0.0", "private": true, "engines": { "node": ">=99.0.0" } }\n' >"$fx/package.json" \
    || { echo "FAIL — could not build the npm fixture."; exit 1; }
  out="$(cd "$fx" && HOME="$T/home" npm_config_cache="$T/npmcache" npm_config_userconfig="$T/npmrc.user" npm_config_globalconfig="$T/npmrc.global" \
         npm install --ignore-scripts --no-audit --no-fund --offline 2>&1)"; rc=$?
  if [ "$rc" -eq 0 ] && grep -Fq EBADENGINE <<<"$out" && grep -Fq "site@1.0.0" <<<"$out"; then
    echo "ok   real npm: an unmet engines prints EBADENGINE for the site's own package and exits 0"
  else
    printf 'FAIL real npm: exit %s, output:\n%s\n' "$rc" "$out"; fails=$((fails+1))
  fi
else
  echo "SKIP: the real npm run (npm not found)"; skips=$((skips+1))
fi

# -- the skip, and the skip turned into a failure ----------------------------------------------------
# The first call of each pair CLEARS REQUIRE_NODE_FLOOR: CI sets it for the whole job, and a probe that
# inherited it would exit 1 where it is meant to show the plain skip.
BASH_BIN="$(command -v bash)"
mkdir "$T/nonode" || { echo "FAIL — could not make the PATH without node."; exit 1; }
for t in bash dirname; do ln -s "$(command -v "$t")" "$T/nonode/$t" || { echo "FAIL — could not link $t."; exit 1; }; done
fresh
for s in "$c/scripts/check_node_floor.sh" "$ROOT/scripts/test_node_floor.sh"; do
  out="$(env -u REQUIRE_NODE_FLOOR PATH="$T/nonode" "$BASH_BIN" "$s" 2>&1)"; rc=$?
  if [ "$rc" -eq 0 ] && grep -Fq "SKIP" <<<"$out"; then echo "ok   no node: ${s##*/} prints SKIP and exits 0"
  else printf 'FAIL no node: %s exit %s:\n%s\n' "${s##*/}" "$rc" "$out"; fails=$((fails+1)); fi
  out="$(env REQUIRE_NODE_FLOOR=1 PATH="$T/nonode" "$BASH_BIN" "$s" 2>&1)"; rc=$?
  if [ "$rc" -eq 1 ] && grep -Fq "SKIP" <<<"$out"; then echo "ok   no node, REQUIRE_NODE_FLOOR=1: ${s##*/} exits 1"
  else printf 'FAIL no node with the variable: %s exit %s:\n%s\n' "${s##*/}" "$rc" "$out"; fails=$((fails+1)); fi
done

if [ "$skips" -gt 0 ] && [ "${REQUIRE_NODE_FLOOR:-}" = 1 ]; then
  echo "FAIL — REQUIRE_NODE_FLOOR=1: $skips case(s) skipped, and a skip counts as a failure."; fails=$((fails+skips))
fi
if [ "$fails" -gt 0 ]; then
  echo "test_node_floor.sh: $fails case(s) failed"; exit 1
elif [ "$skips" -gt 0 ]; then
  echo "test_node_floor.sh: every case that ran passed ($skips skipped)"
else
  echo "test_node_floor.sh: all cases passed"
fi
