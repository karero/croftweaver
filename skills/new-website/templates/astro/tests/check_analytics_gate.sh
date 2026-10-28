#!/usr/bin/env bash
# Regression guard for the analytics switch in src/config.ts:
#   ANALYTICS.enabled = USE_ANALYTICS && process.env.CF_PAGES_BRANCH === PROD_BRANCH
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
#   1. Its own counter, its email-link reader and its CSP reader, on hand-made pages and
#      policies (a tag mentioned in a paragraph is not a tag; a hash that is not the stub's
#      is not the stub's hash), and the check that runs an init stub (a stub in a comment or
#      a string does not start it).
#   2. That public/_headers lists the script's host as a whole token in script-src and
#      connect-src (and in script-src-elem when that is written out). `astro preview` does
#      not apply _headers, so no other test sees a script the browser would block.
#   3. Four builds: on for the live build, with exactly one script tag and one init stub on
#      every page, every stub running (a spy on plausible.init is called), and a CSP that
#      lets THE INIT STUB run: 'unsafe-inline' alone in the directive, or the stub's own
#      sha256 hash. Off for the other three, with no tag, no half of one and no mention of
#      the script's path or id. No build links to /go/email: the browser counts the tap.
#   4. In server mode (USE_ANALYTICS = true and ANALYTICS.mode = 'server' in src/config.ts),
#      steps 2 and 3 are replaced: the same four builds, all with no analytics tag (no page
#      loads the script, so _headers needs no analytics host); on the live build every email
#      link goes to /go/email, the Function that counts the tap, and on the other three none
#      does.
# With USE_ANALYTICS = false in src/config.ts (as the starter ships), steps 2 to 4
# turn around (the mode is then ignored): public/_headers must NOT list the host (with or without a path) in
# script-src, script-src-elem, connect-src or default-src, and all four builds, the live one
# included, must be off. A config.ts that never
# names USE_ANALYTICS (a site made before the switch) counts as true; one that names it
# but has no line in that form fails.
# What it cannot check:
#   - With analytics off, a link to the host that is not a script tag (a preconnect or
#     dns-prefetch added by hand) is not looked for, and no CSP stops one. Base.astro writes
#     none; a site that adds one must take it out with the switch.
#   - It compares the build with src/config.ts, so a wrong scriptId typed INTO config.ts
#     passes. Only the installer's "Verify" step catches that.
#   - It does not evaluate a CSP the way a browser does. A policy that leans on default-src, a
#     nonce or 'strict-dynamic' for these directives fails here, on purpose, and needs this
#     check extended first. A hash covers the init stub ONLY: the theme script and any other
#     inline script need their own hashes, and are not checked here.
#   - A loader that assembles the script's address from pieces at run time (host, "/js/" and
#     the id in separate strings) is not seen: the off-build check looks for the path and the
#     id written whole. Any other analytics script under /js/script*.js or /js/pa-*.js counts
#     as "another analytics tag".
#
# It runs `astro build`, the step of `npm run build` that renders the pages and so decides
# the tag, into a temporary folder: the site's own dist/ is left alone. The two post-build
# steps after it touch heading ids, dist/build.txt and dist/test-build-id.txt (written in test
# builds, removed otherwise).
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
# Whether the owner uses analytics at all. No line means a site made before the switch: on.
use="$(sed -nE "s/^export const USE_ANALYTICS = (true|false);?[[:space:]]*(\/\/.*)?$/\1/p" src/config.ts)"
if [ -z "$use" ]; then
  if grep -q 'USE_ANALYTICS' src/config.ts; then
    echo "✗ analytics gate: src/config.ts names USE_ANALYTICS, but not as one line \"export const USE_ANALYTICS = true;\" or \"= false;\" (a // comment after it is fine)."
    exit 1
  fi
  use=true
fi
case "$use" in
  true|false) ;;
  *) echo "✗ analytics gate: src/config.ts has more than one USE_ANALYTICS line."; exit 1 ;;
esac
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
# The mode: 'script' (the default, and what a config.ts from before the key existed means)
# or 'server', where the Pages Function counts and no page carries a tag.
mode="$(sed -nE "s/^[[:space:]]*mode:[[:space:]]*['\"]([a-z]+)['\"].*/\1/p" src/config.ts)"
mode="${mode:-script}"
if [ "$mode" != script ] && [ "$mode" != server ]; then
  echo "✗ analytics gate: mode in src/config.ts is '$mode'; expected 'script' or 'server'."
  exit 1
fi
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
# HTML comments are dropped first (never inside a script element, whose opening tag is read
# with its quoted values), and attributes are read one at a time, so text inside a quoted
# value never counts as an attribute and <script-x> is not a script. The stub is read
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
  s{(<script(?=[\s/>])(?:[^>"']|"[^"]*"|'[^']*')*>.*?</script\s*>)|<!--.*?-->}{defined $1 ? $1 : ''}gise;
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
# JavaScript context (document, location, navigator, the storage objects, addEventListener,
# setTimeout and matchMedia are inert stand-ins; anything else a stub touches throws, and
# the first line of the error is kept in $work/stub.err). First with a spy already
# installed as plausible.init: THAT spy must be called, so a call in a comment or a string,
# a stub that never reaches the call, or one that overwrites the installed init, fails (in a
# page where the script loads first, overwriting its init breaks it). Then with nothing
# installed: the stub must define plausible and plausible.init itself AND call it (the init
# property of whatever is stored as plausible is watched, so the stub's own init is counted,
# also when it is called through a variable that holds the same function), so a stub that
# only calls plausible.init(), or one whose own definition branch never calls it, fails.
# Not supported (such a stub may be rejected here; extend this check first): a stub that
# defines plausible or its init with Object.defineProperty, one that tests for init with `in`
# or Object.hasOwn before defining it (the watch gives the property to the function early),
# and one that keeps the init function in a variable BEFORE assigning plausible and calls it
# only from there.
stub_runs() {
  local page="$1" out="$work/stub.js" err="$work/stub.err"
  rm -f "$out" "$err"
  ANALYTICS_STUB_OUT="$out" perl -e "$(tags_program)" "$page" >/dev/null || return 1
  [ -s "$out" ] || return 1
  node -e '
    const vm = require("node:vm"), fs = require("node:fs");
    const code = fs.readFileSync(process.argv[1], "utf8");
    function run(seedSpy) {
      let calls = 0, seedCalls = 0, store;
      const ctx = {
        document: { documentElement: { lang: "en", getAttribute() { return null; } }, referrer: "", cookie: "",
                    addEventListener() {}, querySelector() { return null; } },
        location: { hostname: "example.com", host: "example.com", href: "https://example.com/", pathname: "/", search: "", protocol: "https:" },
        navigator: { userAgent: "analytics-gate", webdriver: false },
        localStorage: { getItem() { return null; }, setItem() {} },
        sessionStorage: { getItem() { return null; }, setItem() {} },
        addEventListener() {}, setTimeout() { return 0; }, matchMedia() { return { matches: false, addEventListener() {} }; },
      };
      ctx.window = ctx; ctx.self = ctx; ctx.globalThis = ctx;
      // Whatever is stored as plausible is instrumented: its init property becomes an accessor
      // that wraps any function assigned to it, so a call is counted whoever defined the
      // function, whenever the stub did it (before or after assigning plausible), and through
      // any variable that holds it. A function gets one wrapper, so plausible.init stays equal
      // to itself. An init that cannot be watched (defined non-configurable) is not counted
      // and the check fails, the safe way to be wrong; see the header for the shapes it
      // does not support.
      const wrappers = new WeakMap(), wrapped = new WeakSet();
      const wrap = (f) => {
        if (typeof f !== "function" || wrapped.has(f)) return f;
        let w = wrappers.get(f);
        if (!w) { w = function () { calls++; return f.apply(this, arguments); }; wrappers.set(f, w); wrapped.add(w); }
        return w;
      };
      const watch = (v) => {
        if (typeof v !== "function") return;
        const d = Object.getOwnPropertyDescriptor(v, "init");
        if (d && (!d.configurable || !("value" in d))) return;
        let cur = wrap(d ? d.value : v.init);
        Object.defineProperty(v, "init", { configurable: true, enumerable: true,
          get() { return cur; }, set(f) { cur = wrap(f); } });
      };
      Object.defineProperty(ctx, "plausible", { configurable: true, enumerable: true,
        get() { return store; },
        set(v) { store = v; watch(v); } });
      if (seedSpy) { const f = function () {}; f.init = function () { seedCalls++; }; ctx.plausible = f; }
      vm.createContext(ctx);
      vm.runInContext(code, ctx, { timeout: 2000 });
      return { ctx, calls, seedCalls };
    }
    try {
      const seeded = run(true), plain = run(false);
      const ok = seeded.seedCalls >= 1 && plain.calls >= 1 && typeof plain.ctx.plausible === "function" && typeof plain.ctx.plausible.init === "function";
      if (!ok) console.error("the stub did not call plausible.init, or did not define plausible and plausible.init");
      process.exit(ok ? 0 : 1);
    } catch (e) { console.error(String(e).split("\n")[0]); process.exit(1); }
  ' "$out" >/dev/null 2>"$err"
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

# csp_has <policy> <directive>: true when the directive is written, even with no sources
# (an empty directive means 'none').
csp_has() {
  awk -v dir="$2" 'BEGIN { RS = ";" }
    { n = split($0, t, /[ \t\r\n]+/); i = 1
      while (i <= n && t[i] == "") i++
      if (i <= n && tolower(t[i]) == dir) { f = 1; exit } }
    END { exit f ? 0 : 1 }' <<<"$1"
}

# host_listed <tokens>: true when the script's origin is among the source tokens, spelled
# as the config has it, scheme-less, with :443, with a trailing slash, or as a wildcard
# subdomain of the same domain. This check wants the host as a whole token: a source with a
# path (https://host/js/), `https:` or `*` is not accepted here even where a browser would
# allow it.
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

# csp_policies <file>: every Content-Security-Policy value in the file, one per line.
csp_policies() {
  local line
  while IFS= read -r line; do
    printf '%s\n' "${line#*:}"
  done < <(grep -iE '^[[:space:]]*content-security-policy:' "$1" || true)
}

# csp_host_problems <file>: one line per problem, nothing when the policies list the
# script's origin, as a whole token, in script-src and connect-src (and in script-src-elem
# when that is written out; it governs <script> elements).
csp_host_problems() {
  local file="$1" policy dir tokens n=0
  if [ ! -f "$file" ]; then echo "there is no $file to check the Content-Security-Policy in"; return; fi
  while IFS= read -r policy; do
    n=$((n + 1))
    for dir in script-src connect-src script-src-elem; do
      tokens="$(csp_tokens "$policy" "$dir")"
      if [ -z "$tokens" ]; then
        if [ "$dir" != script-src-elem ]; then
          echo "a Content-Security-Policy has no $dir directive written out, or it lists no source: ${policy:0:80}…"
        elif csp_has "$policy" script-src-elem; then
          echo "script-src-elem is written but lists no source, which allows no <script> at all: ${policy:0:80}…"
        fi
      elif ! host_listed "$tokens"; then
        if [ "$dir" = connect-src ]; then
          echo "$dir does not list $host as a token, so the browser would block the measurement requests: $(printf '%s' "$tokens" | tr '\n' ' ')"
        else
          echo "$dir does not list $host as a token, so the browser would block the analytics script: $(printf '%s' "$tokens" | tr '\n' ' ')"
        fi
      fi
    done
  done < <(csp_policies "$file")
  if [ "$n" -eq 0 ]; then echo "$file has no Content-Security-Policy line"; fi
}

# csp_host_left <file>: one line per directive that still lists the script's origin, for a
# site with analytics switched off; nothing when none does. A source with a path
# (https://host/js/) counts as the host here: it still lets the browser load from it.
# default-src counts too, as it stands in for a directive that is not written out. A file
# with no policy is reported as csp_host_problems reports it.
csp_host_left() {
  local file="$1" policy dir tokens n=0
  if [ ! -f "$file" ]; then echo "there is no $file to check the Content-Security-Policy in"; return; fi
  while IFS= read -r policy; do
    n=$((n + 1))
    for dir in script-src connect-src script-src-elem default-src; do
      # Each source without its path: scheme://host[:port]/anything becomes scheme://host[:port].
      tokens="$(csp_tokens "$policy" "$dir" | awk '{
        p = index($0, "://")
        if (p) { rest = substr($0, p + 3); q = index(rest, "/"); if (q) $0 = substr($0, 1, p + 2) substr(rest, 1, q - 1) }
        else { q = index($0, "/"); if (q > 1) $0 = substr($0, 1, q - 1) }
        print }')"
      if [ -n "$tokens" ] && host_listed "$tokens"; then
        echo "analytics is off (USE_ANALYTICS = false), but $dir still lists $host: take it out of public/_headers"
      fi
    done
  done < <(csp_policies "$file")
  if [ "$n" -eq 0 ]; then echo "$file has no Content-Security-Policy line"; fi
}

# csp_inline_problems <file> <stub-file>: one line per problem, nothing when the directive
# that governs <script> elements (script-src-elem if written out, else script-src) lets the
# stub run: 'unsafe-inline' with no hash and no nonce in the same directive (a browser
# ignores 'unsafe-inline' next to either), or the sha256 hash of the stub's exact text. A
# nonce cannot match in a static _headers file, and 'strict-dynamic' makes a browser ignore
# host sources and 'unsafe-inline', so this check refuses it until it is extended.
csp_inline_problems() {
  local file="$1" stub="$2" policy tokens dir hash
  hash="$(node -e 'process.stdout.write(require("node:crypto").createHash("sha256").update(require("node:fs").readFileSync(process.argv[1])).digest("base64"))' "$stub")"
  while IFS= read -r policy; do
    if csp_has "$policy" script-src-elem; then dir=script-src-elem; else dir=script-src; fi
    tokens="$(csp_tokens "$policy" "$dir")"
    if grep -qixF -- "'strict-dynamic'" <<<"$tokens"; then
      echo "$dir uses 'strict-dynamic', which makes a browser ignore host sources and 'unsafe-inline': this check needs extending before it can judge that"
    elif grep -qiE "^'(sha(256|384|512)|nonce)-" <<<"$tokens"; then
      if ! awk -v want="'sha256-$hash'" '{ if (tolower(substr($0, 1, 8)) == "'"'"'sha256-" && substr($0, 9) "" == substr(want, 9)) f = 1 } END { exit f ? 0 : 1 }' <<<"$tokens"; then
        echo "$dir has a hash or nonce but not 'sha256-$hash', the hash of the built init stub, so the browser would block the stub (change the stub and the hash together; other inline scripts need their own hashes and are not checked here)"
      fi
    elif ! grep -qixF -- "'unsafe-inline'" <<<"$tokens"; then
      echo "$dir allows no inline script ('unsafe-inline', or the stub's sha256 hash), so the browser would block the init stub"
    fi
  done < <(csp_policies "$file")
}

# The counter's own check, and the CSP reader's: each hand-made page must read as the
# counts beside it, the stub check must tell a stub that runs from one that only mentions
# the call, and each hand-made policy must give the verdict beside it.
selftest() {
  local dir="$work/fixtures" want_line got name expect n=0 m=0 hp ip stubjs h
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
  fixture callonly   "$s<script>plausible.init()</script>" ''
  fixture branchy    "$s<script>if(window.plausible){plausible.init()}else{window.plausible=function(){};plausible.init=function(){}}</script>" ''
  fixture replaced   "$s<script>window.plausible=window.plausible||function(){};plausible.init=function(o){plausible.o=o||{}};plausible.init()</script>" ''
  fixture preassign  "$s<script>var p=window.plausible||function(){};p.init=p.init||function(o){p.o=o||{}};window.plausible=p;plausible.init()</script>" ''
  fixture commentstr "$s<script>var m=\"<!--x-->\";window.plausible=window.plausible||function(){};plausible.init=plausible.init||function(o){plausible.o=o||{}};plausible.init()</script>" ''
  local qbody="var m=\"<!--x-->\";window.plausible=window.plausible||function(){};plausible.init=plausible.init||function(o){plausible.o=o||{}};plausible.init()"
  fixture scriptx    "$s" "<script-x><!--<script async src=\"$ANALYTICS_SRC\"></script>--></script-x>"
  fixture quotedtag  "$s<script data-text=\"</script>\">$qbody</script>" ''
  fixture alias      "$s<script>var p=window.plausible||function(){};p.init=p.init||function(o){p.o=o||{}};window.plausible=p;if(0){plausible.init()}p.init()</script>" ''
  fixture identity   "$s<script>window.plausible=window.plausible||function(){};plausible.init=plausible.init||function(o){plausible.o=o||{}};if(plausible.init!==plausible.init){throw new Error('x')};plausible.init()</script>" ''
  fixture defprop    "$s<script>window.plausible=window.plausible||function(){};Object.defineProperty(plausible,'init',{value:function(o){plausible.o=o||{}},configurable:false});plausible.init()</script>" ''
  fixture inherit    "$s<script>var f=function(){};Object.setPrototypeOf(f,{init:function(o){f.o=o||{}}});window.plausible=window.plausible||f;plausible.init()</script>" ''
  # name:expected counts "<script> <stub> <other>"
  for expect in both:'1 1 0' script:'1 0 0' stub:'0 1 0' none:'0 0 0' mention:'1 0 0' options:'1 1 0' \
                spaced:'1 1 0' upper:'1 1 0' jsonld:'0 0 0' comment:'0 0 0' oldform:'0 0 1' oldext:'0 0 1' \
                wrongid:'0 1 1' queryform:'0 1 1' twice:'2 1 0' jscomment:'1 1 0' jsstring:'1 1 0' \
                fakeinit:'1 1 0' usesdoc:'1 1 0' callonly:'1 1 0' branchy:'1 1 0' replaced:'1 1 0' preassign:'1 1 0' commentstr:'1 1 0' \
                scriptx:'1 0 0' quotedtag:'1 1 0' alias:'1 1 0' identity:'1 1 0' defprop:'1 1 0' inherit:'1 1 0'; do
    name="${expect%%:*}"; want_line="${expect#*:}"
    n=$((n + 1))
    got="$(perl -e "$(tags_program)" "$dir/$name.html" | awk '{print $1, $2, $3}')"
    if [ "$got" != "$want_line" ]; then
      echo "✗ analytics gate: its own counter read the '$name' fixture as '$got', not '$want_line'."
      fail=1
    fi
  done
  for expect in both:yes options:yes usesdoc:yes jscomment:no jsstring:no fakeinit:no callonly:no branchy:no replaced:no preassign:yes commentstr:yes stub:yes script:no \
                alias:yes identity:yes quotedtag:yes defprop:no inherit:yes; do
    name="${expect%%:*}"; want_line="${expect#*:}"
    got=no
    if stub_runs "$dir/$name.html"; then got=yes; fi
    if [ "$got" != "$want_line" ]; then
      echo "✗ analytics gate: its stub check said '$got' for the '$name' fixture, not '$want_line'."
      fail=1
    fi
  done
  # The stub is read byte for byte: a quoted '>' or '</script>' in the opening tag, and a
  # comment-like string in the code, must not change it (the CSP hash is of these bytes).
  printf '%s' "$qbody" >"$dir/quotedtag.body"
  stub_runs "$dir/quotedtag.html" || true
  if ! cmp -s "$work/stub.js" "$dir/quotedtag.body"; then
    echo "✗ analytics gate: its counter changed the code of a stub whose opening tag holds a quoted '>'."
    fail=1
  fi
  # CSP policies: name:expected host verdict:expected inline verdict (ok or bad)
  stubjs='window.plausible=window.plausible||function(){};plausible.init=plausible.init||function(o){plausible.o=o||{}};plausible.init()'
  printf '%s' "$stubjs" >"$dir/fixture-stub.js"
  h="$(node -e 'process.stdout.write(require("node:crypto").createHash("sha256").update(require("node:fs").readFileSync(process.argv[1])).digest("base64"))' "$dir/fixture-stub.js")"
  policy() { printf '/*\n  Content-Security-Policy: %s\n' "$2" >"$dir/$1.headers"; }
  policy p_unsafe   "default-src 'self'; script-src 'self' 'unsafe-inline' $host; connect-src 'self' $host"
  policy p_hash     "default-src 'self'; script-src 'self' 'sha256-$h' $host; connect-src 'self' $host"
  policy p_badhash  "default-src 'self'; script-src 'self' 'sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=' $host; connect-src 'self' $host"
  policy p_both     "default-src 'self'; script-src 'self' 'unsafe-inline' 'sha256-$h' $host; connect-src 'self' $host"
  policy p_bothbad  "default-src 'self'; script-src 'self' 'unsafe-inline' 'sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=' $host; connect-src 'self' $host"
  policy p_nonce    "default-src 'self'; script-src 'self' 'nonce-abc' $host; connect-src 'self' $host"
  policy p_strict   "default-src 'self'; script-src 'self' 'unsafe-inline' 'strict-dynamic' $host; connect-src 'self' $host"
  policy p_suffix   "default-src 'self'; script-src 'self' 'unsafe-inline' $host.evil.invalid; connect-src 'self' $host"
  policy p_noconn   "default-src 'self'; script-src 'self' 'unsafe-inline' $host"
  policy p_elem     "default-src 'self'; script-src 'self' 'unsafe-inline' $host; script-src-elem 'self' 'unsafe-inline'; connect-src 'self' $host"
  policy p_bare443  "default-src 'self'; script-src 'self' 'unsafe-inline' ${host#https://}:443; connect-src 'self' ${host#https://}:443"
  policy p_dup      "default-src 'self'; script-src 'self' $host; script-src 'unsafe-inline'; connect-src 'self' $host"
  policy p_upper    "default-src 'self'; Script-Src 'self' 'UNSAFE-INLINE' $host; Connect-Src 'self' $host"
  policy p_emptyel  "default-src 'self'; script-src 'self' 'unsafe-inline' $host; script-src-elem; connect-src 'self' $host"
  policy p_junk     "default-src 'self'; script-src 'self' 'unsafe-inline'junk $host; connect-src 'self' $host"
  policy p_hashjunk "default-src 'self'; script-src 'self' 'sha256-${h}'junk $host; connect-src 'self' $host"
  for expect in p_unsafe:ok:ok p_hash:ok:ok p_badhash:ok:bad p_both:ok:ok p_bothbad:ok:bad p_nonce:ok:bad p_strict:ok:bad \
                p_suffix:bad:ok p_noconn:bad:ok p_elem:bad:ok p_bare443:ok:ok p_dup:ok:bad p_upper:ok:ok \
                p_emptyel:bad:bad p_junk:ok:bad p_hashjunk:ok:bad; do
    name="${expect%%:*}"; want_line="${expect#*:}"; m=$((m + 1))
    hp="$(csp_host_problems "$dir/$name.headers")"; ip="$(csp_inline_problems "$dir/$name.headers" "$dir/fixture-stub.js")"
    got="$([ -z "$hp" ] && echo ok || echo bad):$([ -z "$ip" ] && echo ok || echo bad)"
    if [ "$got" != "$want_line" ]; then
      echo "✗ analytics gate: its CSP reader gave '$got' for the '$name' policy, not '$want_line' (host:inline)."
      fail=1
    fi
  done
  # With analytics off, a policy that names the host in any of the three directives is wrong.
  policy p_nohost   "default-src 'self'; script-src 'self' 'unsafe-inline'; connect-src 'self'"
  policy p_nohostel "default-src 'self'; script-src 'self' 'unsafe-inline'; script-src-elem 'self'; connect-src 'self'"
  policy p_elemonly "default-src 'self'; script-src 'self' 'unsafe-inline'; script-src-elem 'self' $host; connect-src 'self'"
  policy p_path      "default-src 'self'; script-src 'self' 'unsafe-inline' $host/js/; connect-src 'self'"
  policy p_lookalike "default-src 'self'; script-src 'self' 'unsafe-inline' $host.evil.invalid; connect-src 'self' https://x${host#*://}"
  policy p_default   "default-src 'self' $host; script-src 'self' 'unsafe-inline'; connect-src 'self'"
  printf '/*\n  X-Frame-Options: DENY\n' >"$dir/p_nocsp.headers"
  for expect in p_unsafe:bad p_noconn:bad p_suffix:bad p_bare443:bad p_elem:bad p_nohost:ok p_nohostel:ok p_elemonly:bad p_nocsp:bad \
                p_path:bad p_lookalike:ok p_default:bad; do
    name="${expect%%:*}"; want_line="${expect#*:}"; m=$((m + 1))
    got="$([ -z "$(csp_host_left "$dir/$name.headers")" ] && echo ok || echo bad)"
    if [ "$got" != "$want_line" ]; then
      echo "✗ analytics gate: its off-switch CSP check gave '$got' for the '$name' policy, not '$want_line'."
      fail=1
    fi
  done
  if [ "$fail" -ne 0 ]; then exit 1; fi
  echo "✓ analytics gate: the counter reads its $n fixture pages, the stub check its stubs and the CSP reader its $m policies as expected"
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
  # Every page's stub must run, not only the home page's; each stub is kept so the CSP can
  # be judged against every distinct one.
  rm -rf "$work/stubs"; mkdir -p "$work/stubs"
  local k=0
  while IFS= read -r page; do
    k=$((k + 1))
    if stub_runs "$page"; then cp "$work/stub.js" "$work/stubs/$k.js"
    else bad="$bad"$'\n'"    ${page#"$work/$name/"}: $(cat "$work/stub.err" 2>/dev/null || true)"; fi
  done < <(find "$work/$name" -name '*.html' | sort)
  if [ -z "$bad" ]; then
    echo "✓ $what: the init stub on every page runs and calls plausible.init()"
  else
    echo "✗ $what: the init stub does not run and call plausible.init() (in a bare JavaScript context) on these pages:$bad"
    fail=1
  fi
}

# Off means no analytics tag, nor half of one, on any page, and no mention of the script's
# path or id anywhere in the build (a preload link, a script made at run time that writes
# either whole). The path and the id are specific; the host alone may be a site's own
# origin or a service it links to. _headers is skipped: it names the host in the CSP on
# purpose.
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

# Email links (<a> tags whose class has email-link, as EmailLink.astro writes them) and links
# to /go/email, per page: prints "<email links> <email links whose own href is /go/email>
# <links to /go/email> <path>". Attributes are matched whole (data-href is not href), and
# HTML comments are dropped first, so a commented-out link does not count.
go_program() {
  cat <<'PERL'
local $/;
for my $file (@ARGV) {
  open(my $fh, '<', $file) or die "cannot read $file\n";
  my $html = <$fh>;
  close $fh;
  $html =~ s/<!--.*?-->//gs;
  my ($email, $emailgo, $go) = (0, 0, 0);
  while ($html =~ /<a\b((?:[^>"']|"[^"]*"|'[^']*')*)>/gi) {
    my $attrs = $1;
    # One attribute at a time, each value consumed whole, so text inside a quoted value
    # (title="href='/go/email?…'") is never read as an attribute of its own.
    my %attr;
    while ($attrs =~ /([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?/g) {
      my $name = lc $1;
      $attr{$name} = defined $2 ? $2 : defined $3 ? $3 : defined $4 ? $4 : '' unless exists $attr{$name};
    }
    my $is_email = defined $attr{class} && $attr{class} =~ /(?:^|\s)email-link(?:\s|$)/;
    my $is_go = defined $attr{href} && $attr{href} =~ /^\/go\/email\?/;
    $email++ if $is_email;
    $emailgo++ if $is_email && $is_go;
    $go++ if $is_go;
  }
  print "$email $emailgo $go $file\n";
}
PERL
}
go_links() {
  local dir="$1" out pages lines
  out="$(find "$dir" -name '*.html' -exec perl -e "$(go_program)" {} +)" || return 1
  pages="$(find "$dir" -name '*.html' | wc -l | tr -d ' ')"
  lines="$(printf '%s\n' "$out" | grep -c . || true)"
  [ "$pages" -gt 0 ] && [ "$pages" = "$lines" ] || return 1
  printf '%s\n' "$out"
}

# The go-link reader on hand-made pages, each with the counts beside it.
go_selftest() {
  local dir="$work/go-fixtures" expect name want got k=0
  mkdir -p "$dir"
  gofix() { printf '<!doctype html><html><body>%s</body></html>' "$2" >"$dir/$1.html"; }
  gofix plain    '<a class="email-link" href="#" data-email="x">a</a>'
  gofix go       '<a class="email-link" href="/go/email?e=x" rel="nofollow" data-via="server">a</a>'
  gofix extra    '<a class="footer email-link big" href="/go/email?e=x">a</a><a href="/about">b</a>'
  gofix lookalike '<a class="email-links" href="#">a</a><a class="not-email-link" href="#">b</a>'
  gofix handmade '<a href="/go/email?e=x">a</a>'
  gofix comment  '<!-- <a class="email-link" href="/go/email?e=x">a</a> -->'
  gofix quoted   '<a title="a > b" class="email-link" href="/go/email?e=x">a</a>'
  gofix apart    '<a class="email-link" href="#">a</a><a href="/go/email?e=x">b</a>'
  gofix datahref '<a class="email-link" data-href="/go/email?e=x" href="#">a</a>'
  gofix dataclass '<a data-class="email-link" href="/go/email?e=x">a</a>'
  gofix inquote  "<a title=\"href='/go/email?e=x' class='email-link'\" class=\"email-link\" href=\"#\">a</a>"
  gofix unquoted '<a class=email-link href=/go/email?e=x>a</a>'
  for expect in plain:'1 0 0' go:'1 1 1' extra:'1 1 1' lookalike:'0 0 0' handmade:'0 0 1' comment:'0 0 0' \
                quoted:'1 1 1' apart:'1 0 1' datahref:'1 0 0' dataclass:'0 0 1' inquote:'1 0 0' unquoted:'1 1 1'; do
    name="${expect%%:*}"; want="${expect#*:}"; k=$((k + 1))
    got="$(perl -e "$(go_program)" "$dir/$name.html" | awk '{print $1, $2, $3}')"
    if [ "$got" != "$want" ]; then
      echo "✗ analytics gate: the email-link reader reads fixture '$name' as '$got', expected '$want'."
      fail=1
    fi
  done
  if [ "$fail" -ne 0 ]; then exit 1; fi
  echo "✓ analytics gate: the email-link reader reads its $k fixture pages as expected"
}

# expect_go <case> <what> <all|none>: all = every email link on every page goes to
# /go/email (the live build in server mode, else taps go uncounted); none = no link goes
# there (every other build: no Function answers /go/email under astro preview or dev, and
# in script mode the browser counts the tap instead).
expect_go() {
  local name="$1" what="$2" want="$3" counts bad
  counts="$(go_links "$work/$name")" || { echo "✗ $what: could not read the built pages."; fail=1; return; }
  if [ "$want" = all ]; then
    bad="$(printf '%s\n' "$counts" | awk '$1 != $2 { path = $0; sub(/^[^ ]* [^ ]* [^ ]* /, "", path); print path }')"
  else
    bad="$(printf '%s\n' "$counts" | awk '$3 > 0 { path = $0; sub(/^[^ ]* [^ ]* [^ ]* /, "", path); print path }')"
  fi
  if [ -z "$bad" ]; then
    if [ "$want" = all ]; then echo "✓ $what: every email link goes to /go/email"
    else echo "✓ $what: no link goes to /go/email"; fi
  else
    if [ "$want" = all ]; then echo "✗ $what: email links that do not go to /go/email, so their taps would not be counted, on these pages:"
    else echo "✗ $what: links to /go/email, where this build needs plain mailto: links (the Function is not asked here), on these pages:"; fi
    while IFS= read -r page; do printf '    %s\n' "${page#"$work/$name/"}"; done <<< "$bad"
    fail=1
  fi
}

# Report what a problem list holds, as one ✗ line each.
report_problems() {
  local problems="$1" ok_msg="$2" line
  if [ -z "$problems" ]; then
    echo "✓ analytics gate: $ok_msg"
  else
    while IFS= read -r line; do echo "✗ analytics gate: $line"; done <<<"$problems"
    fail=1
  fi
}

selftest
go_selftest

if [ "$use" != false ] && [ "$mode" = server ]; then
  echo "· analytics gate: server mode, so no page loads the script and public/_headers needs no analytics host"
  build live set "$prod"
  expect_off live "CF_PAGES_BRANCH=$prod (the live build, server mode)"
  expect_go live "CF_PAGES_BRANCH=$prod (the live build, server mode)" all
  for c in "unset:unset::CF_PAGES_BRANCH unset (a plain npm run build)" \
           "empty:set::CF_PAGES_BRANCH= (a preview by command)" \
           "preview:set:$preview:CF_PAGES_BRANCH=$preview (a preview branch)"; do
    IFS=: read -r name how value what <<<"$c"
    build "$name" "$how" "$value"
    expect_off "$name" "$what"
    expect_go "$name" "$what" none
  done
  if [ "$fail" -eq 0 ]; then
    echo "✓ analytics gate: $checked builds in server mode, no script in any; email links counted on the live build only"
  fi
  exit "$fail"
fi

if [ "$use" = false ]; then
  report_problems "$(csp_host_left public/_headers)" "analytics is off, and public/_headers lists $host in none of script-src, script-src-elem, connect-src and default-src"
  build live set "$prod"
  expect_off live "CF_PAGES_BRANCH=$prod (the live build, analytics off)"
  expect_go live "CF_PAGES_BRANCH=$prod (the live build, analytics off)" none
else
report_problems "$(csp_host_problems public/_headers)" "public/_headers lists $host as a token in script-src and connect-src"

build live set "$prod"
expect_on live "CF_PAGES_BRANCH=$prod (the live build)"
expect_go live "CF_PAGES_BRANCH=$prod (the live build)" none
# The CSP is judged against every distinct stub the live build wrote (the pages normally share one).
kept=()
for stubfile in "$work"/stubs/*.js; do
  [ -f "$stubfile" ] || continue
  dup=0
  for other in ${kept[@]+"${kept[@]}"}; do
    if cmp -s "$stubfile" "$other"; then dup=1; break; fi
  done
  [ "$dup" -eq 0 ] || continue
  kept+=("$stubfile")
  report_problems "$(csp_inline_problems public/_headers "$stubfile")" "the CSP lets the built init stub run ($(basename "$stubfile"))"
done
fi

build unset unset
expect_off unset "CF_PAGES_BRANCH unset (a plain npm run build)"
expect_go unset "CF_PAGES_BRANCH unset (a plain npm run build)" none

build empty set ""
expect_off empty "CF_PAGES_BRANCH= (a preview by command)"
expect_go empty "CF_PAGES_BRANCH= (a preview by command)" none

build preview set "$preview"
expect_off preview "CF_PAGES_BRANCH=$preview (a preview branch)"
expect_go preview "CF_PAGES_BRANCH=$preview (a preview branch)" none

if [ "$fail" -eq 0 ]; then
  if [ "$use" = false ]; then
    echo "✓ analytics gate: $checked builds, off in every one (USE_ANALYTICS = false)"
  else
    echo "✓ analytics gate: $checked builds, on only when CF_PAGES_BRANCH is '$prod'"
  fi
fi
exit "$fail"
