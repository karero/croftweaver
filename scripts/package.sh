#!/usr/bin/env bash
# Build the handoff zip from the canonical skills/. Replaces the old hand-rebuilt
# zip — run this instead of editing a separate package copy.
set -euo pipefail

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
OUT="$REPO_DIR/dist"
mkdir -p "$OUT"
rm -f "$OUT/croftweaver.zip" "$OUT/website-builder.zip"   # also clears a zip built under the old name

find "$REPO_DIR" -name .DS_Store -delete 2>/dev/null || true
cd "$REPO_DIR"
# Explicit file list (not the scripts/ dir) so the gitignored scripts/.clean-denylist
# can never leak into the handoff. LICENSE + THIRD-PARTY-LICENSES.md ship the notices the
# README points to; Makefile makes `make install` work for a zip recipient. .gitattributes keeps
# scripts LF for a recipient who commits the unzipped folder to a new repo and later clones it on
# Windows: the zip itself has no checkout to convert, but that repo would.
# docs/reviews/ holds internal review trails + plan artifacts — never handoff material.
# docs/BUGLOG.md and docs/DECISIONS_PENDING.md are the maintainer's own trackers: they cite
# docs/reviews/ files the zip does not hold, and a recipient has no use for them.
# docs/local/ is excluded from git entirely (.git/info/exclude) for private, never-shipped
# notes — but zip -r is git-agnostic and would sweep it in anyway if it exists on disk.
# node_modules/, .astro/, __pycache__/, and test-results/ are the same class of leak: all
# gitignored (skills/new-website/templates/.gitignore + root .gitignore), so git itself never
# tracks them, but zip -r doesn't consult .gitignore either — if a template's build/test/install
# byproducts happen to exist on the machine building the release (e.g. from a prior `npm
# test`/`npm install`/`npm run build`/pytest run against the real template tree instead of a
# scratch clone), the whole tree ships in the handoff. Caught live 2026-08-09: a stray
# node_modules from an unrelated earlier session balanced a 201-file zip into 9324 files (185MB)
# before that exclusion existed; caught live 2026-08-29 (v0.23 release prep) for the other three.
zip -r -X "$OUT/croftweaver.zip" \
  skills docs README.md LICENSE THIRD-PARTY-LICENSES.md SECURITY.md Makefile .gitattributes \
  scripts/install.sh scripts/install-codex.sh scripts/check_clean.sh scripts/package.sh \
  scripts/whats-new.sh scripts/check_model_agnostic.sh scripts/check_skill_budgets.sh \
  scripts/test_install_pin.sh scripts/test_whats_new_removed_skill.sh scripts/check_template_coverage.sh scripts/check_cdpath_safe.sh \
  scripts/test_package_leak.sh scripts/check_pipefail_pipes.sh \
  scripts/test_pre_push_hook.sh scripts/test_verify.sh scripts/test_clean_denylist.sh scripts/test_git_stand_hook.sh scripts/test_whats_new.sh \
  scripts/test_mktemp_guard.sh scripts/check_lf_checkout.sh scripts/list_shell_scripts.sh \
  -x '*.DS_Store' '*/dist/*' 'docs/reviews/*' 'docs/local/*' '*/node_modules/*' \
     'docs/BUGLOG.md' 'docs/DECISIONS_PENDING.md' \
     '*/.astro/*' '*/__pycache__/*' '*/test-results/*' >/dev/null

echo "built $OUT/croftweaver.zip"
unzip -l "$OUT/croftweaver.zip" | tail -1

# Integrity check: a handoff zip missing any of these is broken (legal notices, install
# path, the orchestrator, the architecture doc it points at, and every root file the
# orchestrator's §3 step 2 copies into a site — a zip missing one scaffolds a broken repo — plus
# the on-demand team skill and its guide, which §3 also copies). Fail loud if so.
REQUIRED=(
  README.md
  LICENSE
  THIRD-PARTY-LICENSES.md
  SECURITY.md
  Makefile
  .gitattributes
  scripts/install.sh
  scripts/install-codex.sh
  scripts/check_clean.sh
  scripts/package.sh
  scripts/whats-new.sh
  scripts/check_model_agnostic.sh
  scripts/check_skill_budgets.sh
  scripts/test_install_pin.sh
  scripts/test_whats_new_removed_skill.sh
  scripts/check_template_coverage.sh
  scripts/check_cdpath_safe.sh
  scripts/test_package_leak.sh
  scripts/check_pipefail_pipes.sh
  scripts/test_pre_push_hook.sh
  scripts/test_verify.sh
  scripts/test_clean_denylist.sh
  scripts/test_git_stand_hook.sh
  scripts/test_whats_new.sh
  scripts/test_mktemp_guard.sh
  scripts/check_lf_checkout.sh
  scripts/list_shell_scripts.sh
  skills/independent-review/scripts/test_failed_tier_report.sh
  skills/independent-review/scripts/check_perl_minimum.sh
  skills/independent-review/scripts/perl/melious_key.pl
  skills/independent-review/scripts/perl/melious_request.pl
  skills/independent-review/scripts/perl/melious_stream.pl
  skills/independent-review/scripts/perl/ollama_filter.pl
  skills/independent-review/scripts/perl/ollama_request.pl
  skills/independent-review/scripts/perl/ollama_stream.pl
  skills/independent-review/scripts/perl/readable_tail.pl
  docs/ANTIGRAVITY.md
  docs/ANTIGRAVITY-TEST.md
  docs/CODEX.md
  docs/CODEX-TEST.md
  skills/new-website/SKILL.md
  skills/new-website/references/WEBSITE_ARCHITECTURE.md
  skills/new-website/templates/PUBLISHING.md
  skills/new-website/templates/SETUP.md
  skills/new-website/templates/.gitignore
  skills/new-website/templates/claude/settings.json
  skills/new-website/templates/claude/hooks/git-stand.mjs
  skills/new-website/templates/AGENTS.md
  skills/new-website/templates/CLAUDE.md
  skills/website-team-setup/SKILL.md
  skills/website-team-setup/templates/TEAM-GUIDE.md
)
zipfiles="$(unzip -Z1 "$OUT/croftweaver.zip")"
missing=0
for f in "${REQUIRED[@]}"; do
  grep -Fxq "$f" <<<"$zipfiles" || { echo "✗ MISSING from zip: $f"; missing=1; }
done
if [ "$missing" -ne 0 ]; then
  echo "FAIL — handoff zip is incomplete (see ✗ above)."
  exit 1
fi

# leak_check <ERE> <what> [hint] — fail if any zip entry matches: print the first five, then
# the count. awk reads the whole listing and exits 0 whether or not anything matched. This was
# `grep … | head -5 | grep .`, tested by pipeline status: once a leak's listing passed the pipe
# buffer (~64 KiB), head's early exit killed grep, pipefail reported that, and the guard missed
# exactly the large leak it exists for. A non-zero status now can only be an error (the
# herestring's temp file not created, say), so it fails closed rather than reading as clean.
# The patterns carry no backslashes: awk -v would unescape them.
leak_check() {
  local out n
  out="$(awk -v re="$1" '$0 ~ re { if (++n <= 5) print } END { print n + 0 }' <<<"$zipfiles")" \
    || { echo "FAIL — could not scan the zip listing for $2."; exit 1; }
  n="${out##*$'\n'}"
  [ "$n" = 0 ] && return 0
  printf '%s\n' "${out%$'\n'*}"
  echo "FAIL — $n $2 leaked into the handoff zip (first 5 above).${3:+ $3}"
  exit 1
}
# Internal artifacts must never ship: fail loud if any slip past the exclusions.
leak_check '^docs/reviews/|^REVIEW-|^SKILL-PLAN-' "internal review/plan artifact(s)"
leak_check '^docs/(BUGLOG|DECISIONS_PENDING)[.]md$' "maintainer tracker file(s)"
# Belt-and-suspenders on the node_modules exclusion above: catch it here too rather than
# trusting the -x glob alone (the docs/reviews/local exclusions get this same double-check).
leak_check '/node_modules/' "node_modules path(s)" \
  "Was it installed locally before building this release?"
echo "zip integrity OK — all critical files present, no internal artifacts"
