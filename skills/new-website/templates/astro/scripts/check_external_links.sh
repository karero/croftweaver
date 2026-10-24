#!/usr/bin/env bash
# Warn-only outgoing-link liveness check. Fetches every external link in the built
# site and prints a grouped report. It NEVER fails the build (always exits 0) — link
# rot depends on third-party uptime and bot policies, which must not gate a deploy.
# The hard gate is tests/links.spec.ts (offline, blocks known-dead domains). This is
# the network-dependent complement, the script form of the `outgoing-link-audit`
# skill, used for the pre-launch warning and the monthly scheduled run.
#
# Usage: bash scripts/check_external_links.sh   (builds if dist/ is missing)
# Portable to macOS bash 3.2 (no mapfile / no set -u).
cd "$(git rev-parse --show-toplevel)" || exit 0

[ -d dist ] || npm run build >/dev/null 2>&1

# Own production host, derived from `site:` in astro.config.mjs so this stays
# domain-agnostic across sites. Falls back to matching nothing if unset.
SITE_HOST=$(grep -oE "site:[[:space:]]*['\"]https?://[^'\"]+" astro.config.mjs 2>/dev/null \
  | sed -E "s#.*://(www\.)?##; s#/.*##" | head -1)
[ -n "$SITE_HOST" ] || SITE_HOST="__no_site_configured__"

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"

# Distinct external destinations from ANCHORS only (matches tests/links.spec.ts's
# a[href] scope — excludes <link rel="dns-prefetch"> resource hints, which 404 on the
# bare host but aren't navigable links). Decode &#x26;->&, drop our own domain.
URLS=()
while IFS= read -r line; do URLS+=("$line"); done < <(
  grep -rhoE '<a [^>]*href="https?://[^"]+"' dist --include='*.html' \
    | grep -oE 'href="https?://[^"]+"' \
    | sed -E 's/^href="//; s/"$//' \
    | grep -vE "://(www\.)?${SITE_HOST}(/|$|:)" \
    | sed -E 's/&#x26;/\&/g' \
    | sort -u
)

host() { local h="${1#*://}"; h="${h%%/*}"; echo "${h#www.}"; }

dead=(); redirect=(); unverified=(); ok=0
for url in "${URLS[@]}"; do
  out=$(curl -sS -o /dev/null -A "$UA" -L --max-time 25 \
        -w '%{http_code} %{url_effective}' "$url" 2>/dev/null) || out="000 $url"
  code="${out%% *}"; final="${out#* }"
  case "$code" in
    200)
      if [ "$(host "$url")" != "$(host "$final")" ]; then
        redirect+=("$url  ->  $final")
      else
        ok=$((ok + 1))
      fi ;;
    404 | 410 | 5??) dead+=("$code  $url  ->  $final") ;;
    *)               unverified+=("$code  $url") ;;   # 403/429/999/000 = usually bot-block
  esac
done

emit() {  # emit "Title" "${array[@]}"
  local title="$1"; shift
  printf '\n## %s (%d)\n' "$title" "$#"
  if [ "$#" -gt 0 ]; then printf '%s\n' "$@"; else printf '(none)\n'; fi
}

printf '# Outgoing link audit — %d distinct external links\n' "${#URLS[@]}"
emit 'DEAD — 4xx/5xx, fix or remove' ${dead[@]+"${dead[@]}"}
emit 'REDIRECT off-domain — review for rebrand' ${redirect[@]+"${redirect[@]}"}
emit 'UNVERIFIED — likely bot-blocked (403/429/999/timeout), not necessarily dead' ${unverified[@]+"${unverified[@]}"}
printf '\n## OK: %d links healthy (200, same domain)\n' "$ok"
printf '\n_Warn-only: this check never fails the build. Hard gate is tests/links.spec.ts._\n'

exit 0
