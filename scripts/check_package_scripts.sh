#!/usr/bin/env bash
# Guard: every shell script under scripts/ ships in the handoff zip. package.sh names each one
# by hand, in its `zip -r` line and in REQUIRED; this fails when a script is missing from
# either, when one of that line's -x patterns matches it, or when either names a script that
# is gone.
#
# Why: the guards name scripts too (check_cdpath_safe.sh must list every one), and run again
# inside the unzipped zip. A script the guards list but the zip lacks passes `make check` here
# and fails it there, which CI's macos-stock-tools job found only after the push (#445).
#
# No script may stay out: the CDPATH guard would still list it, and fail inside the zip. A
# script that must not ship needs those guards taught first.
set -uo pipefail
CDPATH= cd -- "$(dirname -- "$0")/.." || { echo "FAIL — cannot cd to the repo root from $0."; exit 1; }

PKG=scripts/package.sh
all="$(bash scripts/list_shell_scripts.sh)" || { printf '%s\n' "$all"; exit 1; }
found="$(grep '^scripts/' <<<"$all")"

# The zip command runs from its `zip -r` line to the one that ends in >/dev/null. Each token
# starting scripts/ before -x is a file it ships; every token after -x is a pattern it drops.
# Tokens are split on spaces, not parsed as shell, so a -x token with a backslash or a quote
# that is not one whole pair around it (a space inside quotes) is refused, not misread.
parsed="$(awk '
  /^zip -r/ { z = 1 }
  z {
    for (i = 1; i <= NF; i++) {
      t = $i
      if (t ~ /^>/) { z = 0; break }
      if (t == "-x") { x = 1; continue }
      if (x && t != "\\" && (t ~ /\\/ || t ~ /^["\047].*[^"\047]$|^[^"\047].*["\047]|^["\047]$/)) { print "bad " t; continue }
      gsub(/^["\047]|["\047]$/, "", t)
      if (x && t != "\\") print "exc " t
      else if (t ~ /^scripts\//) print "inc " t
    }
  }' "$PKG")" || { echo "FAIL — could not read $PKG."; exit 1; }
zipped="$(sed -n 's/^inc //p' <<<"$parsed" | sort -u)"
excluded="$(sed -n 's/^exc //p' <<<"$parsed")"
bad="$(sed -n 's/^bad //p' <<<"$parsed")"
required="$(awk '/^REQUIRED=\(/ { r = 1; next } r && /^\)/ { r = 0 } r && $1 ~ /^scripts\// { print $1 }' "$PKG" |
            sort -u)" || { echo "FAIL — could not read REQUIRED in $PKG."; exit 1; }

# A reformatted package.sh could parse to nothing, which would compare as all-missing (loud)
# or, for the -x patterns, as none-excluded (silent). Refuse it instead.
if [ "$(grep -c . <<<"$zipped")" -lt 10 ] || [ "$(grep -c . <<<"$required")" -lt 10 ] ||
   [ -z "$excluded" ]; then
  echo "FAIL — could not read $PKG: fewer than 10 scripts in its zip -r line or REQUIRED, or no -x patterns."
  echo "    If its layout changed, update the parse in $0."
  exit 1
fi

rc=0
if [ -n "$bad" ]; then
  echo "FAIL — $PKG's zip -r line has -x patterns this guard cannot read (a backslash, or a"
  echo "    space inside quotes). Write each as one quoted word without them:"
  printf '%s\n' "$bad" | sed 's/^/    /'
  rc=1
fi
report() {  # report <paths> <message>
  [ -n "$1" ] || return 0
  echo "FAIL — $2"
  printf '%s\n' "$1" | sed 's/^/    /'
  rc=1
}
report "$(comm -23 <(printf '%s\n' "$found") <(printf '%s\n' "$zipped"))" \
  "these shell scripts are not in $PKG's zip -r line, so the handoff zip lacks them. Add each there and to REQUIRED:"
report "$(comm -23 <(printf '%s\n' "$found") <(printf '%s\n' "$required"))" \
  "these shell scripts are not in REQUIRED in $PKG. Add each there and to the zip -r line:"
report "$(comm -13 <(printf '%s\n' "$found") <(printf '%s\n' "$zipped"))" \
  "$PKG's zip -r line names these, but they no longer exist (or lost their shebang):"
report "$(comm -13 <(printf '%s\n' "$found") <(printf '%s\n' "$required"))" \
  "REQUIRED in $PKG names these, but they no longer exist (or lost their shebang):"

# bash's == matches * across /, as zip's -x does, so '*/name.sh' counts.
dropped=""
while IFS= read -r s; do
  while IFS= read -r p; do
    # shellcheck disable=SC2053  # $p is a pattern on purpose
    [[ $s == $p ]] && dropped+="$s (by -x '$p')"$'\n'
  done <<<"$excluded"
done <<<"$found"
report "${dropped%$'\n'}" "a -x pattern in $PKG's zip -r line drops these shell scripts from the zip:"

[ "$rc" = 0 ] && echo "OK — all $(grep -c . <<<"$found") shell scripts under scripts/ ship in the handoff zip (zip -r line and REQUIRED)."
exit $rc
