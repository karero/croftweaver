#!/usr/bin/env bash
#
# test_mktemp_guard.sh — runs each script it lists, every one of which builds itself a
# throwaway folder and removes it on exit, with mktemp failing, from a folder holding a
# sentinel file. Each must stop at once with an error and leave that folder as it found it.
#
# Why it exists: these scripts made their folder with
#     T="$(mktemp -d …)"; trap 'rm -rf "$T"' EXIT; T="$(CDPATH= cd -- "$T" && pwd -P)"
# and never looked at mktemp's status. When mktemp failed (TMPDIR naming a folder that is
# missing or read-only, a full disk), T was empty and bash's `cd ""` stayed where it was. T
# became the folder the script was started in, the whole suite ran there and printed "all
# checks passed", and the EXIT trap deleted the folder. Under `make check` that folder is the
# repo. The scripts that did not reassign T ran on with it empty, so every "$T/…" path pointed
# at the filesystem root. These cases pin the repair: with mktemp failing, the script leaves the
# folder it ran from as it was (same files, the sentinel with the same checksum and length), ends
# with a non-zero status, and prints the message
# that says why as its last line. They do not prove it stopped AT that line: a guard that printed
# the message and then went on in silence to fail would pass. A script that goes on normally
# prints or errors, which puts something after the message.
#
# Which scripts: any shell script that mentions mktemp is in SCRIPTS (tested here) or in
# EXEMPT (with the reason it needs no case here). The completeness check below fails until a
# new one is in one or the other, the way check_cdpath_safe.sh does for CDPATH.
#
# mktemp fails through a stub first on PATH, not through a bad TMPDIR alone: macOS's mktemp
# with no template falls back to the user's temp folder when TMPDIR is bad, so the scripts
# that call it bare would only fail on Linux. TMPDIR names a missing folder as well, as in the
# incident. HOME moves too, so a script whose guard has broken cannot touch the real one.
#
# A listed script that skips (no git, node or python3 on the machine) is reported, and not
# counted as tested. REQUIRE_EVERY_SCRIPT=1 (CI) makes a skip a failure.
#
# Usage: bash scripts/test_mktemp_guard.sh
set -u

# Scripts that build a throwaway folder and remove it on exit. The first two deleted the folder
# they ran from; the rest ran on with the folder's name empty.
SCRIPTS=(
  scripts/test_whats_new.sh
  scripts/test_verify.sh
  scripts/check_cdpath_safe.sh
  scripts/test_clean_denylist.sh
  scripts/test_git_stand_hook.sh
  scripts/test_install_pin.sh
  scripts/test_package_leak.sh
  scripts/test_pre_push_hook.sh
  scripts/test_whats_new_removed_skill.sh
  skills/independent-review/scripts/check_prompt_sync.sh
  skills/independent-review/scripts/test_failed_tier_report.sh
  skills/independent-review/scripts/test_sweep_claims.sh
)
# Scripts that mention mktemp and have no case here: "path|reason".
EXEMPT=(
  "scripts/check_clean.sh|checks mktemp itself, and test_clean_denylist.sh pins it"
  "scripts/check_lf_checkout.sh|checks mktemp itself"
  "scripts/check_pipefail_pipes.sh|checks mktemp itself"
  "scripts/check_skill_budgets.sh|checks mktemp itself"
  "scripts/test_mktemp_guard.sh|this file: with its own guard broken it would run itself without end"
  "skills/independent-review/scripts/check_perl_minimum.sh|checks mktemp itself"
  "skills/independent-review/scripts/merge_link.sh|set -e ends it on a failed mktemp"
  "skills/independent-review/scripts/independent_review.sh|run_agy does not check mktemp (docs/BUGLOG.md)"
  "skills/new-website/templates/astro/scripts/check_internal_links.sh|a site template that makes files, not a folder, and does not check mktemp (docs/BUGLOG.md)"
  "skills/new-website/templates/astro/scripts/ship.sh|set -e ends it on a failed mktemp"
  "skills/new-website/templates/astro/tests/check_analytics_gate.sh|set -e ends it on a failed mktemp"
  "skills/new-website/templates/astro/tests/check_ship_push.sh|set -e ends it on a failed mktemp"
)

HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(dirname -- "$HERE")"
T="$(mktemp -d "${TMPDIR:-/tmp}/mktemp-guard-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
mkdir "$T/stub" \
  && printf '#!/bin/sh\necho "mktemp: stub: cannot create a temp file or folder" >&2\nexit 1\n' >"$T/stub/mktemp" \
  && chmod +x "$T/stub/mktemp" \
  && echo keep >"$T/sentinel.orig" \
  || { echo "FAIL — could not build the failing mktemp."; exit 1; }
# Where timeout exists (not on a stock Mac) it ends a script whose guard has broken and that
# then hangs. One that merely runs on finishes as it does under make check.
TO=""; command -v timeout >/dev/null 2>&1 && TO="timeout 120"
fails=0; skipped=0; n=0
fail() { printf 'FAIL %s\n' "$1"; fails=$((fails+1)); }

# probe <script> — runs it from a folder holding one file, "sentinel", with mktemp failing.
# Sets p_rc (its exit status), p_out (what it printed), p_left (the names the folder holds
# afterwards; empty if the folder is gone) and p_same (yes if the sentinel has the checksum and
# length it had; cksum sees every byte, a NUL and a trailing newline included, which $(cat …)
# would drop).
probe() {
  local d="$T/run.$n"; n=$((n+1))
  mkdir "$d" && cp "$T/sentinel.orig" "$d/sentinel" || { echo "FAIL — could not set up $d."; exit 1; }
  p_out="$(cd "$d" && HOME="$T/home" PATH="$T/stub:$PATH" TMPDIR="$T/missing" $TO bash "$1" 2>&1 </dev/null)"; p_rc=$?
  p_left="$(ls -A "$d" 2>/dev/null)"
  if [ "$(cksum <"$T/sentinel.orig")" = "$({ cksum <"$d/sentinel"; } 2>/dev/null)" ]; then p_same=yes; else p_same=no; fi
}

# why_wrong — empty when the last probe went right, otherwise what went wrong. The message must
# be the LAST thing printed: a guard that says it and then goes on has not stopped the script.
why_wrong() {
  if [ -z "$p_left" ]; then
    echo "it deleted the folder it ran from, sentinel and all"
  elif [ "$p_left" != sentinel ]; then
    echo "it left [$(printf '%s' "$p_left" | tr '\n' ' ')] in the folder it ran from, not just the sentinel"
  elif [ "$p_same" != yes ]; then
    echo "it changed the sentinel"
  elif [ "$p_rc" -eq 0 ]; then
    echo "exited 0"
  else
    case "${p_out##*$'\n'}" in
      *"could not create a temp dir"*) ;;
      *) echo "exited $p_rc, but its last line is not 'could not create a temp dir': it said nothing, or went on" ;;
    esac
  fi
}

# Self-test: each way a script can go wrong must be caught, or that arm of why_wrong could
# vanish and nothing here would fail. catch <what> <phrase> <script>: the probe of <script>
# must go wrong, and why_wrong must say <phrase>.
catch() {
  probe "$3"
  why="$(why_wrong)"
  case "$why" in
    *"$2"*) echo "ok   self-test: caught: $1" ;;
    *) fail "self-test: $1 was not caught as '$2' (why_wrong said: ${why:-nothing})" ;;
  esac
}
mkdir "$T/fx" || { echo "FAIL — could not make the fixture folder."; exit 1; }
cat >"$T/fx/old.sh" <<'FX'
T="$(mktemp -d "${TMPDIR:-/tmp}/old.XXXXXX")"
trap 'rm -rf "$T"' EXIT
T="$(CDPATH= cd -- "$T" && pwd -P)"
echo "all checks passed"
FX
printf 'echo "all checks passed"\n' >"$T/fx/runs-on.sh"
printf 'exit 1\n' >"$T/fx/silent.sh"
printf 'echo "FAIL — could not create a temp dir."\n: >stray\nexit 1\n' >"$T/fx/litters.sh"
printf 'echo "FAIL — could not create a temp dir."\necho changed >sentinel\nexit 1\n' >"$T/fx/rewrites.sh"
printf 'echo "FAIL — could not create a temp dir."\necho >>sentinel\nexit 1\n' >"$T/fx/appends.sh"
printf 'echo "FAIL — could not create a temp dir."\nprintf "\\000" >>sentinel\nexit 1\n' >"$T/fx/nul.sh"
printf 'echo "FAIL — could not create a temp dir."\necho "and on it went"\nexit 1\n' >"$T/fx/goes-on.sh"
catch "the old three lines"                    "deleted the folder"     "$T/fx/old.sh"
catch "a script that runs on and exits 0"      "exited 0"               "$T/fx/runs-on.sh"
catch "a script that exits without a word"     "last line"              "$T/fx/silent.sh"
catch "a script that goes on after its message" "last line"             "$T/fx/goes-on.sh"
catch "a script that leaves a file behind"     "not just the sentinel"  "$T/fx/litters.sh"
catch "a script that rewrites the sentinel"    "changed the sentinel"   "$T/fx/rewrites.sh"
catch "a script that adds a newline to it"     "changed the sentinel"   "$T/fx/appends.sh"
catch "a script that adds a NUL byte to it"    "changed the sentinel"   "$T/fx/nul.sh"

# Completeness: every shell script that mentions mktemp is in SCRIPTS or EXEMPT, so a new one
# forces a choice instead of going untested. list_shell_scripts.sh finds the scripts (by
# shebang, from git's list or, in an unzipped copy, with find). The pattern wants the word
# mktemp, not those letters in a file name: package.sh lists this very test.
all="$(bash "$ROOT/scripts/list_shell_scripts.sh")" || { printf '%s\n' "$all"; exit 1; }
exempt_paths="$(for e in "${EXEMPT[@]}"; do printf '%s\n' "${e%%|*}"; done)"
listed="$(printf '%s\n' "${SCRIPTS[@]}" "$exempt_paths" | sort)"
users="$(while IFS= read -r f; do grep -q -E '(^|[^[:alnum:]_./-])mktemp($|[^[:alnum:]_.-])' "$ROOT/$f" && printf '%s\n' "$f"; done <<<"$all" | sort)"
unlisted="$(comm -23 <(printf '%s\n' "$users") <(printf '%s\n' "$listed"))"
stale="$(comm -13 <(printf '%s\n' "$users") <(printf '%s\n' "$listed"))"
if [ -n "$unlisted" ]; then
  fail "these shell scripts mention mktemp but are in neither SCRIPTS nor EXEMPT in $0:"
  printf '%s\n' "$unlisted" | sed 's/^/    /'
  echo "    Add each to SCRIPTS (it builds a throwaway folder and removes it on exit), or to EXEMPT with the reason it needs no case."
fi
if [ -n "$stale" ]; then
  fail "these are listed in $0 but no longer exist, or no longer mention mktemp:"
  printf '%s\n' "$stale" | sed 's/^/    /'
fi
[ -z "$unlisted$stale" ] && echo "ok   every shell script that mentions mktemp is in SCRIPTS or EXEMPT"

for s in "${SCRIPTS[@]}"; do
  [ -f "$ROOT/$s" ] || { fail "$s: no such script (is this list stale?)"; continue; }
  probe "$ROOT/$s"
  case "$p_out" in
    SKIP*) if [ "$p_rc" -eq 0 ]; then
             skipped=$((skipped+1))
             printf 'skip %s: %s\n' "$s" "$(printf '%s\n' "$p_out" | sed -n 1p)"
             continue
           fi ;;
  esac
  why="$(why_wrong)"
  if [ -z "$why" ]; then
    printf 'ok   %s: stops with an error and leaves its folder alone\n' "$s"
  else
    fail "$s: $why"
  fi
done

if [ "$skipped" -gt 0 ] && [ "${REQUIRE_EVERY_SCRIPT:-}" = 1 ]; then
  fail "$skipped script(s) skipped and REQUIRE_EVERY_SCRIPT=1: install what they need (git, node, python3)"
fi
if [ $fails -ne 0 ]; then echo "$fails check(s) FAILED"; exit 1; fi
if [ "$skipped" -gt 0 ]; then
  echo "all checks passed, but $skipped of ${#SCRIPTS[@]} scripts were skipped and so not tested"
else
  echo "all checks passed"
fi
