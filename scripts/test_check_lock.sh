#!/usr/bin/env bash
#
# test_check_lock.sh — checks that `make check` refuses to start while another `make check` of
# the same user holds the lock (scripts/check_lock.sh), and that a killed run is never a pass.
#
# Why it exists: runs outside the slots the release manager hands out kept overlapping, and
# seven at once pushed this Mac's load past what the browser tests survive. The lock is only
# worth having if the real `make check` goes through it, so every case enters the way production
# does: it runs `make check` (or `make package`) in a copy of the real Makefile and check_lock.sh.
# The exceptions are the unit-level cases: T6's exit status, T8's signal forwarding and T9's output
# checks run the script directly. T6 and T8 sit beside a case that goes through make; T9 does not.
# In the copy the first guard, scripts/check_clean.sh, is a stub that writes a marker file and
# fails, so no case runs the real guards or recurses into this test.
#
# N1 to N8 cover the manager's next-in-line entry (scripts/check_next.sh): a live entry refuses every
# session but the named one, expires 10 minutes after the later of its set time and the last run's
# end, and a damaged or held entry refuses loudly. They go through `make check` too; N5's set, show
# and clear and N7's `set`, `clear` and `show` call check_next.sh directly. Not tested: that the
# entry's flock is held from the read to the emptying (the interleaving cannot be forced without a
# pause hook in the lock; the design is one helper doing both under one flock, which review checks),
# and a run from a checkout cut before this entry existed (its old lock ignores the entry).
#
# Every case points CROFTWEAVER_CHECK_LOCK at a throwaway path (T7 does not, on purpose) and runs
# make with MAKEFLAGS and MAKELEVEL removed, so the `make check` running this test does not shape
# it. A holder is `check_lock.sh sleep 300` in its own process group; the EXIT trap kills the whole
# group, sleep included. A case that waits longer than 60 s is killed and fails, which is how
# a lock that waits instead of refusing shows.
#
# Not tested: no Perl on the PATH. Hiding Perl while keeping make and bash is fragile; that branch
# is three lines at the top of check_lock.sh.
#
# Usage: bash scripts/test_check_lock.sh
set -u
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(dirname -- "$HERE")"
T="$(mktemp -d "${TMPDIR:-/tmp}/check-lock-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
T="$(CDPATH= cd -- "$T" && pwd -P)" || { echo "FAIL — could not create a temp dir."; exit 1; }
holders=()
cleanup() {
  local h
  for h in ${holders[@]+"${holders[@]}"}; do kill -KILL -- "-$h" 2>/dev/null; done
  rm -rf "$T"
}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
command -v perl >/dev/null 2>&1 || { echo "FAIL — perl is needed: check_lock.sh takes its lock with it."; exit 1; }
command -v make >/dev/null 2>&1 || { echo "FAIL — make is needed."; exit 1; }

fails=0
ok() { printf 'ok   %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; fails=$((fails+1)); }

# Runs a command in its own process group and ends the group after 60 s (exit 124).
cat >"$T/guard.pl" <<'PL'
setpgrp(0, 0);
my $p = fork;
defined $p or exit 127;
if (!$p) { exec @ARGV; exit 127 }
$SIG{ALRM} = sub { $SIG{TERM} = 'IGNORE'; kill 'TERM', -$$; print "TIMEOUT: still running after 60 s\n"; exit 124 };
alarm 60;
waitpid($p, 0);
exit(($? & 127) ? 128 + ($? & 127) : $? >> 8);
PL

# copy <name> — a folder holding the real Makefile, check_lock.sh, check_next.sh and the stub guard; sets c.
# The stub notes its parent's command name in the marker and, with CHECK_STUB_KILL_PARENT set,
# kills that parent (the inner make) with TERM.
copy() {
  c="$T/$1"
  mkdir -p "$c/scripts" \
    && cp "$ROOT/Makefile" "$c/Makefile" \
    && cp "$HERE/check_lock.sh" "$c/scripts/check_lock.sh" \
    && cp "$HERE/check_next.sh" "$c/scripts/check_next.sh" \
    && cat >"$c/scripts/check_clean.sh" <<'STUB' \
    || { echo "FAIL — could not build the copy $1."; exit 1; }
printf '%s\n' "$(ps -o comm= -p "$PPID" 2>/dev/null)" >"$CHECK_STUB_MARKER"
[ -z "${CHECK_STUB_ENV:-}" ] || printf '%s\n' "${CROFTWEAVER_CHECK_LOCK-unset}" >"$CHECK_STUB_ENV"
[ -z "${CHECK_STUB_KILL_PARENT:-}" ] || kill -TERM "$PPID"
exit 1
STUB
}

# run_make <folder> <target> [VAR=value ...] — sets m_rc and m_out (stdout and stderr).
run_make() {
  local d="$1" tgt="$2"; shift 2
  m_out="$(cd "$d" && env -u MAKEFLAGS -u MAKELEVEL -u CROFTWEAVER_CHECK_LOCK -u CLAUDE_CODE_HOST_SESSION_ID "$@" \
    perl "$T/guard.pl" make "$tgt" 2>&1 </dev/null)"
  m_rc=$?
}

# start_holder <folder> <session> [VAR=value ...] — sets h (its pid, which is its group's id).
start_holder() {
  local d="$1" s="$2"; shift 2
  ( cd "$d" && exec env -u MAKEFLAGS -u MAKELEVEL -u CROFTWEAVER_CHECK_LOCK "$@" \
      CLAUDE_CODE_HOST_SESSION_ID="$s" \
      perl -e 'setpgrp(0, 0); exec @ARGV' bash scripts/check_lock.sh sleep 300 ) >/dev/null 2>&1 &
  h=$!
  holders+=("$h")
}

# wait_holder <lock file> <pid> — until the file names that pid and it lives (up to 30 s).
wait_holder() {
  local i
  for i in $(seq 1 300); do
    [ "$(sed -n 1p "$1" 2>/dev/null)" = "$2" ] && kill -0 "$2" 2>/dev/null && return 0
    sleep 0.1
  done
  fail "the holder did not take the lock within 30 s ($1)"
  return 1
}

refused() { # the last make run was refused: exit 2, Error 75, the refusal text
  [ "$m_rc" = 2 ] && case "$m_out" in *"Error 75"*"make check refused"*|*"make check refused"*"Error 75"*) true ;; *) false ;; esac
}

# --- T1: refused while another make check runs --------------------------------------------------
copy a; A="$c"; copy b; B="$c"
L1="$T/t1.lock"
start_holder "$A" local_made_up_session CROFTWEAVER_CHECK_LOCK="$L1"
if wait_holder "$L1" "$h"; then
  run_make "$B" check CROFTWEAVER_CHECK_LOCK="$L1" CHECK_STUB_MARKER="$B/marker"
  if refused && [ ! -e "$B/marker" ] \
     && case "$m_out" in *"session: local_made_up_session"*"folder:  $A"*) true ;; *) false ;; esac; then
    ok "T1 make check is refused with Error 75 while another runs, and names its session and folder"
  else
    fail "T1 make check was not refused as it should be (exit $m_rc, marker $([ -e "$B/marker" ] && echo written || echo absent)): $m_out"
  fi

  # --- T4: make package takes the lock too ------------------------------------------------------
  run_make "$B" package CROFTWEAVER_CHECK_LOCK="$L1" CHECK_STUB_MARKER="$B/marker"
  if refused && [ ! -e "$B/marker" ] && [ ! -e "$B/dist" ]; then
    ok "T4 make package is refused too, before it builds anything"
  else
    fail "T4 make package was not refused (exit $m_rc): $m_out"
  fi
fi

# --- T2: runs when nobody holds the lock --------------------------------------------------------
L2="$T/t2.lock"
for pass in first second; do
  rm -f "$B/marker"
  run_make "$B" check CROFTWEAVER_CHECK_LOCK="$L2" CHECK_STUB_MARKER="$B/marker"
  if [ "$m_rc" = 2 ] && [ -e "$B/marker" ] && case "$m_out" in *"Error 75"*|*"refused"*) false ;; *) true ;; esac; then
    ok "T2 make check runs when the lock is free ($pass run)"
  else
    fail "T2 make check did not run, or was refused, with the lock free ($pass run; exit $m_rc): $m_out"
  fi
done

# --- T3: a holder killed with kill -9 leaves no lock --------------------------------------------
L3="$T/t3.lock"
start_holder "$A" local_t3_session CROFTWEAVER_CHECK_LOCK="$L3"
if wait_holder "$L3" "$h"; then
  rm -f "$B/marker"
  run_make "$B" check CROFTWEAVER_CHECK_LOCK="$L3" CHECK_STUB_MARKER="$B/marker"
  alive_refused=0; refused && [ ! -e "$B/marker" ] && alive_refused=1
  kill -KILL "$h"; { wait "$h"; } 2>/dev/null
  for i in $(seq 1 100); do kill -0 "$h" 2>/dev/null || break; sleep 0.1; done
  run_make "$B" check CROFTWEAVER_CHECK_LOCK="$L3" CHECK_STUB_MARKER="$B/marker"
  if [ "$alive_refused" = 1 ] && [ -e "$B/marker" ] && case "$m_out" in *"Error 75"*|*"refused"*) false ;; *) true ;; esac; then
    ok "T3 a run is refused while the holder lives, and runs at once after kill -9"
  else
    fail "T3 holder alive: refused=$alive_refused; after kill -9: exit $m_rc, marker $([ -e "$B/marker" ] && echo written || echo absent): $m_out"
  fi
fi

# --- T6: a run killed by a signal fails ---------------------------------------------------------
rm -f "$T/t6.lock"
CROFTWEAVER_CHECK_LOCK="$T/t6.lock" bash "$HERE/check_lock.sh" sh -c 'kill -TERM $$' >/dev/null 2>&1
rc=$?
if [ "$rc" = 143 ]; then ok "T6 check_lock.sh exits 143 for a command killed by TERM"
else fail "T6 check_lock.sh exited $rc, not 143, for a command killed by TERM"; fi
copy c6; C6="$c"
run_make "$C6" check CROFTWEAVER_CHECK_LOCK="$T/t6b.lock" CHECK_STUB_MARKER="$C6/marker" CHECK_STUB_KILL_PARENT=1
parent="$(sed -n 1p "$C6/marker" 2>/dev/null)"
case "$(basename -- "${parent:-none}")" in
  make*|gmake*)
    # The case is that a killed run is never a pass. Make says so as "Error 143", or, when the
    # killed make loses a race with its own child, "wait: No child processes" and exit 2 (seen
    # once in CI, not reproduced here); both are a failure, so both count, with a non-zero exit.
    case "$m_out" in
      *"Error 143"*|*"wait: No child processes"*)
        if [ "$m_rc" -ne 0 ]; then ok "T6 make check fails (not a pass) when its guards are killed by TERM"
        else fail "T6 make check exited 0 when its guards were killed: $m_out"; fi ;;
      *) fail "T6 make check did not fail with Error 143 when its guards were killed (exit $m_rc): $m_out" ;;
    esac ;;
  *) fail "T6 the stub's parent is '${parent:-nothing}', not make: make no longer runs this recipe line directly, so the kill hits the wrong process" ;;
esac

# --- T7: the default lock path is shared --------------------------------------------------------
copy a7; A7="$c"; copy b7; B7="$c"
mkdir -p "$T/home" "$T/tmp1" "$T/tmp2" "$T/xdg1" "$T/xdg2" || { echo "FAIL — could not make the T7 folders."; exit 1; }
DL="$T/home/.cache/croftweaver/make-check.lock"
start_holder "$A7" local_t7_session HOME="$T/home" TMPDIR="$T/tmp1" XDG_CACHE_HOME="$T/xdg1"
if wait_holder "$DL" "$h"; then
  run_make "$B7" check HOME="$T/home" TMPDIR="$T/tmp2" XDG_CACHE_HOME="$T/xdg2" CHECK_STUB_MARKER="$B7/marker"
  if refused && [ ! -e "$B7/marker" ]; then
    ok "T7 two copies with different TMPDIR and XDG_CACHE_HOME share one default lock under HOME"
  else
    fail "T7 the default lock path is not shared (exit $m_rc, marker $([ -e "$B7/marker" ] && echo written || echo absent)): $m_out"
  fi
fi

# --- T8: a TERM or HUP to the lock holder alone reaches the command and frees the lock after it ends
# A plain kill of the outer make reaches only the process holding the lock. If it died at once, the
# guards would run on with the lock free.
ended() { local s; s="$(ps -o stat= -p "$1" 2>/dev/null)"; case "$s" in ""|Z*) return 0 ;; *) return 1 ;; esac; }
for sig in TERM HUP; do
  L8="$T/t8-$sig.lock"
  start_holder "$A" local_t8_session CROFTWEAVER_CHECK_LOCK="$L8"
  if wait_holder "$L8" "$h"; then
    kid=""
    for i in $(seq 1 100); do kid="$(pgrep -P "$h" | sed -n 1p)"; [ -n "$kid" ] && break; sleep 0.1; done
    if [ -z "$kid" ]; then
      fail "T8 $sig: the holder started no command (no child of pid $h)"
    else
      kill -"$sig" "$h"
      for i in $(seq 1 100); do ended "$h" && break; sleep 0.1; done
      if ended "$h" && ! kill -0 "$kid" 2>/dev/null; then
        { wait "$h"; } 2>/dev/null
        rm -f "$B/marker"
        run_make "$B" check CROFTWEAVER_CHECK_LOCK="$L8" CHECK_STUB_MARKER="$B/marker"
        if [ -e "$B/marker" ] && case "$m_out" in *"Error 75"*|*"refused"*) false ;; *) true ;; esac; then
          ok "T8 a $sig to the holder alone ends its command too, and the lock is free after"
        else
          fail "T8 $sig: the lock was not free after the holder ended (exit $m_rc): $m_out"
        fi
      else
        hend=no; ended "$h" && hend=yes
        krun=no; kill -0 "$kid" 2>/dev/null && krun=yes
        kill -KILL "$kid" 2>/dev/null
        fail "T8 after $sig to the holder alone: holder ended=$hend, its command (pid $kid) still running=$krun"
      fi
    fi
  fi
done

# --- T9: no stray noise on stderr, and a command that cannot start is one clear line ---------------
out="$(CROFTWEAVER_CHECK_LOCK="$T/t9.lock" bash "$HERE/check_lock.sh" true 2>&1)"; rc=$?
if [ "$rc" = 0 ] && [ -z "$out" ]; then ok "T9 a successful run prints nothing of its own"
else fail "T9 a successful run exited $rc and printed: $out"; fi
out="$(CROFTWEAVER_CHECK_LOCK="$T/t9.lock" bash "$HERE/check_lock.sh" /nonexistent/command 2>&1)"; rc=$?
if [ "$rc" = 1 ] && [ "$(printf '%s\n' "$out" | wc -l | tr -d ' ')" = 1 ] \
   && case "$out" in "make check cannot start /nonexistent/command"*) true ;; *) false ;; esac; then
  ok "T9 a command that cannot start gives exit 1 and one line"
else fail "T9 a command that cannot start: exit $rc, output: $out"; fi

# --- N1 to N7: the manager's next-in-line entry (scripts/check_next.sh) -------------------------
# Every N case but the direct set/show/clear calls enters through `make check`, as T1 does. Ids are
# made up, in the app's format. The entry is the lock's path plus .next.
IA=local_00000000-0000-0000-0000-0000000000aa
IB=local_00000000-0000-0000-0000-0000000000bb
IC=local_00000000-0000-0000-0000-0000000000cc
IM=local_00000000-0000-0000-0000-0000000000dd
TAG="croftweaver make-check next-in-line v1"
copy n; N="$c"

# nx <lock> <session or -> <check_next.sh args...> — sets n_rc and n_out.
nx() {
  local l="$1" s="$2"; shift 2
  [ "$s" = - ] && s=""
  n_out="$(cd "$N" && env -u MAKEFLAGS -u MAKELEVEL -u CROFTWEAVER_CHECK_LOCK -u CLAUDE_CODE_HOST_SESSION_ID \
    CROFTWEAVER_CHECK_LOCK="$l" ${s:+CLAUDE_CODE_HOST_SESSION_ID="$s"} \
    perl "$T/guard.pl" bash scripts/check_next.sh "$@" 2>&1 </dev/null)"
  n_rc=$?
}
# mk <lock> <session or -> — make check in the copy, as that session (the stub guard writes $N/marker).
mk() {
  local l="$1" s="$2"; rm -f "$N/marker"
  if [ "$s" = - ]; then run_make "$N" check CROFTWEAVER_CHECK_LOCK="$l" CHECK_STUB_MARKER="$N/marker"
  else run_make "$N" check CROFTWEAVER_CHECK_LOCK="$l" CLAUDE_CODE_HOST_SESSION_ID="$s" CHECK_STUB_MARKER="$N/marker"; fi
}
ran() { [ -e "$N/marker" ] && [ "$m_rc" = 2 ] && case "$m_out" in *"Error 75"*|*"refused"*) false ;; *) true ;; esac; }
no_entry() { [ ! -s "$1.next" ]; }
# emptied <lock> — the entry file exists and is empty: a run empties it in place, never unlinks it.
emptied() { [ -e "$1.next" ] && [ ! -s "$1.next" ]; }
snap() { cksum <"$1.next"; }
# put_entry <lock> <named> <setter> <epoch> — writes an entry by hand, as check_next.sh set would.
put_entry() { printf '%s\n%s\n%s\n%s\n' "$TAG" "$2" "$3" "$4" >"$1.next"; }
fmt_time() { perl -MPOSIX -e 'print strftime("%H:%M %Z", localtime($ARGV[0]))' "$1"; }
# end_holder <pid> — ends the holder's command with TERM, so its lock ends normally and writes the end time.
end_holder() {
  local kid="" i
  for i in $(seq 1 100); do kid="$(pgrep -P "$1" | sed -n 1p)"; [ -n "$kid" ] && break; sleep 0.1; done
  [ -n "$kid" ] && kill -TERM "$kid"
  for i in $(seq 1 100); do ended "$1" && break; sleep 0.1; done
  { wait "$1"; } 2>/dev/null
}
now="$(date +%s)"

# --- N1 (S1) and N6: the named session goes first, and a run writes its end time -----------------
L="$T/n1.lock"; t0="$(date +%s)"
start_holder "$N" "$IM" CROFTWEAVER_CHECK_LOCK="$L"
if wait_holder "$L" "$h"; then
  hold="$h"
  nx "$L" "$IM" set "$IA"
  nx "$L" "$IM" show
  set_ok=0; [ "$n_rc" = 0 ] && case "$n_out" in *"next:    $IA"*"10 minutes after the current run ends"*) set_ok=1 ;; esac
  end_holder "$hold"
  mk "$L" "$IB"
  b_ref=0; refused && [ ! -e "$N/marker" ] && case "$m_out" in *"next:    $IA"*) b_ref=1 ;; esac
  mk "$L" "$IA"
  if [ "$set_ok" = 1 ] && [ "$b_ref" = 1 ] && ran && emptied "$L"; then
    ok "N1 an entry holds off every other session through and after a run; the named session runs and empties it"
  else
    fail "N1 set/show ok=$set_ok, B refused naming A=$b_ref, A ran=$(ran && echo yes || echo no), entry empty=$(no_entry "$L" && echo yes || echo no): $m_out"
  fi
  ended_line="$(sed -n 5p "$L")"; e="${ended_line#ended }"
  # The last run is A's, which ended just now.
  if case "$ended_line" in "ended "[0-9]*) true ;; *) false ;; esac && [ "$e" -ge "$t0" ] && [ "$e" -le "$(( $(date +%s) + 2 ))" ]; then
    ok "N6 a run ends with an 'ended <epoch>' line in the lock file, no older than the run"
  else
    fail "N6 the lock file's fifth line is '$ended_line' (run started $t0, now $(date +%s))"
  fi
fi

# --- N2 (S2): expiry counts from the later of the set time and the end of the last run ------------
L="$T/n2.lock"
put_entry "$L" "$IA" "$IM" "$((now - 660))"
printf '1\nsess\nfolder\nsince\nended %s\n' "$((now - 660))" >"$L"
mk "$L" "$IB"
if ran && no_entry "$L" && case "$m_out" in *"expired"*"$IA"*) true ;; *) false ;; esac; then
  ok "N2 an entry 11 minutes past its set time and its last run's end expires: the next run goes, says so, and empties it"
else
  fail "N2 expired entry: marker $([ -e "$N/marker" ] && echo written || echo absent), entry empty=$(no_entry "$L" && echo yes || echo no): $m_out"
fi
put_entry "$L" "$IA" "$IM" "$((now - 660))"
printf '1\nsess\nfolder\nsince\nended %s\n' "$((now - 120))" >"$L"
before="$(snap "$L")"
mk "$L" "$IB"
if refused && [ ! -e "$N/marker" ] && [ "$(snap "$L")" = "$before" ]; then
  ok "N2 the grace counts from the end of the last run: set 11 minutes ago, run ended 2 minutes ago, still refused"
else
  fail "N2 grace from the run's end: marker $([ -e "$N/marker" ] && echo written || echo absent), exit $m_rc: $m_out"
fi

# --- N3: no session id -------------------------------------------------------------------------
L="$T/n3.lock"
put_entry "$L" "$IA" "$IM" "$now"
mk "$L" -
if refused && [ ! -e "$N/marker" ]; then ok "N3 a run with no session id is refused while an entry is live"
else fail "N3 a run with no session id was not refused (exit $m_rc): $m_out"; fi
: >"$L.next"
nx "$L" - set "$IA"; set_rc="$n_rc"
set_line="$(sed -n 3p "$L.next")"
mk "$L" "$IB"; b_ref=0; refused && [ ! -e "$N/marker" ] && case "$m_out" in *"set by:  none (CLAUDE_CODE_HOST_SESSION_ID not set)"*) b_ref=1 ;; esac
mk "$L" "$IA"
if [ "$set_rc" = 0 ] && [ "$set_line" = none ] && [ "$b_ref" = 1 ] && ran && no_entry "$L"; then
  ok "N3 set with no session id records 'none' as the setter; B is refused, A runs"
else
  fail "N3 set with no session id: exit $set_rc, setter line '$set_line', B refused naming none=$b_ref, A ran=$(ran && echo yes || echo no)"
fi

# --- N4: damaged entries -----------------------------------------------------------------------
L="$T/n4.lock"
damaged() { # damaged <what> <entry text, with \n>
  printf '%b' "$2" >"$L.next"
  local before; before="$(snap "$L")"
  mk "$L" "$IB"
  local r1=0 same=0
  [ "$m_rc" = 2 ] && [ ! -e "$N/marker" ] && case "$m_out" in *"Error 75"*"Ask the manager to clear it"*|*"Ask the manager to clear it"*"Error 75"*) r1=1 ;; esac
  [ "$(snap "$L")" = "$before" ] && same=1
  nx "$L" "$IM" clear
  if [ "$r1" = 1 ] && [ "$same" = 1 ] && [ "$n_rc" = 0 ] && no_entry "$L" && case "$n_out" in *"an unreadable entry was removed"*) true ;; *) false ;; esac; then
    ok "N4 a damaged entry ($1) refuses make check and is left alone; clear removes it"
  else
    fail "N4 damaged entry ($1): refused=$r1, unchanged=$same, clear exit $n_rc, entry empty=$(no_entry "$L" && echo yes || echo no): $m_out / $n_out"
  fi
}
damaged "no tag line" "$IA\n$IM\n$now\n"
damaged "a valid id in place of the tag" "$IM\n$IA\n$IM\n$now\n"
damaged "tag and named id only" "$TAG\n$IA\n"
damaged "a fifth line" "$TAG\n$IA\n$IM\n$now\nextra\n"
damaged "a malformed named id" "$TAG\nlocal_made_up\n$IM\n$now\n"
damaged "a malformed setter id" "$TAG\n$IA\nlocal_made_up\n$now\n"
damaged "a setter that is neither an id nor none" "$TAG\n$IA\nnobody\n$now\n"
damaged "a time that is not a number" "$TAG\n$IA\n$IM\nsoon\n"
damaged "no final newline" "$TAG\n$IA\n$IM\n$now"
damaged "a fifth line with no final newline" "$TAG\n$IA\n$IM\n$now\nX"

# --- N5 (S3, S4): set, replace, clear, show ----------------------------------------------------
L="$T/n5.lock"
nx "$L" "$IM" set "$IM"; r1=0; [ "$n_rc" = 1 ] && no_entry "$L" && r1=1
nx "$L" "$IM" set local_made_up; r2=0; [ "$n_rc" = 1 ] && no_entry "$L" && r2=1
nx "$L" "$IM" set; r3=0; [ "$n_rc" = 2 ] && no_entry "$L" && r3=1
nx "$L" local_made_up set "$IA"; r4=0; [ "$n_rc" = 1 ] && no_entry "$L" && r4=1
if [ "$r1$r2$r3$r4" = 1111 ]; then ok "N5 set refuses the caller's own id, a malformed id, a missing id and an unusable caller id, and writes nothing"
else fail "N5 set refusals (own id, malformed, missing, bad caller): $r1$r2$r3$r4"; fi
nx "$L" "$IM" set "$IA"
nx "$L" "$IM" set "$IC"; named_a=0; case "$n_out" in *"replaced the entry for $IA"*) named_a=1 ;; esac
mk "$L" "$IA"; a_ref=0; refused && [ ! -e "$N/marker" ] && case "$m_out" in *"next:    $IC"*) a_ref=1 ;; esac
mk "$L" "$IC"; c_ran=0; ran && c_ran=1
if [ "$named_a" = 1 ] && [ "$a_ref" = 1 ] && [ "$c_ran" = 1 ] && emptied "$L"; then
  ok "N5 a second set replaces the first and names it; only the new session runs"
else fail "N5 replace: named A=$named_a, A refused naming C=$a_ref, C ran=$c_ran"; fi
nx "$L" "$IM" set "$IA"; nx "$L" "$IM" clear; cl="$n_out"; cl_empty=0; emptied "$L" && cl_empty=1
mk "$L" "$IB"
if case "$cl" in *"cleared the entry for $IA"*) true ;; *) false ;; esac && [ "$cl_empty" = 1 ] && ran; then
  ok "N5 clear names the entry it removed, and the next run goes"
else fail "N5 clear: '$cl', emptied in place right after clear=$cl_empty"; fi
nx "$L" "$IM" show; s1="$n_out"
nx "$L" "$IM" clear; s2="$n_out"
put_entry "$L" "$IA" "$IM" "$((now - 100))"
printf '1\nsess\nfolder\nsince\nended %s\n' "$((now - 20))" >"$L"
nx "$L" "$IM" show; s3="$n_out"
deadpid=99999; while ps -p "$deadpid" >/dev/null 2>&1; do deadpid=$((deadpid - 1)); done
printf '%s\nsess\nfolder\nsince\n' "$deadpid" >"$L"
nx "$L" "$IM" show; s4="$n_out"
if [ "$s1" = "no entry" ] && [ "$s2" = "no entry" ] \
   && case "$s3" in *"next:    $IA"*"set by:  $IM at $(fmt_time $((now - 100)))"*"expires: $(fmt_time $((now + 580)))"*) true ;; *) false ;; esac \
   && case "$s4" in *"expires: $(fmt_time $((now + 500)))"*) true ;; *) false ;; esac; then
  ok "N5 show and clear say 'no entry'; show counts expiry from the last run's end, or from the set time when the run left no end"
else fail "N5 show: [$s1] [$s2] [$s3] [$s4]"; fi

# --- N8: the guards do not inherit the lock path the gate was given --------------------------------
# With no CROFTWEAVER_CHECK_LOCK set (the lock falls back to HOME), a guard must still see none.
mkdir -p "$T/home8" || { echo "FAIL — could not make the N8 folder."; exit 1; }
rm -f "$N/marker" "$N/env"
run_make "$N" check HOME="$T/home8" CLAUDE_CODE_HOST_SESSION_ID="$IB" CHECK_STUB_MARKER="$N/marker" CHECK_STUB_ENV="$N/env"
if ran && [ "$(cat "$N/env" 2>/dev/null)" = unset ]; then
  ok "N8 the guards run with CROFTWEAVER_CHECK_LOCK as the caller left it (unset), not as the gate needed it"
else
  fail "N8 the guards saw CROFTWEAVER_CHECK_LOCK='$(cat "$N/env" 2>/dev/null)' (exit $m_rc): $m_out"
fi

# --- N7: a held entry flock refuses after about 5 s, and changes nothing -------------------------
# The holder keeps the flock 25 s and is killed after each case, so a slow machine cannot let the
# command in after its 5 s wait.
L="$T/n7.lock"
for what in set clear show named other expired; do
  case "$what" in
    expired) rm -f "$L"; put_entry "$L" "$IA" "$IM" "$(( $(date +%s) - 660 ))" ;;
    *) put_entry "$L" "$IA" "$IM" "$(date +%s)" ;;
  esac
  before="$(snap "$L")"
  rm -f "$T/n7.held"
  ( exec perl -e 'setpgrp(0, 0); exec @ARGV' perl -e 'use Fcntl ":flock"; $| = 1; open(F, "+<", $ARGV[0]) or die; flock(F, LOCK_EX) or die; print "held\n"; sleep 25' "$L.next" >"$T/n7.held" 2>&1 ) &
  hp=$!; holders+=("$hp")
  for i in $(seq 1 300); do [ "$(cat "$T/n7.held" 2>/dev/null)" = held ] && break; sleep 0.1; done
  if [ "$(cat "$T/n7.held" 2>/dev/null)" != held ]; then
    kill -KILL -- "-$hp" 2>/dev/null; { wait "$hp"; } 2>/dev/null
    fail "N7 ($what) the test's holder did not take the entry's flock within 30 s"
    continue
  fi
  s0="$(date +%s)"
  case "$what" in
    set) nx "$L" "$IM" set "$IC" ;;
    clear) nx "$L" "$IM" clear ;;
    show) nx "$L" "$IM" show ;;
    named) mk "$L" "$IA" ;;
    *) mk "$L" "$IB" ;;
  esac
  took=$(( $(date +%s) - s0 ))
  kill -KILL -- "-$hp" 2>/dev/null; { wait "$hp"; } 2>/dev/null
  rc_ok=0
  case "$what" in
    set|clear|show) [ "$n_rc" = 1 ] && rc_ok=1; out="$n_out" ;;
    *) [ "$m_rc" = 2 ] && [ ! -e "$N/marker" ] && case "$m_out" in *"Error 75"*) rc_ok=1 ;; esac; out="$m_out" ;;
  esac
  if [ "$rc_ok" = 1 ] && [ "$took" -ge 4 ] && [ "$took" -le 18 ] && [ "$(snap "$L")" = "$before" ] \
     && case "$out" in *"$L.next is held by another command"*) true ;; *) false ;; esac; then
    ok "N7 ($what) a held next-in-line file refuses after about 5 s (4 to 18) and is left unchanged"
  else
    fail "N7 ($what): refused=$rc_ok after ${took}s, entry unchanged=$([ "$(snap "$L")" = "$before" ] && echo yes || echo no): $out"
  fi
done

if [ "$fails" -gt 0 ]; then
  echo "test_check_lock.sh: $fails case(s) failed"
  exit 1
fi
echo "test_check_lock.sh: all cases passed"
