#!/usr/bin/env bash
# independent_review.sh runs its Perl programs from perl/*.pl. Each file declares the Perl it needs
# (`use 5.0xx;`), and this check holds it to that with Perl::MinimumVersion (the library behind
# `perlver`): a file whose syntax needs a newer Perl than it declares fails, and so does a file
# declaring more than its path allows. The programs the HTTP API transports run (GATED) may need up
# to the version api_tools_ok probes for; the ones that run with no version check (UNGATED: the
# ollama CLI filter, readable_tail for any tier's FAILED section, the base check's diff_headers
# and run_limited, and seat_fits's utf8_valid) may need no more than 5.8.
# Every file must be in exactly one list, so a new program has to be placed. Before 2026-10-06 the
# programs were inline and guarded one construct at a time (no r-flag substitution, no `//` in the
# CLI filter); the tool checks every construct it knows.
#
# Perl::MinimumVersion knows constructs, not everything: it reads syntax, so a core module or a
# built-in's newer behaviour can slip past (it is the tool's limit, not a promise of 5.8 safety). The
# runtime tests (test_failed_tier_report.sh, sections 35 and 36) run the transports under a Perl
# that refuses the version probe; that proves the skip, not that the ungated files compile on 5.8.
#
# Always checked, with or without the module: every perl/*.pl is run by independent_review.sh, is
# listed here, and declares a version; every file the script runs or this check lists exists; and
# the script mentions perl only in the forms it is allowed (perl_lines below), so no inline program
# can come back. Without the module the version check is skipped and the run ends on a SKIP line;
# REQUIRE_PERL_MINIMUM=1 (CI) makes that a failure. Install: apt libperl-minimumversion-perl, or
# CPAN Perl::MinimumVersion.
# Scope: independent_review.sh and perl/. The repo's own checks and merge_link.sh keep their few
# lines of Perl inline, outside this check.
# It tests itself first on fixtures, each for the reason it must fail, because a guard that cannot
# fire is worse than none.
# Run: bash skills/independent-review/scripts/check_perl_minimum.sh
set -u
here="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
SCRIPT="$here/independent_review.sh"; PL="$here/perl"
GATED="ollama_request.pl ollama_stream.pl melious_key.pl melious_request.pl melious_stream.pl think_tag.pl"
UNGATED="ollama_filter.pl readable_tail.pl diff_headers.pl run_limited.pl utf8_valid.pl"
UNGATED_MAX=5.008
fails=0
fail() { echo "FAIL — $*"; fails=$((fails+1)); }

# probe_version <script>: the version api_tools_ok probes for, the ceiling for the gated programs.
# Read inside api_tools_ok only; prints nothing unless that function holds exactly one probe.
probe_version() {
  local v; v="$(sed -n '/^api_tools_ok() {/,/^}/p' "$1" | sed -n "s/^[[:space:]]*perl -e 'require \(5\.[0-9]*\)'.*/\1/p")"
  [ "$(printf '%s\n' "$v" | grep -c .)" = 1 ] && printf '%s\n' "$v"
}
# perl_lines <script>: each line, comments aside, that still mentions perl as a word (any case, so
# "$PERL" too, and a versioned perl5.34) once the allowed forms are taken out: a call
# perl "$PERL_DIR/<name>.pl", the PERL_DIR path, `command -v perl`, the two probes, and a WHY="..."
# message holding no command substitution (a $variable in it is fine).
# An allowlist, not a pattern for inline programs: -E, -e"...", a heredoc, `-I lib -e` and
# "$PERL" -e each slipped past such a pattern (round 1, fresh-eyes). A line with a trailing comment
# that names perl fails too, the safe direction.
perl_lines() {
  perl -ne '
    next if /^\s*#/;
    my $l = $_;
    $l =~ s{perl "\$PERL_DIR/[A-Za-z0-9_-]+\.pl"}{}g;
    $l =~ s{"\$SCRIPT_DIR/perl"}{}g;
    $l =~ s{command -v perl(?![A-Za-z0-9_])}{}g;
    $l =~ s{perl -e \x27require 5\.[0-9]+\x27}{}g;
    $l =~ s{perl -MJSON::PP -e 1(?![A-Za-z0-9_])}{}g;
    $l =~ s{WHY="(?:[^"\$\x60]|\$(?!\())*"}{}g;
    print "$.: $_" if $l =~ /(?<![A-Za-z0-9_])perl[0-9.]*(?![A-Za-z0-9_])/i;
  ' "$1"
}
# called_files <script>: the names the script runs as perl "$PERL_DIR/<name>.pl", comments aside.
called_files() {
  perl -ne 'next if /^\s*#/; print "$1\n" while /perl "\$PERL_DIR\/([A-Za-z0-9_-]+\.pl)"/g' "$1" | sort -u
}
# structure <script> <perl dir> <gated list> <ungated list>: prints each problem, one per line.
structure() {
  local script="$1" pl="$2" gated="$3" ungated="$4" f n called
  called=" $(called_files "$script" | tr '\n' ' ')"
  for f in "$pl"/*.pl; do
    [ -e "$f" ] || continue
    n="${f##*/}"
    case " $gated $ungated " in *" $n "*) ;; *) echo "perl/$n is in neither GATED nor UNGATED in this check: place it" ;; esac
    case "$called " in *" $n "*) ;; *) echo "perl/$n is not run by independent_review.sh (no perl \"\$PERL_DIR/$n\" outside a comment)" ;; esac
    grep -qE '^use 5\.[0-9]+;' "$f" || echo "perl/$n declares no Perl version (a line 'use 5.0xx;')"
  done
  for n in $gated; do
    case " $ungated " in *" $n "*) echo "perl/$n is in both GATED and UNGATED" ;; esac
  done
  for n in $gated $ungated; do
    [ -f "$pl/$n" ] || echo "perl/$n is listed in this check but does not exist"
  done
  for n in $called; do
    [ -f "$pl/$n" ] || echo "independent_review.sh runs perl/$n, which does not exist"
  done
  perl_lines "$script" | sed 's/^/independent_review.sh mentions perl outside the allowed forms; move a program to perl\/*.pl: line /'
}
# judge <file> <max>: prints why the file fails its minimum-version check, or nothing.
judge() {
  perl -MPerl::MinimumVersion -Mversion -e '
    my ($file, $max) = @ARGV;
    my $p = Perl::MinimumVersion->new($file) or do { print "Perl::MinimumVersion cannot parse it\n"; exit };
    my $e = $p->minimum_explicit_version;
    my $s = $p->minimum_syntax_version;
    if (!$e) { print "declares no Perl version\n"; exit }
    print "its syntax needs Perl $s, but it declares $e\n" if $s && version->parse("$s") > version->parse("$e");
    print "it declares Perl $e, above the $max its path allows\n" if version->parse("$e") > version->parse($max);
  ' "$1" "$2"
}
# expect <label> <output> <substring>: the self-test's verdict on one fixture.
expect() {
  case "$2" in *"$3"*) ;; *) fail "self-test: $1 should report \"$3\"; got: ${2:-nothing}" ;; esac
}

# --- self-test of the structure checks (no module needed) ---
T="$(mktemp -d "${TMPDIR:-/tmp}/perl-minimum.XXXXXX")" || { echo "FAIL — mktemp"; exit 1; }
trap 'rm -rf "$T"' EXIT
printf 'api_tools_ok() {\n  perl -e '\''require 5.010'\'' 2>/dev/null || x\n}\n  perl -e '\''require 5.020'\'' || elsewhere\n' >"$T/probe1.sh"
printf 'api_tools_ok() {\n  echo none\n}\n' >"$T/probe0.sh"
printf 'api_tools_ok() {\n  perl -e '\''require 5.010'\'' || x\n  perl -e '\''require 5.014'\'' || y\n}\n' >"$T/probe2.sh"
[ "$(probe_version "$T/probe1.sh")" = 5.010 ] || fail "self-test: probe_version misses the one probe"
[ -z "$(probe_version "$T/probe0.sh")" ] || fail "self-test: probe_version invents a probe"
[ -z "$(probe_version "$T/probe2.sh")" ] || fail "self-test: probe_version accepts two probes"
while IFS= read -r l; do
  printf '%s\n' "$l" >"$T/line.sh"
  [ -z "$(perl_lines "$T/line.sh")" ] || fail "self-test: perl_lines rejects an allowed line: $l"
done <<'EOF'
  perl "$PERL_DIR/a_b.pl" "$x" >"$y" 2>>"$z"; prc=$?
  perl "$PERL_DIR/a-b.pl" || { WHY="perl exit $? on $PERL_DIR"; return 1; }
  printf '%s' "$p" | perl "$PERL_DIR/b.pl" "$m" >"$body" || { WHY="could not build the API request"; return 1; }
PERL_DIR="$SCRIPT_DIR/perl"
  command -v perl >/dev/null 2>&1 || { WHY="perl not found"; return 1; }
  perl -e 'require 5.010' 2>/dev/null || { WHY="Perl 5.10 or newer not found"; return 1; }
  perl -MJSON::PP -e 1 2>/dev/null || { WHY="Perl module JSON::PP not found"; return 1; }
  # perl -e 'print 1' in a whole-line comment
EOF
while IFS= read -r l; do
  printf '%s\n' "$l" >"$T/line.sh"
  [ -n "$(perl_lines "$T/line.sh")" ] || fail "self-test: perl_lines passes an inline program: $l"
done <<'EOF'
perl -E 'say 1'
perl -e"print 1"
perl <<'X'
perl - <<X
perl -I lib -e 1
"$PERL" -e 1
perl '-e' 1
perl -0777 -ne 'print'
x | perl -MJSON::PP -e 'print 1'
WHY="$(perl -e 1)"
perl "$PERL_DIR/a.pl"; perl -e 1
perl other.pl
perl5.34 -e 1
WHY="`perl -e 1`"
perl -e 'require 5.010' && perl -e 'print 1'
EOF
mkdir -p "$T/pl" "$T/okpl"
printf 'use 5.008;\n1;\n' >"$T/pl/a.pl"; printf '1;\n' >"$T/pl/b.pl"; printf 'use 5.008;\n1;\n' >"$T/pl/stray.pl"
printf '  perl "$PERL_DIR/a.pl"\n  perl "$PERL_DIR/b.pl"\n  perl "$PERL_DIR/gone.pl"\n  # perl "$PERL_DIR/stray.pl"\n' >"$T/script.sh"
out="$(structure "$T/script.sh" "$T/pl" "a.pl b.pl listed.pl" "b.pl")"
expect "an unlisted file" "$out" "perl/stray.pl is in neither GATED nor UNGATED"
expect "a file named only in a comment" "$out" "perl/stray.pl is not run by independent_review.sh"
expect "a file without a version line" "$out" "perl/b.pl declares no Perl version"
expect "a file in both lists" "$out" "perl/b.pl is in both GATED and UNGATED"
expect "a listed file that is gone" "$out" "perl/listed.pl is listed in this check but does not exist"
expect "a run file that is gone" "$out" "runs perl/gone.pl, which does not exist"
printf 'use 5.008;\n1;\n' >"$T/okpl/a.pl"; printf 'use 5.008;\n1;\n' >"$T/okpl/a-b.pl"
printf '  perl "$PERL_DIR/a.pl"\n  perl "$PERL_DIR/a-b.pl"\n' >"$T/okscript.sh"
out="$(structure "$T/okscript.sh" "$T/okpl" "a.pl a-b.pl" "")"
[ -z "$out" ] || fail "self-test: structure fails a sound layout: $out"

# --- the real files ---
GATED_MAX="$(probe_version "$SCRIPT")"
[ -n "$GATED_MAX" ] || { echo "FAIL — cannot read the one Perl version probe (perl -e 'require 5.0xx') in $SCRIPT"; exit 1; }
while IFS= read -r problem; do
  [ -z "$problem" ] || fail "$problem"
done <<EOF
$(structure "$SCRIPT" "$PL" "$GATED" "$UNGATED")
EOF

# --- minimum versions (Perl::MinimumVersion) ---
skipped=0
if ! perl -MPerl::MinimumVersion -e 1 2>/dev/null; then
  if [ "${REQUIRE_PERL_MINIMUM:-}" = 1 ]; then
    fail "Perl::MinimumVersion is not installed and REQUIRE_PERL_MINIMUM=1 (apt libperl-minimumversion-perl, or CPAN)"
  else
    skipped=1
  fi
else
  printf 'use 5.008;\nmy $x = $y // 0;\n' >"$T/dor.pl"
  printf 'use 5.010;\nmy $x = $y =~ s/a/b/r;\n' >"$T/rflag.pl"
  printf 'my $x = 1;\n' >"$T/noversion.pl"
  printf 'use 5.014;\nmy $x = 1;\n' >"$T/toohigh.pl"
  printf 'use 5.008;\nmy $x = defined $y ? $y : 0;\n' >"$T/plain.pl"
  expect "a // under use 5.008" "$(judge "$T/dor.pl" 5.008)" "its syntax needs Perl 5.010"
  expect "an r-flag substitution under use 5.010" "$(judge "$T/rflag.pl" 5.010)" "its syntax needs Perl 5.013"
  expect "a file without a version line" "$(judge "$T/noversion.pl" 5.010)" "declares no Perl version"
  expect "a version above the ceiling" "$(judge "$T/toohigh.pl" 5.010)" "above the 5.010 its path allows"
  why="$(judge "$T/plain.pl" 5.008)"
  [ -z "$why" ] || fail "self-test: the check fails the plain fixture: $why"
  for n in $GATED $UNGATED; do
    [ -f "$PL/$n" ] || continue   # reported above as listed but missing
    max="$GATED_MAX"; case " $UNGATED " in *" $n "*) max="$UNGATED_MAX" ;; esac
    why="$(judge "$PL/$n" "$max")"
    [ -z "$why" ] || fail "perl/$n: $why"
  done
fi

if [ $fails -ne 0 ]; then echo "$fails Perl minimum-version problem(s)"; exit 1; fi
if [ $skipped = 1 ]; then
  echo "SKIP — perl/*.pl: every program is run and declares its Perl, but Perl::MinimumVersion is not installed (apt libperl-minimumversion-perl, or CPAN), so their minimum Perl was NOT checked. CI checks it."
else
  echo "OK — perl/*.pl: every program is run and declares its Perl; each needs no more than it declares (gated ≤ $GATED_MAX, ungated ≤ $UNGATED_MAX)."
fi
