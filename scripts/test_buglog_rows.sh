#!/usr/bin/env bash
#
# test_buglog_rows.sh — runs scripts/check_buglog_rows.sh on throwaway copies of
# docs/BUGLOG.md, and replays real merges under the repo's .gitattributes.
#
# Why it exists: docs/BUGLOG.md merges with git's union driver, so appends from two branches
# no longer conflict. Union also keeps both versions of a row one side edited next to the
# other side's change, and the guard is what catches that. These cases pin both halves: the
# guard's two rules and their edges, and that a real merge appends cleanly, keeps both
# versions in the edit shapes, and conflicts again without the attribute.
#
# It enters the way make check and CI do: it runs the guard script, which finds the file from
# where it sits, so each copy is laid out as the repo is.
#
# Usage: bash scripts/test_buglog_rows.sh
set -u
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(dirname -- "$HERE")"
T="$(mktemp -d "${TMPDIR:-/tmp}/buglog-rows-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
fails=0; n=0
check() { if "${@:2}"; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s\n' "$1"; fails=$((fails+1)); fi; }
has() { grep -Fq -- "$2" <<<"$1"; }
lacks() { ! grep -Fq -- "$2" <<<"$1"; }
is() { [ "$1" = "$2" ]; }

# A short head with the real header line: six lines, so the first row is line 7.
head6() { printf '# Bug log\n\nIntro.\n\n| Found | Where | What | Category | Impact | Effort | Status |\n|---|---|---|---|---|---|---|\n'; }
row() { printf '| %s | %s | %s | bug | low | small | %s |\n' "$1" "$2" "$3" "$4"; }
# words <n> <stem> — n words: <stem>1 <stem>2 …
words() { local i s=""; for ((i = 1; i <= $1; i++)); do s="$s${s:+ }$2$i"; done; printf '%s' "$s"; }

# fresh — sets c to a new folder laid out as the repo, holding a copy of the guard.
fresh() {
  c="$T/copy.$n"; n=$((n+1))
  mkdir -p "$c/scripts" "$c/docs" && cp "$ROOT/scripts/check_buglog_rows.sh" "$c/scripts/" \
    || { echo "FAIL — could not lay out $c."; exit 1; }
}
guard() { out="$(bash "$1/scripts/check_buglog_rows.sh" 2>&1)"; rc=$?; }

# 1. The repo's own file.
if [ -f "$ROOT/docs/BUGLOG.md" ]; then
  fresh; cp "$ROOT/docs/BUGLOG.md" "$c/docs/"; guard "$c"
  check "1 the repo's docs/BUGLOG.md passes" is "$rc" 0
  [ "$rc" = 0 ] || printf '%s\n' "$out" | sed 's/^/     /'
else
  echo "skip 1 the repo's docs/BUGLOG.md: none here (the handoff zip leaves it out)"
fi

# 2. Two rows each repeated with only Status changed: every pair is named.
fresh
{ head6; row 2026-10-01 "\`a.sh\`" "$(words 30 a)" open; row 2026-10-02 "\`b.sh\`" "$(words 30 b)" open
  row 2026-10-01 "\`a.sh\`" "$(words 30 a)" "fixed in #1"; row 2026-10-03 "\`c.sh\`" "$(words 30 c)" open
  row 2026-10-02 "\`b.sh\`" "$(words 30 b)" "fixed in #2"; } >"$c/docs/BUGLOG.md"
guard "$c"
check "2 two Status-only pairs fail"                is "$rc" 1
check "2 the first pair is named (lines 7 and 9)"   has "$out" "line 7: | 2026-10-01"
check "2   …its second line"                        has "$out" "line 9: | 2026-10-01"
check "2 the second pair is named (lines 8 and 11)" has "$out" "line 8: | 2026-10-02"
check "2   …its second line"                        has "$out" "line 11: | 2026-10-02"
check "2 the message says how to see the original"  has "$out" 'git show "$(git merge-base HEAD^1 HEAD^2)":docs/BUGLOG.md'

# 3. The phone-image shape: same date and Where, What differs after word 20.
fresh
{ head6; row 2026-10-25 "Next release notes" "$(words 25 w) old ending" open
  row 2026-10-25 "Next release notes" "$(words 25 w) new ending" open; } >"$c/docs/BUGLOG.md"
guard "$c"; check "3 same date and Where, What differs late: fails" is "$rc" 1

# 4. Rule (a): same date and Where, What differs from its first word.
fresh
{ head6; row 2026-10-25 "\`x.sh\`, \`f\`" "$(words 25 p)" open
  row 2026-10-25 "\`x.sh\`, \`f\`" "$(words 25 q)" open; } >"$c/docs/BUGLOG.md"
guard "$c"; check "4 same date and Where, What differs early: fails" is "$rc" 1

# 5. Rule (b) and its window: different dates and Where cells.
fresh
{ head6; row 2026-10-01 "\`one.sh\`" "$(words 20 s) alpha" open
  row 2026-10-09 "\`two.sh\`" "$(words 20 s) beta" open; } >"$c/docs/BUGLOG.md"
guard "$c"; check "5 What agrees for 20 words, differs at 21: fails" is "$rc" 1
fresh
{ head6; row 2026-10-01 "\`one.sh\`" "$(words 19 s) alpha tail" open
  row 2026-10-09 "\`two.sh\`" "$(words 19 s) beta tail" open; } >"$c/docs/BUGLOG.md"
guard "$c"; check "5 What differs at word 20: passes" is "$rc" 0
fresh
{ head6; row 2026-10-01 "\`one.sh\`" "$(words 12 s)" open
  row 2026-10-09 "\`two.sh\`" "$(words 12 s)" open; } >"$c/docs/BUGLOG.md"
guard "$c"; check "5 the same short What (12 words) twice: fails" is "$rc" 1

fresh
{ head6; row 2026-10-01 "\`one.sh\`" "" open; row 2026-10-09 "\`two.sh\`" "" open; } >"$c/docs/BUGLOG.md"
guard "$c"; check "5 two rows with an empty What are not a pair" is "$rc" 0

# 6. The SCAN_BASE shape, Where worded apart: two rows, one day, What agreeing for 8 words.
fresh
{ head6; row 2026-10-12 "\`check_clean.sh\`, \`SCAN_BASE\`" "$(words 8 n) packages $(words 10 x)" open
  row 2026-10-12 "\`check_clean.sh\`, \`SCAN_PRESENT\`" "$(words 8 n) plugin $(words 10 y)" open; } >"$c/docs/BUGLOG.md"
guard "$c"; check "6 one day, Where apart, What apart at word 9: passes" is "$rc" 0

# 7. Different rows: one date, or one Where on different dates.
fresh
{ head6; row 2026-10-12 "\`a.sh\`" "$(words 25 a)" open; row 2026-10-12 "\`b.sh\`" "$(words 25 b)" open
  row 2026-10-13 "\`a.sh\`" "$(words 25 c)" open; } >"$c/docs/BUGLOG.md"
guard "$c"
check "7 different rows pass"            is "$rc" 0
check "7   …and the pass names the count" has "$out" "ok   docs/BUGLOG.md: 3 rows, none twice"

# 8. Refusals and the zip.
fresh
{ head6; row 2026-10-12 "\`a.sh\`" "one | two" open; row 2026-10-12 "\`b.sh\`" "escaped \\| pipe" open; } >"$c/docs/BUGLOG.md"
guard "$c"
check "8 a bare | in a cell fails"           is "$rc" 1
check "8   …naming its line"                 has "$out" "line 7: | 2026-10-12"
check "8   …and not the escaped one"         lacks "$out" "line 8:"
fresh
{ head6; row 2026-10-12 "\`a.sh\`" "$(words 25 a)" open; printf '|2026-10-12|`a.sh`|%s|bug|low|small|fixed|\n' "$(words 25 a)"
  printf '| 2026-1-12 | `b.sh` | %s | bug | low | small | open |\n' "$(words 25 b)"; } >"$c/docs/BUGLOG.md"
guard "$c"
check "8 a row written without spaces fails"   has "$out" "line 8: |2026-10-12|"
check "8 a row with a mistyped date fails"     has "$out" "line 9: | 2026-1-12 |"
check "8   …and the exit is 1"                 is "$rc" 1
fresh
{ head6; row 2026-10-12 "\`a.sh\`" "$(words 25 a)" open; printf ' '; row 2026-10-12 "\`a.sh\`" "$(words 25 a)" fixed; } >"$c/docs/BUGLOG.md"
guard "$c"
check "8 an indented row fails"                 is "$rc" 1
check "8   …as a line it cannot read"           has "$out" "not rows the guard can read"
check "8   …naming its line"                    has "$out" "line 8:  | 2026-10-12"
fresh
{ head6; printf '|2026-10-12|`a.sh`|%s|bug|low|small|open|\n' "$(words 25 a)"; } >"$c/docs/BUGLOG.md"
guard "$c"
check "8 a file of unreadable rows only fails"  is "$rc" 1
check "8   …naming the line"                  has "$out" "line 7: |2026-10-12|"
check "8   …and not saying there are no rows"  lacks "$out" "no rows found"
fresh
{ head6; printf '| 2026-10-12 | `a.sh` | %s | bug | low | small | open |  \n' "$(words 25 a)"; } >"$c/docs/BUGLOG.md"
guard "$c"; check "8 trailing blanks after a row's last bar pass" is "$rc" 0
fresh; head6 >"$c/docs/BUGLOG.md"; guard "$c"
check "8 a file with no rows fails"          is "$rc" 1
fresh; mkdir "$c/.git"; guard "$c"
check "8 no file in a checkout fails"        is "$rc" 1
fresh; printf 'gitdir: elsewhere\n' >"$c/.git"; guard "$c"
check "8 no file in a worktree fails"        is "$rc" 1
fresh; guard "$c"
check "8 no file and no .git skips, exit 0"  is "$rc" 0
check "8   …and says so"                     has "$out" "skip — no docs/BUGLOG.md"

# 9–11. Real merges under the repo's .gitattributes.
if ! command -v git >/dev/null 2>&1; then
  echo "skip 9-11 the merge replays: they need git"
else
  # Hermetic: no config or attributes of the runner's may change how these merges go.
  unset GIT_CONFIG_PARAMETERS GIT_CONFIG_COUNT
  while read -r v; do unset "$v"; done < <(env | grep -E '^GIT_CONFIG_(KEY|VALUE)_[0-9]+=' | cut -d= -f1)
  export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_ATTR_NOSYSTEM=1
  g() { git -c user.name=t -c user.email=t@t -c init.defaultBranch=main -c commit.gpgsign=false \
      -c core.hooksPath=/dev/null -c core.attributesFile=/dev/null -c init.templateDir= "$@"; }
  base() { head6; row 2026-10-01 "\`a.sh\`" "$(words 25 a)" open; row 2026-10-02 "\`b.sh\`" "$(words 25 b)" open
           row 2026-10-03 "\`c.sh\`" "$(words 25 c)" open; }
  last_closed() { head6; row 2026-10-01 "\`a.sh\`" "$(words 25 a)" open; row 2026-10-02 "\`b.sh\`" "$(words 25 b)" open
           row 2026-10-03 "\`c.sh\`" "$(words 25 c)" "$1"; }
  ROW_D="$(row 2026-10-04 "\`d.sh\`" "$(words 25 d)" open)"
  ROW_E="$(row 2026-10-05 "\`e.sh\`" "$(words 25 e)" open)"
  # repo <with|without> — sets r to a new repo holding the guard, base() as the BUGLOG and,
  # with "with", this repo's .gitattributes; branches a and b start from it.
  repo() {
    fresh; r="$c"
    if [ "$1" = with ]; then cp "$ROOT/.gitattributes" "$r/" || { echo "FAIL — no .gitattributes to copy."; exit 1; }; fi
    base >"$r/docs/BUGLOG.md"
    { g -C "$r" init -q && g -C "$r" add -A && g -C "$r" commit -q -m base && g -C "$r" branch a; } \
      || { echo "FAIL — could not build the repo $r."; exit 1; }
  }
  # side <branch> <file content> — commits the content as docs/BUGLOG.md on <branch>.
  side() { g -C "$r" checkout -q "$1" && printf '%s\n' "$2" >"$r/docs/BUGLOG.md" \
           && g -C "$r" commit -q -am "$1" || { echo "FAIL — could not commit on $1."; exit 1; }; }
  merge() { g -C "$r" checkout -q -B b main >/dev/null 2>&1; g -C "$r" merge -q --no-edit a >/dev/null 2>&1; mrc=$?; }

  # 9. Both sides append: clean with the attribute, a conflict without it.
  repo with; side a "$(base; printf '%s\n' "$ROW_D")"; side main "$(base; printf '%s\n' "$ROW_E")"
  merge; f="$(cat "$r/docs/BUGLOG.md")"; guard "$r"
  check "9 two appends merge cleanly"           is "$mrc" 0
  check "9   …with no conflict markers"         lacks "$f" "<<<<<<<"
  check "9   …keeping one side's row"           has "$f" "$ROW_D"
  check "9   …and the other's"                  has "$f" "$ROW_E"
  check "9   …and the guard passes"             is "$rc" 0
  repo without; side a "$(base; printf '%s\n' "$ROW_D")"; side main "$(base; printf '%s\n' "$ROW_E")"
  merge; check "9 control: without .gitattributes they conflict" test "$mrc" -ne 0

  # 10. The incident: one side closes the last row, the other appends after it.
  repo with; side a "$(last_closed "fixed in #9")"; side main "$(base; printf '%s\n' "$ROW_E")"
  merge; f="$(cat "$r/docs/BUGLOG.md")"; guard "$r"
  check "10 close + append merges cleanly"      is "$mrc" 0
  check "10   …keeping both versions of the row" is "$(grep -c '^| 2026-10-03 ' <<<"$f")" 2
  check "10   …and the guard fails"             is "$rc" 1
  check "10   …naming the row"                  has "$out" "| 2026-10-03 | \`c.sh\`"

  # 11. Both sides close the same row differently.
  repo with; side a "$(last_closed "fixed in #9")"; side main "$(last_closed "dropped")"
  merge; f="$(cat "$r/docs/BUGLOG.md")"; guard "$r"
  check "11 two edits of one row merge cleanly"  is "$mrc" 0
  check "11   …keeping one side's edit"         has "$f" "| fixed in #9 |"
  check "11   …and the other's"                 has "$f" "| dropped |"
  check "11   …and neither base version"        lacks "$f" "$(row 2026-10-03 "\`c.sh\`" "$(words 25 c)" open)"
  check "11   …and the guard fails"             is "$rc" 1
fi

if [ "$fails" -ne 0 ]; then echo "test_buglog_rows: $fails case(s) failed"; exit 1; fi
echo "test_buglog_rows: all cases passed"
