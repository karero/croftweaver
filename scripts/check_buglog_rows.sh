#!/usr/bin/env bash
# Guard: docs/BUGLOG.md must not hold two versions of one row. The file merges with git's
# union driver (.gitattributes), which keeps both sides when one branch edits a row that sits
# next to rows the other branch changed or added. Two rows count as versions of one row when
# they share the Found date and the Where cell, or the first 20 words of What (any date).
# A table line that is neither the header, its rule line nor a row these rules can read fails
# too, so no line starting with | (after any indent) is skipped unseen. The handoff zip leaves the file out: there it skips.
set -uo pipefail
CDPATH= cd -- "$(dirname -- "$0")/.."

F="docs/BUGLOG.md"
if [ ! -f "$F" ]; then
  if [ -e .git ]; then
    echo "FAIL — $F not found in this checkout."
    exit 1
  fi
  echo "skip — no $F (the handoff zip leaves it out)"
  exit 0
fi

report="$(awk '
  function show(n) { return length(text[n]) > 100 ? substr(text[n], 1, 100) " …" : text[n] }
  /^[ \t]*\|/ {
    l = $0; sub(/[ \t\r]+$/, "", l)
    text[NR] = l
    if (l == "| Found | Where | What | Category | Impact | Effort | Status |" || l ~ /^\|(-+\|)+$/) next
    if (l !~ /^\| [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] \| / || split(l, c, " \\| ") != 7) {
      bad = bad sprintf("  line %d: %s\n", NR, show(NR)); next
    }
    rows++
    m = split(c[3], w, " ")
    k = w[1]
    for (i = 2; i <= m && i <= 20; i++) k = k " " w[i]
    a = substr(c[1], 3) SUBSEP c[2]
    hit = ""
    if (a in byA) hit = byA[a]; else byA[a] = NR
    if (k != "") { if (k in byB) { if (hit == "") hit = byB[k] } else byB[k] = NR }
    if (hit != "") pairs = pairs sprintf("  line %d: %s\n  line %d: %s\n\n", hit, show(hit), NR, show(NR))
  }
  END {
    if (bad != "") {
      printf "FAIL — these table lines of docs/BUGLOG.md are not rows the guard can read:\n%s", bad
      print "A row starts \"| YYYY-MM-DD | \" and splits on \" | \" into the table'"'"'s 7 cells. A bare \" | \""
      print "inside a cell splits it, here and on GitHub: write it as \\|."
    }
    if (rows == 0 && bad == "") print "FAIL — no rows found in docs/BUGLOG.md (a row starts \"| YYYY-MM-DD |\")."
    if (pairs != "") {
      print "FAIL — docs/BUGLOG.md holds two rows that look like two versions of one row"
      print "       (same Found date and Where, or the same first 20 words of What):"
      printf "%s", pairs
      print "A merge probably kept both sides of an edited row (docs/BUGLOG.md merges with git'"'"'s union"
      print "driver; see .gitattributes). Make it one row: keep what each side changed, delete the rest."
      print "To see the file as it was before either side changed it, run right after the merge:"
      print "  git show \"$(git merge-base HEAD^1 HEAD^2)\":docs/BUGLOG.md"
      print "If they really are two different rows, give them different Where cells and a different start"
      print "to What."
    }
    if (bad != "" || pairs != "" || rows == 0) exit 1
    printf "ok   docs/BUGLOG.md: %d rows, none twice\n", rows
  }
' "$F")"
rc=$?
case $rc in
  0|1) printf '%s\n' "$report"; exit "$rc" ;;
  *) echo "FAIL — awk errored (exit $rc) reading $F."; exit 1 ;;
esac
