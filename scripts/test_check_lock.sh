#!/usr/bin/env bash
#
# test_check_lock.sh — checks that `make check` refuses to start while another `make check` of
# the same user holds the lock (scripts/check_lock.sh), and that a killed run is never a pass.
#
# Why it exists: runs outside the slots the release manager hands out kept overlapping, and
# seven at once pushed this Mac's load past what the browser tests survive. The lock is only
# worth having if the real `make check` goes through it, so every case enters the way production
# does: it runs `make check` (or `make package`) in a copy of the real Makefile and check_lock.sh.
# The exceptions are the unit-level cases (T6's exit status, T8's signal forwarding), which run the
# script directly beside the case that goes through make.
# In the copy the first guard, scripts/check_clean.sh, is a stub that writes a marker file and
# fails, so no case runs the real guards or recurses into this test.
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

# copy <name> — a folder holding the real Makefile and check_lock.sh and the stub guard; sets c.
# The stub notes its parent's command name in the marker and, with CHECK_STUB_KILL_PARENT set,
# kills that parent (the inner make) with TERM.
copy() {
  c="$T/$1"
  mkdir -p "$c/scripts" \
    && cp "$ROOT/Makefile" "$c/Makefile" \
    && cp "$HERE/check_lock.sh" "$c/scripts/check_lock.sh" \
    && cat >"$c/scripts/check_clean.sh" <<'STUB' \
    || { echo "FAIL — could not build the copy $1."; exit 1; }
printf '%s\n' "$(ps -o comm= -p "$PPID" 2>/dev/null)" >"$CHECK_STUB_MARKER"
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
    case "$m_out" in
      *"Error 143"*) ok "T6 make check fails with Error 143 when its guards are killed by TERM" ;;
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

# --- T8: a TERM to the lock holder alone reaches the command and frees the lock after it ends ----
# A plain kill of the outer make reaches only the process holding the lock. If it died at once, the
# guards would run on with the lock free.
ended() { local s; s="$(ps -o stat= -p "$1" 2>/dev/null)"; case "$s" in ""|Z*) return 0 ;; *) return 1 ;; esac; }
L8="$T/t8.lock"
start_holder "$A" local_t8_session CROFTWEAVER_CHECK_LOCK="$L8"
if wait_holder "$L8" "$h"; then
  kid=""
  for i in $(seq 1 100); do kid="$(pgrep -P "$h" | sed -n 1p)"; [ -n "$kid" ] && break; sleep 0.1; done
  if [ -z "$kid" ]; then
    fail "T8 the holder started no command (no child of pid $h)"
  else
    kill -TERM "$h"
    for i in $(seq 1 100); do ended "$h" && break; sleep 0.1; done
    if ended "$h" && ! kill -0 "$kid" 2>/dev/null; then
      { wait "$h"; } 2>/dev/null
      rm -f "$B/marker"
      run_make "$B" check CROFTWEAVER_CHECK_LOCK="$L8" CHECK_STUB_MARKER="$B/marker"
      if [ -e "$B/marker" ] && case "$m_out" in *"Error 75"*|*"refused"*) false ;; *) true ;; esac; then
        ok "T8 a TERM to the holder alone ends its command too, and the lock is free after"
      else
        fail "T8 the lock was not free after the holder ended (exit $m_rc): $m_out"
      fi
    else
      hend=no; ended "$h" && hend=yes
      krun=no; kill -0 "$kid" 2>/dev/null && krun=yes
      kill -KILL "$kid" 2>/dev/null
      fail "T8 after TERM to the holder alone: holder ended=$hend, its command (pid $kid) still running=$krun"
    fi
  fi
fi

# --- T9: no stray noise on stderr, and a command that cannot start is one clear line ---------------
out="$(CROFTWEAVER_CHECK_LOCK="$T/t9.lock" bash "$HERE/check_lock.sh" true 2>&1)"; rc=$?
if [ "$rc" = 0 ] && [ -z "$out" ]; then ok "T9 a successful run prints nothing of its own"
else fail "T9 a successful run exited $rc and printed: $out"; fi
out="$(CROFTWEAVER_CHECK_LOCK="$T/t9.lock" bash "$HERE/check_lock.sh" /nonexistent/command 2>&1)"; rc=$?
if [ "$rc" = 1 ] && [ "$(printf '%s\n' "$out" | wc -l | tr -d ' ')" = 1 ] \
   && case "$out" in "make check cannot start /nonexistent/command"*) true ;; *) false ;; esac; then
  ok "T9 a command that cannot start gives exit 1 and one line"
else fail "T9 a command that cannot start: exit $rc, output: $out"; fi

if [ "$fails" -gt 0 ]; then
  echo "test_check_lock.sh: $fails case(s) failed"
  exit 1
fi
echo "test_check_lock.sh: all cases passed"
