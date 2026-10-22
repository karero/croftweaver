# Runs a command under a time limit, for the base check's fetch (independent_review.sh, "BASE
# CHECK" in its header; macOS has no `timeout`). Arguments: the limit in whole seconds, then the
# command. The command runs in a process group of its own, and when the limit passes the whole
# group is ended (TERM, then KILL 2 seconds later), so a helper git started (ssh, git-remote-https,
# an ext:: command) dies with it: a helper left alive would hold the caller's output pipe open,
# and the caller would wait for it. Exit: the command's own status, or 142 when the limit passed.
# Perl 5.8: this path has no Perl version check, so nothing newer may be used here.
use 5.008;
use strict;
use warnings;

my $limit = shift @ARGV;
die "run_limited.pl: a whole number of seconds, then a command\n" unless defined $limit && $limit =~ /^[1-9][0-9]*\z/ && @ARGV;
my $pid = fork;
die "run_limited.pl: cannot fork: $!\n" unless defined $pid;
if ($pid == 0) {
  setpgrp(0, 0);
  exec { $ARGV[0] } @ARGV or exit 127;
}
my $late = 0;
$SIG{ALRM} = sub {
  $late = 1;
  kill 'TERM', -$pid;
  $SIG{ALRM} = sub { kill 'KILL', -$pid; };
  alarm 2;
};
alarm $limit;
waitpid($pid, 0);
my $status = $?;
alarm 0;
if ($late) { kill 'KILL', -$pid; exit 142; }
exit($status & 127 ? 128 + ($status & 127) : $status >> 8);
