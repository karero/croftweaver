#!/usr/bin/env bash
#
# test_pre_push_hook.sh — drives the site template's git pre-push hook
# (skills/new-website/templates/astro/scripts/hooks/pre-push) with a stubbed `npm`, both as
# shipped and with its optional PR-only-main block uncommented.
#
# Why it exists: the hook reads git's ref lines from stdin once and replays them, so the
# block can refuse a push to main and a push that only deletes refs can skip the gate. Every
# check of that was by hand, and one round of hand checks let through a stdin guard that read
# nothing without /proc, so an enabled block waved a push to main through (PR #125). These
# cases pin what the gate does per push shape, per stdin kind and per shell, and that the
# block refuses main whatever stdin git's pipe looks like.
#
# It also runs the "prepare" script that wires the hook (the template's package.json and
# scripts/wire-hooks.mjs) through npm, to pin that the line needs no particular shell and
# that it touches git's hook folder only where the site is the root of its repo. Those cases
# need node and npm, and say so where they are skipped.
#
# Usage: bash scripts/test_pre_push_hook.sh
set -u
if ! command -v git >/dev/null 2>&1; then
  echo "SKIP: test_pre_push_hook.sh needs git (it pushes to a throwaway bare repo)"
  exit 0
fi
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
HOOK="$HERE/../skills/new-website/templates/astro/scripts/hooks/pre-push"
T="$(mktemp -d "${TMPDIR:-/tmp}/pre-push-test.XXXXXX")" \
  || { echo "FAIL — could not create a temp dir."; exit 1; }
trap 'rm -rf "$T"' EXIT
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
unset ALLOW_MAIN_PUSH
# A git hook exports GIT_DIR (and friends) to what it runs. Inherited here, they would aim the
# throwaway repos' git commands at the caller's repo.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
git="git -c user.name=t -c user.email=t@t -c init.defaultBranch=main -c commit.gpgsign=false"
fails=0
check() { if [ "$2" = "$3" ]; then printf 'ok   %s\n' "$1"; else printf 'FAIL %s (expected %s, got %s)\n' "$1" "$2" "$3"; fails=$((fails+1)); fi; }
# yes or no: does $1 contain $2. A function, not an inline "$(case …)": bash 3.2 (macOS)
# ends a $( ) at the first `)` of a case pattern.
has() { case "$1" in *"$2"*) echo yes ;; *) echo no ;; esac; }

# The hook as shipped, and with the block's six commented lines uncommented — the edit
# website-team-setup §5-B makes. If that edit stops changing exactly six lines, the "on"
# cases would silently test the shipped hook, so fail loudly instead.
cp "$HOOK" "$T/off"
sed '/^# while read -r _lref/,/^# done$/s/^# //' "$HOOK" >"$T/on"
changed="$(diff "$T/off" "$T/on" | grep -c '^>')"
check "the block uncomments as six lines" 6 "$changed"

# The real npm, before the stub below shadows it: the "prepare" cases at the end run through it.
NPM="$(command -v npm || true)"
# A stub npm, so "the gate ran" is cheap and visible. No tests/ dir, so the hook's optional
# classifier and SEO steps stay off; no scripts/verify.mjs, so the hook takes its old path.
mkdir -p "$T/bin" "$T/site"
# NPM_FAIL=build, =check or =test makes that step fail, to prove a red gate stops the push.
# `run build` and `test` are what the hook runs in a site without scripts/verify.mjs; the
# `run --silent …` forms are what verify.mjs runs (the cases after the shell loop).
cat >"$T/bin/npm" <<'NPM'
#!/bin/sh
echo "npm $*"
case "$*" in
  "run build")                                [ "${NPM_FAIL:-}" = build ] && exit 1 ;;
  test|"run --silent test -- --reporter=dot") [ "${NPM_FAIL:-}" = test ] && exit 1 ;;
  "run --silent check")                       [ "${NPM_FAIL:-}" = check ] && exit 1 ;;
esac
exit 0
NPM
chmod +x "$T/bin/npm"
export PATH="$T/bin:$PATH"
TO=""; command -v timeout >/dev/null 2>&1 && TO="timeout 20"

# outcome <output> — SKIP (gate skipped), BLOCK (block refused), GATE (gate ran and passed),
# FAILED (a gate step failed), or what went wrong. Every run appends "@@rc=<exit status>",
# and an outcome counts only when the status agrees with the message: git decides on the
# status alone, so a "blocked" message followed by exit 0 would still let the push through.
# A hang shows as a timeout, not a stuck `make check`.
outcome() {
  local rc want name
  rc="$(printf '%s\n' "$1" | sed -n 's/^@@rc=//p')"
  case "$1" in
    *"pre-push gate: skipped"*)        want=0 name=SKIP ;;
    *"Direct push to 'main' blocked"*) want=1 name=BLOCK ;;
    *"✓ pre-push gate passed"*)        want=0 name=GATE ;;
    *"▶ pre-push gate:"*)              want=1 name=FAILED ;;
    *) echo "other(rc=$rc):$(printf '%s' "$1" | tr '\n' ' ' | cut -c1-80)"; return ;;
  esac
  if [ -z "$rc" ]; then echo "$name-without-status"
  elif [ "$want" = 0 ] && [ "$rc" = 0 ]; then echo "$name"
  elif [ "$want" = 1 ] && [ "$rc" != 0 ]; then echo "$name"
  else echo "$name-but-exit-$rc"; fi
}
# run <shell> <hook> <stdin-setup...> — runs the hook in the stub site (or in $SITE_DIR) with
# the given stdin.
run() {
  local sh="$1" hook="$2"; shift 2
  (cd "${SITE_DIR:-$T/site}" && $TO "$@" "$sh" "$hook") 2>&1; printf '\n@@rc=%s\n' "$?"
}

Z=0000000000000000000000000000000000000000; A=1111111111111111111111111111111111111111
DEL="(delete) $Z refs/heads/feat $A"
DEL2="(delete) $Z refs/tags/v1 $A"
UPD="HEAD $A refs/heads/feat $Z"
DELMAIN="(delete) $Z refs/heads/main $A"
PUSHMAIN="HEAD $A refs/heads/main $Z"
printf '%s\n' "$DEL" >"$T/del.txt"
printf '%s\n' "$PUSHMAIN" >"$T/pushmain.txt"

piped() { local sh="$1" hook="$2"; shift 2; printf '%s\n' "$@" | run "$sh" "$hook" env; }

shells="bash"
for s in sh dash; do command -v "$s" >/dev/null 2>&1 && shells="$shells $s"; done
for sh in $shells; do
  for v in off on; do
    h="$T/$v"
    if [ "$v" = on ]; then main_del=BLOCK main_push=BLOCK; else main_del=SKIP main_push=GATE; fi
    p="$sh, block $v:"
    check "$p deleting one ref skips the gate"   SKIP "$(outcome "$(piped "$sh" "$h" "$DEL")")"
    check "$p deleting two refs skips the gate"  SKIP "$(outcome "$(piped "$sh" "$h" "$DEL" "$DEL2")")"
    check "$p a normal push runs the gate"       GATE "$(outcome "$(piped "$sh" "$h" "$UPD")")"
    check "$p a mixed push runs the gate"        GATE "$(outcome "$(piped "$sh" "$h" "$DEL" "$UPD")")"
    check "$p deleting main"                     "$main_del" "$(outcome "$(piped "$sh" "$h" "$DELMAIN")")"
    check "$p pushing main"                      "$main_push" "$(outcome "$(piped "$sh" "$h" "$PUSHMAIN")")"
    check "$p ALLOW_MAIN_PUSH=1 lets main through" GATE \
      "$(outcome "$(printf '%s\n' "$PUSHMAIN" | ALLOW_MAIN_PUSH=1 run "$sh" "$h" env)")"
    check "$p empty stdin runs the gate"         GATE "$(outcome "$(printf '' | run "$sh" "$h" env)")"
    check "$p /dev/null runs the gate"           GATE "$(outcome "$(run "$sh" "$h" env </dev/null)")"
    check "$p closed stdin runs the gate, no hang" GATE "$(outcome "$(run "$sh" "$h" env <&-)")"
    check "$p a failing build stops the push"    FAILED "$(outcome "$(printf '%s\n' "$UPD" | NPM_FAIL=build run "$sh" "$h" env)")"
    check "$p failing tests stop the push"       FAILED "$(outcome "$(printf '%s\n' "$UPD" | NPM_FAIL=test run "$sh" "$h" env)")"
    check "$p refs from a file are read"         SKIP "$(outcome "$(run "$sh" "$h" env <"$T/del.txt")")"
    # A socket is neither a pipe nor a file; a guard testing for those read nothing here.
    if command -v python3 >/dev/null 2>&1; then
      out="$(cd "$T/site" && $TO python3 -c '
import socket, subprocess, sys
a, b = socket.socketpair(); a.sendall(open(sys.argv[3], "rb").read()); a.shutdown(socket.SHUT_WR)
r = subprocess.run([sys.argv[1], sys.argv[2]], stdin=b, capture_output=True, text=True)
print(r.stdout + r.stderr + "\n@@rc=%d" % r.returncode)' "$sh" "$h" "$T/pushmain.txt" 2>&1)"
      check "$p refs from a socket are read" "$main_push" "$(outcome "$out")"
    fi
    # Without /proc, /dev/stdin does not resolve — the case that let main through in PR #125.
    # Needs unprivileged user namespaces; where they are off, say so rather than fail.
    if command -v unshare >/dev/null 2>&1 && unshare -rm true 2>/dev/null; then
      out="$(printf '%s\n' "$PUSHMAIN" | (cd "$T/site" && $TO unshare -rm "$sh" -c \
        'mount -t tmpfs none /proc 2>/dev/null || exit 97; exec "$0" "$1"' "$sh" "$h") 2>&1
        printf '\n@@rc=%s\n' "$?")"
      case "$out" in
        *"@@rc=97"*) printf 'skip %s without /proc (could not hide /proc)\n' "$p" ;;
        *) check "$p refs are read without /proc" "$main_push" "$(outcome "$out")" ;;
      esac
    else
      printf 'skip %s without /proc (no unprivileged unshare here)\n' "$p"
    fi
  done
done

# A site with scripts/verify.mjs: the hook runs that instead of `npm run build` and `npm test`,
# and a red step in it must still refuse the push. The real script, against the stub npm. It
# starts npm by name only without npm's own entry in npm_execpath, so the cases blank it: a
# push from `npm run ship` hands the hook npm's (test_verify.sh covers that branch).
TPL_VERIFY="$HERE/../skills/new-website/templates/astro/scripts/verify.mjs"
if command -v node >/dev/null 2>&1; then
  mkdir -p "$T/site-v/scripts" "$T/site-v/node_modules"
  cp "$TPL_VERIFY" "$T/site-v/scripts/verify.mjs"
  echo '{}' >"$T/site-v/package-lock.json"
  for sh in $shells; do
    p="$sh, site with verify.mjs:"
    out="$(printf '%s\n' "$UPD" | SITE_DIR="$T/site-v" npm_execpath= run "$sh" "$T/off" env)"
    check "$p a normal push runs the gate"      GATE "$(outcome "$out")"
    check "$p ... through verify.mjs"           yes "$(has "$out" "✓ verify: all green")"
    check "$p ... and not the old build step"   no "$(has "$out" "npm run build")"
    check "$p a failing check stops the push"   FAILED "$(outcome "$(printf '%s\n' "$UPD" | SITE_DIR="$T/site-v" npm_execpath= NPM_FAIL=check run "$sh" "$T/off" env)")"
    check "$p failing tests stop the push"      FAILED "$(outcome "$(printf '%s\n' "$UPD" | SITE_DIR="$T/site-v" npm_execpath= NPM_FAIL=test run "$sh" "$T/off" env)")"
  done
else
  echo "SKIP: the verify.mjs cases need node. The hook's verify.mjs path was NOT run."
fi

# Real git: what it actually hands the hook, end to end, as shipped and with the block on.
# Each pass gets a fresh remote, so every push below has a ref to change.
for v in off on; do
  R="$T/remote-$v.git"; W="$T/work-$v"
  $git init -q --bare "$R"
  $git init -q "$W"
  $git -C "$W" commit -q --allow-empty -m one
  $git -C "$W" push -q "$R" HEAD:refs/heads/main HEAD:refs/heads/feat HEAD:refs/heads/feat2 HEAD:refs/heads/keep 2>/dev/null
  # A remote refuses to delete the branch its HEAD names, whatever the hook says; point HEAD
  # elsewhere so "deleting main" tests the hook, not that server-side refusal.
  $git -C "$R" symbolic-ref HEAD refs/heads/keep
  mkdir -p "$W/.hooks"; cp "$T/$v" "$W/.hooks/pre-push"; chmod +x "$W/.hooks/pre-push"
  gpush() { (cd "$W" && $TO $git -c core.hooksPath="$W/.hooks" push "$R" "$@") 2>&1; printf '\n@@rc=%s\n' "$?"; }
  # remote <branch> — the remote's commit for it, or "none": proof a refused push changed nothing.
  remote() { $git -C "$R" rev-parse -q --verify "refs/heads/$1" 2>/dev/null || echo none; }
  $git -C "$W" commit -q --allow-empty -m two
  if [ "$v" = on ]; then main_push=BLOCK main_del=BLOCK; else main_push=GATE main_del=SKIP; fi
  check "git, block $v: --delete of a branch skips the gate" SKIP "$(outcome "$(gpush --delete feat)")"
  check "git, block $v: a mixed push runs the gate"          GATE "$(outcome "$(gpush HEAD:refs/heads/feat2 :refs/heads/feat3)")"
  $git -C "$W" commit -q --allow-empty -m three   # something new, so the refused push had work to do
  before="$(remote feat2)"
  check "git, block $v: the next push would change feat2"    yes "$([ "$before" != "$($git -C "$W" rev-parse HEAD)" ] && echo yes)"
  check "git, block $v: a failing build refuses the push"    FAILED "$(outcome "$(NPM_FAIL=build gpush HEAD:refs/heads/feat2)")"
  check "git, block $v: ... and the remote is unchanged"     "$before" "$(remote feat2)"
  before="$(remote main)"
  check "git, block $v: pushing main"                        "$main_push" "$(outcome "$(gpush HEAD:refs/heads/main)")"
  if [ "$v" = on ]; then
    check "git, block on: ... and the remote main is unchanged" "$before" "$(remote main)"
  fi
  before="$(remote main)"
  check "git, block $v: deleting main"                       "$main_del" "$(outcome "$(gpush --delete main)")"
  if [ "$v" = on ]; then
    check "git, block on: ... and main still exists"          "$before" "$(remote main)"
  else
    check "git, block off: ... and main is gone"              none "$(remote main)"
  fi
done

# The "prepare" script in the template's package.json is what wires the hook: npm runs it in
# the site's folder on every install, through the shell it uses for scripts — by default sh
# on macOS and Linux, cmd.exe on Windows. So the line may hold nothing that one shell reads
# differently from another: it only starts scripts/wire-hooks.mjs, and that script does the
# work. It may point git at scripts/hooks only where the site is the root of its repo. Run
# from a site kept in a subfolder of a bigger repo, an older line pointed that repo's hook
# folder at a scripts/hooks the repo does not have; git then runs no hooks there at all and
# says nothing.
# This toolkit's own commit guard was dead with exactly that setting: the template is such a
# subfolder here, and that line was the only thing in the repo that wrote the value. The
# install that set it was not observed.
TPL="$HERE/../skills/new-website/templates/astro"
PKG="$TPL/package.json"
prepare="$(sed -n 's/^ *"prepare": "\(.*\)",\{0,1\}$/\1/p' "$PKG")"
check "package.json has a prepare line this test can read" yes "$([ -n "$prepare" ] && echo yes)"
# cmd.exe has no `unset`, no /dev/null and no `true`, and reads quotes its own way. A quote or
# a backslash would also be a JSON escape, which sed, reading the line here, does not undo.
check "... and it is a command with plain arguments: nothing a shell has to interpret" 0 "$(printf '%s\n' "$prepare" | grep -c '[^A-Za-z0-9 ./_-]')"
wire="${prepare#node }"
check "... and the script it starts ships in the template" yes "$([ -f "$TPL/$wire" ] && echo yes)"
# The hook's header quotes the line, so a site that has only the hook can repair an old one.
check "... and the hook's header quotes that same line" yes "$(grep -qxF -- "#   $prepare" "$HOOK" && echo yes)"

# site <dir> — what a site has of the starter that "prepare" needs: package.json and the script.
site() { mkdir -p "$(dirname "$1/$wire")" && cp "$PKG" "$1/package.json" && cp "$TPL/$wire" "$1/$wire"; }
# prep <dir> — run "prepare" there through npm, as an install does: npm's own script runner
# and the shell it picks. Prints the exit status.
prep() { (cd "$1" && "$NPM" run --silent prepare) >/dev/null 2>&1; echo "$?"; }
# said <dir> — the same run; prints what it wrote, which an install shows to whoever runs it.
said() { (cd "$1" && "$NPM" run --silent prepare) 2>&1; }
hooks_path() { $git -C "$1" config --local --get core.hooksPath || echo unset; }

if [ -z "$NPM" ] || ! command -v node >/dev/null 2>&1; then
  echo "SKIP: the prepare cases need node and npm (they run the line through npm, as an install does). The script that wires the hook was NOT run."
else
  # npm writes a log per run into its cache folder; a throwaway one keeps this test out of ~/.npm.
  export npm_config_cache="$T/npm-cache" npm_config_update_notifier=false
  $git init -q "$T/root-site"; site "$T/root-site"
  check "prepare, site at the root of its repo: exits 0"         0 "$(prep "$T/root-site")"
  check "prepare, ... and the hook folder is wired"              scripts/hooks "$(hooks_path "$T/root-site")"
  check "prepare, ... without a word"                            "" "$(said "$T/root-site")"
  $git init -q "$T/big"; site "$T/big/apps/site"
  check "prepare, site in a subfolder of a bigger repo: exits 0" 0 "$(prep "$T/big/apps/site")"
  check "prepare, ... and that repo's hooks are left alone"      unset "$(hooks_path "$T/big")"
  # A git hook that runs `npm install` (post-merge, post-checkout) can hand it GIT_DIR: in a
  # linked worktree git exports an absolute one to its hooks. Git then takes the current folder
  # for the top of the working tree, so "am I in a subfolder?" answers no. The script must not
  # trust that.
  check "prepare, ... also run from a git hook (GIT_DIR set): exits 0" 0 "$(GIT_DIR="$T/big/.git" prep "$T/big/apps/site")"
  check "prepare, ... and that repo's hooks are still left alone" unset "$(hooks_path "$T/big")"
  # A git started with --git-dir and --work-tree (a deploy hook's `git --work-tree=… checkout`)
  # hands its hooks GIT_WORK_TREE=. as well. Dropping only one of the two still leaves git
  # taking the site's folder for the top.
  check "prepare, ... also with GIT_WORK_TREE handed down too: exits 0" 0 "$(GIT_DIR="$T/big/.git" GIT_WORK_TREE=. prep "$T/big/apps/site")"
  check "prepare, ... and that repo's hooks are left alone with both set" unset "$(hooks_path "$T/big")"
  # The script asks git about the folder it sits in, not the one it was started from. Started
  # by hand from the top of the bigger repo, it must not take that top for the site.
  check "prepare, ... also started from the top of the bigger repo: exits 0" 0 "$(cd "$T/big" && node "apps/site/$wire" >/dev/null 2>&1; echo "$?")"
  check "prepare, ... and that repo's hooks are left alone then too" unset "$(hooks_path "$T/big")"
  $git -C "$T/big" config core.hooksPath .githooks
  check "prepare, ... also when it has a hook folder: exits 0"   0 "$(prep "$T/big/apps/site")"
  check "prepare, ... and that folder stays in use"              .githooks "$(hooks_path "$T/big")"
  site "$T/plain"
  check "prepare, folder outside any repo: exits 0"              0 "$(GIT_CEILING_DIRECTORIES="$T" prep "$T/plain")"
  check "prepare, ... and says nothing"                          "" "$(GIT_CEILING_DIRECTORIES="$T" said "$T/plain")"
  # git is here and the site is the top of its repo, but git refuses the write: something
  # else holds the lock on the repo's config. Still no failed install, and the one case
  # that says a word, since the gate is off and nothing else would tell.
  $git init -q "$T/locked"; site "$T/locked"; : >"$T/locked/.git/config.lock"
  check "prepare, git refuses the write: exits 0"                0 "$(prep "$T/locked")"
  check "prepare, ... and says the hook is not wired"            1 "$(said "$T/locked" | grep -c 'NOT wired')"
  check "prepare, ... which it is not"                           unset "$(hooks_path "$T/locked")"
  # A machine without git: node alone, on a PATH that holds nothing, in a repo the script
  # would wire if it found git — so a repo left unwired shows git was really out of reach.
  $git init -q "$T/no-git"; site "$T/no-git"; mkdir -p "$T/empty"
  node_bin="$(node -p process.execPath)"
  check "prepare, no git on the machine: exits 0 and says nothing" 0 "$(cd "$T/no-git" && PATH="$T/empty" "$node_bin" "$wire" 2>&1; echo "$?")"
  check "prepare, ... and git was out of reach there"            unset "$(hooks_path "$T/no-git")"
fi

if [ $fails -ne 0 ]; then echo "$fails check(s) FAILED"; exit 1; fi
echo "all checks passed"
