#!/usr/bin/env bash
# Deploy this site as a Cloudflare Worker from this folder, with no GitHub connection:
#   npm run deploy:preview   a Preview, to look at (builds the files as they are)
#   npm run deploy:live      the live Worker (stops if any file is unsaved or the branch is not PROD_BRANCH)
# Add `-- --dry-run` to do everything up to Wrangler and print the command instead. Workers
# sites only: a Pages site must not take this file until it has moved.
#
# The build runs as Workers Builds runs it: WORKERS_CI=1, and for `live` WORKERS_CI_BRANCH set
# to PROD_BRANCH (src/config.ts), which is what switches analytics on. Every CF_* and
# CLOUDFLARE_* variable is removed first, so no build package can read a token from them, and
# build-marker.mjs takes the commit from git. Wrangler itself runs with your own environment.
#
# The body is the function `deploy`, called on the last line: bash reads a script as it runs
# it, and an edit saved mid-deploy would otherwise run. Nothing here may replace the shell with
# another program.
deploy() {
  local mode="" dry=0 arg
  for arg in "$@"; do
    case "$arg" in
      preview|live) [ -z "$mode" ] || { echo "✗ Give one of preview or live, not both."; return 2; }; mode="$arg" ;;
      --dry-run) dry=1 ;;
      *) echo "✗ Unknown argument '$arg'. Use: npm run deploy:preview  or  npm run deploy:live  (add -- --dry-run to try it without Cloudflare)."; return 2 ;;
    esac
  done
  [ -n "$mode" ] || { echo "✗ Say which: npm run deploy:preview  or  npm run deploy:live."; return 2; }

  CDPATH= cd -- "$(dirname -- "$0")/.." || { echo "✗ Cannot find the site's folder from $0."; return 1; }

  # Wrangler's other config names would shadow, or be shadowed by, wrangler.jsonc.
  if [ ! -f wrangler.jsonc ]; then
    echo "✗ No wrangler.jsonc in $PWD. This command deploys a Worker; without its config Wrangler could"
    echo "  publish a live workers.dev address. A site that is still on Cloudflare Pages does not use it."
    return 1
  fi
  if [ -e wrangler.json ] || [ -e wrangler.toml ]; then
    echo "✗ wrangler.jsonc is not alone: this folder also holds wrangler.json or wrangler.toml, and"
    echo "  Wrangler would read one of those instead. Keep one config file."
    return 1
  fi

  # The Worker's name, and whether the config routes a custom domain: the comments are stripped
  # outside strings, then JSON.parse. A file it cannot parse stops the run, naming the file.
  local cfg name domain
  cfg="$(node -e '
    const fs = require("fs");
    const f = process.argv[1];
    const t = fs.readFileSync(f, "utf8");
    let s = "", i = 0;
    while (i < t.length) {
      const c = t[i], d = t[i + 1];
      if (c === "\"") {
        let j = i + 1;
        while (j < t.length && t[j] !== "\"") { if (t[j] === "\\") j++; j++; }
        s += t.slice(i, j + 1); i = j + 1;
      } else if (c === "/" && d === "/") {
        while (i < t.length && t[i] !== "\n") i++;
      } else if (c === "/" && d === "*") {
        const j = t.indexOf("*/", i + 2);
        if (j < 0) { console.error(f + " has a comment that never ends."); process.exit(1); }
        i = j + 2;
      } else { s += c; i++; }
    }
    let conf;
    try { conf = JSON.parse(s); } catch (e) {
      console.error(f + " is not JSON with comments (a trailing comma is not allowed): " + e.message);
      process.exit(1);
    }
    const routes = Array.isArray(conf.routes) ? conf.routes : [];
    console.log("name=" + (typeof conf.name === "string" ? conf.name : ""));
    console.log("domain=" + (routes.some((r) => r && r.custom_domain === true) ? "yes" : "no"));
  ' wrangler.jsonc)" || { echo "✗ Cannot read wrangler.jsonc (see above). Nothing was built or deployed."; return 1; }
  name="$(sed -n 's/^name=//p' <<<"$cfg")"
  domain="$(sed -n 's/^domain=//p' <<<"$cfg")"
  if [ -z "$name" ]; then
    echo "✗ wrangler.jsonc has no \"name\". Nothing was built or deployed."
    return 1
  fi
  if [ "$name" = example-site ]; then
    echo "✗ wrangler.jsonc still has the placeholder name \"example-site\". Set \"name\" to this site's Worker"
    echo "  name first. Nothing was built or deployed."
    return 1
  fi

  local id=""
  if [ "$mode" = live ]; then
    if ! id="$(git rev-parse HEAD 2>/dev/null)" || [ -z "$id" ]; then
      echo "✗ This folder is not a git repository with a commit, so the live build has no commit to name."
      return 1
    fi
    local unsaved
    unsaved="$(git status --porcelain 2>/dev/null)" || { echo "✗ git could not read this folder's state."; return 1; }
    if [ -n "$unsaved" ]; then
      echo "✗ Unsaved changes. The live site must be exactly a commit, so build.txt can name what is served."
      echo "  Save them as a commit first:"
      echo "$unsaved" | sed 's/^/    /'
      return 1
    fi
  fi

  local prod=""
  if [ "$mode" = live ]; then
    prod="$(sed -nE "s/^export const PROD_BRANCH = ['\"]([^'\"]*)['\"];?.*/\1/p" src/config.ts)"
    if [ -z "$prod" ]; then
      echo "✗ No \"export const PROD_BRANCH = '…';\" line in src/config.ts: the live build needs it."
      return 1
    fi
    # Only the production branch goes live, as with a push: a Git-connected Worker builds that
    # branch, and would undo another branch's commit at its next build.
    # The full ref: with a tag of the same name, git's short name would be "heads/<branch>".
    local ref
    ref="$(git symbolic-ref -q HEAD 2>/dev/null || true)"
    if [ "$ref" != "refs/heads/$prod" ]; then
      local on="no branch"
      [ -z "$ref" ] || on="the branch \"${ref#refs/heads/}\""
      echo "✗ The live site comes from the branch \"$prod\" (PROD_BRANCH in src/config.ts), but this folder is on $on."
      echo "  Switch to it first (git switch $prod), or look at this one with npm run deploy:preview. Nothing was built or deployed."
      return 1
    fi
  fi

  # Build with a fixed environment (see the header).
  local -a unset_args=()
  local v
  for v in $(env | sed -n -E 's/^((CF|CLOUDFLARE)_[A-Za-z0-9_]*)=.*/\1/p'); do unset_args+=(-u "$v"); done
  unset_args+=(-u WORKERS_CI_BRANCH)
  local -a set_args=(WORKERS_CI=1)
  [ "$mode" != live ] || set_args+=("WORKERS_CI_BRANCH=$prod")
  echo "→ Building ($mode)…"
  env "${unset_args[@]}" "${set_args[@]}" npm run build || { echo "✗ The build failed. Nothing was deployed."; return 1; }

  local cmd
  if [ "$mode" = live ]; then cmd="wrangler deploy"; else cmd="wrangler preview"; fi
  if [ "$dry" = 1 ]; then
    echo "✓ Dry run: built the $mode files. Not run (no login, nothing sent): $cmd"
    return 0
  fi
  echo "→ $cmd"
  npx --no-install $cmd || { echo "✗ $cmd failed (its own message is above). The site was not changed by this run."; return 1; }
  [ "$mode" = live ] || return 0

  if [ "$domain" != yes ]; then
    echo "✓ Deployed the Worker \"$name\". wrangler.jsonc has no custom_domain route, so"
    echo "  there is no address to check here (a domain added in the dashboard is not looked at). Look at it with npm run deploy:preview."
    return 0
  fi

  # With a domain: the build wrote its commit to /build.txt (scripts/build-marker.mjs). Poll the
  # site until it serves this one, 10 s apart for about 6 minutes (the slowest Workers build seen
  # took about 300 s; scripts/ship.sh waits the same).
  local site matches
  matches="$(grep -oE "site:[[:space:]]*['\"]https?://[^'\"]+" astro.config.mjs || true)"
  site="$(sed -E "s/site:[[:space:]]*['\"]//" <<<"$matches")"
  site="${site%/}"
  if [ -z "$site" ] || [ "$(grep -c . <<<"$matches")" != 1 ]; then
    echo "✓ Deployed the Worker \"$name\", but astro.config.mjs has no single site: address, so this cannot check"
    echo "  the live site. In a few minutes your live URL's /build.txt should show $id."
    return 0
  fi
  echo "→ Verifying $site serves this build (about 6 min)…"
  local i live
  for i in $(seq 1 36); do
    sleep 10 || true
    live="$(curl -sfL -m 8 "$site/build.txt?cb=$RANDOM$i" 2>/dev/null | tr -d '[:space:]')" || true
    if [ "$live" = "$id" ]; then
      echo "✓ LIVE — verified: $site is serving build ${id:0:12} (after $((i * 10))s)."
      return 0
    fi
  done
  echo "⚠ Deployed, but after 6 minutes $site/build.txt does not show ${id:0:12} yet."
  echo "  In a few minutes it should. If it does not, check the domain's route in the Cloudflare"
  echo "  dashboard (Workers & Pages → $name → Settings → Domains & Routes)."
  return 1
}

deploy "$@"; exit "$?"
