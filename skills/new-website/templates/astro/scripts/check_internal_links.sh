#!/usr/bin/env bash
# Warn-only INTERNAL-link audit. Builds the inbound-link graph of the site and prints
# which pages are ORPHANED (no internal link points at them — invisible to crawlers and
# browsing humans) or THIN (a single inbound link, usually just the nav/footer, no
# contextual in-body link). It never fails on link FINDINGS (orphan/thin pages → exit 0);
# only a broken auto-build exits non-zero, since it can't audit a missing/partial dist/.
# It's the judgment-side sweep, the script form of the `internal-link-audit` skill.
#
# The HARD gate is tests/orphans.spec.ts (offline, in CI): it fails if any page is
# unreachable from the home page. This script is the richer report you act on — it tells
# you the inbound COUNT per page (orphans AND thin pages), which the pass/fail gate can't.
#
# Usage: bash scripts/check_internal_links.sh   (builds if dist/ is missing)
# Portable to macOS bash 3.2 (no mapfile / no set -u).
cd "$(git rev-parse --show-toplevel)" || exit 0

# Audit the SHIPPED build. If dist/ is missing, build it and fail LOUDLY on a broken
# build — never print an authoritative graph from a missing/partial dist/. If dist/
# already exists, say we're reusing it (it may be stale; rebuild for a fresh audit).
if [ -d dist ]; then
  echo "ℹ using existing dist/ (not rebuilding — run 'npm run build' first for a fresh audit)" >&2
else
  echo "→ dist/ missing — building…" >&2
  if ! npm run build; then
    echo "✗ build failed — cannot audit links against a missing/partial dist/. Fix the build, then re-run." >&2
    exit 1
  fi
fi

# Own production host, derived from `site:` in astro.config.mjs so this stays
# domain-agnostic. An absolute link to this host counts as internal, same as the tests.
SITE_HOST=$(grep -oE "site:[[:space:]]*['\"]https?://[^'\"]+" astro.config.mjs 2>/dev/null \
  | sed -E "s#.*://(www\.)?##; s#/.*##" | tr 'A-Z' 'a-z' | head -1)
[ -n "$SITE_HOST" ] || SITE_HOST="__no_site_configured__"

# dist/<name>.html  ->  /<name>   (build.format:'file');  dist/index.html -> /
file_to_path() {
  local f="${1#dist}"; f="${f%.html}"
  case "$f" in
    /index|"") echo "/" ;;
    */index)   echo "${f%/index}" ;;   # tolerate format:'directory' too
    *)         echo "$f" ;;
  esac
}

# href -> in-site page path, or non-zero for an external / non-page link. Drops the
# query + fragment (a link to /x?a#b still reaches page /x) and the trailing slash.
#
# Resolves ROOT-RELATIVE (/about) and ABSOLUTE-on-host (https://site/about) links — the
# kit's link convention. It does NOT resolve PAGE-RELATIVE hrefs (about, ./team,
# ../pricing): those are dropped, so a page reachable ONLY via a page-relative link is
# over-reported here as ORPHAN/THIN. The hard gate `tests/orphans.spec.ts` DOES resolve
# them (via `new URL`) and is authoritative; this advisory script intentionally stays
# simple. Prefer root-relative links (the convention) and this divergence never bites.
normalize() {
  local h="$1" rest host
  case "$h" in
    //*) return 1 ;;                                   # protocol-relative = external
    http://*|https://*)
      rest="${h#*://}"; host=$(printf '%s' "${rest%%/*}" | tr 'A-Z' 'a-z'); host="${host#www.}"
      [ "$host" = "$SITE_HOST" ] || return 1   # case-insensitive, matching orphans.spec.ts
      case "$rest" in */*) h="/${rest#*/}" ;; *) h="/" ;; esac ;;
    /*) : ;;                                           # root-relative
    *)  return 1 ;;                                    # mailto:/tel:/#frag/PAGE-relative (see header)
  esac
  h="${h%%[?#]*}"; h="${h%/}"; [ -z "$h" ] && h="/"
  echo "$h"
}

LINKS=$(mktemp); PAGESF=$(mktemp)
trap 'rm -f "$LINKS" "$PAGESF"' EXIT

# One pass over the built HTML: record every page, and every "target<TAB>source" edge.
for f in $(find dist -name '*.html' 2>/dev/null); do
  src=$(file_to_path "$f")
  echo "$src" >> "$PAGESF"
  grep -oE '<a [^>]*href="[^"]+"' "$f" 2>/dev/null \
    | grep -oE 'href="[^"]+"' | sed -E 's/^href="//; s/"$//; s/&#x26;/\&/g; s/&amp;/\&/g' \
    | while IFS= read -r href; do
        tgt=$(normalize "$href") && printf '%s\t%s\n' "$tgt" "$src"
      done >> "$LINKS"
done

NPAGES=$(sort -u "$PAGESF" | grep -c .)
NLINKS=$(grep -c . "$LINKS")

# Distinct (target,source) inbound count per page, ignoring self-links.
INBOUND=$(awk -F'\t' '$1!=$2 && !seen[$1 SUBSEP $2]++ { cnt[$1]++ }
                      END { for (t in cnt) print cnt[t] "\t" t }' "$LINKS")

# Orphans = pages that received zero inbound edges (and aren't the home root).
orphans=""; thin=""
while IFS= read -r p; do
  [ -n "$p" ] || continue
  [ "$p" = "/" ] && continue
  c=$(echo "$INBOUND" | awk -F'\t' -v t="$p" '$2==t{print $1}')
  if [ -z "$c" ]; then
    orphans="$orphans$p
"
  elif [ "$c" = "1" ]; then
    one=$(awk -F'\t' -v t="$p" '$1==t && $1!=$2 {print $2; exit}' "$LINKS")
    thin="$thin$p  <-  $one
"
  fi
done < <(sort -u "$PAGESF")

norphan=$(printf '%s' "$orphans" | grep -c .)
nthin=$(printf '%s' "$thin" | grep -c .)

# Click depth from the home page (BFS over source→target edges via fixed-point
# relaxation — fine for a marketing site's handful of pages). The internal-linking
# strategy (see the internal-link-audit / site-architecture skills) wants important
# pages within ~3 clicks of home: a deeper page bleeds crawl priority and PageRank.
DEEP=$(awk -F'\t' '
  # Discriminate by tab, not FNR==NR: an empty LINKS file would make the FNR==NR idiom
  # misread the first PAGES line as an edge. Edge lines have a tab; PAGES paths never do.
  /\t/    { e_src[++ne]=$2; e_tgt[ne]=$1; next }        # LINKS: source($2) -> target($1)
  { pages[$0]=1 }                                       # PAGES line (no tab)
  END {
    for (p in pages) depth[p] = -1
    depth["/"] = 0
    changed = 1
    while (changed) {
      changed = 0
      for (i=1;i<=ne;i++) {
        s=e_src[i]; t=e_tgt[i]
        if (depth[s] >= 0 && (t in pages) && (depth[t] < 0 || depth[t] > depth[s]+1)) {
          depth[t] = depth[s] + 1; changed = 1
        }
      }
    }
    for (p in pages) if (depth[p] > 3) print depth[p] "\t" p   # >3 clicks from home
  }
' "$LINKS" "$PAGESF" | sort -rn)
ndeep=$(printf '%s' "$DEEP" | grep -c .)

printf '# Internal link audit — %d pages, %d internal links\n' "$NPAGES" "$NLINKS"

printf '\n## ORPHANS — in the build but NO internal link points here (%d)\n' "$norphan"
if [ "$norphan" -gt 0 ]; then
  printf '%s' "$orphans"
  printf '%s\n' '→ Add a contextual in-body link from a related page, or a nav/footer entry in'
  printf '%s\n' '  src/config.ts. Sibling pages (e.g. all the X-vs-Y comparisons) should cross-link;'
  printf '%s\n' '  a footer group that lists only ONE of a set leaves the rest orphaned.'
else
  printf '(none — every page is linked)\n'
fi

printf '\n## THIN — exactly one inbound link, usually just the nav/footer (%d)\n' "$nthin"
if [ "$nthin" -gt 0 ]; then
  printf '%s' "$thin"
  printf '%s\n' '→ Not broken, but weakly connected: one contextual in-body link from a topically'
  printf '%s\n' '  related page strengthens crawl depth and internal PageRank.'
else
  printf '(none)\n'
fi

printf '\n## OK: %d page(s) with ≥2 inbound links (home + orphan/thin excluded)\n' "$((NPAGES - norphan - nthin - 1))"

# Click-depth is an ORTHOGONAL axis (a page can be both thin AND deep), so it's
# reported separately rather than folded into the inbound-count partition above.
printf '\n## DEEP — more than 3 clicks from the home page (%d)\n' "$ndeep"
if [ "$ndeep" -gt 0 ]; then
  printf '%s\n' "$DEEP" | while IFS="$(printf '\t')" read -r d p; do printf '%s clicks  %s\n' "$d" "$p"; done
  printf '%s\n' '→ Add a link from a shallower hub/section page so important content sits within'
  printf '%s\n' '  ~3 clicks of home (crawl depth — see site-architecture internal-linking strategy).'
else
  printf '(none — every reachable page is within 3 clicks of home)\n'
fi

printf '\n_Warn-only: this check never fails the build. Hard gate is tests/orphans.spec.ts._\n'

exit 0
