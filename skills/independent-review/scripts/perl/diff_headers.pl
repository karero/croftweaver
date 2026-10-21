# The base check's reader (independent_review.sh, "BASE CHECK" in its header): reads the diff under
# review on stdin and compares the mode and id of every file side it states with git's own patch of
# the same base. Arguments: the repository's top directory, the base commit, the HEAD commit, and 1
# to list the changed files the diff leaves out (the default base only), else 0.
# Prints tab-separated lines on stdout, one fact each:
#   target <HEAD|the working tree>   what the new sides were compared with
#   left-out <path>                  a file git's patch changes that the diff does not name
#   mismatch <path> <what>           a side that does not match; the run is refused
#   refuse <why>                     a diff this check cannot read; the run is refused
#   error <why>                      git failed
# Exit 0: every side matches; 1: mismatches; 3: refused as unreadable; 4: git failed; 5: there is
# nothing to review (the base is HEAD and the working tree has no change).
# Perl 5.8: this path has no Perl version check, so nothing newer may be used here.
use 5.008;
use strict;
use warnings;

my ($top, $base, $head, $coverage) = @ARGV;
binmode STDIN; binmode STDOUT;
my @art = <STDIN>;

sub say_line { print join("\t", @_), "\n"; }
sub esc { my ($s) = @_; $s =~ s/([\x00-\x1f\\])/sprintf("\\%03o", ord($1))/ge; return $s; }

# git's C quoting of a name: "a/x\ty". Returns the name and what follows it, or () if malformed.
sub unquote {
  my ($s) = @_;
  return () unless $s =~ s/^"//;
  my $out = "";
  my %e = (a => "\a", b => "\b", t => "\t", n => "\n", v => "\013", f => "\f", r => "\r", '"' => '"', '\\' => '\\');
  while (length $s) {
    my $c = substr($s, 0, 1, "");
    if ($c eq '"') { return ($out, $s); }
    if ($c ne '\\') { $out .= $c; next; }
    if ($s =~ s/^([0-7]{3})//) { $out .= chr(oct($1)); next; }
    my $d = substr($s, 0, 1, "");
    return () unless exists $e{$d};
    $out .= $e{$d};
  }
  return ();
}

# A name from a `---` or `+++` line: /dev/null, or the prefix and a path. A C-quoted name is
# unquoted first; an unquoted one loses the tab git adds after a name with a space.
sub side_name {
  my ($raw, $prefix) = @_;
  my $name;
  if ($raw =~ /^"/) { my @u = unquote($raw); return (undef, "a name this check cannot unquote") unless @u; $name = $u[0]; }
  else { $name = $raw; $name =~ s/\t\z//; }
  return ("", undef) if $name eq "/dev/null";
  return (undef, "a prefix other than a/ and b/ (\"" . esc($name) . "\")") unless substr($name, 0, 2) eq $prefix;
  return (substr($name, 2), undef);
}

# Both names of a `diff --git` line, prefixes stripped: (old, new), or (undef, why).
sub git_line_names {
  my ($s) = @_;
  my ($a, $b);
  if ($s =~ /^"/) {
    my @u = unquote($s); return (undef, "a name this check cannot unquote") unless @u;
    ($a, my $rest) = @u;
    return (undef, "an unreadable diff --git line") unless $rest =~ s/^ //;
    if ($rest =~ /^"/) { my @v = unquote($rest); return (undef, "a name this check cannot unquote") unless @v; $b = $v[0]; }
    else { $b = $rest; }
  } else {
    # Unquoted, the line is ambiguous where a name holds " b/". Split where both halves name the
    # same path, as git apply does; a rename's other names come from its own header lines.
    my $l = length($s);
    if (($l - 1) % 2 == 0) { my $h = ($l - 1) / 2; my ($x, $y) = (substr($s, 0, $h), substr($s, $h + 1)); ($a, $b) = ($x, $y) if substr($s, $h, 1) eq " " && substr($x, 2) eq substr($y, 2); }
    if (!defined $a) { return (undef, "a prefix other than a/ and b/") unless $s =~ /^a\/(.+?) b\/(.+)\z/; return ($1, $2); }
  }
  return (undef, "a prefix other than a/ and b/") unless substr($a, 0, 2) eq "a/" && substr($b, 0, 2) eq "b/";
  return (substr($a, 2), substr($b, 2));
}

# Parse a patch into records { old, new, om, nm, oid, nid, ids }; old or new is undef where the file
# is absent on that side. Returns (\@records) or (undef, why).
sub parse {
  my ($lines) = @_;
  my (@recs, $cur, $hdr);
  my $mbox = 0;
  my $n = scalar @$lines;
  for (my $i = 0; $i < $n; $i++) {
    my $l = $lines->[$i]; $l =~ s/\n\z//;
    return (undef, "colour codes (made with --color)") if $l =~ /\e\[[0-9;]*m/;
    if ($l =~ /^From [0-9a-f]{40} /) { $mbox++; return (undef, "a format-patch series (each patch's old side is the one before's new side)") if $mbox > 1; next; }
    return (undef, "a combined diff (diff --cc), which has no single old side") if $l =~ /^diff --(?:cc|combined) /;
    if ($l =~ /^diff --git (.*)\z/) {
      $cur = { git => $1 }; push @recs, $cur; $hdr = 1; next;
    }
    if ($l =~ /^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@/) {
      next unless $cur;
      $hdr = 0;
      my ($ob, $nb) = (defined $1 ? $1 : 1, defined $2 ? $2 : 1);
      # Skip the hunk by its counts. A "\ No newline at end of file" line is not in them.
      while ($ob > 0 || $nb > 0) {
        $i++;
        return (undef, "a hunk that ends before its \@\@ counts do") if $i >= $n;
        my $h = $lines->[$i]; $h =~ s/\n\z//;
        my $c = substr($h, 0, 1);
        if ($c eq "\\") { next; }
        if ($c eq " " || $h eq "") { $ob--; $nb--; }
        elsif ($c eq "-") { $ob--; }
        elsif ($c eq "+") { $nb--; }
        else { return (undef, "a hunk whose \@\@ counts do not match its lines"); }
        return (undef, "a hunk whose \@\@ counts do not match its lines") if $ob < 0 || $nb < 0;
      }
      next;
    }
    next unless $cur && $hdr;
    if    ($l =~ /^old mode ([0-7]+)\z/)          { $cur->{om} = $1; }
    elsif ($l =~ /^new mode ([0-7]+)\z/)          { $cur->{nm} = $1; }
    elsif ($l =~ /^deleted file mode ([0-7]+)\z/) { $cur->{om} = $1; $cur->{deleted} = 1; }
    elsif ($l =~ /^new file mode ([0-7]+)\z/)     { $cur->{nm} = $1; $cur->{created} = 1; }
    elsif ($l =~ /^(?:dis)?similarity index \d+%\z/) { }
    elsif ($l =~ /^rename (from|to) (.*)\z/) {
      my ($k, $v) = ($1, $2);
      if ($v =~ /^"/) { my @u = unquote($v); return (undef, "a name this check cannot unquote") unless @u; $v = $u[0]; }
      $cur->{"r$k"} = $v;
    }
    elsif ($l =~ /^copy (?:from|to) /) { return (undef, "a copy record (made with -C), which this check does not read"); }
    elsif ($l =~ /^index ([0-9a-f]+)\.\.([0-9a-f]+)(?: ([0-7]+))?\z/) {
      ($cur->{oid}, $cur->{nid}) = ($1, $2);
      $cur->{im} = $3;
      return (undef, "an id shorter than git's 4 hex digits") if length($1) < 4 || length($2) < 4;
    }
    elsif ($l =~ /^--- (.*)\z/) { my ($nm, $why) = side_name($1, "a/"); return (undef, $why) if defined $why; $cur->{minus} = $nm; }
    elsif ($l =~ /^\+\+\+ (.*)\z/) { my ($nm, $why) = side_name($1, "b/"); return (undef, $why) if defined $why; $cur->{plus} = $nm; }
    elsif ($l =~ /^(?:Binary files .* differ|GIT binary patch)\z/) { $hdr = 0; }
    else { return (undef, "a header line this check cannot read: \"" . esc($l) . "\""); }
  }
  for my $r (@recs) {
    my ($ga, $gb) = git_line_names($r->{git});
    return (undef, $gb) unless defined $ga;
    my $old = defined $r->{rfrom} ? $r->{rfrom} : defined $r->{minus} ? $r->{minus} : $ga;
    my $new = defined $r->{rto} ? $r->{rto} : defined $r->{plus} ? $r->{plus} : $gb;
    $old = undef if $r->{created} || $old eq "";
    $new = undef if $r->{deleted} || $new eq "";
    if (defined $r->{oid}) {
      $r->{ids} = 1;
      $old = undef if $r->{oid} =~ /^0+\z/;
      $new = undef if $r->{nid} =~ /^0+\z/;
      if (defined $r->{im}) { $r->{om} = $r->{im} unless defined $r->{om}; $r->{nm} = $r->{im} unless defined $r->{nm}; }
    }
    return (undef, "a record with no file on either side") unless defined $old || defined $new;
    @$r{qw(old new)} = ($old, $new);
  }
  return (\@recs);
}

sub git_patch {
  my (@revs) = @_;
  my $fh;
  open($fh, "-|", "git", "-C", $top, "diff", "--no-ext-diff", "--no-color", "--full-index",
       "--no-renames", "--src-prefix=a/", "--dst-prefix=b/", @revs)
    or do { say_line("error", "could not run git diff: $!"); exit 4; };
  binmode $fh;
  my @l = <$fh>;
  close($fh) or do { say_line("error", "git diff " . join(" ", @revs) . " failed (exit " . ($? >> 8) . ")"); exit 4; };
  my ($recs, $why) = parse(\@l);
  if (!$recs) { say_line("error", "git's own patch could not be read: $why"); exit 4; }
  my %by;
  $by{defined $_->{new} ? $_->{new} : $_->{old}} = $_ for @$recs;
  return \%by;
}

sub id7 { return defined $_[0] ? substr($_[0], 0, 7) : "none"; }
sub id_ok { my ($a, $g) = @_; return defined $g && index(lc $g, lc $a) == 0; }

# What does not match between one record of the diff and git's patch (%$g, by path)?
sub compare {
  my ($r, $g, $tname) = @_;
  my @bad;
  my ($o, $n) = ($r->{old}, $r->{new});
  my $go = defined $o ? $g->{$o} : undef;
  my $gn = defined $n ? $g->{$n} : undef;
  my $p = defined $n ? $n : $o;
  # A path git's patch does not list is the same at the base and in the target.
  for my $q (grep { defined } $o, $n) {
    return ([$q, "the diff changes it, but it is the same at the base and in $tname"]) unless $g->{$q};
  }
  if (defined $o && defined $n && $o eq $n) {
    return ([$p, "the base has no such file"]) unless defined $go->{old};
    return ([$p, "$tname has no such file"]) unless defined $go->{new};
    if ($r->{ids} xor $go->{ids}) {
      return ([$p, $r->{ids} ? "the diff changes its content, but only its mode changed" : "the diff changes only its mode, but its content changed too"]);
    }
    if ($r->{ids}) {
      push @bad, [$p, "old side " . $r->{oid} . ", the base has " . id7($go->{oid})] unless id_ok($r->{oid}, $go->{oid});
      push @bad, [$p, "new side " . $r->{nid} . ", $tname has " . id7($go->{nid})] unless id_ok($r->{nid}, $go->{nid});
    }
  } else {
    if (defined $o) {
      if (!$go || !defined $go->{old}) { push @bad, [$o, "the base has no such file"]; }
      elsif (defined $go->{new}) { push @bad, [$o, "the diff removes or renames it, but $tname still has it"]; }
      elsif ($r->{ids} && !id_ok($r->{oid}, $go->{oid})) { push @bad, [$o, "old side " . $r->{oid} . ", the base has " . id7($go->{oid})]; }
    }
    if (defined $n) {
      if (!$gn || !defined $gn->{new}) { push @bad, [$n, "$tname has no such file"]; }
      elsif (defined $gn->{old}) { push @bad, [$n, "the diff adds it, but the base already has it"]; }
      elsif ($r->{ids} && !id_ok($r->{nid}, $gn->{nid})) { push @bad, [$n, "new side " . $r->{nid} . ", $tname has " . id7($gn->{nid})]; }
    }
    if (!@bad && defined $o && defined $n && !$r->{ids} && $go->{oid} ne $gn->{nid}) {
      push @bad, [$n, "a rename with no content change, but the content in $tname differs from the base's"];
    }
  }
  return @bad if @bad;
  my $om = defined $go ? $go->{om} : undef;
  my $nm = defined $gn ? $gn->{nm} : defined $go ? $go->{nm} : undef;
  push @bad, [$p, "old mode " . $r->{om} . ", the base has " . (defined $om ? $om : "none")] if defined $o && defined $r->{om} && (!defined $om || $r->{om} ne $om);
  push @bad, [$p, "new mode " . $r->{nm} . ", $tname has " . (defined $nm ? $nm : "none")] if defined $n && defined $r->{nm} && (!defined $nm || $r->{nm} ne $nm);
  return @bad;
}

my ($recs, $why) = parse(\@art);
if (!$recs) { say_line("refuse", $why); exit 3; }
if (!@$recs) { say_line("refuse", "no diff --git record: not a diff git made"); exit 3; }
my %seen;
for my $r (@$recs) {
  my %paths = map { ($_ => 1) } grep { defined } $r->{old}, $r->{new};
  for my $p (keys %paths) {
    next unless $seen{$p}++;
    say_line("refuse", "a file named in two records (\"" . esc($p) . "\")"); exit 3;
  }
}

my %tried;
for my $t (["HEAD", [$base, $head]], ["the working tree", [$base]]) {
  my ($tname, $revs) = @$t;
  my $g = git_patch(@$revs);
  my @bad = map { compare($_, $g, $tname) } @$recs;
  $tried{$tname} = [$g, \@bad];
  next if @bad;
  say_line("target", $tname);
  if ($coverage) {
    my %named = map { ($_ => 1) } grep { defined } map { ($_->{old}, $_->{new}) } @$recs;
    for my $p (sort keys %$g) { say_line("left-out", esc($p)) unless $named{$p} || $p =~ m{^docs/reviews/}; }
  }
  exit 0;
}
if (!%{$tried{"HEAD"}[0]} && !%{$tried{"the working tree"}[0]}) { say_line("refuse", "nothing to review"); exit 5; }
my ($best) = sort { @{$tried{$a}[1]} <=> @{$tried{$b}[1]} || ($a eq "HEAD" ? -1 : 1) } keys %tried;
say_line("target", $best);
say_line("mismatch", esc($_->[0]), $_->[1]) for @{$tried{$best}[1]};
exit 1;
