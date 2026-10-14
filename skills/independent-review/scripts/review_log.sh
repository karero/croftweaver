#!/usr/bin/env bash
#
# review_log.sh — the cost log of independent-review: one line per reviewer seat per round, so
# the review depths (SKILL.md, "Review depth") and effort levels can be tuned from numbers rather
# than impressions. The log is LOCAL — it never goes in a repo, so it adds no paperwork.
#
#   review_log.sh add --seat <name> [--model M] [--effort E] [--seconds S] [--tokens T]
#                     [--gate plan|diff] [--depth light|normal|high] [--round N] [--outcome O]
#                     [--earned-by KIND] [--cut TEXT]
#       Append one line. independent_review.sh calls this for codex, ollama, melious and agy; the host
#       calls it for the seats it runs itself (fresh-eyes, code-review, double-knuth, owner).
#       Repo, branch and head come from the current directory's git checkout, if any.
#       --earned-by lists the kinds of finding (comma-separated) that earned a round past round 3,
#       and --cut says what the fix since the last round removed or refused (SKILL.md step 6);
#       independent_review.sh checks both before a round runs.
#   review_log.sh new-gate
#       Start a gate: mint an id and keep it in this worktree's git dir. independent_review.sh
#       calls it for --round 1; every later line (its own seats and the host's) carries that id
#       until the next one, so two gates on one reused branch stay two gates. The gate file's
#       second line names the gate this one follows, so a restart cannot hide what came before.
#   review_log.sh summary [--since YYYY-MM-DD] [--repo NAME]
#       Per depth and seat: runs, OK runs, mean and max seconds, mean tokens where known;
#       then rounds per gate by depth (lines logged before gate ids existed: per repo, branch
#       and gate type).
#   review_log.sh gate [--id ID]
#       Up to three lines on the current gate (the id new-gate wrote in this worktree), or on
#       gate ID: the rounds seen, the reviewer seat runs, the tokens summed where a run gave a
#       figure and how many runs gave none; then each round's kinds and cuts, and the runs with no
#       round; then the gate this one follows, if any. independent_review.sh prints them after
#       each run: the owner reads them, so they show what the host did, not only what it cost.
#       Nothing, and exit 0, with no gate or no log.
#   review_log.sh round-check [--round N] [--kinds K1,K2] [--id ID]
#       What independent_review.sh's round checks need, one tab-separated record a line:
#         gate  <id> <highest round logged> <seat runs at that round> <rounds logged below N>
#         owed  <kind> <rounds> <kind as logged>   the kind earned those rounds since its last cut
#         like  <kind> <earlier kind> <its round>  one normalised name starts the other
#       Kinds compare normalised: lower case, without '.', '_' and '-'. A round's kinds are the
#       union of its lines' kinds; a cut on a round settles the kinds that round named. When it
#       cannot tell (log off, missing or unreadable, no gate), it prints "?", a tab and why.
#
# Columns 15 and 16 (earned_by, cut) came after the log existed: an older line has 14 fields,
# and an older log keeps its 14-column header (lines are appended, the file is never rewritten).
# Every reader takes a missing field as "-".
#
# Log file: $REVIEW_LOG, else ${XDG_STATE_HOME:-$HOME/.local/state}/independent-review/runs.tsv.
# REVIEW_LOG=off turns logging off. A failure to log warns and exits 0: bookkeeping never fails
# a review.
set -u
HEADER=$'date\trepo\tbranch\thead\tgate\tdepth\tround\tseat\tmodel\teffort\tseconds\ttokens\toutcome\tgate_id\tearned_by\tcut'
log_path() {   # empty when logging is off
  if [ "${REVIEW_LOG:-}" = off ]; then return 0
  elif [ -n "${REVIEW_LOG:-}" ]; then printf '%s' "$REVIEW_LOG"
  else printf '%s' "${XDG_STATE_HOME:-$HOME/.local/state}/independent-review/runs.tsv"; fi
}
clean() { printf '%s' "${1:--}" | tr '\t\n\r' '   '; }   # one TSV field, never empty
gate_file() { git rev-parse --git-path independent-review-gate 2>/dev/null; }   # empty outside git

gate_has_lines() {   # <id>: true unless the log can show it holds no line of that gate
  local f; f="$(log_path)"
  { [ -n "$f" ] && [ -r "$f" ]; } || return 0
  awk -F'\t' -v id="$1" '$14 == id { found = 1; exit } END { exit !found }' "$f"
}

new_gate() {
  local id f old="" oldprev="" prev=""
  id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
  f="$(gate_file)"
  [ -z "$f" ] || [ ! -r "$f" ] || { IFS= read -r old; IFS= read -r oldprev; } <"$f" || true
  # The old gate becomes this one's predecessor. One that logged nothing (a round 1 refused or
  # restarted at once) is skipped over, so a string of restarts cannot hide the gate that cost.
  if [ -n "$old" ]; then
    if gate_has_lines "$old"; then prev="$old"; else prev="$oldprev"; fi
  fi
  if [ -n "$f" ]; then
    if [ -n "$prev" ]; then printf '%s\n%s\n' "$id" "$prev"; else printf '%s\n' "$id"; fi >"$f" 2>/dev/null || true
  fi
  printf '%s\n' "$id"
}

add() {
  local seat="" model="" effort="" seconds="" tokens="" gate="" depth="" round="" outcome="OK" gate_id=""
  local earned_by="" cut=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --seat|--model|--effort|--seconds|--tokens|--gate|--depth|--round|--outcome|--gate-id|--earned-by|--cut)
        [ $# -ge 2 ] || { echo "review_log.sh: $1 needs a value" >&2; return 2; }
        local k="${1#--}"; k="${k//-/_}"; printf -v "$k" '%s' "$2"; shift 2 ;;
      *) echo "review_log.sh: unknown argument: $1" >&2; return 2 ;;
    esac
  done
  [ -n "$seat" ] || { echo "review_log.sh add: --seat is required" >&2; return 2; }
  local f repo="-" branch="-" head="-" top
  f="$(log_path)"
  [ -n "$f" ] || return 0
  if top="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    repo="$(basename -- "$top")"
    branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo -)"
    head="$(git rev-parse --short=7 HEAD 2>/dev/null || echo -)"
  fi
  if [ -z "$gate_id" ]; then
    local gf; gf="$(gate_file)"
    [ -z "$gf" ] || [ ! -r "$gf" ] || IFS= read -r gate_id <"$gf" || true
  fi
  # The header is APPENDED, like every line: two seats finishing together on a new log (codex
  # and ollama run in parallel) may both see it empty, and a `>` could then overwrite a line
  # the other had written. Appending loses nothing; the worst case is a second header line,
  # which summary skips as it skips the first (by its content).
  { mkdir -p -- "$(dirname -- "$f")" &&
    { [ -s "$f" ] || printf '%s\n' "$HEADER" >>"$f"; } &&
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(clean "$repo")" "$(clean "$branch")" "$(clean "$head")" \
      "$(clean "$gate")" "$(clean "$depth")" "$(clean "$round")" "$(clean "$seat")" \
      "$(clean "$model")" "$(clean "$effort")" "$(clean "$seconds")" "$(clean "$tokens")" \
      "$(clean "$outcome")" "$(clean "$gate_id")" "$(clean "$earned_by")" "$(clean "$cut")" >>"$f"; } 2>/dev/null \
    || echo "note: could not write the review cost log ($f) — the review itself is unaffected." >&2
  return 0
}

summary() {
  local since="" repo=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --since|--repo) [ $# -ge 2 ] || { echo "review_log.sh: $1 needs a value" >&2; return 2; } ;;
    esac
    case "$1" in
      --since) since="$2"; shift 2 ;;
      --repo)  repo="$2"; shift 2 ;;
      *) echo "review_log.sh: unknown argument: $1" >&2; return 2 ;;
    esac
  done
  local f; f="$(log_path)"
  [ -n "$f" ] || { echo "the review cost log is off (REVIEW_LOG=off)"; return 0; }
  [ -s "$f" ] || { echo "no review cost log yet ($f)"; return 0; }
  awk -F'\t' -v since="$since" -v want="$repo" '
    $1 == "date" { next }
    since != "" && substr($1, 1, 10) < since { next }
    want != "" && $2 != want { next }
    {
      k = $6 "\t" $8
      n[k]++; if ($13 == "OK") ok[k]++
      if ($11 ~ /^[0-9]+$/) { s[k] += $11; sn[k]++; if (!(k in mx) || $11 + 0 > mx[k]) mx[k] = $11 + 0 }
      if ($12 ~ /^[0-9]+$/) { t[k] += $12; tn[k]++ }
      # One gate: its id, or for lines from before ids existed, repo + branch + gate type.
      g = $6 "\t" (($14 != "" && $14 != "-") ? $14 : $2 "\t" $3 "\t" $5)
      if ($7 ~ /^[0-9]+$/ && $7 + 0 > r[g] + 0) r[g] = $7 + 0
    }
    END {
      printf "%-8s %-14s %5s %5s %8s %8s %11s\n", "depth", "seat", "runs", "ok", "mean s", "max s", "mean tokens"
      for (k in n) {
        split(k, p, "\t")
        printf "%-8s %-14s %5d %5d %8s %8s %11s\n", p[1], p[2], n[k], ok[k] + 0, \
          (sn[k] ? sprintf("%.0f", s[k] / sn[k]) : "-"), (sn[k] ? mx[k] : "-"), \
          (tn[k] ? sprintf("%.0f", t[k] / tn[k]) : "-")
      }
      for (g in r) { split(g, p, "\t"); gates[p[1]]++; rs[p[1]] += r[g]; if (r[g] > rmx[p[1]] + 0) rmx[p[1]] = r[g] }
      printf "\n%-8s %6s %12s %11s\n", "depth", "gates", "mean rounds", "max rounds"
      for (d in gates) printf "%-8s %6d %12.1f %11d\n", d, gates[d], rs[d] / gates[d], rmx[d]
    }' "$f"
}

current_gate() {   # the id new-gate wrote in this worktree, or nothing
  local gf id=""
  gf="$(gate_file)"
  [ -z "$gf" ] || [ ! -r "$gf" ] || IFS= read -r id <"$gf" || true
  printf '%s' "$id"
}
previous_gate() {   # the gate the current one follows (the gate file's second line), or nothing
  local gf one="" two=""
  gf="$(gate_file)"
  [ -z "$gf" ] || [ ! -r "$gf" ] || { IFS= read -r one; IFS= read -r two; } <"$gf" || true
  printf '%s' "$two"
}

gate() {
  local id="" prev="" f
  while [ $# -gt 0 ]; do
    case "$1" in
      --id) [ $# -ge 2 ] || { echo "review_log.sh: --id needs a value" >&2; return 2; }
            id="$2"; shift 2 ;;
      *) echo "review_log.sh gate: unknown argument: $1 (gate takes only --id)" >&2; return 2 ;;
    esac
  done
  # The predecessor is known only for the worktree's current gate.
  if [ -z "$id" ] || [ "$id" = "$(current_gate)" ]; then id="$(current_gate)"; prev="$(previous_gate)"; fi
  f="$(log_path)"
  { [ -n "$id" ] && [ -n "$f" ] && [ -s "$f" ]; } || return 0
  [ -r "$f" ] || { echo "note: could not read the review cost log ($f) — no running total; the review itself is unaffected." >&2; return 0; }
  # Rounds print as ranges ("rounds 1-3, 5"): a round the log missed shows as a gap, not as a
  # round that never ran. A run with no figure is counted apart, and the line names what it
  # does not count, so a sum of logged seats is never read as the whole cost. The kinds line
  # shows a rename, a rotation among kinds or a cut where the owner reads (SKILL.md step 6).
  awk -F'\t' -v id="$id" -v prev="$prev" '
    function commas(n,   s, out) {
      s = sprintf("%.0f", n); out = ""
      while (length(s) > 3) { out = "," substr(s, length(s) - 2) out; s = substr(s, 1, length(s) - 3) }
      return s out
    }
    function ranges(g,   i, s, k, start) {
      s = ""; k = 0
      for (i = 1; i <= 100; i++) {
        if (!((g, i) in seen)) continue
        k++
        if (!((g, i - 1) in seen)) start = i
        if (!((g, i + 1) in seen)) s = s (s == "" ? "" : ", ") (start == i ? i : start "-" i)
      }
      return k == 0 ? "no numbered round" : ((k == 1 ? "round " : "rounds ") s)
    }
    function plural(n, word) { return n " " word (n == 1 ? "" : "s") }
    $1 == "date" { next }
    { g = ($14 == id) ? 1 : ((prev != "" && $14 == prev) ? 2 : 0) }
    g == 0 { next }
    {
      n[g]++
      if ($12 ~ /^[0-9]+$/) t[g] += $12; else none[g]++
      if ($7 !~ /^[0-9]+$/) { if (g == 1) noround++; next }
      r = $7 + 0; seen[g, r] = 1
      if (g != 1) next
      m = split($15, ks, ",")
      for (i = 1; i <= m; i++) {
        k = tolower(ks[i]); gsub(/[._-]/, "", k)
        if (k == "" || ((r, k) in has)) continue
        has[r, k] = 1; kl[r] = kl[r] (kl[r] == "" ? "" : ",") ks[i]
      }
      if ($16 != "" && $16 != "-") ct[r] = $16
    }
    END {
      if (!n[1]) exit
      printf "gate %s: %s, %s, %s tokens logged", id, ranges(1), plural(n[1], "reviewer seat run"), commas(t[1])
      if (none[1]) printf " (%s gave no figure)", plural(none[1], "run")
      printf ". Not counted: the fixes, the host'"'"'s own work, and fresh-eyes unless the host logged it.\n"
      s = ""
      for (i = 1; i <= 100; i++) {
        if (!(i in kl) && !(i in ct)) continue
        s = s (s == "" ? "" : "; ") i " " ((i in kl) ? kl[i] : "no kind") ((i in ct) ? " (cut: " ct[i] ")" : "")
      }
      if (s != "") s = "kinds: " s
      if (noround) s = s (s == "" ? "" : "; ") plural(noround, "run") " with no round"
      if (s != "") print s
      if (n[2]) printf "follows gate %s: %s, %s tokens\n", prev, ranges(2), commas(t[2])
    }' "$f" || echo "note: could not read the review cost log ($f) — no running total; the review itself is unaffected." >&2
  return 0
}

round_check() {
  local id="" want="" kinds="" f out
  while [ $# -gt 0 ]; do
    case "$1" in
      --id|--round|--kinds) [ $# -ge 2 ] || { echo "review_log.sh: $1 needs a value" >&2; return 2; } ;;
    esac
    case "$1" in
      --id) id="$2"; shift 2 ;;
      --round) case "$2" in ''|*[!0-9]*) echo "review_log.sh: --round needs a number" >&2; return 2 ;; esac
               want="$2"; shift 2 ;;
      --kinds) kinds="$2"; shift 2 ;;
      *) echo "review_log.sh round-check: unknown argument: $1" >&2; return 2 ;;
    esac
  done
  f="$(log_path)"
  [ -n "$f" ] || { printf '?\t%s\n' "the review cost log is off: REVIEW_LOG=off"; return 0; }
  [ -n "$id" ] || id="$(current_gate)"
  [ -n "$id" ] || { printf '?\t%s\n' "no gate started in this worktree; --round 1 starts one"; return 0; }
  [ -e "$f" ] || { printf '?\t%s\n' "no review cost log yet at $f"; return 0; }
  [ -r "$f" ] || { printf '?\t%s\n' "cannot read the review cost log at $f"; return 0; }
  # Every logged round below N counts, not only N-1: kinds that alternate (A, B, A) are caught,
  # and a skipped or repeated round number does not reset anything. Lines older than the two
  # columns have no field 15 or 16, which reads as no kind and no cut.
  out="$(awk -F'\t' -v id="$id" -v want="$want" -v kinds="$kinds" '
    function norm(s) { s = tolower(s); gsub(/[._-]/, "", s); return s }
    $1 == "date" || $14 != id || $7 !~ /^[0-9]+$/ { next }
    {
      r = $7 + 0
      if (r > max) max = r
      runs[r]++
      if (want == "" || r >= want + 0) next
      below[r] = 1
      m = split($15, ks, ",")
      for (i = 1; i <= m; i++) {
        k = norm(ks[i]); if (k == "") continue
        has[r, k] = 1; seen[k] = 1; if (!(k in disp)) disp[k] = ks[i]
      }
      if ($16 != "" && $16 != "-") cutr[r] = 1
    }
    END {
      nb = 0; for (r in below) nb++
      printf "gate\t%s\t%d\t%d\t%d\n", id, max, (max ? runs[max] : 0), nb
      m = split(kinds, gs, ",")
      for (j = 1; j <= m; j++) {
        g = norm(gs[j]); if (g == "" || (g in done)) continue
        done[g] = 1
        last = 0
        for (r = 1; r < want + 0; r++) if (((r, g) in has) && (r in cutr)) last = r
        rs = ""
        for (r = last + 1; r < want + 0; r++) if ((r, g) in has) rs = rs (rs == "" ? "" : ", ") r
        if (rs != "") printf "owed\t%s\t%s\t%s\n", gs[j], rs, disp[g]
        for (k in seen) {
          if (k == g || (index(k, g) != 1 && index(g, k) != 1)) continue
          lr = 0; for (r = 1; r < want + 0; r++) if ((r, k) in has) lr = r
          printf "like\t%s\t%s\t%d\n", gs[j], disp[k], lr
        }
      }
    }' "$f")" || { printf '?\t%s\n' "cannot read the review cost log at $f"; return 0; }
  printf '%s\n' "$out"
}

case "${1:-}" in
  add)     shift; add "$@" ;;
  new-gate) new_gate ;;
  summary) shift; summary "$@" ;;
  gate)    shift; gate "$@" ;;
  round-check) shift; round_check "$@" ;;
  *) echo "usage: review_log.sh add --seat <name> [...] | review_log.sh new-gate | review_log.sh summary [--since YYYY-MM-DD] [--repo NAME] | review_log.sh gate [--id ID] | review_log.sh round-check [--round N] [--kinds K1,K2] [--id ID]" >&2; exit 2 ;;
esac
