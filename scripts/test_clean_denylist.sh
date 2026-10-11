#!/usr/bin/env bash
#
# test_clean_denylist.sh — drives scripts/check_clean.sh's private-name check against a
# throwaway repo with a linked worktree.
#
# Why it exists: the name list is a gitignored file in the main checkout, so a linked
# worktree has no copy of it, and the check skipped itself there and still printed OK.
# Commits are made in worktrees, so the check was off exactly where it mattered: a client
# name reached main that way (2026-09-27). These cases pin that a worktree uses the main
# checkout's list, that a copy with no git still skips (and says so, on its OK line too),
# that CI's masked mode (CLEAN_MASK_NAMES=1) fails on a name without printing it,
# that scripts/ is scanned for names without the list matching itself, and that this repo's
# own short name in an issue or PR reference is not a leak, under the name it has now and
# under the one it had before the rename. The names are made up; the real list never
# appears in this repo.
#
# Usage: bash scripts/test_clean_denylist.sh
set -u
if ! command -v git >/dev/null 2>&1; then
  echo "SKIP: test_clean_denylist.sh needs git (it builds a throwaway repo and worktree)"
  exit 0
fi
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
T="$(mktemp -d "${TMPDIR:-/tmp}/clean-denylist-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git="git -c user.name=t -c user.email=t@t -c init.defaultBranch=main -c commit.gpgsign=false -c core.hooksPath=/dev/null"
fails=0
# expect <label> <exit code wanted> <text the output must contain, or ""> <dir> [VAR=value] [VAR=value]
expect() {
  local out rc
  out="$(cd "$4" && env ${5:+"$5"} ${6:+"$6"} bash scripts/check_clean.sh 2>&1)"; rc=$?
  if [ "$rc" -eq "$2" ] && { [ -z "$3" ] || printf '%s' "$out" | grep -qF -- "$3"; }; then
    printf 'ok   %s\n' "$1"
  else
    printf 'FAIL %s (exit %s, wanted %s)\n%s\n' "$1" "$rc" "$2" "$out" | sed '2,$s/^/     /'
    fails=$((fails+1))
  fi
}

R="$T/repo"; W="$T/worktree"; N="$T/nogit"
mkdir -p "$R/scripts" "$R/skills" "$R/docs"
cp "$HERE/check_clean.sh" "$R/scripts/"
for f in README.md THIRD-PARTY-LICENSES.md SECURITY.md Makefile LICENSE; do : >"$R/$f"; done
printf 'plain notes\n' >"$R/docs/notes.md"
printf '# a skill\n' >"$R/skills/SKILL.md"
printf 'scripts/.clean-denylist\n' >"$R/.gitignore"
$git init -q "$R"; $git -C "$R" add -A; $git -C "$R" commit -qm base
printf '# made-up names\nzorblequux\nkarero\n' >"$R/scripts/.clean-denylist"
$git -C "$R" worktree add -q --detach "$W"

# The list itself sits in the scanned scripts/ folder and holds every name; it must not
# report itself.
expect "main checkout, clean: passes, and says names were checked" 0 "OK — no private names in:" "$R"
expect "worktree, clean: passes without skipping the list" 0 "OK — no private names in:" "$W"
if (cd "$W" && bash scripts/check_clean.sh 2>&1) | grep -q 'denylist skipped'; then
  printf 'FAIL worktree still reports the list as skipped\n'; fails=$((fails+1))
fi

printf 'ran the live check on zorblequux\n' >>"$W/docs/notes.md"
expect "worktree, a listed name: fails" 1 "zorblequux" "$W"

# Scripts ship in the handoff zip, and a client name once sat unnoticed in a script's
# comment because the name check skipped scripts/ along with the generic checks.
printf '#!/usr/bin/env bash\n# first tried on the zorblequux site\n' >"$R/scripts/tool.sh"
expect "a listed name in a scripts/*.sh comment: fails" 1 "scripts/tool.sh" "$R"
rm "$R/scripts/tool.sh"

# In the main checkout, where the list is read either way, so only the self-reference
# allowance decides these cases.
# The org name is split so this file, which the real check scans, holds no bare copy of it.
org="kar""ero"
# Each name the repo has had: what it is called now, and what docs/reviews/ still links to.
for repo in croftweaver website-builder; do
  printf 'fixed in %s/%s#131\nsee https://github.com/%s/%s.\ngit clone https://github.com/%s/%s.git\n%s/%s %s/%s,%s/%s\n' \
    "$org" "$repo" "$org" "$repo" "$org" "$repo" "$org" "$repo" "$org" "$repo" "$org" "$repo" >"$R/docs/notes.md"
  expect "$repo, this repo's name in a reference: passes" 0 "OK —" "$R"
  printf 'ran zorblequux; fixed in %s/%s#131\n' "$org" "$repo" >"$R/docs/notes.md"
  expect "$repo, a listed name beside a self-reference: still fails" 1 "zorblequux" "$R"
  printf 'see %s/%s-private\n' "$org" "$repo" >"$R/docs/notes.md"
  expect "$repo, a longer name that starts like this repo: fails" 1 "$repo-private" "$R"
  printf 'see other-%s/%s\n' "$org" "$repo" >"$R/docs/notes.md"
  expect "$repo, a longer name that ends like this repo: fails" 1 "other-$org" "$R"
  printf 'see %s/%s..private\n' "$org" "$repo" >"$R/docs/notes.md"
  expect "$repo, a longer name joined by two dots: fails" 1 "$repo..private" "$R"
  # The character after a reference must survive the blanking: without it the next word runs
  # into SELF-REPO and the listed name after it is no longer a word of its own.
  printf 'see %s/%s zorblequux\n' "$org" "$repo" >"$R/docs/notes.md"
  expect "$repo, a listed name right after a self-reference: still fails" 1 "zorblequux" "$R"
done
printf 'plain notes\n' >"$R/docs/notes.md"
# GNU grep (CI's) reports a matching binary file on stderr, which the check used to discard.
printf 'ran zorblequux\0\n' >"$R/docs/blob.bin"
expect "a listed name in a binary file: fails" 1 "blob.bin" "$R"
rm "$R/docs/blob.bin"
# A newline in the file name splits GNU grep's message over two lines, and here the part
# after it names the gitignored list, which the filter would drop.
mkdir "$R/docs/nl"$'\n'"scripts"; printf 'ran zorblequux\0\n' >"$R/docs/nl"$'\n'"scripts/.clean-denylist"
expect "a listed name in a binary file with a newline in its path: fails" 1 "personal/site identifier" "$R"
rm -r "$R/docs/nl"$'\n'"scripts"
# A file name holding a newline is refused: here the part after the newline names the list,
# whose own lines are dropped, so the hit inside passed unseen.
mkdir "$R/docs/a"$'\n'"scripts"; printf 'ran zorblequux\n' >"$R/docs/a"$'\n'"scripts/.clean-denylist"
expect "a file name holding a newline: refused" 1 "file names holding a newline" "$R"
rm -r "$R/docs/a"$'\n'"scripts"
# The email and assignment exemptions match a hit's text, not its file name: a binary file's
# hit is its name alone, and these names hold "example".
printf 'mail bob@realmail.de\0\n' >"$R/docs/example.com.bin"
expect "an email in a binary file named like an exemption: fails" 1 "✗ email address" "$R"
rm "$R/docs/example.com.bin"
printf 'api_key = "abcdefghijkl"\0\n' >"$R/docs/example.bin"
expect "an assignment in a binary file named like an exemption: fails" 1 "secret-looking assignment" "$R"
rm "$R/docs/example.bin"
# An entry anchored with ^ found its lines but never reported them; it is refused, grouped
# or not, while a ^ that negates a class is fine.
cp "$R/scripts/.clean-denylist" "$T/list.pre"
printf '^zorblequux\n' >"$R/scripts/.clean-denylist"; printf 'zorblequux leads this line\n' >"$R/docs/notes.md"
expect "an entry anchored with ^: refused" 1 "holding ^" "$R"
printf '(^zorblequux)\n' >"$R/scripts/.clean-denylist"
expect "an entry anchored with ^, in a group: refused" 1 "holding ^" "$R"
printf 'zorble[^x]uux\n' >"$R/scripts/.clean-denylist"
expect "an entry with a negated class: not refused, and finds its name" 1 "personal/site identifier" "$R"
if (cd "$R" && bash scripts/check_clean.sh 2>&1) | grep -q "holding ^"; then
  printf 'FAIL a negated class was refused as an anchor\n'; fails=$((fails+1))
fi
cp "$T/list.pre" "$R/scripts/.clean-denylist"; printf 'plain notes\n' >"$R/docs/notes.md"
# In the C locale, \b can miss a name that starts or ends with a non-ASCII letter, with a
# space beside it for one (GNU grep and this Mac's grep alike).
printf 'zorbleqé\nÖzorbleq\n' >"$R/scripts/.clean-denylist"
printf 'met Zorbleqé.\n' >"$R/docs/notes.md"
expect "a name ending in a non-ASCII letter: fails" 1 "personal/site identifier" "$R"
printf 'see Özorbleq now\n' >"$R/docs/notes.md"
expect "a name starting with a non-ASCII letter: fails" 1 "personal/site identifier" "$R"
# The new edges alone missed an entry that starts or ends with punctuation next to a letter,
# which \b found; both are tried. A name with ASCII letters at both ends, inside a longer
# word, still passes.
printf -- '-zorbleq\nflumm-\n' >"$R/scripts/.clean-denylist"
printf 'see acme-zorbleq\n' >"$R/docs/notes.md"
expect "an entry starting with punctuation, after a letter: fails" 1 "personal/site identifier" "$R"
printf 'the flumm-site\n' >"$R/docs/notes.md"
expect "an entry ending with punctuation, before a letter: fails" 1 "personal/site identifier" "$R"
printf 'zorbleq\n' >"$R/scripts/.clean-denylist"; printf 'zorbleqs and zorbleqx\n' >"$R/docs/notes.md"
expect "a name inside a longer word: passes" 0 "OK — no private names in:" "$R"
cp "$T/list.pre" "$R/scripts/.clean-denylist"; printf 'plain notes\n' >"$R/docs/notes.md"
# A file name holding ":<digit>…:" moved the text's start into the name, where an exemption
# then dropped a real hit; such names are refused.
mkdir "$R/docs/a:1:example.com"; printf 'write to bob@realmail.de\n' >"$R/docs/a:1:example.com/x.md"
expect "a file name holding a colon, a digit and later another colon: refused" 1 "a colon, a digit and later another colon" "$R"
rm -r "$R/docs/a:1:example.com"
# If find fails, the names were not checked.
mkdir -p "$T/badfind"; printf '#!/bin/sh\nexit 2\n' >"$T/badfind/find"; chmod +x "$T/badfind/find"
expect "find failing: a scan error" 1 "find failed" "$R" "PATH=$T/badfind:$PATH"
# If sed fails in the name filter, its hits are lost: a scan error instead.
mkdir -p "$T/badsed"
printf '#!/bin/sh\nfor a in "$@"; do case "$a" in *SELF-REPO*) exit 4 ;; esac; done\nexec "%s" "$@"\n' "$(command -v sed)" >"$T/badsed/sed"
chmod +x "$T/badsed/sed"; printf 'ran zorblequux\n' >"$R/docs/notes.md"
expect "the name filter's sed failing: a scan error, not lost hits" 1 "the name filter failed" "$R" "PATH=$T/badsed:$PATH"
printf 'plain notes\n' >"$R/docs/notes.md"
# A filter grep that fails dropped every hit it was meant to filter. This grep fails when one
# of its arguments holds FAILPAT; each filter in turn. (Which scan error is printed depends
# on whether the stage writing into it dies of the closed pipe first; either fails the run.)
mkdir -p "$T/badfilter"
printf '#!/bin/sh\nfor a in "$@"; do case "$a" in *"$FAILPAT"*) exit 2 ;; esac; done\nexec "%s" "$@"\n' "$(command -v grep)" >"$T/badfilter/grep"
chmod +x "$T/badfilter/grep"; printf 'ran zorblequux\n' >"$R/docs/notes.md"
for f in "|^Binary file |" 'clean-denylist:[0-9]' '@(example' '(placeholder'; do
  expect "a filter grep that fails ($f): a scan error, not lost hits" 1 "scan error" "$R" "PATH=$T/badfilter:$PATH" "FAILPAT=$f"
done
printf 'plain notes\n' >"$R/docs/notes.md"
# With nowhere to put grep's errors, grep never ran, and every scan read as clean.
mkdir -p "$T/nomktemp"; printf '#!/bin/sh\nexit 1\n' >"$T/nomktemp/mktemp"; chmod +x "$T/nomktemp/mktemp"
expect "no temporary file for grep's errors: fails as a scan error" 1 "mktemp failed" "$R" "PATH=$T/nomktemp:$PATH"
printf 'ran zorblequux\n' >"$R/docs/notes:old.md"
expect "a listed name in a file whose name holds a colon: fails" 1 "zorblequux" "$R"
rm "$R/docs/notes:old.md"
# Hits in gitignored files are dropped; a file whose name only starts like an ignored path
# is not ignored, and was dropped too when the name was cut at its first colon.
printf 'docs/scratch\n' >>"$R/.gitignore"
printf 'ran zorblequux\n' >"$R/docs/scratch"
expect "a listed name in a gitignored file: passes" 0 "OK —" "$R"
printf 'ran zorblequux\n' >"$R/docs/scratch:notes.md"
expect "a listed name in a file named like an ignored path plus a colon: fails" 1 "scratch:notes.md" "$R"
rm "$R/docs/scratch" "$R/docs/scratch:notes.md"
# A pattern grep cannot compile is a scan error, which must fail the run, not read as clean.
cp "$R/scripts/.clean-denylist" "$T/list.bak"; printf 'zorble(\n' >>"$R/scripts/.clean-denylist"
expect "a broken pattern in the list: fails as a scan error" 1 "scan error" "$R"
# A list of nothing but comments checks no names, so it must not earn the names-checked OK.
printf '# no names yet\n' >"$R/scripts/.clean-denylist"
expect "a list with no names: the OK line says so" 0 "private-name check SKIPPED: scripts/.clean-denylist lists no names" "$R"
cp "$T/list.bak" "$R/scripts/.clean-denylist"

# CI runs with CLEAN_MASK_NAMES=1 and its logs are public: a hit must still fail the run,
# and nothing scanned may be printed, only counts. No listed name may appear, in any case,
# in a hit, a file name, another report or a grep error.
# masked <label> <exit code wanted> <text the output must contain>
masked() {
  local out rc
  out="$(cd "$R" && CLEAN_MASK_NAMES=1 bash scripts/check_clean.sh 2>&1)"; rc=$?
  if [ "$rc" -eq "$2" ] && printf '%s' "$out" | grep -qF -- "$3" && ! printf '%s' "$out" | grep -qi zorblequux \
     && ! printf '%s' "$out" | grep -q '^    [^(]'; then
    printf 'ok   %s\n' "$1"
  else
    printf 'FAIL %s (exit %s, wanted %s)\n%s\n' "$1" "$rc" "$2" "$out" | sed '2,$s/^/     /'
    fails=$((fails+1))
  fi
}
printf 'ran ZorbleQuux and zorblequux\nand zorblequux again\n' >"$R/docs/notes.md"
masked "masked: a listed name fails, and only a count is printed" 1 "    (2 line(s) withheld"
printf 'plain notes\n' >"$R/docs/notes.md"
# A name in a file name, inside a word, in an email or a home path: other reports print
# their lines too, and each of these leaked when only the name report was masked.
printf 'met zorblequux and the zorblequux_team\nwrite to bob@zorblequux.de\nsee /Users/zorblequux/x\n' >"$R/docs/zorblequux_notes.md"
masked "masked: names in file names, emails and home paths: not printed" 1 "✗ email address"
rm "$R/docs/zorblequux_notes.md"
# Withholding happens after the inner run filtered gitignored files by their real names.
printf 'docs/*-scratch\n' >>"$R/.gitignore"; printf 'ran zorblequux\n' >"$R/docs/zorblequux-scratch"
masked "masked: a listed name in a gitignored file named after it: passes" 0 "OK — no private names in:"
rm "$R/docs/zorblequux-scratch"
printf 'ignored\n' >"$R/docs/scratch"; printf 'ran zorblequux\n' >"$R/docs/scratch:zorblequux.md"
masked "masked: a file named like an ignored path plus a colon and a name: still fails" 1 "personal/site identifier"
rm "$R/docs/scratch" "$R/docs/scratch:zorblequux.md"
# grep's own errors name files, and are withheld like hits.
mkdir "$R/docs/zorblequux-locked"; printf 'x\n' >"$R/docs/zorblequux-locked/a.md"; chmod 000 "$R/docs/zorblequux-locked"
if [ -r "$R/docs/zorblequux-locked" ]; then
  echo "SKIP: masked scan-error case needs a directory this user cannot read (running as root?)"
else
  masked "masked: a grep error naming a file: withheld, and fails" 1 "✗ home path:"
fi
chmod 755 "$R/docs/zorblequux-locked"; rm -r "$R/docs/zorblequux-locked"
# The script's own lines read the same whatever the list holds, and are printed as they are.
printf 'dent\nriva\nmakefil\n' >>"$R/scripts/.clean-denylist"   # inside, and at the start of, its words
masked "masked: entries inside the script's own words leave them alone, and pass" 0 "no contact info or credentials in:"
cp "$T/list.bak" "$R/scripts/.clean-denylist"
# Masked mode prints no scanned text even without a list (an email here).
mv "$R/scripts/.clean-denylist" "$T/list.away"; printf 'write to bob@realmail.de\n' >"$R/docs/notes.md"
masked "masked, no list: generic hits are withheld too" 1 "✗ email address"
mv "$T/list.away" "$R/scripts/.clean-denylist"; printf 'plain notes\n' >"$R/docs/notes.md"
# A list that does not compile is named as the cause, not a name in the output.
cp "$R/scripts/.clean-denylist" "$T/list.pre2"; printf 'zorble(\n' >>"$R/scripts/.clean-denylist"
masked "masked: a list that does not compile: withheld, and says why" 1 "does not compile"
# The same with a long output: grep dies on the pattern unread, and printf dies of SIGPIPE.
awk 'BEGIN { for (i = 0; i < 3000; i++) printf "mail bob%d@realmail.de about the plan for this week\n", i }' >"$R/docs/many.md"
masked "masked: a list that does not compile, long output: says why" 1 "does not compile"
rm "$R/docs/many.md"
cp "$T/list.pre2" "$R/scripts/.clean-denylist"
# The masked check's \b alternative: an entry ending in punctuation, in a report header right
# before a letter ("✗ personal/site identifier:"), where only \b sees it. (The entry also hits
# the scanned script, so the inner run fails either way; what this pins is the header.)
printf 'personal/\n' >>"$R/scripts/.clean-denylist"
masked "masked: a punctuation-edged name in a report header: withheld" 1 "output is withheld"
if (cd "$R" && CLEAN_MASK_NAMES=1 bash scripts/check_clean.sh 2>&1) | grep -qF "personal/site"; then
  printf 'FAIL masked mode printed a report header holding a listed name\n'; fails=$((fails+1))
fi
cp "$T/list.bak" "$R/scripts/.clean-denylist"
# They never hold a whole listed name; if one ever does, nothing is printed.
printf 'skills\n' >>"$R/scripts/.clean-denylist"
masked "masked: a whole name in a line that is not scan output: withheld" 1 "output is withheld"
cp "$T/list.bak" "$R/scripts/.clean-denylist"

# A main checkout whose git data lives elsewhere (--separate-git-dir): git records no path to
# that checkout (it names the git folder instead), so the list cannot be found from a linked
# worktree. What matters is that the check never gives a bare OK: it finds the name (should
# git ever record that path) or says it skipped the list.
S="$T/sep"; SW="$T/sep-worktree"
mkdir -p "$S/scripts" "$S/skills" "$S/docs"
cp "$R/scripts/check_clean.sh" "$R/.gitignore" "$S/scripts/" 2>/dev/null; mv "$S/scripts/.gitignore" "$S/"
for f in README.md THIRD-PARTY-LICENSES.md SECURITY.md Makefile LICENSE; do : >"$S/$f"; done
printf '# a skill\n' >"$S/skills/SKILL.md"; printf 'plain notes\n' >"$S/docs/notes.md"
$git init -q --separate-git-dir "$T/sep.git" "$S"; $git -C "$S" add -A; $git -C "$S" commit -qm base
printf 'zorblequux\n' >"$S/scripts/.clean-denylist"
$git -C "$S" worktree add -q --detach "$SW"
printf 'ran the live check on zorblequux\n' >>"$SW/docs/notes.md"
out="$(cd "$SW" && bash scripts/check_clean.sh 2>&1)"; rc=$?
if { [ "$rc" -eq 1 ] && printf '%s' "$out" | grep -qF zorblequux; } ||
   { [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -qF 'denylist skipped'; }; then
  printf 'ok   worktree of a --separate-git-dir checkout: finds the name or says it skipped\n'
else
  printf 'FAIL worktree of a --separate-git-dir checkout: a bare OK (exit %s)\n' "$rc"; fails=$((fails+1))
fi

# `make push-denylist` copies the list into the CLEAN_DENYLIST secret, through a fake gh that
# records what it was asked to send. It refuses a list CI would fail on or could not mask.
if command -v make >/dev/null 2>&1; then
  cp "$HERE/../Makefile" "$R/Makefile"; cp "$HERE/../Makefile" "$W/Makefile"
  mkdir -p "$T/fakegh"; cat >"$T/fakegh/gh" <<FAKE
#!/bin/sh
case "\$1 \$2" in
  "repo view") echo owner/repo ;;
  "secret set") { echo "args: \$*"; cat; } >"$T/gh.log" ;;
esac
FAKE
  chmod +x "$T/fakegh/gh"
  push() { # <label> <dir> <exit code wanted (make exits 2 when the recipe fails)> <text the output or the gh log must contain>
    local out rc; rm -f "$T/gh.log"
    out="$(cd "$2" && PATH="$T/fakegh:$PATH" make -s push-denylist 2>&1)"; rc=$?
    if [ "$rc" -eq "$3" ] && { printf '%s' "$out"; cat "$T/gh.log" 2>/dev/null || :; } | grep -qF -- "$4"; then
      printf 'ok   %s\n' "$1"
    else
      printf 'FAIL %s (exit %s, wanted %s)\n%s\n' "$1" "$rc" "$3" "$out" | sed '2,$s/^/     /'; fails=$((fails+1))
    fi
  }
  push "push-denylist: sends the list to the repo gh names" "$R" 0 "args: secret set CLEAN_DENYLIST --repo owner/repo"
  names="$(LC_ALL=C tr -d '\r' <"$R/scripts/.clean-denylist" | LC_ALL=C grep -vE '^[[:space:]]*(#|$)')"
  if [ "$(sed -n '2p' "$T/gh.log" 2>/dev/null | base64 --decode)" != "$(printf '# CLEAN_DENYLIST v1\n%s\n' "$names")" ]; then
    printf 'FAIL push-denylist: the secret is not the marker and the names, base64-encoded\n'; fails=$((fails+1))
  fi
  # It keeps the checksum of what it sent; the check fails once the list changes after that,
  # since CI would still check the old one.
  if [ "$(cat "$R/scripts/.clean-denylist.pushed" 2>/dev/null)" != "$(printf '%s\n' "$names" | cksum)" ]; then
    printf 'FAIL push-denylist: no checksum of the list it sent\n'; fails=$((fails+1))
  fi
  expect "the list as pushed: passes, with no reminder" 0 "OK — no private names in:" "$R"
  if (cd "$R" && bash scripts/check_clean.sh 2>&1) | grep -qF "has not been pushed"; then
    printf 'FAIL a pushed list still gets the never-pushed reminder\n'; fails=$((fails+1))
  fi
  printf 'flibbertquux\n' >>"$R/scripts/.clean-denylist"
  expect "the list changed after the push: fails" 1 "changed since the last make push-denylist" "$R"
  printf '# none left\n' >"$R/scripts/.clean-denylist"
  expect "the list emptied after the push: fails, and says to add a name back" 1 "add a name back" "$R"
  { cat "$T/list.bak"; printf '# a comment added later\n\n'; } >"$R/scripts/.clean-denylist"
  expect "a comment added after the push: passes" 0 "OK — no private names in:" "$R"
  # push-denylist and the check must read "the names" alike. In a UTF-8 locale an em space is
  # [[:space:]] to grep (BSD and GNU), so a comment indented with one was a comment to a push
  # run there and a name to the check (which runs in C): the checksum never matched. Without
  # a locale where grep shows that difference, the case would prove nothing: skip, and say so.
  if printf '\342\200\203# x\n' | LC_ALL=C.UTF-8 grep -qE '^[[:space:]]*#' 2>/dev/null; then
    { cat "$T/list.bak"; printf '\342\200\203# a pasted note\n'; } >"$R/scripts/.clean-denylist"
    LC_ALL=C.UTF-8 push "push-denylist in a UTF-8 locale: sends" "$R" 0 "args: secret set"
    expect "a list with an em-space-indented comment, as pushed: passes" 0 "OK — no private names in:" "$R"
    cp "$T/list.bak" "$R/scripts/.clean-denylist"
  else
    echo "SKIP: no C.UTF-8 locale where grep counts an em space as space; the UTF-8 push case would prove nothing"
  fi
  push "push-denylist: in a worktree, sends the main checkout's list" "$W" 0 "/repo/scripts/.clean-denylist"
  printf '# none yet\n' >"$R/scripts/.clean-denylist"
  push "push-denylist: refuses a list with no names" "$R" 2 "lists no names"
  printf '^zorblequux\n' >"$R/scripts/.clean-denylist"
  push "push-denylist: refuses entries anchored with ^" "$R" 2 "holding ^"
  [ -f "$T/gh.log" ] && { printf 'FAIL push-denylist: gh was called for a refused list\n'; fails=$((fails+1)); }
  cp "$T/list.bak" "$R/scripts/.clean-denylist"; : >"$R/Makefile"; : >"$W/Makefile"
  rm -f "$R/scripts/.clean-denylist.pushed"
  # With no checksum, a local run reminds you to push; CI (which sets CI) does not.
  expect "never pushed, locally: a reminder" 0 "has not been pushed from this checkout" "$R" "CI="
  if (cd "$R" && CI=true bash scripts/check_clean.sh 2>&1) | grep -qF "has not been pushed"; then
    printf 'FAIL the never-pushed reminder printed in CI\n'; fails=$((fails+1))
  fi
else
  echo "SKIP: push-denylist cases need make"
fi

# The workflow step that writes the list from the secret, run as written in clean.yml. The
# handoff zip carries no .github/, so there it is skipped, and says so.
WF="$HERE/../.github/workflows/clean.yml"
if [ -f "$WF" ]; then
  awk '/name: Write the private-name list/{f=1} f&&/run: \|/{r=1;next} r&&/^      [#-]/{exit} r{sub(/^          /,"");print}' "$WF" >"$T/step.sh"
  step() { # <label> <secret> <NO_SECRETS> <exit code wanted> <text the output must contain, or "">
    local out rc; rm -f "$T/stepdir/scripts/.clean-denylist"; mkdir -p "$T/stepdir/scripts"
    out="$(cd "$T/stepdir" && CLEAN_DENYLIST="$2" NO_SECRETS="$3" bash -e "$T/step.sh" 2>&1)"; rc=$?
    if [ "$rc" -eq "$4" ] && { [ -z "$5" ] || printf '%s' "$out" | grep -qF -- "$5"; }; then
      printf 'ok   %s\n' "$1"
    else
      printf 'FAIL %s (exit %s, wanted %s)\n%s\n' "$1" "$rc" "$4" "$out" | sed '2,$s/^/     /'; fails=$((fails+1))
    fi
  }
  b64() { { printf '# CLEAN_DENYLIST v1\n'; printf '%s' "$1"; } | base64 | tr -d '\n'; }
  step "CI step: a secret with names is written" "$(b64 "$(printf '# x\r\nzorblequux\r')")" false 0 ""
  if [ "$(cat "$T/stepdir/scripts/.clean-denylist")" != "$(printf '# CLEAN_DENYLIST v1\n# x\nzorblequux')" ]; then
    printf 'FAIL CI step: the list is not written as the secret holds it, less carriage returns\n'; fails=$((fails+1))
  fi
  step "CI step: a secret with no names fails" "$(b64 "# none yet")" false 1 "lists no names"
  step "CI step: a plain list as the secret fails" "$(printf 'zorble quux!\nzorblequux')" false 1 "not set by 'make push-denylist'"
  # Letters only, length a multiple of 4: valid base64 that decodes to garbage, no marker.
  step "CI step: a secret that only decodes as base64 fails" "zorblequuxzz" false 1 "not set by 'make push-denylist'"
  step "CI step: a marker that only starts like ours fails" "$(printf '# CLEAN_DENYLIST v123garbage\nzorblequux' | base64 | tr -d '\n')" false 1 "not set by 'make push-denylist'"
  step "CI step: no secret where secrets exist fails" "" false 1 "secret is missing"
  step "CI step: no secret with NO_SECRETS=true warns" "" true 0 "::warning::"
else
  echo "SKIP: CI step cases need .github/workflows/clean.yml (not in the handoff zip)"
fi

mkdir -p "$N"; (cd "$W" && tar -cf - --exclude .git .) | tar -xf - -C "$N"
printf 'ran the live check on zorblequux\n' >>"$N/docs/notes.md"
expect "no git, no list: skips the list and says so" 0 "denylist skipped" "$N"
# A copy with no list (a fork's CI, the handoff zip) skips the name check. Its OK line is
# all a reader of the green run sees, so the skip must be there, not only in the earlier line.
expect "no git, no list: the OK line says names were skipped" 0 "private-name check SKIPPED: no scripts/.clean-denylist" "$N"
# With no git, check-ignore cannot drop the list's own lines; only the exclusion by path can.
printf 'plain notes\n' >"$N/docs/notes.md"; cp "$R/scripts/.clean-denylist" "$N/scripts/"
expect "no git, list present: the list does not report itself" 0 "OK — no private names in:" "$N"
# That exclusion is for the list's own path only: a file of the same name elsewhere ships.
cp "$R/scripts/.clean-denylist" "$N/docs/"
expect "no git, a copy of the list in docs/: fails" 1 "docs/.clean-denylist" "$N"
rm "$N/docs/.clean-denylist"
# grep prints file:line:text, so this file's lines start like the list's own.
printf 'ran zorblequux\n' >"$N/scripts/.clean-denylist:1:notes"
expect "no git, a file named like the list plus a colon: fails" 1 "zorblequux" "$N"
rm "$N/scripts/.clean-denylist:1:notes"

[ "$fails" -eq 0 ] && { echo "test_clean_denylist: all passed"; exit 0; }
echo "test_clean_denylist: $fails failed"; exit 1
