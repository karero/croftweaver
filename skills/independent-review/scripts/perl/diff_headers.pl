# The base check's reader (independent_review.sh, "BASE CHECK" in its header): reads the diff under
# review on stdin and checks it against git in two steps. Headers: the mode and id of every file
# side it states must match git's own patch of the same base. Content: its text records, applied
# to the base in a throwaway index, must give the target's content (HEAD's, or the working
# tree's) for every file they name, so a diff made with -w or another option that drops lines is
# caught too. Arguments: the repository's top directory, the base commit, the HEAD commit, and 1
# to list the changed files the diff leaves out (the default base only), else 0.
# Prints tab-separated lines on stdout, one fact each:
#   target <HEAD|the working tree>   what the new sides were compared with
#   left-out <path>                  a file git's patch changes that the diff does not name
#   mismatch <path> <what>           a header that does not match; the run is refused
#   content <path>                   a file whose hunks do not give the target's content
#   refuse <why>                     a diff this check cannot read, or hunks that do not apply
#   error <why>                      git failed
# Exit 0: all matches; 1: header mismatches; 3: refused as unreadable; 4: git failed; 5: git sees
# no change from the base to HEAD or to the working tree; 6: the hunks do not apply to the base;
# 7: the hunks do not give the target's content.
# It writes only in a throwaway folder, though `git apply --cached` there may add blob objects to
# the repository's object store, as any apply does.
# Perl 5.8: this path has no Perl version check, so nothing newer may be used here.
use 5.008;
use strict;
use warnings;
use File::Temp qw(tempdir);

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

# The one name of a `diff --git` line whose two names are the same path (a mode-only change, a
# binary file, an empty file): read only where no other header line names the file. Unquoted,
# the line is split where both halves name the same path, as git apply does.
sub git_line_name {
  my ($s) = @_;
  if ($s =~ /^"/) {
    my @u = unquote($s); return undef unless @u && substr($u[0], 0, 2) eq "a/";
    my $rest = $u[1]; return undef unless $rest =~ s/^ //;
    my @v = unquote($rest); return undef unless @v && $v[1] eq "" && $v[0] eq "b/" . substr($u[0], 2);
    return substr($u[0], 2);
  }
  my $l = length($s);
  return undef unless ($l - 1) % 2 == 0;
  my $h = ($l - 1) / 2;
  my ($x, $y) = (substr($s, 0, $h), substr($s, $h + 1));
  return undef unless substr($s, $h, 1) eq " " && substr($x, 0, 2) eq "a/" && substr($y, 0, 2) eq "b/" && substr($x, 2) eq substr($y, 2);
  return substr($x, 2);
}

# Parse a patch into records { old, new, om, nm, oid, nid, ids, binary, start, end }; old or new
# is undef where the file is absent on that side, and start..end are the record's lines. Returns
# (\@records) or (undef, why).
sub parse {
  my ($lines) = @_;
  my (@recs, $cur, $hdr);
  my ($mbox, $in_msg) = (0, 0);
  my $n = scalar @$lines;
  for (my $i = 0; $i < $n; $i++) {
    my $l = $lines->[$i]; $l =~ s/\n\z//;
    return (undef, "colour codes (made with --color)") if $l =~ /\e\[[0-9;]*m/;
    if ($l =~ /^From [0-9a-f]{40} /) {
      $mbox++; return (undef, "a format-patch series (each patch's old side is the one before's new side)") if $mbox > 1;
      ($cur, $hdr, $in_msg) = (undef, 0, 1); next;
    }
    if ($in_msg) { $in_msg = 0 if $l eq "---"; next; }   # a format-patch's message, up to its "---"
    if ($l eq "-- ") { ($cur, $hdr) = (undef, 0); next; } # a format-patch's signature: the record ends
    return (undef, "a combined diff (diff --cc), which has no single old side") if $l =~ /^diff --(?:cc|combined) /;
    if ($l =~ /^diff --git (.*)\z/) {
      my $g = $1;
      return (undef, "a prefix other than a/ and b/") unless $g =~ /^"?a\// && $g =~ / "?b\//;
      $cur = { git => $g, start => $i, end => $i }; push @recs, $cur; $hdr = 1; next;
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
      $i++ while $i + 1 < $n && substr($lines->[$i + 1], 0, 1) eq "\\";
      $cur->{end} = $i;
      next;
    }
    next unless $cur && $hdr;
    $cur->{end} = $i;
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
    elsif ($l =~ /^copy (?:from|to) /) { return (undef, "a copy record (made with -C, or with diff.renames=copies set)"); }
    elsif ($l =~ /^index ([0-9a-f]+)\.\.([0-9a-f]+)(?: ([0-7]+))?\z/) {
      ($cur->{oid}, $cur->{nid}) = ($1, $2);
      $cur->{im} = $3;
      return (undef, "an id shorter than git's 4 hex digits") if length($1) < 4 || length($2) < 4;
    }
    elsif ($l =~ /^--- (.*)\z/) { my ($nm, $why) = side_name($1, "a/"); return (undef, $why) if defined $why; $cur->{minus} = $nm; }
    elsif ($l =~ /^\+\+\+ (.*)\z/) { my ($nm, $why) = side_name($1, "b/"); return (undef, $why) if defined $why; $cur->{plus} = $nm; }
    elsif ($l =~ /^(?:Binary files .* differ|GIT binary patch)\z/) { $hdr = 0; $cur->{binary} = 1; }
    else { return (undef, "a header line this check cannot read: \"" . esc($l) . "\""); }
  }
  for my $r (@recs) {
    my ($old, $new) = (defined $r->{rfrom} ? $r->{rfrom} : $r->{minus}, defined $r->{rto} ? $r->{rto} : $r->{plus});
    if (!defined $old || !defined $new) {
      my $one = git_line_name($r->{git});
      return (undef, "a diff --git line this check cannot read: \"" . esc($r->{git}) . "\"") unless defined $one;
      $old = $one unless defined $old;
      $new = $one unless defined $new;
    }
    $old = undef if $r->{created} || $old eq "";
    $new = undef if $r->{deleted} || $new eq "";
    if (defined $r->{oid}) {
      $r->{ids} = 1;
      $old = undef if $r->{oid} =~ /^0+\z/;
      $new = undef if $r->{nid} =~ /^0+\z/;
      if (defined $r->{im}) { $r->{om} = $r->{im} unless defined $r->{om}; $r->{nm} = $r->{im} unless defined $r->{nm}; }
    } elsif (!(defined $r->{rfrom} && defined $r->{rto})
             && !(defined $old && defined $new && $old eq $new && defined $r->{om} && defined $r->{nm})) {
      # Only a mode-only change and a rename with no content change have no index line.
      return (undef, "a record with no index line that is neither a mode-only change nor a pure rename (cut short?)");
    }
    return (undef, "a record with no file on either side") unless defined $old || defined $new;
    @$r{qw(old new)} = ($old, $new);
  }
  return (\@recs);
}

sub git_patch {
  my (@revs) = @_;
  my $fh;
  open($fh, "-|", "git", "-C", $top, "diff", "--no-ext-diff", "--no-color", "--no-textconv",
       "--full-index", "--no-renames", "--src-prefix=a/", "--dst-prefix=b/", @revs)
    or do { say_line("error", "could not run git diff: $!"); exit 4; };
  binmode $fh;
  my @l = <$fh>;
  close($fh) or do { say_line("error", "git diff " . join(" ", @revs) . " failed (exit " . ($? >> 8) . ")"); exit 4; };
  my ($recs, $why) = parse(\@l);
  if (!$recs) { say_line("error", "git's own patch could not be read: $why"); exit 4; }
  # By side: a type change (a file becoming a symlink) is two records for one path.
  my (%old, %new);
  for my $r (@$recs) { $old{$r->{old}} = $r if defined $r->{old}; $new{$r->{new}} = $r if defined $r->{new}; }
  return { old => \%old, new => \%new };
}

sub id7 { return defined $_[0] ? substr($_[0], 0, 7) : "none"; }
sub id_ok { my ($a, $g) = @_; return defined $g && index(lc $g, lc $a) == 0; }

# What does not match between the diff's records and git's patch (by side, by path)?
sub compare {
  my ($recs, $g, $tname) = @_;
  my ($go, $gn) = ($g->{old}, $g->{new});
  my (@bad, %aold, %anew);
  for my $r (@$recs) { $aold{$r->{old}} = 1 if defined $r->{old}; $anew{$r->{new}} = 1 if defined $r->{new}; }
  my $same = "the diff changes it, but it is the same at the base and in $tname";
  for my $r (@$recs) {
    my ($o, $n) = ($r->{old}, $r->{new});
    if (defined $o) {
      my $G = $go->{$o};
      if (!$G) { push @bad, [$o, $gn->{$o} ? "the base has no such file" : $same]; }
      else {
        push @bad, [$o, "old mode " . $r->{om} . ", the base has " . (defined $G->{om} ? $G->{om} : "none")] if defined $r->{om} && (!defined $G->{om} || $r->{om} ne $G->{om});
        push @bad, [$o, "old side " . $r->{oid} . ", the base has " . id7($G->{oid})] if $r->{ids} && !id_ok($r->{oid}, $G->{oid});
      }
    }
    if (defined $n) {
      my $G = $gn->{$n};
      if (!$G) { push @bad, [$n, $go->{$n} ? "$tname has no such file" : $same]; }
      else {
        push @bad, [$n, "new mode " . $r->{nm} . ", $tname has " . (defined $G->{nm} ? $G->{nm} : "none")] if defined $r->{nm} && (!defined $G->{nm} || $r->{nm} ne $G->{nm});
        push @bad, [$n, "new side " . $r->{nid} . ", $tname has " . id7($G->{nid})] if $r->{ids} && !id_ok($r->{nid}, $G->{nid});
      }
    }
    if (!$r->{ids} && defined $o && defined $n && $go->{$o} && $gn->{$n}) {
      my ($A, $B) = ($go->{$o}, $gn->{$n});
      if ($A == $B) { push @bad, [$n, "the diff changes only its mode, but its content changed too"] if $A->{ids}; }
      elsif (!defined $A->{oid} || !defined $B->{nid} || $A->{oid} ne $B->{nid}) {
        push @bad, [$n, "a rename with no content change, but the content in $tname differs from the base's"];
      }
    }
  }
  # A side git has that the diff leaves out, for a path the diff names.
  my %named = (%aold, %anew);
  for my $p (sort keys %named) {
    push @bad, [$p, "the diff adds it, but the base already has it"] if $go->{$p} && !$aold{$p} && $anew{$p};
    push @bad, [$p, "the diff removes or renames it, but $tname still has it"] if $gn->{$p} && !$anew{$p} && $aold{$p};
  }
  my %dup;
  return grep { !$dup{$_->[0] . "\t" . $_->[1]}++ } @bad;
}

# The content step: apply every text record of the diff to the base in a throwaway index, then
# name each file they touch whose content there differs from the target's. A binary record is
# not applied (a body made with --binary is skipped too): it only clears its old path from the
# throwaway index, so the other half of a type change applies, and its new path's content is left
# to the ids the header check matched. So no text record is ever left out of this step.
sub content {
  my ($recs, $tname) = @_;
  my @bin = grep { $_->{binary} } @$recs;
  my @text = grep { !$_->{binary} } @$recs;
  return () unless @text;
  my $dir = tempdir("ir-base.XXXXXX", TMPDIR => 1, CLEANUP => 1);
  open(my $p, ">", "$dir/text.diff") or do { say_line("error", "cannot write a temp file: $!"); exit 4; };
  binmode $p;
  print $p @art[$_->{start} .. $_->{end}] for @text;
  close($p) or do { say_line("error", "cannot write a temp file: $!"); exit 4; };
  local $ENV{GIT_INDEX_FILE} = "$dir/index";
  system("git", "-C", $top, "read-tree", $base) == 0 or do { say_line("error", "git read-tree of the base failed"); exit 4; };
  my @clear = grep { defined } map { $_->{old} } @bin;
  if (@clear) {
    open(my $u, "|-", "git", "-C", $top, "update-index", "--force-remove", "-z", "--stdin")
      or do { say_line("error", "could not run git update-index: $!"); exit 4; };
    binmode $u; print $u map { "$_\0" } @clear;
    close($u) or do { say_line("error", "git update-index failed (exit " . ($? >> 8) . ")"); exit 4; };
  }
  open(my $saved, ">&STDERR") or do { say_line("error", "cannot save stderr: $!"); exit 4; };
  open(STDERR, ">", "$dir/apply.err") or do { say_line("error", "cannot write a temp file: $!"); exit 4; };
  my $rc = system("git", "-C", $top, "apply", "--cached", "--unidiff-zero", "--whitespace=nowarn", "$dir/text.diff");
  open(STDERR, ">&", $saved) or exit 4;
  if ($rc != 0) {
    open(my $e, "<", "$dir/apply.err"); my @e = $e ? <$e> : (); chomp @e;
    say_line("refuse", esc(join("; ", grep { length } @e[0 .. ($#e < 2 ? $#e : 2)])) || "git apply failed");
    exit 6;
  }
  my @cmd = $tname eq "HEAD" ? ("diff-index", "--cached", "--name-only", "-z", $head) : ("diff", "--no-ext-diff", "--no-color", "--name-only", "-z");
  open(my $fh, "-|", "git", "-C", $top, @cmd) or do { say_line("error", "could not run git @cmd[0..1]: $!"); exit 4; };
  binmode $fh;
  local $/ = "\0";
  my %differ = map { chomp; ($_ => 1) } <$fh>;
  close($fh) or do { say_line("error", "git $cmd[0] failed (exit " . ($? >> 8) . ")"); exit 4; };
  my %binnew = map { ($_ => 1) } grep { defined } map { $_->{new} } @bin;
  my %touched = map { ($_ => 1) } grep { defined && !$binnew{$_} } map { ($_->{old}, $_->{new}) } @text;
  return grep { $differ{$_} } sort keys %touched;
}

my ($recs, $why) = parse(\@art);
if (!$recs) { say_line("refuse", $why); exit 3; }
if (!@$recs) { say_line("refuse", "no diff --git record: not a diff git made"); exit 3; }
my (%aold, %anew);
for my $r (@$recs) {
  for my $side (["old", \%aold], ["new", \%anew]) {
    my $p = $r->{$side->[0]};
    next unless defined $p;
    if ($side->[1]{$p}++) { say_line("refuse", "a file named in two records (\"" . esc($p) . "\")"); exit 3; }
  }
}

my %tried;
for my $t (["HEAD", [$base, $head]], ["the working tree", [$base]]) {
  my ($tname, $revs) = @$t;
  my $g = git_patch(@$revs);
  my @bad = compare($recs, $g, $tname);
  $tried{$tname} = [$g, \@bad];
  next if @bad;
  say_line("target", $tname);
  if (my @c = content($recs, $tname)) { say_line("content", esc($_)) for @c; exit 7; }
  if ($coverage) {
    my %named = map { ($_ => 1) } grep { defined } map { ($_->{old}, $_->{new}) } @$recs;
    my %paths = (%{$g->{old}}, %{$g->{new}});
    for my $p (sort keys %paths) { say_line("left-out", esc($p)) unless $named{$p} || $p =~ m{^docs/reviews/}; }
  }
  exit 0;
}
if (!%{$tried{"HEAD"}[0]{old}} && !%{$tried{"HEAD"}[0]{new}} && !%{$tried{"the working tree"}[0]{old}} && !%{$tried{"the working tree"}[0]{new}}) {
  say_line("refuse", "nothing to review"); exit 5;
}
my ($best) = sort { @{$tried{$a}[1]} <=> @{$tried{$b}[1]} || ($a eq "HEAD" ? -1 : 1) } keys %tried;
say_line("target", $best);
say_line("mismatch", esc($_->[0]), $_->[1]) for @{$tried{$best}[1]};
exit 1;
