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
#       --earned-by is the kind of finding that earned a round past round 3, and --cut what the
#       fix since the last round removed or refused (SKILL.md step 6); independent_review.sh
#       checks both before a round runs.
#   review_log.sh new-gate
#       Start a gate: mint an id and keep it in this worktree's git dir. independent_review.sh
#       calls it for --round 1; every later line (its own seats and the host's) carries that id
#       until the next one, so two gates on one reused branch stay two gates.
#   review_log.sh summary [--since YYYY-MM-DD] [--repo NAME]
#       Per depth and seat: runs, OK runs, mean and max seconds, mean tokens where known;
#       then rounds per gate by depth (lines logged before gate ids existed: per repo, branch
#       and gate type).
#   review_log.sh gate [--id ID]
#       One line on the current gate (the id new-gate wrote in this worktree), or on gate ID:
#       the rounds seen, the seat runs, the tokens summed where a run gave a figure, and how many
#       runs gave none. independent_review.sh prints it after each run, so the running cost is
#       in front of whoever decides on the next round. Nothing, and exit 0, with no gate or no log.
#   review_log.sh earned-by --round N [--id ID]
#       The --earned-by kind recorded for round N of the current gate (or of gate ID), or "-"
#       when that round's lines carry none. When it cannot tell (log off or unreadable, no gate,
#       no line for round N), it prints "?", a tab and why. independent_review.sh's cut check
#       reads this.
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

new_gate() {
  local id f
  id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
  f="$(gate_file)"
  [ -z "$f" ] || printf '%s\n' "$id" >"$f" 2>/dev/null || true
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

# gate_args <args>: sets id (--id) and, for earned-by, want (--round). A usage error exits 2, as
# add's does: that is a caller's typo, not a log that failed.
gate_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --id|--round) [ $# -ge 2 ] || { echo "review_log.sh: $1 needs a value" >&2; return 2; } ;;
    esac
    case "$1" in
      --id) id="$2"; shift 2 ;;
      --round) case "$2" in ''|*[!0-9]*) echo "review_log.sh: --round needs a number" >&2; return 2 ;; esac
               want="$2"; shift 2 ;;
      *) echo "review_log.sh: unknown argument: $1" >&2; return 2 ;;
    esac
  done
}

gate() {
  local id="" want="" f
  gate_args "$@" || return 2
  [ -n "$id" ] || id="$(current_gate)"
  f="$(log_path)"
  { [ -n "$id" ] && [ -n "$f" ] && [ -s "$f" ]; } || return 0
  [ -r "$f" ] || { echo "note: could not read the review cost log ($f) — no running total; the review itself is unaffected." >&2; return 0; }
  # Rounds print as ranges ("rounds 1-3, 5"): a round the log missed shows as a gap, not as a
  # round that never ran. A run with no figure is counted apart, so a sum of known tokens is
  # never read as the whole cost.
  awk -F'\t' -v id="$id" '
    function commas(n,   s, out) {
      s = sprintf("%.0f", n); out = ""
      while (length(s) > 3) { out = "," substr(s, length(s) - 2) out; s = substr(s, 1, length(s) - 3) }
      return s out
    }
    $1 == "date" || $14 != id { next }
    {
      n++
      if ($7 ~ /^[0-9]+$/) seen[$7 + 0] = 1
      if ($12 ~ /^[0-9]+$/) t += $12; else none++
    }
    END {
      if (!n) exit
      r = ""; k = 0
      for (i = 1; i <= 100; i++) {
        if (!(i in seen)) continue
        k++
        if (!((i - 1) in seen)) start = i
        if (!((i + 1) in seen)) r = r (r == "" ? "" : ", ") (start == i ? i : start "-" i)
      }
      r = (k == 0 ? "no numbered round" : (k == 1 ? "round " : "rounds ") r)
      printf "gate %s: %s, %d seat run%s, %s tokens", id, r, n, (n == 1 ? "" : "s"), commas(t)
      if (none) printf " (%d run%s gave no figure)", none, (none == 1 ? "" : "s")
      printf "\n"
    }' "$f" || echo "note: could not read the review cost log ($f) — no running total; the review itself is unaffected." >&2
  return 0
}

earned_by() {
  local id="" want="" f out
  gate_args "$@" || return 2
  [ -n "$want" ] || { echo "review_log.sh earned-by: --round is required" >&2; return 2; }
  f="$(log_path)"
  [ -n "$f" ] || { printf '?\t%s\n' "the review cost log is off: REVIEW_LOG=off"; return 0; }
  [ -n "$id" ] || id="$(current_gate)"
  [ -n "$id" ] || { printf '?\t%s\n' "no gate started in this worktree; --round 1 starts one"; return 0; }
  [ -e "$f" ] || { printf '?\t%s\n' "no review cost log yet at $f"; return 0; }
  [ -r "$f" ] || { printf '?\t%s\n' "cannot read the review cost log at $f"; return 0; }
  # The last kind any seat of that round recorded; "-" when its lines carry none (round 3 and
  # earlier need none, and lines older than the column have no field 15).
  out="$(awk -F'\t' -v id="$id" -v want="$want" '
    $1 == "date" || $14 != id || $7 !~ /^[0-9]+$/ || $7 + 0 != want + 0 { next }
    { n++; if ($15 != "" && $15 != "-") kind = $15 }
    END {
      if (!n) printf "?\tthe log holds no round %d of gate %s\n", want, id
      else print (kind == "" ? "-" : kind)
    }' "$f")" || { printf '?\t%s\n' "cannot read the review cost log at $f"; return 0; }
  printf '%s\n' "$out"
}

case "${1:-}" in
  add)     shift; add "$@" ;;
  new-gate) new_gate ;;
  summary) shift; summary "$@" ;;
  gate)    shift; gate "$@" ;;
  earned-by) shift; earned_by "$@" ;;
  *) echo "usage: review_log.sh add --seat <name> [...] | review_log.sh new-gate | review_log.sh summary [--since YYYY-MM-DD] [--repo NAME] | review_log.sh gate [--id ID] | review_log.sh earned-by --round N [--id ID]" >&2; exit 2 ;;
esac
