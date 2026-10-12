#!/usr/bin/env bash
# Regression guard for the analytics switch in src/config.ts:
#   ANALYTICS.enabled = process.env.CF_PAGES_BRANCH === PROD_BRANCH
#
# Base.astro emits the Plausible <script> only when that is true, and the build decides it:
# Cloudflare sets CF_PAGES_BRANCH when it builds, and a deploy-by-command owner sets it by
# hand (`CF_PAGES_BRANCH=<production-branch> npm run build` for the live site, PUBLISHING.md;
# `CF_PAGES_BRANCH= npm run build` for a preview, new-website's CLOUDFLARE_FIRST_DEPLOY.md).
# Both ways it fails silently: off on the live site, it counts no visitors and nothing says
# so; on for a preview, every look at the preview is counted as a real visitor. The
# Playwright suite cannot see either, since it builds once with whatever the shell had. So
# this builds the site four ways, the way the docs tell the owner to, and reads the built
# HTML. The toolkit's own CI runs it (template-tests.yml); a site's CI does not.
#
# It runs `astro build`, the step of `npm run build` that renders the pages and so decides
# the tag, into a temporary folder: the site's own dist/ is left alone. The two post-build
# steps after it touch heading ids and dist/build.txt only.
#
# Needs `npm ci` first. Each build takes a few seconds.
set -euo pipefail
CDPATH= cd -- "$(dirname -- "$0")/.."

# The production branch as this site names it ('production', or 'main' on a single-stage
# site), read from the line the gate compares against.
prod="$(sed -nE "s/^export const PROD_BRANCH = ['\"]([^'\"]*)['\"];?.*/\1/p" src/config.ts)"
if [ -z "$prod" ]; then
  echo "✗ analytics gate: no \"export const PROD_BRANCH = '…';\" line in src/config.ts to test against."
  exit 1
fi
# A branch Cloudflare builds as a preview: main on a two-stage site.
preview=main
[ "$prod" != main ] || preview=preview

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

fail=0
checked=0

# build <case> <unset|set> [value] — one `astro build` into $work/<case>, with
# CF_PAGES_BRANCH unset or set to value (which may be empty). Every case sets or unsets
# it explicitly, so a value in the calling shell cannot leak into a case.
astro=./node_modules/.bin/astro
if [ ! -x "$astro" ]; then
  echo "✗ analytics gate: $astro not found. Run npm ci first."
  exit 1
fi
build() {
  local name="$1" how="$2" value="${3-}" rc=0
  if [ "$how" = unset ]; then
    env -u CF_PAGES_BRANCH "$astro" build --outDir "$work/$name" >"$work/$name.log" 2>&1 || rc=$?
  else
    CF_PAGES_BRANCH="$value" "$astro" build --outDir "$work/$name" >"$work/$name.log" 2>&1 || rc=$?
  fi
  if [ "$rc" -ne 0 ]; then
    echo "✗ analytics gate: the $name build failed (exit $rc). Its last lines:"
    tail -n 20 "$work/$name.log"
    exit 1
  fi
  if [ ! -f "$work/$name/index.html" ]; then
    echo "✗ analytics gate: the $name build made no index.html in $work/$name."
    exit 1
  fi
}

# The tags Base.astro writes: <script async src="<scriptHost>/js/pa-<id>.js"> and, after it,
# an inline stub that calls plausible.init() (the per-site script starts only on that call).
# For each page, prints "<full> <part> <path>": how many working tags it has (the script AND
# the stub) and how many pieces of a tag it has at all (the script, the stub, or a leftover
# of the older script.js / data-domain form, which this template no longer writes).
# HTML comments are dropped first, and attributes are read one at a time, so text inside a
# quoted value never counts as an attribute and <script-x> is not a script. It reads the
# markup Astro emits from this template; it is not an HTML parser, so a script tag spelled
# out inside another attribute's value or inside a script's code would fool it.
tags_program() {
  cat <<'PERL'
for my $file (@ARGV) {
  open(my $fh, '<', $file) or die "cannot read $file: $!\n";
  local $_ = do { local $/; <$fh> };
  close($fh) or die "cannot finish reading $file: $!\n";
  $_ = '' unless defined;
  s/<!--.*?-->//gs;
  my ($full, $part) = (0, 0);
  my $init = /plausible\.init\(\)/ ? 1 : 0;
  while (/<script(?=[\s\/>])/gi) {
    my %a;
    while (/\G\s*([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/gc) {
      $a{lc $1} = defined $2 ? $2 : defined $3 ? $3 : defined $4 ? $4 : '';
    }
    my $src = exists $a{src} && $a{src} =~ m{/js/pa-[\w-]+\.js(?:[?#]|$)};
    my $old = exists $a{src} && $a{src} =~ m{/js/script(?:\.[\w.-]+)?\.js(?:[?#]|$)};
    $full++ if $src && $init;
    $part++ if $src || $old || exists $a{'data-domain'};
  }
  $part += $init;
  print "$full $part $file\n";
}
PERL
}
# Every page gets exactly one line, or the check fails: a page that could not be read
# must not drop out of the count.
count_tags() {
  local dir="$1" out pages lines
  out="$(find "$dir" -name '*.html' -exec perl -e "$(tags_program)" {} +)" || return 1
  pages="$(find "$dir" -name '*.html' | wc -l | tr -d ' ')"
  lines="$(printf '%s\n' "$out" | grep -c . || true)"
  [ "$pages" -gt 0 ] && [ "$pages" = "$lines" ] || return 1
  printf '%s\n' "$out"
}

# On means on for every page: every page is built from Base.astro.
expect_on() {
  local name="$1" what="$2" counts missing
  checked=$((checked + 1))
  counts="$(count_tags "$work/$name")" || { echo "✗ $what: could not read the built pages."; fail=1; return; }
  missing="$(printf '%s\n' "$counts" | awk '$1 == 0 { sub(/^[^ ]* [^ ]* /, ""); print }')"
  if [ -z "$missing" ]; then
    echo "✓ $what: analytics script on every page"
  else
    echo "✗ $what: NO analytics script on these pages — the live site would not count their visitors:"
    while IFS= read -r page; do printf '    %s\n' "${page#"$work/$name/"}"; done <<< "$missing"
    fail=1
  fi
}

# Off means no analytics tag, nor half of one, on any page.
expect_off() {
  local name="$1" what="$2" counts hits
  checked=$((checked + 1))
  counts="$(count_tags "$work/$name")" || { echo "✗ $what: could not read the built pages."; fail=1; return; }
  hits="$(printf '%s\n' "$counts" | awk '$2 > 0 { sub(/^[^ ]* [^ ]* /, ""); print }')"
  if [ -z "$hits" ]; then
    echo "✓ $what: no analytics script on any page"
  else
    echo "✗ $what: an analytics tag, or half of one, on these pages."
    echo "  (A full tag counts every visit to this build as real.)"
    while IFS= read -r page; do printf '    %s\n' "${page#"$work/$name/"}"; done <<< "$hits"
    fail=1
  fi
}

build live set "$prod"
expect_on live "CF_PAGES_BRANCH=$prod (the live build)"

build unset unset
expect_off unset "CF_PAGES_BRANCH unset (a plain npm run build)"

build empty set ""
expect_off empty "CF_PAGES_BRANCH= (a preview by command)"

build preview set "$preview"
expect_off preview "CF_PAGES_BRANCH=$preview (a preview branch)"

if [ "$fail" -eq 0 ]; then
  echo "✓ analytics gate: $checked builds, on only when CF_PAGES_BRANCH is '$prod'"
fi
exit "$fail"
