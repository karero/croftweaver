# Reads `codex mcp list --json` (the file named by the argument) and prints, for each enabled
# server, the line `mcp_servers.<name>.enabled=false`, to turn it off for one run (run_codex in
# independent_review.sh). A name that is not a TOML bare key (A-Za-z0-9_-) cannot go into a -c
# override safely, so it is not printed: stderr names it and says it stays on. Names always come
# from the list: naming a server that is not configured stops Codex.
# Exit 0 with the lines (none for an empty list); 1, with a reason on stderr, when the file is not
# a JSON list of objects.
use 5.010;
use strict;
use warnings;
use JSON::PP;

my $file = shift @ARGV;
defined $file or die "codex_mcp_off.pl: a file name is needed\n";
open my $f, '<', $file or die "codex_mcp_off.pl: cannot read $file: $!\n";
binmode $f;
my $json = do { local $/; <$f> };
my $list = eval { JSON::PP->new->utf8->decode($json) };
ref $list eq 'ARRAY' or do { print STDERR "codex_mcp_off.pl: not a JSON list\n"; exit 1 };
for my $s (@$list) {
  ref $s eq 'HASH' && defined $s->{name} && !ref $s->{name} or do { print STDERR "codex_mcp_off.pl: an entry has no name\n"; exit 1 };
  $s->{enabled} or next;
  my $n = $s->{name};
  if ($n =~ /\A[A-Za-z0-9_-]+\z/) { print "mcp_servers.$n.enabled=false\n"; next }
  (my $shown = $n) =~ s/[^\x20-\x7E]/?/g;
  print STDERR "codex: MCP server \"$shown\" stays on: its name is not a plain key\n";
}
exit 0;
