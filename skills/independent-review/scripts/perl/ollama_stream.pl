# The ollama HTTP API reply reader (ollama_via_api): arguments are the response file, the HTTP code and
# the tokens file. Prints the review; errors go to stderr as "Error: HTTP <code>: ...". Exit 2: an
# error reply (not 200); 3: a stream line that is not JSON; 4: a truncated review; 6: an error
# mid-stream; 7: not a stream (the first line is not JSON: an HTML page from a proxy, say); 8: an
# empty reply; 1: the reader itself failed. ollama_via_api names each in the
# summary line.
use 5.010;
use JSON::PP;

# A die outside an eval exits with errno, which can collide with the codes above: exit 1 instead.
# $^S is undef while code compiles, as in a require inside an eval: that die is left alone.
$SIG{__DIE__} = sub { return if !defined $^S || $^S; print STDERR "ollama_stream.pl: ", @_; exit 1 };

my ($file, $code, $tok) = @ARGV;
open my $f, "<", $file or do { print STDERR "Error: HTTP $code: no response body\n"; exit($code eq "200" ? 8 : 2) };
my $json = JSON::PP->new->utf8;
my ($c, $done, $n) = ("", undef, 0);
while (my $line = <$f>) {
  next unless $line =~ /\S/;
  $n++;
  my $j = eval { $json->decode($line) };
  if (ref $j ne "HASH") {
    (my $q = $line) =~ s/[\s\x00-\x1f\x7f]+/ /g;   # keep off the /r flag: the API transports need Perl 5.10, not 5.14
    $q =~ s/^ | $//g; $q = substr($q, 0, 300);
    # A non-200 body is the error reply of the server, quoted on the line; a 200 line may be
    # review text, so it goes below, indented, where the classifier does not read.
    if ($code ne "200") { print STDERR "Error: HTTP $code: response is not JSON: $q\n" }
    elsif ($n == 1) { print STDERR "Error: HTTP $code: the reply is not a stream (its first line is not JSON)\n    line began: $q\n" }
    else { print STDERR "Error: HTTP $code: a stream line is not JSON\n    line began: $q\n" }
    exit($code ne "200" ? 2 : $n == 1 ? 7 : 3);
  }
  if (defined $j->{error}) {
    my $e = $j->{error}; $e = JSON::PP->new->encode($e) if ref $e;
    print STDERR "Error: HTTP $code: $e\n"; exit($code eq "200" ? 6 : 2);
  }
  $c .= $j->{message}{content} // "" if ref $j->{message} eq "HASH";
  $done = $j if $j->{done};
}
if ($code ne "200") { print STDERR "Error: HTTP $code: request failed\n"; exit 2 }
if (!$n) { print STDERR "Error: HTTP $code: an empty reply\n"; exit 8 }
# No chunk count in the message: a bare 429 there would read as a quota refusal (QUOTA_RE).
if (!$done) { print STDERR "Error: HTTP $code: the stream ended without its final line — a truncated review\n"; exit 4 }
binmode STDOUT, ":encoding(UTF-8)";
print $c; print "\n" if length $c && $c !~ /\n\z/;
if (defined $done->{eval_count} && open my $t, ">", $tok) {
  print $t (($done->{prompt_eval_count} // 0) + $done->{eval_count}), "\n";
}
