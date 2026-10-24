# readable_tail's cleanup: the last bytes of a tier's .err/.out on stdin, printed as at most 8 readable
# lines (see readable_tail in independent_review.sh for what is dropped and why).
# Perl 5.8: a FAILED section is printed for any tier, on any Perl, so nothing newer may be used here.
use 5.008;
use Encode qw(decode encode);

local $/;   # the whole input is one record, as with -0777 -n
while (<>) {
  $_ = decode("UTF-8", $_);                       # bad bytes become U+FFFD
  s/\e\[[0-9;?]*G|\r/\n/g;                        # cursor-to-column / CR: a redraw
  s/\e\[[\x30-\x3f]*[\x20-\x2f]*[\x40-\x7e]//g;   # any other CSI (ECMA-48 grammar)
  s/\e\][^\a\e]*(?:\a|\e\\)?//g;                  # OSC
  s/\e[\x20-\x2f]*[\x30-\x7e]?//g;                # any other ESC sequence
  s/[\x00-\x08\x0b-\x1f\x7f]//g;                  # remaining control characters
  s/[\x{2800}-\x{28FF}]//g;                       # braille spinner frames
  my (@l, $prev);
  for (split /\n/) {
    s/\s+$//;
    next if $_ eq "" or (defined $prev and $_ eq $prev);
    push @l, $_; $prev = $_;
  }
  splice(@l, 0, @l - 8) if @l > 8;
  print encode("UTF-8", "$_\n") for @l;
}
