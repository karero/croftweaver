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
# Before the builds it feeds a few hand-made pages to its own counter and stops if the
# counter misreads one (a tag mentioned in a paragraph is not a tag), so a loose counter
# cannot pass a build it should fail.
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
# The script address Base.astro must write: <scriptHost>/js/<scriptId>.js, read from the
# same file, so a mistyped host or id on the live build fails here and not in silence.
host="$(sed -nE "s/^[[:space:]]*scriptHost:[[:space:]]*['\"]([^'\"]*)['\"].*/\1/p" src/config.ts)"
id="$(sed -nE "s/^[[:space:]]*scriptId:[[:space:]]*['\"]([^'\"]*)['\"].*/\1/p" src/config.ts)"
if [ -z "$host" ] || [ -z "$id" ]; then
  echo "✗ analytics gate: no scriptHost: '…' and scriptId: '…' lines in src/config.ts to test against."
  exit 1
fi
ANALYTICS_SRC="${host%/}/js/${id}.js"
export ANALYTICS_SRC
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

# The tags Base.astro writes: <script async src="<scriptHost>/js/<scriptId>.js"> and, after
# it, an inline <script> that calls plausible.init() (the per-site script starts only on
# that call). For each page, prints "<script> <stub> <other> <path>":
#   script: <script> tags whose src is exactly $ANALYTICS_SRC;
#   stub:   inline JavaScript <script> tags whose code calls plausible.init(...);
#   other:  tags of an analytics script that is not that one: the older script.js form, a
#           per-site script with another address, or a data-domain attribute.
# HTML comments are dropped first, and attributes are read one at a time, so text inside a
# quoted value never counts as an attribute and <script-x> is not a script. The stub is read
# only inside an inline script tag, so a paragraph, a <code> block or a JSON-LD string that
# mentions plausible.init() does not count. It reads the markup Astro emits from this
# template; it is not an HTML parser.
tags_program() {
  cat <<'PERL'
my $want = $ENV{ANALYTICS_SRC} // '';
die "ANALYTICS_SRC is empty\n" if $want eq '';
for my $file (@ARGV) {
  open(my $fh, '<', $file) or die "cannot read $file: $!\n";
  local $_ = do { local $/; <$fh> };
  close($fh) or die "cannot finish reading $file: $!\n";
  $_ = '' unless defined;
  s/<!--.*?-->//gs;
  my ($script, $stub, $other) = (0, 0, 0);
  while (/<script(?=[\s\/>])/gi) {
    my %a;
    while (/\G\s*([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/gc) {
      $a{lc $1} = defined $2 ? $2 : defined $3 ? $3 : defined $4 ? $4 : '';
    }
    if (exists $a{src}) {
      if ($a{src} eq $want) { $script++ }
      elsif ($a{src} =~ m{/js/(?:script(?:\.[\w.-]+)?|pa-[\w-]+)\.js(?:[?#]|$)}) { $other++ }
      elsif (exists $a{'data-domain'}) { $other++ }
    } else {
      $other++ if exists $a{'data-domain'};
      if (/\G[^>]*>(.*?)<\/script\b/gcs) {
        my $body = $1;
        my $type = lc($a{type} // '');
        if (($type eq '' || $type =~ m{^(?:text/javascript|application/javascript|module)$})
            && $body =~ /\bplausible\.init\s*\(/) { $stub++ }
      }
    }
  }
  print "$script $stub $other $file\n";
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

# The counter's own check: each hand-made page below must read as the counts beside it.
selftest() {
  local dir="$work/fixtures" want_line got name expect n=0
  mkdir -p "$dir"
  local s="<script async src=\"$ANALYTICS_SRC\"></script>"
  local i="<script>window.plausible=window.plausible||function(){};plausible.init()</script>"
  fixture() { printf '<!doctype html><html><head>%s</head><body>%s</body></html>' "$2" "$3" >"$dir/$1.html"; }
  fixture both       "$s$i" ''
  fixture script     "$s" ''
  fixture stub       "$i" ''
  fixture none       '' ''
  fixture mention    "$s" '<p>call plausible.init() first</p><pre><code>plausible.init()</code></pre>'
  fixture options    "$s<script>plausible.init({ outboundLinks: false })</script>" ''
  fixture spaced     "$s<script>plausible.init( )</script>" ''
  fixture jsonld     '<script type="application/ld+json">{"x":"plausible.init()"}</script>' ''
  fixture comment    '<!-- <script>plausible.init()</script> -->' ''
  fixture oldform    '<script defer data-domain="example.com" src="https://h.example/js/script.js"></script>' ''
  fixture oldext     '<script defer src="https://h.example/js/script.outbound-links.js"></script>' ''
  fixture wrongid    "<script async src=\"${ANALYTICS_SRC%/*}/pa-WRONG.js\"></script>$i" ''
  fixture queryform  "<script async src=\"$ANALYTICS_SRC?v=2\"></script>$i" ''
  fixture twice      "$s$s$i" ''
  # name:expected counts "<script> <stub> <other>"
  for expect in both:'1 1 0' script:'1 0 0' stub:'0 1 0' none:'0 0 0' mention:'1 0 0' options:'1 1 0' \
                spaced:'1 1 0' jsonld:'0 0 0' comment:'0 0 0' oldform:'0 0 1' oldext:'0 0 1' \
                wrongid:'0 1 1' queryform:'0 1 1' twice:'2 1 0'; do
    name="${expect%%:*}"; want_line="${expect#*:}"
    n=$((n + 1))
    got="$(perl -e "$(tags_program)" "$dir/$name.html" | awk '{print $1, $2, $3}')"
    if [ "$got" != "$want_line" ]; then
      echo "✗ analytics gate: its own counter read the '$name' fixture as '$got', not '$want_line'."
      fail=1
    fi
  done
  if [ "$fail" -ne 0 ]; then exit 1; fi
  echo "✓ analytics gate: the counter reads its $n fixture pages as expected"
}

# The CSP in public/_headers must list the script's origin in script-src and connect-src: a
# host changed in config.ts and not there makes the browser block the script, and nothing says
# so. Pages cannot apply _headers under `astro preview`, so the Playwright suite never sees it.
csp_check() {
  local csp dir
  if [ ! -f public/_headers ]; then
    echo "✗ analytics gate: no public/_headers to check the Content-Security-Policy in."
    fail=1
    return
  fi
  csp="$(grep -E '^[[:space:]]*Content-Security-Policy:' public/_headers | head -n 1 || true)"
  if [ -z "$csp" ]; then
    echo "✗ analytics gate: public/_headers has no Content-Security-Policy line."
    fail=1
    return
  fi
  for dir in script-src connect-src; do
    if printf '%s\n' "$csp" | grep -Eo "(^|[ ;:])${dir}[^;]*" | grep -qF "${host%/}"; then
      echo "✓ analytics gate: public/_headers lists ${host%/} in $dir"
    else
      echo "✗ analytics gate: $dir in public/_headers does not list ${host%/}: the browser would block the analytics script."
      fail=1
    fi
  done
}

# On means on for every page: every page is built from Base.astro.
expect_on() {
  local name="$1" what="$2" counts missing
  checked=$((checked + 1))
  counts="$(count_tags "$work/$name")" || { echo "✗ $what: could not read the built pages."; fail=1; return; }
  missing="$(printf '%s\n' "$counts" | awk '$1 != 1 || $2 != 1 || $3 > 0 {
    path = $0; sub(/^[^ ]* [^ ]* [^ ]* /, "", path)
    why = ""
    if ($1 == 0) why = why " script missing;"
    if ($1 > 1) why = why " script written more than once;"
    if ($2 == 0) why = why " init stub missing;"
    if ($2 > 1) why = why " init stub written more than once;"
    if ($3 > 0) why = why " another or older analytics tag;"
    print path ":" why }')"
  if [ -z "$missing" ]; then
    echo "✓ $what: one analytics script and one init stub on every page"
  else
    echo "✗ $what: no working analytics tag on these pages, so the live site would not count their visitors"
    echo "  (expected <script async src=\"$ANALYTICS_SRC\"> and the plausible.init() stub):"
    while IFS= read -r page; do printf '    %s\n' "${page#"$work/$name/"}"; done <<< "$missing"
    fail=1
  fi
}

# Off means no analytics tag, nor half of one, on any page.
expect_off() {
  local name="$1" what="$2" counts hits
  checked=$((checked + 1))
  counts="$(count_tags "$work/$name")" || { echo "✗ $what: could not read the built pages."; fail=1; return; }
  hits="$(printf '%s\n' "$counts" | awk '$1 > 0 || $2 > 0 || $3 > 0 { path = $0; sub(/^[^ ]* [^ ]* [^ ]* /, "", path); print path }')"
  # Whatever form the tag takes (a preload link, a script made at runtime), the script's
  # host appears in the build. _headers is skipped: it lists the host in the CSP on purpose.
  hits="$hits$(grep -rlF --exclude=_headers -- "${host%/}" "$work/$name" 2>/dev/null || true)"
  if [ -z "$hits" ]; then
    echo "✓ $what: no analytics script on any page"
  else
    echo "✗ $what: an analytics tag, or half of one, on these pages."
    echo "  (A full tag counts every visit to this build as real.)"
    while IFS= read -r page; do printf '    %s\n' "${page#"$work/$name/"}"; done <<< "$hits"
    fail=1
  fi
}

selftest
csp_check

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
