# The Melious reply reader (run_melious): arguments are the response file, the HTTP code, the tokens
# file, this run's final-review marker and the melious.full path. Prints the review with its notes;
# errors go to stderr as "Error: HTTP <code>: ...". Exit 2: an error reply (not 200); 3: a stream chunk
# that is not JSON; 4: a truncated review; 5: no review text; 6: an error mid-stream; 7: not a stream
# (one JSON object, or a body that is not JSON); 8: an empty reply; 9: an error reply that is not a
# stream (200); 1: the reader itself failed. run_melious names each in the summary line.
use 5.010;
use JSON::PP;
use Encode;

# A die outside an eval exits with errno, which can collide with the codes above: exit 1 instead.
# $^S is undef while code compiles, as in a require inside an eval: that die is left alone.
$SIG{__DIE__} = sub { return if !defined $^S || $^S; print STDERR "melious_stream.pl: ", @_; exit 1 };

my ($file, $code, $tok, $mark, $full) = @ARGV;
open my $f, "<", $file or do { print STDERR "Error: HTTP $code: no response body\n"; exit($code eq "200" ? 8 : 2) };
my $json = JSON::PP->new->utf8;
sub errtext { my $e = shift; $e = $e->{message} // JSON::PP->new->encode($e) if ref $e eq "HASH";
              $e = JSON::PP->new->encode($e) if ref $e; $e }
# A quote of server text: whitespace and control bytes collapsed to one space (so nothing in it
# can start a new line where the classifier reads), cut to 300 bytes (the handle is raw, so a
# multibyte character can be split; readable_tail decodes leniently). No s///r: the API
# transports need Perl 5.10, not 5.14.
sub quoted { my $s = shift; $s =~ s/[\s\x00-\x1f\x7f]+/ /g; $s =~ s/^ | $//g; substr($s, 0, 300) }
if ($code ne "200") {   # an error reply is one JSON object, not a stream
  local $/; my $raw = <$f> // "";
  my $j = eval { $json->decode($raw) };
  my $m = (ref $j eq "HASH" && defined $j->{error}) ? errtext($j->{error})
        : "response is not JSON: " . quoted($raw);
  print STDERR "Error: HTTP $code: $m\n"; exit 2;
}
my ($c, $done, $fin, $usage, $n, $think) = ("", 0, undef, undef, 0, 0);
while (my $line = <$f>) {
  next unless $line =~ /^data:[ \t]*(.*?)\s*$/;
  my $d = $1;
  if ($d eq "[DONE]") { $done = 1; next }
  my $j = eval { $json->decode($d) };
  if (ref $j ne "HASH") { print STDERR "Error: HTTP $code: a stream chunk is not JSON\n    chunk began: ", quoted($d), "\n"; exit 3 }
  if (defined $j->{error}) { print STDERR "Error: HTTP $code: ", errtext($j->{error}), "\n"; exit 6 }
  $n++;
  $usage = $j->{usage} if ref $j->{usage} eq "HASH";
  my $ch = ref $j->{choices} eq "ARRAY" ? $j->{choices}[0] : undef;
  next unless ref $ch eq "HASH";
  if (ref $ch->{delta} eq "HASH") {
    my $dl = $ch->{delta};
    $c .= $dl->{content} if defined $dl->{content} && !ref $dl->{content};
    for my $k (qw(reasoning_content reasoning)) { $think += length $dl->{$k} if defined $dl->{$k} && !ref $dl->{$k} }
  }
  $fin = $ch->{finish_reason} if defined $ch->{finish_reason};
}
if (!$n && !$done) {   # no stream at all: a whole JSON body is the server ignoring stream:true
  seek $f, 0, 0; local $/; my $body = <$f> // "";
  if ($body !~ /\S/) { print STDERR "Error: HTTP $code: an empty reply\n"; exit 8 }
  # The quote goes on its own indented line, which the classifier skips.
  my $j = eval { $json->decode($body) };
  if (ref $j eq "HASH") {
    my $why = defined $j->{error} ? errtext($j->{error}) : "the reply was one JSON object, not a stream (stream:true ignored?)";
    print STDERR "Error: HTTP $code: $why\n    reply began: ", quoted($body), "\n"; exit(defined $j->{error} ? 9 : 7);
  }
  # Not JSON either (an HTML page from a proxy, say): named, not left to read as a truncated review.
  # A body of SSE lines that carried no data (keep-alive comments, then the connection closed) is a
  # stream that ended early, and falls through to the truncated-review check below.
  if ($body !~ /^(?::|event:|id:|retry:)/m) {
    print STDERR "Error: HTTP $code: the reply is not a stream, and not JSON\n    reply began: ", quoted($body), "\n"; exit 7;
  }
}
# The reply as it came, before any check or trim, on every path that reaches the finish check
# (melious.full). An error chunk or a non-JSON chunk stops earlier; melious.resp holds the stream.
my $saved = 0;
if (length $c && open my $fh, ">:encoding(UTF-8)", $full) { $saved = (print $fh $c) && close $fh }
# No chunk count in the message: a bare 429 there would read as a quota refusal (QUOTA_RE).
if (!$done && !defined $fin) { print STDERR "Error: HTTP $code: the stream ended without a finish_reason or [DONE] — a truncated review\n"; exit 4 }
# The finish_reason from the server goes on an Error: line, which the quota classifier reads: only a
# short plain word reaches it (no newline, no 429 forged from a longer value).
if (defined $fin) { $fin = "<not a string>" if ref $fin; $fin =~ s/[^A-Za-z_.-]/_/g; $fin = substr($fin, 0, 40) }
if (defined $fin && $fin ne "stop") {
  print STDERR "Error: HTTP $code: the reply stopped early (finish_reason $fin) — a truncated review",
    ($fin eq "length" ? "; raise MELIOUS_MAX_TOKENS" : ""), "\n"; exit 4;
}
# Think blocks inlined in content: closed ones whose opener starts a line, anywhere in the
# reply, then such an opener never closed (all of the rest is thinking). The tags are built,
# not written out: with literal tags in this file, a review of a diff touching it made the
# provider end the reasoning at a quoted closing tag (#165).
# Only an opener that starts a line is a trace: a review may quote the tag inline while
# discussing tag handling, and must not lose the text after it. What is cut is noted.
my ($open, $close) = ("<" . "think>", "</" . "think>");
my $before_cut = length $c;
$c =~ s/^[ \t]*\Q$open\E.*?\Q$close\E\s*//gms;
$c =~ s/^[ \t]*\Q$open\E.*\z//ms;
my $cut = $before_cut - length $c;
if ($c !~ /\S/) { print STDERR "Error: HTTP $code: the reply holds no text", ($think ? ", only thinking" : ""), " — the model returned no review\n"; exit 5 }
# Keep what follows the LAST marker that ends a line and has findings-shaped text after it: a
# marker repeated at the end, or quoted in a fence after the review, must not win. Markdown
# around the marker (bold, a heading, a quote, backticks) is allowed. The marker need not start
# its line: the melious seat's model glued it to the end of its last line of reasoning (#165, round 16c), and a trace
# can restate the ask, marker and all, before that. A marker that looks quoted is skipped: one
# after other text on a finding line or right after a backtick, or one just inside a fence, so
# a finding that quotes the marker does not cut the findings above it. A cut at a marker after
# other text is said, and so is a cut when more than one marker had findings after it: a skip
# or a quote the rules miss can move the cut, and the reader then checks where the review
# starts. No usable marker: the reply is kept whole, with a warning.
my $note = "";
my $thinknote = $cut ? "(think block text dropped, " . ($cut < 1024 ? "under 1 KB" : "about " . int($cut / 1024 + 0.5) . " KB") . ($saved ? "; the full reply is in melious.full" : "") . ")\n" : "";
my $wrap = qr/[ \t>*_#\x60]*/;
my @at; while ($c =~ /\Q$mark\E$wrap\r?$/mg) { push @at, [$-[0], $+[0]] }
my $findings = qr/\b(?:BUG|RISK|NIT)\b|No BUG\/RISK\/NIT findings/;
my $usable = grep { substr($c, $_->[1]) =~ $findings } @at;
my $kept_whole = 1;
for my $m (reverse @at) {
  my ($start, $end) = @$m;
  my $after = substr($c, $end); $after =~ s/\A\r?\n//;
  next unless $after =~ $findings;
  my $ls = rindex($c, "\n", $start - 1) + 1;   # where the marker line starts
  my $lead = substr($c, $ls, $start - $ls);
  my $glued = $lead !~ /\A$wrap\z/;
  next if $glued && ($lead =~ /\A[ \t>]*(?:[-*+]|\d+[.)])?[ \t]*\**(?:BUG|RISK|NIT)\b/ || $lead =~ /\x60\z/);
  if ($ls > 0) {   # the line above opens a fence: a quote
    my $pl = rindex($c, "\n", $ls - 2) + 1;
    next if substr($c, $pl, $ls - 1 - $pl) =~ /\A[ \t>]*\x60\x60\x60/;
  }
  my $before = substr($c, 0, $end); $before =~ s/$wrap\Q$mark\E$wrap\r?$//mg;
  if ($before =~ /\S/) {
    my $kb = length($before) < 1024 ? "under 1 KB" : "about " . int(length($before) / 1024 + 0.5) . " KB";
    $note = "(text before the final-review marker dropped, $kb" . ($glued ? "; the marker ended a line of other text" : "") . ($usable > 1 ? "; the marker came $usable times with findings after it" : "") . ($glued || $usable > 1 ? ", so check that the section starts with the review" : "") . ($saved ? "; the full reply is in melious.full" : "; the full reply could not be saved") . ")\n\n";
  }
  $c = $after; $kept_whole = 0; last;
}
# A cut with nothing before it has no dropped-text note, but a skipped marker can still mean
# the reply opens with reasoning: said all the same.
$note = "(the final-review marker came $usable times with findings after it, so check that the section starts with the review)\n\n" if !$kept_whole && $note eq "" && $usable > 1;
# No usable marker: the model did not mark its final answer. Kept, and always said: a 21 KB
# reply of working notes with no marker counted as a review and carried no warning (#165,
# round 16), so size alone does not tell a leak from a short review.
if ($kept_whole) {
  my $size = length(Encode::encode("UTF-8", $c)) > 65536 ? "large " : "";   # bytes
  $note = "(no usable final-review marker: this ${size}reply may be leaked reasoning rather than a finished review; read it from the end" . ($saved ? "; the full reply is in melious.full" : "") . ")\n\n";
}
binmode STDOUT, ":encoding(UTF-8)";
print $thinknote, $note, $c; print "\n" if length $c && $c !~ /\n\z/;
if ($usage && open my $t, ">", $tok) {
  my $total = $usage->{total_tokens} // (($usage->{prompt_tokens} // 0) + ($usage->{completion_tokens} // 0));
  print $t "$total\n";
}
