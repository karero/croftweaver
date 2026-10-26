#!/usr/bin/env bash
#
# test_base_check.sh — drives independent_review.sh the way a caller does, with a diff made in a
# throwaway repository whose origin is a bare repository beside it, a stub `codex` first on PATH
# and HOME relocated, and checks its BASE CHECK. A diff on the wrong base is refused before any
# reviewer runs, naming each file that does not match; a diff on the right base, the edge records
# git writes included, reaches the reviewer and the run ends with a base: line. No reviewer is
# contacted and nothing leaves the machine: every fetch goes to the bare repository.
#
# Why it exists: on 2026-10-21 a diff made against a stale base was reviewed without a word, and
# the reviewers spent a whole round on other people's commits. The plan is change 1 of
# docs/reviews/SKILL-PLAN-review-input-base-and-size.md; the cases below are its T1 to T8.
#
# Needs git and perl. Usage: bash skills/independent-review/scripts/test_base_check.sh
set -u
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
SCRIPT="$HERE/independent_review.sh"
command -v git >/dev/null 2>&1 || { echo "SKIP test_base_check.sh — git not found"; exit 0; }
command -v perl >/dev/null 2>&1 || { echo "SKIP test_base_check.sh — perl not found"; exit 0; }
T="$(mktemp -d "${TMPDIR:-/tmp}/ir-base-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap '[ -n "${KEEP:-}" ] || rm -rf "$T"' EXIT
T="$(CDPATH= cd -- "$T" && pwd -P)"
mkdir -p "$T/bin" "$T/u/.codex" "$T/marks" "$T/notrepo"
: >"$T/u/.codex/auth.json"
printf 'model = "stub-codex"\n' >"$T/u/.codex/config.toml"
cat >"$T/bin/codex" <<'EOF'
#!/bin/sh
: >"$STUB_MARKS/codex-ran"
printf '%s\n' '- BUG: stub finding one' '- NIT: stub finding two'
EOF
chmod +x "$T/bin/codex"
printf '# Plan\n\nStep 1: do the thing.\n' >"$T/plan.md"
printf '| id | Sev |\n|---|---|\n| R1 | BUG |\n' >"$T/prior.md"
export GIT_CONFIG_NOSYSTEM=1 HOME="$T/u"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.invalid GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.invalid
unset GIT_DIR GIT_WORK_TREE

fails=0
check() {   # check <description> <command ...>
  if "${@:2}"; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s\n' "$1"; fails=$((fails+1)); fi
}
has()    { grep -qF -- "$2" "$T/$1"; }
lacks()  { ! grep -qF -- "$2" "$T/$1"; }
rc_is()  { [ "$(cat "$T/$1.rc")" = "$2" ]; }
ran()    { [ -e "$T/marks/$1/codex-ran" ]; }
not_ran() { [ ! -e "$T/marks/$1/codex-ran" ]; }
# run <name> <dir> <args to independent_review.sh ...> — leaves $T/<name>.out, .err and .rc
run() {
  local name="$1" dir="$2"; shift 2
  mkdir -p "$T/marks/$name"
  ( cd "$dir" && env -u CODEX_MODEL -u CODEX_EFFORT -u OLLAMA_MODEL -u OLLAMA_HOST -u OLLAMA_TRANSPORT \
      -u MELIOUS_MODEL -u SECOND_SEAT -u REVIEW_FETCH_TIMEOUT \
      PATH="$T/bin:$PATH" WITH_ANTIGRAVITY=0 REVIEW_LOG=off STUB_MARKS="$T/marks/$name" \
      REVIEW_RAW_DIR="$T/raw.$name" "${RUN_ENV[@]+"${RUN_ENV[@]}"}" bash "$SCRIPT" "$@" ) >"$T/$name.out" 2>"$T/$name.err"
  echo $? >"$T/$name.rc"
}
RUN_ENV=()
g() { git -C "$@"; }
commit() { g "$1" add -A && g "$1" commit -q -m "$2"; }
sha() { g "$1" rev-parse "$2"; }

# --- repository 1: origin moves on while a branch is worked on --------------------------------
R="$T/r1"; mkdir -p "$R"
git init -q --bare "$R/origin.git" && g "$R/origin.git" symbolic-ref HEAD refs/heads/main
git init -q "$R/w" && g "$R/w" symbolic-ref HEAD refs/heads/main
printf 'x one\n' >"$R/w/x"; printf 'y one\n' >"$R/w/y"; printf 'z one\n' >"$R/w/z"
commit "$R/w" A && g "$R/w" remote add origin "$R/origin.git" && g "$R/w" push -q origin main \
  && g "$R/w" remote set-head origin main \
  || { echo "FAIL — could not build repository 1."; exit 1; }
A="$(sha "$R/w" HEAD)"
git clone -q "$R/origin.git" "$R/o2" && printf 'z two\n' >"$R/o2/z" \
  && awk 'BEGIN { for (i = 0; i < 2600; i++) printf "line %d of a large file someone else added to the base\n", i }' >"$R/o2/big.txt" \
  && commit "$R/o2" B && g "$R/o2" push -q origin main || { echo "FAIL — could not move origin."; exit 1; }

# T1: the branch is cut from the moved origin (as a host's "update branch" leaves it), and the diff
# is made against the stale local main: it holds the other commit's z and big.txt.
g "$R/w" fetch -q origin && g "$R/w" checkout -q -b feat origin/main && printf 'x two\n' >"$R/w/x" && commit "$R/w" F
g "$R/w" diff main...HEAD >"$T/t1.diff"
run t1 "$R/w" "$T/t1.diff" --seat codex --depth normal
check "T1 stale base: refused (exit 2)" rc_is t1 2
check "T1 stale base: names z" has t1.err "  z: the diff changes it, but it is the same at the base and in HEAD"
check "T1 stale base: names big.txt" has t1.err "  big.txt: the diff changes it"
check "T1 stale base: does not name x, whose sides match" lacks t1.err "  x:"
check "T1 stale base: prints the command for a correct diff" has t1.err "diff --no-ext-diff --no-color --no-textconv -M --src-prefix=a/ --dst-prefix=b/ $(sha "$R/w" origin/main) HEAD"
check "T1 stale base: no reviewer ran" not_ran t1
# T8: base before size. The stale diff is over the 120,000-byte check; the base check speaks first.
check "T8 the stale diff is over 120,000 bytes" [ "$(wc -c <"$T/t1.diff" | tr -d ' ')" -gt 120000 ]
check "T8 base before size: refused by the base check" has t1.err "Base check:"
check "T8 ... before any seat's size limit was reached" sh -c '! grep -q "FAILED" "$1.out" && ! grep -qF "120,000" "$1.err"' _ "$T/t1"

# T2: origin moved on, the branch did not take it; a three-dot diff against the stale local main.
g "$R/w" checkout -q -b old main && printf 'y two\n' >"$R/w/y" && commit "$R/w" G
G="$(sha "$R/w" HEAD)"
printf 'z three\n' >"$R/o2/z" && commit "$R/o2" C && g "$R/o2" push -q origin main
g "$R/w" diff main...HEAD >"$T/t2.diff"
run t2 "$R/w" "$T/t2.diff" --seat codex --depth normal
check "T2 origin moved, branch did not take it: runs (exit 0)" rc_is t2 0
check "T2: the base: line names the merge base, fetched, every file present" has t2.out "base: $A (merge base with origin's HEAD $(sha "$R/o2" HEAD), fetched; every changed tracked file present)"
check "T2: the reviewer ran" ran t2

# T3: deltas. D1 changes y again; the delta since G is y alone.
printf 'y three\n' >"$R/w/y" && commit "$R/w" D1
D1="$(sha "$R/w" HEAD)"
g "$R/w" diff "$G"..HEAD >"$T/t3.diff"
run t3a "$R/w" "$T/t3.diff" --seat codex --verify "$T/prior.md" --base "$G" --depth normal --round 2
check "T3 delta with --verify and --base: runs" rc_is t3a 0
check "T3: the base: line names the given base" has t3a.out "base: $G (--base $G)"
# T3e: --evidence leaves the checked text alone. The evidence opens with a diff record for a file
# the repo does not have, which the check refuses wherever it sits in a diff (the control below):
# if the evidence ever reached the checked text, this run would be refused too.
printf '%s\n' 'diff --git a/nosuch b/nosuch' 'index 1111111..2222222 100644' '--- a/nosuch' '+++ b/nosuch' \
  '@@ -1 +1 @@' '-old' '+new' 'make check: all checks passed' >"$T/ev-diff.txt"
run t3e "$R/w" "$T/t3.diff" --seat codex --verify "$T/prior.md" --base "$G" --depth normal --round 2 --evidence "$T/ev-diff.txt"
check "T3e delta with --evidence: runs, the base check passed" rc_is t3e 0
check "T3e: the base: line names the given base, checked" has t3e.out "base: $G (--base $G)"
check "T3e: the reviewer ran" ran t3e
cat "$T/t3.diff" "$T/ev-diff.txt" >"$T/t3ev.diff"
run t3ev "$R/w" "$T/t3ev.diff" --seat codex --verify "$T/prior.md" --base "$G" --depth normal --round 2
check "T3e control: the same evidence appended to the diff is refused" rc_is t3ev 2
check "T3e control: ... by the base check" has t3ev.err "Base check:"
run t3b "$R/w" "$T/t3.diff" --seat codex --verify "$T/prior.md" --depth normal --round 2
check "T3 --verify with no --base: refused" rc_is t3b 2
check "T3 --verify with no --base: names --base" has t3b.err "Pass --base <last-reviewed-head>."
run t3c "$R/w" "$T/t3.diff" --seat codex --depth normal
check "T3 delta over a file the branch changed before, no --base: refused" rc_is t3c 2
check "T3 ... with the delta line" has t3c.err "For a delta since a reviewed head, pass --base <that head>."
check "T3 ... no reviewer ran" not_ran t3c
# T7: a delta over a file no earlier commit of the branch touched passes the default check, and
# the base: line names what it leaves out.
printf 'x three\n' >"$R/w/x" && commit "$R/w" D2
g "$R/w" diff "$D1"..HEAD >"$T/t7.diff"
run t7 "$R/w" "$T/t7.diff" --seat codex --depth normal
check "T7 last commit only, its file untouched before: runs" rc_is t7 0
check "T7: the base: line names the file it leaves out" has t7.out "; not in this diff: y)"

# T6: --local-only never fetches. origin points at a command that would leave a mark if run.
g "$R/w" config protocol.ext.allow always
g "$R/w" remote set-url origin "ext::sh -c touch% $T/fetched"
g "$R/w" diff main...HEAD >"$T/t6.diff"
run t6 "$R/w" "$T/t6.diff" --local-only --depth normal
check "T6 --local-only: nothing was fetched" [ ! -e "$T/fetched" ]
check "T6 --local-only: the base: line says so" has t6.out "not fetched: --local-only"
g "$R/w" remote set-head origin -d
run t6b "$R/w" "$T/t6.diff" --local-only --depth normal
check "T6 --local-only with no origin/HEAD: refused" rc_is t6b 2
check "T6 ... naming --base" has t6b.err "origin/HEAD is not set here"
check "T6b nothing was fetched" [ ! -e "$T/fetched" ]

# --- repository 2: the records git writes ------------------------------------------------------
R="$T/r2"; mkdir -p "$R"
git init -q --bare "$R/origin.git" && g "$R/origin.git" symbolic-ref HEAD refs/heads/main
W="$R/w"; git init -q "$W" && g "$W" symbolic-ref HEAD refs/heads/main
mkdir -p "$W/w/sub" "$W/d"
for i in 1 2 3 4 5 6 7 8; do printf 'rename me whole, line %s\n' "$i"; done >"$W/r100"
for i in 1 2 3 4 5 6 7 8; do printf 'rename me with an edit, line %s\n' "$i"; done >"$W/r80"
printf '#!/bin/sh\necho hi\n' >"$W/m.sh"; printf '#!/bin/sh\necho two\n' >"$W/m2.sh"; chmod +x "$W/m2.sh"
printf 'bin\000\001\002' >"$W/bin.dat"; printf 'delete me\n' >"$W/del.txt"; printf 'target\n' >"$W/target.txt"
printf 'space\n' >"$W/sp ace.txt"; printf 'tab\n' >"$W/t	ab.txt"; printf 'inside w\n' >"$W/w/inside.txt"
printf 'old has no newline' >"$W/nonl-old.txt"; printf 'new will have none\n' >"$W/nonl-new.txt"; printf 'neither' >"$W/nonl-both.txt"
printf 'keep\n-- x\nkeep\n' >"$W/dash.txt"; printf 'deep\n' >"$W/w/sub/deep.txt"
printf 'plain name\n' >"$W/plain.txt"; printf 'a file\n' >"$W/tc"; ln -s target.txt "$W/sl"
printf 'x = 1\ny = 2\n' >"$W/ws.txt"; printf 'copy me\n' >"$W/cp_src.txt"; printf '#!/bin/sh\n' >"$W/late.sh"
printf 'b2\000' >"$W/bin2.dat"; ln -s target.txt "$W/sl2"
for i in 1 2 3 4 5 6 7 8; do printf 'text that turns binary when renamed, line %s\n' "$i"; done >"$W/tb.txt"
printf 'gone\000\377' >"$W/gone.bin"
commit "$W" E0 && g "$W" remote add origin "$R/origin.git" && g "$W" push -q origin main \
  && g "$W" remote set-head origin main || { echo "FAIL — could not build repository 2."; exit 1; }
E0="$(sha "$W" HEAD)"
g "$W" checkout -q -b feat
g "$W" mv r100 r100b; g "$W" mv r80 r80b; printf 'rename me with an edit, line 8 changed\n' >>"$W/r80b"
chmod +x "$W/m.sh"; printf 'bin\000\001\003' >"$W/bin.dat"; g "$W" rm -q del.txt; printf 'new\n' >"$W/new.txt"
ln -s target.txt "$W/link"; printf 'space two\n' >"$W/sp ace.txt"; printf 'tab two\n' >"$W/t	ab.txt"
g "$W" mv w/inside.txt w/moved.txt
printf 'old has no newline\n' >"$W/nonl-old.txt"; printf 'new will have none' >"$W/nonl-new.txt"; printf 'still neither' >"$W/nonl-both.txt"
printf 'keep\nkeep\n++ x\n' >"$W/dash.txt"; printf 'deep two\n' >"$W/w/sub/deep.txt"
g "$W" mv plain.txt "über.txt"; rm "$W/tc" && ln -s target.txt "$W/tc"; rm "$W/sl" && printf 'now a file\n' >"$W/sl"
: >"$W/empty.txt"; printf 'x  =  1\ny = 3\n' >"$W/ws.txt"; rm "$W/bin2.dat" && ln -s target.txt "$W/bin2.dat"; rm "$W/sl2" && printf 'b3\000' >"$W/sl2"; cp "$W/cp_src.txt" "$W/cp_dst.txt"; printf 'copy me\nmore\n' >"$W/cp_src.txt"
g "$W" mv tb.txt tb.bin; printf '\000' >>"$W/tb.bin"; g "$W" rm -q gone.bin
commit "$W" E1
mkdir "$W/subm" && g "$W" update-index --add --cacheinfo "160000,$E0,subm" && g "$W" commit -q -m "a submodule pointer"
chmod +x "$W/late.sh" && g "$W" add late.sh && g "$W" commit -q -m "late.sh runs now

The message quotes a diff:
diff --git a/x b/x
index 1234567..89abcde 100644"

g "$W" diff -M "$E0"..HEAD >"$T/t4.diff"
check "T4 fixture: git wrote a 100% rename, a rename with an edit, a mode change and a quoted name" \
  sh -c 'grep -q "^similarity index 100%" "$1" && grep -q "^rename from r80" "$1" && grep -q "^new mode 100755" "$1" && grep -q "^diff --git \"a/t" "$1"' _ "$T/t4.diff"
run t4 "$W" "$T/t4.diff" --seat codex --depth normal
check "T4 edge records from git: runs" rc_is t4 0
check "T4: every changed file present" has t4.out "every changed tracked file present)"
run t4sub "$W/w/sub" "$T/t4.diff" --seat codex --depth normal
check "T4 run from a subdirectory: the same result" rc_is t4sub 0
g "$W" format-patch -1 --stdout >"$T/t4fp.diff"
run t4fp "$W" "$T/t4fp.diff" --seat codex --depth normal
check "T4 a one-patch format-patch ending in a mode-only record, its message quoting a diff: runs" rc_is t4fp 0
check "T4 fixture: the diff holds a submodule pointer" grep -q '^+Subproject commit' "$T/t4.diff"
g "$W" format-patch -1 --stdout HEAD~1 >"$T/t4fp2.diff"
run t4fp2 "$W" "$T/t4fp2.diff" --seat codex --depth normal --base "$E0"
check "T4 a one-patch format-patch ending in a hunk: runs" rc_is t4fp2 0
check "T4 fixture: a rename to a C-quoted name, a type change, an empty file, binary and symlink swapping" \
  sh -c 'grep -q "^rename to \"" "$1" && grep -q "^new file mode 120000" "$1" && grep -q "^new file mode 100644" "$1" && grep -q "^Binary files a/bin2.dat and /dev/null differ" "$1" && grep -q "^Binary files /dev/null and b/sl2 differ" "$1"' _ "$T/t4.diff"
check "T4 fixture: a text file renamed to a binary one, written as one binary record (its old side is text)" \
  grep -q "^Binary files a/tb.txt and b/tb.bin differ" "$T/t4.diff"
# A type change's text half is applied too: a hand-edited symlink target is caught.
sed 's|^+target.txt$|+elsewhere.txt|' "$T/t4.diff" >"$T/t5link.diff"
run t5link "$W" "$T/t5link.diff" --seat codex --depth normal
check "T5 a symlink's target edited by hand (in a binary/symlink swap): refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "headers match the base, but" "$1.err" && grep -qF "bin2.dat" "$1.err"' _ "$T/t5link"
g "$W" diff -U0 "$E0"..HEAD >"$T/t4u0.diff"
run t4u0 "$W" "$T/t4u0.diff" --seat codex --depth normal
check "T4 -U0: runs" rc_is t4u0 0
g "$W" diff -w "$E0"..HEAD >"$T/t5w.diff"
run t5w "$W" "$T/t5w.diff" --seat codex --depth normal
check "T5 -w hides a whitespace change beside a real one: refused" rc_is t5w 2
check "T5 ... by the content step, naming the file" sh -c 'grep -qF "headers match the base, but" "$1.err" && grep -qF "ws.txt" "$1.err"' _ "$T/t5w"
printf 'diff --git a/new.txt b/new.txt\nnew file mode 100644\n' >"$T/t5cut.diff"
run t5cut "$W" "$T/t5cut.diff" --seat codex --depth normal
check "T5 a new-file record cut before its index line: refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "no index line" "$1.err"' _ "$T/t5cut"
g "$W" diff "$E0"..HEAD -- dash.txt | sed '/^@@/,$d' >"$T/t5nohunk.diff"
run t5nohunk "$W" "$T/t5nohunk.diff" --seat codex --depth normal --base "$E0"
check "T5 a record whose hunks were cut off: refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "headers match the base, but" "$1.err"' _ "$T/t5nohunk"
# A record marked binary shows the reviewers no readable lines and the content step does not apply
# it, so git's patch must mark its new side binary too (its old side, for a deletion). Refused: a
# text change or deletion relabelled as binary, its index line true, and a rename marked binary
# from a deleted binary file to a new text one. Still run: a real binary record, and git's own
# rename of a text file to a binary one (T4). Git's own rename of a binary file to a text one:
# repository 3.
{ g "$W" diff "$E0"..HEAD -- dash.txt | sed '/^--- /,$d'; printf 'Binary files a/dash.txt and b/dash.txt differ\n'; } >"$T/t5bin.diff"
run t5bin "$W" "$T/t5bin.diff" --seat codex --depth normal --base "$E0"
check "T5 a text record relabelled as binary: refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "  dash.txt: the diff marks it binary, but git shows its content" "$1.err"' _ "$T/t5bin"
{ g "$W" diff "$E0"..HEAD -- del.txt | sed '/^--- /,$d'; printf 'Binary files a/del.txt and /dev/null differ\n'; } >"$T/t5bindel.diff"
run t5bindel "$W" "$T/t5bindel.diff" --seat codex --depth normal --base "$E0"
check "T5 a deleted text file relabelled as binary: refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "  del.txt: the diff marks it binary, but git shows its content" "$1.err"' _ "$T/t5bindel"
printf 'diff --git a/gone.bin b/new.txt\nsimilarity index 60%%\nrename from gone.bin\nrename to new.txt\nindex %s..%s 100644\nBinary files a/gone.bin and b/new.txt differ\n' \
  "$(sha "$W" "$E0:gone.bin")" "$(sha "$W" HEAD:new.txt)" >"$T/t5binmv.diff"
run t5binmv "$W" "$T/t5binmv.diff" --seat codex --depth normal --base "$E0"
check "T5 a rename marked binary, from a deleted binary file to a new text one: refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "  new.txt: the diff marks it binary, but git shows its content" "$1.err"' _ "$T/t5binmv"
g "$W" diff --binary "$E0"..HEAD -- bin.dat >"$T/t4bin.diff"
run t4bin "$W" "$T/t4bin.diff" --seat codex --depth normal --base "$E0"
check "T4 a real binary record on its own, made with --binary: runs" sh -c 'grep -q "^GIT binary patch" "$1.diff" && grep -q "^0$" "$1.rc"' _ "$T/t4bin"
g "$W" -c diff.renames=copies diff "$E0"..HEAD >"$T/t5copies.diff"
run t5copies "$W" "$T/t5copies.diff" --seat codex --depth normal
check "T5 diff.renames=copies writes a copy record: refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "copy record" "$1.err"' _ "$T/t5copies"
remedy="$(sed -n 's/^Make it with git: //p' "$T/t5copies.err")"
( cd "$W" && eval "git -c diff.renames=copies ${remedy#git }" ) >"$T/t4remedy.diff" 2>/dev/null
run t4remedy "$W" "$T/t4remedy.diff" --seat codex --depth normal
check "T4 the printed remedy, run with diff.renames=copies still set, makes a diff that runs" rc_is t4remedy 0
g "$W" diff --cached "$E0" >"$T/t4cached.diff"
run t4cached "$W" "$T/t4cached.diff" --seat codex --depth normal
check "T4 git diff --cached <base> with the index at HEAD: runs" rc_is t4cached 0
printf 'uncommitted\n' >>"$W/new.txt"
g "$W" diff "$E0" >"$T/t4wt.diff"
run t4wt "$W" "$T/t4wt.diff" --seat codex --depth normal
check "T4 a working-tree diff: runs" rc_is t4wt 0
check "T4 ... and says its new sides are the working tree's" has t4wt.out "new sides from the working tree"
# T5: refusals
run t5wt "$W" "$T/t4.diff" --seat codex --depth normal
check "T5 HEAD's diff while the working tree moved on: still runs against HEAD" rc_is t5wt 0
g "$W" -c diff.mnemonicPrefix=true diff "$E0" >"$T/t5mn.diff"
run t5mn "$W" "$T/t5mn.diff" --seat codex --depth normal
check "T5 mnemonic prefixes: refused" rc_is t5mn 2
check "T5 ... as a prefix other than a/ and b/" has t5mn.err "a prefix other than a/ and b/"
g "$W" add new.txt && printf 'more\n' >>"$W/new.txt"
g "$W" diff >"$T/t5idx.diff"
run t5idx "$W" "$T/t5idx.diff" --seat codex --depth normal
check "T5 plain git diff with the index ahead of the base: refused" rc_is t5idx 2
check "T5 ... naming the file" has t5idx.err "  new.txt: the base has no such file"
g "$W" checkout -q -- new.txt && g "$W" reset -q -- new.txt && g "$W" checkout -q -- new.txt
printf 'diff --git a/m2.sh b/m2.sh\nold mode 100644\nnew mode 100755\n' >"$T/t5mode.diff"
run t5mode "$W" "$T/t5mode.diff" --seat codex --depth normal
check "T5 a stale mode change: refused" rc_is t5mode 2
check "T5 ... naming m2.sh" has t5mode.err "  m2.sh: the diff changes it, but it is the same at the base and in"
printf 'one\n' >"$T/a.txt"; printf 'two\n' >"$T/b.txt"; ( cd "$T" && diff -u a.txt b.txt ) >"$T/t5hand.diff"
run t5hand "$W" "$T/t5hand.diff" --seat codex --depth normal
check "T5 a hand-made diff -u: refused" rc_is t5hand 2
check "T5 ... naming --base none" has t5hand.err "pass --base none"
g "$W" diff --no-prefix "$E0"..HEAD >"$T/t5np.diff"
run t5np "$W" "$T/t5np.diff" --seat codex --depth normal
check "T5 --no-prefix: refused" rc_is t5np 2
g "$W" diff --color=always "$E0"..HEAD >"$T/t5col.diff"
run t5col "$W" "$T/t5col.diff" --seat codex --depth normal
check "T5 colour codes: refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "colour codes" "$1.err"' _ "$T/t5col"
printf 'diff --cc x\nindex 1234567,89abcde..0123456\n' >"$T/t5cc.diff"
run t5cc "$W" "$T/t5cc.diff" --seat codex --depth normal
check "T5 diff --cc: refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "combined diff" "$1.err"' _ "$T/t5cc"
printf 'diff --git a/x b/y\nsimilarity index 100%%\ncopy from x\ncopy to y\n' >"$T/t5cp.diff"
run t5cp "$W" "$T/t5cp.diff" --seat codex --depth normal
check "T5 a copy record: refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "copy record" "$1.err"' _ "$T/t5cp"
printf 'later\n' >"$W/later.txt" && commit "$W" E2
g "$W" format-patch -2 --stdout >"$T/t5ser.diff"
run t5ser "$W" "$T/t5ser.diff" --seat codex --depth normal
check "T5 a format-patch series: refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "format-patch series" "$1.err"' _ "$T/t5ser"
run t5out "$T/notrepo" "$T/t4.diff" --seat codex --depth normal
check "T5 outside a work tree: refused, naming --base none" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "not inside a git work tree" "$1.err" && grep -qF -- "--base none" "$1.err"' _ "$T/t5out"
run t5none "$T/notrepo" "$T/t4.diff" --seat codex --depth normal --base none
check "T5 --base none outside a repo: runs" rc_is t5none 0
check "T5 ... and says it was not checked" has t5none.out "base: not checked (--base none)"
run t5dash "$W" "$T/t4.diff" --seat codex --depth normal --base -x
check "T5 --base -x: refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "starts with" "$1.err"' _ "$T/t5dash"
run t5plan "$W" "$T/plan.md" --seat codex --depth normal --base "$E0"
check "T5 --base on a plan: refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF -- "--base is for a diff" "$1.err"' _ "$T/t5plan"
RUN_ENV=(REVIEW_FETCH_TIMEOUT=0)
run t5to "$W" "$T/t4.diff" --seat codex --depth normal
RUN_ENV=()
check "T5 REVIEW_FETCH_TIMEOUT=0: refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "REVIEW_FETCH_TIMEOUT" "$1.err"' _ "$T/t5to"
# The merge base is HEAD and the working tree is clean: on main itself.
g "$W" checkout -q main
printf 'dirty on main\n' >>"$W/dash.txt"
g "$W" diff HEAD >"$T/t4main.diff"
run t4main "$W" "$T/t4main.diff" --seat codex --depth normal
check "T4 uncommitted work on the default branch itself: runs" rc_is t4main 0
check "T4 ... against the working tree" has t4main.out "new sides from the working tree"
g "$W" checkout -q -- dash.txt
run t5head "$W" "$T/t4.diff" --seat codex --depth normal
check "T5 on the default branch with a clean tree: refused, nothing to review" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "nothing to review" "$1.err"' _ "$T/t5head"
# No merge base: an unrelated history, in a clone of its own (the shallow clone's message).
git clone -q "$R/origin.git" "$R/solo" && g "$R/solo" checkout -q --orphan solo && g "$R/solo" rm -rqf . \
  && printf 'alone\n' >"$R/solo/alone.txt" && commit "$R/solo" solo
run t5mb "$R/solo" "$T/t4.diff" --seat codex --depth normal
check "T5 no merge base: refused, naming --unshallow" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "git fetch --unshallow" "$1.err"' _ "$T/t5mb"
g "$W" checkout -q feat
# A fetch that fails, and one that hangs.
g "$W" remote set-url origin "$T/missing.git"
run t5ff "$W" "$T/t4.diff" --seat codex --depth normal
check "T5 a fetch that fails: refused" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "fetching origin'"'"'s HEAD failed" "$1.err"' _ "$T/t5ff"
check "T5 ... offering the local origin/HEAD's merge base" has t5ff.err "To go on with the local origin/HEAD instead: --base $E0"
g "$W" config protocol.ext.allow always
g "$W" remote set-url origin "ext::sh -c sleep% 6"
RUN_ENV=(REVIEW_FETCH_TIMEOUT=2)
started=$SECONDS
run t5hang "$W" "$T/t4.diff" --seat codex --depth normal
took=$((SECONDS - started))
RUN_ENV=()
check "T5 a fetch that hangs: refused within the limit" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "did not finish within 2 seconds" "$1.err"' _ "$T/t5hang"
check "T5 ... in under 6 seconds (took ${took}s)" [ "$took" -lt 6 ]
check "T5 ... and no reviewer ran on any refusal" sh -c 'for m in "$1"/marks/t5*; do case "$m" in *t5none|*t5wt) continue ;; esac; [ ! -e "$m/codex-ran" ] || exit 1; done' _ "$T"

# --- repository 3: git -M's own rename of a binary file to a text one --------------------------
# git writes it as one binary record, so the new text would go unread: refused, and the remedy it
# prints uses --no-renames, which writes the text side's lines. That diff runs.
R="$T/r3"; git init -q "$R" && g "$R" symbolic-ref HEAD refs/heads/main
lines() { for i in 1 2 3 4 5 6 7 8; do printf 'binary until it is renamed, line %s\n' "$i"; done; }
{ lines; printf '\000'; } >"$R/b.dat"
commit "$R" X0 || { echo "FAIL — could not build repository 3."; exit 1; }
X0="$(sha "$R" HEAD)"
g "$R" mv b.dat t.txt && lines >"$R/t.txt" && commit "$R" X1
g "$R" diff -M "$X0" HEAD >"$T/t5bt.diff"
check "T5 fixture: git -M wrote the rename as one binary record" grep -q "^Binary files a/b.dat and b/t.txt differ" "$T/t5bt.diff"
run t5bt "$R" "$T/t5bt.diff" --seat codex --depth normal --base "$X0"
check "T5 git -M's rename of a binary file to a text one: refused, naming t.txt" sh -c 'grep -q "^2$" "$1.rc" && grep -qF "  t.txt: the diff marks it binary, but git shows its content" "$1.err"' _ "$T/t5bt"
check "T5 ... and no reviewer ran" not_ran t5bt
remedy="$(sed -n '/^Make the diff again from that base:$/{n;s/^  //p;}' "$T/t5bt.err")"
check "T5 ... the printed remedy uses --no-renames" sh -c 'case "$1" in *" --no-renames "*) exit 0 ;; esac; exit 1' _ "$remedy"
( cd "$R" && eval "$remedy" ) >"$T/t4bt.diff" 2>"$T/t4bt.remedy.err"; remedy_rc=$?
check "T4 the printed remedy exits 0 (exit $remedy_rc) and writes nothing to stderr" sh -c '[ "$1" = 0 ] && [ ! -s "$2" ]' _ "$remedy_rc" "$T/t4bt.remedy.err"
sed 's/^/     remedy stderr: /' "$T/t4bt.remedy.err"
run t4bt "$R" "$T/t4bt.diff" --seat codex --depth normal --base "$X0"
check "T4 the printed remedy makes a diff that runs" rc_is t4bt 0

if [ "$fails" -eq 0 ]; then echo "PASS — test_base_check.sh"; else echo "FAIL — test_base_check.sh: $fails check(s) failed"; exit 1; fi
