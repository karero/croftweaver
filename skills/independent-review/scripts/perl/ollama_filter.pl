# The ollama CLI transport's output filter (ollama_via_cli): undoes the terminal redraw codes in
# `ollama run`'s stdout and leaves the clean review on stdout. Reads the whole capture (the file named
# as the argument). Exit 3: not valid UTF-8; exit 4: an escape the loop cannot parse.
# Perl 5.8: this path has no Perl version check, so nothing newer may be used here.
use 5.008;
use Encode qw(decode encode FB_CROAK);

local $/;   # the whole input is one record, as with -0777 -n
while (<>) {
  my $s = eval { decode("UTF-8", $_, FB_CROAK) };
  if (!defined $s) { print STDERR "ollama output is not valid UTF-8 — refusing to filter it\n"; exit 3; }
  my $out = "";
  # Every escape shape is consumed, and anything the loop cannot parse fails the tier:
  # an unrecognised escape (e.g. ESC[0~) used to end the loop, silently dropping the
  # rest of the review while the tier still counted (round 2, Codex; pre-existing).
  while ($s =~ /\G(?:([^\e]+)|\e\[(\d+)D\e\[K|\e\[[\x30-\x3f]*[\x20-\x2f]*[\x40-\x7e]|\e\][^\a\e]*(?:\a|\e\\)|\e[\x20-\x2f]*[\x30-\x7e])/gc) {
    if (defined $1) { $out .= $1; next; }
    next unless defined $2;
    my $n = $2;
    my $line_len = length($out) - rindex($out, "\n") - 1;
    $n = $line_len if $n > $line_len;
    substr($out, length($out) - $n, $n, "") if $n > 0;
  }
  # No `//` here (Perl 5.10): unlike the API transports, this path has no Perl version check.
  if ((defined pos($s) ? pos($s) : 0) < length($s)) { print STDERR "ollama output filter could not parse an escape sequence — refusing a truncated review\n"; exit 4; }
  print encode("UTF-8", $out);
}
