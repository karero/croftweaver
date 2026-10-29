#!/usr/bin/env bash
# Guard: every file under skills/new-website/templates/ (the astro overlay, the root
# templates beside it and templates/claude/) must be accounted for in exactly one
# bucket — TEMPLATE_TRACKED (drift-tracked via TESTS-VERSION), SITE_OWNED
# (deliberately not tracked — sites hand-edit it), or SITE_SOURCE (below — becomes the
# site's own application content at scaffold time, or never ships to a site at all).
# TEMPLATE_TRACKED and SITE_OWNED are extracted straight out of scripts/whats-new.sh
# rather than duplicated here, so this guard can never itself drift from the list it's
# checking — that duplication is exactly the bug class PR #87 exposed (a hand-maintained
# list one file at a time silently missing a new template file).
set -uo pipefail
CDPATH= cd -- "$(dirname -- "$0")/.."

WN="scripts/whats-new.sh"
TEMPLATES_DIR="skills/new-website/templates"
TEMPLATE_ASTRO_DIR="$TEMPLATES_DIR/astro"

[ -f "$WN" ] || { echo "FAIL — $WN not found; can't extract TEMPLATE_TRACKED/SITE_OWNED."; exit 1; }

# grep is tri-state: 0 = matches (both lines found), 1 = no match, >1 = error. An I/O
# error must not fall through and read as "extraction succeeded with nothing".
extracted="$(grep -E '^(TEMPLATE_TRACKED|SITE_OWNED)=' "$WN")"
rc=$?
if [ "$rc" -gt 1 ]; then
  echo "FAIL — grep errored (exit $rc) extracting TEMPLATE_TRACKED/SITE_OWNED from $WN;"
  echo "the guard result is unreliable."
  exit 1
fi
if [ "$rc" -eq 1 ] || [ -z "$extracted" ]; then
  echo "FAIL — could not find TEMPLATE_TRACKED=/SITE_OWNED= assignments in $WN"
  echo "(renamed, removed, or reformatted?). Update this guard to match."
  exit 1
fi
# Exactly one assignment each, or a later duplicate would silently win the eval below
# and weaken coverage with no signal that it happened.
tt_count="$(grep -c -E '^TEMPLATE_TRACKED=' "$WN")"
so_count="$(grep -c -E '^SITE_OWNED=' "$WN")"
if [ "$tt_count" -ne 1 ] || [ "$so_count" -ne 1 ]; then
  echo "FAIL — expected exactly one TEMPLATE_TRACKED= and one SITE_OWNED= assignment in"
  echo "$WN, found $tt_count and $so_count. Remove the duplicate(s) before trusting the scan."
  exit 1
fi
# The two lines are static, single-quoted string literals we author ourselves in this
# same repo (not attacker-controlled input) — eval just assigns them into this shell.
eval "$extracted"
if [ -z "${TEMPLATE_TRACKED:-}" ] || [ -z "${SITE_OWNED:-}" ]; then
  echo "FAIL — TEMPLATE_TRACKED or SITE_OWNED came back empty after extraction from $WN."
  echo "Update this guard to match."
  exit 1
fi

# Files that become the site's own application source the moment they're scaffolded
# (src/** — pages/components/config the site owner writes and rewrites as its actual
# content — plus the npm-managed lockfile and the generated/placeholder public/ assets
# below) — or, for README.md, scaffold-time reference documentation for whoever runs
# the new-website skill that is never copied into a site at all (SKILL.md §3 step 1
# points at it for "exact steps", it doesn't cp it). Either way, diffing these against
# upstream carries no actionable drift signal, so — like SITE_OWNED — they're
# deliberately excluded from TEMPLATE_TRACKED. Same "no runtime behavior" note as
# SITE_OWNED: nothing in whats-new.sh reads this; only this guard does.
#
# The six infra/tooling files once parked here alongside these (.nvmrc,
# build-marker.mjs, generate_og_cards.py, hooks/pre-push, set_pdf_title.py, ship.sh)
# were a deliberate, reviewed decision, not an oversight: five were promoted to
# TEMPLATE_TRACKED and generate_og_cards.py moved to SITE_OWNED — see whats-new.sh's
# TEMPLATE_TRACKED/SITE_OWNED comments for the reasoning.
SITE_SOURCE="$TEMPLATE_ASTRO_DIR/src $TEMPLATE_ASTRO_DIR/package-lock.json $TEMPLATE_ASTRO_DIR/public/llms.txt $TEMPLATE_ASTRO_DIR/public/manifest.webmanifest $TEMPLATE_ASTRO_DIR/public/robots.txt $TEMPLATE_ASTRO_DIR/public/images $TEMPLATE_ASTRO_DIR/README.md"

in_bucket() {  # $1 = file path, $2 = space-separated bucket entries (files or dir prefixes)
  local f="$1" list="$2" entry
  for entry in $list; do
    [ "$f" = "$entry" ] && return 0
    case "$f" in
      "$entry"/*) return 0 ;;
    esac
  done
  return 1
}

# $1 = path, $2 = the literal text a case arm for it must START WITH (after stripping
# leading whitespace) — "$path)" for a single file, "$path/*)" for a directory wildcard.
# Anchoring to line-start (not a bare substring grep) means a mention inside a comment
# or an echoed diagnostic string can't be mistaken for an active case arm.
has_case_arm() {
  local path="$1" want="$2" line trimmed
  while IFS= read -r line; do
    trimmed="${line#"${line%%[![:space:]]*}"}"
    case "$trimmed" in
      "$want"*) return 0 ;;
    esac
  done < "$WN"
  return 1
}

# Self-test, both directions. A completeness guard that has never fired is a
# hypothesis, not a guard — and one that flags files it shouldn't is its mirror image.
if ! in_bucket "$TEMPLATE_ASTRO_DIR/tests/some_new_spec.spec.ts" "$TEMPLATE_TRACKED"; then
  echo "FAIL — self-test: in_bucket misses a real tests/ directory entry. Fix the matcher"
  echo "before trusting the scan."
  exit 1
fi
if ! in_bucket "$TEMPLATE_ASTRO_DIR/package.json" "$SITE_OWNED"; then
  echo "FAIL — self-test: in_bucket misses a real SITE_OWNED entry. Fix the matcher before"
  echo "trusting the scan."
  exit 1
fi
# A root template must not count as covered by the astro/ entries beside it.
if in_bucket "$TEMPLATES_DIR/astro" "$TEMPLATE_TRACKED $SITE_OWNED $SITE_SOURCE" \
   || in_bucket "$TEMPLATES_DIR/new-root-file.md" "$TEMPLATE_TRACKED $SITE_OWNED $SITE_SOURCE"; then
  echo "FAIL — self-test: in_bucket matched a root template path that no bucket names."
  echo "Fix the matcher before trusting the scan."
  exit 1
fi
if in_bucket "$TEMPLATE_ASTRO_DIR/definitely-not-a-real-file.txt" "$TEMPLATE_TRACKED $SITE_OWNED $SITE_SOURCE"; then
  echo "FAIL — self-test: in_bucket matched a file that is in none of the bucket lists."
  echo "Fix the matcher before trusting the scan."
  exit 1
fi
# Same both-directions check for the two reverse-validation primitives below: existence
# testing and the process_tests_stamp mapping-arm lookup.
if [ ! -e "$WN" ]; then
  echo "FAIL — self-test: [ -e ] misses a file that definitely exists ($WN). Fix before trusting the scan."
  exit 1
fi
if [ -e "$TEMPLATE_ASTRO_DIR/definitely-not-a-real-file.txt" ]; then
  echo "FAIL — self-test: [ -e ] matched a path that doesn't exist. Fix before trusting the scan."
  exit 1
fi
if ! has_case_arm "skills/new-website/templates/astro/playwright.config.ts" \
     "skills/new-website/templates/astro/playwright.config.ts)"; then
  echo "FAIL — self-test: has_case_arm misses a case arm that definitely exists"
  echo "(playwright.config.ts). Fix before trusting the scan."
  exit 1
fi
if has_case_arm "skills/new-website/templates/astro/definitely-not-a-real-file.txt" \
     "skills/new-website/templates/astro/definitely-not-a-real-file.txt)"; then
  echo "FAIL — self-test: has_case_arm matched a case arm that doesn't exist. Fix before"
  echo "trusting the scan."
  exit 1
fi
if ! has_case_arm "skills/new-website/templates/astro/tests" \
     "skills/new-website/templates/astro/tests/*)"; then
  echo "FAIL — self-test: has_case_arm misses the tests/ directory wildcard arm that"
  echo "definitely exists. Fix before trusting the scan."
  exit 1
fi

[ -d "$TEMPLATE_ASTRO_DIR" ] || { echo "FAIL — $TEMPLATE_ASTRO_DIR does not exist; the template moved."; exit 1; }
[ -d "$TEMPLATES_DIR/claude" ] || { echo "FAIL — $TEMPLATES_DIR/claude does not exist; the template moved."; exit 1; }

# Reverse validation — coverage is otherwise only one-way (every discovered file must
# hit a bucket), which would silently let a stale/misspelled bucket entry (pointing at
# nothing) or a TEMPLATE_TRACKED file with no process_tests_stamp switch-case arm sit
# there indefinitely. A tracked file with no matching case falls through to that
# switch's `*)` default, which prints the raw repo path instead of the site's actual
# in-site path — the exact "silently wrong, not silently missing" mirror of the bug
# this guard exists to catch.
stale_entries=()
for entry in $TEMPLATE_TRACKED $SITE_OWNED $SITE_SOURCE; do
  [ -e "$entry" ] || stale_entries+=("$entry")
done
missing_mapping=()
for entry in $TEMPLATE_TRACKED; do
  if [ -d "$entry" ]; then
    has_case_arm "$entry" "$entry/*)" || missing_mapping+=("$entry/* (directory wildcard arm)")
  else
    has_case_arm "$entry" "$entry)" || missing_mapping+=("$entry")
  fi
done
if [ "${#stale_entries[@]}" -gt 0 ]; then
  echo "FAIL — ${#stale_entries[@]} bucket entry/entries point at a path that no longer exists:"
  printf '    %s\n' "${stale_entries[@]}"
  echo "Remove or fix the entry in $WN (TEMPLATE_TRACKED/SITE_OWNED) or this script (SITE_SOURCE)."
  exit 1
fi
if [ "${#missing_mapping[@]}" -gt 0 ]; then
  echo "FAIL — ${#missing_mapping[@]} TEMPLATE_TRACKED file(s) have no process_tests_stamp"
  echo "switch-case arm in $WN, so a drift report would fall through to its default case"
  echo "and print the raw repo path instead of the site's in-site path:"
  printf '    %s\n' "${missing_mapping[@]}"
  echo "Add a case arm for each, mapping it to the site's actual copy path."
  exit 1
fi

# Discover files, never hardcode a list — that's the whole point of this guard.
# Symlinks count too (-o -type l): a symlink dropped under the template with no real
# bucket entry would otherwise pass silently, defeating the "every file" invariant.
# Captured via command substitution (not process substitution) so find's own exit
# status is checkable via PIPESTATUS — a mid-scan find error must not leave FILES
# looking like a complete, trustworthy listing.
find_output="$(find "$TEMPLATES_DIR" \( -type f -o -type l \) ! -name .DS_Store | sort)"
find_rc="${PIPESTATUS[0]}"
if [ "$find_rc" -ne 0 ]; then
  echo "FAIL — find exited $find_rc scanning $TEMPLATES_DIR; the file listing is unreliable."
  exit 1
fi
FILES=()
while IFS= read -r f; do [ -n "$f" ] && FILES+=("$f"); done <<< "$find_output"
if [ "${#FILES[@]}" -lt 1 ]; then
  echo "FAIL — no files found under $TEMPLATES_DIR; find/path broke or the dir moved."
  exit 1
fi

unaccounted=()
ambiguous=()
for f in "${FILES[@]}"; do
  hits=0
  in_bucket "$f" "$TEMPLATE_TRACKED" && hits=$((hits + 1))
  in_bucket "$f" "$SITE_OWNED" && hits=$((hits + 1))
  in_bucket "$f" "$SITE_SOURCE" && hits=$((hits + 1))
  if [ "$hits" -eq 0 ]; then
    unaccounted+=("$f")
  elif [ "$hits" -gt 1 ]; then
    ambiguous+=("$f")
  fi
done

fail=0
if [ "${#unaccounted[@]}" -gt 0 ]; then
  fail=1
  echo "FAIL — ${#unaccounted[@]} file(s) under $TEMPLATES_DIR are in no bucket:"
  printf '    %s\n' "${unaccounted[@]}"
  echo "Pick one: add it to TEMPLATE_TRACKED or SITE_OWNED in $WN (with its in-site path"
  echo "mapping in process_tests_stamp's switch, per TEMPLATE_TRACKED, if you add it there),"
  echo "or to SITE_SOURCE in this script."
fi
if [ "${#ambiguous[@]}" -gt 0 ]; then
  fail=1
  echo "FAIL — ${#ambiguous[@]} file(s) under $TEMPLATES_DIR are in more than one bucket:"
  printf '    %s\n' "${ambiguous[@]}"
  echo "Each file must be in exactly one of TEMPLATE_TRACKED, SITE_OWNED, SITE_SOURCE."
fi

# The starter's licence notice must be the toolkit's LICENSE, byte for byte: check_clean.sh
# skips the copyright holder's name in it only while that holds, and a drifted copy would
# give every new site a wrong notice. Compared, not parsed.
LICENSE_COPY="$TEMPLATE_ASTRO_DIR/CROFTWEAVER-LICENSE.md"
for need in LICENSE "$LICENSE_COPY"; do
  if [ ! -f "$need" ]; then
    fail=1
    echo "FAIL — $need is missing; the starter's licence notice is a copy of LICENSE."
  fi
done
if [ -f LICENSE ] && [ -f "$LICENSE_COPY" ] && ! cmp -s LICENSE "$LICENSE_COPY"; then
  fail=1
  echo "FAIL — $LICENSE_COPY differs from LICENSE. It must be an exact copy:"
  echo "    cp LICENSE $LICENSE_COPY"
fi

if [ "$fail" -ne 0 ]; then
  exit 1
fi
echo "OK — all ${#FILES[@]} files under $TEMPLATES_DIR are accounted for (TEMPLATE_TRACKED, SITE_OWNED, or SITE_SOURCE)."
