#!/usr/bin/env bash
# What changed in the suite's skills — overall, or since a project was scaffolded.
#
#   scripts/whats-new.sh                          # recent skill changes in the suite
#   scripts/whats-new.sh <project_dir>            # which of that project's bundled skills
#                                                 # have upstream updates (reads the
#                                                 # SUITE-VERSION stamp new-website wrote)
#   scripts/whats-new.sh --refresh <project_dir>  # re-copy the stale skills and re-stamp.
#                                                 # Overwrites local edits to those copies;
#                                                 # refuses while either the suite clone or
#                                                 # the site has uncommitted skill changes.
#                                                 # Skills listed in <skills_dir>/REFRESH-KEEP
#                                                 # (one name per line, # comments) are
#                                                 # deliberate local forks: never overwritten,
#                                                 # reported as "(pinned)", their changes kept
#                                                 # in the report until the owner deletes the
#                                                 # skill's `pinned:` line in SUITE-VERSION.
#   scripts/whats-new.sh --stamp <skills_dir>     # write the SUITE-VERSION stamp, keeping its
#                                                 # `pinned:` lines. This is
#                                                 # the ONLY writer of the stamp format —
#                                                 # new-website's scaffold step calls it too.
#   scripts/whats-new.sh --stamp-tests <tests_dir> # write the TESTS-VERSION stamp next to a
#                                                 # site's tests/ copies. The report uses it
#                                                 # to flag upstream changes to the template
#                                                 # test suite + CONTENT_GUIDE + the frozen
#                                                 # root/config/infra files (see
#                                                 # TEMPLATE_TRACKED below) — files that are
#                                                 # FROZEN one-time copies, which
#                                                 # --refresh deliberately never touches
#                                                 # (a blind overwrite would clobber the
#                                                 # site's own PAGES list / exemptions).
#                                                 # Merge those by hand, then re-stamp. The
#                                                 # stamp keeps the site's `left_out:` and
#                                                 # `kept:` lines, adds one for each file
#                                                 # changed since the last stamp that the
#                                                 # site lacks, and every report lists them.
#
# The report also flags a stale Astro MAJOR version (site's package.json vs. the suite's
# current template pin) and points at docs/UPGRADING.md — deliberately a pointer, not an
# auto-refresh: unlike a skill copy, a dependency bump needs a real build + verification
# pass, which is left to the AI assistant reading that doc, not a blind file overwrite here.
#
# Needs the git clone of the suite (a zip has no history to compare against).
set -euo pipefail

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)"

# The suite must be a git clone, and REPO_DIR must be that repo's own toplevel —
# not a zip extraction sitting inside some unrelated enclosing repository, whose
# history would silently answer every query below.
TOPLEVEL="$(git -C "$REPO_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [ "$TOPLEVEL" != "$REPO_DIR" ]; then
  echo "error: $REPO_DIR is not a git clone of the suite — whats-new compares git" >&2
  echo "history, which a zip install doesn't carry. Clone the suite repo to use this." >&2
  exit 1
fi

suite_dirty() {  # tracked, uncommitted changes under skills/
  [ -n "$(git -C "$REPO_DIR" status --porcelain -uno -- skills/)" ]
}

# Does the suite still have this skill? Read from the committed tree (HEAD), the tree the list
# of changes comes from, not from the working tree: an untracked leftover folder is not the
# suite's skill, and a refresh that copied it would stamp HEAD over content matching no commit.
suite_has() {  # $1 = skill name
  git -C "$REPO_DIR" cat-file -e "HEAD:skills/$1" 2>/dev/null
}

# A folder of a bundled skill that never goes to a site: the brand kit's own test suite (about
# 1.7 MB, run against the toolkit's fixtures; no site runs it and its SKILL.md never asks to).
# --refresh deletes it after the copy, and the report ignores changes inside it, so a site is
# never told to refresh for a file it does not get. new-website's SKILL.md deletes the same
# folder after its copy; test_whats_new_removed_skill.sh checks that the two name one path.
LEFT_BEHIND='website-brand-kit/scripts/tests'

write_stamp() {  # $1 = skills dir, $2 = optional `pinned:` lines to keep (see process_dir)
  printf 'suite_commit: %s\ncopied: %s\n%s' \
    "$(git -C "$REPO_DIR" rev-parse HEAD)" "$(date +%Y-%m-%d)" "${2:-}" > "$1/SUITE-VERSION"
}

# Upstream template files that scaffolded sites carry as FROZEN copies (tests/*,
# CONTENT_GUIDE.md, playwright.config.ts, and the root/infra files below). Tracked via
# TESTS-VERSION; never auto-refreshed. Every file under templates/ must land in
# exactly one of TEMPLATE_TRACKED, SITE_OWNED, or the guard's SITE_SOURCE bucket —
# scripts/check_template_coverage.sh enforces that so a new template file can no longer
# go silently untracked (the bug PR #87 fixed for playwright.config.ts one file at a time).
TEMPLATE_TRACKED='skills/new-website/templates/astro/tests skills/new-website/templates/content-guide.md skills/new-website/templates/AGENTS.md skills/new-website/templates/PUBLISHING.md skills/new-website/templates/SETUP.md skills/new-website/templates/CLAUDE.md skills/new-website/templates/astro/playwright.config.ts skills/new-website/templates/astro/.github/workflows/ci.yml skills/new-website/templates/astro/.github/dependabot.yml skills/new-website/templates/astro/scripts/anchor-ids.mjs skills/new-website/templates/astro/scripts/check_external_links.sh skills/new-website/templates/astro/scripts/check_internal_links.sh skills/new-website/templates/astro/scripts/run_og.mjs skills/new-website/templates/astro/tsconfig.json skills/new-website/templates/astro/public/_headers skills/new-website/templates/astro/scripts/ship.sh skills/new-website/templates/astro/scripts/deploy.sh skills/new-website/templates/astro/scripts/build-marker.mjs skills/new-website/templates/astro/scripts/set_pdf_title.py skills/new-website/templates/astro/scripts/hooks/pre-push skills/new-website/templates/astro/scripts/wire-hooks.mjs skills/new-website/templates/astro/scripts/verify.mjs skills/new-website/templates/astro/.nvmrc skills/new-website/templates/astro/.gitattributes skills/new-website/templates/claude/settings.json skills/new-website/templates/claude/hooks/git-stand.mjs skills/new-website/templates/astro/CROFTWEAVER-LICENSE.md skills/new-website/templates/astro/scripts/make-icons.mjs skills/new-website/templates/astro/scripts/orphan-exempt.mjs'
# The root templates beside templates/astro/ and the files under templates/claude/ are
# scanned by the guard too. AGENTS.md, CLAUDE.md, PUBLISHING.md and SETUP.md are tracked
# because a site's assistants follow them or its skills point into them: PUBLISHING.md's
# "For AI assistants" section holds the deploy rules, CLAUDE.md points Claude Code at
# AGENTS.md, and website-qa and website-team-setup cite SETUP.md. .gitignore, brand.md and
# positioning.md are SITE_OWNED (below).

# Upstream template files that scaffolded sites are EXPECTED to hand-edit — deliberately NOT
# drift-tracked, for two different reasons:
#  - config VALUES: astro.config.mjs's `site:`, package.json's deps. An upstream dep bump would
#    fire TESTS-VERSION drift on every refresh and drown the rare real signal in noise, and
#    check_astro_version() below already covers the part of this that matters (the Astro major
#    pin).
#  - per-site CONTENT lists: scripts/generate_og_cards.py's BRAND block (og-images/SKILL.md
#    step fills in BRAND_NAME etc.) and PAGES-shaped entries (astro-i18n-setup has sites add
#    per-page translated title/subtitle text) are hand-edited by construction — every
#    customized site's copy diverges from upstream immediately, so tracking it would fire on
#    every site, every time, which is the same noise problem as the dep-bump case above.
#  - per-site DOCS and settings: templates/brand.md and templates/positioning.md are blanks the
#    site fills in as BRAND.md and POSITIONING.md, and templates/.gitignore is the site's first
#    commit, which it adds to as it goes (the owner's decision, 2026-10-18); orphan-exempt.txt is
#    the site's own list of pages it leaves unlinked on purpose, and a site with none needs no file.
# This list changes no runtime reporting behavior on its own (nothing above reads it) — it
# exists purely so scripts/check_template_coverage.sh has a machine-readable record of the
# decision instead of a silent gap it would otherwise flag as unaccounted-for.
SITE_OWNED='skills/new-website/templates/astro/astro.config.mjs skills/new-website/templates/astro/package.json skills/new-website/templates/astro/wrangler.jsonc skills/new-website/templates/astro/scripts/generate_og_cards.py skills/new-website/templates/.gitignore skills/new-website/templates/brand.md skills/new-website/templates/positioning.md skills/new-website/templates/astro/orphan-exempt.txt'

# Must agree with the "(site copy: ...)" arms in process_tests_stamp: test_whats_new.sh checks
# every TEMPLATE_TRACKED file against both. PUBLISHING.md has no fixed site path (an owner's
# translation may be saved as PUBLISHING.de.md), so it is never marked MISSING.
site_copy_of() {  # $1 = TEMPLATE_TRACKED file; prints its site-relative copy, or nothing if unknown
  case "$1" in
    skills/new-website/templates/content-guide.md) echo "CONTENT_GUIDE.md" ;;
    skills/new-website/templates/AGENTS.md) echo "AGENTS.md" ;;
    skills/new-website/templates/CLAUDE.md) echo "CLAUDE.md" ;;
    skills/new-website/templates/SETUP.md) echo "SETUP.md" ;;
    # Workers sites only: a Pages site has no use for it, so it is never marked MISSING.
    skills/new-website/templates/astro/scripts/deploy.sh) ;;
    skills/new-website/templates/astro/*) echo "${1#skills/new-website/templates/astro/}" ;;
    skills/new-website/templates/claude/*) echo ".claude/${1#skills/new-website/templates/claude/}" ;;
  esac
}

# The site's record of frozen files it reviewed and did not take: `left_out: <path> — <why>` and
# `kept: <path> — <why>` lines in TESTS-VERSION, written by hand. A stamp keeps them, and adds a
# left_out line for each file it moves past that the site has no copy of (changed upstream since
# the old baseline, and still in the suite), so no stamp hides one; every report lists them. An
# added line goes once the site has the file.
AUTO_LEFT_OUT='— not in the site when stamped'
# An added line, matched whole, so an owner's line that quotes the marker stays the owner's.
AUTO_RE="^left_out: [^ ]+ $AUTO_LEFT_OUT [0-9]{4}-[0-9]{2}-[0-9]{2}\$"

suite_site_paths() {  # prints the site path of each tracked template file at HEAD
  # shellcheck disable=SC2086
  git -C "$REPO_DIR" ls-tree -r --name-only HEAD -- $TEMPLATE_TRACKED | while IFS= read -r f; do site_copy_of "$f"; done
}

# The oldest suite commit, in this clone, among SUITE-VERSION stamps: under-reporting is the
# dangerous direction for a staleness channel.
oldest_stamp_base() {  # $1 = SUITE-VERSION paths, one per line
  local s sb pick=""
  while IFS= read -r s; do
    [ -n "$s" ] || continue
    sb="$(sed -n 's/^suite_commit: //p' "$s")"
    [ -n "$sb" ] && [ "$sb" != "unknown" ] || continue
    git -C "$REPO_DIR" cat-file -e "$sb^{commit}" 2>/dev/null || continue
    # older = ancestor of the current pick (linear history), else compare dates
    if [ -z "$pick" ] || git -C "$REPO_DIR" merge-base --is-ancestor "$sb" "$pick" 2>/dev/null \
       || [ "$(git -C "$REPO_DIR" show -s --format=%ct "$sb")" -lt "$(git -C "$REPO_DIR" show -s --format=%ct "$pick")" ]; then
      pick="$sb"
    fi
  done <<<"$1"
  printf '%s' "$pick"
}

write_tests_stamp() {  # $1 = tests dir
  local stamp="$1/TESTS-VERSION" site_root own="" auto="" old_base="" changed="" suite_paths today gap f rel path rest
  site_root="$(dirname "$1")"
  suite_paths="$(suite_site_paths)"
  today="$(date +%Y-%m-%d)"   # read once, so the added lines and copied: agree across midnight
  if [ -f "$stamp" ]; then
    own="$(grep -E '^(#|(left_out|kept): )' "$stamp" | grep -vE -- "$AUTO_RE" || true)"
    old_base="$(sed -n 's/^suite_commit: //p' "$stamp")"
    # An added line stays while the site lacks the file and the suite still has it.
    while read -r _ path rest; do
      [ -n "$path" ] && [ ! -e "$site_root/$path" ] && grep -Fxq -- "$path" <<<"$suite_paths" && auto="${auto}left_out: $path $rest
"
    done <<<"$(grep -E -- "$AUTO_RE" "$stamp" || true)"
  fi
  # No baseline of its own (a site made before TESTS-VERSION, or "unknown"): the oldest skills
  # stamp, which the report also uses when TESTS-VERSION is absent.
  if [ -z "$old_base" ] || [ "$old_base" = unknown ]; then
    old_base="$(oldest_stamp_base "$(find "$site_root" -maxdepth 4 -name SUITE-VERSION -not -path '*/node_modules/*' 2>/dev/null | sort)")"
  fi
  if [ -n "$old_base" ] && git -C "$REPO_DIR" cat-file -e "$old_base^{commit}" 2>/dev/null; then
    # shellcheck disable=SC2086
    changed="$(git -C "$REPO_DIR" diff --name-only "$old_base" HEAD -- $TEMPLATE_TRACKED)"
  else
    # Nothing to compare from: say so on screen, and in the stamp, which outlives the screen.
    if [ -n "$old_base" ]; then gap="the old baseline in $stamp ($old_base) is not a commit in this clone"
    else gap="no stamp in $site_root names a baseline this clone has"; fi
    echo "warning: $gap, so this" >&2
    echo "stamp cannot list the files changed since then that the site lacks. Compare them by hand" >&2
    echo "and add a \`left_out: <path> — <why>\` line for each file the site does not take." >&2
    own="${own:+$own
}# $today: not compared with the suite, so files the site lacks may be unlisted: $gap"
  fi
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    rel="$(site_copy_of "$f")"
    [ -n "$rel" ] && [ ! -e "$site_root/$rel" ] && git -C "$REPO_DIR" cat-file -e "HEAD:$f" 2>/dev/null || continue
    # skip a path a left_out or kept line already names, site-relative or relative to tests/
    awk -v a="$rel" -v b="${rel#tests/}" '($1 == "left_out:" || $1 == "kept:") && ($2 == a || $2 == b) { found = 1 } END { exit !found }' <<<"$own
$auto" && continue
    auto="${auto}left_out: $rel $AUTO_LEFT_OUT $today
"
  done <<<"$changed"
  printf 'suite_commit: %s\ncopied: %s\n%s%s' \
    "$(git -C "$REPO_DIR" rev-parse HEAD)" "$today" "${own:+$own
}" "$auto" > "$stamp"
}

# True when a left_out or kept line the site wrote names this site path, as the site has it or
# relative to tests/. A line the stamp added itself does not count: it records a file the site
# lacks, which the MISSING list must keep showing.
site_left_out() {  # $1 = tests dir, $2 = site path
  [ -f "$1/TESTS-VERSION" ] || return 1
  grep -E '^(left_out|kept): ' "$1/TESTS-VERSION" | grep -vE -- "$AUTO_RE" \
    | awk -v a="$2" -v b="${2#tests/}" '$2 == a || $2 == b { found = 1 } END { exit !found }'
}

print_left_out() {  # $1 = tests dir
  local lines
  lines="$(grep -E '^(left_out|kept): ' "$1/TESTS-VERSION" 2>/dev/null || true)"
  [ -n "$lines" ] || return 0
  echo "Not taken, or kept after the starter dropped them (the site's record in $1/TESTS-VERSION):"
  printf '%s\n' "$lines" | sed 's/^/  /'
}

is_int() { case "$1" in ''|*[!0-9]*) return 1 ;; *) return 0 ;; esac; }

astro_major() {  # $1 = path to a package.json; prints its "astro" dependency's major version
  sed -n 's/.*"astro"[[:space:]]*:[[:space:]]*"[^0-9]*\([0-9][0-9]*\)\..*/\1/p' "$1" | awk 'NR == 1'
}

check_astro_version() {  # $1 = project dir; report-only, never mutates
  local pkg="$1/package.json" ref="$REPO_DIR/skills/new-website/templates/astro/package.json"
  [ -f "$pkg" ] && [ -f "$ref" ] || return 0
  local site_major suite_major
  site_major="$(astro_major "$pkg")"
  suite_major="$(astro_major "$ref")"
  is_int "$site_major" && is_int "$suite_major" || return 0
  if [ "$site_major" -lt "$suite_major" ]; then
    echo "Astro version: this site pins astro major $site_major; the suite's current template"
    echo "pins major $suite_major. Ask your AI assistant to follow docs/UPGRADING.md (in the"
    echo "suite clone) to upgrade — it walks through the version bump, the known"
    echo "gotchas, and what to verify, so nothing gets silently skipped."
    echo
  fi
}

MODE=report
TARGET=""
for arg in "$@"; do
  case "$arg" in
    --refresh|--stamp|--stamp-tests)
      [ "$MODE" = report ] || { echo "error: conflicting flags: --refresh/--stamp/--stamp-tests" >&2; exit 2; }
      MODE="${arg#--}" ;;
    -*)
      echo "error: unknown flag: $arg" >&2; exit 2 ;;
    *)
      [ -z "$TARGET" ] || { echo "error: unexpected extra argument: $arg" >&2; exit 2; }
      TARGET="$arg" ;;
  esac
done

if [ "$MODE" = stamp ]; then
  [ -n "$TARGET" ] || { echo "error: --stamp needs a <skills_dir> (e.g. <site>/.claude/skills)" >&2; exit 2; }
  [ -d "$TARGET" ] || { echo "error: no such directory: $TARGET" >&2; exit 1; }
  if suite_dirty; then
    echo "warning: the suite clone has uncommitted skill edits — the stamp records HEAD," >&2
    echo "which may not match copies made from the working tree. Commit the suite first" >&2
    echo "for a clean baseline." >&2
  fi
  pins="$(grep '^pinned: ' "$TARGET/SUITE-VERSION" 2>/dev/null || true)"
  write_stamp "$TARGET" "${pins:+$pins
}"
  echo "stamped $TARGET/SUITE-VERSION → $(git -C "$REPO_DIR" rev-parse --short HEAD)"
  exit 0
fi

if [ "$MODE" = stamp-tests ]; then
  [ -n "$TARGET" ] || { echo "error: --stamp-tests needs a <tests_dir> (e.g. <site>/tests)" >&2; exit 2; }
  [ -d "$TARGET" ] || { echo "error: no such directory: $TARGET" >&2; exit 1; }
  if suite_dirty; then
    echo "warning: the suite clone has uncommitted skill edits — the stamp records HEAD," >&2
    echo "which may not match copies made from the working tree. Commit the suite first" >&2
    echo "for a clean baseline." >&2
  fi
  write_tests_stamp "$TARGET"
  echo "stamped $TARGET/TESTS-VERSION → $(git -C "$REPO_DIR" rev-parse --short HEAD)"
  print_left_out "$TARGET"
  echo "A file you reviewed and did not take needs a line \`left_out: <path> — <why>\` in"
  echo "$TARGET/TESTS-VERSION, the path as the site has it or would (tests/x.spec.ts, AGENTS.md);"
  echo "the stamp keeps such lines, and every report lists them."
  exit 0
fi

if [ -z "$TARGET" ]; then
  [ "$MODE" = report ] || { echo "error: --refresh needs a <project_dir>" >&2; exit 2; }
  echo "Recent skill changes in the suite (newest first):"
  git -C "$REPO_DIR" log --oneline -20 -- skills/
  echo
  echo "Tip: scripts/whats-new.sh <project_dir> shows what a scaffolded project is missing."
  exit 0
fi

PROJECT="${TARGET%/}"
[ -d "$PROJECT" ] || { echo "error: no such directory: $PROJECT" >&2; exit 1; }
# Absolute physical path: `git -C` re-anchors relative pathspecs to the repo dir,
# which would silently defeat the dirty guards below for a relative <project_dir>.
# CDPATH= because a relative <project_dir> would otherwise resolve through CDPATH to a
# same-named directory elsewhere — the -d test above passes on the real one, and the
# refresh path then writes into the other.
PROJECT="$(CDPATH= cd -- "$PROJECT" && pwd -P)"

process_dir() {  # $1 = path to a SUITE-VERSION stamp
  local stamp="$1" skills_dir base short_base copied changed stale s missing keep
  skills_dir="$(dirname -- "$stamp")"
  base="$(sed -n 's/^suite_commit: //p' "$stamp")"
  copied="$(sed -n 's/^copied: //p' "$stamp")"

  echo "Skills dir: $skills_dir"

  if [ -z "$base" ] || [ "$base" = "unknown" ]; then
    echo "error: this stamp has no usable commit (the suite had no git history when the" >&2
    echo "project was scaffolded, e.g. a zip install). Refresh the copies by hand if" >&2
    echo "needed, then set a fresh baseline with:" >&2
    echo "  scripts/whats-new.sh --stamp $skills_dir" >&2
    return 1
  fi
  if ! git -C "$REPO_DIR" cat-file -e "$base^{commit}" 2>/dev/null; then
    echo "error: stamped commit $base is not in this clone — run 'git pull' first." >&2
    echo "If it still fails, the stamp was written against a different repository;" >&2
    echo "reset the baseline with:  scripts/whats-new.sh --stamp $skills_dir" >&2
    return 1
  fi
  short_base="$(git -C "$REPO_DIR" rev-parse --short "$base")"
  echo "Scaffolded: $copied at suite commit $short_base"
  echo

  # `|| return`: the caller's `process_dir || FAIL=1` switches set -e off in here, so a git that
  # failed (one that cannot read the exclude, say) would otherwise leave this empty: "Up to date".
  changed="$(git -C "$REPO_DIR" diff --name-only "$base" HEAD -- skills/ ":(exclude)skills/$LEFT_BEHIND" | cut -d/ -f2 | sort -u)" \
    || { echo "error: git could not list the suite's skill changes since $short_base (above)." >&2; return 1; }
  stale=""
  for s in $changed; do
    [ -d "$skills_dir/$s" ] && stale="$stale $s"
  done

  # A skill --refresh skipped as pinned keeps its own baseline in a `pinned: <skill> <commit>`
  # line of the stamp, so its upstream changes stay in the report after the stamp moves on.
  # Deleting the line, once the copy has what the owner wants, ends that.
  pins="$(sed -n 's/^pinned: //p' "$stamp")"
  while read -r s pb; do
    [ -n "$s" ] || continue
    [ -n "$pb" ] || { echo "error: the line 'pinned: $s' in $stamp names no commit — write it as 'pinned: <skill> <commit>', or delete it." >&2; return 1; }
    if ! git -C "$REPO_DIR" cat-file -e "$pb^{commit}" 2>/dev/null; then
      echo "error: the pinned baseline of $s in $stamp ($pb) is not in this clone — run 'git pull'" >&2
      echo "first; if it still fails, delete that line and compare $s by hand." >&2
      return 1
    fi
    case " $stale " in *" $s "*) continue ;; esac
    [ -d "$skills_dir/$s" ] || continue
    git -C "$REPO_DIR" diff --quiet "$pb" HEAD -- "skills/$s" ":(exclude)skills/$LEFT_BEHIND" || stale="$stale $s"
  done <<<"$pins"
  pin_base() { local b; b="$(awk -v s="$1" '$1 == s { print $2; exit }' <<<"$pins")"; printf '%s' "${b:-$base}"; }

  # Skills pinned by the site (deliberate local forks): REFRESH-KEEP next to the
  # stamp, one skill name per line, '#' comments allowed. --refresh leaves them
  # untouched; the report shows their upstream changes since their pinned baseline
  # (above) or, without one, since the stamp, marked (pinned).
  keep=""
  [ -f "$skills_dir/REFRESH-KEEP" ] && keep="$(sed 's/#.*//' "$skills_dir/REFRESH-KEEP")"
  # One name per line, split once: on words, so spaces around a name don't matter, and with
  # globbing off, so an entry like seo-* stays literal instead of matching files in the cwd.
  keep="$(set -f; printf '%s\n' $keep)"
  # Matched below via herestrings, not `printf | grep -q`: under pipefail, grep -q exiting
  # on its match can fail the printf once the list passes the pipe buffer, and a pinned
  # skill would then read as unpinned and be overwritten.

  if [ -z "$stale" ]; then
    echo "Up to date — none of this dir's bundled skills changed upstream since then."
    return 0
  fi

  # A skill the suite no longer has cannot be refreshed: --refresh stops on it and keeps the
  # stamp, so the report would repeat. Say so here, where a reader looks, not only after a
  # failed --refresh. A pinned one is left alone by --refresh, so it is not "gone". "Removed"
  # is suite_has: the committed tree, so the report and --refresh always agree.
  gone=""; n_stale=0; n_gone=0; n_pinned=0
  echo "Bundled skills with upstream updates:"
  for s in $stale; do
    echo
    n_stale=$((n_stale + 1))
    if [ -n "$keep" ] && grep -Fxq -- "$s" <<<"$keep"; then
      echo "  $s   (pinned in REFRESH-KEEP — --refresh will skip it)"
      n_pinned=$((n_pinned + 1))
    elif ! suite_has "$s"; then
      echo "  $s   (removed upstream — delete its copy, or list it in REFRESH-KEEP to keep it)"
      gone="$gone $s"; n_gone=$((n_gone + 1))
    else
      echo "  $s"
    fi
    git -C "$REPO_DIR" log --oneline "$(pin_base "$s")"..HEAD -- "skills/$s" ":(exclude)skills/$LEFT_BEHIND" | sed 's/^/    /'
  done
  echo
  if [ "$n_pinned" -gt 0 ]; then
    echo "Pinned copies are never overwritten, and their changes above stay in this report after a"
    echo "refresh. Once a pinned copy has what you want from them, delete its \`pinned:\` line in"
    echo "$stamp (a refresh writes one), and the report stops listing them."
    echo
  fi

  if [ "$MODE" != refresh ]; then
    if [ "$n_gone" -gt 0 ]; then
      echo "Removed upstream:$gone. --refresh stops on a removed skill and keeps the stamp"
      echo "where it is, so this list comes back until its copy is deleted from $skills_dir,"
      echo "or its name is added to $skills_dir/REFRESH-KEEP and --refresh is run. Files the"
      echo "site took from it stay in the site, unmaintained."
      [ "$n_stale" -gt "$n_gone" ] || return 0
      echo
      echo "Once those are dealt with, refresh the rest (re-stamps, and re-copies the skills"
      echo "above that are not pinned; OVERWRITES any local edits to those copies) with:"
    else
      echo "Refresh them (re-copies the skills above, except any pinned, and re-stamps; OVERWRITES"
      echo "any local edits to those copies) with:"
    fi
    echo "  scripts/whats-new.sh --refresh $PROJECT"
    return 0
  fi

  # Refresh guards — refuse when either side would lose or skew content.
  if suite_dirty; then
    echo "error: the suite clone has uncommitted changes under skills/ — a refresh copies" >&2
    echo "the committed skills, so those edits would not reach the site. Commit or stash first." >&2
    return 1
  fi
  if git -C "$PROJECT" rev-parse --show-toplevel >/dev/null 2>&1; then
    if [ -n "$(git -C "$skills_dir" status --porcelain . 2>/dev/null)" ]; then
      echo "error: the site has uncommitted changes under $skills_dir — a refresh would" >&2
      echo "overwrite them irrecoverably. Commit them in the site repo first; then any" >&2
      echo "overwrite stays recoverable via the site's git history." >&2
      return 1
    fi
    echo "note: refresh overwrites these skill copies; local edits stay recoverable via"
    echo "the site repo's git history."
  else
    echo "warning: $PROJECT is not a git repo — refresh OVERWRITES local edits to these" >&2
    echo "skill copies with no way back." >&2
  fi

  missing=0; pinned_lines=""
  for s in $stale; do
    if [ -n "$keep" ] && grep -Fxq -- "$s" <<<"$keep"; then
      echo "pinned    $s — in REFRESH-KEEP; local copy left as-is despite upstream changes"
      # A pinned skill the suite removed has nothing more to report: no line, so the repeat ends.
      suite_has "$s" && pinned_lines="${pinned_lines}pinned: $s $(git -C "$REPO_DIR" rev-parse "$(pin_base "$s")")
"
      continue
    fi
    if suite_has "$s"; then
      # Write the skill as HEAD holds it, the commit the stamp names, through a throwaway index:
      # not the clone's files (an untracked, ignored, assume-unchanged or skip-worktree one would
      # pass suite_dirty) and not `git archive` (export-ignore thins it). Built beside the old
      # copy and swapped in only once complete. `|| return`: set -e is off in here.
      new="$skills_dir/.$s.refresh"; idx="$new.index"
      rm -rf "${new:?}" "${idx:?}"
      if ! { mkdir "$new" \
          && GIT_INDEX_FILE="$idx" git -C "$REPO_DIR" read-tree "HEAD:skills/$s" \
          && GIT_INDEX_FILE="$idx" git -C "$REPO_DIR" checkout-index -a --prefix="$new/"; }; then
        rm -rf "${new:?}" "${idx:?}"
        echo "error: could not copy $s from the suite; the site's copy of $s is unchanged and the stamp is not advanced." >&2
        return 1
      fi
      rm -f "$idx"
      rm -rf "${skills_dir:?}/$s"
      if [ -e "$skills_dir/$s" ] || [ -L "$skills_dir/$s" ] || ! mv "$new" "$skills_dir/$s"; then
        echo "error: could not replace the site's copy of $s, which may now be partly removed (restore it from the site's git history; the new one is in $new); the stamp is not advanced." >&2
        return 1
      fi
      case "$LEFT_BEHIND" in "$s"/*)
        rm -rf "${skills_dir:?}/$LEFT_BEHIND"
        if [ -e "$skills_dir/$LEFT_BEHIND" ] || [ -L "$skills_dir/$LEFT_BEHIND" ]; then
          echo "error: could not remove $skills_dir/$LEFT_BEHIND from the refreshed $s (a site never takes it); delete that folder by hand, commit the site's changes under $skills_dir, then run --refresh again; the stamp is not advanced." >&2
          return 1
        fi ;;
      esac
      find "$skills_dir/$s" -name .DS_Store -delete 2>/dev/null || true
      echo "refreshed $s"
    else
      echo "✗ $s was removed upstream — its copy in $skills_dir is now unmaintained;" >&2
      echo "  delete it, or list it in $skills_dir/REFRESH-KEEP, then re-run --refresh to advance the stamp." >&2
      missing=1
    fi
  done
  if [ "$missing" -ne 0 ]; then
    echo "stamp NOT advanced (still $short_base) so the removed-upstream warning keeps firing." >&2
    return 1
  fi
  write_stamp "$skills_dir" "$pinned_lines"
  echo "stamp updated → $(git -C "$REPO_DIR" rev-parse --short HEAD)"
  [ -z "$pinned_lines" ] || echo "pinned skills keep their own baseline in $skills_dir/SUITE-VERSION, so their upstream changes stay in the report"
}

# The first ./ or ../ specifier of each one-line static import on stdin. A helper, not a
# parser: other import forms are not read, and the report says so.
# Quotes are made double first (no octal escape for awk to differ on); each /* */ comment
# becomes a blank. The specifier is the quoted string after the first `from`, or a bare
# import's own.
spec_imports() {
  awk '{ gsub(/'\''/, "\"")
      while ((i = index($0, "/*")) && (j = index(substr($0, i + 2), "*/")))
        $0 = substr($0, 1, i - 1) " " substr($0, i + j + 3)
    }
    /^[[:space:]]*import[[:space:]]*"/ { match($0, /"[^"]*"/); s = substr($0, RSTART + 1, RLENGTH - 2)
      if (s ~ /^\.\.?\//) print s; next }
    /^[[:space:]]*import[[:space:]{*]/ && match($0, /[[:space:]}*]from[[:space:]]*"[^"]*"/) {
      s = substr($0, RSTART, RLENGTH); sub(/^.from[[:space:]]*"/, "", s); s = substr(s, 1, length(s) - 1)
      if (s ~ /^\.\.?\//) print s
    }'
}

# $1 = the spec's folder in the site, $2 = specifier; prints the site-relative path (empty
# for the site's top folder), or returns 1 when the specifier leaves the site.
resolve_import() {
  local rest="$1/$2" part out=""
  while [ -n "$rest" ]; do
    part="${rest%%/*}"
    if [ "$part" = "$rest" ]; then rest=""; else rest="${rest#*/}"; fi
    case "$part" in
      ""|.) ;;
      ..) [ -n "$out" ] || return 1
          case "$out" in */*) out="${out%/*}" ;; *) out="" ;; esac ;;
      *) out="${out:+$out/}$part" ;;
    esac
  done
  printf '%s\n' "$out"
}

# Regular files only, so an empty folder of the import's name does not count.
site_has_module() {  # $1 = path in the site, as imported (extension optional)
  [ -f "$1" ] || [ -f "$1.ts" ] || [ -f "$1.tsx" ] || [ -f "$1.js" ] || [ -f "$1.mjs" ] || [ -f "$1/index.ts" ]
}

process_tests_stamp() {  # $1 = tests dir, $2 = baseline commit, $3 = baseline source label
  local tests_dir="$1" base="$2" src="$3" short_base changed f site_rel missing=""
  local site_root spec_site spec path lacking="" specs_checked=""
  site_root="$(dirname "$tests_dir")"
  if [ -z "$base" ] || [ "$base" = "unknown" ]; then
    echo "error: the tests baseline ($src) has no usable commit (zip install?). Compare by" >&2
    echo "hand, then set a fresh baseline with:  scripts/whats-new.sh --stamp-tests $tests_dir" >&2
    return 1
  fi
  if ! git -C "$REPO_DIR" cat-file -e "$base^{commit}" 2>/dev/null; then
    echo "error: tests baseline $base is not in this clone — run 'git pull' first, or" >&2
    echo "reset it with:  scripts/whats-new.sh --stamp-tests $tests_dir" >&2
    return 1
  fi
  short_base="$(git -C "$REPO_DIR" rev-parse --short "$base")"
  echo "Template tests: $tests_dir (baseline $short_base, from $src)"
  print_left_out "$tests_dir"

  # shellcheck disable=SC2086
  changed="$(git -C "$REPO_DIR" diff --name-only "$base" HEAD -- $TEMPLATE_TRACKED)"
  if [ -z "$changed" ]; then
    echo "Up to date — no upstream changes to the template test suite / CONTENT_GUIDE / frozen root+infra files."
    if [ "${src#SUITE-VERSION}" != "$src" ]; then
      echo "Pin the tests baseline off the fallback (it moves when skills refresh):"
      echo "  scripts/whats-new.sh --stamp-tests $tests_dir"
    fi
    return 0
  fi

  echo
  echo "Template test files changed upstream — your site's copies are NOT auto-refreshed"
  echo "(they are frozen one-time copies that may carry site-specific edits like the"
  echo "PAGES list; --refresh deliberately never touches them):"
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    case "$f" in
      skills/new-website/templates/astro/tests/icons.spec.ts)
        echo "  tests/icons.spec.ts (site copy: tests/icons.spec.ts — copy it with scripts/make-icons.mjs, which it imports; that file's note says what the icons need before npm test)" ;;
      skills/new-website/templates/astro/tests/orphans.spec.ts)
        echo "  tests/orphans.spec.ts (site copy: tests/orphans.spec.ts — copy it together with scripts/orphan-exempt.mjs and scripts/check_internal_links.sh. If you added pages to ORPHAN_EXEMPT, write each on its own line in orphan-exempt.txt; if you added none, you need no file)" ;;
      skills/new-website/templates/astro/tests/middleware.spec.ts|skills/new-website/templates/astro/tests/analytics-server.spec.ts)
        echo "  ${f#skills/new-website/templates/astro/} (removed from the starter with Pages Functions and analytics server mode; keep your copy while the site keeps the functions/ file it imports, otherwise delete it)" ;;
      skills/new-website/templates/astro/tests/check_analytics_gate.sh|skills/new-website/templates/astro/tests/check_deploy.sh)
        echo "  ${f#skills/new-website/templates/astro/} (site copy: ${f#skills/new-website/templates/astro/} — it reads src/config.ts, the site's own file, which this report never lists: compare its PROD_BRANCH and USE_ANALYTICS lines and the ANALYTICS enabled: line with the starter's src/config.ts; the test names any line it lacks)" ;;
      skills/new-website/templates/astro/tests/workers-config.spec.ts)
        echo "  tests/workers-config.spec.ts (site copy: tests/workers-config.spec.ts — Workers sites only; a Pages site skips it. It fails unless wrangler.jsonc has no \`main\`, \`workers_dev: false\`, \`preview_urls: true\` and assets from ./dist, so taking it can mean editing wrangler.jsonc, and that changes the deploy: \`workers_dev: false\` closes the workers.dev address, \`preview_urls: true\` turns Preview links on)" ;;
      skills/new-website/templates/astro/tests/*)
        echo "  ${f#skills/new-website/templates/astro/} (site copy: ${f#skills/new-website/templates/astro/})" ;;
      skills/new-website/templates/content-guide.md)
        echo "  templates/content-guide.md (site copy: CONTENT_GUIDE.md)" ;;
      skills/new-website/templates/AGENTS.md)
        echo "  templates/AGENTS.md (site copy: AGENTS.md — rules the assistants execute; merge by hand, the site's copy carries filled slots and §5)" ;;
      skills/new-website/templates/PUBLISHING.md)
        echo "  templates/PUBLISHING.md (site copy: PUBLISHING.md, or the owner's translation — deploy rules the assistants execute; merge by hand, keeping its \"For AI assistants\" section)" ;;
      skills/new-website/templates/CLAUDE.md)
        echo "  templates/CLAUDE.md (site copy: CLAUDE.md — the line that has Claude Code read AGENTS.md; copied unchanged at scaffold, so unless the site edited it, take the new version)" ;;
      skills/new-website/templates/SETUP.md)
        echo "  templates/SETUP.md (site copy: SETUP.md — setup steps the site's skills point into; copied unchanged at scaffold, so unless the site edited it, take the new version)" ;;
      skills/new-website/templates/astro/playwright.config.ts)
        echo "  templates/astro/playwright.config.ts (site copy: playwright.config.ts)" ;;
      skills/new-website/templates/astro/.github/workflows/ci.yml)
        echo "  templates/astro/.github/workflows/ci.yml (site copy: .github/workflows/ci.yml)" ;;
      skills/new-website/templates/astro/.github/dependabot.yml)
        echo "  templates/astro/.github/dependabot.yml (site copy: .github/dependabot.yml — monthly grouped version updates; take it if the site has none, or merge by hand: its \`ignore\` rules hold two majors back, and someone must merge the monthly pull request, so delete it if nobody will; security updates stay on without it)" ;;
      skills/new-website/templates/astro/scripts/anchor-ids.mjs)
        echo "  templates/astro/scripts/anchor-ids.mjs (site copy: scripts/anchor-ids.mjs)" ;;
      skills/new-website/templates/astro/scripts/check_external_links.sh)
        echo "  templates/astro/scripts/check_external_links.sh (site copy: scripts/check_external_links.sh)" ;;
      skills/new-website/templates/astro/scripts/check_internal_links.sh)
        echo "  templates/astro/scripts/check_internal_links.sh (site copy: scripts/check_internal_links.sh — copy it with scripts/orphan-exempt.mjs, which it runs)" ;;
      skills/new-website/templates/astro/scripts/run_og.mjs)
        echo "  templates/astro/scripts/run_og.mjs (site copy: scripts/run_og.mjs)" ;;
      skills/new-website/templates/astro/tsconfig.json)
        echo "  templates/astro/tsconfig.json (site copy: tsconfig.json)" ;;
      skills/new-website/templates/astro/public/_headers)
        echo "  templates/astro/public/_headers (site copy: public/_headers)" ;;
      skills/new-website/templates/astro/scripts/make-icons.mjs)
        echo "  templates/astro/scripts/make-icons.mjs (site copy: scripts/make-icons.mjs — copy it with tests/icons.spec.ts. A site with no icons, or only the Astro logo, runs \`node scripts/make-icons.mjs --setup\` before \`npm test\`; a site with the brand kit's icons needs nothing more; a site built by hand from references/tab-icon.md copies public/icon-512.png to public/images/logo.png)" ;;
      skills/new-website/templates/astro/scripts/orphan-exempt.mjs)
        echo "  templates/astro/scripts/orphan-exempt.mjs (site copy: scripts/orphan-exempt.mjs — copy it with tests/orphans.spec.ts)" ;;
      skills/new-website/templates/astro/scripts/ship.sh)
        echo "  templates/astro/scripts/ship.sh (site copy: scripts/ship.sh)" ;;
      skills/new-website/templates/astro/scripts/deploy.sh)
        echo "  templates/astro/scripts/deploy.sh (site copy: scripts/deploy.sh — Workers sites only; a site still on Cloudflare Pages must not take it until it has moved, and also needs wrangler.jsonc, the \"wrangler\" devDependency and the deploy:preview and deploy:live scripts in its package.json)" ;;
      skills/new-website/templates/astro/scripts/build-marker.mjs)
        echo "  templates/astro/scripts/build-marker.mjs (site copy: scripts/build-marker.mjs)" ;;
      skills/new-website/templates/astro/scripts/set_pdf_title.py)
        echo "  templates/astro/scripts/set_pdf_title.py (site copy: scripts/set_pdf_title.py)" ;;
      skills/new-website/templates/astro/scripts/hooks/pre-push)
        echo "  templates/astro/scripts/hooks/pre-push (site copy: scripts/hooks/pre-push)" ;;
      skills/new-website/templates/astro/scripts/wire-hooks.mjs)
        echo "  templates/astro/scripts/wire-hooks.mjs (site copy: scripts/wire-hooks.mjs — it does nothing until the site's package.json has \"prepare\": \"node scripts/wire-hooks.mjs\"; the hook's header says more)" ;;
      skills/new-website/templates/astro/scripts/verify.mjs)
        echo "  templates/astro/scripts/verify.mjs (site copy: scripts/verify.mjs — the pre-push hook runs it once it is there; \`npm run verify\` also needs \"verify\": \"node scripts/verify.mjs\" in the site's package.json)" ;;
      skills/new-website/templates/astro/.nvmrc)
        echo "  templates/astro/.nvmrc (site copy: .nvmrc)" ;;
      skills/new-website/templates/astro/.gitattributes)
        echo "  templates/astro/.gitattributes (site copy: .gitattributes — keeps the hook and shell scripts LF; a Windows working copy made before it still holds CRLF copies, which Git for Windows runs but WSL or a container does not: there, after committing the file and with no unsaved changes in them, run from the site root in Git Bash: \`git ls-files -z -- scripts/hooks/pre-push \"*.sh\" | xargs -0 rm -f && git checkout -- scripts/hooks/pre-push \"*.sh\"\` (deleting first is needed: git does not rewrite an unchanged file))" ;;
      skills/new-website/templates/astro/CROFTWEAVER-LICENSE.md)
        echo "  templates/astro/CROFTWEAVER-LICENSE.md (site copy: CROFTWEAVER-LICENSE.md — the licence of the Croftweaver files in the site; copy it as is, it is the toolkit's LICENSE)" ;;
      skills/new-website/templates/claude/settings.json)
        echo "  templates/claude/settings.json (site copy: .claude/settings.json — merge by hand, the site's copy may carry its own permissions; every hook it registers needs its script in .claude/hooks/)" ;;
      skills/new-website/templates/claude/hooks/git-stand.mjs)
        echo "  templates/claude/hooks/git-stand.mjs (site copy: .claude/hooks/git-stand.mjs — copy as is; a site without it gets it with website-team-setup, which also registers it in .claude/settings.json)" ;;
      *)
        echo "  $f" ;;
    esac
    # A file the site never had (or deleted) is not drift: merging "changes" into nothing
    # reads as optional, and for verify.mjs or the pre-push hook it means no local gate.
    # A file deleted upstream is left alone; so is one with no known site path.
    site_rel="$(site_copy_of "$f")"
    if [ -n "$site_rel" ] && [ ! -e "$(dirname "$tests_dir")/$site_rel" ] &&
       git -C "$REPO_DIR" cat-file -e "HEAD:$f" 2>/dev/null &&
       ! site_left_out "$tests_dir" "$site_rel"; then
      echo "    MISSING: the site has no $site_rel"
      missing="$missing  $site_rel
"
    fi
    git -C "$REPO_DIR" log --oneline "$base"..HEAD -- "$f" | sed 's/^/    /'
    # A changed spec can import a file the site never had (src/lib, functions/): name it.
    case "$f" in
      skills/new-website/templates/astro/tests/*.spec.ts)
        if git -C "$REPO_DIR" cat-file -e "HEAD:$f" 2>/dev/null; then
          specs_checked=1
          spec_site="${f#skills/new-website/templates/astro/}"
          while IFS= read -r spec; do
            [ -n "$spec" ] || continue
            if ! path="$(resolve_import "$(dirname "$spec_site")" "$spec")" || [ -z "$path" ]; then
              echo "    IMPORT NOT CHECKED: $spec points outside the site or at its top folder"
            elif ! site_has_module "$site_root/$path"; then
              echo "    IMPORT NOT FOUND: $path (this spec imports it)"
              lacking="$lacking  $spec_site → $path
"
            fi
          done <<IMPORTS
$(git -C "$REPO_DIR" show "HEAD:$f" | spec_imports)
IMPORTS
        fi ;;
    esac
  done <<CHANGED
$changed
CHANGED
  if [ -n "$missing" ]; then
    echo
    echo "MISSING from the site — not drift, there is no copy to merge into. Copy each one in"
    echo "from the template (the notes above say what else it needs), or note why the site"
    echo "does without it:"
    printf '%s' "$missing"
  fi
  if [ -n "$lacking" ]; then
    echo
    echo "Specs that import a file this site lacks. Before taking one, take the file too, change"
    echo "the spec, or leave the spec out and note why:"
    printf '%s' "$lacking"
  fi
  if [ -n "$specs_checked" ]; then
    echo
    echo "Import check: reads one-line \"import … from './…'\" and \"import '../…'\" lines only (the path after the first 'from', or a bare import's own; relative paths only); other forms are not checked."
  fi
  echo
  echo "Review + merge each by hand, e.g.:"
  echo "  git -C $REPO_DIR diff $short_base HEAD -- $(head -n 1 <<<"$changed")"
  if grep -q '_helpers\.ts$' <<<"$changed"; then
    echo "NOTE: tests/_helpers.ts changed — specs import it (tone.spec.ts, i18n.spec.ts on"
    echo "multilingual sites, mail-form.spec.ts with a contact form), so merge the helpers together"
    echo "with any spec that uses the new exports, or the import breaks loudly."
  fi
  echo "When the site's copies are current again, advance the baseline. First add a line"
  echo "\`left_out: <path> — <why>\` to $tests_dir/TESTS-VERSION for each file you chose not to take:"
  echo "  scripts/whats-new.sh --stamp-tests $tests_dir"
  return 2
}

# Locate every bundled-skills dir by its stamp — covers .claude/skills,
# .agents/skills, and any custom $PROJECT_SKILLS_DIR new-website was run with.
STAMPS="$(find "$PROJECT" -maxdepth 4 -name SUITE-VERSION -not -path '*/node_modules/*' 2>/dev/null | sort)"
if [ -z "$STAMPS" ]; then
  # Even without a skills stamp, a present tests/TESTS-VERSION is actionable —
  # report the tests channel before erroring on the skills side.
  if [ -f "$PROJECT/tests/TESTS-VERSION" ]; then
    TB="$(sed -n 's/^suite_commit: //p' "$PROJECT/tests/TESTS-VERSION")"
    TESTS_ALONE=0
    process_tests_stamp "$PROJECT/tests" "$TB" "tests/TESTS-VERSION" || TESTS_ALONE=$?
    echo
  fi
  for d in "$PROJECT/.claude/skills" "$PROJECT/.agents/skills"; do
    [ -d "$d" ] || continue
    if [ "${TESTS_ALONE-}" ]; then
      # The tests channel was reported above, so the folder is a note, not a failure: it may be
      # the site's own, not the kit's. Exit as the tests-only branch below does.
      echo "note: $d has no SUITE-VERSION stamp, so the bundled skills were not compared. If the folder is from the kit, stamp it: scripts/whats-new.sh --stamp $d"
      [ "$TESTS_ALONE" = 1 ] && exit 1
      exit 0
    fi
    echo "error: $d exists but has no SUITE-VERSION stamp — the project predates stamping." >&2
    echo "Baseline unknown; compare by hand (git -C $REPO_DIR log --oneline -- skills/)," >&2
    echo "refresh the copies you care about, then create the stamp with:" >&2
    echo "  scripts/whats-new.sh --stamp $d" >&2
    exit 1
  done
  if [ -d "$PROJECT/tests" ] && [ ! -f "$PROJECT/tests/TESTS-VERSION" ]; then
    echo "error: $PROJECT/tests exists, but no SUITE-VERSION or tests/TESTS-VERSION stamp says" >&2
    echo "which suite commit the tests came from, so there is no baseline to compare with." >&2
    echo "Pick one: a suite commit from before the site was made. The suite's commits, newest first:" >&2
    echo "  git -C \"$REPO_DIR\" log --format='%H %cs %s'" >&2
    echo "Write it into the tests stamp, then run this again:" >&2
    echo "  printf 'suite_commit: %s\\n' <that commit> > \"$PROJECT/tests/TESTS-VERSION\"" >&2
    exit 1
  fi
  if [ "${TESTS_ALONE-}" ]; then
    # The tests channel was reported above; stale tests (status 2) are a report, not a failure.
    echo "note: no SUITE-VERSION stamp and no .claude/skills or .agents/skills dir found under $PROJECT, so the bundled skills were not compared."
    [ "$TESTS_ALONE" = 1 ] && exit 1
    exit 0
  fi
  echo "error: no SUITE-VERSION stamp (and no .claude/skills or .agents/skills dir)" >&2
  echo "found under $PROJECT — not a site scaffolded by new-website?" >&2
  exit 1
fi

echo "Project:    $PROJECT"

# Capture the tests-channel FALLBACK baseline NOW — before process_dir, whose
# --refresh rewrites the SUITE-VERSION stamps to HEAD; reading it afterwards
# would silently destroy the pre-refresh baseline (and with it all reported
# template-test drift) for every site that predates TESTS-VERSION. With
# multiple stamps (.claude/skills AND .agents/skills), take the OLDEST commit —
# under-reporting is the dangerous direction for a staleness channel.
FALLBACK_BASE="$(oldest_stamp_base "$STAMPS")"

FAIL=0
while IFS= read -r STAMP; do
  [ -n "$STAMP" ] || continue
  process_dir "$STAMP" || FAIL=1
  echo
done <<EOF
$STAMPS
EOF

# Template-tests staleness (frozen copies, tracked separately from skill dirs).
# Baseline: tests/TESTS-VERSION when present; pre-existing sites (scaffolded
# before TESTS-VERSION existed) fall back to the first SUITE-VERSION stamp's
# commit — the closest recorded scaffold point — and the report says so.
TESTS_DIR="$PROJECT/tests"
TESTS_STATUS=0
if [ -d "$TESTS_DIR" ]; then
  if [ -f "$TESTS_DIR/TESTS-VERSION" ]; then
    TB="$(sed -n 's/^suite_commit: //p' "$TESTS_DIR/TESTS-VERSION")"
    process_tests_stamp "$TESTS_DIR" "$TB" "tests/TESTS-VERSION" || TESTS_STATUS=$?
  elif [ -n "$FALLBACK_BASE" ]; then
    process_tests_stamp "$TESTS_DIR" "$FALLBACK_BASE" "SUITE-VERSION fallback (oldest stamp, captured pre-refresh) — no tests/TESTS-VERSION yet" || TESTS_STATUS=$?
  else
    echo "note: $TESTS_DIR has no TESTS-VERSION and no skills stamp is usable as a" >&2
    echo "fallback — template-test drift can't be reported. Set a baseline with:" >&2
    echo "  scripts/whats-new.sh --stamp-tests $TESTS_DIR" >&2
  fi
  echo
fi
# Stale template tests (status 2) are a report, not a failure; real errors (1) fail.
[ "$TESTS_STATUS" = 1 ] && FAIL=1

check_astro_version "$PROJECT"

exit $FAIL
