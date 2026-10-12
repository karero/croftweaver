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
# What it checks, in order:
#   1. Its own counter, on hand-made pages (a tag mentioned in a paragraph is not a tag), and
#      the check that runs an init stub (a stub in a comment or a string does not start it).
#   2. That public/_headers lists the script's host as a whole token in script-src and
#      connect-src (and in script-src-elem when that is written out). `astro preview` does
#      not apply _headers, so no other test sees a script the browser would block.
#   3. Four builds: on for the live build, with exactly one script tag and one init stub on
#      every page, every stub running (a spy on plausible.init is called), and a CSP that
#      lets the stub run: 'unsafe-inline' alone in the directive, or the stub's own sha256
#      hash. Off for the other three, with no tag, no half of one and no mention of the
#      script's path or id.
# What it cannot check: it compares the build with src/config.ts, so a wrong scriptId typed
# INTO config.ts passes. Only the installer's "Verify" step catches that. It does not
# evaluate a CSP the way a browser does: a policy that leans on default-src, a nonce, or
# 'strict-dynamic' for these directives fails here, on purpose, and needs this check
# extended first.
#
# It runs `astro build`, the step of `npm run build` that renders the pages and so decides
# the tag, into a temporary folder: the site's own dist/ is left alone. The two post-build
# steps after it touch heading ids and dist/build.txt only.
#
# Needs `npm ci` first, and Node (which the build needs anyway). Each build takes a few seconds.
set -euo pipefail
CDPATH= cd -- "$(dirname -- "$0")/.."

if ! command -v node >/dev/null 2>&1; then
  echo "✗ analytics gate: node is not on the PATH; the init-stub check needs it."
  exit 1
fi

# The production branch as this site names it ('production', or 'main' on a single-stage
# site), read from the line the gate compares against.
prod="$(sed -nE "s/^export const PROD_BRANCH = ['\"]([^'\"]*)['\"];?.*/\1/p" src/config.ts)"
if [ -z "$prod" ]; then
  echo "✗ analytics gate: no \"export const PROD_BRANCH = '…';\" line in src/config.ts to test against."
  exit 1
fi
# The script address Base.astro must write: <scriptHost>/js/<scriptId>.js, read from the
# same file, so Base.astro cannot drift from config.ts.
host="$(sed -nE "s/^[[:space:]]*scriptHost:[[:space:]]*['\"]([^'\"]*)['\"].*/\1/p" src/config.ts)"
id="$(sed -nE "s/^[[:space:]]*scriptId:[[:space:]]*['\"]([^'\"]*)['\"].*/\1/p" src/config.ts)"
if [ -z "$host" ] || [ -z "$id" ]; then
  echo "✗ analytics gate: no scriptHost: '…' and scriptId: '…' lines in src/config.ts to test against."
  exit 1
fi
host="${host%/}"
ANALYTICS_SRC="${host}/js/${id}.js"
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
#   stub:   inline JavaScript <script> tags whose code mentions a call plausible.init(...);
#   other:  tags of an analytics script that is not that one: the older script.js form, a
#           per-site script with another address, or a data-domain attribute.
# HTML comments are dropped first, and attributes are read one at a time, so text inside a
# quoted value never counts as an attribute and <script-x> is not a script. The stub is read
# only inside an inline script tag, so a paragraph, a <code> block or a JSON-LD string that
# mentions plausible.init() does not count. A mention inside the script's own code (a
# comment, a string) does count here; stub_runs below is what catches that. With
# ANALYTICS_STUB_OUT set, the first stub's code is also written to that file. It reads the
# markup Astro emits from this template; it is not an HTML parser.
tags_program() {
  cat <<'PERL'
my $want = $ENV{ANALYTICS_SRC} // '';
die "ANALYTICS_SRC is empty\n" if $want eq '';
my $out = $ENV{ANALYTICS_STUB_OUT} // '';
my $wrote = 0;
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
      if (/\G[^>]*>(.*?)<\/script\b/gcsi) {
        my $body = $1;
        my $type = lc($a{type} // '');
        if (($type eq '' || $type =~ m{^(?:text/javascript|application/javascript|module)$})
            && $body =~ /\bplausible\.init\s*\(/) {
          $stub++;
          if ($out ne '' && !$wrote++) {
            open(my $o, '>', $out) or die "cannot write $out: $!\n";
            print $o $body;
            close($o) or die "cannot finish writing $out: $!\n";
          }
        }
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

# stub_runs <page>: extracts the page's first init stub and runs it twice in a bare
# JavaScript context (document, location, navigator and the storage objects are inert
# stand-ins). First with a spy already installed as plausible.init: the spy must be called,
# so a call in a comment or a string, or a stub that never reaches the call, fails. Then
# with nothing installed: the stub must define plausible and plausible.init itself.
# What it prints on failure is the first line of the error, if the code threw.
stub_runs() {
  local page="$1" out="$work/stub.js" err="$work/stub.err"
  rm -f "$out" "$err"
  ANALYTICS_STUB_OUT="$out" perl -e "$(tags_program)" "$page" >/dev/null || return 1
  [ -s "$out" ] || return 1
  node -e '
    const vm = require("node:vm"), fs = require("node:fs");
    const code = fs.readFileSync(process.argv[1], "utf8");
    function run(seedSpy) {
      let calls = 0;
      const ctx = {
        document: { documentElement: { lang: "en", getAttribute() { return null; } }, referrer: "", cookie: "",
                    addEventListener() {}, querySelector() { return null; } },
        location: { hostname: "example.com", host: "example.com", href: "https://example.com/", pathname: "/", search: "", protocol: "https:" },
        navigator: { userAgent: "analytics-gate", webdriver: false },
        localStorage: { getItem() { return null; }, setItem() {} },
        sessionStorage: { getItem() { return null; }, setItem() {} },
      };
      ctx.window = ctx; ctx.self = ctx; ctx.globalThis = ctx;
      if (seedSpy) { const f = function () {}; f.init = function () { calls++; }; ctx.plausible = f; }
      vm.createContext(ctx);
      vm.runInContext(code, ctx, { timeout: 2000 });
      return { ctx, calls };
    }
    try {
      const seeded = run(true), plain = run(false);
      const ok = seeded.calls >= 1 && typeof plain.ctx.plausible === "function" && typeof plain.ctx.plausible.init === "function";
      if (!ok) console.error("the stub did not call plausible.init, or did not define plausible and plausible.init");
      process.exit(ok ? 0 : 1);
    } catch (e) { console.error(String(e).split("\n")[0]); process.exit(1); }
  ' "$out" >/dev/null 2>"$err"
}

# The counter's own check: each hand-made page below must read as the counts beside it,
# and the stub check must tell a stub that runs from one that only mentions the call.
selftest() {
  local dir="$work/fixtures" want_line got name expect n=0
  mkdir -p "$dir"
  local s="<script async src=\"$ANALYTICS_SRC\"></script>"
  local i="<script>window.plausible=window.plausible||function(){};plausible.init=plausible.init||function(o){plausible.o=o||{}};plausible.init()</script>"
  fixture() { printf '<!doctype html><html><head>%s</head><body>%s</body></html>' "$2" "$3" >"$dir/$1.html"; }
  fixture both       "$s$i" ''
  fixture script     "$s" ''
  fixture stub       "$i" ''
  fixture none       '' ''
  fixture mention    "$s" '<p>call plausible.init() first</p><pre><code>plausible.init()</code></pre>'
  fixture options    "$s<script>window.plausible=window.plausible||function(){};plausible.init=plausible.init||function(o){plausible.o=o||{}};plausible.init({ outboundLinks: false })</script>" ''
  fixture spaced     "$s<script>plausible.init( )</script>" ''
  fixture upper      "$s<SCRIPT>plausible.init()</SCRIPT>" ''
  fixture jsonld     '<script type="application/ld+json">{"x":"plausible.init()"}</script>' ''
  fixture comment    '<!-- <script>plausible.init()</script> -->' ''
  fixture oldform    '<script defer data-domain="example.com" src="https://h.example/js/script.js"></script>' ''
  fixture oldext     '<script defer src="https://h.example/js/script.outbound-links.js"></script>' ''
  fixture wrongid    "<script async src=\"${host}/js/pa-WRONG.js\"></script>$i" ''
  fixture queryform  "<script async src=\"${host}/js/pa-selftest.js?v=2\"></script>$i" ''
  fixture twice      "$s$s$i" ''
  fixture jscomment  "$s<script>// plausible.init()</script>" ''
  fixture jsstring   "$s<script>var s = \"plausible.init()\";</script>" ''
  fixture fakeinit   "$s<script>window.plausible=function(){};plausible.init=function(){};plausible.o={};// plausible.init()</script>" ''
  fixture usesdoc    "$s<script>window.plausible=window.plausible||function(){};plausible.init=plausible.init||function(o){plausible.o=o||{}};plausible.init({customProperties:{lang:document.documentElement.lang}})</script>" ''
  # name:expected counts "<script> <stub> <other>"
  for expect in both:'1 1 0' script:'1 0 0' stub:'0 1 0' none:'0 0 0' mention:'1 0 0' options:'1 1 0' \
                spaced:'1 1 0' upper:'1 1 0' jsonld:'0 0 0' comment:'0 0 0' oldform:'0 0 1' oldext:'0 0 1' \
                wrongid:'0 1 1' queryform:'0 1 1' twice:'2 1 0' jscomment:'1 1 0' jsstring:'1 1 0' \
                fakeinit:'1 1 0' usesdoc:'1 1 0'; do
    name="${expect%%:*}"; want_line="${expect#*:}"
    n=$((n + 1))
    got="$(perl -e "$(tags_program)" "$dir/$name.html" | awk '{print $1, $2, $3}')"
    if [ "$got" != "$want_line" ]; then
      echo "✗ analytics gate: its own counter read the '$name' fixture as '$got', not '$want_line'."
      fail=1
    fi
  done
  for expect in both:yes options:yes usesdoc:yes jscomment:no jsstring:no fakeinit:no stub:yes script:no; do
    name="${expect%%:*}"; want_line="${expect#*:}"
    got=no
    if stub_runs "$dir/$name.html"; then got=yes; fi
    if [ "$got" != "$want_line" ]; then
      echo "✗ analytics gate: its stub check said '$got' for the '$name' fixture, not '$want_line'."
      fail=1
    fi
  done
  if [ "$fail" -ne 0 ]; then exit 1; fi
  echo "✓ analytics gate: the counter reads its $n fixture pages as expected, and the stub check tells a running stub from a mention"
}

# csp_tokens <policy> <directive>: the directive's source tokens, one per line. The name is
# compared in lower case and must match exactly, so script-src-elem is not script-src. A
# directive written twice counts once: the first wins in a browser.
csp_tokens() {
  awk -v dir="$2" 'BEGIN { RS = ";" }
    { n = split($0, t, /[ \t\r\n]+/); i = 1
      while (i <= n && t[i] == "") i++
      if (i <= n && tolower(t[i]) == dir && !seen) { seen = 1; for (j = i + 1; j <= n; j++) if (t[j] != "") print t[j] } }' <<<"$1"
}

# host_listed <tokens>: true when the script's origin is among the source tokens, spelled
# as the config has it, scheme-less, with :443, with a trailing slash, or as a wildcard
# subdomain of the same domain. A token with a path below "/" would block the script or its
# POST, so it does not count.
host_listed() {
  local tokens="$1" token bare="${host#https://}" suffix
  while IFS= read -r token; do
    [ -n "$token" ] || continue
    token="${token%/}"
    case "$token" in
      "$host"|"$host:443"|"$bare"|"$bare:443") return 0 ;;
      https://\*.*|\*.*)
        suffix="${token#https://}"; suffix="${suffix#\*}"
        case "$bare" in *"$suffix") return 0 ;; esac ;;
    esac
  done <<<"$tokens"
  return 1
}

# Every Content-Security-Policy line in public/_headers must list the script's origin in
# script-src and connect-src, and in script-src-elem when that is written out (it governs
# <script> elements). Whether the inline stub may run is checked after the live build,
# against the stub's real text: csp_inline_check.
csp_check() {
  local lines line policy dir tokens
  if [ ! -f public/_headers ]; then
    echo "✗ analytics gate: no public/_headers to check the Content-Security-Policy in."
    fail=1
    return
  fi
  lines="$(grep -E '^[[:space:]]*Content-Security-Policy:' public/_headers || true)"
  if [ -z "$lines" ]; then
    echo "✗ analytics gate: public/_headers has no Content-Security-Policy line."
    fail=1
    return
  fi
  while IFS= read -r line; do
    policy="${line#*:}"
    for dir in script-src connect-src script-src-elem; do
      tokens="$(csp_tokens "$policy" "$dir")"
      if [ -z "$tokens" ]; then
        if [ "$dir" != script-src-elem ]; then
          echo "✗ analytics gate: this Content-Security-Policy in public/_headers has no $dir directive written out: ${policy:0:90}…"
          fail=1
        fi
      elif host_listed "$tokens"; then
        echo "✓ analytics gate: public/_headers lists $host in $dir"
      else
        echo "✗ analytics gate: $dir in public/_headers does not list $host as a token, so the browser would block the analytics script: ${policy:0:90}…"
        fail=1
      fi
    done
  done <<<"$lines"
}

# csp_inline_check <stub-file>: the directive that governs <script> elements (script-src-elem
# if written out, else script-src) must let the built stub run: 'unsafe-inline' with no hash
# and no nonce in the same directive (a browser ignores 'unsafe-inline' next to either), or
# the sha256 hash of the stub's exact text. A nonce cannot match in a static _headers file.
csp_inline_check() {
  local stub="$1" lines line policy tokens dir hash
  hash="$(node -e 'process.stdout.write(require("node:crypto").createHash("sha256").update(require("node:fs").readFileSync(process.argv[1])).digest("base64"))' "$stub")"
  lines="$(grep -E '^[[:space:]]*Content-Security-Policy:' public/_headers || true)"
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    policy="${line#*:}"
    dir=script-src-elem
    tokens="$(csp_tokens "$policy" script-src-elem)"
    if [ -z "$tokens" ]; then dir=script-src; tokens="$(csp_tokens "$policy" script-src)"; fi
    if grep -qiE "^'(sha(256|384|512)|nonce)-" <<<"$tokens"; then
      if grep -qF -- "'sha256-$hash'" <<<"$tokens"; then
        echo "✓ analytics gate: $dir carries the sha256 hash of the init stub"
      else
        echo "✗ analytics gate: $dir in public/_headers has a hash or nonce but not 'sha256-$hash', the hash of the built init stub, so the browser would block the stub. Change the stub and the hash together."
        fail=1
      fi
    elif grep -qiF -- "'unsafe-inline'" <<<"$tokens"; then
      echo "✓ analytics gate: $dir allows inline scripts, so the init stub runs"
    else
      echo "✗ analytics gate: $dir in public/_headers allows no inline script ('unsafe-inline', or the stub's sha256 hash): the init stub would be blocked."
      fail=1
    fi
  done <<<"$lines"
}

# On means on for every page: every page is built from Base.astro.
expect_on() {
  local name="$1" what="$2" counts missing page bad=""
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
    return
  fi
  # Every page's stub must run, not only the home page's.
  while IFS= read -r page; do
    if ! stub_runs "$page"; then bad="$bad"$'\n'"    ${page#"$work/$name/"}: $(cat "$work/stub.err" 2>/dev/null)"; fi
  done < <(find "$work/$name" -name '*.html' | sort)
  if [ -z "$bad" ]; then
    echo "✓ $what: the init stub on every page runs and calls plausible.init()"
    stub_runs "$work/$name/index.html" || true
  else
    echo "✗ $what: the init stub does not run and call plausible.init() (in a bare JavaScript context) on these pages:$bad"
    fail=1
  fi
}

# Off means no analytics tag, nor half of one, on any page, and no mention of the script's
# path or id anywhere in the build (a preload link, a script made at runtime). The path and
# the id are specific; the host alone may be a site's own origin or a service it links to.
# _headers is skipped: it names the host in the CSP on purpose.
expect_off() {
  local name="$1" what="$2" counts hits extra
  checked=$((checked + 1))
  counts="$(count_tags "$work/$name")" || { echo "✗ $what: could not read the built pages."; fail=1; return; }
  hits="$(printf '%s\n' "$counts" | awk '$1 > 0 || $2 > 0 || $3 > 0 { path = $0; sub(/^[^ ]* [^ ]* [^ ]* /, "", path); print path }')"
  extra="$(grep -rlF --exclude=_headers -e "/js/${id}.js" -e "$id" "$work/$name" 2>/dev/null || true)"
  hits="$(awk 'NF && !seen[$0]++' <<<"$hits"$'\n'"$extra")"
  if [ -z "$hits" ]; then
    echo "✓ $what: no analytics script on any page"
  else
    echo "✗ $what: an analytics tag, half of one, or the script's path or id, in these files."
    echo "  (A full tag counts every visit to this build as real.)"
    while IFS= read -r page; do printf '    %s\n' "${page#"$work/$name/"}"; done <<< "$hits"
    fail=1
  fi
}

selftest
csp_check

build live set "$prod"
expect_on live "CF_PAGES_BRANCH=$prod (the live build)"
if [ -s "$work/stub.js" ]; then csp_inline_check "$work/stub.js"; fi

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
