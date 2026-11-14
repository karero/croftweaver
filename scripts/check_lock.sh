#!/usr/bin/env bash
# check_lock.sh <command...> — runs the command only if no other `make check` of this user is
# running on this Mac. `make check` calls it, so use `make check`, not this script, by hand.
#
# Why: the guards are heavy, and runs that overlap push the machine's load high enough to fail
# the browser tests. A second run is refused at once; it never waits. Exit status: the command's
# own; 128 plus the signal number when a signal killed it; 1 when it could not be started or the
# lock could not be taken; 75 when another run holds the lock.
#
# The lock is a flock(2) on one file per user, so every checkout and session shares it, and the
# kernel drops it when the holder dies, even on kill -9. macOS has no flock command, so Perl
# (which ships with macOS) takes it. The file also holds the holder's details, written best
# effort so a refused run can say who holds the lock. Perl marks the descriptor close-on-exec,
# so the guards the command starts do not inherit the lock; a TERM or HUP sent to this process alone
# is passed on to the command, and the lock is held until the command ends.
#
# CROFTWEAVER_CHECK_LOCK overrides the file's path, for the tests.
set -u

[ $# -gt 0 ] || { echo "usage: check_lock.sh <command...>" >&2; exit 2; }
command -v perl >/dev/null 2>&1 \
  || { echo "make check cannot take its lock: perl was not found on the PATH." >&2; exit 1; }
lock="${CROFTWEAVER_CHECK_LOCK:-}"
if [ -z "$lock" ]; then
  [ -n "${HOME:-}" ] || { echo "make check cannot take its lock: HOME is not set." >&2; exit 1; }
  lock="$HOME/.cache/croftweaver/make-check.lock"
fi
dir="$(dirname -- "$lock")"
mkdir -p -- "$dir" || { echo "make check cannot create the lock folder $dir" >&2; exit 1; }

exec perl -e '
use strict; use warnings; no warnings "exec";
use Fcntl qw(:flock O_RDWR O_CREAT);
use POSIX qw(strftime);
use Cwd qw(getcwd);
my ($lock, @cmd) = @ARGV;
$| = 1;
sysopen(my $fh, $lock, O_RDWR | O_CREAT, 0600)
  or do { print STDERR "make check cannot open its lock file $lock: $!\n"; exit 1 };
chmod 0600, $fh;
if (!flock($fh, LOCK_EX | LOCK_NB)) {
  my $err = $!;
  if (!$!{EWOULDBLOCK}) { print STDERR "make check cannot lock $lock: $err\n"; exit 1 }
  my $buf = ""; sysread($fh, $buf, 4096);
  my ($pid, $session, $folder, $since) = split /\n/, $buf, 5;
  my @d = map { my $v = defined $_ ? $_ : ""; $v =~ s/[[:cntrl:]]//g; $v } ($session, $folder, $since);
  my $live = defined $pid && $pid =~ /^[0-9]+$/ && $pid > 0 && !grep({ $_ eq "" } @d)
    && (kill(0, $pid) || $!{EPERM});
  my ($s, $f, $t) = $live ? @d : ("(not written yet)") x 3;
  $t .= " (pid $pid)" if $live;
  print STDERR "make check refused: another make check (perhaps inside make package or make smoke) is\n",
    "already running on this Mac.\n",
    "  session: $s\n  folder:  $f\n  since:   $t\n",
    "Wait for that run to end. If a manager session hands out make check slots, ask it for one.\n",
    "Do not start another run yourself, and do not retry in a loop.\n";
  exit 75;
}
my $sess = $ENV{CLAUDE_CODE_HOST_SESSION_ID};
$sess = "none (CLAUDE_CODE_HOST_SESSION_ID not set)" if !defined $sess || $sess eq "";
my $info = join "", map { my $v = $_; $v =~ s/[[:cntrl:]]//g; "$v\n" }
  ($$, $sess, getcwd() // "(unknown)", strftime("%Y-%m-%d %H:%M %Z", localtime));
# Overwrite from the start, then cut the old tail: a refused run never reads a half-empty file.
sysseek($fh, 0, 0);
syswrite($fh, $info);
truncate($fh, length $info);
# TERM and HUP (a plain kill of make reaches only this process) go on to the command, and the lock
# stays held until it ends. They are set before the fork so no signal finds the default action; one
# that arrives before the command exists is sent on once it does. INT and QUIT also reach the command
# from the terminal, so they are ignored here.
my ($kid, $sig);
$SIG{INT} = $SIG{QUIT} = "IGNORE";
$SIG{TERM} = sub { $sig = "TERM"; kill "TERM", $kid if $kid };
$SIG{HUP}  = sub { $sig = "HUP";  kill "HUP",  $kid if $kid };
$kid = fork;
if (!defined $kid) { print STDERR "make check cannot start $cmd[0]: $!\n"; exit 1 }
if (!$kid) {
  $SIG{$_} = "DEFAULT" for qw(INT QUIT TERM HUP);
  exec { $cmd[0] } @cmd;
  print STDERR "make check cannot start $cmd[0]: $!\n";
  POSIX::_exit(1);
}
kill $sig, $kid if $sig;
my $w;
do { $w = waitpid($kid, 0) } while ($w == -1 && $!{EINTR});
my $rc = $?;
exit(128 + ($rc & 127)) if $rc & 127;
exit($rc >> 8);
' -- "$lock" "$@"
