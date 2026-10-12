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
#                                                 # reported as "(pinned)".
#   scripts/whats-new.sh --stamp <skills_dir>     # write the SUITE-VERSION stamp. This is
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
#                                                 # Merge those by hand, then re-stamp.
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

write_stamp() {  # $1 = skills dir
  printf 'suite_commit: %s\ncopied: %s\n' \
    "$(git -C "$REPO_DIR" rev-parse HEAD)" "$(date +%Y-%m-%d)" > "$1/SUITE-VERSION"
}

# Upstream template files that scaffolded sites carry as FROZEN copies (tests/*,
# CONTENT_GUIDE.md, playwright.config.ts, and the root/infra files below). Tracked via
# TESTS-VERSION; never auto-refreshed. Every file under templates/astro/ must land in
# exactly one of TEMPLATE_TRACKED, SITE_OWNED, or the guard's SITE_SOURCE bucket —
# scripts/check_template_coverage.sh enforces that so a new template file can no longer
# go silently untracked (the bug PR #87 fixed for playwright.config.ts one file at a time).
TEMPLATE_TRACKED='skills/new-website/templates/astro/tests skills/new-website/templates/content-guide.md skills/new-website/templates/AGENTS.md skills/new-website/templates/PUBLISHING.md skills/new-website/templates/SETUP.md skills/new-website/templates/astro/playwright.config.ts skills/new-website/templates/astro/functions/_middleware.ts skills/new-website/templates/astro/.github/workflows/ci.yml skills/new-website/templates/astro/scripts/anchor-ids.mjs skills/new-website/templates/astro/scripts/check_external_links.sh skills/new-website/templates/astro/scripts/check_internal_links.sh skills/new-website/templates/astro/scripts/run_og.mjs skills/new-website/templates/astro/tsconfig.json skills/new-website/templates/astro/public/_headers skills/new-website/templates/astro/scripts/ship.sh skills/new-website/templates/astro/scripts/build-marker.mjs skills/new-website/templates/astro/scripts/set_pdf_title.py skills/new-website/templates/astro/scripts/hooks/pre-push skills/new-website/templates/astro/scripts/wire-hooks.mjs skills/new-website/templates/astro/scripts/verify.mjs skills/new-website/templates/astro/.nvmrc skills/new-website/templates/astro/.gitattributes skills/new-website/templates/claude/settings.json skills/new-website/templates/claude/hooks/git-stand.mjs'
# The guard scans templates/astro/ only, so the root templates beside it are added here
# by hand and nothing checks the choice. AGENTS.md, PUBLISHING.md and SETUP.md are
# tracked because a site's assistants follow them or its skills point into them:
# PUBLISHING.md's "For AI assistants" section holds the deploy rules, and website-qa and
# website-team-setup cite SETUP.md. The other root templates have no recorded decision yet.

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
# This list changes no runtime reporting behavior on its own (nothing above reads it) — it
# exists purely so scripts/check_template_coverage.sh has a machine-readable record of the
# decision instead of a silent gap it would otherwise flag as unaccounted-for.
SITE_OWNED='skills/new-website/templates/astro/astro.config.mjs skills/new-website/templates/astro/package.json skills/new-website/templates/astro/scripts/generate_og_cards.py'

write_tests_stamp() {  # $1 = tests dir
  printf 'suite_commit: %s\ncopied: %s\n' \
    "$(git -C "$REPO_DIR" rev-parse HEAD)" "$(date +%Y-%m-%d)" > "$1/TESTS-VERSION"
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
  write_stamp "$TARGET"
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

  changed="$(git -C "$REPO_DIR" diff --name-only "$base" HEAD -- skills/ | cut -d/ -f2 | sort -u)"
  stale=""
  for s in $changed; do
    [ -d "$skills_dir/$s" ] && stale="$stale $s"
  done

  # Skills pinned by the site (deliberate local forks): REFRESH-KEEP next to the
  # stamp, one skill name per line, '#' comments allowed. --refresh leaves them
  # untouched; the report shows their upstream changes SINCE THE STAMP, marked
  # (pinned). Note a refresh advances the stamp past skipped changes too — each
  # pinned change is reported until the next refresh, not forever.
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
  gone=""; n_stale=0; n_gone=0
  echo "Bundled skills with upstream updates:"
  for s in $stale; do
    echo
    n_stale=$((n_stale + 1))
    if [ -n "$keep" ] && grep -Fxq -- "$s" <<<"$keep"; then
      echo "  $s   (pinned in REFRESH-KEEP — --refresh will skip it)"
    elif ! suite_has "$s"; then
      echo "  $s   (removed upstream — delete its copy, or list it in REFRESH-KEEP to keep it)"
      gone="$gone $s"; n_gone=$((n_gone + 1))
    else
      echo "  $s"
    fi
    git -C "$REPO_DIR" log --oneline "$base"..HEAD -- "skills/$s" | sed 's/^/    /'
  done
  echo

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
    echo "error: the suite clone has uncommitted changes under skills/ — a refresh would" >&2
    echo "copy content matching no commit while stamping HEAD. Commit or stash first." >&2
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

  missing=0
  for s in $stale; do
    if [ -n "$keep" ] && grep -Fxq -- "$s" <<<"$keep"; then
      echo "pinned    $s — in REFRESH-KEEP; local copy left as-is despite upstream changes"
      continue
    fi
    if suite_has "$s"; then
      rm -rf "${skills_dir:?}/$s"
      cp -R "$REPO_DIR/skills/$s" "$skills_dir/"
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
  write_stamp "$skills_dir"
  echo "stamp updated → $(git -C "$REPO_DIR" rev-parse --short HEAD)"
}

# Must agree with the "(site copy: ...)" arms in process_tests_stamp: test_whats_new.sh checks
# every TEMPLATE_TRACKED file against both. PUBLISHING.md has no fixed site path (an owner's
# translation may be saved as PUBLISHING.de.md), so it is never marked MISSING.
site_copy_of() {  # $1 = TEMPLATE_TRACKED file; prints its site-relative copy, or nothing if unknown
  case "$1" in
    skills/new-website/templates/content-guide.md) echo "CONTENT_GUIDE.md" ;;
    skills/new-website/templates/AGENTS.md) echo "AGENTS.md" ;;
    skills/new-website/templates/SETUP.md) echo "SETUP.md" ;;
    skills/new-website/templates/astro/*) echo "${1#skills/new-website/templates/astro/}" ;;
    skills/new-website/templates/claude/*) echo ".claude/${1#skills/new-website/templates/claude/}" ;;
  esac
}

process_tests_stamp() {  # $1 = tests dir, $2 = baseline commit, $3 = baseline source label
  local tests_dir="$1" base="$2" src="$3" short_base changed f site_rel missing=""
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
      skills/new-website/templates/astro/tests/*)
        echo "  ${f#skills/new-website/templates/astro/} (site copy: ${f#skills/new-website/templates/astro/})" ;;
      skills/new-website/templates/content-guide.md)
        echo "  templates/content-guide.md (site copy: CONTENT_GUIDE.md)" ;;
      skills/new-website/templates/AGENTS.md)
        echo "  templates/AGENTS.md (site copy: AGENTS.md — rules the assistants execute; merge by hand, the site's copy carries filled slots and §5)" ;;
      skills/new-website/templates/PUBLISHING.md)
        echo "  templates/PUBLISHING.md (site copy: PUBLISHING.md, or the owner's translation — deploy rules the assistants execute; merge by hand, keeping its \"For AI assistants\" section)" ;;
      skills/new-website/templates/SETUP.md)
        echo "  templates/SETUP.md (site copy: SETUP.md — setup steps the site's skills point into; copied unchanged at scaffold, so unless the site edited it, take the new version)" ;;
      skills/new-website/templates/astro/playwright.config.ts)
        echo "  templates/astro/playwright.config.ts (site copy: playwright.config.ts)" ;;
      skills/new-website/templates/astro/functions/_middleware.ts)
        echo "  templates/astro/functions/_middleware.ts (site copy: functions/_middleware.ts)" ;;
      skills/new-website/templates/astro/.github/workflows/ci.yml)
        echo "  templates/astro/.github/workflows/ci.yml (site copy: .github/workflows/ci.yml)" ;;
      skills/new-website/templates/astro/scripts/anchor-ids.mjs)
        echo "  templates/astro/scripts/anchor-ids.mjs (site copy: scripts/anchor-ids.mjs)" ;;
      skills/new-website/templates/astro/scripts/check_external_links.sh)
        echo "  templates/astro/scripts/check_external_links.sh (site copy: scripts/check_external_links.sh)" ;;
      skills/new-website/templates/astro/scripts/check_internal_links.sh)
        echo "  templates/astro/scripts/check_internal_links.sh (site copy: scripts/check_internal_links.sh)" ;;
      skills/new-website/templates/astro/scripts/run_og.mjs)
        echo "  templates/astro/scripts/run_og.mjs (site copy: scripts/run_og.mjs)" ;;
      skills/new-website/templates/astro/tsconfig.json)
        echo "  templates/astro/tsconfig.json (site copy: tsconfig.json)" ;;
      skills/new-website/templates/astro/public/_headers)
        echo "  templates/astro/public/_headers (site copy: public/_headers)" ;;
      skills/new-website/templates/astro/scripts/ship.sh)
        echo "  templates/astro/scripts/ship.sh (site copy: scripts/ship.sh)" ;;
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
       git -C "$REPO_DIR" cat-file -e "HEAD:$f" 2>/dev/null; then
      echo "    MISSING: the site has no $site_rel"
      missing="$missing  $site_rel
"
    fi
    git -C "$REPO_DIR" log --oneline "$base"..HEAD -- "$f" | sed 's/^/    /'
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
  echo
  echo "Review + merge each by hand, e.g.:"
  echo "  git -C $REPO_DIR diff $short_base HEAD -- $(head -n 1 <<<"$changed")"
  if grep -q '_helpers\.ts$' <<<"$changed"; then
    echo "NOTE: tests/_helpers.ts changed — specs import it (tone.spec.ts, i18n.spec.ts on"
    echo "multilingual sites, mail-form.spec.ts with a contact form), so merge the helpers together"
    echo "with any spec that uses the new exports, or the import breaks loudly."
  fi
  echo "When the site's copies are current again, advance the baseline:"
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
    process_tests_stamp "$PROJECT/tests" "$TB" "tests/TESTS-VERSION" || true
    echo
  fi
  for d in "$PROJECT/.claude/skills" "$PROJECT/.agents/skills"; do
    [ -d "$d" ] || continue
    echo "error: $d exists but has no SUITE-VERSION stamp — the project predates stamping." >&2
    echo "Baseline unknown; compare by hand (git -C $REPO_DIR log --oneline -- skills/)," >&2
    echo "refresh the copies you care about, then create the stamp with:" >&2
    echo "  scripts/whats-new.sh --stamp $d" >&2
    exit 1
  done
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
FALLBACK_BASE=""
while IFS= read -r STAMP; do
  [ -n "$STAMP" ] || continue
  SB="$(sed -n 's/^suite_commit: //p' "$STAMP")"
  [ -n "$SB" ] && [ "$SB" != "unknown" ] || continue
  git -C "$REPO_DIR" cat-file -e "$SB^{commit}" 2>/dev/null || continue
  if [ -z "$FALLBACK_BASE" ]; then
    FALLBACK_BASE="$SB"
  else
    # older = ancestor of the current pick (linear history), else compare dates
    if git -C "$REPO_DIR" merge-base --is-ancestor "$SB" "$FALLBACK_BASE" 2>/dev/null; then
      FALLBACK_BASE="$SB"
    elif [ "$(git -C "$REPO_DIR" show -s --format=%ct "$SB")" -lt "$(git -C "$REPO_DIR" show -s --format=%ct "$FALLBACK_BASE")" ]; then
      FALLBACK_BASE="$SB"
    fi
  fi
done <<EOF
$STAMPS
EOF

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
