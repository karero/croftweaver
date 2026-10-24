# Does the file (the argument) hold a think tag: an angle bracket, an optional slash, the word
# "think" or "thinking", with spaces or tabs allowed between them, in any case? run_melious asks
# this before it sends a prompt to a model the list marks "light": such a model was measured
# skipping the text between the tags, with the seat reporting OK (R-MELIOUS-THINK).
# Exit 0 if there is one, 1 if the file is clean, 2 if it cannot be read (one line on stderr
# says why). The caller refuses on 0 and on 2, and goes on only on 1.
# Read as raw bytes, so a malformed byte beside a tag cannot hide it. A newline between the
# bracket and the name does not count, and neither does an entity spelling of the bracket.
# A name that goes on with a dash or a dot (think-mode) does count, on purpose: a wrong refusal
# sends the round to Codex, a miss skips text without a word.
# The pattern spells the word with a bracket class, so that nothing written near it can make this
# file hold a tag: a review of it by the light model would be refused. Plain spelling would pass
# today too; the class is kept as a guard against a later edit.
use 5.008;

my $path = $ARGV[0];
defined $path or do { print STDERR "no file named\n"; exit 2 };
open my $f, '<', $path or do { print STDERR "cannot open the prompt file: $!\n"; exit 2 };
binmode $f;
local $/; my $s = <$f>;
defined $s or do { print STDERR "cannot read the prompt file: $!\n"; exit 2 };
exit(($s =~ m{<[ \t]*/?[ \t]*thi[n]k(?:ing)?(?![A-Za-z0-9_])}i) ? 0 : 1);
