#!/usr/bin/env bash
# Guard: an exported CDPATH must not change what any script does.
#
# `cd "$(dirname "$0")"` is wrong when CDPATH is exported: cd searches CDPATH before the
# current directory for a relative operand, so it can land elsewhere — and it prints where it
# went, corrupting any $(...) capturing it. Both modes were live here until 2026-09-26:
# `CDPATH=/tmp/cdp make check` exited 2, and whats-new.sh resolved a relative <project_dir>
# to a same-named decoy that --refresh would then have written into.
#
# Why a guard: nothing else in this repo sets CDPATH, so a green `make check` looks identical
# whether the scripts are safe or not — the same reason check_template_coverage.sh exists.
#
# Why BEHAVIOURAL, not a grep. The first version of this guard scanned for the textual idiom.
# A review round drove a truck through it: pushd, `SELF=$(dirname "$0"); cd "$SELF"`,
# `cd "${0%/*}"`, backticks, a space after `$(`, a backslash continuation and a second cd on
# the same line all evaded it; `CDPATH=""` and `unset CDPATH` produced false FAILs; it never
# covered the caller-supplied `cd "$PROJECT"` that was the original bug; and a *.sh glob could
# not see extensionless scripts. Running each subject twice and comparing has none of those
# holes, because it tests behaviour instead of spelling.
#
# The comparison is between the two RUNS, deliberately not against a known-good result: a
# subject that fails for its own unrelated reason fails identically both times and is not this
# guard's business. That keeps a leaked model name (say) from also turning this job red.
set -uo pipefail
CDPATH= cd -- "$(dirname -- "$0")/.." || { echo "FAIL — cannot cd to the repo root from $0."; exit 1; }

# Subjects: run twice and diff. Every one is read-only and quick. Invoked by a RELATIVE path,
# which is what makes CDPATH reachable at all.
SUBJECTS=(
  scripts/check_clean.sh
  scripts/check_model_agnostic.sh
  scripts/check_template_coverage.sh
  scripts/check_skill_budgets.sh
  scripts/check_pipefail_pipes.sh
  scripts/check_lf_checkout.sh
  scripts/list_shell_scripts.sh
  scripts/whats-new.sh
  skills/independent-review/scripts/check_prompt_sync.sh
  skills/independent-review/scripts/check_perl_minimum.sh
  skills/independent-review/scripts/sweep_claims.sh
)
# Not run here, each for a reason — not because nobody got to them. The completeness check
# below forces a new script into one list or the other, the same way check_template_coverage.sh
# forces a new template file into a bucket.
NOT_RUN=(
  scripts/install.sh                                            # writes symlinks into ~/.claude/skills
  scripts/install-codex.sh                                      # writes symlinks into ~/.agents/skills
  scripts/package.sh                                            # builds dist/, and runs check itself
  scripts/test_install_pin.sh                                   # builds throwaway repos; needs git
  scripts/test_whats_new_removed_skill.sh                       # builds a throwaway suite and sites; needs git
  scripts/test_package_leak.sh                                  # runs package.sh in a throwaway dir with stub zip/unzip
  scripts/test_pre_push_hook.sh                                 # builds a throwaway repo; needs git
  scripts/test_verify.sh                                        # builds a throwaway site with a stub npm; needs node
  scripts/test_clean_denylist.sh                                # builds a throwaway repo and worktree; needs git
  scripts/test_git_stand_hook.sh                                # builds throwaway repos; needs git and node
  scripts/test_whats_new.sh                                     # builds a throwaway suite repo and site; needs git
  scripts/test_mktemp_guard.sh                                  # runs other scripts with mktemp stubbed to fail
  scripts/check_cdpath_safe.sh                                  # this file
  skills/independent-review/scripts/independent_review.sh       # calls external reviewers, costs money
  skills/independent-review/scripts/review_log.sh               # appends to the owner's cost log; never locates itself
  skills/independent-review/scripts/merge_link.sh               # needs a repo and three revisions; never locates itself
  skills/independent-review/scripts/test_failed_tier_report.sh  # slow; stubs a whole CLI
  skills/independent-review/scripts/test_looks_like_review.sh   # slow; stubs a whole CLI
  skills/independent-review/scripts/test_sweep_claims.sh        # builds throwaway repos; needs git and python3
  skills/new-website/templates/astro/tests/check_ship_push.sh   # template test; needs a built site
  skills/new-website/templates/astro/tests/check_analytics_gate.sh # template test; needs npm ci, builds the site four times
  skills/new-website/templates/astro/scripts/hooks/pre-push     # git hook; expects a push context
  skills/new-website/templates/astro/scripts/ship.sh            # template: pushes a site live
  skills/new-website/templates/astro/scripts/check_external_links.sh # template: needs a built site + network
  skills/new-website/templates/astro/scripts/check_internal_links.sh # template: needs a built site
  skills/search-console-insights/scripts/track.sh               # network + OAuth
  skills/search-console-insights/scripts/schedule_tracking.sh   # writes a launchd job
)

rc=0

# Completeness: every shell script must sit in exactly one list, so a new one forces a
# deliberate choice instead of being silently uncovered. list_shell_scripts.sh finds them (by
# shebang, skipping nested checkouts; the reasons are there).
all_scripts="$(bash scripts/list_shell_scripts.sh)" || { printf '%s\n' "$all_scripts"; exit 1; }
listed="$(printf '%s\n' "${SUBJECTS[@]}" "${NOT_RUN[@]}" | sort)"
unlisted="$(comm -23 <(printf '%s\n' "$all_scripts") <(printf '%s\n' "$listed"))"
stale="$(comm -13 <(printf '%s\n' "$all_scripts") <(printf '%s\n' "$listed"))"
if [ -n "$unlisted" ]; then
  echo "FAIL — these shell scripts are in neither SUBJECTS nor NOT_RUN in $0:"
  printf '%s\n' "$unlisted" | sed 's/^/    /'
  echo "Add each to SUBJECTS (run twice, compare) or to NOT_RUN with the reason it cannot be run."
  rc=1
fi
if [ -n "$stale" ]; then
  echo "FAIL — these are listed in $0 but no longer exist (or lost their shebang):"
  printf '%s\n' "$stale" | sed 's/^/    /'
  rc=1
fi

# --- behavioural case: CDPATH must change nothing --------------------------------------------
# One folder holds both: a second mktemp would be a second status to check and a second folder
# to clean up when it fails.
tmp="$(mktemp -d)" || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$tmp"' EXIT
decoy="$tmp/decoy" proj="$tmp/proj"
# The decoy must contain the first path segment of each subject, or cd never resolves into it.
mkdir -p "$decoy/scripts" "$decoy/skills/independent-review/scripts"

# whats-new.sh compares git history, so it cannot run in an unpacked handoff zip. A zip
# unpacked inside some other repository still answers `git rev-parse`, so ask whether the
# suite root IS the toplevel (an empty --show-prefix), the question whats-new.sh asks too.
not_a_clone() {
  ! command -v git >/dev/null 2>&1 ||
  [ "$(git rev-parse --is-inside-work-tree 2>/dev/null)" != true ] ||
  [ -n "$(git rev-parse --show-prefix 2>/dev/null)" ]
}

diffs=0; skipped=0
for s in "${SUBJECTS[@]}"; do
  [ -f "$s" ] || { echo "FAIL — subject $s does not exist."; rc=1; continue; }
  # Outside a clone whats-new.sh can only exit 1 with nothing on stdout, which the check
  # below would call a FAIL: `make check` in the handoff zip failed on it (found 2026-09-27,
  # already true of the v0.27 zip). Skip it loudly instead, like the regression case below.
  if [ "$s" = scripts/whats-new.sh ] && not_a_clone; then
    echo "SKIP — $s needs a git clone of the suite (it compares suite history)."
    skipped=$((skipped + 1)); continue
  fi
  # STDOUT and exit status only, deliberately NOT stderr. A CDPATH-resolved cd prints the
  # directory it went to on STDOUT, and a wrong directory changes stdout or the exit status, so
  # stdout+status is the whole signal. stderr is not deterministic: GitHub's runner starts jobs
  # with SIGPIPE ignored, so a pipeline whose consumer exits early makes the upstream grep print
  # "write error: Broken pipe" at random. The racer was check_prompt_sync.sh's tier check, a
  # `grep -v | grep -q` (its `| head -1` raced far less). That raced zero times in 15 local runs,
  # where SIGPIPE is not ignored, and ten times in one CI run, failing this guard with the tell
  # "(exit 0 vs 0)" — identical status, noise-only diff. Both pipelines are gone (it now greps
  # the file directly), but any subject can grow another one.
  # Run each subject so that a working copy prints something and exits 0; a script that
  # fails silently either way (sweep_claims.sh with no arguments exits 2 before and after
  # breaking) hides a broken self-location. The check after the runs keeps that true.
  arg=""
  case "$s" in */sweep_claims.sh) arg=--help ;; esac
  a_out="$(bash "$s" $arg 2>/dev/null)"; a_rc=$?
  b_out="$(CDPATH="$decoy" bash "$s" $arg 2>/dev/null)"; b_rc=$?
  if [ "$a_rc" != 0 ] && [ -z "$a_out" ]; then
    echo "FAIL — $s exits $a_rc with no output even without CDPATH, so a CDPATH break could not"
    echo "    show. Give it arguments that make a working copy succeed (see arg= above)."
    diffs=$((diffs + 1)); rc=1; continue
  fi
  if [ "$a_rc" != "$b_rc" ] || [ "$a_out" != "$b_out" ]; then
    echo "FAIL — $s behaves differently under an exported CDPATH (stdout/status; exit $a_rc vs $b_rc):"
    diff <(printf '%s\n' "$a_out") <(printf '%s\n' "$b_out") | sed -n '1,20s/^/    /p'
    diffs=$((diffs + 1)); rc=1
  fi
done
[ "$diffs" = 0 ] && echo "OK — all $((${#SUBJECTS[@]} - skipped)) subjects behave identically with and without an exported CDPATH."

# --- regression case for the original bug -----------------------------------------------------
# The loop above cannot catch it: <project_dir> comes from the CALLER, so it needs a real
# project and a same-named decoy to resolve away to.
# Skip loudly rather than fail outside a clone (not_a_clone, above): a zip recipient should not
# get a red `make check` over a regression test that cannot run there — the same call
# test_install_pin.sh makes for the same reason. Saying SKIP matters; a silent pass here would
# be exactly the vacuous OK this guard exists to prevent.
if not_a_clone; then
  echo "SKIP — the whats-new.sh regression case needs a git clone of the suite (it compares suite history)."
  exit $rc
fi

mkdir -p "$proj/real/myproj/.claude/skills" "$proj/decoy/myproj/.claude/skills"
printf 'suite_commit: %s\n' "$(git rev-parse HEAD 2>/dev/null || echo unknown)" \
  > "$proj/real/myproj/.claude/skills/SUITE-VERSION"
printf 'suite_commit: 0000000\n' > "$proj/decoy/myproj/.claude/skills/SUITE-VERSION"
here="$PWD"
got="$(cd "$proj/real" && CDPATH="$proj/decoy" bash "$here/scripts/whats-new.sh" myproj 2>&1 |
        sed -n 's/^Project: *//p')"
case "$got" in
  *"/real/myproj")
    echo "OK — whats-new.sh resolves a relative <project_dir> to the real one, not a CDPATH decoy." ;;
  *)
    echo "FAIL — whats-new.sh did not resolve a relative <project_dir> to the real directory."
    echo "    got: [${got:-<nothing>}]"
    echo "    --refresh writes into that path, so this is the wrong-project case, not a bad report."
    rc=1 ;;
esac

exit $rc
