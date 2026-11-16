# Is the file (the argument) valid UTF-8 for the decoder the request builders use, Encode's strict
# "UTF-8"? Exit 0 if so; 1 if not, or if it cannot be read (seat_fits then counts every byte as a
# 3-byte U+FFFD, the most a decoder makes of one bad byte).
# With --where first, the test is well-formed UTF-8 (RFC 3629), the rule codex-cli applies to its
# prompt: noncharacters such as U+FFFF pass, which Encode refuses. A file that fails gets one line
# on stdout saying where its first bad byte is, and the "diff --git" header above it, if any, so the
# owner knows which file to fix. A file it cannot read exits 1 with no line.
use 5.008;
use Encode ();

my $where = @ARGV && $ARGV[0] eq '--where' ? shift @ARGV : '';
open my $f, '<', $ARGV[0] or exit 1;
binmode $f;
local $/; my $s = <$f>;
defined $s or exit 1;   # a read error (a folder, say); an empty file reads as ''
unless ($where) {
  my $copy = $s;        # decode with a CHECK may change the string it is given
  exit(eval { Encode::decode('UTF-8', $copy, Encode::FB_CROAK()); 1 } ? 0 : 1);
}
# Well-formed UTF-8 sequences (RFC 3629: no overlongs, surrogates or code points above U+10FFFF).
my $ok = qr/[\x00-\x7F]+|[\xC2-\xDF][\x80-\xBF]|\xE0[\xA0-\xBF][\x80-\xBF]|[\xE1-\xEC\xEE\xEF][\x80-\xBF]{2}|\xED[\x80-\x9F][\x80-\xBF]|\xF0[\x90-\xBF][\x80-\xBF]{2}|[\xF1-\xF3][\x80-\xBF]{3}|\xF4[\x80-\x8F][\x80-\xBF]{2}/;
1 while $s =~ /\G(?:$ok)/gc;
my $at = pos($s) || 0;
exit 0 if $at >= length $s;
my $before = substr($s, 0, $at);
my $line = ($before =~ tr/\n//) + 1;
my $part = '';
if ($before =~ /.*^(diff --git [^\n]*)/ms) {
  (my $head = $1) =~ tr/\x20-\x7E/?/c;   # the header is the diff's own text: no control byte reaches the terminal
  $part = ", in the part that starts \"$head\"";
}
print "the first bad byte is on line $line of the prompt$part";
exit 1;
