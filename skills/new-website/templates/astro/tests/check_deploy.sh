#!/usr/bin/env bash
# Drives `npm run deploy:live` and `npm run deploy:preview` with --dry-run, the commands an owner
# runs without GitHub, in a throwaway copy of this site with its own git (scripts/deploy.sh).
#
# What it checks:
#   - live: exit 0, the built pages carry the analytics tag and its stub on every page when
#     USE_ANALYTICS is true in src/config.ts and none when it is false, dist/build.txt names the
#     copy's HEAD, and the command it prints is `wrangler deploy`.
#   - preview: the same, but no tag either way, and the command is `wrangler preview`. So with
#     analytics on, a WORKERS_CI_BRANCH set in the caller's shell must not switch the tag on.
#   - refusals, each with its own message: an unsaved file (live; an untracked one counts, preview
#     builds it), a branch other than PROD_BRANCH or no branch (live; preview builds it, and live
#     still runs on PROD_BRANCH when a tag has its name), the
#     placeholder Worker name (both), a wrangler.toml beside wrangler.jsonc.
#   - the build's environment (a build step that prints it): no CF_* or CLOUDFLARE_* variable,
#     WORKERS_CI=1, WORKERS_CI_BRANCH only for live; a CF_PAGES_COMMIT_SHA from the caller does
#     not replace HEAD in build.txt.
#   - a comma before a closing } or ] in wrangler.jsonc is read (Wrangler accepts it), and the live
#     check, run against a stand-in wrangler, curl and sleep, asks for the address of the one
#     site: line in code, and for none when two lines or only a comment hold one; deploy.sh's
#     readers for that line are ship.sh's, word for word.
# What it does not check: Wrangler, Cloudflare, or that the build works through the link to this
# folder's node_modules (it is used as it is). A site with no Workers config (a .json or .jsonc
# holding "assets" and no "pages_build_output_dir") is on Pages, so it skips and says so.
#
# The toolkit's CI runs it (template-tests.yml), with analytics off as shipped and again with it on.
# Needs `npm ci` first, git, and node.
set -euo pipefail
CDPATH= cd -- "$(dirname -- "$0")/.."
site="$PWD"

for tool in node git npm; do
  command -v "$tool" >/dev/null 2>&1 || { echo "✗ check_deploy: $tool is not on the PATH."; exit 1; }
done

# The Workers config, by the move tools' rule. Prints its file name; nothing if there is none.
has_workers_config="$(node -e '
  const fs = require("fs");
  for (const f of fs.readdirSync(".").filter((n) => /\.jsonc?$/.test(n)).sort()) {
    let s = "", t = fs.readFileSync(f, "utf8"), i = 0;
    while (i < t.length) {
      if (t[i] === "\"") { let j = i + 1; while (j < t.length && t[j] !== "\"") j += t[j] === "\\" ? 2 : 1; s += t.slice(i, j + 1); i = j + 1; }
      else if (t[i] === "/" && t[i + 1] === "/") { while (i < t.length && t[i] !== "\n") i++; }
      else if (t[i] === "/" && t[i + 1] === "*") { const j = t.indexOf("*/", i + 2); i = j < 0 ? t.length : j + 2; }
      else { s += t[i]; i++; }
    }
    let u = "", k = 0;
    while (k < s.length) {
      const c = s[k];
      if (c === "\"") { let m = k + 1; while (m < s.length && s[m] !== "\"") m += s[m] === "\\" ? 2 : 1; u += s.slice(k, m + 1); k = m + 1; }
      else if (c === "," && /^\s*[}\]]/.test(s.slice(k + 1))) { k++; }
      else { u += c; k++; }
    }
    try { const c = JSON.parse(u); if (c && typeof c === "object" && "assets" in c && !("pages_build_output_dir" in c)) { console.log(f); break; } } catch { /* not ours */ }
  }
')"
if [ -z "$has_workers_config" ]; then
  echo "· check_deploy: no Workers config here (a .json or .jsonc with \"assets\" and no \"pages_build_output_dir\"): this site is on Cloudflare Pages, so there is no deploy command to check. Skipped."
  exit 0
fi
if [ ! -f scripts/deploy.sh ] || [ ! -f wrangler.jsonc ]; then
  echo "✗ check_deploy: the Workers config is $has_workers_config, but scripts/deploy.sh or wrangler.jsonc is missing."
  exit 1
fi
if [ ! -d node_modules ]; then
  echo "✗ check_deploy: node_modules not found. Run npm ci first."
  exit 1
fi

prod="$(sed -nE "s/^export const PROD_BRANCH = ['\"]([^'\"]*)['\"];?.*/\1/p" src/config.ts)"
use="$(sed -nE "s/^export const USE_ANALYTICS = (true|false);?[[:space:]]*(\/\/.*)?$/\1/p" src/config.ts)"
host="$(sed -nE "s/^[[:space:]]*scriptHost:[[:space:]]*['\"]([^'\"]*)['\"].*/\1/p" src/config.ts)"
id="$(sed -nE "s/^[[:space:]]*scriptId:[[:space:]]*['\"]([^'\"]*)['\"].*/\1/p" src/config.ts)"
# src/config.ts is the site's own file, so whats-new never lists a line it lacks: name each one.
missing=""
[ -n "$prod" ] || missing="$missing
  export const PROD_BRANCH = 'production';   (the branch Cloudflare builds as Production)"
[ -n "$use" ] || missing="$missing
  export const USE_ANALYTICS = true;   (or false; one line, a // comment after it is fine)"
[ -n "$host" ] || missing="$missing
  scriptHost: '…',   (inside the ANALYTICS object)"
[ -n "$id" ] || missing="$missing
  scriptId: '…',   (inside the ANALYTICS object)"
if [ -n "$missing" ]; then
  echo "✗ check_deploy: src/config.ts lacks lines this check and the analytics gate read. Add them as the starter's src/config.ts has them:$missing"
  exit 1
fi
script_path="/js/${id}.js"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
copy="$work/site"
mkdir "$copy"
# The site as it is, less what a build or an install makes and its own git; its dependencies are
# linked in.
tar -C "$site" --exclude=./node_modules --exclude=./dist --exclude=./.astro --exclude=./.git -cf - . | tar -C "$copy" -xf -
ln -s "$site/node_modules" "$copy/node_modules"
# A link does not match the `node_modules/` line of .gitignore.
git_in() { git -C "$copy" "$@"; }
git_in init -q -b "$prod"
git_in config user.email check@example.com
git_in config user.name check
git_in config commit.gpgsign false
mkdir -p "$copy/.git/info"
echo node_modules >> "$copy/.git/info/exclude"
if [ -f "$site/.gitignore" ]; then cp "$site/.gitignore" "$copy/.gitignore"; else cp "$site/../.gitignore" "$copy/.gitignore"; fi
# set_name <name>: the copy's Worker name, whatever the site's own is (the first "name" key).
set_name() {
  perl -pi -e 'if (!$d && s/^(\s*"name"\s*:\s*)"[^"]*"/$1"$ENV{NEW}"/) { $d = 1 }' "$copy/wrangler.jsonc"
  grep -qF "\"$1\"" "$copy/wrangler.jsonc" || { echo "✗ check_deploy: could not set the Worker name in the copy's wrangler.jsonc."; exit 1; }
}
# A real Worker name for the copy; the placeholder is what the refusal case puts back.
NEW=check-deploy-site; export NEW
set_name check-deploy-site
# A page below the top folder: the tag must be on nested pages too.
mkdir -p "$copy/src/pages/nested-check"
printf -- "---\nimport Base from '../../layouts/Base.astro';\n---\n<Base title=\"Nested check\" description=\"A page below the top folder, so the checks read every built page.\"><main><h1>Nested check</h1></main></Base>\n" > "$copy/src/pages/nested-check/page.astro"
# A build step that prints its own environment.
envlog="$work/build-env.txt"
sed -i.bak "s|\"build\": \"|\"build\": \"env > '$envlog' \&\& |" "$copy/package.json"
rm -f "$copy/package.json.bak"
git_in add -A
git_in commit -q -m "check_deploy copy"
head_sha="$(git_in rev-parse HEAD)"

fail=0
ok() { echo "✓ check_deploy: $1"; }
bad() { echo "✗ check_deploy: $1"; fail=1; }

# run <log name> <env assignments…> -- <npm script> — runs it in the copy; sets rc, output in $work/<log>.log
rc=0
run() {
  local log="$1"; shift
  local -a envs=()
  while [ "$1" != -- ]; do envs+=("$1"); shift; done
  shift
  rc=0
  rm -rf "$copy/dist" "$envlog"
  # The caller's own Workers/Pages variables never leak into a case that does not set them.
  (cd "$copy" && env -u CF_PAGES_BRANCH -u CF_PAGES_COMMIT_SHA -u WORKERS_CI -u WORKERS_CI_BRANCH -u CF_API_TOKEN -u CLOUDFLARE_API_TOKEN \
     ${envs[@]+"${envs[@]}"} npm run "$@" >"$work/$log.log" 2>&1) || rc=$?
}

# tagged <expect: yes|no> <label> — every built page carries (or none carries) the script and the init stub.
tagged() {
  local expect="$1" label="$2" pages=0 with=0 half=0 f s p
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    pages=$((pages + 1))
    s=0; p=0
    grep -qF "$host$script_path" "$f" && s=1
    grep -qF 'plausible.init' "$f" && p=1
    if [ "$s" = 1 ] && [ "$p" = 1 ]; then with=$((with + 1)); elif [ "$s" = 1 ] || [ "$p" = 1 ]; then half=$((half + 1)); fi
  done <<PAGES
$(find "$copy/dist" -name '*.html' 2>/dev/null | sort)
PAGES
  if [ ! -f "$copy/dist/nested-check/page.html" ]; then bad "$label: the nested test page was not built."; return; fi
  if [ "$pages" = 0 ]; then bad "$label: no built pages in dist/."; return; fi
  if [ "$expect" = yes ] && [ "$with" = "$pages" ] && [ "$half" = 0 ]; then ok "$label: the tag and stub are on all $pages pages"
  elif [ "$expect" = no ] && [ "$with" = 0 ] && [ "$half" = 0 ]; then ok "$label: no page has the tag or the stub ($pages pages)"
  else bad "$label: expected the tag on $expect pages, found it with its stub on $with of $pages (half a tag on $half)."; fi
}

want_tag=no; [ "$use" = false ] || want_tag=yes

# 1. live
run live-dry -- deploy:live -- --dry-run
if [ "$rc" = 0 ]; then ok "deploy:live --dry-run exits 0"; else bad "deploy:live --dry-run exited $rc:"; sed 's/^/  | /' "$work/live-dry.log"; fi
tagged "$want_tag" "deploy:live (USE_ANALYTICS = $use)"
if [ "$(tr -d '[:space:]' < "$copy/dist/build.txt" 2>/dev/null || true)" = "$head_sha" ]; then ok "build.txt names HEAD"; else bad "build.txt does not name HEAD ${head_sha:0:12}."; fi
if grep -qE '(^|[^a-z])wrangler deploy($|[^a-z])' "$work/live-dry.log" && ! grep -q 'wrangler preview' "$work/live-dry.log"; then ok "the command printed is wrangler deploy"; else bad "deploy:live --dry-run did not print wrangler deploy."; fi

# 2. preview, with the caller's shell holding the live branch: a preview must not read it
run preview-dry "WORKERS_CI_BRANCH=$prod" CF_PAGES_BRANCH="$prod" -- deploy:preview -- --dry-run
if [ "$rc" = 0 ]; then ok "deploy:preview --dry-run exits 0"; else bad "deploy:preview --dry-run exited $rc:"; sed 's/^/  | /' "$work/preview-dry.log"; fi
tagged no "deploy:preview (caller's shell has WORKERS_CI_BRANCH and CF_PAGES_BRANCH = $prod)"
if grep -q 'wrangler preview' "$work/preview-dry.log" && ! grep -qE 'wrangler deploy' "$work/preview-dry.log"; then ok "the command printed is wrangler preview"; else bad "deploy:preview --dry-run did not print wrangler preview."; fi

# 3. the build's environment
run env-live CLOUDFLARE_API_TOKEN=dummy CF_API_TOKEN=dummy CF_ACCOUNT_ID=dummy "CF_PAGES_COMMIT_SHA=0000000000000000000000000000000000000000" -- deploy:live -- --dry-run
if [ "$rc" != 0 ]; then
  bad "deploy:live --dry-run with dummy tokens exited $rc:"; sed 's/^/  | /' "$work/env-live.log"
elif [ ! -s "$envlog" ]; then
  bad "the build step that prints its environment did not run."
else
  if grep -qE '^(CF_|CLOUDFLARE_)' "$envlog"; then bad "the live build still sees: $(grep -oE '^(CF_|CLOUDFLARE_)[A-Za-z0-9_]*' "$envlog" | tr '\n' ' ')"; else ok "the live build sees no CF_* or CLOUDFLARE_* variable"; fi
  if grep -qx 'WORKERS_CI=1' "$envlog" && grep -qx "WORKERS_CI_BRANCH=$prod" "$envlog"; then ok "the live build has WORKERS_CI=1 and WORKERS_CI_BRANCH=$prod"; else bad "the live build lacks WORKERS_CI=1 or WORKERS_CI_BRANCH=$prod."; fi
  if [ "$(tr -d '[:space:]' < "$copy/dist/build.txt")" = "$head_sha" ]; then ok "a caller's CF_PAGES_COMMIT_SHA does not replace HEAD in build.txt"; else bad "build.txt did not name HEAD with CF_PAGES_COMMIT_SHA set by the caller."; fi
fi
run env-preview "WORKERS_CI_BRANCH=$prod" -- deploy:preview -- --dry-run
if [ "$rc" != 0 ]; then
  bad "deploy:preview --dry-run exited $rc (environment case):"; sed 's/^/  | /' "$work/env-preview.log"
elif grep -qx 'WORKERS_CI=1' "$envlog" && ! grep -q '^WORKERS_CI_BRANCH=' "$envlog"; then ok "the preview build has WORKERS_CI=1 and no WORKERS_CI_BRANCH"; else bad "the preview build lacks WORKERS_CI=1, or still has WORKERS_CI_BRANCH."; fi

# refused <label> <message part> <log name>: the run (already made) failed, said this, and built nothing
refused() {
  if [ "$rc" != 0 ] && grep -qF -- "$2" "$work/$3.log" && [ ! -d "$copy/dist" ]; then ok "$1 is refused: \"$2\""; else bad "$1 was not refused with \"$2\" before the build (exit $rc):"; sed 's/^/  | /' "$work/$3.log"; fi
}

# 4. refusals
echo "unsaved" > "$copy/unsaved.txt"
run live-dirty -- deploy:live -- --dry-run
refused "live with an untracked file" "Unsaved changes" live-dirty
run preview-dirty -- deploy:preview -- --dry-run
if [ "$rc" = 0 ]; then ok "preview builds an untracked file"; else bad "preview refused an unsaved file (exit $rc)."; fi
rm -f "$copy/unsaved.txt"

git_in switch -q -c "not-$prod"
run branch-live -- deploy:live -- --dry-run
refused "live on a branch other than $prod" "The live site comes from the branch \"$prod\" (PROD_BRANCH in src/config.ts), but this folder is on the branch \"not-$prod\"." branch-live
run branch-preview -- deploy:preview -- --dry-run
if [ "$rc" = 0 ]; then ok "preview builds another branch"; else bad "preview refused another branch (exit $rc)."; fi
git_in switch -q --detach "$prod"
run detached-live -- deploy:live -- --dry-run
refused "live with no branch (detached HEAD)" "but this folder is on no branch" detached-live
run detached-preview -- deploy:preview -- --dry-run
if [ "$rc" = 0 ]; then ok "preview builds with no branch"; else bad "preview refused a detached HEAD (exit $rc)."; fi
git_in switch -q "$prod"
# A tag with the branch's name must not hide the branch.
git_in tag "$prod"
run tag-live -- deploy:live -- --dry-run
if [ "$rc" = 0 ]; then ok "live on $prod with a tag of the same name exits 0"; else bad "live on $prod with a tag named $prod exited $rc:"; sed 's/^/  | /' "$work/tag-live.log"; fi
git_in tag -d "$prod" >/dev/null

cp "$copy/wrangler.jsonc" "$work/wrangler.jsonc.good"
NEW=example-site set_name example-site
git_in commit -q -am "placeholder name"
run name-live -- deploy:live -- --dry-run
refused "live with the placeholder name" 'placeholder name "example-site"' name-live
run name-preview -- deploy:preview -- --dry-run
refused "preview with the placeholder name" 'placeholder name "example-site"' name-preview
cp "$work/wrangler.jsonc.good" "$copy/wrangler.jsonc"
git_in commit -q -am "real name"

echo 'name = "x"' > "$copy/wrangler.toml"
git_in add wrangler.toml; git_in commit -q -m "a second config"
run toml-live -- deploy:live -- --dry-run
refused "live with a wrangler.toml beside wrangler.jsonc" "wrangler.jsonc is not alone" toml-live
run toml-preview -- deploy:preview -- --dry-run
refused "preview with a wrangler.toml beside wrangler.jsonc" "wrangler.jsonc is not alone" toml-preview

# 5. the config reader and the live check, with a domain route. A comma before a closing } or ] is
# read as Wrangler reads it (checked on 4.162.0). The live check runs for real, but against a stand-in
# wrangler, curl and sleep, so nothing leaves this machine: the stand-in curl answers with the copy's HEAD and
# logs the address it was asked for, which shows what deploy.sh took for the site's address.
git_in rm -q -f wrangler.toml
git_in commit -q -m "no second config"
cp "$work/wrangler.jsonc.good" "$copy/wrangler.jsonc"
perl -0pi -e 's/\n\}\s*$/,\n  \/\/ the route, with commas Wrangler accepts\n  "routes": [{ "pattern": "check-deploy.example.invalid", "custom_domain": true, },],\n}\n/' "$copy/wrangler.jsonc"
if grep -q 'custom_domain' "$copy/wrangler.jsonc"; then :; else echo "✗ check_deploy: could not add a route to the copy's wrangler.jsonc."; exit 1; fi
git_in commit -q -am "a route, and trailing commas"
run comma-live -- deploy:live -- --dry-run
if [ "$rc" = 0 ] && grep -qE '(^|[^a-z])wrangler deploy($|[^a-z])' "$work/comma-live.log"; then ok "a trailing comma in wrangler.jsonc is read (the live dry run exits 0)"; else bad "a trailing comma in wrangler.jsonc was refused (exit $rc):"; sed 's/^/  | /' "$work/comma-live.log"; fi

# A node_modules of the copy's own, so its .bin can hold a stand-in wrangler; every package is linked.
rm "$copy/node_modules"
mkdir "$copy/node_modules" "$copy/node_modules/.bin"
for e in "$site"/node_modules/* "$site"/node_modules/.[!.]*; do
  [ -e "$e" ] || continue
  [ "$(basename "$e")" = .bin ] || ln -s "$e" "$copy/node_modules/$(basename "$e")"
done
for e in "$site"/node_modules/.bin/*; do
  [ "$(basename "$e")" = wrangler ] && continue
  target="$e"
  if [ -L "$e" ]; then
    target="$(readlink "$e")"
    case "$target" in /*) ;; *) target="$site/node_modules/.bin/$target" ;; esac
  fi
  ln -s "$target" "$copy/node_modules/.bin/$(basename "$e")"
done
printf '#!/bin/sh\necho "stand-in wrangler $*"\n' > "$copy/node_modules/.bin/wrangler"
chmod +x "$copy/node_modules/.bin/wrangler"
fakebin="$work/fakebin"
mkdir "$fakebin"
printf '#!/bin/sh\nexit 0\n' > "$fakebin/sleep"
printf '#!/bin/sh\nfor a; do u="$a"; done\necho "$u" >> "%s/curl.log"\ngit -C "%s" rev-parse HEAD\n' "$work" "$copy" > "$fakebin/curl"
chmod +x "$fakebin/sleep" "$fakebin/curl"

# live_site <label> <expected curl log> <message part>: the live check on the copy as it is now.
live_site() {
  rm -f "$work/curl.log"
  run "$1" "PATH=$fakebin:$PATH" -- deploy:live
  local asked=""
  [ ! -f "$work/curl.log" ] || asked="$(sed 's/?.*//' "$work/curl.log" | sort -u | tr '\n' ' ')"
  asked="${asked% }"
  if [ "$rc" = 0 ] && [ "$asked" = "$2" ] && grep -qF -- "$3" "$work/$1.log"; then ok "$1: \"$3\" (asked: ${asked:-nothing})"; else bad "$1: expected exit 0, asking \"$2\" and saying \"$3\"; got exit $rc, asked \"$asked\":"; sed 's/^/  | /' "$work/$1.log"; fi
}
# The site's own address, found by a different reader than deploy.sh's: its first plain `site: '…'` line.
own_site="$(sed -nE "s/^[[:space:]]*site:[[:space:]]*['\"](https?:\/\/[^'\"]+)['\"].*/\1/p" "$copy/astro.config.mjs" | awk 'NR==1')"
own_site="${own_site%/}"
if [ -z "$own_site" ]; then
  echo "· check_deploy: astro.config.mjs has no line of the form  site: 'https://…',  so the live-check cases were not run."
else
  live_site site-one "$own_site/build.txt" "LIVE — verified: $own_site is serving build"

# The same address in double quotes, as a formatter may write it: still one address, still checked.
perl -pi -e 's|^(\s*site:\s*)\x27(https?://[^\x27]+)\x27|$1"$2"|' "$copy/astro.config.mjs"
if ! git_in diff --quiet; then git_in commit -q -am "site: in double quotes"; fi   # already double-quoted: nothing to rewrite
live_site site-dq "$own_site/build.txt" "LIVE — verified: $own_site is serving build"

# An old address kept in a comment: two matches, so no one address to check.
perl -pi -e 's|^(\s*site:.*)$|$1\n  // site: \x27https://old.example.invalid\x27,|' "$copy/astro.config.mjs"
git_in commit -q -am "an old address in a comment"
live_site site-many "" "has more than one site: address"

# Only a comment holds a site: address (the real one is written so that it does not match).
perl -pi -e 's|^(\s*)site:(\s*)([\x27"]https?://[^\x27"]+[\x27"])|$1\x27site\x27:$2$3|; s|^(\s*)// site: .*$|$1// site: \x27https://old.example.invalid\x27,|' "$copy/astro.config.mjs"
git_in commit -q -am "the only site: is in a comment"
live_site site-comment "" "sits in a comment"
fi

# deploy.sh's site: readers are the ones in scripts/ship.sh, word for word.
reader() { awk '/^# The `site:` address in the astro.config.mjs text given/{p=1} p{print} p&&/^js_state\(\)/{j=1} j&&/^}$/{exit}' "$1"; }
has_ship=0; has_deploy=0
grep -q '^site_count()' "$site/scripts/ship.sh" && has_ship=1
grep -q '^site_count()' "$site/scripts/deploy.sh" && has_deploy=1
if [ "$has_ship" = 1 ] && [ "$has_deploy" = 1 ]; then
  if [ -n "$(reader "$site/scripts/deploy.sh")" ] && [ "$(reader "$site/scripts/ship.sh")" = "$(reader "$site/scripts/deploy.sh")" ]; then ok "deploy.sh reads site: with the same functions as ship.sh"; else bad "the site: readers in scripts/deploy.sh and scripts/ship.sh differ: copy site_of, site_count and js_state from one to the other."; fi
elif [ "$has_ship" = 1 ] || [ "$has_deploy" = 1 ]; then
  bad "only one of scripts/ship.sh and scripts/deploy.sh has site_count(): copy site_of, site_count and js_state from one to the other."
else
  echo "· check_deploy: neither scripts/ship.sh nor scripts/deploy.sh has site_count(), so their site: readers were not compared."
fi

if [ "$fail" = 0 ]; then echo "✓ check_deploy: all cases passed"; else echo "✗ check_deploy: failed"; exit 1; fi
