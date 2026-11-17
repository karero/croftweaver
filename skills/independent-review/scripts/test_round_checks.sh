#!/usr/bin/env bash
#
# test_round_checks.sh — the round checks of independent_review.sh (its header, ROUND CHECKS)
# and the cost-log readers they use (review_log.sh gate, round-check and new-gate), in a
# throwaway git repo with a throwaway cost log.
#
# Why it exists: SKILL.md step 6 said in prose that a round past 3 must name the kind of
# finding that earned it, and that a kind that comes back calls for a cut rather than another
# patch. Those rules were met in 34 of 45 long gates, and the rounds went on anyway. The script
# now refuses such a round before any reviewer starts. A host can still slip past a check (name
# another kind, leave --round off, restart at round 1), so what the checks cannot stop they
# print, in the lines the owner reads. These cases pin each refusal, each of those lines, the
# warning that replaces the cut check when the log cannot answer, a log written before the two
# new columns existed, and the gate's running total.
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
# With STUB_FRESH set, it also logs a host fresh-eyes line from that repo, as a host would mid-run.
[ -z "${STUB_FRESH:-}" ] || (cd "$STUB_FRESH" && bash "$STUB_LOG_SH" add --seat fresh-eyes --gate plan --depth normal --round 1 >/dev/null 2>&1)
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
NEW_HEADER=$'date\trepo\tbranch\thead\tgate\tdepth\tround\tseat\tmodel\teffort\tseconds\ttokens\toutcome\tgate_id\tearned_by\tcut\treason\tmanager_said'
HEADER17=$'date\trepo\tbranch\thead\tgate\tdepth\tround\tseat\tmodel\teffort\tseconds\ttokens\toutcome\tgate_id\tearned_by\tcut\treason'
OLD_HEADER=$'date\trepo\tbranch\thead\tgate\tdepth\tround\tseat\tmodel\teffort\tseconds\ttokens\toutcome\tgate_id'
line() {   # line <gate id> <round> <seat> <tokens> <earned_by> [cut]: one log line, 16 fields (no manager_said)
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
# (stdout and stderr together: every refusal and warning goes to stderr). A run that passes its
# checks ends with CHECKS_RC, the checks-only code, never 0.
CHECKS_RC=5
SCRIPT_RUN="$SCRIPT"
run() {
  rm -f "$T/marks/"*
  out="$(cd "$T/repo" && INDEPENDENT_REVIEW_CHECKS_ONLY=1 bash "$SCRIPT_RUN" "$T/plan.md" "$@" 2>&1)"; rc=$?
}
use_gate() { printf '%s\n' "$1" >"$GATE_FILE"; }   # make <id> the repo's current gate
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
USAGE_START="usage: independent_review.sh"
P=$CHECKS_RC

# --- the cost log most cases read. G1: rounds 1-4, round 4 earned by config-advice, round 3
# named no kind. G2, another gate, recorded test-gap at round 4. G4 skips round 3; G5 has only a
# run with no round. Gempty has no line at all.
{ printf '%s\n' "$NEW_HEADER"
  line G1 1 codex 100000 -; line G1 1 fresh-eyes - -
  line G1 2 codex 200000 -; line G1 2 ollama-cloud 300000 -
  line G1 3 codex 400000 -; line G1 3 ollama-cloud n/a -
  line G1 4 codex 1431880 config-advice; line G1 4 fresh-eyes - config-advice
  line G2 4 codex 500 test-gap
  line G4 1 codex 10 -; line G4 2 codex 20 -; line G4 4 codex - k
  line G5 - codex 7 -
} >"$LOG"
use_gate G1

# 1. Checks only: the run says nothing was reviewed, on stdout and on stderr, and exits 5.
c_out="$(cd "$T/repo" && INDEPENDENT_REVIEW_CHECKS_ONLY=1 bash "$SCRIPT" "$T/plan.md" 2>"$T/c.err")"; c_rc=$?
if [ $c_rc -eq 5 ] && [[ "$c_out" == *"checks only: nothing was reviewed"* ]] && grep -q "checks only: nothing was reviewed" "$T/c.err"; then
  ok "checks only: exit 5, and 'nothing was reviewed' on stdout and stderr"
else fail "checks only: exit $c_rc, stdout [$c_out], stderr [$(cat "$T/c.err")]"; fi

# 2. No --round: the wording pass and the final full read need neither option. On a gate past
#    round 3 they get one notice, since a real round run this way would skip the checks.
NOROUND="note: no --round, so this run is not a round of gate G1, which is at round 4: the round checks did not run, and the gate line counts it as a run with no round. Right for the final full read; a wording pass passes --wording-pass; a review round is --round 5."
run;                                    check "no --round on a gate past round 3: runs, with the notice" $P "$NOROUND" "$WARN"
# A wording pass says what it was in one line, instead of the notice a forgotten --round needs.
WPNOTE="note: wording pass, not a round of gate G1, which is at round 4."
run --wording-pass;                     check "--wording-pass on a gate past round 3: the one-line note, not the notice" $P "$WPNOTE" "note: no --round"
[ "$(printf '%s\n' "$out" | grep -cxF -- "$WPNOTE")" = 1 ] && ok "--wording-pass: the note is that line exactly, once" \
  || fail "--wording-pass note not found as one exact line. Output: $out"
run --earned-by config-advice;          check "no --round, --earned-by an earlier kind: no cut check" $P "" "Kind config-advice"
use_gate G4
run;                                    check "no --round, gate G4 at round 4: the notice names it" $P "which is at round 4"
use_gate Gempty
run;                                    check "no --round on a gate with no rounds: no notice" $P "" "note: no --round"
use_gate G1

# 3. Rounds up to 3 need no kind; round 4 and later must name one.
use_gate Gempty
run --round 3;                          check "round 3 without --earned-by: runs" $P "" "past round 3"
use_gate G1
R4="Round 4 is past round 3: name the kind of finding that earned it (SKILL.md step 6), as --earned-by <kind>, for example --earned-by config-advice."
run --round 4;                          check "round 4 without --earned-by: refused, exit 2" 2 "$R4"
run --round 12 --cut "dropped it";      check "round 12 without --earned-by, --cut alone: refused" 2 "Round 12 is past round 3"

# 4. Kinds: up to 8, comma-separated, each 1 to 40 letters, digits, '.', '_' or '-', with a
#    letter or digit, not starting with '-' (the next flag).
use_gate Gempty
for bad in "config advice" "a/b" "" "kind;rm" "--cut" "$(printf 'x%.0s' $(seq 41))" "größe" \
           ",a" "a," "a,,b" "a,-b" "._" "a,b,c,d,e,f,g,h,i" "a,$(printf 'y%.0s' $(seq 41))"; do
  run --round 4 --earned-by "$bad";     check "--earned-by \"$bad\": a usage error, exit 2" 2 "bad value for --earned-by"
  case "$out" in *"$USAGE_START"*) ;; *) fail "--earned-by \"$bad\": no usage line" ;; esac
done
run --round 4 --earned-by;              check "--earned-by with no value: a usage error" 2 "--earned-by needs a kind"
run --round 4 --earned-by "$(printf 'k%.0s' $(seq 40))"
                                        check "--earned-by of 40 characters: accepted" $P
run --round 4 --earned-by a,b,c,d,e,f,g,h
                                        check "--earned-by of 8 kinds: accepted" $P

# 5. --cut is one line of 1 to 300 characters, not only blanks, no tab, not starting with '-'.
#    `--cut --local-only` once took the flag as the text and dropped local-only mode (round 1).
for bad in "" "   " $'a\tb' $'one\ntwo' $'one\rtwo' "--local-only" "-x" "$(printf 'c%.0s' $(seq 301))"; do
  run --round 5 --earned-by config-advice --cut "$bad"
  check "--cut \"$(printf '%s' "$bad" | tr '\t\n\r' 'TNR' | cut -c1-20)\": a usage error, exit 2" 2 "bad value for --cut"
  case "$out" in *"$USAGE_START"*) ;; *) fail "--cut bad value: no usage line" ;; esac
done
run --round 5 --earned-by config-advice --cut --local-only
check "--cut --local-only: refused as a flag, not taken as the text" 2 "starts with '-'"
run --round 5 --earned-by config-advice --cut "$(printf 'c%.0s' $(seq 300))"
                                        check "--cut of 300 characters: accepted" $P

# 6. The cut check on G1: config-advice earned round 4.
use_gate G1
CUTMSG='Kind config-advice earned round 4 of this gate too, with no cut since. A kind that comes back needs a cut, not another patch (SKILL.md step 6). Say what was removed or refused: --cut "<what>".'
run --round 5 --earned-by config-advice;                        check "round 5, same kind as round 4, no --cut: refused, exit 2" 2 "$CUTMSG"
run --round 5 --earned-by config-advice --cut "dropped the fallback parser"
                                                                check "round 5, same kind, with --cut: runs" $P "" "$WARN"
run --round 5 --earned-by test-gap;                             check "round 5, another kind (G2's kind): runs, no warning" $P "" "$WARN"
run --round 5 --earned-by test-gap,config-advice;               check "a list: the kind that came back is refused" 2 "$CUTMSG"
run --round 5 --earned-by Config_Advice
check "a respelling (Config_Advice) is the same kind" 2 "Kind Config_Advice (logged as config-advice) earned round 4 of this gate too"
run --round 5 --earned-by config.advice.yaml
check "a finer name: not refused, both named" $P "note: kind config.advice.yaml looks like config-advice, which earned round 4 of this gate: if they are one kind, a cut is owed" "Kind config"
run --round 5 --earned-by config
check "a shorter name: not refused, both named" $P "note: kind config looks like config-advice"
run --round 7 --earned-by config-advice
check "a skipped round number resets nothing: round 7 still sees round 4" 2 "Kind config-advice earned round 4"

# 7. Round numbers below or equal to the highest logged.
run --round 2
check "round 2 on a gate at round 4: a warning naming both" $P "warning: round 2 is below round 4, the highest round gate G1 has logged. A new round is 5; going on."
run --round 4 --earned-by config-advice
check "round 4 again: 're-run of round 4'" $P "note: re-run of round 4: gate G1 already logged 2 seat run(s) for it. A new round is 5."
run --round 5 --earned-by test-gap
check "round 5 on a gate at round 4: no round-number line" $P "" "round 4,"

# 8. Kinds that alternate, a cut that settles a kind, and a round's kinds as a union. Gate G8:
#    4 config-advice; 5 test-gap, and a seat re-run of round 5 naming zip-names.
{ line G8 3 codex 1 -; line G8 4 codex 1 config-advice; line G8 5 codex 1 test-gap; line G8 5 ollama-cloud 1 zip-names; } >>"$LOG"
use_gate G8
run --round 6 --earned-by config-advice;    check "A, B, A: the third round is refused" 2 "Kind config-advice earned round 4 of this gate too"
run --round 6 --earned-by test-gap;         check "a round right after its kind: refused" 2 "Kind test-gap earned round 5"
run --round 6 --earned-by zip-names;        check "a kind named by a seat re-run counts for its round" 2 "Kind zip-names earned round 5"
run --round 6 --earned-by test-gap,zip-names
if [ "$rc" = 2 ] && [[ "$out" == *"Kind test-gap earned"* ]] && [[ "$out" == *"Kind zip-names earned"* ]]; then
  ok "two kinds that came back: one refusal line each"; else fail "two kinds: exit $rc. Output: $out"; fi
line G8 6 codex 1 config-advice "advice removed" >>"$LOG"
run --round 7 --earned-by config-advice;    check "the first round after a cut: runs" $P "" "Kind config-advice"
line G8 7 codex 1 config-advice >>"$LOG"
run --round 8 --earned-by config-advice;    check "the kind back again after the cut: refused, naming only rounds since it" 2 "Kind config-advice earned round 7 of this gate too"
use_gate G1

gt() { (cd "$T/repo" && bash "$LOG_SH" gate "$@" 2>&1); }
# 8b. A cut settles only the kinds on the row that carries it (round 2, Codex). Gate G10: round
#     4, codex alpha and ollama beta; round 5, codex alpha with a cut, ollama beta without one.
{ line G10 4 codex 1 alpha; line G10 4 ollama-cloud 1 beta
  line G10 5 codex 1 alpha "removed alpha"; line G10 5 ollama-cloud 1 beta; } >>"$LOG"
use_gate G10
run --round 6 --earned-by beta;   check "mixed seats: another seat's cut does not settle beta" 2 "Kind beta earned rounds 4, 5 of this gate too"
run --round 6 --earned-by alpha;  check "mixed seats: alpha, cut on its own row, is settled" $P "" "Kind alpha"
got="$(gt --id G10 | grep '^kinds: ')"; want="kinds: 4 alpha,beta; 5 alpha,beta (cut alpha: removed alpha)"
[ "$got" = "$want" ] && ok "gate: a cut that settled one of a round's kinds names that kind" || fail "gate --id G10 kinds: got [$got], want [$want]"
line G10 5 fresh-eyes - beta "removed beta" >>"$LOG"
run --round 6 --earned-by beta;   check "mixed seats: beta's own cut, on a third row, settles it" $P "" "Kind beta"
got="$(gt --id G10 | grep '^kinds: ')"; want="kinds: 4 alpha,beta; 5 alpha,beta (cut alpha: removed alpha; cut beta: removed beta)"
[ "$got" = "$want" ] && ok "gate: every distinct cut of a round, each with its kinds" || fail "gate --id G10 two cuts: got [$got], want [$want]"
use_gate G1

# 9. When the log cannot answer, the cut check says so and the review goes on.
REVIEW_LOG=off run --round 5 --earned-by config-advice
check "REVIEW_LOG=off: warning, checks pass" $P "$WARN (the review cost log is off"
REVIEW_LOG="$T/no-such.tsv" run --round 5 --earned-by config-advice
check "no log file yet: warning" $P "$WARN (no review cost log yet"
use_gate Gempty
run --round 5 --earned-by config-advice
check "no earlier round in the log: warning" $P "$WARN (the log holds no round below 5 of gate Gempty"
use_gate G1
mv "$GATE_FILE" "$GATE_FILE.away"
run --round 5 --earned-by config-advice
check "no gate started in this worktree: warning" $P "$WARN (no gate started"
mv "$GATE_FILE.away" "$GATE_FILE"
if [ "$(id -u)" != 0 ]; then   # root reads a mode-000 file anyway
  chmod 000 "$LOG"
  run --round 5 --earned-by config-advice
  check "unreadable log: warning" $P "$WARN (cannot read the review cost log"
  g_out="$(cd "$T/repo" && bash "$LOG_SH" gate 2>"$T/gate.err")"; g_rc=$?
  if [ $g_rc -eq 0 ] && [ -z "$g_out" ] && grep -q "could not read the review cost log" "$T/gate.err"; then
    ok "review_log.sh gate on an unreadable log: warns, prints nothing, exit 0"
  else fail "review_log.sh gate on an unreadable log: exit $g_rc, stdout [$g_out], stderr [$(cat "$T/gate.err")]"; fi
  chmod 644 "$LOG"
else
  echo "skip unreadable-log cases: running as root"
fi
# review_log.sh beside the script: run through bash, so a copy without its exec bit still answers.
mkdir "$T/copy" && cp "$SCRIPT" "$LOG_SH" "$T/copy/" || { echo "FAIL — could not copy the scripts."; exit 1; }
chmod -x "$T/copy/review_log.sh"
SCRIPT_RUN="$T/copy/independent_review.sh"
run --round 5 --earned-by config-advice;    check "review_log.sh without its exec bit: the cut check still refuses" 2 "$CUTMSG"
rm "$T/copy/review_log.sh"
run --round 5 --earned-by config-advice;    check "review_log.sh missing: warning names it" $P "$WARN (review_log.sh is missing beside this script"
SCRIPT_RUN="$SCRIPT"

# 10. review_log.sh round-check, read directly.
rk() { (cd "$T/repo" && bash "$LOG_SH" round-check "$@"); }
got="$(rk --round 5 --kinds config-advice)"
want="$(printf 'gate\tG1\t4\t2\t4\nfresh\t1,4\nowed\tconfig-advice\t4\tconfig-advice')"
[ "$got" = "$want" ] && ok "round-check: the gate record and the owed kind" || fail "round-check: got [$got], want [$want]"
got="$(rk)"
[ "$got" = "$(printf 'gate\tG1\t4\t2\t0\nfresh\t1,4')" ] && ok "round-check with no --round: the highest round only" || fail "round-check, no --round: [$got]"
case "$(REVIEW_LOG=off rk --round 5)" in '?'*) ok "round-check with the log off answers '?'" ;; *) fail "round-check, log off: [$(REVIEW_LOG=off rk --round 5)]" ;; esac

# 11. review_log.sh gate: the lines, from lines set by hand. G1: 8 runs over rounds 1-4;
#     100000+200000+300000+400000+1431880 = 2431880 tokens; three runs gave none ("-", "n/a", "-").
gt() { (cd "$T/repo" && bash "$LOG_SH" gate "$@" 2>&1); }
NC=". Not counted: the fixes, the host's own work, and fresh-eyes unless the host logged it."
want="gate G1: rounds 1-4, 8 reviewer seat runs, 2,431,880 tokens logged (3 runs gave no figure)$NC
kinds: 4 config-advice"
[ "$(gt)" = "$want" ] && ok "gate: the current gate's sums and kinds" || fail "gate: got [$(gt)], want [$want]"
want="gate G2: round 4, 1 reviewer seat run, 500 tokens logged$NC
kinds: 4 test-gap"
[ "$(gt --id G2)" = "$want" ] && ok "gate --id G2: one round, one run" || fail "gate --id G2: got [$(gt --id G2)], want [$want]"
want="gate G4: rounds 1-2, 4, 3 reviewer seat runs, 30 tokens logged (1 run gave no figure)$NC
kinds: 4 k"
[ "$(gt --id G4)" = "$want" ] && ok "gate: a round missing from the log shows as a gap" || fail "gate --id G4: got [$(gt --id G4)], want [$want]"
want="gate G5: no numbered round, 1 reviewer seat run, 7 tokens logged$NC
1 run with no round"
[ "$(gt --id G5)" = "$want" ] && ok "gate: runs with no round are counted apart" || fail "gate --id G5: got [$(gt --id G5)], want [$want]"
want="kinds: 4 config-advice; 5 test-gap,zip-names; 6 config-advice (cut: advice removed); 7 config-advice [config-advice back after the round 6 cut]"
got="$(gt --id G8 | sed -n 2p)"
[ "$got" = "$want" ] && ok "gate: the kinds and cuts round by round, a round's kinds as a union" || fail "gate --id G8 kinds: got [$got], want [$want]"
g_out="$(cd "$T/repo" && bash "$LOG_SH" gate --round 3 2>&1)"; g_rc=$?
[ $g_rc -eq 2 ] && [[ "$g_out" == *"gate takes only --id"* ]] && ok "gate refuses --round" || fail "gate --round: exit $g_rc, [$g_out]"
[ -z "$(gt --id nope)" ] && ok "gate: an id with no lines prints nothing" || fail "gate --id nope: [$(gt --id nope)]"
[ -z "$(REVIEW_LOG=off gt)" ] && ok "gate: REVIEW_LOG=off prints nothing" || fail "gate with REVIEW_LOG=off: [$(REVIEW_LOG=off gt)]"
[ -z "$(REVIEW_LOG="$T/no-such.tsv" gt)" ] && ok "gate: no log prints nothing" || fail "gate with no log: [$(REVIEW_LOG="$T/no-such.tsv" gt)]"
new_repo "$T/nogate"
g_out="$(cd "$T/nogate" && bash "$LOG_SH" gate 2>&1)"; g_rc=$?
[ $g_rc -eq 0 ] && [ -z "$g_out" ] && ok "gate: no gate in this worktree prints nothing, exit 0" || fail "gate with no gate: exit $g_rc, [$g_out]"

# 12. A restart (--round 1 again) starts a gate that names the one before; the earlier cost
#     stays on the owner's screen. A gate that logged nothing is skipped over.
new_repo "$T/restart"
RLOG="$T/restart.tsv"
rl() { (cd "$T/restart" && REVIEW_LOG="$RLOG" bash "$LOG_SH" "$@"); }
ga="$(rl new-gate)"
rl add --seat codex --round 1 --tokens 1000; rl add --seat codex --round 2 --tokens 2000
gb="$(rl new-gate)"
[ "$(sed -n 2p "$(gate_file_of "$T/restart")")" = "$ga" ] && ok "new-gate: the gate file's second line names the gate before" \
  || fail "new-gate: gate file [$(cat "$(gate_file_of "$T/restart")")], want second line $ga"
gc="$(rl new-gate)"   # gate $gb logged nothing: $gc follows $ga
rl add --seat codex --round 1 --tokens 300
want="gate $gc: round 1, 1 reviewer seat run, 300 tokens logged$NC
follows gate $ga: rounds 1-2, 3,000 tokens"
[ "$(rl gate)" = "$want" ] && ok "gate after restarts: follows the last gate that logged something" || fail "gate after restarts: got [$(rl gate)], want [$want]"
case "$(rl gate --id "$ga")" in *follows*) fail "gate --id of an older gate: printed a follows line" ;; *) ok "gate --id of an older gate: no follows line" ;; esac

# 13. A log written before earned_by and cut: its 14-column header and 14-field lines.
OLDLOG="$T/old.tsv"
{ printf '%s\n' "$OLD_HEADER"
  old_line G3 1 codex 1000; old_line G3 2 codex 2000; old_line G3 3 codex -; old_line G3 4 codex 4000
} >"$OLDLOG"
use_gate G3
REVIEW_LOG="$OLDLOG" run --round 5 --earned-by config-advice
check "old log: round 5 after an old round 4 runs, no warning" $P "" "$WARN"
(cd "$T/repo" && REVIEW_LOG="$OLDLOG" bash "$LOG_SH" add --seat codex --round 5 --tokens 5000 --earned-by config-advice --cut "dropped x")
if [ "$(sed -n 1p "$OLDLOG")" = "$OLD_HEADER" ] && [ "$(grep -c '^date' "$OLDLOG")" = 1 ] && [ "$(grep -c . "$OLDLOG")" = 6 ] \
   && [ "$(tail -n 1 "$OLDLOG" | awk -F'\t' '{print NF ":" $14 ":" $15 ":" $16 ":" $17 ":" $18}')" = "18:G3:config-advice:dropped x:-:-" ]; then
  ok "old log: add appends an 18-field line and keeps the old header, not rewriting the file"
else fail "old log after add: $(cat "$OLDLOG")"; fi
(cd "$T/repo" && REVIEW_LOG="$OLDLOG" bash "$LOG_SH" add --seat codex --round 6 --tokens 6000 --earned-by config-advice)
REVIEW_LOG="$OLDLOG" run --round 7 --earned-by config-advice
check "old log: a kind back after its cut, on new lines below old ones: refused" 2 "Kind config-advice earned round 6"
want="gate G3: rounds 1-6, 6 reviewer seat runs, 18,000 tokens logged (1 run gave no figure)$NC
kinds: 5 config-advice (cut: dropped x); 6 config-advice [config-advice back after the round 5 cut]"
got="$(REVIEW_LOG="$OLDLOG" gt)"
[ "$got" = "$want" ] && ok "old log: gate reads old lines as no kind and no cut" || fail "old log gate: got [$got], want [$want]"
use_gate G1

# 14. The whole script with a stub codex: the options reach every log line it writes, and the
#     closing lines carry the gate's total, its kinds and cuts, its runs with no round, and the
#     gate it follows after a restart. A fresh repo, log and sign-in.
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
id="$(sed -n 1p "$(gate_file_of "$T/e2e")" 2>/dev/null)"
if [ $rc -eq 0 ] && [ -e "$T/marks/codex" ] && [ -n "$id" ] && [[ "$out" == *"gate $id: round 1, 1 reviewer seat run, 1,234 tokens logged$NC"* ]]; then
  ok "full run, round 1: the running total prints after the reviewers"
else fail "full run, round 1: exit $rc, gate [$id]. Output: $out"; fi
[ "$(fields)" = "1:codex:-:-" ] && ok "full run, round 1: no kind, no cut in the log" || fail "full run round 1 log fields: [$(fields)]"
# The host's fresh-eyes seat, logged after round 1 minted the gate: rounds 2 and up refuse a
# Normal gate without it (case 15).
(cd "$T/e2e" && REVIEW_LOG="$E2E_LOG" bash "$LOG_SH" add --seat fresh-eyes --gate plan --depth normal --round 1 --tokens 500 >/dev/null)
full --round 4 --earned-by config-advice,zip-names
[ $rc -eq 0 ] && [ "$(fields)" = "4:codex:config-advice,zip-names:-" ] && ok "full run, round 4: --earned-by reaches the log" \
  || fail "full run round 4: exit $rc, log fields [$(fields)]. Output: $out"
full --round 5 --earned-by zip-names
[ $rc -eq 2 ] && [ ! -e "$T/marks/codex" ] && [[ "$out" == *"Kind zip-names earned round 4"* ]] \
  && ok "full run, round 5, a kind back, no --cut: refused before codex ran" \
  || fail "full run round 5 refusal: exit $rc. Output: $out"
full --round 5 --earned-by zip-names --cut "dropped the zip reader"
if [ $rc -eq 0 ] && [ "$(fields)" = "5:codex:zip-names:dropped the zip reader" ] \
   && [[ "$out" == *"gate $id: rounds 1, 4-5, 4 reviewer seat runs, 4,202 tokens logged$NC"* ]] \
   && [[ "$out" == *"kinds: 4 config-advice,zip-names; 5 zip-names (cut: dropped the zip reader)"* ]]; then
  ok "full run, round 5 with --cut: the cut reaches the log, the closing lines show kinds and cut"
else fail "full run round 5 with --cut: exit $rc, log fields [$(fields)]. Output: $out"; fi
full
if [ $rc -eq 0 ] && [[ "$out" == *"note: no --round, so this run is not a round of gate $id, which is at round 5"* ]] \
   && [[ "$out" == *"; 1 run with no round"* ]]; then
  ok "full run with no --round on a gate past round 3: the notice, and the gate line counts it"
else fail "full run, no --round: exit $rc. Output: $out"; fi
full --round 1
id2="$(sed -n 1p "$(gate_file_of "$T/e2e")" 2>/dev/null)"
if [ $rc -eq 0 ] && [ "$id2" != "$id" ] && [[ "$out" == *"follows gate $id: rounds 1, 4-5, 5,436 tokens"* ]]; then
  ok "full run, a restart at round 1: the new gate names the old one and its cost"
else fail "full run restart: exit $rc, gates [$id] [$id2]. Output: $out"; fi
out_off="$(cd "$T/e2e" && HOME="$T/home2" REVIEW_LOG=off REVIEW_RAW_DIR="$T/raw" bash "$SCRIPT" "$T/plan.md" --seat codex --depth normal 2>&1)"; rc=$?
[ $rc -eq 0 ] && [[ "$out_off" != *"reviewer seat run"* ]] && ok "full run with REVIEW_LOG=off: no running total" \
  || fail "full run with REVIEW_LOG=off: exit $rc. Output: $out_off"

# 15. The manager ask (SKILL.md step 6): a kind at its second return after its first cut starts
#     its round with a warning unless --manager-said answers it, and every round that names a
#     kind cut earlier ends with a reminder. Whole runs with the stub codex, as a host makes them.
#     Gate A: k at round 4, cut at 5, back at 6 (its first return), and round 7 (its second).
ask_run() {   # ask_run <name> [args…]: a whole run in repo ask-<name>. Sets rc and out.
  rm -f "$T/marks/"*
  out="$(cd "$T/ask-$1" && HOME="$T/home2" REVIEW_LOG="$T/ask-$1.tsv" REVIEW_RAW_DIR="$T/raw" \
    bash "$SCRIPT" "$T/plan.md" --seat codex --depth light "${@:2}" 2>&1)"; rc=$?
}
ask_gate() {   # ask_gate <name> <kinds>: rounds 1 and 4, then 5 with a cut
  new_repo "$T/ask-$1"
  ask_run "$1" --round 1
  ask_run "$1" --round 4 --earned-by "$2"
  ask_run "$1" --round 5 --earned-by "$2" --cut "a"
}
col18() { tail -n 1 "$T/ask-$1.tsv" | awk -F'\t' '{print NF ":" $18}'; }
REMIND_K56="Kind k was cut in round 5 and came back in round 6. If this round found it again, ask your manager before the next fix: take it out, make it a warning, or keep fixing?"
ask_gate A k
if [ $rc -eq 0 ] && [[ "$out" != *"Kind k was cut in round"* ]] && [[ "$out" != *"manager not asked"* ]]; then
  ok "ask: the round that makes the cut ends with no reminder"
else fail "ask: round 5 (the cut itself): exit $rc. Output: $out"; fi
ask_run A --round 6 --earned-by k --cut b
if [ $rc -eq 0 ] && [[ "$out" == *"$REMIND_K56"* ]] && [[ "$out" == *"[k back after the round 5 cut]"* ]] \
   && [[ "$out" != *"warning: kind"* ]] && [[ "$out" != *"manager not asked"* ]]; then
  ok "ask: a kind back after its cut (first return): the reminder names rounds 5 and 6, in the gate line too, and no warning at the start"
else fail "ask: round 6 (first return): exit $rc. Output: $out"; fi
ask_run A --round 7 --earned-by K --cut c
if [ $rc -eq 0 ] && [[ "$out" == *"warning: kind K (logged as k) was cut in round 5 and came back in round 6 before this one"* ]] \
   && [[ "$out" == *"[K back after the round 5 cut; K: manager not asked]"* ]] && [ "$(col18 A)" = "18:-" ]; then
  ok "ask: a second return with no --manager-said: the warning (a respelled kind matches), the run goes on, the gate line says 'manager not asked'"
else fail "ask: round 7 without an answer: exit $rc, log [$(col18 A)]. Output: $out"; fi
# the same round with the answer, on a gate of its own
ask_gate B k; ask_run B --round 6 --earned-by k --cut b
ask_run B --round 7 --earned-by K --cut c --manager-said "k: keep fixing"
if [ $rc -eq 0 ] && [[ "$out" != *"warning: kind"* ]] && [[ "$out" != *"manager not asked"* ]] \
   && [[ "$out" == *"manager said: k: keep fixing"* ]] && [ "$(col18 B)" = "18:k: keep fixing" ]; then
  ok "ask: an answer for the kind: no warning, column 18 holds it, the gate line shows it"
else fail "ask: round 7 with the answer: exit $rc, log [$(col18 B)]. Output: $out"; fi
ask_run B --round 8 --earned-by k --cut d
if [ $rc -eq 0 ] && [[ "$out" == *"warning: kind k was cut in round 5 and came back in rounds 6, 7 before this one"* ]]; then
  ok "ask: 'keep fixing' asks again at the next return"
else fail "ask: round 8 after 'keep fixing': exit $rc. Output: $out"; fi
# S7: a round without --cut between. k at 4, cut at 5, round 6 runs with none, round 7 asks.
ask_gate C k; ask_run C --round 6 --earned-by k
if [ $rc -eq 0 ] && [[ "$out" == *"$REMIND_K56"* ]]; then
  ok "ask: the first round after a cut runs without --cut and still reminds"
else fail "ask: round 6 without --cut: exit $rc. Output: $out"; fi
ask_run C --round 7 --earned-by k --cut c
if [ $rc -eq 0 ] && [[ "$out" == *"warning: kind k was cut in round 5 and came back in round 6 before this one"* ]]; then
  ok "ask: a second return asks though only one round carried a cut"
else fail "ask: round 7 after a round without --cut: exit $rc. Output: $out"; fi
# Two kinds due, an answer for one: the warning is for the other only.
ask_gate D k,j; ask_run D --round 6 --earned-by k,j --cut b
ask_run D --round 7 --earned-by k,j --cut c --manager-said "k: make it a warning"
if [ $rc -eq 0 ] && [[ "$out" == *"warning: kind j was cut"* ]] && [[ "$out" != *"warning: kind k"* ]] \
   && [[ "$out" == *"j: manager not asked"* ]] && [[ "$out" != *"k: manager not asked"* ]]; then
  ok "ask: two kinds due, one answered: the warning and the gate line name the other only"
else fail "ask: two kinds, one answer: exit $rc. Output: $out"; fi
ask_run D --round 8 --earned-by k,j --cut d --manager-said "k: keep fixing" --manager-said "J: take it out"
if [ $rc -eq 0 ] && [[ "$out" != *"warning: kind"* ]] && [ "$(col18 D)" = "18:k: keep fixing; J: take it out" ]; then
  ok "ask: one --manager-said per kind: both answered, column 18 joins them with '; '"
else fail "ask: round 8, both answered: exit $rc, log [$(col18 D)]. Output: $out"; fi
# A kind cut once and not named again never warns, and never reminds after its return.
ask_gate E k; ask_run E --round 6 --earned-by j
ask_run E --round 7 --earned-by j --cut c
if [ $rc -eq 0 ] && [[ "$out" != *"warning: kind"* ]] && [[ "$out" != *"Kind k was cut"* ]] && [[ "$out" != *"manager not asked"* ]]; then
  ok "ask: a kind cut once and not named again: nobody is asked"
else fail "ask: a cut that held: exit $rc. Output: $out"; fi
# Bad values are refused before anything runs.
for bad in "" "nocolon" "k:" "k:   " ":x" "--cut" "a b: x" "k: keep fixing; j: " "k: a; j: b" $'k: one\ntwo' "$(printf 'x%.0s' $(seq 301))"; do
  run --round 4 --earned-by k --manager-said "$bad"
  check "--manager-said \"$(printf '%s' "$bad" | tr '\n' 'N' | cut -c1-12)\": a usage error, exit 2" 2 "bad value for --manager-said"
done
run --round 4 --earned-by k --manager-said
check "--manager-said with no value: a usage error" 2 "--manager-said needs"

# 16. A log whose header stops at column 17 (before manager_said): its lines read as no answer.
L17="$T/l17.tsv"
{ printf '%s\n' "$HEADER17"
  line G17 4 codex 1 k; line G17 5 codex 1 k a; line G17 6 codex 1 k b; line G17 7 codex 1 k
} >"$L17"
got="$(REVIEW_LOG="$L17" gt --id G17 | sed -n 2p)"
want="kinds: 4 k; 5 k (cut: a); 6 k (cut: b) [k back after the round 5 cut]; 7 k [k back after the round 5 cut; k: manager not asked]"
[ "$got" = "$want" ] && ok "17-column log: the gate line reads a missing column 18 as no answer" || fail "17-column log gate: got [$got], want [$want]"
got="$(cd "$T/repo" && REVIEW_LOG="$L17" bash "$LOG_SH" round-check --id G17 --round 8 --kinds k)"
want="$(printf 'gate\tG17\t7\t1\t4\nfresh\t-\nowed\tk\t7\tk\nback\tk\t5\tk\nask\tk\t5\t6, 7\tk')"
[ "$got" = "$want" ] && ok "17-column log: round-check names the first cut and the returns" || fail "17-column log round-check: got [$got], want [$want]"
use_gate G17
REVIEW_LOG="$L17" run --round 8 --earned-by k --cut x
check "17-column log: the script warns for the unanswered kind and goes on" $P "warning: kind k was cut in round 5 and came back in rounds 6, 7 before this one"
use_gate G1

# 14. The reason column: log_seat cuts it from the text inside the outcome's parentheses, so every
#     literal outcome="..." assignment but OK must hold " (". A new branch written that way and
#     left without parentheses would log reason "-"; one built another way gets past this check.
outs="$(grep -E '(^|[^A-Za-z_])outcome="' "$SCRIPT")"
n_out="$(printf '%s\n' "$outs" | grep -c .)"
n_bare="$(printf '%s\n' "$outs" | grep -v 'outcome="OK"' | grep -vc 'outcome="[^"]* (')"
if [ "$n_out" -gt 1 ] && [ "$n_bare" -eq 0 ] && [ "$(printf '%s\n' "$outs" | grep -c 'outcome="OK"')" -eq 1 ]; then
  ok "every outcome assignment but OK carries a parenthesised reason ($n_out assignments)"
else fail "outcome assignments without a parenthesised reason: $n_bare of $n_out: $outs"; fi

# 15. The fresh-eyes seat check: round 2 and up of a Normal or High gate refuse until the host's
#     fresh-eyes seat is logged for the rounds that owe it (SKILL.md, Review depth). Each case logs
#     the gate's lines with review_log.sh add, as a host does, on a gate of its own.
FE_REFUSE="needs the host's fresh-eyes seat logged at round(s)"
FE_WARN="warning: the fresh-eyes seat check could not run"
FE_NODEPTH="warning: no --depth, so the fresh-eyes seat check did not run"
fe_add() {   # fe_add <round> <seat> [add options…]: one host line on the current gate, from the repo
  local r="$1" s="$2"; shift 2
  (cd "$T/repo" && bash "$LOG_SH" add --seat "$s" --gate plan --depth normal --round "$r" "$@" >/dev/null 2>&1)
}
use_gate FE1; fe_add 1 codex
run --round 2 --depth normal
check "fresh-eyes: Normal round 2, round 1 has codex only: refused" 2 "Round 2 of a normal gate needs the host's fresh-eyes seat"
check "fresh-eyes: ... naming the seat, round 1 and the gate id" 2 "logged at round(s) 1 (SKILL.md, Review depth), and gate FE1 has no such line"
check "fresh-eyes: ... and the command that settles it" 2 "review_log.sh add --seat fresh-eyes --model <m> --gate <plan|diff> --depth normal --round <r> --gate-id FE1"
for o in OK NOT-COUNTED FAILED; do
  use_gate "FE2-$o"; fe_add 1 codex; fe_add 1 fresh-eyes --outcome "$o" --reason "case 2"
  run --round 2 --depth normal;          check "fresh-eyes: Normal round 2, a $o fresh-eyes line at round 1: runs" $P "" "$FE_REFUSE"
done
use_gate FE3; fe_add 1 codex
(cd "$T" && bash "$LOG_SH" add --seat fresh-eyes --gate plan --depth normal --round 1 --gate-id FE3 >/dev/null 2>&1)
run --round 2 --depth normal;            check "fresh-eyes: a line logged from another directory with --gate-id: runs" $P "" "$FE_REFUSE"
use_gate FE4; fe_add 1 codex; fe_add 1 fresh-eyes-final-read
run --round 2 --depth normal;            check "fresh-eyes: only a fresh-eyes-final-read line: refused" 2 "$FE_REFUSE"
use_gate FE5; fe_add 1 codex; fe_add 1 fresh-eyes; fe_add 2 codex
run --round 3 --depth high;              check "fresh-eyes: High round 3, a line at round 1 only: refused, naming round 2" 2 "logged at round(s) 2 (SKILL.md"
use_gate FE5b; for r in 1 2 3 4; do fe_add "$r" codex; done; for r in 1 2 3; do fe_add "$r" fresh-eyes; done
run --round 5 --depth high --earned-by test-gap
check "fresh-eyes: High round 5, lines at rounds 1 to 3: runs (round 4 owes none)" $P "" "$FE_REFUSE"
use_gate FE6; fe_add 1 codex
run --round 2 --depth light;             check "fresh-eyes: Light round 2, no fresh-eyes: runs, no warning" $P "" "fresh-eyes"
run --round 2;                           check "fresh-eyes: no --depth: runs, with the skipped-check warning" $P "$FE_NODEPTH"
out_off="$(cd "$T/repo" && REVIEW_LOG=off INDEPENDENT_REVIEW_CHECKS_ONLY=1 bash "$SCRIPT_RUN" "$T/plan.md" --round 2 --depth normal 2>&1)"; rc=$?
out="$out_off"; check "fresh-eyes: REVIEW_LOG=off: runs, with the warning" $P "$FE_WARN"
cp "$LOG" "$T/ro.tsv"; chmod a-w "$T/ro.tsv"
out="$(cd "$T/repo" && REVIEW_LOG="$T/ro.tsv" INDEPENDENT_REVIEW_CHECKS_ONLY=1 bash "$SCRIPT_RUN" "$T/plan.md" --round 2 --depth normal 2>&1)"; rc=$?
check "fresh-eyes: a read-only log: runs, with the warning" $P "$FE_WARN (the review cost log cannot be written"
use_gate FE8a; fe_add 1 fresh-eyes
use_gate FE8; fe_add 1 codex
run --round 2 --depth normal;            check "fresh-eyes: a fresh-eyes line of another gate does not count: refused" 2 "gate FE8 has no such line"
# A line logged before a --round 1 re-run: new-gate (what --round 1 calls) mints the gate it
# goes to, so the seat stays with the gate the re-run replaced.
use_gate FE8b; fe_add 1 codex; fe_add 1 fresh-eyes
fe_new="$(cd "$T/repo" && bash "$LOG_SH" new-gate)"; fe_add 1 codex
run --round 2 --depth normal;            check "fresh-eyes: a line logged before a --round 1 re-run: refused" 2 "gate $fe_new has no such line"
# 9 of the plan: round-check alone.
use_gate FE9; fe_add 1 fresh-eyes; fe_add 2 codex; fe_add 3 fresh-eyes
[ "$(rk --round 4 | grep '^fresh')" = "$(printf 'fresh\t1,3')" ] && ok "round-check: fresh lists 1,3" \
  || fail "round-check fresh 1,3: [$(rk --round 4)]"
use_gate FE1
[ "$(rk --round 2 | grep '^fresh')" = "$(printf 'fresh\t-')" ] && ok "round-check: fresh is - with no line" \
  || fail "round-check fresh -: [$(rk --round 2)]"
got="$(cd "$T/repo" && REVIEW_LOG="$T/ro.tsv" bash "$LOG_SH" round-check --round 2 | grep '^fresh')"
[ "$got" = "$(printf 'fresh\t?')" ] && ok "round-check: fresh is ? on a read-only log" || fail "round-check fresh ?: [$got]"
# 10 of the plan: round 1 of the whole script prints the note when no seat is logged, and not
# when the stub codex logs one during the run (after new-gate).
new_repo "$T/e2e3"
FE_NOTE="fresh-eyes: gate "
fe_full() {
  rm -f "$T/marks/"*
  out="$(cd "$T/e2e3" && HOME="$T/home2" REVIEW_LOG="$T/e2e3.tsv" REVIEW_RAW_DIR="$T/raw" \
    bash "$SCRIPT" "$T/plan.md" --seat codex --depth normal --round 1 2>&1)"; rc=$?
}
fe_full
fe_id="$(sed -n 1p "$(gate_file_of "$T/e2e3")" 2>/dev/null)"
if [ $rc -eq 0 ] && [[ "$out" == *"fresh-eyes: gate $fe_id has no fresh-eyes line at round 1 yet"* ]] \
   && [[ "$out" == *"--round 1 --gate-id $fe_id"* ]]; then
  ok "full run, Normal round 1, no fresh-eyes line: the note names the gate"
else fail "full run round 1 fresh-eyes note: exit $rc, gate [$fe_id]. Output: $out"; fi
export STUB_FRESH="$T/e2e3" STUB_LOG_SH="$LOG_SH"
fe_full
unset STUB_FRESH STUB_LOG_SH
if [ $rc -eq 0 ] && [[ "$out" != *"$FE_NOTE"* ]] && [ "$(awk -F'\t' '$8 == "fresh-eyes"' "$T/e2e3.tsv" | wc -l | tr -d ' ')" = 1 ]; then
  ok "full run, Normal round 1, the seat logged during the run: no note"
else fail "full run round 1, seat logged during the run: exit $rc. Output: $out"; fi

echo
if [ $fails -ne 0 ]; then echo "$fails of $n check(s) FAILED"; exit 1; fi
echo "all $n checks passed"
