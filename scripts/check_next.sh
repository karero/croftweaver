#!/usr/bin/env bash
# check_next.sh set <session> | show | clear — the "next in line" entry for `make check`. Meant for
# the manager session that hands out make check slots; a run of `make check` only ever empties it.
#
# Why: the lock (scripts/check_lock.sh) refuses a second run but cannot see the manager's order, so
# whoever ran first after a run ended won. While an entry is live the lock refuses every session but
# the named one. An entry is live until 10 minutes after the later of the time it was set and the
# end of the last run, so a named session that never comes blocks the others for 10 minutes at most.
#
# The entry is one file beside the lock (the lock's path plus .next): empty means no entry, else
# four lines (a tag, the named session, the setter, the set time in epoch seconds). It is never
# unlinked. Every read and write goes through this script's flock on that file, held from the read
# to the write: the lock calls it as `check_next.sh gate` (internal) after it holds the lock, so the
# check and the emptying of an entry cannot interleave with a `set`. That flock waits up to 5 s and
# then refuses; `set`, `show` and `clear` exit 1, the lock's check exits 75.
#
# `set` takes the session's id as that session's own shell prints it (echo
# $CLAUDE_CODE_HOST_SESSION_ID), and refuses the caller's own id. This guards against mistakes, not
# against a session that sets the variable on purpose. `show`'s expiry line is advisory (it reads
# the lock file without the lock); only the lock's check decides.
#
# CROFTWEAVER_CHECK_LOCK overrides the lock's path, and so the entry's, for the tests.
set -u

case "${1:-}" in
  set|show|clear|gate) ;;
  *) echo "usage: check_next.sh set <session> | show | clear" >&2; exit 2 ;;
esac
command -v perl >/dev/null 2>&1 \
  || { echo "check_next.sh cannot run: perl was not found on the PATH." >&2; exit 1; }
lock="${CROFTWEAVER_CHECK_LOCK:-}"
if [ -z "$lock" ]; then
  [ -n "${HOME:-}" ] || { echo "check_next.sh cannot find the lock: HOME is not set." >&2; exit 1; }
  lock="$HOME/.cache/croftweaver/make-check.lock"
fi
mkdir -p -- "$(dirname -- "$lock")" || { echo "check_next.sh cannot create the lock folder for $lock" >&2; exit 1; }

exec perl -e '
use strict; use warnings;
use Fcntl qw(:flock O_RDWR O_CREAT);
use POSIX qw(strftime);
my ($lockfile, $mode, @args) = @ARGV;
my $entry = "$lockfile.next";
my $TAG   = "croftweaver make-check next-in-line v1";
my $ID    = qr/local_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/;
my $GRACE = 600;
my $me = $ENV{CLAUDE_CODE_HOST_SESSION_ID}; $me = "" if !defined $me;
$| = 1;

sub when  { strftime("%H:%M %Z", localtime($_[0])) }
sub who   { $_[0] eq "none" ? "none (CLAUDE_CODE_HOST_SESSION_ID not set)" : $_[0] }
sub later { $_[0] > $_[1] ? $_[0] : $_[1] }

# Opens the entry (creating it empty) and takes its flock, waiting up to 5 s. Exits $busy on a
# held flock, so the lock can refuse with 75 and the commands with 1.
sub open_entry {
  my $busy = shift;
  sysopen(my $fh, $entry, O_RDWR | O_CREAT, 0600)
    or do { print STDERR "check_next.sh cannot open $entry: $!\n"; exit 1 };
  chmod(0600, $fh) or do { print STDERR "check_next.sh cannot secure $entry: $!\n"; exit 1 };
  my $tries = 0;
  while (!flock($fh, LOCK_EX | LOCK_NB)) {
    if (!$!{EWOULDBLOCK}) { print STDERR "check_next.sh cannot lock $entry: $!\n"; exit 1 }
    if (++$tries > 100) {
      print STDERR "the next-in-line file $entry is held by another command; try again, or ask the manager.\n";
      exit $busy;
    }
    select(undef, undef, undef, 0.05);
  }
  return $fh;
}

# The entry as ("none") for an empty file, ("bad") for anything but the four exact lines, else
# ("ok", named, setter, set time).
sub read_entry {
  my $fh = shift;
  sysseek($fh, 0, 0);
  my $buf = "";
  while (length($buf) <= 8192) {
    my $r = sysread($fh, $buf, 4096, length $buf);
    if (!defined $r) { print STDERR "check_next.sh cannot read $entry: $!\n"; exit 1 }
    last if !$r;
  }
  return ("none") if $buf eq "";
  my @l = split /\n/, $buf, -1;
  return ("bad") unless @l == 5 && $l[4] eq "" && $l[0] eq $TAG && $l[1] =~ /\A$ID\z/
    && ($l[2] =~ /\A$ID\z/ || $l[2] eq "none") && $l[3] =~ /\A[0-9]{1,15}\z/;
  return ("ok", @l[1 .. 3]);
}

sub empty_entry {
  my $fh = shift;
  truncate($fh, 0) or do { print STDERR "check_next.sh cannot empty $entry: $!\n"; exit 1 };
}

# The last run as ("running"), ("ended", epoch) or ("unknown"), from the lock file, which is read
# without the lock.
sub last_run {
  open(my $lf, "<", $lockfile) or return ("unknown");
  local $/; my $b = <$lf>; $b = "" if !defined $b;
  my @l = split /\n/, $b;
  return ("ended", $1) if defined $l[4] && $l[4] =~ /\Aended ([0-9]{1,15})\z/;
  return ("running") if defined $l[0] && $l[0] =~ /\A[0-9]+\z/ && $l[0] > 0 && (kill(0, $l[0]) || $!{EPERM});
  return ("unknown");
}

sub describe {
  my ($named, $setter, $set, $until) = @_;
  return "  next:    $named\n  set by:  " . who($setter) . " at " . when($set) . "\n  expires: $until\n";
}

if ($mode eq "gate") {
  # Called by check_lock.sh with the lock held: the one place a run reads or empties an entry.
  my $ended = (defined $args[0] && $args[0] =~ /\A[0-9]{1,15}\z/) ? $args[0] : 0;
  my $fh = open_entry(75);
  my ($st, $named, $setter, $set) = read_entry($fh);
  exit 0 if $st eq "none";
  if ($st eq "bad") {
    print STDERR "make check refused: the next-in-line file $entry is damaged.\n",
      "Ask the manager to clear it (check_next.sh clear). Do not edit it yourself.\n";
    exit 75;
  }
  if ($me ne "" && $me eq $named) { empty_entry($fh); exit 0 }
  my $until = later($set, $ended) + $GRACE;
  if (time < $until) {
    print STDERR "make check refused: the manager has given the next make check slot to another session.\n",
      describe($named, $setter, $set, when($until) . ", if that session has not started its run by then"),
      "Wait, or ask the manager for a slot. Do not set or clear the entry yourself, and do not retry\n",
      "in a loop.\n";
    exit 75;
  }
  empty_entry($fh);
  print STDERR "an expired next-in-line entry for $named was removed\n";
  exit 0;
}

if ($mode eq "set") {
  if (@args != 1) { print STDERR "usage: check_next.sh set <session>\n"; exit 2 }
  my $id = $args[0];
  if ($id !~ /\A$ID\z/) {
    print STDERR "check_next.sh set: \"$id\" is not a session id (local_ and a lowercase UUID). ",
      "Use what that session prints for: echo \$CLAUDE_CODE_HOST_SESSION_ID\n";
    exit 1;
  }
  if ($id eq $me) { print STDERR "check_next.sh set: a session cannot put itself next; ask the manager.\n"; exit 1 }
  my $setter = $me eq "" ? "none" : $me;
  if ($setter ne "none" && $setter !~ /\A$ID\z/) {
    print STDERR "check_next.sh set: your own CLAUDE_CODE_HOST_SESSION_ID is not a session id, so the entry could not name who set it.\n";
    exit 1;
  }
  my $fh = open_entry(1);
  my ($st, $old) = read_entry($fh);
  my $now = time;
  my $text = "$TAG\n$id\n$setter\n$now\n";
  sysseek($fh, 0, 0);
  my $w = syswrite($fh, $text);
  if (!defined $w || $w != length $text || !truncate($fh, length $text)) {
    print STDERR "check_next.sh cannot write $entry: " . ($! || "short write") . "\n"; exit 1;
  }
  print "next make check slot: $id\n";
  print describe($id, $setter, $now, "10 minutes from now, or from the end of the current run if one is running");
  print "Check that id against what that session prints for: echo \$CLAUDE_CODE_HOST_SESSION_ID\n";
  print "This replaced the entry for $old.\n" if $st eq "ok";
  print "This replaced an unreadable entry.\n" if $st eq "bad";
  exit 0;
}

if ($mode eq "show" || $mode eq "clear") {
  if (@args) { print STDERR "usage: check_next.sh $mode\n"; exit 2 }
  my $fh = open_entry(1);
  my ($st, $named, $setter, $set) = read_entry($fh);
  if ($mode eq "clear") {
    if ($st eq "none") { print "no entry\n"; exit 0 }
    empty_entry($fh);
    print $st eq "ok" ? "cleared the entry for $named (set by " . who($setter) . ")\n"
                      : "an unreadable entry was removed\n";
    exit 0;
  }
  if ($st eq "none") { print "no entry\n"; exit 0 }
  if ($st eq "bad") {
    print "the next-in-line file $entry is damaged: every make check is refused until `check_next.sh clear`\n";
    exit 0;
  }
  my ($kind, $ended) = last_run();
  my $until;
  if ($kind eq "running") { $until = "10 minutes after the current run ends" }
  else {
    my $t = later($set, $kind eq "ended" ? $ended : 0) + $GRACE;
    $until = when($t) . (time >= $t ? " (expired: the next make check removes it)" : "");
  }
  print describe($named, $setter, $set, $until);
  exit 0;
}
' -- "$lock" "$@"
