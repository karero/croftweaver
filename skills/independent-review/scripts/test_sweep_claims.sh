#!/usr/bin/env bash
#
# test_sweep_claims.sh — drives sweep_claims.sh the way an author does before round 1
# (--base on a branch, --file on a plan, --worktree on uncommitted edits) against a
# throwaway repo: a branch adds known text, then main moves on, as it does in real life.
#
# Why it exists: the sweep is only worth running if it sees what a per-line grep cannot.
# A per-line grep missed a phrase wrapped across a line break; an earlier sweep silently
# dropped every sentence ending in ".)" or ".*"; the one after it dropped the start of any
# sentence with a period inside a word ("Nothing in SKILL.md changes." came out as
# "md changes."). Its first review found more ways to lose a claim: a false split at "e.g."
# or at a wrapped "2024.", a fence opened on a list line, an rst "~~~" underline read as a
# fence, a deleted qualifier, and a user's diff settings. Its second found three of those
# fixes incomplete (a wrapped "2024." inside a list item, a qualifier removed beside a new
# line, one file under two spellings) and inline code read as a fence. Its third found a
# qualifier removed beside an edit that kept its words, two ``` lines indented four spaces
# pairing up around prose, GIT_DIFF_OPTS widening hunks, a file under a relative and an
# absolute spelling, and a crash on a closed stderr or a Latin-1 locale. It also found guards
# no check could fail; the NIT close-out pinned three: a fence closer's length, a "1." item
# after a paragraph, and a Markdown "~~~" fence. Each of those is a fixture here, and case H
# proves the wrapped one really is a miss for grep: a guard that cannot fire is worse than none.
#
# Usage: bash skills/independent-review/scripts/test_sweep_claims.sh
set -u
for tool in git python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    # A zip recipient without them should not fail `make check`; the sweep itself says so and
    # exits 0 without python3, and that case is tested below whenever python3 is present.
    echo "SKIP: test_sweep_claims.sh needs $tool"
    exit 0
  fi
done
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
SCRIPT="$HERE/sweep_claims.sh"
tmp="${TMPDIR:-/tmp}"   # macOS ends TMPDIR with "/"; the sweep prints paths normalised
T="$(mktemp -d "${tmp%/}/sweep-claims-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
# Hermetic: a developer's global hooks or signing must not decide whether this passes, and
# the "not a repository" case must not find a repo above $T.
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_CEILING_DIRECTORIES="$T"
git="git -c user.name=t -c user.email=t@t -c init.defaultBranch=main -c commit.gpgsign=false -c core.hooksPath=/dev/null"
R="$T/repo"
mkdir -p "$R/docs/reviews" "$T/notrepo" "$T/nopython"

# The base, on main.
printf '# Notes\n\nThe first release never shipped to users.\n\nEvery job ran on the old runner.\nThe new runner is ready.\n' >"$R/notes.md"
printf '# History\n\nThe job never retries\nexcept on a timeout.\n\nThe old runner never ran before\n\nAll services, e.g.\nworkers.\n\nThe cache is never cleared.\nExcept on a restart.\nLogging is off.\n\nIn staging:\nthe queue is never drained.\n\nThe API never retries.\nExcept in staging.\nLogging is off.\n' >"$R/history.md"
printf '# Wrapped\n' >"$R/docs/wrapped.md"
printf 'Nothing here is kept.\n' >"$R/old.md"
printf 'echo hello\n' >"$R/tool.sh"
printf 'ignored/\n' >"$R/.gitignore"
printf 'Never once.\n\nold\n' >"$R/x[1].md"
printf 'Unless noted, retries are off.\nThe API never retries.\n' >"$R/below.md"
$git init -q "$R"; $git -C "$R" add -A; $git -C "$R" commit -qm base
$git -C "$R" checkout -qb change

# The change branch adds the text. Line numbers matter to the checks below.
# notes.md:
#   1  a changed heading, so C sits between two hunks
#   3  C: "never" in a paragraph the change does not touch
#   5  D: first sentence of an old paragraph, untouched ("Every"), beside the edit
#   6  D: its second sentence, edited ("only")
#   8-9  B: wraps AND ends ".)*", then another sentence in the same paragraph
#   13 E: a table row
#   16 F: "never" inside a fenced code block (a "#" line there is not a heading)
#   19 J: a period inside a word before the sentence's end
#   21-22 K: two list items; a sentence must not run from one into the next
#   24-25 L: a heading with a paragraph straight under it
#   27-28 M: a quoted paragraph (its ">" markers must not reach the sentence)
cat >"$R/notes.md" <<'EOF'
# Notes on the rollout

The first release never shipped to users.

Every job ran on the old runner.
The new runner is only ready for tests.

*(As of 2026-01-01, the check has not been
attempted; see Status, row 2.)* The next run is planned.

| # | Step | State | Evidence |
|---|---|---|---|
| 2 | Check | was not attempted | — |

```sh
# never run this twice
```

Nothing in SKILL.md changes.

- Alpha is fine
- Beta was not run

## Plan
Nothing is scheduled yet

> Nothing here
> is final.
EOF
# history.md: ways a claim was lost in the first review.
#   3  N: deleting "except on a timeout." widens the claim left on line 3
#   5-6 O: a wrapped line starting "2024." is not a list item; only line 6 is added
#   8-9 P: "e.g." does not end the sentence; only line 9 is edited
#   11-13 Q: a fence opened on a list line must close there, or its closer opens a fence
#         that pairs with the real one at 28-30 and swallows everything between
#   17 R: "will not" and "won't"
#   19 KNOWN WRONG: an indented code block is read as text (the reference doc says so)
#   21-22 S: "Except on a restart." removed in the same hunk that edits the next line
#   24 T: "In staging:" removed from the line above the claim
#   26 U: "Except in staging." removed in a hunk whose new line keeps its words
#   28-30 a real fence (see Q)
cat >"$R/history.md" <<'EOF'
# History

The job never retries

The old runner never ran before
2024. It ran daily after that.

All services, e.g.
workers, use the new runner.

- ```sh
  make
  ```

Only the owner can approve.

The pin will not move, and the gate won't wait.

    echo "this never runs"

The cache is never cleared.
Logging is on.

the queue is never drained.

The API never retries.
Logging in staging is enabled.

```
make
```
EOF
# A: the phrase wraps across a line break.
printf '# Wrapped\n\nThe verification step has not\nbeen attempted on any device.\n' >"$R/docs/wrapped.md"
# G: the same phrase in a review trail.
printf 'The check has not been attempted.\n' >"$R/docs/reviews/x.md"
# Not prose: swept only when named.
printf 'echo hello\n\necho "it never runs twice"\n' >"$R/tool.sh"
# An upper-case extension is still prose.
printf 'Nothing is loud.\n' >"$R/CAPS.MD"
# A name with glob characters: "x[1].md" as a glob also matches "x1.md", whose new line 1
# must not count as added in "x[1].md", where line 1 is unchanged.
printf 'Never once.\n\nnew\n' >"$R/x[1].md"
printf 'a\n' >"$R/x1.md"
# V: an edit to the line above a claim reports the claim below it.
printf 'Unless noted, retries are on.\nThe API never retries.\n' >"$R/below.md"
rm "$R/old.md"
$git -C "$R" add -A; $git -C "$R" commit -qm change
# Then main moves on and rewrites C's line. The change still has the old line, so a
# two-dot diff from main would list it as added; the three-dot diff must not.
$git -C "$R" checkout -q main
printf '# Notes\n\nThe first release shipped late.\n\nEvery job ran on the old runner.\nThe new runner is ready.\n' >"$R/notes.md"
$git -C "$R" commit -qam "main moves on"
$git -C "$R" checkout -q change

# run <name> <dir> <args...> — runs the sweep from <dir>; leaves $T/<name>.out, .err and .rc
run() {
  local name="$1" dir="$2"; shift 2
  (cd "$dir" && bash "$SCRIPT" "$@") >"$T/$name.out" 2>"$T/$name.err"
  echo $? >"$T/$name.rc"
}
fails=0
check() {   # check <description> <command ...>
  if "${@:2}"; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s\n' "$1"; fails=$((fails+1)); fi
}
line()  { grep -qxF -- "$2" "$T/$1"; }   # the whole output line, exactly
has()   { grep -qF -- "$2" "$T/$1"; }
lacks() { ! grep -qF -- "$2" "$T/$1"; }
rc_is() { [ "$(cat "$T/$1.rc")" = "$2" ]; }
count_is() { [ "$(grep -c . "$T/$1")" = "$2" ]; }

# The branch sweep: added lines only, read at the head commit.
run diff "$R" --base main
check "A: a phrase wrapped across a line break is reported, with its line range" \
  line diff.out "docs/wrapped.md:3-4 [has not, any] The verification step has not been attempted on any device."
check "B: a wrapped sentence ending '.)*' is reported and ends there" \
  line diff.out "notes.md:8-9 [has not] *(As of 2026-01-01, the check has not been attempted; see Status, row 2.)*"
check "C: an untouched paragraph is not reported, although main has since changed it" lacks diff.out "never shipped"
check "D: the edited second sentence is reported alone" \
  line diff.out "notes.md:6 [only] The new runner is only ready for tests."
check "D: so is the untouched sentence beside it: any removal marks its neighbours" \
  line diff.out "notes.md:5 [every] Every job ran on the old runner."
check "E: a table cell is reported" line diff.out "notes.md:13 [was not] was not attempted"
check "F: a fenced code block is not reported" lacks diff.out "run this twice"
check "G: a review trail is not swept by default" lacks diff.out "docs/reviews/"
check "J: a period inside a word does not cut the sentence" \
  line diff.out "notes.md:19 [nothing] Nothing in SKILL.md changes."
check "K: a list item does not run into the next" line diff.out "notes.md:22 [was not] Beta was not run"
check "L: a heading does not run into its paragraph" line diff.out "notes.md:25 [nothing] Nothing is scheduled yet"
check "M: a quoted paragraph reads as one sentence, without its markers" \
  line diff.out "notes.md:27-28 [nothing] Nothing here is final."
check "N: a deleted qualifier reports the claim it widened" line diff.out "history.md:3 [never] The job never retries"
check "O: a wrapped '2024.' does not split the claim from its edit" \
  line diff.out "history.md:5-6 [never] The old runner never ran before 2024."
check "P: 'e.g.' does not split the claim from its edit" \
  line diff.out "history.md:8-9 [all] All services, e.g. workers, use the new runner."
check "Q: a fence opened on a list line closes, so what follows is swept" \
  line diff.out "history.md:15 [only] Only the owner can approve."
check "R: future and conditional negatives are listed" \
  line diff.out "history.md:17 [will not, won't] The pin will not move, and the gate won't wait."
check "KNOWN WRONG: an indented code block is read as text" \
  line diff.out 'history.md:19 [never] echo "this never runs"'
check "S: a qualifier removed beside an edited line reports the claim it widened" \
  line diff.out "history.md:21 [never] The cache is never cleared."
check "T: a qualifier removed from the line above reports the claim below" \
  line diff.out "history.md:24 [never] the queue is never drained."
check "U: a qualifier removed beside an edit that keeps its words reports the claim" \
  line diff.out "history.md:26 [never] The API never retries."
check "V: an edit reports the claim on the line below it too" \
  line diff.out "below.md:2 [never] The API never retries."
check "an upper-case .MD file is swept" line diff.out "CAPS.MD:1 [nothing] Nothing is loud."
check "a path with glob characters is matched literally" lacks diff.out "Never once."
check "a file that is not prose is not swept by default" lacks diff.out "tool.sh"
check "a deleted file is left out, not reported as skipped" lacks diff.err "skipped"
check "nothing else is reported" count_is diff.out 20
check "the count goes to stderr" has diff.err "20 sentences to check in 7 files swept"
check "advisory: exit 0 although it listed sentences" rc_is diff 0

# H: the per-line grep this replaces cannot see fixture A, so A really discriminates.
grep_misses() { ! grep -q -- "$1" "$2"; }
check "H: grep for 'has not been' finds nothing in fixture A" grep_misses 'has not been' "$R/docs/wrapped.md"

# A user's diff settings must not change the list: run from a subdirectory, with settings that
# widen hunks (C would then sit inside one), colour the diff, make it relative to the
# subdirectory, hand it to an external diff tool that prints nothing, drop blank lines through
# a textconv filter (shifting history.md's line numbers), mark every other file binary, and
# widen hunks through GIT_DIFF_OPTS, which overrides -U0.
printf '#!/bin/sh\nexit 0\n' >"$T/extdiff"; chmod +x "$T/extdiff"
$git -C "$R" config color.diff always
$git -C "$R" config diff.interHunkContext 100
$git -C "$R" config diff.relative true
$git -C "$R" config diff.external "$T/extdiff"
$git -C "$R" config diff.squeeze.textconv "grep -v '^\$'"
mkdir -p "$R/.git/info"; printf '* -diff\nhistory.md diff=squeeze\n' >"$R/.git/info/attributes"
GIT_DIFF_OPTS=-u3 run hostile "$R/docs" --base main
for k in color.diff diff.interHunkContext diff.relative diff.external diff.squeeze.textconv; do
  $git -C "$R" config --unset "$k"
done
rm "$R/.git/info/attributes"
check "user diff settings, from a subdirectory: the same list" cmp -s "$T/diff.out" "$T/hostile.out"
check "user diff settings, from a subdirectory: the same count" has hostile.err "20 sentences to check in 7 files swept"

# PATH arguments replace the default set and are taken as given.
run named "$R" --base main tool.sh
check "a named file is swept whatever its type" line named.out 'tool.sh:3 [never] echo "it never runs twice"'
check "and only the named file" count_is named.out 1

# I: --file sweeps a whole document, touched or not.
run whole "$R" --file notes.md
check "I: --file reports the untouched paragraph" \
  line whole.out "notes.md:3 [first, never] The first release never shipped to users."
check "I: --file reports the untouched first sentence" line whole.out "notes.md:5 [every] Every job ran on the old runner."
check "I: --file still skips fenced code" lacks whole.out "run this twice"
check "I: --file reports every matching sentence" count_is whole.out 9
run both "$R" --base main --file ./notes.md
check "--base and --file on one file, spelled differently: each sentence once" count_is both.out 21
check "--base and --file on one file: counted as one file" has both.err "21 sentences to check in 7 files swept"
run bothsub "$R/docs" --base main --file ../notes.md
check "the same, from a subdirectory" count_is bothsub.out 21
run twice "$R" --file ./notes.md --file notes.md
check "--file twice under two spellings: each sentence once" count_is twice.out 9
run twiceabs "$R" --file notes.md --file "$R/notes.md"
check "--file twice, relative and absolute: each sentence once" count_is twiceabs.out 9
# A file outside the repository with the same name and text as one inside is its own file.
mkdir -p "$T/outside"; cp "$R/notes.md" "$T/outside/notes.md"
run outside "$T/outside" --repo "$R" --base main --file notes.md
check "--file outside --repo: labelled by its absolute path" \
  grep -q '^/.*/outside/notes\.md:3 \[first, never\] The first release never shipped to users\.$' "$T/outside.out"
check "--file outside --repo: not merged with the file inside" has outside.err "29 sentences to check in 8 files swept"

# "~~~" is an rst underline, not a fence; a Markdown fence that never closes, or inline code
# that starts with backticks, does not swallow what follows.
printf 'Guide\n=====\n\nUpgrades\n~~~~~~~~\n\nUpgrades are always safe.\n\nData\n~~~~\n\nThe installer never touches your data.\n\nCleanup\n~~~~~~~\n\nNothing is left behind.\n' >"$T/guide.rst"
printf 'Only this is swept.\n\n```\nNothing here is.\n' >"$T/open.md"
# (the real fence at its end would pair with a false opener and swallow the lines between)
printf '```example``` is inline code.\n\nNothing is lost.\n\nEverything was migrated, and it mustn'"'"'t move.\n\n```sh\nmake\n```\n' >"$T/inline.md"
# Two ``` lines indented four spaces are indented code, not a fence pair around the prose.
printf 'Setup:\n\n    ```\n\nNothing is cached.\n\n    ```\n\n\t```\n\nNothing is kept.\n\n\t```\n' >"$T/indented.md"
# Nor does one indented four spaces close a fence opened at the margin; one after a list marker
# may, up to three spaces past the item's text ("10. " is four wide).
printf '```\nNothing is stored.\n    ```\n' >"$T/closer.md"
printf '10. ```sh\n    it never builds\n    ```\n\nOnly this is prose.\n\n```\nmake\n```\n' >"$T/listfence.md"
# Each rule that keeps a sentence whole, on its own: "e.g." before a capital, a stop before a
# lowercase word, and a wrapped "2024." inside a list item; a sibling item still splits.
printf 'All services, e.g. Python and Go, use the new runner.\n\nEvery job ran, approx. twice a day.\n\n- The runner never ran before\n  2024. It ran daily later.\n\n1. Alpha is fine\n2. beta was not run\n' >"$T/splits.md"
# "must" gives an instruction; it is not a claim about the record.
printf 'The page must load fast.\n' >"$T/must.md"
# A "1." item may interrupt a paragraph, so the paragraph's last line does not run into it.
printf 'All of these run\n1. Nothing else does.\n' >"$T/items.md"
# A fence closes only on a marker at least its length: three backticks do not close four.
# "~~~" fences a block in Markdown, although it is an underline in rst.
printf '````md\n```\nNothing inside the long fence is swept.\n```\n````\n\nNothing after the long fence is lost.\n\n~~~\nNothing inside the tilde fence is swept.\n~~~\n\nNothing after the tilde fence is lost.\n' >"$T/fences.md"
run files "$R" --file "$T/guide.rst" --file "$T/open.md" --file "$T/splits.md" --file "$T/inline.md" \
  --file "$T/indented.md" --file "$T/closer.md" --file "$T/listfence.md" --file "$T/items.md" \
  --file "$T/fences.md" --file "$T/must.md"
check "'e.g.' before a capital does not end the sentence" \
  line files.out "$T/splits.md:1 [all] All services, e.g. Python and Go, use the new runner."
check "a stop before a lowercase word does not end the sentence" \
  line files.out "$T/splits.md:3 [every] Every job ran, approx. twice a day."
check "a wrapped '2024.' inside a list item does not split the claim" \
  line files.out "$T/splits.md:5-6 [never] The runner never ran before 2024."
check "a sibling list item still starts a new sentence" line files.out "$T/splits.md:9 [was not] beta was not run"
check "rst: the second section under a '~~~' underline is swept" has files.out "The installer never touches your data."
check "a fence that never closes does not swallow what follows" has files.out "Nothing here is."
check "inline code starting with backticks is not a fence" line files.out "$T/inline.md:3 [nothing] Nothing is lost."
check "compound universals are listed, not an instruction's 'mustn't'" \
  line files.out "$T/inline.md:5 [everything] Everything was migrated, and it mustn't move."
check "an instruction with 'must' alone is not listed" lacks files.out "must load"
check 'two ``` lines indented four spaces do not swallow the prose between' \
  line files.out "$T/indented.md:5 [nothing] Nothing is cached."
check 'nor do two tab-indented ones' line files.out "$T/indented.md:11 [nothing] Nothing is kept."
check 'a fence closer indented four spaces does not close a fence at the margin' \
  has files.out "Nothing is stored."
check 'a list-item fence closes at the item'"'"'s text column, so the prose after it is swept' \
  line files.out "$T/listfence.md:5 [only] Only this is prose."
check 'a fence opened after a list marker "10." is not reported' lacks files.out "it never builds"
check 'a "1." item does not join the paragraph above it' line files.out "$T/items.md:1 [all] All of these run"
check 'and is its own sentence' line files.out "$T/items.md:2 [nothing] Nothing else does."
check 'a ``` line does not close a ```` fence' lacks files.out "inside the long fence"
check 'the prose after the ```` fence is swept' \
  line files.out "$T/fences.md:7 [nothing] Nothing after the long fence is lost."
check 'Markdown: a "~~~" fenced block is not reported' lacks files.out "inside the tilde fence"
check 'Markdown: the prose after a "~~~" fence is swept' \
  line files.out "$T/fences.md:13 [nothing] Nothing after the tilde fence is lost."
check "--file: every matching sentence, and nothing more" count_is files.out 19

# Usage errors exit 2; nothing to sweep is not one.
run noargs "$R"
check "no --base and no --file: exit 2" rc_is noargs 2
run headwt "$R" --base main --head HEAD --worktree
check "--head with --worktree: exit 2" rc_is headwt 2
run badref "$R" --base no-such-ref
check "an unknown ref: exit 2" rc_is badref 2
check "an unknown ref: says which" has badref.err "not a commit: no-such-ref"
run notrepo "$T/notrepo" --base main
check "outside a repository: exit 2" rc_is notrepo 2
run nofile "$R" --file missing.md
check "a missing --file: exit 2" rc_is nofile 2
run dirfile "$R" --file docs
check "an unreadable --file: exit 2" rc_is dirfile 2
check "an unreadable --file: no traceback" lacks dirfile.err "Traceback"
unrelated="$($git -C "$R" commit-tree "$($git -C "$R" mktree </dev/null)" -m unrelated)"
run unrelated "$R" --base "$unrelated"
check "a base with no common ancestor: exit 2" rc_is unrelated 2
check "a base with no common ancestor: says so" has unrelated.err "no common ancestor"
$git clone -q --depth 1 --no-single-branch "file://$R" "$T/shallow"
run shallow "$T/shallow" --base origin/main
check "a shallow clone: exit 2" rc_is shallow 2
check "a shallow clone: says how to fix it" has shallow.err "git fetch --unshallow"
run same "$R" --base HEAD
check "no changed prose: exit 0" rc_is same 0
check "no changed prose: says so" has same.err "no changed"

# A reader that stops early (| head) is not an error, and leaves no traceback.
yes 'Nothing is final.' 2>/dev/null | head -n 3000 >"$T/big.md"
(cd "$R" && bash "$SCRIPT" --file "$T/big.md" 2>"$T/pipe.err" | head -n 1 >/dev/null
 echo "${PIPESTATUS[0]}" >"$T/pipe.rc")
check "a closed pipe: exit 0" rc_is pipe 0
check "a closed pipe: no traceback" lacks pipe.err "Traceback"
check "a closed pipe: the count still reaches stderr" has pipe.err "sentences to check"
(cd "$R" && bash "$SCRIPT" --file "$T/big.md" 2>&1 | head -n 1 >/dev/null
 echo "${PIPESTATUS[0]}" >"$T/pipe2.rc")
check "a closed pipe that stderr shares too (2>&1 | head): exit 0" rc_is pipe2 0

# A file name that is not UTF-8 (built with mktree: some file systems refuse such names).
N="$T/nonutf"; $git init -q "$N"
nb="$($git -C "$N" commit-tree "$($git -C "$N" mktree </dev/null)" -m base)"
blob="$(printf 'It never ran.\n' | $git -C "$N" hash-object -w --stdin)"
nt="$(printf '100644 blob %s\tcaf\351.md\n' "$blob" | $git -C "$N" mktree)"
nc="$($git -C "$N" commit-tree "$nt" -p "$nb" -m change)"
run nonutf "$N" --base "$nb" --head "$nc"
check "a file name that is not UTF-8: exit 0" rc_is nonutf 0
check "a file name that is not UTF-8: the sentence is listed" \
  env LC_ALL=C grep -qF -- ".md:1 [never] It never ran." "$T/nonutf.out"

# A locale that cannot encode a curly apostrophe does not crash the list.
printf 'It doesn\342\200\231t move.\n' >"$T/curly.md"
(cd "$R" && PYTHONIOENCODING=latin-1 bash "$SCRIPT" --file "$T/curly.md") >"$T/curly.out" 2>"$T/curly.err"
echo $? >"$T/curly.rc"
check "a Latin-1 output encoding: exit 0" rc_is curly 0
check "a Latin-1 output encoding: the sentence is listed" has curly.out "t move."

# Without python3 the skill must stay usable: one line, exit 0.
(cd "$R" && env PATH="$T/nopython" "$BASH" "$SCRIPT" --base main) >"$T/nopy.out" 2>"$T/nopy.err"
echo $? >"$T/nopy.rc"
check "no python3: exit 0" rc_is nopy 0
check "no python3: says so in one line" [ "$(grep -c python3 "$T/nopy.err")" = 1 ]
check "no python3: lists nothing" count_is nopy.out 0

# Uncommitted edits: the default reads the head commit; --worktree reads the files.
printf '\nThe rollout is never automatic.\n' >>"$R/notes.md"
printf '# Wrapped\n\nThe verification step has not\nbeen attempted on every device.\n' >"$R/docs/wrapped.md"
printf 'Only the owner can approve.\n' >"$R/draft.md"
printf 'It never ran.\n' >"$R/docs/reviews/y.md"
mkdir -p "$R/ignored"; printf 'It never ran.\n' >"$R/ignored/x.md"
run committed "$R" --base main
check "default: an uncommitted edit is not read" lacks committed.out "rollout"
check "default: an added line is read at head, not from the edited file" \
  line committed.out "docs/wrapped.md:3-4 [has not, any] The verification step has not been attempted on any device."
check "default: an untracked file is not read" lacks committed.out "draft.md"
run wt "$R" --base main --worktree
check "--worktree: an uncommitted edit is reported" line wt.out "notes.md:30 [never] The rollout is never automatic."
check "--worktree: an untracked prose file is reported" line wt.out "draft.md:1 [only] Only the owner can approve."
check "--worktree: an added line is read from the edited file" \
  line wt.out "docs/wrapped.md:3-4 [has not, every] The verification step has not been attempted on every device."
check "--worktree: an untracked review trail is not" lacks wt.out "docs/reviews/"
check "--worktree: a gitignored file is not" lacks wt.out "ignored/"
run wtsub "$R/docs" --base main --worktree
check "--worktree from a subdirectory: an untracked file above it is reported" \
  line wtsub.out "draft.md:1 [only] Only the owner can approve."

if [ $fails -ne 0 ]; then echo "$fails check(s) FAILED"; exit 1; fi
echo "all checks passed"
