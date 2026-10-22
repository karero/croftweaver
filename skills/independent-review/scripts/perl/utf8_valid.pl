# Is the file (the argument) valid UTF-8 for the decoder the request builders use, Encode's strict
# "UTF-8"? Exit 0 if so; 1 if not, or if it cannot be read (seat_fits then counts every byte as a
# 3-byte U+FFFD, the most a decoder makes of one bad byte).
use 5.008;
use Encode ();

open my $f, '<', $ARGV[0] or exit 1;
binmode $f;
local $/; my $s = <$f>; $s = '' unless defined $s;
exit(eval { Encode::decode('UTF-8', $s, Encode::FB_CROAK()); 1 } ? 0 : 1);
