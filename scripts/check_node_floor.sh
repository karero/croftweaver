#!/usr/bin/env bash
# Guard: the Node floor the starter states holds, and the places that state it agree.
#
# Why it exists: Astro raised its Node minimum twice in three releases (7.3.8: 22.12.0, 7.4.0: 22.22.0,
# 7.4.2: 22.23.4, the last time because of Node's October 2026 security releases). The starter states
# its floor in several places, a Dependabot bump changes none of them, and CI could not see the gap.
# Astro also skips its own Node check above Node 23, so a floor that follows Astro lets an older Node 24
# or 26 through. The plan is docs/reviews/SKILL-PLAN-node-floor-guard.md.
#
# It fails, and names the file, when any of these is false (skills/new-website/templates/astro is "the
# starter"; the range in its package.json "engines.node" is the source of truth):
#   G1  the starter's range admits no Node version that Astro's own range refuses. Astro's range is the
#       one its lockfile records for node_modules/astro (offline, read by key). A line may be stricter
#       than Astro's, never looser, so a bump that raises ANY line of Astro's range is caught.
#   G2  the lockfile's root engines.node (packages[""]) equals package.json's.
#   G3  six phrases in four shipped docs (the PHRASES table below) each appear exactly once, on ONE
#       line, and carry the versions package.json gives: the lowest, and the fixed version of each Node
#       line. The phrases are unanchored, so a blockquote's ">" or leading spaces do not matter, and the
#       check never joins lines: a rewrap that splits a phrase gives a red "phrase not on one line", on
#       purpose.
#   G4  the major in .nvmrc and in the starter's ci.yml node-version is one some alternative admits.
#   G5  the set of Node lines is pinned: one alternative per major, every one but the highest bounded to
#       its line with a caret (so ">=24.22.1" in the middle, which would admit 25, is red), and as many
#       alternatives as the SETUP.md and SKILL.md phrases list versions (LINE_COUNT). Adding "|| ^25.9.0"
#       or dropping the 24 alternative is red until the phrase table is changed on purpose.
#
# Ranges it reads: alternatives joined by "||", each ">=X[.Y[.Z]]" or "^X[.Y[.Z]]" (X at least 1), with
# optional spaces after the operator and around "||". Anything else ("22", "22.x", "~22.23") is refused
# with "cannot read this range": the check never passes on a range it did not understand.
#
# What it does not do: it reads only Astro's own range, so a transitive package's floor is not checked;
# it has no network, so it cannot know a newer Node security release (the maintainer's release routine
# compares engines with Node's index); and it does not look for places that state the floor and are not
# in the table (a scan for them was cut from the plan after two rounds of false positives; the release
# routine greps for each version in engines instead).
#
# Every file it reads ships in the handoff zip (CI runs make check inside it, with no git): nothing
# under the repo-root .github/, packages/ or docs/BUGLOG.md is read (the starter's own ci.yml, under
# skills/, is).
#
# Without node it prints one SKIP line and exits 0. With REQUIRE_NODE_FLOOR=1 (both CI jobs set it) it
# prints the same line and exits 1: a skip turned into a failure.
#
# --admits '<range>' <version> prints yes or no (exit 2 on a range it cannot read). It exists for
# scripts/test_node_floor.sh, which compares it with npm's own semver.
#
# Usage: bash scripts/check_node_floor.sh
set -uo pipefail
CDPATH= cd -- "$(dirname -- "$0")/.." || { echo "FAIL — cannot cd to the repo root from $0."; exit 1; }

if ! command -v node >/dev/null 2>&1; then
  echo "SKIP: check_node_floor.sh needs node (it reads JSON)"
  if [ "${REQUIRE_NODE_FLOOR:-}" = 1 ]; then
    echo "FAIL — REQUIRE_NODE_FLOOR=1: a skip counts as a failure."
    exit 1
  fi
  exit 0
fi

exec node - "$@" <<'JS'
'use strict';
const fs = require('fs');

const T = 'skills/new-website/templates';
const FILES = {
  pkg: T + '/astro/package.json',
  lock: T + '/astro/package-lock.json',
  nvmrc: T + '/astro/.nvmrc',
  ci: T + '/astro/.github/workflows/ci.yml',
};
// G3: one phrase per row. "use" says what the captures must equal: the lowest version of the starter's
// range, the fixed version of each line (ascending), or the lowest and then each line.
const PHRASES = [
  { file: T + '/astro/README.md', rx: /the starter needs >=([0-9.]+) \(Cloudflare Pages reads it\)/, use: 'lowest' },
  { file: T + '/astro/README.md', rx: /Requires \*\*Node ≥([0-9.]+)\*\*/, use: 'lowest' },
  { file: T + '/SETUP.md', rx: /\*\*Node ≥([0-9.]+) required\*\*/, use: 'lowest' },
  { file: T + '/SETUP.md', rx: /current security fixes are in \*\*([0-9.]+), ([0-9.]+) and ([0-9.]+)\*\*/, use: 'lines' },
  { file: 'skills/new-website/SKILL.md', rx: /This starter needs Node ≥([0-9.]+)\*\*, and Node's current security fixes are in ([0-9.]+), ([0-9.]+) and ([0-9.]+)/, use: 'lowest+lines' },
  { file: 'docs/UPGRADING.md', rx: /must be ([0-9.]+) or newer on Node 22, ([0-9.]+) or newer on Node 24, or ([0-9.]+) or newer/, use: 'lines' },
];
const LINE_COUNT = 3; // the versions the SETUP.md and SKILL.md phrases list: the 22, 24 and 26 lines

function cmp(a, b) {
  for (let i = 0; i < 3; i++) if (a[i] !== b[i]) return a[i] < b[i] ? -1 : 1;
  return 0;
}
function fmt(v) { return v.join('.'); }

function parseRange(text) {
  if (typeof text !== 'string') throw new Error('cannot read this range: not a string');
  const out = [];
  for (const raw of text.split('||')) {
    const alt = raw.trim();
    const m = /^(>=|\^)\s*([0-9]+)(?:\.([0-9]+))?(?:\.([0-9]+))?$/.exec(alt);
    if (!m) throw new Error('cannot read this range: "' + alt + '" in "' + text + '"');
    const lo = [Number(m[2]), Number(m[3] || 0), Number(m[4] || 0)];
    let hi = null;
    if (m[1] === '^') {
      if (lo[0] < 1) throw new Error('cannot read this range: a caret on 0.x in "' + text + '"');
      hi = [lo[0] + 1, 0, 0];
    }
    out.push({ lo: lo, hi: hi, text: alt });
  }
  return out;
}
function admits(ranges, v) {
  return ranges.some(function (r) { return cmp(v, r.lo) >= 0 && (r.hi === null || cmp(v, r.hi) < 0); });
}
function merged(ranges) {
  const s = ranges.map(function (r) { return { lo: r.lo, hi: r.hi }; }).sort(function (a, b) { return cmp(a.lo, b.lo); });
  const out = [];
  s.forEach(function (r) {
    const last = out[out.length - 1];
    if (last && (last.hi === null || cmp(r.lo, last.hi) <= 0)) {
      if (last.hi !== null && (r.hi === null || cmp(r.hi, last.hi) > 0)) last.hi = r.hi;
    } else {
      out.push({ lo: r.lo, hi: r.hi });
    }
  });
  return out;
}
// the alternatives of "inner" that "outer" does not wholly contain
function notContained(inner, outer) {
  const m = merged(outer);
  return inner.filter(function (s) {
    return !m.some(function (a) {
      return cmp(s.lo, a.lo) >= 0 && (a.hi === null || (s.hi !== null && cmp(s.hi, a.hi) <= 0));
    });
  });
}
function intersectsMajor(ranges, major) {
  const lo = [major, 0, 0], hi = [major + 1, 0, 0];
  return ranges.some(function (r) { return cmp(r.lo, hi) < 0 && (r.hi === null || cmp(r.hi, lo) > 0); });
}

const args = process.argv.slice(2);
if (args[0] === '--admits') {
  try {
    const r = parseRange(args[1]);
    const v = /^([0-9]+)\.([0-9]+)\.([0-9]+)$/.exec(args[2] || '');
    if (!v) throw new Error('cannot read this version: "' + args[2] + '"');
    console.log(admits(r, [Number(v[1]), Number(v[2]), Number(v[3])]) ? 'yes' : 'no');
    process.exit(0);
  } catch (e) {
    console.log(e.message);
    process.exit(2);
  }
}

const fails = [];
function fail(m) { fails.push(m); }
function readText(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch (e) { fail(p + ': cannot read the file (' + (e.code || e.message) + ')'); return null; }
}
function readJson(p) {
  const t = readText(p);
  if (t === null) return null;
  let d;
  try { d = JSON.parse(t); } catch (e) { fail(p + ': not valid JSON'); return null; }
  if (d === null || typeof d !== 'object' || Array.isArray(d)) { fail(p + ': not a JSON object'); return null; }
  return d;
}

const pkg = readJson(FILES.pkg);
const lock = readJson(FILES.lock);

let starterText = null, starter = null, astroText = null, astro = null, astroVersion = '?';
if (pkg) {
  starterText = pkg.engines && pkg.engines.node;
  if (typeof starterText !== 'string') {
    fail(FILES.pkg + ': no engines.node');
    starterText = null;
  } else {
    try { starter = parseRange(starterText); } catch (e) { fail(FILES.pkg + ': engines.node: ' + e.message); }
  }
}
if (lock) {
  const root = lock.packages && lock.packages[''];
  const rootText = root && root.engines && root.engines.node;
  if (typeof rootText !== 'string') {
    fail(FILES.lock + ': the root entry (packages[""]) has no engines.node');
  } else if (starterText !== null && rootText !== starterText) {
    fail(FILES.lock + ': root engines.node "' + rootText + '" differs from package.json "' + starterText + '" (G2): run npm install --package-lock-only in the starter folder');
  }
  const a = lock.packages && lock.packages['node_modules/astro'];
  if (!a) {
    fail(FILES.lock + ': no node_modules/astro entry');
  } else {
    astroVersion = a.version || '?';
    astroText = a.engines && a.engines.node;
    if (typeof astroText !== 'string') {
      fail(FILES.lock + ': the node_modules/astro entry has no engines.node (Astro ' + astroVersion + ')');
      astroText = null;
    } else {
      try { astro = parseRange(astroText); } catch (e) { fail(FILES.lock + ': astro engines.node: ' + e.message); }
    }
  }
}

// G1
if (starter && astro) {
  notContained(starter, astro).forEach(function (b) {
    fail(FILES.pkg + ': engines "' + starterText + '" admits Node from ' + fmt(b.lo) + ' (alternative "' + b.text + '") which Astro ' + astroVersion + ' refuses: its range is "' + astroText + '" (G1). Move the floor, then the docs in the phrase table.');
  });
}
// G5
if (starter) {
  const majors = starter.map(function (r) { return r.lo[0]; });
  if (new Set(majors).size !== majors.length) fail(FILES.pkg + ': engines names a Node line twice: "' + starterText + '" (G5)');
  starter.slice().sort(function (a, b) { return cmp(a.lo, b.lo); }).slice(0, -1).forEach(function (r) {
    if (r.hi === null) {
      fail(FILES.pkg + ': engines alternative "' + r.text + '" is open above but is not the highest; it admits lines the docs do not list (G5): bound it to its line with a caret');
    }
  });
  if (starter.length !== LINE_COUNT) {
    fail(FILES.pkg + ': engines names ' + starter.length + ' lines, the docs list ' + LINE_COUNT + ' (G5): change the phrase table in scripts/check_node_floor.sh on purpose');
  }
}
// G4
function checkMajor(file, label, value) {
  const m = /^["']?([0-9]+)["']?$/.exec(value);
  if (!m) { fail(file + ': cannot read ' + label + ' "' + value + '": expected a plain major such as 24 (G4)'); return; }
  if (starter && !intersectsMajor(starter, Number(m[1]))) {
    fail(file + ': ' + label + ' is Node ' + m[1] + ', which no alternative of engines "' + starterText + '" admits (G4)');
  }
}
{
  const nv = readText(FILES.nvmrc);
  if (nv !== null) checkMajor(FILES.nvmrc, 'the Node version', nv.split('\n')[0].trim());
  const ci = readText(FILES.ci);
  if (ci !== null) {
    const vals = [];
    ci.split('\n').forEach(function (line) {
      const m = /^\s*(?:-\s*)?node-version:\s*(.*?)\s*(?:#.*)?$/.exec(line);
      if (m) vals.push(m[1]);
    });
    if (vals.length === 0) fail(FILES.ci + ': no node-version line (G4)');
    vals.forEach(function (v) { checkMajor(FILES.ci, 'node-version', v); });
  }
}
// G3
const sorted = starter ? starter.slice().sort(function (a, b) { return cmp(a.lo, b.lo); }).map(function (r) { return fmt(r.lo); }) : null;
const textOf = {};
let phrasesOk = 0;
PHRASES.forEach(function (p) {
  if (!(p.file in textOf)) textOf[p.file] = readText(p.file);
  const text = textOf[p.file];
  if (text === null) return;
  const lines = text.split('\n');
  const hits = [];
  lines.forEach(function (l) {
    let rest = l, m;
    while ((m = p.rx.exec(rest)) !== null) {
      hits.push(m);
      rest = rest.slice(m.index + m[0].length);
    }
  });
  if (hits.length === 0) {
    fail(p.file + ': phrase not on one line, or missing (G3): /' + p.rx.source + '/');
    return;
  }
  if (hits.length > 1) {
    fail(p.file + ': phrase found ' + hits.length + ' times, expected once (G3): /' + p.rx.source + '/');
    return;
  }
  if (!sorted) return;
  const caps = hits[0].slice(1);
  const want = p.use === 'lowest' ? [sorted[0]] : p.use === 'lines' ? sorted : [sorted[0]].concat(sorted);
  if (caps.length !== want.length || caps.some(function (c, i) { return c !== want[i]; })) {
    fail(p.file + ': says ' + caps.join(', ') + ' where package.json engines "' + starterText + '" gives ' + want.join(', ') + ' (G3): /' + p.rx.source + '/');
  } else {
    phrasesOk++;
  }
});

if (!fails.length && (!starter || !astro || !sorted || phrasesOk !== PHRASES.length)) {
  fail('internal: the check did not reach every rule (starter ' + !!starter + ', astro ' + !!astro + ', phrases ' + phrasesOk + ' of ' + PHRASES.length + '); it will not say OK');
}
if (fails.length) {
  fails.forEach(function (f) { console.log('FAIL — ' + f); });
  process.exit(1);
}
console.log('OK — the starter\'s Node floor holds: engines "' + starterText + '" is inside Astro ' + astroVersion + '\'s "' + astroText + '", the lockfile root agrees, .nvmrc and ci.yml name an admitted major, and ' + phrasesOk + ' phrases in ' + Object.keys(textOf).length + ' files carry the same versions.');
JS
