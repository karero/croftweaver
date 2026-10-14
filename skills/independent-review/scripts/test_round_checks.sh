#!/usr/bin/env bash
#
# test_round_checks.sh — the round checks of independent_review.sh (its header, ROUND CHECKS)
# and the cost-log readers they use (review_log.sh gate and earned-by), in a throwaway git repo
# with a throwaway cost log.
#
# Why it exists: SKILL.md step 6 said in prose that a round past 3 must name the kind of
# finding that earned it, and that a kind earning two rounds running calls for a cut rather
# than a third patch. Those rules were met in 34 of 45 long gates, and the rounds went on
# anyway. The script now refuses such a round before any reviewer starts. These cases pin each
# refusal, the warning that replaces the cut check when the log cannot answer, a log written
# before the two new columns existed, and the gate's running total.
#
# Nothing here reaches a reviewer or the network. Most runs set INDEPENDENT_REVIEW_CHECKS_ONLY=1,
# which ends the script after its checks; and in case that exit ever breaks, codex, ollama, agy
# and curl are stubs first on PATH, HOME is moved (no codex sign-in, so codex is skipped), and
# every reviewer setting from the caller's shell is cleared. The last cases run the whole script
# with a stub codex, to see the two options reach the log and the running total print.
#
# Usage: bash skills/independent-review/scripts/test_round_checks.sh
set -u
if ! command -v git >/dev/null 2>&1; then
  echo "SKIP: test_round_checks.sh needs git"
  exit 0
fi
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
SCRIPT="$HERE/independent_review.sh"
LOG_SH="$HERE/review_log.sh"
T="$(mktemp -d "${TMPDIR:-/tmp}/round-checks-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT

# The caller's reviewer settings must not reach the script under test.
unset MELIOUS_MODEL MELIOUS_API_KEY MELIOUS_BASE_URL SECOND_SEAT OLLAMA_MODEL OLLAMA_HOST \
  OLLAMA_API_KEY CODEX_MODEL CODEX_EFFORT REVIEW_RAW_DIR AGY_MODEL INDEPENDENT_REVIEW_CHECKS_ONLY
export WITH_ANTIGRAVITY=0 OLLAMA_TRANSPORT=cli HOME="$T/home" XDG_STATE_HOME="$T/state"
export GIT_CONFIG_NOSYSTEM=1 STUB_MARKS="$T/marks"
mkdir -p "$T/bin" "$T/home" "$T/marks" || { echo "FAIL — could not set up $T."; exit 1; }
# Every stub notes that it ran. codex answers like a reviewer and reports its tokens on stderr,
# as the real CLI ends a run; it is reached only where HOME holds a codex sign-in (the last cases).
for tool in ollama agy curl; do
  printf '#!/bin/sh\n: >"$STUB_MARKS/%s"\necho "stub %s: refusing to run in a test" >&2\nexit 1\n' "$tool" "$tool" >"$T/bin/$tool"
done
cat >"$T/bin/codex" <<'EOF'
#!/bin/sh
: >"$STUB_MARKS/codex"
printf '%s\n' '- BUG: stub finding one' '- NIT: stub finding two'
printf '%s\n' 'tokens used' '1,234' >&2
EOF
chmod +x "$T/bin/"* || { echo "FAIL — could not make the stubs runnable."; exit 1; }
export PATH="$T/bin:$PATH"
printf '# Plan\n\nStep 1: do the thing.\n' >"$T/plan.md"

new_repo() {   # new_repo <dir>: an empty git repo (the gate file lives in its git dir)
  git init -q "$1" || { echo "FAIL — git init $1 failed."; exit 1; }
}
gate_file_of() {   # gate_file_of <repo>: where new-gate keeps the current gate's id
  printf '%s/%s' "$1" "$(cd "$1" && git rev-parse --git-path independent-review-gate)"
}
new_repo "$T/repo"
GATE_FILE="$(gate_file_of "$T/repo")"
LOG="$T/runs.tsv"
export REVIEW_LOG="$LOG"
NEW_HEADER=$'date\trepo\tbranch\thead\tgate\tdepth\tround\tseat\tmodel\teffort\tseconds\ttokens\toutcome\tgate_id\tearned_by\tcut'
OLD_HEADER=$'date\trepo\tbranch\thead\tgate\tdepth\tround\tseat\tmodel\teffort\tseconds\ttokens\toutcome\tgate_id'
line() {   # line <gate id> <round> <seat> <tokens> <earned_by> [cut]: one log line, 16 fields
  printf '2026-10-14T10:00:00Z\trepo\tbranch\tabc1234\tdiff\tnormal\t%s\t%s\tmodel\t-\t60\t%s\tOK\t%s\t%s\t%s\n' \
    "$2" "$3" "$4" "$1" "$5" "${6:--}"
}
old_line() {   # old_line <gate id> <round> <seat> <tokens>: a line from before earned_by and cut, 14 fields
  printf '2026-10-01T10:00:00Z\trepo\tbranch\tabc1234\tdiff\tnormal\t%s\t%s\tmodel\t-\t60\t%s\tOK\t%s\n' \
    "$2" "$3" "$4" "$1"
}

fails=0 ; n=0
ok()   { echo "ok   $1"; n=$((n+1)); }
fail() { echo "FAIL $1"; fails=$((fails+1)); n=$((n+1)); }
# run [args…]: the script with the checks only, from the repo, on the plan. Sets rc and out
# (stdout and stderr together: every refusal and warning goes to stderr).
run() {
  rm -f "$T/marks/"*
  out="$(cd "$T/repo" && INDEPENDENT_REVIEW_CHECKS_ONLY=1 bash "$SCRIPT" "$T/plan.md" "$@" 2>&1)"; rc=$?
}
# check <label> <want rc> [must contain] [must not contain]. Each run with the checks only must
# also leave every stub untouched: nothing ran, so nothing could leave the machine.
check() {
  local label="$1" want="$2" has="${3:-}" lacks="${4:-}" ran
  ran="$(ls -A "$T/marks")"
  if [ "$rc" != "$want" ]; then fail "$label: exit $rc, expected $want. Output: $out"
  elif [ -n "$has" ] && [[ "$out" != *"$has"* ]]; then fail "$label: output lacks \"$has\". Output: $out"
  elif [ -n "$lacks" ] && [[ "$out" == *"$lacks"* ]]; then fail "$label: output has \"$lacks\". Output: $out"
  elif [ -n "$ran" ]; then fail "$label: a stub ran ($ran): the checks-only run went past its checks"
  else ok "$label"; fi
}
WARN="warning: the cut check could not run"

# --- the cost log the cut-check cases read: gate G1 is current. Its round 4 was earned by
# config-advice; round 3 named no kind. G2, another gate, recorded test-gap at round 4.
{ printf '%s\n' "$NEW_HEADER"
  line G1 1 codex 100000 -; line G1 1 fresh-eyes - -
  line G1 2 codex 200000 -; line G1 2 ollama-cloud 300000 -
  line G1 3 codex 400000 -; line G1 3 ollama-cloud n/a -
  line G1 4 codex 1431880 config-advice; line G1 4 fresh-eyes - config-advice
  line G2 4 codex 500 test-gap
} >"$LOG"
printf 'G1\n' >"$GATE_FILE"

# 1. No --round: the wording pass and the final full read need neither option, and no kind the
#    log holds can refuse them.
run;                                    check "no --round, no options: runs" 0 "" "$WARN"
run --earned-by config-advice;          check "no --round, --earned-by the last round's kind: no cut check" 0 "" "Two rounds running"

# 2. Rounds up to 3 need no kind.
run --round 3;                          check "round 3 without --earned-by: runs" 0 "" "past round 3"

# 3. Round 4 and later must name the kind that earned them.
R4="Round 4 is past round 3: name the kind of finding that earned it (SKILL.md step 6), as --earned-by <kind>, for example --earned-by config-advice."
run --round 4;                          check "round 4 without --earned-by: refused, exit 2" 2 "$R4"
run --round 12 --cut "dropped it";      check "round 12 without --earned-by, --cut alone: refused" 2 "Round 12 is past round 3"

# 4. A kind is 1 to 40 letters, digits, '.', '_' or '-', and does not start with '-' (the next flag).
for bad in "config advice" "a/b" "" "kind;rm" "--cut" "$(printf 'x%.0s' $(seq 41))" "größe"; do
  run --round 4 --earned-by "$bad";     check "--earned-by \"$bad\": a usage error, exit 2" 2 "bad value for --earned-by"
done
run --round 4 --earned-by;              check "--earned-by with no value: a usage error" 2 "--earned-by needs a kind"
run --round 4 --earned-by "$(printf 'k%.0s' $(seq 40))" --cut x
                                        check "--earned-by of 40 characters: accepted" 0

# 5. --cut is one non-empty line of at most 300 characters.
run --round 5 --earned-by config-advice --cut "";             check "--cut empty: a usage error" 2 "bad value for --cut"
run --round 5 --earned-by config-advice --cut $'one\ntwo';    check "--cut of two lines: a usage error" 2 "bad value for --cut"
run --round 5 --earned-by config-advice --cut "$(printf 'c%.0s' $(seq 301))"
                                        check "--cut of 301 characters: a usage error" 2 "more than 300"
run --round 5 --earned-by config-advice --cut "$(printf 'c%.0s' $(seq 300))"
                                        check "--cut of 300 characters: accepted" 0 "" "$WARN"

# 6. The cut check: round N-1 of this gate earned by the same kind needs --cut.
CUTMSG='Kind config-advice earned round 4 too. Two rounds running: the fix since then must be a cut, not a third patch (SKILL.md step 6). Say what was removed or refused: --cut "<what>".'
run --round 5 --earned-by config-advice;                        check "round 5, same kind as round 4, no --cut: refused, exit 2" 2 "$CUTMSG"
run --round 5 --earned-by config-advice --cut "dropped the fallback parser"
                                                                check "round 5, same kind, with --cut: runs" 0 "" "$WARN"
run --round 5 --earned-by test-gap;                             check "round 5, another kind: runs, no warning" 0 "" "$WARN"
run --round 4 --earned-by config-advice;                        check "round 4 after a round 3 with no kind: runs, no warning" 0 "" "$WARN"
# G2's round 4 was test-gap, but G2 is not the current gate.
run --round 5 --earned-by test-gap;                             check "another gate's round 4 does not count" 0 "" "Two rounds running"

# 7. When the log cannot answer, the cut check says so and the review goes on.
REVIEW_LOG=off run --round 5 --earned-by config-advice
check "REVIEW_LOG=off: warning, exit 0" 0 "$WARN (the review cost log is off"
REVIEW_LOG="$T/no-such.tsv" run --round 5 --earned-by config-advice
check "no log file yet: warning, exit 0" 0 "$WARN (no review cost log yet"
run --round 8 --earned-by config-advice
check "round N-1 not in the log: warning, exit 0" 0 "$WARN (the log holds no round 7 of gate G1"
mv "$GATE_FILE" "$GATE_FILE.away"
run --round 5 --earned-by config-advice
check "no gate started in this worktree: warning, exit 0" 0 "$WARN (no gate started"
mv "$GATE_FILE.away" "$GATE_FILE"
if [ "$(id -u)" != 0 ]; then   # root reads a mode-000 file anyway
  chmod 000 "$LOG"
  run --round 5 --earned-by config-advice
  check "unreadable log: warning, exit 0" 0 "$WARN (cannot read the review cost log"
  g_out="$(cd "$T/repo" && bash "$LOG_SH" gate 2>"$T/gate.err")"; g_rc=$?
  if [ $g_rc -eq 0 ] && [ -z "$g_out" ] && grep -q "could not read the review cost log" "$T/gate.err"; then
    ok "review_log.sh gate on an unreadable log: warns, prints nothing, exit 0"
  else fail "review_log.sh gate on an unreadable log: exit $g_rc, stdout [$g_out], stderr [$(cat "$T/gate.err")]"; fi
  chmod 644 "$LOG"
else
  echo "skip unreadable-log cases: running as root"
fi

# 8. review_log.sh earned-by, read directly.
ek() { (cd "$T/repo" && bash "$LOG_SH" earned-by "$@"); }
[ "$(ek --round 4)" = config-advice ] && ok "earned-by: round 4 of G1 is config-advice" || fail "earned-by round 4: [$(ek --round 4)]"
[ "$(ek --round 3)" = - ] && ok "earned-by: round 3 of G1 named none, '-'" || fail "earned-by round 3: [$(ek --round 3)]"
[ "$(ek --round 4 --id G2)" = test-gap ] && ok "earned-by --id G2: test-gap" || fail "earned-by --id G2: [$(ek --round 4 --id G2)]"
case "$(ek --round 9)" in '?'*) ok "earned-by: a round not in the log answers '?'" ;; *) fail "earned-by round 9: [$(ek --round 9)]" ;; esac

# 9. review_log.sh gate: the sums, from lines set by hand. G1 has 8 seat runs over rounds 1-4;
#    100000+200000+300000+400000+1431880 = 2431880 tokens; three runs gave none ("-", "n/a", "-").
gt() { (cd "$T/repo" && bash "$LOG_SH" gate "$@" 2>&1); }
want="gate G1: rounds 1-4, 8 seat runs, 2,431,880 tokens (3 runs gave no figure)"
[ "$(gt)" = "$want" ] && ok "gate: the current gate's sums" || fail "gate: got [$(gt)], want [$want]"
want="gate G2: round 4, 1 seat run, 500 tokens"
[ "$(gt --id G2)" = "$want" ] && ok "gate --id G2: one round, one run, every run gave a figure" || fail "gate --id G2: got [$(gt --id G2)], want [$want]"
{ line G4 1 codex 10 -; line G4 2 codex 20 -; line G4 4 codex - k; line G5 - codex 7 -; } >>"$LOG"
want="gate G4: rounds 1-2, 4, 3 seat runs, 30 tokens (1 run gave no figure)"
[ "$(gt --id G4)" = "$want" ] && ok "gate: a round missing from the log shows as a gap" || fail "gate --id G4: got [$(gt --id G4)], want [$want]"
want="gate G5: no numbered round, 1 seat run, 7 tokens"
[ "$(gt --id G5)" = "$want" ] && ok "gate: lines with no round (a wording pass)" || fail "gate --id G5: got [$(gt --id G5)], want [$want]"
[ -z "$(gt --id nope)" ] && ok "gate: an id with no lines prints nothing" || fail "gate --id nope: [$(gt --id nope)]"
[ -z "$(REVIEW_LOG=off gt)" ] && ok "gate: REVIEW_LOG=off prints nothing" || fail "gate with REVIEW_LOG=off: [$(REVIEW_LOG=off gt)]"
[ -z "$(REVIEW_LOG="$T/no-such.tsv" gt)" ] && ok "gate: no log prints nothing" || fail "gate with no log: [$(REVIEW_LOG="$T/no-such.tsv" gt)]"
new_repo "$T/nogate"
g_out="$(cd "$T/nogate" && bash "$LOG_SH" gate 2>&1)"; g_rc=$?
[ $g_rc -eq 0 ] && [ -z "$g_out" ] && ok "gate: no gate in this worktree prints nothing, exit 0" || fail "gate with no gate: exit $g_rc, [$g_out]"

# 10. A log written before earned_by and cut: its 14-column header and 14-field lines.
OLDLOG="$T/old.tsv"
{ printf '%s\n' "$OLD_HEADER"
  old_line G3 1 codex 1000; old_line G3 2 codex 2000; old_line G3 3 codex -; old_line G3 4 codex 4000
} >"$OLDLOG"
printf 'G3\n' >"$GATE_FILE"
REVIEW_LOG="$OLDLOG" run --round 5 --earned-by config-advice
check "old log: round 5 after an old round 4 runs, no warning" 0 "" "$WARN"
got="$(REVIEW_LOG="$OLDLOG" ek --round 4)"
[ "$got" = - ] && ok "old log: earned-by reads an old line's missing field as '-'" || fail "old log earned-by round 4: [$got], want [-]"
(cd "$T/repo" && REVIEW_LOG="$OLDLOG" bash "$LOG_SH" add --seat codex --round 5 --tokens 5000 --earned-by config-advice --cut "dropped x")
if [ "$(sed -n 1p "$OLDLOG")" = "$OLD_HEADER" ] && [ "$(grep -c '^date' "$OLDLOG")" = 1 ] && [ "$(grep -c . "$OLDLOG")" = 6 ] \
   && [ "$(tail -n 1 "$OLDLOG" | awk -F'\t' '{print NF ":" $14 ":" $15 ":" $16}')" = "16:G3:config-advice:dropped x" ]; then
  ok "old log: add appends a 16-field line and keeps the old header, not rewriting the file"
else fail "old log after add: $(cat "$OLDLOG")"; fi
REVIEW_LOG="$OLDLOG" run --round 6 --earned-by config-advice
check "old log: round 6, same kind as the new round 5 line: refused" 2 "Kind config-advice earned round 5 too"
want="gate G3: rounds 1-5, 5 seat runs, 12,000 tokens (1 run gave no figure)"
got="$(REVIEW_LOG="$OLDLOG" gt)"
[ "$got" = "$want" ] && ok "old log: gate sums old and new lines" || fail "old log gate: got [$got], want [$want]"
printf 'G1\n' >"$GATE_FILE"

# 11. The whole script with a stub codex: the options reach every log line it writes, and the
#     closing lines carry the gate's running total. A fresh repo, log and sign-in.
mkdir -p "$T/home2/.codex" && : >"$T/home2/.codex/auth.json" && printf 'model = "stub-codex"\n' >"$T/home2/.codex/config.toml" \
  || { echo "FAIL — could not set up the codex sign-in."; exit 1; }
new_repo "$T/e2e"
E2E_LOG="$T/e2e.tsv"
full() {   # full [args…]: a whole run, codex alone. Sets rc and out (stdout and stderr).
  rm -f "$T/marks/"*
  out="$(cd "$T/e2e" && HOME="$T/home2" REVIEW_LOG="$E2E_LOG" REVIEW_RAW_DIR="$T/raw" \
    bash "$SCRIPT" "$T/plan.md" --seat codex --depth normal "$@" 2>&1)"; rc=$?
}
fields() { tail -n 1 "$E2E_LOG" | awk -F'\t' '{print $7 ":" $8 ":" $15 ":" $16}'; }
full --round 1
id="$(cat "$(gate_file_of "$T/e2e")" 2>/dev/null)"
if [ $rc -eq 0 ] && [ -e "$T/marks/codex" ] && [ -n "$id" ] && [[ "$out" == *"gate $id: round 1, 1 seat run, 1,234 tokens"* ]]; then
  ok "full run, round 1: the running total prints after the reviewers"
else fail "full run, round 1: exit $rc, gate [$id]. Output: $out"; fi
[ "$(fields)" = "1:codex:-:-" ] && ok "full run, round 1: no kind, no cut in the log" || fail "full run round 1 log fields: [$(fields)]"
full --round 4 --earned-by config-advice
[ $rc -eq 0 ] && [ "$(fields)" = "4:codex:config-advice:-" ] && ok "full run, round 4: --earned-by reaches the log" \
  || fail "full run round 4: exit $rc, log fields [$(fields)]. Output: $out"
full --round 5 --earned-by config-advice
[ $rc -eq 2 ] && [ ! -e "$T/marks/codex" ] && [[ "$out" == *"Kind config-advice earned round 4 too"* ]] \
  && ok "full run, round 5, same kind, no --cut: refused before codex ran" \
  || fail "full run round 5 refusal: exit $rc. Output: $out"
full --round 5 --earned-by config-advice --cut "dropped the fallback parser"
if [ $rc -eq 0 ] && [ "$(fields)" = "5:codex:config-advice:dropped the fallback parser" ] \
   && [[ "$out" == *"gate $id: rounds 1, 4-5, 3 seat runs, 3,702 tokens"* ]]; then
  ok "full run, round 5 with --cut: the cut reaches the log, the total counts three runs"
else fail "full run round 5 with --cut: exit $rc, log fields [$(fields)]. Output: $out"; fi
out_off="$(cd "$T/e2e" && HOME="$T/home2" REVIEW_LOG=off REVIEW_RAW_DIR="$T/raw" bash "$SCRIPT" "$T/plan.md" --seat codex --depth normal 2>&1)"; rc=$?
[ $rc -eq 0 ] && [[ "$out_off" != *"gate "*": "*"seat run"* ]] && ok "full run with REVIEW_LOG=off: no running total" \
  || fail "full run with REVIEW_LOG=off: exit $rc. Output: $out_off"

echo
if [ $fails -ne 0 ]; then echo "$fails of $n check(s) FAILED"; exit 1; fi
echo "all $n checks passed"
